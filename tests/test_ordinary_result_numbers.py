"""Controlled retained scalars test display policies, not successful Search execution."""

import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from test_candidate_comparison_layout import assert_candidates
from test_equal_best_immediate import scalar_document, scalar_values
from test_guided_frontend_result_presentation import _execution, _position_document

from skatmind.api.v1 import WorkflowV1
from skatmind.app_web.match_report_rendering import render_match_reports_v1
from skatmind.app_web.render_locale import localized_render
from skatmind.app_web.result_immediate import retained_immediate_best_cards
from skatmind.app_web.result_localization import result_label
from skatmind.app_web.result_presentation import build_result_presentation_v1
from skatmind.app_web.result_rendering import render_result_presentation_v1
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.post_game_review import build_post_game_review_summary


@pytest.mark.parametrize("method,source", (
    ("immediate_expected_value", "analysis_report"),
    ("compatible_world_minimax_v1", "bounded_search_result"),
    ("bounded_information_set_policy_search_v1", "information_set_search_result"),
))
def test_retained_scalar_precision_percentages_and_concurrent_locale_isolation(method, source):
    document = _position_document()
    document["recommendation_method_summary"]["effective_method"] = method
    prose = "Version 1.25; ID 0.125; file-3.14.json; 2026-10-28T12:34:56.789Z."
    document["recommendation"]["reason"] = prose
    scalars = ((0.125, -1.23456789, 1.23456789e-7),
               (0.9999999, -0.0, 0), (True, None, "literal 1.25"))
    if source == "analysis_report":
        document[source] = [dict(card=card, is_recommended=index == 1,
            win_rate=rate, expected_point_swing=score, average_trick_points=margin)
            for index, (card, (rate, score, margin)) in enumerate(
                zip(("H9", "S7", "D7"), scalars, strict=True), 1)]
    else:
        document[source] = {"status": "complete", "candidate_results": [dict(
            card=card, rank=index, is_recommended=index == 1, completed_world_count=1000,
            local_contract_success_rate=rate, mean_local_side_game_score=score,
            mean_local_side_card_point_margin=margin)
            for index, (card, (rate, score, margin)) in enumerate(
                zip(("H9", "S7", "D7"), scalars, strict=True), 1)]}
    retained = _execution(WorkflowV1.POSITION_ANALYSIS, document)
    original = retained.result.to_dict()
    barrier = Barrier(2)

    @localized_render
    def render():
        barrier.wait(timeout=10)
        presentation = build_result_presentation_v1(retained)
        return presentation, render_result_presentation_v1(presentation)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for _ in range(3):
            german, english = (pool.submit(render, locale=locale) for locale in ("de", "en"))
            for locale, future in (("de", german), ("en", english)):
                presentation, html = future.result(timeout=15)
                unavailable = text(locale, "status.unavailable")
                metrics = (["12,50%", "-1,23457", "1,23457e-07"] if locale == "de" else
                           ["12.50%", "-1.23457", "1.23457e-07"])
                endpoint = "100,00%" if locale == "de" else "100.00%"
                expected = []
                for index, (card, values) in enumerate(zip(("H9", "S7", "D7"), (
                    metrics, [endpoint, "-0", "0"], [unavailable, unavailable, "literal 1.25"]),
                    strict=True), 1):
                    prefix = [card]
                    if source != "analysis_report":
                        prefix += [str(index)]
                    prefix += [text(locale,
                        "common.answer.yes" if index == 1 else "common.answer.no")]
                    if source != "analysis_report":
                        prefix += ["1000"]
                    expected.append(prefix + values)
                assert_candidates(html, [localized_render(result_label)(column, locale=locale)
                    for column in presentation.sections[2].tables[0].columns], expected)
                assert prose in html
    # Request-local rendering restores the default English projection.
    assert build_result_presentation_v1(retained).sections[2].tables[0].rows[0][-3:] == (
        "12.50%", "-1.23457", "1.23457e-07")
    assert retained.result.to_dict() == original
    assert document == original["document"]


@pytest.mark.parametrize("value,english,german", (
    (1.125, "1.12", "1,12"), (-1.125, "-1.12", "-1,12"),
    (0.0, "0.00", "0,00"), (5.999, "6.00", "6,00"),
))
def test_immediate_tie_explanation_and_cells_keep_python_two_decimal_rounding(
    value, english, german,
):
    document = scalar_document(scalar_values((value, value)))
    retained = _execution(WorkflowV1.POSITION_ANALYSIS, document)
    for locale, expected in (("de", german), ("en", english), ("de", german)):
        presentation = build_result_presentation_v1(retained, locale=locale)
        assert [row[3] for row in presentation.sections[2].tables[0].rows] == [expected] * 2
        assert [row[1] for row in presentation.sections[2].tables[0].rows] == ["equal_best"] * 2
        html = render_result_presentation_v1(presentation, locale=locale)
        assert text(locale, "result.immediate.equal_points", value=expected) in html
    assert retained.result.to_dict()["document"] == document


