"""One explicit, resumable recorded-perspective review worker per managed home."""

import hmac
import secrets
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field, replace
from threading import Event, RLock, Thread

from skatmind.automatic_learning_contracts import AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
from skatmind.automatic_learning_io import release_local_lease
from skatmind.automatic_learning_store import StoreBusyError, StoreConflictError, StoreLimitError
from skatmind.automatic_match_rollout_evidence import build_match_rollout_capture_candidate
from skatmind.errors import SkatMindError
from skatmind.match_analysis_contracts import build_match_analysis_report_v1
from skatmind.match_decision_analysis import (
    build_match_rollout_dependencies_v1,
    execute_match_decision_analysis_v1,
)
from skatmind.whole_game_rollout_workflow import parse_rollout_settings

from .match_evidence_retention import capture_original_document
from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
from .saved_match_analyses import archive_store
from .whole_match_plan import own_plays
from .whole_match_progress import ProgressFile, file_identity


@dataclass
class Controller:
    lock: RLock = field(default_factory=RLock)
    worker: object = None
    pending: tuple | None = None
    generation: int = 0
    plan: tuple | None = None

    def plays(self, workspace, game=None):
        with self.lock:
            if self.plan and self.plan[0] is workspace and self.plan[1] == game:
                return self.plan[2]
        rows = own_plays(workspace, game)
        with self.lock:
            self.plan = (workspace, game, rows)
        return rows


def progress_file(app, active):
    return ProgressFile(app.managed_home.root, active.path.name)


def proof(active, state, *, requested_game=None):
    source = (active.handle, active.capture.content_fingerprint, file_identity(active.path),
              state["run"] if state else None, state.get("game") if state else None, requested_game)
    return hmac.digest(active.card_entry_key, repr(source).encode(), "sha256").hex()


@contextmanager
def evidence_view(app, workspace, source, options):
    """One bulk strict admission per view, pinned through the caller's publication."""
    scope = app.saved_match_analyses
    store = archive_store(app)
    if store is None:
        def validate():
            if app.saved_match_analyses is not scope or archive_store(app) is not None:
                raise RecordingOpenConflict()
        yield {}, None, validate
        return
    # Keep the strict snapshot's operation-local decoded values, never reuse them
    # across workers, requests or the final delivery check.
    values = {}
    snapshot = store.snapshot(_admitted=values)
    compatible = {}
    for value in values.values():
        if (value.entry.envelope.kind != "match_rollout"
                or value.source.document.content_fingerprint != source):
            continue
        report = value.report
        key = f"{report.match_position}:{report.decision_index}"
        if (report.value.profile_binding.acting_player_id ==
                workspace.match_definition.perspective_player_id
                and report.value.options == options.get(key)):
            compatible[value.entry.identity] = value
    del values
    identities = frozenset(compatible)
    with store.pin_objects(tuple(v.entry.envelope for v in compatible.values()),
                           expected_manifest=snapshot.manifest.fingerprint):
        def validate():
            current = store.snapshot()
            if (app.saved_match_analyses is not scope or scope.store is not store
                    or current.manifest != snapshot.manifest
                    or not identities.issubset(current.available_evidence_ids)):
                raise RecordingOpenConflict()
        yield compatible, snapshot.manifest, validate


def row_options(rows, state):
    if state["refs"].keys() - {row.key for row in rows}:
        raise ValueError("Progress references an unrecorded perspective decision.")
    allowed = {(str(row.position), name) for row in rows for name in row.missing}
    if any((p, name) not in allowed for p, values in state["supplements"].items()
           for name in values):
        raise ValueError("Unexpected game-specific supplement.")
    settings = parse_rollout_settings(state["settings"])
    return {r.key: r.options(settings, state["supplements"].get(str(r.position), {}))
            for r in rows}


