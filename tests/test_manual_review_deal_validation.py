"""Manual deal feedback through emitted HTTP forms and retained language return."""

import pytest
from test_completed_trick_input_grouping import assert_accessibility_references, descendants
from test_frontend_language_switching import localized_server as _server
from test_guided_card_palettes import (
    DEAL,
    DEAL_ACTION,
    assert_palette,
    deal_page,
    native_cards,
)
from test_language_switch_context import switch
from test_manual_review_saved_names import snapshot
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

import skatmind.app_web.workflow_operations as operations
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

REPORTED = {**DEAL, "rearhand_hand": tuple(c for c in DEAL["rearhand_hand"] if c != "H7")}


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def assert_count_rejection(page, locale, selections, field, required, *, initial=True):
    tree = Hierarchy(page)
    summary, = [n for n in tree.nodes if n["attrs"].get("class") == "error-summary"]
    links = descendants(tree, summary, "a")
    assert "#field-" + field in [n["attrs"]["href"] for n in links], [n["text"] for n in links]
    link, = [n for n in links if n["attrs"]["href"] == "#field-" + field]
    for item in links:
        assert tree.visible(tree.by_id(item["attrs"]["href"][1:]))
    message = text(locale, "validation.review.deal_count", actual=len(selections[field]),
                   required=required)
    label = text(locale, "task.skat" if field == "skat" else
                 "creation.seat." + field.removesuffix("_hand"))
    assert link["text"] == label + ": " + message
    assert ("autofocus" in summary["attrs"]) == initial
    assert summary["attrs"]["tabindex"] == "-1"
    group = tree.by_id("field-" + field)
    assert tree.visible(group)
    assert group["attrs"]["aria-invalid"] == "true" and group["attrs"]["tabindex"] == "-1"
    inline, = [tree.by_id(identifier) for identifier in group["attrs"]["aria-describedby"].split()]
    assert inline["text"] == message and inline["parents"][-1] is group
    assert inline["attrs"]["class"] == "field-error"
    assert_accessibility_references(tree)
    for name, cards in selections.items():
        assert_palette(page, locale, name, DEAL_ACTION, selected=cards)
        palette = tree.by_id("field-" + name)
        assert palette["attrs"]["data-validation-group"] == name
        caption, = [n for n in descendants(tree, palette, "p")
                    if n["attrs"].get("class") != "field-error"]
        assert caption["text"] == text(locale, "guided.review.cards_required",
                                       count=2 if name == "skat" else 10)
        assert "data-validation-card-count" not in caption["attrs"]
    return tree


