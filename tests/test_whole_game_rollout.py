"""Synthetic whole-game evaluation checks; no recorded or UAT data."""

import copy
import json
import random
from collections import Counter
from dataclasses import FrozenInstanceError, replace

import pytest
from whole_game_rollout_oracle import (
    finite_worlds,
    reference_action,
    reference_continuation,
    small_view,
    synthetic_view,
)

import skatmind.whole_game_rollout as rollout
from skatmind.bounded_search_information import build_live_search_information_view
from skatmind.coherent_hidden_world import derive_simulation_child_seed
from skatmind.compatible_search_world import build_compatible_search_world_space
from skatmind.deck import get_full_deck
from skatmind.exact_search_state import build_exact_search_state
from skatmind.exact_terminal_utility import build_exact_terminal_utility
from skatmind.game_declaration import GameDeclaration
from skatmind.game_state import GameState
from skatmind.hidden_card_inference import (
    PlayerHiddenCardConstraints,
    iter_compatible_hidden_worlds,
    sample_compatible_hidden_worlds,
)
from skatmind.information_set_search_state import (
    InformationSetSearchObservationV1,
    apply_information_set_search_card_v1,
    build_information_set_search_observation_v1,
    build_information_set_search_world_state_v1,
)
from skatmind.public_hand_constraint import canonicalize_cards
from skatmind.rules import get_trick_points
from skatmind.whole_game_rollout import (
    WholeGameRolloutPreparationV1,
    evaluate_whole_game_rollout_v1,
    execute_whole_game_rollout_v1,
    prepare_whole_game_rollout_v1,
)
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1
from skatmind.whole_game_rollout_policy import select_whole_game_rollout_card_v1


def settings(**changes):
    return WholeGameRolloutSettingsV1(**{"random_seed": 284, "requested_worlds": 3, **changes})


def opening_view():
    return build_live_search_information_view(
        state=GameState(
            game_type="clubs",
            player_role="declarer",
            declarer_player="me",
            hand=["C7", "C8", "C9", "C10", "CJ", "CQ", "CK", "CA", "SA", "S10"],
            current_trick=[],
            skat=["H7", "D7"],
            trick_leader="me",
            next_player="me",
        ),
        declaration=GameDeclaration("clubs"),
        left_hand_size=10,
        right_hand_size=10,
        skat_visibility="known_to_declarer",
    )


def test_ten_trick_unknown_bid_opening_completes_every_candidate():
    view = opening_view()
    result = evaluate_whole_game_rollout_v1(
        view, WholeGameRolloutSettingsV1(random_seed=284, requested_worlds=2)
    )
    assert result.status == "complete"
    assert result.objective == "played_game_goal"
    assert result.completed_common_worlds == 2
    assert {item.card for item in result.candidates} == set(view.local_remaining_hand)
    assert all(item.completed_samples == 2 for item in result.candidates)
    assert all(item.total_local_game_score is None for item in result.candidates)
    assert result.work.card_transitions == 2 * 10 * 30
    assert result.work.terminal_evaluations == 20


def test_strict_settlement_missing_inputs_is_unavailable_before_sampling():
    result = evaluate_whole_game_rollout_v1(
        opening_view(),
        WholeGameRolloutSettingsV1(random_seed=284, objective="complete_settlement"),
    )
    assert result.status == "unavailable"
    assert result.stop_reason == "missing_terminal_utility_inputs"
    assert result.work.sampled_worlds == 0
    assert result.recommended_card is None


@pytest.mark.parametrize("game", ["clubs", "spades", "hearts", "diamonds", "grand"])
@pytest.mark.parametrize("remaining,partial,declarer", [(10, 0, "me"), (5, 1, "left"),
                                                       (2, 2, "right")])
