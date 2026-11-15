"""Compact bilingual native monetary forms and read-only retained interpretations."""

from fractions import Fraction
from html import escape

from skatmind.accounting_state import CentRoundV1
from skatmind.errors import SkatMindError
from skatmind.event_context_sources import recording_players_v1
from skatmind.mode_accounting import CENT_SOURCE, STANDARD_RULE, STANDARD_SOURCE, component_totals

from .accounting_frontend import capture_accounting_page, choice_key, fresh_round, session_choices
from .event_context_rendering import _amount
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


def _provenance(locale, value=""):
    return field(locale, "provenance", value, required=True)


def _tournament(page, active, family, locale):
    event = page.event_page
    if event.context is None or not event.context.tournament:
        return ''
    row = page.current
    body = f'<h3>{t(locale, "tournament")}</h3><p>{t(locale, "tournament_help")}</p>'
    if row is not None:
        body += _components(row, locale)
        if row.context != event.context or row.prepared != event.prepared:
            body += f'<p role="status">{t(locale, "stale")}</p>'
    legacy = event.prepared.terms.financial
    fields = select(locale, "rule", choices(locale, "unverified", STANDARD_RULE),
                    "unverified" if row is None else row.rule)
    if family == "matches":
        fields += field(locale, "through_position", event.prepared.game_position - 1
                        if row is None else row.prepared.game_position - 1)
    boundary = (event.prepared.checkpoint.through_position + 1
                if event.prepared.checkpoint is not None else 1)
    fields += field(locale, "rule_from_position",
                    boundary if row is None else row.rule_from_position)
    source = (legacy.fee_source or STANDARD_SOURCE) if row is None else row.rule_source
    fields += field(locale, "fee_reference", source.reference, required=True)
    fields += field(locale, "fee_edition", source.edition, required=True)
    for kind in ("entry", "table"):
        old = None if row is None else next((o for o in row.obligations if o.kind == kind), None)
        paid, committed = getattr(legacy, kind + "_paid"), getattr(legacy, kind + "_committed")
        fields += field(locale, kind + "_total", "" if old is None else _amount(old.total))
        fields += field(locale, kind + "_paid", _amount(paid if old is None else old.paid))
        if paid is not None or committed is not None:
            fields += f'<p>{t(locale, "legacy", paid=_amount(paid) or "?",
                             committed=_amount(committed) or "?")}</p>'
        fields += select(locale, kind + "_overlap", [("", translate(locale, "accounting.choose")),
            *choices(locale, "explicit_total", "committed_is_total", "committed_is_remaining")],
            "explicit_total" if old is not None else "", key="overlap")
    fields += f'<p>{t(locale, "plus_help")}</p>'
    fields += field(locale, "plus_level",
                    "" if row is None or row.plus_level is None else row.plus_level)
    fields += select(locale, "table_rule", choices(locale, "supplied", "published_plus"),
                     "supplied" if row is None else row.table_rule)
    fields += select(locale, "tandem_participation", choices(locale, "unknown", "yes", "no"),
                     "unknown" if row is None else row.tandem_participation)
    earlier = None if row is None else next((o for o in row.obligations
                                           if o.kind == "earlier_losses"), None)
    fields += field(locale, "earlier_losses", "" if earlier is None else _amount(earlier.total))
    fields += field(locale, "earlier_paid", "" if earlier is None else _amount(earlier.paid))
    fields += f'<p>{t(locale, "receipt_help")}</p>'
    for pool in ("base", "plus", "tandem"):
        receipt = None if row is None else next((r for r in row.receipts if r.pool == pool), None)
        fields += field(locale, pool + "_receipt",
                        "" if receipt is None else _amount(receipt.received))
    fields += select(locale, "receipts_complete", choices(locale, "unknown", "yes"),
                     "yes" if row is not None and row.receipts_complete else "unknown")
    if event.prepared.terms.mode == "tournament_cent":
        fields += f'<p>{t(locale, "side_help")}</p>'
        fields += field(locale, "side_settlement", "" if row is None or row.side_settlement is None
                        else money(row.side_settlement.value))
    fields += select(locale, "status", choices(locale, "open", "finished"),
                     "open" if row is None else row.status)
    fields += _provenance(locale, "" if row is None else row.provenance)
    return body + f'<details><summary>{t(locale, "save")}</summary>' + form(
        page, active, family, "save", fields, locale) + '</details>'


def _components(row, locale):
    body = f'<p>{t(locale, "revision", revision=row.revision)}</p><ul>'
    for component in row.components:
        name = component.kind.split(":")[-1] + "_receipt" if component.kind.startswith(
            "receipt:") else component.kind
        value = money(None if component.value is None else component.value.value)
        body += f'<li>{t(locale, name)}: {value} EUR</li>'
    known, net = component_totals(row.components)
    body += f'</ul><p>{t(locale, "totals", known=money(known), net=money(net))}</p>'
    for item in row.obligations:
        body += f'<p>{t(locale, "payment", kind=translate(locale, "accounting." + item.kind),
            total=_amount(item.total), paid=_amount(item.paid) or "?",
            remaining=money(item.remaining))}</p>'
    return body


