# ruff: noqa: E501 - Keep complete server-rendered elements legible.
"""Pure bilingual automatic review projection from captured admitted inputs."""

from collections import Counter
from dataclasses import dataclass
from html import escape

from skatmind.corpus_web.state import prepared_state_values

from .automatic_learning_controller import source_keys
from .automatic_learning_routes import AUTOMATIC_PAGE
from .learning_result_projection import _players, project_learning_result
from .learning_result_rendering import render_learning_result
from .operation_feedback import FEEDBACK_MARKER
from .saved_match_analyses import _caption, render_saved_analysis
from .stateful_localization import card_name, text, translated
from .task_first_rendering import disclosure, form, hidden, paragraph


@dataclass(frozen=True, slots=True)
class AutomaticDisplay:
    body: str
    title: str


def link(route, label):
    return '<a class="button-link secondary" href="' + escape(route, quote=True) + '">' + escape(
        label) + '</a>'


def update_form(view, locale):
    exists = view.binding.result.generation is not None
    return form(locale, AUTOMATIC_PAGE + "/update", hidden("view", view.token),
                "automatic.update" if exists else "automatic.create", primary=True)


def source_labels(bundle, locale):
    # An ordinal is retained source order, not a name/identity join.
    return {snapshot.match_snapshot_id: text(locale, "automatic.source_caption",
        name=snapshot.workspace.match_definition.title or snapshot.match_id, number=index + 1,
        revision=snapshot.workspace_revision,
        version=record.source_version.content_fingerprint[:12])
        for index, (record, snapshot) in enumerate(bundle.sources)}


def situations(bundle):
    return tuple((source_index, snapshot, ref)
        for source_index, (_record, snapshot) in enumerate(bundle.sources)
        for ref in snapshot.decision_references)


def situation_caption(bundle, row, locale):
    _index, snapshot, ref = row
    players = _players(tuple(s for _r, s in bundle.sources), locale)
    game = snapshot.workspace.slots[ref.match_position - 1].observed_game
    play = game.plays[ref.decision_index - 1]
    return text(locale, "automatic.situation_caption",
        source=source_labels(bundle, locale)[snapshot.match_snapshot_id],
        player=players[ref.acting_player_id], game=ref.match_position,
        trick=(ref.decision_index - 1) // 3 + 1, position=(ref.decision_index - 1) % 3 + 1,
        card=card_name(locale, play.card))


def maintenance(view, locale):
    if view.binding.resumed is None:
        return ""
    body = paragraph(locale, "automatic.maintenance_scope")
    body += form(locale, AUTOMATIC_PAGE + "/cleanup-preview",
        hidden("view", view.token) + hidden("mode", "orphans"), "automatic.cleanup")
    body += form(locale, AUTOMATIC_PAGE + "/cleanup-preview",
        hidden("view", view.token) + hidden("mode", "old_evidence"), "automatic.old_evidence")
    body += form(locale, AUTOMATIC_PAGE + "/cleanup-preview",
        hidden("view", view.token) + hidden("mode", "obsolete_sources"), "automatic.obsolete_sources")
    return disclosure(locale, "automatic.maintenance", body)


def source_exceptions(view, locale):
    body = ""
    manifest = None if view.binding.resumed is None else view.binding.resumed.manifest
    exclusions = ({} if view.binding.result.generation is None else {
        row.source: row.reason for row in view.binding.result.generation.recipe.exclusions})
    for index, source in enumerate(source_keys(view)):
        rows = tuple(row for row in view.binding.inventory.rows if row.source == source)
        explicit = manifest is not None and any(row.source == source and row.reason == "explicit"
                                                for row in manifest.exclusions)
        status = ("explicit" if explicit else exclusions.get(source,
                  rows[0].status if rows else "missing"))
        body += '<li><p>' + escape(source.product_id) + ': ' + translated(
            locale, "automatic.input." + status) + '</p>'
        if manifest is not None:
            body += form(locale, AUTOMATIC_PAGE + "/exclude-preview",
                hidden("view", view.token) + hidden("source", index),
                "automatic.include_preview" if explicit else "automatic.exclude_preview")
        body += '</li>'
    for row in view.binding.inventory.rows:
        if row.source is None:
            body += '<li>' + translated(locale, "automatic.input." + row.status) + '</li>'
    if view.binding.result.generation is not None:
        for outcome in view.binding.result.generation.evidence_outcomes:
            if outcome.status != "selected":
                body += '<li>' + translated(locale, "automatic.evidence_exclusion",
                    report=outcome.evidence_id[:12], reason=text(
                        locale, "automatic.evidence." + outcome.status)) + '</li>'
    return '<ul class="workflow-list">' + body + '</ul>'


