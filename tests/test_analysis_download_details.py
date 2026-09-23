"""Analysis artifact/content ownership; real returned pages separate from scalar fixtures."""
import hashlib
import json
from collections import Counter
from dataclasses import replace

import pytest
from test_frontend_language_switching import (
    localized_server as _server,
)
from test_guided_frontend_result_presentation import (
    _execution,
    _historical_document,
    _position_document,
)
from test_guided_frontend_web import ROOT, _multipart, _request
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_decision_context_web import record_context_match, record_second_context_game
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import (
    Browser,
    Forms,
    record_score_review_game,
    score_review_form,
)

from skatmind.api.v1 import WorkflowV1
from skatmind.app_web.guided_rendering import render_analyze_workflow_v1
from skatmind.app_web.result_presentation import (
    RESULT_SECTION_TITLES_V1,
    build_result_presentation_v1,
)
from skatmind.app_web.result_rendering import render_result_presentation_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_analysis_exports import build_match_report_result_export_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def download_nodes(page):
    return [n for n in Hierarchy(page).nodes if n["tag"] == "a" and "download" in n["attrs"]]


def assert_analysis_actions(page, routes, locale="en"):
    tree = Hierarchy(page)
    links = [n for n in download_nodes(page) if n["attrs"]["href"] in routes]
    for link in links:
        assert not any(p["tag"] == "details" for p in link["parents"])
        assert any(p["attrs"].get("class") == "analysis-downloads" for p in link["parents"])
        assert "JSON" in link["text"] and len(link["text"]) > 12
    assert [n["attrs"]["href"] for n in links] == list(routes)
    groups = [n for n in tree.nodes if n["attrs"].get("class") == "analysis-downloads"]
    assert len(groups) == 1
    assert text(locale, "result.downloads") in groups[0]["text"]


def import_example(browser, area, filename):
    page = browser.page("/" + area)
    form = Forms(page).find(f"/actions/{area}/import-json")
    body, kind = _multipart((ROOT / "examples" / filename).read_bytes(),
                            revision=int(form["values"]["revision"]))
    return _request(browser.server, "POST", form["action"], body=body,
        headers={"Cookie": browser.cookie, "Origin": browser.server.origin, "Content-Type": kind})


def assert_delivery(browser, route, expected, filename):
    status, headers, raw = browser.request("GET", route)
    assert status == 200 and raw == expected
    assert headers["content-type"] == "application/json; charset=utf-8"
    assert headers["content-disposition"] == f'attachment; filename="{filename}"'
    assert headers["cache-control"] == "no-store"
    return raw


@pytest.mark.parametrize(("area", "example"), (
    ("analyze", "grand_bounded_search_exhaustive.json"),
    ("review", "historical_grand_normal_completion.json"),
))
def test_real_import_execution_download_and_failed_input(localized_server, area, example):
    browser = Browser(localized_server)
    request_route, result_route = (
        f"/downloads/{area}/{name}.json" for name in ("request", "result"))
    assert not download_nodes(browser.page("/" + area))
    page = follow(browser, import_example(browser, area, example))
    assert [n["attrs"]["href"] for n in download_nodes(page)] == [request_route]
    assert "analysis-downloads" not in page and "result-section-1" not in page
    assert browser.request("GET", result_route)[0] == 404
    page = follow(browser, browser.submit(Forms(page).find(f"/actions/{area}/run-imported")))
    assert 'href="#recorded-decision-' not in page
    state = getattr(localized_server.app_context, area + "_state")
    before = state.request_json_bytes, state.result_json_bytes
    assert_analysis_actions(page, (request_route, result_route))
    assert text("en", "result.import_details") in page
    for name, raw in zip(("request", "result"), before, strict=True):
        assert_delivery(browser, f"/downloads/{area}/{name}.json", raw,
                        f'skatmind-{"position" if area == "analyze" else "review"}-{name}.json')
    # Rejected new input leaves the older accepted import and Result owners intact.
    body, kind = _multipart(b'{"invalid":true}', revision=state.revision)
    rejected = _request(localized_server, "POST", f"/actions/{area}/import-json", body=body,
        headers={"Cookie": browser.cookie, "Origin": localized_server.origin, "Content-Type": kind})
    assert rejected[0] == 400
    assert_analysis_actions(rejected[2].decode(), (request_route, result_route))
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(browser.page("/" + area)).find(
            "/actions/profile/language"), language=locale))
        assert_analysis_actions(page, (request_route, result_route), locale)
    assert (getattr(localized_server.app_context, area + "_state").request_json_bytes,
            getattr(localized_server.app_context, area + "_state").result_json_bytes) == before
    # Accepted replacement invalidates the previous Result; only the new import is downloadable.
    page = follow(browser, import_example(browser, area, example))
    assert [n["attrs"]["href"] for n in download_nodes(page)] == [request_route]
    assert browser.request("GET", result_route)[0] == 404


