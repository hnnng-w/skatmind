# ruff: noqa: E501 - Keep complete server-rendered elements legible.
"""One bilingual debrief view for captured Match and explicit collection evidence."""

from html import escape

from skatmind.match_debrief import build_debrief_projection

from .render_locale import localized_render
from .result_rendering import _section_body, render_result_presentation_v1
from .rollout_result_presentation import build_rollout_presentation
from .stateful_localization import managed_name, text, translated
from .task_first_rendering import disclosure, form, hidden, paragraph, technical_details


def link(route, label):
    return f'<a class="button-link" href="{escape(route, quote=True)}">{escape(label)}</a>'


def collection_name(target, locale, profile=None):
    return managed_name(locale, profile, "corpora", target.corpus.store.document.catalog.corpus_id)


def overview_title(scope, locale, profile=None):
    return (text(locale, "debrief.overview_title", collection=collection_name(
        scope.owner, locale, profile)) if scope.owner else text(locale, "debrief.direct_title"))


def player_name(snapshots, player_id):
    return next((item.player_label or item.player_id for snapshot in snapshots
                 for item in snapshot.workspace.match_definition.participants
                 if item.player_id == player_id), player_id)


def decision_caption(evidence, locale, profile=None):
    report = evidence.report
    definition = evidence.snapshot.workspace.match_definition
    return text(locale, "debrief.decision", match=managed_name(
        locale, profile, "matches", definition.match_id, definition.title),
        game=report.match_position, trick=(report.decision_index - 1) // 3 + 1,
        position=(report.decision_index - 1) % 3 + 1,
        player=player_name((evidence.snapshot,), report.value.profile_binding.acting_player_id))


def report_presentation(evidence, locale):
    value = evidence.report.value
    return localized_render(build_rollout_presentation)(
        value, value.result.to_dict()["document"], "match_decision", locale=locale)


