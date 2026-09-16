"""Real filesystem guards plus explicitly simulated unavailable filesystem edges."""

import json
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_unified_local_app_managed_items import _save_session

import skatmind.app_web.recording_deletion as deletion
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.managed_item_storage import build_managed_item_handle_v1


def saved(tmp_path):
    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "disposable"))
    root = app.managed_stateful.root("sessions")
    target = root / "imported-noncanonical-name.json"
    _save_session(target)
    discovery = app.managed_stateful.refresh("sessions")
    values = {"family": "sessions", "handle": discovery.view.items[0].handle,
              "generation": str(discovery.view.generation), "return_area": "sessions"}
    return app, root, target, values


def test_real_symlink_is_not_followed(tmp_path):
    app, root, target, _ = saved(tmp_path)
    link = root / "link.json"
    try:
        link.symlink_to(target)
    except OSError as error:
        code = error.winerror if os.name == "nt" else error.errno
        pytest.skip(f"Actual symlink creation unavailable: {code}")
    original = target.read_bytes()
    with pytest.raises((ValueError, deletion.RecordingDeletionConflict)):
        deletion._load(root, link, "sessions")
    assert target.read_bytes() == original and link.is_symlink()
    assert app.recording_deletion.pending is None


@pytest.mark.skipif(os.name != "nt", reason="Windows junction fixture")
def test_real_junction_root_is_not_followed(tmp_path):
    import _winapi
    _, root, target, _ = saved(tmp_path)
    junction = tmp_path / "junction"
    _winapi.CreateJunction(str(root), str(junction))
    assert junction.is_junction()
    original = target.read_bytes()
    with pytest.raises((ValueError, deletion.RecordingDeletionConflict)):
        deletion._load(junction, junction / target.name, "sessions")
    assert target.read_bytes() == original and junction.is_junction()


def test_simulated_reparse_attributes_and_multiple_links_are_rejected(tmp_path, monkeypatch):
    _, root, target, _ = saved(tmp_path)
    real = Path.lstat
    for attributes, links in ((getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024), 1), (0, 2)):
        def simulated(path, *, attributes=attributes, links=links):
            value = real(path)
            if path != target:
                return value
            return SimpleNamespace(**{name: getattr(value, name) for name in (
                "st_dev", "st_ino", "st_mode", "st_size", "st_ctime_ns", "st_mtime_ns")},
                st_file_attributes=attributes, st_nlink=links)
        with monkeypatch.context() as patch:
            patch.setattr(Path, "lstat", simulated)
            with pytest.raises(deletion.RecordingDeletionConflict):
                deletion._checked_stat(root, target)
    assert target.is_file()


def test_traversal_nonregular_and_size_checks_precede_loader(tmp_path, monkeypatch):
    _, root, target, _ = saved(tmp_path)
    outside = tmp_path / "outside.json"
    _save_session(outside)
    directory = root / "directory.json"
    directory.mkdir()
    for path in (outside, root / ".." / "outside.json", directory):
        with pytest.raises((OSError, ValueError, deletion.RecordingDeletionConflict)):
            deletion._load(root, path, "sessions")
    # A bounded size guard fixture, not a real 16-MiB Product.
    monkeypatch.setattr(deletion, "MANAGED_ITEM_MAX_IMPORT_BYTES", 1)
    def forbidden(*args):
        raise AssertionError("An oversized source must not reach its Product loader")
    monkeypatch.setattr(deletion.session_files, "load_session_file", forbidden)
    with pytest.raises(deletion.RecordingDeletionConflict):
        deletion._load(root, target, "sessions")
    assert target.is_file() and outside.is_file() and directory.is_dir()


def test_detected_change_during_strict_load_preserves_current_file(tmp_path, monkeypatch):
    app, _, target, values = saved(tmp_path)
    deletion.prepare_recording_deletion(app, values)
    selection = app.recording_deletion.pending.selection
    original = target.read_bytes()
    real = deletion.session_files.load_session_file
    calls = []
    def changed(path):
        result = real(path)
        if not calls:
            target.write_bytes(original + b" ")
            calls.append(path)
        return result
    monkeypatch.setattr(deletion.session_files, "load_session_file", changed)
    with pytest.raises(deletion.RecordingDeletionConflict):
        deletion.apply_recording_deletion(app, {"deletion_selection": selection,
                                               "confirm_delete": "on"})
    assert target.read_bytes() == original + b" " and calls
    assert app.recording_deletion.pending is None


def test_unlink_and_reads_hold_no_app_or_profile_lock(tmp_path, monkeypatch):
    app, _, target, values = saved(tmp_path)
    original = target.read_bytes()
    real_load, real_unlink = deletion.session_files.load_session_file, Path.unlink
    def checked_load(path):
        assert not app.lock._is_owned() and not app.profile_lock.locked()
        return real_load(path)
    def checked_unlink(path, *args, **kwargs):
        assert path == target
        assert not app.lock._is_owned() and not app.profile_lock.locked()
        assert app.managed_stateful.session_lifecycle_lock._is_owned()
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(deletion.session_files, "load_session_file", checked_load)
    monkeypatch.setattr(Path, "unlink", checked_unlink)
    deletion.prepare_recording_deletion(app, values)
    preview = app.recording_deletion.pending
    assert preview.handle == build_managed_item_handle_v1(
        family="sessions", basename=target.name)
    assert target.read_bytes() == original
    deletion.apply_recording_deletion(app, {"deletion_selection": preview.selection,
                                           "confirm_delete": "on"})
    assert not target.exists() and app.recording_deletion.outcome == "deleted"


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_legacy_preview_never_migrates_or_saves_source(tmp_path, monkeypatch, family):
    from test_skatmind_rename import _legacy_session_document, _legacy_workspace_document
    from test_unified_local_app_managed_items import _save_match

    app, _, _, _ = saved(tmp_path)
    root = app.managed_stateful.root(family)
    path = root / "legacy-synthetic.json"
    if family == "sessions":
        _save_session(path, session_id="legacy-synthetic-deletion")
        document = deletion.session_files.load_session_file(path).value.document
        legacy = _legacy_session_document(document)
    else:
        _save_match(path)
        document = deletion.load_match_workspace_file_v1(path).document
        legacy = _legacy_workspace_document(document)
    raw = json.dumps(legacy, indent=3).encode()
    path.write_bytes(raw)
    discovered = app.managed_stateful.refresh(family)
    entry = next(entry for entry in discovered.entries if entry.path == path)
    values = {"family": family, "handle": entry.summary.handle,
              "generation": str(discovered.view.generation), "return_area": family}
    if family == "sessions":
        # Existing public-loader output validation rejects the legacy kind. Deletion
        # neither bypasses discovery's invalid classification nor canonicalizes it.
        assert entry.summary.status == "invalid"
        with pytest.raises(deletion.RecordingDeletionConflict):
            deletion.prepare_recording_deletion(app, values)
        assert path.read_bytes() == raw
        return
    def forbidden(*args, **kwargs):
        raise AssertionError("Deletion must never save a migrated source")
    monkeypatch.setattr(deletion.session_files, "save_session_file", forbidden)
    deletion.prepare_recording_deletion(app, values)
    assert path.read_bytes() == raw
    selected = app.recording_deletion.pending.selection
    deletion.cancel_recording_deletion(app, {"deletion_selection": selected})
    assert path.read_bytes() == raw
