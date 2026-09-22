"""Single-copy presentation regressions; scalar cells are not executed Search evidence."""

import copy
from dataclasses import replace

import pytest
from test_guided_frontend_result_presentation import (
    _execution,
    _historical_document,
    _position_document,
)
from test_recording_task_focus import Hierarchy

from skatmind.api.v1 import WorkflowV1
from skatmind.app_web.match_report_rendering import render_match_reports_v1
from skatmind.app_web.result_presentation import (
    RESULT_SECTION_TITLES_V1,
    BrowserSafeResultPresentationV1,
    ResultSectionV1,
    ResultTableV1,
    build_result_presentation_v1,
)
from skatmind.app_web.result_rendering import render_result_presentation_v1
from skatmind.app_web.stateful_localization import card_name, text


def children(markup, parent, tag=None, css=None):
    return [n for n in markup.nodes if any(p is parent for p in n["parents"])
            and (tag is None or n["tag"] == tag)
            and (css is None or css in n["attrs"].get("class", "").split())]


def assert_candidates(html, columns, rows):
    """Independent literal matrix, unique identity and exact native header associations."""
    markup = Hierarchy(html)
    tables = [n for n in markup.nodes if n["tag"] == "table"]
    assert len(tables) == 1
    table, = tables
    assert table["attrs"]["class"] == "candidate-table"
    assert table["attrs"]["role"] == "table"
    caption, = children(markup, table, "caption")
    assert caption["text"]
    headings = [n for n in children(markup, table, "th") if n["attrs"].get("scope") == "col"]
    assert [n["text"] for n in headings] == columns
    assert all(n["attrs"]["role"] == "columnheader" for n in headings)
    body, = children(markup, table, "tbody")
    actual_rows = children(markup, body, "tr")
    assert len(actual_rows) == len(rows)
    for row, expected in zip(actual_rows, rows, strict=True):
        assert row["attrs"]["role"] == "row"
        cells = [n for n in markup.nodes if n["parents"] and n["parents"][-1] is row]
        assert len(cells) == len(columns)
        assert cells[0]["tag"] == "th" and cells[0]["attrs"]["scope"] == "row"
        assert cells[0]["attrs"]["role"] == "rowheader"
        for index, (cell, value) in enumerate(zip(cells, expected, strict=True)):
            label, = children(markup, cell, css="candidate-label")
            content, = children(markup, cell, css="candidate-value")
            assert label["text"] == columns[index] and label["attrs"]["aria-hidden"] == "true"
            assert content["text"] == value
            assert not any(n["tag"] in {"details", "input", "button"}
                           for n in children(markup, cell))
            assert "tabindex" not in cell["attrs"]
            expected_headers = [headings[index]["attrs"]["id"]]
            if index:
                expected_headers.insert(0, cells[0]["attrs"]["id"])
                assert cell["tag"] == "td" and cell["attrs"]["role"] == "cell"
            assert cell["attrs"]["headers"].split() == expected_headers
    ids = [n["attrs"]["id"] for n in markup.nodes if "id" in n["attrs"]]
    assert len(ids) == len(set(ids))
    assert not any(k.startswith("data-") for n in children(markup, table) for k in n["attrs"])


def presentation(table, *, workflow="position_analysis"):
    return BrowserSafeResultPresentationV1(workflow=workflow, sections=tuple(
        ResultSectionV1(title=title, tables=(table,) if title == "Alternatives" else ())
        for title in RESULT_SECTION_TITLES_V1))


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("count", (1, 2))
def test_literal_five_column_scalar_cells_are_lossless_and_labelled(locale, count):
    table = ResultTableV1(caption="Card comparisons in public Result order",
        columns=("Card", "Evaluation", "Win rate", "Expected point swing", "Average trick points"),
        rows=(("CJ", "equal_best" if count == 2 else "best", "100.00%", "0.00", "6"),
              ("SJ", "equal_best", "0.00%", "-12.25", "Not available"))[:count])
    rendered = render_result_presentation_v1(presentation(table), locale=locale)
    assert_candidates(rendered, [text(locale, k) for k in (
        "validation.field.card", "result.immediate.status", "result.win_rate",
        "result.point_swing", "result.trick_points")], [
            ["CJ", text(locale, "result.immediate." + ("equal_best" if count == 2 else "best")),
             "100.00%", "0.00", "6"],
            ["SJ", text(locale, "result.immediate.equal_best"), "0.00%", "-12.25",
             text(locale, "status.unavailable")]][:count])


@pytest.mark.parametrize("locale", ("de", "en"))
def test_literal_seven_column_scalar_cells_preserve_ordinals_signs_and_unavailable(locale):
    table = ResultTableV1(caption="Search Candidate comparisons in public Result order",
        columns=("Card", "Rank", "Recommended", "Completed worlds", "Contract success rate",
                 "Mean side game score", "Mean card-point margin"),
        rows=(("D10", "1", "Yes", "1000", "75.00%", "+12.5", "-0.125"),
              ("H9", "2", "No", "0", "Not available", "0", "Not available")))
    rendered = render_result_presentation_v1(presentation(table), locale=locale)
    assert_candidates(rendered, [text(locale, k) for k in (
        "validation.field.card", "result.rank", "task.recommendation", "result.completed_worlds",
        "result.success_rate", "result.mean_score", "result.mean_margin")], [
            ["D10", "1", text(locale, "common.answer.yes"), "1000", "75.00%", "+12.5", "-0.125"],
            ["H9", "2", text(locale, "common.answer.no"), "0", text(locale, "status.unavailable"),
             "0", text(locale, "status.unavailable")]])


