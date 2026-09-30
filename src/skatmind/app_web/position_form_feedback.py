"""Bounded private diagnosis for guided Position selection omissions."""

from dataclasses import dataclass

POSITION_COMPLETED_TRICK_ROW_COUNT_V1 = 9
COMPLETED_TRICK_CONTROLS = ("leader", "card_1", "card_2", "card_3")


@dataclass(frozen=True, slots=True)
class PositionFormFeedbackV1:
    reason: str
    trick_number: int | None = None
    missing_controls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        missing = tuple(self.missing_controls)
        object.__setattr__(self, "missing_controls", missing)
        if self.reason == "empty_hand":
            if self.trick_number is not None or missing:
                raise ValueError("Empty-hand feedback has no Trick context.")
        elif self.reason == "incomplete_trick":
            if (type(self.trick_number) is not int
                    or not 1 <= self.trick_number <= POSITION_COMPLETED_TRICK_ROW_COUNT_V1
                    or not 1 <= len(missing) <= 3
                    or missing != tuple(name for name in COMPLETED_TRICK_CONTROLS
                                        if name in missing)):
                raise ValueError("Incomplete-Trick feedback requires a row and ordered omissions.")
        else:
            raise ValueError("Position feedback requires one supported reason.")

    @property
    def fields(self) -> tuple[str, ...]:
        if self.reason == "empty_hand":
            return ("hand",)
        return tuple(f"completed_trick_{self.trick_number}_{name}"
                     for name in self.missing_controls)

    @property
    def message_key(self) -> str:
        return "validation.position." + self.reason
