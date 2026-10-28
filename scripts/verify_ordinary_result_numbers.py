# ruff: noqa: E501 - Keep browser selectors and evidence records legible.
"""Disposable source-tree HTTP/browser verification for ordinary numeric presentation."""

import argparse
import hashlib
import json
import platform
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))

from test_analysis_explanations_web import candidate_values  # noqa: E402
from test_equal_best_immediate import assert_visible_equal_best  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_decision_context_web import (  # noqa: E402
    record_context_match,
    record_second_context_game,
)
from test_session_recorded_review_web import (  # noqa: E402
    Browser,
    record_score_review_game,
    score_review_form,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profiles  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
import skatmind.learning_corpus_import as corpus_import  # noqa: E402
from skatmind.app_web.json_transfer import (  # noqa: E402
    canonical_frontend_json_bytes_v1 as canonical,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.stateful_localization import card_name  # noqa: E402
from skatmind.match_analysis_exports import build_match_report_result_export_v1  # noqa: E402
from skatmind.match_analysis_report_source_export import (  # noqa: E402
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)


def saved_bytes(root, profile):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*") if path.is_file() and path != profile}


def wait(cdp, expression):
    for _ in range(150):
        if cdp.evaluate(expression):
            time.sleep(.2)
            return
        time.sleep(.1)
    raise AssertionError(expression)


def run_case(args, path, script, evidence):
    root = args.output / f"{path}-js{int(script)}"
    root.mkdir()
    fixture = localized_server.__wrapped__(root)
    server = next(fixture)
    local = None
    calls, requests = Counter(), Counter()
    row = dict(path=path, javascript=script, phases=[], views=[])
    evidence["runs"].append(row)

    def counted(key, real):
        def call(*args_, **kwargs):
            calls[key] += 1
            return real(*args_, **kwargs)
        return call

    def request_count(method, real):
        def call(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return call

    try:
        with ExitStack() as stack:
            for module, name, key in (
                (execution, "execute", "session_analysis"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_analysis"),
                (session_files, "save_session_file", "session_write"),
                (match_context, "save_match_workspace_file_v1", "match_write"),
                (learning, "prepare_learning_corpus_artifacts_web_v1", "preparation"),
                (learning, "import_match_workspace_into_learning_corpus_web_v1", "import"),
                (corpus_import, "save_learning_corpus_catalog_v1", "catalog_write"),
                (corpus_import, "publish_learning_corpus_match_snapshot_object_v1", "snapshot_write"),
                (profiles, "save_frontend_profile_file_v1", "profile_save"),
            ):
                stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method,
                    request_count(method, getattr(Handler, "do_" + method))))
            http = Browser(server)
            if path == "session":
                record_score_review_game(http, names=("B 1.25", "C 0.125", "A 3.14"))
            else:
                record_context_match(http, names=("B 1.25", "C 0.125", "A 3.14"))
                record_second_context_game(http)
            row["phases"].append(dict(name="fixture_recording", calls=dict(calls), requests=dict(requests)))
            before, req = calls.copy(), requests.copy()
            if path == "session":
                follow(http, http.submit(score_review_form(http)))
                active = server.app_context.managed_stateful.active_session
                retained = active.execution
                route = "/sessions/current"
                expected_downloads = {f"/sessions/downloads/{name}.json": getattr(retained, name + "_json_bytes")
                                      for name in ("request", "result")}
                exact = canonical(retained.result.result.to_dict())
            else:
                for game in (1, 4):
                    follow(http, http.submit(operation_form(http.page(f"/matches/review/{game}"), "analyze_decision"),
                                             immediate_sample_count="8"))
                active = server.app_context.managed_stateful.active_match
                retained, newer = active.capture.report_store.list()
                route = f"/matches/reports/{retained.report_id}"
                expected_downloads = {
                    f"/matches/api/v1/reports/{retained.report_id}.json": build_match_report_result_export_v1(retained).to_bytes(),
                    f"/matches/api/v1/reports/{retained.report_id}/strategy-source.json": serialize_match_analysis_report_source_export_v1(
                        build_match_analysis_report_source_export_v1(retained)),
                }
                exact = canonical(retained.to_dict())
                row["selected_report"] = retained.report_id
                row["newer_report"] = newer.report_id
            row["phases"].append(dict(name="deliberate_initial_analysis", calls=dict(calls-before), requests=dict(requests-req)))
            home = server.app_context.managed_home.root
            profile = server.app_context.frontend_profile.profile_path
            files = saved_bytes(home, profile)
            local = LocalBrowser(args.browser, root / "browser-profile")
            row["browser"] = local.version
            cdp = local.cdp
            name, value = http.cookie.split("=", 1)
            cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
            cdp.call("Network.setExtraHTTPHeaders", headers={"Accept-Language": "en"})
            before = calls.copy()
            cdp.navigate(server.origin + route)
            assert calls == before
            for index, locale in enumerate(("de", "en", "de")):
                before, req = calls.copy(), requests.copy()
                cdp.activate(f'.language-selector button[value="{locale}"]')
                wait(cdp, "document.readyState === 'complete' && document.documentElement.lang === " + json.dumps(locale))
                assert cdp.evaluate("location.pathname") == route
                assert calls-before == Counter(profile_save=1)
                row["phases"].append(dict(name="explicit_language_" + locale, calls=dict(calls-before), requests=dict(requests-req)))
                before, req = calls.copy(), requests.copy()
                html = cdp.evaluate("document.documentElement.outerHTML")
                assert all(name in html for name in ("B 1.25", "C 0.125", "A 3.14"))
                if path == "session":
                    assert_visible_equal_best(html, locale)
                    assert active.execution is retained and canonical(retained.result.result.to_dict()) == exact
                    expected = [value for candidate in retained.result.result.document["analysis_report"] for value in (
                        f'{candidate["win_rate"] * 100:.2f}%', f'{candidate["expected_point_swing"]:.2f}',
                        f'{candidate["average_trick_points"]:.6g}')]
                    expected = [value.replace(".", ",") if locale == "de" else value for value in expected]
                    values = candidate_values(html)
                    assert [cell for start in (2, 7) for cell in values[start:start + 3]] == expected
                else:
                    expected = []
                    for candidate in retained.value.result.document["analysis_report"]:
                        expected.append(f'{card_name(locale, candidate["card"])} ({candidate["card"]})')
                        expected.extend(str(candidate[key]).replace(".", ",") if locale == "de" else str(candidate[key])
                                        for key in ("expected_point_swing", "win_rate"))
                    assert candidate_values(html) == expected
                    assert active.capture.report_store.get(retained.report_id) is retained
                    assert canonical(retained.to_dict()) == exact
                cdp.evaluate("document.querySelector('.candidate-comparison').scrollIntoView({block:'center'})")
                displayed = cdp.evaluate("[...document.querySelectorAll('.candidate-value')].map(e=>({text:e.innerText,visible:e.checkVisibility()}))")
                assert all(cell["visible"] for cell in displayed)
                cdp.screenshot(root / f"{index}-{locale}-numbers.png")
                view = dict(locale=locale, cells=displayed, downloads=[],
                    scale=cdp.evaluate("({devicePixelRatio,scale:visualViewport.scale})"))
                row["views"].append(view)
                download_dir = root / f"downloads-{index}-{locale}"
                download_dir.mkdir()
                cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(download_dir.resolve()))
                for url, expected_bytes in expected_downloads.items():
                    selector = f'a[download][href="{url}"]'
                    # Open only the native disclosure ancestors of the delivered link.
                    while True:
                        target = cdp.evaluate("(()=>{let e=document.querySelector(" + json.dumps(selector) + ");"
                            "let a=[];for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS'&&!p.open)a.push(p);"
                            "return a.length ? a[a.length-1].querySelector('summary').id || null : false})()")
                        if target is False:
                            break
                        # Summaries need not have IDs; use their actual ancestor structure.
                        cdp.activate(f'details:not([open]):has({selector}) > summary')
                    status, headers, raw = http.request("GET", url)
                    assert status == 200 and raw == expected_bytes
                    filename = headers["content-disposition"].split('filename="', 1)[1].split('"', 1)[0]
                    cdp.activate(selector)
                    destination = download_dir / filename
                    for _ in range(100):
                        if destination.is_file() and destination.read_bytes() == expected_bytes:
                            break
                        time.sleep(.1)
                    else:
                        raise AssertionError("Native download did not match: " + url)
                    view["downloads"].append(dict(route=url, filename=filename, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
                assert calls == before
                assert saved_bytes(home, profile) == files
                assert server.app_context.managed_stateful.active_learning is None
                row["phases"].append(dict(name="passive_view_and_downloads", calls=dict(calls-before), requests=dict(requests-req)))
            row["completed"] = True
    finally:
        if local:
            local.close()
        fixture.close()


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert Path(skatmind.__file__).resolve().is_relative_to(ROOT / "src")
    args.output.mkdir()
    started = time.monotonic()
    evidence = dict(completed=False, python=sys.version, executable=sys.executable,
        platform=platform.platform(), module=skatmind.__file__, runs=[],
        boundary="Disposable genuine Immediate executions from source-tree fixtures; no installed UAT or Learning workflow.",
        zoom="Fresh profiles at default 100%; viewport emulation is not browser zoom.")
    try:
        for path in ("session", "match"):
            for script in (False, True):
                run_case(args, path, script, evidence)
        evidence["completed"] = True
    finally:
        evidence["seconds"] = round(time.monotonic() - started, 3)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(dict(completed=evidence["completed"], seconds=evidence["seconds"], output=str(args.output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
