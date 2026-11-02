"""Managed producer retention and one exact, bounded, save-only retry per owner."""

import secrets
from dataclasses import dataclass, replace

from skatmind.automatic_learning_contracts import AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
from skatmind.automatic_learning_store import StoreConflictError
from skatmind.automatic_match_evidence import ORDINARY_METHODS, build_match_capture_candidate
from skatmind.errors import SkatMindError
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1


@dataclass(frozen=True, slots=True)
class PendingMatchSave:
    token: str
    owner: object
    archive_owner: object
    attempt: object
    document: object
    generation: int
    selection: tuple
    report: object
    candidate: object


@dataclass(frozen=True, slots=True)
class PendingMatchRolloutSave(PendingMatchSave):
    notice: tuple | None
    display_report: object


def _selection(active):
    return (active.selected_position, active.position_generation,
            active.selected_review_decision, active.review_decision_generation,
            active.review_selection_pending)


def require_pending_owner(context, active, pending):
    if active.pending_evidence is not pending:
        raise RecordingOpenConflict()
    require_capture_owner(context, active, pending)


def require_capture_owner(context, active, pending):
    # Caller holds Match then app locks. This checks the active identity itself,
    # not eventual invalidation of the old owner's live Report store.
    if (context.managed_stateful.active_match is not active or active.retired
            or context.saved_match_analyses is not pending.archive_owner
            or pending.owner is not active
            or active.rollout_attempt is not pending.attempt
            or active.capture.report_store.generation != pending.generation
            or active.capture.content_fingerprint != pending.document.content_fingerprint
            or active.workspace != pending.document.workspace
            or _selection(active) != pending.selection):
        raise RecordingOpenConflict()
    if type(pending) is PendingMatchRolloutSave and pending.notice is not None:
        if (active.rollout_notice is not pending.notice
                or pending.notice[0] is not pending.report
                or pending.notice[1] != pending.generation):
            raise RecordingOpenConflict()
    elif active.capture.report_store.get(pending.report.report_id) is not pending.report:
        raise RecordingOpenConflict()
    if type(pending) is PendingMatchRolloutSave and active.capture.report_store.get(
            pending.display_report.report_id) is not pending.display_report:
        raise RecordingOpenConflict()
    require_recording_fresh_v1(active, "matches")


def capture_original_document(context, active):
    with active.capture.lock:
        with context.lock:
            if context.managed_stateful.active_match is not active:
                raise RecordingOpenConflict()
            require_recording_fresh_v1(active, "matches")
            document = load_match_workspace_file_v1(active.path).document
            if document.workspace != active.workspace:
                raise RecordingOpenConflict()
            return document


def retain_published_match(context, active, document, attempt, workspace, report,
                           invocation, execution, *, source_guard):
    if report.value.options.recommendation_method not in ORDINARY_METHODS:
        return
    _retain_published(context, active, document, attempt, workspace, report, invocation,
        execution, source_guard=source_guard, builder=build_match_capture_candidate)


def retain_published_rollout(context, active, document, attempt, workspace, report,
                             invocation, execution, *, source_guard, display_report):
    from skatmind.automatic_match_rollout_evidence import build_match_rollout_capture_candidate

    _retain_published(context, active, document, attempt, workspace, report, invocation,
        execution, source_guard=source_guard, builder=build_match_rollout_capture_candidate,
        display_report=display_report)


def _retain_published(context, active, document, attempt, workspace, report, invocation,
                      execution, *, source_guard, builder, display_report=None):
    if workspace != document.workspace:
        raise RecordingOpenConflict()
    # Pure staging happens unlocked. Nothing is durable until the guarded manifest
    # commit below. A newer attempt cannot be cleared by this abandoned work.
    try:
        candidate = builder(document, report, invocation, execution)
        if any(obj.reference.size_bytes > AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
               for obj in candidate.objects):
            raise ValueError("Evidence exceeds the bounded pending-object limit.")
    except (OSError, ValueError, SkatMindError):
        with active.capture.lock:
            with context.lock:
                if (context.managed_stateful.active_match is active
                        and active.rollout_attempt is attempt and source_guard()):
                    if display_report is not None:
                        binding = PendingMatchRolloutSave(
                            secrets.token_hex(32), active, context.saved_match_analyses,
                            attempt, document, active.capture.report_store.generation,
                            _selection(active), report, None, active.rollout_notice, display_report)
                        require_capture_owner(context, active, binding)
                        active.rollout_evidence_binding = binding
                    active.evidence_notice = (report.report_id, "unavailable", None)
        return
    with active.capture.lock:
        with context.lock:
            if (context.managed_stateful.active_match is not active
                    or active.rollout_attempt is not attempt
                    or active.capture.content_fingerprint != document.content_fingerprint
                    or display_report is None
                    and active.capture.report_store.get(report.report_id) is not report
                    or not source_guard()):
                raise RecordingOpenConflict()
            args = (secrets.token_hex(32), active, context.saved_match_analyses, attempt, document,
                    active.capture.report_store.generation, _selection(active), report, candidate)
            pending = (PendingMatchSave(*args) if display_report is None else
                       PendingMatchRolloutSave(*args, active.rollout_notice, display_report))
            active.pending_evidence = pending
            if display_report is not None:
                active.rollout_evidence_binding = pending
            require_pending_owner(context, active, pending)
    save_pending_match(context, active, pending.token)


def save_pending_match(context, active, token):
    """One persistence attempt, with no evaluator or source rebinding."""
    with active.capture.lock:
        with context.lock:
            pending = active.pending_evidence
            if pending is None or not secrets.compare_digest(pending.token, token):
                raise RecordingOpenConflict()
            require_pending_owner(context, active, pending)
    store = reservation = None
    status = "unsaved"
    try:
        from .saved_match_analyses import archive_store

        store = archive_store(context, initialize=True)
        before = store.snapshot().manifest
        value = pending.candidate
        reservation = store.begin_candidate(value.objects)
        for obj in value.objects:
            if store.publish_object(obj, candidate=reservation) == "conflict":
                raise StoreConflictError("Evidence staging is busy.")
        requested = replace(before, revision=before.revision + 1,
            objects=before.objects + tuple(obj.entry for obj in value.objects
                                          if obj.entry not in before.objects),
            sources=before.sources + (() if value.source in before.sources else (value.source,)),
            evidence=before.evidence + (() if value.evidence in before.evidence
                                       else (value.evidence,)))
        with active.capture.lock:
            with context.lock:
                require_pending_owner(context, active, pending)
                def guard():
                    require_pending_owner(context, active, pending)
                    return True
                result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                    candidate=reservation, commit_guard=guard)
                status = "saved" if result.status in ("saved", "unchanged") else "unsaved"
    except RecordingOpenConflict:
        raise
    except (OSError, ValueError, SkatMindError):
        # os.replace is authoritative even when fsync/return subsequently fails.
        if store is not None:
            try:
                current = store.snapshot()
                if pending.candidate.evidence.identity in current.available_evidence_ids:
                    status = "saved"
            except (OSError, ValueError, SkatMindError):
                status = "unknown"
    finally:
        if store is not None and reservation is not None:
            try:
                store.release_candidate(reservation)
            except (OSError, ValueError):
                pass  # Never release a newer candidate or remove committed objects.
    with active.capture.lock:
        with context.lock:
            require_pending_owner(context, active, pending)
            active.evidence_notice = (
                pending.report.report_id, status, pending.candidate.evidence.identity)
            if status == "saved":
                active.pending_evidence = None
    return status
