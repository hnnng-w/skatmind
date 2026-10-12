"""Compact localized terminal aggregates, preserving the core's exact ordering."""

import json

from .render_locale import localized_card_name, message
from .result_presentation import (
    BrowserSafeResultPresentationV1,
    ResultDetailV1,
    ResultSectionV1,
    ResultTableV1,
)


def build_rollout_presentation(execution, document, information_source):
    result = document["whole_game_rollout_result"]
    comparison = document["whole_game_rollout_comparison"]
    complete = result["status"] == "complete"
    objective = message("rollout.objective." + result["objective"])
    summary = ResultSectionV1("Summary", paragraphs=(
        message("rollout.heading"),
        message("rollout.coverage", completed=result["completed_common_worlds"],
                requested=result["requested_worlds"]),
    ), details=(ResultDetailV1("Comparison objective", objective),
                ResultDetailV1("Actual Card", localized_card_name(comparison["actual_card"]))))
    items = []
    tables = ()
    if complete:
        items.append(message("rollout.best", cards=", ".join(
            localized_card_name(card) for card in result["tied_best_cards"])))
        items.append(message("rollout.comparison." + comparison["status"]))
        if comparison["responsible_metric"] is not None:
            items.append(message("rollout.responsible", metric=message(
                "rollout.metric." + comparison["responsible_metric"])))
        if comparison["display_order_only"]:
            items.append(message("rollout.display_order"))
        if comparison["all_primary_success_equal"]:
            items.append(message("rollout.primary_tie"))
        candidates = {row["card"]: row for row in result["candidates"]}
        columns = ["Card", "Evaluation", "Sampled party success", "Final local point margin"]
        if result["objective"] == "complete_settlement":
            columns.append("Mean settlement score")
        rows = []
        for card in result["ranked_cards"]:
            candidate = candidates[card]
            row = [localized_card_name(card),
                   ("equal_best" if len(result["tied_best_cards"]) > 1 else "best")
                   if card in result["tied_best_cards"] else "lower_evaluated",
                   f'{candidate["local_success_count"]}/{candidate["completed_samples"]} '
                   f'({candidate["sampled_local_success_fraction"]:.3f})',
                   f'{candidate["mean_final_local_card_point_margin"]:.2f}']
            if result["objective"] == "complete_settlement":
                row.append(f'{candidate["mean_local_game_score"]:.2f}')
            rows.append(tuple(row))
        tables = (ResultTableV1("Sampled terminal outcomes", tuple(columns), tuple(rows)),)
    else:
        items.append(message("rollout.no_ranking"))
        items.append(message("rollout.reason." + result["stop_reason"]))
    technical = {"requested_method": "whole_game_rollout", "effective_method": document[
        "recommendation_method_summary"]["effective_method"],
        "settings": dict(result["settings"]), "policy": dict(result["policy"]),
        "work": dict(result["work"]), "source_fingerprint": result["source_fingerprint"],
        "derivation": dict(document.get("whole_game_rollout_derivation", {})),
        "comparison": dict(comparison)}
    return BrowserSafeResultPresentationV1("position_analysis", (
        summary, ResultSectionV1("Recommendation", items=tuple(items)),
        ResultSectionV1("Alternatives", tables=tables),
        ResultSectionV1("Evidence and limits", paragraphs=(
            message("rollout.limits"), message("rollout.margin_definition"),
            message("rollout.objective_help"),
            message("rollout.source" if information_source == "session_checkpoint"
                    else "rollout.supplied_source"),
        )),
        ResultSectionV1("Technical details", details=(ResultDetailV1(
            "Whole-game rollout", json.dumps(technical, ensure_ascii=True, sort_keys=True)),)),
    ), warnings=tuple(execution.result.warnings))
