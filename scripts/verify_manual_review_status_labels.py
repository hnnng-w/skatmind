# ruff: noqa: E501 - Keep DevTools expressions and evidence assertions together.
"""Issue #307 disposable source-tree browser probe; never installed maintainer UAT."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests"), str(ROOT)]

from _workflow_visual_browser import LocalBrowser  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_manual_review_saved_names import snapshot  # noqa: E402
from test_manual_review_status_labels import (  # noqa: E402
    BASELINE_SHA256,
    assert_completed_result,
    assert_completed_summary,
    completed_grand_request,
    summary_cells,
)
from test_session_recorded_review_web import Browser  # noqa: E402

import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile  # noqa: E402
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    assert Path(execution.__file__).resolve().is_relative_to(ROOT / "src")
    source = args.output / "request.json"
    source.write_bytes(canonical_frontend_json_bytes_v1(completed_grand_request()))
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    report = {"completed": False, "python": sys.version, "executable": sys.executable,
              "browser": local.version, "source": execution.__file__, "cases": [],
              "resources": {}, "boundary": "Source-tree developer evidence at 100% zoom; not installed acceptance."}
    for name in ("locales/de.json", "locales/en.json", "result_presentation.py", "result_localization.py",
                 "result_rendering.py", "assets/app.css", "assets/workflow.js"):
        report["resources"][name] = hashlib.sha256((Path(execution.__file__).parent / name).read_bytes()).hexdigest()

    def close_fixture(fixture):
        try:
            next(fixture)
        except StopIteration:
            pass

    try:
        for locale in ("de", "en"):
            for script in (False, True):
                directory = args.output / f"{locale}-{script}"
                directory.mkdir()
                fixture = localized_server.__wrapped__(directory)
                server = next(fixture)
                case = {"locale": locale, "javascript": script, "phase": "initial-language",
                        "posts": [], "phases": {}, "observations": [], "downloads": []}
                report["cases"].append(case)
                counts = Counter()
                real_replace, real_response = os.replace, Handler.send_response

                def counted(label, real, counts=counts):
                    def call(*a, **kw):
                        counts[label] += 1
                        return real(*a, **kw)
                    return call

                def replaced(src, dst, counts=counts, real=real_replace, root=directory / "managed"):
                    if Path(dst).is_relative_to(root):
                        counts["persistent_replacements"] += 1
                    return real(src, dst)

                def responded(handler, status, *a, case=case, real=real_response, **kw):
                    if handler.command == "POST":
                        case["posts"].append({"phase": case["phase"], "path": handler.path, "status": status})
                    return real(handler, status, *a, **kw)

                def checkpoint(next_phase, expected, case=case, counts=counts):
                    assert dict(counts) == expected, (case["phase"], counts, expected)
                    if case["phase"].startswith("passive"):
                        assert not any(p["phase"] == case["phase"] for p in case["posts"])
                    case["phases"][case["phase"]] = dict(counts)
                    counts.clear()
                    case["phase"] = next_phase

                def submit(selector, route, case=case):
                    before = len(case["posts"])
                    cdp.activate(selector)
                    for _ in range(100):
                        if len(case["posts"]) > before and cdp.evaluate("document.readyState === 'complete'"):
                            break
                        time.sleep(.1)
                    assert case["posts"][before:] == [{"phase": case["phase"], "path": route, "status": 303}]

                def import_file(path, server):
                    cdp.activate('details:has(> form[action="/actions/review/import-json"]) > summary')
                    root = cdp.call("DOM.getDocument")["root"]["nodeId"]
                    node = cdp.call("DOM.querySelector", nodeId=root, selector="#request-file")["nodeId"]
                    cdp.call("DOM.setFileInputFiles", nodeId=node, files=[str(path.resolve())])
                    submit('form[action="/actions/review/import-json"] button', "/actions/review/import-json")
                    assert server.app_context.review_state.latest_successful_result is None

                def observe(stage, expected_locale, state, server, directory=directory, case=case):
                    before = snapshot(server.app_context)
                    cdp.evaluate("void 0")
                    event = next(e for e in reversed(cdp.events) if e["params"].get("type") == "Document")
                    raw = cdp.call("Network.getResponseBody", requestId=event["params"]["requestId"])
                    assert not raw.get("base64Encoded")
                    page = raw["body"]
                    (directory / (stage + ".html")).write_text(page, encoding="utf-8")
                    assert_completed_summary(page, expected_locale)
                    dom = cdp.evaluate('Object.fromEntries([...document.querySelectorAll("section[aria-labelledby=result-section-1] dt")].map(e=>[e.textContent,e.nextElementSibling.textContent]))')
                    assert dom == summary_cells(page)
                    assert cdp.evaluate("document.documentElement.lang") == expected_locale
                    assert cdp.evaluate("location.pathname") == "/review"
                    assert not cdp.evaluate('document.querySelector(".technical-details").open')
                    cdp.evaluate('document.querySelector("#result-section-1").scrollIntoView({block:"start"})')
                    cdp.screenshot(directory / (stage + ".png"))
                    assert_completed_result(state)
                    assert server.app_context.review_state is state
                    assert snapshot(server.app_context) == before
                    case["observations"].append({"stage": stage, "locale": expected_locale, "cells": dom,
                                                 "retained_identity": True, "files_unchanged": True})

                def downloads(stage, state, server, directory=directory, case=case):
                    destination = directory / (stage + "-downloads")
                    destination.mkdir()
                    cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
                    files = snapshot(server.app_context)
                    for name, expected_hash in zip(("request", "result"), BASELINE_SHA256, strict=True):
                        route = f"/downloads/review/{name}.json"
                        selector = f'a[download][href="{route}"]'
                        assert not cdp.evaluate(f'document.querySelector({json.dumps(selector)}).closest("details") !== null')
                        cdp.activate(selector)
                        saved = destination / f"skatmind-review-{name}.json"
                        for _ in range(100):
                            if saved.is_file():
                                break
                            time.sleep(.1)
                        raw = saved.read_bytes()
                        assert raw == getattr(state, name + "_json_bytes")
                        assert hashlib.sha256(raw).hexdigest() == expected_hash
                        case["downloads"].append({"stage": stage, "name": name, "sha256": expected_hash, "path": str(saved)})
                    assert server.app_context.review_state is state and snapshot(server.app_context) == files
                    return destination / "skatmind-review-request.json"

                try:
                    with ExitStack() as stack:
                        stack.enter_context(patch.object(execution, "execute", counted("review_executions", execution.execute)))
                        stack.enter_context(patch.object(profile, "save_frontend_profile_file_v1",
                                                         counted("profile_saves", profile.save_frontend_profile_file_v1)))
                        stack.enter_context(patch.object(os, "replace", replaced))
                        stack.enter_context(patch.object(Handler, "send_response", responded))

                        def connect(server, script):
                            http = Browser(server)
                            cdp.call("Network.setCookie", name=http.cookie.split("=", 1)[0], value=http.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)
                            cdp.navigate(server.origin + "/review")

                        connect(server, script)
                        submit(f'.language-selector button[value="{locale}"]', "/actions/profile/language")
                        checkpoint("explicit-import", {"profile_saves": 1, "persistent_replacements": 1})
                        import_file(source, server)
                        checkpoint("explicit-execution", {})
                        submit('form[action="/actions/review/run-imported"] button', "/actions/review/run-imported")
                        state = server.app_context.review_state
                        checkpoint("passive-initial", {"review_executions": 1})
                        observe("initial", locale, state, server)
                        saved_request = downloads("initial", state, server)
                        checkpoint("native-language", {})
                        other = "en" if locale == "de" else "de"
                        # Every cell exercises native language return; enabled cells also
                        # exercise enhanced return on the way back.
                        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
                        submit(f'.language-selector button[value="{other}"]', "/actions/profile/language")
                        checkpoint("passive-other-language", {"profile_saves": 1, "persistent_replacements": 1})
                        observe("native-language", other, state, server)
                        downloads("native-language", state, server)
                        checkpoint("language-back", {})
                        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                        if script:
                            cdp.navigate(server.origin + "/review")
                        submit(f'.language-selector button[value="{locale}"]', "/actions/profile/language")
                        checkpoint("passive-navigation", {"profile_saves": 1, "persistent_replacements": 1})
                        observe("language-back", locale, state, server)
                        cdp.navigate(server.origin + "/")
                        cdp.navigate(server.origin + "/review")
                        observe("returned", locale, state, server)
                        checkpoint("restart-and-import", {})
                        close_fixture(fixture)
                        fixture = localized_server.__wrapped__(directory)
                        server = next(fixture)
                        connect(server, script)
                        assert server.app_context.review_state.latest_successful_result is None
                        import_file(saved_request, server)
                        checkpoint("explicit-reexecution", {})
                        submit('form[action="/actions/review/run-imported"] button', "/actions/review/run-imported")
                        restarted = server.app_context.review_state
                        assert restarted.request_json_bytes == state.request_json_bytes
                        assert restarted.result_json_bytes == state.result_json_bytes
                        checkpoint("passive-restarted", {"review_executions": 1})
                        observe("restarted", locale, restarted, server)
                        downloads("restarted", restarted, server)
                        checkpoint("complete", {})
                finally:
                    close_fixture(fixture)
        report["completed"] = True
        report["operations"] = dict(sum((Counter(v) for c in report["cases"] for v in c["phases"].values()), Counter()))
        report["posts"] = dict(Counter(f'{p["status"]} {p["path"]}' for c in report["cases"] for p in c["posts"]))
    finally:
        local.close()
        report["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        (args.output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"completed": report["completed"], "operations": report.get("operations"),
                      "posts": report.get("posts"), "elapsed_seconds": report["elapsed_seconds"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
