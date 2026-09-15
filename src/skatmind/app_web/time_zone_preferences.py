"""Independent timezone preference mutation through the existing profile CAS."""

from dataclasses import replace

from .frontend_profile_contracts import FrontendInterfacePreferencesV1
from .frontend_profile_operations import (
    FrontendProfilePersistenceConflictError,
    save_prepared_frontend_profile_v1,
)
from .profile_player_operations import _build_updated, _current_document
from .time_zone_provider import packaged_time_zone


class TimeZonePreferenceSaveError(FrontendProfilePersistenceConflictError):
    pass


def set_frontend_time_zone(context, *, time_zone: str | None, expected_generation: int) -> str:
    document = _current_document(context, expected_generation=expected_generation)
    preferences = (FrontendInterfacePreferencesV1() if document is None
                   else document.interface_preferences)
    if time_zone is not None:
        # A selection save verifies the actual packaged resource as well as membership.
        packaged_time_zone(time_zone)
    if preferences.time_zone == time_zone:
        return "unchanged"
    requested = _build_updated(document,
        interface_preferences=replace(preferences, time_zone=time_zone))
    try:
        return save_prepared_frontend_profile_v1(context, requested=requested,
            expected_generation=expected_generation)
    except OSError as error:
        raise TimeZonePreferenceSaveError from error
