"""Genuine retained S2/S3 fixtures; S4 itself is guarded against every execution seam."""

from dataclasses import replace

import pytest
from test_automatic_match_evidence import commit_candidate, genuine_candidate
from test_automatic_match_learning import rewrite, save, setup_service
from test_automatic_match_rollout_evidence import executed
from test_match_decision_analysis import _complete_workspace
from test_match_rollout_review import alex_workspace, rollout_options

from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.automatic_match_evidence import (
    ORDINARY_METHODS,
    build_managed_match_source,
    decode_match_source,
)
from skatmind.automatic_match_rollout_evidence import build_match_rollout_capture_candidate
from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS


@pytest.fixture(scope="module")
def executions():
    # Seven explicit fixture analyses: four complete ordinary methods, one genuine
    # early Search unavailability, one complete rollout, one missing-input rollout.
    ordinary = tuple(genuine_candidate(method) for method in ORDINARY_METHODS)
    unavailable = genuine_candidate("bounded_search", decision=1)
    complete = build_match_rollout_capture_candidate(*executed("complete_settlement"))
    incomplete = build_match_rollout_capture_candidate(*executed(options=replace(
        rollout_options("complete_settlement"), settlement_supplements={})))
    return (*ordinary, unavailable, complete, incomplete)


def forbid_execution(monkeypatch):
    import skatmind.application.execution as application
    import skatmind.application.historical_game_workflow as historical
    import skatmind.application.position_workflow as position
    import skatmind.information_set_search_executor as information
    import skatmind.match_decision_analysis as decision
    import skatmind.recommendation_workflow as workflow
    import skatmind.whole_game_rollout as rollout

    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        pytest.fail("S4 must not execute any new card analysis")

    for module, names in (
        (application, ("execute_application_invocation",)),
        (historical, ("execute_historical_game_workflow",)),
        (position, ("execute_position_analysis_workflow", "execute_recommendation_workflow")),
        (decision, ("execute_application_invocation", "execute_match_decision_analysis_v1")),
        (workflow, ("solve_compatible_world_minimax", "evaluate_whole_game_rollout_v1",
                    "_run_immediate", "execute_recommendation_workflow")),
        (information, ("execute_information_set_search_v1",)),
        (rollout, ("execute_whole_game_rollout_v1", "evaluate_whole_game_rollout_v1")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    return calls


def stage(app, candidates):
    archive = archive_store(app, initialize=True)
    for value in candidates:
        assert commit_candidate(archive, value).status in ("saved", "unchanged")
    return archive


def test_all_methods_rollout_separation_restart_bytes_and_zero_analysis(
    tmp_path, monkeypatch, executions,
):
    app, service = setup_service(tmp_path)
    ordinary_path, _ = save(app, "ordinary", workspace=_complete_workspace())
    rollout_path, _ = save(app, "rollout", workspace=alex_workspace(count=3))
    archive = stage(app, executions)
    before = {path: path.read_bytes() for path in (ordinary_path, rollout_path)}
    native = {value.evidence.identity: archive.read_evidence(value.evidence.identity).downloads
              for value in executions}
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "prepared"
    first = service.inspect().generation
    assert len(first.recipe.source_version_ids) == 2 and len(first.recipe.evidence_ids) == 7

    def check(bundle):
        teacher = bundle.prepared.strategy_teacher_evidence
        assert len(teacher.evidences) == 5
        assert {row.options.recommendation_method for row in teacher.evidences} == set(
            ORDINARY_METHODS)
        assert bundle.debrief.report_count == 1
        assert len(bundle.availability) == 1
        assert bundle.availability[0].report.value.result.document[
            "whole_game_rollout_result"]["status"] == "unavailable"
        assert bundle.coaching.tactical_cross_game_coaching_report.teacher_assessment_count == 5
        return tuple(bundle.download(kind) for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS)

    downloads = service.consume(check)
    manifest = archive.snapshot().manifest
    assert service.update().status == "reused" and archive.snapshot().manifest == manifest
    restarted = AutomaticMatchLearningServiceV1.open(app)
    assert restarted.inspect().status == "reconstruction_needed"
    assert restarted.update().status == "rebuilt"
    assert restarted.inspect().generation == first
    assert restarted.consume(check) == downloads
    assert archive.snapshot().manifest == manifest
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert {key: archive.read_evidence(key).downloads for key in native} == native
    assert calls == []


@pytest.mark.parametrize("family", ("ordinary", "rollout"))
def test_correction_with_equal_revision_never_rebinds_report(
    tmp_path, monkeypatch, executions, family,
):
    value = executions[0 if family == "ordinary" else -2]
    app, service = setup_service(tmp_path)
    source = decode_match_source(value.objects[0], value.source)
    path, document = save(app, workspace=source.document.workspace)
    archive = stage(app, (value,))
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "prepared"
    original = service.inspect().generation
    changed = rewrite(path, document)
    assert changed.workspace.revision == document.workspace.revision
    assert service.update().status == "prepared"
    current = service.inspect().generation
    assert current.recipe.source_version_ids != original.recipe.source_version_ids
    assert current.recipe.evidence_ids == ()
    assert [(row.evidence_id, row.status) for row in current.evidence_outcomes] == [
        (value.evidence.identity, "non_current")]
    assert archive.read_evidence(value.evidence.identity).source.document == source.document
    assert len(archive.snapshot().manifest.sources) == 2 and calls == []


@pytest.mark.parametrize("family", ("ordinary", "rollout"))
def test_new_retained_evidence_during_unlocked_build_conflicts(
    tmp_path, monkeypatch, executions, family,
):
    import skatmind.app_web.automatic_match_learning as module

    value = executions[0 if family == "ordinary" else -2]
    app, service = setup_service(tmp_path)
    source = decode_match_source(value.objects[0], value.source)
    save(app, workspace=source.document.workspace)
    archive = archive_store(app, initialize=True)
    original = module.build_automatic_match_bundle
    calls = forbid_execution(monkeypatch)

    def publish(*args, **kwargs):
        bundle = original(*args, **kwargs)
        assert commit_candidate(archive, value).status == "saved"
        return bundle

    monkeypatch.setattr(module, "build_automatic_match_bundle", publish)
    assert service.update().status == "conflict"
    assert archive.snapshot().manifest.current_generation is None
    assert archive.read_evidence(value.evidence.identity).source == source
    assert calls == []


@pytest.mark.parametrize("dependency", ("source", "report"))
@pytest.mark.parametrize("damage", ("missing", "corrupt", "unsupported"))
def test_quarantine_is_explicit_and_never_repaired(tmp_path, executions, dependency, damage):
    from skatmind.automatic_learning_codec import canonical_json, decode_json
    from skatmind.automatic_match_evidence import _source_record

    value = executions[0]
    app, service = setup_service(tmp_path)
    source = decode_match_source(value.objects[0], value.source)
    save(app, workspace=source.document.workspace)
    archive = stage(app, (value,))
    obj = value.objects[0 if dependency == "source" else 1]
    if damage == "unsupported":
        # Storage-consistent unsupported producer; no fabricated execution claim.
        data = decode_json(obj.payload)
        data["producer_contract"] = 99
        changed = replace(obj, payload=canonical_json(data))
        archive.publish_object(changed)
        before = archive.snapshot().manifest
        if dependency == "report":
            entry = replace(value.evidence, envelope=changed.reference)
            requested = replace(before, revision=before.revision + 1,
                objects=before.objects + (changed.entry,), evidence=before.evidence + (entry,))
        else:
            record = _source_record(source.document, changed.reference)
            envelope = replace(value.objects[1], dependencies=(changed.reference,))
            archive.publish_object(envelope)
            entry = replace(value.evidence, envelope=envelope.reference)
            requested = replace(before, revision=before.revision + 1,
                objects=(changed.entry, envelope.entry), sources=(record,), evidence=(entry,))
        if dependency == "source":
            from skatmind.automatic_learning_objects import manifest_bytes
            # Controlled future on-disk archive, not an allowed mutation of an
            # already accepted immutable source record through today's API.
            (archive.root / "manifest.json").write_bytes(manifest_bytes(requested))
        else:
            assert archive.update_manifest(
                requested, expected_manifest=before.fingerprint).status == "saved"
        # Report case retains one genuine supported run alongside the unsupported envelope.
    else:
        path = archive.root / obj.area / (obj.reference.fingerprint + ".json")
        if damage == "missing":
            path.unlink()
        else:
            path.write_bytes(b"{}")
    before_bytes = {p: p.read_bytes() for p in archive.root.rglob("*.json")}
    result = service.update()
    assert result.status == "prepared"
    generation = service.inspect().generation
    if dependency == "source":
        assert generation.recipe.source_version_ids == ()
        assert generation.recipe.exclusions[0].reason in ("invalid", "unsupported")
        assert generation.recipe.evidence_ids == ()
    else:
        assert len(generation.recipe.source_version_ids) == 1
        assert len(generation.recipe.evidence_ids) == int(damage == "unsupported")
    assert any(row.status == ("dependency_unavailable" if dependency == "source"
        and damage != "unsupported" else damage) for row in generation.evidence_outcomes)
    assert all(p.read_bytes() == raw for p, raw in before_bytes.items()
               if p.name != "manifest.json")


@pytest.mark.parametrize("count,known", (
    (0, False), (3, False), (3, True), (30, False), (30, True)))
def test_partial_complete_passed_and_truthful_reconstruction_skips(
    tmp_path, monkeypatch, count, known,
):
    app, service = setup_service(tmp_path)
    path, document = save(app, workspace=alex_workspace(count=count, known_hand=known))
    original = path.read_bytes()
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "prepared"

    def check(bundle):
        coverage = {row.name: int(row.value) for row in bundle.coverage}
        assert coverage["matches"] == 1 and coverage["observed_games"] == 1
        assert coverage["passed_deals"] == 1 and coverage["empty_slots"] == 34
        assert coverage["recorded_decisions"] == count
        assert coverage["dataset_records"] + coverage["skipped_decisions"] == count
        assert coverage["ordinary_bindings"] == coverage["complete_rollout_reports"] == 0
        assert all(row.reason in ("acting_hand_unavailable", "required_public_hand_unavailable")
                   for row in bundle.skipped)
        if count == 3:
            assert coverage["dataset_records"] == int(known)
        if count == 30:
            assert coverage["dataset_records"] == 30

    service.consume(check)
    obj, record, snapshot = build_managed_match_source(document)
    assert service.store.read_object(record.object_ref).raw == obj.raw
    assert snapshot.match_snapshot_id in service.consume(lambda value:
        value.prepared.player_catalog.current_match_snapshot_ids)
    assert path.read_bytes() == original and calls == []


def test_exact_runs_semantic_consensus_and_cross_game_focus_are_preserved(tmp_path, monkeypatch):
    """Four real Application executions with controlled Search assessments/timing."""
    from test_learning_corpus_tactical_coaching import _below_best_search_result
    from test_match_workspace_contracts import _definition

    import skatmind.recommendation_workflow as workflow

    elapsed, below = 1, frozenset({"C8"})

    def search(**kwargs):
        value = _below_best_search_result(**kwargs, expected_seed=0, below_best_cards=below)
        return replace(value, consumed_budget=replace(value.consumed_budget,
                                                      wall_clock_elapsed_ms=elapsed))

    monkeypatch.setattr(workflow, "solve_compatible_world_minimax", search)
    first_workspace = _complete_workspace(definition=_definition(match_id="first"))
    second_workspace = _complete_workspace(definition=_definition(match_id="second"))
    first = genuine_candidate("bounded_search", workspace=first_workspace, decision=22)
    elapsed = 2
    repeat = genuine_candidate("bounded_search", workspace=first_workspace, decision=22)
    second = genuine_candidate("bounded_search", workspace=second_workspace, decision=22)
    below = frozenset()
    conflicting = genuine_candidate("bounded_search", workspace=first_workspace, decision=22)
    assert first.evidence.identity != repeat.evidence.identity
    assert first.evidence.semantic_fingerprint == repeat.evidence.semantic_fingerprint
    app, service = setup_service(tmp_path)
    save(app, "first", workspace=first_workspace)
    save(app, "second", workspace=second_workspace)
    archive = stage(app, (first, repeat, second, first))
    assert len(archive.snapshot().manifest.evidence) == 3
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "prepared"

    def qualified(bundle):
        report = bundle.coaching.tactical_cross_game_coaching_report
        assert report.teacher_assessment_count == 3
        assert report.strictly_below_best_decision_count == 2
        assert report.focus_area_count == 2
        assert all(row.qualifying_decision_count == 2 and row.distinct_game_count == 2
                   for row in report.focus_areas)

    service.consume(qualified)
    assert commit_candidate(archive, conflicting).status == "saved"
    assert service.inspect().status == "outdated"
    assert service.update().status == "prepared"
    assert service.consume(lambda value:
        value.coaching.tactical_cross_game_coaching_report.focus_area_count) == 0
    assert len(service.inspect().generation.recipe.evidence_ids) == 4
    assert calls == []


@pytest.mark.parametrize("status", ("partial", "timeout"))
def test_controlled_limited_search_enters_teacher_without_focus(tmp_path, monkeypatch, status):
    """Real producer execution, controlled comparable Search prefix, not solver proof."""
    from test_automatic_match_evidence import (
        test_controlled_limited_search_retains_complete_execution,
    )

    # Existing S2 controlled fixture executes once, validates and saves the exact
    # invocation/Result. S4 reads that genuine retained execution, never a summary.
    test_controlled_limited_search_retains_complete_execution(tmp_path, monkeypatch, status)
    from skatmind.automatic_learning_store import resume_automatic_learning_store_v1
    retained_store = resume_automatic_learning_store_v1(tmp_path / "archive")
    entry, = retained_store.snapshot().manifest.evidence
    value = retained_store.read_evidence(entry.identity)
    app, service = setup_service(tmp_path)
    save(app, workspace=value.source.document.workspace)
    from skatmind.automatic_match_evidence import MatchCaptureCandidate
    candidate = MatchCaptureCandidate(value.source.record, entry, (
        retained_store.read_object(value.source.record.object_ref),
        retained_store.read_object(entry.envelope)))
    stage(app, (candidate,))
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "prepared"

    def check(bundle):
        row, = bundle.prepared.strategy_teacher_evidence.evidences
        assert row.search_status == status
        assert bundle.coaching.tactical_cross_game_coaching_report.focus_area_count == 0

    service.consume(check)
    assert calls == []


@pytest.mark.parametrize("status", ("partial", "timeout", "cancelled"))
def test_executed_incomplete_rollouts_stay_separate(tmp_path, monkeypatch, status):
    """Real rollout producer with bounded work or controlled clock/cancellation."""
    import skatmind.recommendation_workflow as workflow
    real = workflow.evaluate_whole_game_rollout_v1

    def evaluate(view, settings):
        if status == "timeout":
            ticks = iter(range(0, 1_000_000, 100))
            return real(view, settings, clock=lambda: next(ticks))
        return real(view, settings, cancelled=lambda: True)

    options = rollout_options(max_card_transitions=1) if status == "partial" else rollout_options()
    if status != "partial":
        monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", evaluate)
    candidate = build_match_rollout_capture_candidate(*executed(options=options))
    source = decode_match_source(candidate.objects[0], candidate.source)
    app, service = setup_service(tmp_path)
    save(app, workspace=source.document.workspace)
    stage(app, (candidate,))
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "prepared"

    def check(bundle):
        assert bundle.debrief.report_count == 0
        assert bundle.prepared.strategy_teacher_evidence.source_report_count == 0
        assert bundle.coaching.tactical_cross_game_coaching_report.teacher_assessment_count == 0
        row, = bundle.availability
        assert row.report.value.result.document["whole_game_rollout_result"]["status"] == status

    service.consume(check)
    assert calls == []


@pytest.mark.parametrize("family", ("ordinary", "rollout"))
def test_overlapping_s2_s3_pending_reservations_keep_their_owner(
    tmp_path, monkeypatch, executions, family,
):
    import skatmind.app_web.automatic_match_learning as module

    value = executions[0 if family == "ordinary" else -2]
    source = decode_match_source(value.objects[0], value.source)
    app, service = setup_service(tmp_path)
    save(app, workspace=source.document.workspace)
    archive = archive_store(app, initialize=True)
    pending = archive.begin_candidate(value.objects)
    original = module.build_automatic_match_bundle

    def save_pending(*args, **kwargs):
        bundle = original(*args, **kwargs)
        assert pending.owner is not service.store.owner
        for obj in value.objects:
            assert archive.publish_object(obj, candidate=pending) in ("saved", "unchanged")
        before = archive.snapshot().manifest
        requested = replace(before, revision=before.revision + 1,
            objects=tuple(obj.entry for obj in value.objects), sources=(value.source,),
            evidence=(value.evidence,))
        assert archive.update_manifest(requested, expected_manifest=before.fingerprint,
                                       candidate=pending).status == "saved"
        return bundle

    monkeypatch.setattr(module, "build_automatic_match_bundle", save_pending)
    calls = forbid_execution(monkeypatch)
    assert service.update().status == "conflict"
    assert archive.read_evidence(value.evidence.identity).source == source
    assert archive.snapshot().manifest.current_generation is None and calls == []
