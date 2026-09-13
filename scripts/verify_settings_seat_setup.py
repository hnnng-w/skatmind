"""Optional installed-browser evidence for Settings and explicit first-Game seats.

Uses the existing dependency-free local DevTools harness, outside runtime checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from importlib.resources import files
from pathlib import Path

from _workflow_visual_browser import LocalBrowser

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

SOURCE_COMMIT = "fca43d777998218b6bd438c947ab64bb4cda0ba1"


def fill(cdp, name, value):
    cdp.evaluate(f"document.querySelector('[name={name}]').value={json.dumps(value)}")


def wait(cdp):
    for _ in range(100):
        time.sleep(.1)
        if cdp.evaluate("document.readyState==='complete'"):
            break
    else:
        raise AssertionError("Native navigation did not complete.")
    assert not cdp.evaluate("!!document.querySelector('.error-summary')")


def baseline(args):
    """Inspect the already retained #224 installed Wheel; never rewrite the checkout."""
    output = args.output.resolve()
    output.mkdir()
    context = AppWebContextV1.create(prepare_managed_home_v1(output / "managed"))
    server = start_app_web_server_v1(context, port=0, token="settings-baseline")
    thread = serve_app_web_in_thread_v1(server)
    browser = LocalBrowser(args.browser, output / "browser")
    cdp = browser.cdp
    evidence = {"source_commit": SOURCE_COMMIT, "browser": browser.version["product"],
                "measurements": [], "resource_hashes": {}}
    try:
        assert not Path(skatmind.__file__).resolve().is_relative_to(Path(__file__).parents[1])
        for resource in ("assets/app.css", "assets/workflow.js"):
            evidence["resource_hashes"][resource] = hashlib.sha256(
                files("skatmind.app_web").joinpath(resource).read_bytes()).hexdigest()
        cdp.call("Page.navigate", url=server.origin + "/?token=settings-baseline")
        time.sleep(.5)
        for name in ("Alexandra-Maria " + "Long synthetic name " * 5, "Boris", "Clara"):
            cdp.navigate(server.origin + "/about")
            cdp.activate("details.add-player summary")
            cdp.evaluate("document.querySelector('form[action$=\"/players/add\"] "
                         "[name=display_name]').value=" + json.dumps(name.strip()))
            cdp.activate('form[action$="/players/add"] button')
            wait(cdp)
        cdp.evaluate("document.querySelector('[name=own_player_handle]').selectedIndex=1")
        cdp.activate('form[action$="/profile/preferences"] button')
        wait(cdp)
        for locale in ("de", "en"):
            for width, height in ((1365, 900), (390, 844), (320, 800)):
                cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                         deviceScaleFactor=1, mobile=False)
                for route in ("/about", "/sessions", "/matches/new"):
                    cdp.navigate(server.origin + route)
                    cdp.activate(f'form.language-selector button[value="{locale}"]')
                    wait(cdp)
                    measured = cdp.evaluate("""({width:document.documentElement.clientWidth,
                      scroll:document.documentElement.scrollWidth,
                      height:document.documentElement.scrollHeight,
                      forms:document.querySelectorAll('main form').length,
                      playerInputs:document.querySelectorAll('main [name=display_name]').length
                    })""")
                    evidence["measurements"].append({"route": route, "locale": locale,
                                                     "viewport": [width, height], **measured})
                    filename = f"{locale}-{width}-{route.strip('/').replace('/', '-')}.png"
                    cdp.screenshot(output / filename, whole=True)
        evidence["completed"] = True
    finally:
        browser.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        (output / "evidence.json").write_text(
            json.dumps(evidence, indent=2), encoding="utf-8")


