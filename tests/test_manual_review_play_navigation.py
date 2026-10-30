"""Delivered manual Review radio selection, feedback and independent navigation."""

import pytest
from test_completed_trick_input_grouping import (
    assert_ids_and_labels,
    descendants,
)
from test_frontend_language_switching import localized_server as _server
from test_guided_card_palettes import CARDS, DEAL, DEAL_ACTION, DISCARD_ACTION, native_cards
from test_language_switch_context import switch
from test_manual_review_saved_names import snapshot, start
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

from skatmind.app_web.historical_form import build_historical_play_view_v1
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

PLAY = "/actions/review/append-play"
BACK = "/actions/review/back"
UNDO = "/actions/review/undo-play"
RESET = "/actions/review/reset"
OPTIONS = "/actions/review/update-options"


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def setup_pages(browser):
    """The supplied Anna/Bea/Clara distribution, through supported HTTP forms only."""
    page = start(browser)
    yield page
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/update-players"),
        forehand_label="Anna", middlehand_label="Bea", rearhand_label="Clara"))
    yield page
    page = follow(browser, browser.submit(native_cards(page, DEAL_ACTION, **DEAL)))
    yield page
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/update-declaration")))
    yield page
    yield follow(browser, browser.submit(native_cards(page, DISCARD_ACTION,
                                                      discarded_cards=DEAL["skat"])))


def play_page(browser):
    return list(setup_pages(browser))[-1]


def append(browser, page, card):
    return follow(browser, browser.submit(Forms(page).find(PLAY), card=card))


def assert_radios(page, locale, allowed, *, selected=()):
    tree = Hierarchy(page)
    assert_ids_and_labels(tree)
    for node in tree.nodes:
        for attr in ("aria-describedby", "aria-labelledby"):
            for identity in node["attrs"].get(attr, "").split():
                assert tree.by_id(identity)
    palette = tree.by_id("field-card")
    assert palette["tag"] == "fieldset"
    assert {"card-palette", "compact-cards"} <= set(palette["attrs"]["class"].split())
    assert palette["attrs"]["data-validation-group"] == "card"
    assert "data-balanced-grid" in palette["attrs"]
    assert page.count('<!-- validation-messages:card -->') == 1
    assert [n["text"] for n in descendants(tree, palette, "legend")] == [
        text(locale, "task.card.choose")]
    form = next(n for n in palette["parents"] if n["tag"] == "form")
    assert form["attrs"]["action"] == PLAY and form["attrs"]["method"] == "post"
    assert "data-language-form" in form["attrs"]
    assert {"revision", "_frontend_form_instance"} <= Forms(page).find(PLAY)["values"].keys()
    expected = tuple(c for c in CARDS if c in allowed)
    groups = [n for n in descendants(tree, palette, "div")
              if n["attrs"].get("class") == "compact-card-group"]
    suits = tuple(s for s in "CSHD" if any(c[0] == s for c in expected))
    assert len(groups) == len(suits)
    for group, suit in zip(groups, suits, strict=True):
        assert [n["text"] for n in descendants(tree, group, "h4")] == [
            text(locale, "task.card.suit." + suit)]
        assert tuple(n["attrs"]["value"] for n in descendants(tree, group, "input")) == tuple(
            c for c in expected if c[0] == suit)
    controls = [n for n in descendants(tree, form, "input") if n["attrs"].get("name") == "card"]
    assert tuple(n["attrs"]["value"] for n in controls) == expected
    assert not descendants(tree, form, "select")
    for node in controls:
        attrs = node["attrs"]
        assert attrs["type"] == "radio" and "required" in attrs
        assert attrs["aria-label"] == card_name(locale, attrs["value"])
        assert ("checked" in attrs) == (attrs["value"] in selected)
        assert not {"form", "onchange", "onclick", "disabled", "tabindex"} & attrs.keys()
        assert node["parents"][-1]["tag"] == "label"
    buttons = descendants(tree, form, "button")
    assert len(buttons) == 1 and buttons[0]["text"] == text(locale, "task.command.record_play")
    for error in (n for n in tree.nodes if n["attrs"].get("class") == "field-error"):
        assert not any("compact-card" in p["attrs"].get("class", "") for p in error["parents"]
                       if p["tag"] != "fieldset")
    return tree


