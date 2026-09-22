"""Small, passive single-decision explanation over retained public facts only."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from skatmind.bounded_search_result import BOUNDED_SEARCH_STOP_REASONS
from skatmind.deck import get_full_deck
from skatmind.information_set_search_contracts import INFORMATION_SET_SEARCH_STOP_REASONS
from skatmind.information_set_search_workflow import INFORMATION_SET_SEARCH_EFFECTIVE_METHOD
from skatmind.recommendation_workflow import COMPATIBLE_WORLD_MINIMAX_METHOD

from .render_locale import localized_render, message
from .result_immediate import _effective_immediate


def _object(value):
    return value if isinstance(value, Mapping) else {}


def _count(value):
    return value if type(value) is int and value >= 0 else None


@dataclass(frozen=True, slots=True)
class AnalysisExplanation:
    method: str
    objective: str | None
    information: str
    skat: str
    samples: int | None
    search_status: str | None
    stop: str | None
    coverage: str | None
    fallback: bool


def _method(document):
    """Reuse #240 Immediate recognition; reconcile explicit Search routing facts."""
    recommendation = _object(document.get("recommendation"))
    card = recommendation.get("card")
    if _effective_immediate(document):
        rows = document.get("analysis_report")
        if (type(card) is str and isinstance(rows, (list, tuple)) and rows
                and _object(rows[0]).get("card") == card):
            return "immediate"
        if "card" in recommendation and card is None:
            return "none"
        return "unclear"
    summary = _object(document.get("recommendation_method_summary"))
    effective = summary.get("effective_method")
    requested = summary.get("requested_method")
    if effective == "none":
        return "none" if "card" in recommendation and card is None else "unclear"
    if requested not in ("auto", "bounded_search", "information_set_search"):
        return "unclear"
    information_set = requested == "information_set_search"
    expected = INFORMATION_SET_SEARCH_EFFECTIVE_METHOD if information_set else (
        COMPATIBLE_WORLD_MINIMAX_METHOD)
    search = _object(document.get(
        "information_set_search_result" if information_set else "bounded_search_result"))
    other = document.get(
        "bounded_search_result" if information_set else "information_set_search_result")
    if (effective != expected or search.get("search_method") != expected
            or _object(document.get("settings")).get("recommendation_method") != requested
            or summary.get("search_attempted") is not True
            or summary.get("fallback_used") is not False
            or "fallback_method" not in summary or summary["fallback_method"] is not None
            or summary.get("analysis_report_method") != "none"
            or document.get("analysis_report") or other is not None
            or type(card) is not str or search.get("recommended_card") != card
            or search.get("status") not in (
                ("complete",) if information_set else ("complete", "partial", "timeout"))):
        return "unclear"
    if not information_set and (search.get("fallback_used") is not False
                               or search.get("fallback_method") is not None):
        return "unclear"
    return "information_set" if information_set else "minimax"


def _skat(position, policy):
    cards = position.get("skat")
    visibility = policy.get("skat_visibility")
    if not isinstance(cards, (list, tuple)):
        return "unclear"
    if not cards:
        return ("unknown" if visibility == "unknown" else "not_supplied"
                if visibility in ("known_to_declarer", "known_post_game") else "unclear")
    if (len(cards) != 2 or any(type(card) is not str or card not in get_full_deck()
                               for card in cards) or cards[0] == cards[1]):
        return "unclear"
    if policy.get("known_skat_cards_allowed") is not True:
        return "unclear"
    if visibility == "known_to_declarer" and position.get("player_role") == "declarer":
        return "declarer"
    if (visibility == "known_post_game" and policy.get("analysis_mode") == "post_game_review"
            and policy.get("known_post_game_skat_allowed") is True):
        return "post_game"
    return "unclear"


def project_analysis_explanation(document: Mapping[str, object], *, source="supplied"):
    """Source is supplied only by app-owned bindings, never an input mode or form."""
    method = _method(document)
    position = _object(document.get("position"))
    policy = _object(document.get("information_policy_summary"))
    summary = _object(document.get("recommendation_method_summary"))
    requested = summary.get("requested_method")
    search = _object(document.get("information_set_search_result" if requested == (
        "information_set_search") else "bounded_search_result"))
    objective = None
    if method == "immediate":
        if position.get("game_type") == "null":
            role = position.get("player_role")
            objective = "null_" + role if role in ("declarer", "defender") else "unclear"
        elif position.get("game_type") in ("clubs", "spades", "hearts", "diamonds", "grand"):
            objective = "points"
        else:
            objective = "unclear"
    information = source if source in (
        "session_checkpoint", "match_snapshot", "current_position") else (
        "supplied_review" if policy.get("analysis_mode") == "post_game_review" else
        "supplied_current" if policy.get("analysis_mode") == "live_decision" else "supplied")
    stop = search.get("stop_reason")
    if type(stop) is not str or stop not in (
            *BOUNDED_SEARCH_STOP_REASONS, *INFORMATION_SET_SEARCH_STOP_REASONS):
        stop = "unclear" if search else None
    status = search.get("status")
    coverage = search.get("world_coverage")
    return AnalysisExplanation(
        method=method, objective=objective, information=information, skat=_skat(position, policy),
        samples=_count(_object(document.get("settings")).get("sample_count")),
        search_status=status if status in (
            "complete", "partial", "timeout", "unavailable") else None,
        stop=stop, coverage=coverage if coverage in (
            "none", "single_exact_world", "all_compatible_worlds",
            "sampled_compatible_worlds") else None,
        fallback=method == "immediate" and summary.get("fallback_used") is True,
    )


@localized_render
def explanation_rows(explanation: AnalysisExplanation):
    """Localized text tuples shared by the two existing rendering compositions."""
    value = explanation
    method = message("analysis.method." + value.method)
    if value.method in ("immediate", "minimax", "information_set"):
        method += " — " + message("analysis.scope." + value.method)
    recommendation = [("Analysis method", method)]
    if value.objective is not None:
        recommendation.append(("Comparison objective", message(
            "analysis.objective." + value.objective)))
    evidence = []
    if value.fallback:
        evidence.append(("Analysis outcome", message("analysis.fallback")))
    if value.search_status is not None:
        outcome = message("result.value." + value.search_status) + ": " + message(
            "analysis.stop." + (value.stop or "unclear"))
        if value.method == "none":
            outcome += " " + message("analysis.strict_none")
        evidence.append(("Search outcome", outcome))
    if value.method == "immediate":
        count = str(value.samples) if value.samples is not None else message("status.unavailable")
        evidence.append(("Samples per Card", count + ". " + message("analysis.samples")))
        evidence.append(("Metric scope", message("analysis.metrics.immediate")))
    elif value.method in ("minimax", "information_set"):
        evidence.append(("Metric scope", message("analysis.metrics.search")))
    if value.coverage is not None:
        evidence.append(("Search coverage", message("analysis.coverage." + value.coverage)))
    evidence.extend((
        ("Information used", message("analysis.information." + value.information)),
        ("Skat Cards used", message("analysis.skat." + value.skat)),
    ))
    return tuple(recommendation), tuple(evidence)
