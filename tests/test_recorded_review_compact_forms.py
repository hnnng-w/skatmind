"""Ten-decision form structure, native ownership, and scoped state preservation."""

import json

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope
from whole_game_review_fixtures import activate_ten_decisions

import skatmind.api.v1.session.files as files
import skatmind.app_web.execution as execution_module
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

ROUTE = "/sessions/review-whole-game"


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def descendants(tree, parent, tag=None):
    return [node for node in tree.nodes if (tag is None or node["tag"] == tag)
            and any(ancestor is parent for ancestor in node["parents"])]


def rollout_nodes(tree):
    return [node for node in tree.nodes if node["tag"] == "form"
            and node["attrs"].get("action") == ROUTE]


def disclosure_state(page, index, opened):
    tree = Hierarchy(page)
    target, = descendants(tree, rollout_nodes(tree)[index], "details")
    return [opened if node is target else "open" in node["attrs"]
            for node in tree.nodes if node["tag"] == "details"]


def forbidden(*args, **kwargs):
    raise AssertionError("Passive layout and invalid input must not evaluate or save")


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("bid", [None, 18])
def test_ten_decisions_separate_basic_actions_and_technical_controls(
    localized_server, monkeypatch, locale, bid,
):
    context = activate_ten_decisions(localized_server, bid_value=bid)
    saved, frozen = context.path.read_bytes(), context.document.to_dict()
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(files, "save_session_file", forbidden)
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                                          language=locale))
    tree = Hierarchy(page)
    region = tree.by_id("recorded-decisions")
    assert region["text"].count(text(locale, "rollout.objective_help")) == 1
    assert region["text"].count(text(locale, "rollout.supplement_help")) == (bid is None)
    identities = [node["attrs"]["id"] for node in descendants(tree, region)
                  if "id" in node["attrs"]]
    assert len(identities) == len(set(identities))
    forms = rollout_nodes(tree)
    assert len(forms) == 10
    for form in forms:
        owned = descendants(tree, form)
        details, = [node for node in owned if node["tag"] == "details"]
        assert "open" not in details["attrs"]
        basic, = [node for node in owned if node["attrs"].get("class") == "recorded-basic"]
        actions, = [node for node in owned if node["attrs"].get("class") == "recorded-actions"]
        assert owned.index(basic) < owned.index(actions) < owned.index(details)
        basic_names = {node["attrs"]["name"] for node in descendants(tree, basic)
                       if "name" in node["attrs"]}
        assert basic_names == (
            {"objective", "analysis_bid_value"} if bid is None else {"objective"})
        assert all(Hierarchy.visible(node) for node in descendants(tree, basic))
        technical = [node for node in descendants(tree, details) if "name" in node["attrs"]]
        assert [node["attrs"]["name"] for node in technical] == ["requested_worlds", "random_seed"]
        assert [node["attrs"]["value"] for node in technical] == ["100", "0"]
        assert all("required" in node["attrs"] for node in technical)
        primary, secondary = descendants(tree, actions, "button")
        assert primary["attrs"]["class"] == "primary" and "form" not in primary["attrs"]
        assert secondary["attrs"]["class"] == "secondary"
        legacy = tree.by_id(secondary["attrs"]["form"])
        assert legacy["attrs"]["action"] == "/sessions/review-decision"
        assert not descendants(tree, legacy, "form") and not descendants(tree, form, "form")
        assert len([node for node in owned if node["attrs"].get("class") == "primary"]) == 1
        for node in descendants(tree, basic):
            if node["tag"] in {"input", "select"}:
                assert all(tree.by_id(identity)["text"] for identity in
                           node["attrs"]["aria-describedby"].split())
    assert context.path.read_bytes() == saved and context.document.to_dict() == frozen
    assert context.rollout_execution is context.execution is None


