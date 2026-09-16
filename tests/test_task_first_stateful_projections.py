from dataclasses import FrozenInstanceError

import pytest
from test_historical_game import build_historical_input
from test_match_workspace_contracts import _definition
from test_session_transitions import _complete_retrospective_session

from skatmind.app_web.task_first_projections import (
    project_task_first_learning_v1,
    project_task_first_match_v1,
    project_task_first_session_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.session_transitions import apply_session_command_v1, create_session_state_v1


def session_states():
    completed = _complete_retrospective_session(build_historical_input())
    state = create_session_state_v1(session_id=completed.session_id, players=completed.players,
                                    capture_mode=completed.initial_capture_mode)
    yield state
    for record in completed.command_log:
        state = apply_session_command_v1(state, record.command).state
        yield state


def test_all_session_phases_are_projected_from_exact_replay_without_mutation():
    phases = set()
    for state in session_states():
        before = state.to_dict()
        view = project_task_first_session_v1(state)
        phases.add(view.facts.phase)
        assert view == project_task_first_session_v1(state)
        assert state.to_dict() == before
        with pytest.raises(FrozenInstanceError):
            view.entry_player_id = "changed"
    assert phases == {"setup", "deal", "declaration", "skat_and_discard", "play", "ended"}


def test_match_positions_are_exact_ordered_and_nonmutating():
    workspace = create_match_workspace_v1(_definition())
    before = workspace.to_dict()
    view = project_task_first_match_v1(workspace, selected_position=17)
    assert tuple(item.match_position for item in view.positions) == tuple(range(1, 37))
    assert view.selected_position == 17 and view.next_position == 1
    assert view.workflow.primary_action == "start_game"
    assert workspace.to_dict() == before
    assert view == project_task_first_match_v1(workspace, selected_position=17)


def test_learning_guidance_uses_only_selections_and_exact_source_status():
    state = {"matches": [], "current_match_snapshots": [], "strategy_sources": []}
    assert project_task_first_learning_v1(state).status == "add"
    state["matches"] = [{}]
    assert project_task_first_learning_v1(state).status == "select"
    state["current_match_snapshots"] = [{}]
    state["matches"] = [{"current_match_snapshot_id": "selected"}]
    assert project_task_first_learning_v1(state).primary_action == "prepare_learning_artifacts"
    state["strategy_sources"] = [{"binding_status": "non_current"}]
    assert project_task_first_learning_v1(state).primary_action is None
