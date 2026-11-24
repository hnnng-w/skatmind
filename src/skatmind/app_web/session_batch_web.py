"""Native saved Session decisions, scope controls and bounded passive run reads."""

import hmac
from html import escape

from skatmind.errors import SkatMindError
from skatmind.rollout_derivation import missing_rollout_settlement_inputs
from skatmind.session_transitions import replay_session_state_v1
from skatmind.whole_game_rollout_workflow import parse_rollout_settings

from . import session_batch as job
from .analysis_controls import EFFORTS, AnalysisControlError
from .language_context import capture_language_source_v1
from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
from .saved_match_analyses import (
    SAVED_SESSION_ROUTE,
    archive_store,
    selection_status,
    validate_saved_delivery,
)
from .session_batch_routes import DECISION, DECISIONS, OVERVIEW, PAGE, WATCH
from .session_evidence_retention import session_delivery_guard, session_source_epoch
from .session_learning_rendering import session_receipt
from .session_recorded_review import project_recorded_session_decisions_v1
from .session_recorded_review_form import (
    parse_recorded_rollout_supplements_v1,
    recorded_rollout_feedback_v1,
)
from .session_recorded_review_rendering import _decision_label, render_recorded_session_decisions_v1
from .stateful_localization import card_name, managed_name, player_name, text, translated
from .task_first_projections import project_task_first_session_v1
from .task_first_rendering import disclosure, form, hidden, input_field, paragraph, select_field
from .task_first_session_rendering import _analysis_controls, _analysis_result
from .validation_contracts import FrontendValidationIssueV1
from .whole_match_plan import OwnPlay
from .whole_match_progress import file_identity
from .whole_match_web import batch_settings, comparison_document, link


def original(active, state, entry, play, token):
    material = f"{job.proof(active, state)}:{play}:{entry.identity}:{token}"
    signature = hmac.digest(active.review_selection_key, material.encode(), "sha256").hex()
    return f"{SAVED_SESSION_ROUTE}/{token}/from-game/{play}/{signature}"


def require_origin(app, origin):
    from .saved_match_analyses import resolve_saved_analysis
    active = app.managed_stateful.active_session
    if active is None:
        raise RecordingOpenConflict()
    with active.lock:
        state = job.progress_file(app, active).read()
        require_recording_fresh_v1(active, "sessions")
        if (not state or state["source"] != active.document.content_fingerprint
                or state["file"] != file_identity(active.path)):
            raise RecordingOpenConflict()
        _, _, _, value = resolve_saved_analysis(app, origin["token"])
        ref = state["refs"].get("1:" + origin["play"])
        detail = origin[0] if not origin["destination"] else origin[0].rsplit("/", 1)[0]
        if (not ref or ref[1] != value.entry.identity or not hmac.compare_digest(detail,
                original(active, state, value.entry, origin["play"], origin["token"]))
                or app.managed_stateful.active_session is not active):
            raise RecordingOpenConflict()
        return active


def roots(active):
    return tuple(row.checkpoint.request.to_dict()["document"]
                 for row in project_recorded_session_decisions_v1(active).decisions)


def start_feedback(app, active, binding):
    row = app.form_feedback.current("sessions", active_identity=active)
    if (row and row.form_key == "session.batch.start"
            and row.safe_visible_values.singular("binding") == binding):
        return row
    return None


