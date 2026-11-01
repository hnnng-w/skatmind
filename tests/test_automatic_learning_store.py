import os
import subprocess
from dataclasses import replace

import pytest
from automatic_learning_helpers import (
    commit_fixture,
    evidence_fixture,
    indexed_manifest,
    source_fixture,
)

import skatmind.automatic_learning_io as io
import skatmind.automatic_learning_store as storage
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_learning_contracts import ManifestV1
from skatmind.automatic_learning_objects import manifest_bytes
from skatmind.automatic_learning_store import (
    StoreConflictError,
    UnsupportedEvidenceError,
    initialize_automatic_learning_store_v1,
    resume_automatic_learning_store_v1,
)


@pytest.fixture
def store(tmp_path):
    return initialize_automatic_learning_store_v1(tmp_path / "automatic-learning")


def test_initialize_resume_are_explicit_and_fresh(tmp_path):
    root = storage.resolve_automatic_learning_root_v1(tmp_path)
    assert not root.exists()
    with pytest.raises(FileNotFoundError):
        resume_automatic_learning_store_v1(root)
    assert not root.exists()
    first = initialize_automatic_learning_store_v1(root)
    second = resume_automatic_learning_store_v1(root)
    assert first.owner is not second.owner
    assert first.snapshot() == second.snapshot()
    assert {path.name for path in root.iterdir()} == {
        "sources", "reports", "generations", "manifest.json", ".coordination.lock",
    }
    with pytest.raises(FileExistsError):
        initialize_automatic_learning_store_v1(root)


@pytest.mark.parametrize("raw", [b"{}", b'{"x":1,"x":2}', b'{"x":NaN}', b"[]"])
def test_invalid_top_manifest_blocks_without_empty_replacement(store, raw):
    path = store.root / "manifest.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        resume_automatic_learning_store_v1(store.root)
    with pytest.raises(ValueError):
        store.publish_object(source_fixture()[1])
    assert path.read_bytes() == raw


def test_storage_roundtrip_does_not_admit_synthetic_reports(store):
    manifest, objects = commit_fixture(store, generation=True)
    resumed = resume_automatic_learning_store_v1(store.root)
    snapshot = resumed.snapshot()
    assert snapshot.manifest == manifest
    assert snapshot.available_evidence_ids == snapshot.trusted_binding_ids == ()
    assert all(item.storage_status == "valid" for item in snapshot.objects)
    assert all(item.consumption_status == "unsupported" for item in snapshot.objects)
    for obj in objects:
        assert resumed.read_object(obj.reference) == obj
    with pytest.raises(UnsupportedEvidenceError):
        resumed.read_evidence(manifest.evidence[0].identity)


def test_exact_publication_and_manifest_bindings_are_idempotent(store):
    manifest, objects = commit_fixture(store)
    before = (store.root / "manifest.json").read_bytes()
    for obj in objects:
        assert store.publish_object(obj) == "unchanged"
    result = store.update_manifest(replace(manifest, revision=manifest.revision + 1),
                                   expected_manifest=manifest.fingerprint)
    assert result.status == "unchanged"
    assert (store.root / "manifest.json").read_bytes() == before


def test_unchanged_commit_releases_only_its_candidate(store):
    manifest, objects = commit_fixture(store)
    candidate = store.begin_candidate(objects)
    result = store.update_manifest(manifest, expected_manifest=manifest.fingerprint,
                                   candidate=candidate)
    assert result.status == "unchanged"
    with pytest.raises(StoreConflictError):
        store.release_candidate(candidate)
    assert store._coordinator.lease is None


def test_resume_detects_manifest_change_during_dependency_validation(store, monkeypatch):
    manifest, _ = commit_fixture(store)
    original = store._object_states
    changed = replace(manifest, revision=2)

    def racing_objects(value):
        result = original(value)
        (store.root / "manifest.json").write_bytes(manifest_bytes(changed))
        return result

    monkeypatch.setattr(store, "_object_states", racing_objects)
    with pytest.raises(StoreConflictError, match="during resume"):
        store.snapshot()
    assert resume_automatic_learning_store_v1(store.root).snapshot().manifest == changed


