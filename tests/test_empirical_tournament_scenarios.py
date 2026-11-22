"""Synthetic original recordings and a separately identified six-player factual basis."""

from dataclasses import replace
from fractions import Fraction
from time import perf_counter

import pytest
from event_context_fixtures import synthetic_context
from test_historical_game import build_historical_input
from test_match_workspace_contracts import _definition, _observed_game, _seat_order, _set_game
from test_observed_game_contracts import declaration_from_historical, observed_plays_from_historical
from whole_game_rollout_oracle import synthetic_view

from skatmind.empirical_tournament_scenarios import (
    FieldFacts,
    FieldPool,
    FieldTable,
    produce_empirical_tournament_money,
)
from skatmind.empirical_tournament_sources import AvailableList, RecordedList, prepare_population
from skatmind.event_context_contracts import (
    TOURNAMENT_RULE,
    CheckpointV1,
    FinancialFactsV1,
    PoolFactV1,
    RuleSourceV1,
)
from skatmind.event_context_sources import recording_version_v1
from skatmind.game_declaration import GameDeclaration
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import (
    clear_match_workspace_slot_v1,
    mark_match_workspace_passed_deal_v1,
    replace_match_workspace_definition_v1,
)
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1
from skatmind.mode_accounting import STANDARD_SOURCE
from skatmind.observed_game_trace import ObservedPlayV1
from skatmind.tournament_money_valuation import ListGame, PoolSchedule, evaluate_tournament_money
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

A, B, C = HOME = ("player-a", "player-b", "player-c")
D, E, F = AWAY = ("d", "e", "f")
PAYOUT = RuleSourceV1(reference="Synthetic six-player prize sheet", edition="1")
SETTINGS = WholeGameRolloutSettingsV1(random_seed=1, requested_worlds=4)
DOCUMENT = build_match_workspace_persistence_document_v1


def settled(definition, pos, declarer_seat):
    data = build_historical_input(declarer_player_id=HOME[declarer_seat])
    seats = dict(zip(HOME, _seat_order(definition, pos), strict=True))
    return _observed_game(definition, match_position=pos, game_timecode=None,
        declarer_player_id=seats[data["declarer_player_id"]],
        declaration=declaration_from_historical(data),
        original_skat=data["skat"], discarded_cards=data["discarded_cards"],
        plays=tuple(replace(p, player_id=seats[p.player_id])
                    for p in observed_plays_from_historical(data)))


def current(definition, pos):
    # Record a legal prefix and the actual 22nd play, not a simulated settlement.
    declaration = GameDeclaration("grand", bid_value=24)
    view, hands, skat = synthetic_view(seed=605, remaining=3, declaration=declaration)
    prefix = [p for trick in view.completed_tricks for p in trick.plays]
    own = [p.card for p in prefix if p.player == "me"] + list(hands["me"])
    seats = dict(zip(("right", "me", "left"), _seat_order(definition, pos), strict=True))
    plays = [(seats[p.player], p.card) for p in prefix] + [(seats["me"], "S8")]
    return _observed_game(definition, match_position=pos, game_timecode=None,
        perspective_initial_hand=own, declarer_player_id=seats["me"], declaration=declaration,
        original_skat=skat, discarded_cards=skat, plays=tuple(ObservedPlayV1(
            decision_index=i, player_id=player, card=card, decision_timecode=None)
            for i, (player, card) in enumerate(plays, 1)))


def recording(name, played, *, decision=None, **metadata):
    definition = _definition(match_id=name, external_match_id=metadata.pop("external_match_id",
        "external-" + name), perspective_player_id=B, played_at=(
        "2026-10-01T08:00:00Z" if decision else "2026-09-01T08:00:00Z"), **metadata)
    workspace = create_match_workspace_v1(definition)
    for pos in range(1, 37):
        if pos != decision and pos not in played:
            workspace = mark_match_workspace_passed_deal_v1(workspace, match_position=pos,
                game_timecode=None, expected_revision=workspace.revision).workspace
    for pos, seat in played.items():
        workspace = _set_game(workspace, settled(definition, pos, seat))
    if decision:
        workspace = _set_game(workspace, current(definition, decision))
    return DOCUMENT(workspace)


