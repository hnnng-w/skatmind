"""Accepted Match evidence presentation; no preparation, replay or mutation."""

from .compact_card_rendering import card_set_display_order, compact_recorded_card
from .stateful_localization import translated
from .task_first_rendering import paragraph


def saved_hand(game):
    return bool(game and game["declaration"] and game["declaration"]["hand_game"])


def missing_hand_discard_evidence(game):
    """The retained-empty prerequisite, after the other strict Game prerequisites."""
    return (saved_hand(game) and game["declaration"]["bid_value"] is not None
            and len(game["plays"]) == 30 and game["original_skat"] is not None
            and game["discarded_cards"] is None)


def accepted_evidence(locale, game, field, *, player=None):
    cards = game[field]
    label = translated(locale, "match_evidence." + field,
                       **({"player": player} if player is not None else {}))
    if field == "discarded_cards" and saved_hand(game):
        value = translated(locale, "match_evidence.hand_not_applicable")
    elif cards is None:
        value = translated(locale, "match_evidence.absent")
    elif not cards:
        value = translated(locale, "match_evidence.explicit_empty")
    else:
        value = ' '.join(compact_recorded_card(locale, card, show_code=False)
                         for card in card_set_display_order(cards))
    return ('<p id="match-accepted-' + field + '" class="match-accepted-evidence"><strong>'
            + label + ':</strong> ' + value + '</p>')


def hand_evidence_remedy(state, locale):
    if not missing_hand_discard_evidence(state["game"]):
        return ""
    return (paragraph(locale, "match_evidence.historical_missing")
        + '<p><a href="/matches/position/' + str(state["selected_position"])
        + '#match-hand-evidence">' + translated(locale, "match_evidence.open_explicit")
        + '</a></p>')
