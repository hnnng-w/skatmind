"""A direct result owns its recording return independently of any batch checkpoint."""

import re
from contextlib import contextmanager
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_match_rollout_web import form, open_alex
from test_session_recorded_review_web import Browser, Forms, record_live_game

import skatmind.recommendation_workflow as workflow
from skatmind.app_web.saved_match_analyses import SELECTION_ROUTE, archive_store


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@contextmanager
def direct_result(server, family):
    app = server.app_context
    if family == "sessions":
        browser = Browser(server)
        record_live_game(browser, play_count=6)
        path = app.managed_stateful.active_session.path
        selections = re.findall(r'href="(/sessions/decisions/[0-9a-f]{64})"',
                                browser.page("/sessions/decisions"))
        first, fifth = selections
        selected = browser.page(fifth)
        native = Forms(selected).find("/sessions/review-whole-game")
    else:
        browser, path, selected = open_alex(server)
        first = fifth = None
        native = form(selected)
    before = path.read_bytes()
    with patch.object(workflow, "evaluate_whole_game_rollout_v1",
                      wraps=workflow.evaluate_whole_game_rollout_v1) as evaluate:
        status, headers, _ = browser.submit(native, objective="played_game_goal",
                                            analysis_effort="quick")
        assert status == 303 and evaluate.call_count == 1
        route = headers["location"]
        if fifth:
            assert route == fifth + "#session-rollout-result"
        page = browser.page(urlsplit(route).path)
        selection = Forms(page).find(SELECTION_ROUTE)
        token = selection["values"]["analysis"]
        assert selection["values"]["origin"].startswith("direct:")
        original = f"/{family}/saved-analyses/{token}"
        def downloads():
            result = []
            for kind in ("request", "result"):
                status, _, raw = browser.request("GET", f"{original}/{kind}.json")
                assert status == 200
                result.append(raw)
            return result
        saved = downloads()
        yield browser, route, first, fifth, path
        assert saved == downloads() and path.read_bytes() == before and evaluate.call_count == 1


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_direct_learning_choice_round_trip_replaced_file_and_exact_return(localized_server, family):
    app = localized_server.app_context
    with direct_result(localized_server, family) as (browser, route, first, fifth, path):
        store = archive_store(app)
        entry, = store.snapshot().manifest.evidence
        page = browser.page(urlsplit(route).path)
        for language, membership in (("de", (entry.identity,)), ("en", ())):
            page = switch(browser, page, language)
            response = browser.submit(Forms(page).find(SELECTION_ROUTE))
            assert response[1].get("location") == route
            page = follow(browser, response)
            assert f'lang="{language}"' in page
            assert store.snapshot().manifest.excluded_analysis_ids == membership
            if fifth:
                assert f'href="{fifth}#recorded-decision-5"' in page
                label = re.search(r'<p id="recorded-decision-5"[^>]*>(.*?)</p>', page)[1]
                selected = browser.page(first)
                assert 'id="recorded-decision-1"' in selected
                assert 'id="recorded-decision-5"' not in selected
                assert '</strong><br>' + label + '</p>' in selected
                target = re.search(r'class="recorded-review-source".*?href="([^"]+)"',
                                   selected, re.S)[1]
                assert target == fifth + "#recorded-decision-5"
                page = browser.page(urlsplit(target).path)
                assert 'id="recorded-decision-5"' in page
            else:
                assert 'href="/matches/position/2#match-recording"' in page
                assert 'id="match-recording"' in browser.page("/matches/position/2")
                page = browser.page(route)
        stale = Forms(page).find(SELECTION_ROUTE)
        before = store.snapshot().manifest
        for invalid in ("direct:" + "0" * 64, "/matches/review/1"):
            assert browser.submit(stale, origin=invalid)[0] == 409
        copy = path.with_suffix(".copy")
        copy.write_bytes(path.read_bytes())
        validate = store._validate_update
        def replace_after_validation(*args):
            admitted = validate(*args)
            copy.replace(path)
            return admitted
        with patch.object(store, "_validate_update", replace_after_validation):
            assert browser.submit(stale)[0] == 409
        assert not copy.exists()
        assert store.snapshot().manifest == before
        if first:
            from test_unified_local_app_managed_items import _save_session
            _save_session(path.with_name("foreign.json"), session_id="other-session")
            previous = app.managed_stateful.active_session
        else:
            from test_unified_local_app_managed_items import _save_match
            previous = app.managed_stateful.active_match
            _save_match(path.with_name("foreign.json"))
        forms = Forms(browser.page("/" + family)).forms
        follow(browser, browser.submit(next(f for f in forms if f["action"] == f"/{family}/open"
                                            and f["values"]["handle"] != previous.handle)))
        assert browser.submit(stale)[0] == 409 and store.snapshot().manifest == before
