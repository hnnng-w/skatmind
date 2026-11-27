"""Native recorded-Match review controls and original-evidence comparisons."""

import hmac
import re
from contextlib import nullcontext
from html import escape

from skatmind.errors import SkatMindError
from skatmind.game_declaration import validate_bid_value, validate_matadors
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

from .analysis_controls import (
    DEFAULT_ANALYSIS_EFFORT,
    AnalysisControlError,
    effort_select,
    resolve_analysis_controls,
)
from .frontend_profile_contracts import effort_preferences
from .language_context import LanguageContextConflict, capture_language_source_v1
from .match_navigation import match_navigation
from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
from .render_locale import localized_render
from .rollout_result_numbers import simulation_success
from .saved_match_analyses import SAVED_MATCH_ROUTE, saved_analyses_link, selection_status
from .session_recorded_review_form import RecordedRolloutFormError, recorded_rollout_feedback_v1
from .stateful_localization import card_name, managed_name, player_name, text, translated
from .task_first_rendering import disclosure, form, hidden, input_field, paragraph, select_field
from .validation_contracts import FrontendValidationIssueV1
from .whole_match_job import control, evidence_view, progress_file, proof, row_options
from .whole_match_progress import file_identity, result_revision
from .whole_match_routes import OVERVIEW, PAGE, WHOLE_SETUP, game_scope, original_path

_localized_success = localized_render(simulation_success)


def link(locale, path, key):
    return f'<a class="button-link secondary" href="{path}">{translated(locale, key)}</a>'


def missing_fields(rows):
    return sorted({(row.position, name) for row in rows for name in row.missing})


def batch_settings(values):
    if values.get("objective") not in ("played_game_goal", "complete_settlement"):
        raise RecordedRolloutFormError("invalid_objective", "objective")
    seed = values.get("random_seed") or "0"
    if not re.fullmatch(r"[0-9]{1,20}", seed) or int(seed) >= 2**64:
        raise RecordedRolloutFormError("invalid_random_seed", "random_seed")
    effective, timeout = resolve_analysis_controls({"settings_mode": "ordinary",
        "analysis_effort": values.get("analysis_effort")}, path="rollout")
    return WholeGameRolloutSettingsV1(objective=values["objective"],
        requested_worlds=int(effective["requested_worlds"]), random_seed=int(seed),
        wall_clock_timeout_ms=timeout)


def configuration(values, workspace, rows):
    fields = missing_fields(rows)
    if values.keys() - {"objective", "analysis_effort", "random_seed",
                        *(f"{name}_{p}" for p, name in fields)}:
        raise RecordedRolloutFormError("invalid_fields")
    settings = batch_settings(values)
    supplements = {}
    for p, name in fields:
        field = f"{name}_{p}"
        raw = values.get(field)
        if raw and settings.objective == "complete_settlement":
            game_type = workspace.slots[p-1].observed_game.declaration.game_type
            try:
                if not re.fullmatch(r"[0-9]{1,20}", raw):
                    raise ValueError("Invalid game supplement.")
                value = int(raw)
                if name == "bid_value":
                    validate_bid_value(value)
                else:
                    validate_matadors(value, game_type)
            except ValueError as error:
                reason = ("invalid_bid" if name == "bid_value" else
                          "invalid_matadors_grand" if game_type == "grand" else
                          "invalid_matadors_suit")
                raise RecordedRolloutFormError(reason, field) from error
            supplements.setdefault(str(p), {})[name] = value
    return settings, supplements


