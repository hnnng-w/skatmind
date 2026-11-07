"""Exact native saved-Review discovery, reopen and confirmed head deletion."""

import secrets
from contextlib import ExitStack
from dataclasses import dataclass, replace
from html import escape

from skatmind.automatic_learning_store import StoreConflictError
from skatmind.errors import SkatMindError

from .automatic_learning_controller import automatic_controller
from .automatic_learning_http import authorize_response
from .automatic_learning_rendering import link
from .historical_learning_rendering import historical_caption, render_historical_evidence
from .historical_review_routes import HISTORICAL_EXECUTION_DOWNLOAD, HISTORICAL_VIEW, SAVED_REVIEWS
from .language_context import capture_language_source_v1
from .stateful_localization import text
from .task_first_rendering import disclosure, form, hidden, paragraph


@dataclass(frozen=True, slots=True)
class ReviewDeletionPreview:
    token: str
    view: object
    index: int
    head: object
    value: object


def _entries(view):
    resumed = view.binding.resumed
    return () if resumed is None else tuple(row for row in resumed.manifest.evidence
                                            if row.envelope.kind == "historical_review")


def _head_value(controller, view, index):
    if view.binding.resumed is None:
        raise StoreConflictError("Saved Review authority is unavailable.")
    head = view.binding.resumed.manifest.historical_heads[index]
    return head, controller.service.read_delivery_evidence(view.binding, head.evidence_id)


def reopen_review(app, controller, view, index):
    head, value = _head_value(controller, view, index)
    controller.service.validate_delivery(view.binding)
    source, execution = value.source, value.execution
    with app.lock:
        controller.service.validate_delivery(view.binding)
        state = app.review_state
        state = state.mutate(expected_revision=state.revision, **(
            {"draft": value.guided_draft} if source.draft is not None else
            {"imported_request": source.request,
             "request_json_bytes": execution.request_json_bytes}))
        state = state.begin(expected_revision=state.revision)
        state = state.publish(expected_revision=state.revision, execution_revision=state.revision,
            request=execution.request, options=execution.options, result=execution.result,
            request_json_bytes=execution.request_json_bytes,
            result_json_bytes=execution.result_json_bytes)
        app.review_state = state
        owner = app.historical_reviews
        owner.source_id, owner.origin = head.source.product_id, source.origin
        owner.head, owner.source, owner.pending = head, source, None
        owner.correction = True
        owner.notice = (state, "saved", head.evidence_id)
    return state


def delete_review(app, controller, preview):
    owner = app.historical_reviews
    controller.service.validate_delivery(preview.view.binding)
    before = preview.view.binding.resumed.manifest
    requested = replace(before, revision=before.revision + 1,
        historical_heads=tuple(row for row in before.historical_heads if row != preview.head),
        historical_retired=tuple(sorted((*before.historical_retired, preview.head.source),
                                        key=lambda key: key.identity)))
    with app.lock:
        if owner.confirmation is not preview:
            raise StoreConflictError("Review deletion consent expired.")
        def guard():
            from .automatic_session_inventory import mixed_inventory_still_current
            service, binding = controller.service, preview.view.binding
            return (app.historical_reviews is owner and owner.confirmation is preview
                and service._owner(binding.attempt) and service.attempt is binding.attempt
                and service._installed is binding.installed
                and service.coordinator.generation == binding.epoch
                and mixed_inventory_still_current(service.home, binding.inventory))
        store = controller.service.store
        try:
            result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                                           commit_guard=guard)
            if result.status == "conflict":
                raise StoreConflictError("Review deletion conflicted.")
        except OSError:
            if store.snapshot().manifest != requested:
                raise
        owner.confirmation = None
        if owner.head == preview.head:
            owner.new(None)
            app.review_state = app.review_state.reset(expected_revision=app.review_state.revision)
    return requested


def recovery(handler):
    handler._retained_delivery_guard = handler._rendered_language_source = None
    handler._retained_delivery_recovery = None
    locale = handler._frontend_state().locale
    body = '<section class="error-summary" role="alert" tabindex="-1" autofocus>'
    body += paragraph(locale, "historical_learning.conflict") + '</section>'
    body += link(SAVED_REVIEWS, text(locale, "historical_learning.saved"))
    handler._content_page("/review", return_to=SAVED_REVIEWS, status=409,
        title=text(locale, "historical_learning.saved"), content=body,
        untranslated_workflow_body=False, task_first=True)


