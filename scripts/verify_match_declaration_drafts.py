# ruff: noqa: E501 - Keep complete browser probes legible, as in the sibling verification tools.
"""Disposable source-tree browser evidence for Issue #292 (not installed UAT)."""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT / "tests"))
if "--baseline-archive" in sys.argv:
    archive = sys.argv[sys.argv.index("--baseline-archive") + 1]
    sys.path.insert(0, str(Path(archive)) + "/src")

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.match_frontend as match_frontend  # noqa: E402
import skatmind.capture_web.analysis as analysis  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402

if "--baseline-archive" not in sys.argv:
    from skatmind.app_web.match_declaration_drafts import DeclarationDraftReturn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline-archive", type=Path)
    args = parser.parse_args()
    assert (".zip" in match_frontend.__file__) == (args.phase == "before")
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
                "browser": local.version, "cases": [], "scope": "source-tree synthetic",
                "loaded_module": match_frontend.__file__,
                "base_head": "9709cb1420d8a9c2158f66d7665f7d7f896f6202"}
    counts = Counter()
    real_save = capture.save_match_workspace_file_v1
    real_operation = match_frontend.apply_unified_match_operation_v1
    real_replace = os.replace

    def save(*a, **kw):
        counts["recording_save"] += 1
        return real_save(*a, **kw)

    def operation(active, values):
        counts[values["operation"]] += 1
        return real_operation(active, values)

    def replace(source, destination):
        if Path(destination).parent == server.app_context.managed_stateful.root("matches"):
            counts["recording_replace"] += 1
        return real_replace(source, destination)

    def counted(name, real):
        def wrapper(*a, **kw):
            counts[name] += 1
            return real(*a, **kw)
        return wrapper

    def snapshot(active):
        game = active.workspace.slots[0].observed_game
        return {"revision": active.workspace.revision,
                "fingerprint": active.capture.content_fingerprint,
                "declarer": game.declarer_player_id,
                "declaration": game.to_dict()["declaration"],
                "discards": game.discarded_cards,
                "visible": cdp.evaluate("Object.fromEntries([...document.querySelectorAll("
                    "'#match-declaration input:not([type=hidden]),#match-declaration select')]"
                    ".map(e=>[e.name,e.type==='checkbox'?e.checked:e.value]))")}

    try:
        browser = Browser(server)
        cdp.call("Network.setCookie", name=browser.cookie.split("=", 1)[0],
                 value=browser.cookie.split("=", 1)[1], url=server.origin,
                 httpOnly=True, sameSite="Strict")
        for locale, script in (("en", False), ("de", False), ("en", True), ("de", True)):
            page = browser.page("/matches/new")
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
            page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
                match_title="Synthetic declaration draft", forehand_name="Anna",
                middlehand_name="Bea", rearhand_name="Clara", perspective_seat="middlehand",
                setup_action="update"))
            page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
                                                  setup_action="create"))
            follow(browser, browser.submit(operation_form(page, "start_game")))
            active = server.app_context.managed_stateful.active_match
            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                     deviceScaleFactor=1, mobile=False)
            cdp.navigate(server.origin + "/matches/position/1")
            # Native keys change actual visible controls; no injected request fields.
            bea_index = cdp.evaluate("[...document.querySelector('select[name=declarer_player_id]').options]"
                ".findIndex(o=>o.textContent.startsWith('Bea'))")
            assert bea_index > 0
            for selector, downs in (("select[name=declarer_player_id]", bea_index),
                                    ("select[name=game_type]", 5)):
                click(cdp, "#match-declaration " + selector)
                keyboard(cdp, "Escape", "Escape", 27)
                keyboard(cdp, "Home", "Home", 36)
                for _ in range(downs):
                    keyboard(cdp, "ArrowDown", "ArrowDown", 40)
                keyboard(cdp, "Enter", "Enter", 13)
            click(cdp, '#match-declaration input[name="bid_value"]')
            cdp.call("Input.insertText", text="18")
            before = snapshot(active)
            assert before["visible"]["game_type"] == "grand"
            assert before["visible"]["bid_value"] == "18"
            assert cdp.evaluate("document.querySelector('select[name=declarer_player_id]')"
                                ".selectedOptions[0].textContent.startsWith('Bea')")
            cdp.screenshot(args.output / f"{locale}-{int(script)}-before.png")
            editor = ('fieldset:has(input[name="evidence_discarded_cards"])'
                      if args.phase == "after" else 'form:has(input[value="discarded_cards_selected"])')
            submitter = ('button[name="recording_action"][value="discarded_cards_selected"]'
                         if args.phase == "after" else editor + ' button[type="submit"]')
            cdp.evaluate("document.querySelector(" + json.dumps(editor)
                         + ").closest('details').querySelector('summary').id='probe-evidence'")
            click(cdp, "#probe-evidence")
            for card in ("H7", "D7"):
                click(cdp, editor + f' input[value="{card}"]')
            counts.clear()
            counts.update({name: 0 for name in ("set_declaration", "profile_write", "analysis")})
            cdp.events.clear()
            with ExitStack() as stack:
                measurements = [
                    (capture, "save_match_workspace_file_v1", save),
                    (match_frontend, "apply_unified_match_operation_v1", operation),
                    (os, "replace", replace),
                    (profile, "save_frontend_profile_file_v1", counted("profile_write", profile.save_frontend_profile_file_v1)),
                    (analysis, "execute_match_decision_analysis_v1", counted("analysis", analysis.execute_match_decision_analysis_v1)),
                    (analysis, "execute_match_historical_analysis_v1", counted("analysis", analysis.execute_match_historical_analysis_v1)),
                ]
                if args.phase == "after":
                    measurements.append((DeclarationDraftReturn, "take",
                        counted("draft_return", DeclarationDraftReturn.take)))
                for module, name, callback in measurements:
                    stack.enter_context(patch.object(module, name, callback))
                click(cdp, submitter)
                time.sleep(.7)
                after = snapshot(active)
                case = {"locale": locale, "javascript": script, "before": before, "after": after,
                        "operations": dict(counts), "steps": []}
                evidence["cases"].append(case)
                cdp.screenshot(args.output / f"{locale}-{int(script)}-after.png")
                assert after["declarer"] is after["declaration"] is None
                assert set(after["discards"]) == {"H7", "D7"}
                assert counts["recording_save"] == counts["recording_replace"] == 1
                assert counts["set_discarded_cards"] == 1 and counts["set_declaration"] == 0
                assert (after["visible"] == before["visible"]) == (args.phase == "after")
                if args.phase == "after":
                    def open_evidence(editor=editor):
                        cdp.evaluate("document.querySelector(" + json.dumps(editor)
                            + ").closest('details').querySelector('summary').id='probe-evidence'")
                        if not cdp.evaluate("document.querySelector('#probe-evidence').parentElement.open"):
                            click(cdp, "#probe-evidence")

                    open_evidence()
                    click(cdp, editor + ' input[value="D7"]')
                    cdp.activate(submitter)
                    invalid = snapshot(active)
                    assert invalid["visible"] == before["visible"]
                    assert cdp.evaluate("!!document.querySelector('.error-summary')")
                    assert counts["recording_save"] == 1
                    assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
                    case["steps"].append({"kind": "invalid", "source": invalid, "counts": dict(counts)})
                    for width, height in ((1365, 900), (390, 844)):
                        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                                 deviceScaleFactor=1, mobile=False)
                        cdp.evaluate("document.querySelector('.error-summary').scrollIntoView({block:'start'})")
                        cdp.screenshot(args.output / f"{locale}-{int(script)}-error-{width}.png")
                        assert cdp.evaluate("document.documentElement.scrollWidth===document.documentElement.clientWidth")
                    click(cdp, editor + ' input[value="D7"]')
                    tab_to(cdp, submitter)
                    keyboard(cdp, "Enter", "Enter", 13, "\r")
                    time.sleep(.7)
                    unchanged = snapshot(active)
                    assert unchanged["visible"] == before["visible"]
                    assert counts["recording_save"] == 1
                    case["steps"].append({"kind": "unchanged", "source": unchanged, "counts": dict(counts)})
                    cdp.activate('#match-declaration button[value="set_declaration"]')
                    accepted = snapshot(active)
                    assert accepted["declaration"]["game_type"] == "grand"
                    assert accepted["declaration"]["bid_value"] == 18
                    assert counts["set_declaration"] == 1
                    assert counts["recording_save"] == counts["recording_replace"] == 2
                    assert counts["profile_write"] == 0
                    case["steps"].append({"kind": "explicit_save", "source": accepted, "counts": dict(counts)})
                    # Existing editable declaration: an incomplete, invalid draft
                    # must not validate or change accepted evidence eligibility.
                    cdp.evaluate("document.querySelector('#match-declaration').closest('details')"
                                 ".querySelector('summary').id='probe-correction'")
                    click(cdp, "#probe-correction")
                    click(cdp, '#match-declaration select[name="declarer_player_id"]')
                    keyboard(cdp, "Escape", "Escape", 27)
                    keyboard(cdp, "Home", "Home", 36)
                    keyboard(cdp, "Enter", "Enter", 13)
                    click(cdp, '#match-declaration input[name="bid_value"]')
                    cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA",
                             windowsVirtualKeyCode=65, modifiers=2)
                    cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA",
                             windowsVirtualKeyCode=65, modifiers=2)
                    cdp.call("Input.insertText", text="-3")
                    click(cdp, '#match-declaration input[name="hand_game"]')
                    invalid_draft = snapshot(active)["visible"]
                    assert invalid_draft["declarer_player_id"] == ""
                    assert invalid_draft["bid_value"] == "-3"
                    requests_before = len(cdp.events)
                    cdp.activate('#match-declaration button[value="set_declaration"]')
                    assert not any(e["params"]["request"]["method"] == "POST"
                                   for e in cdp.events[requests_before:])
                    assert not cdp.evaluate("document.querySelector('#match-recording-input').checkValidity()")
                    assert not cdp.evaluate("!!document.querySelector('[value=discarded_cards_empty]')")
                    open_evidence()
                    for card in ("H8", "D8"):
                        click(cdp, f'input[name="evidence_original_skat"][value="{card}"]')
                    cdp.activate('button[value="original_skat_selected"]')
                    assert snapshot(active)["visible"] == invalid_draft, (snapshot(active), invalid_draft, dict(counts))
                    assert active.workspace.slots[0].observed_game.declaration.bid_value == 18
                    assert counts["set_declaration"] == 1 and counts["recording_replace"] == 3
                    cdp.activate('.language-selector button[value="' + ("de" if locale == "en" else "en") + '"]')
                    assert snapshot(active)["visible"] == invalid_draft
                    assert counts["profile_write"] == 1 and counts["recording_replace"] == 3
                    assert counts["analysis"] == 0
                    case["steps"].append({"kind": "incomplete_and_language", "source": snapshot(active),
                                          "counts": dict(counts)})
                    cdp.evaluate("document.querySelector('#match-declaration').closest('details')"
                                 ".querySelector('summary').id='probe-correction'")
                    if not cdp.evaluate("document.querySelector('#probe-correction').parentElement.open"):
                        click(cdp, "#probe-correction")
                    cdp.evaluate("document.querySelector('#match-declaration').scrollIntoView({block:'start'})")
                    cdp.screenshot(args.output / f"{locale}-{int(script)}-draft-390.png")
            payloads = [parse_qsl(e["params"]["request"].get("postData", ""),
                                 keep_blank_values=True) for e in cdp.events
                        if e["params"]["request"]["method"] == "POST"]
            case["submitted_controls"] = payloads
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "cases": len(evidence["cases"]),
                      "scope": evidence["scope"]}))


if __name__ == "__main__":
    main()
