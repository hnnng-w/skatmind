"""Real returned-form execution plus explicitly controlled display-only regressions."""
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from html import unescape

import pytest
from test_analysis_download_details import assert_analysis_actions
from test_analysis_explanations import normal_result, search_request
from test_equal_best_immediate import assert_visible_equal_best
from test_frontend_language_switching import localized_server as _server
from test_guided_frontend_web import _multipart, _request
from test_match_card_correction_ui import activated_form
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_decision_context_web import record_context_match, record_second_context_game
from test_review_return_labels import assert_session_return
from test_session_declaration_correction_web import PREFIX, preview
from test_session_recorded_review_web import (
    Browser,
    Forms,
    record_score_review_game,
    score_review_form,
)

import skatmind.api.v1.session.files as files
import skatmind.app_web.execution as execution
import skatmind.app_web.frontend_profile_operations as profiles
import skatmind.app_web.task_first_match_state as match_state
import skatmind.capture_web.analysis as match_analysis
import skatmind.capture_web.context as match_context
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1 as canonical
from skatmind.app_web.recorded_decision_context_sources import match_analysis_explanation
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.match_analysis_exports import build_match_report_result_export_v1
from skatmind.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)


def candidate_values(page):
    """Read the delivered candidate cells, excluding responsive duplicate labels."""
    return [unescape(value) for value in re.findall(
        r'<span class="candidate-value">(.*?)</span>', page, re.S)]


def controlled_match_precision_projection(real):
    """Inject screenshot scalars into a disposable display projection, not an execution."""
    rows = [
        {"card": card, "expected_point_swing": points, "win_rate": rate}
        for card, points, rate in (
            ("CQ", 2.0599999999999996, 0.94), ("C10", 1.2400000000000002, 0.96),
            ("C8", 1.2200000000000002, 1.0), ("C7", 1.1600000000000001, 0.58),
        )
    ]
    def project(report):
        value = real(report)
        value["details"]["immediate_candidate_values"] = deepcopy(rows)
        return value
    return project


@pytest.mark.parametrize("locale", ("de", "en"))
def test_controlled_match_screenshot_points_and_percentages_in_delivered_html(
    localized_server, monkeypatch, locale,
):
    browser = Browser(localized_server)
    record_context_match(browser)
    follow(browser, browser.submit(operation_form(browser.page("/matches/review/1"),
        "analyze_decision"), immediate_sample_count="8"))
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    exact, disk = canonical(report.to_dict()), active.path.read_bytes()
    routes = (f"/matches/api/v1/reports/{report.report_id}.json",
              f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")
    downloads = {route: browser.request("GET", route)[2] for route in routes}
    monkeypatch.setattr(match_state, "_selected_report_details",
                        controlled_match_precision_projection(match_state._selected_report_details))
    route = f"/matches/reports/{report.report_id}"
    status, _, raw = browser.request("GET", route, headers={"Accept-Language": locale})
    assert status == 200
    expected = []
    for card, points, rate in (("CQ", "2.06", "94.00%"), ("C10", "1.24", "96.00%"),
                               ("C8", "1.22", "100.00%"), ("C7", "1.16", "58.00%")):
        expected.extend((f"{card_name(locale, card)} ({card})",
                         points.replace(".", ",") if locale == "de" else points,
                         rate.replace(".", ",") if locale == "de" else rate))
    assert candidate_values(raw.decode()) == expected
    assert active.capture.report_store.get(report.report_id) is report
    assert canonical(report.to_dict()) == exact and active.path.read_bytes() == disk
    for route, expected_bytes in downloads.items():
        status, _, raw = browser.request("GET", route)
        assert status == 200 and raw == expected_bytes


@pytest.mark.parametrize("path", ("session", "match"))
def test_real_ordinary_numbers_language_return_and_exact_downloads(
    localized_server, path, monkeypatch,
):
    browser = Browser(localized_server)
    if path == "session":
        record_score_review_game(browser, names=("B 1.25", "C 0.125", "A 3.14"))
        page = follow(browser, browser.submit(score_review_form(browser)))
        active = localized_server.app_context.managed_stateful.active_session
        retained = active.execution
        route = "/sessions/current"
        downloads = {f"/sessions/downloads/{name}.json": getattr(retained, name + "_json_bytes")
                     for name in ("request", "result")}
    else:
        record_context_match(browser, names=("B 1.25", "C 0.125", "A 3.14"))
        record_second_context_game(browser)
        for game in (1, 4):
            page = follow(browser, browser.submit(operation_form(browser.page(
                f"/matches/review/{game}"), "analyze_decision"), immediate_sample_count="8"))
        active = localized_server.app_context.managed_stateful.active_match
        retained, newer = active.capture.report_store.list()
        assert retained.report_id != newer.report_id
        route = f"/matches/reports/{retained.report_id}"
        downloads = {
            f"/matches/api/v1/reports/{retained.report_id}.json":
                build_match_report_result_export_v1(retained).to_bytes(),
            f"/matches/api/v1/reports/{retained.report_id}/strategy-source.json":
                serialize_match_analysis_report_source_export_v1(
                    build_match_analysis_report_source_export_v1(retained)),
        }
    disk = active.path.read_bytes()
    exact = canonical(retained.result.result.to_dict() if path == "session" else retained.to_dict())
    calls = Counter()
    for module, name in (
        (execution, "execute"), (match_analysis, "execute_match_decision_analysis_v1"),
        (files, "save_session_file"), (match_context, "save_match_workspace_file_v1"),
        (profiles, "save_frontend_profile_file_v1"),
    ):
        real = getattr(module, name)
        def counted(*args, _real=real, _name=name, **kwargs):
            calls[_name] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(module, name, counted)

    def check_page(page, locale):
        assert f'<html lang="{locale}">' in page
        assert "B 1.25" in page and "C 0.125" in page and "A 3.14" in page
        if path == "session":
            assert_visible_equal_best(page, locale)
        else:
            rows = retained.value.result.document["analysis_report"]
            assert [row["card"] for row in rows] == ["C8", "C7", "C9"]
            assert [row["win_rate"] for row in rows] == [1.0, 0.875, 0.875]
            assert [row["expected_point_swing"] for row in rows] == [12.0, 10.625, 9.5]
            expected = []
            for card, points, rate in (("C8", "12.00", "100.00%"),
                                      ("C7", "10.62", "87.50%"), ("C9", "9.50", "87.50%")):
                expected.append(f'{card_name(locale, card)} ({card})')
                expected.extend(value.replace(".", ",") if locale == "de" else value
                                for value in (points, rate))
            assert candidate_values(page) == expected
            assert (f'<p>{text(locale, "task.recommendation")}</p>'
                    f'{card_name(locale, "C8")} (C8)') in page
            assert text(locale, "result.win_rate") in page
            for url in downloads:
                assert f'href="{url}"' in page

    # Before an explicit preference is saved, each concurrent HTTP request owns its locale.
    def get(locale):
        status, _, raw = browser.request("GET", route, headers={"Accept-Language": locale})
        assert status == 200
        check_page(raw.decode(), locale)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(get, ("de", "en", "de") * 2))
    assert not calls
    for locale in ("de", "en", "de"):
        page = browser.page(route)
        response = browser.submit(Forms(page).find("/actions/profile/language"), language=locale)
        assert response[0] == 303 and response[1]["location"] == route
        page = follow(browser, response)
        check_page(page, locale)
        if path == "session":
            assert active.execution is retained
        else:
            assert active.capture.report_store.get(retained.report_id) is retained
        for url, raw in downloads.items():
            status, _, downloaded = browser.request("GET", url)
            assert status == 200 and downloaded == raw
    assert active.path.read_bytes() == disk
    assert canonical(
        retained.result.result.to_dict() if path == "session" else retained.to_dict()) == exact
    assert calls == {"save_frontend_profile_file_v1": 3}