def handle_get(handler, path):
    download = HISTORICAL_EXECUTION_DOWNLOAD.fullmatch(path)
    if download is not None:
        app = handler.server.app_context
        try:
            value = app.historical_reviews.views[download[1]]
            value.validate(app)
            handler._retained_delivery_guard = lambda: value.validate(app)
            handler._retained_delivery_recovery = lambda: recovery(handler)
            raw = getattr(value.state, download[2] + "_json_bytes")
            if raw is None:
                raise StoreConflictError("Original native download is unavailable.")
            with ExitStack() as stack:
                if value.store is not None:
                    entry = next(row for row in value.resumed.manifest.evidence
                                 if row.identity == value.notice[2])
                    stack.enter_context(value.store.pin_objects((entry.envelope,),
                        expected_manifest=value.resumed.manifest.fingerprint))
                handler._send_artifact("skatmind-review-" + download[2] + ".json", raw)
        except (OSError, ValueError, KeyError, SkatMindError):
            recovery(handler)
        return True
    match = HISTORICAL_VIEW.fullmatch(path)
    if path != SAVED_REVIEWS and match is None:
        return False
    app = handler.server.app_context
    locale = handler._frontend_state().locale
    try:
        controller = automatic_controller(app)
        pending = getattr(handler, "_language_return", None)
        original = None if pending is None else pending[0].source.automatic_view
        view = (controller.resolve(match[1]) if match else controller.resolve(original.token)
                if original is not None else controller.capture())
        if original is not None and view is not original:
            raise StoreConflictError("Original Review view changed.")
        with ExitStack() as stack:
            stack.enter_context(controller.service.delivery_reader(view.binding))
            if view.binding.resumed is not None:
                refs = tuple(entry.envelope for entry in _entries(view)
                    if entry.identity in view.binding.resumed.available_evidence_ids)
                stack.enter_context(controller.service.store.pin_objects(refs,
                    expected_manifest=view.binding.resumed.manifest.fingerprint))
            authorize_response(handler, controller, view)
            handler._retained_delivery_recovery = lambda: recovery(handler)
            body = ""
            base = SAVED_REVIEWS + "/" + view.token
            if match:
                kind, index = match[2], int(match[3])
                if kind == "evidence":
                    entry = _entries(view)[index]
                    value = controller.service.read_delivery_evidence(view.binding, entry.identity)
                    if match[4]:
                        handler._send_artifact(*value.download(match[4]))
                        return True
                    current = any(head.source_version_id == entry.source_version_id
                                  for head in view.binding.resumed.manifest.historical_heads)
                    body += paragraph(locale, "historical_learning.current" if current else
                                      "historical_learning.retained")
                    body += render_historical_evidence(value, path, locale)
                elif kind == "source":
                    head, value = _head_value(controller, view, index)
                    body += '<h2>' + escape(historical_caption(value, locale)) + '</h2>'
                    body += paragraph(locale, "historical_learning.source", plays=sum(
                        len(trick.plays) for trick in value.game.tricks), origin=text(
                            locale, "historical_learning.origin." + value.source.origin))
                    fields = hidden("view", view.token) + hidden("source", index)
                    body += form(locale, "/review/reopen", fields, "historical_learning.reopen")
                    body += form(locale, "/review/delete-preview", fields,
                                 "historical_learning.delete")
                    body += '<ul>' + ''.join('<li>' + link(base + "/evidence/" + str(i),
                        text(locale, "saved_analysis.open")) + '</li>'
                        for i, entry in enumerate(_entries(view))
                        if entry.source_version_id == head.source_version_id) + '</ul>'
                    body += disclosure(locale, "task.technical", '<p>' + escape(
                        head.source_version_id) + '</p>', technical=True)
                else:
                    preview = app.historical_reviews.confirmation
                    if preview is None or preview.view is not view or preview.index != index:
                        raise StoreConflictError("Original deletion preview expired.")
                    body += '<h2 id="review-deletion" tabindex="-1" autofocus>' + escape(
                        historical_caption(preview.value, locale)) + '</h2>'
                    count = sum(entry.source_version_id == preview.head.source_version_id
                                for entry in _entries(view))
                    body += paragraph(locale, "historical_learning.delete_effect", count=count)
                    fields = hidden("confirmation", preview.token)
                    fields += '<label><input type="checkbox" name="confirm_delete" required>'
                    fields += escape(
                        text(locale, "validation.field.confirm_delete")) + '</label>'
                    body += form(locale, "/review/delete-confirm", fields,
                                 "historical_learning.delete_confirm", destructive=True)
                    original_guard = handler._retained_delivery_guard
                    def guard():
                        original_guard()
                        if app.historical_reviews.confirmation is not preview:
                            raise StoreConflictError("Deletion preview changed.")
                    handler._retained_delivery_guard = guard
            else:
                manifest = None if view.binding.resumed is None else view.binding.resumed.manifest
                for index, head in enumerate(() if manifest is None else manifest.historical_heads):
                    if head.evidence_id not in view.binding.resumed.available_evidence_ids:
                        body += paragraph(locale, "saved_analysis.excluded")
                        continue
                    _head, value = _head_value(controller, view, index)
                    body += '<p>' + link(base + "/source/" + str(index),
                                        historical_caption(value, locale)) + '</p>'
                body += '<h2>' + escape(text(locale, "historical_learning.evidence")) + '</h2>'
                for index, entry in enumerate(_entries(view)):
                    if entry.identity in view.binding.resumed.available_evidence_ids:
                        value = controller.service.read_delivery_evidence(
                            view.binding, entry.identity)
                        body += '<p>' + link(base + "/evidence/" + str(index),
                                            historical_caption(value, locale)) + '</p>'
            body += link(SAVED_REVIEWS, text(locale, "historical_learning.saved"))
            body += link("/review", text(locale, "historical_learning.manual"))
            body += link("/learning/automatic", text(locale, "automatic.back"))
            handler._rendered_language_source = capture_language_source_v1(
                app, path, automatic_view=view)
            handler._content_page("/review", return_to=path,
                title=text(locale, "historical_learning.saved"),
                content=body, untranslated_workflow_body=False, task_first=True)
    except (OSError, ValueError, KeyError, IndexError, SkatMindError):
        recovery(handler)
    return True


