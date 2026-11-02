"""Genuine tiny ordinary executions and strict no-execution archive admission."""

import base64
import hashlib
from dataclasses import replace

import pytest
from test_match_decision_analysis import _complete_workspace

from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_learning_store import (
    UnsupportedEvidenceError,
    initialize_automatic_learning_store_v1,
    resume_automatic_learning_store_v1,
)
from skatmind.automatic_match_evidence import ORDINARY_METHODS, build_match_capture_candidate
from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    build_match_analysis_report_v1,
)
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def genuine_candidate(method="immediate_expected_value", *, workspace=None, decision=28):
    workspace = workspace or _complete_workspace()
    captured = []
    value = execute_match_decision_analysis_v1(workspace, match_position=3, decision_index=decision,
        options=MatchDecisionAnalysisOptionsV1(recommendation_method=method,
            immediate_sample_count=1,
            search_random_seed=None if method == ORDINARY_METHODS[0] else 0),
        execution_observer=lambda invocation, execution: captured.append((invocation, execution)))
    assert value.status == "executed" and len(captured) == 1
    document = build_match_workspace_persistence_document_v1(workspace)
    report = build_match_analysis_report_v1(value)
    return build_match_capture_candidate(document, report, *captured[0])


def commit_candidate(store, value):
    before = store.snapshot().manifest
    reservation = store.begin_candidate(value.objects)
    for obj in value.objects:
        assert store.publish_object(obj, candidate=reservation) in ("saved", "unchanged")
    requested = replace(before, revision=before.revision + 1,
        objects=before.objects + tuple(obj.entry for obj in value.objects
                                       if obj.entry not in before.objects),
        sources=before.sources + (() if value.source in before.sources else (value.source,)),
        evidence=before.evidence + (() if value.evidence in before.evidence else (value.evidence,)))
    return store.update_manifest(requested, expected_manifest=before.fingerprint,
                                 candidate=reservation)


@pytest.mark.parametrize("method", ORDINARY_METHODS)
def test_genuine_ordinary_complete_roundtrip(tmp_path, method):
    value = genuine_candidate(method)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    assert commit_candidate(store, value).status == "saved"
    assert store.snapshot().available_evidence_ids == (value.evidence.identity,)
    retained = store.read_evidence(value.evidence.identity)
    assert retained.report.value.options.recommendation_method == method
    if method != "immediate_expected_value":
        key = ("information_set_search_result" if method == "information_set_search"
               else "bounded_search_result")
        assert retained.report.value.result.document[key]["status"] == "complete"
    assert retained.source.record == value.source
    assert tuple(row[0] for row in retained.downloads) == ("result", "strategy-source", "request")


@pytest.fixture(scope="module")
def candidate():
    return genuine_candidate()


def repack(candidate, data, *, codec=2):
    envelope = replace(candidate.objects[1], payload=canonical_json(data), codec_version=codec)
    return replace(candidate, objects=(candidate.objects[0], envelope),
                   evidence=replace(candidate.evidence, envelope=envelope.reference))


