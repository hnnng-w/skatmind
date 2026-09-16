from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .frontend_profile_codec import build_local_frontend_profile_v1
from .frontend_profile_operations import is_safe_frontend_return_path_v1
from .workflow_state import StaleFrontendWorkflowRevisionError

if TYPE_CHECKING:
    from .context import AppWebContextV1
    from .language_form_preservation import LanguagePageManifestV1, LanguagePageValuesV1


class LanguageContextConflict(StaleFrontendWorkflowRevisionError):
    """The rendered task is no longer the exact current presentation source."""


@dataclass(frozen=True, slots=True)
class LanguageSourceV1:
    route: str
    references: tuple[object, ...]
    values: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class LanguagePageV1:
    source: LanguageSourceV1
    manifest: LanguagePageManifestV1
    created_at: float


@dataclass(slots=True)
class LanguageContextV1:
    """At most 32 rendered bindings and one return overlay; no Product workspace."""

    pages: dict[str, LanguagePageV1] = field(default_factory=dict, repr=False)
    pending: tuple[LanguagePageV1, LanguagePageValuesV1 | None] | None = field(
        default=None, repr=False)
    key: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)
    serial: int = 0

    def retain(self, source: LanguageSourceV1, manifest: LanguagePageManifestV1) -> str:
        now = time.monotonic()
        self.pages = {token: page for token, page in self.pages.items()
                      if now - page.created_at < 1800}
        while len(self.pages) >= 32:
            self.pages.pop(next(iter(self.pages)))
        self.serial += 1
        token = hmac.new(self.key, str(self.serial).encode(), hashlib.sha256).hexdigest()
        self.pages[token] = LanguagePageV1(source, manifest, now)
        return token

    def resolve(self, token: str, route: str) -> LanguagePageV1:
        if not re.fullmatch(r"[0-9a-f]{64}", token):
            raise ValueError("Language context must be an opaque rendered binding.")
        page = self.pages.get(token)
        if page is None or time.monotonic() - page.created_at >= 1800:
            raise LanguageContextConflict
        if page.source.route != route:
            raise LanguageContextConflict
        return page


