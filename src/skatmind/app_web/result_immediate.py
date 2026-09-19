"""Fail-closed private projection of retained effective-Immediate candidate evidence."""

from collections.abc import Mapping
from math import isfinite

from skatmind.deck import get_full_deck
from skatmind.objective_utility import (
    get_best_cards_by_expected_objective,
    sort_cards_by_expected_objective,
)

_IMMEDIATE = "immediate_expected_value"


def _effective_immediate(document: Mapping[str, object]) -> bool:
    settings = document.get("settings")
    if not isinstance(settings, Mapping):
        return False
    bounded = document.get("bounded_search_result")
    if document.get("information_set_search_result") is not None:
        return False
    if "recommendation_method_summary" not in document:
        return "recommendation_method" not in settings and bounded is None
    method = document["recommendation_method_summary"]
    if not isinstance(method, Mapping):
        return False
    requested = method.get("requested_method")
    if requested not in (_IMMEDIATE, "auto") or settings.get("recommendation_method") != requested:
        return False
    fallback = requested == "auto"
    expected = {
        "requested_method": requested, "effective_method": _IMMEDIATE,
        "analysis_report_method": _IMMEDIATE, "search_attempted": fallback,
        "fallback_used": fallback, "fallback_method": _IMMEDIATE if fallback else None,
    }
    if any(key not in method or type(method[key]) is not type(value) or method[key] != value
           for key, value in expected.items()):
        return False
    if not fallback:
        return bounded is None
    return (
        isinstance(bounded, Mapping)
        and bounded.get("status") in ("partial", "timeout", "unavailable")
        and "recommended_card" in bounded and bounded["recommended_card"] is None
        and bounded.get("fallback_used") is True
        and bounded.get("fallback_method") == _IMMEDIATE
    )


def retained_immediate_best_cards(document: Mapping[str, object]) -> tuple[str, ...]:
    """Returns exact maxima only with complete, consistent method/candidate evidence.

    This is a defensive display guard, not a public input validator. It reads no
    recording, recomputes no simulation, and changes no retained value or rank.
    """
    if not _effective_immediate(document):
        return ()
    position = document.get("position")
    recommendation = document.get("recommendation")
    rows = document.get("analysis_report")
    legal = document.get("legal_cards")
    if (not isinstance(position, Mapping) or not isinstance(recommendation, Mapping)
            or not isinstance(rows, (list, tuple)) or not rows
            or not isinstance(legal, (list, tuple))):
        return ()
    game, role = position.get("game_type"), position.get("player_role")
    if game not in ("clubs", "spades", "hearts", "diamonds", "grand", "null"):
        return ()
    if role not in ("declarer", "defender", "unknown") or (game == "null" and role == "unknown"):
        return ()
    declaration = document.get("game_declaration")
    if isinstance(declaration, Mapping) and declaration.get("game_type") != game:
        return ()
    deck = get_full_deck()
    if any(type(card) is not str or card not in deck for card in legal):
        return ()
    if len(set(legal)) != len(legal) or len(rows) != len(legal):
        return ()
    values = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return ()
        card = row.get("card")
        if type(card) is not str or card not in legal or card in values:
            return ()
        if row.get("is_recommended") is not (index == 0):
            return ()
        for key in ("win_rate", "average_trick_points", "average_points_won",
                    "average_points_lost", "expected_point_swing"):
            value = row.get(key)
            if type(value) not in (int, float) or not isfinite(value):
                return ()
        if (not 0 <= row["win_rate"] <= 1
                or any(row[key] < 0 for key in (
                    "average_trick_points", "average_points_won", "average_points_lost"))
                or row["expected_point_swing"] != (
                    float(row["average_points_won"]) - float(row["average_points_lost"]))
                or "expected_objective_utility" in row):
            return ()
        values[card] = row
    if recommendation.get("card") != rows[0]["card"]:
        return ()
    if list(values) != sort_cards_by_expected_objective(list(values), values, game, role):
        return ()
    return get_best_cards_by_expected_objective(values, game, role)
