"""Knowledge choices over real returned forms, accepted Logs, and saved review."""

from html import escape
from unittest.mock import patch

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first
from test_settings_seat_setup_web import add_players, setup_own

import skatmind.api.v1.session as api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.profile_driven_creation as creation
from skatmind.app_web.session_card_entry import project_session_card_task
from skatmind.app_web.task_first_projections import project_task_first_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_native_choices_missing_perspective_and_returned_language_values(localized_server, locale):
    browser = Browser(localized_server)
    app = localized_server.app_context
    page = switch(browser, browser.page("/sessions"), locale)
    before = app.frontend_profile.profile_path.read_bytes()
    form = Forms(page).find("/sessions/create")
    assert form["values"]["capture_mode"] == "live"
    assert form["values"]["own_seat"] == form["values"]["perspective_seat"] == ""
    for key in ("creation.session.knowledge_question", "session.knowledge.perspective",
                "session.knowledge.reconstruction", "creation.session.perspective_help",
                "creation.session.reconstruction_help", "creation.session.knowledge_perspective"):
        assert escape(text(locale, key)) in page
    assert text(locale, "creation.session.after_help") not in page
    with (patch.object(creation, "_materialize_players", side_effect=AssertionError("No IDs")),
          patch.object(session_files, "save_session_file", side_effect=AssertionError("No save"))):
        response = browser.submit(form, game_name="Past <Game>", forehand_name="Anna <&>",
            middlehand_name="Boris", rearhand_name="Clara", setup_action="update")
        assert response[0] == 400
        page = response[2].decode()
        assert text(locale, "validation.session.knowledge_perspective") in page
        assert app.frontend_profile.profile_path.read_bytes() == before
        assert app.managed_stateful.active_session is None
        for language in ("en" if locale == "de" else "de", locale):
            page = switch(browser, page, language)
            returned = Forms(page).find("/sessions/create")["values"]
            assert returned["capture_mode"] == "live"
            assert returned["forehand_name"] == "Anna <&>"
            assert returned["perspective_seat"] == "" and "save_players" not in returned
            assert text(language, "validation.session.knowledge_perspective") in page
        # The same safe roster can explicitly choose reconstruction with no perspective.
        page = follow(browser, browser.submit(Forms(page).find("/sessions/create"),
            capture_mode="retrospective", setup_action="update"))
        for language in ("en" if locale == "de" else "de", locale):
            page = switch(browser, page, language)
            values = Forms(page).find("/sessions/create")["values"]
            assert values["capture_mode"] == "retrospective" and values["perspective_seat"] == ""
            assert values["forehand_name"] == "Anna <&>"
        assert app.managed_stateful.active_session is None
    page = follow(browser, browser.submit(Forms(page).find("/sessions/create"),
                                          setup_action="create"))
    assert app.managed_stateful.active_session.state.capture_mode == "retrospective"
    assert app.managed_stateful.active_session.state.local_player_id is None
    assert text(locale, "session.knowledge.reconstruction") in page


