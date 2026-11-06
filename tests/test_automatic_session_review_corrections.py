"""Issue #314 review reproductions; negative wire values are controlled fixtures."""

import base64
import hashlib
from dataclasses import replace

import pytest
from test_automatic_match_evidence import commit_candidate
from test_automatic_match_learning import save, setup_service
from test_automatic_session_evidence import genuine
from test_automatic_session_web import install_session

from skatmind.app_web.automatic_learning_controller import automatic_controller
from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1
from skatmind.automatic_learning_codec import canonical_json, decode_json, fingerprint
from skatmind.automatic_learning_store import (
    UnsupportedEvidenceError,
    initialize_automatic_learning_store_v1,
    resume_automatic_learning_store_v1,
)
from skatmind.automatic_match_execution_codec import decode_execution_value, validate_execution
from skatmind.automatic_mixed_preparation import admit_generation
from skatmind.automatic_session_evidence import (
    build_managed_session_source,
    decode_session_execution,
)


def archive_bytes(store):
    return {path.relative_to(store.root).as_posix(): path.read_bytes()
            for path in store.root.rglob("*.json")}


@pytest.mark.parametrize("mixed_history", (False, True))
def test_session_cleanup_preserves_unchanged_match_exports_after_restart(tmp_path, mixed_history):
    assert_cleanup_continuity(tmp_path, mixed_history)


@pytest.mark.parametrize("mixed_history", (False, True))
def test_legacy_cleanup_captures_match_basis_before_retiring_descriptors(tmp_path, mixed_history):
    assert_cleanup_continuity(tmp_path, mixed_history, legacy=True)


def assert_cleanup_continuity(tmp_path, mixed_history, *, legacy=False):
    app, service = setup_service(tmp_path)
    session = install_session(app, missing=True) if mixed_history else None
    save(app, "one")
    assert service.update().status == "prepared"
    save(app, "two")
    assert service.update().status == "prepared"
    original = service._installed.bundle
    revision = getattr(service._installed.generation, "match_catalog_revision",
                       service._installed.generation.recipe.catalog_revision)
    assert revision == 2
    if session is None:
        session = install_session(app, missing=True)
        assert service.update().status == "prepared"
    if legacy:
        before = service.store.snapshot().manifest
        assert service.store.update_manifest(replace(before, revision=before.revision + 1,
            match_basis=None), expected_manifest=before.fingerprint).status == "saved"
    session.path.unlink()  # Controlled removal of this disposable managed source.
    controller = automatic_controller(app)
    preview = controller.preview_cleanup(controller.capture(), obsolete_sources=True)
    assert len(preview.sources) == 1
    controller.confirm(preview.token)
    manifest = service.store.snapshot().manifest
    assert manifest.current_generation is None
    assert (manifest.previous_generation is None) == mixed_history
    assert all(row.source_version.source.family == "match" for row in manifest.sources)
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.inspect().status == "missing"
    assert restarted.update().status == "prepared"
    rebuilt = restarted._installed.bundle
    assert rebuilt.sources == original.sources and rebuilt.evidence == original.evidence
    changed = [left.kind for left, right in zip(original.downloads, rebuilt.downloads, strict=True)
               if left.content != right.content]
    current_revision = getattr(restarted._installed.generation, "match_catalog_revision",
                               restarted._installed.generation.recipe.catalog_revision)
    print({"finding": "A", "previous_survives": not mixed_history,
           "before_revision": revision, "after_revision": current_revision,
           "changed_downloads": changed,
           "player_catalog_hashes": [hashlib.sha256(next(item.content for item in bundle.downloads
               if item.kind == "player_catalog")).hexdigest() for bundle in (original, rebuilt)]})
    assert current_revision == revision
    assert rebuilt.downloads == original.downloads


