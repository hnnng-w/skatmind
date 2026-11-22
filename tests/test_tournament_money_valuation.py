"""Finite developer models, with no provider calibration or recording I/O."""

from dataclasses import replace
from fractions import Fraction as Q
from time import monotonic, perf_counter

import pytest
from whole_game_rollout_oracle import synthetic_view

from skatmind.event_context_contracts import (
    TOURNAMENT_RULE,
    CheckpointV1,
    EventBindingV1,
    EventContextV1,
    EventTermsV1,
    FinancialFactsV1,
    ParticipantMapV1,
    PoolFactV1,
    RecordingKeyV1,
    RecordingVersionV1,
    RuleSourceV1,
)
from skatmind.event_context_projection import (
    DecisionCutoffV1,
    OutcomeFactV1,
    RecordingFactsV1,
    prepare_event_context_v1,
)
from skatmind.exact_search_state import build_exact_search_state
from skatmind.game_declaration import GameDeclaration
from skatmind.matador_inference import infer_matadors_from_declarer_cards
from skatmind.mode_accounting import STANDARD_RULE, STANDARD_SOURCE
from skatmind.tournament_money_valuation import (
    Candidate,
    Continuation,
    ListGame,
    PoolSchedule,
    PoolStanding,
    TournamentModel,
    TournamentPrefix,
    WorldOutcome,
    evaluate_tournament_money,
    terminal_list_game,
)
from skatmind.whole_game_rollout import _completed_batches, _Work, prepare_whole_game_rollout_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1
from skatmind.whole_game_rollout_policy import select_whole_game_rollout_card_v1

SOURCE = RuleSourceV1(reference="Synthetic complete tournament schedule", edition="1")
PLAYERS = ("a", "b", "c")
BASE = PoolSchedule(PoolFactV1(pool_id="base", participation="yes", entitlement="yes"),
                    field_size=6, awards_cents=(3000, 0, 0, 0, 0, 0))
PASSED = ListGame(None, None)


def event(*, game=36, selected="b", actor="b", losses=5, mode="tournament"):
    source = RecordingVersionV1(source=RecordingKeyV1(family="match", product_id="fixture-list"),
                                content_fingerprint="a" * 64, revision=7)
    binding = EventBindingV1(attached_source=source, game_position=None,
        players=tuple(ParticipantMapV1(source_player_id=x.upper(), event_player_id=x)
                      for x in PLAYERS), source_selected_player_id=selected.upper())
    context = EventContextV1(event_id="synthetic", series_id="list", event_name="Synthetic",
        series_name="Final series", participant_ids=PLAYERS, selected_participant_id=selected,
        bindings=(binding,), terms=(EventTermsV1(from_position=1, mode=mode, version=2,
            platform="euroskat", scoring_source=SOURCE, scoring_rule=TOURNAMENT_RULE,
            financial=FinancialFactsV1(currency="EUR", fee_source=STANDARD_SOURCE)),),
        checkpoints=(CheckpointV1(through_position=game-2, personal_points=920, own_losses=losses,
                                   provenance="Synthetic checkpoint"),))
    facts = RecordingFactsV1(source=source, player_ids=("A", "B", "C"),
        selected_player_id=selected.upper(), outcomes=(OutcomeFactV1(position=game-1,
            status="settled", outcome="declarer_loss", declarer_id="A", settlement_score=-48,
            evidence_fingerprint="b" * 64),), decisions=(DecisionCutoffV1(position=game,
                decision_index=22, actor_id=actor.upper(), game_id="synthetic-grand"),))
    return context, facts


def prepare(context, facts, *, game=36, decision=22):
    return prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                    game_position=game, decision_index=decision)


def model(prefix, *, worlds=(("w", Q(1)),), **changes):
    defaults = dict(prefix_id=prefix.fingerprint, model_revision="synthetic-v1",
        scenario_set_id="finite-model-1", fee_rule=STANDARD_RULE, payout_source=SOURCE,
        pools=(BASE,), worlds=worlds)
    return TournamentModel(**(defaults | changes))


