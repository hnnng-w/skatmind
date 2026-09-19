"""Exact scalar semantics are separate from the legal public R10 execution."""

from __future__ import annotations

import copy
import re

import pytest
from test_guided_frontend_result_presentation import (
    _execution,
    assert_summary_points,
    score_review_request,
)

from skatmind.analysis_report import build_card_analysis_report_from_values, build_strategic_summary
from skatmind.api.v1 import WorkflowV1, execute, parse_request
from skatmind.app_web.result_immediate import retained_immediate_best_cards
from skatmind.app_web.result_presentation import build_result_presentation_v1
from skatmind.app_web.result_rendering import render_result_presentation_v1
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.game_state import GameState
from skatmind.immediate_explanation import build_equal_best_immediate_explanation
from skatmind.objective_utility import (
    calculate_expected_objective_utility,
    calculate_null_trick_objective_utility,
    choose_best_card_by_expected_objective,
    get_best_cards_by_expected_objective,
)
from skatmind.post_game_review import build_post_game_review_summary


@pytest.fixture(scope="module")
def r10_execution():
    return execute(parse_request(score_review_request()))


def assert_visible_equal_best(html, locale):
    normal = re.search(
        r'<section aria-labelledby="result-section-2">(.*?)'
        r'<section aria-labelledby="result-section-4">', html, re.S,
    ).group(1)
    assert "<details" not in normal
    assert card_name(locale, "CJ") in normal and card_name(locale, "SJ") in normal
    assert text(locale, "result.immediate.actual_equal", card=card_name(locale, "SJ")) in normal
    recommendation = normal.split('<section aria-labelledby="result-section-3">')[0]
    assert text(locale, "result.immediate.equal_points", value="6.00") in recommendation
    assert text(locale, "result.value.optimal") in normal
    assert normal.count("6.00") >= 2
    assert normal.count("<table>") == 1
    table = normal.split("<table>", 1)[1]
    assert f'>{text(locale, "common.answer.yes")}<' not in table
    assert f'>{text(locale, "common.answer.no")}<' not in table
    assert_summary_points(html, locale, 14, 29)


def test_real_public_r10_export_explains_equality(r10_execution):
    result = r10_execution.result.document
    assert result["recommendation"]["card"] == "CJ"
    assert [row["card"] for row in result["analysis_report"]] == ["CJ", "SJ"]
    assert [row["is_recommended"] for row in result["analysis_report"]] == [True, False]
    assert [row["expected_point_swing"] for row in result["analysis_report"]] == [6.0, 6.0]
    review = result["post_game_review_summary"]
    assert (review["recommended_card_rank"], review["actual_card_rank"]) == (1, 2)
    assert review["decision_quality"] == "optimal"
    assert review["better_card_count"] == review["expected_point_swing_difference"] == 0
    for prose in (result["recommendation"]["reason"], result["strategic_summary"]):
        assert "CJ, SJ" in prose and "equally best" in prose
        assert "stable legal-card order" in prose
        assert "advantage" not in prose


@pytest.mark.parametrize("locale", ("de", "en"))
def test_real_public_r10_normal_statuses_agree(r10_execution, locale):
    presentation = build_result_presentation_v1(r10_execution, locale=locale)
    assert presentation.sections[2].tables[0].columns[1] == "Evaluation"
    assert [row[1] for row in presentation.sections[2].tables[0].rows] == [
        "equal_best", "equal_best"]
    assert_visible_equal_best(render_result_presentation_v1(presentation, locale=locale), locale)


def scalar_values(swings):
    """Arithmetic-only fixtures, not a legal simulated deal."""
    return {
        card: {"win_rate": index / 10, "average_trick_points": 20.0 + index,
               "average_points_won": max(swing, 0) + index,
               "average_points_lost": max(-swing, 0) + index}
        for index, (card, swing) in enumerate(zip(("CJ", "SJ", "HJ", "DJ"), swings, strict=False))
    }


