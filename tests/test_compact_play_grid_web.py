"""Normal Play presentation over real returned forms and accepted Session files."""

import json
import re
from html import escape, unescape
from unittest.mock import patch

import pytest
from test_compact_initial_hand_web import recording
from test_consistent_card_presentation import DISPLAY
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_language_view_continuity import return_data
from test_match_recording_recovery_web import follow, start_match
from test_recorded_trick_progress_web import html_totals, summary_html
from test_recording_task_focus import Hierarchy
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

import skatmind.api.v1.session.files as session_files
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def start_play(browser, locale, *, seat="forehand"):
    switch(browser, browser.page("/sessions"), locale)
    page = create(browser, seat=seat)
    assert 'session-play-entry' not in page
    follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                  cards=get_full_deck()[:10]))
    active = browser.server.app_context.managed_stateful.active_session
    browser.command("set_declarer", player_id=active.state.local_player_id)
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    return active, browser.page()


def assert_play(page, locale, cards, *, selected=()):
    primary = recording(page)
    assert 'class="session-play-entry"' in primary and 'session-set-entry' not in page
    assert 'recording-progress-layout' in primary and 'data-recorded-summary' in primary
    assert 'class="recorded-current"' in primary and 'id="session-card-feedback"' in primary
    block = re.search(r'<fieldset class="compact-cards" data-card-mode="play".*?</fieldset>',
                      primary, re.S)[0]
    groups = re.findall(r'<div class="compact-card-group"><h4>(.*?)</h4>(.*?)</div></div>',
                        block, re.S)
    expected = [(suit, [card for card in group if card in cards])
                for suit, group in zip("CSHD", DISPLAY, strict=True) if set(group) & set(cards)]
    assert len(groups) == len(expected)
    for (heading, choices), (suit, codes) in zip(groups, expected, strict=True):
        assert unescape(heading) == text(locale, "task.card.suit." + suit)
        assert re.findall(r'name="cards" value="([^"]+)"', choices) == codes
    markup = Hierarchy(block)
    controls = [node for node in markup.nodes if node["tag"] == "input"]
    assert len(controls) == len(cards)
    checked = [node["attrs"]["value"] for node in controls if "checked" in node["attrs"]]
    assert checked == list(selected)
    ids = []
    for node in controls:
        attrs = node["attrs"]
        assert attrs["type"] == "radio" and attrs["name"] == "cards"
        assert "required" in attrs and "disabled" not in attrs and "tabindex" not in attrs
        assert attrs["aria-label"] == card_name(locale, attrs["value"])
        assert node["parents"][-1]["attrs"]["class"] == "compact-card"
        assert node["parents"][-1]["tag"] == "label"
        assert markup.visible(node)
        ids.append(attrs.get("id"))
    # Validation alone adds an anchor to the first radio; labels wrap every radio.
    assert bool(ids[0]) == (controls[0]["attrs"].get("aria-invalid") == "true")
    assert all(identity is None for identity in ids[1:])
    assert 'compact-selection' not in block
    assert text(locale, "compact.capacity_play", capacity=1) in block
    assert re.search(r'<button type="submit" class="primary"[^>]*>'
                     + re.escape(text(locale, "compact.record")), primary)
    form = Forms(page).find("/sessions/play")
    assert set(form["values"]) - {"cards"} == {
        "managed_handle", "card_selection", "_frontend_form_instance"}
    return form, ids


