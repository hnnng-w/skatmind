"""Bounded S4 archive admission reuse always requires freshly checked exact bytes."""

import os
from collections import Counter
from dataclasses import replace
from time import perf_counter

import pytest
from learning_archive_fixture_helpers import publish_fresh_archive, work_phase
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
