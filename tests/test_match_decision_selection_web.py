"""Selected Match intent must match the installed source-bound analysis controls."""

import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from threading import Event

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_match_rollout_web import downloads, form, open_alex
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Forms

import skatmind.app_web.match_decision_selection as selection
import skatmind.app_web.match_rollout_frontend as rollout
import skatmind.capture_web.analysis as legacy
import skatmind.capture_web.context as capture
from skatmind.app_web.stateful_localization import text

ROUTE = "/matches/select-decision"


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def choose(browser, page, decision, *, enhanced=False):
    selected = Forms(page).find(ROUTE)
    values = {**selected["values"], "decision_index": str(decision)}
    return browser.request("POST", ROUTE, values, headers=(
        {"X-SkatMind-Selection": "prepare"} if enhanced else None))


def controls(page):
    return next(node for node in Hierarchy(page).nodes
                if "data-match-analysis-controls" in node["attrs"])


def test_unapplied_visible_alex_rejects_both_old_bea_actions(localized_server, monkeypatch):
    browser, path, page = open_alex(localized_server, count=30)
    before = path.read_bytes()
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(1)
        pytest.fail("Unapplied visible choice must not evaluate or save")
    monkeypatch.setattr(rollout, "execute_match_decision_analysis_v1", forbidden)
    monkeypatch.setattr(legacy, "execute_match_decision_analysis_v1", forbidden)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", forbidden)
    assert form(page)["values"]["decision_index"] == "1"
    assert "hidden" in controls(page)["attrs"]
    for submitted in (form(page), operation_form(page, "analyze_decision")):
        assert submitted["values"]["decision_index"] == "1"
        response = browser.submit(submitted, visible_decision_index="3")
        assert response[0] == 409
        assert text("en", "validation.match_selection.unapplied") in unescape(response[2].decode())
    assert not calls and path.read_bytes() == before


@pytest.mark.parametrize("enhanced", (False, True))
def test_selection_only_refreshes_context_then_explicit_action_is_alex(
    localized_server, monkeypatch, enhanced,
):
    browser, path, page = open_alex(localized_server, count=30)
    before = path.read_bytes()
    calls = []
    real = rollout.execute_match_decision_analysis_v1
    def counted(*args, **kwargs):
        calls.append(kwargs["decision_index"])
        return real(*args, **kwargs)
    monkeypatch.setattr(rollout, "execute_match_decision_analysis_v1", counted)
    response = choose(browser, page, 3, enhanced=enhanced)
    assert response[0] == (200 if enhanced else 303)
    page = response[2].decode() if enhanced else follow(browser, response)
    assert not calls and path.read_bytes() == before
    assert form(page)["values"]["decision_index"] == "3"
    assert form(page)["values"]["visible_decision_index"] == "3"
    assert operation_form(page, "analyze_decision")["values"]["decision_index"] == "3"
    assert form(page)["values"]["analysis_matadors"] == ""
    assert "analysis_bid_value" not in form(page)["values"]
    assert "hidden" not in controls(page)["attrs"]
    selector = next(n for n in Hierarchy(page).nodes if "data-decision-selector" in n["attrs"])
    assert "hidden" in selector["attrs"]  # Script alone exposes the editable selector here.
    response = browser.submit(form(page), requested_worlds="1", analysis_matadors="1")
    assert response[0] == 303
    page = follow(browser, response)
    active = localized_server.app_context.managed_stateful.active_match
    value = active.capture.report_store.list()[0].value
    assert value.decision_index == 3 and value.profile_binding.acting_player_id == "alex"
    assert value.request.document["actual_card_played"] == "C7"
    assert value.result.document["whole_game_rollout_comparison"]["actual_card"] == "C7"
    assert calls == [3] and path.read_bytes() == before
    assert len(downloads(browser, page)) == 2


def test_selection_keeps_prior_evidence_and_legacy_action_independent(localized_server):
    browser, path, page = open_alex(localized_server, count=30)
    page = follow(browser, choose(browser, page, 1))
    page = follow(browser, browser.submit(form(page), requested_worlds="1", analysis_matadors="2"))
    prior = downloads(browser, page)
    active = localized_server.app_context.managed_stateful.active_match
    first = active.capture.report_store.list()[0]
    page = choose(browser, page, 3, enhanced=True)[2].decode()
    assert downloads(browser, page) == prior
    assert form(page)["values"]["analysis_matadors"] == ""
    response = browser.submit(operation_form(page, "analyze_decision"), immediate_sample_count="1")
    assert response[0] == 303
    report = active.capture.report_store.list()[-1]
    assert report.value.decision_index == 3
    assert report.value.options.recommendation_method == "immediate_expected_value"
    assert active.capture.report_store.list()[0] is first
    for route, content in prior.items():
        assert browser.request("GET", route)[2] == content
    page = choose(browser, follow(browser, response), 1, enhanced=True)[2].decode()
    assert form(page)["values"]["analysis_matadors"] == "2"


