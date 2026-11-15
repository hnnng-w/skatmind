from fractions import Fraction

import pytest

from skatmind.event_context_contracts import AmountV1
from skatmind.mode_accounting import (
    ObligationV1,
    PersonalReceiptV1,
    SignedMoneyV1,
    additional_loss_fee_cents,
    cent_transfers,
    clarify_legacy_obligation,
    component_totals,
    loss_fee_cents,
    obolus_cents,
    plus_table_cents,
    tournament_components,
)


@pytest.mark.parametrize("losses,expected", [(0, 0), (1, 50), (2, 100), (3, 150),
    (4, 250), (5, 350), (6, 650), (7, 1150), (8, 1650), (36, 15650)])
def test_all_progressive_bands(losses, expected):
    assert loss_fee_cents(losses) == expected
    assert additional_loss_fee_cents(4, 6) == 400


@pytest.mark.parametrize("base,fee", [(99, 3), (100, 3), (101, 4), (Fraction(1, 2), 1)])
def test_individual_game_fee_ceiling(base, fee):
    assert obolus_cents(base) == fee


@pytest.mark.parametrize("tariff", ["1/2", "1", "2", "3", "5"])
@pytest.mark.parametrize("settlement", [23, -46, 99, 100, 101])
def test_pairwise_signed_settlement_and_no_second_loss_doubling(tariff, settlement):
    rows = cent_transfers(("a", "b", "c"), "a", settlement, tariff)
    assert sum(row.gross.value for row in rows) == 0
    assert rows[0].gross.value == 2 * Fraction(tariff) * settlement / 100
    assert rows[1].gross.value == -Fraction(tariff) * settlement / 100
    if settlement < 0:
        assert rows[1].fee is None and rows[2].net is None
        assert "defender_fee_allocation" in rows[1].unresolved
    else:
        assert rows[0].fee.value == Fraction(obolus_cents(
            2 * Fraction(tariff) * settlement), 100)


def test_half_cent_principal_and_known_fee_are_retained_without_balancing():
    rows = cent_transfers(("a", "b", "c"), "a", 23, "1/2")
    assert rows[0].net.value == Fraction(22, 100)
    assert rows[1].gross.value == Fraction(-23, 200)
    assert rows[1].fee.value == 0 and rows[1].net is None
    assert rows[1].unresolved == ("fractional_principal_posting",)
    # Individual-game upward rounding differs from netting a block first.
    assert 3 * obolus_cents(101) == 12 != obolus_cents(303)


@pytest.mark.parametrize("value", [True, 0.5, "NaN", "1e3", "-0.0000001", "1/0"])
def test_strict_money_rejects_nonexact_or_unbounded_input(value):
    with pytest.raises(ValueError):
        SignedMoneyV1.parse(value)


def test_signed_money_does_not_widen_legacy_amount():
    assert SignedMoneyV1.parse("-0.005").value == Fraction(-1, 200)
    with pytest.raises(ValueError):
        AmountV1.parse("-1")
    with pytest.raises(ValueError):
        SignedMoneyV1(numerator=True)
    with pytest.raises(ValueError):
        SignedMoneyV1(numerator=2, denominator=4)


def test_payment_is_not_a_second_expense_and_legacy_overlap_is_explicit():
    paid, committed = AmountV1.parse("2"), AmountV1.parse("5")
    with pytest.raises(ValueError):
        clarify_legacy_obligation("entry", paid, committed, interpretation="", provenance="Receipt")
    total = clarify_legacy_obligation("entry", paid, committed,
        interpretation="committed_is_total", provenance="Receipt clarifies overlap")
    remaining = clarify_legacy_obligation("entry", paid, committed,
        interpretation="committed_is_remaining", provenance="Receipt clarifies remainder")
    assert total.total.numerator == 5 and total.remaining == 3
    assert remaining.total.numerator == 7 and remaining.remaining == 5


def components(*, receipts=(), complete=False, before=4, after=6, rule=True, prior=False):
    return tournament_components(obligations=(
        ObligationV1(kind="entry", total=AmountV1.parse("5"), paid=AmountV1.parse("5"),
                     provenance="Personal receipt"),
        ObligationV1(kind="table", total=AmountV1.parse("1.25"), paid=AmountV1.parse("0.75"),
                     provenance="Confirmed Plus level 2")),
        receipts=receipts, receipts_complete=complete, loss_before=before, loss_after=after,
        rule_confirmed=rule, earlier_losses_known=prior)


def test_component_readiness_zero_receipts_and_personal_tandem():
    partial = components()
    assert component_totals(partial) == (Fraction(-41, 4), None)
    assert next(row for row in partial if row.kind == "additional_losses").value.value == -4
    zero = PersonalReceiptV1(pool="base", participation=True, personal_entitlement=False,
                             received=AmountV1.parse("0"), provenance="Confirmed no receipt")
    assert component_totals(components(receipts=(zero,), complete=True, prior=True)) == (
        Fraction(-41, 4), Fraction(-41, 4))
    personal = PersonalReceiptV1(pool="tandem", participation=True, personal_entitlement=True,
        received=AmountV1.parse("7.5"), provenance="My share only; team total was 15")
    assert component_totals(components(receipts=(personal,), complete=True, prior=True))[1] == (
        Fraction(-11, 4))
    assert component_totals(components(rule=False))[1] is None
    assert plus_table_cents(0) == 75 and plus_table_cents(2) == 125


def test_tournament_cent_is_not_three_game_cent():
    rows = tournament_components(obligations=(), receipts=(), receipts_complete=False,
        loss_before=0, loss_after=0, rule_confirmed=True, earlier_losses_known=True,
        tournament_cent=True)
    assert rows[-1].value is None and rows[-1].reason == "tournament_side_rule_unsupported"
