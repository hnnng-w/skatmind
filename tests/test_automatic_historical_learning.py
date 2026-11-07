"""S7 live heads, native producer separation, mixed restart and Match continuity."""

from dataclasses import replace

import pytest
from test_automatic_historical_evidence import genuine_historical
from test_automatic_match_learning import save, setup_service
from test_guided_historical_review_form import _completed_example_draft

from skatmind.app_web.automatic_learning_controller import automatic_controller
from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.historical_form import update_historical_options_v1
from skatmind.app_web.historical_review_retention import (
    capture_attempt,
    retain_manual_review,
    save_pending_historical,
)
from skatmind.app_web.saved_historical_reviews import (
    ReviewDeletionPreview,
    delete_review,
    reopen_review,
)
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.workflow_operations import run_guided_review_v1, start_review_v1
from skatmind.automatic_learning_store import StoreConflictError

__all__ = ["genuine_historical"]


def retain_fixture(app, genuine, *, imported=False, expect_saved=True):
    """Reuse immutable genuine execution; fresh producer owner and lifecycle per test."""
    draft, execution, native = genuine
    app.historical_reviews.new("imported" if imported else "guided")
    state = app.review_state.mutate(expected_revision=app.review_state.revision, **(
        {"imported_request": execution.request} if imported else {"draft": draft}))
    app.review_state = state.begin(expected_revision=state.revision)
    attempt = capture_attempt(app, app.review_state)
    app.review_state = app.review_state.publish(expected_revision=state.revision,
        execution_revision=state.revision, request=execution.request, options=execution.options,
        result=execution.result, request_json_bytes=execution.request_json_bytes,
        result_json_bytes=execution.result_json_bytes)
    retain_manual_review(app, attempt, app.review_state, execution, native)
    assert app.historical_reviews.notice[1] == ("saved" if expect_saved else "unsaved")
    return app.historical_reviews.head


def remove_head(app, controller, index=0):
    view = controller.capture()
    head = view.binding.resumed.manifest.historical_heads[index]
    value = controller.service.store.read_evidence(head.evidence_id)
    preview = ReviewDeletionPreview("original-consent", view, index, head, value)
    app.historical_reviews.confirmation = preview
    delete_review(app, controller, preview)


def test_two_genuine_guided_producers_keep_independent_people_and_games(tmp_path):
    app, service = setup_service(tmp_path)
    draft = update_historical_options_v1(_completed_example_draft())
    for label in ("Alice", "Dora"):
        start_review_v1(app, expected_revision=app.review_state.revision)
        edited = replace(draft, players=(replace(draft.players[0], player_label=label),
                                        *draft.players[1:]))
        app.review_state = app.review_state.mutate(expected_revision=app.review_state.revision,
                                                   draft=edited)
        run_guided_review_v1(app, expected_revision=app.review_state.revision)
        assert app.historical_reviews.notice[1] == "saved"
    assert len(archive_store(app).snapshot().manifest.historical_heads) == 2
    assert service.update().status == "prepared"
    bundle = service._installed.bundle
    assert dict((row.name, row.value) for row in bundle.historical_coverage)["participants"] == "6"
    assert len(bundle.historical_sources) == 2
    assert len({row.game.game_id for row in bundle.historical_sources}) == 1
    assert len({row.record.scope for row in bundle.historical_sources}) == 2
    assert bundle.sources == bundle.evidence == ()


def test_restart_exact_bytes_no_evaluation_and_unchanged_update(
    tmp_path, genuine_historical, monkeypatch,
):
    app, service = setup_service(tmp_path)
    head = retain_fixture(app, genuine_historical)
    import skatmind.app_web.execution as execution_module
    monkeypatch.setattr(execution_module, "execute", lambda *a, **k: pytest.fail("Analysis"))
    assert service.update().status == "prepared"
    descriptor = service._installed.generation
    original = archive_store(app).read_evidence(head.evidence_id)
    restarted_app = AppWebContextV1.create(app.managed_home)
    restarted = AutomaticMatchLearningServiceV1.open(restarted_app)
    assert restarted.inspect().status == "reconstruction_needed"
    assert restarted.update().status == "rebuilt"
    assert restarted._installed.generation == descriptor
    retained = archive_store(restarted_app).read_evidence(head.evidence_id)
    assert retained.downloads == original.downloads
    assert restarted.update().status == "reused"


