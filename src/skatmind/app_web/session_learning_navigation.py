"""Family-local Session navigation over one original mixed delivery binding."""

from html import escape

from skatmind.automatic_learning_store import StoreConflictError
from skatmind.session_transitions import replay_session_state_v1

from .session_learning_rendering import (
    evidence_caption,
    render_session_coverage,
    render_session_evidence,
    session_links,
    source_caption,
)
from .stateful_localization import card_name, text, translated
from .task_first_rendering import disclosure, form, hidden, paragraph


def decisions(bundle):
    rows = []
    for source_index, source in enumerate(getattr(bundle, "session_sources", ())):
        facts = replay_session_state_v1(source.document.state)
        selected = {cp.decision_index: (cp, observation)
                    for _index, cp, observation in source.coverage.decisions}
        for index, (player, card) in enumerate(facts.plays[:source.coverage.recorded_plays], 1):
            if player == source.document.state.local_player_id:
                rows.append((source_index, source, index, player, card, selected.get(index)))
    return tuple(rows)


def decision_caption(row, locale):
    _index, source, decision, player, card, _checkpoint = row
    label = next(p.player_label or p.player_id for p in source.document.state.players
                 if p.player_id == player)
    return text(locale, "session_learning.decision", player=label, decision=decision,
                card=card_name(locale, card))


def render_session_review(view, locale):
    from .automatic_learning_rendering import link
    bundle = view.binding.installed.bundle
    if not hasattr(bundle, "session_sources"):
        return session_links(locale)
    body = '<h3>' + translated(locale, "session_learning.title") + '</h3>'
    body += paragraph(locale, "session_learning.scope")
    body += '<dl>' + ''.join('<dt>' + translated(locale, "session_learning.count." + row.name)
        + '</dt><dd>' + escape(row.value) + '</dd>' for row in bundle.session_coverage) + '</dl>'
    body += '<ul>' + ''.join('<li>' + link(view.base + "/session/source/" + str(i),
        source_caption(source, locale)) + '</li>'
        for i, source in enumerate(bundle.session_sources)) + '</ul>'
    return body + session_links(locale)


def render_session_page(view, kind, index, locale):
    from .automatic_learning_rendering import link
    bundle = view.binding.installed.bundle
    if kind == "evidence":
        value = bundle.session_evidence[index]
        route = view.base + "/session/evidence/" + str(index)
        return (render_session_evidence(value, route, locale)
                + link(view.base + "/all", text(locale, "automatic.view")))
    if kind == "source":
        source = bundle.session_sources[index]
        body = '<h2>' + escape(source_caption(source, locale)) + '</h2>'
        body += render_session_coverage(source, locale)
        body += '<ul>' + ''.join('<li>' + link(view.base + "/session/decision/" + str(i),
            decision_caption(row, locale)) + '</li>' for i, row in enumerate(decisions(bundle))
            if row[0] == index) + '</ul>'
        return body + link(view.base + "/all", text(locale, "automatic.view"))
    row = decisions(bundle)[index]
    source_index, source, decision, _player, _card, checkpoint = row
    body = '<h2>' + escape(decision_caption(row, locale)) + '</h2>'
    body += paragraph(locale, "automatic.knowledge")
    matching = tuple((i, value) for i, value in enumerate(bundle.session_evidence)
        if value.entry.source_version_id == source.record.source_version.identity
        and value.checkpoint.decision_index == decision)
    if checkpoint is None:
        body += paragraph(locale, "session_learning.missing", count=1)
    elif not matching:
        body += paragraph(locale, "automatic.no_comparison")
    body += ''.join('<p>' + link(view.base + "/session/evidence/" + str(i),
        evidence_caption(value, locale)) + '</p>' for i, value in matching)
    if view.binding.result.status == "current":
        body += form(locale, "/learning/automatic/recording", hidden("view", view.token)
            + hidden("situation", "session-" + str(index)),
            "automatic.recording" if checkpoint is not None else "recorded_review.history")
    else:
        body += paragraph(locale, "automatic.recording_changed")
    body += disclosure(locale, "task.technical", '<p>' + escape(
        source.record.source_version.content_fingerprint) + '</p>', technical=True)
    return body + link(view.base + "/session/source/" + str(source_index),
                       text(locale, "automatic.source"))


def open_session_recording(handler, controller, view, index):
    from .managed_item_discovery import discover_managed_items_v1
    from .session_frontend import open_guided_session_v1

    if view.binding.result.status != "current":
        raise StoreConflictError("Prior Session review cannot open a current recording.")
    _source_index, source, decision, _player, _card, checkpoint = decisions(
        view.binding.installed.bundle)[index]
    app = handler.server.app_context
    root = app.managed_home.category("sessions").path
    discovery = discover_managed_items_v1(root, family="sessions", generation=1)
    entries = [entry for entry in discovery.entries if entry.summary.status == "available"
               and entry.summary.semantic_product_id == source.document.state.session_id]
    if len(entries) != 1:
        raise StoreConflictError("Session recording ownership changed.")
    active = open_guided_session_v1(root, entries[0])
    if active.document.content_fingerprint != source.record.source_version.content_fingerprint:
        raise StoreConflictError("Session recording version changed.")
    controller.service.validate_delivery(view.binding)
    handler._activate_session(active)
    anchor = "recorded-decision" if checkpoint is not None else "session-play"
    return f"/sessions/current#{anchor}-{decision}"
