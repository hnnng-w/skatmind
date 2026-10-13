"""Disposable saved decisions with a legal synthetic suffix and optional original inputs."""

from dataclasses import replace
from functools import lru_cache

from test_historical_game import build_historical_input
from test_session_transitions import _apply, _play_commands_from_data, _retrospective_before_play

import skatmind.api.v1.session as session_api
from skatmind.app_web.session_frontend import (
    default_session_position_export_options_v1,
    import_guided_session_v1,
)
from skatmind.deck import get_full_deck
from skatmind.rules import get_legal_cards, get_trick_winner
from skatmind.session_commands import RecordSessionPlayCommandV1
from skatmind.session_history import build_session_state_from_accepted_prefix_v1


def saved_opening(*, complete=False, reverse_hidden=False, actual="CJ",
                  decision_trick=1, bid_value=None, matadors=None):
    assert decision_trick in (1, 2)
    clubs = [card for card in get_full_deck() if card.startswith("C")]
    rest = [card for card in get_full_deck() if card not in [*clubs, "H7", "D7", "SA", "S10"]]
    if reverse_hidden:
        rest.reverse()
    data = build_historical_input(
        game_type="clubs", declarer_player_id="player-a", bid_value=bid_value,
        deck=["H7", "D7", *clubs, *rest, "SA", "S10"])
    data["declaration"]["matadors"] = matadors
    state = _retrospective_before_play(data, local_player_id="player-a")
    if decision_trick == 2:
        cards = []
        for player, hand in zip(("player-a", "player-b", "player-c"),
                                ([*clubs, "SA", "S10"], rest[:10], rest[10:]), strict=True):
            card = "CJ" if not cards else get_legal_cards(hand, cards, "clubs")[0]
            state = _apply(state, RecordSessionPlayCommandV1(
                expected_revision=state.revision, player_id=player, card=card))
            cards.append(card)
    exported = session_api.export_session_position_request(
        state, default_session_position_export_options_v1()).value
    checkpoint = session_api.build_session_decision_checkpoint(
        state=state, position_export=exported).value
    if not complete:
        state = _apply(state, RecordSessionPlayCommandV1(
            expected_revision=state.revision, player_id="player-a", card=actual))
        return state, checkpoint
    hands = {p["player_id"]: list(p["initial_hand"]) for p in data["players"]}
    hands["player-a"] = [*clubs, "SA", "S10"]
    players = [p["player_id"] for p in data["players"]]
    leader = "player-a"
    tricks = []
    for index in range(10):
        order = players[players.index(leader):] + players[:players.index(leader)]
        cards, plays = [], []
        for player in order:
            card = ("CJ" if decision_trick == 2 and index == 0 and not cards else
                    actual if index == decision_trick - 1 and player == "player-a" else
                    get_legal_cards(hands[player], cards, "clubs")[0])
            hands[player].remove(card)
            cards.append(card)
            plays.append({"player_id": player, "card": card})
        tricks.append({"trick_number": index + 1, "leader_player_id": leader, "plays": plays})
        leader = order[get_trick_winner(cards, "clubs")]
    data["tricks"] = tricks[decision_trick - 1:]
    return _play_commands_from_data(state, data), checkpoint


def activate_saved_opening(server, **kwargs):
    state, checkpoint = saved_opening(**kwargs)
    return _activate_saved_decision(server, state, checkpoint)


@lru_cache
def ten_decision_document(*, bid_value=None):
    """Exact disposable prefixes for all ten own Plays, with cheap legacy settings."""
    state, _ = saved_opening(complete=True, bid_value=bid_value)
    checkpoints = []
    for record in state.command_log:
        if (record.command.kind != "record_play"
                or record.command.player_id != state.local_player_id):
            continue
        prefix = build_session_state_from_accepted_prefix_v1(
            state, target_revision=record.revision - 1)
        exported = session_api.export_session_position_request(
            prefix, replace(default_session_position_export_options_v1(), sample_count=1)).value
        checkpoints.append(session_api.build_session_decision_checkpoint(
            state=prefix, position_export=exported).value)
    assert len(checkpoints) == 10
    return session_api.build_session_persistence_document(
        state, decision_checkpoints=tuple(checkpoints)).value


def activate_ten_decisions(server, *, bid_value=None):
    app = server.app_context
    context = import_guided_session_v1(app.managed_stateful.root("sessions"),
        handle="a" * 64, document=ten_decision_document(bid_value=bid_value).to_dict())
    app.managed_stateful.activate_session(context)
    return context


def activate_saved_defender_decision(server, *, bid_value, game_type="clubs"):
    """Own defender hand cannot establish the hidden declarer's matadors."""
    data = build_historical_input(game_type=game_type, declarer_player_id="player-a",
                                  bid_value=bid_value)
    state = _retrospective_before_play(data, local_player_id="player-b")
    first, second = data["tricks"][0]["plays"][:2]
    state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                   player_id=first["player_id"], card=first["card"]))
    exported = session_api.export_session_position_request(
        state, default_session_position_export_options_v1()).value
    checkpoint = session_api.build_session_decision_checkpoint(
        state=state, position_export=exported).value
    state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                   player_id=second["player_id"], card=second["card"]))
    return _activate_saved_decision(server, state, checkpoint)


def _activate_saved_decision(server, state, checkpoint):
    document = session_api.build_session_persistence_document(
        state, decision_checkpoints=(checkpoint,)).value
    app = server.app_context
    context = import_guided_session_v1(app.managed_stateful.root("sessions"),
        handle="a" * 64, document=document.to_dict())
    app.managed_stateful.activate_session(context)
    return context, checkpoint


def synthetic_tied_rollout(view, settings):
    """Reuse one-world scaffolding for a typed synthetic completed aggregate fixture."""
    from skatmind.whole_game_rollout import evaluate_whole_game_rollout_v1
    from skatmind.whole_game_rollout_contracts import WholeGameRolloutWorkV1

    assert settings.requested_worlds == 100 and settings.objective == "played_game_goal"
    result = evaluate_whole_game_rollout_v1(view, replace(settings, requested_worlds=1))
    candidates = []
    for candidate in result.candidates:
        margin = 10520 if candidate.card in ("C9", "C8", "C7") else 10420
        candidates.append(replace(candidate, completed_samples=100, local_success_count=100,
            total_local_card_point_margin=margin, total_declarer_points=(12000 + margin) // 2,
            total_defender_points=(12000 - margin) // 2,
            total_declarer_tricks=900, total_defender_tricks=100))
    ranked = sorted(candidates, key=lambda candidate: candidate.comparison_key(), reverse=True)
    return replace(result, settings=settings, candidates=tuple(candidates),
        completed_common_worlds=100, ranked_cards=tuple(candidate.card for candidate in ranked),
        tied_best_cards=("C9", "C8", "C7"), recommended_card="C9",
        work=WholeGameRolloutWorkV1(sampled_worlds=100, materialized_worlds=100,
            card_transitions=30000, terminal_evaluations=1000))
