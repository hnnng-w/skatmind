"""Managed producer, source/owner races and explicitly controlled storage faults."""

from collections import Counter
from dataclasses import replace

import pytest
from test_match_decision_analysis import _complete_workspace

import skatmind.automatic_learning_io as io
import skatmind.capture_web.analysis as producer
import skatmind.match_decision_analysis as engine
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.match_evidence_retention import save_pending_match
from skatmind.app_web.match_frontend import UnifiedMatchContextV1, execute_unified_match_analysis_v1
from skatmind.app_web.recorded_review_opening import RecordingOpenConflict
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.automatic_learning_store import DEFAULT_LIMITS, StoreLimitsV1
from skatmind.capture_web.context import MatchCaptureWebContextV1
from skatmind.match_workspace_contracts import _build_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def managed(tmp_path):
    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "home"))
    root = app.managed_stateful.root("matches")
    capture = MatchCaptureWebContextV1.open(root / "synthetic.json")
    assert capture.save_candidate(_complete_workspace()) == "saved"
    active = UnifiedMatchContextV1(category_root=root, path=capture.workspace_path,
        handle="a" * 64, capture=capture, selected_position=3)
    app.managed_stateful.activate_match(active)
    return app, active


def execute(app, active, **changes):
    return execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "3", "decision_index": "28",
        "expected_revision": str(active.workspace.revision), "immediate_sample_count": "1",
        **changes}, app_context=app)


def change_source(active):
    changed = _build_match_workspace_v1(revision=active.workspace.revision,
        slots=active.workspace.slots, match_definition=replace(
        active.workspace.match_definition, title="External same-revision correction"))
    assert changed.revision == active.workspace.revision
    assert save_match_workspace_file_v1(active.path,
        build_match_workspace_persistence_document_v1(changed),
        expected_content_fingerprint=active.capture.content_fingerprint).status == "saved"


def test_genuine_capture_idempotent_and_passive_accounting(managed, monkeypatch):
    app, active = managed
    calls = Counter()
    store = archive_store(app, initialize=True)  # Explicit fixture initialization.
    original = active.path.read_bytes()
    real_write, real_execute = io.write_temporary, engine.execute_application_invocation
    def write(directory, raw):
        calls[directory.name] += 1
        return real_write(directory, raw)
    def evaluate(*args, **kwargs):
        calls["evaluate"] += 1
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(io, "write_temporary", write)
    monkeypatch.setattr(engine, "execute_application_invocation", evaluate)
    assert execute(app, active).status == "applied"
    assert calls == {"evaluate": 1, "sources": 1, "reports": 1, "automatic-learning": 1}
    entry, = store.snapshot().manifest.evidence
    value = store.read_evidence(entry.identity)
    before = calls.copy()
    for _ in range(2):
        assert store.read_evidence(entry.identity).downloads == value.downloads
    assert calls == before
    # Explicit second execution yields the same exact Immediate evidence, no writes.
    assert execute(app, active).status == "applied"
    assert calls == {**before, "evaluate": 2}
    assert store.snapshot().manifest.evidence == (entry,)
    assert active.path.read_bytes() == original


@pytest.mark.parametrize("fault", ("object", "manifest", "post_replace", "busy", "quota"))
def test_save_only_failure_retry_and_authoritative_commit(managed, monkeypatch, fault):
    app, active = managed
    store = archive_store(app, initialize=True)
    before = active.path.read_bytes()
    real_write, real_sync, real_publish = (
        io.write_temporary, io.sync_directory, store.publish_object)
    calls = Counter()
    real_execute = engine.execute_application_invocation
    def evaluate(*args, **kwargs):
        calls["evaluate"] += 1
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(engine, "execute_application_invocation", evaluate)
    def fail_write(directory, raw):
        if directory.name == ("reports" if fault == "object" else "automatic-learning"):
            raise OSError("Controlled pre-commit failure")
        return real_write(directory, raw)
    if fault in {"object", "manifest"}:
        monkeypatch.setattr(io, "write_temporary", fail_write)
    elif fault == "post_replace":
        def fail_sync(directory):
            if directory == store.root:
                raise OSError("Controlled post-replacement return failure")
            real_sync(directory)
        monkeypatch.setattr(io, "sync_directory", fail_sync)
    elif fault == "busy":
        monkeypatch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
    else:
        store.limits = StoreLimitsV1(total_bytes=1)
    assert execute(app, active).status == "applied"
    report, = active.capture.report_store.list()
    assert report.value.status == "executed" and calls["evaluate"] == 1
    assert active.evidence_notice[1] == ("saved" if fault == "post_replace" else "unsaved")
    assert not store._coordinator.candidates
    monkeypatch.setattr(io, "write_temporary", real_write)
    monkeypatch.setattr(io, "sync_directory", real_sync)
    monkeypatch.setattr(store, "publish_object", real_publish)
    store.limits = DEFAULT_LIMITS
    if fault != "post_replace":
        pending = active.pending_evidence
        assert save_pending_match(app, active, pending.token) == "saved"
        with pytest.raises(RecordingOpenConflict):
            save_pending_match(app, active, pending.token)
    entry, = store.snapshot().manifest.evidence
    assert store.read_evidence(entry.identity).report == report
    assert calls["evaluate"] == 1 and active.path.read_bytes() == before


