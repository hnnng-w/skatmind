import json
import re

import pytest
from test_compact_card_entry_web import create_live
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_game import build_historical_input
from test_match_recording_recovery_web import entry_action, follow, operation_form, start_match
from test_recorded_trick_progress_web import summary_html
from test_session_recorded_review_web import Browser, Forms, review_first

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.execution as execution
import skatmind.capture_web.analysis as match_analysis
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.capture_web.context import MatchCaptureWebContextV1
from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def pair_html(page):
    match = re.search(
        r'<div class="accepted-declaration" data-unplayed-cards>.*?</div>', page, re.S)
    return "" if match is None else match[0]


def assert_pair(page, pair, *, hand=False, locale="en"):
    block = pair_html(page)
    assert block and page.count("data-unplayed-cards") == 1
    assert text(locale, "unplayed.derived") in block
    assert text(locale, "unplayed.hand_skat" if hand else "unplayed.discards") in block
    assert re.findall(r'aria-label="[^"()]+\(([^)]+)\)"', block) == list(pair)
    if hand:
        assert text(locale, "unplayed.no_discards") in block
    return block


def setup_session(browser, *, hand=False, count=29):
    form = create_live(browser)
    data = build_historical_input(hand_game=hand)
    page = follow(browser, browser.submit(form, cards=data["players"][0]["initial_hand"]))
    active = browser.server.app_context.managed_stateful.active_session
    assert active.state.revision == 11
    opponent = active.state.players[1].player_id
    browser.command("set_declarer", player_id=opponent)
    browser.command("set_declaration", game_type="grand", hand_game="true" if hand else "false")
    plays = [p for trick in data["tricks"] for p in trick["plays"]]
    page = browser.page()
    for play in plays[:count]:
        page = follow(browser, browser.submit(
            Forms(page).find("/sessions/play"), cards=play["card"]))
    return page, plays


def setup_match(browser, *, hand=False, count=29):
    page = start_match(browser)
    if not hand:
        form = operation_form(page, "set_declaration")
        form["values"].pop("hand_game", None)
        page = follow(browser, browser.submit(form))
    data = build_historical_input(hand_game=hand)
    plays = [p for trick in data["tricks"] for p in trick["plays"]]
    for play in plays[:count]:
        page = follow(browser, browser.submit(
            operation_form(page, "append_plays"), cards=play["card"]))
    return page, plays


