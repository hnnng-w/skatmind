# ruff: noqa: E501 - Optional browser observations keep complete expressions together.
"""Issue #268: independent installed Wheels, native input and disposable synthetic roots."""

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
from verify_recording_deletion import click, focus, keyboard, tab_to
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_direct_match_evidence import started  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_session_recorded_review_web import (  # noqa: E402
    Browser,
    Forms,
    record_live_game,
    review_first,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
import skatmind.capture_web.context as capture_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402

MODULES = ("task_first_match_rendering.py", "card_entry_http.py", "form_registry.py", "server.py",
    "validation_rendering.py", "validation_mapping.py", "language_context.py",
    "language_form_preservation.py", "compact_card_rendering.py", "assets/app.css",
    "assets/workflow.js", "locales/en.json", "locales/de.json")


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
    evidence = dict(completed=False, phase=args.phase, python=sys.version,
        versions={name: version(name) for name in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        installed=skatmind.__file__, wheel=digest(args.wheel.read_bytes()), hashes={},
        actions=[], measurements=[], payloads=[], responses=[], sources={},
        inventory=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY),
                   len(load_frontend_translation_catalogs_v1()["en"])],
        limits=["Headless Edge; no physical-device, AT, or maintainer UAT claim.",
                "Doubled computed text is not browser zoom; authenticated downloads are not Save dialogs.",
                "Independent generated identities are not expected to have matching source bytes."])
    assert evidence["inventory"] == ([67, 119, 1811] if after else [67, 112, 1802])
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
    counts, mode = Counter(), "fixture"
    real_read, real_response = Handler._read_body, Handler.send_response

    def counted(label, real):
        def wrapper(*a, **kw):
            counts[mode + ":" + label] += 1
            return real(*a, **kw)
        return wrapper

    def read(handler, *a, **kw):
        result = real_read(handler, *a, **kw)
        evidence["payloads"].append(dict(mode=mode, route=handler.path,
            fields=parse_qsl(result[0].decode(), keep_blank_values=True)))
        return result

    def respond(handler, code, *a, **kw):
        if handler.command == "POST":
            evidence["responses"].append(dict(mode=mode, route=handler.path, status=int(code)))
        return real_response(handler, code, *a, **kw)

    def record(name, callback, *, posts=None):
        before, offset = counts.copy(), len(evidence["payloads"])
        result = callback()
        time.sleep(.12)
        delta = counts - before
        actual = len(evidence["payloads"]) - offset
        if posts is not None:
            assert actual == posts, (name, actual, posts)
        if posts == 0:
            assert all(key.endswith("page_preparation") for key in delta), (name, delta)
        evidence["actions"].append(dict(name=name, mode=mode, operations=dict(delta), posts=actual,
            url=cdp.evaluate("location.pathname+location.hash"), focus=focus(cdp)))
        return result

    def navigate(route):
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + route)

    def activate(selector):
        click(cdp, selector)
        time.sleep(.35)
        cdp.evaluate("void 0")

    def form(prefix, intent="selected"):
        value = prefix + "_" + intent if after else "set_" + prefix
        return 'form[action="/matches/cards"]:has(input[value="' + value + '"])'

    def open_editor(prefix):
        selector = form(prefix)
        summary = cdp.evaluate("(()=>{const s=document.querySelector(" + json.dumps(selector)
            + ").closest('details').querySelector(':scope > summary');if(!s.id)s.id='probe-evidence';return '#'+s.id})()")
        if not cdp.evaluate("document.querySelector(" + json.dumps(summary) + ").parentElement.open"):
            activate(summary)

    def choose_mode(prefix, value):
        selector = form(prefix) + ' select[name="card_evidence_mode"]'
        click(cdp, selector)
        keyboard(cdp, "Escape", "Escape", 27)
        keyboard(cdp, "Home", "Home", 36)
        steps = (2 if prefix == "discarded_cards" else 1) if value == "exact" else int(value == "known_empty")
        for _ in range(steps):
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Enter", "Enter", 13)
        assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").value") == value

    def submit(prefix, intent="selected"):
        selector = form(prefix, intent) + ' button[type="submit"]'
        click(cdp, selector)
        time.sleep(.45)
        cdp.evaluate("void 0")

    def capture(name, selector, *, width=390, scale=1):
        original_scroll = cdp.evaluate("({x:scrollX,y:scrollY})")
        original_focus = focus(cdp)
        # Native viewport slices avoid this Edge build's beyond-viewport screenshot
        # scrollbar removal/reflow. Scroll only; never assign focus in the probe.
        data = cdp.evaluate("""(selector=>{const e=document.querySelector(selector).closest('section'),r=e.getBoundingClientRect();return {
            text:e.innerText,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,
            controls:[...e.querySelectorAll('input:not([type=hidden]),select,button,fieldset')].map(n=>{
                const b=n.getBoundingClientRect();return {tag:n.tagName,name:n.name,value:n.value,type:n.type,
                text:n.innerText,width:b.width,left:b.left,right:b.right,height:b.height,
                font:getComputedStyle(n).fontSize,invalid:n.getAttribute('aria-invalid')}}),
            clip:{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1}}})""" + "(" + json.dumps(selector) + ")")
        data.update(name=name, width=width, scale=scale, locale=cdp.evaluate("document.documentElement.lang"),
                    javascript=not cdp.script_disabled, focus=original_focus)
        assert data["client"] == data["scroll"], data
        clip = data.pop("clip")
        data["screenshots"] = []
        height = cdp.evaluate("innerHeight")
        start = max(0, int(clip["y"]) - 12)
        for part, top in enumerate(range(start, int(clip["y"] + clip["height"]), height - 40)):
            cdp.evaluate(f"window.scrollTo(0,{top})")
            time.sleep(.12)
            shot = cdp.call("Page.captureScreenshot", format="png", captureBeyondViewport=False)
            filename = f"{len(evidence['measurements']):02}-{name}-{data['locale']}-{int(data['javascript'])}-{width}-{scale}-{part}.png"
            (args.output / filename).write_bytes(base64.b64decode(shot["data"]))
            data["screenshots"].append(filename)
        cdp.evaluate(f"window.scrollTo({original_scroll['x']},{original_scroll['y']})")
        keyboard(cdp, "Tab", "Tab", 9)
        data["next_tab"] = focus(cdp)
        evidence["measurements"].append(data)

    def source(name, raw):
        evidence["sources"][name] = dict(bytes=len(raw), sha256=digest(raw))
        (args.output / (name + ".json")).write_bytes(raw)

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_save"),
                (capture_context, "save_match_workspace_file_v1", "match_save"),
                (execution, "execute", "session_analysis"), (analysis, "execute_match_decision_analysis_v1", "match_analysis"),
                (profile, "save_frontend_profile_file_v1", "profile_write"),
                (match_state, "_decision_preparation_summary", "page_preparation")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            stack.enter_context(patch.object(Handler, "_read_body", read))
            stack.enter_context(patch.object(Handler, "send_response", respond))
            browser = Browser(server)
            cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, name in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert digest(browser.request("GET", route)[2]) == evidence["hashes"][name]
            record_live_game(browser, play_count=3)
            review_first(browser)
            session = server.app_context.managed_stateful.active_session
            session_raw, checkpoints = session.path.read_bytes(), session.decision_checkpoints
            source("session", session_raw)
            exports = {kind: browser.request("GET", f"/sessions/downloads/{kind}.json")[2] for kind in ("request", "result")}
            for kind, raw in exports.items():
                source("session-" + kind, raw)
            for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
                mode = "fixture"
                started(browser, locale=locale)
                active = server.app_context.managed_stateful.active_match
                initial = active.path.read_bytes()
                source(f"initial-{locale}-{int(script)}", initial)
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                for prefix, cards in (("perspective_hand", MATCH_HAND), ("original_skat", ("SA", "S7")),
                                      ("discarded_cards", ("SA", "S7"))):
                    mode = "passive"
                    cells = ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)) if locale == "de" and not script else ((390, 844, 1),)
                    selector = form(prefix)
                    for width, height, scale in cells:
                        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
                        record("view-" + prefix, lambda: navigate("/matches/position/1#match-initial-hand"), posts=0)
                        record("open-" + prefix, lambda prefix=prefix: open_editor(prefix), posts=0)
                        if scale == 2:
                            cdp.evaluate(TEXT_ENLARGEMENT)
                        capture("unknown-" + prefix, selector, width=width, scale=scale)
                    cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
                    navigate("/matches/position/1#match-initial-hand")
                    open_editor(prefix)
                    mode = "native"
                    record("one-choice-" + prefix, lambda selector=selector, cards=cards: activate(selector + ' input[value="' + cards[0] + '"]'), posts=0)
                    # Native Space on the clicked checkbox; Enter's actual implicit behavior is recorded.
                    record("space-off-on", lambda: (keyboard(cdp, " ", "Space", 32, " "), keyboard(cdp, " ", "Space", 32, " ")), posts=0)
                    before = active.path.read_bytes()
                    record("save-one-" + prefix, lambda prefix=prefix: submit(prefix), posts=1)
                    assert active.path.read_bytes() == before
                    assert evidence["responses"][-1]["status"] == (400 if after else 303)
                    if not after:
                        open_editor(prefix)
                        record("legacy-mode-prerequisite", lambda prefix=prefix: choose_mode(prefix, "exact"), posts=0)
                        # Unknown mode deliberately discarded the previous checkbox selection.
                        activate(selector + ' input[value="' + cards[0] + '"]')
                        record("legacy-exact-one-rejected", lambda prefix=prefix: submit(prefix), posts=1)
                        assert evidence["responses"][-1]["status"] == 400
                    capture("rejection-" + prefix, selector)
                    # Native language return preserves submitted selections, including without script.
                    other = "en" if locale == "de" else "de"
                    record("language-rejection", lambda other=other: activate(
                        '.language-selector button[value="' + other + '"]'), posts=1)
                    assert cdp.evaluate("document.querySelector(" + json.dumps(selector + ' input[value="' + cards[0] + '"]') + ").checked")
                    record("language-retry-return", lambda locale=locale: activate(
                        '.language-selector button[value="' + locale + '"]'), posts=1)
                    for card in cards[1:]:
                        record("choose-" + card, lambda card=card, selector=selector: activate(selector + ' input[value="' + card + '"]'), posts=0)
                    record("checkbox-enter", lambda: (keyboard(cdp, "Enter", "Enter", 13), time.sleep(.4)))
                    # Checkbox Enter normally does not submit in Edge; if it does, it can only Save.
                    if active.path.read_bytes() == before:
                        tab_to(cdp, selector + ' button[type="submit"]')
                        record("button-enter-save-" + prefix, lambda: (keyboard(cdp, "Enter", "Enter", 13, "\r"), time.sleep(.5)), posts=1)
                    assert active.workspace.slots[0].observed_game.to_dict()[
                        "perspective_initial_hand" if prefix == "perspective_hand" else prefix] is not None
                    assert evidence["responses"][-1]["status"] == 303
                    assert cdp.evaluate("location.hash") == "#match-recording"
                    open_editor(prefix)
                    capture("saved-" + prefix, selector)
                    saved = active.path.read_bytes()
                    for card in cards:
                        activate(selector + ' input[value="' + card + '"]')
                    other = "en" if locale == "de" else "de"
                    record("language-unsent-zero", lambda other=other: activate(
                        '.language-selector button[value="' + other + '"]'), posts=1)
                    checked = cdp.evaluate("[...document.querySelectorAll(" + json.dumps(selector
                        + ' input[name="cards"]:checked') + ")].map(n=>n.value)")
                    assert set(checked) == (set() if script else set(cards)), checked
                    assert active.path.read_bytes() == saved
                    record("language-accepted-return", lambda locale=locale: activate(
                        '.language-selector button[value="' + locale + '"]'), posts=1)
                    navigate("/matches/position/1")
                    open_editor(prefix)
                    record("equal-save", lambda prefix=prefix: submit(prefix), posts=1)
                    assert active.path.read_bytes() == saved
                    open_editor(prefix)
                    record("unsent-deselect", lambda selector=selector, cards=cards: activate(selector + ' input[value="' + cards[0] + '"]'), posts=0)
                    if not after:
                        choose_mode(prefix, "unknown")
                    record("withdraw-" + prefix, lambda prefix=prefix: submit(prefix, "unknown"), posts=1)
                    assert active.workspace.slots[0].observed_game.to_dict()[
                        "perspective_initial_hand" if prefix == "perspective_hand" else prefix] is None
                    if prefix == "discarded_cards":
                        open_editor(prefix)
                        activate(selector + ' input[value="SA"]')
                        if not after:
                            choose_mode(prefix, "known_empty")
                        record("explicit-empty-with-unsent-grid", lambda prefix=prefix: submit(prefix, "empty"), posts=1)
                        assert active.workspace.slots[0].observed_game.discarded_cards == ()
                mode = "fixture"
                started(browser, context="hand", locale=locale)
                mode = "passive"
                navigate("/matches/position/1")
                if after:
                    assert not cdp.evaluate("!!document.querySelector(" + json.dumps(form("discarded_cards")) + ")")
                selector = form("discarded_cards", "empty")
                cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").closest('details').querySelector('summary').id='probe-hand-discard'")
                record("hand-open", lambda: activate("#probe-hand-discard"), posts=0)
                capture("hand-discards", selector)
                mode = "native"
                if not after:
                    choose_mode("discarded_cards", "known_empty")
                record("hand-empty", lambda: submit("discarded_cards", "empty"), posts=1)
                active = server.app_context.managed_stateful.active_match
                before = active.path.read_bytes()
                if after:
                    # Another authorized tab Reloads; the native old action cannot use
                    # a different discriminator to regain the renewed source authority.
                    cdp.evaluate("document.querySelector(" + json.dumps(form("discarded_cards", "unknown"))
                        + ").closest('details').querySelector('summary').id='probe-hand-discard'")
                    activate("#probe-hand-discard")
                    mode = "fixture"
                    page = browser.page("/matches/position/1")
                    reload_form = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/reload")
                    follow(browser, browser.submit(reload_form))
                    mode = "native"
                    record("stale-secondary-after-reload", lambda: submit("discarded_cards", "unknown"), posts=1)
                    assert evidence["responses"][-1]["status"] == 409
                    capture("secondary-conflict", "#match-recording")
                    assert active.path.read_bytes() == before
            mode = "fixture"
            page = record_context_match(browser, with_hand=False)
            active = server.app_context.managed_stateful.active_match
            hand = operation_form(page, "set_perspective_hand")
            # Genuine short Grand context, explicit legacy mode only for the baseline emitted form.
            response = browser.submit(hand, cards=["C7"], **({} if after else {"card_evidence_mode": "exact"}))
            assert response[0] == 400
            page = follow(browser, browser.submit(operation_form(response[2].decode(), "set_perspective_hand"),
                cards=MATCH_HAND, **({} if after else {"card_evidence_mode": "exact"})))
            page = browser.page("/matches/review/1")
            follow(browser, browser.submit(operation_form(page, "analyze_decision")))
            report, = active.capture.report_store.list()
            assert report.value.result.document["position"]["current_trick"] == ("CK",)
            route = f"/matches/api/v1/reports/{report.report_id}.json"
            report_raw = browser.request("GET", route)[2]
            saved = active.path.read_bytes()
            source("grand-match", saved)
            source("grand-report", report_raw)
            mode = "passive"
            for route_view in ("/matches/review/1", "/matches/position/1#match-initial-hand"):
                record("grand-view", lambda route_view=route_view: navigate(route_view), posts=0)
            assert active.path.read_bytes() == saved and browser.request("GET", route)[2] == report_raw
            assert session.path.read_bytes() == session_raw and session.decision_checkpoints == checkpoints
            for kind, raw in exports.items():
                assert browser.request("GET", f"/sessions/downloads/{kind}.json")[2] == raw
            evidence["operation_counts"] = dict(counts)
            evidence["completed"] = True
    finally:
        evidence["operation_counts"] = dict(counts)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({key: evidence[key] for key in ("completed", "inventory", "operation_counts")}, indent=2))


if __name__ == "__main__":
    main()
