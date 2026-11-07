"""Bounded automatic ownership, exact controls and explicit maintenance adapters."""

import secrets
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from threading import RLock

from skatmind import automatic_learning_io as io
from skatmind.automatic_learning_contracts import ExclusionV1
from skatmind.automatic_learning_store import StoreConflictError

from .automatic_match_learning import AutomaticMatchLearningServiceV1
from .automatic_session_inventory import mixed_inventory_still_current as inventory_still_current
from .operation_feedback import FeedbackSource, PendingOperationFeedback


@dataclass(frozen=True, slots=True)
class AutomaticView:
    token: str
    binding: object

    @property
    def base(self):
        return "/learning/automatic/" + self.token


@dataclass(frozen=True, slots=True)
class AutomaticConfirmation:
    token: str
    view: AutomaticView
    kind: str
    source: object = None
    cleanup: object = None
    evidence: tuple = ()
    sources: tuple = ()
    source_release_blocked: bool = False


@dataclass(slots=True)
class AutomaticLearningController:
    lock: object = field(default_factory=RLock)
    service: object = None
    views: dict = field(default_factory=OrderedDict)
    confirmation: AutomaticConfirmation | None = None
    operation_feedback: PendingOperationFeedback = field(default_factory=PendingOperationFeedback)

    def bind(self, app):
        with self.lock:
            if self.service is None:
                self.service = (app.automatic_match_learning
                                or AutomaticMatchLearningServiceV1.open(app))
            if not self.service._owner():
                raise StoreConflictError("Automatic frontend owner changed.")
        return self

    def capture(self):
        binding = self.service.capture_delivery()
        with self.lock:
            for view in self.views.values():
                old = view.binding
                if (old == binding and old.installed is binding.installed
                        and old.attempt is binding.attempt):
                    return view
            view = AutomaticView(secrets.token_hex(32), binding)
            while len(self.views) >= 32:
                self.views.pop(next(iter(self.views)))
            self.views[view.token] = view
            return view

    def resolve(self, token):
        with self.lock:
            view = self.views.get(token)
        if view is None:
            raise StoreConflictError("Automatic view expired.")
        self.service.validate_delivery(view.binding)
        return view

    def feedback_source(self):
        service = self.service
        return FeedbackSource((self, service, service.attempt, service._installed), ())

    def update(self, view):
        self.service.validate_delivery(view.binding)
        with self.lock:
            attempt = self.operation_feedback.begin()
            self.confirmation = None
        result = self.service.update()
        if result.status in ("prepared", "rebuilt", "reused"):
            current = self.capture()
            if (current.binding.result.generation != result.generation
                    or current.binding.attempt is not result.attempt):
                raise StoreConflictError("Automatic update receipt was superseded.")
            with self.lock:
                self.operation_feedback.publish(attempt, self.feedback_source(),
                    ("automatic_" + result.status, ()))
            return result, current
        return result, None

    def preview_exclusion(self, view, source_index):
        self.service.validate_delivery(view.binding)
        rows = source_keys(view)
        if source_index >= len(rows):
            raise StoreConflictError("Automatic source is unavailable.")
        source = rows[source_index]
        manifest = view.binding.resumed.manifest
        kind = "include" if any(row.source == source and row.reason == "explicit"
                                 for row in manifest.exclusions) else "exclude"
        with self.lock:
            self.operation_feedback.begin()
            self.confirmation = AutomaticConfirmation(secrets.token_hex(32), view, kind, source)
            return self.confirmation

    def preview_cleanup(self, view, *, old_evidence=False, obsolete_sources=False):
        from skatmind.automatic_historical_evidence import decode_historical_source
        from skatmind.automatic_match_evidence import decode_match_source
        from skatmind.automatic_session_evidence import decode_session_source

        if old_evidence and obsolete_sources:
            raise ValueError("Source release and Report removal require separate consent.")
        self.service.validate_delivery(view.binding)
        if view.binding.resumed is None:
            raise StoreConflictError("Automatic storage has not been created.")
        manifest = view.binding.resumed.manifest
        current = {row.source_version_id for row in view.binding.inventory.rows
                   if row.status in ("selected", "explicit")}
        entries = tuple(row for row in manifest.evidence
                         if old_evidence and row.source_version_id not in current)
        release_blocked = obsolete_sources and any(row.status not in ("selected", "explicit")
                                                   for row in view.binding.inventory.rows)
        releases = (() if not obsolete_sources or release_blocked else
                    _releasable_sources(view))
        # Capture typed captions/effects BEFORE preview. All reader pins end here.
        captions = []
        available = view.binding.resumed.available_evidence_ids
        refs = (tuple(row.envelope for row in entries if row.identity in available)
                + tuple(row.object_ref for row in releases))
        with self.service.store.pin_objects(refs, expected_manifest=manifest.fingerprint):
            for entry in entries:
                value = (self.service.store.read_evidence(entry.identity)
                         if entry.identity in available else None)
                captions.append((entry, value))
            source_captions = tuple((record, decode_historical_source(
                self.service.store.read_object(record.object_ref), record)
                if record.source_version.source.family == "historical_review"
                else decode_session_source(
                self.service.store.read_object(record.object_ref), record)
                if record.source_version.source.family == "session" else decode_match_source(
                    self.service.store.read_object(record.object_ref), record).snapshot)
                for record in releases)
        self.service.validate_delivery(view.binding)
        preview = self.service.store.preview_cleanup(expected_manifest=manifest.fingerprint,
            remove_evidence_ids=tuple(row.identity for row in entries),
            release_source_version_ids=tuple(row.source_version.identity for row in releases))
        with self.lock:
            self.operation_feedback.begin()
            self.confirmation = AutomaticConfirmation(secrets.token_hex(32), view,
                "obsolete_sources" if obsolete_sources else
                "old_evidence" if old_evidence else "cleanup", cleanup=preview,
                evidence=tuple(captions), sources=source_captions,
                source_release_blocked=release_blocked)
            return self.confirmation

    def require_confirmation(self, token):
        with self.lock:
            value = self.confirmation
        if value is None or value.token != token:
            raise StoreConflictError("Automatic confirmation expired.")
        self.service.validate_delivery(value.view.binding)
        if value.cleanup is not None:
            store, preview = self.service.store, value.cleanup
            # Read-only checks: never pin, consume, refresh CAS or regenerate consent.
            with store._guard():
                if (store._coordinator.epoch != preview.epoch
                        or store._manifest().fingerprint != preview.expected_manifest
                        or store._inventory_fingerprint(io.scan_files(store.root))
                        != preview.inventory_fingerprint):
                    raise StoreConflictError("Cleanup preview is stale; preview again.")
        return value

    def confirm(self, token):
        value = self.require_confirmation(token)
        service, store = self.service, self.service.store
        with self.lock:
            if self.confirmation is not value:
                raise StoreConflictError("Automatic confirmation changed.")
            self.confirmation = None  # One-use consent even on partial failure.
            attempt = self.operation_feedback.begin()
        before = value.view.binding.resumed.manifest
        binding = value.view.binding
        def guard():
            return (service._owner(binding.attempt) and service.attempt is binding.attempt
                    and service._installed is binding.installed
                    and service.coordinator.generation == binding.epoch
                    and inventory_still_current(service.home, binding.inventory))
        try:
            with service.app.lock, service.coordinator.lock:
                service.validate_delivery(value.view.binding)
                if value.cleanup is not None:
                    result = store.commit_cleanup(value.cleanup, commit_guard=guard)
                else:
                    exclusions = tuple(row for row in before.exclusions
                                       if row.source != value.source)
                    if value.kind == "exclude":
                        exclusions += (ExclusionV1(source=value.source, reason="explicit"),)
                    requested = replace(before, revision=before.revision + 1,
                                        exclusions=exclusions)
                    result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                        commit_guard=guard)
            if result.status == "conflict":
                if (value.cleanup is not None and value.cleanup.manifest != before
                        and store.snapshot().manifest == value.cleanup.manifest):
                    raise OSError("Cleanup references committed before a later conflict.")
                raise StoreConflictError("Automatic maintenance conflicted.")
            message = "automatic_maintained"
        except OSError:
            # Reference-first cleanup can commit before an unlink/sync fails.
            authority = store.snapshot().manifest
            if value.cleanup is None or authority != value.cleanup.manifest:
                raise
            message = "automatic_partial_cleanup"
        authority = store.snapshot().manifest
        if (service._installed is not None
                and service._installed.reference not in authority.generations):
            service._installed = None
        current = self.capture()
        with self.lock:
            self.operation_feedback.publish(attempt, self.feedback_source(), (message, ()))
        return current


