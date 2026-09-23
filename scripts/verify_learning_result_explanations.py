# ruff: noqa: E501 - Keep optional browser selectors and evidence records legible.
"""Independent #258 Wheel evidence with real synthetic preparation and native downloads."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import verify_learning_outcome_navigation as prior
from test_learning_result_explanations import CANONICAL, GROUPS

import skatmind.corpus_web.preparation as preparation


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(prior.skatmind.__file__).resolve().is_relative_to(prior.ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = dict(completed=False, phase=args.phase, python=prior.sys.version,
        package=prior.skatmind.__version__, installed_module=prior.skatmind.__file__,
        wheel=prior.hashes({"wheel": args.wheel.read_bytes()}),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=prior.ROOT, text=True).strip(),
        registry=[len(prior.UNIFIED_FRONTEND_POST_ROUTES), len(prior.FRONTEND_FORM_REGISTRY)],
        keys={k: len(v) for k, v in prior.load_frontend_translation_catalogs_v1().items()},
        hashes={}, runs=[], limits=[
            "Synthetic headless Edge, not screen-reader, physical-device, browser zoom or maintainer UAT.",
            "Real partial/no-Teacher and bound Immediate Teacher/Tactical preparations; no available-focus browser claim.",
            "Other statuses, malformed facts and bounded complete-Search focus fixtures are focused-test coverage."])
    assert evidence["registry"] == [67, 112]
    assert evidence["keys"] == {"de": 1786 if after else 1738, "en": 1786 if after else 1738}
    modules = (*prior.MODULES, "learning_outcome_navigation.py",
               *(("learning_result_rendering.py",) if after else ()))
    for name in modules:
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
            item = dict(locale=locale, javascript=script, operations=[], actions=[], views=[], downloads=[], states={})
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

            def action(selector, name, *, posts=1):
                def invoke():
                    before = sum(v for k, v in requests.items() if k.startswith("POST "))
                    cdp.activate(selector)
                    assert sum(v for k, v in requests.items() if k.startswith("POST ")) - before == posts
                operation(name, invoke)

            def size(width, height):
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

            def measure(name, *, landing=False, selector="#learning-results"):
                before, req = calls.copy(), requests.copy()
                if not landing:
                    cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'})")
                view = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),a=document.activeElement;
                    const rects=n=>{const r=document.createRange();r.selectNodeContents(n);return [...r.getClientRects()].map(x=>x.toJSON())};
                    return {url:location.pathname+location.hash,viewport:[innerWidth,innerHeight],
                        font:getComputedStyle(document.body).fontSize,client:document.documentElement.clientWidth,
                        scrollWidth:document.documentElement.scrollWidth,rect:e.getBoundingClientRect().toJSON(),text:e.innerText,
                        focus:{id:a.id,tag:a.tagName,name:a.name},
                        content:[...e.querySelectorAll('h2,h3,h4,p,a,summary,dt,dd')].filter(n=>n.checkVisibility()).map(n=>({
                            tag:n.tagName,text:n.innerText,font:getComputedStyle(n).fontSize,rects:rects(n)})),
                        links:[...e.querySelectorAll('a')].map(n=>({text:n.innerText,href:n.getAttribute('href'),visible:n.checkVisibility()})),
                        details:[...document.querySelectorAll('#task-first-learning details')].map(n=>({open:n.open,caption:n.querySelector('summary').innerText}))};})""" + "(" + json.dumps(selector) + ")")
                view.update(name=name, landing=landing)
                item["views"].append(view)
                cdp.screenshot(root / (name + ".png"))
                if landing:
                    assert view["focus"]["id"] == "learning-results" if selector == "#learning-results" else view["focus"]["tag"] == "SECTION"
                    assert -1 <= view["rect"]["y"] < view["viewport"][1]
                    prior.keyboard(cdp, "Tab", "Tab", 9)
                    view["next_tab"] = cdp.evaluate("(()=>{const e=document.activeElement;return {id:e.id,tag:e.tagName,text:e.innerText,href:e.getAttribute('href')}})()")
                if selector == "#learning-results":
                    kinds = [kind for _, group in GROUPS for kind in group] if after else CANONICAL
                    assert [link["href"] for link in view["links"]] == ["/learning/downloads/" + k.replace("_", "-") + ".json" for k in kinds]
                    assert all(link["visible"] for link in view["links"])
                    if after:
                        assert view["scrollWidth"] <= view["client"] + 1
                        assert all(r["right"] <= view["client"] + 1 for n in view["content"] for r in n["rects"])
                        assert all(float(n["font"].removesuffix("px")) >= float(view["font"].removesuffix("px")) for n in view["content"])
                    link = cdp.call("Runtime.evaluate", expression="document.querySelector('#learning-results a')")["result"]["objectId"]
                    view["first_link_accessibility"] = cdp.call("Accessibility.getPartialAXTree", objectId=link)
                assert calls == before and requests == req
                return view

            def native_downloads(label):
                retained = operation(label + ": compare retained HTTP bytes", lambda: prior.downloads(client))
                for kind, (disposition, raw) in retained.items():
                    expected = prior.learning.build_unified_learning_download_v1(active, kind=kind)
                    assert raw == expected.content and disposition == f'attachment; filename="{expected.filename}"'
                    status, headers, content = client.request("GET", "/learning/downloads/" + kind.replace("_", "-") + ".json")
                    assert status == 200 and content == raw
                    destination = root / (label + "-" + kind)
                    destination.mkdir()
                    cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
                    action(f'a[download][href="/learning/downloads/{kind.replace("_", "-")}.json"]', label + ": native " + kind, posts=0)
                    for _ in range(100):
                        saved = [p for p in destination.iterdir() if p.is_file() and not p.name.endswith(".crdownload")]
                        if saved:
                            break
                        time.sleep(.1)
                    assert len(saved) == 1 and saved[0].name == expected.filename and saved[0].read_bytes() == raw
                    item["downloads"].append(dict(state=label, kind=kind, filename=expected.filename, headers=headers, bytes=len(raw), sha256=prior.digest(raw)))
                return retained

            try:
                with ExitStack() as stack:
                    for module, name, label in (
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
                        (prior.corpus_import, "save_learning_corpus_catalog_v1", "catalog_changes"),
                        (prior.corpus_import, "publish_learning_corpus_match_snapshot_object_v1", "object_publications")):
                        stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
                    for name in ("build_learning_corpus_player_catalog_v1", "build_learning_corpus_human_evidence_collection_v1",
                        "build_learning_corpus_strategy_teacher_evidence_collection_v1", "build_learning_dataset_v2",
                        "prepare_learning_dataset_v2_partitions_v1", "build_learning_dataset_v2_cross_game_summary_v1",
                        "build_learning_corpus_tactical_motif_evidence_collection_v1", "build_learning_corpus_tactical_motif_cross_game_summary_v1",
                        "build_learning_corpus_tactical_cross_game_coaching_report_v1"):
                        stack.enter_context(patch.object(preparation, name, counted(name, getattr(preparation, name))))
                    for method in ("GET", "POST"):
                        stack.enter_context(patch.object(prior.Handler, "do_" + method, request_counter(method, getattr(prior.Handler, "do_" + method))))

                    def setup():
                        prior.record_score_review_game(client)
                        prior.follow(client, client.submit(prior.score_review_form(client)))
                        path, workspace = prior.saved_partial_match(server)
                        prior.follow(client, client.submit(prior.chooser_form(client.page("/review/recorded"), "matches")))
                        prior.follow(client, client.submit(prior.operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                        source_report = app.managed_stateful.active_match.capture.report_store.list()[0]
                        source = client.request("GET", f"/matches/api/v1/reports/{source_report.report_id}/strategy-source.json")[2]
                        other_path = path.with_name("unrelated.json")
                        other = prior.independent_workspace(workspace, "unrelated-match")
                        assert prior.navigation_fixtures.save_match_workspace_file_v1(other_path,
                            prior.build_match_workspace_persistence_document_v1(other), expected_content_fingerprint=None).status == "saved"
                        form = next(f for f in prior.Forms(client.page("/review/recorded")).forms
                            if f["action"] == "/review/open-recording" and f["values"]["handle"] == prior.source_handle(other_path))
                        prior.follow(client, client.submit(form))
                        prior.follow(client, client.submit(prior.operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                        return path, workspace, source
                    path, workspace, source = operation("fixture: genuine Session SJ and two independent partial Match analyses", setup)
                    session, match = app.managed_stateful.active_session, app.managed_stateful.active_match
                    execution, report = session.execution, match.capture.report_store.list()[0]
                    assert execution.request.document["actual_card_played"] == "SJ" and report.value.status == "executed"
                    def unrelated():
                        return {"session": session.path.read_bytes(), "match": match.path.read_bytes(),
                            "result": client.request("GET", "/sessions/downloads/result.json")[2],
                            "report": client.request("GET", f"/matches/api/v1/reports/{report.report_id}.json")[2]}
                    original = unrelated()
                    source_path = root / "teacher.json"
                    source_path.write_bytes(source)
                    item["source_hashes"] = prior.hashes({**original, "teacher": source,
                                                        "learning_input": path.read_bytes()})
                    local = prior.LocalBrowser(args.browser, root / "profile")
                    cdp = local.cdp
                    item["browser"] = local.version
                    def initialize():
                        cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                    initialize()
                    size(1365, 900)
                    cdp.navigate(server.origin + "/learning")
                    action(f'.language-selector button[value="{locale}"]', "initial-language")
                    prior.native_text(cdp, 'form[action="/learning/create"] [name="collection_name"]', "Synthetic result collection")
                    action('form[action="/learning/create"] button', "create")
                    active = app.managed_stateful.active_learning
                    prior.choose_source(cdp, prior.source_handle(path), item)
                    action(prior.ADD + ' > button', "add")
                    action(prior.BUILD, "prepare-no-teacher")
                    measure("no-teacher-native-landing", landing=True)
                    item["states"]["no_teacher"] = prior.learning.build_unified_learning_state_v1(active)["prepared"]
                    retained = native_downloads("no-teacher")
                    for width, height in ((390, 844), (320, 800)):
                        size(width, height)
                        measure("no-teacher-" + str(width))
                    action('#task-first-learning > details.advanced-settings > summary', "open-report-controls", posts=0)
                    upload = 'form:has(input[value="import_strategy_teacher_report"])'
                    doc = cdp.call("DOM.getDocument")["root"]["nodeId"]
                    node = cdp.call("DOM.querySelector", nodeId=doc, selector=upload + ' input[type="file"]')["nodeId"]
                    cdp.call("DOM.setFileInputFiles", nodeId=node, files=[str(source_path.resolve())])
                    action(upload + ' button', "attach-exact-teacher")
                    assert active.corpus.prepared_artifacts is None
                    action(prior.BUILD, "prepare-teacher")
                    measure("teacher-native-landing", landing=True)
                    state = prior.learning.build_unified_learning_state_v1(active)["prepared"]
                    item["states"]["teacher"] = state
                    assert state["strategy_teacher_evidence_count"] == 1 and state["tactical_evidence_count"] == 2
                    assert state["tactical_coaching_status"] == "insufficient_evidence"
                    assert state["known_player"]["status"] == state["unseen_player"]["status"] == "unavailable"
                    retained = native_downloads("teacher")
                    for width, height in ((1365, 900), (390, 844), (320, 800)):
                        size(width, height)
                        measure("teacher-" + str(width))
                    action('#learning-build details > summary', "open-settings", posts=0)
                    prior.native_text(cdp, '#learning-build [name="train_weight"]', "0")
                    action(prior.BUILD, "failed-recreation")
                    measure("failed-recreation-error", landing=True, selector=".error-summary")
                    measure("older-retained-result")
                    assert prior.downloads(client) == retained
                    files = prior.saved_bytes(active.path)
                    artifacts = (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts)
                    before_preparations = calls["preparations"]
                    def passive():
                        cdp.navigate(server.origin + "/learning/current")
                        other = "en" if locale == "de" else "de"
                        for language in (other, locale):
                            action(f'.language-selector button[value="{language}"]', "passive-language")
                        action('#task-first-learning > details.technical-details > summary', "open-technical", posts=0)
                        measure("technical-details", selector="#task-first-learning > details.technical-details")
                        action('#task-first-learning > details.technical-details > summary', "close-technical", posts=0)
                        prior.choose_source(cdp, prior.source_handle(path), item)
                        action(prior.ADD + ' > button', "identical-add")
                        assert active.last_result.status == "unchanged"
                    operation("passive views and identical Add", passive)
                    assert calls["preparations"] == before_preparations
                    assert prior.saved_bytes(active.path) == files and prior.downloads(client) == retained
                    assert all(old is new for old, new in zip(artifacts, (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts), strict=True))
                    for asset, route in (("app.css", "/assets/app.css"),
                                         ("workflow.js", "/matches/assets/capture.js")):
                        status, _, raw = client.request("GET", route)
                        assert status == 200
                        assert raw == (Path(prior.skatmind.__file__).parent / "app_web/assets" / asset).read_bytes()
                        item.setdefault("served", {})[asset] = prior.digest(raw)
                    local.close()
                    profile = root / "font-profile"
                    (profile / "Default").mkdir(parents=True)
                    (profile / "Default/Preferences").write_text(json.dumps({"webkit": {"webprefs": {"default_font_size": 32}}}))
                    local = prior.LocalBrowser(args.browser, profile)
                    cdp = local.cdp
                    initialize()
                    size(320, 800)
                    cdp.navigate(server.origin + "/learning/current")
                    assert cdp.evaluate("getComputedStyle(document.body).fontSize") == "32px"
                    measure("teacher-text200")
                    # Read every source/coverage/status sentence, including long paragraph tails.
                    paragraphs = cdp.evaluate("[...document.querySelectorAll('#learning-results > section > p')].map((n,i)=>({i,height:n.getBoundingClientRect().height}))")
                    for row in paragraphs:
                        selector = f"document.querySelectorAll('#learning-results > section > p')[{row['i']}]"
                        cdp.evaluate(selector + ".scrollIntoView({block:'start'})")
                        cdp.screenshot(root / f"text200-prose-{row['i']}.png")
                        if row["height"] > 700:
                            cdp.evaluate(selector + ".scrollIntoView({block:'end'})")
                            cdp.screenshot(root / f"text200-prose-{row['i']}-tail.png")
                    for index in range(10):
                        cdp.evaluate(f"document.querySelectorAll('#learning-results li')[{index}].scrollIntoView({{block:'start'}})")
                        cdp.screenshot(root / f"text200-download-{index}.png")
                        cdp.evaluate(f"document.querySelectorAll('#learning-results li')[{index}].scrollIntoView({{block:'end'}})")
                        cdp.screenshot(root / f"text200-download-{index}-tail.png")
                    assert prior.downloads(client) == retained and prior.saved_bytes(active.path) == files
                    # Remove the exact Teacher before changing Current, then regenerate explicitly.
                    action('#task-first-learning > details.advanced-settings > summary', "open-report-controls-again", posts=0)
                    action('form:has(input[value="remove_strategy_teacher_report"]) button', "remove-teacher")
                    assert active.corpus.prepared_artifacts is None
                    operation("fixture: external later saved revision", lambda: prior.external_pass(path, workspace))
                    cdp.navigate(server.origin + "/learning/current")
                    prior.choose_source(cdp, prior.source_handle(path), item)
                    action(prior.ADD + ' > button', "later-version-add")
                    action('#insight-versions details > summary', "open-alternatives", posts=0)
                    action('form:has(input[value="select_current_snapshot"]) button', "select-later")
                    assert active.corpus.prepared_artifacts is None
                    action(prior.BUILD, "regenerate-later")
                    measure("regenerated-native-landing", landing=True)
                    regenerated = prior.downloads(client)
                    files = prior.saved_bytes(active.path)
                    item["saved_sources"] = prior.hashes(files)
                    page = client.page("/learning")
                    operation("strict reopen actual returned HTTP form", lambda: prior.follow(client, client.submit(prior.Forms(page).find("/learning/open"))))
                    active = app.managed_stateful.active_learning
                    assert active.corpus.prepared_artifacts is None
                    assert client.request("GET", "/learning/downloads/cross-game-summary.json")[0] == 404
                    cdp.navigate(server.origin + "/learning/current")
                    action(prior.BUILD, "regenerate-reopened")
                    measure("reopened-native-landing", landing=True)
                    assert prior.downloads(client) == regenerated and prior.saved_bytes(active.path) == files
                    assert session.execution is execution and match.capture.report_store.list() == (report,)
                    assert unrelated() == original
                    item["calls"], item["requests"] = dict(calls), dict(requests)
                    assert calls["preparations"] == 4 and calls["imports"] == 3 and calls["selections"] == 1
            finally:
                if local is not None:
                    local.close()
                fixture.close()
        for locale, script in (("de", False), ("en", True), ("de", True), ("en", False)):
            run_one(locale, script)
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(completed=True, runs=len(evidence["runs"]), views=sum(len(r["views"]) for r in evidence["runs"])) ))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
