# ruff: noqa: E501 - Keep browser probes and evidence records legible.
"""Disposable source-tree #293 before/after native prepared-result navigation evidence."""

import argparse
import json
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import verify_learning_outcome_navigation as prior
from test_learning_direct_entry_web import add_form, create_collection
from test_match_rollout_web import open_alex

VIEW = '#task-first-learning > p > a.button-link'
DISCLOSURE = 'details:has(> #learning-build)'


def run(args):
    assert args.output.parent.is_dir() and not args.output.exists()
    args.output.mkdir()
    evidence = dict(completed=False, phase=args.phase, python=sys.version, runs=[],
        boundary="Disposable source-tree verification; not installed maintainer UAT.")
    try:
        for locale in ("de", "en"):
            for script in (False, True):
                root = args.output / (locale + ("-js" if script else "-native"))
                root.mkdir()
                fixture = prior.localized_server.__wrapped__(root)
                server = next(fixture)
                local = None
                calls, requests = Counter(), Counter()
                item = dict(locale=locale, javascript=script, actions=[], landings=[])
                evidence["runs"].append(item)

                def counted(key, real, calls=calls):
                    def wrapped(*a, **kw):
                        calls[key] += 1
                        return real(*a, **kw)
                    return wrapped

                def request_counter(method, real, requests=requests):
                    def wrapped(handler):
                        requests[method + " " + handler.path] += 1
                        return real(handler)
                    return wrapped

                try:
                    with ExitStack() as stack:
                        for module, name, key in (
                            (prior.learning, "prepare_learning_corpus_artifacts_web_v1", "prepare"),
                            (prior.learning, "import_match_workspace_into_learning_corpus_web_v1", "import"),
                            (prior.learning, "select_current_learning_corpus_snapshot_web_v1", "select"),
                            (prior.learning, "reload_unified_learning_corpus_v1", "reload"),
                            (prior.web, "reload_unified_learning_corpus_v1", "reload_http"),
                            (prior.match_analysis, "execute_match_decision_analysis_v1", "analysis"),
                            (prior.execution, "execute", "session_analysis"),
                            (prior.match_context, "save_match_workspace_file_v1", "recording_write"),
                            (prior.session_files, "save_session_file", "session_write"),
                            (prior.corpus_import, "save_learning_corpus_catalog_v1", "catalog_write"),
                            (prior.corpus_import, "publish_learning_corpus_match_snapshot_object_v1", "object_write"),
                            (prior.profiles, "save_frontend_profile_file_v1", "profile_write"),
                        ):
                            stack.enter_context(patch.object(module, name, counted(key, getattr(module, name))))
                        for method in ("GET", "POST"):
                            stack.enter_context(patch.object(prior.Handler, "do_" + method,
                                request_counter(method, getattr(prior.Handler, "do_" + method))))
                        http, path, _ = open_alex(server, count=30)
                        create_collection(http)
                        page = prior.follow(http, http.submit(add_form(http), source_handle=prior.source_handle(path)))
                        active = server.app_context.managed_stateful.active_learning
                        # Locale setup is an actual delivered form submission, counted separately.
                        prior.follow(http, http.submit(prior.Forms(page).find("/actions/profile/language"), language=locale))
                        local = prior.LocalBrowser(args.browser, root / "browser-profile")
                        cdp = local.cdp
                        item["browser"] = local.version
                        name, value = http.cookie.split("=", 1)
                        cdp.call("Network.setCookie", name=name, value=value, url=server.origin)
                        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
                        cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900, deviceScaleFactor=1, mobile=False)

                        def action(selector, label, *, pointer=False, tab=False,
                                   calls=calls, requests=requests, cdp=cdp, item=item):
                            before, req = calls.copy(), requests.copy()
                            cdp.events.clear()
                            before_submit = None
                            if pointer:
                                from verify_recording_deletion import click
                                click(cdp, selector)
                            elif tab:
                                # Locate via native Tab only: no test focus/scroll on the destination.
                                for _ in range(180):
                                    if cdp.evaluate("document.activeElement.matches(" + json.dumps(selector) + ")"):
                                        break
                                    prior.keyboard(cdp, "Tab", "Tab", 9)
                                else:
                                    raise AssertionError("Native Tab did not reach " + selector)
                                before_submit = cdp.evaluate("({scrollY,open:document.querySelector('details:has(> #learning-build)')?.open,focus:document.activeElement.value})")
                                prior.keyboard(cdp, "Enter", "Enter", 13, "\r")
                            else:
                                cdp.activate(selector)
                            time.sleep(.8)
                            for _ in range(100):
                                if cdp.evaluate("document.readyState === 'complete' && !!document.activeElement"):
                                    break
                                time.sleep(.05)
                            time.sleep(.2)
                            cdp.evaluate("void 0")
                            item["actions"].append(dict(name=label, calls=dict(calls-before), requests=dict(requests-req),
                                before_submit=before_submit,
                                network=[dict(method=e["params"]["request"]["method"], url=e["params"]["request"]["url"],
                                    redirect_status=e["params"].get("redirectResponse", {}).get("status")) for e in cdp.events]))

                        def landing(label, *, corrected=False, error=False,
                                    cdp=cdp, root=root, item=item):
                            # Capture native landing BEFORE any test-only scroll/focus or next Tab.
                            row = cdp.evaluate("""(()=>{const result=document.querySelector('#learning-prepared-result'),
                                target=document.querySelector('#learning-results'),h=result?.querySelector('h2'),
                                d=result?.closest('details'),a=document.activeElement;
                                return {url:location.pathname+location.search+location.hash, viewport:[innerWidth,innerHeight],scrollY,
                                  open:d?.open, resultVisible:!!h?.checkVisibility(),heading:h?.innerText,
                                  headingRect:h?.getBoundingClientRect().toJSON(),targetVisible:!!target?.checkVisibility(),
                                  content:result?.innerText,focus:{id:a.id,tag:a.tagName,cls:a.className},
                                  autofocus:[...document.querySelectorAll('[autofocus]')].map(e=>({id:e.id,cls:e.className})),
                                  receipts:[...document.querySelectorAll('[data-operation-feedback]')].map(e=>e.innerText)};})()""")
                            row["name"] = label
                            cdp.screenshot(root / (label + ".png"))
                            prior.keyboard(cdp, "Tab", "Tab", 9)
                            row["next_tab"] = cdp.evaluate("(()=>{const e=document.activeElement;return {id:e.id,tag:e.tagName,cls:e.className,text:e.innerText,href:e.getAttribute('href')}})()")
                            item["landings"].append(row)
                            if corrected:
                                assert row["open"] and row["resultVisible"], row
                                assert row["focus"]["id"] == "learning-results", row
                                assert -1 <= row["headingRect"]["y"] < row["viewport"][1], row
                                if row["receipts"] and item["javascript"]:
                                    assert row["next_tab"]["cls"] == "operation-dismiss", row
                                else:
                                    assert row["next_tab"]["href"] == "/review/recorded", row
                            if error:
                                assert row["focus"]["cls"] == "error-summary", row
                                assert all(a["id"] != "learning-results" for a in row["autofocus"]), row
                            return row

                        cdp.navigate(server.origin + "/learning/current")
                        action(DISCLOSURE + ' > summary', "open-preparation")
                        action(prior.BUILD, "prepare", pointer=True)
                        row = landing("preparation-landing", corrected=args.phase == "after")
                        if args.phase == "before":
                            assert row["targetVisible"] and not row["open"] and not row["resultVisible"], row
                            action(VIEW, "view", pointer=True)
                            row = landing("view-landing")
                            assert row["targetVisible"] and not row["open"] and not row["resultVisible"], row
                        else:
                            verify_after(cdp, server, http, active, path, item, calls, requests, action, landing, root)
                        item["totals"] = dict(calls)
                finally:
                    if local is not None:
                        local.close()
                    fixture.close()
        evidence["completed"] = True
    finally:
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(dict(completed=evidence["completed"], runs=len(evidence["runs"]))))


