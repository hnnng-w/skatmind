"""Optional real installed-Wheel Card-entry evidence using dependency-free DevTools."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from _workflow_visual_browser import LocalBrowser

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_historical_game import build_historical_input  # noqa: E402

BASELINE = "392fef89f19c0c93686e5be0b8c6163b1f8bc553"
MODULES = (
    "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json",
    "session_frontend.py", "task_first_session_rendering.py", "task_first_match_rendering.py",
    "form_registry.py", "validation_rendering.py", "language_context.py", "server.py",
    "card_entry_http.py", "session_card_entry.py", "compact_card_rendering.py",
    "stateful_context.py", "match_frontend.py", "validation_mapping.py",
)


def wait(cdp, *, error=False):
    time.sleep(.15)
    for _ in range(100):
        if cdp.evaluate("document.readyState==='complete'"):
            break
        time.sleep(.1)
    else:
        raise AssertionError("Native navigation did not complete")
    assert cdp.evaluate("!!document.querySelector('.error-summary')") == error


def fill(cdp, selector, value):
    cdp.evaluate(f"document.querySelector({json.dumps(selector)}).value={json.dumps(value)}")


def choose(cdp, selector):
    cdp.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'center'}})")
    cdp.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
    cdp.call("Input.dispatchKeyEvent", type="keyDown", key=" ", code="Space",
             windowsVirtualKeyCode=32, text=" ")
    cdp.call("Input.dispatchKeyEvent", type="keyUp", key=" ", code="Space",
             windowsVirtualKeyCode=32)


def posts(cdp):
    cdp.evaluate("void 0")  # Drain pending DevTools events.
    return [urlsplit(event["params"]["request"]["url"]).path for event in cdp.events
            if event["params"]["request"]["method"] == "POST"]


def create_session(cdp, origin, name):
    cdp.navigate(origin + "/sessions")
    form = 'form[action="/sessions/create"]'
    for key, value in {"game_name": name, "perspective_seat": "forehand",
                       "forehand_name": ("Alexandra-Maria " + "Long synthetic name " * 5).strip(),
                       "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, form + f' [name="{key}"]', value)
    choose(cdp, form + ' input[value="live"]')
    cdp.activate(form + ' button[value="update"]')
    wait(cdp)
    cdp.activate(form + ' button[value="create"]')
    wait(cdp)
    cdp.activate('form:has(input[name="kind"][value="set_game_metadata"]) button')
    wait(cdp)


def measure(cdp, output, evidence, name, *, locale, width, height, scale=1):
    geometry = cdp.evaluate("""(() => {
      const f=document.querySelector('.compact-cards') || document.querySelector('#session-app');
      const selected=[...document.querySelectorAll('.compact-cards input:checked')].map(e=>e.value);
      const card=document.querySelector('.compact-card');
      const style=card && getComputedStyle(card);
      const rect=f.getBoundingClientRect();
      return {client:document.documentElement.clientWidth,
        scroll:document.documentElement.scrollWidth,
        overflow:[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility() &&
          e.getBoundingClientRect().right>document.documentElement.clientWidth+1).map(e=>
          ({tag:e.tagName,classes:e.className,width:e.getBoundingClientRect().width})).slice(0,20),
        selector:{width:rect.width,height:rect.height},selected,
        card:card && {width:card.getBoundingClientRect().width,
          height:card.getBoundingClientRect().height,color:style.color,background:style.backgroundColor,
          border:style.borderColor},active:document.activeElement.tagName,
        focus:getComputedStyle(document.activeElement).outlineColor,
        focusWidth:getComputedStyle(document.activeElement).outlineWidth,
        cardFocus:document.querySelector('.compact-card:focus-within') &&
          getComputedStyle(document.querySelector('.compact-card:focus-within')).outlineColor,
        resources:[...document.querySelectorAll('link[rel=stylesheet],script[src]')].map(
          e=>new URL(e.href||e.src).pathname)};
    })()""")
    evidence["measurements"].append({"name": name, "locale": locale,
        "viewport": [width, height], "text_scale": scale, **geometry})
    if evidence["phase"] == "after":
        assert geometry["client"] == geometry["scroll"], geometry
        pair = geometry["card"]
        if pair:
            pair["contrast"] = contrast(pair["color"], pair["background"])
            pair["border_contrast"] = contrast(pair["border"], pair["background"])
            assert pair["contrast"] >= 4.5 and pair["border_contrast"] >= 3, pair
    cdp.evaluate("(document.querySelector('.compact-cards') || "
                 "document.querySelector('#session-app'))"
                 ".scrollIntoView({block:'start'})")
    cdp.screenshot(output / f"{name}-{locale}-{width}-{scale}.png")
    if scale == 2:
        cdp.evaluate("document.querySelector('.compact-card-choices').scrollIntoView({block:'start'})")
        cdp.screenshot(output / f"{name}-{locale}-{width}-{scale}-cards.png")


def contrast(foreground, background):
    def luminance(color):
        channels = [int(value.strip()) / 255
                    for value in color.split('(')[1].split(')')[0].split(',')]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels[:3]]
        return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722), strict=True))
    a, b = sorted((luminance(foreground), luminance(background)))
    return (b + .05) / (a + .05)


def match_flow(cdp, server, context, output, evidence, suffix, hand):
    cdp.navigate(server.origin + "/matches/new")
    form = 'form[action="/matches/api/v1/create"]'
    for key, value in {"match_title": "Synthetic compact Match", "perspective_seat": "forehand",
                       "forehand_name": "Alexandra-Maria von Hohenlohe-Schillingsfuerst",
                       "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, form + f' [name="{key}"]', value)
    cdp.activate(form + ' button[value="update"]')
    wait(cdp)
    cdp.activate(form + ' button[value="create"]')
    wait(cdp)
    cdp.activate('form:has(input[value="start_game"]) button')
    wait(cdp)
    declaration = 'form:has(input[value="set_declaration"])'
    cdp.evaluate(f"document.querySelector('{declaration} "
                 "[name=declarer_player_id]').selectedIndex=1")
    fill(cdp, declaration + ' [name=game_type]', "grand")
    choose(cdp, declaration + ' input[name=hand_game]')
    cdp.activate(declaration + ' button')
    wait(cdp)
    play = 'form[action="/matches/cards"]:has(input[value="append_plays"])'
    choose(cdp, play + f' input[value="{hand[0]}"]')
    cdp.activate(play + ' button')
    wait(cdp)
    evidence_form = 'form[action="/matches/cards"]:has(input[value="set_perspective_hand"])'
    # Open the optional hand editor, then enter original evidence containing its owner's Play.
    cdp.activate('#match-recording details:has(input[value="set_perspective_hand"]) > summary')
    fill(cdp, evidence_form + ' [name=card_evidence_mode]', "exact")
    for card in hand:
        choose(cdp, evidence_form + f' input[value="{card}"]')
    cdp.events.clear()
    cdp.activate(evidence_form + ' button')
    wait(cdp)
    assert posts(cdp) == ["/matches/cards"]
    active = context.managed_stateful.active_match
    assert set(active.workspace.slots[0].observed_game.perspective_initial_hand) == set(hand)
    for locale in ("de", "en"):
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp)
        for width, height in ((1365, 900), (390, 844), (320, 800)):
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                     deviceScaleFactor=1, mobile=False)
            measure(cdp, output, evidence, suffix + "-match", locale=locale,
                    width=width, height=height)
    assert cdp.evaluate(f"document.querySelector('{play} input[value=\"{hand[0]}\"]')===null")
    choose(cdp, play + ' input[value="H7"]')
    cdp.activate(play + ' button')
    wait(cdp)
    choose(cdp, play + ' input[value="D7"]')
    cdp.activate(play + ' button')
    wait(cdp)
    assert cdp.evaluate("document.activeElement.id") == "match-recording"
    assert len(active.workspace.slots[0].observed_game.plays) == 3
    evidence["match_initial_hand_after_play"] = True


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh evidence directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install the Wheel first"
    hashes = {}
    for resource in MODULES:
        loaded = files("skatmind.app_web").joinpath(resource)
        if args.phase == "before" and not loaded.is_file():
            continue
        content = loaded.read_bytes()
        if args.phase == "after":
            assert content == (ROOT / "src/skatmind/app_web" / resource).read_bytes(), resource
        hashes[resource] = hashlib.sha256(content).hexdigest()
    evidence = {"baseline": BASELINE, "phase": args.phase, "package": skatmind.__version__,
                "python": sys.version.split()[0], "resources": hashes, "runs": []}
    try:
        for javascript in (True, False):
            suffix = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / f"managed-{suffix}"))
            server = start_app_web_server_v1(context, port=0, token="compact-local-evidence")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / f"browser-{suffix}")
            cdp = browser.cdp
            run_evidence = {"javascript": javascript, "browser": browser.version["product"],
                            "phase": args.phase, "measurements": [], "post_sequences": {}}
            evidence["runs"].append(run_evidence)
            try:
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=compact-local-evidence")
                time.sleep(.5)
                create_session(cdp, server.origin, "Synthetic compact recording")
                data = build_historical_input(hand_game=True, declarer_player_id="player-a",
                                             bid_value=24)
                hand = data["players"][0]["initial_hand"]
                cdp.events.clear()
                if args.phase == "before":
                    cdp.call("Emulation.setDeviceMetricsOverride", width=1365, height=900,
                             deviceScaleFactor=1, mobile=False)
                    measure(cdp, output, run_evidence, suffix + "-hand", locale="en",
                            width=1365, height=900)
                    for card in hand:
                        fill(cdp, 'form:has(input[value="record_dealt_card"]) '
                             'select[name=card]', card)
                        cdp.activate('form:has(input[value="record_dealt_card"]) button')
                        wait(cdp)
                    run_evidence["post_sequences"]["ten_cards"] = posts(cdp)
                    assert len(posts(cdp)) == 10
                    continue
                form = 'form[action="/sessions/cards"]'
                for card in hand:
                    choose(cdp, form + f' input[value="{card}"]')
                assert posts(cdp) == []
                run_evidence["post_sequences"]["select_ten"] = posts(cdp)
                before = context.managed_stateful.active_session.path.read_bytes()
                if javascript:
                    selection = cdp.evaluate("[...document.querySelectorAll('.compact-cards "
                                             "input:checked')].map(e=>e.value)")
                    cdp.activate('form.language-selector button[value="de"]')
                    wait(cdp)
                    assert cdp.evaluate("[...document.querySelectorAll('.compact-cards "
                                        "input:checked')].map(e=>e.value)") == selection
                    assert context.managed_stateful.active_session.path.read_bytes() == before
                    run_evidence["post_sequences"]["unsent_language"] = posts(cdp)
                # Reflow/200%-text measurements use returned controls and native pending selections.
                for locale in ("de", "en"):
                    cdp.activate(f'form.language-selector button[value="{locale}"]')
                    wait(cdp)
                    if not javascript:
                        for card in hand:
                            choose(cdp, form + f' input[value="{card}"]')
                    for width, height in ((1365, 900), (390, 844), (320, 800)):
                        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                                 deviceScaleFactor=1, mobile=False)
                        measure(cdp, output, run_evidence, suffix + "-hand", locale=locale,
                                width=width, height=height)
                    cdp.evaluate("""(() => {const sizes=[...document.querySelectorAll('body *')]
                      .map(e=>[e,parseFloat(getComputedStyle(e).fontSize)]);
                      for(const [e,size] of sizes)e.style.fontSize=size*2+'px';})()""")
                    measure(cdp, output, run_evidence, suffix + "-hand", locale=locale,
                            width=320, height=800, scale=2)
                cdp.events.clear()
                cdp.activate(form + ' button')
                wait(cdp)
                run_evidence["post_sequences"]["ten_cards"] = posts(cdp)
                assert posts(cdp) == ["/sessions/cards"]
                assert context.managed_stateful.active_session.state.phase == "declaration"
                cdp.activate('form:has(input[value="set_declarer"]) button')
                wait(cdp)
                fill(cdp, 'form:has(input[value="set_declaration"]) [name=game_type]', "grand")
                fill(cdp, 'form:has(input[value="set_declaration"]) [name=hand_game]', "true")
                cdp.activate('form:has(input[value="set_declaration"]) button')
                wait(cdp)
                cdp.events.clear()
                plays = [p for trick in data["tricks"] for p in trick["plays"]]
                for play in plays[:5]:
                    form = 'form[action="/sessions/play"]'
                    assert cdp.evaluate(
                        f"document.querySelectorAll('{form} input:checked').length") == 0
                    choose(cdp, form + f' input[value="{play["card"]}"]')
                    cdp.activate(form + ' button')
                    wait(cdp)
                    assert cdp.evaluate("location.hash") == "#session-recording"
                    assert cdp.evaluate("document.activeElement.id") == "session-recording"
                run_evidence["success_focus"] = cdp.evaluate("""({
                  id:document.activeElement.id,
                  top:document.activeElement.getBoundingClientRect().top,
                  outline:getComputedStyle(document.activeElement).outlineColor})""")
                cdp.screenshot(output / f"{suffix}-recording-focus.png")
                run_evidence["post_sequences"]["five_plays"] = posts(cdp)
                assert posts(cdp) == ["/sessions/play"] * 5
                measure(cdp, output, run_evidence, suffix + "-next-trick", locale="en",
                        width=320, height=800)
                # Another real current setup: eligible local Declarer pickup/discards.
                create_session(cdp, server.origin, "Synthetic pickup recording")
                form = 'form[action="/sessions/cards"]'
                for card in hand + ["D7"]:
                    choose(cdp, form + f' input[value="{card}"]')
                before = context.managed_stateful.active_session.path.read_bytes()
                cdp.activate(form + ' button')
                wait(cdp, error=True)
                assert context.managed_stateful.active_session.path.read_bytes() == before
                assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
                run_evidence["error_focus"] = cdp.evaluate("""({
                  classes:document.activeElement.className,
                  top:document.activeElement.getBoundingClientRect().top})""")
                cdp.screenshot(output / f"{suffix}-error-focus.png")
                measure(cdp, output, run_evidence, suffix + "-error", locale="en",
                        width=320, height=800)
                choose(cdp, form + ' input[value="D7"]')
                cdp.activate(form + ' button')
                wait(cdp)
                cdp.activate('form:has(input[value="set_declarer"]) button')
                wait(cdp)
                fill(cdp, 'form:has(input[value="set_declaration"]) [name=game_type]', "grand")
                cdp.activate('form:has(input[value="set_declaration"]) button')
                wait(cdp)
                for task, cards in (("skat", ["D7", "H7"]), ("discard", ["D7", hand[0]])):
                    cdp.events.clear()
                    for card in cards:
                        choose(cdp, form + f' input[value="{card}"]')
                    assert posts(cdp) == []
                    measure(cdp, output, run_evidence, suffix + "-" + task, locale="en",
                            width=320, height=800)
                    cdp.activate(form + ' button')
                    wait(cdp)
                    run_evidence["post_sequences"][task] = posts(cdp)
                    assert posts(cdp) == ["/sessions/cards"]
                assert context.managed_stateful.active_session.state.phase == "play"
                match_flow(cdp, server, context, output, run_evidence, suffix, hand)
                run_evidence["completed"] = True
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        (output / "summary.json").write_text(json.dumps({
            "completed": evidence.get("completed", False),
            "runs": len(evidence["runs"]), "measurements": sum(len(run["measurements"])
              for run in evidence["runs"])}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), default="after")
    run(parser.parse_args())
