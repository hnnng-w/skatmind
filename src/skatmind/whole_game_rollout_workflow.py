"""Strict flat-review transport adaptation for the versioned rollout core."""

import hashlib
import json
import re
from dataclasses import asdict

from skatmind.game_declaration import (
    GameDeclaration,
    get_nested_game_declaration_data,
    resolve_boolean_declaration_value,
    resolve_nullable_declaration_value,
)
from skatmind.whole_game_rollout_contracts import (
    ROLLOUT_POLICY,
    ROLLOUT_POLICY_VERSION,
    WholeGameRolloutResultV1,
    WholeGameRolloutSettingsV1,
    WholeGameRolloutWorkV1,
)

WHOLE_GAME_ROLLOUT_METHOD = "whole_game_rollout"
PUBLIC_ROLLOUT_TIMEOUT_MS = 30_000
ROLLOUT_SETTING_KEYS = frozenset((*WholeGameRolloutSettingsV1.__dataclass_fields__,
                                "policy_profile", "policy_version"))


def serialize_rollout_settings(settings: WholeGameRolloutSettingsV1) -> dict:
    return {**asdict(settings), "policy_profile": ROLLOUT_POLICY,
            "policy_version": ROLLOUT_POLICY_VERSION}


def parse_rollout_settings(value: object) -> WholeGameRolloutSettingsV1:
    if type(value) is not dict or set(value) != ROLLOUT_SETTING_KEYS:
        raise ValueError("whole_game_rollout_settings requires exactly the documented settings.")
    if value["policy_profile"] != ROLLOUT_POLICY or (
        type(value["policy_version"]) is not int
        or value["policy_version"] != ROLLOUT_POLICY_VERSION
    ):
        raise ValueError("Only side_aware_baseline policy version 1 is supported.")
    timeout = value["wall_clock_timeout_ms"]
    if type(timeout) is not int or not 1 <= timeout <= 60_000:
        raise ValueError("Public rollout timeout must be an integer in [1, 60000].")
    return WholeGameRolloutSettingsV1(**{
        key: value[key] for key in WholeGameRolloutSettingsV1.__dataclass_fields__
    })


def validate_rollout_derivation(value: object, data: dict | None = None) -> None:
    from skatmind.match_rollout_review import (
        MATCH_ROLLOUT_POLICY,
        validate_match_rollout_derivation_v1,
    )
    from skatmind.rollout_derivation import (
        MANUAL_SETTLEMENT_POLICY,
        validate_manual_rollout_derivation,
    )

    if type(value) is dict and value.get("policy") == MATCH_ROLLOUT_POLICY:
        validate_match_rollout_derivation_v1(value, data)
        return
    keys = {"version", "policy", "original_request_fingerprint", "checkpoint_fingerprint",
            "source_revision", "checkpoint_decision_index"}
    manual = type(value) is dict and value.get("policy") == MANUAL_SETTLEMENT_POLICY
    if manual:
        keys.update(("original_request", "supplement_origin", "supplements",
                     "effective_declaration"))
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Rollout derivation must contain exactly its bounded source references.")
    if type(value["version"]) is not int or value["version"] != (2 if manual else 1) or (
        not manual and value["policy"] != "frozen_checkpoint_method_settings_only"
    ):
        raise ValueError("Unsupported rollout derivation version or policy.")
    for name in ("original_request_fingerprint", "checkpoint_fingerprint"):
        if type(value[name]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[name]) is None:
            raise ValueError("Rollout source references must be SHA-256 fingerprints.")
    if type(value["source_revision"]) is not int or value["source_revision"] < 0 or (
        type(value["checkpoint_decision_index"]) is not int
        or not 1 <= value["checkpoint_decision_index"] <= 30
    ):
        raise ValueError("Invalid rollout checkpoint identity.")
    if manual:
        if data is None:
            raise ValueError("Manual derivation validation requires the effective Request.")
        validate_manual_rollout_derivation(value, data)


