"""Private stored-key syntax, independent of installed timezone data."""

import re

TIME_ZONE_KEY_MAX_LENGTH = 255
DEFAULT_TIME_ZONE = "Europe/Berlin"
_KEY = re.compile(r"[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)*\Z", re.ASCII)


def require_time_zone_key(value: object) -> str:
    if (type(value) is not str or not 1 <= len(value) <= TIME_ZONE_KEY_MAX_LENGTH
            or _KEY.fullmatch(value) is None):
        raise ValueError("Time zone must be a bounded IANA-style key.")
    return value
