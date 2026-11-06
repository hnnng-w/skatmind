"""Native Session evidence presentation, isolated from Match qualification."""

from html import escape

from .recorded_decision_context import project_recorded_decision_context, source_player_labels
from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .stateful_localization import card_name, text
from .task_first_rendering import disclosure, form, hidden, paragraph


def source_caption(source, locale):
    name = source.document.state.session_id
    if len(name) > 32:
        name = source.record.source_version.source.identity[:12]
    return text(locale, "session_learning.source", name=name,
                revision=source.document.state.revision)


def evidence_caption(value, locale):
    checkpoint = value.checkpoint
    state = value.source.document.state
    player = next(p.player_label or p.player_id for p in state.players
                  if p.player_id == checkpoint.acting_player_id)
    method = value.execution.request.document.get(
        "recommendation_method", "immediate_expected_value")
    return text(locale, "session_learning.comparison", source=source_caption(value.source, locale),
        player=player, decision=checkpoint.decision_index,
        card=card_name(locale, value.observation.actual_card),
        method=text(locale, "saved_analysis.method." + method))


def render_session_evidence(value, route, locale):
    execution, checkpoint = value.execution, value.checkpoint
    players = source_player_labels(value.source.document.state.players,
                                    checkpoint.relative_player_map)
    context = project_recorded_decision_context(execution.result.result.document,
        players=players, trick_number=checkpoint.trick_number, play_index=checkpoint.play_index)
    body = '<section id="saved-analysis" tabindex="-1"><h2>' + escape(
        evidence_caption(value, locale)) + '</h2>'
    body += paragraph(locale, "saved_analysis.historical")
    body += render_result_presentation_v1(build_result_presentation_v1(execution.result,
        locale=locale, information_source="session_checkpoint"),
        request_download_available=True, result_download_available=True,
        request_download_route=route + "/request.json",
        result_download_route=route + "/result.json",
        recorded_context=context, recorded_context_locale=locale, locale=locale)
    body += disclosure(locale, "task.technical", '<p>' + escape(
        value.source.record.source_version.content_fingerprint) + '</p><p>'
        + escape(value.entry.identity) + '</p>', technical=True)
    return body + '</section>'


def session_links(locale):
    return ('<p><a class="button-link secondary" href="/sessions/saved-analyses">'
            + escape(text(locale, "session_learning.saved")) + '</a></p>')


def session_receipt(active, locale):
    notice = active.evidence_notice
    body = session_links(locale)
    if notice is None:
        return body
    source, status, _evidence_id = notice
    if source.attempt is not active.execution_attempt:
        return body
    body += '<div role="status">' + paragraph(locale, "session_learning." + (
        "saved_notice" if status == "saved" else status)) + '</div>'
    pending = active.pending_evidence
    if pending is not None and pending.source is source:
        body += form(locale, "/sessions/retry-saving", hidden("managed_handle", active.handle)
                     + hidden("save_token", pending.token), "saved_analysis.retry")
    return body


def render_session_coverage(source, locale):
    coverage = source.coverage
    body = paragraph(locale, "session_learning.coverage", recorded=coverage.recorded_plays,
        own=coverage.own_plays, eligible=len(coverage.decisions))
    if not coverage.has_perspective:
        body += paragraph(locale, "session_learning.no_perspective")
    if coverage.missing_checkpoints:
        body += paragraph(locale, "session_learning.missing", count=coverage.missing_checkpoints)
    for status, count in coverage.unavailable:
        if count:
            body += paragraph(locale, "recorded_review." + status, count=count)
    return body