def start_form(locale, rows, binding, feedback, game=None, *,
               default_effort=DEFAULT_ANALYSIS_EFFORT):
    inputs = hidden("binding", binding)
    if game is not None:
        inputs += hidden("game", game)
    if feedback is not None:
        inputs += hidden("retry_generation", feedback.feedback_generation)
    inputs += effort_select(locale, "analysis_effort", "analysis.effort", default_effort)
    inputs += select_field(locale, "objective", "rollout.objective",
        [(o, text(locale, "rollout.objective." + o))
         for o in ("complete_settlement", "played_game_goal")], "complete_settlement")
    inputs += disclosure(locale, "analysis.technical",
                         paragraph(locale, "whole_review.budgets")
                         + input_field(locale, "random_seed", "rollout.seed", "0"), technical=True)
    assumptions = ""
    for p, name in missing_fields(rows):
        assumptions += ('<fieldset><legend>' + translated(locale, "accounting.game_number",
            number=p) + '</legend>' + input_field(locale, f"{name}_{p}", "rollout.analysis_"
            + name, kind="number") + '</fieldset>')
    if assumptions:
        inputs += disclosure(locale, "whole_review.assumptions",
                             paragraph(locale, "whole_review.assumptions_help") + assumptions)
    return form(locale, PAGE + "/start", inputs, "whole_review.start" if game is None else
                "batch.game_start", primary=True)


def comparison(locale, row, retained, detail):
    doc = retained.report.value.result.document
    return comparison_document(locale, row, doc, detail)


def comparison_document(locale, row, doc, detail):
    result = doc["whole_game_rollout_result"]
    best = result["tied_best_cards"]
    if not best:
        return ('<tr><th scope="row">' + str(row.decision) + '</th><td>'
                + escape(card_name(locale, row.actual)) + '</td><td colspan="3">'
                + translated(locale, "rollout.reason." + result["stop_reason"])
                + f' ({result["completed_common_worlds"]}/{result["settings"]["requested_worlds"]})'
                + '</td><td>' + detail + '</td></tr>')
    candidates = {v["card"]: v for v in result["candidates"]}
    actual, recommended = candidates[row.actual], candidates[best[0]]
    metric = doc["whole_game_rollout_comparison"]["responsible_metric"]
    def metrics(v):
        out = escape(_localized_success(v["local_success_count"], v["completed_samples"],
                                        locale=locale))
        if metric in ("total_local_game_score", "total_local_card_point_margin"):
            # Exact totals with common denominators also distinguish close means.
            out += '<br>' + translated(locale, "rollout.metric." + metric)
            out += f': {v[metric]}/{v["completed_samples"]}'
        return out
    return (f'<tr><th scope="row">{row.decision}</th><td>' + escape(card_name(locale, row.actual))
        + '</td><td>' + metrics(actual) + '</td><td>'
        + escape(", ".join(card_name(locale, c) for c in best))
        + '</td><td>' + metrics(recommended) + '</td><td>' + detail + '</td></tr>')


def _game_links(position, origin):
    if origin is not None and position == int(origin["game"]):
        detail = origin[0].removesuffix("/overview")
        return detail + "/recording#match-recording", detail + "/review"
    return f"/matches/position/{position}#match-recording", f"/matches/review/{position}"


