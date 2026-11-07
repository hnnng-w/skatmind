"""Saved Historical per-game findings remain separate from recurring Match focuses."""

from html import escape

from skatmind.api.v1 import ExecutionArtifactV1, ExecutionResultV1

from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .stateful_localization import text
from .task_first_rendering import disclosure, form, hidden, paragraph


def historical_caption(value, locale):
    game = value.game
    people = " / ".join(player.player_label or player.player_id for player in game.players)
    name = text(locale, "task.value." + game.declaration.game_type)
    if value.report is not None:
        definition = value.source.document.workspace.match_definition
        name = (definition.title or definition.match_id) + " · " + str(value.report.match_position)
    return text(locale, "historical_learning.caption", name=name, people=people,
                revision=value.source.record.revision)


def render_historical_evidence(value, route, locale):
    internal = value.internal_execution
    public = (value.execution.result if value.execution is not None else ExecutionResultV1(
        result=internal.result, artifacts=tuple(ExecutionArtifactV1(
            name=row.name, document=row.to_dict()) for row in internal.artifacts)))
    body = '<section id="saved-analysis" tabindex="-1"><h2>' + escape(
        historical_caption(value, locale)) + '</h2>'
    body += paragraph(locale, "historical_learning.separate")
    body += render_result_presentation_v1(build_result_presentation_v1(public, locale=locale),
        request_download_available=True, result_download_available=True,
        request_download_route=route + "/request.json",
        result_download_route=route + "/result.json",
        locale=locale)
    body += disclosure(locale, "task.technical", '<p>' + escape(
        value.source.record.source_version.content_fingerprint) + '</p><p>'
        + escape(value.entry.identity) + '</p><p>' + escape(value.game.game_id)
        + '</p>', technical=True)
    return body + '</section>'


def historical_links(locale):
    return ('<p><a class="button-link secondary" href="/review/saved">'
            + escape(text(locale, "historical_learning.saved")) + '</a></p>')


def historical_source_controls(value, view, locale):
    if view.binding.result.status != "current":
        return paragraph(locale, "automatic.recording_changed")
    if value.report is not None:
        from .automatic_learning_rendering import situations
        index = next((i for i, (source_index, _snapshot, ref) in enumerate(
            situations(view.binding.installed.bundle))
            if view.binding.installed.bundle.sources[source_index][0] == value.source.record
            and ref.match_position == value.report.match_position), None)
        if index is not None:
            return form(locale, "/learning/automatic/recording", hidden("view", view.token)
                        + hidden("situation", index), "historical_learning.open_source")
    else:
        index = next((i for i, head in enumerate(view.binding.resumed.manifest.historical_heads)
                      if head.source_version_id == value.entry.source_version_id), None)
        if index is not None:
            return form(locale, "/review/reopen", hidden("view", view.token)
                        + hidden("source", index), "historical_learning.reopen")
    return paragraph(locale, "automatic.recording_changed")


def render_historical_review(view, locale):
    bundle = view.binding.installed.bundle
    body = historical_links(locale)
    if not hasattr(bundle, "historical_sources"):
        return body
    body += '<h3>' + escape(text(locale, "historical_learning.title")) + '</h3>'
    body += paragraph(locale, "historical_learning.separate")
    body += '<dl>' + ''.join('<dt>' + escape(text(locale, "historical_learning.count." + row.name))
        + '</dt><dd>' + escape(row.value) + '</dd>' for row in bundle.historical_coverage) + '</dl>'
    body += '<ul>' + ''.join('<li><a href="' + view.base + '/historical/evidence/' + str(i)
        + '">' + escape(historical_caption(value, locale)) + '</a></li>'
        for i, value in enumerate(bundle.historical_evidence)) + '</ul>'
    return body


def manual_receipt(app, locale):
    owner, state = app.historical_reviews, app.review_state
    notice = owner.notice
    if notice is None or notice[0] is not state:
        return ""
    body = '<aside role="status">' + paragraph(locale, "historical_learning." + (
        "saved_notice" if notice[1] == "saved" else notice[1]))
    if owner.pending is not None and owner.pending.state is state:
        body += form(locale, "/review/retry-saving", hidden("save_token", owner.pending.token),
                     "saved_analysis.retry")
    return body + '</aside>'
