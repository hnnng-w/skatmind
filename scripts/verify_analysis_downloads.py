# ruff: noqa: E501
"""Optional #252 independent-Wheel browser evidence over real returned forms."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_analysis_download_details import download_nodes, import_example  # noqa: E402
from test_frontend_language_switching import localized_server  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_recorded_review_navigation import chooser_form, home_chooser  # noqa: E402
from test_session_recorded_review_web import Browser, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profiles  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.form_registry import (  # noqa: E402
    FRONTEND_FORM_REGISTRY,
    UNIFIED_FRONTEND_POST_ROUTES,
)
from skatmind.app_web.json_transfer import (  # noqa: E402
    canonical_frontend_json_bytes_v1 as canonical,
)
from skatmind.app_web.result_presentation import build_result_presentation_v1  # noqa: E402
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

MEASURE = r"""(() => {
 const box=e=>{let r=e.getBoundingClientRect();return {x:r.x,right:r.right,width:r.width,height:r.height}};
 const ancestors=e=>{let a=[];for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')a.push(p.querySelector('summary').textContent);return a};
 const links=[...document.querySelectorAll('a[download]')].map(e=>({href:e.getAttribute('href'),text:e.textContent,ancestors:ancestors(e),box:box(e),parent:box(e.parentElement),font:getComputedStyle(e).fontSize,color:getComputedStyle(e).color,background:getComputedStyle(e).backgroundColor}));
 const details=[...document.querySelectorAll('details')].map(e=>({summary:e.querySelector('summary').textContent,ancestors:ancestors(e),open:e.open}));
 const technical=document.querySelector('#result-section-5')?.closest('details') || document.querySelector('#result-section-5')?.parentElement.querySelector('details') || document.querySelector('#match-review .technical-details');
 const focus=document.activeElement,s=getComputedStyle(focus);
 return {links,details,technical:technical?{text:technical.textContent,box:box(technical),scroll:technical.scrollWidth,client:technical.clientWidth}:null,
   groups:document.querySelectorAll('.analysis-downloads').length,
   candidate:[...document.querySelectorAll('.candidate-table tbody tr')].map(r=>[...r.cells].map(c=>(c.querySelector('.candidate-value')||c).textContent)),
   candidate_geometry:[...document.querySelectorAll('.candidate-comparison')].map(e=>({box:box(e),client:e.clientWidth,scroll:e.scrollWidth})),
   focus:{id:focus.id,tag:focus.tagName,href:focus.getAttribute('href'),outline:s.outline,offset:s.outlineOffset}};
})()"""


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("browser", "output", "wheel"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel": digest(args.wheel.read_bytes()),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "hashes": {}, "pages": [], "actions": [], "downloads": [], "passive": [],
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "limits": ["Headless Edge CSS viewport emulation, not device, screen-reader or maintainer UAT.",
            "200% text doubles computed fonts, not browser zoom. Full-page form/Historical-table redesign is excluded."]}
    names = ("result_rendering.py", "result_presentation.py", "result_localization.py", "guided_rendering.py",
        "task_first_rendering.py", "task_first_session_rendering.py", "task_first_match_rendering.py",
        "match_report_rendering.py", "candidate_table_rendering.py", "workflow_state.py",
        "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json")
    for name in names + (("analysis_download_rendering.py",) if after else ()):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = (ROOT / "src/skatmind/app_web" / name).read_bytes() if after else subprocess.check_output(
            ["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT)
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
        if name.startswith("locales/"):
            evidence.setdefault("catalog_counts", {})[name] = len(json.loads(raw))
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    calls, requests = Counter(), Counter()
    evidence["browser"] = local.version

    def counted(label, real):
        def wrapped(*a, **kw):
            calls[label] += 1
            return real(*a, **kw)
        return wrapped

    def counted_request(method, real):
        def wrapped(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return wrapped

    def navigate(path, script=False, width=1365):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844, deviceScaleFactor=1, mobile=False)
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def action(selector, route=None):
        before, work = requests.copy(), calls.copy()
        cdp.activate(selector)
        assert sum(n for p, n in (requests-before).items() if p.startswith("POST ")) == int(route is not None)
        if route:
            assert (requests-before)["POST " + route] == 1
        evidence["actions"].append({"selector": selector, "script": not cdp.script_disabled,
            "requests": dict(requests-before), "calls": dict(calls-work),
            "focus": cdp.evaluate("document.activeElement.id")})

    def key(name, number):
        for kind in ("keyDown", "keyUp"):
            cdp.call("Input.dispatchKeyEvent", type=kind, key=name, windowsVirtualKeyCode=number)

    def photo(stem, selector):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});scrollBy(0,-15)")
        cdp.screenshot(args.output / (stem + ".png"))

    def native_download(route, expected, *, surface):
        selector = 'a[download][href="' + route + '"]'
        nodes = cdp.evaluate(MEASURE)["links"]
        link = next(n for n in nodes if n["href"] == route)
        if after:
            assert not link["ancestors"], link
        elif link["ancestors"]:
            # Baseline limitation only: open its actual native ancestors before activation.
            cdp.evaluate("(()=>{for(let p=document.querySelector(" + json.dumps(selector) + ").parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true})()")
        destination = args.output / f"download-{len(evidence['downloads']) + 1}"
        destination.mkdir()
        cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
        before = calls.copy()
        action(selector)
        for _ in range(100):
            received = set(destination.glob("*.json"))
            if received:
                break
            time.sleep(.1)
        assert len(received) == 1, route
        saved, = received
        assert saved.read_bytes() == expected
        assert calls == before
        evidence["downloads"].append({"surface": surface, "filename": saved.name,
            "ancestor_count": len(link["ancestors"]), "script": not cdp.script_disabled,
            "accessible_name": link["text"], **digest(expected)})

    def matrix(surface, path, routes):
        before = calls.copy()
        technical = '#result-section-5' if surface != "match" else '#match-review .technical-details > summary'
        for locale in ("de", "en"):
            for script in (False, True):
                navigate(path, script)
                action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                # Native activation from a returned Result with details still closed.
                for route, raw in routes.items():
                    native_download(route, raw, surface=surface)
                for width, scale in (((1365, 1), (390, 1), (320, 1), (320, 2))
                                     if locale == "de" and not script else ((390, 1),)):
                    navigate(path, script, width)
                    if scale == 2:
                        cdp.evaluate(TEXT_ENLARGEMENT)
                    row = cdp.evaluate(MEASURE)
                    row.update(surface=surface, locale=locale, script=script, width=width, scale=scale)
                    evidence["pages"].append(row)
                    selected = [n for n in row["links"] if n["href"] in routes]
                    if after:
                        assert row["groups"] == 1 and len(selected) == len(routes)
                        assert all(not n["ancestors"] for n in selected)
                        assert all(n["box"]["width"] > 0 and n["box"]["height"] > 0
                                   and n["box"]["right"] <= n["parent"]["right"] + 1 for n in selected)
                        assert all(g["scroll"] <= g["client"] + 1 for g in row["candidate_geometry"])
                    stem = f"{surface}-{locale}-{int(script)}-{width}-{scale}"
                    photo(stem + "-downloads", ".analysis-downloads" if after else (
                        '#result-section-5' if surface != "match" else selector_for_first(routes)))
                    if surface == "session" and scale == 2:
                        photo(stem + "-candidates", ".candidate-comparison")
                    # Open exactly the analysis disclosure with native keyboard activation.
                    if after:
                        action(technical)
                    else:
                        action('#result-section-5 + details > summary' if surface != "match" else technical)
                    row["opened"] = cdp.evaluate(MEASURE)["technical"]
                    if after:
                        assert row["opened"]["scroll"] <= row["opened"]["client"] + 1
                    photo(stem + "-technical", technical)
                    ax = cdp.call("Accessibility.getFullAXTree")["nodes"]
                    row["accessible_downloads"] = [n.get("name", {}).get("value") for n in ax
                        if n.get("role", {}).get("value") == "link" and "JSON" in n.get("name", {}).get("value", "")]
                    if after:
                        assert all(n["text"] in row["accessible_downloads"] for n in selected)
                    if surface == "session" and locale == "en" and not script:
                        row["policy_occurrences"] = {scope: row["opened"]["text"].count(scope + " fixed policy")
                                                     for scope in ("General", "Left", "Right")}
                        if after:
                            assert list(row["policy_occurrences"].values()) == [1, 1, 1]
                        photo(stem + "-policies", '.analysis-technical dl:last-of-type' if after else '#result-section-5 + details dl:last-of-type')
                # Script-enabled same-source restoration retains the opened analysis region.
                if script and after:
                    action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                    assert any(d["open"] and d["summary"] in {"Technical analysis details", "Technische Analysedetails"}
                               for d in cdp.evaluate(MEASURE)["details"])
        assert all(calls[k] == before[k] for k in ("session_saves", "match_saves", "executions", "match_executions"))
        evidence["passive"].append({"surface": surface, "calls": dict(calls-before)})

    def selector_for_first(routes):
        return 'a[download][href="' + next(iter(routes)) + '"]'

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"), (execution, "execute", "executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (profiles, "save_frontend_profile_file_v1", "profile_saves"),
                (match_state, "_decision_preparation_summary", "match_page_preparations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_"+method, counted_request(method, getattr(Handler, "do_"+method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(args.output.resolve()))
            assert digest(client.request("GET", "/assets/app.css")[2]) == evidence["hashes"]["assets/app.css"]
            plays = record_score_review_game(client, play_count=18)
            session = server.app_context.managed_stateful.active_session
            assert replay_session_state_v1(session.state).remaining_hand_for(session.state.local_player_id) == ("C10", "CJ", "DK", "D7")
            for play in plays[18:27]:
                client.command("record_play", card=play["card"])
            assert replay_session_state_v1(session.state).remaining_hand_for(session.state.local_player_id) == ("CJ",)
            for play in plays[27:]:
                client.command("record_play", card=play["card"])
            client.command("set_game_end")
            evidence["session_fixture_calls"] = dict(calls)
            navigate("/sessions/current")
            action('#recorded-decision-12 + button', "/sessions/review-decision")
            assert cdp.evaluate("document.activeElement.id") == "session-result"
            photo("session-native-focus", "#session-result")
            key("Tab", 9)
            assert cdp.evaluate("document.activeElement.getAttribute('href')") == "#recorded-decision-12"
            key("Enter", 13)
            execution_value = session.execution
            sources = {"session": session.path.read_bytes(), "checkpoints": canonical([c.to_dict() for c in session.decision_checkpoints])}
            retained = {f"/sessions/downloads/{name}.json": getattr(execution_value, name + "_json_bytes") for name in ("request", "result")}
            projection = build_result_presentation_v1(execution_value.result)
            evidence["policy_projection"] = [d.label for s in projection.sections for d in s.details if "fixed policy" in d.label]
            evidence["baseline_session_links"] = [{"href": n["attrs"]["href"], "details": sum(p["tag"] == "details" for p in n["parents"])} for n in download_nodes(client.page())]
            matrix("session", "/sessions/current", retained)
            follow(client, client.submit(chooser_form(home_chooser(client), "sessions")))
            assert session.execution is execution_value
            navigate("/sessions/current", True)
            action('.accepted-declaration form[action="/sessions/declaration-correction/select"]:last-of-type button', "/sessions/declaration-correction/select")
            action('form[action="/sessions/declaration-correction/preview"] button[type="submit"]', "/sessions/declaration-correction/preview")
            assert session.execution is execution_value
            photo("session-preview", "#session-declaration-correction")
            action('form[action="/sessions/declaration-correction/cancel"] button', "/sessions/declaration-correction/cancel")
            assert session.execution is execution_value
            before = calls.copy()
            record_context_match(client)
            evidence["match_fixture_calls"] = dict(calls-before)
            match = server.app_context.managed_stateful.active_match
            navigate("/matches/review/1", True)
            action('form:has(input[name="operation"][value="analyze_decision"]) button', "/matches/api/v1/analysis")
            report, = match.capture.report_store.list()
            path = f"/matches/reports/{report.report_id}"
            route = f"/matches/api/v1/reports/{report.report_id}.json"
            raw = client.request("GET", route)[2]
            retained[route] = raw
            sources.update(match=match.path.read_bytes(), report=canonical(report.to_dict()))
            matrix("match", path, {route: raw})
            client.page("/matches/position/2")
            navigate(path, True)
            assert next(n for n in cdp.evaluate(MEASURE)["links"] if n["href"] == route)
            # The Report still owns Game 1's pre-Card situation, not selected Game 2.
            assert cdp.evaluate("document.querySelector('.recorded-decision-context').textContent.includes('1')")
            for area, example in (("analyze", "grand_bounded_search_exhaustive.json"), ("review", "historical_grand_normal_completion.json")):
                follow(client, import_example(client, area, example))
                navigate("/" + area)
                row = cdp.evaluate(MEASURE)
                evidence.setdefault("import_only", {})[area] = row
                assert len(row["links"]) == 1 and row["technical"] is None
                request_route = f"/downloads/{area}/request.json"
                native_download(request_route, client.request("GET", request_route)[2], surface=area + "-import")
                photo(area + "-import", ".import-summary")
                action(f'form[action="/actions/{area}/run-imported"] button', f"/actions/{area}/run-imported")
                group = {f"/downloads/{area}/{name}.json": client.request("GET", f"/downloads/{area}/{name}.json")[2] for name in ("request", "result")}
                retained.update(group)
                matrix(area, "/" + area, group)
            for route, raw in retained.items():
                assert client.request("GET", route)[2] == raw
            assert session.path.read_bytes() == sources["session"] and match.path.read_bytes() == sources["match"]
            assert canonical([c.to_dict() for c in session.decision_checkpoints]) == sources["checkpoints"]
            assert canonical(report.to_dict()) == sources["report"]
            evidence["retained"] = {k: digest(v) for k, v in retained.items()}
            evidence["sources"] = {k: digest(v) for k, v in sources.items()}
            evidence["completed"] = True
    finally:
        evidence["calls"], evidence["requests"] = dict(calls), dict(requests)
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
        local.close()
        try:
            next(fixture)
        except StopIteration:
            pass
    print(json.dumps({"completed": evidence["completed"], "pages": len(evidence["pages"]), "calls": dict(calls)}, indent=2))


if __name__ == "__main__":
    main()
