"""Delivered guided forms: suit layout must not reorder native submitted Cards."""

import pytest
from test_completed_trick_input_grouping import (
    assert_accessibility_references,
    assert_ids_and_labels,
    descendants,
)
from test_frontend_language_switching import localized_server as _server
from test_language_switch_context import switch
from test_manual_review_saved_names import snapshot, start
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

import skatmind.app_web.workflow_operations as operations
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

CARDS = tuple(s + r for s in "CSHD" for r in ("A", "10", "K", "Q", "J", "9", "8", "7"))
DEAL = dict(zip(("forehand_hand", "middlehand_hand", "rearhand_hand", "skat"),
                (CARDS[:10], CARDS[10:20], CARDS[20:30], CARDS[30:]), strict=True))
DEAL_ACTION = "/actions/review/update-deal"
DISCARD_ACTION = "/actions/review/update-discards"
ANALYZE_ACTION = "/actions/analyze/run-guided"


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def deal_page(browser):
    return follow(browser, browser.submit(Forms(start(browser)).find(
        "/actions/review/update-players")))


def native_cards(page, action, **selections):
    """Choose from emitted controls, serializing checkboxes in their real DOM order."""
    tree = Hierarchy(page)
    form = next(n for n in tree.nodes if n["tag"] == "form" and n["attrs"]["action"] == action)
    emitted = descendants(tree, form, "input")
    values = Forms(page).find(action)
    for field, selected in selections.items():
        controls = [n["attrs"] for n in emitted if n["attrs"].get("name") == field]
        assert controls and all(c["type"] == "checkbox" for c in controls)
        assert set(selected) <= {c["value"] for c in controls}
        values["values"][field] = [c["value"] for c in controls if c["value"] in selected]
    return values


def assert_palette(page, locale, field, action, *, allowed=CARDS, selected=(), feedback=False):
    tree = Hierarchy(page)
    assert_ids_and_labels(tree)
    palette = tree.by_id("field-" + field)
    assert palette["tag"] == "fieldset"
    assert {"card-palette", "compact-cards"} <= set(palette["attrs"]["class"].split())
    assert "data-balanced-grid" in palette["attrs"]
    form = next(n for n in palette["parents"] if n["tag"] == "form")
    assert form["attrs"]["id"] == "workflow-form"
    assert form["attrs"]["action"] == action and form["attrs"]["method"] == "post"
    assert "data-language-form" in form["attrs"]
    transport = Forms(page).find(action)["values"]
    assert "revision" in transport and "_frontend_form_instance" in transport
    groups = [n for n in descendants(tree, palette, "div")
              if n["attrs"].get("class") == "compact-card-group"]
    expected = tuple(c for c in CARDS if c in allowed)
    suits = tuple(s for s in "CSHD" if any(c[0] == s for c in expected))
    assert len(groups) == len(suits)
    for group, suit in zip(groups, suits, strict=True):
        assert [n["text"] for n in descendants(tree, group, "h4")] == [
            text(locale, "task.card.suit." + suit)]
        assert tuple(n["attrs"]["value"] for n in descendants(tree, group, "input")) == tuple(
            c for c in expected if c[0] == suit)
    inputs = descendants(tree, palette, "input")
    assert tuple(n["attrs"]["value"] for n in inputs) == expected
    assert len(inputs) == len(set(expected))
    for node in inputs:
        attrs = node["attrs"]
        assert attrs["name"] == field and attrs["type"] == "checkbox"
        assert attrs["aria-label"] == card_name(locale, attrs["value"])
        assert ("checked" in attrs) == (attrs["value"] in selected)
        assert not {"disabled", "required", "form", "tabindex"} & attrs.keys()
        assert node["parents"][-1]["tag"] == "label"
    assert not any(n["attrs"].get("class") in {
        "compact-selection", "compact-count", "compact-selected"}
        for n in descendants(tree, palette, "p") + descendants(tree, palette, "span"))
    if feedback:
        assert palette["attrs"]["data-validation-group"] == field
        counts = [n for n in descendants(tree, palette, "p")
                  if n["attrs"].get("data-validation-card-count") == field]
        assert len(counts) == 1
        assert counts[0]["text"] == text(locale, "guided.cards_selected", count=len(set(selected)))
        assert page.count(f'<!-- validation-messages:{field} -->') == 1
    return tree