def render_entry(view, locale, *, landing=False):
    status = view.binding.result.status
    body = '<section class="panel automatic-learning"><h2>' + translated(
        locale, "automatic.title") + '</h2>'
    body += FEEDBACK_MARKER + paragraph(locale, "automatic.scope")
    body += paragraph(locale, "automatic.state." + status) + update_form(view, locale)
    if view.binding.installed is not None and status in ("current", "outdated"):
        body += link(view.base + "/all", text(locale,
            "automatic.view_prior" if status == "outdated" else "automatic.view"))
    if not landing:
        included = disclosure(locale, "learning.result.included_data", source_exceptions(view, locale))
        if status in ("excluded", "deleted"):
            included = included.replace('<details ', '<details open ', 1)
        body += included
        body += maintenance(view, locale)
    body += '</section>'
    if landing:
        body += '<h2 id="independent-collections">' + translated(
            locale, "automatic.independent") + '</h2>'
        body += link("/learning/collections", text(locale, "automatic.independent"))
    else:
        body += link("/learning/collections", text(locale, "automatic.independent"))
    return body


def render_review(view, selector, locale):
    bundle = view.binding.installed.bundle
    snapshots = tuple(snapshot for _record, snapshot in bundle.sources)
    players = _players(snapshots, locale)
    player_ids = tuple(players)
    player = None if selector == "all" else player_ids[int(selector)]
    labels = source_labels(bundle, locale)
    refs = situations(bundle)
    urls = {ref.decision_reference_id: view.base + "/situation/" + str(index)
            for index, (_s, _snapshot, ref) in enumerate(refs)}
    display = project_learning_result((bundle.prepared, bundle.tactical, bundle.coaching),
        snapshots, None, locale, labels=labels, player_id=player, reference_urls=urls)
    body = ('<section class="panel automatic-learning"><h2 id="learning-result" '
            'tabindex="-1" data-learning-result-focus')
    body += ' autofocus>' + translated(locale, "task.learning.results") + '</h2>' + FEEDBACK_MARKER
    body += paragraph(locale, "automatic.scope")
    if view.binding.result.status == "outdated":
        body += paragraph(locale, "automatic.state.outdated")
    body += '<nav class="debrief-actions" aria-label="' + translated(locale, "debrief.player") + '">'
    body += link(view.base + "/all", text(locale, "debrief.all_players"))
    body += ''.join(link(view.base + "/" + str(i), name) for i, name in enumerate(players.values()))
    body += '</nav>'
    if player is not None:
        body += paragraph(locale, "automatic.player_scope", player=players[player])
    inputs = paragraph(locale, "automatic.identities")
    inputs += '<ul>' + ''.join('<li>' + link(view.base + "/source/" + str(i),
        labels[snapshot.match_snapshot_id]) + '</li>' for i, (_record, snapshot)
        in enumerate(bundle.sources) if player is None or player in {
            p.player_id for p in snapshot.workspace.match_definition.participants}) + '</ul>'
    if player is not None:
        inputs += '<ul>' + ''.join('<li>' + link(urls[ref.decision_reference_id],
            situation_caption(bundle, row, locale)) + '</li>' for row in refs
            for ref in (row[2],) if ref.acting_player_id == player) + '</ul>'
    inputs += '<dl>' + ''.join('<dt>' + translated(locale, "automatic.count." + row.name)
        + '</dt><dd>' + escape(row.value) + '</dd>' for row in bundle.coverage) + '</dl>'
    inputs += paragraph(locale, "automatic.rollout_separate")
    inputs += source_exceptions(view, locale)
    state = prepared_state_values(bundle.prepared, bundle.tactical, bundle.coaching)
    body += render_learning_result(state, locale, display=display, included_links=inputs,
                                    download_base=view.base + "/downloads")
    body += update_form(view, locale) + maintenance(view, locale)
    body += link(AUTOMATIC_PAGE, text(locale, "automatic.back")) + '</section>'
    return AutomaticDisplay(body, text(locale, "automatic.title"))


def render_source(view, index, locale):
    bundle = view.binding.installed.bundle
    _record, snapshot = bundle.sources[index]
    body = '<h2>' + escape(source_labels(bundle, locale)[snapshot.match_snapshot_id]) + '</h2>'
    body += '<ul>' + ''.join('<li>' + link(view.base + "/situation/" + str(i),
        situation_caption(bundle, row, locale)) + '</li>' for i, row in enumerate(situations(bundle))
        if row[0] == index) + '</ul>'
    return body + link(view.base + "/all", text(locale, "automatic.view"))


