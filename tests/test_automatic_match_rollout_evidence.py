"""S3 genuine execution retention; controlled faults are identified by each test."""

from dataclasses import replace

import pytest
from test_automatic_match_evidence import commit_candidate, repack
from test_match_rollout_review import alex_workspace, rollout_options

from skatmind.automatic_learning_codec import decode_json
from skatmind.automatic_learning_store import (
    initialize_automatic_learning_store_v1,
    resume_automatic_learning_store_v1,
)
from skatmind.automatic_match_rollout_evidence import build_match_rollout_capture_candidate
from skatmind.errors import SkatMindError
from skatmind.match_analysis_contracts import build_match_analysis_report_v1
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def executed(objective="played_game_goal", *, options=None, workspace=None):
    workspace = workspace or alex_workspace(count=3)
    captured = []
    value = execute_match_decision_analysis_v1(workspace, match_position=2, decision_index=3,
        options=options or rollout_options(objective),
        execution_observer=lambda *args: captured.append(args))
    return (build_match_workspace_persistence_document_v1(workspace),
            build_match_analysis_report_v1(value), *captured[0])


@pytest.mark.parametrize("objective", ("played_game_goal", "complete_settlement"))
def test_genuine_rollout_retains_exact_typed_execution_and_native_exports(objective):
    from skatmind.automatic_match_evidence import decode_match_source
    from skatmind.automatic_match_rollout_evidence import (
        build_match_rollout_capture_candidate,
        decode_match_rollout,
    )
    from skatmind.match_analysis_exports import (
        build_match_report_result_export_v1,
        build_match_rollout_request_export_v1,
    )
    values = executed(objective)
    candidate = build_match_rollout_capture_candidate(*values)
    source = decode_match_source(candidate.objects[0], candidate.source)
    retained = decode_match_rollout(candidate.objects[1], candidate.evidence, source)
    assert (retained.source.document, retained.report, retained.invocation,
            retained.execution) == values
    assert retained.entry.evidence_class == "rollout"
    assert retained.comparison.source_snapshot == retained.source.snapshot
    for kind, builder in (("result", build_match_report_result_export_v1),
                          ("request", build_match_rollout_request_export_v1)):
        artifact = builder(values[1])
        assert retained.download(kind) == (artifact.filename, artifact.to_bytes())
    with pytest.raises(KeyError):
        retained.download("strategy-source")


def test_genuine_inner_unavailable_is_not_complete_debrief():
    from skatmind.automatic_match_evidence import decode_match_source
    from skatmind.automatic_match_rollout_evidence import (
        build_match_rollout_capture_candidate,
        decode_match_rollout,
    )
    values = executed(options=replace(rollout_options("complete_settlement"),
                                      settlement_supplements={}))
    assert values[1].value.status == "executed"
    assert values[1].value.result.document["whole_game_rollout_result"]["status"] == "unavailable"
    candidate = build_match_rollout_capture_candidate(*values)
    retained = decode_match_rollout(candidate.objects[1], candidate.evidence,
        decode_match_source(candidate.objects[0], candidate.source))
    assert retained.comparison is None
    assert retained.report == values[1]


@pytest.fixture(scope="module")
def original():
    return executed("complete_settlement")


@pytest.fixture(scope="module")
def candidate(original):
    return build_match_rollout_capture_candidate(*original)


def mapping(wire, name):
    return next(pair for pair in wire["value"] if pair[0] == name)


