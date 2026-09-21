"""Private display order is not canonical batch, chronological or ranked order."""

import re
from copy import deepcopy
from html import escape

import pytest

from skatmind.app_web.compact_card_rendering import (
    card_display_groups,
    compact_card_selector,
    compact_recorded_card,
)
from skatmind.app_web.session_card_entry import validate_card_selection
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.task_first_rendering import cards_summary
from skatmind.deck import get_full_deck
from skatmind.rules import get_legal_cards

DISPLAY = (
    ("CJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7"),
    ("SJ", "SA", "S10", "SK", "SQ", "S9", "S8", "S7"),
    ("HJ", "HA", "H10", "HK", "HQ", "H9", "H8", "H7"),
    ("DJ", "DA", "D10", "DK", "DQ", "D9", "D8", "D7"),
)
GAMES = (None, "clubs", "spades", "hearts", "diamonds", "grand", "null")


@pytest.mark.parametrize("game", GAMES)
def test_four_literal_printed_suit_groups_for_every_declaration(game):
    source = list(reversed(get_full_deck()))
    original = source.copy()
    assert card_display_groups(source, game) == tuple(zip(
        ("task.card.suit.C", "task.card.suit.S", "task.card.suit.H", "task.card.suit.D"),
        DISPLAY, strict=True))
    assert source == original
    html = compact_card_selector("en", mode="set", cards=source, game_type=game)
    assert re.findall(r'name="cards" value="([^"]+)"', html) == [
        card for group in DISPLAY for card in group]
    assert html.count('class="compact-card-group"') == 4


@pytest.mark.parametrize("game", GAMES)
def test_filtered_palette_omits_empty_groups_and_never_adds_rejected_cards(game):
    cards = ["D7", "C10", "CJ", "HA", "CA", "HJ", "H10"]
    assert card_display_groups(cards, game) == (
        ("task.card.suit.C", ("CJ", "CA", "C10")),
        ("task.card.suit.H", ("HJ", "HA", "H10")),
        ("task.card.suit.D", ("D7",)))
    html = compact_card_selector("de", mode="play", cards=cards,
                                 selected=("H10", "SA"), game_type=game)
    assert 'value="SA"' not in html and html.count(' checked') == 1
    assert card_display_groups((), game) == ()


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("selected", ((), ("H10",)))
def test_single_play_has_native_state_but_no_pending_summary(locale, selected):
    html = compact_card_selector(locale, mode="play", cards=("H10", "D7"), selected=selected)
    assert 'compact-selection' not in html
    assert 'compact-selected' not in html and 'compact-count' not in html
    assert html.count('type="radio"') == html.count(' required') == 2
    assert html.count(' checked') == len(selected)
    assert 'compact-rejected' in html
    multiple = compact_card_selector(locale, mode="set", selected=selected, capacity=10)
    assert 'compact-selection' in multiple and 'compact-count' in multiple
    assert multiple.count('type="checkbox"') == 32 and ' required' not in multiple


@pytest.mark.parametrize("locale", ("de", "en"))
def test_all_faces_have_validated_suit_and_rank_hooks_and_complete_names(locale):
    for card in get_full_deck():
        for html in (compact_recorded_card(locale, card),
                     compact_recorded_card(locale, card, show_code=False),
                     compact_card_selector(locale, mode="play", cards=(card,))):
            assert f'class="card-face" data-card-suit="{card[0]}"' in html
            assert f'class="card-rank">{card[1:]}</span>' in html
            assert 'class="card-suit"' in html
            assert escape(card_name(locale, card), quote=True) in html
        readonly = compact_recorded_card(locale, card, show_code=False)
        assert f'({card})' not in readonly
        assert all(tag not in readonly for tag in ('<input', 'tabindex=', '<button'))
    assert 'Jack' in compact_recorded_card("en", "HJ")
    assert 'Bube' in compact_recorded_card("de", "HJ")


def test_literal_canonical_batch_and_rule_order_remain_independent():
    assert get_full_deck() == (
        "CA C10 CK CQ CJ C9 C8 C7 SA S10 SK SQ SJ S9 S8 S7 "
        "HA H10 HK HQ HJ H9 H8 H7 DA D10 DK DQ DJ D9 D8 D7").split()
    assert validate_card_selection(["CJ", "CA", "C10", "D7"], capacity=10) == (
        "CA", "C10", "CJ", "D7")
    hand = ["C10", "CA", "CJ", "SJ", "HJ", "D7"]
    original = hand.copy()
    for game in ("clubs", "spades", "hearts", "diamonds", "grand"):
        expected = ["C10", "CA", "CJ", "SJ", "HJ"] if game == "clubs" else ["CJ", "SJ", "HJ"]
        if game == "diamonds":
            expected.append("D7")
        assert get_legal_cards(hand, ["CJ"], game) == expected
    assert get_legal_cards(hand, ["CJ"], "null") == ["C10", "CA", "CJ"]
    assert hand == original


