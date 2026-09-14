"""Optional installed-Wheel progress inspection using existing dependency-free DevTools."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from importlib.resources import files
from pathlib import Path

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, fill, posts, wait

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_match_recording_recovery_web import (  # noqa: E402
    follow,
    operation_form,
    start_match,
)
from test_recorded_trick_progress import GRAND_PREFIXES, progress_data  # noqa: E402
from test_session_recorded_review_web import Browser, Forms  # noqa: E402

RESOURCES = (
    "assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json",
    "recorded_trick_progress.py", "recorded_trick_rendering.py", "compact_card_rendering.py",
    "task_first_session_rendering.py", "task_first_match_rendering.py",
    "task_first_match_state.py", "match_recovery_rendering.py", "server.py",
)


def native_play(cdp, family, card):
    form = ('form[action="/sessions/play"]' if family == "session" else
            'form[action="/matches/cards"]:has(input[value="append_plays"])')
    choose(cdp, form + f' input[value="{card}"]')
    cdp.activate(form + ' button')
    wait(cdp)
    assert cdp.evaluate("document.activeElement.id") == family + "-recording"
    assert cdp.evaluate("location.hash") == "#" + family + "-recording"


def create_session(http):
    page = follow(http, http.submit(Forms(http.page("/sessions")).find("/sessions/create"),
        game_name="Synthetic progress Game", capture_mode="live", perspective_seat="forehand",
        forehand_name="Alexandra-Maria von Hohenlohe-Schillingsfuerst",
        middlehand_name="Boris", rearhand_name="Clara", setup_action="update"))
    follow(http, http.submit(Forms(page).find("/sessions/create"), setup_action="create"))
    http.command("set_game_metadata")
    return Forms(http.page()).find("/sessions/cards")


def geometry(cdp):
    return cdp.evaluate("""(() => {
      const box=e=>{if(!e)return null;const r=e.getBoundingClientRect();
        return {top:r.top,left:r.left,width:r.width,height:r.height};};
      const summary=document.querySelector('[data-recorded-summary]');
      const selector=document.querySelector('[data-card-mode=play]');
      const history=document.querySelector('.recorded-history');
      return {locale:document.documentElement.lang,fragment:location.hash,
        viewport:[innerWidth,innerHeight],
        focus:document.activeElement.id,client:document.documentElement.clientWidth,
        scroll:document.documentElement.scrollWidth,summary:box(summary),selector:box(selector),
        recording:box(document.querySelector('#session-recording,#match-recording')),
        visible_totals:summary.innerText,
        totals:[...summary.querySelectorAll('.trick-total')].map(p=>({seat:p.dataset.seat,
          values:[...p.querySelectorAll('dd')].map(e=>Number(e.textContent))})),
        history_count:document.querySelectorAll('.recorded-trick').length,
        history_after_controls:!selector||!history||!!(selector.compareDocumentPosition(history)&4),
        overflow:[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility()&&
          e.getBoundingClientRect().right>document.documentElement.clientWidth+1).map(e=>
          ({tag:e.tagName,classes:e.className,...box(e)})).slice(0,20)};
    })()""")


def sweep(cdp, server, output, run, name, route, expected, *, count, family):
    for locale in ("de", "en"):
        cdp.navigate(server.origin + route)
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        for width, height, scale in ((1365, 900, 1), (390, 844, 1),
                                     (320, 800, 1), (320, 800, 2)):
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                     deviceScaleFactor=1, mobile=False)
            cdp.navigate(server.origin + route + "#" + family + "-recording")
            if scale == 2:
                cdp.evaluate("""(() => {const sizes=[...document.querySelectorAll('body *')]
                  .map(e=>[e,parseFloat(getComputedStyle(e).fontSize)]);
                  for(const [e,size] of sizes)e.style.fontSize=size*2+'px';})()""")
            cdp.evaluate(f"document.getElementById('{family}-recording').scrollIntoView()")
            item = {"state": name, "viewport": [width, height], "text_scale": scale,
                    **geometry(cdp)}
            run["measurements"].append(item)
            assert item["locale"] == locale
            assert [p["values"] for p in item["totals"]] == [list(p) for p in expected], item
            assert item["history_count"] == count and item["history_after_controls"], item
            assert item["client"] == item["scroll"], item
            prefix = f'{run["script"]}-{name}-{locale}-{width}-{scale}'
            item["screenshots"] = []
            for area, selector in (("recording", f"#{family}-recording"),
                                   ("summary", "[data-recorded-summary]"),
                                   ("history", ".recorded-history"),
                                   ("last", ".recorded-trick:last-child")):
                if cdp.evaluate(f"!!document.querySelector({json.dumps(selector)})"):
                    cdp.evaluate(f"document.querySelector({json.dumps(selector)})"
                                 ".scrollIntoView({block:'start'})")
                    filename = prefix + f"-{area}.png"
                    cdp.screenshot(output / filename)
                    item["screenshots"].append(filename)


def unsent_language(cdp, active, family, card, run):
    form = ('form[action="/sessions/play"]' if family == "session" else
            'form[action="/matches/cards"]:has(input[value="append_plays"])')
    choose(cdp, form + f' input[value="{card}"]')
    before = active.path.read_bytes()
    for locale in ("de", "en"):
        cdp.events.clear()
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp)
        assert active.path.read_bytes() == before
        assert posts(cdp) == ["/actions/profile/language"]
        selected = cdp.evaluate(f"[...document.querySelectorAll('{form} input:checked')]"
                                ".map(e=>e.value)")
        assert selected == [card]
    run["unsent_language"].append({"family": family, "card": card, "unchanged_bytes": True})


def native_correction(cdp, card, run):
    cdp.events.clear()
    cdp.activate('#match-play-2 form[action="/matches/recovery/select"] button')
    wait(cdp)
    fill(cdp, 'form[action="/matches/recovery/preview"] select[name=card]', card)
    cdp.activate('form[action="/matches/recovery/preview"] button')
    wait(cdp)
    run["preview_visible_totals"].append(geometry(cdp)["visible_totals"])
    choose(cdp, 'form[action="/matches/recovery/apply"] input[name=confirm_apply]')
    cdp.activate('form[action="/matches/recovery/apply"] button')
    wait(cdp)
    assert cdp.evaluate("document.activeElement.id") == "match-recording"
    run["corrections"].append({"card": card, "posts": posts(cdp), **geometry(cdp)})


def inspect_run(args, output, evidence, javascript):
    script = "js" if javascript else "native"
    context = AppWebContextV1.create(prepare_managed_home_v1(output / f"managed-{script}"))
    server = start_app_web_server_v1(context, port=0, token="localization-test-token")
    thread = serve_app_web_in_thread_v1(server)
    browser = LocalBrowser(args.browser, output / f"browser-{script}")
    cdp = browser.cdp
    http = Browser(server)
    run = {"script": script, "browser": browser.version["product"], "measurements": [],
           "unsent_language": [], "corrections": [], "preview_visible_totals": []}
    evidence["runs"].append(run)
    try:
        cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
        cdp.call("Emulation.setDeviceMetricsOverride", width=320, height=800,
                 deviceScaleFactor=1, mobile=False)
        cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
        time.sleep(.5)
        # All setup uses real returned forms and persistence, with no injected success.
        data = progress_data()
        form = create_session(http)
        follow(http, http.submit(form, cards=data["players"][0]["initial_hand"]))
        http.command("set_declarer")
        http.command("set_declaration", game_type="grand", hand_game="true")
        cdp.navigate(server.origin + "/sessions/current")
        cards = [p["card"] for t in data["tricks"] for p in t["plays"]]
        for card in cards[:5]:
            native_play(cdp, "session", card)
        run["native_session_return"] = geometry(cdp)
        active = context.managed_stateful.active_session
        if javascript:
            unsent_language(cdp, active, "session", cards[5], run)
        sweep(cdp, server, output, run, "session-incomplete", "/sessions/current",
              GRAND_PREFIXES[1], count=2, family="session")
        cdp.navigate(server.origin + "/sessions/current")
        native_play(cdp, "session", cards[5])
        sweep(cdp, server, output, run, "session-completed", "/sessions/current",
              GRAND_PREFIXES[2], count=2, family="session")
        before = active.path.read_bytes()
        rejected = http.submit(Forms(http.page()).find("/sessions/play"), cards="CA")
        assert rejected[0] == 400 and active.path.read_bytes() == before
        sweep(cdp, server, output, run, "session-error", "/sessions/current",
              GRAND_PREFIXES[2], count=2, family="session")
        for card in cards[6:]:
            follow(http, http.submit(Forms(http.page()).find("/sessions/play"), cards=card))
        sweep(cdp, server, output, run, "session-ten", "/sessions/current",
              GRAND_PREFIXES[10], count=10, family="session")
        # A returned correction form establishes a real Null accepted prefix.
        form = next(f for f in Forms(http.page()).forms
                    if f["values"].get("kind") == "set_declaration"
                    and "target_revision" in f["values"])
        revision = next(r.revision for r in active.state.command_log
                        if r.command.kind == "set_declaration")
        follow(http, http.submit(form, target_revision=revision,
                                game_type="null", hand_game="true"))
        # Null removes the Jack-trump winner at Trick 3; existing suffix replay stops at Play 10.
        sweep(cdp, server, output, run, "session-null", "/sessions/current",
              ((3,), (0,), (0,)), count=3, family="session")
        page = start_match(http, name="Alexandra-Maria von Hohenlohe-Schillingsfuerst")
        for card in cards[:5]:
            page = follow(http, http.submit(operation_form(page, "append_plays"), cards=card))
        cdp.navigate(server.origin + "/matches/position/1")
        active = context.managed_stateful.active_match
        if javascript:
            unsent_language(cdp, active, "match", cards[5], run)
        sweep(cdp, server, output, run, "match-incomplete", "/matches/position/1",
              GRAND_PREFIXES[1], count=2, family="match")
        cdp.navigate(server.origin + "/matches/position/1")
        native_play(cdp, "match", cards[5])
        native_correction(cdp, "S9", run)
        sweep(cdp, server, output, run, "match-corrected", "/matches/position/1",
              ((2, 24), (0, 0), (0, 0)), count=2, family="match")
        cdp.navigate(server.origin + "/matches/position/1")
        native_correction(cdp, "SK", run)
        for card in cards[6:]:
            page = http.page("/matches/position/1")
            follow(http, http.submit(operation_form(page, "append_plays"), cards=card))
        sweep(cdp, server, output, run, "match-ten", "/matches/position/1",
              GRAND_PREFIXES[10], count=10, family="match")
        page = http.page("/matches/position/2")
        page = follow(http, http.submit(operation_form(page, "start_game")))
        page = follow(http, http.submit(operation_form(page, "set_declaration"),
            declarer_player_id=active.workspace.match_definition.participants[0].player_id,
            game_type="null", hand_game="on"))
        for card in "C10 CJ CQ".split():
            page = follow(http, http.submit(operation_form(page, "append_plays"), cards=card))
        sweep(cdp, server, output, run, "match-null", "/matches/position/2",
              ((0,), (0,), (1,)), count=1, family="match")
        page = http.page("/matches/position/3")
        page = follow(http, http.submit(operation_form(page, "start_game")))
        page = follow(http, http.submit(operation_form(page, "set_declaration"),
            declarer_player_id=active.workspace.match_definition.participants[0].player_id,
            game_type="grand", hand_game="on"))
        for card in "SA H7 S7 CA S8".split():
            page = follow(http, http.submit(operation_form(page, "append_plays"), cards=card))
        sweep(cdp, server, output, run, "match-warning", "/matches/position/3",
              ((1, 11), (0, 0), (0, 0)), count=2, family="match")
        cdp.navigate(server.origin + "/matches/position/3")
        # An actual existing Advanced ordered-input form can propose a duplicate Card.
        selector = 'form[action="/matches/api/v1/operation"]:has(input[value="append_plays"])'
        cdp.evaluate(f"document.querySelector('{selector}').closest('details').open=true")
        fill(cdp, selector + ' [name=cards]', "SA")
        before = active.path.read_bytes()
        cdp.activate(selector + ' button')
        wait(cdp, error=True)
        assert active.path.read_bytes() == before
        run["native_rejection"] = geometry(cdp)
        sweep(cdp, server, output, run, "match-error", "/matches/position/3",
              ((1, 11), (0, 0), (0, 0)), count=2, family="match")
        cdp.navigate(server.origin + "/matches/position/3")
        cdp.activate('.trick-warning a')
        assert cdp.evaluate("location.hash") == "#match-play-2"
        run["diagnostic_navigation"] = geometry(cdp)
        cdp.screenshot(output / f"{script}-diagnostic-target.png")
        # Hash the real HTTP-delivered bytes in addition to installed modules.
        run["http_resources"] = {}
        for route, resource in (("/assets/app.css", "assets/app.css"),
                                ("/matches/assets/capture.js", "assets/workflow.js")):
            status, _, content = http.request("GET", route)
            assert status == 200
            digest = hashlib.sha256(content).hexdigest()
            assert digest == evidence["resources"][resource]
            run["http_resources"][route] = digest
    finally:
        browser.close()
        server.shutdown()
        server.server_close()
        thread.join(5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh evidence directory under an existing scratch parent")
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install the Wheel first"
    output.mkdir()
    resources = {}
    for resource in RESOURCES:
        loaded = files("skatmind.app_web").joinpath(resource).read_bytes()
        assert loaded == (ROOT / "src/skatmind/app_web" / resource).read_bytes(), resource
        resources[resource] = hashlib.sha256(loaded).hexdigest()
    evidence = {"baseline": "b8eb8e3b0eca8f7df29896e8db1720100ae810f7",
                "python": sys.version.split()[0], "package": skatmind.__version__,
                "resources": resources, "runs": [], "completed": False}
    try:
        for javascript in (True, False):
            inspect_run(args, output, evidence, javascript)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        (output / "summary.json").write_text(json.dumps({"completed": evidence["completed"],
            "measurements": sum(len(run["measurements"]) for run in evidence["runs"]),
            "resources": resources}, indent=2), encoding="utf-8")
    print(json.dumps({"completed": True, "runs": len(evidence["runs"])}))


if __name__ == "__main__":
    main()
