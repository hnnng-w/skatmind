from datetime import UTC, datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import patch

import pytest

from skatmind.app_web.local_time_conversion import LocalTimeError, local_time_candidates
from skatmind.app_web.time_zone_keys import require_time_zone_key
from skatmind.app_web.time_zone_provider import (
    TimeZoneUnavailable,
    _load_zone,
    packaged_time_zone,
    time_zone_inventory,
)


@pytest.mark.parametrize("zone,day,clock,expected", (
    ("Europe/Berlin", "2026-01-15", "19:30", "2026-01-15T19:30:00+01:00"),
    ("Europe/Berlin", "2026-07-15", "19:30", "2026-07-15T19:30:00+02:00"),
    ("UTC", "2026-01-15", "19:30:12.123456", "2026-01-15T19:30:12.123456+00:00"),
    ("Asia/Kathmandu", "2026-01-01", "00:15", "2026-01-01T00:15:00+05:45"),
    ("Pacific/Kiritimati", "2026-01-01", "00:15", "2026-01-01T00:15:00+14:00"),
    ("UTC", "0001-01-01", "00:00", "0001-01-01T00:00:00+00:00"),
    ("UTC", "9999-12-31", "23:59:59.1", "9999-12-31T23:59:59.100000+00:00"),
))
def test_independently_expected_unique_times(zone, day, clock, expected):
    candidates = local_time_candidates(day, clock, packaged_time_zone(zone))
    assert len(candidates) == 1
    assert candidates[0].timestamp == expected
    if zone == "Pacific/Kiritimati":
        assert candidates[0].utc == datetime(2025, 12, 31, 10, 15, tzinfo=UTC)


@pytest.mark.parametrize("zone,day,clock,offsets,minutes", (
    ("Europe/Berlin", "2026-10-25", "02:30", ("+02:00", "+01:00"), 60),
    ("Australia/Lord_Howe", "2026-04-05", "01:45", ("+11:00", "+10:30"), 30),
))
def test_fold_is_two_distinct_ordered_instants(zone, day, clock, offsets, minutes):
    candidates = local_time_candidates(day, clock, packaged_time_zone(zone))
    assert tuple(c.offset for c in candidates) == offsets
    assert candidates[1].utc - candidates[0].utc == timedelta(minutes=minutes)


@pytest.mark.parametrize("zone,day,clock", (
    ("Europe/Berlin", "2026-03-29", "02:30"),
    ("Australia/Lord_Howe", "2026-10-04", "02:15"),
    ("Pacific/Apia", "2011-12-30", "12:00"),
))
def test_gap_rejects_instead_of_rolling_forward(zone, day, clock):
    with pytest.raises(LocalTimeError, match="gap"):
        local_time_candidates(day, clock, packaged_time_zone(zone))


@pytest.mark.parametrize("day,clock,reason", (
    ("2026-02-29", "12:00", "date"), ("20260115", "12:00", "date"),
    ("2026-1-15", "12:00", "date"), ("0000-01-01", "12:00", "date"),
    ("10000-01-01", "12:00", "date"), ("2026-01-01", "1:00", "time"),
    ("2026-01-01", "24:00", "time"), ("2026-01-01", "12:00:60", "time"),
    ("2026-01-01", "12:00:00.1234567", "time"),
    ("2026-01-01", "12:00Z", "time"), ("2026-01-01", "12:00:00,5", "time"),
    ("2026-01-01", "12:00.5", "time"), ("2026-01-01", " 12:00", "time"),
))
def test_strict_native_syntax(day, clock, reason):
    with pytest.raises(LocalTimeError) as error:
        local_time_candidates(day, clock, UTC)
    assert error.value.reason == reason


def test_conversion_range_and_offset_seconds_are_not_rounded():
    with pytest.raises(LocalTimeError, match="range"):
        local_time_candidates("0001-01-01", "00:00", timezone(timedelta(hours=1)))
    with pytest.raises(LocalTimeError, match="range"):
        local_time_candidates("9999-12-31", "23:59", timezone(timedelta(hours=-1)))
    with pytest.raises(LocalTimeError, match="offset_seconds"):
        local_time_candidates("1800-01-01", "12:00", packaged_time_zone("Europe/Berlin"))


@pytest.mark.parametrize("key", ("", "/UTC", "../UTC", "Europe/../UTC", "C:\\UTC",
    "Europe//Berlin", "UTC\n", "UTC\x00", "UTC ", "a" * 256, None, 1, "Europe/Berlin.txt"))
def test_key_validation_precedes_inventory_and_resources(key):
    with patch("skatmind.app_web.time_zone_provider.time_zone_inventory") as inventory:
        with pytest.raises(TimeZoneUnavailable, match="zone"):
            packaged_time_zone(key)
    inventory.assert_not_called()


def test_inventory_order_exact_membership_cache_and_host_independence():
    inventory = time_zone_inventory()
    assert inventory.keys[:2] == ("Europe/Berlin", "UTC")
    assert inventory.keys[2:] == tuple(sorted(inventory.membership - {"Europe/Berlin", "UTC"}))
    assert len(inventory.keys) == len(inventory.membership)
    assert time_zone_inventory() is inventory
    require_time_zone_key("Former/Unavailable")  # Stored syntax needs no database lookup.
    with patch("skatmind.app_web.time_zone_provider.resources.files") as resources:
        with pytest.raises(TimeZoneUnavailable, match="zone"):
            packaged_time_zone("Former/Unavailable")
    resources.assert_not_called()
    import zoneinfo
    original = zoneinfo.TZPATH
    try:
        zoneinfo.reset_tzpath(())
        _load_zone.cache_clear()
        assert packaged_time_zone("Europe/Berlin").utcoffset(datetime(2026, 7, 15)) == timedelta(
            hours=2)
    finally:
        zoneinfo.reset_tzpath(original)
    assert _load_zone.cache_info().maxsize == 64


def test_missing_corrupt_and_oversized_database_fail_actionably():
    inventory = time_zone_inventory()
    try:
        time_zone_inventory.cache_clear()
        with patch.dict("sys.modules", {"tzdata": None}), pytest.raises(TimeZoneUnavailable):
            time_zone_inventory()
        for content in (b"", b"UTC\n../bad\n", b"UTC\nUTC\n", b"x" * 1_048_577):
            with patch("skatmind.app_web.time_zone_provider.resources.files") as files:
                files.return_value.joinpath.return_value.open.return_value = BytesIO(content)
                with pytest.raises(TimeZoneUnavailable):
                    time_zone_inventory()
        assert time_zone_inventory() == inventory
        _load_zone.cache_clear()
        for broken in (b"broken", b"TZif2" + b"\0" * 35, b"TZif2" + b"\0" * 39):
            with patch("skatmind.app_web.time_zone_provider.resources.files") as files:
                files.return_value.joinpath.return_value.open.return_value = BytesIO(broken)
                with pytest.raises(TimeZoneUnavailable):
                    packaged_time_zone("UTC")
    finally:
        time_zone_inventory.cache_clear()
        _load_zone.cache_clear()
