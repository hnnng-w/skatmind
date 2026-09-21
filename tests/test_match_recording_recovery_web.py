import re
from urllib.parse import urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_game import build_historical_input
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_workspace_persistence import load_match_workspace_file_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def synthetic_cards():
    # Complete test-only deal; only observed Plays are submitted to the server.
    deck = ("SA CA C10 CK CQ C9 C8 C7 H10 H9 "
            "S9 S8 SK SQ S10 CJ SJ HJ DJ D10 "
            "S7 HA HK HQ H8 DA DK DQ D9 D8 H7 D7").split()
    data = build_historical_input(deck=deck, hand_game=True)
    return tuple(play["card"] for trick in data["tricks"] for play in trick["plays"])


def follow(browser, response):
    status, headers, body = response
    assert status == 303, (status, body.decode())
    return browser.page(urlsplit(headers["location"]).path)


def operation_form(page, operation):
    return next(form for form in Forms(page).forms
                if form["values"].get("operation") == operation)


def entry_action(page, index, *, rewind=False):
    block = page.split(f'<li id="match-play-{index}"', 1)[1].split('</li>', 1)[0]
    return Forms(block).find("/matches/recovery/select", index=int(rewind))


def start_match(browser, locale="en", name="Alexandra Long-Synthetic-Player-Name"):
    page = browser.page("/matches/new")
    if locale == "de":
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        match_title="Synthetic recovery Match",
        forehand_name=name,
        middlehand_name="Boris", rearhand_name="Clara", perspective_seat="forehand",
        platform_choice="in_person", setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        setup_action="create"))
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    # Resolve the named Declarer choice from returned HTML, not internal IDs.
    options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    declarer = re.findall(r'<option value="([^"]+)"', options)[0]
    return follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=declarer, game_type="grand", hand_game="true"))


@pytest.mark.parametrize("locale", ("en", "de"))
@pytest.mark.parametrize("late", (False, True))
def test_real_record_warning_or_late_replay_recover_complete_reopen(localized_server, locale, late):
    browser = Browser(localized_server)
    page = start_match(browser, locale)
    active = localized_server.app_context.managed_stateful.active_match
    source_id = active.workspace.slots[0].observed_game.game_id
    cards = synthetic_cards()
    assert cards[:5] == ("SA", "S9", "S7", "CA", "S8")
    altered = (cards[0], "H7", *cards[2:])
    for card in altered[:29 if late else 5]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    assert text(locale, "recovery.warning") in page
    assert 'href="#match-play-2"' in page and 'href="#match-play-5"' in page
    original = active.path.read_bytes()
    accepted = active.workspace
    if late:
        status, _, body = browser.submit(operation_form(page, "append_plays"), cards=cards[-1])
        assert status == 400
        page = body.decode()
        assert text(locale, "recovery.complete_replay") in page
        assert active.recovery.diagnostic.play_index == 2
        assert active.recovery.diagnostic.witness_index == 5
        assert 'id="match-play-30"' not in page
        assert re.search(r'<input[^>]*value="' + cards[-1] + r'"[^>]*checked', page)
        assert active.path.read_bytes() == original and active.workspace is accepted
    page = follow(browser, browser.submit(entry_action(page, 2)))
    assert text(locale, "recovery.preview_title") in page
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="S9"))
    assert text(locale, "recovery.annotations_unchanged") not in page
    assert active.path.read_bytes() == original and active.workspace is accepted
    apply = Forms(page).find("/matches/recovery/apply")
    assert "confirm_apply" not in apply["values"]
    response = browser.submit(apply, confirm_apply="on")
    assert response[1]["location"] == "/matches/position/1#match-recording"
    page = follow(browser, response)
    assert text(locale, "recovery.saved" if late else "feedback.correction") in page
    if late:
        assert 'data-operation-feedback' not in page
    assert active.workspace.revision == accepted.revision + 1
    assert len(active.workspace.slots[0].observed_game.plays) == (29 if late else 5)
    assert browser.submit(apply, confirm_apply="on")[0] == 409
    page = browser.page("/matches/current")
    for card in cards[29 if late else 5:]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    game = active.workspace.slots[0].observed_game
    assert game.game_id == source_id and tuple(play.card for play in game.plays) == cards
    assert game.perspective_initial_hand is game.original_skat is None
    assert text(locale, "recovery.warning") not in page
    saved = active.path.read_bytes()
    loaded = load_match_workspace_file_v1(active.path)
    assert loaded.document.workspace == active.workspace
    landing = browser.page("/matches")
    page = follow(browser, browser.submit(Forms(landing).find("/matches/open")))
    reopened = localized_server.app_context.managed_stateful.active_match
    assert reopened is not active and reopened.workspace == active.workspace
    assert reopened.path.read_bytes() == saved
    assert 'id="match-play-30"' in page


