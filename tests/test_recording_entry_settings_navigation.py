"""R01a/c/d/e: rendered entry meaning, local shortcuts and real source retention."""

import re
from html import escape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_recorded_review_navigation import chooser_form, home_chooser
from test_session_recorded_review_web import Browser, Forms, record_live_game
from test_settings_seat_setup_web import player_action

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as t

ENTRY = {
    "de": "Ein Spiel erfassen oder eine gespeicherte Aufzeichnung öffnen.",
    "en": "Record one Game or open a saved recording.",
}
TECHNICAL = {
    "de": ("Entwicklung und Automatisierung", "Befehlszeilenschnittstellen und die öffentliche "
           "Python-API (Vertragsversion 1) bieten Zugang für Skripte und Werkzeuge; "
           "für die normale Nutzung im Browser sind sie nicht erforderlich."),
    "en": ("Development and automation", "Command-line interfaces and the Public Python API "
           "(contract version 1) provide access for scripts and tools; ordinary browser use "
           "does not require them."),
}
TECHNICAL_FILES = ["README.md", "docs/installed_cli.md", "docs/public_python_api_v1.md",
                   "docs/unified_local_frontend_contract.md"]
TASKS = ["/matches", "/sessions", "/review/recorded", "/analyze", "/learning"]
NAVIGATION = ["/", *TASKS, "/settings"]


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def main_content(page):
    return page.split("<main", 1)[1].split("</main>", 1)[0]


def technical_section(page):
    return re.search(r'<section aria-labelledby="interfaces-heading">(.*?)</section>',
                     page, re.S)[1]


def assert_shell(page):
    navigation = re.search(r'<ul class="site-nav">(.*?)</ul>', page, re.S)[1]
    assert re.findall(r'href="([^"]+)"', navigation) == NAVIGATION
    footer = page.split("<footer", 1)[1].split("</footer>", 1)[0]
    assert re.findall(r'href="([^"]+)"', footer) == ["/about"]


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("route", ("/", "/sessions"))
def test_recording_entry_literal_meaning_and_existing_destinations(localized_server, locale, route):
    browser = Browser(localized_server)
    status, _, raw = browser.request("GET", route, headers={"Accept-Language": locale})
    assert status == 200
    page = raw.decode()
    assert_shell(page)
    if route == "/":
        cards = re.findall(r'<article class="task-card">(.*?)</article>', page, re.S)
        assert [re.search(r'href="([^"]+)"', card)[1] for card in cards] == TASKS
        assert re.findall(r'<section class="home-group" aria-labelledby="([^"]+)"', page) == [
            "home-group-record_games", "home-group-analyze_and_review",
            "home-group-learn_across_matches"]
        assert f'<p class="task-summary">{ENTRY[locale]}</p>' in cards[1]
        assert escape(t(locale, "home.task.record_session.title")) in cards[1]
        assert escape(t(locale, "home.task.record_session.action")) in cards[1]
        assert escape(t(locale, "home.task.review_game.summary")) in cards[2]
        assert escape(t(locale, "home.task.analyze_decision.summary")) in cards[3]
    else:
        assert f'<p class="entry-introduction">{ENTRY[locale]}</p>' in page
        assert len(re.findall('class="entry-introduction"', page)) == 1
        assert Forms(page).find("/sessions/create")
        assert 'value="live"' in page and 'value="retrospective"' in page
    assert not localized_server.app_context.frontend_profile.profile_path.exists()


@pytest.mark.parametrize("locale", ("de", "en"))
def test_settings_removes_only_loose_body_creation_links(localized_server, locale):
    browser = Browser(localized_server)
    page = browser.request("GET", "/settings", headers={"Accept-Language": locale})[2].decode()
    assert_shell(page)
    body = main_content(page)
    assert '<p><a href="/sessions">' not in body
    assert '<a href="/matches/new">' not in body
    forms = Forms(page).forms
    assert [f["action"] for f in forms] == ["/actions/profile/language",
        "/actions/profile/players/edit", "/actions/profile/preferences",
        "/actions/profile/time-zone", "/actions/profile/recommended-defaults/reset",
        "/actions/profile/reset"]
    assert Forms(page).find("/actions/profile/preferences")["values"][
        "advanced_settings_expanded"] == ""
    for name in ("confirm_recommended_reset", "confirm_reset"):
        assert re.search(rf'<input type="checkbox" name="{name}" value="on" required', page)
        assert all(name not in f["values"] for f in forms)
    assert Forms(page).find("/actions/profile/reset")["values"]["return_to"] == "/settings"
    assert escape(t(locale, "profile.reset.description")) in page
    assert '<input type="hidden" name="advanced_settings_expanded" value="">' in page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_about_removes_only_generic_body_settings_link(localized_server, locale):
    browser = Browser(localized_server)
    page = browser.request("GET", "/about", headers={"Accept-Language": locale})[2].decode()
    assert_shell(page)
    assert '<p><a href="/settings">' not in main_content(page)
    assert "AGPL-3.0-only" in page and "Copyright (C) 2026 Henning Wiese" in page
    assert "Python &gt;=3.13" in page and "CPython 3.13" in page
    assert '<details class="storage-disclosure"><summary>' in page
    assert [f["action"] for f in Forms(page).forms] == ["/actions/profile/language"]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_about_technical_purpose_and_exact_nonclickable_inventory(localized_server, locale):
    browser = Browser(localized_server)
    page = browser.request("GET", "/about", headers={"Accept-Language": locale})[2].decode()
    section = technical_section(page)
    heading, explanation = TECHNICAL[locale]
    assert f'<h2 id="interfaces-heading">{heading}</h2>' in section
    assert f'<p>{explanation}</p>' in section
    assert re.findall(r'<code>(.*?)</code>', section) == TECHNICAL_FILES
    assert not re.findall(r'<(?:a|button|form|details)\b|href=', section)
    assert section.count('<p>') == 2


