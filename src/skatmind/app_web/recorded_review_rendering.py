from __future__ import annotations

from .friendly_creation_rendering import managed_item_label_v1
from .recorded_review_opening import OPEN_RECORDING_ROUTE, RECORDING_FAMILIES
from .recording_deletion_http import render_delete_action
from .stateful_localization import translated
from .task_first_rendering import hidden, paragraph


def render_recorded_review_chooser_v1(discoveries, *, profile, locale, active_sources=()):
    """Render strict discovery classifications, never decision eligibility or Requests."""
    body = '<div id="recorded-review-chooser">' + paragraph(locale, "recordings.introduction")
    body += paragraph(locale, "recordings.lifetime")
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
            if item.status == "available":
                body += (f'<form method="post" action="{OPEN_RECORDING_ROUTE}">'
                         + hidden("family", family) + hidden("handle", item.handle)
                         + hidden("generation", view.generation)
                         + '<button type="submit">' + translated(locale, "recordings.open")
                          + '</button></form>')
                body += render_delete_action(item, locale, "review")
            body += '</article>'
        body += f'<p><a href="/{family}">' + translated(
            locale, f"navigation.{family}") + '</a></p></section>'
    body += '<p><a href="/review">' + translated(locale, "recordings.manual") + '</a></p>'
    body += paragraph(locale, "recordings.manual_help")
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