def evidence(document):
    return RecordedList(document, AvailableList(recording_version_v1(document),
        "2026-09-02T08:00:00Z", "Synthetic dated complete list archive", TOURNAMENT_RULE,
        "tournament", 1))


@pytest.fixture(scope="module")
def donors():
    return (evidence(recording("donor-1", {3: 0, 35: 0, 36: 1})),
            evidence(recording("donor-2", {6: 1, 34: 0, 35: 1})))


@pytest.fixture(scope="module")
def target():
    return recording("target", {**dict.fromkeys((3, 6, 9, 12), 1),
                                **dict.fromkeys(range(1, 23, 3), 0)}, decision=33)


def pool(name, members, awards):
    return FieldPool(PoolSchedule(PoolFactV1(pool_id=name, participation="yes", entitlement="yes"),
        len(members), awards), members, members)


def basis(doc, pos=33):
    return FieldFacts(source=recording_version_v1(doc), event_id="synthetic-event",
        series_id="synthetic-series",
        game_position=pos, decision_index=22, available_at="2026-10-01T07:30:00Z",
        reference="Synthetic single-series entry sheet and pre-drawn tie priority",
        series_count=1, tables=(FieldTable("home", HOME), FieldTable("away", AWAY)),
        pools=(pool("base", HOME + AWAY, (3000, 1500, 800, 400, 100, 0)),
               pool("plus", (B, C, D), (600, 200, 0))),
        payout_source=PAYOUT, transfer_cents=0, other_charge_cents=0)


def event(doc):
    context = synthetic_context(doc, checkpoint=False)
    return replace(context, terms=(replace(context.terms[0], platform="euroskat", version=2,
        financial=FinancialFactsV1(currency="EUR", fee_source=STANDARD_SOURCE)),))


def run(doc, sources, *, pos=33, **kwargs):
    values = dict(context=event(doc), game_position=pos, decision_index=22, field=basis(doc, pos),
                  sources=sources, settings=SETTINGS)
    return produce_empirical_tournament_money(doc, **(values | kwargs))


