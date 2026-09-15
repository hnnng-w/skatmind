import re
from unittest.mock import patch

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.local_time_forms import LOCAL_TIME_FIELDS
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def local_form(page, marker, target=None):
    return next(form for form in Forms(page).forms if form["values"].get("time_form") == marker
        and (target is None or form["values"].get("target_revision") == str(target)))


def create_match(browser, **metadata):
    form = local_form(browser.page("/matches/new"), "match-create")
    assert "played_at" not in form["values"]
    page = follow(browser, browser.submit(form, match_title="Exact time Match",
        forehand_name="Alex", middlehand_name="Boris", rearhand_name="Clara",
        perspective_seat="rearhand", setup_action="update", **metadata))
    form = local_form(page, "match-create")
    return follow(browser, browser.submit(form, setup_action="create"))


def create_session(browser):
    form = Forms(browser.page("/sessions")).find("/sessions/create")
    page = follow(browser, browser.submit(form, game_name="Exact time Game",
        forehand_name="Alex", middlehand_name="Boris", rearhand_name="Clara",
        perspective_seat="forehand", setup_action="update"))
    return follow(browser, browser.submit(
        Forms(page).find("/sessions/create"), setup_action="create"))


def occurrence(page, which):
    return re.search(r'<option value="(' + which + r'\.[0-9a-f]{64})"', page)[1]


def test_settings_restart_date_only_exact_metadata_and_reopen(localized_server):
    browser = Browser(localized_server)
    app = localized_server.app_context
    page = browser.page("/settings")
    assert not app.frontend_profile.profile_path.exists()
    form = Forms(page).find("/actions/profile/time-zone")
    assert form["values"]["time_zone"] == ""
    page = follow(browser, browser.submit(form, time_zone="Europe/Berlin"))
    saved = app.frontend_profile.profile_path.read_bytes()
    form = Forms(page).find("/actions/profile/time-zone")
    page = follow(browser, browser.submit(form))
    assert app.frontend_profile.profile_path.read_bytes() == saved
    page = switch(browser, page, "de")
    restarted = AppWebContextV1.create(app.managed_home)
    assert restarted.frontend_profile.document.interface_preferences.time_zone == "Europe/Berlin"
    server = start_app_web_server_v1(restarted, port=0, token="localization-test-token")
    thread = serve_app_web_in_thread_v1(server)
    try:
        browser = Browser(server)
        page = create_match(browser, played_date="2026-01-15")
        date_only = restarted.managed_stateful.active_match
        assert date_only.workspace.match_definition.played_at is None
        assert (restarted.frontend_profile.document.managed_item_display_labels[-1].played_date
                == "2026-01-15")
        page = create_match(browser, played_date="2026-07-15",
                            local_date="2026-07-15", local_time="19:30")
        active = restarted.managed_stateful.active_match
        assert active.workspace.match_definition.played_at == "2026-07-15T19:30:00+02:00"
        labels = restarted.frontend_profile.profile_path.read_bytes()
        page = follow(browser, browser.submit(
            local_form(page, "match-metadata"), title="Edited title"))
        assert active.workspace.match_definition.played_at == "2026-07-15T19:30:00+02:00"
        assert restarted.frontend_profile.profile_path.read_bytes() == labels
        content = active.path.read_bytes()
        reopen = next(form for form in Forms(browser.page("/matches")).forms
            if form["action"] == "/matches/open" and form["values"]["handle"] == active.handle)
        page = follow(browser, browser.submit(reopen))
        assert restarted.managed_stateful.active_match.path.read_bytes() == content
        assert local_form(page, "match-metadata")["values"]["time_mode"] == "keep"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


@pytest.mark.parametrize("metadata,reason", (
    ({"local_date": "2026-03-29", "local_time": "02:30"}, "does not exist"),
    ({"local_date": "2026-01-15"}, "local time as well"),
    ({"local_time": "19:30"}, "local date as well"),
    ({"local_date": "2026-10-25", "local_time": "02:30"}, "occurs twice"),
    ({"local_date": "2026-01-15", "local_time": "19:30", "local_zone": "../UTC"},
     "zone is unavailable"),
    ({"local_date": "2026-01-01", "local_time": "00:15", "played_date": "2025-12-31"},
     "same calendar date"),
    ({"played_at": "2026-01-15T19:30:00Z"}, "cannot be combined"),
))
def test_bad_time_input_generates_no_id_product_or_profile(localized_server, metadata, reason):
    browser = Browser(localized_server)
    form = local_form(browser.page("/matches/new"), "match-create")
    with (
        patch("skatmind.app_web.profile_driven_creation.generate_frontend_match_id_v1") as match_id,
        patch("skatmind.app_web.profile_driven_creation.generate_frontend_player_id_v1"
              ) as player_id,
        patch("skatmind.app_web.server.create_unified_match_v1") as create,
    ):
        response = browser.submit(form, match_title="Rejected", forehand_name="A",
            middlehand_name="B", rearhand_name="C", perspective_seat="forehand",
            setup_action="update", **metadata)
    assert response[0] == 400 and reason in response[2].decode()
    for call in (match_id, player_id, create):
        call.assert_not_called()
    assert not localized_server.app_context.frontend_profile.profile_path.exists()
    assert localized_server.app_context.managed_stateful.active_match is None


