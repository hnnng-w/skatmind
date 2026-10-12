"""Public flat-review execution and immutable annotation boundaries."""

import copy
import json
import subprocess
import sys
from dataclasses import replace

import pytest

from skatmind.api.v1 import ExecutionOptionsV1, execute, parse_request, serialize_result
from skatmind.errors import SkatMindError
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1
from skatmind.whole_game_rollout_workflow import compare_rollout_actual, serialize_rollout_settings


def opening_request(**settings):
    return {
        "game_type": "clubs", "player_role": "declarer", "declarer_player": "me",
        "player_position": "forehand", "played_cards": [], "declarer_points": 0,
        "defender_points": 0, "sample_count": 100, "random_seed": 0,
        "use_basic_opponent_strategy": True,
        "hand": ["C7", "C8", "C9", "C10", "CJ", "CQ", "CK", "CA", "SA", "S10"],
        "current_trick": [], "completed_tricks": [], "trick_leader": "me", "next_player": "me",
        "left_hand_size": 10, "right_hand_size": 10, "skat": ["H7", "D7"],
        "skat_visibility": "known_to_declarer", "analysis_mode": "post_game_review",
        "actual_card_played": "CJ", "recommendation_method": "whole_game_rollout",
        "whole_game_rollout_settings": serialize_rollout_settings(WholeGameRolloutSettingsV1(
            random_seed=0, requested_worlds=2, wall_clock_timeout_ms=30000, **settings)),
    }


def run(root):
    execution = execute(parse_request(root), options=ExecutionOptionsV1())
    serialize_result(execution)
    return execution.result.to_dict()["document"]


def without_time(result):
    result = copy.deepcopy(result)
    result["work"]["elapsed_ms"] = 0
    return result


def test_public_opening_no_bid_round_trip_and_actual_independence():
    root = opening_request()
    original = copy.deepcopy(root)
    first = run(root)
    assert root == original
    rollout = first["whole_game_rollout_result"]
    assert rollout["status"] == "complete"
    assert rollout["completed_common_worlds"] == 2
    assert first["game_declaration"]["bid_value"] is None
    assert first["game_declaration"]["matadors"] is None
    assert first["analysis_report"] == []
    root["actual_card_played"] = "SA"
    second = run(root)
    assert without_time(rollout) == without_time(second["whole_game_rollout_result"])
    assert first["whole_game_rollout_comparison"]["actual_card"] == "CJ"
    assert second["whole_game_rollout_comparison"]["actual_card"] == "SA"


@pytest.mark.parametrize("settings,reason", [
    ({"objective": "complete_settlement"}, "missing_terminal_utility_inputs"),
    ({"max_card_transitions": 1}, "transition_budget_exhausted"),
    ({"max_preparation_work": 1}, "preparation_budget_exhausted"),
])
def test_unavailable_and_incomplete_never_rank_or_fallback(settings, reason):
    result = run(opening_request(**settings))
    rollout = result["whole_game_rollout_result"]
    assert rollout["stop_reason"] == reason
    assert rollout["ranked_cards"] == rollout["tied_best_cards"] == []
    assert result["recommendation"]["card"] is None
    assert result["whole_game_rollout_comparison"]["status"] == "unavailable"
    assert result["recommendation_method_summary"]["fallback_used"] is False


@pytest.mark.parametrize("key,value", [
    ("requested_worlds", True), ("requested_worlds", 1001), ("random_seed", -1),
    ("wall_clock_timeout_ms", None), ("wall_clock_timeout_ms", 60001),
    ("max_card_transitions", 300001), ("policy_version", 2), ("objective", "win"),
])
def test_strict_settings(key, value):
    root = opening_request()
    root["whole_game_rollout_settings"][key] = value
    with pytest.raises(SkatMindError):
        run(root)


@pytest.mark.parametrize("changes", [
    {"analysis_mode": "live_decision"}, {"recommendation_method": "immediate_expected_value"},
    {"bounded_search_settings": {}}, {"skat_visibility": "known_post_game"},
])
def test_incompatible_methods_modes_and_evidence_rejected(changes):
    root = opening_request()
    root.update(changes)
    with pytest.raises(SkatMindError):
        run(root)


def test_missing_attributed_prefix_is_explicit_unavailable():
    root = opening_request()
    root["hand"].remove("C7")
    root.update(left_hand_size=9, right_hand_size=9)
    result = run(root)["whole_game_rollout_result"]
    assert result["stop_reason"] == "incomplete_public_history"
    assert result["source"] == "flat_decision_input"
    assert result["completed_common_worlds"] == 0 and result["ranked_cards"] == []


def test_missing_matadors_are_not_inferred_for_settlement():
    root = opening_request(objective="complete_settlement")
    root["bid_value"] = 18
    result = run(root)
    assert result["game_declaration"]["matadors"] is None
    assert result["whole_game_rollout_result"]["stop_reason"] == "missing_terminal_utility_inputs"


def test_partial_common_coverage_is_not_a_ranking():
    result = run(opening_request(max_card_transitions=301))
    rollout = result["whole_game_rollout_result"]
    assert rollout["status"] == "partial" and rollout["completed_common_worlds"] == 1
    assert all(c["completed_samples"] == 1 for c in rollout["candidates"])
    assert rollout["ranked_cards"] == [] and result["recommendation"]["card"] is None


