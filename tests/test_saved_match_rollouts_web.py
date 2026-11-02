"""Native S3 HTTP capabilities, retained-source rendering and save-only navigation."""

from collections import Counter
from html import unescape

import pytest
from test_match_recording_recovery_web import follow
from test_match_rollout_web import downloads, form, open_alex
from test_saved_match_analyses_web import localized_server as localized_server
from test_saved_match_analyses_web import saved_route
from test_session_recorded_review_web import Browser, Forms

import skatmind.application.execution as application_execution
import skatmind.automatic_learning_io as io
import skatmind.recommendation_workflow as workflow
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.saved_match_analyses import SAVED_MATCH_ROUTE, archive_store
from skatmind.app_web.stateful_localization import text


@pytest.mark.parametrize("objective", ("played_game_goal", "complete_settlement"))
def test_restart_without_match_exact_exports_both_locales_and_no_dead_links(
    localized_server, monkeypatch, objective,
):
    browser, path, page = open_alex(localized_server)
    app = localized_server.app_context
    original = path.read_bytes()
    response = browser.submit(form(page), objective=objective, requested_worlds="2",
                              analysis_matadors="1")
    assert response[0] == 303
    live = downloads(browser, follow(browser, response))
    entry, = archive_store(app).snapshot().manifest.evidence
    captured = archive_store(app).read_evidence(entry.identity)
    route = saved_route(browser.page(SAVED_MATCH_ROUTE))
    # The one-byte Windows coordination lease may still be held through delivery.
    before = {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")}
    localized_server.app_context = AppWebContextV1.create(app.managed_home)
    browser = Browser(localized_server)
    def forbidden(*a, **kw):
        pytest.fail("Passive saved access executed or wrote archive data")
    monkeypatch.setattr(application_execution, "execute_application_invocation", forbidden)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", forbidden)
    monkeypatch.setattr(io, "write_temporary", forbidden)
    assert browser.request("GET", route)[0] == 409
    route = saved_route(browser.page(SAVED_MATCH_ROUTE))
    page = browser.page(route)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert text(locale, "saved_analysis.historical") in unescape(page)
        assert text(locale, "saved_analysis.method.whole_game_rollout") in unescape(page)
        assert text(locale, "rollout.objective." + objective) in unescape(page)
        assert '/learning/debrief/from/' not in page and '/matches/api/v1/reports/' not in page
        assert "strategy-source.json" not in page
        for kind in ("request", "result"):
            response = browser.request("GET", route + "/" + kind + ".json")
            assert response[0] == 200 and response[2] == captured.download(kind)[1]
            assert response[2] in live.values()
    assert browser.request("GET", route + "/strategy-source.json")[0] == 409
    assert localized_server.app_context.managed_stateful.active_match is None
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert path.read_bytes() == original
    assert archive_store(localized_server.app_context).read_evidence(entry.identity) == captured


def test_native_incomplete_save_only_retry_keeps_selected_complete(localized_server, monkeypatch):
    browser, path, page = open_alex(localized_server)
    app = localized_server.app_context
    page = follow(browser, browser.submit(form(page), objective="played_game_goal",
                                         requested_worlds="1"))
    active = app.managed_stateful.active_match
    complete, = active.capture.report_store.list()
    prior = downloads(browser, page)
    counts = Counter()
    execute = application_execution.execute_application_invocation
    evaluate = workflow.evaluate_whole_game_rollout_v1
    write = io.write_temporary
    failing = True
    def counted(*args, **kwargs):
        counts["execute"] += 1
        return execute(*args, **kwargs)
    def interrupted(directory, raw):
        if directory.name == "reports" and failing:
            counts["failure"] += 1
            raise OSError("Controlled pre-publication write failure")
        counts[directory.name] += 1
        return write(directory, raw)
    monkeypatch.setattr(application_execution, "execute_application_invocation", counted)
    monkeypatch.setattr(io, "write_temporary", interrupted)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1",
                        lambda view, settings: evaluate(view, settings, cancelled=lambda: True))
    response = browser.submit(form(page), random_seed="1")
    assert response[0] == 400
    page = response[2].decode()
    assert text("en", "saved_analysis.rollout.unsaved") in unescape(page)
    attempt = active.rollout_notice[0]
    assert active.capture.report_store.get(attempt.report_id) is None
    retry = Forms(page).find("/matches/retry-saving")
    assert downloads(browser, page) == prior
    assert counts == {"execute": 1, "failure": 1}
    failing = False
    monkeypatch.setattr(application_execution, "execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Retry executed"))
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1",
                        lambda *a, **kw: pytest.fail("Retry evaluated"))
    response = browser.submit(retry)
    assert response[0] == 303
    assert response[1]["location"] == f"/matches/reports/{complete.report_id}"
    page = follow(browser, response)
    assert text("en", "saved_analysis.rollout.saved") in unescape(page)
    assert text("en", "rollout.reason.cancelled") in unescape(page)
    assert downloads(browser, page) == prior
    assert active.capture.report_store.list() == (complete,)
    assert counts == {"execute": 1, "failure": 1, "reports": 1, "automatic-learning": 1}
    assert browser.submit(retry)[0] == 409
    store = archive_store(app)
    entry = store.snapshot().manifest.evidence[-1]
    route = SAVED_MATCH_ROUTE + "/" + app.saved_match_analyses.token(
        store.snapshot().manifest.space_id, entry)
    saved = browser.page(route)
    assert text("en", "rollout.reason.cancelled") in unescape(saved)
    assert store.read_evidence(entry.identity).report is not complete
    assert browser.request("GET", route + "/result.json")[2] == (
        store.read_evidence(entry.identity).download("result")[1])


