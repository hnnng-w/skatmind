"""Process-owned access to family-specific original Match evidence."""

import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass, field
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
from .match_report_rendering import render_match_reports_v1
from .recorded_decision_context_sources import match_analysis_explanation, match_decision_context
from .recorded_review_opening import RecordingOpenConflict
from .stateful_localization import text
from .task_first_rendering import paragraph

SAVED_MATCH_ROUTE = "/matches/saved-analyses"
RETRY_MATCH_ROUTE = "/matches/retry-saving"
SAVED_MATCH_PATTERN = re.compile(
    r"/matches/saved-analyses/([0-9a-f]{64})(?:/(request|result|strategy-source)\.json)?\Z")
SAVED_SESSION_ROUTE = "/sessions/saved-analyses"
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


def retention_feedback(context, active, report_id, locale):
    from .match_evidence_retention import require_capture_owner, require_pending_owner

    notice = active.evidence_notice
    if notice is None or notice[0] != report_id:
        return ""
    binding = active.rollout_evidence_binding
    if binding is not None and binding.report.report_id == report_id:
        try:
            with active.capture.lock:
                with context.lock:
                    require_capture_owner(context, active, binding)
        except RecordingOpenConflict:
            # Navigation expires the receipt/retry, not the earlier live comparison.
            return ""
    status = notice[1]
    if status == "saved":
        try:
            store = archive_store(context)
            if store is None or notice[2] not in store.snapshot().available_evidence_ids:
                status = "unknown"
        except (OSError, ValueError, SkatMindError):
            status = "unknown"
    pending = active.pending_evidence
    retry = False
    if pending is not None and pending.report.report_id == report_id:
        try:
            with active.capture.lock:
                with context.lock:
                    require_pending_owner(context, active, pending)
            retry = True
        except RecordingOpenConflict:
            return ""
    elif status not in {"saved", "unknown"}:
        status = "unavailable"
    report = active.capture.report_store.get(report_id)
    if active.rollout_notice is not None and active.rollout_notice[0].report_id == report_id:
        report = active.rollout_notice[0]
    prefix = ("saved_analysis.rollout." if (binding is not None
              and binding.report.report_id == report_id) or (report is not None
               and getattr(report.value.options, "recommendation_method", None)
               == "whole_game_rollout")
              else "saved_analysis.")
    body = '<div role="status">' + paragraph(locale, prefix + status) + '</div>'
    if retry:
        body += (f'<form method="post" action="{RETRY_MATCH_ROUTE}">'
            f'<input type="hidden" name="managed_handle" value="{active.handle}">'
            f'<input type="hidden" name="save_token" value="{pending.token}">'
            '<button type="submit">' + escape(text(locale, "saved_analysis.retry")) + '</button>'
            '</form>')
    return body


def live_retention_delivery_guard(context, active, report_id):
    """Bind the new receipt/retry presentation through final HTML delivery."""
    from .match_evidence_retention import require_capture_owner, require_pending_owner
    from .recorded_review_opening import require_recording_fresh_v1

    with active.capture.lock:
        notice = active.evidence_notice
        if notice is None or notice[0] != report_id:
            return None
        pending = active.pending_evidence
        fingerprint = active.capture.content_fingerprint
        generation = active.capture.report_store.generation
        report = active.capture.report_store.get(report_id)
        binding = active.rollout_evidence_binding
        if binding is not None and binding.report.report_id == report_id:
            try:
                with context.lock:
                    require_capture_owner(context, active, binding)
            except RecordingOpenConflict:
                return None

    def guard():
        with active.capture.lock:
            with context.lock:
                if (context.managed_stateful.active_match is not active or active.retired
                        or active.evidence_notice is not notice
                        or active.capture.content_fingerprint != fingerprint
                        or active.capture.report_store.generation != generation
                        or active.capture.report_store.get(report_id) is not report):
                    raise RecordingOpenConflict()
                require_recording_fresh_v1(active, "matches")
                if binding is not None and binding.report.report_id == report_id:
                    if active.rollout_evidence_binding is not binding:
                        raise RecordingOpenConflict()
                    require_capture_owner(context, active, binding)
                if pending is not None:
                    require_pending_owner(context, active, pending)
        if notice[1] == "saved":
            store = archive_store(context)
            if store is None or notice[2] not in store.snapshot().available_evidence_ids:
                raise RecordingOpenConflict()
    return guard


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


def handle_saved_analysis_get(handler, path):
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

                    handler._rendered_language_source = capture_language_source_v1(context, path)
                    handler._content_page(area, return_to=path,
                        title=text(locale, "saved_analysis.title"),
                        content=render_saved_analysis(value, path, locale),
                        feedback_identity=scope,
                        untranslated_workflow_body=False)
            return True
        snapshot = None if store is None else store.snapshot()
        entries = (() if snapshot is None else tuple(entry for entry in snapshot.manifest.evidence
                   if entry.envelope.kind.startswith(family + "_")))
        body = ""
        refs = () if snapshot is None else tuple(
            entry.envelope for entry in entries
            if entry.identity in snapshot.available_evidence_ids)
        from contextlib import nullcontext
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
                feedback_identity=scope,
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
