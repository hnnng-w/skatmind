"""Private single-file removal under single-app ownership, with optimistic rechecks.

The final check and unlink are separate operations. Uncontrolled external writers
can still race that interval; this is not atomic compare-and-delete.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import stat
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from skatmind.api.v1.session import files as session_files
from skatmind.errors import SkatMindError
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

from .managed_item_contracts import MANAGED_ITEM_MAX_IMPORT_BYTES
from .managed_item_discovery import discover_managed_items_v1
from .managed_item_storage import validate_managed_direct_child_path_v1
from .workflow_state import StaleFrontendWorkflowRevisionError

DELETION_PAGE = "/recordings/delete"
DELETION_POST_ROUTES = tuple(
    f"{DELETION_PAGE}/{action}" for action in ("preview", "apply", "cancel"))
DELETION_BODY_LIMIT = 8_192
DELETION_LIFETIME = 1_800
RETURN_AREAS = {"sessions": "/sessions", "matches": "/matches", "review": "/review/recorded"}


class RecordingDeletionConflict(StaleFrontendWorkflowRevisionError):
    """A fresh named preview is required; no client target can replace it."""


class RecordingDeletionRefused(ValueError):
    """A filesystem refusal before removal; the accepted attempt is consumed."""


@dataclass(frozen=True, slots=True)
class DeletionPreview:
    selection: str
    family: str
    handle: str
    path: Path
    product_id: str
    fingerprint: str
    digest: str
    file_identity: tuple
    root_identity: tuple
    summary: object
    profile_label: object
    players: tuple[str | None, ...]
    progress: tuple[int, ...]
    active: object
    active_binding: tuple
    return_area: str
    created_at: float


@dataclass(slots=True)
class RecordingDeletionState:
    # Order: deletion gate -> family lifecycle gate -> Product lock -> short app lock.
    lock: RLock = field(default_factory=RLock, repr=False)
    pending: DeletionPreview | None = field(default=None, repr=False)
    outcome: str | None = None
    outcome_area: str | None = None


def current_deletion_preview(app):
    with app.lock:
        preview = app.recording_deletion.pending
        return (preview if preview is not None
                and time.monotonic() - preview.created_at < DELETION_LIFETIME else None)


def _label(app, family, identity):
    profile = app.frontend_profile.document
    return next((label for label in (() if profile is None else profile.managed_item_display_labels)
                 if label.family == family and label.product_id == identity), None)


def _active(app, family, path):
    managed = app.managed_stateful
    value = managed.active_session if family == "sessions" else managed.active_match
    return value if value is not None and value.path == path else None


def _binding(active, family):
    if active is None:
        return ()
    if family == "sessions":
        return (active.generation, active.document.content_fingerprint, active.review_selection_key,
                active.execution, active.recorded_review_source, active.execution_attempt)
    return (active.capture.content_fingerprint, active.card_entry_key,
            active.selected_position, active.position_generation,
            active.capture.report_store.generation, active.capture.report_store.list(),
            active.recovery.selected, active.recovery.preview)


def _gate(app, family):
    managed = app.managed_stateful
    return managed.session_lifecycle_lock if family == "sessions" else managed.match_lifecycle_lock


def _product_lock(active, family):
    return (nullcontext() if active is None else active.lock if family == "sessions"
            else active.capture.lock)


def _stamp(value):
    return (value.st_dev, value.st_ino, getattr(value, "st_birthtime_ns", None),
            value.st_ctime_ns, value.st_mtime_ns, value.st_size, value.st_nlink, value.st_mode)


def _root_stamp(value):
    return (value.st_dev, value.st_ino, getattr(value, "st_birthtime_ns", None))


def _checked_stat(root, path):
    validate_managed_direct_child_path_v1(root, path, expected_kind="file")
    parent, target = root.lstat(), path.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if any(getattr(value, "st_file_attributes", 0) & reparse for value in (parent, target)):
        raise RecordingDeletionConflict()
    if target.st_nlink != 1 or not 0 < target.st_size <= MANAGED_ITEM_MAX_IMPORT_BYTES:
        raise RecordingDeletionConflict()
    return _root_stamp(parent), _stamp(target)


def _digest(root, path):
    before = _checked_stat(root, path)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        descriptor = _stamp(os.fstat(stream.fileno()))
        # Windows 3.13 lstat/fstat expose different ctime semantics. Compare their
        # file ID, birthtime, mtime, size, links and type; recheck each own full stamp.
        if descriptor[:3] + descriptor[4:] != before[1][:3] + before[1][4:]:
            raise RecordingDeletionConflict()
        raw = stream.read(MANAGED_ITEM_MAX_IMPORT_BYTES + 1)
        if (len(raw) > MANAGED_ITEM_MAX_IMPORT_BYTES
                or _stamp(os.fstat(stream.fileno())) != descriptor):
            raise RecordingDeletionConflict()
    if _checked_stat(root, path) != before:
        raise RecordingDeletionConflict()
    return (*before, hashlib.sha256(raw).hexdigest())


def _load(root, path, family):
    """Strict load without activation, migration Save, or retained file contents."""
    before = _digest(root, path)
    resumed = (session_files.load_session_file(path).value if family == "sessions"
               else load_match_workspace_file_v1(path))
    if _digest(root, path) != before:
        raise RecordingDeletionConflict()
    document = resumed.document
    if family == "sessions":
        source = document.state
        identity = source.session_id
        players = tuple(player.player_label for player in source.players)
        progress = (sum(record.command.kind == "record_play" for record in source.command_log),)
    else:
        source = document.workspace
        identity = source.match_definition.match_id
        players = tuple(player.player_label for player in source.match_definition.participants)
        progress = (resumed.progress.observed_game_count, resumed.progress.passed_deal_count,
                    resumed.progress.empty_slot_count)
    return identity, document.content_fingerprint, before, players, progress


def _fresh_entry(root, family, handle, product_id):
    # A fresh bounded classification detects newly introduced semantic duplicates.
    discovery = discover_managed_items_v1(root, family=family, generation=1)
    entry = discovery.resolve(handle)
    if (discovery.view.candidate_limit_reached or entry is None
            or entry.summary.status != "available"
            or entry.summary.semantic_product_id != product_id):
        raise RecordingDeletionConflict()
    return entry


def prepare_recording_deletion(app, values):
    if set(values) != {"family", "handle", "generation", "return_area"}:
        raise ValueError("Use the exact recording selection form.")
    family = values["family"]
    if (family not in {"sessions", "matches"} or values["return_area"] not in {family, "review"}
            or not re.fullmatch(r"[0-9a-f]{64}", values["handle"])
            or not re.fullmatch(r"[1-9][0-9]{0,15}", values["generation"])):
        raise ValueError("Use a supported recording and return area.")
    with app.recording_deletion.lock, _gate(app, family):
        with app.lock:
            managed = app.managed_stateful
            try:
                entry = managed.resolve(family, handle=values["handle"],
                                        generation=int(values["generation"]))
            except ValueError as error:
                raise RecordingDeletionConflict() from error
            if entry.summary.status != "available":
                raise RecordingDeletionConflict()
            root = managed.root(family)
            active = _active(app, family, entry.path)
            label = _label(app, family, entry.summary.semantic_product_id)
        with _product_lock(active, family):
            try:
                identity, fingerprint, stamps, players, progress = _load(root, entry.path, family)
                fresh = _fresh_entry(root, family, values["handle"], identity)
                if (identity != entry.summary.semantic_product_id or fresh.path != entry.path
                        or (active is not None and _binding(active, family)[
                            1 if family == "sessions" else 0] != fingerprint)):
                    raise RecordingDeletionConflict()
            except (OSError, ValueError, SkatMindError) as error:
                raise RecordingDeletionConflict() from error
            with app.lock:
                if (managed.resolve(family, handle=values["handle"],
                                    generation=int(values["generation"])) is not entry
                        or _label(app, family, identity) != label):
                    raise RecordingDeletionConflict()
                preview = DeletionPreview(secrets.token_hex(32), family, values["handle"],
                    entry.path, identity, fingerprint, stamps[2], stamps[1], stamps[0],
                    fresh.summary, label, players, progress, active, _binding(active, family),
                    values["return_area"], time.monotonic())
                app.recording_deletion.pending = preview
                app.recording_deletion.outcome = None
                app.form_feedback.clear("deletion")
    return DELETION_PAGE


def _require_selection(app, selection):
    preview = current_deletion_preview(app)
    if (type(selection) is not str or not re.fullmatch(r"[0-9a-f]{64}", selection)
            or preview is None or not secrets.compare_digest(preview.selection, selection)):
        raise RecordingDeletionConflict()
    return preview


def _revalidate(app, preview):
    if time.monotonic() - preview.created_at >= DELETION_LIFETIME:
        raise RecordingDeletionConflict()
    family, path = preview.family, preview.path
    root = app.managed_stateful.root(family)
    with app.lock:
        if (_active(app, family, path) is not preview.active
                or _label(app, family, preview.product_id) != preview.profile_label):
            raise RecordingDeletionConflict()
    if _binding(preview.active, family) != preview.active_binding:
        raise RecordingDeletionConflict()
    _checked_stat(root, path)
    fresh = _fresh_entry(root, family, preview.handle, preview.product_id)
    identity, fingerprint, stamps, _players, _progress = _load(root, path, family)
    if (fresh.path != path or fresh.summary.display_label != preview.summary.display_label
            or identity != preview.product_id or fingerprint != preview.fingerprint
            or stamps != (preview.root_identity, preview.file_identity, preview.digest)):
        raise RecordingDeletionConflict()
    with app.lock:
        if _label(app, family, preview.product_id) != preview.profile_label:
            raise RecordingDeletionConflict()


def invalidate_deletion_activation(app, previous, current):
    """Caller holds the app lock; only the pending target's activation matters."""
    preview = app.recording_deletion.pending
    if preview is not None and any(value is not None and value.path == preview.path
                                   for value in (previous, current)):
        app.recording_deletion.pending = None


