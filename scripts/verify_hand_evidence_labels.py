# ruff: noqa: E501 - Keep bounded browser measurements and selectors legible.
"""Optional #247 baseline/repaired Wheel evidence using the existing native harness."""
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

from _workflow_visual_browser import LocalBrowser
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_historical_game import build_historical_input  # noqa: E402
from test_match_recording_recovery_web import entry_action, follow, operation_form  # noqa: E402
from test_recorded_decision_context import SESSION_HAND, assert_context  # noqa: E402
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402
from test_unplayed_card_summary_web import setup_match  # noqa: E402

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
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text  # noqa: E402

OVERVIEW = 'section:has(> #session-hand-1)'
PAIR = '[data-unplayed-cards]'
EDITOR = 'form[action="/matches/cards"]:has(input[value="set_discarded_cards"])'
MEASURE = r"""(() => {
  const box=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {text:e.innerText,top:r.top+scrollY,left:r.left,right:r.right,width:r.width,height:r.height,scroll:e.scrollWidth,client:e.clientWidth,visible:e.checkVisibility()}};
  const overview=document.querySelector('#session-hand-1')?.closest('section'), pair=document.querySelector('[data-unplayed-cards]');
  return {page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
    overview:box(overview),pair:box(pair),pairCount:document.querySelectorAll('[data-unplayed-cards]').length,
    hands:[...overview?.querySelectorAll('[id^="session-hand-"]')??[]].map(e=>({id:e.id,...box(e)})),
    labels:[...overview?.querySelectorAll('h2,h3,li,strong')??[],...pair?.querySelectorAll('h3,p')??[]].map(box),
    pairCards:[...pair?.querySelectorAll('.recorded-card')??[]].map(e=>({name:e.getAttribute('aria-label'),...box(e)})),
    editors:[...document.querySelectorAll('form[action="/matches/cards"]')].filter(e=>e.querySelector('[name="card_evidence_mode"]')).map(e=>({operation:e.querySelector('[name="operation"]').value,mode:e.querySelector('[name="card_evidence_mode"]').value,cards:[...e.querySelectorAll('[name="cards"]:checked')].map(e=>e.value)})),
    historyCount:document.querySelectorAll('.recorded-history').length,
    receipt:!!document.querySelector('[data-operation-feedback]'),focus:document.activeElement.id,fragment:location.hash};
})()"""


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
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "hashes": {}, "pages": [], "actions": [], "sources": {},
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "limitations": ["Synthetic headless Edge, emulated widths and doubled computed text, not maintainer UAT or assistive-technology testing.",
            "Existing narrow analysis comparison-table limitation remains outside the measured normal evidence regions."]}
    for name in ("task_first_session_rendering.py", "task_first_rendering.py", "unplayed_card_summary.py",
        "unplayed_card_rendering.py", "task_first_match_state.py", "task_first_match_rendering.py",
        "match_review_rendering.py", "compact_card_rendering.py", "recorded_trick_rendering.py",
        "operation_feedback.py", "locales/en.json", "locales/de.json", "assets/app.css", "assets/workflow.js"):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if args.phase == "after" else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = hashlib.sha256(raw).hexdigest()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, requests = Counter(), Counter()

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

    def navigate(path, script=False):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def click(selector, route=None):
        before, work = requests.copy(), calls.copy()
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
            + ");e.scrollIntoView({block:'center'});const r=e.tagName==='A'?e.getClientRects()[0]:e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)
        time.sleep(.5)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (route is None or requests["POST " + route] > before["POST " + route]):
                break
            time.sleep(.1)
        delta = requests - before
        assert sum(n for p, n in delta.items() if p.startswith("POST ")) == int(route is not None), delta
        evidence["actions"].append({"selector": selector, "requests": dict(delta), "calls": dict(calls-work),
            "javascript": not cdp.script_disabled, "focus": cdp.evaluate("document.activeElement.id"), "fragment": cdp.evaluate("location.hash")})

    def photo(stem, selector):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});window.scrollBy(0,-20)")
        cdp.screenshot(args.output / (stem + ".png"))

    def capture(name, path, *, remaining=None, pair=(), hand=False, full=True,
                hand_index=2, scope="remaining_hands"):
        source = (server.app_context.managed_stateful.active_session if path.startswith("/sessions") else
                  server.app_context.managed_stateful.active_match)
        before, raw = calls.copy(), source.path.read_bytes()
        frozen = tuple(c.to_dict() for c in source.decision_checkpoints) if remaining is not None else ()
        cells = [(locale, script, width, scale) for locale in ("de", "en") for script in (False, True)
                 for width, scale in (((1365, 1), (390, 1), (320, 1), (320, 2)) if full else ((390, 1),))]
        for locale, script, width, scale in cells:
            follow(client, client.submit(Forms(client.page(path)).find("/actions/profile/language"), language=locale))
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844 if width == 390 else 800, deviceScaleFactor=1, mobile=False)
            navigate(path, script)
            if scale == 2:
                cdp.evaluate(TEXT_ENLARGEMENT)
            row = cdp.evaluate(MEASURE)
            row.update(state=name, locale=locale, javascript=script, width=width, text_scale=scale)
            assert row["page"] == row["client"] and not row["receipt"], row
            assert row["pairCount"] == bool(pair)
            assert all(label["visible"] and label["scroll"] <= label["client"] + 1 for label in row["labels"])
            if remaining is not None:
                assert len(row["hands"]) == 3
                assert all(f"({card})" in row["hands"][hand_index]["text"] for card in remaining)
                if args.phase == "after":
                    assert text(locale, "task.session." + scope) in row["overview"]["text"]
                    assert text(locale, "task.session.initial_seating") in row["overview"]["text"]
                    assert row["overview"]["text"].count(text(locale, "task.session.hand_unknown")) == 2
                    if not remaining:
                        assert text(locale, "task.session.hand_empty") in row["hands"][2]["text"]
            if pair:
                assert len(row["pairCards"]) == 2 and all(f"({card})" in c["name"] for card, c in zip(pair, row["pairCards"], strict=True))
                assert text(locale, "unplayed.derived") in row["pair"]["text"]
                assert (text(locale, "unplayed.recorded_input") in row["pair"]["text"]) == (args.phase == "before")
                if hand:
                    assert text(locale, "unplayed.no_discards") in row["pair"]["text"]
            evidence["pages"].append(row)
            stem = f"{name}-{locale}-{int(script)}-{width}-{scale}"
            if remaining is not None:
                photo(stem + "-hands", OVERVIEW)
                if scale == 2:
                    photo(stem + "-hand-tail", '#session-hand-' + str(hand_index + 1))
            if pair:
                photo(stem + "-pair", PAIR)
            if name == "match-recording":
                cdp.evaluate("document.querySelector(" + json.dumps(EDITOR) + ").closest('details').open=true")
                photo(stem + "-source-editor", '#match-evidence')
                photo(stem + "-discard-editor", 'section:has(> form > input[value="set_discarded_cards"])')
                editors = {e["operation"]: e for e in row["editors"]}
                assert editors["set_discarded_cards"]["mode"] == "unknown" and editors["set_discarded_cards"]["cards"] == []
                assert editors["set_original_skat"]["mode"] == "unknown" and editors["set_original_skat"]["cards"] == []
            if name == "match-hand":
                editor = next(e for e in row["editors"] if e["operation"] == "set_discarded_cards")
                assert editor["mode"] == "known_empty" and editor["cards"] == []
            if name == "session-ended":
                assert_context(client.page(path), locale, hand=SESSION_HAND,
                    prefix=(("B", "HJ"), ("C", "DJ")), actor="A", trick=4, play=3)
        assert source.path.read_bytes() == raw
        if frozen:
            assert tuple(c.to_dict() for c in source.decision_checkpoints) == frozen
        assert all(calls[k] == before[k] for k in ("session_saves", "match_saves", "session_executions", "match_executions"))
        evidence["sources"][name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "passive_calls": dict(calls-before)}

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"), (execution, "execute", "session_executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (match_state, "_decision_preparation_summary", "match_page_preparations"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method, request_count(method, getattr(Handler, "do_" + method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert hashlib.sha256(client.request("GET", route)[2]).hexdigest() == evidence["hashes"][resource]
            plays = record_score_review_game(client, play_count=18)
            capture("session-six", "/sessions/current", remaining=("C10", "CJ", "DK", "D7"), full=False)
            for play in plays[18:27]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            capture("session-nine", "/sessions/current", remaining=("CJ",), full=False)
            for play in plays[27:29]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            navigate("/sessions/current", script=True)
            click('#session-recording input[value="CJ"]')
            click('#session-recording button[type="submit"]', "/sessions/play")
            capture("session-complete", "/sessions/current", remaining=(), pair=("S9", "H7"))
            navigate("/sessions/current")
            click('#session-recording button[type="submit"]', "/sessions/command")
            click('#recorded-decision-12 + button', "/sessions/review-decision")
            session = server.app_context.managed_stateful.active_session
            downloads = tuple(client.request("GET", f"/sessions/downloads/{k}.json")[2] for k in ("session", "request", "result"))
            capture("session-ended", "/sessions/current", remaining=(), pair=("S9", "H7"))
            assert tuple(client.request("GET", f"/sessions/downloads/{k}.json")[2] for k in ("session", "request", "result")) == downloads
            evidence["downloads"] = {k: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for k, b in zip(("session", "request", "result"), downloads, strict=True)}
            last = next(r for r in reversed(session.state.command_log) if r.command.kind == "record_play")
            follow(client, client.submit(Forms(client.page()).find("/sessions/undo"), target_revision=str(last.revision-1)))
            capture("session-rewound", "/sessions/current", remaining=("CJ",), full=False)
            follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards="CJ"))
            saved = session.path.read_bytes()
            follow(client, client.submit(Forms(client.page("/sessions")).find("/sessions/open")))
            assert server.app_context.managed_stateful.active_session.path.read_bytes() == saved
            page, match_plays = setup_match(client, count=29)
            navigate("/matches/position/1")
            click('#match-recording input[value="' + match_plays[-1]["card"] + '"]')
            click('#match-recording form[action="/matches/cards"] button', "/matches/cards")
            capture("match-recording", "/matches/position/1", pair=("SK", "SQ"))
            capture("match-review", "/matches/review/1", pair=("SK", "SQ"))
            match = server.app_context.managed_stateful.active_match
            page = client.page("/matches/position/1")
            initial = build_historical_input()["players"][0]["initial_hand"]
            page = follow(client, client.submit(operation_form(page, "set_perspective_hand"), card_evidence_mode="exact", cards=initial))
            assert set(operation_form(page, "set_perspective_hand")["values"]["cards"]) == set(initial)
            page = client.page("/matches/review/1")
            page = follow(client, client.submit(operation_form(page, "analyze_decision"), immediate_sample_count="4"))
            report, = match.capture.report_store.list()
            route = f"/matches/api/v1/reports/{report.report_id}.json"
            retained = client.request("GET", route)[2]
            navigate(f"/matches/reports/{report.report_id}")
            click('button[name="language"][value="de"]', "/actions/profile/language")
            click('a[href="/matches/position/1#match-recording"]')
            assert client.request("GET", route)[2] == retained
            evidence["match_download"] = {"sha256": hashlib.sha256(retained).hexdigest(), "bytes": len(retained)}
            # Existing #234 correction: S9 -> SK. Cancel, accepted Apply, then same-Card no-op.
            for cancel in (True, False, False):
                page = follow(client, client.submit(entry_action(client.page("/matches/position/1"), 4)))
                page = follow(client, client.submit(Forms(page).find("/matches/recovery/preview"), card="SK"))
                raw, before = match.path.read_bytes(), calls["match_saves"]
                noop = match.workspace.slots[0].observed_game.plays[3].card == "SK"
                page = follow(client, client.submit(Forms(page).find("/matches/recovery/cancel" if cancel else "/matches/recovery/apply"), **({} if cancel else {"confirm_apply": "on"})))
                if cancel or noop:
                    assert match.path.read_bytes() == raw and calls["match_saves"] == before
            page = follow(client, client.submit(entry_action(page, 30, rewind=True)))
            page = follow(client, client.submit(Forms(page).find("/matches/recovery/apply"), confirm_apply="on"))
            assert "data-unplayed-cards" not in page
            page = follow(client, client.submit(operation_form(page, "append_plays"), cards=match_plays[-1]["card"]))
            saved = match.path.read_bytes()
            follow(client, client.submit(Forms(client.page("/matches")).find("/matches/open")))
            assert server.app_context.managed_stateful.active_match.path.read_bytes() == saved
            # Separate valid Hand fixture; Unknown and known-empty remain different editor states.
            setup_match(client, hand=True, count=30)
            page = client.page("/matches/position/1")
            follow(client, client.submit(operation_form(page, "set_discarded_cards"), card_evidence_mode="known_empty", cards=[]))
            capture("match-hand", "/matches/position/1", pair=("D8", "D7"), hand=True, full=False)
            capture("match-hand-review", "/matches/review/1", pair=("D8", "D7"), hand=True, full=False)
            # Real rejected transport payload: native witness/language navigation, no successful save mocked.
            page = follow(client, client.submit(Forms(client.page("/sessions")).find("/sessions/create"),
                game_name="Synthetic evidence target", capture_mode="live", perspective_seat="forehand",
                forehand_name='Alexandra <&> Long-Synthetic-Player-Name', middlehand_name="Boris",
                rearhand_name="Clara", setup_action="update"))
            page = follow(client, client.submit(Forms(page).find("/sessions/create"), setup_action="create"))
            form = Forms(page).find("/sessions/cards")
            page = follow(client, client.submit(form, cards="CA"))
            response = client.submit(Forms(page).find("/sessions/cards"), cards="CA")
            assert response[0] == 400
            active = server.app_context.managed_stateful.active_session
            raw = active.path.read_bytes()
            capture("session-initial-error", "/sessions/current", remaining=("CA",),
                    hand_index=0, scope="initial_so_far")
            for script in (False, True):
                navigate("/sessions/current", script)
                for _ in range(50):
                    if cdp.evaluate("document.activeElement.matches('a.session-card-evidence')"):
                        break
                    cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Tab", windowsVirtualKeyCode=9)
                    cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Tab", windowsVirtualKeyCode=9)
                assert cdp.evaluate("document.activeElement.matches('a.session-card-evidence')")
                cdp.screenshot(args.output / f"keyboard-evidence-link-{int(script)}.png")
                before = requests.copy()
                cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Enter", windowsVirtualKeyCode=13, text="\r")
                cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Enter", windowsVirtualKeyCode=13)
                time.sleep(.2)
                assert cdp.evaluate("document.activeElement.id") == "session-hand-1"
                assert requests == before
                evidence["actions"].append({"keyboard": "Tab then Enter on evidence link", "javascript": script,
                    "requests": {}, "focus": "session-hand-1"})
                photo(f"evidence-target-{int(script)}", OVERVIEW)
                click('button[name="language"][value="de"]', "/actions/profile/language")
                assert cdp.evaluate("document.activeElement.id") == "session-card-error"
                click('a.session-card-evidence')
                photo(f"evidence-target-de-{int(script)}", OVERVIEW)
                assert active.path.read_bytes() == raw
            evidence.update(completed=True, calls=dict(calls), requests=dict(requests))
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]), "calls": dict(calls), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