@pytest.mark.parametrize("locale", ("de", "en"))
def test_complete_pending_single_save_unknown_actor_sparse_and_rejection(localized_server, locale):
    browser = Browser(localized_server)
    active, page = start_play(browser, locale)
    hand = get_full_deck()[:10]  # Eight genuine Clubs plus SA/S10, not a padded palette.
    original, ids = assert_play(page, locale, hand)
    actor = "Alex — " + text(locale, "creation.seat.forehand")
    assert escape(text(locale, "task.record_next_card", player=actor)) in recording(page)
    assert "cards" not in original["values"]
    assert html_totals(summary_html(page)) == ((0, 0), (0, 0))
    prefix, saved = active.state.command_log, active.path.read_bytes()
    alternate = "en" if locale == "de" else "de"
    pending = json.loads(envelope(page, "/sessions/play", {"cards": ["CA"]}))
    pending["view"] = {"anchor": "id:session-recording", "offset": -80, "x": 0, "focus": alternate}
    with patch.object(session_files, "save_session_file",
                      wraps=session_files.save_session_file) as saves:
        page = follow(browser, enhanced_switch(browser, page, json.dumps(pending), alternate))
        assert return_data(page)["view"] == pending["view"]
        form, returned_ids = assert_play(page, alternate, hand, selected=("CA",))
        assert returned_ids == ids
        assert form["values"] == {**original["values"], "cards": "CA"}
        assert active.path.read_bytes() == saved and active.state.command_log == prefix
        assert saves.call_count == 0
        response = browser.submit(form)
        assert response[0] == 303
        assert response[1]["location"] == "/sessions/current#session-recording"
        page = follow(browser, response)
        assert saves.call_count == 1 and active.state.revision == len(prefix) + 1
        assert active.state.command_log[:-1] == prefix
        command = active.state.command_log[-1].command
        assert command.card == "CA" and command.player_id == active.state.local_player_id
        facts = replay_session_state_v1(active.state)
        assert facts.next_player_id == active.state.players[1].player_id
        assert facts.remaining_hand_for(facts.next_player_id) is None
        form, _ = assert_play(page, alternate, get_full_deck()[10:])
        actor = "Boris — " + text(alternate, "creation.seat.middlehand")
        assert escape(text(alternate, "task.record_next_card", player=actor)) in recording(page)
        assert "cards" not in form["values"]
        assert text(alternate, "task.match.scope.bounded_observation_candidates") in recording(page)
        assert escape(card_name(alternate, "CA")) in recording(page)
        assert html_totals(summary_html(page)) == ((0, 0), (0, 0))
        for card in ("H7", "D7"):
            page = follow(browser, browser.submit(Forms(page).find("/sessions/play"), cards=card))
        assert saves.call_count == 3
        sparse = [card for card in hand if card != "CA"]
        form, _ = assert_play(page, alternate, sparse)
        assert html_totals(summary_html(page)) == ((1, 11), (0, 0))
        assert 'data-trick-number="1"' in page and 'id="session-play-1"' in page
        assert text(alternate, "recovery.trick", number=2) in recording(page)
        before, document = active.path.read_bytes(), active.document
        rejected = browser.submit(form, cards="CA")
        assert rejected[0] == 400
        page = rejected[2].decode()
        assert_play(page, alternate, sparse)
        assert 'class="session-card-evidence" href="#session-play-1"' in page
        assert 'role="alert" tabindex="-1"' in page and 'aria-invalid="true"' in page
        page = switch(browser, page, locale)
        assert_play(page, locale, sparse)
        assert html_totals(summary_html(page)) == ((1, 11), (0, 0))
        assert 'class="session-card-evidence" href="#session-play-1"' in page
        assert active.document is document and active.path.read_bytes() == before
        assert saves.call_count == 3


@pytest.mark.parametrize("locale", ("de", "en"))
def test_follow_suit_stays_sparse_and_only_normal_session_play_opts_in(localized_server, locale):
    browser = Browser(localized_server)
    active, _ = start_play(browser, locale, seat="middlehand")
    browser.command("record_play", card="SK")
    page = browser.page()
    assert_play(page, locale, ("SA", "S10"))
    assert text(locale, "task.match.scope.exact_legal_cards") in recording(page)
    markup = Hierarchy(page)
    kind = next(node for node in markup.nodes if node["attrs"].get("name") == "kind"
                and node["attrs"].get("value") == "record_play")
    correction = next(parent for parent in reversed(kind["parents"]) if parent["tag"] == "form")
    assert not any(parent["attrs"].get("class") == "session-play-entry"
                   for parent in correction["parents"])
    assert 'session-play-entry' not in start_match(browser, locale)
    assert active.state.revision == 14
