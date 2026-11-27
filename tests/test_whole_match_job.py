from dataclasses import replace
from threading import Event

import pytest
from test_match_evidence_retention import change_source
from test_match_rollout_retention import RolloutProbe, execute, make_managed
from test_match_rollout_review import alex_workspace
from test_match_workspace_contracts import _observed_game, _set_game

import skatmind.application.execution as executor
import skatmind.automatic_learning_io as io
import skatmind.recommendation_workflow as workflow
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.match_frontend import UnifiedMatchContextV1
from skatmind.app_web.recorded_review_opening import RecordingOpenConflict
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.whole_match_job import (
    control,
    evidence_view,
    progress_file,
    proof,
    row_options,
)
from skatmind.app_web.whole_match_plan import own_plays
from skatmind.app_web.whole_match_web import configuration
from skatmind.capture_web.context import MatchCaptureWebContextV1


def config(active, **overrides):
    return configuration({"objective": "played_game_goal", "analysis_effort": "quick",
        "random_seed": "0", **overrides}, active.workspace, own_plays(active.workspace))


def submit(app, active, action="start", **changes):
    state = progress_file(app, active).read()
    with app.whole_match.lock:
        control(app, active, action, proof(active, state),
            configuration=config(active, **changes) if action == "start" else None)
        return app.whole_match.worker.thread


def finish(app, active, thread):
    thread.join(120)
    assert not thread.is_alive()
    return progress_file(app, active).read()


def restart(app, active):
    new = AppWebContextV1.create(app.managed_home)
    capture = MatchCaptureWebContextV1.open(active.path)
    current = UnifiedMatchContextV1(category_root=active.category_root, path=active.path,
        handle="b" * 64, capture=capture)
    new.managed_stateful.activate_match(current)
    return new, current


@pytest.fixture
def calls(monkeypatch):
    records = []
    real = executor.execute_application_invocation
    def counted(inv, **kwargs):
        records.append(inv.input_reference)
        return real(inv, **kwargs)
    monkeypatch.setattr(executor, "execute_application_invocation", counted)
    return records


def test_plan_uses_only_real_perspective_plays_and_per_game_inputs():
    rows = own_plays(alex_workspace())
    assert len(rows) == 10 and {row.position for row in rows} == {2}
    assert rows[-1].reason == "forced"
    partial = own_plays(alex_workspace(count=3, known_hand=False))
    assert [(r.key, r.reason) for r in partial] == [("2:3", "acting_hand_unavailable")]
    workspace = alex_workspace(count=3)
    inputs = {"objective": "complete_settlement", "analysis_effort": "standard", "random_seed": "9"}
    settings, extras = configuration(inputs, workspace, rows)
    assert (settings.requested_worlds, settings.wall_clock_timeout_ms, extras) == (100, 30000, {})
    assert rows[0].options(settings, extras) is None
    expected = {"2": {"matadors": 3}}
    assert configuration({**inputs, "matadors_2": "3"}, workspace, rows)[1] == expected
    with pytest.raises(ValueError):
        configuration({**inputs, "matadors_1": "3"}, workspace, rows)

    game = workspace.slots[1].observed_game
    workspace = _set_game(workspace, _observed_game(workspace.match_definition, match_position=5,
        plays=game.plays, declaration=game.declaration, declarer_player_id=game.declarer_player_id,
        perspective_initial_hand=game.perspective_initial_hand))
    a, b = rows = own_plays(workspace)
    settings, supplements = configuration({**inputs, "matadors_2": "1"}, workspace, rows)
    assert a.options(settings, supplements[str(a.position)]).settlement_supplements == {
        "matadors": 1}
    assert b.options(settings, supplements.get(str(b.position), {})) is None


