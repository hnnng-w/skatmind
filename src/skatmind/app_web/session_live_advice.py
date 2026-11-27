"""One explicitly enabled Session owner. Only native POST handlers reserve work."""

from __future__ import annotations

import hmac
from contextlib import nullcontext
from dataclasses import dataclass

import skatmind.api.v1.session as api
from skatmind.accounting_store import accounting_publication_lock
from skatmind.api.v1.schema_validation import validate_input_document
from skatmind.errors import SkatMindError
from skatmind.live_whole_game import LiveGameOutcome, evaluate_live_game, live_rollout_view
from skatmind.match_source_coordination import SavedSourceEpoch, match_source_coordinator
from skatmind.session_persistence import _build_session_persistence_file_bytes_v1

from .analysis_controls import COUNTS, EFFORTS, TIMEOUTS
from .forced_card_guidance import ForcedCardGuidance, forced_card_guidance
from .frontend_profile_contracts import effort_preferences
from .live_effort_preferences import cent_scope, resolve_session_effort, submitted_effort
from .managed_item_storage import validate_managed_direct_child_path_v1
from .session_form_translation import build_session_position_options_from_form_v1
from .session_live_cent import CentAuthority, capture_cent_authority
from .whole_match_progress import file_identity
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
    authority: CentAuthority | None
    legal_card_count: int

    @property
    def accounting_lock(self):
        return self.authority.source.lock if self.authority is not None else nullcontext()


@dataclass(slots=True)
class LiveAssistance:
    effort: str | None = None
    control_revision: int = 0
    attempt: LiveAttempt | None = None
    outcome: LiveGameOutcome | ForcedCardGuidance | None = None
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


def control_binding(active, route, *, scope=None):
    serial = active.live.control_revision if route in LIVE_ROUTES else ""
    material = (f"live:{route}:{active.generation}:"
                f"{active.document.content_fingerprint}:{serial}:{scope}").encode()
    return hmac.digest(active.review_selection_key, material, "sha256").hex()


def configure_live(active, route, values, *, profile=None):
    from .card_entry_http import _fresh

    token = values.pop("live_binding", "")
    enabled = active.live.effort is not None
    if (route == LIVE_ROUTES[0]) == enabled:
        raise StaleFrontendWorkflowRevisionError()
    coordinator = match_source_coordinator(active.category_root)
    with accounting_publication_lock(), coordinator.lock:
        scope = None
        if route != LIVE_ROUTES[2]:
            try:
                _fresh(active, session=True)
                if file_identity(active.path) != active.saved_file_identity:
                    raise StaleFrontendWorkflowRevisionError()
                scope = cent_scope(active)
            except (ValueError, OSError, SkatMindError) as error:
                raise StaleFrontendWorkflowRevisionError() from error
        bound_scope = scope if route == LIVE_ROUTES[1] else None
        if not token.isascii() or not hmac.compare_digest(
                token, control_binding(active, route, scope=bound_scope)):
            raise StaleFrontendWorkflowRevisionError()
        selected = None
        block = False
        if route == LIVE_ROUTES[1]:
            selected, block = submitted_effort(values)
        elif values:
            raise ValueError("Unexpected Live control fields.")
        effort = None if route == LIVE_ROUTES[2] else resolve_session_effort(
            active, scope, effort_preferences(profile).live_effort, selected=selected, block=block)
        active.live.configure(effort)


def reserve_live_attempt(app, active):
    """Caller still owns the accepted mutation. Readiness cheaply excludes other turns."""
    from .session_card_entry import project_session_card_task

    effort = active.live.effort
    if (effort is None or active.state.phase != "play"
            or active.state.validation.position_export.status != "available"):
        return None
    try:
        source = match_source_coordinator(active.category_root).watch_source(active.path.name)
        epoch = source.generation
        task = project_session_card_task(active.state)
        if (task is None or task.kind != "record_play" or task.scope != "exact_legal_cards"
                or task.player_id != active.state.local_player_id):
            return None
        count = len(task.selectable_cards)
        authority = (capture_cent_authority(app.managed_home.root, active.document)
                     if count > 1 else None)
    except Exception:
        # Optional preparation is downstream of an already committed edit.
        active.live.invalidate()
        active.live.unavailable = True
        return None
    attempt = LiveAttempt(active.document, active.generation, effort,
                          active.operation_feedback.attempt, source, epoch, authority, count)
    active.live.invalidate()
    active.live.attempt = attempt
    return attempt


