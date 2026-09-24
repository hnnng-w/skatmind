"""Native confirmation and bounded HTTP adapter for managed recording removal."""

from __future__ import annotations

from html import escape

from .friendly_creation_rendering import managed_item_label_v1
from .recording_deletion import (
    DELETION_PAGE,
    RETURN_AREAS,
    RecordingDeletionConflict,
    RecordingDeletionRefused,
    apply_recording_deletion,
    cancel_recording_deletion,
    current_deletion_preview,
    prepare_recording_deletion,
    validate_deletion_preview,
)
from .stateful_localization import translated
from .task_first_rendering import hidden, paragraph
from .translation_catalog import translate_frontend_message_v1


def render_delete_action(item, locale, return_area):
    if item.family not in {"sessions", "matches"} or item.status != "available":
        return ""
    return (f'<form method="post" action="{DELETION_PAGE}/preview" class="delete-recording">'
            + hidden("family", item.family) + hidden("handle", item.handle)
            + hidden("generation", item.discovery_generation) + hidden("return_area", return_area)
            + '<button type="submit" class="secondary">'
            + translated(locale, f"deletion.action.{item.family}") + '</button></form>')


def deletion_notice(app, route, locale):
    with app.lock:
        state = app.recording_deletion
        key = state.outcome if state.outcome_area == route else None
    return (f'<div class="notice" role="status">{paragraph(locale, "deletion." + key)}</div>'
            if key else "")


def render_deletion_page(handler, *, status=200):
    app = handler.server.app_context
    preview = current_deletion_preview(app)
    if preview is not None:
        try:
            validate_deletion_preview(app, preview)
        except RecordingDeletionConflict:
            preview = None
            status = 409
    locale = handler._frontend_state().locale
    with app.lock:
        profile = app.frontend_profile.document
        outcome = app.recording_deletion.outcome
    body = '<section class="panel recording-deletion" id="recording-deletion">'
    if preview is None:
        body += paragraph(locale, "deletion." + (outcome or "missing"))
        body += '<nav aria-label="' + translated(locale, "deletion.return") + '">'
        for area, route in RETURN_AREAS.items():
            body += f'<p><a href="{route}">' + translated(locale, f"navigation.{area}") + '</a></p>'
        body += '</nav>'
    else:
        body += ('<h2>' + managed_item_label_v1(preview.summary, profile=profile, locale=locale)
                 + '</h2>')
        body += '<p><strong>' + translated(locale, f"deletion.family.{preview.family}")
        body += '</strong> · ' + ', '.join(escape(name) if name else translated(
            locale, "deletion.player", number=index)
            for index, name in enumerate(preview.players, 1)) + '<br>'
        if preview.family == "sessions":
            body += translated(locale, "deletion.session_progress", plays=preview.progress[0],
                              phase=translate_frontend_message_v1(
                                  locale, f"task.session.phase.{preview.summary.phase}"))
        else:
            body += translated(locale, "deletion.match_progress", observed=preview.progress[0],
                              passed=preview.progress[1], empty=preview.progress[2])
        body += '</p><p>' + translated(locale, f"deletion.scope.{preview.family}")
        body += ' ' + translated(locale, "deletion.permanent") + '</p>'
        if preview.active is not None:
            body += paragraph(locale, "deletion.active")
        body += paragraph(locale, "deletion.retained") + paragraph(locale, "deletion.download")
        body += (f'<form method="post" action="{DELETION_PAGE}/apply" autocomplete="off">'
                 + hidden("deletion_selection", preview.selection)
                 + '<label><input type="checkbox" name="confirm_delete" value="on" required> '
                 + translated(locale, "deletion.consent") + '</label>'
                 + '<button type="submit">' + translated(locale, f"deletion.apply.{preview.family}")
                 + '</button></form>'
                 + f'<form method="post" action="{DELETION_PAGE}/cancel">'
                 + hidden("deletion_selection", preview.selection)
                 + '<button type="submit" class="secondary">'
                 + translated(locale, "deletion.cancel") + '</button></form>')
    body += '</section>'
    from .language_context import capture_language_source_v1
    handler._rendered_language_source = capture_language_source_v1(app, DELETION_PAGE)
    handler._content_page("/review/recorded", return_to=DELETION_PAGE,
        title=translate_frontend_message_v1(locale, "deletion.title"), content=body, status=status,
        feedback_family="deletion", feedback_identity=current_deletion_preview(app),
        untranslated_workflow_body=False)


def dispatch_recording_deletion(handler, path, values):
    app = handler.server.app_context
    with app.recording_deletion.lock:
        if path.endswith("/preview"):
            location = prepare_recording_deletion(app, values)
        elif path.endswith("/cancel"):
            location = cancel_recording_deletion(app, values)
        else:
            preview = apply_recording_deletion(app, values)
            location = RETURN_AREAS[preview.return_area]
            with app.lock:
                app.recording_deletion.outcome_area = location
            try:
                handler._refresh_category(preview.family)
            except Exception:
                # Unlink already committed. Surface the failure without retry or recreation.
                with app.lock:
                    app.recording_deletion.outcome = "deleted_refresh_warning"
                location = DELETION_PAGE
    handler._redirect(location)


def deletion_error_key(error, status):
    return ("refused" if isinstance(error, RecordingDeletionRefused) else
            "stale" if status == 409 else "invalid")


def render_foreign_deletion_error(handler, key, status):
    """An old/foreign form must not attach feedback or controls to a newer target."""
    locale = handler._frontend_state().locale
    handler._content_page("/review/recorded", return_to="/review/recorded", status=status,
        title=translate_frontend_message_v1(locale, "deletion.title"),
        content=('<section class="panel"><div class="error-summary" role="alert" tabindex="-1">'
                 + paragraph(locale, "validation.deletion." + key) + '</div><p>'
                 + '<a href="/review/recorded">' + translated(locale, "deletion.return")
                 + '</a></p></section>'), untranslated_workflow_body=False)