@pytest.mark.parametrize("which,expected", (("earlier", "+02:00"), ("later", "+01:00")))
def test_returned_fold_choices_language_and_single_creation(localized_server, which, expected):
    browser = Browser(localized_server)
    form = local_form(browser.page("/matches/new"), "match-create")
    response = browser.submit(form, match_title="Fold", forehand_name="A", middlehand_name="B",
        rearhand_name="C", perspective_seat="forehand", setup_action="update",
        local_date="2026-10-25", local_time="02:30")
    assert response[0] == 400
    page = response[2].decode()
    assert "UTC+02:00" in page and "UTC+01:00" in page
    assert local_form(page, "match-create")["values"]["local_occurrence"] == ""
    old = occurrence(page, which)
    response = browser.submit(local_form(page, "match-create"), local_time="02:31",
        local_occurrence=old, setup_action="update")
    assert response[0] == 400 and "does not match" in response[2].decode()
    page = switch(browser, response[2].decode(), "de")
    assert local_form(page, "match-create")["values"]["local_time"] == "02:31"
    page = follow(browser, browser.submit(local_form(page, "match-create"),
        local_occurrence=occurrence(page, which), setup_action="update"))
    assert local_form(page, "match-create")["values"]["local_occurrence"] == ""
    page = follow(browser, browser.submit(local_form(page, "match-create"),
        local_occurrence=occurrence(page, which), setup_action="create"))
    active = localized_server.app_context.managed_stateful.active_match
    assert active.workspace.match_definition.played_at == "2026-10-25T02:31:00" + expected
    assert len(tuple(active.category_root.glob("*.json"))) == 1
    assert active.workspace.revision == 0


@pytest.mark.parametrize("original", (
    "2026-01-15t19:30:00.123456789z", "2016-12-31T23:59:60Z",
    "2026-01-15T19:30:00-00:00", "2026-01-15t19:30:00.120000000+05:45",
))
def test_session_original_command_keep_replace_remove_and_reopen(localized_server, original):
    browser = Browser(localized_server)
    page = create_session(browser)
    form = local_form(page, "session-metadata")
    # Explicit legacy adapter submission, not a hidden source timestamp in a local form.
    legacy = {name: value for name, value in form["values"].items()
              if name not in {*LOCAL_TIME_FIELDS, "profile_generation", "_frontend_form_instance"}}
    response = browser.request("POST", "/sessions/command", {**legacy, "played_at": original})
    assert response[0] == 303
    active = localized_server.app_context.managed_stateful.active_session
    page = browser.page()
    correction = local_form(page, "session-metadata-correction", 1)
    assert correction["values"]["time_mode"] == "keep" and "played_at" not in correction["values"]
    assert original in page
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(correction))
    assert active.path.read_bytes() == before and active.last_operation.status == "unchanged"
    page = follow(browser, browser.submit(
        local_form(page, "session-metadata-correction", 1), game_id="Edited"))
    assert active.state.command_log[0].command.played_at == original
    old_source = local_form(page, "session-metadata-correction", 1)
    response = browser.submit(old_source, local_date="2026-01-15", local_time="19:30")
    assert response[0] == 400 and "Choose Replace" in response[2].decode()
    page = follow(browser, browser.submit(
        local_form(response[2].decode(), "session-metadata-correction", 1),
        time_mode="replace"))
    assert replay_session_state_v1(active.state).played_at == "2026-01-15T19:30:00+01:00"
    assert browser.submit(old_source)[0] == 409  # Equal revision, different content.
    page = browser.page()
    page = follow(browser, browser.submit(
        local_form(page, "session-metadata-correction", 1), time_mode="remove"))
    assert replay_session_state_v1(active.state).played_at is None
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert localized_server.app_context.managed_stateful.active_session.path.read_bytes() == before


