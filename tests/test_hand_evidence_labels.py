"""Scoped R05 wording over accepted facts, never a source-completion assertion."""

import re
from dataclasses import replace
from html import escape

import pytest
from test_compact_card_entry_web import create_live
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms, record_score_review_game
from test_unplayed_card_summary_web import pair_html

from skatmind.app_web.task_first_rendering import cards_summary
from skatmind.app_web.task_first_session_rendering import _hand_summary
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def overview_html(page):
    return re.search(r'<section class="panel"><h2>[^<]+</h2>(?:(?!</section>).)*'
                     r'id="session-hand-1".*?</section>', page, re.S)[0]


def hand_row(page, number):
    return re.search(fr'<p id="session-hand-{number}"[^>]*>.*?</p>', page, re.S)[0]


@pytest.mark.parametrize("count,remaining", ((18, ("C10", "CJ", "DK", "D7")),
    (27, ("CJ",)), (29, ("CJ",)), (30, ())))
def test_remaining_hand_overview_has_explicit_time_scope(localized_server, count, remaining):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=count)
    overview = overview_html(browser.page())
    assert "<h3>Initial seating</h3>" in overview
    assert "<h3>Remaining hand Cards</h3>" in overview
    assert "A — Rearhand" in overview
    assert overview.count("Hand Cards unknown") == 2
    displayed = ("CJ", "C10", "DK", "D7") if count == 18 else remaining
    assert re.findall(r'\(([A-Z0-9]+)\)', hand_row(overview, 3)) == list(displayed)
    active = localized_server.app_context.managed_stateful.active_session
    facts = replay_session_state_v1(active.state)
    assert facts.remaining_hand_for(facts.local_player_id) == remaining
    assert facts.known_skat == facts.discarded_cards == ()
    assert all(facts.remaining_hand_for(p.player_id) is None for p in facts.players[:2])
    assert bool(pair_html(browser.page())) == (count == 30)
    if count == 30:
        assert 'No hand Cards left' in hand_row(overview, 3)


def test_exhausted_hand_is_plain_and_opponents_stay_unknown(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=30)
    page = follow(browser, browser.submit(Forms(browser.page()).find(
        "/actions/profile/language"), language="de"))
    overview = overview_html(page)
    assert '<strong>A</strong>: ' + text("de", "task.session.hand_empty") in overview
    assert overview.count(text("de", "task.session.hand_unknown")) == 2


def test_derived_pair_does_not_repeat_absent_discard_input(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=30)
    pair = pair_html(browser.page())
    assert "Recorded input: Not recorded" not in pair
    assert "Derived from recorded play" in pair
    assert "<strong>Original Skat</strong>: Not recorded" in pair


def test_partial_initial_pickup_and_discard_labels_use_current_accepted_facts(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    page = follow(browser, browser.submit(form, cards="CA"))
    assert "<h3>Initial Cards entered so far</h3>" in overview_html(page)
    assert "(CA)" in hand_row(page, 1)
    active = localized_server.app_context.managed_stateful.active_session
    assert len(replay_session_state_v1(active.state).initial_hand_for(
        active.state.local_player_id)) == 1
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                          cards=get_full_deck()[1:10]))
    assert "<h3>Recorded initial hand Cards</h3>" in overview_html(page)
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="false")
    for skat in ("H7", "D7"):
        page = follow(browser, browser.submit(Forms(browser.page()).find("/sessions/cards"),
                                              cards=skat))
        assert "<h3>Current known hand Cards</h3>" in overview_html(page)
        assert f"({skat})" in hand_row(page, 1)
    assert len(re.findall(r'\(([A-Z0-9]+)\)', hand_row(page, 1))) == 12
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards="CA"))
    assert "<h3>Current known hand Cards</h3>" in overview_html(page)
    assert "(CA)" not in hand_row(page, 1)
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards="H7"))
    assert "<h3>Remaining hand Cards</h3>" in overview_html(page)
    assert len(re.findall(r'\(([A-Z0-9]+)\)', hand_row(page, 1))) == 10
    facts = replay_session_state_v1(active.state)
    assert facts.known_skat == ("H7", "D7") and facts.discarded_cards == ("CA", "H7")
    assert cards_summary("en", ()) == text("en", "task.known_empty")
    assert cards_summary("en", None) == text("en", "task.unknown")


def test_public_hand_keeps_its_own_membership_and_link_target(localized_server):
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(create_live(browser), cards=get_full_deck()[:10]))
    active = localized_server.app_context.managed_stateful.active_session
    owner = active.state.players[1].player_id
    browser.command("set_declarer", player_id=owner)
    browser.command("set_declaration", game_type="null", hand_game="true", ouvert="true")
    browser.command("set_public_hand", player_id=owner, cards=" ".join(get_full_deck()[10:20]))
    browser.command("record_play", card="SA")
    browser.command("record_play", card="SQ")
    page = browser.page()
    public = re.search(r'<div id="session-public-hand-2"[^>]*>(.*?)</div>', page, re.S)[1]
    assert text("en", "task.session.public_hand") in public
    assert "(SQ)" not in public and "(SJ)" in public
    assert "Hand Cards unknown" in hand_row(page, 2)
    assert replay_session_state_v1(active.state).remaining_hand_for(owner) is None


@pytest.mark.parametrize("phase", ("deal", "play", "ended"))
def test_defensive_empty_partial_or_missing_hand_is_not_exhausted(phase):
    from test_unplayed_card_summary import complete_facts
    facts = complete_facts()
    player = facts.local_player_id
    # Explicit malformed-presentation fixtures, not canonically accepted Sessions.
    for initial, remaining in (((), ()), (("CA",), ()), (("CA",), None)):
        malformed = replace(facts, phase=phase, initial_known_hands=((player, initial),),
            remaining_known_hands=() if remaining is None else ((player, remaining),))
        assert _hand_summary("en", malformed, player) == "Hand Cards unknown"


def test_defensive_missing_declaration_and_pickup_evidence_do_not_certify_empty():
    from test_unplayed_card_summary import complete_facts
    facts = complete_facts()
    player = facts.local_player_id
    assert _hand_summary("en", facts, player) == "No hand Cards left"
    assert _hand_summary("en", replace(facts, declaration=None), player) == "Hand Cards unknown"
    # This change of declarer without their pickup evidence is explicitly inconsistent input.
    malformed = replace(facts, declarer_player_id=player)
    assert _hand_summary("en", malformed, player) == "Hand Cards unknown"


def test_complete_names_are_escaped_and_original_seats_survive_new_leader(localized_server):
    browser = Browser(localized_server)
    name = 'Alexandra <&> "Long-Synthetic-Player-Name"'
    record_score_review_game(browser, play_count=3, names=("B", "C", name))
    page = browser.page()
    overview = overview_html(page)
    assert escape(name + " — Rearhand") in overview
    assert f'<strong>{escape(name)}</strong>' in hand_row(page, 3)
    active = localized_server.app_context.managed_stateful.active_session
    facts = replay_session_state_v1(active.state)
    assert facts.next_player_id == facts.local_player_id
    assert facts.players[2].seat == "rearhand"
    assert all(p.player_id not in overview for p in facts.players)
