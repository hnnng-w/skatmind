# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from skatmind.deck import get_full_deck
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.session_commands import SESSION_COMMAND_KINDS

from .card_entry_http import session_card_binding
from .compact_card_rendering import compact_card_selector
from .compact_declaration_http import declaration_binding
from .compact_declaration_rendering import (
    accepted_declaration_summary,
    compact_declaration_fields,
)
from .local_time_http import local_time_context
from .local_time_rendering import render_local_time_editor
from .recorded_trick_progress import project_session_trick_progress
from .recorded_trick_rendering import (
    render_current_trick,
    render_recorded_history,
    render_recorded_summary,
)
from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .session_card_entry import project_session_card_task
from .session_frontend import GuidedSessionContextV1
from .session_recorded_review_rendering import (
    render_recorded_review_source_v1,
    render_recorded_session_decisions_v1,
)
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
from .unplayed_card_rendering import render_unplayed_cards
from .unplayed_card_summary import project_unplayed_cards


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
        return compact_declaration_fields(locale, session=True)
    if kind == "record_discard":
        cards = facts.remaining_hand_for(facts.declarer_player_id) if normal else None
        return card_select(locale, cards=cards)
    if kind == "record_play":
        return player + card_select(locale) + paragraph(locale, "task.session.card_help")
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


def _metadata_command(context, locale, view, app, *, normal=False, record=None):
    if record is None and not normal and view.facts.played_at is not None:
        return paragraph(locale, "local_time.correction_help") + '<p><a href="#session-history">' + translated(
            locale, "task.session.corrections") + '</a></p>'
    marker = "session-metadata" if record is None else "session-metadata-correction"
    target = "" if record is None else str(record.revision)
    original = view.facts.played_at if record is None else record.command.played_at
    game_id = ((view.facts.session_id if view.facts.game_id is None else None)
               if record is None else record.command.game_id)
    fields = hidden("managed_handle", context.handle) + hidden("expected_revision", context.state.revision)
    fields += hidden("kind", "set_game_metadata")
    if record is not None:
        fields += hidden("target_revision", target) + paragraph(locale, "local_time.correction", revision=target)
    fields += (hidden("game_id", game_id) if normal else disclosure(locale, "task.technical",
        input_field(locale, "game_id", "task.field.game_id", game_id), technical=True))
    fields += paragraph(locale, "task.session.metadata_help") + render_local_time_editor(locale,
        local_time_context(app, context, marker, target), original=original,
        new=record is None and original is None)
    return form(locale, "/sessions/command", fields, "task.command.set_game_metadata", primary=normal)


