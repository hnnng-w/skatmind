"""One recoverable Cent game publication. Never search for an orphan by label."""

import hashlib
import os

from skatmind.accounting_state import CentRoundV1
from skatmind.accounting_store import (
    MAX_BYTES,
    accounting_bytes,
    append_accounting,
    load_accounting,
    save_accounting,
)
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_learning_io import (
    checked_root,
    read_bounded,
    sync_directory,
    write_temporary,
)
from skatmind.event_context_recording_files import load_event_recording_v1
from skatmind.event_context_sources import recording_version_v1
from skatmind.session_persistence_codec import resume_session_document_v1

from .accounting_forms import AccountingFormError
from .cent_sources import open_bound, session_entries
from .event_context_frontend import EventFormConflict
from .managed_item_storage import build_managed_item_handle_v1, build_managed_item_storage_path_v1
from .session_frontend import create_guided_session_v1
from .whole_match_progress import file_identity

PENDING = ".cent-game-start.json"
INTENT_LIMIT = 4 * 1024 * 1024


def pending(root):
    checked_root(root)
    try:
        return read_bounded(root / PENDING, INTENT_LIMIT)
    except FileNotFoundError:
        return None


def release_attempt(root, raw):
    """Release only this reservation; saved recordings and journal rows are never removed."""
    if raw is None or pending(root) != raw:
        raise EventFormConflict("stale")
    (root / PENDING).unlink()
    sync_directory(root)


def publish_game(app, journal, row, document, *, parent=None, documents=(), guard):
    """Reserve a validated attempt before creating either durable Product object."""
    root = app.managed_home.root
    updated = append_accounting(journal, row)
    if len(accounting_bytes(updated)) > MAX_BYTES:
        raise AccountingFormError()
    candidate = updated.head(row.identity)
    payload = dict(row=candidate.to_dict(), document=document.to_dict(),
        parent=None if parent is None else [parent.identity, parent.revision],
        sources=[[path.name, file_identity(path), recording_version_v1(doc).to_dict()]
                 for path, doc in documents])
    raw = canonical_json(dict(version=1, attempt=payload,
                              digest=hashlib.sha256(canonical_json(payload)).hexdigest()))
    if len(raw) > INTENT_LIMIT or pending(root) is not None or not guard():
        raise EventFormConflict("save")
    path = build_managed_item_storage_path_v1(app.managed_stateful.root("sessions"),
        family="sessions", product_id=document.state.session_id)
    if os.path.lexists(path) or any(e.summary.semantic_product_id == document.state.session_id
                                    for e in session_entries(app)):
        raise EventFormConflict("source")
    temp = write_temporary(root, raw)
    try:
        os.link(temp, root / PENDING)  # no-clobber publication of the complete intent
        sync_directory(root)
    finally:
        temp.unlink()
    return complete_game(app, raw, journal, guard=guard)


def complete_game(app, raw, journal, *, guard):
    root = app.managed_home.root
    envelope = decode_json(raw)
    if (not isinstance(envelope, dict) or set(envelope) != {"version", "digest", "attempt"}
            or type(envelope["version"]) is not int or envelope["version"] != 1):
        raise EventFormConflict("save")
    attempt = envelope["attempt"]
    if (not isinstance(attempt, dict) or set(attempt) != {"row", "document", "parent", "sources"}
            or hashlib.sha256(canonical_json(attempt)).hexdigest() != envelope["digest"]
            or pending(root) != raw):
        raise EventFormConflict("save")
    row = CentRoundV1.from_dict(attempt["row"])
    document = resume_session_document_v1(attempt["document"]).document
    state = document.state
    version = recording_version_v1(document)
    binding = row.context.binding(version.source)
    if state.revision or binding is None or binding.attached_source != version:
        raise AccountingFormError("source")
    committed = row in journal.rounds
    category = app.managed_stateful.root("sessions")
    path = build_managed_item_storage_path_v1(category, family="sessions",
                                              product_id=state.session_id)
    entries = session_entries(app)
    if not committed:
        parent = attempt["parent"]
        if parent is not None:
            previous = journal.head(parent[0])
            if previous is None or previous.revision != parent[1]:
                raise EventFormConflict("stale")
        candidate = append_accounting(journal, row)
        if candidate.head(row.identity) != row:
            raise EventFormConflict("stale")
        def current():
            if not guard() or pending(root) != raw:
                return False
            current_entries = session_entries(app)
            for name, stamp, source in attempt["sources"]:
                matches = [e for e in current_entries if e.summary.semantic_product_id ==
                           source["source"]["product_id"] and e.summary.status == "available"]
                if (len(matches) != 1 or matches[0].path.name != name
                        or file_identity(matches[0].path) != stamp):
                    return False
                if recording_version_v1(load_event_recording_v1(matches[0].path, "session")
                        ).to_dict() != source:
                    return False
            return True
        if not current():
            raise EventFormConflict("source")
        if not os.path.lexists(path):
            if any(e.summary.semantic_product_id == state.session_id for e in entries):
                raise EventFormConflict("source")
            create_guided_session_v1(category, handle=build_managed_item_handle_v1(
                family="sessions", basename=path.name), session_id=state.session_id,
                players=state.players, capture_mode=state.capture_mode,
                local_player_id=state.local_player_id)
        def ready():
            active = open_bound(app, row, binding, session_entries(app))
            return active.path == path and active.document == document and current()
        save_accounting(root, candidate, expected_fingerprint=journal.fingerprint,
                        source_guard=ready)
    published = load_accounting(root)
    owner = published.for_source(version.source)
    if row not in published.rounds or owner is None or owner.identity != row.identity:
        raise EventFormConflict("save")
    active = open_bound(app, owner, binding, session_entries(app))
    if (active.path != path or active.document != document or pending(root) != raw
            or published.head(row.identity) != row):
        raise EventFormConflict("save")
    release_attempt(root, raw)
    return active
