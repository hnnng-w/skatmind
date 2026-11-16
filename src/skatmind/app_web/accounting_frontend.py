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
    TournamentAccountingV1,
    accounting_boundary_prefix,
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
    AmountV1,
    EventContextV1,
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
    CENT_ACCOUNTING_RULE,
    CENT_PAIRWISE_RULE,
    STANDARD_RULE,
    STANDARD_SOURCE,
    ObligationV1,
    plus_table_cents,
)

from .accounting_forms import ACCOUNTING_FIELDS, AccountingFormError, optional_amount
from .event_context_forms import LOCAL_SOURCE, actual_platform, resolve_platform, supported_terms
from .event_context_frontend import (
    EventFormConflict,
    _documents,
    capture_event_page,
    checkpoint_review,
    platform_document,
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
        b"mode_accounting_form_v2\0" + canonical_json(scope), hashlib.sha256).hexdigest()
    return AccountingPage(event, journal, current, documents, selection)


def _integer(values, field, minimum=1, maximum=36):
    value = values.get(field, "")
    if not value.isascii() or not value.isdecimal() or not minimum <= int(value) <= maximum:
        raise AccountingFormError("invalid", field)
    return int(value)


def _round_facts(context, documents):
    return tuple(build_recording_facts_v1(document, through_position=1,
        selected_player_id=context.binding(recording_version_v1(document).source)
        .source_selected_player_id) for _, document in documents
        if context.binding(recording_version_v1(document).source) is not None)


def fresh_round(row, documents):
    # Refresh only on an accepted action. Passive rendering labels this as a preview.
    return replace(row, status="open", recordings=_round_facts(row.context, documents),
        rule=CENT_ACCOUNTING_RULE if all(t.platform == "euroskat" for t in row.context.terms)
            else CENT_PAIRWISE_RULE)


def ordinary_round(row, documents):
    """Read-only game arithmetic excludes old monetary overrides and adjustments."""
    return replace(fresh_round(row, documents),
        confirmations=tuple(c for c in row.confirmations if c.status != "external"),
        adjustment=None, net_confirmation=None)


def known_declarer(row, number):
    binding = next((b for b in row.context.bindings if b.game_position == number), None)
    if binding is None:
        return None
    recording = next((r for r in row.recordings if r.source.source == binding.source), None)
    if recording is not None and recording.signatures:
        seat = next((d.value for d in recording.signatures[0].declaration
                     if d.name == "declarer_seat"), None)
        if seat is not None:
            index = ("forehand", "middlehand", "rearhand").index(seat)
            return binding.players[index].event_player_id
    return None


def _start(page, values):
    if page.current is not None:
        raise AccountingFormError("owned")
    document = page.event_page.document
    players, selected = recording_players_v1(document)
    existing = page.event_page.context
    if selected is None:
        selected = (existing.binding(recording_version_v1(document).source)
                    .source_selected_player_id
                    if existing is not None else
                    players[_integer(values, "selected_player", maximum=3) - 1])
    provenance = "Explicit native three-game round start."
    if existing is not None:
        if existing.tournament:
            raise AccountingFormError("owned")
        term = existing.applicable_terms(1)
        platform = resolve_platform(document, values, term)
        context = replace(existing, event_name=values.get("title", "").strip(),
            terms=tuple(supported_terms("cent", platform, from_position=prior.from_position,
                tariff=values.get("cent_tariff") if prior.from_position == 1
                    else prior.financial.cent_tariff) for prior in existing.terms))
    else:
        binding = build_event_binding_v1(document, game_position=1, selected_player_id=selected)
        context = EventContextV1(event_id="round-" + secrets.token_hex(16),
            series_id="block-" + secrets.token_hex(16),
            event_name=values.get("title", "").strip(),
            series_name="Local round 1", participant_ids=players,
            selected_participant_id=selected, bindings=(binding,), provenance=provenance,
            terms=(supported_terms("cent", resolve_platform(document, values),
                tariff=values.get("cent_tariff")),))
    selected_binding = context.binding(recording_version_v1(document).source)
    labels = {selected_binding.player(player.player_id): player.player_label or player.player_id
              for player in document.state.players}
    return CentRoundV1(context=context, table_id="table-" + secrets.token_hex(16),
        participant_labels=tuple(labels.get(player, player) for player in context.participant_ids),
        recordings=_round_facts(context, page.documents), confirmations=(),
        rule_source=context.terms[0].scoring_source, provenance=provenance,
        rule=CENT_ACCOUNTING_RULE if context.terms[0].platform == "euroskat"
            else CENT_PAIRWISE_RULE)


def tournament_preparation(page):
    event = page.event_page
    if event.context is None or not event.context.tournament:
        raise AccountingFormError("context")
    if recording_version_v1(event.document).source.family != "match":
        return event.prepared
    facts = build_recording_facts_v1(event.document, through_position=36)
    through = max((f.position for f in facts.outcomes if f.status != "missing"), default=0)
    through = max(through, max((c.through_position for c in event.context.checkpoints), default=0))
    return checkpoint_review(event, through)


def tournament_values(page):
    row = page.current
    values = {}
    for kind in ("entry", "table"):
        item = None if row is None else next((o for o in row.obligations if o.kind == kind), None)
        if item is not None:
            values[kind + "_total"] = str(item.total.numerator) + "/" + str(item.total.denominator)
    if row is not None and row.plus_level is not None:
        values["plus_level"] = str(row.plus_level)
    return values


