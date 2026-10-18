"""Private rule completion, separate from complete traces and explicit endings."""

from collections.abc import Sequence
from dataclasses import dataclass

from skatmind.game_declaration import GameDeclaration


@dataclass(frozen=True, slots=True)
class RecordingRuleEnd:
    """The first accepted completed declarer trick proves a Null loss."""

    declarer_player_id: str
    trick_number: int

    @property
    def decisive_play_count(self) -> int:
        return self.trick_number * 3


def derive_recording_rule_end(
    declaration: GameDeclaration | None,
    declarer_player_id: str | None,
    validated_winner_player_ids: Sequence[str],
) -> RecordingRuleEnd | None:
    """Consume rule-resolved winners from validated records, never asserted roles.

    Replay callers retain the entire observed archive. Capture and decision callers
    use the first decisive boundary; neither points nor unknown ownership enter it.
    """
    if declaration is not None and declaration.game_type == "null" and declarer_player_id:
        for number, winner in enumerate(validated_winner_player_ids, 1):
            if winner == declarer_player_id:
                return RecordingRuleEnd(declarer_player_id, number)
    return None
