"""Exact ordinary accounting form fields; transport tokens are never reflected."""

from skatmind.event_context_contracts import AmountV1
from skatmind.mode_accounting import ObligationV1, clarify_legacy_obligation

ACCOUNTING_FIELDS = {
    "save": ("rule", "rule_from_position", "through_position", "fee_reference", "fee_edition",
        "provenance",
        "entry_total", "entry_paid", "entry_overlap", "table_total", "table_paid",
        "table_overlap", "table_rule", "plus_level", "tandem_participation",
        "earlier_losses", "earlier_paid",
        "receipts_complete",
        "base_receipt", "plus_receipt", "tandem_receipt", "side_settlement", "status"),
    "start": ("round_name", "cent_tariff", "selected_player", "provenance",
              "fee_reference", "fee_edition", "confirm_terms"),
    "game": ("position", "game_status", "declarer", "settlement", "personal_net",
             "provenance", "reconciliation"),
    "open": ("position", "source_choice", "map_1", "map_2", "map_3", "provenance"),
    "lifecycle": ("status", "actual_complete", "personal_net", "net_scope",
                  "net_action", "net_provenance",
                  "adjustment", "adjustment_provenance", "provenance", "cent_tariff",
                  "from_position", "change_kind"),
    "next": ("round_name", "continuing_terms", "provenance"),
}
ACCOUNTING_ROUTES = ("/matches/accounting/save", "/sessions/accounting/save",
    *(f"/sessions/accounting/{action}" for action in (
        "start", "game", "open", "lifecycle", "next")))


class AccountingFormError(ValueError):
    def __init__(self, reason="invalid", field=None):
        self.reason, self.field_key = reason, field
        super().__init__("Accounting confirmation could not be accepted.")


def optional_amount(values, name):
    value = values.get(name, "").strip()
    try:
        return None if not value else AmountV1.parse(value)
    except ValueError as error:
        raise AccountingFormError("amount", name) from error


def obligation(values, kind, legacy):
    total = optional_amount(values, kind + "_total")
    paid = optional_amount(values, kind + "_paid")
    old_paid, committed = getattr(legacy, kind + "_paid"), getattr(legacy, kind + "_committed")
    overlap = values.get(kind + "_overlap", "")
    if old_paid is not None or committed is not None:
        if overlap not in ("explicit_total", "committed_is_total", "committed_is_remaining"):
            raise AccountingFormError("overlap", kind + "_overlap")
        if overlap != "explicit_total":
            return clarify_legacy_obligation(kind, old_paid, committed,
                interpretation=overlap, provenance=values.get("provenance", "").strip())
    if total is None:
        if paid is not None:
            raise AccountingFormError("amount", kind + "_total")
        return None
    return ObligationV1(kind=kind, total=total, paid=paid,
                        provenance=values.get("provenance", "").strip())
