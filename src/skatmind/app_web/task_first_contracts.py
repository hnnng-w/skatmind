from __future__ import annotations

from dataclasses import dataclass

from skatmind.match_capture_application_contracts import MatchCapturePositionViewV1
from skatmind.session_projection import SessionProjectionV1


@dataclass(frozen=True, slots=True)
class TaskFirstWorkflowV1:
    """Presentation ordering only; never an authoritative phase or readiness system."""

    status: str
    next_task_key: str
    primary_action: str | None
    completed_steps: tuple[str, ...] = ()
    secondary_actions: tuple[str, ...] = ()
    blocked_reason_keys: tuple[str, ...] = ()
    advanced_sections: tuple[str, ...] = ()
    technical_sections: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "completed_steps", "secondary_actions", "blocked_reason_keys",
            "advanced_sections", "technical_sections",
        ):
            values = getattr(self, name)
            if type(values) is not tuple or any(type(value) is not str for value in values):
                raise ValueError("Task presentation collections must be immutable text tuples.")


@dataclass(frozen=True, slots=True)
class TaskFirstSessionV1:
    workflow: TaskFirstWorkflowV1
    facts: SessionProjectionV1
    entry_player_id: str | None
    deal_destination: str
    position_available: bool
    historical_available: bool

    def __post_init__(self) -> None:
        if (type(self.workflow) is not TaskFirstWorkflowV1
                or type(self.facts) is not SessionProjectionV1):
            raise ValueError("Session presentation requires exact immutable projections.")
        if type(self.position_available) is not bool or type(self.historical_available) is not bool:
            raise ValueError("Session availability must retain exact boolean values.")


@dataclass(frozen=True, slots=True)
class TaskFirstMatchV1:
    workflow: TaskFirstWorkflowV1
    positions: tuple[MatchCapturePositionViewV1, ...]
    selected_position: int
    next_position: int | None

    def __post_init__(self) -> None:
        if type(self.positions) is not tuple or len(self.positions) != 36:
            raise ValueError("Match presentation requires exactly 36 immutable positions.")
        if any(type(view) is not MatchCapturePositionViewV1 for view in self.positions):
            raise ValueError("Match presentation requires existing Product position views.")
        if tuple(view.match_position for view in self.positions) != tuple(range(1, 37)):
            raise ValueError("Match presentation must retain canonical position order.")

    @property
    def selected(self) -> MatchCapturePositionViewV1:
        return self.positions[self.selected_position - 1]
