"""Optional #288 source-checkout native browser evidence using only synthetic data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, keyboard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_rollout_web import open_alex  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.match_rollout_frontend as frontend  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402
from skatmind.match_analysis_exports import (  # noqa: E402
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
)

FORM = 'form[action="/matches/review-whole-game"]'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    download_dir = args.output / "downloads"
    download_dir.mkdir()
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    browser = None
    evidence = {"completed": False, "python": sys.version, "module": skatmind.__file__,
                "measurements": [], "downloads": {}, "resource_hashes": {},
                "limits": ["Synthetic source-checkout evidence, not installed acceptance.",
                           "Headless viewport observations are not true browser zoom.",
                           "One default-size observation is not a latency or quality guarantee."]}
    try:
        http, path, _ = open_alex(server, count=30)
        original = path.read_bytes()
        browser = LocalBrowser(args.browser, args.output / "browser-profile")
        cdp = browser.cdp
        evidence["browser"] = browser.version
        cookie_name, cookie_value = http.cookie.split("=", 1)
        cdp.call("Network.setCookie", name=cookie_name, value=cookie_value, url=server.origin)
        cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(download_dir))
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                 deviceScaleFactor=1, mobile=False)
        cdp.navigate(server.origin + "/matches/review/2")
        calls = Counter()
        def counted(name, real):
            def wrapped(*args, **kwargs):
                calls[name] += 1
                return real(*args, **kwargs)
            return wrapped
        with ExitStack() as stack:
            stack.enter_context(patch.object(frontend, "execute_match_decision_analysis_v1",
                counted("evaluations", frontend.execute_match_decision_analysis_v1)))
            stack.enter_context(patch.object(capture, "save_match_workspace_file_v1",
                counted("recording_saves", capture.save_match_workspace_file_v1)))
            # Select Alex's third-card decision through the explicit native preparation form.
            selector = 'form[data-decision-selector] select[name="decision_index"]'
            click(cdp, selector)
            keyboard(cdp, "Home", "Home", 36)
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
            keyboard(cdp, "ArrowDown", "ArrowDown", 40)
            keyboard(cdp, "Enter", "Enter", 13, "\r")
            click(cdp, 'form[data-decision-selector] button')
            time.sleep(.8)
            assert cdp.evaluate(
                f'document.querySelector(\'{FORM} input[name="decision_index"]\').value') == "3"
            for locale in ("de", "en"):
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                time.sleep(.7)
                assert cdp.evaluate("document.documentElement.lang") == locale
                observation = cdp.evaluate("""(()=>{const f=document.querySelector(
                    'form[action="/matches/review-whole-game"]');
                    const b=f.querySelector('button.primary').getBoundingClientRect();
                    const m=f.querySelector('[name="analysis_matadors"]');
                    const a=f.querySelector('details');
                    return {locale:document.documentElement.lang, action_top:b.top,
                    objective:f.objective.value, worlds:f.requested_worlds.value,
                    seed:f.random_seed.value, missing_value:m.value,
                    missing_visible:m.getBoundingClientRect().height>0,
                    advanced_open:a.open, overflow:document.documentElement.scrollWidth-innerWidth};
                })()""")
                assert observation["objective"] == "complete_settlement"
                assert observation["missing_visible"] and not observation["missing_value"]
                assert not observation["advanced_open"] and observation["overflow"] <= 1
                evidence["measurements"].append(observation)
                cdp.screenshot(args.output / f"{locale}-controls.png", whole=True)
            assert not calls
            click(cdp, FORM + ' input[name="analysis_matadors"]')
            cdp.call("Input.insertText", text="1")
            start = time.perf_counter()
            click(cdp, FORM + ' button.primary')
            for _ in range(600):
                if cdp.evaluate("location.pathname.startsWith('/matches/reports/')"):
                    break
                time.sleep(.1)
            else:
                raise AssertionError("Default-sized native action did not publish a report.")
            evidence["submission_seconds"] = time.perf_counter() - start
            active = server.app_context.managed_stateful.active_match
            report, = active.capture.report_store.list()
            document = report.value.result.to_dict()["document"]
            evidence["rollout"] = document["whole_game_rollout_result"]
            assert evidence["rollout"]["status"] == "complete"
            assert evidence["rollout"]["completed_common_worlds"] == 100
            for locale, width, height in (("en", 1365, 900), ("de", 1365, 900), ("de", 390, 844)):
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                time.sleep(.7)
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                         deviceScaleFactor=1, mobile=False)
                evidence["measurements"].append(cdp.evaluate("""({locale:document.documentElement.lang,
                    width:innerWidth, overflow:document.documentElement.scrollWidth-innerWidth,
                    text:document.querySelector('main').innerText})"""))
                assert evidence["measurements"][-1]["overflow"] <= 1
                cdp.screenshot(args.output / f"{locale}-result-{width}.png", whole=True)
            for artifact, route in (
                    (build_match_rollout_request_export_v1(report),
                     f"/matches/api/v1/reports/{report.report_id}/rollout-request.json"),
                    (build_match_report_result_export_v1(report),
                     f"/matches/api/v1/reports/{report.report_id}.json")):
                click(cdp, f'a[href="{route}"]')
                target = download_dir / artifact.filename
                for _ in range(100):
                    if target.exists():
                        break
                    time.sleep(.1)
                assert target.read_bytes() == artifact.to_bytes()
                evidence["downloads"][artifact.filename] = digest(target.read_bytes())
            assert calls == {"evaluations": 1}
            assert path.read_bytes() == original
            evidence["calls"] = dict(calls)
        for resource in ("assets/app.css", "assets/workflow.js",
                         "locales/en.json", "locales/de.json",
                         "match_rollout_frontend.py", "match_rollout_rendering.py",
                         "rollout_form_rendering.py", "rollout_result_presentation.py"):
            raw = (Path(skatmind.__file__).parent / "app_web" / resource).read_bytes()
            evidence["resource_hashes"][resource] = digest(raw)
            if resource.startswith("assets/"):
                route = "/assets/app.css" if resource.endswith(".css") else (
                    "/matches/assets/capture.js")
                status, _, served = http.request("GET", route)
                assert status == 200 and served == raw
        catalogs = load_frontend_translation_catalogs_v1()
        evidence["inventory"] = [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY),
                                 len(catalogs["en"]), len(catalogs["de"])]
        evidence["recording_sha256"] = digest(original)
        evidence["completed"] = True
    finally:
        if browser is not None:
            browser.close()
        fixture.close()
        (args.output / "report.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in (
        "completed", "browser", "submission_seconds", "calls", "inventory")}, indent=2))


if __name__ == "__main__":
    main()
