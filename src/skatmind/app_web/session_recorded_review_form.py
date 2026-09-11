from __future__ import annotations

import re
from collections.abc import Mapping

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