def test_recorded_sources_to_joint_money(target, donors, record_property, monkeypatch):
    from skatmind import empirical_tournament_sources as adapter

    read_sources = []
    extract = adapter.build_recording_facts_v1

    def counted(doc, **kwargs):
        read_sources.append((doc.workspace.match_definition.match_id,
                             kwargs.get("through_position", 36)))
        return extract(doc, **kwargs)

    monkeypatch.setattr(adapter, "build_recording_facts_v1", counted)
    start = perf_counter()
    result = run(target, donors)
    record_property("complete_path_ms", (perf_counter() - start) * 1000)
    record_property("source_preparation_ms", result.source_preparation_ms)
    record_property("preparation_units", result.work.preparation_units)
    assert sorted(read_sources) == [("donor-1", 36), ("donor-2", 36), ("target", 32)]
    assert result.status == "complete", result.reasons
    assert result.prefix_points == (160, 8, 160)
    assert result.prefix.prepared.own_losses == 4
    assert result.work.sampled_worlds == result.work.materialized_worlds == 4
    assert (result.work.card_transitions, result.work.terminal_evaluations) == (108, 12)
    assert result.modeled_tables == ("away", "home")
    assert not result.population.excluded and len(result.population.donors) == 2
    # Independently tabulated actual donor settlements in canonical place order.
    passed = ListGame(None, None)
    suffixes = {
        "donor-1": (passed, ListGame(C, 48), ListGame(B, -144)),
        "donor-2": (ListGame(B, 48), ListGame(A, -144), passed),
    }
    suffix_points = {"donor-1": (40, -194, 138), "donor-2": (-194, 138, 40)}
    whole_points = {"donor-1": (138, -194, 138), "donor-2": (-154, -56, 80)}
    current_outcomes = {"S10": (-96, -96, 48, -96), "S8": (72, -96, -96, -96),
                        "H9": (48, 48, 48, 48)}
    for card, valued in zip(result.candidates, result.comparison.candidates, strict=True):
        assert len(card.worlds) == len({w.world_id for w in card.worlds}) == 4
        prize = fees = 0
        for i, (world, row) in enumerate(zip(card.worlds, valued.outcomes, strict=True)):
            remote, home = result.draws[i]
            leaf, = world.continuations
            assert row.weight == Fraction(1, 4) and leaf.probability == 1
            assert leaf.future_games == suffixes[home]
            score = current_outcomes[card.name][i]
            assert world.current_game == ListGame(B, score)
            a, b, c = suffix_points[home]
            a += 160 + 40 * (score < 0)
            c += 160 + 40 * (score < 0)
            b += 8 + score + (50 if score > 0 else -50)
            d, e, f = whole_points[remote]
            assert row.final_points == b
            assert [s.other_scores for s in leaf.standings] == [(a, c, d, e, f), (c, d)]
            # Ties: synthetic priority is A,B,C,D,E,F and B,C,D respectively.
            base_ahead = sum(x > b for x in (a, c, d, e, f)) + (a == b)
            award = (3000, 1500, 800, 400, 100, 0)[base_ahead]
            plus = (600, 200, 0)[sum(x > b for x in (c, d))]
            losses = (score < 0) + (home == "donor-1")
            fee = (0, 100, 400)[losses]  # Fifth and sixth personal losses.
            assert dict(row.awards_cents) == {"base": award, "plus": plus}
            assert row.final_own_losses == 4 + losses
            assert (row.money.loss_fee_cents, row.money.net_cents) == (fee, award + plus - fee)
            prize += award + plus
            fees += fee
        assert (valued.expected.prize_cents, valued.expected.loss_fee_cents,
                valued.expected.net_cents) == tuple(Fraction(x, 4) for x in
                                                     (prize, fees, prize-fees))
    assert any(row.final_own_losses == 6
               for c in result.comparison.candidates for row in c.outcomes)
    assert result.comparison.ranking == (("H9",), ("S10",), ("S8",))
    record_property("draws", str(result.draws))
    record_property("money", str([(c.name, c.expected) for c in result.comparison.candidates]))


def test_common_seed_order_and_later_actual_results(target, donors):
    base = run(target, donors)
    assert base.draws == (("donor-2", "donor-2"), ("donor-2", "donor-1"),
                          ("donor-1", "donor-2"), ("donor-1", "donor-1"))
    permuted = run(target, donors[::-1], candidate_order=("H9", "S8", "S10"))
    assert permuted == base
    changed = DOCUMENT(_set_game(target.workspace,
        settled(target.workspace.match_definition, 36, 1)))
    after = run(changed, donors)
    assert base.draws == after.draws
    assert after.comparison.candidates == base.comparison.candidates
    assert after.comparison.basis.scenario_set_id != base.comparison.basis.scenario_set_id
    with pytest.raises(ValueError, match="exact tournament prefix"):
        evaluate_tournament_money(after.prefix, base.comparison.basis, base.candidates)
    with pytest.raises(ValueError, match="exact Match decision"):
        run(changed, donors, field=basis(target))
    revised = replace(basis(target), reference="Corrected dated field sheet")
    other = run(target, donors, field=revised)
    assert other.comparison.basis != base.comparison.basis
    with pytest.raises(ValueError, match="complete world and monetary basis"):
        evaluate_tournament_money(base.prefix, other.comparison.basis, base.candidates)


def test_identical_values_retain_occurrences_and_single_donor_weight(target, donors):
    sample = run(target, (donors[0], donors[0]))
    assert sample.population.unique_donor_count == sample.population.excluded_source_count == 1
    assert sample.draws == (("donor-1", "donor-1"),) * 4
    h9 = next(c for c in sample.comparison.candidates if c.name == "H9")
    assert len({row.money for row in h9.outcomes}) == 1
    assert len({row.world_id for row in h9.outcomes}) == 4
    assert [r.weight for r in h9.outcomes] == [Fraction(1, 4)] * 4


