"""Manual Review producer ownership and atomic source/execution/head publication."""

import secrets
from dataclasses import dataclass, field, replace

from skatmind.automatic_historical_evidence import build_historical_capture_candidate
from skatmind.automatic_learning_contracts import (
    AUTOMATIC_LEARNING_MAX_OBJECT_BYTES,
    HistoricalReviewHeadV1,
)
from skatmind.automatic_learning_store import StoreConflictError
from skatmind.errors import SkatMindError


@dataclass(slots=True)
class HistoricalReviewOwner:
    source_id: str = field(default_factory=lambda: secrets.token_hex(32))
    origin: str | None = None
    head: object = None
    source: object = None
    pending: object = None
    notice: object = None
    views: dict = field(default_factory=dict)
    confirmation: object = None
    delivery_receipt: object = None
    correction: bool = False

    def new(self, origin):
        self.source_id = secrets.token_hex(32)
        self.origin = origin
        self.head = self.source = self.pending = self.notice = None
        self.correction = False


@dataclass(frozen=True, slots=True)
class HistoricalAttempt:
    owner: object
    archive_owner: object
    source_id: str
    head: object
    source: object
    origin: str
    draft: object


@dataclass(frozen=True, slots=True)
class PendingHistoricalSave:
    token: str
    attempt: HistoricalAttempt
    state: object
    execution: object
    candidate: object


def capture_attempt(app, state):
    owner = app.historical_reviews
    origin = "guided" if state.draft is not None else "imported"
    if owner.origin != origin:
        owner.new(origin)
    owner.pending = owner.notice = None
    return HistoricalAttempt(owner, app.saved_match_analyses, owner.source_id, owner.head,
                             owner.source, origin, state.draft)


def require_pending(app, pending):
    attempt, owner = pending.attempt, app.historical_reviews
    if (owner is not attempt.owner or app.saved_match_analyses is not attempt.archive_owner
            or owner.source_id != attempt.source_id or owner.head != attempt.head
            or owner.pending is not pending or app.review_state is not pending.state):
        raise StoreConflictError("The original manual Review attempt changed.")


def retain_manual_review(app, attempt, state, execution, native):
    source_revision = 0 if attempt.source is None else attempt.source.record.revision
    if attempt.source is not None and attempt.source.request != execution.request:
        source_revision += 1
    try:
        candidate = build_historical_capture_candidate(attempt.source_id, source_revision,
            execution, native, draft=attempt.draft)
        if any(obj.reference.size_bytes > AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
               for obj in candidate.objects):
            raise ValueError("Historical pending evidence exceeds its bound.")
    except (OSError, ValueError, SkatMindError):
        with app.lock:
            if app.review_state is state and app.historical_reviews is attempt.owner:
                attempt.owner.notice = (state, "unavailable", None)
        return
    pending = PendingHistoricalSave(secrets.token_hex(32), attempt, state, execution, candidate)
    with app.lock:
        if app.review_state is not state or app.historical_reviews is not attempt.owner:
            raise StoreConflictError("Historical publication was superseded.")
        attempt.owner.pending = pending
        require_pending(app, pending)
    save_pending_historical(app, pending.token)


