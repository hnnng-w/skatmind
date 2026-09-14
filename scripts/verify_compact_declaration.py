"""Optional installed-Wheel native declaration verification; no runtime dependency."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, contrast, create_session, fill, posts, wait

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.deck import get_full_deck
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.session_transitions import replay_session_state_v1

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "app_web/assets/app.css", "app_web/assets/workflow.js",
    "app_web/locales/en.json", "app_web/locales/de.json", "game_declaration.py",
    "app_web/task_first_session_rendering.py", "app_web/task_first_match_rendering.py",
    "app_web/compact_declaration_form.py", "app_web/compact_declaration_http.py",
    "app_web/compact_declaration_rendering.py", "declaration_diagnostics.py",
    "app_web/form_registry.py", "app_web/validation_mapping.py",
    "app_web/validation_rendering.py", "app_web/server.py", "app_web/session_frontend.py",
)
SESSION = 'form:has(input[name="kind"][value="set_declaration"])'
MATCH = 'form:has(input[name="operation"][value="set_declaration"])'


def measure(cdp, output, evidence, selector, name, *, locale, width, height, scale=1):
    cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
             deviceScaleFactor=1, mobile=False)
    if scale == 2:
        cdp.evaluate("""(() => { const all=[...document.querySelectorAll('body,body *')];
          const sizes=all.map(e=>parseFloat(getComputedStyle(e).fontSize));
          all.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px'); })()""")
    cdp.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView({{block:'start'}})")
    geometry = cdp.evaluate("""(selector => {
      const f=document.querySelector(selector), r=f.getBoundingClientRect();
      const visible=e=>e.checkVisibility({visibilityProperty:true});
      const check=f.querySelector('.declaration-checks label');
      const style=check && getComputedStyle(check);
      return {client:document.documentElement.clientWidth,
        scroll:document.documentElement.scrollWidth,
        form:{width:r.width,height:r.height},
        checkbox_text:style && {color:style.color,background:style.backgroundColor},
        bid_visible:visible(f.querySelector('[name=bid_value]')),
        focus:{tag:document.activeElement.tagName,id:document.activeElement.id,
          outline:getComputedStyle(document.activeElement).outlineColor},
        fields:[...f.querySelectorAll('input,select,button')].map(e=>({name:e.name,type:e.type,
          visible:visible(e),checked:e.checked,required:e.required,disabled:e.disabled})),
        checks:[...f.querySelectorAll('input[type=checkbox]')].map(e=>({name:e.name,
          width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height})),
        overflow:[...document.querySelectorAll('main *')].filter(e=>visible(e) &&
          e.getBoundingClientRect().right>document.documentElement.clientWidth+1).map(e=>
          ({tag:e.tagName,classes:e.className,width:e.getBoundingClientRect().width})).slice(0,12)};
    })(""" + json.dumps(selector) + ")")
    evidence["measurements"].append({"state": name, "locale": locale,
        "viewport": [width, height], "text_scale": scale, **geometry})
    if evidence["phase"] == "after":
        assert geometry["scroll"] == geometry["client"], geometry
        assert geometry["bid_visible"], geometry
        assert all(not field["disabled"] for field in geometry["fields"]), geometry
        pair = geometry["checkbox_text"]
        if pair:
            pair["contrast"] = contrast(pair["color"], pair["background"])
            assert pair["contrast"] >= 4.5
    cdp.screenshot(output / f"{evidence['mode']}-{name}-{locale}-{width}-{scale}.png")
    if evidence["phase"] == "after":
        # Inspect the optional explanation at the same viewport/text scale as its form.
        opened = cdp.evaluate(f"document.querySelector('{selector} .declaration-count').open")
        cdp.evaluate(f"document.querySelector('{selector} .declaration-count').open=true")
        cdp.evaluate(f"document.querySelector('{selector} .declaration-count').scrollIntoView()")
        cdp.screenshot(output / f"{evidence['mode']}-{name}-{locale}-{width}-{scale}-help.png")
        cdp.evaluate(f"document.querySelector('{selector} .declaration-count').open="
                     + json.dumps(opened))


def layout(cdp, output, evidence, selector, name, *, error=False, expanded=False):
    for locale in ("de", "en"):
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp, error=error)
        if expanded:
            cdp.evaluate(f"document.querySelector('{selector} details').open=true")
        for width, height in ((1365, 900), (390, 844), (320, 800)):
            measure(cdp, output, evidence, selector, name, locale=locale,
                    width=width, height=height)
        measure(cdp, output, evidence, selector, name, locale=locale,
                width=320, height=800, scale=2)
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp, error=error)
    # Re-render after representative 200% text so later measurements start at 100%.
    cdp.activate('form.language-selector button[value="de"]')
    wait(cdp, error=error)