def validate_deletion_preview(app, preview):
    """Read-only GET/language validation retains target, consent absence, and expiry."""
    with app.recording_deletion.lock, _gate(app, preview.family), _product_lock(
            preview.active, preview.family):
        if _require_selection(app, preview.selection) is not preview:
            raise RecordingDeletionConflict()
        try:
            _revalidate(app, preview)
        except (OSError, ValueError, SkatMindError) as error:
            raise RecordingDeletionConflict() from error


def cancel_recording_deletion(app, values):
    if set(values) != {"deletion_selection"}:
        raise ValueError("Cancel accepts only its exact deletion selection.")
    with app.recording_deletion.lock, app.lock:
        preview = _require_selection(app, values["deletion_selection"])
        app.recording_deletion.pending = None
    return RETURN_AREAS[preview.return_area]


def apply_recording_deletion(app, values):
    if set(values) != {"deletion_selection", "confirm_delete"} or values["confirm_delete"] != "on":
        raise ValueError("Permanent deletion requires fresh explicit confirmation.")
    with app.recording_deletion.lock:
        with app.lock:
            preview = _require_selection(app, values["deletion_selection"])
            # Consume before any accepted destructive attempt, including a refused attempt.
            app.recording_deletion.pending = None
        with _gate(app, preview.family), _product_lock(preview.active, preview.family):
            try:
                _revalidate(app, preview)
            except PermissionError as error:
                raise RecordingDeletionRefused() from error
            except (OSError, ValueError, SkatMindError) as error:
                raise RecordingDeletionConflict() from error
            try:
                # One narrow removal, no retry, permission changes, recursion or rollback.
                preview.path.unlink()
            except OSError as error:
                raise RecordingDeletionRefused() from error
            active = preview.active
            if active is not None:
                active.retired = True
                if preview.family == "sessions":
                    active.clear_execution()
                    active.last_operation = None
                else:
                    active.capture.report_store.clear()
                    active.capture.workspace = None
                    active.capture.content_fingerprint = None
                    active.recovery.clear()
                    active.last_result = active.transfer_notice = None
            with app.lock:
                if active is not None:
                    attribute = "active_session" if preview.family == "sessions" else "active_match"
                    setattr(app.managed_stateful, attribute, None)
                    app.form_feedback.clear(preview.family)
                    app.stateful_creation_notices.pop(preview.family, None)
                language = app.language_context
                def bound(page):
                    return any(reference is preview or (active is not None and reference is active)
                               for reference in page.source.references)
                language.pages = {token: page for token, page in language.pages.items()
                                  if not bound(page)}
                if language.pending is not None and bound(language.pending[0]):
                    language.pending = None
                # Commit the truth before a fallible discovery refresh.
                app.recording_deletion.outcome = "deleted"
                app.managed_stateful.generations[preview.family] += 1
                app.managed_stateful.discoveries.pop(preview.family, None)
    return preview