def test_selected_execution_reuse_restart_and_changed_settings(tmp_path, calls):
    from skatmind.app_web.settings_forms import set_ordinary_preferences_v1

    app, active = make_managed(tmp_path / "home")
    execute(app, active, analysis_effort="quick", settings_mode="ordinary")
    assert len(calls) == 1
    state = finish(app, active, submit(app, active))
    assert state["phase"] == "finished" and state["refs"]["2:3"][0] == "reused"
    set_ordinary_preferences_v1(app, {"own_player_handle": "", "platform_choice": "",
        "custom_platform": "", "analysis_effort": "more_time"},
        generation=app.frontend_profile.generation)
    app, active = restart(app, active)
    assert progress_file(app, active).read() == state
    resumed = finish(app, active, submit(app, active, "resume"))
    assert resumed["refs"] == state["refs"] and resumed["settings"] == state["settings"]
    assert len(calls) == 1
    changed = finish(app, active, submit(app, active, random_seed="19"))
    assert changed["refs"]["2:3"][0] == "computed" and len(calls) == 2


@pytest.mark.parametrize("action", ["cancel", "correct", "delete", "supersede"])
def test_cancel_or_source_change_during_real_work(tmp_path, monkeypatch, calls, action):
    app, active = make_managed(tmp_path / "home")
    probe = RolloutProbe(monkeypatch)
    thread = submit(app, active, random_seed="7")
    try:
        assert probe.entered.wait(20)
        with pytest.raises(RecordingOpenConflict):
            submit(app, active)
        other, reopened = restart(app, active)
        with pytest.raises((OSError, RecordingOpenConflict)):
            submit(other, reopened, "resume")
        if action == "correct":
            change_source(active)
        elif action == "delete":
            active.path.unlink()
        elif action == "supersede":
            progress = progress_file(app, active)
            newer = {**progress.read(), "run": "f" * 64, "phase": "paused"}
            progress.write(newer)  # Inject a changed authority just before publication.
        else:
            submit(app, active, "cancel")
    finally:
        probe.release.set()
    state = finish(app, active, thread)
    assert len(calls) == 1
    if action == "supersede":
        assert state == newer and archive_store(app) is None
    elif action != "cancel":
        assert not state["refs"] and archive_store(app) is None
        with pytest.raises((RecordingOpenConflict, FileNotFoundError)):
            submit(app, active, "resume")
    else:
        result = probe.results[7]
        assert result.status == "cancelled" and not result.ranked_cards
        assert result.work.card_transitions == 85 and result.completed_common_worlds == 1
        assert state["phase"] == "paused"
        app, active = restart(app, active)
        state = finish(app, active, submit(app, active, "resume"))
        assert state["phase"] == "finished" and len(calls) == 2


@pytest.mark.parametrize("failure", ["quota", "after_commit"])
def test_save_boundary_and_save_only_retry(tmp_path, monkeypatch, calls, failure):
    app, active = make_managed(tmp_path / "home")
    store = archive_store(app, initialize=True)
    with monkeypatch.context() as patch:
        if failure == "quota":
            patch.setattr(store, "limits", replace(store.limits, total_bytes=1000,
                                                  object_bytes=1000))
        else:
            real = store.update_manifest
            def interrupted(*args, **kwargs):
                assert real(*args, **kwargs).status == "saved"
                raise OSError("Interrupted after evidence commit")
            patch.setattr(store, "update_manifest", interrupted)
        state = finish(app, active, submit(app, active))
        assert state["phase"] == ("quota" if failure == "quota" else "unsaved")
        assert state["refs"]["2:3"][0] == "saving"
    if failure == "after_commit":
        app, active = restart(app, active)
    state = finish(app, active, submit(app, active, "resume"))
    assert state["phase"] == "finished" and state["refs"]["2:3"][0] == "computed"
    assert len(calls) == 1


@pytest.mark.parametrize("missing", [False, True])
def test_final_evidence_check_and_reopened_exclusion(tmp_path, calls, missing):
    app, active = make_managed(tmp_path / "home")
    state = finish(app, active, submit(app, active))
    store = archive_store(app)
    entry, = store.snapshot().manifest.evidence
    options = row_options(own_plays(active.workspace), state)
    with evidence_view(app, active.workspace, state["source"], options) as (values, _, guard):
        assert entry.identity in values
        path = io.object_path(store.root, entry.envelope)
        if missing:
            path.unlink()
        else:
            path.write_bytes(b"{}")
        with pytest.raises(RecordingOpenConflict):
            guard()
    with evidence_view(app, active.workspace, state["source"], options) as (values, _, guard):
        assert not values
        guard()
    assert len(calls) == 1