def run(args):
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Use a fresh evidence directory.")
    output.mkdir()
    root = Path(__file__).resolve().parents[1]
    if args.expect_installed and Path(skatmind.__file__).resolve().is_relative_to(root):
        raise ValueError("Installed verification must not load SkatMind from the checkout.")
    resources = {}
    for resource in ("assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json",
                     "player_seat_setup.py", "settings_forms.py", "profile_driven_creation.py",
                     "profile_settings_rendering.py", "seat_setup_rendering.py"):
        content = files("skatmind.app_web").joinpath(resource).read_bytes()
        assert content == (root / "src/skatmind/app_web" / resource).read_bytes()
        resources[resource] = hashlib.sha256(content).hexdigest()
    evidence = {"source_commit": SOURCE_COMMIT, "package": skatmind.__version__,
                "installed": args.expect_installed, "resources": resources, "runs": []}
    for javascript in (True, False):
        suffix = "script" if javascript else "native"
        context = AppWebContextV1.create(prepare_managed_home_v1(output / f"managed-{suffix}"))
        server = start_app_web_server_v1(context, port=0, token="local-settings-verification")
        thread = serve_app_web_in_thread_v1(server)
        browser = LocalBrowser(args.browser, output / f"browser-{suffix}")
        cdp = browser.cdp
        run_evidence = {"javascript": javascript, "browser": browser.version["product"],
                        "measurements": [], "assignments": {}}
        evidence["runs"].append(run_evidence)
        try:
            cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
            cdp.call("Page.navigate", url=server.origin + "/?token=local-settings-verification")
            time.sleep(.5)
            cdp.navigate(server.origin + "/settings")
            names = (("Alexandra-Maria " + "Long synthetic name " * 5).strip(), "Boris", "Clara")
            for name in names:
                cdp.activate('form[action$="/players/edit"]:has(input[value=""]) button')
                wait(cdp)
                fill(cdp, "display_name", name)
                cdp.activate('form[action$="/players/add"] button')
                wait(cdp)
            cdp.evaluate("document.querySelector('[name=own_player_handle]').selectedIndex=1")
            cdp.activate('form[action$="/profile/preferences"] button')
            wait(cdp)
            assert len(context.frontend_profile.document.known_players) == 3
            for family, route, action, title_field in (
                ("sessions", "/sessions", "/sessions/create", "game_name"),
                ("matches", "/matches/new", "/matches/api/v1/create", "match_title"),
            ):
                cdp.navigate(server.origin + route)
                assert cdp.evaluate("document.querySelector('[name=own_seat]').value") == ""
                fill(cdp, "own_seat", "rearhand")
                cdp.activate(f'form[action="{action}"] button[value="update"]')
                wait(cdp)
                cdp.evaluate("document.querySelector('[name=forehand_handle]').selectedIndex=2")
                cdp.evaluate("document.querySelector('[name=middlehand_handle]').selectedIndex=3")
                fill(cdp, title_field, f"Browser {family} {suffix}")
                fill(cdp, "own_seat", "forehand")
                cdp.activate(f'form[action="{action}"] button[value="update"]')
                assert cdp.evaluate("!!document.querySelector('.error-summary')")
                assert cdp.evaluate("document.activeElement.classList.contains('error-summary')")
                cdp.screenshot(output / f"{suffix}-{family}-collision.png", whole=True)
                fill(cdp, "own_seat", "rearhand")
                cdp.activate(f'form[action="{action}"] button[value="update"]')
                wait(cdp)
                assert names[0] in cdp.evaluate(
                    "document.querySelector('.roster-summary').innerText")
                cdp.screenshot(output / f"{suffix}-{family}-roster.png", whole=True)
                cdp.activate(f'form[action="{action}"] button[value="create"]')
                wait(cdp)
                if family == "sessions":
                    session = context.managed_stateful.active_session
                    run_evidence["assignments"][family] = [
                        [p.seat, p.player_label] for p in session.state.players]
                    own = next(p for p in session.state.players if p.player_label == names[0])
                    assert own.seat == "rearhand" and session.state.local_player_id == own.player_id
                else:
                    cdp.activate('form:has(input[name="operation"][value="start_game"]) button')
                    wait(cdp)
                    match = context.managed_stateful.active_match
                    loaded = load_match_workspace_file_v1(match.path).document.workspace
                    game = loaded.slots[0].observed_game
                    labels = {p.player_id: p.player_label
                              for p in match.workspace.match_definition.participants}
                    run_evidence["assignments"][family] = [
                        [p.seat, labels[p.player_id]] for p in game.players]
                    assert labels[game.perspective_player_id] == names[0]
                    assert next(p.seat for p in game.players
                                if p.player_id == game.perspective_player_id) == "rearhand"
                    cdp.screenshot(output / f"{suffix}-first-game.png", whole=True)
                    cdp.navigate(server.origin + "/matches")
                    cdp.activate('form[action="/matches/open"] button')
                    wait(cdp)
                    assert context.managed_stateful.active_match.workspace == match.workspace
            session_bytes, match_bytes = session.path.read_bytes(), match.path.read_bytes()
            cdp.navigate(server.origin + "/settings")
            cdp.activate('form[action$="/players/remove-preview"] button')
            wait(cdp)
            cdp.screenshot(output / f"{suffix}-remove-preview.png", whole=True)
            cdp.activate('form[action$="/players/cancel"] button')
            wait(cdp)
            assert len(context.frontend_profile.document.known_players) == 3
            cdp.activate('form[action$="/players/remove-preview"] button')
            wait(cdp)
            cdp.evaluate("document.querySelector('[name=confirm_replace]').focus()")
            cdp.call("Input.dispatchKeyEvent", type="keyDown", key=" ", code="Space",
                     windowsVirtualKeyCode=32, text=" ")
            cdp.call("Input.dispatchKeyEvent", type="keyUp", key=" ", code="Space",
                     windowsVirtualKeyCode=32)
            cdp.activate('form[action$="/players/remove"] button')
            wait(cdp)
            assert len(context.frontend_profile.document.known_players) == 2
            assert (session.path.read_bytes() == session_bytes
                    and match.path.read_bytes() == match_bytes)
            run_evidence["recording_bytes_unchanged"] = True
            cdp.activate('form[action$="/players/edit"]:has(input[value=""]) button')
            fill(cdp, "display_name", names[0])
            cdp.activate('form[action$="/players/add"] button')
            wait(cdp)
            cdp.evaluate("document.querySelector('[name=own_player_handle]').selectedIndex=3")
            cdp.activate('form[action$="/profile/preferences"] button')
            wait(cdp)
            for locale in ("de", "en"):
                for width, height in ((1365, 900), (390, 844), (320, 800)):
                    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                             deviceScaleFactor=1, mobile=False)
                    for route in ("/settings", "/sessions", "/matches/new"):
                        cdp.navigate(server.origin + route)
                        cdp.activate(f'form.language-selector button[value="{locale}"]')
                        wait(cdp)
                        if route == "/settings":
                            cdp.activate('form[action$="/players/edit"] button')
                            wait(cdp)
                        assert cdp.evaluate("document.documentElement.lang") == locale
                        state = route.strip('/').replace('/', '-')
                        for scale in ((1, 2) if width == 320 else (1,)):
                            if scale == 2:
                                cdp.evaluate("""(() => {
                                  const sizes = [...document.querySelectorAll('body *')].map(
                                    e => [e, parseFloat(getComputedStyle(e).fontSize)]);
                                  for (const [e, size] of sizes) e.style.fontSize = size * 2 + 'px';
                                })()""")
                            geometry = cdp.evaluate("""({width:document.documentElement.clientWidth,
                              scroll:document.documentElement.scrollWidth,
                              height:document.documentElement.scrollHeight,
                              forms:document.querySelectorAll('main form').length,
                              playerInputs:document.querySelectorAll(
                                'main [name=display_name]').length,
                              styles:[...document.querySelectorAll('link[rel=stylesheet]')].map(e=>e.getAttribute('href'))})""")
                            if geometry["width"] != geometry["scroll"]:
                                geometry["offenders"] = cdp.evaluate("""
                                  [...document.querySelectorAll('main *')]
                                  .filter(e=>e.getBoundingClientRect().right>document.documentElement.clientWidth)
                                  .map(e=>({tag:e.tagName,cls:e.className,name:e.getAttribute('name')}))""")
                                run_evidence["failure"] = geometry
                                cdp.screenshot(output / "overflow.png", whole=True)
                            assert geometry["width"] == geometry["scroll"], (route, width, geometry)
                            assert geometry["styles"] == ["/assets/app.css"]
                            geometry["focus"] = cdp.evaluate("""(() => {
                              const e = document.querySelector(
                                'button[value="update"], .player-editor button');
                              e.focus(); const style = getComputedStyle(e);
                              return {outline: style.outlineStyle, width: style.outlineWidth};
                            })()""")
                            assert geometry["focus"]["outline"] != "none"
                            run_evidence["measurements"].append({"route": route, "locale": locale,
                                "viewport": [width, height], "text_scale": scale, **geometry})
                            cdp.screenshot(
                                output / f"{suffix}-{locale}-{width}-{state}-{scale}.png",
                                whole=True)
            # Unsent input is presentation-only and requires the optional enhancement.
            if javascript:
                cdp.navigate(server.origin + "/sessions")
                fill(cdp, "game_name", "Safe unsent name")
                cdp.activate('form.language-selector button[value="de"]')
                wait(cdp)
                assert cdp.evaluate(
                    "document.querySelector('[name=game_name]').value") == "Safe unsent name"
                run_evidence["safe_unsent_language"] = True
            run_evidence["loaded_resources"] = sorted({
                event["params"]["request"]["url"].removeprefix(server.origin)
                for event in cdp.events
                if "/assets/" in event["params"]["request"]["url"]
                and event["params"]["request"]["url"].startswith(server.origin)})
            run_evidence["post_paths"] = [
                event["params"]["request"]["url"].removeprefix(server.origin)
                for event in cdp.events if event["params"]["request"]["method"] == "POST"
                and event["params"]["request"]["url"].startswith(server.origin)]
        finally:
            browser.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            (output / "evidence.json").write_text(
                json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(json.dumps({"completed": True,
        "measurements": sum(len(run["measurements"]) for run in evidence["runs"])}),
        encoding="utf-8")
    print("Installed Settings/seat browser verification completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-installed", action="store_true")
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    baseline(args) if args.baseline else run(args)
