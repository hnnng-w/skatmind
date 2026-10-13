"""Recorded-review UI initialization stays separate from execution defaults."""

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms, record_live_game
from test_task_first_language_preservation import enhanced_switch, envelope
from test_whole_game_rollout_workflow import opening_request, run
from whole_game_review_fixtures import activate_saved_defender_decision, activate_saved_opening

import skatmind.api.v1.session.files as session_files
import skatmind.app_web.execution as execution_module
from skatmind.api.v1 import parse_request
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.errors import SkatMindError
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def form(page):
    return Forms(page).find("/sessions/review-whole-game")


def forbidden(*args, **kwargs):
    raise AssertionError("Passive views and invalid submissions must not evaluate or save")


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("missing", [(), ("bid_value",), ("matadors",), ("bid_value", "matadors")])
def test_fresh_native_form_defaults_and_exposes_only_missing_inputs(
    localized_server, monkeypatch, locale, missing,
):
    bid = None if "bid_value" in missing else 18
    if "matadors" in missing:
        context, checkpoint = activate_saved_defender_decision(localized_server, bid_value=bid)
    else:
        context, checkpoint = activate_saved_opening(localized_server, bid_value=bid)
    saved, frozen = context.path.read_bytes(), checkpoint.to_dict()
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(session_files, "save_session_file", forbidden)
    browser = Browser(localized_server)
    response = browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                              language=locale)
    assert response[0] == 303
    page = browser.page()
    values = form(page)["values"]
    assert values["objective"] == "complete_settlement"
    assert {name for name in values if name.startswith("analysis_")} == {
        "analysis_" + name for name in missing}
    tree = Hierarchy(page)
    for name in missing:
        assert values["analysis_" + name] == ""
        node = next(node for node in tree.nodes if node["attrs"].get("name") == "analysis_" + name)
        assert not any(parent["tag"] == "details" for parent in node["parents"])
    for objective in ("complete_settlement", "played_game_goal"):
        assert text(locale, "rollout.option." + objective) in page
    assert 'class="field-error"' not in page and 'class="error-summary"' not in page
    assert context.rollout_execution is None
    assert context.path.read_bytes() == saved and checkpoint.to_dict() == frozen


def test_explicit_alternative_survives_invalid_numeric_and_both_language_returns(
    localized_server, monkeypatch,
):
    context, _ = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    saved = context.path.read_bytes()
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(session_files, "save_session_file", forbidden)
    page = browser.page()
    # Enhanced return carries an explicit unsent choice before any evaluation.
    response = enhanced_switch(browser, page, envelope(page, "/sessions/review-whole-game", {
        "objective": ["played_game_goal"], "random_seed": ["7"],
    }), "de")
    assert response[0] == 303
    page = follow(browser, response)
    assert form(page)["values"]["objective"] == "played_game_goal"
    response = browser.submit(form(page), requested_worlds="0")
    assert response[0] == 400
    page = response[2].decode()
    assert form(page)["values"]["objective"] == "played_game_goal"
    response = browser.submit(Forms(page).find("/actions/profile/language"), language="en")
    assert response[0] == 303
    page = follow(browser, response)
    assert form(page)["values"]["objective"] == "played_game_goal"
    assert form(page)["values"]["requested_worlds"] == "0"
    assert text("en", "validation.rollout.invalid_requested_worlds") in page
    assert context.path.read_bytes() == saved and context.rollout_execution is None


@pytest.mark.parametrize("objective", [None, "", "unsupported"])
def test_missing_or_invalid_objective_is_not_reinitialized(
    localized_server, monkeypatch, objective,
):
    activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    monkeypatch.setattr(execution_module, "execute", forbidden)
    submitted = form(browser.page())
    if objective is None:
        submitted["values"].pop("objective")
    else:
        submitted["values"]["objective"] = objective
    response = browser.submit(submitted)
    assert response[0] == 400
    page = response[2].decode()
    reason = "invalid_fields" if objective is None else "invalid_objective"
    assert text("en", "validation.rollout." + reason) in page
    assert form(page)["values"]["objective"] == ""
    response = browser.submit(Forms(page).find("/actions/profile/language"), language="de")
    assert response[0] == 303
    assert form(follow(browser, response))["values"]["objective"] == ""


