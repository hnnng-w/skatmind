# ruff: noqa: E501 - Keep native selectors and evidence records legible.
"""Optional #269/#271 independent-Wheel evidence using the dependency-free browser."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
from importlib.metadata import metadata, version
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl
from zipfile import ZipFile

from _workflow_visual_browser import LocalBrowser
from verify_learning_direct_entry import ADD, BUILD, digest
from verify_learning_entry_purpose import MODULES, hashes
from verify_recording_deletion import focus, keyboard, submit, tab_to

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
from test_recorded_review_navigation import external_pass, saved_partial_match  # noqa: E402
from test_session_recorded_review_web import Browser  # noqa: E402

import skatmind  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profiles  # noqa: E402
import skatmind.app_web.learning_direct_entry as direct  # noqa: E402
import skatmind.app_web.learning_frontend as learning  # noqa: E402
import skatmind.app_web.server as web  # noqa: E402
import skatmind.app_web.stateful_context as managed  # noqa: E402
import skatmind.learning_corpus_import as corpus_import  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1  # noqa: E402
from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS  # noqa: E402
from skatmind.match_workspace_contracts import _build_match_workspace_v1  # noqa: E402
from skatmind.match_workspace_persistence import save_match_workspace_file_v1  # noqa: E402
from skatmind.match_workspace_persistence_codec import (  # noqa: E402
    build_match_workspace_persistence_document_v1,
)

SOURCE = "#learning-recorded-matches"
REFRESH = 'a[href="/learning/recorded-matches/refresh"]'


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    catalogs = load_frontend_translation_catalogs_v1()  # Exact key/order/placeholder checks.
    assert [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)] == [67, 119]
    assert {k: len(v) for k, v in catalogs.items()} == {"de": 1811, "en": 1811}
    package = metadata("skatmind")
    assert (package["Version"], package["Requires-Python"], package["License-Expression"]) == (
        "0.17.0", ">=3.13", "AGPL-3.0-only")
    assert "tzdata>=2026.4" in package.get_all("Requires-Dist")
    evidence = dict(completed=False, phase=args.phase, python=sys.version, platform=platform.platform(),
        captions=args.captions,
        installed_module=skatmind.__file__, wheel=hashes({"wheel": args.wheel.read_bytes()}),
        head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        registry=[67, 119], catalog_keys={k: len(v) for k, v in catalogs.items()},
        versions={k: version(k) for k in ("skatmind", "pytest", "jsonschema", "referencing", "tzdata")},
        dependencies=package.get_all("Requires-Dist"), hashes={}, runs=[],
        limits=["Synthetic headless Edge; no device, screen-reader or maintainer UAT claim.",
                "Doubled computed text is not browser zoom; authenticated HTTP bytes are not Save-dialog testing.",
                "Only bootstrap sets a URL; subsequent navigation uses actual controls and native browser Back."])
    with ZipFile(args.wheel) as wheel:
        for name in (*MODULES, "task_first_rendering.py", "validation_rendering.py", "card_entry_http.py", "card_form.py", "compact_card_rendering.py"):
            raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
            assert raw == wheel.read("skatmind/app_web/" + name)
            expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if args.phase == "after"
                        else subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
            assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
            evidence["hashes"][name] = digest(raw)
    try:
        for locale in ("de", "en"):
            for javascript in (False, True):
                run_one(args, evidence, locale, javascript)
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print("Evidence completed:", evidence["completed"], flush=True)


def run_one(args, evidence, locale, javascript):
    root = args.output / (locale + ("-js" if javascript else "-native"))
    root.mkdir()
    fixture = localized_server.__wrapped__(root)
    server = next(fixture)
    local = None
    calls, requests, responses = Counter(), Counter(), []
    item = dict(locale=locale, javascript=javascript, actions=[], operations=[], measurements=[], operation_counts=calls)
    evidence["runs"].append(item)

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapped

    def response(handler, status, *a, **kw):
        route = handler.path.split("?", 1)[0]
        requests[handler.command + " " + route] += 1
        responses.append(dict(method=handler.command, path=route, status=int(status)))
        return original_response(handler, status, *a, **kw)

    def operation(name, function):
        before, req, start = calls.copy(), requests.copy(), len(responses)
        value = function()
        item["operations"].append(dict(name=name, calls=dict(calls-before), requests=dict(requests-req), responses=responses[start:]))
        return value

    def action(selector, name, posts=1):
        operation(name, lambda: submit(cdp, selector, item, name, expected_posts=posts))
        if args.captions:
            item["operations"][-1]["payloads"] = [dict(path=e["params"]["request"]["url"],
                fields=parse_qsl(e["params"]["request"].get("postData", ""), keep_blank_values=True))
                for e in cdp.events if e["params"]["request"]["method"] == "POST"]

    def back(name):
        def invoke():
            for kind in ("mousePressed", "mouseReleased"):
                cdp.call("Input.dispatchMouseEvent", type=kind, x=20, y=20, button="back", clickCount=1)
            time.sleep(.7)
            item["actions"].append(dict(name=name, path=cdp.evaluate("location.pathname+location.hash"), focus=focus(cdp)))
        operation(name, invoke)

    def choose(path, *, pointer=False):
        def invoke():
            selector = ADD + ' [name="source_handle"]'
            tab_to(cdp, selector)
            index = cdp.evaluate(f"[...document.querySelector('{selector}').options].findIndex(o=>o.value==={json.dumps(source_handle(path))})")
            assert index > 0
            if pointer:
                # Focus was reached through Tab, not assigned with script.
                time.sleep(.3)
                point = cdp.evaluate(f"(()=>{{const r=document.querySelector('{selector}').getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
                for kind in ("mousePressed", "mouseReleased"):
                    cdp.call("Input.dispatchMouseEvent", type=kind, **point, button="left", clickCount=1)
                time.sleep(.3)
                cdp.screenshot(root / "native-popup-attempt.png")
                item["popup_observation"] = "Native pointer opening attempted; Page.captureScreenshot may omit the OS popup. Inspect pixels; do not infer popup geometry from the select DOM."
            keyboard(cdp, "Home", "Home", 36)
            for _ in range(index):
                keyboard(cdp, "ArrowDown", "ArrowDown", 40)
            if pointer:
                keyboard(cdp, "Enter", "Enter", 13, "\r")
            assert cdp.evaluate(f"document.querySelector('{selector}').value") == source_handle(path)
            chosen = cdp.evaluate(f"(()=>{{const s=document.querySelector('{selector}');return {{value:s.value,index:s.selectedIndex,caption:s.selectedOptions[0].text,rows:[...document.querySelectorAll('#learning-recorded-source-captions li')].map(n=>n.textContent)}}}})()")
            item.setdefault("choices", []).append(dict(pointer=pointer, **chosen))
            keyboard(cdp, "Tab", "Tab", 9)
            item["actions"].append(dict(name="source-choice", path=cdp.evaluate("location.pathname+location.hash"), next_tab=focus(cdp)))
        before = requests.copy()
        operation("source-choice-no-request", invoke)
        assert requests == before

    def capture(name, selector, width=390, height=844, scale=1):
        before, req = calls.copy(), requests.copy()
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=False)
        if scale == 2:
            cdp.evaluate("(()=>{const a=[...document.querySelectorAll('body,body *')],s=a.map(e=>parseFloat(getComputedStyle(e).fontSize));a.forEach((e,i)=>e.style.fontSize=s[i]*2+'px')})()")
        time.sleep(.3)
        measured = cdp.evaluate("""(selector=>{const e=document.querySelector(selector),r=e.getBoundingClientRect();return {
            url:location.pathname+location.hash,text:e.innerText,html:e.outerHTML,top:r.top+scrollY,bottom:r.bottom+scrollY,
            client:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,font:getComputedStyle(document.body).fontSize,
            controls:[...e.querySelectorAll('a,button,select,label,summary')].map(n=>({tag:n.tagName,text:n.innerText,
                href:n.getAttribute('href'),name:n.name,visible:n.checkVisibility(),disabled:n.disabled,rect:n.getBoundingClientRect().toJSON()}))};})""" + "(" + json.dumps(selector) + ")")
        measured.update(name=name, viewport=[width, height], text_scale=scale, focus=focus(cdp))
        assert measured["client"] == measured["scroll"], measured
        if args.captions and selector == SOURCE:
            measured["captions"] = cdp.evaluate("""(()=>{const s=document.querySelector('select[name="source_handle"]'),l=document.querySelector('#learning-recorded-source-captions');
                const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,width:r.width,top:r.top+scrollY,bottom:r.bottom+scrollY,height:r.height,client:e.clientWidth,scroll:e.scrollWidth}};
                return {options:[...s.options].map(o=>({value:o.value,caption:o.text})),value:s.value,select:box(s),label:box(s.parentElement),
                    describedBy:s.getAttribute('aria-describedby'),list:l?box(l):null,add:box(s.form.querySelector(':scope > button')),
                    rows:l?[...l.children].map(n=>{const r=document.createRange();r.selectNodeContents(n);const a=[...r.getClientRects()].map(x=>({x:x.x,right:x.right,top:x.top+scrollY,bottom:x.bottom+scrollY}));
                        const tail=document.createRange();tail.setStart(n.firstChild,Math.max(0,n.textContent.length-24));tail.setEnd(n.firstChild,n.textContent.length);
                        return {text:n.textContent,box:box(n),textRects:a,tail:[...tail.getClientRects()].map(x=>({x:x.x,right:x.right,top:x.top+scrollY,bottom:x.bottom+scrollY})),font:getComputedStyle(n).fontSize,overflow:getComputedStyle(n).overflow,whiteSpace:getComputedStyle(n).whiteSpace}}):[]};})()""")
            refs = measured["captions"]
            offered = [o["caption"] for o in refs["options"] if o["value"] != ""]
            assert [r["text"] for r in refs["rows"]] == (offered if args.phase == "after" else [])
            for row in refs["rows"]:
                assert row["box"]["client"] == row["box"]["scroll"]
                assert row["overflow"] == "visible" and row["whiteSpace"] == "normal"
                assert all(r["x"] >= row["box"]["x"] - 1 and r["right"] <= row["box"]["x"] + row["box"]["width"] + 1 for r in row["textRects"])
        # Ordinary viewport slices retain the scrollbar and cover the full target.
        measured["screenshots"] = []
        for index, y in enumerate(range(max(0, int(measured["top"])), int(measured["bottom"]) + 1, height - 80)):
            if args.captions:
                scroll_to(y)
            else:
                cdp.evaluate(f"window.scrollTo(0,{y})")
            filename = f"{name}-{index}.png"
            cdp.screenshot(root / filename)
            measured["screenshots"].append(filename)
        item["measurements"].append(measured)
        if scale == 2:
            cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>e.style.removeProperty('font-size'))")
        assert calls == before and requests == req

    def scroll_to(y):
        # CDP mouse wheel input scrolls the ordinary viewport; no DOM focus assignment.
        for _ in range(12):
            current = cdp.evaluate("scrollY")
            delta = y - current
            if abs(delta) < 2:
                return
            cdp.call("Input.dispatchMouseEvent", type="mouseWheel", x=15, y=150,
                     deltaX=0, deltaY=delta)
            time.sleep(.22)
            if cdp.evaluate("scrollY") == current:
                return

    def export_bytes():
        if not args.captions:
            return downloads(client)
        result = {}
        headers_by_kind = {}
        for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
            status, headers, raw = client.request("GET", f'/learning/downloads/{kind.replace("_", "-")}.json')
            assert status == 200
            assert headers["content-type"] == "application/json; charset=utf-8"
            assert headers["x-content-type-options"] == "nosniff"
            assert headers["cache-control"] == "no-store"
            result[kind] = (headers["content-disposition"], raw)
            headers_by_kind[kind] = headers
        item.setdefault("export_headers", []).append(headers_by_kind)
        return result

    def save_fixture(workspace, path, *, previous=None):
        fingerprint = None if previous is None else build_match_workspace_persistence_document_v1(previous).content_fingerprint
        assert save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(workspace),
            expected_content_fingerprint=fingerprint).status == "saved"

    def source_links(recovery=False):
        value = cdp.evaluate("""(()=>{const e=document.querySelector('#learning-recorded-matches');return {
            links:[...e.querySelectorAll('a')].map(n=>({href:n.getAttribute('href'),text:n.innerText})),
            fields:[...e.querySelectorAll('input,select')].map(n=>n.name),form:e.querySelector('form').action,
            disabled:e.querySelector('form > button').disabled};})()""")
        expected = recovery or (args.phase == "before" and not args.captions)
        assert any(link["href"] == "/matches" for link in value["links"]) == expected
        assert any(link["href"] == "/learning/recorded-matches/refresh" for link in value["links"])
        assert value["disabled"] == recovery
        item.setdefault("source_links", []).append(value)

    try:
        with ExitStack() as stack:
            for module, name, label in (
                (profiles, "save_frontend_profile_file_v1", "profile_saves"),
                (web, "discover_managed_items_v1", "navigation_discovery"),
                (direct, "discover_managed_items_v1", "source_revalidation"),
                (learning, "initialize_learning_corpus_web_v1", "collection_creations"),
                (learning, "import_match_workspace_into_learning_corpus_web_v1", "imports"),
                (learning, "prepare_learning_corpus_artifacts_web_v1", "preparations"),
                (learning, "select_current_learning_corpus_snapshot_web_v1", "selections"),
                (corpus_import, "save_learning_corpus_catalog_v1", "catalog_saves"),
                (managed.ManagedStatefulContextV1, "activate_match", "source_loads"),
            ):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            original_response = web.SkatMindAppWebRequestHandlerV1.send_response
            stack.enter_context(patch.object(web.SkatMindAppWebRequestHandlerV1, "send_response", response))
            client = operation("setup: authenticate HTTP byte client", lambda: Browser(server))
            local = LocalBrowser(args.browser, root / "browser-profile")
            cdp = local.cdp
            item["browser"] = local.version
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
            operation("setup: bootstrap Home", lambda: cdp.navigate(server.origin + "/"))
            action(f'.language-selector button[value="{locale}"]', "initial-language")
            action('.home-group a[href="/learning"]', "home-learning", 0)
            tab_to(cdp, 'form[action="/learning/create"] [name="collection_name"]')
            cdp.call("Input.insertText", text="Synthetic navigation collection")
            action('form[action="/learning/create"] button', "create-collection")
            active = server.app_context.managed_stateful.active_learning
            source_links(recovery=True)
            capture("empty-remedy", SOURCE)
            action(SOURCE + ' a[href="/matches"]', "empty-match-remedy", 0)
            assert cdp.evaluate("location.pathname") == "/matches"
            action('main a[href="/matches/new"]', "empty-create-entry", 0)
            assert cdp.evaluate("location.pathname") == "/matches/new"
            back("empty-back-to-match-entry")
            back("empty-back-to-collection")
            assert cdp.evaluate("location.pathname") == "/learning/current"
            path, workspace = operation("setup: genuine saved six-Play partial Match", lambda: saved_partial_match(server))
            if args.captions:
                action(REFRESH, "refresh-singleton", 0)
                capture("singleton", SOURCE)
                old = workspace
                workspace = _build_match_workspace_v1(revision=workspace.revision, slots=workspace.slots, match_definition=replace(workspace.match_definition,
                    title='Synthetic <same & "title"> ' + 'LongName' * 12))
                operation("setup: long source title", lambda: save_fixture(workspace, path, previous=old))
                first = independent_workspace(workspace, "first-equal-title")
                first_path = path.with_name("aaa.json")
                assert first.revision == workspace.revision
                operation("setup: distinct equal-title equal-revision source", lambda: save_fixture(first, first_path))
            original = path.read_bytes()
            (root / "original-match.json").write_bytes(original)
            item["source"] = hashes({"match": original})
            action(REFRESH, "refresh-new-source", 0)
            assert cdp.evaluate("location.pathname+location.hash") == direct.LEARNING_ENTRY_LOCATION
            source_links()
            if locale == "de" and not javascript:
                for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
                    capture(f"ordinary-{width}-{scale}", SOURCE, width, height, scale)
            else:
                capture("ordinary", SOURCE)
            before, req = calls.copy(), requests.copy()
            tab_to(cdp, SOURCE + " " + REFRESH)
            before_tab = focus(cdp)
            keyboard(cdp, "Tab", "Tab", 9)
            after_tab = focus(cdp)
            item["refresh_next_tab"] = dict(before=before_tab, after=after_tab)
            assert (after_tab["href"] == "/matches") == (args.phase == "before" and not args.captions)
            assert calls == before and requests == req
            choose(path, pointer=args.captions)
            if args.captions:
                assert item["choices"][-1]["index"] == 2
                capture("pending-choice", SOURCE, 390, 844)
                if locale == "de" and not javascript:
                    capture("pending-choice-320-double", SOURCE, 320, 800, 2)
            for language in ("en" if locale == "de" else "de", locale):
                action(f'.language-selector button[value="{language}"]', "unsent-language-" + language)
                assert cdp.evaluate(f"document.querySelector('{ADD} [name=source_handle]').value") == (source_handle(path) if javascript else "")
            if not javascript:
                choose(path)
            assert calls["imports"] == calls["preparations"] == 0
            action(ADD + ' > button', "first-add")
            assert cdp.evaluate("location.hash").startswith("#learning-match-")
            assert active.corpus.store.match_snapshots[0].workspace == workspace
            if args.captions:
                payload = item["operations"][-1]["payloads"][0]["fields"]
                assert [v for k, v in payload if k == "source_handle"] == [source_handle(path)]
                item["import_identity"] = dict(selected_handle=source_handle(path),
                    selected_match=workspace.match_definition.match_id,
                    imported_match=active.corpus.store.match_snapshots[0].workspace.match_definition.match_id)
            action(BUILD, "explicit-evaluation")
            assert cdp.evaluate("location.pathname+location.hash") == "/learning/current#learning-results"
            assert calls["preparations"] == 1
            capture("retained-results", "#learning-results", 320, 800)
            artifacts = active.corpus.prepared_artifacts
            current = active.corpus.store.document.catalog.current_matches
            corpus_bytes = saved_bytes(active.path)
            retained = operation("passive: ten authenticated exports", export_bytes)
            item["exports"] = {kind: {"filename": filename, **hashes({kind: raw})[kind]} for kind, (filename, raw) in retained.items()}
            for kind, (_, raw) in retained.items():
                (root / (kind + ".json")).write_bytes(raw)

            def retained_check(name):
                assert active.corpus.prepared_artifacts is artifacts
                assert active.corpus.store.document.catalog.current_matches == current
                assert saved_bytes(active.path) == corpus_bytes and path.read_bytes() == original
                assert operation("passive: ten exports after " + name, export_bytes) == retained
                assert calls["preparations"] == 1 and calls["source_loads"] == 0

            action('.site-nav a[href="/matches"]', "global-match-entry", 0)
            assert cdp.evaluate("location.pathname") == "/matches"
            assert cdp.evaluate("!!document.querySelector('form[action=\"/matches/open\"]')")
            back("global-back-to-collection")
            assert cdp.evaluate("location.pathname") == "/learning/current"
            retained_check("global-navigation")
            action('.site-nav a[href="/"]', "global-home", 0)
            action('.home-group a[href="/matches"]', "home-match-entry", 0)
            assert cdp.evaluate("location.pathname") == "/matches"
            back("home-back-to-home")
            back("home-back-to-collection")
            assert cdp.evaluate("location.pathname") == "/learning/current"
            retained_check("home-navigation")
            action(REFRESH, "passive-refresh", 0)
            retained_check("refresh")
            for language in ("en" if locale == "de" else "de", locale):
                action(f'.language-selector button[value="{language}"]', "retained-language-" + language)
                retained_check("language-" + language)
            choose(path)
            action(ADD + ' > button', "duplicate-add")
            assert active.last_result.status == "unchanged"
            retained_check("duplicate")
            assert not cdp.evaluate("!!document.querySelector('[data-operation-feedback]')")
            # Genuine external invalidation in this disposable source, no mocked success.
            choose(path)
            operation("setup: invalidate disposable source", lambda: path.write_bytes(b"{}"))
            action(ADD + ' > button', "reject-invalid-source")
            rejection = next(r for r in item["operations"][-1]["responses"] if r["method"] == "POST")
            assert rejection["path"] == "/learning/add-recorded-match" and rejection["status"] == 409
            assert cdp.evaluate("!!document.querySelector('.error-summary')")
            capture("error-summary", ".error-summary")
            capture("source-rejection", SOURCE)
            if args.captions:
                for language in ("en" if locale == "de" else "de", locale):
                    action(f'.language-selector button[value="{language}"]', "rejection-language-" + language)
                    assert cdp.evaluate("!!document.querySelector('.error-summary')")
                    assert cdp.evaluate(f"document.querySelector('{ADD} [name=source_handle]').value") == source_handle(path)
                capture("rejection-language-return", SOURCE, 320, 800)
            assert active.corpus.prepared_artifacts is artifacts
            operation("setup: restore original disposable source", lambda: path.write_bytes(original))
            action(REFRESH, "rejection-refresh-remedy", 0)
            retained_check("rejection-remedy")
            choose(path)
            action(ADD + ' > button', "remedied-duplicate")
            retained_check("remedied-duplicate")
            assert calls["imports"] == 3 and calls["catalog_saves"] == 1
            operation("setup: genuine later saved source revision", lambda: external_pass(path, workspace))
            choose(path)
            action(ADD + ' > button', "genuine-add-keep-current")
            assert active.corpus.prepared_artifacts is None
            assert active.corpus.store.document.catalog.current_matches == current
            assert calls["imports"] == 4 and calls["catalog_saves"] == 2 and calls["preparations"] == 1
            item["final_source"] = hashes({"match": path.read_bytes()})
            if args.captions and locale == "de" and not javascript:
                for index in range(10):
                    extra = independent_workspace(workspace, f"larger-source-{index}")
                    extra = _build_match_workspace_v1(revision=extra.revision, slots=extra.slots, match_definition=replace(extra.match_definition, title=f"Synthetic offered recording {index + 3}"))
                    operation("setup: larger-list saved source", lambda extra=extra, index=index: save_fixture(extra, path.with_name(f"extra-{index:02}.json")))
                action(REFRESH, "larger-list-refresh", 0)
                capture("larger-list-12", SOURCE, 320, 800)
            for route, resource in (("/assets/app.css", "assets/app.css"), ("/matches/assets/capture.js", "assets/workflow.js")):
                status, _, raw = operation("passive: served " + resource, lambda route=route: client.request("GET", route))
                assert status == 200 and digest(raw) == evidence["hashes"][resource]
            item.update(calls=dict(calls), requests=dict(requests), completed=True)
            print(root.name, "completed", len(item["measurements"]), "measurements", flush=True)
    finally:
        if local is not None:
            local.close()
            item["browser_exit"] = local.process.returncode
        fixture.close()
        item["server_stopped"] = True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("browser", "output", "wheel"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--captions", action="store_true", help="Verify #271 captions on the integrated #270 baseline.")
    run(parser.parse_args())
