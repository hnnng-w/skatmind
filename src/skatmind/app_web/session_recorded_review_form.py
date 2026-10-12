from __future__ import annotations

import re
from collections.abc import Mapping

from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1
from skatmind.whole_game_rollout_workflow import PUBLIC_ROLLOUT_TIMEOUT_MS

from .session_recorded_review import RecordedDecisionReviewConflictError
from .validation_contracts import FrontendValidationIssueV1


def parse_recorded_review_selection_v1(values: Mapping[str, str]) -> str:
    if set(values) != {"decision_selection"}:
        raise ValueError("Recorded review accepts only its server-owned selection.")
    selection = values["decision_selection"]
    if re.fullmatch(r"[0-9a-f]{64}", selection) is None:
        raise ValueError("Recorded review selection must be one bounded opaque value.")
    return selection


def recorded_review_feedback_v1(error: Exception, *, status: int) -> FrontendValidationIssueV1:
    reason = (error.reason if isinstance(error, RecordedDecisionReviewConflictError)
              else "selection" if status == 409 else "invalid_fields")
    return FrontendValidationIssueV1(
        field_key=None, message_key=f"validation.recorded_review.{reason}",
    )


def parse_recorded_rollout_form_v1(values: Mapping[str, str]):
    if set(values) != {"decision_selection", "objective", "requested_worlds", "random_seed"}:
        raise ValueError("Whole-game review accepts only selection, objective, worlds, and seed.")
    selection = parse_recorded_review_selection_v1({
        "decision_selection": values["decision_selection"]})
    if any(re.fullmatch(r"[0-9]{1,20}", values[name]) is None
           for name in ("requested_worlds", "random_seed")):
        raise ValueError("Rollout worlds and seed must be bounded unsigned integers.")
    return selection, WholeGameRolloutSettingsV1(
        objective=values["objective"], requested_worlds=int(values["requested_worlds"]),
        random_seed=int(values["random_seed"]), wall_clock_timeout_ms=PUBLIC_ROLLOUT_TIMEOUT_MS,
    )
