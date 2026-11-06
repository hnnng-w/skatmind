"""Native S5 transport. Serialize first, authorize at headers, retain reader lifetime."""

from html import escape

from skatmind.automatic_learning_store import (
    StoreConflictError,
    StoreLimitError,
    StoreManifestError,
)
from skatmind.automatic_match_preparation import UnsupportedGeneration
from skatmind.errors import SkatMindError

from .automatic_learning_controller import automatic_controller
from .automatic_learning_rendering import (
    link,
    render_confirmation,
    render_entry,
    render_evidence,
    render_review,
    render_situation,
    render_source,
    situations,
)
from .automatic_learning_routes import AUTOMATIC_CONFIRMATION, AUTOMATIC_PAGE, AUTOMATIC_VIEW
from .automatic_match_inventory import InventoryConflict
from .language_context import capture_language_source_v1
from .stateful_localization import text
from .task_first_rendering import paragraph


def failure_kind(error):
    if isinstance(error, StoreManifestError):
        return "invalid_storage"
    if isinstance(error, StoreLimitError):
        return "quota"
    if isinstance(error, UnsupportedGeneration):
        return "unsupported"
    if isinstance(error, (StoreConflictError, InventoryConflict)):
        return "conflict"
    return "failed"


def recovery(handler, kind="conflict", *, status=409):
    """Complete source-independent response; never recursively render rejected evidence."""
    handler._retained_delivery_guard = None
    handler._retained_delivery_recovery = None
    handler._rendered_language_source = None
    handler._operation_feedback_delivery = None
    locale = handler._frontend_state().locale
    body = '<section class="error-summary" role="alert" tabindex="-1" autofocus><h2>'
    body += escape(text(locale, "automatic.failure_title")) + '</h2>'
    body += paragraph(locale, "automatic.state." + kind) + '</section>'
    body += link(AUTOMATIC_PAGE, text(locale, "automatic.recover"))
    body += link("/learning/collections", text(locale, "automatic.independent"))
    if kind == "quota":
        from .automatic_learning_rendering import maintenance
        try:
            controller = automatic_controller(handler.server.app_context)
            view = controller.capture()
            body += maintenance(view, locale).replace('<details ', '<details open ', 1)
            authorize_response(handler, controller, view)
        except (OSError, ValueError, SkatMindError):
            pass  # Source-independent recovery remains complete if storage is inaccessible.
    handler._content_page("/learning", title=text(locale, "automatic.title"), content=body,
        return_to=AUTOMATIC_PAGE, status=status, untranslated_workflow_body=False, task_first=True)


def authorize_response(handler, controller, view, *, confirmation=None):
    def guard():
        if handler.server.app_context.automatic_learning_ui is not controller:
            raise StoreConflictError("Automatic frontend changed.")
        controller.service.validate_delivery(view.binding)
        if confirmation is not None:
            controller.require_confirmation(confirmation.token)
    handler._retained_delivery_guard = guard
    handler._retained_delivery_recovery = lambda: recovery(handler)


def send_page(handler, controller, view, route, body, *, status=200, confirmation=None):
    authorize_response(handler, controller, view, confirmation=confirmation)
    handler._rendered_language_source = capture_language_source_v1(
        handler.server.app_context, route, automatic_view=view)
    handler._operation_feedback_delivery = (controller, "automatic", controller.feedback_source(),
                                             status >= 400)
    handler._content_page("/learning",
        title=text(handler._frontend_state().locale, "automatic.title"),
        content=body, return_to=route, status=status,
        feedback_family="learning" if route == "/learning" else "automatic",
        feedback_identity=None if route == "/learning" else controller,
        untranslated_workflow_body=False, task_first=True)


def _entry_view(handler, controller):
    pending = getattr(handler, "_language_return", None)
    original = None if pending is None else pending[0].source.automatic_view
    if original is not None:
        if controller.resolve(original.token) is not original:
            raise StoreConflictError("Automatic language entry changed.")
        return original
    return controller.capture()


def send_landing(handler, manual_body, *, status=200):
    try:
        controller = automatic_controller(handler.server.app_context)
        view = _entry_view(handler, controller)
        with controller.service.delivery_reader(view.binding):
            send_page(handler, controller, view, "/learning",
                render_entry(view, handler._frontend_state().locale, landing=True) + manual_body,
                status=status)
    except (OSError, ValueError, SkatMindError) as error:
        recovery(handler, failure_kind(error))


def handle_get(handler, path):
    match = AUTOMATIC_VIEW.fullmatch(path)
    confirmation_match = AUTOMATIC_CONFIRMATION.fullmatch(path)
    if path != AUTOMATIC_PAGE and match is None and confirmation_match is None:
        return False
    try:
        controller = automatic_controller(handler.server.app_context)
        locale = handler._frontend_state().locale
        if confirmation_match is not None:
            value = controller.require_confirmation(confirmation_match[1])
            # Deliberately no delivery_reader/consume: a new pin invalidates exact consent.
            send_page(handler, controller, value.view, path, render_confirmation(value, locale),
                      confirmation=value)
            return True
        view = _entry_view(handler, controller) if match is None else controller.resolve(match[1])
        with controller.service.delivery_reader(view.binding):
            if match is None:
                body = render_entry(view, locale)
            else:
                if (view.binding.result.status not in ("current", "outdated")
                        or view.binding.installed is None):
                    raise StoreConflictError("Automatic result unavailable.")
                selector = match[2]
                parts = selector.split("/")
                if parts[0] == "session":
                    from .session_learning_navigation import render_session_page
                    if len(parts) == 4:
                        value = view.binding.installed.bundle.session_evidence[int(parts[2])]
                        authorize_response(handler, controller, view)
                        handler._send_artifact(*value.download(parts[3][:-5]))
                        return True
                    body = render_session_page(view, parts[1], int(parts[2]), locale)
                    send_page(handler, controller, view, path, body)
                    return True
                if parts[0] == "downloads":
                    kind = parts[1][:-5].replace("-", "_")
                    download = view.binding.installed.bundle.download(kind)
                    authorize_response(handler, controller, view)
                    handler._send_artifact(download.filename, download.content)
                    return True
                if parts[0] == "evidence" and len(parts) == 3:
                    value = view.binding.installed.bundle.evidence[int(parts[1])]
                    filename, content = value.download(parts[2][:-5])
                    authorize_response(handler, controller, view)
                    handler._send_artifact(filename, content)
                    return True
                if parts[0] in ("source", "situation", "evidence"):
                    body = {"source": render_source, "situation": render_situation,
                            "evidence": render_evidence}[parts[0]](view, int(parts[1]), locale)
                    from .automatic_learning_rendering import update_form
                    body += update_form(view, locale)
                else:
                    body = render_review(view, selector, locale).body
            send_page(handler, controller, view, path, body)
    except (OSError, ValueError, KeyError, IndexError, StopIteration, SkatMindError) as error:
        recovery(handler, failure_kind(error))
    return True


