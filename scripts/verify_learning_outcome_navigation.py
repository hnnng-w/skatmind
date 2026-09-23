# ruff: noqa: E501 - Keep native browser selectors and evidence records legible.
"""Optional #256 independent-Wheel evidence, using the existing dependency-free harness."""
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
from verify_learning_entry_purpose import MODULES, hashes
from verify_match_format_presentation import native_text
from verify_recording_deletion import keyboard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
import test_recorded_review_navigation as navigation_fixtures  # noqa: E402
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
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1  # noqa: E402
from skatmind.match_workspace_persistence_codec import (  # noqa: E402
    build_match_workspace_persistence_document_v1,
)


def target(active, match_id):
    return "learning-match-" + digest(f"learning-match-v1:{active.handle}:{match_id}".encode())


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = dict(completed=False, phase=args.phase, python=sys.version, package=skatmind.__version__,
        installed_module=skatmind.__file__, wheel=hashes({"wheel": args.wheel.read_bytes()}),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        registry=[len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        keys={k: len(v) for k, v in load_frontend_translation_catalogs_v1().items()}, hashes={}, runs=[],
        limits=["Synthetic headless Edge, not physical-device, screen-reader or maintainer UAT.",
                "200% default-font preference measured as computed text, not browser zoom.",
                "Native landing is captured before any manual target scroll/focus; next Tab measured separately."])
    names = (*MODULES, *(("learning_outcome_navigation.py",) if after else ()))
    for name in names:
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = (ROOT / "src/skatmind/app_web" / name).read_bytes() if after else subprocess.check_output(
            ["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT)
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
    try:
        def run_one(locale, script):
                root = args.output / (locale + ("-js" if script else "-native"))
                root.mkdir()
                fixture = localized_server.__wrapped__(root)
                server = next(fixture)
                client, app = Browser(server), server.app_context
                calls, requests, responses = Counter(), Counter(), []
                item = dict(locale=locale, javascript=script, actions=[], operations=[], landings=[], downloads=[])
                evidence["runs"].append(item)
                local = None

                def counted(name, real):
                    def wrapped(*a, **kw):
                        calls[name] += 1
                        return real(*a, **kw)
                    return wrapped

                def request_counter(method, real):
                    def wrapped(handler):
                        requests[method + " " + handler.path.split("?", 1)[0]] += 1
                        return real(handler)
                    return wrapped

                def operation(name, function):
                    before, req = calls.copy(), requests.copy()
                    result = function()
                    item["operations"].append(dict(name=name, calls=dict(calls-before), requests=dict(requests-req)))
                    return result

                def size(width, height):
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                             deviceScaleFactor=1, mobile=False)

                def action(selector, name, *, pointer=False, posts=1):
                    def invoke():
                        response_start = len(responses)
                        cdp.events.clear()
                        if pointer:
                            point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getClientRects()[0];return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                            for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                                cdp.call("Input.dispatchMouseEvent", type=kind, **point,
                                    **({"button": "left", "clickCount": 1} if kind != "mouseMoved" else {}))
                            time.sleep(.8)
                        else:
                            cdp.activate(selector)
                        cdp.evaluate("void 0")
                        sequence = [dict(method=e["params"]["request"]["method"],
                            url=e["params"]["request"]["url"], redirect=e["params"].get("redirectResponse"))
                            for e in cdp.events]
                        assert sum(e["method"] == "POST" for e in sequence) == posts, (name, sequence)
                        item["actions"].append(dict(name=name, pointer=pointer, sequence=sequence,
                            responses=responses[response_start:],
                            location=cdp.evaluate("location.pathname+location.hash")))
                    operation(name, invoke)

                def landing(name, expected, *, error=False):
                    # No target activation, focus(), scrollIntoView(), or scrollTo() here.
                    before, req = calls.copy(), requests.copy()
                    result = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),a=document.activeElement;
                        const r=e?.getBoundingClientRect(),h=e?.querySelector('h2,h3'),hr=h?.getBoundingClientRect();
                        return {url:location.pathname+location.hash,scrollY,viewport:[innerWidth,innerHeight],
                            bodyFont:getComputedStyle(document.body).fontSize,client:document.documentElement.clientWidth,
                            overflow:[...document.querySelectorAll('body *')].filter(n=>n.checkVisibility() && n.getBoundingClientRect().right>document.documentElement.clientWidth+1)
                                .map(n=>({tag:n.tagName,id:n.id,cls:n.className,text:n.innerText?.slice(0,100),rect:n.getBoundingClientRect().toJSON()})),
                            scrollWidth:document.documentElement.scrollWidth,target:selector,exists:!!e,
                            rect:r?.toJSON(),heading:h?.innerText,headingRect:hr?.toJSON(),text:e?.innerText,
                            focus:{id:a.id,tag:a.tagName,name:a.name,href:a.getAttribute('href')},
                            notices:[...document.querySelectorAll('[data-operation-feedback]')].map(n=>({text:n.innerText,
                                owner:n.parentElement.id})),labels:[...document.querySelectorAll('main a,main button,main summary')]
                                .filter(n=>n.checkVisibility()).map(n=>({tag:n.tagName,text:n.innerText,aria:n.getAttribute('aria-label')}))};})""" + "(" + json.dumps(".error-summary" if error else "#" + expected) + ")")
                    result["name"] = name
                    cdp.screenshot(root / (name + ".png"))
                    keyboard(cdp, "Tab", "Tab", 9)
                    result["next_tab"] = cdp.evaluate("(()=>{const e=document.activeElement;return {id:e.id,tag:e.tagName,name:e.name,text:e.innerText,href:e.getAttribute('href')}})()")
                    item["landings"].append(result)
                    assert calls == before and requests == req
                    if after or error:
                        assert result["exists"], result
                        assert result["rect"]["y"] < result["viewport"][1] and result["rect"]["y"] >= -1, result
                        assert result["scrollWidth"] <= result["client"] + 1, result
                        assert result["focus"]["id"] == expected if not error else result["focus"]["tag"] == "SECTION", result
                        assert result["next_tab"]["tag"] in {"A", "SUMMARY", "BUTTON", "INPUT", "SELECT"}, result
                    return result

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
                        stack.enter_context(patch.object(navigation_fixtures, "save_match_workspace_file_v1",
                            counted("fixture_match_saves", navigation_fixtures.save_match_workspace_file_v1)))
                        real_response = Handler.send_response
                        def response_status(handler, status, *a, **kw):
                            responses.append(dict(method=handler.command, path=handler.path.split("?", 1)[0], status=int(status)))
                            return real_response(handler, status, *a, **kw)
                        stack.enter_context(patch.object(Handler, "send_response", response_status))

                        def setup():
                            record_score_review_game(client)
                            follow(client, client.submit(score_review_form(client)))
                            path, workspace = saved_partial_match(server)
                            follow(client, client.submit(chooser_form(client.page("/review/recorded"), "matches")))
                            follow(client, client.submit(operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                            report = app.managed_stateful.active_match.capture.report_store.list()[0]
                            source_export = client.request("GET", f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")[2]
                            other = independent_workspace(workspace, "zz-independent-same-title")
                            assert other.match_definition.title == workspace.match_definition.title
                            other_path = path.with_name("other.json")
                            assert navigation_fixtures.save_match_workspace_file_v1(other_path, build_match_workspace_persistence_document_v1(other), expected_content_fingerprint=None).status == "saved"
                            unrelated_path = path.with_name("unrelated.json")
                            unrelated_workspace = independent_workspace(workspace, "unrelated-result-source")
                            assert navigation_fixtures.save_match_workspace_file_v1(unrelated_path, build_match_workspace_persistence_document_v1(unrelated_workspace), expected_content_fingerprint=None).status == "saved"
                            open_form = next(f for f in Forms(client.page("/review/recorded")).forms
                                if f["action"] == "/review/open-recording" and f["values"]["handle"] == source_handle(unrelated_path))
                            follow(client, client.submit(open_form))
                            follow(client, client.submit(operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                            return path, workspace, other_path, other, source_export
                        path, workspace, other_path, other, source_export = operation("fixture: real Session SJ and unrelated Match Report; two saved partial Matches", setup)
                        session, match = app.managed_stateful.active_session, app.managed_stateful.active_match
                        retained_execution, report = session.execution, match.capture.report_store.list()[0]
                        assert retained_execution.request.document["actual_card_played"] == "SJ" and report.value.status == "executed"
                        report_route = f"/matches/api/v1/reports/{report.report_id}.json"
                        unrelated = {"session_file": session.path.read_bytes(), "match_file": match.path.read_bytes(),
                            "session_result": client.request("GET", "/sessions/downloads/result.json")[2],
                            "match_report": client.request("GET", report_route)[2]}
                        item["unrelated"] = hashes(unrelated)
                        local = LocalBrowser(args.browser, root / "browser-profile")
                        cdp = local.cdp
                        item["browser"] = local.version
                        cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                        size(1365, 900)
                        cdp.navigate(server.origin + "/learning")
                        action(f'.language-selector button[value="{locale}"]', "initial-language")
                        native_text(cdp, 'form[action="/learning/create"] [name="collection_name"]', 'Synthetic outcome collection')
                        action('form[action="/learning/create"] button', "create", pointer=True)
                        active = app.managed_stateful.active_learning
                        assert not active.corpus.store.match_snapshots and active.corpus.prepared_artifacts is None
                        # Two equal-title Matches ensure the second target is not the first row.
                        for source, saved in ((path, workspace), (other_path, other)):
                            before, req = calls.copy(), requests.copy()
                            choose_source(cdp, source_handle(source), item)
                            assert calls == before and requests == req
                            name = "first-add" if source == path else "second-match-add"
                            action(ADD + ' > button', name, pointer=source == other_path)
                            expected = target(active, saved.match_definition.match_id)
                            assert cdp.evaluate("location.pathname+location.hash") == ("/learning/current#" + expected if after else direct.LEARNING_ENTRY_LOCATION)
                            landing(name, expected)
                        item["source_identities"] = [workspace.match_definition.match_id, other.match_definition.match_id]
                        first = active.corpus.store.document.catalog.current_matches
                        action(BUILD, "evaluate", pointer=True)
                        assert cdp.evaluate("location.pathname+location.hash") == ("/learning/current#learning-results" if after else "/learning/current")
                        landing("evaluate", "learning-results")
                        retained = downloads(client)
                        item["retained_exports"] = {kind: {"filename": filename, **hashes({kind: raw})[kind]} for kind, (filename, raw) in retained.items()}
                        files, artifacts = saved_bytes(active.path), active.corpus.prepared_artifacts
                        size(390, 844)
                        choose_source(cdp, source_handle(other_path), item)
                        action(ADD + ' > button', "identical-add")
                        landing("identical-add", target(active, other.match_definition.match_id))
                        assert active.last_result.status == "unchanged" and active.corpus.prepared_artifacts is artifacts
                        assert downloads(client) == retained and saved_bytes(active.path) == files
                        # Real non-current source blocker, without automatic Report incorporation.
                        first_snapshot = next(s.match_snapshot_id for s in first if s.match_id == workspace.match_definition.match_id)
                        operation("fixture: explicit exact Report source", lambda: learning.import_report_source_bytes_into_unified_learning_v1(active, source_export, match_snapshot_id=first_snapshot))
                        operation("fixture: external later saved source", lambda: external_pass(other_path, other))
                        size(320, 800)
                        cdp.navigate(server.origin + "/learning/current")
                        choose_source(cdp, source_handle(other_path), item)
                        action(ADD + ' > button', "later-add-keep-current")
                        landing("later-add-keep-current", target(active, other.match_definition.match_id))
                        assert active.corpus.store.document.catalog.current_matches == first and active.corpus.prepared_artifacts is None
                        cdp.activate('#insight-versions details > summary')
                        action('form:has(input[value="select_current_snapshot"]) button', "explicit-selection")
                        assert cdp.evaluate("location.pathname+location.hash") == "/learning/current"
                        action(BUILD, "evaluate-selected-version")
                        landing("evaluate-selected-version", "learning-results")
                        # A bad scalar is an actual native validation failure, not a failed computation.
                        cdp.activate('#learning-build details > summary')
                        native_text(cdp, '#learning-build [name="train_weight"]', "0")
                        action(BUILD, "failed-recreation")
                        landing("failed-recreation", "", error=True)
                        assert active.corpus.prepared_artifacts is not None
                        native_text(cdp, '#learning-build [name="train_weight"]', "70")
                        action(BUILD, "recreate")
                        landing("recreate", "learning-results")
                        # Real missing-file source rejection from the previously emitted form.
                        choose_source(cdp, source_handle(other_path), item)
                        missing = other_path.with_suffix(".unavailable")
                        other_path.rename(missing)
                        try:
                            action(ADD + ' > button', "missing-source")
                            landing("missing-source", "", error=True)
                        finally:
                            missing.rename(other_path)
                        assert active.corpus.prepared_artifacts is not None
                        # Make the exact Report non-current with an explicit saved source update/select.
                        operation("fixture: external Report-source revision", lambda: external_pass(path, workspace))
                        cdp.navigate(server.origin + "/learning/current")
                        choose_source(cdp, source_handle(path), item)
                        action(ADD + ' > button', "report-source-add")
                        cdp.activate('#insight-versions details > summary')
                        action('form:has(input[value="select_current_snapshot"]):has(input[value="' + workspace.match_definition.match_id + '"]) button', "select-report-source-version")
                        assert cdp.evaluate("document.querySelector('#learning-build form')===null")
                        action('a[href="#learning-sources"]', "blocker-remedy", posts=0)
                        # Blocker is the existing source region, not a successful preparation.
                        cdp.screenshot(root / "source-blocker.png")
                        action('form:has(input[value="remove_strategy_teacher_report"]) button', "remove-source")
                        action(BUILD, "evaluate-after-remedy")
                        landing("evaluate-after-remedy", "learning-results")
                        retained = downloads(client)
                        item["final_exports"] = {kind: {"filename": filename, **hashes({kind: raw})[kind]} for kind, (filename, raw) in retained.items()}
                        action('a[href="#learning-results"]', "view-evaluation", posts=0)
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
                        files = saved_bytes(active.path)
                        artifacts = (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts)
                        def passive():
                            for route in ("/", "/learning", "/learning/current"):
                                cdp.navigate(server.origin + route)
                            for language in ("en" if locale == "de" else "de", locale):
                                action(f'.language-selector button[value="{language}"]', "passive-language-" + language)
                            assert saved_bytes(active.path) == files and downloads(client) == retained
                            assert all(a is b for a, b in zip(artifacts, (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts), strict=True))
                        operation("passive navigation and language", passive)
                        # Reuse the same sources with a native browser font preference set BEFORE load.
                        local.close()
                        font_profile = root / "font-profile"
                        (font_profile / "Default").mkdir(parents=True)
                        (font_profile / "Default/Preferences").write_text(json.dumps({"webkit": {"webprefs": {"default_font_size": 32}}}))
                        local = LocalBrowser(args.browser, font_profile)
                        cdp = local.cdp
                        cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                        size(320, 800)
                        cdp.navigate(server.origin + "/learning/current")
                        assert cdp.evaluate("getComputedStyle(document.body).fontSize") == "32px"
                        choose_source(cdp, source_handle(other_path), item)
                        action(ADD + ' > button', "text200-identical")
                        landing("text200-identical", target(active, other.match_definition.match_id))
                        action(BUILD, "text200-recreate")
                        landing("text200-recreate", "learning-results")
                        # Strict reopening restores only saved sources; regeneration remains explicit.
                        loaded = load_learning_corpus_directory_v1(active.path)
                        page = client.page("/learning")
                        open_form = next(f for f in Forms(page).forms if f["action"] == "/learning/open")
                        operation("explicit strict reopen HTTP", lambda: follow(client, client.submit(open_form)))
                        reopened = app.managed_stateful.active_learning
                        assert reopened is not active and reopened.corpus.store.document == loaded.document
                        assert reopened.corpus.prepared_artifacts is None
                        cdp.navigate(server.origin + "/learning/current")
                        action(BUILD, "text200-regenerate-reopened")
                        landing("text200-regenerate-reopened", "learning-results")
                        assert downloads(client) == retained
                        assert session.execution is retained_execution and match.capture.report_store.list() == (report,)
                        assert unrelated == {"session_file": session.path.read_bytes(), "match_file": match.path.read_bytes(),
                            "session_result": client.request("GET", "/sessions/downloads/result.json")[2],
                            "match_report": client.request("GET", report_route)[2]}
                        assert {k: calls[k] for k in ("imports", "preparations", "selections", "catalog_changes", "fixture_match_saves")} == dict(
                            imports=6, preparations=6, selections=2, catalog_changes=6, fixture_match_saves=5)
                        item["calls"], item["requests"] = dict(calls), dict(requests)
                finally:
                    if local is not None:
                        local.close()
                    fixture.close()
        for locale in ("de", "en"):
            for script in (False, True):
                run_one(locale, script)
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"completed": True, "runs": len(evidence["runs"]), "landings": sum(len(r["landings"]) for r in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
