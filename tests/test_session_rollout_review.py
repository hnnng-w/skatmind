import copy

import pytest
from test_whole_game_rollout_workflow import without_time
from whole_game_review_fixtures import saved_opening

from skatmind.api.v1 import ExecutionOptionsV1, execute, parse_request, serialize_result
from skatmind.api.v1.schema_validation import validate_input_document, validate_output_document
from skatmind.errors import SkatMindError
from skatmind.rollout_derivation import rollout_source_fingerprint
from skatmind.session_rollout_review import derive_session_rollout_review_request_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1


def test_manual_bid_derivation_preserves_source_and_executes_publicly():
    state, checkpoint = saved_opening(decision_trick=2, actual="C7")
    original = checkpoint.to_dict()
    settings = WholeGameRolloutSettingsV1(objective="complete_settlement", random_seed=7,
                                          requested_worlds=1, wall_clock_timeout_ms=30000)
    request = derive_session_rollout_review_request_v1(
        state=state, checkpoint=checkpoint, settings=settings, supplements={"bid_value": 18})
    root = request.to_dict()["document"]
    derivation = root["whole_game_rollout_derivation"]
    assert derivation["version"] == 2
    assert derivation["policy"] == "frozen_checkpoint_with_manual_settlement_inputs"
    assert derivation["supplement_origin"] == "manual_analysis_input"
    assert derivation["supplements"] == {"bid_value": 18}
    assert derivation["original_request"] == checkpoint.request.to_dict()
    assert derivation["effective_declaration"] == root["game_declaration"]
    assert checkpoint.to_dict() == original
    executed = execute(request, options=ExecutionOptionsV1(include_provenance=True))
    result = serialize_result(executed)["document"]
    assert result["whole_game_rollout_result"]["status"] == "complete"
    assert result["whole_game_rollout_derivation"] == derivation
    assert result["game_declaration"]["bid_value"] == 18
    entries = executed.field_provenance.result.to_dict()["ledger"]["entries"]
    bid = next(entry for entry in entries if entry["field_path"] == "/game_declaration/bid_value")
    assert bid["origin"] == "caller_supplied"
    assert bid["source_references"][0]["field_path"] == (
        "/whole_game_rollout_derivation/supplements/bid_value")
    validate_input_document(root)
    validate_output_document(result)
    changed = copy.deepcopy(root)
    changed["actual_card_played"] = "C8"
    other = execute(parse_request(changed)).result.to_dict()["document"]
    assert without_time(result["whole_game_rollout_result"]) == without_time(
        other["whole_game_rollout_result"])


@pytest.fixture(scope="module")
def supplemented_root():
    state, checkpoint = saved_opening()
    return derive_session_rollout_review_request_v1(
        state=state, checkpoint=checkpoint,
        settings=WholeGameRolloutSettingsV1(objective="complete_settlement", random_seed=0,
                                           requested_worlds=1, wall_clock_timeout_ms=30000),
        supplements={"bid_value": 18}).to_dict()["document"]


@pytest.mark.parametrize("change", [
    "origin", "fingerprint", "effective", "value", "extra", "known", "source_fact",
    "root_fact", "original_mode", "nested_derivation", "version", "objective", "boolean",
])
def test_public_supplement_derivation_rejects_inconsistent_or_forged_differences(
    supplemented_root, change,
):
    root = copy.deepcopy(supplemented_root)
    metadata = root["whole_game_rollout_derivation"]
    if change == "origin":
        metadata["supplement_origin"] = "historically_verified"
    elif change == "fingerprint":
        metadata["original_request_fingerprint"] = "f" * 64
    elif change == "effective":
        metadata["effective_declaration"]["bid_value"] = 24
    elif change == "value":
        metadata["supplements"]["bid_value"] = 24
    elif change == "extra":
        metadata["supplements"]["declarer_points"] = 60
    elif change == "known":
        metadata["original_request"]["document"]["game_declaration"]["bid_value"] = 18
        metadata["original_request_fingerprint"] = rollout_source_fingerprint(
            "skatmind.rollout.original_request.v1", metadata["original_request"])
    elif change == "source_fact":
        metadata["original_request"]["document"]["sample_count"] = 2
    elif change == "root_fact":
        root["sample_count"] = 2
    elif change == "original_mode":
        metadata["original_request"]["document"]["analysis_mode"] = "post_game_review"
    elif change == "nested_derivation":
        metadata["original_request"]["document"]["whole_game_rollout_derivation"] = {}
    elif change == "version":
        metadata.update(version=1, policy="frozen_checkpoint_method_settings_only")
    elif change == "objective":
        root["whole_game_rollout_settings"]["objective"] = "played_game_goal"
    elif change == "boolean":
        metadata["supplements"]["bid_value"] = True
    with pytest.raises(SkatMindError):
        execute(parse_request(root))


@pytest.mark.parametrize("supplements", [{"matadors": 1}, {"hand": []}, {"bid_value": 0},
                                        {"bid_value": -18}, {"bid_value": True}])
def test_adapter_never_overwrites_known_inputs_or_accepts_other_facts(supplements):
    state, checkpoint = saved_opening()
    original = checkpoint.to_dict()
    with pytest.raises(ValueError):
        derive_session_rollout_review_request_v1(
            state=state, checkpoint=checkpoint, supplements=supplements,
            settings=WholeGameRolloutSettingsV1(objective="complete_settlement", random_seed=0,
                                               wall_clock_timeout_ms=30000))
    assert checkpoint.to_dict() == original


def test_changed_later_hidden_hands_and_outcomes_do_not_enrich_frozen_root():
    settings = WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=1,
                                         wall_clock_timeout_ms=30000)
    outputs, roots = [], []
    for reversed_hands in (False, True):
        state, checkpoint = saved_opening(complete=True, reverse_hidden=reversed_hands)
        original = checkpoint.to_dict()
        request = derive_session_rollout_review_request_v1(
            state=state, checkpoint=checkpoint, settings=settings)
        root = request.to_dict()["document"]
        root.pop("whole_game_rollout_derivation")
        roots.append(root)
        result = execute(request).result.to_dict()["document"]["whole_game_rollout_result"]
        result["work"].pop("elapsed_ms")
        outputs.append(result)
        assert checkpoint.to_dict() == original
    assert roots[0] == roots[1]
    assert outputs[0] == outputs[1]
