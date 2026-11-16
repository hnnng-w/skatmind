"""Bilingual native cost summaries and Session-backed three-game rounds."""

from fractions import Fraction
from html import escape

from skatmind.accounting_state import CentRoundV1
from skatmind.errors import SkatMindError
from skatmind.event_context_recording_files import load_event_recording_v1
from skatmind.event_context_sources import recording_players_v1

from .accounting_frontend import (
    _tournament,
    capture_accounting_page,
    choice_key,
    known_declarer,
    ordinary_round,
    session_choices,
    tournament_values,
)
from .event_context_forms import actual_platform
from .event_context_frontend import platform_document
from .event_context_rendering import platform_field, suggested_title
from .translation_catalog import translate_frontend_message_v1 as translate
from .workflow_state import StaleFrontendWorkflowRevisionError


def e(value):
    return escape(str(value), quote=True)


def t(locale, key, **values):
    return e(translate(locale, "accounting." + key, **values))


def money(value):
    if value is None:
        return "?"
    value = Fraction(value)
    if 10**6 % value.denominator == 0:
        sign = "-" if value < 0 else ""
        scaled = abs(value.numerator) * (10**6 // value.denominator)
        whole, tail = divmod(scaled, 10**6)
        return sign + (str(whole) if not tail else f"{whole}.{tail:06d}".rstrip("0"))
    return str(value)


def field(locale, name, value="", *, key=None, required=False):
    return (f'<label>{t(locale, key or name)} <input name="{name}" value="{e(value)}"'
            f' maxlength="500"{" required" if required else ""}></label>')


def select(locale, name, choices, selected="", *, key=None):
    return (f'<label>{t(locale, key or name)} <select name="{name}">'
        + ''.join(f'<option value="{e(value)}"{" selected" if value == selected else ""}>'
                  f'{e(label)}</option>' for value, label in choices) + '</select></label>')


def choices(locale, *keys):
    return [(key, translate(locale, "accounting." + key)) for key in keys]


def form(page, active, family, action, fields, locale, *, label=None, round_id=None):
    hidden = ('' if round_id is None else
              f'<input type="hidden" name="round_id" value="{e(round_id)}">')
    return (f'<form method="post" action="/{family}/accounting/{action}" class="form-grid">'
        f'<input type="hidden" name="managed_handle" value="{e(active.handle)}">'
        f'<input type="hidden" name="accounting_selection" value="{page.selection}">'
        + hidden + fields + f'<button type="submit">{t(locale, label or action)}</button></form>')


def _costs(page, active, family, locale):
    event = page.event_page
    if event.context is None or not event.context.tournament:
        return ''
    values = tournament_values(page)
    row = _tournament(page, values)
    body = f'<h3>{t(locale, "tournament")}</h3>'
    body += f'<p>{t(locale, "cost_boundary", start=row.rule_from_position,
        through=row.prepared.game_position - 1, before=row.losses_before,
        after=row.prepared.own_losses if row.prepared.status == "ready" else "?")}</p><ul>'
    subtotal = Fraction()
    for component in row.components:
        if component.kind not in ("entry", "table", "earlier_losses", "additional_losses"):
            continue
        value = None if component.value is None else -component.value.value
        if value is not None:
            subtotal += value
        body += f'<li>{t(locale, component.kind)}: {money(value)} EUR</li>'
    body += f'</ul><p>{t(locale, "cost_subtotal", total=money(subtotal))}</p>'
    fields = field(locale, "entry_total", money(Fraction(values["entry_total"]))
                   if values.get("entry_total") else "")
    if actual_platform(platform_document(event), row.prepared.terms) == "euroskat":
        fields += select(locale, "plus_level", [("", translate(locale, "accounting.unknown")),
            *[(str(n), str(n)) for n in range(9)]], values.get("plus_level", ""))
        fields += f'<p>{t(locale, "plus_help")}</p>'
    else:
        fields += field(locale, "table_total", money(Fraction(values["table_total"]))
                        if values.get("table_total") else "")
        body += f'<p>{t(locale, "local_fees_unknown")}</p>'
    return body + form(page, active, family, "save", fields, locale)


