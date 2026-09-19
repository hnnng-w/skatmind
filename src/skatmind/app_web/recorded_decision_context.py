"""Minimized retained Position facts; no Request, replay or execution dependencies."""

from collections.abc import Mapping
from dataclasses import dataclass

from skatmind.deck import get_full_deck
from skatmind.turn_phase import CONCRETE_PLAYERS, derive_next_player


@dataclass(frozen=True, slots=True)
class DecisionContextPlayer:
    label: str | None
    number: int


@dataclass(frozen=True, slots=True)
class RecordedDecisionContext:
    game_number: int | None
    trick_number: int | None
    play_index: int | None
    actor: DecisionContextPlayer | None
    game_type: str | None
    declarer: DecisionContextPlayer | None
    current_trick: tuple[tuple[DecisionContextPlayer | None, str], ...] | None
    next_player: DecisionContextPlayer | None
    hand: tuple[str, ...] | None
    declarer_points: int | None
    defender_points: int | None


def _object(value):
    return value if isinstance(value, Mapping) else {}


def _cards(value, maximum):
    if (not isinstance(value, (list, tuple)) or len(value) > maximum
            or any(type(card) is not str or card not in get_full_deck() for card in value)
            or len(set(value)) != len(value)):
        return None
    return tuple(value)


def _integer(value):
    return value if type(value) is int else None


def source_player_labels(players, relative_ids):
    """Resolve only a complete source-bound identity map; never retain stable IDs."""
    if (set(relative_ids) != set(CONCRETE_PLAYERS)
            or len(set(relative_ids.values())) != 3
            or set(relative_ids.values()) != {player.player_id for player in players}):
        return {}
    labels = {player.player_id: DecisionContextPlayer(player.player_label or None, number)
              for number, player in enumerate(players, 1)}
    return {relative: labels[player_id] for relative, player_id in relative_ids.items()}


def project_recorded_decision_context(
    document, *, players, trick_number=None, play_index=None, game_number=None,
):
    """Allowlist independent display fields from an already retained Position Result.

    Malformed defensive presentation fixtures keep valid siblings, without input
    validation, coercion, missing-as-empty defaults or reconstruction.
    """
    position = _object(_object(document).get("position"))
    if not position:
        return None
    score = _object(document.get("score_summary"))
    prefix = _cards(position.get("current_trick"), 2)
    leader = position.get("trick_leader")
    current = None if prefix is None else tuple(
        (players.get(derive_next_player(leader, offset))
         if leader in CONCRETE_PLAYERS else None, card)
        for offset, card in enumerate(prefix)
    )
    game_type = position.get("game_type")
    declarer = position.get("declarer_player")
    next_player = position.get("next_player")
    return RecordedDecisionContext(
        _integer(game_number), _integer(trick_number), _integer(play_index), players.get("me"),
        game_type if game_type in (
            "clubs", "spades", "hearts", "diamonds", "grand", "null") else None,
        players.get(declarer) if type(declarer) is str else None,
        current,
        players.get(next_player) if type(next_player) is str else None,
        _cards(position.get("hand"), 10),
        _integer(score.get("total_declarer_points")), _integer(score.get("total_defender_points")),
    )
