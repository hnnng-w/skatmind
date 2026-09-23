# ruff: noqa: E501 - Keep optional native evidence selectors legible.
"""Bounded #257 installed-Wheel evidence. Reuses #256's harness and real fixtures."""
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
from test_learning_version_selection_web import save_variant
from verify_local_time_entry import native_select

SELECT = 'form:has(input[value="select_current_snapshot"])'
MODULES = (*prior.MODULES, "learning_outcome_navigation.py", "validation_rendering.py")


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
            "Headless Edge; not browser zoom, screen-reader, physical-device or maintainer UAT.",
            "Current HEAD has per-alternative buttons, not a version dropdown; that domain is preserved.",
            "Inspection scrolls are separate from untouched native landing/focus measurements.",
            "Valid equal-revision source construction and external writes are identified fixture work."])
    assert evidence["registry"] == [67, 112]
    assert evidence["keys"] == {"de": 1738 if after else 1735, "en": 1738 if after else 1735}
    for name in MODULES:
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
                item = dict(locale=locale, javascript=script, operations=[], actions=[], views=[], downloads=[])
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
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)

                def action(selector, name, *, pointer=False, posts=1):
                    def invoke():
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
                            url=e["params"]["request"]["url"], payload=e["params"]["request"].get("postData"),
                            redirect=e["params"].get("redirectResponse")) for e in cdp.events]
                        assert sum(e["method"] == "POST" for e in sequence) == posts, (name, sequence)
                        item["actions"].append(dict(name=name, pointer=pointer, sequence=sequence,
                                                   location=cdp.evaluate("location.pathname+location.hash")))
                    operation(name, invoke)

                def measure(name, selector, *, landing=False, error=False):
                    # Landing measurements never move focus/scroll to the destination.
                    if not landing:
                        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'})")
                    result = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),a=document.activeElement;
                        const textRects=n=>{const range=document.createRange();range.selectNodeContents(n);return [...range.getClientRects()].map(r=>r.toJSON())};
                        return {url:location.pathname+location.hash,viewport:[innerWidth,innerHeight],
                            bodyFont:getComputedStyle(document.body).fontSize,client:document.documentElement.clientWidth,
                            scrollWidth:document.documentElement.scrollWidth,rect:e.getBoundingClientRect().toJSON(),text:e.innerText,
                            focus:{id:a.id,tag:a.tagName,name:a.name},
                            content:[...e.querySelectorAll('h3,h4,p,button,summary,label')].filter(n=>n.checkVisibility()).map(n=>({
                                tag:n.tagName,text:n.innerText,rect:n.getBoundingClientRect().toJSON(),textRects:textRects(n),
                                labelledby:n.getAttribute('aria-labelledby'),describedby:n.getAttribute('aria-describedby')})),
                            choices:[...e.querySelectorAll('select')].map(n=>({name:n.name,value:n.value,description:
                                document.getElementById(n.getAttribute('aria-describedby'))?.innerText,
                                options:[...n.options].map(o=>({value:o.value,text:o.text,selected:o.selected}))})),
                            forms:[...e.querySelectorAll('form')].map(f=>({action:f.action,fields:[...new FormData(f).entries()]})),
                            disclosures:[...e.querySelectorAll('details')].map(n=>({open:n.open,text:n.innerText}))};})""" + "(" + json.dumps(selector) + ")")
                    result.update(name=name, landing=landing)
                    item["views"].append(result)
                    cdp.screenshot(root / (name + ".png"))
                    if landing:
                        prior.keyboard(cdp, "Tab", "Tab", 9)
                        result["next_tab"] = cdp.evaluate("(()=>{const e=document.activeElement;return {id:e.id,tag:e.tagName,name:e.name,text:e.innerText}})()")
                        assert result["focus"]["id"] == selector[1:] if not error else result["focus"]["tag"] == "SECTION"
                        assert -1 <= result["rect"]["y"] < result["viewport"][1]
                    if after:
                        assert result["scrollWidth"] <= result["client"] + 1, result
                        if name in {"variant-choice-text200", "full-policy-description-text200"}:
                            assert result["rect"]["width"] >= 190, result
                        # Actual wrapped captions/descriptions, not merely document width.
                        for row in result["content"]:
                            if row["tag"] in {"H3", "H4", "P", "BUTTON", "SUMMARY"}:
                                assert all(r["right"] <= result["client"] + 1 for r in row["textRects"]), row
                    return result

                def choose(source):
                    before, req = calls.copy(), requests.copy()
                    prior.choose_source(cdp, prior.source_handle(source), item)
                    assert calls == before and requests == req

                def open_versions(snapshot_id):
                    selector = SELECT + ':has(input[value="' + snapshot_id + '"])'
                    summaries = cdp.evaluate("(()=>{const f=document.querySelector(" + json.dumps(selector) + ");return [...document.querySelectorAll('#insight-versions details')].map((d,i)=>({i,open:d.open,contains:d.contains(f)})).filter(d=>d.contains&&!d.open).map(d=>d.i)})()")
                    for index in summaries:
                        before, req = calls.copy(), requests.copy()
                        action(f'#insight-versions details:nth-of-type({index+1}) > summary' if not after else
                               '#' + prior.target(active, workspace.match_definition.match_id) + ' details > summary',
                               "open-versions", posts=0)
                        assert calls == before and requests == req
                    return selector

                def select(snapshot_id, name, pointer=False):
                    selector = open_versions(snapshot_id)
                    before = calls["preparations"]
                    action(selector + ' button', name, pointer=pointer)
                    assert cdp.evaluate("location.pathname+location.hash") == "/learning/current"
                    assert active.corpus.store.document.catalog.current_matches[0].match_snapshot_id == snapshot_id
                    assert active.corpus.prepared_artifacts is None and calls["preparations"] == before

                def inspect_variant(snapshot_id, name):
                    identity = "learning-version-" + prior.digest(
                        f"learning-version-v1:{active.handle}:{snapshot_id}".encode())
                    view = measure(name, "#" + identity)
                    if after:
                        button = cdp.call("Runtime.evaluate", expression="document.querySelector(" +
                            json.dumps("#" + identity + "-action") + ")")["result"]["objectId"]
                        view["accessibility"] = cdp.call("Accessibility.getPartialAXTree", objectId=button)
                        names = [n.get("name", {}).get("value", "") for n in view["accessibility"]["nodes"]
                                 if n.get("role", {}).get("value") == "button"]
                        assert len(names) == 1 and ("variant" if locale == "en" else "Variante") in names[0]

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
                        for method in ("GET", "POST"):
                            stack.enter_context(patch.object(prior.Handler, "do_" + method,
                                request_counter(method, getattr(prior.Handler, "do_" + method))))

                        def setup():
                            prior.record_score_review_game(client)
                            prior.follow(client, client.submit(prior.score_review_form(client)))
                            path, workspace = prior.saved_partial_match(server)
                            prior.follow(client, client.submit(prior.chooser_form(client.page("/review/recorded"), "matches")))
                            prior.follow(client, client.submit(prior.operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                            report = app.managed_stateful.active_match.capture.report_store.list()[0]
                            source = client.request("GET", f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")[2]
                            other = prior.independent_workspace(workspace, "zz-equal-title")
                            other_path = path.with_name("other.json")
                            assert prior.navigation_fixtures.save_match_workspace_file_v1(other_path,
                                prior.build_match_workspace_persistence_document_v1(other), expected_content_fingerprint=None).status == "saved"
                            form = next(f for f in prior.Forms(client.page("/review/recorded")).forms
                                if f["action"] == "/review/open-recording" and f["values"]["handle"] == prior.source_handle(other_path))
                            prior.follow(client, client.submit(form))
                            prior.follow(client, client.submit(prior.operation_form(client.page("/matches/position/3"), "analyze_decision"), immediate_sample_count="2"))
                            return path, workspace, other_path, source
                        path, workspace, other_path, source = operation("fixture: real Session SJ and two Match Reports; two equal-title partial sources", setup)
                        session, match = app.managed_stateful.active_session, app.managed_stateful.active_match
                        execution, report = session.execution, match.capture.report_store.list()[0]
                        assert execution.request.document["actual_card_played"] == "SJ" and report.value.status == "executed"
                        report_route = f"/matches/api/v1/reports/{report.report_id}.json"
                        def unrelated():
                            return {"session_file": session.path.read_bytes(), "match_file": match.path.read_bytes(),
                                "session_result": client.request("GET", "/sessions/downloads/result.json")[2],
                                "match_report": client.request("GET", report_route)[2]}
                        saved_unrelated = unrelated()
                        item["unrelated"] = prior.hashes(saved_unrelated)
                        item["fixture_sources"] = prior.hashes({"match": path.read_bytes(), "other_match": other_path.read_bytes(), "teacher": source})
                        local = prior.LocalBrowser(args.browser, root / "browser-profile")
                        cdp = local.cdp
                        item["browser"] = local.version
                        def initialize_browser():
                            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
                            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                        initialize_browser()
                        size(1365, 900)
                        cdp.navigate(server.origin + "/learning")
                        action(f'.language-selector button[value="{locale}"]', "initial-language")
                        prior.native_text(cdp, 'form[action="/learning/create"] [name="collection_name"]', 'Synthetic version collection')
                        action('form[action="/learning/create"] button', "create", pointer=True)
                        active = app.managed_stateful.active_learning
                        choose(path)
                        action(prior.ADD + ' > button', "first-add", pointer=True)
                        target = '#' + prior.target(active, workspace.match_definition.match_id)
                        measure("singleton-landing", target, landing=True)
                        view = measure("singleton-versions", "#insight-versions")
                        assert len(view["forms"]) == 0
                        assert len(view["disclosures"]) == (0 if after else 1)
                        first = active.entry_outcome.snapshot_id
                        action(prior.BUILD, "prepare-first")
                        measure("first-results", "#learning-results", landing=True)
                        retained, prepared, files = prior.downloads(client), active.corpus.prepared_artifacts, prior.saved_bytes(active.path)
                        size(390, 844)
                        choose(path)
                        action(prior.ADD + ' > button', "identical-add")
                        measure("identical-landing", target, landing=True)
                        assert active.last_result.status == "unchanged" and active.corpus.prepared_artifacts is prepared
                        assert prior.downloads(client) == retained and prior.saved_bytes(active.path) == files
                        choose(other_path)
                        action(prior.ADD + ' > button', "equal-title-other-match")
                        measure("other-match-landing", '#' + prior.target(active, match.workspace.match_definition.match_id), landing=True)
                        operation("fixture: exact Teacher binding", lambda: prior.learning.import_report_source_bytes_into_unified_learning_v1(active, source, match_snapshot_id=first))
                        revised = operation("fixture: external later revision", lambda: prior.external_pass(path, workspace))
                        size(320, 800)
                        cdp.navigate(server.origin + "/learning/current")
                        choose(path)
                        action(prior.ADD + ' > button', "later-add-keep-current")
                        measure("later-landing", target, landing=True)
                        later = active.entry_outcome.snapshot_id
                        assert active.corpus.store.document.catalog.current_matches[0].match_snapshot_id == first
                        open_versions(later)
                        measure("multiple-revisions", "#insight-versions")
                        select(later, "select-later", pointer=True)
                        assert cdp.evaluate("document.querySelector('#learning-build form')===null")
                        measure("teacher-mismatch", "#learning-sources")
                        select(first, "restore-older-binding")
                        action('#task-first-learning > details.advanced-settings > summary', "open-source-controls", posts=0)
                        action('form:has(input[value="remove_strategy_teacher_report"]) button', "remove-teacher")
                        operation("fixture: same-revision equal-title equal-progress external variant", lambda: save_variant(path, revised, 2))
                        cdp.navigate(server.origin + "/learning/current")
                        choose(path)
                        before = prior.saved_bytes(active.path)
                        action(prior.ADD + ' > button', "reject-conflicting-version")
                        measure("conflict-error", ".error-summary", landing=True, error=True)
                        assert active.last_result.status == "resolution_required" and prior.saved_bytes(active.path) == before
                        other_locale = "en" if locale == "de" else "de"
                        action(f'.language-selector button[value="{other_locale}"]', "error-language")
                        assert cdp.evaluate("document.querySelector('" + prior.ADD + " [name=source_handle]').value") == prior.source_handle(path)
                        action(f'.language-selector button[value="{locale}"]', "restore-error-language")
                        measure("conflict-policy", prior.ADD)
                        before_calls, before_requests = calls.copy(), requests.copy()
                        assert native_select(cdp, prior.ADD + ' [name="same_revision_resolution"]', down=1) == "retain"
                        assert calls == before_calls and requests == before_requests
                        action(f'.language-selector button[value="{other_locale}"]', "unsent-policy-language")
                        assert cdp.evaluate("document.querySelector('" + prior.ADD + " [name=same_revision_resolution]').value") == ("retain" if script else "reject")
                        action(f'.language-selector button[value="{locale}"]', "restore-unsent-policy-language")
                        if not script:
                            assert native_select(cdp, prior.ADD + ' [name="same_revision_resolution"]', down=1) == "retain"
                        action(prior.ADD + ' > button', "retain-conflicting-version", pointer=True)
                        measure("retained-landing", target, landing=True)
                        variant = active.entry_outcome.snapshot_id
                        assert active.corpus.store.document.catalog.current_matches[0].match_snapshot_id == first
                        open_versions(variant)
                        variants = measure("equal-revision-variants", "#insight-versions")
                        if after:
                            assert ("variant 1" if locale == "en" else "Variante 1") in variants["text"]
                            assert ("variant 2" if locale == "en" else "Variante 2") in variants["text"]
                        item["snapshot_mapping"] = prior.learning.build_unified_learning_state_v1(active)["matches"]
                        inspect_variant(variant, "variant-choice-320")
                        select(variant, "select-variant", pointer=True)
                        action(prior.BUILD, "prepare-variant")
                        select(later, "select-other-variant")
                        action(prior.BUILD, "prepare-other-variant")
                        retained = prior.downloads(client)
                        item["exports"] = {kind: {"filename": filename, **prior.hashes({kind: raw})[kind]} for kind, (filename, raw) in retained.items()}
                        for kind, (_filename, raw) in retained.items():
                            destination = root / ("download-" + kind)
                            destination.mkdir()
                            cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
                            action(f'a[download][href="/learning/downloads/{kind.replace("_", "-")}.json"]', "download-" + kind, posts=0, pointer=True)
                            for _ in range(100):
                                saved = [p for p in destination.iterdir() if p.is_file() and not p.name.endswith(".crdownload")]
                                if saved:
                                    break
                                time.sleep(.1)
                            assert len(saved) == 1 and saved[0].read_bytes() == raw
                            item["downloads"].append(dict(kind=kind, bytes=len(raw), sha256=prior.digest(raw)))
                        files = prior.saved_bytes(active.path)
                        item["saved_sources"] = prior.hashes(files)
                        artifacts = (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts)
                        def passive():
                            for route in ("/", "/learning", "/learning/current"):
                                cdp.navigate(server.origin + route)
                            for language in (other_locale, locale):
                                action(f'.language-selector button[value="{language}"]', "passive-language-" + language)
                            choose(path)
                            action(prior.ADD + ' > button', "passive-identical-add")
                            assert active.last_result.status == "unchanged"
                            assert prior.saved_bytes(active.path) == files and prior.downloads(client) == retained
                            assert all(a is b for a, b in zip(artifacts, (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts), strict=True))
                        operation("passive navigation language and identical Add", passive)
                        local.close()
                        font_profile = root / "font-profile"
                        (font_profile / "Default").mkdir(parents=True)
                        (font_profile / "Default/Preferences").write_text(json.dumps({"webkit": {"webprefs": {"default_font_size": 32}}}))
                        local = prior.LocalBrowser(args.browser, font_profile)
                        cdp = local.cdp
                        initialize_browser()
                        size(320, 800)
                        cdp.navigate(server.origin + "/learning/current")
                        assert cdp.evaluate("getComputedStyle(document.body).fontSize") == "32px"
                        open_versions(variant)
                        measure("variants-text200", "#insight-versions")
                        inspect_variant(variant, "variant-choice-text200")
                        action(prior.ADD + ' details > summary', "open-policy-text200", posts=0)
                        measure("policy-text200", prior.ADD)
                        if after:
                            measure("full-policy-description-text200", "#learning-add-conflict-help")
                        assert prior.downloads(client) == retained and prior.saved_bytes(active.path) == files
                        loaded = prior.load_learning_corpus_directory_v1(active.path)
                        page = client.page("/learning")
                        form = prior.Forms(page).find("/learning/open")
                        operation("strict reopen via actual HTTP form", lambda: prior.follow(client, client.submit(form)))
                        reopened = app.managed_stateful.active_learning
                        assert reopened is not active and reopened.corpus.store.document == loaded.document
                        assert reopened.corpus.prepared_artifacts is None
                        cdp.navigate(server.origin + "/learning/current")
                        action(prior.BUILD, "regenerate-reopened")
                        measure("reopened-results", "#learning-results", landing=True)
                        assert prior.downloads(client) == retained
                        assert session.execution is execution and match.capture.report_store.list() == (report,)
                        assert unrelated() == saved_unrelated
                        item["calls"], item["requests"] = dict(calls), dict(requests)
                        assert {k: calls[k] for k in ("collection_creations", "imports", "selections", "preparations", "catalog_changes", "object_publications")} == dict(
                            collection_creations=1, imports=7, selections=4, preparations=4, catalog_changes=8, object_publications=4)
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
    print(json.dumps({"completed": True, "runs": len(evidence["runs"]), "views": sum(len(r["views"]) for r in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
