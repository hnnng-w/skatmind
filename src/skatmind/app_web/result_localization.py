# ruff: noqa: E501 - Trusted presentation vocabulary is kept as exact entries.
from __future__ import annotations

from .render_locale import message

# These are trusted presentation-field identities, never user-content lookups.
RESULT_LABEL_KEYS = {
    "Summary": "result.summary",
    "Recommendation": "result.recommendation",
    "Alternatives": "result.alternatives",
    "Evidence and limits": "result.evidence",
    "Technical details": "task.technical",
    "Analysis mode": "guided.mode",
    "Contract": "task.field.game_type",
    "Player role": "guided.role",
    "Player seat": "guided.seat",
    "Next player": "result.next_player",
    "Current Trick": "result.current_trick",
    "Completed Tricks": "result.completed_tricks",
    "Legal Cards": "result.legal_cards",
    "Declarer points": "guided.declarer_points",
    "Defender points": "guided.defender_points",
    "Recommended Card": "task.recommendation",
    "Best evaluated Cards": "result.immediate.best_cards",
    "Immediate evaluation": "result.immediate.evaluation",
    "Evaluation": "result.immediate.status",
    "Deterministic representative": "result.immediate.representative",
    "Method": "task.field.recommendation_method",
    "Actual Card": "result.actual_card",
    "Decision quality": "result.decision_quality",
    "Requested method": "result.requested_method",
    "Effective method": "result.effective_method",
    "Fallback used": "result.fallback_used",
    "Fallback method": "result.fallback_method",
    "Search status": "result.search_status",
    "Stop reason": "result.stop_reason",
    "World coverage": "result.world_coverage",
    "Compatible world count": "result.compatible_worlds",
    "Selected worlds": "result.selected_worlds",
    "Completed worlds": "result.completed_worlds",
    "Sampled worlds": "result.sampled_worlds",
    "Unique sampled worlds": "result.unique_worlds",
    "Samples": "task.field.sample_count",
    "Information cutoff mode": "result.cutoff",
    "Skat visibility": "result.skat_visibility",
    "Result status": "result.status",
    "Game": "guided.review.game",
    "Status": "result.status",
    "Players": "result.players",
    "Declarer": "task.field.declarer_player_id",
    "Declaration": "task.field.game_type",
    "Game end": "task.field.game_end_reason",
    "Winner": "result.winner",
    "Result": "result.result",
    "Overbid": "result.overbid",
    "Settlement": "result.settlement",
    "Hand game": "task.field.hand_game",
    "Ouvert": "task.field.ouvert",
    "Schneider announced": "task.field.schneider_announced",
    "Schwarz announced": "task.field.schwarz_announced",
    "Bid value": "task.field.bid_value",
    "Matadors": "task.field.matadors",
    "Immediate review Decisions": "result.immediate_decisions",
    "Immediate Decisions": "result.immediate_decisions",
    "Immediate reviewed Decisions": "result.immediate_assessed",
    "Immediate assessed Decisions": "result.immediate_assessed",
    "Immediate unavailable Decisions": "result.immediate_unavailable",
    "Bounded Search review Decisions": "result.search_decisions",
    "Bounded Search Decisions": "result.search_decisions",
    "Information-set review Decisions": "result.information_decisions",
    "Information-set Decisions": "result.information_decisions",
    "Tactical observations": "task.field.tactical_motif_review",
    "Tactical motif occurrences": "task.learning.count.tactical_motif_occurrence_count",
    "Exact coverage Decisions": "result.exact_decisions",
    "Sampled coverage Decisions": "result.sampled_decisions",
    "No coverage Decisions": "result.no_coverage_decisions",
    "Claim proof status": "result.claim_status",
    "Claim maximum unresolved Tricks": "result.claim_tricks",
    "Card": "validation.field.card",
    "Recommended": "task.recommendation",
    "Rank": "result.rank",
    "Win rate": "result.win_rate",
    "Expected point swing": "result.point_swing",
    "Average trick points": "result.trick_points",
    "Contract success rate": "result.success_rate",
    "Mean side game score": "result.mean_score",
    "Mean card-point margin": "result.mean_margin",
    "Decision": "task.field.decision_index",
    "Trick": "result.trick",
    "Play": "result.play",
    "Player": "task.field.player_id",
    "Actual": "result.actual_card",
    "Review": "result.review",
    "Search": "task.value.bounded_search",
    "Immediate": "task.value.immediate",
    "Information-set": "task.value.information_set_search",
    "PIMC": "result.pimc",
    "Comparison": "result.comparison",
    "Comparison available": "result.comparison_available",
    "Card comparisons in public Result order": "result.table.immediate",
    "Search Candidate comparisons in public Result order": "result.table.search",
    "Immediate review comparisons in chronological Result order": "result.table.review",
    "Bounded Search review comparisons in chronological Result order": "result.table.search_review",
    "Information-set review comparisons in chronological Result order": "result.table.information_review",
    "Search method": "task.field.recommendation_method",
    "Solution claim": "result.technical.solution",
    "Policy claim": "result.technical.policy_claim",
    "Policy consistency": "result.technical.consistency",
    "Controlled policy decisions": "result.technical.controlled_decisions",
    "Maximum remaining Tricks": "result.technical.remaining_tricks",
    "Maximum depth plies": "result.technical.depth",
    "Maximum selected worlds": "result.technical.selected_worlds",
    "Maximum sampled worlds": "result.technical.sampled_worlds",
    "Minimum comparable worlds": "result.technical.comparable_worlds",
    "Timeout milliseconds": "result.technical.timeout",
    "Depth reached": "result.technical.depth_reached",
    "Nodes expanded": "result.technical.nodes",
    "State nodes evaluated": "result.technical.states",
    "Information sets evaluated": "result.technical.information_sets",
    "General fixed policy": "result.technical.general_policy",
    "Left fixed policy": "result.technical.left_policy",
    "Right fixed policy": "result.technical.right_policy",
    "Game end reason": "task.field.game_end_reason",
    "Multi-Step requested Decisions": "result.technical.requested_steps",
    "Multi-Step simulated Decisions": "result.technical.simulated_steps",
    "Multi-Step stop reason": "result.stop_reason",
    "Multi-Step Card Policy": "guided.advanced.local_policy",
    "Policy Comparison requested Decisions": "result.technical.comparison_steps",
    "Recommended comparison Policy": "result.technical.recommended_policy",
    "Public artifacts": "result.technical.artifacts",
    "Public API contract version": "result.technical.api_version",
    "Player IDs": "result.technical.player_ids",
    "Historical schema version": "result.technical.schema_version",
    "Played at": "task.field.played_at",
    "Schneider status": "result.technical.schneider",
    "Schwarz status": "result.technical.schwarz",
    "Game value": "result.technical.game_value",
    "Effective game value": "result.technical.effective_value",
    "Overbid required game value": "result.technical.required_value",
    "Settlement complete": "result.technical.settlement_complete",
    "Settlement score": "result.settlement",
    "Claim proof states evaluated": "result.technical.claim_states",
    "Claim proof terminal states": "result.technical.claim_terminals",
    "Immediate review method": "task.field.immediate_review",
    "Bounded Search review method": "task.field.search_review",
    "Information-set review method": "task.field.information_set_search_review",
    "Replay Coaching method": "task.field.replay_coaching",
    "Information-set Coaching method": "task.field.information_set_replay_coaching",
    "Tactical Review method": "task.field.tactical_motif_review",
    "Game ID": "task.field.game_id",
}