def native_save(cdp, selector, evidence, name, *, error=False):
    cdp.events.clear()
    cdp.activate(selector + ' button[type=submit]')
    wait(cdp, error=error)
    assert len(posts(cdp)) == 1, posts(cdp)
    requests = []
    for event in cdp.events:
        request = event["params"]["request"]
        if request["method"] != "POST":
            continue
        fields = parse_qs(request.get("postData", ""), keep_blank_values=True)
        for key in ("managed_handle", "declaration_selection", "_frontend_language_context"):
            if key in fields:
                fields[key] = ["<opaque>"]
        requests.append({"path": urlsplit(request["url"]).path, "fields": fields})
    evidence["actions"][name] = requests
    evidence.setdefault("focus", {})[name] = cdp.evaluate("""(() => {
      const e=document.activeElement,r=e.getBoundingClientRect(),s=getComputedStyle(e);
      return {tag:e.tagName,id:e.id,classes:e.className,top:r.top,
              outline:s.outlineColor,outlineWidth:s.outlineWidth}; })()""")


def resource_evidence(cdp, server, evidence):
    cookies = cdp.call("Network.getCookies", urls=[server.origin])["cookies"]
    cookie = "; ".join(item["name"] + "=" + item["value"] for item in cookies)
    evidence["http_resources"] = {}
    for route, name in (("/assets/app.css", "assets/app.css"),
                        ("/matches/assets/capture.js", "assets/workflow.js")):
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=30)
        try:
            connection.request("GET", route, headers={"Cookie": cookie})
            response = connection.getresponse()
            content = response.read()
            assert response.status == 200
            assert content == files("skatmind.app_web").joinpath(name).read_bytes()
            evidence["http_resources"][route] = hashlib.sha256(content).hexdigest()
        finally:
            connection.close()


