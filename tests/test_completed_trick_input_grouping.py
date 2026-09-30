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

import skatmind.app_web.workflow_operations as operations
from skatmind.app_web.card_form import CANONICAL_CARD_CONTROLS_V1
from skatmind.app_web.form_parsing import FormValuesV1
from skatmind.app_web.form_registry import resolve_frontend_form_v1
from skatmind.app_web.guided_rendering import (
    render_analyze_workflow_v1,
    render_review_workflow_v1,
)
from skatmind.app_web.historical_form import build_historical_play_view_v1
from skatmind.app_web.position_form import (
    CompletedTrickFormValueV1,
    build_guided_position_execution_v1,
    parse_position_form_v1,
)
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.app_web.validation_contracts import (
    FrontendSubmittedFormStateV1,
    FrontendValidationIssueV1,
)
from skatmind.app_web.validation_rendering import apply_validation_feedback_to_html_v1
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
                if select["attrs"].get("aria-invalid") == "true":
                    assert tree.by_id(select["attrs"]["id"]) is select
                else:
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


def assert_accessibility_references(tree):
    assert_ids_and_labels(tree)
    for node in tree.nodes:
        for attribute in ("aria-describedby", "aria-labelledby"):
            for identity in node["attrs"].get(attribute, "").split():
                assert tree.by_id(identity)["text"]
    summary = next(node for node in tree.nodes
                   if node["attrs"].get("class") == "error-summary")
    for link in descendants(tree, summary, "a"):
        target = tree.by_id(link["attrs"]["href"][1:])
        assert tree.visible(target) and target["attrs"].get("type") != "hidden"
        assert target["attrs"]["aria-invalid"] == "true"
    for message in (node for node in tree.nodes if node["attrs"].get("class") == "field-error"):
        assert not any(parent["attrs"].get("class") in {
            "card-grid", "card-choice", "completed-trick-row", "completed-trick-field"}
            for parent in message["parents"])


@pytest.mark.parametrize("locale", ("de", "en"))
def test_reported_empty_hand_and_incomplete_trick_post_feedback(
    localized_server, locale, monkeypatch,
):
    browser = Browser(localized_server)
    page = follow(browser, browser.request("POST", ACTION,
                  {**_position_values(0), "sample_count": "1"}))
    switch(browser, page, locale)
    accepted = localized_server.app_context.analyze_state
    assert accepted.latest_successful_result is not None
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(args)
        raise AssertionError("Rejected selection must not execute analysis")
    monkeypatch.setattr(operations, "execute_guided_frontend_analysis_v1", forbidden)
    values = {**_position_values(accepted.revision), "hand": [],
              "completed_trick_1_leader": "me", "completed_trick_1_card_1": "CK",
              "completed_trick_1_card_2": "C7", "completed_trick_1_card_3": ""}
    status, _, body = browser.request("POST", ACTION, values)
    assert status == 400
    page = body.decode()
    retained = localized_server.app_context.form_feedback._feedback["analyze"]
    assert retained[1].safe_visible_values.all("hand") == ("",)
    assert "completed_tricks" not in {
        field.field_key for field in resolve_frontend_form_v1(ACTION).safe_fields}
    for index, language in enumerate((locale, "en" if locale == "de" else "de", locale)):
        if index:
            page = switch(browser, page, language)
        tree = assert_completed_rows(page, language, values)
        assert_accessibility_references(tree)
        assert_neighbor_selects(tree, language)
        messages = [node for node in tree.nodes if node["attrs"].get("class") == "field-error"]
        assert len(messages) == 2
        hand, trick = messages
        hand_group = tree.by_id("field-hand")
        assert hand["parents"][-1] is hand_group
        assert hand_group["attrs"]["tabindex"] == "-1"
        assert hand_group["attrs"]["aria-describedby"] == hand["attrs"]["id"]
        assert text(language, "guided.cards_selected", count=0) in hand_group["text"]
        assert len(descendants(tree, hand_group, "input")) == 32
        assert trick["parents"][-1] is tree.by_id("field-completed_tricks")
        assert hand["text"] != trick["text"]
        assert hand["text"] == text(language, "validation.position.empty_hand")
        assert trick["text"] == text(language, "validation.position.incomplete_trick", number=1,
                                     missing=text(language, "guided.card_number", number=3))
        summary = next(node for node in tree.nodes
                       if node["attrs"].get("class") == "error-summary")
        links = descendants(tree, summary, "a")
        assert [link["attrs"]["href"] for link in links] == [
            "#field-hand", "#completed-trick-1-card-3"]
        assert text(language, "guided.hand") in links[0]["text"]
        assert text(language, "guided.trick_number", number=1) in links[1]["text"]
        assert not any(node["attrs"].get("name") == "hand" and "checked" in node["attrs"]
                       for node in tree.nodes)
        assert localized_server.app_context.analyze_state is accepted
        assert localized_server.app_context.form_feedback._feedback["analyze"] is retained
        assert text(language, "validation.last_valid_result") in page
    assert (browser.request("GET", "/downloads/analyze/request.json")[2]
            == accepted.request_json_bytes)
    assert browser.request("GET", "/downloads/analyze/result.json")[2] == accepted.result_json_bytes
    assert calls == []


