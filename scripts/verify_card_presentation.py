# ruff: noqa: E501 - Keep browser expressions and evidence selectors legible.
"""Optional #248 independent Wheel/real HTTP/native browser evidence; no runtime dependency."""
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
from verify_compact_card_entry import contrast
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_compact_card_entry_web import create_live  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form, start_match  # noqa: E402
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile_operations  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

HAND = ("CJ", "CA", "C10", "SJ", "SA", "S10", "HJ", "HA", "H10", "D7")
CANONICAL = ("CA", "C10", "CJ", "SA", "S10", "SJ", "HA", "H10", "HJ", "D7")
SESSION = 'form[action="/sessions/cards"]'
PLAY = 'form[action="/sessions/play"]'
MATCH = 'form[action="/matches/cards"]'

MEASURE = r"""(() => {
  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}};
  const background=e=>{for(let p=e;p;p=p.parentElement){const c=getComputedStyle(p).backgroundColor;if(c!=='rgba(0, 0, 0, 0)')return c}return 'rgb(255, 255, 255)'};
  const face=e=>{const s=getComputedStyle(e);let opacity=1;for(let p=e;p;p=p.parentElement)opacity*=Number(getComputedStyle(p).opacity);return {text:e.textContent,color:s.color,background:background(e),opacity,font:s.fontSize,forced:s.forcedColorAdjust,box:rect(e)}};
  return {page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,
    focus:{tag:document.activeElement.tagName,value:document.activeElement.value,id:document.activeElement.id},
    palettes:[...document.querySelectorAll('.compact-cards')].filter(e=>e.checkVisibility()).map(e=>({
      mode:e.dataset.cardMode,groups:[...e.querySelectorAll('h4')].map(e=>e.textContent),
      summary:e.querySelector('.compact-selection')?.textContent??null,
      cards:[...e.querySelectorAll('.compact-card')].map(c=>{const i=c.querySelector('input'),f=c.querySelector('.card-face')||c.querySelector('span'),s=getComputedStyle(c),b=rect(c),fb=rect(f);return {
        card:i.value,type:i.type,checked:i.checked,required:i.required,name:i.getAttribute('aria-label'),box:b,input:rect(i),face:face(f),
        parts:[...f.querySelectorAll('.card-suit,.card-rank')].map(face),border:s.borderColor,outline:s.outline,offset:s.outlineOffset,
        ring:s.outlineStyle==='none'?0:parseFloat(s.outlineWidth)+parseFloat(s.outlineOffset),group:rect(c.parentElement),
        complete:fb.x>=b.x&&fb.right<=b.right&&fb.y>=b.y&&fb.bottom<=b.bottom&&f.scrollWidth<=f.clientWidth+1}})})),
    readonly:[...document.querySelectorAll('.recorded-card')].filter(e=>e.checkVisibility()).map(e=>({name:e.getAttribute('aria-label'),...face(e.querySelector('.card-face')||e.querySelector('span'))})),
    history:[...document.querySelectorAll('.recorded-history .recorded-card')].map(e=>e.getAttribute('aria-label')),
    hand:[...document.querySelectorAll('.decision-context-hand .recorded-card')].map(e=>e.getAttribute('aria-label')),
    trick:[...document.querySelectorAll('.decision-context-trick .recorded-card')].map(e=>e.getAttribute('aria-label'))};
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
    evidence = {"completed": False, "phase": args.phase, "python": sys.version, "package": skatmind.__version__,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(), "hashes": {}, "pages": [], "actions": [], "sources": {},
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "limitations": ["Synthetic headless browser, forced-colors emulation and doubled computed text; no AT or maintainer UAT.",
            "Existing narrow comparison table remains outside Card acceptance."]}
    for name in ("compact_card_rendering.py", "task_first_rendering.py", "task_first_session_rendering.py", "task_first_match_rendering.py",
        "recorded_decision_context_rendering.py", "recorded_trick_rendering.py", "unplayed_card_rendering.py", "session_card_entry.py", "card_entry_http.py",
        "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json"):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if args.phase == "after" else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = hashlib.sha256(raw).hexdigest()
        if name.startswith("locales/"):
            evidence.setdefault("catalog_counts", {})[name] = len(json.loads(raw))
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

    def navigate(path, script):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def key(name, code, number):
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key=name, code=code, windowsVirtualKeyCode=number)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key=name, code=code, windowsVirtualKeyCode=number)

    def click(selector, route=None):
        before, work = requests.copy(), calls.copy()
        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+Math.min(20,r.height/2)}})()")
        cdp.call("Input.dispatchMouseEvent", type="mouseMoved", **point)
        for kind in ("mousePressed", "mouseReleased"):
            cdp.call("Input.dispatchMouseEvent", type=kind, button="left", clickCount=1, **point)
        time.sleep(.2 if route else .02)
        for _ in range(200):
            if cdp.evaluate("document.readyState==='complete'") and (route is None or requests["POST " + route] > before["POST " + route]):
                break
            time.sleep(.1)
        delta = requests-before
        assert sum(n for p, n in delta.items() if p.startswith("POST ")) == int(route is not None), delta
        evidence["actions"].append({"selector": selector, "javascript": not cdp.script_disabled, "requests": dict(delta), "calls": dict(calls-work)})

    def select(form, cards):
        wanted = set(cards)
        order = cdp.evaluate("[...document.querySelectorAll(" + json.dumps(form + ' input[name="cards"]') + ")].map(e=>({card:e.value,checked:e.checked}))")
        for item in order:
            if item["checked"] != (item["card"] in wanted):
                click(form + ' label:has(input[value="' + item["card"] + '"])')
        return [item["card"] for item in order if item["card"] in wanted]

    def values(form):
        return cdp.evaluate("[...document.querySelectorAll(" + json.dumps(form + ' input[name="cards"]:checked') + ")].map(e=>e.value)")

    def photo(name, selector):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});scrollBy(0,-20)")
        cdp.screenshot(args.output / (name + ".png"))

    def measure(name, locale, script, *, forced=False):
        row = cdp.evaluate(MEASURE)
        row.update(state=name, locale=locale, javascript=script, forced_colors=forced)
        for palette in row["palettes"]:
            for card in palette["cards"]:
                card["face"]["contrast"] = contrast(card["face"]["color"], card["face"]["background"])
                for part in card["parts"]:
                    part["contrast"] = contrast(part["color"], part["background"])
        for face in row["readonly"]:
            face["contrast"] = contrast(face["color"], face["background"])
        evidence["pages"].append(row)
        if args.phase == "after":
            assert row["page"] == row["client"], name
            for palette in row["palettes"]:
                assert (palette["summary"] is None) == (palette["mode"] == "play")
                widths = {c["box"]["width"] for c in palette["cards"]}
                assert len(widths) <= 1, (name, widths)
                assert all(c["complete"] and c["box"]["height"] >= 44 for c in palette["cards"]), name
                assert all(c["face"]["contrast"] >= 4.5 and c["face"]["opacity"] == 1 for c in palette["cards"]), name
                for card in palette["cards"]:
                    assert all(p["color"] == card["face"]["color"] and p["contrast"] >= 4.5 for p in card["parts"])
                    assert card["box"]["right"] <= card["group"]["right"], (name, card)
                    if card["ring"] > 0:
                        assert card["box"]["x"]-card["ring"] >= card["group"]["x"]-.1
                        assert card["box"]["right"]+card["ring"] <= card["group"]["right"]+.1
            assert all(f["contrast"] >= 4.5 and f["opacity"] == 1 for f in row["readonly"]), name
        return row

    def responsive(name, path, locale, script, selector, *, open_selector=None):
        source = server.app_context.managed_stateful.active_session if path.startswith("/sessions") else server.app_context.managed_stateful.active_match
        raw, before = source.path.read_bytes(), calls.copy()
        cells = ((1365, 1), (390, 1), (320, 1), (320, 2)) if locale == "de" and not script else ((390, 1),)
        for width, scale in cells:
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844, deviceScaleFactor=1, mobile=False)
            navigate(path, script)
            if open_selector:
                click(open_selector)
            if scale == 2:
                cdp.evaluate(TEXT_ENLARGEMENT)
            row = measure(name, locale, script)
            row.update(width=width, text_scale=scale)
            photo(f"{name}-{locale}-{int(script)}-{width}-{scale}", selector)
            if scale == 2:
                detail = '.decision-context-hand' if name == "session-context" else selector + ' .compact-card-group:has(input[value="H10"])'
                photo(f"{name}-{locale}-{int(script)}-{width}-{scale}-faces", detail)
        assert source.path.read_bytes() == raw
        assert calls["session_saves"] == before["session_saves"] and calls["match_saves"] == before["match_saves"]
        assert calls["executions"] == before["executions"]
        evidence["sources"][f"{name}-{locale}-{int(script)}"] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "passive_calls": dict(calls-before)}
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
        navigate(path, script)

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"), (match_context, "save_match_workspace_file_v1", "match_saves"),
                (execution, "execute", "executions"), (profile_operations, "save_frontend_profile_file_v1", "profile_saves"),
                (match_state, "_decision_preparation_summary", "match_page_preparations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_"+method, request_count(method, getattr(Handler, "do_"+method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                assert hashlib.sha256(client.request("GET", route)[2]).hexdigest() == evidence["hashes"][resource]
            for locale in ("de", "en"):
                for script in (False, True):
                    create_live(client)
                    follow(client, client.submit(Forms(client.page()).find("/actions/profile/language"), language=locale))
                    responsive("session-hand", "/sessions/current", locale, script, ".compact-cards")
                    source = server.app_context.managed_stateful.active_session
                    before = source.path.read_bytes()
                    select(SESSION, ("H10", "HJ", "HA"))
                    measure("red-selected", locale, script)
                    photo(f"red-selected-{locale}-{int(script)}", '.compact-card-group:has(input[value="H10"])')
                    # Native Space toggles a checkbox; Tab moves focus, without submission.
                    click(SESSION + ' input[value="H10"]')
                    work, req = calls.copy(), requests.copy()
                    key(" ", "Space", 32)
                    key("Tab", "Tab", 9)
                    assert source.path.read_bytes() == before and calls == work and requests == req
                    measure("keyboard-focus", locale, script)
                    photo(f"focus-{locale}-{int(script)}", '.compact-card-group:has(input[value="H10"])')
                    submitted = select(SESSION, ("CJ", "CA", "C10", "D7"))
                    if script:
                        click('form.language-selector button[value="' + ("en" if locale == "de" else "de") + '"]', "/actions/profile/language")
                        assert values(SESSION) == submitted and source.path.read_bytes() == before
                        click('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                    work = calls.copy()
                    click(SESSION + ' button[type="submit"]', "/sessions/cards")
                    assert calls["session_saves"] == work["session_saves"] + 1
                    assert tuple(r.command.card for r in source.state.command_log[1:]) == ("CA", "C10", "CJ", "D7")
                    evidence["actions"].append({"rendered_batch": submitted, "saved_batch": [r.command.card for r in source.state.command_log[1:]]})
                    raw = source.path.read_bytes()
                    reopen = next(f for f in Forms(client.page("/sessions")).forms
                        if f["action"] == "/sessions/open" and f["values"]["handle"] == source.handle)
                    follow(client, client.submit(reopen))
                    source = server.app_context.managed_stateful.active_session
                    assert source.path.read_bytes() == raw
                    navigate("/sessions/current", script)
                    select(SESSION, ("SJ", "SA", "S10", "HJ", "HA", "H10"))
                    click(SESSION + ' button[type="submit"]', "/sessions/cards")
                    assert tuple(r.command.card for r in source.state.command_log[5:]) == ("SA", "S10", "SJ", "HA", "H10", "HJ")
                    client.command("set_declarer")
                    client.command("set_declaration", game_type="grand", hand_game="false")
                    for cards in (("H7", "D8"), ("H7", "D8")):
                        navigate("/sessions/current", script)
                        select(SESSION, cards)
                        click(SESSION + ' button[type="submit"]', "/sessions/cards")
                    responsive("session-play", "/sessions/current", locale, script, ".compact-cards")
                    assert values(PLAY) == []
                    work = calls.copy()
                    click(PLAY + ' button[type="submit"]')  # Native required validation: no POST.
                    assert calls == work
                    select(PLAY, ("HJ",))
                    req = requests.copy()
                    key("ArrowRight", "ArrowRight", 39)
                    assert len(values(PLAY)) == 1 and requests == req
                    select(PLAY, ("H10",))
                    measure("single-selected", locale, script)
                    frozen = tuple(c.to_dict() for c in source.decision_checkpoints)
                    click(PLAY + ' button[type="submit"]', "/sessions/play")
                    assert tuple(c.to_dict() for c in source.decision_checkpoints) == frozen
                    assert source.state.command_log[-1].command.card == "H10"

                    page = start_match(client, locale)
                    match = server.app_context.managed_stateful.active_match
                    navigate("/matches/position/1", script)
                    mplay = MATCH + ':has(input[value="append_plays"])'
                    select(mplay, ("CA",))
                    click(mplay + ' button', "/matches/cards")
                    hand = MATCH + ':has(input[value="set_perspective_hand"])'
                    opener = '#match-recording details:has(input[value="set_perspective_hand"]) > summary'
                    responsive("match-play", "/matches/position/1", locale, script, ".compact-cards")
                    click(opener)
                    cdp.evaluate("document.querySelector(" + json.dumps(hand + ' [name="card_evidence_mode"]') + ").value='exact'")
                    submitted = select(hand, HAND)
                    work = calls.copy()
                    click(hand + ' button', "/matches/cards")
                    assert calls["match_saves"] == work["match_saves"] + 1
                    assert match.workspace.slots[0].observed_game.perspective_initial_hand == CANONICAL
                    responsive("match-evidence", "/matches/position/1", locale, script, hand, open_selector=opener)
                    click(opener)
                    raw, work = match.path.read_bytes(), calls.copy()
                    click(hand + ' button', "/matches/cards")
                    assert match.path.read_bytes() == raw and calls["match_saves"] == work["match_saves"]
                    click(opener)
                    select(hand, ("HJ", "HA", "H10"))
                    click(hand + ' button', "/matches/cards")  # Real exact-count rejection.
                    assert match.path.read_bytes() == raw
                    assert values(hand) == [c for c in submitted if c in {"HJ", "HA", "H10"}]
                    click('form.language-selector button[value="' + ("en" if locale == "de" else "de") + '"]', "/actions/profile/language")
                    assert set(values(hand)) == {"HJ", "HA", "H10"} and match.path.read_bytes() == raw
                    measure("match-rejected-language", locale, script)
                    photo(f"match-rejected-{locale}-{int(script)}", hand)
                    page = client.page("/matches/position/1")
                    follow(client, client.submit(operation_form(page, "set_original_skat"), card_evidence_mode="exact", cards=["D8", "H7"]))
                    page = client.page("/matches/position/1")
                    follow(client, client.submit(operation_form(page, "set_discarded_cards"), card_evidence_mode="known_empty", cards=[]))
                    raw = match.path.read_bytes()
                    reopen = next(f for f in Forms(client.page("/matches")).forms
                        if f["action"] == "/matches/open" and f["values"]["handle"] == match.handle)
                    follow(client, client.submit(reopen))
                    assert server.app_context.managed_stateful.active_match.path.read_bytes() == raw
            # One genuine unchanged #246/#247 sequence, reused across all context measurements.
            plays = record_score_review_game(client, play_count=18)
            source = server.app_context.managed_stateful.active_session
            assert replay_session_state_v1(source.state).remaining_hand_for(source.state.local_player_id) == ("C10", "CJ", "DK", "D7")
            for play in plays[18:27]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            assert replay_session_state_v1(source.state).remaining_hand_for(source.state.local_player_id) == ("CJ",)
            for play in plays[27:]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            client.command("set_game_end")
            navigate("/sessions/current", True)
            click('#recorded-decision-12 + button', "/sessions/review-decision")
            downloads = {k: client.request("GET", f"/sessions/downloads/{k}.json")[2] for k in ("session", "request", "result")}
            result = source.execution.result.result.to_dict()["document"]
            assert result["position"]["hand"] == ["C10", "CJ", "SA", "SJ", "HA", "DK", "D7"]
            for name, raw in downloads.items():
                (args.output / (name + ".json")).write_bytes(raw)
            evidence["downloads"] = {k: {"bytes": len(v), "sha256": hashlib.sha256(v).hexdigest()} for k, v in downloads.items()}
            evidence["retained_hand"] = result["position"]["hand"]
            evidence["retained_candidates"] = [r["card"] for r in result["analysis_report"]]
            assert evidence["retained_candidates"] == ["CJ", "SJ"]
            assert result["score_summary"]["total_declarer_points"] == 14
            assert result["score_summary"]["total_defender_points"] == 29
            frozen = tuple(c.to_dict() for c in source.decision_checkpoints)
            evidence["checkpoint_count"] = len(frozen)
            evidence["checkpoint_sha256"] = hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest()
            for locale in ("de", "en"):
                for script in (False, True):
                    follow(client, client.submit(Forms(client.page()).find("/actions/profile/language"), language=locale))
                    responsive("session-context", "/sessions/current", locale, script, ".recorded-decision-context")
                    photo(f"history-{locale}-{int(script)}", ".recorded-history")
            assert tuple(c.to_dict() for c in source.decision_checkpoints) == frozen
            cdp.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
            measure("forced-readonly", "en", True, forced=True)
            photo("forced-readonly", ".recorded-decision-context")
            navigate("/matches/position/1", True)
            click('#match-recording details:has(input[value="set_perspective_hand"]) > summary')
            select(hand, ("HJ", "HA", "H10"))
            measure("forced-interactive", "en", True, forced=True)
            photo("forced-interactive", hand)
            assert downloads == {k: client.request("GET", f"/sessions/downloads/{k}.json")[2] for k in downloads}
            evidence["completed"] = True
    finally:
        evidence["calls"] = dict(calls)
        evidence["requests"] = dict(requests)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]), "calls": dict(calls)}, indent=2))


if __name__ == "__main__":
    main()
