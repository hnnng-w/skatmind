"""Managed S3 ownership and controlled save failures; actual rollout executor counted."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from threading import Event, local

import pytest
from test_match_evidence_retention import change_source
from test_match_rollout_review import alex_workspace

import skatmind.application.execution as application_execution
import skatmind.automatic_learning_io as io
import skatmind.recommendation_workflow as workflow
import skatmind.whole_game_rollout as core
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.match_evidence_retention import save_pending_match
from skatmind.app_web.match_frontend import (
    UnifiedMatchContextV1,
    execute_unified_match_analysis_v1,
    select_unified_match_position_v1,
)
from skatmind.app_web.match_rollout_frontend import (
    execute_unified_match_rollout,
    match_rollout_binding,
)
from skatmind.app_web.recorded_review_opening import RecordingOpenConflict
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.workflow_state import StaleFrontendWorkflowRevisionError
from skatmind.automatic_learning_store import DEFAULT_LIMITS, StoreLimitsV1
from skatmind.capture_web.context import MatchCaptureWebContextV1


@pytest.fixture
def managed(tmp_path):
    return make_managed(tmp_path / "home")


def make_managed(home):
    app = AppWebContextV1.create(prepare_managed_home_v1(home))
    root = app.managed_stateful.root("matches")
    capture = MatchCaptureWebContextV1.open(root / "synthetic.json")
    assert capture.save_candidate(alex_workspace(count=3)) == "saved"
    active = UnifiedMatchContextV1(category_root=root, path=capture.workspace_path,
        handle="a" * 64, capture=capture, selected_position=2, selected_review_decision=3)
    app.managed_stateful.activate_match(active)
    return app, active


class RolloutProbe:
    """Pause real seed-7 work; count actual draws/transitions in each invocation."""

    def __init__(self, monkeypatch):
        self.entered, self.release = Event(), Event()
        self.phase = "evaluation"
        self.counts, self.results, self.predicates = {}, {}, {}
        self.local = local()
        evaluate = workflow.evaluate_whole_game_rollout_v1
        sample = core.iter_compatible_hidden_worlds
        apply = core.apply_information_set_search_card_v1

        def pause():
            self.entered.set()
            assert self.release.wait(60), "Test did not release real rollout work"

        def sampled(*args, **kwargs):
            for world in sample(*args, **kwargs):
                self.counts[self.local.seed]["sampled_worlds"] += 1
                yield world

        def applied(*args, **kwargs):
            result = apply(*args, **kwargs)
            counts = self.counts[self.local.seed]
            counts["card_transitions"] += 1
            # Three candidates x 28 remaining Cards complete one common world.
            # Stop one actual transition into the second world, before its next check.
            if self.local.seed == 7 and counts["card_transitions"] == 85:
                pause()
            return result

        def evaluated(view, settings, *, cancelled=None):
            seed = self.local.seed = settings.random_seed
            self.counts[seed] = Counter()
            self.predicates[seed] = cancelled
            if seed == 7 and self.phase == "preparation":
                pause()
            result = evaluate(view, settings, clock=lambda: 0.0, cancelled=cancelled)
            self.results[seed] = result
            return result

        monkeypatch.setattr(core, "iter_compatible_hidden_worlds", sampled)
        monkeypatch.setattr(core, "apply_information_set_search_card_v1", applied)
        monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", evaluated)

    def assert_cancelled(self):
        result = self.results[7]
        print("A2 cancelled", self.phase, asdict(result.work), dict(self.counts[7]))
        assert result.status == result.stop_reason == "cancelled"
        assert result.ranked_cards == result.tied_best_cards == ()
        assert result.recommended_card is None
        if self.phase == "preparation":
            assert self.counts[7] == {}
            assert result.work.preparation_units == result.work.sampled_worlds == 0
            assert result.work.materialized_worlds == result.work.card_transitions == 0
            assert result.work.terminal_evaluations == result.completed_common_worlds == 0
        else:
            assert self.counts[7] == {"sampled_worlds": 2, "card_transitions": 85}
            assert result.work.sampled_worlds == result.work.materialized_worlds == 2
            assert result.work.card_transitions == 85
            assert result.work.terminal_evaluations == 3
            assert result.completed_common_worlds == 1 < result.settings.requested_worlds
        assert all(row.completed_samples == result.completed_common_worlds
                   for row in result.candidates)

    def assert_complete(self, seed):
        result = self.results[seed]
        print("A2 complete", seed, asdict(result.work), dict(self.counts[seed]))
        assert result.status == "complete" and result.completed_common_worlds == 2
        assert result.ranked_cards and result.recommended_card is not None
        assert result.work.terminal_evaluations == 6
        assert result.work.card_transitions == 168
        assert self.counts[seed] == {"sampled_worlds": 2, "card_transitions": 168}


@pytest.fixture
def rollout_probe(monkeypatch):
    probe = RolloutProbe(monkeypatch)
    yield probe
    probe.release.set()


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
    def timed(view, settings, *, cancelled=None):
        ticks = iter(range(0, 1_000_000, 100))
        return evaluate(view, settings, clock=lambda: next(ticks), cancelled=cancelled)
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


@pytest.mark.parametrize("change", (
    "owner", "selection", "attempt", "generation", "archive_owner", "retired",
    "workspace", "fingerprint", "position", "explicit_selection", "ordinary_analysis"))
def test_real_work_cancellation_observes_each_owner(managed, rollout_probe, change, monkeypatch):
    import skatmind.app_web.match_rollout_frontend as frontend
    from skatmind.app_web.match_decision_selection import apply_match_decision_selection

    app, active = managed
    original = active.path.read_bytes()
    complete, _ = execute(app, active)
    store = archive_store(app)
    entry, = store.snapshot().manifest.evidence
    retained = store.read_evidence(entry.identity)
    archive_bytes = {path: path.read_bytes() for path in store.root.rglob("*.json")}
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(execute, app, active, random_seed="7")
        try:
            assert rollout_probe.entered.wait(60)
            # Checkpoint reads must stay in memory, even though final guards read disk.
            with monkeypatch.context() as patch:
                patch.setattr(frontend, "require_recording_fresh_v1",
                              lambda *a: pytest.fail("Cancellation read the recording"))
                assert rollout_probe.predicates[7]() is False
            with active.capture.lock:
                if change == "retired":
                    active.retired = True
                elif change == "workspace":
                    active.capture.workspace = alex_workspace(count=3)
                elif change == "fingerprint":
                    active.capture.content_fingerprint = "f" * 64
                elif change == "position":
                    select_unified_match_position_v1(active, 1)
                    select_unified_match_position_v1(active, 2)
                elif change == "explicit_selection":
                    apply_match_decision_selection(active, 3)
                elif change != "ordinary_analysis":
                    with app.lock:
                        mutate(app, active, change)
            if change == "ordinary_analysis":
                value = execute_unified_match_analysis_v1(active, {
                    "operation": "analyze_decision", "match_position": "2",
                    "decision_index": "3", "expected_revision": str(active.workspace.revision),
                    "immediate_sample_count": "1"})
                assert value.status == "applied"
            assert rollout_probe.predicates[7]() is True
        finally:
            rollout_probe.release.set()
        with pytest.raises((RecordingOpenConflict, StaleFrontendWorkflowRevisionError)):
            future.result()
    rollout_probe.assert_cancelled()
    assert active.pending_evidence is None and active.rollout_notice is None
    if change not in ("generation", "fingerprint"):
        assert complete in active.capture.report_store.list()
    assert store.snapshot().manifest.evidence == (entry,)
    assert store.read_evidence(entry.identity).downloads == retained.downloads
    assert {path: path.read_bytes() for path in store.root.rglob("*.json")} == archive_bytes
    assert active.path.read_bytes() == original


def test_independent_and_later_invocations_keep_their_own_cancellation(
    managed, tmp_path, rollout_probe,
):
    app, active = managed
    other_app, other_active = make_managed(tmp_path / "independent")
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(execute, app, active, random_seed="7")
        try:
            assert rollout_probe.entered.wait(60)
            execute(other_app, other_active)
            assert rollout_probe.predicates[7]() is False
            with active.capture.lock:
                active.rollout_attempt = object()
            assert rollout_probe.predicates[7]() is True
            assert rollout_probe.predicates[0]() is False
        finally:
            rollout_probe.release.set()
        with pytest.raises(RecordingOpenConflict):
            future.result()
    rollout_probe.assert_cancelled()
    rollout_probe.assert_complete(0)
    assert not active.capture.report_store.list() and active.pending_evidence is None
    assert not (app.managed_home.root / "automatic-learning").exists()
    execute(app, active, random_seed="1")
    rollout_probe.assert_complete(1)
    assert rollout_probe.predicates[0]() is False
    assert rollout_probe.predicates[1]() is False
    assert len(archive_store(app).snapshot().manifest.evidence) == 1
    assert len(archive_store(other_app).snapshot().manifest.evidence) == 1


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
                      lambda view, settings, *, cancelled=None: real(view, settings,
                          cancelled=lambda: (cancelled is not None and cancelled()) or True))
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
