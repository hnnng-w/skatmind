"""Small native event actions; rule authority follows actual source/platform facts."""

from skatmind.event_context_contracts import (
    CENT_RULE,
    TOURNAMENT_RULE,
    CheckpointV1,
    EventTermsV1,
    FinancialFactsV1,
    RuleSourceV1,
)
from skatmind.mode_accounting import CENT_SOURCE, STANDARD_SOURCE

EVENT_ACTIONS = ("create", "checkpoint", "terms", "attach", "reconfirm", "remove", "freeze")
EVENT_ROUTES = tuple(f"/{family}/event-context/{action}"
                     for family in ("matches", "sessions") for action in EVENT_ACTIONS
                     if family != "matches" or action != "attach")
CHECKPOINT_FIELDS = ("through_position", "personal_points", "own_losses")
EVENT_FIELDS = {
    "create": ("title", "event_mode", "platform", "selected_player"),
    "checkpoint": CHECKPOINT_FIELDS,
    "terms": ("title", "event_mode", "platform"),
    "attach": ("event_choice", "game_position", "selected_player", "map_1", "map_2", "map_3"),
    "reconfirm": ("through_position", "disagreement"),
    "remove": ("through_position",),
    "freeze": ("decision_index",),
}
LOCAL_SOURCE = RuleSourceV1(reference="skatmind:supported-game-rules",
                           edition="Supported fixed-three-player rules v1")
TOURNAMENT_SOURCE = RuleSourceV1(reference="https://www.euroskat.com/turniere/36er-standard",
                                edition="Supported fixed-three-player list scoring v1")


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


def actual_platform(document, terms=None):
    if hasattr(document, "workspace"):
        return {"EuroSkat": "euroskat", "In-person game": "in_person"}.get(
            document.workspace.match_definition.game_platform, "unknown")
    return None if terms is None else terms.platform


def resolve_platform(document, values, terms=None):
    platform = actual_platform(document, terms)
    if platform is not None:
        if values.get("platform", platform) != platform:
            raise EventFormError("invalid", "platform")
        return platform
    if values.get("platform") not in ("euroskat", "in_person"):
        raise EventFormError("invalid", "platform")
    return values["platform"]


def supported_terms(mode, platform, *, from_position=1, tariff=None):
    if mode not in ("tournament", "tournament_cent", "cent"):
        raise EventFormError("invalid", "event_mode")
    source = (CENT_SOURCE if mode == "cent" else TOURNAMENT_SOURCE
              ) if platform == "euroskat" else LOCAL_SOURCE
    if mode == "tournament_cent" and platform == "euroskat":
        tariff = "1/4"
    return EventTermsV1(from_position=from_position, mode=mode,
        scoring_rule=CENT_RULE if mode == "cent" else TOURNAMENT_RULE,
        scoring_source=source, platform=platform, version=2,
        financial=FinancialFactsV1(currency="EUR", cent_tariff=tariff,
            fee_source=(CENT_SOURCE if mode == "cent" else STANDARD_SOURCE)
                if platform == "euroskat" else None,
            provenance="Explicit native platform/mode selection."))


def parse_event_checkpoint(values):
    try:
        return CheckpointV1(through_position=number(values, "through_position"),
            personal_points=number(values, "personal_points", minimum=-10**9, maximum=10**9),
            own_losses=number(values, "own_losses"),
            provenance="Explicit native checkpoint confirmation.")
    except EventFormError:
        raise
    except ValueError:
        raise EventFormError("checkpoint") from None
