from __future__ import annotations

from .friendly_creation_rendering import managed_item_label_v1
from .recorded_review_opening import OPEN_RECORDING_ROUTE, RECORDING_FAMILIES
from .recording_deletion_http import render_delete_action
from .stateful_localization import managed_name, text, translated
from .task_first_rendering import hidden, paragraph, select_field


def recording_scopes(handler, path):
    from html import escape

    from .language_context import capture_language_source_v1, validate_language_source_v1
    from .session_batch_routes import DECISIONS
    from .session_batch_routes import PAGE as SESSION_GAME
    from .whole_match_routes import SCOPES, WHOLE_SETUP

    app, locale = handler.server.app_context, handler._frontend_state().locale
    source = capture_language_source_v1(app, path)
    def guard():
        validate_language_source_v1(app, source, check_files=True)

    def choice(url, key):
        return f'<li><a class="button-link" href="{url}">{translated(locale, key)}</a></li>'

    profile = app.frontend_profile.document
    if path == SCOPES:
        active = handler._active_match()
        definition = active.workspace.match_definition
        title = managed_name(locale, profile, "matches", definition.match_id, definition.title)
        position = active.selected_position
        choices = choice(WHOLE_SETUP, "whole_review.title")
        choices += f'<li><form method="get" action="{SCOPES}">' + select_field(locale,
            "position", "recordings.match.select", [(n, text(locale, "accounting.game_number",
            number=n)) for n in range(1, 37)], position)
        choices += '<button type="submit">' + translated(locale, "batch.scope_game")
        choices += '</button></form></li>'
        choices += choice(f"/matches/review/{position}", "match_nav.single")
    else:
        from .cent_sources import member_label
        active = handler._active_session()
        title = managed_name(locale, profile, "sessions", active.state.session_id)
        title = member_label(app, active, locale) or title
        choices = choice(SESSION_GAME, "batch.session") + choice(DECISIONS, "match_nav.single")
    handler._rendered_language_source = source
    handler._retained_delivery_guard = guard
    handler._content_page("/matches" if path == SCOPES else "/sessions", return_to=path,
        title=text(locale, "batch.scope"), content='<p>' + escape(title)
        + '</p><ul class="workflow-list" id="analysis-scopes">' + choices + '</ul>',
        analysis=True, task_first=True, untranslated_workflow_body=False)


def render_recorded_review_chooser_v1(discoveries, *, profile, locale, active_sources=(),
                                      memberships=None):
    """Render strict discovery classifications, never decision eligibility or Requests."""
    body = '<div id="recorded-review-chooser">' + paragraph(locale, "recordings.introduction")
    body += paragraph(locale, "batch.scope_help")
    body += paragraph(locale, "recordings.lifetime")
    body += '<p class="entry-actions"><a class="button-link secondary" href="/analyze">'
    body += translated(locale, "entry.decision.heading") + '</a> '
    body += '<a class="button-link secondary" href="/review">'
    body += translated(locale, "recordings.manual") + '</a></p>'
    body += paragraph(locale, "recordings.manual_help")
    body += '<p class="entry-actions"><a class="button-link secondary" href="/learning">'
    body += translated(locale, "navigation.learning") + '</a></p>'
    for family in RECORDING_FAMILIES:
        view = discoveries[family].view
        body += '<section><h2>' + translated(locale, f"recordings.{family}") + '</h2>'
        if view.candidate_limit_reached:
            body += paragraph(locale, "creation.managed.limit")
        if not view.items:
            body += paragraph(locale, "recordings.empty")
        for item in view.items:
            label = managed_item_label_v1(item, profile=profile, locale=locale)
            body += '<article class="recording-choice"><h3>' + label + '</h3>'
            body += paragraph(locale, f"creation.managed.status.{item.status}")
            member = (memberships or {}).get(item.handle) if family == "sessions" else None
            if member:
                label = (translated(locale, "cent.member", title=member[0], number=member[1])
                         if member[2] else translated(locale, "cent.source"))
                body += f'<p>{label}</p>'
            if item.status == "available" and (not member or member[2]):
                body += (f'<form method="post" action="{OPEN_RECORDING_ROUTE}">'
                         + hidden("family", family) + hidden("handle", item.handle)
                          + hidden("generation", view.generation)
                          + (hidden("bound_selection", member[2]) if member else "")
                         + '<button type="submit">' + translated(locale, "recordings.open")
                          + '</button></form>')
            if item.status == "available":
                body += render_delete_action(item, locale, "review")
            body += '</article>'
        body += (f'<p class="entry-actions"><a class="button-link secondary" href="/{family}">'
                 + translated(locale, f"navigation.{family}") + '</a></p></section>')
    if any(item.status != "available" for discovery in discoveries.values()
           for item in discovery.view.items):
        body += '<p><a href="/about">' + translated(locale, "recordings.storage_help") + '</a></p>'
    # Existing explicit Reload is the only replacement path for changed active files.
    for family, handle, position in active_sources:
        route = "/sessions/reload" if family == "sessions" else "/matches/api/v1/reload"
        body += '<details class="secondary-action"><summary>' + translated(
            locale, f"recordings.reload.{family}") + '</summary>'
        body += paragraph(locale, "recordings.reload_help")
        body += f'<form method="post" action="{route}">' + hidden("managed_handle", handle)
        if family == "matches":
            body += hidden("match_position", position)
        body += '<button type="submit">' + translated(locale, "common.action.reload")
        body += '</button></form></details>'
    return body + '</div>'
