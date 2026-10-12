import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_rollout_result_presentation import primary_summary
from test_session_recorded_review_web import Browser, Forms
from test_whole_game_rollout_workflow import without_time
from whole_game_review_fixtures import activate_saved_opening, synthetic_tied_rollout

import skatmind.app_web.execution as execution_module
from skatmind.api.v1 import execute, parse_request, serialize_result
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def rollout_form(browser):
    return Forms(browser.page()).find("/sessions/review-whole-game")


def test_tied_primary_summary_http_languages_and_retained_download_identity(
    localized_server, monkeypatch,
):
    import skatmind.api.v1.session.files as files
    import skatmind.recommendation_workflow as workflow
    from skatmind.api.v1.schema_validation import validate_output_document

    context, checkpoint = activate_saved_opening(localized_server, complete=True, actual="C7")
    browser = Browser(localized_server)
    saved, frozen = context.path.read_bytes(), checkpoint.to_dict()
    # Only the candidate fixture is synthetic; POST, source binding, public output
    # validation, retained execution, rendering and downloads use the real path.
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", synthetic_tied_rollout)
    assert browser.submit(rollout_form(browser), requested_worlds="100")[0] == 303
    retained, source = context.rollout_execution, context.rollout_review_source
    document = retained.result.result.to_dict()["document"]
    validate_output_document(document)
    result = document["whole_game_rollout_result"]
    assert result["recommended_card"] == document["recommendation"]["card"] == "C9"
    assert result["tied_best_cards"] == ["C9", "C8", "C7"]
    assert document["whole_game_rollout_comparison"]["actual_card"] == "C7"
    request_bytes, result_bytes = retained.request_json_bytes, retained.result_json_bytes

    def forbidden(*args, **kwargs):
        raise AssertionError("Passive rendering must not execute or save")
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", forbidden)
    monkeypatch.setattr(files, "save_session_file", forbidden)
    for locale in ("de", "en"):
        assert browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                              language=locale)[0] == 303
        page = browser.page()
        summary = primary_summary(page, prefix="rollout-result")
        cards = ", ".join(card_name(locale, card) + f" ({card})" for card in ["C9", "C8", "C7"])
        assert f'<dt>{text(locale, "rollout.recommended_plural")}</dt><dd>{cards}</dd>' in summary
        played = text(locale, "rollout.played_tied", card=card_name(locale, "C7") + " (C7)")
        assert f'<dt>{text(locale, "rollout.played")}</dt><dd>{played}</dd>' in summary
        assert page.index(summary) < page.index('class="result-table-wrap candidate-comparison"')
        assert text(locale, "rollout.recommended") not in page
        assert text(locale, "rollout.comparison.equal_complete_objective") in page
        assert '<details class="technical-details">' in page
        assert browser.request("GET", "/sessions/downloads/rollout-request.json")[2] == (
            request_bytes)
        assert browser.request("GET", "/sessions/downloads/rollout-result.json")[2] == result_bytes
        assert context.rollout_execution is retained and context.rollout_review_source is source
        assert retained.result.result.to_dict()["document"] == document
        assert context.path.read_bytes() == saved and checkpoint.to_dict() == frozen


def test_real_post_derived_root_dual_downloads_and_passive_languages(localized_server, monkeypatch):
    context, checkpoint = activate_saved_opening(localized_server, complete=True)
    browser = Browser(localized_server)
    saved, frozen = context.path.read_bytes(), checkpoint.request.to_dict()
    legacy_form = Forms(browser.page()).find("/sessions/review-decision")
    assert browser.submit(legacy_form)[0] == 303
    legacy = context.execution
    form = rollout_form(browser)
    status, headers, body = browser.submit(form, requested_worlds="2", random_seed="7")
    assert status == 303, body.decode()
    assert headers["location"] == "/sessions/current#session-rollout-result"
    retained = context.rollout_execution
    assert context.execution is legacy
    root = json.loads(retained.request_json_bytes)
    unchanged = {k: v for k, v in root.items() if k not in {
        "recommendation_method", "whole_game_rollout_settings", "whole_game_rollout_derivation",
        "analysis_mode", "actual_card_played"}}
    assert unchanged == {k: v for k, v in frozen["document"].items() if k != "analysis_mode"}
    assert root["actual_card_played"] == "CJ"
    assert root["whole_game_rollout_derivation"]["source_revision"] == checkpoint.source_revision
    assert root["whole_game_rollout_settings"]["random_seed"] == 7
    public = retained.result.result.document["whole_game_rollout_result"]
    assert public["status"] == "complete" and public["completed_common_worlds"] == 2
    # Exported bytes are genuine public Requests, not a browser-only envelope.
    repeated = execute(parse_request(root)).result.to_dict()["document"][
        "whole_game_rollout_result"]
    assert without_time(json.loads(retained.result_json_bytes)["document"][
        "whole_game_rollout_result"]) == without_time(repeated)
    def forbidden(*args, **kwargs):
        raise AssertionError("Passive action must not execute or save")
    monkeypatch.setattr(execution_module, "execute", forbidden)
    import skatmind.api.v1.session.files as files
    monkeypatch.setattr(files, "save_session_file", forbidden)
    for language in ("de", "en"):
        form = Forms(browser.page()).find("/actions/profile/language")
        assert browser.submit(form, language=language)[0] == 303
        page = browser.page()
        assert text(language, "rollout.heading") in page
        assert text(language, "rollout.all_succeeded", candidates=10, samples=2,
                    goal=text(language, "rollout.goal.played_game_goal")) in page
        assert 'value="7"' in page
        assert 'class="result-table-wrap candidate-comparison"' in page
        for name, expected in (("request", legacy.request_json_bytes),
                               ("result", legacy.result_json_bytes),
                               ("rollout-request", retained.request_json_bytes),
                               ("rollout-result", retained.result_json_bytes)):
            assert browser.request("GET", f"/sessions/downloads/{name}.json")[2] == expected
    assert json.loads(retained.result_json_bytes) == serialize_result(retained.result)
    assert context.path.read_bytes() == saved and checkpoint.request.to_dict() == frozen


