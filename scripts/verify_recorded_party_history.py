# ruff: noqa: E501 - Keep browser selectors and measurements legible.
"""Optional R05 installed-Wheel verification with real synthetic forms and native input.

Uses the existing dependency-free DevTools transport, outside check.ps1 and UAT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND, SESSION_HAND, assert_context  # noqa: E402
from test_recorded_party_presentation import corrected_match_setup  # noqa: E402
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile_operations  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402

MEASURE = r"""(() => {
  const box=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {top:r.top+scrollY,left:r.left,width:r.width,height:r.height,visible:e.checkVisibility()}};
  const summary=document.querySelector('.recorded-summary'), history=document.querySelector('.recorded-history');
  const task=document.querySelector('#session-recording,#match-recording'), result=document.querySelector('#session-result');
  return {page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
    headings:[...document.querySelectorAll('main h1, main h2, main h3')].filter(e=>e.checkVisibility()).map(e=>e.textContent),
    summary:box(summary),summaryText:summary?.innerText,history:box(history),task:box(task),
    histories:document.querySelectorAll('.recorded-history').length,individuals:document.querySelectorAll('.trick-total').length,
    parties:[...document.querySelectorAll('[data-recorded-party]')].map(e=>({side:e.dataset.recordedParty,text:e.innerText,...box(e)})),
    metrics:[...summary?.querySelectorAll('[data-trick-metric]')??[]].map(e=>({kind:e.dataset.trickMetric,value:Number(e.textContent)})),
    rows:[...history?.querySelectorAll('li')??[]].map(e=>({id:e.id,text:e.innerText,...box(e)})),
    cards:[...history?.querySelectorAll('.recorded-card')??[]].map(e=>({name:e.getAttribute('aria-label'),...box(e)})),
    correctionForms:history?.querySelectorAll('form[action="/matches/recovery/select"]').length??0,
    receipt:!!document.querySelector('[data-operation-feedback]'),
    result:box(result),resultText:result?.innerText,contextCards:result?.querySelectorAll('.decision-context-hand .recorded-card').length,
    focus:document.activeElement.id,fragment:location.hash};
})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(REPOSITORY)
    args.output.mkdir()
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip(),
        "hashes": {}, "pages": [], "actions": [], "sources": {},
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "limitations": ["Synthetic headless Edge; emulated viewports and text enlargement, not maintainer UAT.",
            "Existing narrow analysis comparison-table limitation remains; no whole-page accessibility or physical-device claim."]}
    for name in ("recorded_trick_rendering.py", "recorded_trick_progress.py", "match_review_rendering.py",
        "task_first_session_rendering.py", "task_first_match_rendering.py", "task_first_match_state.py",
        "match_recovery_rendering.py", "compact_card_rendering.py", "operation_feedback.py", "server.py",
        "locales/en.json", "locales/de.json", "assets/app.css", "assets/workflow.js"):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((REPOSITORY / "src/skatmind/app_web" / name).read_bytes() if args.phase == "after"
                    else subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=REPOSITORY))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = hashlib.sha256(raw).hexdigest()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, requests = Counter(), Counter()

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapped

    def request_count(method, real):
        def wrapped(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return wrapped

    def navigate(path, script=False):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def key(value):
        number = {"Enter": 13, "Home": 36, "ArrowDown": 40, "Escape": 27}[value]
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=value, windowsVirtualKeyCode=number,
                 **({"text": "\r"} if value == "Enter" else {}))
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=value, windowsVirtualKeyCode=number)

    def click(selector):
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
            + ");e.scrollIntoView({block:'center'});const r=e.tagName==='A'?e.getClientRects()[0]:e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)

    def action(selector, route=None):
        before, work = requests.copy(), calls.copy()
        click(selector)
        time.sleep(.5)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (route is None or requests["POST " + route] > before["POST " + route]):
                break
            time.sleep(.1)
        delta = requests - before
        assert sum(n for path, n in delta.items() if path.startswith("POST ")) == int(route is not None), delta
        evidence["actions"].append({"selector": selector, "requests": dict(delta), "calls": dict(calls-work),
            "javascript": not cdp.script_disabled, "focus": cdp.evaluate("document.activeElement.id"), "fragment": cdp.evaluate("location.hash")})

    def choose(selector, value):
        values = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].map(e=>e.value)")
        click(selector)
        key("Escape")
        key("Home")
        for _ in range(values.index(value)):
            key("ArrowDown")
        key("Enter")
        assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").value") == value

    def photo(stem, selector):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});window.scrollBy(0,-20)")
        cdp.screenshot(args.output / (stem + ".png"))

    def capture(name, path, count, expected=None):
        before = calls.copy()
        source = server.app_context.managed_stateful.active_session if path.startswith("/sessions") else server.app_context.managed_stateful.active_match
        raw = source.path.read_bytes()
        cells = (("de", False, 1365, 1), ("en", True, 390, 1), ("de", True, 320, 1),
                 ("en", False, 320, 1), ("de", False, 320, 2), ("en", True, 1365, 1),
                 ("de", True, 390, 1), ("en", False, 390, 1), ("en", True, 320, 2))
        for locale, script, width, scale in cells:
            follow(client, client.submit(Forms(client.page(path)).find("/actions/profile/language"), language=locale))
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844 if width == 390 else 800, deviceScaleFactor=1, mobile=False)
            navigate(path, script)
            if scale == 2:
                cdp.evaluate(TEXT_ENLARGEMENT)
            row = cdp.evaluate(MEASURE)
            row.update(state=name, locale=locale, javascript=script, width=width, text_scale=scale)
            assert row["page"] == row["client"], row
            assert not row["receipt"], row
            if args.phase == "after":
                assert row["histories"] == 1 and len(row["rows"]) == count and row["individuals"] == 0, row
                assert all(card["visible"] and card["name"] for card in row["cards"])
                assert all(r["visible"] for r in row["rows"])
                if row["task"]:
                    assert row["task"]["top"] < row["history"]["top"]
                if expected:
                    assert [m["value"] for m in row["metrics"]] == expected, row
                    assert len(row["parties"]) == 2
                else:
                    assert row["metrics"] == []  # Null has only its recorded-Trick fact.
                assert row["correctionForms"] == (count * 2 if path.startswith("/matches/position/") else 0)
            if name == "session-ended":
                assert row["contextCards"] == 7
                assert_context(client.page(path), locale, hand=SESSION_HAND,
                    prefix=(("B", "HJ"), ("C", "DJ")), actor="A", trick=4, play=3)
            evidence["pages"].append(row)
            stem = f"{name}-{locale}-{int(script)}-{width}-{scale}"
            photo(stem + "-score", ".recorded-summary")
            if args.phase == "after" and expected and scale == 2:
                photo(stem + "-defenders", '[data-recorded-party="defenders"]')
            if row["history"]:
                photo(stem + "-history", ".recorded-history")
                if count == 30 and width in (1365, 320) and scale == 1:
                    photo(stem + "-last-trick", '.recorded-trick[data-trick-number="10"]')
            if name == "session-ended" and width == 320:
                photo(stem + "-result", "#session-result")
                photo(stem + "-context", ".recorded-decision-context")
                photo(stem + "-historical-score", 'section[aria-labelledby="result-section-1"] > dl')
        assert source.path.read_bytes() == raw
        assert all(calls[k] == before[k] for k in ("session_saves", "match_saves", "session_executions", "match_executions"))
        evidence["sources"][name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            "passive_calls": dict(calls-before)}

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"),
                (execution, "execute", "session_executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (match_state, "_decision_preparation_summary", "match_page_preparations"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method, request_count(method, getattr(Handler, "do_" + method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert hashlib.sha256(client.request("GET", route)[2]).hexdigest() == evidence["hashes"][resource]
            # One full legal fixture, with native recording of the saved decision and explicit End.
            plays = record_score_review_game(client, play_count=11)
            capture("session-partial", "/sessions/current", 11, [14, 1, 29, 2])
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
            navigate("/sessions/current")
            action('#session-recording input[value="SJ"]')
            action('#session-recording button[type="submit"]', "/sessions/play")
            for play in plays[12:]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            navigate("/sessions/current")
            action('#session-recording button[type="submit"]', "/sessions/command")
            session = server.app_context.managed_stateful.active_session
            assert session.state.phase == "ended" and len(session.decision_checkpoints) == 10
            action('#recorded-decision-12 + button', "/sessions/review-decision")
            downloads = tuple(client.request("GET", f"/sessions/downloads/{kind}.json")[2] for kind in ("request", "result"))
            capture("session-ended", "/sessions/current", 30, [42, 3, 78, 7])
            navigate("/sessions/current#session-result", script=True)
            action('button[name="language"][value="de"]', "/actions/profile/language")
            action('#session-result a[href="#recorded-decision-12"]')
            assert cdp.evaluate("location.hash") == "#recorded-decision-12"
            assert tuple(client.request("GET", f"/sessions/downloads/{kind}.json")[2] for kind in ("request", "result")) == downloads
            follow(client, client.submit(Forms(client.page("/sessions")).find("/sessions/open")))
            assert server.app_context.managed_stateful.active_session.execution is None
            navigate("/sessions/current")
            action('#recorded-decision-12 + button', "/sessions/review-decision")
            assert tuple(client.request("GET", f"/sessions/downloads/{kind}.json")[2] for kind in ("request", "result")) == downloads
            evidence["downloads"] = {kind: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                                     for kind, raw in zip(("request", "result"), downloads, strict=True)}
            # Independent corrected Match: CA -> C10, Cancel first, same-Card no-op last.
            corrected_match_setup(client)
            match = server.app_context.managed_stateful.active_match
            for script, cancel in ((False, True), (True, False), (False, False)):
                navigate("/matches/position/1", script)
                action('#match-play-3 .match-recovery-actions form:first-child button', "/matches/recovery/select")
                choose('#match-recovery select[name="card"]', "C10")
                action('form[action="/matches/recovery/preview"] button', "/matches/recovery/preview")
                original, before = match.path.read_bytes(), calls["match_saves"]
                if cancel:
                    action('form[action="/matches/recovery/cancel"] button', "/matches/recovery/cancel")
                    assert match.path.read_bytes() == original and calls["match_saves"] == before
                else:
                    noop = match.workspace.slots[0].observed_game.plays[-1].card == "C10"
                    action('input[name="confirm_apply"]')
                    action('form[action="/matches/recovery/apply"] button', "/matches/recovery/apply")
                    assert calls["match_saves"] == before + int(not noop)
            capture("match-recording", "/matches/position/1", 3, [0, 0, 14, 1])
            capture("match-zero-ready", "/matches/review/1", 3, [0, 0, 14, 1])
            if args.phase == "after":
                navigate("/matches/review/1")
                action('.recorded-history a[href="/matches/position/1#match-play-3"]')
                assert cdp.evaluate("document.activeElement.id") == "match-play-3"
            page = client.page("/matches/position/1")
            follow(client, client.submit(operation_form(page, "set_perspective_hand"), card_evidence_mode="exact", cards=MATCH_HAND))
            capture("match-ready", "/matches/review/1", 3, [0, 0, 14, 1])
            navigate("/matches/review/1", script=True)
            action('button[name="language"][value="en"]', "/actions/profile/language")
            action('form[action="/matches/api/v1/analysis"] button', "/matches/api/v1/analysis")
            report, = match.capture.report_store.list()
            assert report.value.status == "executed"
            report_download = client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2]
            report_path = f"/matches/reports/{report.report_id}"
            assert_context(client.page(report_path), "en", hand=MATCH_HAND,
                prefix=(("B", "CK"),), actor="C", trick=1, play=2, game=1)
            photo("match-retained-report", ".recorded-decision-context")
            action('button[name="language"][value="de"]', "/actions/profile/language")
            assert client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2] == report_download
            evidence["match_download"] = {"sha256": hashlib.sha256(report_download).hexdigest(), "bytes": len(report_download)}
            action('a[href="/matches/position/1#match-recording"]')
            # Next Card is A's actual lead, through the normal native input.
            navigate("/matches/position/1")
            action('#match-recording input[name="cards"][value="SK"]')
            action('#match-recording form[action="/matches/cards"] button', "/matches/cards")
            assert match.workspace.slots[0].observed_game.plays[-1].card == "SK"
            # Pass Game 2, return, then strict reopen without changing accepted Game-1 bytes.
            page = client.page("/matches/position/2")
            follow(client, client.submit(operation_form(page, "mark_passed_deal")))
            client.page("/matches/position/1")
            raw, save_count = match.path.read_bytes(), calls["match_saves"]
            follow(client, client.submit(Forms(client.page("/matches")).find("/matches/open")))
            match = server.app_context.managed_stateful.active_match
            assert match.path.read_bytes() == raw and calls["match_saves"] == save_count
            assert match.workspace.slots[1].slot_kind == "passed_deal"
            navigate("/matches/position/1")
            reopened = cdp.evaluate(MEASURE)
            assert len(reopened["rows"]) == 4
            evidence["reopened_match"] = reopened
            # Separate rotated Game supplies accepted warning and native focus navigation.
            page = client.page("/matches/position/4")
            page = follow(client, client.submit(operation_form(page, "start_game")))
            declarer = re.search(r'<select name="declarer_player_id".*?<option value="([^"]+)"', page, re.S)[1]
            page = follow(client, client.submit(operation_form(page, "set_declaration"), declarer_player_id=declarer, game_type="grand"))
            for card in ("SA", "H7", "S7", "CA", "S8"):
                page = follow(client, client.submit(Forms(page).find("/matches/cards"), cards=card))
            navigate("/matches/position/4")
            action('.trick-warning a[href="#match-play-2"]')
            assert cdp.evaluate("document.activeElement.id") == "match-play-2"
            photo("warning-target", "#match-play-2")
            if args.phase == "after":
                navigate("/matches/review/4", script=True)
                action('.trick-warning a[href="#match-play-2"]')
                assert cdp.evaluate("document.activeElement.id") == "match-play-2"
                photo("review-warning-target", "#match-play-2")
            # A real separate Null declaration and completed Trick, no inferred outcome.
            page = client.page("/matches/position/3")
            page = follow(client, client.submit(operation_form(page, "start_game")))
            declarer = re.search(r'<select name="declarer_player_id".*?<option value="([^"]+)"', page, re.S)[1]
            page = follow(client, client.submit(operation_form(page, "set_declaration"), declarer_player_id=declarer, game_type="null"))
            for card in ("CA", "C7", "C8"):
                page = follow(client, client.submit(Forms(page).find("/matches/cards"), cards=card))
            capture("match-null", "/matches/position/3", 3)
            evidence["calls"] = dict(calls)
            evidence["requests"] = dict(requests)
            evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]),
                      "calls": dict(calls), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
