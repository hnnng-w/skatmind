import hashlib
import json
from unittest.mock import patch

import pytest

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_profile_codec import (
    build_frontend_profile_bytes_v1,
    build_local_frontend_profile_v1,
    resume_local_frontend_profile_v1,
)
from skatmind.app_web.frontend_profile_contracts import FrontendInterfacePreferencesV1
from skatmind.app_web.frontend_profile_operations import (
    FrontendProfilePersistenceConflictError,
    StaleFrontendProfileGenerationError,
    reset_frontend_profile_v1,
    reset_frontend_recommended_defaults_v1,
    save_prepared_frontend_profile_v1,
    set_frontend_language_v1,
)
from skatmind.app_web.frontend_profile_persistence import load_frontend_profile_file_v1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.profile_player_contracts import (
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
    ManagedItemDisplayLabelV1,
)
from skatmind.app_web.profile_player_operations import (
    replace_known_player_v1,
    set_frontend_creation_preferences_v1,
    set_managed_item_display_label_v1,
)
from skatmind.app_web.time_zone_preferences import (
    TimeZonePreferenceSaveError,
    set_frontend_time_zone,
)
from skatmind.app_web.time_zone_provider import TimeZoneUnavailable


@pytest.fixture
def context(tmp_path):
    return AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))


