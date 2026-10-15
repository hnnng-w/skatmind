"""Native authenticated routes for retained comparisons, never analysis navigation."""

import re

from skatmind.match_analysis_exports import (
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
)

from .debrief_frontend import (
    DebriefUnavailable,
    capture_direct_scope,
    incorporate_report,
    recording_return,
    remove_source,
    resolve_scope,
)
from .debrief_rendering import (
    collection_name,
    link,
    overview_title,
    render_comparison,
    render_debrief,
)
from .language_context import capture_language_source_v1
from .operation_feedback import feedback_source
from .stateful_localization import text
from .task_first_rendering import paragraph

DEBRIEF_FROM_PATTERN = re.compile(r"/learning/debrief/from/([0-9a-f]{64})\Z")
DEBRIEF_INPUTS_PATTERN = re.compile(r"/learning/debrief/([0-9a-f]{64})/(all|[0-9]+)/inputs\Z")
DEBRIEF_PAGE_PATTERN = re.compile(
    r"/learning/debrief/([0-9a-f]{64})/(all|[0-9]+)(?:/([0-9a-f]{64}))?\Z")
DEBRIEF_RESOURCE_PATTERN = re.compile(
    r"(/learning/debrief/([0-9a-f]{64})/(all|[0-9]+)/([0-9a-f]{64}))/"
    r"(recording|request\.json|result\.json)\Z")


def _error(handler, reason, *, return_to="/learning"):
    handler._rendered_language_source = None
    locale = handler._frontend_state().locale
    with handler.server.app_context.lock:
        has_collection = handler.server.app_context.managed_stateful.active_learning is not None
    collection_link = (link("/learning/current#learning-debrief",
                            text(locale, "debrief.open_overview"))
                       if has_collection else "")
    handler._content_page("/learning", return_to=return_to, title=text(locale, "debrief.heading"),
        content='<div role="alert">' + paragraph(locale, "debrief." + reason) + '</div>'
            + collection_link
            + link("/review/recorded", text(locale, "debrief.choose")),
        status=409, untranslated_workflow_body=False)


def handle_debrief_post(handler, path, values):
    try:
        operation = incorporate_report if path.endswith("/include") else remove_source
        result = operation(handler.server.app_context, values)
    except DebriefUnavailable as error:
        _error(handler, error.reason)
        return
    handler._redirect(f"/learning/debrief/{result.scope.scope_id}/all#learning-debrief"
        if path.endswith("/include") else "/learning/current#learning-debrief")


def handle_debrief_get(handler, path):
    inputs = DEBRIEF_INPUTS_PATTERN.fullmatch(path)
    direct = DEBRIEF_FROM_PATTERN.fullmatch(path)
    page = DEBRIEF_PAGE_PATTERN.fullmatch(path)
    resource = DEBRIEF_RESOURCE_PATTERN.fullmatch(path)
    if direct is None and page is None and resource is None and inputs is None:
        return False
    app = handler.server.app_context
    locale = handler._frontend_state().locale
    try:
        if inputs:
            scope = resolve_scope(app, inputs[1])
            scope.player(inputs[2])
            if scope.owner is None:
                raise DebriefUnavailable()
            handler._learning_page(initialize_discovery=True, expected_active=scope.owner)
            return True
        if direct:
            scope = capture_direct_scope(app, direct[1])
            handler._redirect(f"/learning/debrief/{scope.scope_id}/all")
            return True
        scope_id, selector, report_id = page.groups() if page else resource.groups()[1:4]
        scope = resolve_scope(app, scope_id)
        player = scope.player(selector)
        evidence = None if report_id is None else next((item for item in scope.sources
            if item.report.report_id == report_id and item.snapshot in scope.snapshots
            and (player is None or item.reference.acting_player_id == player)), None)
        if report_id is not None and evidence is None:
            raise DebriefUnavailable()
        if resource:
            if resource[5] == "recording":
                handler._match_page(recording_return(app, evidence,
                    dict(scope.source_handles).get(evidence.binding_id)),
                    position=evidence.report.match_position, review=True, debrief_evidence=evidence)
            else:
                artifact = (build_match_rollout_request_export_v1(evidence.report)
                    if resource[5] == "request.json"
                    else build_match_report_result_export_v1(evidence.report))
                resolve_scope(app, scope_id)
                handler._send_artifact(artifact.filename, artifact.to_bytes())
            return True
        with app.lock:
            profile = app.frontend_profile.document
        handler._rendered_language_source = capture_language_source_v1(app, path)
        content = (render_debrief(scope, locale, selector=selector, profile=profile, heading=False)
            if evidence is None else render_comparison(scope, evidence, selector, locale, profile))
        if scope.owner is not None:
            handler._debrief_overview_route = f"/learning/debrief/{scope.scope_id}/{selector}"
            with scope.owner.corpus.lock:
                handler._operation_feedback_delivery = (
                    scope.owner, "learning", feedback_source(scope.owner), False)
            content = '<!-- operation-feedback -->' + content
        content += link(f"/learning/debrief/{scope.scope_id}/{selector}/inputs"
                        if scope.owner else "/review/recorded",
                        text(locale, "debrief.collection" if scope.owner else "debrief.choose"))
        resolve_scope(app, scope_id)  # Recheck the captured lineage before publication.
        handler._content_page("/learning", return_to=path,
            title=(text(locale, "debrief.comparison_title", collection=collection_name(
                scope.owner, locale, profile)) if evidence is not None and scope.owner
                else overview_title(scope, locale, profile)),
            content=content, feedback_identity=scope, untranslated_workflow_body=False)
    except DebriefUnavailable as error:
        _error(handler, error.reason, return_to="/learning")
    return True