def capture_language_source_v1(context: AppWebContextV1, route: str) -> LanguageSourceV1:
    """Snapshot immutable source references under existing locks, with no I/O.

    Never acquire a Product lock while holding the app or profile lock. Retained
    references distinguish reopen and equal-revision replacement without exposing
    paths, fingerprints, or independent browser-owned Product contexts.
    """
    if not is_safe_frontend_return_path_v1(route):
        raise ValueError("Language origin must be a safe HTML route.")
    if route == "/recordings/delete":
        from .recording_deletion import _active, _binding, _label, current_deletion_preview
        preview = current_deletion_preview(context)
        with context.lock:
            feedback = context.form_feedback._feedback.get("deletion")
            label = None if preview is None else _label(context, preview.family, preview.product_id)
            active = None if preview is None else _active(context, preview.family, preview.path)
            outcome = context.recording_deletion.outcome
        binding = ()
        if active is not None:
            lock = active.lock if preview.family == "sessions" else active.capture.lock
            with lock:
                binding = _binding(active, preview.family)
        return LanguageSourceV1(route, (preview, active, None if feedback is None else feedback[1]),
                                (label, binding, outcome))
    references: list[object] = []
    values: list[object] = []
    with context.lock:
        managed = context.managed_stateful
        session = managed.active_session
        match = managed.active_match
        learning = managed.active_learning
        profile = context.frontend_profile.document or build_local_frontend_profile_v1()
        values.append((profile.known_players, profile.own_player_id,
            profile.preferred_perspective_player_id, profile.preferred_game_platform,
            profile.interface_preferences, profile.workflow_preferences,
            profile.managed_item_display_labels))
        if route == "/analyze":
            references.append(context.analyze_state)
        elif route == "/review":
            references.append(context.review_state)
        elif route == "/review/recorded":
            references.extend((managed.discoveries.get("sessions"),
                               managed.discoveries.get("matches"), session, match))
            values.extend((managed.generations["sessions"], managed.generations["matches"]))
        family = {"/sessions": "sessions", "/matches": "matches", "/learning": "corpora"}.get(route)
        if family is not None:
            references.append(managed.discoveries.get(family))
            values.append(managed.generations[family])
        feedback_family = ("recordings" if route == "/review/recorded" else
            "sessions" if route.startswith("/sessions") else
            "matches" if route.startswith("/matches") else
            "learning" if route.startswith("/learning") else
            "local_settings" if route == "/settings" else route.removeprefix("/"))
        if route == "/settings":
            references.append(context.settings_editor)
        setup_family = {"/sessions": "sessions", "/matches/new": "matches"}.get(route)
        if setup_family:
            from .player_seat_setup import current_seat_setup_v1
            references.append(current_seat_setup_v1(
                context, setup_family, context.frontend_profile.document))
        # Reading the private binding avoids current()'s invalidation side effect.
        feedback = context.form_feedback._feedback.get(feedback_family)
        expected_identity = (session if route == "/sessions/current" else
            match if route == "/matches/current" or route.startswith(
                ("/matches/position/", "/matches/review/", "/matches/reports/")) else
            learning if route == "/learning/current" else None)
        if feedback is not None and feedback[0] is not expected_identity:
            feedback = None
        references.append(None if feedback is None else feedback[1])
    if route == "/sessions/current":
        if session is None:
            raise LanguageContextConflict
        with session.lock:
            references.extend((session, session.document, session.execution,
                               session.recorded_review_source, session.execution_attempt,
                               session.last_operation))
            values.append(session.generation)
    if route == "/review/recorded" and match is not None:
        with match.capture.lock:
            values.append(match.selected_position)
    if route == "/matches/current" or route.startswith(
            ("/matches/position/", "/matches/review/", "/matches/reports/")):
        if match is None:
            raise LanguageContextConflict
        with match.capture.lock:
            if (route.startswith(("/matches/position/", "/matches/review/"))
                    and int(route.rsplit("/", 1)[1]) != match.selected_position):
                raise LanguageContextConflict
            selected = match.recovery.selected
            if selected is not None and time.monotonic() - selected.created_at >= 1800:
                selected = None
            references.extend((match, match.workspace, selected,
                               match.recovery.preview if selected is not None else None,
                               match.last_result))
            references.extend(match.capture.report_store.list())
            values.extend((match.selected_position, match.position_generation,
                           match.capture.content_fingerprint,
                           match.capture.report_store.generation))
            if route.startswith("/matches/reports/"):
                from .match_frontend import get_unified_match_report_v1
                status, report = get_unified_match_report_v1(match, route.rsplit("/", 1)[1])
                if status != "found" or report is None:
                    raise LanguageContextConflict
                references.append(report)
        # Transfer forms also depend on the exact selected target collection.
        references.append(learning)
    if route == "/learning/current" or (
            learning is not None and route.startswith(
                ("/matches/position/", "/matches/review/", "/matches/reports/"))):
        if learning is None:
            raise LanguageContextConflict
        with learning.corpus.lock:
            references.extend((learning, learning.corpus.store, learning.corpus.prepared_artifacts,
                learning.corpus.tactical_prepared_artifacts,
                learning.corpus.tactical_coaching_prepared_artifacts, learning.last_result))
            values.extend((learning.corpus.generation,
                           learning.corpus.strategy_source_store.revision))
        if route == "/learning/current":
            with context.lock:
                references.append(managed.discoveries.get("matches"))
                values.append(managed.generations["matches"])
            references.append(match)
            if match is not None:
                with match.capture.lock:
                    references.append(match.workspace)
    return LanguageSourceV1(route, tuple(references), tuple(values))