class Worker:
    def __init__(self, app, active, document, progress, state, lease, pending):
        self.app, self.active, self.document = app, active, document
        self.workspace = active.workspace
        self.archive = app.saved_match_analyses
        self.progress, self.state, self.lease = progress, state, lease
        self.expected = deepcopy(state)
        self.pending = pending
        self.stop = Event()
        self.thread = Thread(target=self.run, name="whole-match-review", daemon=True)

    def owns_source(self):
        return (not self.active.retired and self.active.workspace is self.workspace
                and self.app.managed_stateful.active_match is self.active
                and self.app.saved_match_analyses is self.archive
                and self.app.whole_match.worker is self)

    def cancelled(self):
        return self.stop.is_set() or not self.owns_source()

    @contextmanager
    def publishing(self):
        with self.active.capture.lock, self.app.lock:
            self.require_authority()
            yield

    def require_authority(self):
        persisted = self.progress.read()
        if (not self.owns_source() or file_identity(self.active.path) != self.state["file"]
                or persisted != self.expected):
            raise RecordingOpenConflict()
        require_recording_fresh_v1(self.active, "matches")
        return True

    @contextmanager
    def final_publication(self):
        # Other producers can hold Match/app while waiting on this store.
        # Never wait in the opposite direction; a busy commit is save-only retryable.
        capture = self.active.capture.lock
        if not capture.acquire(blocking=False):
            raise StoreBusyError("Match publication is busy.")
        try:
            if not self.app.lock.acquire(blocking=False):
                raise StoreBusyError("Application publication is busy.")
            try:
                yield
            finally:
                self.app.lock.release()
        finally:
            capture.release()

    def checkpoint(self, phase):
        with self.publishing():
            self.state["phase"] = phase
            self.progress.write(self.state)
            self.expected = deepcopy(self.state)

    def reconcile(self, options):
        refs = self.state["refs"]
        done = set()
        with evidence_view(self.app, self.workspace, self.state["source"], options) as (
                values, _, validate):
            matches = {}
            for identity, value in values.items():
                key = f"{value.report.match_position}:{value.report.decision_index}"
                matches.setdefault(key, []).append((identity, value.comparison is not None))
            values.clear()  # Only identities are needed during the fresh final admission.
            for key, candidates in matches.items():
                former = refs.get(key, [None, None])
                if (former[1], True) in candidates:
                    if former[0] == "saving":
                        refs[key] = ["computed", former[1]]
                else:
                    complete = next((i for i, valid in candidates if valid), None)
                    if complete:
                        refs[key] = ["reused", complete]
                    elif former[0] == "saving" and (former[1], False) in candidates:
                        refs[key] = ["computed", former[1]]
                    else:
                        continue
                done.add(key)
            validate()
            self.checkpoint("working")
        return done

    def save(self, key, candidate):
        # Record the exact intent before staging. Recovery distinguishes an
        # accepted incomplete execution from an interrupted computation as well.
        if any(obj.reference.size_bytes > AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
               for obj in candidate.objects):
            raise StoreLimitError("Execution exceeds the archive object limit.")
        self.state["refs"][key] = ["saving", candidate.evidence.identity]
        self.pending = (key, candidate)
        self.checkpoint("working")
        store = archive_store(self.app, initialize=True)
        reservation = store.begin_candidate(candidate.objects)
        try:
            before = store._manifest()
            for obj in candidate.objects:
                if store.publish_object(obj, candidate=reservation) == "conflict":
                    raise ValueError("Evidence staging conflict.")
            requested = replace(before, revision=before.revision + 1,
                objects=before.objects + tuple(obj.entry for obj in candidate.objects
                                              if obj.entry not in before.objects),
                sources=before.sources + (() if candidate.source in before.sources
                                          else (candidate.source,)),
                evidence=before.evidence + (() if candidate.evidence in before.evidence
                                            else (candidate.evidence,)))
            result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                candidate=reservation, commit_guard=self.require_authority,
                publication_context=self.final_publication)
            if result.status not in ("saved", "unchanged"):
                raise ValueError("Evidence manifest conflict.")
        finally:
            try:
                store.release_candidate(reservation)
            except StoreConflictError:
                pass  # The successful manifest commit consumes its reservation.
        self.state["refs"][key][0] = "computed"
        self.checkpoint("working")
        self.pending = None

    def process(self):
        rows = self.app.whole_match.plays(self.workspace, self.state.get("game"))
        options = row_options(rows, self.state)
        done = self.reconcile(options)
        if self.pending:
            key, candidate = self.pending
            if key not in done:
                self.save(key, candidate)
                done.add(key)
            self.pending = None
        for row in rows:
            if self.cancelled():
                return "paused"
            if row.key in done or options[row.key] is None:
                continue
            capture = []
            report = build_match_analysis_report_v1(execute_match_decision_analysis_v1(
                self.workspace, match_position=row.position, decision_index=row.decision,
                options=options[row.key],
                execution_observer=lambda i, e, c=capture: c.append((i, e)),
                dependencies=build_match_rollout_dependencies_v1(cancelled=self.cancelled)))
            with self.publishing():
                pass
            (invocation, execution), = capture
            candidate = build_match_rollout_capture_candidate(
                self.document, report, invocation, execution)
            self.save(row.key, candidate)
        return "paused" if self.stop.is_set() else "finished"

    def run(self):
        owner = self.app.whole_match
        try:
            try:
                phase = self.process()
            except StoreLimitError:
                phase = "quota"
            except (OSError, ValueError, SkatMindError):
                phase = "unsaved" if self.pending else "failed"
            self.checkpoint(phase)
        except (OSError, ValueError, RecordingOpenConflict, SkatMindError):
            # Unpublished work has no durable receipt. A surviving "working"
            # checkpoint with no worker always presents as interrupted.
            pass
        finally:
            with owner.lock:
                if owner.worker is self:
                    owner.pending = ((self.active, self.workspace, self.archive,
                                      self.state["run"], self.pending) if self.pending else None)
                    owner.worker = None
                release_local_lease(self.lease)


