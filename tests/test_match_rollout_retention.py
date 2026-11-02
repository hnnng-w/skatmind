"""Managed S3 ownership and controlled save failures; actual rollout executor counted."""

from collections import Counter
from dataclasses import replace

import pytest
from test_match_evidence_retention import change_source
from test_match_rollout_review import alex_workspace

import skatmind.application.execution as application_execution
import skatmind.automatic_learning_io as io
import skatmind.recommendation_workflow as workflow
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.match_evidence_retention import save_pending_match
from skatmind.app_web.match_frontend import UnifiedMatchContextV1
from skatmind.app_web.match_rollout_frontend import (
    execute_unified_match_rollout,
    match_rollout_binding,
)
from skatmind.app_web.recorded_review_opening import RecordingOpenConflict
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.automatic_learning_store import DEFAULT_LIMITS, StoreLimitsV1
from skatmind.capture_web.context import MatchCaptureWebContextV1


@pytest.fixture
def managed(tmp_path):
    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "home"))
    root = app.managed_stateful.root("matches")
    capture = MatchCaptureWebContextV1.open(root / "synthetic.json")
    assert capture.save_candidate(alex_workspace(count=3)) == "saved"
    active = UnifiedMatchContextV1(category_root=root, path=capture.workspace_path,
        handle="a" * 64, capture=capture, selected_position=2, selected_review_decision=3)
    app.managed_stateful.activate_match(active)
    return app, active


def execute(app, active, **changes):
    return execute_unified_match_rollout(active, {
        "match_position": "2", "decision_index": "3", "visible_decision_index": "3",
        "expected_revision": str(active.workspace.revision),
        "decision_selection": match_rollout_binding(active, 3),
        "objective": "played_game_goal", "requested_worlds": "2", "random_seed": "0",
        **changes}, app_context=app)


def test_incomplete_after_complete_retry_preserves_both_original_executions(managed, monkeypatch):
    app, active = managed
    calls = Counter()
    real = application_execution.execute_application_invocation
    def counted(*args, **kwargs):
        calls["execute"] += 1
        return real(*args, **kwargs)
    monkeypatch.setattr(application_execution, "execute_application_invocation", counted)
    complete, selected = execute(app, active)
    assert selected is complete
    store = archive_store(app)
    before = active.path.read_bytes()
    evaluate = workflow.evaluate_whole_game_rollout_v1
    def timed(view, settings):
        ticks = iter(range(0, 1_000_000, 100))
        return evaluate(view, settings, clock=lambda: next(ticks))
    with monkeypatch.context() as patch:
        patch.setattr(workflow, "evaluate_whole_game_rollout_v1", timed)
        patch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
        attempt, selected = execute(app, active, random_seed="1")
    assert selected is complete
    assert active.rollout_notice[0] is attempt
    assert active.capture.report_store.get(attempt.report_id) is None
    pending = active.pending_evidence
    assert pending.report is attempt
    assert active.evidence_notice[1] == "unsaved"
    monkeypatch.setattr(application_execution, "execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Save-only retry executed"))
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1",
                        lambda *a, **kw: pytest.fail("Save-only retry evaluated"))
    assert save_pending_match(app, active, pending.token) == "saved"
    assert calls == {"execute": 2}
    assert active.capture.report_store.list() == (complete,)
    assert active.rollout_notice[0] is attempt
    values = tuple(store.read_evidence(row.identity) for row in store.snapshot().manifest.evidence)
    assert tuple(value.report for value in values) == (complete, attempt)
    assert values[0].comparison is not None and values[1].comparison is None
    assert active.path.read_bytes() == before


def mutate(app, active, change):
    if change == "owner":
        app.managed_stateful.activate_match(replace(active, handle="b" * 64))
    elif change == "source":
        change_source(active)
    elif change == "selection":
        active.review_decision_generation += 1
    elif change == "attempt":
        active.rollout_attempt = object()
    elif change == "archive_owner":
        from skatmind.app_web.saved_match_analyses import SavedMatchAnalyses
        app.saved_match_analyses = SavedMatchAnalyses()
    else:
        active.capture.report_store.clear()


@pytest.mark.parametrize("phase", ("execution", "staging", "manifest"))
@pytest.mark.parametrize("change", (
    "owner", "source", "selection", "attempt", "generation", "archive_owner"))