def validate_language_source_v1(
    context: AppWebContextV1, source: LanguageSourceV1, *, check_files: bool = False,
) -> None:
    current = capture_language_source_v1(context, source.route)
    if (current.values != source.values or len(current.references) != len(source.references)
            or any(a is not b for a, b in zip(current.references, source.references, strict=True))):
        raise LanguageContextConflict
    if check_files:
        _require_files(context, source.route)
        # Filesystem validation holds no app lock. Recheck the active binding afterward.
        validate_language_source_v1(context, source)


def validate_language_page_v1(
    context: AppWebContextV1, page: LanguagePageV1, *, check_files: bool = False,
) -> None:
    if time.monotonic() - page.created_at >= 1800:
        raise LanguageContextConflict
    validate_language_source_v1(context, page.source, check_files=check_files)


def _require_files(context: AppWebContextV1, route: str) -> None:
    if route == "/recordings/delete":
        from .recording_deletion import (
            RecordingDeletionConflict,
            current_deletion_preview,
            validate_deletion_preview,
        )
        preview = current_deletion_preview(context)
        if preview is not None:
            try:
                validate_deletion_preview(context, preview)
            except RecordingDeletionConflict as error:
                raise LanguageContextConflict from error
        return
    from skatmind.api.v1.session import files as session_files
    from skatmind.errors import SkatMindValidationError
    from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1
    from skatmind.match_workspace_persistence import load_match_workspace_file_v1

    from .managed_item_storage import validate_managed_direct_child_path_v1

    with context.lock:
        managed = context.managed_stateful
        session, match, learning = (
            managed.active_session, managed.active_match, managed.active_learning)
    try:
        if route == "/sessions/current" and session is not None:
            with session.lock:
                validate_managed_direct_child_path_v1(session.category_root, session.path,
                                                     expected_kind="file")
                loaded = session_files.load_session_file(session.path).value.document
                if loaded.content_fingerprint != session.document.content_fingerprint:
                    raise LanguageContextConflict
        if (route.startswith(("/matches/position/", "/matches/review/", "/matches/reports/"))
                or route == "/matches/current"):
            if match is None:
                raise LanguageContextConflict
            with match.capture.lock:
                validate_managed_direct_child_path_v1(
                    match.category_root, match.path, expected_kind="file")
                loaded = load_match_workspace_file_v1(match.path).document
                if loaded.content_fingerprint != match.capture.content_fingerprint:
                    raise LanguageContextConflict
        if route == "/learning/current" and learning is not None:
            with learning.corpus.lock:
                validate_managed_direct_child_path_v1(learning.category_root, learning.path,
                                                     expected_kind="directory")
                loaded = load_learning_corpus_directory_v1(learning.path)
                if loaded.document != learning.corpus.store.document:
                    raise LanguageContextConflict
    except (OSError, ValueError, SkatMindValidationError) as error:
        raise LanguageContextConflict from error


def language_return_location_v1(context: AppWebContextV1, route: str) -> str:
    """Only known server-owned anchors; the HTML-route allowlist stays fragment-free."""
    with context.lock:
        session = context.managed_stateful.active_session
        match = context.managed_stateful.active_match
    if route == "/sessions/current" and session is not None:
        with session.lock:
            with context.lock:
                feedback = context.form_feedback.current("sessions", active_identity=session)
            if feedback is not None and feedback.originating_route in {
                    "/sessions/cards", "/sessions/play"}:
                return route + "#session-card-error"
            if session.recorded_review_source is not None:
                return route + "#session-result"
            return route + "#session-recording"
    if route.startswith("/matches/position/") and match is not None:
        with match.capture.lock:
            selected = match.recovery.selected
            return route + ("#match-recovery" if selected is not None
                            and time.monotonic() - selected.created_at < 1800
                             else "#match-recording")
    if route.startswith(("/matches/review/", "/matches/reports/")):
        return route + "#match-review"
    if route == "/review/recorded":
        return route + "#recorded-review-chooser"
    return route
