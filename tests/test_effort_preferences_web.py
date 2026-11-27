"""Native effort forms over disposable recordings, including a cold app context."""

import os
from contextlib import contextmanager

import pytest
from test_accounting_web import activate_session, game_form, open_form, start
from test_event_context_web import native_submit
from test_frontend_language_switching import localized_server
from test_language_switch_context import known_players
from test_match_game_navigation_web import create_empty
from test_match_live_advice import operation
from test_match_recording_recovery_web import follow
from test_match_rollout_web import open_alex
from test_session_recorded_review_web import Browser, Forms
from whole_game_review_fixtures import activate_ten_decisions

from skatmind.app_web.frontend_profile_operations import FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE
from skatmind.app_web.match_live_advice import MATCH_LIVE_ROUTES
from skatmind.app_web.session_live_advice import LIVE_ROUTES
from skatmind.app_web.stateful_localization import text

serve = contextmanager(localized_server.__wrapped__)


def submit(browser, page, action, **values):
    return follow(browser, browser.submit(Forms(page).find(action), **values))


def preferences(browser, **values):
    return submit(browser, browser.page("/settings"), FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
                  **values)


def start_live(browser, page, routes, expected):
    assert not any(f["action"] == routes[1] for f in Forms(page).forms)
    page = submit(browser, page, routes[0])
    fields = Forms(page).find(routes[1])["values"]
    assert fields["analysis_effort"] == expected and "apply_block" not in fields
    return page


