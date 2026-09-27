# ruff: noqa: E501 - Keep optional browser expressions and evidence selectors readable.
"""Bounded #270 independent-Wheel About evidence; fresh disposable cwd only."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, focus, keyboard, tab_to
from verify_recording_entry_settings_navigation import MODULES
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_recording_entry_settings_navigation import (  # noqa: E402
    NAVIGATION,
    TECHNICAL_FILES,
)
from test_session_recorded_review_web import Browser, record_live_game, review_first  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.server as web  # noqa: E402
import skatmind.app_web.stateful_context as stateful  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

SUMMARY = ".storage-disclosure > summary"
GEOMETRY = """(() => {
 const rect=r=>({x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom});
 const box=e=>{const s=getComputedStyle(e);return {tag:e.tagName,id:e.id,classes:e.className,
   ...rect(e.getBoundingClientRect()),client:e.clientWidth,scroll:e.scrollWidth,
   font:s.fontSize,display:s.display,overflowX:s.overflowX,overflowY:s.overflowY,
   wrap:s.overflowWrap,whiteSpace:s.whiteSpace,textOverflow:s.textOverflow,
   columns:s.gridTemplateColumns,padding:s.padding,clip:s.clipPath,lineClamp:s.webkitLineClamp,
   visible:e.checkVisibility(),text:e.textContent}};
 const panels=[...document.querySelectorAll('.about-grid > section')];
 const text=[];
 panels.forEach(panel=>{const walker=document.createTreeWalker(panel,NodeFilter.SHOW_TEXT);
   while(walker.nextNode()) {const n=walker.currentNode;if(!n.textContent.trim()||!n.parentElement.checkVisibility())continue;
     const range=document.createRange();range.selectNodeContents(n);
     text.push({parent:n.parentElement.tagName,text:n.textContent,panel:panel.getAttribute('aria-labelledby'),
       bounds:[...range.getClientRects()].map(rect)});}});
 const summary=document.querySelector('.storage-disclosure > summary'), s=getComputedStyle(summary);
 return {client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
   viewport:{width:innerWidth,height:innerHeight},scrollX,scrollY,height:document.documentElement.scrollHeight,
   open:summary.parentElement.open,main:box(document.querySelector('main')),
   grid:box(document.querySelector('.about-grid')),panels:panels.map(box),
   components:[...document.querySelectorAll('.about-grid h2,.about-grid p,.about-list,.about-list dt,.about-list dd,.storage-disclosure,summary,.about-grid code')].map(box),
   text,marker:{display:s.display,type:s.listStyleType,position:s.listStylePosition,
     content:getComputedStyle(summary,'::marker').content,font:getComputedStyle(summary,'::marker').fontSize},
   filenames:[...document.querySelectorAll('[aria-labelledby="interfaces-heading"] code')].map(e=>e.textContent),
   storage:document.querySelector('.storage-disclosure code').textContent,
   sectionOrder:panels.map(e=>e.getAttribute('aria-labelledby')),
   content:panels.map(e=>({heading:e.querySelector('h2').textContent,
     paragraphs:[...e.querySelectorAll('p')].map(p=>p.textContent),
     facts:[...e.querySelectorAll('dt,dd')].map(d=>d.textContent)})),
   controls:[...document.querySelectorAll('main a,main button,main input,main summary')].map(e=>({tag:e.tagName,text:e.textContent,href:e.getAttribute('href')}))};
})()"""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    assert Path.cwd() != ROOT and args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    # Relative --data-dir values are supported. This is the real configured path,
    # not a shortened renderer value; cwd is a dedicated external disposable root.
    synthetic = Path(args.output.name + "-synthetic") / ("long-storage-name-" * 4 + "&-evidence")
    assert not synthetic.exists()
    evidence = dict(completed=False, phase=args.phase, python=sys.version, platform=platform.platform(),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        wheel=digest(args.wheel.read_bytes()), installed_module=skatmind.__file__,
        versions={n: version(n) for n in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        hashes={}, served={}, measurements=[], actions=[], screenshots=[], responses=[], counts={}, unaffected=[],
        tolerance_css_px=1, configured_root=str(synthetic / "managed"))
    catalogs = load_frontend_translation_catalogs_v1()
    assert tuple(catalogs["de"]) == tuple(catalogs["en"])
    evidence["inventory"] = [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])]
    assert evidence["inventory"] == [67, 119, 1811]
    with ZipFile(args.wheel) as wheel:
        for name in MODULES:
            raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
            assert raw == wheel.read("skatmind/app_web/" + name)
            source = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if args.phase == "after" else
                subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
            assert raw.replace(b"\r\n", b"\n") == source.replace(b"\r\n", b"\n"), name
            evidence["hashes"][name] = digest(raw)
    fixture = localized_server.__wrapped__(synthetic)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp, calls, mode = local.cdp, Counter(), "bootstrap"
    evidence["browser"] = local.version
    evidence["browser_pid"] = local.process.pid
    handler = web.SkatMindAppWebRequestHandlerV1
    send_bytes = handler._send_bytes

    def counted(label, real):
        def call(*a, **kw):
            calls[mode + ":" + label] += 1
            value = real(*a, **kw)
            if label == "profile_save":
                calls[mode + ":profile_" + value.status] += 1
            return value
        return call

    def send(instance, status, raw, **kw):
        evidence["responses"].append(dict(mode=mode, method=instance.command,
            route=instance.path, status=int(status), location=dict(kw.get("extra_headers", ())).get("Location")))
        return send_bytes(instance, status, raw, **kw)

    def action(name, selector, key=None, *, post=False, toggle=False):
        start, previous = len(evidence["responses"]), calls.copy()
        profile_path = server.app_context.frontend_profile.profile_path
        old_profile = profile_path.read_bytes() if profile_path.exists() else None
        if key:
            tab_to(cdp, selector)
        before = focus(cdp)
        if key:
            keyboard(cdp, *key)
        elif selector == SUMMARY:
            # The pre-fix doubled summary extends beyond the viewport. Click its
            # visible native surface instead of the helper's offscreen midpoint.
            point = cdp.evaluate("""(() => {const e=document.querySelector('.storage-disclosure > summary');
                e.scrollIntoView({block:'center',inline:'nearest'});const r=e.getBoundingClientRect();
                return {x:(Math.max(0,r.left)+Math.min(document.documentElement.clientWidth,r.right))/2,
                        y:r.top+Math.min(15,r.height/2)}})()""")
            for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                cdp.call("Input.dispatchMouseEvent", type=kind, **point,
                    **({"button": "left", "clickCount": 1} if kind != "mouseMoved" else {}))
        else:
            click(cdp, selector)
        time.sleep(.6)
        for _ in range(100):
            if cdp.evaluate("document.readyState==='complete'"):
                break
            time.sleep(.1)
        row = dict(name=name, mode=mode, selector=selector, input=key or "pointer",
            locale=cdp.evaluate("document.documentElement.lang"), javascript=not cdp.script_disabled,
            url=cdp.evaluate("location.pathname+location.hash"), before=before, active=focus(cdp),
            calls=dict(calls - previous), responses=evidence["responses"][start:])
        keyboard(cdp, "Tab", "Tab", 9)
        row["next_tab"] = focus(cdp)
        evidence["actions"].append(row)
        posts = [r for r in row["responses"] if r["method"] == "POST"]
        assert len(posts) == int(post), row
        if toggle:
            assert not row["responses"] and not row["calls"], row
        if not post:
            assert (profile_path.read_bytes() if profile_path.exists() else None) == old_profile

    def screenshot(name):
        # Native smooth scrolling can outlive dispatch; measure only at rest.
        previous, stable = None, 0
        for _ in range(50):
            position = cdp.evaluate("[scrollX,scrollY]")
            stable = stable + 1 if position == previous else 0
            if stable == 3:
                break
            previous = position
            time.sleep(.1)
        assert stable == 3
        geometry = cdp.evaluate("({width:innerWidth,height:innerHeight,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,x:scrollX,y:scrollY})")
        cdp.screenshot(args.output / (name + ".png"))
        assert geometry == cdp.evaluate("({width:innerWidth,height:innerHeight,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,x:scrollX,y:scrollY})")
        evidence["screenshots"].append(dict(name=name, **geometry, kind="ordinary viewport"))

    def sweep(name):
        # Native Home/wheel scrolling; no viewport enlargement or full-document image.
        keyboard(cdp, "Home", "Home", 36)
        for index in range(30):
            screenshot(f"{name}-{index:02}")
            old = cdp.evaluate("scrollY")
            cdp.call("Input.dispatchMouseEvent", type="mouseWheel", x=100, y=200,
                deltaX=0, deltaY=cdp.evaluate("innerHeight*.8"))
            time.sleep(.5)
            if cdp.evaluate("scrollY") == old:
                return
        raise AssertionError("Bounded screenshot sweep did not reach footer")

    try:
        with ExitStack() as stack:
            for module, name, label in (
                (session_files, "save_session_file", "session_save"),
                (profile, "save_frontend_profile_file_v1", "profile_save"),
                (execution, "execute", "execution"),
                (web, "discover_managed_items_v1", "discovery"),
                (stateful, "discover_managed_items_v1", "discovery"),
                (web, "open_guided_session_v1", "source_load"),
                (web, "open_unified_match_v1", "source_load")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(handler, "_send_bytes", send))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.navigate(server.origin + "/")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                raw = browser.request("GET", route)[2]
                assert digest(raw) == evidence["hashes"][resource]
                evidence["served"][route] = digest(raw)
            for locale, script in (("de", False), ("en", False), ("de", True), ("en", True)):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                mode = "language"
                action("matrix-language", f'.language-selector button[value="{locale}"]', ("Enter", "Enter", 13, "\r"), post=True)
                for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
                    mode = "navigation"
                    action("footer-about", 'footer a[href="/about"]', ("Enter", "Enter", 13, "\r"))
                    assert not cdp.evaluate("document.querySelector('.storage-disclosure').open")
                    if scale == 2:
                        cdp.evaluate(TEXT_ENLARGEMENT)
                    for opened in (False, True):
                        mode = "toggle"
                        if opened:
                            action("open-storage", SUMMARY, ("Enter", "Enter", 13, "\r"), toggle=True)
                            # Native Shift+Tab returns from footer to summary, preserving focus-visible.
                            cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Tab", code="Tab", windowsVirtualKeyCode=9, modifiers=8)
                            cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Tab", code="Tab", windowsVirtualKeyCode=9, modifiers=8)
                            assert cdp.evaluate("document.activeElement.matches(" + json.dumps(SUMMARY) + ")")
                        mode = "passive"
                        row = cdp.evaluate(GEOMETRY)
                        row.update(locale=locale, javascript=script, width=width, scale=scale, focus=focus(cdp))
                        evidence["measurements"].append(row)
                        assert row["open"] == opened
                        assert row["storage"] == str(server.app_context.managed_home.root)
                        assert row["filenames"] == TECHNICAL_FILES
                        assert row["sectionOrder"] == ["installation-heading", "operation-heading", "interfaces-heading"]
                        assert len(row["controls"]) == 1 and row["controls"][0]["tag"] == "SUMMARY"
                        assert row["marker"]["display"] == "list-item"
                        assert row["marker"]["type"] == ("disclosure-open" if opened else "disclosure-closed")
                        assert cdp.evaluate("[...document.querySelectorAll('.site-nav a')].map(e=>e.getAttribute('href'))") == NAVIGATION
                        assert cdp.evaluate("[...document.querySelectorAll('footer a')].map(e=>e.getAttribute('href'))") == ["/about"]
                        if args.phase == "after":
                            assert row["scroll"] <= row["client"] + 1, row
                            for element in row["panels"] + row["components"]:
                                if element["visible"]:
                                    assert element["right"] <= row["client"] + 1, element
                                    assert element["scroll"] <= element["client"] + 1, element
                                    assert element["overflowX"] == "visible" and element["clip"] == "none", element
                            for text in row["text"]:
                                panel = row["panels"][row["sectionOrder"].index(text["panel"])]
                                for bounds in text["bounds"]:
                                    assert bounds["x"] >= panel["x"] - 1 and bounds["right"] <= panel["right"] + 1, text
                        name = f"about-{locale}-{int(script)}-{width}-{scale}-{'open' if opened else 'closed'}"
                        if opened:
                            assert row["focus"]["visible"] and float(row["focus"]["width"].removesuffix("px")) > 0
                            screenshot(name + "-focus")
                        if (locale, script) in (("de", False), ("en", True)):
                            sweep(name)
                    mode = "toggle"
                    action("close-space", SUMMARY, (" ", "Space", 32, " "), toggle=True)
                    assert not cdp.evaluate("document.querySelector('.storage-disclosure').open")
                    action("open-pointer", SUMMARY, toggle=True)
                    assert cdp.evaluate("document.querySelector('.storage-disclosure').open")
                    mode = "language"
                    action("same-language", f'.language-selector button[value="{locale}"]', post=True)
                    assert cdp.evaluate("document.querySelector('.storage-disclosure').open") == script
                    action("changed-language", f'.language-selector button[value="{ "en" if locale == "de" else "de" }"]', post=True)
                    assert cdp.evaluate("document.querySelector('.storage-disclosure').open") == script
                    action("restore-language", f'.language-selector button[value="{locale}"]', post=True)
                    mode = "navigation"
                    action("global-home", "a.brand", ("Enter", "Enter", 13, "\r"))
            # Representative unaffected real pages, including Settings' shared description list.
            cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
            for route in ("/", "/settings", "/sessions", "/matches", "/learning"):
                mode = "navigation"
                cdp.navigate(server.origin + route)
                if route == "/settings":
                    action("settings-profile-details", ".secondary-action > summary", ("Enter", "Enter", 13, "\r"), toggle=True)
                evidence["unaffected"].append(cdp.evaluate("""(() => {const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,classes:e.className,width:r.width,height:r.height,client:e.clientWidth,scroll:e.scrollWidth,wrap:s.overflowWrap,font:s.fontSize,columns:s.gridTemplateColumns}};return {route:location.pathname,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,matches:document.querySelectorAll('.about-grid > section,.storage-disclosure summary').length,components:[...document.querySelectorAll('main,.about-list,.about-list dt,.about-list dd,.task-card,.managed-landing,.entry-introduction')].map(box)}})()"""))
                assert evidence["unaffected"][-1]["matches"] == 0
            mode = "fixture"
            record_live_game(browser, play_count=3)
            active = server.app_context.managed_stateful.active_session
            pending = active.operation_feedback.pending
            assert pending is not None
            for route in ("/", "/settings", "/about"):
                browser.page(route)
                assert active.operation_feedback.pending is pending
            review_first(browser)
            result, source, saved = active.execution, active.recorded_review_source, active.path.read_bytes()
            assert result is not None and source is not None
            retained = {n: browser.request("GET", f"/sessions/downloads/{n}.json")[2] for n in ("request", "result")}
            evidence["retained"] = {n: dict(bytes=len(raw), sha256=digest(raw)) for n, raw in {"session": saved, **retained}.items()}
            for n, raw in {"session": saved, **retained}.items():
                (args.output / (n + ".json")).write_bytes(raw)
            for script in (False, True):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                mode = "navigation"
                action("retained-global-settings", '.site-nav a[href="/settings"]', ("Enter", "Enter", 13, "\r"))
                action("retained-footer-about", 'footer a[href="/about"]')
                mode = "language"
                action("retained-language", '.language-selector button[value="de"]', ("Enter", "Enter", 13, "\r"), post=True)
                mode = "retention"
                assert server.app_context.managed_stateful.active_session is active
                assert active.execution is result and active.recorded_review_source is source
                assert active.path.read_bytes() == saved
                assert all(browser.request("GET", f"/sessions/downloads/{n}.json")[2] == raw for n, raw in retained.items())
            if args.baseline:
                old = json.loads(args.baseline.read_text(encoding="utf-8"))
                assert old["completed"] and old["unaffected"] == evidence["unaffected"]
                for before, after in zip(old["measurements"], evidence["measurements"], strict=True):
                    for key in ("locale", "javascript", "width", "scale", "open", "content", "controls", "filenames", "sectionOrder"):
                        assert before[key] == after[key], key
                evidence["comparison"] = "Exact About facts/prose/control/order and unaffected computed geometry; each real configured storage path checked independently. No normalized dynamic HTML comparison."
            assert calls["fixture:execution"] == 1
            assert not any(v for k, v in calls.items() if not k.startswith("fixture:") and k.endswith((":session_save", ":execution", ":source_load")))
            evidence["completed"] = True
    finally:
        evidence["counts"] = dict(calls)
        local.close()
        fixture.close()
        evidence["browser_exit"] = local.process.returncode
        evidence["server_closed"] = True
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: evidence[k] for k in ("completed", "phase", "inventory", "counts", "browser_exit", "server_closed")}, indent=2))


if __name__ == "__main__":
    main()