def render_debrief(scope, locale, *, selector="all", profile=None, heading=True):
    player = scope.player(selector)
    view = build_debrief_projection(scope.snapshots, scope.sources, player_id=player,
                                    tactical=scope.tactical, coaching=scope.coaching)
    base = f"/learning/debrief/{scope.scope_id}"
    body = '<section id="learning-debrief" class="panel analysis-overview" tabindex="-1">'
    if heading:
        body += '<h2>' + escape(overview_title(scope, locale, profile)) + '</h2>'
    body += paragraph(locale, "debrief.collection_scope" if scope.owner else "debrief.direct_scope")
    body += '<p>' + ' · '.join(escape(managed_name(locale, profile, "matches", item.match_id,
        item.workspace.match_definition.title)) + ' — ' + translated(locale,
            "task.learning.saved_revision", revision=item.workspace_revision)
        for item in scope.snapshots) + '</p>'
    body += '<nav class="debrief-actions" aria-label="' + translated(locale, "debrief.player") + '">'
    for value, label in (("all", text(locale, "debrief.all_players")), *(
            (str(index), player_name(scope.snapshots, identity))
            for index, identity in enumerate(scope.players))):
        anchor = link(base + "/" + value, label)
        if value == selector:
            anchor = anchor.replace('<a ', '<a aria-current="true" ', 1)
        body += anchor
    body += '</nav>'
    body += paragraph(locale, "debrief.counts", recorded=view.recorded_decisions,
                      decisions=len(view.decisions), reports=view.report_count)
    if not view.decisions:
        body += paragraph(locale, "debrief.empty")
        body += link("/review/recorded", text(locale, "debrief.choose"))
    else:
        body += paragraph(locale, "debrief.qualification")
    for decision in view.decisions:
        body += '<article class="debrief-decision"><h3>' + escape(
            decision_caption(decision.reports[0], locale, profile)) + '</h3>'
        if decision.mixed:
            body += paragraph(locale, "debrief.mixed")
        if decision.motifs:
            body += '<p>' + translated(locale, "debrief.topics") + ': ' + ', '.join(
                translated(locale, "debrief.motif." + motif) for motif in decision.motifs) + '</p>'
        for number, evidence in enumerate(decision.reports, 1):
            presentation = report_presentation(evidence, locale)
            settings = evidence.report.value.options.rollout_settings
            if len(decision.reports) > 1:
                body += '<h4>' + translated(locale, "debrief.report_number", number=number) + '</h4>'
            summary, recommendation = presentation.sections[:2]
            forced = len(evidence.report.value.result.document["legal_cards"]) == 1
            body += '<div class="debrief-report"><div class="debrief-meaning">'
            # Use the shared authoritative Card labels and actual-card comparison.
            actual = recommendation.details[-1].value
            body += '<p><strong>' + translated(locale, "result.actual_card") + ': </strong>' + escape(actual) + '</p>'
            body += '<p>' + escape(text(locale, "rollout.only_card") if forced else recommendation.items[0]) + '</p>'
            if not forced:
                best = recommendation.details[0]
                body += '<p>' + translated(locale, "debrief.alternatives") + ': ' + escape(best.value) + '</p>'
            body += '<p class="debrief-context">' + translated(locale, "rollout.objective." + settings.objective)
            supplements = evidence.report.value.options.settlement_supplements
            if supplements:
                body += ' · ' + translated(locale, "debrief.supplements", values="; ".join(
                    text(locale, "rollout.analysis_" + key) + ": " + str(value)
                    for key, value in supplements.items()))
            body += '</p></div><div class="debrief-row-actions">'
            route = base + "/" + selector + "/" + evidence.report.report_id
            body += link(route, text(locale, "debrief.comparison")) + '</div></div>'
            details = localized_render(_section_body)(summary, locale=locale)
            details += paragraph(locale, "debrief.variant", number=number,
                seed=settings.random_seed, worlds=settings.requested_worlds)
            bid = evidence.report.value.request.document["whole_game_rollout_derivation"][
                "original_request"]["document"]["game_declaration"]["bid_value"]
            if bid is not None:
                details += paragraph(locale, "debrief.known_bid", bid=bid)
            body += disclosure(locale, "debrief.entry_details", details)
        body += '</article>'
    if view.topics:
        topics = paragraph(locale, "debrief.topic_limit")
        for identity, motif, decisions, games in view.topics:
            topics += paragraph(locale, "debrief.topic_counts", player=player_name(scope.snapshots, identity),
                topic=text(locale, "debrief.motif." + motif), decisions=decisions, games=games)
        body += disclosure(locale, "debrief.topics", topics)
    if view.focuses:
        body += '<h3>' + translated(locale, "debrief.focuses") + '</h3>'
        for focus in view.focuses:
            body += paragraph(locale, "debrief.topic_counts", player=player_name(scope.snapshots, focus.player_id),
                topic=text(locale, "debrief.motif." + focus.motif_type),
                decisions=focus.qualifying_decision_count, games=focus.distinct_game_count)
            body += paragraph(locale, "debrief.guidance." + focus.guidance_code)
    current = {item.match_snapshot_id for item in scope.snapshots}
    stale = [item for item in scope.sources if item.snapshot.match_snapshot_id not in current]
    for evidence in stale:
        body += '<p role="status">' + escape(decision_caption(evidence, locale, profile)) + '</p>'
        body += paragraph(locale, "debrief.snapshot_mismatch")
        body += link("/learning/current#insight-versions", text(locale, "task.learning.choose_version"))
        body += _remove_form(scope, evidence, locale)
    details = paragraph(locale, "debrief.lifetime")
    details += technical_details(locale, {"scope_id": scope.scope_id,
        "snapshot_ids": [item.match_snapshot_id for item in scope.snapshots],
        "report_count": view.report_count, "semantic_report_count": view.semantic_report_count,
        "sources": [{"binding_id": item.binding_id, "report_id": item.report.report_id,
                     "snapshot_id": item.snapshot.match_snapshot_id,
                     "source_content_fingerprint": item.source_snapshot.source_content_fingerprint}
                    for item in scope.sources]})
    if scope.owner:
        for evidence in scope.sources:
            if evidence not in stale:
                details += '<p>' + escape(decision_caption(evidence, locale, profile)) + '</p>'
                details += _remove_form(scope, evidence, locale)
    body += disclosure(locale, "debrief.technical", details)
    return body + '</section>'