def test_early_middle_partial_roots_agree_with_independent_reference(game, remaining,
                                                                  partial, declarer):
    view, _, _ = synthetic_view(
        seed=19, remaining=remaining, partial=partial, declarer=declarer,
        declaration=GameDeclaration(game),
    )
    p = prepare_whole_game_rollout_v1(view, settings(requested_worlds=2))
    result = execute_whole_game_rollout_v1(p)
    assert result.status == "complete"
    assert result.remaining_tricks == remaining
    assert len(view.current_trick) == partial
    assert result.work.card_transitions == 2 * len(result.candidates) * (3 * remaining - partial)
    for candidate in result.candidates:
        expected = [reference_continuation(
            view, {player: root.exact_state.hand_for(player) for player in ("me", "left", "right")},
            root.exact_state.out_of_play_cards, candidate.card,
        ) for root in p._worlds]
        assert candidate.local_success_count == sum(row[0] for row in expected)
        assert candidate.total_local_card_point_margin == sum(row[1] for row in expected)
        assert candidate.total_declarer_points == sum(row[2][0] for row in expected)
        assert candidate.total_defender_points == sum(row[2][1] for row in expected)
        assert candidate.total_declarer_tricks == sum(row[3][0] for row in expected)
        assert candidate.total_defender_tricks == sum(row[3][1] for row in expected)
        assert candidate.total_declarer_points + candidate.total_defender_points == 240
        assert candidate.total_declarer_tricks + candidate.total_defender_tricks == 20


def test_manually_checkable_immediate_and_terminal_rankings_differ():
    view, hands, skat = small_view()
    assert (view.declarer_points, view.defender_points) == (36, 46)
    assert get_trick_points(list(skat)) == 4
    s9 = reference_continuation(view, hands, skat, "S9")
    da = reference_continuation(view, hands, skat, "DA")
    # S9/D7/S10 loses 10; DQ/DA/D10 then wins 24: 36 + 4 + 24 = 64.
    assert s9[:5] == (1, 8, (64, 56), (5, 5), -10)
    # DA/D7/DQ wins 14; S9/D10/S10 then loses 20: 36 + 4 + 14 = 54.
    assert da[:5] == (0, -12, (54, 66), (5, 5), 14)
    result = evaluate_whole_game_rollout_v1(view, settings())
    assert result.compatible_world_count == 1
    assert result.unique_sampled_worlds == 1
    assert result.completed_common_worlds == 3  # Exact duplicate draws retain unit weight.
    assert result.ranked_cards == ("S9", "DA")
    assert result.tied_best_cards == ("S9",)
    assert result.recommended_card == "S9"
    assert [(c.card, c.local_success_count, c.total_local_card_point_margin)
            for c in result.candidates] == [("S9", 3, 24), ("DA", 0, -36)]


def test_tiny_finite_world_oracle_and_real_sample_duplicate_weighting(monkeypatch):
    view, _, _ = small_view(public=False)
    worlds = finite_worlds(view)
    assert len(worlds) == 6
    oracle = {
        world: {
            card: reference_continuation(
                view, {"me": view.local_remaining_hand, "left": world.left_hand,
                       "right": world.right_hand}, view.known_skat_cards, card,
            ) for card in view.local_remaining_hand
        } for world in worlds
    }
    # Exhaustively exercise the independent finite sequence at the sampler seam.
    original = rollout.iter_compatible_hidden_worlds
    monkeypatch.setattr(rollout, "iter_compatible_hidden_worlds", lambda *a, **k: iter(worlds))
    exhaustive = evaluate_whole_game_rollout_v1(view, settings(requested_worlds=6))
    assert exhaustive.compatible_world_count == 6
    for c in exhaustive.candidates:
        assert c.local_success_count == sum(oracle[w][c.card][0] for w in worlds)
        assert c.total_local_card_point_margin == sum(oracle[w][c.card][1] for w in worlds)
    monkeypatch.setattr(rollout, "iter_compatible_hidden_worlds", original)
    config = settings(requested_worlds=17)
    space = build_compatible_search_world_space(view)
    seed = derive_simulation_child_seed(config.random_seed, "whole_game_rollout_worlds_v1")
    draws = sample_compatible_hidden_worlds(space._assignment_problem, 17, random.Random(seed))
    multiplicities = Counter(draws)
    assert len(multiplicities) < len(draws)
    assert len(set(multiplicities.values())) > 1
    sampled = evaluate_whole_game_rollout_v1(view, config)
    assert sampled.unique_sampled_worlds == len(multiplicities)
    assert sampled.completed_common_worlds == 17
    for c in sampled.candidates:
        assert c.completed_samples == 17
        assert c.local_success_count == sum(oracle[w][c.card][0] for w in draws)
        assert c.total_local_card_point_margin == sum(oracle[w][c.card][1] for w in draws)


