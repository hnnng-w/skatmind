"""Saved display text suggestions over actual manual forms, never Player bindings."""

from html import escape

import pytest
from test_frontend_language_switching import localized_server as _server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_settings_seat_setup_web import player_action
from test_task_first_language_preservation import enhanced_switch, envelope

import skatmind.app_web.server as server_module
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.rendering import render_app_page_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

ACTION = "/actions/review/update-players"
FIELDS = ("forehand_label", "middlehand_label", "rearhand_label")
IDS = ("frontend-forehand", "frontend-middlehand", "frontend-rearhand")
NAMES = ('Alex <A & "B">', "Boris", "Clara")


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def add_names(browser, names=NAMES):
    for name in names:
        page = follow(browser, browser.submit(player_action(browser.page("/settings"), "edit")))
        follow(browser, browser.submit(player_action(page, "add"), display_name=name))


def start(browser):
    return follow(browser, browser.submit(Forms(browser.page("/review")).find(
        "/actions/review/start")))


def snapshot(context):
    root = context.managed_home.root
    return {p.relative_to(root): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob("*") if p.is_file()}


def assert_suggestions(page, locale, names):
    tree = Hierarchy(page)
    lists = [node for node in tree.nodes if node["tag"] == "datalist"]
    assert len(lists) == 1
    datalist = lists[0]
    identity = datalist["attrs"]["id"]
    options = tree.within(identity, "option")
    assert [node["attrs"]["value"] for node in options] == list(names)
    assert not any(node["attrs"].get("name") for node in [datalist, *options])
    inputs = [node for node in tree.within("workflow-form", "input")
              if node["attrs"].get("name") in FIELDS]
    assert len(inputs) == 3
    assert all(node["attrs"].get("list") == identity for node in inputs)
    assert all("required" not in node["attrs"] for node in inputs)
    ids = [node["attrs"]["id"] for node in tree.nodes if "id" in node["attrs"]]
    assert len(ids) == len(set(ids))
    assert page.count(text(locale, "guided.review.saved_names_help")) == 1
    for name in names:
        assert f'value="{escape(name, quote=True)}"' in page
    values = Forms(page).find(ACTION)["values"]
    assert set(values) == {*FIELDS, "revision", "_frontend_form_instance"}
    return values


@pytest.mark.parametrize("locale", ("de", "en"))
def test_valid_saved_names_are_optional_escaped_text_with_no_passive_writes(
    localized_server, locale,
):
    browser = Browser(localized_server)
    add_names(browser)
    page = switch(browser, start(browser), locale)
    context = localized_server.app_context
    profile = context.frontend_profile.document
    before = snapshot(context)
    accepted = context.review_state
    for route in ("/review", "/analyze", "/review/recorded", "/review"):
        page = browser.page(route)
        if route == "/review":
            values = assert_suggestions(page, locale, NAMES)
            assert all(values[field] == "" for field in FIELDS)
            assert all(player.player_id not in page for player in profile.known_players)
        else:
            assert '<datalist' not in page
        assert context.review_state is accepted
        assert snapshot(context) == before
    assert context.managed_stateful.active_session is context.managed_stateful.active_match is None


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("profile_status", ("absent", "empty", "invalid"))
def test_no_names_keeps_free_text_guidance_without_suggestion_hint(
    localized_server, locale, profile_status,
):
    browser = Browser(localized_server)
    if profile_status == "empty":
        switch(browser, browser.page("/review"), locale)
    if profile_status == "invalid":
        context = localized_server.app_context
        context.frontend_profile.profile_path.write_text('{"known_players":["Untrusted"]}')
        localized_server.app_context = AppWebContextV1.create(context.managed_home)
    page = start(browser)
    page = browser.request("GET", "/review", headers={"Accept-Language": locale})[2].decode()
    tree = Hierarchy(page)
    assert not any(node["tag"] == "datalist" or "list" in node["attrs"] for node in tree.nodes)
    assert 'id="review-player-name-help"' not in page
    # Invalid profiles retain the existing English fallback, even with a German header.
    resolved_locale = "en" if profile_status == "invalid" else locale
    assert text(resolved_locale, "guided.review.players_help") in page
    assert "Untrusted" not in page
    before = snapshot(localized_server.app_context)
    page = follow(browser, browser.submit(Forms(page).find(ACTION),
        forehand_label="", middlehand_label="Typed visitor", rearhand_label=""))
    draft = localized_server.app_context.review_state.draft
    assert draft.step == 2
    assert tuple(p.player_label for p in draft.players) == (None, "Typed visitor", None)
    assert tuple(p.player_id for p in draft.players) == IDS
    assert snapshot(localized_server.app_context) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("enhanced", (False, True))
