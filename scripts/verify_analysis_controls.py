"""Optional #325 source-browser evidence with disposable synthetic data and no page script."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import keyboard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_analysis_controls_web import open_profile_match  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402
from test_session_recorded_review_web import Forms  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.match_rollout_frontend as rollout  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402

FORM = 'form[action="/matches/review-whole-game"]'
HISTORY = 'form:has(input[name="operation"][value="analyze_historical_game"])'


def wait(cdp, expression):
    for _ in range(600):
        if cdp.evaluate(expression):
            return
        time.sleep(.1)
    raise AssertionError(expression)


def choose(cdp, selector, index):
    click(cdp, selector)
    keyboard(cdp, "Enter", "Enter", 13, "\r")
    keyboard(cdp, "Home", "Home", 36)
    for _ in range(index):
        keyboard(cdp, "ArrowDown", "ArrowDown", 40)
    keyboard(cdp, "Enter", "Enter", 13, "\r")
    actual = cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").selectedIndex")
    assert actual == index, (selector, actual, index)


def click(cdp, selector):
    """Focus the real control, then activate using native keyboard input."""
    kind = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
        + ");e.scrollIntoView({block:'center'});e.focus();return [e.tagName,e.type]})()")
    if kind[1] == "checkbox":
        keyboard(cdp, " ", "Space", 32, " ")
    elif kind[0] in {"BUTTON", "SUMMARY"}:
        keyboard(cdp, "Enter", "Enter", 13, "\r")


def fill(cdp, selector, value):
    click(cdp, selector)
    for kind in ("keyDown", "keyUp"):
        cdp.call("Input.dispatchKeyEvent", type=kind, key="a", code="KeyA", modifiers=2,
                 windowsVirtualKeyCode=65)
    cdp.call("Input.insertText", text=value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    browser = None
    report = {"completed": False, "python": sys.version, "module": skatmind.__file__,
              "page_javascript": False, "observations": [], "downloads": {}}
    calls = Counter()
    try:
        http, source, page = open_profile_match(server)
        page = follow(http, http.submit(Forms(page).find("/matches/select-decision"),
                                       decision_index="28"))
        original = source.read_bytes()
        browser = LocalBrowser(args.browser, args.output / "browser-profile")
        cdp = browser.cdp
        report["browser"] = browser.version
        name, value = http.cookie.split("=", 1)
        cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                 deviceScaleFactor=1, mobile=False)
        cdp.navigate(server.origin + "/matches/review/3")
        real = rollout.execute_match_decision_analysis_v1
        def execute(*a, **kw):
            calls["executions"] += 1
            return real(*a, **kw)
        def forbidden(*a, **kw):
            calls["recording_saves"] += 1
            raise AssertionError("Passive controls and analysis must not save the recording")
        with patch.object(rollout, "execute_match_decision_analysis_v1", execute), patch.object(
                capture, "save_match_workspace_file_v1", forbidden):
            for locale in ("de", "en"):
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                wait(cdp, f'document.documentElement.lang === "{locale}"')
                observation = cdp.evaluate("""(()=>{const f=document.querySelector(
                    'form[action="/matches/review-whole-game"]');return {
                    locale:document.documentElement.lang, effort:f.analysis_effort.value,
                    mode:f.settings_mode.value, closed:!f.querySelector('details').open,
                    profile_in_rollout:!!f.querySelector('[name="use_profile_presets"]')};})()""")
                assert observation == {"locale": locale, "effort": "standard", "mode": "ordinary",
                                       "closed": True, "profile_in_rollout": False}
                report["observations"].append(observation)
            assert not calls
            choose(cdp, FORM + ' [name="objective"]', 1)
            choose(cdp, FORM + ' [name="analysis_effort"]', 0)
            click(cdp, FORM + ' button.primary')
            wait(cdp, "location.pathname.startsWith('/matches/reports/')")
            active = server.app_context.managed_stateful.active_match
            first = active.capture.report_store.list()[-1]
            settings = first.value.request.document["whole_game_rollout_settings"]
            assert (settings["requested_worlds"], settings["wall_clock_timeout_ms"]) == (25, 5000)
            assert first.value.result.document["whole_game_rollout_result"]["status"] == "complete"
            report["preset_settings"] = dict(settings)
            click(cdp, FORM + ' details > summary')
            choose(cdp, FORM + ' [name="settings_mode"]', 1)
            fill(cdp, FORM + ' [name="requested_worlds"]', "2")
            fill(cdp, FORM + ' [name="random_seed"]', "-1")
            click(cdp, FORM + ' button.primary')
            wait(cdp, '!!document.querySelector("[name=random_seed][aria-invalid=true]")')
            assert calls["executions"] == 1
            assert cdp.evaluate(
                "document.querySelector('[name=random_seed]').closest('details').open")
            for locale in ("de", "en"):
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                wait(cdp, f'document.documentElement.lang === "{locale}"')
                mode = cdp.evaluate(
                    f'document.querySelector(\'{FORM} [name=settings_mode]\').value')
                assert mode == "custom"
            fill(cdp, FORM + ' [name="random_seed"]', "19")
            choose(cdp, FORM + ' [name="analysis_effort"]', 2)
            click(cdp, FORM + ' details > summary')
            click(cdp, FORM + ' button.primary')
            wait(cdp, "location.pathname.startsWith('/matches/reports/') && location.pathname !== "
                 + json.dumps("/matches/reports/" + first.report_id))
            current = active.capture.report_store.list()[-1]
            settings = current.value.request.document["whole_game_rollout_settings"]
            assert (settings["requested_worlds"], settings["wall_clock_timeout_ms"],
                    settings["random_seed"]) == (2, 5000, 19)
            report["custom_settings"] = dict(settings)
            # A separate historical form owns its optional output and profile choice.
            cdp.navigate(server.origin + "/matches/review/3")
            click(cdp, 'details:has(input[name="operation"]'
                  '[value="analyze_historical_game"]) > summary')
            click(cdp, HISTORY + ' details:has([name="tactical_motif_review"]) > summary')
            click(cdp, HISTORY + ' [name="tactical_motif_review"]')
            click(cdp, HISTORY + ' details:has([name="settings_mode"]) > summary')
            choose(cdp, HISTORY + ' [name="settings_mode"]', 1)
            fill(cdp, HISTORY + ' [name="immediate_sample_count"]', "-1")
            click(cdp, HISTORY + ' button[type="submit"]')
            wait(cdp, '!!document.querySelector('
                 '"[name=immediate_sample_count][aria-invalid=true]")')
            for locale in ("de", "en"):
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                wait(cdp, f'document.documentElement.lang === "{locale}"')
                observation = cdp.evaluate("""(()=>{const f=document.querySelector(
                    'form:has(input[value="analyze_historical_game"])');const p=f.querySelector(
                    '[name="use_profile_presets"]');return {locale:document.documentElement.lang,
                    tactical:f.tactical_motif_review.checked, profile:p.checked,
                    profile_in_technical:p.closest('details')?.closest('form')===f,
                    custom:f.settings_mode.value, sample:f.immediate_sample_count.value};})()""")
                assert observation["tactical"] and observation["profile"]
                assert not observation["profile_in_technical"]
                assert (observation["custom"], observation["sample"]) == ("custom", "-1")
                report["observations"].append(observation)
            for suffix, expected in (
                ("rollout-request.json", current.value.request.to_dict()["document"]),
                (None, current.value.result.to_dict()["document"]),
            ):
                route = f"/matches/api/v1/reports/{current.report_id}" + (
                    "/" + suffix if suffix else ".json")
                status, _, raw = http.request("GET", route)
                assert status == 200 and json.loads(raw) == expected
                report["downloads"][route] = hashlib.sha256(raw).hexdigest()
            assert calls == {"executions": 2}
            assert source.read_bytes() == original
            report["source_sha256"] = hashlib.sha256(original).hexdigest()
            report["counts"] = dict(calls)
            report["completed"] = True
    finally:
        if browser is not None:
            browser.close()
        try:
            next(fixture)
        except StopIteration:
            pass
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
