# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from .compact_card_rendering import compact_card_selector
from .compact_declaration_rendering import accepted_declaration_summary, compact_declaration_fields
from .form_registry import get_frontend_form_by_key_v1
from .friendly_creation_rendering import render_fixed_match_format_v1
from .local_time_rendering import render_local_time_editor
from .match_report_rendering import render_match_reports_v1
from .recorded_trick_rendering import (
    render_current_trick,
    render_recorded_history,
    render_recorded_summary,
)
from .stateful_localization import text, translated
from .task_first_rendering import (
    card_palette,
    card_set_summary,
    disclosure,
    form,
    hidden,
    input_field,
    paragraph,
    section,
    select_field,
    technical_details,
)
from .unplayed_card_rendering import render_unplayed_cards


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
    if operation == "set_declaration":
        fields = _hidden(state, handle, operation) + hidden("declaration_form", "match-declaration")
        fields += hidden("declaration_selection", state.get("declaration_bindings", {}).get("match-declaration", ""))
        fields += select_field(locale, "declarer_player_id", "task.field.declarer_player_id",
            (("", text(locale, "declaration.choose_declarer")), *(
                (player["player_id"], _named_seat(state, locale, player["player_id"]))
                for player in state["participants"])), values.get("declarer_player_id"), required=True)
        fields += compact_declaration_fields(locale, values)
        return form(locale, "/matches/api/v1/operation", fields, "declaration.save", primary=primary)
    definition = get_frontend_form_by_key_v1(
        f"match.{'analysis' if analysis else 'operation'}.{operation}")
    fields = _hidden(state, handle, operation) + extra
    if analysis and state.get("review_binding"):
        fields += hidden("review_binding", state["review_binding"])
    technical = ""
    advanced = ""
    for field in definition.safe_fields:
        name = field.field_key
        if operation == "update_match_metadata" and name == "played_at" and state.get("local_time_context"):
            fields += render_local_time_editor(locale, state["local_time_context"],
                original=values.get("played_at"), new=False)
            continue
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
                options = tuple((row["decision_index"], text(locale, "recordings.match.decision",
                    trick=(row["decision_index"] - 1) // 3 + 1,
                    player=_named_seat(state, locale, row["acting_player_id"]), card=row["actual_card"]))
                    for row in state["decision_preparation"]["decisions"] if row["state"] == "prepared")
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
        elif analysis and operation == "analyze_decision" and name != "decision_index":
            advanced += control
        else:
            fields += control
    if advanced:
        fields += disclosure(locale, "recordings.match.advanced", paragraph(locale, "task.analysis_help") + advanced)
    if technical:
        fields += disclosure(locale, "task.technical", technical, technical=True)
    return form(locale, f"/matches/api/v1/{'analysis' if analysis else 'operation'}", fields,
                f"task.match.action.{operation}", primary=primary, disabled=disabled,
                confirm_key="task.match.remove_note_help" if operation == "remove_commentary" else None)


def _card_form(state, handle, locale, operation, binding, *, cards=(), mode="exact", play=False):
    fields = hidden("managed_handle", handle) + hidden("operation", operation)
    fields += hidden("card_selection", binding)
    if not play:
        modes = ("unknown", "known_empty", "exact") if operation == "set_discarded_cards" else ("unknown", "exact")
        fields += select_field(locale, "card_evidence_mode", "task.field.card_evidence_mode",
            tuple((value, text(locale, f"task.value.{value}")) for value in modes), mode)
        fields += paragraph(locale, "compact.replace")
    game = state["game"]
    fields += compact_card_selector(locale, mode="play" if play else "set",
        cards=cards if play else None, selected=() if play else cards,
        game_type=None if not game or game["declaration"] is None else game["declaration"]["game_type"],
        capacity=1 if play else 10 if operation == "set_perspective_hand" else 2)
    return form(locale, "/matches/cards", fields, "compact.record" if play else "compact.save",
                primary=play)


def _evidence(state, handle, locale, bindings, *, hand=False):
    game = state["game"]
    if game is None:
        return ""
    content = paragraph(locale, "task.match.evidence_help")
    for operation, name in (("set_perspective_hand", "perspective_initial_hand"),
                             ("set_original_skat", "original_skat"),
                             ("set_discarded_cards", "discarded_cards")):
        if (operation == "set_perspective_hand") != hand:
            continue
        cards = game[name]
        mode = "unknown" if cards is None else "known_empty" if not cards else "exact"
        content += section(locale, f"task.match.action.{operation}", card_set_summary(locale, cards)
            + _card_form(state, handle, locale, operation, bindings.get(operation, ""),
                         cards=cards, mode=mode), level=3)
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


