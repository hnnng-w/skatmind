"""Native posts, source-owned timeouts and original downloads over small genuine games."""

from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_guided_historical_review_form import _completed_example_draft
from test_match_recording_recovery_web import follow, operation_form
from test_match_rollout_web import downloads, open_alex
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from whole_game_review_fixtures import activate_ten_decisions, ten_decision_document

from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_analysis_contracts import (
    MatchDecisionAnalysisOptionsV1,
    build_match_analysis_report_v1,
)
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

PRESETS = (("quick", 25, 250, 5000), ("standard", 100, 1000, 30000),
           ("more_time", 400, 4000, 60000))


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def last_session_form(browser):
    return Forms(browser.page()).find("/sessions/review-whole-game", index=9)


def last_match(server, *, decision=30):
    browser, path, page = open_alex(server, count=30)
    page = follow(browser, browser.submit(Forms(page).find("/matches/select-decision"),
                                          decision_index=str(decision)))
    return browser, path, page


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_native_rollout_presets_custom_retry_languages_and_downloads(localized_server, family):
    if family == "sessions":
        active = activate_ten_decisions(localized_server, bid_value=18)
        browser, path = Browser(localized_server), active.path
        def form():
            return Forms(browser.page()).find("/sessions/review-whole-game", index=8)
        def retained():
            return active.rollout_execution.request.document["whole_game_rollout_settings"]
        def artifacts():
            return {kind: browser.request("GET", f"/sessions/downloads/rollout-{kind}.json")[2]
                    for kind in ("request", "result")}
    else:
        browser, path, _ = last_match(localized_server, decision=27)
        active = localized_server.app_context.managed_stateful.active_match
        def form():
            return Forms(browser.page("/matches/review/2")).find("/matches/review-whole-game")
        def retained():
            return active.capture.report_store.list()[-1].value.request.document[
                "whole_game_rollout_settings"]
        def artifacts():
            return downloads(browser, browser.page("/matches/reports/"
                + active.capture.report_store.list()[-1].report_id))
    before = path.read_bytes()
    for effort, worlds, _, timeout in PRESETS:
        response = browser.submit(form(), settings_mode="ordinary", analysis_effort=effort,
            objective="played_game_goal", requested_worlds="3", random_seed="17")
        assert response[0] == 303, response[2].decode()
        assert (retained()["requested_worlds"], retained()["wall_clock_timeout_ms"]) == (
            worlds, timeout)
        assert retained()["random_seed"] == 17
    originals = artifacts()
    # Inactive custom worlds survive an ordinary run, even with the disclosure closed.
    assert form()["values"]["requested_worlds"] == "3"
    response = browser.submit(form(), settings_mode="custom", random_seed="invalid")
    assert response[0] == 400
    page = response[2].decode()
    tree = Hierarchy(page)
    invalid = next(node for node in tree.nodes if node["attrs"].get("name") == "random_seed"
                   and "aria-invalid" in node["attrs"])
    assert any(node["tag"] == "details" and "open" in node["attrs"] for node in invalid["parents"])
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert text(locale, "analysis.mode.custom") in page
        assert artifacts() == originals
    retry = next(item for item in Forms(page).forms
                 if item["action"] == f"/{family}/review-whole-game"
                 and item["values"].get("random_seed") == "invalid")
    assert retry["values"]["settings_mode"] == "custom"
    assert browser.submit(retry, random_seed="19", analysis_effort="quick")[0] == 303
    assert (retained()["requested_worlds"], retained()["wall_clock_timeout_ms"]) == (3, 60000)
    assert path.read_bytes() == before