def test_missing_settlement_and_rejected_attempt_retain_completed_output(localized_server):
    context, _ = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    assert browser.submit(rollout_form(browser), requested_worlds="1")[0] == 303
    retained, source = context.rollout_execution, context.rollout_review_source
    form = rollout_form(browser)
    status, _, content = browser.submit(form, objective="complete_settlement")
    assert status == 400
    page = content.decode()
    assert text("en", "rollout.reason.missing_terminal_utility_inputs") in page
    assert text("en", "rollout.retained") in page
    assert context.rollout_execution is retained and context.rollout_review_source is source
    for extra in ({"actual_card_played": "SA"}, {"requested_worlds": "1001"},
                  {"random_seed": "-1"}, {"max_card_transitions": "999999"}):
        assert browser.submit(form, **extra)[0] == 400
        assert context.rollout_execution is retained
    assert browser.submit(form, decision_selection="f" * 64)[0] == 409
    context.path.write_bytes(b"{}\n")
    assert browser.request("GET", "/sessions/downloads/rollout-result.json")[0] == 409
    assert context.rollout_execution is context.execution is None


def test_out_of_order_rollout_publication_is_source_and_attempt_owned(
    localized_server, monkeypatch,
):
    context, _ = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    form = rollout_form(browser)
    entered, release = Event(), Event()
    real = execution_module.execute
    calls = 0
    def blocked(request, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            assert release.wait(30)
        return real(request, **kwargs)
    monkeypatch.setattr(execution_module, "execute", blocked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        prior = pool.submit(browser.submit, form, requested_worlds="1", random_seed="1")
        assert entered.wait(30)
        # This would deadlock if the global or Session lock covered evaluation.
        assert browser.submit(form, requested_worlds="1", random_seed="2")[0] == 303
        latest = context.rollout_execution
        release.set()
        assert prior.result(timeout=30)[0] == 409
    assert context.rollout_execution is latest
    assert latest.request.document["whole_game_rollout_settings"]["random_seed"] == 2


@pytest.mark.parametrize("change", ["reload", "retire", "file"])
def test_inflight_context_or_file_change_cannot_publish(localized_server, monkeypatch, change):
    from skatmind.app_web.managed_item_discovery import discover_managed_items_v1
    from skatmind.app_web.session_frontend import open_guided_session_v1, reload_guided_session_v1
    context, _ = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    form = rollout_form(browser)
    entered, release = Event(), Event()
    real = execution_module.execute
    def blocked(request, **kwargs):
        entered.set()
        assert release.wait(30)
        return real(request, **kwargs)
    monkeypatch.setattr(execution_module, "execute", blocked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(browser.submit, form, requested_worlds="1")
        assert entered.wait(30)
        if change == "reload":
            reload_guided_session_v1(context)
        elif change == "retire":
            discovery = discover_managed_items_v1(
                context.category_root, family="sessions", generation=1)
            replacement = open_guided_session_v1(context.category_root, discovery.entries[0])
            localized_server.app_context.managed_stateful.activate_session(replacement)
        else:
            context.path.write_bytes(b"{}\n")
        release.set()
        assert future.result(timeout=30)[0] == 409
    assert context.rollout_execution is None
    assert localized_server.app_context.managed_stateful.active_session.rollout_execution is None


def test_interrupted_real_core_and_executor_failure_keep_previous_bytes(
    localized_server, monkeypatch,
):
    import skatmind.recommendation_workflow as workflow
    from skatmind.errors import SkatMindValidationError
    context, _ = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    assert browser.submit(rollout_form(browser), requested_worlds="1")[0] == 303
    retained = context.rollout_execution
    real = workflow.evaluate_whole_game_rollout_v1
    def timed_out(view, settings):
        ticks = iter(range(0, 100000, 31))
        return real(view, settings, clock=lambda: next(ticks))
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", timed_out)
    assert browser.submit(rollout_form(browser), requested_worlds="1")[0] == 400
    assert context.rollout_notice.reason == "wall_clock_timeout"
    assert context.rollout_execution is retained
    def failed(*args, **kwargs):
        raise SkatMindValidationError("Synthetic rejected execution")
    monkeypatch.setattr(execution_module, "execute", failed)
    assert browser.submit(rollout_form(browser), requested_worlds="1")[0] == 400
    assert context.rollout_execution is retained
    assert browser.request("GET", "/sessions/downloads/rollout-result.json")[2] == (
        retained.result_json_bytes)


def test_enhanced_language_return_preserves_rollout_view_and_unsent_settings(
    localized_server, monkeypatch,
):
    from test_language_view_continuity import return_data
    from test_match_recording_recovery_web import follow
    from test_task_first_language_preservation import enhanced_switch, envelope

    context, _ = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    assert browser.submit(rollout_form(browser), requested_worlds="1")[0] == 303
    retained, document = context.rollout_execution, context.document
    def forbidden(*args, **kwargs):
        raise AssertionError("Language return must not execute")
    monkeypatch.setattr(execution_module, "execute", forbidden)
    page = browser.page()
    for locale in ("de", "en"):
        value = json.loads(envelope(page, "/sessions/review-whole-game", {
            "random_seed": ["99"], "requested_worlds": ["5"],
            "objective": ["complete_settlement"],
        }))
        value["view"] = {"anchor": "id:session-rollout-result", "offset": -120,
                         "x": 0, "focus": locale}
        response = enhanced_switch(browser, page, json.dumps(value), locale)
        assert response[0] == 303
        page = follow(browser, response)
        assert return_data(page)["view"] == value["view"]
        values = Forms(page).find("/sessions/review-whole-game")["values"]
        assert (values["random_seed"], values["requested_worlds"], values["objective"]) == (
            "99", "5", "complete_settlement")
        assert context.rollout_execution is retained and context.document is document


def test_passive_clarity_rendering_preserves_an_old_export_explanation(
    localized_server, monkeypatch,
):
    from dataclasses import replace

    import skatmind.api.v1.session.files as files
    from skatmind.api.v1 import ExecutionResultV1
    from skatmind.api.v1.schema_validation import validate_output_document
    from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1

    context, checkpoint = activate_saved_opening(localized_server)
    browser = Browser(localized_server)
    assert browser.submit(rollout_form(browser), requested_worlds="1")[0] == 303
    executed = context.rollout_execution
    old_document = executed.result.result.to_dict()["document"]
    old_text = ("No post-game review decision quality is available because "
                "immediate analysis is unavailable.")
    old_document["post_game_review_summary"]["decision_explanation"] = old_text
    validate_output_document(old_document)
    old_result = ExecutionResultV1(result=replace(executed.result.result, document=old_document))
    # Simulate a valid previously retained producer Result, never alter a saved file.
    retained = replace(executed, result=old_result,
        result_json_bytes=canonical_frontend_json_bytes_v1(serialize_result(old_result)))
    context.rollout_execution = retained
    source = context.rollout_review_source
    saved, frozen = context.path.read_bytes(), checkpoint.to_dict()
    def forbidden(*args, **kwargs):
        raise AssertionError("Passive rendering must not execute or save")
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(files, "save_session_file", forbidden)
    for locale in ("de", "en"):
        page = browser.page()
        response = browser.submit(Forms(page).find("/actions/profile/language"), language=locale)
        assert response[0] == 303
        page = browser.page()
        ties = old_document["whole_game_rollout_result"]["tied_best_cards"]
        label = text(locale, "rollout.recommended_plural" if len(ties) > 1
                     else "rollout.recommended")
        cards = ", ".join(card_name(locale, card) + f" ({card})" for card in ties)
        assert f'<dt>{label}</dt><dd>{cards}</dd>' in primary_summary(page, prefix="rollout-result")
        assert text(locale, "rollout.calculation_details") in page
        assert '<details class="technical-details">' in page
        assert 'class="recorded-review-source"' in page and 'href="#recorded-decision-1"' in page
        assert browser.request("GET", "/sessions/downloads/rollout-request.json")[2] == (
            retained.request_json_bytes)
        assert browser.request("GET", "/sessions/downloads/rollout-result.json")[2] == (
            retained.result_json_bytes)
        assert old_text in retained.result_json_bytes.decode()
        assert context.rollout_execution is retained and context.rollout_review_source is source
        assert context.path.read_bytes() == saved and checkpoint.to_dict() == frozen
