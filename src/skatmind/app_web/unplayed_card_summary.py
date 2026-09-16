"""Private deck accounting over one accepted page snapshot, never source evidence."""

from dataclasses import dataclass

from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration

from .recorded_trick_progress import (
    RecordedPlay,
    RecordedPlayer,
    RecordedPrefix,
    RecordedTrick,
    RecordedTrickProgress,
)


@dataclass(frozen=True, slots=True)
class UnplayedCardSummary:
    cards: tuple[str, ...]
    hand_game: bool


def project_unplayed_cards(
    progress: RecordedTrickProgress, declaration: GameDeclaration | None,
) -> UnplayedCardSummary | None:
    """Guard the bounded normalized structure; do not replay or certify legality."""
    if (not isinstance(progress, RecordedTrickProgress)
            or not isinstance(declaration, GameDeclaration)
            or type(declaration.hand_game) is not bool
            or progress.game_type != declaration.game_type
            or progress.status not in ("complete", "ended")
            or not isinstance(progress.players, tuple) or len(progress.players) != 3
            or not isinstance(progress.tricks, tuple) or len(progress.tricks) != 10):
        return None
    if any(not isinstance(p, RecordedPlayer) or not isinstance(p.player_id, str)
           or not p.player_id for p in progress.players):
        return None
    players = tuple(p.player_id for p in progress.players)
    if len(set(players)) != 3 or progress.declarer_player_id not in players:
        return None
    deck = get_full_deck()
    seen = set()
    counts = dict.fromkeys(players, 0)
    for number, trick in enumerate(progress.tricks, 1):
        if (not isinstance(trick, RecordedTrick) or type(trick.number) is not int
                or trick.number != number
                or not isinstance(trick.prefix, RecordedPrefix)
                or trick.winner_player_id not in players
                or not isinstance(trick.plays, tuple) or len(trick.plays) != 3):
            return None
        actors = []
        for offset, play in enumerate(trick.plays, 1):
            if (not isinstance(play, RecordedPlay)
                    or type(play.decision_index) is not int
                    or play.decision_index != (number - 1) * 3 + offset
                    or play.player_id not in players
                    or not isinstance(play.card, str) or play.card not in deck
                    or play.card in seen):
                return None
            seen.add(play.card)
            counts[play.player_id] += 1
            actors.append(play.player_id)
        if len(set(actors)) != 3:
            return None
    if progress.completed_count != 10 or any(count != 10 for count in counts.values()):
        return None
    cards = tuple(card for card in deck if card not in seen)
    return UnplayedCardSummary(cards, declaration.hand_game) if len(cards) == 2 else None