def test_context_sorts_only_hand_copy_and_generic_summary_preserves_ranking():
    from test_recorded_decision_context import document, project

    from skatmind.app_web.recorded_decision_context_rendering import (
        render_recorded_decision_context,
    )

    source = document()
    original = deepcopy(source)
    context = project(source)
    html = render_recorded_decision_context(context, "en")
    hand = re.search(r'<ul class="decision-context-hand">(.*?)</ul>', html)[1]
    assert re.findall(r'aria-label="([^"]+)"', hand) == [card_name("en", card) for card in
        ("CJ", "C10", "SJ", "SA", "HA", "DK", "D7")]
    trick = re.search(r'<ol class="decision-context-trick">(.*?)</ol>', html)[1]
    assert re.findall(r'aria-label="([^"]+)"', trick) == [card_name("en", c) for c in ("HJ", "DJ")]
    ranked = ["D7", "CA", "CJ"]
    assert re.findall(r'\(([^)]+)\)', cards_summary("en", ranked)) == ranked
    assert source == original and context.hand == tuple(original["position"]["hand"])


def test_set_summaries_copy_membership_without_reordering_generic_sequences():
    from skatmind.app_web.task_first_rendering import card_set_summary
    from skatmind.app_web.unplayed_card_rendering import recorded_cards_summary

    cards = ["D7", "C10", "CA", "CJ"]
    for summary in (card_set_summary, recorded_cards_summary):
        assert re.findall(r'\(([^)]+)\)', summary("en", cards)) == ["CJ", "CA", "C10", "D7"]
    assert cards == ["D7", "C10", "CA", "CJ"]
    assert re.findall(r'\(([^)]+)\)', cards_summary("en", cards)) == cards


def test_face_rejects_noncanonical_suit_markup():
    with pytest.raises(ValueError):
        compact_recorded_card("en", 'H10" data-unsafe="yes')


def test_real_rendered_batch_keeps_canonical_commands_intermediate_states_and_one_save(
    tmp_path, monkeypatch,
):
    from test_compact_card_entry_web import choice_codes, create_live
    from test_frontend_language_switching import localized_server
    from test_match_recording_recovery_web import follow
    from test_session_recorded_review_web import Browser

    import skatmind.api.v1.session as api
    import skatmind.api.v1.session.files as files
    import skatmind.app_web.session_card_entry as entry
    from skatmind.session_transitions import replay_session_state_v1

    fixture = localized_server.__wrapped__(tmp_path)
    server = next(fixture)
    try:
        browser = Browser(server)
        form = create_live(browser)
        active = server.app_context.managed_stateful.active_session
        state = active.state
        submitted = [c for c in choice_codes(browser.page(), mode="set")
                     if c in {"CJ", "CA", "C10", "D7"}]
        assert submitted == ["CJ", "CA", "C10", "D7"]
        saves, checkpoints = [], []
        real_save, collect = files.save_session_file, entry._collect_current_checkpoint

        def save(*a, **kw):
            saves.append(kw["expected_content_fingerprint"])
            return real_save(*a, **kw)

        def capture(**kw):
            result = collect(**kw)
            checkpoints.append((kw["state"], result))
            return result

        monkeypatch.setattr(files, "save_session_file", save)
        monkeypatch.setattr(entry, "_collect_current_checkpoint", capture)
        page = follow(browser, browser.submit(form, cards=submitted))
        assert len(saves) == 1
        assert re.findall(r'\(([A-Z0-9]+)\)', re.search(
            r'<p id="session-hand-1"[^>]*>.*?</p>', page)[0]) == submitted
        reference = api.apply_session_command(state, api.SetSessionGameMetadataCommandV1(
            expected_revision=0, game_id=state.session_id, played_at=None)).value.state
        states = {0: state, 1: reference}
        for card in ("CA", "C10", "CJ", "D7"):
            reference = api.apply_session_command(reference, api.RecordSessionDealtCardCommandV1(
                expected_revision=reference.revision, destination="player_hand",
                player_id=state.local_player_id, card=card)).value.state
            states[reference.revision] = reference
        assert active.state == reference
        assert [s.revision for s, _ in checkpoints] == [0, 1, 1, 2, 2, 3, 3, 4, 4, 5]
        assert all(s == states[s.revision] and c == () for s, c in checkpoints)
        assert replay_session_state_v1(active.state).initial_hand_for(state.local_player_id) == (
            "CA", "C10", "CJ", "D7")
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass
