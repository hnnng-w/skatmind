"""Returned native forms for the exact installed-UAT evidence, with disposable data."""

import re

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_null_recording_end import HAND, PLAYS
from test_session_recorded_review_web import Browser, Forms


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def record_null_prefix(browser, count=8):
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/create"),
        game_name="Disposable Null recording", capture_mode="live", forehand_name="Bea",
        middlehand_name="Chris", rearhand_name="Alex", perspective_seat="rearhand",
        setup_action="update"))
    follow(browser, browser.submit(Forms(page).find("/sessions/create"), setup_action="create"))
    browser.command("set_game_metadata")
    page = follow(browser, browser.submit(Forms(browser.page()).find("/sessions/cards"),
                                         cards=HAND))
    options = re.search(r'<select name="player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    chris = next(value for value, label in re.findall(
        r'<option value="([^"]+)"[^>]*>(.*?)</option>', options) if label.startswith("Chris"))
    browser.command("set_declarer", player_id=chris)
    browser.command("set_declaration", game_type="null", bid_value="18", hand_game="false")
    for _, card in PLAYS[:count]:
        browser.command("record_play", card=card)
    return browser.page()


def test_returned_ninth_card_has_persistent_terminal_view(localized_server):
    browser = Browser(localized_server)
    page = record_null_prefix(browser)
    assert 'action="/sessions/play"' in page
    page = follow(browser, browser.submit(Forms(page).find("/sessions/play"), cards="HK"))
    assert "Null game lost" in page
    assert "Chris won trick 3. The game has ended." in page
    assert 'action="/sessions/play"' not in page
    assert 'href="#recorded-decisions"' in page


def test_actual_declaration_correction_lineage_then_decisive_append(localized_server):
    from test_match_card_correction_ui import activated_form
    from test_session_declaration_correction_web import PREFIX, names, select
    from test_session_recorded_review_web import record_score_review_game

    from skatmind.session_transitions import replay_session_state_v1
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=9, names=("Bea", "Chris", "Alex"))
    active = localized_server.app_context.managed_stateful.active_session
    page, editor = select(browser, "set_declarer")
    page = follow(browser, browser.submit(editor, player_id=names(page)["Chris"]))
    assert len(active.declaration_correction.preview.result.replayed_suffix_records) >= 9
    page = follow(browser, browser.submit(activated_form(page, PREFIX + "apply")))
    assert replay_session_state_v1(active.state).played_card_count == 9
    page, editor = select(browser, "set_declaration")
    page = follow(browser, browser.submit(editor, game_type="null"))
    candidate = active.declaration_correction.preview.result
    assert [r.command.card for r in candidate.discarded_suffix_records] == ["HK", "H9", "H10"]
    assert replay_session_state_v1(candidate.state).played_card_count == 6
    apply = Forms(page).find(PREFIX + "apply")
    before = active.path.read_bytes()
    assert browser.submit(apply)[0] == 400
    assert active.path.read_bytes() == before
    follow(browser, browser.submit(apply, confirm_apply="on"))
    for card in ("H9", "H10", "HK"):
        browser.command("record_play", card=card)
    facts = replay_session_state_v1(active.state)
    assert facts.played_card_count == 9 and facts.recording_rule_end.trick_number == 3
    assert "Chris won trick 3. The game has ended." in browser.page()


