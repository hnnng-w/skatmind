"""Initial-hand presentation over final HTTP responses and real accepted Session files."""

import re
from html import escape, unescape

import pytest
from test_consistent_card_presentation import DISPLAY
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow, start_match
from test_recording_task_focus import Hierarchy
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.stateful_localization import card_name, text
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def recording(page):
    return page.split('id="session-recording"', 1)[1].split('</section></div>', 1)[0]


def assert_palette(page, locale, cards):
    block = re.search(r'<fieldset class="compact-cards".*?</fieldset>', page, re.S)[0]
    groups = re.findall(r'<div class="compact-card-group"><h4>(.*?)</h4>(.*?)</div></div>',
                        block, re.S)
    expected = [(suit, [c for c in group if c in cards])
                for suit, group in zip("CSHD", DISPLAY, strict=True) if set(group) & set(cards)]
    assert len(groups) == len(expected)
    for (heading, choices), (suit, codes) in zip(groups, expected, strict=True):
        assert unescape(heading) == text(locale, "task.card.suit." + suit)
        assert re.findall(r'name="cards" value="([^"]+)"', choices) == codes
        assert choices.count('<label class="compact-card">') == len(codes)
        assert choices.count('type="checkbox"') == len(codes)
        assert ' disabled' not in choices and ' required' not in choices
        assert 'tabindex=' not in choices
        for code in codes:
            assert escape(card_name(locale, code), quote=True) in choices
            assert f'data-card-suit="{suit}"' in choices
            assert f'class="card-rank">{code[1:]}</span>' in choices


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("mode,seat", (("live", "forehand"), ("live", "middlehand"),
    ("live", "rearhand"), ("retrospective", "rearhand"), ("retrospective", "")))
def test_empty_has_one_named_target_and_concise_native_task(localized_server, locale, mode, seat):
    browser = Browser(localized_server)
    switch(browser, browser.page("/sessions"), locale)
    page = create(browser, mode, seat)
    active = localized_server.app_context.managed_stateful.active_session
    target = next(p for p in active.state.players
                  if p.seat == (seat if mode == "live" else "forehand"))
    primary = recording(page)
    expected = text(locale, "session.initial_hand.title", player=target.player_label,
                    seat=text(locale, "creation.seat." + target.seat))
    assert '<h1>Direct startup</h1>' in page
    assert re.findall(r'<h2>(.*?)</h2>', primary) == [escape(expected)]
    assert primary.count(target.player_label) == 1
    assert text(locale, "session.initial_hand.start", capacity=10) in primary
    assert 'data-recorded-summary' not in primary and 'recording-progress-layout' not in primary
    assert 'class="initial-hand-entry"' in primary
    for key in ("compact.accepted", "compact.append", "task.known_empty"):
        assert escape(text(locale, key)) not in primary
    assert 'session-initial-accepted' not in primary
    markup = Hierarchy(page)
    intro_text = " ".join(node["text"] for node in markup.within("session-recording", "p"))
    old_guidance = text(locale, "session.knowledge.local_hand", player=target.player_label)
    assert old_guidance not in intro_text
    assert not markup.within("session-recording", "aside")
    assert all(markup.visible(node) for node in markup.within("session-recording", "input"))
    if mode == "retrospective" and seat:
        assert text(locale, "task.session.perspective",
                    player="Clara — " + text(locale, "creation.seat.rearhand")) in primary
    else:
        assert text(locale, "task.session.perspective", player=target.player_label) not in primary
    # Secondary source context retains effective mode/phase without an introduction stack.
    intro = page.split('<h1>', 1)[1].split('id="session-recording"', 1)[0]
    assert text(locale, "session.knowledge.accepted_mode",
                mode=text(locale, "session.knowledge.perspective")) not in intro
    assert text(locale, "task.session.phase.setup") in page
    assert_palette(page, locale, get_full_deck())
    form = Forms(page).find("/sessions/cards")
    assert set(form['values']) == {"managed_handle", "card_selection", "_frontend_form_instance"}
    assert re.search(r'<button type="submit" class="primary"[^>]*>'
                     + re.escape(text(locale, "compact.save")), primary)
    assert active.state.revision == 0 and active.state.command_log == ()


