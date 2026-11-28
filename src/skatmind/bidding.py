"""Chronological public bidding observations (ISkO November 2022, 3.3.1–3.3.8)."""

from dataclasses import asdict, dataclass

# Official game-value table, including the four fixed Null values.
BID_VALUES = tuple(sorted(
    {base * factor for base in (9, 10, 11, 12) for factor in range(2, 19)}
    | {24 * factor for factor in range(2, 12)} | {23, 35, 46, 59}
))


class BiddingContinuationConflict(ValueError):
    """The correction would discard later observations without explicit consent."""

    def __init__(self, count: int):
        self.count = count
        super().__init__(f"The bidding correction conflicts with {count} later entries.")


@dataclass(frozen=True, slots=True)
class BidAction:
    player_id: str
    action: str
    value: int | None = None

    def __post_init__(self):
        if not isinstance(self.player_id, str) or not self.player_id.strip():
            raise ValueError("A bidding action requires a player.")
        if self.action not in ("bid", "hold", "pass", "take"):
            raise ValueError("Unknown bidding action.")
        if self.action in ("bid", "hold"):
            if type(self.value) is not int or self.value not in BID_VALUES:
                raise ValueError("The observed value must be a legal game value.")
        elif self.value is not None:
            raise ValueError("Passing and taking an unbid game have no spoken value.")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BiddingTurn:
    actor: str | None
    actions: tuple[str, ...]
    value: int | None
    declarer: str | None

    @property
    def effective_value(self):
        return (self.value or 18) if self.declarer is not None else None


def replay_bidding(seats: tuple[str, ...], events: tuple[BidAction, ...]) -> BiddingTurn:
    """Derive the next turn or outcome from public facts alone, including a strict prefix."""
    if len(seats) != 3 or len(set(seats)) != 3:
        raise ValueError("Bidding requires three distinct seated players.")
    forehand, middlehand, rearhand = seats
    bidder, listener = middlehand, forehand
    actor, value, winner = bidder, None, None
    unbid_choice = False
    for event in events:
        if type(event) is not BidAction or actor is None or event.player_id != actor:
            raise ValueError("The bidding action does not match the next player.")
        if unbid_choice:
            if event.action not in ("pass", "take"):
                raise ValueError("Forehand must take the unbid game or pass.")
            winner = forehand if event.action == "take" else None
            actor = None
        elif event.action == "pass":
            remaining = listener if actor == bidder else bidder
            if bidder == middlehand:
                bidder, listener = rearhand, remaining
                actor = rearhand
            elif value is None:
                actor, unbid_choice = forehand, True
            else:
                actor, winner = None, remaining
        elif actor == bidder and event.action == "bid" and event.value > (value or 0):
            value, actor = event.value, listener
        elif actor == listener and event.action == "hold" and event.value == value:
            actor = bidder
        else:
            raise ValueError("The action or value conflicts with the bidding prefix.")
    if actor is None:
        actions = ()
    elif unbid_choice:
        actions = ("take", "pass")
    elif actor == listener:
        actions = ("hold", "pass")
    else:
        actions = ("pass",) if value == BID_VALUES[-1] else ("bid", "pass")
    return BiddingTurn(actor, actions, value, winner)