def leaf(*, field=(500, 650, 1070, 1040, 900), **changes):
    defaults = dict(scenario_id="field", probability=Q(1), future_games=(),
        standings=(PoolStanding("base", other_scores=field),), transfer_cents=0,
        other_charge_cents=0)
    return Continuation(**(defaults | changes))


def candidate(basis, name, game, *leaves):
    return Candidate(name, basis, (WorldOutcome("w", game, tuple(leaves)),))


def prefix_at(game=36, *, decision=22, **kwargs):
    context, facts = event(game=game, **kwargs)
    return TournamentPrefix(prepare(context, facts, game=game, decision=decision), context)


def single(prefix, basis, game, *leaves):
    return evaluate_tournament_money(prefix, basis, (candidate(basis, "one", game, *leaves),))


def test_real_common_card_continuations_reverse_success_and_score(record_property):
    context, facts = event()
    prefix = TournamentPrefix(prepare(context, facts), context)
    assert prefix.seats == ("a", "b", "c")
    assert (prefix.prepared.personal_points, prefix.prepared.own_losses,
            prefix.prepared.remaining_including_current) == (960, 5, 1)
    view, _, _ = synthetic_view(seed=605, remaining=3,
                                declaration=GameDeclaration("grand", matadors=1, bid_value=24))
    owned = [p.card for trick in view.completed_tricks for p in trick.plays if p.player == "me"]
    assert infer_matadors_from_declarer_cards("grand", [
        *owned, *view.local_remaining_hand, *view.known_skat_cards]) == view.declaration.matadors
    settings = WholeGameRolloutSettingsV1(random_seed=1, requested_worlds=4,
                                          objective="complete_settlement")
    assert view.completed_tricks[0].plays[0].player == "right"  # Game-36 forehand A.
    start = perf_counter()
    rollout = prepare_whole_game_rollout_v1(view, settings)
    assert rollout.status == "ready"
    assert rollout.legal_root_cards == ("S10", "S8", "H9")
    work = _Work(settings, monotonic, None, rollout.work)
    draws = tuple((f"draw-{i}", Q(1, 4)) for i in range(4))
    basis = model(prefix, worlds=draws)
    batches = _completed_batches(rollout, rollout.legal_root_cards, work,
        select_whole_game_rollout_card_v1, lambda state, *_: terminal_list_game(prefix, state))
    candidates = {c: [] for c in rollout.legal_root_cards}
    for (world_id, _), batch in zip(draws, batches, strict=True):
        for card, game in batch.items():
            # The two table rivals also receive their 40 points when B loses.
            bonus = 40 * (game.settlement_score < 0)
            candidates[card].append(WorldOutcome(world_id, game, (
                leaf(field=(500 + bonus, 650 + bonus, 1070, 1040, 900)),)))
    alternatives = tuple(Candidate(c, basis, tuple(rows)) for c, rows in candidates.items())
    valuation_start = perf_counter()
    result = evaluate_tournament_money(prefix, basis, alternatives)
    end = perf_counter()
    record_property("valuation_ms", (end - valuation_start) * 1000)
    record_property("fixture_ms", (end - start) * 1000)
    assert (work.terminal_evaluations, work.card_transitions) == (12, 108)
    assert [[r.current_game.settlement_score for r in c.worlds] for c in alternatives] == [
        [-96, -96, 48, -96], [72, -96, -96, -96], [48, 48, 48, 48]]
    assert [sum(r.weight * r.final_points for r in c.outcomes) for c in result.candidates] == [
        875, 881, 1058]
    assert [[r.weight for r in c.outcomes] for c in result.candidates] == [[Q(1, 4)] * 4] * 3
    assert [(c.expected.prize_cents, c.expected.loss_fee_cents, c.expected.net_cents)
            for c in result.candidates] == [(0, 225, -225), (750, 225, 525), (0, 0, 0)]
    assert result.ranking == (("S8",), ("H9",), ("S10",))


