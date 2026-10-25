"""Accepted Match evidence presentation; no preparation, replay or mutation."""

from .compact_card_rendering import card_set_display_order, compact_recorded_card
from .stateful_localization import translated


def saved_hand(game):
    return bool(game and game["declaration"] and game["declaration"]["hand_game"])


def initial_source_editor(game, perspective_player_id):
    """One optional editor from accepted facts only; never a Play prerequisite."""
    if game is None or game["plays"]:
        return None
    if game["perspective_initial_hand"] is None:
        return "perspective_initial_hand"
    if (game["declaration"] is None or saved_hand(game)
            or perspective_player_id != game["declarer_player_id"]):
        return None
    return next((field for field in ("original_skat", "discarded_cards")
                 if game[field] is None), None)


def card_selection_explanation(game, perspective_player_id, next_player_id, scope):
    """Choose finite copy without deriving or filtering any selectable Card."""
    if scope == "exact_legal_cards":
        return "match_evidence.selection.exact"
    if scope != "bounded_observation_candidates":
        return "task.match.scope." + scope
    if next_player_id != perspective_player_id:
        return "match_evidence.selection.opponent"
    if game["perspective_initial_hand"] is None:
        return "match_evidence.selection.initial_hand"
    if (game["declaration"] is not None and not saved_hand(game)
            and game["declarer_player_id"] == next_player_id):
        missing = [field for field in ("original_skat", "discarded_cards") if game[field] is None]
        if missing:
            return "match_evidence.selection." + ("both" if len(missing) == 2 else missing[0])
    return "task.match.scope." + scope


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
