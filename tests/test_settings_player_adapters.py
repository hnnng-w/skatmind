from __future__ import annotations

import pytest

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.frontend_profile_operations import (
    StaleFrontendProfileGenerationError,
    save_prepared_frontend_profile_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.profile_player_contracts import KnownPlayerPlatformIdV1, KnownPlayerV1
from skatmind.app_web.settings_forms import (
    confirm_player_change_v1,
    edit_player_v1,
    select_settings_editor_v1,
    set_ordinary_preferences_v1,
)


@pytest.fixture
def legacy_context(tmp_path):
    context = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))
    a = KnownPlayerV1("frontend-player-" + "a" * 64, "A", ("Alias A", "A=legacy"),
        (KnownPlayerPlatformIdV1("First", "exact=one"), KnownPlayerPlatformIdV1("Second", "two")))
    b = KnownPlayerV1("frontend-player-" + "b" * 64, "B", (), ())
    profile = build_local_frontend_profile_v1(known_players=(a, b), own_player_id=a.player_id,
        preferred_perspective_player_id=b.player_id)
    save_prepared_frontend_profile_v1(context, requested=profile, expected_generation=0)
    return context, a, b


def test_name_only_adapter_preserves_all_legacy_values_and_noop_bytes(legacy_context):
    context, a, _ = legacy_context
    values = {"player_handle": build_known_player_handle_v1(a.player_id),
              "display_name": "Renamed A", "account_action": "keep"}
    edit_player_v1(context, values, generation=1, entropy_source=None)
    result = context.frontend_profile.document.known_players[0]
    assert (result.player_id, result.aliases, result.platform_player_ids) == (
        a.player_id, a.aliases, a.platform_player_ids)
    path = context.frontend_profile.profile_path
    before = path.read_bytes(), path.stat().st_mtime_ns
    assert edit_player_v1(context, values, generation=2, entropy_source=None).status == "unchanged"
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_ordinary_own_preference_keeps_differing_hidden_preference(legacy_context):
    context, _, b = legacy_context
    set_ordinary_preferences_v1(context, {"own_player_handle": "", "platform_choice": "",
        "custom_platform": ""}, generation=1)
    assert context.frontend_profile.document.own_player_id is None
    assert context.frontend_profile.document.preferred_perspective_player_id == b.player_id


@pytest.mark.parametrize("kind", ("accounts", "remove"))
def test_confirmation_exact_target_single_use_and_cancel(legacy_context, kind):
    context, a, b = legacy_context
    handle = build_known_player_handle_v1(a.player_id)
    before = context.frontend_profile.profile_path.read_bytes()
    select_settings_editor_v1(context, kind=kind, handle=handle, generation=1)
    preview = context.settings_editor
    assert context.frontend_profile.profile_path.read_bytes() == before
    context.settings_editor = None
    values = {"player_handle": handle, "confirmation_selection": preview.confirmation,
              "confirm_replace": "on"}
    with pytest.raises(StaleFrontendProfileGenerationError):
        confirm_player_change_v1(context, values, kind=kind, generation=1)
    select_settings_editor_v1(context, kind=kind, handle=handle, generation=1)
    values["confirmation_selection"] = context.settings_editor.confirmation
    with pytest.raises(StaleFrontendProfileGenerationError):
        confirm_player_change_v1(context, {
            **values, "player_handle": build_known_player_handle_v1(b.player_id)},
            kind=kind, generation=1)
    confirm_player_change_v1(context, values, kind=kind, generation=1)
    profile = context.frontend_profile.document
    assert profile.preferred_perspective_player_id == b.player_id
    if kind == "accounts":
        assert profile.known_players[0].aliases == a.aliases
        assert profile.known_players[0].platform_player_ids == ()
    else:
        assert profile.known_players == (b,)
        assert profile.own_player_id is None
    with pytest.raises(StaleFrontendProfileGenerationError):
        confirm_player_change_v1(context, values, kind=kind, generation=2)


def test_confirmation_expiry_and_single_account_explicit_clear(legacy_context):
    from dataclasses import replace

    context, a, _ = legacy_context
    handle = build_known_player_handle_v1(a.player_id)
    select_settings_editor_v1(context, kind="accounts", handle=handle, generation=1,
        accounts=(KnownPlayerPlatformIdV1("One", "exact"),))
    editor = context.settings_editor
    context.settings_editor = replace(editor, created_at=editor.created_at - 1801)
    values = {"player_handle": handle, "confirmation_selection": editor.confirmation,
              "confirm_replace": "on"}
    before = context.frontend_profile.profile_path.read_bytes()
    with pytest.raises(StaleFrontendProfileGenerationError):
        confirm_player_change_v1(context, values, kind="accounts", generation=1)
    assert context.frontend_profile.profile_path.read_bytes() == before
    context.settings_editor = editor
    confirm_player_change_v1(context, values, kind="accounts", generation=1)
    edit_player_v1(context, {"player_handle": handle, "display_name": "A",
        "account_action": "edit", "account_platform": "", "account_id": ""},
        generation=2, entropy_source=None)
    assert context.frontend_profile.document.known_players[0].aliases == a.aliases
    assert context.frontend_profile.document.known_players[0].platform_player_ids == ()


def test_absent_preferences_noop_and_invalid_account_precede_identity_generation(tmp_path):
    context = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))
    assert set_ordinary_preferences_v1(context, {"own_player_handle": "",
        "platform_choice": "", "custom_platform": ""}, generation=0) == "unchanged"
    def forbidden(_size):
        pytest.fail("Invalid input requested an identity.")
    for values in ({"display_name": "A", "account_id": "incomplete"},
                   {"display_name": "A" * 121},
                   {"display_name": "A", "account_platform": "x" * 121, "account_id": "x"},
                   {"display_name": "A", "account_platform": "x", "account_id": "x" * 256}):
        with pytest.raises(ValueError):
            edit_player_v1(context, values, generation=0, entropy_source=forbidden)
    assert not context.frontend_profile.profile_path.exists()
