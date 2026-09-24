# ruff: noqa: E501 - Keep optional native selectors and evidence records legible.
"""Bounded #260 independent-Wheel evidence; synthetic data, existing DevTools only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, wait
from verify_match_game_navigation import MODULES, PLAY
from verify_recording_task_focus import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_game_navigation_web import create_empty, declare, primary  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form, synthetic_cards  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.server as server_module  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402
from skatmind.match_workspace_persistence import load_match_workspace_file_v1  # noqa: E402


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    evidence = dict(completed=False, phase=args.phase, python=sys.version,
        installed_module=skatmind.__file__, versions={name: version(name) for name in (
            "skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        wheel_sha256=digest(args.wheel.read_bytes()), hashes={}, runs=[],
        registry=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        keys={k: len(v) for k, v in load_frontend_translation_catalogs_v1().items()},
        starting_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip())
    assert evidence["registry"] == [67, 112]
    for name in (*MODULES, "app_web/task_first_contracts.py", "match_capture_application_contracts.py"):
        raw = (Path(skatmind.__file__).parent / name).read_bytes()
        expected = ((ROOT / "src/skatmind" / name).read_bytes() if args.phase == "after" else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/" + name], cwd=ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
    try:
        def run_one(locale, javascript):
            root = args.output / (locale + ("-js" if javascript else "-native"))
            root.mkdir()
            fixture = localized_server.__wrapped__(root)
            server = next(fixture)
            browser = Browser(server)
            local = LocalBrowser(args.browser, root / "browser")
            cdp = local.cdp
            calls, requests = Counter(), Counter()
            item = dict(locale=locale, javascript=javascript, browser=local.version,
                operations=[], measurements=[], retained={})
            evidence["runs"].append(item)

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

            real_replace = os.replace

            def replace(source, destination):
                if Path(destination).parent == server.app_context.managed_stateful.root("matches"):
                    calls["match_save"] += 1
                return real_replace(source, destination)

            def operation(name, function, *, passive=False):
                before, req = calls.copy(), requests.copy()
                result = function()
                delta = calls - before
                item["operations"].append(dict(name=name, calls=dict(delta), requests=dict(requests-req)))
                if passive:
                    assert not delta["match_save"] and not delta["analysis"]
                return result

            def key(name):
                for kind in ("keyDown", "keyUp"):
                    cdp.call("Input.dispatchKeyEvent", type=kind, key=name,
                        windowsVirtualKeyCode={"Tab": 9, "Enter": 13}[name],
                        **({"text": "\r"} if name == "Enter" and kind == "keyDown" else {}))

            def focus():
                return cdp.evaluate("({tag:document.activeElement.tagName,id:document.activeElement.id,name:document.activeElement.name,href:document.activeElement.getAttribute('href'),text:document.activeElement.innerText,outline:getComputedStyle(document.activeElement).outline})")

            def click(selector):
                point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getClientRects()[0];return {x:r.x+r.width/2,y:r.y+Math.min(15,r.height/2)}})()")
                for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                    cdp.call("Input.dispatchMouseEvent", type=kind, **point,
                        **({"button": "left", "clickCount": 1} if kind != "mouseMoved" else {}))
                time.sleep(.6)

            def action(name, selector, *, passive=False, keyboard=False):
                def invoke():
                    if keyboard:
                        # Reach the control by Tab from the native fragment destination.
                        for _ in range(160):
                            if cdp.evaluate("document.activeElement.matches(" + json.dumps(selector) + ")"):
                                break
                            key("Tab")
                        else:
                            raise AssertionError((selector, focus()))
                        key("Enter")
                        time.sleep(.6)
                    else:
                        click(selector)
                    wait(cdp)
                    result = dict(url=cdp.evaluate("location.pathname+location.hash"), focus=focus(),
                        selected=server.app_context.managed_stateful.active_match.selected_position)
                    key("Tab")
                    result["next_tab"] = focus()
                    item.setdefault("navigation", {})[name] = result
                operation(name, invoke, passive=passive)

            def navigate(path):
                cdp.navigate("about:blank")
                cdp.navigate(server.origin + path)

            def measure(name, position=1, *, matrix=False):
                active = server.app_context.managed_stateful.active_match
                accepted = active.path.read_bytes()
                sizes = ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)) if matrix else ((390, 844, 1),)
                for width, height, scale in sizes:
                    def inspect(width=width, height=height, scale=scale):
                        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
                        navigate(f"/matches/position/{position}#match-recording")
                        if scale == 2:
                            cdp.evaluate(TEXT_ENLARGEMENT)
                            # Restore the photographed region after font reflow, without moving focus.
                            cdp.evaluate("document.querySelector('#match-recording').scrollIntoView()")
                        values = cdp.evaluate("""(()=>{const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText,top:r.top+scrollY,left:r.left,width:r.width,height:r.height,font:s.fontSize,weight:s.fontWeight,color:s.color}};
                            const root=document.querySelector('#match-recording'),tiles=[...document.querySelectorAll('.match-tile')];
                            return {client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                            heading:box(document.querySelector('#match-recording-heading')),following:box(document.querySelector('#match-recording-heading').nextElementSibling),
                            status:root.querySelector('.match-recording-status')?.innerText??null,
                            round:box(document.querySelector('#match-games h3')),rounds:document.querySelectorAll('.round-slots').length,
                            selected:tiles.filter(e=>e.hasAttribute('aria-current')).map(box),tiles:tiles.map(e=>({href:e.getAttribute('href'),...box(e)})),
                            continuation:[...root.querySelectorAll('a[href^="/matches/position/"]')].map(e=>({href:e.getAttribute('href'),...box(e)}))};})()""")
                        values.update(state=name, width=width, scale=scale, focus=focus())
                        assert values["rounds"] == 12 and len(values["selected"]) == 1
                        assert [t["href"] for t in values["tiles"]] == [f"/matches/position/{n}#match-recording" for n in range(1, 37)]
                        assert values["client"] == values["scroll"], values
                        item["measurements"].append(values)
                        cdp.screenshot(root / f"{name}-{width}-{scale}-recording.png")
                        cdp.evaluate("document.querySelector('#match-games').scrollIntoView()")
                        cdp.screenshot(root / f"{name}-{width}-{scale}-overview.png")
                        if scale == 2:
                            cdp.evaluate("document.querySelector('.match-tile[aria-current]').scrollIntoView()")
                            cdp.screenshot(root / f"{name}-{width}-{scale}-selected.png")
                    operation(f"measure-{name}-{width}-{scale}", inspect, passive=True)
                assert active.path.read_bytes() == accepted

            try:
                with ExitStack() as stack:
                    stack.enter_context(patch("os.replace", replace))
                    for module, attr, label in (
                        (profile, "save_frontend_profile_file_v1", "profile_save"),
                        (server_module, "build_task_first_match_page_state_v1", "page_preparation"),
                        (analysis, "execute_match_decision_analysis_v1", "analysis")):
                        stack.enter_context(patch.object(module, attr, counted(label, getattr(module, attr))))
                    for method in ("GET", "POST"):
                        attr = "do_" + method
                        stack.enter_context(patch.object(Handler, attr, request_count(method, getattr(Handler, attr))))
                    page = operation("fixture-create-returned-forms", lambda: create_empty(browser, locale))
                    active = server.app_context.managed_stateful.active_match
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                    cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
                    time.sleep(.6)
                    measure("empty")
                    page = operation("fixture-start", lambda: follow(browser, browser.submit(primary(page, "start_game"))))
                    measure("setup")
                    page = operation("fixture-declare", lambda: declare(browser, page))
                    measure("ready")
                    cards = synthetic_cards()
                    for count, card in enumerate(cards[:4], 1):
                        navigate("/matches/position/1#match-recording")
                        choose(cdp, PLAY + f' input[value="{card}"]')
                        action(f"record-{count}", PLAY + " button")
                        measure(f"plays-{count}", matrix=count in (3, 4))
                    navigate("/matches/position/1#match-recording")
                    action("overview-keyboard", 'a[href="#match-games"]', passive=True, keyboard=True)
                    # Tab from the native overview target: the back-link, Game 1, then Game 2.
                    action("game-2-keyboard", '.match-tile[href="/matches/position/2#match-recording"]', passive=True, keyboard=True)
                    action("pass", '#match-recording form:has(input[value="mark_passed_deal"]) button')
                    measure("passed-earlier-target", 2, matrix=True)
                    action("earlier-target-pointer", '#match-recording a[href="/matches/position/1#match-recording"]', passive=True)
                    assert active.selected_position == 1
                    page = browser.page("/matches/current")
                    legacy = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/operation" and f["values"].get("operation") == "append_plays")
                    operation("fixture-25-legal-plays", lambda: follow(browser, browser.submit(legacy, cards=" ".join(cards[4:29]))))
                    measure("plays-29", matrix=True)
                    navigate("/matches/position/1#match-recording")
                    choose(cdp, PLAY + f' input[value="{cards[-1]}"]')
                    action("record-30", PLAY + " button")
                    measure("complete", matrix=True)
                    action("review", '#match-recording a[href="/matches/review/1"]', passive=True)
                    # One bounded genuine execution through an emitted form, separate from navigation.
                    page = browser.page("/matches/review/1")
                    operation("explicit-report-returned-form", lambda: follow(browser, browser.submit(operation_form(page, "analyze_decision"), immediate_sample_count="1")))
                    report = active.capture.report_store.list()[-1]
                    assert report.value.status == "executed"
                    route = f"/matches/api/v1/reports/{report.report_id}.json"
                    raw = operation("retained-download", lambda: browser.request("GET", route)[2], passive=True)
                    accepted = active.path.read_bytes()
                    item["retained"] = dict(report_id=report.report_id, game=report.match_position,
                        report_sha256=digest(raw), workspace_sha256=digest(accepted), bytes=len(raw),
                        request_sha256=digest(json.dumps(report.value.request.to_dict(), sort_keys=True).encode()),
                        result_sha256=digest(json.dumps(report.value.result.to_dict(), sort_keys=True).encode()))
                    for pos in (1, 2, 1):
                        operation(f"retained-navigation-{pos}", lambda pos=pos: navigate(f"/matches/position/{pos}#match-recording"), passive=True)
                        if pos == 2:
                            selected_text = cdp.evaluate("document.querySelector('.match-tile[aria-current]').innerText")
                            assert ("Eingepasst" if locale == "de" else "Passed") in selected_text
                            item["retained"]["other_selected_tile"] = selected_text
                    for target in ("en" if locale == "de" else "de", locale):
                        action("language-" + target, f'form.language-selector button[value="{target}"]', passive=True)
                    assert active.capture.report_store.list() == (report,)
                    assert operation("retained-download-again", lambda: browser.request("GET", route)[2], passive=True) == raw
                    assert active.path.read_bytes() == accepted
                    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
                    operation("strict-reopen-returned-form", lambda: follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open"))), passive=True)
                    reopened = server.app_context.managed_stateful.active_match
                    assert reopened is not active and reopened.workspace == active.workspace
                    assert reopened.path.read_bytes() == accepted and not reopened.capture.report_store.list()
                    item["totals"] = dict(calls)
                    item["requests"] = dict(requests)
            finally:
                local.close()
                fixture.close()
        for locale, javascript in (("de", False), ("en", True), ("de", True), ("en", False)):
            run_one(locale, javascript)
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(dict(completed=True, measurements=sum(len(r["measurements"]) for r in evidence["runs"]))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    run(parser.parse_args())
