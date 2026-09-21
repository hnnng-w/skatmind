"""Exact private leaf forms under the existing Session lifecycle lock."""

from __future__ import annotations

from dataclasses import replace
from http import HTTPStatus

from .card_entry_http import CardEntryConflict, _fresh
from .compact_declaration_form import DECLARATION_FIELDS, form_error, parse_compact_declaration
from .compact_declaration_http import _session_rejection
from .session_declaration_correction import (
    SessionCorrectionConflict,
    apply_correction,
    current_selection,
    preview_correction,
    require_selection,
    select_correction,
)
from .workflow_state import StaleFrontendWorkflowRevisionError


def handle_session_correction(handler, path, body, content_type):
    """Include strict parsing/rejection in the same lifecycle order as Apply."""
    from .form_registry import capture_safe_submitted_values_v1, get_frontend_form_by_key_v1

    app = handler.server.app_context
    action = path.rsplit("/", 1)[-1]
    with app.managed_stateful.session_lifecycle_lock:
        with app.lock:
            active = app.managed_stateful.active_session
        if active is None:
            raise SessionCorrectionConflict()
        with active.lock:
            pending = active.declaration_correction
            kind = pending.selected.record.command.kind if pending.selected else "set_declaration"
            definition = get_frontend_form_by_key_v1("session.correction." + action
                + ("." + kind if action == "preview" else ""))
            handler._current_form_definition = definition
            handler._submitted_active = active
            try:
                parsed = handler._urlencoded_form(body, content_type)
                handler._current_safe_values = capture_safe_submitted_values_v1(definition, parsed)
                if (action == "preview" and current_selection(active, pending.selected)
                        and parsed.get("managed_handle") == [active.handle]
                        and parsed.get("correction_selection") == [pending.selected.token]):
                    pending.preview = None
                if any(len(items) != 1 for items in parsed.values()):
                    raise form_error("duplicate")
                values = {key: items[0] for key, items in parsed.items()}
                if not values.get("managed_handle") or not values.get("correction_selection"):
                    raise form_error("fields")
                if values.pop("managed_handle", None) != active.handle:
                    raise SessionCorrectionConflict()
                location = dispatch_session_correction(app, active, path, values)
            except (ValueError, StaleFrontendWorkflowRevisionError) as error:
                handler._reject_registered_form(error, status=(HTTPStatus.CONFLICT if isinstance(
                    error, StaleFrontendWorkflowRevisionError) else HTTPStatus.BAD_REQUEST))
                return
            handler._redirect(location)


def dispatch_session_correction(app, active, path, values):
    """Caller holds lifecycle/Session locks even through error publication."""
    action = path.rsplit("/", 1)[-1]
    active.require_attached()
    with app.lock:
        if app.managed_stateful.active_session is not active:
            raise SessionCorrectionConflict()
    token = values.get("correction_selection", "")
    state = active.declaration_correction
    if action == "preview":
        selected = require_selection(active, token)
        # Invalid replacement attempts also revoke the older Apply, before parsing.
        state.preview = None
    elif action == "cancel":
        require_selection(active, token)
    required = {"correction_selection"}
    allowed = set(required)
    if action == "preview":
        kind = selected.record.command.kind
        required.add("correction_kind")
        required.update(("player_id",) if kind == "set_declarer" else
                        ("game_type", "bid_value", "matadors"))
        allowed = required | (set(DECLARATION_FIELDS) if kind == "set_declaration" else set())
        if values.get("correction_kind") != kind:
            raise form_error("fields")
    elif action == "apply":
        required.add("confirm_apply")
        allowed = required
    if required - set(values) or set(values) - allowed:
        raise form_error("fields")
    try:
        _fresh(active, session=True)
    except CardEntryConflict as error:
        state.clear()
        raise SessionCorrectionConflict(error.reason) from error
    if action == "select":
        select_correction(active, token)
    elif action == "preview":
        original = selected.record.command
        if original.kind == "set_declarer":
            if values["player_id"] not in {p.player_id for p in selected.source.state.players}:
                raise form_error("declarer", "player_id")
            command = replace(original, declarer_player_id=values["player_id"])
        else:
            command = replace(original, declaration=parse_compact_declaration(values))
        result = preview_correction(active, selected, command)
        if result.status == "rejected":
            # Existing typed Matador path/code mapping; no prose parsing or rules copy.
            from .session_frontend import GuidedSessionOperationResultV1
            raise _session_rejection(GuidedSessionOperationResultV1(status="rejected",
                message="The replacement was rejected.", validation_diagnostics=result.diagnostics))
        if result.status == "revision_conflict":
            raise SessionCorrectionConflict()
    elif action == "apply":
        if values["confirm_apply"] != "on":
            raise form_error("fields", "confirm_apply")
        apply_correction(active, token)
    else:
        require_selection(active, token)
        state.clear()
    anchor = ("session-declaration-correction" if action in {"select", "preview"}
              else "session-recording")
    return "/sessions/current#" + anchor