@pytest.mark.parametrize("locale", ("de", "en"))
def test_all_complete_palettes_are_grouped_without_reordering_or_passive_writes(
    localized_server, locale, monkeypatch,
):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    before = snapshot(localized_server.app_context)
    state = localized_server.app_context.review_state
    def forbidden(*args, **kwargs):
        pytest.fail("Presentation must not execute a Product workflow")
    monkeypatch.setattr(operations, "execute_guided_frontend_analysis_v1", forbidden)
    monkeypatch.setattr(operations, "execute_guided_frontend_review_v1", forbidden)
    for field in DEAL:
        assert_palette(page, locale, field, DEAL_ACTION)
    page = browser.page("/analyze")
    for field in ("hand", "skat", "public_declarer_cards"):
        assert_palette(page, locale, field, ANALYZE_ACTION, feedback=True)
    assert localized_server.app_context.review_state is state
    assert snapshot(localized_server.app_context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("hand", (False, True))
def test_complete_deal_restricted_discards_hand_and_back_use_actual_forms(
    localized_server, locale, hand,
):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    before = snapshot(localized_server.app_context)
    stale = native_cards(page, DEAL_ACTION, **DEAL)
    page = follow(browser, browser.submit(stale))
    assert browser.submit(stale)[0] == 409
    draft = localized_server.app_context.review_state.draft
    assert tuple(p.initial_hand for p in draft.players) == tuple(DEAL.values())[:3]
    assert draft.skat == DEAL["skat"]
    declaration = Forms(page).find("/actions/review/update-declaration")
    if hand:
        declaration["values"]["hand_game"] = "on"
    page = follow(browser, browser.submit(declaration))
    if hand:
        assert 'name="discarded_cards"' not in page
        submit = Forms(page).find(DISCARD_ACTION)
    else:
        allowed = (*DEAL["forehand_hand"], *DEAL["skat"])
        assert_palette(page, locale, "discarded_cards", DISCARD_ACTION, allowed=allowed)
        submit = native_cards(page, DISCARD_ACTION, discarded_cards=DEAL["skat"])
    page = follow(browser, browser.submit(submit))
    assert localized_server.app_context.review_state.draft.step == 5
    assert localized_server.app_context.review_state.draft.discarded_cards == (
        () if hand else DEAL["skat"])
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/back")))
    if not hand:
        assert_palette(page, locale, "discarded_cards", DISCARD_ACTION,
                       allowed=allowed, selected=DEAL["skat"])
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/back")))
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/back")))
    for field, cards in DEAL.items():
        assert_palette(page, locale, field, DEAL_ACTION, selected=cards)
    assert snapshot(localized_server.app_context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("duplicate", (False, True))
def test_rejected_deal_preserves_selections_and_native_language_return(
    localized_server, locale, duplicate,
):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    state = localized_server.app_context.review_state
    rejected = {**DEAL, "forehand_hand": CARDS[:9]}
    if duplicate:
        rejected["forehand_hand"] = (*CARDS[:9], CARDS[10])
    response = browser.submit(native_cards(page, DEAL_ACTION, **rejected))
    assert response[0] == 400
    page = response[2].decode()
    tree = Hierarchy(page)
    assert_ids_and_labels(tree)
    summary = next(n for n in tree.nodes if n["attrs"].get("class") == "error-summary")
    for link in descendants(tree, summary, "a"):
        # Historical deal-wide diagnostics may target the whole form.
        assert tree.visible(tree.by_id(link["attrs"]["href"][1:]))
    for language in (locale, "en" if locale == "de" else "de"):
        if language != locale:
            page = switch(browser, page, language)
        for field, cards in rejected.items():
            assert_palette(page, language, field, DEAL_ACTION, selected=cards)
        assert localized_server.app_context.review_state is state
    page = follow(browser, browser.submit(native_cards(page, DEAL_ACTION, **DEAL)))
    assert localized_server.app_context.review_state.draft.step == 3


@pytest.mark.parametrize("locale", ("de", "en"))
def test_analysis_counts_rejected_values_and_enhanced_language_return(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/analyze"), locale)
    selections = {"hand": ("CA", "C10", "CJ"), "skat": ("S7",),
                  "public_declarer_cards": ("HA", "HJ")}
    response = browser.submit(native_cards(page, ANALYZE_ACTION, **selections))
    assert response[0] == 400
    page = response[2].decode()
    state = localized_server.app_context.analyze_state
    assert state.latest_successful_result is None
    assert_accessibility_references(Hierarchy(page))
    for field, cards in selections.items():
        assert_palette(page, locale, field, ANALYZE_ACTION, selected=cards, feedback=True)
    other = "en" if locale == "de" else "de"
    page = switch(browser, page, other)
    for field, cards in selections.items():
        assert_palette(page, other, field, ANALYZE_ACTION, selected=cards, feedback=True)
    pending = {"hand": ["D7", "CJ", "CA"], "skat": [], "public_declarer_cards": ["S10"]}
    page = follow(browser, enhanced_switch(browser, page, envelope(
        page, ANALYZE_ACTION, pending), locale))
    # The presentation overlay retains native pending checks; the accepted state is untouched.
    for field, cards in pending.items():
        assert_palette(page, locale, field, ANALYZE_ACTION, selected=cards)
    assert localized_server.app_context.analyze_state is state


@pytest.mark.parametrize("locale", ("de", "en"))
def test_restricted_rejection_and_enhanced_return_never_expand_membership(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    page = follow(browser, browser.submit(native_cards(page, DEAL_ACTION, **DEAL)))
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/update-declaration")))
    allowed = (*DEAL["forehand_hand"], *DEAL["skat"])
    state = localized_server.app_context.review_state
    response = browser.submit(native_cards(page, DISCARD_ACTION, discarded_cards=("CA",)))
    assert response[0] == 400
    page = response[2].decode()
    assert_palette(page, locale, "discarded_cards", DISCARD_ACTION,
                   allowed=allowed, selected=("CA",))
    other = "en" if locale == "de" else "de"
    page = follow(browser, enhanced_switch(browser, page, envelope(
        page, DISCARD_ACTION, {"discarded_cards": ["D7", "CJ"]}), other))
    assert_palette(page, other, "discarded_cards", DISCARD_ACTION,
                   allowed=allowed, selected=("D7", "CJ"))
    assert localized_server.app_context.review_state is state
    # Forged unavailable values still reach the existing validator, never a new tile.
    response = browser.submit(Forms(page).find(DISCARD_ACTION), discarded_cards=["HA", "H10"])
    assert response[0] == 400
    assert_palette(response[2].decode(), other, "discarded_cards", DISCARD_ACTION, allowed=allowed)
    assert localized_server.app_context.review_state is state


@pytest.mark.parametrize("locale", ("de", "en"))
def test_native_position_submission_retains_exact_request_array_order(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/analyze"), locale)
    form = native_cards(page, ANALYZE_ACTION, hand=tuple(reversed(CARDS[:10])), skat=CARDS[-2:])
    form["values"]["sample_count"] = "1"
    page = follow(browser, browser.submit(form))
    state = localized_server.app_context.analyze_state
    assert state.draft.hand == CARDS[:10] and state.draft.skat == CARDS[-2:]
    import json

    request = json.loads(browser.request("GET", "/downloads/analyze/request.json")[2])
    assert request["hand"] == list(CARDS[:10]) and request["skat"] == list(CARDS[-2:])
    assert_palette(page, locale, "hand", ANALYZE_ACTION, selected=CARDS[:10], feedback=True)
