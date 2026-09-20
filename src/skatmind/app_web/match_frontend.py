from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skatmind.capture_web.analysis import (
    execute_match_capture_web_analysis_v1,
    get_current_match_analysis_report_v1,
    get_current_materialization_report_v1,
)
from skatmind.capture_web.context import MatchCaptureWebContextV1
from skatmind.capture_web.contracts import MatchCaptureWebResultV1
from skatmind.capture_web.operations import (
    apply_match_capture_web_operation_v1,
    create_match_capture_workspace_v1,
    reload_match_capture_workspace_v1,
)
from skatmind.capture_web.report_store import MatchAnalysisReportStoreV1
from skatmind.capture_web.state import build_match_capture_web_state_v1
from skatmind.errors import SkatMindInvariantError
from skatmind.match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisResultV1,
)
from skatmind.match_analysis_exports import (
    build_match_historical_game_collection_export_v1,
    build_match_historical_list_aggregation_export_v1,
    build_match_historical_list_input_export_v1,
    build_match_materialization_summary_export_v1,
    build_match_report_result_export_v1,
    build_match_training_source_collection_export_v1,
)
from skatmind.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)
from skatmind.match_workspace_persistence import (
    _build_match_workspace_file_bytes_v1,
    save_match_workspace_file_v1,
)
from skatmind.match_workspace_persistence_codec import resume_match_workspace_document_v1
from skatmind.observed_trace_diagnostics import ObservedTraceError

from .managed_item_contracts import DiscoveredManagedItemV1
from .managed_item_storage import (
    build_managed_item_storage_path_v1,
    validate_managed_direct_child_path_v1,
)
from .match_recovery import MatchRecoveryState, retain_recording_error
from .operation_feedback import PendingOperationFeedback, feedback_source
from .operation_feedback_mapping import match_operation_message

_SAFE_WORKSPACE_FILENAME = "managed-match.json"
UNIFIED_MATCH_EXPORT_KINDS = (
    "materialization",
    "historical_games",
    "training_sources",
    "historical_list_input",
    "historical_list_aggregation",
)


@dataclass(slots=True, kw_only=True)
class UnifiedMatchContextV1:
    """One active managed Match over the unchanged Capture operation context."""

    category_root: Path = field(repr=False)
    path: Path = field(repr=False)
    handle: str
    capture: MatchCaptureWebContextV1 = field(repr=False)
    selected_position: int = 1
    retired: bool = field(default=False, repr=False)
    position_generation: int = field(default=0, repr=False)
    last_result: MatchCaptureWebResultV1 | None = field(default=None, repr=False)
    operation_feedback: PendingOperationFeedback = field(
        default_factory=PendingOperationFeedback, repr=False)
    transfer_notice: str | None = field(default=None, repr=False)
    transfer_feedback_key: str | None = field(default=None, repr=False)
    recovery: MatchRecoveryState = field(default_factory=MatchRecoveryState, repr=False)
    card_entry_key: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.category_root, Path) or not isinstance(self.path, Path):
            raise ValueError("Managed Match paths must be private Paths.")
        if self.path.parent != self.category_root:
            raise ValueError("Managed Match must be one direct category child.")
        if type(self.handle) is not str or len(self.handle) != 64:
            raise ValueError("handle must be one opaque managed handle.")
        if type(self.capture) is not MatchCaptureWebContextV1:
            raise ValueError("capture must be an exact Match Capture Web context.")
        if not 1 <= self.selected_position <= 36:
            raise ValueError("selected_position must be from 1 through 36.")
        if self.transfer_notice is not None and (
            type(self.transfer_notice) is not str or not self.transfer_notice
        ):
            raise ValueError("transfer_notice must be null or non-empty text.")

    @property
    def workspace(self):
        return self.capture.workspace

    def require_attached(self):
        if self.retired:
            from .workflow_state import StaleFrontendWorkflowRevisionError
            raise StaleFrontendWorkflowRevisionError()


def _context(
    *,
    category_root: Path,
    path: Path,
    handle: str,
    capture: MatchCaptureWebContextV1,
    last_result: MatchCaptureWebResultV1 | None = None,
) -> UnifiedMatchContextV1:
    return UnifiedMatchContextV1(
        category_root=category_root,
        path=path,
        handle=handle,
        capture=capture,
        last_result=last_result,
    )


