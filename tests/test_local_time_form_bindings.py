from dataclasses import replace
from unittest.mock import patch

import pytest

from skatmind.app_web.local_time_conversion import LocalTimeError
from skatmind.app_web.local_time_forms import (
    LocalTimeFormContext,
    canonical_time_payload,
    occurrence_choices,
    resolve_local_form_timestamp,
)
from skatmind.app_web.time_zone_provider import TimeZoneUnavailable, time_zone_inventory

CONTEXT = LocalTimeFormContext("session-metadata", "a" * 64, b"test-key", 3)


def values(**changes):
    return {"time_form": CONTEXT.marker, "time_selection": CONTEXT.selection,
        "time_mode": "enter", "local_date": "2026-10-25", "local_time": "02:30",
        "local_zone": "Europe/Berlin", "local_occurrence": "", **changes}


@pytest.mark.parametrize("change", ({"local_date": "2025-10-26"}, {"local_time": "02:31"},
                                  {"local_zone": "Europe/Paris"}))
def test_occurrence_cannot_retime_changed_inputs(change):
    initial = values()
    token = occurrence_choices(initial, CONTEXT)[0][0]
    with pytest.raises(LocalTimeError, match="occurrence"):
        resolve_local_form_timestamp(values(**change, local_occurrence=token), CONTEXT,
                                     original=None, new=True)


def test_occurrence_is_bound_to_provider_version_form_and_source():
    initial = values()
    token = occurrence_choices(initial, CONTEXT)[0][0]
    for context in (replace(CONTEXT, marker="match-create"), replace(CONTEXT, selection="b" * 64)):
        with pytest.raises(LocalTimeError, match="occurrence"):
            resolve_local_form_timestamp(values(local_occurrence=token), context,
                                         original=None, new=True)
    for name in ("package_version", "iana_version"):
        with patch("skatmind.app_web.local_time_forms.time_zone_inventory", return_value=replace(
                time_zone_inventory(), **{name: "future"})):
            with pytest.raises(LocalTimeError, match="occurrence"):
                resolve_local_form_timestamp(values(local_occurrence=token), CONTEXT,
                                             original=None, new=True)


def test_keep_remove_and_blank_new_entry_need_no_conversion():
    original = "2016-12-31t23:59:60.123456789z"
    with patch("skatmind.app_web.local_time_forms.packaged_time_zone",
               side_effect=TimeZoneUnavailable()) as provider:
        for mode, expected in (("keep", original), ("remove", None)):
            assert resolve_local_form_timestamp(
                values(time_mode=mode, local_date="", local_time=""),
                CONTEXT, original=original, new=False) == expected
        assert resolve_local_form_timestamp(values(local_date="", local_time=""), CONTEXT,
                                            original=None, new=True) is None
    provider.assert_not_called()


def test_replacement_intent_and_private_stripping():
    for mode in ("keep", "remove"):
        with pytest.raises(LocalTimeError, match="intent"):
            resolve_local_form_timestamp(values(time_mode=mode), CONTEXT,
                                         original="source", new=False)
    payload = canonical_time_payload(
        {**values(), "kind": "set_game_metadata", "profile_generation": "3"},
        "2026-01-15T19:30:00+01:00")
    assert payload == {"kind": "set_game_metadata", "played_at": "2026-01-15T19:30:00+01:00"}