def test_duplicate_rejection_and_language_return_keep_editable_labels(
    localized_server, locale, enhanced,
):
    browser = Browser(localized_server)
    add_names(browser)
    page = switch(browser, start(browser), locale)
    accepted = localized_server.app_context.review_state
    values = assert_suggestions(page, locale, NAMES)
    assert all(values[field] == "" for field in FIELDS)
    response = browser.submit(Forms(page).find(ACTION), forehand_label=NAMES[0],
                              middlehand_label=NAMES[0], rearhand_label="Visitor")
    assert response[0] == 400
    page = response[2].decode()
    assert 'class="error-summary"' in page and "autofocus" in page
    other = "en" if locale == "de" else "de"
    raw = envelope(page, ACTION, {"rearhand_label": ["Unsent visitor"]}) if enhanced else None
    page = (follow(browser, enhanced_switch(browser, page, raw, other)) if enhanced
            else switch(browser, page, other))
    values = assert_suggestions(page, other, NAMES)
    assert values["forehand_label"] == values["middlehand_label"] == NAMES[0]
    assert values["rearhand_label"] == ("Unsent visitor" if enhanced else "Visitor")
    assert localized_server.app_context.review_state is accepted
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == "/review"
    page = follow(browser, browser.submit(Forms(page).find(ACTION), middlehand_label=""))
    draft = localized_server.app_context.review_state.draft
    assert draft.step == 2 and tuple(p.player_id for p in draft.players) == IDS
    assert draft.players[0].player_label == NAMES[0]
    assert draft.players[1].player_label is None
    assert '<datalist' not in page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_profile_rename_does_not_rename_draft_or_invalidate_previously_offered_text(
    localized_server, locale,
):
    browser = Browser(localized_server)
    add_names(browser)
    page = switch(browser, start(browser), locale)
    offered = Forms(page).find(ACTION)
    page = follow(browser, browser.submit(offered, forehand_label=NAMES[0],
                                        middlehand_label="Independent visitor", rearhand_label=""))
    context = localized_server.app_context
    accepted = context.review_state
    player = context.frontend_profile.document.known_players[0]
    handle = build_known_player_handle_v1(player.player_id)
    page = follow(browser, browser.submit(player_action(browser.page("/settings"), "edit", handle)))
    follow(browser, browser.submit(player_action(page, "update", handle),
                                   display_name="Renamed Alex"))
    assert context.review_state is accepted
    assert tuple(p.player_id for p in accepted.draft.players) == IDS
    assert accepted.draft.players[0].player_label == NAMES[0]
    before = snapshot(context)
    page = browser.page("/review")
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/back")))
    values = assert_suggestions(page, locale, ("Renamed Alex", *NAMES[1:]))
    assert values["forehand_label"] == NAMES[0]
    assert values["middlehand_label"] == "Independent visitor"
    follow(browser, browser.submit(Forms(page).find(ACTION)))
    assert context.review_state.draft.players == accepted.draft.players
    assert snapshot(context) == before


def test_server_projects_only_immutable_names_under_existing_profile_boundary(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    add_names(browser)
    start(browser)
    seen = []
    original = server_module.render_app_page_v1

    def observed(*args, **kwargs):
        seen.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(server_module, "render_app_page_v1", observed)
    page = browser.page("/review")
    assert_suggestions(page, "en", NAMES)
    assert seen[-1]["profile"] is None
    assert type(seen[-1]["review_player_names"]) is tuple
    assert seen[-1]["review_player_names"] == NAMES
    with pytest.raises(ValueError, match="Private profile"):
        render_app_page_v1(localized_server.app_context.browser_state, "/review",
                          profile=localized_server.app_context.frontend_profile.document)