def _round_summary(row, locale):
    body = (f'<p>{e(row.context.event_name)} · {t(locale, row.status)} · '
            f'{t(locale, "revision", revision=row.revision)}</p>')
    body += f'<p>{t(locale, "provider_boundary")}</p><table><thead><tr>'
    body += ''.join(f'<th>{t(locale, key)}</th>' for key in (
        "position", "participant", "gross", "fee", "net", "basis")) + '</tr></thead><tbody>'
    totals = {player: [Fraction(), Fraction(), Fraction(), True]
              for player in row.context.participant_ids}
    for number in range(1, 4):
        status, rows, origin = row.game(number)
        if rows is None:
            body += f'<tr><td>{number}</td><td colspan="5">{t(locale, status)}</td></tr>'
            for values in totals.values():
                values[3] = False
            continue
        for item, label in zip(rows, row.participant_labels, strict=True):
            totals[item.player_id][0] += item.gross.value
            if item.fee is not None:
                totals[item.player_id][1] += item.fee.value
            if item.net is not None:
                totals[item.player_id][2] += item.net.value
            else:
                totals[item.player_id][3] = False
            gaps = ', '.join(translate(locale, "accounting." + key) for key in item.unresolved)
            body += (f'<tr><td>{number}</td><td>{e(label)}</td><td>{money(item.gross.value)}</td>'
                f'<td>{money(None if item.fee is None else item.fee.value)}</td>'
                f'<td>{money(None if item.net is None else item.net.value)}</td>'
                f'<td>{t(locale, origin)} {e(gaps)}</td></tr>')
    body += '</tbody></table>'
    for player, label in zip(row.context.participant_ids, row.participant_labels, strict=True):
        gross, fee, net, complete = totals[player]
        body += f'<p>{e(label)}: {t(locale, "round_totals", gross=money(gross),
            fee=money(fee), net=money(net) if complete else "?")}</p>'
    actual = t(locale, "yes" if row.actual_block_complete else "unknown")
    body += f'<p>{t(locale, "actual_complete")}: {actual}</p>'
    for confirmation in row.confirmations:
        if confirmation.personal_net is not None:
            message = t(locale, "game_external", position=confirmation.position,
                        net=money(confirmation.personal_net.value))
            body += f'<p>{message} · {e(confirmation.provenance)}</p>'
    if row.adjustment is not None:
        body += (f'<p>{t(locale, "adjustment")}: {money(row.adjustment.amount.value)} EUR · '
                 f'{e(row.adjustment.provenance)}</p>')
    if row.net_confirmation is not None:
        confirmation = row.net_confirmation
        message = t(locale, "confirmed_net", net=money(confirmation.personal_net.value),
                    count=len(confirmation.round_ids))
        body += f'<p>{message} · {e(confirmation.provenance)}</p>'
    known, net = row.personal_totals()
    body += f'<p>{t(locale, "personal_totals", known=money(known), net=money(net))}</p>'
    return body


