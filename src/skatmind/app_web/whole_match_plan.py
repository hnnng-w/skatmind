"""Inventory of actual perspective plays. Only before-card evidence decides eligibility."""

from dataclasses import dataclass

from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
from skatmind.match_decision_review_preparation import (
    _build_match_decision_states_from_reconstruction_v1,
)
from skatmind.match_observed_reconstruction import build_match_observed_game_reconstruction_v1
from skatmind.match_workspace_contracts import _validate_match_workspace_with_traces_v1
from skatmind.rollout_derivation import SETTLEMENT_INPUTS


@dataclass(frozen=True, slots=True)
class OwnPlay:
    position: int
    decision: int
    actual: str
    reason: str
    missing: tuple[str, ...]

    @property
    def key(self):
        return f"{self.position}:{self.decision}"

    def options(self, settings, supplements):
        if self.reason:
            return None
        supplied = {}
        if settings.objective == "complete_settlement":
            for name in self.missing:
                if name not in supplements:
                    return None
                supplied[name] = supplements[name]
        return MatchDecisionAnalysisOptionsV1(recommendation_method="whole_game_rollout",
            rollout_settings=settings, settlement_supplements=supplied, use_profile_presets=False)


def own_plays(workspace):
    traces = dict(_validate_match_workspace_with_traces_v1(workspace))
    perspective = workspace.match_definition.perspective_player_id
    rows = []
    for slot in workspace.slots:
        game = slot.observed_game
        if game is None:
            continue
        trace = traces[slot.match_position]
        reconstruction = build_match_observed_game_reconstruction_v1(game, validated_trace=trace)
        snapshots, skips, _ = _build_match_decision_states_from_reconstruction_v1(
            reconstruction, source_played_at=workspace.match_definition.played_at)
        by_index = {s.decision_index: s for s in snapshots}
        skipped = {s.decision_index: s.reason for s in skips}
        for play in trace.plays:
            if play.player_id != perspective:
                continue
            reason = skipped.get(play.decision_index, "")
            missing = ()
            if not reason:
                state = by_index[play.decision_index].visible_state
                # This snapshot has the exact, shrinking playable hand, not an editor's
                # candidate list. Actor has played exactly once per completed trick.
                if len(state.own_hand) != 10 - len(state.completed_tricks):
                    raise ValueError("Expected the full decision-time hand.")
                if state.legal_cards == (play.card,):
                    reason = "forced"
                elif state.game_type == "null":
                    reason = "unsupported_game_type"
                else:
                    missing = tuple(k for k in SETTLEMENT_INPUTS
                                    if getattr(state.declaration, k) is None)
            rows.append(OwnPlay(slot.match_position, play.decision_index, play.card,
                                reason, missing))
    return tuple(rows)
