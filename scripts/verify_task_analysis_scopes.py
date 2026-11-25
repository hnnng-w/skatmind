"""Disposable Edge check of task navigation, automatic results and native original controls."""

import argparse
import hashlib
import json
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_saved_match_analyses import TOKEN, wait
from verify_whole_match_browser import OVERVIEW, PAGE, Server

from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.session_batch_routes import DECISIONS
from skatmind.app_web.session_batch_routes import PAGE as SESSION
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def verify_publication_and_returns(output, cdp, evidence):
    from test_direct_analysis_returns import direct_result
    from test_frontend_language_switching import localized_server
    from test_recorded_analysis_races import interleaved_run

    for family in ("matches", "sessions"):
        for scenario in ("race", "direct"):
            fixture = localized_server.__wrapped__(output / f"{scenario}-{family}")
            with closing(fixture):
                server = next(fixture)
                origin = server.origin
                cdp.call("Emulation.setScriptExecutionDisabled", value=scenario == "direct")
                cdp.call("Page.navigate", url=origin + "/?token=localization-test-token")
                wait(cdp, "location.pathname==='/'")
                if scenario == "race":
                    with interleaved_run(server, family) as run:
                        client, page, watch, release, finish, conflicts = run
                        before = json.loads(client.page(watch + "/status"))
                        assert (before["phase"], before["processed"]) == ("working", 1)
                        cdp.navigate(origin + page)
                        table = "document.querySelector('[data-batch-results]')"
                        if family == "matches":
                            wait(cdp, f"{table}?.innerText.includes('/25)')")
                            cdp.evaluate(f"{table}.querySelector('tbody a').focus()")
                            release.set()
                            finish()
                            wait(cdp, "!document.querySelector('[data-batch-resume]').hidden")
                            assert cdp.evaluate(f"{table}.contains(document.activeElement)")
                            assert cdp.evaluate(f"{table}.innerText.includes('/25)')")
                            cdp.evaluate("document.querySelector('.site-nav a').focus()")
                            wait(cdp, rf"/\b84\s*%/.test({table}?.innerText)")
                        else:
                            wait(cdp, f"{table}?.querySelectorAll('tbody a').length===2")
                            assert conflicts == [watch + "/results"]
                        after = json.loads(client.page(watch + "/status"))
                        assert after["phase"] == "finished"
                        assert before["revision"] != after["revision"]
                        assert cdp.evaluate("location.pathname") == page
                        evidence["race_" + family] = dict(before=before, after=after,
                                                            conflicts=len(conflicts))
                        cdp.screenshot(output / f"recovered-{family}.png")
                else:
                    with direct_result(server, family) as (_, route, first, fifth, _path):
                        cdp.call("Page.navigate", url=origin + route)
                        choose = 'form[action="/learning/analysis-selection"]'
                        for locale, choice in (("de", "include"), ("en", "exclude")):
                            wait(cdp, f"!!document.querySelector('{choose}')")
                            cdp.activate(f'.language-selector button[value="{locale}"]')
                            wait(cdp, f"document.documentElement.lang==='{locale}'")
                            cdp.activate(choose + ' button')
                            field = f"document.querySelector('{choose} [name=choice]')"
                            wait(cdp, f"{field}?.value==='{choice}'")
                            assert cdp.evaluate("location.pathname+location.hash") == route
                        if fifth:
                            cdp.activate(f'a[href="{first}"]')
                            wait(cdp, "!!document.getElementById('recorded-decision-1')")
                            back = f'a[href="{fifth}#recorded-decision-5"]'
                            cdp.activate(back)
                            wait(cdp, "!!document.querySelector('#recorded-decision-5:target')")
                            actual = cdp.evaluate("location.pathname")
                            assert actual == fifth
                        else:
                            cdp.activate('a[href="/matches/position/2#match-recording"]')
                            wait(cdp, "document.querySelector(':target')?.id==='match-recording'")
                            actual = cdp.evaluate("location.pathname")
                            assert actual == "/matches/position/2"
                        evidence["direct_" + family] = dict(result=urlsplit(route).path,
                                                             returned=actual)