def test_match_point_precision_preserves_raw_rates_signed_zero_booleans_and_literal_text():
    rows = [dict(card="C7", expected_point_swing=-1.23456789, win_rate=1.23456789e-7),
            dict(card="C8", expected_point_swing=-0.0, win_rate=False),
            dict(card="C9", expected_point_swing="literal 1.25", win_rate=None)]
    state = {"reports": [], "selected_report": {"report_kind": "decision_analysis",
        "details": {"immediate_candidate_values": rows}},
        "download_availability": {"report_result": False}}
    original = copy.deepcopy(state)
    def render(locale):
        html = render_match_reports_v1(state, locale)
        assert_candidates(html, [text(locale, key) for key in (
            "validation.field.card", "result.point_swing", "result.win_rate")], [
            [f'{card_name(locale, "C7")} (C7)',
             "-1,23" if locale == "de" else "-1.23",
             "1,23456789e-07" if locale == "de" else "1.23456789e-07"],
            [f'{card_name(locale, "C8")} (C8)', "-0,00" if locale == "de" else "-0.00", "False"],
            [f'{card_name(locale, "C9")} (C9)', "literal 1.25",
             text(locale, "status.unavailable")]])
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(render, ("de", "en", "de") * 3))
    assert state == original


@pytest.mark.parametrize("value,expected", (
    (10.23, "10.23"), (9.95, "9.95"), (5.44, "5.44"), (2.96, "2.96"),
    (1.125, "1.12"), (-1.125, "-1.12"), (1.375, "1.38"), (2.675, "2.67"),
    (0, "0.00"), (7, "7.00"), (-4, "-4.00"), (0.0, "0.00"), (-0.0, "-0.00"),
    (-0.004, "-0.00"), (None, None), (True, "True"), (False, "False"),
    ("literal 1.25", "literal 1.25"), ("2.0599999999999996", "2.0599999999999996"),
))
def test_match_point_policy_keeps_defensive_values_and_independent_rate_precision(value, expected):
    rows = [dict(card=card, expected_point_swing=value, win_rate=rate)
            for card, rate in (("CQ", 0.125), ("C10", 1.0), ("C8", 0), ("C7", 0.0))]
    state = {"reports": [], "selected_report": {"report_kind": "decision_analysis",
        "details": {"immediate_candidate_values": rows}},
        "download_availability": {"report_result": False}}
    original = copy.deepcopy(state)
    for locale in ("de", "en", "de"):
        points = (text(locale, "status.unavailable") if expected is None else
                  expected.replace(".", ",") if locale == "de" and type(value) in {int, float}
                  else expected)
        assert_candidates(render_match_reports_v1(state, locale), [text(locale, key) for key in (
            "validation.field.card", "result.point_swing", "result.win_rate")], [
            [f'{card_name(locale, "CQ")} (CQ)', points, "0,125" if locale == "de" else "0.125"],
            [f'{card_name(locale, "C10")} (C10)', points, "1,0" if locale == "de" else "1.0"],
            [f'{card_name(locale, "C8")} (C8)', points, "0"],
            [f'{card_name(locale, "C7")} (C7)', points, "0,0" if locale == "de" else "0.0"]])
    assert state == original


def test_match_rounding_collision_preserves_distinct_scores_order_and_recommendation():
    # Arithmetic-only retained fixture: both displayed scores round to 1.24.
    document = scalar_document(scalar_values((1.2421875, 1.240234375)))
    rows = document["analysis_report"]
    review = build_post_game_review_summary("SJ", rows, "grand", "defender")
    assert retained_immediate_best_cards(document) == ("CJ",)
    assert [row["expected_point_swing"] for row in rows] == [1.2421875, 1.240234375]
    assert [row["is_recommended"] for row in rows] == [True, False]
    assert review["better_card_count"] == 1 and review["actual_card_rank"] == 2
    assert review["expected_point_swing_difference"] > 0
    state = {"reports": [], "selected_report": {"report_kind": "decision_analysis",
        "details": {"recommendation": document["recommendation"], "post_game_review": review,
                    "immediate_candidate_values": rows}},
        "download_availability": {"report_result": False}}
    original = copy.deepcopy(state)
    for locale in ("de", "en", "de"):
        html = render_match_reports_v1(state, locale)
        points = "1,24" if locale == "de" else "1.24"
        assert_candidates(html, [text(locale, key) for key in (
            "validation.field.card", "result.point_swing", "result.win_rate")], [
            [f'{card_name(locale, "CJ")} (CJ)', points, "0,0" if locale == "de" else "0.0"],
            [f'{card_name(locale, "SJ")} (SJ)', points, "0,1" if locale == "de" else "0.1"]])
        recommendation = html.split('class="workflow-table-scroll')[0]
        assert f'{card_name(locale, "CJ")} (CJ)' in recommendation
        assert f'{card_name(locale, "SJ")} (SJ)' not in recommendation
        assert retained_immediate_best_cards(document) == ("CJ",)
    assert state == original
