# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from skatmind.deck import get_full_deck
from skatmind.rules import get_legal_cards
from skatmind.session_commands import SESSION_COMMAND_KINDS
from skatmind.session_incremental_validation import _has_exact_playable_hand

from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .session_frontend import GuidedSessionContextV1
from .stateful_localization import player_name, text, translated
from .task_first_contracts import TaskFirstSessionV1
from .task_first_projections import project_task_first_session_v1
from .task_first_rendering import (
    boolean_field,
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


def _players(locale, facts):
    return tuple((player.player_id, player_name(locale, facts.players, player.player_id)
                  + " — " + text(locale, f"creation.seat.{player.seat}"))
                 for player in facts.players)


def _choice(locale, name, values, current=None):
    return select_field(locale, name, f"task.field.{name}",
                        tuple((value, text(locale, f"task.value.{value}")) for value in values),
                        current)


def session_command_fields(locale: str, view: TaskFirstSessionV1, kind: str, *, normal=False):
    facts = view.facts
    players = _players(locale, facts)
    player = select_field(locale, "player_id", "task.field.player_id", players,
                          view.entry_player_id)
    if kind == "set_game_metadata":
        identity = hidden("game_id", facts.session_id) if normal else input_field(
            locale, "game_id", "task.field.game_id", "")
        timing = input_field(locale, "played_at", "task.field.played_at")
        return paragraph(locale, "task.session.metadata_help") + (
            identity + disclosure(locale, "task.technical", timing, technical=True) if normal
            else disclosure(locale, "task.technical", identity + timing, technical=True))
    if kind == "record_dealt_card":
        if normal:
            player = hidden("player_id", view.entry_player_id or "") + paragraph(
                locale, "task.session.deal_for", player=(text(locale, "task.skat")
                    if view.deal_destination == "skat" else
                    player_name(locale, facts.players, view.entry_player_id)))
            destination = hidden("destination", view.deal_destination)
        else:
            destination = _choice(locale, "destination", ("player_hand", "skat"))
        used = {card for _, cards in facts.initial_known_hands for card in cards} | set(facts.known_skat)
        return destination + player + card_select(locale, cards=(
            tuple(card for card in get_full_deck() if card not in used) if normal else None))
    if kind == "set_declarer":
        return select_field(locale, "player_id", "task.field.declarer_player_id", players)
    if kind == "set_declaration":
        return (_choice(locale, "game_type", ("clubs", "spades", "hearts", "diamonds", "grand", "null"))
                + boolean_field(locale, "hand_game", "task.field.hand_game")
                + boolean_field(locale, "ouvert", "task.field.ouvert")
                + disclosure(locale, "task.advanced", ''.join(
                    boolean_field(locale, name, f"task.field.{name}")
                    for name in ("schneider_announced", "schwarz_announced"))
                    + input_field(locale, "matadors", "task.field.matadors", kind="number")
                    + input_field(locale, "bid_value", "task.field.bid_value", kind="number")))
    if kind == "record_discard":
        cards = facts.remaining_hand_for(facts.declarer_player_id) if normal else None
        return card_select(locale, cards=cards)
    if kind == "record_play":
        cards = None
        if normal:
            player = hidden("player_id", view.entry_player_id) + paragraph(
                locale, "task.session.play_for",
                player=player_name(locale, facts.players, view.entry_player_id))
            hand = (facts.remaining_hand_for(view.entry_player_id)
                    if _has_exact_playable_hand(facts, view.entry_player_id)
                    else facts.public_hand_for(view.entry_player_id))
            if hand is not None:
                cards = tuple(get_legal_cards(list(hand),
                    [] if facts.incomplete_trick is None else [card for _, card in facts.incomplete_trick.plays],
                    facts.declaration.game_type))
        return player + card_select(locale, cards=cards) + paragraph(locale, "task.session.card_help")
    if kind == "set_public_hand":
        return player + input_field(locale, "cards", "task.field.cards") + paragraph(
            locale, "task.session.public_help")
    if kind == "promote_to_retrospective":
        return paragraph(locale, "task.session.promotion_help")
    if kind == "set_game_end" and normal:
        return hidden("game_end_reason", "normal_completion") + paragraph(
            locale, "task.session.normal_end")
    from .form_registry import get_frontend_form_by_key_v1
    definition = get_frontend_form_by_key_v1(f"session.command.{kind}")
    fields = []
    for field in definition.safe_fields:
        name = field.field_key
        if name == "target_revision":
            continue
        if name.endswith("player_id"):
            fields.append(select_field(locale, name, f"task.field.{name}",
                                       (("", text(locale, "task.unknown")), *players)))
        elif name == "consenting_player_ids":
            from itertools import combinations
            fields.append(select_field(locale, name, f"task.field.{name}",
                ((" ".join(item[0] for item in group), ", ".join(item[1] for item in group)
                  or text(locale, "task.known_empty"))
                 for size in range(4) for group in combinations(players, size))))
        elif field.allowed_values:
            fields.append(_choice(locale, name, field.allowed_values))
        else:
            control = input_field(locale, name, f"task.field.{name}",
                                  "explicit" if name.endswith("_form") else "")
            fields.append(disclosure(locale, "task.technical", control, technical=True)
                if name.endswith("_form") or name in {"consent_status", "statement_classification"}
                else control)
    return paragraph(locale, "task.session.event_help") + ''.join(fields)


def _command(context, locale, view, kind, *, normal=False, correction=False):
    fields = hidden("managed_handle", context.handle) + hidden("expected_revision", context.state.revision)
    fields += hidden("kind", kind)
    if correction:
        fields += paragraph(locale, "task.session.correction_help") + input_field(
            locale, "target_revision", "task.field.target_revision", kind="number", required=True)
    fields += session_command_fields(locale, view, kind, normal=normal)
    return form(locale, "/sessions/command", fields, f"task.command.{kind}", primary=normal)


def _analysis(context, locale, view):
    base = hidden("managed_handle", context.handle) + hidden("expected_revision", context.state.revision)
    position_fields = (
        input_field(locale, "sample_count", "task.field.sample_count", 100, kind="number")
        + input_field(locale, "random_seed", "task.field.random_seed", 0, kind="number")
        + _choice(locale, "opponent_strategy", ("basic", "random"))
        + select_field(locale, "recommendation_method", "task.field.recommendation_method", (
            ("", text(locale, "task.value.automatic")),
            *((value, text(locale, f"task.value.{value}")) for value in
              ("immediate_expected_value", "bounded_search", "auto"))))
        + _choice(locale, "search_budget_profile", ("interactive_v1", "historical_review_v1")))
    historical_fields = ''.join(boolean_field(locale, name, f"task.field.{name}",
                                               name == "immediate_review")
        for name in ("decision_snapshots", "immediate_review", "search_review",
                     "information_set_search_review", "replay_coaching",
                     "information_set_replay_coaching", "historical_tactical_motif_review"))
    historical_fields += ''.join(input_field(locale, name, f"task.field.{name}", default, kind="number")
        for name, default in (("sample_count", 100), ("random_seed", 0), ("search_seed", 0)))
    historical_fields += _choice(locale, "search_budget_profile", ("historical_review_v1", "interactive_v1"))
    controls = paragraph(locale, "task.analysis_help")
    for route, fields, label, available in (
        ("analyze", position_fields, "task.session.analyze", view.position_available),
        ("review", historical_fields, "task.session.review", view.historical_available),
    ):
        if available:
            controls += form(locale, f"/sessions/{route}", base
                + disclosure(locale, "task.advanced", fields), label)
        else:
            controls += paragraph(locale, "task.session.analysis_blocked")
    diagnostics = context.state.validation.diagnostics
    controls += '<ul>' + ''.join('<li>' + translated(locale, "task.session.readiness."
        + ("historical" if item.blocks_historical_export else "position")
        + "." + item.path.strip("/")) + '</li>' for item in diagnostics) + '</ul>'
    if context.execution is not None:
        controls += render_result_presentation_v1(
            build_result_presentation_v1(context.execution.result, locale=locale),
            request_download_available=True, result_download_available=True,
            request_download_route="/sessions/downloads/request.json",
            result_download_route="/sessions/downloads/result.json",
            locale=locale,
        )
    return section(locale, "task.session.analysis", controls)


def render_task_first_session_v1(
    context: GuidedSessionContextV1, *, locale: str = "en", show_operation_notice: bool = True,
) -> str:
    with context.lock:
        view = project_task_first_session_v1(context.state)
        facts = view.facts
        mode = "during" if facts.capture_mode == "live" else "after"
        current = paragraph(locale, f"creation.session.{mode}")
        current += paragraph(locale, f"task.session.phase.{facts.phase}")
        current += paragraph(locale, f"task.session.phase_help.{facts.phase}")
        current += paragraph(locale, "task.session.perspective",
                             player=player_name(locale, facts.players, facts.local_player_id))
        primary = view.workflow.primary_action
        normal = section(locale, "task.session.state", current)
        normal += section(locale, "task.session.next", paragraph(locale, view.workflow.next_task_key))
        normal += section(locale, "task.session.primary", _command(
            context, locale, view, primary, normal=True) if primary else paragraph(
                locale, "task.session.next.complete"))
        entered = '<ul>' + ''.join('<li>' + escape(label) + '</li>' for _, label in _players(locale, facts)) + '</ul>'
        for player in facts.players:
            hand = facts.remaining_hand_for(player.player_id)
            entered += '<p><strong>' + escape(player_name(locale, facts.players, player.player_id))
            entered += '</strong>: ' + cards_summary(locale, hand) + '</p>'
            public = facts.public_hand_for(player.player_id)
            if public is not None:
                entered += paragraph(locale, "task.session.public_hand") + cards_summary(locale, public)
        entered += paragraph(locale, "task.session.declarer",
            player=player_name(locale, facts.players, facts.declarer_player_id))
        if facts.declaration is not None:
            entered += paragraph(locale, f"task.value.{facts.declaration.game_type}")
            entered += '<dl>' + ''.join('<dt>' + translated(locale, f"task.field.{name}")
                + '</dt><dd>' + translated(locale, "common.answer.yes" if getattr(facts.declaration, name)
                    else "common.answer.no") + '</dd>'
                for name in ("hand_game", "ouvert", "schneider_announced", "schwarz_announced")) + '</dl>'
        entered += paragraph(locale, "task.skat") + cards_summary(locale, facts.known_skat or None)
        discards = facts.discarded_cards or (() if facts.declaration and facts.declaration.hand_game else None)
        entered += paragraph(locale, "task.discards") + cards_summary(locale, discards)
        entered += paragraph(locale, "task.session.play_progress", plays=facts.played_card_count,
                             tricks=len(facts.completed_tricks))
        entered += paragraph(locale, "result.current_trick") + cards_summary(locale,
            () if facts.incomplete_trick is None else tuple(card for _, card in facts.incomplete_trick.plays))
        for trick in facts.completed_tricks:
            entered += '<p>' + translated(locale, "guided.trick_number", number=trick.trick_number)
            entered += ': ' + escape(player_name(locale, facts.players, trick.winner_player_id))
            entered += ' — ' + str(trick.trick_points) + '</p>'
        entered += '<ol>' + ''.join('<li>' + escape(player_name(locale, facts.players, player_id))
            + ': ' + cards_summary(locale, (card,)) + '</li>' for player_id, card in facts.plays) + '</ol>'
        if facts.continuation_event is not None:
            entered += paragraph(locale, "task.session.event_recorded")
        if facts.game_end_reason is not None:
            entered += paragraph(locale, f"task.value.{facts.game_end_reason}")
        normal += section(locale, "task.session.entered", entered)
        if show_operation_notice and context.last_operation is not None:
            normal += paragraph(locale, "task.operation." + (
                "conflict" if context.last_operation.status in {"conflict", "stale"} else
                "partial" if context.last_operation.status == "partial" else
                "rejected" if context.last_operation.status in {"rejected", "unavailable"} else "saved"))
        optional = ''.join(disclosure(locale, f"task.command.{kind}",
            _command(context, locale, view, kind)) for kind in view.workflow.secondary_actions)
        normal += disclosure(locale, "task.session.optional", optional)
        normal += _analysis(context, locale, view)
        corrections = paragraph(locale, "task.session.correction_help")
        corrections += ''.join(disclosure(locale, f"task.command.{kind}",
            _command(context, locale, view, kind, correction=True)) for kind in SESSION_COMMAND_KINDS)
        corrections += form(locale, "/sessions/undo", hidden("managed_handle", context.handle)
            + hidden("expected_revision", context.state.revision)
            + input_field(locale, "target_revision", "task.field.target_revision", kind="number", required=True),
            "task.session.undo")
        corrections += form(locale, "/sessions/reload", hidden("managed_handle", context.handle), "common.action.reload")
        normal += disclosure(locale, "task.session.corrections", corrections)
        normal += '<p><a href="/sessions/downloads/session.json" download>' + translated(
            locale, "task.session.download") + '</a></p>'
        normal += technical_details(locale, {
            "session_id": facts.session_id, "game_id": facts.game_id, "played_at": facts.played_at,
            "revision": context.state.revision, "phase": facts.phase,
            "decision_checkpoint_count": len(context.decision_checkpoints),
            "decision_checkpoint_sources": [
                {"source_revision": checkpoint.source_revision,
                 "acting_player_id": checkpoint.acting_player_id}
                for checkpoint in context.decision_checkpoints
            ],
            "last_operation_status": None if context.last_operation is None else context.last_operation.status,
            "last_operation_diagnostics": [] if context.last_operation is None else list(context.last_operation.diagnostics),
            "players": [player.to_dict() for player in facts.players],
            "command_log": [record.to_dict() for record in context.state.command_log],
        })
        return '<div id="session-app">' + normal + '</div>'