def test_public_output_schema_rejects_private_or_misleading_rollout_fields():
    from skatmind.api.v1.schema_validation import validate_output_document
    document = run(opening_request())
    changed = copy.deepcopy(document)
    changed["whole_game_rollout_result"]["candidates"][0]["hidden_hand"] = ["HA"]
    with pytest.raises(SkatMindError):
        validate_output_document(changed)
    changed = copy.deepcopy(document)
    changed["whole_game_rollout_result"]["status"] = "partial"
    with pytest.raises(SkatMindError):
        validate_output_document(changed)
    changed["whole_game_rollout_result"].update(ranked_cards=[], tied_best_cards=[],
                                               recommended_card=None)
    with pytest.raises(SkatMindError):
        validate_output_document(changed)


@pytest.mark.parametrize("objective,values,actual,status,metric,display", [
    ("played_game_goal", ((1, 10, None), (0, 20, None)), "DA",
     "lower_primary_success", "local_success_count", False),
    ("played_game_goal", ((1, 10, None), (1, 12, None)), "S9",
     "lower_secondary_outcome", "total_local_card_point_margin", False),
    ("played_game_goal", ((1, 10, None), (1, 10, None)), "DA",
     "equal_complete_objective", None, True),
    ("complete_settlement", ((1, 12, 24), (1, 10, 48)), "S9",
     "lower_secondary_outcome", "total_local_game_score", False),
    ("complete_settlement", ((1, 10, 48), (1, 12, 48)), "S9",
     "lower_secondary_outcome", "total_local_card_point_margin", False),
])
def test_exact_primary_secondary_and_complete_tie_comparisons(
    objective, values, actual, status, metric, display,
):
    from whole_game_rollout_oracle import small_view

    from skatmind.whole_game_rollout import evaluate_whole_game_rollout_v1
    result = evaluate_whole_game_rollout_v1(small_view()[0], WholeGameRolloutSettingsV1(
        random_seed=0, requested_worlds=1))
    assert tuple(c.card for c in result.candidates) == ("S9", "DA")
    candidates = tuple(replace(candidate, local_success_count=success,
        total_local_card_point_margin=margin, total_local_game_score=score,
        total_declarer_points=60 + margin // 2, total_defender_points=60 - margin // 2)
        for candidate, (success, margin, score) in zip(result.candidates, values, strict=True))
    ranked = sorted(candidates, key=lambda row: row.comparison_key(), reverse=True)
    ties = tuple(c.card for c in ranked if c.comparison_key() == ranked[0].comparison_key())
    result = replace(result, settings=replace(result.settings, objective=objective),
        candidates=candidates, ranked_cards=tuple(c.card for c in ranked),
        tied_best_cards=ties, recommended_card=ties[0])
    comparison = compare_rollout_actual(result, actual)
    assert comparison["status"] == status
    assert comparison["responsible_metric"] == metric
    assert comparison["display_order_only"] is display
    assert comparison["all_primary_success_equal"] == (values[0][0] == values[1][0])


def test_provenance_separates_rollout_from_actual_and_does_not_call_immediate(monkeypatch):
    import skatmind.recommendation_workflow as workflow
    def forbidden(*args, **kwargs):
        raise AssertionError("Rollout must not invoke Immediate or its assessment thresholds")
    monkeypatch.setattr(workflow, "recommend_card_by_expected_value", forbidden)
    execution = execute(parse_request(opening_request()), options=ExecutionOptionsV1(
        include_provenance=True))
    output = serialize_result(execution)
    assert output["document"]["whole_game_rollout_result"]["status"] == "complete"
    assert "field_provenance" in output["document"]


@pytest.mark.parametrize("entry", [("main.py",), ("-m", "skatmind")])
def test_generic_cli_transport(entry, tmp_path):
    source, target = tmp_path / "request.json", tmp_path / "result.json"
    source.write_text(json.dumps(opening_request()), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, *entry, "--input", str(source), "--output", str(target)],
        capture_output=True, text=True, timeout=30)
    assert completed.returncode == 0, completed.stderr
    assert "Whole-game rollout review" in completed.stdout
    assert "Decision quality:" not in completed.stdout
    result = json.loads(target.read_text(encoding="utf-8"))
    assert result["whole_game_rollout_result"]["status"] == "complete"


def test_installed_style_canonical_run_matches_public_execution(tmp_path, capsys):
    from skatmind.cli.execution import run_cli
    source, target = tmp_path / "request.json", tmp_path / "result.json"
    root = opening_request()
    source.write_text(json.dumps(root), encoding="utf-8")
    assert run_cli(["run", "--input", str(source), "--output", str(target), "--quiet"],
                   invocation_style="installed") == 0
    assert capsys.readouterr().out == ""
    actual = json.loads(target.read_text(encoding="utf-8"))
    expected = execute(parse_request(root), input_reference=str(source)).result.to_dict()[
        "document"]
    actual["whole_game_rollout_result"]["work"]["elapsed_ms"] = 0
    expected["whole_game_rollout_result"]["work"]["elapsed_ms"] = 0
    assert actual == expected