@pytest.mark.parametrize("hand", (False, True))
def test_session_real_final_save_end_reopen_review_passive_bytes_and_undo(
    localized_server, monkeypatch, hand,
):
    browser = Browser(localized_server)
    counts = {"save": 0, "execute": 0}
    real_save, real_execute = session_files.save_session_file, execution.execute
    def save(*args, **kwargs):
        counts["save"] += 1
        return real_save(*args, **kwargs)
    def execute(*args, **kwargs):
        counts["execute"] += 1
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    monkeypatch.setattr(execution, "execute", execute)
    page, plays = setup_session(browser, hand=hand)
    active = localized_server.app_context.managed_stateful.active_session
    assert not pair_html(page) and counts == {"save": 33, "execute": 0}
    frozen = active.decision_checkpoints[0].request.to_dict()["document"]
    source, before = active.document, active.path.read_bytes()
    final_form = Forms(page).find("/sessions/play")
    rejected = browser.submit(final_form, cards=plays[0]["card"])
    assert rejected[0] == 400 and not pair_html(rejected[2].decode())
    assert active.document is source and active.path.read_bytes() == before
    # Fault-injected storage failure is separate from the real duplicate rejection.
    with monkeypatch.context() as fault:
        def fail(*args, **kwargs):
            raise OSError("Injected final-Card pre-save failure")
        fault.setattr(session_files, "save_session_file", fail)
        failed = browser.submit(final_form, cards=plays[-1]["card"])
    assert failed[0] == 409 and not pair_html(failed[2].decode())
    assert active.path.read_bytes() == before and active.document is source
    page = follow(browser, browser.submit(final_form, cards=plays[-1]["card"]))
    expected = ("D8", "D7") if hand else ("SK", "SQ")
    assert_pair(page, expected, hand=hand)
    assert ('<p>' + text("en", "task.discards") + '</p>' + text("en", "task.unknown")) not in page
    assert counts == {"save": 34, "execute": 0}
    facts = replay_session_state_v1(active.state)
    assert facts.known_skat == facts.discarded_cards == ()
    assert len(facts.initial_known_hands) == 1 and active.state.phase == "play"
    assert active.state.validation.historical_export.status == "unavailable"
    assert [r.command.kind for r in active.state.command_log].count("set_game_metadata") == 1
    assert active.decision_checkpoints[0].request.to_dict()["document"] == frozen
    assert browser.submit(final_form, cards=plays[-1]["card"])[0] == 409
    browser.command("set_game_end")
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    page, _ = review_first(browser)
    downloads = tuple(browser.request("GET", f"/sessions/downloads/{kind}.json")[2]
                      for kind in ("session", "request", "result"))
    assert json.loads(downloads[1]) == {**frozen, "analysis_mode": "post_game_review",
                                      "actual_card_played": plays[0]["card"]}
    assert counts == {"save": 35, "execute": 1}
    retained, checkpoints = active.execution, active.decision_checkpoints
    totals = summary_html(page)
    def forbidden(*args, **kwargs):
        pytest.fail("Passive conclusion must not collect, save, or execute")
    import skatmind.app_web.session_frontend as frontend
    with monkeypatch.context() as guard:
        guard.setattr(frontend, "_collect_current_checkpoint", forbidden)
        guard.setattr(session_files, "save_session_file", forbidden)
        guard.setattr(execution, "execute", forbidden)
        for locale in ("de", "en"):
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
            assert_pair(page, expected, hand=hand, locale=locale)
            assert active.execution is retained and active.decision_checkpoints == checkpoints
            assert tuple(browser.request("GET", f"/sessions/downloads/{kind}.json")[2]
                         for kind in ("session", "request", "result")) == downloads
            assert active.path.read_bytes() == downloads[0]
        assert summary_html(page) == totals
    # Actual accepted Undo removes End and the last Play, not recorded evidence.
    last_play = next(r for r in reversed(active.state.command_log)
                     if r.command.kind == "record_play")
    page = follow(browser, browser.submit(Forms(page).find("/sessions/undo"),
        target_revision=str(last_play.revision - 1)))
    assert not pair_html(page) and active.execution is None
    assert replay_session_state_v1(active.state).played_card_count == 29
    assert active.decision_checkpoints[0].request.to_dict()["document"] == frozen
    if not hand:
        # Valid opponent correction S9 -> SK, followed by the actual last Card.
        record = [r for r in active.state.command_log if r.command.kind == "record_play"][3]
        correction = Forms(page).find("/sessions/command", kind="record_play")
        page = follow(browser, browser.submit(correction, target_revision=str(record.revision),
            player_id=record.command.player_id, card="SK"))
        assert not pair_html(page)
        page = follow(browser, browser.submit(
            Forms(page).find("/sessions/play"), cards=plays[-1]["card"]))
        assert_pair(page, ("SQ", "S9"))
        request = session_api.export_session_checkpoint_review_request(
            state=active.state, checkpoint=active.decision_checkpoints[0]
        ).value.request.to_dict()["document"]
        assert request == json.loads(downloads[1])


