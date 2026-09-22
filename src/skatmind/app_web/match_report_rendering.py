# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from .candidate_table_rendering import candidate_table_html
from .recorded_decision_context_rendering import render_recorded_decision_context
from .stateful_localization import translated
from .task_first_rendering import cards_summary, paragraph, technical_details


def render_match_reports_v1(state, locale, *, materialization_form="", results=True):
    """Present retained validated report projections, with their actual Game/decision."""
    content = paragraph(locale, "task.match.reports_help") if results else ""
    for report in state["reports"] if results else ():
        if report["match_position"] not in {None, state["selected_position"]}:
            continue
        content += f'<p><a href="/matches/reports/{report["report_id"]}">' + translated(
            locale, f"task.report.{report['report_kind']}")
        if report["match_position"] is not None:
            content += ' — ' + translated(locale, "task.match.position", number=report["match_position"])
        content += '</a></p>'
    report = state["selected_report"] if results else None
    if report is not None:
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
        candidates = details.get("immediate_candidate_values", [])
        if candidates:
            content += ('<div class="workflow-table-scroll candidate-comparison" role="region" tabindex="0" aria-label="'
                + translated(locale, "result.table.immediate") + '">' + candidate_table_html(
                    caption_html=translated(locale, "result.table.immediate"),
                    columns_html=tuple(translated(locale, key) for key in (
                        "validation.field.card", "result.point_swing", "result.win_rate")),
                    rows_html=tuple((cards_summary(locale, (candidate["card"],)), *(
                        translated(locale, "status.unavailable") if candidate.get(key) is None
                        else escape(str(candidate[key])) for key in ("expected_point_swing", "win_rate")))
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
        content += technical_details(locale, report)
        if state["download_availability"]["report_result"]:
            content += f'<p><a href="/matches/api/v1/reports/{report["report_id"]}.json" download>' + translated(
                locale, "task.result_download") + '</a></p>'
    if materialization_form:
        content += materialization_form
        for kind, available in state["download_availability"].items():
            if kind != "report_result" and available:
                content += f'<p><a href="/matches/api/v1/exports/{kind.replace("_", "-")}.json" download>' + translated(
                    locale, f"task.download.{kind}") + '</a></p>'
    return content