def overview(app, workspace, state, rows, options, values, manifest, locale, binding, title, *,
             origin=None):
    refs = state["refs"]
    body = []
    counts = {"complete": 0, "forced": 0, "incomplete": 0}
    for slot in workspace.slots:
        p = slot.match_position
        if state.get("game", p) != p:
            continue
        heading = translated(locale, "accounting.game_number", number=p)
        section = (f'<section class="panel" id="game-{p}" tabindex="-1">'
                   + '<p class="comparison-location">' + escape(title) + ' · '
                   + translated(locale, "match_nav.review") + f'</p><h2>{heading}</h2>')
        game = slot.observed_game
        if game is None:
            body.append(section + paragraph(locale, "task.match.status." + slot.slot_kind)
                        + '</section>')
            continue
        section += paragraph(locale, "whole_review.plays", count=len(game.plays))
        recording, _ = _game_links(p, origin)
        section += f'<p><a href="{recording}">' + translated(
            locale, "recordings.continue", number=p) + '</a></p>'
        if game.declaration:
            section += paragraph(locale, "task.value." + game.declaration.game_type)
            if game.declaration.game_type == "null":
                section += paragraph(locale, "rollout.reason.unsupported_game_type")
        if game.declarer_player_id:
            side = ("declarer" if game.declarer_player_id == game.perspective_player_id
                    else "defenders")
            section += paragraph(locale, "rollout.party." + side)
        for name, value in state["supplements"].get(str(p), {}).items():
            section += '<p>' + translated(locale, "rollout.analysis_" + name) + f': {value}</p>'
        table = []
        for row in rows:
            if row.position != p:
                continue
            ref = refs.get(row.key)
            value = values.get(ref[1]) if ref else None
            if (value is not None and value.report.match_position == p
                    and value.report.decision_index == row.decision):
                token = app.saved_match_analyses.token(manifest.space_id, value.entry)
                table.append(comparison(locale, row, value,
                    link(locale, original_path(app.saved_match_analyses, binding, token, p,
                         row.decision, value.entry.identity), "saved_analysis.open")
                    + paragraph(locale, selection_status(manifest, value.entry, locale))))
                counts["complete" if value.comparison is not None else "incomplete"] += 1
                continue
            reason = ("recordings.skip." + row.reason if row.reason in (
                "after_rule_end", "acting_hand_unavailable", "required_public_hand_unavailable")
                else "whole_review.forced" if row.reason == "forced"
                else "rollout.reason.unsupported_game_type" if row.reason
                else "rollout.reason.missing_terminal_utility_inputs" if options[row.key] is None
                else "whole_review.absent" if ref else "whole_review.pending")
            counts["forced"] += row.reason == "forced"
            table.append(f'<tr><th scope="row">{row.decision}</th><td>'
                + escape(card_name(locale, row.actual)) + '</td><td colspan="4">'
                + translated(locale, reason) + '</td></tr>')
        if table:
            section += (f'<div class="workflow-table-scroll" role="region" aria-label="{heading}" '
                        'tabindex="0"><table><thead><tr>')
            section += ''.join('<th scope="col">' + translated(locale, key) + '</th>' for key in (
                "whole_review.decision", "whole_review.actual", "rollout.success",
                "whole_review.best", "rollout.success", "whole_review.details"))
            section += '</tr></thead><tbody>' + ''.join(table) + '</tbody></table></div>'
        body.append(section + '</section>')
    jumps = ' · '.join(f'<a href="#game-{p}">{p}</a>' for p in range(1, 37)
                       if state.get("game", p) == p)
    return (paragraph(locale, "whole_review.coverage", total=len(rows), **counts)
            + ("" if state.get("game") else disclosure(locale, "whole_review.overview", jumps))
            + ''.join(body))


def _start_feedback(app, active, binding):
    state = app.form_feedback.current("matches", active_identity=active)
    if (state is not None and state.form_key == "match.whole_review.start"
            and state.safe_visible_values.singular("binding") == binding):
        return state
    return None