def test_invalid_profile_contextual_settings_remedy_survives(localized_server):
    context = localized_server.app_context
    context.frontend_profile.profile_path.write_text("{}", encoding="utf-8")
    localized_server.app_context = AppWebContextV1.create(context.managed_home)
    browser = Browser(localized_server)
    for route in ("/", "/sessions", "/settings", "/about"):
        page = browser.page(route)
        warning = re.search(r'<aside class="profile-warning".*?</aside>', page, re.S)[0]
        assert 'href="/settings"' in warning
        assert escape(t("en", "profile.invalid_warning")) in warning
        assert_shell(page)
    assert context.frontend_profile.profile_path.read_bytes() == b"{}"


def test_emitted_settings_validation_language_recovery_and_form_identity(localized_server):
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(player_action(browser.page("/settings"), "edit")))
    form = player_action(page, "add")
    response = browser.submit(form, display_name='Synthetic <A & B>', account_platform="club")
    assert response[0] == 400
    page = response[2].decode()
    assert 'class="error-summary"' in page
    page = switch(browser, page, "de")
    retained = player_action(page, "add")
    assert (retained["values"]["_frontend_form_instance"]
            == form["values"]["_frontend_form_instance"])
    assert retained["values"]["display_name"] == 'Synthetic <A & B>'
    assert retained["values"]["account_platform"] == "club"
    assert 'Synthetic &lt;A &amp; B&gt;' in page
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == "/settings"
    response = browser.submit(retained, account_id="synthetic-1")
    page = follow(browser, response)
    assert response[1]["location"] == "/settings"
    context = localized_server.app_context
    player = context.frontend_profile.document.known_players[0]
    assert player.display_name == 'Synthetic <A & B>'
    assert player.platform_player_ids[0].player_id == "synthetic-1"
    profile = context.frontend_profile.profile_path.read_bytes()
    for route in ("/", "/about", "/settings"):
        assert_shell(browser.page(route))
    assert context.frontend_profile.profile_path.read_bytes() == profile
    assert context.managed_stateful.active_session is context.managed_stateful.active_match is None


def test_short_recording_real_result_receipt_and_same_source_navigation(localized_server):
    browser = Browser(localized_server)
    record_live_game(browser, play_count=3)
    context = localized_server.app_context
    active = context.managed_stateful.active_session
    pending = active.operation_feedback.pending
    assert pending is not None
    for route in ("/", "/settings", "/about"):
        browser.page(route)
        assert active.operation_feedback.pending is pending
    page = browser.page()
    assert 'data-operation-feedback' in page and active.operation_feedback.pending is None
    response = browser.submit(Forms(page).find("/sessions/review-decision"))
    follow(browser, response)
    retained, source = active.execution, active.recorded_review_source
    assert retained is not None and source is not None
    disk = active.path.read_bytes()
    downloads = {kind: browser.request("GET", f"/sessions/downloads/{kind}.json")[2]
                 for kind in ("request", "result")}
    profile = context.frontend_profile.profile_path.read_bytes()
    for route in ("/", "/settings", "/about", "/sessions"):
        browser.page(route)
    assert context.frontend_profile.profile_path.read_bytes() == profile
    page = home_chooser(browser)
    assert 'href="/review"' in page  # Independent manual completed-Game entry remains.
    page = follow(browser, browser.submit(chooser_form(page, "sessions")))
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        assert active.execution is retained and active.recorded_review_source is source
        assert context.managed_stateful.active_session is active
        assert active.path.read_bytes() == disk
        for kind, raw in downloads.items():
            assert browser.request("GET", f"/sessions/downloads/{kind}.json")[2] == raw
    assert 'data-operation-feedback' not in browser.page()