@pytest.mark.parametrize("phase", ("execution", "staging", "manifest"))
@pytest.mark.parametrize("change", ("owner", "source", "selection", "attempt", "generation"))
def test_changed_authority_cannot_commit(managed, monkeypatch, phase, change):
    app, active = managed
    store = archive_store(app, initialize=True)
    changed = False
    def mutate():
        nonlocal changed
        if changed:
            return
        changed = True
        if change == "owner":
            app.managed_stateful.activate_match(replace(active, handle="b" * 64))
        elif change == "source":
            change_source(active)
        elif change == "selection":
            active.review_decision_generation += 1
        elif change == "attempt":
            active.rollout_attempt = object()
        else:
            active.capture.report_store.clear()
    if phase == "execution":
        real = producer.execute_match_decision_analysis_v1
        def execution(*args, **kwargs):
            value = real(*args, **kwargs)
            mutate()
            return value
        monkeypatch.setattr(producer, "execute_match_decision_analysis_v1", execution)
    elif phase == "staging":
        real = store.publish_object
        def publish(*args, **kwargs):
            value = real(*args, **kwargs)
            mutate()
            return value
        monkeypatch.setattr(store, "publish_object", publish)
    else:
        real = io.write_temporary
        def write(directory, raw):
            value = real(directory, raw)
            if directory == store.root:
                mutate()
            return value
        monkeypatch.setattr(io, "write_temporary", write)
    try:
        result = execute(app, active)
        assert result.status == "revision_conflict"
    except RecordingOpenConflict:
        pass
    assert changed and not store.snapshot().manifest.evidence
    assert not store._coordinator.candidates


@pytest.mark.parametrize("change", (
    "owner", "source", "attempt", "generation", "selection", "archive_owner",
))
def test_expired_retry_does_not_write_or_execute(managed, monkeypatch, change):
    app, active = managed
    store = archive_store(app, initialize=True)
    with monkeypatch.context() as patch:
        patch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
        execute(app, active)
    token = active.pending_evidence.token
    if change == "owner":
        app.managed_stateful.activate_match(replace(active, handle="b" * 64))
    elif change == "source":
        change_source(active)
    elif change == "attempt":
        active.rollout_attempt = object()
    elif change == "generation":
        active.capture.report_store.clear()
    elif change == "selection":
        active.review_decision_generation += 1
    else:
        from skatmind.app_web.saved_match_analyses import SavedMatchAnalyses
        app.saved_match_analyses = SavedMatchAnalyses()
    monkeypatch.setattr(io, "write_temporary", lambda *a, **kw: pytest.fail("Expired retry wrote"))
    monkeypatch.setattr(engine, "execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Retry evaluated"))
    with pytest.raises(RecordingOpenConflict):
        save_pending_match(app, active, token)
    assert not store.snapshot().manifest.evidence


@pytest.mark.parametrize("case", (
    "rejected", "unavailable", "execution_error", "materialization", "historical",
))
def test_ineligible_operations_never_initialize_archive(managed, monkeypatch, case):
    app, active = managed
    root = app.managed_home.root / "automatic-learning"
    if case == "rejected":
        with pytest.raises(ValueError):
            execute(app, active, recommendation_method="unsupported")
    elif case == "unavailable":
        assert execute(app, active, match_position="1").status == "applied"
    elif case == "execution_error":
        def fail(*args, **kwargs):
            raise RuntimeError("Controlled execution failure")
        monkeypatch.setattr(engine, "execute_application_invocation", fail)
        with pytest.raises(RuntimeError):
            execute(app, active)
    elif case == "historical":
        result = execute_unified_match_analysis_v1(active, {
            "operation": "analyze_historical_game", "match_position": "3",
            "expected_revision": str(active.workspace.revision), "decision_snapshots": "true"},
            app_context=app)
        assert result.status == "applied"
    else:
        result = execute_unified_match_analysis_v1(active, {
            "operation": "prepare_materialization", "match_position": "3",
            "expected_revision": str(active.workspace.revision)}, app_context=app)
        assert result.status == "applied"
    assert not root.exists()


@pytest.mark.parametrize("change", ("source", "owner", "attempt", "selection"))
def test_retry_staging_revalidates_authority(managed, monkeypatch, change):
    app, active = managed
    store = archive_store(app, initialize=True)
    with monkeypatch.context() as patch:
        patch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
        execute(app, active)
    pending = active.pending_evidence
    real = store.publish_object
    changed = False
    def publish(*args, **kwargs):
        nonlocal changed
        value = real(*args, **kwargs)
        if not changed:
            changed = True
            if change == "source":
                change_source(active)
            elif change == "owner":
                app.managed_stateful.activate_match(replace(active, handle="b" * 64))
            elif change == "attempt":
                active.rollout_attempt = object()
            else:
                active.review_decision_generation += 1
        return value
    monkeypatch.setattr(store, "publish_object", publish)
    monkeypatch.setattr(engine, "execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Retry evaluated"))
    with pytest.raises(RecordingOpenConflict):
        save_pending_match(app, active, pending.token)
    assert not store.snapshot().manifest.evidence and not store._coordinator.candidates


def test_abandoned_publication_does_not_release_newer_pending_reservation(managed, monkeypatch):
    app, active = managed
    store = archive_store(app, initialize=True)
    with monkeypatch.context() as patch:
        patch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
        execute(app, active)
    old = active.pending_evidence
    newer = replace(old, token="b" * 64, attempt=object())
    real = store.publish_object
    reservations = []
    def publish(*args, **kwargs):
        result = real(*args, **kwargs)
        if not reservations:
            reservations.append(store.begin_candidate(old.candidate.objects))
            active.pending_evidence = newer
            active.rollout_attempt = newer.attempt
        return result
    monkeypatch.setattr(store, "publish_object", publish)
    with pytest.raises(RecordingOpenConflict):
        save_pending_match(app, active, old.token)
    assert active.pending_evidence is newer
    assert store._coordinator.candidates[store.owner] is reservations[0]
    store.release_candidate(reservations[0])  # Explicit disposable-fixture release.
