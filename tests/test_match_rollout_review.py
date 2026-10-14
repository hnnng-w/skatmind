"""Synthetic #288 roots; no maintainer recording or preferred winning card."""

import copy
from dataclasses import replace

import pytest
from test_match_workspace_contracts import _definition, _observed_game, _set_game

from skatmind.api.v1 import ExecutionOptionsV1, ResultDocumentV1, execute, parse_request
from skatmind.game_declaration import GameDeclaration
from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    build_match_analysis_report_v1,
)
from skatmind.match_decision_analysis import (
    build_match_decision_position_request_v1,
    execute_match_decision_analysis_v1,
)
from skatmind.match_player_snapshot import MatchParticipantV1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1
from skatmind.observed_game_trace import ObservedPlayV1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

ALEX_HAND = "CK C9 C7 SJ SA S8 HA H8 D10 D7".split()
TRACE = (
    ("bea", "CQ"), ("chris", "CA"), ("alex", "C7"),
    ("chris", "H7"), ("alex", "SJ"), ("bea", "CJ"),
    ("bea", "S10"), ("chris", "SQ"), ("alex", "SA"),
    ("alex", "D7"), ("bea", "DA"), ("chris", "D8"),
    ("bea", "HK"), ("chris", "H10"), ("alex", "H8"),
    ("chris", "SK"), ("alex", "S8"), ("bea", "S9"),
    ("chris", "S7"), ("alex", "HA"), ("bea", "DJ"),
    ("bea", "HJ"), ("chris", "D9"), ("alex", "D10"),
    ("bea", "HQ"), ("chris", "C8"), ("alex", "C9"),
    ("bea", "DQ"), ("chris", "DK"), ("alex", "CK"),
)


def alex_workspace(*, count=30, suffix_variant=False, actual="C7", known_hand=True, bid=18):
    participants = tuple(MatchParticipantV1(player_id=name, player_label=name.title(),
        platform_player_id=None, table_place=f"place_{index}", statistics_snapshot=None)
        for index, name in enumerate(("chris", "alex", "bea"), 1))
    definition = _definition(match_id="synthetic-288", title="Synthetic Hearts review",
        participants=participants, perspective_player_id="alex")
    trace = list(TRACE)
    if suffix_variant:
        # Both remain legal; root prefix/own hand stay identical while future
        # opponent ownership changes (same-suit low cards off lead).
        trace[22] = ("chris", "DQ")
        trace[27] = ("bea", "D9")
    if actual != "C7":
        other = next(index for index, pair in enumerate(trace) if pair == ("alex", actual))
        trace[2], trace[other] = trace[other], trace[2]
    game = _observed_game(definition, match_position=2,
        perspective_initial_hand=ALEX_HAND if known_hand else None,
        declarer_player_id="bea", declaration=GameDeclaration(game_type="hearts", bid_value=bid),
        plays=tuple(ObservedPlayV1(decision_index=index, player_id=player, card=card,
                    decision_timecode=None)
                    for index, (player, card) in enumerate(trace[:count], 1)))
    workspace = create_match_workspace_v1(definition)
    workspace = mark_match_workspace_passed_deal_v1(workspace, match_position=1,
        expected_revision=workspace.revision, game_timecode=None).workspace
    return _set_game(workspace, game)


def rollout_options(objective="played_game_goal", **settings):
    return MatchDecisionAnalysisOptionsV1(recommendation_method="whole_game_rollout",
        use_profile_presets=False, rollout_settings=WholeGameRolloutSettingsV1(
            objective=objective, requested_worlds=2, random_seed=0,
            wall_clock_timeout_ms=30_000, **settings),
        settlement_supplements={"matadors": 1} if objective == "complete_settlement" else {})


def prepared(workspace, *, decision=3, options=None):
    return build_match_decision_position_request_v1(workspace, match_position=2,
        decision_index=decision, options=options or rollout_options()).request


def metrics(result):
    raw = copy.deepcopy(result)
    raw["work"].pop("elapsed_ms")
    return raw


