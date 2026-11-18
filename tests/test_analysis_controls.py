"""Concrete settings and explicit native precedence at the private adapters."""

from dataclasses import replace

import pytest
from test_guided_historical_review_form import _completed_example_draft
from test_guided_position_form import _form

from skatmind.app_web.analysis_controls import AnalysisControlError, resolve_analysis_controls
from skatmind.app_web.historical_form import HistoricalFormOptionsV1
from skatmind.app_web.historical_form_parsing import parse_historical_options_form_v1
from skatmind.app_web.position_form import (
    build_guided_position_execution_v1,
    parse_position_form_v1,
)
from skatmind.app_web.session_form_translation import (
    build_session_historical_execution_options_from_form_v1,
    build_session_position_options_from_form_v1,
)
from skatmind.app_web.session_recorded_review_form import parse_recorded_rollout_form_v1
from skatmind.capture_web.analysis import _decision_options, _historical_options

PRESETS = (("quick", 25, 250, 5000), ("standard", 100, 1000, 30000),
           ("more_time", 400, 4000, 60000))


@pytest.mark.parametrize("effort,count,position_count,timeout", PRESETS)
def test_all_adapters_resolve_actual_effective_settings(effort, count, position_count, timeout):
    ui = {"settings_mode": "ordinary", "analysis_effort": effort}
    draft = parse_position_form_v1(_form(**{key: [value] for key, value in {
        **ui, "sample_count": "7", "analysis_method": "bounded_search", "random_seed": "19",
        "search_seed": "23", "multi_step_count": "2", "compare_policies": "on",
        "include_provenance": "on"}.items()}))
    request, options = build_guided_position_execution_v1(draft)
    assert request.document["sample_count"] == position_count
    assert request.document["random_seed"] == 19
    assert "recommendation_method" not in request.document
    assert options.include_provenance and "multi_step_count" not in options.workflow_options
    assert draft.form_values.singular("sample_count") == "7"
    assert draft.form_values.singular("analysis_method") == "bounded_search"
    position = build_session_position_options_from_form_v1({**ui, "sample_count": "7",
        "random_seed": "19", "opponent_strategy": "random", "recommendation_method": "auto",
        "search_budget_profile": "historical_review_v1"})
    assert position.sample_count == count and position.random_seed == 19
    assert position.recommendation_method is None
    assert position.bounded_search_settings is None and not position.use_basic_opponent_strategy
    history = build_session_historical_execution_options_from_form_v1({**ui,
        "sample_count": "7", "random_seed": "19", "search_seed": "23",
        "search_budget_profile": "historical_review_v1", "immediate_review": "false",
        "search_review": "true", "information_set_search_review": "false",
        "decision_snapshots": "true", "historical_tactical_motif_review": "true",
        "replay_coaching": "false", "information_set_replay_coaching": "false"})
    assert history.workflow_options["immediate_sample_count"] == count
    assert history.workflow_options["immediate_base_random_seed"] == 19
    assert history.workflow_options["immediate_review"] is True
    assert history.workflow_options["search_review"] is False
    assert history.workflow_options["historical_tactical_motif_review"] is True
    match = {**ui, "immediate_sample_count": "7", "immediate_random_seed": "19",
        "search_random_seed": "23", "search_budget_profile": "interactive_v1",
        "recommendation_method": "information_set_search", "use_profile_presets": "on"}
    decision = _decision_options(resolve_analysis_controls(match, path="match_decision"),
                                 browser_form=True)
    assert decision.immediate_sample_count == count and decision.immediate_random_seed == 19
    assert decision.recommendation_method == "immediate_expected_value"
    assert decision.use_profile_presets
    match.pop("recommendation_method")
    historical = _historical_options(resolve_analysis_controls(match, path="match_history"),
                                     browser_form=True)
    assert historical.immediate_sample_count == count and historical.immediate_review
    _, rollout, _ = parse_recorded_rollout_form_v1({**ui, "decision_selection": "a" * 64,
        "objective": "played_game_goal", "requested_worlds": "7", "random_seed": "19"},
        retained_timeout=12345)
    assert (rollout.requested_worlds, rollout.wall_clock_timeout_ms) == (count, timeout)
    assert rollout.random_seed == 19
    assert (rollout.max_preparation_work, rollout.max_card_transitions) == (100000, 300000)
    draft = parse_historical_options_form_v1(replace(_completed_example_draft(), step=6),
        {key: [value] for key, value in {**ui, "immediate_sample_count": "7",
         "immediate_base_random_seed": "19", "search_seed": "23", "tactical": "on",
         "include_provenance": "on"}.items()})
    assert draft.options.immediate_review and draft.options.immediate_sample_count == count
    assert draft.options.immediate_base_random_seed == 19
    assert draft.options.tactical and draft.options.include_provenance


@pytest.mark.parametrize("effort,count,position_count,timeout", PRESETS)
@pytest.mark.parametrize("method", (
    "immediate", "bounded_search", "auto", "information_set_search"))
def test_custom_method_and_simulation_ignore_effort(effort, count, position_count, timeout, method):
    values = _form(settings_mode=["custom"], analysis_effort=[effort], analysis_method=[method],
                   sample_count=["7"], random_seed=["19"], multi_step_count=["2"],
                   compare_policies=["on"], include_provenance=["on"])
    draft = parse_position_form_v1(values)
    request, options = build_guided_position_execution_v1(draft)
    assert draft.analysis_method == method and request.document["sample_count"] == 7
    assert options.workflow_options["multi_step_count"] == 2 and options.include_provenance
    assert draft.form_values.singular("analysis_effort") == effort


@pytest.mark.parametrize("timeout", (5000, 60000, 12345))
def test_custom_rollout_preserves_owner_supplied_timeout_and_rejects_hidden_authority(timeout):
    values = {"settings_mode": "custom", "analysis_effort": "standard",
        "decision_selection": "a" * 64, "objective": "played_game_goal",
        "requested_worlds": "7", "random_seed": "19"}
    parsed = parse_recorded_rollout_form_v1(values, retained_timeout=timeout)[1]
    assert parsed.wall_clock_timeout_ms == timeout
    with pytest.raises(ValueError):
        parse_recorded_rollout_form_v1({**values, "wall_clock_timeout_ms": "30000"},
                                      retained_timeout=timeout)


def test_result_only_legacy_and_explicit_custom_history_stay_result_only():
    assert HistoricalFormOptionsV1().immediate_review is False
    draft = replace(_completed_example_draft(), step=6)
    for values in ({}, {"settings_mode": ["custom"], "analysis_effort": ["more_time"]}):
        assert parse_historical_options_form_v1(draft, values).options.immediate_review is False
    for values in ({"settings_mode": "invalid"}, {"analysis_effort": "unbounded"}):
        with pytest.raises(AnalysisControlError):
            resolve_analysis_controls(values, path="position")


def test_additional_families_keep_their_dependency_validation():
    draft = replace(_completed_example_draft(), step=6)
    with pytest.raises(ValueError, match="cannot be combined"):
        parse_historical_options_form_v1(draft, {"settings_mode": ["ordinary"],
            "analysis_effort": ["quick"], "replay_coaching": ["on"],
            "information_set_replay_coaching": ["on"]})
