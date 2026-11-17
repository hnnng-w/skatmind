"""Bounded S4 archive admission reuse always requires freshly checked exact bytes."""

import os
from collections import Counter
from dataclasses import replace
from time import perf_counter

import pytest
from learning_archive_fixture_helpers import measure_work, publish_fresh_archive, work_phase
from test_automatic_match_learning import save, setup_service
from test_automatic_match_rollout_evidence import executed
from test_match_rollout_review import alex_workspace, rollout_options

from skatmind.automatic_learning_store import AutomaticLearningStoreV1, StoreConflictError
from skatmind.automatic_match_evidence import build_match_capture_candidate
from skatmind.automatic_match_rollout_evidence import build_match_rollout_capture_candidate
from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1


def test_unchanged_delivery_reads_bytes_without_repeating_typed_admission(tmp_path, monkeypatch):
    import skatmind.automatic_learning_io as io

    app, service = setup_service(tmp_path)
    save(app)
    assert service.update().status == "prepared"
    store = service.store
    first, receipt = store._snapshot_for_delivery()
    assert receipt is not None
    counts = Counter()
    read, admit = io.read_bounded, store._admission
    def reading(*args, **kwargs):
        counts["read"] += 1
        return read(*args, **kwargs)
    def admitting(*args, **kwargs):
        counts["admission"] += 1
        return admit(*args, **kwargs)
    monkeypatch.setattr(io, "read_bounded", reading)
    monkeypatch.setattr(store, "_admission", admitting)
    second, reused = store._snapshot_for_delivery(receipt)
    assert second is first and reused is receipt
    assert counts["admission"] == 0
    assert counts["read"] >= len(first.manifest.objects) + 2


@pytest.fixture(scope="module")
def attempts():
    # Three genuine original partial-Match executions, never timed test thresholds.
    start = perf_counter()
    ordinary = build_match_capture_candidate(*executed(options=MatchDecisionAnalysisOptionsV1(
        recommendation_method="immediate_expected_value", immediate_sample_count=1)))
    complete = build_match_rollout_capture_candidate(*executed("complete_settlement"))
    unavailable = build_match_rollout_capture_candidate(*executed(options=replace(
        rollout_options("complete_settlement"), settlement_supplements={})))
    print({"phase": "receipt_executions", "seconds": perf_counter() - start,
           "new_card_executions": 3})
    return ordinary, complete, unavailable


@pytest.fixture
def admitted(tmp_path, attempts, monkeypatch):
    from skatmind.app_web.saved_match_analyses import archive_store

    app, service = setup_service(tmp_path)
    save(app, workspace=alex_workspace(count=3))
    archive = archive_store(app, initialize=True)
    with work_phase(monkeypatch, archive, "receipt_empty_store"):
        empty = archive.snapshot()
    with work_phase(monkeypatch, archive, "receipt_fixture_publication"):
        publish_fresh_archive(archive, empty, attempts)
    # Perform Update's required owner initialization once, measured separately.
    with work_phase(monkeypatch, archive, "receipt_final_owner_admission"):
        assert service._store(initialize=True) is service.store
    with work_phase(monkeypatch, archive, "receipt_update"):
        assert service.update().status == "prepared"
    store = service.store
    with work_phase(monkeypatch, store, "receipt_fresh_capture"):
        snapshot, receipt = store._snapshot_for_delivery()
    assert receipt is not None and len(snapshot.available_evidence_ids) == 3
    return service, snapshot, receipt


def rewrite_same_metadata(path):
    before = path.stat()
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    path.write_bytes(raw[:-1] + b" ")  # Same-length noncanonical wire bytes.
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    after = path.stat()
    assert (before.st_ino, before.st_size, before.st_mtime_ns) == (
        after.st_ino, after.st_size, after.st_mtime_ns)


@pytest.mark.parametrize("family", ("source", "ordinary", "rollout", "generation"))
@pytest.mark.parametrize("change", ("missing", "same_metadata_corruption"))
def test_receipt_never_hides_changed_bytes_or_missing_dependencies(admitted, family, change):
    from skatmind import automatic_learning_io as io

    service, before, receipt = admitted
    store = service.store
    ref = (before.manifest.sources[0].object_ref if family == "source" else
           before.manifest.current_generation if family == "generation" else
           next(entry.envelope for entry in before.manifest.evidence
                if entry.evidence_class == ("decision" if family == "ordinary" else "rollout")))
    path = io.object_path(store.root, ref)
    if change == "missing":
        path.unlink()
    else:
        rewrite_same_metadata(path)
    after, retained = store._snapshot_for_delivery(receipt)
    assert retained is None and after is not before
    assert next(row for row in after.objects if row.reference == ref).storage_status == (
        "missing" if change == "missing" else "corrupt")
    if family == "source":
        assert after.available_evidence_ids == ()
    elif family != "generation":
        assert len(after.available_evidence_ids) == 2