def handle_get(handler, path, *, rejection=None, origin=None):
    app = handler.server.app_context
    active = handler._active_match() if origin is None else require_origin(app, origin)
    locale = handler._frontend_state().locale
    progress = progress_file(app, active)
    game = game_scope(path)
    with active.capture.lock:
        require_recording_fresh_v1(active, "matches")
        if active.live.effort is not None:
            active.live.configure(None)
        workspace, source = active.workspace, active.capture.content_fingerprint
        state = progress.read()
        binding = proof(active, state, requested_game=game)
        position = active.selected_position if origin is None else int(origin["game"])
        current = (state is not None and state["source"] == source
                   and state["file"] == file_identity(active.path))
        if game is not None:
            position = game
            current = current and state.get("game") == game
        elif current and state.get("game") and path == WHOLE_SETUP:
            current = False
        elif current and state.get("game") and origin is None:
            position = state["game"]
        reading = current and path == OVERVIEW
        with app.lock:
            if app.managed_stateful.active_match is not active:
                raise RecordingOpenConflict()
            feedback = None if reading else _start_feedback(app, active, binding)
            if rejection is not None and feedback is not rejection:
                raise RecordingOpenConflict()
            profile = app.frontend_profile.document
            return_to = path if origin is None else origin[0]
            handler._rendered_language_source = capture_language_source_v1(
                app, return_to, whole_match_binding=binding)
    definition = workspace.match_definition
    title = managed_name(locale, profile, "matches", definition.match_id, definition.title)
    recording, review = _game_links(position, origin)
    body = match_navigation(locale, title, position, recording=recording)
    scope_game = state.get("game") if current else game
    scope_title = (text(locale, "batch.game", number=scope_game) if scope_game
                   else text(locale, "whole_review.title"))
    body += f'<p><a href="{review}">' + translated(
        locale, "recordings.match.open", number=position) + '</a></p>'
    body += paragraph(locale, "whole_review.intro", player=player_name(
        locale, definition.participants, definition.perspective_player_id),
        match=title, revision=workspace.revision)
    worker = app.whole_match.worker
    running = current and worker and worker.owns_source() and worker.state["run"] == state["run"]
    rows = app.whole_match.plays(workspace, scope_game)
    options = row_options(rows, state) if current else {}
    with (evidence_view(app, workspace, source, options) if reading else
            nullcontext(({}, None, None))) as (values, space, archive_guard):
        if current:
            settings = state["settings"]
            phase = (("stopping" if worker.stop.is_set() else "working") if running else
                     "paused" if state["phase"] == "working" else state["phase"])
            run_binding = proof(active, state)
            watch = f"{PAGE}/watch/{run_binding}"
            body += f'<p data-batch-watch="{watch}" role="status" aria-live="polite" '
            body += 'data-unavailable="' + translated(locale, "batch.watch_unavailable") + '">'
            body += translated(locale, "whole_review." + phase) + '</p>'
            body += paragraph(locale, "whole_review.settings", objective=text(locale,
                "rollout.objective." + settings["objective"]), worlds=settings["requested_worlds"],
                seed=settings["random_seed"], seconds=settings["wall_clock_timeout_ms"] // 1000)
            body += '<p data-batch-counts>' + escape(_counts(locale, rows, state)) + '</p>'
            action = "cancel" if running else "resume"
            body += '<div data-batch-cancel>' + form(locale, PAGE + "/" + action,
                hidden("binding", run_binding), "whole_review." + action) + '</div>'
            if running:
                body += '<div data-batch-resume hidden>' + form(locale, PAGE + "/resume",
                    hidden("binding", run_binding), "whole_review.resume") + '</div>'
            body += ('<div data-batch-native><p>' + link(locale, PAGE, "whole_review.refresh")
                     + '</p>')
            body += ("" if reading else link(locale, OVERVIEW, "whole_review.overview")) + '</div>'
            if reading:
                fragment = overview(app, workspace, state, rows, options, values, space, locale,
                                    binding, title, origin=origin)
                body += (fragment if origin else
                         f'<div data-batch-results data-revision="{result_revision(state)}">'
                         f'{fragment}</div>')
                values.clear()
            else:
                body += '<div data-batch-results></div>'
        elif state and game is None and path != WHOLE_SETUP:
            body += paragraph(locale, "whole_review.changed")
        if not running and not reading and not (current and scope_game and game is None):
            fields = start_form(locale, rows, binding, feedback, game,
                                default_effort=effort_preferences(profile).analysis_effort)
            body += disclosure(locale, "whole_review.new", fields) if current else fields
            if feedback and not current:
                body += '<p>' + link(locale, PAGE, "whole_review.refresh") + '</p>'
        elif current and scope_game and not reading:
            body += link(locale, WHOLE_SETUP, "whole_review.title")
        body += saved_analyses_link(locale)
        def final():
            if archive_guard:
                archive_guard()
            if origin is not None:
                require_origin(app, origin)
            with active.capture.lock, app.lock:
                now = progress.read()
                if (app.managed_stateful.active_match is not active
                        or active.workspace is not workspace
                        or proof(active, now, requested_game=game) != binding
                        or reading and now != state
                        or not reading and _start_feedback(app, active, binding) is not feedback):
                    raise RecordingOpenConflict()
                require_recording_fresh_v1(active, "matches")
        handler._retained_delivery_guard = final
        handler._content_page("/matches", title=scope_title,
            return_to=return_to, content=body, untranslated_workflow_body=False, task_first=True,
            status=400 if rejection is not None else 200, feedback_identity=active, analysis=True,
            feedback_family="matches" if feedback else None)


def require_origin(app, origin):
    """Re-admit a link minted for an exact admitted overview row, never by caption."""
    with app.lock:
        active = app.managed_stateful.active_match
    if active is None:
        raise RecordingOpenConflict()
    with active.capture.lock:
        require_recording_fresh_v1(active, "matches")
        state = progress_file(app, active).read()
        ref = state and state["refs"].get(f'{origin["game"]}:{origin["play"]}')
        if (not ref or active.retired or state["source"] != active.capture.content_fingerprint
                or state["file"] != file_identity(active.path)):
            raise RecordingOpenConflict()
        expected = original_path(app.saved_match_analyses, proof(active, state), origin["token"],
                                 origin["game"], origin["play"], ref[1])
        detail = origin[0] if origin["destination"] is None else origin[0].rsplit("/", 1)[0]
        with app.lock:
            if app.managed_stateful.active_match is not active or not hmac.compare_digest(
                    detail, expected):
                raise RecordingOpenConflict()
        return active


def origin_fallback(handler, origin):
    route = SAVED_MATCH_ROUTE + "/" + origin["token"]
    locale = handler._frontend_state().locale
    handler._rendered_language_source = None
    handler._retained_delivery_guard = None
    handler._content_page("/matches", return_to=route, status=409,
        title=text(locale, "saved_analysis.title"), content=paragraph(locale, "match_nav.stale")
        + link(locale, route, "saved_analysis.open") + saved_analyses_link(locale),
        untranslated_workflow_body=False, analysis=True)


def return_from_original(handler, origin):
    app = handler.server.app_context
    handler._retained_delivery_recovery = lambda: origin_fallback(handler, origin)
    try:
        if origin["destination"] == "overview":
            handle_get(handler, OVERVIEW, origin=origin)
        else:
            active = require_origin(app, origin)
            handler._match_page(active, position=int(origin["game"]), match_origin=origin,
                                review=origin["destination"] == "review")
    except (KeyError, OSError, ValueError, RecordingOpenConflict, LanguageContextConflict,
            SkatMindError):
        origin_fallback(handler, origin)


def _start(handler, active, binding, values):
    app = handler.server.app_context
    workspace = active.workspace
    retry = values.pop("retry_generation", None)
    game = values.pop("game", None)
    if game is not None:
        if not re.fullmatch(r"[1-9]|[12][0-9]|3[0-6]", game):
            raise RecordingOpenConflict()
        game = int(game)
    with active.capture.lock, app.lock:
        if (app.managed_stateful.active_match is not active or active.retired
                or not hmac.compare_digest(proof(active, progress_file(app, active).read(),
                                                 requested_game=game), binding)):
            raise RecordingOpenConflict()
    try:
        config = configuration(values, workspace, app.whole_match.plays(workspace, game))
        issue = None
    except RecordedRolloutFormError as error:
        issue = recorded_rollout_feedback_v1(error, status=400)
    except AnalysisControlError as error:
        issue = FrontendValidationIssueV1(field_key=error.field_key,
                                          message_key="validation.message.choice")

    with active.capture.lock, app.lock:
        if app.managed_stateful.active_match is not active or active.workspace is not workspace:
            raise RecordingOpenConflict()
        feedback = _start_feedback(app, active, binding)
        if retry != (str(feedback.feedback_generation) if feedback else None):
            raise RecordingOpenConflict()
        if issue is None:
            control(app, active, "start", binding, configuration=config, game=game)
            handler._clear_redirect_feedback()
        else:
            require_recording_fresh_v1(active, "matches")
            current = proof(active, progress_file(app, active).read(), requested_game=game)
            if (active.retired or app.whole_match.worker
                    or not hmac.compare_digest(current, binding)):
                raise RecordingOpenConflict()
            handler._retain_form_feedback(handler._current_form_definition, issues=(issue,),
                                          status=400)
            rejected = app.form_feedback.current("matches", active_identity=active)
    if issue is None:
        handler._redirect(PAGE, clear_feedback=False)
    else:
        target = f"{PAGE}/game/{game}" if game else (
            WHOLE_SETUP if (progress_file(app, active).read() or {}).get("game") else PAGE)
        handle_get(handler, target, rejection=rejected)


def _counts(locale, rows, state):
    refs = state["refs"].values()
    return text(locale, "whole_review.progress", total=len(rows),
                computed=sum(ref[0] == "computed" for ref in refs),
                reused=sum(ref[0] == "reused" for ref in refs))


def watch_run(handler, watch):
    """Poll the bounded checkpoint; admit original evidence only for a result projection."""
    app = handler.server.app_context
    active = handler._active_match()
    locale = handler._frontend_state().locale
    progress = progress_file(app, active)

    def checked():
        state = progress.read()
        if (active.retired or app.managed_stateful.active_match is not active or state is None
                or state["source"] != active.capture.content_fingerprint
                or state["file"] != file_identity(active.path)
                or not hmac.compare_digest(proof(active, state), watch[1])
                or _start_feedback(app, active, watch[1]) is not None):
            raise RecordingOpenConflict()
        return state

    try:
        with active.capture.lock, app.lock:
            state = checked()
            workspace = active.workspace
            worker = app.whole_match.worker
            running = worker and worker.owns_source() and worker.state["run"] == state["run"]
            phase = ("stopping" if worker.stop.is_set() else "working") if running else (
                "paused" if state["phase"] == "working" else state["phase"])
        rows = app.whole_match.plays(workspace, state.get("game"))
        options = row_options(rows, state)
        count = sum(ref[0] != "saving" for ref in state["refs"].values())
        def final():
            with active.capture.lock, app.lock:
                checked()
        handler._retained_delivery_guard = final
        if watch[2] == "status":
            handler._send_json(200, {"phase": phase, "processed": count,
                "revision": result_revision(state), "counts": _counts(locale, rows, state),
                "label": text(locale, "whole_review." + phase) + " · " + text(
                    locale, "batch.processed", count=count,
                    total=sum(o is not None for o in options.values()))})
            return
        with evidence_view(app, workspace, state["source"], options) as (values, space, guard):
            title = managed_name(locale, app.frontend_profile.document, "matches",
                workspace.match_definition.match_id, workspace.match_definition.title)
            body = overview(app, workspace, state, rows, options, values, space, locale,
                            watch[1], title)
            def authorize_results():
                guard()
                with active.capture.lock, app.lock:
                    if checked()["refs"] != state["refs"]:
                        raise RecordingOpenConflict()
                require_recording_fresh_v1(active, "matches")
            handler._retained_delivery_guard = authorize_results
            handler._send_bytes(200, body.encode(), content_type="text/html; charset=utf-8",
                                extra_headers=(("X-Result-Revision", result_revision(state)),))
    except (OSError, ValueError, RecordingOpenConflict, SkatMindError):
        handler._retained_delivery_guard = None
        handler._send_common_error(409)


def dispatch(handler, path, values=None):
    try:
        if values is None:
            handle_get(handler, path)
        else:
            active = handler._active_match()
            values = dict(values)
            binding = values.pop("binding")
            if not re.fullmatch("[0-9a-f]{64}", binding):
                raise RecordingOpenConflict()
            action = path.rsplit("/", 1)[1]
            if action == "start":
                _start(handler, active, binding, values)
                return
            if values:
                raise ValueError("Unexpected control fields.")
            app = handler.server.app_context
            with active.capture.lock, app.lock:
                control(app, active, action, binding)
                handler._clear_redirect_feedback()
            handler._redirect(PAGE, clear_feedback=False)
    except (KeyError, ValueError, OSError, RecordingOpenConflict, SkatMindError) as error:
        locale = handler._frontend_state().locale
        handler._retained_delivery_guard = None
        handler._rendered_language_source = None
        handler._content_page("/matches", title=text(locale, "whole_review.title"),
            content=paragraph(locale, "whole_review.error") + link(locale, PAGE,
                "whole_review.refresh") + saved_analyses_link(locale), return_to="/matches",
            status=400 if isinstance(error, ValueError) else 409, untranslated_workflow_body=False,
            analysis=True)
