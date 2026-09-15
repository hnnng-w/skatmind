from __future__ import annotations

from collections.abc import Mapping

from skatmind.match_capture_position_view import build_match_capture_position_view_v1
from skatmind.match_workspace_contracts import MatchWorkspaceV1
from skatmind.session_commands import SESSION_COMMAND_ALLOWED_PHASES, SESSION_COMMAND_KINDS
from skatmind.session_contracts import SessionStateV1
from skatmind.session_transitions import replay_session_state_v1

from .task_first_contracts import TaskFirstMatchV1, TaskFirstSessionV1, TaskFirstWorkflowV1


def project_task_first_session_v1(state: SessionStateV1) -> TaskFirstSessionV1:
    facts = replay_session_state_v1(state)
    allowed = tuple(kind for kind in SESSION_COMMAND_KINDS
                    if state.phase in SESSION_COMMAND_ALLOWED_PHASES[kind])
    player_id = facts.next_player_id
    destination = "player_hand"
    action = None
    task = "task.session.next.complete"
    completed = ["result.players"]
    if facts.declaration is not None:
        completed.append("task.command.set_declaration")
    if facts.played_card_count:
        completed.append("task.command.record_play")
    if state.phase in {"setup", "deal"}:
        action = "record_dealt_card"
        player_id = next((player.player_id for player in facts.players
                          if (state.capture_mode == "retrospective"
                              or player.player_id == state.local_player_id)
                          and len(facts.initial_hand_for(player.player_id) or ()) < 10), None)
        if player_id is None:
            destination = "skat"
    elif facts.game_id is None and "set_game_metadata" in allowed:
        action = "set_game_metadata"
    elif state.phase == "declaration":
        action = "set_declarer" if facts.declarer_player_id is None else "set_declaration"
    elif state.phase == "skat_and_discard":
        action = "record_dealt_card" if len(facts.known_skat) < 2 else "record_discard"
        destination = "skat"
        player_id = facts.declarer_player_id
    elif state.phase == "play":
        if facts.played_card_count == 30:
            action = "set_game_end"
        elif any(item.path == "/exact_public_hands" and item.blocks_position_export
                 for item in state.validation.diagnostics):
            action = "set_public_hand"
            player_id = facts.declarer_player_id
        else:
            action = "record_play"
    if action is not None:
        task = f"task.session.next.{action}"
    position = state.validation.position_export.status == "available"
    historical = state.validation.historical_export.status == "available"
    blockers = () if position or historical else ("task.session.analysis_blocked",)
    return TaskFirstSessionV1(
        TaskFirstWorkflowV1(
            state.phase, task, action, tuple(completed),
            tuple(kind for kind in allowed if kind != action), blockers,
            ("task.session.optional", "task.session.analysis", "task.session.corrections"),
            ("task.technical",),
        ), facts, player_id, destination, position, historical,
    )


def project_task_first_match_v1(
    workspace: MatchWorkspaceV1, *, selected_position: int,
) -> TaskFirstMatchV1:
    positions = tuple(build_match_capture_position_view_v1(workspace, match_position=position)
                      for position in range(1, 37))
    if type(selected_position) is not int or not 1 <= selected_position <= 36:
        raise ValueError("selected_position must be from 1 through 36.")
    selected = positions[selected_position - 1]
    next_position = next((view.match_position for view in positions
                          if view.game_state not in {"passed_deal", "play_complete"}), None)
    game = workspace.slots[selected_position - 1].observed_game
    completed = []
    if selected.slot_kind == "empty":
        action = "start_game"
    elif game is None:
        action = None
    else:
        completed.append("start_game")
        if game.perspective_initial_hand is not None:
            completed.append("set_perspective_hand")
        if game.declaration is not None:
            completed.append("set_declaration")
        if game.original_skat is not None:
            completed.append("set_original_skat")
        if game.discarded_cards is not None:
            completed.append("set_discarded_cards")
        # Unknown evidence is optional. It must not trap an observer in a wizard.
        action = "set_declaration" if game.declaration is None else (
            "append_plays" if selected.can_record_play else None
        )
    task = f"task.match.next.{action or selected.game_state}"
    return TaskFirstMatchV1(
        TaskFirstWorkflowV1(
            selected.game_state, task, action, tuple(completed),
            ("mark_passed_deal",) if game is None else (
                "set_perspective_hand", "set_original_skat", "set_discarded_cards",
                "set_commentary", "set_response_link",
            ),
            tuple(f"task.match.blocker.{reason}" for reason in selected.record_play_blockers),
            ("task.match.evidence", "task.match.metadata", "task.match.statistics",
             "task.match.analysis", "task.match.corrections"), ("task.technical",),
        ), positions, selected_position, next_position,
    )


def project_task_first_learning_v1(state: Mapping[str, object]) -> TaskFirstWorkflowV1:
    """Order existing Catalog selections and source classifications without preparing."""
    matches = state["matches"]
    selections = state["current_match_snapshots"]
    sources = state["strategy_sources"]
    completed = []
    if not matches:
        task, action = "add", None
    elif not selections:
        task, action = "select", None
        completed.append("task.learning.added")
    elif any(source["binding_status"] == "non_current" for source in sources):
        task, action = "sources", None
        completed.extend(("task.learning.added", "task.learning.selected"))
    else:
        task, action = "build", "prepare_learning_artifacts"
        completed.extend(("task.learning.added", "task.learning.selected"))
    return TaskFirstWorkflowV1(
        task, f"task.learning.next.{task}", action, tuple(completed),
        ("import_match_workspace", "select_current_snapshot", "reload_corpus"),
        () if action else (f"task.learning.next.{task}",),
        ("task.learning.settings", "task.learning.sources", "task.learning.alternatives"),
        ("task.technical",),
    )
