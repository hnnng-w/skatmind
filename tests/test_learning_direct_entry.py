"""Exact binding, saved-source lifecycle and real Corpus conflict outcomes."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from test_learning_direct_entry_web import (
    add_form,
    build,
    create_collection,
    downloads,
    saved_bytes,
    source_handle,
)
from test_learning_direct_entry_web import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_review_navigation import chooser_form, external_pass, saved_partial_match
from test_recording_deletion_web import preview
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.learning_direct_entry as entry
from skatmind.app_web.learning_frontend import build_unified_learning_state_v1
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@pytest.mark.parametrize("mode", ("empty", "passed", "complete"))
def test_empty_passed_and_single_complete_game_are_valid_sources(localized_server, mode):
    from test_match_workspace_contracts import _complete_observed_game, _set_game

    browser = Browser(localized_server)
    path, partial = saved_partial_match(localized_server)
    empty = create_match_workspace_v1(partial.match_definition)
    document = build_match_workspace_persistence_document_v1(empty)
    assert save_match_workspace_file_v1(path, document,
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(
            partial).content_fingerprint).status == "saved"
    if mode == "passed":
        external_pass(path, empty)
    elif mode == "complete":
        complete = _set_game(empty, _complete_observed_game(empty.match_definition))
        assert save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(
            complete), expected_content_fingerprint=document.content_fingerprint).status == "saved"
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    build(browser)
    state = build_unified_learning_state_v1(
        localized_server.app_context.managed_stateful.active_learning)
    assert state["prepared"]["observed_decision_count"] == (30 if mode == "complete" else 0)
    assert state["prepared"]["strategy_teacher_evidence_count"] == 0
    assert state["prepared"]["dataset_status"] == ("complete" if mode == "complete" else "empty")
    downloads(browser)


def test_same_revision_reject_then_explicit_retain_without_retry(localized_server, monkeypatch):
    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    target = localized_server.app_context.managed_stateful.active_learning
    build(browser)
    prepared = target.corpus.prepared_artifacts
    old_current = target.corpus.store.document.catalog.current_matches
    altered = _build_match_workspace_v1(match_definition=replace(workspace.match_definition,
        title="Different content"), revision=workspace.revision, slots=workspace.slots)
    assert save_match_workspace_file_v1(
        path, build_match_workspace_persistence_document_v1(altered),
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(
            workspace).content_fingerprint).status == "saved"
    calls = []
    real = entry.import_workspace_bytes_into_unified_learning_v1
    def counted(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    monkeypatch.setattr(entry, "import_workspace_bytes_into_unified_learning_v1", counted)
    before = saved_bytes(target.path)
    status, _, body = browser.submit(add_form(browser), source_handle=source_handle(path))
    assert status == 200 and b"Nothing changed" in body
    assert target.last_result.status == "resolution_required" and len(calls) == 1
    assert target.corpus.prepared_artifacts is prepared and saved_bytes(target.path) == before
    form = Forms(body.decode()).find(entry.LEARNING_ADD_ROUTE)
    assert form["values"]["source_handle"] == source_handle(path)
    page = follow(browser, browser.submit(form, same_revision_resolution="retain"))
    assert "keeping the previously selected" in page and len(calls) == 2
    assert target.corpus.prepared_artifacts is None
    assert target.corpus.store.document.catalog.current_matches == old_current


@pytest.mark.parametrize("change", ("reopen", "other", "foreign_token", "reload"))
def test_equal_revision_and_reopened_targets_never_retarget_old_forms(localized_server, change):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    original = localized_server.app_context.managed_stateful.active_learning
    form = add_form(browser)
    if change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/open")))
    elif change == "other":
        create_collection(browser, "Other collection")
    elif change == "reload":
        follow(browser, browser.submit(operation_form(
            browser.page("/learning/current"), "reload_corpus")))
    else:
        form["values"]["learning_selection"] = "f" * 64
    current = localized_server.app_context.managed_stateful.active_learning
    before = saved_bytes(current.path)
    assert browser.submit(form, source_handle=source_handle(path))[0] == 409
    assert saved_bytes(current.path) == before and original.path.exists()


@pytest.mark.parametrize("after_capture", (False, True))
def test_real_deletion_before_and_after_guarded_capture(
    localized_server, monkeypatch, after_capture,
):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    # The real deletion preview refreshes discovery; obtain the Add form afterward.
    deletion = Forms(preview(browser, "matches", source_handle(path))).find(
        "/recordings/delete/apply")
    form = add_form(browser)
    entered, release = Event(), Event()
    real = entry.capture_recorded_match_v1
    def paused(*args):
        captured = real(*args) if after_capture else None
        entered.set()
        assert release.wait(20)
        return captured if after_capture else real(*args)
    monkeypatch.setattr(entry, "capture_recorded_match_v1", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(browser.submit, form, source_handle=source_handle(path))
        try:
            assert entered.wait(20)
            assert browser.submit(deletion, confirm_delete="on")[0] == 303
            assert not path.exists()
        finally:
            release.set()
        assert future.result()[0] == (303 if after_capture else 409)
    target = localized_server.app_context.managed_stateful.active_learning
    assert len(target.corpus.store.match_snapshots) == int(after_capture)
    assert not path.exists()


def test_switch_during_capture_rejects_without_notice_or_write_to_new_target(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    old = localized_server.app_context.managed_stateful.active_learning
    before = saved_bytes(old.path)
    form = add_form(browser)
    entered, release = Event(), Event()
    real = entry.capture_recorded_match_v1
    def paused(*args):
        copy = real(*args)
        entered.set()
        assert release.wait(20)
        return copy
    monkeypatch.setattr(entry, "capture_recorded_match_v1", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(browser.submit, form, source_handle=source_handle(path))
        try:
            assert entered.wait(20)
            create_collection(browser, "Replaced target")
            fresh = localized_server.app_context.managed_stateful.active_learning
        finally:
            release.set()
        assert future.result()[0] == 409
    assert saved_bytes(old.path) == before
    assert fresh.entry_outcome is None and not fresh.corpus.store.match_snapshots
    assert localized_server.app_context.form_feedback.current(
        "learning", active_identity=fresh) is None


def test_two_simultaneous_adds_save_catalog_once(localized_server, monkeypatch):
    from threading import Barrier
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    form = add_form(browser)
    barrier = Barrier(2)
    real = entry.capture_recorded_match_v1
    def paused(*args):
        copy = real(*args)
        barrier.wait(timeout=20)
        return copy
    monkeypatch.setattr(entry, "capture_recorded_match_v1", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(browser.submit, form, source_handle=source_handle(path))
                   for _ in range(2)]
        assert sorted(future.result()[0] for future in futures) == [303, 409]
    target = localized_server.app_context.managed_stateful.active_learning
    assert target.corpus.store.document.catalog.revision == 1
    assert len(load_learning_corpus_directory_v1(target.path).match_snapshots) == 1


def test_target_activation_waits_for_guarded_canonical_import(localized_server, monkeypatch):
    import skatmind.app_web.server as web
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser, "Later target")
    other = localized_server.app_context.managed_stateful.active_learning
    create_collection(browser, "Import target")
    app = localized_server.app_context
    target = app.managed_stateful.active_learning
    opening = next(form for form in Forms(browser.page("/learning")).forms
                   if form["action"] == "/learning/open"
                   and form["values"]["handle"] == other.handle)
    form = add_form(browser)
    entered, release, activating = Event(), Event(), Event()
    real_import = entry.import_workspace_bytes_into_unified_learning_v1
    real_activate = web.SkatMindAppWebRequestHandlerV1._activate_learning
    def blocked(*args, **kwargs):
        assert app.managed_stateful.learning_lifecycle_lock._is_owned()
        assert not app.managed_stateful.match_lifecycle_lock._is_owned()
        assert not app.lock._is_owned() and not app.profile_lock.locked()
        entered.set()
        assert release.wait(20)
        return real_import(*args, **kwargs)
    def activate(handler, active):
        activating.set()
        return real_activate(handler, active)
    monkeypatch.setattr(entry, "import_workspace_bytes_into_unified_learning_v1", blocked)
    monkeypatch.setattr(web.SkatMindAppWebRequestHandlerV1, "_activate_learning", activate)
    with ThreadPoolExecutor(max_workers=2) as pool:
        added = pool.submit(browser.submit, form, source_handle=source_handle(path))
        try:
            assert entered.wait(20)
            opened = pool.submit(browser.submit, opening)
            assert activating.wait(20)
            assert app.managed_stateful.active_learning is target and not opened.done()
        finally:
            release.set()
        assert added.result()[0] in {303, 409}  # Response can lose the publication race.
        assert opened.result()[0] == 303
    assert len(load_learning_corpus_directory_v1(target.path).match_snapshots) == 1
    current = app.managed_stateful.active_learning
    assert current.handle == other.handle and not current.corpus.store.match_snapshots
    assert current.entry_outcome is None


def test_active_saved_file_edit_fails_without_reload_or_report_clear(localized_server):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    active = localized_server.app_context.managed_stateful.active_match
    create_collection(browser)
    form = add_form(browser)
    external_pass(path, workspace)
    assert browser.submit(form, source_handle=source_handle(path))[0] == 409
    assert active.workspace == workspace and active.selected_position == 1


def test_canonical_save_conflict_can_leave_a_real_valid_orphan(localized_server, monkeypatch):
    import skatmind.learning_corpus_import as imports
    from skatmind.learning_corpus_catalog import build_learning_corpus_catalog_v1
    from skatmind.learning_corpus_persistence_codec import (
        build_learning_corpus_catalog_persistence_document_v1,
    )
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    target = localized_server.app_context.managed_stateful.active_learning
    original = target.corpus.store
    competing = build_learning_corpus_catalog_persistence_document_v1(
        build_learning_corpus_catalog_v1(corpus_id=original.document.catalog.corpus_id,
            revision=1, match_snapshots=(), current_matches=()))
    real = imports.save_learning_corpus_catalog_v1
    calls = []
    def conflict(root, document, *, expected_content_fingerprint):
        calls.append(document)
        assert real(root, competing, expected_content_fingerprint=expected_content_fingerprint
                    ).status == "saved"
        return real(root, document, expected_content_fingerprint=expected_content_fingerprint)
    monkeypatch.setattr(imports, "save_learning_corpus_catalog_v1", conflict)
    assert browser.submit(add_form(browser), source_handle=source_handle(path))[0] == 409
    assert len(calls) == 1 and target.corpus.store is original
    disk = load_learning_corpus_directory_v1(target.path)
    assert disk.document == competing and len(disk.orphan_match_snapshot_ids) == 1
    assert not disk.match_snapshots and path.exists()


def test_non_current_report_has_visible_removal_and_explicit_rebuild(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    page = browser.page("/matches/position/3")
    follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                   immediate_sample_count="2"))
    active = localized_server.app_context.managed_stateful.active_match
    report = active.capture.report_store.list()[0]
    assert report.value.status == "executed"
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    target = localized_server.app_context.managed_stateful.active_learning
    from skatmind.app_web.cross_area_transfer import transfer_active_match_report_to_corpus_v1
    result = transfer_active_match_report_to_corpus_v1(active, target,
        report_id=report.report_id,
        match_snapshot_id=target.corpus.store.document.catalog.current_matches[0].match_snapshot_id)
    assert result.status == "applied"
    build(browser)
    page = browser.page("/matches/position/2")
    follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = follow(browser, browser.submit(operation_form(page, "select_current_snapshot")))
    assert target.corpus.prepared_artifacts is None
    assert build_unified_learning_state_v1(target)["strategy_sources"][0]["binding_status"] == (
        "non_current")
    from html.parser import HTMLParser
    class Visibility(HTMLParser):
        closed = 0
        seen = False
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "details" and "open" not in attrs:
                self.closed += 1
            if tag == "input" and attrs.get("value") == "remove_strategy_teacher_report":
                assert self.closed == 0
                self.seen = True
        def handle_endtag(self, tag):
            if tag == "details" and self.closed:
                self.closed -= 1
    visibility = Visibility()
    visibility.feed(page)
    assert visibility.seen
    page = follow(browser, browser.submit(operation_form(page, "remove_strategy_teacher_report")))
    build(browser, page)
    state = build_unified_learning_state_v1(target)
    assert state["prepared"]["strategy_teacher_evidence_count"] == 0


def test_restart_strictly_resumes_copies_but_not_process_local_results(localized_server):
    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.learning_frontend import open_unified_learning_corpus_v1
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    build(browser)
    app = localized_server.app_context
    target = app.managed_stateful.active_learning
    old = add_form(browser)["values"]
    old.pop("_frontend_form_instance")
    old["source_handle"] = source_handle(path)
    restarted = AppWebContextV1.create(app.managed_home)
    discovery = restarted.managed_stateful.refresh("corpora")
    reopened = open_unified_learning_corpus_v1(restarted.managed_stateful.root("corpora"),
                                               discovery.entries[0])
    restarted.managed_stateful.activate_learning(reopened)
    restarted.managed_stateful.refresh("matches")
    before = saved_bytes(target.path)
    assert reopened.corpus.store == target.corpus.store
    assert reopened.corpus.prepared_artifacts is None
    with pytest.raises(entry.LearningEntryConflict):
        entry.add_recorded_match_v1(restarted, reopened, old)
    assert saved_bytes(target.path) == before


@pytest.mark.parametrize("kind", ("symlink", "hardlink", "directory", "oversize", "junction"))
def test_actual_file_boundaries_fail_before_import(localized_server, monkeypatch, kind):
    import os
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    form = add_form(browser)
    original = path.read_bytes()
    external = path.parent.parent / "synthetic-external.json"
    external.write_bytes(original)
    if kind == "symlink":
        link = path.parent / "probe.json"
        try:
            link.symlink_to(external)
        except OSError as error:
            pytest.skip(f"Actual symlink creation unavailable: {error.errno}")
        path.unlink()
        link.rename(path)
    elif kind == "hardlink":
        path.unlink()
        os.link(external, path)
    elif kind == "directory":
        path.unlink()
        path.mkdir()
    elif kind == "junction":
        if os.name != "nt":
            pytest.skip("Windows junction fixture")
        import _winapi
        path.unlink()
        _winapi.CreateJunction(str(external.parent), str(path))
        assert path.is_junction()
    else:
        # Real oversized regular file, not a relaxed loader eligibility fixture.
        from skatmind.app_web.managed_item_contracts import MANAGED_ITEM_MAX_IMPORT_BYTES
        path.write_bytes(b" " * (MANAGED_ITEM_MAX_IMPORT_BYTES + 1))
    monkeypatch.setattr(entry, "import_workspace_bytes_into_unified_learning_v1",
                        lambda *a, **k: pytest.fail("Unsafe source entered Corpus"))
    assert browser.submit(form, source_handle=source_handle(path))[0] == 409
    assert external.read_bytes() == original


def test_edit_during_strict_load_is_rejected_and_reads_hold_no_global_lock(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    form = add_form(browser)
    app = localized_server.app_context
    real = entry.load_match_workspace_file_v1
    def changed(source_path):
        assert not app.lock._is_owned() and not app.profile_lock.locked()
        assert app.managed_stateful.match_lifecycle_lock._is_owned()
        loaded = real(source_path)
        external_pass(path, workspace)
        return loaded
    monkeypatch.setattr(entry, "load_match_workspace_file_v1", changed)
    assert browser.submit(form, source_handle=source_handle(path))[0] == 409
    assert not app.managed_stateful.active_learning.corpus.store.match_snapshots


def test_discovery_invalid_duplicates_same_titles_and_limit_are_visible(
    localized_server, monkeypatch,
):
    from test_learning_direct_entry_web import independent_workspace

    import skatmind.app_web.managed_item_discovery as discovery_module
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    other = path.with_name("other.json")
    assert save_match_workspace_file_v1(other, build_match_workspace_persistence_document_v1(
        independent_workspace(workspace, "same-title")),
        expected_content_fingerprint=None).status == "saved"
    path.with_name("invalid.json").write_bytes(b"{}")
    create_collection(browser)
    page = browser.page("/learning/current")
    assert source_handle(path) in page and source_handle(other) in page
    assert "It cannot be added" in page
    path.with_name("duplicate.json").write_bytes(path.read_bytes())
    page = follow(browser, browser.request("GET", entry.LEARNING_REFRESH_ROUTE))
    assert "manual" in page.lower() or "resolution" in page.lower()
    assert f'value="{source_handle(path)}"' not in page
    monkeypatch.setattr(discovery_module, "MANAGED_ITEM_MAX_CANDIDATES", 1)
    page = follow(browser, browser.request("GET", entry.LEARNING_REFRESH_ROUTE))
    assert "truncated" in page