def unavailable_rollout_root(*, state, declaration, left_hand_size, right_hand_size,
                             public_hand_constraints, settings):
    """Report missing safe-view prerequisites without inventing an attributed prefix."""
    remaining = max(len(state.hand), left_hand_size, right_hand_size)
    reason = None
    if state.played_cards or state.declarer_points or state.defender_points or (
        len(state.completed_tricks) + remaining != 10
        or any("players" not in trick for trick in state.completed_tricks)
    ):
        reason = "incomplete_public_history"
    elif declaration.ouvert and not any(
        constraint.player == state.declarer_player for constraint in public_hand_constraints
    ):
        reason = "missing_public_declarer_hand"
    if reason is None:
        return None
    facts = {"state": asdict(state), "declaration": asdict(declaration),
             "left_hand_size": left_hand_size, "right_hand_size": right_hand_size,
             "public_hand_constraints": [asdict(item) for item in public_hand_constraints]}
    fingerprint = hashlib.sha256(b"skatmind.rollout.unprepared_source.v1\0" + json.dumps(
        facts, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return WholeGameRolloutResultV1(
        settings, "flat_decision_input", "current_decision", fingerprint, state.game_type,
        "declarer" if state.declarer_player == "me" else "defenders"
        if state.declarer_player in ("left", "right") else None,
        remaining, "unavailable", reason, None, 0, 0, (), (), (), None, WholeGameRolloutWorkV1(),
    )


def rollout_declaration(data: dict) -> GameDeclaration:
    """Normalize declarations without inferring an absent bid or matador value."""
    nested = get_nested_game_declaration_data(data)
    return GameDeclaration(
        game_type=data["game_type"],
        **{name: resolve_boolean_declaration_value(data, nested, name) for name in (
            "hand_game", "ouvert", "schneider_announced", "schwarz_announced")},
        **{name: resolve_nullable_declaration_value(data, nested, name)
           for name in ("matadors", "bid_value")},
    )


def serialize_rollout_result(result: WholeGameRolloutResultV1) -> dict:
    document = result.to_dict()
    document["settings"] = serialize_rollout_settings(result.settings)
    document["limitations"].remove("internal_only_pending_recorded_review_integration")
    return document


def compare_rollout_actual(result: WholeGameRolloutResultV1, actual_card: str) -> dict:
    """Attach observed behavior only after the complete candidate evaluation."""
    comparison = {
        "actual_card": actual_card,
        "status": "unavailable",
        "responsible_metric": None,
        "best_card": result.recommended_card,
        "all_primary_success_equal": None,
        "display_order_only": False,
        "primary_success_count_gap": None,
        "total_local_game_score_gap": None,
        "total_local_card_point_margin_gap": None,
    }
    if result.status != "complete":
        return comparison
    candidates = {item.card: item for item in result.candidates}
    if actual_card not in candidates:
        raise ValueError("Actual card must be a legal rollout candidate.")
    actual = candidates[actual_card]
    best = candidates[result.recommended_card]
    comparison.update(
        all_primary_success_equal=len({c.local_success_count for c in result.candidates}) == 1,
        primary_success_count_gap=best.local_success_count - actual.local_success_count,
        total_local_game_score_gap=(None if best.total_local_game_score is None else
                                   best.total_local_game_score - actual.total_local_game_score),
        total_local_card_point_margin_gap=(best.total_local_card_point_margin
                                          - actual.total_local_card_point_margin),
    )
    if actual.comparison_key() == best.comparison_key():
        comparison.update(status="equal_complete_objective",
                          display_order_only=actual.card != best.card)
    elif actual.local_success_count != best.local_success_count:
        comparison.update(status="lower_primary_success", responsible_metric="local_success_count")
    else:
        comparison.update(status="lower_secondary_outcome", responsible_metric=(
            "total_local_game_score" if actual.total_local_game_score != best.total_local_game_score
            else "total_local_card_point_margin"))
    return comparison