def completed_values(number=1):
    return {**_position_values(0), "sample_count": "1",
            "hand": ["CJ", "CA", "C10", "CQ", "C9", "SA", "S10", "HA", "H10"],
            **{f"completed_trick_{number}_{name}": value for name, value in (
                ("leader", "me"), ("card_1", "CK"), ("card_2", "C7"), ("card_3", "C8"))}}


def assert_builds(values):
    build_guided_position_execution_v1(parse_position_form_v1({
        name: value if isinstance(value, list) else [value]
        for name, value in values.items() if name != "revision"}))


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("number", (1, 5, 9))
@pytest.mark.parametrize("missing", (("leader",), ("card_1",), ("card_2",), ("card_3",),
                                      ("leader", "card_2"), ("card_1", "card_2", "card_3")))
def test_incomplete_row_alone_targets_each_missing_control(
    localized_server, locale, number, missing,
):
    browser = Browser(localized_server)
    switch(browser, browser.page("/analyze"), locale)
    values = completed_values(number)
    assert_builds(values)
    values.update({f"completed_trick_{number}_{name}": "" for name in missing})
    status, _, body = browser.request("POST", ACTION, values)
    assert status == 400
    tree = assert_completed_rows(body.decode(), locale, values)
    assert_accessibility_references(tree)
    messages = [node for node in tree.nodes if node["attrs"].get("class") == "field-error"]
    assert len(messages) == 1
    expected_missing = ", ".join(text(locale, "guided.leader") if name == "leader" else
                                 text(locale, "guided.card_number", number=name[-1])
                                 for name in missing)
    assert messages[0]["text"] == text(locale, "validation.position.incomplete_trick",
                                        number=number, missing=expected_missing)
    invalid = [node for node in tree.nodes if node["attrs"].get("aria-invalid") == "true"]
    assert [node["attrs"]["name"] for node in invalid] == [
        f"completed_trick_{number}_{name}" for name in missing]
    assert all(node["attrs"]["aria-describedby"] == messages[0]["attrs"]["id"] for node in invalid)
    summary = next(node for node in tree.nodes
                   if node["attrs"].get("class") == "error-summary")
    assert descendants(tree, summary, "a")[0]["attrs"]["href"] == "#" + invalid[0]["attrs"]["id"]
    assert messages[0]["parents"][-1] is tree.by_id("field-completed_tricks")
    row = next(parent for parent in invalid[0]["parents"] if parent["tag"] == "fieldset")
    siblings = children(tree, row["parents"][-1])
    assert siblings[siblings.index(row) + 1] is messages[0]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_empty_hand_alone_and_corrected_form_with_unused_rows_are_valid(localized_server, locale):
    browser = Browser(localized_server)
    switch(browser, browser.page("/analyze"), locale)
    values = {**_position_values(0), "sample_count": "1"}
    values.update({f"completed_trick_{number}_{name}": "" for number in range(1, 10)
                   for name in ("leader", "card_1", "card_2", "card_3")})
    assert_builds(values)
    status, _, body = browser.request("POST", ACTION, {**values, "hand": [""]})
    assert status == 400
    tree = assert_completed_rows(body.decode(), locale, values)
    assert_accessibility_references(tree)
    messages = [node for node in tree.nodes if node["attrs"].get("class") == "field-error"]
    assert [message["text"] for message in messages] == [
        text(locale, "validation.position.empty_hand")]
    response = browser.request("POST", ACTION, values)
    assert response[0] == 303
    assert 'class="error-summary"' not in follow(browser, response)
    assert localized_server.app_context.analyze_state.latest_successful_result is not None


