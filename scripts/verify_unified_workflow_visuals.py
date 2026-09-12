# ruff: noqa: E501 - Keep browser expressions and native selectors legible.
"""Optional real-server browser evidence; see docs/unified_workflow_visual_contract.md.

Run separately from check.ps1. Requires the existing dev environment and a caller-
supplied local Edge/Chromium executable. All Product data is synthetic and temporary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from _workflow_visual_browser import LocalBrowser

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import (  # noqa: E402
    Browser,
    Forms,
    entry_action,
    follow,
    operation_form,
    start_match,
    synthetic_cards,
)
from test_session_recorded_review_web import record_live_game, review_first  # noqa: E402

import skatmind  # noqa: E402
from skatmind.capture_web.server import (  # noqa: E402
    serve_match_capture_web_in_thread_v1,
    start_match_capture_web_server_v1,
)
from skatmind.corpus_web.server import (  # noqa: E402
    serve_learning_corpus_web_in_thread_v1,
    start_learning_corpus_web_server_v1,
)

METRICS = r"""(() => {
  const style = e => getComputedStyle(e);
  const rgba = s => (s.match(/[\d.]+/g) || []).map(Number);
  const over = (a,b) => [...a.slice(0,3).map((v,i)=>v*(a[3]??1)+b[i]*(1-(a[3]??1))),1];
  const luminance = c => c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4)
    .reduce((v,x,i)=>v+x*[.2126,.7152,.0722][i],0);
  const ratio = (a,b) => {const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
  function background(e) {
    if (!e) return [255,255,255,1];
    const c=rgba(style(e).backgroundColor);
    return c[3]===1 ? c : over(c,background(e.parentElement));
  }
  const visible=e=>e.checkVisibility({checkVisibilityCSS:true}) && e.getBoundingClientRect().width>0;
  const identity=e=>({tag:e.tagName,id:e.id,name:e.getAttribute('name'),class:e.className});
  const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,width:r.width,right:r.right,height:r.height}};
  const elements=[...document.querySelectorAll('main,main *')].filter(visible);
  const text=elements.filter(e=>([...e.childNodes].some(n=>n.nodeType===3 && n.textContent.trim())
    || e.matches('input:not([type=hidden],[type=checkbox],[type=radio]),textarea,select'))
    && !['OPTION','SCRIPT','STYLE'].includes(e.tagName));
  const pairs=text.map(e=>{const s=style(e),bg=background(e),fg=over(rgba(s.color),bg);
    const large=parseFloat(s.fontSize)>=24 || (parseFloat(s.fontSize)>=18.6667 && +s.fontWeight>=700);
    return {...identity(e),foreground:fg,background:bg,ratio:ratio(fg,bg),size:s.fontSize,
      required:large?3:4.5,inactive:e.matches(':disabled'),opacity:s.opacity};});
  const unique=[...new Map(pairs.map(p=>[JSON.stringify([p.foreground,p.background,p.required,p.inactive]),p])).values()];
  const controls=elements.filter(e=>e.matches('input:not([type=hidden]),select,button,textarea'));
  const visuals=controls.filter(e=>!e.disabled && !e.matches('[type=checkbox],[type=radio]')).map(e=>{
    const s=style(e),border=over(rgba(s.borderTopColor),background(e.parentElement));
    return {...identity(e),border:s.borderTopColor,inside:ratio(border,background(e)),
      outside:ratio(border,background(e.parentElement)),width:parseFloat(s.borderTopWidth)};});
  const focus=[...document.querySelectorAll(':focus-visible')].filter(e=>e.matches('button,a,input,select,textarea,.workflow-table-scroll'))
    .map(e=>({...identity(e),outline:style(e).outlineColor,adjacent:background(e.parentElement),
      ratio:ratio(over(rgba(style(e).outlineColor),background(e.parentElement)),background(e.parentElement))}));
  return {viewport:[innerWidth,innerHeight],clientWidth:document.documentElement.clientWidth,
    pageWidth:document.documentElement.scrollWidth,lang:document.documentElement.lang,
    stylesheets:[...document.styleSheets].map(s=>new URL(s.href).pathname),
    overflow:elements.filter(e=>!e.closest('.workflow-table-scroll') && box(e).right>document.documentElement.clientWidth+1)
      .map(e=>({...identity(e),...box(e),minWidth:style(e).minWidth,columns:style(e).gridTemplateColumns})),
    pairs:unique,contrastFailures:unique.filter(p=>!p.inactive && p.ratio<p.required),
    gradients:elements.filter(e=>style(e).backgroundImage!=='none').map(identity),
    tiles:[...document.querySelectorAll('a.position-card, a.match-tile')].map(e=>({...box(e),
      columns:style(e).gridTemplateColumns,participantWidth:e.querySelector('small, .match-tile-participants')?.getBoundingClientRect().width,
      selected:e.getAttribute('aria-current'),status:e.dataset.status})),
    visuals:[...new Map(visuals.map(v=>[JSON.stringify([v.border,v.inside,v.outside]),v])).values()],
    visualFailures:visuals.filter(v=>v.width>0 && v.outside<3),
    controlCount:controls.length,
    focus,
    tables:[...document.querySelectorAll('.workflow-table-scroll')].filter(visible).map(e=>({
      ...box(e),scrollWidth:e.scrollWidth,clientWidth:e.clientWidth,label:e.getAttribute('aria-label'),tabindex:e.tabIndex})),
    nativeValueScroll:controls.filter(e=>e.matches('input:not([type=file]),select') && e.scrollWidth>e.clientWidth+1).map(identity),
    clipped:elements.filter(e=>!e.matches('input:not([type=file]),select') && ['hidden','clip'].includes(style(e).overflowX) && e.scrollWidth>e.clientWidth+1).map(identity)
  };
})()"""

TEXT_ENLARGEMENT = """(() => {
  const entries=[...document.querySelectorAll('body, body *')].map(e=>[e,getComputedStyle(e).fontSize]);
  entries.forEach(([e,size])=>e.style.fontSize=(parseFloat(size)*2)+'px');
})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline", type=Path, help="Earlier sanitized evidence.json to compare")
    parser.add_argument("--expect-installed", action="store_true",
                        help="Require the application to load outside the source checkout")
    args = parser.parse_args()
    if not args.browser.is_file() or not args.output.parent.is_dir():
        parser.error("Browser and output parent must already exist.")
    args.output.mkdir(exist_ok=True)
    installed = not Path(skatmind.__file__).resolve().is_relative_to(REPOSITORY)
    if args.expect_installed and not installed:
        parser.error("Use the isolated installed Wheel interpreter for --expect-installed.")
    evidence = {"phase": args.phase, "commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip(),
        "zoom": 1, "resource_mode": "installed" if installed else "source/editable",
        "pages": [], "actions": []}
    evidence["resource_hashes"] = {name: hashlib.sha256((REPOSITORY / name).read_bytes()).hexdigest()
        for name in ("src/skatmind/app_web/assets/app.css", "src/skatmind/app_web/templates/app.html",
                     "src/skatmind/capture_web/assets/capture.css", "src/skatmind/corpus_web/assets/corpus.css")}
    for name, digest in evidence["resource_hashes"].items():
        parts = Path(name).parts
        content = importlib.resources.files(".".join(parts[1:3])).joinpath(*parts[3:]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == digest
    with tempfile.TemporaryDirectory(prefix="workflow-visual-") as temp:
        fixture = localized_server.__wrapped__(Path(temp))
        server = next(fixture)
        client = Browser(server)
        browser = LocalBrowser(args.browser, Path(temp) / "browser")
        cdp = browser.cdp
        evidence["browser"] = browser.version
        cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0],
                 value=client.cookie.split("=", 1)[1], url=server.origin,
                 httpOnly=True, sameSite="Strict")
        try:
            def capture(name, route, anchor, *, extended=False):
                for locale in ("de", "en"):
                    page = client.page(route)
                    follow(client, client.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
                    for width, height in ((1365, 900), (390, 844), (320, 800), (768, 1024)):
                        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                                 deviceScaleFactor=1, mobile=False)
                        cdp.navigate(server.origin + route)
                        for opened in (False, True):
                            cdp.evaluate("document.querySelectorAll('details').forEach(d=>d.open="
                                         + str(opened).lower() + ")")
                            result = cdp.evaluate(METRICS)
                            result.update(state=name, opened=opened, text_scale=1,
                                          javascript=not cdp.script_disabled)
                            evidence["pages"].append(result)
                            if locale == "de" and width in (390, 1365) and opened:
                                stem = f"{name}-{locale}-{width}"
                                cdp.screenshot(args.output / f"{stem}-whole.png", whole=True)
                                cdp.evaluate(f"document.querySelector({json.dumps(anchor)}).scrollIntoView()")
                                cdp.screenshot(args.output / f"{stem}-area.png")
                            print(name, locale, width, opened, result["pageWidth"],
                                  len(result["contrastFailures"]), flush=True)
                            if args.phase == "after":
                                assert result["stylesheets"] == ["/assets/app.css"]
                                assert result["pageWidth"] <= result["clientWidth"]
                                assert not result["contrastFailures"] and not result["clipped"]
                                assert not result["visualFailures"]
                        if extended and width in (320, 768):
                            cdp.evaluate(TEXT_ENLARGEMENT)
                            result = cdp.evaluate(METRICS)
                            result.update(state=name, opened=True, text_scale=2,
                                          javascript=not cdp.script_disabled)
                            evidence["pages"].append(result)
                            print(name, locale, width, "200%", result["pageWidth"], flush=True)
                            cdp.evaluate(f"document.querySelector({json.dumps(anchor)}).scrollIntoView()")
                            cdp.screenshot(args.output / f"{name}-{locale}-{width}-text200.png")
                            assert result["pageWidth"] <= result["clientWidth"]
                            assert not result["contrastFailures"] and not result["clipped"]
                            for table in result["tables"]:
                                if table["scrollWidth"] > table["clientWidth"]:
                                    cdp.evaluate("document.querySelector('.workflow-table-scroll').focus()")
                                    cdp.call("Input.dispatchKeyEvent", type="keyDown", key="ArrowRight", code="ArrowRight", windowsVirtualKeyCode=39)
                                    cdp.call("Input.dispatchKeyEvent", type="keyUp", key="ArrowRight", code="ArrowRight", windowsVirtualKeyCode=39)
                                    time.sleep(.2)
                                    assert cdp.evaluate("document.querySelector('.workflow-table-scroll').scrollLeft") > 0
                                    evidence["table_keyboard_scroll_verified"] = True

            def activate(selector):
                cdp.events.clear()
                cdp.activate(selector)
                fragment = cdp.evaluate("location.hash")
                posts = [event["params"]["request"] for event in cdp.events
                         if event["params"]["request"]["method"] == "POST"]
                # Deliberately retain only paths, never cookies, tokens or form values.
                paths = [request["url"].removeprefix(server.origin) for request in posts]
                evidence["actions"].append({"post_paths": paths,
                    "javascript": not cdp.script_disabled,
                    "locale": cdp.evaluate("document.documentElement.lang"),
                    "fragment": fragment})
                assert len(paths) == 1

            def native_language(route, field, value, *, expected_fragment=None):
                cdp.call("Emulation.setScriptExecutionDisabled", value=False)
                cdp.navigate(server.origin + route)
                cdp.evaluate(f"document.querySelector({json.dumps(field)}).value={json.dumps(value)};"
                             "document.querySelectorAll('details').forEach(d=>d.open=true)")
                for locale in ("de", "en"):
                    activate(f'.language-selector button[value="{locale}"]')
                    assert evidence["actions"][-1]["post_paths"] == ["/actions/profile/language"]
                    assert cdp.evaluate("document.documentElement.lang") == locale
                    assert cdp.evaluate(f"document.querySelector({json.dumps(field)}).value") == value
                    assert cdp.evaluate("[...document.querySelectorAll('details')].every(d=>d.open)")
                    if expected_fragment:
                        assert cdp.evaluate("location.hash") == expected_fragment

            def control_states(name, route):
                cdp.navigate(server.origin + route)
                cdp.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
                selectors = ('main button.primary:enabled', 'main button.secondary:enabled',
                    'main form:has([value=clear_position]) button', 'main button:disabled',
                    'main select', 'main input[type=file]', '.match-tile[aria-current=page]',
                    '.workflow-table-scroll', '.language-selector button[aria-pressed=true]')
                for selector in selectors:
                    if not cdp.evaluate(f"!!document.querySelector({json.dumps(selector)})"):
                        continue
                    point = cdp.evaluate(f"(()=>{{const e=document.querySelector({json.dumps(selector)});"
                        "e.scrollIntoView({block:'center'});e.focus();const r=e.getBoundingClientRect();"
                        "return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                    cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Shift", code="ShiftLeft")
                    cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Shift", code="ShiftLeft")
                    focus = cdp.evaluate(f"(()=>{{const e=document.querySelector({json.dumps(selector)}),s=getComputedStyle(e);"
                        "return {focused:e===document.activeElement,visible:e.matches(':focus-visible'),"
                        "outline:s.outlineColor,width:s.outlineWidth,offset:s.outlineOffset,"
                        "color:s.color,background:s.backgroundColor,disabled:e.disabled??false}})()")
                    cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
                    hover = cdp.evaluate(METRICS)
                    evidence.setdefault("control_states", []).append({"state": name,
                        "selector": selector, "focus": focus, "focus_pairs": hover["focus"],
                        "hover_pairs": hover["pairs"]})
                    if not focus["disabled"]:
                        assert focus["focused"] and focus["visible"] and float(focus["width"][:-2]) >= 2
                        assert all(pair["ratio"] >= 3 for pair in hover["focus"])
                    assert not hover["contrastFailures"]
                    if selector == "main select":
                        original = cdp.evaluate("document.activeElement.value")
                        for key in ("ArrowDown", "ArrowUp"):
                            key_code = 40 if key == "ArrowDown" else 38
                            cdp.call("Input.dispatchKeyEvent", type="keyDown", key=key, code=key, windowsVirtualKeyCode=key_code)
                            cdp.call("Input.dispatchKeyEvent", type="keyUp", key=key, code=key, windowsVirtualKeyCode=key_code)
                        # Restore only the unsent presentation if the first option was at an edge.
                        cdp.evaluate("document.activeElement.value=" + json.dumps(original))
                    cdp.screenshot(args.output / f"{name}-control-{selectors.index(selector)}.png")

            page = client.page("/learning")
            follow(client, client.submit(Forms(page).find("/learning/create"),
                                         collection_name="Synthetic Learning Collection"))
            capture("learning-empty", "/learning/current", "#task-first-learning",
                    extended=args.phase == "after")
            page = start_match(client, name="Alexandra-Maria von Hohenlohe-Schillingsfuerst")
            for card in ("SA", "H7", "S7", "CA", "S8", "HA"):
                page = follow(client, client.submit(operation_form(page, "append_plays"), cards=card))
            capture("match-warning-settings", "/matches/position/1",
                    'form[action="/matches/transfer-workspace"]', extended=args.phase == "after")
            page = client.page("/matches/position/1")
            page = follow(client, client.submit(entry_action(page, 2)))
            follow(client, client.submit(Forms(page).find("/matches/recovery/preview"), card="S9"))
            capture("match-preview", "/matches/position/1", "#match-recovery")
            page = client.page("/matches/position/1")
            follow(client, client.submit(Forms(page).find("/matches/recovery/apply"), confirm_apply="on"))
            page = client.page("/matches/position/1")
            follow(client, client.submit(Forms(page).find("/matches/transfer-workspace")))
            page = client.page("/learning/current")
            follow(client, client.submit(operation_form(page, "prepare_learning_artifacts")))
            capture("learning-prepared", "/learning/current", "#task-first-learning")
            if args.phase == "after":
                match = server.app_context.managed_stateful.active_match
                learning = server.app_context.managed_stateful.active_learning
                match_bytes = match.path.read_bytes()
                prepared = learning.corpus.prepared_artifacts
                native_language("/learning/current", '[name="dataset_id"]', "Unsent safe dataset")
                assert learning.corpus.prepared_artifacts is prepared
                native_language("/matches/position/1", '[name="source_title"]', "Unsent safe source")
                assert match.path.read_bytes() == match_bytes
                # Real native no-JavaScript replacement, continued Card entry and rewind.
                cdp.call("Emulation.setScriptExecutionDisabled", value=True)
                cdp.navigate(server.origin + "/matches/position/1")
                activate('#match-play-2 form[action="/matches/recovery/select"] button')
                cdp.evaluate("document.querySelector('[name=card]').value='SK'")
                activate('form[action="/matches/recovery/preview"] button')
                capture("match-native-preview", "/matches/position/1", "#match-recovery")
                cdp.evaluate("document.querySelector('[name=confirm_apply]').checked=true")
                revision = match.workspace.revision
                activate('form[action="/matches/recovery/apply"] button')
                assert match.workspace.revision == revision + 1
                assert match.workspace.slots[0].observed_game.plays[1].card == "SK"
                cdp.evaluate("document.querySelector('#match-recording [name=cards]').value="
                             + json.dumps(synthetic_cards()[6]))
                activate('#match-recording form:has([name=operation][value=append_plays]) button')
                assert len(match.workspace.slots[0].observed_game.plays) == 7
                # Submit a genuine duplicate through the existing secondary recording form.
                cdp.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true);"
                    "document.querySelector('form:has([name=operation][value=append_plays]) input[name=cards]')"
                    ".value='SA'")
                activate('form:has(input[name=cards]):has([name=operation][value=append_plays]) button')
                assert cdp.evaluate("!!document.querySelector('.error-summary')")
                assert len(match.workspace.slots[0].observed_game.plays) == 7
                capture("match-error", "/matches/position/1", ".error-summary", extended=True)
                cdp.navigate(server.origin + "/matches/position/1")
                activate('#match-play-7 form[action="/matches/recovery/select"]:last-child button')
                capture("match-rewind", "/matches/position/1", "#match-recovery", extended=True)
                cdp.evaluate("document.querySelector('[name=confirm_apply]').checked=true")
                activate('form[action="/matches/recovery/apply"] button')
                assert len(match.workspace.slots[0].observed_game.plays) == 6
                # Return Play 2 to the legal fixture; complete only once, reusing this state.
                page = client.page("/matches/position/1")
                page = follow(client, client.submit(entry_action(page, 2)))
                page = follow(client, client.submit(Forms(page).find("/matches/recovery/preview"), card="S9"))
                page = follow(client, client.submit(Forms(page).find("/matches/recovery/apply"), confirm_apply="on"))
                for card in synthetic_cards()[6:]:
                    page = follow(client, client.submit(operation_form(page, "append_plays"), cards=card))
                # Long realistic labels exercise layout; generated IDs stay out of evidence.
                long_name = ("Alexandra-Maria von Hohenlohe-Schillingsfuerst " * 3)[:120]
                page = follow(client, client.submit(operation_form(page, "update_match_metadata"),
                    player_1_label=long_name.strip(),
                    player_2_label=("Boris Alexander de la Cruz " * 4).strip(),
                    player_3_label=("Clara Elisabeth von Linden " * 4).strip()))
                page = client.page("/matches/position/2")
                follow(client, client.submit(operation_form(page, "mark_passed_deal")))
                capture("match-mixed-next-selected", "/matches/position/3", ".round-slots", extended=True)
                capture("match-mixed-different", "/matches/position/1", ".round-slots")
                page = client.page("/matches/position/3")
                follow(client, client.submit(operation_form(page, "start_game")))
                capture("match-declaration", "/matches/position/3", "#match-recording")
                # Complete observed trace supports real Decision analysis without invented hands.
                page = client.page("/matches/position/1")
                page = follow(client, client.submit(operation_form(page, "analyze_decision"),
                    decision_index="1", immediate_sample_count="4", use_profile_presets="true"))
                report_id = match.capture.report_store.list()[-1].report_id
                report_route = f"/matches/reports/{report_id}"
                capture("match-report", report_route, ".workflow-table-scroll", extended=True)
                control_states("match-report", report_route)
                before_report = client.request("GET", f"/matches/api/v1/reports/{report_id}.json")[2]
                native_language(report_route, '[name="source_title"]', "Unsent Report source")
                assert client.request("GET", f"/matches/api/v1/reports/{report_id}.json")[2] == before_report
                cdp.call("Emulation.setScriptExecutionDisabled", value=True)
                cdp.navigate(server.origin + "/matches/position/1")
                activate('form[action="/matches/transfer-workspace"] button')
                cdp.navigate(server.origin + report_route)
                cdp.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true)")
                activate('form[action="/matches/transfer-report"] button')
                capture("learning-selected-versions", "/learning/current", "#insight-versions", extended=True)
                cdp.navigate(server.origin + "/learning/current")
                activate('form:has([value="prepare_learning_artifacts"]) button')
                assert learning.corpus.prepared_artifacts is not None
                capture("learning-native-prepared", "/learning/current", "#task-first-learning", extended=True)
                control_states("learning-prepared", "/learning/current")
                downloads = cdp.evaluate("[...document.querySelectorAll('a[download]')].map(a=>a.pathname)")
                assert len(downloads) == 10
                downloads_dir = Path(temp) / "downloads"
                downloads_dir.mkdir()
                cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(downloads_dir))
                cdp.activate('a[download]')
                for _ in range(100):
                    completed_downloads = list(downloads_dir.glob("*.json"))
                    if completed_downloads:
                        break
                    time.sleep(.1)
                assert len(completed_downloads) == 1
                for route in downloads:
                    status, headers, content = client.request("GET", route)
                    assert status == 200 and json.loads(content)
                    evidence.setdefault("downloads", []).append({"route": route,
                        "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
                    if route == downloads[0]:
                        assert completed_downloads[0].read_bytes() == content
                evidence["native_download_matches_retained_bytes"] = True
                # Real preparation rejection leaves required controls exposed and Results retained.
                cdp.evaluate("document.querySelectorAll('details').forEach(d=>d.open=true);"
                             "document.querySelector('[name=train_weight]').value='-1'")
                activate('form:has([value="prepare_learning_artifacts"]) button')
                assert cdp.evaluate("!!document.querySelector('.error-summary')")
                capture("learning-error", "/learning/current", ".error-summary", extended=True)
                native_language("/learning/current", '[name=dataset_id]', "Unsent error draft")
                # Move Current by a genuine new Workspace import; retained Teacher becomes non-current.
                page = client.page("/matches/position/4")
                follow(client, client.submit(operation_form(page, "mark_passed_deal")))
                page = client.page("/matches/position/1")
                follow(client, client.submit(Forms(page).find("/matches/transfer-workspace")))
                capture("learning-blocked-source", "/learning/current", "#task-first-learning", extended=True)
                record_live_game(client)
                review_first(client)
                session = server.app_context.managed_stateful.active_session
                exact_result = session.execution.result_json_bytes
                native_language("/sessions/current", '[name="game_id"]', "Unsent Session label",
                                expected_fragment="#session-result")
                assert session.execution.result_json_bytes == exact_result
                for name, route, anchor in (("home", "/", "main"),
                    ("session-result", "/sessions/current", "#session-result")):
                    # Compatibility spot checks use their real shell resource set.
                    cdp.navigate(server.origin + route)
                    cdp.evaluate(f"document.querySelector({json.dumps(anchor)}).scrollIntoView()")
                    cdp.screenshot(args.output / f"{name}-spot.png")
                    evidence.setdefault("compatibility", []).append({"state": name,
                        "stylesheets": cdp.evaluate("[...document.styleSheets].map(s=>new URL(s.href).pathname)")})
                for name, starter, runner, context in (
                    ("capture", start_match_capture_web_server_v1,
                     serve_match_capture_web_in_thread_v1, match.capture),
                    ("corpus", start_learning_corpus_web_server_v1,
                     serve_learning_corpus_web_in_thread_v1, learning.corpus),
                ):
                    standalone = starter(context, port=0, token="synthetic-visual-token")
                    thread = runner(standalone)
                    try:
                        cdp.call("Page.navigate", url=standalone.origin + "/?token=synthetic-visual-token")
                        time.sleep(1)
                        for width, height in ((1365, 900), (390, 844)):
                            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                                     deviceScaleFactor=1, mobile=False)
                            cdp.navigate(standalone.origin + "/")
                            styles = cdp.evaluate("[...document.styleSheets].map(s=>new URL(s.href).pathname)")
                            assert styles == [f"/assets/{name}.css"]
                            cdp.screenshot(args.output / f"standalone-{name}-{width}.png")
                            evidence.setdefault("compatibility", []).append({"state": name,
                                "stylesheets": styles, "viewport": [width, height], "locale": "en"})
                    finally:
                        standalone.shutdown()
                        standalone.server_close()
                        thread.join(timeout=5)
            evidence["completed"] = True
        finally:
            evidence["summary"] = [{"state": page["state"], "locale": page["lang"],
                "viewport": page["viewport"], "opened": page["opened"], "text_scale": page["text_scale"],
                "page_width": page["pageWidth"], "client_width": page["clientWidth"],
                "minimum_text_contrast": min((p["ratio"] for p in page["pairs"] if not p["inactive"]), default=None),
                "minimum_control_boundary": min((p["outside"] for p in page["visuals"]), default=None)}
                for page in evidence["pages"]]
            if args.baseline:
                before = json.loads(args.baseline.read_text(encoding="utf-8"))
                evidence["baseline_comparison"] = []
                for old in before["pages"]:
                    if old["lang"] != "de" or old["viewport"][0] != 390 or not old["opened"]:
                        continue
                    new = next(p for p in evidence["pages"] if p["state"] == old["state"]
                        and p["lang"] == old["lang"] and p["viewport"] == old["viewport"]
                        and p["opened"] and p["text_scale"] == 1)
                    evidence["baseline_comparison"].append({"state": old["state"],
                        "before_width": old["pageWidth"], "after_width": new["pageWidth"],
                        "before_pairs": old["pairs"], "after_pairs": new["pairs"],
                        "before_overflow": old["overflow"], "after_overflow": new["overflow"],
                        "before_tiles": old["tiles"][:3], "after_tiles": new["tiles"][:3]})
            (args.output / "evidence.json").write_text(
                json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
            (args.output / "summary.json").write_text(json.dumps({
                "browser": evidence["browser"]["product"], "commit": evidence["commit"],
                "completed": evidence.get("completed", False),
                "pages": evidence["summary"], "actions": evidence["actions"],
                "comparison": evidence.get("baseline_comparison", []),
                "native_download": evidence.get("native_download_matches_retained_bytes", False),
                "table_keyboard_scroll": evidence.get("table_keyboard_scroll_verified", False),
                "compatibility": evidence.get("compatibility", []),
            }, indent=2) + "\n", encoding="utf-8")
            browser.close()
            try:
                next(fixture)
            except StopIteration:
                pass


if __name__ == "__main__":
    main()
