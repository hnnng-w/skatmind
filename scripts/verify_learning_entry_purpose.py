# ruff: noqa: E501 - Keep native selectors and evidence records legible.
"""Optional independent-Wheel #255 evidence; disposable sources and real operations only."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_learning_direct_entry import ADD, BUILD, choose_source, digest
from verify_match_format_presentation import native_text
from verify_recording_deletion import measure, submit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
from test_frontend_language_switching import localized_server  # noqa: E402
from test_learning_direct_entry_web import (  # noqa: E402
    downloads,
    independent_workspace,
    saved_bytes,
    source_handle,
)
from test_match_recording_recovery_web import follow, operation_form  # noqa: E402
from test_recorded_review_navigation import (  # noqa: E402
    chooser_form,
    external_pass,
    saved_partial_match,
)
from test_session_recorded_review_web import (  # noqa: E402
    Browser,
    Forms,
    record_score_review_game,
    score_review_form,
)

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profiles  # noqa: E402
import skatmind.app_web.learning_direct_entry as direct  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.app_web.server as web  # noqa: E402
import skatmind.app_web.stateful_context as managed  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
import skatmind.learning_corpus_import as corpus_import  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.app_web.translation_catalog import (  # noqa: E402
    load_frontend_translation_catalogs_v1,
)
from skatmind.app_web.translation_catalog import (  # noqa: E402
    translate_frontend_message_v1 as t,
)
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1  # noqa: E402
from skatmind.match_workspace_persistence import save_match_workspace_file_v1  # noqa: E402
from skatmind.match_workspace_persistence_codec import (  # noqa: E402
    build_match_workspace_persistence_document_v1,
)

MODULES = ("rendering.py", "entry_rendering.py", "friendly_creation_rendering.py",
    "information_architecture.py", "task_first_learning_rendering.py", "task_first_projections.py",
    "learning_direct_entry.py", "learning_direct_entry_http.py", "learning_frontend.py", "server.py",
    "form_registry.py", "operation_feedback.py", "operation_feedback_mapping.py", "language_context.py",
    "language_form_preservation.py", "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json")


def hashes(values):
    return {str(k): {"bytes": len(v), "sha256": digest(v)} for k, v in values.items()}


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = dict(completed=False, phase=args.phase, python=sys.version, package=skatmind.__version__,
        installed_module=skatmind.__file__, wheel_sha256=digest(args.wheel.read_bytes()),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        registry=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        keys={k: len(v) for k, v in load_frontend_translation_catalogs_v1().items()}, hashes={}, runs=[],
        limitations=["Synthetic headless Edge; no physical-device, screen-reader or maintainer UAT claim.",
            "Computed 200% text is not browser zoom. Current Add/Build redirects are observed, not repaired.",
            "HTTP fixture setup is separate from native collection actions; no simulated successful saves or preparation."])
    for name in MODULES:
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = (ROOT / "src/skatmind/app_web" / name).read_bytes() if after else subprocess.check_output(
            ["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT)
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
    try:
        for locale in ("de", "en"):
            for script in (False, True):
                key = locale + ("-js" if script else "-native")
                root = args.output / key
                root.mkdir()
                fixture = localized_server.__wrapped__(root)
                server = next(fixture)
                local = LocalBrowser(args.browser, root / "browser-profile")
                cdp, client = local.cdp, Browser(server)
                app = server.app_context
                calls, requests = Counter(), Counter()
                item = dict(key=key, locale=locale, javascript=script, browser=local.version,
                            actions=[], measurements=[], operations=[], passive=[], downloads=[])
                evidence["runs"].append(item)

                def counted(label, real, calls=calls):
                    def wrapped(*arguments, **kw):
                        calls[label] += 1
                        return real(*arguments, **kw)
                    return wrapped

                def request_counter(method, real, requests=requests):
                    def wrapped(handler):
                        requests[method + " " + handler.path.split("?", 1)[0]] += 1
                        return real(handler)
                    return wrapped

                def operation(name, function, calls=calls, requests=requests, item=item):
                    before, req = calls.copy(), requests.copy()
                    result = function()
                    item["operations"].append(dict(name=name, calls=dict(calls-before), requests=dict(requests-req)))
                    return result

                def action(selector, name, pointer=False, posts=1, cdp=cdp, item=item,
                           requests=requests, operation=operation):
                    def invoke():
                        if not pointer:
                            submit(cdp, selector, item, name, expected_posts=posts)
                        else:
                            old = requests.copy()
                            point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getClientRects()[0];return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                            for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                                cdp.call("Input.dispatchMouseEvent", type=kind, **point,
                                         **({"button": "left", "clickCount": 1} if kind != "mouseMoved" else {}))
                            time.sleep(.8)
                            assert sum(v for k, v in (requests-old).items() if k.startswith("POST ")) == posts
                        item["actions"].append(dict(name=name, pointer=pointer,
                            location=cdp.evaluate("location.pathname+location.hash"),
                            focus=cdp.evaluate("({id:document.activeElement.id,tag:document.activeElement.tagName,name:document.activeElement.name})")))
                    return operation(name, invoke)

                def capture(name, selector, calls=calls, requests=requests, cdp=cdp,
                            root=root, item=item):
                    before, req = calls.copy(), requests.copy()
                    measure(cdp, root, item, name, selector)
                    assert calls == before and requests == req
                    item["measurements"][-1]["controls"] = cdp.evaluate("[...document.querySelectorAll('main button,main a,main select')].filter(e=>e.checkVisibility()).map(e=>({tag:e.tagName,text:e.textContent,href:e.getAttribute('href'),name:e.name,disabled:e.disabled,font:getComputedStyle(e).fontSize}))")
                    normal = cdp.evaluate("parseFloat(getComputedStyle(document.body).fontSize)")
                    cdp.evaluate("(()=>{const a=[...document.querySelectorAll('body,body *')];const s=a.map(e=>parseFloat(getComputedStyle(e).fontSize));a.forEach((e,i)=>e.style.fontSize=s[i]*2+'px')})()")
                    enlarged = cdp.evaluate("parseFloat(getComputedStyle(document.body).fontSize)")
                    assert enlarged == 2 * normal
                    item["measurements"][-1]["computed_body_text"] = [normal, enlarged]
                    cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>e.style.removeProperty('font-size'))")

                try:
                    with ExitStack() as stack:
                        for module, name, label in (
                            (session_files, "save_session_file", "session_saves"),
                            (execution, "execute", "session_executions"),
                            (match_context, "save_match_workspace_file_v1", "match_saves"),
                            (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                            (match_state, "_decision_preparation_summary", "existing_match_preparation"),
                            (profiles, "save_frontend_profile_file_v1", "profile_saves"),
                            (managed, "discover_managed_items_v1", "managed_discovery"),
                            (web, "discover_managed_items_v1", "server_discovery"),
                            (direct, "discover_managed_items_v1", "add_source_revalidation"),
                            (learning, "initialize_learning_corpus_web_v1", "collection_creations"),
                            (learning, "import_match_workspace_into_learning_corpus_web_v1", "imports"),
                            (learning, "prepare_learning_corpus_artifacts_web_v1", "preparations"),
                            (learning, "select_current_learning_corpus_snapshot_web_v1", "selections"),
                            (learning, "import_strategy_teacher_report_into_learning_corpus_web_v1", "report_imports"),
                            (corpus_import, "save_learning_corpus_catalog_v1", "catalog_changes")):
                            stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
                        for method in ("GET", "POST"):
                            stack.enter_context(patch.object(Handler, "do_" + method, request_counter(method, getattr(Handler, "do_" + method))))

                        def setup(client=client, server=server, app=app):
                            record_score_review_game(client)
                            follow(client, client.submit(score_review_form(client)))
                            path, workspace = saved_partial_match(server)
                            follow(client, client.submit(chooser_form(client.page("/review/recorded"), "matches")))
                            follow(client, client.submit(operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                            source_context = app.managed_stateful.active_match
                            source_report = source_context.capture.report_store.list()[0]
                            source_export = client.request("GET", f"/matches/api/v1/reports/{source_report.report_id}/strategy-source.json")[2]
                            other = independent_workspace(workspace, "unrelated-browser-match")
                            other_path = path.with_name("other.json")
                            assert save_match_workspace_file_v1(other_path, build_match_workspace_persistence_document_v1(other), expected_content_fingerprint=None).status == "saved"
                            form = next(f for f in Forms(client.page("/review/recorded")).forms if f["action"] == "/review/open-recording" and f["values"]["handle"] == source_handle(other_path))
                            follow(client, client.submit(form))
                            follow(client, client.submit(operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                            return path, workspace, source_export
                        path, workspace, source_export = operation("fixture: real Session SJ review, partial source Report and unrelated Match Report", setup)
                        session, match = app.managed_stateful.active_session, app.managed_stateful.active_match
                        retained_execution, report = session.execution, match.capture.report_store.list()[0]
                        assert retained_execution.request.document["actual_card_played"] == "SJ"
                        assert report.value.status == "executed"
                        report_route = f"/matches/api/v1/reports/{report.report_id}.json"
                        unrelated = {"session_file": session.path.read_bytes(), "match_file": match.path.read_bytes(),
                            "session_result": client.request("GET", "/sessions/downloads/result.json")[2],
                            "match_report": client.request("GET", report_route)[2]}
                        item["unrelated"] = hashes(unrelated)
                        cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                        cdp.navigate(server.origin + "/")
                        action(f'.language-selector button[value="{locale}"]', "initial-language")
                        capture("home", "main")
                        capture("home-learning-card", ".home-group:last-of-type")
                        assert cdp.evaluate("document.querySelectorAll('.task-card').length") == (5 if after else 4)
                        action('.home-group a[href="/learning"]', "home-learning", pointer=True, posts=0)
                        capture("landing", "main")
                        assert t(locale, "entry.learning") in cdp.evaluate("document.querySelector('main').innerText")
                        native_text(cdp, 'form[action="/learning/create"] [name="collection_name"]', '<Synthetic & collection> ' + 'LongName' * 15)
                        action('form[action="/learning/create"] button', "create", pointer=True)
                        target = app.managed_stateful.active_learning
                        assert not target.corpus.store.match_snapshots and target.corpus.prepared_artifacts is None
                        assert calls["imports"] == calls["preparations"] == 0
                        capture("empty", "#task-first-learning")
                        action('a[href="/learning/recorded-matches/refresh"]', "explicit-refresh", posts=0)
                        operation("source-dropdown-only", lambda cdp=cdp, path=path, item=item: choose_source(cdp, source_handle(path), item))
                        assert calls["imports"] == 0 and not target.corpus.store.match_snapshots
                        for language in ("en" if locale == "de" else "de", locale):
                            action(f'.language-selector button[value="{language}"]', "unsent-source-language-" + language)
                            assert cdp.evaluate(f"document.querySelector('{ADD} [name=source_handle]').value") == (source_handle(path) if script else "")
                        if not script:
                            choose_source(cdp, source_handle(path), item)
                        assert calls["imports"] == calls["preparations"] == 0
                        action(ADD + ' > button', "first-add")
                        assert cdp.evaluate("location.pathname+location.hash") == direct.LEARNING_ENTRY_LOCATION
                        assert target.corpus.store.match_snapshots[0].workspace == workspace
                        first = target.corpus.store.document.catalog.current_matches
                        capture("ready", "#learning-build")
                        action(BUILD, "evaluate", pointer=True)
                        assert cdp.evaluate("location.pathname+location.hash") == "/learning/current"
                        prepared = learning.build_unified_learning_state_v1(target)["prepared"]
                        item["coverage"] = {k: prepared[k] for k in ("observed_decision_count", "record_count", "skipped_decision_count", "strategy_teacher_evidence_count")}
                        assert tuple(item["coverage"].values()) == (6, 2, 4, 0)
                        capture("prepared", "#task-first-learning")
                        action('a[href="#learning-results"]', "view-evaluation", posts=0)
                        assert cdp.evaluate("document.activeElement.id") == "learning-results"
                        retained = downloads(client)
                        item["download_bytes"] = {kind: {"filename": filename, **hashes({kind: raw})[kind]} for kind, (filename, raw) in retained.items()}
                        for kind, (_filename, raw) in retained.items():
                            destination = root / ("download-" + kind)
                            destination.mkdir()
                            cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
                            action(f'a[download][href="/learning/downloads/{kind.replace("_", "-")}.json"]', "download-" + kind, pointer=True, posts=0)
                            for _ in range(100):
                                saved = [p for p in destination.iterdir() if p.is_file() and not p.name.endswith(".crdownload")]
                                if saved:
                                    break
                                time.sleep(.1)
                            assert len(saved) == 1 and saved[0].read_bytes() == raw
                            item["downloads"].append(dict(kind=kind, bytes=len(raw), sha256=digest(raw)))

                        files_before = saved_bytes(target.path)
                        sources_before = saved_bytes(app.managed_stateful.root("matches"))
                        artifacts = (target.corpus.prepared_artifacts, target.corpus.tactical_prepared_artifacts, target.corpus.tactical_coaching_prepared_artifacts)
                        before, req = calls.copy(), requests.copy()
                        for route in ("/", "/learning", "/learning/current"):
                            cdp.navigate(server.origin + route)
                        for language in ("en" if locale == "de" else "de", locale):
                            action(f'.language-selector button[value="{language}"]', "passive-language-" + language)
                        assert saved_bytes(target.path) == files_before and saved_bytes(app.managed_stateful.root("matches")) == sources_before
                        assert all(a is b for a, b in zip(artifacts, (target.corpus.prepared_artifacts, target.corpus.tactical_prepared_artifacts, target.corpus.tactical_coaching_prepared_artifacts), strict=True))
                        assert downloads(client) == retained
                        item["passive"].append(dict(calls=dict(calls-before), requests=dict(requests-req), corpus=hashes(files_before), sources=hashes(sources_before)))
                        assert not any((calls-before)[k] for k in ("imports", "preparations", "selections", "catalog_changes", "session_saves", "match_saves", "session_executions", "match_executions"))
                        choose_source(cdp, source_handle(path), item)
                        action(ADD + ' > button', "identical-add")
                        assert target.last_result.status == "unchanged" and saved_bytes(target.path) == files_before
                        assert downloads(client) == retained

                        operation("explicit Report-source fixture import for real blocker", lambda target=target, source_export=source_export, first=first: learning.import_report_source_bytes_into_unified_learning_v1(target, source_export, match_snapshot_id=first[0].match_snapshot_id))
                        operation("fixture: external saved source revision", lambda path=path, workspace=workspace: external_pass(path, workspace))
                        cdp.navigate(server.origin + "/learning/current")
                        choose_source(cdp, source_handle(path), item)
                        action(ADD + ' > button', "later-add-keep-current")
                        assert target.corpus.store.document.catalog.current_matches == first
                        assert target.corpus.prepared_artifacts is None
                        cdp.activate('#insight-versions details > summary')
                        action('form:has(input[value="select_current_snapshot"]) button', "explicit-selection")
                        assert target.corpus.store.document.catalog.current_matches != first
                        assert learning.build_unified_learning_state_v1(target)["strategy_sources"][0]["binding_status"] == "non_current"
                        capture("source-blocked", "#learning-build")
                        assert cdp.evaluate("document.querySelector('#learning-build form')===null")
                        action('a[href="#learning-sources"]', "blocker-remedy", posts=0)
                        action('form:has(input[value="remove_strategy_teacher_report"]) button', "remove-blocking-source")
                        action(BUILD, "evaluate-selected-version")
                        action(BUILD, "explicit-recreate")
                        assert calls["imports"] == 3 and calls["preparations"] == 3 and calls["selections"] == 1
                        saved_store = load_learning_corpus_directory_v1(target.path)
                        regenerated = downloads(client)
                        corpus_bytes = saved_bytes(target.path)
                        cdp.navigate(server.origin + "/learning")
                        action('form[action="/learning/open"] button', "strict-reopen")
                        reopened = app.managed_stateful.active_learning
                        assert reopened is not target and reopened.corpus.store == saved_store
                        assert reopened.corpus.prepared_artifacts is None and saved_bytes(target.path) == corpus_bytes
                        action(BUILD, "explicit-regeneration-after-reopen")
                        assert downloads(client) == regenerated
                        item["final_corpus"] = hashes(corpus_bytes)
                        assert app.managed_stateful.active_session is session and session.execution is retained_execution
                        assert app.managed_stateful.active_match is match and match.capture.report_store.list() == (report,)
                        assert unrelated == {"session_file": session.path.read_bytes(), "match_file": match.path.read_bytes(),
                            "session_result": client.request("GET", "/sessions/downloads/result.json")[2],
                            "match_report": client.request("GET", report_route)[2]}
                        for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                            assert digest(client.request("GET", route)[2]) == evidence["hashes"][resource]
                        item.update(calls=dict(calls), requests=dict(requests), completed=True)
                        print(key, "complete", len(item["measurements"]), "measurements", flush=True)
                finally:
                    local.close()
                    fixture.close()
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print("Evidence completed:", evidence["completed"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("browser", "output", "wheel"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    run(parser.parse_args())
