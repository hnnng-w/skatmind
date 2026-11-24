"""Navigate a disposable source Match without page scripts, using real retained originals."""

import argparse
import hashlib
import json
from pathlib import Path

from _workflow_visual_browser import LocalBrowser
from verify_recording_deletion import click, focus, keyboard, tab_to
from verify_saved_match_analyses import TOKEN, request, wait
from verify_whole_match_browser import OVERVIEW, PAGE, Server

from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.stateful_localization import text
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def probe(output, executable):
    from test_match_rollout_review import alex_workspace

    output.mkdir()
    home = prepare_managed_home_v1(output / "managed")
    recording = home.category("matches").path / "synthetic-hearts.json"
    assert save_match_workspace_file_v1(recording, build_match_workspace_persistence_document_v1(
        alex_workspace(count=18, bid=None)), expected_content_fingerprint=None).status == "saved"
    original = recording.read_bytes()
    stamp = recording.stat().st_mtime_ns
    (output / recording.name).write_bytes(original)
    server = Server(home.root)
    server.port = server.info["port"]
    browser = LocalBrowser(executable, output / "browser-profile")
    cdp = browser.cdp
    evidence = {"browser": browser.version, "import_sha256": hashlib.sha256(original).hexdigest()}

    def visible(selector):
        wait(cdp, f"!!document.querySelector({json.dumps(selector)})?.getClientRects().length")

    def context(area, game=2, play=None):
        visible(".match-navigation strong")
        locale = cdp.evaluate("document.documentElement.lang")
        caption = cdp.evaluate("document.querySelector('.match-navigation').innerText")
        assert "Synthetic Hearts review" in caption
        assert text(locale, "task.match.game_heading", number=game) in caption
        if play:
            assert text(locale, "match_nav.play", number=play) in caption
        assert cdp.evaluate("document.querySelector('.match-navigation [aria-current]').innerText"
                            ) == text(locale, "match_nav." + area)

    def language(locale):
        cdp.activate(f'form[action="/actions/profile/language"] button[value="{locale}"]')
        wait(cdp, f'document.documentElement.lang==="{locale}"')

    def refresh():
        cdp.navigate(cdp.evaluate("location.href"))

    def settings(form):
        for field, key, code in (("analysis_effort", "Home", 36), ("objective", "End", 35)):
            click(cdp, form + f' select[name="{field}"]')
            keyboard(cdp, key, key, code)
            keyboard(cdp, "Enter", "Enter", 13, "\r")

    def originals():
        downloads = cdp.evaluate("""[...document.querySelectorAll(
            'a[href$="/request.json"], a[href$="/result.json"]')].map(a=>a.pathname)""")
        assert len(downloads) == 2
        result = {}
        for route in downloads:
            status, _, raw = request(server, route)
            assert status == 200
            result[route] = hashlib.sha256(raw).hexdigest()
        return result

    def size(width):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=900,
                 deviceScaleFactor=1, mobile=False)

    try:
        cdp.call("Emulation.setScriptExecutionDisabled", value=True)
        size(1280)
        cdp.call("Page.navigate", url=server.origin + "/?token=" + TOKEN)
        wait(cdp, "location.pathname==='/'")
        cdp.activate('a[href="/matches"]')
        visible('form[action="/matches/open"] button')
        cdp.activate('form[action="/matches/open"] button')
        context("record", 1)
        cdp.activate('a[href="/matches/position/2#match-recording"]')
        context("record")
        language("en")
        refresh()
        context("record")
        assert not cdp.evaluate("!!document.querySelector('input[name=cards]:checked')")
        tab_to(cdp, '.match-navigation a')
        evidence["keyboard"] = focus(cdp)
        assert evidence["keyboard"]["visible"] and evidence["keyboard"]["width"] != "0px"
        cdp.screenshot(output / "record-focus.png")
        keyboard(cdp, "Enter", "Enter", 13, "\r")
        visible('[data-apply-decision]')
        context("review")
        cdp.activate('[data-apply-decision]')
        single = 'form[action="/matches/review-whole-game"]'
        visible(single + " button")
        language("de")
        refresh()
        context("review", play=3)
        assert server.control() == {"counts": {}, "phase": None, "refs": {}}
        settings(single)
        cdp.activate(single + " button")
        visible("#match-rollout-result")
        context("review", play=3)
        evidence["individual"] = server.control()
        assert evidence["individual"] == {"counts": {"execute": 1, "evaluate": 1},
                                          "phase": None, "refs": {}}
        cdp.activate('.match-navigation a')
        context("record")
        cdp.activate('.match-navigation a')
        cdp.activate(f'a[href="{PAGE}/match"]')
        context("review")
        start = f'form[action="{PAGE}/start"]'
        settings(start)
        cdp.activate(start + " button")
        visible(f'a[href="{PAGE}"]')
        evidence["finished"] = server.control(finish=True)
        assert evidence["finished"]["phase"] == "finished"
        assert evidence["finished"]["counts"] == {"execute": 5, "evaluate": 5}
        assert evidence["finished"]["refs"]["2:3"][0] == "reused"
        manifest = (home.root / "automatic-learning" / "manifest.json").read_bytes()
        cdp.activate(f'a[href="{PAGE}"]')
        cdp.activate(f'a[href="{OVERVIEW}"]')
        context("review")
        detail = '#game-2 tbody a'
        for width in (1280, 390):
            size(width)
            cdp.evaluate("document.querySelector('#game-2 table').scrollIntoView({block:'center'})")
            assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth")
            cdp.screenshot(output / f"comparison-{width}.png")
        rows = cdp.evaluate("document.querySelector('#game-2 table').innerText")
        assert "1284/25" in rows and "1386/25" in rows
        evidence["rows"] = rows
        cdp.activate(detail)
        context("review", play=3)
        hashes = originals()
        language("en")
        refresh()
        context("review", play=3)
        assert originals() == hashes
        cdp.evaluate("document.querySelector('.match-navigation').scrollIntoView()")
        cdp.screenshot(output / "original-narrow.png")
        cdp.activate('a[href$="/overview#game-2"]')
        wait(cdp, "location.hash==='#game-2' && !!document.querySelector('#game-2 tbody')")
        language("de")
        assert cdp.evaluate("location.hash") == "#game-2"
        visible("#game-2 .comparison-location")
        assert cdp.evaluate("document.querySelector('#game-2 .comparison-location').innerText"
                            ) == "Synthetic Hearts review · " + text("de", "match_nav.review")
        cdp.screenshot(output / "overview-return.png")
        cdp.activate('#game-2 a[href$="/recording#match-recording"]')
        context("record")
        refresh()
        language("en")
        context("record")
        evidence["passive_end"] = server.control()
        assert evidence["passive_end"] == evidence["finished"]
        assert recording.read_bytes() == original and recording.stat().st_mtime_ns == stamp
        assert (home.root / "automatic-learning" / "manifest.json").read_bytes() == manifest
        evidence["originals"] = hashes
    finally:
        browser.close()
        server.close()
        (output / "navigation.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", type=Path, required=True)
    args = parser.parse_args()
    probe(args.output, args.browser)