@pytest.mark.parametrize("objective", ("played_game_goal", "complete_settlement"))
def test_partial_complete_and_legal_suffix_have_identical_core_inputs_and_metrics(objective):
    roots, results = [], []
    for workspace in (alex_workspace(count=3), alex_workspace(),
                      alex_workspace(suffix_variant=True), alex_workspace(known_hand=False)):
        request = prepared(workspace, options=rollout_options(objective))
        root = request.to_dict()["document"]
        assert root["current_trick"] == ["CQ", "CA"]
        assert set(root["hand"]) == set(ALEX_HAND)
        assert root["declarer_player"] == "left"
        assert root["player_role"] == "defender" and root["player_position"] == "rearhand"
        assert root["left_hand_size"] == root["right_hand_size"] == 9
        assert root["skat"] == [] and root["skat_visibility"] == "unknown"
        assert root["declarer_points"] == root["defender_points"] == 0
        assert root["completed_tricks"] == [] and root["played_cards"] == []
        source = root.pop("whole_game_rollout_derivation")
        assert source["original_request"]["document"]["game_declaration"]["matadors"] is None
        assert source["policy"] == "reconstructed_match_decision"
        roots.append(root)
        result = execute(request).result.to_dict()["document"]
        assert result["legal_cards"] == ["CK", "C9", "C7"]
        assert result["whole_game_rollout_result"]["status"] == "complete"
        results.append(metrics(result["whole_game_rollout_result"]))
    assert all(root == roots[0] for root in roots)
    assert all(result == results[0] for result in results)


def test_match_execution_retains_typed_report_and_public_roundtrip():
    value = execute_match_decision_analysis_v1(alex_workspace(count=3), match_position=2,
        decision_index=3, options=rollout_options("complete_settlement"))
    assert value.status == "executed"
    replay = execute(parse_request(value.request.to_dict()["document"]))
    replay = replay.result.to_dict()["document"]
    assert metrics(replay["whole_game_rollout_result"]) == metrics(
        value.result.to_dict()["document"]["whole_game_rollout_result"])


@pytest.mark.parametrize("card", ("CK", "C9", "C7"))
def test_actual_card_is_comparison_only(card):
    request = prepared(alex_workspace(count=3)).to_dict()["document"]
    original = execute(parse_request(request)).result.to_dict()["document"]
    request["actual_card_played"] = card
    changed = execute(parse_request(request)).result.to_dict()["document"]
    assert metrics(original["whole_game_rollout_result"]) == metrics(
        changed["whole_game_rollout_result"])
    assert changed["whole_game_rollout_comparison"]["actual_card"] == card


@pytest.mark.parametrize("decision", (1, 2, 5, 10, 24, 30))
@pytest.mark.parametrize("objective", ("played_game_goal", "complete_settlement"))
def test_other_actors_partial_tricks_and_banked_prefix(decision, objective):
    workspace = alex_workspace()
    original = prepared(workspace, decision=decision)
    options = rollout_options(objective)
    if original.document["game_declaration"]["matadors"] is not None:
        options = replace(options, settlement_supplements={})
    request = prepared(workspace, decision=decision, options=options)
    result = execute(request).result.to_dict()["document"]
    assert result["whole_game_rollout_result"]["status"] == "complete"
    assert len(request.document["completed_tricks"]) == (decision - 1) // 3
    assert len(request.document["current_trick"]) == (decision - 1) % 3
    assert result["whole_game_rollout_result"]["local_side"] == (
        "declarer" if TRACE[decision - 1][0] == "bea" else "defenders")


@pytest.mark.parametrize("change", ("hand", "source", "settings", "known_bid", "effective"))
def test_public_derivation_rejects_tampering(change):
    root = prepared(alex_workspace(count=3), options=rollout_options(
        "complete_settlement")).to_dict()["document"]
    source = root["whole_game_rollout_derivation"]
    if change == "hand":
        root["hand"][0] = "C8"
    elif change == "source":
        source["game_id"] = "another-game"
    elif change == "settings":
        root["whole_game_rollout_settings"]["random_seed"] = 9
    elif change == "known_bid":
        source["supplements"]["bid_value"] = 18
    else:
        source["effective_declaration"]["matadors"] = 2
    with pytest.raises(ValueError):
        execute(parse_request(root))


def test_missing_inputs_and_incomplete_execution_have_no_fallback():
    options = rollout_options("complete_settlement")
    for configured, reason in ((replace(options, settlement_supplements={}),
                                "missing_terminal_utility_inputs"),
                               (rollout_options(max_card_transitions=1),
                                "transition_budget_exhausted")):
        value = execute_match_decision_analysis_v1(alex_workspace(count=3), match_position=2,
            decision_index=3, options=configured)
        raw = value.result.to_dict()["document"]
        assert raw["whole_game_rollout_result"]["stop_reason"] == reason
        assert raw["whole_game_rollout_result"]["ranked_cards"] == []
        assert raw["recommendation"]["card"] is None


