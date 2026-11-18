"""Real authenticated native Match submissions over disposable synthetic recordings."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_match_rollout_retention import rollout_probe as _rollout_probe
from test_match_rollout_review import alex_workspace, metrics
from test_recorded_review_navigation import chooser_form, home_chooser
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.match_rollout_frontend as frontend
from skatmind.api.v1 import execute, parse_request
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.stateful_localization import text
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1

ROUTE = "/matches/review-whole-game"


@pytest.fixture
def localized_server(tmp_path):
    for server in _localized_server.__wrapped__(tmp_path):
        # Track request threads so concurrency tests can join handlers before
        # inspecting persistent evidence, not just wait for the client response.
        server.daemon_threads = False
        yield server


@pytest.fixture
def rollout_probe(monkeypatch):
    yield from _rollout_probe.__wrapped__(monkeypatch)


def open_alex(server, *, count=3, bid=18):
    workspace = alex_workspace(count=count, bid=bid)
    path = server.app_context.managed_stateful.root("matches") / "synthetic-288.json"
    saved = save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(
        workspace), expected_content_fingerprint=None)
    assert saved.status == "saved"
    browser = Browser(server)
    follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    page = browser.page("/matches/review/2")
    return browser, path, page


def form(page):
    return Forms(page).find(ROUTE)


def downloads(browser, page):
    routes = re.findall(r'href="(/matches/api/v1/reports/[^\"]+)"', page)
    return {route: browser.request("GET", route)[2] for route in routes}


def test_real_native_root_supplement_result_and_matched_downloads(localized_server, monkeypatch):
    browser, path, page = open_alex(localized_server)
    before = path.read_bytes()
    calls = []
    real = frontend.execute_match_decision_analysis_v1
    def counted(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    monkeypatch.setattr(frontend, "execute_match_decision_analysis_v1", counted)
    values = form(page)["values"]
    assert values["decision_index"] == "3"
    assert values["objective"] == "complete_settlement"
    assert values["requested_worlds"] == "100" and values["random_seed"] == "0"
    assert values["analysis_matadors"] == "" and "analysis_bid_value" not in values
    assert not set(values) & {"immediate_sample_count", "use_profile_presets", "search_random_seed"}
    nodes = Hierarchy(page).nodes
    control = next(node for node in nodes if node["attrs"].get("name") == "analysis_matadors")
    assert not any(node["tag"] == "details" for node in control["parents"])
    response = browser.submit(form(page), settings_mode="custom", requested_worlds="2")
    assert response[0] == 400
    page = response[2].decode()
    assert 'aria-invalid="true"' in page and not calls
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert form(page)["values"]["requested_worlds"] == "2"
        assert text(locale, "match_rollout.source") in unescape(page)
    response = browser.submit(form(page), analysis_matadors="1")
    assert response[0] == 303, response[2].decode()
    page = follow(browser, response)
    assert len(calls) == 1
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    root = report.value.request.to_dict()["document"]
    assert root["game_declaration"]["bid_value"] == 18
    assert root["whole_game_rollout_derivation"]["supplements"] == {"matadors": 1}
    assert report.value.result.document["whole_game_rollout_result"]["local_side"] == "defenders"
    exported = downloads(browser, page)
    assert len(exported) == 2
    request_bytes = next(content for route, content in exported.items() if "request" in route)
    result_bytes = next(content for route, content in exported.items() if "request" not in route)
    assert json.loads(request_bytes) == root
    assert json.loads(result_bytes) == report.value.result.to_dict()["document"]
    replay = execute(parse_request(json.loads(request_bytes))).result.to_dict()["document"]
    assert metrics(replay["whole_game_rollout_result"]) == metrics(
        json.loads(result_bytes)["whole_game_rollout_result"])
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert downloads(browser, page) == exported
        assert form(page)["values"]["analysis_matadors"] == "1"
        assert text(locale, "rollout.calculation_details") in page
    assert path.read_bytes() == before and len(calls) == 1


def test_invalid_attempt_keeps_report_bytes_and_scoped_choices(localized_server):
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(form(page), objective="played_game_goal",
                                         settings_mode="custom", requested_worlds="1"))
    prior = downloads(browser, page)
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    response = browser.submit(form(page), objective="complete_settlement", analysis_matadors="0")
    assert response[0] == 400
    assert active.capture.report_store.list() == (report,)
    for route, content in prior.items():
        assert browser.request("GET", route)[2] == content
    page = response[2].decode()
    assert form(page)["values"]["analysis_matadors"] == "0"
    assert form(page)["values"]["objective"] == "complete_settlement"
    route = f"/matches/api/v1/reports/{report.report_id}/strategy-source.json"
    assert browser.request("GET", route)[0] == 404


@pytest.mark.parametrize("phase", ("preparation", "evaluation"))
def test_superseded_unlocked_work_cannot_publish(localized_server, rollout_probe, phase):
    browser, path, page = open_alex(localized_server)
    original = path.read_bytes()
    rollout_probe.phase = phase
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(browser.submit, form(page), objective="played_game_goal",
                            settings_mode="custom", requested_worlds="2", random_seed="7")
        try:
            assert rollout_probe.entered.wait(60)
            response = browser.submit(form(page), objective="played_game_goal",
                                      settings_mode="custom", requested_worlds="2")
            assert response[0] == 303
        finally:
            rollout_probe.release.set()
        stale = first.result()
        assert stale[0] == 409
    # The stale tab can recover through the current review without another execution.
    current_page = follow(browser, response)
    assert form(current_page)["values"]["decision_index"] == "3"
    localized_server._threads.join()
    rollout_probe.assert_cancelled()
    rollout_probe.assert_complete(0)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    reports = active.capture.report_store.list()
    assert len(reports) == 1 and reports[0].value.options.rollout_settings.random_seed == 0
    assert active.pending_evidence is None and active.rollout_notice is None
    entry, = archive_store(app).snapshot().manifest.evidence
    assert archive_store(app).read_evidence(entry.identity).report == reports[0]
    assert path.read_bytes() == original


def test_same_decision_superseded_rejection_cannot_invalidate_new_report_get(
        localized_server, rollout_probe, monkeypatch):
    from threading import Event

    import skatmind.app_web.server as server_module

    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(Forms(page).find("/matches/select-decision"),
                                         decision_index="3"))
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    original = path.read_bytes()
    source = (active.workspace, active.position_generation, active.review_decision_generation)
    rollout_probe.phase = "preparation"
    rendering, finish_render, rejection_observed = Event(), Event(), Event()
    obsolete_feedback, conflict_sent = Event(), Event()
    handler = server_module.SkatMindAppWebRequestHandlerV1
    send, retain = handler._send_text, handler._retain_form_feedback
    report_route = None

    def sent(self, status, *args, **kwargs):
        if self.command == "GET" and self.path == report_route and status == 200:
            assert self._rendered_language_source is not None
            rendering.set()
            assert finish_render.wait(60)
        result = send(self, status, *args, **kwargs)
        if self.command == "POST" and self.path == ROUTE and status == 409:
            conflict_sent.set()
            rejection_observed.set()
        return result

    def retained(self, *args, **kwargs):
        result = retain(self, *args, **kwargs)
        if self.command == "POST" and self.path == ROUTE and kwargs["status"] == 409:
            # Observe the broken path without deadlocking on its subsequent
            # rejection rendering behind the held Report GET lifecycle lock.
            obsolete_feedback.set()
            rejection_observed.set()
        return result

    monkeypatch.setattr(handler, "_send_text", sent)
    monkeypatch.setattr(handler, "_retain_form_feedback", retained)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(browser.submit, form(page), objective="played_game_goal",
                            settings_mode="custom", requested_worlds="2", random_seed="7")
        try:
            assert rollout_probe.entered.wait(60)
            first_attempt = active.rollout_attempt
            response = browser.submit(form(page), objective="played_game_goal",
                                      settings_mode="custom", requested_worlds="2", random_seed="0")
            assert response[0] == 303
            report, = active.capture.report_store.list()
            assert report.value.options.rollout_settings.random_seed == 0
            second_attempt = active.rollout_attempt
            assert second_attempt is not first_attempt
            assert source == (active.workspace, active.position_generation,
                              active.review_decision_generation)
            report_route = response[1]["location"]
            assert report_route == f"/matches/reports/{report.report_id}"
            routes = (f"/matches/api/v1/reports/{report.report_id}.json",
                      f"/matches/api/v1/reports/{report.report_id}/rollout-request.json")
            original_downloads = {}
            for route in routes:
                status, _, content = browser.request("GET", route)
                assert status == 200
                original_downloads[route] = content
            assert app.form_feedback.current("matches", active_identity=active) is None
            report_get = pool.submit(browser.request, "GET", report_route)
            assert rendering.wait(60)
            rollout_probe.release.set()
            assert rejection_observed.wait(60)
            completed_while_report_held = conflict_sent.is_set()
            if completed_while_report_held:
                assert first.result(timeout=60)[0] == 409
        finally:
            rollout_probe.release.set()
            finish_render.set()
        assert first.result(timeout=60)[0] == 409
        current = report_get.result(timeout=60)
        assert current[0] == 200
        assert completed_while_report_held
    localized_server._threads.join()
    assert not obsolete_feedback.is_set()
    assert app.form_feedback.current("matches", active_identity=active) is None
    assert active.rollout_attempt is second_attempt
    assert active.capture.report_store.list() == (report,)
    assert active.capture.report_store.list()[0] is report
    assert form(current[2].decode())["values"]["random_seed"] == "0"
    assert downloads(browser, current[2].decode()) == original_downloads
    entry, = archive_store(app).snapshot().manifest.evidence
    assert archive_store(app).read_evidence(entry.identity).report == report
    rollout_probe.assert_cancelled()
    rollout_probe.assert_complete(0)
    assert path.read_bytes() == original


def test_selected_actor_and_foreign_stale_binding_do_not_run(localized_server, monkeypatch):
    browser, path, page = open_alex(localized_server, count=30)
    stale = form(page)
    page = follow(browser, browser.request("GET", "/matches/review/2?decision_index=3"))
    assert form(page)["values"]["decision_index"] == "3"
    assert form(page)["values"]["analysis_matadors"] == ""
    calls = []
    monkeypatch.setattr(frontend, "execute_match_decision_analysis_v1",
                        lambda *args, **kwargs: calls.append(kwargs))
    assert browser.submit(stale, objective="played_game_goal")[0] == 409
    current = form(browser.page("/matches/review/2"))
    assert browser.submit(current, decision_index="2")[0] == 409
    assert browser.submit(current, expected_revision="0")[0] == 409
    assert not calls


@pytest.mark.parametrize("when", ("before", "during"))
def test_external_file_conflict_prevents_publication(localized_server, monkeypatch, when):
    from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1

    browser, path, page = open_alex(localized_server)
    active = localized_server.app_context.managed_stateful.active_match
    changed = mark_match_workspace_passed_deal_v1(active.workspace, match_position=3,
        expected_revision=active.workspace.revision, game_timecode=None).workspace
    def change_file():
        saved = save_match_workspace_file_v1(path,
            build_match_workspace_persistence_document_v1(changed),
            expected_content_fingerprint=active.capture.content_fingerprint)
        assert saved.status == "saved"
    real = frontend.execute_match_decision_analysis_v1
    calls = []
    def run(*args, **kwargs):
        calls.append(1)
        result = real(*args, **kwargs)
        change_file()
        return result
    monkeypatch.setattr(frontend, "execute_match_decision_analysis_v1", run)
    if when == "before":
        change_file()
    response = browser.submit(form(page), settings_mode="custom", objective="played_game_goal",
                              requested_worlds="1")
    assert response[0] == 409 and not active.capture.report_store.list()
    assert len(calls) == (0 if when == "before" else 1)


def test_timeout_retains_completed_bytes_and_names_attempt_separately(
    localized_server, monkeypatch,
):
    import skatmind.recommendation_workflow as workflow

    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(form(page), objective="played_game_goal",
                                         settings_mode="custom", requested_worlds="1"))
    prior = downloads(browser, page)
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    real = workflow.evaluate_whole_game_rollout_v1
    def timed(view, settings, *, cancelled=None):
        ticks = iter(range(0, 1_000_000, 100))
        return real(view, settings, clock=lambda: next(ticks), cancelled=cancelled)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", timed)
    response = browser.submit(form(page), objective="complete_settlement", analysis_matadors="1")
    assert response[0] == 400
    page = response[2].decode()
    assert active.capture.report_store.list() == (report,)
    assert active.rollout_notice[0].value.result.document["whole_game_rollout_result"][
        "status"] == "timeout"
    assert downloads(browser, page) == prior
    assert text("en", "rollout.retained") in unescape(page)
    assert form(page)["values"]["objective"] == "complete_settlement"


def test_failed_execution_keeps_previous_report(localized_server, monkeypatch):
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(form(page), objective="played_game_goal",
                                         settings_mode="custom", requested_worlds="1"))
    prior = downloads(browser, page)
    def failed(*args, **kwargs):
        raise ValueError("Synthetic execution failure")
    monkeypatch.setattr(frontend, "execute_match_decision_analysis_v1", failed)
    response = browser.submit(form(page))
    assert response[0] == 400
    assert text("en", "validation.rollout.execution_failed") in unescape(response[2].decode())
    for route, content in prior.items():
        assert browser.request("GET", route)[2] == content


def test_exact_tied_set_and_actual_membership_use_shared_renderer(localized_server, monkeypatch):
    from dataclasses import replace

    import skatmind.recommendation_workflow as workflow

    real = workflow.evaluate_whole_game_rollout_v1
    def tied(view, settings, *, cancelled=None):
        result = real(view, settings, cancelled=cancelled)
        # A deliberately synthetic retained full tie exercises presentation, not
        # a claim about which card wins the independent acceptance fixture.
        candidates = tuple(replace(result.candidates[0], card=row.card)
                           for row in result.candidates)
        cards = tuple(row.card for row in candidates)
        return replace(result, candidates=candidates, ranked_cards=cards,
                       tied_best_cards=cards, recommended_card=cards[0])
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", tied)
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(form(page), settings_mode="custom", requested_worlds="1",
                                         analysis_matadors="1"))
    prior = downloads(browser, page)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        recommendation = page.split('id="match-rollout-result-section-2"', 1)[1].split(
            'id="match-rollout-result-section-3"', 1)[0]
        for card in ("CK", "C9", "C7"):
            assert f"({card})" in recommendation
        assert text(locale, "rollout.comparison.equal_complete_objective") in unescape(page)
        assert downloads(browser, page) == prior


def test_known_value_injection_and_explicit_objective_switch(localized_server):
    browser, path, page = open_alex(localized_server)
    assert browser.submit(form(page), analysis_bid_value="18", analysis_matadors="1")[0] == 400
    active = localized_server.app_context.managed_stateful.active_match
    assert not active.capture.report_store.list()
    page = browser.page("/matches/review/2")
    response = browser.submit(form(page), objective="played_game_goal",
                              settings_mode="custom", requested_worlds="1",
                              analysis_matadors="not a number")
    assert response[0] == 303
    report, = localized_server.app_context.managed_stateful.active_match.capture.report_store.list()
    assert not report.value.options.settlement_supplements
    assert report.value.request.document["game_declaration"]["matadors"] is None


def test_invalid_new_attempt_supersedes_old_inflight_work(localized_server, rollout_probe):
    browser, path, page = open_alex(localized_server)
    original = path.read_bytes()
    page = follow(browser, browser.submit(form(page), objective="played_game_goal",
                                         settings_mode="custom", requested_worlds="2"))
    prior = downloads(browser, page)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    report, = active.capture.report_store.list()
    store = archive_store(app)
    archive_bytes = {path: path.read_bytes() for path in store.root.rglob("*.json")}
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(browser.submit, form(page), objective="played_game_goal",
                            settings_mode="custom", requested_worlds="2", random_seed="7")
        try:
            assert rollout_probe.entered.wait(60)
            assert browser.submit(form(page), objective="complete_settlement",
                                  analysis_matadors="")[0] == 400
        finally:
            rollout_probe.release.set()
        assert first.result()[0] == 409
    rollout_probe.assert_cancelled()
    feedback = app.form_feedback.current("matches", active_identity=active)
    assert feedback.form_key == "match.review_whole_game"
    assert feedback.safe_visible_values.singular("objective") == "complete_settlement"
    assert feedback.safe_visible_values.singular("random_seed") == "0"
    assert feedback.safe_visible_values.singular("analysis_matadors") == ""
    assert active.capture.report_store.list() == (report,)
    assert active.pending_evidence is None and active.rollout_notice is None
    assert downloads(browser, browser.page(f"/matches/reports/{report.report_id}")) == prior
    localized_server._threads.join()
    assert {path: path.read_bytes() for path in store.root.rglob("*.json")} == archive_bytes
    assert path.read_bytes() == original


def test_unchanged_passive_reads_and_language_do_not_cancel(localized_server, rollout_probe):
    browser, path, page = open_alex(localized_server)
    original = path.read_bytes()
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(browser.submit, form(page), objective="played_game_goal",
                             settings_mode="custom", requested_worlds="2", random_seed="7")
        try:
            assert rollout_probe.entered.wait(60)
            browser.page("/")
            page = browser.page("/matches/review/2")
            follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                            language="de"))
            assert rollout_probe.predicates[7]() is False
        finally:
            rollout_probe.release.set()
        assert future.result()[0] == 303
    localized_server._threads.join()
    rollout_probe.assert_complete(7)
    app = localized_server.app_context
    assert len(archive_store(app).snapshot().manifest.evidence) == 1
    assert path.read_bytes() == original


def test_both_missing_inputs_stay_visible_and_values_survive_rejection(localized_server):
    browser, path, page = open_alex(localized_server, bid=None)
    before = path.read_bytes()
    assert form(page)["values"]["analysis_bid_value"] == ""
    assert form(page)["values"]["analysis_matadors"] == ""
    response = browser.submit(form(page), settings_mode="custom", requested_worlds="1",
                              analysis_bid_value="18")
    assert response[0] == 400
    page = response[2].decode()
    assert form(page)["values"]["analysis_bid_value"] == "18"
    assert text("en", "validation.rollout.required_matadors") in unescape(page)
    page = follow(browser, browser.submit(form(page), analysis_matadors="1"))
    report, = localized_server.app_context.managed_stateful.active_match.capture.report_store.list()
    assert report.value.options.settlement_supplements == {"bid_value": 18, "matadors": 1}
    assert path.read_bytes() == before


def test_retained_downloads_ignore_current_game_then_invalidate_on_reload(localized_server):
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(form(page), settings_mode="custom", requested_worlds="1",
                                         analysis_matadors="1"))
    prior = downloads(browser, page)
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    browser.page("/matches/review/1")
    for route, content in prior.items():
        assert browser.request("GET", route)[2] == content
    page = browser.page(f"/matches/reports/{report.report_id}")
    assert form(page)["values"]["match_position"] == "2"
    assert report.value.request.document["current_trick"] == ("CQ", "CA")
    reload_form = Forms(page).find("/matches/api/v1/reload")
    assert browser.submit(reload_form)[0] == 303
    for route in prior:
        assert browser.request("GET", route)[0] == 404


def test_decision_selector_without_active_match_has_normal_missing_response(localized_server):
    browser = Browser(localized_server)
    assert browser.request("GET", "/matches/review/2?decision_index=3")[0] == 404
