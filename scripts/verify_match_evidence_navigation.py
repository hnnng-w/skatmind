# ruff: noqa: E501 - Keep optional browser expressions and evidence records together.
"""Bounded #263 installed-Wheel comparison using existing DevTools and synthetic HTTP fixtures."""

from __future__ import annotations

import argparse
import base64
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
from verify_recording_deletion import click, focus, keyboard
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_game_navigation_web import create_empty  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND, assert_context  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_session_recorded_review_web import Browser, record_live_game, review_first  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.json_transfer import (  # noqa: E402
    canonical_frontend_json_bytes_v1 as canonical,  # noqa: E402
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

HAND = 'form[action="/matches/cards"]:has(input[value="set_perspective_hand"])'
MODULES = ("task_first_match_rendering.py", "match_review_rendering.py", "task_first_match_state.py",
    "match_review_context.py", "compact_card_rendering.py", "card_entry_http.py", "validation_rendering.py",
    "language_context.py", "language_form_preservation.py", "form_registry.py", "assets/app.css",
    "assets/workflow.js", "locales/de.json", "locales/en.json")


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
    evidence = dict(completed=False, phase=args.phase, python=sys.version,
        versions={name: version(name) for name in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        starting_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        installed_module=skatmind.__file__, wheel=digest(args.wheel.read_bytes()), hashes={},
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY), len(catalogs["en"])],
        actions=[], measurements=[], payloads=[], sources={},
        limits=["Headless Edge; no physical-device, screen-reader or maintainer-UAT claim.",
            "200% computed text is not browser zoom. Enlarged target is revisited by native fragment navigation after reflow.",
            "Authenticated HTTP downloads are exact-byte checks, not native Save-dialog tests.",
            "One three-Play independent Session Result; no thirty-Card replay per viewport."])
    assert evidence["inventory"] == [67, 112, 1805 if after else 1802]
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
    calls, mode = Counter(), "fixture"
    real_read = Handler._read_body

    def read_body(handler, *a, **kw):
        result = real_read(handler, *a, **kw)
        evidence["payloads"].append(dict(mode=mode, route=handler.path,
            fields=parse_qsl(result[0].decode(), keep_blank_values=True)))
        return result

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[mode + ":" + label] += 1
            return real(*a, **kw)
        return wrapped

    def record(name, callback, *, passive=False):
        before, posts = calls.copy(), len(evidence["payloads"])
        result = callback()
        delta = calls - before
        if passive:
            assert all(key.endswith("page_preparation") for key in delta), delta
            assert len(evidence["payloads"]) == posts
        evidence["actions"].append(dict(name=name, mode=mode, operations=dict(delta),
            posts=len(evidence["payloads"]) - posts))
        return result

    def navigate(route):
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + route)

    def activate(selector):
        click(cdp, selector)
        time.sleep(.65)
        cdp.evaluate("void 0")

    def choose(value):
        select = HAND + ' select[name="card_evidence_mode"]'
        click(cdp, select)
        keyboard(cdp, "Escape", "Escape", 27)
        keyboard(cdp, "Home", "Home", 36)
        if value == "exact":
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Enter", "Enter", 13)
        assert cdp.evaluate("document.querySelector(" + json.dumps(select) + ").value") == value

    def identify_summary():
        return cdp.evaluate("(()=>{const s=document.querySelector(" + json.dumps(HAND) + ").closest('details').querySelector(':scope > summary');if(!s.id)s.id='probe-old-hand';return '#'+s.id})()")

    def inspect(name, selector, width, scale, *, target=False):
        data = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),r=e.getBoundingClientRect();
            const box=n=>{const b=n.getBoundingClientRect();return {text:n.innerText,left:b.left,right:b.right,width:b.width,height:b.height,font:getComputedStyle(n).fontSize}};
            return {url:location.pathname+location.hash,tag:e.tagName,id:e.id,text:e.innerText,top:r.top,bottom:r.bottom,
                visible:e.checkVisibility(),open:e.closest('details')?.open??null,
                client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
                unique_ids:new Set([...document.querySelectorAll('[id]')].map(n=>n.id)).size===document.querySelectorAll('[id]').length,
                controls:[...e.closest('details,section,main').querySelectorAll('.compact-card,select,button,[aria-invalid=true]')].filter(n=>n.checkVisibility()).map(box)};})""" + "(" + json.dumps(selector) + ")")
        data.update(name=name, width=width, scale=scale, locale=cdp.evaluate("document.documentElement.lang"),
                    javascript=not cdp.script_disabled, focus=focus(cdp))
        assert data["unique_ids"] and data["client"] == data["scroll"], data
        if target:
            assert data["visible"] and 0 <= data["top"] < cdp.evaluate("innerHeight"), data
        basename = f"{name}-{data['locale']}-{int(data['javascript'])}-{width}-{scale}"
        cdp.screenshot(args.output / (basename + ".png"))
        if name == "editor":
            clip = cdp.evaluate("(()=>{const r=document.querySelector(" + json.dumps(selector) + ").closest('details').getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}})()")
            shot = cdp.call("Page.captureScreenshot", format="png", captureBeyondViewport=True, clip=clip)
            (args.output / (basename + "-complete.png")).write_bytes(base64.b64decode(shot["data"]))
        keyboard(cdp, "Tab", "Tab", 9)
        data["next_tab"] = focus(cdp)
        evidence["measurements"].append(data)
        return data

    def source(name, raw):
        evidence["sources"][name] = digest(raw)
        (args.output / (name + ".json")).write_bytes(raw)

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_save"),
                (capture, "save_match_workspace_file_v1", "match_save"),
                (execution, "execute", "session_analysis"),
                (analysis, "execute_match_decision_analysis_v1", "match_analysis"),
                (profile, "save_frontend_profile_file_v1", "profile_write"),
                (match_state, "_decision_preparation_summary", "page_preparation")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read_body))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert digest(browser.request("GET", route)[2]) == evidence["hashes"][resource]
            record_live_game(browser, play_count=3)
            review_first(browser)
            session = server.app_context.managed_stateful.active_session
            session_raw, checkpoints = session.path.read_bytes(), session.decision_checkpoints
            source("session", session_raw)
            session_exports = {kind: browser.request("GET", f"/sessions/downloads/{kind}.json")[2] for kind in ("request", "result")}
            for kind, raw in session_exports.items():
                source("session-" + kind, raw)
            for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
                mode = "fixture"
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                page = create_empty(browser, locale)
                mode = "passive"
                for kind, position in (("empty", 1), ("passed", 2)):
                    if kind == "passed":
                        mode = "fixture"
                        page = browser.page("/matches/position/2")
                        follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
                        mode = "passive"
                    record(kind, lambda position=position: navigate(f"/matches/position/{position}#match-recording"), passive=True)
                    assert cdp.evaluate("!!document.querySelector('#match-evidence')") == (not after)
                    cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
                    inspect(kind, "#match-recording", 390, 1)
                mode = "fixture"
                record_context_match(browser, names=("B", "C Synthetic Long-Player-Name", "A"), with_hand=False)
                active = server.app_context.managed_stateful.active_match
                initial = active.path.read_bytes()
                source(f"match-before-{locale}-{int(script)}", initial)
                mode = "passive"
                cells = ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)) if locale == "de" and not script else ((390, 844, 1),)
                for width, height, scale in cells:
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
                    record("review-before", lambda: navigate("/matches/review/1"), passive=True)
                    link = 'a[href="/matches/position/1#match-initial-hand"]'
                    found = cdp.evaluate("!!document.querySelector(" + json.dumps(link) + ")")
                    assert found == after
                    if not found:
                        link = 'a[href="/matches/position/1#match-recording"]'
                    record("native-remedy" if after else "baseline-generic-return", lambda link=link: activate(link), passive=True)
                    summary = identify_summary()
                    if scale == 2:
                        cdp.evaluate(TEXT_ENLARGEMENT)
                        # Revisit the real emitted href after computed-font reflow, via native link activation.
                        if after:
                            cdp.evaluate("document.querySelector(" + json.dumps(link) + ").closest('details').querySelector('summary').id='probe-analysis'")
                            activate("#probe-analysis")
                        record("native-enlarged-fragment", lambda link=link: activate(link if after else 'a[href="#match-recording"]'), passive=True)
                    inspect("arrival", summary if after else "#match-recording", width, scale, target=True)
                    opened = cdp.evaluate("document.querySelector(" + json.dumps(summary) + ").parentElement.open")
                    if not opened:
                        record("native-summary-opening", lambda summary=summary: activate(summary), passive=True)
                    assert cdp.evaluate("document.querySelector(" + json.dumps(HAND) + ").checkVisibility()")
                    inspect("editor", summary, width, scale)
                    assert cdp.evaluate("[...document.querySelectorAll(" + json.dumps(HAND + ' input[name="cards"]') + ")].length") == 32
                    assert active.path.read_bytes() == initial
                # Reload normal text, follow the real remedy again, then use native controls only.
                cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
                record("review-before-save", lambda: navigate("/matches/review/1"), passive=True)
                record("return-before-save", lambda link=link: activate(link), passive=True)
                summary = identify_summary()
                record("open-before-save", lambda summary=summary: activate(summary), passive=True)
                mode = "native"
                record("mode-exact", lambda: choose("exact"))
                record("select-C7", lambda: activate(HAND + ' input[value="C7"]'))
                before = active.path.read_bytes()
                record("reject-one-card", lambda: activate(HAND + " button"))
                assert cdp.evaluate("!!document.querySelector('.error-summary')")
                assert active.path.read_bytes() == before
                inspect("rejection", ".error-summary", 390, 1)
                record("error-language", lambda locale=locale: activate(f'form.language-selector button[value="{"en" if locale == "de" else "de"}"]'))
                assert cdp.evaluate("[...document.querySelectorAll(" + json.dumps(HAND + ' input[name="cards"]:checked') + ")].map(e=>e.value)") == ["C7"]
                inspect("error-language", ".error-summary", 390, 1)
                # Unsent choices/disclosures survive only the existing enhanced language path.
                record("unsent-C8", lambda: activate(HAND + ' input[value="C8"]'))
                record("return-language", lambda locale=locale: activate(f'form.language-selector button[value="{locale}"]'))
                selected = cdp.evaluate("[...document.querySelectorAll(" + json.dumps(HAND + ' input[name="cards"]:checked') + ")].map(e=>e.value)")
                assert set(selected) == ({"C7", "C8"} if script else {"C7"})
                for card in MATCH_HAND:
                    if card not in selected:
                        record("select-" + card, lambda card=card: activate(HAND + f' input[value="{card}"]'))
                assert active.path.read_bytes() == before
                record("save-ten-cards", lambda: activate(HAND + " button"))
                assert cdp.evaluate("location.pathname+location.hash") == "/matches/position/1#match-recording"
                assert active.workspace.slots[0].observed_game.perspective_initial_hand == MATCH_HAND
                assert not active.capture.report_store.list()
                mode = "passive"
                record("native-review", lambda: activate('#match-recording a[href="/matches/review/1"]'), passive=True)
                assert ("1 von 3" if locale == "de" else "1 of 3") in cdp.evaluate("document.body.innerText")
                assert not cdp.evaluate("!!document.querySelector('a[href$=\"#match-initial-hand\"]')")
                mode = "native"
                record("explicit-C-analysis", lambda: activate('form:has(input[value="analyze_decision"]) button'))
                report, = active.capture.report_store.list()
                assert report.value.result.document["position"]["hand"] == MATCH_HAND
                assert report.value.result.document["position"]["current_trick"] == ("CK",)
                assert_context(cdp.evaluate("document.documentElement.outerHTML"), locale, hand=MATCH_HAND,
                    prefix=(("B", "CK"),), actor="C Synthetic Long-Player-Name", trick=1, play=2, game=1)
                route = f"/matches/api/v1/reports/{report.report_id}.json"
                saved, retained = active.path.read_bytes(), canonical(report.to_dict())
                downloaded = browser.request("GET", route)[2]
                for name, raw in (("match", saved), ("report", retained), ("download", downloaded),
                                  ("match-request", canonical(report.value.request.to_dict()))):
                    source(f"{name}-{locale}-{int(script)}", raw)
                mode = "passive"
                for path in ("/matches/review/1", "/matches/position/1#match-initial-hand", f"/matches/reports/{report.report_id}"):
                    record("retained-view", lambda path=path: navigate(path), passive=True)
                    assert active.path.read_bytes() == saved and canonical(report.to_dict()) == retained
                    assert browser.request("GET", route)[2] == downloaded
                mode = "native"
                for language in ("en" if locale == "de" else "de", locale):
                    record("retained-language", lambda language=language: activate(f'form.language-selector button[value="{language}"]'))
                    assert active.path.read_bytes() == saved and canonical(report.to_dict()) == retained
                    assert browser.request("GET", route)[2] == downloaded
                mode = "passive"
                assert session.path.read_bytes() == session_raw and session.decision_checkpoints == checkpoints
                for kind, raw in session_exports.items():
                    assert browser.request("GET", f"/sessions/downloads/{kind}.json")[2] == raw
                source(f"checkpoint-parity-{locale}-{int(script)}", canonical([c.to_dict() for c in checkpoints]))
            evidence["counts"] = dict(calls)
            evidence["completed"] = True
    finally:
        evidence["counts"] = dict(calls)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=True), encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({"completed": evidence["completed"], "measurements": len(evidence["measurements"]),
        "actions": len(evidence["actions"]), "counts": dict(calls), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
