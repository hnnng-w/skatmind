"""Private exact monetary components. These are not provider account postings."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from fractions import Fraction

from .automatic_learning_codec import Record, canonical_json, integer, unique
from .event_context_contracts import CENT_TARIFFS, AmountV1, RuleSourceV1, bounded_text

STANDARD_RULE = "euroskat_standard_2026_11_v1"
CENT_ACCOUNTING_RULE = "euroskat_cent_2026_11_v1"
CENT_PAIRWISE_RULE = "cent_pairwise_unverified_fees_v1"
STANDARD_SOURCE = RuleSourceV1(reference="https://www.euroskat.com/turniere/gebuehren",
                               edition="Published wording reviewed 2026-11-15")
CENT_SOURCE = RuleSourceV1(reference="https://www.euroskat.com/spiele/cent-skat",
                           edition="Published wording reviewed 2026-11-15")


def accounting_identity(domain, value):
    return hashlib.sha256(b"skatmind\0mode_accounting_v1\0" + domain.encode("ascii")
                          + b"\0" + canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class SignedMoneyV1(Record):
    """Reduced signed rational in currency units; AmountV1 stays nonnegative."""

    numerator: int
    denominator: int = 1
    version: int = 1

    def __post_init__(self):
        self.validate()
        integer(self.denominator, 1)
        if abs(self.numerator) > 10**12 or self.denominator > 10**6:
            raise ValueError("Money exceeds its private bound.")
        if (self.value.numerator, self.value.denominator) != (self.numerator, self.denominator):
            raise ValueError("Money must be a reduced exact fraction.")

    @property
    def value(self):
        return Fraction(self.numerator, self.denominator)

    @classmethod
    def exact(cls, value):
        if type(value) not in (int, Fraction):
            raise ValueError("Exact money cannot consume floats or Boolean values.")
        value = Fraction(value)
        return cls(numerator=value.numerator, denominator=value.denominator)

    @classmethod
    def parse(cls, value):
        if type(value) is not str or not re.fullmatch(
                r"-?[0-9]{1,12}(?:\.[0-9]{1,6}|/[1-9][0-9]{0,5})?", value):
            raise ValueError("Use an exact signed decimal or rational amount.")
        return cls.exact(Fraction(value))


def amount(value):
    return None if value is None else Fraction(value.numerator, value.denominator)


def loss_fee_cents(losses):
    integer(losses)
    if losses > 36:
        raise ValueError("The bounded list has at most 36 own losses.")
    return (50 * min(losses, 3) + 100 * min(max(losses - 3, 0), 2)
            + 300 * (losses >= 6) + 500 * max(losses - 6, 0))


def additional_loss_fee_cents(before, after):
    integer(before)
    integer(after, before)
    return loss_fee_cents(after) - loss_fee_cents(before)


def plus_table_cents(level):
    integer(level)
    if level > 8:
        raise ValueError("Unsupported bounded Plus selection.")
    return 75 + 25 * level


def obolus_cents(positive_base):
    if type(positive_base) not in (int, Fraction) or positive_base <= 0:
        raise ValueError("Obolus requires an established positive individual winning base.")
    value = Fraction(positive_base) * Fraction(3, 100)
    return -(-value.numerator // value.denominator)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObligationV1(Record):
    kind: str
    total: AmountV1
    paid: AmountV1 | None
    provenance: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.kind not in ("entry", "table", "earlier_losses"):
            raise ValueError("Unsupported personal obligation.")
        bounded_text(self.provenance)
        if self.paid is not None and amount(self.paid) > amount(self.total):
            raise ValueError("Payment against an obligation cannot exceed that obligation.")

    @property
    def remaining(self):
        return None if self.paid is None else amount(self.total) - amount(self.paid)


def clarify_legacy_obligation(kind, paid, committed, *, interpretation, provenance):
    """An explicit confirmation decides overlap; never reinterpret old facts in place."""
    if interpretation not in ("committed_is_total", "committed_is_remaining"):
        raise ValueError("Clarify whether committed is the total or the unpaid remainder.")
    if committed is None:
        raise ValueError("Unknown total requires an explicit total obligation.")
    total = amount(committed)
    if interpretation == "committed_is_remaining":
        if paid is None:
            raise ValueError("Unknown payment cannot be added as zero.")
        total += amount(paid)
    return ObligationV1(kind=kind, total=AmountV1(numerator=total.numerator,
        denominator=total.denominator), paid=paid, provenance=provenance)


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonalReceiptV1(Record):
    pool: str
    participation: bool
    personal_entitlement: bool
    received: AmountV1 | None
    provenance: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.pool, 120)
        bounded_text(self.provenance)
        if self.received is not None and amount(self.received) > 0 and not (
                self.participation and self.personal_entitlement):
            raise ValueError("A receipt requires confirmed personal participation and entitlement.")


@dataclass(frozen=True, slots=True, kw_only=True)
class MoneyComponentV1(Record):
    kind: str
    value: SignedMoneyV1 | None
    reason: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.kind)
        bounded_text(self.reason)


@dataclass(frozen=True, slots=True, kw_only=True)
class CentPlayerV1(Record):
    player_id: str
    gross: SignedMoneyV1
    fee: SignedMoneyV1 | None
    net: SignedMoneyV1 | None
    unresolved: tuple[str, ...]
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.player_id)


def cent_transfers(players, declarer, settlement, tariff, *, provider_fees=True):
    """Loss doubling is already in settlement. Do not call the tournament scorer."""
    unique(players)
    if len(players) != 3 or declarer not in players or tariff not in CENT_TARIFFS:
        raise ValueError("An exact three-player Cent game and supported tariff are required.")
    if type(settlement) is not int or settlement == 0 or abs(settlement) > 100000:
        raise ValueError("An established nonzero signed settlement is required.")
    rows = []
    for player in players:
        cents = Fraction(tariff) * settlement * (2 if player == declarer else -1)
        gaps = []
        # Current evidence establishes the winning declarer's individual fee base.
        # Winning defenders' allocation/rounding remains a separate provider gap.
        fee = None if not provider_fees else Fraction(0) if cents < 0 else (
            Fraction(obolus_cents(cents), 100) if player == declarer else None)
        if fee is None:
            gaps.append("defender_fee_allocation" if provider_fees else "local_fees_unknown")
        if provider_fees and cents.denominator != 1:
            gaps.append("fractional_principal_posting")
        gross = SignedMoneyV1.exact(cents / 100)
        rows.append(CentPlayerV1(player_id=player, gross=gross,
            fee=None if fee is None else SignedMoneyV1.exact(fee),
            net=None if gaps else SignedMoneyV1.exact(gross.value - fee),
            unresolved=tuple(gaps)))
    return tuple(rows)


def tournament_components(*, obligations, receipts, receipts_complete, loss_before,
                          loss_after, rule_confirmed, earlier_losses_known,
                          side_settlement=None, tournament_cent=False):
    """Known components remain useful independently of missing prize/fee components."""
    result = []
    for kind in ("entry", "table"):
        item = next((row for row in obligations if row.kind == kind), None)
        result.append(MoneyComponentV1(kind=kind,
            value=None if item is None else SignedMoneyV1.exact(-amount(item.total)),
            reason="confirmed_obligation" if item else "unknown_obligation"))
    earlier = next((row for row in obligations if row.kind == "earlier_losses"), None)
    result.append(MoneyComponentV1(kind="earlier_losses", value=(
        SignedMoneyV1.exact(-amount(earlier.total)) if earlier else
        SignedMoneyV1.exact(0) if earlier_losses_known else None),
        reason="confirmed_earlier_cost" if earlier else "earlier_rate_not_established"))
    known = rule_confirmed and loss_before is not None and loss_after is not None
    result.append(MoneyComponentV1(kind="additional_losses", value=SignedMoneyV1.exact(
        -Fraction(additional_loss_fee_cents(loss_before, loss_after), 100)) if known else None,
        reason="confirmed_standard_rule" if known else "loss_rule_or_counter_unknown"))
    for receipt in receipts:
        result.append(MoneyComponentV1(kind="receipt:" + receipt.pool,
            value=None if receipt.received is None else
                SignedMoneyV1.exact(amount(receipt.received)),
            reason="personal_receipt" if receipt.received else "personal_receipt_unknown"))
    if not receipts_complete:
        result.append(MoneyComponentV1(kind="other_receipts", value=None,
                                      reason="receipt_coverage_unknown"))
    if tournament_cent:
        result.append(MoneyComponentV1(kind="tournament_side_settlement", value=side_settlement,
            reason="confirmed_side_result" if side_settlement is not None else
                   "tournament_side_rule_unsupported"))
    return tuple(result)


def component_totals(components):
    known = sum((row.value.value for row in components if row.value is not None), Fraction())
    return known, known if all(row.value is not None for row in components) else None