@pytest.mark.parametrize("locale", ("de", "en"))
def test_partial_reopened_rejected_and_corrected_append(localized_server, locale):
    browser = Browser(localized_server)
    switch(browser, browser.page("/sessions"), locale)
    page = create(browser)
    accepted = get_full_deck()[:8]  # Complete Clubs suit is no longer an available group.
    follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=accepted))
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    prefix, before = active.state.command_log, active.path.read_bytes()
    page = browser.page()
    primary = recording(page)
    assert text(locale, "session.initial_hand.more", capacity=2) in primary
    saved = re.search(r'<div class="session-initial-accepted">(.*?)</div>', primary, re.S)[1]
    assert re.findall(r'\(([CSHD][A-Z0-9]+)\)', saved) == list(DISPLAY[0])
    assert 'href="#session-history"' in saved and 'id="session-history"' in page
    assert not Forms(page).find("/sessions/cards")["values"].get("cards")
    assert_palette(page, locale, get_full_deck()[8:])
    response = browser.submit(Forms(page).find("/sessions/cards"), cards=["CA", "SJ"])
    assert response[0] == 400
    page = response[2].decode()
    for language in (locale, "en" if locale == "de" else "de"):
        if language != locale:
            page = switch(browser, page, language)
        assert Forms(page).find("/sessions/cards")["values"]["cards"] == "SJ"
        assert_palette(page, language, get_full_deck()[8:])
        assert 'href="#session-hand-1"' in page and 'id="session-hand-1" tabindex="-1"' in page
        assert 'role="alert" tabindex="-1"' in page and 'aria-invalid="true"' in page
        assert ('autofocus' in page) == (language == locale)
        assert active.path.read_bytes() == before and active.state.command_log == prefix
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards")))
    assert active.state.command_log[:-1] == prefix
    assert active.state.command_log[-1].command.card == "SJ"
    assert active.state.revision == 10
    assert text(language, "session.initial_hand.more", capacity=1) in recording(page)


def test_original_skat_and_later_play_keep_their_existing_progress(localized_server):
    browser = Browser(localized_server)
    page = create(browser, "retrospective", "rearhand")
    for start in (0, 10, 20):
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                             cards=get_full_deck()[start:start + 10]))
    primary = recording(page)
    assert 'initial-hand-entry' not in page
    assert 'data-recorded-summary' in primary and 'recording-progress-layout' in primary
    assert text("en", "task.session.enter_skat") in primary
    assert_palette(page, "en", get_full_deck()[30:])
    follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=get_full_deck()[30:]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true")
    browser.command("record_play", card="CA")
    browser.command("record_play", card="HA")
    browser.command("record_play", card="D9")
    page = browser.page()
    assert 'initial-hand-entry' not in page
    assert 'data-recorded-summary' in recording(page)
    assert 'data-trick-metric="points">22</dd>' in page
    assert 'data-trick-number="1"' in page and 'id="session-play-1"' in page
    active = localized_server.app_context.managed_stateful.active_session
    assert len(replay_session_state_v1(active.state).completed_tricks) == 1
    assert 'initial-hand-entry' not in start_match(browser)


def test_long_user_names_remain_complete_and_escaped(localized_server):
    browser = Browser(localized_server)
    name = "Synthetic <&> " + "LongName" * 12
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/create"),
        game_name=name, forehand_name=name, middlehand_name="Boris", rearhand_name="Clara",
        capture_mode="live", perspective_seat="forehand", setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/sessions/create"),
                                          setup_action="create"))
    for language in ("en", "de"):
        page = switch(browser, page, language)
        assert f'<h1>{escape(name)}</h1>' in page
        assert recording(page).count(escape(name)) == 1
        assert name not in page
