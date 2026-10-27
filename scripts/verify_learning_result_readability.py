# ruff: noqa: E501 - Keep browser probes and evidence records legible.
"""Disposable HTTP/DevTools evidence; controlled retained Search is identified explicitly."""

import argparse
import json
import sys
import time
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
import verify_learning_outcome_navigation as prior
from test_learning_result_readability import (
    controlled_focus_bundles,
    include_bundles,
    one_item_result,
)

import skatmind.app_web.frontend_identifier_generation as identifiers
import skatmind.app_web.learning_result_projection as projection
import skatmind.learning_corpus_persistence as persistence
import skatmind.learning_corpus_strategy_teacher_builder as teacher
import skatmind.learning_corpus_tactical_motif_builder as tactical
import skatmind.learning_dataset_v2_builder as dataset
import skatmind.recommendation_workflow as recommendation

OUTER = 'details:has(> #learning-build)'
VIEW = '#task-first-learning > p > a.button-link'


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    start = time.monotonic()
    evidence = dict(completed=False, python=sys.version,
        boundary="Disposable source-tree fixtures, not installed UAT. Focus fixtures use controlled retained Search, not a real Search execution.",
        zoom="Fresh isolated browser profile, default 100% zoom; devicePixelRatio and visualViewport.scale measured. No genuine 200% evidence.",
        runs=[])
    try:
        for focus in (False, True):
            for locale in ("en", "de"):
                for script in (False, True):
                    root = args.output / f'{"focus" if focus else "one-item"}-{locale}-js{int(script)}'
                    root.mkdir()
                    fixture = prior.localized_server.__wrapped__(root)
                    server = next(fixture)
                    local = None
                    calls, requests = Counter(), Counter()
                    row = dict(focus_fixture=focus, locale=locale, javascript=script, states=[], phases=[])
                    evidence["runs"].append(row)
                    def counted(key, real, calls=calls):
                        def call(*args_, **kw):
                            calls[key] += 1
                            return real(*args_, **kw)
                        return call
                    def request_count(method, real, requests=requests):
                        def call(handler):
                            requests[method + " " + handler.path] += 1
                            return real(handler)
                        return call
                    try:
                        with ExitStack() as stack:
                            for module, name, key in (
                                (prior.learning, "prepare_learning_corpus_artifacts_web_v1", "preparation"),
                                (prior.learning, "import_match_workspace_into_learning_corpus_web_v1", "import"),
                                (prior.learning, "select_current_learning_corpus_snapshot_web_v1", "selection"),
                                (prior.learning, "reload_unified_learning_corpus_v1", "reload"),
                                (prior.web, "reload_unified_learning_corpus_v1", "reload_http"),
                                (prior.match_analysis, "execute_match_decision_analysis_v1", "analysis"),
                                (recommendation, "solve_compatible_world_minimax", "search"),
                                (prior.execution, "execute", "session_analysis"),
                                (teacher, "build_match_decision_position_request_v1", "reconciliation"),
                                (dataset, "build_match_observed_game_reconstruction_v1", "dataset_reconstruction"),
                                (tactical, "build_match_observed_game_reconstruction_v1", "tactical_reconstruction"),
                                (prior.match_context, "save_match_workspace_file_v1", "recording_write"),
                                (prior.session_files, "save_session_file", "session_write"),
                                (prior.corpus_import, "save_learning_corpus_catalog_v1", "catalog_write"),
                                (persistence, "save_learning_corpus_catalog_v1", "catalog_write"),
                                (prior.corpus_import, "publish_learning_corpus_match_snapshot_object_v1", "snapshot_write"),
                                (prior.profiles, "save_frontend_profile_file_v1", "profile_write"),
                                (identifiers, "_generate_identifier", "product_id"),
                            ):
                                stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
                            for method in ("GET", "POST"):
                                stack.enter_context(patch.object(prior.Handler, "do_" + method,
                                    request_count(method, getattr(prior.Handler, "do_" + method))))
                            if focus:
                                http = prior.Browser(server)
                                with pytest.MonkeyPatch.context() as controlled:
                                    bundles = controlled_focus_bundles(controlled)
                                    page = include_bundles(http, bundles, variants=True)
                                row["controlled_search_reports"] = len(bundles)
                            else:
                                http, page, _ = one_item_result(server)
                            row["phases"].append(dict(name="explicit_fixture_setup", calls=dict(calls)))
                            active = server.app_context.managed_stateful.active_learning
                            before = calls.copy()
                            prior.follow(http, http.submit(prior.Forms(page).find("/actions/profile/language"), language=locale))
                            row["phases"].append(dict(name="explicit_locale_setup", calls=dict(calls-before)))
                            local = prior.LocalBrowser(args.browser, root / "browser-profile")
                            row["browser"] = local.version
                            cdp = local.cdp
                            name, value = http.cookie.split("=", 1)
                            cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
                            cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                            cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)

                            def key(value, cdp=cdp):
                                code, virtual = {"Tab": ("Tab", 9), "Enter": ("Enter", 13), " ": ("Space", 32)}[value]
                                for kind in ("keyDown", "keyUp"):
                                    cdp.call("Input.dispatchKeyEvent", type=kind, key=value, code=code, windowsVirtualKeyCode=virtual,
                                        **({"text": "\r" if value == "Enter" else value} if kind == "keyDown" and value != "Tab" else {}))

                            def activate(selector, *, keyboard=False, space=False, cdp=cdp, key=key):
                                if keyboard:
                                    for _ in range(300):
                                        if cdp.evaluate("document.activeElement===document.querySelector(" + json.dumps(selector) + ")"):
                                            break
                                        key("Tab")
                                    else:
                                        raise AssertionError("Native Tab target unavailable: " + selector)
                                    assert cdp.evaluate("document.activeElement.matches(':focus-visible')")
                                    key(" " if space else "Enter")
                                else:
                                    from verify_recording_deletion import click
                                    click(cdp, selector)
                                time.sleep(.5)
                                for _ in range(100):
                                    if cdp.evaluate("document.readyState") == "complete":
                                        break
                                    time.sleep(.05)
                                time.sleep(.2)

                            def capture(label, cdp=cdp, row=row, root=root):
                                # Always called before test scrolling/focusing or next-Tab probes at landings.
                                state = cdp.evaluate("""(()=>{const h=document.querySelector('#learning-results'),a=document.activeElement;
                                    return {path:location.pathname,hash:location.hash,scrollY,viewport:[innerWidth,innerHeight],width:document.documentElement.scrollWidth,
                                    devicePixelRatio,scale:visualViewport.scale,heading:h?.innerText,rect:h?.getBoundingClientRect().toJSON(),
                                    primary:document.querySelector('#learning-result-primary')?.innerText,
                                    focus:{id:a.id,tag:a.tagName,cls:a.className,value:a.value,visible:a.matches(':focus-visible'),outline:getComputedStyle(a).outline},
                                    outer:document.querySelector('details:has(> #learning-build)')?.open,
                                    technical:document.querySelector('#learning-result-technical')?.open,inputs:document.querySelector('#learning-result-inputs')?.open,
                                    downloads:[...document.querySelectorAll('a[download][href^="/learning/downloads/"]')].map(a=>({href:a.getAttribute('href'),visible:a.checkVisibility()})),
                                    focuses:[...document.querySelectorAll('.learning-focus')].map(e=>e.innerText),
                                    receipt:!!document.querySelector('[data-operation-feedback]'),autofocus:document.querySelectorAll('[autofocus]').length};})()""")
                                state["name"] = label
                                row["states"].append(state)
                                cdp.screenshot(root / (label + ".png"))
                                assert state["width"] <= state["viewport"][0], state
                                return state

                            cdp.navigate(server.origin + "/learning/current")
                            activate(OUTER + ' > summary', keyboard=not script, space=not script)
                            before, req = calls.copy(), requests.copy()
                            cdp.events.clear()
                            activate(prior.BUILD, keyboard=not script)
                            initial = capture("initial-preparation-landing")
                            row["phases"].append(dict(name="explicit_browser_preparation", calls=dict(calls-before), requests=dict(requests-req)))
                            assert calls["preparation"] - before["preparation"] == 1
                            assert initial["outer"] and not initial["technical"] and not initial["inputs"]
                            assert initial["focus"]["id"] == "learning-results" and initial["hash"] == ""
                            assert 0 <= initial["rect"]["y"] < 900 and initial["heading"]
                            assert len(initial["downloads"]) == 10 and not any(a["visible"] for a in initial["downloads"])
                            assert bool(initial["focuses"]) is focus
                            assert any(e["params"].get("redirectResponse", {}).get("status") == 303 for e in cdp.events)
                            route = initial["path"]
                            references = (active.corpus.store, active.corpus.prepared_artifacts,
                                active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts)
                            stamp = (active.corpus.generation, active.corpus.strategy_source_store.revision,
                                     active.corpus.store.document.catalog.revision)
                            retained = prior.downloads(http)
                            row["downloads"] = {kind: dict(disposition=name, bytes=len(raw), sha256=prior.digest(raw))
                                for kind, (name, raw) in retained.items()}
                            for kind, (_name, raw) in retained.items():
                                (root / (kind + ".json")).write_bytes(raw)
                            home = server.app_context.managed_home.root
                            files = prior.saved_bytes(home)
                            before = calls.copy()
                            key("Tab")
                            next_tab = cdp.evaluate("({tag:document.activeElement.tagName,cls:document.activeElement.className,href:document.activeElement.getAttribute('href'),text:document.activeElement.innerText})")
                            row["next_tab"] = next_tab
                            assert (next_tab["cls"] == "operation-dismiss" if script else
                                next_tab["tag"] == "SUMMARY" if focus else next_tab["href"] == "/review/recorded")
                            for selector in ("#learning-result-inputs", "#learning-result-technical"):
                                req = requests.copy()
                                activate(selector + " > summary", keyboard=True, space=True)
                                assert cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").open")
                                assert requests == req
                            capture("expanded-details")
                            if focus:
                                activate(".learning-focus details > summary", keyboard=True)
                                capture("supporting-decisions")
                            cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=900, deviceScaleFactor=1, mobile=False)
                            capture("narrow-expanded-details")
                            activate(VIEW)
                            explicit = capture("initial-explicit-view-landing")
                            assert explicit["focus"]["id"] == "learning-results" and not explicit["technical"]
                            assert not explicit["receipt"]
                            assert calls == before and prior.saved_bytes(home) == files
                            row["phases"].append(dict(name="passive_view_disclosures_downloads", calls=dict(calls-before)))
                            for closed in (False, True):
                                activate("#learning-result-technical > summary", keyboard=True, space=True)
                                if closed:
                                    activate(OUTER + " > summary")
                                language = "de" if cdp.evaluate("document.documentElement.lang") == "en" else "en"
                                before = calls.copy()
                                activate('.language-selector button[value="' + language + '"]', keyboard=True)
                                returned = capture("language-" + ("closed" if closed else "open"))
                                assert returned["path"] == route and returned["autofocus"] == 0
                                if script:
                                    assert returned["outer"] is not closed and returned["technical"]
                                    assert returned["focus"]["value"] == language
                                else:
                                    assert returned["outer"] and not returned["technical"]
                                assert calls-before == Counter(profile_write=1)
                                row["phases"].append(dict(name="explicit_language_change", calls=dict(calls-before)))
                                activate(VIEW)
                            assert all(a is b for a, b in zip(references, (active.corpus.store, active.corpus.prepared_artifacts,
                                active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts), strict=True))
                            assert stamp == (active.corpus.generation, active.corpus.strategy_source_store.revision,
                                             active.corpus.store.document.catalog.revision)
                            profile_path = server.app_context.frontend_profile.profile_path
                            assert {p: b for p, b in files.items() if home / p != profile_path} == {
                                p: b for p, b in prior.saved_bytes(home).items() if home / p != profile_path}
                            assert prior.downloads(http) == retained
                            # Deliberate lifetime probes are separate from passive activity.
                            if focus:
                                active.corpus.prepared_artifacts = replace(active.corpus.prepared_artifacts)
                                cdp.navigate(server.origin + route)
                                assert capture("prepared-replacement-rejection").get("primary") is None
                                cdp.navigate(server.origin + "/learning/current")
                                current_route = cdp.evaluate("document.querySelector(" + json.dumps(VIEW) + ").getAttribute('href')")
                                before = calls.copy()
                                activate('#insight-versions details > summary')
                                activate('form:has(input[value="select_current_snapshot"]) button', keyboard=True)
                                row["phases"].append(dict(name="explicit_version_selection", calls=dict(calls-before)))
                                assert calls-before == Counter(selection=1, catalog_write=1)
                                cdp.navigate(server.origin + current_route)
                                assert capture("version-selection-rejection").get("primary") is None
                            else:
                                real = projection.project_learning_result
                                def change_during_render(*args_, real=real, active=active, **kw):
                                    display = real(*args_, **kw)
                                    active.corpus.strategy_source_store.revision += 1
                                    return display
                                with patch.object(projection, "project_learning_result", change_during_render):
                                    cdp.navigate(server.origin + route)
                                assert capture("source-change-during-render-rejection").get("primary") is None
                            row["completed"] = True
                    finally:
                        if local:
                            local.close()
                        fixture.close()
        evidence["completed"] = True
    finally:
        evidence["seconds"] = round(time.monotonic()-start, 3)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(dict(completed=evidence["completed"], seconds=evidence["seconds"], output=str(args.output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