@pytest.mark.parametrize("declarer", ["me", "left", "right"])
@pytest.mark.parametrize("declaration", [
    GameDeclaration("grand", matadors=1, bid_value=24),
    GameDeclaration("grand", matadors=1, bid_value=120),
    GameDeclaration("clubs", schneider_announced=True, matadors=2, bid_value=18),
    GameDeclaration("clubs", schwarz_announced=True, matadors=2, bid_value=18),
    GameDeclaration("grand", ouvert=True, matadors=1, bid_value=24),
])
def test_strict_settlement_rollouts_match_existing_terminal_utility(declarer, declaration):
    view, _, _ = synthetic_view(seed=8, remaining=2, partial=1, declarer=declarer,
                                declaration=declaration)
    p = prepare_whole_game_rollout_v1(view, settings(objective="complete_settlement"))
    result = execute_whole_game_rollout_v1(p)
    assert result.status == "complete"
    for c in result.candidates:
        utilities = []
        for root in p._worlds:
            state = root.exact_state
            row = reference_continuation(
                view, {player: state.hand_for(player) for player in ("me", "left", "right")},
                state.out_of_play_cards, c.card,
            )
            terminal = build_exact_search_state(
                declaration=declaration, declarer_player=declarer,
                remaining_hands={"me": (), "left": (), "right": ()},
                current_trick=(), next_player="me",
                declarer_trick_points=row[2][0] - get_trick_points(list(state.out_of_play_cards)),
                defender_trick_points=row[2][1], declarer_completed_tricks=row[3][0],
                defender_completed_tricks=row[3][1], out_of_play_cards=state.out_of_play_cards,
            )
            utilities.append(build_exact_terminal_utility(
                state=terminal, local_side=view.local_side
            ))
        assert c.local_success_count == sum(u.local_contract_success for u in utilities)
        assert c.total_local_game_score == sum(u.local_side_game_score for u in utilities)
        assert c.total_local_card_point_margin == sum(
            u.local_side_card_point_margin for u in utilities
        )


@pytest.mark.parametrize("declaration,points,tricks,won", [
    (GameDeclaration("grand"), 60, 5, False),
    (GameDeclaration("grand"), 61, 5, True),
    (GameDeclaration("grand", schneider_announced=True), 89, 8, False),
    (GameDeclaration("grand", schneider_announced=True), 90, 8, True),
    (GameDeclaration("grand", schwarz_announced=True), 120, 9, False),
    (GameDeclaration("grand", schwarz_announced=True), 120, 10, True),
    (GameDeclaration("clubs", ouvert=True), 120, 9, False),
    (GameDeclaration("clubs", ouvert=True), 120, 10, True),
    (GameDeclaration("clubs", matadors=1, bid_value=200), 100, 9, True),
])
def test_played_goals_use_announcements_and_tricks_without_settlement(declaration, points,
                                                                   tricks, won):
    terminal = build_exact_search_state(
        declaration=declaration, declarer_player="me",
        remaining_hands={"me": (), "left": (), "right": ()}, current_trick=(), next_player="me",
        declarer_trick_points=points, defender_trick_points=120 - points,
        declarer_completed_tricks=tricks, defender_completed_tricks=10 - tricks,
        out_of_play_cards=("D7", "D8"),
    )
    local = rollout._terminal_candidate(terminal, "CJ", "played_game_goal", "declarer")
    defender = rollout._terminal_candidate(terminal, "CJ", "played_game_goal", "defenders")
    assert local.local_success_count == won
    assert defender.local_success_count == (not won)
    assert local.total_local_card_point_margin == -defender.total_local_card_point_margin
    assert local.total_local_game_score is defender.total_local_game_score is None