@pytest.mark.parametrize("resource", ("", "/request.json", "/result.json"))
@pytest.mark.parametrize("change", ("owner", "dependency", "recording"))
def test_rollout_archive_final_delivery_and_old_source(
    localized_server, monkeypatch, resource, change,
):
    from test_match_evidence_retention import change_source

    from skatmind.app_web.saved_match_analyses import SavedMatchAnalyses
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    browser, path, page = open_alex(localized_server)
    follow(browser, browser.submit(form(page), objective="played_game_goal", requested_worlds="1"))
    app = localized_server.app_context
    route = saved_route(browser.page(SAVED_MATCH_ROUTE))
    store = archive_store(app)
    source = store.snapshot().manifest.sources[0].object_ref
    real = Handler._send_bytes
    fired = False
    def send(handler, status, content, **kwargs):
        nonlocal fired
        if not fired and handler.path == route + resource:
            fired = True
            if change == "owner":
                app.saved_match_analyses = SavedMatchAnalyses()
            elif change == "dependency":
                (store.root / source.area / (source.fingerprint + ".json")).write_bytes(b"{}")
            else:
                change_source(app.managed_stateful.active_match)
        return real(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", send)
    response = browser.request("GET", route + resource)
    assert fired and response[0] == (200 if change == "recording" else 409)


@pytest.mark.parametrize("change", ("owner", "source", "selection", "attempt", "archive_owner"))
def test_incomplete_receipt_final_delivery_uses_attempt_owner(
    localized_server, monkeypatch, change,
):
    from test_match_rollout_retention import mutate

    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(form(page), objective="played_game_goal",
                                         requested_worlds="1"))
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    evaluate = workflow.evaluate_whole_game_rollout_v1
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1",
                        lambda view, settings: evaluate(view, settings, cancelled=lambda: True))
    monkeypatch.setattr(archive_store(app), "publish_object", lambda *a, **kw: "conflict")
    real = Handler._send_bytes
    fired = False
    def send(handler, status, content, **kwargs):
        nonlocal fired
        if not fired and handler.path == "/matches/review-whole-game" and status == 400:
            fired = True
            mutate(app, active, change)
        return real(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", send)
    response = browser.submit(form(page), random_seed="1")
    assert fired and response[0] == 409
    assert text("en", "saved_analysis.rollout.unsaved") not in unescape(response[2].decode())
