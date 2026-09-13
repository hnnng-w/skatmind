from __future__ import annotations

import re

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_session_recorded_review_web import Browser, Forms

from skatmind.api.v1.session import files as session_files
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def player_action(page, action, handle=""):
    return next(form for form in Forms(page).forms
        if form["action"] == f"/actions/profile/players/{action}"
        and form["values"].get("player_handle", "") == handle)


def add_players(browser):
    page = browser.page("/settings")
    for name in ("A", "B", "C"):
        page = follow(browser, browser.submit(player_action(page, "edit")))
        page = follow(browser, browser.submit(player_action(page, "add"), display_name=name))
    form = Forms(page).find("/actions/profile/preferences")
    choices = re.search(r'<select name="own_player_handle"[^>]*>(.*?)</select>', page, re.S)[1]
    handles = re.findall(r'<option value="([0-9a-f]{64})"', choices)
    page = follow(browser, browser.submit(form, own_player_handle=handles[0]))
    return page, handles


def setup_own(browser, family, handles, seat):
    route = "/sessions" if family == "sessions" else "/matches/new"
    action = "/sessions/create" if family == "sessions" else "/matches/api/v1/create"
    page = browser.page(route)
    form = Forms(page).find(action)
    assert form["values"]["own_seat"] == ""
    assert all(form["values"][f"{s}_handle"] == "" for s in ("forehand", "middlehand", "rearhand"))
    assert "save_players" not in form["values"]
    page = follow(browser, browser.submit(form, own_seat=seat, setup_action="update"))
    form = Forms(page).find(action)
    assert form["values"][f"{seat}_handle"] == handles[0]
    remaining = iter(handles[1:])
    values = {f"{s}_handle": next(remaining)
              for s in ("forehand", "middlehand", "rearhand") if s != seat}
    values["game_name" if family == "sessions" else "match_title"] = "Exact roster"
    page = follow(browser, browser.submit(form, **values, setup_action="update"))
    assert 'name="setup_action" value="create"' in page
    return page, action


@pytest.mark.parametrize("seat", ("rearhand", "forehand", "middlehand"))
def test_real_settings_session_match_start_reopen_and_scoped_removal(localized_server, seat):
    browser = Browser(localized_server)
    context = localized_server.app_context
    assert 'href="/settings"' in browser.page("/")
    assert "/actions/profile/players/add" not in browser.page("/about")
    assert not context.frontend_profile.profile_path.exists()
    page, handles = add_players(browser)
    assert context.managed_stateful.active_session is context.managed_stateful.active_match is None
    profile_bytes = context.frontend_profile.profile_path.read_bytes()
    page, action = setup_own(browser, "sessions", handles, seat)
    assert context.frontend_profile.profile_path.read_bytes() == profile_bytes
    page = follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
    session = context.managed_stateful.active_session
    state = session_files.load_session_file(session.path).value.document.state
    own = next(player for player in state.players if player.player_label == "A")
    assert own.seat == seat and state.local_player_id == own.player_id
    session_bytes = session.path.read_bytes()

    page, action = setup_own(browser, "matches", handles, seat)
    roster = Forms(page).find(action)["values"]
    expected = {s: roster[f"{s}_handle"] for s in ("forehand", "middlehand", "rearhand")}
    page = follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    match = context.managed_stateful.active_match
    definition = match.workspace.match_definition
    assignment = build_match_workspace_seat_assignment_v1(definition, 1)
    from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
    for s, handle in expected.items():
        assert build_known_player_handle_v1(getattr(assignment, f"{s}_player_id")) == handle
    assert definition.perspective_player_id == own.player_id
    game = match.workspace.slots[0].observed_game
    assert {p.seat: p.player_id for p in game.players} == {
        s: getattr(assignment, f"{s}_player_id") for s in expected}
    assert game.perspective_player_id == own.player_id
    assert getattr(assignment, f"{seat}_player_id") == own.player_id
    match_bytes = match.path.read_bytes()
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    reopened = context.managed_stateful.active_match
    assert reopened.path.read_bytes() == match_bytes
    assert load_match_workspace_file_v1(reopened.path).document.workspace == match.workspace

    page = browser.page("/settings")
    page = follow(browser, browser.submit(player_action(page, "remove-preview", handles[0])))
    assert "Your player preference will be cleared" in page
    page = follow(browser, browser.submit(player_action(page, "cancel", handles[0])))
    assert len(context.frontend_profile.document.known_players) == 3
    page = follow(browser, browser.submit(player_action(page, "remove-preview", handles[0])))
    confirm = player_action(page, "remove", handles[0])
    assert "confirm_replace" not in confirm["values"]
    follow(browser, browser.submit(confirm, confirm_replace="on"))
    assert browser.submit(confirm, confirm_replace="on")[0] == 409
    assert len(context.frontend_profile.document.known_players) == 2
    assert context.frontend_profile.document.own_player_id is None
    assert session.path.read_bytes() == session_bytes and reopened.path.read_bytes() == match_bytes


