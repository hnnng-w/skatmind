"""Workflow-specific source binding and existing metadata mutation dispatch."""

import hashlib
import hmac
import json
import re

from .card_entry_http import CardEntryConflict, _fresh
from .compact_declaration_http import declaration_binding
from .frontend_profile_operations import StaleFrontendProfileGenerationError
from .local_time_conversion import LocalTimeError
from .local_time_forms import (
    LOCAL_TIME_FIELDS,
    LocalTimeFormContext,
    canonical_time_payload,
    resolve_local_form_timestamp,
)
from .player_seat_setup import current_seat_setup_v1
from .time_zone_keys import DEFAULT_TIME_ZONE
from .workflow_state import StaleFrontendWorkflowRevisionError


class LocalTimeConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason="stale"):
        self.reason = reason
        super().__init__(reason)


def local_time_context(app, active, marker, target=""):
    """Profile generation is separately checked and regenerated after a language save."""
    if app is None:
        profile, generation, feedback = None, 0, None
        key = active.review_selection_key if active is not None else b"unbound-rendering"
    else:
        with app.lock:
            profile = app.frontend_profile.document
            generation = app.frontend_profile.generation
            key = app.language_context.key
            family = "sessions" if marker.startswith("session-") else "matches"
            retained = app.form_feedback._feedback.get(family)
            feedback = retained[1] if retained is not None and retained[0] is active else None
    zone = (DEFAULT_TIME_ZONE if profile is None or profile.interface_preferences.time_zone is None
            else profile.interface_preferences.time_zone)
    if marker == "match-create":
        setup = current_seat_setup_v1(app, "matches", profile)
        source = (setup.token, zone)
    else:
        source = (declaration_binding(active,
            "session-time" if marker.startswith("session-") else "match-time", target), zone)
    selection = hmac.new(key, b"local_time_source\0" + json.dumps(
        (marker, source, str(target)), separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
    submitted = ()
    if (feedback is not None
            and feedback.safe_visible_values.singular("time_selection") == selection):
        submitted = tuple((entry.field, entry.values[0])
                          for entry in feedback.safe_visible_values.entries)
    elif marker == "match-create":
        submitted = setup.values
    return LocalTimeFormContext(marker, selection, key, generation, zone, submitted)


def require_local_source(values, context):
    if values.get("time_form") != context.marker:
        raise LocalTimeError("fields")
    if values.get("profile_generation") != str(context.profile_generation):
        raise StaleFrontendProfileGenerationError
    selection = values.get("time_selection")
    if type(selection) is not str or not re.fullmatch(r"[0-9a-f]{64}", selection):
        raise LocalTimeError("fields")
    if not hmac.compare_digest(selection, context.selection):
        raise LocalTimeConflict()


def prepare_match_creation_time(app, values):
    context = local_time_context(app, None, "match-create")
    require_local_source(values, context)
    timestamp = resolve_local_form_timestamp(values, context, original=None, new=True)
    if timestamp and values.get("played_date") and values["played_date"] != values["local_date"]:
        raise LocalTimeError("date_mismatch", "local_date")
    return timestamp


def dispatch_local_metadata(app, route, values):
    session = route == "/sessions/command"
    marker = values.get("time_form")
    if marker not in (("session-metadata", "session-metadata-correction") if session else
                      ("match-metadata",)):
        raise LocalTimeError("fields")
    from .form_registry import _MATCH_METADATA_FIELDS
    allowed = {*LOCAL_TIME_FIELDS, "profile_generation", "managed_handle", "expected_revision"}
    allowed |= {"kind", "game_id"} if session else {
        "operation", "match_position", *set(_MATCH_METADATA_FIELDS) - {"played_at"}}
    target = values.get("target_revision", "")
    if marker == "session-metadata-correction":
        allowed.add("target_revision")
        if not re.fullmatch(r"[1-9][0-9]{0,5}", target):
            raise LocalTimeError("fields")
    if "played_at" in values:
        raise LocalTimeError("mixed", "local_time")
    if set(values) - allowed or allowed - {"local_occurrence"} - set(values):
        raise LocalTimeError("fields")
    if values.get("kind" if session else "operation") != (
            "set_game_metadata" if session else "update_match_metadata"):
        raise LocalTimeError("fields")
    managed = app.managed_stateful
    gate = managed.session_lifecycle_lock if session else managed.match_lifecycle_lock
    with gate:
        with app.lock:
            active = managed.active_session if session else managed.active_match
        if active is None or values["managed_handle"] != active.handle:
            raise LocalTimeConflict()
        with active.lock if session else active.capture.lock:
            context = local_time_context(app, active, marker, target)
            require_local_source(values, context)
            revision = active.state.revision if session else active.workspace.revision
            if values["expected_revision"] != str(revision) or (not session and
                    values["match_position"] != str(active.selected_position)):
                raise LocalTimeConflict()
            if session:
                from skatmind.session_transitions import replay_session_state_v1
                original = replay_session_state_v1(active.state).played_at
                if target:
                    record = next((r for r in active.state.command_log if r.revision == int(target)
                                   and r.command.kind == "set_game_metadata"), None)
                    if record is None:
                        raise LocalTimeConflict()
                    original = record.command.played_at
            else:
                original = active.workspace.match_definition.played_at
            try:
                _fresh(active, session=session)
            except CardEntryConflict as error:
                raise LocalTimeConflict(error.reason) from error
            timestamp = resolve_local_form_timestamp(values, context, original=original,
                new=marker == "session-metadata" and original is None)
            if marker == "session-metadata" and original is not None:
                if values["time_mode"] != "keep":
                    raise LocalTimeError("correction_required", "time_mode")
                # Append-only metadata may supply a missing ID, but cannot record
                # an already accepted timestamp twice. Absence preserves its exact text.
                timestamp = None
            payload = canonical_time_payload(values, timestamp)
            payload.pop("managed_handle")
            # Recheck generation immediately before invoking the existing mutation.
            with app.lock:
                if app.frontend_profile.generation != context.profile_generation:
                    raise StaleFrontendProfileGenerationError
            try:
                if session:
                    from .session_form_translation import build_session_edit_from_form_v1
                    from .session_frontend import apply_guided_session_edit_v1
                    payload.pop("expected_revision")
                    edit = build_session_edit_from_form_v1(payload, current_revision=revision)
                    result = apply_guided_session_edit_v1(active, edit)
                    if result.status in {"conflict", "stale"}:
                        raise LocalTimeConflict("file_changed")
                    if result.status in {"rejected", "unavailable"}:
                        raise LocalTimeError("rejected")
                    return "/sessions/current#session-recording"
                from .match_frontend import apply_unified_match_operation_v1
                result = apply_unified_match_operation_v1(active, payload)
                if result.http_status == 409:
                    raise LocalTimeConflict("file_changed")
                if result.http_status != 200:
                    raise LocalTimeError("rejected")
                return f"/matches/position/{active.selected_position}#match-metadata"
            except OSError as error:
                raise LocalTimeConflict("save_failed") from error
