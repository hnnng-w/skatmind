"""Source-bound, process-local one-Decision Match rollout capture and publication."""

import hashlib
import hmac

from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    build_match_analysis_report_v1,
)
from skatmind.match_decision_analysis import (
    build_match_decision_position_request_v1,
    execute_match_decision_analysis_v1,
)
from skatmind.rollout_derivation import missing_rollout_settlement_inputs

from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1
from .session_recorded_review_form import (
    RecordedRolloutFormError,
    parse_recorded_rollout_form_v1,
    parse_recorded_rollout_supplements_v1,
)


def match_rollout_binding(active, decision):
    source = (active.handle, active.capture.content_fingerprint, active.position_generation,
              active.selected_position, decision)
    return hmac.new(active.card_entry_key, repr(source).encode(), hashlib.sha256).hexdigest()


def project_match_rollout_form(active, preparation):
    ready = [row["decision_index"] for row in preparation["decisions"]
             if row["state"] == "prepared"]
    if not ready:
        return None
    decision = active.selected_review_decision
    if decision not in ready:
        decision = ready[0]
    request = build_match_decision_position_request_v1(active.workspace,
        match_position=active.selected_position, decision_index=decision,
        options=MatchDecisionAnalysisOptionsV1(use_profile_presets=False)).request
    root = request.to_dict()["document"]
    settings = {"objective": "complete_settlement", "requested_worlds": 100, "random_seed": 0}
    supplied = {}
    for report in reversed(active.capture.report_store.list()):
        if (report.match_position == active.selected_position and report.decision_index == decision
                and report.workspace_revision == active.workspace.revision
                and report.value.status == "executed"
                and report.value.options.recommendation_method == "whole_game_rollout"):
            settings = report.value.request.document["whole_game_rollout_settings"]
            supplied = report.value.options.settlement_supplements
            break
    return {"decision": decision, "selection": match_rollout_binding(active, decision),
            "settings": settings, "supplied": supplied,
            "missing": missing_rollout_settlement_inputs(root)}


def execute_unified_match_rollout(active, values):
    """Capture under the workspace lock, evaluate unlocked, then verify ownership again."""
    values = dict(values)
    with active.capture.lock:
        active.require_attached()
        try:
            require_recording_fresh_v1(active, "matches")
        except RecordingOpenConflict:
            active.capture.report_store.clear()
            raise
        try:
            position = int(values.pop("match_position"))
            decision = int(values.pop("decision_index"))
            revision = int(values.pop("expected_revision"))
        except (KeyError, ValueError, TypeError) as error:
            raise RecordingOpenConflict() from error
        selection = match_rollout_binding(active, decision)
        if (position != active.selected_position or revision != active.workspace.revision
                or not hmac.compare_digest(str(values.get("decision_selection", "")), selection)):
            raise RecordingOpenConflict()
        attempt = object()
        active.rollout_attempt = attempt
        active.rollout_notice = None
        generation = active.capture.report_store.generation
        workspace = active.workspace
        _, settings, submitted = parse_recorded_rollout_form_v1(values)
        try:
            original = build_match_decision_position_request_v1(workspace,
                match_position=position, decision_index=decision,
                options=MatchDecisionAnalysisOptionsV1(use_profile_presets=False))
        except ValueError as error:
            raise RecordedRolloutFormError("match_unavailable") from error
        supplements = parse_recorded_rollout_supplements_v1(
            submitted, original.request.to_dict()["document"], settings.objective)
        options = MatchDecisionAnalysisOptionsV1(recommendation_method="whole_game_rollout",
            use_profile_presets=False, rollout_settings=settings,
            settlement_supplements=supplements)
    value = execute_match_decision_analysis_v1(workspace, match_position=position,
        decision_index=decision, options=options)
    report = build_match_analysis_report_v1(value)
    with active.capture.lock:
        active.require_attached()
        try:
            require_recording_fresh_v1(active, "matches")
        except RecordingOpenConflict:
            active.capture.report_store.clear()
            raise
        if (active.rollout_attempt is not attempt or active.workspace is not workspace
                or active.capture.report_store.generation != generation
                or match_rollout_binding(active, decision) != selection):
            raise RecordingOpenConflict()
        complete = (value.result is not None
                    and value.result.document["whole_game_rollout_result"]["status"] == "complete")
        retained = next((old for old in reversed(active.capture.report_store.list())
            if old.match_position == position and old.decision_index == decision
            and old.value.status == "executed"
            and old.value.options.recommendation_method == "whole_game_rollout"
            and old.value.result.document["whole_game_rollout_result"]["status"] == "complete"),
            None)
        if not complete:
            active.rollout_notice = (report, generation)
        if complete or retained is None:
            active.capture.report_store.put(report)
        active.selected_review_decision = decision
    return report, report if complete or retained is None else retained