@pytest.mark.parametrize("locale", ("de", "en"))
def test_multiple_incomplete_rows_and_neighbor_values_survive_language_return(
    localized_server, locale,
):
    browser = Browser(localized_server)
    switch(browser, browser.page("/analyze"), locale)
    values = {**_position_values(0), "analysis_mode": "post_game_review",
              "actual_card_played": "CJ", "current_trick": ["", "H10"],
              "completed_trick_2_leader": "me", "completed_trick_2_card_2": "C7",
              "completed_trick_7_card_1": "D10", "completed_trick_7_card_3": "D7"}
    status, _, body = browser.request("POST", ACTION, values)
    assert status == 400
    page = body.decode()
    for index, language in enumerate((locale, "en" if locale == "de" else "de")):
        if index:
            page = switch(browser, page, language)
        tree = assert_completed_rows(page, language, values)
        assert_accessibility_references(tree)
        assert_neighbor_selects(tree, language, ("", "H10"), "CJ")
        messages = [node for node in tree.nodes if node["attrs"].get("class") == "field-error"]
        assert len(messages) == 2
        for message, number in zip(messages, (2, 7), strict=True):
            assert message["text"].startswith(text(language, "guided.trick_number", number=number))
        feedback = localized_server.app_context.form_feedback._feedback["analyze"][1]
        assert feedback.safe_visible_values.all("current_trick") == ("", "H10")
        assert [issue.field_key for issue in feedback.validation_issues] == [
            "completed_trick_2_card_1", "completed_trick_7_leader"]


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("updates, field", (
    ({"hand": ["CA"]}, "hand"),
    ({"hand": list(CARDS[:11])}, "hand"),
    ({"hand": ["CA", "CA"]}, "hand"),
    ({"hand": ["invalid"]}, "hand"),
    ({"skat": ["D7"]}, "skat"),
    ({"public_declarer_cards": ["H7"]}, "public_declarer_cards"),
    ({"current_trick": ["CA", ""]}, "current_trick"),
    ({"actual_card_played": "CJ"}, "actual_card_played"),
))
def test_other_analyze_card_rejections_keep_generic_reason_and_correct_group(
    localized_server, locale, updates, field,
):
    browser = Browser(localized_server)
    switch(browser, browser.page("/analyze"), locale)
    status, _, body = browser.request("POST", ACTION, {**_position_values(0), **updates})
    assert status == 400
    tree = Hierarchy(body.decode())
    assert_accessibility_references(tree)
    feedback = localized_server.app_context.form_feedback._feedback["analyze"][1]
    assert all(issue.position_feedback is None for issue in feedback.validation_issues)
    assert field in {issue.field_key for issue in feedback.validation_issues}
    group = tree.by_id(f"field-{field}")
    errors = [node for node in children(tree, group) if node["attrs"].get("class") == "field-error"]
    assert errors
    assert all(node["text"] == text(locale, "validation.message.card_conflict") for node in errors)


def test_correcting_incomplete_row_runs_once_and_clears_feedback(localized_server, monkeypatch):
    browser = Browser(localized_server)
    real_execute = operations.execute_guided_frontend_analysis_v1
    calls = []
    def execute(*args, **kwargs):
        calls.append(args)
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(operations, "execute_guided_frontend_analysis_v1", execute)
    values = completed_values()
    assert browser.request("POST", ACTION, {**values, "completed_trick_1_card_3": ""})[0] == 400
    assert calls == []
    response = browser.request("POST", ACTION, values)
    assert response[0] == 303
    page = follow(browser, response)
    tree = assert_completed_rows(page, "en", values)
    assert not any(node["attrs"].get("class") in {"error-summary", "field-error"}
                   for node in tree.nodes)
    assert len(calls) == 1
    accepted = localized_server.app_context.analyze_state
    assert accepted.draft.completed_tricks[0].cards == ("CK", "C7", "C8")
    assert "analyze" not in localized_server.app_context.form_feedback._feedback


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
    assert {"field-hand", "field-skat"} <= {target["attrs"].get("id") for target in targets}
    for identity in ("field-hand", "field-skat"):
        group = tree.by_id(identity)
        assert group["tag"] == "fieldset" and group["attrs"]["tabindex"] == "-1"
        assert descendants(tree, group, "input")


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


@pytest.mark.parametrize("locale", ("de", "en"))
def test_manual_review_card_feedback_keeps_native_label_control_and_target(locale):
    draft = _draft_at_play()
    page = render_review_workflow_v1(
        ProcessLocalFrontendWorkflowStateV1(draft=draft), locale=locale)
    definition = resolve_frontend_form_v1("/actions/review/append-play")
    feedback = FrontendSubmittedFormStateV1(
        contract_version=1, form_key=definition.form_key, originating_route=definition.action_route,
        active_family_binding="review", review_wizard_step=5, form_instance=None,
        safe_visible_values=FormValuesV1(), validation_issues=(FrontendValidationIssueV1(
            field_key="card", message_key="validation.message.card_conflict"),),
        status="invalid", feedback_generation=1)
    tree = Hierarchy(apply_validation_feedback_to_html_v1(
        page, definition, feedback, locale=locale))
    assert_accessibility_references(tree)
    control = tree.by_id("legal-card")
    label, rendered_control, error = children(tree, control["parents"][-1])
    assert rendered_control is control
    assert label["attrs"]["for"] == control["attrs"]["id"]
    assert error["attrs"]["id"] == control["attrs"]["aria-describedby"]
    view = build_historical_play_view_v1(draft)
    first = next(card for card in CARDS if card in view.legal_cards)
    assert_card_select(tree, control, locale, first, allowed=view.legal_cards, empty=False)