def _reports(state, handle, locale, *, secondary=True, results=True):
    return render_match_reports_v1(state, locale, results=results, materialization_form=(
        operation_form(state, handle, locale, "prepare_materialization", analysis=True)
        if secondary else ""))


def _game_overview(state, view, locale):
    positions = ''
    for round_number in range(1, 13):
        positions += '<section><h3>' + translated(locale, "task.match.round", number=round_number) + '</h3><div class="round-slots">'
        for position in view.positions[(round_number - 1) * 3:round_number * 3]:
            selected = position.match_position == view.selected_position
            following = position.match_position == view.next_position
            positions += (f'<a class="match-tile{" selected" if selected else ""}" '
                f'href="/matches/position/{position.match_position}#match-recording" data-status="{position.game_state}"'
                f'{" aria-current=\"page\"" if selected else ""}>'
                + '<strong class="match-tile-title">'
                + translated(locale, "task.match.position", number=position.match_position)
                + '</strong><span class="match-tile-status">'
                + translated(locale, f"task.match.status.{position.game_state}") + '</span>'
                + '<span class="match-tile-markers">')
            if selected:
                positions += '<span>' + translated(locale, "task.match.selected") + '</span>'
            if following:
                positions += '<span>' + translated(locale, "task.match.next") + '</span>'
            positions += '</span><span class="match-tile-participants">'
            for seat in ("forehand", "middlehand", "rearhand"):
                positions += '<span><b>' + translated(locale, f"creation.seat.{seat}") + ':</b> ' + escape(
                    _name(state, locale, getattr(position, f"{seat}_player_id"))) + '</span>'
            positions += '</span><span>' + translated(locale, "task.match.plays", count=position.play_count) + '</span></a>'
        positions += '</div></section>'
    return ('<section id="match-games" class="panel" tabindex="-1" aria-labelledby="match-games-heading">'
        + '<h2 id="match-games-heading">' + translated(locale, "task.match.overview") + '</h2>'
        + paragraph(locale, "task.match.navigation_help")
        + '<p><a href="#match-recording">' + translated(locale, "task.match.selected") + '</a></p>'
        + positions + '</section>')