def _round_summary(row, locale, *, status=None):
    state = t(locale, "round_state." + (status or row.status))
    body = f'<p>{e(row.context.event_name)} · {state}</p>'
    platform = row.context.terms[-1].platform or "unknown"
    body += f'<p>{e(translate(locale, "event.platform." + platform))}</p>'
    boundary = "provider_boundary" if platform == "euroskat" else "local_fees_unknown"
    body += f'<p>{t(locale, boundary)}</p>'
    body += '<table><thead><tr>' + ''.join(f'<th>{t(locale, key)}</th>' for key in (
        "position", "participant", "gross", "fee", "net")) + '</tr></thead><tbody>'
    totals = {player: [Fraction(), Fraction(), Fraction(), True]
              for player in row.context.participant_ids}
    for number in range(1, 4):
        status, rows, origin = row.game(number)
        if rows is None:
            body += f'<tr><td>{number}</td><td colspan="4">{t(locale, status)}</td></tr>'
            for values in totals.values():
                values[3] = False
            continue
        for index, (item, label) in enumerate(zip(rows, row.participant_labels, strict=True)):
            values = totals[item.player_id]
            values[0] += item.gross.value
            if item.fee is not None:
                values[1] += item.fee.value
            if item.net is not None:
                values[2] += item.net.value
            else:
                values[3] = False
            position = f'<td rowspan="3">{number} · {t(locale, origin)}</td>' if index == 0 else ''
            body += (f'<tr>{position}<td>{e(label)}</td>'
                f'<td>{money(item.gross.value)}</td>'
                f'<td>{money(None if item.fee is None else item.fee.value)}</td>'
                f'<td>{money(None if item.net is None else item.net.value)}</td></tr>')
    body += '</tbody></table>'
    for player, label in zip(row.context.participant_ids, row.participant_labels, strict=True):
        gross, fee, net, complete = totals[player]
        body += f'<p>{e(label)}: {t(locale, "round_totals", gross=money(gross),
            fee=money(fee), net=money(net) if complete else "?")}</p>'
    return body


def _tariff(locale, value):
    return select(locale, "cent_tariff", [("", translate(locale, "accounting.choose")),
        ("1/2", "0.5"), *[(s, s) for s in ("1", "2", "3", "5")]], value or "")


def _result_form(page, active, row, number, locale):
    supplied = next((c for c in row.confirmations if c.position == number), None)
    if row.game(number)[0] in ("settled", "passed") and supplied is None:
        return f'<p>{t(locale, "derived")}</p>'
    status = ("passed" if supplied and supplied.status == "passed" else
              "lost" if supplied and supplied.settlement and supplied.settlement < 0 else "won")
    fields = f'<input type="hidden" name="position" value="{number}">'
    options = ("won", "lost", "passed", "derived") if supplied else ("won", "lost", "passed")
    fields += select(locale, "game_status", choices(locale, *options), status)
    if known_declarer(row, number) is None:
        declarer = (str(row.context.participant_ids.index(supplied.declarer_id) + 1)
                    if supplied and supplied.declarer_id else "")
        fields += select(locale, "declarer", [("", translate(locale, "accounting.choose")),
            *[(str(i), label) for i, label in enumerate(row.participant_labels, 1)]], declarer)
    value = (abs(supplied.settlement) // (2 if supplied.settlement < 0 else 1)
             if supplied and supplied.settlement else "")
    fields += field(locale, "game_value", value)
    result = form(page, active, "sessions", "game", fields, locale)
    if supplied is not None:
        result = f'<details><summary>{t(locale, "correct_result")}</summary>{result}</details>'
    return result


def _open_forms(page, active, row, number, locale, entries):
    hidden = f'<input type="hidden" name="position" value="{number}">'
    bound = next((b for b in row.context.bindings if b.game_position == number), None)
    fields = hidden if bound else hidden + '<input type="hidden" name="source_choice" value="new">'
    body = form(page, active, "sessions", "open", fields, locale,
                label="open" if bound else "continue_game")
    if bound:
        return body + _result_form(page, active, row, number, locale)
    if not entries:
        return body
    body += f'<details><summary>{t(locale, "attach_existing")}</summary>'
    for entry in entries:
        document = load_event_recording_v1(entry.path, "session")
        fields = hidden + f'<input type="hidden" name="source_choice" value="{choice_key(entry)}">'
        fields += f'<p>{e(entry.summary.display_label)}</p>'
        for index, player in enumerate(document.state.players, 1):
            if player.player_id in row.context.participant_ids:
                continue
            fields += f'<p>{e(player.player_label or player.player_id)}</p>'
            fields += select(locale, f"map_{index}", [("", translate(locale, "accounting.choose")),
                *[(str(i), label) for i, label in enumerate(row.participant_labels, 1)]],
                key="maps_to")
        body += form(page, active, "sessions", "open", fields, locale, label="attach_existing")
    return body + '</details>'


