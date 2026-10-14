"""Bounded #289 synthetic source-checkout browser evidence, outside maintainer data."""

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
from verify_recording_deletion import click

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_frontend_language_switching import localized_server  # noqa: E402
from test_learning_debrief_web import complete_report  # noqa: E402
from test_learning_direct_entry_web import add_form, create_collection, source_handle  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.debrief_http as debrief_http  # noqa: E402
import skatmind.app_web.debrief_rendering as rendering  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.app_web.match_rollout_frontend as rollout  # noqa: E402
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


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


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
    counters = Counter(evaluations=0, recording_writes=0, incorporations=0,
                       workspace_imports=0, dataset_preparations=0, projections=0)
    evidence = {"completed": False, "python": sys.version, "module": skatmind.__file__,
        "observations": [], "limits": ["Synthetic source checkout, not installed UAT.",
            "Narrow viewport, not true browser zoom."]}
    def counted(key, real):
        def wrapped(*args, **kwargs):
            counters[key] += 1
            return real(*args, **kwargs)
        return wrapped
    try:
        with ExitStack() as stack:
            for module, name, key in (
                    (rollout, "execute_match_decision_analysis_v1", "evaluations"),
                    (capture, "save_match_workspace_file_v1", "recording_writes"),
                    (debrief_http, "incorporate_report", "incorporations"),
                    (learning, "import_match_workspace_into_learning_corpus_web_v1",
                     "workspace_imports"),
                    (learning, "prepare_learning_corpus_artifacts_web_v1", "dataset_preparations"),
                    (rendering, "build_debrief_projection", "projections")):
                stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
            http, path, _, report = complete_report(server)
            original = path.read_bytes()
            browser = LocalBrowser(args.browser, args.output / "browser-profile")
            cdp = browser.cdp
            evidence["browser"] = browser.version
            name, value = http.cookie.split("=", 1)
            cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
            cdp.call("Emulation.setScriptExecutionDisabled", value=True)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                     deviceScaleFactor=1, mobile=False)
            cdp.navigate(server.origin + f"/matches/reports/{report.report_id}")
            click(cdp, 'form[action="/actions/profile/language"] button[value="en"]')
            time.sleep(.7)
            def observe(label):
                time.sleep(.3)
                row = cdp.evaluate("""(()=>{const buttons=Array.from(document.querySelectorAll(
                    'main a.button-link, main button')).filter(n=>n.checkVisibility());
                    return {route:location.pathname, locale:document.documentElement.lang,
                    width:innerWidth, overflow:document.documentElement.scrollWidth-innerWidth,
                    focus:{tag:document.activeElement.tagName, id:document.activeElement.id,
                      name:document.activeElement.name, value:document.activeElement.value},
                    controls:buttons.map(n=>({text:n.textContent.trim(),
                      width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height})),
                    text:document.querySelector('main').innerText};})()""")
                row["label"] = label
                row["counters"] = dict(counters)
                assert row["overflow"] <= 1
                assert all(control["height"] >= 32 for control in row["controls"])
                evidence["observations"].append(row)
                cdp.screenshot(args.output / (label + ".png"), whole=True)
            click(cdp, f'a[href="/learning/debrief/from/{report.report_id}"]')
            time.sleep(.5)
            assert server.app_context.managed_stateful.active_learning is None
            observe("direct-desktop-native")
            create_collection(http, "Synthetic debrief collection")
            follow(http, http.submit(add_form(http), source_handle=source_handle(path)))
            target = server.app_context.managed_stateful.active_learning
            assert not target.debrief_sources.sources
            cdp.navigate(server.origin + "/learning/current")
            observe("empty-desktop-native")
            assert "Recorded decisions: 30" in evidence["observations"][-1]["text"]
            assert "No completed comparisons are included" in evidence["observations"][-1]["text"]
            click(cdp, 'form[action="/learning/debrief/include"] button')
            for _ in range(100):
                if target.debrief_sources.sources:
                    break
                time.sleep(.1)
            assert len(target.debrief_sources.sources) == 1
            observe("included-desktop-native")
            route = cdp.evaluate(
                "document.querySelector('.debrief-decision a').getAttribute('href')")
            click(cdp, '.debrief-decision a')
            time.sleep(.5)
            observe("comparison-desktop-native")
            for suffix, builder in (("request.json", build_match_rollout_request_export_v1),
                                    ("result.json", build_match_report_result_export_v1)):
                status, _, raw = http.request("GET", route + "/" + suffix)
                assert status == 200 and raw == builder(report).to_bytes()
                evidence[suffix + "_sha256"] = digest(raw)
            click(cdp, 'a[href$="/recording"]')
            time.sleep(.5)
            assert cdp.evaluate("document.querySelector("
                "'form[action=\"/matches/review-whole-game\"]'"
                ").querySelector('[name=decision_index]').value") == "3"
            observe("safe-return-native")
            cdp.navigate(server.origin + route)
            click(cdp, 'form[action="/actions/profile/language"] button[value="de"]')
            time.sleep(.7)
            assert cdp.evaluate("document.documentElement.lang") == "de"
            cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844,
                     deviceScaleFactor=1, mobile=False)
            observe("comparison-narrow-native-de")
            # The same captured comparison also supports the existing enhancement.
            cdp.call("Emulation.setScriptExecutionDisabled", value=False)
            cdp.navigate(server.origin + route.rsplit("/", 1)[0])
            observe("included-narrow-enhanced-de")
            click(cdp, 'form[action="/actions/profile/language"] button[value="en"]')
            time.sleep(.7)
            assert cdp.evaluate("document.documentElement.lang") == "en"
            assert cdp.evaluate("location.pathname") == route.rsplit("/", 1)[0]
            observe("included-narrow-enhanced-en")
            assert evidence["observations"][-1]["focus"]["value"] == "en"
            assert counters["evaluations"] == 1 and counters["recording_writes"] == 0
            assert counters["incorporations"] == 1 and path.read_bytes() == original
            assert counters["workspace_imports"] == 1 and counters["dataset_preparations"] == 0
            assert target.corpus.prepared_artifacts is None
            evidence["counters"] = dict(counters)
            evidence["recording_sha256"] = digest(original)
        catalogs = load_frontend_translation_catalogs_v1()
        evidence["inventory"] = {"post_routes": len(UNIFIED_FRONTEND_POST_ROUTES),
            "forms": len(FRONTEND_FORM_REGISTRY), "catalog_keys": len(catalogs["en"])}
        evidence["resources"] = {}
        for name in ("assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json",
                     "debrief_frontend.py", "debrief_rendering.py", "debrief_http.py"):
            raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
            evidence["resources"][name] = digest(raw)
            if name.startswith("assets/"):
                route = "/assets/app.css" if name.endswith("css") else "/matches/assets/capture.js"
                assert http.request("GET", route)[2] == raw
        evidence["completed"] = True
    finally:
        if browser:
            browser.close()
        fixture.close()
        (args.output / "report.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in (
        "completed", "counters", "inventory")}, indent=2))


if __name__ == "__main__":
    main()
