"""Exact-source private Card forms; Product save boundaries remain authoritative."""

from __future__ import annotations

import hashlib
import hmac
import json
import re

from skatmind.api.v1.session import files as session_files
from skatmind.errors import SkatMindValidationError
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

from .managed_item_storage import validate_managed_direct_child_path_v1
from .session_card_entry import (
    CardEntryError,
    prepare_session_card_candidate,
    project_session_card_task,
    validate_card_selection,
)
from .session_card_feedback import SessionCardFeedback, render_card_witness
from .session_frontend import _persist_session_mutation
from .workflow_state import StaleFrontendWorkflowRevisionError

CARD_ENTRY_ROUTES = ("/sessions/cards", "/sessions/play", "/matches/cards")
MATCH_CARD_OPERATIONS = (
    "set_perspective_hand", "set_original_skat", "set_discarded_cards", "append_plays",
)


class CardEntryConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason="stale"):
        super().__init__()
        self.reason = reason


def _token(key, material):
    data = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, b"compact_card_entry\0" + data, hashlib.sha256).hexdigest()


def session_card_binding(context, task):
    return _token(context.review_selection_key, (
        context.handle, context.generation, context.document.to_dict(),
        task.kind, task.destination, task.player_id,
    ))


def match_card_binding(context, operation):
    game = context.workspace.slots[context.selected_position - 1].observed_game
    return _token(context.card_entry_key, (
        context.handle, context.position_generation, context.capture.content_fingerprint,
        context.workspace.to_dict(), context.selected_position,
        None if game is None else game.game_id, operation,
    ))


def _require_binding(supplied, expected):
    if type(supplied) is not str or not re.fullmatch(r"[0-9a-f]{64}", supplied):
        raise CardEntryError("binding", "card_selection")
    if not hmac.compare_digest(supplied, expected):
        raise CardEntryConflict()


def _fresh(context, *, session):
    try:
        validate_managed_direct_child_path_v1(
            context.category_root, context.path, expected_kind="file")
        loaded = (session_files.load_session_file(context.path).value.document if session
                  else load_match_workspace_file_v1(context.path).document)
        fresh = (loaded == context.document if session else
                 loaded.workspace == context.workspace
                 and loaded.content_fingerprint == context.capture.content_fingerprint)
    except (OSError, ValueError, SkatMindValidationError):
        fresh = False
    if not fresh:
        raise CardEntryConflict("file_changed")


def _cards(values):
    raw = values.get("cards", ())
    return (raw,) if isinstance(raw, str) else raw


def dispatch_card_entry(app, route, values):
    """Lifecycle gate -> Product lock -> short active-identity check; no app-locked I/O."""
    session = route.startswith("/sessions/")
    managed = app.managed_stateful
    gate = managed.session_lifecycle_lock if session else managed.match_lifecycle_lock
    with gate:
        with app.lock:
            active = managed.active_session if session else managed.active_match
        if active is None:
            raise CardEntryConflict()
        with active.lock if session else active.capture.lock:
            with app.lock:
                if values.get("managed_handle") != active.handle:
                    raise CardEntryConflict()
            if session:
                return _session_entry(active, route, values)
            return _match_entry(active, values)


def _session_entry(active, route, values):
    active.require_attached()
    if set(values) - {"managed_handle", "card_selection", "cards"}:
        raise CardEntryError("fields", "cards")
    task = project_session_card_task(active.state)
    if task is None:
        raise CardEntryConflict()
    _require_binding(values.get("card_selection"), session_card_binding(active, task))
    if (route == "/sessions/play") != (task.kind == "record_play"):
        raise CardEntryConflict()
    _fresh(active, session=True)
    try:
        candidate = prepare_session_card_candidate(
            active.state, active.decision_checkpoints, _cards(values), task=task)
    except CardEntryError as error:
        if error.witness is not None:
            error.feedback = SessionCardFeedback(selection=values["card_selection"],
                                                route=route, witness=error.witness)
        raise
    try:
        result = _persist_session_mutation(
            active, state=candidate.state, checkpoints=candidate.checkpoints,
            result_status="applied", diagnostics=())
    except OSError as error:
        raise CardEntryConflict("save_failed") from error
    if result.status == "conflict":
        raise CardEntryConflict("file_changed")
    return "/sessions/current#session-recording"


def resolve_session_card_feedback(active, feedback, locale):
    """Caller holds the Session lock; no labels or witness links before source checks."""
    if active is None or active.retired:
        return None
    task = project_session_card_task(active.state)
    if task is None or (feedback.route == "/sessions/play") != (task.kind == "record_play"):
        return None
    try:
        _require_binding(feedback.selection, session_card_binding(active, task))
        _fresh(active, session=True)
    except (CardEntryError, CardEntryConflict):
        return None
    return render_card_witness(feedback.witness, active.state.players, locale)


def _match_entry(active, values):
    from .match_frontend import apply_unified_match_operation_v1

    operation = values.get("operation")
    if operation not in MATCH_CARD_OPERATIONS:
        raise CardEntryError("fields")
    allowed = {"managed_handle", "card_selection", "operation", "cards"}
    if operation != "append_plays":
        allowed.add("card_evidence_mode")
    if set(values) - allowed:
        raise CardEntryError("fields")
    _require_binding(values.get("card_selection"), match_card_binding(active, operation))
    _fresh(active, session=False)
    cards = _cards(values)
    if operation == "append_plays":
        validate_card_selection(cards, capacity=1)
    elif cards:
        validate_card_selection(cards, capacity=10 if operation == "set_perspective_hand" else 2)
    mode = values.get("card_evidence_mode")
    if operation != "append_plays":
        permitted = ("unknown", "exact", "known_empty") if operation == "set_discarded_cards" else (
            "unknown", "exact")
        if mode not in permitted:
            raise CardEntryError("mode", "card_evidence_mode")
        if mode == "exact" and len(cards) != (10 if operation == "set_perspective_hand" else 2):
            raise CardEntryError("exact_count")
    payload = {"operation": operation, "match_position": str(active.selected_position),
               "expected_revision": str(active.workspace.revision), "cards": cards}
    if operation != "append_plays":
        payload["card_evidence_mode"] = mode
    try:
        result = apply_unified_match_operation_v1(active, payload)
    except OSError as error:
        raise CardEntryConflict("save_failed") from error
    if result.http_status == 409:
        raise CardEntryConflict("file_changed")
    if result.http_status != 200:
        raise CardEntryError("ownership")
    return f"/matches/position/{active.selected_position}#match-recording"