def test_session_initial_gap_saved_time_suffix_source_conflict_and_save_failure(localized_server):
    browser = Browser(localized_server)
    page = create_session(browser)
    active = localized_server.app_context.managed_stateful.active_session
    original = active.path.read_bytes()
    response = browser.submit(local_form(page, "session-metadata"),
                              local_date="2026-03-29", local_time="02:30")
    assert response[0] == 400 and active.path.read_bytes() == original
    page = switch(browser, response[2].decode(), "de")
    form = local_form(page, "session-metadata")
    assert form["values"]["local_date"] == "2026-03-29"
    page = follow(browser, browser.submit(form, local_date="2026-01-15", local_time="19:30"))
    assert active.state.command_log[0].command.played_at == "2026-01-15T19:30:00+01:00"
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards="CA"))
    suffix = active.state.command_log[1:]
    form = local_form(page, "session-metadata-correction", 1)
    before = active.path.read_bytes()
    with patch("skatmind.app_web.session_frontend.session_files.save_session_file",
               side_effect=OSError):
        response = browser.submit(form, time_mode="replace",
                                  local_date="2026-07-15", local_time="19:30")
    assert response[0] == 409 and active.path.read_bytes() == before
    page = follow(browser, browser.submit(form, time_mode="replace",
                                        local_date="2026-07-15", local_time="19:30"))
    assert active.state.command_log[1:] == suffix and active.last_operation.status == "applied"
    assert active.state.command_log[0].command.played_at == "2026-07-15T19:30:00+02:00"
    old = local_form(page, "session-metadata-correction", 1)
    settings = Forms(browser.page("/settings")).find("/actions/profile/time-zone")
    follow(browser, browser.submit(settings, time_zone="UTC"))
    assert browser.submit(old, time_mode="remove")[0] == 409


def test_recorded_review_survives_passive_views_and_zone_preference(localized_server):
    browser = Browser(localized_server)
    record_live_game(browser)
    review_first(browser)
    active = localized_server.app_context.managed_stateful.active_session
    execution, checkpoints = active.execution, active.decision_checkpoints
    before = active.path.read_bytes()
    request = browser.request("GET", "/sessions/downloads/request.json")[2]
    result = browser.request("GET", "/sessions/downloads/result.json")[2]
    settings = Forms(browser.page("/settings")).find("/actions/profile/time-zone")
    follow(browser, browser.submit(settings, time_zone="Asia/Kathmandu"))
    browser.page("/")
    browser.page("/review/recorded")
    browser.page()
    assert active.execution is execution and active.decision_checkpoints == checkpoints
    assert active.path.read_bytes() == before
    assert browser.request("GET", "/sessions/downloads/request.json")[2] == request
    assert browser.request("GET", "/sessions/downloads/result.json")[2] == result


@pytest.mark.parametrize("change", ("position", "roundtrip", "reopen", "equal_revision"))
def test_match_time_source_cannot_follow_navigation_or_changed_content(localized_server, change):
    from dataclasses import replace

    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    browser = Browser(localized_server)
    page = create_match(browser)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    old = local_form(page, "match-metadata")
    before = active.path.read_bytes()
    profile = app.frontend_profile.profile_path.read_bytes()
    if change in {"position", "roundtrip"}:
        browser.page("/matches/position/2")
        if change == "roundtrip":
            browser.page("/matches/position/1")
    elif change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    else:
        # Fault-injected equal-revision content change, not a successful-save fixture.
        active.capture.workspace = _build_match_workspace_v1(
            revision=active.workspace.revision, slots=active.workspace.slots,
            match_definition=replace(active.workspace.match_definition, title="Changed"))
    response = browser.submit(old, time_mode="replace", local_date="2026-01-15", local_time="19:30")
    assert response[0] == 409
    assert active.path.read_bytes() == before
    assert app.frontend_profile.profile_path.read_bytes() == profile