def test_rollout_final_publication_rechecks_every_owner(managed, monkeypatch, phase, change):
    app, active = managed
    store = archive_store(app, initialize=True)  # Explicit fixture creation.
    fired = False
    def change_once():
        nonlocal fired
        if not fired:
            fired = True
            mutate(app, active, change)
    if phase == "execution":
        real = application_execution.execute_application_invocation
        def run(*args, **kwargs):
            value = real(*args, **kwargs)
            change_once()
            return value
        monkeypatch.setattr(application_execution, "execute_application_invocation", run)
    elif phase == "staging":
        real = store.publish_object
        def run(*args, **kwargs):
            value = real(*args, **kwargs)
            change_once()
            return value
        monkeypatch.setattr(store, "publish_object", run)
    else:
        real = io.write_temporary
        def write(directory, raw):
            value = real(directory, raw)
            if directory == store.root:
                change_once()
            return value
        monkeypatch.setattr(io, "write_temporary", write)
    with pytest.raises(RecordingOpenConflict):
        execute(app, active)
    assert fired and not store.snapshot().manifest.evidence
    assert not store._coordinator.candidates


@pytest.mark.parametrize("change", (
    "owner", "source", "selection", "attempt", "generation", "archive_owner"))
def test_incomplete_pending_retry_expires_without_writes(managed, monkeypatch, change):
    app, active = managed
    complete, _ = execute(app, active)
    store = archive_store(app)
    real = workflow.evaluate_whole_game_rollout_v1
    with monkeypatch.context() as patch:
        patch.setattr(workflow, "evaluate_whole_game_rollout_v1",
                      lambda view, settings: real(view, settings, cancelled=lambda: True))
        patch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
        report, selected = execute(app, active, random_seed="1")
    assert selected is complete and active.capture.report_store.get(report.report_id) is None
    token = active.pending_evidence.token
    mutate(app, active, change)
    def forbidden(*a, **kw):
        pytest.fail("Expired retry performed work")
    monkeypatch.setattr(io, "write_temporary", forbidden)
    monkeypatch.setattr(application_execution, "execute_application_invocation", forbidden)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", forbidden)
    with pytest.raises(RecordingOpenConflict):
        save_pending_match(app, active, token)
    assert len(store.snapshot().manifest.evidence) == 1


@pytest.mark.parametrize("fault", (
    "source", "report", "manifest", "post_replace", "quota", "count_quota"))
def test_rollout_faults_save_only_retry_and_post_commit_authority(managed, monkeypatch, fault):
    app, active = managed
    store = archive_store(app, initialize=True)
    real_write, real_sync = io.write_temporary, io.sync_directory
    def write(directory, raw):
        if directory.name == {"source": "sources", "report": "reports",
                              "manifest": "automatic-learning"}.get(fault):
            raise OSError("Controlled dependency/manifest interruption")
        return real_write(directory, raw)
    def sync(directory):
        if fault == "post_replace" and directory == store.root:
            raise OSError("Controlled failure after authoritative replacement")
        return real_sync(directory)
    monkeypatch.setattr(io, "write_temporary", write)
    monkeypatch.setattr(io, "sync_directory", sync)
    if fault == "quota":
        store.limits = StoreLimitsV1(total_bytes=1)
    elif fault == "count_quota":
        # A first distinct entry fills the injected global rollout bound.
        execute(app, active)
        store.limits = StoreLimitsV1(evidence_per_class=1)
    report, _ = execute(app, active, random_seed="1")
    assert active.evidence_notice[1] == ("saved" if fault == "post_replace" else "unsaved")
    monkeypatch.setattr(io, "write_temporary", real_write)
    monkeypatch.setattr(io, "sync_directory", real_sync)
    store.limits = DEFAULT_LIMITS
    monkeypatch.setattr(application_execution, "execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Retry executed"))
    if fault != "post_replace":
        token = active.pending_evidence.token
        assert save_pending_match(app, active, token) == "saved"
        with pytest.raises(RecordingOpenConflict):
            save_pending_match(app, active, token)
    assert store.read_evidence(store.snapshot().manifest.evidence[-1].identity).report == report
    assert not store._coordinator.candidates


@pytest.mark.parametrize("case", (
    "rejected", "outer_unavailable", "exception", "observer_then_exception"))
def test_rollout_without_valid_publication_never_initializes_archive(managed, monkeypatch, case):
    import skatmind.app_web.match_rollout_frontend as frontend
    from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
    app, active = managed
    real = frontend.execute_match_decision_analysis_v1
    if case == "outer_unavailable":
        def unavailable(workspace, **kwargs):
            return execute_match_decision_analysis_v1(workspace, match_position=1,
                decision_index=3, options=kwargs["options"])
        monkeypatch.setattr(frontend, "execute_match_decision_analysis_v1", unavailable)
        report, _ = execute(app, active)
        assert report.value.status == "unavailable"
    else:
        if case != "rejected":
            def fail(*args, **kwargs):
                if case == "observer_then_exception":
                    real(*args, **kwargs)
                raise RuntimeError("Controlled execution exception")
            monkeypatch.setattr(frontend, "execute_match_decision_analysis_v1", fail)
        with pytest.raises((ValueError, RuntimeError)):
            execute(app, active, **({"requested_worlds": "0"} if case == "rejected" else {}))
    assert not (app.managed_home.root / "automatic-learning").exists()