@pytest.mark.parametrize(("selected", "declarer", "points", "expected"), [
    ("c", "left", 60, (-96, -146, 1)),
    ("c", "left", 61, (48, 98, 0)),
    ("a", "left", 60, (-96, 40, 0)),
    ("b", "left", 60, (-96, 40, 0)),
    ("b", "right", 61, (48, 0, 0)),
])
def test_rotated_event_aliases_terminal_score_and_both_defenders(selected, declarer,
                                                                 points, expected):
    prefix = prefix_at(35, selected=selected, actor="b")
    assert prefix.seats == ("c", "a", "b")
    terminal = build_exact_search_state(declaration=GameDeclaration("grand", matadors=1,
        bid_value=24), declarer_player=declarer,
        remaining_hands={"me": (), "left": (), "right": ()},
        current_trick=(), next_player="me", declarer_trick_points=points,
        defender_trick_points=120-points, declarer_completed_tricks=5, defender_completed_tricks=5,
        out_of_play_cards=("D7", "D8"))
    game = terminal_list_game(prefix, terminal)
    assert game.declarer_id == ("c" if declarer == "left" else "a")
    row = game.contribution(prefix)
    assert (game.settlement_score, row.total_performance_points, row.own_games_lost) == expected
    valued = single(prefix, model(prefix), game, leaf(future_games=(PASSED,))).candidates[0]
    assert valued.outcomes[0].final_own_losses == prefix.prepared.own_losses + expected[2]
    assert valued.expected.loss_fee_cents == 300 * expected[2]


def test_unsupported_null_overbid_has_no_monetary_settlement():
    terminal = build_exact_search_state(declaration=GameDeclaration("null", bid_value=48),
        declarer_player="me", remaining_hands={"me": (), "left": (), "right": ()},
        current_trick=(), next_player="me", declarer_trick_points=0, defender_trick_points=120,
        declarer_completed_tricks=0, defender_completed_tricks=10, out_of_play_cards=("D7", "D8"))
    with pytest.raises(ValueError, match="no supported complete terminal settlement"):
        terminal_list_game(prefix_at(), terminal)


def test_conditioned_futures_with_equal_expected_losses_and_nonlinear_fees():
    prefix = prefix_at(34, losses=4)
    basis = model(prefix)
    current = ListGame("c", 24)
    loss = ListGame("b", -48)
    field = (3000, 2500, 3200, 2000, 3100)
    def path(name, games, weight):
        return leaf(field=field, scenario_id=name, future_games=games, probability=weight,
                    transfer_cents=Q(-3, 2), other_charge_cents=Q(1, 2))
    alternatives = (
        candidate(basis, "spread", current, path("none", (PASSED, PASSED), Q(1, 2)),
                  path("two", (loss, loss), Q(1, 2))),
        candidate(basis, "steady", current, path("one", (loss, PASSED), Q(1))),
    )
    result = evaluate_tournament_money(prefix, basis, alternatives)
    assert result.ranking == (("steady",), ("spread",))
    spread, steady = result.candidates
    assert [r.money.loss_fee_cents for r in spread.outcomes] == [0, 400]
    for c in result.candidates:
        assert sum(r.weight * r.final_own_losses for r in c.outcomes) == 5
        assert sum(r.weight * r.final_points for r in c.outcomes) == 862
        assert c.expected.prize_cents == 0 and c.expected.transfer_cents == Q(-3, 2)
        assert c.total_net_cents is None
    assert (spread.expected.loss_fee_cents, steady.expected.loss_fee_cents) == (200, 100)
    assert (spread.expected.cost_cents, steady.expected.cost_cents) == (Q(401, 2), Q(201, 2))
    assert (spread.expected.net_cents, steady.expected.net_cents) == (-202, -102)


