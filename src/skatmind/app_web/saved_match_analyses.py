"""Process-owned access to family-specific original Match evidence."""

import hashlib
import hmac
import os
import re
import secrets
from contextlib import ExitStack, contextmanager, nullcontext
from dataclasses import dataclass, field, replace
from html import escape
from threading import RLock

from skatmind.capture_web.state import _selected_report_details
from skatmind.errors import SkatMindError

from .analysis_download_rendering import analysis_downloads
from .automatic_learning import (
    automatic_learning_root_v1,
    initialize_managed_automatic_learning_v1,
    resume_managed_automatic_learning_v1,
)
from .match_navigation import match_navigation
from .match_report_rendering import render_match_reports_v1
from .recorded_decision_context_sources import match_analysis_explanation, match_decision_context
from .recorded_review_opening import RecordingOpenConflict
from .session_batch_routes import ORIGIN as SESSION_ORIGIN
from .stateful_localization import managed_name, text, translated
from .task_first_rendering import form, hidden, paragraph
from .whole_match_routes import ORIGIN

SAVED_MATCH_ROUTE = "/matches/saved-analyses"
RETRY_MATCH_ROUTE = "/matches/retry-saving"
SAVED_MATCH_PATTERN = re.compile(
    r"/matches/saved-analyses/([0-9a-f]{64})(?:/(request|result|strategy-source)\.json)?\Z")
SAVED_SESSION_ROUTE = "/sessions/saved-analyses"
SELECTION_ROUTE = "/learning/analysis-selection"
SAVED_SESSION_PATTERN = re.compile(
    r"/sessions/saved-analyses/([0-9a-f]{64})(?:/(request|result)\.json)?\Z")


@dataclass(slots=True)
class SavedMatchAnalyses:
    key: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)
    store: object | None = field(default=None, repr=False)
    lock: object = field(default_factory=RLock, repr=False)

    def token(self, space_id, entry):
        return hmac.new(self.key, (space_id + ":" + entry.identity).encode(),
                        hashlib.sha256).hexdigest()


def archive_store(context, *, initialize=False):
    scope = context.saved_match_analyses
    with scope.lock:
        if scope.store is None:
            root = automatic_learning_root_v1(context.managed_home)
            if not os.path.lexists(root):
                if not initialize:
                    return None
                scope.store = initialize_managed_automatic_learning_v1(context.managed_home)
            else:
                scope.store = resume_managed_automatic_learning_v1(context.managed_home)
        return scope.store


def resolve_saved_analysis(context, token):
    scope = context.saved_match_analyses
    store = archive_store(context)
    if store is None:
        raise RecordingOpenConflict()
    snapshot = store.snapshot()
    entry = next((entry for entry in snapshot.manifest.evidence
        if hmac.compare_digest(scope.token(snapshot.manifest.space_id, entry), token)), None)
    if entry is None or entry.identity not in snapshot.available_evidence_ids:
        raise RecordingOpenConflict()
    value = store.read_evidence(entry.identity)
    if context.saved_match_analyses is not scope:
        raise RecordingOpenConflict()
    return scope, store, snapshot.manifest, value


def validate_saved_delivery(context, scope, store, manifest, value=None, *, evidence_ids=()):
    if context.saved_match_analyses is not scope or scope.store is not store:
        raise RecordingOpenConflict()
    current = store.snapshot()
    if current.manifest != manifest:
        raise RecordingOpenConflict()
    if value is not None and value.entry.identity not in current.available_evidence_ids:
        raise RecordingOpenConflict()
    if not set(evidence_ids).issubset(current.available_evidence_ids):
        raise RecordingOpenConflict()


def saved_analyses_link(locale):
    return ('<p><a class="button-link secondary" href="' + SAVED_MATCH_ROUTE + '">'
            + escape(text(locale, "saved_analysis.title")) + '</a></p>')


