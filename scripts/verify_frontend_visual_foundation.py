# ruff: noqa: E501 - Keep browser measurement expressions readable.
"""Source-tree visual foundation evidence using disposable HTTP fixtures only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, keyboard, tab_to

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_recording_deletion_web import preview  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402
from test_settings_reset_presentation import CONSENT, populate_profile, saved_sources  # noqa: E402

import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.match_frontend as match_frontend  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    started = time.perf_counter()
    catalogs = load_frontend_translation_catalogs_v1()
    evidence = dict(completed=False, phase=args.phase, python=sys.version, os=platform.platform(),
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        measurements=[], actions=[], payloads=[], resources={}, states=[],
        scope="Source-tree disposable developer checks, not installed UAT. No manual reset executed.",
        zoom="Actual 100% measured by Page.getLayoutMetrics; actual 200% unavailable in headless transport, installed retest pending.")
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    http = Browser(server)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    counts = Counter()
    mode = "fixture"
    real_replace, real_unlink, real_body = os.replace, Path.unlink, Handler._read_body

    def replaced(source, destination):
        if Path(destination).is_relative_to(server.app_context.managed_home.root):
            counts[mode + ":replace"] += 1
        return real_replace(source, destination)

    def unlinked(path, *a, **kw):
        if path.is_relative_to(server.app_context.managed_home.root):
            counts[mode + ":unlink"] += 1
        return real_unlink(path, *a, **kw)

    def body(handler, *a, **kw):
        raw, kind = real_body(handler, *a, **kw)
        evidence["payloads"].append(dict(mode=mode, route=handler.path,
            fields=parse_qsl(raw.decode(), keep_blank_values=True)))
        return raw, kind

    def counted(label, real):
        def call(*a, **kw):
            counts[mode + ":" + label] += 1
            return real(*a, **kw)
        return call

    def action(selector, label, *, pointer=False):
        before, index = counts.copy(), len(evidence["payloads"])
        if pointer:
            click(cdp, selector)
        else:
            tab_to(cdp, selector)
            keyboard(cdp, "Enter", "Enter", 13, "\r")
        time.sleep(.6)
        evidence["actions"].append(dict(name=label, counts=dict(counts-before),
            payloads=evidence["payloads"][index:], focus=cdp.evaluate("({tag:document.activeElement.tagName,name:document.activeElement.name})")))

    def measure(label, *, selector="main", width=1365):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'})")
        time.sleep(.15)
        data = cdp.evaluate("""(()=>{const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,text:e.innerText,x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontSize,family:s.fontFamily,line:s.lineHeight,margin:s.margin,padding:s.padding,color:s.color,background:s.backgroundColor,outline:s.outlineWidth,offset:s.outlineOffset}};
            const root=document.querySelector(""" + json.dumps(selector) + """);return {locale:document.documentElement.lang,viewport:innerWidth,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                body:box(document.body),title:box(document.querySelector('h1')),target:box(root),
                content:[...root.querySelectorAll('h2,h3,p,label,button')].filter(e=>e.checkVisibility()).map(box),
                consents:[...root.querySelectorAll('input[type=checkbox]')].map(e=>({name:e.name,checked:e.checked,required:e.required,width:e.getBoundingClientRect().width})),
                hiddenButtons:[...document.querySelectorAll('button[hidden]')].map(e=>({name:e.name,value:e.value,visible:e.checkVisibility(),height:e.getBoundingClientRect().height})),
                focus:box(document.activeElement)}})()""")
        data.update(name=label, javascript=not cdp.script_disabled,
                    zoom=cdp.call("Page.getLayoutMetrics")["cssVisualViewport"].get("zoom"))
        evidence["measurements"].append(data)
        cdp.screenshot(args.output / (label + ".png"))
        assert data["zoom"] == 1
        assert all(not b["visible"] and b["height"] == 0 for b in data["hiddenButtons"])
        if args.phase == "after":
            assert data["client"] == data["scroll"], label
            assert data["body"]["font"] == "16px" and data["title"]["font"] == "28px"
            assert data["body"]["family"].startswith("system-ui")
            assert all(e["height"] >= 44 for e in data["content"] if e["tag"] == "BUTTON")
        return data

    def control_states(selector, label):
        """Native focus and pointer states; release outside to avoid an operation."""
        index, before = len(evidence["payloads"]), counts.copy()
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'center'})")
        point = cdp.evaluate("(()=>{const r=document.querySelector(" + json.dumps(selector) + ").getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")

        def capture(state):
            data = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + "),s=getComputedStyle(e),r=e.getBoundingClientRect();return {font:s.fontSize,height:r.height,color:s.color,background:s.backgroundColor,border:s.borderColor,outline:s.outlineWidth,offset:s.outlineOffset,focus:e.matches(':focus-visible'),disabled:e.disabled,visible:e.checkVisibility()}})()")
            evidence["states"].append(dict(control=label, state=state, **data))
            cdp.screenshot(args.output / (label + "-" + state + ".png"))
            assert data["visible"]
            if args.phase == "after":
                assert data["height"] >= 44 and data["font"] == "16px"
            return data

        capture("normal")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        capture("hover")
        if not cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").disabled"):
            cdp.call("Input.dispatchMouseEvent", type="mousePressed", button="left", clickCount=1, **point)
            capture("active")
            cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=1, y=1)
            cdp.call("Input.dispatchMouseEvent", type="mouseReleased", button="left", clickCount=1, x=1, y=1)
            keyboard(cdp, "Tab", "Tab", 9)
            tab_to(cdp, selector)
            data = capture("focus")
            assert data["focus"] and float(data["outline"].removesuffix("px")) >= 2
        assert len(evidence["payloads"]) == index and counts == before

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(os, "replace", replaced))
            stack.enter_context(patch.object(Path, "unlink", unlinked))
            stack.enter_context(patch.object(Handler, "_read_body", body))
            for module, name in ((execution, "execute"),
                                 (match_frontend, "apply_unified_match_operation_v1"),
                                 (match_frontend, "execute_unified_match_analysis_v1")):
                stack.enter_context(patch.object(module, name, counted(name, getattr(module, name))))
            name, value = http.cookie.split("=", 1)
            cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
            cdp.call("Network.setExtraHTTPHeaders", headers={"Accept-Language": "en"})
            cdp.navigate(server.origin + "/settings")
            mode = "passive"
            measure("empty-settings", selector="main")
            measure("empty-resets", selector='[aria-labelledby="settings-reset-heading"]')
            assert not server.app_context.frontend_profile.profile_path.exists()
            mode = "fixture"
            files, downloads = saved_sources(http)
            populate_profile(http)
            app = server.app_context
            # Real profile edit; long names exercise wrapping without changing recording identities.
            form = Forms(http.page("/settings")).find("/actions/profile/players/edit")
            response = http.submit(form)
            edit_page = http.page(response[1]["location"])
            response = http.submit(Forms(edit_page).find("/actions/profile/players/update"),
                display_name="Alexandra-Maria von Hohenlohe-Schillingsfuerst " * 2)
            assert response[0] == 303
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                raw = http.request("GET", route)[2]
                assert raw == (ROOT / "src/skatmind/app_web" / resource).read_bytes()
                evidence["resources"][route] = hashlib.sha256(raw).hexdigest()
            evidence["csp"] = http.request("GET", "/settings")[1]["content-security-policy"]
            for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                cdp.navigate(server.origin + "/settings")
                mode = "language"
                action('.language-selector button[value="' + locale + '"]', "language-" + locale, pointer=True)
                mode = "passive"
                key = locale + ("-js" if script else "-native")
                before = counts.copy()
                profile_bytes = app.frontend_profile.profile_path.read_bytes()
                for width in ((1365, 390, 320) if locale == "de" else (1365, 390)):
                    measure(key + "-settings-" + str(width), width=width)
                    data = measure(key + "-resets-" + str(width), selector='[aria-labelledby="settings-reset-heading"]', width=width)
                    assert all(not c["checked"] and c["required"] for c in data["consents"])
                for route, consent in CONSENT.items():
                    selector = 'form[action="' + route + '"] button'
                    action(selector, key + "-unchecked-" + consent)
                    assert not evidence["actions"][-1]["payloads"]
                    assert evidence["actions"][-1]["focus"]["name"] == consent
                    measure(key + "-focus-" + consent, selector='form[action="' + route + '"]', width=390)
                for family in ("sessions", "matches"):
                    target = getattr(app.managed_stateful, "active_session" if family == "sessions" else "active_match")
                    preview(http, family, target.handle)
                    cdp.navigate(server.origin + "/recordings/delete")
                    for width in (1365, 390):
                        data = measure(key + "-delete-" + family + "-" + str(width), selector="#recording-deletion", width=width)
                        consent, = data["consents"]
                        assert consent["name"] == "confirm_delete" and not consent["checked"] and consent["required"]
                        if args.phase == "after":
                            assert consent["width"] == 20
                    action('form[action="/recordings/delete/apply"] button', key + "-unchecked-delete-" + family)
                    assert not evidence["actions"][-1]["payloads"]
                    action('form[action="/recordings/delete/cancel"] button', key + "-cancel-" + family, pointer=True)
                    assert evidence["actions"][-1]["payloads"][0]["route"] == "/recordings/delete/cancel"
                    assert app.recording_deletion.pending is None
                assert counts == before
                assert app.frontend_profile.profile_path.read_bytes() == profile_bytes
                assert all(path.read_bytes() == raw for path, raw in files.items())
                assert all(http.request("GET", route)[2] == raw for route, raw in downloads.items())
                if locale == "en" and script:
                    for route, label in (("/", "home"), ("/analyze", "analyze"), ("/review", "review"), ("/matches/new", "match-creation"), ("/matches/position/1", "match-recording"), ("/sessions/current", "session-card")):
                        cdp.navigate(server.origin + route)
                        data = measure(label, width=1365)
                        if label in {"match-creation", "match-recording"}:
                            expected = "setup_action" if label == "match-creation" else "recording_action"
                            assert any(b["name"] == expected for b in data["hiddenButtons"])
                        measure(label + "-narrow", width=390)
                    cdp.navigate(server.origin + "/settings")
                    for selector, label in (
                        ('form[action="/actions/profile/preferences"] button', "primary"),
                        ('.known-player-card:first-child .player-actions form:first-child button', "secondary"),
                        ('form[action="/actions/profile/reset"] button', "destructive"),
                    ):
                        control_states(selector, label)
                    cdp.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
                    measure("forced-colors-resets", selector='[aria-labelledby="settings-reset-heading"]', width=390)
                    cdp.call("Emulation.setEmulatedMedia", features=[])
                    cdp.navigate(server.origin + "/learning/current")
                    selector = 'button[disabled]'
                    summaries = cdp.evaluate("(()=>{let e=document.querySelector('button[disabled]'),a=[];while(e){if(e.tagName==='DETAILS'&&!e.open){const s=e.querySelector('summary');s.id='probe-disabled-'+a.length;a.push('#'+s.id)}e=e.parentElement}return a.reverse()})()")
                    for summary in summaries:
                        click(cdp, summary)
                    control_states(selector, "disabled")
            evidence["counts"] = dict(counts)
            evidence["external_requests"] = [e["params"]["request"]["url"] for e in cdp.events
                if urlsplit(e["params"]["request"]["url"]).scheme in {"http", "https"}
                and not e["params"]["request"]["url"].startswith(server.origin + "/")]
            assert not evidence["external_requests"]
            assert not any(k.startswith("passive:") for k in counts)
            evidence["completed"] = True
    finally:
        local.close()
        fixture.close()
        evidence["seconds"] = round(time.perf_counter() - started, 3)
        (args.output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(dict(completed=True, measurements=len(evidence["measurements"]), seconds=evidence["seconds"])))


if __name__ == "__main__":
    main()