@pytest.mark.parametrize("winner", ["equal", "corrupt", "different"])
def test_no_clobber_publication_winner_is_validated(store, monkeypatch, winner):
    _, obj = source_fixture()
    _, different = source_fixture(content="other")
    original_link = os.link

    def racing_link(source, target):
        if winner == "equal":
            original_link(source, target)
        else:
            target.write_bytes(b"{}\n" if winner == "corrupt" else different.raw)
        raise FileExistsError("racing winner")

    monkeypatch.setattr(storage.os, "link", racing_link)
    if winner == "equal":
        assert store.publish_object(obj) == "unchanged"
    else:
        with pytest.raises(ValueError):
            store.publish_object(obj)
    path = io.object_path(store.root, obj.reference)
    assert path.read_bytes() == (obj.raw if winner == "equal" else
                                 b"{}\n" if winner == "corrupt" else different.raw)
    assert not store.snapshot().temporary_names


def test_stale_manifest_conflicts_without_automatic_retry(store):
    original = store.snapshot().manifest
    manifest, _ = indexed_manifest(store)
    assert store.update_manifest(manifest, expected_manifest=original.fingerprint).status == "saved"
    conflict = store.update_manifest(manifest, expected_manifest=original.fingerprint)
    assert conflict.status == "conflict"
    assert store.snapshot().manifest == manifest


def test_second_manifest_check_preserves_concurrent_winner(store, monkeypatch):
    original = store.snapshot().manifest
    requested, _ = indexed_manifest(store)
    winner = ManifestV1(space_id=original.space_id, revision=1)
    write = io.write_temporary

    def race(directory, raw):
        path = write(directory, raw)
        (store.root / "manifest.json").write_bytes(manifest_bytes(winner))
        return path

    monkeypatch.setattr(io, "write_temporary", race)
    result = store.update_manifest(requested, expected_manifest=original.fingerprint)
    assert result.status == "conflict"
    assert store.snapshot().manifest == winner
    assert len(store.snapshot().orphan_names) == 2


@pytest.mark.parametrize("phase", ["write", "flush", "replace", "after_replace", "return"])
def test_manifest_interruption_commit_boundary(store, monkeypatch, phase):
    original = store.snapshot().manifest
    requested, _ = indexed_manifest(store, generation=True)
    replace_file = os.replace
    original_result = storage.WriteResultV1

    def fail(*args, **kwargs):
        raise OSError("injected interruption")

    if phase == "write":
        monkeypatch.setattr(io, "write_temporary", fail)
    elif phase == "flush":
        monkeypatch.setattr(io.os, "fsync", fail)
    elif phase == "replace":
        monkeypatch.setattr(storage.os, "replace", fail)
    elif phase == "after_replace":
        def committed_then_failed(source, target):
            replace_file(source, target)
            raise OSError("injected interruption")
        monkeypatch.setattr(storage.os, "replace", committed_then_failed)
    else:
        monkeypatch.setattr(storage, "WriteResultV1", fail)
    with pytest.raises(OSError, match="injected"):
        store.update_manifest(requested, expected_manifest=original.fingerprint)
    monkeypatch.setattr(storage, "WriteResultV1", original_result)
    resumed = resume_automatic_learning_store_v1(store.root)
    assert resumed.snapshot().manifest == (
        requested if phase in ("after_replace", "return") else original
    )
    assert all(item.storage_status == "valid" for item in resumed.snapshot().objects)


def test_failure_after_commit_never_rolls_back_newer_writer(store, monkeypatch):
    original = store.snapshot().manifest
    requested, _ = indexed_manifest(store)
    newer = replace(requested, revision=2)
    replace_file = os.replace

    def two_commits(source, target):
        replace_file(source, target)
        target.write_bytes(manifest_bytes(newer))
        raise OSError("after newer commit")

    monkeypatch.setattr(storage.os, "replace", two_commits)
    with pytest.raises(OSError):
        store.update_manifest(requested, expected_manifest=original.fingerprint)
    assert resume_automatic_learning_store_v1(store.root).snapshot().manifest == newer


def test_initializer_failure_after_commit_preserves_manifest(tmp_path, monkeypatch):
    original = storage.AutomaticLearningStoreV1

    def fail(*args, **kwargs):
        raise OSError("return load failed")

    monkeypatch.setattr(storage, "AutomaticLearningStoreV1", fail)
    root = tmp_path / "automatic-learning"
    with pytest.raises(OSError):
        initialize_automatic_learning_store_v1(root)
    assert original(root).snapshot().manifest.revision == 0