@pytest.mark.parametrize("swings,expected", [
    ((6.0, 6.0), ("CJ", "SJ")), ((6.0, 6.0, 6.0, 1.0), ("CJ", "SJ", "HJ")),
    ((6.0,) * 4, ("CJ", "SJ", "HJ", "DJ")), ((0.0, 0.0), ("CJ", "SJ")),
    ((-6.0, -6.0, -9.0), ("CJ", "SJ")), ((6.0, 5.0, 5.0), ("CJ",)),
    ((6.0, 5.999), ("CJ",)), ((6.0,), ("CJ",)), ((), ()),
])
def test_scalar_exact_maxima_prose_order_and_unchanged_review(swings, expected):
    values = scalar_values(swings)
    original = copy.deepcopy(values)
    assert get_best_cards_by_expected_objective(values, "grand", "defender") == expected
    report = build_card_analysis_report_from_values(
        GameState(game_type="grand", player_role="defender", hand=list(values),
                  current_trick=[]), values)
    summary = build_strategic_summary(report, "grand", "defender")
    explanation = build_equal_best_immediate_explanation(values, "grand", "defender")
    if len(expected) > 1:
        assert ", ".join(expected) in explanation
        assert summary == "Strategic summary: " + explanation
        assert "least damaging" not in summary and "advantage" not in summary
        for index, actual in enumerate(expected, 1):
            review = build_post_game_review_summary(actual, report, "grand", "defender")
            assert review["actual_card_rank"] == index
            assert review["decision_quality"] == "optimal"
            assert review["better_card_count"] == review["expected_point_swing_difference"] == 0
    else:
        assert explanation is None
        assert "equally best" not in summary
    if expected:
        assert choose_best_card_by_expected_objective(values, "grand", "defender") == expected[0]
        assert [row["is_recommended"] for row in report] == [True] + [False] * (len(values) - 1)
        assert [row["card"] for row in report] == list(values)
    assert values == original


@pytest.mark.parametrize("role", ("declarer", "defender"))
def test_scalar_null_ties_use_existing_objective_despite_different_point_swings(role):
    values = scalar_values((10.0, -2.0, 3.0))
    winner = "defenders" if role == "declarer" else "declarer"
    utility = calculate_null_trick_objective_utility(role, winner)
    for index, value in enumerate(values.values()):
        value["win_rate"] = 0.0 if index < 2 else 1.0
        value["expected_objective_utility"] = utility if index < 2 else 0.0
    assert get_best_cards_by_expected_objective(values, "null", role) == ("CJ", "SJ")
    report = build_card_analysis_report_from_values(
        GameState(game_type="null", player_role=role, hand=list(values), current_trick=[]), values)
    assert [calculate_expected_objective_utility("null", role, row) for row in report] == [1, 1, 0]
    for prose in (build_equal_best_immediate_explanation(values, "null", role),
                  build_strategic_summary(report, "null", role)):
        assert "CJ, SJ" in prose and "Null contract-objective" in prose
        assert "expected point" not in prose
        assert ("avoid taking" if role == "declarer" else "concrete declarer") in prose
    review = build_post_game_review_summary("SJ", report, "null", role, game_value=23)
    assert review["decision_quality"] == "optimal" and review["better_card_count"] == 0
    assert review["actual_card_rank"] == 2
    assert review["expected_point_swing_difference"] == 12.0
    document = scalar_document(values, "null", role)
    assert retained_immediate_best_cards(document) == ("CJ", "SJ")
    assert "expected point" not in build_equal_best_immediate_explanation(values, "null", role)


@pytest.mark.parametrize("game,role", (("grand", "defender"), ("null", "declarer"),
                                       ("null", "defender")))
def test_positive_zero_looking_gap_is_not_equality(game, role):
    values = scalar_values((6.0, 5.999))
    if game == "null":
        values["CJ"]["win_rate"], values["SJ"]["win_rate"] = 0.0, 0.0001
    report = build_card_analysis_report_from_values(
        GameState(game_type=game, player_role=role, hand=list(values), current_trick=[]), values)
    summary = build_strategic_summary(report, game, role)
    assert ("less than 0.001" if game == "null" else "less than 0.01 expected points") in summary
    assert "equally best" not in summary
    assert get_best_cards_by_expected_objective(values, game, role) == ("CJ",)
    review = build_post_game_review_summary("SJ", report, game, role, game_value=23)
    assert review["decision_quality"] == "acceptable" and review["better_card_count"] == 1
    assert review["expected_point_swing_difference"] == (
        report[0]["expected_point_swing"] - report[1]["expected_point_swing"])
    assert retained_immediate_best_cards(scalar_document(values, game, role)) == ("CJ",)


