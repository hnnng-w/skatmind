"""Real returned-form execution and source lifetimes; no successful-operation mocks."""
from collections import Counter

import pytest
from test_analysis_download_details import assert_analysis_actions
from test_analysis_explanations import normal_result
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
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1 as canonical
from skatmind.app_web.recorded_decision_context_sources import match_analysis_explanation


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
