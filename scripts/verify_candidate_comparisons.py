# ruff: noqa: E501 - Keep browser expressions and evidence selectors legible.
"""Optional #251 installed-Wheel evidence; real HTTP sources, dependency-free DevTools."""
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

from test_frontend_language_switching import localized_server  # noqa: E402
from test_guided_frontend_web import _multipart, _request  # noqa: E402
from test_match_recording_recovery_web import follow  # noqa: E402
from test_recorded_decision_context import MATCH_HAND, SESSION_HAND, assert_context  # noqa: E402
from test_recorded_decision_context_web import record_context_match  # noqa: E402
from test_recorded_review_navigation import chooser_form, home_chooser  # noqa: E402
from test_session_recorded_review_web import Browser, Forms, record_score_review_game  # noqa: E402

import skatmind  # noqa: E402
import skatmind.api.v1.session.files as session_files  # noqa: E402
import skatmind.app_web.execution as execution  # noqa: E402
import skatmind.app_web.frontend_profile_operations as profile_operations  # noqa: E402
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
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler  # noqa: E402
from skatmind.session_transitions import replay_session_state_v1  # noqa: E402

TABLE = '.result-table-wrap table, .workflow-table-scroll table'
MEASURE = r"""(() => {
 const table=document.querySelector('.result-table-wrap table, .workflow-table-scroll table'),wrap=table.parentElement;
 const box=e=>{const r=e.getBoundingClientRect();return {x:r.x,right:r.right,width:r.width,height:r.height}};
 const text=e=>{const walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT),parts=[];let n;
   while(n=walker.nextNode()){if(n.parentElement.closest('[aria-hidden="true"]'))continue;
   const re=/\S+/g;let m;while(m=re.exec(n.textContent)){const r=document.createRange();r.setStart(n,m.index);r.setEnd(n,m.index+m[0].length);
       parts.push({text:m[0],rects:[...r.getClientRects()].map(x=>({x:x.x,right:x.right,width:x.width,height:x.height}))});}}
   return parts;};
 const rows=[...table.tBodies[0].rows].map(r=>[...r.cells].map(c=>{
   const value=c.querySelector('.candidate-value')||c,label=c.querySelector('.candidate-label'),s=getComputedStyle(c);
   return {value:value.textContent,box:box(c),content:box(value),tokens:text(value),font:s.fontSize,display:s.display,
     scroll:c.scrollWidth,client:c.clientWidth,label:label?{text:label.textContent,box:box(label),display:getComputedStyle(label).display}:null,
     headers:c.getAttribute('headers'),scope:c.scope,faces:[...c.querySelectorAll('.card-face')].map(f=>({box:box(f),font:getComputedStyle(f).fontSize,color:getComputedStyle(f).color,forced:getComputedStyle(f).forcedColorAdjust,scroll:f.scrollWidth,client:f.clientWidth}))};}));
 const focus=document.activeElement,fs=getComputedStyle(focus);
 const faces=[...document.querySelectorAll('.recorded-decision-context .card-face')].map(f=>({box:box(f),parent:box(f.parentElement),font:getComputedStyle(f).fontSize,color:getComputedStyle(f).color,forced:getComputedStyle(f).forcedColorAdjust}));
 return {page:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,wrap:{...box(wrap),scroll:wrap.scrollWidth,client:wrap.clientWidth},table:box(table),
   faces,caption:{text:table.caption.textContent,box:box(table.caption),scroll:table.caption.scrollWidth,client:table.caption.clientWidth},
   columns:[...table.tHead.rows[0].cells].map(c=>c.textContent),
   column_geometry:[...table.tHead.rows[0].cells].map(c=>({box:box(c),tokens:text(c)})),rows,
   ancestors:[wrap,wrap.parentElement,wrap.parentElement.parentElement].map(e=>({tag:e.tagName,classes:e.className,box:box(e),overflow:getComputedStyle(e).overflow})),
   focus:{id:focus.id,tag:focus.tagName,href:focus.getAttribute('href'),outline:fs.outline,offset:fs.outlineOffset},
   ids:[...document.querySelectorAll('[id]')].map(e=>e.id)};
})()"""


