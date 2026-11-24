from dataclasses import replace
from threading import Event

import pytest
from test_match_rollout_retention import make_managed
from test_match_workspace_contracts import _observed_game, _set_game
from test_session_recorded_review import context_for
from test_whole_match_job import finish, restart, submit

from skatmind.app_web import session_batch, whole_match_job, whole_match_plan
from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.recorded_review_opening import RecordingOpenConflict
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.session_frontend import GuidedSessionContextV1
from skatmind.app_web.whole_match_web import batch_settings


def test_game_batch_freezes_before_planning_and_whole_reuses_exact_original(tmp_path, monkeypatch):
    app, active = make_managed(tmp_path / "home")
    game = active.workspace.slots[1].observed_game
    workspace = _set_game(active.workspace, _observed_game(active.workspace.match_definition,
        match_position=5, plays=game.plays, declaration=game.declaration,
        declarer_player_id=game.declarer_player_id,
        perspective_initial_hand=game.perspective_initial_hand))
    assert active.capture.save_candidate(workspace) == "saved"
    calls = []
    real = whole_match_job.execute_match_decision_analysis_v1
    def evaluate(*args, **kwargs):
        calls.append(kwargs["match_position"])
        return real(*args, **kwargs)
    monkeypatch.setattr(whole_match_job, "execute_match_decision_analysis_v1", evaluate)
    reconstructed = []
    reconstruct = whole_match_plan.build_match_observed_game_reconstruction_v1
    def recorded(game, **kwargs):
        reconstructed.append(game.match_position)
        return reconstruct(game, **kwargs)
    monkeypatch.setattr(whole_match_plan, "build_match_observed_game_reconstruction_v1", recorded)
    settings = batch_settings({"objective": "played_game_goal", "analysis_effort": "quick"})
    with app.whole_match.lock:
        whole_match_job.control(app, active, "start",
            whole_match_job.proof(active, None, requested_game=2), game=2,
            configuration=(settings, {}))
        thread = app.whole_match.worker.thread
        active.selected_position = 5
    scoped = finish(app, active, thread)
    assert scoped["game"] == 2 and scoped["version"] == 2
    assert calls == [2] and set(scoped["refs"]) == {"2:3"}
    assert reconstructed == [2]
    app, active = restart(app, active)
    resumed = finish(app, active, submit(app, active, "resume"))
    assert resumed["refs"] == scoped["refs"] and calls == [2]
    whole = finish(app, active, submit(app, active))
    assert whole["version"] == 1 and "game" not in whole
    assert calls == [2, 5] and whole["refs"]["2:3"] == ["reused", scoped["refs"]["2:3"][1]]
    service = AutomaticMatchLearningServiceV1.open(app)
    first = service.update().generation
    excluded = whole["refs"]["2:3"][1]
    remaining = whole["refs"]["5:3"][1]
    assert set(first.recipe.evidence_ids) == {excluded, remaining}
    store = archive_store(app)
    original = store.read_evidence(excluded).download("result")
    before = store.snapshot().manifest
    assert store.update_manifest(replace(before, revision=before.revision + 1,
        excluded_analysis_ids=(excluded,)), expected_manifest=before.fingerprint).status == "saved"
    assert service.inspect().status == "excluded"
    assert service.update().generation.recipe.evidence_ids == (remaining,)
    app, active = restart(app, active)
    assert finish(app, active, submit(app, active, "resume"))["refs"] == whole["refs"]
    assert archive_store(app).read_evidence(excluded).download("result") == original
    assert archive_store(app).snapshot().manifest.excluded_analysis_ids == (excluded,)
    assert calls == [2, 5]


@pytest.mark.parametrize("fail_save", (False, True))
def test_session_checkpoint_batch_resume_preserves_original(tmp_path, monkeypatch, fail_save):
    app, active = context_for(tmp_path)
    disk = active.path.read_bytes()
    settings = batch_settings({"objective": "played_game_goal", "analysis_effort": "quick"})
    def run(action):
        state = session_batch.progress_file(app, active).read()
        with app.session_batch.lock:
            session_batch.control(app, active, action, session_batch.proof(active, state),
                                  (settings, {}))
            thread = app.session_batch.worker.thread
        thread.join(120)
        assert not thread.is_alive()
        return session_batch.progress_file(app, active).read()

    calls = []
    real = session_batch.execute_recorded_session_decision_v1
    def evaluate(*args, **kwargs):
        calls.append(kwargs["selection"])
        return real(*args, **kwargs)
    monkeypatch.setattr(session_batch, "execute_recorded_session_decision_v1", evaluate)
    store = archive_store(app, initialize=True)
    with monkeypatch.context() as patch:
        if fail_save:
            def unavailable(*args, **kwargs):
                raise OSError("Disposable save failure.")
            patch.setattr(store, "update_manifest", unavailable)
        state = run("start")
    if fail_save:
        assert state["phase"] == "unsaved" and active.pending_evidence is not None
        pending = active.pending_evidence.execution.result_json_bytes
        from skatmind.app_web.session_recorded_review import RecordedDecisionReviewConflictError
        with active.lock, pytest.raises(RecordedDecisionReviewConflictError):
            active.begin_execution()
        state = run("resume")
    assert state["phase"] == "finished" and len(state["refs"]) == 1 and len(calls) == 1
    identity = next(iter(state["refs"].values()))[1]
    retained = store.read_evidence(identity)
    assert retained.checkpoint in active.document.decision_checkpoints
    if fail_save:
        assert retained.download("result")[1] == pending
    app = AppWebContextV1.create(app.managed_home)
    active = GuidedSessionContextV1(category_root=active.category_root, path=active.path,
                                    handle="b" * 64, document=active.document)
    app.managed_stateful.activate_session(active)
    assert run("resume")["refs"] == state["refs"] and len(calls) == 1
    assert active.path.read_bytes() == disk


@pytest.mark.parametrize("interruption", ("cancel", "supersede", "replace_file"))
def test_session_run_authority_at_unlocked_execution(tmp_path, monkeypatch, interruption):
    from skatmind.app_web import session_recorded_review as review

    app, active = context_for(tmp_path)
    progress = session_batch.progress_file(app, active)
    entered, release = Event(), Event()
    execute = review.execute_guided_frontend_review_v1
    def wait_for_action(*args, **kwargs):
        entered.set()
        assert release.wait(30)
        return execute(*args, **kwargs)
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", wait_for_action)
    before = session_batch.proof(active, None)
    settings = batch_settings({"objective": "played_game_goal", "analysis_effort": "quick"})
    session_batch.control(app, active, "start", before, (settings, {}))
    worker = app.session_batch.worker
    try:
        assert entered.wait(30)
        with pytest.raises(RecordingOpenConflict):
            session_batch.control(app, active, "cancel", before)
        if interruption == "cancel":
            binding = session_batch.proof(active, progress.read())
            session_batch.control(app, active, "cancel", binding)
        elif interruption == "supersede":
            with active.lock:
                active.begin_execution()
        else:
            copy = active.path.with_suffix(".copy")
            copy.write_bytes(active.path.read_bytes())
            copy.replace(active.path)
    finally:
        release.set()
        worker.thread.join(120)
    assert not worker.thread.is_alive()
    if interruption == "cancel":
        assert progress.read()["phase"] == "paused" and len(progress.read()["refs"]) == 1
    else:
        assert not progress.read()["refs"] and archive_store(app) is None
