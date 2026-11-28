"""Transient assistance owned by one selected game in the unified Match recorder."""

import hmac
from dataclasses import dataclass
from pathlib import Path

from skatmind.live_whole_game import LiveGameOutcome
from skatmind.match_live_position import current_match_position
from skatmind.match_source_coordination import SavedSourceEpoch, match_source_coordinator
from skatmind.match_workspace_contracts import MatchWorkspaceV1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

from .analysis_controls import COUNTS, EFFORTS
from .forced_card_guidance import ForcedCardGuidance, forced_card_guidance
from .frontend_profile_contracts import effort_preferences
from .live_effort_preferences import match_game_key, resolve_recording_effort, submitted_effort
from .managed_item_storage import validate_managed_direct_child_path_v1
from .session_live_advice import evaluate_live_position
from .whole_match_progress import file_identity
from .workflow_state import StaleFrontendWorkflowRevisionError

MATCH_LIVE_ROUTES = ("/matches/live-start", "/matches/live-effort", "/matches/live-stop")


@dataclass(frozen=True, slots=True, eq=False)
class MatchLiveAttempt:
    path: Path
    workspace: MatchWorkspaceV1
    fingerprint: str
    position: int
    selection: int
    control: int
    effort: str
    feedback: object
    source: SavedSourceEpoch
    epoch: int
    file_stamp: str


@dataclass(slots=True)
class MatchLiveAssistance:
    effort: str | None = None
    control_revision: int = 0
    preference_revision: int = 0
    attempt: MatchLiveAttempt | None = None
    outcome: ForcedCardGuidance | LiveGameOutcome | None = None
    unavailable: bool = False
    source: SavedSourceEpoch | None = None
    epoch: int = 0
    file_stamp: str | None = None

    def invalidate(self):
        self.attempt = self.outcome = None
        self.unavailable = False

    def configure(self, effort):
        self.invalidate()
        self.effort = effort
        self.control_revision += 1
        if effort is None:
            self.source = None
            self.file_stamp = None


def match_live_binding(active, route, *, stamp=None):
    if route == MATCH_LIVE_ROUTES[2]:
        stamp = ""
    elif stamp is None:
        try:
            stamp = file_identity(active.path)
        except (OSError, ValueError):
            stamp = ""
    choice = active.live.preference_revision if route == MATCH_LIVE_ROUTES[1] else ""
    material = (f"{route}:{active.handle}:{active.selected_position}:{active.position_generation}:"
                f"{active.capture.content_fingerprint}:{active.live.control_revision}:"
                f"{choice}:{stamp}").encode()
    return hmac.digest(active.card_entry_key, material, "sha256").hex()


def configure_match_live(active, route, values, *, profile=None):
    # Serialize the file identity check and preference write with managed replacements.
    coordinator = match_source_coordinator(active.category_root)
    with coordinator.lock:
        _configure_match_live(active, route, values, profile, coordinator)


def _configure_match_live(active, route, values, profile, coordinator):
    from .card_entry_http import _fresh

    token = values.pop("live_binding", "")
    try:
        stamp = "" if route == MATCH_LIVE_ROUTES[2] else file_identity(active.path)
    except (OSError, ValueError) as error:
        raise StaleFrontendWorkflowRevisionError() from error
    game = active.workspace.slots[active.selected_position - 1].observed_game
    if (game is None or not token.isascii()
            or not hmac.compare_digest(token, match_live_binding(active, route, stamp=stamp))
            or values.pop("expected_revision", None) != str(active.workspace.revision)
            or (route == MATCH_LIVE_ROUTES[0]) != (active.live.effort is None)):
        raise StaleFrontendWorkflowRevisionError()
    effort = selected = None
    block = False
    if route == MATCH_LIVE_ROUTES[1]:
        selected, block = submitted_effort(values)
    elif values:
        raise ValueError("Unexpected Match Live fields.")
    if route != MATCH_LIVE_ROUTES[2]:
        source = active.live.source or coordinator.watch_source(active.path.name)
        epoch = source.generation
        _fresh(active, session=False)
        if (source.generation != epoch or file_identity(active.path) != stamp
                or active.live.file_stamp not in (None, stamp)
                or active.live.source is not None and active.live.epoch != epoch):
            raise StaleFrontendWorkflowRevisionError()
        effort = resolve_recording_effort(active.path, active.capture.content_fingerprint, stamp,
            match_game_key(game), effort_preferences(profile).live_effort,
            selected=selected, block=block)
        active.live.source, active.live.epoch = source, epoch
        active.live.file_stamp = stamp
        if selected is not None:
            # Consume the Apply form even when only the saved scope changes.
            # The current turn's unchanged calculation can still finish.
            active.live.preference_revision += 1
    if effort != active.live.effort:
        active.operation_feedback.begin()
        active.live.configure(effort)


def _play_facts(game):
    pickup = (game.declarer_player_id == game.perspective_player_id
              and game.declaration is not None and not game.declaration.hand_game)
    return (game.declarer_player_id, game.declaration, game.perspective_initial_hand,
            game.original_skat if pickup else None, game.discarded_cards if pickup else None,
            tuple((p.player_id, p.card) for p in game.plays))


