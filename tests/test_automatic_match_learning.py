"""S4 service regressions with disposable genuine recording sources."""

from dataclasses import replace

import pytest
from test_match_workspace_contracts import _definition

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def setup_service(tmp_path):
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1

    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "home"))
    return app, AutomaticMatchLearningServiceV1.open(app)


def save(app, name="one", *, workspace=None):
    path = app.managed_home.category("matches").path / (name + ".json")
    workspace = workspace or create_match_workspace_v1(_definition(match_id=name))
    document = build_match_workspace_persistence_document_v1(workspace)
    assert save_match_workspace_file_v1(path, document,
        expected_content_fingerprint=None).status == "saved"
    return path, document


def test_empty_sources_and_restart_reproduce_all_ten_downloads(tmp_path):
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
    from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    original = path.read_bytes()
    assert service.inspect().status == "missing"
    assert service.update().status == "prepared"
    downloads = tuple(service.download(kind)
                      for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS)
    descriptor = service.inspect().generation
    assert len(descriptor.recipe.source_version_ids) == 1
    assert service.update().status == "reused"
    restarted = AutomaticMatchLearningServiceV1.open(app)
    assert restarted.inspect().status == "reconstruction_needed"
    assert restarted.update().status == "rebuilt"
    assert restarted.inspect().generation == descriptor
    assert tuple(restarted.download(kind) for kind in
                 LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS) == downloads
    assert path.read_bytes() == original


def test_duplicate_and_unidentified_invalid_candidates_are_not_sources(tmp_path):
    app, service = setup_service(tmp_path)
    path, _ = save(app)
    path.with_name("copy.json").write_bytes(path.read_bytes())
    path.with_name("invalid.json").write_bytes(b'{"match_id":"untrusted"}')
    assert service.update().status == "prepared"
    generation = service.inspect().generation
    assert generation.recipe.source_version_ids == ()
    assert [(row.source.product_id, row.reason) for row in generation.recipe.exclusions] == [
        ("one", "ambiguous")]
    assert sorted(row.status for row in generation.inventory) == [
        "ambiguous", "ambiguous", "invalid"]
    assert next(row for row in generation.inventory if row.status == "invalid").source is None


def test_new_source_during_unlocked_build_conflicts(tmp_path, monkeypatch):
    import skatmind.app_web.automatic_match_learning as module

    app, service = setup_service(tmp_path)
    save(app)
    original = module.build_automatic_match_bundle

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        save(app, "new")
        return value

    monkeypatch.setattr(module, "build_automatic_match_bundle", changed)
    assert service.update().status == "conflict"
    assert service.inspect().status == "missing"


def test_deleted_source_hides_aggregate_at_final_consumption(tmp_path):
    app, service = setup_service(tmp_path)
    path, _ = save(app)
    assert service.update().status == "prepared"

    def delete_during_projection(bundle):
        path.unlink()  # Controlled external mutation of the disposable source.
        return bundle.prepared.dataset_id

    with pytest.raises(ValueError, match="changed|deleted|conflict"):
        service.consume(delete_during_projection)
    assert service.inspect().status == "deleted"
    assert service.update().status == "prepared"
    assert service.inspect().generation.recipe.source_version_ids == ()


def test_changed_excluded_candidate_conflicts(tmp_path, monkeypatch):
    import skatmind.app_web.automatic_match_learning as module
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_learning_contracts import ExclusionV1, SourceKeyV1

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    archive = archive_store(app, initialize=True)
    before = archive.snapshot().manifest
    requested = replace(before, revision=1, exclusions=(ExclusionV1(
        source=SourceKeyV1(family="match", product_id="one"), reason="explicit"),))
    assert archive.update_manifest(
        requested, expected_manifest=before.fingerprint).status == "saved"
    original = module.build_automatic_match_bundle

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        path.write_bytes(b"{}")
        return value

    monkeypatch.setattr(module, "build_automatic_match_bundle", changed)
    assert service.update().status == "conflict"
    assert archive.snapshot().manifest == requested


def rewrite(path, document, *, title="Correction", revision=None):
    from skatmind.match_workspace_contracts import _build_match_workspace_v1

    old = document.workspace
    workspace = _build_match_workspace_v1(
        match_definition=replace(old.match_definition, title=title), slots=old.slots,
        revision=old.revision if revision is None else revision)
    changed = build_match_workspace_persistence_document_v1(workspace)
    assert save_match_workspace_file_v1(path, changed,
        expected_content_fingerprint=document.content_fingerprint).status == "saved"
    return changed


