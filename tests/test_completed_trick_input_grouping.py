"""Completed-trick layout units and final response semantics, independently of CSS."""

from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _server
from test_guided_frontend_web import _position_values
from test_guided_historical_review_form import _draft_at_play
from test_guided_position_form import _form
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser
from test_task_first_language_preservation import enhanced_switch, envelope

from skatmind.app_web.card_form import CANONICAL_CARD_CONTROLS_V1
from skatmind.app_web.guided_rendering import (
    render_analyze_workflow_v1,
    render_review_workflow_v1,
)
from skatmind.app_web.historical_form import build_historical_play_view_v1
from skatmind.app_web.position_form import CompletedTrickFormValueV1, parse_position_form_v1
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.app_web.workflow_state import ProcessLocalFrontendWorkflowStateV1

ACTION = "/actions/analyze/run-guided"
CARDS = tuple(card.code for card in CANONICAL_CARD_CONTROLS_V1)


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def children(tree, parent):
    return [node for node in tree.nodes if node["parents"] and node["parents"][-1] is parent]


def descendants(tree, parent, tag):
    return [node for node in tree.nodes if node["tag"] == tag
            and any(ancestor is parent for ancestor in node["parents"])]


def selected_value(tree, select):
    options = descendants(tree, select, "option")
    selected = [option for option in options if "selected" in option["attrs"]]
    assert len(selected) <= 1
    return (selected or options)[0]["attrs"]["value"]


def assert_ids_and_labels(tree):
    ids = [node["attrs"]["id"] for node in tree.nodes if "id" in node["attrs"]]
    assert len(ids) == len(set(ids))
    for label in (node for node in tree.nodes if node["tag"] == "label"):
        if "for" in label["attrs"]:
            assert tree.by_id(label["attrs"]["for"])["tag"] in {"input", "select", "textarea"}
        else:
            assert sum(len(descendants(tree, label, tag))
                       for tag in ("input", "select", "textarea")) == 1


def assert_card_select(tree, select, locale, current, *, allowed=CARDS, empty=True):
    options = descendants(tree, select, "option")
    codes = tuple(code for code in CARDS if code in allowed)
    assert tuple(option["attrs"]["value"] for option in options) == (
        ("", *codes) if empty else codes)
    captions = [f"{card_name(locale, code)} ({code})" for code in codes]
    if empty:
        captions.insert(0, text(locale, "guided.no_card"))
    assert [option["text"] for option in options] == captions
    assert selected_value(tree, select) == current
    assert not {"disabled", "multiple", "tabindex"} & select["attrs"].keys()


def assert_completed_rows(page, locale, values):
    tree = Hierarchy(page)
    assert_ids_and_labels(tree)
    container = tree.by_id("field-completed_tricks")
    rows = descendants(tree, container, "fieldset")
    assert len(rows) == 9
    names = []
    for number, row in enumerate(rows, 1):
        legend, *groups = children(tree, row)
        assert legend["tag"] == "legend"
        assert legend["text"] == text(locale, "guided.trick_number", number=number)
        assert len(groups) == 4
        for index, group in enumerate(groups):
            # A direct row child must contain exactly one complete label/control pair.
            labels = descendants(tree, group, "label")
            selects = descendants(tree, group, "select")
            assert len(labels) == len(selects) == 1
            label, select = labels[0], selects[0]
            assert children(tree, group) == ([label] if index == 0 else [label, select])
            field = f"completed_trick_{number}_" + (f"card_{index}" if index else "leader")
            names.append(select["attrs"]["name"])
            assert select["attrs"]["name"] == field
            if index:
                identity = f"completed-trick-{number}-card-{index}"
                assert label["attrs"]["for"] == select["attrs"]["id"] == identity
                assert label["text"] == text(locale, "guided.card_number", number=index)
                assert_card_select(tree, select, locale, values.get(field, ""))
            else:
                assert select["parents"][-1] is label
                assert "id" not in select["attrs"]
                assert label["text"].startswith(text(locale, "guided.leader"))
                options = descendants(tree, select, "option")
                assert [option["attrs"]["value"] for option in options] == [
                    "", "me", "left", "right"]
                assert [option["text"] for option in options] == [
                    text(locale, key) for key in ("guided.no_trick", "guided.leader.me",
                                                 "guided.leader.left", "guided.leader.right")]
                assert selected_value(tree, select) == values.get(field, "")
    assert names == [f"completed_trick_{number}_{suffix}" for number in range(1, 10)
                     for suffix in ("leader", "card_1", "card_2", "card_3")]
    form = tree.by_id("workflow-form")
    assert form["attrs"]["action"] == ACTION and form["attrs"]["method"] == "post"
    assert all(any(parent is form for parent in row["parents"]) for row in rows)
    return tree


