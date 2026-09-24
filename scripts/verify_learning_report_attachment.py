# ruff: noqa: E501 - Keep optional native selectors and evidence records legible.
"""Independent #259 Wheel evidence; real optional multipart submission, no dialog claim."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
from email import policy
from email.parser import BytesParser
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch

import verify_learning_outcome_navigation as prior
from test_learning_report_attachment_web import open_other, save_other
from test_learning_result_explanations import GROUPS
from test_learning_version_selection_web import save_variant
from verify_local_time_entry import native_select

import skatmind.learning_corpus_strategy_teacher_builder as teacher
from skatmind.match_workspace_contracts import _build_match_workspace_v1

UPLOAD = 'form:has(input[value="import_strategy_teacher_report"])'
TARGET = UPLOAD + ' [name="match_snapshot_id"]'


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(prior.skatmind.__file__).resolve().is_relative_to(prior.ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = dict(completed=False, phase=args.phase, python=prior.sys.version,
        package=prior.skatmind.__version__, installed_module=prior.skatmind.__file__,
        versions={name: version(name) for name in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        wheel=prior.hashes({"wheel": args.wheel.read_bytes()}),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=prior.ROOT, text=True).strip(),
        registry=[len(prior.UNIFIED_FRONTEND_POST_ROUTES), len(prior.FRONTEND_FORM_REGISTRY)],
        keys={k: len(v) for k, v in prior.load_frontend_translation_catalogs_v1().items()},
        hashes={}, runs=[], limits=[
            "Synthetic headless Edge; no physical file-dialog, screen-reader, device, zoom or UAT claim.",
            "DOM.setFileInputFiles supplies disposable synthetic files; keyboard/pointer submits native multipart forms.",
            "200% is a default-font preference measured as 32px, not browser zoom.",
            "Fixture saves/executions and returned-form HTTP reopen are separate from native browser operations."])
    assert evidence["registry"] == [67, 112]
    assert evidence["keys"] == {"de": 1797 if after else 1786, "en": 1797 if after else 1786}
    for name in (*prior.MODULES, "learning_outcome_navigation.py", "learning_result_rendering.py", "validation_rendering.py"):
        raw = (Path(prior.skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((prior.ROOT / "src/skatmind/app_web" / name).read_bytes() if after
                    else subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=prior.ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = prior.digest(raw)
    try:
        def run_one(locale, script):
            root = args.output / (locale + ("-js" if script else "-native"))
            root.mkdir()
            fixture = prior.localized_server.__wrapped__(root)
            server = next(fixture)
            client, app = prior.Browser(server), server.app_context
            calls, requests = Counter(), Counter()
            item = dict(locale=locale, javascript=script, operations=[], actions=[], views=[], downloads=[], uploads=[], states={})
            evidence["runs"].append(item)
            local = None

            def counted(key, real):
                def wrapped(*a, **kw):
                    calls[key] += 1
                    return real(*a, **kw)
                return wrapped

            def request_counter(method, real):
                def wrapped(handler):
                    requests[method + " " + handler.path.split("?", 1)[0]] += 1
                    return real(handler)
                return wrapped

            def multipart_observer(real):
                def wrapped(handler, body, content_type):
                    if content_type.startswith("multipart/"):
                        message = BytesParser(policy=policy.default).parsebytes(
                            ("Content-Type: " + content_type + "\r\n\r\n").encode() + body)
                        parts = []
                        for part in message.iter_parts():
                            raw = part.get_payload(decode=True)
                            parts.append(dict(name=part.get_param("name", header="content-disposition"),
                                filename=part.get_filename(), bytes=len(raw), sha256=prior.digest(raw),
                                value=None if part.get_filename() is not None else raw.decode()))
                        item["uploads"].append(dict(content_type=content_type, bytes=len(body),
                            sha256=prior.digest(body), parts=parts))
                    return real(handler, body, content_type)
                return wrapped

            def operation(name, function):
                before, req = calls.copy(), requests.copy()
                result = function()
                item["operations"].append(dict(name=name, calls=dict(calls-before), requests=dict(requests-req)))
                return result

            def action(selector, name, *, posts=1, pointer=False):
                def invoke():
                    before = sum(v for k, v in requests.items() if k.startswith("POST "))
                    cdp.events.clear()
                    if pointer:
                        point = cdp.evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector) + ");e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
                        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
                            cdp.call("Input.dispatchMouseEvent", type=kind, **point,
                                **({"button": "left", "clickCount": 1} if kind != "mouseMoved" else {}))
                        time.sleep(.8)
                    else:
                        cdp.activate(selector)
                    cdp.evaluate("void 0")
                    assert sum(v for k, v in requests.items() if k.startswith("POST ")) - before == posts
                    item["actions"].append(dict(name=name, pointer=pointer,
                        location=cdp.evaluate("location.pathname+location.hash"),
                        requests=[dict(method=e["params"]["request"]["method"], url=e["params"]["request"]["url"],
                            redirect=e["params"].get("redirectResponse")) for e in cdp.events]))
                return operation(name, invoke)

            def open_sources():
                closed = cdp.evaluate("(()=>{const e=document.querySelector('#learning-sources');return e.closest('details')?.open===false})()")
                if closed:
                    action('#task-first-learning > details.advanced-settings > summary', "open-optional", posts=0)

            def choose_target(identity):
                before, req = calls.copy(), requests.copy()
                index = cdp.evaluate("[...document.querySelector(" + json.dumps(TARGET) + ").options].findIndex(o=>o.value===" + json.dumps(identity) + ")")
                assert index >= 0 and native_select(cdp, TARGET, down=index) == identity
                assert calls == before and requests == req
                item["actions"].append(dict(name="choose-target", identity=identity, requests=[]))

            def supply_file(path):
                before, req = calls.copy(), requests.copy()
                node = cdp.call("DOM.querySelector", nodeId=cdp.call("DOM.getDocument")["root"]["nodeId"],
                    selector=UPLOAD + ' input[type="file"]')["nodeId"]
                cdp.call("DOM.setFileInputFiles", nodeId=node, files=[str(path.resolve())])
                assert cdp.evaluate("document.querySelector(" + json.dumps(UPLOAD + ' input[type="file"]') + ").files.length") == 1
                assert calls == before and requests == req
                item["actions"].append(dict(name="supply-file-via-CDP", sha256=prior.digest(path.read_bytes()), requests=[]))

            def size(width, height):
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

            def measure(name, *, selector="#learning-sources", landing=False):
                before, req = calls.copy(), requests.copy()
                if not landing:
                    cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'})")
                view = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),a=document.activeElement;
                    const rects=n=>{const r=document.createRange();r.selectNodeContents(n);return [...r.getClientRects()].map(x=>x.toJSON())};
                    return {url:location.pathname+location.hash,viewport:[innerWidth,innerHeight],font:getComputedStyle(document.body).fontSize,
                        client:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,
                        text:e.innerText,rect:e.getBoundingClientRect().toJSON(),focus:{id:a.id,tag:a.tagName,name:a.name},
                        content:[...e.querySelectorAll('h3,h4,p,li,label,button,a')].filter(n=>n.checkVisibility()).map(n=>({tag:n.tagName,text:n.innerText,font:getComputedStyle(n).fontSize,rects:rects(n)})),
                        controls:[...e.querySelectorAll('input,select')].map(n=>({name:n.name,type:n.type,value:n.type==='file'?null:n.value,visible:n.checkVisibility(),described:n.getAttribute('aria-describedby'),options:n.options?[...n.options].map(o=>({value:o.value,text:o.text})):null})),
                        details:[...document.querySelectorAll('#task-first-learning details')].map(n=>({open:n.open,text:n.querySelector('summary').innerText}))};})""" + "(" + json.dumps(selector) + ")")
                view.update(name=name, landing=landing)
                item["views"].append(view)
                cdp.screenshot(root / (name + ".png"))
                if landing:
                    prior.keyboard(cdp, "Tab", "Tab", 9)
                    view["next_tab"] = cdp.evaluate("(()=>{const e=document.activeElement;return {id:e.id,tag:e.tagName,href:e.getAttribute('href'),text:e.innerText}})()")
                    if selector == ".error-summary":
                        assert view["focus"]["tag"] == "SECTION"
                        assert view["next_tab"]["tag"] == "A"
                else:
                    node = cdp.call("Runtime.evaluate", expression="document.querySelector(" + json.dumps(selector) + ")")["result"]["objectId"]
                    view["accessibility"] = cdp.call("Accessibility.getPartialAXTree", objectId=node)
                    view["control_accessibility"] = []
                    for control in (UPLOAD + ' input[type="file"]', UPLOAD + ' select', UPLOAD + ' button'):
                        result = cdp.call("Runtime.evaluate", expression="document.querySelector(" + json.dumps(control) + ")")["result"]
                        if result.get("objectId") is not None:
                            view["control_accessibility"].append(dict(selector=control,
                                tree=cdp.call("Accessibility.getPartialAXTree", objectId=result["objectId"])))
                if after:
                    assert view["scrollWidth"] <= view["client"] + 1, view
                    assert all(r["right"] <= view["client"] + 1 for n in view["content"] for r in n["rects"]), view
                assert calls == before and requests == req
                return view

            def layouts(name):
                open_sources()
                for width, height in ((1365, 900), (390, 844), (320, 800)):
                    size(width, height)
                    measure(name + "-" + str(width))

            def native_downloads(label):
                retained = prior.downloads(client)
                for kind, (disposition, raw) in retained.items():
                    expected = prior.learning.build_unified_learning_download_v1(active, kind=kind)
                    assert raw == expected.content and disposition == f'attachment; filename="{expected.filename}"'
                    destination = root / (label + "-" + kind)
                    destination.mkdir()
                    cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
                    action(f'a[download][href="/learning/downloads/{kind.replace("_", "-")}.json"]', label + ": download " + kind, posts=0)
                    for _ in range(100):
                        saved = [p for p in destination.iterdir() if p.is_file() and not p.name.endswith(".crdownload")]
                        if saved:
                            break
                        time.sleep(.1)
                    assert len(saved) == 1 and saved[0].name == expected.filename and saved[0].read_bytes() == raw
                    status, headers, response = client.request("GET", "/learning/downloads/" + kind.replace("_", "-") + ".json")
                    assert status == 200 and response == raw
                    item["downloads"].append(dict(state=label, kind=kind, filename=expected.filename, headers=headers, bytes=len(raw), sha256=prior.digest(raw)))
                return retained

            def snapshot(label):
                state = prior.learning.build_unified_learning_state_v1(active)
                item["states"][label] = dict(state=state, catalog=active.corpus.store.document.content_fingerprint,
                    generation=active.corpus.generation, source_revision=active.corpus.strategy_source_store.revision,
                    source_fingerprints=[s.source_report_fingerprint for s in active.corpus.strategy_source_store.sources])

            def initialize():
                cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                cdp.call("Emulation.setScriptExecutionDisabled", value=not script)

            try:
                with ExitStack() as stack:
                    for module, name, key in (
                        (prior.session_files, "save_session_file", "session_saves"),
                        (prior.execution, "execute", "session_executions"),
                        (prior.match_context, "save_match_workspace_file_v1", "match_saves"),
                        (prior.match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                        (prior.match_state, "_decision_preparation_summary", "existing_match_preparation"),
                        (prior.profiles, "save_frontend_profile_file_v1", "profile_saves"),
                        (prior.managed, "discover_managed_items_v1", "managed_discovery"),
                        (prior.web, "discover_managed_items_v1", "server_discovery"),
                        (prior.direct, "discover_managed_items_v1", "add_source_revalidation"),
                        (prior.learning, "initialize_learning_corpus_web_v1", "collection_creations"),
                        (prior.learning, "import_match_workspace_into_learning_corpus_web_v1", "imports"),
                        (prior.learning, "prepare_learning_corpus_artifacts_web_v1", "preparations"),
                        (prior.learning, "select_current_learning_corpus_snapshot_web_v1", "selections"),
                        (prior.learning, "import_strategy_teacher_report_into_learning_corpus_web_v1", "report_imports"),
                        (prior.learning, "remove_strategy_teacher_report_from_learning_corpus_web_v1", "report_removals"),
                        (prior.learning, "reload_learning_corpus_web_v1", "reloads"),
                        (teacher, "build_match_decision_position_request_v1", "source_request_reconciliation"),
                        (prior.corpus_import, "save_learning_corpus_catalog_v1", "catalog_changes"),
                        (prior.corpus_import, "publish_learning_corpus_match_snapshot_object_v1", "object_publications")):
                        stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
                    for method in ("GET", "POST"):
                        stack.enter_context(patch.object(prior.Handler, "do_" + method, request_counter(method, getattr(prior.Handler, "do_" + method))))
                    stack.enter_context(patch.object(prior.Handler, "_learning_operation", multipart_observer(prior.Handler._learning_operation)))

                    def setup():
                        prior.record_score_review_game(client)
                        prior.follow(client, client.submit(prior.score_review_form(client)))
                        path, initial = prior.saved_partial_match(server)
                        workspace = _build_match_workspace_v1(match_definition=replace(initial.match_definition,
                            title="Synthetic equally named Match with a deliberately long descriptive title for attachment"),
                            revision=initial.revision, slots=initial.slots)
                        assert prior.navigation_fixtures.save_match_workspace_file_v1(path,
                            prior.build_match_workspace_persistence_document_v1(workspace),
                            expected_content_fingerprint=prior.build_match_workspace_persistence_document_v1(initial).content_fingerprint).status == "saved"
                        prior.follow(client, client.submit(prior.chooser_form(client.page("/review/recorded"), "matches")))
                        prior.follow(client, client.submit(prior.operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                        report = app.managed_stateful.active_match.capture.report_store.list()[0]
                        source = client.request("GET", f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")[2]
                        other_path, _ = save_other(path, workspace)
                        open_other(client, other_path)
                        prior.follow(client, client.submit(prior.operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                        other_report = app.managed_stateful.active_match.capture.report_store.list()[0]
                        other_source = client.request("GET", f"/matches/api/v1/reports/{other_report.report_id}/strategy-source.json")[2]
                        return path, workspace, other_path, report, source, other_source
                    path, workspace, other_path, source_report, source, other_source = operation("fixture: real Session SJ and two Match executions", setup)
                    session, match = app.managed_stateful.active_session, app.managed_stateful.active_match
                    execution, report = session.execution, match.capture.report_store.list()[0]
                    assert execution.request.document["actual_card_played"] == "SJ"
                    def unrelated():
                        return {"session": session.path.read_bytes(), "match": match.path.read_bytes(),
                            "result": client.request("GET", "/sessions/downloads/result.json")[2],
                            "report": client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2]}
                    original = unrelated()
                    source_path, other_source_path = root / "source.json", root / "other-source.json"
                    source_path.write_bytes(source)
                    other_source_path.write_bytes(other_source)
                    item["source_hashes"] = prior.hashes({**original, "source": source, "other_source": other_source, "workspace": path.read_bytes()})
                    item["source_report_id"] = source_report.report_id
                    local = prior.LocalBrowser(args.browser, root / "profile")
                    cdp = local.cdp
                    item["browser"] = local.version
                    initialize()
                    size(1365, 900)
                    cdp.navigate(server.origin + "/learning")
                    action(f'.language-selector button[value="{locale}"]', "initial-language")
                    prior.native_text(cdp, 'form[action="/learning/create"] [name="collection_name"]', "Synthetic optional attachment")
                    action('form[action="/learning/create"] button', "create")
                    active = app.managed_stateful.active_learning
                    layouts("zero")
                    assert cdp.evaluate("!!document.querySelector(" + json.dumps(UPLOAD) + ")") != after
                    prior.choose_source(cdp, prior.source_handle(path), item)
                    action(prior.ADD + ' > button', "add-first")
                    layouts("singleton")
                    expected_type = "hidden" if after else "select-one"
                    assert cdp.evaluate("document.querySelector(" + json.dumps(TARGET) + ").type") == expected_type
                    first = cdp.evaluate("document.querySelector(" + json.dumps(TARGET) + ").value")
                    operation("fixture: valid equal-revision metadata variant save", lambda: save_variant(path, workspace, 2))
                    cdp.navigate(server.origin + "/learning/current")
                    prior.choose_source(cdp, prior.source_handle(path), item)
                    action(prior.ADD + ' details > summary', "open-retain-policy", posts=0)
                    assert native_select(cdp, prior.ADD + ' [name="same_revision_resolution"]', down=1) == "retain"
                    action(prior.ADD + ' > button', "retain-variant")
                    second = active.entry_outcome.snapshot_id
                    layouts("retained-variants-one-current")
                    assert cdp.evaluate("document.querySelector(" + json.dumps(TARGET) + ").value") == first
                    supply_file(source_path)
                    action(f'.language-selector button[value="{"en" if locale == "de" else "de"}"]', "file-language-return")
                    open_sources()
                    assert cdp.evaluate("document.querySelector(" + json.dumps(UPLOAD + ' input[type="file"]') + ").files.length") == 0
                    measure("file-reselection-language")
                    action(f'.language-selector button[value="{locale}"]', "restore-language")
                    open_sources()
                    supply_file(source_path)
                    before = calls.copy()
                    action(UPLOAD + ' button', "attach-singleton", pointer=True)
                    assert calls - before == {"report_imports": 1, "source_request_reconciliation": 1}
                    assert active.corpus.prepared_artifacts is None
                    snapshot("attached-singleton")
                    action(prior.BUILD, "prepare-singleton")
                    snapshot("prepared-singleton")
                    measure("prepared-landing", selector="#learning-results", landing=True)
                    retained = native_downloads("prepared")
                    files = prior.saved_bytes(active.path)
                    prepared = active.corpus.prepared_artifacts
                    passive_before = calls.copy()
                    cdp.navigate(server.origin + "/learning/current")
                    for language in ("en" if locale == "de" else "de", locale):
                        action(f'.language-selector button[value="{language}"]', "passive-language")
                    open_sources()
                    supply_file(source_path)
                    action(UPLOAD + ' button', "exact-duplicate")
                    assert active.last_result.status == "unchanged" and active.corpus.prepared_artifacts is prepared
                    assert native_downloads("duplicate") == retained and prior.saved_bytes(active.path) == files
                    assert calls["preparations"] == passive_before["preparations"] and calls["match_executions"] == passive_before["match_executions"]
                    prior.choose_source(cdp, prior.source_handle(other_path), item)
                    action(prior.ADD + ' > button', "add-unrelated-match")
                    layouts("multiple")
                    wrong = next(s.match_snapshot_id for s in active.corpus.store.document.catalog.current_matches if s.match_snapshot_id != first)
                    action(prior.BUILD, "prepare-multiple")
                    prepared, retained = active.corpus.prepared_artifacts, prior.downloads(client)
                    open_sources()
                    choose_target(wrong)
                    supply_file(source_path)
                    action(UPLOAD + ' button', "mismatch")
                    measure("mismatch-landing", selector=".error-summary", landing=True)
                    assert active.corpus.prepared_artifacts is prepared and prior.downloads(client) == retained
                    assert cdp.evaluate("document.querySelector(" + json.dumps(TARGET) + ").value") == wrong
                    assert cdp.evaluate("document.querySelector(" + json.dumps(UPLOAD + ' input[type="file"]') + ").files.length") == 0
                    action(f'.language-selector button[value="{"en" if locale == "de" else "de"}"]', "error-language")
                    assert cdp.evaluate("document.querySelector(" + json.dumps(TARGET) + ").value") == wrong
                    action(f'.language-selector button[value="{locale}"]', "error-language-back")
                    layouts("mismatch-retry")
                    choose_target(first)
                    supply_file(source_path)
                    action(UPLOAD + ' button', "retry-exact-source")
                    assert active.last_result.status == "unchanged" and active.corpus.prepared_artifacts is prepared
                    open_sources()
                    choose_target(wrong)
                    supply_file(other_source_path)
                    action(UPLOAD + ' button', "attach-multiple", pointer=True)
                    assert len(active.corpus.strategy_source_store.sources) == 2 and active.corpus.prepared_artifacts is None
                    action(prior.BUILD, "prepare-two-sources")
                    snapshot("prepared-two-sources")
                    retained = native_downloads("two-sources")
                    # The next browser uses a real default-font preference, not injected CSS or zoom.
                    local.close()
                    profile = root / "font-profile"
                    (profile / "Default").mkdir(parents=True)
                    (profile / "Default/Preferences").write_text(json.dumps({"webkit": {"webprefs": {"default_font_size": 32}}}))
                    local = prior.LocalBrowser(args.browser, profile)
                    cdp = local.cdp
                    initialize()
                    size(320, 800)
                    cdp.navigate(server.origin + "/learning/current")
                    open_sources()
                    assert cdp.evaluate("getComputedStyle(document.body).fontSize") == "32px"
                    measure("multiple-text200")
                    if after:
                        selector = "document.querySelectorAll('#learning-sources h4,#learning-sources p,#learning-sources li')"
                        for index in range(cdp.evaluate(selector + ".length")):
                            cdp.evaluate(f"{selector}[{index}].scrollIntoView({{block:'start'}})")
                            cdp.screenshot(root / f"source-text200-{index}.png")
                            if cdp.evaluate(f"{selector}[{index}].getBoundingClientRect().height") > 700:
                                cdp.evaluate(f"{selector}[{index}].scrollIntoView({{block:'end'}})")
                                cdp.screenshot(root / f"source-text200-{index}-tail.png")
                    assert prior.downloads(client) == retained
                    action('#insight-versions details > summary', "open-current-alternative", posts=0)
                    action(f'form:has(input[value="select_current_snapshot"]):has(input[value="{second}"]) button', "change-current")
                    snapshot("non-current")
                    assert active.corpus.prepared_artifacts is None
                    measure("non-current-text200")
                    assert not cdp.evaluate("!!document.querySelector('#learning-build form > button')")
                    binding = next(s.source_binding_id for s in active.corpus.strategy_source_store.sources if s.match_snapshot_id == first)
                    action(f'form:has(input[value="remove_strategy_teacher_report"]):has(input[value="{binding}"]) button', "remove-non-current")
                    assert len(active.corpus.strategy_source_store.sources) == 1
                    open_sources()
                    measure("removed-text200")
                    action(prior.BUILD, "explicit-after-removal")
                    snapshot("after-removal")
                    open_sources()
                    action('form:has(input[value="reload_corpus"]) button', "same-context-reload")
                    assert len(active.corpus.strategy_source_store.sources) == 1 and active.corpus.prepared_artifacts is None
                    snapshot("reloaded")
                    operation("HTTP returned-form fresh context", lambda: prior.follow(client, client.submit(prior.Forms(client.page("/learning")).find("/learning/open"))))
                    active = app.managed_stateful.active_learning
                    assert active.corpus.strategy_source_store.sources == () and active.corpus.prepared_artifacts is None
                    snapshot("fresh-context")
                    assert session.execution is execution and match.capture.report_store.list() == (report,)
                    assert unrelated() == original
                    assert calls["match_executions"] == 2 and calls["session_executions"] == 1
                    assert calls["preparations"] == 4 and calls["report_imports"] == 5
                    for upload in item["uploads"]:
                        assert [p["name"] for p in upload["parts"]].count("match_snapshot_id") == 1
                        assert set(p["name"] for p in upload["parts"]) == {"managed_handle", "operation", "match_snapshot_id", "report_source_file"}
                    for asset, route in (("app.css", "/assets/app.css"), ("workflow.js", "/matches/assets/capture.js")):
                        status, _, raw = client.request("GET", route)
                        assert status == 200 and raw == (Path(prior.skatmind.__file__).parent / "app_web/assets" / asset).read_bytes()
                        item.setdefault("served", {})[asset] = prior.digest(raw)
                    kinds = [kind for _, group in GROUPS for kind in group]
                    item["download_groups"] = kinds
                    item["calls"], item["requests"] = dict(calls), dict(requests)
                    item["saved_sources"] = prior.hashes(prior.saved_bytes(active.path))
            finally:
                if local is not None:
                    local.close()
                fixture.close()
        for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
            run_one(locale, script)
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(completed=True, runs=len(evidence["runs"]), views=sum(len(r["views"]) for r in evidence["runs"]))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