@pytest.mark.parametrize("defect", (
    "source", "snapshot", "actor", "observed", "cutoff", "report_id", "request", "result",
    "options", "supplement", "provenance", "option_presence", "invocation", "arithmetic",
    "ties", "actual_comparison", "legal", "settings", "origin", "transform", "warning",
    "download_bytes", "download_digest", "download_order", "extra", "constructor",
))
def test_recomputed_envelope_rejects_tampering(tmp_path, candidate, defect):
    from skatmind.automatic_match_evidence import decode_match_source
    from skatmind.automatic_match_rollout_evidence import decode_match_rollout
    data = decode_json(candidate.objects[1].payload)
    report = data["report"]["value"]
    value = report["value"]["value"]
    request = value["request"]["value"]["document"]
    result = value["result"]["value"]["document"]
    if defect == "source":
        data["original_source"]["source_version"]["content_fingerprint"] = "f" * 64
    elif defect == "snapshot":
        data["snapshot_id"] = "wrong"
    elif defect in {"actor", "observed", "cutoff"}:
        key = {"actor": "actor_id", "observed": "observed_card",
               "cutoff": "information_cutoff"}[defect]
        data["situation"][key] = 1 if defect == "cutoff" else "wrong"
    elif defect == "report_id":
        report["report_id"] = "f" * 64
    elif defect == "request":
        mapping(request, "actual_card_played")[1] = "CK"
    elif defect == "result":
        mapping(result, "input_file")[1] = "wrong"
    elif defect == "options":
        value["options"]["value"]["rollout_settings"]["value"]["random_seed"] = 42
    elif defect == "supplement":
        mapping(value["options"]["value"]["settlement_supplements"], "matadors")[1] = 2
    elif defect == "provenance":
        data["execution"]["value"]["provenance"] = None
    elif defect == "option_presence":
        data["invocation"]["value"]["options"]["value"]["position_analysis"]["supplied"] = []
    elif defect == "invocation":
        data["invocation"]["value"]["input_reference"] = "wrong"
    elif defect in {"arithmetic", "ties"}:
        rollout = mapping(result, "whole_game_rollout_result")[1]
        if defect == "ties":
            mapping(rollout, "tied_best_cards")[1]["value"] = ["DA"]
        else:
            row = mapping(rollout, "candidates")[1]["value"][0]
            mapping(row, "total_local_card_point_margin")[1] += 1
    elif defect == "actual_comparison":
        mapping(mapping(result, "whole_game_rollout_comparison")[1], "actual_card")[1] = "CK"
    elif defect == "legal":
        mapping(result, "legal_cards")[1]["value"] = ["DA"]
    elif defect == "settings":
        mapping(mapping(result, "settings")[1], "recommendation_method")[1] = "auto"
    elif defect in {"origin", "transform"}:
        derivation = mapping(request, "whole_game_rollout_derivation")[1]
        key = "supplement_origin" if defect == "origin" else "reconstruction_policy"
        mapping(derivation, key)[1] = "invented"
    elif defect == "warning":
        value["result"]["value"]["warnings"]["value"] = ["invented"]
    elif defect.startswith("download_"):
        if defect == "download_order":
            data["downloads"].reverse()
        else:
            data["downloads"][0]["bytes" if defect == "download_bytes" else "sha256"] = "wrong"
    elif defect == "constructor":
        data["report"]["type"] = "arbitrary.module.Class"
    else:
        data["extra"] = True
    changed = repack(candidate, data)
    with pytest.raises((ValueError, TypeError, KeyError, SkatMindError)):
        decode_match_rollout(changed.objects[1], changed.evidence,
                            decode_match_source(candidate.objects[0], candidate.source))


@pytest.mark.parametrize("defect", ("codec1", "future_codec", "version", "producer",
                                   "producer_contract", "package_version"))
def test_future_contracts_are_unsupported_and_preserve_bytes(tmp_path, candidate, defect):
    data = decode_json(candidate.objects[1].payload)
    codec = 1 if defect == "codec1" else 99 if defect == "future_codec" else 2
    if defect not in {"codec1", "future_codec"}:
        data[defect] = 99 if defect in {"version", "producer_contract"} else "future"
    changed = repack(candidate, data, codec=codec)
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, changed)
    before = {p: p.read_bytes() for p in store.root.rglob("*") if p.is_file()}
    resumed = resume_automatic_learning_store_v1(store.root)
    state = next(s for s in resumed.snapshot().objects if s.reference == changed.evidence.envelope)
    assert state.consumption_status == "unsupported"
    assert not resumed.snapshot().available_evidence_ids
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_mixed_families_share_exact_s2_source_bytes_and_restart(
    tmp_path, original, candidate, monkeypatch,
):
    import skatmind.application.execution as application_execution
    import skatmind.automatic_learning_io as io
    import skatmind.match_decision_analysis as ordinary_execution
    import skatmind.recommendation_workflow as workflow
    from skatmind.automatic_match_evidence import build_match_capture_candidate
    from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
    captured = []
    document = original[0]
    value = execute_match_decision_analysis_v1(document.workspace,
        match_position=2, decision_index=3,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1),
        execution_observer=lambda *args: captured.append(args))
    ordinary = build_match_capture_candidate(document, build_match_analysis_report_v1(value),
                                             *captured[0])
    assert ordinary.objects[0].raw == candidate.objects[0].raw
    assert ordinary.source == candidate.source
    assert decode_json(candidate.objects[0].payload)["producer"] == "managed_match_decision"
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    for value in (ordinary, candidate):
        assert commit_candidate(store, value).status == "saved"
    manifest = store.snapshot().manifest
    assert len(manifest.sources) == 1 and len(manifest.objects) == 3
    assert commit_candidate(store, candidate).status == "unchanged"
    assert store.snapshot().manifest == manifest
    def forbidden(*a, **kw):
        pytest.fail("Passive validation performed execution or a persistent write")
    monkeypatch.setattr(application_execution, "execute_application_invocation", forbidden)
    monkeypatch.setattr(ordinary_execution, "execute_application_invocation", forbidden)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", forbidden)
    monkeypatch.setattr(io, "write_temporary", forbidden)
    resumed = resume_automatic_learning_store_v1(store.root)
    assert resumed.snapshot().available_evidence_ids == tuple(e.identity for e in manifest.evidence)
    assert resumed.read_evidence(candidate.evidence.identity).report == original[1]


