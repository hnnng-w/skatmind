from __future__ import annotations

import re

from skatmind.api.v1.session import files as session_files
from skatmind.errors import SkatMindError
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

from .managed_item_storage import validate_managed_direct_child_path_v1
from .match_frontend import open_unified_match_v1
from .session_frontend import open_guided_session_v1
from .workflow_state import StaleFrontendWorkflowRevisionError

RECORDED_REVIEW_ROUTE = "/review/recorded"
OPEN_RECORDING_ROUTE = "/review/open-recording"
RECORDING_FAMILIES = ("sessions", "matches")


class RecordingOpenConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason="selection"):
        self.reason = reason
        super().__init__("The selected recording context changed.")


def require_recording_fresh_v1(active, family: str) -> None:
    """Use strict canonical loaders without replacing memory or extending any lifetime."""
    try:
        validate_managed_direct_child_path_v1(active.category_root, active.path,
                                             expected_kind="file")
        if family == "sessions":
            document = session_files.load_session_file(active.path).value.document
            expected = active.document.content_fingerprint
        else:
            document = load_match_workspace_file_v1(active.path).document
            expected = active.capture.content_fingerprint
        if document.content_fingerprint != expected:
            raise RecordingOpenConflict("file")
    except (OSError, ValueError, SkatMindError) as error:
        raise RecordingOpenConflict("file") from error


def open_recording_for_review_v1(context, values: dict[str, str]) -> str:
    if set(values) != {"family", "handle", "generation"}:
        raise ValueError("Recording selection accepts only family, handle and generation.")
    family = values["family"]
    if (family not in RECORDING_FAMILIES or not re.fullmatch(r"[0-9a-f]{64}", values["handle"])
            or not re.fullmatch(r"[1-9][0-9]{0,15}", values["generation"])):
        raise ValueError("Recording selection fields are invalid.")
    managed = context.managed_stateful
    attribute = "active_session" if family == "sessions" else "active_match"
    gate = managed.session_lifecycle_lock if family == "sessions" else managed.match_lifecycle_lock
    generation = int(values["generation"])

    def resolve():
        try:
            entry = managed.resolve(family, handle=values["handle"], generation=generation)
        except ValueError as error:
            raise RecordingOpenConflict() from error
        if entry.summary.status != "available":
            raise RecordingOpenConflict()
        return entry

    with context.lock:
        entry = resolve()
        previous = getattr(managed, attribute)
        root = managed.root(family)
    with gate:
        with context.lock:
            if getattr(managed, attribute) is not previous or resolve() is not entry:
                raise RecordingOpenConflict()
        same = (previous is not None and previous.handle == entry.summary.handle
                and previous.path == entry.path)
        if same:
            active = previous
        else:
            try:
                active = (open_guided_session_v1(root, entry) if family == "sessions"
                          else open_unified_match_v1(root, entry))
            except (OSError, ValueError, SkatMindError) as error:
                raise RecordingOpenConflict() from error
        lock = active.lock if family == "sessions" else active.capture.lock
        with lock:
            identity = (active.state.session_id if family == "sessions"
                        else active.workspace.match_definition.match_id)
            if identity != entry.summary.semantic_product_id:
                raise RecordingOpenConflict()
            require_recording_fresh_v1(active, family)
            with context.lock:
                if getattr(managed, attribute) is not previous or resolve() is not entry:
                    raise RecordingOpenConflict()
                if not same:
                    from .recording_deletion import invalidate_deletion_activation
                    invalidate_deletion_activation(context, previous, active)
                    if family == "sessions":
                        managed.activate_session(active)
                    else:
                        managed.activate_match(active)
                    context.form_feedback.clear(family)
            location = ("/sessions/current#recorded-decisions" if family == "sessions"
                        else f"/matches/review/{active.selected_position}")
        if not same and previous is not None:
            old_lock = previous.lock if family == "sessions" else previous.capture.lock
            with old_lock:
                if family == "sessions":
                    previous.clear_execution()
                else:
                    previous.capture.report_store.clear()
                    previous.recovery.clear()
    return location
