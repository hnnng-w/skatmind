"""Two narrow trusted-source adapters, called inside existing page snapshot locks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .recorded_decision_context import project_recorded_decision_context, source_player_labels

if TYPE_CHECKING:
    from skatmind.api.v1 import ResultDocumentV1
    from skatmind.match_analysis_contracts import MatchAnalysisReportV1
    from skatmind.match_workspace_contracts import MatchWorkspaceV1

    from .session_recorded_review import RecordedReviewSourceV1


def session_decision_context(source: RecordedReviewSourceV1 | None, result: ResultDocumentV1):
    if source is None:
        return None
    checkpoint = source.decision.checkpoint
    state = source.document.state
    matches = (checkpoint.session_id == state.session_id
               and checkpoint.relative_player_map["me"] == checkpoint.acting_player_id)
    players = source_player_labels(state.players, checkpoint.relative_player_map) if matches else {}
    return project_recorded_decision_context(
        result.document, players=players,
        trick_number=checkpoint.trick_number if matches else None,
        play_index=checkpoint.play_index if matches else None,
    )


def match_decision_context(report: MatchAnalysisReportV1 | None, workspace: MatchWorkspaceV1):
    if (report is None or report.report_kind != "decision_analysis"
            or report.value.status != "executed"):
        return None
    value = report.value
    binding = value.profile_binding
    definition = workspace.match_definition
    game = workspace.slots[report.match_position - 1].observed_game
    matches = (report.match_id == definition.match_id
               and report.workspace_revision == workspace.revision
               and game is not None and value.game_id == game.game_id)
    players = source_player_labels(definition.participants, {
        "me": binding.acting_player_id, "left": binding.left_opponent_player_id,
        "right": binding.right_opponent_player_id,
    }) if matches else {}
    return project_recorded_decision_context(
        value.result.document, players=players,
        game_number=report.match_position if matches else None,
        trick_number=(report.decision_index - 1) // 3 + 1 if matches else None,
        play_index=(report.decision_index - 1) % 3 + 1 if matches else None,
    )
