# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from .analysis_download_rendering import analysis_downloads
from .analysis_explanation import explanation_rows
from .candidate_table_rendering import candidate_table_html
from .ordinary_result_numbers import ordinary_scalar
from .recorded_decision_context_rendering import render_recorded_decision_context
from .render_locale import localized_render
from .result_localization import result_label
from .stateful_localization import translated
from .task_first_rendering import cards_summary, paragraph, technical_details


def render_match_reports_v1(state, locale, *, materialization_form="", results=True):
    """Present retained validated report projections, with their actual Game/decision."""
    content = paragraph(locale, "task.match.reports_help") if results else ""
    for report in state["reports"] if results else ():
        if report["match_position"] not in {None, state["selected_position"]}:
            continue
        content += f'<p><a href="/matches/reports/{report["report_id"]}">'
        if report["report_kind"] == "decision_analysis" and report["match_position"] is not None:
            index = report["decision_index"]
            content += (translated(locale, "recordings.match.report", number=report["match_position"])
                if index is None else translated(locale, "recordings.match.report_decision",
                    number=report["match_position"], trick=(index - 1) // 3 + 1, position=(index - 1) % 3 + 1))
        else:
            content += translated(locale, f"task.report.{report['report_kind']}")
            if report["match_position"] is not None:
                content += ' — ' + translated(locale, "task.match.position", number=report["match_position"])
        content += '</a></p>'
    report = state["selected_report"] if results else None
    rollout = state.get("rollout_report") if results else None
    notice = state.get("rollout_notice") if results else None
    if notice is not None and notice.result is not None:
        from .task_first_match_rendering import _named_seat

        attempt = notice.result.document["whole_game_rollout_result"]
        content += paragraph(locale, "recordings.match.game", position=notice.match_position)
        content += paragraph(locale, "recordings.match.decision",
            trick=(notice.decision_index - 1) // 3 + 1,
            player=_named_seat(state, locale, notice.profile_binding.acting_player_id),
            card=notice.request.document["actual_card_played"])
        content += paragraph(locale, "rollout.objective." + attempt["objective"])
        content += paragraph(locale, "rollout.coverage", completed=attempt["completed_common_worlds"],
                             requested=attempt["requested_worlds"])
        content += paragraph(locale, "rollout.reason." + attempt["stop_reason"])
        if rollout is not None and rollout is not notice:
            content += paragraph(locale, "rollout.retained")
    if report is not None and rollout is not None:
        from .result_rendering import render_result_presentation_v1
        from .rollout_result_presentation import build_rollout_presentation

        content += '<div id="match-rollout-result" tabindex="-1">'
        content += state.get("debrief_collection_actions", "")
        content += paragraph(locale, "match_rollout.source")
        presentation = localized_render(build_rollout_presentation)(
            rollout, rollout.result.to_dict()["document"], "match_decision", locale=locale)
        content += render_result_presentation_v1(presentation, locale=locale,
            request_download_available=True, result_download_available=True,
            request_download_route=f'/matches/api/v1/reports/{report["report_id"]}/rollout-request.json',
            result_download_route=f'/matches/api/v1/reports/{report["report_id"]}.json',
            recorded_context=state.get("decision_context"), recorded_context_locale=locale,
            identity_prefix="match-rollout-result")
        if rollout.result.document["whole_game_rollout_result"]["status"] == "complete":
            from .debrief_rendering import link
            from .stateful_localization import text
            from .task_first_rendering import disclosure

            content += disclosure(locale, "debrief.direct_title", link(
                f'/learning/debrief/from/{report["report_id"]}', text(locale, "debrief.open")))
        content += '</div>'
    elif report is not None:
        content += paragraph(locale, f"task.report.{report['report_kind']}")
        if state.get("decision_context") is not None:
            content += render_recorded_decision_context(state["decision_context"], locale)
        details = report["details"]
        status = details.get("status")
        if status in {"complete", "partial", "timeout", "unavailable", "not_assessable", "final"}:
            content += paragraph(locale, f"result.value.{status}")
        if status == "unavailable":
            content += paragraph(locale, "task.match.historical_blocked" if report["report_kind"] == "historical_analysis"
                                 else "task.match.decision_blocked")
        if details.get("actual_card") is not None:
            content += paragraph(locale, "result.actual_card") + cards_summary(locale, (details["actual_card"],))
        recommendation = details.get("recommendation")
        if isinstance(recommendation, dict) and recommendation.get("card") is not None:
            content += paragraph(locale, "task.recommendation") + cards_summary(locale, (recommendation["card"],))
        elif report["report_kind"] == "decision_analysis":
            content += paragraph(locale, "result.no_recommendation")
        explanation = state.get("analysis_explanation")
        if explanation is not None:
            method_rows, evidence_rows = explanation_rows(explanation, locale=locale)
            content += _explanation_details(method_rows, locale)
        candidates = details.get("immediate_candidate_values", [])
        if candidates:
            content += ('<div class="workflow-table-scroll candidate-comparison" role="region" tabindex="0" aria-label="'
                + translated(locale, "result.table.immediate") + '">' + candidate_table_html(
                    caption_html=translated(locale, "result.table.immediate"),
                    columns_html=tuple(translated(locale, key) for key in (
                        "validation.field.card", "result.point_swing", "result.win_rate")),
                    rows_html=tuple((cards_summary(locale, (candidate["card"],)), *(
                        _candidate_value(candidate.get(key), key, locale)
                        for key in ("expected_point_swing", "win_rate")))
                        for candidate in candidates), identity="match-candidates") + '</div>')
        for key, label_key in (("declarer_points", "guided.declarer_points"),
                               ("defender_points", "guided.defender_points")):
            if key in details:
                content += '<p>' + translated(locale, label_key) + ': ' + (
                    translated(locale, "task.unknown") if details[key] is None else escape(str(details[key]))) + '</p>'
        if isinstance(details.get("settlement"), dict):
            score = details["settlement"].get("settlement_score")
            content += '<p>' + translated(locale, "result.settlement") + ': ' + (
                translated(locale, "task.unknown") if score is None else escape(str(score))) + '</p>'
        if explanation is not None:
            content += '<h3>' + translated(locale, "result.evidence") + '</h3>'
            content += _explanation_details(evidence_rows, locale)
        if state["download_availability"]["report_result"]:
            content += analysis_downloads(
                result_href=f'/matches/api/v1/reports/{report["report_id"]}.json',
                report_source_href=(f'/matches/api/v1/reports/{report["report_id"]}/strategy-source.json'
                    if state.get("report_source_available", False) else None), locale=locale)
        content += technical_details(locale, report, caption_key="result.analysis_details")
    if materialization_form:
        content += materialization_form
        for kind, available in state["download_availability"].items():
            if kind != "report_result" and available:
                content += f'<p><a href="/matches/api/v1/exports/{kind.replace("_", "-")}.json" download>' + translated(
                    locale, f"task.download.{kind}") + '</a></p>'
    return content


def _candidate_value(value, key, locale):
    if value is None:
        return translated(locale, "status.unavailable")
    if key == "win_rate" and type(value) in {int, float}:
        return escape(ordinary_scalar(float(value) * 100, ".2f", locale=locale) + "%")
    return escape(ordinary_scalar(value, ".2f" if key == "expected_point_swing" else "", locale=locale))


def _explanation_details(rows, locale):
    return '<dl class="result-details">' + ''.join(
        '<dt>' + escape(localized_render(result_label)(label, locale=locale)) + '</dt><dd>'
        + escape(value) + '</dd>' for label, value in rows) + '</dl>'
