# ruff: noqa: E501 - Keep optional browser measurements and native actions legible.
"""Bounded #264 installed-Wheel evidence, using existing dependency-free browser tooling."""

from __future__ import annotations

import argparse
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
from verify_optional_matador_entry import digest
from verify_recording_deletion import click, focus, keyboard, tab_to
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_analysis_action_placement import (  # noqa: E402
    ADVANCED,
    DEFAULTS,
    assert_decision_form,
)
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
import skatmind.match_decision_analysis as decision_analysis  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.json_transfer import (  # noqa: E402
    canonical_frontend_json_bytes_v1 as canonical,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402
from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1  # noqa: E402
from skatmind.match_decision_analysis import build_match_decision_position_request_v1  # noqa: E402

FORM = 'form[action="/matches/api/v1/analysis"]:has(input[value="analyze_decision"])'
SELECT = FORM + ' select[name="decision_index"]'
BUTTON = FORM + ' > button'
DETAILS = FORM + ' > details'
SUMMARY = DETAILS + ' > summary'
OUTER = 'details:has(> form > input[value="analyze_decision"]) > summary'
MODULES = ("task_first_rendering.py", "task_first_match_rendering.py", "match_review_rendering.py",
    "task_first_match_state.py", "match_review_context.py", "validation_rendering.py",
    "language_context.py", "language_form_preservation.py", "form_registry.py", "server.py",
    "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json")


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
    assert tuple(catalogs["en"]) == tuple(catalogs["de"])
    evidence = dict(completed=False, phase=args.phase, python=sys.version,
        starting_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        versions={name: version(name) for name in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        installed_module=skatmind.__file__, wheel=digest(args.wheel.read_bytes()), hashes={},
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        actions=[], measurements=[], payloads=[], responses=[], sources={}, executions=[],
        limits=["Headless Edge, synthetic data, no physical-device, screen-reader or maintainer UAT.",
            "200% computed text is not browser zoom. HTTP download bytes are not Save-dialog testing.",
            "Native DevTools input; no element.focus or scripted form submission.",
            "One six-Play partial Match reused across views; no full Game or race framework."])
    assert evidence["inventory"] == [67, 112, 1805]
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
    calls, mode, invocations = Counter(), "setup", []
    real_read, real_send = Handler._read_body, Handler._send_bytes

    def read_body(handler, *a, **kw):
        result = real_read(handler, *a, **kw)
        evidence["payloads"].append(dict(mode=mode, route=handler.path,
            content_type=result[1], fields=parse_qsl(result[0].decode(), keep_blank_values=True)))
        return result

    def send(handler, status, content, **kw):
        evidence["responses"].append(dict(mode=mode, method=handler.command, route=handler.path,
            status=int(status), location=dict(kw.get("extra_headers", ())).get("Location")))
        return real_send(handler, status, content, **kw)

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[mode + ":" + label] += 1
            if label == "application":
                invocations.append(a[0])
            return real(*a, **kw)
        return wrapped

    def record(name, callback, *, passive=False):
        before, posts = calls.copy(), len(evidence["payloads"])
        result = callback()
        delta = calls - before
        if passive:
            assert all(k.endswith("page_preparation") for k in delta), delta
            assert len(evidence["payloads"]) == posts
        evidence["actions"].append(dict(name=name, mode=mode, calls=dict(delta),
            posts=len(evidence["payloads"]) - posts, active=focus(cdp)))
        return result

    def navigate(route):
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + route)
        cdp.call("Page.bringToFront")

    def activate(selector):
        click(cdp, selector)
        time.sleep(.6)
        cdp.evaluate("void 0")

    def key(name="Tab", shift=False):
        number = {"Tab": 9, "Enter": 13, " ": 32}[name]
        code = "Space" if name == " " else name
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=name, code=code,
            windowsVirtualKeyCode=number, modifiers=8 if shift else 0,
            **({"text": "\r"} if name == "Enter" else {}))
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=name, code=code,
            windowsVirtualKeyCode=number, modifiers=8 if shift else 0)

    def type_value(name, value):
        click(cdp, FORM + f' input[name="{name}"]')
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.insertText", text=value)

    def choose_second():
        click(cdp, SELECT)
        keyboard(cdp, "Escape", "Escape", 27)
        keyboard(cdp, "Home", "Home", 36)
        keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Enter", "Enter", 13)
        assert cdp.evaluate("document.querySelector(" + json.dumps(SELECT) + ").value") == "6"

    def wait_post(before, status):
        for _ in range(600):
            cdp.evaluate("void 0")
            rows = [r for r in evidence["responses"][before:] if r["method"] == "POST"]
            if rows and cdp.evaluate("document.readyState==='complete'"):
                assert rows[-1]["status"] == status, rows
                time.sleep(.3)
                return
            time.sleep(.1)
        raise AssertionError("Native submission did not finish")

    def submit(name, *, implicit=False, pointer=False, status=303):
        def action():
            before = len(evidence["responses"])
            if pointer:
                click(cdp, BUTTON)
            else:
                if not implicit:
                    tab_to(cdp, BUTTON)
                key("Enter")
            wait_post(before, status)
        record(name, action)

    def source(name, raw):
        evidence["sources"][name] = digest(raw)
        (args.output / (name + ".json")).write_bytes(raw)

    def current_report():
        route = cdp.evaluate("location.pathname")
        assert route.startswith("/matches/reports/")
        return active.capture.report_store.get(route.rsplit("/", 1)[1])

    def measure(name, caller, width, scale):
        data = cdp.evaluate("""(s=>{const f=document.querySelector(s),sel=f.querySelector('select'),b=f.querySelector('button'),d=f.querySelector('details');
            const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right,font:s.fontSize,visible:e.checkVisibility(),text:e.tagName==='SELECT'?e.selectedOptions[0].text:e.innerText}};
            return {selector:box(sel),button:box(b),disclosure:box(d),summary:box(d.querySelector('summary')),open:d.open,
                order:[...f.querySelectorAll('select[name=decision_index],button,details')].map(e=>e.tagName),
                labels:[...f.querySelectorAll('input:not([type=hidden]),select')].map(e=>({name:e.name,labels:[...e.labels].map(l=>l.innerText),disabled:e.disabled})),
                values:[...new FormData(f).entries()], client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                unique_ids:new Set([...document.querySelectorAll('[id]')].map(e=>e.id)).size===document.querySelectorAll('[id]').length};})""" + "(" + json.dumps(FORM) + ")")
        data.update(name=name, caller=caller, width=width, scale=scale,
            locale=cdp.evaluate("document.documentElement.lang"), javascript=not cdp.script_disabled)
        assert data["order"] == (["SELECT", "BUTTON", "DETAILS"] if after else ["SELECT", "DETAILS", "BUTTON"])
        assert data["client"] == data["scroll"] and data["unique_ids"]
        assert all(row["labels"] and not row["disabled"] for row in data["labels"])
        assert all(data[k]["visible"] for k in ("selector", "button", "summary"))
        if after:
            assert data["selector"]["bottom"] <= data["button"]["y"] < data["disclosure"]["y"]
        else:
            assert data["selector"]["bottom"] <= data["disclosure"]["y"] < data["button"]["y"]
        data["selector_button_gap"] = data["button"]["y"] - data["selector"]["bottom"]
        evidence["measurements"].append(data)
        cdp.evaluate("document.querySelector(" + json.dumps(SELECT) + ").closest('label').scrollIntoView({block:'start'});window.scrollBy(0,-12)")
        cdp.screenshot(args.output / f"{caller}-{name}-{data['locale']}-{int(data['javascript'])}-{width}-{scale}.png")

    try:
        with ExitStack() as stack:
            for module, name, label in (
                (capture, "save_match_workspace_file_v1", "match_save"),
                (analysis, "execute_match_decision_analysis_v1", "match_analysis"),
                (decision_analysis, "execute_application_invocation", "application"),
                (profile, "save_frontend_profile_file_v1", "profile_write"),
                (match_state, "_decision_preparation_summary", "page_preparation")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read_body))
            stack.enter_context(patch.object(Handler, "_send_bytes", send))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert digest(browser.request("GET", route)[2]) == evidence["hashes"][resource]
            page = record_context_match(browser)
            for card in ("SA", "S7", "S10"):
                page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
            active = server.app_context.managed_stateful.active_match
            saved = active.path.read_bytes()
            source("match", saved)
            evidence["setup"] = dict(calls=dict(calls), description="Returned native HTTP creation, declaration, six legal Plays and C's initial hand. No injected Report.")
            for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
                mode = "language"
                page = browser.page("/matches/review/1")
                follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language=locale))
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
                mode = "passive"
                recording = locale == "de" and not script
                record("default-recording" if recording else "default-review", lambda recording=recording: navigate("/matches/current" if recording else "/matches/review/1"), passive=True)
                if recording:
                    record("explicit-outer-default-analysis-opening", lambda: activate(OUTER), passive=True)
                assert_decision_form(cdp.evaluate("document.documentElement.outerHTML"), locale, indexes=("2", "6"), focused=not recording, ordered=after)
                mode = "native"
                submit("default-analysis", pointer=True)
                first = current_report()
                assert first.value.options == MatchDecisionAnalysisOptionsV1()
                assert first.value.decision_index == 2
                report_route = f"/matches/reports/{first.report_id}"
                assert cdp.evaluate("location.pathname") == report_route
                snapshot = canonical(first.to_dict())
                download_route = f"/matches/api/v1/reports/{first.report_id}.json"
                download = browser.request("GET", download_route)[2]
                prefix = f"{locale}-{int(script)}"
                source(prefix + "-default-report", snapshot)
                source(prefix + "-default-download", download)
                mode = "passive"
                for caller, route in (("recording", "/matches/position/1"), ("review", "/matches/review/1"), ("report", report_route)):
                    cells = ((1365, 1), (390, 1), (320, 1), (320, 2)) if locale == "de" and not script else ((390, 1),)
                    for width, scale in cells:
                        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
                        record(caller + "-navigation", lambda route=route: navigate(route), passive=True)
                        if caller == "recording":
                            assert not cdp.evaluate("document.querySelector(" + json.dumps(FORM) + ").closest('details').open")
                            record("explicit-outer-analysis-opening", lambda: activate(OUTER), passive=True)
                        if scale == 2:
                            cdp.evaluate(TEXT_ENLARGEMENT)
                        measure("closed", caller, width, scale)
                        # Reach the select by native Tab from the current page/outer summary.
                        tab_to(cdp, SELECT)
                        chain = [focus(cdp)]
                        key()
                        chain.append(focus(cdp))
                        assert cdp.evaluate("document.activeElement.matches(" + json.dumps(BUTTON if after else SUMMARY) + ")")
                        key("Tab", shift=True)
                        assert cdp.evaluate("document.activeElement.matches(" + json.dumps(SELECT) + ")")
                        tab_to(cdp, SUMMARY)
                        chain.append(focus(cdp))
                        key(" ")
                        assert cdp.evaluate("document.querySelector(" + json.dumps(DETAILS) + ").open")
                        measure("open", caller, width, scale)
                        key()
                        chain.append(focus(cdp))
                        evidence["actions"].append(dict(name="native-tab-shift-tab-summary-space-next-tab", caller=caller, locale=locale, script=script, width=width, scale=scale, chain=chain))
                        assert active.path.read_bytes() == saved and canonical(first.to_dict()) == snapshot
                        assert browser.request("GET", download_route)[2] == download
                # Normal unsent fields and disclosure state: enhanced restoration versus native defaults.
                mode = "native"
                record("normal-unsent-seed", lambda: type_value("immediate_random_seed", "17"), passive=True)
                for language in ("en" if locale == "de" else "de", locale):
                    record("normal-language", lambda language=language: activate(f'form.language-selector button[value="{language}"]'))
                    assert cdp.evaluate("document.querySelector(" + json.dumps(DETAILS) + ").open") is script
                    assert cdp.evaluate("document.querySelector(" + json.dumps(FORM + ' input[name="immediate_random_seed"]') + ").value") == ("17" if script else "0")
                    assert active.path.read_bytes() == saved and canonical(first.to_dict()) == snapshot
                    assert browser.request("GET", download_route)[2] == download
                # Real invalid advanced data, submitted after closing details; recovery through language.
                mode = "passive"
                record("nondefault-report", lambda report_route=report_route: navigate(report_route), passive=True)
                mode = "native"
                record("select-nonfirst", choose_second, passive=True)
                record("open-settings", lambda: activate(SUMMARY), passive=True)
                for name, value in (("immediate_sample_count", "-1"), ("immediate_random_seed", "27"), ("search_random_seed", "91")):
                    record("type-" + name, lambda name=name, value=value: type_value(name, value), passive=True)
                tab_to(cdp, FORM + ' input[name="use_profile_presets"]')
                record("unchecked-profiles-space", lambda: key(" "), passive=True)
                record("close-changed-settings", lambda: activate(SUMMARY), passive=True)
                submit("invalid-closed-settings", status=400)
                assert cdp.evaluate("document.querySelector(" + json.dumps(DETAILS) + ").open")
                assert cdp.evaluate("!!document.querySelector('[name=immediate_sample_count][aria-invalid=true]')")
                evidence["actions"].append(dict(name="error-focus", focus=focus(cdp)))
                cdp.screenshot(args.output / (prefix + "-error.png"))
                if (locale, script) in (("de", False), ("en", True)):
                    measure("invalid", "review", cdp.evaluate("innerWidth"), 1)
                for language in ("en" if locale == "de" else "de", locale):
                    record("error-language", lambda language=language: activate(f'form.language-selector button[value="{language}"]'))
                    assert cdp.evaluate("document.querySelector(" + json.dumps(DETAILS) + ").open")
                record("unsent-seed", lambda: type_value("immediate_random_seed", "31"), passive=True)
                record("close-invalid-settings", lambda: activate(SUMMARY), passive=True)
                record("unsent-language", lambda locale=locale: activate(f'form.language-selector button[value="{"en" if locale == "de" else "de"}"]'))
                assert cdp.evaluate("document.querySelector(" + json.dumps(DETAILS) + ").open")
                seed = "31" if script else "27"
                values = dict(cdp.evaluate("[...new FormData(document.querySelector(" + json.dumps(FORM) + ")).entries()]"))
                assert values["immediate_random_seed"] == seed and values["decision_index"] == "6"
                assert "use_profile_presets" not in values
                assert browser.request("GET", download_route)[2] == download
                # Error-summary link reaches the later field without manufactured focus.
                record("error-summary-link", lambda: activate('.error-summary a[href^="#validation-field-"]'), passive=True)
                cdp.screenshot(args.output / (prefix + "-field-error.png"))
                record("recover-sample-count", lambda: type_value("immediate_sample_count", "3"), passive=True)
                if (locale, script) in (("de", False), ("en", True)):
                    measure("recovery", "review", cdp.evaluate("innerWidth"), 1)
                record("close-recovered-settings", lambda: activate(SUMMARY), passive=True)
                submit("closed-nondefault-recovery")
                result = current_report()
                expected = MatchDecisionAnalysisOptionsV1(immediate_sample_count=3, immediate_random_seed=int(seed), use_profile_presets=False)
                assert result.value.decision_index == 6 and result.value.options == expected
                prepared = build_match_decision_position_request_v1(active.workspace, match_position=1, decision_index=6, options=expected)
                assert result.value.request == prepared.request == invocations[-1].request
                assert invocations[-1].options == prepared.application_options
                assert invocations[-1].external_documents == prepared.external_documents
                assert cdp.evaluate("location.pathname") == f"/matches/reports/{result.report_id}"
                values = operation_form(cdp.evaluate("document.documentElement.outerHTML"), "analyze_decision")["values"]
                assert values["decision_index"] == "2" and {k: values[k] for k in ADVANCED} == DEFAULTS
                result_focus = focus(cdp)
                key()
                evidence["executions"].append(dict(locale=locale, script=script, decision=6, options=expected.to_dict(), focus=result_focus, next_tab=focus(cdp)))
                source(prefix + "-request", canonical(result.value.request.to_dict()))
                source(prefix + "-result", canonical(result.value.result.to_dict()))
                source(prefix + "-report", canonical(result.to_dict()))
                source(prefix + "-download", browser.request("GET", f"/matches/api/v1/reports/{result.report_id}.json")[2])
                assert active.path.read_bytes() == saved
                if locale == "en" and script:
                    # A separate native text-field Enter on the retained Report form.
                    record("report-open-settings", lambda: activate(SUMMARY), passive=True)
                    record("report-sample-count", lambda: type_value("immediate_sample_count", "2"), passive=True)
                    submit("report-implicit-enter", implicit=True)
                    assert current_report().value.options.immediate_sample_count == 2
            evidence["counts"] = dict(calls)
            assert calls["native:match_analysis"] == calls["native:application"] == 9
            assert not any(value for name, value in calls.items() if name.endswith("match_save") and not name.startswith("setup:"))
            evidence["completed"] = True
    finally:
        evidence["counts"] = dict(calls)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({key: evidence[key] for key in ("completed", "phase", "inventory", "counts")}, indent=2))


if __name__ == "__main__":
    main()