def control(app, active, action, binding, *, configuration=None, game=None):
    owner = app.whole_match
    progress = progress_file(app, active)
    with active.capture.lock, app.lock, owner.lock:
        active.require_attached()
        if app.managed_stateful.active_match is not active:
            raise RecordingOpenConflict()
        require_recording_fresh_v1(active, "matches")
        state = progress.read()
        if game is not None and (action != "start" or type(game) is not int or not 1 <= game <= 36):
            raise RecordingOpenConflict()
        if not hmac.compare_digest(proof(active, state, requested_game=game), binding):
            raise RecordingOpenConflict()
        if action == "cancel":
            worker = owner.worker
            if (not worker or not state or not worker.owns_source()
                    or worker.state["run"] != state["run"]):
                raise RecordingOpenConflict()
            worker.stop.set()
            return
        if owner.worker or action not in ("start", "resume"):
            raise RecordingOpenConflict()
        lease = progress.lease()
        try:
            if progress.read() != state:
                raise RecordingOpenConflict()
            document = capture_original_document(app, active)
            pending = None
            file = file_identity(active.path)
            if action == "start":
                old = owner.pending
                if (old and state and old[0] is active and old[1] is active.workspace
                        and old[2] is app.saved_match_analyses and old[3] == state["run"]):
                    raise RecordingOpenConflict()
                fresh = progress.initial(document.content_fingerprint, file, secrets.token_hex(32),
                    *configuration, game=game)
                if (state and state.get("game") == game and all(fresh[k] == state[k] for k in
                                  ("source", "file", "settings", "supplements"))):
                    raise RecordingOpenConflict()  # Use explicit Resume on this job.
                state = fresh
            else:
                if (state is None or state["source"] != document.content_fingerprint
                        or state["file"] != file):
                    raise RecordingOpenConflict()
                old = owner.pending
                if (old and old[0] is active and old[1] is active.workspace
                        and old[2] is app.saved_match_analyses and old[3] == state["run"]):
                    pending = old[4]
                state.update(run=secrets.token_hex(32), phase="working")
            worker = Worker(app, active, document, progress, state, lease, pending)
            if file_identity(active.path) != file or not hmac.compare_digest(
                    proof(active, progress.read(), requested_game=game), binding):
                raise RecordingOpenConflict()
            progress.write(state)
            owner.generation += 1
            owner.worker = worker
            owner.pending = None
            worker.thread.start()
        except BaseException:
            owner.worker = None
            release_local_lease(lease)
            raise
