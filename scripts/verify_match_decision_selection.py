"""Bounded #288 native/enhanced selection evidence on disposable synthetic source data."""

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from threading import Event
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, keyboard

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_rollout_web import open_alex  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.match_decision_selection as selection  # noqa: E402
import skatmind.app_web.match_rollout_frontend as rollout  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.match_analysis_exports import (  # noqa: E402
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
)

SELECT = 'form[data-decision-selector] select[name="decision_index"]'
FORM = 'form[action="/matches/review-whole-game"]'


def wait_for(cdp, expression):
    for _ in range(200):
        if cdp.evaluate(expression):
            return
        time.sleep(.05)
    raise AssertionError(expression)


def choose(cdp, index):
    click(cdp, SELECT)
    keyboard(cdp, "Home", "Home", 36)
    for _ in range(index - 1):
        keyboard(cdp, "ArrowDown", "ArrowDown", 40)
    keyboard(cdp, "Enter", "Enter", 13, "\r")


def fill(cdp, name, value):
    click(cdp, FORM + f' [name="{name}"]')
    for kind in ("keyDown", "keyUp"):
        cdp.call("Input.dispatchKeyEvent", type=kind, key="a", code="KeyA", modifiers=2,
                 windowsVirtualKeyCode=65)
    cdp.call("Input.insertText", text=value)