@pytest.mark.parametrize("locale", ("de", "en"))
def test_reported_deal_rejection_language_return_and_explicit_correction(
    localized_server, locale, monkeypatch,
):
    def forbidden(*args, **kwargs):
        pytest.fail("Manual deal validation must not execute analysis or review")
    monkeypatch.setattr(operations, "execute_guided_frontend_analysis_v1", forbidden)
    monkeypatch.setattr(operations, "execute_guided_frontend_review_v1", forbidden)
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    context = localized_server.app_context
    before, state = snapshot(context), context.review_state
    emitted = native_cards(page, DEAL_ACTION, **REPORTED)
    assert {"revision", "_frontend_form_instance"} <= emitted["values"].keys()
    response = browser.submit(emitted)
    assert response[0] == 400
    page = response[2].decode()
    for language in (locale, "en" if locale == "de" else "de"):
        if language != locale:
            page = switch(browser, page, language)
            after = snapshot(context)
            assert {str(path) for path in before.keys() | after.keys()
                    if before.get(path) != after.get(path)} == {"frontend-profile.json"}
            before = after
        assert_count_rejection(page, language, REPORTED, "rearhand_hand", 10,
                               initial=language == locale)
        assert sum(len(cards) for cards in REPORTED.values()) == 31
        assert context.review_state is state and state.draft.step == 2
        assert snapshot(context) == before
    # Correct the returned native form; all other checks must survive unchanged.
    returned = Forms(page).find(DEAL_ACTION)
    assert set(returned["values"]["rearhand_hand"]) == set(REPORTED["rearhand_hand"])
    page = follow(browser, browser.submit(native_cards(
        page, DEAL_ACTION, rearhand_hand=(*REPORTED["rearhand_hand"], "H7"))))
    assert context.review_state.revision == state.revision + 1
    assert context.review_state.draft.step == 3
    assert tuple(p.initial_hand for p in context.review_state.draft.players) == tuple(
        DEAL.values())[:3]
    assert context.review_state.draft.skat == DEAL["skat"]
    assert Forms(page).find("/actions/review/update-declaration")
    assert snapshot(context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("field", tuple(DEAL))
@pytest.mark.parametrize("size", ("empty", "short", "excess"))
def test_each_group_exact_counts_with_safe_native_selections(localized_server, locale, field, size):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    if size == "empty":
        page = follow(browser, browser.submit(native_cards(page, DEAL_ACTION, **DEAL)))
        page = follow(browser, browser.submit(Forms(page).find("/actions/review/back")))
    context = localized_server.app_context
    state, before = context.review_state, snapshot(context)
    selections = dict(DEAL)
    if size == "excess":
        # Transfer a real Card; do not mask excess with a cross-group duplicate.
        donor = next(name for name in DEAL if name != field)
        selections[field] = (*DEAL[field], DEAL[donor][0])
        selections[donor] = DEAL[donor][1:]
    else:
        selections[field] = () if size == "empty" else DEAL[field][:-1]
    response = browser.submit(native_cards(page, DEAL_ACTION, **selections))
    assert response[0] == 400
    page = response[2].decode()
    required = 2 if field == "skat" else 10
    assert_count_rejection(page, locale, selections, field, required)
    assert context.review_state is state and snapshot(context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
def test_enhanced_return_preserves_diagnostic_and_static_requirement(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    context = localized_server.app_context
    state = context.review_state
    page = browser.submit(native_cards(page, DEAL_ACTION, **REPORTED))[2].decode()
    other = "en" if locale == "de" else "de"
    page = follow(browser, enhanced_switch(browser, page, envelope(
        page, DEAL_ACTION, {name: list(cards) for name, cards in REPORTED.items()}), other))
    assert_count_rejection(page, other, REPORTED, "rearhand_hand", 10, initial=False)
    # Pending selections are presentation only; the diagnostic describes the rejected POST.
    page = follow(browser, enhanced_switch(browser, page, envelope(
        page, DEAL_ACTION, {name: list(cards) for name, cards in DEAL.items()}), locale))
    for field, cards in DEAL.items():
        assert_palette(page, locale, field, DEAL_ACTION, selected=cards)
    assert text(locale, "validation.review.deal_count", actual=9, required=10) in page
    assert page.count(text(locale, "guided.review.cards_required", count=10)) == 3
    assert context.review_state is state
    follow(browser, browser.submit(Forms(page).find(DEAL_ACTION)))
    assert context.review_state.draft.step == 3


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("kind", (
    "within_duplicate", "cross_duplicate", "duplicate_and_short", "invalid_and_short",
    "blank", "padded", "unsupported", "repeated_revision", "stale",
))
def test_other_authoritative_rejections_are_not_count_diagnostics(localized_server, locale, kind):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    context = localized_server.app_context
    state, before = context.review_state, snapshot(context)
    form = native_cards(page, DEAL_ACTION, **REPORTED)
    values = form["values"]
    if kind in {"within_duplicate", "cross_duplicate"}:
        values["rearhand_hand"] = list(DEAL["rearhand_hand"])
        values["rearhand_hand"][0] = "H9" if kind == "within_duplicate" else "CA"
    elif kind == "duplicate_and_short":
        values["rearhand_hand"] = [*REPORTED["rearhand_hand"], "H9"]
        values["forehand_hand"] = list(DEAL["forehand_hand"][:-1])
    elif kind in {"invalid_and_short", "blank", "padded"}:
        values["rearhand_hand"] = [*REPORTED["rearhand_hand"], {
            "invalid_and_short": "ZZ", "blank": "", "padded": " H7"}[kind]]
        values["forehand_hand"] = list(DEAL["forehand_hand"][:-1])
    elif kind == "unsupported":
        values["unsupported"] = "H7"
    elif kind == "repeated_revision":
        values["revision"] = [str(state.revision), str(state.revision)]
    else:
        values["revision"] = str(state.revision - 1)
    response = browser.submit(form)
    assert response[0] == (409 if kind == "stale" else 400)
    page = response[2].decode()
    assert "error-summary" in page
    assert text(locale, "validation.review.deal_count", actual=9, required=10) not in page
    if "duplicate" in kind:
        assert text(locale, "validation.message.duplicate") in page
    elif kind in {"invalid_and_short", "blank", "padded"}:
        assert text(locale, "validation.message.card_conflict") in page
    elif kind == "stale":
        assert text(locale, "validation.message.stale") in page
    assert context.review_state is state and snapshot(context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
def test_old_deal_and_language_forms_reject_after_accepted_advance(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, deal_page(browser), locale)
    rejected = native_cards(page, DEAL_ACTION, **REPORTED)
    page = browser.submit(rejected)[2].decode()
    language = Forms(page).find("/actions/profile/language")
    follow(browser, browser.submit(native_cards(page, DEAL_ACTION, **DEAL)))
    context = localized_server.app_context
    state, profile = context.review_state, context.frontend_profile
    assert browser.submit(rejected)[0] == 409
    assert browser.submit(language, language="en" if locale == "de" else "de")[0] == 409
    # A forged fresh revision still cannot bypass the accepted step guard.
    rejected["values"]["revision"] = str(state.revision)
    assert browser.submit(rejected)[0] == 400
    assert context.review_state is state and context.frontend_profile is profile