def test_equal_mean_points_separate_plus_field_and_no_score_threshold():
    prefix = prefix_at(35)
    plus = PoolSchedule(replace(BASE.membership, pool_id="plus-1"), 3, (700, 200, 0))
    basis = model(prefix, pools=(BASE, plus))
    # The selected player's fixed current win yields 1058; a later win gives 1156.
    current = ListGame("b", 48)
    def path(name, future, high, weight):
        field = (1400, 1350, 1200, 1170, 1160) if high else (800, 700, 550, 420, 350)
        plus_field = (1400, 1200) if high else (1960, 200)
        return leaf(scenario_id=name, probability=weight, future_games=(future,), standings=(
            PoolStanding("base", other_scores=field),
            PoolStanding("plus-1", other_scores=plus_field)))
    alternatives = tuple(candidate(basis, name, current,
        path("no_delta", PASSED, low_is_high, Q(1, 2)),
        path("later_win", current, True, Q(1, 2)))
        for name, low_is_high in (("spread_fields", False), ("strong_field", True)))
    result = evaluate_tournament_money(prefix, basis, alternatives)
    assert [sum(r.weight*r.final_points for r in c.outcomes) for c in result.candidates] == [
        1107, 1107]
    low, high = result.candidates[0].outcomes
    assert (low.final_points, low.awards_cents) == (1058, (("base", 3000), ("plus-1", 200)))
    assert (high.final_points, high.awards_cents) == (1156, (("base", 0), ("plus-1", 0)))
    assert [c.expected.net_cents for c in result.candidates] == [1600, 0]


def test_known_pass_accounting_is_not_a_card_alternative():
    prefix = prefix_at(decision=None)
    c, = single(prefix, model(prefix), PASSED, leaf()).candidates
    assert c.expected.net_cents == 0 and c.outcomes[0].final_points == 960
    assert c.outcomes[0].final_own_losses == 5
    prefix = prefix_at()
    with pytest.raises(ValueError, match="cannot change the current declarer or pass"):
        single(prefix, model(prefix), PASSED, leaf())


def test_sunk_invariance_with_exact_primary_ties():
    prefix = prefix_at()
    results = []
    for sunk in (None, -675, -1675):
        basis = model(prefix, sunk_net_cents=sunk)
        choices = tuple(candidate(basis, name, ListGame("b", score), leaf(transfer_cents=Q(1, 3)))
                        for name, score in (("x", 48), ("y", 48), ("z", -96)))
        results.append(evaluate_tournament_money(prefix, basis, choices))
    for result in results:
        assert result.ranking == (("x", "y"), ("z",))
        row = result.candidates[0].outcomes[0]
        assert (row.final_points, row.final_own_losses, row.money.loss_fee_cents) == (1058, 5, 0)
        assert row.money.net_cents == Q(1, 3)
    assert [r.candidates[0].total_net_cents for r in results] == [
        None, Q(1, 3)-675, Q(1, 3)-1675]


@pytest.mark.parametrize(("pool", "standing", "reason"), [
    (replace(BASE, awards_cents=(3000,)), PoolStanding("base", resolved_rank=1),
     "incomplete_schedule"),
    (replace(BASE, membership=replace(BASE.membership, entitlement="unknown")), None,
     "entitlement_unknown"),
    (BASE, None, "standing_missing"),
    (BASE, PoolStanding("base", resolved_rank=2), "rank_evidence_missing"),
    (BASE, PoolStanding("base", other_scores=(100, 200)), "incomplete_field"),
    (BASE, PoolStanding("base", other_scores=(960, 900, 800, 700, 600)), "unresolved_tie"),
])
def test_unresolved_prize_has_reason_and_retains_established_cost(pool, standing, reason):
    prefix = prefix_at()
    basis = model(prefix, pools=(pool,))
    result = single(prefix, basis, ListGame("c", 48),
                    leaf(standings=() if standing is None else (standing,), other_charge_cents=47))
    c, = result.candidates
    assert c.outcomes[0].unavailable == (f"base:{reason}",)
    assert c.expected.cost_cents == 47 and c.expected.transfer_cents == 0
    assert c.expected.prize_cents is c.expected.net_cents is None
    assert not result.ranking


def test_resolved_ties_rank_evidence_and_zero_mass_unresolved_component():
    prefix = prefix_at()
    basis = model(prefix)
    tied = PoolStanding("base", other_scores=(960, 900, 800, 700, 600), tied_ahead=0,
                        resolution_evidence="Modeled first on the synthetic tie key")
    resolved = PoolStanding("base", resolved_rank=2, resolution_evidence="Synthetic final draw")
    good = candidate(basis, "one", ListGame("a", 48), leaf(standings=(tied,)),
                     leaf(scenario_id="absent", probability=0, transfer_cents=None))
    other = candidate(basis, "two", ListGame("a", 48), leaf(standings=(resolved,)))
    result = evaluate_tournament_money(prefix, basis, (good, other))
    assert [c.expected.net_cents for c in result.candidates] == [3000, 0]
    assert result.ranking == (("one",), ("two",))
    partial = candidate(basis, "two", ListGame("a", 48), leaf(probability=Q(99, 100)),
                        leaf(scenario_id="gap", probability=Q(1, 100), standings=()))
    assert not evaluate_tournament_money(prefix, basis, (good, partial)).ranking


