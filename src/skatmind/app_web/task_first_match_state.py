from __future__ import annotations

from skatmind.capture_web.state import (
    _decision_preparation_summary,
    _game_summary,
    _participant_summary,
    _selected_report_details,
    build_match_analysis_report_summary_v1,
)
from skatmind.capture_web.timecodes import format_media_timecode_v1
from skatmind.match_player_statistics_preparation import (
    build_match_player_statistics_preparation_v1,
)

from .recorded_trick_progress import project_match_trick_progress
from .unplayed_card_summary import project_unplayed_cards


def build_task_first_match_page_state_v1(context, view, *, report_id=None):
    """Project entered facts and retained Reports; never materialize or execute on GET."""
    workspace = context.workspace
    definition = workspace.match_definition
    statistics = build_match_player_statistics_preparation_v1(definition)
    reports = tuple(report for report in context.capture.report_store.list()
                    if report.match_id == definition.match_id
                    and report.workspace_revision == workspace.revision)
    selected = next((report for report in reports if report.report_id == report_id), None)
    materialization = next((report for report in reversed(reports)
                            if report.report_kind == "materialization"), None)
    list_available = (materialization is not None and materialization.value.materialization
                      .historical_list_materialization.status == "available")
    game = workspace.slots[view.selected_position - 1].observed_game
    recorded = project_match_trick_progress(workspace, view.selected_position)
    return {
        "selected_position": view.selected_position,
        "recorded_progress": recorded,
        "unplayed_cards": project_unplayed_cards(
            recorded, None if game is None else game.declaration),
        "workspace_revision": workspace.revision,
        "match": {"match_id": definition.match_id, "title": definition.title,
                  "game_platform": definition.game_platform,
                  "external_match_id": definition.external_match_id,
                  "played_at": definition.played_at},
        "source": {"source_kind": definition.source.source_kind,
                   "source_url": definition.source.source_url,
                   "source_title": definition.source.source_title,
                   "source_channel_name": definition.source.source_channel_name,
                   "match_timecode": format_media_timecode_v1(definition.source.match_timecode)},
        "participants": [_participant_summary(player, preparation)
                         for player, preparation in zip(definition.participants,
                             statistics.participant_contexts, strict=True)],
        "progress": view.selected.workspace_progress.to_dict(),
        "position_view": view.selected.to_dict(),
        "game": _game_summary(game),
        "decision_preparation": _decision_preparation_summary(workspace, view.selected_position),
        "reports": [build_match_analysis_report_summary_v1(report, selected=report is selected)
                    for report in reports],
        "selected_report": None if selected is None else _selected_report_details(selected),
        "download_availability": {
            "report_result": selected is not None and selected.report_kind != "materialization"
                             and selected.value.status == "executed",
            "materialization": materialization is not None,
            "historical_games": materialization is not None,
            "training_sources": materialization is not None,
            "historical_list_input": list_available,
            "historical_list_aggregation": list_available,
        },
    }
