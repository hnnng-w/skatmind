"""Scalar presentation fixtures, not assertions about a preferred engine move."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from html import unescape

import pytest

from skatmind.api.v1 import ExecutionResultV1, ResultDocumentV1, WorkflowV1
from skatmind.app_web.render_locale import localized_render
from skatmind.app_web.result_presentation import build_result_presentation_v1
from skatmind.app_web.result_rendering import render_result_presentation_v1
from skatmind.app_web.rollout_result_numbers import decimal_number, simulation_success
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


def opening_result():
    margins = {"CJ": 10118, "C9": 9320, "C8": 9320, "C7": 9320, "SA": 9204,
               "S10": 9200, "CQ": 8666, "CK": 8466, "C10": 7266, "CA": 7066}
    return {
        "recommendation_method_summary": {"requested_method": "whole_game_rollout",
                                          "effective_method": "whole_game_rollout"},
        "whole_game_rollout_result": {
            "objective": "played_game_goal", "status": "complete", "stop_reason": "completed",
            "completed_common_worlds": 100, "requested_worlds": 100,
            "ranked_cards": list(margins), "tied_best_cards": ["CJ"], "recommended_card": "CJ",
            "local_side": "declarer", "source_fingerprint": "a" * 64,
            "settings": {"random_seed": 0, "requested_worlds": 100},
            "policy": {"profile": "side_aware_baseline", "version": 1}, "work": {},
            "candidates": [{"card": card, "completed_samples": 100, "local_success_count": 100,
                "total_local_card_point_margin": margin, "total_local_game_score": None,
                "sampled_local_success_fraction": 1.0,
                "mean_final_local_card_point_margin": margin / 100,
                "mean_local_game_score": None} for card, margin in margins.items()],
        },
        "whole_game_rollout_comparison": {"actual_card": "CJ", "best_card": "CJ",
            "status": "equal_complete_objective", "responsible_metric": None,
            "all_primary_success_equal": True, "display_order_only": False},
    }


def render(document, locale):
    execution = ExecutionResultV1(result=ResultDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS, document=document))
    presentation = build_result_presentation_v1(
        execution, information_source="session_checkpoint", locale=locale)
    return presentation, unescape(render_result_presentation_v1(presentation, locale=locale))


def tied_result(*, objective="played_game_goal", actual="C7",
                metric="total_local_card_point_margin"):
    """Completed aggregate fixture: three exact best cards and one lower candidate."""
    document = opening_result()
    result = document["whole_game_rollout_result"]
    cards = ["C9", "C8", "C7", "SA"]
    rows = {row["card"]: row for row in result["candidates"]}
    result.update(objective=objective, recommended_card="C9", tied_best_cards=cards[:3],
                  ranked_cards=cards, candidates=[rows[card] for card in cards])
    for row in result["candidates"]:
        row.update(total_local_card_point_margin=10520,
                   mean_final_local_card_point_margin=105.2)
        if objective == "complete_settlement":
            row.update(total_local_game_score=4800, mean_local_game_score=48.0)
    lower = result["candidates"][-1]
    lower[metric] -= 1 if metric == "local_success_count" else 100
    lower.update(sampled_local_success_fraction=lower["local_success_count"] / 100,
                 mean_final_local_card_point_margin=lower["total_local_card_point_margin"] / 100,
                 mean_local_game_score=None if objective == "played_game_goal" else
                 lower["total_local_game_score"] / 100)
    member = actual in result["tied_best_cards"]
    document["whole_game_rollout_comparison"].update(
        actual_card=actual, best_card="C9", display_order_only=member and actual != "C9",
        status="equal_complete_objective" if member else "lower_primary_success" if
        metric == "local_success_count" else "lower_secondary_outcome",
        responsible_metric=None if member else metric,
        all_primary_success_equal=metric != "local_success_count")
    return document


def primary_summary(html, *, prefix="result"):
    """Inspect the first visible recommendation details, never the alternatives."""
    section = unescape(html).split(f'<section aria-labelledby="{prefix}-section-2">', 1)[1]
    return section.split('<dl class="result-details">', 1)[1].split('</dl>', 1)[0]


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("objective", ["played_game_goal", "complete_settlement"])
@pytest.mark.parametrize("actual", ["C9", "C7", "SA"])
def test_primary_summary_shows_authoritative_full_set_and_actual_membership(
    locale, objective, actual,
):
    document = tied_result(objective=objective, actual=actual)
    before = deepcopy(document)
    presentation, html = render(document, locale)
    cards = ", ".join(card_name(locale, card) + f" ({card})" for card in ["C9", "C8", "C7"])
    details = presentation.sections[1].details
    assert details[0].value == cards
    assert details[0].label == "Equally recommended cards"
    summary = primary_summary(html)
    assert f'<dt>{text(locale, "rollout.recommended_plural")}</dt><dd>{cards}</dd>' in summary
    played = card_name(locale, actual) + f" ({actual})"
    if actual != "SA":
        played = text(locale, "rollout.played_tied", card=played)
        assert text(locale, "rollout.comparison.equal_complete_objective") in html
    assert f'<dt>{text(locale, "rollout.played")}</dt><dd>{played}</dd>' in summary
    visible = html.split('<section class="analysis-technical"', 1)[0]
    assert text(locale, "rollout.recommended") not in visible
    assert text(locale, "rollout.tied_best") in visible
    table, = presentation.sections[2].tables
    assert [row[0].split("(")[1].split(")")[0] for row in table.rows] == ["C9", "C8", "C7", "SA"]
    assert all(text(locale, "rollout.marker.tied") in row[0] for row in table.rows[:3])
    assert text(locale, "rollout.marker.tied") not in table.rows[3][0]
    assert document == before


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("objective,metric,preference", [
    ("played_game_goal", "local_success_count", "local_success_count"),
    ("played_game_goal", "total_local_card_point_margin", "total_local_card_point_margin"),
    ("complete_settlement", "local_success_count", "local_success_count"),
    ("complete_settlement", "total_local_game_score", "total_local_game_score"),
    ("complete_settlement", "total_local_card_point_margin", "settlement_margin"),
])
def test_lower_actual_compares_with_group_using_exact_decisive_metric(
    locale, objective, metric, preference,
):
    document = tied_result(objective=objective, actual="SA", metric=metric)
    presentation, html = render(document, locale)
    actual = card_name(locale, "SA") + " (SA)"
    goal = text(locale, "rollout.goal." + objective)
    items = presentation.sections[1].items
    assert text(locale, "rollout.preference.group_" + preference, other=actual, goal=goal) in items
    status = document["whole_game_rollout_comparison"]["status"]
    values = {"goal": goal} if metric == "local_success_count" else {
        "metric": text(locale, "rollout.metric." + metric)}
    assert text(locale, "rollout.comparison.group_" + status, actual=actual, **values) in items
    assert not any("(C9)" in item for item in items)
    assert text(locale, "rollout.played_tied", card=actual) not in primary_summary(html)
    assert text(locale, "rollout.comparison.equal_complete_objective") not in items


@pytest.mark.parametrize("locale,margin", [("de", "101,18"), ("en", "101.18")])
def test_supplied_case_uses_direct_labels_compact_table_and_native_details(
    locale, margin,
):
    document = opening_result()
    before = deepcopy(document)
    presentation, html = render(document, locale)
    assert text(locale, "rollout.recommended") in html and text(locale, "rollout.played") in html
    success = text(locale, "rollout.number.success", successes=100, samples=100, percentage="100")
    assert success in html and margin in html
    table, = presentation.sections[2].tables
    assert len(table.columns) == 3 and len(table.rows) == 10
    assert [row[0].split("(")[1].split(")")[0] for row in table.rows] == (
        document["whole_game_rollout_result"]["ranked_cards"])
    assert f'>{text(locale, "rollout.calculation_details")}</summary>' in html
    assert '<details class="technical-details">' in html
    assert text(locale, "result.immediate.lower_evaluated") not in html
    assert "1.000" not in html
    visible, technical = html.split('<section class="analysis-technical"', 1)
    assert text(locale, "rollout.limits") in visible
    assert text(locale, "rollout.played_goal_limit") in visible
    assert text(locale, "rollout.source") not in visible
    assert text(locale, "rollout.source") in technical
    assert "side_aware_baseline" not in visible and "side_aware_baseline" in technical
    assert text(locale, "rollout.matches", actual=card_name(locale, "CJ") + " (CJ)") in visible
    summary = primary_summary(html)
    card = card_name(locale, "CJ") + " (CJ)"
    assert f'<dt>{text(locale, "rollout.recommended")}</dt><dd>{card}</dd>' in summary
    assert f'<dt>{text(locale, "rollout.played")}</dt><dd>{card}</dd>' in summary
    assert text(locale, "rollout.recommended_plural") not in visible
    assert text(locale, "rollout.all_succeeded", candidates=10, samples=100,
                goal=text(locale, "rollout.goal.played_game_goal")) in visible
    assert document == before


def two_cards(*, objective="played_game_goal", successes=(100, 100),
              margins=(10118, 9204), scores=(None, None), tied=False, actual="SA"):
    document = opening_result()
    result = document["whole_game_rollout_result"]
    rows = {row["card"]: row for row in result["candidates"]}
    result.update(objective=objective, ranked_cards=["CJ", "SA"],
                  tied_best_cards=["CJ", "SA"] if tied else ["CJ"],
                  candidates=[rows["CJ"], rows["SA"]])
    for row, success, margin, score in zip(result["candidates"], successes,
                                          margins, scores, strict=True):
        row.update(local_success_count=success, sampled_local_success_fraction=success / 100,
                   total_local_card_point_margin=margin,
                   mean_final_local_card_point_margin=margin / 100,
                   total_local_game_score=score,
                   mean_local_game_score=None if score is None else score / 100)
    comparison = document["whole_game_rollout_comparison"]
    status = "equal_complete_objective" if tied or actual == "CJ" else (
        "lower_primary_success" if successes[0] != successes[1] else "lower_secondary_outcome")
    comparison.update(actual_card=actual, status=status, display_order_only=tied and actual != "CJ",
                      all_primary_success_equal=successes[0] == successes[1],
                      responsible_metric=None if status == "equal_complete_objective" else
                      "local_success_count" if status == "lower_primary_success" else
                      "total_local_game_score" if scores[0] != scores[1] else
                      "total_local_card_point_margin")
    return document


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("changes,metric", [
    ({"successes": (75, 50), "margins": (-1200, 2000)}, "local_success_count"),
    ({}, "total_local_card_point_margin"),
    ({"objective": "complete_settlement", "scores": (4800, 2400),
      "margins": (1000, 2000)}, "total_local_game_score"),
    ({"objective": "complete_settlement", "scores": (4800, 4800)}, "settlement_margin"),
    ({"objective": "complete_settlement", "successes": (75, 50),
      "scores": (2400, 4800)}, "local_success_count"),
])
def test_exact_decisive_metric_and_actual_comparison(locale, changes, metric):
    document = two_cards(**changes)
    before = deepcopy(document)
    presentation, html = render(document, locale)
    normal = html.split('<section class="analysis-technical"', 1)[0]
    best = card_name(locale, "CJ") + " (CJ)"
    actual = card_name(locale, "SA") + " (SA)"
    goal = text(locale, "rollout.goal." + document["whole_game_rollout_result"]["objective"])
    assert text(locale, "rollout.preference." + metric,
                best=best, other=actual, goal=goal) in normal
    if metric == "local_success_count":
        expected = text(locale, "rollout.comparison.lower_primary_success",
                        actual=actual, best=best, goal=goal)
    else:
        expected = text(locale, "rollout.comparison.lower_secondary_outcome",
            actual=actual, best=best, metric=text(locale, "rollout.metric." + (
                "total_local_card_point_margin" if metric == "settlement_margin" else metric)))
    assert expected in normal
    assert f'<dt>{text(locale, "rollout.recommended")}</dt><dd>{best}</dd>' in primary_summary(html)
    assert f'<dt>{text(locale, "rollout.played")}</dt><dd>{actual}</dd>' in primary_summary(html)
    assert text(locale, "rollout.recommended_plural") not in normal
    table, = presentation.sections[2].tables
    assert len(table.columns) == (
        4 if changes.get("objective") == "complete_settlement" else 3)
    assert document == before


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("actual", ["CJ", "SA"])
def test_full_ties_have_text_markers_and_no_canonical_advantage(locale, actual):
    document = two_cards(tied=True, margins=(10000, 10000), actual=actual)
    presentation, html = render(document, locale)
    normal = html.split('<section class="analysis-technical"', 1)[0]
    assert text(locale, "rollout.display_order") in normal
    rows = presentation.sections[2].tables[0].rows
    assert all(text(locale, "rollout.marker.tied") in row[0] for row in rows)
    assert sum(text(locale, "rollout.marker.played") in row[0] for row in rows) == 1
    assert document["whole_game_rollout_result"]["ranked_cards"] == ["CJ", "SA"]


@pytest.mark.parametrize("locale", ["de", "en"])
def test_defender_orientation_and_negative_zero_display(locale):
    document = two_cards(margins=(-1234, -2000))
    document["whole_game_rollout_result"]["local_side"] = "defenders"
    _, html = render(document, locale)
    normal = html.split('<section class="analysis-technical"', 1)[0]
    assert text(locale, "rollout.party.defenders") in normal
    assert ("-12,34" if locale == "de" else "-12.34") in normal
    assert text(locale, "rollout.party.declarer") not in normal


@pytest.mark.parametrize("locale", ["de", "en"])
def test_equal_display_rounding_does_not_create_a_tie(locale):
    document = two_cards(margins=(101182, 101180))
    result = document["whole_game_rollout_result"]
    for row in result["candidates"]:
        row.update(completed_samples=1000, local_success_count=1000,
                   mean_final_local_card_point_margin=row["total_local_card_point_margin"] / 1000)
    result.update(completed_common_worlds=1000, requested_worlds=1000)
    presentation, html = render(document, locale)
    summary = primary_summary(html)
    best, actual = card_name(locale, "CJ") + " (CJ)", card_name(locale, "SA") + " (SA)"
    assert f'<dt>{text(locale, "rollout.recommended")}</dt><dd>{best}</dd>' in summary
    assert f'<dt>{text(locale, "rollout.played")}</dt><dd>{actual}</dd>' in summary
    assert text(locale, "rollout.recommended_plural") not in summary
    rows = presentation.sections[2].tables[0].rows
    assert rows[0][2] == rows[1][2] == ("101,18" if locale == "de" else "101.18")
    assert text(locale, "rollout.marker.recommended") in rows[0][0]
    assert text(locale, "rollout.marker.tied") not in str(rows)
    assert text(locale, "rollout.marker.recommended") not in rows[1][0]
    assert result["ranked_cards"] == ["CJ", "SA"] and result["tied_best_cards"] == ["CJ"]


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("status,reason", [("unavailable", "missing_terminal_utility_inputs"),
    ("partial", "transition_budget_exhausted"), ("timeout", "wall_clock_timeout"),
    ("cancelled", "cancelled")])
def test_incomplete_keeps_reason_coverage_and_no_table_or_recommendation(locale, status, reason):
    document = opening_result()
    document["whole_game_rollout_result"].update(status=status, stop_reason=reason,
        completed_common_worlds=0, ranked_cards=[], tied_best_cards=[], recommended_card=None)
    document["whole_game_rollout_comparison"].update(status="unavailable", best_card=None)
    presentation, html = render(document, locale)
    normal = html.split('<section class="analysis-technical"', 1)[0]
    assert not presentation.sections[2].tables
    assert text(locale, "rollout.no_ranking") in normal
    assert text(locale, "rollout.reason." + reason) in normal
    assert text(locale, "rollout.coverage", completed=0, requested=100) in normal
    assert text(locale, "rollout.recommended") not in normal
    assert text(locale, "rollout.recommended_plural") not in normal
    assert len(presentation.sections[1].details) == 1
    played = card_name(locale, "CJ") + " (CJ)"
    assert f'<dt>{text(locale, "rollout.played")}</dt><dd>{played}</dd>' in primary_summary(html)


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("value,expected", [(0, "0.00"), (-0.0, "0.00"), (-0.004, "0.00"),
    (-12.345, "-12.34"), (2.675, "2.68"), (101.18, "101.18"), (None, None),
    (True, None), ("92.04", None), (float("inf"), None), (float("nan"), None)])
def test_decimal_formatting(value, expected, locale):
    actual = localized_render(decimal_number)(value, locale=locale)
    assert actual == (text(locale, "status.unavailable") if expected is None else
                      expected.replace(".", "," if locale == "de" else "."))


@pytest.mark.parametrize("locale", ["de", "en"])
@pytest.mark.parametrize("successes,samples,percentage", [(0, 100, "0"), (100, 100, "100"),
    (1, 3, "33.33"), (999, 1000, "99.9"), (99999, 100000, "99.999"),
    (1, 1000000, "0.0001"), (0, 0, None), (None, 100, None), (-1, 100, None)])
def test_success_counts_percentages_and_endpoints(locale, successes, samples, percentage):
    actual = localized_render(simulation_success)(successes, samples, locale=locale)
    expected = text(locale, "status.unavailable") if percentage is None else text(
        locale, "rollout.number.success", successes=successes, samples=samples,
        percentage=percentage.replace(".", "," if locale == "de" else "."))
    assert actual == expected


def test_concurrent_locales_do_not_share_mutable_number_format_state():
    locales = ["de", "en"] * 10
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda locale: localized_render(decimal_number)(
            92.04, locale=locale), locales))
    assert results == ["92,04", "92.04"] * 10


@pytest.mark.parametrize("locale", ["de", "en"])
def test_equal_zero_success_is_not_the_all_successful_explanation(locale):
    document = two_cards(successes=(0, 0), margins=(-1000, -2000))
    presentation, html = render(document, locale)
    normal = html.split('<section class="analysis-technical"', 1)[0]
    assert text(locale, "rollout.primary_tie") in normal
    assert text(locale, "rollout.number.success",
                successes=0, samples=100, percentage="0") in normal
    assert len(presentation.sections[2].tables[0].rows) == 2
    assert text(locale, "rollout.all_succeeded", candidates=2, samples=100,
                goal=text(locale, "rollout.goal.played_game_goal")) not in normal


@pytest.mark.parametrize("locale", ["de", "en"])
def test_sole_card_and_unavailable_cell_do_not_invent_an_alternative_or_zero(locale):
    document = opening_result()
    result = document["whole_game_rollout_result"]
    result["candidates"] = [row for row in result["candidates"] if row["card"] == "CJ"]
    result["ranked_cards"] = ["CJ"]
    result["candidates"][0]["mean_final_local_card_point_margin"] = None
    presentation, html = render(document, locale)
    assert text(locale, "rollout.only_card") in html
    table, = presentation.sections[2].tables
    assert len(table.rows) == 1 and table.rows[0][2] == text(locale, "status.unavailable")