@pytest.mark.parametrize("declaration", [GameDeclaration("grand", matadors=1),
                                        GameDeclaration("grand", bid_value=24)])
def test_either_missing_settlement_input_does_not_change_objective(declaration):
    view, _, _ = small_view(declaration=declaration)
    played = evaluate_whole_game_rollout_v1(view, settings())
    strict = evaluate_whole_game_rollout_v1(view, settings(objective="complete_settlement"))
    assert played.status == "complete"
    assert strict.status == "unavailable"
    assert strict.objective == "complete_settlement"
    assert strict.work.sampled_worlds == strict.work.card_transitions == 0


def test_seed_and_candidate_order_reproducibility_and_ties():
    view, _, _ = small_view(public=False)
    config = settings(requested_worlds=13)
    p = prepare_whole_game_rollout_v1(view, config)
    first = execute_whole_game_rollout_v1(p)
    reverse = execute_whole_game_rollout_v1(p, candidate_order=tuple(reversed(p.legal_root_cards)))
    assert first == reverse == evaluate_whole_game_rollout_v1(view, config)
    for bad in [("S9",), ("S9", "S9"), ["S9", "DA"]]:
        with pytest.raises(ValueError, match="permute"):
            execute_whole_game_rollout_v1(p, candidate_order=bad)
    # An exact small fixture where both candidates produce identical terminal facts.
    tied_view, _, _ = synthetic_view(seed=1, remaining=2, public_players=("left", "right"))
    tied = evaluate_whole_game_rollout_v1(tied_view, settings())
    best = max(c.comparison_key() for c in tied.candidates)
    expected = tuple(c.card for c in tied.candidates if c.comparison_key() == best)
    assert len(expected) == 2
    assert tied.tied_best_cards == expected
    assert tied.recommended_card == expected[0]


def test_every_later_actor_receives_only_an_observation_and_matches_reference(monkeypatch):
    actors = Counter()
    original = rollout.select_whole_game_rollout_card_v1

    def checked(observation):
        assert isinstance(observation, InformationSetSearchObservationV1)
        assert not hasattr(observation, "exact_state")
        assert not hasattr(observation, "world_index")
        assert not hasattr(observation, "random_seed")
        actors[observation.actor_player] += 1
        selected = original(observation)
        assert selected == reference_action(
            observation.own_remaining_hand,
            [(play.player, play.card) for play in observation.current_trick],
            observation.actor_player, observation.declarer_player, observation.game_type,
        )
        return selected

    monkeypatch.setattr(rollout, "select_whole_game_rollout_card_v1", checked)
    result = evaluate_whole_game_rollout_v1(opening_view(), settings(requested_worlds=2))
    assert result.status == "complete"
    assert actors == {"me": 180, "left": 200, "right": 200}


@pytest.mark.parametrize("actor", ["me", "left", "right"])
def test_same_observation_different_hidden_world_policy_invariance(actor):
    view, _, _ = synthetic_view(remaining=10, declaration=GameDeclaration("grand", hand_game=True))
    p = prepare_whole_game_rollout_v1(view, settings(requested_worlds=1))
    root = p._worlds[0]
    state = root.exact_state
    hands = {player: list(state.hand_for(player)) for player in ("me", "left", "right")}
    skat = list(state.out_of_play_cards)
    if actor == "me":
        hands["left"][-1], hands["right"][-1] = hands["right"][-1], hands["left"][-1]
    else:
        other = "right" if actor == "left" else "left"
        hands[other][-1], skat[-1] = skat[-1], hands[other][-1]
    alternate = build_exact_search_state(
        declaration=state.declaration, declarer_player=state.declarer_player,
        remaining_hands=hands, current_trick=(), next_player="me",
        declarer_trick_points=0, defender_trick_points=0,
        declarer_completed_tricks=0, defender_completed_tricks=0, out_of_play_cards=skat,
    )
    roots = [root, build_information_set_search_world_state_v1(information_view=view,
                                                               exact_state=alternate)]
    while roots[0].exact_state.next_player != actor:
        legal = [set(build_information_set_search_observation_v1(r).legal_cards) for r in roots]
        card = canonicalize_cards(tuple(legal[0] & legal[1]))[0]
        roots = [apply_information_set_search_card_v1(r, card) for r in roots]
    observations = [build_information_set_search_observation_v1(r) for r in roots]
    assert roots[0].exact_state != roots[1].exact_state
    assert observations[0] == observations[1]
    assert select_whole_game_rollout_card_v1(observations[0]) == (
        select_whole_game_rollout_card_v1(observations[1])
    )