@pytest.mark.parametrize("field,value", (
    ("decision_index", ""), ("decision_index", "31"), ("selection_context", "f" * 64),
    ("expected_revision", "0"), ("match_position", "1"),
    ("return_to", "/matches/review/1"),
))
def test_unknown_foreign_missing_and_stale_selections_never_fall_back(
    localized_server, field, value,
):
    browser, path, page = open_alex(localized_server, count=30)
    selected = Forms(page).find(ROUTE)
    response = browser.submit(selected, **{field: value})
    assert response[0] == 409
    active = localized_server.app_context.managed_stateful.active_match
    assert not active.capture.report_store.list() and active.selected_review_decision is None
    values = dict(selected["values"])
    values.pop(field)
    assert browser.request("POST", ROUTE, values)[0] == 409


def test_stale_selection_response_cannot_apply_after_a_newer_context(localized_server):
    browser, path, page = open_alex(localized_server, count=30)
    old = Forms(page).find(ROUTE)
    current = choose(browser, page, 3, enhanced=True)[2].decode()
    assert browser.submit(old, decision_index="1")[0] == 409
    active = localized_server.app_context.managed_stateful.active_match
    assert active.selected_review_decision == 3
    assert choose(browser, current, 1, enhanced=True)[0] == 200
    assert active.selected_review_decision == 1


def test_failed_preparation_disables_old_context_and_supports_explicit_recovery(localized_server):
    browser, path, page = open_alex(localized_server, count=3)
    old = form(page)
    response = choose(browser, page, 2, enhanced=True)
    assert response[0] == 409
    page = response[2].decode()
    assert 'data-ready="false"' in page and "hidden" in controls(page)["attrs"]
    assert browser.submit(old, requested_worlds="1", objective="played_game_goal")[0] == 409
    assert choose(browser, page, 3, enhanced=True)[0] == 200
    active = localized_server.app_context.managed_stateful.active_match
    assert not active.capture.report_store.list()


@pytest.mark.parametrize("method", ("rollout", "legacy"))
def test_selection_supersedes_inflight_analysis_before_publication(
    localized_server, monkeypatch, method,
):
    browser, path, page = open_alex(localized_server, count=30)
    entered, selected, release = Event(), Event(), Event()
    owner = rollout if method == "rollout" else legacy
    real = owner.execute_match_decision_analysis_v1
    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(15)
        return real(*args, **kwargs)
    apply = selection.apply_match_decision_selection
    def apply_counted(*args):
        result = apply(*args)
        selected.set()
        return result
    monkeypatch.setattr(owner, "execute_match_decision_analysis_v1", delayed)
    monkeypatch.setattr(selection, "apply_match_decision_selection", apply_counted)
    submitted = form(page) if method == "rollout" else operation_form(page, "analyze_decision")
    settings = ({"objective": "played_game_goal", "requested_worlds": "1"}
                if method == "rollout" else {"immediate_sample_count": "1"})
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(browser.submit, submitted, **settings)
        assert entered.wait(10)
        second = pool.submit(choose, browser, page, 3, enhanced=True)
        assert selected.wait(10)
        release.set()
        assert first.result()[0] == 409
        assert second.result()[0] == 200
    active = localized_server.app_context.managed_stateful.active_match
    assert active.selected_review_decision == 3 and not active.capture.report_store.list()


def test_language_return_retains_exact_selected_controls_and_values(localized_server):
    browser, path, page = open_alex(localized_server, count=30)
    page = choose(browser, page, 3, enhanced=True)[2].decode()
    response = browser.submit(form(page), requested_worlds="1", analysis_matadors="0")
    assert response[0] == 400
    page = response[2].decode()
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert form(page)["values"]["decision_index"] == "3"
        assert form(page)["values"]["analysis_matadors"] == "0"
        assert re.search(r'data-applied="3"', page)


