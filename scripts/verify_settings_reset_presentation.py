# ruff: noqa: E501 - Optional native-browser evidence keeps selectors readable.
"""Bounded #266 baseline/repaired Wheel evidence in fresh synthetic roots only."""

from __future__ import annotations

import argparse
import base64
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402
from test_settings_reset_presentation import (  # noqa: E402
    CONSENT,
    FULL,
    RECOMMENDED,
    SCOPE,
    populate_profile,
    saved_sources,
)

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
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1  # noqa: E402
from skatmind.app_web.frontend_profile_persistence import (  # noqa: E402
    load_frontend_profile_file_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1  # noqa: E402
from skatmind.app_web.profile_player_contracts import ManagedItemDisplayLabelV1  # noqa: E402
from skatmind.app_web.profile_player_operations import (  # noqa: E402
    set_managed_item_display_label_v1,
)
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

MODULES = ("rendering.py", "profile_settings_rendering.py", "locales/de.json", "locales/en.json",
    "assets/app.css", "assets/workflow.js", "templates/app.html", "server.py", "form_registry.py",
    "frontend_profile_operations.py", "frontend_profile_codec.py", "frontend_profile_state.py",
    "frontend_profile_persistence.py", "frontend_profile_contracts.py", "settings_forms.py",
    "language_context.py", "language_form_preservation.py", "player_seat_setup.py")


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
    evidence = dict(completed=False, phase=args.phase, python=sys.version, os=platform.platform(),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        installed=skatmind.__file__, wheel=digest(args.wheel.read_bytes()),
        versions={n: version(n) for n in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        hashes={}, served={}, actions=[], measurements=[], payloads=[], responses=[], sources={}, profiles=[])
    assert evidence["inventory"] == [67, 112, 1805]
    with ZipFile(args.wheel) as wheel:
        for name in MODULES:
            raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
            assert raw == wheel.read("skatmind/app_web/" + name)
            expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if after else
                subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
            assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
            evidence["hashes"][name] = digest(raw)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, mode = Counter(), "fixture"
    Handler = web.SkatMindAppWebRequestHandlerV1
    read_body, send_bytes = Handler._read_body, Handler._send_bytes

    def counted(label, real):
        def call(*a, **kw):
            calls[mode + ":" + label] += 1
            try:
                result = real(*a, **kw)
            except Exception:
                calls[mode + ":" + label + ":rejected"] += 1
                raise
            if label in {"profile_save", "recommended", "full", "language"}:
                calls[mode + ":" + label + ":" + (result if isinstance(result, str) else result.status)] += 1
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

    def action(name, selector, *, key="Enter", pointer=False, post=None):
        before, start = calls.copy(), len(evidence["payloads"])
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
        row = dict(name=name, mode=mode, script=not cdp.script_disabled, selector=selector,
            input="pointer" if pointer else "Tab/" + key, pre=pre, active=focus(cdp),
            url=cdp.evaluate("location.pathname+location.hash"), locale=cdp.evaluate("document.documentElement.lang"),
            counts=dict(calls - before), posts=evidence["payloads"][start:])
        keyboard(cdp, "Tab", "Tab", 9)
        row["next_tab"] = focus(cdp)
        evidence["actions"].append(row)
        assert [p["route"] for p in row["posts"]] == ([] if post is None else [post]), row
        if post is None:
            assert not row["counts"], row
        return row

    def measure(name, width, scale, *, invalid=False):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900,
                 deviceScaleFactor=1, mobile=False)
        cdp.navigate(server.origin + "/settings")
        if scale == 2:
            cdp.evaluate(TEXT_ENLARGEMENT)
        time.sleep(.2)
        data = cdp.evaluate("""(() => {const box=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {text:e.innerText,x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontSize,visible:e.checkVisibility()}};
            return {locale:document.documentElement.lang,url:location.pathname,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                headings:[...document.querySelectorAll('main h2,main h3')].map(box),
                warnings:[...document.querySelectorAll('.reset-form p,.reset-form label,#recommended-reset-heading~p,#recommended-reset-heading~form label,.profile-warning')].map(box),
                grouped:!!document.querySelector('[aria-labelledby="settings-reset-heading"]'),
                order:[...document.querySelectorAll('.secondary-action,form[action*="/reset"]')].map(e=>e.getAttribute('action')||'profile-information'),
                forms:[...document.forms].map(f=>({action:f.getAttribute('action'),fields:[...f.elements].map(e=>({tag:e.tagName,name:e.name,type:e.type,value:e.name==='_frontend_language_context'?'process-local':e.value,checked:e.checked,required:e.required}))})),
                overflow:[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility()&&e.getBoundingClientRect().right>innerWidth+1).map(box)};})()""")
        data.update(name=name, script=not cdp.script_disabled, width=width, scale=scale, invalid=invalid)
        assert data["grouped"] is after
        assert data["order"] == (["profile-information", FULL] if invalid else
            ["profile-information", RECOMMENDED, FULL] if after else
            [RECOMMENDED, "profile-information", FULL])
        if after:
            if not invalid:
                for statement in SCOPE[data["locale"]]:
                    assert any(statement in item["text"] for item in data["warnings"])
            assert data["client"] == data["scroll"] and not data["overflow"], data
        evidence["measurements"].append(data)
        cdp.screenshot(args.output / f"{name}-{data['locale']}-{int(data['script'])}-{width}-{scale}.png", whole=True)
        if name == "populated" and width == 320 and scale == 2:
            # Full-page thumbnails cannot show the enlarged warning text legibly.
            # Retain readable vertical slices of the complete lower reset area.
            start = cdp.evaluate("document.querySelector('#recommended-reset-heading').getBoundingClientRect().top+scrollY")
            end = cdp.evaluate("document.querySelector('footer').getBoundingClientRect().top+scrollY")
            for index, y in enumerate(range(int(start), int(end), 1000)):
                shot = cdp.call("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                    clip={"x": 0, "y": y, "width": width, "height": min(1000, end-y), "scale": 1})
                (args.output / f"enlarged-reset-{index}.png").write_bytes(base64.b64decode(shot["data"]))

    fixture = None
    try:
        with ExitStack() as stack:
            for module, name, label in (
                (profile, "save_frontend_profile_file_v1", "profile_save"),
                (web, "reset_frontend_recommended_defaults_v1", "recommended"),
                (web, "reset_frontend_profile_v1", "full"),
                (web, "set_frontend_language_v1", "language"),
                (session_files, "save_session_file", "session_save"),
                (capture, "save_match_workspace_file_v1", "match_save"),
                (execution, "execute", "execute"),
                (web, "discover_managed_items_v1", "discovery"),
                (stateful, "discover_managed_items_v1", "discovery")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read))
            stack.enter_context(patch.object(Handler, "_send_bytes", send))
            fixture = localized_server.__wrapped__(args.output)
            server = next(fixture)
            browser = Browser(server)
            files, downloads = saved_sources(browser)
            app = server.app_context
            active = app.managed_stateful.active_session
            retained, source = active.execution, active.recorded_review_source
            populate_profile(browser)
            set_managed_item_display_label_v1(app, label=ManagedItemDisplayLabelV1(
                "matches", app.managed_stateful.active_match.workspace.match_definition.match_id,
                "Synthetic dated recording", "2026-09-02"),
                expected_generation=app.frontend_profile.generation)
            for path, raw in files.items():
                evidence["sources"][str(path.relative_to(args.output))] = digest(raw)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.call("Network.setExtraHTTPHeaders", headers={"Accept-Language": "en"})
            cdp.navigate(server.origin + "/settings")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                raw = browser.request("GET", route)[2]
                assert digest(raw) == evidence["hashes"][resource]
                evidence["served"][route] = digest(raw)
            for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                mode = "matrix-language"
                action("matrix-language", f'.language-selector button[value="{locale}"]', pointer=True, post="/actions/profile/language")
                mode = "passive"
                for width, scale in (((1365, 1), (390, 1), (320, 1), (320, 2)) if (locale, script) == ("de", False) else ((390, 1),)):
                    measure("populated", width, scale)
            for script in (False, True):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                if script:
                    mode = "fixture-refill"
                    populate_profile(browser)
                mode = "native"
                measure("before-actions", 390, 1)
                action("ordinary-save-enter", 'form[action="/actions/profile/preferences"] input[name="custom_platform"]', post="/actions/profile/preferences")
                action("profile-information", ".secondary-action > summary")
                for route, consent in CONSENT.items():
                    form = f'form[action="{route}"]'
                    row = action("unchecked-blocked", form + " button")
                    assert row["active"]["name"] == consent and row["next_tab"]["tag"] == "BUTTON"
                    assert not cdp.evaluate(f"document.querySelector({json.dumps(form+' input[type=checkbox]')}).checked")
                    cdp.screenshot(args.output / f"blocked-{consent}-{int(script)}.png")
                    action("check-only", form + " input[type=checkbox]", key=" ")
                    assert cdp.evaluate(f"document.querySelector({json.dumps(form+' input[type=checkbox]')}).checked")
                action("language-clears-both-consents", '.language-selector button[value="en"]', pointer=True, post="/actions/profile/language")
                assert not cdp.evaluate("[...document.querySelectorAll('form[action$=\"/reset\"] input[type=checkbox]')].some(e=>e.checked)")
                assert cdp.evaluate("location.pathname") == "/settings"
                # Competing genuine language action advances the profile; old browser form stays stale.
                mode = "competing-language"
                assert browser.submit(Forms(browser.page("/settings")).find("/actions/profile/language"), language="de")[0] == 303
                browser.page("/settings")  # Complete the competing client's genuine PRG.
                mode = "native"
                form = f'form[action="{RECOMMENDED}"]'
                action("stale-check", form + " input[type=checkbox]", key=" ")
                row = action("stale-reset", form + " button", post=RECOMMENDED)
                assert evidence["responses"][-1]["status"] in (200, 409)
                assert cdp.evaluate("!!document.querySelector('.error-summary')")
                assert row["url"] == RECOMMENDED
                cdp.screenshot(args.output / f"stale-error-{int(script)}.png", whole=True)
                row = action("error-target", '.error-summary a[href^="#validation-form-heading-"]')
                assert row["url"] == RECOMMENDED + row["pre"]["href"]
                assert row["next_tab"]["name"] == "confirm_recommended_reset"
                cdp.screenshot(args.output / f"error-target-{int(script)}.png")
                # Native remedy reaches the semantic Settings URL, not a scripted submit.
                action("error-return", '.site-nav a[href="/settings"]', pointer=True)
                for route, consent in CONSENT.items():
                    before = app.frontend_profile.document
                    evidence["profiles"].append(dict(stage="before-"+consent, data=before.to_dict(), sha256=digest(app.frontend_profile.profile_path.read_bytes())))
                    form = f'form[action="{route}"]'
                    action("explicit-consent", form + " input[type=checkbox]", key=" ")
                    row = action("explicit-reset", form + " button", pointer=route == FULL, post=route)
                    assert row["url"] == "/settings"
                    current = app.frontend_profile.document
                    assert current.revision == before.revision + 1
                    assert load_frontend_profile_file_v1(app.managed_home.root).document == current
                    if route == RECOMMENDED:
                        assert current.language == "de" and current.known_players == before.known_players
                        assert current.own_player_id == before.own_player_id
                        assert current.interface_preferences.time_zone == "America/New_York"
                        assert current.managed_item_display_labels == before.managed_item_display_labels
                        assert current.preferred_perspective_player_id is None and current.preferred_game_platform is None
                        assert current.interface_preferences.advanced_settings_expanded is False
                        raw = app.frontend_profile.profile_path.read_bytes()
                        action("noop-consent", form + " input[type=checkbox]", key=" ")
                        action("recommended-noop", form + " button", post=route)
                        assert app.frontend_profile.profile_path.read_bytes() == raw
                    else:
                        assert current == build_local_frontend_profile_v1(revision=current.revision)
                        assert row["locale"] == "en"  # Browser fallback, no old-locale rewrite.
                    evidence["profiles"].append(dict(stage="after-"+consent, data=current.to_dict(), sha256=digest(app.frontend_profile.profile_path.read_bytes())))
                    assert active.execution is retained and active.recorded_review_source is source
                    assert all(path.read_bytes() == raw for path, raw in files.items())
                    assert all(browser.request("GET", route)[2] == raw for route, raw in downloads.items())
                measure("after-full", 390, 1)
            assert all(path.read_bytes() == raw for path, raw in files.items())
            fixture.close()
            fixture = None
            # Controlled invalid fixture; the normal Settings forms never become eligible here.
            invalid_root = args.output / "invalid"
            invalid_root.mkdir()
            home = prepare_managed_home_v1(invalid_root / "managed")
            invalid_path = home.root / "frontend-profile.json"
            invalid_path.write_bytes(b"controlled invalid synthetic profile\n")
            mode = "invalid-fixture"
            fixture = localized_server.__wrapped__(invalid_root)
            server = next(fixture)
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.call("Network.setExtraHTTPHeaders", headers={"Accept-Language": "de"})
            for script, width, scale in ((False, 320, 2), (True, 390, 1)):
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                mode = "invalid-passive"
                measure("invalid", width, scale, invalid=True)
                assert RECOMMENDED not in cdp.evaluate("document.documentElement.outerHTML")
                assert cdp.evaluate("document.documentElement.lang") == "en"
            mode = "invalid-native"
            form = f'form[action="{FULL}"]'
            action("invalid-unchecked-blocked", form + " button")
            action("invalid-explicit-consent", form + " input[type=checkbox]", key=" ")
            row = action("invalid-recovery", form + " button", post=FULL)
            assert row["url"] == "/settings" and row["locale"] == "de"
            assert load_frontend_profile_file_v1(home.root).document == build_local_frontend_profile_v1()
            if args.baseline:
                baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
                old = [r for r in baseline["measurements"] if r["name"] == "populated"]
                new = [r for r in evidence["measurements"] if r["name"] == "populated"]
                assert len(old) == len(new)
                def form_shape(forms):
                    # Generated Player handles differ between independent installations.
                    # Keep their repeated identity pattern; raw values remain in evidence.
                    copied = json.loads(json.dumps(forms))
                    handles = {}
                    for form in copied:
                        for field in form["fields"]:
                            if field["name"] in {"player_handle", "own_player_handle"} and field["value"]:
                                value = field["value"]
                                assert len(value) == 64 and all(c in "0123456789abcdef" for c in value)
                                field["value"] = handles.setdefault(value, f"player-{len(handles)}")
                    return copied
                for left, right in zip(old, new, strict=True):
                    assert form_shape(left["forms"]) == form_shape(right["forms"])
                evidence["baseline_form_parity"] = len(new)
            evidence["completed"] = True
    finally:
        evidence["counts"] = dict(calls)
        (args.output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        if fixture is not None:
            fixture.close()
        local.close()
    print(json.dumps({k: evidence[k] for k in ("completed", "phase", "inventory", "counts")}, indent=2))


if __name__ == "__main__":
    main()
