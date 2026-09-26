# ruff: noqa: E501 - Optional native-browser evidence keeps selectors readable.
"""Bounded #267 independent-Wheel browser evidence, using disposable roots only."""

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
from urllib.parse import parse_qsl
from zipfile import ZipFile

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, focus, keyboard, tab_to
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_creation_details import seed_profile  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from test_settings_reset_presentation import saved_sources  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.server as web  # noqa: E402
import skatmind.app_web.stateful_context as stateful  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.frontend_profile_persistence import (  # noqa: E402
    load_frontend_profile_file_v1,
)
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

START = "082c7fb1997fcba801663577233350436fe9d351"
PREF = 'form[action="/actions/profile/preferences"]'
CREATE = 'form[action="/matches/api/v1/create"]'
OUTER = CREATE + ' > details.advanced-settings'
LANG = 'form[action="/actions/profile/language"]'
FIELD = "advanced_settings_expanded"
MODULES = ("friendly_creation_rendering.py", "profile_settings_rendering.py", "form_registry.py",
    "locales/de.json", "locales/en.json", "assets/app.css", "assets/workflow.js", "templates/app.html",
    "server.py", "settings_forms.py", "profile_player_operations.py", "frontend_profile_operations.py",
    "frontend_profile_contracts.py", "frontend_profile_codec.py", "frontend_profile_persistence.py",
    "player_seat_setup.py", "language_context.py", "language_form_preservation.py", "validation_rendering.py")
