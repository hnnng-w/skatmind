# ruff: noqa: E501 - Keep browser measurements and native selectors legible.
"""Focused #277 evidence using disposable source-tree data and isolated Edge profiles.

Uses the existing optional standard-library CDP utility; never part of maintainer UAT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_language_view_continuity import skat_entry  # noqa: E402
from test_match_recording_recovery_web import follow, start_match  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402

TRACE = r"""(() => {
  const trace = window.__viewTrace = [];
  const snapshot = event => {
    const focus = document.activeElement;
    const task = document.getElementById('session-recording') || document.getElementById('match-recording');
    const visible = [...document.querySelectorAll('main [id]')].filter(e => {
      const r=e.getBoundingClientRect(); return r.width && r.height && r.top>=0 && r.top<innerHeight;
    }).slice(0, 6).map(e => ({id:e.id,top:e.getBoundingClientRect().top,text:(e.innerText||e.value||'').slice(0,160)}));
    const reading=[...document.querySelectorAll('main h2,main legend,main label,main summary')].filter(e=>{
      const r=e.getBoundingClientRect();return r.width&&r.height&&r.bottom>0&&r.top<innerHeight;
    }).slice(0,8).map(e=>({tag:e.tagName,text:e.innerText,top:e.getBoundingClientRect().top}));
    return {event, time:performance.now(), ready:document.readyState,y:scrollY,hash:location.hash,
      taskTop:task?.getBoundingClientRect().top,focus:focus?{tag:focus.tagName,id:focus.id,name:focus.name,value:focus.value}:null,visible,reading};
  };
  window.__viewSnapshot = snapshot;
  for(const event of ['DOMContentLoaded','load','scroll','focusin','pageshow'])
    addEventListener(event,()=>trace.push(snapshot(event)));
  const scroll = window.scrollTo.bind(window);
  window.scrollTo = (...args) => {trace.push(snapshot('before-scrollTo'));scroll(...args);trace.push(snapshot('after-scrollTo'));};
  let frames=0;
  const frame=()=>{trace.push(snapshot('frame'));if(++frames<40)requestAnimationFrame(frame)};
  requestAnimationFrame(frame);
})()"""

MEASURE = r"""(() => ({...__viewSnapshot('measurement'),locale:document.documentElement.lang,
  url:location.pathname+location.search+location.hash,
  viewport:{innerWidth,innerHeight,outerWidth,outerHeight,devicePixelRatio,visualScale:visualViewport.scale},
  selected:[...document.querySelectorAll('input[name="cards"]:checked')].map(e=>e.value),
  errors:[...document.querySelectorAll('.error-summary')].map(e=>e.innerText),
  autofocus:document.querySelector('[autofocus]')!==null,
  receipts:document.querySelectorAll('[data-operation-feedback]').length,
  overlayMode:document.documentElement.classList.contains('operation-overlays'),
  meta:document.querySelector('meta[name="language-return"]')!==null}))()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    evidence = {"completed": False, "installation": "source-tree", "python": sys.version,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "changes": subprocess.check_output(["git", "diff", "--stat"], text=True),
        "hashes": {name: hashlib.sha256((ROOT / "src/skatmind/app_web" / name).read_bytes()).hexdigest()
                   for name in ("language_context.py", "language_form_preservation.py", "rendering.py", "server.py", "assets/workflow.js")},
        "cases": [], "limitations": ["Synthetic headless developer evidence; installed-build maintainer acceptance remains open.",
            "The isolated Edge default-zoom preference probe in 277-view-03 remained at devicePixelRatio 1. Actual 200% browser zoom is unverified; narrow resizing below is not zoom evidence."]}
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    browser = Browser(server)
    skat_entry(browser)
    active = server.app_context.managed_stateful.active_session
    accepted = active.path.read_bytes()
    document = active.document
    requests = Counter()
    original_post = Handler.do_POST
    original_get = Handler.do_GET

    def post(handler):
        requests["POST " + handler.path.split("?", 1)[0]] += 1
        return original_post(handler)

    def get(handler):
        requests["GET " + handler.path.split("?", 1)[0]] += 1
        return original_get(handler)

    def enter(cdp):
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter", windowsVirtualKeyCode=13, text="\r")
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter", windowsVirtualKeyCode=13)
        time.sleep(.8)

    try:
        for zoom, width in ((1, 1440), (1, 534)):
            follow(browser, browser.submit(Forms(browser.page()).find(
                "/actions/profile/language"), language="en"))
            profile = args.output / f"edge-{width}"
            default = profile / "Default"
            default.mkdir(parents=True)
            (default / "Preferences").write_text(json.dumps({"partition": {"default_zoom_level": math.log(zoom) / math.log(1.2)}}), encoding="utf-8")
            local = LocalBrowser(args.browser, profile)
            try:
                cdp = local.cdp
                evidence["browser"] = local.version
                window = cdp.call("Browser.getWindowForTarget")
                cdp.call("Browser.setWindowBounds", windowId=window["windowId"], bounds={"width": width, "height": 1000, "windowState": "normal"})
                cdp.call("Page.addScriptToEvaluateOnNewDocument", source=TRACE)
                cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
                time.sleep(.5)
                cdp.navigate(server.origin + "/sessions/current#session-recording")
                metrics = cdp.evaluate(MEASURE)["viewport"]
                assert metrics["devicePixelRatio"] == zoom and metrics["visualScale"] == 1, metrics

                def switch_case(name, locale, *, scrolled, retained=False, route="/sessions/current", target="session-recording", cdp=cdp, zoom=zoom, width=width):
                    cdp.navigate(server.origin + "/about")
                    cdp.navigate(server.origin + route + "#" + target)
                    if not retained and route == "/sessions/current":
                        # A native checkbox click edits only the unsent form.
                        cdp.evaluate("(()=>{const e=document.querySelector('input[name=cards][value=H7]');if(!e.checked)e.click()})()")
                    # Focus the native language control, then deliberately view other
                    # content while retaining keyboard focus, as after user scrolling.
                    cdp.evaluate("document.querySelector('.language-selector button[value=" + locale + "]').focus()")
                    cdp.evaluate("window.scrollTo(0," + ("document.getElementById('" + target + "').getBoundingClientRect().top+scrollY+180" if scrolled else "0") + ")")
                    before = cdp.evaluate(MEASURE)
                    cdp.screenshot(args.output / f"{width}-{name}-before.png")
                    request_start = requests.copy()
                    with (patch.object(Handler, "do_POST", post), patch.object(Handler, "do_GET", get),
                          patch.object(session_files, "save_session_file", wraps=session_files.save_session_file) as saves,
                          patch.object(execution, "execute", wraps=execution.execute) as analyses):
                        enter(cdp)
                    after = cdp.evaluate(MEASURE)
                    trace = cdp.evaluate("__viewTrace")
                    cdp.screenshot(args.output / f"{width}-{name}-after.png")
                    row = {"case": name, "zoom": zoom, "before": before, "after": after, "trace": trace,
                           "requests": dict(requests - request_start), "product_saves": saves.call_count,
                           "analyses": analyses.call_count}
                    evidence["cases"].append(row)
                    assert after["locale"] == locale and after["url"] == route
                    assert after["focus"]["name"] == "language" and after["focus"]["value"] == locale
                    assert after["receipts"] == 0 and not after["autofocus"] and not after["meta"]
                    assert {key: value for key, value in row["requests"].items() if key.startswith("POST")} == {"POST /actions/profile/language": 1}
                    assert saves.call_count == analyses.call_count == 0
                    assert after["selected"] == before["selected"]
                    assert active.document is document and active.path.read_bytes() == accepted
                    frames = [sample for sample in trace if sample["event"] == "frame" and sample.get("taskTop") is not None]
                    assert frames and all(abs(sample["y"] - after["y"]) < 1 for sample in frames), row
                    scrolls = [sample for sample in trace if sample["event"] == "after-scrollTo"]
                    assert len(scrolls) == 1
                    assert after["overlayMode"]
                    if not scrolled:
                        assert after["y"] == 0
                    else:
                        assert after["y"] > 0
                        shared = [(old, new) for old in before["visible"] for new in after["visible"] if old["id"] == new["id"]]
                        assert (shared and min(abs(old["top"] - new["top"]) for old, new in shared) <= 2
                                or abs(before["taskTop"] - after["taskTop"]) <= 2)

                switch_case("pending-top-to-de", "de", scrolled=False)
                switch_case("pending-scrolled-to-en", "en", scrolled=True)
                # Actual rejected synthetic request, kept in the real server feedback store.
                page = browser.page()
                assert browser.submit(Forms(page).find("/sessions/cards"), cards=["H7", "H7"])[0] == 400
                switch_case("retained-scrolled-to-de", "de", scrolled=True, retained=True)
                switch_case("retained-top-to-en", "en", scrolled=False, retained=True)
                cdp.activate(".error-summary a[href^='#']")
                explicit = cdp.evaluate(MEASURE)
                assert "#" in explicit["url"] and explicit["y"] > 0
                evidence["cases"].append({"case": "explicit-error-link", "zoom": zoom, "after": explicit})
                # Reload and history must not replay the old presentation instruction.
                cdp.call("Page.reload")
                time.sleep(.5)
                assert not cdp.evaluate("__viewTrace.some(e=>e.event==='after-scrollTo')")
                refreshed = cdp.evaluate(MEASURE)
                cdp.navigate(server.origin + "/about")
                history = cdp.call("Page.getNavigationHistory")
                cdp.call("Page.navigateToHistoryEntry", entryId=history["entries"][history["currentIndex"] - 1]["id"])
                time.sleep(.5)
                assert not cdp.evaluate("__viewTrace.some(e=>e.event==='after-scrollTo')")
                evidence["cases"].append({"case": "refresh-and-history", "zoom": zoom,
                    "refresh": refreshed, "history": cdp.evaluate(MEASURE), "restoration_replayed": False})
                if width == 1440:
                    start_match(browser)
                    switch_case("shared-match-scrolled-to-de", "de", scrolled=True,
                                route="/matches/position/1", target="match-recording")
                    cdp.call("Emulation.setScriptExecutionDisabled", value=True)
                    cdp.navigate(server.origin + "/sessions/current#session-recording")
                    cdp.activate('.language-selector button[value="en"]')
                    native = cdp.evaluate("({url:location.pathname+location.search+location.hash,locale:document.documentElement.lang,autofocus:!!document.querySelector('[autofocus]'),selected:[...document.querySelectorAll('input[name=cards]:checked')].map(e=>e.value)})")
                    assert native["url"] == "/sessions/current" and native["locale"] == "en" and not native["autofocus"]
                    evidence["cases"].append({"case": "native-fallback", "after": native})
                evidence["accepted_session_unchanged"] = active.document is document and active.path.read_bytes() == accepted
            finally:
                local.close()
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        fixture.close()
    print(json.dumps({"completed": True, "cases": len(evidence["cases"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
