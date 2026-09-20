# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from html import escape

from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS

from .stateful_localization import managed_name, text, translated
from .task_first_projections import project_task_first_learning_v1
from .task_first_rendering import (
    disclosure,
    form,
    hidden,
    input_field,
    paragraph,
    section,
    select_field,
    technical_details,
)


def transfer_choices(locale):
    return (paragraph(locale, "task.transfer.choices_help")
        + select_field(locale, "selection_mode", "task.transfer.selection", (
            ("select_imported", text(locale, "task.transfer.select_imported")),
            ("keep_current", text(locale, "task.transfer.keep_current"))))
        + select_field(locale, "same_revision_resolution", "task.transfer.conflict", (
            ("reject", text(locale, "task.transfer.reject")),
            ("retain", text(locale, "task.transfer.retain")))))


def render_task_first_transfer_v1(
    state, *, source_handle, source_id, source_label, target_handle=None,
    target_label=None, report_id=None, locale="en", show_feedback=False,
):
    content = paragraph(locale, "task.transfer.help")
    if state is None:
        content += paragraph(locale, "task.transfer.open_collection")
        content += '<p><a href="/learning">' + translated(locale, "navigation.learning") + '</a></p>'
    else:
        content += paragraph(locale, "task.transfer.source_target", source=source_label, target=target_label)
        exists = any(match["match_id"] == source_id for match in state["matches"])
        content += paragraph(locale, "task.transfer.exists" if exists else "task.transfer.new")
        content += paragraph(locale, "task.transfer.default_selection")
        common = hidden("managed_handle", source_handle) + hidden("target_managed_handle", target_handle)
        content += form(locale, "/matches/transfer-workspace", common
            + hidden("expected_catalog_revision", state["corpus"]["catalog_revision"])
            + disclosure(locale, "task.advanced", transfer_choices(locale)), "task.transfer.add")
        if report_id is not None:
            options = tuple((item["match_snapshot_id"], text(locale, "task.learning.version_number", number=index))
                            for index, item in enumerate(state["current_match_snapshots"], 1))
            content += disclosure(locale, "task.transfer.report", paragraph(locale, "task.transfer.report_help")
                + form(locale, "/matches/transfer-report", common + hidden("report_id", report_id)
                    + select_field(locale, "match_snapshot_id", "task.learning.used_version", options),
                    "task.transfer.report", disabled=not options))
    rendered = disclosure(locale, "task.transfer.heading", content)
    return rendered.replace('<details ', '<details open ', 1) if show_feedback else rendered


def _hidden(handle, operation):
    return hidden("managed_handle", handle) + hidden("operation", operation)


def _match_label(locale, profile, match_id, recorded):
    fallback = next((item.display_label for item in recorded if item.semantic_product_id == match_id), None)
    return managed_name(locale, profile, "matches", match_id, fallback)


def _version(locale, snapshot, number):
    return (paragraph(locale, "task.learning.version_number", number=number)
        + paragraph(locale, "task.learning.saved_revision", revision=snapshot["workspace_revision"])
        + paragraph(locale, "task.learning.version_progress", games=snapshot["observed_game_count"],
                    decisions=snapshot["decision_count"]))


