"""Bounded immutable accounting interpretations over retained source facts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .automatic_learning_codec import Record, canonical_json, decode_json, digest, integer, unique
from .event_context_contracts import EventContextV1, RuleSourceV1, bounded_text
from .event_context_projection import (
    OutcomeFactV1,
    PreparedEventContextV1,
    PreparedEventContextV2,
    RecordingFactsV1,
    _prepare_from_basis,
    bind_recording_facts,
    validate_frozen_context_v1,
)
from .mode_accounting import (
    CENT_ACCOUNTING_RULE,
    CENT_PAIRWISE_RULE,
    STANDARD_RULE,
    ObligationV1,
    PersonalReceiptV1,
    SignedMoneyV1,
    accounting_identity,
    cent_transfers,
    tournament_components,
)


def freeze_preparation(value):
    return canonical_json(value.to_dict()).decode("ascii")


def thaw_preparation(value):
    data = decode_json(value.encode("ascii"))
    kind = {1: PreparedEventContextV1, 2: PreparedEventContextV2}.get(data.get("version"))
    if kind is None:
        raise ValueError("Unsupported retained context preparation.")
    return kind.from_dict(data)


def accounting_boundary_prefix(context, prepared, boundary):
    """Project a fee cutoff from the retained #321 basis, never today's recording.

    This is a prefix calculation, not a new decision/source attachment. Keep the
    original preparation version and its authorized acknowledgement evidence.
    """
    integer(boundary, 1)
    if boundary > prepared.game_position:
        raise ValueError("The fee boundary cannot follow the consumed prefix.")
    return _prepare_from_basis(context, prepared.basis[:boundary - 1],
        target=prepared.target_key, target_source=prepared.target_source,
        game_position=boundary, decision_index=None, actor=None, game_id=None,
        preparation_version=prepared.version,
        acknowledgement_aliases=getattr(prepared, "acknowledgement_aliases", ()))


@dataclass(frozen=True, slots=True, kw_only=True)
class TournamentAccountingV1(Record):
    context: EventContextV1
    preparation: str
    rule: str
    rule_source: RuleSourceV1
    rule_from_position: int
    losses_before: int
    obligations: tuple[ObligationV1, ...]
    receipts: tuple[PersonalReceiptV1, ...]
    receipts_complete: bool
    currency: str
    provenance: str
    plus_level: int | None = None
    table_rule: str = "supplied"
    tandem_participation: str = "unknown"
    side_settlement: SignedMoneyV1 | None = None
    revision: int = 0
    status: str = "open"
    version: int = 1

    def __post_init__(self):
        self.validate()
        if not self.context.tournament or self.rule not in (STANDARD_RULE, "unverified"):
            raise ValueError("Tournament accounting requires its own confirmed rule.")
        if self.currency != "EUR" or self.status not in ("open", "finished"):
            raise ValueError("Unsupported accounting currency or state.")
        integer(self.revision)
        if self.plus_level is not None:
            integer(self.plus_level)
            if self.plus_level > 8:
                raise ValueError("Unsupported Plus participation level.")
        if self.tandem_participation not in ("unknown", "yes", "no"):
            raise ValueError("Tandem participation must be explicit.")
        if self.table_rule not in ("supplied", "published_plus"):
            raise ValueError("Unsupported table obligation rule.")
        if self.table_rule == "published_plus":
            from .mode_accounting import amount, plus_table_cents

            table = next((o for o in self.obligations if o.kind == "table"), None)
            if self.plus_level is None or table is None or (
                    amount(table.total) * 100 != plus_table_cents(self.plus_level)):
                raise ValueError("The confirmed Plus table obligation must match its actual level.")
        integer(self.losses_before)
        integer(self.rule_from_position, 1)
        prepared = self.prepared
        validate_frozen_context_v1(prepared, self.context)
        prefix = accounting_boundary_prefix(self.context, prepared, self.rule_from_position)
        if prefix.established_through != self.rule_from_position - 1:
            raise ValueError("The fee boundary needs established loss-count evidence.")
        if prefix.own_losses != self.losses_before:
            raise ValueError("The fee boundary count differs from its retained evidence.")
        unique(tuple(row.kind for row in self.obligations))
        unique(tuple(row.pool for row in self.receipts))
        if len(self.receipts) > 8 or self.receipts_complete and not self.receipts:
            raise ValueError("Complete receipt coverage needs explicit receipts, including zero.")
        if prepared.terms.mode != "tournament_cent" and self.side_settlement is not None:
            raise ValueError("Side settlement belongs only to the tournament Cent variant.")
        bounded_text(self.provenance)

    @property
    def prepared(self):
        return thaw_preparation(self.preparation)

    @property
    def identity(self):
        return self.context.event_id

    @property
    def components(self):
        prepared = self.prepared
        prefix = accounting_boundary_prefix(self.context, prepared, self.rule_from_position)
        return tournament_components(obligations=self.obligations, receipts=self.receipts,
            receipts_complete=self.receipts_complete, loss_before=self.losses_before,
            loss_after=prepared.own_losses if prepared.status == prefix.status == "ready" else None,
            rule_confirmed=self.rule == STANDARD_RULE,
            earlier_losses_known=self.losses_before == 0,
            tournament_cent=prepared.terms.mode == "tournament_cent",
            side_settlement=self.side_settlement)


@dataclass(frozen=True, slots=True, kw_only=True)
class ConfirmedGameV1(Record):
    position: int
    status: str
    provenance: str
    declarer_id: str | None = None
    settlement: int | None = None
    personal_net: SignedMoneyV1 | None = None
    reconciliation: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        integer(self.position, 1)
        if self.position > 3 or self.status not in ("settled", "passed", "interrupted", "external"):
            raise ValueError("Invalid confirmed Cent position.")
        bounded_text(self.provenance)
        if self.reconciliation is not None:
            bounded_text(self.reconciliation)
        if self.status == "settled":
            bounded_text(self.declarer_id)
            if type(self.settlement) is not int or not 0 < abs(self.settlement) <= 100000:
                raise ValueError("Confirm the actual signed settlement, including loss doubling.")
        elif self.declarer_id is not None or self.settlement is not None:
            raise ValueError("Only settled games have declarer/settlement facts.")
        if (self.personal_net is not None) != (self.status == "external"):
            raise ValueError("External actual monetary results have their own explicit scope.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalAdjustmentV1(Record):
    amount: SignedMoneyV1
    provenance: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.provenance)


@dataclass(frozen=True, slots=True, kw_only=True)
class NetConfirmationV1(Record):
    """Reconciliation of covered activity, never an additive receipt or funding."""

    scope: str
    round_ids: tuple[str, ...]
    activity_fingerprints: tuple[str, ...]
    personal_net: SignedMoneyV1
    provenance: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        unique(self.round_ids)
        if self.scope not in ("block", "table_stay") or not 1 <= len(self.round_ids) <= 128:
            raise ValueError("A net confirmation needs explicit bounded activity coverage.")
        if self.scope == "block" and len(self.round_ids) != 1:
            raise ValueError("A block confirmation covers exactly one round.")
        for value in (*self.round_ids, self.provenance):
            bounded_text(value)
        if len(self.activity_fingerprints) != len(self.round_ids):
            raise ValueError("Each covered round requires its exact retained activity.")
        for value in self.activity_fingerprints:
            digest(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class CentRoundV1(Record):
    context: EventContextV1
    table_id: str
    participant_labels: tuple[str, ...]
    recordings: tuple[RecordingFactsV1, ...]
    confirmations: tuple[ConfirmedGameV1, ...]
    rule_source: RuleSourceV1
    provenance: str
    previous_round_id: str | None = None
    rule: str = CENT_ACCOUNTING_RULE
    currency: str = "EUR"
    status: str = "open"
    actual_block_complete: bool = False
    adjustment: ExternalAdjustmentV1 | None = None
    net_confirmation: NetConfirmationV1 | None = None
    revision: int = 0
    version: int = 1

    def __post_init__(self):
        self.validate()
        if (self.context.tournament or self.rule not in (CENT_ACCOUNTING_RULE, CENT_PAIRWISE_RULE)
                or self.currency != "EUR"):
            raise ValueError("A Cent round requires its distinct exact accounting rule.")
        if any(term.version == 2 and term.platform != "euroskat" for term in self.context.terms
               ) and self.rule == CENT_ACCOUNTING_RULE:
            raise ValueError("EuroSkat fees require an actual EuroSkat platform.")
        if self.status not in ("open", "finished", "interrupted"):
            raise ValueError("Unsupported round lifecycle state.")
        integer(self.revision)
        bounded_text(self.table_id)
        bounded_text(self.provenance)
        if len(self.participant_labels) != 3:
            raise ValueError("Retain exactly three participant labels.")
        for label in self.participant_labels:
            bounded_text(label)
        if self.previous_round_id is not None:
            bounded_text(self.previous_round_id)
        unique(tuple(row.position for row in self.confirmations))
        if any(c.declarer_id not in self.context.participant_ids for c in self.confirmations
               if c.status == "settled"):
            raise ValueError("Confirmed declarer is outside this round.")
        unique(tuple(binding.game_position for binding in self.context.bindings))
        if any(c.position not in tuple(b.game_position for b in self.context.bindings)
               for c in self.confirmations):
            raise ValueError("A confirmed position requires an actual Session binding.")
        if any(self.context.binding(record.source.source) is None for record in self.recordings):
            raise ValueError("Unbound recording facts cannot enter a round.")
        if any(term.financial.cent_tariff is None for term in self.context.terms):
            raise ValueError("Confirm the actual tariff before starting a round.")
        if (self.net_confirmation is not None
                and self.identity not in self.net_confirmation.round_ids):
            raise ValueError("A confirmation must cover its owning round.")
        if self.status == "finished" and any(self.game(number)[0] not in (
                "settled", "passed", "external") for number in range(1, 4)):
            raise ValueError("Finish requires three recorded positions without contradictions.")

    @property
    def identity(self):
        return self.context.event_id

    @property
    def activity_fingerprint(self):
        return accounting_identity("round_activity", {
            "context": self.context.to_dict(),
            "recordings": [row.to_dict() for row in self.recordings],
            "confirmations": [row.to_dict() for row in self.confirmations],
            "adjustment": None if self.adjustment is None else self.adjustment.to_dict(),
        })

    def game(self, number):
        basis = bind_recording_facts(self.context, self.recordings,
                                     through_position=3)[number - 1]
        supplied = next((row for row in self.confirmations if row.position == number), None)
        fact = basis.fact
        if supplied is not None:
            # A genuinely missing source cannot be repaired by a stale confirmation.
            if fact.status in ("source_unavailable", "source_conflict"):
                return fact.status, None, "conflict"
            binding = next(b for b in self.context.bindings if b.game_position == number)
            recording = next((r for r in self.recordings
                              if r.source.source == binding.source), None)
            if recording is not None and recording.signatures:
                signature = recording.signatures[0]
                declaration = {item.name: item.value for item in signature.declaration}
                seat = declaration.get("declarer_seat")
                declared = None if seat is None else binding.players[
                    ("forehand", "middlehand", "rearhand").index(seat)].event_player_id
                if (supplied.status == "passed" and (signature.trace_prefixes or declaration)
                        or supplied.status == "settled" and declared is not None
                        and supplied.declarer_id != declared):
                    return "source_conflict", None, "reconciliation_required"
            contradicts = (supplied.status != "external"
                and fact.status in ("settled", "passed") and (
                supplied.status != fact.status or supplied.status == "settled" and
                (supplied.declarer_id, supplied.settlement) !=
                (fact.declarer_id, fact.settlement_score)))
            if contradicts:
                return "source_conflict", None, "reconciliation_required"
            if supplied.status == "settled":
                fact = OutcomeFactV1(position=number, status="settled",
                    declarer_id=supplied.declarer_id, settlement_score=supplied.settlement,
                    outcome="declarer_win" if supplied.settlement > 0 else "declarer_loss",
                    evidence_fingerprint=accounting_identity("confirmed_outcome",
                                                             supplied.to_dict()))
            else:
                return supplied.status, None, "supplied"
        if fact.status != "settled":
            return fact.status, None, "derived"
        tariff = self.context.applicable_terms(number).financial.cent_tariff
        return "settled", cent_transfers(self.context.participant_ids, fact.declarer_id,
            fact.settlement_score, tariff, provider_fees=self.rule == CENT_ACCOUNTING_RULE
            ), "supplied" if supplied else "derived"

    def personal_totals(self):
        """Known per-game net subtotal and completeness; aggregates reconcile, never add."""
        from fractions import Fraction

        known, complete = Fraction(), True
        for number in range(1, 4):
            status, rows, _ = self.game(number)
            if status == "external":
                known += next(c.personal_net.value for c in self.confirmations
                              if c.position == number)
            elif rows is not None:
                selected = next(r for r in rows
                                if r.player_id == self.context.selected_participant_id)
                if selected.net is None:
                    complete = False
                else:
                    known += selected.net.value
            else:
                complete = False
        if self.adjustment is not None:
            known += self.adjustment.amount.value
        return known, known if complete else None


def revise_accounting(previous, candidate):
    """A repeated interpretation is a no-op; corrections replace the current head once."""
    if previous is None:
        if candidate.revision:
            raise ValueError("First accounting revision must be zero.")
        return candidate
    if type(previous) is not type(candidate) or previous.identity != candidate.identity:
        raise ValueError("Accounting identity cannot change in a revision.")
    candidate = replace(candidate, revision=previous.revision)
    if candidate == previous:
        return previous
    return replace(candidate, revision=previous.revision + 1)