def test_game_36_and_remote_progress(donors):
    doc = recording("last", {}, decision=36)
    facts = basis(doc, 36)
    home, away = facts.tables
    completed = replace(away, through=36, points=(100, 50, -70))
    end = run(doc, (), pos=36, field=replace(facts, tables=(home, completed)))
    assert end.status == "complete" and end.modeled_tables == ()
    assert end.population.unique_donor_count == 0 and end.draws == ((),) * 4
    for card in end.candidates:
        for w in card.worlds:
            leaf, = w.continuations
            assert leaf.future_games == ()
            assert leaf.standings[0].other_scores[-3:] == completed.points
    remote = replace(facts, tables=(home, replace(away, through=35, points=(100, 50, -70))))
    assert run(doc, (), pos=36, field=remote).reasons == ("eligible_donor_population_empty",)
    end = run(doc, donors[:1], pos=36, field=remote)
    assert end.modeled_tables == ("away",) and end.draws == (("donor-1",),) * 4
    assert end.candidates[0].worlds[0].continuations[0].standings[0].other_scores[-3:] == (
        140, -144, -30)


def test_source_identity_and_admission_reasons(target, donors):
    first, second = donors
    doc = second.document
    workspace = doc.workspace
    other_version = DOCUMENT(replace_match_workspace_definition_v1(workspace,
        replace(workspace.match_definition, title="New revision"),
        expected_revision=workspace.revision).workspace)
    copy = evidence(recording("independent-capture", {}, external_match_id="external-target"))
    older_target = DOCUMENT(clear_match_workspace_slot_v1(target.workspace, match_position=33,
        expected_revision=target.workspace.revision).workspace)
    collection = (evidence(target), evidence(older_target), copy, first, first, second,
                  evidence(other_version))
    pop = prepare_population(target, collection, work_hook=lambda: None)
    assert [d.evidence for d in pop.donors] == [first.evidence]
    assert sorted(r for _, r in pop.excluded) == [
        "conflicting_revisions", "conflicting_revisions", "duplicate_copy",
        "target_match", "target_match", "target_match"]
    assert pop == prepare_population(target, collection[::-1], work_hook=lambda: None)
    # Neither a shared score trajectory nor identical player IDs establish logical identity.
    identical = evidence(recording("different-match", {3: 0, 35: 0, 36: 1}))
    pop = prepare_population(target, (first, identical), work_hook=lambda: None)
    assert pop.unique_donor_count == 2 and pop.donors[0].games == pop.donors[1].games


@pytest.mark.parametrize(("change", "reason"), [
    (None, "complete_list_availability_missing"),
    ({"available_at": "2026-09-02"}, "complete_list_availability_ambiguous"),
    ({"available_at": "2026-10-01T07:00:01-00:00"}, "complete_list_availability_ambiguous"),
    ({"available_at": "2026-10-01T10:00:00+02:00"}, "not_available_before_cutoff"),
    ({"available_at": "2026-10-02T08:00:00Z"}, "not_available_before_cutoff"),
    ({"available_at": "2026-09-01T07:59:59Z"}, "availability_not_after_start"),
    ({"mode": "cent"}, "incompatible_scoring"),
    ({"scoring_rule": "unknown"}, "incompatible_scoring"),
    ({"series_count": 2}, "unsupported_series_count"),
])
def test_time_and_scoring_admission(target, donors, change, reason):
    first = donors[0]
    src = replace(first, evidence=None if change is None else replace(first.evidence, **change))
    pop = prepare_population(target, (src,), work_hook=lambda: None)
    assert not pop.donors and pop.excluded == ((first.evidence.source, reason),)


