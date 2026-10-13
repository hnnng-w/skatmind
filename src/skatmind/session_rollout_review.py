"""Separately identified analysis derived from an unchanged saved decision."""

from skatmind.api.v1 import parse_request
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.rollout_derivation import (
    MANUAL_SETTLEMENT_POLICY,
    rollout_analysis_root,
    rollout_source_fingerprint,
)
from skatmind.session_checkpoint_review import export_session_checkpoint_review_request_v1
from skatmind.whole_game_rollout_workflow import rollout_declaration


def derive_session_rollout_review_request_v1(*, state, checkpoint, settings, supplements=None):
    """Resolve the accepted observation, transform configuration, retain the cutoff."""
    exported = export_session_checkpoint_review_request_v1(state=state, checkpoint=checkpoint)
    if exported.status != "available":
        raise ValueError("An observed frozen checkpoint is required for rollout review.")
    supplements = {} if supplements is None else supplements
    root = rollout_analysis_root(checkpoint.request.to_dict()["document"],
                                 exported.observation.actual_card, settings, supplements)
    root["whole_game_rollout_derivation"] = {
        "version": 1,
        "policy": "frozen_checkpoint_method_settings_only",
        "original_request_fingerprint": rollout_source_fingerprint(
            "skatmind.rollout.original_request.v1", checkpoint.request.to_dict()),
        "checkpoint_fingerprint": rollout_source_fingerprint(
            "skatmind.rollout.checkpoint.v1", checkpoint.to_dict()),
        "source_revision": checkpoint.source_revision,
        "checkpoint_decision_index": checkpoint.decision_index,
    }
    if supplements:
        root["whole_game_rollout_derivation"].update(
            version=2, policy=MANUAL_SETTLEMENT_POLICY,
            original_request=checkpoint.request.to_dict(),
            supplement_origin="manual_analysis_input", supplements=dict(supplements),
            effective_declaration=build_serializable_game_declaration(rollout_declaration(root)))
    return parse_request(root)
