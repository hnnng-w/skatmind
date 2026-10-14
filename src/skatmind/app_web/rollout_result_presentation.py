"""Compact localized terminal aggregates, preserving the core's exact ordering."""

import json

from .render_locale import localized_card_name, message
from .result_presentation import (
    BrowserSafeResultPresentationV1,
    ResultDetailV1,
    ResultSectionV1,
    ResultTableV1,
)
from .rollout_result_numbers import decimal_number, simulation_success


def _card(card):
    return f"{localized_card_name(card)} ({card})"


def _recommendation_items(result, comparison, candidates):
    best = result["recommended_card"]
    actual = comparison["actual_card"]
    status = comparison["status"]
    goal = message("rollout.goal." + result["objective"])
    ties = result["tied_best_cards"]
    group = len(ties) > 1
    comparison_prefix = "rollout.comparison.group_" if group else "rollout.comparison."
    best_values = {} if group else {"best": _card(best)}
    if actual in ties and group:
        items = [message("rollout.comparison.equal_complete_objective")]
    elif status == "equal_complete_objective" and actual == best:
        items = [message("rollout.matches", actual=_card(actual))]
    elif status == "lower_secondary_outcome":
        items = [message(comparison_prefix + "lower_secondary_outcome", actual=_card(actual),
                         **best_values, metric=message(
                             "rollout.metric." + comparison["responsible_metric"]))]
    elif status == "lower_primary_success":
        items = [message(comparison_prefix + "lower_primary_success", actual=_card(actual),
                         **best_values, goal=goal)]
    else:
        items = [message("rollout.comparison.unavailable")]
    if group:
        items.append(message("rollout.tied_best"))
        items.append(message("rollout.display_order"))
    if len(candidates) == 1:
        items.append(message("rollout.only_card"))
    elif comparison["all_primary_success_equal"]:
        row = candidates[best]
        if row["completed_samples"] > 0 and row["local_success_count"] == row["completed_samples"]:
            items.append(message("rollout.all_succeeded", candidates=len(candidates), goal=goal,
                                 samples=row["completed_samples"]))
        else:
            items.append(message("rollout.primary_tie") + " " + simulation_success(
                row["local_success_count"], row["completed_samples"]))
    other = next((card for card in result["ranked_cards"] if card not in ties), None)
    if other is not None:
        # Read the first exact difference in the core's ranking order. Neither
        # display rounding nor canonical card order is an evaluated advantage.
        metrics = ["local_success_count"]
        if result["objective"] == "complete_settlement":
            metrics.append("total_local_game_score")
        metrics.append("total_local_card_point_margin")
        decisive = next((metric for metric in metrics
                         if candidates[best][metric] != candidates[other][metric]), None)
        if decisive is not None:
            if decisive == "total_local_card_point_margin" and len(metrics) == 3:
                decisive = "settlement_margin"
            prefix = "rollout.preference.group_" if group else "rollout.preference."
            items.append(message(prefix + decisive,
                                 **best_values, other=_card(other), goal=goal))
    return tuple(items)


def build_rollout_presentation(execution, document, information_source):
    result = document["whole_game_rollout_result"]
    comparison = document["whole_game_rollout_comparison"]
    complete = result["status"] == "complete"
    objective = message("rollout.objective." + result["objective"])
    derivation = document.get("whole_game_rollout_derivation", {})
    supplements = derivation.get("supplements", {})
    supplemental_caption = (() if not supplements else (message(
        "rollout.manual_inputs", values="; ".join(
            message("rollout.analysis_" + name) + ": " + str(supplements[name])
            for name in ("bid_value", "matadors") if name in supplements)),))
    summary = ResultSectionV1("Summary", paragraphs=(
        message("rollout.heading"),
        *supplemental_caption,
        message("rollout.coverage", completed=result["completed_common_worlds"],
                requested=result["requested_worlds"]),
    ), details=(ResultDetailV1("Comparison objective", objective),))
    items = []
    tables = ()
    actual = comparison["actual_card"]
    recommendation_details = [ResultDetailV1("Played card", _card(actual))]
    if complete:
        candidates = {row["card"]: row for row in result["candidates"]}
        items = _recommendation_items(result, comparison, candidates)
        ties = result["tied_best_cards"]
        if len(ties) > 1 and actual in ties:
            recommendation_details[0] = ResultDetailV1(
                "Played card", message("rollout.played_tied", card=_card(actual)))
        recommendation_details.insert(0, ResultDetailV1(
            "Equally recommended cards" if len(ties) > 1 else "Recommended card",
            ", ".join(_card(card) for card in ties)))
        settlement = result["objective"] == "complete_settlement"
        columns = ["Card", "Simulated settlement success" if settlement
                   else "Sampled party success", "Final local point margin"]
        if settlement:
            columns.append("Mean settlement score")
        rows = []
        for card in result["ranked_cards"]:
            candidate = candidates[card]
            markers = []
            if card in result["tied_best_cards"]:
                markers.append(message("rollout.marker.tied" if len(result["tied_best_cards"]) > 1
                                       else "rollout.marker.recommended"))
            if card == comparison["actual_card"]:
                markers.append(message("rollout.marker.played"))
            row = [_card(card) + (" — " + ", ".join(markers) if markers else ""),
                   simulation_success(candidate["local_success_count"],
                                      candidate["completed_samples"]),
                   decimal_number(candidate["mean_final_local_card_point_margin"])]
            if settlement:
                row.append(decimal_number(candidate["mean_local_game_score"]))
            rows.append(tuple(row))
        tables = (ResultTableV1("Sampled terminal outcomes", tuple(columns), tuple(rows)),)
    else:
        items.append(message("rollout.no_ranking"))
        items.append(message("rollout.reason." + result["stop_reason"]))
    raw = execution.result.to_dict()["document"]
    technical = {"requested_method": "whole_game_rollout", "effective_method": document[
        "recommendation_method_summary"]["effective_method"],
        "result": raw["whole_game_rollout_result"],
        "derivation": raw.get("whole_game_rollout_derivation"),
        "comparison": raw["whole_game_rollout_comparison"]}
    limits = [message("rollout.limits")]
    if result["objective"] == "played_game_goal":
        limits.append(message("rollout.played_goal_limit"))
    limits.append(message("rollout.margin_definition") + " " + message(
        "rollout.party." + result["local_side"]) if result["local_side"] is not None
        else message("rollout.margin_definition"))
    return BrowserSafeResultPresentationV1("position_analysis", (
        summary, ResultSectionV1("Recommendation", items=tuple(items),
                                 details=tuple(recommendation_details)),
        ResultSectionV1("Alternatives", tables=tables),
        ResultSectionV1("Evidence and limits", paragraphs=tuple(limits)),
        ResultSectionV1("Technical details", paragraphs=(
            message("rollout.policy_details", profile=result["policy"]["profile"],
                    version=result["policy"]["version"]), message("rollout.objective_help"),
            message("match_rollout.source" if information_source == "match_decision" else
                    "rollout.supplemented_source" if supplements else
                    "rollout.source" if information_source == "session_checkpoint"
                    else "rollout.supplied_source"),
        ), details=(ResultDetailV1(
            "Whole-game rollout", json.dumps(technical, ensure_ascii=True, sort_keys=True)),)),
    ), warnings=tuple(execution.result.warnings),
        technical_disclosure_label=message("rollout.calculation_details"))