@pytest.fixture(autouse=True)
def no_work(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Passive navigation, preferences and incomplete games must not evaluate.")

    for target in ("execution.execute", "session_live_advice.evaluate_live_position",
                   "match_live_advice.evaluate_live_position",
                   "automatic_learning_controller.AutomaticLearningController.update"):
        monkeypatch.setattr("skatmind.app_web." + target, forbidden)


def test_default_settings_restart_and_fresh_forms(tmp_path):
    with serve(tmp_path) as server:
        browser = Browser(server)
        settings = Forms(browser.page("/settings")).find(FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE)
        assert (settings["values"]["live_effort"], settings["values"]["analysis_effort"]) == (
            "quick", "standard")
        create_empty(browser, "de")
        known_players(browser)
        profile = server.app_context.frontend_profile.document
        settings = browser.page("/settings")
        for key in ("live_effort", "analysis_effort"):
            assert text("de", "settings.preferences." + key) in settings
        old = Forms(settings).find(FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE)
        preferences(browser, live_effort="standard", analysis_effort="more_time")
        assert browser.submit(old)[0] == 409
    with serve(tmp_path) as server:
        app = server.app_context
        saved = app.frontend_profile.document
        assert saved.language == profile.language == "de"
        assert saved.known_players == profile.known_players and saved.known_players
        assert saved.managed_item_display_labels == profile.managed_item_display_labels
        browser = Browser(server)
        page = submit(browser, browser.page("/settings"), "/actions/profile/language",
                      language="en")
        for key, expected in (("analysis_effort", "more_time"), ("live_effort", "standard")):
            assert text("en", "settings.preferences." + key) in page
            assert Forms(page).find(FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE)["values"][key] == (
                expected)
        assert Forms(browser.page("/analyze")).find("/actions/analyze/run-guided")[
            "values"]["analysis_effort"] == "more_time"
        submit(browser, browser.page("/review"), "/actions/review/start")
        draft = app.review_state.draft
        assert draft.analysis_form_values.singular("analysis_effort") == "more_time"
        activate_ten_decisions(server)
        for route, action in (("/sessions/decisions", "/sessions/review-whole-game"),
                              ("/sessions/game-review", "/sessions/game-review/start")):
            fields = Forms(browser.page(route)).find(action)["values"]
            assert fields["analysis_effort"] == "more_time"


def test_match_analysis_defaults_and_retained_form(localized_server):
    browser, path, page = open_alex(localized_server)
    original = path.read_bytes()
    for effort in ("quick", "more_time"):
        preferences(browser, analysis_effort=effort)
        for route, action in (("/matches/review/2", "/matches/review-whole-game"),
                              ("/matches/whole-review/game/2", "/matches/whole-review/start"),
                              ("/matches/whole-review/match", "/matches/whole-review/start")):
            form = Forms(browser.page(route)).find(action)
            assert form["values"]["analysis_effort"] == effort
    # The original native form remains authoritative after a defaults save.
    retry = Forms(page).find("/matches/review-whole-game")
    rejected = browser.submit(retry, settings_mode="custom", requested_worlds="invalid")
    assert rejected[0] == 400
    values = Forms(rejected[2].decode()).find(retry["action"])["values"]
    assert values["analysis_effort"] == "standard" and values["settings_mode"] == "custom"
    assert path.read_bytes() == original


def test_standalone_game_choice_and_active_effort_ignore_new_global_default(tmp_path):
    routes = LIVE_ROUTES
    with serve(tmp_path) as server:
        browser = Browser(server)
        active = activate_session(server.app_context)
        preferences(browser, live_effort="more_time")
        page = start_live(browser, browser.page(), routes, "more_time")
        original = active.path.read_bytes()
        assert 'name="apply_block"' not in page
        assert browser.submit(Forms(page).find(routes[1]), apply_block="on")[0] == 409
        preferences(browser, live_effort="standard")
        assert active.live.effort == "more_time"
        submit(browser, browser.page(), routes[1], analysis_effort="quick")
        assert active.path.read_bytes() == original
    with serve(tmp_path) as server:
        browser = Browser(server)
        page = submit(browser, browser.page("/sessions"), "/sessions/open")
        start_live(browser, page, routes, "quick")


def test_match_block_and_game_choices_survive_edits_restart_and_reject_copy(tmp_path):
    routes = MATCH_LIVE_ROUTES
    with serve(tmp_path) as server:
        browser = Browser(server)
        create_empty(browser, "en")
        preferences(browser, live_effort="standard")
        page = operation(browser, browser.page("/matches/position/1"), "start_game")
        page = start_live(browser, page, routes, "standard")
        assert text("en", "analysis.live.apply_match") in page
        same_effort = Forms(page).find(routes[1])
        page = submit(browser, page, routes[1], analysis_effort="standard")
        assert browser.submit(same_effort, apply_block="on")[0] == 409
        submit(browser, page, routes[1], analysis_effort="quick")
        page = operation(browser, browser.page("/matches/position/2"), "start_game")
        page = start_live(browser, page, routes, "standard")
        submit(browser, page, routes[1], analysis_effort="more_time", apply_block="on")
    with serve(tmp_path) as server:
        browser = Browser(server)
        submit(browser, browser.page("/matches"), "/matches/open")
        page = operation(browser, browser.page("/matches/position/3"), "start_game")
        page = start_live(browser, page, routes, "more_time")
        page = submit(browser, page, "/actions/profile/language", language="de")
        assert text("de", "analysis.live.apply_match") in page
        submit(browser, page, routes[1], analysis_effort="quick", apply_block="on")
        page = operation(browser, browser.page("/matches/position/4"), "start_game")
        start_live(browser, page, routes, "quick")
        for position, expected in ((1, "quick"), (2, "more_time")):
            page = start_live(browser, browser.page(f"/matches/position/{position}"), routes,
                              expected)
        # Reusing a cleared slot starts a new game, even with the same generated game ID.
        page = operation(browser, page, "clear_position", confirm_clear="on")
        page = operation(browser, page, "start_game")
        page = start_live(browser, page, routes, "quick")
        active = server.app_context.managed_stateful.active_match
        path = active.path
        copy = path.with_suffix(".copy")
        copy.write_bytes(path.read_bytes())
        os.replace(copy, path)
        assert browser.submit(Forms(page).find(routes[1]), apply_block="on")[0] == 409
        page = submit(browser, browser.page("/matches/position/2"), "/matches/api/v1/reload")
        start_live(browser, page, routes, "standard")
        create_empty(browser, "en")  # Same display name; independent recording.
        page = operation(browser, browser.page("/matches/position/1"), "start_game")
        start_live(browser, page, routes, "standard")


def test_cent_round_scope_restart_and_replacement(tmp_path):
    routes = LIVE_ROUTES
    with serve(tmp_path) as server:
        browser = Browser(server)
        page = start_live(browser, start(browser), routes, "quick")
        assert text("en", "analysis.live.apply_cent") in page
        page = submit(browser, page, routes[1], analysis_effort="more_time", apply_block="on")
        page = follow(browser, native_submit(browser, game_form(page, 1), game_status="passed"))
        page = follow(browser, native_submit(browser, open_form(page, 2)))
        page = start_live(browser, page, routes, "more_time")
        submit(browser, page, routes[1], analysis_effort="standard")
    with serve(tmp_path) as server:
        browser = Browser(server)
        page = submit(browser, browser.page("/cent"), "/cent/resume")
        page = follow(browser, native_submit(browser, open_form(page, 2)))
        page = start_live(browser, page, routes, "standard")
        page = submit(browser, page, "/actions/profile/language", language="de")
        assert text("de", "analysis.live.apply_cent") in page
        page = follow(browser, native_submit(browser, game_form(page, 2), game_status="passed"))
        page = follow(browser, native_submit(browser, open_form(page, 3)))
        page = start_live(browser, page, routes, "more_time")
        active = server.app_context.managed_stateful.active_session
        duplicate = active.path.with_name("duplicate.json")
        duplicate.write_bytes(active.path.read_bytes())
        assert browser.submit(Forms(page).find(routes[1]), apply_block="on")[0] == 409
        duplicate.rename(duplicate.with_suffix(".bak"))
        page = follow(browser, native_submit(browser, game_form(page, 3), game_status="passed"))
        page = submit(browser, page, "/sessions/accounting/lifecycle")
        page = submit(browser, page, "/sessions/accounting/next")
        page = start_live(browser, page, routes, "quick")
        active = server.app_context.managed_stateful.active_session
        foreign = active.path.with_suffix(".copy")
        foreign.write_bytes(active.path.read_bytes())
        os.replace(foreign, active.path)
        assert browser.submit(Forms(page).find(routes[1]), apply_block="on")[0] == 409