def handle_post(handler, path, values):
    app = handler.server.app_context
    try:
        from .historical_review_retention import capture_manual_delivery
        controller = automatic_controller(app)
        if path == "/review/retry-saving":
            from .historical_review_retention import save_pending_historical
            handler._exact_fields(values, {"save_token"})
            pending = app.historical_reviews.pending
            save_pending_historical(app, values["save_token"])
            delivery = capture_manual_delivery(app)
            if pending is None or delivery.state is not pending.state:
                raise StoreConflictError("The original retry delivery changed.")
            handler._retained_delivery_guard = lambda: delivery.validate(app)
            destination = "/review"
        elif path == "/review/delete-confirm":
            handler._exact_fields(values, {"confirmation", "confirm_delete"})
            preview = app.historical_reviews.confirmation
            if (preview is None or values["confirmation"] != preview.token
                    or values["confirm_delete"] != "on"):
                raise StoreConflictError("Explicit original consent is required.")
            authority = delete_review(app, controller, preview)
            current = controller.capture()
            if (current.binding.resumed.manifest != authority
                    or current.binding.attempt is not preview.view.binding.attempt):
                raise StoreConflictError("Review deletion committed before newer publication.")
            authorize_response(handler, controller, current)
            destination = SAVED_REVIEWS
        else:
            handler._exact_fields(values, {"view", "source"})
            from .automatic_learning_http import _index
            view, index = controller.resolve(values["view"]), _index(values["source"])
            if path == "/review/reopen":
                state = reopen_review(app, controller, view, index)
                delivery = capture_manual_delivery(app)
                if delivery.state is not state:
                    raise StoreConflictError("Reopened Review delivery was superseded.")
                def guard():
                    controller.service.validate_delivery(view.binding)
                    delivery.validate(app)
                handler._retained_delivery_guard = guard
                destination = "/review"
            else:
                head, value = _head_value(controller, view, index)
                preview = ReviewDeletionPreview(secrets.token_hex(32), view, index, head, value)
                with app.lock:
                    controller.service.validate_delivery(view.binding)
                    app.historical_reviews.confirmation = preview
                def guard():
                    controller.service.validate_delivery(view.binding)
                    if app.historical_reviews.confirmation is not preview:
                        raise StoreConflictError("Original deletion preview changed.")
                handler._retained_delivery_guard = guard
                destination = SAVED_REVIEWS + "/" + view.token + "/delete/" + str(index)
        handler._retained_delivery_recovery = lambda: recovery(handler)
        handler._redirect(destination)
    except (OSError, ValueError, KeyError, IndexError, SkatMindError):
        recovery(handler)