def test_imported_placeholder_claims_remain_ambiguous(tmp_path, genuine_historical):
    app, service = setup_service(tmp_path)
    retain_fixture(app, genuine_historical, imported=True)
    retain_fixture(app, genuine_historical, imported=True)
    retain_fixture(app, genuine_historical)
    assert service.update().status == "prepared"
    assert len(service._installed.bundle.historical_sources) == 1
    assert [row.reason for row in service._installed.generation.recipe.exclusions] == [
        "ambiguous", "ambiguous"]


def test_correction_isolated_and_deleted_head_never_resurrects(tmp_path, genuine_historical):
    app, service = setup_service(tmp_path)
    first = retain_fixture(app, genuine_historical)
    second = retain_fixture(app, genuine_historical)
    controller = automatic_controller(app)
    view = controller.capture()
    index = view.binding.resumed.manifest.historical_heads.index(first)
    reopen_review(app, controller, view, index)
    source = app.historical_reviews.source
    draft = replace(source.draft, players=(
        replace(source.draft.players[0], player_label="Correction"),
                                           *source.draft.players[1:]))
    app.review_state = app.review_state.mutate(
        expected_revision=app.review_state.revision, draft=draft)
    run_guided_review_v1(app, expected_revision=app.review_state.revision)
    corrected = app.historical_reviews.head
    assert corrected.source == first.source
    assert corrected.source_version_id != first.source_version_id
    assert second in archive_store(app).snapshot().manifest.historical_heads
    assert service.update().status == "prepared"
    view = controller.capture()
    index = view.binding.resumed.manifest.historical_heads.index(corrected)
    remove_head(app, controller, index)
    assert service.inspect().status == "deleted"
    assert service.update().status == "prepared"
    assert len(service._installed.bundle.historical_sources) == 1
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.update().status == "rebuilt"
    assert len(restarted._installed.bundle.historical_sources) == 1
    assert first.evidence_id in archive_store(app).snapshot().available_evidence_ids


def test_historical_cleanup_retires_both_generations_preserves_ten_match_bytes(
    tmp_path, genuine_historical,
):
    app, service = setup_service(tmp_path)
    save(app, "one")
    service.update()
    save(app, "two")
    service.update()
    original = service._installed.bundle.downloads
    retain_fixture(app, genuine_historical)
    service.update()
    retain_fixture(app, genuine_historical)
    service.update()
    assert service._installed.generation.match_catalog_revision == 2
    controller = automatic_controller(app)
    remove_head(app, controller)
    remove_head(app, controller)
    preview = controller.preview_cleanup(controller.capture(), old_evidence=True)
    assert len(preview.evidence) == 2
    controller.confirm(preview.token)
    assert service.store.snapshot().manifest.generations == ()
    preview = controller.preview_cleanup(controller.capture(), obsolete_sources=True)
    assert len(preview.sources) == 2
    controller.confirm(preview.token)
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.update().status == "prepared"
    assert restarted._installed.bundle.downloads == original
    assert restarted._installed.generation.recipe.catalog_revision == 2


@pytest.mark.parametrize("failure", ("before", "after"))
def test_save_fault_preserves_result_and_exact_persistence_only_retry(
    tmp_path, genuine_historical, monkeypatch, failure,
):
    from skatmind import automatic_learning_io as io
    app, _service = setup_service(tmp_path)
    store = archive_store(app, initialize=True)
    real = store.update_manifest
    def fault(*args, **kwargs):
        if failure == "after":
            real(*args, **kwargs)
        raise OSError("controlled manifest publication fault")
    monkeypatch.setattr(store, "update_manifest", fault)
    draft, execution, native = genuine_historical
    app.review_state = app.review_state.mutate(expected_revision=0, draft=draft)
    attempt = capture_attempt(app, app.review_state)
    state = app.review_state
    retain_manual_review(app, attempt, state, execution, native)
    assert app.review_state is state
    if failure == "after":
        assert app.historical_reviews.notice[1] == "saved"
        return
    assert app.historical_reviews.notice[1] == "unsaved"
    pending = app.historical_reviews.pending
    monkeypatch.setattr(store, "update_manifest", real)
    import skatmind.app_web.execution as execution_module
    monkeypatch.setattr(execution_module, "execute", lambda *a, **k: pytest.fail("Retry analysis"))
    writes = []
    original_write = io.write_temporary
    def counted(path, raw):
        writes.append(path.name)
        return original_write(path, raw)
    monkeypatch.setattr(io, "write_temporary", counted)
    assert save_pending_historical(app, pending.token) == "saved"
    assert writes == ["automatic-learning"]
    assert store.read_evidence(pending.candidate.evidence.identity).execution == execution


