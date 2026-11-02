"""Bounded S3 source-tree probe: synthetic data, native operation and real restart."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, focus
from verify_saved_match_analyses import (
    ROOT,
    SAVED,
    TOKEN,
    ProbeServer,
    native_enter,
    request,
    switch_language,
    wait,
)

FORM = 'form[action="/matches/review-whole-game"]'


def serve(home):
    import skatmind
    import skatmind.application.execution as executor
    import skatmind.automatic_learning_io as io
    import skatmind.recommendation_workflow as workflow
    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.managed_data import prepare_managed_home_v1
    from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1

    assert Path(skatmind.__file__).resolve().is_relative_to(ROOT / "src")
    context = AppWebContextV1.create(prepare_managed_home_v1(home))
    counts = Counter()
    controls = {"failure": False, "cancelled": False, "allow_execution": False}
    real_write = io.write_temporary
    real_execute = executor.execute_application_invocation
    real_evaluate = workflow.evaluate_whole_game_rollout_v1

    def write(directory, raw):
        if not controls["allow_execution"] and not controls.get("allow_save"):
            raise AssertionError("Passive archive write")
        if directory.name == "reports" and controls["failure"]:
            counts["controlled_failure"] += 1
            raise OSError("Controlled reports-only interruption")
        value = real_write(directory, raw)
        counts["write_" + directory.name] += 1
        return value

    def execute(*args, **kwargs):
        assert controls["allow_execution"], "Passive or save-only execution"
        counts["execute"] += 1
        return real_execute(*args, **kwargs)

    def evaluate(view, settings):
        assert controls["allow_execution"], "Passive or save-only evaluation"
        counts["evaluate"] += 1
        return real_evaluate(view, settings,
            **({"cancelled": lambda: True} if controls["cancelled"] else {}))

    def forbidden(*args, **kwargs):
        counts["learning_preparation"] += 1
        raise AssertionError("S3 must not prepare Learning artifacts")

    with (patch.object(io, "write_temporary", write),
          patch.object(executor, "execute_application_invocation", execute),
          patch.object(workflow, "evaluate_whole_game_rollout_v1", evaluate),
          patch("skatmind.corpus_web.preparation.prepare_learning_corpus_artifacts_web_v1",
                forbidden)):
        server = start_app_web_server_v1(context, port=0, token=TOKEN)
        thread = serve_app_web_in_thread_v1(server)
        print(json.dumps({"port": server.port, "pid": __import__("os").getpid(),
                          "module": skatmind.__file__}), flush=True)
        try:
            for line in sys.stdin:
                command = json.loads(line)
                if command.get("stop"):
                    break
                controls.update(command)
                store = context.saved_match_analyses.store
                manifest = None if store is None else store.snapshot().manifest
                print(json.dumps({"counts": dict(counts),
                    "evidence": [] if manifest is None else [e.identity for e in manifest.evidence],
                    "active_match": context.managed_stateful.active_match is not None,
                    "profile_revision": None if context.frontend_profile.document is None
                    else context.frontend_profile.document.revision}), flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)


class RolloutServer(ProbeServer):
    def __init__(self, home):
        self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
            "--serve", str(home)], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(self.process.stderr.read())
        self.info = json.loads(line)
        self.port = self.info["port"]
        self.origin = f"http://127.0.0.1:{self.port}"


def reveal(cdp, selector):
    for index in range(10):
        parent = cdp.evaluate("""(()=>{const n=document.querySelector(SELECTOR);const parents=[];
            for(let p=n.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS'&&!p.open)
            parents.push(p);if(!parents.length)return null;const p=parents.at(-1);
            p.id=p.id||ID;return '#'+p.id+' > summary'})()""".replace(
                "SELECTOR", json.dumps(selector)).replace(
                    "ID", json.dumps(f"probe-details-{index}")))
        if parent is None:
            return
        click(cdp, parent)
    raise AssertionError("Disclosure nesting exceeded")


def fill(cdp, name, value):
    selector = FORM + ' input[name="' + name + '"]'
    reveal(cdp, selector)
    click(cdp, selector)
    for event in ("keyDown", "keyUp"):
        cdp.call("Input.dispatchKeyEvent", type=event, key="a", code="KeyA",
                 windowsVirtualKeyCode=65, modifiers=2)
    cdp.call("Input.insertText", text=value)


def main(output, browser_path):
    from test_match_rollout_review import alex_workspace

    from skatmind.app_web.managed_data import prepare_managed_home_v1
    from skatmind.app_web.stateful_localization import text
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    started = time.monotonic()
    assert output.parent.is_dir() and not output.exists()
    output.mkdir()
    home = prepare_managed_home_v1(output / "home")
    path = home.category("matches").path / "synthetic-s3.json"
    assert save_match_workspace_file_v1(path,
        build_match_workspace_persistence_document_v1(alex_workspace(count=3)),
        expected_content_fingerprint=None).status == "saved"
    original = path.read_bytes()
    evidence = {"completed": False, "python": sys.version, "source_tree": True,
                "fixture_writes": "one synthetic Match save", "phases": [], "views": []}
    server = RolloutServer(home.root)
    local = LocalBrowser(browser_path, output / "browser-profile")
    cdp = local.cdp
    evidence["browser"] = local.version
    evidence["first_process"] = server.info
    try:
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        cdp.call("Network.setExtraHTTPHeaders", headers={"Accept-Language": "de"})
        cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
        wait(cdp, "location.pathname==='/'")
        cdp.navigate(server.origin + "/matches")
        native_enter(cdp, 'form[action="/matches/open"] button')
        cdp.navigate(server.origin + "/matches/review/2")
        native_enter(cdp, 'form[action="/matches/select-decision"] button')
        wait(cdp, "location.hash==='#match-decision-controls'")
        evidence["phases"].append({"name": "passive_entry_selection", **server.control()})
        fill(cdp, "analysis_matadors", "1")
        fill(cdp, "requested_worlds", "2")
        server.control(allow_execution=True)
        evidence["analysis_focus"] = native_enter(cdp, FORM + ' button[type="submit"]')
        wait(cdp, "location.pathname.startsWith('/matches/reports/')")
        evidence["phases"].append({"name": "explicit_complete",
                                  **server.control(allow_execution=False)})
        assert text("de", "saved_analysis.rollout.saved") in cdp.evaluate("document.body.innerText")
        live_route = cdp.evaluate("location.pathname")
        links = cdp.evaluate(
            "Array.from(document.querySelectorAll('a[download]')).map(a=>a.pathname)")
        live = {route: request(server, route)[2] for route in links
                if route.startswith('/matches/api/v1/reports/')}
        fill(cdp, "random_seed", "1")
        server.control(allow_execution=True, failure=True, cancelled=True)
        native_enter(cdp, FORM + ' button[type="submit"]')
        wait(cdp, "document.querySelector('form[action=\"/matches/retry-saving\"]')!==null")
        evidence["phases"].append({"name": "controlled_cancelled_and_save_failure",
                                  **server.control(allow_execution=False)})
        server.control(failure=False, allow_save=True)
        evidence["retry_focus"] = native_enter(cdp, 'form[action="/matches/retry-saving"] button')
        wait(cdp, "location.pathname===" + json.dumps(live_route))
        evidence["phases"].append({"name": "save_only_retry", **server.control(allow_save=False)})
        assert text("de", "saved_analysis.rollout.saved") in cdp.evaluate("document.body.innerText")
        assert text("de", "rollout.reason.cancelled") in cdp.evaluate("document.body.innerText")
        assert all(request(server, route)[2] == raw for route, raw in live.items())
        cdp.navigate(server.origin + SAVED)
        saved_links = ("Array.from(document.querySelectorAll("
                       "'a[href^=\"/matches/saved-analyses/\"]')).map(a=>a.pathname)")
        routes = cdp.evaluate(saved_links)
        assert len(routes) == 2
        complete_route, incomplete_route = routes
        evidence["open_focus"] = native_enter(cdp, 'a[href="' + complete_route + '"]')
        wait(cdp, "location.pathname===" + json.dumps(complete_route))
        exports = {}
        folder = output / "downloads"
        folder.mkdir()
        cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(folder))
        for kind in ("request", "result"):
            route = complete_route + "/" + kind + ".json"
            status, headers, raw = request(server, route)
            assert status == 200 and raw in live.values()
            selector = 'a[href="' + route + '"]'
            reveal(cdp, selector)
            native_enter(cdp, selector)
            filename = headers["Content-Disposition"].split('filename="')[1].rstrip('"')
            until = time.monotonic() + 30
            while not (folder / filename).exists() and time.monotonic() < until:
                time.sleep(.1)
            assert (folder / filename).read_bytes() == raw
            exports[kind] = raw
        evidence["downloads"] = {kind: hashlib.sha256(raw).hexdigest()
                                 for kind, raw in exports.items()}
        for locale in ("de", "en"):
            if locale == "en":
                switch_language(cdp, locale)
            for width in (1100, 390):
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=850,
                         deviceScaleFactor=1, mobile=False)
                assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth")
                cdp.screenshot(output / f"native-{locale}-{width}.png", whole=True)
                evidence["views"].append({"locale": locale, "width": width, "javascript": False,
                    "scroll_width": cdp.evaluate("document.documentElement.scrollWidth")})
        cdp.navigate(server.origin + incomplete_route)
        assert "cancelled" in cdp.evaluate("document.body.innerText").lower()
        cdp.screenshot(output / "native-en-incomplete-390.png", whole=True)
        incomplete = {kind: request(server, incomplete_route + "/" + kind + ".json")[2]
                      for kind in ("request", "result")}
        evidence["phases"].append({"name": "native_reads_and_language", **server.control()})
        server.close()
        server = RolloutServer(home.root)
        evidence["second_process"] = server.info
        assert server.info["pid"] != evidence["first_process"]["pid"]
        cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
        wait(cdp, "location.pathname==='/'")
        assert request(server, complete_route)[0] == 409
        cdp.navigate(server.origin + SAVED)
        fresh = cdp.evaluate(saved_links)
        assert len(fresh) == 2 and fresh != routes
        for route, expected in zip(fresh, (exports, incomplete), strict=True):
            cdp.navigate(server.origin + route)
            for kind, raw in expected.items():
                assert request(server, route + "/" + kind + ".json")[2] == raw
        evidence["phases"].append({"name": "restart_reads", **server.control()})
        assert server.control()["counts"] == {} and not server.control()["active_match"]
        cdp.call("Emulation.setScriptExecutionDisabled", value=False)
        cdp.navigate(server.origin + fresh[0])
        switch_language(cdp, "de")
        assert cdp.evaluate("location.pathname") == fresh[0]
        evidence["enhanced_focus"] = focus(cdp)
        evidence["phases"].append({"name": "enhanced_language", **server.control()})
        assert path.read_bytes() == original
        evidence["recording_bytes_unchanged"] = True
        evidence["completed"] = True
    finally:
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "last-page.html").write_text(
            cdp.evaluate("document.documentElement.outerHTML"), encoding="utf-8")
        (output / "evidence.json").write_text(
            json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        local.close()
        server.close()
    print(json.dumps({"completed": True, "evidence": str(output / "evidence.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    if args.serve:
        serve(args.serve)
    else:
        main(args.output, args.browser)
