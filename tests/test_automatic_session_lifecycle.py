from dataclasses import replace

import pytest
from test_automatic_learning_delivery_receipt import rewrite_same_metadata
from test_automatic_match_learning import save
from test_historical_game import build_historical_input
from test_session_recorded_review import context_for, selection
from test_session_transitions import _play_commands_from_data, _retrospective_before_play

from skatmind import automatic_learning_io as io
from skatmind.app_web.automatic_learning_controller import automatic_controller
from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1
from skatmind.automatic_learning_contracts import EntityReferenceV1, OriginBindingV1
from skatmind.automatic_learning_store import StoreConflictError
from skatmind.session_persistence import save_session_persistence_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1


@pytest.mark.parametrize("ended", (False, True))
def test_no_perspective_is_valid_limited_session_coverage(tmp_path, ended):
    data = build_historical_input()
    state = _retrospective_before_play(data)
    if ended:
        state = _play_commands_from_data(state, data)
    app, _active = context_for(tmp_path, state, ())
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    source, = service._installed.bundle.session_sources
    assert not source.coverage.has_perspective
    assert source.coverage.recorded_plays == (30 if ended else 0)
    assert source.coverage.own_plays == source.coverage.missing_checkpoints == 0


@pytest.mark.parametrize("family", ("source", "execution", "generation"))
def test_session_receipt_checks_exact_bytes_and_skips_unchanged_admission(
    tmp_path, monkeypatch, family,
):
    app, active = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    store = service.store
    before, receipt = store._snapshot_for_delivery()
    original = store._admission
    calls = []
    def admission(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(store, "_admission", admission)
    assert store._snapshot_for_delivery(receipt) == (before, receipt)
    assert calls == []
    ref = (before.manifest.sources[0].object_ref if family == "source" else
           before.manifest.evidence[0].envelope if family == "execution" else
           before.manifest.current_generation)
    rewrite_same_metadata(io.object_path(store.root, ref))
    after, retained = store._snapshot_for_delivery(receipt)
    assert retained is None and calls
    assert next(row for row in after.objects if row.reference == ref).storage_status == "corrupt"


def test_session_history_release_preserves_current_and_retained_evidence(tmp_path):
    app, active = context_for(tmp_path)
    controller = automatic_controller(app)
    assert controller.service.update().status == "prepared"
    original = active.document
    stripped = build_session_persistence_document_v1(active.state, decision_checkpoints=())
    save_session_persistence_file_v1(active.path, stripped,
                                    expected_content_fingerprint=original.content_fingerprint)
    assert controller.service.update().status == "prepared"
    confirmation = controller.preview_cleanup(controller.capture(), obsolete_sources=True)
    assert len(confirmation.sources) == 1
    controller.confirm(confirmation.token)
    manifest = controller.service.store.snapshot().manifest
    assert len(manifest.sources) == 1
    assert manifest.sources[0].source_version.content_fingerprint == stripped.content_fingerprint
    with pytest.raises(StoreConflictError):
        controller.confirm(confirmation.token)


def test_unverified_cross_family_origin_claim_blocks_both_sources(tmp_path):
    app, _active = context_for(tmp_path)
    save(app)
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    store = service.store
    before = store.snapshot().manifest
    match = next(row for row in before.sources if row.source_version.source.family == "match")
    session = next(row for row in before.sources if row.source_version.source.family == "session")
    def entity(row):
        return EntityReferenceV1(source=row.source_version.source, scope=row.scope,
                                  entity_kind="game", original_id="claimed-game")
    claim = OriginBindingV1(kind="cross_source_game", subject=entity(match), target=entity(session),
        proof=session.object_ref, validator="unverified_fixture", validator_version=1)
    assert store.update_manifest(replace(before, revision=before.revision + 1, bindings=(claim,)),
                                 expected_manifest=before.fingerprint).status == "saved"
    assert service.update().status == "prepared"
    assert service._installed.bundle.sources == service._installed.bundle.session_sources == ()
    assert len(service._installed.generation.recipe.exclusions) == 2


def test_mixed_attempt_supersession_cannot_install_old_result(tmp_path, monkeypatch):
    import skatmind.app_web.automatic_match_learning as module
    app, _active = context_for(tmp_path)
    service = AutomaticMatchLearningServiceV1.open(app)
    original = module.build_mixed_bundle
    newer = []
    def supersede(*args, **kwargs):
        monkeypatch.setattr(module, "build_mixed_bundle", original)
        newer.append(service.update())
        return original(*args, **kwargs)
    monkeypatch.setattr(module, "build_mixed_bundle", supersede)
    assert service.update().status == "conflict"
    assert newer[0].status == "prepared"
    assert service._installed.generation == newer[0].generation


def test_committed_generation_rebuilds_after_install_interruption(tmp_path, monkeypatch):
    app, _active = context_for(tmp_path)
    service = AutomaticMatchLearningServiceV1.open(app)
    def interrupted(*args, **kwargs):
        raise OSError("Controlled interruption after manifest commit")
    monkeypatch.setattr(service, "_install", interrupted)
    assert service.update().status == "unconfirmed"
    assert service.store.snapshot().manifest.current_generation is not None
    restarted = AutomaticMatchLearningServiceV1.open(app)
    assert restarted.inspect().status == "reconstruction_needed"
    assert restarted.update().status == "rebuilt"


def test_bounded_delivery_reuses_source_admission_but_reads_every_candidate(tmp_path, monkeypatch):
    import skatmind.app_web.automatic_match_learning as module
    app, active = context_for(tmp_path)
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    binding = service.capture_delivery()
    monkeypatch.setattr(module, "capture_match_inventory",
                        lambda *a, **kw: pytest.fail("Unchanged bounded source admission"))
    service.validate_delivery(binding)
    # Fresh bytes, not mtime/size, invalidate the receipt and re-enter strict admission.
    raw = active.path.read_bytes()
    info = active.path.stat()
    active.path.write_bytes(raw[:-1] + b" ")
    import os
    os.utime(active.path, ns=(info.st_atime_ns, info.st_mtime_ns))
    with pytest.raises(pytest.fail.Exception, match="Unchanged bounded source admission"):
        service.capture_delivery()


def test_session_report_release_precedes_original_source_history_release(tmp_path):
    app, active = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    controller = automatic_controller(app)
    assert controller.service.update().status == "prepared"
    stripped = build_session_persistence_document_v1(active.state, decision_checkpoints=())
    save_session_persistence_file_v1(active.path, stripped,
        expected_content_fingerprint=active.document.content_fingerprint)
    assert controller.service.update().status == "prepared"
    protected = controller.preview_cleanup(controller.capture(), obsolete_sources=True)
    assert protected.sources == ()
    removal = controller.preview_cleanup(controller.capture(), old_evidence=True)
    assert len(removal.evidence) == 1
    assert removal.evidence[0][1].source.document == active.document
    controller.confirm(removal.token)
    release = controller.preview_cleanup(controller.capture(), obsolete_sources=True)
    assert len(release.sources) == 1
    controller.confirm(release.token)
    assert controller.service.store.snapshot().manifest.evidence == ()
    assert len(controller.service.store.snapshot().manifest.sources) == 1


def test_partial_checkpoint_coverage_does_not_claim_all_snapshots_are_missing(tmp_path):
    from test_session_position_export import _options, _state_for_decision

    from skatmind.app_web.session_learning_rendering import render_session_coverage
    from skatmind.app_web.stateful_localization import text
    from skatmind.automatic_session_evidence import build_managed_session_source
    from skatmind.session_decision_checkpoint import build_session_decision_checkpoint_v1
    from skatmind.session_position_export import export_session_position_analysis_request_v1

    data = build_historical_input()
    state = _state_for_decision(data, 1)
    checkpoint = build_session_decision_checkpoint_v1(state=state,
        position_export=export_session_position_analysis_request_v1(state, _options()))
    state = _play_commands_from_data(state, data)
    document = build_session_persistence_document_v1(state, decision_checkpoints=(checkpoint,))
    source = build_managed_session_source(document)[2]
    assert source.coverage.own_plays == 10 and source.coverage.missing_checkpoints == 9
    for locale in ("en", "de"):
        body = render_session_coverage(source, locale)
        assert text(locale, "session_learning.missing", count=9) in body
        assert text(locale, "recorded_review.no_snapshots") not in body
