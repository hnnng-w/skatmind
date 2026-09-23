"""Explicit saved-Match capture followed by the existing independent Corpus import."""

from __future__ import annotations

import hashlib
import hmac
import re
from contextlib import nullcontext

from skatmind.errors import SkatMindError
from skatmind.match_workspace_persistence import (
    _build_match_workspace_file_bytes_v1,
    load_match_workspace_file_v1,
)

from .learning_frontend import import_workspace_bytes_into_unified_learning_v1
from .learning_outcome_navigation import LearningEntryOutcome
from .managed_item_discovery import discover_managed_items_v1
from .operation_feedback import feedback_source
from .recording_deletion import _digest
from .workflow_state import StaleFrontendWorkflowRevisionError

LEARNING_ADD_ROUTE = "/learning/add-recorded-match"
LEARNING_REFRESH_ROUTE = "/learning/recorded-matches/refresh"
LEARNING_ENTRY_LOCATION = "/learning/current#learning-recorded-matches"
LEARNING_ENTRY_BODY_LIMIT = 8_192
LEARNING_ENTRY_FIELDS = frozenset((
    "managed_handle", "source_handle", "source_generation", "expected_catalog_revision",
    "learning_selection", "same_revision_resolution",
))


class LearningEntryConflict(StaleFrontendWorkflowRevisionError):
    """The exact collection or discovered saved source is no longer available."""


def learning_selection_v1(target, discovery, generation):
    """Caller holds the Corpus lock; no paths/fingerprints leave this keyed binding."""
    store = target.corpus.store
    if store is None or discovery is None:
        raise LearningEntryConflict()
    material = (f"learning-direct-entry-v1:{id(discovery)}:{generation}:"
                f"{target.corpus.generation}:{store.document.catalog.revision}:"
                f"{store.document.content_fingerprint}").encode("ascii")
    return hmac.new(target.entry_key, material, hashlib.sha256).hexdigest()


def _require_target(app, target, discovery, values, *, captured=False):
    # Product -> short app snapshot. Never acquire a Product lock under the app lock.
    with app.lock:
        managed = app.managed_stateful
        if (managed.active_learning is not target or (not captured and (
                managed.discoveries.get("matches") is not discovery
                or managed.generations["matches"] != int(values["source_generation"])))):
            raise LearningEntryConflict()
    expected = learning_selection_v1(target, discovery, int(values["source_generation"]))
    if (target.handle != values["managed_handle"]
            or target.corpus.store.document.catalog.revision != int(
                values["expected_catalog_revision"])
            or not hmac.compare_digest(expected, values["learning_selection"])):
        raise LearningEntryConflict()


def capture_recorded_match_v1(app, discovery, values):
    """No activation, reload, Report/recovery access or publication into a recording.

    The lifecycle gate serializes capture with #235 unlink. Once these immutable
    bytes are returned, source editing/deletion does not revoke the independent copy.
    """
    managed = app.managed_stateful
    with managed.match_lifecycle_lock:
        with app.lock:
            if managed.discoveries.get("matches") is not discovery:
                raise LearningEntryConflict()
            try:
                entry = managed.resolve("matches", handle=values["source_handle"],
                                        generation=int(values["source_generation"]))
            except ValueError as error:
                raise LearningEntryConflict() from error
            if entry.summary.status != "available":
                raise LearningEntryConflict()
            root = managed.root("matches")
            active = managed.active_match
            if active is not None and active.path != entry.path:
                active = None
        with nullcontext() if active is None else active.capture.lock:
            try:
                if active is not None:
                    active.require_attached()
                before = _digest(root, entry.path)
                document = load_match_workspace_file_v1(entry.path).document
                workspace = document.workspace
                identity = workspace.match_definition.match_id
                # Reuse bounded strict classification without publishing a new discovery
                # generation or invalidating the submitted/native-language form.
                fresh = discover_managed_items_v1(root, family="matches", generation=1)
                current = fresh.resolve(values["source_handle"])
                if (current is None or current.summary.status != "available"
                        or current.summary.semantic_product_id != identity
                        or identity != entry.summary.semantic_product_id
                        or _digest(root, entry.path) != before
                        or (active is not None and (
                            active.workspace.match_definition.match_id != identity
                            or active.capture.content_fingerprint
                            != document.content_fingerprint))):
                    raise LearningEntryConflict()
                content = _build_match_workspace_file_bytes_v1(document)
            except (OSError, ValueError, SkatMindError) as error:
                raise LearningEntryConflict() from error
            with app.lock:
                if (managed.discoveries.get("matches") is not discovery
                        or managed.generations["matches"] != int(values["source_generation"])):
                    raise LearningEntryConflict()
            return content, document


def add_recorded_match_v1(app, target, values):
    if set(values) != LEARNING_ENTRY_FIELDS:
        raise ValueError("Use exactly the saved Match selection fields.")
    if (any(not re.fullmatch(r"[0-9a-f]{64}", values[name]) for name in (
            "managed_handle", "source_handle", "learning_selection"))
            or not re.fullmatch(r"[1-9][0-9]{0,15}", values["source_generation"])
            or not re.fullmatch(r"0|[1-9][0-9]{0,15}", values["expected_catalog_revision"])
            or values["same_revision_resolution"] not in {"reject", "retain"}):
        raise ValueError("Choose a saved Match and a supported conflict resolution.")
    with app.lock:
        discovery = app.managed_stateful.discoveries.get("matches")
    with target.corpus.lock:
        _require_target(app, target, discovery, values)
    content, document = capture_recorded_match_v1(app, discovery, values)
    identity = document.workspace.match_definition.match_id
    # Source locks are released before acquiring the target lifecycle/Product locks.
    # Activation uses the same gate; a stale target cannot receive a Catalog write.
    with app.managed_stateful.learning_lifecycle_lock, target.corpus.lock:
        _require_target(app, target, discovery, values, captured=True)
        result = import_workspace_bytes_into_unified_learning_v1(
            target, content, selection_mode="keep_current",
            same_revision_resolution=values["same_revision_resolution"],
            expected_catalog_revision=int(values["expected_catalog_revision"]),
        )
        store = target.corpus.store
        matching = {snapshot.match_snapshot_id for snapshot in store.match_snapshots
                    if snapshot.source_content_fingerprint == document.content_fingerprint}
        selected = any(selection.match_snapshot_id in matching
                       for selection in store.document.catalog.current_matches)
        target.entry_outcome = LearningEntryOutcome(
            result, identity, document.workspace.revision, selected,
            next(iter(matching), None), feedback_source(target))
        return result
