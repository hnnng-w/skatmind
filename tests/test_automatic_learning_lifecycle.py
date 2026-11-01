import io as stdlib_io
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from automatic_learning_helpers import (
    commit_fixture,
    evidence_fixture,
    generation_fixture,
    source_fixture,
)

import skatmind.automatic_learning_io as io
from skatmind.automatic_learning_contracts import ManifestV1
from skatmind.automatic_learning_objects import manifest_bytes
from skatmind.automatic_learning_store import (
    StoreConflictError,
    StoreLimitError,
    StoreLimitsV1,
    initialize_automatic_learning_store_v1,
    resume_automatic_learning_store_v1,
)


@pytest.fixture
def store(tmp_path):
    return initialize_automatic_learning_store_v1(tmp_path / "automatic-learning")


def test_reads_are_bounded_even_if_file_grows_after_stat(tmp_path, monkeypatch):
    path = tmp_path / "growing"
    path.write_bytes(b"x")
    requested = []

    class GrowingFile(stdlib_io.BytesIO):
        def fileno(self):
            return 42

        def read(self, size=-1):
            requested.append(size)
            assert size == 33
            return super().read(size)

    before = path.stat()
    monkeypatch.setattr(io.os, "open", lambda *args: 42)
    monkeypatch.setattr(io.os, "fdopen", lambda *args: GrowingFile(b"x" * 100))
    monkeypatch.setattr(io.os, "fstat", lambda *args: before)
    with pytest.raises(ValueError, match="read bound"):
        io.read_bounded(path, 32)
    assert requested == [33]


def test_oversize_file_rejected_before_open(tmp_path, monkeypatch):
    path = tmp_path / "oversize"
    path.write_bytes(b"x" * 33)

    def forbidden(*args):
        pytest.fail("An oversize file must not be opened.")

    monkeypatch.setattr(io.os, "open", forbidden)
    with pytest.raises(ValueError, match="byte limit"):
        io.read_bounded(path, 32)


def test_object_limit_boundary_and_existing_reference_size(tmp_path):
    _, obj = source_fixture()
    limit = len(obj.raw)
    store = initialize_automatic_learning_store_v1(
        tmp_path / "automatic-learning", limits=StoreLimitsV1(object_bytes=limit),
    )
    assert store.publish_object(obj) == "saved"
    assert store.read_object(obj.reference) == obj
    _, larger = source_fixture(content="second-longer")
    with pytest.raises(StoreLimitError):
        store.publish_object(larger)
    with pytest.raises(ValueError, match="identity"):
        store.read_object(replace(obj.reference, size_bytes=1))


def test_pending_reservations_global_per_root_and_supersession(tmp_path):
    _, first = source_fixture(content="first")
    _, second = source_fixture(content="second")
    limit = max(len(first.raw), len(second.raw))
    limits = StoreLimitsV1(total_bytes=limit)
    one = initialize_automatic_learning_store_v1(tmp_path / "automatic-learning", limits=limits)
    two = resume_automatic_learning_store_v1(one.root, limits=limits)
    prior = one.begin_candidate((first,))
    with pytest.raises(StoreLimitError):
        two.begin_candidate((second,))
    # A replacement candidate releases only this owner's old reservation.
    active = one.begin_candidate((second,))
    with pytest.raises(StoreConflictError):
        one.publish_object(first, candidate=prior)
    with pytest.raises(StoreConflictError):
        one.release_candidate(prior)
    assert one.publish_object(second, candidate=active) == "saved"
    one.release_candidate(active)
    # Disk orphans still count after the pending reservation is released.
    with pytest.raises(StoreLimitError):
        two.publish_object(first)
    snapshot = two.snapshot()
    assert snapshot.retained_bytes == len(second.raw)
    assert len(snapshot.orphan_names) == 1


def test_concurrent_reservations_cannot_oversubscribe(tmp_path):
    _, first = source_fixture(content="first")
    _, second = source_fixture(content="second")
    limits = StoreLimitsV1(total_bytes=max(len(first.raw), len(second.raw)))
    one = initialize_automatic_learning_store_v1(tmp_path / "automatic-learning", limits=limits)
    two = resume_automatic_learning_store_v1(one.root, limits=limits)
    barrier = threading.Barrier(2)

    def reserve(store, obj):
        barrier.wait(timeout=5)
        try:
            store.begin_candidate((obj,))
            return "reserved"
        except StoreLimitError:
            return "limited"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reserve, one, first), pool.submit(reserve, two, second)]
        assert sorted(future.result(timeout=10) for future in futures) == ["limited", "reserved"]


