"""Before/after #289 overview geometry and two-report native/enhanced navigation."""

import argparse
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
from test_learning_direct_entry_web import add_form, create_collection, source_handle  # noqa: E402
from test_learning_overview_navigation import analyze_retained, setup_collection  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402

import skatmind.app_web.debrief_http as debrief_http  # noqa: E402
import skatmind.app_web.debrief_rendering as rendering  # noqa: E402
import skatmind.app_web.match_rollout_frontend as rollout  # noqa: E402
import skatmind.capture_web.context as capture  # noqa: E402
from skatmind.app_web.stateful_localization import text  # noqa: E402
from skatmind.match_analysis_exports import (  # noqa: E402
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
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
    browser = None
    counts = Counter(evaluations=0, recording_writes=0, incorporations=0, projections=0)
    evidence = {"phase": args.phase, "python": sys.version, "measurements": [], "actions": []}
    def counted(key, real):
        def run(*args, **kwargs):
            counts[key] += 1
            return real(*args, **kwargs)
        return run
    try:
        with ExitStack() as stack:
            for module, name, key in (
                    (rollout, "execute_match_decision_analysis_v1", "evaluations"),
                    (capture, "save_match_workspace_file_v1", "recording_writes"),
                    (debrief_http, "incorporate_report", "incorporations"),
                    (rendering, "build_debrief_projection", "projections")):
                stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
            http, path, _, first = setup_collection(server)
            original = path.read_bytes()
            browser = LocalBrowser(args.browser, args.output / "browser-profile")
            cdp = browser.cdp
            evidence["browser"] = browser.version
            name, value = http.cookie.split("=", 1)
            cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                     deviceScaleFactor=1, mobile=False)
            def navigate(route):
                cdp.navigate(server.origin + route)
            def settle():
                time.sleep(.6)
            def add(report, collection="Synthetic overview"):
                navigate(f"/matches/reports/{report.report_id}" if args.phase == "after"
                         else "/learning/current")
                action = 'form[action="/learning/debrief/include"]'
                selector = action + ':has(input[value="' + report.report_id + '"]) button'
                if args.phase == "after":
                    locale = cdp.evaluate("document.documentElement.lang")
                    caption = cdp.evaluate(
                        f"document.querySelector({json.dumps(selector)}).textContent")
                    assert caption == text(locale, "debrief.add_to", collection=collection)
                    evidence["actions"].append({"report": report.report_id, "label": caption,
                        "target_handle": (
                            server.app_context.managed_stateful.active_learning.handle)})
                    cdp.screenshot(args.output / (
                        f"individual-{locale}-{report.decision_index}.png"), whole=True)
                cdp.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
                keyboard(cdp, "Enter", "Enter", 13, "\r")
                settle()
            def measure(label):
                settle()
                row = cdp.evaluate("""(()=>{const root=document.querySelector('#learning-debrief');
                    const rows=Array.from(root.querySelectorAll('.debrief-decision'));
                    return {route:location.pathname,locale:document.documentElement.lang,
                      width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth,
                      section:root.getBoundingClientRect().toJSON(),
                      rows:rows.map(n=>({geometry:n.getBoundingClientRect().toJSON(),text:n.innerText})),
                      controls:Array.from(root.querySelectorAll('a,button')).filter(n=>n.checkVisibility())
                        .map(n=>({text:n.textContent,height:n.getBoundingClientRect().height})),
                      focus:{name:document.activeElement.name,value:document.activeElement.value}};})()""")
                row.update(label=label, counters=dict(counts))
                assert row["overflow"] <= 1
                evidence["measurements"].append(row)
                cdp.screenshot(args.output / (label + ".png"), whole=True)
            navigate("/learning/current")
            click(cdp, 'form[action="/actions/profile/language"] button[value="en"]')
            settle()
            add(first)
            _, second = analyze_retained(http, 17)
            add(second)
            target = server.app_context.managed_stateful.active_learning
            assert len(target.debrief_sources.sources) == 2
            measure("two-desktop-en")
            for locale in ("de", "en"):
                click(cdp, f'form[action="/actions/profile/language"] button[value="{locale}"]')
                settle()
                assert cdp.evaluate("document.documentElement.lang") == locale
            base = cdp.evaluate(
                "document.querySelector('.debrief-decision a').getAttribute('href')")
            exact_overview = base.rsplit("/", 1)[0]
            click(cdp, f'a[href="{base}"]')
            settle()
            click(cdp, f'a[href="{exact_overview}"]')
            settle()
            assert cdp.evaluate("location.pathname") == exact_overview
            assert cdp.evaluate("document.querySelectorAll('.debrief-decision').length") == 2
            alex = next(index for index, name in enumerate(("chris", "alex", "bea"))
                        if name == "alex")
            filtered = exact_overview.rsplit("/", 1)[0] + "/" + str(alex)
            click(cdp, f'a[href="{filtered}"]')
            settle()
            click(cdp, 'form[action="/actions/profile/language"] button[value="de"]')
            settle()
            assert cdp.evaluate("location.pathname") == filtered
            cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=844,
                     deviceScaleFactor=1, mobile=False)
            measure("two-narrow-de-alex")
            for report in (first, second):
                for suffix, builder in (("result.json", build_match_report_result_export_v1),
                                        ("request.json", build_match_rollout_request_export_v1)):
                    route = filtered + "/" + report.report_id + "/" + suffix
                    assert http.request("GET", route)[2] == builder(report).to_bytes()
            if args.phase == "after":
                # New explicitly chosen collection; reuse the same two executions for native entry.
                create_collection(http, "Synthetic native target")
                follow(http, http.submit(add_form(http), source_handle=source_handle(path)))
                cdp.call("Emulation.setScriptExecutionDisabled", value=True)
                for report in (first, second):
                    add(report, "Synthetic native target")
                measure("two-narrow-native-de")
            assert counts["evaluations"] == 2 and counts["recording_writes"] == 0
            assert path.read_bytes() == original
            evidence.update(counters=dict(counts), completed=True,
                comparisons=[report.value.result.to_dict()["document"]["whole_game_rollout_comparison"]
                             for report in (first, second)])
    finally:
        if browser:
            browser.close()
        fixture.close()
        (args.output / "report.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in (
        "completed", "comparisons", "counters")}, indent=2))


if __name__ == "__main__":
    main()
