"""Controlled interruption, corruption, quota and stale-generation fixtures for S7."""

from dataclasses import replace

import pytest
from test_automatic_historical_evidence import genuine_historical
from test_automatic_historical_learning import retain_fixture
from test_automatic_learning_ui import localized_server
from test_automatic_match_learning import save, setup_service
from test_automatic_match_learning_evidence import forbid_execution
from test_session_recorded_review_web import Browser

from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.historical_review_retention import capture_attempt, retain_manual_review
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.automatic_learning_codec import canonical_json, decode_json, fingerprint
from skatmind.automatic_learning_store import StoreLimitsV1
from skatmind.automatic_mixed_preparation import admit_generation

__all__ = ["genuine_historical", "localized_server"]


@pytest.mark.parametrize("member", (None, [], 1, {"family": []}, {"family": {}}),
                         ids=("null", "array", "number", "family-array", "family-object"))
def test_malformed_historical_generation_has_controlled_restart_and_http(
    localized_server, genuine_historical, member,
):
    app = localized_server.app_context
    retain_fixture(app, genuine_historical)
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "prepared"
    store = service.store
    before = store.snapshot().manifest
    obj = store.read_object(before.current_generation)
    assert obj.codec_version == 4
    data = decode_json(obj.payload)
    data["inventory"] = [member]
    data["input_fingerprint"] = fingerprint("automatic_match_inputs_v1", {
        "inventory": data["inventory"], "evidence": data["evidence_outcomes"],
        "exclusions": data["recipe"]["exclusions"],
        "selected": data["recipe"]["source_version_ids"]})
    malformed = replace(obj, payload=canonical_json(data))
    store.publish_object(malformed)
    requested = replace(before, revision=before.revision + 1,
        objects=tuple(malformed.entry if row.reference == obj.reference else row
                      for row in before.objects), current_generation=malformed.reference)
    store.update_manifest(requested, expected_manifest=before.fingerprint)
    with pytest.raises(ValueError):
        admit_generation(malformed, requested)
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.inspect().status == "excluded"
    assert restarted.update().status == "failed"
    response = Browser(localized_server).request("GET", "/learning/automatic")
    assert response[0] == 409 and b"</html>" in response[2]
    assert store.snapshot().manifest == requested


@pytest.mark.parametrize("payload", (None, []), ids=("null", "array"))
def test_malformed_stored_envelope_has_controlled_delivery_recovery(
    localized_server, genuine_historical, payload,
):
    from skatmind.automatic_learning_io import object_path
    app = localized_server.app_context
    head = retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    browser.page("/review/saved")
    store = app.automatic_match_learning.store
    before, receipt = store._snapshot_for_delivery()
    entry = next(row for row in before.manifest.evidence if row.identity == head.evidence_id)
    path = object_path(store.root, entry.envelope)
    data = decode_json(path.read_bytes())
    data["payload"] = payload
    raw = canonical_json(data) + b"\n"
    path.write_bytes(raw)  # Controlled corruption of the disposable stored envelope.
    resumed, fresh = store._snapshot_for_delivery(receipt)
    assert fresh is None and head.evidence_id not in resumed.available_evidence_ids
    response = browser.request("GET", "/review/saved")
    assert response[0] in (200, 409) and b"</html>" in response[2]
    assert path.read_bytes() == raw


@pytest.mark.parametrize("codec", (2, 3, 5))
def test_historical_recipe_never_reinterprets_older_or_future_codecs(
    tmp_path, genuine_historical, codec,
):
    app, service = setup_service(tmp_path)
    retain_fixture(app, genuine_historical)
    assert service.update().status == "prepared"
    manifest = service.store.snapshot().manifest
    obj = service.store.read_object(manifest.current_generation)
    changed = replace(obj, codec_version=codec)
    with pytest.raises(ValueError):
        admit_generation(changed, manifest)


def test_quota_failure_keeps_execution_and_no_live_game(tmp_path, genuine_historical):
    app, _service = setup_service(tmp_path)
    store = archive_store(app, initialize=True)
    store.limits = StoreLimitsV1(total_bytes=1)
    draft, execution, native = genuine_historical
    app.review_state = app.review_state.mutate(expected_revision=0, draft=draft)
    attempt = capture_attempt(app, app.review_state)
    retain_manual_review(app, attempt, app.review_state, execution, native)
    assert app.historical_reviews.notice[1] == "unsaved"
    assert app.historical_reviews.pending.execution is execution
    assert store.snapshot().manifest.historical_heads == ()
    assert not store._coordinator.candidates


def test_unexecuted_drafts_and_imports_are_not_saved_games(tmp_path, genuine_historical):
    app, service = setup_service(tmp_path)
    draft, execution, _native = genuine_historical
    for values in ({"draft": draft}, {"imported_request": execution.request}):
        app.review_state = app.review_state.mutate(
            expected_revision=app.review_state.revision, **values)
        assert service.update().status in ("prepared", "reused")
        assert service._installed.generation.recipe.source_version_ids == ()
        assert archive_store(app).snapshot().manifest.historical_heads == ()


def test_unlocked_preparation_cannot_publish_after_head_deletion(
    tmp_path, genuine_historical, monkeypatch,
):
    import skatmind.app_web.automatic_match_learning as module
    app, service = setup_service(tmp_path)
    head = retain_fixture(app, genuine_historical)
    original = module.build_historical_bundle
    def changed(*args, **kwargs):
        bundle = original(*args, **kwargs)
        store = archive_store(app)
        before = store.snapshot().manifest
        store.update_manifest(replace(before, revision=before.revision + 1,
            historical_heads=(), historical_retired=(head.source,)),
            expected_manifest=before.fingerprint)
        return bundle
    monkeypatch.setattr(module, "build_historical_bundle", changed)
    assert service.update().status == "conflict"
    assert archive_store(app).snapshot().manifest.current_generation is None


def test_postcommit_generation_interruption_keeps_authority_and_rebuilds(
    tmp_path, genuine_historical, monkeypatch,
):
    app, service = setup_service(tmp_path)
    retain_fixture(app, genuine_historical)
    monkeypatch.setattr(service, "_install", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert service.update().status == "unconfirmed"
    before = archive_store(app).snapshot().manifest
    assert before.current_generation is not None
    forbid_execution(monkeypatch)
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.inspect().status == "reconstruction_needed"
    assert restarted.update().status == "rebuilt"
    assert archive_store(app).snapshot().manifest == before


def test_historical_update_preserves_session_and_independent_collection(
    tmp_path, genuine_historical,
):
    from test_automatic_session_web import install_session

    from skatmind.learning_corpus_persistence import initialize_learning_corpus_directory_v1
    app, service = setup_service(tmp_path)
    save(app)
    session = install_session(app, missing=True)
    manual = app.managed_home.category("corpora").path / "independent"
    initialize_learning_corpus_directory_v1(manual, corpus_id="independent")
    originals = {path: path.read_bytes() for path in manual.rglob("*.json")}
    session_bytes = session.path.read_bytes()
    assert service.update().status == "prepared"
    prior = service._installed.bundle
    retain_fixture(app, genuine_historical)
    assert service.update().status == "prepared"
    assert service._installed.bundle.session_sources == prior.session_sources
    assert service._installed.bundle.downloads == prior.downloads
    assert session.path.read_bytes() == session_bytes
    assert all(path.read_bytes() == raw for path, raw in originals.items())
