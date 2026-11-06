"""Validate retained native rollout arithmetic and comparison without simulation."""

from dataclasses import asdict

from .bounded_search_information import build_live_search_information_view
from .game_continuation import resolve_game_continuation
from .input_loader import build_local_game_state_from_input, get_game_continuation_from_input
from .ouvert_simulation import (
    build_declared_ouvert_public_hand_constraint,
    resolve_effective_public_hand_constraints,
)
from .rollout_derivation import rollout_source_fingerprint
from .rules import get_legal_cards
from .whole_game_rollout_contracts import (
    WholeGameRolloutCandidateV1,
    WholeGameRolloutResultV1,
    WholeGameRolloutWorkV1,
)
from .whole_game_rollout_workflow import (
    compare_rollout_actual,
    parse_rollout_settings,
    rollout_declaration,
    serialize_rollout_result,
    unavailable_rollout_root,
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
    declaration = rollout_declaration(request)
    continuation = get_game_continuation_from_input(request)
    continuation = (None if continuation is None else
                    resolve_game_continuation(request, continuation))
    public = resolve_effective_public_hand_constraints(tuple(value for value in (
        build_declared_ouvert_public_hand_constraint(request),
        None if continuation is None else continuation.public_hand_constraint)
        if value is not None))
    arguments = dict(state=state, declaration=declaration, left_hand_size=request["left_hand_size"],
                     right_hand_size=request["right_hand_size"], public_hand_constraints=public)
    unprepared = unavailable_rollout_root(**arguments, settings=settings)
    if unprepared is None:
        view = build_live_search_information_view(**arguments,
                                                  skat_visibility=request["skat_visibility"])
        expected_fingerprint = rollout_source_fingerprint(
            "skatmind.whole_game_rollout.source.v1", asdict(view))
        source, cutoff, game_type, side = (view.source, view.information_cutoff,
                                          view.game_type, view.local_side)
    else:
        expected_fingerprint = unprepared.source_fingerprint
        source, cutoff, game_type, side = (unprepared.source, unprepared.information_cutoff,
                                          unprepared.game_type, unprepared.local_side)
        if (typed.status, typed.stop_reason) != (unprepared.status, unprepared.stop_reason):
            raise ValueError("Native rollout changed its unavailable preparation outcome.")
    if (typed.source_fingerprint != expected_fingerprint
            or (typed.source, typed.information_cutoff, typed.game_type, typed.local_side)
            != (source, cutoff, game_type, side)):
        raise ValueError("Native rollout changed its authoritative core source identity.")
    expected_position = asdict(state)
    if any(key not in expected_position or value != expected_position[key]
           for key, value in result["position"].items()):
        raise ValueError("Native rollout changed its prepared Position facts.")
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