def _cent(page, active, locale, app):
    row = page.current
    body = f'<h3>{t(locale, "cent")}</h3>'
    if row is None and (page.event_page.context is None or not page.event_page.context.tournament):
        document = page.event_page.document
        existing = page.event_page.context
        tariff = "" if existing is None else existing.applicable_terms(1).financial.cent_tariff
        source = (CENT_SOURCE if existing is None else
                  existing.applicable_terms(1).financial.fee_source or CENT_SOURCE)
        fields = field(locale, "round_name", required=True)
        fields += select(locale, "cent_tariff", [("", translate(locale, "accounting.choose")),
            ("1/2", "0.5"), *[(s, s) for s in ("1", "2", "3", "5")]], tariff)
        if recording_players_v1(document)[1] is None:
            fields += select(locale, "selected_player", [(str(index), p.player_label or p.player_id)
                for index, p in enumerate(document.state.players, 1)], key="participant")
        fields += f'<p>{t(locale, "participants_once")}</p>'
        fields += field(locale, "fee_reference", source.reference)
        fields += field(locale, "fee_edition", source.edition)
        fields += select(locale, "confirm_terms", choices(locale, "unknown", "yes"))
        fields += _provenance(locale)
        body += form(page, active, "sessions", "start", fields, locale)
    if type(row) is CentRoundV1:
        body += _round_summary(row, locale)
        if row.net_confirmation is not None and any(
                page.journal.head(identity).activity_fingerprint != fingerprint
                for identity, fingerprint in zip(row.net_confirmation.round_ids,
                    row.net_confirmation.activity_fingerprints, strict=True)):
            body += f'<p role="status">{t(locale, "stale")}</p>'
        preview = fresh_round(row, page.documents)
        if preview.recordings != row.recordings:
            body += f'<p role="status">{t(locale, "stale")}</p>'
            body += (f'<details><summary>{t(locale, "preview")}</summary>'
                     + _round_summary(preview, locale) + '</details>')
        if row.status == "open":
            choices_source = [("new", translate(locale, "accounting.new_session"))]
            owned = {binding.source.product_id for saved in page.journal.round_heads
                     for binding in saved.context.bindings}
            choices_source += [(choice_key(entry), entry.summary.display_label or
                translate(locale, "accounting.saved_session", number=index))
                for index, entry in enumerate(session_choices(app), 1)
                if entry.summary.semantic_product_id not in owned]
            for number in range(1, 4):
                body += f'<details><summary>{t(locale, "game_number", number=number)}</summary>'
                hidden = f'<input type="hidden" name="position" value="{number}">'
                bound = next((b for b in row.context.bindings if b.game_position == number), None)
                fields = hidden
                if bound is None:
                    fields += select(locale, "source_choice", choices_source, "new")
                    for index in range(1, 4):
                        fields += select(locale, f"map_{index}", [(str(i), label) for i, label
                            in enumerate(row.participant_labels, 1)], str(index), key="maps_to")
                    fields += _provenance(locale)
                body += form(page, active, "sessions", "open", fields, locale)
                if bound is not None:
                    supplied = next((c for c in row.confirmations if c.position == number), None)
                    fields = hidden + select(locale, "game_status", choices(locale,
                        "derived", "settled", "passed", "interrupted", "external"),
                        "derived" if supplied is None else supplied.status)
                    declarer = (str(row.context.participant_ids.index(supplied.declarer_id) + 1)
                                if supplied and supplied.declarer_id else "1")
                    fields += select(locale, "declarer", [(str(i), label) for i, label
                        in enumerate(row.participant_labels, 1)], declarer)
                    fields += field(locale, "settlement",
                                    supplied.settlement if supplied and supplied.settlement else "")
                    fields += field(locale, "personal_net", money(supplied.personal_net.value)
                                    if supplied and supplied.personal_net else "")
                    fields += _provenance(locale, "" if supplied is None else supplied.provenance)
                    fields += field(locale, "reconciliation",
                                    supplied.reconciliation or "" if supplied else "")
                    body += form(page, active, "sessions", "game", fields, locale)
                body += '</details>'
        fields = select(locale, "status", choices(locale, "open", "finished", "interrupted"),
                        row.status)
        fields += select(locale, "actual_complete", choices(locale, "unknown", "yes"),
                         "yes" if row.actual_block_complete else "unknown")
        fields += f'<p>{t(locale, "net_help")}</p>'
        fields += select(locale, "net_scope", choices(locale, "block", "table_stay"),
                         "block" if row.net_confirmation is None else row.net_confirmation.scope)
        fields += field(locale, "personal_net", "" if row.net_confirmation is None
                        else money(row.net_confirmation.personal_net.value))
        fields += field(locale, "adjustment", "" if row.adjustment is None
                        else money(row.adjustment.amount.value))
        fields += field(locale, "adjustment_provenance", "" if row.adjustment is None
                        else row.adjustment.provenance)
        fields += f'<details><summary>{t(locale, "terms")}</summary>'
        fields += select(locale, "cent_tariff", [("", translate(locale, "accounting.keep_terms")),
            ("1/2", "0.5"), *[(s, s) for s in ("1", "2", "3", "5")]])
        fields += field(locale, "from_position", "1")
        fields += select(locale, "change_kind", choices(locale, "correction", "later"))
        fields += '</details>'
        fields += _provenance(locale, row.provenance)
        body += form(page, active, "sessions", "lifecycle", fields, locale)
        if row.status != "open":
            fields = field(locale, "round_name", required=True)
            fields += select(locale, "continuing_terms", choices(locale, "unknown", "yes"))
            fields += _provenance(locale)
            body += form(page, active, "sessions", "next", fields, locale)
    body += f'<details><summary>{t(locale, "history")}</summary>'
    for saved in page.journal.round_heads:
        fields = (f'<p>{e(saved.context.event_name)}</p><input type="hidden" name="position" '
                  f'value="{saved.context.bindings[0].game_position}">')
        body += form(page, active, "sessions", "open", fields, locale, round_id=saved.identity)
    return body + '</details>'


def render_accounting(app, active, family, locale):
    try:
        with active.capture.lock if family == "matches" else active.lock:
            page = capture_accounting_page(app, active, family)
        body = f'<section class="panel" id="accounting"><h2>{t(locale, "title")}</h2>'
        body += f'<p>{t(locale, "units")}</p>' + _tournament(page, active, family, locale)
        if family == "sessions":
            body += _cent(page, active, locale, app)
        if page.current is not None:
            body += f'<details><summary>{t(locale, "revisions")}</summary>'
            history = (page.journal.rounds if type(page.current) is CentRoundV1
                       else page.journal.tournaments)
            for row in history:
                if row.identity == page.current.identity and row != page.current:
                    body += (_round_summary(row, locale) if type(row) is CentRoundV1
                             else _components(row, locale))
            body += '</details>'
        return body + '</section>'
    except (OSError, ValueError, SkatMindError, StaleFrontendWorkflowRevisionError):
        return (f'<section id="accounting"><h2>{t(locale, "title")}</h2>'
                f'<p role="alert">{t(locale, "unavailable")}</p></section>')
