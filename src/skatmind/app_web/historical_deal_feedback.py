"""Private exact-count facts from authoritative manual deal validation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HistoricalDealCountV1:
    field: str
    actual: int
    required: int

    def __post_init__(self) -> None:
        required = {"forehand_hand": 10, "middlehand_hand": 10, "rearhand_hand": 10, "skat": 2}
        if (self.field not in required or type(self.required) is not int
                or self.required != required[self.field] or type(self.actual) is not int
                or not 0 <= self.actual <= 32 or self.actual == self.required):
            raise ValueError("Deal count feedback requires an exact field and unequal Card counts.")


class HistoricalDealCountError(ValueError):
    def __init__(self, counts: tuple[HistoricalDealCountV1, ...]) -> None:
        self.counts = counts
        super().__init__(" ".join(
            f"{count.field} must contain exactly {count.required} cards." for count in counts))
