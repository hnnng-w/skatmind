"""One reconstructed Match decision, with no recorded continuation in the evaluator."""

import json
import re

from skatmind.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.match_decision_review_preparation import MATCH_DECISION_REVIEW_INFORMATION_POLICY
from skatmind.rollout_derivation import rollout_analysis_root, rollout_source_fingerprint
from skatmind.whole_game_rollout_contracts import (
    WholeGameRolloutCandidateV1,
    WholeGameRolloutResultV1,
    WholeGameRolloutWorkV1,
)
from skatmind.whole_game_rollout_workflow import (
    compare_rollout_actual,
    parse_rollout_settings,
    rollout_declaration,
    serialize_rollout_result,
    serialize_rollout_settings,
)

MATCH_ROLLOUT_POLICY = "reconstructed_match_decision"
_DOMAIN = "skatmind.rollout.match_derivation.v1"
_FIELDS = {
    "version", "policy", "reconstruction_policy", "match_id", "workspace_revision",
    "workspace_content_fingerprint", "game_id", "match_position", "match_decision_index",
    "relative_player_map", "original_request", "original_request_fingerprint",
    "effective_settings", "supplement_origin", "supplements", "effective_declaration",
    "derivation_fingerprint",
}


def derive_match_rollout_request_v1(original_root, *, workspace, match_position, snapshot, options):
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    original = RequestDocumentV1(workflow=WorkflowV1.POSITION_ANALYSIS,
                                 document=original_root).to_dict()
    root = rollout_analysis_root(original_root, snapshot.actual_card_played,
                                 options.rollout_settings, dict(options.settlement_supplements))
    source = {
        "version": 1, "policy": MATCH_ROLLOUT_POLICY,
        "reconstruction_policy": MATCH_DECISION_REVIEW_INFORMATION_POLICY,
        "match_id": workspace.match_definition.match_id,
        "workspace_revision": workspace.revision,
        "workspace_content_fingerprint": build_match_workspace_persistence_document_v1(
            workspace).content_fingerprint,
        "game_id": snapshot.source_game_id,
        "match_position": match_position,
        "match_decision_index": snapshot.decision_index,
        "relative_player_map": dict(snapshot.relative_player_map),
        "original_request": original,
        "original_request_fingerprint": rollout_source_fingerprint(
            "skatmind.rollout.original_request.v1", original),
        "effective_settings": serialize_rollout_settings(options.rollout_settings),
        "supplement_origin": "manual_analysis_input" if options.settlement_supplements else None,
        "supplements": dict(options.settlement_supplements),
        "effective_declaration": build_serializable_game_declaration(rollout_declaration(root)),
    }
    source["derivation_fingerprint"] = rollout_source_fingerprint(_DOMAIN, source)
    root["whole_game_rollout_derivation"] = source
    return root