def _cent(page, active, locale, app):
    row = page.current
    body = f'<h3>{t(locale, "cent")}</h3>'
    document = page.event_page.document
    if row is None and (page.event_page.context is None or not page.event_page.context.tournament):
        existing = page.event_page.context
        term = None if existing is None else existing.applicable_terms(1)
        fields = field(locale, "title", existing.event_name if existing else
            suggested_title(app, document, locale), key="editable_title", required=True)
        fields += platform_field(document, locale, term)
        fields += _tariff(locale, None if term is None else term.financial.cent_tariff)
        if recording_players_v1(document)[1] is None and existing is None:
            fields += select(locale, "selected_player", [(str(index), p.player_label or p.player_id)
                for index, p in enumerate(document.state.players, 1)], key="participant")
        fields += f'<p>{t(locale, "participants_once")}</p>'
        body += form(page, active, "sessions", "start", fields, locale)
    if type(row) is CentRoundV1:
        preview = ordinary_round(row, page.documents)
        body += _round_summary(preview, locale, status=row.status)
        if row.status == "open":
            owned = {b.source.product_id for r in page.journal.round_heads
                     for b in r.context.bindings}
            entries = tuple(entry for entry in session_choices(app)
                            if entry.summary.semantic_product_id not in owned)
            for number in range(1, 4):
                # Only the next position is offered until previous games are established.
                if number > 1 and preview.game(number - 1)[0] not in (
                        "settled", "passed"):
                    break
                body += f'<h4>{t(locale, "game_number", number=number)}</h4>'
                body += _open_forms(page, active, preview, number, locale, entries)
        status = "finished" if row.status == "open" else "open"
        if status == "open" or all(preview.game(n)[0] in ("settled", "passed")
                                   for n in range(1, 4)):
            fields = f'<input type="hidden" name="status" value="{status}">'
            body += form(page, active, "sessions", "lifecycle", fields, locale,
                         label="finish_round" if status == "finished" else "reopen_round")
        if row.status != "open":
            count = 1 + sum(r.table_id == row.table_id for r in page.journal.round_heads)
            first = next(r for r in page.journal.round_heads if r.table_id == row.table_id)
            title = translate(locale, "accounting.next_title", title=first.context.event_name[:450],
                              number=count)
            fields = field(locale, "title", title, key="editable_title", required=True)
            fields += platform_field(document, locale, row.context.applicable_terms(3))
            fields += _tariff(locale, row.context.applicable_terms(3).financial.cent_tariff)
            body += form(page, active, "sessions", "next", fields, locale)
    if page.journal.round_heads:
        body += f'<details><summary>{t(locale, "history")}</summary>'
        for saved in page.journal.round_heads:
            fields = (f'<p>{e(saved.context.event_name)}</p><input type="hidden" name="position" '
                      f'value="{saved.context.bindings[0].game_position}">')
            body += form(page, active, "sessions", "open", fields, locale, round_id=saved.identity)
        body += '</details>'
    return body


def render_accounting(app, active, family, locale):
    try:
        with active.capture.lock if family == "matches" else active.lock:
            page = capture_accounting_page(app, active, family)
        body = f'<section class="panel" id="accounting"><h2>{t(locale, "title")}</h2>'
        body += _costs(page, active, family, locale)
        if family == "sessions":
            body += _cent(page, active, locale, app)
        return body + '</section>'
    except (OSError, ValueError, SkatMindError, StaleFrontendWorkflowRevisionError):
        return (f'<section id="accounting"><h2>{t(locale, "title")}</h2>'
                f'<p role="alert">{t(locale, "unavailable")}</p></section>')