def submit(handler, path, values):
    app = handler.server.app_context
    active = handler._active_session()
    binding = values.pop("binding", "")
    config = None
    action = path.rsplit("/", 1)[1]
    try:
        if action == "start":
            with active.lock, app.lock:
                current = job.proof(active, job.progress_file(app, active).read())
                feedback = start_feedback(app, active, current)
                if (not hmac.compare_digest(binding, current)
                        or values.pop("retry_generation", None) != (
                            str(feedback.feedback_generation) if feedback else None)):
                    raise RecordingOpenConflict()
            settings = batch_settings(values)
            originals = roots(active)
            missing = {k for root in originals for k in missing_rollout_settlement_inputs(root)}
            allowed = {"objective", "analysis_effort", "random_seed",
                       *(f"analysis_{k}" for k in missing)}
            if values.keys() - allowed:
                raise ValueError("Unknown game setting.")
            extras = {}
            for root in originals:
                fields = {k: values.get("analysis_" + k, "")
                          for k in missing_rollout_settlement_inputs(root)}
                extras.update(parse_recorded_rollout_supplements_v1(
                    fields, root, settings.objective, require_missing=False))
            config = settings, extras
        elif values:
            raise ValueError("Unexpected fields.")
        job.control(app, active, action, binding, config)
    except (OSError, RuntimeError, SkatMindError):
        handler._send_common_error(409)
        return
    except ValueError as error:
        if action != "start":
            handler._send_common_error(400)
            return
        with active.lock, app.lock:
            if (app.managed_stateful.active_session is not active or app.session_batch.worker
                    or binding != job.proof(active, job.progress_file(app, active).read())):
                handler._send_common_error(409)
                return
            issue = (FrontendValidationIssueV1(field_key=error.field_key,
                message_key="validation.message.choice") if isinstance(error, AnalysisControlError)
                else recorded_rollout_feedback_v1(error, status=400))
            handler._retain_form_feedback(handler._current_form_definition, issues=(issue,),
                                          status=400)
        render(handler, PAGE, status=400)
        return
    if action == "start":
        handler._clear_redirect_feedback()
    handler._redirect(PAGE, clear_feedback=False)


def comparisons(app, active, state, locale):
    coverage, rows = job.plan(active, parse_rollout_settings(state["settings"]),
                              state["supplements"].get("1", {}))
    store = archive_store(app) if state["refs"] else None
    values = {}
    snapshot = store.snapshot(_admitted=values) if store else None
    body = paragraph(locale, "recorded_review.coverage", available=len(rows),
                     recorded=coverage.local_play_count)
    if coverage.missing_snapshot_count:
        body += paragraph(locale, "recorded_review.missing", count=coverage.missing_snapshot_count)
    for reason, count in coverage.unavailable_counts:
        if count:
            body += paragraph(locale, "recorded_review." + reason, count=count)
    body += ('<div class="workflow-table-scroll" role="region" tabindex="0" aria-label="'
             + translated(locale, "whole_review.overview") + '"><table><thead><tr>') + "".join(
        '<th scope="col">' + translated(locale, k) + '</th>' for k in (
            "whole_review.decision", "whole_review.actual", "rollout.success", "whole_review.best",
            "rollout.success", "whole_review.details")) + '</tr></thead><tbody>'
    ids = []
    scope = app.saved_match_analyses
    facts = replay_session_state_v1(active.state)
    plays = facts.plays
    if facts.recording_rule_end:
        plays = plays[:facts.recording_rule_end.decisive_play_count]
    available = {row.checkpoint.decision_index: (key, row, reason, request)
                 for key, row, reason, _, request in rows}
    for index, (player, actual) in enumerate(plays, 1):
        if player != active.state.local_player_id:
            continue
        if index not in available:
            body += (f'<tr><th scope="row">{index}</th><td>' + escape(card_name(locale, actual))
                     + '</td><td colspan="4">' + translated(locale, "batch.no_checkpoint")
                     + '</td></tr>')
            continue
        key, row, reason, request = available[index]
        ref = state["refs"].get(key)
        value = values.get(ref[1]) if ref else None
        if (value and value.entry.envelope.kind == "session_rollout"
                and value.source.document == active.document and value.checkpoint == row.checkpoint
                and value.observation == row.observation and value.execution.request == request):
            ids.append(ref[1])
            body += comparison_document(locale, OwnPlay(1, row.checkpoint.decision_index,
                row.observation.actual_card, "", ()), value.execution.result.result.document,
                link(locale, original(active, state, value.entry, row.checkpoint.decision_index,
                    scope.token(snapshot.manifest.space_id, value.entry)), "saved_analysis.open")
                + paragraph(locale, selection_status(snapshot.manifest, value.entry, locale)))
        else:
            body += (f'<tr><th scope="row">{index}</th><td>'
                     + escape(card_name(locale, actual)) + '</td><td colspan="4">'
                     + translated(locale, reason or ("whole_review.absent" if ref else
                                  "whole_review.pending")) + '</td></tr>')
    guard = (lambda: validate_saved_delivery(app, scope, store, snapshot.manifest,
                                             evidence_ids=ids)) if snapshot else None
    return body + '</tbody></table></div>', guard


