"""One explicit saved-game review. The accepted document identifies each observed checkpoint."""

import hmac
import secrets
from copy import deepcopy
from threading import Event, Thread

from skatmind.automatic_learning_io import release_local_lease
from skatmind.errors import SkatMindError
from skatmind.rollout_derivation import missing_rollout_settlement_inputs
from skatmind.session_rollout_review import derive_session_rollout_review_request_v1
from skatmind.whole_game_rollout_workflow import parse_rollout_settings

from .forced_card_guidance import forced_card_guidance
from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
from .saved_match_analyses import archive_store
from .session_evidence_retention import save_pending_session, session_source_epoch
from .session_recorded_review import (
    RecordedDecisionReviewConflictError,
    execute_recorded_session_decision_v1,
    project_recorded_session_decisions_v1,
)
from .session_recorded_review_form import parse_recorded_rollout_supplements_v1
from .whole_match_progress import ProgressFile, file_identity


class SessionProgress(ProgressFile):
    directory = "session-game-reviews"

    def read(self):
        state = super().read()
        if state is not None and state.get("game") != 1:
            raise ValueError("Expected a single saved Session game.")
        return state


def progress_file(app, active):
    return SessionProgress(app.managed_home.root, active.path.name)


def proof(active, state):
    material = (active.handle, active.generation, active.document.content_fingerprint,
                file_identity(active.path), state and state["run"])
    return hmac.digest(active.review_selection_key, repr(material).encode(), "sha256").hex()


def plan(active, settings, supplements):
    coverage = project_recorded_session_decisions_v1(active)
    rows = []
    for row in coverage.decisions:
        checkpoint = row.checkpoint
        root = checkpoint.request.to_dict()["document"]
        missing = missing_rollout_settlement_inputs(root)
        supplied = {k: str(v) for k, v in supplements.items() if k in missing}
        reason = ("whole_review.forced" if forced_card_guidance(checkpoint.request) else
                  "rollout.reason.unsupported_game_type" if root["game_type"] == "null" else
                  "rollout.reason.missing_terminal_utility_inputs"
                  if settings.objective == "complete_settlement" and set(missing) - supplied.keys()
                  else None)
        request = None
        if not reason:
            extras = parse_recorded_rollout_supplements_v1(supplied, root, settings.objective)
            request = derive_session_rollout_review_request_v1(state=active.state,
                checkpoint=checkpoint, settings=settings, supplements=extras)
        rows.append((f"1:{checkpoint.decision_index}", row, reason, supplied, request))
    return coverage, rows


