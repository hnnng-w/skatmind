"""Bounded S2 source-tree browser probe, using disposable synthetic data only.

The child stdin control channel is an external verification harness, never a
production route. It counts writes/executions and controls a reports-only failure.
No distribution is built or installed. Existing Chromium/native-input helpers
are reused without invoking their installed verification entry points.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, focus, keyboard, tab_to

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
TOKEN = "disposable-source-tree-s2-probe"
SAVED = "/matches/saved-analyses"
FORM = 'form[action="/matches/api/v1/analysis"]:has(input[value="analyze_decision"])'


def serve(home):
    import skatmind
    import skatmind.automatic_learning_io as io
    import skatmind.match_decision_analysis as engine
    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.managed_data import prepare_managed_home_v1
    from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1

    assert Path(skatmind.__file__).resolve().is_relative_to(ROOT / "src")
    context = AppWebContextV1.create(prepare_managed_home_v1(home))
    counts = Counter()
    failing = False
    real_write, real_execute = io.write_temporary, engine.execute_application_invocation

    def write(directory, raw):
        if directory.name == "reports" and failing:
            counts["controlled_retention_failure"] += 1
            raise OSError("Disposable external harness retention failure")
        result = real_write(directory, raw)
        counts["archive_write_" + directory.name] += 1
        return result

    def evaluate(*args, **kwargs):
        counts["application_execution"] += 1
        return real_execute(*args, **kwargs)

    def forbidden(*args, **kwargs):
        counts["learning_preparation"] += 1
        raise AssertionError("S2 must not prepare Learning artifacts")

    with (patch.object(io, "write_temporary", write),
          patch.object(engine, "execute_application_invocation", evaluate),
          patch("skatmind.corpus_web.preparation.prepare_learning_corpus_artifacts_web_v1",
                forbidden)):
        server = start_app_web_server_v1(context, port=0, token=TOKEN)
        thread = serve_app_web_in_thread_v1(server)
        print(json.dumps({"port": server.port, "pid": __import__("os").getpid(),
                          "module": skatmind.__file__}), flush=True)
        try:
            for line in sys.stdin:
                command = json.loads(line)
                if "failure" in command:
                    failing = command["failure"]
                if command.get("stop"):
                    break
                store = context.saved_match_analyses.store
                evidence = () if store is None else store.snapshot().manifest.evidence
                print(json.dumps({"counts": dict(counts),
                    "evidence": [e.identity for e in evidence],
                    "profile_revision": None if context.frontend_profile.document is None
                    else context.frontend_profile.document.revision}), flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(5)


class ProbeServer:
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

    def control(self, **values):
        self.process.stdin.write(json.dumps(values) + "\n")
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())

    def close(self):
        if self.process.poll() is not None:
            return
        self.process.stdin.write('{"stop":true}\n')
        self.process.stdin.flush()
        self.process.wait(30)
        assert self.process.returncode == 0, self.process.stderr.read()


def wait(cdp, expression, seconds=120):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if cdp.evaluate("document.readyState==='complete' && (" + expression + ")"):
            return
        time.sleep(.1)
    raise AssertionError((expression, cdp.evaluate("location.href")))


def request(server, route):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=120)
    connection.request("GET", route, headers={"Cookie": "skatmind_app_token=" + TOKEN})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def native_enter(cdp, selector):
    tab_to(cdp, selector)
    before = focus(cdp)
    keyboard(cdp, "Enter", "Enter", 13, "\r")
    time.sleep(.5)
    return before


def ordinary(cdp):
    # Open only the native disclosures enclosing the ordinary form and its settings.
    for index in range(5):
        selector = cdp.evaluate("""(()=>{const f=document.querySelector(FORM_SELECTOR);
            const a=[]; for(let p=f.parentElement;p;p=p.parentElement)
            if(p.tagName==='DETAILS'&&!p.open)a.push(p);
            if(a.length){const p=a[a.length-1];p.id=p.id||PROBE_ID;
            return '#'+p.id+' > summary';}return null;})()""".replace(
                "FORM_SELECTOR", json.dumps(FORM)).replace(
                "PROBE_ID", json.dumps("probe-disclosure-" + str(index))))
        if selector is None:
            break
        click(cdp, selector)
    details = FORM + " > details > summary"
    click(cdp, details)
    selector = FORM + ' input[name="immediate_sample_count"]'
    click(cdp, selector)
    cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA",
             windowsVirtualKeyCode=65, modifiers=2)
    cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA",
             windowsVirtualKeyCode=65, modifiers=2)
    cdp.call("Input.insertText", text="1")
    return native_enter(cdp, FORM + ' > button')


def switch_language(cdp, locale):
    selector = 'form[action="/actions/profile/language"]'
    native_enter(cdp, selector + ' button[value="' + locale + '"]')
    wait(cdp, "document.documentElement.lang===" + json.dumps(locale))


def main(output, browser_path):
    started = time.monotonic()
    from test_match_rollout_review import alex_workspace

    from skatmind.app_web.managed_data import prepare_managed_home_v1
    from skatmind.learning_corpus_persistence import initialize_learning_corpus_directory_v1
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    assert output.parent.is_dir() and not output.exists()
    output.mkdir()
    home = prepare_managed_home_v1(output / "home")
    recording = home.category("matches").path / "synthetic-s2.json"
    save_match_workspace_file_v1(recording,
        build_match_workspace_persistence_document_v1(alex_workspace(count=3)),
        expected_content_fingerprint=None)
    initialize_learning_corpus_directory_v1(home.category("corpora").path / "manual",
                                            corpus_id="synthetic-independent")
    original = {p: p.read_bytes() for category in home.categories
                for p in category.path.rglob("*") if p.is_file()}
    evidence = {"completed": False, "source_tree": True, "python": sys.version,
                "fixture_writes": "one Match save and one independent manual Corpus initialization",
                "phases": [], "views": [], "downloads": {}}
    receipt = output / "evidence.json"
    server = ProbeServer(home.root)
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
        wait(cdp, "location.pathname.startsWith('/matches/') && location.pathname!='/matches'")
        cdp.navigate(server.origin + "/matches/review/2")
        native_enter(cdp, 'form[action="/matches/select-decision"] button')
        wait(cdp, "location.hash==='#match-decision-controls'")
        evidence["phases"].append({"name": "passive_entry_and_selection", **server.control()})
        evidence["analysis_focus"] = ordinary(cdp)
        wait(cdp, "location.pathname.startsWith('/matches/reports/')")
        assert "Lernbelege gespeichert" in cdp.evaluate("document.body.innerText")
        evidence["phases"].append({"name": "explicit_analysis", **server.control()})
        links = cdp.evaluate(
            "Array.from(document.querySelectorAll('a[download]')).map(a=>a.pathname)")
        live = {route: request(server, route)[2] for route in links
                if route.startswith("/matches/api/v1/reports/")}
        cdp.navigate(server.origin + SAVED)
        cdp.call("Emulation.setDeviceMetricsOverride", width=390, height=850,
                 deviceScaleFactor=1, mobile=False)
        cdp.screenshot(output / "native-de-saved-list-390.png", whole=True)
        assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth")
        saved_link = 'a[href^="/matches/saved-analyses/"]'
        route = cdp.evaluate("document.querySelector(" + json.dumps(saved_link) + ").pathname")
        evidence["open_focus"] = native_enter(cdp, 'a[href="' + route + '"]')
        wait(cdp, "location.pathname===" + json.dumps(route))
        evidence["initial_saved_landing"] = cdp.evaluate(
            "({path:location.pathname,top:scrollY,heading:document.querySelector('h1').innerText})")
        for locale in ("de", "en"):
            if locale == "en":
                switch_language(cdp, locale)
            for width in (1100, 390):
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=850,
                         deviceScaleFactor=1, mobile=False)
                cdp.screenshot(output / f"native-{locale}-{width}.png", whole=True)
                metrics = cdp.evaluate(
                    "({width:innerWidth,scroll:document.documentElement.scrollWidth})")
                assert metrics["scroll"] <= metrics["width"]
                evidence["views"].append({"locale": locale, "javascript": False, **metrics})
        original_downloads = {}
        downloads = output / "downloads"
        downloads.mkdir()
        cdp.call("Browser.setDownloadBehavior", behavior="allow", downloadPath=str(downloads))
        for kind in ("request", "result", "strategy-source"):
            status, headers, raw = request(server, route + "/" + kind + ".json")
            assert status == 200
            filename = headers["Content-Disposition"].split('filename="')[1].rstrip('"')
            native_enter(cdp, 'a[href="' + route + "/" + kind + '.json"]')
            until = time.monotonic() + 30
            while not (downloads / filename).exists() and time.monotonic() < until:
                time.sleep(.1)
            assert (downloads / filename).read_bytes() == raw
            original_downloads[kind] = raw
            evidence["downloads"][kind] = {
                "filename": filename, "sha256": hashlib.sha256(raw).hexdigest()}
        assert original_downloads["result"] in live.values()
        assert original_downloads["strategy-source"] in live.values()
        evidence["phases"].append({"name": "native_reads_and_language", **server.control()})
        server.close()
        server = ProbeServer(home.root)
        evidence["second_process"] = server.info
        assert evidence["first_process"]["pid"] != server.info["pid"]
        cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
        wait(cdp, "location.pathname==='/'")
        assert request(server, route)[0] == 409
        cdp.navigate(server.origin + SAVED)
        fresh = cdp.evaluate("document.querySelector(" + json.dumps(saved_link) + ").pathname")
        assert fresh != route
        cdp.navigate(server.origin + fresh)
        for kind, raw in original_downloads.items():
            assert request(server, fresh + "/" + kind + ".json")[2] == raw
        evidence["phases"].append({"name": "restart_reads", **server.control()})
        assert server.control()["counts"] == {}
        cdp.call("Emulation.setScriptExecutionDisabled", value=False)
        cdp.navigate(server.origin + fresh)
        switch_language(cdp, "de")
        assert cdp.evaluate("location.pathname") == fresh
        evidence["enhanced_return_focus"] = focus(cdp)
        evidence["phases"].append({"name": "enhanced_language", **server.control()})
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        cdp.navigate(server.origin + "/matches")
        native_enter(cdp, 'form[action="/matches/open"] button')
        wait(cdp, "location.pathname.startsWith('/matches/') && location.pathname!='/matches'")
        cdp.navigate(server.origin + "/matches/review/2")
        native_enter(cdp, 'form[action="/matches/select-decision"] button')
        wait(cdp, "location.hash==='#match-decision-controls'")
        # Different seed makes a second exact ordinary execution for the failure probe.
        server.control(failure=True)
        # The first exact Immediate Report may be reused, so change the submitted seed natively.
        for _ in range(4):
            selector = cdp.evaluate("""(()=>{const f=document.querySelector(FORM_SELECTOR);
                for(let p=f.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS'&&!p.open)
                {p.id=p.id||'probe-failure-disclosure';return '#'+p.id+' > summary';}
                return null})()""".replace("FORM_SELECTOR", json.dumps(FORM)))
            if not selector:
                break
            click(cdp, selector)
        click(cdp, FORM + ' > details > summary')
        click(cdp, FORM + ' input[name="immediate_random_seed"]')
        keyboard(cdp, "End", "End", 35)
        keyboard(cdp, "1", "Digit1", 49, "1")
        click(cdp, FORM + ' > details > summary')
        ordinary(cdp)
        wait(cdp, "location.pathname.startsWith('/matches/reports/')")
        assert "Lernbelege wurden nicht gespeichert" in cdp.evaluate("document.body.innerText")
        evidence["phases"].append({"name": "controlled_failure", **server.control()})
        server.control(failure=False)
        evidence["retry_focus"] = native_enter(cdp, 'form[action="/matches/retry-saving"] button')
        wait(cdp, "document.body.innerText.includes('Lernbelege gespeichert')")
        evidence["phases"].append({"name": "save_only_retry", **server.control()})
        assert server.control()["counts"]["application_execution"] == 1
        assert len(server.control()["evidence"]) == 2
        assert all(p.read_bytes() == raw for p, raw in original.items())
        evidence["recording_and_manual_bytes_unchanged"] = True
        evidence["completed"] = True
    finally:
        evidence["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "last-page.html").write_text(
            cdp.evaluate("document.documentElement.outerHTML"), encoding="utf-8")
        receipt.write_text(json.dumps(evidence, indent=2, ensure_ascii=True) + "\n",
                           encoding="utf-8")
        local.close()
        server.close()
    print(json.dumps({"completed": True, "receipt": str(receipt)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--browser", type=Path)
    arguments = parser.parse_args()
    if arguments.serve:
        serve(arguments.serve)
    else:
        main(arguments.output, arguments.browser)
