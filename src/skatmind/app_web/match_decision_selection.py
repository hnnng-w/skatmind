"""Bounded selection/preparation only; both analysis actions share the same owner."""

import hashlib
import hmac
import re

from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
from skatmind.match_decision_analysis import build_match_decision_position_request_v1

from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1

MATCH_DECISION_SELECTION_ROUTE = "/matches/select-decision"


class MatchDecisionSelectionConflict(RecordingOpenConflict):
    """The intended selection has not installed a matching ready analysis context."""


def _index(value):
    if type(value) is not str or re.fullmatch(r"[1-9]|[12][0-9]|30", value) is None:
        raise MatchDecisionSelectionConflict()
    return int(value)


def match_decision_source_scope(active):
    values = (active.handle, active.capture.content_fingerprint, active.selected_position,
              active.position_generation, active.capture.report_store.generation)
    return hmac.new(active.card_entry_key, repr(values).encode(), hashlib.sha256).hexdigest()


def match_decision_selection_binding(active, return_to):
    from .match_rollout_frontend import match_rollout_binding

    return match_rollout_binding(active, ("select_decision", return_to))


def require_bound_match_decision(active, values):
    from .match_rollout_frontend import match_rollout_binding

    active.require_attached()
    decision = _index(values.get("decision_index"))
    visible = _index(values.get("visible_decision_index"))
    binding = values.get("decision_selection")
    if (active.review_selection_pending or visible != decision
            or active.selected_review_decision not in (None, decision)
            or type(binding) is not str
            or not hmac.compare_digest(binding, match_rollout_binding(active, decision))
            or str(values.get("match_position")) != str(active.selected_position)
            or str(values.get("expected_revision")) != str(active.workspace.revision)):
        raise MatchDecisionSelectionConflict()
    require_recording_fresh_v1(active, "matches")
    return decision


def select_match_decision(active, values):
    """Apply one authenticated selection; failure leaves old controls unready."""
    if set(values) != {"decision_index", "selection_context", "return_to",
                       "match_position", "expected_revision"}:
        raise MatchDecisionSelectionConflict()
    with active.capture.lock:
        active.require_attached()
        return_to = values["return_to"]
        allowed = {"/matches/current", f"/matches/position/{active.selected_position}",
                   f"/matches/review/{active.selected_position}"}
        allowed.update(f"/matches/reports/{report.report_id}"
            for report in active.capture.report_store.list()
            if report.match_position == active.selected_position
            and report.workspace_revision == active.workspace.revision)
        binding = values["selection_context"]
        if (return_to not in allowed or type(binding) is not str
                or not hmac.compare_digest(binding,
                    match_decision_selection_binding(active, return_to))
                or str(values["match_position"]) != str(active.selected_position)
                or str(values["expected_revision"]) != str(active.workspace.revision)):
            raise MatchDecisionSelectionConflict()
        require_recording_fresh_v1(active, "matches")
        decision = _index(values["decision_index"])
        apply_match_decision_selection(active, decision)
        return return_to


def apply_match_decision_selection(active, decision):
    """Caller holds the Capture lock; accepted evidence owns availability."""
    active.review_decision_generation += 1
    active.review_selection_pending = True
    active.review_selection_native_ready = False
    active.rollout_attempt = None
    active.rollout_notice = None
    try:
        build_match_decision_position_request_v1(active.workspace,
            match_position=active.selected_position, decision_index=decision,
            options=MatchDecisionAnalysisOptionsV1(use_profile_presets=False))
    except ValueError as error:
        raise MatchDecisionSelectionConflict() from error
    require_recording_fresh_v1(active, "matches")
    active.selected_review_decision = decision
    active.review_selection_pending = False
    active.review_selection_native_ready = True