def test_real_session_downloads_have_no_technical_ancestor(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=12)
    page = follow(browser, browser.submit(score_review_form(browser)))
    context = localized_server.app_context.managed_stateful.active_session
    execution, source = context.execution, context.path.read_bytes()
    routes = tuple(f"/sessions/downloads/{name}.json" for name in ("request", "result"))
    assert_analysis_actions(page, routes)
    assert [page.count(text("en", f"result.technical.{scope}_policy"))
            for scope in ("general", "left", "right")] == [1, 1, 1]
    assert hashlib.sha256(execution.request_json_bytes).hexdigest() == (
        "05dc65aa713fb37c7b40cd9a4027ce6926881e6bb0c98adaf4256b8a7f14ec94")
    assert hashlib.sha256(execution.result_json_bytes).hexdigest() == (
        "76eb05221cab155ff59f734ec568bbead767c2f309d6823546d598412ac545c1")
    for name in ("request", "result"):
        assert_delivery(browser, f"/sessions/downloads/{name}.json",
                        getattr(execution, name + "_json_bytes"), f"skatmind-session-{name}.json")
    assert context.path.read_bytes() == source
    page = follow(browser, browser.submit(Forms(page).find("/sessions/reload")))
    assert 'id="session-result"' not in page
    assert all(browser.request("GET", route)[0] == 404 for route in routes)
    page = follow(browser, browser.submit(score_review_form(browser)))
    assert_analysis_actions(page, routes)
    assert context.execution.request_json_bytes == execution.request_json_bytes
    assert context.execution.result_json_bytes == execution.result_json_bytes


def test_real_match_selected_report_owns_only_its_result(localized_server):
    browser = Browser(localized_server)
    record_context_match(browser)
    record_second_context_game(browser)
    active = localized_server.app_context.managed_stateful.active_match
    retained = []
    for game in (4, 1):
        page = follow(browser, browser.submit(operation_form(
            browser.page(f"/matches/review/{game}"), "analyze_decision")))
        report = active.capture.report_store.list()[-1]
        route = f"/matches/api/v1/reports/{report.report_id}.json"
        artifact = build_match_report_result_export_v1(report)
        assert_analysis_actions(page, (route,))
        assert page.index('class="analysis-downloads"') < page.index('class="technical-details"')
        assert_delivery(browser, route, artifact.to_bytes(), artifact.filename)
        retained.append((report, route, artifact))
    source = active.path.read_bytes()
    browser.page("/matches/position/2")
    for report, route, artifact in retained:
        page = browser.page(f"/matches/reports/{report.report_id}")
        assert_analysis_actions(page, (route,))
        assert len(download_nodes(page)) == 1
        assert_delivery(browser, route, artifact.to_bytes(), artifact.filename)
    assert active.path.read_bytes() == source
    # Deliberate external-file fault, not a mocked successful save or execution.
    active.path.write_bytes(b"{}\n")
    assert browser.request("GET", retained[0][1])[0] == 409
    active.path.write_bytes(source)
    assert all(browser.request("GET", route)[0] == 404 for _, route, _ in retained)
    follow(browser, browser.submit(Forms(page).find("/matches/api/v1/reload")))
    for _, route, _ in retained:
        assert browser.request("GET", route)[0] == 404


