"""Native Cent entry independent of the currently active individual game."""

import hashlib
import hmac
import secrets
from contextlib import nullcontext
from html import escape

from skatmind.accounting_store import AccountingConflict, load_accounting
from skatmind.errors import SkatMindError
from skatmind.event_context_contracts import CENT_TARIFFS

from .accounting_forms import CENT_SETUP_FIELDS, AccountingFormError
from .accounting_frontend import new_round
from .accounting_rendering import _tariff
from .cent_publication import complete_game, pending, publish_game, release_attempt
from .cent_round_context import round_labels
from .cent_sources import bound_selection, open_bound, selection, session_entries
from .event_context_forms import resolve_platform, supported_terms
from .event_context_frontend import EventFormConflict
from .event_context_rendering import platform_field
from .friendly_creation_rendering import render_card_knowledge
from .language_context import capture_language_source_v1
from .player_seat_setup import project_own_seat_v1
from .profile_driven_creation import prepare_profile_driven_session_creation_v1
from .seat_setup_rendering import render_seat_setup_v1
from .session_frontend import prepare_guided_session_document
from .stateful_localization import translated
from .task_first_rendering import hidden


def entry_selection(app, journal, raw):
    active = app.managed_stateful.active_session
    return selection(app, "entry-v2", journal.fingerprint, app.recording_task,
        hashlib.sha256(raw).hexdigest() if raw else None,
        None if active is None else [active.review_selection_key.hex(), active.generation,
                                     active.document.content_fingerprint])


def require_selection(actual, expected):
    if not isinstance(actual, str) or not actual.isascii() or not hmac.compare_digest(
            actual, expected):
        raise EventFormConflict("stale")


def entry_fields(app, journal, raw):
    return (hidden("entry_selection", entry_selection(app, journal, raw))
            + hidden("profile_generation", app.frontend_profile.generation))


def round_history(app, journal, labels, token, locale):
    body = ""
    try:
        entries = session_entries(app) if journal.round_heads else ()
    except (ValueError, SkatMindError, OSError):
        entries = ()  # No selection can be authorized from an incomplete inventory.
    for row in journal.round_heads:
        body += '<article><h3>' + escape(labels[row.identity]) + '</h3><p>' + translated(
            locale, "accounting.round_state." + row.status) + '</p>'
        for binding in sorted(row.context.bindings, key=lambda b: b.game_position):
            label = translated(locale, "accounting.game_number", number=binding.game_position)
            try:
                active = open_bound(app, row, binding, entries)
                proof = bound_selection(app, journal, row, binding, active)
            except (ValueError, SkatMindError, OSError):
                body += f'<p role="alert">{label}: {translated(locale, "cent.source")}</p>'
                continue
            body += ('<form method="post" action="/cent/resume">' + token
                + hidden("round_id", row.identity) + hidden("position", binding.game_position)
                + hidden("bound_selection", proof)
                + '<button>' + translated(locale, "accounting.open") + ' · ' + label
                + '</button></form>')
        body += '</article>'
    return body


def render_entry(handler, *, status=200):
    app, locale = handler.server.app_context, handler._frontend_state().locale
    with app.managed_stateful.session_lifecycle_lock:
        root = app.managed_home.root
        journal, raw = load_accounting(root), pending(root)
        token = entry_fields(app, journal, raw)
        labels, proposed = round_labels(journal, locale)
        handler._rendered_language_source = capture_language_source_v1(app, "/cent")
        if raw is not None:
            body = ('<p role="status">' + translated(locale, "cent.pending")
                + '</p><form method="post" action="/cent/recover">' + token
                + '<button>' + translated(locale, "cent.recover") + '</button></form>'
                + '<details><summary>' + translated(locale, "cent.stop") + '</summary><p>'
                + translated(locale, "cent.stop_help") + '</p><form method="post" '
                + 'action="/cent/recover">' + token + hidden("stop", "yes")
                + '<button>' + translated(locale, "cent.stop") + '</button></form></details>')
        else:
            body = ('<section class="friendly-create"><h2>' + translated(locale, "cent.new")
                + '</h2><p>' + escape(proposed) + '</p>'
                + '<form class="form-grid" method="post" action="/cent/start">' + token
                + render_card_knowledge(locale)
                + render_seat_setup_v1(app.frontend_profile.document, locale, family="sessions",
                                       cent=True)
                + platform_field(None, locale) + _tariff(locale, "")
                + '<button type="submit">' + translated(locale, "accounting.start")
                + '</button></form></section>')
        body += f'<section id="round-history"><h2>{translated(locale, "accounting.history")}</h2>'
        body += round_history(app, journal, labels, token, locale)
    handler._content_page("/sessions", return_to="/cent", status=status,
        title=translated(locale, "formats.cent"), content=body + '</section>',
        feedback_family="cent", untranslated_workflow_body=False, task_first=True)


