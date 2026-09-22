# ruff: noqa: E501 - Browser expressions and evidence selectors stay together.
"""Optional #253 independent-Wheel evidence using genuine returned forms and DevTools."""
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
from verify_analysis_downloads import MEASURE as DOWNLOADS
from verify_analysis_downloads import digest
from verify_candidate_comparisons import MEASURE as CANDIDATES
from verify_unified_workflow_visuals import TEXT_ENLARGEMENT

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_frontend_web import _multipart, _request  # noqa: E402
from test_information_set_search_position_workflow import _position  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profiles  # noqa: E402
import skatmind.app_web.task_first_match_state as match_state  # noqa: E402
import skatmind.capture_web.analysis as match_analysis  # noqa: E402
import skatmind.capture_web.context as match_context  # noqa: E402
from skatmind.app_web.json_transfer import (  # noqa: E402
    canonical_frontend_json_bytes_v1 as canonical,
)
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

PROSE = r"""(() => {
 const root=document.querySelector('.result-presentation')||document.querySelector('#match-review');
 const nodes=[...root.querySelectorAll('dt,dd,p,li,h2,h3')].filter(e=>!e.closest('details'));
 return nodes.map(e=>({tag:e.tagName,text:e.textContent,client:e.clientWidth,scroll:e.scrollWidth,
   box:(()=>{const r=e.getBoundingClientRect();return {x:r.x,right:r.right,width:r.width,height:r.height}})()}));
})()"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("browser", "output", "wheel"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    evidence = {"completed": False, "phase": args.phase, "python": sys.version,
        "package": skatmind.__version__, "wheel": digest(args.wheel.read_bytes()),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "hashes": {}, "pages": [], "actions": [], "downloads": [], "passive": [],
        "limits": ["Headless Edge CSS viewports and doubled computed fonts, not real-device, page zoom, screen-reader or maintainer UAT.",
            "Native method coverage: shared legacy Immediate, selected Match explicit Immediate, imported available Minimax and Information-set Search.",
            "Auto fallback, strict unavailable, defensive timeout, Null and Skat variants have focused tests, not native browser coverage."]}
    for name in ("result_presentation.py", "result_rendering.py", "result_localization.py", "result_immediate.py",
                 "recorded_decision_context_sources.py", "task_first_session_rendering.py", "task_first_match_state.py",
                 "match_report_rendering.py", "candidate_table_rendering.py", "analysis_download_rendering.py",
                 "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json") + (("analysis_explanation.py",) if after else ()):
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = (ROOT / "src/skatmind/app_web" / name).read_bytes() if after else subprocess.check_output(
            ["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT)
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
    fixture = localized_server.__wrapped__(args.output)
    server = next(fixture)
    local = LocalBrowser(args.browser, args.output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    calls, requests = Counter(), Counter()

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
        delta = requests - before
        assert sum(n for p, n in delta.items() if p.startswith("POST ")) == int(route is not None)
        if route:
            assert delta["POST " + route] == 1
        evidence["actions"].append({"selector": selector, "script": not cdp.script_disabled,
            "requests": dict(delta), "calls": dict(calls-work), "focus": cdp.evaluate("document.activeElement.id")})

    def photo(stem, selector):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});scrollBy(0,-15)")
        cdp.screenshot(args.output / (stem + ".png"))

    def download(route, raw, surface):
        link = next(n for n in cdp.evaluate(DOWNLOADS)["links"] if n["href"] == route)
        assert not link["ancestors"]
        destination = args.output / f"download-{len(evidence['downloads']) + 1}"
        destination.mkdir()
        cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(destination.resolve()))
        before = calls.copy()
        action('a[download][href="' + route + '"]')
        for _ in range(100):
            received = set(destination.glob("*.json"))
            if received:
                break
            time.sleep(.1)
        assert len(received) == 1
        saved, = received
        assert saved.read_bytes() == raw and calls == before
        evidence["downloads"].append({"surface": surface, "name": saved.name,
            "script": not cdp.script_disabled, "label": link["text"], **digest(raw)})

    def matrix(surface, path, routes):
        before = calls.copy()
        for locale in ("de", "en"):
            for script in (False, True):
                navigate(path, script)
                action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                for route, raw in routes.items():
                    download(route, raw, surface)
                for width, scale in (((1365, 1), (390, 1), (320, 1), (320, 2)) if locale == "de" and not script else ((390, 1),)):
                    navigate(path, script, width)
                    if scale == 2:
                        cdp.evaluate(TEXT_ENLARGEMENT)
                    row = {"surface": surface, "locale": locale, "script": script, "width": width, "scale": scale,
                           "prose": cdp.evaluate(PROSE), "downloads": cdp.evaluate(DOWNLOADS), "candidates": cdp.evaluate(CANDIDATES)}
                    evidence["pages"].append(row)
                    prose = " ".join(n["text"] for n in row["prose"])
                    if after:
                        assert ("Verwendeter Wissensstand" if locale == "de" else "Information used") in prose
                        assert "Information cutoff mode" not in prose
                        assert "Only information available at the analysis cutoff" not in prose
                        assert all(n["scroll"] <= n["client"] + 1 for n in row["prose"])
                    elif surface == "session" and locale == "en":
                        assert "Information cutoff mode" in prose and "Samples" in prose
                    assert all(g["scroll"] <= g["client"] + 1 for g in row["downloads"]["candidate_geometry"])
                    table = row["candidates"]
                    for cells in table["rows"]:
                        for cell in cells:
                            assert cell["scroll"] <= cell["client"] + 1
                            if cell["label"] and cell["label"]["display"] != "none":
                                assert cell["label"]["box"]["right"] <= cell["box"]["right"] + 1
                            for token in cell["tokens"]:
                                assert all(r["right"] <= cell["box"]["right"] + 1 for r in token["rects"])
                    if baseline:
                        old = next(p for p in baseline["pages"] if all(p[k] == row[k] for k in ("surface", "locale", "script", "width", "scale")))
                        assert row["downloads"]["candidate"] == old["downloads"]["candidate"]
                    stem = f"{surface}-{locale}-{int(script)}-{width}-{scale}"
                    for suffix, selector in (("method", "#result-section-2" if surface != "match" else "#match-review"),
                        ("evidence", "#result-section-4" if surface != "match" else (
                            "#match-review section > dl.result-details:last-of-type" if after else ".recorded-decision-context")),
                        ("candidates", ".candidate-comparison"), ("downloads", ".analysis-downloads")):
                        photo(stem + "-" + suffix, selector)
                    row["accessible_names"] = [n.get("name", {}).get("value") for n in cdp.call("Accessibility.getFullAXTree")["nodes"]]
                    assert all(n["label"] in row["accessible_names"] for n in evidence["downloads"] if n["surface"] == surface and n["script"] == script and n["label"] in [x["text"] for x in row["downloads"]["links"]])
        assert all(calls[k] == before[k] for k in ("session_saves", "match_saves", "executions", "match_executions"))
        evidence["passive"].append({"surface": surface, "calls": dict(calls-before)})

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"), (execution, "execute", "executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (profiles, "save_frontend_profile_file_v1", "profile_saves"),
                (match_state, "_decision_preparation_summary", "match_page_preparations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_" + method, counted_request(method, getattr(Handler, "do_" + method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
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
            photo("native-session-focus", "#session-result")
            for kind in ("keyDown", "keyUp"):
                cdp.call("Input.dispatchKeyEvent", type=kind, key="Tab", windowsVirtualKeyCode=9)
            assert cdp.evaluate("document.activeElement.getAttribute('href')") == "#recorded-decision-12"
            retained = {f"/sessions/downloads/{name}.json": getattr(session.execution, name + "_json_bytes") for name in ("request", "result")}
            sources = {"session": session.path.read_bytes(), "checkpoints": canonical([c.to_dict() for c in session.decision_checkpoints])}
            matrix("session", "/sessions/current", retained)
            before = calls.copy()
            record_context_match(client)
            evidence["match_fixture_calls"] = dict(calls-before)
            match = server.app_context.managed_stateful.active_match
            navigate("/matches/review/1", True)
            action('form:has(input[name="operation"][value="analyze_decision"]) button', "/matches/api/v1/analysis")
            report, = match.capture.report_store.list()
            route = f"/matches/api/v1/reports/{report.report_id}.json"
            raw = client.request("GET", route)[2]
            retained[route] = raw
            sources.update(match=match.path.read_bytes(), report=canonical(report.to_dict()))
            matrix("match", f"/matches/reports/{report.report_id}", {route: raw})
            for surface, area, request in (("minimax", "analyze", json.loads((ROOT / "examples/grand_bounded_search_exhaustive.json").read_text())),
                                           ("information_set", "review", _position(post_game=True))):
                form = Forms(client.page('/' + area)).find(f"/actions/{area}/import-json")
                body, kind = _multipart(canonical(request), revision=int(form["values"]["revision"]))
                follow(client, _request(server, "POST", form["action"], body=body, headers={"Cookie": client.cookie, "Origin": server.origin, "Content-Type": kind}))
                navigate('/' + area)
                action(f'form[action="/actions/{area}/run-imported"] button', f"/actions/{area}/run-imported")
                group = {f"/downloads/{area}/{name}.json": client.request("GET", f"/downloads/{area}/{name}.json")[2] for name in ("request", "result")}
                retained.update(group)
                matrix(surface, '/' + area, group)
            for route, raw in retained.items():
                assert client.request("GET", route)[2] == raw
            assert session.path.read_bytes() == sources["session"] and match.path.read_bytes() == sources["match"]
            assert canonical([c.to_dict() for c in session.decision_checkpoints]) == sources["checkpoints"]
            assert canonical(report.to_dict()) == sources["report"]
            evidence["sources"] = {k: digest(v) for k, v in sources.items()}
            evidence["retained"] = {k: digest(v) for k, v in retained.items()}
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
