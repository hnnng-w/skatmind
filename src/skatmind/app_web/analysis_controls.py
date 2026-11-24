"""Private native-form effort translation; concrete settings alone reach engines."""

from collections.abc import Mapping

CONTROL_FIELDS = ("analysis_effort", "settings_mode")
EFFORTS = ("quick", "standard", "more_time")
MODES = ("ordinary", "custom")
COUNTS = (25, 100, 400)
POSITION_COUNTS = (250, 1000, 4000)
TIMEOUTS = (5000, 30000, 60000)
ADDITIONAL_FIELDS = frozenset({
    "decision_snapshots", "replay_coaching", "information_set_replay_coaching",
    "tactical", "tactical_motif_review", "historical_tactical_motif_review",
    "include_provenance",
})


class AnalysisControlError(ValueError):
    def __init__(self, field):
        self.field_key = field
        super().__init__(f"{field} must be one supported explicit choice.")


def resolve_analysis_controls(values: Mapping, *, path: str, retained_timeout=None):
    """Mode wins over closed technical controls. Missing mode is legacy custom.

    Callers retain the original safe form values separately. A change of effort
    alone cannot leave custom mode. Rollout timeout authority is supplied by the
    owner only after its fresh source/selection checks, never by a hidden field.
    """
    result = dict(values)
    mode = result.pop("settings_mode", "custom")
    effort = result.pop("analysis_effort", "standard")
    if mode not in MODES:
        raise AnalysisControlError("settings_mode")
    if effort not in EFFORTS:
        raise AnalysisControlError("analysis_effort")
    index = EFFORTS.index(effort)
    if path == "rollout":
        if mode == "ordinary":
            result["requested_worlds"] = str(COUNTS[index])
        timeout = TIMEOUTS[index] if mode == "ordinary" else (
            30000 if retained_timeout is None else retained_timeout)
        return result, timeout
    if mode == "custom":
        return result
    sample_field = ("sample_count" if path in {"position", "session_position", "session_history"}
                    else "immediate_sample_count")
    result[sample_field] = str((POSITION_COUNTS if path == "position" else COUNTS)[index])
    if path == "position":
        result["analysis_method"] = "immediate"
        for name in ("multi_step_count", "card_selection_policy", "strict_context",
                     "compare_policies", "comparison_only"):
            result.pop(name, None)
    elif path in {"session_position", "match_decision"}:
        # Session's ordinary exporter has always omitted the explicit method;
        # retain exact default checkpoint identity as well as Immediate behavior.
        result["recommendation_method"] = (
            "" if path == "session_position" else "immediate_expected_value")
        if path == "match_decision":
            result["search_budget_profile"] = "historical_review_v1"
    else:
        result["immediate_review"] = "true" if path == "session_history" else "on"
        for name in ("search_review", "information_set_search_review"):
            if path == "session_history":
                result[name] = "false"
            else:
                result.pop(name, None)
        if path == "match_history" and not any(result.get(name) in (True, "on", "true", "1")
                for name in ("replay_coaching", "information_set_replay_coaching")):
            result["search_budget_profile"] = "historical_review_v1"
    return result


def control_values(values=None, *, fresh=False):
    values = values or {}
    return {"analysis_effort": values.get("analysis_effort", "standard"),
            "settings_mode": values.get("settings_mode", "ordinary" if fresh else "custom")}


def effort_fields(locale, values=None, *, fresh=False, position=False, compact=False):
    from .stateful_localization import text
    from .task_first_rendering import paragraph, select_field

    values = control_values(values, fresh=fresh)
    control = (select_field(locale, "analysis_effort", "analysis.effort", (
        (value, text(locale, "analysis.effort." + value)) for value in EFFORTS),
        values["analysis_effort"])
          + '<p class="analysis-custom-state">' + text(locale, "analysis.mode.custom") + '</p>')
    return control if compact else (control + paragraph(locale, "analysis.effort.help")
        + paragraph(locale, "analysis.effort.position" if position else "analysis.effort.decisions")
    )


def mode_fields(locale, values=None, *, fresh=False):
    from .stateful_localization import text
    from .task_first_rendering import paragraph, select_field

    values = control_values(values, fresh=fresh)
    return (select_field(locale, "settings_mode", "analysis.mode", (
        (value, text(locale, "analysis.mode." + value)) for value in MODES),
        values["settings_mode"])
        + paragraph(locale, "analysis.mode.help"))


def restore_controls(markup, values):
    """Restore private, already allowlisted native values, including inactive ones."""
    from .form_parsing import FormValuesV1
    from .validation_rendering import _replace_safe_values

    return markup if values is None else _replace_safe_values(markup, values if isinstance(
        values, FormValuesV1) else safe_controls(values))


def native_analysis_form(markup):
    # Native constraints cannot depend on the selected mode without script. The
    # existing server field validators own active controls and reveal errors.
    return markup.replace("<form ", "<form novalidate ", 1)


def safe_controls(values, form_key=None):
    from .form_parsing import FormValuesV1, FormValueV1
    if form_key is not None:
        from .form_registry import capture_safe_submitted_values_v1, get_frontend_form_by_key_v1
        return capture_safe_submitted_values_v1(get_frontend_form_by_key_v1(form_key), values)
    return FormValuesV1(tuple(FormValueV1(key, (str(value),)) for key, value in values.items()))


def values_dict(values):
    return {} if values is None else {entry.field: values.singular(entry.field)
                                      for entry in values.entries}


def session_scope(context):
    return context.generation, context.document.content_fingerprint


def match_scope(context):
    return (context.capture.content_fingerprint, context.capture.report_store.generation,
            context.position_generation,
            context.review_decision_generation, context.selected_position)


def remembered_controls(context, key, scope):
    retained = context.analysis_forms.get(key)
    return retained[1:] if retained is not None and retained[0] == scope else (None, None)


def remember_controls(context, key, scope, values, *, timeout=None):
    # One small slot per existing form owner, not preferences or persisted data.
    context.analysis_forms[key] = (scope, safe_controls(values, key), timeout)


def retained_match_controls(context, reports, preparation):
    """An old source-matched execution has deliberate values, never inferred presets."""
    controls = {key: entry[1] for key, entry in context.analysis_forms.items()
                if entry[0] == match_scope(context)}
    decision = context.selected_review_decision or next((row["decision_index"]
        for row in preparation["decisions"] if row["state"] == "prepared"), None)
    for report in reversed(reports):
        if report.match_position != context.selected_position or report.value.status != "executed":
            continue
        if report.report_kind == "decision_analysis":
            if (report.decision_index != decision
                    or report.value.options.recommendation_method == "whole_game_rollout"):
                continue
            key = "match.analysis.analyze_decision"
        elif report.report_kind == "historical_analysis":
            key = "match.analysis.analyze_historical_game"
        else:
            continue
        if key not in controls:
            values = {name: ("on" if value else "") if isinstance(value, bool)
                      else str(value if value is not None else 0)
                      for name, value in report.value.options.to_dict().items()}
            controls[key] = safe_controls({**values, "settings_mode": "custom",
                                          "analysis_effort": "standard"}, key)
    return controls