def validate_match_rollout_derivation_v1(value, data):
    """Validate supplied identity/transform consistency, not historical authentication."""
    from skatmind.input_loader import build_position_from_document

    if type(value) is not dict or set(value) != _FIELDS or data is None:
        raise ValueError("Match derivation requires its exact source and effective Request.")
    if (type(value["version"]) is not int or value["version"] != 1
            or value["policy"] != MATCH_ROLLOUT_POLICY
            or value["reconstruction_policy"] != MATCH_DECISION_REVIEW_INFORMATION_POLICY):
        raise ValueError("Unsupported reconstructed Match policy.")
    for key in ("original_request_fingerprint", "workspace_content_fingerprint",
                "derivation_fingerprint"):
        if type(value[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            raise ValueError("Match derivation requires SHA-256 identities.")
    for key, minimum, maximum in (("workspace_revision", 0, None), ("match_position", 1, 36),
                                  ("match_decision_index", 1, 30)):
        number = value[key]
        if type(number) is not int or number < minimum or maximum is not None and number > maximum:
            raise ValueError("Invalid Match source selection.")
    for key in ("match_id", "game_id"):
        if type(value[key]) is not str or not value[key] or value[key].strip() != value[key]:
            raise ValueError("Match source identifiers must be nonempty and unpadded.")
    players = value["relative_player_map"]
    if (type(players) is not dict or set(players) != {"me", "left", "right"}
            or any(type(player) is not str or not player or player.strip() != player
                   for player in players.values()) or len(set(players.values())) != 3):
        raise ValueError("Match derivation requires the selected actor's relative map.")
    source = {key: item for key, item in value.items() if key != "derivation_fingerprint"}
    if value["derivation_fingerprint"] != rollout_source_fingerprint(_DOMAIN, source):
        raise ValueError("Match derivation identity changed.")
    original = value["original_request"]
    if (type(original) is not dict or set(original) != {
            "api_contract_version", "workflow", "document"}
            or type(original["api_contract_version"]) is not int
            or original["api_contract_version"] != 1
            or original["workflow"] != "position_analysis"):
        raise ValueError("Match derivation requires the original Position Request.")
    root = original["document"]
    if (type(root) is not dict or root.get("analysis_mode") != "live_decision"
            or root.get("recommendation_method") != "immediate_expected_value"
            or any(key in root for key in ("actual_card_played", "whole_game_rollout_settings",
                                           "whole_game_rollout_derivation"))):
        raise ValueError("Original Match Request must be an unsupplemented before-card view.")
    build_position_from_document(root)
    if value["match_decision_index"] != (
            3 * len(root.get("completed_tricks", [])) + len(root["current_trick"]) + 1):
        raise ValueError("Match decision identity must equal the accepted before-card prefix.")
    if value["original_request_fingerprint"] != rollout_source_fingerprint(
            "skatmind.rollout.original_request.v1", original):
        raise ValueError("Original Match Request identity changed.")
    settings = parse_rollout_settings(value["effective_settings"])
    if value["supplement_origin"] != ("manual_analysis_input" if value["supplements"] else None):
        raise ValueError("Match settlement inputs must be explicit analysis assumptions.")
    expected = rollout_analysis_root(
        root, data["actual_card_played"], settings, value["supplements"])
    actual = {key: item for key, item in data.items() if key != "whole_game_rollout_derivation"}
    if json.dumps(expected, sort_keys=True) != json.dumps(actual, sort_keys=True):
        raise ValueError("Derived Match Request changed facts outside the permitted changes.")
    if value["effective_declaration"] != build_serializable_game_declaration(
            rollout_declaration(expected)):
        raise ValueError("Effective Match declaration changed.")


def validate_match_rollout_report_v1(report):
    """Reconcile retained typed aggregates and source identity without executing again."""
    from dataclasses import asdict

    from skatmind.bounded_search_information import build_live_search_information_view
    from skatmind.input_loader import build_local_game_state_from_input
    from skatmind.ouvert_simulation import (
        build_declared_ouvert_public_hand_constraint,
        resolve_effective_public_hand_constraints,
    )
    from skatmind.rules import get_legal_cards

    request = report.request.to_dict()["document"]
    result = report.result.to_dict()["document"]
    source = request["whole_game_rollout_derivation"]
    validate_match_rollout_derivation_v1(source, request)
    for key in ("match_id", "workspace_revision", "match_position", "game_id"):
        if source[key] != getattr(report, key):
            raise ValueError("Rollout report changed its captured Match selection.")
    if source["match_decision_index"] != report.decision_index:
        raise ValueError("Rollout report changed its captured Match Decision.")
    binding = report.profile_binding
    if source["relative_player_map"] != {"me": binding.acting_player_id,
            "left": binding.left_opponent_player_id, "right": binding.right_opponent_player_id}:
        raise ValueError("Rollout report changed its actor-relative mapping.")
    if (source["effective_settings"] != serialize_rollout_settings(report.options.rollout_settings)
            or source["supplements"] != dict(report.options.settlement_supplements)
            or result.get("whole_game_rollout_derivation") != source
            or result.get("game_declaration") != source["effective_declaration"]):
        raise ValueError("Rollout report changed its effective inputs.")
    raw = result["whole_game_rollout_result"]
    fields = WholeGameRolloutResultV1.__dataclass_fields__
    typed = WholeGameRolloutResultV1(**{
        **{key: raw[key] for key in fields if key not in {
            "settings", "candidates", "ranked_cards", "tied_best_cards", "work"}},
        "settings": report.options.rollout_settings,
        "candidates": tuple(WholeGameRolloutCandidateV1(**{
            key: row[key] for key in WholeGameRolloutCandidateV1.__dataclass_fields__
        }) for row in raw["candidates"]),
        "ranked_cards": tuple(raw["ranked_cards"]),
        "tied_best_cards": tuple(raw["tied_best_cards"]),
        "work": WholeGameRolloutWorkV1(**raw["work"]),
    })
    state = build_local_game_state_from_input(request)
    public = build_declared_ouvert_public_hand_constraint(request)
    view = build_live_search_information_view(state=state,
        declaration=rollout_declaration(request), left_hand_size=request["left_hand_size"],
        right_hand_size=request["right_hand_size"], skat_visibility=request["skat_visibility"],
        public_hand_constraints=resolve_effective_public_hand_constraints(
            () if public is None else (public,)))
    if (typed.source_fingerprint != rollout_source_fingerprint(
            "skatmind.whole_game_rollout.source.v1", asdict(view))
            or typed.source != view.source or typed.information_cutoff != view.information_cutoff):
        raise ValueError("Rollout report changed its reconstructed core source identity.")
    expected_position = asdict(state)
    if any(result["position"].get(key) != expected_position[key] for key in result["position"]):
        raise ValueError("Rollout report changed the prepared Position facts.")
    if typed.game_type != request["game_type"] or typed.local_side != (
            "declarer" if request["declarer_player"] == "me" else "defenders"):
        raise ValueError("Rollout report changed its selected actor's contract or party.")
    legal = get_legal_cards(state.hand, state.current_trick, state.game_type)
    if typed.candidates and {row.card for row in typed.candidates} != set(legal):
        raise ValueError("Rollout report changed its legal candidate set.")
    for row in typed.candidates:
        expected_margin = row.total_declarer_points - row.total_defender_points
        if typed.local_side == "defenders":
            expected_margin = -expected_margin
        if row.total_local_card_point_margin != expected_margin:
            raise ValueError("Rollout report changed its party-oriented point margin.")
    if raw != serialize_rollout_result(typed) or result["whole_game_rollout_comparison"] != (
            compare_rollout_actual(typed, request["actual_card_played"])):
        raise ValueError("Rollout report changed retained aggregates or actual-card comparison.")
    summary = result["recommendation_method_summary"]
    if (summary["requested_method"] != "whole_game_rollout" or summary["effective_method"] != (
            "whole_game_rollout" if typed.status == "complete" else "none")
            or result["recommendation"]["card"] != typed.recommended_card
            or summary["fallback_used"] or summary["fallback_method"] is not None
            or result.get("opponent_profile_application_summary") is not None):
        raise ValueError("Rollout report changed its method or fixed-policy boundary.")
