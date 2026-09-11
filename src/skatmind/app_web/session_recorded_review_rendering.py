from __future__ import annotations

from html import escape

from .session_frontend import GuidedSessionContextV1
from .session_recorded_review import RecordedDecisionV1, project_recorded_session_decisions_v1
from .stateful_localization import player_name, translated
from .task_first_rendering import hidden, paragraph


def _decision_label(locale: str, context: GuidedSessionContextV1, row: RecordedDecisionV1) -> str:
    checkpoint = row.checkpoint
    return translated(
        locale, "recorded_review.decision",
        player=player_name(locale, context.state.players, checkpoint.acting_player_id),
        trick=checkpoint.trick_number, position=checkpoint.play_index,
        card=row.observation.actual_card,
    )


def render_recorded_session_decisions_v1(context: GuidedSessionContextV1, *, locale: str) -> str:
    view = project_recorded_session_decisions_v1(context)
    content = paragraph(locale, "recorded_review.coverage", available=len(view.decisions),
                        recorded=view.local_play_count)
    if context.state.local_player_id is None:
        content += paragraph(locale, "recorded_review.no_perspective")
    if not context.decision_checkpoints:
        content += paragraph(locale, "recorded_review.no_snapshots")
    elif view.missing_snapshot_count:
        content += paragraph(locale, "recorded_review.missing", count=view.missing_snapshot_count)
    content += '<ul class="recorded-decisions">'
    for row in view.decisions:
        index = row.checkpoint.decision_index
        label_id = f"recorded-decision-{index}"
        content += (
            '<li><form method="post" action="/sessions/review-decision">'
            + hidden("managed_handle", context.handle)
            + hidden("expected_revision", context.state.revision)
            + hidden("decision_selection", row.selection)
            + f'<p id="{label_id}">{_decision_label(locale, context, row)}</p>'
            + f'<button type="submit" class="secondary" aria-describedby="{label_id}">'
            + translated(locale, "recorded_review.action") + '</button></form></li>'
        )
    content += '</ul>'
    for status, count in view.unavailable_counts:
        if count:
            content += paragraph(locale, f"recorded_review.{status}", count=count)
    if any(count for _, count in view.unavailable_counts) or view.missing_snapshot_count:
        content += '<p><a href="#session-history">' + translated(
            locale, "recorded_review.history") + '</a></p>'
    return (
        '<section id="recorded-decisions" class="panel" aria-labelledby="recorded-review-title">'
        '<h2 id="recorded-review-title">' + translated(locale, "recorded_review.title")
        + '</h2><div id="recorded-review-feedback"></div>' + content + '</section>'
    )


def render_recorded_review_source_v1(
    context: GuidedSessionContextV1, *, locale: str, game_label: str,
) -> str:
    source = context.recorded_review_source
    if source is None:
        return ""
    return (
        '<p class="recorded-review-source"><strong>'
        + translated(locale, "recorded_review.result", game=game_label) + '</strong><br>'
        + _decision_label(locale, context, source.decision) + '</p>'
        + paragraph(locale, "recorded_review.limit")
        + '<p><a href="#recorded-decision-'
        + escape(str(source.decision.checkpoint.decision_index)) + '">'
        + translated(locale, "recorded_review.back") + '</a></p>'
    )
