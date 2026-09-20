# ruff: noqa: E501 - Browser expressions remain legible alongside their measurements.
"""Optional installed-Wheel R08 evidence using synthetic returned forms and native input.

Separate from check.ps1; reuses the existing dependency-free DevTools transport.
See docs/unified_workflow_visual_contract.md. Never use a real Product data root.
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
from test_match_recording_recovery_web import (  # noqa: E402
    Browser,
    Forms,
    follow,
    operation_form,
    start_match,
    synthetic_cards,
)
from test_session_recorded_review_web import (  # noqa: E402
    record_score_review_game,
    score_review_form,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile_operations  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import (  # noqa: E402
    SkatMindAppWebRequestHandlerV1 as Handler,
)

MEASURE = r"""selector => {
  const e=document.querySelector(selector),s=getComputedStyle(e),r=e.getBoundingClientRect();
  const rgba=x=>(x.match(/[\d.]+/g)||[]).map(Number);
  const over=(a,b)=>[...a.slice(0,3).map((v,i)=>v*(a[3]??1)+b[i]*(1-(a[3]??1))),1];
  const bg=n=>!n?[255,255,255,1]:over(rgba(getComputedStyle(n).backgroundColor),bg(n.parentElement));
  const lum=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
  const ancestors=[];for(let n=e;n;n=n.parentElement) ancestors.push({opacity:getComputedStyle(n).opacity,gradient:getComputedStyle(n).backgroundImage});
  const background=bg(e),foreground=over(rgba(s.color),background),adjacent=bg(e.parentElement);
  const range=document.createRange();range.selectNodeContents(e.querySelector('.recorded-review-source')||e);
  const text=range.getBoundingClientRect();
  return {selector,color:s.color,backgroundColor:s.backgroundColor,foreground,background,ratio:ratio(foreground,background),ancestors,
    outline:{style:s.outlineStyle,width:s.outlineWidth,offset:s.outlineOffset,color:s.outlineColor,ratio:ratio(rgba(s.outlineColor),adjacent)},
    visible:e.checkVisibility(),active:e===document.activeElement,documentFocus:document.hasFocus(),focus:e.matches(':focus'),focusVisible:e.matches(':focus-visible'),hover:e.matches(':hover'),pressed:e.matches(':active'),disabled:e.disabled??false,
    box:{x:r.x,y:r.y,width:r.width,height:r.height,right:r.right},textInset:{left:text.left-r.left,top:text.top-r.top},
    padding:s.padding,border:s.border,font:[s.fontSize,s.fontWeight,s.lineHeight],marginBottom:s.marginBottom,
    marker:[s.display,s.listStyleType,s.listStylePosition],client:e.clientWidth,scroll:e.scrollWidth,
    page:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth,
    activeElement:{tag:document.activeElement.tagName,id:document.activeElement.id,href:document.activeElement.getAttribute('href'),name:document.activeElement.name??null}};
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(REPOSITORY)
    args.output.mkdir()
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "installed_module": skatmind.__file__,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPOSITORY, text=True).strip(),
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "hashes": {}, "states": [], "actions": [], "pages": [], "focus": [],
        "limitations": ["Headless browser; synthetic returned-form setup, not maintainer UAT.",
            "Viewport/text/forced-colors are emulated. Native input uses DevTools input dispatch, never element.focus for review returns.",
            "Known #240 comparison-table clipping remains separately recorded; no whole-page accessibility claim."]}
    for name in ("assets/app.css", "assets/workflow.js", "session_recorded_review_rendering.py",
                 "task_first_session_rendering.py", "task_first_match_rendering.py", "result_rendering.py",
                 "validation_rendering.py", "language_context.py", "form_registry.py", "server.py"):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        if args.phase == "after" or name != "assets/app.css":
            assert raw == (REPOSITORY / "src/skatmind/app_web" / name).read_bytes()
        evidence["hashes"][name] = hashlib.sha256(raw).hexdigest()
    calls, requests = Counter(), Counter()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    browser = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = browser.cdp
    evidence["browser"] = browser.version

    def count(name, function):
        def counted(*a, **kw):
            calls[name] += 1
            return function(*a, **kw)
        return counted

    def request_count(function, method):
        def counted(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return function(handler)
        return counted

    def measure(selector):
        return cdp.evaluate("(" + MEASURE + ")(" + json.dumps(selector) + ")")

    def navigate(url):
        # A same-URL fragment navigation can retain inline text enlargement.
        cdp.navigate("about:blank")
        cdp.navigate(url)
        cdp.call("Page.bringToFront")

    def key(name, shift=False):
        code = {"Tab": 9, "Enter": 13, " ": 32}[name]
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=name,
                 code="Space" if name == " " else name, windowsVirtualKeyCode=code,
                 modifiers=8 if shift else 0, **({"text": "\r"} if name == "Enter" else {}))
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=name,
                 code="Space" if name == " " else name, windowsVirtualKeyCode=code,
                 modifiers=8 if shift else 0)

    def tab_to(selector):
        # Traverse the real tab order, rather than manufacturing the target's focus.
        for _ in range(240):
            if cdp.evaluate("document.activeElement===document.querySelector(" + json.dumps(selector) + ")"):
                return
            key("Tab")
        raise AssertionError("Native Tab target not reached: " + selector)

    def point(selector):
        return cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
            + ");e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(r.height/2,20)}})()")

    def mouse(selector, kind="click"):
        p = point(selector)
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **p)
        if kind == "hover":
            return
        cdp.call("Input.dispatchMouseEvent", type="mousePressed", button="left", clickCount=1, **p)
        if kind == "press":
            return
        cdp.call("Input.dispatchMouseEvent", type="mouseReleased", button="left", clickCount=1, **p)

    def action(selector, route=None, pointer=False, activation="Enter"):
        prior, prior_calls = requests.copy(), calls.copy()
        if pointer:
            mouse(selector)
        else:
            tab_to(selector)
            key(activation)
        time.sleep(.7)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (
                route is None or requests["POST " + route] > prior["POST " + route]):
                break
            time.sleep(.1)
        delta = requests - prior
        cdp.call("Page.bringToFront")
        if route:
            assert sum(v for k, v in delta.items() if k.startswith("POST ")) == 1, delta
        else:
            assert not any(k.startswith("POST ") for k in delta), delta
        evidence["actions"].append({"selector": selector, "pointer": pointer,
            "javascript": not cdp.script_disabled, "requests": dict(delta),
            "calls": dict(calls - prior_calls), "fragment": cdp.evaluate("location.hash")})

    def states(name, selector):
        prior_calls, prior_requests = calls.copy(), requests.copy()
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=0, y=0)
        rows = []
        rows.append(("rest", measure(selector)))
        assert rows[0][1]["visible"] and rows[0][1]["box"]["width"] > 0
        mouse(selector, "hover")
        rows.append(("hover", measure(selector)))
        assert rows[-1][1]["hover"]
        if not rows[0][1]["disabled"]:
            tab_to(selector)
            mouse(selector, "hover")
            rows.append(("hover-focus", measure(selector)))
            assert rows[-1][1]["hover"] and rows[-1][1]["focusVisible"]
            cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=0, y=0)
            rows.append(("keyboard-focus", measure(selector)))
            mouse(selector, "press")
            rows.append(("pressed", measure(selector)))
            # Release away from the control so a state measurement never submits it.
            cdp.call("Input.dispatchMouseEvent", type="mouseMoved", x=0, y=0)
            cdp.call("Input.dispatchMouseEvent", type="mouseReleased", button="left", clickCount=1, x=0, y=0)
            key("Tab")
            key("Tab", shift=True)
        for state, row in rows:
            evidence["states"].append({"name": name, "state": state, **row})
            assert all(a["opacity"] == "1" for a in row["ancestors"]), row
            if args.phase == "after" and not row["disabled"]:
                assert row["ratio"] >= 4.5, (name, state, row)
                if row["focusVisible"]:
                    assert row["outline"]["ratio"] >= 3, (name, state, row)
        assert calls == prior_calls and requests == prior_requests

    def screenshot(name, selector):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});window.scrollBy(0,-20)")
        if "hover" in name:
            mouse(selector, "hover")
        cdp.screenshot(args.output / (name + ".png"))

    try:
        with ExitStack() as stack:
            for module, name, label in (
                (execution, "execute", "executions"),
                (session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves"),
            ):
                stack.enter_context(patch.object(module, name, count(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "do_GET", request_count(Handler.do_GET, "GET")))
            stack.enter_context(patch.object(Handler, "do_POST", request_count(Handler.do_POST, "POST")))
            client = Browser(server)
            assert hashlib.sha256(client.request("GET", "/assets/app.css")[2]).hexdigest() == evidence["hashes"]["assets/app.css"]
            record_score_review_game(client, play_count=12)
            selected = score_review_form(client)["values"]["decision_selection"]
            review = 'form[action="/sessions/review-decision"]:has(input[value="' + selected + '"]) button'
            page = start_match(client)
            for card in synthetic_cards()[:6]:
                page = follow(client, client.submit(operation_form(page, "append_plays"), cards=card))
            follow(client, client.submit(Forms(client.page('/learning')).find('/learning/create'), collection_name='Synthetic styling collection'))
            session = server.app_context.managed_stateful.active_session
            match = server.app_context.managed_stateful.active_match
            learning = server.app_context.managed_stateful.active_learning.corpus.store.document
            saved = (session.path.read_bytes(), match.path.read_bytes())
            evidence["setup"] = {"calls": dict(calls), "requests": dict(requests),
                "description": "Returned HTTP forms; 12 legal Session Plays with real Checkpoints, six normal Match Plays, one empty Learning creation for native disabled controls. No injected Result."}
            calls.clear()
            requests.clear()
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
            for disabled in (False, True):
                cdp.call("Emulation.setScriptExecutionDisabled", value=disabled)
                for pointer in (True, False):
                    locale = "de" if pointer else "en"
                    follow(client, client.submit(Forms(client.page()).find('/actions/profile/language'), language=locale))
                    navigate(server.origin + "/sessions/current")
                    if not disabled and pointer:
                        states("saved-review", review)
                        mouse(review, "hover")
                        screenshot("review-hover-1365", review)
                    before = calls["executions"]
                    action(review, "/sessions/review-decision", pointer=pointer)
                    assert calls["executions"] == before + 1
                    result = measure("#session-result")
                    assert result["active"] and cdp.evaluate("location.hash") == "#session-result"
                    if args.phase == "after":
                        assert result["outline"]["style"] == "solid" and result["outline"]["width"] == "2px", result
                        assert result["outline"]["offset"] == "3px" and result["outline"]["ratio"] >= 3
                        assert result["textInset"]["left"] >= 4
                    screenshot(f"result-{int(disabled)}-{int(pointer)}-1365", "#session-result")
                    key("Tab")
                    unfocused = measure("#session-result")
                    next_target = unfocused["activeElement"]
                    assert [unfocused["box"][p] for p in ("width", "height")] == [result["box"][p] for p in ("width", "height")]
                    assert next_target["href"] == "#recorded-decision-12", next_target
                    evidence["focus"].append({"pointer": pointer, "locale": locale, "javascript": not disabled, "result": result, "next": next_target})
            retained = {name: client.request("GET", f"/sessions/downloads/{name}.json")[2] for name in ("request", "result")}
            source = session.recorded_review_source
            evidence["retained"] = {name: hashlib.sha256(raw).hexdigest() for name, raw in retained.items()}
            assert session.execution.result.result.document["score_summary"]["total_declarer_points"] == 14
            assert session.execution.result.result.document["score_summary"]["total_defender_points"] == 29
            # Reuse these accepted sources/results for the bounded responsive matrix.
            for route, target in (("/sessions/current#session-result", "#session-result"), ("/matches/position/1", "#match-metadata > details")):
                for disabled in (False, True):
                    cdp.call("Emulation.setScriptExecutionDisabled", value=disabled)
                    for locale in ("de", "en"):
                        page = client.page(route.split("#")[0])
                        follow(client, client.submit(Forms(page).find("/actions/profile/language"), language=locale))
                        for width, scale in ((1365, 1), (390, 1), (320, 1), (320, 2)):
                            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
                            navigate(server.origin + route)
                            assert cdp.evaluate("document.documentElement.lang") == locale
                            if scale == 2:
                                cdp.evaluate(TEXT_ENLARGEMENT)
                            row = {"route": route, "locale": locale, "javascript": not disabled, "width": width, "text_scale": scale, "target": measure(target)}
                            if "matches" in route:
                                direct = "#task-first-match > details.advanced-settings"
                                wrapped = "#match-metadata > details"
                                row["peers"] = [measure(s) for s in (direct, wrapped, direct + " > summary", wrapped + " > summary")]
                                action(wrapped + " > summary", pointer=True)
                                row["open"] = measure(wrapped + " > summary")
                                if args.phase == "after":
                                    for prop in ("padding", "border", "font"):
                                        assert row["peers"][0][prop] == row["peers"][1][prop], row
                                    for prop in ("font", "marker", "padding"):
                                        assert row["peers"][2][prop] == row["peers"][3][prop], row
                                    assert row["open"]["marginBottom"] == "16px"
                            else:
                                row["context"] = measure(".recorded-decision-context")
                                assert row["context"]["scroll"] <= row["context"]["client"] + 1
                                assert row["target"]["font"][0] == ("32px" if scale == 2 else "16px")
                                row["comparison_table_limitation"] = cdp.evaluate("[...document.querySelectorAll('.result-table-wrap')].map(e=>({section:e.parentElement.clientWidth,wrapper:e.clientWidth,scroll:e.scrollWidth,table:e.querySelector('table').getBoundingClientRect().width,sectionOverflow:getComputedStyle(e.parentElement).overflowX,wrapperOverflow:getComputedStyle(e).overflowX}))")
                                row["review_button"] = measure(review)
                                assert row["review_button"]["scroll"] <= row["review_button"]["client"] + 1
                            evidence["pages"].append(row)
                            if args.phase == "after":
                                assert row["target"]["page"] <= row["target"]["viewport"], row
                                assert row["target"]["box"]["right"] + 5 <= row["target"]["viewport"], row
                            if locale == "de" and not disabled:
                                screenshot(f"{'match' if 'matches' in route else 'result'}-{width}-{scale}", target)
                                if "sessions" in route and width == 320 and scale == 2:
                                    screenshot('comparison-table-320-2', '.result-table-wrap')
                                    mouse(review, "hover")
                                    screenshot('review-hover-320-2', review)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
            cdp.call("Emulation.setScriptExecutionDisabled", value=False)
            navigate(server.origin + "/matches/position/1")
            # Open genuine disclosures by native mouse, then test native Enter/Space.
            for selector in ("#match-metadata > details > summary", "#task-first-match > details:has([value=clear_position]) > summary"):
                action(selector, pointer=True)
            states("nested-secondary", '#match-metadata button')
            states("primary", '#match-recording button.primary')
            states("danger", 'form:has([name=operation][value=clear_position]) button')
            states("metadata-summary", '#match-metadata summary')
            action('#match-metadata summary', activation=" ")
            action('#match-metadata summary', activation="Enter")
            states("selected-language", '.language-selector button[aria-pressed=true]')
            states("other-language", '.language-selector button[aria-pressed=false]')
            states("header-link", '.site-nav a')
            states("footer-link", 'footer a')
            states("ordinary-link", '#match-recording a')
            navigate(server.origin + '/sessions/current')
            action('#session-history > details > summary', pointer=True)
            states("session-nested-secondary", 'form[action="/sessions/reload"] button')
            navigate(server.origin + '/settings')
            states("settings-danger", '.reset-form button')
            navigate(server.origin + "/")
            states("button-link", '.button-link')
            navigate(server.origin + "/learning/current")
            while not cdp.evaluate("document.querySelector('main button:disabled').checkVisibility()"):
                action('details:not([open]):has(button:disabled) > summary', pointer=True)
            states("disabled", 'main button:disabled')
            # Source-safe language switch with safe unsent metadata and exact disclosure state.
            navigate(server.origin + "/matches/position/1")
            action('#match-metadata summary', pointer=True)
            cdp.evaluate("document.querySelector('[name=source_title]').value='Unsent synthetic title'")
            opened = cdp.evaluate("[...document.querySelectorAll('details')].map(e=>e.open)")
            action('.language-selector button[value=de]', '/actions/profile/language', pointer=True)
            assert cdp.evaluate("document.querySelector('[name=source_title]').value") == 'Unsent synthetic title'
            assert cdp.evaluate("[...document.querySelectorAll('details')].map(e=>e.open)") == opened
            # Whitespace satisfies native required but is genuinely rejected as an empty title.
            cdp.evaluate("document.querySelector('#match-metadata [name=title]').value='   '")
            action('#match-metadata button', '/matches/api/v1/operation', pointer=True)
            assert cdp.evaluate("document.activeElement.matches('.error-summary')")
            action('.language-selector button[value=en]', '/actions/profile/language', pointer=True)
            assert cdp.evaluate("document.activeElement.matches('.error-summary')")
            action('.error-summary a', pointer=True)
            evidence['error_field_focus'] = cdp.evaluate("({id:document.activeElement.id,name:document.activeElement.name,open:[...document.querySelectorAll('details')].filter(e=>e.contains(document.activeElement)).every(e=>e.open)})")
            assert evidence['error_field_focus']['open'] and evidence['error_field_focus']['name'] == 'title'
            screenshot('contextual-error', '.error-summary')
            # Preview and cancel only: accepted source and saved bytes remain intact.
            navigate(server.origin + "/matches/position/1")
            action('#match-play-2 form[action="/matches/recovery/select"] button', '/matches/recovery/select', pointer=True)
            cdp.evaluate("document.querySelector('[name=card]').value='SK'")
            action('form[action="/matches/recovery/preview"] button', '/matches/recovery/preview', pointer=True)
            assert cdp.evaluate("document.activeElement.id") == 'match-recovery'
            screenshot('recovery-preview', '#match-recovery')
            action('form[action="/matches/recovery/cancel"] button', '/matches/recovery/cancel')
            evidence['cancel_focus'] = cdp.evaluate("document.activeElement.id")
            assert evidence['cancel_focus'] == 'match-recording'
            # A same-source language return really focuses the retained Result, then emulates forced colors.
            navigate(server.origin + '/sessions/current')
            action('.language-selector button[value=de]', '/actions/profile/language', pointer=True)
            assert cdp.evaluate("document.activeElement.id") == 'session-result'
            cdp.call('Emulation.setEmulatedMedia', features=[{'name':'forced-colors','value':'active'}])
            evidence['forced_colors'] = measure('#session-result')
            if args.phase == 'after':
                assert evidence['forced_colors']['outline']['style'] == 'solid'
                assert evidence['forced_colors']['outline']['ratio'] >= 3
            screenshot('forced-colors-result', '#session-result')
            cdp.call('Emulation.setEmulatedMedia', features=[])
            passive_calls, passive_requests = calls.copy(), requests.copy()
            focused_outline = measure('#session-result')['outline']
            time.sleep(2)
            assert calls == passive_calls and requests == passive_requests
            assert measure('#session-result')['outline'] == focused_outline
            assert (session.path.read_bytes(), match.path.read_bytes()) == saved
            assert server.app_context.managed_stateful.active_learning.corpus.store.document is learning
            assert session.recorded_review_source is source
            for name, raw in retained.items():
                assert client.request('GET', f'/sessions/downloads/{name}.json')[2] == raw
            assert calls['executions'] == 4 and calls['session_saves'] == calls['match_saves'] == 0
            evidence.update(completed=True, calls=dict(calls), requests=dict(requests), passive_zero=True)
    finally:
        (args.output / 'evidence.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
        browser.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({k: evidence[k] for k in ('completed', 'phase', 'registry', 'calls')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
