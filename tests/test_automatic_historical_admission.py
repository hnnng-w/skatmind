"""Strict semantic and bounded-codec negatives, separate from genuine fixture analyses."""

import base64
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_automatic_historical_evidence import genuine_historical
from test_automatic_match_evidence import commit_candidate
from test_automatic_match_learning_evidence import forbid_execution
from test_automatic_session_review_corrections import archive_bytes

from skatmind.api.v1 import ExecutionOptionsV1, WorkflowV1, parse_request
from skatmind.app_web.execution import execute_guided_frontend_review_v1
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1
from skatmind.automatic_historical_codec import pack_native, unpack_native
from skatmind.automatic_historical_evidence import (
    build_historical_capture_candidate,
    decode_historical_execution,
    decode_historical_source,
)
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_learning_store import (
    initialize_automatic_learning_store_v1,
    resume_automatic_learning_store_v1,
)
from skatmind.automatic_match_execution_codec import (
    decode_execution_value,
    encode_execution_value,
    validate_execution,
)
from skatmind.private_execution_capture import capture_native_execution

__all__ = ["genuine_historical"]
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("example", (
    "historical_grand_normal_completion", "historical_grand_declarer_concession",
    "historical_grand_defender_concession", "historical_grand_declarer_card_exposure",
    "historical_grand_defender_open_play", "historical_grand_open_card_throw",
    "historical_party_wide_claim", "historical_grand_defender_open_play_continuation",
    "historical_grand_declarer_card_exposure_continuation",
    "historical_grand_defender_open_play_continuation_declarer_concession",
    "historical_grand_declarer_card_exposure_continuation_defender_concession",
))
def test_supported_imported_endings_resume_without_analysis(tmp_path, monkeypatch, example):
    request = parse_request(json.loads((ROOT / "examples" / (example + ".json")).read_text()))
    with capture_native_execution() as native:
        execution = execute_guided_frontend_review_v1(request, options=ExecutionOptionsV1())
    forbid_execution(monkeypatch)
    monkeypatch.setattr("skatmind.historical_party_wide_claim.execute_party_wide_claim_proof_v1",
                        lambda *a, **k: pytest.fail("Admission reran a Claim proof"))
    candidate = build_historical_capture_candidate("imported-ending", 0, execution, native[0])
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    before = archive_bytes(store)
    restarted = resume_automatic_learning_store_v1(store.root)
    retained = restarted.read_evidence(candidate.evidence.identity)
    assert retained.execution == execution
    assert retained.source.origin == "imported"
    assert retained.download("result")[1] == execution.result_json_bytes
    assert archive_bytes(store) == before
    if retained.game.game_end_reason in (
            "defender_open_play", "party_wide_all_remaining_tricks_claim"):
        from skatmind.api.v1 import ResultDocumentV1
        from skatmind.automatic_historical_validation import validate_historical_execution
        # Controlled scalar contradiction specifically exercises independent source
        # reconciliation; this modified tuple is not claimed as genuine evidence.
        document = retained.internal_execution.result.to_dict()["document"]
        document["historical_game_summary"]["point_accounting"]["observed_declarer_points"] += 1
        changed = replace(retained.internal_execution, result=ResultDocumentV1(
            workflow=WorkflowV1.HISTORICAL_GAME, document=document))
        with pytest.raises(ValueError, match="point accounting"):
            validate_historical_execution(retained.game, retained.invocation, changed)


@pytest.mark.parametrize("mode", ("immediate_review", "search_review", "replay_coaching",
    "information_set_search_review", "information_set_replay_coaching",
    "historical_tactical_motif_review"))
def test_genuine_bounded_optional_families_retain_only_executed_assessments(mode, monkeypatch):
    root = json.loads((ROOT / "examples/historical_grand_declarer_concession.json").read_text())
    root["historical_game_input"]["tricks"] = root["historical_game_input"]["tricks"][:1]
    root["historical_game_input"]["game_end"]["declarer_hand_cards_remaining"] = 9
    root["historical_game_input"]["game_end"]["defender_consent"] = {
        "status": "not_required", "consenting_defender_player_ids": []}
    request = parse_request(root)
    workflow = {mode: True}
    if mode != "historical_tactical_motif_review":
        workflow.update(immediate_sample_count=1, immediate_base_random_seed=0)
    if mode not in ("immediate_review", "historical_tactical_motif_review"):
        workflow["search_seed"] = 0
    external = {}
    if mode == "immediate_review":
        workflow["use_profile_presets_override"] = True
        external = {"opponent_statistics_document": json.loads(
            (ROOT / "examples/historical_opponent_statistics.json").read_text()),
            "opponent_statistics_reference": "memory://original-s7-statistics"}
    options = ExecutionOptionsV1(include_provenance=True, workflow_options=workflow, **external)
    with capture_native_execution() as native:
        execution = execute_guided_frontend_review_v1(request, options=options)
    # Early-game Search unavailability is a genuinely executed bounded outcome,
    # not an injected recommendation or a solver claim.
    forbid_execution(monkeypatch)
    candidate = build_historical_capture_candidate("optional", 0, execution, native[0])
    source = decode_historical_source(candidate.objects[0], candidate.source)
    retained = decode_historical_execution(candidate.objects[1], candidate.evidence, source)
    assert retained.execution == execution
    assert retained.execution.result.field_provenance is not None
    assert retained.execution.options._provenance_supplied_option_names == (
        "include_provenance", "workflow_options", *external)