def selection_status(manifest, entry, locale):
    source = next(r.source_version.source for r in manifest.sources
                  if r.source_version.identity == entry.source_version_id)
    if source.family not in ("match", "session"):
        return "batch.ineligible"
    if any(e.source == source for e in manifest.exclusions):
        return "batch.source_excluded"
    return ("batch.excluded" if entry.identity in manifest.excluded_analysis_ids
            else "batch.selected")


def selection_form(scope, manifest, entry, locale, *, origin=None):
    status = selection_status(manifest, entry, locale)
    if status == "batch.ineligible":
        return paragraph(locale, status)
    excluded = entry.identity in manifest.excluded_analysis_ids
    fields = (hidden("analysis", scope.token(manifest.space_id, entry))
              + hidden("manifest", manifest.fingerprint)
              + hidden("choice", "include" if excluded else "exclude"))
    if origin is not None:
        fields += hidden("origin", origin)
    return paragraph(locale, status) + form(locale, SELECTION_ROUTE, fields,
                                           "batch.include" if excluded else "batch.exclude")


def direct_selection(app, active, entry, family):
    """Reconstruct only the current genuine receipt's destination, never a submitted URL."""
    from .match_evidence_retention import _selection, require_capture_owner
    from .recorded_review_opening import require_recording_fresh_v1
    from .session_recorded_review import _require_source
    from .whole_match_progress import file_identity

    notice = active.evidence_notice
    if active.retired or not notice or notice[1:] != ("saved", entry.identity):
        raise RecordingOpenConflict()
    if family == "session":
        source = notice[0]
        if app.managed_stateful.active_session is not active:
            raise RecordingOpenConflict()
        _require_source(active, source)
        rollout = entry.envelope.kind == "session_rollout"
        route = "/sessions/decisions/" + source.decision.selection + (
            "#session-rollout-result" if rollout else "#session-result")
        key, owner = active.review_selection_key, (source.generation, source.source_epoch)
        require_recording_fresh_v1(active, "sessions")
    else:
        if app.managed_stateful.active_match is not active:
            raise RecordingOpenConflict()
        binding = active.rollout_evidence_binding
        if binding is not None and binding.report.report_id == notice[0]:
            require_capture_owner(app, active, binding)
            report = binding.display_report
        else:
            report = active.capture.report_store.get(notice[0])
        if report is None or report.match_position != active.selected_position:
            raise RecordingOpenConflict()
        route = "/matches/reports/" + report.report_id
        key = active.card_entry_key
        owner = (active.capture.content_fingerprint, active.capture.report_store.generation,
                 _selection(active))
        require_recording_fresh_v1(active, "matches")
    material = (route, entry.identity, owner, file_identity(active.path))
    return "direct:" + hmac.digest(key, repr(material).encode(), "sha256").hex(), route


