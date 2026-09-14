"""Exact-source adapter on existing declaration routes and save/correction boundaries."""

from __future__ import annotations

import hashlib
import hmac
import json
import re

from .card_entry_http import CardEntryConflict, _fresh
from .compact_declaration_form import (
    DECLARATION_FIELDS,
    explicit_declaration_values,
    form_error,
    parse_compact_declaration,
)
from .session_form_translation import build_session_edit_from_form_v1
from .session_frontend import apply_guided_session_edit_v1
from .workflow_state import StaleFrontendWorkflowRevisionError


class DeclarationConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason="stale"):
        super().__init__()
        self.reason = reason


def declaration_binding(context, marker, target=""):
    session = marker.startswith("session-")
    if session:
        key = context.review_selection_key
        source = (context.handle, context.generation, context.document.to_dict())
    else:
        key = context.card_entry_key
        game = context.workspace.slots[context.selected_position - 1].observed_game
        source = (context.handle, context.position_generation, context.capture.content_fingerprint,
                  context.workspace.to_dict(), context.selected_position,
                  None if game is None else game.game_id)
    data = json.dumps((source, marker, str(target)), sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, b"compact_declaration\0" + data, hashlib.sha256).hexdigest()


def dispatch_compact_declaration(app, route, values):
    session = route == "/sessions/command"
    marker = values.get("declaration_form")
    permitted = ("session-declaration", "session-correction") if session else (
        "match-declaration", "match-clear")
    if marker not in permitted:
        raise form_error("fields")
    required = {"managed_handle", "expected_revision", "declaration_form", "declaration_selection",
                "kind" if session else "operation"}
    if not session:
        required.add("match_position")
    if marker == "session-correction":
        required.add("target_revision")
    if marker == "match-clear":
        required.add("confirm_clear")
        allowed = required
    else:
        required.update(("game_type", "bid_value", "matadors"))
        if not session:
            required.add("declarer_player_id")
        allowed = required | set(DECLARATION_FIELDS)
    if set(values) - allowed or required - set(values):
        raise form_error("fields")
    if values.get("kind" if session else "operation") != "set_declaration":
        raise form_error("fields")
    target = values.get("target_revision", "")
    if marker == "session-correction" and (
            type(target) is not str or not re.fullmatch(r"[1-9][0-9]*", target)):
        raise form_error("target", "target_revision")
    managed = app.managed_stateful
    gate = managed.session_lifecycle_lock if session else managed.match_lifecycle_lock
    with gate:
        with app.lock:
            active = managed.active_session if session else managed.active_match
        if active is None or values["managed_handle"] != active.handle:
            raise DeclarationConflict()
        with active.lock if session else active.capture.lock:
            selection = values["declaration_selection"]
            if type(selection) is not str or not re.fullmatch(r"[0-9a-f]{64}", selection):
                raise form_error("binding")
            if not hmac.compare_digest(selection, declaration_binding(active, marker, target)):
                raise DeclarationConflict()
            revision = active.state.revision if session else active.workspace.revision
            if values["expected_revision"] != str(revision) or (
                    not session and values["match_position"] != str(active.selected_position)):
                raise DeclarationConflict()
            if marker == "session-correction" and not any(
                    record.revision == int(target) and record.command.kind == "set_declaration"
                    for record in active.state.command_log):
                raise DeclarationConflict()
            try:
                _fresh(active, session=session)
            except CardEntryConflict as error:
                raise DeclarationConflict(error.reason) from error
            if marker == "match-clear":
                if values["confirm_clear"] != "on":
                    raise form_error("fields", "confirm_clear")
                payload = {"game_type": "", "declarer_player_id": ""}
            else:
                declaration = parse_compact_declaration(values)
                payload = explicit_declaration_values(declaration)
            try:
                if session:
                    payload["kind"] = "set_declaration"
                    if target:
                        payload["target_revision"] = target
                    edit = build_session_edit_from_form_v1(payload, current_revision=revision)
                    result = apply_guided_session_edit_v1(active, edit)
                    if result.status in {"conflict", "stale"}:
                        raise DeclarationConflict("file_changed")
                    if result.status == "rejected":
                        raise _session_rejection(result)
                    return "/sessions/current#session-recording"
                from .match_frontend import apply_unified_match_operation_v1
                if marker != "match-clear":
                    declarer = values["declarer_player_id"]
                    if declarer not in {
                            p.player_id for p in active.workspace.match_definition.participants}:
                        raise form_error("declarer", "declarer_player_id")
                    payload["declarer_player_id"] = declarer
                payload.update(operation="set_declaration",
                               match_position=str(active.selected_position),
                               expected_revision=str(revision))
                result = apply_unified_match_operation_v1(active, payload)
                if result.http_status == 409:
                    raise DeclarationConflict("file_changed")
                if result.http_status != 200:
                    raise form_error("rejected")
                return f"/matches/position/{active.selected_position}#match-recording"
            except OSError as error:
                raise DeclarationConflict("save_failed") from error


def _session_rejection(result):
    for diagnostic in result.validation_diagnostics:
        if diagnostic.path == "/command/declaration/matadors":
            reason = {"declaration_violation": "count_mismatch",
                      "information_policy_violation": "count_unverifiable",
                      "missing_required_value": "count_complete_deal"}.get(diagnostic.code)
            if reason:
                return form_error(reason, "matadors")
    return form_error("rejected")