def save_pending_historical(app, token):
    from .saved_match_analyses import archive_store
    with app.lock:
        pending = app.historical_reviews.pending
        if pending is None or not secrets.compare_digest(pending.token, token):
            raise StoreConflictError("Historical persistence attempt expired.")
        require_pending(app, pending)
    store = reservation = None
    status = "unsaved"
    candidate, attempt = pending.candidate, pending.attempt
    head = HistoricalReviewHeadV1(source=candidate.source.source_version.source,
        source_version_id=candidate.source.source_version.identity,
        evidence_id=candidate.evidence.identity)
    try:
        store = archive_store(app, initialize=True)
        before = store.snapshot().manifest
        if head.source in before.historical_retired:
            raise StoreConflictError("The original Review source was deleted.")
        current = next((row for row in before.historical_heads if row.source == head.source), None)
        if current != attempt.head:
            raise StoreConflictError("The saved Review head changed.")
        reservation = store.begin_candidate(candidate.objects)
        for obj in candidate.objects:
            if store.publish_object(obj, candidate=reservation) == "conflict":
                raise StoreConflictError("Historical staging conflicted.")
        requested = replace(before, revision=before.revision + 1,
            objects=before.objects + tuple(obj.entry for obj in candidate.objects
                                          if obj.entry not in before.objects),
            sources=before.sources + (() if candidate.source in before.sources
                                      else (candidate.source,)),
            evidence=before.evidence + (() if candidate.evidence in before.evidence else
                                        (candidate.evidence,)),
            historical_heads=tuple(sorted((*(row for row in before.historical_heads
                if row.source != head.source), head), key=lambda row: row.source.identity)))
        with app.lock:
            def guard():
                require_pending(app, pending)
                return True
            result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                                           candidate=reservation, commit_guard=guard)
            status = "saved" if result.status in ("saved", "unchanged") else "unsaved"
    except (OSError, ValueError, SkatMindError):
        if store is not None:
            try:
                authority = store.snapshot()
                if (head in authority.manifest.historical_heads
                        and head.evidence_id in authority.available_evidence_ids):
                    status = "saved"
            except (OSError, ValueError, SkatMindError):
                status = "unknown"
    finally:
        if store is not None and reservation is not None:
            try:
                store.release_candidate(reservation)
            except (OSError, ValueError):
                pass
    with app.lock:
        require_pending(app, pending)
        owner = attempt.owner
        owner.notice = (pending.state, status, candidate.evidence.identity)
        if status == "saved":
            from skatmind.automatic_historical_evidence import decode_historical_source
            owner.head = head
            owner.source = decode_historical_source(candidate.objects[0], candidate.source)
            owner.pending = None
    return status


@dataclass(frozen=True, slots=True)
class ManualReviewDelivery:
    token: str
    owner: object
    state: object
    notice: object
    pending: object
    archive_owner: object
    store: object
    resumed: object

    def validate(self, app):
        def require_original():
            if (app.historical_reviews is not self.owner or app.review_state is not self.state
                    or self.owner.notice is not self.notice
                    or self.owner.pending is not self.pending
                    or app.saved_match_analyses is not self.archive_owner):
                raise StoreConflictError("Original manual Review delivery changed.")
        with app.lock:
            require_original()
        if self.store is not None:
            current, receipt = self.store._snapshot_for_delivery(self.owner.delivery_receipt)
            if current != self.resumed or self.archive_owner.store is not self.store:
                raise StoreConflictError("Original saved Review authority changed.")
            with app.lock:
                require_original()
                self.owner.delivery_receipt = receipt


def capture_manual_delivery(app):
    from .saved_match_analyses import archive_store
    with app.lock:
        owner, state = app.historical_reviews, app.review_state
        notice, pending = owner.notice, owner.pending
        archive_owner = app.saved_match_analyses
    store = receipt = resumed = None
    if notice is not None and notice[0] is state and notice[1] == "saved":
        store = archive_store(app)
        if store is None:
            raise StoreConflictError("Saved Review archive disappeared.")
        resumed, receipt = store._snapshot_for_delivery(owner.delivery_receipt)
        if (owner.head not in resumed.manifest.historical_heads
                or notice[2] not in resumed.available_evidence_ids):
            raise StoreConflictError("Saved Review head changed.")
        owner.delivery_receipt = receipt
    with app.lock:
        value = next((value for value in owner.views.values()
            if value.state is state and value.notice is notice and value.pending is pending
            and value.archive_owner is archive_owner and value.resumed == resumed), None)
        if value is None:
            value = ManualReviewDelivery(secrets.token_hex(32), owner, state, notice, pending,
                                         archive_owner, store, resumed)
    value.validate(app)
    with app.lock:
        while len(owner.views) >= 32 and value.token not in owner.views:
            owner.views.pop(next(iter(owner.views)))
        owner.views[value.token] = value
    return value