@pytest.mark.parametrize("defect", (
    "whole_source", "snapshot", "actor", "actual_card", "cutoff", "profile", "input_reference",
    "request_bytes", "result_bytes", "wrapper_bytes", "byte_digest", "byte_format", "byte_order",
    "warning",
    "result_semantics", "execution_options", "provenance", "extra_field",
))
def test_recomputed_hashes_do_not_admit_semantic_or_byte_tampering(tmp_path, candidate, defect):
    data = decode_json(candidate.objects[1].payload)
    if defect == "whole_source":
        data["original_source"]["source_version"]["content_fingerprint"] = "f" * 64
    elif defect == "snapshot":
        data["snapshot_id"] = "f" * 64
    elif defect in {"actor", "actual_card", "cutoff"}:
        key = {"actor": "actor_id", "actual_card": "observed_card",
               "cutoff": "information_cutoff"}[defect]
        data["situation"][key] = 0 if defect == "cutoff" else "wrong"
    elif defect in {"request_bytes", "result_bytes", "wrapper_bytes", "byte_digest", "byte_format",
                    "byte_order"}:
        index = {"request_bytes": 2, "result_bytes": 0, "wrapper_bytes": 1}.get(defect, 0)
        row = data["downloads"][index]
        raw = (base64.b64decode(row["bytes"]) + b" " if defect == "byte_format" else b"{}\n")
        if defect == "byte_order":
            from skatmind.match_analysis_exports import canonical_match_artifact_json_bytes_v1
            document = decode_json(base64.b64decode(row["bytes"]))
            raw = canonical_match_artifact_json_bytes_v1(dict(reversed(tuple(document.items()))))
        row["bytes"] = base64.b64encode(raw).decode()
        if defect != "byte_digest":
            row["sha256"] = hashlib.sha256(raw).hexdigest()
    elif defect == "extra_field":
        data["extra"] = True
    elif defect == "execution_options":
        data["invocation"]["value"]["options"]["value"]["position_analysis"]["value"][
            "sample_count_override"] = 2
    elif defect == "provenance":
        data["execution"]["value"]["provenance"] = None
    else:
        value = data["report_source"]["report"]["value"]
        if defect == "profile":
            value["profile_binding"]["acting_player_id"] = "wrong"
        elif defect == "warning":
            value["result"]["warnings"] = ["invented"]
        else:
            value["result"]["document"]["input_file" if defect == "input_reference"
                else "legal_cards"] = "wrong"
    changed = repack(candidate, data)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    commit_candidate(store, changed)  # Storage accepts opaque, consistently hashed objects.
    assert store.snapshot().available_evidence_ids == (candidate.evidence.identity,)
    with pytest.raises(UnsupportedEvidenceError):
        store.read_evidence(changed.evidence.identity)


@pytest.mark.parametrize("defect", ("codec1", "future_codec", "version", "producer",
                                   "producer_contract", "package_version"))
def test_unknown_contracts_and_s1_codec_remain_nonconsumable(tmp_path, candidate, defect):
    data = decode_json(candidate.objects[1].payload)
    codec = 1 if defect == "codec1" else 99 if defect == "future_codec" else 2
    if defect not in {"codec1", "future_codec"}:
        data[defect] = 99 if defect in {"version", "producer_contract"} else "unknown"
    changed = repack(candidate, data, codec=codec)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, changed)
    before = {p: p.read_bytes() for p in store.root.rglob("*.json")}
    resumed = resume_automatic_learning_store_v1(store.root)
    assert not resumed.snapshot().available_evidence_ids
    assert next(s for s in resumed.snapshot().objects
                if s.reference == changed.evidence.envelope).consumption_status == "unsupported"
    with pytest.raises(UnsupportedEvidenceError):
        resumed.read_evidence(changed.evidence.identity)
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("dependency", ("source", "report"))
@pytest.mark.parametrize("damage", ("missing", "corrupt"))
def test_restart_dependency_exclusion_preserves_independent_evidence(
    tmp_path, candidate, dependency, damage,
):
    from test_match_workspace_contracts import _definition
    other = genuine_candidate(workspace=_complete_workspace(
        definition=_definition(match_id="other")))
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    commit_candidate(store, other)
    obj = candidate.objects[0 if dependency == "source" else 1]
    path = store.root / obj.area / (obj.reference.fingerprint + ".json")
    if damage == "missing":
        path.unlink()  # Deliberate disposable corruption fixture.
    else:
        path.write_bytes(b"{}")
    resumed = resume_automatic_learning_store_v1(store.root)
    assert resumed.snapshot().available_evidence_ids == (other.evidence.identity,)
    assert resumed.read_evidence(other.evidence.identity).report.match_id == "other"
    with pytest.raises(UnsupportedEvidenceError):
        resumed.read_evidence(candidate.evidence.identity)


def test_unindexed_intact_object_is_not_execution_admission(tmp_path, candidate):
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    for obj in candidate.objects:
        store.publish_object(obj)
    assert store.read_object(candidate.evidence.envelope) == candidate.objects[1]
    with pytest.raises(ValueError, match="not indexed"):
        store.read_evidence(candidate.evidence.identity)


