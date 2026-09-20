# ruff: noqa: E501 - Keep native selectors and browser measurements legible.
"""Independent installed-Wheel operation-feedback evidence on disposable synthetic roots.

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

from test_equal_best_immediate import assert_visible_equal_best  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_frontend_result_presentation import assert_summary_points  # noqa: E402
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
    generic:[...document.querySelectorAll('p')].filter(e=>/^(The explicit operation completed\.|Der ausdrückliche Vorgang wurde abgeschlossen\.)$/.test(e.textContent)).length,
    error:document.querySelector('.error-summary[role="alert"]')?.innerText??null,fragment:location.hash,visibility:document.visibilityState};
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
    repaired = args.phase == "after"
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip(),
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "hashes": {}, "pages": [], "actions": [], "setup": [], "sources": {}, "timing": {},
        "limitations": ["Synthetic headless Edge; no screen-reader/physical-device or maintainer UAT coverage.",
            "Existing narrow/enlarged comparison-table limit remains.",
            "Native cached history can retain an old response; server pop cannot erase browser caches."]}
    names = ("session_frontend.py", "match_frontend.py", "learning_frontend.py", "server.py",
        "card_entry_http.py", "match_recovery.py", "match_recovery_http.py", "match_recovery_rendering.py",
        "task_first_session_rendering.py", "task_first_match_rendering.py", "task_first_learning_rendering.py",
        "local_time_http.py", "language_context.py", "validation_rendering.py", "form_registry.py",
        "locales/en.json", "locales/de.json", "assets/app.css", "assets/workflow.js")
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
                assert row["notice"]["position"] == "static"
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
                    assert cdp.evaluate("document.activeElement.className") == "operation-dismiss"
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


if __name__ == "__main__":
    main()