def test_match_precision_keep_noop_replace_remove_save_counts_and_temporal_safety(localized_server):
    import skatmind.app_web.profile_driven_creation as creation
    import skatmind.app_web.server as server_module
    import skatmind.match_workspace_persistence as persistence
    from skatmind.match_player_statistics_context import (
        classify_match_player_statistics_temporal_status_v1 as classify,
    )
    browser = Browser(localized_server)
    with (
        patch.object(creation, "generate_frontend_match_id_v1",
                     wraps=creation.generate_frontend_match_id_v1) as match_ids,
        patch.object(creation, "generate_frontend_player_id_v1",
                     wraps=creation.generate_frontend_player_id_v1) as player_ids,
        patch.object(server_module, "create_unified_match_v1",
                     wraps=server_module.create_unified_match_v1) as creates,
    ):
        page = create_match(browser, played_date="2026-01-01",
            local_date="2026-01-01", local_time="00:15", local_zone="Pacific/Kiritimati")
    assert (match_ids.call_count, player_ids.call_count, creates.call_count) == (1, 3, 1)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    assert active.workspace.match_definition.played_at == "2026-01-01T00:15:00+14:00"
    assert app.frontend_profile.document.interface_preferences.time_zone is None
    assert app.frontend_profile.document.managed_item_display_labels[-1].played_date == "2026-01-01"
    form = local_form(page, "match-metadata")
    legacy = {name: value for name, value in form["values"].items()
        if name not in {*LOCAL_TIME_FIELDS, "profile_generation", "_frontend_form_instance"}}
    original = "2026-01-15t19:30:00.123456789-00:00"
    page = follow(browser, browser.request(
        "POST", form["action"], {**legacy, "played_at": original}))
    form = local_form(page, "match-metadata")
    before, labels = active.path.read_bytes(), app.frontend_profile.profile_path.read_bytes()
    with patch.object(persistence.os, "replace", wraps=persistence.os.replace) as saves:
        page = follow(browser, browser.submit(form))
        assert saves.call_count == 0 and active.path.read_bytes() == before
        page = follow(browser, browser.submit(
            local_form(page, "match-metadata"), title="Only title"))
        assert saves.call_count == 1
    assert active.workspace.match_definition.played_at == original
    assert app.frontend_profile.profile_path.read_bytes() == labels
    form = local_form(page, "match-metadata")
    before = active.path.read_bytes()
    with patch.object(persistence.os, "replace", side_effect=OSError):
        response = browser.submit(form, time_mode="replace",
                                  local_date="2026-07-15", local_time="19:30")
    assert response[0] == 409 and active.path.read_bytes() == before
    page = follow(browser, browser.submit(form, time_mode="replace",
                                        local_date="2026-07-15", local_time="19:30"))
    timestamp = active.workspace.match_definition.played_at
    assert timestamp == "2026-07-15T19:30:00+02:00"
    expected = ("eligible", "captured_not_before_match", "captured_not_before_match")
    def eligibility():
        return tuple(classify(captured_at=instant,
                             played_at=active.workspace.match_definition.played_at)
                     for instant in ("2026-07-15T17:29:59Z", "2026-07-15T17:30:00Z",
                                     "2026-07-15T17:30:01Z"))
    assert eligibility() == expected
    settings = Forms(browser.page("/settings")).find("/actions/profile/time-zone")
    before = active.path.read_bytes()
    follow(browser, browser.submit(settings, time_zone="UTC"))
    assert active.path.read_bytes() == before and eligibility() == expected
    page = follow(browser, browser.submit(local_form(browser.page("/matches/position/1"),
        "match-metadata"), time_mode="remove"))
    assert active.workspace.match_definition.played_at is None
    assert eligibility() == ("match_time_unavailable",) * 3


def test_unavailable_preference_get_security_failed_save_and_explicit_clear(localized_server):
    from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
    from skatmind.app_web.frontend_profile_contracts import FrontendInterfacePreferencesV1
    from skatmind.app_web.frontend_profile_operations import save_prepared_frontend_profile_v1
    app = localized_server.app_context
    save_prepared_frontend_profile_v1(app, requested=build_local_frontend_profile_v1(
        language="en", interface_preferences=FrontendInterfacePreferencesV1(
            time_zone="Former/Unavailable")), expected_generation=0)
    browser = Browser(localized_server)
    before = app.frontend_profile.profile_path.read_bytes()
    page = browser.page("/settings")
    assert "zone is unavailable" in page and "invalid local profile" not in page
    form = Forms(page).find("/actions/profile/time-zone")
    assert form["values"]["time_zone"] == "Former/Unavailable"
    create = local_form(browser.page("/matches/new"), "match-create")
    assert create["values"]["local_zone"] == "Former/Unavailable"
    assert app.frontend_profile.profile_path.read_bytes() == before
    assert browser.request("POST", form["action"], form["values"],
                           headers={"Origin": "null"})[0] == 403
    with patch("skatmind.app_web.frontend_profile_persistence.os.replace", side_effect=OSError):
        assert browser.submit(form, time_zone="UTC")[0] == 409
    assert app.frontend_profile.profile_path.read_bytes() == before
    follow(browser, browser.submit(form, time_zone=""))
    assert app.frontend_profile.document.interface_preferences.time_zone is None
    assert app.frontend_profile.document.language == "en"


