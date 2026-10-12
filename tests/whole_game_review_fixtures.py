"""Disposable saved opening with a legal synthetic suffix and no bid."""

from dataclasses import replace

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


def saved_opening(*, complete=False, reverse_hidden=False, actual="CJ"):
    clubs = [card for card in get_full_deck() if card.startswith("C")]
    rest = [card for card in get_full_deck() if card not in [*clubs, "H7", "D7", "SA", "S10"]]
    if reverse_hidden:
        rest.reverse()
    data = build_historical_input(game_type="clubs", declarer_player_id="player-a",
                                  bid_value=None, deck=["H7", "D7", *clubs, *rest, "SA", "S10"])
    state = _retrospective_before_play(data, local_player_id="player-a")
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
            card = actual if index == 0 and not cards else get_legal_cards(
                hands[player], cards, "clubs")[0]
            hands[player].remove(card)
            cards.append(card)
            plays.append({"player_id": player, "card": card})
        tricks.append({"trick_number": index + 1, "leader_player_id": leader, "plays": plays})
        leader = order[get_trick_winner(cards, "clubs")]
    data["tricks"] = tricks
    return _play_commands_from_data(state, data), checkpoint


def activate_saved_opening(server, **kwargs):
    state, checkpoint = saved_opening(**kwargs)
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
