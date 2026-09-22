"""Single-decision interpretation; execution and defensive scalar cases are separate."""
import json
from dataclasses import FrozenInstanceError
from html import unescape
from pathlib import Path

import pytest
from test_equal_best_immediate import scalar_document, scalar_values
from test_guided_frontend_result_presentation import _execution, score_review_request
from test_information_set_search_position_workflow import _position

from skatmind.api.v1 import WorkflowV1, execute, parse_request, serialize_result
from skatmind.app_web.analysis_explanation import project_analysis_explanation
from skatmind.app_web.result_presentation import build_result_presentation_v1
from skatmind.app_web.result_rendering import render_result_presentation_v1


@pytest.fixture(scope="module")
def immediate_execution():
    return execute(parse_request(score_review_request()))


def normal_result(execution, locale="en", **kwargs):
    return unescape(render_result_presentation_v1(
        build_result_presentation_v1(execution, locale=locale, **kwargs), locale=locale
    ).split('<section class="analysis-technical"')[0])


@pytest.mark.parametrize(("locale", "method", "samples", "information"), (
    ("en", "Current-Trick evaluation", "Samples per Card", "Information used"),
    ("de", "Bewertung des aktuellen Stichs", "Stichproben je Karte", "Verwendeter Wissensstand"),
))
def test_executed_immediate_has_plain_method_count_and_information(
    immediate_execution, locale, method, samples, information,
):
    html = normal_result(immediate_execution, locale)
    assert method in html
    assert samples in html and "100" in html
    assert information in html
    assert "Information cutoff mode" not in html
    assert "Standard immediate analysis" not in html


@pytest.mark.parametrize("locale", ("de", "en"))
def test_executed_immediate_replaces_irrelevant_static_limitations(immediate_execution, locale):
    presentation = build_result_presentation_v1(immediate_execution, locale=locale)
    assert presentation.sections[3].items == ()
    html = normal_result(immediate_execution, locale)
    assert "Search is not a perfect-play claim" not in html
    assert "Only information available at the analysis cutoff is used" not in html
    assert "100 different worlds" not in html and "100 full Games" not in html


def search_request(method):
    if method == "information_set_search":
        return _position(post_game=True)
    if method == "minimax":
        return json.loads((Path(__file__).parents[1] / "examples" /
                           "grand_bounded_search_exhaustive.json").read_text())
    request = score_review_request()
    request["recommendation_method"] = method
    if method != "immediate_expected_value":
        request["bounded_search_settings"] = {
            "random_seed": 0, "max_remaining_tricks": 3, "max_depth_plies": 9,
            "max_nodes": 100, "max_selected_worlds": 1, "max_sampled_worlds": 1,
            "minimum_comparable_worlds": 1, "wall_clock_timeout_ms": None,
        }
    return request


@pytest.fixture(scope="module", params=(
    "immediate_expected_value", "auto", "bounded_search", "minimax", "information_set_search"))
def routed_execution(request):
    return request.param, execute(parse_request(search_request(request.param)))


def test_genuine_method_routing_and_unchanged_bytes(routed_execution):
    requested, execution = routed_execution
    before = serialize_result(execution)
    html = normal_result(execution)
    document = execution.result.document
    if requested in ("immediate_expected_value", "auto"):
        assert "Current-Trick evaluation" in html
        assert "Per-Card setting for one-Trick outcomes" in html
        if requested == "auto":
            assert "Auto tried Search first" in html
            assert "Too many Tricks remained for this Search limit" in html
    elif requested == "bounded_search":
        assert document["recommendation"]["card"] is None
        assert "No recommendation was produced" in html
        assert "Too many Tricks remained for this Search limit" in html
        assert "Samples per Card" not in html and "Current-Trick evaluation" not in html
    elif requested == "minimax":
        assert "treating each selected distribution as fully known within its solver" in html
        assert "consistent choices for the controlled Player" not in html
        assert "Samples per Card" not in html
    else:
        assert "consistent choices for the controlled Player at equal visible information" in html
        assert "fixed other-Player policies" in html
        assert "not a joint-defender solution" in html
        assert "diagnostic, not the recommendation method" in html
        assert "Samples per Card" not in html
    if requested in ("minimax", "information_set_search"):
        assert "not calibrated forecasts of human play" in html
        assert "does not guarantee the real Game’s outcome" in html
    for locale in ("de", "en"):
        normal_result(execution, locale)
    assert serialize_result(execution) == before