@pytest.mark.parametrize("seat", ("forehand", "middlehand", "rearhand"))
@pytest.mark.parametrize("mode", ("live", "retrospective"))
def test_own_identity_survives_mode_change_but_requires_setup_review(localized_server, seat, mode):
    browser = Browser(localized_server)
    app = localized_server.app_context
    _, handles = add_players(browser)
    page, action = setup_own(browser, "sessions", handles, seat)
    if mode == "live":
        page = follow(browser, browser.submit(Forms(page).find(action),
            capture_mode="retrospective", setup_action="update"))
    before = app.frontend_profile.profile_path.read_bytes()
    with patch.object(creation, "_materialize_players", side_effect=AssertionError("No IDs")):
        response = browser.submit(Forms(page).find(action), capture_mode=mode,
                                  setup_action="create")
        assert response[0] == 400
        values = Forms(response[2].decode()).find(action)["values"]
        assert values["capture_mode"] == mode and values["own_seat"] == seat
        assert values[f"{seat}_handle"] == handles[0]
        assert app.frontend_profile.profile_path.read_bytes() == before
        assert app.managed_stateful.active_session is None
        page = follow(browser, browser.submit(Forms(response[2].decode()).find(action),
            setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
    active = app.managed_stateful.active_session
    assert active.state.capture_mode == mode
    own = next(p for p in active.state.players if p.player_label == "A")
    assert active.state.local_player_id == own.player_id and own.seat == seat
    actor = own if mode == "live" else active.state.players[0]
    assert project_session_card_task(active.state).player_id == actor.player_id
    key = "perspective" if mode == "live" else "reconstruction"
    assert text("en", "session.knowledge.accepted_mode",
                mode=text("en", f"session.knowledge.{key}")) in page


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("seat", ("rearhand", ""))
def test_complete_reconstruction_requires_all_named_hands_and_original_skat(
    localized_server, locale, seat,
):
    browser = Browser(localized_server)
    switch(browser, browser.page("/sessions"), locale)
    page = create(browser, "retrospective", seat)
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.revision == 0 and active.state.phase == "setup"
    players = ", ".join(p.player_label + " — " + text(locale, "creation.seat." + p.seat)
                        for p in active.state.players)
    guidance = escape(text(locale, "session.knowledge.all_hands", players=players))
    for index, player in enumerate(active.state.players):
        assert guidance in page
        assert project_session_card_task(active.state).player_id == player.player_id
        assert escape(text(locale, "compact.for", player=player.player_label + " — "
                           + text(locale, "creation.seat." + player.seat))) in page
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
            cards=get_full_deck()[index * 10:(index + 1) * 10]))
        assert active.state.phase == "deal"
        view = project_task_first_session_v1(active.state)
        assert view.workflow.primary_action == "record_dealt_card"
        # #250 emits declarer entry only at its valid first-entry phase, and
        # correction only for an accepted target. Expert transport still rejects
        # a premature declarer without bypassing the complete-deal requirement.
        before = active.path.read_bytes()
        assert not any(form["values"].get("kind") == "set_declarer"
                       for form in Forms(page).forms)
        response = browser.request("POST", "/sessions/command", {
            "managed_handle": active.handle, "expected_revision": active.state.revision,
            "kind": "set_declarer", "player_id": active.state.players[0].player_id})
        assert response[0] == 400 and active.path.read_bytes() == before
    assert project_session_card_task(active.state).destination == "skat"
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                          cards=get_full_deck()[30:]))
    assert active.state.phase == "declaration" and active.state.revision == 33
    assert project_task_first_session_v1(active.state).workflow.primary_action == "set_declarer"
    saved = active.path.read_bytes()
    document = session_files.load_session_file(active.path).value.document
    assert document == active.document
    assert api.resume_session_document(document.to_dict()).value.document == document
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened.path.read_bytes() == saved and reopened.state == active.state


@pytest.mark.parametrize("ended", (False, True))
def test_specialist_promotion_keeps_phase_and_frozen_ancestor_but_invalidates_result(
    localized_server, ended,
):
    browser = Browser(localized_server)
    record_live_game(browser, play_count=30 if ended else 3)
    if ended:
        browser.command("set_game_end")
    active = localized_server.app_context.managed_stateful.active_session
    page, _ = review_first(browser)
    frozen = active.recorded_review_source.decision.checkpoint
    request = api.export_session_checkpoint_review_request(
        state=active.state, checkpoint=frozen).value.request
    before = active.path.read_bytes()
    retained = active.execution
    for language in ("de", "en"):
        page = switch(browser, page, language)
        assert text(language, "task.session.promotion_help") in page
        assert active.execution is retained and active.path.read_bytes() == before
    phase, prefix = active.state.phase, active.state.command_log
    browser.command("promote_to_retrospective")
    assert active.state.phase == phase and active.state.command_log[:-1] == prefix
    assert active.state.capture_mode == "retrospective"
    assert active.state.initial_capture_mode == "live"
    assert active.execution is active.recorded_review_source is None
    assert browser.request("GET", "/sessions/downloads/result.json")[0] == 404
    exported = api.export_session_checkpoint_review_request(
        state=active.state, checkpoint=frozen).value
    assert exported.request == request
    assert exported.observation_revision == active.state.revision
    assert active.state.validation.historical_export.status == "unavailable"
    assert len(replay_session_state_v1(active.state).initial_known_hands) == 1
    page = browser.page()
    assert text("en", "session.knowledge.accepted_mode",
                mode=text("en", "session.knowledge.reconstruction")) in page
    assert "/sessions/cards" not in page
    # An explicit old canonical payload still meets the unchanged phase rejection.
    before = active.path.read_bytes()
    response = browser.request("POST", "/sessions/command", {
        "managed_handle": active.handle, "expected_revision": active.state.revision,
        "kind": "record_dealt_card", "destination": "player_hand",
        "player_id": active.state.players[1].player_id, "card": "D7"})
    assert response[0] == 400 and active.path.read_bytes() == before
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened.path.read_bytes() == before and reopened.state == active.state
    assert api.export_session_checkpoint_review_request(
        state=reopened.state, checkpoint=frozen).value.request == request
