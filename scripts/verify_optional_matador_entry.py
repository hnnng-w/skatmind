# ruff: noqa: E501 - Browser expressions retain their local measurement context.
"""Optional #262 installed-Wheel evidence; existing DevTools transport and legal test fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl
from zipfile import ZipFile

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, focus, keyboard, tab_to
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_compact_declaration_web import before_declaration  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_game_navigation_web import create_empty  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND  # noqa: E402
from test_recorded_party_presentation import corrected_match_setup  # noqa: E402
from test_session_recorded_review_web import (  # noqa: E402
    Browser,
    Forms,
    record_live_game,
    review_first,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session as api  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.session_frontend as session_frontend  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

PREFIX = "/sessions/declaration-correction/"
ENTRY = 'form:has(input[value="session-declaration"])'
EDITOR = 'form[action="' + PREFIX + 'preview"]'
MATCH = 'form:has(input[value="match-declaration"])'
MODULES = ("compact_declaration_rendering.py", "compact_declaration_form.py",
    "compact_declaration_http.py", "task_first_rendering.py", "task_first_session_rendering.py",
    "task_first_match_rendering.py", "session_declaration_correction_rendering.py",
    "session_declaration_correction.py", "session_declaration_correction_http.py",
    "validation_rendering.py", "form_registry.py", "language_form_preservation.py",
    "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json")


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
    catalogs = load_frontend_translation_catalogs_v1()
    assert tuple(catalogs["de"]) == tuple(catalogs["en"]) == tuple(sorted(catalogs["en"]))
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "versions": {name: version(name) for name in ("skatmind", "jsonschema", "referencing", "tzdata", "pytest")},
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "wheel": digest(args.wheel.read_bytes()), "hashes": {}, "measurements": [],
        "actions": [], "payloads": [], "sources": {}, "passive": [],
        "inventory": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        "limits": ["Headless Edge emulation, not physical devices, screen readers or maintainer UAT.",
            "200% computed text is not browser zoom. Authenticated HTTP bytes are not Save-dialog tests.",
            "Existing pytest fixtures provide setup; no successful validation, persistence or analysis is mocked."]}
    with ZipFile(args.wheel) as wheel:
        for name in MODULES:
            raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
            assert raw == wheel.read("skatmind/app_web/" + name)
            expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if after else
                subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
            assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
            evidence["hashes"][name] = digest(raw)
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    mode, calls = "setup", Counter()
    real_read = Handler._read_body

    def read_body(handler, *a, **kw):
        result = real_read(handler, *a, **kw)
        evidence["payloads"].append({"mode": mode, "route": handler.path,
            "fields": parse_qsl(result[0].decode(), keep_blank_values=True)})
        return result

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[mode + ":" + label] += 1
            return real(*a, **kw)
        return wrapped

    def navigate(route, script):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + route)

    def expose(selector):
        # Locate closed ancestors, then use actual pointer activation on each summary.
        for _ in range(8):
            found = cdp.evaluate("(()=>{let e=document.querySelector(" + json.dumps(selector) + "),outer=null;for(;e;e=e.parentElement)if(e.matches('details:not([open])'))outer=e;if(!outer)return false;outer.querySelector(':scope > summary').id='probe-summary';return true})()")
            if not found:
                return
            click(cdp, "#probe-summary")
            cdp.evaluate("document.querySelector('#probe-summary').removeAttribute('id')")
        raise AssertionError("Could not expose native control: " + selector)

    def action(selector, route=None):
        start, before = len(evidence["payloads"]), calls.copy()
        expose(selector)
        tab_to(cdp, selector)
        keyboard(cdp, "Enter", "Enter", 13, "\r")
        time.sleep(.6)
        cdp.evaluate("void 0")
        posts = evidence["payloads"][start:]
        assert [p["route"] for p in posts] == ([] if route is None else [route]), (selector, posts)
        row = {"selector": selector, "posts": posts, "focus": focus(cdp),
            "operations": dict(calls - before), "javascript": not cdp.script_disabled}
        keyboard(cdp, "Tab", "Tab", 9)
        row["next_tab"] = focus(cdp)
        evidence["actions"].append(row)

    def enter(selector, value):
        start, before = len(evidence["payloads"]), calls.copy()
        expose(selector)
        click(cdp, selector)
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", windowsVirtualKeyCode=65, modifiers=2)
        keyboard(cdp, "Backspace", "Backspace", 8)
        if value:
            cdp.call("Input.insertText", text=value)
        assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").value") == value
        assert len(evidence["payloads"]) == start and calls == before
        evidence["actions"].append({"edit": selector, "value": value, "posts": [], "operations": {}})

    def choose(selector, value):
        expose(selector)
        click(cdp, selector)
        keyboard(cdp, "Escape", "Escape", 27)
        options = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].map(e=>e.value)")
        keyboard(cdp, "Home", "Home", 36)
        for _ in range(options.index(value)):
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Enter", "Enter", 13)
        assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").value") == value

    def measure(name, form, locale, *, responsive=False):
        source = server.app_context.managed_stateful.active_match if form == MATCH else server.app_context.managed_stateful.active_session
        raw, before, posts = source.path.read_bytes(), calls.copy(), len(evidence["payloads"])
        control = form + ' input[name="matadors"]'
        expose(control)
        cells = ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)) if responsive else ((390, 844, 1),)
        for width, height, scale in cells:
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
            if scale == 2:
                cdp.evaluate(TEXT_ENLARGEMENT)
            tab_to(cdp, control)
            cdp.evaluate("document.querySelector(" + json.dumps(control) + ").closest('details').scrollIntoView({block:'start'});scrollBy(0,-12)")
            row = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),d=e.closest('details'),f=e.form;
                const rect=n=>{const r=n.getBoundingClientRect(),s=getComputedStyle(n);return {width:r.width,height:r.height,left:r.left,right:r.right,font:s.fontSize,padding:s.padding,outline:s.outline,text:n.innerText,client:n.clientWidth,scroll:n.scrollWidth}};
                return {input:{...rect(e),value:e.value,type:e.type,attributes:Object.fromEntries([...e.attributes].map(a=>[a.name,a.value]))},
                    container:rect(d),label:rect(e.closest('label')),help:[...d.querySelectorAll('p')].map(rect),
                    bid:rect(f.querySelector('[name=bid_value]')),page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
                    unique_ids:new Set([...document.querySelectorAll('[id]')].map(n=>n.id)).size===document.querySelectorAll('[id]').length,
                    associations:(e.getAttribute('aria-describedby')||'').split(' ').filter(Boolean).map(id=>({id,text:document.getElementById(id)?.innerText}))};})""" + "(" + json.dumps(control) + ")")
            row.update(name=name, locale=locale, javascript=not cdp.script_disabled, viewport=[width, height], scale=scale, focus=focus(cdp))
            evidence["measurements"].append(row)
            (args.output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=True, indent=2), encoding="utf-8")
            assert row["unique_ids"]
            if after:
                assert row["input"]["width"] <= min(7 * float(row["input"]["font"][:-2]), row["label"]["width"]) + 1
                assert row["input"]["attributes"]["class"] == "declaration-matadors"
                assert len(row["associations"]) >= 1
            cdp.screenshot(args.output / f"{name}-{locale}-{int(not cdp.script_disabled)}-{width}-{scale}.png")
        assert source.path.read_bytes() == raw and calls == before and len(evidence["payloads"]) == posts
        evidence["passive"].append({"name": name, "source": digest(raw), "operations": {}, "posts": 0})
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
        if responsive:
            navigate("/matches/position/1" if form == MATCH else "/sessions/current", not cdp.script_disabled)

    def editor():
        selectors = '.accepted-declaration form[action="' + PREFIX + 'select"]'
        cdp.evaluate("document.querySelectorAll(" + json.dumps(selectors) + ")[1].id='probe-entry'")
        action("#probe-entry button", PREFIX + "select")

    def save_source(name, raw):
        evidence["sources"][name] = digest(raw)
        (args.output / (name + ".json")).write_bytes(raw)

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_save"),
                (capture.MatchCaptureWebContextV1, "save_candidate", "match_save"),
                (api, "correct_session_command", "correction"),
                (session_frontend, "_collect_current_checkpoint", "checkpoint_collection"),
                (execution, "execute", "session_analysis"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_analysis"),
                (profile, "save_frontend_profile_file_v1", "profile_write"),
                (match_state, "_decision_preparation_summary", "match_page_preparation")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read_body))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert digest(browser.request("GET", route)[2]) == evidence["hashes"][resource]
            for script, locale in ((True, "de"), (False, "en"), (False, "de"), (True, "en")):
                mode = "setup"
                defender = locale == "en"
                before_declaration(browser, defender=defender, hand="CJ SJ HJ DJ CA C10 CK CQ C9 C8".split())
                follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"), language=locale))
                navigate("/sessions/current", script)
                active = server.app_context.managed_stateful.active_session
                source = active.path.read_bytes()
                mode = "native"
                choose(ENTRY + ' select[name="game_type"]', "grand")
                click(cdp, ENTRY + ' input[name="hand_game"]')
                enter(ENTRY + ' input[name="matadors"]', "2" if defender else "4")
                measure("session-entry", ENTRY, locale, responsive=script and locale == "de")
                # A responsive reload deliberately loses unsent native input; enter again.
                choose(ENTRY + ' select[name="game_type"]', "grand")
                if not cdp.evaluate("document.querySelector(" + json.dumps(ENTRY + ' input[name="hand_game"]') + ").checked"):
                    click(cdp, ENTRY + ' input[name="hand_game"]')
                enter(ENTRY + ' input[name="matadors"]', "2" if defender else "4")
                action(ENTRY + ' button[type="submit"]', "/sessions/command")
                if defender:
                    assert active.path.read_bytes() == source
                    measure("session-error", ENTRY, locale)
                    enter(ENTRY + ' input[name="matadors"]', "")
                    action(ENTRY + ' button[type="submit"]', "/sessions/command")
                assert active.state.command_log[-1].command.declaration.matadors == (None if defender else 4)
                editor()
                measure("session-editor", EDITOR, locale, responsive=not script and locale == "en")
                selected = active.declaration_correction.selected
                source = active.path.read_bytes()
                enter(EDITOR + ' input[name="matadors"]', "12345bad")
                other = "en" if locale == "de" else "de"
                action('form.language-selector button[value="' + other + '"]', "/actions/profile/language")
                assert cdp.evaluate("document.querySelector(" + json.dumps(EDITOR + ' input[name="matadors"]') + ").value") == ("12345bad" if script else "" if defender else "4")
                assert active.declaration_correction.selected is selected and active.path.read_bytes() == source
                enter(EDITOR + ' input[name="matadors"]', "12345bad")
                action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
                assert active.path.read_bytes() == source
                action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                assert cdp.evaluate("document.querySelector(" + json.dumps(EDITOR + ' input[name="matadors"]') + ").value") == "12345bad"
                measure("editor-error", EDITOR, locale)
                enter(EDITOR + ' input[name="matadors"]', "")
                action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
                assert not cdp.evaluate("!!document.querySelector('input[name=matadors]')")
                assert active.path.read_bytes() == source
                action('form[action="' + PREFIX + 'cancel"] button', PREFIX + "cancel")
                editor()
                action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
                action('form[action="' + PREFIX + 'apply"] button', PREFIX + "apply")
                assert active.path.read_bytes() == source
                editor()
                enter(EDITOR + ' input[name="matadors"]', "")
                enter(EDITOR + ' input[name="bid_value"]', "17")
                action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
                action('form[action="' + PREFIX + 'apply"] button', PREFIX + "apply")
                assert active.state.command_log[-1].command.declaration.matadors is None
                save_source(f"session-{locale}-{int(script)}", active.path.read_bytes())
                mode = "setup"
                opener = next(f for f in Forms(browser.page("/sessions")).forms if f["action"] == "/sessions/open" and f["values"]["handle"] == active.handle)
                follow(browser, browser.submit(opener))
                assert server.app_context.managed_stateful.active_session.document == active.document
                page = create_empty(browser, locale)
                follow(browser, browser.submit(operation_form(page, "start_game")))
                navigate("/matches/position/1", script)
                mode = "native"
                player = cdp.evaluate("[...document.querySelector('select[name=declarer_player_id]').options].find(o=>o.value).value")
                choose(MATCH + ' select[name="declarer_player_id"]', player)
                choose(MATCH + ' select[name="game_type"]', "clubs")
                enter(MATCH + ' input[name="matadors"]', "11")
                action(MATCH + ' button[type="submit"]', "/matches/api/v1/operation")
                match = server.app_context.managed_stateful.active_match
                assert match.workspace.slots[0].observed_game.declaration.matadors == 11
                measure("match-count-11", MATCH, locale, responsive=not script and locale == "de")
                choose(MATCH + ' select[name="game_type"]', "null")
                action(MATCH + ' button[type="submit"]', "/matches/api/v1/operation")
                measure("match-null-error", MATCH, locale, responsive=script and locale == "en")
                enter(MATCH + ' input[name="matadors"]', "")
                action(MATCH + ' button[type="submit"]', "/matches/api/v1/operation")
                assert match.workspace.slots[0].observed_game.declaration.matadors is None
                save_source(f"match-{locale}-{int(script)}", match.path.read_bytes())
                mode = "setup"
                opener = next(f for f in Forms(browser.page("/matches")).forms if f["action"] == "/matches/open" and f["values"]["handle"] == match.handle)
                follow(browser, browser.submit(opener))
                assert server.app_context.managed_stateful.active_match.workspace == match.workspace

            # One bounded genuine execution per family, reused for passive byte comparisons.
            mode = "artifact_setup"
            record_live_game(browser, play_count=3)
            review_first(browser)
            active = server.app_context.managed_stateful.active_session
            retained = active.execution
            downloads = {n: browser.request("GET", "/sessions/downloads/" + n + ".json")[2] for n in ("session", "request", "result")}
            page = corrected_match_setup(browser)
            follow(browser, browser.submit(operation_form(page, "set_perspective_hand"), cards=MATCH_HAND, card_evidence_mode="exact"))
            analysis = next(f for f in Forms(browser.page("/matches/review/1")).forms if f["action"] == "/matches/api/v1/analysis" and f["values"].get("operation") == "analyze_decision")
            follow(browser, browser.submit(analysis))
            match = server.app_context.managed_stateful.active_match
            report, = match.capture.report_store.list()
            report_route = f"/matches/api/v1/reports/{report.report_id}.json"
            report_raw = browser.request("GET", report_route)[2]
            for name, raw in downloads.items():
                save_source("retained-" + name, raw)
            save_source("retained-report", report_raw)
            mode = "artifact_passive"
            navigate("/sessions/current", True)
            editor()
            for locale in ("de", "en"):
                action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                measure("retained-editor", EDITOR, locale)
            action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
            action('form[action="' + PREFIX + 'cancel"] button', PREFIX + "cancel")
            editor()
            action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
            action('form[action="' + PREFIX + 'apply"] button', PREFIX + "apply")
            assert active.execution is retained
            for name, raw in downloads.items():
                assert browser.request("GET", "/sessions/downloads/" + name + ".json")[2] == raw
            navigate("/matches/position/1", False)
            for locale in ("de", "en"):
                action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                measure("retained-match", MATCH, locale)
            assert browser.request("GET", report_route)[2] == report_raw
            assert match.capture.report_store.list() == (report,)
            mode = "artifact_mutation"
            navigate("/sessions/current", True)
            editor()
            enter(EDITOR + ' input[name="bid_value"]', "17")
            action(EDITOR + ' button[type="submit"]', PREFIX + "preview")
            assert active.execution is retained
            action('form[action="' + PREFIX + 'apply"] button', PREFIX + "apply")
            assert active.execution is None and browser.request("GET", report_route)[2] == report_raw
            evidence["completed"] = True
    finally:
        evidence["calls"] = dict(calls)
        (args.output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=True, indent=2), encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({"completed": True, "measurements": len(evidence["measurements"]), "calls": dict(calls)}))


if __name__ == "__main__":
    main()
