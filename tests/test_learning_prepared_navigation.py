"""Exact HTTP prepared-result views over genuine disposable collection preparations."""

import json
import re
from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_view_continuity import return_data
from test_learning_direct_entry_web import (
    add_form,
    create_collection,
    downloads,
    saved_bytes,
    source_handle,
)
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_review_navigation import external_pass, saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch

import skatmind.app_web.learning_frontend as learning
import skatmind.app_web.server as web
from skatmind.app_web.debrief_frontend import DebriefScopeV1, collection_scope
from skatmind.app_web.frontend_profile_operations import is_safe_frontend_return_path_v1
from skatmind.corpus_web import downloads as artifact_downloads


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def prepared(browser):
    path, workspace = saved_partial_match(browser.server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[0] == 303
    return response, path, workspace


def view_link(page):
    links = [n["attrs"]["href"] for n in Hierarchy(page).nodes
             if n["tag"] == "a" and n["text"] == "View prepared datasets"]
    assert len(links) == 1
    assert re.fullmatch(r"/learning/prepared/[0-9a-f]{64}", links[0])
    return links[0]


def result_node(page, *, visible=True, autofocus=True):
    rows = [n for n in Hierarchy(page).nodes if n["attrs"].get("id") == "learning-results"]
    assert len(rows) == 1
    row = rows[0]
    assert row["tag"] == "h2"
    assert Hierarchy.visible(row) is visible
    assert ("autofocus" in row["attrs"]) is autofocus
    assert row["attrs"]["tabindex"] == "-1"
    assert "Prepared datasets" in row["text"]
    assert "Recreate dataset preparation" not in row["text"]
    assert any(p["tag"] == "details" for p in row["parents"])
    return row


def test_delivered_view_and_preparation_share_exact_native_result_destination(localized_server):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    page = follow(browser, response)
    destination = view_link(page)
    assert response[1]["location"] == destination
    result_node(page)
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == destination
    for _ in range(2):
        page = browser.page(view_link(page))
        result_node(page)
        assert "data-operation-feedback " not in page
    ordinary = browser.page("/learning/current")
    assert view_link(ordinary) == destination
    result_node(ordinary, visible=False, autofocus=False)


def test_passive_views_retain_exact_objects_files_and_all_downloads(localized_server, monkeypatch):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    page = follow(browser, response)
    active = localized_server.app_context.managed_stateful.active_learning
    retained = downloads(browser)
    files = saved_bytes(localized_server.app_context.managed_home.root)
    references = (active.corpus.store, active.corpus.prepared_artifacts,
                  active.corpus.tactical_prepared_artifacts,
                  active.corpus.tactical_coaching_prepared_artifacts, active.last_result)
    revisions = (active.corpus.generation, active.corpus.strategy_source_store.revision,
                 active.debrief_sources.revision)
    def forbidden(*args, **kwargs):
        pytest.fail("Passive result navigation executed an operation or serialized a download")
    with monkeypatch.context() as guard:
        for name in ("prepare_learning_corpus_artifacts_web_v1",
                     "import_match_workspace_into_learning_corpus_web_v1",
                     "select_current_learning_corpus_snapshot_web_v1",
                     "reload_unified_learning_corpus_v1"):
            guard.setattr(learning, name, forbidden)
        guard.setattr(web, "reload_unified_learning_corpus_v1", forbidden)
        guard.setattr(artifact_downloads, "_download_value", forbidden)
        for _ in range(3):
            page = browser.page(view_link(page))
            result_node(page)
            assert "data-operation-feedback " not in page
        ordinary = browser.page("/learning/current")
        assert view_link(ordinary) == view_link(page)
    assert files == saved_bytes(localized_server.app_context.managed_home.root)
    assert all(old is new for old, new in zip(references, (
        active.corpus.store, active.corpus.prepared_artifacts,
        active.corpus.tactical_prepared_artifacts,
        active.corpus.tactical_coaching_prepared_artifacts, active.last_result), strict=True))
    assert revisions == (active.corpus.generation, active.corpus.strategy_source_store.revision,
                         active.debrief_sources.revision)
    assert downloads(browser) == retained


def test_missing_result_and_match_owned_scopes_are_not_prepared_views(localized_server):
    browser = Browser(localized_server)
    create_collection(browser)
    app = localized_server.app_context
    scope = collection_scope(app, app.managed_stateful.active_learning)
    assert browser.request("GET", f"/learning/prepared/{scope.scope_id}")[0] == 409
    direct = DebriefScopeV1("a" * 64, (), ())
    app.managed_stateful.debrief_scopes[direct.scope_id] = direct
    assert browser.request("GET", f"/learning/prepared/{direct.scope_id}")[0] == 409
    assert "View prepared datasets" not in browser.page("/learning/current")


def test_actual_bounded_scope_eviction_expires_the_prepared_link(localized_server):
    from skatmind.app_web.debrief_frontend import _retain
    from skatmind.match_analysis_contracts import MATCH_ANALYSIS_REPORT_STORE_LIMIT

    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    app = localized_server.app_context
    for number in range(MATCH_ANALYSIS_REPORT_STORE_LIMIT):
        _retain(app, DebriefScopeV1(f"{number:064x}", (), (), lineage=(number,)))
    assert len(app.managed_stateful.debrief_scopes) == MATCH_ANALYSIS_REPORT_STORE_LIMIT
    assert browser.request("GET", response[1]["location"])[0] == 409
    assert app.managed_stateful.active_learning.corpus.prepared_artifacts is not None


@pytest.mark.parametrize("tail", ("", "g" * 64, "a" * 63, "A" * 64,
    "a" * 64 + "/", "a" * 64 + "/inputs", "a" * 64 + "/result.json"))
def test_only_exact_prepared_path_is_dispatched_and_allowed(localized_server, tail):
    browser = Browser(localized_server)
    route = "/learning/prepared/" + tail
    assert not is_safe_frontend_return_path_v1(route)
    assert browser.request("GET", route)[0] == 404


def test_unknown_scope_and_existing_authorization_are_preserved(localized_server):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    route = response[1]["location"]
    assert browser.request("GET", "/learning/prepared/" + "f" * 64)[0] == 409
    assert browser.request("GET", route, headers={"Cookie": ""})[0] == 403
    assert browser.request("GET", route, headers={"Host": "example.com"})[0] == 403
    assert browser.request("GET", route + "?open=1")[0] == 403
    page = follow(browser, response)
    language = Forms(page).find("/actions/profile/language")
    for invalid in (route + "?x=1", route + "#learning-results", "https://example.com" + route,
                    route + "/inputs", route + "?", route + "#"):
        assert not is_safe_frontend_return_path_v1(invalid)
        assert browser.submit(language, language="de", return_to=invalid)[0] == 400
    assert browser.request("POST", language["action"], {**language["values"], "language": "de"},
                           headers={"Origin": "null"})[0] == 403


def invalidate(browser, active, change):
    app = browser.server.app_context
    if change == "switch":
        create_collection(browser, "Other collection")
    elif change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/open")))
    elif change == "reload":
        learning.reload_unified_learning_corpus_v1(active)
    elif change == "generation":
        active.corpus.generation += 1
    elif change == "source_revision":
        active.corpus.strategy_source_store.revision += 1
    elif change == "evict":
        # Exact bounded eviction is exercised separately; this removes the same lookup entry.
        app.managed_stateful.debrief_scopes.clear()
    elif change in {"prepared", "tactical", "coaching"}:
        name = {"prepared": "prepared_artifacts", "tactical": "tactical_prepared_artifacts",
                "coaching": "tactical_coaching_prepared_artifacts"}[change]
        setattr(active.corpus, name, None)
    elif change in {"_prepared_store", "_prepared_generation", "_prepared_source_revision"}:
        setattr(active.corpus, change, None)
    elif change == "catalog_file":
        (active.path / "catalog.json").write_bytes(b"{}")
    elif change == "snapshot_file":
        next((active.path / "objects").rglob("*.json")).write_bytes(b"{}")
    elif change == "last_result":
        active.last_result = replace(active.last_result)
    elif change == "discovery":
        app.managed_stateful.generations["matches"] += 1
    elif change == "feedback":
        form = operation_form(browser.page("/learning/current"), "prepare_learning_artifacts")
        browser.submit(form, train_weight="0")
    else:
        raise AssertionError(change)


@pytest.mark.parametrize("change", ("switch", "reopen", "reload", "generation", "source_revision",
    "evict", "prepared", "tactical", "coaching", "_prepared_store", "_prepared_generation",
    "_prepared_source_revision", "catalog_file", "snapshot_file"))
def test_stale_prepared_get_never_substitutes_or_repairs(localized_server, change):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    app = localized_server.app_context
    active = app.managed_stateful.active_learning
    invalidate(browser, active, change)
    before = saved_bytes(app.managed_home.root)
    status, _, body = browser.request("GET", response[1]["location"])
    assert status == 409
    assert b'id="learning-prepared-result"' not in body
    assert b"data-operation-feedback " not in body
    assert saved_bytes(app.managed_home.root) == before


@pytest.mark.parametrize("change", ("switch", "_prepared_generation", "snapshot_file"))
def test_revalidate_after_render_before_html_delivery(localized_server, monkeypatch, change):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    real = web.render_task_first_learning_v1
    def render(*args, **kwargs):
        content = real(*args, **kwargs)
        if change == "switch":
            localized_server.app_context.managed_stateful.active_learning = None
        else:
            invalidate(browser, active, change)
        return content
    monkeypatch.setattr(web, "render_task_first_learning_v1", render)
    status, _, body = browser.request("GET", response[1]["location"])
    assert status == 409 and b'id="learning-prepared-result"' not in body
    assert b"data-operation-feedback " not in body


@pytest.mark.parametrize("enhanced", (False, True))
@pytest.mark.parametrize("closed", (False, True))
def test_language_return_keeps_route_and_never_reissues_result_focus(
    localized_server, enhanced, closed,
):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    page = follow(browser, response)
    route = view_link(page)
    if enhanced:
        details = [n for n in Hierarchy(page).nodes if n["tag"] == "details"]
        values = {"forms": [], "disclosures": ["open" in n["attrs"] for n in details],
                  "view": {"anchor": "id:learning-results" if not closed else "top",
                           "offset": 0, "x": 0, "focus": "de"}}
        if closed:
            values["disclosures"] = [False] * len(details)
        response = enhanced_switch(browser, page, json.dumps(values), "de")
    else:
        response = browser.submit(Forms(page).find("/actions/profile/language"), language="de")
    assert response[0] == 303
    assert response[1]["location"].split("?", 1)[0] == route
    returned = follow(browser, response)
    assert return_data(returned) is not None
    assert 'lang="de"' in returned and "autofocus" not in returned
    result = next(n for n in Hierarchy(returned).nodes
                  if n["attrs"].get("id") == "learning-results")
    assert Hierarchy.visible(result) is (not enhanced or not closed)
    assert Forms(returned).find("/actions/profile/language")["values"]["return_to"] == route
    if enhanced:
        assert return_data(returned)["view"] == values["view"]


@pytest.mark.parametrize("enhanced", (False, True))
@pytest.mark.parametrize("stage", ("submission", "return"))
@pytest.mark.parametrize("change", ("switch", "reopen", "_prepared_generation", "prepared",
    "last_result", "discovery", "feedback", "catalog_file", "snapshot_file", "evict"))
def test_language_binding_rejects_stale_full_learning_sources(
    localized_server, stage, change, enhanced,
):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    page = follow(browser, response)
    language = Forms(page).find("/actions/profile/language")
    values = ({"_frontend_language_values": json.dumps({"forms": [],
        "disclosures": [False] * len(re.findall(r"<details\b", page)),
        "view": {"anchor": "top", "offset": 0, "x": 0, "focus": "de"}})}
        if enhanced else {})
    active = localized_server.app_context.managed_stateful.active_learning
    if stage == "return":
        response = browser.submit(language, language="de", **values)
        assert response[0] == 303
    invalidate(browser, active, change)
    profile = localized_server.app_context.frontend_profile
    result = (browser.submit(language, language="de", **values) if stage == "submission" else
              browser.request("GET", response[1]["location"]))
    assert result[0] == 409
    assert b'id="learning-prepared-result"' not in result[2]
    assert return_data(result[2].decode()) is None
    assert localized_server.app_context.frontend_profile is profile


def test_retained_error_wins_even_on_200_explicit_get(localized_server):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    page = follow(browser, response)
    route = view_link(page)
    retained = downloads(browser)
    rejected = browser.submit(operation_form(page, "prepare_learning_artifacts"), train_weight="0")
    assert rejected[0] == 400 and "location" not in rejected[1]
    page = browser.page(route)
    result_node(page, autofocus=False)
    autofocus = [n for n in Hierarchy(page).nodes if "autofocus" in n["attrs"]]
    assert len(autofocus) == 1 and autofocus[0]["attrs"]["class"] == "error-summary"
    assert "data-operation-feedback " not in page
    assert operation_form(page, "prepare_learning_artifacts")["values"]["train_weight"] == "0"
    assert downloads(browser) == retained


def test_rejected_current_preparation_does_not_redirect_to_older_success(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    response, _, _ = prepared(browser)
    page = follow(browser, response)
    active = localized_server.app_context.managed_stateful.active_learning
    old_result = active.last_result
    old_artifact = active.corpus.prepared_artifacts
    retained = downloads(browser)
    # Controlled current invocation rejection at the Application return boundary;
    # leave the genuine prior result and bundle in place to expose stale-result routing.
    rejected = replace(old_result, status="source_changed", http_status=409)
    monkeypatch.setattr(web, "prepare_unified_learning_artifacts_v1", lambda *a, **kw: rejected)
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[0] == 409 and "location" not in response[1]
    assert b'class="error-summary"' in response[2]
    assert b"data-operation-feedback " not in response[2]
    assert active.last_result is old_result and active.corpus.prepared_artifacts is old_artifact
    assert downloads(browser) == retained


@pytest.mark.parametrize("stage", ("submission", "return"))
def test_full_learning_language_binding_includes_active_match_reports(localized_server, stage):
    from test_match_rollout_web import open_alex

    browser, path, _ = open_alex(localized_server, count=30)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))
    form = Forms(page).find("/actions/profile/language")
    if stage == "return":
        response = browser.submit(form, language="de")
        assert response[0] == 303
    app = localized_server.app_context
    match = app.managed_stateful.active_match
    match.capture.report_store.clear()
    profile = app.frontend_profile
    result = (browser.submit(form, language="de") if stage == "submission" else
              browser.request("GET", response[1]["location"]))
    assert result[0] == 409 and b'id="learning-prepared-result"' not in result[2]
    assert app.frontend_profile is profile


def test_actual_version_selection_expires_old_prepared_destination(localized_server):
    browser = Browser(localized_server)
    response, path, workspace = prepared(browser)
    old_route = response[1]["location"]
    follow(browser, response)
    external_pass(path, workspace)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = follow(browser, browser.submit(operation_form(page, "select_current_snapshot")))
    app = localized_server.app_context
    active = app.managed_stateful.active_learning
    assert active.corpus.prepared_artifacts is None
    before = saved_bytes(app.managed_home.root)
    assert browser.request("GET", old_route)[0] == 409
    assert saved_bytes(app.managed_home.root) == before
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    new_page = follow(browser, response)
    assert view_link(new_page) == response[1]["location"] != old_route
    result_node(new_page)
