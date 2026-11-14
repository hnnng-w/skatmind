from dataclasses import replace

import pytest
from event_context_fixtures import synthetic_context, synthetic_match

from skatmind.event_context_contracts import (
    CENT_RULE,
    AmountV1,
    CheckpointV1,
    FinancialFactsV1,
    ParticipantMapV1,
    RecordingKeyV1,
    RuleSourceV1,
)
from skatmind.event_context_operations import set_event_checkpoint_v1, set_event_terms_v1
from skatmind.event_context_projection import (
    OutcomeFactV1,
    preparation_is_current_v1,
    prepare_event_context_v1,
)
from skatmind.event_context_sources import build_recording_facts_v1, recording_version_v1


@pytest.fixture
def scenario():
    document = synthetic_match()
    context = synthetic_context(document)
    facts = build_recording_facts_v1(document, decision_position=25)
    return context, facts


def prepare(context, facts, game=26, **kwargs):
    return prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                    game_position=game, **kwargs)


def test_checkpoint_continuation_counts_only_established_later_result_once(scenario):
    context, facts = scenario
    before = prepare(context, facts, 25, decision_index=1)
    after = prepare(context, facts)
    assert (before.personal_points, before.own_losses,
            before.remaining_including_current) == (780, 3, 12)
    delta, losses = after.basis[24].contribution(context)
    assert (delta, losses) == (40, 0)
    assert (after.personal_points, after.own_losses) == (780 + delta, 3 + losses)
    assert after.status == "ready" and after.established_through == 25
    assert after == prepare(context, facts)
    assert before.actor_id != before.selected_participant_id
    assert before.financial_missing  # Financial unknowns do not block score readiness.


@pytest.mark.parametrize("game", [1, 12, 24])
def test_later_anchor_outcomes_and_terms_never_enter_earlier_decision(scenario, game):
    context, facts = scenario
    later = replace(context.terms[0], from_position=25,
        financial=FinancialFactsV1(currency="EUR"))
    revised = set_event_terms_v1(context, later, expected_revision=0, correction=False,
                                provenance="Terms changed from game 25")
    value = prepare(revised, facts, game)
    assert value.checkpoint is None
    assert value.terms == context.terms[0]
    assert all(row.fact.position < game for row in value.basis)
    assert value.personal_points == 0
    assert value.status == ("ready" if game == 1 else "incomplete")


@pytest.mark.parametrize("status", ["missing", "unfinished", "unsettled", "passed"])
def test_position_kinds_negative_score_and_uncovered_gaps(scenario, status):
    context, facts = scenario
    context = replace(context, checkpoints=(replace(context.checkpoints[0], personal_points=-90),))
    facts = replace(facts, outcomes=tuple(replace(row, status=status, declarer_id=None,
        outcome=None, settlement_score=None, evidence_fingerprint=None)
        if row.position == 25 else row
        for row in facts.outcomes))
    value = prepare(context, facts)
    assert (value.personal_points, value.own_losses) == (-90, 3)
    assert value.status == ("ready" if status == "passed" else "incomplete")
    assert value.established_through == (25 if status == "passed" else 24)
    if status != "passed":
        assert value.unresolved[0].fact.status == status


@pytest.mark.parametrize("own", [True, False])
def test_only_own_lost_declarer_games_advance_loss_count(scenario, own):
    context, facts = scenario
    declarer = context.selected_participant_id if own else next(
        player for player in context.participant_ids if player != context.selected_participant_id)
    loss = OutcomeFactV1(position=25, status="settled", declarer_id=declarer,
        outcome="declarer_loss", settlement_score=-48, evidence_fingerprint="a" * 64)
    facts = replace(facts, outcomes=tuple(loss if row.position == 25 else row
                                        for row in facts.outcomes))
    value = prepare(context, facts)
    assert value.own_losses == 3 + int(own)
    assert value.personal_points == 780 + (-98 if own else 40)


def test_overlapping_cumulative_anchors_and_backfill_are_not_added(scenario):
    context, facts = scenario
    derived = prepare(context, facts)
    later = CheckpointV1(through_position=25, personal_points=derived.personal_points,
        own_losses=derived.own_losses, provenance="Confirmed later total")
    context = set_event_checkpoint_v1(context, later, expected_revision=0)
    assert prepare(context, facts).personal_points == derived.personal_points
    assert prepare(context, facts).disagreements == ()
    wrong = replace(later, personal_points=later.personal_points + 10)
    context = set_event_checkpoint_v1(context, wrong, expected_revision=1)
    conflict = prepare(context, facts)
    assert conflict.status == "conflict"
    assert conflict.personal_points == wrong.personal_points
    assert conflict.disagreements[0].derived_points == later.personal_points
    # Earlier missing history is not fabricated to compare the position-24 anchor.
    assert len(conflict.disagreements) == 1


