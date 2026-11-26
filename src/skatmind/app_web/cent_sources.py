"""Resolve round membership against a unique managed recording and its retained version."""

from hashlib import sha256
from hmac import new as hmac_new

from skatmind.accounting_state import CentRoundV1
from skatmind.accounting_store import load_accounting
from skatmind.automatic_learning_codec import canonical_json
from skatmind.errors import SkatMindError
from skatmind.event_context_sources import recording_version_v1

from .accounting_forms import AccountingFormError
from .cent_continuity import entries_for, unique_entry, validate_binding
from .cent_round_context import round_labels
from .session_frontend import open_guided_session_v1
from .translation_catalog import translate_frontend_message_v1
from .whole_match_progress import file_identity


def selection(app, purpose, *scope):
    return hmac_new(app.language_context.key, b"cent-entry-v1\0" +
                    canonical_json([purpose, *scope]), sha256).hexdigest()


def session_entries(app):
    return entries_for(app.managed_stateful.root("sessions"))


def open_bound(app, row, binding, entries):
    entry = unique_entry(entries, binding.source)
    active = open_guided_session_v1(app.managed_stateful.root("sessions"), entry)
    try:
        if validate_binding(row, active.document, active.path) != binding:
            raise AccountingFormError("source")
    except (SkatMindError, ValueError) as error:
        raise AccountingFormError("source") from error
    return active


def bound_selection(app, journal, row, binding, active):
    if file_identity(active.path) != active.saved_file_identity:
        raise AccountingFormError("source")
    return selection(app, "bound", journal.fingerprint, row.identity, binding.game_position,
                     active.handle, active.document.content_fingerprint, active.saved_file_identity)


def member_label(app, active, locale):
    try:
        key = recording_version_v1(active.document).source
        journal = load_accounting(app.managed_home.root)
        owner = journal.for_source(key)
        if not isinstance(owner, CentRoundV1):
            return ""
        binding = owner.context.binding(key)
        bound = open_bound(app, owner, binding, session_entries(app))
        if bound.path != active.path or bound.document != active.document:
            raise AccountingFormError("source")
        labels, _ = round_labels(journal, locale)
        return translate_frontend_message_v1(locale, "cent.member", title=labels[owner.identity],
                                             number=binding.game_position)
    except (OSError, ValueError, SkatMindError):
        return translate_frontend_message_v1(locale, "cent.source")


def review_memberships(app, discovery, locale):
    journal = load_accounting(app.managed_home.root)
    labels, _ = round_labels(journal, locale)
    result = {}
    by_id = {}
    for entry in discovery.entries:
        by_id.setdefault(entry.summary.semantic_product_id, []).append(entry)
    for row in journal.round_heads:
        for binding in row.context.bindings:
            matches = by_id.get(binding.source.product_id, ())
            token = None
            if len(matches) == 1 and not discovery.view.candidate_limit_reached:
                try:
                    active = open_bound(app, row, binding, matches)
                    token = bound_selection(app, journal, row, binding, active)
                except (OSError, ValueError, SkatMindError):
                    pass
            for entry in matches:
                result[entry.summary.handle] = labels[row.identity], binding.game_position, token
    return result