def test_timeout_has_original_but_no_comparison_until_explicit_retry(tmp_path, calls, monkeypatch):
    app, active = make_managed(tmp_path / "home")
    original = workflow.evaluate_whole_game_rollout_v1
    def timed(*args, **kwargs):
        ticks = iter(range(0, 1000000, 100))
        return original(*args, clock=lambda: next(ticks), **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(workflow, "evaluate_whole_game_rollout_v1", timed)
        state = finish(app, active, submit(app, active))
    store = archive_store(app)
    attempt = store.read_evidence(state["refs"]["2:3"][1])
    assert attempt.report.value.result.document["whole_game_rollout_result"]["status"] == "timeout"
    assert attempt.comparison is None and attempt.download("result")[1]
    state = finish(app, active, submit(app, active, "resume"))
    assert store.read_evidence(state["refs"]["2:3"][1]).comparison is not None and len(calls) == 2


def test_exact_file_replacement_requires_new_consent(tmp_path, calls):
    app, active = make_managed(tmp_path / "home")
    state = finish(app, active, submit(app, active))
    replacement = tmp_path / "copy.json"
    replacement.write_bytes(active.path.read_bytes())
    replacement.replace(active.path)
    with pytest.raises(RecordingOpenConflict):
        submit(app, active, "resume")
    assert archive_store(app).read_evidence(state["refs"]["2:3"][1]).comparison
    assert len(calls) == 1


def test_later_save_failure_keeps_first_original_and_resume_skips_it(tmp_path, calls, monkeypatch):
    app, active = make_managed(tmp_path / "home")
    assert active.capture.save_candidate(alex_workspace(count=6)) == "saved"
    store = archive_store(app, initialize=True)
    original = store.publish_object
    with monkeypatch.context() as p:
        def fail_second(obj, **kw):
            if obj.area == "reports" and len(calls) == 2:
                raise OSError("Second report write failed.")
            return original(obj, **kw)
        p.setattr(store, "publish_object", fail_second)
        state = finish(app, active, submit(app, active))
    assert state["phase"] == "unsaved" and len(calls) == 2
    first = store.read_evidence(state["refs"]["2:3"][1])
    state = finish(app, active, submit(app, active, "resume"))
    assert state["phase"] == "finished" and len(calls) == 2
    assert store.read_evidence(state["refs"]["2:3"][1]).downloads == first.downloads
    assert state["refs"]["2:5"][0] == "computed"


def test_damaged_checkpoint_fails_closed_without_execution(tmp_path, calls):
    app, active = make_managed(tmp_path / "home")
    progress = progress_file(app, active)
    finish(app, active, submit(app, active))
    progress.path.write_bytes(progress.path.read_bytes().replace(b'"random_seed":0',
                                                                 b'"random_seed":1'))
    with pytest.raises(ValueError, match="progress"):
        submit(app, active, "resume")
    assert len(calls) == 1


@pytest.mark.parametrize("change", [False, True])
def test_progress_and_cancel_remain_available_during_archive_validation(
        tmp_path, calls, monkeypatch, change):
    app, active = make_managed(tmp_path / "home")
    store = archive_store(app, initialize=True)
    real = store._validate_update
    entered, release = Event(), Event()
    def paused(*args):
        entered.set()
        assert release.wait(30)
        return real(*args)
    monkeypatch.setattr(store, "_validate_update", paused)
    thread = submit(app, active)
    try:
        assert entered.wait(30)
        for lock in (active.capture.lock, app.lock):
            assert lock.acquire(blocking=False)
            lock.release()
        if change:
            change_source(active)
        else:
            submit(app, active, "cancel")
    finally:
        release.set()
    state = finish(app, active, thread)
    assert len(calls) == 1
    if change:
        assert not store.snapshot().manifest.evidence
        assert state["refs"]["2:3"][0] == "saving"
    else:
        assert state["phase"] == "paused" and state["refs"]["2:3"][0] == "computed"