def test_missing_selected_pool_and_side_settlement_remain_unavailable():
    context, facts = event(mode="tournament_cent")
    terms, = context.terms
    plus = replace(BASE.membership, pool_id="plus-2")
    context = replace(context, terms=(replace(terms, financial=replace(terms.financial,
        pools=(plus,), provenance="Confirmed selection at entry")),))
    prefix = TournamentPrefix(prepare(context, facts), context)
    basis = model(prefix)
    result = single(prefix, basis, ListGame("c", -48), leaf())
    row = result.candidates[0].outcomes[0]
    assert row.unavailable == ("plus-2:missing_pool_basis", "tournament_side_unresolved")
    assert dict(row.awards_cents) == {"base": 0, "plus-2": None}
    assert row.money.net_cents is None and row.money.loss_fee_cents == 0
    full = replace(basis, pools=(BASE, PoolSchedule(plus, 1, (150,))))
    supplied = leaf(standings=(PoolStanding("base", other_scores=(1, 2, 3, 4, 5)),
                               PoolStanding("plus-2", other_scores=())),
                    tournament_side_cents=-53, other_charge_cents=4)
    value = single(prefix, full, ListGame("c", -48), supplied).candidates[0].expected
    assert (value.prize_cents, value.transfer_cents, value.net_cents) == (3150, -53, 3093)
    denied = replace(full.pools[1], membership=replace(plus, entitlement="no"))
    with pytest.raises(ValueError, match="membership conflicts"):
        single(prefix, replace(full, pools=(BASE, denied)), ListGame("c", -48), supplied)


def test_no_entitlement_is_zero_but_unknown_fees_or_charges_are_not_zero():
    prefix = prefix_at()
    denied = replace(BASE, membership=replace(BASE.membership, entitlement="no"))
    basis = model(prefix, pools=(denied,), fee_rule="unverified")
    result = single(prefix, basis, ListGame("b", -48), leaf(standings=(), other_charge_cents=None))
    row = result.candidates[0].outcomes[0]
    assert row.money.prize_cents == 0 and row.money.cost_cents is row.money.net_cents is None
    assert row.unavailable == ("loss_rule_unconfirmed", "future_charge_unknown")
    assert not result.ranking


def test_current_and_later_facts_do_not_enter_the_model_or_replace_missing_prize_data():
    context, facts = event(game=35)
    terms, = context.terms
    misleading = replace(terms, from_position=36, platform="in_person",
                         financial=FinancialFactsV1(currency="USD"))
    context = replace(context, terms=(replace(terms, financial=replace(terms.financial,
        prize_facts="Receipt 500. Everyone over 1100 wins.", prize_completeness="complete",
        payout_source=SOURCE, provenance="Legacy fact")), misleading),
        checkpoints=(*context.checkpoints, CheckpointV1(through_position=36, personal_points=2000,
            own_losses=6, provenance="Unusable end-of-list checkpoint")))
    before = TournamentPrefix(prepare(context, facts, game=35), context)
    changed = replace(facts, source=replace(facts.source, revision=8, content_fingerprint="c"*64),
        outcomes=(*facts.outcomes, replace(facts.outcomes[0], position=35, declarer_id="B"),
                  replace(facts.outcomes[0], position=36, declarer_id="B")))
    after = TournamentPrefix(prepare(context, changed, game=35), context)
    assert before.fingerprint != after.fingerprint
    results = []
    for prefix in (before, after):
        basis = model(prefix, pools=(replace(BASE, awards_cents=None),))
        results.append(single(prefix, basis, ListGame("b", 48), leaf(future_games=(PASSED,))))
    assert results[0].candidates == results[1].candidates
    assert results[0].candidates[0].outcomes[0].final_points == 1058
    assert results[0].candidates[0].outcomes[0].unavailable == ("base:incomplete_schedule",)
    with pytest.raises(ValueError, match="prefix"):
        single(after, results[0].basis, ListGame("b", 48), leaf(future_games=(PASSED,)))
    with pytest.raises(ValueError, match="edition conflicts"):
        single(after, model(after, payout_source=replace(SOURCE, edition="unrelated")),
               ListGame("b", 48), leaf(future_games=(PASSED,)))


