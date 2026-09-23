"""Literal native return contracts over real disposable Corpus operations."""

import hashlib
from collections import Counter
from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_learning_direct_entry_web import (
    add_form,
    create_collection,
    downloads,
    independent_workspace,
    saved_bytes,
    source_handle,
)
from test_match_recording_recovery_web import follow, operation_form
from test_operation_feedback_web import notice, notices
from test_recorded_review_navigation import external_pass, saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.learning_frontend as learning
import skatmind.learning_corpus_import as corpus_import
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_workspace_contracts import _build_match_workspace_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def match_target(active, match_id):
    identity = f"learning-match-v1:{active.handle}:{match_id}".encode()
    return "learning-match-" + hashlib.sha256(identity).hexdigest()


def node(page, identity):
    rows = [n for n in Hierarchy(page).nodes if n["attrs"].get("id") == identity]
    assert len(rows) == 1
    assert Hierarchy.visible(rows[0])
    return rows[0]


def test_first_add_returns_to_accepted_match_not_source_selector(localized_server):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    response = browser.submit(add_form(browser), source_handle=source_handle(path))
    target = match_target(active, workspace.match_definition.match_id)
    assert response[0] == 303
    assert response[1]["location"] == "/learning/current#" + target
    page = follow(browser, response)
    row = node(page, target)
    assert row["attrs"]["tabindex"] == "-1" and "autofocus" not in row["attrs"]
    assert "Version used for evaluation" in row["text"]
    assert any(p["attrs"].get("id") == target for p in notice(page, "version_added")["parents"])