@pytest.mark.parametrize("family", ("sessions", "matches"))
@pytest.mark.parametrize("timeout", (5000, 60000, 12345))
def test_reopened_retained_configuration_is_timeout_authority(localized_server, family, timeout):
    settings = WholeGameRolloutSettingsV1(requested_worlds=1, random_seed=7,
        wall_clock_timeout_ms=timeout, max_card_transitions=200000, max_preparation_work=90000)
    if family == "sessions":
        active = activate_ten_decisions(localized_server, bid_value=18)
        browser = Browser(localized_server)
        selection = last_session_form(browser)["values"]["decision_selection"]
        execute_recorded_session_decision_v1(localized_server.app_context, active,
                                             selection=selection, rollout_settings=settings)
        def get_form():
            return last_session_form(browser)
        def get_settings():
            return active.rollout_execution.request.document["whole_game_rollout_settings"]
    else:
        browser, _, _ = last_match(localized_server)
        active = localized_server.app_context.managed_stateful.active_match
        value = execute_match_decision_analysis_v1(active.workspace, match_position=2,
            decision_index=30, options=MatchDecisionAnalysisOptionsV1(
                recommendation_method="whole_game_rollout", use_profile_presets=False,
                rollout_settings=settings))
        active.capture.report_store.put(build_match_analysis_report_v1(value))
        def get_form():
            return Forms(browser.page("/matches/review/2")).find("/matches/review-whole-game")
        def get_settings():
            return active.capture.report_store.list()[-1].value.request.document[
                "whole_game_rollout_settings"]
    active.analysis_forms.clear()
    native = get_form()
    assert native["values"]["settings_mode"] == "custom"
    assert browser.submit(native, random_seed="8", analysis_effort="standard")[0] == 303
    assert get_settings()["wall_clock_timeout_ms"] == timeout
    assert get_settings()["requested_worlds"] == 1
    assert get_settings()["max_card_transitions"] == 200000
    assert get_settings()["max_preparation_work"] == 90000
    assert browser.submit(get_form(), wall_clock_timeout_ms="30000")[0] == 400


def test_guided_native_position_effective_presets_and_preserved_custom(localized_server):
    active = activate_ten_decisions(localized_server, bid_value=18)
    root = active.decision_checkpoints[-2].request.to_dict()["document"]
    browser = Browser(localized_server)
    page = browser.page("/analyze")
    base = {name: root[name] for name in ("game_type", "player_role", "player_position",
        "declarer_player", "trick_leader", "hand", "declarer_points", "defender_points")}
    base["current_trick"] = root["current_trick"] or [""]
    for i, trick in enumerate(root["completed_tricks"], 1):
        base[f"completed_trick_{i}_leader"] = trick["players"][0]
        for j, card in enumerate(trick["cards"], 1):
            base[f"completed_trick_{i}_card_{j}"] = card
    for effort, _, samples, _ in PRESETS:
        form = Forms(page).find("/actions/analyze/run-guided")
        page = follow(browser, browser.submit(form, **base, analysis_effort=effort,
            sample_count="3", random_seed="19", include_provenance="on"))
        current = localized_server.app_context.analyze_state.latest_successful_request
        assert current.document["sample_count"] == samples and current.document["random_seed"] == 19
    form = Forms(page).find("/actions/analyze/run-guided")
    assert form["values"]["sample_count"] == "3"
    page = follow(browser, browser.submit(form, settings_mode="custom",
                                          analysis_method="bounded_search"))
    retained = browser.request("GET", "/downloads/analyze/request.json")
    assert retained[0] == 200
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        form = Forms(page).find("/actions/analyze/run-guided")
        assert form["values"]["settings_mode"] == "custom"
        assert form["values"]["analysis_method"] == "bounded_search"
        assert form["values"]["include_provenance"] == "on"
        downloaded = browser.request("GET", "/downloads/analyze/request.json")
        assert (downloaded[0], downloaded[2]) == (200, retained[2])
    page = follow(browser, browser.submit(form, analysis_effort="quick"))
    current = localized_server.app_context.analyze_state.latest_successful_request
    assert current.document["recommendation_method"] == "bounded_search"
    assert current.document["sample_count"] == 3


