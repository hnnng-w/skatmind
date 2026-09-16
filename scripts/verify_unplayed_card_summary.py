"""Optional installed-Wheel evidence for accepted unplayed-Card conclusions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, posts
from verify_compact_declaration import resource_evidence
from verify_home_recorded_review import download
from verify_local_time_entry import native_select
from verify_match_format_presentation import native_text
from verify_session_direct_card_start import measure, open_metadata
from verify_session_knowledge_entry import submit

import skatmind
import skatmind.app_web.execution as execution
import skatmind.capture_web.analysis as match_analysis
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.session_transitions import replay_session_state_v1

ROOT = Path(__file__).resolve().parents[1]
START = "fc81206ae09bc5abbeab05bfd1754248bc63ad38"
PAIR = '[data-unplayed-cards]'
MODULES = (
    "unplayed_card_summary.py", "unplayed_card_rendering.py", "task_first_session_rendering.py",
    "task_first_match_state.py", "task_first_match_rendering.py", "match_review_rendering.py",
    "recorded_trick_progress.py", "recorded_trick_rendering.py", "compact_card_rendering.py",
    "locales/en.json", "locales/de.json", "assets/app.css", "assets/workflow.js",
)


def assert_pair(cdp, expected):
    labels = cdp.evaluate("[...document.querySelectorAll('[data-unplayed-cards] "
                          "[aria-label]')].map(e=>e.getAttribute('aria-label'))")
    assert len(labels) == len(expected), labels
    assert all(f"({card})" in label for card, label in zip(expected, labels, strict=True))


def layout(cdp, active, counts, output, evidence, selector, name, pair=()):
    before, totals = active.path.read_bytes(), dict(counts)
    for locale in ("de", "en"):
        evidence["locale"] = locale
        submit(cdp, f'form.language-selector button[value="{locale}"]', evidence,
               name + "-language-" + locale)
        assert_pair(cdp, pair)
        if pair:
            assert text(locale, "unplayed.derived") in cdp.evaluate(
                f"document.querySelector('{PAIR}').innerText")
        measure(cdp, output, evidence, selector, name)
        if pair and selector == PAIR:
            cdp.evaluate(f"document.querySelector('{PAIR} p:last-child').scrollIntoView()")
            cdp.screenshot(output / f"{evidence['mode']}-{locale}-{name}-source-tail.png")
    assert active.path.read_bytes() == before and counts == totals


def final_card(cdp, active, counts, evidence, form, card, family):
    before, saves = active.path.read_bytes(), counts[family]
    cdp.events.clear()
    choose(cdp, form + f' input[value="{card}"]')
    assert not posts(cdp) and active.path.read_bytes() == before
    assert_pair(cdp, ())
    submit(cdp, form + ' button', evidence, family + "-final-save")
    assert counts[family] == saves + 1
    assert cdp.evaluate("document.activeElement.id") == (
        "session-recording" if family == "sessions" else "match-recording")


def flow(cdp, server, output, evidence, counts):
    sys.path.insert(0, str(ROOT))
    from test_match_recording_recovery_web import follow, operation_form
    from test_session_recorded_review_web import Browser
    from test_unplayed_card_summary_web import setup_match, setup_session

    browser = Browser(server)
    _, plays = setup_session(browser)
    active = server.app_context.managed_stateful.active_session
    evidence["fixture_setup"] = ["Returned-form HTTP: perspective Session, local hand only, "
        "opponent non-Hand declarer, 29 legal Plays; no injected Report or Checkpoint"]
    frozen = active.decision_checkpoints[0].request.to_dict()["document"]
    cdp.navigate(server.origin + "/sessions/current")
    layout(cdp, active, counts, output, evidence, "#session-recording", "session-29")
    final_card(cdp, active, counts, evidence, 'form[action="/sessions/play"]',
               plays[-1]["card"], "sessions")
    assert_pair(cdp, ("SK", "SQ"))
    facts = replay_session_state_v1(active.state)
    assert facts.known_skat == facts.discarded_cards == () and active.state.phase == "play"
    layout(cdp, active, counts, output, evidence, PAIR, "session-non-hand", ("SK", "SQ"))
    submit(cdp, '#session-recording form button', evidence, "session-explicit-end")
    submit(cdp, 'form[action="/sessions/review-decision"] button', evidence, "session-review")
    request = download(cdp, server, "/sessions/downloads/request.json")
    result = download(cdp, server, "/sessions/downloads/result.json")
    assert json.loads(request) == {**frozen, "analysis_mode": "post_game_review",
                                 "actual_card_played": plays[0]["card"]}
    layout(cdp, active, counts, output, evidence, "#session-result", "session-report", ("SK", "SQ"))
    assert download(cdp, server, "/sessions/downloads/result.json") == result
    evidence["session_review"] = {"frozen_request_exact": True,
        "request_sha256": hashlib.sha256(request).hexdigest(),
        "result_sha256": hashlib.sha256(result).hexdigest(), "passive_bytes_equal": True}
    last = next(r for r in reversed(active.state.command_log) if r.command.kind == "record_play")
    undo = 'form[action="/sessions/undo"]'
    open_metadata(cdp, undo)
    native_text(cdp, undo + ' [name=target_revision]', str(last.revision - 1))
    submit(cdp, undo + ' button', evidence, "session-undo-to-29")
    assert_pair(cdp, ())
    assert replay_session_state_v1(active.state).played_card_count == 29
    browser.command("set_game_end", game_end_reason="defender_concession",
                    player_id=active.state.local_player_id, concession_form="explicit_verbal")
    evidence["fixture_setup"].append("Returned-form HTTP: explicit shortened ending at 29 Plays")
    cdp.navigate(server.origin + "/sessions/current")
    layout(cdp, active, counts, output, evidence, "#session-recording", "session-shortened")
    setup_session(browser, hand=True, count=30)
    active = server.app_context.managed_stateful.active_session
    evidence["fixture_setup"].append("Returned-form HTTP: Hand Session, local initial hand only, "
                                      "30 Plays, original Skat absent")
    cdp.navigate(server.origin + "/sessions/current")
    layout(cdp, active, counts, output, evidence, PAIR, "session-hand", ("D8", "D7"))
    assert text("en", "unplayed.no_discards") in cdp.evaluate(
        f"document.querySelector('{PAIR}').innerText")

    _, plays = setup_match(browser)
    active = server.app_context.managed_stateful.active_match
    evidence["fixture_setup"].append("Returned-form HTTP: non-Hand Match Game, 29 legal Plays, "
                                      "no original hand/Skat/discard evidence")
    cdp.navigate(server.origin + "/matches/position/1")
    layout(cdp, active, counts, output, evidence, "#match-recording", "match-29")
    play_form = 'form[action="/matches/cards"]:has(input[value="append_plays"])'
    final_card(cdp, active, counts, evidence, play_form, plays[-1]["card"], "matches")
    layout(cdp, active, counts, output, evidence, PAIR, "match-non-hand", ("SK", "SQ"))
    editor = 'form[action="/matches/cards"]:has(input[value="set_discarded_cards"])'
    open_metadata(cdp, editor)
    cdp.events.clear()
    assert cdp.evaluate(f"document.querySelector('{editor} [name=card_evidence_mode]').value") == (
        "unknown")
    assert not cdp.evaluate(f"document.querySelectorAll('{editor} [name=cards]:checked').length")
    assert not posts(cdp)
    # Reopen the native source editor after each language navigation for screenshots.
    for locale in ("de", "en"):
        evidence["locale"] = locale
        before, totals = active.path.read_bytes(), dict(counts)
        submit(cdp, f'form.language-selector button[value="{locale}"]', evidence,
               "editor-language-" + locale)
        open_metadata(cdp, editor)
        measure(cdp, output, evidence, "#match-evidence", "recorded-evidence-editor")
        assert active.path.read_bytes() == before and counts == totals
    cdp.navigate(server.origin + "/matches/review/1")
    analyze = 'form[action="/matches/api/v1/analysis"]:has(input[value="analyze_decision"])'
    submit(cdp, analyze + ' > button', evidence, "match-explicit-review")
    report = active.capture.report_store.list()[0]
    route = f"/matches/api/v1/reports/{report.report_id}.json"
    retained = download(cdp, server, route)
    layout(cdp, active, counts, output, evidence, "#match-review", "match-report", ("SK", "SQ"))
    layout(cdp, active, counts, output, evidence, PAIR, "match-review-conclusion", ("SK", "SQ"))
    assert download(cdp, server, route) == retained
    evidence["match_review"] = {"download_sha256": hashlib.sha256(retained).hexdigest(),
        "passive_bytes_equal": True, "source_skat": None, "source_discards": None}
    cdp.navigate(server.origin + "/matches/position/1")
    select = '#match-play-4 form[action="/matches/recovery/select"]:first-of-type'
    submit(cdp, select + ' button', evidence, "match-correction-select")
    correction = 'form[action="/matches/recovery/preview"]'
    index = cdp.evaluate(f"[...document.querySelector('{correction} [name=card]').options]"
                         ".findIndex(o=>o.value==='SK')")
    assert native_select(cdp, correction + ' [name=card]', down=index) == "SK"
    submit(cdp, correction + ' button', evidence, "match-correction-preview")
    assert_pair(cdp, ("SK", "SQ"))
    preview = active.recovery.preview
    layout(cdp, active, counts, output, evidence, PAIR, "match-preview", ("SK", "SQ"))
    assert active.recovery.preview is preview and download(cdp, server, route) == retained
    submit(cdp, 'form[action="/matches/recovery/cancel"] button', evidence, "match-preview-cancel")
    assert_pair(cdp, ("SK", "SQ"))
    select = '#match-play-30 form[action="/matches/recovery/select"]:last-of-type'
    submit(cdp, select + ' button', evidence, "match-rewind-select")
    apply = 'form[action="/matches/recovery/apply"]'
    choose(cdp, apply + ' [name=confirm_apply]')
    submit(cdp, apply + ' button', evidence, "match-rewind-apply")
    assert_pair(cdp, ())
    assert len(active.workspace.slots[0].observed_game.plays) == 29
    assert not active.capture.report_store.list()
    layout(cdp, active, counts, output, evidence, "#match-recording", "match-rewound")
    page = browser.page("/matches/position/1")
    page = follow(browser, browser.submit(operation_form(page, "append_plays"),
                                          cards=plays[-1]["card"]))
    follow(browser, browser.submit(operation_form(page, "set_declaration"), hand_game="true"))
    evidence["fixture_setup"].append("Returned-form HTTP: re-record final Match Card and accept "
                                      "Hand declaration correction; evidence remains absent")
    cdp.navigate(server.origin + "/matches/position/1")
    layout(cdp, active, counts, output, evidence, PAIR, "match-hand", ("SK", "SQ"))
    assert text("en", "unplayed.no_discards") in cdp.evaluate(
        f"document.querySelector('{PAIR}').innerText")
    cdp.navigate(server.origin + "/matches/position/2")
    layout(cdp, active, counts, output, evidence, "#match-recording", "match-empty")
    page = browser.page("/matches/position/2")
    follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    cdp.navigate(server.origin + "/matches/position/2")
    layout(cdp, active, counts, output, evidence, "#match-recording", "match-passed")
    resource_evidence(cdp, server, evidence)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    hashes = {}
    for name in MODULES:
        data = files("skatmind.app_web").joinpath(name).read_bytes()
        assert data == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = hashlib.sha256(data).hexdigest()
    evidence = {"starting_sha": START, "completed": False, "python": sys.version,
        "package": skatmind.__version__, "module": skatmind.__file__, "hashes": hashes,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(), "runs": []}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="localization-test-token")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            try:
                cdp = browser.cdp
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
                time.sleep(.5)
                item = {"javascript": javascript, "mode": mode, "locale": "en",
                    "browser": browser.version, "actions": {}, "measurements": []}
                evidence["runs"].append(item)
                counts = {"sessions": 0, "matches": 0, "executes": 0, "match_executes": 0}
                real_replace, real_execute = os.replace, execution.execute
                real_match = match_analysis.execute_match_decision_analysis_v1
                def saved(source, destination, real_replace=real_replace, counts=counts):
                    result = real_replace(source, destination)
                    family = Path(destination).parent.name
                    if family in {"sessions", "matches"}:
                        counts[family] += 1
                    return result
                def executed(*args, real_execute=real_execute, counts=counts, **kwargs):
                    counts["executes"] += 1
                    return real_execute(*args, **kwargs)
                def match_executed(*args, real_match=real_match, counts=counts, **kwargs):
                    counts["match_executes"] += 1
                    return real_match(*args, **kwargs)
                with (patch.object(os, "replace", saved),
                      patch.object(execution, "execute", executed),
                      patch.object(match_analysis, "execute_match_decision_analysis_v1",
                                   match_executed)):
                    flow(cdp, server, output, item, counts)
                assert counts["executes"] == counts["match_executes"] == 1
                item["counts_including_fixture_setup"] = counts
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"completed": evidence["completed"], "measurements": sum(
            len(item["measurements"]) for item in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