def render(handler, path, status=200, *, origin=None):
    app = handler.server.app_context
    active = handler._active_session() if origin is None else require_origin(app, origin)
    locale = handler._frontend_state().locale
    progress = job.progress_file(app, active)
    watch = WATCH.fullmatch(path)
    try:
        with active.lock:
            if not watch:
                require_recording_fresh_v1(active, "sessions")
                if active.live.effort is not None:
                    active.live.configure(None)
            document, generation = active.document, active.generation
            coordinator, epoch = session_source_epoch(active)
            state = progress.read()
            binding = job.proof(active, state)
            current = state and state["source"] == document.content_fingerprint and (
                state["file"] == file_identity(active.path))
        guard = None
        def final():
            if guard:
                guard()
            if origin:
                require_origin(app, origin)
            with active.lock, app.lock:
                if (active.document is not document or active.generation != generation
                        or coordinator.generation != epoch
                        or app.managed_stateful.active_session is not active
                        or job.proof(active, progress.read()) != binding):
                    raise RecordingOpenConflict()
                if not watch or watch[2] == "results":
                    require_recording_fresh_v1(active, "sessions")
        handler._retained_delivery_guard = final
        if watch and (not current or watch[1] != binding):
            raise RecordingOpenConflict()
        title = managed_name(locale, app.frontend_profile.document, "sessions",
                             document.state.session_id)
        player = player_name(locale, document.state.players, document.state.local_player_id)
        body = '<p>' + escape(title + " · " + player) + '</p>'
        detail = origin[0].rsplit("/", 1)[0] if origin else None
        recording = detail + "/recording" if detail else "/sessions/current"
        body += link(locale, recording + "#session-recording", "batch.back")
        if path == DECISIONS or DECISION.fullmatch(path):
            with active.lock:
                view = project_recorded_session_decisions_v1(active)
                body += '<p>' + link(locale, PAGE, "batch.session") + '</p>'
                body += '<h2>' + translated(locale, "match_nav.single") + '</h2>'
                chosen = next((row for row in view.decisions if path.endswith(row.selection)), None)
                if chosen is None and path != DECISIONS:
                    raise RecordingOpenConflict()
                active.review_page = path
                chosen = chosen or next(iter(view.decisions), None)
                if len(view.decisions) > 1:
                    body += '<ul>' + ''.join(f'<li><a href="{DECISIONS}/{row.selection}">'
                        + _decision_label(locale, document.state.players, row) + '</a></li>'
                        for row in view.decisions) + '</ul>'
                body += render_recorded_session_decisions_v1(active, locale=locale,
                    view=view, selected=chosen)
                body += disclosure(locale, "analysis.technical", _analysis_controls(active, locale,
                    project_task_first_session_v1(active.state)))
                body += session_receipt(active, locale) + _analysis_result(active, locale, title)
                guard = session_delivery_guard(app, active)
                notice = active.evidence_notice
                if notice and notice[1] == "saved":
                    from .saved_match_analyses import selection_form
                    scope, store = app.saved_match_analyses, archive_store(app)
                    snapshot = store.snapshot()
                    entry = next((e for e in snapshot.manifest.evidence
                                  if e.identity == notice[2]), None)
                    if entry is None:
                        raise RecordingOpenConflict()
                    body += selection_form(scope, snapshot.manifest, entry, locale)
                    source_guard = guard
                    def guard():
                        source_guard()
                        validate_saved_delivery(app, scope, store, snapshot.manifest,
                                                evidence_ids=(entry.identity,))
        else:
            worker = app.session_batch.worker
            running = current and worker and worker.active is active and (
                worker.state["run"] == state["run"])
            phase = ("stopping" if worker.stop.is_set() else "working") if running else (
                "paused" if current and state["phase"] == "working" else state and state["phase"])
            if current:
                count = sum(ref[0] != "saving" for ref in state["refs"].values())
                cached = app.session_batch.plan
                if not cached or cached[:2] != (binding, generation):
                    _, rows = job.plan(active, parse_rollout_settings(state["settings"]),
                                       state["supplements"].get("1", {}))
                    cached = app.session_batch.plan = binding, generation, sum(
                        reason is None for _, _, reason, _, _ in rows)
                label = text(locale, "batch.session_stopping" if phase == "stopping" else
                             "whole_review." + phase) + " · " + text(
                                 locale, "batch.processed", count=count, total=cached[2])
            if watch and watch[2] == "status":
                handler._send_json(200, {"phase": phase, "processed": count, "label": label})
                return
            if watch:
                fragment, guard = comparisons(app, active, state, locale)
                handler._send_bytes(200, fragment.encode(), content_type="text/html; charset=utf-8")
                return
            body += '<h2>' + translated(locale, "batch.session") + '</h2>'
            body += link(locale, detail + "/review" if detail else DECISIONS, "match_nav.single")
            if current:
                body += f'<p data-batch-watch="{PAGE}/watch/{binding}" role="status" '
                body += 'data-unavailable="' + translated(locale, "batch.unavailable") + '">'
                body += escape(label) + '</p>'
                settings = state["settings"]
                body += paragraph(locale, "whole_review.settings", objective=text(locale,
                    "rollout.objective." + settings["objective"]),
                    worlds=settings["requested_worlds"],
                    seconds=settings["wall_clock_timeout_ms"] // 1000, seed=settings["random_seed"])
                action = "cancel" if running else "resume"
                body += '<div data-batch-cancel>' + form(locale, PAGE + "/" + action,
                    hidden("binding", binding), "whole_review." + action) + '</div>'
                if running:
                    body += '<div data-batch-resume hidden>' + form(locale, PAGE + "/resume",
                        hidden("binding", binding), "whole_review.resume") + '</div>'
                body += '<div data-batch-native>' + link(locale, PAGE, "whole_review.refresh")
                body += link(locale, OVERVIEW, "whole_review.overview") + '</div>'
                if path == OVERVIEW:
                    fragment, guard = comparisons(app, active, state, locale)
                    body += (fragment if origin else
                             f'<div data-batch-results data-processed="{count}">{fragment}</div>')
                else:
                    body += '<div data-batch-results></div>'
            if not running and path != OVERVIEW:
                fields = hidden("binding", binding) + select_field(locale, "objective",
                    "rollout.objective", [(v, text(locale, "rollout.objective." + v)) for v in (
                        "complete_settlement", "played_game_goal")], "complete_settlement")
                fields += select_field(locale, "analysis_effort", "analysis.effort",
                     [(v, text(locale, "analysis.effort." + v)) for v in EFFORTS], "standard")
                feedback = start_feedback(app, active, binding)
                if feedback:
                    fields += hidden("retry_generation", feedback.feedback_generation)
                fields += disclosure(locale, "analysis.technical",
                    input_field(locale, "random_seed", "rollout.seed", "0"), technical=True)
                assumptions = ""
                for k in sorted({k for root in roots(active)
                                 for k in missing_rollout_settlement_inputs(root)}):
                    assumptions += input_field(locale, "analysis_" + k, "rollout.analysis_" + k)
                if assumptions:
                    fields += disclosure(locale, "whole_review.assumptions",
                        paragraph(locale, "whole_review.assumptions_help") + assumptions)
                start = form(locale, PAGE + "/start", fields, "batch.game_start", primary=True)
                body += disclosure(locale, "whole_review.new", start) if current else start
        return_to = origin[0] if origin and origin["destination"] == "overview" else path
        handler._rendered_language_source = capture_language_source_v1(app, return_to,
            session_batch_binding=binding if path in (PAGE, OVERVIEW) else None)
        handler._content_page("/sessions", return_to=return_to, title=title, content=body,
            feedback_identity=active, feedback_family="sessions", untranslated_workflow_body=False,
            analysis=True, status=status)
    except (OSError, RuntimeError, ValueError, SkatMindError):
        handler._retained_delivery_guard = None
        handler._send_common_error(409)