def change_selection(handler, fields):
    app = handler.server.app_context
    try:
        origin = fields.pop("origin", None)
        if set(fields) != {"analysis", "manifest", "choice"}:
            raise RecordingOpenConflict()
        token = fields["analysis"]
        scope, store, manifest, value = resolve_saved_analysis(app, token)
        family = value.source.record.source_version.source.family
        allowed = set(manifest.excluded_analysis_ids)
        identity = value.entry.identity
        expected = "include" if identity in allowed else "exclude"
        if (family not in ("match", "session") or fields["choice"] != expected
                or fields["manifest"] != manifest.fingerprint):
            raise RecordingOpenConflict()
        route = (SAVED_MATCH_ROUTE if family == "match" else SAVED_SESSION_ROUTE) + "/" + token
        direct = origin is not None and re.fullmatch(r"direct:[0-9a-f]{64}", origin)
        if origin is not None and not direct:
            match = (ORIGIN if family == "match" else SESSION_ORIGIN).fullmatch(origin)
            if not match or match["destination"] or match["token"] != token:
                raise RecordingOpenConflict()
            if family == "session":
                from .session_batch_web import require_origin
            else:
                from .whole_match_web import require_origin
            require_origin(app, match)
            route = origin
        if expected == "include":
            allowed.remove(identity)
        else:
            allowed.add(identity)
        requested = replace(manifest, revision=manifest.revision + 1,
                            excluded_analysis_ids=tuple(sorted(allowed)))
        publication = nullcontext
        if direct:
            active = (app.managed_stateful.active_match if family == "match"
                      else app.managed_stateful.active_session)
            if active is None:
                raise RecordingOpenConflict()
            lock = active.capture.lock if family == "match" else active.lock
            with lock, app.lock:
                expected_origin, route = direct_selection(app, active, value.entry, family)
                if not hmac.compare_digest(expected_origin, origin):
                    raise RecordingOpenConflict()

            @contextmanager
            def publication():
                # The archive already holds its writer lock. Never wait for a producer.
                with ExitStack() as locks:
                    for fence in (lock, app.lock):
                        if not fence.acquire(blocking=False):
                            raise RecordingOpenConflict()
                        locks.callback(fence.release)
                    if direct_selection(app, active, value.entry, family)[0] != origin:
                        raise RecordingOpenConflict()
                    yield

        result = store.update_manifest(requested, expected_manifest=manifest.fingerprint,
            publication_context=publication,
            commit_guard=lambda: app.saved_match_analyses is scope and scope.store is store)
        if result.status != "saved":
            raise RecordingOpenConflict()
    except (OSError, ValueError, RuntimeError, SkatMindError):
        handler._send_common_error(409)
        return
    handler._redirect(route)


def _retention_feedback(locale, active, status, retry, rollout):
    prefix = "saved_analysis.rollout." if rollout else "saved_analysis."
    body = '<div role="status">' + paragraph(locale, prefix + status) + '</div>'
    if retry is not None:
        body += (f'<form method="post" action="{RETRY_MATCH_ROUTE}">'
            f'<input type="hidden" name="managed_handle" value="{active.handle}">'
            f'<input type="hidden" name="save_token" value="{retry.token}">'
            '<button type="submit">' + escape(text(locale, "saved_analysis.retry")) + '</button>'
            '</form>')
    return body


def live_retention_delivery(context, active, report_id, locale):
    """Prepare feedback and its header guard together for this one response."""
    from .match_evidence_retention import _selection, require_capture_owner, require_pending_owner
    from .recorded_review_opening import require_recording_fresh_v1

    with active.capture.lock:
        notice = active.evidence_notice
        if notice is None or notice[0] != report_id:
            return "", None
        pending = active.pending_evidence
        fingerprint = active.capture.content_fingerprint
        generation = active.capture.report_store.generation
        report = active.capture.report_store.get(report_id)
        binding = active.rollout_evidence_binding
        bound_rollout = binding is not None and binding.report.report_id == report_id
        retry = pending if pending is not None and pending.report.report_id == report_id else None
        attempt, selection = active.rollout_attempt, _selection(active)
        with context.lock:
            scope = context.saved_match_analyses
            if bound_rollout:
                try:
                    require_capture_owner(context, active, binding)
                except RecordingOpenConflict:
                    return "", None  # Navigation expired this rollout's feedback.
            show_feedback = True
            if retry is not None:
                try:
                    require_pending_owner(context, active, retry)
                except RecordingOpenConflict:
                    # Omit expired consent but retain the original final owner guard.
                    show_feedback = False
        rollout = bound_rollout or (report is not None and getattr(
            report.value.options, "recommendation_method", None) == "whole_game_rollout")

    store = resumed = receipt = None
    status = notice[1]
    if status == "saved":
        try:
            store = archive_store(context)
            if store is not None:
                resumed, receipt = store._snapshot_for_delivery()
            if resumed is None or notice[2] not in resumed.available_evidence_ids:
                status = "unknown"
        except (OSError, ValueError, SkatMindError):
            status = "unknown"
    elif retry is None and status != "unknown":
        status = "unavailable"

    def require_live_owner():
        with active.capture.lock:
            with context.lock:
                if (context.managed_stateful.active_match is not active or active.retired
                        or active.evidence_notice is not notice
                        or context.saved_match_analyses is not scope
                        or (notice[1] == "saved" and scope.store is not store)
                        or active.rollout_attempt is not attempt or _selection(active) != selection
                        or active.capture.content_fingerprint != fingerprint
                        or active.capture.report_store.generation != generation
                        or active.capture.report_store.get(report_id) is not report):
                    raise RecordingOpenConflict()
                require_recording_fresh_v1(active, "matches")
                if bound_rollout:
                    if active.rollout_evidence_binding is not binding:
                        raise RecordingOpenConflict()
                    require_capture_owner(context, active, binding)
                if pending is not None:
                    require_pending_owner(context, active, pending)

    def guard():
        if notice[1] == "saved":
            if (store is None or context.saved_match_analyses is not scope
                    or scope.store is not store):
                raise RecordingOpenConflict()
            # The store rereads exact bytes + inventory even on a hit. No entry
            # survives this response; above the bounds both snapshots are strict.
            final, _ = store._snapshot_for_delivery(receipt)
            if (resumed is not None and final != resumed
                    or notice[2] not in final.available_evidence_ids):
                raise RecordingOpenConflict()
        require_live_owner()  # Unlocked archive validation may race a recording change.
    body = _retention_feedback(locale, active, status, retry, rollout) if show_feedback else ""
    if show_feedback and status == "saved":
        entry = next(e for e in resumed.manifest.evidence if e.identity == notice[2])
        with active.capture.lock, context.lock:
            require_live_owner()
            origin, _ = direct_selection(context, active, entry, "match")
        body += selection_form(scope, resumed.manifest, entry, locale, origin=origin)
    return body, guard


