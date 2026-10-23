"""Private witnesses from rejected evidence and the exact accepted Match source."""

import re
from dataclasses import dataclass

from skatmind.deck import get_full_deck


@dataclass(frozen=True, slots=True)
class MatchEvidenceFeedback:
    selection: str
    operation: str
    card: str
    source: str

    def __post_init__(self):
        if (type(self.selection) is not str
                or re.fullmatch(r"[0-9a-f]{64}", self.selection) is None
                or (self.operation, self.source) not in {
                    ("set_original_skat", "initial_hand"),
                    ("set_perspective_hand", "original_skat")}
                or type(self.card) is not str or self.card not in get_full_deck()):
            raise ValueError("Match evidence feedback requires a bound explicit-source witness.")


def rejected_evidence_witness(active, values):
    """Called after authoritative rejection, never used to accept a candidate."""
    game = active.workspace.slots[active.selected_position - 1].observed_game
    operation = values["operation"]
    if game is None or operation not in {"set_original_skat", "set_perspective_hand"}:
        return None
    source = "initial_hand" if operation == "set_original_skat" else "original_skat"
    accepted = (game.perspective_initial_hand if source == "initial_hand" else game.original_skat)
    cards = values.get("cards", ())
    conflict = next((card for card in get_full_deck()
                     if card in cards and card in (accepted or ())), None)
    return None if conflict is None else MatchEvidenceFeedback(
        values["card_selection"], operation, conflict, source)


def resolve_match_evidence_feedback(active, feedback, locale):
    """Resolve labels only after binding and disk freshness under the Capture lock."""
    from .card_entry_http import CardEntryConflict, _fresh, match_card_binding
    from .stateful_localization import card_name, player_name, text

    if (active is None or active.retired
            or feedback.selection != match_card_binding(active, feedback.operation)):
        return None
    try:
        _fresh(active, session=False)
    except CardEntryConflict:
        return None
    game = active.workspace.slots[active.selected_position - 1].observed_game
    values = {"card": card_name(locale, feedback.card)}
    if feedback.source == "initial_hand":
        values["player"] = player_name(locale, active.workspace.match_definition.participants,
                                       game.perspective_player_id)
    return text(locale, "validation.match_evidence." + feedback.source, **values)