def _command(context, locale, view, kind, *, normal=False, correction=False, progress=None, app=None):
    if kind == "set_game_metadata":
        if correction:
            return ''.join(_metadata_command(context, locale, view, app, record=record)
                for record in context.state.command_log if record.command.kind == kind)
        return _metadata_command(context, locale, view, app, normal=normal)
    if normal and kind in {"record_dealt_card", "record_discard", "record_play"}:
        task = project_session_card_task(context.state, view=view)
        facts = view.facts
        play = kind == "record_play"
        fields = hidden("managed_handle", context.handle) + hidden(
            "card_selection", session_card_binding(context, task))
        player = dict(_players(locale, facts)).get(task.player_id, text(locale, "task.skat"))
        fields += paragraph(locale, "task.session.play_for" if play else "compact.for",
                            player=player)
        if kind == "record_dealt_card" and facts.phase in {"setup", "deal"}:
            if facts.capture_mode == "live":
                fields += paragraph(locale, "session.knowledge.local_hand", player=player)
            else:
                fields += paragraph(locale, "session.knowledge.all_hands",
                    players=", ".join(label for _, label in _players(locale, facts)))
        if play:
            fields += paragraph(locale, "recovery.trick", number=len(facts.completed_tricks) + 1)
            fields += render_current_trick(progress, locale)
            fields += paragraph(locale, "task.match.scope." + task.scope)
        else:
            fields += paragraph(locale, "compact.append") + paragraph(locale, "compact.accepted")
            fields += '<p>' + cards_summary(locale, task.accepted_cards) + '</p>'
        fields += compact_card_selector(locale, mode="play" if play else "set",
            cards=task.selectable_cards, capacity=task.capacity,
            game_type=None if facts.declaration is None else facts.declaration.game_type)
        return form(locale, "/sessions/play" if play else "/sessions/cards", fields,
                    "compact.record" if play else "compact.save", primary=True)
    fields = hidden("managed_handle", context.handle) + hidden("expected_revision", context.state.revision)
    fields += hidden("kind", kind)
    if kind == "set_declaration":
        marker = "session-correction" if correction else "session-declaration"
        target = ""
        values = None
        declarer = view.facts.declarer_player_id
        if correction:
            record = next((record for record in context.state.command_log
                           if record.command.kind == kind), None)
            if record is None:
                return ""
            target = str(record.revision)
            values = build_serializable_game_declaration(record.command.declaration)
            declarer = next((item.command.declarer_player_id for item in context.state.command_log
                if item.revision < record.revision and item.command.kind == "set_declarer"), None)
            fields += hidden("target_revision", target) + paragraph(
                locale, "declaration.correction", revision=target)
        fields += hidden("declaration_form", marker) + hidden(
            "declaration_selection", declaration_binding(context, marker, target))
        fields += paragraph(locale, "task.session.declarer",
            player=player_name(locale, view.facts.players, declarer))
        fields += compact_declaration_fields(locale, values, session=True)
        return form(locale, "/sessions/command", fields, "declaration.save", primary=normal)
    if correction:
        fields += paragraph(locale, "task.session.correction_help") + input_field(
            locale, "target_revision", "task.field.target_revision", kind="number", required=True)
    fields += session_command_fields(locale, view, kind, normal=normal)
    return form(locale, "/sessions/command", fields, f"task.command.{kind}", primary=normal)


def _analysis(context, locale, view, game_label):
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
            controls += paragraph(locale, f"recorded_review.{route}_unavailable")
    diagnostics = context.state.validation.diagnostics
    controls += '<ul>' + ''.join('<li>' + translated(locale, "task.session.readiness."
        + ("historical" if item.blocks_historical_export else "position")
        + "." + item.path.strip("/")) + '</li>' for item in diagnostics) + '</ul>'
    if context.execution is not None:
        controls += '<div id="session-result" tabindex="-1">'
        controls += render_recorded_review_source_v1(context, locale=locale, game_label=game_label)
        controls += render_result_presentation_v1(
            build_result_presentation_v1(context.execution.result, locale=locale),
            request_download_available=True, result_download_available=True,
            request_download_route="/sessions/downloads/request.json",
            result_download_route="/sessions/downloads/result.json",
            locale=locale,
        )
        controls += '</div>'
    return section(locale, "task.session.analysis", controls)