def test_superseded_pending_save_cannot_publish(tmp_path, genuine_historical, monkeypatch):
    app, _service = setup_service(tmp_path)
    store = archive_store(app, initialize=True)
    monkeypatch.setattr(store, "update_manifest", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    draft, execution, native = genuine_historical
    app.review_state = app.review_state.mutate(expected_revision=0, draft=draft)
    retain_manual_review(app, capture_attempt(app, app.review_state),
                         app.review_state, execution, native)
    pending = app.historical_reviews.pending
    start_review_v1(app, expected_revision=app.review_state.revision)
    with pytest.raises(StoreConflictError):
        save_pending_historical(app, pending.token)
    assert store.snapshot().manifest.historical_heads == ()


def test_superseded_genuine_manual_execution_never_becomes_saved_game(tmp_path, monkeypatch):
    import skatmind.app_web.workflow_operations as operations
    from skatmind.app_web.workflow_state import StaleFrontendWorkflowRevisionError
    app, _service = setup_service(tmp_path)
    draft = update_historical_options_v1(_completed_example_draft())
    app.review_state = app.review_state.mutate(expected_revision=0, draft=draft)
    real = operations.execute_guided_frontend_review_v1
    def superseded(*args, **kwargs):
        result = real(*args, **kwargs)
        start_review_v1(app, expected_revision=app.review_state.revision)
        return result
    monkeypatch.setattr(operations, "execute_guided_frontend_review_v1", superseded)
    with pytest.raises(StaleFrontendWorkflowRevisionError):
        run_guided_review_v1(app, expected_revision=app.review_state.revision)
    assert archive_store(app) is None
    assert app.review_state.latest_successful_result is None


def test_imported_correction_keeps_identity_and_does_not_change_other_source(
    tmp_path, genuine_historical,
):
    from skatmind.api.v1 import parse_request
    from skatmind.app_web.json_transfer import FrontendJsonImportV1
    from skatmind.app_web.workflow_operations import (
        run_imported_request_v1,
        store_frontend_import_v1,
    )
    app, _service = setup_service(tmp_path)
    first = retain_fixture(app, genuine_historical, imported=True)
    second = retain_fixture(app, genuine_historical)
    controller = automatic_controller(app)
    view = controller.capture()
    reopen_review(app, controller, view,
                  view.binding.resumed.manifest.historical_heads.index(first))
    root = genuine_historical[1].request.to_dict()["document"]
    root["historical_game_input"]["players"][0]["player_label"] = "Imported correction"
    request = parse_request(root)
    # The existing strict import boundary is exercised by the native HTTP modules;
    # this lifecycle fixture retains its exact typed accepted import.
    from skatmind.app_web.json_transfer import (
        build_frontend_request_json_bytes_v1,
        summarize_frontend_request_v1,
    )
    imported = FrontendJsonImportV1(revision=str(app.review_state.revision), request=request,
        summary=summarize_frontend_request_v1(request),
        request_json_bytes=build_frontend_request_json_bytes_v1(request))
    store_frontend_import_v1(app, page="review", expected_revision=app.review_state.revision,
                             imported=imported)
    run_imported_request_v1(app, page="review", expected_revision=app.review_state.revision)
    assert app.historical_reviews.head.source == first.source
    assert app.historical_reviews.source.record.scope.kind == "shared_claim"
    assert second in archive_store(app).snapshot().manifest.historical_heads


def test_new_execution_options_preserve_same_saved_game_version(tmp_path, genuine_historical):
    app, service = setup_service(tmp_path)
    original = retain_fixture(app, genuine_historical)
    draft = genuine_historical[0]
    changed = replace(draft, options=replace(draft.options, decision_snapshots=True))
    app.review_state = app.review_state.mutate(expected_revision=app.review_state.revision,
                                              draft=changed)
    run_guided_review_v1(app, expected_revision=app.review_state.revision)
    head = app.historical_reviews.head
    assert head.source_version_id == original.source_version_id
    assert head.evidence_id != original.evidence_id
    assert service.update().status == "prepared"
    assert len(service._installed.bundle.historical_sources) == 1
    assert len(service._installed.bundle.historical_evidence) == 2
    controller = automatic_controller(app)
    reopen_review(app, controller, controller.capture(), 0)
    assert app.review_state.draft.options.decision_snapshots is True