def test_preparation_returns_to_existing_results_and_owns_receipt(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[0] == 303
    assert response[1]["location"] == "/learning/current#learning-results"
    page = follow(browser, response)
    row = node(page, "learning-results")
    assert row["attrs"]["tabindex"] == "-1" and "autofocus" not in row["attrs"]
    assert any(p["attrs"].get("id") == "learning-results"
               for p in notice(page, "prepared")["parents"])


def affected(page, active):
    outcome = active.entry_outcome
    row = node(page, match_target(active, outcome.match_id))
    match = next(m for m in learning.build_unified_learning_state_v1(active)["matches"]
                 if m["match_id"] == outcome.match_id)
    number = next(n for n, s in enumerate(match["snapshots"], 1)
                  if s["match_snapshot_id"] == outcome.snapshot_id)
    selected_number = next(n for n, s in enumerate(match["snapshots"], 1) if s["current"])
    assert text("en", "task.learning.affected_version", number=number,
                revision=outcome.copied_revision, selected_number=selected_number) in row["text"]
    current = next(s for s in match["snapshots"] if s["current"])
    assert text("en", "task.learning.saved_revision",
                revision=current["workspace_revision"]) in row["text"]
    return row


def test_multiple_equal_titles_affected_not_current_and_exact_passive_exports(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    other = independent_workspace(workspace, "second-same-title")
    assert other.match_definition.title == workspace.match_definition.title
    other_path = path.with_name("other.json")
    assert save_match_workspace_file_v1(other_path,
        build_match_workspace_persistence_document_v1(other),
        expected_content_fingerprint=None).status == "saved"
    calls = Counter()
    def count(name, real):
        def wrapped(*args, **kwargs):
            calls[name] += 1
            return real(*args, **kwargs)
        return wrapped
    for module, function, key in (
        (learning, "import_match_workspace_into_learning_corpus_web_v1", "imports"),
        (learning, "prepare_learning_corpus_artifacts_web_v1", "preparations"),
        (learning, "select_current_learning_corpus_snapshot_web_v1", "selections"),
        (corpus_import, "save_learning_corpus_catalog_v1", "catalog_saves"),
    ):
        monkeypatch.setattr(module, function, count(key, getattr(module, function)))
    create_collection(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    for source in (path, other_path):
        response = browser.submit(add_form(browser), source_handle=source_handle(source))
        assert response[0] == 303
        assert response[1]["location"] == "/learning/current#" + match_target(
            active, active.entry_outcome.match_id)
        page = follow(browser, response)
        affected(page, active)
    target = match_target(active, other.match_definition.match_id)
    assert page.index('id="' + target) > page.index('id="' + match_target(
        active, workspace.match_definition.match_id))
    ids = [n["attrs"]["id"] for n in Hierarchy(page).nodes if "id" in n["attrs"]]
    assert len(ids) == len(set(ids))
    current = active.corpus.store.document.catalog.current_matches
    page = follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))
    retained, files = downloads(browser), saved_bytes(active.path)
    prepared = active.corpus.prepared_artifacts
    page = follow(browser, browser.submit(add_form(browser),
                                         source_handle=source_handle(other_path)))
    row = affected(page, active)
    assert "identical content" in row["text"] and not notices(page)
    assert active.corpus.prepared_artifacts is prepared
    assert downloads(browser) == retained and saved_bytes(active.path) == files
    before = calls.copy()
    for _ in range(2):
        assert not notices(browser.page("/learning/current#" + target))
    page = switch(browser, page, "de")
    page = switch(browser, page, "en")
    assert not notices(page) and calls == before and downloads(browser) == retained
    external_pass(other_path, other)
    response = browser.submit(add_form(browser), source_handle=source_handle(other_path))
    assert response[1]["location"] == "/learning/current#" + target
    page = follow(browser, response)
    row = affected(page, active)
    assert "keeping the previously selected" in row["text"] and not notices(page)
    assert active.corpus.store.document.catalog.current_matches == current
    assert active.entry_outcome.snapshot_id not in {s.match_snapshot_id for s in current}
    assert active.corpus.prepared_artifacts is None
    response = browser.submit(operation_form(page, "select_current_snapshot"))
    assert response[1]["location"] == "/learning/current"
    page = follow(browser, response)
    assert active.corpus.store.document.catalog.current_matches != current
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[1]["location"] == "/learning/current#learning-results"
    follow(browser, response)
    downloads(browser)
    assert calls == Counter(imports=4, preparations=2, selections=1, catalog_saves=4)


def test_same_revision_variants_use_exact_snapshot_not_revision(localized_server):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    active = localized_server.app_context.managed_stateful.active_learning
    first = active.entry_outcome.snapshot_id
    altered = _build_match_workspace_v1(match_definition=replace(workspace.match_definition,
        title="Different synthetic content"), revision=workspace.revision, slots=workspace.slots)
    assert save_match_workspace_file_v1(
        path, build_match_workspace_persistence_document_v1(altered),
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(workspace)
            .content_fingerprint).status == "saved"
    response = browser.submit(add_form(browser), source_handle=source_handle(path))
    assert response[0] == 200 and "location" not in response[1]
    page = response[2].decode()
    assert 'autofocus' in page and not notices(page)
    assert "Nothing changed" in node(page, "learning-recorded-matches")["text"]
    response = browser.submit(Forms(page).find("/learning/add-recorded-match"),
                              same_revision_resolution="retain")
    assert response[0] == 303
    page = follow(browser, response)
    row = affected(page, active)
    assert "keeping the previously selected" in row["text"]
    assert active.entry_outcome.snapshot_id != first
    assert active.entry_outcome.copied_revision == workspace.revision
    versions = [n for n in Hierarchy(page).nodes
                if n["attrs"].get("id", "").startswith("learning-version-")]
    assert len(versions) == 2 and versions[0]["attrs"]["id"] != versions[1]["attrs"]["id"]


@pytest.mark.parametrize("operation", ("add", "prepare"))
@pytest.mark.parametrize("expire", (False, True))
def test_receipt_delivery_is_separate_from_content_lifetime(localized_server, operation, expire):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    response = browser.submit(add_form(browser), source_handle=source_handle(path))
    active = localized_server.app_context.managed_stateful.active_learning
    if operation == "prepare":
        page = follow(browser, response)
        response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    receipt = active.operation_feedback.pending
    state = learning.build_unified_learning_state_v1(active)
    render_task_first_learning_v1(state, managed_handle=active.handle,
                                 entry_outcome=active.entry_outcome if operation == "add" else None)
    for route in ("/assets/app.css", "/assets/workflow.js", "/"):
        browser.request("GET", route)
    browser.request("HEAD", "/learning/current")
    if operation == "prepare":
        retained = downloads(browser)
    assert active.operation_feedback.pending is receipt
    if expire:
        # Controlled receipt deadline only; Product computation and persistence were real.
        active.operation_feedback.pending = replace(receipt, expires_at=0)
    page = follow(browser, response)
    assert len(notices(page)) == (0 if expire else 1)
    target = response[1]["location"].split("#")[1]
    node(page, target)
    page = browser.page("/learning/current")
    assert not notices(page)
    node(page, target)
    if operation == "prepare":
        assert downloads(browser) == retained


@pytest.mark.parametrize("operation", ("add", "prepare"))
@pytest.mark.parametrize("change", ("other_collection", "reload", "prepare"))
def test_post_to_get_supersession_never_replays_add_or_attributes_old_notice(
    localized_server, change, operation,
):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    form = add_form(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    response = browser.submit(form, source_handle=source_handle(path))
    if operation == "prepare":
        page = follow(browser, response)
        response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    old_target = response[1]["location"].split("#")[1]
    if change == "other_collection":
        create_collection(browser, "Other collection")
    elif change == "reload":
        # Existing real operation at the bounded interval before redirect GET.
        learning.reload_unified_learning_corpus_v1(active)
    else:
        learning.prepare_unified_learning_artifacts_v1(active, dataset_id="superseding",
            known_player_seed=0, unseen_player_seed=0, train_weight=70,
            validation_weight=15, test_weight=15)
    current = localized_server.app_context.managed_stateful.active_learning
    before = saved_bytes(current.path)
    page = follow(browser, response)
    assert text("en", "feedback.version_added") not in page
    if change == "other_collection":
        assert not current.corpus.store.match_snapshots
        assert text("en", "feedback.prepared") not in page
        if operation == "add":
            assert 'id="' + old_target + '"' not in page
    else:
        node(page, old_target)
        assert text("en", "task.learning.affected_version", number=1,
                    revision=active.entry_outcome.copied_revision, selected_number=1) not in page
    if change == "prepare":
        row = notice(page, "prepared")
        assert any(p["attrs"].get("id") == "learning-results" for p in row["parents"])
    assert saved_bytes(current.path) == before


def test_failed_recreation_keeps_older_bytes_but_error_has_priority(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))
    retained = downloads(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    prepared = active.corpus.prepared_artifacts
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"), train_weight="0")
    assert response[0] == 400 and "location" not in response[1]
    page = response[2].decode()
    assert 'role="alert"' in page and 'autofocus' in page and not notices(page)
    assert page.index('class="error-summary"') < page.index('id="learning-results"')
    assert active.corpus.prepared_artifacts is prepared and downloads(browser) == retained
    assert Forms(page).forms  # Safe invalid value is still in its actual preparation form.
    assert operation_form(page, "prepare_learning_artifacts")["values"]["train_weight"] == "0"


@pytest.mark.parametrize("empty", (False, True))
def test_successful_limited_and_empty_results_keep_qualifications_before_counts(
    localized_server, empty,
):
    from skatmind.match_workspace_contracts import create_match_workspace_v1

    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    if empty:
        assert save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(
            create_match_workspace_v1(workspace.match_definition)),
            expected_content_fingerprint=build_match_workspace_persistence_document_v1(workspace)
                .content_fingerprint).status == "saved"
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[1]["location"] == "/learning/current#learning-results"
    page = follow(browser, response)
    result = node(page, "learning-results")
    status = text("en", "task.learning.dataset." + ("empty" if empty else "partial"))
    assert status in result["text"]
    assert page.index(status) < page.index('<dt>Matches</dt>')
    assert page.count('data-operation-feedback ') == 1
    downloads(browser)