@pytest.mark.parametrize("change", ("manifest", "owner", "limits", "inventory"))
def test_receipt_requires_exact_owner_binding_limits_and_inventory(admitted, monkeypatch, change):
    from automatic_learning_helpers import source_fixture

    from skatmind.automatic_learning_contracts import ExclusionV1
    from skatmind.automatic_learning_store import StoreLimitsV1

    service, before, receipt = admitted
    store = service.store
    if change == "manifest":
        source = before.manifest.sources[0].source_version.source
        requested = replace(before.manifest, revision=before.manifest.revision + 1,
                            exclusions=(ExclusionV1(source=source, reason="explicit"),))
        assert store.update_manifest(requested,
            expected_manifest=before.manifest.fingerprint).status == "saved"
    elif change == "owner":
        store = AutomaticLearningStoreV1(store.root)
    elif change == "limits":
        store.limits = StoreLimitsV1(total_bytes=before.retained_bytes)
    else:
        _record, orphan = source_fixture()  # Storage-only orphan, not executed evidence.
        assert store.publish_object(orphan) == "saved"
    original = store._admission
    calls = []
    def admit(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(store, "_admission", admit)
    after, fresh = store._snapshot_for_delivery(receipt)
    assert calls == [1] and fresh is not receipt and after is not before
    assert len(after.available_evidence_ids) == 3


@pytest.mark.parametrize("bound", ("_DELIVERY_RECEIPT_MAX_OBJECTS", "_DELIVERY_RECEIPT_MAX_BYTES"))
def test_large_delivery_uses_strict_snapshot_without_truncation(admitted, monkeypatch, bound):
    import skatmind.automatic_learning_store as module

    service, before, receipt = admitted
    monkeypatch.setattr(module, bound, 1)
    after, fresh = service.store._snapshot_for_delivery(receipt)
    assert fresh is None and after == before and after is not before
    assert len(after.available_evidence_ids) == 3


def test_receipt_seeding_detects_bytes_changed_during_semantic_admission(admitted, monkeypatch):
    from skatmind import automatic_learning_io as io

    service, before, _receipt = admitted
    store = service.store
    original = store._admission
    def changed(*args):
        result = original(*args)
        rewrite_same_metadata(io.object_path(store.root, before.manifest.sources[0].object_ref))
        return result
    monkeypatch.setattr(store, "_admission", changed)
    with pytest.raises(StoreConflictError):
        store._snapshot_for_delivery()


def test_changed_manifest_binding_reenters_original_source_admission(admitted):
    from skatmind.automatic_learning_objects import manifest_bytes

    service, before, receipt = admitted
    source, = before.manifest.sources
    tampered = replace(before.manifest, revision=before.manifest.revision + 1,
                       sources=(replace(source, revision=source.revision + 1),))
    # Controlled on-disk semantic tampering: immutable source/Report bytes stay exact.
    # This is deliberately not a mutation accepted by the publication API.
    (service.store.root / "manifest.json").write_bytes(manifest_bytes(tampered))
    after, fresh = service.store._snapshot_for_delivery(receipt)
    assert fresh is not receipt and after.available_evidence_ids == ()
    row = next(row for row in after.objects if row.reference == source.object_ref)
    assert row.storage_status == "valid" and row.consumption_status == "corrupt"


def test_live_source_same_metadata_change_still_rejects_original_delivery(admitted):
    service, _before, _receipt = admitted
    binding = service.capture_delivery()
    path = service.home.category("matches").path / "one.json"
    stat = path.stat()
    raw = path.read_bytes()
    assert b"Synthetic Hearts review" in raw
    path.write_bytes(raw.replace(b"Synthetic Hearts review", b"Synthetic Hearts REVIEW"))
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert path.stat().st_size == stat.st_size
    with pytest.raises(StoreConflictError):
        service.validate_delivery(binding)


@pytest.fixture
def startup_archive(tmp_path, attempts):
    from skatmind.app_web.saved_match_analyses import archive_store

    app, service = setup_service(tmp_path)
    save(app, workspace=alex_workspace(count=3))
    archive = archive_store(app, initialize=True)
    # Reuse the module's genuine ordinary execution; no new fixture analysis.
    publish_fresh_archive(archive, archive.snapshot(), attempts[:1])
    return app, service, archive, attempts[0]


def test_opt_in_constructor_admits_once_and_hands_off_only_to_first_capture(
    startup_archive, monkeypatch,
):
    from test_automatic_match_learning_evidence import forbid_execution

    app, service, archive, candidate = startup_archive
    original = {p: p.read_bytes() for p in app.managed_home.root.rglob("*") if p.is_file()}
    forbid_execution(monkeypatch)
    counts = measure_work(monkeypatch, archive)
    store = service._store()
    receipt = store._startup_delivery_receipt
    assert receipt is not None and receipt.owner is store.owner
    assert store.owner is not archive.owner and archive._startup_delivery_receipt is None
    assert counts["admissions"] == counts["retained_results_loaded"] == 1
    counts.clear()
    resumed, _inventory, _epoch = service._capture(store)
    assert resumed is receipt.resumed
    assert resumed.available_evidence_ids == (candidate.evidence.identity,)
    assert counts["admissions"] == 0 and counts["object_reads"] >= 2
    assert store._startup_delivery_receipt is None
    assert service._delivery_snapshot_receipt.archive is receipt
    assert store._take_startup_delivery_receipt() is None
    # Clearing the normal receipt cannot recover the already-consumed startup reference.
    service._delivery_snapshot_receipt = None
    service._capture(store)
    assert counts["admissions"] == counts["retained_results_loaded"] == 1
    assert counts["manifest_publications"] == counts["object_publications"] == 0
    assert original == {p: p.read_bytes() for p in app.managed_home.root.rglob("*") if p.is_file()}


def test_ordinary_constructor_still_uses_its_original_snapshot_path(startup_archive, monkeypatch):
    _app, _service, archive, _candidate = startup_archive
    counts = measure_work(monkeypatch, archive)
    with monkeypatch.context() as patch:
        patch.setattr(AutomaticLearningStoreV1, "_snapshot_for_delivery",
                      lambda *a, **kw: pytest.fail("Ordinary construction seeded a receipt"))
        ordinary = AutomaticLearningStoreV1(archive.root)
    assert counts["admissions"] == 1
    assert ordinary._startup_delivery_receipt is None
    assert ordinary._take_startup_delivery_receipt() is None


@pytest.mark.parametrize("receipt_kind", ("absent", "wrong_owner", "unusable"))
def test_missing_or_foreign_startup_receipt_never_skips_capture_admission(
    startup_archive, monkeypatch, receipt_kind,
):
    _app, service, archive, candidate = startup_archive
    store = service._store()
    foreign = archive._snapshot_for_delivery()[1]
    assert foreign.owner is not store.owner
    store._startup_delivery_receipt = {
        "absent": None, "wrong_owner": foreign, "unusable": object()}[receipt_kind]
    counts = measure_work(monkeypatch, archive)
    resumed, _inventory, _epoch = service._capture(store)
    assert counts["admissions"] == counts["retained_results_loaded"] == 1
    assert resumed.available_evidence_ids == (candidate.evidence.identity,)
    assert store._startup_delivery_receipt is None
    assert service._delivery_snapshot_receipt.archive.owner is store.owner


def test_failed_first_capture_also_clears_startup_reference(startup_archive, monkeypatch):
    _app, service, archive, _candidate = startup_archive
    store = service._store()
    assert store._startup_delivery_receipt is not None
    with monkeypatch.context() as patch:
        def unavailable(*args):
            raise OSError("Controlled first capture interruption")
        patch.setattr(store, "_snapshot_for_delivery", unavailable)
        with pytest.raises(OSError):
            service._capture(store)
    assert store._startup_delivery_receipt is None
    counts = measure_work(monkeypatch, archive)
    service._capture(store)
    assert counts["admissions"] == 1


@pytest.mark.parametrize("restart", (False, True))
def test_service_replacement_and_restart_seed_their_own_store_receipt(
    startup_archive, monkeypatch, restart,
):
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
    from skatmind.app_web.context import AppWebContextV1

    app, first, archive, _candidate = startup_archive
    old = first._store()._startup_delivery_receipt
    counts = measure_work(monkeypatch, archive)
    other_app = AppWebContextV1.create(app.managed_home) if restart else app
    replacement = AutomaticMatchLearningServiceV1.open(other_app)
    store = replacement._store()
    fresh = store._startup_delivery_receipt
    assert fresh is not old and fresh.owner is store.owner and fresh.owner is not old.owner
    assert counts["admissions"] == (2 if restart else 1)
    counts.clear()
    replacement._capture(store)
    assert counts["admissions"] == 0 and store._startup_delivery_receipt is None
    if not restart:
        with pytest.raises(StoreConflictError):
            first._store()


@pytest.mark.parametrize("index", (0, 1), ids=("source", "report"))
def test_same_metadata_corruption_after_constructor_is_rejected_before_reuse(
    startup_archive, monkeypatch, index,
):
    from skatmind import automatic_learning_io as io

    _app, service, archive, candidate = startup_archive
    store = service._store()
    ref = candidate.objects[index].reference
    rewrite_same_metadata(io.object_path(store.root, ref))
    counts = measure_work(monkeypatch, archive)
    resumed, _inventory, _epoch = service._capture(store)
    assert counts["admissions"] == 1
    assert candidate.evidence.identity not in resumed.available_evidence_ids
    assert next(row for row in resumed.objects if row.reference == ref).storage_status == "corrupt"
    assert store._startup_delivery_receipt is service._delivery_snapshot_receipt is None


@pytest.mark.parametrize("change", ("manifest", "inventory", "limits", "root", "invalid_manifest"))
def test_first_capture_revalidates_constructor_bindings(startup_archive, monkeypatch, change):
    from automatic_learning_helpers import source_fixture

    from skatmind.automatic_learning_objects import manifest_bytes
    from skatmind.automatic_learning_store import StoreLimitsV1

    _app, service, archive, candidate = startup_archive
    store = service._store()
    receipt = store._startup_delivery_receipt
    if change == "manifest":
        before = receipt.resumed.manifest
        (store.root / "manifest.json").write_bytes(manifest_bytes(
            replace(before, revision=before.revision + 1)))
    elif change == "inventory":
        assert archive.publish_object(source_fixture()[1]) == "saved"
    elif change == "limits":
        store.limits = StoreLimitsV1(total_bytes=1)
    elif change == "root":
        (store.root / "reports").rename(store.root / "original-reports")
        (store.root / "reports").mkdir()
    else:
        (store.root / "manifest.json").write_bytes(b"{}")
    counts = measure_work(monkeypatch, archive)
    if change in ("root", "invalid_manifest"):
        with pytest.raises(ValueError):
            service._capture(store)
    else:
        resumed, _inventory, _epoch = service._capture(store)
        assert resumed is not receipt.resumed and counts["admissions"] == 1
        assert resumed.available_evidence_ids == (candidate.evidence.identity,)
        assert service._delivery_snapshot_receipt.archive is not receipt
    assert store._startup_delivery_receipt is None


@pytest.mark.parametrize("bound", ("_DELIVERY_RECEIPT_MAX_OBJECTS", "_DELIVERY_RECEIPT_MAX_BYTES"))
def test_startup_over_archive_bound_keeps_complete_strict_fallback(
    startup_archive, monkeypatch, bound,
):
    import skatmind.automatic_learning_store as storage

    _app, service, archive, candidate = startup_archive
    monkeypatch.setattr(storage, bound, 1)
    counts = measure_work(monkeypatch, archive)
    store = service._store()
    assert counts["admissions"] == 1 and store._startup_delivery_receipt is None
    resumed, _inventory, _epoch = service._capture(store)
    assert counts["admissions"] == 2 and service._delivery_snapshot_receipt is None
    assert resumed.available_evidence_ids == (candidate.evidence.identity,)


@pytest.mark.parametrize("bound", ("_DELIVERY_RECEIPT_MAX_OBJECTS", "_DELIVERY_RECEIPT_MAX_BYTES"))
def test_startup_receipt_cannot_bypass_combined_recording_input_bound(
    startup_archive, monkeypatch, bound,
):
    import skatmind.app_web.automatic_match_learning as module

    _app, service, archive, candidate = startup_archive
    store = service._store()
    receipt = store._startup_delivery_receipt
    objects = receipt.resumed.manifest.objects
    monkeypatch.setattr(module, bound, len(objects) if bound.endswith("OBJECTS") else
                        sum(row.reference.size_bytes for row in objects))
    counts = measure_work(monkeypatch, archive)
    resumed, _inventory, _epoch = service._capture(store)
    assert counts["admissions"] == 1
    assert resumed.available_evidence_ids == (candidate.evidence.identity,)
    assert store._startup_delivery_receipt is service._delivery_snapshot_receipt is None
    service._capture(store)
    assert counts["admissions"] == 2


@pytest.mark.parametrize("defect", ("unsupported", "expanded_limit", "invalid"))
def test_startup_seeding_preserves_strict_unavailable_evidence_and_expanded_bound(
    startup_archive, monkeypatch, defect,
):
    from test_automatic_match_evidence import commit_candidate, repack

    from skatmind.automatic_learning_codec import decode_json

    _app, service, archive, candidate = startup_archive
    payload = decode_json(candidate.objects[1].payload)
    if defect == "expanded_limit":
        payload["execution"] = {"encoding": "zlib-json-v1", "size": 128 * 1024 * 1024 + 1}
    elif defect == "invalid":
        payload["execution"] = None
    changed = repack(candidate, payload, codec=99 if defect == "unsupported" else 2)
    assert commit_candidate(archive, changed).status == "saved"
    counts = measure_work(monkeypatch, archive)
    store = service._store()
    assert counts["admissions"] == 1
    if defect == "expanded_limit":
        assert store._startup_delivery_receipt is None
    resumed, _inventory, _epoch = service._capture(store)
    assert candidate.evidence.identity in resumed.available_evidence_ids
    assert changed.evidence.identity not in resumed.available_evidence_ids
    assert store._startup_delivery_receipt is None