def render_task_first_learning_v1(state, *, managed_handle, locale="en", profile=None, recorded=(), rejected_build=False, active_recorded=None, learning_selection=None, source_generation=0, candidate_limit_reached=False, entry_outcome=None):
    view = project_task_first_learning_v1(state)
    handle = managed_handle
    revision = state["corpus"]["catalog_revision"]
    guidance = paragraph(locale, view.next_task_key)
    if not state["matches"]:
        guidance += '<p><a class="button-link" href="#learning-recorded-matches">' + translated(locale, "task.learning.choose_recorded") + '</a></p>'
    elif view.status == "select":
        guidance += '<p><a href="#insight-versions">' + translated(locale, "task.learning.choose_version") + '</a></p>'
    elif view.status == "sources":
        guidance += paragraph(locale, "task.learning.sources_help")
        guidance += '<p><a href="#learning-sources">' + translated(locale, "task.learning.sources") + '</a></p>'
    elif view.status == "results":
        guidance += '<p><a class="button-link" href="#learning-results">' + translated(locale, "task.learning.view_results") + '</a></p>'
    else:
        guidance += '<p><a href="#learning-build">' + translated(locale, "task.learning.build") + '</a></p>'
    body = section(locale, "task.learning.next", guidance)
    available = paragraph(locale, "task.learning.recorded_help")
    options = [("", text(locale, "task.learning.choose_recorded"))]
    for number, item in enumerate(recorded, 1):
        if item.status == "available":
            label = _match_label(locale, profile, item.semantic_product_id, recorded)
            options.append((item.handle, text(locale, "task.learning.recorded_choice",
                number=number, name=label, revision=item.revision)))
        else:
            available += paragraph(locale, "task.learning.recorded_unavailable", number=number,
                reason=text(locale, "creation.managed.status." + item.status))
    if len(options) == 1:
        available += paragraph(locale, "task.learning.no_recorded")
    if candidate_limit_reached:
        available += paragraph(locale, "task.learning.discovery_limit")
    if learning_selection is not None:
        resolution = disclosure(locale, "task.advanced", select_field(locale, "same_revision_resolution",
            "task.transfer.conflict", (("reject", text(locale, "task.transfer.reject")),
                                      ("retain", text(locale, "task.transfer.retain")))))
        if entry_outcome is not None and entry_outcome[0].status == "resolution_required":
            resolution = resolution.replace('<details', '<details open', 1)
        available += form(locale, "/learning/add-recorded-match",
            hidden("managed_handle", handle) + hidden("learning_selection", learning_selection)
            + hidden("source_generation", source_generation)
            + hidden("expected_catalog_revision", revision)
            + select_field(locale, "source_handle", "task.learning.choose_recorded", tuple(options), required=True)
            + resolution,
            "task.learning.add_recorded", primary=not state["matches"], disabled=len(options) == 1)
    if entry_outcome is not None:
        result, match_id, copied_revision, selected = entry_outcome
        outcome = {"unchanged": "unchanged", "resolution_required": "resolution",
                   "revision_conflict": "conflict", "persistence_conflict": "conflict"}.get(result.status)
        if result.status == "applied":
            outcome = "selected" if result.state["relation"] == "new_match" and selected else "retained"
        if outcome is not None:
            available += '<div role="status">' + paragraph(locale, "task.learning.import." + outcome,
                name=_match_label(locale, profile, match_id, recorded), revision=copied_revision) + '</div>'
    available += '<p><a href="/learning/recorded-matches/refresh">' + translated(locale, "task.learning.refresh_recorded") + '</a></p>'
    available += '<p><a href="/matches">' + translated(locale, "task.learning.open_matches") + '</a></p>'
    body += '<div id="learning-recorded-matches" tabindex="-1">' + section(locale, "task.learning.recorded", available) + '</div>'
    selections = paragraph(locale, "task.learning.versions_help")
    alternatives = ''
    for match in state["matches"]:
        label = '<h3>' + escape(_match_label(locale, profile, match["match_id"], recorded)) + '</h3>'
        selections += label
        selected = next((snapshot for snapshot in match["snapshots"] if snapshot["current"]), None)
        if selected is None:
            selections += paragraph(locale, "task.learning.missing_selection")
        else:
            selections += paragraph(locale, "task.learning.used_version")
        choices = ''
        for number, snapshot in enumerate(match["snapshots"], 1):
            summary = _version(locale, snapshot, number)
            if snapshot["current"]:
                selections += summary
            else:
                choices += summary + form(locale, "/learning/api/v1/operations",
                    _hidden(handle, "select_current_snapshot")
                    + hidden("expected_catalog_revision", revision)
                    + hidden("match_id", match["match_id"])
                    + hidden("match_snapshot_id", snapshot["match_snapshot_id"]), "task.learning.use_version")
        if selected is None:
            selections += choices
        else:
            alternatives += label + choices
    if alternatives:
        selections += disclosure(locale, "task.learning.alternatives", alternatives)
    if state["matches"]:
        body += '<div id="insight-versions">' + section(locale, "task.learning.selected", selections) + '</div>'
    fields = ''.join(input_field(locale, name, f"task.field.{name}", default, kind=kind, required=True)
        for name, default, kind in (
            ("dataset_id", state["corpus"]["corpus_id"] + "-learning-dataset-v2", "text"),
            ("known_player_seed", 0, "number"), ("unseen_player_seed", 0, "number"),
            ("train_weight", 70, "number"), ("validation_weight", 15, "number"), ("test_weight", 15, "number")))
    build = paragraph(locale, "task.learning.build_help")
    build += paragraph(locale, "concept.learning.automatic")
    if view.primary_action:
        build += form(locale, "/learning/api/v1/operations", _hidden(handle, "prepare_learning_artifacts")
            + disclosure(locale, "task.learning.settings", paragraph(locale, "task.learning.settings_help")
                          + fields), "task.learning.build", primary=view.status == "build")
    else:
        build += paragraph(locale, view.next_task_key)
        if rejected_build:
            build += form(locale, "/learning/api/v1/operations",
                _hidden(handle, "prepare_learning_artifacts")
                + disclosure(locale, "task.learning.settings", fields),
                "task.learning.build", disabled=True)
    body += '<div id="learning-build" tabindex="-1">' + section(locale, "task.learning.build", build) + '</div>'
    prepared = state["prepared"]
    results = paragraph(locale, "task.learning.no_results")
    if prepared is not None:
        results = paragraph(locale, "task.learning.current_results")
        results += paragraph(locale, "task.learning.coverage_help")
        results += paragraph(locale, "task.learning.dataset_status",
                             status=text(locale, "task.learning.dataset." + prepared["dataset_status"]))
        results += '<dl>' + ''.join('<dt>' + translated(locale, f"task.learning.count.{name}") + '</dt><dd>'
            + escape(str(prepared[name])) + '</dd>' for name in (
                "cross_game_match_count", "cross_game_player_count", "observed_decision_count",
                "record_count", "skipped_decision_count", "commentary_evidence_count",
                "response_evidence_count", "strategy_teacher_evidence_count",
                "tactical_motif_occurrence_count", "tactical_coaching_focus_area_count")) + '</dl>'
        results += '<ul>' + ''.join(f'<li><a href="/learning/downloads/{kind.replace("_", "-")}.json" download>'
            + translated(locale, f"task.download.{kind}") + '</a></li>'
            for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS) + '</ul>'
    body += '<div id="learning-results" tabindex="-1">' + section(locale, "task.learning.results", results) + '</div>'
    advanced = ''
    upload = ('<label>' + translated(locale, "creation.import.file")
              + '<input type="file" name="workspace_file" accept="application/json,.json" required></label>')
    advanced += section(locale, "creation.import.heading", paragraph(locale, "task.transfer.help")
        + form(locale, "/learning/api/v1/operations", _hidden(handle, "import_match_workspace")
            + hidden("expected_catalog_revision", revision) + upload + transfer_choices(locale),
            "creation.import.action", multipart=True), level=3)
    source_options = tuple((item["match_snapshot_id"], _match_label(locale, profile, item["match_id"], recorded))
                           for item in state["current_match_snapshots"])
    sources = paragraph(locale, "task.learning.sources_help")
    sources += form(locale, "/learning/api/v1/operations", _hidden(handle, "import_strategy_teacher_report")
        + '<label>' + translated(locale, "task.learning.report_file")
        + '<input type="file" name="report_source_file" accept="application/json,.json" required></label>'
        + select_field(locale, "match_snapshot_id", "task.learning.used_version", source_options),
        "task.learning.add_source", multipart=True, disabled=not source_options)
    for source in state["strategy_sources"]:
        sources += '<h4>' + escape(_match_label(locale, profile, source["match_id"], recorded)) + '</h4>'
        sources += paragraph(locale, "task.match.position", number=source["match_position"])
        sources += '<p>' + translated(locale, "task.field.decision_index") + ': ' + str(source["decision_index"]) + '</p>'
        sources += paragraph(locale, "task.value." + source["recommendation_method"])
        sources += paragraph(locale, "task.learning.binding." + source["binding_status"])
        sources += form(locale, "/learning/api/v1/operations", _hidden(handle, "remove_strategy_teacher_report")
            + hidden("source_binding_id", source["source_binding_id"]), "task.learning.remove_source")
    sources += form(locale, "/learning/api/v1/operations", _hidden(handle, "clear_strategy_teacher_reports"),
                    "task.learning.clear_sources", disabled=not state["strategy_sources"])
    source_section = '<div id="learning-sources">' + section(locale, "task.learning.sources", sources, level=3) + '</div>'
    if view.status == "sources":
        body += source_section
    else:
        advanced += source_section
    advanced += form(locale, "/learning/api/v1/operations", _hidden(handle, "reload_corpus"), "common.action.reload")
    body += disclosure(locale, "task.advanced", advanced)
    body += technical_details(locale, {"corpus": state["corpus"], "matches": state["matches"],
                                        "strategy_sources": state["strategy_sources"], "prepared": prepared})
    return '<div id="task-first-learning">' + body + '</div>'
