# ruff: noqa: E501 - Keep browser measurements and native selectors legible.
"""Optional installed-Wheel R03 check using the existing dependency-free browser transport.

Uses fresh synthetic roots and real returned forms; separate from check.ps1 and UAT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
sys.path.insert(0, str(REPOSITORY / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_game_navigation_web import create_empty  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND, SESSION_HAND  # noqa: E402
from test_session_direct_card_start_web import create  # noqa: E402
from test_session_recorded_review_web import (  # noqa: E402
    Browser,
    Forms,
    record_score_review_game,
    score_review_form,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile_operations  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.deck import get_full_deck  # noqa: E402

GEOMETRY = r"""({anchor,control}) => {
  const visible=e=>e.checkVisibility(),box=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {top:r.top+scrollY,left:r.left,width:r.width,height:r.height,visible:visible(e)}};
  const root=document.querySelector(anchor), current=control?document.querySelector(control):null;
  const result=document.querySelector('#session-result');
  return {page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
    height:document.documentElement.scrollHeight,anchor:box(root),control:box(current),
    headings:[...document.querySelectorAll('main h1,main h2,main h3')].filter(visible).map(e=>({text:e.textContent,...box(e)})),
    normalForms:[...root.querySelectorAll('form')].filter(visible).map(e=>({action:e.getAttribute('action'),...box(e)})),
    reviewLinks:[...document.querySelectorAll('a[href="#recorded-decisions"],#match-recording a[href^="/matches/review/"]')].filter(visible).map(e=>e.textContent),
    decisions:[...document.querySelectorAll('form[action="/sessions/review-decision"]')].filter(visible).length,
    transferVisible:document.querySelector('form[action="/matches/transfer-workspace"]')?.checkVisibility()??false,
    resultVisible:result?.checkVisibility()??false,resultInsideDisclosure:!!result?.closest('details'),
    resultText:result?.innerText??null,focus:{id:document.activeElement.id,name:document.activeElement.name},fragment:location.hash};
}"""


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
        "limitations": ["Synthetic headless Edge and emulated viewports/text, not maintainer UAT.",
            "Existing narrow candidate-table limit remains; no table layout change or whole-page accessibility claim."]}
    for name in ("task_first_session_rendering.py", "session_recorded_review_rendering.py", "task_first_match_rendering.py",
                 "task_first_match_state.py", "match_review_rendering.py", "task_first_learning_rendering.py", "server.py",
                 "session_recorded_review.py", "language_context.py", "validation_rendering.py", "form_registry.py",
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
        def wrapper(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapper

    def request_count(method, real):
        def wrapper(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return wrapper

    def navigate(path, anchor=""):
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path + anchor)
        cdp.call("Page.bringToFront")

    def key(value, code=None, modifiers=0):
        number = code or {"Enter": 13, "Home": 36, "ArrowDown": 40, "Escape": 27, "Tab": 9}[value]
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=value, windowsVirtualKeyCode=number,
                 modifiers=modifiers, **({"text": "\r"} if value == "Enter" else {}))
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=value, windowsVirtualKeyCode=number, modifiers=modifiers)

    def click(selector):
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
            + ");e.scrollIntoView({block:'center'});const r=e.tagName==='A'?e.getClientRects()[0]:e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)

    def action(selector, route=None):
        before, old_calls = requests.copy(), calls.copy()
        click(selector)
        time.sleep(.7)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (route is None or requests["POST " + route] > before["POST " + route]):
                break
            time.sleep(.1)
        delta = requests - before
        assert sum(n for path, n in delta.items() if path.startswith("POST ")) == int(route is not None), delta
        evidence["actions"].append({"selector": selector, "requests": dict(delta), "calls": dict(calls-old_calls),
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

    def native(path, script=False):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
        navigate(path)

    def capture(name, path, anchor, control=None):
        before = calls.copy()
        for script in (False, True):
            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
            for locale in ("de", "en"):
                follow(client, client.submit(Forms(client.page(path)).find("/actions/profile/language"), language=locale))
                for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
                    navigate(path, anchor)
                    if scale == 2:
                        cdp.evaluate(TEXT_ENLARGEMENT)
                    row = cdp.evaluate("(" + GEOMETRY + ")(" + json.dumps({"anchor": anchor, "control": control}) + ")")
                    row.update(state=name, locale=locale, javascript=script, width=width, text_scale=scale)
                    assert row["page"] == row["client"], row
                    if control:
                        assert row["control"]["visible"] and row["control"]["width"] > 0, row
                    if args.phase == "after":
                        if name in {"session-initial", "session-partial-hand", "session-declarer", "match-empty", "match-declaration"}:
                            assert row["reviewLinks"] == [] and row["decisions"] == 0, row
                        if name == "ended-result":
                            assert row["resultVisible"] and not row["resultInsideDisclosure"]
                    evidence["pages"].append(row)
                    stem = f'{name}-{locale}-{int(script)}-{width}-{scale}'
                    cdp.evaluate("document.querySelector(" + json.dumps(anchor) + ").scrollIntoView();window.scrollBy(0,-20)")
                    cdp.screenshot(args.output / (stem + ".png"))
                    if control and row["control"]["top"]-row["anchor"]["top"] > height*.7:
                        cdp.evaluate("document.querySelector(" + json.dumps(control) + ").scrollIntoView({block:'center'})")
                        cdp.screenshot(args.output / (stem + "-control.png"))
        assert all(calls[k] == before[k] for k in ("session_saves", "match_saves", "session_executions", "match_executions"))

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"),
                (execution, "execute", "session_executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method, request_count(method, getattr(Handler, "do_" + method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=",1)[0], value=client.cookie.split("=",1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert hashlib.sha256(client.request("GET", route)[2]).hexdigest() == evidence["hashes"][resource]
            create(client)
            capture("session-initial", "/sessions/current", "#session-recording", '#session-recording button[type="submit"]')
            native("/sessions/current", script=True)
            for card in get_full_deck()[:4]:
                action(f'#session-recording input[name="cards"][value="{card}"]')
            action('button[name="language"][value="de"]', "/actions/profile/language")
            assert cdp.evaluate("document.querySelectorAll('#session-recording input[name=cards]:checked').length") == 4
            action('#session-recording button[type="submit"]', "/sessions/cards")
            assert server.app_context.managed_stateful.active_session.state.revision == 5
            capture("session-partial-hand", "/sessions/current", "#session-recording", '#session-recording button[type="submit"]')
            native("/sessions/current")
            for card in get_full_deck()[4:10]:
                action(f'#session-recording input[name="cards"][value="{card}"]')
            action('#session-recording button[type="submit"]', "/sessions/cards")
            assert server.app_context.managed_stateful.active_session.state.revision == 11
            capture("session-declarer", "/sessions/current", "#session-recording", '#session-recording select[name="player_id"]')
            native("/sessions/current")
            action('#session-recording button[type="submit"]', "/sessions/command")
            capture("session-declaration", "/sessions/current", "#session-recording", '#session-recording select[name="game_type"]')
            native("/sessions/current")
            choose('#session-recording select[name="game_type"]', "grand")
            action('#session-recording input[name="hand_game"]')
            action('#session-recording button[type="submit"]', "/sessions/command")
            assert server.app_context.managed_stateful.active_session.state.phase == "play"

            # One legal full-game setup shared across all Result locales/viewports.
            before_setup = calls.copy()
            record_score_review_game(client, play_count=30)
            session = server.app_context.managed_stateful.active_session
            assert session.state.phase == "play" and len(session.decision_checkpoints) == 10
            evidence["ended_fixture_setup"] = dict(calls-before_setup)
            capture("session-explicit-end", "/sessions/current", "#session-recording", '#session-recording button[type="submit"]')
            native("/sessions/current")
            action('#session-recording button[type="submit"]', "/sessions/command")
            assert session.state.phase == "ended"
            assert session.state.validation.position_export.status == session.state.validation.historical_export.status == "unavailable"
            selection = score_review_form(client)["values"]["decision_selection"]
            capture("ended-eligible", "/sessions/current", "#recorded-decisions", f'form:has(input[value="{selection}"]) button')
            native("/sessions/current")
            action(f'form:has(input[value="{selection}"]) button', "/sessions/review-decision")
            assert cdp.evaluate("document.activeElement.id") == "session-result"
            request, result = session.execution.request_json_bytes, session.execution.result_json_bytes
            saved = session.path.read_bytes()
            assert tuple(session.execution.result.result.document["position"]["hand"]) == SESSION_HAND
            capture("ended-result", "/sessions/current", "#session-result", '#session-result a[href="#recorded-decision-12"]')
            native("/sessions/current", script=True)
            action('button[name="language"][value="de"]', "/actions/profile/language")
            assert cdp.evaluate("document.activeElement.id") == "session-result"
            action('#session-result a[href="#recorded-decision-12"]')
            assert cdp.evaluate("location.hash") == "#recorded-decision-12"
            for route, raw in (("request",request),("result",result)):
                assert client.request("GET", f"/sessions/downloads/{route}.json")[2] == raw
            assert session.path.read_bytes() == saved
            opener = next(form for form in Forms(client.page("/sessions")).forms
                          if form["action"] == "/sessions/open" and form["values"]["handle"] == session.handle)
            follow(client, client.submit(opener))
            reopened = server.app_context.managed_stateful.active_session
            assert reopened is not session and reopened.execution is None and reopened.path.read_bytes() == saved
            native("/sessions/current")
            selection = score_review_form(client)["values"]["decision_selection"]
            action(f'form:has(input[value="{selection}"]) button', "/sessions/review-decision")
            assert reopened.execution.request_json_bytes == request and reopened.execution.result_json_bytes == result
            evidence["sources"]["session"] = {"revision": reopened.state.revision, "checkpoints": len(reopened.decision_checkpoints),
                "saved_sha256": hashlib.sha256(saved).hexdigest(), "request_sha256": hashlib.sha256(request).hexdigest(), "result_sha256": hashlib.sha256(result).hexdigest()}

            create_empty(client, "en")
            match = server.app_context.managed_stateful.active_match
            capture("match-empty", "/matches/position/1", "#match-recording", '#match-recording button.primary')
            native("/matches/position/1")
            action('#match-recording form:has(input[value="start_game"]) button', "/matches/api/v1/operation")
            capture("match-declaration", "/matches/position/1", "#match-recording", '#match-declaration select[name="game_type"]')
            native("/matches/position/1", script=True)
            declarer = operation_form(client.page('/matches/position/1'), 'set_declaration')["values"]["declarer_player_id"]
            if not declarer:
                declarer = cdp.evaluate("[...document.querySelector('#match-declaration select[name=declarer_player_id]').options].find(e=>e.value).value")
            choose('#match-declaration select[name="declarer_player_id"]', declarer)
            choose('#match-declaration select[name="game_type"]', "grand")
            action('#match-declaration button', "/matches/api/v1/operation")
            for card in ("CK", "C7", "C10"):
                action(f'#match-recording input[name="cards"][value="{card}"]')
                action('#match-recording form:has(input[value="append_plays"]) button', "/matches/cards")
            capture("match-missing-evidence", "/matches/position/1", "#match-recording", '#match-recording button.primary')
            native("/matches/position/1")
            action('#match-recording a[href="/matches/review/1"]')
            assert not cdp.evaluate("!!document.querySelector('form:has(input[value=analyze_decision])')")
            native("/matches/position/1")
            action('#match-recording details:has(form input[value="set_perspective_hand"]) > summary')
            choose('form:has(input[value="set_perspective_hand"]) select[name="card_evidence_mode"]', "exact")
            for card in MATCH_HAND:
                action(f'form:has(input[value="set_perspective_hand"]) input[name="cards"][value="{card}"]')
            action('form:has(input[value="set_perspective_hand"]) button', "/matches/cards")
            capture("match-prepared", "/matches/review/1", "#match-review", 'form:has(input[value="analyze_decision"]) button')
            native("/matches/review/1")
            action('form:has(input[value="analyze_decision"]) button', "/matches/api/v1/analysis")
            report, = match.capture.report_store.list()
            downloaded = client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2]
            native("/matches/position/2")
            assert match.capture.report_store.list() == (report,)
            native(f"/matches/reports/{report.report_id}")
            assert match.selected_position == 1
            assert client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2] == downloaded
            native("/matches/position/1", script=True)
            action('#match-metadata > details > summary')
            click('#match-metadata input[name="title"]')
            key("a", code=65, modifiers=2)
            cdp.call("Input.insertText", text=" ")
            action('#match-metadata form button', "/matches/api/v1/operation")
            assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
            action('button[name="language"][value="de"]', "/actions/profile/language")
            assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
            action('a[href^="#validation-field-"][href$="-title"]')
            assert cdp.evaluate("document.activeElement.name") == "title"
            cdp.screenshot(args.output / 'match-error-field-focus.png')
            capture("match-field-error", "/matches/position/1", "#match-metadata", '#match-metadata input[name="title"]')
            native("/matches/position/1")
            action('#match-play-3 form[action="/matches/recovery/select"] button', "/matches/recovery/select")
            choose('form[action="/matches/recovery/preview"] select[name="card"]', "CA")
            action('form[action="/matches/recovery/preview"] button', "/matches/recovery/preview")
            assert cdp.evaluate("document.activeElement.id") == "match-recovery"
            cdp.screenshot(args.output / 'match-correction-preview.png')
            action('form[action="/matches/recovery/cancel"] button', "/matches/recovery/cancel")
            assert cdp.evaluate("document.activeElement.id") == "match-recording"
            assert client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2] == downloaded
            native("/matches/position/2")
            action('#match-recording form:has(input[value="mark_passed_deal"]) button', "/matches/api/v1/operation")
            assert match.selected_position == 2 and match.workspace.slots[1].slot_kind == "passed_deal"
            capture("match-passed-direct", "/matches/review/2", "#match-review", '#match-review a[href="/matches/position/2#match-recording"]')
            follow(client, client.submit(Forms(client.page('/learning')).find('/learning/create'), collection_name='Synthetic optional transfer'))
            target = server.app_context.managed_stateful.active_learning
            native("/matches/position/2", script=True)
            form = Forms(client.page('/matches/position/2')).find('/matches/transfer-workspace')
            if args.phase == "after":
                assert not cdp.evaluate("document.querySelector('form[action=\"/matches/transfer-workspace\"]').checkVisibility()")
                action('#task-first-match > details:has(form[action="/matches/transfer-workspace"]) > summary')
            assert target.corpus.store.document.catalog.revision == 0
            # Negative fixture: stale target revision through a real returned form.
            response = client.submit(form, expected_catalog_revision="99")
            assert response[0] == 409
            capture("transfer-error", "/matches/position/2", "#match-recording", 'form[action="/matches/transfer-workspace"] button')
            native("/matches/position/2")
            action('button[name="language"][value="de"]', "/actions/profile/language")
            assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
            cdp.screenshot(args.output / 'transfer-error-focus.png')
            action('form[action="/matches/transfer-workspace"] button', "/matches/transfer-workspace")
            assert target.corpus.store.document.catalog.revision == 1 and target.corpus.prepared_artifacts is None
            assert match.selected_position == 2 and len(match.workspace.slots[0].observed_game.plays) == 3
            evidence["sources"]["match"] = {"revision": match.workspace.revision, "plays": 3, "passed": 2,
                "saved_sha256": hashlib.sha256(match.path.read_bytes()).hexdigest(), "report_sha256": hashlib.sha256(downloaded).hexdigest(), "catalog_revision": 1}
            evidence["completed"] = True
    finally:
        evidence.update(calls=dict(calls), requests=dict(requests))
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({"completed": evidence["completed"], "measurements": len(evidence["pages"]), "calls": dict(calls), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
