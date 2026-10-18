"""Bounded checkout-browser Null-end evidence in a fresh disposable managed root."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, posts, wait

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_null_recording_end import session_prefix  # noqa: E402
from test_null_recording_end_web import (  # noqa: E402
    record_null_match_prefix,
    record_null_prefix,
)
from test_session_recorded_review_web import Browser, Forms  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session as api  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.managed_item_storage import (  # noqa: E402
    build_managed_item_handle_v1,
    build_managed_item_storage_name_v1,
)
from skatmind.app_web.session_frontend import import_guided_session_v1  # noqa: E402
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "disposable-browser-profile")
    cdp = local.cdp
    counts = Counter()
    phase = "fixture"
    evidence = {"completed": False, "python": sys.version, "import": skatmind.__file__,
        "browser": local.version, "pages": [], "actions": [],
        "inventory": {"routes": len(UNIFIED_FRONTEND_POST_ROUTES),
                      "forms": len(FRONTEND_FORM_REGISTRY),
                      "catalog": len(load_frontend_translation_catalogs_v1()["en"])},
        "limits": "Checkout source; headless Edge; emulated viewport, not browser zoom or UAT."}
    real_replace = os.replace

    def replace(source, target):
        result = real_replace(source, target)
        family = Path(target).parent.name
        counts[f"{phase}:{family}:writes"] += 1
        return result

    def no_analysis(*a, **kw):
        counts["analysis_calls"] += 1
        raise AssertionError("Capture/navigation must not execute analysis")

    def measure(label, section, script):
        for width, height in ((1365, 900), (390, 844)):
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                     deviceScaleFactor=1, mobile=False)
            cdp.evaluate(f"document.querySelector({json.dumps(section)})"
                         ".scrollIntoView({block:'start'})")
            row = cdp.evaluate("({text:document.querySelector(" + json.dumps(section)
                + ").innerText,width:document.documentElement.clientWidth,"
                "scroll:document.documentElement.scrollWidth,focus:document.activeElement.id})")
            row.update(label=label, javascript=script, viewport=width)
            assert row["width"] == row["scroll"], row
            evidence["pages"].append(row)
            cdp.screenshot(args.output / f"{label}-{int(script)}-{width}.png")

    def activate(selector):
        before = counts.copy()
        cdp.events.clear()
        cdp.activate(selector)
        wait(cdp)
        evidence["actions"].append({"selector": selector, "posts": posts(cdp),
                                    "operations": dict(counts - before)})

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(os, "replace", replace))
            for module, name in (
                ("skatmind.app_web.session_frontend", "execute_guided_frontend_analysis_v1"),
                ("skatmind.app_web.session_frontend", "execute_guided_frontend_review_v1"),
                ("skatmind.app_web.session_recorded_review", "execute_guided_frontend_review_v1"),
            ):
                stack.enter_context(patch(module + "." + name, no_analysis))
            browser = Browser(server)
            cookie_name, cookie_value = browser.cookie.split("=", 1)
            cdp.call("Network.setCookie", name=cookie_name, value=cookie_value, url=server.origin)
            for script in (True, False):
                for family in ("sessions", "matches"):
                    phase = "fixture"
                    page = (record_null_prefix(browser) if family == "sessions" else
                            record_null_match_prefix(browser))
                    active = (server.app_context.managed_stateful.active_session
                              if family == "sessions" else
                              server.app_context.managed_stateful.active_match)
                    route = f"/{family}/current"
                    section = "#session-recording" if family == "sessions" else "#match-recording"
                    form = ('form[action="/sessions/play"]' if family == "sessions" else
                            'form[action="/matches/cards"]:has(input[value="append_plays"])')
                    stale = (Forms(page).find("/sessions/play") if family == "sessions" else
                             next(f for f in Forms(page).forms
                                  if f["values"].get("operation") == "append_plays"))
                    phase = "passive"
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                    cdp.navigate(server.origin + route)
                    activate('form.language-selector button[value="en"]')
                    measure(f"{family}-eight", section, script)
                    before = active.path.read_bytes()
                    counts_before = counts.copy()
                    cdp.events.clear()
                    choose(cdp, form + ' input[value="HK"]')
                    assert posts(cdp) == [] and active.path.read_bytes() == before
                    phase = "accepted_play"
                    activate(form + ' button[type="submit"]')
                    assert counts[f"accepted_play:{family}:writes"] - counts_before[
                        f"accepted_play:{family}:writes"] == 1
                    saved = active.path.read_bytes()
                    assert b'"set_game_end"' not in saved
                    phase = "passive"
                    assert cdp.evaluate("document.body.innerText.includes('Null game lost')")
                    assert cdp.evaluate(f"document.querySelector({json.dumps(form)})===null")
                    measure(f"{family}-terminal-en", section, script)
                    if family == "sessions":
                        activate('#session-recording a[href="#recorded-decisions"]')
                        measure("sessions-decisions", "#recorded-decisions", script)
                        cdp.navigate(server.origin + route)
                    else:
                        activate('#match-recording a[href="/matches/review/1"]')
                        measure("matches-history", ".recorded-history", script)
                        cdp.navigate(server.origin + route)
                    activate('form.language-selector button[value="de"]')
                    assert cdp.evaluate("document.body.innerText.includes('Nullspiel verloren')")
                    measure(f"{family}-terminal-de", section, script)
                    activate('form.language-selector button[value="en"]')
                    phase = "rejected_append"
                    assert browser.submit(stale, cards="HK")[0] == 409
                    counts[f"rejected_append:{family}:requests"] += 1
                    phase = "passive"
                    cdp.navigate(server.origin + f"/{family}")
                    activate(f'form[action="/{family}/open"]:has('
                             f'input[value="{active.handle}"]) button[type="submit"]')
                    assert cdp.evaluate("document.body.innerText.includes('Null game lost')")
                    assert active.path.read_bytes() == saved
                    evidence[f"{family}-{script}-saved_sha256"] = hashlib.sha256(saved).hexdigest()
                # Build the nine-card source with the actual baseline transition implementation.
                phase = "fixture"
                original = subprocess.check_output([
                    "git", "show", "HEAD:src/skatmind/session_transitions.py"], cwd=ROOT)
                baseline = {}
                exec(compile(original, "baseline-transitions.py", "exec"), baseline)
                prototype = session_prefix(9)
                state = baseline["create_session_state_v1"](
                    session_id=f"pre-fix-null-{script}", players=prototype.players,
                    capture_mode="live", local_player_id=prototype.local_player_id)
                for record in prototype.command_log:
                    result = baseline["apply_session_command_v1"](state, record.command)
                    assert result.status == "applied"
                    state = result.state
                document = api.build_session_persistence_document(state).value
                storage = build_managed_item_storage_name_v1(family="sessions",
                                                             product_id=state.session_id)
                handle = build_managed_item_handle_v1(family="sessions", basename=storage)
                imported = import_guided_session_v1(
                    server.app_context.managed_stateful.root("sessions"), handle=handle,
                    document=document.to_dict())
                saved = imported.path.read_bytes()
                phase = "passive"
                cdp.navigate(server.origin + "/sessions")
                activate('form[action="/sessions/open"]:has('
                         f'input[value="{handle}"]) button[type="submit"]')
                assert cdp.evaluate("document.body.innerText.includes('Null game lost')")
                measure("pre-fix-nine-reopened", "#session-recording", script)
                assert imported.path.read_bytes() == saved
                evidence[f"baseline-{script}-sha256"] = hashlib.sha256(saved).hexdigest()
            assert counts["analysis_calls"] == 0
            assert all(counts[f"{p}:{f}:writes"] == 0 for p in ("passive", "rejected_append")
                       for f in ("sessions", "matches"))
            evidence["completed"] = True
    finally:
        evidence["operations"] = dict(counts)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        local.close()
        fixture.close()
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]),
                      "operations": evidence["operations"]}))


if __name__ == "__main__":
    main()