def session_flow(cdp, server, context, output, evidence):
    create_session(cdp, server.origin, "Synthetic declaration Game")
    for card in get_full_deck()[:10]:
        choose(cdp, f'form[action="/sessions/cards"] input[value="{card}"]')
    cdp.activate('form[action="/sessions/cards"] button')
    wait(cdp)
    declarer = 'form:has(input[value="set_declarer"])'
    cdp.evaluate(f"document.querySelector('{declarer} select').selectedIndex=1")
    cdp.activate(declarer + ' button')
    wait(cdp)
    layout(cdp, output, evidence, SESSION, "session-normal")
    if evidence["phase"] == "before":
        layout(cdp, output, evidence, SESSION, "session-expanded", expanded=True)
        return
    active = context.managed_stateful.active_session
    before = active.path.read_bytes()
    cdp.events.clear()
    fill(cdp, SESSION + ' [name=game_type]', "grand")
    fill(cdp, SESSION + ' [name=bid_value]', "19")
    choose(cdp, SESSION + ' [name=schneider_announced]')
    assert posts(cdp) == [] and active.path.read_bytes() == before
    evidence["actions"]["session-draft"] = []
    native_save(cdp, SESSION, evidence, "session-dependency", error=True)
    cdp.screenshot(output / f"{evidence['mode']}-session-error-focus.png")
    layout(cdp, output, evidence, SESSION, "session-dependency", error=True)
    assert active.path.read_bytes() == before
    assert cdp.evaluate(f"document.querySelector('{SESSION} [name=schneider_announced]').checked")
    assert not cdp.evaluate(f"document.querySelector('{SESSION} [name=hand_game]').checked")
    choose(cdp, SESSION + ' [name=schneider_announced]')
    if evidence["javascript"]:
        fill(cdp, SESSION + ' [name=bid_value]', "17")
        cdp.events.clear()
        cdp.activate('form.language-selector button[value="en"]')
        wait(cdp, error=True)
        assert posts(cdp) == ["/actions/profile/language"]
        assert cdp.evaluate(f"document.querySelector('{SESSION} [name=bid_value]').value") == "17"
        assert not cdp.evaluate(
            f"document.querySelector('{SESSION} [name=schneider_announced]').checked")
        evidence["unsent_language"] = True
    native_save(cdp, SESSION, evidence, "session-save")
    declaration = replay_session_state_v1(active.state).declaration
    evidence["session_accepted"] = build_serializable_game_declaration(declaration)
    assert active.state.phase == "play" and not declaration.hand_game
    assert cdp.evaluate("document.activeElement.id") == "session-recording"
    cdp.screenshot(output / f"{evidence['mode']}-session-saved-focus.png")
    cdp.evaluate("document.querySelector('.accepted-declaration').scrollIntoView({block:'start'})")
    cdp.screenshot(output / f"{evidence['mode']}-session-accepted.png")
    saved = active.path.read_bytes()
    cdp.navigate(server.origin + "/sessions")
    cdp.activate('form[action="/sessions/open"] button')
    wait(cdp)
    assert context.managed_stateful.active_session.path.read_bytes() == saved
    assert cdp.evaluate("!!document.querySelector('.accepted-declaration')")
    assert cdp.evaluate("!!document.querySelector('form[action=\"/sessions/play\"]')")
    evidence["session_reopened"] = True
    correction = 'form:has(input[value="session-correction"])'
    cdp.evaluate(f"document.querySelector('{correction}').closest('details').open=true")
    cdp.evaluate("document.querySelector('#session-history > details').open=true")
    fill(cdp, correction + ' [name=bid_value]', "29")
    native_save(cdp, correction, evidence, "session-correction")
    declaration = replay_session_state_v1(context.managed_stateful.active_session.state).declaration
    evidence["session_corrected"] = build_serializable_game_declaration(declaration)
    assert declaration.bid_value == 29 and not declaration.hand_game