def test_once_entered_normal_declaration_bid_reaches_later_snapshots(localized_server, monkeypatch):
    browser = Browser(localized_server)
    monkeypatch.setattr(execution_module, "execute", forbidden)
    record_live_game(browser, play_count=6)
    context = localized_server.app_context.managed_stateful.active_session
    declarations = [entry for entry in context.state.command_log
                    if entry.command.kind == "set_declaration"]
    assert len(declarations) == 1
    checkpoints = context.document.decision_checkpoints
    assert len(checkpoints) >= 2
    assert all(cp.request.document["game_declaration"]["bid_value"] == 24 for cp in checkpoints)
    forms = [item for item in Forms(browser.page()).forms
             if item["action"] == "/sessions/review-whole-game"]
    assert len(forms) >= 2
    assert all(item["values"]["objective"] == "complete_settlement" for item in forms)
    assert all("analysis_bid_value" not in item["values"] for item in forms)


def test_retained_choice_and_rejected_choice_are_decision_bound(localized_server, monkeypatch):
    from whole_game_review_fixtures import saved_opening

    import skatmind.api.v1.session as session_api
    from skatmind.app_web.session_frontend import import_guided_session_v1

    _, first = saved_opening()
    state, second = saved_opening(decision_trick=2, actual="C7")
    app = localized_server.app_context
    document = session_api.build_session_persistence_document(
        state, decision_checkpoints=(first, second)).value
    context = import_guided_session_v1(app.managed_stateful.root("sessions"),
                                       handle="b" * 64, document=document.to_dict())
    app.managed_stateful.activate_session(context)
    browser = Browser(localized_server)
    assert browser.submit(form(browser.page()), objective="played_game_goal",
                          requested_worlds="1")[0] == 303
    retained, source = context.rollout_execution, context.rollout_review_source
    saved, frozen = context.path.read_bytes(), document.to_dict()
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(session_files, "save_session_file", forbidden)
    for locale in ("en", "de"):
        assert browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                              language=locale)[0] == 303
        page = browser.page()
        forms = Forms(page)
        assert forms.find("/sessions/review-whole-game", index=0)["values"][
            "objective"] == "played_game_goal"
        assert forms.find("/sessions/review-whole-game", index=1)["values"][
            "objective"] == "complete_settlement"
        result = page.split('<div id="session-rollout-result"', 1)[1]
        assert text(locale, "rollout.objective.played_game_goal") in result
        assert text(locale, "rollout.option.complete_settlement") not in result
        for name, expected in (("request", retained.request_json_bytes),
                               ("result", retained.result_json_bytes)):
            assert browser.request("GET", f"/sessions/downloads/rollout-{name}.json")[2] == expected
    response = browser.submit(forms.find("/sessions/review-whole-game", index=1),
                              objective="played_game_goal", random_seed="invalid")
    assert response[0] == 400
    page = response[2].decode()
    response = browser.submit(Forms(page).find("/actions/profile/language"), language="en")
    assert response[0] == 303
    forms = Forms(follow(browser, response))
    assert all(item["values"]["objective"] == "played_game_goal" for item in forms.forms
               if item["action"] == "/sessions/review-whole-game")
    assert context.rollout_execution is retained and context.rollout_review_source is source
    assert context.path.read_bytes() == saved and context.document.to_dict() == frozen


def test_core_and_public_omitted_settings_meaning_is_unchanged():
    assert WholeGameRolloutSettingsV1(random_seed=0).objective == "played_game_goal"
    root = opening_request()
    assert root["whole_game_rollout_settings"]["objective"] == "played_game_goal"
    del root["whole_game_rollout_settings"]["objective"]
    with pytest.raises(SkatMindError):
        parse_request(root)
    del root["recommendation_method"]
    del root["whole_game_rollout_settings"]
    root["sample_count"] = 1
    result = run(root)
    assert "whole_game_rollout_result" not in result
    assert "recommendation_method_summary" not in result
