"""Private exact-file continuity for a Cent-owned managed Session."""

import os
import re
from dataclasses import replace
from hashlib import sha256

from skatmind.accounting_state import CentRoundV1
from skatmind.accounting_store import accounting_publication_lock, load_accounting
from skatmind.automatic_learning_codec import canonical_json
from skatmind.automatic_learning_io import (
    checked_root,
    read_bounded,
    sync_directory,
    write_temporary,
)
from skatmind.event_context_sources import build_event_binding_v1, recording_version_v1
from skatmind.session_history import build_session_state_from_accepted_prefix_v1
from skatmind.session_persistence import save_session_persistence_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1

from .accounting_forms import AccountingFormError
from .managed_item_discovery import discover_managed_items_v1
from .whole_match_progress import file_identity


def entries_for(category):
    result = discover_managed_items_v1(category, family="sessions", generation=1)
    if result.view.candidate_limit_reached:
        raise AccountingFormError("source")
    return result.entries


def unique_entry(entries, source):
    matches = [e for e in entries if e.summary.semantic_product_id == source.product_id]
    if len(matches) != 1 or matches[0].summary.status != "available":
        raise AccountingFormError("source")
    return matches[0]


def _receipt_path(home, source):
    # Locate by source, not filename: renaming a file must not select the legacy path.
    key = sha256(canonical_json(source.to_dict())).hexdigest()
    return home / f".cent-member-{key}.receipt"


def _read(path):
    checked_root(path.parent)
    try:
        raw = read_bounded(path, 160)
    except FileNotFoundError:
        return None
    if not re.fullmatch(rb"cent-file-v1\n(?:[a-f0-9]{64}\n){1,2}", raw):
        raise AccountingFormError("source")
    return raw.splitlines()[1:]


def _endpoint(row, binding, path, document, stamp):
    return sha256(canonical_json([row.table_id, row.identity, binding.to_dict(),
        path.name, document.content_fingerprint, stamp])).hexdigest().encode("ascii")


def _write(path, *endpoints):
    temp = write_temporary(path.parent, b"cent-file-v1\n" + b"\n".join(endpoints) + b"\n")
    try:
        os.replace(temp, path)
        sync_directory(path.parent)
    finally:
        temp.unlink(missing_ok=True)


def anchor_created(row, binding, active):
    """The verified revision-zero publication is the first exact file endpoint."""
    path = _receipt_path(active.category_root.parent, binding.source)
    if file_identity(active.path) != active.saved_file_identity:
        raise AccountingFormError("source")
    endpoint = _endpoint(row, binding, active.path, active.document, active.saved_file_identity)
    saved = _read(path)
    if saved is None:
        _write(path, endpoint)
    elif endpoint not in saved:
        raise AccountingFormError("source")


def validate_binding(row, document, path):
    version = recording_version_v1(document)
    binding = row.context.binding(version.source)
    if binding is None:
        raise AccountingFormError("source")
    rebuilt = build_event_binding_v1(document, game_position=binding.game_position,
        selected_player_id=binding.source_selected_player_id,
        player_map={p.source_player_id: p.event_player_id for p in binding.players})
    if replace(rebuilt, attached_source=binding.attached_source) != binding:
        raise AccountingFormError("source")
    endpoints = _read(_receipt_path(path.parent.parent, binding.source))
    if endpoints is not None:
        if _endpoint(row, binding, path, document, file_identity(path)) not in endpoints:
            raise AccountingFormError("source")
        return binding

    # Legacy journals predate file receipts. Require the complete retained content
    # fingerprints, including any checkpoint collected on the boundary revision.
    retained = {binding.attached_source, *(r.source for r in row.recordings
                                            if r.source.source == version.source)}
    for prior in retained - {version}:
        if prior.revision > version.revision:
            raise AccountingFormError("source")
        prefix = build_session_state_from_accepted_prefix_v1(document.state,
                                                             target_revision=prior.revision)
        earlier = tuple(c for c in document.decision_checkpoints if c.source_revision <
                        prior.revision)
        through = tuple(c for c in document.decision_checkpoints if c.source_revision <=
                        prior.revision)
        if not any(build_session_persistence_document_v1(prefix, decision_checkpoints=cs
                ).content_fingerprint == prior.content_fingerprint for cs in (earlier, through)):
            raise AccountingFormError("source")
    return binding


def save_cent_member_edit(active, candidate):
    """Return the guarded save status, or None for the ordinary Session adapter."""
    home = active.category_root.parent
    source = recording_version_v1(active.document).source
    expected = active.document.content_fingerprint
    receipt = _receipt_path(home, source)
    try:
        owner = load_accounting(home).for_source(source)
    except (ValueError, OSError):
        # An unreadable optional journal cannot grant continuity, nor should it
        # stop independent capture. Leave a known member's last endpoint intact.
        if os.path.lexists(receipt):
            return "conflict"
        owner = None
    if not isinstance(owner, CentRoundV1):
        return None

    # Same serialization order as accounting: lifecycle/Session -> journal -> file CAS.
    with accounting_publication_lock():
        def guard(staged):
            stamp = active.saved_file_identity
            if (load_accounting(home).for_source(source) != owner or
                    unique_entry(entries_for(active.category_root), source).path != active.path
                    or file_identity(active.path) != stamp):
                raise AccountingFormError("source")
            binding = validate_binding(owner, active.document, active.path)
            # Write ahead of replace. After interruption only the endpoint matching
            # the actual file (including its inode/stamp) can authorize access.
            _write(receipt,
                   _endpoint(owner, binding, active.path, active.document, stamp),
                   _endpoint(owner, binding, active.path, candidate, file_identity(staged)))
            if file_identity(active.path) != stamp:
                raise AccountingFormError("source")

        try:
            return save_session_persistence_file_v1(active.path, candidate,
                expected_content_fingerprint=expected, before_replace=guard).status
        except AccountingFormError:
            return "conflict"