def test_equal_pending_objects_are_accounted_once_and_publish_once(store):
    _, obj = source_fixture()
    other = resume_automatic_learning_store_v1(store.root)
    first = store.begin_candidate((obj,))
    second = other.begin_candidate((obj,))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(store.publish_object, obj, candidate=first),
                   pool.submit(other.publish_object, obj, candidate=second)]
        assert sorted(future.result(timeout=10) for future in futures) == ["saved", "unchanged"]
    assert store.snapshot().retained_bytes == len(obj.raw)


@pytest.mark.parametrize("kind", ["decision", "rollout", "historical"])
def test_evidence_count_bound_is_per_class_globally(tmp_path, kind):
    store = initialize_automatic_learning_store_v1(
        tmp_path / "automatic-learning", limits=StoreLimitsV1(evidence_per_class=1),
    )
    original = store.snapshot().manifest
    sources, evidence, objects = [], [], []
    for index in range(2):
        source, obj = source_fixture(name=f"source-{index}", content=str(index))
        entry, envelope = evidence_fixture(source, obj, evidence_class=kind)
        sources.append(source)
        evidence.append(entry)
        objects.extend((obj, envelope))
        store.publish_object(obj)
        store.publish_object(envelope)
    requested = replace(original, revision=1, sources=tuple(sources), evidence=tuple(evidence),
                        objects=tuple(obj.entry for obj in objects))
    with pytest.raises(StoreLimitError, match="class limit"):
        store.update_manifest(requested, expected_manifest=original.fingerprint)
    assert store.snapshot().manifest == original


def test_independent_evidence_classes_do_not_share_count_allowance(tmp_path):
    store = initialize_automatic_learning_store_v1(
        tmp_path / "automatic-learning", limits=StoreLimitsV1(evidence_per_class=1),
    )
    original = store.snapshot().manifest
    source, obj = source_fixture()
    store.publish_object(obj)
    evidence, objects = [], [obj]
    for kind in ("decision", "rollout", "historical"):
        entry, envelope = evidence_fixture(source, obj, evidence_class=kind)
        evidence.append(entry)
        objects.append(envelope)
        store.publish_object(envelope)
    requested = replace(original, revision=1, sources=(source,), evidence=tuple(evidence),
                        objects=tuple(obj.entry for obj in objects))
    result = store.update_manifest(requested, expected_manifest=original.fingerprint)
    assert result.status == "saved"


def test_old_dependencies_and_partial_temps_count_without_becoming_candidates(store):
    manifest, _ = commit_fixture(store)
    _, orphan = source_fixture(content="orphan")
    store.publish_object(orphan)
    temporary = store.root / "reports" / (".auto-" + "a" * 32 + ".tmp")
    temporary.write_bytes(b"partial")
    snapshot = store.snapshot()
    assert snapshot.manifest == manifest
    assert snapshot.retained_bytes == sum(ref.reference.size_bytes for ref in manifest.objects) + (
        len(orphan.raw) + len(b"partial")
    )
    assert len(snapshot.orphan_names) == len(snapshot.temporary_names) == 1
    tight = resume_automatic_learning_store_v1(store.root, limits=StoreLimitsV1(total_bytes=1))
    assert tight.snapshot().over_limit
    with pytest.raises(StoreLimitError):
        tight.publish_object(source_fixture(content="third")[1])


def test_cleanup_default_only_owned_unreferenced_objects(store):
    manifest, _ = commit_fixture(store)
    _, orphan = source_fixture(content="orphan")
    store.publish_object(orphan)
    temp = store.root / "reports" / (".auto-" + "b" * 32 + ".tmp")
    temp.write_bytes(b"partial")
    foreign = store.root / "reports" / "notes.txt"
    foreign.write_bytes(b"keep")
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint)
    assert len(preview.files) == 2
    assert preview.removed_evidence_ids == ()
    assert store.commit_cleanup(preview).status == "saved"
    assert foreign.read_bytes() == b"keep"
    assert store.snapshot().manifest == manifest
    assert store.snapshot().orphan_names == store.snapshot().temporary_names == ()