def test_same_revision_changed_whole_workspace_is_not_original_binding(tmp_path, candidate):
    from skatmind.automatic_match_evidence import _source_record
    from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
    from skatmind.match_analysis_report_source_codec import (
        resume_match_analysis_report_source_export_v1,
    )
    from skatmind.match_decision_analysis import build_match_decision_position_request_v1
    from skatmind.match_workspace_contracts import _build_match_workspace_v1

    data = decode_json(candidate.objects[0].payload)
    workspace = _complete_workspace()
    changed = _build_match_workspace_v1(revision=workspace.revision, slots=workspace.slots,
        match_definition=replace(workspace.match_definition, title="Other whole-source content"))
    report = resume_match_analysis_report_source_export_v1(
        decode_json(candidate.objects[1].payload)["report_source"]).report
    assert build_match_decision_position_request_v1(changed, match_position=3,
        decision_index=28, options=report.value.options).request == report.value.request
    document = build_match_workspace_persistence_document_v1(changed)
    data.update(document=document.to_dict(),
                snapshot=build_learning_corpus_match_snapshot_v1(document).to_dict())
    source = replace(candidate.objects[0], payload=canonical_json(data))
    record = _source_record(document, source.reference)
    # A storage-consistent new dependency/index cannot rewrite the original envelope binding.
    envelope = replace(candidate.objects[1], dependencies=(source.reference,))
    entry = replace(candidate.evidence, source_version_id=record.source_version.identity,
        envelope=envelope.reference, situation=replace(candidate.evidence.situation,
            source_version_id=record.source_version.identity))
    mismatch = replace(candidate, source=record, evidence=entry, objects=(source, envelope))
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, mismatch)
    assert not store.snapshot().available_evidence_ids


@pytest.mark.parametrize("method", ("bounded_search", "auto", "information_set_search"))
def test_genuine_inner_unavailable_is_executed_evidence(tmp_path, method):
    value = genuine_candidate(method, decision=1)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, value)
    retained = store.read_evidence(value.evidence.identity)
    result = retained.report.value.result.document
    key = ("information_set_search_result" if method == "information_set_search"
           else "bounded_search_result")
    assert result[key]["status"] == "unavailable"
    assert retained.report.value.status == "executed"


def test_original_external_profile_context_is_retained(tmp_path):
    from test_match_player_statistics_context import _actionable_snapshot, _capture_with_snapshots
    definition = _capture_with_snapshots(snapshots=tuple(
        _actionable_snapshot("player-" + side, "snapshot-" + side) for side in "abc"))
    candidate = genuine_candidate(workspace=_complete_workspace(definition=definition))
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    retained = resume_automatic_learning_store_v1(store.root).read_evidence(
        candidate.evidence.identity)
    external = retained.invocation.external_documents
    assert external.opponent_statistics_document is not None
    assert "eligible-player-statistics" in external.opponent_statistics_reference
    assert retained.report.value.result.document["opponent_profile_application_summary"]


def test_distinct_elapsed_only_reports_keep_separate_identity_and_semantic_group(
    tmp_path, monkeypatch,
):
    """Real Search with controlled elapsed diagnostics, avoiding a timing assertion."""
    import skatmind.recommendation_workflow as workflow
    real = workflow.solve_compatible_world_minimax
    elapsed = 1
    def search(**kwargs):
        result = real(**kwargs)
        assert result.status == "complete"
        return replace(result, consumed_budget=replace(result.consumed_budget,
                                                       wall_clock_elapsed_ms=elapsed))
    monkeypatch.setattr(workflow, "solve_compatible_world_minimax", search)
    first = genuine_candidate("bounded_search", decision=22)
    elapsed = 2
    second = genuine_candidate("bounded_search", decision=22)
    assert first.evidence.identity != second.evidence.identity
    assert first.evidence.semantic_fingerprint == second.evidence.semantic_fingerprint
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, first)
    commit_candidate(store, second)
    assert len(store.snapshot().available_evidence_ids) == 2