def test_one_off_manual_duplicate_language_correction_and_no_implicit_saving(localized_server):
    from test_language_switch_context import switch

    browser = Browser(localized_server)
    page = browser.page("/sessions")
    form = Forms(page).find("/sessions/create")
    assert form["values"]["perspective_mode"] == "manual"
    response = browser.submit(form, game_name="One-off", capture_mode="retrospective",
        forehand_name="A", middlehand_name="a", rearhand_name="C", setup_action="update")
    assert response[0] == 400
    assert not localized_server.app_context.frontend_profile.profile_path.exists()
    assert localized_server.app_context.managed_stateful.active_session is None
    page = switch(browser, response[2].decode(), "de")
    form = Forms(page).find("/sessions/create")
    assert form["values"]["middlehand_name"] == "a" and "save_players" not in form["values"]
    page = follow(browser, browser.submit(form, middlehand_name="B", setup_action="update"))
    page = follow(browser, browser.submit(
        Forms(page).find("/sessions/create"), setup_action="create"))
    context = localized_server.app_context
    assert context.frontend_profile.document.known_players == ()
    session = context.managed_stateful.active_session
    assert session.state.local_player_id is None
    assert tuple(player.player_label for player in session.state.players) == ("A", "B", "C")
    assert all(player.player_id.startswith("frontend-player-") for player in session.state.players)


def test_collision_retention_stale_own_binding_and_ambiguous_payload(localized_server):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    page = browser.page("/sessions")
    page = follow(browser, browser.submit(Forms(page).find("/sessions/create"),
        own_seat="rearhand", setup_action="update"))
    form = Forms(page).find("/sessions/create")
    response = browser.submit(form, own_seat="forehand", forehand_handle=handles[1],
                               setup_action="update")
    assert response[0] == 400
    retained = Forms(response[2].decode()).find("/sessions/create")
    assert retained["values"]["forehand_handle"] == handles[1]
    assert retained["values"]["rearhand_handle"] == handles[0]
    assert "destination seat" in response[2].decode()
    page = follow(browser, browser.submit(retained, forehand_handle="", setup_action="update"))
    current = Forms(page).find("/sessions/create")
    assert current["values"]["forehand_handle"] == handles[0]
    assert current["values"]["rearhand_handle"] == ""
    profile_before = localized_server.app_context.frontend_profile.profile_path.read_bytes()
    response = browser.submit(current, own_player_handle=handles[1], setup_action="update")
    assert response[0] == 409
    assert localized_server.app_context.frontend_profile.profile_path.read_bytes() == profile_before
    assert browser.submit(current, player_1_name="Ambiguous", setup_action="update")[0] == 400
    assert localized_server.app_context.managed_stateful.active_session is None


