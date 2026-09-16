from __future__ import annotations

import re

from skatmind.declaration_diagnostics import DeclarationValueError
from skatmind.errors import SkatMindWorkflowError
from skatmind.observed_trace_diagnostics import ObservedTraceError

from .card_entry_http import CardEntryConflict
from .compact_declaration_http import DeclarationConflict
from .form_parsing import FormFieldErrorV1
from .form_registry import FrontendFormDefinitionV1
from .frontend_profile_operations import FrontendProfilePersistenceConflictError
from .local_time_conversion import LocalTimeError
from .local_time_http import LocalTimeConflict
from .match_recovery import MatchRecoveryConflict
from .player_seat_setup import SeatSetupError
from .profile_driven_creation import ProfileDrivenCreationFieldError
from .session_card_entry import CardEntryError
from .time_zone_preferences import TimeZonePreferenceSaveError
from .time_zone_provider import TimeZoneUnavailable
from .validation_contracts import FrontendValidationIssueV1


def _issue(
    field: str | None,
    key: str,
    **arguments: object,
) -> FrontendValidationIssueV1:
    return FrontendValidationIssueV1(
        field_key=field,
        message_key=key,
        interpolation_arguments=tuple(
            sorted((name, str(value)) for name, value in arguments.items())
        ),
    )


def _known_field(
    definition: FrontendFormDefinitionV1,
    candidate: str | None,
) -> str | None:
    fields = {field.field_key for field in definition.safe_fields}
    return candidate if candidate in fields else None


def _mapped_message(field: str | None, message: str) -> FrontendValidationIssueV1:
    lowered = message.lower()
    minimum = re.search(r"at least ([0-9]+)", lowered)
    maximum = re.search(r"at most ([0-9]+)", lowered)
    if minimum is not None:
        return _issue(field, "validation.message.minimum", minimum=minimum.group(1))
    if maximum is not None:
        return _issue(field, "validation.message.maximum", maximum=maximum.group(1))
    if "required" in lowered or "must be non-empty" in lowered or "must contain exactly" in lowered:
        return _issue(field, "validation.message.required")
    if "integer" in lowered or "number" in lowered:
        return _issue(field, "validation.message.integer")
    if "duplicate" in lowered or "unique" in lowered or "already" in lowered:
        return _issue(field, "validation.message.duplicate")
    if "card" in lowered:
        return _issue(field, "validation.message.card_conflict")
    if (
        "rfc 3339" in lowered
        or "date" in lowered
        or "timecode" in lowered
        or "timestamp" in lowered
    ):
        return _issue(field, "validation.message.date_time")
    if "source" in lowered:
        return _issue(field, "validation.message.source_combination")
    if (
        "choice" in lowered
        or "supported" in lowered
        or "identify one" in lowered
        or "must be one" in lowered
    ):
        return _issue(field, "validation.message.choice")
    return _issue(field, "validation.message.product_rejected")


def map_form_field_errors_v1(
    errors: tuple[FormFieldErrorV1, ...],
    definition: FrontendFormDefinitionV1,
) -> tuple[FrontendValidationIssueV1, ...]:
    return tuple(
        _mapped_message(
            _known_field(definition, None if error.field == "_form" else error.field),
            error.message,
        )
        for error in errors
    )


def map_frontend_exception_v1(
    error: Exception,
    definition: FrontendFormDefinitionV1,
    *,
    status: int,
) -> tuple[FrontendValidationIssueV1, ...]:
    if isinstance(error, LocalTimeError):
        return (_issue(_known_field(definition, error.field_key),
                       "validation.local_time." + error.reason),)
    if isinstance(error, LocalTimeConflict):
        return (_issue(None, "validation.local_time." + error.reason),)
    if isinstance(error, TimeZoneUnavailable):
        return (_issue(_known_field(definition, "time_zone"),
                       "validation.local_time." + error.reason),)
    if isinstance(error, TimeZonePreferenceSaveError):
        return (_issue("time_zone", "validation.local_time.preference_save_failed"),)
    if isinstance(error, DeclarationValueError) and (
            definition.discriminator_field == "declaration_form" or definition.form_key in {
                "session.command.set_declaration", "match.operation.set_declaration"}):
        return (_issue(_known_field(definition, error.field_key),
                       f"validation.declaration.{error.reason}"),)
    if isinstance(error, DeclarationConflict):
        return (_issue(None, f"validation.declaration.{error.reason}"),)
    if isinstance(error, CardEntryError):
        return (FrontendValidationIssueV1(
            field_key=_known_field(definition, error.field_key),
            message_key=f"validation.card_entry.{error.reason}",
            session_card_feedback=(error.feedback if definition.action_route in {
                "/sessions/cards", "/sessions/play"} else None)),)
    if isinstance(error, CardEntryConflict):
        return (_issue(None, f"validation.card_entry.{error.reason}"),)
    if isinstance(error, ObservedTraceError) and definition.active_context_requirement == "matches":
        return (_issue(None, "validation.message.match_recording_conflict"),)
    if isinstance(error, MatchRecoveryConflict):
        return (_issue(None, f"validation.message.match_recovery_{error.reason}"),)
    if isinstance(error, SeatSetupError):
        return (_issue(_known_field(definition, error.field_key),
                        f"validation.message.setup_{error.reason}"),)
    if (isinstance(error, ProfileDrivenCreationFieldError)
            and definition.form_key == "session.create"
            and error.field_key == "perspective_seat"
            and str(error) == "Player-perspective recording requires one perspective seat."):
        return (_issue("perspective_seat", "validation.session.knowledge_perspective"),)
    fields = tuple(field.field_key for field in definition.safe_fields)
    lowered = str(error).lower()
    declared_field = getattr(error, "field_key", None)
    field = _known_field(definition, declared_field)
    if field is None:
        field = next(
            (
                candidate
                for candidate in sorted(fields, key=len, reverse=True)
                if re.search(
                    rf"(?<![a-z0-9_]){re.escape(candidate.lower())}(?![a-z0-9_])",
                    lowered,
                )
            ),
            None,
        )
    if isinstance(error, FrontendProfilePersistenceConflictError):
        return (_issue(field, "validation.message.persistence_conflict"),)
    if status == 409:
        key = (
            "validation.message.persistence_conflict"
            if any(word in lowered for word in ("disk", "file", "persist", "exists"))
            else "validation.message.stale"
        )
        return (_issue(field, key),)
    if isinstance(error, SkatMindWorkflowError):
        return (_issue(field, "validation.message.unsupported_workflow"),)
    return (_mapped_message(field, str(error)),)


def upload_validation_issues_v1(
    definition: FrontendFormDefinitionV1,
    *,
    status: int,
) -> tuple[FrontendValidationIssueV1, ...]:
    file_field = next(
        (field.field_key for field in definition.safe_fields if field.control_type == "file"),
        None,
    )
    key = (
        "validation.message.upload_size"
        if status == 413
        else "validation.message.upload_type"
        if status == 415
        else "validation.message.invalid_upload"
    )
    issues = [_issue(file_field, key)]
    if definition.file_reselection_behavior == "required":
        issues.append(_issue(file_field, "validation.message.file_reselection"))
    return tuple(issues)