@pytest.mark.parametrize("dependency", ("source", "report"))
@pytest.mark.parametrize("damage", ("missing", "corrupt"))
def test_dependency_outcomes_remain_distinct(tmp_path, candidate, dependency, damage):
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    obj = candidate.objects[0 if dependency == "source" else 1]
    path = store.root / obj.area / (obj.reference.fingerprint + ".json")
    if damage == "missing":
        path.unlink()  # Deliberate disposable interruption fixture.
    else:
        path.write_bytes(b"{}")
    state = resume_automatic_learning_store_v1(store.root).snapshot()
    assert not state.available_evidence_ids
    assert next(s for s in state.objects if s.reference == obj.reference).storage_status == damage
    expected = "dependency_unavailable" if dependency == "source" else damage
    status = next(s for s in state.objects if s.reference == candidate.evidence.envelope)
    assert status.consumption_status == expected


def test_compatible_manual_target_cannot_replace_original(original):
    from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
    from skatmind.match_debrief import MatchDebriefEvidenceV1
    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    document, report, invocation, execution = original
    workspace = document.workspace
    changed = _build_match_workspace_v1(revision=workspace.revision, slots=workspace.slots,
        match_definition=replace(workspace.match_definition, title="Compatible manual target"))
    target = build_match_workspace_persistence_document_v1(changed)
    source_snapshot = build_learning_corpus_match_snapshot_v1(document)
    target_snapshot = build_learning_corpus_match_snapshot_v1(target)
    manual = MatchDebriefEvidenceV1(report, source_snapshot, target_snapshot)
    assert manual.snapshot != manual.source_snapshot
    with pytest.raises(ValueError):
        build_match_rollout_capture_candidate(target, report, invocation, execution)


@pytest.mark.parametrize("status", ("partial", "timeout", "cancelled"))
def test_controlled_executed_availability_is_not_a_comparison(monkeypatch, status):
    import skatmind.recommendation_workflow as workflow
    from skatmind.automatic_match_evidence import decode_match_source
    from skatmind.automatic_match_rollout_evidence import decode_match_rollout
    real = workflow.evaluate_whole_game_rollout_v1
    def evaluate(view, settings):
        if status == "timeout":
            ticks = iter(range(0, 1_000_000, 100))
            return real(view, settings, clock=lambda: next(ticks))
        return real(view, settings, cancelled=lambda: True)
    options = rollout_options(max_card_transitions=1) if status == "partial" else rollout_options()
    if status != "partial":
        monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", evaluate)
    values = executed(options=options)
    assert values[1].value.result.document["whole_game_rollout_result"]["status"] == status
    candidate = build_match_rollout_capture_candidate(*values)
    retained = decode_match_rollout(candidate.objects[1], candidate.evidence,
        decode_match_source(candidate.objects[0], candidate.source))
    assert retained.comparison is None
    result = retained.report.value.result.document
    assert result["whole_game_rollout_result"]["tied_best_cards"] == ()
    assert result["recommendation"]["card"] is None
    assert not result["recommendation_method_summary"]["fallback_used"]


def test_elapsed_semantics_and_meaningful_variants(monkeypatch):
    import skatmind.recommendation_workflow as workflow
    real = workflow.evaluate_whole_game_rollout_v1
    elapsed = 1.0
    def evaluate(view, settings):
        result = real(view, settings)
        return replace(result, work=replace(result.work, elapsed_ms=elapsed))
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", evaluate)
    first = build_match_rollout_capture_candidate(*executed())
    elapsed = 2.0
    second = build_match_rollout_capture_candidate(*executed())
    assert first.evidence.identity != second.evidence.identity
    assert first.evidence.semantic_fingerprint == second.evidence.semantic_fingerprint
    options = rollout_options()
    changed = build_match_rollout_capture_candidate(*executed(options=replace(options,
        rollout_settings=replace(options.rollout_settings, random_seed=1))))
    assert changed.evidence.semantic_fingerprint != first.evidence.semantic_fingerprint


def test_controlled_full_tied_best_set_and_actual_membership_survive(tmp_path, monkeypatch):
    """Deterministic aggregate tie injected before Application serialization/provenance."""
    import skatmind.recommendation_workflow as workflow
    real = workflow.evaluate_whole_game_rollout_v1
    def evaluate(view, settings):
        result = real(view, settings)
        candidates = tuple(replace(result.candidates[0], card=row.card)
                           for row in result.candidates)
        cards = tuple(row.card for row in candidates)
        return replace(result, candidates=candidates, ranked_cards=cards,
                       tied_best_cards=cards, recommended_card=cards[0])
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", evaluate)
    candidate = build_match_rollout_capture_candidate(*executed())
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    commit_candidate(store, candidate)
    retained = resume_automatic_learning_store_v1(store.root).read_evidence(
        candidate.evidence.identity)
    result = retained.report.value.result.document
    assert set(result["whole_game_rollout_result"]["tied_best_cards"]) == {"CK", "C9", "C7"}
    assert result["whole_game_rollout_comparison"]["actual_card"] == "C7"
    assert retained.comparison.semantic_fingerprint == retained.entry.semantic_fingerprint