def probe(output, executable):
    from test_match_rollout_review import alex_workspace
    from test_session_recorded_review import context_for

    output.mkdir()
    home = prepare_managed_home_v1(output / "managed")
    recording = home.category("matches").path / "synthetic-hearts.json"
    assert save_match_workspace_file_v1(recording, build_match_workspace_persistence_document_v1(
        alex_workspace(count=3)), expected_content_fingerprint=None).status == "saved"
    original = recording.read_bytes()
    _, sample = context_for(output)
    session_bytes = sample.path.read_bytes()
    server = Server(home.root)
    browser = LocalBrowser(executable, output / "browser-profile")
    cdp = browser.cdp
    evidence = {"browser": browser.version}
    def visible(selector):
        wait(cdp, f"!!document.querySelector({json.dumps(selector)})?.getClientRects().length")
    def open_scopes(family):
        cdp.activate('.site-nav a[href="/review/recorded"]')
        saved = f'form[action="/review/open-recording"]:has(input[value="{family}"]) button'
        visible(saved)
        cdp.activate(saved)
        visible('#analysis-scopes')
        assert not cdp.evaluate("!!document.querySelector('[name=analysis_effort]')")
    def shot(name, width):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900,
                 deviceScaleFactor=1, mobile=False)
        assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth")
        cdp.screenshot(output / f"{name}-{width}.png")
    try:
        cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
        visible('main a[href="/record-after"]')
        shot("tasks", 1280)
        cdp.activate('main a[href="/record-after"]')
        assert cdp.evaluate("Array.from(document.querySelectorAll('#recording-formats a'),"
                            "a=>a.pathname)") == ["/matches", "/cent", "/sessions"]
        cdp.activate('#recording-formats a[href="/matches"]')
        cdp.activate('form[action="/matches/open"] button')
        cdp.activate('a[href="/matches/position/2#match-recording"]')
        assert not cdp.evaluate("!!document.querySelector('form[action=\"/matches/live-start\"]')")
        open_scopes("matches")
        shot("match-scopes", 390)
        cdp.activate('#analysis-scopes a[href="/matches/review/2"]')
        visible('#match-review')
        open_scopes("matches")
        cdp.activate(f'#analysis-scopes a[href="{PAGE}/match"]')
        visible(f'form[action="{PAGE}/start"] button')
        open_scopes("matches")
        assert server.control()["counts"] == {}
        cdp.activate('form.language-selector button[value="en"]')
        scope = f'#analysis-scopes form[action="{PAGE}/scopes"]'
        assert cdp.evaluate(f"document.querySelector('{scope} select').value") == "2"
        cdp.activate(scope + ' button')
        start = f'form[action="{PAGE}/start"]'
        visible(start + ' button')
        assert not cdp.evaluate("!!document.querySelector('[name=matadors_5]')")
        cdp.evaluate(f"document.querySelector('{start} [name=analysis_effort]').value='quick'")
        cdp.evaluate(f"document.querySelector('{start} [name=objective]').value='played_game_goal'")
        shot("game-settings", 390)
        cdp.evaluate(f"document.querySelector('{start} button').scrollIntoView({{block:'center'}})")
        shot("game-start", 390)
        cdp.activate(start + " button")
        visible("[data-batch-results] #game-2 tbody a")
        assert not cdp.evaluate("!!document.querySelector('#game-5')")
        assert not cdp.evaluate(
            "!!document.querySelector('form[action$=\"/cancel\"] button')?.getClientRects().length")
        evidence["processed"] = server.control(finish=True)
        assert evidence["processed"]["counts"] == {"evaluate": 1, "execute": 1}
        cdp.evaluate("document.querySelector('#game-2 table').scrollIntoView({block:'center'})")
        shot("game-comparisons", 390)
        shot("game-comparisons", 1280)
        cdp.activate("#game-2 tbody a")
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        choose = 'form[action="/learning/analysis-selection"]'
        cdp.activate(choose + " button")
        wait(cdp, f"document.querySelector('{choose} [name=choice]')?.value==='include'")
        cdp.activate('form.language-selector button[value="de"]')
        visible(choose + ' button')
        cdp.evaluate(f"document.querySelector('{choose} button').scrollIntoView()")
        shot("excluded-original", 390)
        cdp.activate('a[href$="/overview#game-2"]')
        visible("#game-2 tbody a")
        cdp.activate('a[href$="/recording#match-recording"]')
        visible('.match-navigation')
        evidence["after_navigation"] = server.control()
        assert evidence["processed"] == evidence["after_navigation"]
        cdp.activate('.match-navigation a')
        cdp.activate(f'a[href="{PAGE}/match"]')
        visible(start + ' button')
        cdp.evaluate(f"document.querySelector('{start} [name=analysis_effort]').value='quick'")
        cdp.evaluate(f"document.querySelector('{start} [name=objective]').value='played_game_goal'")
        cdp.activate(start + " button")
        visible(f'a[href="{OVERVIEW}"]')
        evidence["native_whole_match"] = server.control(finish=True)
        assert evidence["native_whole_match"]["counts"] == evidence["processed"]["counts"]
        cdp.activate(f'a[href="{OVERVIEW}"]')
        visible("#game-2 tbody a")
        assert cdp.evaluate("!!document.querySelector('#game-5')")
        cdp.call("Emulation.setScriptExecutionDisabled", value=False)
        open_scopes("sessions")
        shot("session-scopes", 390)
        cdp.activate(f'#analysis-scopes a[href="{DECISIONS}"]')
        visible('form[action="/sessions/review-whole-game"] button')
        open_scopes("sessions")
        assert server.control()["counts"] == evidence["processed"]["counts"]
        cdp.activate(f'a[href="{SESSION}"]')
        one = f'form[action="{SESSION}/start"]'
        visible(one + ' button')
        cdp.evaluate(f"document.querySelector('{one} [name=objective]').value='played_game_goal'")
        cdp.evaluate(f"document.querySelector('{one} [name=analysis_effort]').value='quick'")
        cdp.activate(one + ' button')
        visible('[data-batch-results] tbody a')
        cdp.evaluate("document.querySelector('[data-batch-results] table').scrollIntoView()")
        shot("session-game", 390)
        cdp.activate('[data-batch-results] tbody a')
        visible('a[href$="/overview"]')
        cdp.activate('a[href$="/overview"]')
        visible('a[href$="/review"]')
        cdp.activate('a[href$="/review"]')
        visible('form[action="/sessions/review-whole-game"] button')
        evidence["after_session"] = server.control()
        assert evidence["after_session"]["counts"]["evaluate"] == 2
        assert sample.path.read_bytes() == session_bytes
        assert recording.read_bytes() == original
        evidence["recording_sha256"] = hashlib.sha256(original).hexdigest()
        verify_publication_and_returns(output, cdp, evidence)
    except Exception:
        evidence["page"] = cdp.evaluate("location.pathname")
        evidence["visible_text"] = cdp.evaluate("document.body?.innerText.slice(0,2500)")
        cdp.screenshot(output / "diagnostic.png")
        raise
    finally:
        browser.close()
        server.close()
        (output / "observations.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    args = parser.parse_args()
    probe(args.output, args.browser)
