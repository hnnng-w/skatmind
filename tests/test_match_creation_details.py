"""Grouped native creation controls and lossless hidden Settings compatibility."""

import json
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode

import pytest
from frontend_creation_forms import new_name_roster
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
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
    "rearhand_platform_id",
)
SOURCE_FIELDS = (
    "source_url", "source_kind", "source_title", "source_channel_name",
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


def outer_details(page, kind="advanced-settings"):
    return next(d for d in Markup(form_block(page, CREATE)).details
                if d.get("class") == kind)


@pytest.mark.parametrize("stored,zone", ((None, None), (False, None), (True, None),
                                         (False, "UTC"), (True, "Europe/Berlin")))
@pytest.mark.parametrize("locale", ("de", "en"))
def test_fresh_closed_groups_are_independent_of_profile_and_preserve_optional_fields(
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
        assert "open" not in outer_details(page)
        assert [(d.get("class"), "open" in d) for d in parsed.details] == [
            ("match-optional-details", False), ("local-time-editor", False),
            ("save-defaults", False), ("advanced-settings", False), ("technical-details", False)]
        assert "id" not in outer_details(page)
        controls = [c for c in parsed.controls if c.get("name") in ADVANCED_FIELDS]
        assert tuple(c["name"] for c in controls) == ADVANCED_FIELDS
        assert all("required" not in c and not c.get("value") for c in controls)
        tree = Hierarchy(block)
        fields = [n for n in tree.nodes if n["tag"] in {"input", "select", "textarea"}]
        for name in (*ADVANCED_FIELDS, *SOURCE_FIELDS, "played_date", "local_date", "local_time",
                     "local_zone", "save_players", "save_platform"):
            matches = [n for n in fields if n["attrs"].get("name") == name]
            assert len(matches) == 1 and "disabled" not in matches[0]["attrs"]
            classes = [p["attrs"].get("class") for p in matches[0]["parents"]]
            assert ("advanced-settings" in classes) == (name in ADVANCED_FIELDS)
            assert ("match-source" in classes) == (name in SOURCE_FIELDS)
            assert ("video-source-fields" in classes) == (name in (
                "source_channel_name", "match_timecode_start", "match_timecode_end"))
            assert ("save-defaults" in classes) == name.startswith("save_")
        assert block.index('name="match_title"') < block.index('class="match-optional-details"')
        assert block.index('name="match_timecode_end"') < block.index('class="seat-entry"')
        assert [n["attrs"]["name"] for n in fields
                if n["attrs"].get("name") in SOURCE_FIELDS] == list(SOURCE_FIELDS)
        for name in ("save_players", "save_platform"):
            assert name not in Forms(page).find(CREATE)["values"]
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
        "platform_choice", "custom_platform", "live_effort", "analysis_effort",
        "_frontend_form_instance"}
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
        "own_player_handle", "platform_choice", "custom_platform",
        "live_effort", "analysis_effort", "profile_generation")


@pytest.mark.parametrize("stored", (False, True))
@pytest.mark.parametrize("include_view", (False, True))
def test_hidden_regeneration_after_error_language_and_overlay_rejection(
    localized_server, stored, include_view,
):
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
    values = json.loads(envelope(page, PREFERENCES, {"custom_platform": ["Unsent club"]}))
    if include_view:
        values["view"] = {"anchor": "id:main-content", "offset": -100, "x": 0, "focus": "de"}
    page = follow(browser, enhanced_switch(browser, page, json.dumps(values)))
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
    assert "open" not in outer_details(page)
    page = switch(browser, page, "en")  # Native/no-script language form, no DOM collapse payload.
    assert "open" not in outer_details(page)
    response = browser.submit(Forms(page).find(CREATE), **new_name_roster(),
        match_title="Synthetic Match", perspective_seat="forehand", setup_action="update",
        source_kind="manual_observation", source_url="https://example.invalid/video")
    assert response[0] == 400
    page = response[2].decode()
    assert 'name="source_kind" aria-invalid="true"' in page
    page = follow(browser, enhanced_switch(browser, page, envelope(page, CREATE, {})))
    assert "open" in outer_details(page, "match-optional-details")
    assert 'name="source_kind" aria-invalid="true"' in page
    assert localized_server.app_context.managed_stateful.active_match is None