def scalar_document(values, game="grand", role="defender"):
    report = build_card_analysis_report_from_values(
        GameState(game_type=game, player_role=role, hand=list(values), current_trick=[]), values)
    return {"settings": {}, "position": {"game_type": game, "player_role": role},
            "recommendation": {"card": report[0]["card"] if report else None},
            "legal_cards": list(values), "analysis_report": report}


@pytest.mark.parametrize("invalid", (None, True, False, "6", float("nan"), float("inf"), []))
@pytest.mark.parametrize("key", ("win_rate", "average_trick_points", "average_points_won",
                                 "average_points_lost", "expected_point_swing"))
def test_defensive_scalar_candidate_values_fail_closed(key, invalid):
    document = scalar_document(scalar_values((6.0, 6.0)))
    document["analysis_report"][1][key] = invalid
    assert retained_immediate_best_cards(document) == ()


@pytest.mark.parametrize("defect", (
    "duplicate", "missing", "extra", "non_object", "double_flag", "no_flag", "bool_flag",
    "wrong_choice", "missing_metric", "unknown_card", "bad_legal", "duplicate_legal",
    "wrong_swing", "wrong_order", "null_unknown", "wrong_declaration", "unavailable",
))
def test_incomplete_or_inconsistent_candidates_never_claim_tie(defect):
    document = scalar_document(scalar_values((6.0, 6.0)))
    rows = document["analysis_report"]
    if defect == "duplicate":
        rows[1] = dict(rows[0], is_recommended=False)
    elif defect == "missing":
        rows.pop()
    elif defect == "extra":
        rows.append(dict(rows[1]))
    elif defect == "non_object":
        rows[1] = None
    elif defect == "double_flag":
        rows[1]["is_recommended"] = True
    elif defect == "no_flag":
        rows[0]["is_recommended"] = False
    elif defect == "bool_flag":
        rows[0]["is_recommended"] = 1
    elif defect == "wrong_choice":
        document["recommendation"]["card"] = "SJ"
    elif defect == "missing_metric":
        del rows[1]["win_rate"]
    elif defect == "unknown_card":
        rows[1]["card"] = "<bad>"
    elif defect == "bad_legal":
        document["legal_cards"] = ["CJ", {}]
    elif defect == "duplicate_legal":
        document["legal_cards"] = ["CJ", "CJ"]
    elif defect == "wrong_swing":
        rows[1]["expected_point_swing"] = 7.0
    elif defect == "wrong_order":
        rows[1].update(average_points_won=8, expected_point_swing=7)
    elif defect == "null_unknown":
        document["position"].update(game_type="null", player_role="unknown")
    elif defect == "wrong_declaration":
        document["game_declaration"] = {"game_type": "null"}
    elif defect == "unavailable":
        document["recommendation"]["card"] = None
    assert retained_immediate_best_cards(document) == ()


def test_multiple_recommended_flags_still_rejected():
    document = scalar_document(scalar_values((6.0, 6.0)))
    document["analysis_report"][1]["is_recommended"] = True
    with pytest.raises(ValueError, match="exactly one recommended"):
        build_post_game_review_summary("SJ", document["analysis_report"])


@pytest.mark.parametrize("defect", ("empty", "missing", "effective", "settings", "fallback",
                                    "bool", "diagnostic", "legacy_search"))