@pytest.mark.parametrize("damage", ["missing", "corrupt", "fingerprint", "unknown_codec"])
def test_individual_dependency_quarantine_preserves_independent_entries(store, damage):
    original = store.snapshot().manifest
    source, obj = source_fixture()
    if damage == "unknown_codec":
        obj = replace(obj, codec_version=999)
        source = replace(source, object_ref=obj.reference)
    evidence, envelope = evidence_fixture(source, obj)
    independent, independent_obj = source_fixture(name="independent", content="independent")
    for item in (obj, envelope, independent_obj):
        store.publish_object(item)
    requested = replace(original, revision=1, sources=(source, independent), evidence=(evidence,),
                        objects=tuple(item.entry for item in (obj, envelope, independent_obj)))
    store.update_manifest(requested, expected_manifest=original.fingerprint)
    path = io.object_path(store.root, obj.reference)
    if damage == "missing":
        path.unlink()
    elif damage == "corrupt":
        path.write_bytes(b"{}")
    elif damage == "fingerprint":
        data = decode_json(obj.raw)
        data["payload"]["changed"] = True
        path.write_bytes(canonical_json(data) + b"\n")
    manifest_before = (store.root / "manifest.json").read_bytes()
    snapshot = resume_automatic_learning_store_v1(store.root).snapshot()
    states = {item.reference: item for item in snapshot.objects}
    assert states[independent_obj.reference].storage_status == "valid"
    if damage == "unknown_codec":
        assert states[obj.reference].consumption_status == "unsupported"
        assert states[envelope.reference].consumption_status == "unsupported"
    else:
        expected_status = "missing" if damage == "missing" else "corrupt"
        assert states[obj.reference].storage_status == expected_status
        assert states[envelope.reference].consumption_status == "dependency_unavailable"
    assert (store.root / "manifest.json").read_bytes() == manifest_before


def test_publication_and_manifest_reject_missing_dependencies(store):
    original = store.snapshot().manifest
    source, obj = source_fixture()
    evidence, envelope = evidence_fixture(source, obj)
    with pytest.raises(FileNotFoundError):
        store.publish_object(envelope)
    manifest = replace(original, revision=1, sources=(source,), evidence=(evidence,),
                       objects=(obj.entry, envelope.entry))
    with pytest.raises(ValueError, match="intact dependencies"):
        store.update_manifest(manifest, expected_manifest=original.fingerprint)
    assert store.snapshot().manifest == original


def test_same_version_cannot_rebind_object_or_execution_situation(store):
    manifest, _ = commit_fixture(store)
    evidence = manifest.evidence[0]
    changed = replace(evidence, situation=replace(evidence.situation, actor_id="other"))
    with pytest.raises(ValueError, match="immutable"):
        store.update_manifest(replace(manifest, revision=2, evidence=(changed,)),
                              expected_manifest=manifest.fingerprint)


def test_owned_directory_substitution_is_a_conflict(store):
    reports = store.root / "reports"
    reports.rename(store.root / "prior-reports")
    reports.mkdir()
    with pytest.raises(StoreConflictError):
        store.snapshot()


def test_linked_object_is_quarantined_and_never_followed(store, tmp_path):
    manifest, objects = commit_fixture(store)
    obj = objects[0]
    path = io.object_path(store.root, obj.reference)
    target = tmp_path / "external.json"
    target.write_bytes(obj.raw)
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("Creating symlinks requires account privileges.")
    snapshot = store.snapshot()
    assert snapshot.objects[0].storage_status == "corrupt"
    preview = store.preview_cleanup(expected_manifest=manifest.fingerprint)
    assert not preview.files
    assert target.read_bytes() == obj.raw


@pytest.mark.parametrize("directory", ["root", "sources"])
def test_linked_root_or_object_directory_rejected(tmp_path, directory):
    root = tmp_path / "real"
    store = initialize_automatic_learning_store_v1(root)
    if directory == "root":
        link = tmp_path / "link"
        target = root
    else:
        link = root / "sources"
        link.rmdir()
        target = tmp_path / "outside"
        target.mkdir()
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires account privileges.")
    with pytest.raises(ValueError):
        resume_automatic_learning_store_v1(link if directory == "root" else store.root)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
@pytest.mark.parametrize("directory", ["root", "sources"])
def test_windows_junctions_rejected_without_following_targets(tmp_path, directory):
    root = tmp_path / "automatic-learning"
    initialize_automatic_learning_store_v1(root)
    if directory == "root":
        junction, target = tmp_path / "junction", root
    else:
        junction, target = root / "sources", tmp_path / "outside"
        junction.rmdir()
        target.mkdir()
    result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(target)],
                            capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    try:
        with pytest.raises(ValueError, match="links or reparse"):
            resume_automatic_learning_store_v1(junction if directory == "root" else root)
        assert target.is_dir()
    finally:
        junction.rmdir()