def assert_footer(page, step):
    tree = Hierarchy(page)
    assert_ids_and_labels(tree)
    footer = next(n for n in tree.nodes if n["attrs"].get("class") == "wizard-actions")
    assert footer["parents"][-1]["attrs"]["class"] == "wizard"
    forms = descendants(tree, footer, "form")
    assert [n["attrs"]["action"] for n in forms] == ([BACK] if step > 1 else []) + [RESET]
    for form in forms:
        assert form["parents"][-1] is footer and form["attrs"]["method"] == "post"
        assert "data-preserve-fields" in form["attrs"]
        assert not any(n["tag"] == "form" for n in form["parents"])
        values = Forms(page).find(form["attrs"]["action"])["values"]
        assert set(values) == {"revision", "_frontend_form_instance"}
        button, = descendants(tree, form, "button")
        assert button["attrs"]["type"] == "submit"
        assert button["attrs"]["class"] == (
            "secondary" if form["attrs"]["action"] == BACK else "destructive")
    consent, = [n for n in descendants(tree, forms[-1], "input")
                if n["attrs"].get("name") == "confirm_reset"]
    assert consent["attrs"]["type"] == "checkbox" and "required" in consent["attrs"]
    assert "checked" not in consent["attrs"]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_legal_palette_explicit_chronology_trick_undo_back_and_singleton(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, play_page(browser), locale)
    context = localized_server.app_context
    before = snapshot(context)
    original = context.review_state
    assert_radios(page, locale, DEAL["forehand_hand"])
    assert context.review_state is original
    page = append(browser, page, "SA")
    view = build_historical_play_view_v1(context.review_state.draft)
    assert context.review_state.revision == original.revision + 1
    assert view.acting_player_id == "frontend-middlehand"
    assert tuple(p.card for p in view.current_trick_plays) == ("SA",)
    assert_radios(page, locale, ("SK", "SQ", "S9", "S8", "S7"))
    page = append(browser, page, "SK")
    page = append(browser, page, "H9")
    view = build_historical_play_view_v1(context.review_state.draft)
    assert view.acting_player_id == view.last_trick_winner_player_id == "frontend-forehand"
    assert view.next_leader_player_id == "frontend-forehand"
    assert not view.current_trick_plays and len(view.completed_tricks) == 1
    assert_radios(page, locale, tuple(c for c in DEAL["forehand_hand"] if c != "SA"))
    page = follow(browser, browser.submit(Forms(page).find(UNDO)))
    draft = context.review_state.draft
    assert len(draft.plays) == 2
    assert build_historical_play_view_v1(draft).acting_player_id == "frontend-rearhand"
    page = follow(browser, browser.submit(Forms(page).find(BACK)))
    assert context.review_state.draft.step == 4 and context.review_state.draft.plays == draft.plays
    page = follow(browser, browser.submit(Forms(page).find(DISCARD_ACTION)))
    for _ in range(2):
        page = follow(browser, browser.submit(Forms(page).find(UNDO)))
    page = append(browser, page, "CJ")
    assert build_historical_play_view_v1(context.review_state.draft).legal_cards == ("SJ",)
    assert_radios(page, locale, ("SJ",))
    assert snapshot(context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("values", ({}, {"card": ""}, {"card": ["SK", "SQ"]},
    {"card": ["SK", "SK"]}, {"card": "invalid"}, {"card": "HA"}, {"card": "CA"}))
def test_rejection_leaves_actor_and_plays_with_real_feedback_outside_tiles(
    localized_server, locale, values,
):
    browser = Browser(localized_server)
    page = switch(browser, append(browser, play_page(browser), "SA"), locale)
    context = localized_server.app_context
    state = context.review_state
    form = Forms(page).find(PLAY)
    form["values"].pop("card", None)
    response = browser.submit(form, **values)
    assert response[0] == 400
    page = response[2].decode()
    tree = assert_radios(page, locale, ("SK", "SQ", "S9", "S8", "S7"))
    summary, = [n for n in tree.nodes if n["attrs"].get("class") == "error-summary"]
    assert "autofocus" in summary["attrs"] and summary["attrs"]["tabindex"] == "-1"
    for link in descendants(tree, summary, "a"):
        assert tree.visible(tree.by_id(link["attrs"]["href"][1:]))
    if tree.by_id("field-card")["attrs"].get("aria-invalid") == "true":
        assert tree.by_id("field-card")["attrs"]["tabindex"] == "-1"
    assert context.review_state is state
    assert build_historical_play_view_v1(state.draft).acting_player_id == "frontend-middlehand"


@pytest.mark.parametrize("locale", ("de", "en"))
def test_safe_rejected_radio_and_language_return_selected_and_explicit_empty(
    localized_server, locale,
):
    browser = Browser(localized_server)
    page = switch(browser, play_page(browser), locale)
    context = localized_server.app_context
    state = context.review_state
    response = browser.submit(Forms(page).find(PLAY), card="CA", revision=str(state.revision - 1))
    assert response[0] == 409
    page = response[2].decode()
    assert_radios(page, locale, DEAL["forehand_hand"], selected=("CA",))
    other = "en" if locale == "de" else "de"
    page = switch(browser, page, other)
    assert_radios(page, other, DEAL["forehand_hand"], selected=("CA",))
    for cards in (["C10"], []):
        page = follow(browser, enhanced_switch(browser, page,
            envelope(page, PLAY, {"card": cards}), locale))
        assert_radios(page, locale, DEAL["forehand_hand"], selected=cards)
        assert context.review_state is state
    # No unavailable tile can be introduced by a forged enhanced return.
    profile = context.frontend_profile
    assert enhanced_switch(browser, page, envelope(page, PLAY, {"card": ["DA"]}), other)[0] == 400
    assert context.frontend_profile is profile and context.review_state is state


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("operation", (PLAY, UNDO, BACK))
@pytest.mark.parametrize("enhanced", (False, True))
def test_old_language_and_play_forms_reject_after_accepted_operation(
    localized_server, locale, operation, enhanced,
):
    browser = Browser(localized_server)
    page = switch(browser, append(browser, play_page(browser), "SA"), locale)
    old_play = Forms(page).find(PLAY)
    language = Forms(page).find("/actions/profile/language")
    raw = envelope(page, PLAY, {"card": ["SK"]}) if enhanced else None
    follow(browser, browser.submit(Forms(page).find(operation),
                                   **({"card": "SK"} if operation == PLAY else {})))
    context = localized_server.app_context
    state, profile = context.review_state, context.frontend_profile
    assert browser.submit(old_play, card="SK")[0] == 409
    assert browser.submit(language, language="en" if locale == "de" else "de",
        **({"_frontend_language_values": raw} if enhanced else {}))[0] == 409
    assert context.review_state is state and context.frontend_profile is profile


@pytest.mark.parametrize("locale", ("de", "en"))
def test_all_seven_footers_complete_back_continue_and_explicit_reset(localized_server, locale):
    browser = Browser(localized_server)
    switch(browser, browser.page("/review"), locale)
    context = localized_server.app_context
    before = snapshot(context)
    for step, page in enumerate(setup_pages(browser), 1):
        assert_footer(page, step)
    while len(context.review_state.draft.plays) < 30:
        view = build_historical_play_view_v1(context.review_state.draft)
        assert_radios(page, locale, view.legal_cards)
        page = append(browser, page, view.legal_cards[0])
    assert context.review_state.draft.step == 6
    assert_footer(page, 6)
    completed = context.review_state.draft.plays
    page = follow(browser, browser.submit(Forms(page).find(BACK)))
    assert_footer(page, 5)
    assert 'name="card"' not in page and 'id="field-card"' not in page
    assert set(Forms(page).find(PLAY)["values"]) == {"revision", "_frontend_form_instance"}
    page = follow(browser, browser.submit(Forms(page).find(PLAY)))
    assert context.review_state.draft.step == 6 and context.review_state.draft.plays == completed
    page = follow(browser, browser.submit(Forms(page).find(OPTIONS)))
    assert_footer(page, 7)
    state = context.review_state
    response = browser.submit(Forms(page).find(RESET))
    assert response[0] == 400 and context.review_state is state
    page = response[2].decode()
    assert_footer(page, 7)
    page = follow(browser, browser.submit(Forms(page).find(RESET), confirm_reset="on"))
    assert context.review_state.draft is None
    assert context.review_state.revision == state.revision + 1
    assert snapshot(context) == before