def test_consistently_rehashed_outcome_cannot_override_recorded_cards(
    tmp_path, genuine_historical, monkeypatch,
):
    draft, execution, native = genuine_historical
    candidate = build_historical_capture_candidate("semantic", 0, execution, native, draft=draft)
    data = decode_json(candidate.objects[1].payload)
    def contradict(value):
        if type(value) is list:
            return [contradict(item) for item in value]
        if type(value) is dict:
            changed = {key: contradict(item) for key, item in value.items()}
            if value.get("type") == "mapping":
                changed["value"] = [[key, item + 1 if key in (
                    "declarer_points", "total_declarer_points") and type(item) is int else item]
                    for key, item in changed["value"]]
            return changed
        return value
    for field in ("result", "internal_execution"):
        wire = encode_execution_value(unpack_native(data[field]))
        data[field] = pack_native(decode_execution_value(contradict(wire)))
    public = unpack_native(data["result"])
    raw = canonical_frontend_json_bytes_v1(public)
    data["downloads"][1].update(bytes=base64.b64encode(raw).decode("ascii"),
                                sha256=hashlib.sha256(raw).hexdigest())
    validate_execution(unpack_native(data["invocation"]), unpack_native(data["internal_execution"]),
                       workflow=WorkflowV1.HISTORICAL_GAME)
    obj = replace(candidate.objects[1], payload=canonical_json(data))
    entry = replace(candidate.evidence, envelope=obj.reference)
    corrupted = replace(candidate, evidence=entry, objects=(candidate.objects[0], obj))
    source = decode_historical_source(candidate.objects[0], candidate.source)
    forbid_execution(monkeypatch)
    with pytest.raises(ValueError, match="recorded outcome"):
        decode_historical_execution(obj, entry, source)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, corrupted)
    assert entry.identity not in resume_automatic_learning_store_v1(store.root).snapshot(
        ).available_evidence_ids


@pytest.mark.parametrize("field", ("size", "sha256", "bytes", "encoding"))
def test_bounded_native_codec_rejects_forged_compression(genuine_historical, field):
    packed = pack_native(genuine_historical[2][1])
    packed[field] = {"size": 129 * 1024 * 1024, "sha256": "0" * 64,
                     "bytes": "not-base64", "encoding": "future"}[field]
    with pytest.raises(ValueError):
        unpack_native(packed)


@pytest.mark.parametrize("field", ("options", "supplied_options", "downloads", "original_source"))
def test_retained_native_envelope_rejects_contradictory_wire(genuine_historical, field):
    draft, execution, native = genuine_historical
    candidate = build_historical_capture_candidate("envelope", 0, execution, native, draft=draft)
    data = decode_json(candidate.objects[1].payload)
    data[field] = None
    obj = replace(candidate.objects[1], payload=canonical_json(data))
    entry = replace(candidate.evidence, envelope=obj.reference)
    source = decode_historical_source(candidate.objects[0], candidate.source)
    with pytest.raises((ValueError, TypeError, AttributeError)):
        decode_historical_execution(obj, entry, source)


@pytest.fixture(scope="module", params=(
    "historical_grand_defender_open_play", "historical_party_wide_claim"))
def genuine_proof_ending(request):
    root = parse_request(json.loads((ROOT / "examples" / (request.param + ".json")).read_text()))
    with capture_native_execution() as native:
        execution = execute_guided_frontend_review_v1(root, options=ExecutionOptionsV1())
    candidate = build_historical_capture_candidate("proof-settlement", 0, execution, native[0])
    return candidate, execution


def test_rehashed_proof_settlement_is_rejected_without_reexecution_or_writes(
    tmp_path, genuine_proof_ending, monkeypatch,
):
    from skatmind.automatic_learning_store import UnsupportedEvidenceError
    candidate, execution = genuine_proof_ending
    original = decode_json(candidate.objects[1].payload)
    data = decode_json(candidate.objects[1].payload)
    changed_count = 0

    def contradict(value):
        nonlocal changed_count
        if type(value) is list:
            return [contradict(item) for item in value]
        if type(value) is dict:
            changed = {key: contradict(item) for key, item in value.items()}
            if value.get("type") == "mapping":
                for pair in changed["value"]:
                    if pair[0] == "settlement_score" and type(pair[1]) is int:
                        pair[1] += 1
                        changed_count += 1
            return changed
        return value

    for field in ("result", "internal_execution"):
        data[field] = pack_native(decode_execution_value(
            contradict(encode_execution_value(unpack_native(data[field])))))
    assert changed_count >= 2
    public = unpack_native(data["result"])
    raw = canonical_frontend_json_bytes_v1(public)
    data["downloads"][1].update(bytes=base64.b64encode(raw).decode("ascii"),
                                sha256=hashlib.sha256(raw).hexdigest())
    for field in ("original_source", "invocation", "options", "supplied_options", "guided_draft"):
        assert data[field] == original[field]
    retained_summary = public["document"]["historical_game_summary"]
    original_summary = unpack_native(original["result"])["document"]["historical_game_summary"]
    for field in ("record", "point_accounting", "historical_game_end_summary"):
        assert retained_summary[field] == original_summary[field]
    validate_execution(unpack_native(data["invocation"]), unpack_native(data["internal_execution"]),
                       workflow=WorkflowV1.HISTORICAL_GAME)
    obj = replace(candidate.objects[1], payload=canonical_json(data))
    entry = replace(candidate.evidence, envelope=obj.reference)
    corrupted = replace(candidate, evidence=entry, objects=(candidate.objects[0], obj))
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    assert commit_candidate(store, corrupted).status == "saved"
    before = archive_bytes(store)
    forbid_execution(monkeypatch)
    def forbidden(*args, **kwargs):
        pytest.fail("Proof admission must not execute a solver or write the archive")
    monkeypatch.setattr("skatmind.historical_party_wide_claim.execute_party_wide_claim_proof_v1",
                        forbidden)
    monkeypatch.setattr("skatmind.defender_open_play.prove_defender_rest_tricks", forbidden)
    monkeypatch.setattr("skatmind.automatic_learning_io.write_temporary", forbidden)
    source = decode_historical_source(candidate.objects[0], candidate.source)
    genuine = decode_historical_execution(candidate.objects[1], candidate.evidence, source)
    assert genuine.download("request")[1] == execution.request_json_bytes
    assert genuine.download("result")[1] == execution.result_json_bytes
    direct_rejected = False
    try:
        decode_historical_execution(obj, entry, source)
    except ValueError:
        direct_rejected = True
    restarted = resume_automatic_learning_store_v1(store.root)
    resumed = restarted.snapshot()
    archived = entry.identity in resumed.available_evidence_ids
    print({"direct_rejected": direct_rejected, "restart_admitted": archived,
           "original_score": original_summary["final_settlement_summary"]["settlement_score"],
           "changed_score": retained_summary["final_settlement_summary"]["settlement_score"]})
    assert archive_bytes(store) == before
    assert direct_rejected and not archived
    assert next(row for row in resumed.objects if row.reference == entry.envelope
                ).consumption_status == "corrupt"
    with pytest.raises(UnsupportedEvidenceError):
        restarted.read_evidence(entry.identity)


@pytest.mark.parametrize(("section", "field"), (
    ("game_value_summary", "game_value"), ("overbid_summary", "margin"),
    ("game_result_summary", "winner"),
))
def test_proof_outcome_reconciles_declaration_and_retained_result(
    genuine_proof_ending, monkeypatch, section, field,
):
    from skatmind.api.v1 import ResultDocumentV1
    from skatmind.automatic_historical_validation import validate_historical_execution
    candidate, _execution = genuine_proof_ending
    source = decode_historical_source(candidate.objects[0], candidate.source)
    data = decode_json(candidate.objects[1].payload)
    invocation = unpack_native(data["invocation"])
    internal = unpack_native(data["internal_execution"])
    document = internal.result.to_dict()["document"]
    value = document["historical_game_summary"][section][field]
    # Controlled scalar corruption, not another executed or archived Report.
    document["historical_game_summary"][section][field] = (
        "defenders" if value == "declarer" else "declarer") if field == "winner" else value + 1
    changed = replace(internal, result=ResultDocumentV1(
        workflow=WorkflowV1.HISTORICAL_GAME, document=document))
    forbid_execution(monkeypatch)
    with pytest.raises(ValueError):
        validate_historical_execution(source.game, invocation, changed)
