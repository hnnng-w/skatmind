from __future__ import annotations

from html import escape

from skatmind.rollout_derivation import missing_rollout_settlement_inputs

from .session_frontend import GuidedSessionContextV1
from .session_recorded_review import (
    RecordedDecisionV1,
    RecordedReviewProjectionV1,
    project_recorded_session_decisions_v1,
)
from .session_recorded_review_form import recorded_rollout_notice_feedback_v1
from .stateful_localization import player_name, translated
from .task_first_rendering import disclosure, hidden, paragraph, select_field


def _decision_label(locale: str, players, row: RecordedDecisionV1) -> str:
    checkpoint = row.checkpoint
    return translated(
        locale, "recorded_review.decision",
        player=player_name(locale, players, checkpoint.acting_player_id),
        trick=checkpoint.trick_number, position=checkpoint.play_index,
        card=row.observation.actual_card,
    )


def render_recorded_session_decisions_v1(
    context: GuidedSessionContextV1, *, locale: str,
    view: RecordedReviewProjectionV1 | None = None,
) -> str:
    view = project_recorded_session_decisions_v1(context) if view is None else view
    content = ""
    if context.state.local_player_id is None:
        content += paragraph(locale, "recorded_review.no_perspective")
    elif not view.local_play_count:
        content += paragraph(locale, "recorded_review.no_observations")
    else:
        content += paragraph(locale, "recorded_review.coverage", available=len(view.decisions),
                             recorded=view.local_play_count)
    if view.local_play_count and not context.decision_checkpoints:
        content += paragraph(locale, "recorded_review.no_snapshots")
    elif view.missing_snapshot_count:
        content += paragraph(locale, "recorded_review.missing", count=view.missing_snapshot_count)
    content += '<ul class="recorded-decisions">' if view.decisions else ""
    for row in view.decisions:
        index = row.checkpoint.decision_index
        label_id = f"recorded-decision-{index}"
        fields = (hidden("managed_handle", context.handle)
                  + hidden("expected_revision", context.state.revision)
                  + hidden("decision_selection", row.selection))
        settings = {"objective": "played_game_goal", "requested_worlds": 100, "random_seed": 0}
        if (context.rollout_review_source is not None
                and context.rollout_review_source.decision.selection == row.selection):
            settings = context.rollout_execution.request.document["whole_game_rollout_settings"]
        advanced = select_field(locale, "objective", "rollout.objective", (
            (value, translated(locale, f"rollout.objective.{value}"))
            for value in ("played_game_goal", "complete_settlement")), settings["objective"])
        advanced += paragraph(locale, "rollout.objective_help")
        missing = missing_rollout_settlement_inputs(row.checkpoint.request.to_dict()["document"])
        if missing:
            supplied = {}
            if (context.rollout_review_source is not None
                    and context.rollout_review_source.decision.selection == row.selection):
                supplied = context.rollout_execution.request.document.get(
                    "whole_game_rollout_derivation", {}).get("supplements", {})
            advanced += '<fieldset class="rollout-settlement-inputs"><legend>' + translated(
                locale, "rollout.supplement_heading") + '</legend>'
            for name in missing:
                advanced += ('<label>' + translated(locale, "rollout.analysis_" + name)
                    + ' <input type="text" inputmode="numeric" maxlength="21" '
                    + f'name="analysis_{name}" value="{escape(str(supplied.get(name, "")))}">'
                    + '</label>')
            advanced += paragraph(locale, "rollout.supplement_help")
            if "matadors" in missing:
                advanced += paragraph(locale, "declaration.count_examples")
            advanced += '</fieldset>'
        for name, key, maximum in (("requested_worlds", "rollout.worlds", 1000),
                                   ("random_seed", "rollout.seed", 2**64 - 1)):
            advanced += (f'<label>{translated(locale, key)} <input type="number" '
                         f'name="{name}" min="{1 if name == "requested_worlds" else 0}" '
                         f'max="{maximum}" step="1" required value="{settings[name]}"></label>')
        method = row.checkpoint.request.document.get(
            "recommendation_method", "immediate_expected_value")
        content += (
            '<li>'
            + f'<p id="{label_id}">{_decision_label(locale, context.state.players, row)}</p>'
            + '<form method="post" action="/sessions/review-whole-game">' + fields
            + disclosure(locale, "task.advanced", advanced)
            + f'<button type="submit" class="primary" aria-describedby="{label_id}">'
            + translated(locale, "rollout.action") + '</button></form>'
            + '<form method="post" action="/sessions/review-decision">' + fields
            + f'<button type="submit" class="secondary" aria-describedby="{label_id}">'
            + translated(locale, "rollout.legacy_action", method=translated(
                locale, f"task.value.{method}"))
            + '</button></form></li>'
        )
    content += '</ul>' if view.decisions else ""
    for status, count in view.unavailable_counts:
        if count:
            content += paragraph(locale, f"recorded_review.{status}", count=count)
    if any(count for _, count in view.unavailable_counts) or view.missing_snapshot_count:
        content += '<p><a href="#session-history">' + translated(
            locale, "recorded_review.history") + '</a></p>'
    if not view.local_play_count:
        return ('<section id="recorded-decisions" tabindex="-1" aria-label="'
                + translated(locale, "recorded_review.title")
                + '"><div id="recorded-review-feedback"></div>' + content + '</section>')
    return ('<section id="recorded-decisions" class="panel" tabindex="-1" '
            'aria-labelledby="recorded-review-title"><h2 id="recorded-review-title">'
            + translated(locale, "recorded_review.title" if view.decisions
                         else "recorded_review.inspect")
            + '</h2><div id="recorded-review-feedback"></div>' + content + '</section>')


def render_recorded_review_source_v1(
    context: GuidedSessionContextV1, *, locale: str, game_label: str,
    rollout: bool = False,
) -> str:
    source = context.rollout_review_source if rollout else context.recorded_review_source
    if source is None:
        return ""
    return (
        '<p class="recorded-review-source"><strong>'
        + translated(locale, "recorded_review.result", game=game_label) + '</strong><br>'
        + _decision_label(locale, source.document.state.players, source.decision) + '</p>'
        + ("" if rollout else paragraph(locale, "recorded_review.limit"))
        + '<p><a href="#recorded-decision-'
        + escape(str(source.decision.checkpoint.decision_index)) + '">'
        + translated(locale, "recorded_review.back", trick=source.decision.checkpoint.trick_number,
                     position=source.decision.checkpoint.play_index) + '</a></p>'
    )


def render_rollout_notice_v1(context: GuidedSessionContextV1, *, locale: str) -> str:
    notice = context.rollout_notice
    if notice is None:
        return ""
    feedback = recorded_rollout_notice_feedback_v1(notice)
    return (paragraph(locale, feedback.message_key)
            + '<p>' + _decision_label(locale, notice.source.document.state.players,
                                     notice.source.decision) + '</p>'
            + paragraph(locale, "rollout.objective." + notice.settings.objective)
            + paragraph(locale, "rollout.coverage", completed=notice.completed_worlds,
                        requested=notice.settings.requested_worlds)
            + ("" if notice.missing_inputs else paragraph(
                locale, "rollout.reason." + notice.reason)))
