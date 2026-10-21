# ruff: noqa: E501 - Keep complete native browser probes legible.
"""Issue #292 follow-up: disposable native reload/language and implicit-Enter evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from contextlib import ExitStack
from itertools import count
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_direct_match_evidence import started  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_recorded_decision_context import MATCH_HAND  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from verify_recording_deletion import click, keyboard, tab_to  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.match_frontend as frontend  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402


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
    browsers = [LocalBrowser(args.browser, args.output / name) for name in ("first-profile", "second-profile")]
    cdp, other = (browser.cdp for browser in browsers)
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "browser": browsers[0].version, "base_head": "27431d03df7e4ee0e157ed4e0b3e191e68e5db4e",
        "scope": "source-tree synthetic", "cases": []}
    counts = Counter()
    disclosures = count()
    real_replace, real_operation = os.replace, frontend.apply_unified_match_operation_v1
    real_response = Handler.send_response

    def response(handler, code, *a, **kw):
        if handler.command == "POST":
            counts[f"post_{int(code)}"] += 1
        return real_response(handler, code, *a, **kw)

    def replacement(source, destination):
        if Path(destination).parent == server.app_context.managed_stateful.root("matches"):
            counts["recording_writes"] += 1
        return real_replace(source, destination)

    def operation(active, values):
        counts[values["operation"]] += 1
        return real_operation(active, values)

    def counted(name, real):
        def wrapper(*a, **kw):
            counts[name] += 1
            return real(*a, **kw)
        return wrapper

    def settle():
        time.sleep(.65)
        cdp.evaluate("void 0")

    def open_ancestors(selector):
        # Only locate disclosures; activation uses actual pointer events.
        prefix = f"probe-disclosure-{next(disclosures)}-"
        ancestors = cdp.evaluate("(()=>{let e=document.querySelector(" + json.dumps(selector) + ");const a=[];while(e){if(e.tagName==='DETAILS'&&!e.open){const s=e.querySelector(':scope > summary');s.id=" + json.dumps(prefix) + "+a.length;a.push('#'+s.id)}e=e.parentElement}return a.reverse()})()")
        for summary in ancestors:
            click(cdp, summary)

    def choose(selector, value):
        open_ancestors(selector)
        index = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].findIndex(o=>o.value===" + json.dumps(value) + ")")
        assert index >= 0
        click(cdp, selector)
        keyboard(cdp, "Escape", "Escape", 27)
        keyboard(cdp, "Home", "Home", 36)
        for _ in range(index):
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Enter", "Enter", 13)

    def enter(selector, value):
        open_ancestors(selector)
        click(cdp, selector)
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA", windowsVirtualKeyCode=65, modifiers=2)
        cdp.call("Input.insertText", text=value)

    def explicit_button(selector, *, keys=False):
        open_ancestors(selector)
        if keys:
            tab_to(cdp, selector)
            keyboard(cdp, "Enter", "Enter", 13, "\r")
        else:
            click(cdp, selector)

    def snapshot(active):
        game = active.workspace.slots[0].observed_game
        return {"revision": active.workspace.revision, "fingerprint": active.capture.content_fingerprint,
            "accepted_declaration": game.to_dict()["declaration"],
            "initial_hand": game.perspective_initial_hand, "discards": game.discarded_cards,
            "bid_control": cdp.evaluate("document.querySelector('#match-declaration [name=bid_value]')?.value"),
            "matador_control": cdp.evaluate("document.querySelector('#match-declaration [name=matadors]')?.value")}

    def observe(case, name, active, action):
        counts.clear()
        cdp.events.clear()
        before = snapshot(active)
        action()
        settle()
        after = snapshot(active)
        requests = [{"route": urlsplit(e["params"]["request"]["url"]).path,
            "fields": parse_qs(e["params"]["request"].get("postData", ""), keep_blank_values=True)}
            for e in cdp.events if e["params"]["request"]["method"] == "POST"]
        observation = {"name": name, "before": before, "after": after,
            "requests": requests, "counts": dict(counts)}
        case["actions"].append(observation)
        return observation

    try:
        client = Browser(server)
        for tab in (cdp, other):
            tab.call("Network.setCookie", name=client.cookie.split("=", 1)[0],
                value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
        with ExitStack() as stack:
            for module, name, wrapper in (
                (os, "replace", replacement), (frontend, "apply_unified_match_operation_v1", operation),
                (Handler, "send_response", response),
                (capture, "save_match_workspace_file_v1", counted("save_calls", capture.save_match_workspace_file_v1)),
                (profile, "save_frontend_profile_file_v1", counted("profile_writes", profile.save_frontend_profile_file_v1)),
            ):
                stack.enter_context(patch.object(module, name, wrapper))
            for locale, script in (("en", False), ("de", False), ("en", True), ("de", True)):
                case = {"locale": locale, "javascript": script, "actions": []}
                evidence["cases"].append(case)
                started(client, locale=locale)
                active = server.app_context.managed_stateful.active_match
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                cdp.navigate(server.origin + "/matches/position/1")
                choose('#match-declaration [name=game_type]', "grand")
                enter('#match-declaration [name=bid_value]', "18")
                for card in ("H7", "D7"):
                    selector = f'input[name=evidence_discarded_cards][value={card}]'
                    open_ancestors(selector)
                    click(cdp, selector)
                observe(case, "evidence", active, lambda: click(cdp, 'button[value=discarded_cards_selected]'))
                assert snapshot(active)["bid_control"] == "18" and active.workspace.slots[0].observed_game.declaration is None
                target = "de" if locale == "en" else "en"
                observe(case, "immediate_language", active, lambda target=target: cdp.activate('.language-selector button[value=' + target + ']'))
                assert snapshot(active)["bid_control"] == "18"
                saved = active.path.read_bytes()
                other.navigate(server.origin + "/matches/position/1")
                assert other.evaluate("document.querySelector('#match-declaration [name=bid_value]').value") == ""
                result = observe(case, "stale_language_after_reload", active,
                    lambda locale=locale: cdp.activate('.language-selector button[value=' + locale + ']'))
                assert (result["after"]["bid_control"] == "18") == (args.phase == "before")
                assert active.path.read_bytes() == saved
                assert counts["recording_writes"] == counts["set_declaration"] == 0
                assert counts["profile_writes"] == int(args.phase == "before")
                assert counts["post_303" if args.phase == "before" else "post_409"] == 1
                cdp.screenshot(args.output / f"{locale}-{int(script)}-language.png")

                started(client, context="non_hand", locale=locale)
                active = server.app_context.managed_stateful.active_match
                cdp.navigate(server.origin + "/matches/position/1")
                for card in MATCH_HAND:
                    selector = f'input[name=evidence_perspective_hand][value="{card}"]'
                    open_ancestors(selector)
                    click(cdp, selector)
                for field, value in (("bid_value", "19"), ("matadors", "2")):
                    enter('#match-declaration [name=' + field + ']', value)
                    result = observe(case, "implicit_" + field, active,
                        lambda: keyboard(cdp, "Enter", "Enter", 13, "\r"))
                    request, = result["requests"]
                    expected = "perspective_hand_selected" if args.phase == "before" else "set_declaration"
                    assert request["fields"]["recording_action"] == [expected], result
                    assert counts["set_perspective_hand"] == int(args.phase == "before")
                    assert counts["set_declaration"] == int(args.phase == "after")
                    assert counts["recording_writes"] == int(field == "bid_value" or args.phase == "after")
                    assert counts["profile_writes"] == 0
                    if args.phase == "after":
                        assert active.workspace.slots[0].observed_game.perspective_initial_hand is None
                    cdp.screenshot(args.output / f"{locale}-{int(script)}-{field}.png")
                if args.phase == "after":
                    enter('#match-declaration [name=matadors]', "invalid")
                    result = observe(case, "implicit_invalid_matadors", active,
                        lambda: keyboard(cdp, "Enter", "Enter", 13, "\r"))
                    assert result["requests"][0]["fields"]["recording_action"] == ["set_declaration"]
                    assert counts["post_400"] == 1 and counts["recording_writes"] == 0
                    assert counts["set_declaration"] == counts["set_perspective_hand"] == 0
                    assert result["after"]["accepted_declaration"] == result["before"]["accepted_declaration"]

                    started(client, locale=locale)
                    active = server.app_context.managed_stateful.active_match
                    cdp.navigate(server.origin + "/matches/position/1")
                    choose('#match-declaration [name=game_type]', "grand")
                    enter('#match-declaration [name=bid_value]', "invalid")
                    result = observe(case, "implicit_incomplete", active,
                        lambda: keyboard(cdp, "Enter", "Enter", 13, "\r"))
                    assert result["requests"] == [] and counts["recording_writes"] == 0
                    for prefix, cards in (("perspective_hand", MATCH_HAND),
                                          ("original_skat", ("SA", "S7")),
                                          ("discarded_cards", ("SA", "S7"))):
                        for use_keys in (False, True):
                            for card in cards:
                                selector = f'input[name="evidence_{prefix}"][value="{card}"]'
                                open_ancestors(selector)
                                click(cdp, selector)
                            for intent, keys, writes in (("selected", use_keys, 1), ("selected", not use_keys, 0),
                                                         ("unknown", use_keys, 1)):
                                action = prefix + "_" + intent
                                result = observe(case, "explicit_" + action + ("_keys" if keys else "_pointer"), active,
                                    lambda action=action, keys=keys: explicit_button('button[value="' + action + '"]', keys=keys))
                                assert result["requests"][0]["fields"]["recording_action"] == [action]
                                assert counts["set_" + prefix] == 1 and counts["recording_writes"] == writes
                                assert counts["set_declaration"] == counts["profile_writes"] == 0
                                assert result["after"]["bid_control"] == "invalid"
                                assert result["after"]["accepted_declaration"] is None
                    for keys, writes in ((False, 1), (True, 0)):
                        result = observe(case, "explicit_empty_" + str(keys), active,
                            lambda keys=keys: explicit_button('button[value=discarded_cards_empty]', keys=keys))
                        assert result["requests"][0]["fields"]["recording_action"] == ["discarded_cards_empty"]
                        assert counts["set_discarded_cards"] == 1 and counts["recording_writes"] == writes
                        assert counts["set_declaration"] == counts["profile_writes"] == 0
                        assert active.workspace.slots[0].observed_game.discarded_cards == ()
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        for browser in browsers:
            browser.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "cases": len(evidence["cases"]), "phase": args.phase}))


if __name__ == "__main__":
    main()