def test_explicit_shared_source_mapping_deduplicates_and_detects_contradictions(scenario):
    context, facts = scenario
    source = replace(facts.source, source=RecordingKeyV1(family="session", product_id="session-25"))
    players = context.bindings[0].players
    binding = replace(context.bindings[0], attached_source=source, game_position=25,
                      players=(*players[1:], players[0]))
    context = replace(context, bindings=(*context.bindings, binding))
    row = replace(facts.outcomes[24], position=1)
    session = replace(facts, source=source, outcomes=(row,), decisions=(),
                      player_ids=tuple(item.source_player_id for item in binding.players))
    value = prepare_event_context_v1(context, (facts, session), target=facts.source.source,
                                    game_position=26)
    expected = prepare(synthetic_context(synthetic_match()), facts).personal_points
    assert value.personal_points == expected
    assert len(value.basis[24].sources) == 2
    session = replace(session, outcomes=(replace(row, evidence_fingerprint="b" * 64),))
    conflict = prepare_event_context_v1(context, (facts, session), target=facts.source.source,
                                       game_position=26)
    assert conflict.status == "conflict"
    with pytest.raises(ValueError):
        prepare_event_context_v1(context, (facts, replace(session,
            player_ids=("same-name-a", "same-name-b", "same-name-c"))),
            target=facts.source.source, game_position=26)


def test_missing_source_and_stale_preparation_are_explicit(scenario):
    context, facts = scenario
    value = prepare(context, facts, 25, decision_index=1)
    assert preparation_is_current_v1(value, context, (facts,))
    assert not preparation_is_current_v1(value, context, (
        replace(facts, source=replace(facts.source, content_fingerprint="f" * 64)),))
    assert prepare_event_context_v1(context, (), target=facts.source.source,
        game_position=25, decision_index=1).status == "source_unavailable"
    changed = replace(facts, source=replace(facts.source, content_fingerprint="f" * 64))
    historical = prepare_event_context_v1(context, (changed,), target=facts.source.source,
        game_position=25, decision_index=1, expected_source=facts.source)
    assert historical.status == "source_unavailable" and historical.target_source is None


def test_exact_money_unknowns_and_mode_source_compatibility(scenario):
    context, _ = scenario
    assert AmountV1.parse("0.25") == AmountV1(numerator=1, denominator=4)
    for value in ("nan", "-1", "1e2", 0.5, "0,5"):
        with pytest.raises(ValueError):
            AmountV1.parse(value)
    with pytest.raises(ValueError, match="currency"):
        FinancialFactsV1(entry_paid=AmountV1.parse("5.00"), provenance="receipt")
    with pytest.raises(ValueError, match="Cent-Skat"):
        replace(context, checkpoints=(), terms=(replace(context.terms[0], mode="cent",
                                                       scoring_rule=CENT_RULE),))
    with pytest.raises(ValueError, match="tariff"):
        replace(context.terms[0], financial=FinancialFactsV1(currency="EUR", cent_tariff="1",
                                                           provenance="Confirmed"))
    terms = replace(context.terms[0], mode="tournament_cent",
        financial=FinancialFactsV1(currency="EUR", cent_tariff="1/4", provenance="Confirmed"))
    assert replace(context, terms=(terms,)).tournament


def test_strict_contract_rejects_unknown_fields_bool_counts_and_invalid_binding(scenario):
    context, _ = scenario
    value = context.to_dict()
    value["extra"] = 1
    with pytest.raises(ValueError):
        type(context).from_dict(value)
    with pytest.raises(ValueError):
        replace(context.checkpoints[0], own_losses=True)
    with pytest.raises(ValueError):
        replace(context.bindings[0], players=(ParticipantMapV1(
            source_player_id="foreign", event_player_id="foreign"),))


def test_real_complete_trace_without_skat_is_unsettled_not_a_result():
    document = synthetic_match(missing_skat=True)
    facts = build_recording_facts_v1(document)
    assert facts.outcomes[24].status == "unsettled"
    assert facts.source == recording_version_v1(document)


def test_rule_source_requires_identified_edition():
    with pytest.raises(ValueError):
        RuleSourceV1(reference="Confirmed provider page", edition="")
