# ruff: noqa: E501 - Keep native selectors and browser measurements legible.
"""Operation-feedback browser evidence on disposable synthetic roots.

Optional dependency-free Chromium transport; never part of check.ps1 or maintainer UAT.
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
from urllib.request import urlopen

from _workflow_visual_browser import DevTools, LocalBrowser
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "tests"))
sys.path.insert(1, str(REPOSITORY))

from test_equal_best_immediate import assert_visible_equal_best  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_frontend_result_presentation import assert_summary_points  # noqa: E402
from test_local_time_entry_web import local_form  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402
from test_recorded_decision_context import SESSION_HAND  # noqa: E402
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
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.deck import get_full_deck  # noqa: E402

MEASURE = r"""(() => {
  const n=document.querySelector('[data-operation-feedback]'), box=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,visible:e.checkVisibility({visibilityProperty:true}),position:getComputedStyle(e).position}};
  const inputs=[...document.querySelectorAll('#session-recording input:checked,#match-recording input:checked')].map(e=>({name:e.name,value:e.value}));
  const control=document.querySelector('#session-recording form button,#match-recording form button,#learning-recorded-matches form button');
  return {text:n?.textContent??null,notice:box(n),dismiss:box(n?.querySelector('button')),control:box(control),
    color:n?getComputedStyle(n).color:null,background:n?getComputedStyle(n).backgroundColor:null,
    dismissColor:n?.querySelector('button')?getComputedStyle(n.querySelector('button')).color:null,
    dismissBackground:n?.querySelector('button')?getComputedStyle(n.querySelector('button')).backgroundColor:null,
    role:n?.getAttribute('role'),live:n?.getAttribute('aria-live'),atomic:n?.getAttribute('aria-atomic'),
    focus:{id:document.activeElement.id,name:document.activeElement.name,tag:document.activeElement.tagName},inputs,
    page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
    viewport:{innerWidth,innerHeight,outerWidth,outerHeight,devicePixelRatio,scale:visualViewport.scale},
    height:document.documentElement.scrollHeight,count:document.querySelectorAll('[data-operation-feedback]').length,
    generic:[...document.querySelectorAll('p')].filter(e=>/^(The explicit operation completed\.|Der ausdrückliche Vorgang wurde abgeschlossen\.)$/.test(e.textContent)).length,
    error:document.querySelector('.error-summary[role="alert"]')?.innerText??null,fragment:location.hash,visibility:document.visibilityState};
})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    installation = parser.add_mutually_exclusive_group(required=True)
    installation.add_argument("--wheel", type=Path)
    installation.add_argument("--source", action="store_true")
    parser.add_argument("--overlay", action="store_true", help="Focused Issue #276 overlay checks")
    parser.add_argument("--language-continuity", action="store_true",
                        help="Focused Issue #280 visible-feedback language continuation")
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert Path(skatmind.__file__).resolve().is_relative_to(REPOSITORY) == args.source
    args.output.mkdir()
    repaired = args.phase == "after"
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest() if args.wheel else None,
        "installation": "source-tree" if args.source else "installed Wheel",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip(),
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "hashes": {}, "pages": [], "actions": [], "setup": [], "sources": {}, "timing": {},
        "limitations": ["Synthetic headless Edge; no screen-reader/physical-device or maintainer UAT coverage.",
            "Existing narrow/enlarged comparison-table limit remains.",
            "Native cached history can retain an old response; server pop cannot erase browser caches."]}
    names = ("session_frontend.py", "match_frontend.py", "learning_frontend.py", "server.py",
        "card_entry_http.py", "match_recovery.py", "match_recovery_http.py", "match_recovery_rendering.py",
        "task_first_session_rendering.py", "task_first_match_rendering.py", "task_first_learning_rendering.py",
        "local_time_http.py", "language_context.py", "language_form_preservation.py",
        "validation_rendering.py", "form_registry.py",
        "locales/en.json", "locales/de.json", "assets/app.css", "assets/workflow.js",
        "rendering.py", "templates/app.html")
    if repaired:
        names += ("operation_feedback.py", "operation_feedback_mapping.py")
    for name in names:
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((REPOSITORY / "src/skatmind/app_web" / name).read_bytes() if repaired else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=REPOSITORY))
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

    def click(selector):
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
            + ");e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)

    def key(value, number, **extra):
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=value, windowsVirtualKeyCode=number, **extra)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=value, windowsVirtualKeyCode=number)

    def choose(selector, value):
        options = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].map(e=>e.value)")
        click(selector)
        key("Escape", 27)
        key("Home", 36)
        for _ in range(options.index(value)):
            key("ArrowDown", 40)
        key("Enter", 13, text="\r")
        assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").value") == value

    def action(selector, route):
        old_requests, old_calls = requests.copy(), calls.copy()
        click(selector)
        for _ in range(300):
            time.sleep(.1)
            if requests["POST " + route] > old_requests["POST " + route] and cdp.evaluate("document.readyState==='complete'"):
                time.sleep(.25)
                break
        delta = requests - old_requests
        assert sum(n for path, n in delta.items() if path.startswith("POST ")) == 1, (selector, delta)
        evidence["actions"].append({"selector": selector, "requests": dict(delta), "calls": dict(calls-old_calls),
            "javascript": not cdp.script_disabled, "focus": cdp.evaluate("document.activeElement.id")})

    def native(path, script, width=1365, height=900):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def capture(name, *, success=None, enlarged=False):
        if enlarged:
            cdp.evaluate(TEXT_ENLARGEMENT)
        row = cdp.evaluate(MEASURE)
        row.update(state=name, locale=cdp.evaluate("document.documentElement.lang"),
                   javascript=not cdp.script_disabled, enlarged=enlarged)
        assert row["page"] == row["client"], row
        if repaired:
            assert row["generic"] == 0
            if success is True:
                assert row["notice"]["visible"] and row["role"] == "status" and row["live"] == "polite", row
                assert row["notice"]["x"] >= 0 and row["notice"]["x"] + row["notice"]["width"] <= row["client"] + 1
                assert row["notice"]["position"] == ("static" if cdp.script_disabled else "fixed")
                assert row["dismiss"] is None if cdp.script_disabled else row["dismiss"]["visible"]
                def contrast(foreground, background):
                    def light(color):
                        components = [float(v) / 255 for v in color.removeprefix("rgb(").removesuffix(")").split(",")]
                        return sum(weight * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055)**2.4)
                                   for weight, v in zip((.2126, .7152, .0722), components, strict=True))
                    a, b = sorted((light(foreground), light(background)))
                    return (b + .05) / (a + .05)
                row["contrast"] = contrast(row["color"], row["background"])
                assert row["contrast"] >= 4.5
                if row["dismiss"] is not None:
                    row["dismissContrast"] = contrast(row["dismissColor"], row["dismissBackground"])
                    assert row["dismissContrast"] >= 4.5
                root = cdp.call("DOM.getDocument")["root"]["nodeId"]
                node = cdp.call("DOM.querySelector", nodeId=root, selector="[data-operation-feedback]")["nodeId"]
                tree = cdp.call("Accessibility.getPartialAXTree", nodeId=node)
                row["accessibility"] = [{k: item.get(k) for k in ("role", "name", "ignored", "properties")}
                    for item in tree["nodes"] if item.get("role", {}).get("value") in {"status", "StaticText", "button"}]
                status_node = next(item for item in row["accessibility"] if item["role"]["value"] == "status")
                assert not status_node["ignored"]
            if success is False:
                assert row["notice"] is None or not row["notice"]["visible"], row
        evidence["pages"].append(row)
        cdp.screenshot(args.output / (name + ".png"))
        return row

    def setup(label, function):
        old_calls, old_requests = calls.copy(), requests.copy()
        result = function()
        evidence["setup"].append({"label": label, "calls": dict(calls-old_calls), "requests": dict(requests-old_requests)})
        return result

    def hash_source(label, active):
        raw = active.path.read_bytes()
        evidence["sources"][label] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        return raw

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"),
                (execution, "execute", "session_executions"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves"),
                (learning, "import_match_workspace_into_learning_corpus_web_v1", "workspace_imports"),
                (learning, "prepare_learning_corpus_artifacts_web_v1", "preparations"),
                (learning, "initialize_learning_corpus_web_v1", "collection_creations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method, request_count(method, getattr(Handler, "do_" + method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=",1)[0], value=client.cookie.split("=",1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert hashlib.sha256(client.request("GET", route)[2]).hexdigest() == evidence["hashes"][resource]

            if args.language_continuity:
                verify_language_continuity(cdp, server, client, evidence, requests, calls,
                                           capture, action, click, key)
                evidence["completed"] = True
                print(json.dumps({"completed": True, "output": str(args.output)}, indent=2))
                return
            if args.overlay:
                verify_overlay(cdp, server, client, evidence, requests, calls, capture, action, click, key)
                evidence["completed"] = True
                print(json.dumps({"completed": True, "output": str(args.output)}, indent=2))
                return

            for locale in ("de", "en"):
                for script in (False, True):
                    stem = locale + ("-js" if script else "-native")
                    def prepare_creation(locale=locale):
                        page = client.page("/sessions")
                        page = follow(client, client.submit(Forms(page).find("/actions/profile/language"), language=locale))
                        return follow(client, client.submit(Forms(page).find("/sessions/create"),
                            game_name="Synthetic feedback", forehand_name="Alex", middlehand_name="Boris",
                            rearhand_name="Clara", capture_mode="live", perspective_seat="forehand", setup_action="update"))
                    setup(stem + "-roster", prepare_creation)
                    native("/sessions", script)
                    action('form[action="/sessions/create"] button[value="create"]', "/sessions/create")
                    capture(stem + "-created-1365", success=True)
                    if not script and locale == "de":
                        before = requests.copy()
                        time.sleep(8.3)
                        row = capture(stem + "-native-untimed", success=True)
                        assert requests == before
                        evidence["native_untimed"] = {"observed_seconds": 8.3,
                                                       "requests": dict(requests-before), "page": row}
                    active = server.app_context.managed_stateful.active_session
                    cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
                    for card in get_full_deck()[:11]:
                        click(f'#session-recording input[name="cards"][value="{card}"]')
                    action('#session-recording button[type="submit"]', "/sessions/cards")
                    row = capture(stem + "-error-390", success=False)
                    assert row["error"] and len(row["inputs"]) == 11
                    assert active.state.revision == 0
                    click(f'#session-recording input[name="cards"][value="{get_full_deck()[10]}"]')
                    action('#session-recording button[type="submit"]', "/sessions/cards")
                    capture(stem + "-hand-390", success=True)
                    assert active.state.revision == 11
                    action('#session-recording button[type="submit"]', "/sessions/command")
                    choose('#session-recording select[name="game_type"]', "grand")
                    click('#session-recording input[name="hand_game"]')
                    action('#session-recording button[type="submit"]', "/sessions/command")
                    # Explicit Grand declaration, shared with the existing legal fixture.
                    cdp.call("Emulation.setDeviceMetricsOverride", width=320, height=800, deviceScaleFactor=1, mobile=False)
                    click('#session-recording input[name="cards"][value="CK"]')
                    action('#session-recording button[type="submit"]', "/sessions/play")
                    capture(stem + "-play-320", success=True)
                    capture(stem + "-play-320-text200", success=True, enlarged=True)
                    saved = hash_source(stem, active)
                    if script and locale == "en" and repaired:
                        # Actual idle time, actual hover/focus and actual hidden-document events.
                        n = '[data-operation-feedback]'
                        click('#session-recording form input[name="cards"]')
                        cdp.evaluate(f"document.querySelector('{n}').scrollIntoView()")
                        point = cdp.evaluate(f"(()=>{{const r=document.querySelector('{n}').getBoundingClientRect();return {{x:r.x+5,y:r.y+5}}}})()")
                        before = requests.copy()
                        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
                        time.sleep(8.3)
                        assert cdp.evaluate(f"document.querySelector('{n}').checkVisibility({{visibilityProperty:true}})")
                        cdp.evaluate(f"document.querySelector('{n} button').focus()")
                        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=1, y=1)
                        time.sleep(8.3)
                        assert cdp.evaluate(f"document.querySelector('{n}').checkVisibility({{visibilityProperty:true}})")
                        cdp.evaluate("document.querySelector('#session-recording').focus()")
                        port = cdp.socket.getpeername()[1]
                        target = cdp.call("Target.createTarget", url="about:blank")["targetId"]
                        with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
                            tabs = json.load(response)
                        other = DevTools(next(t["webSocketDebuggerUrl"] for t in tabs if t["id"] == target))
                        other.call("Page.bringToFront")
                        hidden = cdp.evaluate("document.visibilityState")
                        assert hidden == "hidden", hidden
                        time.sleep(8.3)
                        assert cdp.evaluate(f"document.querySelector('{n}').checkVisibility({{visibilityProperty:true}})")
                        cdp.call("Page.bringToFront")
                        other.socket.close()
                        cdp.call("Target.closeTarget", targetId=target)
                        before_idle = cdp.evaluate(MEASURE)
                        started = time.monotonic()
                        while cdp.evaluate(f"document.querySelector('{n}').checkVisibility({{visibilityProperty:true}})"):
                            assert time.monotonic() - started < 10, cdp.evaluate(
                                "({hidden:document.hidden,hover:document.querySelector('[data-operation-feedback]').matches(':hover'),"
                                "focus:document.querySelector('[data-operation-feedback]').matches(':focus-within'),active:document.activeElement.outerHTML})")
                            time.sleep(.15)
                        after_idle = cdp.evaluate(MEASURE)
                        assert before_idle["focus"] == after_idle["focus"] and before_idle["inputs"] == after_idle["inputs"]
                        assert before_idle["control"] == after_idle["control"]
                        assert requests == before
                        evidence["timing"] = {"hover_seconds": 8.3, "focus_seconds": 8.3, "hidden_seconds": 8.3,
                            "hidden_state": hidden, "observed_final_idle_seconds": time.monotonic()-started,
                            "requests_during_display_hide": dict(requests-before), "before": before_idle, "after": after_idle}
                        cdp.screenshot(args.output / "actual-timeout.png")
                        history = cdp.call("Page.getNavigationHistory")
                        prior = history["entries"][history["currentIndex"]]["id"]
                        cdp.navigate(server.origin + "/")
                        cdp.call("Page.navigateToHistoryEntry", entryId=prior)
                        time.sleep(.8)
                        restored = cdp.evaluate(MEASURE)
                        assert restored["notice"] is None or not restored["notice"]["visible"]
                        evidence["expired_success_history"] = restored
                    # Native refresh and language do not reconstruct the completed Play.
                    native("/sessions/current", script, 320, 800)
                    capture(stem + "-refresh", success=False)
                    action(f'button[name="language"][value="{"en" if locale == "de" else "de"}"]', "/actions/profile/language")
                    capture(stem + "-language", success=False)
                    assert active.path.read_bytes() == saved
                    assert client.request("GET", "/sessions/downloads/session.json")[2] == saved

            # Match native start/Card/correction and same-Card Apply, then Learning native add/build.
            def match_setup():
                page = client.page("/matches/new")
                page = follow(client, client.submit(Forms(page).find("/actions/profile/language"), language="en"))
                return follow(client, client.submit(Forms(page).find("/matches/api/v1/create"),
                    match_title="Synthetic feedback Match", forehand_name="Anna", middlehand_name="Boris",
                    rearhand_name="Clara", perspective_seat="middlehand", setup_action="update"))
            setup("match-roster", match_setup)
            native("/matches/new", True, 390, 844)
            action('form[action="/matches/api/v1/create"] button[value="create"]', "/matches/api/v1/create")
            capture("match-created", success=True)
            action('#match-recording form:has(input[value="start_game"]) button', "/matches/api/v1/operation")
            capture("match-start", success=True)
            declarer_selector = '#match-recording select[name="declarer_player_id"]'
            declarer = cdp.evaluate("[...document.querySelector(" + json.dumps(declarer_selector)
                + ").options].map(e=>e.value).find(Boolean)")
            choose(declarer_selector, declarer)
            choose('#match-recording select[name="game_type"]', "grand")
            click('#match-recording input[name="hand_game"]')
            action('#match-recording form:has(input[value="set_declaration"]) button', "/matches/api/v1/operation")
            for card in ("CK", "C7", "CA"):
                click(f'#match-recording input[name="cards"][value="{card}"]')
                action('#match-recording form[action="/matches/cards"] button', "/matches/cards")
            capture("match-play", success=True)
            match = server.app_context.managed_stateful.active_match
            for suffix in ("changed", "noop"):
                action('#match-play-3 form[action="/matches/recovery/select"] button', "/matches/recovery/select")
                # Existing correction select, unchanged by this issue.
                selector = 'form[action="/matches/recovery/preview"] select[name="card"]'
                options = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].map(e=>e.value)")
                click(selector)
                key("Escape", 27)
                key("Home", 36)
                for _ in range(options.index("C10")):
                    key("ArrowDown", 40)
                key("Enter", 13, text="\r")
                action('form[action="/matches/recovery/preview"] button', "/matches/recovery/preview")
                click('input[name="confirm_apply"]')
                action('form[action="/matches/recovery/apply"] button', "/matches/recovery/apply")
                capture("match-correction-" + suffix, success=suffix == "changed")
                if suffix == "changed" and repaired:
                    cdp.call("Emulation.setEmulatedMedia", features=[
                        {"name": "prefers-reduced-motion", "value": "reduce"},
                        {"name": "forced-colors", "value": "active"}])
                    evidence["forced_colors"] = cdp.evaluate("(()=>{const n=document.querySelector('[data-operation-feedback]');const s=getComputedStyle(n);return {forced:matchMedia('(forced-colors: active)').matches,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,adjust:s.forcedColorAdjust,animation:s.animationName,visible:n.checkVisibility({visibilityProperty:true})}})()")
                    cdp.screenshot(args.output / "feedback-forced-colors.png")
                    cdp.call("Emulation.setEmulatedMedia", features=[])
                    before = requests.copy()
                    cdp.evaluate("document.querySelector('.operation-dismiss').focus()")
                    key("Enter", 13, text="\r")
                    assert cdp.evaluate("document.activeElement.className") != "operation-dismiss"
                    key("Tab", 9)
                    time.sleep(.1)
                    assert not cdp.evaluate("document.querySelector('[data-operation-feedback]').checkVisibility({visibilityProperty:true})")
                    assert requests == before
                    evidence["dismissal"] = {"requests": dict(requests-before), "focus_after_tab": cdp.evaluate("document.activeElement.name")}
            match_bytes = hash_source("match", match)
            setup("learning-form", lambda: client.page("/learning"))
            native("/learning", False, 320, 800)
            click('form[action="/learning/create"] input[name="collection_name"]')
            cdp.call("Input.insertText", text="Synthetic feedback collection")
            action('form[action="/learning/create"] button', "/learning/create")
            capture("learning-created", success=True)
            selector = 'form[action="/learning/add-recorded-match"] select[name="source_handle"]'
            click(selector)
            key("Escape", 27)
            key("Home", 36)
            key("ArrowDown", 40)
            key("Enter", 13, text="\r")
            action('form[action="/learning/add-recorded-match"] button', "/learning/add-recorded-match")
            capture("learning-added", success=True)
            click(selector)
            key("Escape", 27)
            key("Home", 36)
            key("ArrowDown", 40)
            key("Enter", 13, text="\r")
            action('form[action="/learning/add-recorded-match"] button', "/learning/add-recorded-match")
            capture("learning-identical", success=False)
            action('form:has(input[value="prepare_learning_artifacts"]) button', "/learning/api/v1/operations")
            capture("learning-built", success=True)
            assert match.path.read_bytes() == match_bytes
            target = server.app_context.managed_stateful.active_learning
            prepared = target.corpus.prepared_artifacts
            evidence["learning_downloads"] = {}
            from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
            for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
                raw = client.request("GET", '/learning/downloads/' + kind.replace('_', '-') + '.json')[2]
                evidence["learning_downloads"][kind] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            native("/learning/current", False, 320, 800)
            capture("learning-refresh", success=False)
            assert target.corpus.prepared_artifacts is prepared

            # Reuse one real ended SJ fixture, not a full replay for every receipt measurement.
            setup("ended-SJ-recording", lambda: record_score_review_game(client, play_count=30))
            setup("explicit-end", lambda: client.command("set_game_end"))
            session = server.app_context.managed_stateful.active_session
            selection = score_review_form(client)["values"]["decision_selection"]
            native("/sessions/current", True)
            action(f'form:has(input[value="{selection}"]) button', "/sessions/review-decision")
            capture("ended-SJ-result", success=False)
            assert cdp.evaluate("document.activeElement.id") == "session-result"
            assert len(session.decision_checkpoints) == 10 and session.state.revision == 44
            result = session.execution.result.result.document
            assert tuple(result["position"]["hand"]) == SESSION_HAND
            assert result["score_summary"]["explicit_declarer_points"] == 0
            assert result["score_summary"]["total_declarer_points"] == 14
            assert result["score_summary"]["total_defender_points"] == 29
            html = cdp.evaluate("document.documentElement.outerHTML")
            assert_summary_points(html, "en", 14, 29)
            assert_visible_equal_best(html, "en")
            evidence["SJ"] = {"checkpoints": 10, "revision": 44, "hand": list(SESSION_HAND),
                "request": {"bytes": len(session.execution.request_json_bytes), "sha256": hashlib.sha256(session.execution.request_json_bytes).hexdigest()},
                "result": {"bytes": len(session.execution.result_json_bytes), "sha256": hashlib.sha256(session.execution.result_json_bytes).hexdigest()},
                "visible": cdp.evaluate("document.querySelector('#session-result').innerText")}
            tree = cdp.call("Accessibility.getFullAXTree")
            evidence["result_accessibility_roles"] = Counter(n.get("role", {}).get("value") for n in tree["nodes"])
            history = cdp.call("Page.getNavigationHistory")
            current = history["entries"][history["currentIndex"]]["id"]
            cdp.navigate(server.origin + "/")
            cdp.call("Page.navigateToHistoryEntry", entryId=current)
            time.sleep(.8)
            assert session.execution is not None
            evidence["history_return"] = cdp.evaluate(MEASURE)
            evidence["counts"] = dict(calls)
            evidence["requests"] = dict(requests)
            evidence["native_post_count"] = sum(sum(n for path, n in row["requests"].items() if path.startswith("POST ")) for row in evidence["actions"])
            evidence["native_calls"] = dict(sum((Counter(row["calls"]) for row in evidence["actions"]), Counter()))
            evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=True), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({key: evidence[key] for key in ("completed", "phase", "counts", "native_post_count", "native_calls")}, indent=2))


