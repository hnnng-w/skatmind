"""Private local-field semantics and source-bound occurrence choices."""

import hashlib
import hmac
import json
from dataclasses import dataclass

from .local_time_conversion import LocalTimeError, local_time_candidates
from .time_zone_keys import DEFAULT_TIME_ZONE
from .time_zone_provider import TimeZoneUnavailable, packaged_time_zone, time_zone_inventory

LOCAL_TIME_VISIBLE_FIELDS = ("time_mode", "local_date", "local_time", "local_zone",
                             "local_occurrence")
LOCAL_TIME_FIELDS = ("time_form", "time_selection", *LOCAL_TIME_VISIBLE_FIELDS)


@dataclass(frozen=True, slots=True)
class LocalTimeFormContext:
    marker: str
    selection: str
    key: bytes
    profile_generation: int
    zone: str = DEFAULT_TIME_ZONE
    submitted: tuple[tuple[str, str], ...] = ()


def occurrence_choices(values, context):
    zone = packaged_time_zone(values["local_zone"])
    inventory = time_zone_inventory()
    candidates = local_time_candidates(values["local_date"], values["local_time"], zone)
    source = (context.marker, context.selection, values["local_date"], values["local_time"],
              values["local_zone"], inventory.package_version, inventory.iana_version)
    return tuple((name + "." + hmac.new(context.key, b"local_occurrence\0" + json.dumps(
        (source, name, candidate.timestamp), separators=(",", ":")).encode(),
        hashlib.sha256).hexdigest(), candidate)
        for name, candidate in zip(("earlier", "later"), candidates, strict=False))


def resolve_local_form_timestamp(values, context, *, original: str | None, new: bool) -> str | None:
    """Keep is source-text identity, including spellings datetime cannot reproduce."""
    if "played_at" in values:
        raise LocalTimeError("mixed", "local_time")
    required = set(LOCAL_TIME_FIELDS) - {"local_occurrence"}
    if required - set(values) or any(type(values[name]) is not str for name in required):
        raise LocalTimeError("fields")
    mode = values["time_mode"]
    if mode not in (("enter",) if new else ("keep", "replace", "remove")):
        raise LocalTimeError("mode", "time_mode")
    clock, day = values["local_time"], values["local_date"]
    occurrence = values.get("local_occurrence", "")
    if type(occurrence) is not str or len(occurrence) > 72:
        raise LocalTimeError("occurrence", "local_occurrence")
    if mode in {"keep", "remove"}:
        if day or clock or occurrence:
            raise LocalTimeError("intent", "time_mode")
        return original if mode == "keep" else None
    if not day and not clock and new:
        if occurrence:
            raise LocalTimeError("occurrence", "local_occurrence")
        return None
    if not day:
        raise LocalTimeError("date_required", "local_date")
    if not clock:
        raise LocalTimeError("time_required", "local_time")
    try:
        choices = occurrence_choices(values, context)
    except TimeZoneUnavailable as error:
        raise LocalTimeError(error.reason, "local_zone") from error
    if len(choices) == 1:
        if occurrence:
            raise LocalTimeError("occurrence", "local_occurrence")
        return choices[0][1].timestamp
    if not occurrence:
        raise LocalTimeError("ambiguous", "local_occurrence")
    for token, candidate in choices:
        if hmac.compare_digest(occurrence, token):
            return candidate.timestamp
    raise LocalTimeError("occurrence", "local_occurrence")


def canonical_time_payload(values, timestamp):
    """Strip only marked private fields before the unchanged Product form parser."""
    return {**{name: value for name, value in values.items()
               if name not in {*LOCAL_TIME_FIELDS, "profile_generation"}},
            "played_at": timestamp or ""}