def test_match_real_completion_report_preview_correction_rewind_and_selection(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    page, plays = setup_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    assert not pair_html(page)
    editors = {op: operation_form(page, op)["values"] for op in
               ("set_original_skat", "set_discarded_cards")}
    saves, executions = [], []
    real_save = MatchCaptureWebContextV1.save_candidate
    real_execute = match_analysis.execute_match_decision_analysis_v1
    def save(context, candidate):
        saves.append(candidate)
        return real_save(context, candidate)
    def execute(*args, **kwargs):
        executions.append(kwargs)
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(MatchCaptureWebContextV1, "save_candidate", save)
    monkeypatch.setattr(match_analysis, "execute_match_decision_analysis_v1", execute)
    page = follow(browser, browser.submit(
        operation_form(page, "append_plays"), cards=plays[-1]["card"]))
    assert_pair(page, ("SK", "SQ"))
    assert len(saves) == 1 and not executions
    game = active.workspace.slots[0].observed_game
    evidence = build_observed_game_evidence_summary_v1(game)
    assert game.original_skat is game.discarded_cards is None
    assert not evidence.complete_initial_deal_reconstructable
    for op, original in editors.items():
        current = operation_form(page, op)["values"]
        assert original["card_evidence_mode"] == current["card_evidence_mode"] == "unknown"
        assert "cards" not in current and "cards" not in original
    source, source_bytes = active.workspace, active.path.read_bytes()
    page = browser.page("/matches/review/1")
    assert_pair(page, ("SK", "SQ"))
    assert text("en", "unplayed.review_scope") in page
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                          immediate_sample_count="4"))
    report = active.capture.report_store.list()[0]
    assert report.value.status == "executed" and len(executions) == 1
    route = f"/matches/reports/{report.report_id}"
    download_route = f"/matches/api/v1/reports/{report.report_id}.json"
    downloaded = browser.request("GET", download_route)[2]
    request = report.value.request.to_dict()
    result_section = page.split(download_route, 1)[1].split('</section>', 1)[0]
    assert "data-unplayed-cards" not in result_section
    assert page.index("data-unplayed-cards") > page.index(download_route)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(
            Forms(page).find("/actions/profile/language"), language=locale))
        assert_pair(page, ("SK", "SQ"), locale=locale)
        browser.page("/matches/position/1")
        page = browser.page(route)
        assert browser.request("GET", download_route)[2] == downloaded
        assert report.value.request.to_dict() == request
        assert active.workspace is source and active.path.read_bytes() == source_bytes
        assert build_observed_game_evidence_summary_v1(game) == evidence
    assert len(saves) == len(executions) == 1
    page = browser.page("/matches/position/1")
    for cancel in (True, False):
        page = follow(browser, browser.submit(entry_action(page, 4)))
        page = follow(browser, browser.submit(
            Forms(page).find("/matches/recovery/preview"), card="SK"))
        assert_pair(page, ("SK", "SQ"))
        preview = active.recovery.preview
        page = browser.page("/matches/position/1")
        assert active.recovery.preview is preview
        assert browser.request("GET", download_route)[2] == downloaded
        if cancel:
            page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/cancel")))
        else:
            page = follow(browser, browser.submit(
                Forms(page).find("/matches/recovery/apply"), confirm_apply="on"))
    assert_pair(page, ("SQ", "S9"))
    assert len(saves) == 2 and len(executions) == 1 and not active.capture.report_store.list()
    page = follow(browser, browser.submit(entry_action(page, 30, rewind=True)))
    assert_pair(page, ("SQ", "S9"))
    page = follow(browser, browser.submit(
        Forms(page).find("/matches/recovery/apply"), confirm_apply="on"))
    assert not pair_html(page) and len(saves) == 3
    page = follow(browser, browser.submit(
        operation_form(page, "append_plays"), cards=plays[-1]["card"]))
    assert_pair(page, ("SQ", "S9"))
    saved = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    assert_pair(page, ("SQ", "S9"))
    assert active.path.read_bytes() == saved
    page = browser.page("/matches/position/2")
    assert not pair_html(page)
    page = follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    assert not pair_html(page) and not pair_html(browser.page("/matches/review/2"))
    assert_pair(browser.page("/matches/review/1"), ("SQ", "S9"))
    page = browser.page("/matches/position/3")
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=game.declarer_player_id, game_type="grand", hand_game="true"))
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards="CA"))
    assert not pair_html(page) and not pair_html(browser.page("/matches/review/3"))
