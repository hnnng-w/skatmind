"""Literal Hand observations and their shared complete-deal projection boundary."""

from dataclasses import replace

import pytest
from test_historical_game import build_historical_input
from test_learning_corpus_human_evidence import _store
from test_learning_dataset_v2 import _dataset
from test_match_workspace_contracts import _definition, _observed_game, _set_game
from test_observed_game_contracts import declaration_from_historical, observed_plays_from_historical

from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    MatchHistoricalAnalysisOptionsV1,
)
from skatmind.match_capture_position_view import build_match_capture_position_view_v1
from skatmind.match_decision_analysis import build_match_decision_position_request_v1
from skatmind.match_decision_review_preparation import build_match_decision_review_preparation_v1
from skatmind.match_historical_analysis import execute_match_historical_analysis_v1
from skatmind.match_historical_materialization import materialize_match_observed_game_historical_v1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_materialization import build_match_workspace_materialization_v1
from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1
from skatmind.match_workspace_progress import build_match_workspace_progress_v1
from skatmind.observed_game_evidence import (
    ObservedGameEvidenceSummaryV1,
    build_observed_game_evidence_summary_v1,
)


def hand_workspace(*, discards=None, hand=True, skat=True, bid=True, count=30, time=True):
    definition = _definition(played_at="2026-08-09T18:00:00Z" if time else None)
    data = build_historical_input(game_type="grand", hand_game=hand, declarer_player_id="player-a")
    declaration = declaration_from_historical(data)
    if not bid:
        declaration = replace(declaration, bid_value=None)
    game = _observed_game(definition, match_position=3, game_id="derived-hand",
        declarer_player_id=data["declarer_player_id"], declaration=declaration,
        original_skat=data["skat"] if skat else None, discarded_cards=discards,
        plays=observed_plays_from_historical(data, count=count))
    return _set_game(create_match_workspace_v1(definition), game)


@pytest.mark.parametrize("discards", (None, ()))
def test_hand_shared_consumers_keep_literal_source_and_information_boundaries(discards):
    workspace = hand_workspace(discards=discards)
    source = build_match_workspace_persistence_document_v1(workspace)
    before = source.to_dict()
    evidence = build_observed_game_evidence_summary_v1(workspace.slots[2].observed_game)
    assert evidence.complete_initial_deal_reconstructable
    assert evidence.discarded_cards_known is (discards is not None)
    assert build_match_workspace_progress_v1(workspace).complete_initial_deal_ready_game_count == 1
    view = build_match_capture_position_view_v1(workspace, match_position=3)
    assert view.evidence_summary == evidence
    result = build_match_workspace_materialization_v1(workspace)
    assert result.historical_game_count == result.training_record_count == 1
    assert result.training_source_collection.records[0].historical_game.discarded_cards == ()
    preparation = build_match_decision_review_preparation_v1(workspace, match_position=3)
    assert preparation.prepared_decision_count == 30
    for snapshot in preparation.snapshots:
        assert snapshot.visible_state.skat_visibility == "unknown"
        assert snapshot.visible_state.known_skat_cards == ()
    options = MatchDecisionAnalysisOptionsV1()
    request = build_match_decision_position_request_v1(workspace, match_position=3,
        decision_index=1, options=options).request.to_dict()
    assert request["document"]["skat"] == []
    assert request["document"]["skat_visibility"] == "unknown"
    without_skat = build_match_decision_position_request_v1(
        hand_workspace(discards=discards, skat=False), match_position=3,
        decision_index=1, options=options).request.to_dict()
    assert request == without_skat
    snapshot = build_learning_corpus_match_snapshot_v1(source)
    dataset = _dataset(_store(snapshot, current=(snapshot,)))
    assert len(dataset.records) == 30
    for row in dataset.records:
        visible = row.decision_state.to_dict()["visible_state"]
        assert visible["skat_visibility"] == "unknown"
        assert visible["known_skat_cards"] == []
    assert build_match_workspace_persistence_document_v1(workspace).to_dict() == before


def test_hand_equivalence_reaches_canonical_requests_training_and_complete_list():
    sources, requests, materials = [], [], []
    for discards in (None, ()):
        workspace = hand_workspace(discards=discards)
        for position in range(1, 37):
            if position != 3:
                workspace = mark_match_workspace_passed_deal_v1(workspace,
                    match_position=position, game_timecode=None,
                    expected_revision=workspace.revision).workspace
        source = build_match_workspace_persistence_document_v1(workspace)
        sources.append(source)
        result = build_match_workspace_materialization_v1(workspace)
        assert result.status == "complete" and result.historical_game_count == 1
        assert result.historical_list_materialization.status == "available"
        materials.append(result)
        execution = execute_match_historical_analysis_v1(workspace, match_position=3,
            options=MatchHistoricalAnalysisOptionsV1(
                decision_snapshots=True, immediate_review=False))
        assert execution.status == "executed"
        requests.append(execution.request.to_dict())
        assert build_match_workspace_persistence_document_v1(workspace) == source
    assert sources[0].content_fingerprint != sources[1].content_fingerprint
    assert sources[0].workspace.slots[2].observed_game.discarded_cards is None
    assert sources[1].workspace.slots[2].observed_game.discarded_cards == ()
    assert requests[0] == requests[1]
    assert materials[0].training_source_collection == materials[1].training_source_collection
    assert (materials[0].historical_list_materialization
            == materials[1].historical_list_materialization)


@pytest.mark.parametrize("options,capability,reason", (
    ({"hand": False}, False, "discarded_cards_unavailable"),
    ({"skat": False}, False, "original_skat_unavailable"),
    ({"bid": False}, True, "declaration_unavailable"),
    ({"count": 27}, False, "incomplete_play_trace"),
    ({"count": 27, "skat": False}, False, "incomplete_play_trace"),
    ({"time": False}, True, None),
))
def test_derived_hand_requirements_and_reason_precedence(options, capability, reason):
    workspace = hand_workspace(**options)
    evidence = build_observed_game_evidence_summary_v1(workspace.slots[2].observed_game)
    assert evidence.complete_initial_deal_reconstructable is capability
    assert not evidence.discarded_cards_known
    result = materialize_match_observed_game_historical_v1(workspace, match_position=3)
    assert result.unavailable_reason == reason


def test_summary_universal_implication_does_not_infer_a_hand_declaration():
    summary = build_observed_game_evidence_summary_v1(hand_workspace().slots[2].observed_game)
    values = summary.to_dict()
    values.pop("observed_game_evidence_version")
    assert ObservedGameEvidenceSummaryV1._from_validated(**values) == summary
    with pytest.raises(ValueError, match="complete Play and Skat"):
        ObservedGameEvidenceSummaryV1._from_validated(**{**values, "original_skat_known": False})
    with pytest.raises(ValueError, match="Discard review"):
        ObservedGameEvidenceSummaryV1._from_validated(
            **{**values, "discard_review_reconstructable": True})


def test_invalid_retained_nonempty_hand_discards_are_validated_before_projection():
    workspace = hand_workspace()
    object.__setattr__(workspace.slots[2].observed_game, "discarded_cards", ("H7", "D7"))
    with pytest.raises(ValueError):
        materialize_match_observed_game_historical_v1(workspace, match_position=3)
