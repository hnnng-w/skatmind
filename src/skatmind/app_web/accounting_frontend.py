"""Explicit source-bound monetary actions composed with existing managed Sessions."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass, replace

from skatmind.accounting_state import (
    CentRoundV1,
    ConfirmedGameV1,
    ExternalAdjustmentV1,
    NetConfirmationV1,
    TournamentAccountingV1,
    freeze_preparation,
)
from skatmind.accounting_store import (
    AccountingConflict,
    append_accounting,
    load_accounting,
    save_accounting,
)
from skatmind.automatic_learning_codec import canonical_json
from skatmind.event_context_contracts import (
    CENT_RULE,
    EventContextV1,
    EventTermsV1,
    FinancialFactsV1,
    RuleSourceV1,
    bounded_text,
)
from skatmind.event_context_recording_files import load_event_recording_v1
from skatmind.event_context_sources import (
    build_event_binding_v1,
    build_recording_facts_v1,
    recording_players_v1,
    recording_version_v1,
)
from skatmind.mode_accounting import (
    CENT_SOURCE,
    STANDARD_SOURCE,
    ObligationV1,
    PersonalReceiptV1,
    SignedMoneyV1,
    plus_table_cents,
)

from .accounting_forms import ACCOUNTING_FIELDS, AccountingFormError, obligation, optional_amount
from .event_context_frontend import (
    EventFormConflict,
    _documents,
    capture_event_page,
    checkpoint_review,
)
from .managed_item_discovery import discover_managed_items_v1
from .session_frontend import (
    build_guided_session_players_v1,
    create_guided_session_v1,
    open_guided_session_v1,
)


@dataclass(frozen=True)
class AccountingPage:
    event_page: object
    journal: object
    current: object
    documents: tuple
    selection: str


def capture_accounting_page(app, active, family):
    event = capture_event_page(app, active, family)
    journal = load_accounting(app.managed_home.root)
    current = journal.for_source(recording_version_v1(event.document).source)
    documents = event.documents
    if type(current) is CentRoundV1:
        documents = _documents(app, current.context, active, family, event.document)
    scope = [event.selection, journal.fingerprint,
             [recording_version_v1(doc).to_dict() for _, doc in documents]]
    selection = hmac.new(app.language_context.key,
        b"mode_accounting_form_v1\0" + canonical_json(scope), hashlib.sha256).hexdigest()
    return AccountingPage(event, journal, current, documents, selection)


def _integer(values, field, minimum=1, maximum=36):
    value = values.get(field, "")
    if not value.isascii() or not value.isdecimal() or not minimum <= int(value) <= maximum:
        raise AccountingFormError("invalid", field)
    return int(value)


def _source(values, default):
    return RuleSourceV1(reference=values.get("fee_reference", default.reference).strip(),
                        edition=values.get("fee_edition", default.edition).strip())


def _round_facts(context, documents):
    return tuple(build_recording_facts_v1(document, through_position=1,
        selected_player_id=context.binding(recording_version_v1(document).source)
        .source_selected_player_id) for _, document in documents
        if context.binding(recording_version_v1(document).source) is not None)


def fresh_round(row, documents):
    # Refresh only on an accepted action. Passive rendering labels this as a preview.
    return replace(row, status="open", recordings=_round_facts(row.context, documents))


def _start(page, values):
    if page.current is not None:
        raise AccountingFormError("owned")
    document = page.event_page.document
    players, selected = recording_players_v1(document)
    if selected is None:
        selected = players[_integer(values, "selected_player", maximum=3) - 1]
    if values.get("confirm_terms") != "yes":
        raise AccountingFormError("confirm", "confirm_terms")
    provenance = values.get("provenance", "").strip()
    existing = page.event_page.context
    if existing is not None:
        if existing.tournament:
            raise AccountingFormError("owned")
        context = existing
        if values.get("cent_tariff") != context.applicable_terms(1).financial.cent_tariff:
            raise AccountingFormError("terms")
    else:
        binding = build_event_binding_v1(document, game_position=1, selected_player_id=selected)
        context = EventContextV1(event_id="round-" + secrets.token_hex(16),
            series_id="block-" + secrets.token_hex(16),
            event_name=values.get("round_name", "").strip(),
            series_name=values.get("round_name", "").strip(), participant_ids=players,
            selected_participant_id=selected, bindings=(binding,), provenance=provenance,
            terms=(EventTermsV1(from_position=1, mode="cent", scoring_rule=CENT_RULE,
                scoring_source=CENT_SOURCE, financial=FinancialFactsV1(currency="EUR",
                    cent_tariff=values.get("cent_tariff"), fee_source=_source(values, CENT_SOURCE),
                    provenance=provenance)),))
    selected_binding = context.binding(recording_version_v1(document).source)
    labels = {selected_binding.player(player.player_id): player.player_label or player.player_id
              for player in document.state.players}
    return CentRoundV1(context=context, table_id="table-" + secrets.token_hex(16),
        participant_labels=tuple(labels.get(player, player) for player in context.participant_ids),
        recordings=_round_facts(context, page.documents), confirmations=(),
        rule_source=_source(values, CENT_SOURCE), provenance=provenance)


def _tournament(page, values):
    event = page.event_page
    if event.context is None or not event.context.tournament:
        raise AccountingFormError("context")
    prepared = (checkpoint_review(event, _integer(values, "through_position", minimum=0))
                if recording_version_v1(event.document).source.family == "match"
                else event.prepared)
    legacy = prepared.terms.financial
    if legacy.currency not in (None, "EUR"):
        raise AccountingFormError("amount")
    if values.get("table_rule") == "published_plus":
        proposed = SignedMoneyV1.exact(plus_table_cents(
            _integer(values, "plus_level", minimum=0, maximum=8)))
        from fractions import Fraction

        supplied = optional_amount(values, "table_total")
        expected = proposed.value / 100
        if supplied is not None and Fraction(supplied.numerator, supplied.denominator) != expected:
            raise AccountingFormError("amount", "table_total")
        values = {**values, "table_total": str(expected)}
    obligations = tuple(item for kind in ("entry", "table")
                        if (item := obligation(values, kind, legacy)) is not None)
    earlier = optional_amount(values, "earlier_losses")
    if earlier is not None:
        obligations += (ObligationV1(kind="earlier_losses", total=earlier,
            paid=optional_amount(values, "earlier_paid"), provenance=values["provenance"].strip()),)
    boundary = _integer(values, "rule_from_position", maximum=37)
    checkpoint = next((c for c in event.context.checkpoints
                       if c.through_position == boundary - 1), None)
    losses = 0 if boundary == 1 else checkpoint.own_losses if checkpoint else sum(
        row.contribution(event.context)[1] for row in prepared.basis[:boundary - 1]
        if row.fact.status in ("passed", "settled"))
    receipts = tuple(PersonalReceiptV1(pool=pool, participation=True,
        personal_entitlement=value.numerator > 0, received=value,
        provenance=values.get("provenance", "").strip()) for pool in ("base", "plus", "tandem")
        if (value := optional_amount(values, pool + "_receipt")) is not None)
    return TournamentAccountingV1(context=event.context, preparation=freeze_preparation(prepared),
        rule=values.get("rule", "unverified"), rule_source=_source(values, STANDARD_SOURCE),
        rule_from_position=boundary, losses_before=losses, obligations=obligations,
        receipts=receipts, receipts_complete=values.get("receipts_complete") == "yes",
        currency="EUR", provenance=values.get("provenance", "").strip(),
        plus_level=_integer(values, "plus_level", minimum=0, maximum=8)
            if values.get("plus_level") else None,
        tandem_participation=values.get("tandem_participation", "unknown"),
        table_rule=values.get("table_rule", "supplied"),
        side_settlement=SignedMoneyV1.parse(values["side_settlement"])
            if values.get("side_settlement") else None, status=values.get("status", "open"))


def session_choices(app):
    result = discover_managed_items_v1(app.managed_stateful.root("sessions"),
        family="sessions", generation=1, active_handle=None)
    if result.view.candidate_limit_reached:
        raise EventFormConflict("source")
    return tuple(entry for entry in result.entries if entry.summary.status == "available")


def choice_key(entry):
    document = load_event_recording_v1(entry.path, "session")
    return hashlib.sha256(canonical_json([entry.path.name,
        recording_version_v1(document).to_dict()])).hexdigest()


def _create_round_session(app, row, number):
    ids = row.context.participant_ids
    labels = dict(zip(ids, row.participant_labels, strict=True))
    ordered = ids[number - 1:] + ids[:number - 1]
    values = {f"player_{index}_{field}": value
              for index, player in enumerate(ordered, 1)
              for field, value in (("id", player), ("label", labels[player]))}
    return create_guided_session_v1(app.managed_stateful.root("sessions"),
        handle=secrets.token_hex(32), session_id="cent-session-" + secrets.token_hex(16),
        players=build_guided_session_players_v1(values), capture_mode="live",
        local_player_id=row.context.selected_participant_id)


def _open_position(app, row, number, values):
    binding = next((b for b in row.context.bindings if b.game_position == number), None)
    entries = session_choices(app)
    created = None
    if binding is None:
        bounded_text(values.get("provenance", "").strip())
    if binding is not None:
        matches = [entry for entry in entries if entry.summary.semantic_product_id
                   == binding.source.product_id]
    elif values.get("source_choice") != "new":
        matches = [entry for entry in entries if choice_key(entry) == values.get("source_choice")]
    else:
        created = _create_round_session(app, row, number)
        matches = []
    if created is None:
        if len(matches) != 1:
            raise AccountingFormError("source", "source_choice")
        created = open_guided_session_v1(app.managed_stateful.root("sessions"), matches[0])
    if binding is None:
        players, selected = recording_players_v1(created.document)
        if all(player in row.context.participant_ids for player in players):
            mapping = {player: player for player in players}
        else:
            mapping = {player: row.context.participant_ids[_integer(values, f"map_{index}",
                maximum=3) - 1] for index, player in enumerate(players, 1)}
        selected = selected or next(player for player in players
            if mapping[player] == row.context.selected_participant_id)
        binding = build_event_binding_v1(created.document, game_position=number,
            player_map=mapping, selected_player_id=selected)
        row = replace(row, context=replace(row.context, bindings=row.context.bindings + (binding,)))
    facts = build_recording_facts_v1(created.document, through_position=1,
                                    selected_player_id=binding.source_selected_player_id)
    row = replace(row, recordings=tuple(f for f in row.recordings
                                       if f.source.source != binding.source) + (facts,))
    return row, created


def dispatch_accounting(app, route, values, *, activate_session):
    family, action = route.split("/")[1], route.rsplit("/", 1)[1]
    if set(values) - {"managed_handle", "accounting_selection", "round_id",
                      *ACCOUNTING_FIELDS[action]}:
        raise AccountingFormError()
    managed = app.managed_stateful
    gate = managed.match_lifecycle_lock if family == "matches" else managed.session_lifecycle_lock
    with gate:
        active = managed.active_match if family == "matches" else managed.active_session
        if active is None or values.get("managed_handle") != active.handle:
            raise EventFormConflict()
        with active.capture.lock if family == "matches" else active.lock:
            page = capture_accounting_page(app, active, family)
            selection = values.get("accounting_selection", "")
            if (not re.fullmatch(r"[0-9a-f]{64}", selection)
                    or not hmac.compare_digest(page.selection, selection)):
                raise EventFormConflict()
            row = page.current
            opened = None
            provenance = values.get("provenance", "").strip()
            if action == "save":
                row = _tournament(page, values)
            elif action == "start":
                row = _start(page, values)
            elif action == "open" and values.get("round_id"):
                row = page.journal.head(values["round_id"])
                if type(row) is not CentRoundV1:
                    raise AccountingFormError("source")
                # Navigation to an existing source does not refresh or write an accounting.
                number = _integer(values, "position", maximum=3)
                if not any(b.game_position == number for b in row.context.bindings):
                    raise AccountingFormError("source")
                _, opened = _open_position(app, row, number, values)
                activate_session(opened)
                return "/sessions/current#accounting"
            elif type(row) is not CentRoundV1:
                raise AccountingFormError("context")
            elif action == "next":
                if row.status == "open" or values.get("continuing_terms") != "yes":
                    raise AccountingFormError("confirm")
                bounded_text(values.get("round_name", "").strip())
                bounded_text(provenance)
                opened = _create_round_session(app, row, 1)
                binding = build_event_binding_v1(opened.document, game_position=1)
                context = replace(row.context, event_id="round-" + secrets.token_hex(16),
                    series_id="block-" + secrets.token_hex(16), revision=0, change="created",
                    event_name=values.get("round_name", "").strip(),
                    series_name=values.get("round_name", "").strip(), bindings=(binding,),
                    terms=(replace(row.context.applicable_terms(3), from_position=1),),
                    provenance=provenance)
                row = CentRoundV1(context=context, table_id=row.table_id,
                    participant_labels=row.participant_labels,
                    recordings=_round_facts(context, ((opened.path, opened.document),)),
                    confirmations=(), rule_source=row.rule_source, provenance=provenance,
                    previous_round_id=row.identity)
            else:
                if row.status != "open" and not (
                        action == "lifecycle" and values.get("status") == "open"):
                    raise AccountingFormError("reopen")
                row = fresh_round(row, page.documents)
                if action == "open":
                    row, opened = _open_position(app, row,
                        _integer(values, "position", maximum=3), values)
                elif action == "game":
                    number = _integer(values, "position", maximum=3)
                    if not any(b.game_position == number for b in row.context.bindings):
                        raise AccountingFormError("source")
                    confirmations = tuple(c for c in row.confirmations if c.position != number)
                    if values.get("game_status") != "derived":
                        status = values.get("game_status")
                        confirmations += (ConfirmedGameV1(position=number, status=status,
                            provenance=provenance, declarer_id=(row.context.participant_ids[
                                _integer(values, "declarer", maximum=3)-1]
                                if status == "settled" else None),
                            settlement=int(values.get("settlement", ""))
                                if status == "settled" else None,
                            personal_net=SignedMoneyV1.parse(values.get("personal_net", ""))
                                if status == "external" else None,
                            reconciliation=values.get("reconciliation", "").strip() or None),)
                    old = next((c for c in row.confirmations if c.position == number), None)
                    updated = next((c for c in confirmations if c.position == number), None)
                    if (old is not None and old != updated
                            and not values.get("reconciliation", "").strip()):
                        raise AccountingFormError("reconcile", "reconciliation")
                    row = replace(row, confirmations=tuple(sorted(confirmations,
                        key=lambda c: c.position)), provenance=provenance)
                elif action == "lifecycle":
                    if values.get("cent_tariff"):
                        from skatmind.event_context_operations import set_event_terms_v1

                        boundary = _integer(values, "from_position", maximum=3)
                        term = row.context.applicable_terms(boundary)
                        if values.get("change_kind") not in ("correction", "later"):
                            raise AccountingFormError("terms")
                        term = replace(term, from_position=boundary,
                            financial=replace(term.financial,
                            cent_tariff=values["cent_tariff"], provenance=provenance))
                        context = set_event_terms_v1(row.context, term,
                            expected_revision=row.context.revision,
                            correction=values["change_kind"] == "correction", provenance=provenance)
                        row = replace(row, context=context)
                    row = replace(row, adjustment=ExternalAdjustmentV1(
                        amount=SignedMoneyV1.parse(values["adjustment"]),
                        provenance=values.get("adjustment_provenance", "").strip())
                        if values.get("adjustment") else None)
                    net = None
                    if values.get("personal_net"):
                        scope = values.get("net_scope")
                        coverage = (row.identity,) if scope == "block" else tuple(
                            r.identity for r in page.journal.round_heads
                            if r.table_id == row.table_id)
                        net = NetConfirmationV1(scope=scope, round_ids=coverage,
                            activity_fingerprints=tuple((row if identity == row.identity else
                                page.journal.head(identity)).activity_fingerprint
                                for identity in coverage),
                            personal_net=SignedMoneyV1.parse(values["personal_net"]),
                            provenance=provenance)
                    row = replace(row, status=values.get("status"), provenance=provenance,
                        actual_block_complete=values.get("actual_complete") == "yes",
                        net_confirmation=net)
            journal = append_accounting(page.journal, row)

            def guard():
                return (capture_accounting_page(app, active, family).selection == page.selection
                        and (opened is None or load_event_recording_v1(opened.path, "session")
                             == opened.document))

            try:
                save_accounting(app.managed_home.root, journal,
                    expected_fingerprint=page.journal.fingerprint, source_guard=guard)
            except (AccountingConflict, OSError) as error:
                raise EventFormConflict("save") from error
            if opened is not None:
                activate_session(opened)
    return (f"/matches/position/{active.selected_position}" if family == "matches"
            else "/sessions/current") + "#accounting"
