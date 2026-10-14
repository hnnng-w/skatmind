"""Captured debrief scopes and explicit source incorporation; no evaluator or recording writes."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass, field, replace

from skatmind.corpus_web.contracts import LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES
from skatmind.errors import SkatMindError
from skatmind.learning_corpus_current_snapshots import (
    resolve_learning_corpus_current_match_snapshots_v1,
)
from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
from skatmind.match_analysis_contracts import MATCH_ANALYSIS_REPORT_STORE_LIMIT
from skatmind.match_debrief import MatchDebriefEvidenceV1, completed_rollout
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1

from .match_frontend import get_unified_match_report_v1
from .recorded_review_opening import require_recording_fresh_v1

DEBRIEF_POST_ROUTES = ("/learning/debrief/include", "/learning/debrief/remove")


class DebriefUnavailable(ValueError):
    def __init__(self, reason="expired"):
        self.reason = reason
        super().__init__(reason)


@dataclass(slots=True)
class DebriefSourceStoreV1:
    """Collection-owned copies, with the existing 2,048-source lifetime bound."""

    sources: tuple[MatchDebriefEvidenceV1, ...] = ()
    revision: int = 0
    handles: tuple[tuple[str, str], ...] = ()

    def add(self, source, *, source_handle=None):
        if type(source) is not MatchDebriefEvidenceV1:
            raise ValueError("An exact debrief evidence value is required.")
        source.__post_init__()
        if source.binding_id in {item.binding_id for item in self.sources}:
            return "unchanged"
        if len(self.sources) >= LEARNING_CORPUS_WEB_MAX_STRATEGY_TEACHER_SOURCES:
            raise ValueError("Debrief source limit reached.")
        self.sources = (*self.sources, source)
        if source_handle is not None:
            self.handles = (*self.handles, (source.binding_id, source_handle))
        self.revision += 1
        return "applied"

    def remove(self, binding_id):
        retained = tuple(item for item in self.sources if item.binding_id != binding_id)
        if retained == self.sources:
            return "unchanged"
        self.sources = retained
        self.handles = tuple(item for item in self.handles if item[0] != binding_id)
        self.revision += 1
        return "applied"


@dataclass(frozen=True, slots=True)
class DebriefScopeV1:
    scope_id: str
    snapshots: tuple
    sources: tuple[MatchDebriefEvidenceV1, ...]
    owner: object = field(default=None, repr=False)
    lineage: tuple = ()
    tactical: object = field(default=None, repr=False)
    coaching: object = field(default=None, repr=False)
    source_handles: tuple[tuple[str, str], ...] = ()

    @property
    def players(self):
        return tuple(dict.fromkeys(player.player_id for snapshot in self.snapshots
                     for player in snapshot.workspace.match_definition.participants))

    def player(self, selector):
        if selector == "all":
            return None
        if selector not in {str(index) for index in range(len(self.players))}:
            raise DebriefUnavailable()
        return self.players[int(selector)]


def _lineage(target):
    corpus = target.corpus
    return (id(corpus.store), corpus.store.document.content_fingerprint, corpus.generation,
            corpus.strategy_source_store.revision, target.debrief_sources.revision,
            id(corpus.tactical_prepared_artifacts), id(corpus.tactical_coaching_prepared_artifacts))


def _retain(app, scope):
    # Caller owns any Product lock before this short app-lock publication.
    with app.lock:
        scopes = app.managed_stateful.debrief_scopes
        existing = next((old for old in scopes.values() if old.owner is scope.owner
                         and old.lineage == scope.lineage), None)
        if existing is not None:
            return existing
        while len(scopes) >= MATCH_ANALYSIS_REPORT_STORE_LIMIT:
            scopes.pop(next(iter(scopes)))
        scopes[scope.scope_id] = scope
    return scope


def resolve_scope(app, scope_id):
    with app.lock:
        scope = app.managed_stateful.debrief_scopes.get(scope_id)
    if scope is None:
        raise DebriefUnavailable()
    if scope.owner is not None:
        with scope.owner.corpus.lock:
            with app.lock:
                target = app.managed_stateful.active_learning
            if target is not scope.owner or _lineage(target) != scope.lineage:
                raise DebriefUnavailable("changed")
    return scope


def _capture(app, report_id, source_handle=None):
    with app.managed_stateful.match_lifecycle_lock:
        with app.lock:
            source = app.managed_stateful.active_match
        if source is None or source_handle is not None and source.handle != source_handle:
            raise DebriefUnavailable()
        with source.capture.lock:
            source.require_attached()
            try:
                require_recording_fresh_v1(source, "matches")
            except (ValueError, RuntimeError, OSError, SkatMindError) as error:
                raise DebriefUnavailable("recording_changed") from error
            status, report = get_unified_match_report_v1(source, report_id)
            if status != "found" or report is None:
                raise DebriefUnavailable()
            if not completed_rollout(report):
                raise DebriefUnavailable("incomplete")
            snapshot = build_learning_corpus_match_snapshot_v1(
                build_match_workspace_persistence_document_v1(source.workspace))
            evidence = MatchDebriefEvidenceV1(report, snapshot, snapshot)
            stamp = (id(source), source.handle, source.capture.report_store.generation,
                     source.capture.content_fingerprint)
    return evidence, stamp


def capture_direct_scope(app, report_id):
    evidence, stamp = _capture(app, report_id)
    return _retain(app, DebriefScopeV1(secrets.token_hex(32), (evidence.snapshot,), (evidence,),
        lineage=(stamp, report_id), source_handles=((evidence.binding_id, stamp[1]),)))


def collection_scope(app, target):
    with target.corpus.lock:
        snapshots = resolve_learning_corpus_current_match_snapshots_v1(target.corpus.store)
        lineage = _lineage(target)
        tactical = target.corpus.tactical_prepared_artifacts
        coaching = target.corpus.tactical_coaching_prepared_artifacts
        with app.lock:
            if app.managed_stateful.active_learning is not target:
                raise DebriefUnavailable("changed")
        return _retain(app, DebriefScopeV1(secrets.token_hex(32), snapshots,
            target.debrief_sources.sources, target, lineage,
            None if tactical is None else tactical.tactical_motif_collection,
            None if coaching is None else coaching.tactical_cross_game_coaching_report,
            target.debrief_sources.handles))


def _selection(target, stamp, report_id):
    material = repr((_lineage(target), stamp, report_id)).encode()
    return hmac.new(target.entry_key, material, hashlib.sha256).hexdigest()


def available_reports(app, target):
    """Only the active bounded report store; no discovery, report files or evaluation."""
    with app.lock:
        active = app.managed_stateful.active_match
    if active is None:
        return ()
    with active.capture.lock:
        reports = active.capture.report_store.list()
    offers = []
    for report in reports:
        if (report.report_kind != "decision_analysis"
                or report.value.options.recommendation_method != "whole_game_rollout"):
            continue
        try:
            evidence, stamp = _capture(app, report.report_id, active.handle)
        except (ValueError, RuntimeError, OSError, SkatMindError):
            offers.append((None, report, "expired" if completed_rollout(report) else "incomplete",
                           active.handle, ""))
            continue
        with target.corpus.lock:
            snapshots = resolve_learning_corpus_current_match_snapshots_v1(target.corpus.store)
            snapshot = next((item for item in snapshots if item.match_id == report.match_id), None)
            proof = _selection(target, stamp, report.report_id)
            reason = "missing_snapshot" if snapshot is None else None
            if snapshot is not None:
                try:
                    evidence = replace(evidence, snapshot=snapshot)
                except ValueError:
                    reason = "snapshot_mismatch"
            if reason is None and evidence.binding_id in {
                    item.binding_id for item in target.debrief_sources.sources}:
                continue
        offers.append((evidence, report, reason, active.handle, proof))
    return tuple(offers)


def incorporate_report(app, values):
    if set(values) != {"managed_handle", "source_handle", "report_id", "selection"}:
        raise ValueError("Use the exact captured debrief incorporation fields.")
    with app.lock:
        target = app.managed_stateful.active_learning
    if target is None or values["managed_handle"] != target.handle:
        raise DebriefUnavailable("changed")
    # Capture under Match locks, then release them before entering any Corpus lock.
    evidence, stamp = _capture(app, values["report_id"], values["source_handle"])
    with target.corpus.lock:
        lineage = _lineage(target)
        if not hmac.compare_digest(_selection(target, stamp, values["report_id"]),
                                   values["selection"]):
            raise DebriefUnavailable("changed")
        snapshots = resolve_learning_corpus_current_match_snapshots_v1(target.corpus.store)
        snapshot = next((item for item in snapshots
                         if item.match_id == evidence.report.match_id), None)
    if snapshot is None:
        raise DebriefUnavailable("missing_snapshot")
    try:
        evidence = replace(evidence, snapshot=snapshot)
    except ValueError as error:
        raise DebriefUnavailable("snapshot_mismatch") from error
    # Source copy is now independent. Target activation and Current/source changes
    # must still be checked before publishing; a rejection preserves the old sources.
    with app.managed_stateful.learning_lifecycle_lock, target.corpus.lock:
        with app.lock:
            if app.managed_stateful.active_learning is not target:
                raise DebriefUnavailable("changed")
        if _lineage(target) != lineage:
            raise DebriefUnavailable("changed")
        return target.debrief_sources.add(evidence, source_handle=stamp[1])


def remove_source(app, values):
    if set(values) != {"managed_handle", "scope_id", "binding_id"}:
        raise ValueError("Use the exact debrief removal fields.")
    scope = resolve_scope(app, values["scope_id"])
    target = scope.owner
    if target is None or target.handle != values["managed_handle"]:
        raise DebriefUnavailable("changed")
    with app.managed_stateful.learning_lifecycle_lock, target.corpus.lock:
        resolve_scope(app, scope.scope_id)
        return target.debrief_sources.remove(values["binding_id"])


def recording_return(app, evidence, source_handle):
    """Never substitute another revision or implicitly reopen a same-looking Game."""
    with app.managed_stateful.match_lifecycle_lock:
        with app.lock:
            source = app.managed_stateful.active_match
        if source is None or source.handle != source_handle:
            raise DebriefUnavailable("recording_changed")
        with source.capture.lock:
            require_evidence_recording(source, evidence)
            return source


def require_evidence_recording(source, evidence):
    """Caller owns Capture lock; also used at the recording-page capture boundary."""
    source.require_attached()
    try:
        require_recording_fresh_v1(source, "matches")
    except (ValueError, RuntimeError, OSError) as error:
        raise DebriefUnavailable("recording_changed") from error
    if (source.capture.content_fingerprint
            != evidence.source_snapshot.source_content_fingerprint):
        raise DebriefUnavailable("recording_changed")
