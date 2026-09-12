# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from .form_registry import get_frontend_form_by_key_v1
from .stateful_localization import text, translated
from .task_first_rendering import (
    card_palette,
    card_select,
    cards_summary,
    disclosure,
    form,
    hidden,
    input_field,
    paragraph,
    section,
    select_field,
    technical_details,
)


def _name(state, locale, player_id):
    return next((player["player_label"] or text(locale, "task.player", number=index)
                 for index, player in enumerate(state["participants"], 1)
                 if player["player_id"] == player_id), text(locale, "task.unknown"))


def _named_seat(state, locale, player_id):
    name = _name(state, locale, player_id)
    seat = next((seat for seat in ("forehand", "middlehand", "rearhand")
                 if state["position_view"][f"{seat}_player_id"] == player_id), None)
    return name if seat is None else name + " — " + text(locale, f"creation.seat.{seat}")


def _hidden(state, handle, operation):
    return (hidden("managed_handle", handle) + hidden("operation", operation)
            + hidden("match_position", state["selected_position"])
            + hidden("expected_revision", state["workspace_revision"]))


def _options(state, locale, field, default=None):
    name = field.field_key
    game = state["game"]
    if name in {"declarer_player_id", "commentator_player_id"}:
        return (("", text(locale, "task.unknown")), *(
            (player["player_id"], _named_seat(state, locale, player["player_id"]))
            for player in state["participants"]))
    if name in {"decision_index", "response_decision_index"}:
        return tuple((play["decision_index"], text(locale, "task.match.decision_choice",
            number=play["decision_index"], player=_named_seat(state, locale, play["player_id"]),
            card=play["card"])) for play in (game or {}).get("plays", []))
    if name == "target_play_count":
        return tuple((count, text(locale, "task.match.retain_plays", count=count))
                     for count in range(len((game or {}).get("plays", [])) + 1))
    return tuple((value, text(locale, f"task.value.{value or 'unknown'}"))
                 for value in field.allowed_values)


def operation_form(state, handle, locale, operation, *, values=None, primary=False, extra="", analysis=False, disabled=False):
    values = values or {}
    definition = get_frontend_form_by_key_v1(
        f"match.{'analysis' if analysis else 'operation'}.{operation}")
    fields = _hidden(state, handle, operation) + extra
    technical = ""
    for field in definition.safe_fields:
        name = field.field_key
        key = f"task.field.{name}"
        value = values.get(name, "")
        if name == "cards" and operation in {"set_perspective_hand", "set_original_skat", "set_discarded_cards"}:
            control = card_palette(locale, value)
        elif field.control_type in {"select", "radio"}:
            options = _options(state, locale, field)
            if operation == "analyze_decision" and name == "decision_index":
                prepared = {item["decision_index"] for item in state["decision_preparation"]["decisions"]
                            if item["state"] == "prepared"}
                options = tuple(option for option in options if option[0] in prepared)
            control = select_field(locale, name, key, options, value)
        elif field.control_type == "checkbox":
            control = (f'<label><input type="checkbox" name="{name}"'
                       f'{" checked" if value else ""}{" required" if field.clear_after_rejection else ""}>'
                       f'{translated(locale, key)}</label>')
        elif field.control_type == "textarea":
            control = f'<label>{translated(locale, key)}<textarea name="{name}">{escape(str(value))}</textarea></label>'
        else:
            control = input_field(locale, name, key, value)
        if name in {"game_id", "snapshot_id", "external_match_id", "source_player_id"} or name.endswith("_platform_id"):
            technical += control
        else:
            fields += control
    if technical:
        fields += disclosure(locale, "task.technical", technical, technical=True)
    return form(locale, f"/matches/api/v1/{'analysis' if analysis else 'operation'}", fields,
                f"task.match.action.{operation}", primary=primary, disabled=disabled,
                confirm_key="task.match.remove_note_help" if operation == "remove_commentary" else None)


