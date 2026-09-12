from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from skatmind.deck import get_full_deck
from skatmind.errors import SkatMindValidationError
from skatmind.match_recording_recovery import (
    MatchRecoveryCandidate,
    build_match_recovery_candidate,
)
from skatmind.match_workspace_contracts import MatchWorkspaceV1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.observed_trace_diagnostics import ObservedTraceDiagnostic, ObservedTraceError

from .managed_item_storage import validate_managed_direct_child_path_v1
from .workflow_state import StaleFrontendWorkflowRevisionError

if TYPE_CHECKING:
    from .match_frontend import UnifiedMatchContextV1

RECOVERY_ROUTES = tuple(f"/matches/recovery/{action}" for action in (
    "select", "preview", "apply", "cancel",
))


class MatchRecoveryConflict(StaleFrontendWorkflowRevisionError):
    def __init__(self, reason: str = "stale") -> None:
        super().__init__()
        self.reason = reason


@dataclass(frozen=True, slots=True)
class MatchRecoverySelection:
    token: str
    source: MatchWorkspaceV1
    content_fingerprint: str
    position: int
    game_id: str
    play_index: int
    action: Literal["replace", "rewind"]
    created_at: float


@dataclass(frozen=True, slots=True)
class MatchRecoveryPreview:
    selection: MatchRecoverySelection
    card: str | None
    candidate: MatchRecoveryCandidate
    apply_token: str


@dataclass(slots=True)
class MatchRecoveryState:
    """Capture-lock-owned, bounded private state, discarded on reload/change."""

    selections: dict[str, MatchRecoverySelection] = field(default_factory=dict)
    selected: MatchRecoverySelection | None = None
    preview: MatchRecoveryPreview | None = None
    diagnostic: ObservedTraceDiagnostic | None = None
    diagnostic_source: MatchWorkspaceV1 | None = None
    proposed_cards: tuple[str, ...] = ()
    proposed_index: int | None = None
    notice: str | None = None

    def clear(self) -> None:
        self.selections.clear()
        self.selected = None
        self.preview = None
        self.diagnostic = None
        self.diagnostic_source = None
        self.proposed_cards = ()
        self.proposed_index = None
        self.notice = None


def recording_selections(context: UnifiedMatchContextV1) -> tuple[MatchRecoverySelection, ...]:
    """Issue at most sixty exact-source entry actions without touching Product bytes."""
    state = context.recovery
    now = time.monotonic()
    state.selections = {
        token: item for token, item in state.selections.items()
        if item.source == context.workspace and item.position == context.selected_position
        and now - item.created_at < 1800
    }
    game = context.workspace.slots[context.selected_position - 1].observed_game
    if game is None:
        return ()
    for play in game.plays:
        for action in ("replace", "rewind"):
            if any(item.play_index == play.decision_index and item.action == action
                   for item in state.selections.values()):
                continue
            item = MatchRecoverySelection(
                secrets.token_hex(32), context.workspace, context.capture.content_fingerprint,
                context.selected_position, game.game_id, play.decision_index, action, now,
            )
            state.selections[item.token] = item
    return tuple(state.selections.values())


def _fresh(context: UnifiedMatchContextV1, selection: MatchRecoverySelection) -> None:
    game = context.workspace.slots[context.selected_position - 1].observed_game
    if (context.workspace != selection.source or selection.position != context.selected_position
            or context.capture.content_fingerprint != selection.content_fingerprint
            or game is None or game.game_id != selection.game_id
            or time.monotonic() - selection.created_at >= 1800):
        raise MatchRecoveryConflict()
    try:
        validate_managed_direct_child_path_v1(
            context.category_root, context.path, expected_kind="file")
        loaded = load_match_workspace_file_v1(context.path).document
        fresh = (loaded.content_fingerprint == selection.content_fingerprint
                 and loaded.workspace == selection.source)
    except (OSError, ValueError, SkatMindValidationError):
        fresh = False
    if not fresh:
        raise MatchRecoveryConflict("file_changed")


def _resolve(context: UnifiedMatchContextV1, token: str) -> MatchRecoverySelection:
    selection = context.recovery.selections.get(token)
    if selection is None:
        raise MatchRecoveryConflict()
    _fresh(context, selection)
    return selection


def select_match_recovery(context: UnifiedMatchContextV1, token: str) -> None:
    with context.capture.lock:
        selection = _resolve(context, token)
        context.recovery.selected = selection
        context.recovery.preview = None
        if selection.action == "rewind":
            preview_match_recovery(context, token)


def preview_match_recovery(
    context: UnifiedMatchContextV1, token: str, *, card: str | None = None,
) -> None:
    with context.capture.lock:
        selection = _resolve(context, token)
        state = context.recovery
        state.preview = None
        state.selected = selection
        state.diagnostic = None
        try:
            candidate = build_match_recovery_candidate(
                context.workspace, position=selection.position, play_index=selection.play_index,
                action=selection.action, card=card,
            )
        except ObservedTraceError as error:
            retain_recording_error(context, error, (card,), selection.play_index)
            raise
        state.preview = MatchRecoveryPreview(selection, card, candidate, secrets.token_hex(32))
        state.diagnostic = None
        state.notice = None


def apply_match_recovery(context: UnifiedMatchContextV1, token: str) -> str:
    """Rebuild at Apply; one CAS Save; failed saves never publish the candidate."""
    with context.capture.lock:
        state = context.recovery
        preview = state.preview
        if preview is None or not secrets.compare_digest(preview.apply_token, token):
            raise MatchRecoveryConflict()
        selection = _resolve(context, preview.selection.token)
        candidate = build_match_recovery_candidate(
            context.workspace, position=selection.position, play_index=selection.play_index,
            action=selection.action, card=preview.card,
        )
        if candidate != preview.candidate:
            raise MatchRecoveryConflict()
        if candidate.change.status == "unchanged":
            state.clear()
            state.notice = "unchanged"
            return "unchanged"
        try:
            status = context.capture.save_candidate(candidate.change.workspace)
        except OSError as error:
            raise MatchRecoveryConflict("save_failed") from error
        if status == "conflict":
            raise MatchRecoveryConflict("file_changed")
        context.capture.report_store.clear()
        context.last_result = None
        context.transfer_notice = None
        state.clear()
        state.notice = "saved"
        return "saved"


def retain_recording_error(context, error, cards=(), proposed_index=None):
    state = context.recovery
    state.diagnostic = error.diagnostic
    state.diagnostic_source = context.workspace
    state.proposed_cards = tuple(card for card in cards if card in get_full_deck())[:30]
    state.proposed_index = proposed_index
    state.notice = None