def test_source_version_platform_and_unestablished_position(target, donors):
    doc = donors[0].document
    gap = DOCUMENT(clear_match_workspace_slot_v1(doc.workspace, match_position=4,
        expected_revision=doc.workspace.revision).workspace)
    different = evidence(recording("not-euroskat", {}, game_platform="Unknown"))
    partial = DOCUMENT(_set_game(doc.workspace, _observed_game(
        doc.workspace.match_definition, match_position=4, game_timecode=None)))
    game = doc.workspace.slots[2].observed_game
    unsettled = DOCUMENT(_set_game(doc.workspace, _observed_game(doc.workspace.match_definition,
        match_position=3, game_timecode=None, declaration=game.declaration,
        declarer_player_id=game.declarer_player_id, plays=game.plays,
        discarded_cards=game.discarded_cards, original_skat=None)))
    for src, reason in ((replace(donors[0], document=gap), "availability_source_mismatch"),
                        (evidence(gap), "position_4:missing"),
                        (evidence(partial), "position_4:unfinished"),
                        (evidence(unsettled), "position_3:unsettled"),
                        (different, "unsupported_platform_or_format")):
        pop = prepare_population(target, (src,), work_hook=lambda: None)
        assert pop.excluded == ((recording_version_v1(src.document), reason),)


def test_missing_opponent_prefix_is_not_covered_by_selected_checkpoint(target, donors):
    gap = DOCUMENT(clear_match_workspace_slot_v1(target.workspace, match_position=3,
        expected_revision=target.workspace.revision).workspace)
    context = replace(event(gap), checkpoints=(CheckpointV1(through_position=32,
        own_losses=4, personal_points=8, provenance="Synthetic payee-only score"),))
    answer = run(gap, donors, context=context)
    assert answer.reasons == (f"opponent_prefix:{A}:position_3:missing",
                              f"opponent_prefix:{C}:position_3:missing")
    assert answer.comparison is None and answer.work.sampled_worlds == 0


def test_field_missing_future_unknown_edition_and_format(target, donors):
    field = basis(target)
    for facts, reason in ((None, "field_facts_missing"), (replace(field, series_count=2),
            "unsupported_series_count"), (replace(field, tables=(), pools=()),
            "current_table_places_missing"), (replace(field, available_at="2026-10-02T00:00:00Z"),
            "field_not_available_at_cutoff")):
        answer = run(target, donors, field=facts)
        assert answer.reasons == (reason,) and answer.comparison is None
    base, plus = field.pools
    unknown = replace(base, members=None, priority=None)
    denied = replace(plus, schedule=PoolSchedule(
        replace(plus.schedule.membership, entitlement="no"), 3, None), members=None, priority=None)
    answer = run(target, donors, field=replace(field, pools=(unknown, denied)))
    assert answer.status == "unavailable" and answer.reasons == ("base:standing_missing",)
    assert not answer.comparison.ranking
    for c in answer.comparison.candidates:
        assert c.expected.net_cents is None and c.expected.loss_fee_cents is not None
        for row in c.outcomes:
            assert dict(row.awards_cents) == {"base": None, "plus": 0}
    unknown = replace(plus, schedule=replace(plus.schedule,
        membership=replace(plus.schedule.membership, entitlement="unknown")))
    ctx = event(target)
    ctx = replace(ctx, terms=(replace(ctx.terms[0], mode="tournament_cent"),))
    answer = run(target, donors, context=ctx, field=replace(field, pools=(base, unknown)))
    assert answer.reasons == ("plus:entitlement_unknown", "tournament_side_unresolved")
    assert not answer.comparison.ranking
    answer = run(target, donors, field=replace(field, payout_source=None))
    assert answer.reasons == ("base:incomplete_schedule", "plus:incomplete_schedule")
    answer = run(target, donors, field=replace(field, transfer_cents=None, other_charge_cents=None))
    assert answer.reasons == ("future_charge_unknown", "future_transfer_unknown")
    assert answer.comparison.candidates[0].expected.prize_cents is not None


def test_target_start_is_required_and_field_facts_cannot_follow_it(target, donors):
    workspace = target.workspace
    missing = DOCUMENT(replace_match_workspace_definition_v1(workspace,
        replace(workspace.match_definition, played_at=None),
        expected_revision=workspace.revision).workspace)
    assert run(missing, donors).reasons == ("target_cutoff_missing",)
    # Same-instant field evidence is allowed; even a sub-microsecond later is not.
    facts = replace(basis(target), available_at="2026-10-01T08:00:00.0000001Z")
    assert run(target, donors, field=facts).reasons == ("field_not_available_at_cutoff",)