@pytest.mark.parametrize("previous", ("exact", "unrelated", "unsupported"))
def test_legacy_previous_is_used_only_for_exact_supported_match_inputs(tmp_path, previous):
    app, service = setup_service(tmp_path)
    save(app, "one")
    service.update()
    save(app, "two")
    service.update()
    store = service.store
    before = store.snapshot().manifest
    original = store.read_object(before.current_generation)
    replacement = original
    if previous == "unsupported":
        data = decode_json(original.payload)
        data["recipe"]["builder_versions"][0]["value"] = "future"
        replacement = replace(original, payload=canonical_json(data))
        assert store.publish_object(replacement) == "saved"
    objects = tuple(row for row in before.objects if row.reference not in before.generations)
    requested = replace(before, revision=before.revision + 1, match_basis=None,
        current_generation=None, previous_generation=replacement.reference,
        objects=(*objects, replacement.entry))
    store.update_manifest(requested, expected_manifest=before.fingerprint)
    if previous == "unrelated":
        save(app, "three")
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.inspect().status == "missing"
    assert restarted.update().status == "prepared"
    expected_revision = 2 if previous == "exact" else 1
    assert restarted._installed.generation.recipe.catalog_revision == expected_revision


def test_match_evidence_changes_do_not_reset_membership_revision(tmp_path):
    from test_automatic_match_evidence import genuine_candidate
    candidate = genuine_candidate()  # One genuine ordinary Match fixture analysis.
    app, service = setup_service(tmp_path)
    save(app, "one")
    service.update()
    save(app, "analyzed", workspace=build_managed_match_workspace(candidate))
    service.update()
    original = service._installed.bundle.downloads
    assert service._installed.generation.recipe.catalog_revision == 2
    assert commit_candidate(service.store, candidate).status == "saved"
    assert service.update().status == "prepared"
    assert service._installed.generation.recipe.catalog_revision == 2
    assert service._installed.bundle.downloads != original
    install_session(app, missing=True)
    service.update()
    store = service.store
    before = store.snapshot().manifest
    preview = store.preview_cleanup(expected_manifest=before.fingerprint,
                                    remove_evidence_ids=(candidate.evidence.identity,))
    assert preview.manifest.generations == ()
    assert store.commit_cleanup(preview).status == "saved"
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.update().status == "prepared"
    assert restarted._installed.generation.match_catalog_revision == 2
    assert restarted._installed.bundle.downloads == original


def build_managed_match_workspace(candidate):
    from skatmind.automatic_match_evidence import decode_match_source
    return decode_match_source(candidate.objects[0], candidate.source).document.workspace


def test_legacy_manifest_bytes_and_closed_match_basis_references(tmp_path):
    from skatmind.automatic_learning_contracts import ManifestV1
    from skatmind.automatic_learning_objects import manifest_bytes, resume_manifest
    legacy = ManifestV1(space_id="legacy-space")
    raw = manifest_bytes(legacy)
    assert "match_basis" not in decode_json(raw)["manifest"]
    assert manifest_bytes(resume_manifest(raw)) == raw
    app, service = setup_service(tmp_path)
    save(app)
    service.update()
    manifest = service.store.snapshot().manifest
    assert resume_manifest(manifest_bytes(manifest)) == manifest
    for defect in ("space", "source", "version"):
        document = decode_json(manifest_bytes(manifest))
        basis = document["manifest"]["match_basis"]
        if defect == "space":
            basis["space_id"] = "foreign-space"
        elif defect == "source":
            basis["recipe"]["source_version_ids"] = ["f" * 64]
        else:
            basis["version"] = True
        document["content_fingerprint"] = fingerprint("manifest_v1", document["manifest"])
        with pytest.raises(ValueError):
            resume_manifest(canonical_json(document))


def test_unsupported_match_basis_cannot_seed_a_rebuild(tmp_path):
    from skatmind.automatic_learning_contracts import NamedValueV1
    app, service = setup_service(tmp_path)
    save(app)
    service.update()
    before = service.store.snapshot().manifest
    basis = replace(before.match_basis, recipe=replace(before.match_basis.recipe,
        builder_versions=(NamedValueV1(name="future_builder", value="99"),)))
    service.store.update_manifest(replace(before, revision=before.revision + 1, match_basis=basis),
                                   expected_manifest=before.fingerprint)
    raw = archive_bytes(service.store)
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    assert restarted.update().status == "unsupported"
    assert archive_bytes(service.store) == raw