def test_native_language_invalid_suffix_rewind_cancel_and_security(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in synthetic_cards()[:6]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    active = localized_server.app_context.managed_stateful.active_match
    original = active.path.read_bytes()
    page = follow(browser, browser.submit(entry_action(page, 2)))
    preview_form = Forms(page).find("/matches/recovery/preview")
    status, _, body = browser.submit(preview_form, card="CJ")
    assert status == 400
    page = body.decode()
    assert text("en", "recovery.reason.wrong_actor") in page
    assert 'href="#match-play-4"' in page
    language = Forms(page).find("/actions/profile/language")
    assert language["values"]["return_to"] == "/matches/position/1"
    page = follow(browser, browser.submit(language, language="de"))
    assert text("de", "recovery.reason.wrong_actor") in page
    assert Forms(page).find("/matches/recovery/preview")["values"]["card"] == "CJ"
    assert active.path.read_bytes() == original
    page = follow(browser, browser.submit(entry_action(page, 2, rewind=True)))
    assert text("de", "recovery.removal_final") in page
    apply = Forms(page).find("/matches/recovery/apply")
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/cancel")))
    assert active.path.read_bytes() == original
    assert browser.submit(apply, confirm_apply="on")[0] == 409
    page = browser.page("/matches/current")
    page = follow(browser, browser.submit(entry_action(page, 6, rewind=True)))
    apply = Forms(page).find("/matches/recovery/apply")
    for header in ({"Origin": "null"}, {"Origin": "http://foreign.invalid"}, {"Cookie": ""}):
        assert browser.request("POST", apply["action"],
            {**apply["values"], "confirm_apply": "on"}, headers=header)[0] == 403
    assert browser.submit(apply, confirm_apply="on", card="CA")[0] == 400
    assert active.path.read_bytes() == original
    follow(browser, browser.submit(apply, confirm_apply="on"))
    assert len(active.workspace.slots[0].observed_game.plays) == 5


def test_superseded_foreign_reload_and_expired_forms_are_contextual(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in synthetic_cards()[:3]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    active = localized_server.app_context.managed_stateful.active_match
    original = active.path.read_bytes()
    first = entry_action(page, 2)
    page = follow(browser, browser.submit(first))
    preview = Forms(page).find("/matches/recovery/preview")
    page = follow(browser, browser.submit(preview, card="S8"))
    old_apply = Forms(page).find("/matches/recovery/apply")
    page = follow(browser, browser.submit(preview, card="SK"))
    assert browser.submit(old_apply, confirm_apply="on")[0] == 409
    foreign = {**first["values"], "managed_handle": "0" * 64}
    status, _, body = browser.request("POST", first["action"], foreign)
    assert status == 409 and b'id="match-recording"' in body
    page = browser.page("/matches/current")
    reload_form = Forms(page).find("/matches/api/v1/reload")
    page = follow(browser, browser.submit(reload_form))
    status, _, body = browser.submit(first)
    assert status == 409 and b'id="match-recovery-feedback"' in body
    assert active.path.read_bytes() == original


def test_rejected_proposed_witness_and_escaped_names_are_distinguished(localized_server):
    from skatmind.app_web.match_recovery_rendering import render_match_diagnostic
    from skatmind.app_web.stateful_localization import card_name
    from skatmind.observed_trace_diagnostics import find_observed_trace_warning
    browser = Browser(localized_server)
    page = start_match(browser, name="<script>Synthetic</script>")
    for card in ("SA", "H7", "S7", "CA", "S8"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    active = localized_server.app_context.managed_stateful.active_match
    warning = find_observed_trace_warning(active.workspace.slots[0].observed_game.plays, "grand")
    # Renderer edge: the same witness is proposed rather than accepted in a candidate.
    rendered = render_match_diagnostic(active, "en", warning, proposed_index=5)
    witness = card_name("en", "S8")
    assert text("en", "recovery.witness.proposed", card=witness) in rendered
    assert text("en", "recovery.witness.accepted", card=witness) not in rendered
    assert "<script>Synthetic</script>" not in page
    assert "&lt;script&gt;Synthetic&lt;/script&gt;" in page
    for player in active.workspace.match_definition.participants:
        assert player.player_id not in rendered


def test_invalid_then_valid_preview_does_not_restore_rejected_replacement(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in synthetic_cards()[:6]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    page = follow(browser, browser.submit(entry_action(page, 2)))
    preview = Forms(page).find("/matches/recovery/preview")
    assert browser.submit(preview, card="CJ")[0] == 400
    page = follow(browser, browser.submit(preview, card="SK"))
    assert not any(f["action"] == "/matches/recovery/preview" for f in Forms(page).forms)
    assert localized_server.app_context.managed_stateful.active_match.recovery.preview.card == "SK"
    assert 'class="error-summary"' not in page


@pytest.mark.parametrize("locale", ("en", "de"))
def test_final_proposed_card_is_the_first_supported_witness(localized_server, locale):
    from skatmind.app_web.stateful_localization import card_name
    browser = Browser(localized_server)
    page = start_match(browser, locale)
    # Frozen synthetic legal trace: DQ at Play 30 is the first witness that
    # contradicts an off-suit replacement of D10 at Play 26. No hidden hand input.
    cards = ("DK D8 D7 H10 HQ H7 SQ S10 S8 S9 S7 SK DJ SJ HJ "
             "H8 CQ HA C10 CA CK H9 DA C9 D9 D10 CJ C7 C8 DQ").split()
    for index, card in enumerate(cards[:29], 1):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"),
                                              cards="SA" if index == 26 else card))
    assert text(locale, "recovery.warning") not in page
    active = localized_server.app_context.managed_stateful.active_match
    original = active.path.read_bytes()
    status, _, body = browser.submit(operation_form(page, "append_plays"), cards="DQ")
    assert status == 400
    page = body.decode()
    assert (active.recovery.diagnostic.play_index,
            active.recovery.diagnostic.witness_index) == (26, 30)
    assert text(locale, "recovery.witness.proposed", card=card_name(locale, "DQ")) in page
    assert 'href="#match-play-26"' in page
    assert 'id="match-play-30"' not in page and 'href="#match-play-30"' not in page
    assert active.path.read_bytes() == original
    page = follow(browser, browser.submit(entry_action(page, 26)))
    page = follow(browser, browser.submit(
        Forms(page).find("/matches/recovery/preview"), card="D10"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    assert len(active.workspace.slots[0].observed_game.plays) == 29
    follow(browser, browser.submit(operation_form(page, "append_plays"), cards="DQ"))
    recorded = active.workspace.slots[0].observed_game.plays
    assert tuple(play.card for play in recorded) == tuple(cards)