def test_omitted_pool_uses_frozen_personal_membership(target, donors):
    field = basis(target)
    base, plus = field.pools
    ctx = event(target)
    terms, = ctx.terms
    for entitlement in ("no", "unknown"):
        cutoff_member = replace(plus.schedule.membership, entitlement=entitlement)
        context = replace(ctx, terms=(replace(terms, financial=replace(terms.financial,
            pools=(cutoff_member,), provenance="Synthetic recorded entry facts")),))
        answer = run(target, donors, context=context, field=replace(field, pools=(base,)))
        assert bool(answer.comparison.ranking) == (entitlement == "no")
        for card in answer.comparison.candidates:
            for row in card.outcomes:
                assert dict(row.awards_cents)["plus"] == (0 if entitlement == "no" else None)
                assert dict(row.awards_cents)["base"] is not None


def test_equal_scores_need_bound_tie_facts(donors):
    doc = recording("last-tie", {}, decision=36)
    field = basis(doc, 36)
    home, away = field.tables
    field = replace(field, tables=(home, replace(away, through=36, points=(98, -146, 122))))
    for priority in (None, HOME + AWAY, AWAY + HOME):
        base, plus = field.pools
        answer = run(doc, (), pos=36, field=replace(field, pools=(
            replace(base, priority=priority), plus)))
        h9 = next(c for c in answer.comparison.candidates if c.name == "H9")
        if priority is None:
            assert answer.reasons == ("base:unresolved_tie",) and not answer.comparison.ranking
            assert h9.expected.loss_fee_cents == 0 and h9.expected.net_cents is None
        else:
            assert answer.status == "complete"
            assert dict(h9.outcomes[0].awards_cents)["base"] == (
                1500 if priority == HOME + AWAY else 800)


def test_cancelled_partial_and_timed_out_never_value_a_subset(target, donors):
    answer = run(target, donors, cancelled=lambda: True)
    assert answer.status == "cancelled" and answer.comparison is None
    ticks = iter(range(1000))
    answer = run(target, donors, settings=replace(SETTINGS, wall_clock_timeout_ms=2),
                 clock=lambda: next(ticks) / 1000)
    assert answer.status == "timeout" and not answer.candidates
    answer = run(target, donors, settings=replace(SETTINGS, max_preparation_work=20))
    assert answer.reasons == ("preparation_budget_exhausted",) and not answer.draws
    answer = run(target, donors, settings=replace(SETTINGS, max_card_transitions=29))
    assert answer.reasons == ("transition_budget_exhausted",)
    assert len(answer.draws) == 1 and answer.work.card_transitions == 29
    assert answer.status == "partial" and not answer.candidates and answer.comparison is None


def test_finite_structural_bounds_and_contradictory_field(target, donors):
    field = basis(target)
    with pytest.raises(ValueError, match="128"):
        run(target, donors * 65)
    with pytest.raises(ValueError, match="Duplicate"):
        replace(field, tables=field.tables*2)
    with pytest.raises(ValueError, match="Tie priority"):
        replace(field.pools[0], priority=HOME)
    with pytest.raises(ValueError, match="substitute"):
        run(target, donors, field=replace(field, tables=(replace(field.tables[0], through=36),
                                                         field.tables[1])))
    with pytest.raises(ValueError, match="permute"):
        run(target, donors, candidate_order=("S8",))


def test_cancellation_at_valuation_discards_even_complete_draws(target, donors, monkeypatch):
    import skatmind.empirical_tournament_scenarios as producer

    valuing = False

    def valuation(*args, **kwargs):
        nonlocal valuing
        valuing = True
        return evaluate_tournament_money(*args, **kwargs)

    monkeypatch.setattr(producer, "evaluate_tournament_money", valuation)
    answer = run(target, donors, cancelled=lambda: valuing)
    assert len(answer.draws) == 4 and answer.work.terminal_evaluations == 12
    assert answer.status == "cancelled" and not answer.candidates and answer.comparison is None
