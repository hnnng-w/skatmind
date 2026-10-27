"""Selected retained Report actions over real execution and authenticated delivered HTML."""

import pytest
from test_analysis_download_details import assert_analysis_actions, assert_delivery, download_nodes
from test_frontend_language_switching import localized_server as _server
from test_learning_report_attachment_web import executed_source, open_other, save_other
from test_match_decision_analysis import _complete_workspace
from test_match_historical_analysis import _strict_workspace
from test_match_recording_recovery_web import follow, operation_form
from test_match_rollout_web import form as rollout_form
from test_match_rollout_web import open_alex
from test_recorded_review_navigation import chooser_form, external_pass
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.match_frontend as frontend
import skatmind.match_analysis_report_source_export as source_export
from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    MatchHistoricalAnalysisOptionsV1,
    build_match_analysis_report_v1,
    prepare_match_materialization_report_v1,
)
from skatmind.match_analysis_exports import build_match_report_result_export_v1
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.match_historical_analysis import execute_match_historical_analysis_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def open_workspace(server, workspace):
    path = server.app_context.managed_stateful.root("matches") / "synthetic-299.json"
    assert save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(
        workspace), expected_content_fingerprint=None).status == "saved"
    browser = Browser(server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    return browser, server.app_context.managed_stateful.active_match


@pytest.mark.parametrize(("method", "decision"), (
    ("immediate_expected_value", 30), ("bounded_search", 30), ("auto", 30),
    ("information_set_search", 30), ("information_set_search", 1),
))
def test_supported_executed_reports_keep_exact_source_action_without_learning(
    localized_server, monkeypatch, method, decision,
):
    browser, active = open_workspace(localized_server, _complete_workspace())
    # Explicit fixture execution, separate from the guarded view/download phase.
    result = frontend.execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "3",
        "expected_revision": str(active.workspace.revision), "decision_index": str(decision),
        "recommendation_method": method, "immediate_sample_count": "1",
        "immediate_random_seed": "0", "search_random_seed": "0",
        "search_budget_profile": ("historical_review_v1" if method == "immediate_expected_value"
                                  else "interactive_v1"), "use_profile_presets": False,
    })
    assert result.status == "applied"
    report, = active.capture.report_store.list()
    assert report.value.status == "executed"
    if method == "information_set_search":
        document = report.value.result.document
        assert document["information_set_search_result"]["status"] == (
            "unavailable" if decision == 1 else "complete")
        if decision == 1:
            assert document["recommendation"]["card"] is None
    artifact = build_match_report_result_export_v1(report)
    expected = source_export.serialize_match_analysis_report_source_export_v1(
        source_export.build_match_analysis_report_source_export_v1(report))
    before = active.path.read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail("Report view attempted source serialization, Request rebuilding or execution")

    import skatmind.capture_web.analysis as analysis
    import skatmind.match_decision_analysis as decision_analysis

    with monkeypatch.context() as guard:
        guard.setattr(analysis, "execute_match_decision_analysis_v1", forbidden)
        guard.setattr(decision_analysis, "build_match_decision_position_request_v1", forbidden)
        guard.setattr(frontend, "build_match_analysis_report_source_export_v1", forbidden)
        guard.setattr(source_export, "serialize_match_analysis_report_source_export_v1", forbidden)
        page = browser.page(f"/matches/reports/{report.report_id}")
    links = download_nodes(page)
    result_route, source_route = (node["attrs"]["href"] for node in links)
    assert_analysis_actions(page, (result_route, source_route))
    assert source_route == f"/matches/api/v1/reports/{report.report_id}/strategy-source.json"
    assert_delivery(browser, result_route, artifact.to_bytes(), artifact.filename)
    assert_delivery(browser, source_route, expected,
        artifact.filename.removesuffix(".json") + "-strategy-source.json")
    assert browser.request("GET", source_route, headers={"Cookie": ""})[0] == 403
    assert browser.request("GET", source_route, headers={"Host": "example.com"})[0] == 403
    assert active.path.read_bytes() == before
    assert localized_server.app_context.managed_stateful.active_learning is None


