"""Optional installed-Wheel navigation evidence using local native Chromium controls."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
from dataclasses import replace
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import contrast, fill, posts, wait

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json",
           "rendering.py", "server.py", "contracts.py", "information_architecture.py",
           "entry_rendering.py", "recorded_review_opening.py", "recorded_review_rendering.py",
           "match_review_context.py", "match_review_rendering.py", "match_report_rendering.py",
           "task_first_match_rendering.py", "language_context.py", "form_registry.py")


def measure(cdp, output, run, name, locale, width, height, scale=1):
    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
             deviceScaleFactor=1, mobile=False)
    if scale == 2:
        cdp.evaluate("""(() => {const es=[...document.querySelectorAll('body,body *')];
          const sizes=es.map(e=>parseFloat(getComputedStyle(e).fontSize));
          es.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px');})()""")
    geometry = cdp.evaluate("""(() => {
      const visible=e=>e.checkVisibility({visibilityProperty:true});
      const box=e=>{const r=e.getBoundingClientRect(); return {top:r.top+scrollY,
        left:r.left,width:r.width,height:r.height};};
      return {path:location.pathname,client:document.documentElement.clientWidth,
        scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,
        headings:[...document.querySelectorAll('main h1,main h2,main h3')].filter(visible)
          .map(e=>({tag:e.tagName,text:e.textContent,...box(e)})),
        orientation:document.querySelectorAll('.scope-guide,.concept-guide,.related-areas').length,
        about:document.querySelector('footer a') && {
          color:getComputedStyle(document.querySelector('footer a')).color,
          background:getComputedStyle(document.querySelector('footer')).backgroundColor},
        actions:[...document.querySelectorAll('main a.button-link,main button[type=submit]')]
          .filter(visible).map(e=>({text:e.textContent,href:e.getAttribute('href'),...box(e)})),
        focus:{tag:document.activeElement.tagName,outline:getComputedStyle(document.activeElement).outline},
        overflow:[...document.querySelectorAll('body *')].filter(e=>visible(e) &&
          e.getBoundingClientRect().right>document.documentElement.clientWidth+1)
          .map(e=>({tag:e.tagName,classes:e.className,...box(e)})).slice(0,12)};
    })()""")
    run["measurements"].append({"state": name, "locale": locale, "viewport": [width, height],
                                "text_scale": scale, **geometry})
    cdp.screenshot(output / f"{run['mode']}-{name}-{locale}-{width}-{scale}.png", whole=True)
    target = ('#session-result' if name == "session-result" else
              '#recorded-decisions' if name == "session-decisions" else
              '#match-review' if name.startswith("match-") and name != "match-entry" else
              '.error-summary' if "error" in name else 'main')
    cdp.evaluate(f'document.querySelector({json.dumps(target)}).scrollIntoView()')
    cdp.screenshot(output / f"{run['mode']}-{name}-{locale}-{width}-{scale}-viewport.png")
    if run["phase"] == "after":
        assert geometry["scroll"] == geometry["client"], geometry
        assert contrast(geometry["about"]["color"], geometry["about"]["background"]) >= 4.5


def entry_layout(cdp, server, output, run):
    for route, name in (("/", "home"), ("/sessions", "session-entry"),
                        ("/matches", "match-entry"), ("/learning", "learning-entry"),
                        ("/review", "manual-entry")):
        for locale in ("de", "en"):
            cdp.navigate(server.origin + route)
            cdp.activate(f'form.language-selector button[value="{locale}"]')
            time.sleep(.4)
            for width, height in ((1365, 900), (390, 844), (320, 800)):
                measure(cdp, output, run, name, locale, width, height)
            measure(cdp, output, run, name, locale, 320, 800, 2)


def current_layout(cdp, output, item, name, *, error=False):
    for locale in ("de", "en"):
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp, error=error)
        for width, height in ((1365, 900), (390, 844), (320, 800)):
            measure(cdp, output, item, name, locale, width, height)
        measure(cdp, output, item, name, locale, 320, 800, 2)
        # Native language rerender resets verification-only text enlargement.
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp, error=error)