def test_chronology_gaps_conflicts_and_forged_totals_are_not_ready():
    context, facts = event()
    prefix = prepare(context, facts)
    with pytest.raises(ValueError, match="retained basis"):
        TournamentPrefix(replace(prefix, personal_points=10000), context)
    for status in ("missing", "unfinished", "source_conflict"):
        invalid = replace(facts, outcomes=(OutcomeFactV1(position=35, status=status),))
        with pytest.raises(ValueError, match="ready tournament"):
            TournamentPrefix(prepare(context, invalid), context)
    with pytest.raises(ValueError, match="ready tournament"):
        TournamentPrefix(prepare(context, replace(facts, decisions=())), context)


@pytest.mark.parametrize("bad_worlds", [
    (), (("x", Q(1, 2)),), (("x", 1), ("y", 1)), (("x", 2), ("y", -1)),
    (("x", Q(1, 2)), ("x", Q(1, 2))), (("x", 1.0),), (("x", True),),
])
def test_explicit_world_measure_is_exact_complete_and_unique(bad_worlds):
    with pytest.raises(ValueError):
        model(prefix_at(), worlds=bad_worlds)


def test_reject_incomplete_double_counted_and_incomparable_conditionals():
    prefix = prefix_at()
    basis = model(prefix, worlds=(("x", Q(1, 3)), ("y", Q(2, 3))))
    game = ListGame("b", -48)
    world = WorldOutcome("x", game, (leaf(),))
    good = Candidate("one", basis, (world, replace(world, world_id="y")))
    for bad in ((leaf(probability=Q(1, 2)),), (leaf(), leaf(scenario_id="extra")),
                (leaf(probability=Q(1, 2)),)*2):
        with pytest.raises(ValueError):
            replace(world, continuations=bad)
    with pytest.raises(ValueError):
        replace(good, worlds=(world, world))
    for wrong in (replace(good, worlds=(world,)), replace(good, basis=replace(basis,
            model_revision="other")), replace(good, basis=replace(basis, scenario_set_id="other")),
            replace(good, basis=replace(basis, pools=(replace(BASE, awards_cents=(0,)*6),))),
            replace(good, basis=replace(basis, fee_rule="unverified"))):
        with pytest.raises(ValueError, match="complete world and monetary basis"):
            evaluate_tournament_money(prefix, basis, (good, replace(wrong, name="other")))
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate_tournament_money(prefix, basis, (good, good))
    with pytest.raises(ValueError, match="objective"):
        replace(basis, objective="party_success")


def test_impossible_position_counts_field_and_settlement_rejected():
    prefix = prefix_at()
    basis = model(prefix)
    for game, invalid in (
        (ListGame("a", 18), leaf(future_games=(PASSED,))),
        (ListGame("missing", -48), leaf()), (PASSED, leaf()),
        (ListGame("a", 18), leaf(standings=(PoolStanding("base", resolved_rank=7),))),
        (ListGame("a", 18), leaf(standings=(PoolStanding("base", other_scores=(1,)*6),))),
        (ListGame("a", 18), leaf(standings=(PoolStanding("base", other_scores=(960,)*5,
                                                         tied_ahead=6),))),
    ):
        with pytest.raises(ValueError):
            single(prefix, basis, game, invalid)
    with pytest.raises(ValueError, match="nonzero signed"):
        ListGame("b", 0)
    with pytest.raises(ValueError, match="remaining positions"):
        prefix = prefix_at(35)
        single(prefix, model(prefix), ListGame("b", 18), leaf())
    for value in (True, 0.5, -1):
        with pytest.raises(ValueError):
            leaf(other_charge_cents=value)
