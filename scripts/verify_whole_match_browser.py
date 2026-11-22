"""Disposable #332 source-browser scenario, with a genuine server process restart."""

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, keyboard
from verify_saved_match_analyses import TOKEN, ProbeServer, wait

from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.whole_match_routes import OVERVIEW, PAGE
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


class Server(ProbeServer):
    def __init__(self, home):
        self.process = subprocess.Popen([sys.executable, __file__, "--serve", str(home)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
        self.info = json.loads(self.process.stdout.readline())
        self.origin = 'http://127.0.0.1:' + str(self.info["port"])


def serve(home):
    from test_frontend_language_switching import localized_server

    import skatmind.application.execution as executor
    import skatmind.recommendation_workflow as workflow
    from skatmind.app_web.server import start_app_web_server_v1
    from skatmind.app_web.whole_match_job import progress_file

    calls = Counter()
    def counted(name, real):
        def run(*args, **kwargs):
            calls[name] += 1
            return real(*args, **kwargs)
        return run
    with (patch("test_frontend_language_switching.start_app_web_server_v1", side_effect=lambda
            context, **kw: start_app_web_server_v1(context, port=0, token=TOKEN)),
            patch.object(executor, "execute_application_invocation",
                         counted("execute", executor.execute_application_invocation)),
            patch.object(workflow, "evaluate_whole_game_rollout_v1",
                         counted("evaluate", workflow.evaluate_whole_game_rollout_v1))):
        fixture = localized_server.__wrapped__(home.parent)
        server = next(fixture)
        print(json.dumps({"pid": os.getpid(), "port": server.port}), flush=True)
        try:
            for line in sys.stdin:
                command = json.loads(line)
                if command.get("stop"):
                    break
                app = server.app_context
                if command.get("finish") and (worker := app.whole_match.worker):
                    worker.thread.join(180)
                state = progress_file(app, app.managed_stateful.active_match).read()
                print(json.dumps({"counts": dict(calls), "phase": state["phase"] if state else None,
                    "refs": state["refs"] if state else {}}), flush=True)
        finally:
            fixture.close()


def probe(output, executable):
    from test_match_rollout_review import alex_workspace

    output.mkdir()
    home = prepare_managed_home_v1(output / "managed")
    recording = home.category("matches").path / "synthetic-browser.json"
    assert save_match_workspace_file_v1(recording, build_match_workspace_persistence_document_v1(
        alex_workspace(count=18)), expected_content_fingerprint=None).status == "saved"
    server = Server(home.root)
    browser = LocalBrowser(executable, output / "browser-profile")
    cdp = browser.cdp
    evidence = {"browser": browser.version, "first_process": server.info}
    def enter():
        cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
        wait(cdp, "location.pathname==='/'")
        cdp.navigate(server.origin + "/matches")
        cdp.activate('form[action="/matches/open"] button')
        wait(cdp, f'!!document.querySelector(\'a[href="{PAGE}"]\')')
        cdp.activate(f'a[href="{PAGE}"]')
        wait(cdp, f'location.pathname==="{PAGE}"')

    def button(action):
        return f'form[action="{PAGE}/{action}"] button'

    try:
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        cdp.call("Emulation.setDeviceMetricsOverride", width=1280, height=900,
                 deviceScaleFactor=1, mobile=False)
        enter()
        for name, key, code in (("analysis_effort", "Home", 36), ("objective", "End", 35)):
            selector = f'select[name="{name}"]'
            click(cdp, selector)
            keyboard(cdp, key, key, code)
            keyboard(cdp, "Enter", "Enter", 13, "\r")
        assert cdp.evaluate('document.querySelector("[name=analysis_effort]").value') == "quick"
        assert not server.control()["counts"]
        cdp.activate(button("start"))
        wait(cdp, f'!!document.querySelector(\'{button("cancel")}\')')
        evidence["progress"] = cdp.evaluate("document.querySelector('main').innerText")
        cdp.activate(button("cancel"))
        evidence["cancelled"] = server.control(finish=True)
        assert evidence["cancelled"]["phase"] == "paused"
        server.close()
        server = Server(home.root)
        evidence["second_process"] = server.info
        enter()
        assert cdp.evaluate(f"!!document.querySelector('{button('resume')}')")
        evidence["after_restart"] = server.control()
        assert evidence["after_restart"]["counts"].get("execute", 0) == 0
        cdp.activate(button("resume"))
        evidence["resumed"] = server.control(finish=True)
        assert evidence["resumed"]["phase"] == "finished"
        cdp.navigate(server.origin + PAGE)
        cdp.activate(f'a[href="{OVERVIEW}"]')
        for locale in ("de", "en"):
            cdp.activate(f'form[action="/actions/profile/language"] button[value="{locale}"]')
            wait(cdp, f'document.documentElement.lang==="{locale}" && '
                      f'location.pathname==="{OVERVIEW}"')
            wait(cdp, "!!document.querySelector('table tbody')")
            evidence[locale] = cdp.evaluate("""(()=>{const table=document.querySelector(
                'table:has(a[href*="/saved-analyses/"])');table.scrollIntoView({block:'center'});
                return {rows:table.innerText,columns:[...table.tHead.rows[0].cells].map(
                c=>c.getBoundingClientRect().x),overflow:document.documentElement.scrollWidth-
                innerWidth}})()""")
            assert "/25" in evidence[locale]["rows"] and evidence[locale]["overflow"] <= 0
            cdp.screenshot(output / f"overview-{locale}.png")
        detail = cdp.evaluate("document.querySelector('tbody a').pathname")
        cdp.activate("tbody a")
        wait(cdp, "!!document.querySelector('a[href$=\"/request.json\"]')")
        assert cdp.evaluate("location.pathname") == detail
        cdp.call("Page.navigate", url=server.origin + OVERVIEW)
        wait(cdp, "!!document.querySelector('tbody a')")
        evidence["passive"] = server.control()
        assert evidence["passive"]["counts"] == evidence["resumed"]["counts"]
    finally:
        browser.close()
        server.close()
        (output / "browser.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1] == "--serve":
        serve(Path(sys.argv[2]))
        sys.exit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    args = parser.parse_args()
    probe(args.output, args.browser)
