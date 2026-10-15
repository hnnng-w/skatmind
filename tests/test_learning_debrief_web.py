"""Native direct/collection flow through the real authenticated server."""

import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from threading import Event

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_learning_direct_entry_web import add_form, create_collection, saved_bytes, source_handle
from test_match_recording_recovery_web import follow, operation_form
from test_match_rollout_web import form, open_alex
from test_recorded_review_navigation import external_pass
from test_session_recorded_review_web import Forms

import skatmind.app_web.match_rollout_frontend as rollout
from skatmind.app_web.debrief_frontend import collection_scope
from skatmind.app_web.stateful_localization import text
from skatmind.match_analysis_exports import (
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
)


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def comparison_link(page):
    pattern = r'href="(/learning/debrief/[a-f0-9]{64}/(?:all|[0-9]+)/[a-f0-9]{64})"'
    return re.search(pattern, page)[1]


def complete_report(server):
    browser, path, page = open_alex(server, count=30)
    page = follow(browser, browser.request("GET", "/matches/review/2?decision_index=3"))
    page = follow(browser, browser.submit(form(page), requested_worlds="2", analysis_matadors="1"))
    report, = server.app_context.managed_stateful.active_match.capture.report_store.list()
    return browser, path, page, report


def test_direct_without_collection_captured_comparison_language_return_and_downloads(
    localized_server, monkeypatch,
):
    browser, path, page, report = complete_report(localized_server)
    before = path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Navigation must not analyze again")
    monkeypatch.setattr(rollout, "execute_match_decision_analysis_v1", forbidden)
    assert localized_server.app_context.managed_stateful.active_learning is None
    assert f'/learning/debrief/from/{report.report_id}' in page
    page = follow(browser, browser.request("GET", f"/learning/debrief/from/{report.report_id}"))
    assert "Alex" in page and "C7" in page and "30" in page
    route = comparison_link(page)
    # Normal Match navigation replaces selection but cannot replace the captured report.
    browser.page("/matches/position/1")
    page = browser.page(route)
    assert "Alex" in page and "C7" in page
    for suffix, builder in (("request.json", build_match_rollout_request_export_v1),
                            ("result.json", build_match_report_result_export_v1)):
        assert browser.request("GET", route + "/" + suffix)[2] == builder(report).to_bytes()
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert text(locale, "debrief.comparison") not in page
        assert text(locale, "debrief.recording") in unescape(page)
    returned = browser.page(route + "/recording")
    assert form(returned)["values"]["decision_index"] == "3"
    assert path.read_bytes() == before
    assert localized_server.app_context.managed_stateful.active_learning is None


