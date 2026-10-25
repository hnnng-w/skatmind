# ruff: noqa: E501 - Keep native DevTools expressions and evidence assertions legible.
"""Disposable source-tree Issue #297 browser evidence; never installed maintainer UAT."""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
import json
import os
import platform
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
if "--baseline-archive" in sys.argv:
    sys.path.insert(0, sys.argv[sys.argv.index("--baseline-archive") + 1] + "/src")

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_direct_match_evidence import independent_form  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_evidence_presentation import HAND, complete_hand, source_game  # noqa: E402
from test_match_recording_recovery_web import declarer_choice, follow, operation_form  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.match_frontend as frontend  # noqa: E402
import skatmind.app_web.profile_driven_creation as creation  # noqa: E402
import skatmind.app_web.server as web  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.stateful_localization import card_name  # noqa: E402
from skatmind.match_historical_materialization import (  # noqa: E402
    materialize_match_observed_game_historical_v1,
)
from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline-archive", type=Path)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert (".zip" in frontend.__file__) == (args.phase == "before")
    args.output.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    began = time.perf_counter()
    report = {"completed": False, "phase": args.phase, "python": sys.version,
              "os": platform.platform(), "browser": local.version, "cases": [], "landings": [],
              "measurements": [], "scope": "Disposable source-tree HTTP; CSS emulation is not zoom",
              "loaded_module": frontend.__file__, "true_200_percent_zoom": "pending installed retest"}
    report["hashes"] = {name: hashlib.sha256(importlib.resources.files("skatmind.app_web")
        .joinpath(name).read_bytes()).hexdigest() for name in ("assets/app.css", "assets/workflow.js",
            "locales/en.json", "locales/de.json", "task_first_match_rendering.py",
            "seat_setup_rendering.py", "match_declaration_drafts.py", "match_evidence_presentation.py")}
    counts = Counter()
    real_replace, real_operation = os.replace, frontend.apply_unified_match_operation_v1

    def replaced(source, destination):
        if Path(destination).parent == server.app_context.managed_stateful.root("matches"):
            counts["recording_writes"] += 1
        return real_replace(source, destination)

    def operated(active, values):
        counts[values["operation"]] += 1
        return real_operation(active, values)

    def counted(name, real):
        def call(*a, **kw):
            counts[name] += 1
            return real(*a, **kw)
        return call

    def accounting():
        stack = ExitStack()
        for module, name, callback in (
            (os, "replace", replaced),
            (frontend, "apply_unified_match_operation_v1", operated),
            (capture, "save_match_workspace_file_v1", counted("recording_saves", capture.save_match_workspace_file_v1)),
            (web, "create_unified_match_v1", counted("match_creations", web.create_unified_match_v1)),
            (profile, "save_frontend_profile_file_v1", counted("profile_writes", profile.save_frontend_profile_file_v1)),
            (creation, "generate_frontend_match_id_v1", counted("match_ids", creation.generate_frontend_match_id_v1)),
            (creation, "generate_frontend_player_id_v1", counted("player_ids", creation.generate_frontend_player_id_v1)),
            (analysis, "execute_match_decision_analysis_v1", counted("analysis", analysis.execute_match_decision_analysis_v1)),
            (analysis, "execute_match_historical_analysis_v1", counted("analysis", analysis.execute_match_historical_analysis_v1)),
        ):
            stack.enter_context(patch.object(module, name, callback))
        return stack

    def submit(selector, *, pointer=False):
        if pointer:
            click(cdp, selector)
        else:
            tab_to(cdp, selector)
            keyboard(cdp, "Enter", "Enter", 13, "\r")
        time.sleep(.65)

    def enter(name, value):
        click(cdp, f'input[name="{name}"]')
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        keyboard(cdp, "Backspace", "Backspace", 8)
        cdp.call("Input.insertText", text=value)

    def reveal(selector):
        selectors = cdp.evaluate("(()=>{let e=document.querySelector(" + json.dumps(selector) + ");let a=[];while(e){if(e.tagName==='DETAILS'&&!e.open){let s=e.querySelector('summary');if(!s.id)s.id='probe-open-'+[...document.querySelectorAll('summary')].indexOf(s);a.push('#'+s.id)}e=e.parentElement}return a.reverse()})()")
        for target in selectors:
            click(cdp, target)

    def selected(prefix, cards):
        field = "evidence_" + prefix
        reveal(f'input[name="{field}"]')
        current = cdp.evaluate(f"[...document.querySelectorAll('input[name={field}]:checked')].map(e=>e.value)")
        for card in sorted(set(current) ^ set(cards)):
            click(cdp, f'input[name="{field}"][value="{card}"]')

    def landing(case, stage):
        # Must run before any verifier scroll, focus, Tab or disclosure activation.
        data = cdp.evaluate("""(()=>{const rect=e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right,width:r.width,height:r.height,visible:e.checkVisibility(),inViewport:e.checkVisibility()&&r.top>=0&&r.bottom<=innerHeight}};return {url:location.href,width:innerWidth,height:innerHeight,scrollY,active:{id:document.activeElement.id,name:document.activeElement.name,value:document.activeElement.value,html:document.activeElement.outerHTML.slice(0,1000)},review:[...document.querySelectorAll('.reviewed-perspective')].map(e=>({text:e.textContent,...rect(e)})),create:[...document.querySelectorAll('button[value=create]')].map(rect),sources:[...document.querySelectorAll('.match-source-editor')].map(e=>({source:e.dataset.source,open:e.open,...rect(e)})),error:[...document.querySelectorAll('.error-summary')].map(e=>({text:e.textContent,...rect(e)})),explanation:document.querySelector('#match-card-selection-help')?.textContent,candidates:[...document.querySelectorAll('input[name=cards][type=radio]')].map(e=>e.value)}})()""")
        data.update(case=case, stage=stage, counts=dict(counts), zoom=cdp.call("Page.getLayoutMetrics")["cssVisualViewport"].get("zoom"))
        report["landings"].append(data)
        cdp.screenshot(args.output / f"{case}-{stage}.png")
        return data

    def snapshot(active, stage):
        game = active.workspace.slots[active.selected_position - 1].observed_game
        return {"stage": stage, "counts": dict(counts), "revision": active.workspace.revision,
                "sha256": hashlib.sha256(active.path.read_bytes()).hexdigest(),
                "fingerprint": active.capture.content_fingerprint, "game": None if game is None else game.to_dict()}

    def requests():
        cdp.evaluate("void 0")
        return [{"url": e["params"]["request"]["url"], "fields": parse_qs(
            e["params"]["request"].get("postData", ""), keep_blank_values=True)}
            for e in cdp.events if e["params"]["request"]["method"] == "POST"]

    def layouts(case):
        for prefix in ("perspective_hand", "original_skat", "discarded_cards"):
            reveal(f'input[name="evidence_{prefix}"]')
        for width in (1365, 1920, 2560, 700, 520, 320, 240):
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900, deviceScaleFactor=1, mobile=False)
            data = cdp.evaluate("""(()=>{return {width:innerWidth,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,palettes:[...document.querySelectorAll('.compact-cards')].filter(e=>e.checkVisibility()).map(e=>({name:e.querySelector('input').name,width:e.getBoundingClientRect().width,groups:[...e.querySelectorAll('.compact-card-group')].map(g=>{let rows={};for(const l of g.querySelectorAll('.compact-card')){const y=Math.round(l.getBoundingClientRect().y*10);(rows[y]??=[]).push(l.querySelector('input').value)}return Object.values(rows)}),tiles:[...e.querySelectorAll('.compact-card')].map(l=>({height:l.getBoundingClientRect().height,font:getComputedStyle(l).fontSize,input:l.querySelector('input').getBoundingClientRect().width,overflow:l.scrollWidth>l.clientWidth+1}))}))}})()""")
            data.update(case=case, zoom=cdp.call("Page.getLayoutMetrics")["cssVisualViewport"].get("zoom"))
            report["measurements"].append(data)
            assert data["document"] == data["client"] and data["zoom"] == 1, data
            assert {p["name"] for p in data["palettes"]} == {
                "evidence_perspective_hand", "evidence_original_skat", "evidence_discarded_cards", "cards"}
            for palette in data["palettes"]:
                assert all(t["height"] >= 44 and t["font"] == "16px" and t["input"] == 20 and not t["overflow"] for t in palette["tiles"])
                for rows in palette["groups"]:
                    if sum(map(len, rows)) == 8:
                        assert list(map(len, rows)) in ([8], [4, 4], [2] * 4, [1] * 8), rows
                        if width >= 1365:
                            assert len(rows) == 1, (palette["name"], width, rows)
                selector = f'input[name="{palette["name"]}"]'
                cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'center'});document.querySelector(" + json.dumps(selector) + ").focus()")
                palette["focus"] = cdp.evaluate("(()=>{const e=document.activeElement,l=e.closest('label'),s=getComputedStyle(l);return {name:e.name,value:e.value,outline:s.outlineWidth,visible:e.checkVisibility()}})()")
                assert palette["focus"]["visible"]
                cdp.screenshot(args.output / f"{case}-layout-{width}-{palette['name']}.png")

    try:
        http = Browser(server)
        cdp.call("Network.setCookie", name=http.cookie.split("=", 1)[0], value=http.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
        for locale, script in (("de", False), ("en", False), ("de", True), ("en", True)):
            case_id = f"{locale}-{int(script)}"
            page = http.page("/matches/new")
            follow(http, http.submit(Forms(page).find("/actions/profile/language"), language=locale))
            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
            cdp.navigate(server.origin + "/matches/new")
            counts.clear()
            cdp.events.clear()
            case = {"locale": locale, "javascript": script, "steps": []}
            report["cases"].append(case)
            with accounting():
                enter("match_title", "Synthetic Match 297")
                for seat, name in zip(("forehand", "middlehand", "rearhand"), ("Anna", "Bea", "Clara"), strict=True):
                    enter(seat + "_name", name)
                keyboard(cdp, "Enter", "Enter", 13, "\r")
                time.sleep(.65)
                assert not server.app_context.creation_setups["matches"].reviewed and not counts
                assert not cdp.evaluate("!!document.querySelector('button[value=create]')")
                submit('button[value="choose_forehand"]', pointer=script)
                result = landing(case_id, "review-initial-landing")
                assert server.app_context.creation_setups["matches"].reviewed and not counts
                assert len(result["review"]) == 1 and "Anna" in result["review"][0]["text"]
                keyboard(cdp, "Tab", "Tab", 9)
                case["next_tab"] = cdp.evaluate("({name:document.activeElement.name,value:document.activeElement.value})")
                if args.phase == "after":
                    assert result["active"]["id"] == "match-setup-review"
                    assert result["review"][0]["inViewport"] and result["create"][0]["inViewport"]
                    assert case["next_tab"] == {"name": "setup_action", "value": "create"}
                    submit('button[value="update"]:not([hidden])')
                    result = landing(case_id, "update-initial-landing")
                    assert result["active"]["id"] == "match-setup-review"
                    assert result["review"][0]["text"].endswith(": Anna") and not counts
                submit('button[value="create"]')
                active = server.app_context.managed_stateful.active_match
                case["steps"].append(snapshot(active, "created"))
                assert counts["match_creations"] == counts["recording_writes"] == counts["match_ids"] == counts["profile_writes"] == 1
                assert counts["player_ids"] == 3
                assert active.workspace.match_definition.perspective_player_id == next(p.player_id for p in active.workspace.match_definition.participants if p.player_label == "Anna")
                landing(case_id, "created-initial-landing")
            # Fixture declaration: excluded from the following evidence-phase accounting.
            page = http.page("/matches/position/1")
            page = follow(http, http.submit(operation_form(page, "start_game")))
            page = follow(http, http.submit(operation_form(page, "set_declaration"), declarer_player_id=declarer_choice(page, "Anna"), game_type="grand", bid_value="18"))
            counts.clear()
            with accounting():
                cdp.navigate(server.origin + "/matches/position/1")
                landing(case_id, "sources-initial-landing")
                selected("perspective_hand", HAND)
                submit('button[value="perspective_hand_selected"]')
                result = landing(case_id, "known-hand-initial-landing")
                assert len(result["candidates"]) == 32
                case["steps"].append(snapshot(active, "hand-saved"))
                if args.phase == "before":
                    # Baseline defect: normal empty Save rejects; 32 candidates are correct.
                    selected("original_skat", ())
                    submit('button[value="original_skat_selected"]')
                    result = landing(case_id, "baseline-empty-rejection")
                    assert result["error"] and active.workspace.slots[0].observed_game.original_skat is None
                    case["steps"].append(snapshot(active, "empty-rejected"))
                    case["requests"] = requests()
                    continue
                assert result["sources"][1]["open"]
                assert ("ursprüngliche Skat" if locale == "de" else "original Skat") in result["explanation"]
                # Enhanced language preserves a deliberate close; native language uses the server policy.
                click(cdp, 'details[data-source="original_skat"] > summary')
                before = active.path.read_bytes()
                other = "en" if locale == "de" else "de"
                submit(f'.language-selector button[value="{other}"]', pointer=True)
                result = landing(case_id, "closed-editor-language-landing")
                assert result["sources"][1]["open"] is (not script)
                assert active.path.read_bytes() == before
                submit(f'.language-selector button[value="{locale}"]', pointer=True)
                selected("original_skat", ("CJ", "D7"))
                submit('button[value="original_skat_selected"]')
                result = landing(case_id, "overlap-error-initial-landing")
                assert result["error"] and 'class="error-summary"' in result["active"]["html"]
                assert [e["source"] for e in result["sources"] if e["open"]] == ["original_skat"]
                assert counts["recording_writes"] == 1
                selected("original_skat", ("D7",))
                submit('button[value="original_skat_selected"]')
                result = landing(case_id, "count-error-initial-landing")
                assert result["error"] and 'class="error-summary"' in result["active"]["html"]
                assert counts["recording_writes"] == 1
                for target in (other, locale):
                    submit(f'.language-selector button[value="{target}"]', pointer=True)
                    result = landing(case_id, "error-language-" + target + "-initial-landing")
                    assert 'class="error-summary"' in result["active"]["html"]
                    assert [e["source"] for e in result["sources"] if e["open"]] == ["original_skat"]
                selected("original_skat", ("HA", "D7"))
                submit('button[value="original_skat_selected"]', pointer=True)
                result = landing(case_id, "skat-saved-initial-landing")
                assert len(result["candidates"]) == 32 and result["sources"][2]["open"]
                assert ("ursprüngliche Skat" if locale == "de" else "original Skat") not in result["explanation"]
                case["steps"].append(snapshot(active, "skat-saved"))
                for prefix, cards, writes, label in (
                    ("original_skat", ("HA", "D7"), 2, "pair-noop"),
                    ("discarded_cards", ("HA", "D7"), 3, "discards-saved"),
                    ("discarded_cards", (), 4, "discards-withdrawn"),
                    ("discarded_cards", ("HA", "D7"), 5, "discards-restored"),
                    ("original_skat", (), 6, "skat-withdrawn"),
                    ("original_skat", (), 6, "absent-noop"),
                    ("original_skat", ("HA", "D7"), 7, "skat-restored"),
                ):
                    selected(prefix, cards)
                    submit(f'button[value="{prefix}_selected"]', pointer=bool(writes % 2))
                    result = landing(case_id, label + "-initial-landing")
                    case["steps"].append(snapshot(active, label))
                    assert counts["recording_writes"] == counts["recording_saves"] == writes
                    assert counts["set_declaration"] == counts["analysis"] == 0
                    assert counts["profile_writes"] == 4
                    if label in {"discards-saved", "skat-restored"}:
                        assert set(result["candidates"]) == set(HAND)
                        assert not any(e["open"] for e in result["sources"])
                for card in ("S10", "SK", "S7"):
                    click(cdp, f'input[name=cards][value="{card}"]')
                    submit('form[action="/matches/cards"] button')
                    result = landing(case_id, "play-" + card + "-initial-landing")
                    assert not any(e["open"] for e in result["sources"])
                assert counts["recording_writes"] == 10
                submit('#match-play-2 form[action="/matches/recovery/select"]:last-of-type button')
                result = landing(case_id, "rewind-initial-landing")
                assert card_name(locale, "S10") in cdp.evaluate("document.querySelector('#match-rewind-retained').textContent")
                before = active.path.read_bytes()
                submit('#match-recovery form[action="/matches/recovery/cancel"] button')
                assert active.path.read_bytes() == before
                submit('#match-play-2 form[action="/matches/recovery/select"]:last-of-type button')
                click(cdp, '#match-recovery input[name="confirm_apply"]')
                submit('#match-recovery form[action="/matches/recovery/apply"] button')
                case["steps"].append(snapshot(active, "rewind-applied"))
                assert [p.card for p in active.workspace.slots[0].observed_game.plays] == ["S10"]
                assert counts["recording_writes"] == 11
                before_counts = counts.copy()
                layouts(case_id)
                assert counts == before_counts
            # Complete Hand fixture uses generated legal Plays, never maintainer data.
            page = complete_hand(http, locale)
            active = server.app_context.managed_stateful.active_match
            counts.clear()
            with accounting():
                cdp.navigate(server.origin + "/matches/position/1")
                result = landing(case_id, "complete-hand-initial-landing")
                before = active.path.read_bytes()
                assert build_observed_game_evidence_summary_v1(active.workspace.slots[0].observed_game).complete_initial_deal_reconstructable
                assert materialize_match_observed_game_historical_v1(active.workspace, match_position=1).status == "available"
                assert not cdp.evaluate("!!document.querySelector('button[value=discarded_cards_empty]')")
                assert active.path.read_bytes() == before and not counts
            # Construct a legacy [] through its independent existing contract.
            page = follow(http, http.submit(independent_form(http, "set_discarded_cards", "discarded_cards_empty")))
            counts.clear()
            with accounting():
                cdp.navigate(server.origin + "/matches/position/1")
                landing(case_id, "legacy-hand-initial-landing")
                reveal('#match-declaration input[name="hand_game"]')
                click(cdp, '#match-declaration input[name="hand_game"]')
                submit('#match-declaration button[value="set_declaration"]')
                assert active.workspace.slots[0].observed_game.discarded_cards == () and counts["recording_writes"] == 0
                counts.clear()
                submit('button[value="discarded_cards_unknown"]')
                result = landing(case_id, "legacy-withdrawal-initial-landing")
                case["steps"].append(snapshot(active, "legacy-withdrawn"))
                assert active.workspace.slots[0].observed_game.discarded_cards is None
                assert active.workspace.slots[0].observed_game.declaration.hand_game
                assert not cdp.evaluate("document.querySelector('#match-declaration input[name=hand_game]').checked")
                assert counts == Counter(set_discarded_cards=1, recording_saves=1, recording_writes=1)
                assert materialize_match_observed_game_historical_v1(active.workspace, match_position=1).status == "available"
                reveal('#match-declaration button[value="set_declaration"]')
                submit('#match-declaration button[value="set_declaration"]')
                case["steps"].append(snapshot(active, "explicit-non-hand-declaration"))
                assert not active.workspace.slots[0].observed_game.declaration.hand_game
                assert counts["set_declaration"] == 1 and counts["recording_writes"] == 2
                assert materialize_match_observed_game_historical_v1(active.workspace, match_position=1).unavailable_reason == "discarded_cards_unavailable"
            case["requests"] = requests()
        if args.phase == "after":
            source_game(http, name="Anna <&> " + "Long-name-" * 10)
            counts.clear()
            with accounting():
                cdp.navigate(server.origin + "/matches/position/1")
                landing("long-name", "initial-landing")
                layouts("long-name")
                assert not counts
        else:
            complete_hand(http)
            active = server.app_context.managed_stateful.active_match
            report["baseline_hand"] = {"capability": build_observed_game_evidence_summary_v1(active.workspace.slots[0].observed_game).to_dict(), "historical": materialize_match_observed_game_historical_v1(active.workspace, match_position=1).status}
            assert not report["baseline_hand"]["capability"]["complete_initial_deal_reconstructable"]
        report["completed"] = True
    finally:
        report["elapsed_seconds"] = round(time.perf_counter() - began, 3)
        (args.output / "evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({"completed": report["completed"], "cases": len(report["cases"]), "landings": len(report["landings"]), "layouts": len(report["measurements"]), "elapsed_seconds": report["elapsed_seconds"], "evidence": str(args.output / "evidence.json")}))


if __name__ == "__main__":
    main()