def _releasable_sources(view):
    """Conservative eligibility only; S1 owns graph retirement and physical cleanup.

    The caller requires a complete, valid, unambiguous live inventory. Explicitly
    excluded live versions still count as current. Retained evidence and every
    non-retirable dependency edge protect their original source records/objects.
    """
    manifest = view.binding.resumed.manifest
    live = {row.source_version_id for row in view.binding.inventory.rows}
    retained = {row.source_version_id for row in manifest.evidence}
    dependencies = {dependency for entry in manifest.objects
                    if entry.reference not in manifest.generations
                    for dependency in entry.dependencies}
    bound_sources = {entity.source for row in manifest.bindings
                     for entity in (row.subject, row.target) if entity is not None}
    available = {row.reference for row in view.binding.resumed.objects
                 if row.consumption_status == "available"}
    return tuple(row for row in manifest.sources
        if row.source_version.source.family in ("match", "session", "historical_review")
        and row.source_version.identity not in live | retained
        and row.object_ref not in dependencies and row.source_version.source not in bound_sources
        and row.object_ref in available)


def source_keys(view):
    """One verified logical identity, including duplicate-owner/excluded diagnostics."""
    keys = {row.source for row in view.binding.inventory.rows if row.source is not None}
    if view.binding.resumed is not None:
        keys.update(row.source for row in view.binding.resumed.manifest.exclusions
                     if row.source.family in ("match", "session", "historical_review"))
    if view.binding.result.generation is not None:
        keys.update(row.source for row in view.binding.result.generation.recipe.exclusions)
    return tuple(sorted(keys, key=lambda row: row.identity))


def automatic_controller(app):
    return app.automatic_learning_ui.bind(app)