def identity(cdp):
    return cdp.evaluate("""(()=>{const r=document.querySelector('[data-match-selection]');
      const s=r.querySelector('select[name="decision_index"]');
      const f=r.querySelector('form[action="/matches/review-whole-game"]');
      const legacy=r.querySelector('input[value="analyze_decision"]').form;
      return {visible:s.value, applied:r.dataset.applied, ready:r.dataset.ready,
        focus:document.activeElement===s, selector_top:s.getBoundingClientRect().top,
        selector_visible:!!s.getClientRects().length,
        bound:f.decision_index.value, submitted_visible:f.visible_decision_index.value,
        legacy_bound:legacy.decision_index.value, objective:f.objective.value,
        matadors:f.analysis_matadors?.value, worlds:f.requested_worlds.value,
        action_disabled:f.querySelector('button.primary').disabled,
        action_visible:!!f.querySelector('button.primary').getClientRects().length,
        manual_visible:!!r.querySelector('[data-apply-decision]').getClientRects().length};})()""")


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
    entered, release, fail_next = Event(), Event(), Event()
    evidence = {"completed": False, "python": sys.version, "module": skatmind.__file__,
                "observations": {}, "calls": {}, "resources": {}, "downloads": {},
                "responses": []}
    try:
        http, path, _ = open_alex(server, count=30)
        original = path.read_bytes()
        active = server.app_context.managed_stateful.active_match
        browser = LocalBrowser(args.browser, args.output / "browser-profile")
        cdp = browser.cdp
        evidence["browser"] = browser.version
        key, value = http.cookie.split("=", 1)
        cdp.call("Network.setCookie", name=key, value=value, url=server.origin)
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                 deviceScaleFactor=1, mobile=False)
        cdp.navigate(server.origin + "/matches/review/2")
        calls = Counter()
        real_prepare = selection.build_match_decision_position_request_v1
        real_execute = rollout.execute_match_decision_analysis_v1
        send = Handler._send_bytes
        def observed_response(handler, status, content, **kwargs):
            evidence["responses"].append({"method": handler.command, "path": handler.path,
                                          "status": int(status)})
            return send(handler, status, content, **kwargs)
        def prepare(*args, **kwargs):
            calls["preparations"] += 1
            if fail_next.is_set():
                fail_next.clear()
                raise ValueError("Synthetic preparation failure")
            if kwargs["decision_index"] == 3 and not entered.is_set():
                entered.set()
                assert release.wait(20)
            return real_prepare(*args, **kwargs)
        def execute(*args, **kwargs):
            calls["evaluations"] += 1
            return real_execute(*args, **kwargs)
        def forbidden_save(*args, **kwargs):
            calls["recording_saves"] += 1
            raise AssertionError("Selection and review must not save the Match")
        with ExitStack() as stack:
            stack.enter_context(patch.object(Handler, "_send_bytes", observed_response))
            stack.enter_context(patch.object(selection, "build_match_decision_position_request_v1",
                                              prepare))
            stack.enter_context(patch.object(
                rollout, "execute_match_decision_analysis_v1", execute))
            stack.enter_context(patch.object(
                capture, "save_match_workspace_file_v1", forbidden_save))
            wait_for(cdp, f"!document.querySelector('{FORM}').hidden")
            evidence["observations"]["initial"] = identity(cdp)
            assert identity(cdp)["applied"] == "1" and not identity(cdp)["manual_visible"]
            fill(cdp, "analysis_matadors", "2")
            click(cdp, FORM + " details summary")
            fill(cdp, "requested_worlds", "1")
            choose(cdp, 3)
            assert entered.wait(10)
            evidence["observations"]["pending"] = identity(cdp)
            assert identity(cdp)["ready"] == "false" and identity(cdp)["action_disabled"]
            click(cdp, FORM + " button.primary")
            assert calls["evaluations"] == 0
            choose(cdp, 1)
            release.set()
            wait_for(cdp, "document.querySelector('[data-match-selection]').dataset.ready==='true'")
            evidence["observations"]["rapid_return"] = identity(cdp)
            assert identity(cdp)["applied"] == "1" and identity(cdp)["matadors"] == "2"
            choose(cdp, 3)
            top = identity(cdp)["selector_top"]
            wait_for(cdp,
                "document.querySelector('[data-match-selection]').dataset.applied==='3' && "
                "document.querySelector('[data-match-selection]').dataset.ready==='true'")
            observation = identity(cdp)
            evidence["observations"]["alex_ready"] = observation
            assert observation["focus"] and abs(observation["selector_top"] - top) <= 1
            assert observation["bound"] == observation["legacy_bound"] == "3"
            assert observation["matadors"] == "" and observation["worlds"] == "100"
            assert calls["evaluations"] == calls["recording_saves"] == 0
            cdp.screenshot(args.output / "enhanced-alex-ready.png")
            fill(cdp, "analysis_matadors", "1")
            click(cdp, FORM + " details summary")
            fill(cdp, "requested_worlds", "1")
            for locale in ("de", "en"):
                origin = cdp.evaluate("performance.timeOrigin")
                click(cdp, f'form.language-selector button[value="{locale}"]')
                wait_for(cdp, f"performance.timeOrigin!=={origin} && "
                    "document.readyState==='complete' && "
                    f"document.documentElement.lang==='{locale}'")
                assert identity(cdp)["applied"] == "3" and identity(cdp)["matadors"] == "1"
            click(cdp, FORM + " button.primary")
            wait_for(cdp, "location.pathname.startsWith('/matches/reports/')")
            report, = active.capture.report_store.list()
            assert report.decision_index == 3
            assert report.value.profile_binding.acting_player_id == "alex"
            evidence["report"] = {"id": report.report_id, "decision": report.decision_index,
                "actor": report.value.profile_binding.acting_player_id,
                "actual": report.value.request.document["actual_card_played"]}
            expected = {
                f"/matches/api/v1/reports/{report.report_id}/rollout-request.json":
                    build_match_rollout_request_export_v1(report).to_bytes(),
                f"/matches/api/v1/reports/{report.report_id}.json":
                    build_match_report_result_export_v1(report).to_bytes(),
            }
            fail_next.set()
            choose(cdp, 1)
            wait_for(cdp, "!document.querySelector('[data-apply-decision]').hidden && "
                          "document.querySelector('[data-selection-status]').textContent!==''")
            observation = identity(cdp)
            evidence["observations"]["failed_selection"] = observation
            assert observation["visible"] == "1" and observation["ready"] == "false"
            assert not observation["action_visible"] and calls["evaluations"] == 1
            for locale in ("de", "en"):
                origin = cdp.evaluate("performance.timeOrigin")
                click(cdp, f'form.language-selector button[value="{locale}"]')
                wait_for(cdp, f"performance.timeOrigin!=={origin} && "
                    "document.readyState==='complete' && "
                    f"document.documentElement.lang==='{locale}'")
                assert identity(cdp)["ready"] == "false" and identity(cdp)["manual_visible"]
            choose(cdp, 3)
            wait_for(cdp, "document.querySelector('[data-match-selection]').dataset.ready==='true'")
            assert identity(cdp)["applied"] == "3" and calls["evaluations"] == 1
            # Native fallback has an editable selection step or ready actions, never both.
            cdp.call("Emulation.setScriptExecutionDisabled", value=True)
            cdp.call("Page.navigate", url=server.origin + "/matches/review/2?choose_decision=1")
            wait_for(cdp, "location.pathname==='/matches/review/2' && !location.search")
            choose(cdp, 1)
            observation = identity(cdp)
            evidence["observations"]["native_unapplied"] = observation
            assert observation["visible"] == "1" and not observation["action_visible"]
            assert observation["manual_visible"] and observation["selector_visible"]
            click(cdp, "[data-apply-decision]")
            wait_for(cdp, "document.querySelector('[data-match-selection]').dataset.applied==='1'")
            observation = identity(cdp)
            evidence["observations"]["native_applied"] = observation
            assert not observation["selector_visible"] and observation["action_visible"]
            cdp.screenshot(args.output / "native-applied.png")
            for route, raw in expected.items():
                assert http.request("GET", route)[2] == raw
                evidence["downloads"][route] = hashlib.sha256(raw).hexdigest()
            assert active.capture.report_store.list() == (report,)
            assert path.read_bytes() == original
            assert calls["evaluations"] == 1 and calls["recording_saves"] == 0
            evidence["calls"] = dict(calls)
        for resource, route in (("assets/app.css", "/assets/app.css"),
                                ("assets/workflow.js", "/matches/assets/capture.js")):
            raw = (Path(skatmind.__file__).parent / "app_web" / resource).read_bytes()
            assert http.request("GET", route)[2] == raw
            evidence["resources"][resource] = hashlib.sha256(raw).hexdigest()
        evidence["completed"] = True
    except Exception:
        if browser is not None:
            (args.output / "failure.html").write_text(
                browser.cdp.evaluate("document.documentElement.outerHTML"), encoding="utf-8")
            browser.cdp.screenshot(args.output / "failure.png")
        raise
    finally:
        release.set()
        if browser is not None:
            browser.close()
        fixture.close()
        (args.output / "report.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