def reserve_match_live(active, before, previous_control, *, recording_only=False):
    """Called under the save lock. No trace projection or analysis here."""
    live = active.live
    if live.effort is None:
        return None
    # Only the single accepted native save may advance this game's authority.
    # A cooperating replacement and byte-identical restoration still retire it.
    epoch = live.epoch + int(before is not active.workspace)
    if live.source.generation != epoch:
        live.configure(None)
        return None
    live.epoch = epoch
    position = active.selected_position
    game = active.workspace.slots[position - 1].observed_game
    prior = before.slots[position - 1].observed_game
    if prior is None or game is None or prior.game_id != game.game_id:
        live.configure(None)
        return None
    if before is not active.workspace:
        live.file_stamp = file_identity(active.path)
        live.invalidate()
    if recording_only:
        return None
    if previous_control == live.control_revision and (
            before is active.workspace or _play_facts(prior) == _play_facts(game)):
        return None
    if game.perspective_initial_hand is None or game.declaration is None:
        return None
    attempt = MatchLiveAttempt(
        active.path, active.workspace, active.capture.content_fingerprint, position,
        active.position_generation, live.control_revision, live.effort,
        active.operation_feedback.attempt, live.source, epoch, live.file_stamp)
    live.attempt = attempt
    return attempt


def _owned(app, active, attempt):
    return (app.managed_stateful.active_match is active and not active.retired
            and active.workspace is attempt.workspace and active.live.attempt is attempt
            and active.path == attempt.path == active.capture.workspace_path
            and active.capture.content_fingerprint == attempt.fingerprint
            and active.selected_position == attempt.position
            and active.position_generation == attempt.selection
            and active.live.control_revision == attempt.control
            and active.live.effort == attempt.effort
            and attempt.source.generation == attempt.epoch)


def _require_file(active, attempt):
    validate_managed_direct_child_path_v1(active.category_root, attempt.path, expected_kind="file")
    doc = load_match_workspace_file_v1(attempt.path).document
    if (doc.workspace != attempt.workspace or doc.content_fingerprint != attempt.fingerprint
            or file_identity(attempt.path) != attempt.file_stamp):
        raise ValueError("Match Live source changed.")


def expire_changed_match_live(active):
    """Before rendering controls, retire a replaced owner; passive reads never reserve work."""
    from .card_entry_http import CardEntryConflict, _fresh

    live = active.live
    if live.source is not None:
        try:
            if (live.source.generation == live.epoch
                    and file_identity(active.path) == live.file_stamp):
                _fresh(active, session=False)
                return
        except (OSError, ValueError, CardEntryConflict):
            pass
        live.configure(None)


def run_match_live(app, active, attempt):
    """Unlocked preparation and evaluation; the save already succeeded."""
    def current():
        return (_owned(app, active, attempt)
                and active.operation_feedback.attempt is attempt.feedback)

    outcome, unavailable = None, False
    try:
        if not current():
            return False
        _require_file(active, attempt)
        prepared = current_match_position(attempt.workspace, attempt.position,
                                          samples=COUNTS[EFFORTS.index(attempt.effort)])
        if prepared is not None and current():
            request, legal = prepared
            outcome = (forced_card_guidance(request) if len(legal) == 1 else
                       evaluate_live_position(request, effort=attempt.effort,
                                              cancelled=lambda: not current()))
            unavailable = outcome is None or (
                isinstance(outcome, LiveGameOutcome) and outcome.status != "complete")
    except Exception:
        unavailable = True
    if not current():
        return False
    try:
        _require_file(active, attempt)
    except Exception:
        return False
    with active.capture.lock, app.lock, attempt.source.lock:
        if not current():
            return False
        active.live.outcome, active.live.unavailable = outcome, unavailable
        return True


def match_live_delivery_guard(app, active):
    """Capture under the Product lock, verify again just before sending decorated HTML."""
    attempt = active.live.attempt
    outcome, unavailable = active.live.outcome, active.live.unavailable
    if attempt is None or (outcome is None and not unavailable):
        return None
    feedback = active.operation_feedback.attempt

    def guard():
        _require_file(active, attempt)
        with active.capture.lock, app.lock, attempt.source.lock:
            if (not _owned(app, active, attempt) or active.live.outcome is not outcome
                    or active.live.unavailable != unavailable
                    or active.operation_feedback.attempt is not feedback):
                raise ValueError("Match Live advice changed before delivery.")
    return guard


def match_live_redirect(app, active, attempt, location):
    """Land on the actual choices; never link a superseded input to newer feedback."""
    with active.capture.lock:
        outcome = active.live.outcome
        if isinstance(outcome, ForcedCardGuidance):
            location = location.partition("#")[0] + "#forced-card-guidance"
        elif isinstance(outcome, LiveGameOutcome) and outcome.status == "complete":
            location = location.partition("#")[0] + "#live-recommendation"

    def guard():
        _require_file(active, attempt)
        with active.capture.lock, app.lock, attempt.source.lock:
            if not _owned(app, active, attempt) or active.operation_feedback.attempt is not (
                    attempt.feedback):
                raise ValueError("Match Live input changed before redirect.")
    return location, guard