@pytest.mark.parametrize("revision", (0, 1, 8))
def test_content_authority_replaces_whole_contribution_and_keeps_archive(tmp_path, revision):
    from skatmind.match_workspace_contracts import _build_match_workspace_v1

    app, service = setup_service(tmp_path)
    workspace = create_match_workspace_v1(_definition(match_id="one"))
    workspace = _build_match_workspace_v1(match_definition=workspace.match_definition,
                                          revision=8, slots=workspace.slots)
    path, document = save(app, workspace=workspace)
    assert service.update().status == "prepared"
    first = service.inspect().generation
    rewrite(path, document, revision=revision)
    assert service.inspect().status == "outdated"
    assert service.consume(lambda value: dict((r.name, r.value) for r in value.coverage),
                           allow_outdated=True)["matches"] == "1"
    assert service.update().status == "prepared"
    second = service.inspect().generation
    assert len(second.recipe.source_version_ids) == 1
    assert second.recipe.source_version_ids != first.recipe.source_version_ids
    assert second.recipe.catalog_revision == first.recipe.catalog_revision + 1
    assert len(service.store.snapshot().manifest.sources) == 2


@pytest.mark.parametrize("failure", (
    "cap", "root_missing", "read_denied", "oversize", "interrupted"))
def test_incomplete_inventory_preserves_prior_generation(tmp_path, monkeypatch, failure):
    import skatmind.app_web.automatic_match_inventory as module

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    assert service.update().status == "prepared"
    before = service.store.snapshot().manifest
    if failure == "cap":
        monkeypatch.setattr(module, "MANAGED_ITEM_MAX_CANDIDATES", 1)
        save(app, "two")
    elif failure == "root_missing":
        path.parent.rename(path.parent.with_name("unavailable"))
    elif failure == "oversize":
        monkeypatch.setattr(module, "MANAGED_ITEM_MAX_IMPORT_BYTES", 10)
    elif failure == "read_denied":
        original = module.io.read_bounded

        def denied(target, limit):
            if target == path:
                raise PermissionError("controlled read denial")
            return original(target, limit)

        monkeypatch.setattr(module.io, "read_bounded", denied)
    else:
        original = module._capture

        def interrupted(root):
            value = original(root)
            path.write_bytes(path.read_bytes() + b" ")
            return value

        monkeypatch.setattr(module, "_capture", interrupted)
    assert service.update().status == "conflict"
    assert service.store.snapshot().manifest == before


def test_complete_empty_inventory_is_success_and_passive_does_not_initialize(tmp_path):
    app, service = setup_service(tmp_path)
    root = app.managed_home.root / "automatic-learning"
    assert service.inspect().status == "missing" and not root.exists()
    assert service.update().status == "prepared"
    assert service.inspect().generation.recipe.source_version_ids == ()
    assert service.consume(lambda value: value.prepared.learning_dataset.record_count) == 0


@pytest.mark.parametrize("change", ("invalid", "explicit", "duplicate", "root", "owner", "attempt"))
def test_every_input_and_owner_is_revalidated_after_build(tmp_path, monkeypatch, change):
    import skatmind.app_web.automatic_match_learning as module
    from skatmind.automatic_learning_contracts import ExclusionV1, SourceKeyV1

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    bad = path.with_name("bad.json")
    bad.write_bytes(b"{}")
    original = module.build_automatic_match_bundle
    original_root = path.parent

    def changed(*args, **kwargs):
        value = original(*args, **kwargs)
        if change == "invalid":
            bad.write_bytes(b"[]")
        elif change == "explicit":
            before = service.store.snapshot().manifest
            service.store.update_manifest(replace(before, revision=before.revision + 1,
                exclusions=(ExclusionV1(source=SourceKeyV1(family="match", product_id="one"),
                                        reason="explicit"),)), expected_manifest=before.fingerprint)
        elif change == "duplicate":
            path.with_name("duplicate.json").write_bytes(path.read_bytes())
        elif change == "root":
            original_root.rename(original_root.with_name("old-matches"))
            original_root.mkdir()
        elif change == "owner":
            module.AutomaticMatchLearningServiceV1.open(app)
        else:
            service.attempt = object()  # Controlled supersession seam.
        return value

    monkeypatch.setattr(module, "build_automatic_match_bundle", changed)
    assert service.update().status == "conflict"
    assert service.store.snapshot().manifest.current_generation is None


