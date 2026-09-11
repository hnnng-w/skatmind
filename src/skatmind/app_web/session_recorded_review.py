from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import TYPE_CHECKING

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.errors import SkatMindValidationError

from .execution import execute_guided_frontend_review_v1
from .json_transfer import canonical_frontend_json_bytes_v1
from .managed_item_storage import validate_managed_direct_child_path_v1
from .workflow_state import StaleFrontendWorkflowRevisionError

if TYPE_CHECKING:
    from .context import AppWebContextV1
    from .session_frontend import GuidedSessionContextV1


class RecordedDecisionReviewConflictError(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason: str = "selection") -> None:
        super().__init__()
        self.reason = reason


@dataclass(frozen=True, slots=True)
class RecordedDecisionV1:
    checkpoint: session_api.SessionDecisionCheckpointV1
    observation: session_api.SessionDecisionObservationV1
    selection: str


@dataclass(frozen=True, slots=True)
class RecordedReviewProjectionV1:
    decisions: tuple[RecordedDecisionV1, ...]
    local_play_count: int
    missing_snapshot_count: int
    unavailable_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class RecordedReviewSourceV1:
    document: session_api.SessionPersistenceDocumentV1
    generation: int
    decision: RecordedDecisionV1
    attempt: object


def project_recorded_session_decisions_v1(
    context: GuidedSessionContextV1,
) -> RecordedReviewProjectionV1:
    """Read only; select variants within this exact accepted history, never backfill."""
    with context.lock:
        document = context.document
        state = document.state
        selected: dict[int, tuple[int, RecordedDecisionV1]] = {}
        unavailable = dict.fromkeys(("pending", "future", "diverged", "ended_without_play"), 0)
        for index, checkpoint in enumerate(document.decision_checkpoints):
            observation = session_api.observe_session_decision_checkpoint(
                state=state, checkpoint=checkpoint,
            ).value
            if observation.status != "observed":
                unavailable[observation.status] += 1
                continue
            revision = observation.observed_play_revision
            previous = selected.get(revision)
            if previous is not None and (
                previous[1].checkpoint.source_revision >= checkpoint.source_revision
            ):
                continue
            # The complete document binds the accepted Play and every stored variant.
            # A per-context secret also distinguishes reopen of the identical file.
            material = canonical_frontend_json_bytes_v1((
                context.generation, document.content_fingerprint, index,
                checkpoint.to_dict(), observation.to_dict(),
            ))
            selection = hmac.new(context.review_selection_key, material, hashlib.sha256).hexdigest()
            selected[revision] = (index, RecordedDecisionV1(checkpoint, observation, selection))
        local_plays = sum(
            record.command.kind == "record_play"
            and record.command.player_id == state.local_player_id
            for record in state.command_log
        )
        decisions = tuple(sorted(
            (value[1] for value in selected.values()),
            key=lambda value: value.checkpoint.decision_index,
        ))
        return RecordedReviewProjectionV1(
            decisions, local_plays, local_plays - len(decisions), tuple(unavailable.items()),
        )


def require_recorded_review_file_fresh_v1(context: GuidedSessionContextV1) -> None:
    """Strict read/fingerprint check under the Session lock, never the app lock."""
    with context.lock:
        try:
            validate_managed_direct_child_path_v1(
                context.category_root, context.path, expected_kind="file",
            )
            loaded = session_files.load_session_file(context.path).value.document
            fresh = loaded.content_fingerprint == context.document.content_fingerprint
        except (OSError, ValueError, SkatMindValidationError):
            fresh = False
        if not fresh:
            context.clear_execution()
            raise RecordedDecisionReviewConflictError("source_changed")


def _require_binding(app: AppWebContextV1, context: GuidedSessionContextV1) -> None:
    if app.managed_stateful.active_session is not context:
        raise RecordedDecisionReviewConflictError("context_changed")


def _require_source(context: GuidedSessionContextV1, source: RecordedReviewSourceV1) -> None:
    if (context.generation != source.generation
            or context.document != source.document):
        raise RecordedDecisionReviewConflictError("selection")
    if context.execution_attempt is not source.attempt:
        raise RecordedDecisionReviewConflictError("superseded")


def execute_recorded_session_decision_v1(
    app: AppWebContextV1, context: GuidedSessionContextV1, *, selection: str,
) -> None:
    """One exported frozen Request; atomic source/Result publication after unlocked execution."""
    with context.lock:
        with app.lock:
            _require_binding(app, context)
        decision = next((row for row in project_recorded_session_decisions_v1(context).decisions
                         if hmac.compare_digest(row.selection, selection)), None)
        if decision is None:
            raise RecordedDecisionReviewConflictError()
        require_recorded_review_file_fresh_v1(context)
        exported = session_api.export_session_checkpoint_review_request(
            state=context.state, checkpoint=decision.checkpoint,
        ).value
        if exported.status != "available" or exported.observation != decision.observation:
            raise RecordedDecisionReviewConflictError()
        with app.lock:
            _require_binding(app, context)
            attempt = context.begin_execution()
            source = RecordedReviewSourceV1(context.document, context.generation, decision, attempt)
    execution = execute_guided_frontend_review_v1(exported.request, options=ExecutionOptionsV1())
    with context.lock:
        _require_source(context, source)
        require_recorded_review_file_fresh_v1(context)
        # Session -> short app binding/publication lock. Activation releases the app
        # lock before clearing a previous Session; no filesystem/engine work is nested.
        with app.lock:
            _require_binding(app, context)
            _require_source(context, source)
            context.execution = execution
            context.recorded_review_source = source
