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
from skatmind.app_web.profile_driven_creation import prepare_profile_driven_match_creation_v1
from skatmind.app_web.profile_player_contracts import KnownPlayerV1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1


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
