"""Private content identities and the existing direct-entry outcome's source binding."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from skatmind.corpus_web.contracts import LearningCorpusWebResultV1

from .operation_feedback import FeedbackSource, feedback_source


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