@pytest.mark.parametrize("known_count", [0, 1])
def test_local_partial_skat_knowledge_never_expands_to_sampled_skat(known_count):
    view = opening_view()
    state = GameState(
        game_type="clubs", player_role="declarer", declarer_player="me",
        hand=list(view.local_remaining_hand), current_trick=[],
        skat=list(view.known_skat_cards[:known_count]), trick_leader="me", next_player="me",
    )
    view = build_live_search_information_view(
        state=state, declaration=view.declaration, left_hand_size=10, right_hand_size=10,
        skat_visibility="known_to_declarer",
    )
    p = prepare_whole_game_rollout_v1(view, settings(requested_worlds=2))
    for root in p._worlds:
        # The original Search entry remains strict by default.
        with pytest.raises(ValueError, match="visibility"):
            build_information_set_search_world_state_v1(information_view=view,
                                                        exact_state=root.exact_state)
        child = root
        while not child.exact_state.is_terminal:
            observation = build_information_set_search_observation_v1(child)
            if observation.actor_player == "me":
                assert observation.visible_out_of_play_cards == view.known_skat_cards
            else:
                assert observation.visible_out_of_play_cards == ()
            child = apply_information_set_search_card_v1(
                child, select_whole_game_rollout_card_v1(observation)
            )
    assert execute_whole_game_rollout_v1(p).status == "complete"


@pytest.mark.parametrize("limit,completed,terminals", [(1, 0, 0), (30, 0, 1), (301, 1, 10)])
def test_transition_interruption_discards_incomplete_candidate_batch(limit, completed, terminals):
    result = evaluate_whole_game_rollout_v1(
        opening_view(), settings(requested_worlds=2, max_card_transitions=limit)
    )
    assert result.status == "partial"
    assert result.stop_reason == "transition_budget_exhausted"
    assert result.completed_common_worlds == completed
    assert result.work.card_transitions == limit
    assert result.work.terminal_evaluations == terminals
    assert all(c.completed_samples == completed for c in result.candidates)
    assert result.recommended_card is None
    assert result.ranked_cards == result.tied_best_cards == ()
    if completed:
        one = evaluate_whole_game_rollout_v1(opening_view(), settings(requested_worlds=1))
        assert result.candidates == one.candidates


def test_preparation_budget_and_controlled_clock_cancellation():
    view = opening_view()
    prep = evaluate_whole_game_rollout_v1(view, settings(max_preparation_work=5))
    assert prep.status == "partial"
    assert prep.stop_reason == "preparation_budget_exhausted"
    assert prep.work.preparation_units == 5
    assert prep.work.sampled_worlds == prep.work.card_transitions == 0
    ticks = iter(range(10000))
    timed = evaluate_whole_game_rollout_v1(
        view, settings(wall_clock_timeout_ms=3), clock=lambda: next(ticks) / 1000
    )
    assert timed.status == "timeout"
    assert timed.completed_common_worlds == 0
    assert timed.recommended_card is None
    cancelled = evaluate_whole_game_rollout_v1(view, settings(), cancelled=lambda: True)
    assert cancelled.status == "cancelled"
    assert cancelled.work.preparation_units == 0
    assert cancelled.work.sampled_worlds == 0