def test_cleanup_retires_dependent_generations_before_deleting_evidence(store):
    manifest, objects = commit_fixture(store, generation=True)
    second = generation_fixture(manifest.sources, manifest.evidence, seed=1)
    store.publish_object(second)
    both = replace(manifest, revision=2, objects=(*manifest.objects, second.entry),
                   current_generation=second.reference, previous_generation=objects[-1].reference)
    store.update_manifest(both, expected_manifest=manifest.fingerprint)
    preview = store.preview_cleanup(expected_manifest=both.fingerprint,
                                    remove_evidence_ids=(both.evidence[0].identity,))
    assert preview.manifest.current_generation is None
    assert preview.manifest.previous_generation is None
    assert preview.manifest.evidence == ()
    assert store.commit_cleanup(preview).status == "saved"
    assert store.snapshot().manifest == preview.manifest
    assert store.read_object(objects[0].reference) == objects[0]
    with pytest.raises(FileNotFoundError):
        store.read_object(objects[1].reference)


def test_removing_one_report_keeps_shared_original_source(store):
    manifest, objects = commit_fixture(store)
    entry, envelope = evidence_fixture(manifest.sources[0], objects[0], run=2)
    store.publish_object(envelope)
    both = replace(manifest, revision=2, evidence=(*manifest.evidence, entry),
                   objects=(*manifest.objects, envelope.entry))
    store.update_manifest(both, expected_manifest=manifest.fingerprint)
    preview = store.preview_cleanup(expected_manifest=both.fingerprint,
                                    remove_evidence_ids=(manifest.evidence[0].identity,))
    assert store.commit_cleanup(preview).status == "saved"
    assert store.read_object(objects[0].reference) == objects[0]
    assert store.read_object(envelope.reference) == envelope
    with pytest.raises(ValueError, match="original source"):
        store.preview_cleanup(expected_manifest=preview.manifest.fingerprint,
                              release_source_version_ids=(manifest.sources[0].source_version.identity,))


def test_pinned_reader_protects_released_dependencies_across_owners(store):
    manifest, objects = commit_fixture(store, generation=True)
    cleaner = resume_automatic_learning_store_v1(store.root)
    with store.pin_objects((objects[-1].reference,), expected_manifest=manifest.fingerprint):
        preview = cleaner.preview_cleanup(
            expected_manifest=manifest.fingerprint,
            remove_evidence_ids=(manifest.evidence[0].identity,),
            release_source_version_ids=(manifest.sources[0].source_version.identity,),
        )
        assert preview.files == ()
        assert cleaner.commit_cleanup(preview).status == "saved"
        for obj in objects:
            assert store.read_object(obj.reference) == obj
    current = cleaner.snapshot().manifest
    released = cleaner.preview_cleanup(expected_manifest=current.fingerprint)
    assert len(released.files) == 3
    assert cleaner.commit_cleanup(released).status == "saved"


@pytest.mark.parametrize("intervening", ["candidate", "publication", "reader", "manifest"])
def test_competing_cleanup_conflicts_without_deleting_new_work(store, intervening):
    manifest, objects = commit_fixture(store)
    _, orphan = source_fixture(content="orphan")
    store.publish_object(orphan)
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint)
    other = resume_automatic_learning_store_v1(store.root)
    if intervening == "candidate":
        other.begin_candidate((orphan,))
    elif intervening == "publication":
        other.publish_object(source_fixture(content="new")[1])
    elif intervening == "reader":
        with other.pin_objects((objects[0].reference,), expected_manifest=manifest.fingerprint):
            assert store.commit_cleanup(preview).status == "conflict"
        return
    else:
        newer = replace(manifest, revision=2)
        (store.root / "manifest.json").write_bytes(manifest_bytes(newer))
    assert store.commit_cleanup(preview).status == "conflict"
    assert store.read_object(orphan.reference) == orphan