def test_supported_legacy_identity_domains_and_bytes_survive_read(tmp_path, candidate):
    """Controlled legacy identity conversion of a genuine current execution."""
    from test_skatmind_rename import _legacy_report_source, _legacy_workspace_document

    from skatmind.automatic_match_evidence import _download_record, _situation, _source_record
    from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
    from skatmind.learning_corpus_strategy_teacher_builder import validate_original_match_teacher_v1
    from skatmind.match_analysis_exports import canonical_match_artifact_json_bytes_v1
    from skatmind.match_analysis_report_source_codec import (
        resume_match_analysis_report_source_export_v1,
    )
    from skatmind.match_workspace_persistence_codec import resume_match_workspace_document_v1

    source_data = decode_json(candidate.objects[0].payload)
    document = resume_match_workspace_document_v1(source_data["document"]).document
    legacy_document = resume_match_workspace_document_v1(
        _legacy_workspace_document(document)).document
    snapshot = build_learning_corpus_match_snapshot_v1(legacy_document)
    source_data.update(document=legacy_document.to_dict(), snapshot=snapshot.to_dict())
    source_object = replace(candidate.objects[0], payload=canonical_json(source_data))
    record = _source_record(legacy_document, source_object.reference)
    data = decode_json(candidate.objects[1].payload)
    wrapper = _legacy_report_source(decode_json(base64.b64decode(data["downloads"][1]["bytes"])))
    report = resume_match_analysis_report_source_export_v1(wrapper).report
    situation = _situation(record, report)
    data.update(original_source=record.to_dict(), snapshot_id=snapshot.match_snapshot_id,
        situation=situation.to_dict(), report_source=wrapper)
    raw = canonical_match_artifact_json_bytes_v1(wrapper)
    data["downloads"][1] = _download_record(
        "strategy-source", data["downloads"][1]["filename"], raw)
    envelope = replace(candidate.objects[1], payload=canonical_json(data),
                       dependencies=(source_object.reference,))
    entry = replace(candidate.evidence, source_version_id=record.source_version.identity,
        envelope=envelope.reference, situation=situation,
        semantic_fingerprint=validate_original_match_teacher_v1(
            report, snapshot).teacher_semantic_fingerprint)
    legacy = replace(candidate, source=record, evidence=entry, objects=(source_object, envelope))
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, legacy)
    before = {p: p.read_bytes() for p in store.root.rglob("*.json")}
    retained = resume_automatic_learning_store_v1(store.root).read_evidence(entry.identity)
    assert retained.report.report_id == wrapper["report_id"]
    assert retained.source.snapshot == snapshot
    assert retained.download("strategy-source")[1] == raw
    assert all(p.read_bytes() == payload for p, payload in before.items())


@pytest.mark.parametrize("status", ("partial", "timeout"))
def test_controlled_limited_search_retains_complete_execution(tmp_path, monkeypatch, status):
    """Controlled Search output; the ordinary Application producer really executes."""
    from skatmind.bounded_search_result import (
        AggregateSearchCandidateResult,
        BoundedSearchResult,
        ConsumedSearchBudget,
        rank_search_candidate_results,
    )
    from skatmind.rules import get_legal_cards
    def search(*, information_view, requested_budget, random_seed):
        completed = requested_budget.minimum_comparable_worlds
        cards = get_legal_cards(list(information_view.local_remaining_hand),
            [p.card for p in information_view.current_trick], information_view.game_type)
        candidates = rank_search_candidate_results(tuple(AggregateSearchCandidateResult(
            card=card, rank=1, is_recommended=False, completed_world_count=completed,
            local_contract_success_count=completed, local_contract_success_rate=1.0,
            mean_local_side_game_score=24.0, mean_local_side_card_point_margin=10.0)
            for card in cards), information_view.game_type, recommend=True)
        return BoundedSearchResult(schema_version=1, analysis_method="bounded_search",
            search_method="compatible_world_minimax_v1", game_type=information_view.game_type,
            status=status, stop_reason=("wall_clock_timeout" if status == "timeout"
                                        else "node_budget_exhausted"),
            world_coverage="all_compatible_worlds",
            solution_claim="none" if status == "timeout" else "node_limited_partial",
            terminal_utility_version=1, requested_budget=requested_budget,
            consumed_budget=ConsumedSearchBudget(depth_reached=1,
                nodes_expanded=1 if status == "timeout" else requested_budget.max_nodes,
                selected_world_count=completed + 1, completed_world_count=completed,
                sampled_world_count=0,
                unique_sampled_world_count=0,
                wall_clock_elapsed_ms=(requested_budget.wall_clock_timeout_ms
                                       if status == "timeout" else 1)),
            compatible_world_count=completed + 1, candidate_results=candidates,
            recommended_card=candidates[0].card,
            fallback_used=False, fallback_method=None)
    monkeypatch.setattr("skatmind.recommendation_workflow.solve_compatible_world_minimax", search)
    candidate = genuine_candidate("bounded_search", decision=22)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    retained = store.read_evidence(candidate.evidence.identity)
    assert retained.report.value.result.document["bounded_search_result"]["status"] == status
