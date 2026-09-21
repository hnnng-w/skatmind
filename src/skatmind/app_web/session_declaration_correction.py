"""Bounded Session-only staged correction; the public immutable operation owns replay."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, replace

import skatmind.api.v1.session as api

from .workflow_state import StaleFrontendWorkflowRevisionError

CORRECTION_ROUTES = tuple(f"/sessions/declaration-correction/{action}" for action in (
    "select", "preview", "apply", "cancel"))
CORRECTION_BODY_LIMIT = 8192
CORRECTION_KINDS = ("set_declarer", "set_declaration")


class SessionCorrectionConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason="stale"):
        super().__init__()
        self.reason = reason


@dataclass(frozen=True, slots=True)
class SessionCorrectionSelection:
    token: str
    source: api.SessionPersistenceDocumentV1
    generation: int
    context_key: bytes
    handle: str
    record: api.SessionCommandRecordV1
    created_at: float


@dataclass(frozen=True, slots=True)
class SessionCorrectionPreview:
    correction: api.SessionCommandCorrectionV1
    result: api.SessionCorrectionResultV1
    apply_token: str


@dataclass(slots=True)
class SessionDeclarationCorrectionState:
    """Owned by the existing Session lock, never persisted or shared across contexts."""

    entries: tuple[SessionCorrectionSelection, ...] = ()
    selected: SessionCorrectionSelection | None = None
    proposal: api.SessionCommandV1 | None = None
    preview: SessionCorrectionPreview | None = None

    def clear(self):
        self.entries = ()
        self.selected = None
        self.proposal = None
        self.preview = None


def accepted_record(context, kind):
    records = tuple(r for r in context.state.command_log if r.command.kind == kind)
    return records[0] if len(records) == 1 else None


def current_selection(context, selection):
    return (selection is not None and not context.retired
        and selection.context_key == context.review_selection_key
        and selection.handle == context.handle and selection.generation == context.generation
        and selection.source == context.document
        and accepted_record(context, selection.record.command.kind) == selection.record
        and time.monotonic() - selection.created_at < 1800)


def correction_entries(context):
    """At most two source entries. GET never evaluates a correction candidate."""
    state = context.declaration_correction
    state.entries = tuple(item for item in state.entries if current_selection(context, item))
    if not current_selection(context, state.selected):
        state.selected = state.proposal = state.preview = None
    if context.retired:
        return ()
    for kind in CORRECTION_KINDS:
        record = accepted_record(context, kind)
        if record is not None and not any(item.record == record for item in state.entries):
            state.entries += (SessionCorrectionSelection(secrets.token_hex(32), context.document,
                context.generation, context.review_selection_key, context.handle,
                record, time.monotonic()),)
    return state.entries


def require_selection(context, token):
    selected = context.declaration_correction.selected
    if not current_selection(context, selected) or selected.token != token:
        raise SessionCorrectionConflict()
    return selected


def select_correction(context, token):
    state = context.declaration_correction
    old = state.selected
    selection = (old if old is not None and old.token == token else
                 next((item for item in state.entries if item.token == token), None))
    if not current_selection(context, selection):
        raise SessionCorrectionConflict()
    # Each explicit selection is a new editor identity; stale Cancel cannot clear it.
    state.selected = replace(selection, token=secrets.token_hex(32))
    state.proposal = state.proposal if selection is old else selection.record.command
    state.preview = None


def preview_correction(context, selection, command):
    correction = api.SessionCommandCorrectionV1(expected_revision=context.state.revision,
        target_revision=selection.record.revision, replacement_command=command)
    result = api.correct_session_command(context.state, correction).value
    state = context.declaration_correction
    state.proposal = command
    state.preview = SessionCorrectionPreview(correction, result, secrets.token_hex(32))
    return result


def apply_correction(context, token):
    from .session_frontend import correct_guided_session_command_v1

    state = context.declaration_correction
    preview = state.preview
    if (preview is None or preview.apply_token != token
            or preview.result.status not in {"applied", "partial", "unchanged"}):
        raise SessionCorrectionConflict()
    require_selection(context, state.selected.token if state.selected else "")
    rebuilt = api.correct_session_command(context.state, preview.correction).value
    if rebuilt != preview.result:
        state.preview = None
        raise SessionCorrectionConflict()
    # The caller holds the lifecycle gate AND the reentrant Session lock throughout.
    # Recalculation here deliberately reuses the authoritative Checkpoint/save boundary.
    try:
        result = correct_guided_session_command_v1(context, preview.correction)
    except OSError as error:
        state.preview = None
        raise SessionCorrectionConflict("save_failed") from error
    if result.status not in {"applied", "partial", "unchanged"}:
        state.preview = None
        raise SessionCorrectionConflict("file_changed")
    state.clear()
    return result