def _tournament(page, values):
    event = page.event_page
    prepared = tournament_preparation(page)
    platform = actual_platform(platform_document(event), prepared.terms)
    provenance = "Explicit native cost selection; bank facts excluded."
    plus = (_integer(values, "plus_level", minimum=0, maximum=8)
            if values.get("plus_level") else None)
    table = optional_amount(values, "table_total")
    if platform == "euroskat" and plus is not None:
        from fractions import Fraction

        amount = Fraction(plus_table_cents(plus), 100)
        table = AmountV1(numerator=amount.numerator, denominator=amount.denominator)
    obligations = tuple(ObligationV1(kind=kind, total=amount, paid=None, provenance=provenance)
        for kind, amount in (("entry", optional_amount(values, "entry_total")), ("table", table))
        if amount is not None)
    # The first cumulative anchor starts the additional-fee interval. Later
    # checkpoints update that interval's total, rather than reset its fee base.
    boundary = max(prepared.terms.from_position,
        event.context.checkpoints[0].through_position + 1 if event.context.checkpoints else 1)
    previous = page.current
    if (type(previous) is TournamentAccountingV1 and previous.rule == STANDARD_RULE
            and previous.rule_source == STANDARD_SOURCE
            and prepared.terms.from_position <= previous.rule_from_position
            <= prepared.game_position):
        boundary = previous.rule_from_position
    boundary = min(boundary, prepared.game_position)
    prefix = accounting_boundary_prefix(event.context, prepared, boundary)
    rule_known = platform == "euroskat" and prefix.status == "ready"
    if prefix.status != "ready":
        # Preserve cost entry despite a missing fee boundary. The empty prefix is
        # only a storage basis here; it cannot authorize a historical fee policy.
        boundary = 1
        prefix = accounting_boundary_prefix(event.context, prepared, boundary)
    losses = prefix.own_losses
    return TournamentAccountingV1(context=event.context, preparation=freeze_preparation(prepared),
        rule=STANDARD_RULE if rule_known else "unverified",
        rule_source=STANDARD_SOURCE if platform == "euroskat" else LOCAL_SOURCE,
        rule_from_position=boundary, losses_before=losses, obligations=obligations,
        receipts=(), receipts_complete=False, currency="EUR", provenance=provenance,
        plus_level=plus if platform == "euroskat" else None,
        table_rule="published_plus" if platform == "euroskat" and plus is not None else "supplied")


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
        ids = row.context.participant_ids
        expected = ids[number - 1:] + ids[:number - 1]
        if tuple(p.event_player_id for p in binding.players) != expected:
            raise AccountingFormError("source", "source_choice")
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
            provenance = "Explicit native round action."
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
                if row.status == "open":
                    raise AccountingFormError("confirm")
                bounded_text(values.get("title", "").strip())
                term = row.context.applicable_terms(3)
                term = supported_terms("cent", resolve_platform(page.event_page.document,
                    values, term), tariff=values.get("cent_tariff"))
                opened = _create_round_session(app, row, 1)
                binding = build_event_binding_v1(opened.document, game_position=1)
                count = 1 + sum(r.table_id == row.table_id for r in page.journal.round_heads)
                context = replace(row.context, event_id="round-" + secrets.token_hex(16),
                    series_id="block-" + secrets.token_hex(16), revision=0, change="created",
                    event_name=values.get("title", "").strip(),
                    series_name=f"Local round {count}",
                    bindings=(binding,), terms=(term,),
                    provenance=provenance)
                row = CentRoundV1(context=context, table_id=row.table_id,
                    participant_labels=row.participant_labels,
                    recordings=_round_facts(context, ((opened.path, opened.document),)),
                    confirmations=(), rule_source=term.scoring_source, provenance=provenance,
                    rule=CENT_ACCOUNTING_RULE if term.platform == "euroskat"
                        else CENT_PAIRWISE_RULE,
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
                    status = values.get("game_status")
                    if status not in ("derived", "won", "lost", "passed"):
                        raise AccountingFormError("invalid", "game_status")
                    if status != "derived":
                        declarer = known_declarer(row, number)
                        if status in ("won", "lost") and declarer is None:
                            declarer = row.context.participant_ids[
                                _integer(values, "declarer", maximum=3)-1]
                        confirmations += (ConfirmedGameV1(position=number,
                            status="settled" if status in ("won", "lost") else "passed",
                            provenance="Explicit native game result.",
                            declarer_id=declarer if status != "passed" else None,
                            settlement=_integer(values, "game_value", maximum=50000) * (
                                -2 if status == "lost" else 1) if status != "passed" else None,
                            reconciliation="Explicit native result correction." if any(
                                c.position == number for c in row.confirmations) else None),)
                    old = next((c for c in row.confirmations if c.position == number), None)
                    updated = next((c for c in confirmations if c.position == number), None)
                    if old is not None and updated is not None and replace(updated,
                            reconciliation=old.reconciliation) == old:
                        confirmations = tuple(old if c.position == number else c
                                              for c in confirmations)
                    row = replace(row, confirmations=tuple(sorted(confirmations,
                        key=lambda c: c.position)), provenance=provenance)
                elif action == "lifecycle":
                    # A local lifecycle action must neither clear nor renew retained
                    # external confirmations. Their exact historical basis survives.
                    if values.get("status") == "finished" and any(
                            ordinary_round(row, page.documents).game(n)[0] not in (
                                "settled", "passed") for n in range(1, 4)):
                        raise AccountingFormError("context")
                    row = replace(row, status=values.get("status"), provenance=provenance)
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