def create_unified_match_v1(
    category_root: Path,
    *,
    handle: str,
    values: Mapping[str, object],
) -> UnifiedMatchContextV1:
    match_id = values.get("match_id")
    if type(match_id) is not str or not match_id:
        raise ValueError("match_id is required.")
    path = build_managed_item_storage_path_v1(
        category_root,
        family="matches",
        product_id=match_id,
    )
    if os.path.lexists(path):
        raise FileExistsError("A managed Match already uses this Product identity.")
    capture = MatchCaptureWebContextV1.open(path)
    result = create_match_capture_workspace_v1(capture, values)
    if result.status != "applied" or capture.workspace is None:
        raise SkatMindInvariantError("New managed Match was not saved exactly once.")
    return _context(
        category_root=category_root,
        path=path,
        handle=handle,
        capture=capture,
        last_result=result,
    )


def import_unified_match_v1(
    category_root: Path,
    *,
    handle: str,
    document: Mapping[str, object],
) -> UnifiedMatchContextV1:
    resumed = resume_match_workspace_document_v1(document)
    persistence = resumed.document
    match_id = persistence.workspace.match_definition.match_id
    path = build_managed_item_storage_path_v1(
        category_root,
        family="matches",
        product_id=match_id,
    )
    if os.path.lexists(path):
        raise FileExistsError("A managed Match already uses this Product identity.")
    saved = save_match_workspace_file_v1(
        path,
        persistence,
        expected_content_fingerprint=None,
    )
    if saved.status != "saved":
        raise SkatMindInvariantError("Imported managed Match was not saved exactly once.")
    return _context(
        category_root=category_root,
        path=path,
        handle=handle,
        capture=MatchCaptureWebContextV1.open(path),
    )


def open_unified_match_v1(
    category_root: Path,
    entry: DiscoveredManagedItemV1,
) -> UnifiedMatchContextV1:
    if entry.summary.family != "matches" or entry.summary.status != "available":
        raise ValueError("Only one available discovered Match can be opened.")
    validate_managed_direct_child_path_v1(
        category_root,
        entry.path,
        expected_kind="file",
    )
    capture = MatchCaptureWebContextV1.open(entry.path)
    if (
        capture.workspace is None
        or capture.workspace.match_definition.match_id
        != entry.summary.semantic_product_id
    ):
        raise ValueError("Managed Match identity changed after discovery.")
    return _context(
        category_root=category_root,
        path=entry.path,
        handle=entry.summary.handle,
        capture=capture,
    )


def reload_unified_match_v1(
    context: UnifiedMatchContextV1,
) -> MatchCaptureWebResultV1:
    with context.capture.lock:
        context.require_attached()
        context.operation_feedback.begin()
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="file",
        )
        result = reload_match_capture_workspace_v1(
            context.capture,
            selected_position=context.selected_position,
        )
        context.recovery.clear()
        context.card_entry_key = secrets.token_bytes(32)
        context.transfer_notice = None
    context.last_result = result
    return result


def apply_unified_match_operation_v1(
    context: UnifiedMatchContextV1,
    values: Mapping[str, object],
) -> MatchCaptureWebResultV1:
    with context.capture.lock:
        context.require_attached()
        attempt = context.operation_feedback.begin()
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="file",
        )
        position = int(values.get("match_position", context.selected_position))
        select_unified_match_position_v1(context, position)
        # Selection can invalidate a pending receipt; start on this exact Game.
        attempt = context.operation_feedback.begin()
        previous_game = context.workspace.slots[position - 1].observed_game
        context.recovery.diagnostic = None
        try:
            result = apply_match_capture_web_operation_v1(context.capture, values)
        except ObservedTraceError as error:
            cards = values.get("cards", ())
            if isinstance(cards, str):
                cards = cards.replace(",", " ").split()
            game = context.workspace.slots[position - 1].observed_game
            retain_recording_error(context, error, cards,
                len(game.plays) + 1 if values.get("operation") == "append_plays" else None)
            raise
        if result.status == "applied":
            context.recovery.clear()
            context.transfer_notice = None
            context.operation_feedback.publish(attempt, feedback_source(context),
                match_operation_message(context, values.get("operation"), previous_game))
    selected = result.state.get("selected_position")
    if type(selected) is int and 1 <= selected <= 36:
        select_unified_match_position_v1(context, selected)
    context.last_result = result
    return result


def execute_unified_match_analysis_v1(
    context: UnifiedMatchContextV1,
    values: Mapping[str, object],
) -> MatchCaptureWebResultV1:
    with context.capture.lock:
        context.require_attached()
        context.operation_feedback.begin()
        validate_managed_direct_child_path_v1(
            context.category_root,
            context.path,
            expected_kind="file",
        )
    result = execute_match_capture_web_analysis_v1(
        context.capture,
        values,
        browser_form=True,
    )
    with context.capture.lock:
        context.require_attached()
    selected = result.state.get("selected_position")
    if type(selected) is int and 1 <= selected <= 36:
        select_unified_match_position_v1(context, selected)
    context.last_result = result
    return result