def replace_scalar(value, old, new):
    if type(value) is dict:
        return {key: replace_scalar(item, old, new) for key, item in value.items()}
    if type(value) is list:
        return [replace_scalar(item, old, new) for item in value]
    return new if value == old else value


def without_elapsed(value):
    if type(value) is dict:
        return {key: without_elapsed(item) for key, item in value.items()
                if key not in ("wall_clock_elapsed_ms", "elapsed_ms")}
    if type(value) in (list, tuple):
        return [without_elapsed(item) for item in value]
    return value


def contradictory_core_wire(candidate, execution):
    """Reconcile every retained copy and wire identity, keeping authoritative input fixed."""
    obj = candidate.objects[1]
    data = decode_json(obj.payload)
    old = execution.result.result.document["whole_game_rollout_result"]["source_fingerprint"]
    new = "0" * 64 if old != "0" * 64 else "1" * 64
    data["internal_execution"] = replace_scalar(data["internal_execution"], old, new)
    data["result"] = replace_scalar(data["result"], old, new)
    public = decode_execution_value(data["result"])
    raw = canonical_frontend_json_bytes_v1(public)
    data["downloads"][1].update(bytes=base64.b64encode(raw).decode("ascii"),
                                sha256=hashlib.sha256(raw).hexdigest())
    semantic = fingerprint("session_execution_semantics_v1", {
        "situation": candidate.evidence.situation.to_dict(),
        "request": execution.request.to_dict(), "options": execution.options.to_dict(),
        "supplied_options": list(execution.options._provenance_supplied_option_names),
        "result": without_elapsed(public)})
    wire = replace(obj, payload=canonical_json(data))
    entry = replace(candidate.evidence, envelope=wire.reference, semantic_fingerprint=semantic)
    validate_execution(decode_execution_value(data["invocation"]),
                       decode_execution_value(data["internal_execution"]))
    original = decode_json(obj.payload)
    for key in ("original_source", "checkpoint", "observation", "review_export", "request",
                "options", "supplied_options", "invocation"):
        assert data[key] == original[key]
    return replace(candidate, objects=(candidate.objects[0], wire), evidence=entry)


def test_consistent_false_core_fingerprint_is_rejected_by_native_and_store_admission(
    tmp_path, monkeypatch,
):
    # One genuine fixture analysis; the contradictory wire is never evaluated.
    candidate, execution, document = genuine(tmp_path, rollout=True)
    wire = contradictory_core_wire(candidate, execution)
    source = build_managed_session_source(document)[2]
    monkeypatch.setattr("skatmind.application.execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Admission must not analyze"))
    accepted = True
    try:
        decode_session_execution(wire.objects[1], wire.evidence, source)
    except ValueError:
        accepted = False
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    assert commit_candidate(store, wire).status == "saved"
    before = archive_bytes(store)
    admitted = wire.evidence.identity in store.snapshot().available_evidence_ids
    print({"finding": "B", "native_accepted": accepted, "store_admitted": admitted,
           "provenance_validation": "passed", "fixture_analyses": 1})
    assert archive_bytes(store) == before
    assert not accepted and not admitted
    restarted = resume_automatic_learning_store_v1(store.root)
    assert next(row for row in restarted.snapshot().objects
                if row.reference == wire.evidence.envelope).consumption_status == "corrupt"
    with pytest.raises(UnsupportedEvidenceError):
        restarted.read_evidence(wire.evidence.identity)
    assert archive_bytes(store) == before


@pytest.fixture(scope="module")
def rollout_fixture(tmp_path_factory):
    return genuine(tmp_path_factory.mktemp("review-core"), rollout=True)


@pytest.mark.parametrize("field", ("source", "information_cutoff", "game_type", "local_side",
                                  "position"))
