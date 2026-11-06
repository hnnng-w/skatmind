"""Pure saved-Session coverage. Never collect Checkpoints or execute analysis."""

from dataclasses import dataclass

from .session_decision_observation import observe_session_decision_checkpoint_v1
from .session_transitions import replay_session_state_v1


@dataclass(frozen=True, slots=True)
class SavedSessionCoverage:
    decisions: tuple
    recorded_plays: int
    own_plays: int
    missing_checkpoints: int
    unavailable: tuple
    has_perspective: bool
    game_id: str


def project_saved_session_coverage(document):
    """Greatest eligible revision, then first canonical saved variant on a tie."""
    state = document.state
    selected = {}
    unavailable = dict.fromkeys(("pending", "future", "diverged", "ended_without_play"), 0)
    for index, checkpoint in enumerate(document.decision_checkpoints):
        observation = observe_session_decision_checkpoint_v1(state=state, checkpoint=checkpoint)
        if observation.status != "observed":
            unavailable[observation.status] += 1
            continue
        if checkpoint.acting_player_id != state.local_player_id:
            continue
        revision = observation.observed_play_revision
        previous = selected.get(revision)
        if previous is None or previous[1].source_revision < checkpoint.source_revision:
            selected[revision] = (index, checkpoint, observation)
    facts = replay_session_state_v1(state)
    end = facts.recording_rule_end
    plays = facts.plays if end is None else facts.plays[:end.decisive_play_count]
    own = sum(player == state.local_player_id for player, _card in plays)
    decisions = tuple(sorted(selected.values(), key=lambda row: row[1].decision_index))
    return SavedSessionCoverage(decisions, len(plays), own, own - len(decisions),
                                tuple(unavailable.items()), state.local_player_id is not None,
                                facts.game_id or state.session_id)
