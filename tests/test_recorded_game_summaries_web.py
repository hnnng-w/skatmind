"""Accepted summary facts at the displayed prefix, independent of original hand knowledge."""

import re
from html import unescape

import pytest
from test_compact_declaration_web import before_declaration, summary
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow, start_match
from test_session_recorded_review_web import Browser, Forms, record_live_game

import skatmind.api.v1.session.files as session_files
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def hand_text(page, number):
    row = re.search(fr'<p id="session-hand-{number}"[^>]*>(.*?)</p>', page, re.S)[1]
    return unescape(re.sub(r'<[^>]+>', '', row))


def assert_declaration_order(page, locale):
    groups = re.findall(r'<dl[^>]*>(.*?)</dl>', summary(page), re.S)
    keys = (
        ("task.field.declarer_player_id", "declaration.game_type", "declaration.bid_value",
         "declaration.matadors"),
        tuple("declaration." + key for key in
              ("hand_game", "schneider_announced", "schwarz_announced", "ouvert")),
    )
    assert len(groups) == 2
    for group, expected in zip(groups, keys, strict=True):
        assert re.findall(r'<dt>(.*?)</dt>', group) == [text(locale, key) for key in expected]
        assert len(re.findall(r'<div><dt>.*?</dt><dd>.*?</dd></div>', group, re.S)) == 4


@pytest.mark.parametrize("locale", ("en", "de"))
def test_perspective_ten_tricks_exhausts_each_hand_before_and_after_end(
    localized_server, locale, monkeypatch,
):
    browser = Browser(localized_server)
    record_live_game(browser, play_count=30)
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.phase == "play"
    before = active.path.read_bytes()
    state, checkpoints = active.state, active.decision_checkpoints
    download = browser.request("GET", "/sessions/downloads/session.json")[2]
    saves = []
    real_save = session_files.save_session_file
    def save(*args, **kwargs):
        saves.append(1)
        return real_save(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    page = follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                                          language=locale))
    for number in range(1, 4):
        assert text(locale, "task.session.hand_empty") in hand_text(page, number)
        assert text(locale, "task.session.hand_unknown") not in hand_text(page, number)
    assert_declaration_order(page, locale)
    facts = replay_session_state_v1(active.state)
    assert facts.played_card_count == 30 and len(facts.completed_tricks) == 10
    assert facts.game_end_reason is None
    for player in facts.players[1:]:
        assert facts.initial_hand_for(player.player_id) is None
        assert facts.remaining_hand_for(player.player_id) is None
    assert active.state is state and active.decision_checkpoints == checkpoints
    assert active.path.read_bytes() == before
    assert browser.request("GET", "/sessions/downloads/session.json")[2] == download
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.path.read_bytes() == before and active.state == state
    assert all(text(locale, "task.session.hand_empty") in hand_text(page, n) for n in range(1, 4))
    assert not saves
    browser.command("set_game_end")
    assert active.state.phase == "ended"
    assert len(saves) == 1
    assert all(text(locale, "task.session.hand_empty") in hand_text(browser.page(), n)
               for n in range(1, 4))


def test_selected_earlier_prefix_and_partial_final_trick_are_player_specific(localized_server):
    browser = Browser(localized_server)
    data, plays = record_live_game(browser, play_count=30)
    active = localized_server.app_context.managed_stateful.active_session
    first_play = next(r.revision for r in active.state.command_log
                      if r.command.kind == "record_play")
    checkpoints = active.decision_checkpoints
    frozen = tuple(c.to_dict() for c in checkpoints)
    # Select a real strict prefix after recording the full synthetic game.
    page = follow(browser, browser.submit(Forms(browser.page()).find("/sessions/undo"),
                                          target_revision=str(first_play + 26)))
    for count in range(27, 31):
        facts = replay_session_state_v1(active.state)
        for number, (player, source) in enumerate(
            zip(facts.players, data["players"], strict=True), 1,
        ):
            played = sum(p["player_id"] == source["player_id"] for p in plays[:count])
            visible = hand_text(page, number)
            if played == 10:
                assert text("en", "task.session.hand_empty") in visible
            elif number != 1:
                assert text("en", "task.session.hand_unknown") in visible
                assert text("en", "task.session.hand_empty") not in visible
            else:
                assert re.findall(r'\(([A-Z0-9]+)\)', visible)
                assert text("en", "task.session.hand_empty") not in visible
            if number != 1:
                assert facts.initial_hand_for(player.player_id) is None
        if count < 30:
            browser.command("record_play", card=plays[count]["card"])
            page = browser.page()
    assert tuple(c.to_dict() for c in checkpoints) == frozen


