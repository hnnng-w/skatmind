import pytest
from test_session_recorded_review import context_for, selection

from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.session_evidence_retention import save_pending_session
from skatmind.app_web.session_recorded_review import (
    RecordedDecisionReviewConflictError,
    execute_recorded_session_decision_v1,
)


def test_retry_is_persistence_only_for_original_execution(tmp_path, monkeypatch):
    import skatmind.app_web.session_recorded_review as producer
    import skatmind.automatic_learning_io as io
    app, active = context_for(tmp_path)
    original = io.write_temporary
    def fail(directory, raw):
        if directory.name == "reports":
            raise OSError("Controlled archive write fault")
        return original(directory, raw)
    monkeypatch.setattr(io, "write_temporary", fail)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    assert active.evidence_notice[1] == "unsaved"
    pending = active.pending_evidence
    execution = active.execution
    monkeypatch.setattr(io, "write_temporary", original)
    monkeypatch.setattr(producer, "execute_guided_frontend_review_v1",
                        lambda *a, **kw: pytest.fail("Retry must not execute"))
    assert save_pending_session(app, active, pending.token) == "saved"
    assert active.execution is execution
    retained = archive_store(app).read_evidence(pending.candidate.evidence.identity)
    assert retained.execution == execution
    with pytest.raises(RecordedDecisionReviewConflictError):
        save_pending_session(app, active, pending.token)


def test_post_commit_interruption_reports_authoritative_saved_state(tmp_path, monkeypatch):
    from skatmind.automatic_learning_store import AutomaticLearningStoreV1
    app, active = context_for(tmp_path)
    original = AutomaticLearningStoreV1.update_manifest
    def interrupted(store, *args, **kwargs):
        result = original(store, *args, **kwargs)
        if result.status == "saved":
            raise OSError("Controlled post-commit return fault")
        return result
    monkeypatch.setattr(AutomaticLearningStoreV1, "update_manifest", interrupted)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    assert active.evidence_notice[1] == "saved" and active.pending_evidence is None
    assert len(archive_store(app).snapshot().available_evidence_ids) == 1


def test_incomplete_retry_keeps_previous_complete_and_saves_actual_attempt(tmp_path, monkeypatch):
    import skatmind.automatic_learning_io as io
    from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1
    app, active = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, active, selection=selection(active),
        rollout_settings=WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=1,
                                                    wall_clock_timeout_ms=30000))
    complete = active.rollout_execution
    original = io.write_temporary
    def fail(directory, raw):
        if directory.name == "reports":
            raise OSError("Controlled incomplete-attempt archive failure")
        return original(directory, raw)
    monkeypatch.setattr(io, "write_temporary", fail)
    execute_recorded_session_decision_v1(app, active, selection=selection(active),
        rollout_settings=WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=1,
            max_card_transitions=1, wall_clock_timeout_ms=30000))
    pending = active.pending_evidence
    assert active.rollout_execution is complete and pending.execution is not complete
    assert active.evidence_notice[1] == "unsaved"
    monkeypatch.setattr(io, "write_temporary", original)
    monkeypatch.setattr("skatmind.app_web.session_recorded_review.execute_guided_frontend_review_v1",
                        lambda *a, **kw: pytest.fail("Retry must not evaluate"))
    assert save_pending_session(app, active, pending.token) == "saved"
    retained = archive_store(app).read_evidence(pending.candidate.evidence.identity)
    outcome = retained.execution.result.result.document["whole_game_rollout_result"]
    assert outcome["status"] != "complete"
    assert active.rollout_execution is complete
