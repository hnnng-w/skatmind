from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from .automatic_learning_routes import automatic_html_route
from .frontend_profile_codec import build_local_frontend_profile_v1
from .frontend_profile_operations import is_safe_frontend_return_path_v1
from .historical_review_routes import historical_html_route
from .workflow_state import StaleFrontendWorkflowRevisionError

if TYPE_CHECKING:
    from .context import AppWebContextV1
    from .language_form_preservation import LanguagePageManifestV1, LanguagePageValuesV1
    from .match_declaration_drafts import DeclarationDraftAuthorization
    from .operation_feedback import FeedbackPresentation


class LanguageContextConflict(StaleFrontendWorkflowRevisionError):
    """The rendered task is no longer the exact current presentation source."""


@dataclass(frozen=True, slots=True)
class LanguageSourceV1:
    route: str
    references: tuple[object, ...]
    values: tuple[object, ...]
    automatic_view: object | None = None
    historical_delivery: object | None = None


@dataclass(frozen=True, slots=True)
class LanguagePageV1:
    source: LanguageSourceV1
    manifest: LanguagePageManifestV1
    created_at: float
    feedback: FeedbackPresentation | None = None
    native_match_draft: LanguagePageValuesV1 | None = field(default=None, repr=False)
    native_match_draft_deadline: float | None = None
    native_match_draft_consumed: bool = False
    native_match_draft_authorization: DeclarationDraftAuthorization | None = field(
        default=None, repr=False)

    def require_native_draft_authorization(self):
        if self.native_match_draft is not None:
            from .match_declaration_drafts import DeclarationDraftConflict

            if self.native_match_draft_authorization is None:
                raise DeclarationDraftConflict()
            self.native_match_draft_authorization.require_current()


@dataclass(slots=True)
class LanguageContextV1:
    """At most 32 rendered bindings and one return overlay; no Product workspace."""

    pages: dict[str, LanguagePageV1] = field(default_factory=dict, repr=False)
    pending: tuple[LanguagePageV1, LanguagePageValuesV1 | None] | None = field(
        default=None, repr=False)
    pending_token: str | None = field(default=None, repr=False)
    pending_generation: int | None = None
    pending_route: str | None = None
    key: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)
    serial: int = 0

    def retain(self, source: LanguageSourceV1, manifest: LanguagePageManifestV1,
               feedback: FeedbackPresentation | None = None, *, native_match_draft=None,
               native_match_draft_deadline=None, native_match_draft_authorization=None) -> str:
        now = time.monotonic()
        self.pages = {token: page for token, page in self.pages.items()
                      if now - page.created_at < 1800}
        while len(self.pages) >= 32:
            self.pages.pop(next(iter(self.pages)))
        self.serial += 1
        token = hmac.new(self.key, str(self.serial).encode(), hashlib.sha256).hexdigest()
        self.pages[token] = LanguagePageV1(source, manifest, now, feedback,
            native_match_draft, native_match_draft_deadline,
            native_match_draft_authorization=native_match_draft_authorization)
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


    def submit(self, token: str, route: str) -> LanguagePageV1:
        """Retire feedback authorization even on failed/no-op language submissions.

        Form/view bindings keep their existing lifetime. Feedback is never inferred
        from a later GET or another page's binding. Caller owns the app lock.
        """
        page = self.resolve(token, route)
        page.require_native_draft_authorization()
        if page.native_match_draft_consumed or (
                page.native_match_draft_deadline is not None
                and time.monotonic() >= page.native_match_draft_deadline):
            from .match_declaration_drafts import DeclarationDraftConflict

            raise DeclarationDraftConflict()
        self.pages[token] = replace(page, feedback=None, native_match_draft=None,
            native_match_draft_deadline=None,
            native_match_draft_consumed=page.native_match_draft is not None)
        return page