GEOMETRY = r"""(() => {
  const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,width:r.width,height:r.height}};
  const root=document.querySelector('#session-recording,#learning-results') ||
    document.querySelector(location.hash==='#match-metadata'?'#match-metadata':'#match-recording');
  return {height:document.documentElement.scrollHeight,task:box(root),
    controls:[...root.querySelectorAll('input:not([type=hidden]),select,button')].filter(e=>e.getClientRects().length&&!e.closest('[data-operation-feedback]')).map(box)};
})()"""


def verify_language_continuity(cdp, server, client, evidence, requests, calls,
                               capture, action, click, key):
    """One real save/partial-display/translation/expiry sequence; no clock injection."""
    import skatmind.app_web.server as web_server
    from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

    evidence["limitations"] = [
        "Disposable synthetic source-tree developer evidence, not installed-build or maintainer UAT acceptance.",
        "Actual 200% browser zoom unavailable in the existing headless transport; no resize or scale is claimed as zoom.",
        "No screen-reader or physical-device verification.",
    ]
    window = cdp.call("Browser.getWindowForTarget")["windowId"]
    cdp.call("Browser.setWindowBounds", windowId=window,
             bounds={"width": 1440, "height": 1000, "windowState": "normal"})
    cdp.call("Page.addScriptToEvaluateOnNewDocument", source=r"""
      window.feedbackTrace={shown:null,hidden:null,loading:[]};
      new MutationObserver(()=>{
        const n=document.querySelector('[data-operation-feedback]');if(!n)return;
        const trace=window.feedbackTrace;
        if(trace.loading.length<20)trace.loading.push({ready:document.readyState,position:getComputedStyle(n).position});
        if(n.dataset.enhanced && !n.hidden && trace.shown===null)trace.shown=performance.now();
        if(trace.shown!==null && n.hidden && trace.hidden===null)trace.hidden=performance.now();
      }).observe(document,{childList:true,subtree:true,attributes:true});
    """)
    page = client.page("/sessions")
    page = follow(client, client.submit(Forms(page).find("/actions/profile/language"), language="en"))
    page = follow(client, client.submit(Forms(page).find("/sessions/create"),
        game_name="Synthetic language feedback 280", forehand_name='Alex <&> "Player"',
        middlehand_name="Boris", rearhand_name="Clara", capture_mode="live",
        perspective_seat="forehand", setup_action="update"))
    follow(client, client.submit(Forms(page).find("/sessions/create"), setup_action="create"))
    cdp.navigate(server.origin + "/sessions/current")
    before_save = calls.copy()
    click('#session-recording input[name="cards"][value="CA"]')
    action('#session-recording button[type="submit"]', "/sessions/cards")
    assert calls["session_saves"] == before_save["session_saves"] + 1
    active = server.app_context.managed_stateful.active_session
    document, operation = active.document, active.last_operation
    accepted = active.path.read_bytes()
    assert active.state.revision == 2
    cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=1, y=1)
    cdp.evaluate("document.querySelector('input[name=cards][value=H7]').click()")
    cdp.evaluate("document.querySelector('.language-selector button[value=de]').focus({preventScroll:true});window.scrollTo(0,document.getElementById('session-recording').offsetTop-250)")
    capture("language-visible-before", success=True)
    while cdp.evaluate("performance.now()-feedbackTrace.shown") < 3000:
        time.sleep(.05)
    before_view = cdp.evaluate("({y:scrollY,top:document.getElementById('session-recording').getBoundingClientRect().top})")
    before_requests, before_calls = requests.copy(), calls.copy()
    before_trace = cdp.evaluate("feedbackTrace")
    with patch.object(web_server, "parse_language_page_values_v1",
                      wraps=web_server.parse_language_page_values_v1) as parsed:
        key("Enter", 13, text="\r")
        started = time.monotonic()
        while cdp.evaluate("document.documentElement.lang!=='de' || document.readyState!=='complete'"):
            assert time.monotonic() - started < 15
            time.sleep(.05)
    assert parsed.call_count == 1
    submitted = json.loads(parsed.call_args.args[0])
    remaining = submitted["feedback_remaining_ms"]
    assert 3500 < remaining < 5500, remaining
    returned = capture("language-visible-translated", success=True)
    assert text("de", "feedback.initial_cards", count=1, player='Alex <&> "Player"') in returned["text"]
    assert text("de", "feedback.dismiss") in returned["text"]
    assert returned["focus"]["name"] == "language" and returned["inputs"] == [{"name": "cards", "value": "H7"}]
    assert returned["count"] == 1
    assert cdp.evaluate("document.activeElement.value") == "de"
    after_view = cdp.evaluate("({y:scrollY,top:document.getElementById('session-recording').getBoundingClientRect().top})")
    assert abs(before_view["top"] - after_view["top"]) < 2
    assert cdp.evaluate("location.search+location.hash") == ""
    geometry = cdp.evaluate(GEOMETRY)
    while cdp.evaluate("!document.querySelector('[data-operation-feedback]').hidden"):
        assert time.monotonic() - started < 8
        time.sleep(.05)
    trace = cdp.evaluate("feedbackTrace")
    elapsed = trace["hidden"] - trace["shown"]
    assert abs(elapsed - remaining) < 350, (elapsed, remaining)
    assert elapsed < 6000
    assert geometry == cdp.evaluate(GEOMETRY)
    expired = capture("language-remaining-expired", success=False)
    assert expired["focus"] == returned["focus"] and expired["inputs"] == returned["inputs"]
    assert any(row["ready"] == "loading" for row in trace["loading"])
    assert all(row["position"] == "fixed" for row in trace["loading"])
    action('.language-selector button[value="en"]', "/actions/profile/language")
    absent = capture("language-expired-not-restored", success=False)
    assert absent["count"] == 0 and absent["inputs"] == returned["inputs"]
    assert active.document is document and active.last_operation is operation
    assert active.path.read_bytes() == accepted
    assert client.request("GET", "/sessions/downloads/session.json")[2] == accepted
    changed_calls = calls - before_calls
    assert {name: count for name, count in changed_calls.items()
            if name != "profile_saves"} == {}
    assert changed_calls["profile_saves"] == 2
    delta = requests - before_requests
    assert {route: count for route, count in delta.items() if route.startswith("POST ")} == {
        "POST /actions/profile/language": 2}
    evidence["continuation"] = {"submitted_remaining_ms": remaining,
        "active_ms_before_submission": 8000 - remaining, "observed_resumed_ms": elapsed,
        "before_trace": before_trace, "return_trace": trace,
        "view_before": before_view, "view_after": after_view,
        "requests": dict(delta), "product_calls": {}, "profile_saves": 2,
        "accepted_revision": active.state.revision,
        "accepted_sha256": hashlib.sha256(accepted).hexdigest(), "accepted_unchanged": True,
        "downloads_unchanged": True, "geometry_unchanged_on_expiry": True}
    # Small opposite-direction/dismissal check; no additional expiry sleep.
    action('#session-recording button[type="submit"]', "/sessions/cards")  # Save pending H7.
    action('.language-selector button[value="de"]', "/actions/profile/language")
    capture("language-second-visible-de", success=True)
    action('.language-selector button[value="en"]', "/actions/profile/language")
    capture("language-second-visible-en", success=True)
    cdp.evaluate("document.querySelector('.operation-dismiss').focus({preventScroll:true})")
    key("Enter", 13, text="\r")
    action('.language-selector button[value="de"]', "/actions/profile/language")
    dismissed = capture("language-dismissed-not-restored", success=False)
    assert dismissed["count"] == 0
    evidence["opposite_direction_and_dismissal"] = True
    evidence["counts"] = dict(calls)
    evidence["requests"] = dict(requests)