def _caption(value, locale):
    if value.entry.evidence_class == "historical":
        from .historical_learning_rendering import historical_caption
        return historical_caption(value, locale)
    if value.entry.envelope.kind.startswith("session_"):
        from .session_learning_rendering import evidence_caption
        return evidence_caption(value, locale)
    report = value.report
    definition = value.source.document.workspace.match_definition
    actor = report.value.profile_binding.acting_player_id
    label = next(player.player_label or player.player_id for player in definition.participants
                 if player.player_id == actor)
    caption = text(locale, "saved_analysis.caption", match=definition.title or report.match_id,
        game=report.match_position, decision=report.decision_index, actor=label,
        method=text(locale, "saved_analysis.method." + report.value.options.recommendation_method))
    if value.entry.evidence_class == "rollout":
        result = report.value.result.document["whole_game_rollout_result"]
        status = result["status"]
        caption += " · " + text(locale, "saved_analysis.rollout.caption",
            objective=text(locale, "rollout.objective." + result["objective"]),
            status=text(locale, "saved_analysis.rollout.cancelled" if status == "cancelled"
                        else "result.value." + status))
    return caption


def render_saved_analysis(value, route, locale):
    if value.entry.evidence_class == "historical":
        from .historical_learning_rendering import render_historical_evidence
        return (render_historical_evidence(value, route, locale) + saved_analyses_link(locale)
                + '<p><a href="/learning/automatic">' + escape(text(locale, "automatic.back"))
                + '</a></p>')
    if value.entry.envelope.kind.startswith("session_"):
        from .session_learning_rendering import render_session_evidence, session_links
        return (render_session_evidence(value, route, locale) + session_links(locale)
                + '<p><a href="/learning/automatic">' + escape(text(locale, "automatic.back"))
                + '</a></p>')
    workspace, report = value.source.document.workspace, value.report
    state = {"reports": [], "selected_report": _selected_report_details(report),
        "selected_position": report.match_position,
        "decision_context": match_decision_context(report, workspace),
        "analysis_explanation": match_analysis_explanation(report, workspace),
        "download_availability": {"report_result": False}}
    rollout = value.entry.evidence_class == "rollout"
    if rollout:
        state["rollout_report"] = report.value
        state["rollout_archive_downloads"] = (route + "/request.json", route + "/result.json")
    body = ('<section id="saved-analysis" tabindex="-1"><h2>'
            + escape(_caption(value, locale)) + '</h2>')
    body += paragraph(locale, "saved_analysis.captured", revision=workspace.revision,
        source=value.source.record.source_version.content_fingerprint[:12],
        report=report.report_id[:12])
    body += paragraph(locale, "saved_analysis.historical")
    body += render_match_reports_v1(state, locale, retained_archive=True)
    if not rollout:
        body += analysis_downloads(request_href=route + "/request.json",
            result_href=route + "/result.json", report_source_href=route + "/strategy-source.json",
            locale=locale)
    return body + '</section>' + saved_analyses_link(locale)


