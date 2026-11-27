"""Order Match recording submissions with their own post-save Live attempt."""

from http import HTTPStatus

from .card_entry_http import dispatch_card_entry
from .compact_declaration_http import dispatch_compact_declaration
from .local_time_http import dispatch_local_metadata
from .match_declaration_drafts import MATCH_RECORDING_INPUT_ROUTE, dispatch_recording_input
from .match_frontend import apply_unified_match_operation_v1
from .match_live_advice import (
    MATCH_LIVE_ROUTES,
    configure_match_live,
    match_live_redirect,
    reserve_match_live,
    run_match_live,
)
from .match_recovery_http import dispatch_match_recovery
from .workflow_state import StaleFrontendWorkflowRevisionError


def _apply(handler, app, active, path, body, content_type):
    if path == MATCH_RECORDING_INPUT_ROUTE:
        return dispatch_recording_input(handler, handler._urlencoded_form(body, content_type))
    if path in MATCH_LIVE_ROUTES or path == "/matches/recovery/apply":
        values = handler._text_form(body, content_type)
        handler._bound_active("matches", values)
        if path in MATCH_LIVE_ROUTES:
            if app.recording_task == "/record-after":
                raise StaleFrontendWorkflowRevisionError()
            configure_match_live(active, path, values, profile=app.frontend_profile.document)
            return f"/matches/position/{active.selected_position}#match-recording"
        return dispatch_match_recovery(app, active, path, values)
    values = handler._flat_form(body, content_type, repeated_cards=True)
    if path == "/matches/cards":
        return dispatch_card_entry(app, path, values)
    if "time_form" in values or "time_selection" in values:
        return dispatch_local_metadata(app, path, values)
    if "declaration_form" in values or "declaration_selection" in values:
        return dispatch_compact_declaration(app, path, values)
    handler._bound_active("matches", values)
    result = apply_unified_match_operation_v1(active, values)
    if result.http_status != HTTPStatus.OK:
        handler._reject_match_result(active, active.selected_position, result)
        return None
    return f"/matches/position/{active.selected_position}#match-recording"


def handle_match_input(handler, path, body, content_type):
    app = handler.server.app_context
    with app.managed_stateful.match_lifecycle_lock:
        with app.lock:
            active = app.managed_stateful.active_match
        if active is None:
            raise StaleFrontendWorkflowRevisionError()
        with active.capture.lock:
            active.require_attached()
            before, control = active.workspace, active.live.control_revision
            try:
                location = _apply(handler, app, active, path, body, content_type)
            except (ValueError, StaleFrontendWorkflowRevisionError) as error:
                if path not in MATCH_LIVE_ROUTES and active.live.effort is None:
                    raise
                stale = isinstance(error, StaleFrontendWorkflowRevisionError)
                if stale and (path in MATCH_LIVE_ROUTES or getattr(error, "reason", "") == "stale"):
                    handler._send_common_error(HTTPStatus.CONFLICT)
                elif not handler._reject_registered_form(error, status=(
                        HTTPStatus.CONFLICT if stale else HTTPStatus.BAD_REQUEST)):
                    raise
                return
            if location is None:  # The native handler already delivered a rejection.
                return
            try:
                attempt = reserve_match_live(active, before, control)
            except Exception:
                # Optional advice must never turn a committed edit into a failed save.
                active.live.invalidate()
                attempt = None
            handler._clear_redirect_feedback()
    if attempt is not None:
        if not run_match_live(app, active, attempt):
            handler._send_common_error(HTTPStatus.CONFLICT)
            return
        location, handler._retained_delivery_guard = match_live_redirect(
            app, active, attempt, location)
    handler._redirect(location, clear_feedback=False)