def render_task_first_match_v1(state, view, *, managed_handle: str, locale="en", transfer="", recovery=None, card_bindings=None):
    card_bindings = card_bindings or {}
    handle = managed_handle
    progress = state["progress"]
    body = '<p><strong>' + translated(locale, "task.match.progress") + ':</strong> ' + translated(
        locale, "task.match.progress_value", observed=progress["observed_game_count"],
        complete=progress["complete_play_trace_count"], passed=progress["passed_deal_count"]) + '</p>'
    game = state["game"]
    task = '<!-- operation-feedback --><h2 id="match-recording-heading">' + translated(
        locale, "task.match.game_heading", number=view.selected_position) + '</h2>'
    task += paragraph(locale, "task.match.round", number=view.selected.round_number)
    task += '<dl class="match-game-seats">' + ''.join('<div><dt>' + translated(
        locale, f"creation.seat.{seat}") + '</dt><dd>' + escape(_name(
            state, locale, getattr(view.selected, f"{seat}_player_id"))) + '</dd></div>'
        for seat in ("forehand", "middlehand", "rearhand")) + '</dl>'
    task += '<div id="match-recovery-feedback"></div>' + ("" if recovery is None else recovery[0])
    recorded = state.get("recorded_progress")
    task += '<div class="recording-progress-layout"><div>'
    if view.workflow.primary_action == "start_game":
        task += '<h3>' + translated(locale, "task.match.action.start_game") + '</h3>'
        task += form(locale, "/matches/api/v1/operation", _hidden(state, handle, "start_game"),
                     "task.match.action.start_game", primary=True)
        task += form(locale, "/matches/api/v1/operation", _hidden(state, handle, "mark_passed_deal"),
                     "task.match.action.mark_passed_deal")
    elif view.workflow.primary_action == "set_declaration":
        task += '<div id="match-declaration"><h3>' + translated(locale, "declaration.title") + '</h3>'
        task += operation_form(state, handle, locale, "set_declaration", primary=True)
        task += '</div>'
    elif view.workflow.primary_action == "append_plays":
        task += '<h3>' + translated(locale, "task.record_next_card",
            player=_named_seat(state, locale, view.selected.next_player_id)) + '</h3>'
        task += paragraph(locale, "task.match.scope." + view.selected.card_selection_scope)
        task += paragraph(locale, "recovery.trick", number=view.selected.completed_trick_count + 1)
        if recorded is not None:
            task += render_current_trick(recorded, locale)
        task += _card_form(state, handle, locale, "append_plays", card_bindings.get("append_plays", ""),
                           cards=view.selected.selectable_cards, play=True)
    else:
        task += paragraph(locale, view.workflow.next_task_key)
    task += '</div>' + ("" if recorded is None else render_recorded_summary(recorded, locale)) + '</div>'
    if view.next_position is None:
        task += paragraph(locale, "task.match.all_complete")
    elif view.next_position != view.selected_position:
        task += f'<p><a href="/matches/position/{view.next_position}#match-recording">' + translated(
            locale, "task.match.first_unfinished", number=view.next_position) + '</a></p>'
    task += '<p><a href="#match-games">' + translated(locale, "task.match.overview") + '</a>'
    if view.selected.play_count:
        ready = state["decision_preparation"]["prepared_decision_count"] > 0
        task += ' · <a href="/matches/review/' + str(view.selected_position) + '">' + translated(
            locale, "recordings.match.open" if ready else "recordings.match.inspect") + '</a>'
    task += '</p>'
    if game is not None:
        task += accepted_declaration_summary(locale, game["declaration"],
                                             _named_seat(state, locale, game["declarer_player_id"]))
        task += render_unplayed_cards(state.get("unplayed_cards"), locale,
            original_skat=game["original_skat"], discarded_cards=game["discarded_cards"])
        task += disclosure(locale, "compact.optional_hand", _evidence(
            state, handle, locale, card_bindings, hand=True))
    if game is not None:
        task += (recovery[1] if recovery is not None else "" if recorded is None
                 else render_recorded_history(recorded, locale))
    body += '<section id="match-recording" class="panel" tabindex="-1" aria-labelledby="match-recording-heading">' + task + '</section>'
    body += _game_overview(state, view, locale)
    body += transfer
    body += disclosure(locale, "task.match.evidence", '<div id="match-evidence">' + _evidence(state, handle, locale, card_bindings) + '</div>')
    body += disclosure(locale, "task.match.annotations", _annotations(state, handle, locale))
    metadata = {**state["match"], **state["source"],
        "match_timecode_start": state["source"]["match_timecode"]["start"],
        "match_timecode_end": state["source"]["match_timecode"]["end"]}
    for index, player in enumerate(state["participants"], 1):
        metadata[f"player_{index}_label"] = player["player_label"]
        metadata[f"player_{index}_platform_id"] = player["platform_player_id"]
    body += '<div id="match-metadata" tabindex="-1"><!-- metadata-operation-feedback -->' + disclosure(locale, "task.match.metadata", render_fixed_match_format_v1(locale) + paragraph(locale, "task.match.metadata_help")
        + operation_form(state, handle, locale, "update_match_metadata", values=metadata)) + '</div>'
    body += disclosure(locale, "task.match.statistics", _statistics(state, handle, locale))
    from .match_review_rendering import render_match_analysis_v1
    analysis = render_match_analysis_v1(state, view, handle, locale)
    body += disclosure(locale, "task.match.analysis", analysis + _reports(state, handle, locale))
    corrections = paragraph(locale, "task.match.correction_help")
    if view.selected.slot_kind == "empty":
        corrections += operation_form(state, handle, locale, "start_game")
        corrections += operation_form(state, handle, locale, "mark_passed_deal")
    if game is not None:
        if game["declaration"] is not None:
            corrections += '<div id="match-declaration"><h3>' + translated(locale, "declaration.title") + '</h3>'
            corrections += operation_form(state, handle, locale, "set_declaration", values={
                **game["declaration"], "declarer_player_id": game["declarer_player_id"]}) + '</div>'
            corrections += disclosure(locale, "declaration.clear", form(locale,
                "/matches/api/v1/operation", _hidden(state, handle, "set_declaration")
                + hidden("declaration_form", "match-clear")
                + hidden("declaration_selection", state.get("declaration_bindings", {}).get("match-clear", ""))
                + '<label><input type="checkbox" name="confirm_clear" required>'
                + translated(locale, "declaration.confirm_clear") + '</label>', "declaration.clear"))
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