def test_supplement_provenance_and_known_overwrite_with_recomputed_hash():
    from skatmind.rollout_derivation import rollout_source_fingerprint

    request = prepared(alex_workspace(count=3), options=rollout_options("complete_settlement"))
    executed = execute(request, options=ExecutionOptionsV1(include_provenance=True))
    entries = executed.field_provenance.result.to_dict()["ledger"]["entries"]
    entry = next(row for row in entries if row["field_path"] == "/game_declaration/matadors")
    assert entry["origin"] == "caller_supplied"
    assert any(ref["field_path"] == "/whole_game_rollout_derivation/supplements/matadors"
               for ref in entry["source_references"])
    root = request.to_dict()["document"]
    source = root["whole_game_rollout_derivation"]
    source["supplements"]["bid_value"] = 18
    source["derivation_fingerprint"] = rollout_source_fingerprint(
        "skatmind.rollout.match_derivation.v1",
        {key: value for key, value in source.items() if key != "derivation_fingerprint"})
    with pytest.raises(ValueError, match="missing settlement"):
        execute(parse_request(root))


@pytest.mark.parametrize("change", (
    "position", "party", "metric", "comparison", "source", "fingerprint",
))
def test_typed_report_rejects_cross_source_and_result_tampering(change):
    value = execute_match_decision_analysis_v1(alex_workspace(count=3), match_position=2,
        decision_index=3, options=rollout_options())
    result = value.result.to_dict()["document"]
    if change == "position":
        result["position"]["current_trick"] = []
    elif change == "party":
        result["whole_game_rollout_result"]["local_side"] = "declarer"
    elif change == "metric":
        result["whole_game_rollout_result"]["candidates"][0]["local_success_count"] += 1
    elif change == "comparison":
        result["whole_game_rollout_comparison"]["actual_card"] = "CK"
    elif change == "fingerprint":
        result["whole_game_rollout_result"]["source_fingerprint"] = "0" * 64
    else:
        with pytest.raises(ValueError):
            replace(value, game_id="another-game")
        return
    with pytest.raises(ValueError):
        replace(value, result=ResultDocumentV1(workflow=value.result.workflow, document=result))


def test_unsupported_game_and_unpreparable_actor_remain_distinct():
    from test_match_decision_analysis import _complete_workspace

    unsupported = execute_match_decision_analysis_v1(_complete_workspace(game_type="null"),
        match_position=3, decision_index=1, options=rollout_options())
    assert unsupported.status == "executed"
    assert unsupported.result.document["whole_game_rollout_result"]["stop_reason"] == (
        "unsupported_game_type")
    missing = execute_match_decision_analysis_v1(alex_workspace(count=3, known_hand=False),
        match_position=2, decision_index=3, options=rollout_options())
    assert missing.status == "unavailable" and missing.skipped_reason == "acting_hand_unavailable"


def test_teacher_transfer_rejects_rollout_without_widening_shared_methods():
    from skatmind.learning_corpus_strategy_teacher import _validate_exact_decision_report
    from skatmind.match_analysis_report_source_codec import _resume_options
    from skatmind.match_analysis_report_source_export import (
        build_match_analysis_report_source_export_v1,
    )
    from skatmind.recommendation_workflow import FLAT_RECOMMENDATION_METHODS

    assert "whole_game_rollout" not in FLAT_RECOMMENDATION_METHODS
    report = build_match_analysis_report_v1(execute_match_decision_analysis_v1(
        alex_workspace(count=3), match_position=2, decision_index=3, options=rollout_options()))
    for action in (build_match_analysis_report_source_export_v1, _validate_exact_decision_report):
        with pytest.raises(ValueError, match="support"):
            action(report)
    with pytest.raises(ValueError, match="support"):
        _resume_options(report.value.options.to_dict())


@pytest.mark.parametrize("decision", (1, 2))
def test_authorized_declared_ouvert_hand_keeps_actor_relative_mapping(decision):
    from test_historical_game import build_historical_input
    from test_observed_game_contracts import observed_plays_from_historical

    definition = _definition()
    data = build_historical_input(hand_game=True)
    game = _observed_game(definition, match_position=3,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=data["declarer_player_id"],
        declaration=GameDeclaration(game_type="grand", hand_game=True, ouvert=True,
            schneider_announced=True, schwarz_announced=True, bid_value=18),
        original_skat=data["skat"], discarded_cards=[], plays=observed_plays_from_historical(data))
    value = execute_match_decision_analysis_v1(
        _set_game(create_match_workspace_v1(definition), game),
        match_position=3, decision_index=decision, options=rollout_options())
    assert value.result.document["whole_game_rollout_result"]["status"] == "complete"
    assert value.request.document["public_declarer_cards"]
    assert value.request.document["skat"] == ()