def test_ten_decision_language_return_preserves_independent_fields_and_open_details(
    localized_server, monkeypatch,
):
    context = activate_ten_decisions(localized_server)
    saved = context.path.read_bytes()
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(files, "save_session_file", forbidden)
    browser = Browser(localized_server)
    page = browser.page()
    for locale, objective in (("de", "complete_settlement"), ("en", "played_game_goal"),
                              ("de", "complete_settlement")):
        values = json.loads(envelope(page, ROUTE, {
            "objective": [objective], "analysis_bid_value": ["18"],
            "requested_worlds": ["3"], "random_seed": ["77"],
        }, index=3, disclosures=disclosure_state(page, 3, True)))
        values["forms"] += json.loads(envelope(page, ROUTE, {
            "objective": ["played_game_goal"], "requested_worlds": ["2"], "random_seed": ["8"],
        }, index=7))["forms"]
        page = follow(browser, enhanced_switch(browser, page, json.dumps(values), locale))
        forms = Forms(page)
        for index in range(10):
            current = forms.find(ROUTE, index=index)["values"]
            expected = ((objective, "18", "3", "77") if index == 3 else
                        ("played_game_goal", "", "2", "8") if index == 7 else
                        ("complete_settlement", "", "100", "0"))
            assert tuple(current[name] for name in ("objective", "analysis_bid_value",
                                                   "requested_worlds", "random_seed")) == expected
        tree = Hierarchy(page)
        for index, form in enumerate(rollout_nodes(tree)):
            details, = descendants(tree, form, "details")
            assert ("open" in details["attrs"]) == (index == 3)
    assert context.path.read_bytes() == saved and context.rollout_execution is None


@pytest.mark.parametrize("opened", [False, True])
def test_technical_values_submit_in_the_owning_form_open_or_closed(localized_server, opened):
    context = activate_ten_decisions(localized_server)
    browser = Browser(localized_server)
    page = browser.page()
    page = follow(browser, enhanced_switch(browser, page, envelope(page, ROUTE, {
        "objective": ["played_game_goal"], "requested_worlds": ["1"], "random_seed": ["9"],
    }, index=4, disclosures=disclosure_state(page, 4, opened))))
    response = browser.submit(Forms(page).find(ROUTE, index=4))
    assert response[0] == 303, response[2].decode()
    request = context.rollout_execution.request.document
    assert request["whole_game_rollout_settings"]["requested_worlds"] == 1
    assert request["whole_game_rollout_settings"]["random_seed"] == 9
    assert context.rollout_review_source.decision.checkpoint.trick_number == 5


def test_legacy_submission_does_not_inherit_invalid_rollout_controls(localized_server):
    context = activate_ten_decisions(localized_server)
    browser = Browser(localized_server)
    page = browser.page()
    page = follow(browser, enhanced_switch(browser, page, envelope(page, ROUTE, {
        "requested_worlds": [""], "random_seed": [""], "analysis_bid_value": [""],
    }, index=2)))
    legacy = Forms(page).find("/sessions/review-decision", index=2)
    assert set(legacy["values"]) == {
        "managed_handle", "expected_revision", "decision_selection", "_frontend_form_instance"}
    response = browser.submit(legacy)
    assert response[0] == 303
    assert context.execution is not None and context.rollout_execution is None
    assert context.recorded_review_source.decision.checkpoint.trick_number == 3


@pytest.mark.parametrize("field,value,key", [
    ("analysis_bid_value", "", "required_bid_value"),
    ("requested_worlds", "0", "invalid_requested_worlds"),
    ("random_seed", "", "invalid_random_seed"),
])
def test_errors_target_only_the_correct_decision_and_technical_disclosure(
    localized_server, monkeypatch, field, value, key,
):
    activate_ten_decisions(localized_server)
    browser = Browser(localized_server)
    monkeypatch.setattr(execution_module, "execute", forbidden)
    submitted = Forms(browser.page()).find(ROUTE, index=6)
    response = browser.submit(submitted, **{field: value})
    assert response[0] == 400
    page = response[2].decode()
    tree = Hierarchy(page)
    for index, form in enumerate(rollout_nodes(tree)):
        details, = descendants(tree, form, "details")
        assert ("open" in details["attrs"]) == (index == 6 and field != "analysis_bid_value")
    form = rollout_nodes(tree)[6]
    target = next(node for node in descendants(tree, form) if node["attrs"].get("name") == field)
    assert target["attrs"]["aria-invalid"] == "true"
    assert any(text("en", "validation.rollout." + key) in tree.by_id(identity)["text"]
               for identity in target["attrs"]["aria-describedby"].split())
    if field != "analysis_bid_value":
        assert f'href="#{target["attrs"]["id"]}"' in page
    else:
        assert "autofocus" in target["attrs"]