def _evidence(state, handle, locale):
    game = state["game"]
    if game is None:
        return ""
    content = paragraph(locale, "task.match.evidence_help")
    for operation, name in (("set_perspective_hand", "perspective_initial_hand"),
                            ("set_original_skat", "original_skat"),
                            ("set_discarded_cards", "discarded_cards")):
        cards = game[name]
        mode = "unknown" if cards is None else "known_empty" if not cards else "exact"
        content += section(locale, f"task.match.action.{operation}", cards_summary(locale, cards)
            + operation_form(state, handle, locale, operation,
                             values={"cards": cards, "card_evidence_mode": mode}), level=3)
    return content


def _annotations(state, handle, locale):
    game = state["game"]
    if game is None or not game["plays"]:
        return paragraph(locale, "task.match.annotations_blocked")
    content = paragraph(locale, "task.match.annotations_help")
    content += operation_form(state, handle, locale, "set_commentary")
    for note in game["commentaries"]:
        content += '<article><p>' + escape(note["text"]) + '</p>'
        identity = hidden("commentary_id", note["commentary_id"])
        content += operation_form(state, handle, locale, "set_commentary", values=note, extra=identity)
        content += operation_form(state, handle, locale, "remove_commentary", extra=identity)
        content += paragraph(locale, "task.match.remove_note_help")
        content += operation_form(state, handle, locale, "set_response_link", extra=identity)
        for link in game["response_links"]:
            if link["commentary_id"] == note["commentary_id"]:
                content += operation_form(state, handle, locale, "set_response_link", values=link,
                                           extra=identity + hidden("link_id", link["link_id"]))
                content += operation_form(state, handle, locale, "remove_response_link",
                                           extra=hidden("link_id", link["link_id"]))
        content += '</article>'
    return content


def _statistics(state, handle, locale):
    content = paragraph(locale, "task.match.statistics_help")
    for player in state["participants"]:
        snapshot = player["statistics_snapshot"]
        record = {} if snapshot is None else snapshot["statistics_record"]
        source = record.get("source", {})
        values = {**record.get("statistics", {}), **(record.get("exact_counts") or {}),
                  "games_played": record.get("games_played", ""),
                  "observed_at": source.get("captured_at", ""),
                  "source_type": source.get("source_type", "manual_entry"),
                  "source_name": source.get("source_name", ""), "notes": source.get("notes", "")}
        content += '<article><h3>' + escape(_name(state, locale, player["player_id"])) + '</h3>'
        content += paragraph(locale, "task.statistics.temporal." + player["statistics_temporal_status"])
        content += paragraph(locale, "task.statistics.profile")
        content += operation_form(state, handle, locale, "set_player_statistics_snapshot",
                                   values=values, extra=hidden("player_id", player["player_id"]))
        if snapshot is not None:
            content += operation_form(state, handle, locale, "clear_player_statistics_snapshot",
                                       extra=hidden("player_id", player["player_id"]))
        content += technical_details(locale, {key: player[key] for key in (
            "statistics_snapshot", "normalized_profile", "profile_confidence",
            "profile_classification", "profile_derivation_status", "recommended_policy_preset",
            "actionable_policy_preset", "profile_explanations")}) + '</article>'
    return content


def _reports(state, handle, locale):
    content = paragraph(locale, "task.match.reports_help")
    for report in state["reports"]:
        content += f'<p><a href="/matches/reports/{report["report_id"]}">' + translated(
            locale, f"task.report.{report['report_kind']}") + '</a></p>'
    report = state["selected_report"]
    if report is not None:
        content += paragraph(locale, f"task.report.{report['report_kind']}")
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
    content += operation_form(state, handle, locale, "prepare_materialization", analysis=True)
    for kind, available in state["download_availability"].items():
        if kind != "report_result" and available:
            content += f'<p><a href="/matches/api/v1/exports/{kind.replace("_", "-")}.json" download>' + translated(
                locale, f"task.download.{kind}") + '</a></p>'
    return content