def fixtures(server):
    """Legal persisted synthetic sources; no Report or successful execution is injected."""
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    from test_match_decision_review_preparation import _workspace_with_partial_game
    from test_session_recorded_review_web import Browser, record_live_game
    from test_unified_local_app_managed_items import _save_session

    from skatmind.match_workspace_contracts import create_match_workspace_v1
    from skatmind.match_workspace_operations import (
        mark_match_workspace_passed_deal_v1,
        set_match_workspace_observed_game_v1,
    )
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    record_live_game(Browser(server), play_count=30)
    context = server.app_context
    session = context.managed_stateful.active_session
    workspace, _ = _workspace_with_partial_game()
    title = "Synthetic duplicate Match — Alexandra-Maria Long-Recording-Name " * 2
    definition = replace(workspace.match_definition, title=title.strip(), participants=tuple(
        replace(player, player_label=f"Player {index} Long-Synthetic-Participant-Name")
        for index, player in enumerate(workspace.match_definition.participants, 1)))
    workspace = set_match_workspace_observed_game_v1(create_match_workspace_v1(definition),
        workspace.slots[2].observed_game, expected_revision=0).workspace
    workspace = mark_match_workspace_passed_deal_v1(workspace, match_position=2,
        game_timecode=None, expected_revision=workspace.revision).workspace
    paths = []
    for name, source in (("recording.json", workspace), ("duplicate-title.json",
            create_match_workspace_v1(replace(definition, match_id="duplicate-title-match")))):
        path = context.managed_stateful.root("matches") / name
        result = save_match_workspace_file_v1(path,
            build_match_workspace_persistence_document_v1(source),
            expected_content_fingerprint=None)
        assert result.status == "saved"
        paths.append(path)
    for name in ("first", "second"):
        _save_session(context.managed_stateful.root("sessions") / (name + ".json"),
                      session_id="synthetic-" + name)
    (context.managed_stateful.root("matches") / "invalid.json").write_text("{}", encoding="utf-8")
    # Strict startup restores recordings only; the chooser performs the real opening.
    server.app_context = AppWebContextV1.create(context.managed_home)
    return session, paths[0]


def action(cdp, selector, item, name, expected, *, error=False):
    cdp.events.clear()
    cdp.activate(selector)
    wait(cdp, error=error)
    observed = posts(cdp)
    item["actions"][name] = {"posts": observed,
        "requests": [{"method": event["params"]["request"]["method"],
                      "path": urlsplit(event["params"]["request"]["url"]).path}
                     for event in cdp.events],
        "path": cdp.evaluate("location.pathname+location.hash"),
        "focus": cdp.evaluate("({tag:document.activeElement.tagName,"
            "id:document.activeElement.id,outline:getComputedStyle(document.activeElement).outline})")}
    assert observed == expected, (name, observed)


def download(cdp, server, route):
    cookies = cdp.call("Network.getCookies", urls=[server.origin])["cookies"]
    cookie = "; ".join(item["name"] + "=" + item["value"] for item in cookies)
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=120)
    try:
        connection.request("GET", route, headers={"Cookie": cookie})
        response = connection.getresponse()
        content = response.read()
        assert response.status == 200, (route, response.status)
        return content
    finally:
        connection.close()