@pytest.mark.parametrize("stage", ("source", "generation", "manifest", "after_commit"))
def test_interrupted_update_has_one_authoritative_commit_boundary(tmp_path, monkeypatch, stage):
    import skatmind.automatic_learning_io as io

    app, service = setup_service(tmp_path)
    path, document = save(app)
    assert service.update().status == "prepared"
    before = service.store.snapshot().manifest
    rewrite(path, document)
    original_write, original_sync = io.write_temporary, io.sync_directory
    root = service.store.root

    def write(directory, raw):
        target = {"source": root / "sources", "generation": root / "generations",
                  "manifest": root}.get(stage)
        if directory == target:
            raise OSError("controlled pre-commit write fault")
        return original_write(directory, raw)

    def sync(directory):
        if stage == "after_commit" and directory == root:
            raise OSError("controlled post-replacement synchronization fault")
        return original_sync(directory)

    with monkeypatch.context() as patch:
        patch.setattr(io, "write_temporary", write)
        patch.setattr(io, "sync_directory", sync)
        result = service.update()
    after = service.store.snapshot().manifest
    if stage == "after_commit":
        assert result.status == "prepared" and result.committed
        assert after.revision == before.revision + 1
        assert service.inspect().status == "current"
    else:
        assert result.status == "failed" and after == before
        assert service.inspect().status == "outdated"
        assert service.update().status == "prepared"  # One explicit retry only.
    assert len(service.store.snapshot().manifest.sources) == 2


def test_candidate_and_reader_pins_survive_cleanup_without_stealing_other_owner(tmp_path):
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_match_evidence import build_managed_match_source

    app, service = setup_service(tmp_path)
    _, document = save(app)
    archive = archive_store(app, initialize=True)
    obj, _, _ = build_managed_match_source(document)
    pending = archive.begin_candidate((obj,))
    assert service.update().status == "prepared"
    assert service.store.owner is not archive.owner
    assert archive.publish_object(obj, candidate=pending) == "unchanged"
    archive.release_candidate(pending)
    manifest = archive.snapshot().manifest
    reference = manifest.current_generation
    with archive.pin_objects((reference,), expected_manifest=manifest.fingerprint):
        preview = archive.preview_cleanup(expected_manifest=manifest.fingerprint)
        assert preview.files == ()
        assert archive.commit_cleanup(preview).status == "unchanged"


@pytest.mark.parametrize("change", (
    "source", "new_source", "owner", "archive", "cleanup", "invalid", "attempt"))
def test_final_consumption_rejects_unlocked_changes(tmp_path, change):
    from skatmind.app_web.saved_match_analyses import SavedMatchAnalyses

    app, service = setup_service(tmp_path)
    path, document = save(app)
    assert service.update().status == "prepared"

    def project(bundle):
        if change == "source":
            rewrite(path, document)
        elif change == "new_source":
            save(app, "new")
        elif change == "owner":
            app.automatic_match_learning = None
        elif change == "archive":
            app.saved_match_analyses = SavedMatchAnalyses()
        elif change == "invalid":
            path.with_name("bad.json").write_bytes(b"{}")
        elif change == "attempt":
            service.attempt = object()
        else:
            before = service.store.snapshot().manifest
            preview = service.store.preview_cleanup(expected_manifest=before.fingerprint,
                release_source_version_ids=tuple(
                    row.source_version.identity for row in before.sources))
            assert service.store.commit_cleanup(preview).status == "saved"
            # Current descriptor's pin prevents its physical removal through delivery.
            assert service.store.read_object(before.current_generation)
        return bundle.download("player_catalog")

    with pytest.raises(ValueError):
        service.consume(project)


def test_quota_failure_preserves_sources_and_prior_descriptor(tmp_path):
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_learning_store import StoreLimitsV1

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    archive = archive_store(app, initialize=True)
    archive.limits = StoreLimitsV1(total_bytes=1)
    before = path.read_bytes()
    assert service.update().status == "quota"
    assert path.read_bytes() == before
    assert archive.snapshot().manifest.current_generation is None


