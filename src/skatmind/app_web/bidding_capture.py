"""Native recording controls over the verified Session log or rotated Match slot."""

from __future__ import annotations

import hmac
import re

from skatmind.bidding import BID_VALUES, BidAction, BiddingContinuationConflict, replay_bidding
from skatmind.match_bidding import edit_match_bidding
from skatmind.match_source_coordination import match_source_coordinator
from skatmind.session_commands import RecordSessionBidCommandV2
from skatmind.session_history import correct_session_command_v1
from skatmind.session_history_contracts import SessionCommandCorrectionV1

from .card_entry_http import CardEntryConflict, _fresh
from .compact_declaration_http import DeclarationConflict, declaration_binding
from .session_frontend import apply_guided_session_edit_v1
from .stateful_localization import text, translated
from .task_first_rendering import disclosure, form, hidden, paragraph, select_field
from .whole_match_progress import file_identity


def bidding_binding(active, session):
    marker = "session-bidding" if session else "match-bidding"
    return declaration_binding(active, marker, active.saved_file_identity)


def render_bidding(locale, *, seats, names, events, route, fields):
    def editor(index, turn, original=None):
        choices = []
        for action in turn.actions:
            if action == "bid":
                choices.extend((str(v), text(locale, "bidding.bid") + f" {v}")
                               for v in BID_VALUES if v > (turn.value or 0))
            else:
                choices.append((action, text(locale, "bidding." + action)
                                + (f" {turn.value}" if action == "hold" else "")))
        selected = None if original is None else (
            str(original.value) if original.action == "bid" else original.action)
        controls = (fields + hidden("bidding_form", "auction") + hidden("index", index)
                    + hidden("player_id", turn.actor) + select_field(locale, "choice",
                    "bidding.action", choices, selected, required=True))
        if original is not None:
            controls += ('<label><input type="checkbox" name="confirm_suffix" value="yes">'
                         + translated(locale, "bidding.suffix") + '</label>')
        return form(locale, route, controls, "bidding.save" if original is None else "bidding.edit",
                    primary=original is None)

    turn = replay_bidding(seats, events)
    body = f'<section id="bidding" tabindex="-1"><h2>{translated(locale, "bidding.title")}</h2>'
    if events:
        body += '<ol>'
        for i, event in enumerate(events):
            label = translated(locale, "bidding.entry", player=names[event.player_id],
                action=text(locale, "bidding." + event.action),
                value="" if event.value is None else str(event.value))
            body += '<li>' + label + disclosure(locale, "bidding.edit",
                editor(i, replay_bidding(seats, events[:i]), event)) + '</li>'
        body += '</ol>'
    if turn.actor is not None:
        body += paragraph(locale, "bidding.next", player=names[turn.actor],
                          value=turn.value or text(locale, "bidding.none"))
        body += editor(len(events), turn)
    elif turn.declarer is None:
        body += paragraph(locale, "task.value.passed_deal")
    else:
        body += paragraph(locale, "bidding.unbid" if turn.value is None else "bidding.winner",
                          player=names[turn.declarer], value=turn.effective_value)
    return body + '</section>'


def save_bidding(active, values, *, session):
    """Caller holds the family lifecycle and source locks, as for declaration capture."""
    active.require_attached()
    expected = {"bidding_form", "managed_handle", "expected_revision", "bidding_binding",
                "index", "player_id", "choice"}
    if not session:
        expected.add("match_position")
    if ((set(values) - {"confirm_suffix"}) != expected or values["bidding_form"] != "auction"
            or any(type(v) is not str for v in values.values())
            or values.get("confirm_suffix", "yes") != "yes"):
        raise ValueError("Invalid bidding form.")
    revision = active.state.revision if session else active.workspace.revision
    if (values["managed_handle"] != active.handle or values["expected_revision"] != str(revision)
            or (not session and values["match_position"] != str(active.selected_position))
            or not re.fullmatch("[0-9a-f]{64}", values["bidding_binding"])
            or not hmac.compare_digest(values["bidding_binding"],
                                       bidding_binding(active, session))):
        raise DeclarationConflict()
    try:
        _fresh(active, session=session)
        if active.saved_file_identity != file_identity(active.path):
            raise DeclarationConflict()
    except (OSError, CardEntryConflict) as error:
        raise DeclarationConflict("file_changed") from error
    if session:
        records = [r for r in active.state.command_log if r.command.kind == "record_bid"]
        events = tuple(r.command.observation for r in records)
        seats = tuple(player.player_id for player in active.state.players)
    else:
        slot = active.workspace.slots[active.selected_position - 1]
        game = slot.observed_game or slot.passed_game
        if game is None:
            raise ValueError("Start the game before recording bidding.")
        seats = tuple(player.player_id for player in game.players)
        events = slot.bidding
    if not re.fullmatch(r"0|[1-9][0-9]{0,2}", values["index"]):
        raise ValueError("Invalid bidding selection.")
    index = int(values["index"])
    correction = index < len(events)
    if index > len(events) or ("confirm_suffix" in values and not correction):
        raise ValueError("Invalid correction target.")
    turn = replay_bidding(seats, events[:index])
    choice = values["choice"]
    if re.fullmatch(r"[1-9][0-9]{1,2}", choice):
        event = BidAction(values["player_id"], "bid", int(choice))
    else:
        event = BidAction(values["player_id"], choice, turn.value if choice == "hold" else None)
    confirmed = "confirm_suffix" in values
    if session:
        command = RecordSessionBidCommandV2(expected_revision=(
            records[index].revision - 1 if correction else revision), observation=event)
        if correction:
            command = SessionCommandCorrectionV1(expected_revision=revision,
                target_revision=records[index].revision, replacement_command=command)
            if not confirmed:
                preview = correct_session_command_v1(active.state, command)
                if preview.discarded_suffix_records:
                    raise BiddingContinuationConflict(len(preview.discarded_suffix_records))
        result = apply_guided_session_edit_v1(active, command)
        if result.status in {"conflict", "stale"}:
            raise DeclarationConflict()
        if result.status == "rejected":
            raise ValueError("Bidding action rejected.")
        return "/sessions/current#bidding"
    change = edit_match_bidding(active.workspace, active.selected_position, index, event,
                                expected_revision=revision, confirm_suffix=confirmed)
    if change.status == "applied":
        with match_source_coordinator(active.category_root).lock:
            if active.saved_file_identity != file_identity(active.path):
                raise DeclarationConflict()
            if active.capture.save_candidate(change.workspace) == "conflict":
                raise DeclarationConflict()
            active.saved_file_identity = file_identity(active.path)
        active.capture.report_store.clear()
        active.live.invalidate()
        active.recovery.clear()
        active.transfer_notice = None
        active.operation_feedback.begin()
    return f"/matches/position/{active.selected_position}#bidding"
