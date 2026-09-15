"""Finite packaged tzdata access; never consult or change host TZPATH."""

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from io import BytesIO
from struct import error as StructError
from zoneinfo import ZoneInfo

from .time_zone_keys import require_time_zone_key

_MAX_RESOURCE_BYTES = 1_048_576
_MAX_KEYS = 2048


class TimeZoneUnavailable(ValueError):
    def __init__(self, reason="database"):
        self.reason = reason
        super().__init__("Packaged time zone data is unavailable: " + reason + ".")


@dataclass(frozen=True, slots=True)
class TimeZoneInventory:
    package_version: str
    iana_version: str
    keys: tuple[str, ...]
    membership: frozenset[str]


def _read(resource) -> bytes:
    with resource.open("rb") as stream:
        data = stream.read(_MAX_RESOURCE_BYTES + 1)
    if not data or len(data) > _MAX_RESOURCE_BYTES:
        raise TimeZoneUnavailable()
    return data


@lru_cache(maxsize=1)
def time_zone_inventory() -> TimeZoneInventory:
    try:
        import tzdata

        keys = _read(resources.files(tzdata).joinpath("zones")).decode("ascii").splitlines()
        if not 2 <= len(keys) <= _MAX_KEYS or len(set(keys)) != len(keys):
            raise TimeZoneUnavailable()
        for key in keys:
            require_time_zone_key(key)
        members = frozenset(keys)
        if not {"Europe/Berlin", "UTC"} <= members:
            raise TimeZoneUnavailable()
        versions = (tzdata.__version__, tzdata.IANA_VERSION)
        if any(type(v) is not str or not 1 <= len(v) <= 32 or not v.isascii()
               or not v.replace(".", "").isalnum() for v in versions):
            raise TimeZoneUnavailable()
        ordered = ("Europe/Berlin", "UTC", *sorted(members - {"Europe/Berlin", "UTC"}))
        return TimeZoneInventory(*versions, ordered, members)
    except (ImportError, OSError, ValueError, AttributeError) as error:
        raise TimeZoneUnavailable() from error


def packaged_time_zone(key: str) -> ZoneInfo:
    try:
        require_time_zone_key(key)
    except ValueError as error:
        raise TimeZoneUnavailable("zone") from error
    inventory = time_zone_inventory()
    # Membership is checked before any key-dependent resource traversal or cache access.
    if key not in inventory.membership:
        raise TimeZoneUnavailable("zone")
    return _load_zone(key, inventory.package_version, inventory.iana_version)


@lru_cache(maxsize=64)
def _load_zone(key: str, package_version: str, iana_version: str) -> ZoneInfo:
    try:
        resource = resources.files("tzdata.zoneinfo").joinpath(*key.split("/"))
        return ZoneInfo.from_file(BytesIO(_read(resource)), key=key)
    except (ImportError, OSError, ValueError, EOFError, StructError, AssertionError) as error:
        raise TimeZoneUnavailable() from error