@pytest.mark.parametrize("when", ("before", "during"))
def test_changed_source_cannot_publish_a_prepared_selection(localized_server, monkeypatch, when):
    from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    browser, path, page = open_alex(localized_server, count=30)
    active = localized_server.app_context.managed_stateful.active_match
    source = active.workspace
    changed = mark_match_workspace_passed_deal_v1(source, match_position=3,
        expected_revision=source.revision, game_timecode=None).workspace
    def change_file():
        assert save_match_workspace_file_v1(path,
            build_match_workspace_persistence_document_v1(changed),
            expected_content_fingerprint=active.capture.content_fingerprint).status == "saved"
    prepare = selection.build_match_decision_position_request_v1
    def prepare_then_change(*args, **kwargs):
        result = prepare(*args, **kwargs)
        change_file()
        return result
    if when == "before":
        change_file()
    else:
        monkeypatch.setattr(selection, "build_match_decision_position_request_v1",
                            prepare_then_change)
    response = choose(browser, page, 3, enhanced=True)
    assert response[0] == 409 and active.selected_review_decision is None
    assert not active.capture.report_store.list() and active.workspace is source


@pytest.mark.parametrize("method", ("rollout", "legacy"))
@pytest.mark.parametrize("field", ("visible_decision_index", "decision_selection"))
def test_analysis_requires_explicit_intent_and_bound_proof(localized_server, method, field):
    browser, path, page = open_alex(localized_server, count=30)
    submitted = form(page) if method == "rollout" else operation_form(page, "analyze_decision")
    submitted["values"].pop(field)
    assert browser.submit(submitted)[0] == 409
    active = localized_server.app_context.managed_stateful.active_match
    assert not active.capture.report_store.list()


def test_stale_legacy_settings_do_not_restore_into_another_decision(localized_server):
    browser, path, page = open_alex(localized_server, count=30)
    old = operation_form(page, "analyze_decision")
    choose(browser, page, 3, enhanced=True)
    response = browser.submit(old, immediate_random_seed="123")
    assert response[0] == 409
    current = operation_form(response[2].decode(), "analyze_decision")["values"]
    assert current["decision_index"] == "3" and current["immediate_random_seed"] == "0"


@pytest.mark.parametrize("view", ("report", "recording"))
def test_failed_enhanced_selection_retains_the_page_manifest_and_report_owner(
    localized_server, monkeypatch, view,
):
    browser, path, page = open_alex(localized_server, count=30)
    page = follow(browser, choose(browser, page, 3))
    page = follow(browser, browser.submit(form(page), requested_worlds="1", analysis_matadors="1"))
    prior = downloads(browser, page)
    if view == "recording":
        page = browser.page("/matches/position/2")
    language = Forms(page).find("/actions/profile/language")
    def fail(*args, **kwargs):
        raise ValueError("Synthetic preparation failure")
    monkeypatch.setattr(selection, "build_match_decision_position_request_v1", fail)
    response = choose(browser, page, 1, enhanced=True)
    assert response[0] == 409
    failed = response[2].decode()
    assert Forms(failed).find("/actions/profile/language")["values"]["return_to"] == (
        language["values"]["return_to"])
    assert failed.count("<details") == page.count("<details")
    if view == "report":
        assert downloads(browser, failed) == prior
    page = follow(browser, browser.submit(Forms(failed).find("/actions/profile/language"),
                                          language="de"))
    assert 'data-ready="false"' in page


def test_removed_selected_decision_requires_a_new_explicit_choice(localized_server):
    from skatmind.app_web.match_frontend import apply_unified_match_operation_v1

    browser, path, page = open_alex(localized_server, count=30)
    page = follow(browser, choose(browser, page, 30))
    old = form(page)
    active = localized_server.app_context.managed_stateful.active_match
    result = apply_unified_match_operation_v1(active, {
        "operation": "truncate_plays", "match_position": "2", "target_play_count": "27",
        "expected_revision": str(active.workspace.revision)})
    assert result.status == "applied"
    page = browser.page("/matches/review/2")
    assert Forms(page).find(ROUTE)["values"]["decision_index"] == ""
    assert not any(item["action"] == "/matches/review-whole-game" for item in Forms(page).forms)
    assert 'data-ready="false"' in page
    assert browser.submit(old, requested_worlds="1", objective="played_game_goal")[0] == 409
    response = choose(browser, page, 3, enhanced=True)
    assert response[0] == 200 and form(response[2].decode())["values"]["decision_index"] == "3"
    assert not active.capture.report_store.list()