@pytest.mark.parametrize("locale", ("de", "en"))
def test_unique_best_and_lower_candidate_statuses_remain_in_original_order(locale):
    table = ResultTableV1(caption="Card comparisons in public Result order",
        columns=("Card", "Evaluation", "Win rate", "Expected point swing", "Average trick points"),
        rows=(("Clubs Ace", "best", "75.00%", "15.00", "15"),
              ("Clubs Ten", "lower_evaluated", "75.00%", "14.00", "14")))
    assert_candidates(render_result_presentation_v1(presentation(table), locale=locale),
        [text(locale, k) for k in ("validation.field.card", "result.immediate.status",
            "result.win_rate", "result.point_swing", "result.trick_points")], [
            ["Clubs Ace", text(locale, "result.immediate.best"), "75.00%", "15.00", "15"],
            ["Clubs Ten", text(locale, "result.immediate.lower_evaluated"),
             "75.00%", "14.00", "14"]])


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("count", (0, 1, 3))
def test_match_curated_scalar_shape_keeps_fractions_and_empty_state(locale, count):
    rows = [{"card": "C7", "expected_point_swing": -1.25, "win_rate": 0.125},
            {"card": "C9", "expected_point_swing": 0, "win_rate": 0},
            {"card": "C8", "expected_point_swing": None, "win_rate": None}][:count]
    state = {"reports": [], "selected_position": 1,
        "download_availability": {"report_result": False},
        "selected_report": {"report_kind": "decision_analysis", "details": {
            "status": "unavailable", "immediate_candidate_values": rows}}}
    original = copy.deepcopy(state)
    rendered = render_match_reports_v1(state, locale)
    if count:
        assert_candidates(rendered, [text(locale, k) for k in (
            "validation.field.card", "result.point_swing", "result.win_rate")], [
                [f'{card_name(locale, "C7")} (C7)', "-1.25", "0.125"],
                [f'{card_name(locale, "C9")} (C9)', "0", "0"],
                [f'{card_name(locale, "C8")} (C8)', text(locale, "status.unavailable"),
                 text(locale, "status.unavailable")]][:count])
        region, = [n for n in Hierarchy(rendered).nodes if n["attrs"].get("role") == "region"]
        assert region["attrs"]["tabindex"] == "0"
        assert region["attrs"]["aria-label"] == text(locale, "result.table.immediate")
    else:
        assert "<table" not in rendered and "candidate-comparison" not in rendered
    assert state == original


def test_opt_in_uses_workflow_and_section_identity_not_caption_or_column_text():
    table = ResultTableV1(caption="untranslated <caption>", columns=("Card", "custom <metric>"),
                          rows=(("<unsafe & name>", "<script>"),))
    value = presentation(table)
    rendered = render_result_presentation_v1(value)
    assert_candidates(rendered, ["Card", "custom <metric>"], [["<unsafe & name>", "<script>"]])
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
    for alternative in (replace(value, workflow="historical_game"),
        replace(value, sections=tuple(replace(s, tables=()) if s.title == "Alternatives" else
            replace(s, tables=(table,)) if s.title == "Technical details" else s
            for s in value.sections))):
        html = render_result_presentation_v1(alternative)
        assert '<div class="result-table-wrap"><table>' in html
        assert "candidate-label" not in html and "candidate-comparison" not in html
    document = _historical_document()
    document["historical_game_summary"]["historical_information_set_search_review_summary"] = {
        "decisions": [{"decision_index": 3, "trick_number": 1, "play_index": 3,
                       "actual_card": "D7"}]}
    historical = build_result_presentation_v1(_execution(WorkflowV1.HISTORICAL_GAME, document))
    assert len(historical.sections[2].tables) == 3
    assert "candidate-table" not in render_result_presentation_v1(historical)


@pytest.mark.parametrize("effective,source", (
    ("immediate_expected_value", "analysis_report"),
    ("compatible_world_minimax_v1", "bounded_search_result"),
    ("bounded_information_set_policy_search_v1", "information_set_search_result"),
))
@pytest.mark.parametrize("status", ("complete", "partial", "timeout", "unavailable"))
def test_retained_method_selection_and_empty_states_are_not_changed_by_layout(
    effective, source, status,
):
    # Bounded scalar routing fixture, not a claimed successful engine execution.
    document = _position_document(status=status)
    document["recommendation_method_summary"]["effective_method"] = effective
    if source != "analysis_report":
        document[source] = {"status": status,
            "candidate_results": [] if status == "unavailable" else [
            {"card": "D7", "rank": 1, "is_recommended": True, "completed_world_count": 0,
             "local_contract_success_rate": None, "mean_local_side_game_score": -24,
             "mean_local_side_card_point_margin": 0}]}
    elif status == "unavailable":
        document[source] = []
    retained = copy.deepcopy(document)
    result = _execution(WorkflowV1.POSITION_ANALYSIS, document)
    value = build_result_presentation_v1(result)
    rendered = render_result_presentation_v1(value)
    if status == "unavailable":
        assert "<table" not in rendered and text("en", "result.no_candidates") in rendered
    else:
        assert rendered.count('class="candidate-table"') == 1
        assert len(value.sections[2].tables[0].columns) == (5 if source == "analysis_report" else 7)
        expected_card = "H9" if source == "analysis_report" else "D7"
        assert value.sections[2].tables[0].rows[0][0] == expected_card
    assert result.result.to_dict()["document"] == retained
