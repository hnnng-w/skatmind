from dataclasses import replace

import pytest
from event_context_fixtures import synthetic_context, synthetic_match
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_game import build_historical_input
from test_session_transitions import _complete_retrospective_session

from skatmind.event_context_contracts import CENT_RULE, EventContextV1, EventTermsV1, RuleSourceV1
from skatmind.event_context_projection import prepare_event_context_v1
from skatmind.event_context_sources import (
    build_event_binding_v1,
    build_recording_facts_v1,
    recording_version_v1,
    validate_session_match_seats_v1,
)
from skatmind.session_persistence_codec import build_session_persistence_document_v1


@pytest.mark.parametrize("builder", [build_historical_input, build_concession_prefix,
                                    build_defender_concession_prefix])
def test_session_established_paths_reuse_existing_outcome_without_analysis(builder, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Context preparation must not execute Card analysis or proof search")
    monkeypatch.setattr("skatmind.historical_game.adjudicate_historical_defender_open_play",
                        forbidden)
    state = _complete_retrospective_session(builder())
    document = build_session_persistence_document_v1(state)
    facts = build_recording_facts_v1(document, selected_player_id="player-a", decision_position=1)
    assert facts.outcomes[0].status == "settled"
    assert facts.source == recording_version_v1(document)
    assert facts.outcomes[0].settlement_score != 0


def test_genuine_match_session_same_event_position_has_one_contribution():
    match = synthetic_match(settled_position=27)
    event = synthetic_context(match)
    session = build_session_persistence_document_v1(_complete_retrospective_session(
        build_historical_input(game_type="grand", hand_game=False)))
    binding = build_event_binding_v1(session, game_position=27, selected_player_id="player-a")
    validate_session_match_seats_v1(event, session, binding, match)
    event = replace(event, bindings=(*event.bindings, binding))
    match_facts = build_recording_facts_v1(match)
    session_facts = build_recording_facts_v1(session, selected_player_id="player-a")
    value = prepare_event_context_v1(event, (match_facts, session_facts),
        target=match_facts.source.source, game_position=28)
    assert value.basis[26].fact.status == "settled"
    assert len(value.basis[26].sources) == 2
    assert value.status == "incomplete"  # Positions 25/26 were never supplied.
    with pytest.raises(ValueError, match="rotation"):
        validate_session_match_seats_v1(event, session, replace(binding, game_position=26), match)


def test_session_cent_context_keeps_tournament_score_not_applicable():
    session = build_session_persistence_document_v1(_complete_retrospective_session(
        build_historical_input()))
    binding = build_event_binding_v1(session, game_position=2, selected_player_id="player-a")
    context = EventContextV1(event_id="cent-event", series_id="confirmed-cent-series",
        event_name="Actual Cent table", series_name="Confirmed block",
        participant_ids=("player-a", "player-b", "player-c"), selected_participant_id="player-a",
        bindings=(binding,), terms=(EventTermsV1(from_position=1, mode="cent",
            scoring_rule=CENT_RULE, scoring_source=RuleSourceV1(
                reference="Confirmed Cent-Skat page", edition="2026-11-14")),))
    facts = build_recording_facts_v1(session, decision_position=2, selected_player_id="player-a")
    value = prepare_event_context_v1(context, (facts,), target=facts.source.source,
                                      game_position=2, decision_index=1)
    assert value.status == "not_applicable"
    assert value.personal_points is value.own_losses is value.remaining_including_current is None
    assert "cent_tariff" in value.financial_missing


def test_decision_preparation_does_not_consume_current_game_outcome():
    document = synthetic_match()
    facts = build_recording_facts_v1(document, through_position=24, decision_position=25)
    assert len(facts.outcomes) == 24
    assert len(facts.decisions) == 30
    assert facts.decisions[0].actor_id == "player-b"
    value = prepare_event_context_v1(synthetic_context(document), (facts,),
        target=facts.source.source, game_position=25, decision_index=1)
    assert all(row.fact.position < 25 for row in value.basis)


def test_partial_contradictory_recording_cannot_be_hidden_by_a_settled_surface():
    from skatmind.event_context_projection import OutcomeFactV1

    match = synthetic_match(settled_position=27)
    event = synthetic_context(match)
    session = build_session_persistence_document_v1(_complete_retrospective_session(
        build_historical_input(game_type="grand", hand_game=False)))
    binding = build_event_binding_v1(session, game_position=27, selected_player_id="player-a")
    event = replace(event, bindings=(*event.bindings, binding))
    first = build_recording_facts_v1(match)
    second = build_recording_facts_v1(session, selected_player_id="player-a")
    signature = second.signatures[0]
    second = replace(second, outcomes=(OutcomeFactV1(position=1, status="unfinished"),),
        signatures=(replace(signature, trace_prefixes=("f" * 64,)),))
    value = prepare_event_context_v1(event, (first, second), target=first.source.source,
                                      game_position=28)
    assert value.status == "conflict"
    assert value.basis[26].fact.status == "source_conflict"


def test_disposable_fixture_generator_is_small_reproducible_and_no_clobber(tmp_path, monkeypatch):
    import sys

    from event_context_fixtures import main

    from skatmind.match_workspace_persistence import load_match_workspace_file_v1

    target = tmp_path / "synthetic-event-match.json"
    monkeypatch.setattr(sys, "argv", ["event_context_fixtures.py", "--output", str(target)])
    main()
    loaded = load_match_workspace_file_v1(target).document
    assert loaded == synthetic_match()
    assert sum(slot.slot_kind != "empty" for slot in loaded.workspace.slots) == 1
    original = target.read_bytes()
    with pytest.raises(SystemExit):
        main()
    assert target.read_bytes() == original
