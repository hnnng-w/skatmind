"""Bounded browser presentation for deliberate own-seat placement, without Product work."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

from .frontend_identifier_generation import build_known_player_handle_v1
from .frontend_profile_operations import StaleFrontendProfileGenerationError
from .profile_player_operations import resolve_known_player_handle_v1

SEATS = ("forehand", "middlehand", "rearhand")
MATCH_PERSON_SETUP_ACTIONS = {f"choose_{seat}": seat for seat in SEATS}
SEAT_SETUP_FIELDS = (
    "perspective_mode", "own_seat", "own_player_handle", "perspective_seat",
    *(f"{seat}_{suffix}" for seat in SEATS for suffix in ("mode", "handle", "name")),
)


class SeatSetupError(ValueError):
    def __init__(self, reason, field_key=None):
        self.reason = reason
        self.field_key = field_key
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class SeatSetupV1:
    token: str
    profile_key: tuple
    values: tuple[tuple[str, str], ...]
    auto_seat: str = ""
    reviewed: bool = False
    created_at: float = 0


def profile_setup_key_v1(profile):
    from .frontend_profile_codec import build_local_frontend_profile_v1
    profile = profile or build_local_frontend_profile_v1()
    return (profile.known_players, profile.own_player_id,
        profile.preferred_game_platform, profile.interface_preferences)


def own_handle_v1(profile):
    return (build_known_player_handle_v1(profile.own_player_id)
            if profile is not None and profile.own_player_id else "")


def initial_seat_values_v1(profile):
    own = own_handle_v1(profile)
    return {
        "perspective_mode": "own" if own else "manual", "own_seat": "",
        "own_player_handle": own, "perspective_seat": "",
        **{f"{seat}_{suffix}": ("saved" if profile and profile.known_players else "new")
           if suffix == "mode" else "" for seat in SEATS for suffix in ("mode", "handle", "name")},
    }


def current_seat_setup_v1(context, family, profile):
    with context.lock:
        current = context.creation_setups.get(family)
        key = profile_setup_key_v1(profile)
        if (current is None or current.profile_key != key
                or time.monotonic() - current.created_at >= 1800):
            context.setup_serial += 1
            token = hmac.new(context.language_context.key,
                f"seat-setup\0{family}\0{context.setup_serial}".encode(),
                hashlib.sha256).hexdigest()
            current = SeatSetupV1(token, key, tuple(initial_seat_values_v1(profile).items()),
                                  created_at=time.monotonic())
            context.creation_setups[family] = current
        return current


def project_own_seat_v1(values, profile, *, auto_seat=""):
    """Move only the server-retained automatic bundle; collisions never swap rows."""
    result = dict(values)
    own = own_handle_v1(profile)
    mode = result.get("perspective_mode")
    seat = result.get("own_seat", "")
    if mode not in {"own", "manual"} or seat not in {"", *SEATS}:
        raise SeatSetupError("choice", "own_seat")
    if result.get("own_player_handle", "") != own:
        raise StaleFrontendProfileGenerationError
    if mode == "own" and not own:
        raise StaleFrontendProfileGenerationError
    if mode == "own":
        resolve_known_player_handle_v1(profile, own)
    for place in SEATS:
        if result.get(f"{place}_mode") not in {"saved", "new"}:
            raise SeatSetupError("choice", f"{place}_mode")
    target = seat if mode == "own" else ""
    if auto_seat:
        if (result.get(f"{auto_seat}_handle") != own
                or result.get(f"{auto_seat}_name", "").strip()
                or result.get(f"{auto_seat}_mode") != "saved"):
            raise SeatSetupError("own_binding", f"{auto_seat}_handle")
    if target != auto_seat:
        exact_own = bool(target and result.get(f"{target}_mode") == "saved"
            and result.get(f"{target}_handle") == own
            and not result.get(f"{target}_name", "").strip())
        if target and any(result.get(f"{target}_{suffix}", "").strip()
                          for suffix in ("handle", "name", "platform_id")) and not exact_own:
            raise SeatSetupError("occupied", f"{target}_handle")
        account = result.get(f"{auto_seat}_platform_id", "").strip() if auto_seat else ""
        target_account = result.get(f"{target}_platform_id", "").strip() if exact_own else ""
        if account and target_account and account != target_account:
            raise SeatSetupError("account_conflict", f"{target}_platform_id")
        account = account or target_account
        if auto_seat:
            result[f"{auto_seat}_handle"] = ""
            if f"{auto_seat}_platform_id" in result:
                result[f"{auto_seat}_platform_id"] = ""
        if target:
            result[f"{target}_mode"] = "saved"
            result[f"{target}_handle"] = own
            result[f"{target}_name"] = ""
            if f"{target}_platform_id" in result or account:
                result[f"{target}_platform_id"] = account
    if mode == "own":
        for place in SEATS:
            if place != target and result.get(f"{place}_handle") == own:
                raise SeatSetupError("duplicate_own", f"{place}_handle")
        if result.get("perspective_seat", "") not in {"", target, auto_seat}:
            raise SeatSetupError("own_binding", "perspective_seat")
        result["perspective_seat"] = target
    elif auto_seat:
        result["perspective_seat"] = ""
    return result, target


def require_own_binding_v1(values, profile):
    mode = values.get("perspective_mode")
    if mode not in {"own", "manual"}:
        raise SeatSetupError("choice", "perspective_mode")
    if mode == "own":
        seat = values.get("own_seat")
        own = own_handle_v1(profile)
        if not own or values.get("own_player_handle") != own:
            raise StaleFrontendProfileGenerationError
        if seat not in SEATS:
            raise SeatSetupError("seat_required", "own_seat")
        if (values.get(f"{seat}_handle") != own or values.get(f"{seat}_name", "").strip()
                or values.get(f"{seat}_mode") != "saved" or values.get("perspective_seat") != seat):
            raise SeatSetupError("own_binding", "own_seat")


def roster_names_v1(values, profile):
    names = []
    for seat in SEATS:
        handle = values.get(f"{seat}_handle", "")
        if handle:
            try:
                name = resolve_known_player_handle_v1(profile, handle).display_name
            except ValueError:
                name = ""
        else:
            name = values.get(f"{seat}_name", "").strip()
        names.append(name)
    return tuple(names)


def roster_person_value_v1(values, seat):
    """Presentation identity only: no Player ID generation or saved default."""
    handle = values.get(f"{seat}_handle", "").strip()
    name = values.get(f"{seat}_name", "").strip()
    mode = values.get(f"{seat}_mode")
    if mode == "saved" and handle and not name:
        return "saved:" + handle
    if mode == "new" and name and not handle:
        return "new:" + hashlib.sha256(name.encode("utf-8")).hexdigest()
    return ""


def match_perspective_seat_v1(values):
    choice = values.get("perspective_seat", "")
    # Own placement and the low-level seat adapter retain their existing semantics.
    if choice in SEATS:
        return choice
    matches = [seat for seat in SEATS if choice and roster_person_value_v1(values, seat) == choice]
    return matches[0] if len(matches) == 1 else ""


def submit_seat_setup_v1(context, family, profile, values, *, generation, local_timestamp=None):
    """Return True only for an unchanged, explicitly reviewed final roster."""
    from .profile_driven_creation import (
        prepare_profile_driven_match_creation_v1,
        prepare_profile_driven_session_creation_v1,
    )

    action = values.pop("setup_action", "")
    token = values.pop("setup_context", "")
    current = current_seat_setup_v1(context, family, profile)
    if current.token != token:
        raise StaleFrontendProfileGenerationError
    chosen_seat = MATCH_PERSON_SETUP_ACTIONS.get(action) if family == "matches" else None
    if action not in {"update", "create"} and chosen_seat is None:
        raise SeatSetupError("review_required")
    if chosen_seat is not None:
        if values.get("perspective_mode") != "manual":
            raise SeatSetupError("choice", "perspective_mode")
        if values.get("time_form") == "match-create":
            from .local_time_http import local_time_context, require_local_source
            require_local_source({**values, "profile_generation": str(generation)},
                local_time_context(context, None, "match-create"))
    if any(len(value) > 8192 for value in values.values()):
        raise SeatSetupError("choice")
    for name in ("save_players", "save_platform"):
        if values.get(name, "") not in {"", "on"}:
            raise SeatSetupError("choice", name)
    if action == "create":
        if (family == "matches" and values.get("perspective_mode") == "manual"
                and values.get("perspective_seat") in SEATS):
            # Explicit legacy clients may resend the seat they reviewed. The full
            # roster comparison below still prevents reinterpreting that seat.
            values["perspective_seat"] = roster_person_value_v1(values, values["perspective_seat"])
        compared = {name: value for name, value in values.items() if name != "local_occurrence"}
        previous = {name: value for name, value in current.values if name != "local_occurrence"}
        if not current.reviewed or previous != compared:
            raise SeatSetupError("review_required")
        require_own_binding_v1(values, profile)
        with context.lock:
            if (context.creation_setups.get(family) is not current
                    or context.frontend_profile.generation != generation):
                raise StaleFrontendProfileGenerationError
            # A final submission is single-use even if Product/profile persistence fails.
            del context.creation_setups[family]
        return True
    if (family == "matches" and values.get("perspective_mode") == "own"
            and dict(current.values).get("perspective_mode") == "manual"):
        # Changing assistance mode derives the own person; it is not a second choice.
        values["perspective_seat"] = ""
    try:
        projected, auto = project_own_seat_v1(values, profile, auto_seat=current.auto_seat)
    except SeatSetupError as error:
        if family == "matches" and error.field_key == "perspective_seat":
            raise SeatSetupError(error.reason, "own_seat") from error
        raise
    if family == "matches" and projected.get("perspective_mode") == "manual":
        choice = projected.get("perspective_seat", "")
        if chosen_seat is not None:
            # The activated row action chooses from this submitted roster, never
            # from the old occupant of a seat or a second editable person control.
            choice = roster_person_value_v1(projected, chosen_seat)
            if not choice:
                field = "name" if projected.get(f"{chosen_seat}_mode") == "new" else "handle"
                raise SeatSetupError("choice", f"{chosen_seat}_{field}")
        elif choice in SEATS:
            previous = dict(current.values)
            # Legacy seat clients are bound to the previously presented person.
            # Only a first explicit legacy submission has no prior roster to bind.
            source = previous if any(roster_names_v1(previous, profile)) else projected
            choice = roster_person_value_v1(source, choice)
        projected["perspective_seat"] = choice
        if not match_perspective_seat_v1(projected):
            projected["perspective_seat"] = ""
    values.clear()
    values.update(projected)
    with context.lock:
        if (context.creation_setups.get(family) is not current
                or context.frontend_profile.generation != generation):
            raise StaleFrontendProfileGenerationError
        current = SeatSetupV1(current.token, current.profile_key,
            tuple(values.items()), auto, False, current.created_at)
        context.creation_setups[family] = current
    complete = all(roster_names_v1(values, profile))
    if complete or chosen_seat is not None:
        if family == "sessions":
            prepare_profile_driven_session_creation_v1(values, profile=profile,
                expected_profile_generation=generation, existing_session_ids=(),
                entropy_source=None, validation_only=True)
        else:
            from .local_time_forms import canonical_time_payload
            if chosen_seat is not None and values.get("time_form") == "match-create":
                from .local_time_http import prepare_match_creation_time
                local_timestamp = prepare_match_creation_time(context,
                    {**values, "profile_generation": str(generation)})
            metadata = (canonical_time_payload(values, local_timestamp)
                        if values.get("time_form") == "match-create" else values)
            prepare_profile_driven_match_creation_v1(metadata, profile=profile,
                expected_profile_generation=generation, existing_match_ids=(),
                entropy_source=None, validation_only=True, allow_missing_perspective=True)
            complete = bool(match_perspective_seat_v1(values))
    with context.lock:
        if (context.creation_setups.get(family) is not current
                or context.frontend_profile.generation != generation):
            raise StaleFrontendProfileGenerationError
        context.creation_setups[family] = SeatSetupV1(current.token, current.profile_key,
            tuple(values.items()), auto, complete, current.created_at)
    return False