@pytest.mark.parametrize("stored", (None, False, True))
def test_closed_groups_keep_reviewed_values_and_changed_source_still_requires_review(
    localized_server, stored,
):
    app = localized_server.app_context
    seed_profile(app, stored)
    browser = Browser(localized_server)
    form = Forms(browser.page("/matches/new")).find(CREATE)
    response = browser.submit(form, **new_name_roster(), match_title="Synthetic Match",
        perspective_seat="forehand", source_title="Reviewed title", setup_action="update")
    assert response[0] == 303 and response[1]["location"] == "/matches/new#match-setup-review"
    page = follow(browser, response)
    assert "open" not in outer_details(page)
    form = Forms(page).find(CREATE)
    assert form["values"]["source_title"] == "Reviewed title"
    before = profile_bytes(app)
    response = browser.submit(form, source_title="Edited title", setup_action="create")
    assert response[0] == 400 and app.managed_stateful.active_match is None
    assert profile_bytes(app) == before
    page = response[2].decode()
    page = follow(browser, browser.submit(Forms(page).find(CREATE), setup_action="update"))
    assert "open" not in outer_details(page)
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


@pytest.mark.parametrize("field,values,containers", (
    ("source_channel_name", {"source_channel_name": "Synthetic channel"},
     ("match-optional-details",)),
    ("match_timecode_start", {"source_url": "https://example.invalid/video",
                              "match_timecode_start": "bad"}, ("match-optional-details",)),
    ("match_timecode_end", {"source_url": "https://example.invalid/video",
                            "match_timecode_start": "00:02:00", "match_timecode_end": "00:01:00"},
     ("match-optional-details",)),
    ("local_time", {"local_date": "2026-03-29", "local_time": "02:30"},
     ("match-optional-details", "local-time-editor")),
    ("forehand_platform_id", {"forehand_platform_id": "x" * 256}, ("advanced-settings",)),
))
def test_errors_reveal_nested_controls_and_language_cannot_hide_them(
    localized_server, field, values, containers,
):
    browser = Browser(localized_server)
    response = browser.submit(Forms(browser.page("/matches/new")).find(CREATE),
        **new_name_roster(), match_title="Synthetic retry", perspective_seat="forehand",
        setup_action="update", save_players="on", save_platform="on", **values)
    assert response[0] == 400
    page = response[2].decode()
    for locale in ("de", "en"):
        page = follow(browser, enhanced_switch(browser, page, envelope(page, CREATE, {}), locale))
        node = next(n for n in Hierarchy(page).nodes if n["attrs"].get("name") == field)
        assert node["attrs"]["aria-invalid"] == "true"
        assert Hierarchy.visible(node)
        assert [p["attrs"].get("class") for p in node["parents"]
                if p["tag"] == "details"] == list(containers)
        form = Forms(page).find(CREATE)
        assert form["values"][field] == values[field]
        assert form["values"]["save_players"] == form["values"]["save_platform"] == "on"
    assert localized_server.app_context.managed_stateful.active_match is None


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_save_defaults_unsent_choices_disclosures_and_native_review_survive_language(
    localized_server, family,
):
    app = localized_server.app_context
    browser = Browser(localized_server)
    route, action, title = (("/sessions", "/sessions/create", "game_name") if family == "sessions"
                            else ("/matches/new", CREATE, "match_title"))
    page = browser.page(route)
    fields = ("save_players",) if family == "sessions" else ("save_players", "save_platform")
    assert all(name not in Forms(page).find(action)["values"] for name in fields)
    for locale, selected in (("de", True), ("en", False), ("de", True)):
        disclosures = [d.get("class") == "save-defaults" for d in Markup(page).details]
        values = {name: ["on"] if selected else [] for name in fields}
        values[title] = ["Unsent synthetic title"]
        page = follow(browser, enhanced_switch(browser, page,
            envelope(page, action, values, disclosures=disclosures), locale))
        assert "open" in next(d for d in Markup(page).details
                              if d.get("class") == "save-defaults")
        form = Forms(page).find(action)
        assert form["values"][title] == "Unsent synthetic title"
        assert all((name in form["values"]) is selected for name in fields)
        assert app.frontend_profile.document.known_players == ()
        assert app.frontend_profile.document.preferred_game_platform is None
    page = follow(browser, browser.submit(form, **new_name_roster(),
        perspective_seat="forehand", setup_action="update"))
    page = switch(browser, page, "en")
    form = Forms(page).find(action)
    assert all(form["values"][name] == "on" for name in fields)
    follow(browser, browser.submit(form, setup_action="create"))
    assert len(app.frontend_profile.document.known_players) == 3
    assert app.frontend_profile.document.preferred_game_platform == (
        "Unknown" if family == "matches" else None)