@pytest.mark.parametrize("workflow", (WorkflowV1.POSITION_ANALYSIS, WorkflowV1.HISTORICAL_GAME))
@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("response", ("random", "basic"))
def test_scalar_technical_inventory_once_without_merging_equal_scopes(workflow, locale, response):
    """Not an execution fixture: inventory every projected detail and producer prose."""
    document = (_position_document() if workflow is WorkflowV1.POSITION_ANALYSIS
                else _historical_document())
    for key in ("opponent_policy_settings", "left_opponent_policy_settings",
                "right_opponent_policy_settings"):
        document[key] = {"opponent_lead_policy": "random", "opponent_response_policy": response}
    presentation = build_result_presentation_v1(
        _execution(workflow, document, warnings=("Exact warning <retained>.",)), locale=locale)
    before = repr(presentation)
    page = render_result_presentation_v1(presentation, locale=locale)
    tree = Hierarchy(page)
    assert tuple(s.title for s in presentation.sections) == RESULT_SECTION_TITLES_V1
    ids = [f"result-section-{i}" for i in range(1, 6)]
    assert [n["attrs"]["id"] for n in tree.nodes if n["attrs"].get("id") in ids] == ids
    assert len([n for n in tree.nodes if n["tag"] == "details"]) == 1
    from skatmind.app_web.render_locale import localized_render
    from skatmind.app_web.result_localization import needs_raw_technical_value, result_label
    expected = Counter(localized_render(result_label)(d.label, locale=locale)
                       for s in presentation.sections for d in s.details)
    # A localized 'see technical details' placeholder is not another raw value.
    # Only previously unmapped enums need that original value alongside the placeholder.
    expected.update(localized_render(result_label)(d.label, locale=locale)
                    for s in presentation.sections[:-1] for d in s.details
                    if needs_raw_technical_value(d.label, d.value))
    actual = Counter(n["text"] for n in tree.nodes if n["tag"] == "dt")
    assert actual == expected
    assert page.count(text(locale, "result.analysis_details")) == 1
    # All technical-only originals survive, including budget fields and producer
    # prose. Lead/response are not parsed or merged when equal across three scopes.
    technical = tree.by_id("result-section-5")["parents"][-1]
    technical_values = [n["text"] for n in tree.nodes if n["tag"] == "dd"
                        and any(p is technical for p in n["parents"])]
    for detail in presentation.sections[-1].details:
        assert detail.value in technical_values
    if workflow is WorkflowV1.POSITION_ANALYSIS:
        assert technical_values.count(f"lead random; response {response}") == 3
        assert "node_budget_exhausted" in technical_values
        assert "sampled_compatible_worlds" in technical_values
    for section in presentation.sections:
        for content in (*section.paragraphs, *section.items):
            assert sum(n["text"] == content for n in tree.nodes if n["tag"] in {"p", "li"}) == 1
    assert sum(n["text"] == "Exact warning <retained>."
               for n in tree.nodes if n["tag"] == "li") == 1
    assert repr(presentation) == before


def test_running_import_keeps_request_action_when_result_is_not_displayed(localized_server):
    browser = Browser(localized_server)
    page = follow(browser, import_example(
        browser, "analyze", "grand_bounded_search_exhaustive.json"))
    follow(browser, browser.submit(Forms(page).find("/actions/analyze/run-imported")))
    state = localized_server.app_context.analyze_state
    running = state.begin(expected_revision=state.revision)
    html = render_analyze_workflow_v1(running)
    assert "result-section-1" not in html
    assert [n["attrs"]["href"] for n in download_nodes(html)] == ["/downloads/analyze/request.json"]
    # Defensive mismatched retained owners are not equated through identical hrefs.
    other = replace(state.imported_request, document={
        **state.imported_request.to_dict()["document"], "random_seed": 999})
    mismatched = replace(state, imported_request=other)
    html = render_analyze_workflow_v1(mismatched)
    assert [n["attrs"]["href"] for n in download_nodes(html)] == [
        "/downloads/analyze/request.json", "/downloads/analyze/result.json"]


def test_scalar_match_curated_technical_content_is_lossless():
    """Curated Report diagnostics are a separate minimized source, never a full Result."""
    from skatmind.app_web.match_report_rendering import render_match_reports_v1
    report = {"report_id": "a" * 64, "report_kind": "decision_analysis", "match_position": 1,
              "details": {"status": "unavailable", "unavailable_reason": "missing_evidence",
                          "recommendation_method": {"requested_method": "bounded_search",
                                                    "effective_method": None}}}
    source = json.dumps(report)
    html = render_match_reports_v1({"reports": [], "selected_report": report,
        "download_availability": {"report_result": False}}, "en")
    tree = Hierarchy(html)
    raw, = (n["text"] for n in tree.nodes if n["tag"] == "pre")
    assert json.loads(raw) == report and json.dumps(report) == source
    assert "analysis-downloads" not in html and not download_nodes(html)


@pytest.mark.parametrize("status", ("complete", "partial", "timeout", "unavailable"))
def test_scalar_download_availability_is_not_inferred_from_analysis_status(status):
    presentation = build_result_presentation_v1(_execution(
        WorkflowV1.POSITION_ANALYSIS, _position_document(status=status)))
    assert not download_nodes(render_result_presentation_v1(presentation))
    html = render_result_presentation_v1(presentation, request_download_available=True,
                                       result_download_available=True)
    assert_analysis_actions(html, (
        "/downloads/analyze/request.json", "/downloads/analyze/result.json"))
