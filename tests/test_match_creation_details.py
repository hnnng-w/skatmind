"""R01g: one fresh-open disclosure and lossless hidden Settings compatibility."""

import json
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode

import pytest
from frontend_creation_forms import new_name_roster
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

from skatmind.app_web.form_registry import FRONTEND_FORM_REGISTRY
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.frontend_profile_contracts import FrontendInterfacePreferencesV1
from skatmind.app_web.frontend_profile_operations import save_prepared_frontend_profile_v1
from skatmind.app_web.frontend_profile_persistence import (
    load_frontend_profile_file_v1,
    save_frontend_profile_file_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1

PREFERENCES = "/actions/profile/preferences"
CREATE = "/matches/api/v1/create"
FIELD = "advanced_settings_expanded"
ADVANCED_FIELDS = (
    "external_match_id", "forehand_platform_id", "middlehand_platform_id",
    "rearhand_platform_id", "source_kind", "source_title", "source_channel_name",
    "match_timecode_start", "match_timecode_end",
)


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.controls = []
        self.details = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"input", "select", "textarea"}:
            self.controls.append(attrs)
        if tag == "details":
            self.details.append(attrs)


def form_block(page, route):
    return next(m[0] for m in re.finditer(r"<form\b.*?</form>", page, re.S)
                if f'action="{route}"' in m[0])


def seed_profile(app, stored, zone=None):
    if stored is not None:
        assert save_prepared_frontend_profile_v1(app,
            requested=build_local_frontend_profile_v1(
                interface_preferences=FrontendInterfacePreferencesV1(stored, zone)),
            expected_generation=0) == "saved"


def profile_bytes(app):
    path = app.frontend_profile.profile_path
    return path.read_bytes() if path.exists() else None


def outer_details(page):
    return next(d for d in Markup(form_block(page, CREATE)).details
                if d.get("class") == "advanced-settings")


@pytest.mark.parametrize("stored,zone", ((None, None), (False, None), (True, None),
                                         (False, "UTC"), (True, "Europe/Berlin")))
@pytest.mark.parametrize("locale", ("de", "en"))
def test_fresh_open_is_independent_of_profile_and_preserves_optional_fields(
    localized_server, stored, zone, locale,
):
    app = localized_server.app_context
    seed_profile(app, stored, zone)
    browser = Browser(localized_server)
    before, generation = profile_bytes(app), app.frontend_profile.generation
    for _ in range(2):
        page = browser.request("GET", "/matches/new",
                               headers={"Accept-Language": locale})[2].decode()
        block = form_block(page, CREATE)
        parsed = Markup(block)
        assert "open" in outer_details(page)
        assert [(d.get("class"), "open" in d) for d in parsed.details] == [
            ("local-time-editor", False), ("advanced-settings", True), ("technical-details", False)]
        assert "id" not in outer_details(page)
        controls = [c for c in parsed.controls if c.get("name") in ADVANCED_FIELDS]
        assert tuple(c["name"] for c in controls) == ADVANCED_FIELDS
        assert all("required" not in c and not c.get("value") for c in controls)
        assert Forms(page).find(CREATE)["values"]["time_form"] == "match-create"
    assert profile_bytes(app) == before and app.frontend_profile.generation == generation
    assert load_frontend_profile_file_v1(app.managed_home.root).status == (
        "absent" if stored is None else "available")


@pytest.mark.parametrize("stored", (None, False, True))
@pytest.mark.parametrize("locale", ("de", "en"))
def test_real_settings_hidden_multimap_and_unrelated_noop_saves(localized_server, stored, locale):
    app = localized_server.app_context
    seed_profile(app, stored)
    browser = Browser(localized_server)
    before, generation = profile_bytes(app), app.frontend_profile.generation
    page = browser.request("GET", "/settings", headers={"Accept-Language": locale})[2].decode()
    block = form_block(page, PREFERENCES)
    hidden = [c for c in Markup(block).controls if c.get("name") == FIELD]
    assert len(hidden) == 1 and hidden[0]["type"] == "hidden"
    assert hidden[0]["value"] == ("on" if stored else "")
    assert "Start Advanced creation details expanded" not in page
    assert "Erweiterte Erfassungsangaben anfangs öffnen" not in page
    assert "Optional Match creation details start open." not in page
    assert "Optionale Match-Angaben werden anfangs aufgeklappt." not in page
    form = Forms(page).find(PREFERENCES)
    assert set(form["values"]) == {FIELD, "profile_generation", "own_player_handle",
        "platform_choice", "custom_platform", "_frontend_form_instance"}
    assert parse_qs(urlencode(form["values"]), keep_blank_values=True)[FIELD] == [
        "on" if stored else ""]
    assert profile_bytes(app) == before
    follow(browser, browser.submit(form))
    assert profile_bytes(app) == before and app.frontend_profile.generation == generation
    page = follow(browser, browser.submit(Forms(browser.page("/settings")).find(PREFERENCES),
                                        platform_choice="custom", custom_platform="Synthetic club"))
    assert app.frontend_profile.document.interface_preferences.advanced_settings_expanded is bool(
        stored)
    assert app.frontend_profile.document.preferred_game_platform == "Synthetic club"
    assert app.frontend_profile.generation == generation + 1
    changed = profile_bytes(app)
    follow(browser, browser.submit(Forms(page).find(PREFERENCES)))
    assert profile_bytes(app) == changed and app.frontend_profile.generation == generation + 1
    assert load_frontend_profile_file_v1(app.managed_home.root).document == (
        app.frontend_profile.document)


