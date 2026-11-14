"""Bounded ordinary event form fields, independent from global UI preferences."""

from skatmind.event_context_contracts import (
    CENT_RULE,
    TOURNAMENT_RULE,
    AmountV1,
    CheckpointV1,
    EventTermsV1,
    FinancialFactsV1,
    PoolFactV1,
    RuleSourceV1,
)

EVENT_ACTIONS = ("create", "checkpoint", "terms", "attach", "reconfirm", "remove", "freeze")
EVENT_ROUTES = tuple(f"/{family}/event-context/{action}"
                     for family in ("matches", "sessions") for action in EVENT_ACTIONS
                     if family != "matches" or action != "attach")
CHECKPOINT_FIELDS = ("through_position", "personal_points", "own_losses", "provenance")
FINANCIAL_FIELDS = ("currency", "entry_paid", "entry_committed", "table_paid", "table_committed",
    "cent_tariff", "fee_source", "fee_edition", "payout_source", "payout_edition", "prize_facts",
    "prize_completeness", "financial_provenance",
    *(f"pool_{number}_{field}" for number in range(1, 9)
      for field in ("name", "participation", "entitlement")))
TERMS_FIELDS = ("event_mode", "scoring_source", "scoring_edition", *FINANCIAL_FIELDS)
EVENT_FIELDS = {
    "create": ("event_name", "series_name", "game_position", "selected_player", *TERMS_FIELDS,
               *CHECKPOINT_FIELDS),
    "checkpoint": CHECKPOINT_FIELDS,
    "terms": ("event_name", "series_name", "from_position", "change_kind", "provenance",
              *TERMS_FIELDS),
    "attach": ("event_choice", "game_position", "selected_player", "map_1", "map_2", "map_3",
               "provenance"),
    "reconfirm": ("through_position", "provenance", "disagreement"),
    "remove": ("through_position", "provenance"),
    "freeze": ("decision_index",),
}


class EventFormError(ValueError):
    def __init__(self, reason="invalid", field_key=None):
        self.reason, self.field_key = reason, field_key
        super().__init__("Event context form could not be accepted.")


def number(values, name, *, minimum=0, maximum=36):
    value = values.get(name, "")
    try:
        if not value or len(value) > 12 or str(int(value)) != value:
            raise ValueError
        value = int(value)
        if not minimum <= value <= maximum:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise EventFormError("number", name) from None


def _source(values, name, edition, *, optional=False):
    reference, version = values.get(name, "").strip(), values.get(edition, "").strip()
    if optional and not reference and not version:
        return None
    if not reference or not version:
        raise EventFormError("rule_source", name)
    return RuleSourceV1(reference=reference, edition=version)


def parse_event_terms(values, *, from_position):
    amounts = {}
    for name in ("entry_paid", "entry_committed", "table_paid", "table_committed"):
        raw = values.get(name, "").strip()
        try:
            amounts[name] = None if not raw else AmountV1.parse(raw)
        except ValueError:
            raise EventFormError("amount", name) from None
    pools = []
    for index in range(1, 9):
        name = values.get(f"pool_{index}_name", "").strip()
        participation = values.get(f"pool_{index}_participation", "unknown")
        entitlement = values.get(f"pool_{index}_entitlement", "unknown")
        if name:
            pools.append(PoolFactV1(pool_id=name, participation=participation,
                                     entitlement=entitlement))
        elif participation != "unknown" or entitlement != "unknown":
            raise EventFormError("pool", f"pool_{index}_name")
    financial = FinancialFactsV1(**amounts, currency=values.get("currency", "").strip() or None,
        cent_tariff=values.get("cent_tariff", "") or None, pools=tuple(pools),
        fee_source=_source(values, "fee_source", "fee_edition", optional=True),
        payout_source=_source(values, "payout_source", "payout_edition", optional=True),
        prize_facts=values.get("prize_facts", "").strip() or None,
        prize_completeness=values.get("prize_completeness", "unknown"),
        provenance=values.get("financial_provenance", "").strip() or None)
    mode = values.get("event_mode", "")
    return EventTermsV1(from_position=from_position, mode=mode,
        scoring_rule=CENT_RULE if mode == "cent" else TOURNAMENT_RULE,
        scoring_source=_source(values, "scoring_source", "scoring_edition"), financial=financial)


def parse_event_checkpoint(values):
    try:
        return CheckpointV1(through_position=number(values, "through_position"),
            personal_points=number(values, "personal_points", minimum=-10**9, maximum=10**9),
            own_losses=number(values, "own_losses"),
            provenance=values.get("provenance", "").strip())
    except EventFormError:
        raise
    except ValueError:
        raise EventFormError("checkpoint") from None