def test_one_durable_write_rejected_appends_passive_navigation_and_reopen(
    localized_server, monkeypatch,
):
    import skatmind.session_persistence as persistence
    from skatmind.app_web import execution
    from skatmind.session_transitions import replay_session_state_v1
    browser = Browser(localized_server)
    page = record_null_prefix(browser)
    active = localized_server.app_context.managed_stateful.active_session
    checkpoints = tuple(cp.to_dict() for cp in active.decision_checkpoints)
    writes = []
    real_replace = persistence.os.replace
    def replace(source, target):
        result = real_replace(source, target)
        if target == active.path:
            writes.append(target)
        return result
    def forbidden(*args, **kwargs):
        pytest.fail("Passive or capture operation executed analysis")
    monkeypatch.setattr(persistence.os, "replace", replace)
    monkeypatch.setattr(execution, "execute_guided_frontend_review_v1", forbidden)
    stale = Forms(page).find("/sessions/play")
    page = follow(browser, browser.submit(stale, cards="HK"))
    assert len(writes) == 1
    saved = active.path.read_bytes()
    assert tuple(cp.to_dict() for cp in active.decision_checkpoints) == checkpoints
    assert browser.submit(stale, cards="HK")[0] == 409
    assert browser.request("POST", "/sessions/command", {
        "managed_handle": active.handle, "expected_revision": str(active.state.revision),
        "kind": "record_play",
        "player_id": replay_session_state_v1(active.state).declarer_player_id,
        "card": "C8"})[0] == 400
    for locale, title in (("de", "Nullspiel verloren"), ("en", "Null game lost")):
        page = follow(browser, browser.submit(
            Forms(browser.page()).find("/actions/profile/language"), language=locale))
        assert title in page and 'action="/sessions/play"' not in page
        assert browser.request("GET", "/sessions/downloads/session.json")[2] == saved
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened.path.read_bytes() == saved and len(writes) == 1
    assert "Null game lost" in browser.page()


@pytest.mark.parametrize("fault", ("save", "conflict"))
def test_decisive_save_failure_has_no_partial_end_and_no_passive_retry(
    localized_server, monkeypatch, fault,
):
    import skatmind.api.v1.session as api
    import skatmind.api.v1.session.files as files
    import skatmind.session_persistence as persistence
    from skatmind.session_commands import SetSessionGameMetadataCommandV1
    from skatmind.session_transitions import replay_session_state_v1
    browser = Browser(localized_server)
    page = record_null_prefix(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before, document = active.path.read_bytes(), active.document
    calls = []
    real_replace = persistence.os.replace
    def fail(source, target):
        if target == active.path:
            calls.append(target)
            raise OSError("Synthetic pre-replacement failure")
        return real_replace(source, target)
    if fault == "save":
        monkeypatch.setattr(persistence.os, "replace", fail)
    else:
        external = api.apply_session_command(active.state, SetSessionGameMetadataCommandV1(
            expected_revision=active.state.revision, played_at="2026-10-01T12:00:00Z")).value.state
        files.save_session_file(active.path, api.build_session_persistence_document(external,
            decision_checkpoints=active.decision_checkpoints).value,
            expected_content_fingerprint=document.content_fingerprint)
        before = active.path.read_bytes()
    response = browser.submit(Forms(page).find("/sessions/play"), cards="HK")
    assert response[0] == 409
    assert active.document is document and active.path.read_bytes() == before
    assert replay_session_state_v1(active.state).recording_rule_end is None
    for _ in range(2):
        assert "Null game lost" not in browser.page()
    assert len(calls) == int(fault == "save") and active.path.read_bytes() == before


def record_null_match_prefix(browser, count=8):
    from test_match_recording_recovery_web import operation_form
    page = browser.page("/matches/new")
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        match_title="Disposable Null Match", forehand_name="Bea", middlehand_name="Chris",
        rearhand_name="Alex", perspective_seat="rearhand", platform_choice="in_person",
        setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
                                         setup_action="create"))
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    chris = next(value for value, label in re.findall(
        r'<option value="([^"]+)"[^>]*>(.*?)</option>', options) if label.startswith("Chris"))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=chris, game_type="null", bid_value="18"))
    for _, card in PLAYS[:count]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    return page


def test_match_returned_form_progress_guard_language_history_and_reopen(
    localized_server, monkeypatch,
):
    from test_match_recording_recovery_web import operation_form

    import skatmind.match_workspace_persistence as persistence
    from skatmind.match_workspace_persistence import load_match_workspace_file_v1
    browser = Browser(localized_server)
    page = record_null_match_prefix(browser)
    active = localized_server.app_context.managed_stateful.active_match
    writes = []
    real = persistence.os.replace
    def save(source, target):
        result = real(source, target)
        if target == active.path:
            writes.append(target)
        return result
    monkeypatch.setattr(persistence.os, "replace", save)
    stale = operation_form(page, "append_plays")
    page = follow(browser, browser.submit(stale, cards="HK"))
    assert "Chris won trick 3. The game has ended." in page
    assert 'href="/matches/position/2#match-recording"' in page
    assert not any(f["values"].get("operation") == "append_plays" for f in Forms(page).forms)
    assert len(writes) == 1
    saved = active.path.read_bytes()
    assert browser.submit(stale, cards="HK")[0] == 409
    assert browser.request("POST", "/matches/api/v1/operation", {
        "managed_handle": active.handle, "expected_revision": str(active.workspace.revision),
        "match_position": "1", "operation": "append_plays", "cards": "C8"})[0] in {400, 409}
    assert 'id="match-play-9"' in browser.page("/matches/review/1")
    page = follow(browser, browser.submit(Forms(browser.page("/matches/current")).find(
        "/actions/profile/language"), language="de"))
    assert "Nullspiel verloren" in page
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
    assert active.path.read_bytes() == saved and len(writes) == 1
    assert active.workspace.slots[1].slot_kind == "empty"