@pytest.mark.parametrize("zone", (None, "Europe/Berlin", "Former/Unavailable"))
def test_exact_nested_shape_old_bytes_and_new_fingerprint(zone):
    old = build_local_frontend_profile_v1(language="de")
    original = build_frontend_profile_bytes_v1(old)
    document = build_local_frontend_profile_v1(language="de",
        interface_preferences=FrontendInterfacePreferencesV1(time_zone=zone))
    value = document.to_dict()
    expected = {"advanced_settings_expanded": False}
    if zone is not None:
        expected["time_zone"] = zone
    assert value["interface_preferences"] == expected
    assert tuple(value["interface_preferences"]) == tuple(expected)
    assert build_frontend_profile_bytes_v1(resume_local_frontend_profile_v1(value)) == (
        build_frontend_profile_bytes_v1(document))
    payload = {k: v for k, v in value.items() if k != "content_fingerprint"}
    assert document.content_fingerprint == hashlib.sha256(b"skatmind\0frontend_profile_v1\0" + (
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()).hexdigest()
    assert (build_frontend_profile_bytes_v1(document) == original) == (zone is None)


@pytest.mark.parametrize("shape", (
    {"advanced_settings_expanded": False, "time_zone": None},
    {"advanced_settings_expanded": False, "time_zone": ""},
    {"time_zone": "UTC", "advanced_settings_expanded": False},
    {"advanced_settings_expanded": False, "time_zone": "UTC", "extra": False},
    {"time_zone": "UTC"}, {"advanced_settings_expanded": False, "time_zone": "../UTC"},
))
def test_rejected_shapes_are_not_alternate_encodings(shape):
    value = build_local_frontend_profile_v1().to_dict()
    value["interface_preferences"] = shape
    with pytest.raises(ValueError):
        resume_local_frontend_profile_v1(value)


def test_explicit_default_noop_clear_and_reset_policies_preserve_legacy_data(context):
    assert set_frontend_time_zone(context, time_zone=None, expected_generation=0) == "unchanged"
    assert not context.frontend_profile.profile_path.exists()
    player_id = "frontend-player-" + "a" * 64
    player = KnownPlayerV1(player_id, "Alex", ("Alias",), (
        KnownPlayerPlatformIdV1("first", "one"), KnownPlayerPlatformIdV1("second", "two")))
    document = build_local_frontend_profile_v1(language="de", known_players=(player,),
        own_player_id=player_id, preferred_perspective_player_id=player_id)
    save_prepared_frontend_profile_v1(context, requested=document, expected_generation=0)
    def generation():
        return context.frontend_profile.generation
    assert set_frontend_time_zone(context, time_zone="Europe/Berlin",
                                 expected_generation=generation()) == "saved"
    path = context.frontend_profile.profile_path
    saved = path.read_bytes(), path.stat().st_mtime_ns
    with patch(
        "skatmind.app_web.frontend_profile_operations.save_frontend_profile_file_v1"
    ) as save:
        assert set_frontend_time_zone(context, time_zone="Europe/Berlin",
                                     expected_generation=generation()) == "unchanged"
    save.assert_not_called()
    assert (path.read_bytes(), path.stat().st_mtime_ns) == saved
    set_frontend_language_v1(context, language="en", expected_generation=generation())
    set_frontend_creation_preferences_v1(context, own_player_id=player_id,
        preferred_perspective_player_id=player_id, preferred_game_platform="Example",
        advanced_settings_expanded=True, expected_generation=generation())
    from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
    replace_known_player_v1(context, player_handle=build_known_player_handle_v1(player_id),
        display_name="Renamed", aliases=player.aliases,
        platform_player_ids=player.platform_player_ids,
        expected_generation=generation())
    set_managed_item_display_label_v1(context,
        label=ManagedItemDisplayLabelV1("matches", "example", "Label", "2026-01-15"),
        expected_generation=generation())
    reset_frontend_recommended_defaults_v1(context, expected_generation=generation())
    current = context.frontend_profile.document
    assert current.interface_preferences == FrontendInterfacePreferencesV1(
        time_zone="Europe/Berlin")
    assert current.known_players[0].aliases == player.aliases
    assert current.known_players[0].platform_player_ids == player.platform_player_ids
    before = current.to_dict()
    set_frontend_time_zone(context, time_zone=None, expected_generation=generation())
    after = context.frontend_profile.document.to_dict()
    for key in before.keys() - {"revision", "content_fingerprint", "interface_preferences"}:
        assert after[key] == before[key]
    assert after["interface_preferences"] == {"advanced_settings_expanded": False}
    set_frontend_time_zone(context, time_zone="UTC", expected_generation=generation())
    reset_frontend_profile_v1(context, expected_generation=generation())
    assert context.frontend_profile.document.interface_preferences.time_zone is None
    assert context.frontend_profile.document.known_players == ()


def test_unavailable_stored_key_loads_and_can_be_cleared_without_provider(context):
    document = build_local_frontend_profile_v1(
        interface_preferences=FrontendInterfacePreferencesV1(time_zone="Former/Unavailable"))
    save_prepared_frontend_profile_v1(context, requested=document, expected_generation=0)
    with patch("skatmind.app_web.time_zone_provider.time_zone_inventory",
               side_effect=TimeZoneUnavailable()):
        loaded = load_frontend_profile_file_v1(context.managed_home.root)
        assert loaded.status == "available" and loaded.document == document
        assert set_frontend_time_zone(context, time_zone=None, expected_generation=1) == "saved"


def test_stale_generation_external_cas_and_failed_save_leave_bytes_intact(context):
    set_frontend_time_zone(context, time_zone="UTC", expected_generation=0)
    path = context.frontend_profile.profile_path
    original = path.read_bytes()
    with pytest.raises(StaleFrontendProfileGenerationError):
        set_frontend_time_zone(context, time_zone="Europe/Berlin", expected_generation=0)
    with patch("skatmind.app_web.frontend_profile_persistence.os.replace", side_effect=OSError):
        with pytest.raises(TimeZonePreferenceSaveError):
            set_frontend_time_zone(context, time_zone="Europe/Berlin", expected_generation=1)
    assert path.read_bytes() == original and context.frontend_profile.generation == 1
    external = AppWebContextV1.create(context.managed_home)
    set_frontend_time_zone(external, time_zone="Asia/Kathmandu", expected_generation=0)
    changed = path.read_bytes()
    with pytest.raises(FrontendProfilePersistenceConflictError):
        set_frontend_time_zone(context, time_zone="Europe/Berlin", expected_generation=1)
    assert path.read_bytes() == changed
    assert context.frontend_profile.document.interface_preferences.time_zone == "UTC"
