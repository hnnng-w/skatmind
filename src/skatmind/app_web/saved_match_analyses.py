"""Separate process-owned access to indexed original ordinary Match evidence."""

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


def validate_saved_delivery(context, scope, store, manifest, value=None):
    if context.saved_match_analyses is not scope or scope.store is not store:
        raise RecordingOpenConflict()
    current = store.snapshot()
    if current.manifest != manifest:
        raise RecordingOpenConflict()
    if value is not None and value.entry.identity not in current.available_evidence_ids:
        raise RecordingOpenConflict()


def saved_analyses_link(locale):
    return ('<p><a class="button-link secondary" href="' + SAVED_MATCH_ROUTE + '">'
            + escape(text(locale, "saved_analysis.title")) + '</a></p>')


def retention_feedback(context, active, report_id, locale):
    from .match_evidence_retention import require_pending_owner

    notice = active.evidence_notice
    if notice is None or notice[0] != report_id:
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
    body = '<div role="status">' + paragraph(locale, "saved_analysis." + status) + '</div>'
    if retry:
        body += (f'<form method="post" action="{RETRY_MATCH_ROUTE}">'
            f'<input type="hidden" name="managed_handle" value="{active.handle}">'
            f'<input type="hidden" name="save_token" value="{pending.token}">'
            '<button type="submit">' + escape(text(locale, "saved_analysis.retry")) + '</button>'
            '</form>')
    return body


def live_retention_delivery_guard(context, active, report_id):
    """Bind the new receipt/retry presentation through final HTML delivery."""
    from .match_evidence_retention import require_pending_owner
    from .recorded_review_opening import require_recording_fresh_v1

    with active.capture.lock:
        notice = active.evidence_notice
        if notice is None or notice[0] != report_id:
            return None
        pending = active.pending_evidence
        fingerprint = active.capture.content_fingerprint
        generation = active.capture.report_store.generation
        report = active.capture.report_store.get(report_id)

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
                if pending is not None:
                    require_pending_owner(context, active, pending)
        if notice[1] == "saved":
            store = archive_store(context)
            if store is None or notice[2] not in store.snapshot().available_evidence_ids:
                raise RecordingOpenConflict()
    return guard


def _caption(value, locale):
    report = value.report
    definition = value.source.document.workspace.match_definition
    actor = report.value.profile_binding.acting_player_id
    label = next(player.player_label or player.player_id for player in definition.participants
                 if player.player_id == actor)
    return text(locale, "saved_analysis.caption", match=definition.title or report.match_id,
        game=report.match_position, decision=report.decision_index, actor=label,
        method=text(locale, "saved_analysis.method." + report.value.options.recommendation_method))


def render_saved_analysis(value, route, locale):
    workspace, report = value.source.document.workspace, value.report
    state = {"reports": [], "selected_report": _selected_report_details(report),
        "selected_position": report.match_position,
        "decision_context": match_decision_context(report, workspace),
        "analysis_explanation": match_analysis_explanation(report, workspace),
        "download_availability": {"report_result": False}}
    body = ('<section id="saved-analysis" tabindex="-1"><h2>'
            + escape(_caption(value, locale)) + '</h2>')
    body += paragraph(locale, "saved_analysis.captured", revision=workspace.revision,
        source=value.source.record.source_version.content_fingerprint[:12],
        report=report.report_id[:12])
    body += paragraph(locale, "saved_analysis.historical")
    body += render_match_reports_v1(state, locale, retained_archive=True)
    body += analysis_downloads(request_href=route + "/request.json",
        result_href=route + "/result.json", report_source_href=route + "/strategy-source.json",
        locale=locale)
    return body + '</section>' + saved_analyses_link(locale)


def handle_saved_analysis_get(handler, path):
    match = SAVED_MATCH_PATTERN.fullmatch(path)
    if path != SAVED_MATCH_ROUTE and match is None:
        return False
    context = handler.server.app_context
    scope = context.saved_match_analyses
    locale = handler._frontend_state().locale
    try:
        store = archive_store(context)
        if match is not None:
            scope, store, manifest, value = resolve_saved_analysis(context, match[1])
            with store.pin_objects((value.entry.envelope,), expected_manifest=manifest.fingerprint):
                handler._retained_delivery_guard = lambda: validate_saved_delivery(
                    context, scope, store, manifest, value)
                if match[2]:
                    handler._send_artifact(*value.download(match[2]))
                else:
                    from .language_context import capture_language_source_v1

                    handler._rendered_language_source = capture_language_source_v1(context, path)
                    handler._content_page("/matches", return_to=path,
                        title=text(locale, "saved_analysis.title"),
                        content=render_saved_analysis(value, path, locale),
                        feedback_identity=scope,
                        untranslated_workflow_body=False)
            return True
        snapshot = None if store is None else store.snapshot()
        body = ""
        refs = () if snapshot is None else tuple(
            entry.envelope for entry in snapshot.manifest.evidence
            if entry.identity in snapshot.available_evidence_ids)
        from contextlib import nullcontext
        with (nullcontext() if store is None else store.pin_objects(refs,
                expected_manifest=snapshot.manifest.fingerprint)):
            for entry in () if snapshot is None else snapshot.manifest.evidence:
                if entry.identity not in snapshot.available_evidence_ids:
                    continue
                value = store.read_evidence(entry.identity)
                token = scope.token(snapshot.manifest.space_id, entry)
                body += '<li><p>' + escape(_caption(value, locale)) + '</p>'
                body += paragraph(locale, "saved_analysis.captured",
                    revision=value.source.document.workspace.revision,
                    source=value.source.record.source_version.content_fingerprint[:12],
                    report=value.report.report_id[:12])
                body += (f'<a class="button-link secondary" href="{SAVED_MATCH_ROUTE}/{token}">'
                         + escape(text(locale, "saved_analysis.open")) + '</a></li>')
            body = '<ul class="workflow-list">' + body + '</ul>' if body else paragraph(
                locale, "saved_analysis.empty")
            if snapshot is not None:
                if len(refs) != len(snapshot.manifest.evidence):
                    body += paragraph(locale, "saved_analysis.excluded")
                handler._retained_delivery_guard = lambda: validate_saved_delivery(
                    context, scope, store, snapshot.manifest)
            from .language_context import capture_language_source_v1

            handler._rendered_language_source = capture_language_source_v1(context, path)
            handler._content_page("/matches", return_to=path,
                title=text(locale, "saved_analysis.title"), content=body,
                feedback_identity=scope,
                untranslated_workflow_body=False)
    except (OSError, ValueError, SkatMindError, RecordingOpenConflict):
        handler._retained_delivery_guard = None
        handler._rendered_language_source = None
        handler._content_page("/matches", return_to=SAVED_MATCH_ROUTE,
            title=text(locale, "saved_analysis.title"), status=409,
            content=paragraph(locale, "saved_analysis.blocked"), untranslated_workflow_body=False)
    return True


def handle_retry_saving(handler, values):
    from .match_evidence_retention import save_pending_match

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
    handler._redirect(f"/matches/reports/{pending.report.report_id}")
