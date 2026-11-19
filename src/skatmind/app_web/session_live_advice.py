"""One explicitly enabled Session owner. Only native POST handlers reserve work."""

from __future__ import annotations

import hmac
from dataclasses import dataclass

import skatmind.api.v1.session as api
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.api.v1.schema_validation import _share_checked_resources
from skatmind.match_source_coordination import SavedSourceEpoch, match_source_coordinator
from skatmind.session_persistence import _build_session_persistence_file_bytes_v1

from .analysis_controls import EFFORTS
from .execution import GuidedFrontendExecutionV1, execute_guided_frontend_analysis_v1
from .forced_card_guidance import ForcedCardGuidance, forced_card_guidance
from .managed_item_storage import validate_managed_direct_child_path_v1
from .session_form_translation import build_session_position_options_from_form_v1
from .workflow_state import StaleFrontendWorkflowRevisionError

LIVE_ROUTES = ("/sessions/live-start", "/sessions/live-effort", "/sessions/live-stop")


@dataclass(frozen=True, slots=True, eq=False)
class LiveAttempt:
    document: api.SessionPersistenceDocumentV1
    generation: int
    effort: str
    feedback_attempt: object
    source: SavedSourceEpoch
    epoch: int


@dataclass(slots=True)
class LiveAssistance:
    effort: str | None = None
    control_revision: int = 0
    attempt: LiveAttempt | None = None
    outcome: GuidedFrontendExecutionV1 | ForcedCardGuidance | None = None
    unavailable: bool = False

    def invalidate(self):
        self.attempt = self.outcome = None
        self.unavailable = False

    def configure(self, effort):
        self.invalidate()
        self.control_revision += 1
        self.effort = effort


def game_identity(state):
    return next((r.command.game_id for r in reversed(state.command_log)
                 if r.command.kind == "set_game_metadata" and r.command.game_id is not None), None)


def control_binding(active, route):
    serial = active.live.control_revision if route in LIVE_ROUTES else ""
    material = (f"live:{route}:{active.generation}:"
                f"{active.document.content_fingerprint}:{serial}").encode()
    return hmac.digest(active.review_selection_key, material, "sha256").hex()


def configure_live(active, route, values):
    from .card_entry_http import _fresh

    token = values.pop("live_binding", "")
    if not token.isascii() or not hmac.compare_digest(token, control_binding(active, route)):
        raise StaleFrontendWorkflowRevisionError()
    enabled = active.live.effort is not None
    if (route == LIVE_ROUTES[0]) == enabled:
        raise StaleFrontendWorkflowRevisionError()
    if route == LIVE_ROUTES[1]:
        if set(values) != {"analysis_effort"} or values["analysis_effort"] not in EFFORTS:
            raise ValueError("Expected one ordinary analysis effort.")
        effort = values["analysis_effort"]
    else:
        if values:
            raise ValueError("Unexpected Live control fields.")
        effort = "quick" if route == LIVE_ROUTES[0] else None
    if effort is not None:
        _fresh(active, session=True)
    active.live.configure(effort)


def reserve_live_attempt(active):
    """Caller still owns the accepted mutation. Readiness cheaply excludes other turns."""
    effort = active.live.effort
    if (effort is None or active.state.phase != "play"
            or active.state.validation.position_export.status != "available"):
        return None
    try:
        source = match_source_coordinator(active.category_root).watch_source(active.path.name)
    except OSError:
        return None
    attempt = LiveAttempt(active.document, active.generation, effort,
                          active.operation_feedback.attempt, source, source.generation)
    active.live.invalidate()
    active.live.attempt = attempt
    return attempt


def after_live_edit(active, previous_generation):
    # A partial correction saved a prefix but rejected part of the requested suffix.
    if (active.generation != previous_generation and active.last_operation is not None
            and active.last_operation.status == "applied"):
        return reserve_live_attempt(active)
    return None


def _owned(app, active, attempt):
    return (app.managed_stateful.active_session is active and not active.retired
            and active.live.attempt is attempt and active.generation == attempt.generation
            and active.document is attempt.document and active.live.effort == attempt.effort
            and attempt.source.generation == attempt.epoch)


def _fresh_source(active, document):
    """Compare the full file to the admitted immutable document, never stat-only.

    A valid noncanonical encoding must pass the existing strict resume boundary.
    """
    from .card_entry_http import _fresh

    validate_managed_direct_child_path_v1(active.category_root, active.path, expected_kind="file")
    expected = _build_session_persistence_file_bytes_v1(document)
    with active.path.open("rb") as source:
        if source.read(len(expected) + 1) == expected:
            return
    _fresh(active, session=True)


def run_live_attempt(app, active, attempt):
    """Post-save only. Advice failure cannot undo or misreport an accepted save."""
    from .session_card_entry import project_session_card_task

    def current():
        return (_owned(app, active, attempt)
                and active.operation_feedback.attempt is attempt.feedback_attempt)

    try:
        with active.lock:
            with app.lock:
                if not current():
                    return
            _fresh_source(active, attempt.document)
        state = attempt.document.state
        task = project_session_card_task(state)
        if (task is None or task.kind != "record_play" or task.player_id != state.local_player_id
                or task.scope != "exact_legal_cards"):
            return
        options = build_session_position_options_from_form_v1({
            "settings_mode": "ordinary", "analysis_effort": attempt.effort,
            "random_seed": "0", "opponent_strategy": "basic"})
        exported = api.export_session_position_request(state, options).value
        if exported.status != "available":
            return
        with active.lock, app.lock:
            if not current():
                return
        if len(task.selectable_cards) == 1:
            outcome = forced_card_guidance(exported.request)
        elif len(task.selectable_cards) > 1:
            with _share_checked_resources():
                outcome = execute_guided_frontend_analysis_v1(exported.request,
                                                              options=ExecutionOptionsV1())
        else:
            outcome = None
    except Exception:
        # Optional advice, including its preparation, is downstream of the committed edit.
        outcome = None
    with active.lock:
        with app.lock:
            if not current():
                return
        try:
            _fresh_source(active, attempt.document)
        except Exception:
            return
        with app.lock, attempt.source.lock:
            if current():
                active.live.outcome = outcome
                active.live.unavailable = outcome is None


def live_delivery_guard(app, active, prior):
    """Capture alongside the rendered card area under its lock; check again at send."""
    attempt = active.live.attempt
    outcome, unavailable = active.live.outcome, active.live.unavailable
    if attempt is None or (outcome is None and not unavailable):
        return prior

    def guard():
        if prior is not None:
            prior()
        with active.lock:
            with app.lock:
                if (not _owned(app, active, attempt) or active.live.outcome is not outcome
                        or active.live.unavailable != unavailable):
                    raise ValueError("Live advice changed before delivery.")
            try:
                _fresh_source(active, attempt.document)
            except StaleFrontendWorkflowRevisionError as error:
                raise ValueError("Live source changed before delivery.") from error
            with app.lock, attempt.source.lock:
                if not _owned(app, active, attempt):
                    raise ValueError("Live source changed before delivery.")
    return guard