def test_compatibility_field_is_not_editable_registry_metadata():
    form = next(f for f in FRONTEND_FORM_REGISTRY if f.form_key == "profile.preferences")
    assert tuple(f.field_key for f in form.safe_fields) == (
        "own_player_handle", "platform_choice", "custom_platform", "profile_generation")


@pytest.mark.parametrize("stored", (False, True))
def test_hidden_regeneration_after_error_language_and_overlay_rejection(localized_server, stored):
    app = localized_server.app_context
    seed_profile(app, stored)
    browser = Browser(localized_server)
    page = browser.page("/settings")
    original = profile_bytes(app)
    raw = envelope(page, PREFERENCES, {FIELD: ["" if stored else "on"]})
    assert enhanced_switch(browser, page, raw)[0] == 400
    assert profile_bytes(app) == original
    # A valid legacy value is still accepted by transport, but an unrelated error
    # cannot turn it into accepted profile state or a reflected hidden override.
    response = browser.submit(Forms(browser.page("/settings")).find(PREFERENCES),
        platform_choice="custom", custom_platform="", **{FIELD: "" if stored else "on"})
    assert response[0] == 400
    page = response[2].decode()
    assert Forms(page).find(PREFERENCES)["values"][FIELD] == ("on" if stored else "")
    assert profile_bytes(app) == original
    page = follow(browser, enhanced_switch(browser, page,
        envelope(page, PREFERENCES, {"custom_platform": ["Unsent club"]})))
    values = Forms(page).find(PREFERENCES)["values"]
    assert values[FIELD] == ("on" if stored else "")
    assert values["custom_platform"] == "Unsent club"
    assert app.frontend_profile.document.interface_preferences.advanced_settings_expanded is stored
    assert app.frontend_profile.document.language == "de"
    assert app.frontend_profile.document.preferred_game_platform is None


def test_language_closure_then_fresh_default_and_error_priority(localized_server):
    browser = Browser(localized_server)
    page = browser.page("/matches/new")
    page = follow(browser, enhanced_switch(browser, page, envelope(page, CREATE, {
        "source_title": ["Unsent title"]})))
    assert "open" not in outer_details(page)
    assert Forms(page).find(CREATE)["values"]["source_title"] == "Unsent title"
    # Consumed language overlay is not a persistent preference.
    page = browser.page("/matches/new")
    assert "open" in outer_details(page)
    page = switch(browser, page, "en")  # Native/no-script language form, no DOM collapse payload.
    assert "open" in outer_details(page)
    response = browser.submit(Forms(page).find(CREATE), **new_name_roster(),
        match_title="Synthetic Match", perspective_seat="forehand", setup_action="update",
        source_kind="manual_observation", source_url="https://example.invalid/video")
    assert response[0] == 400
    page = response[2].decode()
    assert 'name="source_kind" aria-invalid="true"' in page
    page = follow(browser, enhanced_switch(browser, page, envelope(page, CREATE, {})))
    assert "open" in outer_details(page)
    assert 'name="source_kind" aria-invalid="true"' in page
    assert localized_server.app_context.managed_stateful.active_match is None


@pytest.mark.parametrize("stored", (None, False, True))
def test_update_opens_but_changed_advanced_values_still_require_review(localized_server, stored):
    app = localized_server.app_context
    seed_profile(app, stored)
    browser = Browser(localized_server)
    form = Forms(browser.page("/matches/new")).find(CREATE)
    response = browser.submit(form, **new_name_roster(), match_title="Synthetic Match",
        perspective_seat="forehand", source_title="Reviewed title", setup_action="update")
    assert response[0] == 303 and response[1]["location"] == "/matches/new"
    page = follow(browser, response)
    assert "open" in outer_details(page)
    form = Forms(page).find(CREATE)
    assert form["values"]["source_title"] == "Reviewed title"
    before = profile_bytes(app)
    response = browser.submit(form, source_title="Edited title", setup_action="create")
    assert response[0] == 400 and app.managed_stateful.active_match is None
    assert profile_bytes(app) == before
    page = response[2].decode()
    page = follow(browser, browser.submit(Forms(page).find(CREATE), setup_action="update"))
    assert "open" in outer_details(page)
    form = Forms(page).find(CREATE)
    response = browser.submit(form, setup_action="create")
    assert response[0] == 303 and response[1]["location"] == "/matches/position/1#match-recording"
    active = app.managed_stateful.active_match
    assert active is not None and active.path.exists()
    assert b"Edited title" in active.path.read_bytes()
    assert app.frontend_profile.document.interface_preferences.advanced_settings_expanded is bool(
        stored)
    saved = active.path.read_bytes()
    assert browser.submit(form, setup_action="create")[0] == 409
    assert active.path.read_bytes() == saved and app.managed_stateful.active_match is active


