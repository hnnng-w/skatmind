# ruff: noqa: E501 - Keep native browser probes legible.
"""Disposable Issue #296 source-tree checks, not installed maintainer UAT."""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
import json
import os
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_evidence_presentation import HAND, complete_hand, source_game  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.match_frontend as frontend  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.match_historical_materialization import (  # noqa: E402
    materialize_match_observed_game_historical_v1,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    started = time.perf_counter()
    report = {"completed": False, "phase": args.phase, "python": sys.version,
              "browser": local.version, "cases": [], "measurements": [],
              "scope": "Disposable source-tree HTTP; emulated viewports, actual zoom 1"}
    report["source_sha256"] = {name: hashlib.sha256(importlib.resources.files(
        "skatmind.app_web").joinpath(name).read_bytes()).hexdigest() for name in (
            "assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json",
            "match_recovery_rendering.py", "task_first_match_rendering.py", "card_entry_http.py",
            "match_evidence_presentation.py", "match_evidence_feedback.py")
        if importlib.resources.files("skatmind.app_web").joinpath(name).is_file()}
    counts = Counter()
    real_replace = os.replace
    real_operation = frontend.apply_unified_match_operation_v1

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

    def submit(selector, *, pointer=True):
        if pointer:
            click(cdp, selector)
        else:
            tab_to(cdp, selector)
            keyboard(cdp, "Enter", "Enter", 13, "\r")
        time.sleep(.6)

    def reveal(selector):
        # Only after the initial landing capture; activate actual native summaries.
        summaries = cdp.evaluate("(()=>{let e=document.querySelector(" + json.dumps(selector) + ");let a=[];while(e){if(e.tagName==='DETAILS'&&!e.open){const s=e.querySelector('summary');s.id='probe-summary-'+a.length;a.push('#'+s.id)}e=e.parentElement}return a.reverse()})()")
        for summary in summaries:
            click(cdp, summary)

    def snapshot(active, stage):
        raw = active.path.read_bytes()
        game = active.workspace.slots[0].observed_game
        return {"stage": stage, "counts": dict(counts), "revision": active.workspace.revision,
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "plays": [p.to_dict() for p in game.plays],
                "hand": game.perspective_initial_hand, "skat": game.original_skat,
                "discards": game.discarded_cards,
                "receipt": cdp.evaluate("document.querySelector('[data-operation-feedback]')?.textContent"),
                "error": cdp.evaluate("document.querySelector('.error-summary')?.textContent")}

    def delivered_receipt():
        token = cdp.evaluate("document.querySelector('input[name=_frontend_language_context]').value")
        return server.app_context.language_context.pages[token].feedback

    def measure(case, stage):
        data = cdp.evaluate("""(()=>{const ids=['match-recovery','match-accepted-perspective_initial_hand','match-accepted-original_skat','match-accepted-discarded_cards'];return {width:innerWidth,height:innerHeight,document:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,focus:document.activeElement.outerHTML,areas:ids.map(id=>{const e=document.getElementById(id);return e?{id,text:e.textContent,visible:e.checkVisibility(),width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}:null})}})()""")
        data.update(case=case, stage=stage, zoom=cdp.call("Page.getLayoutMetrics")["cssVisualViewport"].get("zoom"))
        data["controls"] = cdp.evaluate("[...document.querySelectorAll('#match-recovery button,#match-hand-evidence button,.compact-card')].filter(e=>e.checkVisibility()).map(e=>({tag:e.tagName,height:e.getBoundingClientRect().height,font:getComputedStyle(e).fontSize,input:e.querySelector('input')?.getBoundingClientRect().width}))")
        data["suit_rows"] = cdp.evaluate("[...document.querySelectorAll('.compact-cards[data-balanced-grid] .compact-card-group')].filter(e=>e.checkVisibility()).map(e=>{let rows={};for(const c of e.querySelectorAll('.compact-card')){const y=c.getBoundingClientRect().y;(rows[y]??=[]).push(c.querySelector('input').value)}return Object.values(rows)})")
        report["measurements"].append(data)
        cdp.screenshot(args.output / f"{case}-{stage}-{data['width']}.png")
        assert data["document"] == data["client"] and data["zoom"] == 1

    try:
        browser = Browser(server)
        cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0], value=browser.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
        for locale, script in (("de", False), ("en", False), ("de", True), ("en", True)):
            case_id = f"{locale}-{int(script)}"
            page = source_game(browser, locale)
            for card in ("SA", "SK", "S7"):
                page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
            active = server.app_context.managed_stateful.active_match
            counts.clear()
            counts.update({name: 0 for name in ("recording_writes", "recording_saves", "profile_writes", "analysis", "set_declaration")})
            cdp.events.clear()
            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
            with ExitStack() as stack:
                for module, name, callback in (
                    (os, "replace", replaced), (frontend, "apply_unified_match_operation_v1", operated),
                    (capture, "save_match_workspace_file_v1", counted("recording_saves", capture.save_match_workspace_file_v1)),
                    (profile, "save_frontend_profile_file_v1", counted("profile_writes", profile.save_frontend_profile_file_v1)),
                    (analysis, "execute_match_decision_analysis_v1", counted("analysis", analysis.execute_match_decision_analysis_v1)),
                    (analysis, "execute_match_historical_analysis_v1", counted("analysis", analysis.execute_match_historical_analysis_v1)),
                ):
                    stack.enter_context(patch.object(module, name, callback))
                cdp.navigate(server.origin + "/matches/position/1")
                measure(case_id, "initial-landing")
                steps = [snapshot(active, "initial")]
                case = {"locale": locale, "javascript": script, "steps": steps}
                report["cases"].append(case)
                submit('#match-play-1 form[action="/matches/recovery/select"]:first-of-type button')
                click(cdp, '#match-recovery input[name="card"][value="S10"]')
                submit('#match-recovery form[action="/matches/recovery/preview"] button', pointer=False)
                measure(case_id, "replacement-preview")
                assert "15 → 14" in cdp.evaluate("document.querySelector('#match-recovery').textContent")
                steps.append(snapshot(active, "preview"))
                assert steps[-1]["sha256"] == steps[0]["sha256"]
                submit('#match-recovery form[action="/matches/recovery/apply"] button')
                steps.append(snapshot(active, "replacement-applied"))
                assert counts["recording_writes"] == 1
                submit('#match-play-2 form[action="/matches/recovery/select"]:last-of-type button')
                measure(case_id, "rewind-landing")
                visible = cdp.evaluate("[...document.querySelectorAll('#match-recovery li')].filter(e=>e.checkVisibility()).map(e=>e.textContent)")
                case["initial_visible_rewind_rows"] = visible
                assert bool(visible) == (args.phase == "after")
                if args.phase == "after":
                    assert len(visible) == 3
                    click(cdp, '#match-recovery input[name="confirm_apply"]')
                    for language in (("en" if locale == "de" else "de"), locale):
                        submit('.language-selector button[value="' + language + '"]')
                        assert not cdp.evaluate("document.querySelector('#match-recovery input[name=confirm_apply]').checked")
                    steps.append(snapshot(active, "rewind-language-clears-consent"))
                    assert counts["profile_writes"] == 2 and counts["recording_writes"] == 1
                cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844, deviceScaleFactor=1, mobile=False)
                measure(case_id, "rewind-narrow-landing")
                steps.append(snapshot(active, "rewind-preview"))
                submit('#match-recovery form[action="/matches/recovery/cancel"] button', pointer=False)
                steps.append(snapshot(active, "rewind-cancelled"))
                assert steps[-1]["sha256"] == steps[-2]["sha256"]
                submit('#match-play-2 form[action="/matches/recovery/select"]:last-of-type button')
                submit('#match-recovery form[action="/matches/recovery/apply"] button')
                assert counts["recording_writes"] == 1
                click(cdp, '#match-recovery input[name="confirm_apply"]')
                submit('#match-recovery form[action="/matches/recovery/apply"] button', pointer=False)
                steps.append(snapshot(active, "rewind-applied"))
                assert [p.card for p in active.workspace.slots[0].observed_game.plays] == ["S10"]
                assert counts["recording_writes"] == 2
                # Evidence uses the actual external controls and their native owner.
                reveal('input[name="evidence_perspective_hand"]')
                for card in HAND:
                    click(cdp, f'input[name="evidence_perspective_hand"][value="{card}"]')
                if args.phase == "after":
                    assert active.workspace.slots[0].observed_game.perspective_initial_hand is None
                    assert cdp.evaluate("document.querySelector('#match-accepted-perspective_initial_hand').textContent").endswith("nicht erfasst" if locale == "de" else "not recorded")
                    assert counts["recording_writes"] == 2
                    click(cdp, 'input[name="evidence_perspective_hand"][value="S10"]')
                    submit('button[value="perspective_hand_selected"]', pointer=False)
                    steps.append(snapshot(active, "hand-nine-rejected"))
                    assert "10" in steps[-1]["error"] and steps[-1]["receipt"] is None
                    assert counts["recording_writes"] == 2
                    measure(case_id, "hand-count-rejection-landing")
                    click(cdp, 'input[name="evidence_perspective_hand"][value="S10"]')
                submit('button[value="perspective_hand_selected"]')
                measure(case_id, "accepted-hand-landing")
                if args.phase == "after":
                    cdp.evaluate("document.querySelector('#match-accepted-perspective_initial_hand').scrollIntoView({block:'center'})")
                    measure(case_id, "accepted-status")
                steps.append(snapshot(active, "hand-saved"))
                reveal('input[name="evidence_original_skat"]')
                for card in ("CJ", "D7"):
                    click(cdp, f'input[name="evidence_original_skat"][value="{card}"]')
                submit('button[value="original_skat_selected"]', pointer=False)
                measure(case_id, "overlap-rejection-landing")
                steps.append(snapshot(active, "overlap-rejected"))
                assert steps[-1]["sha256"] == steps[-2]["sha256"]
                if args.phase == "after":
                    assert "Alex" in steps[-1]["error"]
                # Correct the source-checked rejected choices, then exercise no-op/withdraw.
                reveal('input[name="evidence_original_skat"]')
                for card in ("CJ", "HA"):
                    click(cdp, f'input[name="evidence_original_skat"][value="{card}"]')
                submit('button[value="original_skat_selected"]')
                steps.append(snapshot(active, "skat-saved"))
                reveal('input[name="evidence_original_skat"]')
                submit('button[value="original_skat_selected"]', pointer=False)
                steps.append(snapshot(active, "skat-unchanged"))
                assert steps[-1]["sha256"] == steps[-2]["sha256"]
                if args.phase == "after":
                    reveal('input[name="evidence_original_skat"]')
                    for card in ("HA", "D7"):
                        click(cdp, f'input[name="evidence_original_skat"][value="{card}"]')
                    for stage, card in (("skat-empty-rejected", None), ("skat-one-rejected", "HA")):
                        if card:
                            click(cdp, f'input[name="evidence_original_skat"][value="{card}"]')
                        submit('button[value="original_skat_selected"]', pointer=False)
                        steps.append(snapshot(active, stage))
                        assert "2" in steps[-1]["error"] and steps[-1]["receipt"] is None
                        assert counts["recording_writes"] == 4
                    click(cdp, 'input[name="evidence_original_skat"][value="D7"]')
                    submit('button[value="original_skat_selected"]', pointer=False)
                    steps.append(snapshot(active, "skat-restored-noop"))
                    assert counts["recording_writes"] == 4
                reveal('button[value="original_skat_unknown"]')
                submit('button[value="original_skat_unknown"]', pointer=False)
                steps.append(snapshot(active, "skat-withdrawn"))
                assert counts["recording_writes"] == counts["recording_saves"] == 5
                assert counts["analysis"] == counts["set_declaration"] == 0
                assert counts["profile_writes"] == (2 if args.phase == "after" else 0)
                if args.phase == "after":
                    assert steps[-2]["receipt"] and steps[-1]["receipt"]
                    delivered = delivered_receipt()
                    assert delivered is not None
                    submit('.language-selector button[value="' + ("en" if locale == "de" else "de") + '"]')
                    translated = delivered_receipt()
                    if script:
                        assert translated.receipt is delivered.receipt
                        assert translated.remaining_ms < delivered.remaining_ms
                    else:
                        assert translated is None
                    steps.append(snapshot(active, "authorized-language"))
                    assert counts["profile_writes"] == 3 and counts["recording_writes"] == 5
                    assert steps[-1]["sha256"] == steps[-2]["sha256"]
                cdp.evaluate("void 0")
                case["submitted_controls"] = [parse_qsl(e["params"]["request"].get("postData", ""), keep_blank_values=True) for e in cdp.events if e["params"]["request"]["method"] == "POST"]
                if args.phase == "after":
                    # Fully recorded Hand; only retained discard evidence is missing.
                    complete_hand(browser, locale)
                    active = server.app_context.managed_stateful.active_match
                    counts.clear()
                    cdp.events.clear()
                    counts.update({name: 0 for name in ("recording_writes", "recording_saves", "profile_writes", "analysis", "set_declaration")})
                    assert materialize_match_observed_game_historical_v1(active.workspace, match_position=1).unavailable_reason == "discarded_cards_unavailable"
                    cdp.navigate(server.origin + "/matches/review/1")
                    measure(case_id, "hand-review-landing")
                    hand_steps = [snapshot(active, "hand-null-review")]
                    case["hand_steps"] = hand_steps
                    link = 'a[href="/matches/position/1#match-hand-evidence"]'
                    assert cdp.evaluate('document.querySelector(' + json.dumps(link) + ').checkVisibility()')
                    click(cdp, link)
                    time.sleep(.6)
                    measure(case_id, "hand-remedy-landing")
                    button = 'button[value="discarded_cards_empty"]'
                    assert cdp.evaluate('document.querySelector(' + json.dumps(button) + ').checkVisibility()')
                    assert cdp.evaluate('document.querySelector(' + json.dumps(button) + ').form.id') == "match-recording-input"
                    hand_steps.append(snapshot(active, "native-remedy-open"))
                    assert counts["recording_writes"] == counts["profile_writes"] == counts["analysis"] == 0
                    submit(button, pointer=False)
                    hand_steps.append(snapshot(active, "explicit-empty"))
                    assert active.workspace.slots[0].observed_game.discarded_cards == ()
                    assert materialize_match_observed_game_historical_v1(active.workspace, match_position=1).status == "available"
                    assert counts["recording_writes"] == 1
                    reveal('button[value="discarded_cards_unknown"]')
                    submit('button[value="discarded_cards_unknown"]', pointer=False)
                    hand_steps.append(snapshot(active, "explicit-withdrawal"))
                    assert active.workspace.slots[0].observed_game.discarded_cards is None
                    assert materialize_match_observed_game_historical_v1(active.workspace, match_position=1).unavailable_reason == "discarded_cards_unavailable"
                    assert counts["recording_writes"] == counts["recording_saves"] == 2
                    assert counts["analysis"] == counts["profile_writes"] == counts["set_declaration"] == 0
                    cdp.evaluate("void 0")
                    case["hand_submitted_controls"] = [parse_qsl(e["params"]["request"].get("postData", ""), keep_blank_values=True) for e in cdp.events if e["params"]["request"]["method"] == "POST"]
                    if locale == "en" and script:
                        name = "Alexandra-Maria von Hohenlohe-Schillingsfuerst with a long synthetic name"
                        page = source_game(browser, locale, name=name)
                        page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"), cards=HAND))
                        for card in ("SA", "SK", "S7"):
                            page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
                        active = server.app_context.managed_stateful.active_match
                        counts.clear()
                        before = active.path.read_bytes()
                        for width, height in ((1365, 900), (390, 844)):
                            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
                            cdp.navigate(server.origin + "/matches/position/1")
                            measure("long-name", "initial-landing")
                            cdp.evaluate("document.querySelector('#match-accepted-perspective_initial_hand').scrollIntoView({block:'center'})")
                            measure("long-name", "accepted-status")
                            submit('#match-play-1 form[action="/matches/recovery/select"]:last-of-type button')
                            measure("long-name", "rewind-first-landing")
                            tab_to(cdp, '#match-recovery input[name="confirm_apply"]')
                            measure("long-name", "confirmation-focus")
                            submit('#match-recovery form[action="/matches/recovery/cancel"] button', pointer=False)
                        assert not counts and active.path.read_bytes() == before
                        case["long_name_passive_counts"] = dict(counts)
        report["completed"] = True
    finally:
        report["elapsed_seconds"] = time.perf_counter() - started
        (args.output / "evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": report["completed"], "cases": len(report["cases"]), "elapsed_seconds": report["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