@pytest.mark.parametrize("kind", ("unavailable", "historical", "materialization"))
def test_ineligible_selected_reports_do_not_borrow_eligible_source(localized_server, kind):
    browser, active = open_workspace(localized_server, _strict_workspace())
    eligible = build_match_analysis_report_v1(execute_match_decision_analysis_v1(
        active.workspace, match_position=3, decision_index=30,
        options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1)))
    active.capture.report_store.put(eligible)
    if kind == "unavailable":
        value = execute_match_decision_analysis_v1(active.workspace, match_position=3,
            decision_index=99, options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1))
        assert value.status == "unavailable"
    elif kind == "historical":
        value = execute_match_historical_analysis_v1(active.workspace, match_position=3,
            options=MatchHistoricalAnalysisOptionsV1(immediate_review=False,
                                                     tactical_motif_review=True))
        assert value.status == "executed"
    else:
        value = prepare_match_materialization_report_v1(active.workspace)
    report = active.capture.report_store.put(build_match_analysis_report_v1(value))
    page = browser.page(f"/matches/reports/{report.report_id}")
    assert "strategy-source.json" not in page and "exports/report-source.json" not in page
    if kind == "historical":
        assert len(download_nodes(page)) == 1
    # Preserve the builder's existing error ordering: unavailable/materialization
    # have no Root Result artifact; Historical has one but is not a source.
    assert browser.request("GET",
        f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")[0] == (
            404 if kind == "historical" else 500)
    assert "strategy-source.json" in browser.page(f"/matches/reports/{eligible.report_id}")


def test_selected_rollout_keeps_its_two_artifacts_and_separate_debrief(localized_server):
    browser, _, page = open_alex(localized_server)
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                          immediate_sample_count="1"))
    active = localized_server.app_context.managed_stateful.active_match
    eligible, = active.capture.report_store.list()
    assert "strategy-source.json" in page
    page = follow(browser, browser.submit(rollout_form(page), objective="played_game_goal",
                                          requested_worlds="1"))
    assert len(active.capture.report_store.list()) == 2
    assert "strategy-source.json" not in page and len(download_nodes(page)) == 2
    assert '/learning/debrief/from/' in page
    assert "strategy-source.json" in browser.page(f"/matches/reports/{eligible.report_id}")


@pytest.mark.parametrize("change", ("mutation", "reload", "active", "replacement", "deletion",
                                   "missing", "eviction"))
def test_emitted_source_link_expires_without_substitution_or_execution(
    localized_server, monkeypatch, change,
):
    browser = Browser(localized_server)
    path, workspace, report, _ = executed_source(browser, localized_server)
    active = localized_server.app_context.managed_stateful.active_match
    page = browser.page(f"/matches/reports/{report.report_id}")
    route, = (node["attrs"]["href"] for node in download_nodes(page)
              if node["attrs"]["href"].endswith("/strategy-source.json"))
    if change == "mutation":
        follow(browser, browser.submit(operation_form(browser.page("/matches/position/2"),
                                                      "mark_passed_deal")))
    elif change == "reload":
        follow(browser, browser.submit(Forms(page).find("/matches/api/v1/reload")))
    elif change == "active":
        other, _ = save_other(path, workspace)
        open_other(browser, other)
    elif change == "replacement":
        external_pass(path, workspace)
    elif change == "deletion":
        path.unlink()  # Deliberate deletion of this disposable fixture only.
    elif change == "missing":
        active.capture.report_store.clear()
    else:
        for seed in range(8):
            active.capture.report_store.put(build_match_analysis_report_v1(
                execute_match_decision_analysis_v1(workspace, match_position=3, decision_index=1,
                    options=MatchDecisionAnalysisOptionsV1(immediate_sample_count=1,
                                                           immediate_random_seed=seed))))
        assert active.capture.report_store.get(report.report_id) is None
    import skatmind.capture_web.analysis as analysis
    monkeypatch.setattr(analysis, "execute_match_decision_analysis_v1",
                        lambda *a, **kw: pytest.fail("Download regenerated an analysis"))
    status, _, raw = browser.request("GET", route)
    assert status in {404, 409} and b'"document_kind"' not in raw
