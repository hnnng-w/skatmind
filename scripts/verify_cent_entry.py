"""Issue #334: narrow development-source Edge verification using disposable managed data."""

import argparse
import hashlib
import json
from contextlib import ExitStack, closing
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_saved_match_analyses import wait


def probe(output, executable):
    from test_accounting_web import activate_session, historical_round
    from test_direct_analysis_returns import direct_result
    from test_frontend_language_switching import localized_server
    from test_session_recorded_review_web import Browser, Forms

    from skatmind.app_web.session_batch_routes import DECISIONS, PAGE

    output.mkdir()
    home = output / "source"
    with closing(localized_server.__wrapped__(home)) as fixture:
        server = next(fixture)
        app = server.app_context
        with direct_result(server, "sessions") as (client, route, _, _, path):
            historical_round(app, title="Earlier bound game")
            form = Forms(client.page(route.split("#")[0])).find("/learning/analysis-selection")
            assert client.submit(form)[0] == 303
            base = "/sessions/saved-analyses/" + form["values"]["analysis"]
            originals = [client.request("GET", base + f"/{kind}.json")[2]
                         for kind in ("request", "result")]
        independent = activate_session(app, "independent-game")
        before = {p: p.read_bytes() for p in (path, independent.path)}

    edge = LocalBrowser(executable, output / "edge-profile")
    cdp = edge.cdp
    evidence = {"browser": edge.version}
    try:
        with closing(localized_server.__wrapped__(home)) as fixture, ExitStack() as stack:
            server = next(fixture)
            app = server.app_context
            client = Browser(server)
            counters = {name: stack.enter_context(patch(name, side_effect=AssertionError(name)))
                for name in ("skatmind.recommendation_workflow.evaluate_whole_game_rollout_v1",
                             "skatmind.app_web.execution.execute",
                             "skatmind.app_web.automatic_match_learning."
                             "AutomaticMatchLearningServiceV1.update")}
            cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
            wait(cdp, "!!document.querySelector('main a[href=\"/live-play\"]')")
            cdp.call("Emulation.setScriptExecutionDisabled", value=True)
            def activate(selector):
                wait(cdp, f"!!document.querySelector({json.dumps(selector)})")
                cdp.activate(selector)
            def shot(name):
                assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth")
                cdp.screenshot(output / (name + ".png"))
            for width, locale, task, labels in (
                (1280, "de", "/live-play", ["36er Standard", "Cent-Skat", "Einzelspiel"]),
                (390, "en", "/record-after", ["36-game Standard", "Cent-Skat", "Individual game"]),
            ):
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900,
                         deviceScaleFactor=1, mobile=False)
                activate(f'.site-nav a[href="{task}"]')
                activate(f'.language-selector button[value="{locale}"]')
                wait(cdp, f"document.documentElement.lang==='{locale}'")
                assert cdp.evaluate("Array.from(document.querySelectorAll('#recording-formats a'),"
                                    "a=>a.textContent)") == labels
                shot("formats-" + locale)
                activate('#recording-formats a[href="/cent"]')
                assert cdp.evaluate("!!document.querySelector('form[action=\"/cent/start\"]')")
                shot("cent-" + locale)
            assert app.managed_stateful.active_session is None
            activate('form[action="/cent/resume"] button')
            wait(cdp, "!!document.querySelector('.cent-membership')")
            assert app.managed_stateful.active_session.path == path
            assert "Earlier bound game" in cdp.evaluate("document.querySelector('main').innerText")
            activate('.site-nav a[href="/record-after"]')
            activate('#recording-formats a[href="/cent"]')
            fields = dict(title="Direct synthetic round", platform="in_person", cent_tariff="3",
                forehand_name="Alice", middlehand_name="Bob", rearhand_name="Carol",
                perspective_seat="middlehand")
            for name, value in fields.items():
                cdp.evaluate(f"document.querySelector('[name={name}]').value={json.dumps(value)}")
            cdp.evaluate("document.querySelector('[name=capture_mode][value=retrospective]').click()")
            activate('form[action="/cent/start"] button')
            wait(cdp, "!!document.querySelector('.cent-membership')")
            first = app.managed_stateful.active_session
            assert first.state.capture_mode == "retrospective"
            assert cdp.evaluate("document.querySelector('.cent-membership').innerText") == (
                "Direct synthetic round · Cent-Skat · Game 1 of 3")
            game = 'form[action="/sessions/accounting/game"]'
            cdp.evaluate(f"document.querySelector('{game} [name=game_status]').value='passed'")
            activate(game + ' button')
            next_game = 'form[action="/sessions/accounting/open"]:has([name=position][value="2"])'
            assert cdp.evaluate("!document.querySelector('[name=source_choice],[name=map_1]')")
            activate(next_game + ' button')
            wait(cdp, "document.querySelector('.cent-membership')?.innerText.includes('2 of 3')")
            assert "2 of 3" in cdp.evaluate("document.querySelector('.cent-membership').innerText")
            second = app.managed_stateful.active_session
            assert second.state.capture_mode == "retrospective"
            assert first.state.local_player_id == second.state.local_player_id
            second_result = game + ':has([name=position][value="2"])'
            cdp.evaluate(f"document.querySelector('{second_result} [name=game_status]')"
                         ".value='passed'")
            activate(second_result + ' button')
            activate(next_game.replace('value="2"', 'value="3"') + ' button')
            wait(cdp, "document.querySelector('.cent-membership')?.innerText.includes('3 of 3')")
            third = app.managed_stateful.active_session
            assert third.state.capture_mode == first.state.capture_mode
            assert third.state.local_player_id == first.state.local_player_id
            for index, recording in enumerate((first, second, third)):
                assert [p.player_id for p in recording.state.players] == [
                    p.player_id for p in first.state.players[index:] + first.state.players[:index]]
            before.update({p: p.read_bytes() for p in (first.path, second.path, third.path)})
            activate('.site-nav a[href="/review/recorded"]')
            archive_choice = ("Array.from(document.querySelectorAll('.recording-choice')).find("
                              "e=>e.innerText.includes('Earlier bound game'))")
            assert cdp.evaluate(archive_choice + ".innerText.includes('Game 1 of 3')")
            shot("analyze-membership")
            cdp.evaluate(archive_choice + ".id='earlier'")
            activate('#earlier form[action="/review/open-recording"] button')
            wait(cdp, "!!document.querySelector('#analysis-scopes')")
            assert app.managed_stateful.active_session.path == path
            activate(f'#analysis-scopes a[href="{PAGE}"]')
            assert cdp.evaluate(f"!!document.querySelector('form[action=\"{PAGE}/start\"]')")
            activate(f'main a[href="{DECISIONS}"]')
            activate('a[href="/sessions/saved-analyses"]')
            activate('main a[href^="/sessions/saved-analyses/"]')
            choose = 'form[action="/learning/analysis-selection"]'
            wait(cdp, f"!!document.querySelector('{choose}')")
            choice = cdp.evaluate(f"document.querySelector('{choose} [name=choice]').value")
            assert choice == "include"
            base = cdp.evaluate("location.pathname")
            assert originals == [client.request("GET", base + f"/{kind}.json")[2]
                                 for kind in ("request", "result")]
            activate('.language-selector button[value="de"]')
            wait(cdp, "document.documentElement.lang==='de'")
            cdp.navigate(server.origin + base)
            wait(cdp, f"document.querySelector('{choose} [name=choice]')?.value==='include'")
            assert cdp.evaluate("document.documentElement.lang") == "de"
            activate('.site-nav a[href="/review/recorded"]')
            activate('.recording-choice form[action="/review/open-recording"]'
                     ':not(:has([name=bound_selection])) button')
            wait(cdp, "!!document.querySelector('#analysis-scopes')")
            assert app.managed_stateful.active_session.path == independent.path
            assert before == {p: p.read_bytes() for p in before}
            evidence.update(passive_calls={k: v.call_count for k, v in counters.items()},
                recordings={p.name: hashlib.sha256(raw).hexdigest() for p, raw in before.items()},
                original_sha256=[hashlib.sha256(raw).hexdigest() for raw in originals],
                viewport_css_pixels=[[1280, 900], [390, 900]], scale=1,
                keyboard="Enter on focused native controls; page scripts disabled")
            assert not any(evidence["passive_calls"].values())
    except Exception:
        evidence["diagnostic"] = cdp.evaluate("document.body.innerText.slice(0,3000)")
        cdp.screenshot(output / "diagnostic.png")
        raise
    finally:
        edge.close()
        (output / "observations.json").write_text(json.dumps(evidence, indent=2), encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    args = parser.parse_args()
    probe(args.output, args.browser)