@pytest.mark.parametrize("url,kind,title", (
    ("https://www.youtube.com/watch?v=synthetic", "youtube_video", ""),
    ("https://example.invalid/video", "other_video", "Alternate title"),
))
def test_automatic_source_and_title_fallback_survive_collapsed_native_submission(
    localized_server, url, kind, title,
):
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(Forms(browser.page("/matches/new")).find(CREATE),
        **new_name_roster(), match_title="Synthetic source", perspective_seat="forehand",
        setup_action="update", source_url=url, source_title=title,
        source_channel_name="Synthetic channel", match_timecode_start="00:01:00",
        match_timecode_end="00:02:00", played_date="2026-09-01"))
    assert "open" not in outer_details(page, "match-optional-details")
    assert Forms(page).find(CREATE)["values"]["source_kind"] == ""
    follow(browser, browser.submit(Forms(page).find(CREATE), setup_action="create"))
    active = localized_server.app_context.managed_stateful.active_match
    definition = active.workspace.match_definition
    assert definition.source.source_kind == kind and definition.source.source_url == url
    assert definition.source.source_title == (title or "Synthetic source")
    assert definition.source.source_channel_name == "Synthetic channel"
    assert definition.played_at is None


@pytest.mark.parametrize("locale", ("en", "de"))
def test_manual_source_error_keeps_video_values_reachable_through_language(
    localized_server, locale,
):
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/matches/new"), locale)
    response = browser.submit(Forms(page).find(CREATE), **new_name_roster(),
        match_title="Synthetic manual correction", perspective_seat="forehand",
        setup_action="update", source_kind="manual_observation", source_channel_name="Channel",
        match_timecode_start="01:00", match_timecode_end="02:00")
    assert response[0] == 400
    page = switch(browser, response[2].decode(), "en" if locale == "de" else "de")
    form = Forms(page).find(CREATE)
    assert form["values"]["source_kind"] == "manual_observation"
    for name, value in (("source_channel_name", "Channel"), ("match_timecode_start", "01:00"),
                        ("match_timecode_end", "02:00")):
        assert form["values"][name] == value
    field = next(n for n in Hierarchy(page).nodes
                 if n["attrs"].get("name") == "source_channel_name")
    assert field["attrs"]["aria-invalid"] == "true" and Hierarchy.visible(field)
    page = follow(browser, browser.submit(form, source_kind="other_video",
        source_url="https://example.invalid/video", setup_action="update"))
    follow(browser, browser.submit(Forms(page).find(CREATE), setup_action="create"))
    active = localized_server.app_context.managed_stateful.active_match
    definition = active.workspace.match_definition
    assert definition.source.source_channel_name == "Channel"
    assert definition.source.source_kind == "other_video"


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
    assert "open" not in outer_details(browser.page("/matches/new"))


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
