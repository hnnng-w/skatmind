from __future__ import annotations

from itertools import permutations

import pytest

from skatmind.app_web.frontend_identifier_generation import build_known_player_handle_v1
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.match_frontend import create_unified_match_v1
from skatmind.app_web.player_seat_setup import (
    SEATS,
    SeatSetupError,
    initial_seat_values_v1,
    project_own_seat_v1,
)
from skatmind.app_web.profile_driven_creation import (
    prepare_profile_driven_match_creation_v1,
    prepare_profile_driven_session_creation_v1,
)
from skatmind.app_web.profile_player_contracts import KnownPlayerV1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1


@pytest.fixture
def own_profile():
    players = tuple(KnownPlayerV1("frontend-player-" + name.lower() * 64, name, (), ())
                    for name in "ABC")
    return build_local_frontend_profile_v1(
        known_players=players, own_player_id=players[0].player_id,
        preferred_perspective_player_id=players[2].player_id)


@pytest.mark.parametrize("family", ("sessions", "matches"))
@pytest.mark.parametrize("seat", SEATS)
def test_duplicate_saved_own_uat_payload_equals_placeholder_roster(own_profile, family, seat):
    """R02 compatibility: submit saved A at the chosen own seat, without clearing it."""
    values = {**initial_seat_values_v1(own_profile), "own_seat": seat,
        "game_name": "Exact roster", "match_title": "Exact roster", "capture_mode": "live",
        "platform_choice": "unknown"}
    others = iter(own_profile.known_players[1:])
    for place in SEATS:
        if place != seat:
            values[f"{place}_handle"] = build_known_player_handle_v1(next(others).player_id)
    reference, _ = project_own_seat_v1(values, own_profile)
    values[f"{seat}_handle"] = values["own_player_handle"]
    before = dict(values)
    actual, auto = project_own_seat_v1(values, own_profile)
    assert values == before
    assert actual == reference and auto == seat
    assert project_own_seat_v1(actual, own_profile, auto_seat=auto) == (actual, auto)
    prepare = (prepare_profile_driven_session_creation_v1 if family == "sessions"
               else prepare_profile_driven_match_creation_v1)
    kwargs = {"existing_session_ids" if family == "sessions" else "existing_match_ids": (),
        "profile": own_profile, "expected_profile_generation": 0,
        "entropy_source": lambda _: b"r" * 32}
    assert prepare(actual, **kwargs) == prepare(reference, **kwargs)


@pytest.mark.parametrize("source,target", tuple(permutations(SEATS, 2)))
@pytest.mark.parametrize("accounts,expected", (
    (("", ""), ""), ((" explicit ", ""), "explicit"), (("", " explicit "), "explicit"),
    ((" explicit ", "explicit"), "explicit"), (("source", "target"), None),
))
def test_exact_own_bundle_moves_losslessly(own_profile, source, target, accounts, expected):
    values, auto = project_own_seat_v1(
        {**initial_seat_values_v1(own_profile), "own_seat": source}, own_profile)
    values.update(own_seat=target, **{f"{target}_handle": values["own_player_handle"],
        f"{source}_platform_id": accounts[0], f"{target}_platform_id": accounts[1]})
    before = dict(values)
    if expected is None:
        with pytest.raises(SeatSetupError, match="account_conflict") as caught:
            project_own_seat_v1(values, own_profile, auto_seat=auto)
        assert caught.value.field_key == f"{target}_platform_id"
    else:
        result, auto = project_own_seat_v1(values, own_profile, auto_seat=auto)
        assert auto == target and result["perspective_seat"] == target
        assert result[f"{target}_platform_id"] == expected
        assert result[f"{source}_handle"] == result[f"{source}_platform_id"] == ""
        assert project_own_seat_v1(result, own_profile, auto_seat=auto) == (result, auto)
    assert values == before


@pytest.mark.parametrize("overrides", (
    {"rearhand_handle": "other"}, {"rearhand_handle": "f" * 64},
    {"rearhand_mode": "new", "rearhand_name": "A"},
    {"rearhand_mode": "new", "rearhand_handle": "own"},
    {"rearhand_handle": "own", "rearhand_name": "A"},
    {"rearhand_platform_id": "account-only"},
    {"rearhand_handle": "own", "forehand_handle": "own"},
))
def test_independent_and_ambiguous_target_is_never_adopted(own_profile, overrides):
    values = {**initial_seat_values_v1(own_profile), "own_seat": "rearhand"}
    handles = {"own": values["own_player_handle"],
        "other": build_known_player_handle_v1(own_profile.known_players[1].player_id)}
    values.update({key: handles.get(value, value) for key, value in overrides.items()})
    before = dict(values)
    with pytest.raises(SeatSetupError):
        project_own_seat_v1(values, own_profile)
    assert values == before


@pytest.mark.parametrize("field,value", (
    ("rearhand_mode", "new"), ("rearhand_handle", ""), ("rearhand_name", "ambiguous"),
))
def test_automatic_source_validation_precedes_exact_target(own_profile, field, value):
    values, auto = project_own_seat_v1(
        {**initial_seat_values_v1(own_profile), "own_seat": "rearhand"}, own_profile)
    values.update(own_seat="forehand", forehand_handle=values["own_player_handle"])
    values[field] = value
    before = dict(values)
    with pytest.raises(SeatSetupError, match="own_binding"):
        project_own_seat_v1(values, own_profile, auto_seat=auto)
    assert values == before