def render_situation(view, index, locale):
    bundle = view.binding.installed.bundle
    row = situations(bundle)[index]
    source_index, snapshot, ref = row
    record = bundle.sources[source_index][0]
    body = '<h2>' + escape(situation_caption(bundle, row, locale)) + '</h2>'
    body += paragraph(locale, "automatic.knowledge")
    matching = tuple((i, value) for i, value in enumerate(bundle.evidence)
        if value.entry.source_version_id == record.source_version.identity
        and value.report.match_position == ref.match_position
        and value.report.decision_index == ref.decision_index)
    if not matching:
        body += paragraph(locale, "automatic.no_comparison")
    for i, value in matching:
        body += '<p>' + link(view.base + "/evidence/" + str(i), _caption(value, locale)) + '</p>'
    # Match exact identity/content, never a same-named or corrected recording.
    fresh = [r for r in view.binding.inventory.rows if r.status == "selected"
             and r.source_version_id == record.source_version.identity]
    if len(fresh) == 1 and view.binding.result.status == "current":
        body += form(locale, AUTOMATIC_PAGE + "/recording", hidden("view", view.token)
            + hidden("situation", index), "automatic.recording")
    else:
        body += paragraph(locale, "automatic.recording_changed")
    body += disclosure(locale, "automatic.retrospective", paragraph(locale, "automatic.retrospective_note"))
    return body + link(view.base + "/source/" + str(source_index), text(locale, "automatic.source"))


def render_evidence(view, index, locale):
    return render_saved_analysis(view.binding.installed.bundle.evidence[index],
        view.base + "/evidence/" + str(index), locale) + link(
            view.base + "/all", text(locale, "automatic.view"))


def render_confirmation(value, locale):
    body = '<section class="panel automatic-learning"><h2 id="automatic-confirmation" tabindex="-1" autofocus>'
    body += translated(locale, "automatic.confirmation") + '</h2>'
    cleanup = value.cleanup
    manifest_changed = (cleanup is not None
                        and cleanup.manifest != value.view.binding.resumed.manifest)
    actionable = cleanup is None or bool(cleanup.files) or manifest_changed
    if value.source_release_blocked:
        body += paragraph(locale, "automatic.source_release_blocked")
        blockers = Counter(row.status for row in value.view.binding.inventory.rows)
        for reason in ("ambiguous", "invalid", "unsupported"):
            if blockers[reason]:
                body += paragraph(locale, "automatic.source_release_blocker." + reason,
                                  count=blockers[reason])
    if not actionable:
        body += paragraph(locale, "automatic.preview.no_changes")
    elif value.source_release_blocked:
        body += paragraph(locale, "automatic.preview.blocked_cleanup")
    else:
        meaning = (value.kind if cleanup is None or value.sources or cleanup.removed_evidence_ids
                   else "cleanup")
        body += paragraph(locale, "automatic.preview." + meaning)
    if value.source is not None:
        body += '<p>' + escape(value.source.product_id) + '</p>'
    if cleanup is not None:
        body += paragraph(locale, "automatic.cleanup_effect", objects=len(cleanup.files),
                          reports=len(cleanup.removed_evidence_ids))
        body += '<ul>' + ''.join('<li>' + (escape(_caption(retained, locale)) if retained else
            translated(locale, "automatic.unavailable_report", report=entry.identity[:12]))
            + '</li>' for entry, retained in value.evidence) + '</ul>'
        if value.kind == "obsolete_sources":
            retained = sum(row.source_version.source.family == "match"
                           for row in cleanup.manifest.sources)
            body += paragraph(locale, "automatic.source_release_count",
                              sources=len(value.sources), retained=retained)
            body += '<ul>' + ''.join('<li>' + translated(locale, "automatic.source_release_name",
                name=snapshot.workspace.match_definition.title or snapshot.match_id,
                revision=snapshot.workspace_revision, number=number) + '</li>'
                for number, (_record, snapshot) in enumerate(value.sources, 1)) + '</ul>'
        if cleanup.manifest.generations != value.view.binding.resumed.manifest.generations:
            body += paragraph(locale, "automatic.retire_generation")
        details = paragraph(locale, "automatic.preview.reference_change") if manifest_changed else ""
        if value.sources:
            details += '<ul>' + ''.join('<li>' + translated(locale, "automatic.source_release_caption",
                name=snapshot.workspace.match_definition.title or snapshot.match_id,
                identity=snapshot.match_id, revision=snapshot.workspace_revision,
                version=record.source_version.content_fingerprint) + '</li>'
                for record, snapshot in value.sources) + '</ul>'
        if details:
            body += disclosure(locale, "task.technical", details, technical=True)
    if actionable:
        fields = hidden("confirmation", value.token)
        fields += '<label><input type="checkbox" name="confirm_apply" required>' + translated(
            locale, "automatic.consent") + '</label>'
        body += form(locale, AUTOMATIC_PAGE + "/confirm", fields, "automatic.confirm", destructive=True)
    body += link(AUTOMATIC_PAGE, text(locale, "automatic.cancel" if actionable else "automatic.recover")) + '</section>'
    return body
