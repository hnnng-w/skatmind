"""Private public-Play projection. Callers supply one locked accepted snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from skatmind.match_recording_recovery import recovery_tricks
from skatmind.match_workspace_contracts import MatchWorkspaceV1
from skatmind.observed_trace_diagnostics import (
    ObservedTraceDiagnostic,
    find_observed_trace_warning,
)
from skatmind.session_projection import SessionProjectionV1


@dataclass(frozen=True, slots=True)
class RecordedPlayer:
    player_id: str
    player_label: str | None
    seat: str
    fallback_number: int


@dataclass(frozen=True, slots=True)
class CapturedTotal:
    tricks: int = 0
    points: int = 0


@dataclass(frozen=True, slots=True)
class RecordedPrefix:
    players: tuple[tuple[str, CapturedTotal], ...]
    declarer: CapturedTotal | None
    defenders: CapturedTotal | None


@dataclass(frozen=True, slots=True)
class RecordedPlay:
    decision_index: int
    player_id: str
    card: str


@dataclass(frozen=True, slots=True)
class RecordedTrick:
    number: int
    plays: tuple[RecordedPlay, ...]
    winner_player_id: str | None
    points: int | None
    prefix: RecordedPrefix | None


@dataclass(frozen=True, slots=True)
class RecordedTrickProgress:
    players: tuple[RecordedPlayer, ...]
    game_type: str | None
    declarer_player_id: str | None
    status: str
    tricks: tuple[RecordedTrick, ...]
    warning: ObservedTraceDiagnostic | None = None

    @property
    def completed_count(self) -> int:
        return sum(trick.prefix is not None for trick in self.tricks)

    @property
    def latest(self) -> RecordedPrefix | None:
        if self.game_type is None:
            return None
        return next((trick.prefix for trick in reversed(self.tricks) if trick.prefix is not None),
                    _prefix(tuple((p.player_id, CapturedTotal()) for p in self.players),
                            self.declarer_player_id))


def _prefix(players, declarer_id):
    declarer = next((value for player_id, value in players if player_id == declarer_id), None)
    defenders = None if declarer is None else CapturedTotal(
        sum(value.tricks for player_id, value in players if player_id != declarer_id),
        sum(value.points for player_id, value in players if player_id != declarer_id))
    return RecordedPrefix(players, declarer, defenders)


def _accumulate(players, declarer_id, completed, incomplete):
    """Credit each existing completed-Trick value once; retain immutable prefixes."""
    totals = {player.player_id: CapturedTotal() for player in players}
    rows = []
    index = 0
    source = (*completed, (incomplete, None, None)) if incomplete else completed
    for plays, winner, points in source:
        public_plays = tuple(RecordedPlay(index + offset, player_id, card)
                             for offset, (player_id, card) in enumerate(plays, 1))
        prefix = None
        if winner is not None:
            prior = totals[winner]
            totals[winner] = CapturedTotal(prior.tricks + 1, prior.points + points)
            prefix = _prefix(tuple(totals.items()), declarer_id)
        rows.append(RecordedTrick(len(rows) + 1, public_plays, winner, points, prefix))
        index += len(plays)
    return tuple(rows)


def project_session_trick_progress(facts: SessionProjectionV1) -> RecordedTrickProgress:
    """Adapt the replay already retained by the Session page, never replay per row."""
    players = tuple(RecordedPlayer(p.player_id, p.player_label, p.seat, index)
                    for index, p in enumerate(facts.players, 1))
    status = ("undeclared" if facts.declaration is None else "ended" if facts.game_end_reason
              else "complete" if facts.played_card_count == 30 else "active")
    return RecordedTrickProgress(
        players, None if facts.declaration is None else facts.declaration.game_type,
        facts.declarer_player_id, status,
        _accumulate(players, facts.declarer_player_id,
                    tuple((t.plays, t.winner_player_id, t.trick_points)
                          for t in facts.completed_tricks),
                    () if facts.incomplete_trick is None else facts.incomplete_trick.plays))


def project_match_trick_progress(
    workspace: MatchWorkspaceV1, position: int,
) -> RecordedTrickProgress:
    """Use accepted Game seats and recovery rules, never reconstruct hidden hands."""
    slot = workspace.slots[position - 1]
    game = slot.observed_game
    if game is None:
        return RecordedTrickProgress((), None, None, slot.slot_kind, ())
    names = {p.player_id: (p.player_label, index)
             for index, p in enumerate(workspace.match_definition.participants, 1)}
    players = tuple(RecordedPlayer(p.player_id, names[p.player_id][0], p.seat,
                                   names[p.player_id][1]) for p in game.players)
    completed = recovery_tricks(game)
    game_type = None if game.declaration is None else game.declaration.game_type
    return RecordedTrickProgress(
        players, game_type, game.declarer_player_id,
        "undeclared" if game_type is None else "complete" if len(game.plays) == 30 else "active",
        _accumulate(players, game.declarer_player_id,
                    tuple((tuple((p.player_id, p.card)
                                 for p in game.plays[(t.number - 1)*3:t.number*3]),
                           t.winner_player_id, t.points) for t in completed),
                    tuple((p.player_id, p.card) for p in game.plays[len(completed)*3:])),
        None if game_type is None else find_observed_trace_warning(game.plays, game_type))