def test_inconsistent_method_evidence_fails_closed(r10_execution, defect):
    document = r10_execution.result.to_dict()["document"]
    method = {"requested_method": "immediate_expected_value",
              "effective_method": "immediate_expected_value", "search_attempted": False,
              "fallback_used": False, "fallback_method": None,
              "analysis_report_method": "immediate_expected_value"}
    document["recommendation_method_summary"] = method
    document["settings"]["recommendation_method"] = "immediate_expected_value"
    if defect == "empty":
        document["recommendation_method_summary"] = {}
    elif defect == "missing":
        del method["analysis_report_method"]
    elif defect == "effective":
        method["effective_method"] = "none"
    elif defect == "settings":
        document["settings"]["recommendation_method"] = "auto"
    elif defect == "fallback":
        method.update(requested_method="auto", fallback_used=True)
    elif defect == "bool":
        method["search_attempted"] = 0
    elif defect == "diagnostic":
        document["information_set_search_result"] = {"status": "complete"}
    elif defect == "legacy_search":
        del document["recommendation_method_summary"]
        del document["settings"]["recommendation_method"]
        document["bounded_search_result"] = {"status": "complete"}
    assert retained_immediate_best_cards(document) == ()


@pytest.mark.parametrize("method", ("immediate_expected_value", "auto", "bounded_search"))
def test_real_explicit_routing_and_diagnostic_baseline_boundary(method):
    request = score_review_request()
    request["recommendation_method"] = method
    if method != "immediate_expected_value":
        request["bounded_search_settings"] = {
            "random_seed": 0, "max_remaining_tricks": 3, "max_depth_plies": 9,
            "max_nodes": 100, "max_selected_worlds": 1, "max_sampled_worlds": 1,
            "minimum_comparable_worlds": 1, "wall_clock_timeout_ms": None,
        }
    execution = execute(parse_request(request))
    document = execution.result.document
    if method == "bounded_search":
        assert document["recommendation"]["card"] is None
        assert document["analysis_report"] == ()
        assert retained_immediate_best_cards(document) == ()
    else:
        assert retained_immediate_best_cards(document) == ("CJ", "SJ")
        if method == "auto":
            assert document["recommendation_method_summary"]["fallback_used"] is True
        assert_visible_equal_best(render_result_presentation_v1(build_result_presentation_v1(
            execution)), "en")


def test_old_retained_prose_is_presented_without_rewriting_export(r10_execution):
    document = r10_execution.result.to_dict()["document"]
    document["recommendation"]["reason"] = (
        "This card has the highest estimated immediate expected point swing: 6.00.")
    document["strategic_summary"] = (
        "Strategic summary: CJ is recommended, but the advantage over SJ is modest. "
        "The expected point swing gap is 0.00, so this position may be close.")
    retained = _execution(WorkflowV1.POSITION_ANALYSIS, document)
    before = retained.result.to_dict()
    for locale in ("de", "en"):
        assert_visible_equal_best(render_result_presentation_v1(build_result_presentation_v1(
            retained, locale=locale), locale=locale), locale)
    assert retained.result.to_dict() == before


@pytest.mark.parametrize("swings,statuses", (
    ((6.0, 6.0, 1.0), ("equal_best", "equal_best", "lower_evaluated")),
    ((6.0, 5.0, 5.0), ("best", "lower_evaluated", "lower_evaluated")),
    ((0.0, 0.0, 0.0), ("equal_best",) * 3),
    ((-6.0, -6.0), ("equal_best",) * 2),
    ((6.0,), ("best",)),
))
def test_scalar_normal_table_statuses_preserve_order_and_objective(swings, statuses):
    document = scalar_document(scalar_values(swings))
    before = copy.deepcopy(document)
    presentation = build_result_presentation_v1(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    table = presentation.sections[2].tables[0]
    assert tuple(row[1] for row in table.rows) == statuses
    assert tuple(row[0] for row in table.rows) == tuple(
        card_name("en", row["card"]) for row in document["analysis_report"])
    assert document == before


@pytest.mark.parametrize("actual", ("CJ", "SJ", None))
def test_actual_equal_best_explanation_is_based_on_retained_assessment(r10_execution, actual):
    document = r10_execution.result.to_dict()["document"]
    document["post_game_review_summary"] = build_post_game_review_summary(
        actual, document["analysis_report"], "grand", "defender")
    presentation = build_result_presentation_v1(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    details = {detail.label: detail.value for detail in presentation.sections[1].details}
    if actual is not None:
        assert text("en", "result.immediate.actual_equal", card=card_name("en", actual)) in (
            details["Immediate evaluation"])
        assert details["Decision quality"] == "optimal"
    else:
        assert "played" not in details["Immediate evaluation"]
