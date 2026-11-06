from dataclasses import replace

import pytest
from test_automatic_match_learning import save
from test_session_recorded_review import context_for, selection

from skatmind.app_web.automatic_learning_controller import automatic_controller
from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.session_frontend import rewind_guided_session_v1
from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1
from skatmind.automatic_learning_store import StoreConflictError
from skatmind.session_persistence import save_session_persistence_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1


def test_session_only_preparation_reuse_and_restart_execute_nothing(tmp_path, monkeypatch):
    app, active = context_for(tmp_path)
    original = active.path.read_bytes()
    service = AutomaticMatchLearningServiceV1.open(app)
    first = service.update()
    assert first.status == "prepared"
    bundle = service.consume(lambda value: value)
    assert bundle.sources == ()
    assert dict((row.name, row.value) for row in bundle.session_coverage) == {
        "sessions": "1", "recorded_plays": "1", "own_plays": "1", "eligible_decisions": "1",
        "covered_decisions": "0", "retained_executions": "0", "missing_checkpoints": "0",
        "no_perspective": "0"}
    before = service.store.snapshot().manifest
    monkeypatch.setattr("skatmind.app_web.automatic_match_learning.build_mixed_bundle",
                        lambda *a, **kw: pytest.fail("Unchanged update must not prepare"))
    assert service.update().status == "reused"
    monkeypatch.undo()
    reopened = AppWebContextV1.create(app.managed_home)
    new = AutomaticMatchLearningServiceV1.open(reopened)
    assert new.inspect().status == "reconstruction_needed"
    assert new.update().status == "rebuilt"
    assert new.store.snapshot().manifest == before
    assert active.path.read_bytes() == original


def test_native_both_families_cover_one_decision_and_keep_incomplete_attempt(tmp_path):
    app, active = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    assert active.evidence_notice[1] == "saved"
    settings = WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=1,
                                         wall_clock_timeout_ms=30000)
    execute_recorded_session_decision_v1(app, active, selection=selection(active),
                                         rollout_settings=settings)
    assert active.evidence_notice[1] == "saved"
    complete = active.rollout_execution
    assert complete.result.result.document["whole_game_rollout_result"]["status"] == "complete"
    # Genuine work-budget-limited attempt, not a forged Result outcome.
    execute_recorded_session_decision_v1(app, active, selection=selection(active),
        rollout_settings=replace(settings, max_card_transitions=1))
    assert active.rollout_execution is complete
    assert active.rollout_notice is not None
    assert active.evidence_notice[1] == "saved"
    store = archive_store(app)
    values = tuple(store.read_evidence(key) for key in store.snapshot().available_evidence_ids)
    assert len(values) == 3
    assert sum(row.entry.evidence_class == "rollout" for row in values) == 2
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    coverage = dict((row.name, row.value) for row in service._installed.bundle.session_coverage)
    assert (coverage["covered_decisions"], coverage["retained_executions"]) == ("1", "3")


def test_session_changes_leave_ten_match_exports_identical(tmp_path):
    app, active = context_for(tmp_path)
    save(app)
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    before = service._installed.bundle.downloads
    revision = service._installed.generation.match_catalog_revision
    changed = build_session_persistence_document_v1(active.state, decision_checkpoints=())
    assert save_session_persistence_file_v1(active.path, changed,
        expected_content_fingerprint=active.document.content_fingerprint).status == "saved"
    assert service.inspect().status == "outdated"
    assert service.update().status == "prepared"
    assert service._installed.bundle.downloads == before
    assert service._installed.generation.match_catalog_revision == revision


def test_duplicate_sessions_are_excluded_without_selecting_a_winner(tmp_path):
    app, active = context_for(tmp_path)
    active.path.with_name("duplicate.json").write_bytes(active.path.read_bytes())
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    assert service._installed.bundle.session_sources == ()
    assert len(service._installed.generation.recipe.exclusions) == 1
    assert service._installed.generation.recipe.exclusions[0].reason == "ambiguous"


@pytest.mark.parametrize("change", ("delete", "checkpoint_only", "accepted_restore"))
def test_source_changes_during_preparation_reject_original_attempt(tmp_path, monkeypatch, change):
    import skatmind.app_web.automatic_match_learning as module
    app, active = context_for(tmp_path)
    service = AutomaticMatchLearningServiceV1.open(app)
    original = module.build_mixed_bundle

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        if change == "delete":
            active.path.unlink()
        else:
            stripped = build_session_persistence_document_v1(active.state, decision_checkpoints=())
            save_session_persistence_file_v1(active.path, stripped,
                expected_content_fingerprint=active.document.content_fingerprint)
            if change == "accepted_restore":
                save_session_persistence_file_v1(active.path, active.document,
                    expected_content_fingerprint=stripped.content_fingerprint)
        return result
    monkeypatch.setattr(module, "build_mixed_bundle", changed)
    assert service.update().status == "conflict"
    assert service._installed is None


def test_exact_version_isolation_exclusion_and_final_delivery(tmp_path):
    app, active = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    controller = automatic_controller(app)
    assert controller.service.update().status == "prepared"
    view = controller.capture()
    rewind_guided_session_v1(active, target_revision=active.state.revision - 1)
    with pytest.raises(StoreConflictError):
        controller.service.validate_delivery(view.binding)
    assert controller.service.update().status == "prepared"
    assert controller.service._installed.bundle.session_evidence == ()
    assert len(archive_store(app).snapshot().available_evidence_ids) == 1
    view = controller.capture()
    confirmation = controller.preview_exclusion(view, 0)
    controller.confirm(confirmation.token)
    assert controller.service.inspect().status == "excluded"
    assert controller.service.update().status == "prepared"
    assert controller.service._installed.bundle.session_sources == ()