def test_execution_clock_and_cancellation_keep_only_common_coverage():
    view, _, _ = small_view()
    p = prepare_whole_game_rollout_v1(view, settings(), clock=lambda: 0.0)
    calls = 0

    def cancelled():
        nonlocal calls
        calls += 1
        return calls == 20

    result = execute_whole_game_rollout_v1(p, cancelled=cancelled)
    assert result.status == "cancelled"
    assert result.completed_common_worlds == 1
    assert all(c.completed_samples == 1 for c in result.candidates)
    assert result.recommended_card is None
    p = prepare_whole_game_rollout_v1(
        view, settings(wall_clock_timeout_ms=18), clock=lambda: 0.0
    )
    ticks = iter(range(1000))
    timed = execute_whole_game_rollout_v1(p, clock=lambda: next(ticks) / 1000)
    assert timed.status == "timeout"
    assert timed.completed_common_worlds == 1
    assert all(c.completed_samples == 1 for c in timed.candidates)
    assert timed.ranked_cards == ()


def test_privacy_immutability_source_binding_and_historical_cutoff():
    view = opening_view()
    before = copy.deepcopy(view)
    p = prepare_whole_game_rollout_v1(view, settings())
    result = execute_whole_game_rollout_v1(p)
    assert view == before
    assert p == copy.deepcopy(p)
    assert execute_whole_game_rollout_v1(p) == result
    with pytest.raises(FrozenInstanceError):
        result.recommended_card = "SA"
    with pytest.raises(FrozenInstanceError):
        p.settings.random_seed = 5
    with pytest.raises(TypeError):
        WholeGameRolloutPreparationV1()
    payload = result.to_dict()
    text = json.dumps(payload, allow_nan=False)
    for forbidden in ("exact_state", "hypothetical_skat", "own_remaining_hand", "world_digest",
                      "_worlds", "continuation", "principal_variation", "actual_card_played"):
        assert f'"{forbidden}"' not in text

    def strings(value):
        if isinstance(value, dict):
            return {s for item in value.values() for s in strings(item)}
        if isinstance(value, list):
            return {s for item in value for s in strings(item)}
        return {value} if isinstance(value, str) else set()

    assert strings(payload) & set(get_full_deck()) == set(view.local_remaining_hand)
    payload["candidates"][0]["card"] = "changed"
    assert result.to_dict()["candidates"][0]["card"] != "changed"
    another = evaluate_whole_game_rollout_v1(view, settings(random_seed=285))
    assert another.source_fingerprint == result.source_fingerprint
    historical = evaluate_whole_game_rollout_v1(
        replace(view, source="historical_decision_snapshot"), settings()
    )
    assert historical.candidates == result.candidates
    assert historical.source_fingerprint != result.source_fingerprint
    assert historical.information_cutoff == "current_decision"
    assert "played_goal_excludes_overbid_and_complete_settlement" in result.limitations


@pytest.mark.parametrize("changes", [
    {"random_seed": True}, {"random_seed": -1}, {"random_seed": 2**64},
    {"requested_worlds": 0}, {"requested_worlds": 1001}, {"requested_worlds": 1.5},
    {"max_card_transitions": True}, {"max_card_transitions": 300001},
    {"max_preparation_work": 0}, {"max_preparation_work": 100001},
    {"wall_clock_timeout_ms": 0}, {"wall_clock_timeout_ms": float("nan")},
    {"objective": "auto"},
])
def test_malformed_settings_rejected(changes):
    with pytest.raises(ValueError):
        settings(**changes)


@pytest.mark.parametrize("change", [
    {"declarer_points": 5}, {"information_cutoff": "post_game"},
    {"declarer_trick_count": 1},
    {"hidden_card_constraints": (
        PlayerHiddenCardConstraints("me", (), opening_view().local_remaining_hand),
        PlayerHiddenCardConstraints("left", (), ("SJ",)),
        PlayerHiddenCardConstraints("right", (), ()),
    )},
])
def test_forged_or_future_information_rejected_before_sampling(change):
    with pytest.raises(ValueError):
        prepare_whole_game_rollout_v1(replace(opening_view(), **change), settings())


