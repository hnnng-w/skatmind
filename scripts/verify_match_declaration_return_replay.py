# ruff: noqa: E501 - Keep native browser probes and evidence assertions legible.
"""Disposable #292 consumed-return replay evidence; no installed-UAT claim."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_declaration_drafts import create_replay_match  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402
from verify_recording_deletion import click, keyboard  # noqa: E402

import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
import skatmind.app_web.match_frontend as frontend  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text  # noqa: E402


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
    browsers = [LocalBrowser(args.browser, args.output / name) for name in ("original-profile", "replay-profile")]
    cdp, other = (browser.cdp for browser in browsers)
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "browser": browsers[0].version, "base_head": "b1b4bd2f0e7d14fd9c8af9fd328a62dec450a23b",
        "scope": "source-tree synthetic", "cases": []}
    counts, trace, locations = Counter(), [], []
    hold, waiting, release = Event(), Event(), Event()
    real_replace, real_operation = os.replace, frontend.apply_unified_match_operation_v1
    real_response, real_header = Handler.send_response, Handler.send_header
    real_return, real_profile = Handler._consume_profile_redirect_return, profile.save_frontend_profile_file_v1

    def replace(source, destination):
        if Path(destination).parent == server.app_context.managed_stateful.root("matches"):
            counts["recording_writes"] += 1
        return real_replace(source, destination)

    def operation(active, values):
        counts[values["operation"]] += 1
        return real_operation(active, values)

    def save_profile(*a, **kw):
        counts["profile_writes"] += 1
        return real_profile(*a, **kw)

    def response(handler, code, *a, **kw):
        trace.append({"method": handler.command, "path": handler.path, "status": int(code)})
        return real_response(handler, code, *a, **kw)

    def header(handler, name, value):
        if name.lower() == "location":
            locations.append({"source": handler.path, "location": value})
        return real_header(handler, name, value)

    def delayed_return(handler, path):
        # Delay the real browser's prepared GET before consumption, without changing
        # any request, source, guard or result. The original handler always runs.
        if hold.is_set() and "?_language_return=" in handler.path:
            waiting.set()
            assert release.wait(20), "Prepared browser delivery was not released"
        return real_return(handler, path)

    def settled(tab):
        for _ in range(100):
            if tab.evaluate("document.readyState==='complete'"):
                return
            time.sleep(.05)
        raise AssertionError("Browser delivery did not complete")

    def visible(tab):
        return tab.evaluate("Object.fromEntries([...document.querySelectorAll('#match-declaration input:not([type=hidden]),#match-declaration select')].map(e=>[e.name,e.type==='checkbox'?e.checked:e.value]))")

    def choose(selector, value):
        index = cdp.evaluate("[...document.querySelector(" + json.dumps(selector) + ").options].findIndex(o=>o.value===" + json.dumps(value) + ")")
        assert index >= 0
        click(cdp, selector)
        keyboard(cdp, "Escape", "Escape", 27)
        keyboard(cdp, "Home", "Home", 36)
        for _ in range(index):
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
        keyboard(cdp, "Enter", "Enter", 13)

    def language_page():
        token = cdp.evaluate("document.querySelector('.language-selector [name=_frontend_language_context]').value")
        return server.app_context.language_context.pages[token]

    try:
        client = Browser(server)
        for tab in (cdp, other):
            tab.call("Network.setCookie", name=client.cookie.split("=", 1)[0],
                value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
        with ExitStack() as stack:
            for module, name, wrapper in ((os, "replace", replace),
                (frontend, "apply_unified_match_operation_v1", operation),
                (profile, "save_frontend_profile_file_v1", save_profile),
                (Handler, "send_response", response), (Handler, "send_header", header),
                (Handler, "_consume_profile_redirect_return", delayed_return)):
                stack.enter_context(patch.object(module, name, wrapper))
            for locale, script in (("en", False), ("de", False), ("en", True), ("de", True)):
                for kind in ("unused", "prepared", "immediate"):
                    hold.clear()
                    waiting.clear()
                    release.clear()
                    create_replay_match(client, locale)
                    active = server.app_context.managed_stateful.active_match
                    for tab in (cdp, other):
                        tab.call("Emulation.setScriptExecutionDisabled", value=not script)
                    cdp.navigate(server.origin + "/matches/position/1")
                    bea = cdp.evaluate("[...document.querySelector('#match-declaration [name=declarer_player_id]').options].find(o=>o.textContent.startsWith('Bea')).value")
                    choose('#match-declaration [name=declarer_player_id]', bea)
                    choose('#match-declaration [name=game_type]', "grand")
                    click(cdp, '#match-declaration [name=bid_value]')
                    cdp.call("Input.insertText", text="18")
                    draft = visible(cdp)
                    cdp.evaluate("document.querySelector('[name=evidence_discarded_cards]').closest('details').querySelector('summary').id='probe-evidence'")
                    click(cdp, '#probe-evidence')
                    for card in ("H7", "D7"):
                        click(cdp, f'[name=evidence_discarded_cards][value={card}]')
                    counts.clear()
                    trace.clear()
                    locations.clear()
                    cdp.events.clear()
                    before = {"revision": active.workspace.revision, "fingerprint": active.capture.content_fingerprint}
                    click(cdp, 'button[value=discarded_cards_selected]')
                    time.sleep(.6)
                    settled(cdp)
                    location = next(item["location"] for item in locations if item["source"] == "/matches/recording-input")
                    assert "?_declaration_return=" in location
                    assert cdp.evaluate("location.pathname+location.search+location.hash") == location
                    assert visible(cdp) == draft
                    retained = language_page()
                    deadline = retained.native_match_draft_deadline
                    saved, workspace = active.path.read_bytes(), active.workspace
                    game = workspace.slots[0].observed_game
                    assert game.declaration is game.declarer_player_id is None
                    assert set(game.discarded_cards) == {"H7", "D7"}
                    assert counts == {"recording_writes": 1, "set_discarded_cards": 1}
                    case = {"locale": locale, "javascript": script, "kind": kind,
                        "before": before, "delivered_location": location, "draft": draft,
                        "after_evidence": {"revision": workspace.revision, "fingerprint": active.capture.content_fingerprint},
                        "counts_after_evidence": dict(counts)}
                    evidence["cases"].append(case)
                    target = "de" if locale == "en" else "en"
                    selector = '.language-selector button[value=' + target + ']'
                    if kind == "prepared":
                        hold.set()
                        cdp.activate(selector)
                        assert waiting.wait(5)
                        pending, _ = server.app_context.language_context.pending
                        assert pending.native_match_draft_authorization is retained.native_match_draft_authorization
                        assert pending.native_match_draft_deadline == deadline
                        assert counts["profile_writes"] == 1
                    case["counts_before_replay"] = dict(counts)
                    if kind != "immediate":
                        other.navigate(server.origin + location)
                        assert visible(other).get("bid_value") == ""
                        other.call("Page.reload", ignoreCache=True)
                        time.sleep(.5)
                        settled(other)
                        assert other.evaluate("location.pathname+location.search+location.hash") == location
                        path = location.split("#", 1)[0]
                        assert [row["status"] for row in trace if row["path"] == path] == [200, 409, 409]
                        assert counts == Counter(case["counts_before_replay"])
                        assert text(target if kind == "prepared" else locale, "validation.declaration.draft_conflict") in other.evaluate("document.body.textContent")
                    case["counts_after_replay"] = dict(counts)
                    assert time.monotonic() < deadline
                    if kind == "prepared":
                        release.set()
                        time.sleep(.6)
                    else:
                        cdp.activate(selector)
                    settled(cdp)
                    restored = kind == "immediate" or args.phase == "before"
                    if restored:
                        assert visible(cdp) == draft
                        assert language_page().native_match_draft_deadline == deadline
                    else:
                        assert visible(cdp).get("bid_value") != "18"
                        assert text(target if kind == "prepared" else locale, "validation.declaration.draft_conflict") in cdp.evaluate("document.body.textContent")
                    if restored or kind == "prepared":
                        language_location = next(item["location"] for item in locations if item["source"] == "/actions/profile/language")
                        assert any(row == {"method": "GET", "path": language_location,
                            "status": 200 if restored else 409} for row in trace)
                    else:
                        assert {"method": "POST", "path": "/actions/profile/language", "status": 409} in trace
                    assert cdp.evaluate("document.documentElement.lang") == (target if restored or kind == "prepared" else locale)
                    assert counts["profile_writes"] == int(kind != "unused" or args.phase == "before")
                    assert counts["recording_writes"] == 1 and counts["set_declaration"] == 0
                    assert active.workspace is workspace and active.path.read_bytes() == saved
                    assert time.monotonic() < deadline
                    case.update(final_controls=visible(cdp), final_counts=dict(counts),
                        remaining_seconds=deadline - time.monotonic(), http=list(trace),
                        requests=[{"route": urlsplit(e["params"]["request"]["url"]).path,
                            "fields": parse_qs(e["params"]["request"].get("postData", ""), keep_blank_values=True)}
                            for e in cdp.events if e["params"]["request"]["method"] == "POST"])
                    cdp.screenshot(args.output / f"{locale}-{int(script)}-{kind}.png")
        evidence["completed"] = True
    finally:
        release.set()
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