def digest(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    assert args.output.parent.is_dir() and not args.output.exists()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT)
    args.output.mkdir()
    after = args.phase == "after"
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    if baseline:
        assert baseline["completed"] and baseline["phase"] == "before"
    evidence = {"completed": False, "phase": args.phase, "python": sys.version, "package": skatmind.__version__,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "wheel": digest(args.wheel.read_bytes()), "hashes": {}, "pages": [], "actions": [], "passive": [],
        "registry": [len(UNIFIED_FRONTEND_POST_ROUTES), len(FRONTEND_FORM_REGISTRY)],
        "limits": ["Headless Chromium/Edge, not physical-device, screen-reader or maintainer UAT.",
            "Device metrics set CSS viewport at scale 1. Doubled computed fonts are text enlargement, not actual page zoom.",
            "Local-parent constraint and forced-colors are explicit emulations. No whole-app accessibility claim."]}
    names = ["result_rendering.py", "result_presentation.py", "result_localization.py", "result_immediate.py",
        "match_report_rendering.py", "recorded_decision_context_rendering.py", "compact_card_rendering.py",
        "assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json"]
    if after:
        names.append("candidate_table_rendering.py")
    for name in names:
        raw = (Path(skatmind.__file__).parent / "app_web" / name).read_bytes()
        expected = ((ROOT / "src/skatmind/app_web" / name).read_bytes() if after else
            subprocess.check_output(["git", "show", "HEAD:src/skatmind/app_web/" + name], cwd=ROOT))
        assert raw.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n"), name
        evidence["hashes"][name] = digest(raw)
        if name.startswith("locales/"):
            evidence.setdefault("catalog_counts", {})[name] = len(json.loads(raw))
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

    def request_count(method, real):
        def wrapped(handler):
            requests[method + " " + handler.path.split("?", 1)[0]] += 1
            return real(handler)
        return wrapped

    def navigate(path, script):
        cdp.call("Emulation.setScriptExecutionDisabled", value=not script)
        cdp.navigate("about:blank")
        cdp.navigate(server.origin + path)
        cdp.call("Page.bringToFront")

    def key(name, number):
        for kind in ("keyDown", "keyUp"):
            cdp.call("Input.dispatchKeyEvent", type=kind, key=name, windowsVirtualKeyCode=number)

    def action(selector, route=None):
        before, work = requests.copy(), calls.copy()
        cdp.activate(selector)
        assert sum(n for p, n in (requests-before).items() if p.startswith("POST ")) == int(route is not None)
        if route:
            assert (requests-before)["POST " + route] == 1
        evidence["actions"].append({"selector": selector, "javascript": not cdp.script_disabled,
            "requests": dict(requests-before), "calls": dict(calls-work), "focus": cdp.evaluate("document.activeElement.id")})

    def viewport(width):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900 if width == 1365 else 844, deviceScaleFactor=1, mobile=False)

    def photo(stem, selector=TABLE):
        cdp.evaluate("document.querySelector(" + json.dumps(selector) + ").scrollIntoView({block:'start'});scrollBy(0,-15)")
        cdp.screenshot(args.output / (stem + ".png"))

    def measure(surface, locale, script, width, scale, *, parent=False, forced=False):
        row = cdp.evaluate(MEASURE)
        row.update(surface=surface, locale=locale, javascript=script, width=width, text_scale=scale, narrow_parent=parent, forced=forced)
        ax = cdp.call("Accessibility.getFullAXTree")["nodes"]
        table_nodes = [n for n in ax if n.get("role", {}).get("value") == "table"]
        nodes = {n["nodeId"]: n for n in ax}
        descendants = []
        def collect(node):
            descendants.append(node)
            for child in node.get("childIds", []):
                collect(nodes[child])
        assert len(table_nodes) == 1, table_nodes
        collect(table_nodes[0])
        row["ax_roles"] = dict(Counter(n.get("role", {}).get("value") for n in descendants if not n.get("ignored")))
        row["ax_table_name"] = table_nodes[0].get("name", {}).get("value")
        matrix = {"columns": row["columns"], "rows": [[c["value"] for c in r] for r in row["rows"]]}
        prior = evidence.setdefault("matrices", {}).setdefault(surface + "-" + locale, matrix)
        assert matrix == prior
        if baseline:
            expected = next(p for p in baseline["pages"] if p["surface"] == surface and p["locale"] == locale)
            assert matrix == {"columns": expected["columns"], "rows": [[c["value"] for c in r] for r in expected["rows"]]}
        evidence["pages"].append(row)
        stem = f"{surface}-{locale}-{int(script)}-{width}-{scale}" + ("-parent" if parent else "") + ("-forced" if forced else "")
        (args.output / (stem + "-ax.json")).write_text(json.dumps(descendants, indent=2), encoding="utf-8")
        (args.output / (stem + ".html")).write_text(cdp.evaluate("document.querySelector(" + json.dumps(TABLE) + ").outerHTML"), encoding="utf-8")
        if after:
            assert len(row["ids"]) == len(set(row["ids"]))
            assert row["wrap"]["scroll"] <= row["wrap"]["client"] + 1, row
            assert row["table"]["right"] <= row["wrap"]["right"] + 1
            assert row["caption"]["scroll"] <= row["caption"]["client"] + 1
            assert row["ax_roles"]["columnheader"] == len(row["columns"])
            assert row["ax_roles"]["rowheader"] == len(row["rows"])
            assert row["ax_roles"]["cell"] == len(row["rows"]) * (len(row["columns"])-1)
            assert row["ax_roles"]["StaticText"] == 1 + len(row["columns"]) * (1 + len(row["rows"]))
            for face in row["faces"]:
                assert face["box"]["width"] > 0 and face["box"]["height"] > 0
                assert face["parent"]["x"] <= face["box"]["x"] < face["box"]["right"] <= face["parent"]["right"]
                assert face["forced"] == "auto"
            for cells in row["rows"]:
                for cell in cells:
                    assert cell["scroll"] <= cell["client"] + 1, cell
                    assert float(cell["font"][:-2]) >= 16 * scale
                    for token in cell["tokens"]:
                        assert len(token["rects"]) == 1, token
                        assert token["rects"][0]["right"] <= cell["box"]["right"] + 1, token
                        assert token["rects"][0]["x"] >= cell["box"]["x"] - 1, token
                    for face in cell["faces"]:
                        assert face["box"]["right"] <= cell["box"]["right"] + 1
                    if cell["label"] and cell["label"]["display"] != "none":
                        assert cell["label"]["box"]["width"] >= min(8 * 16 * scale, cell["box"]["width"] - 2 - 16 * scale), cell
            if width <= 390 or parent or scale == 2:
                assert row["rows"][0][0]["display"] == "block"
            else:
                assert row["rows"][0][0]["display"] == "table-cell"
                for column in row["column_geometry"][:2]:
                    assert all(len(t["rects"]) == 1 for t in column["tokens"]), column
        photo(stem)
        photo(stem + "-last", '.result-table-wrap tbody tr:last-child td:last-child, .workflow-table-scroll tbody tr:last-child td:last-child')
        if surface in ("session", "match") and locale == "de" and not script and width == 320 and scale == 2:
            photo(stem + "-context", ".recorded-decision-context")
            photo(stem + "-faces", ".decision-context-hand")
        return row

    def responsive(surface, path):
        before = calls.copy()
        for locale in ("de", "en"):
            for script in (False, True):
                viewport(1365)
                navigate(path, script)
                action('form.language-selector button[value="' + locale + '"]', "/actions/profile/language")
                for width, scale in (((1365, 1), (390, 1), (320, 1), (320, 2), (1365, 2)) if locale == "de" and not script else ((390, 1), (320, 2))):
                    viewport(width)
                    navigate(path, script)
                    if scale == 2:
                        cdp.evaluate(TEXT_ENLARGEMENT)
                    measure(surface, locale, script, width, scale)
                viewport(1365)
                navigate(path, script)
        # Same retained DOM narrow -> wide -> narrow, with the native named focus target.
        viewport(320)
        target = "#session-result" if surface == "session" else ".workflow-table-scroll" if surface == "match" else "#result-section-3"
        cdp.evaluate("window.probeRows=[...document.querySelectorAll('tbody tr')];window.probeFocus=document.querySelector(" + json.dumps(target) + ");probeFocus.focus()")
        start, work = requests.copy(), calls.copy()
        for width in (320, 1365, 320):
            viewport(width)
            assert cdp.evaluate("probeRows.every((r,i)=>r===document.querySelectorAll('tbody tr')[i])")
            if surface != "search":
                assert cdp.evaluate("document.activeElement===probeFocus")
        assert requests == start and calls == work
        evidence["passive"].append({"surface": surface, "resize_requests": dict(requests-start), "resize_calls": dict(calls-work), "row_identity": True})
        # A genuine installed page in a constrained parent at a wide CSS viewport.
        viewport(1365)
        cdp.evaluate("document.querySelector(" + json.dumps(TABLE) + ").parentElement.parentElement.style.maxWidth='20em'")
        measure(surface, "en", True, 1365, 1, parent=True)
        cdp.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        measure(surface, "en", True, 1365, 1, parent=True, forced=True)
        cdp.call("Emulation.setEmulatedMedia", features=[])
        if surface == "match":
            key("Tab", 9)
            # #252 places the native Result download ahead of technical details.
            expected_tag = "A" if cdp.evaluate("!!document.querySelector('.analysis-downloads')") else "SUMMARY"
            assert cdp.evaluate("document.activeElement.tagName") == expected_tag
            evidence["actions"].append({"native_tab_from_match_wrapper": expected_tag, "requests": dict(requests-start)})
        assert calls["session_saves"] == before["session_saves"] and calls["match_saves"] == before["match_saves"]
        assert calls["executions"] == before["executions"] and calls["match_executions"] == before["match_executions"]
        evidence["passive"].append({"surface": surface, "views_and_language_calls": dict(calls-before)})

    try:
        with ExitStack() as stack:
            for module, name, label in ((session_files, "save_session_file", "session_saves"),
                (match_context, "save_match_workspace_file_v1", "match_saves"), (execution, "execute", "executions"),
                (match_analysis, "execute_match_decision_analysis_v1", "match_executions"),
                (profile_operations, "save_frontend_profile_file_v1", "profile_saves"),
                (match_state, "_decision_preparation_summary", "match_page_preparations")):
                stack.enter_context(patch.object(module, name, counted(label, getattr(module, name))))
            for method in ("GET", "POST"):
                stack.enter_context(patch.object(Handler, "do_"+method, request_count(method, getattr(Handler, "do_"+method))))
            client = Browser(server)
            cdp.call("Network.setCookie", name=client.cookie.split("=", 1)[0], value=client.cookie.split("=", 1)[1], url=server.origin, httpOnly=True, sameSite="Strict")
            assert digest(client.request("GET", "/assets/app.css")[2]) == evidence["hashes"]["assets/app.css"]
            plays = record_score_review_game(client, play_count=18)
            source = server.app_context.managed_stateful.active_session
            assert replay_session_state_v1(source.state).remaining_hand_for(source.state.local_player_id) == ("C10", "CJ", "DK", "D7")
            for play in plays[18:27]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            assert replay_session_state_v1(source.state).remaining_hand_for(source.state.local_player_id) == ("CJ",)
            for play in plays[27:]:
                follow(client, client.submit(Forms(client.page()).find("/sessions/play"), cards=play["card"]))
            client.command("set_game_end")
            viewport(1365)
            navigate("/sessions/current", False)
            action('#recorded-decision-12 + button', "/sessions/review-decision")
            assert cdp.evaluate("document.activeElement.id") == "session-result"
            photo("session-native-result-focus", "#session-result")
            key("Tab", 9)
            assert cdp.evaluate("document.activeElement.getAttribute('href')") == "#recorded-decision-12"
            key("Enter", 13)
            assert cdp.evaluate("location.hash") == "#recorded-decision-12"
            retained = {f"/sessions/downloads/{name}.json": client.request("GET", f"/sessions/downloads/{name}.json")[2] for name in ("session", "request", "result")}
            session_raw = source.path.read_bytes()
            checkpoint_bytes = canonical([c.to_dict() for c in source.decision_checkpoints])
            result = source.execution.result.result.document
            assert result["position"]["hand"] == SESSION_HAND and result["position"]["current_trick"] == ("HJ", "DJ")
            assert [r["card"] for r in result["analysis_report"]] == ["CJ", "SJ"]
            assert result["score_summary"]["total_declarer_points"] == 14 and result["score_summary"]["total_defender_points"] == 29
            responsive("session", "/sessions/current")
            page = follow(client, client.submit(chooser_form(home_chooser(client), "sessions")))
            assert_context(page, "en", hand=SESSION_HAND, prefix=(("B", "HJ"), ("C", "DJ")), actor="A", trick=4, play=3)
            # One representative #250 no-op Preview/Cancel, retaining the same real review.
            navigate("/sessions/current", True)
            action('.accepted-declaration form[action="/sessions/declaration-correction/select"]:last-of-type button', "/sessions/declaration-correction/select")
            action('form[action="/sessions/declaration-correction/preview"] button[type="submit"]', "/sessions/declaration-correction/preview")
            assert source.execution is not None
            photo("session-preview-retained", "#session-declaration-correction")
            action('form[action="/sessions/declaration-correction/cancel"] button', "/sessions/declaration-correction/cancel")
            assert source.path.read_bytes() == session_raw and canonical([c.to_dict() for c in source.decision_checkpoints]) == checkpoint_bytes
            record_context_match(client)
            match = server.app_context.managed_stateful.active_match
            navigate("/matches/review/1", True)
            action('form:has(input[name="operation"][value="analyze_decision"]) button', "/matches/api/v1/analysis")
            report, = match.capture.report_store.list()
            report_raw, match_raw = canonical(report.to_dict()), match.path.read_bytes()
            path = f"/matches/reports/{report.report_id}"
            download = f"/matches/api/v1/reports/{report.report_id}.json"
            retained[download] = client.request("GET", download)[2]
            evidence["match_candidates"] = report.value.result.to_dict()["document"]["analysis_report"]
            responsive("match", path)
            client.page("/matches/position/2")
            assert_context(client.page(path), "en", hand=MATCH_HAND, prefix=(("B", "CK"),), actor="C", trick=1, play=2, game=1)
            for route in ("/matches/position/1", "/matches/review/1"):
                # These current routes link to Reports; only the explicit Report route selects one.
                assert f'href="{path}"' in client.page(route)
            # A real available bounded Search, through explicit JSON import and returned Run.
            request = (ROOT / "examples/grand_bounded_search_exhaustive.json").read_bytes()
            body, content_type = _multipart(request, revision=0)
            response = _request(server, "POST", "/actions/analyze/import-json", body=body,
                headers={"Cookie": client.cookie, "Origin": server.origin, "Content-Type": content_type})
            assert response[0] == 303
            navigate("/analyze", False)
            action('form[action="/actions/analyze/run-imported"] button', "/actions/analyze/run-imported")
            for name in ("request", "result"):
                route = f"/downloads/analyze/{name}.json"
                retained[route] = client.request("GET", route)[2]
            search_document = json.loads(retained["/downloads/analyze/result.json"])["document"]
            assert search_document["bounded_search_result"]["status"] == "complete"
            evidence["search_candidates"] = search_document["bounded_search_result"]["candidate_results"]
            responsive("search", "/analyze")
            # Native browser downloads reuse exact retained bytes, including this timed execution.
            cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(args.output.resolve()))
            for route, raw in retained.items():
                page = "/sessions/current" if route.startswith("/sessions/") else path if route.startswith("/matches/") else "/analyze"
                navigate(page, False)
                selector = 'a[download][href="' + route + '"]'
                # Disclosure expansion is fixture navigation; activation is native keyboard Enter.
                cdp.evaluate("(()=>{for(let p=document.querySelector(" + json.dumps(selector) + ").parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true})()")
                existing = set(args.output.glob("*.json"))
                action(selector)
                for _ in range(100):
                    received = set(args.output.glob("*.json")) - existing
                    if received:
                        break
                    time.sleep(.1)
                assert len(received) == 1, route
                downloaded, = received
                assert downloaded.read_bytes() == raw, route
                evidence.setdefault("native_downloads", {})[route] = digest(raw)
            for route, raw in retained.items():
                assert client.request("GET", route)[2] == raw, route
            assert source.path.read_bytes() == session_raw and match.path.read_bytes() == match_raw
            assert canonical(report.to_dict()) == report_raw
            evidence["retained"] = {route: digest(raw) for route, raw in retained.items()}
            evidence["source_bytes"] = {"session": digest(session_raw), "checkpoints": digest(checkpoint_bytes), "match": digest(match_raw), "report": digest(report_raw)}
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
