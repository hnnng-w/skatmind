# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from .stateful_localization import text, translated
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
        row = next((row for row in state["decision_preparation"]["decisions"]
                    if row["decision_index"] == report["decision_index"]), None)
        if row is not None:
            player = next((player["player_label"] or text(locale, "task.unknown")
                           for player in state["participants"]
                           if player["player_id"] == row["acting_player_id"]), text(locale, "task.unknown"))
            content += paragraph(locale, "recordings.match.decision", player=player,
                trick=(row["decision_index"] - 1) // 3 + 1, card=row["actual_card"])
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
            content += ('<div class="workflow-table-scroll" role="region" tabindex="0" aria-label="'
                + translated(locale, "result.table.immediate") + '"><table><caption>'
                + translated(locale, "result.table.immediate") + '</caption><thead><tr>')
            content += ''.join('<th scope="col">' + translated(locale, key) + '</th>'
                               for key in ("validation.field.card", "result.point_swing", "result.win_rate")) + '</tr></thead><tbody>'
            for candidate in candidates:
                content += '<tr><th scope="row">' + cards_summary(locale, (candidate["card"],)) + '</th>'
                content += ''.join('<td>' + (translated(locale, "status.unavailable") if candidate.get(key) is None
                    else escape(str(candidate[key]))) + '</td>' for key in ("expected_point_swing", "win_rate")) + '</tr>'
            content += '</tbody></table></div>'
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
