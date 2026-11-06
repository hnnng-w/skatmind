"""One bounded original Session attempt; retry only publishes already retained bytes."""

import secrets
from dataclasses import dataclass, replace

from skatmind.automatic_learning_contracts import AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
from skatmind.automatic_learning_store import StoreConflictError
from skatmind.automatic_session_evidence import build_session_capture_candidate
from skatmind.errors import SkatMindError
from skatmind.match_source_coordination import match_source_coordinator


@dataclass(frozen=True, slots=True)
class PendingSessionSave:
    token: str
    owner: object
    archive_owner: object
    source: object
    execution: object
    candidate: object
    coordinator: object
    epoch: int


def require_session_save(app, active, pending):
    from .session_recorded_review import (
        RecordedDecisionReviewConflictError,
        _require_binding,
        _require_source,
        require_recorded_review_file_fresh_v1,
    )
    _require_binding(app, active)
    _require_source(active, pending.source)
    if (pending.owner is not active or active.pending_evidence is not pending
            or app.saved_match_analyses is not pending.archive_owner or active.retired
            or pending.coordinator.generation != pending.epoch):
        raise RecordedDecisionReviewConflictError("superseded")
    require_recorded_review_file_fresh_v1(active)


def retain_published_session(app, active, source, execution, native, coordinator, epoch):
    """The caller supplies the attempted execution, never the selected display slot."""
    from .session_recorded_review import _require_binding, _require_source

    try:
        candidate = build_session_capture_candidate(source.document, source.decision.checkpoint,
            source.decision.observation, execution, native)
        if any(obj.reference.size_bytes > AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
               for obj in candidate.objects):
            raise ValueError("Session evidence exceeds pending bounds.")
    except (ValueError, OSError, SkatMindError):
        with active.lock, app.lock:
            _require_binding(app, active)
            _require_source(active, source)
            active.evidence_notice = (source, "unavailable", None)
        return
    pending = PendingSessionSave(secrets.token_hex(32), active, app.saved_match_analyses,
                                 source, execution, candidate, coordinator, epoch)
    with active.lock, app.lock:
        _require_binding(app, active)
        _require_source(active, source)
        active.pending_evidence = pending
        require_session_save(app, active, pending)
    save_pending_session(app, active, pending.token)


def save_pending_session(app, active, token):
    from .saved_match_analyses import archive_store
    from .session_recorded_review import RecordedDecisionReviewConflictError

    with active.lock, app.lock:
        pending = active.pending_evidence
        if pending is None or not secrets.compare_digest(token, pending.token):
            raise RecordedDecisionReviewConflictError("superseded")
        require_session_save(app, active, pending)
    store = reservation = None
    status = "unsaved"
    try:
        store = archive_store(app, initialize=True)
        before = store.snapshot().manifest
        candidate = pending.candidate
        reservation = store.begin_candidate(candidate.objects)
        for obj in candidate.objects:
            if store.publish_object(obj, candidate=reservation) == "conflict":
                raise StoreConflictError("Session evidence publication conflicted.")
        requested = replace(before, revision=before.revision + 1,
            objects=before.objects + tuple(obj.entry for obj in candidate.objects
                                          if obj.entry not in before.objects),
            sources=before.sources + (() if candidate.source in before.sources else
                                      (candidate.source,)),
            evidence=before.evidence + (() if candidate.evidence in before.evidence else
                                        (candidate.evidence,)))
        with active.lock, app.lock, pending.coordinator.lock:
            def guard():
                require_session_save(app, active, pending)
                return True
            result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                                           candidate=reservation, commit_guard=guard)
            status = "saved" if result.status in ("saved", "unchanged") else "unsaved"
    except RecordedDecisionReviewConflictError:
        raise
    except (OSError, ValueError, SkatMindError):
        if store is not None:
            try:
                if pending.candidate.evidence.identity in store.snapshot().available_evidence_ids:
                    status = "saved"
            except (OSError, ValueError, SkatMindError):
                status = "unknown"
    finally:
        if store is not None and reservation is not None:
            try:
                store.release_candidate(reservation)
            except (OSError, ValueError):
                pass
    with active.lock, app.lock:
        require_session_save(app, active, pending)
        active.evidence_notice = (pending.source, status, pending.candidate.evidence.identity)
        if status == "saved":
            active.pending_evidence = None
    return status


def session_source_epoch(active):
    coordinator = match_source_coordinator(active.category_root).watch_source(active.path.name)
    return coordinator, coordinator.generation


def session_delivery_guard(app, active):
    """Capture the original receipt and source, never the latest view from another tab."""
    from .session_recorded_review import (
        RecordedDecisionReviewConflictError,
        _require_binding,
        _require_source,
        require_recorded_review_file_fresh_v1,
    )
    with active.lock:
        notice, pending = active.evidence_notice, active.pending_evidence
        original_values = (active.execution, active.rollout_execution,
                           active.recorded_review_source, active.rollout_review_source)
        source = active.recorded_review_source or active.rollout_review_source
        if notice is not None:
            source = notice[0]
        if source is None:
            return None

    def guard():
        try:
            with active.lock, app.lock:
                _require_binding(app, active)
                if active.evidence_notice is not notice or active.pending_evidence is not pending:
                    raise RecordedDecisionReviewConflictError()
                if any(before is not after for before, after in zip(original_values,
                    (active.execution, active.rollout_execution, active.recorded_review_source,
                     active.rollout_review_source), strict=True)):
                    raise RecordedDecisionReviewConflictError()
                if notice is not None:
                    _require_source(active, source)
                elif active.document != source.document or active.generation != source.generation:
                    raise RecordedDecisionReviewConflictError()
                if (source.coordinator is not None
                        and source.coordinator.generation != source.source_epoch):
                    raise RecordedDecisionReviewConflictError()
                require_recorded_review_file_fresh_v1(active)
                if pending is not None:
                    require_session_save(app, active, pending)
            if notice is not None and notice[1] == "saved":
                from .saved_match_analyses import archive_store
                store = archive_store(app)
                if store is None or notice[2] not in store.snapshot().available_evidence_ids:
                    raise RecordedDecisionReviewConflictError()
        except RecordedDecisionReviewConflictError as error:
            raise StoreConflictError("Session evidence delivery changed.") from error
    return guard