def test_family_build_failure_publishes_nothing_and_manual_state_survives(tmp_path, monkeypatch):
    import skatmind.corpus_web.preparation as module
    from skatmind.corpus_web.context import LearningCorpusWebContextV1
    from skatmind.learning_corpus_persistence import initialize_learning_corpus_directory_v1

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    manual_root = app.managed_home.category("corpora").path / "manual"
    initialize_learning_corpus_directory_v1(manual_root, corpus_id="independent")
    manual = LearningCorpusWebContextV1.open(manual_root)
    module.prepare_learning_corpus_artifacts_web_v1(manual,
        dataset_id="manual", known_player_seed=7,
        unseen_player_seed=9, train_weight=60, validation_weight=20, test_weight=20)
    manual_values = (manual.store, manual.prepared_artifacts, manual.tactical_prepared_artifacts,
                     manual.tactical_coaching_prepared_artifacts,
                     manual.strategy_source_store.sources)
    before = {p: p.read_bytes() for category in app.managed_home.categories
              for p in category.path.rglob("*.json")}

    def failure(**kwargs):
        raise ValueError("controlled final Coaching-family failure")

    monkeypatch.setattr(module,
        "build_learning_corpus_tactical_cross_game_coaching_report_v1", failure)
    assert service.update().status == "failed"
    assert service.store.snapshot().manifest.current_generation is None
    assert all(p.read_bytes() == raw for p, raw in before.items()) and path in before
    assert (manual.store, manual.prepared_artifacts, manual.tactical_prepared_artifacts,
            manual.tactical_coaching_prepared_artifacts,
            manual.strategy_source_store.sources) == manual_values


@pytest.mark.parametrize("field", ("seed", "partition_weights", "builder_versions", "corpus_id",
                                   "derived_fingerprints", "input_fingerprint",
                                   "inventory_shape", "outcomes_shape"))
def test_storage_valid_generation_tampering_does_not_authorize_rebuild(tmp_path, field):
    from skatmind.automatic_learning_codec import canonical_json, decode_json

    app, service = setup_service(tmp_path)
    save(app)
    assert service.update().status == "prepared"
    store = service.store
    before = store.snapshot().manifest
    original = store.read_object(before.current_generation)
    data = decode_json(original.payload)
    if field in ("inventory_shape", "outcomes_shape"):
        data["inventory" if field == "inventory_shape" else "evidence_outcomes"] = None
    elif field == "input_fingerprint":
        data[field] = "f" * 64
    elif field == "seed":
        data["recipe"][field] = 7
    elif field == "partition_weights":
        data["recipe"][field] = [60, 20, 20]
    elif field == "builder_versions":
        data["recipe"][field][0]["value"] = "99"
    elif field == "corpus_id":
        data["recipe"][field] = "unrelated"
    else:
        data["recipe"][field][0]["value"] = "f" * 64
    obj = replace(original, payload=canonical_json(data))
    assert store.publish_object(obj) == "saved"
    requested = replace(before, revision=before.revision + 1,
        objects=tuple(row for row in before.objects if row.reference != before.current_generation)
                + (obj.entry,), current_generation=obj.reference)
    assert store.update_manifest(requested, expected_manifest=before.fingerprint).status == "saved"
    assert service.update().status in ("unsupported", "failed")
    assert store.snapshot().manifest == requested
    with pytest.raises(ValueError):
        service.download("player_catalog")


def test_successful_unchanged_and_restart_write_accounting(tmp_path, monkeypatch):
    import skatmind.app_web.automatic_match_learning as module
    import skatmind.automatic_learning_io as io
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1

    app, service = setup_service(tmp_path)
    path, document = save(app)
    writes = []
    preparations = []
    original = io.write_temporary
    original_build = module.build_automatic_match_bundle

    def build(*args, **kwargs):
        preparations.append("prepare")
        return original_build(*args, **kwargs)

    def counted(directory, raw):
        result = original(directory, raw)
        writes.append(directory.name)
        return result

    monkeypatch.setattr(io, "write_temporary", counted)
    monkeypatch.setattr(module, "build_automatic_match_bundle", build)
    assert service.update().status == "prepared"
    assert sorted(writes) == ["automatic-learning", "automatic-learning", "generations", "sources"]
    assert len(preparations) == 1
    writes.clear()
    assert service.update().status == "reused"
    assert service.download("player_catalog").content
    assert len(preparations) == 1
    service = AutomaticMatchLearningServiceV1.open(app)
    assert service.update().status == "rebuilt" and len(preparations) == 2
    assert writes == []
    rewrite(path, document)
    assert service.update().status == "prepared"
    assert sorted(writes) == ["automatic-learning", "generations", "sources"]
    writes.clear()
    path.unlink()
    assert service.update().status == "prepared"
    assert sorted(writes) == ["automatic-learning", "generations"]
    writes.clear()
    save(app, "replacement")

    def interrupted(directory, raw):
        if directory.name == "automatic-learning":
            raise OSError("controlled manifest fault before writing bytes")
        return counted(directory, raw)

    with monkeypatch.context() as patch:
        patch.setattr(io, "write_temporary", interrupted)
        assert service.update().status == "failed"
    assert sorted(writes) == ["generations", "sources"]
    writes.clear()
    assert service.update().status == "prepared"
    assert writes == ["automatic-learning"] and len(preparations) == 6


