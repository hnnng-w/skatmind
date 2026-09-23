# ruff: noqa: E501 - Keep scoped browser expressions and evidence records together.
"""Optional #254 native navigation evidence over independently installed Wheels."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_analysis_downloads import MEASURE as DOWNLOADS
from verify_analysis_downloads import digest
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context_web import (  # noqa: E402
    record_context_match,
    record_second_context_game,
)
from test_session_declaration_correction_web import PREFIX, preview  # noqa: E402
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profiles  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.json_transfer import (  # noqa: E402
    canonical_frontend_json_bytes_v1 as canonical,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

FOCUS = """(() => {const e=document.activeElement,s=getComputedStyle(e);return {
 tag:e.tagName,id:e.id,href:e.getAttribute('href'),text:e===document.body?'':e.textContent,
 describedby:e.getAttribute('aria-describedby'),outline:s.outline,offset:s.outlineOffset}})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("browser", "output", "wheel"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = dict(completed=False, phase=args.phase, python=sys.version, package=skatmind.__version__,
        wheel=digest(args.wheel.read_bytes()), head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        hashes={}, navigation=[], downloads=[], operations=[], limits=[
            "Synthetic headless Edge, CSS viewports, computed 200% text; not browser zoom, physical-device, AT or maintainer UAT.",
            "Setup/Preview use real returned HTTP forms; link and analysis activation use native pointer/keys.",
            "No target is programmatically focused; fragment landing and next Tab are observed separately."])
    for name in ("session_recorded_review_rendering.py", "session_recorded_review.py", "task_first_session_rendering.py",
                 "match_review_rendering.py", "match_report_rendering.py", "task_first_match_rendering.py",
                 "recorded_decision_context_sources.py", "task_first_match_state.py", "analysis_explanation.py",
                 "candidate_table_rendering.py", "analysis_download_rendering.py", "assets/app.css", "assets/workflow.js",
                 "locales/de.json", "locales/en.json"):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = (ROOT / "src/skatmind/app_web" / name).read_bytes() if after else subprocess.check_output(
            ["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT)
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, requests = Counter(), Counter()

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapped

    def request_counter(method, real):
        def wrapped(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return wrapped

    def key(name, code):
        for kind in ("keyDown", "keyUp"):
            cdp.call("Input.dispatchKeyEvent", type=kind, key=name, windowsVirtualKeyCode=code,
                     **({"text": "\r"} if name == "Enter" and kind == "keyDown" else {}))

    def activate(selector, *, keyboard=False, focus_photo=None):
        """Locate an origin, then native Tab/Enter or pointer. Never focus a target."""
        if keyboard:
            for _ in range(240):
                if cdp.evaluate("document.activeElement===document.querySelector(" + json.dumps(selector) + ")"):
                    break
                key("Tab", 9)
            else:
                raise AssertionError("Native Tab did not reach " + selector)
            if focus_photo:
                cdp.screenshot(args.output / focus_photo)
            key("Enter", 13)
        else:
            point = cdp.evaluate("(() => {const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getClientRects()[0];return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
            for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                cdp.call("Input.dispatchMouseEvent", type=kind, **point,
                         **({"button": "left", "clickCount": 1} if kind != "mouseMoved" else {}))
        time.sleep(.65)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'"):
                break
            time.sleep(.1)

    def navigate(path, script=False, width=1365, scale=1):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844, deviceScaleFactor=1, mobile=False)
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")
        if scale == 2:
            cdp.evaluate(TEXT_ENLARGEMENT)

    def link(surface, selector, target, expected_href, expected_text, metadata, *, keyboard):
        work, req = calls.copy(), requests.copy()
        info = cdp.evaluate("(() => {const e=document.querySelector(" + json.dumps(selector) + ");return {text:e.textContent,href:e.getAttribute('href'),aria:e.getAttribute('aria-label'),font:getComputedStyle(e).fontSize,rects:[...e.getClientRects()].map(r=>({x:r.x,right:r.right,width:r.width})),client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}})()")
        assert info["href"] == expected_href and info["text"] == expected_text, info
        assert info["scroll"] <= info["client"] + 1 and all(r["right"] <= info["client"] for r in info["rects"])
        names = [n.get("name", {}).get("value") for n in cdp.call("Accessibility.getFullAXTree")["nodes"] if n.get("role", {}).get("value") == "link"]
        assert expected_text in names and info["aria"] in (None, expected_text)
        stem = f"{surface}-{metadata['locale']}-{int(metadata['script'])}-{metadata['width']}-{metadata['scale']}"
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'center'})")
        cdp.screenshot(args.output / (stem + "-link.png"))
        activate(selector, keyboard=keyboard, focus_photo=stem + "-origin-focus.png")
        url, focus = cdp.evaluate("location.pathname+location.hash"), cdp.evaluate(FOCUS)
        expected_url = "/sessions/current" + expected_href if expected_href.startswith("#") else expected_href
        assert url == expected_url, (url, expected_url)
        landing = cdp.evaluate("(() => {const e=document.querySelector(" + json.dumps(target) + "),r=e.getBoundingClientRect();return {text:e.textContent,top:r.top,bottom:r.bottom,width:r.width,visible:r.top<innerHeight&&r.bottom>0,client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}})()")
        if surface == "session":
            assert "SJ" in landing["text"] and ("Stich 4" if metadata["locale"] == "de" else "Trick 4") in landing["text"]
        assert landing["visible"] and landing["scroll"] <= landing["client"] + 1, landing
        cdp.screenshot(args.output / (stem + "-landing.png"))
        key("Tab", 9)
        next_focus = cdp.evaluate(FOCUS)
        if surface == "session":
            assert next_focus["tag"] == "BUTTON" and next_focus["describedby"] == "recorded-decision-12"
        cdp.screenshot(args.output / (stem + "-next-tab.png"))
        assert all(calls[k] == work[k] for k in ("session_saves", "match_saves", "executions", "match_executions"))
        assert not any(k.startswith("POST ") for k in requests-req)
        presentation = cdp.evaluate(DOWNLOADS)
        evidence["navigation"].append(dict(surface=surface, **metadata, origin=info, keyboard=keyboard,
            url=url, focus=focus, next_tab=next_focus, landing=landing, candidates=presentation["candidate"],
            downloads=presentation["links"], calls=dict(calls-work), requests=dict(requests-req)))

    def download(route, raw):
        node = next(n for n in cdp.evaluate(DOWNLOADS)["links"] if n["href"] == route)
        assert not node["ancestors"]
        destination = args.output / ("download-" + str(len(evidence["downloads"])))
        destination.mkdir()
        cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
        work = calls.copy()
        activate('a[download][href="' + route + '"]')
        for _ in range(100):
            received = list(destination.glob("*.json"))
            if received:
                break
            time.sleep(.1)
        assert len(received) == 1 and received[0].read_bytes() == raw and calls == work
        evidence["downloads"].append(dict(label=node["text"], name=received[0].name, **digest(raw)))

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"), (execution, "execute", "executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (profiles, "save_frontend_profile_file_v1", "profile_saves"),
                (match_state, "_decision_preparation_summary", "match_page_preparations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method, request_counter(method, getattr(Handler, "do_" + method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            plays = record_score_review_game(client, play_count=18)
            session = server.app_context.managed_stateful.active_session
            assert replay_session_state_v1(session.state).remaining_hand_for(session.state.local_player_id) == ("C10", "CJ", "DK", "D7")
            for play in plays[18:27]:
                client.command("record_play", card=play["card"])
            assert replay_session_state_v1(session.state).remaining_hand_for(session.state.local_player_id) == ("CJ",)
            for play in plays[27:]:
                client.command("record_play", card=play["card"])
            client.command("set_game_end")
            evidence["session_fixture_calls"] = dict(calls)
            navigate("/sessions/current#recorded-decision-12")
            before = calls.copy()
            activate('#recorded-decision-12 + button', keyboard=True)
            evidence["operations"].append(dict(operation="native Session SJ review", calls=dict(calls-before)))
            assert cdp.evaluate("document.activeElement.id") == "session-result"
            cdp.screenshot(args.output / "native-result-focus.png")
            retained = {f"/sessions/downloads/{name}.json": getattr(session.execution, name + "_json_bytes") for name in ("request", "result")}
            result = session.execution.result.result.document
            assert result["score_summary"]["total_declarer_points"] == 14 and result["score_summary"]["total_defender_points"] == 29
            assert result["position"]["current_trick"] == ("HJ", "DJ") and len(result["position"]["hand"]) == 7
            assert [(r["card"], r["expected_point_swing"]) for r in result["analysis_report"]] == [("CJ", 6.0), ("SJ", 6.0)]
            before = calls.copy()
            record_context_match(client)
            record_second_context_game(client)
            follow(client, client.submit(operation_form(client.page("/matches/position/2"), "mark_passed_deal")))
            evidence["match_fixture_calls"] = dict(calls-before)
            match = server.app_context.managed_stateful.active_match
            for number in (4, 1):
                navigate(f"/matches/review/{number}", True)
                before = calls.copy()
                activate('form:has(input[name="operation"][value="analyze_decision"]) button')
                evidence["operations"].append(dict(operation=f"native Game {number} decision 2 analysis", calls=dict(calls-before)))
            other, report = match.capture.report_store.list()
            assert (other.decision_index, report.decision_index) == (2, 2)
            report_path = f"/matches/reports/{report.report_id}"
            route = f"/matches/api/v1/reports/{report.report_id}.json"
            retained[route] = client.request("GET", route)[2]
            evidence["report_owners"] = [dict(report_id=r.report_id, game=r.match_position,
                decision=r.decision_index, report=digest(canonical(r.to_dict()))) for r in (other, report)]
            sources = dict(session=session.path.read_bytes(), checkpoints=canonical([c.to_dict() for c in session.decision_checkpoints]),
                           match=match.path.read_bytes(), reports=canonical([r.to_dict() for r in match.capture.report_store.list()]))
            work = calls.copy()
            for locale in ("de", "en"):
                for script in (False, True):
                    navigate("/sessions/current", script)
                    activate('form.language-selector button[value="' + locale + '"]')
                    for path, raw in retained.items():
                        navigate(report_path if path == route else "/sessions/current", script)
                        download(path, raw)
                    matrix = ((1365, 1), (390, 1), (320, 1), (320, 2)) if locale == "de" and not script else ((390, 1),)
                    for width, scale in matrix:
                        meta = dict(locale=locale, script=script, width=width, scale=scale)
                        keyboard = width != 1365
                        navigate("/sessions/current#session-result", script, width, scale)
                        text = ("Zur Entscheidungsauswahl: Stich 4, Karte 3" if locale == "de" else "Decision selection: Trick 4, Card 3") if after else ("Zurück zur ausgewerteten Entscheidung" if locale == "de" else "Back to the source decision")
                        link("session", '#session-result a[href="#recorded-decision-12"]', "#recorded-decision-12", "#recorded-decision-12", text, meta, keyboard=keyboard)
                        navigate("/matches/review/1", script, width, scale)
                        text = ("Zur Erfassung: Spiel 1" if locale == "de" else "Recording: Game 1") if after else ("Aufzeichnung fortsetzen" if locale == "de" else "Continue recording")
                        link("recording", '#match-review a[href="/matches/position/1#match-recording"]', "#match-recording", "/matches/position/1#match-recording", text, meta, keyboard=keyboard)
                        navigate("/matches/position/1#match-recording", script, width, scale)
                        text = ("Zur Entscheidungsauswahl: Spiel 1" if locale == "de" else "Decision selection: Game 1") if after else ("Dieses erfasste Spiel auswerten" if locale == "de" else "Review this recorded Game")
                        link("review", 'a[href="/matches/review/1"]', "#match-review", "/matches/review/1", text, meta, keyboard=keyboard)
                        # Render a real Report list, then select Game 2 in an independent HTTP client.
                        # The already-rendered native href still opens the exact retained Game-1 Report.
                        navigate("/matches/review/1", script, width, scale)
                        client.page("/matches/position/2")
                        assert match.selected_position == 2
                        text = ("Vorhandene Auswertung öffnen: Spiel 1 — Stich 1, Karte 2" if locale == "de" else "Open existing analysis: Game 1 — Trick 1, Card 2") if after else ("Analyse einer erfassten Entscheidung — Spiel 1" if locale == "de" else "Recorded-decision analysis — Game 1")
                        link("report", 'a[href="' + report_path + '"]', "#match-review", report_path, text, meta, keyboard=keyboard)
                        assert match.selected_position == 1
                        assert cdp.evaluate("document.querySelector('.decision-context-trick .card-face').dataset.cardSuit==='C' && document.querySelector('.decision-context-trick .card-rank').textContent==='K'")
            # Representative existing #250 no-op Preview/Cancel, real HTTP returned forms.
            saved_execution = session.execution
            before = calls.copy()
            page = preview(client)
            assert session.execution is saved_execution
            evidence["operations"].append(dict(operation="returned-form HTTP no-op Preview/Cancel", calls=dict(calls-before)))
            follow(client, client.submit(Forms(page).find(PREFIX + "cancel")))
            assert session.execution is saved_execution
            assert all(calls[k] == work[k] for k in ("session_saves", "match_saves", "executions", "match_executions"))
            evidence["passive_calls"] = dict(calls-work)
            for path, raw in retained.items():
                assert client.request("GET", path)[2] == raw
            assert session.path.read_bytes() == sources["session"] and match.path.read_bytes() == sources["match"]
            assert canonical([c.to_dict() for c in session.decision_checkpoints]) == sources["checkpoints"]
            assert canonical([r.to_dict() for r in match.capture.report_store.list()]) == sources["reports"]
            evidence["sources"], evidence["retained"] = ({k: digest(v) for k, v in data.items()} for data in (sources, retained))
            if args.baseline:
                baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
                assert len(baseline["navigation"]) == len(evidence["navigation"])
                for old, new in zip(baseline["navigation"], evidence["navigation"], strict=True):
                    assert all(old[k] == new[k] for k in ("surface", "locale", "script", "width", "scale", "candidates"))
                    for field in ("focus", "next_tab"):
                        assert all(old[field][k] == new[field][k] for k in ("tag", "id", "href", "describedby", "outline", "offset"))
            evidence["completed"] = True
    finally:
        evidence["calls"], evidence["requests"] = dict(calls), dict(requests)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps(dict(completed=evidence["completed"], navigation=len(evidence["navigation"]), calls=dict(calls)), indent=2))


if __name__ == "__main__":
    main()