def test_unwritten_candidate_protects_existing_original_dependency(store):
    source, obj = source_fixture()
    store.publish_object(obj)
    _, envelope = evidence_fixture(source, obj)
    candidate = store.begin_candidate((envelope,))
    original = store.snapshot().manifest
    preview = store.preview_cleanup(expected_manifest=original.fingerprint)
    assert not preview.files
    assert store.publish_object(envelope, candidate=candidate) == "saved"
    store.release_candidate(candidate)
    assert len(store.preview_cleanup(expected_manifest=original.fingerprint).files) == 2


def test_interrupted_cleanup_commits_references_first_and_leaves_only_orphans(store, monkeypatch):
    manifest, objects = commit_fixture(store, generation=True)
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint,
                                    remove_evidence_ids=(manifest.evidence[0].identity,))
    unlink = Path.unlink
    deletions = []

    def fail_second(path, *args, **kwargs):
        if path.suffix == ".json":
            deletions.append(path)
            if len(deletions) == 2:
                raise OSError("interrupted deletion")
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_second)
    with pytest.raises(OSError, match="interrupted"):
        store.commit_cleanup(preview)
    snapshot = resume_automatic_learning_store_v1(store.root).snapshot()
    assert snapshot.manifest == preview.manifest
    assert len(snapshot.orphan_names) == 1
    assert all(item.storage_status == "valid" for item in snapshot.objects)
    assert store.read_object(objects[0].reference) == objects[0]


def test_cleanup_rechecks_external_commit_before_each_deletion(store, monkeypatch):
    original = store.snapshot().manifest
    first, obj = source_fixture()
    second, other = source_fixture(name="second", content="second")
    for item in (obj, other):
        store.publish_object(item)
    preview = store.preview_cleanup(expected_manifest=original.fingerprint)
    first_name = preview.files[0][0]
    protected_source, protected_obj = (second, other) if first_name.endswith(
        obj.reference.fingerprint + ".json"
    ) else (first, obj)
    winner = replace(
        original, revision=1, sources=(protected_source,), objects=(protected_obj.entry,),
    )
    unlink = Path.unlink

    def race(path, *args, **kwargs):
        result = unlink(path, *args, **kwargs)
        (store.root / "manifest.json").write_bytes(manifest_bytes(winner))
        return result

    monkeypatch.setattr(Path, "unlink", race)
    assert store.commit_cleanup(preview).status == "conflict"
    assert store.read_object(protected_obj.reference) == protected_obj


def test_cleanup_empty_is_unchanged_and_preview_cannot_cross_owners(store):
    manifest = store.snapshot().manifest
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint)
    assert store.commit_cleanup(preview).status == "unchanged"
    other = resume_automatic_learning_store_v1(store.root)
    with pytest.raises(StoreConflictError):
        other.commit_cleanup(preview)


def test_unknown_kind_is_storage_only_and_unsupported(store):
    source, obj = source_fixture()
    unknown = replace(obj, kind="future_unknown")
    store.publish_object(unknown)
    original = store.snapshot().manifest
    requested = replace(original, revision=1, objects=(unknown.entry,),
                        sources=(replace(source, object_ref=unknown.reference),))
    # A future-shaped archive can be resumed without enabling an unknown consumer.
    (store.root / "manifest.json").write_bytes(manifest_bytes(requested))
    snapshot = resume_automatic_learning_store_v1(store.root).snapshot()
    assert snapshot.objects[0].storage_status == "valid"
    assert snapshot.objects[0].consumption_status == "unsupported"
    assert not snapshot.available_evidence_ids


def test_released_source_with_no_remaining_roots_is_cleanable(store):
    source, obj = source_fixture()
    store.publish_object(obj)
    original = store.snapshot().manifest
    requested = ManifestV1(space_id=original.space_id, revision=1,
                           sources=(source,), objects=(obj.entry,))
    store.update_manifest(requested, expected_manifest=original.fingerprint)
    preview = store.preview_cleanup(expected_manifest=requested.fingerprint,
                                    release_source_version_ids=(source.source_version.identity,))
    assert store.commit_cleanup(preview).status == "saved"
    assert store.snapshot().retained_bytes == 0