def test_legacy_account_preview_language_cancel_confirm_and_exact_aliases(localized_server):
    from test_language_switch_context import switch

    from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
    from skatmind.app_web.frontend_profile_operations import save_prepared_frontend_profile_v1
    from skatmind.app_web.profile_player_contracts import KnownPlayerPlatformIdV1, KnownPlayerV1

    context = localized_server.app_context
    legacy = KnownPlayerV1("frontend-player-" + "a" * 64, "Legacy", tuple(
        f"Alias {index}" for index in range(16)), tuple(
        KnownPlayerPlatformIdV1(f"Platform {index}", f"exact={index}") for index in range(16)))
    save_prepared_frontend_profile_v1(context,
        requested=build_local_frontend_profile_v1(known_players=(legacy,)), expected_generation=0)
    browser = Browser(localized_server)
    page = browser.page("/settings")
    edit = Forms(page).find("/actions/profile/players/edit")
    handle = edit["values"]["player_handle"]
    page = follow(browser, browser.submit(edit))
    assert 'name="aliases"' not in page and 'name="platform_player_ids"' not in page
    assert "16 legacy accounts" in page
    rename = Forms(page).find("/actions/profile/players/update")
    page = follow(browser, browser.submit(rename, display_name="Legacy renamed"))
    renamed = context.frontend_profile.document.known_players[0]
    assert renamed.aliases == legacy.aliases
    assert renamed.platform_player_ids == legacy.platform_player_ids
    page = follow(browser, browser.submit(player_action(page, "edit", handle)))
    original = context.frontend_profile.profile_path.read_bytes()
    page = follow(browser, browser.submit(
        Forms(page).find("/actions/profile/players/accounts-preview"),
        account_platform="New", account_id="one"))
    preview = Forms(page).find("/actions/profile/players/accounts-replace")
    assert "exact=15" in page and "New: one" in page
    assert context.frontend_profile.profile_path.read_bytes() == original
    page = switch(browser, page, "de")
    assert not any(form["action"].endswith("accounts-replace") for form in Forms(page).forms)
    assert browser.submit(preview, confirm_replace="on")[0] == 409
    page = browser.page("/settings")
    page = follow(browser, browser.submit(player_action(page, "cancel", handle)))
    assert context.frontend_profile.document.known_players[0] == renamed
    page = follow(browser, browser.submit(player_action(page, "edit", handle)))
    page = follow(browser, browser.submit(
        Forms(page).find("/actions/profile/players/accounts-preview"),
        account_platform="New", account_id="one"))
    confirm = Forms(page).find("/actions/profile/players/accounts-replace")
    assert "confirm_replace" not in confirm["values"]
    follow(browser, browser.submit(confirm, confirm_replace="on"))
    assert context.frontend_profile.document.known_players[0].aliases == legacy.aliases
    assert context.frontend_profile.document.known_players[0].platform_player_ids == (
        KnownPlayerPlatformIdV1("New", "one"),)
    assert browser.submit(confirm, confirm_replace="on")[0] == 409


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_manual_other_perspective_and_stale_reviewed_setup(localized_server, family):
    browser = Browser(localized_server)
    _, handles = add_players(browser)
    context = localized_server.app_context
    route = "/sessions" if family == "sessions" else "/matches/new"
    action = "/sessions/create" if family == "sessions" else "/matches/api/v1/create"
    form = Forms(browser.page(route)).find(action)
    values = {"game_name" if family == "sessions" else "match_title": "Other perspective",
        "perspective_mode": "manual", "perspective_seat": "middlehand",
        "forehand_handle": handles[0], "middlehand_handle": handles[1],
        "rearhand_handle": handles[2], "setup_action": "update"}
    page = follow(browser, browser.submit(form, **values))
    old = Forms(page).find(action)
    settings = browser.page("/settings")
    follow(browser, browser.submit(Forms(settings).find("/actions/profile/preferences"),
        own_player_handle=handles[2]))
    before = context.frontend_profile.profile_path.read_bytes()
    assert browser.submit(old, setup_action="create")[0] == 409
    assert context.frontend_profile.profile_path.read_bytes() == before
    page = follow(browser, browser.submit(Forms(browser.page(route)).find(action), **values))
    follow(browser, browser.submit(Forms(page).find(action), setup_action="create"))
    b = context.frontend_profile.document.known_players[1].player_id
    if family == "sessions":
        assert context.managed_stateful.active_session.state.local_player_id == b
    else:
        definition = context.managed_stateful.active_match.workspace.match_definition
        assert definition.perspective_player_id == b


def test_setup_preview_and_rejection_never_generate_ids_or_create_products(
    localized_server, monkeypatch,
):
    import skatmind.app_web.server as server_module

    browser = Browser(localized_server)
    form = Forms(browser.page("/sessions")).find("/sessions/create")
    def forbidden(*_args, **_kwargs):
        pytest.fail("Setup generated an identity or created a Product.")
    monkeypatch.setattr(server_module.secrets, "token_bytes", forbidden)
    monkeypatch.setattr(server_module, "create_guided_session_v1", forbidden)
    page = follow(browser, browser.submit(form, game_name="Preview only",
        forehand_name="A", middlehand_name="B", rearhand_name="C",
        perspective_seat="rearhand", setup_action="update"))
    response = browser.submit(Forms(page).find("/sessions/create"),
        middlehand_name="A", setup_action="update")
    assert response[0] == 400
    assert localized_server.app_context.managed_stateful.active_session is None
    assert not localized_server.app_context.frontend_profile.profile_path.exists()
