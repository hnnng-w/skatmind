"""R01f: lower reset composition and unchanged real profile/file boundaries."""

import re
from html import escape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import known_players, switch
from test_match_recording_recovery_web import follow
from test_recording_entry_settings_navigation import assert_shell, main_content
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first

import skatmind.app_web.frontend_profile_operations as operations
import skatmind.app_web.frontend_profile_persistence as persistence
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.player_seat_setup import current_seat_setup_v1
from skatmind.app_web.profile_player_contracts import ManagedItemDisplayLabelV1
from skatmind.app_web.profile_player_operations import set_frontend_creation_preferences_v1
from skatmind.app_web.profile_player_operations import set_managed_item_display_label_v1 as label
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1

RECOMMENDED = "/actions/profile/recommended-defaults/reset"
FULL = "/actions/profile/reset"
CONSENT = {RECOMMENDED: "confirm_recommended_reset", FULL: "confirm_reset"}

# Independent visible-scope expectations, not a Product reset-map helper.
CAPTIONS = {
    "en": ("Reset", "Restore recommended defaults", "Reset entire local profile"),
    "de": ("Zurücksetzen", "Empfohlene Voreinstellungen wiederherstellen",
           "Lokales Profil vollständig zurücksetzen"),
}
SCOPE = {
    "en": (
        "Keeps language, time zone, saved players, your player and recording names/dates.",
        "Recording files, independent Learning copies and exports remain; displayed names/dates "
        "may fall back.",
        "Language follows the browser or application default.",
    ),
    "de": (
        "Sprache, Zeitzone, gespeicherte Spieler, eigener Spieler und Namen/Datumsangaben "
        "der Aufzeichnungen bleiben erhalten.",
        "Aufzeichnungsdateien, unabhängige Lernen-Kopien und Exporte bleiben erhalten; "
        "angezeigte Namen/Datumsangaben können auf Ersatzwerte zurückfallen.",
        "Die Sprache folgt dem Browser oder der Anwendungsvorgabe.",
    ),
}


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def populate_profile(browser):
    """Supported real operations, including the compatible non-UI perspective field."""
    known_players(browser)
    context = browser.server.app_context
    profile = context.frontend_profile.document
    assert set_frontend_creation_preferences_v1(context,
        own_player_id=profile.known_players[0].player_id,
        preferred_perspective_player_id=profile.known_players[1].player_id,
        preferred_game_platform="Synthetic club", advanced_settings_expanded=True,
        expected_generation=context.frontend_profile.generation) == "saved"
    page = browser.page("/settings")
    follow(browser, browser.submit(Forms(page).find("/actions/profile/time-zone"),
                                  time_zone="America/New_York"))
    switch(browser, browser.page("/settings"), "de")
    return context.frontend_profile.document


@pytest.mark.parametrize("populated", (False, True))
@pytest.mark.parametrize("locale", ("de", "en"))
def test_one_lower_reset_area_after_all_ordinary_settings(localized_server, locale, populated):
    browser = Browser(localized_server)
    if populated:
        populate_profile(browser)
        switch(browser, browser.page("/settings"), locale)
    page = browser.request("GET", "/settings", headers={"Accept-Language": locale})[2].decode()
    assert_shell(page)
    body = main_content(page)
    assert '<p><a href="/sessions">' not in body and '<a href="/matches/new">' not in body
    area = re.search(r'<section[^>]*aria-labelledby="settings-reset-heading"[^>]*>(.*)</section>',
                     body, re.S)
    assert area, "Both existing reset forms must share one lower, visibly headed area"
    before = body[:area.start()]
    assert before.index('class="local-settings"') < before.index('class="secondary-action"')
    assert RECOMMENDED not in before and FULL not in before
    assert [f["action"] for f in Forms(area[0]).forms] == [RECOMMENDED, FULL]
    assert "<details" not in area[0]
    assert page.index(area[0]) < page.index("<footer")
    for caption in CAPTIONS[locale]:
        assert escape(caption) in area[0]
    for route, field in CONSENT.items():
        assert len([f for f in Forms(page).forms if f["action"] == route]) == 1
        form = Forms(page).find(route)
        assert field not in form["values"]
        assert set(form["values"]) == {"profile_generation", "_frontend_form_instance"} | (
            {"return_to"} if route == FULL else set())
        assert re.search(rf'<input type="checkbox" name="{field}" value="on" required', area[0])
    assert Forms(page).find(FULL)["values"]["return_to"] == "/settings"
    assert [f["action"] for f in Forms(before).forms][-2:] == [
        "/actions/profile/preferences", "/actions/profile/time-zone"]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_literal_copy_distinguishes_profile_labels_from_recordings(localized_server, locale):
    page = Browser(localized_server).request(
        "GET", "/settings", headers={"Accept-Language": locale})[2].decode()
    for statement in SCOPE[locale]:
        assert escape(statement) in page
    assert "factory reset" not in page.lower()
    assert "delete all Games" not in page