@pytest.mark.parametrize("count", (0, 4, 28))
def test_early_ending_preserves_unexhausted_known_and_unknown_hands(localized_server, count):
    browser = Browser(localized_server)
    data, plays = record_live_game(browser, play_count=count)
    active = localized_server.app_context.managed_stateful.active_session
    before_page = browser.page()
    hands = [hand_text(before_page, number) for number in range(1, 4)]
    for number, source in enumerate(data["players"], 1):
        played = sum(p["player_id"] == source["player_id"] for p in plays[:count])
        assert (text("en", "task.session.hand_empty") in hands[number - 1]) == (played == 10)
        if number != 1 and played < 10:
            assert text("en", "task.session.hand_unknown") in hands[number - 1]
    browser.command("set_game_end", game_end_reason="defender_concession",
        player_id=active.state.players[1].player_id, concession_form="explicit_verbal")
    assert active.state.phase == "ended"
    assert [hand_text(browser.page(), number) for number in range(1, 4)] == hands


@pytest.mark.parametrize("game_type,flags,bid,matadors", (
    ("grand", (True, True, True, True), "24", "4"),
    ("hearts", (True, True, False, False), "", ""),
    ("null", (False, False, False, True), "46", ""),
))
def test_saved_groups_preserve_values_and_correction_actions_in_both_languages(
    localized_server, game_type, flags, bid, matadors,
):
    browser = Browser(localized_server)
    form = before_declaration(browser, defender=False,
                              hand="CJ SJ HJ DJ CA C10 CK CQ C9 C8".split())
    names = ("hand_game", "schneider_announced", "schwarz_announced", "ouvert")
    page = follow(browser, browser.submit(form, game_type=game_type, bid_value=bid,
        matadors=matadors, **{key: "true" for key, enabled in zip(names, flags, strict=True)
                            if enabled}))
    active = localized_server.app_context.managed_stateful.active_session
    before, state = active.path.read_bytes(), active.state
    actions = Forms(summary(page)).forms
    assert len(actions) == 2
    assert all(form["action"] == "/sessions/declaration-correction/select" for form in actions)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert_declaration_order(page, locale)
        accepted = summary(page)
        assert Forms(accepted).forms == actions
        values = re.findall(r'<dd>(.*?)</dd>', re.sub(r'<form.*?</form>', '', accepted, flags=re.S))
        assert values[:4] == ["Alexandra Long-Synthetic-Player-Name",
            text(locale, "task.value." + game_type),
            bid or text(locale, "declaration.not_entered"),
            text(locale, "declaration.not_applicable") if game_type == "null" else
            matadors or text(locale, "declaration.not_entered")]
        assert values[4:] == [text(locale, "common.answer.yes" if flag else "common.answer.no")
                              for flag in flags]
        assert active.state is state and active.path.read_bytes() == before


@pytest.mark.parametrize("locale", ("en", "de"))
def test_shared_match_recording_and_review_keep_order_and_destinations(localized_server, locale):
    browser = Browser(localized_server)
    page = start_match(browser, locale)
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    assert_declaration_order(page, locale)
    assert 'id="match-declaration"' in page
    page = browser.page("/matches/review/1")
    assert_declaration_order(page, locale)
    assert 'href="/matches/position/1#match-recording"' in page
    assert active.path.read_bytes() == before
