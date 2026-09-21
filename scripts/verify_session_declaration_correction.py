# ruff: noqa: E501 - Keep browser expressions and evidence selectors legible.
"""Optional #250 independent-Wheel native browser evidence using disposable synthetic roots."""
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
from urllib.parse import parse_qsl

from _workflow_visual_browser import LocalBrowser
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from test_equal_best_immediate import assert_visible_equal_best  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_frontend_result_presentation import assert_summary_points  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND, SESSION_HAND, assert_context  # noqa: E402
from test_recorded_party_presentation import corrected_match_setup  # noqa: E402
from test_session_recorded_review_web import (  # noqa: E402
    Browser,
    Forms,
    record_score_review_game,
    score_review_form,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session as api  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.session_frontend as session_frontend  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

PREFIX = "/sessions/declaration-correction/"
SECTION = "#session-declaration-correction"


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel": digest(args.wheel.read_bytes()),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "hashes": {}, "pages": [], "actions": [], "sources": {},
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "limits": ["Headless Edge, emulated desktop/390/320 and doubled text, not physical-device, AT or maintainer UAT.",
            "Representative state/viewport cells, not every outcome at every width. Existing narrow Result tables are outside this correction slice.",
            "Baseline has direct saves, no Preview/Cancel/removal consent. These absent operations are recorded, not simulated.",
            "Clock, competing Apply and save faults are automated regression tests, not browser fault injections."]}
    modules = ["session_frontend.py", "task_first_session_rendering.py", "compact_declaration_rendering.py",
        "compact_declaration_http.py", "form_registry.py", "server.py", "validation_mapping.py",
        "validation_rendering.py", "language_context.py", "assets/app.css", "assets/workflow.js",
        "locales/en.json", "locales/de.json"]
    if after:
        modules += ["session_declaration_correction.py", "session_declaration_correction_http.py",
                    "session_declaration_correction_rendering.py"]
    for name in modules:
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if after else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, payloads = Counter(), []
    real_read = Handler._read_body

    def read_body(handler, *a, **kw):
        result = real_read(handler, *a, **kw)
        payloads.append({"route": handler.path, "fields": parse_qsl(result[0].decode(), keep_blank_values=True)})
        return result

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapped

    def navigate(path, script):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def click(selector):
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");for(let p=e.tagName==='SUMMARY'?e.parentElement.parentElement:e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)

    def key(name, code):
        for kind in ("keyDown", "keyUp"):
            cdp.call("Input.dispatchKeyEvent", type=kind, key=name, windowsVirtualKeyCode=code)

    def action(selector, route=None, keyboard=False):
        start, work = len(payloads), calls.copy()
        if keyboard:
            cdp.evaluate("(()=>{for(let p=document.querySelector(" + json.dumps(selector)
                + ").parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true})()")
            cdp.activate(selector)
        else:
            click(selector)
        time.sleep(.25 if route else .05)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (route is None or len(payloads) > start):
                break
            time.sleep(.1)
        submitted = payloads[start:]
        assert len(submitted) == int(route is not None), (selector, submitted)
        if route:
            assert submitted[0]["route"] == route
        if route == PREFIX + "apply":
            assert [(k, v) for k, v in submitted[0]["fields"] if k == "confirm_apply"] == [("confirm_apply", "on")]
        if route == "/actions/profile/language":
            for name, value in submitted[0]["fields"]:
                if name == "_frontend_language_values":
                    assert all("confirm_apply" not in row["values"] for row in json.loads(value)["forms"])
        evidence["actions"].append({"selector": selector, "keyboard": keyboard,
            "javascript": not cdp.script_disabled, "submitted": submitted, "calls": dict(calls-work),
            "focus": cdp.evaluate("document.activeElement.id"), "fragment": cdp.evaluate("location.hash")})

    def choose(selector, value):
        start = len(payloads)
        click(selector)
        key("Escape", 27)
        options = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].map(e=>e.value)")
        key("Home", 36)
        for _ in range(options.index(value)):
            key("ArrowDown", 40)
        key("Enter", 13)
        assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").value") == value
        assert len(payloads) == start
        evidence["actions"].append({"native_selection": selector, "value": value, "selection_posts": 0})

    def enter(selector, value):
        start = len(payloads)
        click(selector)
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", windowsVirtualKeyCode=65, modifiers=2)
        key("Backspace", 8)
        if value:
            cdp.call("Input.insertText", text=value)
        assert len(payloads) == start

    def measure(label, selector, locale, script, *, responsive=False):
        source = server.app_context.managed_stateful.active_session
        before, work = source.path.read_bytes(), calls.copy()
        cells = ((1365, 1), (390, 1), (320, 1), (320, 2)) if responsive else ((390, 1),)
        for width, scale in cells:
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844, deviceScaleFactor=1, mobile=False)
            if scale == 2:
                cdp.evaluate(TEXT_ENLARGEMENT)
            cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;e.scrollIntoView({block:'start'});scrollBy(0,-15)})()")
            row = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");return {text:e.innerText,page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,focus:document.activeElement.id,fragment:location.hash,controls:[...e.querySelectorAll('input,select,button')].map(x=>({tag:x.tagName,type:x.type,name:x.name,value:x.value,checked:x.checked,required:x.required,label:x.innerText,preserve:x.form?.dataset.preserveFields}))}})()")
            row.update(label=label, locale=locale, javascript=script, width=width, text_scale=scale)
            evidence["pages"].append(row)
            if after:
                assert row["page"] == row["client"], row
            stem = f"{label}-{locale}-{int(script)}-{width}-{scale}"
            cdp.screenshot(args.output / (stem + ".png"))
            if after and selector == SECTION:
                cdp.evaluate("document.querySelector('#session-declaration-correction .recovery-primary-actions button.primary').scrollIntoView({block:'center'})")
                cdp.screenshot(args.output / (stem + "-actions.png"))
        assert source.path.read_bytes() == before and calls == work
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
        if responsive:
            navigate("/sessions/current", script)

    def editor(kind):
        if after:
            # The accepted-fact entries are separate from the Change proposal control.
            entry = '.accepted-declaration form[action="' + PREFIX + 'select"]'
            selector = entry + (':has(button)' if kind == "set_declarer" else '')
            index = 0 if kind == "set_declarer" else 1
            cdp.evaluate("document.querySelectorAll(" + json.dumps(entry) + ")[" + str(index) + "].id='correction-entry'")
            action("#correction-entry button", PREFIX + "select")
            return 'form[action="' + PREFIX + 'preview"]'
        selector = ('form:has(input[value="session-correction"])' if kind == "set_declaration" else
                    '#session-history form:has(input[name="kind"][value="set_declarer"])')
        if kind == "set_declarer":
            source = server.app_context.managed_stateful.active_session
            record = next(r for r in source.state.command_log if r.command.kind == kind)
            enter(selector + ' input[name="target_revision"]', str(record.revision))
        return selector

    def submit_proposal(selector, *, partial=False, keyboard=False):
        if after:
            action(selector + " button[type=submit]", PREFIX + "preview", keyboard=keyboard)
            assert not cdp.evaluate("!!document.querySelector('form[action=\"" + PREFIX + "preview\"]')")
        else:
            action(selector + " button[type=submit]", "/sessions/command", keyboard=keyboard)

    def apply(partial=False, keyboard=False):
        if partial:
            action('form[action="' + PREFIX + 'apply"] input[name="confirm_apply"]')
        action('form[action="' + PREFIX + 'apply"] button', PREFIX + "apply", keyboard=keyboard)

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "saves"),
                (api, "correct_session_command", "corrections"),
                (session_frontend, "_collect_current_checkpoint", "checkpoint_collections"),
                (execution, "execute", "executions")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read_body))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0],
                value=browser.cookie.split("=", 1)[1], url=server.origin,
                httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"),
                ("/matches/assets/capture.js", "assets/workflow.js")):
                assert digest(browser.request("GET", route)[2]) == evidence["hashes"][resource]
            for script in (True, False):
                for locale in ("de", "en"):
                    plays = record_score_review_game(browser, play_count=0)
                    page = browser.page()
                    follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language=locale))
                    navigate("/sessions/current", script)
                    active = server.app_context.managed_stateful.active_session
                    prefix = f"{locale}-{int(script)}"
                    evidence["sources"][prefix + "-initial"] = digest(active.path.read_bytes())
                    (args.output / (prefix + "-initial.json")).write_bytes(active.path.read_bytes())
                    form = editor("set_declarer")
                    select = form + ' select[name="player_id"]'
                    values = cdp.evaluate("[...document.querySelector(" + json.dumps(select) + ").options].map(x=>x.value)")
                    choose(select, values[1])
                    if after:
                        other = "en" if locale == "de" else "de"
                        action('form.language-selector button[value="' + other + '"]', "/actions/profile/language")
                        assert cdp.evaluate("document.querySelector(" + json.dumps(select) + ").value") == values[int(script)]
                        action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                        choose(select, values[1])
                    measure("declarer-editor", SECTION if after else form, locale, script, responsive=locale == "de" and not script)
                    if not after:
                        form = editor("set_declarer")
                    # Responsive refresh reconstructs accepted prefill, so make the native choice again.
                    choose(select, values[1])
                    source = active.path.read_bytes()
                    submit_proposal(form, keyboard=True)
                    if after:
                        assert active.path.read_bytes() == source
                        measure("declarer-preview", SECTION, locale, script)
                        action('form[action="' + PREFIX + 'cancel"] button', PREFIX + "cancel")
                        assert active.path.read_bytes() == source
                        form = editor("set_declarer")
                        choose(form + ' select[name="player_id"]', values[1])
                        submit_proposal(form)
                        apply(keyboard=True)
                    for play in plays[:9]:
                        browser.command("record_play", card=play["card"])
                    navigate("/sessions/current", script)
                    form = editor("set_declaration")
                    measure("declaration-editor", SECTION if after else form, locale, script, responsive=locale == "de" and not script)
                    enter(form + ' input[name="bid_value"]', "20")
                    if after:
                        # Enhanced unsent values follow this exact source; native language uses saved input.
                        action('form.language-selector button[value="' + other + '"]', "/actions/profile/language")
                        assert cdp.evaluate("document.querySelector(" + json.dumps(form + ' input[name="bid_value"]') + ").value") == ("20" if script else "18")
                        action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                        enter(form + ' input[name="bid_value"]', "20")
                    submit_proposal(form)
                    if after:
                        measure("lossless", SECTION, locale, script)
                        apply()
                    form = editor("set_declaration")
                    source = active.path.read_bytes()
                    submit_proposal(form, keyboard=True)
                    if after:
                        measure("noop", SECTION, locale, script)
                        apply(keyboard=True)
                    assert active.path.read_bytes() == source
                    form = editor("set_declaration")
                    enter(form + ' input[name="matadors"]', "2")
                    action(form + ' button[type=submit]', PREFIX + "preview" if after else "/sessions/command")
                    assert active.path.read_bytes() == source
                    measure("rejected", SECTION if after else form, locale, script)
                    enter(form + ' input[name="matadors"]', "")
                    choose(form + ' select[name="game_type"]', "null")
                    (args.output / (prefix + "-before-partial.json")).write_bytes(active.path.read_bytes())
                    submit_proposal(form)
                    if after:
                        assert active.path.read_bytes() == source
                        measure("partial", SECTION, locale, script, responsive=locale == "de" and not script)
                        # Native required checkbox prevents submission before fresh consent.
                        action('form[action="' + PREFIX + 'apply"] button')
                        action('form[action="' + PREFIX + 'apply"] input[name="confirm_apply"]')
                        target_language = "en" if locale == "de" else "de"
                        action('form.language-selector button[value="' + target_language + '"]', "/actions/profile/language")
                        assert not cdp.evaluate("document.querySelector('input[name=confirm_apply]').checked")
                        assert active.path.read_bytes() == source
                        # Inspect removal detail natively, including the first failed record.
                        summaries = cdp.evaluate("[...document.querySelectorAll('#session-declaration-correction details summary')].map(e=>e.innerText)")
                        assert len(summaries) >= 2
                        action('#session-declaration-correction details:nth-of-type(2) summary')
                        assert cdp.evaluate("document.querySelector('#session-declaration-correction details:nth-of-type(2)').open")
                        measure("removed-records", SECTION, target_language, script)
                        cdp.evaluate("document.querySelector('#session-declaration-correction details:nth-of-type(2)').scrollIntoView({block:'start'})")
                        cdp.screenshot(args.output / (prefix + "-removed-list.png"))
                        apply(partial=True, keyboard=True)
                    retained = [r.command.card for r in active.state.command_log if r.command.kind == "record_play"]
                    assert retained == ["CK", "C7", "CA", "SK", "S7", "S10"]
                    evidence["sources"][prefix + "-partial"] = digest(active.path.read_bytes())
                    (args.output / (prefix + "-partial.json")).write_bytes(active.path.read_bytes())
                    browser.command("record_play", card="HA")
                    opener = next(f for f in Forms(browser.page("/sessions")).forms
                        if f["action"] == "/sessions/open" and f["values"]["handle"] == active.handle)
                    follow(browser, browser.submit(opener))
                    assert server.app_context.managed_stateful.active_session.document == active.document
            # Genuine SJ review and unrelated Match Report remain independently source-bound.
            plays = record_score_review_game(browser, play_count=18)
            active = server.app_context.managed_stateful.active_session
            assert replay_session_state_v1(active.state).remaining_hand_for(active.state.local_player_id) == ("C10", "CJ", "DK", "D7")
            for play in plays[18:27]:
                browser.command("record_play", card=play["card"])
            assert replay_session_state_v1(active.state).remaining_hand_for(active.state.local_player_id) == ("CJ",)
            for play in plays[27:]:
                browser.command("record_play", card=play["card"])
            browser.command("set_game_end")
            page = follow(browser, browser.submit(score_review_form(browser)))
            locale = re.search(r'<html lang="([^"]+)"', page)[1]
            assert_summary_points(page, locale, 14, 29)
            assert_visible_equal_best(page, locale)
            assert_context(page, locale, hand=SESSION_HAND,
                prefix=(("B", "HJ"), ("C", "DJ")), actor="A", trick=4, play=3)
            active = server.app_context.managed_stateful.active_session
            retained = active.execution
            download_bytes = {name: browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                              for name in ("session", "request", "result")}
            for name, raw in download_bytes.items():
                (args.output / ("sj-" + name + ".json")).write_bytes(raw)
                evidence["sources"]["sj-" + name] = digest(raw)
            page = corrected_match_setup(browser)
            follow(browser, browser.submit(operation_form(page, "set_perspective_hand"), cards=MATCH_HAND, card_evidence_mode="exact"))
            match = server.app_context.managed_stateful.active_match
            analysis = next(f for f in Forms(browser.page("/matches/review/1")).forms if f["action"] == "/matches/api/v1/analysis" and f["values"].get("operation") == "analyze_decision")
            follow(browser, browser.submit(analysis))
            reports = match.capture.report_store.list()
            assert reports
            report_route = f"/matches/api/v1/reports/{reports[0].report_id}.json"
            report_bytes = browser.request("GET", report_route)[2]
            (args.output / "unrelated-match-report.json").write_bytes(report_bytes)
            evidence["sources"]["unrelated-match-report"] = digest(report_bytes)
            navigate("/sessions/current", True)
            form = editor("set_declaration")
            submit_proposal(form)
            if after:
                action('form[action="' + PREFIX + 'cancel"] button', PREFIX + "cancel")
                form = editor("set_declaration")
                submit_proposal(form)
                apply()
            assert active.execution is retained and match.capture.report_store.list() == reports
            for name, raw in download_bytes.items():
                assert browser.request("GET", "/sessions/downloads/" + name + ".json")[2] == raw
            form = editor("set_declaration")
            enter(form + ' input[name="bid_value"]', "20")
            submit_proposal(form)
            if after:
                apply()
            assert active.execution is None and match.capture.report_store.list() == reports
            assert browser.request("GET", report_route)[2] == report_bytes
            evidence.update(completed=True, calls=dict(calls), payloads=payloads)
    finally:
        evidence.update(calls=dict(calls), payloads=payloads)
        (args.output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=True, indent=2), encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]),
                      "actions": len(evidence["actions"]), "calls": dict(calls)}))


if __name__ == "__main__":
    main()
