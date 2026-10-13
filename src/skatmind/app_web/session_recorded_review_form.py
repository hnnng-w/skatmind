from __future__ import annotations

import re
from collections.abc import Mapping

from skatmind.game_declaration import validate_bid_value, validate_matadors
from skatmind.rollout_derivation import missing_rollout_settlement_inputs
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1
from skatmind.whole_game_rollout_workflow import PUBLIC_ROLLOUT_TIMEOUT_MS

from .session_recorded_review import RecordedDecisionReviewConflictError, RecordedRolloutNoticeV1
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


class RecordedRolloutFormError(ValueError):
    def __init__(self, reason: str, field: str | None = None) -> None:
        super().__init__("Invalid whole-game review form.")
        self.reason = reason
        self.field = field


def recorded_rollout_feedback_v1(
    error: Exception, *, status: int, execution_started: bool = False,
) -> FrontendValidationIssueV1:
    if isinstance(error, RecordedDecisionReviewConflictError) or status == 409:
        return recorded_review_feedback_v1(error, status=status)
    if isinstance(error, RecordedRolloutFormError):
        return FrontendValidationIssueV1(
            field_key=error.field, message_key="validation.rollout." + error.reason)
    return FrontendValidationIssueV1(field_key=None, message_key="validation.rollout." + (
        "execution_failed" if execution_started else "invalid_fields"))


def recorded_rollout_notice_feedback_v1(
    notice: RecordedRolloutNoticeV1,
) -> FrontendValidationIssueV1:
    reason = {
        ("bid_value",): "missing_bid",
        ("matadors",): "missing_matadors",
        ("bid_value", "matadors"): "missing_bid_and_matadors",
    }.get(notice.missing_inputs) if notice.reason == "missing_terminal_utility_inputs" else None
    return FrontendValidationIssueV1(
        field_key="objective" if reason else None,
        message_key="validation.rollout." + (reason or "incomplete_attempt"))


def parse_recorded_rollout_form_v1(values: Mapping[str, str]):
    required = {"decision_selection", "objective", "requested_worlds", "random_seed"}
    if not required <= set(values) or set(values) - required - {
        "analysis_bid_value", "analysis_matadors"
    }:
        raise RecordedRolloutFormError("invalid_fields")
    try:
        selection = parse_recorded_review_selection_v1({
            "decision_selection": values["decision_selection"]})
    except ValueError as error:
        raise RecordedRolloutFormError("invalid_selection") from error
    if values["objective"] not in ("played_game_goal", "complete_settlement"):
        raise RecordedRolloutFormError("invalid_objective", "objective")
    for name, minimum, maximum in (("requested_worlds", 1, 1000), ("random_seed", 0, 2**64 - 1)):
        if (re.fullmatch(r"[0-9]{1,20}", values[name]) is None
                or not minimum <= int(values[name]) <= maximum):
            raise RecordedRolloutFormError("invalid_" + name, name)
    settings = WholeGameRolloutSettingsV1(
        objective=values["objective"], requested_worlds=int(values["requested_worlds"]),
        random_seed=int(values["random_seed"]), wall_clock_timeout_ms=PUBLIC_ROLLOUT_TIMEOUT_MS,
    )
    return selection, settings, {name.removeprefix("analysis_"): value
                                for name, value in values.items() if name.startswith("analysis_")}


def parse_recorded_rollout_supplements_v1(values, root, objective):
    missing = missing_rollout_settlement_inputs(root)
    if set(values) - set(missing):
        raise RecordedRolloutFormError("known_input")
    # Native controls may still contain text when the user changes objectives.
    # It is not applied, validated as historical knowledge, or copied to the root.
    if objective != "complete_settlement":
        return {}
    result = {}
    for name in missing:
        raw = values.get(name, "")
        field = "analysis_" + name
        reason = "invalid_bid" if name == "bid_value" else (
            "invalid_matadors_grand" if root["game_type"] == "grand" else "invalid_matadors_suit")
        if not raw:
            raise RecordedRolloutFormError("required_" + name, field)
        try:
            if re.fullmatch(r"-?[0-9]{1,20}", raw) is None:
                raise ValueError("Expected a bounded whole number.")
            value = int(raw)
            if name == "bid_value":
                validate_bid_value(value)
            else:
                validate_matadors(value, root["game_type"])
        except ValueError as error:
            raise RecordedRolloutFormError(reason, field) from error
        result[name] = value
    return result