@pytest.mark.parametrize("invalid", (None, True, False, -1, "100", 100.0, [], {}))
def test_defensive_missing_or_malformed_count_is_not_zero(immediate_execution, invalid):
    document = immediate_execution.result.to_dict()["document"]
    document["settings"]["sample_count"] = invalid
    html = normal_result(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert "<dt>Samples per Card</dt><dd>Unavailable." in html
    del document["settings"]["sample_count"]
    assert "<dt>Samples per Card</dt><dd>Unavailable." in normal_result(
        _execution(WorkflowV1.POSITION_ANALYSIS, document))


def test_defensive_recorded_zero_and_immutable_projection(immediate_execution):
    document = immediate_execution.result.to_dict()["document"]
    document["settings"]["sample_count"] = 0  # Scalar fixture, not an accepted execution setting.
    assert "<dt>Samples per Card</dt><dd>0." in normal_result(
        _execution(WorkflowV1.POSITION_ANALYSIS, document))
    projected = project_analysis_explanation(document)
    with pytest.raises(FrozenInstanceError):
        projected.samples = 100


@pytest.mark.parametrize("defect", ("explicit_none", "empty", "null", "unknown", "settings",
                                    "legacy_search", "wrong_card"))
def test_defensive_method_metadata_never_guesses_from_settings_or_prose(
    immediate_execution, defect,
):
    document = immediate_execution.result.to_dict()["document"]
    if defect == "explicit_none":
        document["recommendation_method_summary"] = {"effective_method": "none"}
        document["recommendation"]["card"] = None
    elif defect in ("empty", "null", "unknown"):
        document["recommendation_method_summary"] = (
            {} if defect == "empty" else None if defect == "null" else {"effective_method": "new"})
    elif defect == "settings":
        document["settings"]["recommendation_method"] = "immediate_expected_value"
    elif defect == "legacy_search":
        document["bounded_search_result"] = {"status": "complete"}
    else:
        document["recommendation"]["card"] = "D7"
    html = normal_result(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert "Current-Trick evaluation" not in html
    assert ("No recommendation was produced" if defect == "explicit_none" else
            "effective method is missing or unclear") in html


@pytest.mark.parametrize("role,meaning", (
    ("declarer", "the declarer aims to avoid taking this Trick"),
    ("defender", "the defenders aim to make the declarer take this Trick"),
))
def test_scalar_null_roles_do_not_relabel_point_columns_as_the_objective(role, meaning):
    document = scalar_document(scalar_values((10.0, -2.0)), "null", role)
    html = normal_result(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert meaning in html
    assert "Displayed point values and Trick-win fractions are not the ranking objective" in html
    assert "Compares the estimated point swing for your side" not in html


@pytest.mark.parametrize("visibility,cards,meaning", (
    ("unknown", [], "None — unknown in this analysis"),
    ("known_post_game", [], "None in this analysis. Visibility or permission alone"),
    ("known_post_game", ["S9", "H7"], "Explicitly supplied post-game Skat knowledge was used"),
))
def test_genuine_post_game_permission_is_not_concrete_skat_use(visibility, cards, meaning):
    request = score_review_request()
    request.update(skat_visibility=visibility, skat=cards)
    execution = execute(parse_request(request))
    assert execution.result.document["information_policy_summary"]["known_post_game_skat_allowed"]
    html = normal_result(execution)
    assert meaning in html
    assert "Saved situation before this recorded Card" not in html


@pytest.mark.parametrize("cards,meaning", (
    ([], "None in this analysis. Visibility or permission alone"),
    (["S9", "H7"], "Supplied Cards known to the declarer were used"),
))
def test_scalar_declarer_skat_visibility_requires_concrete_cards(
    immediate_execution, cards, meaning,
):
    document = immediate_execution.result.to_dict()["document"]
    document["position"].update(player_role="declarer", skat=cards)
    document["information_policy_summary"].update(skat_visibility="known_to_declarer")
    html = normal_result(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert meaning in html


def test_defensive_timeout_none_keeps_diagnostic_baseline_separate(immediate_execution):
    document = immediate_execution.result.to_dict()["document"]
    document["recommendation_method_summary"] = {
        "requested_method": "information_set_search", "effective_method": "none"}
    document["recommendation"]["card"] = None
    document["information_set_search_result"] = {
        "status": "timeout", "stop_reason": "wall_clock_timeout", "recommended_card": None}
    html = normal_result(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert "No recommendation was produced" in html
    assert "time limit was reached; coverage is incomplete" in html
    assert "No diagnostic comparison is used as a replacement recommendation" in html
    assert "Current-Trick evaluation" not in html and "Samples per Card" not in html


@pytest.mark.parametrize("role,cards,meaning", (
    ("declarer", [], "None in this analysis"),
    ("declarer", ["C7", "D8"], "Supplied Cards known to the declarer were used"),
    ("defender", ["C7", "D8"], "None in this analysis"),
))
def test_genuine_local_visibility_not_privileged_input_skat(role, cards, meaning):
    request = {
        "game_type": "grand", "player_role": role,
        "declarer_player": "me" if role == "declarer" else "left",
        "player_position": "middlehand", "trick_leader": "me", "next_player": "me",
        "hand": ["SA", "S10", "S9"], "current_trick": [], "played_cards": [],
        "completed_tricks": [], "declarer_points": 0, "defender_points": 0,
        "use_basic_opponent_strategy": True, "game_end_reason": "not_ended",
        "skat": cards, "skat_visibility": "known_to_declarer", "analysis_mode": "live_decision",
        "left_hand_size": 3, "right_hand_size": 3, "sample_count": 20, "random_seed": 42,
    }
    execution = execute(parse_request(request))
    assert meaning in normal_result(execution)
    if role == "defender":
        assert execution.result.document["position"]["skat"] == ()


def test_scalar_search_counts_keep_units_without_arithmetic(routed_execution):
    requested, execution = routed_execution
    if requested != "minimax":
        return
    document = execution.result.to_dict()["document"]
    document["bounded_search_result"]["consumed_budget"].update(
        selected_world_count=5, completed_world_count=0,
        sampled_world_count=5, unique_sampled_world_count=2)
    document["recommendation_method_summary"]["effective_method"] = "none"
    document["recommendation"]["card"] = None
    document["bounded_search_result"].update(status="partial", recommended_card=None,
                                            stop_reason="node_budget_exhausted")
    document["bounded_search_result"]["requested_budget"].update(
        max_selected_worlds=8, max_sampled_worlds=8)
    document["bounded_search_result"]["world_coverage"] = "sampled_compatible_worlds"
    presentation = build_result_presentation_v1(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    technical = {d.label: d.value for d in presentation.sections[-1].details}
    assert [technical[k] for k in ("Selected worlds", "Completed worlds", "Sampled worlds",
                                  "Unique sampled worlds")] == ["5", "0", "5", "2"]
    assert technical["Maximum selected worlds"] == "8"
    html = normal_result(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert "Repeated draws retain their weight" in html and "not exhaustive coverage" in html
    assert "Samples per Card" not in html