def render_task_first_session_v1(
    context: GuidedSessionContextV1, *, locale: str = "en", show_operation_notice: bool = True,
    game_label: str | None = None,
    app_context=None,
) -> str:
    with context.lock:
        view = project_task_first_session_v1(context.state)
        facts = view.facts
        progress = project_session_trick_progress(facts)
        unplayed = project_unplayed_cards(progress, facts.declaration)
        mode = "perspective" if facts.capture_mode == "live" else "reconstruction"
        current = paragraph(locale, "session.knowledge.accepted_mode",
                            mode=text(locale, f"session.knowledge.{mode}"))
        current += paragraph(locale, f"task.session.phase.{facts.phase}")
        current += paragraph(locale, f"task.session.phase_help.{facts.phase}")
        current += paragraph(locale, "task.session.perspective",
                             player=player_name(locale, facts.players, facts.local_player_id))
        current += '<p><a href="#recorded-decisions">' + translated(
            locale, "recorded_review.title") + '</a></p>'
        primary = view.workflow.primary_action
        normal = section(locale, "task.session.state", current)
        normal += section(locale, "task.session.next", paragraph(locale, view.workflow.next_task_key))
        controls = (_command(context, locale, view, primary, normal=True, progress=progress, app=app_context)
                    if primary else paragraph(locale, "task.session.next.complete"))
        normal += '<div id="session-recording" tabindex="-1"><div id="session-card-feedback"></div>' + section(
            locale, "declaration.title" if primary == "set_declaration" else "task.session.primary", '<div class="recording-progress-layout"><div>'
            + controls + '</div>' + render_recorded_summary(progress, locale) + '</div>') + '</div>'
        if facts.declaration is not None:
            normal += accepted_declaration_summary(locale,
                build_serializable_game_declaration(facts.declaration),
                player_name(locale, facts.players, facts.declarer_player_id))
        normal += render_unplayed_cards(unplayed, locale,
            original_skat=facts.known_skat or None, discarded_cards=facts.discarded_cards or None)
        normal += render_recorded_session_decisions_v1(context, locale=locale)
        normal += render_recorded_history(progress, locale)
        entered = '<ul>' + ''.join('<li>' + escape(label) + '</li>' for _, label in _players(locale, facts)) + '</ul>'
        for player in facts.players:
            hand = facts.remaining_hand_for(player.player_id)
            entered += '<p><strong>' + escape(player_name(locale, facts.players, player.player_id))
            entered += '</strong>: ' + cards_summary(locale, hand) + '</p>'
            public = facts.public_hand_for(player.player_id)
            if public is not None:
                entered += paragraph(locale, "task.session.public_hand") + cards_summary(locale, public)
        if facts.declaration is None:
            entered += paragraph(locale, "task.session.declarer",
                player=player_name(locale, facts.players, facts.declarer_player_id))
        if unplayed is None:
            entered += paragraph(locale, "task.skat") + cards_summary(locale, facts.known_skat or None)
            discards = facts.discarded_cards or (() if facts.declaration and facts.declaration.hand_game else None)
            entered += paragraph(locale, "task.discards") + cards_summary(locale, discards)
        entered += paragraph(locale, "task.session.play_progress", plays=facts.played_card_count,
                             tricks=len(facts.completed_tricks))
        if facts.continuation_event is not None:
            entered += paragraph(locale, "task.session.event_recorded")
        if facts.game_end_reason is not None:
            entered += paragraph(locale, f"task.value.{facts.game_end_reason}")
        normal += section(locale, "task.session.entered", entered)
        if (show_operation_notice and context.last_operation is not None
                and context.recorded_review_source is None):
            normal += paragraph(locale, "task.operation." + (
                "conflict" if context.last_operation.status in {"conflict", "stale"} else
                "partial" if context.last_operation.status == "partial" else
                "rejected" if context.last_operation.status in {"rejected", "unavailable"} else "saved"))
        optional = ''.join(disclosure(locale, "task.session.metadata_title" if kind == "set_game_metadata" else f"task.command.{kind}",
            _command(context, locale, view, kind, app=app_context)) for kind in view.workflow.secondary_actions)
        normal += disclosure(locale, "task.session.optional", optional)
        normal += _analysis(context, locale, view, game_label or text(locale, "page.session_current.title"))
        corrections = paragraph(locale, "task.session.correction_help")
        corrections += ''.join(disclosure(locale, f"task.command.{kind}",
            _command(context, locale, view, kind, correction=True, app=app_context)) for kind in SESSION_COMMAND_KINDS)
        corrections += form(locale, "/sessions/undo", hidden("managed_handle", context.handle)
            + hidden("expected_revision", context.state.revision)
            + input_field(locale, "target_revision", "task.field.target_revision", kind="number", required=True),
            "task.session.undo")
        corrections += form(locale, "/sessions/reload", hidden("managed_handle", context.handle), "common.action.reload")
        normal += '<div id="session-history">' + disclosure(
            locale, "task.session.corrections", corrections) + '</div>'
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