def saved_sources(browser):
    """One short recording per family and a genuine independently persisted Corpus copy."""
    from test_recorded_decision_context_web import record_context_match

    record_live_game(browser, play_count=3)
    review_first(browser)
    record_context_match(browser)
    follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/create"),
                                  collection_name="Synthetic independent collection"))
    follow(browser, browser.submit(Forms(browser.page("/matches/position/1")).find(
        "/matches/transfer-workspace")))
    app = browser.server.app_context
    session, match, learning = (app.managed_stateful.active_session,
                               app.managed_stateful.active_match,
                               app.managed_stateful.active_learning)
    store = load_learning_corpus_directory_v1(learning.path)
    assert len(store.document.catalog.current_matches) == 1
    files = {p: p.read_bytes() for p in learning.path.rglob("*.json")}
    assert len(files) == 2  # Catalog and immutable Snapshot, not a fabricated sentinel.
    files.update({session.path: session.path.read_bytes(), match.path: match.path.read_bytes()})
    downloads = {}
    for kind in ("request", "result"):
        route = f"/sessions/downloads/{kind}.json"
        status, _, raw = browser.request("GET", route)
        assert status == 200
        downloads[route] = raw
        exported = app.managed_home.root.parent / f"independent-{kind}.json"
        exported.write_bytes(raw)
        files[exported] = raw
    return files, downloads


def assert_reload(context):
    loaded = persistence.load_frontend_profile_file_v1(context.managed_home.root)
    assert loaded.status == "available" and loaded.document == context.frontend_profile.document
    reopened = AppWebContextV1.create(context.managed_home)
    assert reopened.frontend_profile.document == loaded.document