def _remove_form(scope, evidence, locale):
    return form(locale, "/learning/debrief/remove", hidden("managed_handle", scope.owner.handle)
        + hidden("scope_id", scope.scope_id) + hidden("binding_id", evidence.binding_id),
        "task.learning.remove_source")


def render_available_reports(offers, target, locale, profile=None):
    if not offers:
        return ""
    body = '<section class="panel"><h2>' + translated(locale, "debrief.available") + '</h2>'
    for number, (evidence, report, reason, handle, proof) in enumerate(offers, 1):
        if evidence is not None:
            body += '<h3>' + escape(decision_caption(evidence, locale, profile)) + '</h3>'
            settings = report.value.options.rollout_settings
            body += paragraph(locale, "debrief.variant", number=number,
                               seed=settings.random_seed, worlds=settings.requested_worlds)
            body += paragraph(locale, "task.learning.saved_revision",
                               revision=evidence.snapshot.workspace_revision)
            body += paragraph(locale, "rollout.objective." + settings.objective)
            if evidence.report.value.options.settlement_supplements:
                summary = report_presentation(evidence, locale).sections[0]
                body += '<p>' + escape(summary.paragraphs[1]) + '</p>'
        else:
            body += paragraph(locale, "recordings.match.report_decision", number=report.match_position,
                trick=(report.decision_index - 1) // 3 + 1, position=(report.decision_index - 1) % 3 + 1)
        if reason:
            body += paragraph(locale, "debrief." + reason)
            destination = ("/learning/current#learning-recorded-matches" if reason == "missing_snapshot"
                else "/learning/current#insight-versions" if reason == "snapshot_mismatch"
                else "/review/recorded")
            body += link(destination, text(locale, "debrief.remedy"))
        else:
            body += incorporation_form(target, handle, report.report_id, proof, locale, profile)
    return body + '</section>'


def incorporation_form(target, source_handle, report_id, proof, locale, profile=None):
    name = collection_name(target, locale, profile)
    fields = (hidden("managed_handle", target.handle) + hidden("source_handle", source_handle)
        + hidden("report_id", report_id) + hidden("selection", proof))
    return ('<form method="post" action="/learning/debrief/include" class="form-grid">'
        + fields + '<button type="submit" class="primary">'
        + translated(locale, "debrief.add_to", collection=name) + '</button></form>')


def render_report_collection_actions(scope, offers, report_id, locale, profile=None):
    body = '<div class="report-collection-actions">'
    if scope is None:
        return body + link("/learning", text(locale, "debrief.choose_collection")) + '</div>'
    name = collection_name(scope.owner, locale, profile)
    current = {item.match_snapshot_id for item in scope.snapshots}
    included = next((item for item in scope.sources if item.report.report_id == report_id
                     and item.snapshot.match_snapshot_id in current), None)
    if included is not None:
        body += paragraph(locale, "debrief.included", collection=name)
    else:
        for _evidence, report, reason, handle, proof in offers:
            if report.report_id != report_id:
                continue
            if reason is None:
                body += incorporation_form(scope.owner, handle, report_id, proof, locale, profile)
            else:
                body += paragraph(locale, "debrief." + reason)
                body += link("/learning/current#learning-recorded-matches" if reason == "missing_snapshot"
                    else "/learning/current#insight-versions", text(locale, "debrief.remedy"))
    body += link(f"/learning/debrief/{scope.scope_id}/all", text(locale, "debrief.open_overview"))
    return body + '</div>'


def render_comparison(scope, evidence, selector, locale, profile=None):
    base = f"/learning/debrief/{scope.scope_id}/{selector}"
    route = base + "/" + evidence.report.report_id
    body = '<h2>' + escape(decision_caption(evidence, locale, profile)) + '</h2>'
    body += '<nav class="debrief-actions">' + link(base, text(locale,
        "debrief.open_overview" if scope.owner else "debrief.back"))
    body += link(route + "/recording", text(locale, "debrief.recording")) + '</nav>'
    body += render_result_presentation_v1(report_presentation(evidence, locale), locale=locale,
        identity_prefix="debrief-comparison")
    exports = link(route + "/request.json", text(locale, "result.download_request"))
    exports += link(route + "/result.json", text(locale, "result.download_result"))
    return body + disclosure(locale, "debrief.technical", exports)