def verify_overlay(cdp, server, client, evidence, requests, calls, capture, action, click, key):
    """Real native final-Card returns, never recreated receipts or accelerated clocks."""
    evidence["limitations"] = [
        "Headless Edge/source or explicitly identified Wheel; no interactive GUI or maintainer UAT.",
        "Actual 200% browser zoom unperformed: existing transport has no verified real-zoom control. No CSS/device scaling is represented as zoom.",
        "No screen-reader test; accessibility tree inspection only.",
    ]
    evidence["zoom"] = "Fresh isolated profile default 100%; native window bounds, DPR/visual scale measured per capture."
    window = cdp.call("Browser.getWindowForTarget")["windowId"]
    cdp.call("Page.addScriptToEvaluateOnNewDocument", source=r"""
      window.feedbackLoading=[];window.feedbackRestored=false;
      new MutationObserver(()=>{
        const n=document.querySelector('[data-operation-feedback]');
        if(n&&feedbackLoading.length<30)feedbackLoading.push({ready:document.readyState,position:getComputedStyle(n).position});
      }).observe(document,{childList:true,subtree:true});
      addEventListener('pageshow',e=>{window.feedbackRestored=e.persisted});
    """)

    def resize(width, height):
        cdp.call("Browser.setWindowBounds", windowId=window,
                 bounds={"width": width, "height": height, "windowState": "normal"})
        time.sleep(.2)
        measured = cdp.evaluate("({innerWidth,innerHeight,outerWidth,outerHeight})")
        cdp.call("Browser.setWindowBounds", windowId=window, bounds={
            "width": width + measured["outerWidth"] - measured["innerWidth"],
            "height": height + measured["outerHeight"] - measured["innerHeight"]})
        time.sleep(.2)
        assert cdp.evaluate("[innerWidth,innerHeight]") == [width, height], cdp.evaluate("({innerWidth,innerHeight,outerWidth,outerHeight})")

    def create(locale, width, *, script=True, long=False, blocked=False, final=True):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.call("Network.setBlockedURLs", urls=["*capture.js"] if blocked else [])
        resize(width, 900 if width > 800 else 844)
        page = client.page("/sessions")
        page = follow(client, client.submit(Forms(page).find("/actions/profile/language"), language=locale))
        page = follow(client, client.submit(Forms(page).find("/sessions/create"),
            game_name="Synthetic overlay 276", forehand_name="Synthetic Alex <&> " + ("LongPlayerName" * 7 if long else ""),
            middlehand_name="Synthetic Boris", rearhand_name="Synthetic Clara",
            capture_mode="live", perspective_seat="forehand", setup_action="update"))
        page = follow(client, client.submit(Forms(page).find("/sessions/create"), setup_action="create"))
        if final:
            follow(client, client.submit(Forms(page).find("/sessions/cards"),
                cards=["CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA"]))
        cdp.navigate(server.origin + "/sessions/current")
        click('#session-recording input[name="cards"][value="S10"]')
        action('#session-recording button[type="submit"]', "/sessions/cards")
        active = server.app_context.managed_stateful.active_session
        if final:
            assert active.state.revision == 11
            assert cdp.evaluate("!!document.querySelector('#session-recording select[name=player_id]')")
        return active

    def visible():
        return cdp.evaluate("document.querySelector('[data-operation-feedback]')?.checkVisibility({visibilityProperty:true}) ?? false")

    def remove_compare(before):
        cdp.evaluate("document.querySelector('[data-operation-feedback]').remove()")
        absent = cdp.evaluate(GEOMETRY)
        assert before == absent, {"before": before, "absent": absent}
        return absent

    def wait_expired():
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=1, y=1)
        start = time.monotonic()
        while visible():
            assert time.monotonic() - start < 10
            time.sleep(.1)
        return time.monotonic() - start

    evidence["overlay_geometry"] = []
    for locale in ("de", "en"):
        for width in (1365, 600):
            for mode in ("expiry", "dismissal"):
                active = create(locale, width, long=True)
                name = f"overlay-{locale}-{width}-{mode}"
                capture(name + "-arrival", success=True)
                # User scroll leaves room to exercise input during the full timed display.
                # A separate overlap case below verifies immediate withdrawal on focus.
                cdp.evaluate("window.scrollBy(0,-250)")
                row = capture(name, success=True)
                assert row["count"] == 1 and row["viewport"]["devicePixelRatio"] == 1
                assert cdp.evaluate("(()=>{const n=document.querySelector('[data-operation-feedback]'),r=n.getBoundingClientRect();return !n.contains(document.elementFromPoint(r.x+3,r.y+3))})()")
                loading = cdp.evaluate("feedbackLoading")
                assert loading and all(item["position"] == "fixed" for item in loading), loading
                assert any(item["ready"] == "loading" for item in loading), loading
                geometry = cdp.evaluate(GEOMETRY)
                saved, before_requests, before_calls = active.path.read_bytes(), requests.copy(), calls.copy()
                selector = '#session-recording select[name="player_id"]'
                cdp.evaluate(f"document.querySelector('{selector}').focus({{preventScroll:true}})")
                assert visible()
                key("ArrowDown", 40)
                selected = cdp.evaluate(f"document.querySelector('{selector}').value")
                if mode == "expiry":
                    elapsed = wait_expired()
                else:
                    cdp.evaluate("document.querySelector('.operation-dismiss').focus({preventScroll:true})")
                    assert cdp.evaluate("getComputedStyle(document.activeElement).outlineStyle") != "none"
                    key("Enter", 13, text="\r")
                    elapsed = None
                assert not visible()
                assert cdp.evaluate(f"document.activeElement===document.querySelector('{selector}')")
                assert cdp.evaluate(f"document.querySelector('{selector}').value") == selected
                hidden_geometry = cdp.evaluate(GEOMETRY)
                assert geometry == hidden_geometry
                assert cdp.evaluate("document.querySelector('.operation-dismiss').getClientRects().length") == 0
                hidden = capture(name + "-hidden", success=False)
                absent = remove_compare(geometry)
                assert requests == before_requests and calls == before_calls and active.path.read_bytes() == saved
                # Also compare the actual ordinary GET, whose server receipt is already consumed.
                cdp.navigate(server.origin + "/sessions/current")
                assert not visible() and cdp.evaluate(GEOMETRY) == absent
                evidence["overlay_geometry"].append({"case": name, "visible": geometry,
                    "hidden": hidden_geometry, "absent": absent, "initialization": loading,
                    "elapsed_idle_seconds": elapsed, "focus_after": hidden["focus"],
                    "presentation_requests": 0, "presentation_product_calls": 0})

    # Actual hover, focused-button and hidden-document time, with pending Cards.
    active = create("en", 1365, final=False)
    click('#session-recording input[name="cards"][value="SJ"]')
    before = cdp.evaluate(MEASURE)
    pending, saved = before["inputs"], active.path.read_bytes()
    before_requests, before_calls = requests.copy(), calls.copy()
    cdp.evaluate("window.scrollTo(0,document.querySelector('#session-recording').offsetTop-250)")
    time.sleep(.2)  # Wait for the real scroll event before locating the pointer target.
    point = cdp.evaluate("(()=>{const r=document.querySelector('.operation-dismiss').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
    cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
    assert cdp.evaluate("document.querySelector('.operation-dismiss').matches(':hover')")
    time.sleep(8.3)
    assert visible()
    cdp.evaluate("document.querySelector('.operation-dismiss').focus({preventScroll:true})")
    cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=1, y=1)
    time.sleep(8.3)
    assert visible()
    cdp.evaluate("document.querySelector('#session-recording input[value=SJ]').focus({preventScroll:true})")
    target = cdp.call("Target.createTarget", url="about:blank")["targetId"]
    port = cdp.socket.getpeername()[1]
    with urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as response:
        tabs = json.load(response)
    other = DevTools(next(t["webSocketDebuggerUrl"] for t in tabs if t["id"] == target))
    try:
        other.call("Page.bringToFront")
        assert cdp.evaluate("document.visibilityState") == "hidden"
        time.sleep(8.3)
        assert visible()
        cdp.call("Page.bringToFront")
    finally:
        other.socket.close()
        cdp.call("Target.closeTarget", targetId=target)
    elapsed = wait_expired()
    after = capture("overlay-pauses-expired", success=False)
    assert after["inputs"] == pending and after["focus"]["name"] == "cards"
    assert requests == before_requests and calls == before_calls and active.path.read_bytes() == saved
    evidence["timing"] = {"hover_seconds": 8.3, "focus_seconds": 8.3, "hidden_seconds": 8.3,
        "remaining_idle_seconds": elapsed, "pending": pending, "requests": 0, "product_calls": 0}
    history = cdp.call("Page.getNavigationHistory")
    prior = history["entries"][history["currentIndex"]]["id"]
    cdp.navigate(server.origin + "/")
    cdp.call("Page.navigateToHistoryEntry", entryId=prior)
    time.sleep(.8)
    assert not visible()
    evidence["history"] = {"cached": cdp.evaluate("feedbackRestored"), "page": cdp.evaluate(MEASURE)}
    if not evidence["history"]["cached"]:
        evidence["limitations"].append("History returned without BFCache; cached-history restoration was not exercised.")

    # Pointer-transparent content plus bounded withdrawal when an active input overlaps.
    create("de", 600)
    cdp.evaluate("window.scrollBy(0,-250)")
    capture("overlay-scrolled", success=True)
    cdp.call("Emulation.setEmulatedMedia", features=[
        {"name": "prefers-reduced-motion", "value": "reduce"},
        {"name": "forced-colors", "value": "active"}])
    capture("overlay-forced-colors")
    assert cdp.evaluate("getComputedStyle(document.querySelector('[data-operation-feedback]')).animationName") == "none"
    cdp.call("Emulation.setEmulatedMedia", features=[])
    cdp.evaluate("(()=>{const e=document.querySelector('#session-recording select');window.scrollBy(0,e.getBoundingClientRect().top-20);e.focus({preventScroll:true})})()")
    assert not visible()
    assert cdp.evaluate("document.activeElement.tagName") == "SELECT"
    capture("overlay-active-control-withdrawal", success=False)

    create("en", 600, long=True)
    cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=300, deviceScaleFactor=1, mobile=False)
    time.sleep(.2)
    capture("overlay-small-viewport-withdrawal", success=False)
    evidence["small_viewport"] = "390x300 CDP viewport emulation, not browser zoom; oversized receipt withdrawn."
    cdp.call("Emulation.clearDeviceMetricsOverride")

    # Native forms, script delivery failure, safe selections and persistent errors.
    for script, blocked, name in ((False, False, "native"), (True, True, "blocked-script")):
        create("de" if not script else "en", 600, script=script, blocked=blocked)
        row = capture(name + "-confirmation", success=True if not script else None)
        assert row["notice"]["position"] == "static" and row["dismiss"] is None
        time.sleep(8.3)
        assert visible()
        action('#session-recording button[type="submit"]', "/sessions/command")
    cdp.call("Network.setBlockedURLs", urls=[])
    create("en", 600, final=False)
    selected = cdp.evaluate("[...document.querySelectorAll('#session-recording input[name=cards]')].slice(0,11).map(e=>e.value)")
    for card in selected:
        click(f'#session-recording input[name="cards"][value="{card}"]')
    action('#session-recording button[type="submit"]', "/sessions/cards")
    error = capture("overlay-persistent-error", success=False)
    assert error["error"] and len(error["inputs"]) == 11
    time.sleep(8.3)
    assert cdp.evaluate(MEASURE)["error"] == error["error"]
    action('button[name="language"][value="de"]', "/actions/profile/language")
    assert cdp.evaluate(MEASURE)["inputs"] == error["inputs"]
    click(f'#session-recording input[name="cards"][value="{selected[-1]}"]')
    action('button[name="language"][value="en"]', "/actions/profile/language")
    assert len(cdp.evaluate(MEASURE)["inputs"]) == 10
    assert "10" in cdp.evaluate("document.querySelector('.compact-count').textContent")

    page = client.page("/sessions")
    follow(client, client.submit(Forms(page).find("/sessions/create"),
        game_name="Synthetic warning 276", forehand_name="Alex", middlehand_name="Boris",
        rearhand_name="Clara", capture_mode="live", perspective_seat="forehand", setup_action="update"))
    cdp.navigate(server.origin + "/sessions")
    import skatmind.app_web.server as web_server
    with patch.object(web_server, "save_prepared_frontend_profile_v1", side_effect=OSError("Synthetic profile fault")):
        action('form[action="/sessions/create"] button[value="create"]', "/sessions/create")
    capture("overlay-persistent-warning", success=False)
    warning = cdp.evaluate("document.querySelector('.profile-warning').textContent")
    time.sleep(8.3)
    assert cdp.evaluate("document.querySelector('.profile-warning').textContent") == warning

    # Shared real Match metadata return and Learning creation/Add/retained outcomes.
    from test_learning_direct_entry_web import create_collection
    from test_match_game_navigation_web import create_empty
    resize(1365, 900)
    create_empty(client, "en")
    page = client.page("/matches/current")
    response = client.submit(local_form(page, "match-metadata"), time_mode="replace",
                             local_date="2026-01-15", local_time="19:30")
    assert response[0] == 303
    cdp.navigate(server.origin + response[1]["location"])
    capture("overlay-match-metadata", success=True)
    geometry = cdp.evaluate(GEOMETRY)
    remove_compare(geometry)
    create_collection(client)
    cdp.navigate(server.origin + "/learning/current")
    selector = 'form[action="/learning/add-recorded-match"] select[name="source_handle"]'
    cdp.evaluate(f"document.querySelector('{selector}').focus()")
    key("ArrowDown", 40)
    action('form[action="/learning/add-recorded-match"] button', "/learning/add-recorded-match")
    capture("overlay-learning-added", success=True)
    action('form:has(input[value="prepare_learning_artifacts"]) button', "/learning/api/v1/operations")
    capture("overlay-learning-outcome", success=True)
    geometry = cdp.evaluate(GEOMETRY)
    remove_compare(geometry)
    target = server.app_context.managed_stateful.active_learning
    prepared = target.corpus.prepared_artifacts
    from test_learning_direct_entry_web import downloads
    retained = downloads(client)
    cdp.evaluate(f"document.querySelector('{selector}').focus()")
    key("ArrowDown", 40)
    action('form[action="/learning/add-recorded-match"] button', "/learning/add-recorded-match")
    capture("overlay-learning-neutral-outcome", success=False)
    assert target.corpus.prepared_artifacts is prepared and downloads(client) == retained
    evidence["counts"] = dict(calls)
    evidence["requests"] = dict(requests)


if __name__ == "__main__":
    main()
