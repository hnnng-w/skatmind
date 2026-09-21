"""Source facts and retained typed correction effects; rendering never builds candidates."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

from skatmind.game_declaration import build_serializable_game_declaration

from .compact_declaration_rendering import compact_declaration_fields
from .session_declaration_correction import correction_entries, current_selection
from .stateful_localization import card_name, player_name, text, translated
from .task_first_rendering import (
    disclosure,
    form,
    hidden,
    paragraph,
    select_field,
    technical_details,
)
from .translation_catalog import load_frontend_translation_catalogs_v1

PREFIX = "/sessions/declaration-correction/"


def _action(context, locale, action, token, key, fields="", **options):
    return form(locale, PREFIX + action, hidden("managed_handle", context.handle)
        + hidden("correction_selection", token) + fields, key, **options)


def correction_actions(context, locale):
    return {item.record.command.kind: _action(context, locale, "select", item.token,
                "session.correction." + item.record.command.kind)
            for item in correction_entries(context)}


def _declaration_value(locale, name, value):
    if type(value) is bool:
        return text(locale, "common.answer.yes" if value else "common.answer.no")
    if value is None:
        return text(locale, "declaration.not_entered")
    return text(locale, "task.value." + value) if name == "game_type" else str(value)


def _fact(context, locale, command):
    if command.kind == "set_declarer":
        return escape(player_name(locale, context.state.players, command.declarer_player_id))
    return ' · '.join(translated(locale, "declaration." + name) + ': '
        + escape(_declaration_value(locale, name, value))
        for name, value in build_serializable_game_declaration(command.declaration).items()
        if value is not False and (value is not None or name == "bid_value"))


def _change(context, locale, original, replacement):
    if original.kind == "set_declarer":
        return '<p>' + _fact(context, locale, original) + ' → ' + _fact(
            context, locale, replacement) + '</p>'
    before = build_serializable_game_declaration(original.declaration)
    after = build_serializable_game_declaration(replacement.declaration)
    return '<ul>' + ''.join('<li>' + translated(locale, "declaration." + name) + ': '
        + escape(_declaration_value(locale, name, before[name])) + ' → '
        + escape(_declaration_value(locale, name, value)) + '</li>'
        for name, value in after.items() if before[name] != value) + '</ul>'


def _record(context, locale, record):
    """Every removed typed record remains inspectable, with human Player/Card labels."""
    command = record.command
    label = translated(locale, "task.command." + command.kind)
    if command.kind == "record_play":
        index = sum(r.command.kind == "record_play" for r in context.state.command_log
                    if r.revision <= record.revision)
        label = (f'<a href="#session-play-{index}">' + translated(locale, "recovery.location",
            trick=(index - 1) // 3 + 1, position=(index - 1) % 3 + 1) + '</a>')
    if command.kind in {"set_declarer", "set_declaration"}:
        return label + ': ' + _fact(context, locale, command)
    if command.kind in {"record_play", "record_dealt_card", "record_discard", "set_public_hand"}:
        player = getattr(command, "player_id", None)
        if player:
            label += ' — ' + escape(player_name(locale, context.state.players, player))
        if getattr(command, "destination", None) == "skat":
            label += ' — ' + translated(locale, "task.skat")
        cards = getattr(command, "cards", ()) or (getattr(command, "card", None),)
        label += ': ' + ', '.join(escape(card_name(locale, c)) for c in cards if c)
    elif command.kind == "set_game_end":
        label += ': ' + translated(locale, "task.value." + command.game_end_reason)
        if command.game_end:
            label += _event_evidence(context, locale, command.game_end)
    elif command.kind == "set_game_event":
        label += _event_evidence(context, locale, command.event)
    elif command.kind == "set_game_metadata":
        label += ': ' + escape(' · '.join(v for v in (command.game_id, command.played_at) if v))
    return label


def _event_evidence(context, locale, value):
    """Inspect supplied nested event/end facts without accepting or inferring any."""
    catalog = load_frontend_translation_catalogs_v1()[locale]
    if isinstance(value, Mapping):
        rows = []
        for key, item in value.items():
            if key == "schema_version":
                continue
            field_key = "task.field." + {"kind": "event_kind", "status": "consent_status",
                "exposing_defender_player_id": "player_id", "defender_player_id": "player_id",
                "consenting_defender_player_ids": "consenting_player_ids",
                "declarer_hand_cards_remaining": "remaining_card_count"}.get(key, key)
            label = catalog.get(field_key, catalog["session.correction.evidence"])
            rows.append('<li>' + escape(label) + ': '
                        + _event_evidence(context, locale, item) + '</li>')
        return '<ul>' + ''.join(rows) + '</ul>'
    if isinstance(value, (tuple, list)):
        return ' · '.join(_event_evidence(context, locale, v) for v in value)
    if value in {p.player_id for p in context.state.players}:
        return escape(player_name(locale, context.state.players, value))
    if isinstance(value, str):
        from skatmind.deck import get_full_deck
        if value in get_full_deck():
            return escape(card_name(locale, value))
        return escape(catalog.get("task.value." + value, value))
    return escape(str(value))


def _records(context, locale, records):
    return '<ol>' + ''.join('<li>' + _record(context, locale, r) + '</li>'
                           for r in records) + '</ol>'


def render_session_correction(context, locale):
    state = context.declaration_correction
    selected = state.selected
    body = '<div id="session-correction-feedback"></div>'
    if not current_selection(context, selected):
        return body
    original = selected.record.command
    preview = state.preview
    result = None if preview is None else preview.result
    ready = result is not None and result.status in {"applied", "partial", "unchanged"}
    body += '<section id="session-declaration-correction" tabindex="-1"><h2>' + translated(
        locale, "session.correction.title") + '</h2>'
    body += '<p>' + translated(locale, "session.correction.original") + ': ' + _fact(
        context, locale, original) + '</p>'
    # The other fact is context, never another mutable field in this operation.
    opposite = "set_declaration" if original.kind == "set_declarer" else "set_declarer"
    other = tuple(r for r in selected.source.state.command_log if r.command.kind == opposite)
    if len(other) == 1:
        body += '<p>' + translated(locale, "session.correction.context") + ': ' + _fact(
            context, locale, other[0].command) + '</p>'
    main = ''
    if not ready:
        proposal = state.proposal or original
        fields = hidden("correction_kind", original.kind)
        if original.kind == "set_declarer":
            fields += select_field(locale, "player_id", "task.field.declarer_player_id",
                ((p.player_id, player_name(locale, context.state.players, p.player_id))
                 for p in context.state.players), proposal.declarer_player_id, required=True)
        else:
            fields += compact_declaration_fields(locale,
                build_serializable_game_declaration(proposal.declaration), session=True)
        main = _action(context, locale, "preview", selected.token,
                       "session.correction.preview", fields, primary=True)
    else:
        body += '<p>' + translated(locale, "session.correction.proposed") + '</p>'
        body += _change(context, locale, original, result.replacement_command)
        plays = sum(r.command.kind == "record_play" for r in result.state.command_log)
        suffix = (selected.source.state.command_log[selected.record.revision:]
                  if result.status == "unchanged" else result.replayed_suffix_records)
        body += paragraph(locale, "session.correction.retained", plays=plays, records=len(suffix))
        if suffix:
            body += disclosure(locale, "session.correction.retained_details", _records(
                context, locale, suffix))
        partial = result.status == "partial"
        if partial:
            removed = result.discarded_suffix_records
            lost_plays = sum(r.command.kind == "record_play" for r in removed)
            body += '<div class="session-correction-warning">' + paragraph(locale,
                "session.correction.removal", plays=lost_plays, other=len(removed) - lost_plays)
            body += '<p>' + translated(locale, "session.correction.boundary") + ': ' + _record(
                context, locale, removed[0]) + '</p>'
            for diagnostic in result.diagnostics:
                key = {"turn_order_violation": "turn", "phase_violation": "phase",
                       "declaration_violation": "declaration",
                       "information_policy_violation": "knowledge",
                       "card_ownership_violation": "ownership"}.get(diagnostic.code, "conflict")
                body += paragraph(locale, "session.correction.reason." + key)
            body += paragraph(locale, "session.correction.final") + '</div>'
            body += disclosure(locale, "session.correction.removed_details", _records(
                context, locale, removed))
            next_key = ("task.session.next.set_game_end" if plays == 30 else
                        "task.session.next.record_play") if result.state.phase == "play" else (
                        "session.correction.next_skat" if result.state.phase == "skat_and_discard"
                        else "task.session.phase." + result.state.phase)
            body += paragraph(locale, "session.correction.next") + paragraph(locale, next_key)
        elif result.status == "unchanged":
            body += paragraph(locale, "session.correction.unchanged")
        else:
            body += paragraph(locale, "session.correction.lossless")
        if result.status != "unchanged" and context.execution is not None:
            body += paragraph(locale, "session.correction.result")
        confirmation = ('<label><input type="checkbox" name="confirm_apply" required>'
            + translated(locale, "session.correction.consent") + '</label>' if partial else '')
        main = _action(context, locale, "apply", preview.apply_token,
            "session.correction.apply_partial" if partial else "session.correction.apply",
            confirmation, primary=True, submitter=None if partial else ("confirm_apply", "on"))
    body += '<div class="recovery-primary-actions">' + main + _action(
        context, locale, "cancel", selected.token, "recovery.cancel") + '</div>'
    if ready:
        body += _action(context, locale, "select", selected.token, "session.correction.edit")
    if result is not None and result.diagnostics:
        body += technical_details(locale, {
            "diagnostics": [d.to_dict() for d in result.diagnostics]})
    return body + '</section>'