class SessionWorker:
    def __init__(self, app, active, progress, state, lease, recovered=None):
        self.app, self.active, self.progress, self.state = app, active, progress, state
        self.lease, self.expected = lease, deepcopy(state)
        self.document, self.generation = active.document, active.generation
        self.archive = app.saved_match_analyses
        self.attempt = active.execution_attempt
        self.recovered = recovered
        self.coordinator, self.epoch = session_source_epoch(active)
        self.thread = Thread(target=self.run, daemon=True, name="session-game-review")
        self.stop = Event()

    def authority(self):
        active = self.active
        if (active.retired or self.app.managed_stateful.active_session is not active
                or active.document is not self.document or active.generation != self.generation
                or self.coordinator.generation != self.epoch
                or self.app.saved_match_analyses is not self.archive
                or self.progress.read() != self.expected
                or file_identity(active.path) != self.state["file"]):
            raise RecordedDecisionReviewConflictError("source_changed")
        require_recording_fresh_v1(active, "sessions")

    def checkpoint(self, phase):
        with self.active.lock, self.app.lock:
            self.authority()
            self.state["phase"] = phase
            self.progress.write(self.state)
            self.expected = deepcopy(self.state)

    def reusable(self, value, row, request):
        return (value is not None and value.entry.envelope.kind == "session_rollout"
                and value.source.document == self.document and value.checkpoint == row.checkpoint
                and value.observation == row.observation and value.execution.request == request
                and (value.entry.identity == self.recovered or
                     value.execution.result.result.document["whole_game_rollout_result"]["status"]
                     == "complete"))

    def process(self):
        active = self.active
        settings = parse_rollout_settings(self.state["settings"])
        _, rows = plan(active, settings, self.state["supplements"].get("1", {}))
        self.authority()
        values = {}
        store = archive_store(self.app)
        if store:
            store.snapshot(_admitted=values)
        for key, row, reason, supplied, request in rows:
            if self.stop.is_set():
                return "paused"
            if reason:
                continue
            old = self.state["refs"].get(key)
            previous = old and values.get(old[1])
            match = previous if self.reusable(previous, row, request) else next(
                (v for v in values.values() if self.reusable(v, row, request)), None)
            if match:
                if not old or old[1] != match.entry.identity:
                    self.state["refs"][key] = ["reused", match.entry.identity]
                self.checkpoint("working")
                continue
            def begin():
                self.authority()
                if active.execution_attempt is not self.attempt or self.stop.is_set():
                    raise RecordedDecisionReviewConflictError("superseded")
            execute_recorded_session_decision_v1(self.app, active, selection=row.selection,
                rollout_settings=settings, rollout_supplements=supplied, batch_guard=self.authority,
                before_batch_attempt=begin)
            with active.lock:
                notice = active.evidence_notice
                if not notice or notice[0].decision != row or notice[1] != "saved":
                    return "unsaved"
                self.attempt = notice[0].attempt
                self.state["refs"][key] = ["computed", notice[2]]
            self.checkpoint("working")
        return "paused" if self.stop.is_set() else "finished"

    def run(self):
        try:
            try:
                phase = self.process()
            except (OSError, RuntimeError, ValueError, SkatMindError):
                phase = "unsaved" if self.active.pending_evidence else "failed"
            self.checkpoint(phase)
        except (OSError, RuntimeError, ValueError, SkatMindError):
            pass  # An interrupted receipt remains retryable only for its exact file.
        finally:
            with self.app.session_batch.lock:
                self.app.session_batch.worker = None
                release_local_lease(self.lease)


def control(app, active, action, binding, configuration=None):
    owner = app.session_batch
    progress = progress_file(app, active)
    with active.lock, app.lock, owner.lock:
        require_recording_fresh_v1(active, "sessions")
        state = progress.read()
        if app.managed_stateful.active_session is not active or proof(active, state) != binding:
            raise RecordingOpenConflict()
        worker = owner.worker
        if action == "cancel" and worker and worker.active is active:
            worker.authority()
            worker.stop.set()
            return
        if worker or action not in ("start", "resume"):
            raise RecordingOpenConflict()
        recovered = None
        if active.pending_evidence:
            pending = active.pending_evidence
            if (action != "resume" or not pending.source.batch_guard
                    or save_pending_session(app, active, pending.token) != "saved"):
                raise RecordingOpenConflict()
            recovered = pending.candidate.evidence.identity
        lease = progress.lease()
        try:
            if progress.read() != state:
                raise RecordingOpenConflict()
            run, file = secrets.token_hex(32), file_identity(active.path)
            source = active.document.content_fingerprint
            if action == "start":
                settings, extras = configuration
                fresh = progress.initial(source, file, run, settings, {"1": extras} if extras
                                         else {}, game=1)
                if state and all(fresh[k] == state[k] for k in (
                        "source", "file", "settings", "supplements")):
                    raise RecordingOpenConflict()
                state = fresh
            elif state and state["source"] == source and state["file"] == file:
                state.update(run=run, phase="working")
            else:
                raise RecordingOpenConflict()
            progress.write(state)
            worker = owner.worker = SessionWorker(app, active, progress, state, lease, recovered)
            owner.generation += 1
            worker.thread.start()
        except BaseException:
            owner.worker = None
            release_local_lease(lease)
            raise