def after_live_edit(app, active, previous_generation):
    # A partial correction saved a prefix but rejected part of the requested suffix.
    if (active.generation != previous_generation and active.last_operation is not None
            and active.last_operation.status == "applied"):
        return reserve_live_attempt(app, active)
    return None


def _owned(app, active, attempt):
    return (app.managed_stateful.active_session is active and not active.retired
            and active.live.attempt is attempt and active.generation == attempt.generation
            and active.document is attempt.document and active.live.effort == attempt.effort
            and attempt.source.generation == attempt.epoch
            and (attempt.authority is None or attempt.authority.unchanged))


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


def evaluate_live_position(request, *, effort, cancelled, cent=None, supplied_matadors=None):
    data = request.to_dict()["document"]
    validate_input_document(data)
    index = EFFORTS.index(effort)
    return evaluate_live_game(live_rollout_view(data), worlds=COUNTS[index],
                              timeout_ms=TIMEOUTS[index], cancelled=cancelled, cent=cent,
                              supplied_matadors=supplied_matadors)


def _context_current(app, attempt):
    try:
        return attempt.authority is None or attempt.authority.current(
            app.managed_home.root, attempt.document)
    except (OSError, ValueError, TypeError):
        return False


def run_live_attempt(app, active, attempt):
    """Post-save only. Advice failure cannot undo or misreport an accepted save."""
    def current():
        return (_owned(app, active, attempt)
                and active.operation_feedback.attempt is attempt.feedback_attempt)

    try:
        with active.lock:
            with app.lock:
                if not current():
                    return
            _fresh_source(active, attempt.document)
            if not _context_current(app, attempt):
                return
        state = attempt.document.state
        options = build_session_position_options_from_form_v1({
            "settings_mode": "ordinary", "analysis_effort": attempt.effort,
            "random_seed": "0", "opponent_strategy": "basic"})
        exported = api.export_session_position_request(state, options).value
        if exported.status != "available":
            return
        with active.lock, app.lock:
            if not current():
                return
        if attempt.legal_card_count == 1:
            outcome = forced_card_guidance(exported.request)
        elif attempt.legal_card_count > 1:
            # Lock-free identity reads only signal cancellation; they never authorize
            # publication. No filesystem, replay or archive work inside the rollout loop.
            money = {}
            if attempt.authority.binding is not None:
                # The public Position export intentionally contains only inferred visible
                # matadors. The explicitly accepted declaration constrains private draws.
                supplied = next(r.command.declaration.matadors for r in reversed(state.command_log)
                                if r.command.kind == "set_declaration")
                money = {"cent": attempt.authority.binding.terms, "supplied_matadors": supplied}
            outcome = evaluate_live_position(exported.request, effort=attempt.effort,
                                             cancelled=lambda: not current(), **money)
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
            if not _context_current(app, attempt):
                return
        except Exception:
            return
        with app.lock, attempt.source.lock, attempt.accounting_lock:
            if current():
                active.live.outcome = outcome
                active.live.unavailable = outcome is None or (
                    isinstance(outcome, LiveGameOutcome) and outcome.status != "complete")


def expire_changed_cent_advice(app, active):
    """Drop stale advice before taking any page/language bindings. Caller owns Session."""
    attempt = active.live.attempt
    if (attempt and (active.live.outcome is not None or active.live.unavailable)
            and not _context_current(app, attempt)):
        active.live.invalidate()


def live_delivery_guard(app, active, prior):
    """Capture alongside the rendered card area under its lock; check again at send."""
    attempt = active.live.attempt
    outcome, unavailable = active.live.outcome, active.live.unavailable
    feedback = active.operation_feedback.attempt
    if attempt is None or (outcome is None and not unavailable):
        return prior

    def guard():
        if prior is not None:
            prior()
        with active.lock:
            with app.lock:
                if (not _owned(app, active, attempt) or active.live.outcome is not outcome
                        or active.live.unavailable != unavailable
                        or active.operation_feedback.attempt is not feedback):
                    raise ValueError("Live advice changed before delivery.")
            try:
                _fresh_source(active, attempt.document)
                if not _context_current(app, attempt):
                    raise ValueError("Live round changed before delivery.")
            except StaleFrontendWorkflowRevisionError as error:
                raise ValueError("Live source changed before delivery.") from error
            with app.lock, attempt.source.lock, attempt.accounting_lock:
                if not _owned(app, active, attempt):
                    raise ValueError("Live source changed before delivery.")
    return guard