def test_enhanced_unsent_local_values_preserve_language_without_saving(localized_server):
    from test_task_first_language_preservation import enhanced_switch, envelope
    browser = Browser(localized_server)
    page = create_session(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    raw = envelope(page, "/sessions/command", {
        "local_date": ["2026-10-25"], "local_time": ["02:30"], "local_zone": ["Europe/Berlin"]})
    page = follow(browser, enhanced_switch(browser, page, raw, "de"))
    form = local_form(page, "session-metadata")
    assert form["values"]["local_date"] == "2026-10-25"
    assert form["values"]["local_time"] == "02:30"
    assert form["values"]["local_occurrence"] == ""
    assert active.path.read_bytes() == before
    response = browser.submit(form)
    assert response[0] == 400 and "zweimal" in response[2].decode()


def test_correction_keep_reads_target_command_not_latest_projection(localized_server):
    browser = Browser(localized_server)
    page = create_session(browser)
    form = local_form(page, "session-metadata")
    legacy = {name: value for name, value in form["values"].items()
              if name not in {*LOCAL_TIME_FIELDS, "profile_generation", "_frontend_form_instance"}}
    second = "2026-01-15t19:30:00.123456789z"
    follow(browser, browser.request("POST", form["action"], {**legacy, "played_at": ""}))
    page = follow(browser, browser.request("POST", form["action"], {
        **legacy, "expected_revision": "1", "game_id": "", "played_at": second}))
    active = localized_server.app_context.managed_stateful.active_session
    page = follow(browser, browser.submit(local_form(page, "session-metadata-correction", 1),
                                        game_id="First metadata renamed"))
    assert active.state.command_log[0].command.played_at is None
    assert active.state.command_log[1].command.played_at == second
    assert replay_session_state_v1(active.state).played_at == second


def test_optional_session_time_appends_only_missing_metadata(localized_server):
    browser = Browser(localized_server)
    page = create_session(browser)
    page = follow(browser, browser.submit(local_form(page, "session-metadata")))
    extra = local_form(page, "session-metadata")
    assert extra["values"]["game_id"] == "" and extra["values"]["time_mode"] == "enter"
    page = follow(browser, browser.submit(extra, local_date="2026-01-15", local_time="19:30"))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.command_log[1].command.game_id is None
    assert active.state.command_log[1].command.played_at == "2026-01-15T19:30:00+01:00"
    assert "Use its accepted metadata correction" in page


def test_creation_old_generation_and_setup_cannot_create_or_enrich(localized_server):
    browser = Browser(localized_server)
    app = localized_server.app_context
    old = local_form(browser.page("/matches/new"), "match-create")
    follow(browser, browser.submit(Forms(browser.page("/settings")).find(
        "/actions/profile/time-zone"), time_zone="UTC"))
    before = app.frontend_profile.profile_path.read_bytes()
    response = browser.submit(old, local_date="2026-01-15", local_time="19:30",
        match_title="Stale", forehand_name="A", middlehand_name="B", rearhand_name="C",
        perspective_seat="forehand", setup_action="update")
    assert response[0] == 409 and app.managed_stateful.active_match is None
    assert app.frontend_profile.profile_path.read_bytes() == before
    current = local_form(browser.page("/matches/new"), "match-create")
    current["values"]["time_selection"] = old["values"]["time_selection"]
    assert browser.submit(current, setup_action="update")[0] == 409
    assert app.frontend_profile.profile_path.read_bytes() == before


def test_explicit_legacy_match_creation_transport_keeps_original_string(localized_server):
    browser = Browser(localized_server)
    form = local_form(browser.page("/matches/new"), "match-create")
    original = "2016-12-31t23:59:60.123456789z"
    legacy = {name: value for name, value in form["values"].items()
              if name not in {*LOCAL_TIME_FIELDS, "_frontend_form_instance"}}
    legacy.update(match_title="Legacy exact time", played_date="2016-12-31",
        played_at=original, forehand_name="A", middlehand_name="B", rearhand_name="C",
        perspective_seat="forehand", setup_action="update")
    response = browser.request("POST", form["action"], legacy)
    assert response[0] == 303
    assert localized_server.app_context.managed_stateful.active_match is None
    # The legacy client retains its explicitly supplied timestamp, not a server-converted value.
    response = browser.request("POST", form["action"], {**legacy, "setup_action": "create"})
    assert response[0] == 303
    active = localized_server.app_context.managed_stateful.active_match
    assert active.workspace.match_definition.played_at == original