def test_fresh_manual_default_native_options_additional_and_result_only(localized_server):
    browser = Browser(localized_server)
    page = browser.page("/review")
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/start")))
    app = localized_server.app_context
    fresh = app.review_state.draft
    assert fresh.options.immediate_review
    # Use a genuine completed synthetic game instead of manually entering thirty cards.
    app.review_state = replace(app.review_state, draft=replace(_completed_example_draft(), step=6,
        options=fresh.options, analysis_form_values=fresh.analysis_form_values))
    page = browser.page("/review")
    for effort, count, _, _ in PRESETS:
        form = Forms(page).find("/actions/review/update-options")
        page = follow(browser, browser.submit(form, analysis_effort=effort,
            immediate_sample_count="3", immediate_base_random_seed="19", tactical="on",
            include_provenance="on"))
        assert app.review_state.draft.options.immediate_sample_count == count
        assert app.review_state.draft.options.immediate_review
        page = follow(browser, browser.submit(Forms(page).find("/actions/review/back")))
    form = Forms(page).find("/actions/review/update-options")
    assert form["values"]["immediate_sample_count"] == "3"
    assert form["values"]["include_provenance"] == "on"
    form["values"].pop("immediate_review")
    page = follow(browser, browser.submit(form, settings_mode="custom"))
    assert not app.review_state.draft.options.immediate_review
    assert app.review_state.draft.options.tactical
    assert app.review_state.draft.options.include_provenance
    assert app.review_state.draft.options.immediate_sample_count == 3
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/run-guided")))
    result = app.review_state.latest_successful_result.result.document["historical_game_summary"]
    assert "historical_tactical_motif_review_summary" in result
    assert "historical_game_review_summary" not in result
    original = browser.request("GET", "/downloads/review/result.json")
    assert original[0] == 200
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    downloaded = browser.request("GET", "/downloads/review/result.json")
    assert (downloaded[0], downloaded[2]) == (200, original[2])


def test_match_legacy_native_custom_and_existing_profile_availability(localized_server):
    browser, _, page = last_match(localized_server, decision=27)
    active = localized_server.app_context.managed_stateful.active_match
    for effort, count, _, _ in PRESETS:
        page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
            analysis_effort=effort, immediate_sample_count="3", immediate_random_seed="19"))
        report = active.capture.report_store.list()[-1]
        assert report.value.options.immediate_sample_count == count
        assert report.value.options.immediate_random_seed == 19
    assert text("en", "analysis.opponents") not in page
    assert text("en", "analysis.no_opponents") in page
    native = operation_form(page, "analyze_decision")
    assert native["values"]["immediate_sample_count"] == "3"
    page = follow(browser, browser.submit(native, settings_mode="custom",
        recommendation_method="information_set_search", search_budget_profile="interactive_v1"))
    options = active.capture.report_store.list()[-1].value.options
    assert options.recommendation_method == "information_set_search"
    assert options.search_budget_profile == "interactive_v1"
    assert options.immediate_sample_count == 3
    from skatmind.app_web.match_frontend import reload_unified_match_v1
    assert active.analysis_forms
    reload_unified_match_v1(active)
    fresh = operation_form(browser.page("/matches/review/2"), "analyze_decision")
    assert fresh["values"]["settings_mode"] == "ordinary"
    assert fresh["values"]["immediate_sample_count"] == "100"
    materialize = operation_form(browser.page("/matches/review/2"), "prepare_materialization")
    assert not {"settings_mode", "analysis_effort"} & materialize["values"].keys()
    assert browser.submit(materialize)[0] == 303