def dispatch_entry(app, path, values, *, activate_session):
    managed = app.managed_stateful
    with managed.session_lifecycle_lock:
        previous = managed.active_session
        with previous.lock if previous is not None else nullcontext():
            root = app.managed_home.root
            journal, raw = load_accounting(root), pending(root)
            generation = app.frontend_profile.generation
            if values.pop("profile_generation", None) != str(generation):
                raise EventFormConflict("stale")
            token = values.pop("entry_selection", None)
            require_selection(token, entry_selection(app, journal, raw))
            def current():
                # The newly reserved intent is the only expected change before commit.
                return (generation == app.frontend_profile.generation
                        and token == entry_selection(app, load_accounting(root), raw))
            try:
                if path == "/cent/start" and raw is None:
                    if set(values) - set(CENT_SETUP_FIELDS) or app.frontend_profile.load_status == (
                            "invalid"):
                        raise AccountingFormError()
                    if values.get("cent_tariff") not in CENT_TARIFFS:
                        raise AccountingFormError("invalid", "cent_tariff")
                    term = supported_terms("cent", resolve_platform(None, values),
                                           tariff=values["cent_tariff"])
                    fields, _ = project_own_seat_v1(values, app.frontend_profile.document)
                    if not fields.get("perspective_seat"):
                        raise AccountingFormError("invalid", "perspective_seat")
                    setup = prepare_profile_driven_session_creation_v1(
                        {**fields, "game_name": "Round 1"},
                        profile=app.frontend_profile.document,
                        expected_profile_generation=app.frontend_profile.generation,
                        existing_session_ids=tuple(e.summary.semantic_product_id for e in
                            session_entries(app) if e.summary.semantic_product_id),
                        entropy_source=secrets.token_bytes)
                    doc = prepare_guided_session_document(setup.session_id, setup.players,
                                                          setup.capture_mode, setup.local_player_id)
                    row = new_round(doc, term)
                    opened = publish_game(app, journal, row, doc, guard=current)
                elif path == "/cent/recover" and raw is not None and not values:
                    opened = complete_game(app, raw, journal, guard=current)
                elif path == "/cent/recover" and raw is not None and values == {"stop": "yes"}:
                    if not current():
                        raise EventFormConflict("stale")
                    release_attempt(root, raw)
                    with app.lock:
                        app.form_feedback.clear("cent")
                    return "/cent"
                elif path == "/cent/resume" and set(values) == {
                        "round_id", "position", "bound_selection"}:
                    row = next((r for r in journal.round_heads if r.identity == values["round_id"]),
                               None)
                    binding = next((b for b in row.context.bindings
                        if str(b.game_position) == values["position"]), None) if row else None
                    if binding is None:
                        raise EventFormConflict("source")
                    opened = open_bound(app, row, binding, session_entries(app))
                    require_selection(values["bound_selection"],
                                      bound_selection(app, journal, row, binding, opened))
                    if not current():
                        raise EventFormConflict("source")
                else:
                    raise AccountingFormError()
                activate_session(opened)
                with app.lock:
                    app.form_feedback.clear("cent")
            except (AccountingConflict, OSError) as error:
                raise EventFormConflict("save") from error
    return "/sessions/current"
