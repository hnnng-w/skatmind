"""Pure bounded wall-time resolution, with explicit UTC-instant deduplication."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, tzinfo

from skatmind.rfc3339 import parse_rfc3339_datetime

_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_TIME = re.compile(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?\Z")


class LocalTimeError(ValueError):
    def __init__(self, reason: str, field_key: str | None = None):
        self.reason = reason
        self.field_key = field_key
        super().__init__("Local time input is invalid: " + reason + ".")


@dataclass(frozen=True, slots=True)
class LocalTimeCandidate:
    timestamp: str
    offset: str
    utc: datetime


def local_time_candidates(local_date: str, local_time: str, zone: tzinfo
                          ) -> tuple[LocalTimeCandidate, ...]:
    if not isinstance(zone, tzinfo):
        raise LocalTimeError("zone", "local_zone")
    if type(local_date) is not str or _DATE.fullmatch(local_date) is None:
        raise LocalTimeError("date", "local_date")
    if type(local_time) is not str or _TIME.fullmatch(local_time) is None:
        raise LocalTimeError("time", "local_time")
    try:
        day = datetime.strptime(local_date, "%Y-%m-%d").date()
    except ValueError as error:
        raise LocalTimeError("date", "local_date") from error
    try:
        wall = datetime.combine(day, time.fromisoformat(local_time))
    except ValueError as error:
        raise LocalTimeError("time", "local_time") from error
    candidates = {}
    try:
        for fold in (0, 1):
            aware = wall.replace(tzinfo=zone, fold=fold)
            instant = aware.astimezone(UTC)
            if instant.astimezone(zone).replace(tzinfo=None) != wall:
                continue
            offset = aware.utcoffset()
            if offset is None or offset.total_seconds() % 60:
                raise LocalTimeError("offset_seconds", "local_date")
            timestamp = aware.isoformat(timespec="microseconds" if "." in local_time else "seconds")
            parse_rfc3339_datetime(timestamp, "played_at")
            candidates[instant] = LocalTimeCandidate(timestamp, timestamp[-6:], instant)
    except (OverflowError, ValueError) as error:
        if isinstance(error, LocalTimeError):
            raise
        raise LocalTimeError("range", "local_date") from error
    if not candidates:
        raise LocalTimeError("gap", "local_time")
    return tuple(candidates[instant] for instant in sorted(candidates))
