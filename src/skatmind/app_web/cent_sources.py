"""Resolve round membership against a unique managed recording and its retained version."""

from dataclasses import replace
from hashlib import sha256
from hmac import new as hmac_new

from skatmind.accounting_state import CentRoundV1
from skatmind.accounting_store import load_accounting
from skatmind.automatic_learning_codec import canonical_json
from skatmind.errors import SkatMindError
from skatmind.event_context_sources import build_event_binding_v1, recording_version_v1
from skatmind.session_history import build_session_state_from_accepted_prefix_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1

from .accounting_forms import AccountingFormError
from .managed_item_discovery import discover_managed_items_v1
from .session_frontend import open_guided_session_v1
from .translation_catalog import translate_frontend_message_v1
from .whole_match_progress import file_identity


def selection(app, purpose, *scope):
    return hmac_new(app.language_context.key, b"cent-entry-v1\0" +
                    canonical_json([purpose, *scope]), sha256).hexdigest()


def session_entries(app):
    result = discover_managed_items_v1(app.managed_stateful.root("sessions"),
        family="sessions", generation=1)
    if result.view.candidate_limit_reached:
        raise AccountingFormError("source")
    return result.entries


def validate_binding(row, document):
    version = recording_version_v1(document)
    binding = row.context.binding(version.source)
    if binding is None:
        raise AccountingFormError("source")
    rebuilt = build_event_binding_v1(document, game_position=binding.game_position,
        selected_player_id=binding.source_selected_player_id,
        player_map={p.source_player_id: p.event_player_id for p in binding.players})
    if replace(rebuilt, attached_source=binding.attached_source) != binding:
        raise AccountingFormError("source")
    # Normal capture appends commands and pre-play checkpoints. An ID alone
    # cannot distinguish a replaced file with the same seats and perspective.
    retained = {binding.attached_source, *(r.source for r in row.recordings
                                            if r.source.source == version.source)}
    for prior in retained:
        if prior == version:
            continue
        if prior.revision >= version.revision:
            raise AccountingFormError("source")
        prefix = build_session_state_from_accepted_prefix_v1(document.state,
                                                             target_revision=prior.revision)
        checkpoints = tuple(c for c in document.decision_checkpoints
                            if c.source_revision < prior.revision)
        if build_session_persistence_document_v1(prefix, decision_checkpoints=checkpoints
                ).content_fingerprint != prior.content_fingerprint:
            raise AccountingFormError("source")
    return binding


def open_bound(app, row, binding, entries):
    entries = [e for e in entries if e.summary.semantic_product_id == binding.source.product_id]
    if len(entries) != 1 or entries[0].summary.status != "available":
        raise AccountingFormError("source")
    active = open_guided_session_v1(app.managed_stateful.root("sessions"), entries[0])
    try:
        if validate_binding(row, active.document) != binding:
            raise AccountingFormError("source")
    except (SkatMindError, ValueError) as error:
        raise AccountingFormError("source") from error
    return active


def bound_selection(app, journal, row, binding, active):
    return selection(app, "bound", journal.fingerprint, row.identity, binding.game_position,
                     active.handle, active.document.content_fingerprint, file_identity(active.path))


def member_label(app, active, locale):
    try:
        key = recording_version_v1(active.document).source
        owner = load_accounting(app.managed_home.root).for_source(key)
        if not isinstance(owner, CentRoundV1):
            return ""
        binding = owner.context.binding(key)
        bound = open_bound(app, owner, binding, session_entries(app))
        if bound.path != active.path or bound.document != active.document:
            raise AccountingFormError("source")
        return translate_frontend_message_v1(locale, "cent.member", title=owner.context.event_name,
                                             number=binding.game_position)
    except (OSError, ValueError, SkatMindError):
        return translate_frontend_message_v1(locale, "cent.source")


def review_memberships(app, discovery):
    journal = load_accounting(app.managed_home.root)
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
                result[entry.summary.handle] = row.context.event_name, binding.game_position, token
    return result