def _index(value):
    if not value.isascii() or not value.isdecimal() or str(int(value)) != value or len(value) > 7:
        raise ValueError("Expected a canonical bounded index.")
    return int(value)


def handle_post(handler, path, values):
    try:
        controller = automatic_controller(handler.server.app_context)
        handler._submitted_active = controller
        action = path.rsplit("/", 1)[1]
        fields = {"update": {"view"}, "exclude-preview": {"view", "source"},
                  "cleanup-preview": {"view", "mode"}, "confirm": {"confirmation", "confirm_apply"},
                  "recording": {"view", "situation"}}[action]
        handler._exact_fields(values, fields)
        if action == "confirm":
            if values["confirm_apply"] != "on":
                raise ValueError("Explicit unchecked-by-default consent is required.")
            view = controller.confirm(values["confirmation"])
            destination = AUTOMATIC_PAGE
        else:
            view = controller.resolve(values["view"])
            if action == "update":
                result, current = controller.update(view)
                if current is None:
                    recovery(handler, result.failure or result.status)
                    return
                view = current
                destination = view.base + "/all#learning-result"
            elif action == "exclude-preview":
                confirmation = controller.preview_exclusion(view, _index(values["source"]))
                destination = AUTOMATIC_PAGE + "/confirmation/" + confirmation.token
            elif action == "cleanup-preview":
                if values["mode"] not in ("orphans", "old_evidence", "obsolete_sources"):
                    raise ValueError("Unsupported cleanup mode.")
                confirmation = controller.preview_cleanup(view,
                    old_evidence=values["mode"] == "old_evidence",
                    obsolete_sources=values["mode"] == "obsolete_sources")
                destination = AUTOMATIC_PAGE + "/confirmation/" + confirmation.token
            else:
                if values["situation"].startswith("session-"):
                    from .session_learning_navigation import open_session_recording
                    destination = open_session_recording(handler, controller, view,
                        _index(values["situation"][8:]))
                else:
                    destination = open_recording(handler, controller, view,
                                                 _index(values["situation"]))
        with handler.server.app_context.lock:
            handler.server.app_context.form_feedback.clear("automatic")
        authorize_response(handler, controller, view)
        handler._redirect(destination)
    except (OSError, ValueError, KeyError, IndexError, SkatMindError) as error:
        from .validation_contracts import FrontendValidationIssueV1
        definition = getattr(handler, "_current_form_definition", None)
        if definition is not None:
            handler._retain_form_feedback(definition, issues=(FrontendValidationIssueV1(
                field_key=None, message_key="validation.message.stale" if isinstance(
                    error, (StoreConflictError, InventoryConflict))
                    else "validation.message.product_rejected"),),
                status=409 if isinstance(error, (StoreConflictError, InventoryConflict)) else 400)
        recovery(handler, failure_kind(error), status=409 if isinstance(
            error, (StoreConflictError, InventoryConflict, StoreManifestError)) else 400)


def open_recording(handler, controller, view, index):
    from .managed_item_discovery import discover_managed_items_v1
    from .match_decision_selection import apply_match_decision_selection
    from .match_frontend import open_unified_match_v1, select_unified_match_position_v1

    if view.binding.result.status != "current":
        raise StoreConflictError("Prior reviews cannot open a current recording.")
    bundle = view.binding.installed.bundle
    source_index, snapshot, ref = situations(bundle)[index]
    record = bundle.sources[source_index][0]
    rows = [row for row in view.binding.inventory.rows if row.status == "selected"
            and row.source_version_id == record.source_version.identity]
    if len(rows) != 1:
        raise StoreConflictError("The exact original recording is not current.")
    app = handler.server.app_context
    root = app.managed_home.category("matches").path
    discovery = discover_managed_items_v1(root, family="matches", generation=1)
    entries = [entry for entry in discovery.entries
               if entry.summary.semantic_product_id == snapshot.match_id
               and entry.summary.status == "available"]
    if len(entries) != 1:
        raise StoreConflictError("Recording ownership changed.")
    active = open_unified_match_v1(root, entries[0])
    with active.capture.lock:
        if active.capture.content_fingerprint != record.source_version.content_fingerprint:
            raise StoreConflictError("Recording version changed.")
        controller.service.validate_delivery(view.binding)
        select_unified_match_position_v1(active, ref.match_position)
        apply_match_decision_selection(active, ref.decision_index)
    handler._activate_match(active)
    return f"/matches/review/{ref.match_position}"
