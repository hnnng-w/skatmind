# ruff: noqa: E501 - Keep native browser expressions and evidence selectors legible.
"""Optional #249 independent-Wheel native verification; disposable data, no browser dependency."""
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
from urllib.parse import parse_qsl

from _workflow_visual_browser import LocalBrowser
from verify_card_presentation import MEASURE as CARD_MEASURE
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context import MATCH_HAND  # noqa: E402
from test_recorded_party_presentation import (  # noqa: E402
    assert_match_cards,
    assert_party_score,
    corrected_match_setup,
)
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile_operations  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.match_workspace_persistence import load_match_workspace_file_v1  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

PREFIX = "/matches/recovery/"
PREVIEW = 'form[action="/matches/recovery/preview"]'
APPLY = 'form[action="/matches/recovery/apply"]'
CANCEL = 'form[action="/matches/recovery/cancel"]'
ENTRY = '#match-play-3 form[action="/matches/recovery/select"]'


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
        "limitations": ["Synthetic headless Edge, emulated viewports and doubled text; no AT, physical device or maintainer UAT.",
            "Known narrow analysis-table limit is separate. Bounded viewport/state matrix, not every flow at every size.",
            "CAS, expired/foreign tokens and persistence faults are focused automated tests, not browser fault injections."]}
    for name in ("compact_card_rendering.py", "task_first_rendering.py", "match_recovery_rendering.py",
        "match_recovery.py", "match_recovery_http.py", "validation_rendering.py", "form_registry.py",
        "language_form_preservation.py", "task_first_match_state.py", "assets/app.css", "assets/workflow.js",
        "locales/en.json", "locales/de.json"):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if after else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
        if name.startswith("locales/"):
            evidence.setdefault("catalog_counts", {})[name] = len(json.loads(raw))
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, requests, payloads = Counter(), Counter(), []

    def counted(label, real):
        def wrapper(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapper

    def request_count(method, real):
        def wrapper(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return wrapper

    real_read = Handler._read_body
    def read_body(handler, *a, **kw):
        result = real_read(handler, *a, **kw)
        payloads.append({"route": handler.path, "fields": parse_qsl(result[0].decode(), keep_blank_values=True)})
        return result

    def navigate(path, script):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def key(name, number):
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=name, windowsVirtualKeyCode=number)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=name, windowsVirtualKeyCode=number)

    def click(selector):
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)

    def action(selector, route=None, *, keyboard=False):
        before, work, start = requests.copy(), calls.copy(), len(payloads)
        if keyboard == "space":
            cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").focus()")
            key(" ", 32)
        elif keyboard:
            cdp.activate(selector)
        else:
            click(selector)
        time.sleep(.25 if route else .03)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (route is None or requests["POST " + route] > before["POST " + route]):
                break
            time.sleep(.1)
        delta = requests - before
        assert sum(n for p, n in delta.items() if p.startswith("POST ")) == int(route is not None), (selector, delta)
        submitted = payloads[start:]
        assert len(submitted) == int(route is not None)
        if submitted:
            fields = submitted[0]["fields"]
            names = [k for k, _ in fields]
            assert ([(k, v) for k, v in fields if k == "confirm_apply"] == [("confirm_apply", "on")]) == (route == PREFIX + "apply")
            if route == PREFIX + "preview":
                assert names.count("card") == 1 and "cards" not in names and "card_selection" not in names
            if route.startswith(PREFIX):
                assert set(names) == {"managed_handle", "_frontend_form_instance", *({"recovery_selection", "card"} if route.endswith("preview") else
                    {"recovery_selection", "confirm_apply"} if route.endswith("apply") else {"recovery_selection"} if route.endswith("select") else set())}
            if route == "/actions/profile/language":
                for name, raw in fields:
                    if name == "_frontend_language_values":
                        assert all("confirm_apply" not in f["values"] for f in json.loads(raw)["forms"])
        evidence["actions"].append({"selector": selector, "keyboard": keyboard, "javascript": not cdp.script_disabled,
            "requests": dict(delta), "calls": dict(calls-work), "submitted": submitted,
            "focus": cdp.evaluate("document.activeElement.id"), "fragment": cdp.evaluate("location.hash")})

    def choose(card):
        if after:
            action(PREVIEW + ' label:has(input[value="' + card + '"])')
        else:
            before = len(payloads)
            selector = PREVIEW + ' select[name="card"]'
            options = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].map(e=>e.value)")
            click(selector)
            key("Escape", 27)
            key("Home", 36)
            for _ in range(options.index(card)):
                key("ArrowDown", 40)
            key("Enter", 13)
            assert len(payloads) == before
        assert choice() == card

    def choice():
        return cdp.evaluate("document.querySelector(" + json.dumps(PREVIEW + (' input[name="card"]:checked' if after else ' select[name="card"]')) + ")?.value")

    def photo(stem, selector="#match-recovery"):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});scrollBy(0,-20)")
        cdp.screenshot(args.output / (stem + ".png"))

    def measure(state, locale, script, width=1365, scale=1):
        row = cdp.evaluate(CARD_MEASURE)
        recovery = cdp.evaluate("(()=>{const r=document.querySelector('#match-recovery');return {text:r.innerText, forms:[...r.querySelectorAll('form')].map(f=>({action:f.getAttribute('action'),preserve:f.dataset.preserveFields, controls:[...f.elements].map(e=>({tag:e.tagName,type:e.type,name:e.name,value:e.value,checked:e.checked,required:e.required})),buttons:[...f.querySelectorAll('button')].map(e=>{const b=e.getBoundingClientRect();return {text:e.innerText,x:b.x,y:b.y,width:b.width,height:b.height,outline:getComputedStyle(e).outline}})}))}})()")
        row.update(state=state, locale=locale, javascript=script, width=width, text_scale=scale, recovery=recovery)
        evidence["pages"].append(row)
        if after:
            assert row["page"] == row["client"], (state, width, scale)
            for palette in row["palettes"]:
                assert len({c["box"]["width"] for c in palette["cards"]}) <= 1
                assert all(c["complete"] and c["box"]["height"] >= 44 for c in palette["cards"])
        photo(f"{state}-{locale}-{int(script)}-{width}-{scale}")
        if after:
            photo(f"{state}-{locale}-{int(script)}-{width}-{scale}-actions", '#match-recovery .recovery-primary-actions button.primary')
        if state == "selection" and after and scale == 2:
            photo(f"{state}-{locale}-{int(script)}-{width}-{scale}-faces", PREVIEW + ' .compact-card-group:has(input[value="H10"])')

    def responsive(state, locale, script):
        source = server.app_context.managed_stateful.active_match
        raw, work = source.path.read_bytes(), calls.copy()
        cells = ((1365, 1), (390, 1), (320, 1), (320, 2)) if locale == "de" and not script else ((390, 1),)
        for width, scale in cells:
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844, deviceScaleFactor=1, mobile=False)
            navigate("/matches/position/1", script)
            if scale == 2:
                cdp.evaluate(TEXT_ENLARGEMENT)
            measure(state, locale, script, width, scale)
        assert source.path.read_bytes() == raw
        assert all(calls[k] == work[k] for k in ("match_saves", "session_saves", "match_executions", "session_executions"))
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
        navigate("/matches/position/1", script)

    def apply(*, keyboard=False):
        if not after:
            action(APPLY + ' input[name="confirm_apply"]')
        action(APPLY + ' button', PREFIX + "apply", keyboard=keyboard)

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"),
                (execution, "execute", "session_executions"), (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves"),
                (match_state, "_decision_preparation_summary", "match_page_preparations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_"+method, request_count(method, getattr(Handler, "do_"+method))))
            stack.enter_context(patch.object(Handler, "_read_body", read_body))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert digest(client.request("GET", route)[2]) == evidence["hashes"][resource]
            # Unrelated genuine SJ Result using the approved #246/#247 exact prefix/suffix.
            plays = record_score_review_game(client, play_count=18)
            session = server.app_context.managed_stateful.active_session
            assert replay_session_state_v1(session.state).remaining_hand_for(session.state.local_player_id) == ("C10", "CJ", "DK", "D7")
            for play in plays[18:27]:
                client.command("record_play", card=play["card"])
            assert replay_session_state_v1(session.state).remaining_hand_for(session.state.local_player_id) == ("CJ",)
            for play in plays[27:]:
                client.command("record_play", card=play["card"])
            client.command("set_game_end")
            follow(client, client.submit(Forms(client.page()).find("/sessions/review-decision", index=3)))
            downloads = {k: client.request("GET", f"/sessions/downloads/{k}.json")[2] for k in ("session", "request", "result")}
            for k, raw in downloads.items():
                (args.output / ("session-" + k + ".json")).write_bytes(raw)
            evidence["session_downloads"] = {k: digest(v) for k, v in downloads.items()}
            result = session.execution.result.result.to_dict()["document"]
            assert result["position"]["hand"] == ["C10", "CJ", "SA", "SJ", "HA", "DK", "D7"]
            assert [r["card"] for r in result["analysis_report"]] == ["CJ", "SJ"]
            assert (result["score_summary"]["total_declarer_points"], result["score_summary"]["total_defender_points"]) == (14, 29)
            session_bytes, checkpoints = session.path.read_bytes(), session.decision_checkpoints
            for locale in ("de", "en"):
                for script in (False, True):
                    page = corrected_match_setup(client)
                    page = follow(client, client.submit(operation_form(page, "set_perspective_hand"), card_evidence_mode="exact", cards=MATCH_HAND))
                    follow(client, client.submit(operation_form(client.page("/matches/review/1"), "analyze_decision")))
                    active = server.app_context.managed_stateful.active_match
                    report, = active.capture.report_store.list()
                    assert report.value.status == "executed"
                    report_route = f"/matches/api/v1/reports/{report.report_id}.json"
                    report_bytes = client.request("GET", report_route)[2]
                    raw, work = active.path.read_bytes(), calls.copy()
                    follow(client, client.submit(Forms(client.page("/matches/position/1")).find("/actions/profile/language"), language=locale))
                    navigate("/matches/position/1", script)
                    action(ENTRY + ' button', PREFIX + "select")
                    selected = active.recovery.selected
                    responsive("selection", locale, script)
                    choose("C10")
                    if after:
                        # Native arrows and Space on the radio; no JS selection assignment.
                        before = len(payloads)
                        key("ArrowRight", 39)
                        assert choice() == "CK"
                        key("ArrowLeft", 37)
                        key(" ", 32)
                        assert choice() == "C10" and len(payloads) == before
                        measure("radio-focus", locale, script)
                    other = "en" if locale == "de" else "de"
                    action('form.language-selector button[value="' + other + '"]', "/actions/profile/language")
                    assert choice() == ("C10" if script else "CA")
                    action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                    choose("C10")
                    action(PREVIEW + ' button', PREFIX + "preview", keyboard=True)
                    assert active.recovery.preview.card == "C10"
                    assert active.path.read_bytes() == raw
                    assert_party_score(client.page("/matches/position/1"), (0, 0), (15, 1))
                    responsive("preview", locale, script)
                    token = active.recovery.preview.apply_token
                    action('form.language-selector button[value="' + other + '"]', "/actions/profile/language")
                    assert active.recovery.preview.apply_token == token
                    action(CANCEL + ' button', PREFIX + "cancel", keyboard=True)
                    assert active.path.read_bytes() == raw and client.request("GET", report_route)[2] == report_bytes
                    action(ENTRY + ' button', PREFIX + "select")
                    choose("C10")
                    action(PREVIEW + ' button', PREFIX + "preview")
                    old_apply = Forms(client.page("/matches/position/1")).find(PREFIX + "apply")
                    current = active.recovery.selected
                    if after:
                        action('#match-recovery > form[action="/matches/recovery/select"] button', PREFIX + "select")
                    else:
                        action(ENTRY + ' button', PREFIX + "select")
                    # Cancel above issued a new selection; choose-another itself preserves this identity/time.
                    assert active.recovery.preview is None
                    assert client.submit(old_apply, confirm_apply="on")[0] == 409
                    assert active.recovery.selected is current
                    choose("CK")
                    action(PREVIEW + ' button', PREFIX + "preview")
                    assert active.recovery.preview is None
                    assert cdp.evaluate("!!document.querySelector('.error-summary')")
                    assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
                    measure("rejected", other, script)
                    action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                    assert choice() == "CK"
                    choose("CA")
                    action(PREVIEW + ' button', PREFIX + "preview")
                    apply(keyboard=True)
                    assert active.path.read_bytes() == raw and client.request("GET", report_route)[2] == report_bytes
                    assert calls["match_saves"] == work["match_saves"] and calls["match_executions"] == work["match_executions"]
                    evidence["sources"][f"passive-{locale}-{int(script)}"] = {"workspace": digest(raw), "report": digest(report_bytes), "calls": dict(calls-work), "initial_selection_time": selected.created_at}
                    action(ENTRY + ' button', PREFIX + "select")
                    choose("C10")
                    action(PREVIEW + ' button', PREFIX + "preview")
                    apply(keyboard="space" if not script and locale == "de" else not script)
                    assert calls["match_saves"] == work["match_saves"] + 1
                    assert active.workspace.slots[0].observed_game.plays[2].card == "C10"
                    assert client.request("GET", report_route)[0] == 404
                    assert_party_score(client.page("/matches/position/1"), (0, 0), (14, 1))
                    assert cdp.evaluate("document.activeElement.id") == "match-recording"
                    navigate("/matches/position/2", script)
                    action('form:has(input[value="mark_passed_deal"]) button', "/matches/api/v1/operation")
                    navigate("/matches/position/1", script)
                    saved = active.path.read_bytes()
                    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
                    opener = next(f for f in Forms(client.page("/matches")).forms if f["action"] == "/matches/open" and f["values"]["handle"] == active.handle)
                    follow(client, client.submit(opener))
                    active = server.app_context.managed_stateful.active_match
                    assert active.path.read_bytes() == saved and active.workspace.slots[1].slot_kind == "passed_deal"
                    assert_match_cards(client.page("/matches/review/1"), ["CK", "C7", "C10"], review=True)
                    navigate("/matches/position/1", script)
                    action(ENTRY + ':nth-of-type(2) button', PREFIX + "select")
                    responsive("rewind", locale, script)
                    assert not cdp.evaluate("document.querySelector(" + json.dumps(APPLY + ' input[name="confirm_apply"]') + ").checked")
                    action(APPLY + ' button')  # Native required validation: zero POSTs.
                    action(APPLY + ' input[name="confirm_apply"]')
                    action('form.language-selector button[value="' + other + '"]', "/actions/profile/language")
                    assert not cdp.evaluate("document.querySelector(" + json.dumps(APPLY + ' input[name="confirm_apply"]') + ").checked")
                    assert active.path.read_bytes() == saved
                    action(APPLY + ' input[name="confirm_apply"]')
                    action(APPLY + ' button', PREFIX + "apply", keyboard=True)
                    assert [p.card for p in active.workspace.slots[0].observed_game.plays] == ["CK", "C7"]
                    assert calls["match_saves"] == work["match_saves"] + 3
                    assert session.path.read_bytes() == session_bytes and session.decision_checkpoints == checkpoints
                    assert downloads == {k: client.request("GET", f"/sessions/downloads/{k}.json")[2] for k in downloads}
            evidence["completed"] = True
    finally:
        evidence.update(calls=dict(calls), requests=dict(requests), payloads=payloads)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]), "calls": dict(calls)}, indent=2))


if __name__ == "__main__":
    main()