def test_cooperating_process_cannot_publish_while_reservation_or_reader_is_active(store):
    manifest, objects = commit_fixture(store)
    script = """
import sys
from pathlib import Path
from skatmind.automatic_learning_codec import canonical_json
from skatmind.automatic_learning_objects import StoredObjectV1
from skatmind.automatic_learning_store import resume_automatic_learning_store_v1
store = resume_automatic_learning_store_v1(Path(sys.argv[1]))
obj = StoredObjectV1(area='sources', kind='match_source', codec_version=1,
                     payload=canonical_json({'synthetic': 'another process'}))
print(store.publish_object(obj))
"""

    def child_status():
        result = subprocess.run([sys.executable, "-c", script, str(store.root)],
                                capture_output=True, text=True, check=True, timeout=30)
        return result.stdout.strip()

    candidate = store.begin_candidate((objects[0],))
    assert child_status() == "conflict"
    store.release_candidate(candidate)
    with store.pin_objects((objects[1].reference,), expected_manifest=manifest.fingerprint):
        assert child_status() == "conflict"
    assert child_status() == "saved"


def test_corrupt_removed_report_does_not_block_manifest_first_cleanup(store):
    manifest, objects = commit_fixture(store, generation=True)
    io.object_path(store.root, objects[1].reference).write_bytes(b"corrupt")
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint,
                                    remove_evidence_ids=(manifest.evidence[0].identity,))
    assert store.commit_cleanup(preview).status == "saved"
    assert store.snapshot().manifest.evidence == ()
    assert all(item.storage_status == "valid" for item in store.snapshot().objects)


def test_cleanup_can_release_evidence_at_exact_retained_object_quota(store):
    manifest, _ = commit_fixture(store)
    retained = store.snapshot().retained_bytes
    tight = resume_automatic_learning_store_v1(
        store.root, limits=StoreLimitsV1(total_bytes=retained),
    )
    preview = tight.preview_cleanup(expected_manifest=manifest.fingerprint,
                                    remove_evidence_ids=(manifest.evidence[0].identity,))
    assert tight.commit_cleanup(preview).status == "saved"
    assert tight.snapshot().retained_bytes < retained


def test_quarantined_unchanged_objects_can_remain_while_independent_evidence_is_removed(store):
    manifest, objects = commit_fixture(store)
    io.object_path(store.root, objects[0].reference).unlink()
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint,
                                    remove_evidence_ids=(manifest.evidence[0].identity,))
    assert store.commit_cleanup(preview).status == "saved"
    assert store.snapshot().objects[0].storage_status == "missing"


def test_process_exit_releases_candidate_lease_and_preserves_only_complete_orphans(store):
    original = store.snapshot().manifest
    script = """
import os, sys
from pathlib import Path
from skatmind.automatic_learning_codec import canonical_json
from skatmind.automatic_learning_objects import StoredObjectV1
from skatmind.automatic_learning_store import resume_automatic_learning_store_v1
store = resume_automatic_learning_store_v1(Path(sys.argv[1]))
obj = StoredObjectV1(area='sources', kind='match_source', codec_version=1,
                     payload=canonical_json({'synthetic': 'interrupted process'}))
candidate = store.begin_candidate((obj,))
assert store.publish_object(obj, candidate=candidate) == 'saved'
os._exit(7)
"""
    result = subprocess.run([sys.executable, "-c", script, str(store.root)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 7, result.stderr
    resumed = resume_automatic_learning_store_v1(store.root)
    snapshot = resumed.snapshot()
    assert snapshot.manifest == original
    assert len(snapshot.orphan_names) == 1
    assert resumed.publish_object(source_fixture()[1]) == "saved"


def test_pending_publication_interruption_does_not_register_evidence(store, monkeypatch):
    original = store.snapshot().manifest
    _, obj = source_fixture()
    candidate = store.begin_candidate((obj,))
    real_write = io.write_temporary

    def interrupted(directory, raw):
        real_write(directory, raw[:20])
        raise OSError("interrupted staged write")

    monkeypatch.setattr(io, "write_temporary", interrupted)
    with pytest.raises(OSError):
        store.publish_object(obj, candidate=candidate)
    assert store.snapshot().manifest == original
    assert not store.snapshot().orphan_names
    assert len(store.snapshot().temporary_names) == 1
    assert store.snapshot().retained_bytes == 20
    store.release_candidate(candidate)
    preview = store.preview_cleanup(expected_manifest=original.fingerprint)
    assert len(preview.files) == 1
    assert store.commit_cleanup(preview).status == "saved"
