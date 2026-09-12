from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from skatmind.rules import get_effective_suit, get_legal_cards

if TYPE_CHECKING:
    from skatmind.observed_game_trace import ObservedPlayV1


@dataclass(frozen=True, slots=True)
class ObservedTraceDiagnostic:
    """Private retained evidence, never a public Result or reconstructed hand."""

    reason: Literal["duplicate", "ownership", "discard", "skat", "wrong_actor", "follow_suit"]
    play_index: int
    card: str
    player_id: str
    witness_index: int | None = None
    witness_card: str | None = None
    expected_player_id: str | None = None
    required_suit: str | None = None
    complete_replay: bool = False


class ObservedTraceError(ValueError):
    """Keep the existing English ValueError message and precise private evidence."""

    def __init__(self, message: str, diagnostic: ObservedTraceDiagnostic) -> None:
        super().__init__(message)
        self.diagnostic = diagnostic


def follow_suit_diagnostic(
    plays: tuple[ObservedPlayV1, ...], play: ObservedPlayV1,
    legal_cards: list[str], game_type: str, *, complete_replay: bool = False,
) -> ObservedTraceDiagnostic:
    lead = plays[((play.decision_index - 1) // 3) * 3]
    witness = next((later for later in plays[play.decision_index:]
                    if later.player_id == play.player_id and later.card in legal_cards), None)
    return ObservedTraceDiagnostic(
        "follow_suit", play.decision_index, play.card, play.player_id,
        witness_index=None if witness is None else witness.decision_index,
        witness_card=legal_cards[0] if witness is None else witness.card,
        required_suit=get_effective_suit(lead.card, game_type),
        complete_replay=complete_replay,
    )


def find_observed_trace_warning(
    plays: tuple[ObservedPlayV1, ...], game_type: str,
) -> ObservedTraceDiagnostic | None:
    """Earliest contradiction proved by a later same-actor observation only.

    This does not validate or change partial-record acceptance. The two-card
    evidence subset suffices to prove a violation; it is never a completed hand
    and must never be supplied to an earlier Decision Request.
    """
    for offset, play in enumerate(plays):
        trick_start = (offset // 3) * 3
        trick = [item.card for item in plays[trick_start:offset]]
        for later in plays[offset + 1:]:
            if later.player_id != play.player_id:
                continue
            legal = get_legal_cards([play.card, later.card], trick, game_type)
            if play.card not in legal:
                return follow_suit_diagnostic(plays, play, legal, game_type)
    return None
