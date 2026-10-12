"""Separately identified analysis derived from an unchanged saved decision."""

import hashlib
import json

from skatmind.api.v1 import parse_request
from skatmind.session_checkpoint_review import export_session_checkpoint_review_request_v1
from skatmind.whole_game_rollout_workflow import serialize_rollout_settings


def _fingerprint(domain: str, value: dict) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\0" + json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("utf-8")).hexdigest()


def derive_session_rollout_review_request_v1(*, state, checkpoint, settings):
    """Resolve the accepted observation, transform configuration, retain the cutoff."""
    exported = export_session_checkpoint_review_request_v1(state=state, checkpoint=checkpoint)
    if exported.status != "available":
        raise ValueError("An observed frozen checkpoint is required for rollout review.")
    root = exported.request.to_dict()["document"]
    for key in ("bounded_search_settings", "information_set_search_settings"):
        root.pop(key, None)
    root["recommendation_method"] = "whole_game_rollout"
    root["whole_game_rollout_settings"] = serialize_rollout_settings(settings)
    root["whole_game_rollout_derivation"] = {
        "version": 1,
        "policy": "frozen_checkpoint_method_settings_only",
        "original_request_fingerprint": _fingerprint(
            "skatmind.rollout.original_request.v1", checkpoint.request.to_dict()),
        "checkpoint_fingerprint": _fingerprint(
            "skatmind.rollout.checkpoint.v1", checkpoint.to_dict()),
        "source_revision": checkpoint.source_revision,
        "checkpoint_decision_index": checkpoint.decision_index,
    }
    return parse_request(root)