def result_label(label: str) -> str:
    key = RESULT_LABEL_KEYS.get(label)
    if key is not None:
        return message(key)
    for prefix, key in (("Bounded Search", "task.value.bounded_search"),
                        ("Information-set Search", "task.value.information_set_search")):
        for status in ("complete", "partial", "timeout", "unavailable", "not_available"):
            if label == f"{prefix} {status}":
                return message("result.status_count", method=message(key),
                               status=message(f"result.value.{status}"))
    return label


_ENUM_LABELS = frozenset({
    "Analysis mode", "Contract", "Player role", "Player seat", "Next player", "Method",
    "Decision quality", "Requested method", "Effective method", "Fallback method", "Search status",
    "Stop reason", "World coverage", "Information cutoff mode", "Skat visibility", "Result status",
    "Status", "Declaration", "Game end", "Winner", "Result", "Overbid", "Review", "Comparison",
})


def result_value(label: str, value: str) -> str:
    if label == "Evaluation":
        return message(f"result.immediate.{value}")
    if label in {"Players", "Declarer", "Player"}:
        return value
    if value == "Not available":
        return message("status.unavailable")
    if value == "None":
        return message("task.known_empty")
    if value in {"Yes", "No"}:
        return message("common.answer.yes" if value == "Yes" else "common.answer.no")
    if label not in _ENUM_LABELS:
        return value
    from .translation_catalog import load_frontend_translation_catalogs_v1
    catalog = load_frontend_translation_catalogs_v1()["en"]
    for prefix in ("task.value.", "creation.seat.", "result.value."):
        if prefix + value in catalog:
            return message(prefix + value)
    # Exact unrecognized machine values belong to the technical disclosure.
    return message("result.technical_value")