def render_task_first_match_v1(state, view, *, managed_handle: str, locale="en", transfer="", recovery=None):
    handle = managed_handle
    progress = state["progress"]
    body = section(locale, "task.match.progress", paragraph(locale, "task.match.progress_value",
        occupied=progress["occupied_slot_count"], passed=progress["passed_deal_count"]))
    next_content = paragraph(locale, "task.match.all_complete") if view.next_position is None else (
        f'<p><a href="/matches/position/{view.next_position}">' + translated(
            locale, "task.match.position", number=view.next_position) + '</a></p>')
    body += section(locale, "task.match.next", next_content)
    positions = ''
    for round_number in range(1, 13):
        positions += '<section><h3>' + translated(locale, "task.match.round", number=round_number) + '</h3><div class="round-slots">'
        for position in view.positions[(round_number - 1) * 3:round_number * 3]:
            selected = position.match_position == view.selected_position
            following = position.match_position == view.next_position
            positions += (f'<a class="match-tile{" selected" if selected else ""}" '
                f'href="/matches/position/{position.match_position}" data-status="{position.game_state}"'
                f'{" aria-current=\"page\"" if selected else ""}>'
                + '<strong class="match-tile-title">'
                + translated(locale, "task.match.position", number=position.match_position)
                + '</strong><span class="match-tile-status">'
                + translated(locale, f"task.match.status.{position.game_state}") + '</span>'
                + '<span class="match-tile-markers">')
            if selected:
                positions += '<span>' + translated(locale, "task.selected") + '</span>'
            if following:
                positions += '<span>' + translated(locale, "task.next") + '</span>'
            positions += '</span><span class="match-tile-participants">'
            for seat in ("forehand", "middlehand", "rearhand"):
                positions += '<span><b>' + translated(locale, f"creation.seat.{seat}") + ':</b> ' + escape(
                    _name(state, locale, getattr(position, f"{seat}_player_id"))) + '</span>'
            positions += '</span><span>' + translated(locale, "task.match.plays", count=position.play_count) + '</span></a>'
        positions += '</div></section>'
    body += section(locale, "task.match.overview", positions)
    game = state["game"]
    task = '<div id="match-recovery-feedback"></div>' + ("" if recovery is None else recovery[0]) + paragraph(locale, view.workflow.next_task_key)
    if view.workflow.primary_action == "start_game":
        task += form(locale, "/matches/api/v1/operation", _hidden(state, handle, "start_game"),
                     "task.match.action.start_game", primary=True)
        task += form(locale, "/matches/api/v1/operation", _hidden(state, handle, "mark_passed_deal"),
                     "task.match.action.mark_passed_deal")
    elif view.workflow.primary_action == "set_declaration":
        task += operation_form(state, handle, locale, "set_declaration", primary=True)
    elif view.workflow.primary_action == "append_plays":
        task += paragraph(locale, "task.match.scope." + view.selected.card_selection_scope)
        task += paragraph(locale, "task.session.play_for", player=_named_seat(state, locale, view.selected.next_player_id))
        task += form(locale, "/matches/api/v1/operation", _hidden(state, handle, "append_plays")
                     + card_select(locale, "cards", cards=view.selected.selectable_cards),
                     "task.match.action.append_plays", primary=True)
    if game is not None:
        task += '<ul>' + ''.join('<li>' + translated(locale, f"task.match.action.{step}") + ' — '
            + translated(locale, "task.recorded") + '</li>' for step in view.workflow.completed_steps) + '</ul>'
        task += (recovery[1] if recovery is not None else '<ol>' + ''.join('<li>' + escape(_name(state, locale, play["player_id"])) + ': '
            + cards_summary(locale, (play["card"],)) + '</li>' for play in game["plays"]) + '</ol>')
    body += '<div id="match-recording" tabindex="-1">' + section(locale, "task.match.record_or_pass", task) + '</div>'
    body += transfer
    body += disclosure(locale, "task.match.evidence", '<div id="match-evidence">' + _evidence(state, handle, locale) + '</div>')
    body += disclosure(locale, "task.match.annotations", _annotations(state, handle, locale))
    metadata = {**state["match"], **state["source"],
        "match_timecode_start": state["source"]["match_timecode"]["start"],
        "match_timecode_end": state["source"]["match_timecode"]["end"]}
    for index, player in enumerate(state["participants"], 1):
        metadata[f"player_{index}_label"] = player["player_label"]
        metadata[f"player_{index}_platform_id"] = player["platform_player_id"]
    body += disclosure(locale, "task.match.metadata", paragraph(locale, "task.match.metadata_help")
        + operation_form(state, handle, locale, "update_match_metadata", values=metadata))
    body += disclosure(locale, "task.match.statistics", _statistics(state, handle, locale))
    analysis = paragraph(locale, "task.analysis_help")
    if game is not None:
        decision_ready = state["decision_preparation"]["prepared_decision_count"] > 0
        evidence = view.selected.evidence_summary
        historical_ready = (evidence is not None and evidence.complete_initial_deal_reconstructable
                            and state["match"]["played_at"] is not None)
        if not decision_ready:
            analysis += paragraph(locale, "task.match.decision_blocked")
        if not historical_ready:
            analysis += paragraph(locale, "task.match.historical_blocked")
        analysis += operation_form(state, handle, locale, "analyze_decision", analysis=True, disabled=not decision_ready, values={
            "immediate_sample_count": 100, "immediate_random_seed": 0, "search_random_seed": 0,
            "search_budget_profile": "historical_review_v1", "recommendation_method": "immediate_expected_value", "use_profile_presets": True})
        analysis += operation_form(state, handle, locale, "analyze_historical_game", analysis=True, disabled=not historical_ready, values={
            "immediate_sample_count": 100, "immediate_random_seed": 0, "search_random_seed": 0,
            "search_budget_profile": "historical_review_v1", "immediate_review": True, "use_profile_presets": True})
    body += disclosure(locale, "task.match.analysis", analysis + _reports(state, handle, locale))
    corrections = paragraph(locale, "task.match.correction_help")
    if view.selected.slot_kind == "empty":
        corrections += operation_form(state, handle, locale, "start_game")
        corrections += operation_form(state, handle, locale, "mark_passed_deal")
    if game is not None:
        corrections += '<div id="match-declaration">' + operation_form(state, handle, locale, "set_declaration", values={
            **(game["declaration"] or {}), "declarer_player_id": game["declarer_player_id"]}) + '</div>'
        corrections += operation_form(state, handle, locale, "set_game_timecode", values={
            "game_timecode_start": game["game_timecode"]["start"], "game_timecode_end": game["game_timecode"]["end"]})
        corrections += operation_form(state, handle, locale, "append_plays")
        corrections += operation_form(state, handle, locale, "truncate_plays")
        corrections += operation_form(state, handle, locale, "mark_passed_deal", extra=(
            '<label><input type="checkbox" name="confirm_replace" required>'
            + translated(locale, "task.field.confirm_replace") + '</label>'))
    corrections += operation_form(state, handle, locale, "clear_position")
    corrections += form(locale, "/matches/api/v1/reload", hidden("managed_handle", handle)
                        + hidden("match_position", view.selected_position), "common.action.reload")
    body += disclosure(locale, "task.match.corrections", corrections)
    body += '<p><a href="/matches/downloads/workspace.json" download>' + translated(locale, "task.match.download") + '</a></p>'
    body += technical_details(locale, {"match_id": state["match"]["match_id"],
        "workspace_revision": state["workspace_revision"], "position_view": state["position_view"]})
    return '<div id="task-first-match">' + body + '</div>'
