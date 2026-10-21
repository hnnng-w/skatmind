"""Private content identities and the existing direct-entry outcome's source binding."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from skatmind.corpus_web.contracts import LearningCorpusWebResultV1
from skatmind.corpus_web.downloads import (
    LearningCorpusPreparedDownloadUnavailableError,
    require_learning_corpus_prepared_bundle_v1,
)

from .debrief_frontend import DebriefUnavailable, collection_scope, resolve_scope
from .operation_feedback import FeedbackSource, feedback_source

LEARNING_PREPARED_PATTERN = re.compile(r"/learning/prepared/([0-9a-f]{64})\Z")


def resolve_prepared_scope(app, scope_id):
    """Scope lineage is necessary, but never replaces actual bundle availability."""
    scope = resolve_scope(app, scope_id)
    if scope.owner is None:
        raise DebriefUnavailable()
    with scope.owner.corpus.lock:
        resolve_scope(app, scope_id)
        try:
            require_learning_corpus_prepared_bundle_v1(scope.owner.corpus)
        except LearningCorpusPreparedDownloadUnavailableError as error:
            raise DebriefUnavailable("changed") from error
    return scope


def prepared_result_location(app, target):
    """Retain only the existing bounded collection scope; perform no preparation."""
    with target.corpus.lock:
        scope = collection_scope(app, target)
        resolve_prepared_scope(app, scope.scope_id)
        return f"/learning/prepared/{scope.scope_id}"


def learning_match_target(handle: str, match_id: str) -> str:
    material = f"learning-match-v1:{handle}:{match_id}".encode()
    return "learning-match-" + hashlib.sha256(material).hexdigest()


def learning_version_target(handle: str, snapshot_id: str) -> str:
    material = f"learning-version-v1:{handle}:{snapshot_id}".encode()
    return "learning-version-" + hashlib.sha256(material).hexdigest()


@dataclass(frozen=True, slots=True)
class LearningEntryOutcome:
    result: LearningCorpusWebResultV1
    match_id: str
    copied_revision: int
    selected: bool
    snapshot_id: str | None
    source: FeedbackSource


def current_learning_entry_outcome(active):
    """Caller owns the Corpus lock. Navigation never establishes Current or freshness."""
    outcome = active.entry_outcome
    if (outcome is not None and outcome.result is active.last_result
            and outcome.source.matches(feedback_source(active))):
        return outcome
    return None