def test_collection_empty_explicit_native_include_counts_and_unchanged_recording(
    localized_server, monkeypatch,
):
    browser, path, _, report = complete_report(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    target = localized_server.app_context.managed_stateful.active_learning
    assert target.debrief_sources.sources == () and target.corpus.prepared_artifacts is None
    assert "Recorded decisions: 30" in page and "No completed comparisons are included" in page
    files, recording = saved_bytes(target.path), path.read_bytes()
    include = Forms(page).find("/learning/debrief/include")
    def forbidden(*args, **kwargs):
        pytest.fail("Reuse must not execute analysis or full dataset preparation")
    monkeypatch.setattr(rollout, "execute_match_decision_analysis_v1", forbidden)
    monkeypatch.setattr("skatmind.app_web.learning_frontend.prepare_learning_corpus_artifacts_web_v1",
                        forbidden)
    page = follow(browser, browser.submit(include))
    assert target.debrief_sources.sources[0].report is report
    assert target.corpus.strategy_source_store.sources == ()
    assert "Distinct analyzed decisions included: 1 (1 reports)" in page
    assert "Alex" in page and "C7" in page and "matador" in page.lower()
    route = comparison_link(page)
    assert browser.request("GET", route)[0] == 200
    scope = collection_scope(localized_server.app_context, target)
    alex = scope.players.index("alex")
    filtered = browser.page(f"/learning/debrief/{scope.scope_id}/{alex}")
    assert "Recorded decisions: 10" in filtered
    bea = scope.players.index("bea")
    filtered = browser.page(f"/learning/debrief/{scope.scope_id}/{bea}")
    assert "Recorded decisions: 10" in filtered and "included: 0 (0 reports)" in filtered
    # Replaying an old mutation proof cannot replace matching evidence.
    assert browser.submit(include)[0] == 409
    assert len(target.debrief_sources.sources) == 1
    assert files == saved_bytes(target.path) and recording == path.read_bytes()


def test_changed_recording_and_expired_scope_do_not_substitute(localized_server):
    browser, path, _, report = complete_report(localized_server)
    page = follow(browser, browser.request("GET", f"/learning/debrief/from/{report.report_id}"))
    route = comparison_link(page)
    active = localized_server.app_context.managed_stateful.active_match
    external_pass(path, active.workspace)
    assert browser.request("GET", route + "/recording")[0] == 409
    assert browser.request("GET", route)[0] == 200
    localized_server.app_context.managed_stateful.debrief_scopes.clear()
    response = browser.request("GET", route)
    assert response[0] == 409 and "no longer available" in response[2].decode()
    assert 'href="/learning/current"' not in response[2].decode()
    assert 'href="/review/recorded"' in response[2].decode()


def collection_with_offer(server):
    browser, path, page, report = complete_report(server)
    create_collection(browser)
    missing = browser.page("/learning/current")
    assert text("en", "debrief.missing_snapshot") in unescape(missing)
    assert not any(f["action"] == "/learning/debrief/include" for f in Forms(missing).forms)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    return browser, path, page, report


@pytest.mark.parametrize("field", ("selection", "report_id", "source_handle", "managed_handle"))
def test_foreign_or_tampered_transfer_preserves_prior_output(localized_server, field):
    browser, _, page, _ = collection_with_offer(localized_server)
    include = Forms(page).find("/learning/debrief/include")
    target = localized_server.app_context.managed_stateful.active_learning
    before = saved_bytes(target.path)
    response = browser.submit(include, **{field: "0" * 64})
    assert response[0] == 409
    assert target.debrief_sources.sources == () and saved_bytes(target.path) == before
    follow(browser, browser.submit(include))
    retained = target.debrief_sources.sources
    assert browser.submit(include, **{field: "0" * 64})[0] == 409
    assert target.debrief_sources.sources == retained


def test_report_expiry_copied_evidence_and_reload_reopen_lifetimes(localized_server):
    from test_learning_direct_entry_web import build, downloads

    browser, _, page, report = collection_with_offer(localized_server)
    target = localized_server.app_context.managed_stateful.active_learning
    # An explicit technical preparation is independent of debrief incorporation.
    page = build(browser, page)
    prepared, exports = target.corpus.prepared_artifacts, downloads(browser)
    include = Forms(page).find("/learning/debrief/include")
    page = follow(browser, browser.submit(include))
    route = comparison_link(page)
    assert target.corpus.prepared_artifacts is prepared and downloads(browser) == exports
    assert prepared.learning_dataset.strategy_teacher_evidence_count == 0
    active = localized_server.app_context.managed_stateful.active_match
    active.capture.report_store.clear()
    assert browser.request("GET", f"/learning/debrief/from/{report.report_id}")[0] == 409
    assert browser.request("GET", route)[0] == 200
    page = browser.page(route.rsplit("/", 1)[0] + "/inputs")
    page = follow(browser, browser.submit(operation_form(page, "reload_corpus")))
    assert len(target.debrief_sources.sources) == 1
    assert browser.request("GET", route)[0] == 409
    assert browser.request("GET", comparison_link(page))[0] == 200
    follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/open")))
    reopened = localized_server.app_context.managed_stateful.active_learning
    assert reopened is not target and reopened.debrief_sources.sources == ()


def test_current_change_keeps_explicit_old_binding_and_working_restore(localized_server):
    from skatmind.app_web.learning_frontend import (
        import_workspace_bytes_into_unified_learning_v1,
    )
    from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1
    from skatmind.match_workspace_persistence import _build_match_workspace_file_bytes_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    browser, _, page, report = collection_with_offer(localized_server)
    page = follow(browser, browser.submit(Forms(page).find("/learning/debrief/include")))
    route = comparison_link(page)
    target = localized_server.app_context.managed_stateful.active_learning
    retained, = target.debrief_sources.sources
    workspace = retained.snapshot.workspace
    changed = mark_match_workspace_passed_deal_v1(workspace, match_position=3,
        expected_revision=workspace.revision, game_timecode=None).workspace
    result = import_workspace_bytes_into_unified_learning_v1(target,
        _build_match_workspace_file_bytes_v1(build_match_workspace_persistence_document_v1(changed)),
        selection_mode="select_imported", same_revision_resolution="reject",
        expected_catalog_revision=target.corpus.store.document.catalog.revision)
    assert result.status == "applied"
    page = browser.page("/learning/current")
    assert text("en", "debrief.snapshot_mismatch") in unescape(page)
    assert not any(f["action"] == "/learning/debrief/include" for f in Forms(page).forms)
    assert browser.request("GET", route)[0] == 409
    assert target.debrief_sources.sources == (retained,)
    restored = follow(browser, browser.submit(operation_form(page, "select_current_snapshot")))
    assert "included: 1 (1 reports)" in restored
    assert report.report_id in comparison_link(restored)


def test_target_change_during_unlocked_reconciliation_rejects_publication(
    localized_server, monkeypatch,
):
    import skatmind.app_web.debrief_frontend as frontend

    browser, _, page, _ = collection_with_offer(localized_server)
    target = localized_server.app_context.managed_stateful.active_learning
    include = Forms(page).find("/learning/debrief/include")
    entered, release = Event(), Event()
    real = frontend.replace
    def delayed(*args, **kwargs):
        value = real(*args, **kwargs)
        entered.set()
        assert release.wait(15)
        return value
    monkeypatch.setattr(frontend, "replace", delayed)
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(browser.submit, include)
        assert entered.wait(10)
        target.corpus.reload()
        release.set()
        assert pending.result()[0] == 409
    assert target.debrief_sources.sources == ()


def test_remove_is_explicit_and_invalidates_only_the_debrief(localized_server):
    browser, path, page, _ = collection_with_offer(localized_server)
    page = follow(browser, browser.submit(Forms(page).find("/learning/debrief/include")))
    route = comparison_link(page)
    target = localized_server.app_context.managed_stateful.active_learning
    before = path.read_bytes(), saved_bytes(target.path)
    page = follow(browser, browser.submit(Forms(page).find("/learning/debrief/remove")))
    assert "included: 0 (0 reports)" in page and target.debrief_sources.sources == ()
    assert browser.request("GET", route)[0] == 409
    assert before == (path.read_bytes(), saved_bytes(target.path))


def test_direct_scope_bound_and_original_handle_are_enforced(localized_server):
    from dataclasses import replace

    from skatmind.api.v1.contracts import ResultDocumentV1
    from skatmind.app_web.debrief_frontend import capture_direct_scope
    from skatmind.match_analysis_contracts import build_match_analysis_report_v1

    browser, _, _, report = complete_report(localized_server)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    first = capture_direct_scope(app, report.report_id)
    first_route = f"/learning/debrief/{first.scope_id}/all/{report.report_id}"
    original_handle = active.handle
    active.handle = "0" * 64
    assert browser.request("GET", first_route + "/recording")[0] == 409
    active.handle = original_handle
    assert browser.request("GET", first_route)[0] == 200
    for index in range(1, 9):
        raw = report.value.result.to_dict()["document"]
        raw["whole_game_rollout_result"]["work"]["elapsed_ms"] += index
        variant = build_match_analysis_report_v1(replace(report.value,
            result=ResultDocumentV1(workflow=report.value.result.workflow, document=raw)))
        active.capture.report_store.put(variant)
        capture_direct_scope(app, variant.report_id)
    assert len(app.managed_stateful.debrief_scopes) == 8
    assert browser.request("GET", first_route)[0] == 409
    assert len(active.capture.report_store.list()) == 8


def test_resource_routes_are_exact_and_foreign_players_cannot_open_comparison(localized_server):
    browser, _, _, report = complete_report(localized_server)
    page = follow(browser, browser.request("GET", f"/learning/debrief/from/{report.report_id}"))
    route = comparison_link(page)
    assert browser.request("GET", route + "/requestXjson")[0] == 404
    assert browser.request("GET", route.replace("/all/", "/0/"))[0] == 409  # Chris, not Alex.
    assert browser.request("GET", route + "/request.json")[0] == 200


def test_scope_lookup_rechecks_target_after_waiting_for_corpus_lock(localized_server):
    from skatmind.app_web.debrief_frontend import DebriefUnavailable, resolve_scope

    browser, _, page, _ = collection_with_offer(localized_server)
    follow(browser, browser.submit(Forms(page).find("/learning/debrief/include")))
    app = localized_server.app_context
    target = app.managed_stateful.active_learning
    scope = collection_scope(app, target)
    original_lock = target.corpus.lock
    class ReplacedWhileWaiting:
        def __enter__(self):
            original_lock.acquire()
            with app.lock:
                app.managed_stateful.active_learning = None
        def __exit__(self, *args):
            original_lock.release()
    target.corpus.lock = ReplacedWhileWaiting()
    try:
        with pytest.raises(DebriefUnavailable, match="changed"):
            resolve_scope(app, scope.scope_id)
    finally:
        target.corpus.lock = original_lock
        app.managed_stateful.active_learning = target