def test_null_frozen_review_downloads_survive_reads_and_end_requires_no_analysis(
    localized_server, monkeypatch,
):
    from skatmind.app_web import session_frontend, session_recorded_review
    from skatmind.app_web.session_frontend import (
        default_guided_session_execution_options_v1,
        default_session_position_export_options_v1,
        execute_guided_session_position_v1,
    )
    browser = Browser(localized_server)
    page = record_null_prefix(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(page).find("/sessions/review-decision")))
    retained = active.execution
    downloads = {name: browser.request("GET", f"/sessions/downloads/{name}.json")[2]
                 for name in ("request", "result")}
    assert active.path.read_bytes() == before
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(1)
        pytest.fail("No automatic analysis or fallback is allowed")
    monkeypatch.setattr(session_frontend, "execute_guided_frontend_analysis_v1", forbidden)
    monkeypatch.setattr(session_recorded_review, "execute_guided_frontend_review_v1", forbidden)
    for _ in range(2):
        browser.page()
        for name, raw in downloads.items():
            assert browser.request("GET", f"/sessions/downloads/{name}.json")[2] == raw
    assert active.execution is retained
    follow(browser, browser.submit(Forms(page).find("/sessions/play"), cards="HK"))
    assert active.execution is None  # A genuine source mutation keeps existing invalidation.
    outcome = execute_guided_session_position_v1(active,
        export_options=default_session_position_export_options_v1(),
        execution_options=default_guided_session_execution_options_v1())
    assert outcome.status == "unavailable" and calls == []
    assert retained.request.document["completed_tricks"] == ()


def test_match_decisive_replace_failure_does_not_publish_or_retry(localized_server, monkeypatch):
    from test_match_recording_recovery_web import operation_form

    import skatmind.match_workspace_persistence as persistence
    browser = Browser(localized_server)
    page = record_null_match_prefix(browser)
    active = localized_server.app_context.managed_stateful.active_match
    before, workspace = active.path.read_bytes(), active.workspace
    calls = []
    real = persistence.os.replace
    def fail(source, target):
        if target == active.path:
            calls.append(target)
            raise OSError("Synthetic decisive-card replacement failure")
        return real(source, target)
    monkeypatch.setattr(persistence.os, "replace", fail)
    response = browser.submit(operation_form(page, "append_plays"), cards="HK")
    assert response[0] == 409
    assert active.workspace is workspace and active.path.read_bytes() == before
    assert "Null game lost" not in browser.page("/matches/current")
    assert len(calls) == 1


def test_rule_end_does_not_enable_null_rollout_or_fallback(localized_server, monkeypatch):
    import skatmind.recommendation_workflow as workflow
    import skatmind.whole_game_rollout as core
    from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
    browser = Browser(localized_server)
    page = record_null_prefix(browser, count=9)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    def forbidden(*a, **kw):
        pytest.fail("Unsupported Null rollout must not sample or fall back")
    monkeypatch.setattr(core, "build_compatible_search_world_space", forbidden)
    monkeypatch.setattr(workflow, "recommend_card_by_expected_value", forbidden)
    response = browser.submit(Forms(page).find("/sessions/review-whole-game"),
        objective="complete_settlement", requested_worlds="1")
    assert response[0] == 400
    assert text("en", "rollout.reason.unsupported_game_type") in response[2].decode()
    assert active.path.read_bytes() == before