def test_native_core_checks_request_classification_party_and_position(rollout_fixture, field):
    from skatmind.automatic_session_rollout_validation import validate_native_rollout
    _candidate, execution, _document = rollout_fixture
    request = execution.request.to_dict()["document"]
    result = execution.result.result.to_dict()["document"]
    if field == "position":
        result["position"]["declarer_points"] += 1
    else:
        result["whole_game_rollout_result"][field] = {
            "source": "flat_decision_input", "information_cutoff": "after_play",
            "game_type": "null", "local_side": "defenders"}[field]
    with pytest.raises(ValueError, match="authoritative core source identity|prepared Position"):
        validate_native_rollout(request, result)


def test_genuine_unavailable_settlement_retains_authoritative_core_identity(tmp_path, monkeypatch):
    from whole_game_review_fixtures import saved_opening

    from skatmind.api.v1 import ExecutionOptionsV1
    from skatmind.app_web.execution import execute_guided_frontend_review_v1
    from skatmind.automatic_session_evidence import build_session_capture_candidate
    from skatmind.private_execution_capture import capture_native_execution
    from skatmind.session_persistence_codec import build_session_persistence_document_v1
    from skatmind.session_recorded_coverage import project_saved_session_coverage
    from skatmind.session_rollout_review import derive_session_rollout_review_request_v1
    from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

    state, checkpoint = saved_opening()
    document = build_session_persistence_document_v1(state, decision_checkpoints=(checkpoint,))
    observation = project_saved_session_coverage(document).decisions[0][2]
    request = derive_session_rollout_review_request_v1(state=state, checkpoint=checkpoint,
        settings=WholeGameRolloutSettingsV1(objective="complete_settlement", random_seed=0,
            requested_worlds=1, wall_clock_timeout_ms=30000))
    with capture_native_execution() as captured:
        execution = execute_guided_frontend_review_v1(request, options=ExecutionOptionsV1())
    assert execution.result.result.document["whole_game_rollout_result"]["status"] == "unavailable"
    monkeypatch.setattr("skatmind.application.execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Admission must not analyze"))
    candidate = build_session_capture_candidate(document, checkpoint, observation,
                                                  execution, captured[0])
    assert decode_session_execution(candidate.objects[1], candidate.evidence,
        build_managed_session_source(document)[2]).execution == execution


def malformed_generation(store, member):
    before = store.snapshot().manifest
    original = store.read_object(before.current_generation)
    assert original.codec_version == 3
    data = decode_json(original.payload)
    data["inventory"] = [member]
    data["input_fingerprint"] = fingerprint("automatic_match_inputs_v1", {
        "inventory": data["inventory"], "evidence": data["evidence_outcomes"],
        "exclusions": data["recipe"]["exclusions"],
        "selected": data["recipe"]["source_version_ids"]})
    wire = replace(original, payload=canonical_json(data))
    assert store.publish_object(wire) == "saved"
    requested = replace(before, revision=before.revision + 1,
        objects=tuple(wire.entry if row.reference == original.reference else row
                      for row in before.objects), current_generation=wire.reference)
    assert store.update_manifest(requested, expected_manifest=before.fingerprint).status == "saved"
    return wire, requested


@pytest.mark.parametrize("member", (None, []), ids=("null", "array"))
def test_malformed_inventory_member_has_controlled_admission_and_service_results(tmp_path, member):
    app, service = setup_service(tmp_path)
    install_session(app, missing=True)
    assert service.update().status == "prepared"
    wire, manifest = malformed_generation(service.store, member)
    before = archive_bytes(service.store)
    restarted = AutomaticMatchLearningServiceV1.open(AppWebContextV1.create(app.managed_home))
    outcomes = {}
    for label, operation in (("direct", lambda: admit_generation(wire, manifest)),
                             ("inspect", restarted.inspect), ("update", restarted.update)):
        try:
            result = operation()
            outcomes[label] = getattr(result, "status", "accepted")
        except (ValueError, AttributeError) as error:
            outcomes[label] = type(error).__name__
    print({"finding": "C", "member": member, "outcomes": outcomes})
    assert archive_bytes(service.store) == before
    assert outcomes == {"direct": "ValueError", "inspect": "excluded", "update": "failed"}