def verify_after(cdp, server, http, active, path, item, calls, requests, action, landing, root):
    route = cdp.evaluate("location.pathname")
    assert cdp.evaluate("location.search+location.hash") == ""
    assert cdp.evaluate("document.querySelector(" + json.dumps(VIEW) + ").getAttribute('href')") == route
    assert item["landings"][0]["receipts"]
    assert item["actions"][-1]["calls"] == {"prepare": 1}
    assert any(e["redirect_status"] == 303 and e["url"] == server.origin + route
               for e in item["actions"][-1]["network"])
    artifacts = (active.corpus.prepared_artifacts, active.corpus.tactical_prepared_artifacts,
                 active.corpus.tactical_coaching_prepared_artifacts)
    stamp = (active.corpus.generation, active.corpus.strategy_source_store.revision,
             active.corpus.store.document.catalog.revision, active.debrief_sources.revision)
    retained = prior.downloads(http)
    item["downloads"] = {kind: dict(disposition=name, bytes=len(raw), sha256=prior.digest(raw))
                         for kind, (name, raw) in retained.items()}
    files = prior.saved_bytes(active.path)
    recording = path.read_bytes()
    home = server.app_context.managed_home.root
    before_calls = calls.copy()
    before_files = prior.saved_bytes(home)

    def view(label, *, pointer=False):
        req = requests.copy()
        action(VIEW, label, pointer=pointer, tab=not pointer)
        assert requests["GET " + route] - req["GET " + route] == 1
        assert not item["actions"][-1]["calls"]
        assert any(e["method"] == "GET" and e["url"] == server.origin + route
                   for e in item["actions"][-1]["network"])
        row = landing(label, corrected=True)
        assert not row["receipts"]

    view("pointer-view-from-result-page", pointer=True)
    for pointer in (False, True):
        action(DISCLOSURE + ' > summary', "manually-close", pointer=True)
        assert not cdp.evaluate("document.querySelector(" + json.dumps(DISCLOSURE) + ").open")
        view("closed-view-" + ("pointer" if pointer else "tab-enter"), pointer=pointer)
    # Refresh the native landing, before the measurement helper's next-Tab probe
    # scrolls onward to the decision chooser (reload may legitimately restore that viewport).
    action(VIEW, "return-before-refresh", pointer=True)
    req = requests.copy()
    cdp.call("Page.reload", ignoreCache=True)
    time.sleep(.8)
    landing("refresh", corrected=True)
    assert requests["GET " + route] - req["GET " + route] == 1
    assert calls == before_calls and prior.saved_bytes(home) == before_files

    item["language"] = []
    for closed in (False, True):
        if closed:
            action(DISCLOSURE + ' > summary', "close-before-language", pointer=True)
        locale = cdp.evaluate("document.documentElement.lang")
        language = "en" if locale == "de" else "de"
        before = calls.copy()
        profile = server.app_context.frontend_profile.profile_path
        profile_before = profile.read_bytes()
        other_files = {p: raw for p, raw in prior.saved_bytes(home).items() if home / p != profile}
        action(f'.language-selector button[value="{language}"]', "language-" + ("closed" if closed else "open"), tab=True)
        # No landing helper before measuring continuity: it intentionally advances Tab.
        actual = cdp.evaluate("""(()=>{const a=document.activeElement,m=document.querySelector('meta[name="language-return"]');return {route:location.pathname,hash:location.hash,
            scrollY,locale:document.documentElement.lang,focus:a.value,id:a.id,
            open:document.querySelector('details:has(> #learning-build)').open,
            autofocus:document.querySelectorAll('[autofocus]').length,
            view:m ? JSON.parse(m.content).view : null}})()""")
        actual["manually_closed"] = closed
        item["language"].append(actual)
        cdp.screenshot(root / ("language-closed.png" if closed else "language-open.png"))
        assert actual["route"] == route and actual["hash"] == "" and actual["autofocus"] == 0
        assert actual["locale"] == language
        if item["javascript"]:
            assert actual["open"] is not closed and actual["focus"] == language
            assert abs(actual["scrollY"] - item["actions"][-1]["before_submit"]["scrollY"]) <= 2
        else:
            assert actual["open"] and actual["id"] != "learning-results"
        assert calls - before == Counter(profile_write=1)
        assert profile.read_bytes() != profile_before
        assert other_files == {p: raw for p, raw in prior.saved_bytes(home).items() if home / p != profile}
        view("view-after-language-" + ("closed" if closed else "open"), pointer=True)

    # A rejected recreation preserves the prior genuine bundle and its bytes.
    action('#learning-build details > summary', "open-settings", pointer=True)
    prior.native_text(cdp, '#learning-build [name="train_weight"]', "0")
    before = calls.copy()
    action(prior.BUILD, "failed-recreation", pointer=True)
    landing("failed-recreation", error=True)
    assert calls == before and prior.downloads(http) == retained
    action(VIEW, "view-with-retained-error", pointer=True)
    row = landing("view-with-retained-error", error=True)
    assert row["open"] and row["resultVisible"] and not row["receipts"]
    assert prior.saved_bytes(active.path) == files and path.read_bytes() == recording
    assert all(a is b for a, b in zip(artifacts, (active.corpus.prepared_artifacts,
        active.corpus.tactical_prepared_artifacts, active.corpus.tactical_coaching_prepared_artifacts), strict=True))
    assert stamp == (active.corpus.generation, active.corpus.strategy_source_store.revision,
                    active.corpus.store.document.catalog.revision, active.debrief_sources.revision)
    assert prior.downloads(http) == retained
    item["retained_objects_and_files"] = True
    item["passive_delta_including_language"] = dict(calls - before_calls)
    assert calls - before_calls == Counter(profile_write=2)

    # Competing tab: explicit collection creation is accounted separately, then stale View.
    before = calls.copy()
    create_collection(http, "Competing synthetic collection")
    item["competing_collection_setup"] = dict(calls - before)
    current = server.app_context.managed_stateful.active_learning
    files = prior.saved_bytes(home)
    before = calls.copy()
    action(VIEW, "stale-view-after-collection-switch", pointer=True)
    assert calls == before and prior.saved_bytes(home) == files
    assert server.app_context.managed_stateful.active_learning is current
    assert cdp.evaluate("document.querySelector('#learning-prepared-result')===null")
    cdp.screenshot(root / "stale-view.png")
    item["stale"] = dict(route=cdp.evaluate("location.pathname"), text=cdp.evaluate("document.querySelector('main').innerText"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
