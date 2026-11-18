"""Complete-hand facts, original result preservation and fresh native delivery."""

from dataclasses import replace
from html import unescape

import pytest
from test_analysis_controls_web import last_match
from test_frontend_language_switching import localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_session_recorded_review_web import Browser, Forms
from whole_game_review_fixtures import activate_ten_decisions, ten_decision_document

import skatmind.api.v1.session as session_api
from skatmind.api.v1 import parse_request
from skatmind.app_web.forced_card_guidance import forced_card_guidance
from skatmind.app_web.session_frontend import import_guided_session_v1
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.errors import SkatMindValidationError
from skatmind.session_history import build_session_state_from_accepted_prefix_v1

__all__ = ["localized_server"]


def current_session(server):
    document = ten_decision_document(bid_value=18)
    prefix = build_session_state_from_accepted_prefix_v1(document.state,
        target_revision=document.decision_checkpoints[-1].source_revision)
    active = import_guided_session_v1(server.app_context.managed_stateful.root("sessions"),
        handle="a" * 64,
        document=session_api.build_session_persistence_document(prefix).value.to_dict())
    server.app_context.managed_stateful.activate_session(active)
    return active


@pytest.fixture(scope="module")
def requests():
    return tuple(row.request for row in ten_decision_document(bid_value=18).decision_checkpoints)


def test_complete_legal_set_and_invalid_unknown_opponent_or_finished_inputs(requests):
    assert forced_card_guidance(requests[-1]).card == "S10"
    assert forced_card_guidance(requests[-2]) is None
    multiple = requests[-2].to_dict()["document"]
    assert forced_card_guidance(parse_request({**multiple,
        "legal_cards": [multiple["hand"][0]]})) is None
    opening = requests[0].to_dict()["document"]
    assert forced_card_guidance(parse_request({**opening, "hand": opening["hand"][:1]})) is None
    assert forced_card_guidance(parse_request({**opening,
        "next_player": "left", "trick_leader": "left"})) is None
    root = requests[-1].to_dict()["document"]
    for changed in ({"hand": []}, {"hand": ["S10", "S10"]}, {"hand": None},
                    {"hand": ["S10"], "left_hand_size": 10},
                    {"next_player": "left"}):
        # Invalid/filtered observations can never become a complete legal hand.
        try:
            result = forced_card_guidance(parse_request({**root, **changed}))
        except (ValueError, SkatMindValidationError):
            continue
        assert result is None, changed


@pytest.mark.parametrize("family", ("current", "recorded", "match_rollout", "match_immediate"))
def test_native_forced_advice_is_localized_zero_analysis_and_keeps_originals(
    localized_server, monkeypatch, family,
):
    from test_automatic_match_learning_evidence import forbid_execution

    app = localized_server.app_context
    if family.startswith("match"):
        browser, path, page = last_match(localized_server)
        active = app.managed_stateful.active_match
        def native(page):
            return (Forms(page).find("/matches/review-whole-game") if family == "match_rollout"
                    else operation_form(page, "analyze_decision"))
        route, card = "/matches/review/2", "CK"
        custom = {"requested_worlds": "1", "objective": "played_game_goal"} if family == (
            "match_rollout") else {"immediate_sample_count": "1"}
    else:
        active = (current_session(localized_server) if family == "current" else
                  activate_ten_decisions(localized_server, bid_value=18))
        browser, path, route, card = (Browser(localized_server), active.path,
                                     "/sessions/current", "S10")
        page = browser.page(route)
        def native(page):
            return (Forms(page).find("/sessions/analyze") if family == "current" else
                    Forms(page).find("/sessions/review-whole-game", index=9))
        custom = {"sample_count": "1"} if family == "current" else {
            "requested_worlds": "1", "objective": "played_game_goal"}
    # Explicit custom analysis still evaluates the sole Card and keeps its real output.
    response = browser.submit(native(page), settings_mode="custom", **custom)
    assert response[0] == 303
    page = follow(browser, response)
    if family.startswith("match"):
        retained = active.capture.report_store.list()
    else:
        retained = (active.execution, active.rollout_execution)
    before = path.read_bytes()
    archive = app.saved_match_analyses.store
    archive_before = None if archive is None else archive.snapshot().manifest
    forbid_execution(monkeypatch)
    import skatmind.hidden_card_inference as inference
    import skatmind.simulation as simulation
    def forbidden(*args, **kwargs):
        pytest.fail("Rule-only guidance must not build inference or sample hidden cards")
    for module, names in ((inference, ("build_hidden_card_inference_model",
                                      "sample_compatible_hidden_world")),
                          (simulation, ("build_hidden_card_inference_model",
                                        "generate_sampled_hidden_state"))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    for locale in ("de", "en"):
        page = browser.page(route)
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                             language=locale))
        response = browser.submit(native(page), settings_mode="ordinary", analysis_effort="quick")
        assert response[0] == 200
        body = unescape(response[2].decode())
        assert text(locale, "analysis.forced_card", card=card_name(locale, card)) in body
        assert text(locale, "analysis.forced_card_help") in body
        assert "100%" not in body and "100 %" not in body
        assert "analysis_report" not in body and 'id="forced-card-guidance"' in body
        assert path.read_bytes() == before
        assert (active.capture.report_store.list() if family.startswith("match") else
                (active.execution, active.rollout_execution)) == retained
    assert (None if archive is None else archive.snapshot().manifest) == archive_before