def test_manual_release_preserves_independent_input_and_other_perspective(own_profile):
    values, auto = project_own_seat_v1(
        {**initial_seat_values_v1(own_profile), "own_seat": "rearhand"}, own_profile)
    values.update(perspective_mode="manual", rearhand_platform_id="automatic-account",
                  forehand_name="Independent", forehand_mode="new", forehand_platform_id="kept")
    released, auto = project_own_seat_v1(values, own_profile, auto_seat=auto)
    assert auto == "" and released["rearhand_handle"] == released["rearhand_platform_id"] == ""
    assert released["forehand_name"] == "Independent" and released["forehand_platform_id"] == "kept"
    released.update(perspective_seat="middlehand", forehand_mode="saved", forehand_name="",
        forehand_handle=build_known_player_handle_v1(own_profile.known_players[1].player_id),
        middlehand_handle=build_known_player_handle_v1(own_profile.known_players[2].player_id),
        rearhand_handle=values["own_player_handle"])
    assert project_own_seat_v1(released, own_profile) == (released, "")


def test_move_retains_supplied_account_when_optional_target_field_is_absent(own_profile):
    values, auto = project_own_seat_v1(
        {**initial_seat_values_v1(own_profile), "own_seat": "rearhand"}, own_profile)
    values.update(own_seat="forehand", rearhand_platform_id="explicit-source",
                  forehand_handle=values["own_player_handle"])
    assert "forehand_platform_id" not in values
    projected, _ = project_own_seat_v1(values, own_profile, auto_seat=auto)
    assert projected["forehand_platform_id"] == "explicit-source"
    assert projected["rearhand_platform_id"] == ""


@pytest.mark.parametrize("order", tuple(permutations("ABC")))
@pytest.mark.parametrize("perspective", SEATS)
def test_real_persisted_match_all_bundles_perspectives_and_36_rotations(
    tmp_path, order, perspective,
):
    players = tuple(KnownPlayerV1("frontend-player-" + character.lower() * 64, character, (), ())
                    for character in order)
    profile = build_local_frontend_profile_v1(known_players=players)
    values = {**initial_seat_values_v1(profile), "match_title": "Permutation",
              "platform_choice": "euroskat", "perspective_seat": perspective}
    for seat, player in zip(SEATS, players, strict=True):
        values[f"{seat}_handle"] = build_known_player_handle_v1(player.player_id)
        values[f"{seat}_platform_id"] = f"explicit-{player.display_name}"
    prepared = prepare_profile_driven_match_creation_v1(values, profile=profile,
        expected_profile_generation=0, existing_match_ids=(), entropy_source=lambda _: b"m" * 32)
    active = create_unified_match_v1(tmp_path, handle="a" * 64, values=prepared.product_values)
    loaded = load_match_workspace_file_v1(active.path).document.workspace
    assert loaded == active.workspace
    definition = loaded.match_definition
    assert definition.perspective_player_id == players[SEATS.index(perspective)].player_id
    for participant in definition.participants:
        assert participant.platform_player_id == f"explicit-{participant.player_label}"
        assert participant.player_id == next(
            p.player_id for p in players if p.display_name == participant.player_label)
    for number in range(1, 37):
        assignment = build_match_workspace_seat_assignment_v1(definition, number)
        assert tuple(getattr(assignment, f"{seat}_player_id") for seat in SEATS) == tuple(
            players[(index + number - 1) % 3].player_id for index in range(3))
        assert assignment.dealer_player_id == assignment.rearhand_player_id


def test_seat_move_only_moves_automatic_bundle_and_retains_collision_input():
    own = KnownPlayerV1("frontend-player-" + "a" * 64, "Own", (), ())
    other = KnownPlayerV1("frontend-player-" + "b" * 64, "Other", (), ())
    profile = build_local_frontend_profile_v1(
        known_players=(own, other), own_player_id=own.player_id,
        preferred_perspective_player_id=other.player_id)
    values = initial_seat_values_v1(profile)
    assert not any(values[f"{seat}_handle"] for seat in SEATS)
    values["own_seat"] = "rearhand"
    values, auto = project_own_seat_v1(values, profile)
    values.update(own_seat="forehand", rearhand_platform_id="explicit-own",
                  forehand_platform_id="",
                  forehand_handle=build_known_player_handle_v1(other.player_id))
    before = dict(values)
    with pytest.raises(SeatSetupError, match="occupied"):
        project_own_seat_v1(values, profile, auto_seat=auto)
    assert values == before
    values["forehand_handle"] = ""
    moved, auto = project_own_seat_v1(values, profile, auto_seat=auto)
    assert auto == "forehand" and moved["rearhand_handle"] == ""
    assert moved["rearhand_platform_id"] == ""
    assert moved["forehand_platform_id"] == "explicit-own"
    assert moved["perspective_seat"] == "forehand"
