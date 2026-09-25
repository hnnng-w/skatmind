# ruff: noqa: E501 - Optional native-browser observations retain readable selectors.
"""Bounded #265 independent-Wheel comparison; fresh synthetic roots only."""

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

from test_frontend_language_switching import localized_server  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_recording_entry_settings_navigation import (  # noqa: E402
    ENTRY,
    TECHNICAL,
    TECHNICAL_FILES,
    assert_shell,
    main_content,
    technical_section,
)
from test_session_recorded_review_web import Browser, record_live_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.recorded_review_opening as opening  # noqa: E402
import skatmind.app_web.server as web  # noqa: E402
import skatmind.app_web.stateful_context as stateful  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

MODULES = ("rendering.py", "entry_rendering.py", "profile_settings_rendering.py",
    "locales/de.json", "locales/en.json", "assets/app.css", "assets/workflow.js",
    "templates/app.html", "server.py", "form_registry.py", "information_architecture.py",
    "frontend_profile_operations.py", "frontend_profile_codec.py", "recorded_review_opening.py",
    "task_first_rendering.py", "task_first_match_rendering.py")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    catalogs = load_frontend_translation_catalogs_v1()
    evidence = dict(completed=False, phase=args.phase, python=sys.version,
        starting_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        installed_module=skatmind.__file__, wheel=digest(args.wheel.read_bytes()),
        versions={name: version(name) for name in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        hashes={}, served={}, actions=[], measurements=[], payloads=[], responses=[], sources={},
        limits=["Headless Edge with synthetic sources; no physical device, screen-reader or maintainer UAT.",
            "200% computed text is not browser zoom; authenticated HTTP bytes are not Save-dialog tests.",
            "About technical area is an always-visible secondary section, not a disclosure. Only its existing storage disclosure is opened.",
            "Technical filenames are non-clickable code text; no extra service or external URL is launched."])
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
    calls, mode = Counter(), "bootstrap"
    Handler = web.SkatMindAppWebRequestHandlerV1
    read_body, send_bytes = Handler._read_body, Handler._send_bytes

    def counted(label, real):
        def call(*a, **kw):
            calls[mode + ":" + label] += 1
            result = real(*a, **kw)
            if label == "profile_save":
                calls[mode + ":profile_" + result.status] += 1
            return result
        return call

    def read(handler, *a, **kw):
        body, kind = read_body(handler, *a, **kw)
        evidence["payloads"].append(dict(mode=mode, route=handler.path,
            fields=parse_qsl(body.decode(), keep_blank_values=True)))
        return body, kind

    def send(handler, status, raw, **kw):
        evidence["responses"].append(dict(mode=mode, method=handler.command, route=handler.path,
            status=int(status), location=dict(kw.get("extra_headers", ())).get("Location")))
        return send_bytes(handler, status, raw, **kw)

    def action(name, selector, *, native_key=False, post=None):
        before, start = calls.copy(), len(evidence["payloads"])
        profile_path = server.app_context.frontend_profile.profile_path
        profile_before = profile_path.read_bytes() if profile_path.exists() else None
        if native_key:
            tab_to(cdp, selector)
            pre_focus = focus(cdp)
            if name in {"session-remaining-route", "settings-remaining-route"} and cdp.evaluate("innerWidth") == 390:
                cdp.screenshot(args.output / (name + "-focus-" + cdp.evaluate("document.documentElement.lang") + "-" + str(int(not cdp.script_disabled)) + ".png"))
            keyboard(cdp, "Enter", "Enter", 13, "\r")
        else:
            # The native next-Tab observation may expose the skip link over the brand.
            # Tab away before pointer hit-testing; do not manufacture focus or click through it.
            if cdp.evaluate("document.activeElement.matches('.skip-link')"):
                keyboard(cdp, "Tab", "Tab", 9)
            pre_focus = focus(cdp)
            click(cdp, selector)
        for _ in range(600):
            time.sleep(.1)
            ready = cdp.evaluate("document.readyState==='complete'")
            if ready and (post is None or len(evidence["payloads"]) > start):
                break
        time.sleep(.4)
        row = dict(name=name, mode=mode, javascript=not cdp.script_disabled,
            locale=cdp.evaluate("document.documentElement.lang"), selector=selector,
            input="Tab/Enter" if native_key else "pointer", before_focus=pre_focus,
            url=cdp.evaluate("location.pathname+location.hash"), active=focus(cdp),
            calls=dict(calls - before), posts=evidence["payloads"][start:])
        keyboard(cdp, "Tab", "Tab", 9)
        row["next_tab"] = focus(cdp)
        evidence["actions"].append(row)
        assert [r["route"] for r in row["posts"]] == ([] if post is None else [post]), row
        if post is None:
            assert all(k.endswith((":discovery", ":review_open")) for k in row["calls"]), row
            assert (profile_path.read_bytes() if profile_path.exists() else None) == profile_before

    def type_value(selector, value):
        click(cdp, selector)
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.insertText", text=value)

    def measure(name, locale, script, width, scale):
        page = cdp.evaluate("(() => {const copy=document.documentElement.cloneNode(true);copy.querySelectorAll('[style]').forEach(e=>e.removeAttribute('style'));return copy.outerHTML})()")
        assert_shell(page)
        if name == "home":
            caption = cdp.evaluate("document.querySelectorAll('.task-summary')[1].textContent")
            assert (caption == ENTRY[locale]) is after
        if name == "session":
            caption = cdp.evaluate("document.querySelector('.entry-introduction').textContent")
            assert (caption == ENTRY[locale]) is after
        if name == "settings":
            assert ('<p><a href="/sessions">' not in main_content(page)) is after
            assert ('<a href="/matches/new">' not in main_content(page)) is after
        if name == "about":
            section = technical_section(page)
            assert re.findall(r'<code>(.*?)</code>', section) == TECHNICAL_FILES
            assert not re.findall(r'<(?:a|button|form|details)\b|href=', section)
            assert (TECHNICAL[locale][0] in section) is after
            assert ('<p><a href="/settings">' not in main_content(page)) is after
        data = cdp.evaluate("""(() => {const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText,x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontSize,visible:e.checkVisibility()}};
            return {url:location.pathname,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
                headings:[...document.querySelectorAll('main h1,main h2,main h3')].map(box),
                affected:[...document.querySelectorAll('.task-summary,.entry-introduction,.local-settings>p,#interfaces-heading,#interfaces-heading~p')].map(box),
                links:[...document.querySelectorAll('main a')].map(e=>({href:e.getAttribute('href'),text:e.textContent})),
                warnings:[...document.querySelectorAll('.error-summary,.field-error,.profile-warning,.reset-form p,#recommended-reset-heading~p')].map(box),
                forms:[...document.forms].map(f=>({action:f.getAttribute('action'),method:f.method,fields:[...f.elements].map(e=>({tag:e.tagName,name:e.name,type:e.type,value:e.type==='file'?'':e.name==='_frontend_language_context'?'process-local-language-binding':e.value,checked:e.checked,required:e.required,maxlength:e.getAttribute('maxlength')}))})),
                technical:document.querySelector('#interfaces-heading')?.parentElement.innerText,
                overflow:[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility()&&e.getBoundingClientRect().right>innerWidth+1).map(box)};})()""")
        data.update(name=name, locale=locale, javascript=script, width=width, scale=scale)
        evidence["measurements"].append(data)
        cdp.screenshot(args.output / f"{name}-{locale}-{int(script)}-{width}-{scale}.png", whole=True)

    try:
        with ExitStack() as stack:
            for module, name, label in (
                (session_files, "save_session_file", "session_save"),
                (capture, "save_match_workspace_file_v1", "match_save"),
                (profile, "save_frontend_profile_file_v1", "profile_save"),
                (execution, "execute", "execution"),
                (web, "discover_managed_items_v1", "discovery"),
                (stateful, "discover_managed_items_v1", "discovery"),
                (web, "open_recording_for_review_v1", "review_open"),
                (web, "open_guided_session_v1", "source_load"),
                (web, "open_unified_match_v1", "source_load"),
                (opening, "open_guided_session_v1", "source_load"),
                (opening, "open_unified_match_v1", "source_load")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read))
            stack.enter_context(patch.object(Handler, "_send_bytes", send))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.navigate(server.origin + "/")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                raw = browser.request("GET", route)[2]
                assert digest(raw) == evidence["hashes"][resource]
                evidence["served"][route] = digest(raw)
            for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                mode = "language"
                action("matrix-language", f'.language-selector button[value="{locale}"]', post="/actions/profile/language")
                cells = ((1365, 1), (390, 1), (320, 1), (320, 2)) if (locale, script) == ("de", False) else ((390, 1),)
                for width, scale in cells:
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
                    mode = "passive"
                    for name, selector in (("home", "a.brand"), ("session", 'main a[href="/sessions"]'), ("settings", '.site-nav a[href="/settings"]'), ("about", 'footer a[href="/about"]')):
                        action(name + "-remaining-route", selector, native_key=name in {"session", "settings"})
                        if scale == 2:
                            cdp.evaluate(TEXT_ENLARGEMENT)
                        measure(name, locale, script, width, scale)
                    action("storage-disclosure-open", ".storage-disclosure > summary", native_key=True)
                    assert cdp.evaluate("document.querySelector('.storage-disclosure').open")
                    action("storage-disclosure-close", ".storage-disclosure > summary")
                action("home-return", "a.brand")

            # One short legal source per family; genuine emitted creation and recording forms.
            mode = "setup"
            record_live_game(browser, play_count=3)
            record_context_match(browser)
            context = server.app_context
            active = context.managed_stateful.active_session
            match = context.managed_stateful.active_match
            saved = {active.path: active.path.read_bytes(), match.path: match.path.read_bytes()}
            for label, path in (("session", active.path), ("match", match.path)):
                evidence["sources"][label] = digest(saved[path])
                (args.output / (label + ".json")).write_bytes(saved[path])
            mode = "native"
            action("home-recorded-review", 'main a[href="/review/recorded"]', native_key=True)
            session_open = 'form[action="/review/open-recording"]:has(input[name="family"][value="sessions"]) button'
            action("same-session-open", session_open, post="/review/open-recording")
            action("execute-saved-decision", 'form[action="/sessions/review-decision"] button', native_key=True, post="/sessions/review-decision")
            result, source = active.execution, active.recorded_review_source
            assert result is not None and source is not None
            downloads = {k: browser.request("GET", f"/sessions/downloads/{k}.json")[2] for k in ("request", "result")}
            for kind, raw in downloads.items():
                evidence["sources"][kind] = digest(raw)
                (args.output / (kind + ".json")).write_bytes(raw)
            for script in (False, True):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                mode = "native"
                action("global-settings", '.site-nav a[href="/settings"]', native_key=True)
                action("add-player-editor", 'form[action="/actions/profile/players/edit"]:has(input[name="player_handle"][value=""]) button', post="/actions/profile/players/edit")
                form = 'form[action="/actions/profile/players/add"]'
                name = f"Synthetic <Player & {int(script)}>"
                type_value(form + ' [name="display_name"]', name)
                type_value(form + ' [name="account_platform"]', "local-club")
                action("settings-validation", form + " button", native_key=True, post="/actions/profile/players/add")
                assert cdp.evaluate("!!document.querySelector('.error-summary')")
                # Retained submitted values survive both native and enhanced language changes.
                for language in ("de", "en"):
                    action("settings-error-language", f'.language-selector button[value="{language}"]', post="/actions/profile/language")
                    assert cdp.evaluate("document.querySelector(" + json.dumps(form + ' [name="display_name"]') + ").value") == name
                    assert cdp.evaluate("location.pathname") == "/settings"
                cdp.screenshot(args.output / f"settings-error-{int(script)}.png", whole=True)
                type_value(form + ' [name="account_id"]', "unsent-account")
                action("settings-unsent-language", '.language-selector button[value="de"]', post="/actions/profile/language")
                assert cdp.evaluate("document.querySelector(" + json.dumps(form + ' [name="account_id"]') + ").value") == ("unsent-account" if script else "")
                action("error-field-link", '.error-summary a[href^="#validation-field-"]', native_key=True)
                type_value(form + ' [name="account_id"]', f"player-{int(script)}")
                action("settings-recovery", form + " button", native_key=True, post="/actions/profile/players/add")
                assert any(p.display_name == name for p in context.frontend_profile.document.known_players)
                action("profile-information-open", ".secondary-action > summary", native_key=True)
                assert cdp.evaluate("document.querySelector('.secondary-action').open")
                action("about-footer", 'footer a[href="/about"]')
                action("home-global", "a.brand")
                action("review-task", 'main a[href="/review/recorded"]', native_key=True)
                action("same-source-review-return", session_open, post="/review/open-recording")
                action("result-language", '.language-selector button[value="de"]', post="/actions/profile/language")
                assert context.managed_stateful.active_session is active
                assert active.execution is result and active.recorded_review_source is source
                assert all(path.read_bytes() == raw for path, raw in saved.items())
                assert all(browser.request("GET", f"/sessions/downloads/{k}.json")[2] == raw for k, raw in downloads.items())
            action("match-home", "a.brand")
            action("match-task", 'main a[href="/matches"]', native_key=True)
            action("existing-match-open", 'form[action="/matches/open"] button', native_key=True, post="/matches/open")
            assert context.managed_stateful.active_match.path.read_bytes() == saved[match.path]
            assert active.execution is result
            assert all(path.read_bytes() == raw for path, raw in saved.items())
            evidence["retention"] = dict(same_session_identity=True, same_result_identity=True,
                same_source_identity=True, product_bytes=True, request_result_download_bytes=True)
            if args.baseline:
                baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
                evidence["comparison"] = []
                # Independent process secrets cannot be equal across installations.
                # Require one exact stable hidden setup token within each run; retain the raw
                # observations and compare every other form field/value without normalization.
                for run in (baseline, evidence):
                    tokens = [f for m in run["measurements"] for form in m["forms"]
                              for f in form["fields"] if f["name"] == "setup_context"]
                    assert len(tokens) == 7
                    assert all(f["type"] == "hidden" and re.fullmatch("[0-9a-f]{64}", f["value"]) for f in tokens)
                    assert len({f["value"] for f in tokens}) == 1

                def form_contract(forms):
                    copied = json.loads(json.dumps(forms))
                    for form in copied:
                        for field in form["fields"]:
                            if field["name"] == "setup_context":
                                field["value"] = "process-local-creation-binding"
                    return copied

                for old, new in zip(baseline["measurements"], evidence["measurements"], strict=True):
                    for key in ("name", "locale", "javascript", "width", "scale"):
                        assert old[key] == new[key], (key, old["name"])
                    assert form_contract(old["forms"]) == form_contract(new["forms"]), old["name"]
                    evidence["comparison"].append(dict(name=new["name"], locale=new["locale"], javascript=new["javascript"], width=new["width"], scale=new["scale"], heights=[old["height"], new["height"]], scroll=[old["scroll"], new["scroll"]]))
                evidence["form_contract_parity"] = "Exact except separately validated independent process-local language/setup bindings"
            assert calls["native:execution"] == 1
            assert not calls["passive:execution"]
            assert not calls["native:session_save"] and not calls["native:match_save"]
            evidence["completed"] = True
    finally:
        evidence["counts"] = dict(calls)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({k: evidence[k] for k in ("completed", "phase", "inventory", "counts")}, indent=2))


if __name__ == "__main__":
    main()