def assert_neighbor_selects(tree, locale, current=("", ""), actual=""):
    for identity, name, label_key, value in (
        ("current-trick-first", "current_trick", "guided.current_first", current[0]),
        ("current-trick-second", "current_trick", "guided.current_second", current[1]),
        ("actual-card-played", "actual_card_played", "guided.actual_card", actual),
    ):
        select = tree.by_id(identity)
        assert select["attrs"]["name"] == name
        siblings = children(tree, select["parents"][-1])
        label = siblings[siblings.index(select) - 1]
        assert label["tag"] == "label" and label["attrs"]["for"] == identity
        assert label["text"] == text(locale, label_key)
        assert_card_select(tree, select, locale, value)
        assert not any(parent["attrs"].get("class") == "completed-trick-row"
                       for parent in select["parents"])


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("populated", (None, 0, 1, 9))
def test_all_rows_are_complete_ordered_groups_for_empty_and_populated_drafts(locale, populated):
    draft = None
    expected = {}
    if populated is not None:
        # Presentation-only fixture exercises every row and leader choice; no execution.
        tricks = tuple(CompletedTrickFormValueV1(
            leader=("me", "left", "right")[index % 3], cards=CARDS[index * 3:index * 3 + 3],
            players=("me", "left", "right"), winner_player="me", winner_side="declarer",
        ) for index in range(populated))
        draft = replace(parse_position_form_v1(_form()), completed_tricks=tricks,
                        current_trick=("H7", "S10"), actual_card_played="CJ")
        for number, trick in enumerate(tricks, 1):
            expected[f"completed_trick_{number}_leader"] = trick.leader
            expected.update({f"completed_trick_{number}_card_{index}": card
                             for index, card in enumerate(trick.cards, 1)})
    state = ProcessLocalFrontendWorkflowStateV1(draft=draft)
    tree = assert_completed_rows(render_analyze_workflow_v1(state, locale=locale), locale, expected)
    assert_neighbor_selects(tree, locale, ("H7", "S10") if draft else ("", ""),
                            "CJ" if draft else "")


def assert_feedback(tree):
    summaries = [node for node in tree.nodes if node["attrs"].get("class") == "error-summary"]
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary["attrs"]["role"] == "alert" and summary["attrs"]["tabindex"] == "-1"
    assert "autofocus" in summary["attrs"]
    assert tree.by_id(summary["attrs"]["aria-labelledby"])["tag"] == "h2"
    targets = [tree.by_id(link["attrs"]["href"].removeprefix("#"))
               for link in descendants(tree, summary, "a")]
    assert targets
    invalid = [node for node in tree.nodes if node["attrs"].get("aria-invalid") == "true"]
    assert invalid
    for control in invalid:
        descriptions = control["attrs"]["aria-describedby"].split()
        assert descriptions
        for identity in descriptions:
            message = tree.by_id(identity)
            assert message["attrs"]["class"] == "field-error" and message["text"]
    assert any(target["attrs"].get("aria-invalid") == "true" for target in targets)
    assert {"hand", "skat"} <= {target["attrs"].get("name") for target in targets}


@pytest.mark.parametrize("locale", ("de", "en"))
def test_final_rejected_response_and_native_language_return_preserve_groups_and_safe_values(
    localized_server, locale,
):
    browser = Browser(localized_server)
    page = follow(browser, browser.request(
        "POST", ACTION, {**_position_values(0), "sample_count": "1"}))
    page = switch(browser, page, locale)
    accepted = localized_server.app_context.analyze_state
    values = {
        **_position_values(accepted.revision), "analysis_mode": "post_game_review",
        "completed_trick_1_leader": "me", "completed_trick_1_card_1": "C7",
        "completed_trick_1_card_2": "C8", "completed_trick_1_card_3": "CA",
        "completed_trick_2_leader": "right", "completed_trick_2_card_1": "S7",
        "completed_trick_2_card_2": "S8", "completed_trick_2_card_3": "",
        "current_trick": ["H7", ""], "actual_card_played": "CJ",
        "skat": ["CJ", "D7"],
    }
    status, _, body = browser.request("POST", ACTION, values)
    assert status == 400
    page = body.decode()
    feedback = localized_server.app_context.form_feedback._feedback["analyze"]
    assert feedback[1].safe_visible_values.all("current_trick") == ("H7", "")
    for index, language in enumerate((locale, "en" if locale == "de" else "de", locale)):
        if index:
            page = switch(browser, page, language)
        assert f'<html lang="{language}">' in page
        tree = assert_completed_rows(page, language, values)
        assert_neighbor_selects(tree, language, ("H7", ""), "CJ")
        assert_feedback(tree)
        assert text(language, "validation.last_valid_result") in page
        assert localized_server.app_context.analyze_state is accepted
        assert localized_server.app_context.form_feedback._feedback["analyze"] is feedback


@pytest.mark.parametrize("locale", ("de", "en"))
def test_enhanced_language_return_preserves_unsent_row_and_repeated_current_values(
    localized_server, locale,
):
    browser = Browser(localized_server)
    page = browser.page("/analyze")
    accepted = localized_server.app_context.analyze_state
    values = {f"completed_trick_{number}_{suffix}": [value]
              for number in range(1, 10)
              for suffix, value in (("leader", "left"), ("card_1", "D10"),
                                    ("card_2", ""), ("card_3", "CQ"))}
    values.update(current_trick=["", "SA"], actual_card_played=["C10"])
    page = follow(browser, enhanced_switch(browser, page, envelope(page, ACTION, values), locale))
    tree = assert_completed_rows(page, locale, {key: value[0] for key, value in values.items()})
    assert_neighbor_selects(tree, locale, ("", "SA"), "C10")
    assert localized_server.app_context.analyze_state is accepted


@pytest.mark.parametrize("locale", ("de", "en"))
def test_manual_historical_legal_card_selector_keeps_its_association_and_options(locale):
    draft = _draft_at_play()
    view = build_historical_play_view_v1(draft)
    page = render_review_workflow_v1(
        ProcessLocalFrontendWorkflowStateV1(draft=draft), locale=locale)
    tree = Hierarchy(page)
    assert_ids_and_labels(tree)
    select = tree.by_id("legal-card")
    assert select["attrs"]["name"] == "card"
    label, control = children(tree, select["parents"][-1])
    assert control is select and label["attrs"]["for"] == "legal-card"
    assert label["text"] == text(locale, "task.card.choose")
    first = next(card for card in CARDS if card in view.legal_cards)
    assert_card_select(tree, select, locale, first, allowed=view.legal_cards, empty=False)