@pytest.mark.parametrize("family", ("current", "recorded", "match"))
@pytest.mark.parametrize("when", ("before_post", "at_headers"))
def test_hint_rejects_changed_recording_owner_or_selection(
    localized_server, monkeypatch, family, when,
):
    from test_automatic_match_learning_evidence import forbid_execution

    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler

    app = localized_server.app_context
    if family == "match":
        browser, _path, page = last_match(localized_server)
        active = app.managed_stateful.active_match
        form = Forms(page).find("/matches/review-whole-game")
        def change():
            active.review_decision_generation += 1
    else:
        active = current_session(localized_server) if family == "current" else (
            activate_ten_decisions(localized_server, bid_value=18))
        browser = Browser(localized_server)
        form = (Forms(browser.page()).find("/sessions/analyze") if family == "current" else
                Forms(browser.page()).find("/sessions/review-whole-game", index=9))
        def change():
            active.document = replace(active.document, state=replace(active.state,
                revision=active.state.revision)) if when == "at_headers" else active.document
            active.generation += 1
            if when == "before_post":
                active.path.write_bytes(b"{")
    forbid_execution(monkeypatch)
    if when == "before_post":
        change()
    else:
        original = Handler._send_bytes
        def send(handler, status, content, **kwargs):
            if b'id="forced-card-guidance"' in content:
                change()
            return original(handler, status, content, **kwargs)
        monkeypatch.setattr(Handler, "_send_bytes", send)
    response = browser.submit(form, settings_mode="ordinary")
    assert response[0] in (400, 409)
    assert b'id="forced-card-guidance"' not in response[2]


def test_guided_ordinary_hint_keeps_custom_downloads_and_survives_language_return(
    localized_server, requests, monkeypatch,
):
    from test_automatic_match_learning_evidence import forbid_execution

    app, browser = localized_server.app_context, Browser(localized_server)
    root = requests[-1].to_dict()["document"]
    values = {name: root[name] for name in ("game_type", "player_role", "player_position",
        "declarer_player", "trick_leader", "hand", "declarer_points", "defender_points")}
    values["current_trick"] = root["current_trick"] or [""]
    for i, trick in enumerate(root["completed_tricks"], 1):
        values[f"completed_trick_{i}_leader"] = trick["players"][0]
        for j, card in enumerate(trick["cards"], 1):
            values[f"completed_trick_{i}_card_{j}"] = card
    form = Forms(browser.page("/analyze")).find("/actions/analyze/run-guided")
    page = follow(browser, browser.submit(form, **values, settings_mode="custom", sample_count="1"))
    original = app.analyze_state.latest_successful_result
    raw = browser.request("GET", "/downloads/analyze/result.json")[2]
    forbid_execution(monkeypatch)
    page = follow(browser, browser.submit(Forms(page).find("/actions/analyze/run-guided"),
                                         settings_mode="ordinary", analysis_effort="quick"))
    assert app.analyze_state.latest_successful_result is original
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                             language=locale))
        assert text(locale, "analysis.forced_previous") in unescape(page)
        assert text(locale, "analysis.forced_card", card=card_name(locale, "S10")) in unescape(page)
        assert browser.request("GET", "/downloads/analyze/result.json")[2] == raw