def select_unified_match_position_v1(
    context: UnifiedMatchContextV1,
    position: int,
) -> None:
    if type(position) is not int or not 1 <= position <= 36:
        raise ValueError("position must be an integer from 1 through 36.")
    if context.selected_position != position:
        context.recovery.clear()
        context.operation_feedback.begin()
        context.position_generation += 1
    context.selected_position = position


def build_unified_match_state_v1(
    context: UnifiedMatchContextV1,
    *,
    selected_report_id: str | None = None,
) -> dict[str, Any]:
    with context.capture.lock:
        return build_match_capture_web_state_v1(
            context.capture.workspace,
            workspace_filename=_SAFE_WORKSPACE_FILENAME,
            selected_position=context.selected_position,
            report_store=context.capture.report_store,
            selected_report_id=selected_report_id,
        )


def build_unified_match_creation_state_v1() -> dict[str, Any]:
    return build_match_capture_web_state_v1(
        None,
        workspace_filename=_SAFE_WORKSPACE_FILENAME,
        selected_position=1,
        report_store=MatchAnalysisReportStoreV1(),
    )


def get_unified_match_report_v1(
    context: UnifiedMatchContextV1,
    report_id: str,
) -> tuple[str, MatchAnalysisReportV1 | None]:
    return get_current_match_analysis_report_v1(context.capture, report_id)


def get_unified_match_materialization_report_v1(
    context: UnifiedMatchContextV1,
) -> tuple[str, MatchAnalysisReportV1 | None]:
    return get_current_materialization_report_v1(context.capture)


def build_unified_match_workspace_download_v1(
    context: UnifiedMatchContextV1,
) -> bytes:
    with context.capture.lock:
        context.require_attached()
        workspace = context.capture.workspace
        if workspace is None:
            raise ValueError("No managed Match is active.")
        from skatmind.match_workspace_persistence_codec import (
            build_match_workspace_persistence_document_v1,
        )

        return _build_match_workspace_file_bytes_v1(
            build_match_workspace_persistence_document_v1(workspace)
        )


def build_unified_match_report_download_v1(
    context: UnifiedMatchContextV1,
    report_id: str,
    *,
    strategy_source: bool,
) -> tuple[str, bytes]:
    from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
    with context.capture.lock:
        try:
            require_recording_fresh_v1(context, "matches")
        except RecordingOpenConflict:
            context.capture.report_store.clear()
            raise
        status, report = get_unified_match_report_v1(context, report_id)
        if status == "missing" or report is None:
            raise KeyError("Match report is unavailable.")
        if status == "stale":
            raise RuntimeError("Match report revision is stale.")
        root_artifact = build_match_report_result_export_v1(report)
        if not strategy_source:
            return root_artifact.filename, root_artifact.to_bytes()
        if (
            report.report_kind != "decision_analysis"
            or type(report.value) is not MatchDecisionAnalysisResultV1
            or report.value.status != "executed"
        ):
            raise KeyError("Strategy Teacher source is unavailable.")
        exported = build_match_analysis_report_source_export_v1(report)
        filename = (
            f"{root_artifact.filename.removesuffix('.json')}-strategy-source.json"
        )
        return filename, serialize_match_analysis_report_source_export_v1(exported)


def build_unified_match_export_download_v1(
    context: UnifiedMatchContextV1,
    *,
    kind: str,
) -> tuple[str, bytes]:
    if kind not in UNIFIED_MATCH_EXPORT_KINDS:
        raise ValueError("kind must identify one Match export.")
    with context.capture.lock:
        status, report = get_current_materialization_report_v1(context.capture)
        if status == "missing" or report is None:
            raise KeyError("Match materialization is unavailable.")
        if status == "stale":
            raise RuntimeError("Match materialization revision is stale.")
        materialization = report.value.materialization
        if kind == "materialization":
            artifact = build_match_materialization_summary_export_v1(report.value)
        elif kind == "historical_games":
            artifact = build_match_historical_game_collection_export_v1(materialization)
        elif kind == "training_sources":
            artifact = build_match_training_source_collection_export_v1(materialization)
        elif kind == "historical_list_input":
            artifact = build_match_historical_list_input_export_v1(materialization)
        else:
            artifact = build_match_historical_list_aggregation_export_v1(materialization)
        return artifact.filename, artifact.to_bytes()