@pytest.mark.parametrize("field", ("match_workspace_persistence_version", "document_kind"))
def test_future_source_contract_is_safe_unsupported_without_product_identity(tmp_path, field):
    import json

    app, service = setup_service(tmp_path)
    path, document = save(app)
    data = document.to_dict()
    data[field] = 99 if field.endswith("version") else "future_match_workspace"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert service.update().status == "prepared"
    row, = service.inspect().generation.inventory
    assert row.status == "unsupported" and row.source is None


def test_newer_writer_after_our_manifest_commit_is_never_installed(tmp_path, monkeypatch):
    import skatmind.automatic_learning_io as io
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1

    app, service = setup_service(tmp_path)
    _, document = save(app)
    original = io.sync_directory
    competitor = []

    def newer(directory):
        if directory == app.managed_home.root / "automatic-learning" and not competitor:
            # Initialization also syncs, so wait for a committed descriptor.
            if service.store is None or service.store._manifest().current_generation is None:
                return original(directory)
            other_app = AppWebContextV1.create(app.managed_home)
            other = AutomaticMatchLearningServiceV1.open(other_app)
            competitor.append(other)
            save(app, "new")
            assert other.update().status == "prepared"
            raise OSError("controlled failed return after a newer successful writer")
        return original(directory)

    monkeypatch.setattr(io, "sync_directory", newer)
    result = service.update()
    assert result.status == "committed_superseded" and result.committed
    assert service._installed is None
    assert competitor[0].inspect().status == "current"
    assert len(competitor[0].inspect().generation.recipe.source_version_ids) == 2
    assert document.workspace.match_definition.match_id == "one"


def test_crash_after_commit_requires_explicit_restart_reconstruction(tmp_path, monkeypatch):
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1

    app, service = setup_service(tmp_path)
    save(app)

    def crash(*args, **kwargs):
        raise SystemExit("controlled process-death seam after descriptor commit")

    monkeypatch.setattr(service, "_install", crash)
    with pytest.raises(SystemExit):
        service.update()
    assert service.store.snapshot().manifest.current_generation is not None
    restarted = AutomaticMatchLearningServiceV1.open(app)
    assert restarted.inspect().status == "reconstruction_needed"
    assert restarted.update().status == "rebuilt"


def test_threaded_attempt_supersession_and_real_accepted_write_barrier(tmp_path, monkeypatch):
    import threading

    import skatmind.app_web.automatic_match_learning as module

    app, service = setup_service(tmp_path)
    path, document = save(app)
    entered, release = threading.Event(), threading.Event()
    original = module.build_automatic_match_bundle
    results = []

    def blocked(*args, **kwargs):
        assert not app.lock._is_owned()
        assert not service.coordinator.lock._is_owned()
        if threading.current_thread().name == "old-preparation":
            entered.set()
            assert release.wait(30)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "build_automatic_match_bundle", blocked)
    thread = threading.Thread(target=lambda: results.append(service.update()),
                              name="old-preparation")
    thread.start()
    try:
        assert entered.wait(30)
        epoch = service.coordinator.generation
        rewrite(path, document)
        assert service.coordinator.generation == epoch + 1
        assert service.update().status == "prepared"
        current = service.store.snapshot().manifest
    finally:
        release.set()
        thread.join(30)
    assert not thread.is_alive()
    assert results[0].status == "conflict"
    assert service.store.snapshot().manifest == current
    assert service.inspect().status == "current"


