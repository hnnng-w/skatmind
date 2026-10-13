"""Exact, analysis-only settlement supplementation of a retained decision Request."""

import copy
import hashlib
import json

from skatmind.game_declaration import (
    SUIT_GAME_TYPES,
    build_serializable_game_declaration,
    validate_bid_value,
    validate_matadors,
)
from skatmind.whole_game_rollout_workflow import rollout_declaration, serialize_rollout_settings

MANUAL_SETTLEMENT_POLICY = "frozen_checkpoint_with_manual_settlement_inputs"
SETTLEMENT_INPUTS = ("bid_value", "matadors")


def rollout_source_fingerprint(domain: str, value: dict) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\0" + json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")).hexdigest()


def missing_rollout_settlement_inputs(root):
    declaration = rollout_declaration(root)
    if declaration.game_type not in (*SUIT_GAME_TYPES, "grand"):
        return ()
    return tuple(name for name in SETTLEMENT_INPUTS if getattr(declaration, name) is None)


def apply_rollout_settlement_supplements(root, supplements):
    """Validate only absent values; return a fresh root without enriching other facts."""
    if type(supplements) is not dict or not set(supplements) <= set(
        missing_rollout_settlement_inputs(root)
    ):
        raise ValueError("Only originally missing settlement inputs may be supplemented.")
    declaration = rollout_declaration(root)
    for name, value in supplements.items():
        if type(value) is not int:
            raise ValueError("Settlement supplements must be explicit integers.")
        if name == "bid_value":
            validate_bid_value(value)
        else:
            validate_matadors(value, declaration.game_type)
    derived = copy.deepcopy(root)
    if supplements:
        derived.setdefault("game_declaration", {}).update(supplements)
        for name, value in supplements.items():
            if name in derived:
                derived[name] = value
    return derived


def rollout_analysis_root(original, actual_card, settings, supplements):
    if supplements and settings.objective != "complete_settlement":
        raise ValueError("Manual settlement inputs require complete_settlement.")
    root = apply_rollout_settlement_supplements(original, supplements)
    for key in ("bounded_search_settings", "information_set_search_settings"):
        root.pop(key, None)
    root.update(analysis_mode="post_game_review", actual_card_played=actual_card,
                recommendation_method="whole_game_rollout",
                whole_game_rollout_settings=serialize_rollout_settings(settings))
    return root


def validate_manual_rollout_derivation(value, data):
    """Check transport consistency; only a Session binding authenticates the source."""
    from skatmind.input_loader import build_position_from_document
    from skatmind.whole_game_rollout_workflow import parse_rollout_settings

    original = value["original_request"]
    if type(original) is not dict or set(original) != {
        "api_contract_version", "workflow", "document"
    } or type(original["api_contract_version"]) is not int or (
        original["api_contract_version"] != 1 or original["workflow"] != "position_analysis"
    ):
        raise ValueError("Manual derivation requires the original Position Request.")
    root = original["document"]
    if type(root) is not dict or root.get("analysis_mode") != "live_decision" or any(
        key in root for key in ("actual_card_played", "whole_game_rollout_settings",
                                "whole_game_rollout_derivation")
    ) or root.get("recommendation_method") == "whole_game_rollout":
        raise ValueError("Original Request must be an unsupplemented before-card decision.")
    build_position_from_document(root)
    if value["original_request_fingerprint"] != rollout_source_fingerprint(
        "skatmind.rollout.original_request.v1", original
    ) or value["supplement_origin"] != "manual_analysis_input" or not value["supplements"]:
        raise ValueError("Manual derivation requires exact source identity and explicit inputs.")
    settings = parse_rollout_settings(data["whole_game_rollout_settings"])
    expected = rollout_analysis_root(root, data["actual_card_played"], settings,
                                     value["supplements"])
    actual = {key: item for key, item in data.items() if key != "whole_game_rollout_derivation"}
    if json.dumps(expected, sort_keys=True) != json.dumps(actual, sort_keys=True):
        raise ValueError("Derived Request changed facts outside the permitted transformation.")
    effective = build_serializable_game_declaration(rollout_declaration(expected))
    if json.dumps(effective, sort_keys=True) != json.dumps(
        value["effective_declaration"], sort_keys=True
    ):
        raise ValueError("Effective declaration must match the supplemented analysis inputs.")