def test_null_complete_and_wrong_actor_are_explicitly_unavailable():
    null, _, _ = synthetic_view(remaining=10, declaration=GameDeclaration("null"))
    complete, _, _ = synthetic_view(remaining=0)
    wrong_actor = replace(opening_view(), next_player="left")
    for view, reason in [(null, "unsupported_game_type"), (complete, "game_already_complete"),
                         (wrong_actor, "local_player_not_to_act")]:
        result = evaluate_whole_game_rollout_v1(view, settings())
        assert result.status == "unavailable"
        assert result.stop_reason == reason
        assert result.work.sampled_worlds == 0
        assert result.recommended_card is None


def test_unresolved_roles_and_turns_are_unavailable():
    root = opening_view()
    for declarer, next_player, reason in [
        ("unknown", "me", "missing_concrete_declarer"),
        ("me", "unknown", "unsupported_turn_phase"),
    ]:
        view = build_live_search_information_view(
            state=GameState(
                game_type="clubs", player_role="unknown" if declarer == "unknown" else "declarer",
                declarer_player=declarer, hand=list(root.local_remaining_hand), current_trick=[],
                trick_leader=next_player, next_player=next_player,
            ),
            declaration=root.declaration, left_hand_size=10, right_hand_size=10,
        )
        result = evaluate_whole_game_rollout_v1(view, settings())
        assert result.status == "unavailable"
        assert result.stop_reason == reason
        assert result.work.sampled_worlds == 0


def test_goal_and_overbid_settlement_are_distinct_on_the_same_worlds():
    view, _, _ = small_view(declaration=GameDeclaration("grand", matadors=1, bid_value=200))
    played = evaluate_whole_game_rollout_v1(view, settings())
    strict = evaluate_whole_game_rollout_v1(view, settings(objective="complete_settlement"))
    assert played.status == strict.status == "complete"
    assert played.candidates[0].local_success_count == 3
    assert strict.candidates[0].local_success_count == 0
    assert strict.candidates[0].total_local_game_score < 0
    assert played.candidates[0].total_local_game_score is None
    assert played.source_fingerprint == strict.source_fingerprint
    assert [c.total_local_card_point_margin for c in played.candidates] == [
        c.total_local_card_point_margin for c in strict.candidates
    ]


def test_result_contract_rejects_partial_recommendation_and_mixed_coverage():
    complete = evaluate_whole_game_rollout_v1(opening_view(), settings(requested_worlds=1))
    with pytest.raises(ValueError, match="cannot rank"):
        replace(complete, status="partial")
    with pytest.raises(ValueError, match="identical common coverage"):
        replace(complete, completed_common_worlds=0)
    with pytest.raises(TypeError, match="tuple"):
        replace(complete, candidates=list(complete.candidates))
    with pytest.raises(TypeError):
        evaluate_whole_game_rollout_v1(opening_view(), settings(), actual_card_played="CJ")


def test_sampling_and_materialization_work_are_bounded_without_ranking():
    view, _, _ = small_view(public=False)
    complete = prepare_whole_game_rollout_v1(view, settings(requested_worlds=1))
    # Stop just before the final root materialization, after a complete draw was produced.
    stopped = prepare_whole_game_rollout_v1(
        view, settings(requested_worlds=1, max_preparation_work=complete.work.preparation_units - 1)
    )
    assert stopped.status == "partial"
    assert stopped.work.sampled_worlds == stopped.unique_sampled_worlds == 1
    assert stopped.work.materialized_worlds == 0
    result = execute_whole_game_rollout_v1(stopped)
    assert result.completed_common_worlds == 0
    assert result.work.card_transitions == 0
    assert result.recommended_card is None


def test_streaming_sampler_preserves_old_batch_sequence_and_counts_work():
    view, _, _ = small_view(public=False)
    space = build_compatible_search_world_space(view)
    units = 0

    def count():
        nonlocal units
        units += 1

    streamed = tuple(iter_compatible_hidden_worlds(
        space._assignment_problem, 10, random.Random(7), work_hook=count
    ))
    assert streamed == sample_compatible_hidden_worlds(
        space._assignment_problem, 10, random.Random(7)
    )
    assert units > 10 * len(space._assignment_problem.cards)
