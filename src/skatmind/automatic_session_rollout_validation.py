"""Validate retained native rollout arithmetic and comparison without simulation."""

from .input_loader import build_local_game_state_from_input
from .rules import get_legal_cards
from .whole_game_rollout_contracts import (
    WholeGameRolloutCandidateV1,
    WholeGameRolloutResultV1,
    WholeGameRolloutWorkV1,
)
from .whole_game_rollout_workflow import (
    compare_rollout_actual,
    parse_rollout_settings,
    serialize_rollout_result,
)


def validate_native_rollout(request, result):
    settings = parse_rollout_settings(request["whole_game_rollout_settings"])
    raw = result["whole_game_rollout_result"]
    typed = WholeGameRolloutResultV1(**{
        **{key: raw[key] for key in WholeGameRolloutResultV1.__dataclass_fields__ if key not in {
            "settings", "candidates", "ranked_cards", "tied_best_cards", "work"}},
        "settings": settings,
        "candidates": tuple(WholeGameRolloutCandidateV1(**{
            key: row[key] for key in WholeGameRolloutCandidateV1.__dataclass_fields__})
            for row in raw["candidates"]),
        "ranked_cards": tuple(raw["ranked_cards"]),
        "tied_best_cards": tuple(raw["tied_best_cards"]),
        "work": WholeGameRolloutWorkV1(**raw["work"])})
    state = build_local_game_state_from_input(request)
    legal = get_legal_cards(state.hand, state.current_trick, state.game_type)
    if typed.candidates and {row.card for row in typed.candidates} != set(legal):
        raise ValueError("Native rollout changed its legal candidates.")
    for row in typed.candidates:
        margin = row.total_declarer_points - row.total_defender_points
        if typed.local_side == "defenders":
            margin = -margin
        if row.total_local_card_point_margin != margin:
            raise ValueError("Native rollout changed its party-oriented points.")
    summary = result["recommendation_method_summary"]
    if (raw != serialize_rollout_result(typed) or result["whole_game_rollout_comparison"] !=
            compare_rollout_actual(typed, request["actual_card_played"])
            or result["whole_game_rollout_derivation"] != request["whole_game_rollout_derivation"]
            or result["settings"]["whole_game_rollout_settings"]
            != request["whole_game_rollout_settings"]
            or summary["requested_method"] != "whole_game_rollout"
            or summary["effective_method"] != (
                "whole_game_rollout" if typed.status == "complete" else "none")
            or summary["fallback_used"] or summary["fallback_method"] is not None
            or result["recommendation"]["card"] != typed.recommended_card
            or result.get("opponent_profile_application_summary") is not None):
        raise ValueError("Native rollout changed its aggregates, comparison or method boundary.")