@pytest.mark.parametrize("value,expected", ((None, False), ("", False), ("on", True)))
def test_legacy_omitted_empty_on_remain_real_supported_changes(localized_server, value, expected):
    app = localized_server.app_context
    seed_profile(app, not expected, "UTC")
    browser = Browser(localized_server)
    form = Forms(browser.page("/settings")).find(PREFERENCES)
    if value is None:
        del form["values"][FIELD]
    else:
        form["values"][FIELD] = value
    follow(browser, browser.submit(form))
    assert app.frontend_profile.document.interface_preferences.to_dict() == {
        FIELD: expected, "time_zone": "UTC"}
    assert app.frontend_profile.generation == 2
    assert "open" in outer_details(browser.page("/matches/new"))


@pytest.mark.parametrize("value", ("true", "off", ["on", ""], ["on", "on"]))
def test_invalid_and_duplicate_compatibility_inputs_do_not_write(localized_server, value):
    app = localized_server.app_context
    seed_profile(app, True)
    browser = Browser(localized_server)
    before = profile_bytes(app)
    response = browser.submit(Forms(browser.page("/settings")).find(PREFERENCES), **{FIELD: value})
    assert response[0] == 400
    assert profile_bytes(app) == before and app.frontend_profile.generation == 1
    assert Forms(response[2].decode()).find(PREFERENCES)["values"][FIELD] == "on"


def test_stale_generation_and_actual_external_cas_preserve_accepted_hidden_value(localized_server):
    app = localized_server.app_context
    seed_profile(app, True)
    browser = Browser(localized_server)
    stale = Forms(browser.page("/settings")).find(PREFERENCES)
    follow(browser, browser.submit(stale, platform_choice="euroskat"))
    before = profile_bytes(app)
    assert browser.submit(stale, **{FIELD: ""})[0] == 409
    assert profile_bytes(app) == before
    accepted = app.frontend_profile.document
    external = build_local_frontend_profile_v1(revision=accepted.revision + 1)
    assert save_frontend_profile_file_v1(app.managed_home.root, external,
        expected_fingerprint=accepted.content_fingerprint).status == "saved"
    external_bytes = profile_bytes(app)
    response = browser.submit(Forms(browser.page("/settings")).find(PREFERENCES),
                              platform_choice="custom", custom_platform="External conflict")
    assert response[0] == 409 and b"Restart SkatMind" in response[2]
    assert profile_bytes(app) == external_bytes
    assert app.frontend_profile.document is accepted
    assert Forms(response[2].decode()).find(PREFERENCES)["values"][FIELD] == "on"


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_legacy_boolean_change_invalidates_pending_setup_and_language_source(
    localized_server, family,
):
    app = localized_server.app_context
    seed_profile(app, False)
    browser = Browser(localized_server)
    route = "/sessions" if family == "sessions" else "/matches/new"
    action = "/sessions/create" if family == "sessions" else CREATE
    page = browser.page(route)
    page = follow(browser, browser.submit(Forms(page).find(action), **new_name_roster(),
        **{"game_name" if family == "sessions" else "match_title": "Pending setup"},
        perspective_seat="forehand", setup_action="update"))
    form = Forms(page).find(action)
    language = Forms(page).find("/actions/profile/language")
    token = form["values"]["setup_context"]
    follow(browser, browser.submit(Forms(browser.page("/settings")).find(PREFERENCES),
                                  **{FIELD: "on"}))
    assert browser.submit(language, language="de")[0] == 409
    # Updating generation alone cannot resurrect the old reviewed setup/source.
    assert browser.submit(form, profile_generation=str(app.frontend_profile.generation),
                          setup_action="create")[0] == 409
    current = Forms(browser.page(route)).find(action)
    assert current["values"]["setup_context"] != token
    assert app.managed_stateful.active_session is app.managed_stateful.active_match is None


@pytest.mark.parametrize("interface", (None, {}, {"time_zone": "UTC"},
                                       {FIELD: "false"}, {FIELD: 0}))
def test_invalid_existing_profile_never_fabricates_preferences(tmp_path, interface):
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / "frontend-profile.json"
    value = build_local_frontend_profile_v1().to_dict()
    value["interface_preferences"] = interface
    raw = b"invalid JSON" if interface is None else (
        json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(raw)
    fixture = _localized_server.__wrapped__(tmp_path)
    server = next(fixture)
    try:
        browser = Browser(server)
        for route in ("/settings", "/matches/new"):
            page = browser.page(route)
            assert 'class="profile-warning"' in page
            assert PREFERENCES not in page
            assert FIELD not in page and path.read_bytes() == raw
        # Match markup remains available with the existing warning, but its
        # mutation boundary still requires explicit invalid-profile recovery.
        assert browser.submit(Forms(page).find(CREATE), **new_name_roster(),
            match_title="Rejected invalid profile", perspective_seat="forehand",
            setup_action="update")[0] == 409
        assert path.read_bytes() == raw and server.app_context.managed_stateful.active_match is None
        assert load_frontend_profile_file_v1(home.root).status == "invalid"
    finally:
        fixture.close()