@pytest.mark.parametrize("method,key", (
    ("minimax", "bounded_search_result"),
    ("information_set_search", "information_set_search_result"),
))
def test_genuine_guided_search_numeric_cells_and_canonical_bytes(localized_server, method, key):
    browser = Browser(localized_server)
    form = Forms(browser.page("/analyze")).find("/actions/analyze/import-json")
    body, kind = _multipart(
        canonical(search_request(method)), revision=int(form["values"]["revision"]))
    page = follow(browser, _request(localized_server, "POST", form["action"], body=body,
        headers={"Cookie": browser.cookie, "Origin": localized_server.origin,
                 "Content-Type": kind}))
    follow(browser, browser.submit(Forms(page).find("/actions/analyze/run-imported")))
    state = localized_server.app_context.analyze_state
    result = state.latest_successful_result.result
    search = result.document[key]
    assert search["status"] == "complete" and search["candidate_results"]
    exact = canonical(result.to_dict())
    for locale in ("de", "en", "de"):
        page = follow(browser, browser.submit(Forms(browser.page("/analyze")).find(
            "/actions/profile/language"), language=locale))
        expected = []
        for row in search["candidate_results"]:
            expected.extend((row["card"], str(row["rank"]), text(locale,
                "common.answer.yes" if row["is_recommended"] else "common.answer.no"),
                str(row["completed_world_count"])))
            numbers = [f'{float(row["local_contract_success_rate"]) * 100:.2f}%', *(
                format(row[field], ".6g") if type(row[field]) is float else str(row[field])
                for field in ("mean_local_side_game_score", "mean_local_side_card_point_margin"))]
            expected.extend(value.replace(".", ",") if locale == "de" else value
                            for value in numbers)
        assert candidate_values(page) == expected
        for name in ("request", "result"):
            status, _, raw = browser.request("GET", f"/downloads/analyze/{name}.json")
            assert status == 200 and raw == getattr(state, name + "_json_bytes")
    assert localized_server.app_context.analyze_state is state
    assert canonical(result.to_dict()) == exact


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def test_real_session_binding_manual_same_mode_preview_and_invalidation(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    plays = record_score_review_game(browser, play_count=12)
    page = follow(browser, browser.submit(score_review_form(browser)))
    context = localized_server.app_context.managed_stateful.active_session
    retained, source = context.execution, context.path.read_bytes()
    checkpoints = canonical([c.to_dict() for c in context.decision_checkpoints])
    assert "Saved situation before this recorded Card" in page
    assert_session_return(page, "en")
    assert "None — unknown in this analysis" in page
    manual = normal_result(retained.result)
    assert "supplied review facts and accepted information policy" in manual
    assert "Saved situation before this recorded Card" not in manual
    # The identical exported review Request also runs through the real import form.
    form = Forms(browser.page("/review")).find("/actions/review/import-json")
    body, kind = _multipart(retained.request_json_bytes, revision=int(form["values"]["revision"]))
    page = follow(browser, _request(localized_server, "POST", form["action"], body=body,
        headers={"Cookie": browser.cookie, "Origin": localized_server.origin,
                 "Content-Type": kind}))
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/run-imported")))
    assert "supplied review facts and accepted information policy" in page
    assert "Saved situation before this recorded Card" not in page
    assert 'href="#recorded-decision-' not in page
    calls = Counter()
    for module, name, label in ((files, "save_session_file", "saves"),
                                (execution, "execute", "executions")):
        real = getattr(module, name)
        def counted(*args, _real=real, _label=label, **kwargs):
            calls[_label] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(module, name, counted)
    for locale, meaning in (("de", "Gespeicherte Situation vor dieser erfassten Karte"),
                            ("en", "Saved situation before this recorded Card")):
        page = follow(browser, browser.submit(Forms(browser.page()).find(
            "/actions/profile/language"), language=locale))
        assert meaning in page
        assert_session_return(page, locale)
        assert_analysis_actions(page, tuple(
            f"/sessions/downloads/{name}.json" for name in ("request", "result")), locale)
    for action in ("cancel", "apply"):
        page = preview(browser)
        assert context.execution is retained
        form = Forms(page).find(PREFIX + action) if action == "cancel" else activated_form(
            page, PREFIX + action)
        page = follow(browser, browser.submit(form))
        assert context.execution is retained
        assert "Saved situation before this recorded Card" in page
        assert_session_return(page, "en")
    # Negative input: a rejected later row must not relabel the surviving SJ Result.
    later = Forms(browser.page()).find("/sessions/review-decision", index=0)
    status, _, rejected = browser.submit(later, actual_card_played="CA")
    assert status == 400 and context.execution is retained
    assert_session_return(rejected.decode(), "en")
    assert not calls
    assert context.path.read_bytes() == source
    assert canonical([c.to_dict() for c in context.decision_checkpoints]) == checkpoints
    for name in ("request", "result"):
        assert browser.request("GET", f"/sessions/downloads/{name}.json")[2] == getattr(
            retained, name + "_json_bytes")
    page = follow(browser, browser.submit(Forms(page).find("/sessions/reload")))
    assert "Saved situation before this recorded Card" not in page and context.execution is None
    assert browser.request("GET", "/sessions/downloads/result.json")[0] == 404
    page = follow(browser, browser.submit(score_review_form(browser)))
    assert calls == {"executions": 1}
    assert context.execution.result_json_bytes == retained.result_json_bytes
    browser.command("record_play", card=plays[12]["card"])
    assert context.execution is None and calls == {"executions": 1, "saves": 1}
    assert "Saved situation before this recorded Card" not in browser.page()


@pytest.mark.parametrize("method", ("immediate_expected_value", "auto", "bounded_search",
                                    "information_set_search"))
def test_real_selected_match_explanation_and_other_game(localized_server, method):
    browser = Browser(localized_server)
    record_context_match(browser)
    record_second_context_game(browser)
    active = localized_server.app_context.managed_stateful.active_match
    for game in (4, 1):
        page = follow(browser, browser.submit(operation_form(browser.page(
            f"/matches/review/{game}"), "analyze_decision"), recommendation_method=method))
        report = active.capture.report_store.list()[-1]
        assert "Reconstructed situation before this Card in the selected Report" in page
        assert "Hand evidence may have been supplied later" in page
        if method in ("auto", "immediate_expected_value"):
            assert "Current-Trick evaluation" in page and "Samples per Card" in page
        else:
            assert "No recommendation was produced" in page and "Samples per Card" not in page
        if method == "auto":
            assert "Auto tried Search first" in page
    source, exact = active.path.read_bytes(), canonical(report.to_dict())
    route = f"/matches/api/v1/reports/{report.report_id}.json"
    raw = browser.request("GET", route)[2]
    browser.page("/matches/position/2")
    for locale, meaning in (("de", "Rekonstruierte Situation vor dieser Karte"),
                            ("en", "Reconstructed situation before this Card")):
        page = browser.page(f"/matches/reports/{report.report_id}")
        page = follow(browser, browser.submit(Forms(page).find(
            "/actions/profile/language"), language=locale))
        assert meaning in page
        assert_analysis_actions(page, (route,), locale)
        assert browser.request("GET", route)[2] == raw
    assert active.path.read_bytes() == source and canonical(report.to_dict()) == exact
    assert match_analysis_explanation(report, active.workspace).information == "match_snapshot"