@pytest.mark.parametrize("change", ("source", "excluded", "owner"))
def test_change_during_manifest_temporary_write_rejects_final_commit(tmp_path, monkeypatch, change):
    import skatmind.automatic_learning_io as io

    app, service = setup_service(tmp_path)
    path, document = save(app)
    assert service.update().status == "prepared"
    rewrite(path, document)
    before = service.store.snapshot().manifest
    original = io.write_temporary

    def late(directory, raw):
        temporary = original(directory, raw)
        if directory == service.store.root:
            if change == "source":
                path.write_bytes(b"{}")
            elif change == "excluded":
                path.with_name("new-invalid.json").write_bytes(b"{}")
            else:
                app.automatic_match_learning = None
        return temporary

    monkeypatch.setattr(io, "write_temporary", late)
    assert service.update().status == "conflict"
    assert service.store.snapshot().manifest == before


@pytest.mark.parametrize("kind", ("directory", "file_symlink", "root_junction", "reparse"))
def test_inventory_never_follows_nonregular_or_linked_candidates(tmp_path, monkeypatch, kind):
    import os
    import stat
    import subprocess
    from types import SimpleNamespace

    import skatmind.app_web.automatic_match_inventory as inventory

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    before = path.read_bytes()
    if kind == "directory":
        path.with_name("directory.json").mkdir()
    elif kind == "file_symlink":
        try:
            path.with_name("link.json").symlink_to(path)
        except OSError:
            pytest.skip("This account cannot create real symlinks")
    elif kind == "root_junction":
        if os.name != "nt":
            pytest.skip("Windows junction boundary")
        old = path.parent.with_name("old-matches")
        path.parent.rename(old)
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(path.parent), str(old)],
                                capture_output=True)
        assert result.returncode == 0, result.stderr
        assert service.update().status == "conflict"
        assert (old / path.name).read_bytes() == before
        return
    else:
        original = type(path).lstat
        # Controlled Windows reparse metadata, distinct from actual junction test.
        def marked(value):
            info = original(value)
            if value == path:
                return SimpleNamespace(**{name: getattr(info, name) for name in (
                    "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode", "st_nlink")},
                    st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return info
        monkeypatch.setattr(type(path), "lstat", marked)
    assert service.update().status == "prepared"
    generation = service.inspect().generation
    assert sum(row.status == "invalid" for row in generation.inventory) == 1
    assert path.read_bytes() == before
    assert inventory.MANAGED_ITEM_MAX_CANDIDATES == 2048


def test_canonical_source_order_ignores_filename_revision_and_timestamp(tmp_path):
    app, service = setup_service(tmp_path)
    save(app, "zzz", workspace=create_match_workspace_v1(_definition(match_id="a")))
    save(app, "aaa", workspace=create_match_workspace_v1(_definition(match_id="z")))
    assert service.update().status == "prepared"
    recipe = service.inspect().generation.recipe
    records = {row.source_version.identity: row
               for row in service.store.snapshot().manifest.sources}
    assert tuple(records[key].source_version.source.product_id for key in recipe.source_version_ids
                 ) == ("a", "z")


def test_invalid_top_manifest_is_never_repaired(tmp_path):
    app, service = setup_service(tmp_path)
    save(app)
    assert service.update().status == "prepared"
    path = service.store.root / "manifest.json"
    path.write_bytes(b"{}")
    assert service.inspect().status == "excluded"
    assert service.update().status == "failed"
    assert path.read_bytes() == b"{}"


def test_independent_manual_copies_selection_and_prepared_state_survive_updates(tmp_path):
    from skatmind.app_web.learning_frontend import UnifiedLearningContextV1
    from skatmind.corpus_web.context import LearningCorpusWebContextV1
    from skatmind.corpus_web.downloads import build_learning_corpus_prepared_download_v1
    from skatmind.corpus_web.preparation import prepare_learning_corpus_artifacts_web_v1
    from skatmind.learning_corpus_import import import_match_workspace_file_into_learning_corpus_v1
    from skatmind.learning_corpus_persistence import (
        initialize_learning_corpus_directory_v1,
        load_learning_corpus_directory_v1,
    )

    app, service = setup_service(tmp_path)
    path, document = save(app)
    root = app.managed_home.category("corpora").path / "independent"
    initialize_learning_corpus_directory_v1(root, corpus_id="manual")

    def manual_import(resolution):
        before = load_learning_corpus_directory_v1(root).document
        return import_match_workspace_file_into_learning_corpus_v1(root, path,
            expected_catalog_revision=before.catalog.revision,
            expected_catalog_content_fingerprint=before.content_fingerprint,
            selection_mode="keep_current", same_revision_resolution=resolution)

    assert manual_import("reject").status == "applied"
    rewrite(path, document)
    assert manual_import("reject").status == "resolution_required"
    assert manual_import("retain").status == "applied"
    manual = LearningCorpusWebContextV1.open(root)
    prepare_learning_corpus_artifacts_web_v1(manual, dataset_id="manual", known_player_seed=0,
        unseen_player_seed=0, train_weight=70, validation_weight=15, test_weight=15)
    active = UnifiedLearningContextV1(category_root=root.parent, path=root,
                                      handle="a" * 64, corpus=manual)
    app.managed_stateful.active_learning = active
    original = {p: p.read_bytes() for p in root.rglob("*.json")}
    prepared = manual.prepared_artifacts
    selections = manual.store.document.catalog.current_matches
    download = build_learning_corpus_prepared_download_v1(manual, kind="player_catalog")
    assert service.update().status == "prepared"
    path.unlink()
    assert service.update().status == "prepared"
    assert service.inspect().generation.recipe.source_version_ids == ()
    assert all(p.read_bytes() == raw for p, raw in original.items())
    assert app.managed_stateful.active_learning is active and manual.prepared_artifacts is prepared
    assert manual.store.document.catalog.current_matches == selections
    assert build_learning_corpus_prepared_download_v1(manual, kind="player_catalog") == download


def test_external_hardlink_is_not_owned_source_identity(tmp_path):
    import os

    app, service = setup_service(tmp_path)
    path, _ = save(app)
    target = tmp_path / "external.json"
    os.link(path, target)
    before = target.read_bytes()
    assert service.update().status == "prepared"
    row, = service.inspect().generation.inventory
    assert row.status == "invalid" and row.source is None
    assert target.read_bytes() == before


def test_replaced_category_root_cannot_rebind_existing_service_owner(tmp_path):
    app, service = setup_service(tmp_path)
    path, _ = save(app)
    assert service.update().status == "prepared"
    root = path.parent
    original = path.read_bytes()
    root.rename(root.with_name("old-matches"))
    root.mkdir()
    path.write_bytes(original)
    assert service.inspect().status == "conflict"
    assert service.update().status == "conflict"
    with pytest.raises(ValueError):
        service.download("player_catalog")


@pytest.mark.parametrize("interval", ("before_consume", "after_consume"))
def test_unchanged_reuse_rejects_newer_generation_receipt(tmp_path, monkeypatch, interval):
    """Deterministic A/B interleaving around consume, with genuine saved sources."""
    from test_automatic_match_learning_evidence import forbid_execution

    import skatmind.app_web.automatic_match_learning as module
    import skatmind.automatic_learning_io as io

    app, service = setup_service(tmp_path)
    save(app)
    initial = service.update()
    assert initial.status == "prepared" and service.inspect().status == "current"
    old_installed = service._installed
    old_manifest = service.store.snapshot().manifest
    analyses = forbid_execution(monkeypatch)
    builds, writes, newer = [], [], []
    original_build, original_write = module.build_automatic_match_bundle, io.write_temporary
    original_consume = service.consume

    def build(*args, **kwargs):
        builds.append("build")
        return original_build(*args, **kwargs)

    def write(directory, raw):
        value = original_write(directory, raw)
        writes.append(directory.name)
        return value

    def complete_newer_update():
        # A has selected old_installed, but is paused outside consume's attempt capture
        # (or immediately after its final guard for the second interval).
        assert service._installed is old_installed
        attempt_a = service.attempt
        save(app, "second")  # Accepted Match persistence, not a fabricated inventory.
        result_b = service.update()
        assert result_b.status == "prepared" and service.attempt is not attempt_a
        assert len(result_b.generation.recipe.source_version_ids) == 2
        assert len(initial.generation.recipe.source_version_ids) == 1
        assert service._installed is not old_installed
        manifest_b = service.store.snapshot().manifest
        assert manifest_b.current_generation == service._installed.reference
        assert manifest_b.previous_generation == old_manifest.current_generation
        assert len(builds) == 1
        assert sorted(writes) == ["automatic-learning", "generations", "sources"]
        newer.append((result_b, service._installed, manifest_b,
                      {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")}))

    def interleaved(projector, **kwargs):
        if interval == "before_consume":
            complete_newer_update()
        value = original_consume(projector, **kwargs)
        if interval == "after_consume":
            complete_newer_update()
        return value

    monkeypatch.setattr(module, "build_automatic_match_bundle", build)
    monkeypatch.setattr(io, "write_temporary", write)
    monkeypatch.setattr(service, "consume", interleaved)
    result_a = service.update()
    (result_b, installed_b, manifest_b, bytes_b), = newer
    assert service._installed is installed_b
    assert service._installed.bundle is installed_b.bundle
    assert service.store.snapshot().manifest == manifest_b
    assert service.inspect().generation == result_b.generation
    assert service.inspect().status == "current"
    assert {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")} == bytes_b
    assert len(builds) == 1
    assert sorted(writes) == ["automatic-learning", "generations", "sources"]
    assert analyses == []
    assert result_a.status == "conflict"
    assert result_a.generation is None and not result_a.committed


@pytest.mark.parametrize("interval", ("before_consume", "after_consume"))
@pytest.mark.parametrize("change", ("attempt", "owner", "installed", "manifest"))
def test_unchanged_reuse_binds_original_authorization(tmp_path, monkeypatch, interval, change):
    """Controlled independent changes to each fast-path authorization component."""
    import skatmind.app_web.automatic_match_learning as module
    import skatmind.automatic_learning_io as io
    from skatmind.automatic_learning_contracts import ExclusionV1, SourceKeyV1

    app, service = setup_service(tmp_path)
    save(app)
    assert service.update().status == "prepared"
    installed = service._installed
    original_consume = service.consume
    expected = []

    def changed():
        if change == "attempt":
            service.attempt = object()
        elif change == "owner":
            app.automatic_match_learning = object()
        elif change == "installed":
            # Equal values are insufficient: the selected process-local bundle owner changed.
            service._installed = replace(installed)
        else:
            before = service.store.snapshot().manifest
            requested = replace(before, revision=before.revision + 1,
                exclusions=(ExclusionV1(source=SourceKeyV1(family="match", product_id="absent"),
                                        reason="explicit"),))
            assert service.store.update_manifest(
                requested, expected_manifest=before.fingerprint).status == "saved"
        expected.append((service._installed, service.store.snapshot().manifest,
                         {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")}))

    def forbidden(*args, **kwargs):
        pytest.fail("Superseded reuse must not prepare or write")

    def interleaved(projector, **kwargs):
        if interval == "before_consume":
            changed()
        with monkeypatch.context() as patch:
            patch.setattr(io, "write_temporary", forbidden)
            value = original_consume(projector, **kwargs)
        if interval == "after_consume":
            changed()
        monkeypatch.setattr(io, "write_temporary", forbidden)
        return value

    monkeypatch.setattr(module, "build_automatic_match_bundle", forbidden)
    monkeypatch.setattr(service, "consume", interleaved)
    result = service.update()
    (installed_after, manifest_after, bytes_after), = expected
    assert service._installed is installed_after
    assert service.store.snapshot().manifest == manifest_after
    assert {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")} == bytes_after
    assert result.status == "conflict"
    assert result.generation is None and not result.committed


def test_unchanged_reuse_preserves_bundle_identity_without_work(tmp_path, monkeypatch):
    from test_automatic_match_learning_evidence import forbid_execution

    import skatmind.app_web.automatic_match_learning as module
    import skatmind.automatic_learning_io as io

    app, service = setup_service(tmp_path)
    save(app)
    prepared = service.update()
    assert prepared.status == "prepared"
    installed = service._installed
    manifest = service.store.snapshot().manifest
    before = {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")}
    analyses = forbid_execution(monkeypatch)

    def forbidden(*args, **kwargs):
        pytest.fail("Unchanged reuse must perform no preparation, reservation or writes")

    monkeypatch.setattr(module, "build_automatic_match_bundle", forbidden)
    monkeypatch.setattr(io, "write_temporary", forbidden)
    monkeypatch.setattr(service.store, "begin_candidate", forbidden)
    monkeypatch.setattr(service.store, "publish_object", forbidden)
    monkeypatch.setattr(service.store, "update_manifest", forbidden)
    reused = service.update()
    assert reused.status == "reused" and reused.generation == prepared.generation
    assert service._installed is installed and service._installed.bundle is installed.bundle
    assert service.store.snapshot().manifest == manifest
    assert {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")} == before
    assert analyses == []
