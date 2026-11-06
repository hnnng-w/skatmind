"""Bounded genuine native executions; wire mutations are controlled negative fixtures."""

from dataclasses import replace

import pytest
from test_session_recorded_review import context_for

from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.app_web.execution import execute_guided_frontend_review_v1
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_session_evidence import (
    build_managed_session_source,
    build_session_capture_candidate,
    decode_session_execution,
)
from skatmind.private_execution_capture import capture_native_execution
from skatmind.session_checkpoint_review import export_session_checkpoint_review_request_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.session_recorded_coverage import project_saved_session_coverage
from skatmind.session_rollout_review import derive_session_rollout_review_request_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1


def genuine(tmp_path, rollout=False):
    _app, active = context_for(tmp_path)
    document = active.document
    _, checkpoint, observation = project_saved_session_coverage(document).decisions[0]
    request = export_session_checkpoint_review_request_v1(
        state=document.state, checkpoint=checkpoint).request
    if rollout:
        request = derive_session_rollout_review_request_v1(state=document.state,
            checkpoint=checkpoint, settings=WholeGameRolloutSettingsV1(
                requested_worlds=1, random_seed=0, wall_clock_timeout_ms=30000))
    with capture_native_execution() as captured:
        execution = execute_guided_frontend_review_v1(request, options=ExecutionOptionsV1())
    assert len(captured) == 1
    candidate = build_session_capture_candidate(document, checkpoint, observation,
                                                  execution, captured[0])
    return candidate, execution, document


@pytest.mark.parametrize("rollout", (False, True))
def test_native_roundtrip_keeps_original_tuple_and_bytes(tmp_path, rollout):
    candidate, execution, document = genuine(tmp_path, rollout)
    source = build_managed_session_source(document)[2]
    retained = decode_session_execution(candidate.objects[1], candidate.evidence, source)
    assert retained.execution == execution
    assert retained.execution.options._provenance_supplied_option_names == ()
    assert retained.download("request")[1] == execution.request_json_bytes
    assert retained.download("result")[1] == execution.result_json_bytes
    assert source.coverage.own_plays == len(source.coverage.decisions) == 1


def test_checkpoint_only_change_has_distinct_complete_source_identity(tmp_path):
    _app, active = context_for(tmp_path)
    stripped = build_session_persistence_document_v1(active.state, decision_checkpoints=())
    original = build_managed_session_source(active.document)[1]
    changed = build_managed_session_source(stripped)[1]
    assert active.document.state_fingerprint == stripped.state_fingerprint
    assert original.revision == changed.revision
    assert original.source_version.identity != changed.source_version.identity
    coverage = project_saved_session_coverage(stripped)
    assert coverage.own_plays == coverage.missing_checkpoints == 1


@pytest.mark.parametrize("field", ("observation", "checkpoint", "review_export", "downloads",
                                  "supplied_options", "internal_execution", "original_source"))
def test_independent_malformed_wire_is_rejected(tmp_path, field):
    candidate, _execution, document = genuine(tmp_path)
    obj = candidate.objects[1]
    data = decode_json(obj.payload)
    data[field] = ["validate_output"] if field == "supplied_options" else []
    malformed = replace(obj, payload=canonical_json(data))
    entry = replace(candidate.evidence, envelope=malformed.reference)
    with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
        decode_session_execution(malformed, entry, build_managed_session_source(document)[2])


@pytest.mark.parametrize("method", (None, "immediate_expected_value", "bounded_search", "auto"))
def test_all_existing_saved_session_methods_are_retained(tmp_path, method):
    from test_session_decision_checkpoint import _ready_live_state
    from test_session_position_export import _options, _search_settings
    from test_session_recorded_review import selection
    from test_session_transitions import _apply

    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1
    from skatmind.session_commands import RecordSessionPlayCommandV1
    from skatmind.session_decision_checkpoint import build_session_decision_checkpoint_v1
    from skatmind.session_position_export import export_session_position_analysis_request_v1

    state = _ready_live_state()
    settings = _search_settings() if method in ("bounded_search", "auto") else None
    options = replace(_options(recommendation_method=method,
        bounded_search_settings=settings),
        sample_count=1)
    checkpoint = build_session_decision_checkpoint_v1(state=state,
        position_export=export_session_position_analysis_request_v1(state, options))
    state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                                                    player_id="player-a", card="CA"))
    app, active = context_for(tmp_path, state, (checkpoint,))
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    assert active.evidence_notice[1] == "saved"
    store = archive_store(app)
    retained = store.read_evidence(store.snapshot().available_evidence_ids[0])
    assert retained.execution.request.document.get("recommendation_method") == method
    assert retained.execution.result == active.execution.result


def test_native_v2_supplements_and_supplied_provenance_survive_admission(tmp_path):
    from whole_game_review_fixtures import saved_opening
    state, checkpoint = saved_opening(decision_trick=2, actual="C7")
    document = build_session_persistence_document_v1(state, decision_checkpoints=(checkpoint,))
    source = build_managed_session_source(document)[2]
    _, checkpoint, observation = source.coverage.decisions[0]
    request = derive_session_rollout_review_request_v1(state=state, checkpoint=checkpoint,
        settings=WholeGameRolloutSettingsV1(objective="complete_settlement", random_seed=7,
            requested_worlds=1, wall_clock_timeout_ms=30000), supplements={"bid_value": 18})
    # Genuine public execution with explicitly supplied native provenance options.
    # This codec fixture does not introduce a new frontend option or method.
    options = ExecutionOptionsV1(validate_output=True, include_provenance=True)
    with capture_native_execution() as observed:
        execution = execute_guided_frontend_review_v1(request, options=options)
    candidate = build_session_capture_candidate(document, checkpoint, observation,
                                                execution, observed[0])
    retained = decode_session_execution(candidate.objects[1], candidate.evidence, source)
    assert retained.execution.options._provenance_supplied_option_names == (
        "validate_output", "include_provenance")
    assert retained.execution.result.field_provenance is not None
    assert retained.execution.request.document["whole_game_rollout_derivation"]["version"] == 2
    assert retained.download("result")[1] == execution.result_json_bytes


@pytest.mark.parametrize("change", ("dependency", "bytes", "provenance", "options"))
def test_wire_identity_cannot_substitute_native_evidence(tmp_path, change):
    from skatmind.automatic_match_execution_codec import (
        decode_execution_value,
        encode_execution_value,
    )
    candidate, _execution, document = genuine(tmp_path)
    obj = candidate.objects[1]
    data = decode_json(obj.payload)
    dependencies = obj.dependencies
    if change == "dependency":
        dependencies = ()
    elif change == "bytes":
        import base64
        import hashlib
        raw = base64.b64decode(data["downloads"][0]["bytes"]) + b" "
        data["downloads"][0].update(bytes=base64.b64encode(raw).decode(),
                                    sha256=hashlib.sha256(raw).hexdigest())
    elif change == "provenance":
        data["invocation"]["value"]["provenance_source_metadata"] = None
    else:
        options = decode_execution_value(data["options"])
        options["workflow_options"] = {"sample_count_override": 2}
        data["options"] = encode_execution_value(options)
        data["supplied_options"] = ["workflow_options"]
    wire = replace(obj, payload=canonical_json(data), dependencies=dependencies)
    entry = replace(candidate.evidence, envelope=wire.reference)
    with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
        decode_session_execution(wire, entry, build_managed_session_source(document)[2])