MATRIX = ((None, "en", True, 1280, 1), (False, "de", False, 390, 1),
          (True, "en", True, 320, 2), (False, "en", False, 320, 2),
          (True, "de", False, 1280, 1), (None, "de", True, 390, 2))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


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
    evidence = dict(completed=False, phase=args.phase, start=START, head=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), python=sys.version,
        os=platform.platform(), installed=skatmind.__file__, wheel=digest(args.wheel.read_bytes()),
        verifier_sha256=digest(Path(__file__).read_bytes()),
        versions={n: version(n) for n in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        hashes={}, served={}, actions=[], measurements=[], payloads=[], responses=[], profiles=[], sources={})
    assert evidence["inventory"] == [67, 112, 1802 if after else 1805]
    assert tuple(catalogs["en"]) == tuple(catalogs["de"])
    with ZipFile(args.wheel) as wheel:
        for name in MODULES:
            raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
            assert raw == wheel.read("skatmind/app_web/" + name)
            expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if after else
                subprocess.check_output(["git", "show", START + ":src/skatmind/app_web/" + name], cwd=ROOT))
            assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
            evidence["hashes"][name] = digest(raw)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    evidence["worker"] = {"browser_pid": local.process.pid, "profile": str(args.output / "browser-profile")}
    calls, mode, case = Counter(), "fixture", -1
    handler = web.SkatMindAppWebRequestHandlerV1
    real_read, real_send = handler._read_body, handler._send_bytes

    def counted(label, real):
        def call(*a, **kw):
            calls[f"{case}:{mode}:{label}"] += 1
            result = real(*a, **kw)
            if label in {"profile_save", "language"}:
                calls[f"{case}:{mode}:{label}:" + (result if isinstance(result, str) else result.status)] += 1
            return result
        return call

    def read(h, *a, **kw):
        body, kind = real_read(h, *a, **kw)
        evidence["payloads"].append(dict(case=case, mode=mode, route=h.path,
            fields=parse_qsl(body.decode(), keep_blank_values=True)))
        return body, kind

    def send(h, status, raw, **kw):
        evidence["responses"].append(dict(case=case, mode=mode, method=h.command, route=h.path,
            status=int(status), location=dict(kw.get("extra_headers", ())).get("Location")))
        return real_send(h, status, raw, **kw)

    def action(name, selector, *, pointer=False, key="Enter", post=None, status=303):
        start, count, responses = len(evidence["payloads"]), calls.copy(), len(evidence["responses"])
        if pointer:
            pre = focus(cdp)
            click(cdp, selector)
        else:
            tab_to(cdp, selector)
            pre = focus(cdp)
            keyboard(cdp, key, "Space" if key == " " else "Enter", 32 if key == " " else 13,
                     " " if key == " " else "\r")
        for _ in range(200):
            time.sleep(.05)
            if cdp.evaluate("document.readyState==='complete'") and (post is None or len(evidence["payloads"]) > start):
                break
        time.sleep(.25)
        row = dict(case=case, mode=mode, name=name, script=not cdp.script_disabled,
            selector=selector, input="pointer" if pointer else "Tab/" + key, pre=pre, active=focus(cdp),
            url=cdp.evaluate("location.pathname+location.hash"), counts=dict(calls-count),
            active_error=cdp.evaluate("document.activeElement.matches('.error-summary')"),
            posts=evidence["payloads"][start:], responses=evidence["responses"][responses:])
        keyboard(cdp, "Tab", "Tab", 9)
        row["next_tab"] = focus(cdp)
        evidence["actions"].append(row)
        assert [p["route"] for p in row["posts"]] == ([] if post is None else [post]), row
        if post is None:
            assert not row["counts"] and not row["responses"], row
        else:
            assert any(r["method"] == "POST" and r["route"] == post and r["status"] == status
                       for r in row["responses"]), row
        return row

    def fill(name, value):
        selector = '[name="' + name + '"]'
        tab_to(cdp, selector)
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        keyboard(cdp, "Backspace", "Backspace", 8)
        if value:
            cdp.call("Input.insertText", text=value)

    def select(name, steps):
        tab_to(cdp, '[name="' + name + '"]')
        keyboard(cdp, "Home", "Home", 36)
        for _ in range(steps):
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Tab", "Tab", 9)

    def opened():
        return cdp.evaluate("document.querySelector(" + json.dumps(OUTER) + ").open")

    def measure(name, width, scale, *, enlarge=True):
        if scale == 2 and enlarge:
            cdp.evaluate(TEXT_ENLARGEMENT)
        data = cdp.evaluate("""(() => {const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {tag:e.tagName,name:e.name,text:e.innerText,x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontSize,visible:e.checkVisibility()}};
            return {locale:document.documentElement.lang,url:location.pathname,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                details:[...document.querySelectorAll('main details')].map(e=>({summary:e.querySelector('summary').textContent,open:e.open,class:e.className,id:e.id})),
                fields:[...document.querySelectorAll('main input:not([type=hidden]),main select,main button,main summary')].map(box),
                forms:[...document.forms].map(f=>({action:f.getAttribute('action'),fields:[...new FormData(f)].map(([k,v])=>[k,v]),preserve:f.dataset.preserveFields})),
                overflow:[...document.querySelectorAll('main input,main select,main button,main summary,main label')].filter(e=>e.checkVisibility()&&e.getBoundingClientRect().right>innerWidth+1).map(box)};})()""")
        data.update(case=case, name=name, width=width, scale=scale, script=not cdp.script_disabled)
        evidence["measurements"].append(data)
        assert data["client"] == data["scroll"] and not data["overflow"], data
        cdp.screenshot(args.output / f"{case}-{name}.png", whole=True)
        if cdp.evaluate("!!document.querySelector(" + json.dumps(OUTER) + ")"):
            assert not cdp.evaluate("document.querySelector('.local-time-editor').open")
            assert not cdp.evaluate("document.querySelector('.technical-details').open")
            if opened():
                cdp.evaluate("document.querySelector(" + json.dumps(OUTER) + ").scrollIntoView()")
                cdp.screenshot(args.output / f"{case}-{name}-details.png")

    fixture = None
    try:
        with ExitStack() as stack:
            for module, name, label in (
                (profile, "save_frontend_profile_file_v1", "profile_save"),
                (web, "set_frontend_language_v1", "language"),
                (web, "submit_seat_setup_v1", "setup_submit"),
                (web, "prepare_profile_driven_match_creation_v1", "creation_prepare"),
                (web, "create_unified_match_v1", "match_create"),
                (session_files, "save_session_file", "session_save"),
                (capture, "save_match_workspace_file_v1", "match_save"),
                (execution, "execute", "execute"),
                (web, "discover_managed_items_v1", "discovery"),
                (stateful, "discover_managed_items_v1", "discovery")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(handler, "_read_body", read))
            stack.enter_context(patch.object(handler, "_send_bytes", send))
            for case, (stored, locale, script, width, scale) in enumerate(MATRIX):
                mode = "fixture"
                root = args.output / f"case-{case}"
                root.mkdir()
                fixture = localized_server.__wrapped__(root)
                server = next(fixture)
                app = server.app_context
                seed_profile(app, stored)
                browser = Browser(server)
                files, downloads = saved_sources(browser) if case == 2 else ({}, {})
                retained = app.managed_stateful.active_session.execution if case == 2 else None
                evidence["sources"].update({str(p.relative_to(args.output)): dict(bytes=len(raw), sha256=digest(raw)) for p, raw in files.items()})
                evidence["sources"].update({"http:" + route: dict(bytes=len(raw), sha256=digest(raw)) for route, raw in downloads.items()})
                cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                cdp.call("Network.setExtraHTTPHeaders", headers={"Accept-Language": locale})
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
                def snapshot(label, app=app, case=case):
                    path = app.frontend_profile.profile_path
                    raw = path.read_bytes() if path.exists() else None
                    evidence["profiles"].append(dict(case=case, label=label, bytes=None if raw is None else len(raw), sha256=None if raw is None else digest(raw), generation=app.frontend_profile.generation,
                        document=None if app.frontend_profile.document is None else app.frontend_profile.document.to_dict()))
                    return raw
                initial = snapshot("before-passive")
                mode = "passive"
                cdp.navigate(server.origin + "/matches/new")
                assert opened() is (after or bool(stored))
                measure("initial-match", width, scale)
                assert snapshot("after-initial-match") == initial
                cdp.navigate(server.origin + "/settings")
                measure("settings", width, scale)
                assert snapshot("after-passive") == initial
                field = cdp.evaluate("(()=>{const f=document.querySelector(" + json.dumps(PREF) + ");return [...f.elements].filter(e=>e.name==='advanced_settings_expanded').map(e=>({type:e.type,value:e.value,checked:e.checked,visible:e.checkVisibility()}))})()")
                assert len(field) == 1 and field[0]["type"] == ("hidden" if after else "checkbox")
                assert field[0]["value"] == ("on" if stored or not after else "")
                mode = "native-save"
                row = action("noop-settings-save", PREF + " button", post="/actions/profile/preferences")
                assert [v for k, v in row["posts"][0]["fields"] if k == FIELD] == (["on"] if stored else [""] if after else [])
                assert snapshot("after-noop") == initial
                select("platform_choice", 5)  # none, EuroSkat, in-person, other-online, unknown, custom
                fill("custom_platform", "Synthetic browser club")
                action("unrelated-settings-save", PREF + " button", post="/actions/profile/preferences", pointer=True)
                assert app.frontend_profile.document.interface_preferences.advanced_settings_expanded is bool(stored)
                assert app.frontend_profile.document.preferred_game_platform == "Synthetic browser club"
                accepted = snapshot("after-unrelated-save")
                mode = "passive"
                cdp.navigate(server.origin + "/matches/new")
                assert opened() is (after or bool(stored))
                measure("fresh-match", width, scale)
                assert snapshot("after-match-get") == accepted
                mode = "native-toggle"
                if not opened():
                    action("baseline-open", OUTER + " > summary")
                fill("source_title", "Unsent synthetic source")
                action("close", OUTER + " > summary", pointer=True)
                assert not opened()
                action("reopen", OUTER + " > summary", key=" ")
                assert opened() and cdp.evaluate("document.querySelector('[name=source_title]').value") == "Unsent synthetic source"
                action("close-before-language", OUTER + " > summary")
                assert snapshot("after-toggles") == accepted
                mode = "native-language"
                target = "de" if locale == "en" else "en"
                action("closed-language-return", LANG + ' button[value="' + target + '"]', post="/actions/profile/language")
                assert opened() is (False if script else after or bool(stored))
                assert cdp.evaluate("document.querySelector('[name=source_title]').value") == ("Unsent synthetic source" if script else "")
                snapshot("after-language")
                if case in {0, 1}:
                    mode = "native-creation"
                    if not opened():
                        action("open-to-enter", OUTER + " > summary")
                    fill("match_title", "Native synthetic Match")
                    for name, value in (("forehand_name", "Alice"), ("middlehand_name", "Bob"), ("rearhand_name", "Carol")):
                        fill(name, value)
                    select("perspective_seat", 1)
                    fill("source_url", "https://example.invalid/video")
                    select("source_kind", 3)
                    action("close-before-error", OUTER + " > summary")
                    row = action("source-kind-error", CREATE + ' button[value="update"]', post="/matches/api/v1/create", status=400)
                    assert opened()
                    assert row["active_error"]  # Native autofocus also works without script.
                    measure("source-error", width, scale)
                    action("close-error-before-language", OUTER + " > summary")
                    action("error-language-return", LANG + ' button[value="' + locale + '"]', post="/actions/profile/language")
                    assert opened()
                    select("source_kind", 2)
                    row = action("update", CREATE + ' button[value="update"]', post="/matches/api/v1/create")
                    assert row["url"] == "/matches/new" and opened() is (after or bool(stored))
                    if not opened():
                        action("baseline-open-reviewed", OUTER + " > summary")
                    fill("source_title", "Changed after review")
                    action("stale-reviewed-values", CREATE + ' button[value="create"]', post="/matches/api/v1/create", status=400)
                    action("review-again", CREATE + ' button[value="update"]', post="/matches/api/v1/create")
                    measure("reviewed-create", width, scale)
                    row = action("create", CREATE + ' button[value="create"]', post="/matches/api/v1/create")
                    assert row["url"] == "/matches/position/1#match-recording"
                    assert app.managed_stateful.active_match.path.exists()
                    assert app.frontend_profile.document.interface_preferences.advanced_settings_expanded is bool(stored)
                    snapshot("after-create")
                mode = "passive-bytes"
                assert all(p.read_bytes() == raw for p, raw in files.items())
                assert all(browser.request("GET", route)[2] == raw for route, raw in downloads.items())
                if case == 2:
                    assert app.managed_stateful.active_session.execution is retained
                    for route, consent in (("/actions/profile/recommended-defaults/reset", "confirm_recommended_reset"),
                                           ("/actions/profile/reset", "confirm_reset")):
                        mode = "native-reset"
                        cdp.navigate(server.origin + "/settings")
                        reset = 'form[action="' + route + '"]'
                        action("reset-consent", reset + ' input[name="' + consent + '"]', key=" ")
                        action("reset", reset + ' button', post=route)
                        assert app.frontend_profile.document.interface_preferences.advanced_settings_expanded is False
                        snapshot("after-" + consent)
                        mode = "passive-after-reset"
                        cdp.navigate(server.origin + "/matches/new")
                        assert opened() is after
                        assert all(p.read_bytes() == raw for p, raw in files.items())
                        assert all(browser.request("GET", route)[2] == raw for route, raw in downloads.items())
                        assert app.managed_stateful.active_session.execution is retained
                assert load_frontend_profile_file_v1(app.managed_home.root).document == app.frontend_profile.document
                for resource, route in (("app.css", "/assets/app.css"),
                                         ("workflow.js", "/matches/assets/capture.js")):
                    status, _, raw = browser.request("GET", route)
                    assert status == 200 and digest(raw) == evidence["hashes"]["assets/" + resource]
                    evidence["served"][resource] = digest(raw)
                fixture.close()
                fixture = None
            evidence["completed"] = True
    finally:
        evidence["counts"] = dict(calls)
        if fixture is not None:
            fixture.close()
        local.close()
        evidence["browser_exit"] = local.process.poll()
        (args.output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: evidence[k] for k in ("completed", "phase", "inventory", "counts")}, indent=2))


if __name__ == "__main__":
    main()