def capture_language_source_v1(context: AppWebContextV1, route: str, *,
                               automatic_view=None, historical_delivery=None) -> LanguageSourceV1:
    """Snapshot immutable source references under existing locks, with no I/O.

    Never acquire a Product lock while holding the app or profile lock. Retained
    references distinguish reopen and equal-revision replacement without exposing
    paths, fingerprints, or independent browser-owned Product contexts.
    """
    if not is_safe_frontend_return_path_v1(route):
        raise ValueError("Language origin must be a safe HTML route.")
    if automatic_html_route(route) or historical_html_route(route):
        controller = context.automatic_learning_ui
        service = controller.service
        return LanguageSourceV1(route, (controller, service,
            None if service is None else service.attempt,
            None if service is None else service._installed, controller.confirmation,
            context.historical_reviews.confirmation if historical_html_route(route) else None), (),
            automatic_view=automatic_view)
    if route in ("/matches/saved-analyses", "/sessions/saved-analyses") or route.startswith(
            ("/matches/saved-analyses/", "/sessions/saved-analyses/")):
        return LanguageSourceV1(route, (context.saved_match_analyses,), ())
    from .learning_outcome_navigation import LEARNING_PREPARED_PATTERN, resolve_prepared_scope

    prepared_view = LEARNING_PREPARED_PATTERN.fullmatch(route)
    learning_page = route == "/learning/current" or prepared_view is not None
    if route.startswith("/learning/debrief/"):
        from .debrief_frontend import DebriefUnavailable, resolve_scope

        try:
            scope = resolve_scope(context, route.split("/")[3])
        except DebriefUnavailable as error:
            raise LanguageContextConflict from error
        with context.lock:
            labels = context.frontend_profile.document
        return LanguageSourceV1(route, (scope,), (
            () if labels is None else labels.managed_item_display_labels,))
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
    if prepared_view is not None:
        from .debrief_frontend import DebriefUnavailable

        try:
            references.append(resolve_prepared_scope(context, prepared_view[1]))
        except DebriefUnavailable as error:
            raise LanguageContextConflict from error
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
        family = {"/sessions": "sessions", "/matches": "matches", "/learning": "corpora",
                  "/learning/collections": "corpora"}.get(route)
        if family is not None:
            references.append(managed.discoveries.get(family))
            values.append(managed.generations[family])
            if family == "corpora":
                references.append(learning)
            if route == "/learning":
                automatic = context.automatic_learning_ui
                references.append(automatic)
                if automatic.service is not None:
                    references.extend((automatic.service, automatic.service.attempt,
                                       automatic.service._installed))
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
            learning if learning_page else None)
        if feedback is not None and feedback[0] is not expected_identity:
            feedback = None
        references.append(None if feedback is None else feedback[1])
    if route == "/sessions/current":
        if session is None:
            raise LanguageContextConflict
        with session.lock:
            from .session_declaration_correction import current_selection
            pending = session.declaration_correction
            selected = pending.selected if current_selection(session, pending.selected) else None
            references.extend((session, session.document, session.execution,
                                 session.recorded_review_source, session.execution_attempt,
                                 session.rollout_execution, session.rollout_review_source,
                                 session.rollout_notice,
                                session.last_operation, selected,
                                pending.preview if selected is not None else None,
                                pending.proposal if selected is not None else None))
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
            references.append(match.rollout_notice)
            values.extend((match.selected_position, match.position_generation,
                           match.selected_review_decision,
                           match.review_decision_generation, match.review_selection_pending,
                           match.review_selection_native_ready,
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
    if learning_page or (route in ("/learning", "/learning/collections")
                        and learning is not None) or (
            learning is not None and route.startswith(
                ("/matches/position/", "/matches/review/", "/matches/reports/"))):
        if learning is None:
            raise LanguageContextConflict
        with learning.corpus.lock:
            if learning_page and any(value is not None for value in (
                learning.corpus.prepared_artifacts, learning.corpus.tactical_prepared_artifacts,
                learning.corpus.tactical_coaching_prepared_artifacts,
            )):
                from skatmind.corpus_web.downloads import (
                    LearningCorpusPreparedDownloadUnavailableError,
                    require_learning_corpus_prepared_bundle_v1,
                )

                try:
                    require_learning_corpus_prepared_bundle_v1(learning.corpus)
                except LearningCorpusPreparedDownloadUnavailableError as error:
                    raise LanguageContextConflict from error
            references.extend((learning, learning.corpus.store, learning.corpus.prepared_artifacts,
                learning.corpus.tactical_prepared_artifacts,
                learning.corpus.tactical_coaching_prepared_artifacts, learning.last_result))
            values.extend((learning.corpus.generation,
                           learning.corpus.strategy_source_store.revision,
                           learning.debrief_sources.revision))
        if learning_page:
            with context.lock:
                references.append(managed.discoveries.get("matches"))
                values.append(managed.generations["matches"])
            references.append(match)
            if match is not None:
                with match.capture.lock:
                    references.append(match.workspace)
                    references.extend(match.capture.report_store.list())
                    values.append(match.capture.report_store.generation)
    return LanguageSourceV1(route, tuple(references), tuple(values), automatic_view=automatic_view,
                            historical_delivery=historical_delivery)


def _require_language_identity(context: AppWebContextV1, source: LanguageSourceV1) -> None:
    """Recheck retained process identities without repeating filesystem validation."""
    current = capture_language_source_v1(context, source.route,
                                         automatic_view=source.automatic_view,
                                         historical_delivery=source.historical_delivery)
    if (current.values != source.values or len(current.references) != len(source.references)
            or any(a is not b for a, b in zip(current.references, source.references, strict=True))):
        raise LanguageContextConflict


def validate_language_source_v1(
    context: AppWebContextV1, source: LanguageSourceV1, *, check_files: bool = False,
) -> None:
    _require_language_identity(context, source)
    if source.historical_delivery is not None:
        try:
            source.historical_delivery.validate(context)
        except (OSError, ValueError) as error:
            raise LanguageContextConflict from error
    if (check_files or automatic_html_route(source.route) or historical_html_route(source.route)
            or source.route == "/learning"):
        _require_files(context, source.route, automatic_view=source.automatic_view)
        # Filesystem validation holds no app lock. Recheck the active binding afterward.
        _require_language_identity(context, source)


def validate_language_page_v1(
    context: AppWebContextV1, page: LanguagePageV1, *, check_files: bool = False,
) -> None:
    page.require_native_draft_authorization()
    if time.monotonic() - page.created_at >= 1800:
        raise LanguageContextConflict
    validate_language_source_v1(context, page.source, check_files=check_files)


def _require_files(context: AppWebContextV1, route: str, *, automatic_view=None) -> None:
    if route == "/learning" or automatic_html_route(route) or historical_html_route(route):
        from .automatic_learning_routes import AUTOMATIC_CONFIRMATION, AUTOMATIC_VIEW
        controller = context.automatic_learning_ui
        try:
            confirmation = AUTOMATIC_CONFIRMATION.fullmatch(route)
            view = AUTOMATIC_VIEW.fullmatch(route)
            if confirmation:
                retained = controller.require_confirmation(confirmation[1])
                if automatic_view is not None:
                    with controller.lock:
                        if (retained.view is not automatic_view or
                                controller.views.get(automatic_view.token) is not automatic_view):
                            raise LanguageContextConflict
            elif automatic_view is not None:
                if view is not None and view[1] != automatic_view.token:
                    raise LanguageContextConflict
                if controller.resolve(automatic_view.token) is not automatic_view:
                    raise LanguageContextConflict
            elif view is not None:
                controller.resolve(view[1])
            elif route != "/learning":
                # The root entry has no token in its URL. Only its delivered page
                # binding authorizes language return; fresh state cannot replace it.
                raise LanguageContextConflict
        except (OSError, ValueError) as error:
            raise LanguageContextConflict from error
        return
    if route.startswith(("/matches/saved-analyses/", "/sessions/saved-analyses/")):
        from .saved_match_analyses import resolve_saved_analysis

        try:
            resolve_saved_analysis(context, route.rsplit("/", 1)[1])
        except (OSError, ValueError, RuntimeError) as error:
            raise LanguageContextConflict from error
        return
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

    from .learning_outcome_navigation import LEARNING_PREPARED_PATTERN
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
        if (route == "/learning/current" or LEARNING_PREPARED_PATTERN.fullmatch(route)):
            if learning is None:
                raise LanguageContextConflict
            with learning.corpus.lock:
                validate_managed_direct_child_path_v1(learning.category_root, learning.path,
                                                     expected_kind="directory")
                loaded = load_learning_corpus_directory_v1(learning.path)
                if loaded.document != learning.corpus.store.document:
                    raise LanguageContextConflict
    except (OSError, ValueError, SkatMindValidationError) as error:
        raise LanguageContextConflict from error


def language_return_location_v1(context: AppWebContextV1, route: str) -> str:
    """Language is not an operation destination; keep the HTML allowlist unchanged."""
    if not is_safe_frontend_return_path_v1(route):
        raise ValueError("Language return must be a safe HTML route.")
    return route
