from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from skatmind.match_capture_game_updates import (
    rebuild_match_capture_game_v1,
    truncate_match_capture_game_plays_v1,
)
from skatmind.match_workspace_contracts import MatchWorkspaceV1
from skatmind.match_workspace_operations import (
    MatchWorkspaceChangeResultV1,
    set_match_workspace_observed_game_v1,
)
from skatmind.observed_game_contracts import ObservedGameRecordV1
from skatmind.observed_trace_diagnostics import (
    ObservedTraceDiagnostic,
    find_observed_trace_warning,
)
from skatmind.rules import get_trick_points, get_trick_winner


@dataclass(frozen=True, slots=True)
class RecoveryTrick:
    number: int
    winner_player_id: str
    points: int


@dataclass(frozen=True, slots=True)
class MatchRecoveryCandidate:
    change: MatchWorkspaceChangeResultV1
    game: ObservedGameRecordV1
    retained_play_count: int
    removed_play_count: int
    removed_commentary_count: int
    removed_response_count: int
    changed_tricks: tuple[tuple[RecoveryTrick, RecoveryTrick], ...]
    warning: ObservedTraceDiagnostic | None


def recovery_tricks(game: ObservedGameRecordV1) -> tuple[RecoveryTrick, ...]:
    if game.declaration is None:
        return ()
    result = []
    for start in range(0, len(game.plays) - 2, 3):
        plays = game.plays[start:start + 3]
        cards = [play.card for play in plays]
        winner = get_trick_winner(cards, game.declaration.game_type)
        result.append(RecoveryTrick(start // 3 + 1, plays[winner].player_id,
                                    get_trick_points(cards)))
    return tuple(result)


def build_match_recovery_candidate(
    workspace: MatchWorkspaceV1, *, position: int, play_index: int,
    action: Literal["replace", "rewind"], card: str | None = None,
) -> MatchRecoveryCandidate:
    """One private candidate; no Capture enum extension and no persistence.

    Replacement retains actor, index, timecode, full suffix and annotations.
    Rewind reuses the canonical suffix/annotation removal builder.
    """
    if type(position) is not int or not 1 <= position <= 36:
        raise ValueError("position must identify one Match Game.")
    game = workspace.slots[position - 1].observed_game
    if game is None or type(play_index) is not int or not 1 <= play_index <= len(game.plays):
        raise ValueError("play_index must identify one accepted Play.")
    removed_notes: tuple[str, ...] = ()
    removed_links: tuple[str, ...] = ()
    if action == "replace":
        plays = list(game.plays)
        plays[play_index - 1] = replace(plays[play_index - 1], card=card)
        candidate = rebuild_match_capture_game_v1(workspace, game, plays=tuple(plays))
    elif action == "rewind" and card is None:
        candidate, removed_notes, removed_links = truncate_match_capture_game_plays_v1(
            workspace, game, target_play_count=play_index - 1,
        )
    else:
        raise ValueError("action must identify one supported recording correction.")
    change = set_match_workspace_observed_game_v1(
        workspace, candidate, expected_revision=workspace.revision,
    )
    before, after = recovery_tricks(game), recovery_tricks(candidate)
    return MatchRecoveryCandidate(
        change, candidate, len(candidate.plays), len(game.plays) - len(candidate.plays),
        len(removed_notes), len(removed_links),
        tuple((old, new) for old, new in zip(before, after, strict=False) if old != new),
        None if candidate.declaration is None else find_observed_trace_warning(
            candidate.plays, candidate.declaration.game_type),
    )
