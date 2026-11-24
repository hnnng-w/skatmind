"""Private legal-card facts; never numeric analysis, execution or Learning evidence."""

from dataclasses import dataclass

from skatmind.api.v1.schema_validation import validate_input_document
from skatmind.input_loader import build_game_state_from_input, build_position_from_document
from skatmind.rules import get_legal_cards


@dataclass(frozen=True, slots=True)
class ForcedCardGuidance:
    card: str


def forced_card_guidance(request):
    """Accept only a complete validated Position hand and its concrete own turn.

    Observation candidates are deliberately not an input to this boundary.
    Position validation reconciles hand size, chronology and the full legal set.
    """
    document = request.to_dict()["document"]
    validate_input_document(document)
    root = build_position_from_document(document)
    state = build_game_state_from_input(root)
    if (state.next_player != "me" or not state.hand or root.get("played_cards")
            or root.get("game_end_reason", "not_ended") != "not_ended"
            or root.get("game_shortening") is not None):
        return None
    from .position_form import _derived_hand_sizes
    sizes = _derived_hand_sizes(state.completed_tricks, state.current_trick, state.trick_leader)
    if (len(state.hand) != sizes["me"] or root["left_hand_size"] != sizes["left"]
            or root["right_hand_size"] != sizes["right"]):
        return None
    legal = get_legal_cards(state.hand, state.current_trick, state.game_type)
    return ForcedCardGuidance(legal[0]) if len(legal) == 1 else None


def ordinary(values):
    return values.get("settings_mode") == "ordinary"


def render_guidance(value, locale):
    from .stateful_localization import card_name
    from .task_first_rendering import paragraph

    if value is None:
        return ""
    return ('<section id="forced-card-guidance" role="status" tabindex="-1">'
        + paragraph(locale, "analysis.forced_card", card=card_name(locale, value.card))
        + paragraph(locale, "analysis.forced_card_help") + '</section>')


def send_guidance(handler, value, guard, destination):
    from .automatic_learning_rendering import link
    from .stateful_localization import text

    locale = handler._frontend_state().locale
    handler._retained_delivery_guard = guard
    handler._content_page("/matches" if destination.startswith("/matches") else "/sessions",
        return_to=destination,
        title=text(locale, "analysis.forced_title"), content=render_guidance(value, locale)
        + link(destination, text(locale, "analysis.forced_return")),
        untranslated_workflow_body=False, task_first=True)


def session_guidance(handler, active, values, *, export_options=None):
    """Fresh source/selection admission and independent final delivery, with no writes."""
    import skatmind.api.v1.session as session_api

    from .session_recorded_review import (
        RecordedDecisionReviewConflictError,
        project_recorded_session_decisions_v1,
        require_recorded_review_file_fresh_v1,
    )

    if not ordinary(values):
        return False
    app = handler.server.app_context
    with active.lock:
        active.require_attached()
        require_recorded_review_file_fresh_v1(active)
        document, generation = active.document, active.generation
        if export_options is not None:
            exported = session_api.export_session_position_request(
                active.state, export_options).value
            if exported.status != "available":
                return False
            request = exported.request
        else:
            from .session_recorded_review_form import (
                parse_recorded_rollout_form_v1,
                parse_recorded_rollout_supplements_v1,
            )
            _, settings, supplied = parse_recorded_rollout_form_v1(values)
            selection = values.get("decision_selection")
            row = next((row for row in project_recorded_session_decisions_v1(active).decisions
                        if row.selection == selection), None)
            if row is None or row.checkpoint.acting_player_id != active.state.local_player_id:
                raise RecordedDecisionReviewConflictError()
            request = row.checkpoint.request
        value = forced_card_guidance(request)
        if value is None:
            return False
        if export_options is None:
            parse_recorded_rollout_supplements_v1(supplied, request.to_dict()["document"],
                settings.objective, require_missing=False)
        def guard():
            with active.lock:
                active.require_attached()
                require_recorded_review_file_fresh_v1(active)
                with app.lock:
                    if (app.managed_stateful.active_session is not active
                            or active.document is not document or active.generation != generation):
                        raise RecordedDecisionReviewConflictError()
        guard()
        from .analysis_controls import remember_controls, session_scope
        remember_controls(active, "session.analyze" if export_options is not None else
            "session.review_whole_game", session_scope(active) if export_options is not None else
            (*session_scope(active), selection), values)
    send_guidance(handler, value, guard, active.review_page or "/sessions/current")
    return True


def match_guidance(handler, active, values):
    from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
    from skatmind.match_decision_analysis import build_match_decision_position_request_v1

    from .match_decision_selection import require_bound_match_decision
    from .recorded_review_opening import RecordingOpenConflict, require_recording_fresh_v1

    if not ordinary(values):
        return False
    app = handler.server.app_context
    with active.capture.lock:
        active.require_attached()
        require_bound_match_decision(active, values)
        if "review_binding" in values:
            from .match_review_context import require_match_review_binding_v1
            require_match_review_binding_v1(active, dict(values))
        require_recording_fresh_v1(active, "matches")
        workspace = active.workspace
        position = int(values["match_position"])
        if int(values["expected_revision"]) != workspace.revision:
            raise RecordingOpenConflict()
        from .analysis_controls import match_scope, remember_controls, resolve_analysis_controls
        if values.get("operation") == "analyze_decision":
            from skatmind.capture_web.analysis import _decision_options, _validate_fields

            controls = resolve_analysis_controls(values, path="match_decision")
            controls = {key: value for key, value in controls.items() if key not in
                        {"visible_decision_index", "decision_selection", "review_binding"}}
            _validate_fields(controls, "analyze_decision")
            _decision_options(controls, browser_form=True)
        else:
            from .session_recorded_review_form import (
                parse_recorded_rollout_form_v1,
                parse_recorded_rollout_supplements_v1,
            )
            _, settings, supplied = parse_recorded_rollout_form_v1({
                key: value for key, value in values.items()
                if key not in {"match_position", "decision_index", "expected_revision",
                               "visible_decision_index"}})
        prepared = build_match_decision_position_request_v1(workspace,
            match_position=position, decision_index=int(values["decision_index"]),
            options=MatchDecisionAnalysisOptionsV1(use_profile_presets=False))
        if prepared.request is None:
            return False
        value = forced_card_guidance(prepared.request)
        if value is None:
            return False
        if values.get("operation") != "analyze_decision":
            parse_recorded_rollout_supplements_v1(supplied,
                prepared.request.to_dict()["document"], settings.objective, require_missing=False)
        def guard():
            with active.capture.lock:
                active.require_attached()
                require_bound_match_decision(active, values)
                if "review_binding" in values:
                    require_match_review_binding_v1(active, dict(values))
                require_recording_fresh_v1(active, "matches")
                with app.lock:
                    if (app.managed_stateful.active_match is not active
                            or active.workspace is not workspace):
                        raise RecordingOpenConflict()
        guard()
        remember_controls(active, "match.analysis.analyze_decision" if values.get("operation")
            else "match.review_whole_game", match_scope(active) if values.get("operation") else
            (*match_scope(active), int(values["decision_index"])), values)
    send_guidance(handler, value, guard, f"/matches/review/{position}")
    return True