def test_real_resets_keep_exact_sources_and_retained_result_with_actual_lifecycle(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    files, downloads = saved_sources(browser)
    app = localized_server.app_context
    session, match, learning = (app.managed_stateful.active_session,
                               app.managed_stateful.active_match,
                               app.managed_stateful.active_learning)
    retained, source = session.execution, session.recorded_review_source
    populate_profile(browser)
    label(app, label=ManagedItemDisplayLabelV1("sessions", session.state.session_id,
        "Private synthetic title"),
        expected_generation=app.frontend_profile.generation)
    label(app, label=ManagedItemDisplayLabelV1("matches", match.workspace.match_definition.match_id,
        "Private Match title", "2026-09-02"), expected_generation=app.frontend_profile.generation)
    profile = app.frontend_profile.document
    assert len(profile.managed_item_display_labels) == 3
    follow(browser, browser.submit(Forms(browser.page("/review")).find("/actions/review/start")))
    manual = app.review_state
    setup = current_seat_setup_v1(app, "sessions", profile)
    page = browser.page("/settings")
    editor_form = Forms(page).find("/actions/profile/players/remove-preview")
    follow(browser, browser.submit(editor_form))
    editor = app.settings_editor
    page = browser.page("/settings")
    stale_overlay = Forms(page).find("/actions/profile/language")
    original_bytes = app.frontend_profile.profile_path.read_bytes()
    saved = []
    real_save = operations.save_frontend_profile_file_v1

    def counted(*args, **kwargs):
        result = real_save(*args, **kwargs)
        saved.append(result.status)
        return result

    monkeypatch.setattr(operations, "save_frontend_profile_file_v1", counted)
    for route in (RECOMMENDED, FULL):
        form = Forms(page).find(route)
        status, _, raw = browser.submit(form)  # Server rejection, not native validation.
        assert status == 400
        rejected = raw.decode()
        assert 'class="error-summary"' in rejected
        assert CONSENT[route] not in Forms(rejected).find(route)["values"]
        assert app.frontend_profile.profile_path.read_bytes() == original_bytes
        assert saved == [] and session.execution is retained
        page = browser.page("/settings")

    generation = app.frontend_profile.generation
    stale_full = Forms(page).find(FULL)
    response = browser.submit(Forms(page).find(RECOMMENDED), confirm_recommended_reset="on")
    assert response[0] == 303 and response[1]["location"] == "/settings"
    page = follow(browser, response)
    reset = app.frontend_profile.document
    assert reset.revision == profile.revision + 1
    assert app.frontend_profile.generation == generation + 1 and saved == ["saved"]
    assert reset.language == "de" and '<html lang="de">' in page
    assert reset.known_players == profile.known_players
    assert reset.own_player_id == profile.own_player_id
    assert reset.interface_preferences.time_zone == "America/New_York"
    assert reset.interface_preferences.advanced_settings_expanded is False
    assert reset.preferred_perspective_player_id is None and reset.preferred_game_platform is None
    assert reset.workflow_preferences.to_dict() == {"position_analysis": None,
                                                   "historical_review": None}
    assert reset.managed_item_display_labels == profile.managed_item_display_labels
    assert_reload(app)
    assert current_seat_setup_v1(app, "sessions", reset) is not setup
    assert app.settings_editor is editor and editor.generation != app.frontend_profile.generation
    assert 'name="confirm_replace"' not in page
    assert app.language_context.pending is None
    assert browser.submit(stale_overlay, language="en")[0] == 409
    assert browser.submit(stale_full, confirm_reset="on")[0] == 409
    assert saved == ["saved"]
    assert session.execution is retained and session.recorded_review_source is source
    assert all(browser.request("GET", route)[2] == raw for route, raw in downloads.items())
    assert all(path.read_bytes() == raw for path, raw in files.items())

    # Full reset uses a fresh emitted form and does not secretly restore saved German.
    response = browser.submit(Forms(browser.page("/settings")).find(FULL), confirm_reset="on")
    assert response[0] == 303 and response[1]["location"] == "/settings"
    page = follow(browser, response)
    full = app.frontend_profile.document
    assert full.revision == reset.revision + 1 and saved == ["saved", "saved"]
    assert app.frontend_profile.generation == generation + 2
    assert full.language is None and '<html lang="en">' in page
    assert full.known_players == () and full.own_player_id is None
    assert full.preferred_perspective_player_id is None and full.preferred_game_platform is None
    assert full.interface_preferences.to_dict() == {"advanced_settings_expanded": False}
    assert full.workflow_preferences.to_dict() == {"position_analysis": None,
                                                  "historical_review": None}
    assert full.managed_item_display_labels == ()
    assert_reload(app)
    assert app.review_state is manual
    assert (app.managed_stateful.active_session, app.managed_stateful.active_match,
            app.managed_stateful.active_learning) == (session, match, learning)
    assert session.execution is retained and session.recorded_review_source is source
    assert all(browser.request("GET", route)[2] == raw for route, raw in downloads.items())
    assert all(path.read_bytes() == raw for path, raw in files.items())
    assert "Private synthetic title" not in browser.page("/sessions")
    assert saved == ["saved", "saved"]  # Discovery is distinct from reset writes.


@pytest.mark.parametrize("initial", ("absent", "default"))
def test_current_default_and_absent_operation_counts(localized_server, monkeypatch, initial):
    app = localized_server.app_context
    if initial == "default":
        operations.save_prepared_frontend_profile_v1(app,
            requested=build_local_frontend_profile_v1(), expected_generation=0)
    browser = Browser(localized_server)
    saves = []
    real = operations.save_frontend_profile_file_v1

    def counted(*args, **kwargs):
        result = real(*args, **kwargs)
        saves.append(result.status)
        return result

    monkeypatch.setattr(operations, "save_frontend_profile_file_v1", counted)
    generation = app.frontend_profile.generation
    before = app.frontend_profile.document
    for _ in range(2):
        follow(browser, browser.submit(Forms(browser.page("/settings")).find(RECOMMENDED),
                                      confirm_recommended_reset="on"))
    assert saves == [] and app.frontend_profile.generation == generation
    assert app.frontend_profile.document is before
    for index in range(2):
        follow(browser, browser.submit(Forms(browser.page("/settings")).find(FULL),
                                      confirm_reset="on"))
        assert app.frontend_profile.generation == generation + index + 1
        assert app.frontend_profile.document.revision == index + (initial == "default")
        assert_reload(app)
    assert saves == ["saved", "saved"]


@pytest.mark.parametrize("route", (RECOMMENDED, FULL))
def test_reset_failures_keep_accepted_profile_and_exact_forms(localized_server, monkeypatch, route):
    browser = Browser(localized_server)
    populate_profile(browser)
    app = localized_server.app_context
    before = app.frontend_profile
    raw = before.profile_path.read_bytes()

    def failed_replace(*args):
        raise OSError("Controlled atomic profile replacement failure")

    with monkeypatch.context() as patch:
        patch.setattr(persistence.os, "replace", failed_replace)
        assert browser.submit(Forms(browser.page("/settings")).find(route),
                              **{CONSENT[route]: "on"})[0] == 500
    assert app.frontend_profile is before and before.profile_path.read_bytes() == raw
    assert not tuple(app.managed_home.root.glob(".frontend-profile.json.*.tmp"))
    external = build_local_frontend_profile_v1(revision=before.document.revision + 1, language="en")
    assert persistence.save_frontend_profile_file_v1(app.managed_home.root, external,
        expected_fingerprint=before.expected_fingerprint).status == "saved"
    external_bytes = before.profile_path.read_bytes()
    status, _, raw = browser.submit(Forms(browser.page("/settings")).find(route),
                                   **{CONSENT[route]: "on"})
    assert status == 409 and app.frontend_profile is before
    assert 'class="error-summary"' in raw.decode()
    assert CONSENT[route] not in Forms(raw.decode()).find(route)["values"]
    assert before.profile_path.read_bytes() == external_bytes


def test_invalid_profile_recovery_emitted_full_form_only(tmp_path):
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / "frontend-profile.json"
    invalid = b"controlled invalid profile\n"
    path.write_bytes(invalid)
    fixture = _localized_server.__wrapped__(tmp_path)
    server = next(fixture)
    try:
        browser = Browser(server)
        page = browser.request("GET", "/settings", headers={"Accept-Language": "de"})[2].decode()
        assert '<html lang="en">' in page and 'class="profile-warning"' in page
        assert RECOMMENDED not in page and 'class="local-settings"' in page
        assert '/actions/profile/preferences' not in page
        assert page.index('class="profile-warning"') < page.index('settings-reset-heading')
        assert path.read_bytes() == invalid
        form = Forms(page).find(FULL)
        assert browser.submit(form)[0] == 400 and path.read_bytes() == invalid
        follow(browser, browser.submit(Forms(browser.page("/settings")).find(FULL),
                                      confirm_reset="on"))
        assert_reload(server.app_context)
        assert server.app_context.frontend_profile.document == build_local_frontend_profile_v1()
        assert server.app_context.frontend_profile.generation == 1
    finally:
        fixture.close()


@pytest.mark.parametrize("route", (RECOMMENDED, FULL))
def test_language_manifest_excludes_consent_and_authority(localized_server, route):
    from test_task_first_language_preservation import enhanced_switch, envelope

    browser = Browser(localized_server)
    populate_profile(browser)
    page = browser.page("/settings")
    block = next(value for value in re.findall(r'<form\b.*?</form>', page, re.S)
                 if f'action="{route}"' in value)
    # There are no safe editable controls in either reset form, so neither is in
    # the language-value manifest. Authority cannot enter via another form either.
    assert "data-language-form" not in block
    for field in (CONSENT[route], "profile_generation"):
        response = enhanced_switch(browser, page, envelope(
            page, "/actions/profile/preferences", {field: ["on"]}))
        assert response[0] == 400
        assert CONSENT[route] not in Forms(response[2].decode()).find(route)["values"]
    page = switch(browser, browser.page("/settings"), "en")
    for action, consent in CONSENT.items():
        assert consent not in Forms(page).find(action)["values"]
    assert browser.server.app_context.frontend_profile.document.preferred_game_platform == (
        "Synthetic club")


def test_settings_resets_do_not_consume_another_workflows_pending_acknowledgement(localized_server):
    from test_operation_feedback_web import notice, notices
    from test_session_direct_card_start_web import create

    browser = Browser(localized_server)
    page = create(browser)
    assert browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"])[0] == 303
    app = localized_server.app_context
    active = app.managed_stateful.active_session
    pending = active.operation_feedback.pending
    assert pending is not None
    saved = active.path.read_bytes()
    for route, consent in CONSENT.items():
        page = browser.page("/settings")
        assert not notices(page) and active.operation_feedback.pending is pending
        assert browser.submit(Forms(page).find(route), **{consent: "true"})[0] == 400
        assert active.operation_feedback.pending is pending
        page = follow(browser, browser.submit(Forms(browser.page("/settings")).find(route),
                                             **{consent: "on"}))
        assert not notices(page) and active.operation_feedback.pending is pending
        assert active.path.read_bytes() == saved
    notice(browser.page(), "initial_cards", count=1, player="Alex")
    assert not notices(browser.page())
