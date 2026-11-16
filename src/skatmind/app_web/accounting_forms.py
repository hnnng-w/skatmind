"""Approved native cost/result inputs, without payment or payout collection."""

from skatmind.event_context_contracts import AmountV1

ACCOUNTING_FIELDS = {
    "save": ("entry_total", "table_total", "plus_level"),
    "start": ("title", "cent_tariff", "platform", "selected_player"),
    "game": ("position", "game_status", "declarer", "game_value"),
    "open": ("position", "source_choice", "map_1", "map_2", "map_3"),
    "lifecycle": ("status",),
    "next": ("title", "cent_tariff", "platform"),
}
ACCOUNTING_ROUTES = ("/matches/accounting/save", "/sessions/accounting/save",
    *(f"/sessions/accounting/{action}" for action in (
        "start", "game", "open", "lifecycle", "next")))


class AccountingFormError(ValueError):
    def __init__(self, reason="invalid", field=None):
        self.reason, self.field_key = reason, field
        super().__init__("Accounting action could not be accepted.")


def optional_amount(values, name):
    value = values.get(name, "").strip()
    try:
        return None if not value else AmountV1.parse(value)
    except ValueError as error:
        raise AccountingFormError("amount", name) from error