def handle_saved_analysis_get(handler, path, *, origin=None):
    return_to = path
    if origin is not None:
        path = path.partition("/" + origin["token"] + "/")[0] + "/" + origin["token"]
    session = path == SAVED_SESSION_ROUTE or path.startswith(SAVED_SESSION_ROUTE + "/")
    route = SAVED_SESSION_ROUTE if session else SAVED_MATCH_ROUTE
    family = "session" if session else "match"
    area = "/sessions" if session else "/matches"
    match = (SAVED_SESSION_PATTERN if session else SAVED_MATCH_PATTERN).fullmatch(path)
    if path != route and match is None:
        return False
    context = handler.server.app_context
    scope = context.saved_match_analyses
    locale = handler._frontend_state().locale
    try:
        store = archive_store(context)
        if match is not None:
            scope, store, manifest, value = resolve_saved_analysis(context, match[1])
            if value.source.record.source_version.source.family != family:
                raise RecordingOpenConflict()
            with store.pin_objects((value.entry.envelope,), expected_manifest=manifest.fingerprint):
                handler._retained_delivery_guard = lambda: validate_saved_delivery(
                    context, scope, store, manifest, value)
                if match[2]:
                    handler._send_artifact(*value.download(match[2]))
                else:
                    from .language_context import capture_language_source_v1

                    navigation = ""
                    if origin is not None and session:
                        from .session_batch_web import require_origin
                        try:
                            require_origin(context, origin)
                        except (OSError, ValueError, RecordingOpenConflict, SkatMindError):
                            return_to = path
                            navigation = paragraph(locale, "batch.unavailable")
                        else:
                            navigation = f'<p><a href="{return_to}/overview">' + translated(
                                locale, "whole_review.overview") + '</a></p>'
                            navigation += f'<p><a href="{return_to}/recording#session-recording">'
                            navigation += translated(locale, "batch.back") + '</a></p>'
                            def guard():
                                validate_saved_delivery(context, scope, store, manifest, value)
                                require_origin(context, origin)
                            handler._retained_delivery_guard = guard
                    elif origin is not None:
                        from .whole_match_web import origin_fallback, require_origin

                        try:
                            active = require_origin(context, origin)
                        except (OSError, ValueError, RecordingOpenConflict, SkatMindError):
                            navigation = paragraph(locale, "match_nav.stale")
                            return_to = path
                        else:
                            game = int(origin["game"])
                            definition = active.workspace.match_definition
                            title = managed_name(locale, context.frontend_profile.document,
                                "matches", definition.match_id, definition.title)
                            navigation = match_navigation(locale, title, game,
                                recording=return_to + "/recording#match-recording",
                                decision=int(origin["play"]))
                            navigation += (f'<p><a href="{return_to}/overview#game-{game}">'
                                + translated(locale, "match_nav.back", number=game) + '</a></p>')

                            def guard():
                                validate_saved_delivery(context, scope, store, manifest, value)
                                require_origin(context, origin)
                            handler._retained_delivery_guard = guard
                            handler._retained_delivery_recovery = lambda: origin_fallback(
                                handler, origin)
                    handler._rendered_language_source = capture_language_source_v1(
                        context, return_to)
                    handler._content_page(area, return_to=return_to,
                        title=text(locale, "saved_analysis.title"),
                        content=navigation + selection_form(scope, manifest, value.entry, locale,
                            origin=origin[0] if return_to != path else None)
                        + render_saved_analysis(value, path, locale),
                        feedback_identity=scope, analysis=True,
                        untranslated_workflow_body=False)
            return True
        snapshot = None if store is None else store.snapshot()
        entries = (() if snapshot is None else tuple(entry for entry in snapshot.manifest.evidence
                   if entry.envelope.kind.startswith(family + "_")))
        body = ""
        refs = () if snapshot is None else tuple(
            entry.envelope for entry in entries
            if entry.identity in snapshot.available_evidence_ids)
        with (nullcontext() if store is None else store.pin_objects(refs,
                expected_manifest=snapshot.manifest.fingerprint)):
            values = (() if store is None else store.read_evidence_many(
                tuple(entry.identity for entry in entries
                      if entry.identity in snapshot.available_evidence_ids),
                expected_manifest=snapshot.manifest.fingerprint))
            for value in values:
                entry = value.entry
                token = scope.token(snapshot.manifest.space_id, entry)
                body += '<li><p>' + escape(_caption(value, locale)) + '</p>'
                body += paragraph(locale, "saved_analysis.captured",
                    revision=value.source.record.revision,
                    source=value.source.record.source_version.content_fingerprint[:12],
                    report=entry.identity[:12] if session else value.report.report_id[:12])
                body += (f'<a class="button-link secondary" href="{route}/{token}">'
                         + escape(text(locale, "saved_analysis.open")) + '</a></li>')
            body = '<ul class="workflow-list">' + body + '</ul>' if body else paragraph(
                locale, "saved_analysis.empty")
            if snapshot is not None:
                if len(refs) != len(entries):
                    body += paragraph(locale, "saved_analysis.excluded")
                handler._retained_delivery_guard = lambda: validate_saved_delivery(
                    context, scope, store, snapshot.manifest,
                    evidence_ids=tuple(value.entry.identity for value in values))
            from .language_context import capture_language_source_v1

            handler._rendered_language_source = capture_language_source_v1(context, path)
            body += ('<p><a href="/learning/automatic">'
                     + escape(text(locale, "automatic.back")) + '</a></p>')
            handler._content_page(area, return_to=path,
                title=text(locale, "saved_analysis.title"), content=body,
                feedback_identity=scope, analysis=True,
                untranslated_workflow_body=False)
    except (OSError, ValueError, KeyError, SkatMindError, RecordingOpenConflict):
        handler._retained_delivery_guard = None
        handler._rendered_language_source = None
        handler._content_page(area, return_to=route,
            title=text(locale, "saved_analysis.title"), status=409,
            content=paragraph(locale, "saved_analysis.blocked"), untranslated_workflow_body=False)
    return True


def handle_retry_saving(handler, values):
    from .match_evidence_retention import PendingMatchRolloutSave, save_pending_match

    context = handler.server.app_context
    try:
        if set(values) != {"managed_handle", "save_token"}:
            raise RecordingOpenConflict()
        with context.lock:
            active = context.managed_stateful.active_match
            if active is None or active.handle != values["managed_handle"]:
                raise RecordingOpenConflict()
            pending = active.pending_evidence
        save_pending_match(context, active, values["save_token"])
    except RecordingOpenConflict:
        locale = handler._frontend_state().locale
        handler._content_page("/matches", return_to=SAVED_MATCH_ROUTE, status=409,
            title=text(locale, "saved_analysis.title"),
            content=paragraph(locale, "saved_analysis.expired") + saved_analyses_link(locale),
            untranslated_workflow_body=False)
        return
    display = pending.display_report if type(pending) is PendingMatchRolloutSave else pending.report
    handler._redirect(f"/matches/reports/{display.report_id}")