def open_profile_match(server, *, timing="before", actor_only=False):
    from test_match_decision_analysis import _complete_workspace
    from test_match_player_statistics_context import _actionable_snapshot, _capture_with_snapshots
    from test_recorded_review_navigation import chooser_form, home_chooser

    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    snapshots = tuple(_actionable_snapshot(player, "snapshot-" + player)
                      for player in (("player-a",) if actor_only else
                                     ("player-a", "player-b", "player-c")))
    played_at = {"before": "2026-08-09T18:00:00Z", "equal": snapshots[0].observed_at,
                 "unknown": None}[timing]
    workspace = _complete_workspace(definition=_capture_with_snapshots(
        played_at=played_at, snapshots=snapshots))
    path = server.app_context.managed_stateful.root("matches") / "profile-controls.json"
    assert save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(
        workspace), expected_content_fingerprint=None).status == "saved"
    browser = Browser(server)
    follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    page = browser.page("/matches/review/3")
    page = follow(browser, browser.submit(Forms(page).find("/matches/select-decision"),
                                         decision_index="1"))
    return browser, path, page


@pytest.mark.parametrize("timing,actor_only,eligible", (
    ("before", False, True), ("equal", False, False), ("unknown", False, False),
    ("before", True, False)))
def test_opponent_choice_uses_actual_time_safe_nonactor_sources(
    localized_server, timing, actor_only, eligible,
):
    browser, _, page = open_profile_match(localized_server, timing=timing, actor_only=actor_only)
    tree = Hierarchy(page)
    field = next(node for node in tree.nodes if node["attrs"].get("name") == "use_profile_presets"
        and any(parent["tag"] == "form" and parent["attrs"].get("action") ==
                "/matches/api/v1/analysis" for parent in node["parents"]))
    owner = next(parent for parent in field["parents"] if parent["tag"] == "form")
    inside = field["parents"][field["parents"].index(owner) + 1:]
    assert any(parent["tag"] == "details" for parent in inside) is not eligible
    assert text("en", "analysis.opponents") in owner["text"] if eligible else (
        text("en", "analysis.no_opponents") in owner["text"])
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
        settings_mode="custom", immediate_sample_count="1"))
    active = localized_server.app_context.managed_stateful.active_match
    binding = active.capture.report_store.list()[-1].value.profile_binding
    assert (binding.left_profile_available or binding.right_profile_available) is eligible
    rollout = Forms(page).find("/matches/review-whole-game")
    assert "use_profile_presets" not in rollout["values"]


def test_session_current_position_native_presets_and_custom_are_source_scoped(localized_server):
    import skatmind.api.v1.session as session_api
    from skatmind.app_web.session_frontend import import_guided_session_v1
    from skatmind.session_history import build_session_state_from_accepted_prefix_v1

    document = ten_decision_document(bid_value=18)
    checkpoint = document.decision_checkpoints[-2]
    prefix = build_session_state_from_accepted_prefix_v1(document.state,
        target_revision=checkpoint.source_revision)
    current = session_api.build_session_persistence_document(prefix).value
    app = localized_server.app_context
    active = import_guided_session_v1(app.managed_stateful.root("sessions"),
        handle="a" * 64, document=current.to_dict())
    app.managed_stateful.activate_session(active)
    browser = Browser(localized_server)
    for effort, count, _, _ in PRESETS:
        form = Forms(browser.page()).find("/sessions/analyze")
        response = browser.submit(form, analysis_effort=effort, sample_count="3", random_seed="19")
        assert response[0] == 303
        assert active.execution.request.document["sample_count"] == count
        assert active.execution.request.document["random_seed"] == 19
    form = Forms(browser.page()).find("/sessions/analyze")
    assert form["values"]["sample_count"] == "3"
    response = browser.submit(form, settings_mode="custom", recommendation_method="bounded_search")
    assert response[0] == 303
    before = active.execution.request_json_bytes
    page = follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                                          language="de"))
    form = Forms(page).find("/sessions/analyze")
    assert form["values"]["settings_mode"] == "custom"
    assert browser.request("GET", "/sessions/downloads/request.json")[2] == before
    assert browser.submit(form, analysis_effort="quick")[0] == 303
    assert active.execution.request.document["sample_count"] == 3
    assert active.execution.request.document["recommendation_method"] == "bounded_search"
