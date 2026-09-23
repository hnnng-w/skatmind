"""Exact returned-form operations over canonical disposable equal-revision sources."""

from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_learning_direct_entry_web import (
    add_form,
    build,
    create_collection,
    downloads,
    saved_bytes,
    source_handle,
)
from test_learning_version_presentation import selections
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_review_navigation import external_pass, saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.learning_frontend import build_unified_learning_state_v1
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1
from skatmind.match_workspace_contracts import _build_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def save_variant(path, previous, variant):
    """Controlled external write of valid content, not a forged fingerprint or UI edit."""
    changed = _build_match_workspace_v1(match_definition=replace(previous.match_definition,
        external_match_id=f"synthetic-variant-{variant}"), revision=previous.revision,
        slots=previous.slots)
    document = build_match_workspace_persistence_document_v1(changed)
    assert save_match_workspace_file_v1(path, document,
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(previous)
            .content_fingerprint).status == "saved"
    return changed


def exact_selection(page, snapshot_id):
    return next(f for f in selections(page) if f["values"]["match_snapshot_id"] == snapshot_id)


def test_real_equal_revision_variants_select_both_reopen_and_noop(localized_server):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    active = localized_server.app_context.managed_stateful.active_learning
    assert not selections(page) and "Choose a different saved version" not in page
    first = active.corpus.store.document.catalog.current_matches[0].match_snapshot_id
    page = build(browser, page)
    prepared = active.corpus.prepared_artifacts
    retained, files = downloads(browser), saved_bytes(active.path)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    assert active.last_result.status == "unchanged"
    assert active.last_result.state["relation"] == "duplicate_snapshot"
    assert active.corpus.prepared_artifacts is prepared and downloads(browser) == retained
    assert saved_bytes(active.path) == files
    changed = save_variant(path, workspace, 2)
    assert changed.match_definition.title == workspace.match_definition.title
    response = browser.submit(add_form(browser), source_handle=source_handle(path))
    assert response[0] == 200 and active.last_result.status == "resolution_required"
    assert active.last_result.state["relation"] == "same_revision_content_conflict"
    assert saved_bytes(active.path) == files and active.corpus.prepared_artifacts is prepared
    page = response[2].decode()
    assert "This version was not added" in page and 'autofocus' in page
    page = switch(browser, page, "de")
    form = Forms(page).find("/learning/add-recorded-match")
    assert form["values"]["source_handle"] == source_handle(path)
    assert form["values"]["same_revision_resolution"] == "reject"
    page = follow(browser, browser.submit(form, same_revision_resolution="retain"))
    second = active.entry_outcome.snapshot_id
    assert second != first and active.corpus.prepared_artifacts is None
    assert active.corpus.store.document.catalog.current_matches[0].match_snapshot_id == first
    page = switch(browser, page, "en")
    # Mapping is captured Catalog order, independently of the display helper.
    state = build_unified_learning_state_v1(active)
    for index, snapshot in enumerate(state["matches"][0]["snapshots"], 1):
        assert snapshot["workspace_revision"] == 1
        assert snapshot["observed_game_count"] == 1 and snapshot["decision_count"] == 6
        expected = f"Saved recording revision 1 — variant {index}"
        if not snapshot["current"]:
            form = exact_selection(page, snapshot["match_snapshot_id"])
            assert form["values"]["match_id"] == workspace.match_definition.match_id
        assert expected in page
    select_second = exact_selection(page, second)
    response = browser.submit(select_second)
    assert response[1]["location"] == "/learning/current"
    page = follow(browser, response)
    assert active.corpus.prepared_artifacts is None
    page = build(browser, page)
    assert build_unified_learning_state_v1(active)["prepared"]["cross_game_match_count"] == 1
    prepared = active.corpus.prepared_artifacts
    retained, files = downloads(browser), saved_bytes(active.path)
    # Replay the genuine emitted form with today's explicit guard: backend no-op,
    # not a newly invented normal singleton/Current control.
    current_form = operation_form(page, "select_current_snapshot")
    revision = current_form["values"]["expected_catalog_revision"]
    response = browser.submit(select_second, expected_catalog_revision=revision)
    assert response[0] == 303 and active.last_result.status == "unchanged"
    assert active.corpus.prepared_artifacts is prepared and downloads(browser) == retained
    assert saved_bytes(active.path) == files
    page = follow(browser, response)
    response = browser.submit(exact_selection(page, first))
    page = follow(browser, response)
    assert active.corpus.prepared_artifacts is None
    page = build(browser, page)
    retained = downloads(browser)
    store = load_learning_corpus_directory_v1(active.path)
    assert store.document.catalog.current_matches[0].match_snapshot_id == first
    page = follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/open")))
    reopened = localized_server.app_context.managed_stateful.active_learning
    assert reopened is not active and reopened.corpus.store.document == store.document
    assert reopened.corpus.prepared_artifacts is None
    build(browser, page)
    assert downloads(browser) == retained
    # A third distinct same-revision variant remains a supported explicit retention.
    save_variant(path, changed, 3)
    response = browser.submit(add_form(browser), source_handle=source_handle(path))
    assert response[0] == 200 and reopened.last_result.status == "resolution_required"
    form = Forms(response[2].decode()).find("/learning/add-recorded-match")
    page = follow(browser, browser.submit(form, same_revision_resolution="retain"))
    assert len(reopened.corpus.store.match_snapshots) == 3
    assert reopened.corpus.store.document.catalog.current_matches[0].match_snapshot_id == first
    assert reopened.corpus.prepared_artifacts is None
    assert len(selections(page)) == 2
    assert all(f"Saved recording revision 1 — variant {i}" in page for i in (1, 2, 3))


@pytest.mark.parametrize("fault", ("foreign", "malformed", "stale", "extra"))
def test_rejected_alternative_never_substitutes_current_and_keeps_recovery(localized_server, fault):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    active = localized_server.app_context.managed_stateful.active_learning
    external_pass(path, workspace)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = build(browser, page)
    form = operation_form(page, "select_current_snapshot")
    override = {"foreign": {"match_id": "other-match"},
                "malformed": {"match_snapshot_id": "invalid"},
                "stale": {"expected_catalog_revision": "0"}, "extra": {"extra": "invalid"}}[fault]
    before, retained = saved_bytes(active.path), downloads(browser)
    prepared = active.corpus.prepared_artifacts
    response = browser.submit(form, **override)
    assert response[0] == (409 if fault == "stale" else 400)
    page = response[2].decode()
    assert 'autofocus' in page and 'role="alert"' in page
    assert "data-operation-feedback" not in page
    assert saved_bytes(active.path) == before and downloads(browser) == retained
    assert active.corpus.prepared_artifacts is prepared
    page = switch(browser, page, "de")
    returned = operation_form(page, "select_current_snapshot")
    assert returned["values"]["match_snapshot_id"] == form["values"]["match_snapshot_id"]
    current = active.corpus.store.document.catalog.current_matches[0]
    assert returned["values"]["match_snapshot_id"] != current.match_snapshot_id
    tree = Hierarchy(page)
    assert any(n["tag"] == "details" and "open" in n["attrs"] for n in tree.nodes)
    response = browser.submit(returned)
    assert response[0] == 303 and active.corpus.prepared_artifacts is None
