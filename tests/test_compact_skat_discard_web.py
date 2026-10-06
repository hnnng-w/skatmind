"""Scoped set-entry presentation over real accepted files and returned HTTP forms."""

import json
import re
from html import escape
from unittest.mock import patch

import pytest
from test_compact_initial_hand_web import assert_palette, recording
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_language_view_continuity import return_data, view_envelope
from test_match_recording_recovery_web import follow
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch

import skatmind.api.v1.session.files as session_files
from skatmind.app_web.stateful_localization import text
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def start_skat(browser, locale, *, reconstruction=False):
    switch(browser, browser.page("/sessions"), locale)
    page = create(browser, "retrospective" if reconstruction else "live")
    for start in ((0, 10, 20) if reconstruction else (0,)):
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
            cards=get_full_deck()[start:start + 10]))
    if not reconstruction:
        browser.command("set_declarer")
        browser.command("set_declaration", game_type="clubs", hand_game="false", bid_value="18")
        page = browser.page()
    return page


def assert_task(page, locale, variant, cards, *, accepted=()):
    primary = recording(page)
    title = text(locale, "session." + variant + ".title", **(
        {"player": "Alex"} if variant == "discard" else {}))
    assert re.findall(r'<h2>(.*?)</h2>', primary) == [escape(title)]
    assert 'class="session-set-entry"' in primary
    assert 'recording-progress-layout' not in primary and 'data-recorded-summary' not in primary
    assert text(locale, f"session.{variant}.{'more' if accepted else 'start'}",
                capacity=2 - len(accepted)) in primary
    for key in ("compact.accepted", "compact.append", "task.known_empty"):
        assert escape(text(locale, key)) not in primary
    intro = page.split('<h1>', 1)[1].split('id="session-recording"', 1)[0]
    assert text(locale, "task.session.perspective", player="Alex") not in intro
    assert text(locale, "session.knowledge.accepted_mode",
                mode=text(locale, "session.knowledge.perspective")) not in intro
    saved = re.search(r'<div class="session-set-accepted">(.*?)</div>', primary, re.S)
    if accepted:
        assert saved and text(locale, f"session.{variant}.saved") in saved[1]
        assert re.findall(r'\(([CSHD][A-Z0-9]+)\)', saved[1]) == list(accepted)
        assert 'href="#session-history"' in saved[1]
    else:
        assert saved is None
    assert 'id="session-history"' in page and 'id="session-card-feedback"' in primary
    assert_palette(page, locale, cards)
    assert re.search(r'<button type="submit" class="primary"[^>]*>'
                     + re.escape(text(locale, "compact.save")), primary)
    form = Forms(page).find("/sessions/cards")
    assert set(form['values']) - {"cards"} == {
        "managed_handle", "card_selection", "_frontend_form_instance"}
    return form


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("variant", ("original_skat", "discard"))
def test_normal_empty_partial_reopen_rejection_language_and_completion(
    localized_server, locale, variant,
):
    browser = Browser(localized_server)
    page = start_skat(browser, locale)
    if variant == "discard":
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                              cards=["D7", "H7"]))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.phase == "skat_and_discard"
    domain = (get_full_deck()[10:] if variant == "original_skat" else
              [*get_full_deck()[:10], "H7", "D7"])
    initial = assert_task(page, locale, variant, domain)
    declaration = re.search(r'<section class="accepted-declaration">(.*?)</section>', page, re.S)[1]
    assert "Alex" in declaration and text(locale, "task.value.clubs") in declaration
    assert "<dd>18</dd>" in declaration
    assert text(locale, "session.correction.set_declaration") in declaration
    assert "cards" not in initial["values"]
    prefix = active.state.command_log
    # H7 is an offered original-Skat Card, and later an offered discard from that Skat.
    with patch.object(session_files, "save_session_file",
                      wraps=session_files.save_session_file) as saves:
        follow(browser, browser.submit(initial, cards="H7"))
        assert saves.call_count == 1
        saved = active.path.read_bytes()
        follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
        active = localized_server.app_context.managed_stateful.active_session
        assert active.path.read_bytes() == saved and saves.call_count == 1
        assert active.state.command_log[:-1] == prefix
        assert active.state.command_log[-1].command.card == "H7"
        page = browser.page()
        remaining = [card for card in domain if card != "H7"]
        form = assert_task(page, locale, variant, remaining, accepted=("H7",))
        assert "cards" not in form["values"]
        # Reopening renews the exact source binding; an old task cannot append.
        assert browser.submit(initial, cards="D7")[0] == 409
        page = browser.page()
        alternate = "en" if locale == "de" else "de"
        envelope = view_envelope(page, anchor="id:session-recording", offset=-80,
                                 locale=alternate, cards=("D7",))
        page = follow(browser, enhanced_switch(browser, page, json.dumps(envelope), alternate))
        assert return_data(page)["view"] == envelope["view"]
        assert Forms(page).find("/sessions/cards")["values"]["cards"] == "D7"
        assert active.path.read_bytes() == saved and saves.call_count == 1
        pending = ["HA" if variant == "original_skat" else "CA", "D7"]
        response = browser.submit(Forms(page).find("/sessions/cards"), cards=pending)
        assert response[0] == 400
        page = response[2].decode()
        assert "autofocus" in page and 'aria-invalid="true"' in page
        assert text(alternate, "validation.card_entry.capacity") in page
        assert Forms(page).find("/sessions/cards")["values"]["cards"] == pending
        assert_task(page, alternate, variant, remaining, accepted=("H7",))
        page = switch(browser, page, locale)
        assert "autofocus" not in page and 'role="alert" tabindex="-1"' in page
        assert text(locale, "validation.card_entry.capacity") in page
        form = assert_task(page, locale, variant, remaining, accepted=("H7",))
        assert form["values"]["cards"] == pending
        assert active.path.read_bytes() == saved and active.state.command_log[:-1] == prefix
        assert saves.call_count == 1
        response = browser.submit(form, cards="D7")
        assert response[1]["location"] == "/sessions/current#session-recording"
        page = follow(browser, response)
        assert saves.call_count == 2
    records = active.state.command_log[len(prefix):]
    assert [r.command.card for r in records] == ["H7", "D7"]
    assert [r.revision for r in records] == [len(prefix) + 1, len(prefix) + 2]
    assert [r.command.expected_revision for r in records] == [len(prefix), len(prefix) + 1]
    facts = replay_session_state_v1(active.state)
    if variant == "original_skat":
        assert facts.known_skat == ("H7", "D7")
        assert_task(page, locale, "discard", [*get_full_deck()[:10], "H7", "D7"])
    else:
        assert facts.discarded_cards == ("H7", "D7") and facts.phase == "play"
        assert facts.remaining_hand_for(facts.local_player_id) == tuple(get_full_deck()[:10])
        assert 'session-set-entry' not in page
        assert 'recording-progress-layout' in recording(page)
        assert 'data-recorded-summary' in recording(page)
        assert 'type="radio"' in recording(page)
        assert 'cards' not in Forms(page).find("/sessions/play")["values"]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_reconstruction_skat_before_declaration_keeps_filtered_domain(localized_server, locale):
    browser = Browser(localized_server)
    page = start_skat(browser, locale, reconstruction=True)
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.phase == "deal" and active.state.revision == 31
    cards = get_full_deck()[30:]
    form = assert_task(page, locale, "original_skat", cards)
    assert 'class="accepted-declaration"' not in page
    page = follow(browser, browser.submit(form, cards=cards[0]))
    form = assert_task(page, locale, "original_skat", cards[1:], accepted=(cards[0],))
    page = follow(browser, browser.submit(form, cards=cards[1]))
    assert active.state.phase == "declaration" and active.state.revision == 33
    assert replay_session_state_v1(active.state).known_skat == tuple(cards)
    assert 'session-set-entry' not in page
    assert Forms(page).find("/sessions/command", kind="set_declarer")