def match_flow(cdp, server, context, output, evidence):
    cdp.navigate(server.origin + "/matches/new")
    creation = 'form[action="/matches/api/v1/create"]'
    for name, value in {"match_title": "Synthetic declaration Match",
                        "perspective_seat": "forehand",
                        "forehand_name": "Alexandra-Maria " + "Long synthetic name " * 5,
                        "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, creation + f' [name="{name}"]', value.strip())
    cdp.activate(creation + ' button[value="update"]')
    wait(cdp)
    cdp.activate(creation + ' button[value="create"]')
    wait(cdp)
    cdp.activate('form:has(input[value="start_game"]) button')
    wait(cdp)
    layout(cdp, output, evidence, MATCH, "match-normal")
    if evidence["phase"] == "before":
        return
    active = context.managed_stateful.active_match
    before = active.path.read_bytes()
    cdp.events.clear()
    cdp.evaluate(f"document.querySelector('{MATCH} [name=declarer_player_id]').selectedIndex=1")
    fill(cdp, MATCH + ' [name=game_type]', "grand")
    fill(cdp, MATCH + ' [name=bid_value]', "19")
    assert posts(cdp) == [] and active.path.read_bytes() == before
    evidence["actions"]["match-draft"] = []
    native_save(cdp, MATCH, evidence, "match-save")
    assert cdp.evaluate("document.activeElement.id") == "match-recording"
    cdp.screenshot(output / f"{evidence['mode']}-match-saved-focus.png")
    editor = '#match-declaration ' + MATCH
    cdp.evaluate("document.querySelector('#match-declaration').closest('details').open=true")
    fill(cdp, editor + ' [name=game_type]', "null")
    cdp.evaluate(f"document.querySelector('{editor} details').open=true")
    fill(cdp, editor + ' [name=matadors]', "2")
    choose(cdp, editor + ' [name=schneider_announced]')
    before = active.path.read_bytes()
    native_save(cdp, editor, evidence, "match-null-count", error=True)
    cdp.screenshot(output / f"{evidence['mode']}-match-error-focus.png")
    layout(cdp, output, evidence, editor, "match-null-error", error=True)
    assert active.path.read_bytes() == before
    fill(cdp, editor + ' [name=matadors]', "")
    native_save(cdp, editor, evidence, "match-null-announcement", error=True)
    choose(cdp, editor + ' [name=schneider_announced]')
    choose(cdp, editor + ' [name=ouvert]')
    fill(cdp, editor + ' [name=bid_value]', "")
    if evidence["javascript"]:
        cdp.events.clear()
        cdp.activate('form.language-selector button[value="en"]')
        wait(cdp, error=True)
        assert posts(cdp) == ["/actions/profile/language"]
        assert cdp.evaluate(f"document.querySelector('{editor} [name=matadors]').value") == ""
        assert cdp.evaluate(f"document.querySelector('{editor} [name=bid_value]').value") == ""
    native_save(cdp, editor, evidence, "match-null-save")
    game = active.workspace.slots[0].observed_game
    evidence["match_accepted"] = build_serializable_game_declaration(game.declaration)
    assert game.declaration.ouvert and not game.declaration.hand_game
    assert game.declaration.matadors is None and game.declaration.bid_value is None
    cdp.evaluate("document.querySelector('.accepted-declaration').scrollIntoView({block:'start'})")
    cdp.screenshot(output / f"{evidence['mode']}-match-accepted.png")
    play = 'form[action="/matches/cards"]:has(input[value="append_plays"])'
    choose(cdp, play + ' input[value="CA"]')
    native_save(cdp, play, evidence, "match-next-card")
    saved = active.path.read_bytes()
    cdp.navigate(server.origin + "/matches")
    cdp.activate('form[action="/matches/open"] button')
    wait(cdp)
    assert context.managed_stateful.active_match.path.read_bytes() == saved
    assert cdp.evaluate("!!document.querySelector('.accepted-declaration')")
    evidence["match_reopened"] = True


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    hashes = {}
    for resource in MODULES:
        loaded = files("skatmind").joinpath(resource)
        if args.phase == "before" and not loaded.is_file():
            continue
        content = loaded.read_bytes()
        if args.phase == "after":
            assert content == (ROOT / "src/skatmind" / resource).read_bytes(), resource
        hashes[resource] = hashlib.sha256(content).hexdigest()
    evidence = {"baseline": "9f4a172c07d6aff26c2e378ac50ee90293150673", "phase": args.phase,
                "python": sys.version.split()[0], "package": skatmind.__version__,
                "hashes": hashes, "runs": [], "completed": False}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(
                prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="declaration-local-evidence")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            cdp = browser.cdp
            item = {"javascript": javascript, "mode": mode, "phase": args.phase,
                    "browser": browser.version["product"], "measurements": [], "actions": {}}
            evidence["runs"].append(item)
            try:
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=declaration-local-evidence")
                time.sleep(.5)
                session_flow(cdp, server, context, output, item)
                match_flow(cdp, server, context, output, item)
                resource_evidence(cdp, server, item)
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        count = sum(len(run["measurements"]) for run in evidence["runs"])
        summary = {"completed": evidence["completed"], "phase": args.phase, "measurements": count,
                   "normal_heights": [{key: row[key] for key in (
                       "state", "locale", "viewport", "text_scale", "form", "bid_visible")}
                       for row in evidence["runs"][0]["measurements"]
                       if row["state"].endswith(("normal", "expanded"))]}
        if args.baseline:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            old = {(row["state"], row["locale"], tuple(row["viewport"]), row["text_scale"]): row
                   for row in baseline["runs"][0]["measurements"]}
            for row in summary["normal_heights"]:
                previous = old.get((row["state"], row["locale"],
                                    tuple(row["viewport"]), row["text_scale"]))
                if previous:
                    row["before_form"] = previous["form"]
                if row["state"] == "session-normal":
                    expanded = old.get(("session-expanded", row["locale"],
                                        tuple(row["viewport"]), row["text_scale"]))
                    if expanded:
                        row["before_with_bid_visible"] = expanded["form"]
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    parser.add_argument("--baseline", type=Path)
    run(parser.parse_args())