def recorded_flows(cdp, server, output, item):
    import skatmind.app_web.execution as session_execution
    import skatmind.capture_web.analysis as match_execution

    current_layout(cdp, output, item, "chooser-empty")
    session_source, match_path = fixtures(server)
    counts = {"session": 0, "match": 0}
    original_session = session_execution.execute
    original_match = match_execution.execute_match_decision_analysis_v1
    def counted_session(*args, **kwargs):
        counts["session"] += 1
        return original_session(*args, **kwargs)
    def counted_match(*args, **kwargs):
        counts["match"] += 1
        return original_match(*args, **kwargs)
    session_execution.execute = counted_session
    match_execution.execute_match_decision_analysis_v1 = counted_match
    try:
        source_bytes = {path: path.read_bytes()
            for path in server.app_context.managed_home.root.rglob("*.json")
            if path.name != "frontend-profile.json"}
        cdp.navigate(server.origin + "/")
        action(cdp, 'main a[href="/review/recorded"]', item, "home-chooser", [])
        current_layout(cdp, output, item, "chooser-populated")
        session_form = ('form[action="/review/open-recording"]:has(input[name="handle"][value="'
                        + session_source.handle + '"]) button')
        action(cdp, session_form, item, "session-open", ["/review/open-recording"])
        active = server.app_context.managed_stateful.active_session
        assert counts == {"session": 0, "match": 0}
        current_layout(cdp, output, item, "session-decisions")
        action(cdp, 'form[action="/sessions/review-decision"] button', item,
               "session-review", ["/sessions/review-decision"])
        assert counts == {"session": 1, "match": 0}
        execution, source = active.execution, active.recorded_review_source
        current_layout(cdp, output, item, "session-result")
        session_bytes = download(cdp, server, "/sessions/downloads/result.json")
        assert session_bytes == execution.result_json_bytes
        action(cdp, 'a.brand', item, "session-home", [])
        action(cdp, 'main a[href="/review/recorded"]', item, "session-chooser-return", [])
        action(cdp, session_form, item, "session-reuse", ["/review/open-recording"])
        assert server.app_context.managed_stateful.active_session is active
        assert active.execution is execution and active.recorded_review_source is source
        assert download(cdp, server, "/sessions/downloads/result.json") == session_bytes
        action(cdp, 'a.brand', item, "match-home", [])
        action(cdp, 'main a[href="/review/recorded"]', item, "match-chooser", [])
        from skatmind.app_web.managed_item_storage import build_managed_item_handle_v1
        handle = build_managed_item_handle_v1(family="matches", basename=match_path.name)
        match_form = ('form[action="/review/open-recording"]:has(input[name="handle"][value="'
                      + handle + '"]) button')
        action(cdp, match_form, item, "match-open", ["/review/open-recording"])
        match = server.app_context.managed_stateful.active_match
        assert match.selected_position == 1 and counts["match"] == 0
        current_layout(cdp, output, item, "match-empty")
        fill(cdp, '.match-review-selector select', "2")
        action(cdp, '.match-review-selector button', item, "match-passed-select", [])
        current_layout(cdp, output, item, "match-passed")
        fill(cdp, '.match-review-selector select', "3")
        action(cdp, '.match-review-selector button', item, "match-recorded-select", [])
        current_layout(cdp, output, item, "match-review")
        decision = 'form:has(input[name="operation"][value="analyze_decision"])'
        # Relevant safe unsent settings survive the optional enhancement only.
        fill(cdp, decision + ' [name=immediate_random_seed]', "27")
        action(cdp, 'form.language-selector button[value="de"]', item,
               "match-unsent-language", ["/actions/profile/language"])
        seed = cdp.evaluate(
            f"document.querySelector('{decision} [name=immediate_random_seed]').value")
        assert seed == ("27" if item["mode"] == "js" else "0")
        item["unsent_seed"] = seed
        action(cdp, decision + ' button[type=submit]', item, "match-analysis",
               ["/matches/api/v1/analysis"])
        assert counts == {"session": 1, "match": 1}
        report = match.capture.report_store.list()[0]
        assert report.match_position == 3 and report.value.status == "executed"
        report_route = f"/matches/reports/{report.report_id}"
        assert cdp.evaluate("location.pathname") == report_route
        current_layout(cdp, output, item, "match-result")
        report_bytes = download(cdp, server, f"/matches/api/v1/reports/{report.report_id}.json")
        action(cdp, 'a[href="/matches/position/3#match-recording"]', item, "back-to-recording", [])
        action(cdp, 'a[href="/matches/review/3"]', item, "back-to-game-review", [])
        assert match.selected_position == 3 and match.capture.report_store.list() == (report,)
        # Native contextual error, followed by native language switching and safe values.
        fill(cdp, decision + ' [name=immediate_sample_count]', "-1")
        action(cdp, decision + ' button[type=submit]', item, "analysis-error",
               ["/matches/api/v1/analysis"], error=True)
        current_layout(cdp, output, item, "analysis-error", error=True)
        cdp.navigate(server.origin + "/matches/reports/" + "0" * 64)
        current_layout(cdp, output, item, "report-error", error=True)
        action(cdp, 'a.brand', item, "error-home", [])
        action(cdp, 'main a[href="/review/recorded"]', item, "error-chooser", [])
        download(cdp, server, "/review/recorded")  # A genuine competing discovery refresh.
        action(cdp, session_form, item, "stale-chooser", ["/review/open-recording"], error=True)
        current_layout(cdp, output, item, "chooser-error", error=True)
        cdp.navigate(server.origin + "/review/recorded")
        discovery = server.app_context.managed_stateful.discoveries["sessions"]
        missing = next(entry.summary.handle for entry in discovery.entries
                       if entry.summary.semantic_product_id == "synthetic-first")
        missing_form = ('form[action="/review/open-recording"]:has(input[name="handle"][value="'
                        + missing + '"]) button')
        action(cdp, missing_form, item, "missing-snapshots-open", ["/review/open-recording"])
        current_layout(cdp, output, item, "session-missing-snapshots")
        action(cdp, 'footer a[href="/about"]', item, "footer-about", [])
        assert cdp.evaluate("location.pathname") == "/about"
        item["sources"] = {"session": active.state.session_id, "match": report.match_id,
            "position": report.match_position,
            "game": match.workspace.slots[2].observed_game.game_id,
            "decision": report.decision_index, "report": report.report_id,
            "session_result_sha256": hashlib.sha256(session_bytes).hexdigest(),
            "match_result_sha256": hashlib.sha256(report_bytes).hexdigest()}
        assert counts == {"session": 1, "match": 1}
        assert all(path.read_bytes() == content for path, content in source_bytes.items())
        item["executions"] = counts
        item["recording_bytes_unchanged"] = True
        item["http_resources"] = {}
        for route, resource in (("/assets/app.css", "assets/app.css"),
                                ("/matches/assets/capture.js", "assets/workflow.js")):
            content = download(cdp, server, route)
            assert content == files("skatmind.app_web").joinpath(resource).read_bytes()
            item["http_resources"][route] = hashlib.sha256(content).hexdigest()
    finally:
        session_execution.execute = original_session
        match_execution.execute_match_decision_analysis_v1 = original_match


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    output.mkdir()
    hashes = {}
    for resource in MODULES:
        loaded = files("skatmind.app_web").joinpath(resource)
        if args.phase == "before" and not loaded.is_file():
            continue
        content = loaded.read_bytes()
        assert content == (ROOT / "src/skatmind/app_web" / resource).read_bytes(), resource
        hashes[resource] = hashlib.sha256(content).hexdigest()
    evidence = {"baseline": "115c9b8299c93c711a928b8feb2c8f02c919582a", "phase": args.phase,
                "python": sys.version, "package": skatmind.__version__, "hashes": hashes,
                "runs": [], "completed": False}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="localization-test-token")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            cdp = browser.cdp
            item = {"mode": mode, "phase": args.phase, "browser": browser.version,
                    "measurements": [], "actions": {}}
            evidence["runs"].append(item)
            try:
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
                time.sleep(.5)
                entry_layout(cdp, server, output, item)
                if args.phase == "after":
                    cdp.navigate(server.origin + "/review/recorded")
                    recorded_flows(cdp, server, output, item)
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        if args.baseline:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            old = {(r["mode"], row["state"], row["locale"],
                    tuple(row["viewport"]), row["text_scale"]): row
                   for r in baseline["runs"] for row in r["measurements"]}
            evidence["comparisons"] = []
            for r in evidence["runs"]:
                for row in r["measurements"]:
                    prior = old.get((r["mode"], row["state"], row["locale"],
                                     tuple(row["viewport"]), row["text_scale"]))
                    if prior:
                        evidence["comparisons"].append({"mode": r["mode"], "state": row["state"],
                            "locale": row["locale"], "viewport": row["viewport"],
                            "text_scale": row["text_scale"],
                            "height": [prior["height"], row["height"]],
                            "headings": [len(prior["headings"]), len(row["headings"])],
                            "orientation": [prior["orientation"], row["orientation"]],
                            "first_action_top": [
                                value["actions"][0]["top"] if value["actions"] else None
                                for value in (prior, row)]})
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"completed": evidence["completed"], "output": str(output),
                          "measurements": sum(len(r["measurements"]) for r in evidence["runs"]),
                          "comparisons": [r for r in evidence.get("comparisons", [])
                              if r["mode"] == "native" and r["locale"] == "de"
                              and r["text_scale"] == 1 and r["viewport"][0] in {1365, 320}]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    parser.add_argument("--baseline", type=Path)
    run(parser.parse_args())
