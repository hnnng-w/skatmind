"""Optional installed-Wheel direct-start evidence using existing local DevTools tooling."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, contrast, fill, posts, wait
from verify_compact_declaration import resource_evidence
from verify_local_time_entry import native_select, time_values

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "aecd151aafff1601b0366bb024e65a98006f4240"
MODULES = ("assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json",
    "task_first_projections.py", "session_card_entry.py", "card_entry_http.py",
    "session_frontend.py", "task_first_session_rendering.py", "compact_card_rendering.py",
    "local_time_http.py", "local_time_rendering.py", "local_time_forms.py",
    "friendly_creation_rendering.py", "profile_driven_creation.py", "player_seat_setup.py",
    "language_context.py", "language_form_preservation.py", "form_registry.py", "server.py")
CARDS = 'form[action="/sessions/cards"]'
METADATA = 'form:has(input[name="time_form"][value="session-metadata"])'


def focus(cdp):
    return cdp.evaluate("""(() => {const e=document.activeElement,s=getComputedStyle(e);
        return {id:e.id,tag:e.tagName,outline:s.outlineColor,width:s.outlineWidth};})()""")


def submit(cdp, selector, evidence, name, *, error=False):
    cdp.events.clear()
    cdp.activate(selector)
    wait(cdp, error=error)
    paths = posts(cdp)
    assert len(paths) == 1, paths
    evidence["actions"][name] = {"posts": paths, "focus": focus(cdp)}
    return paths


def measure(cdp, output, evidence, selector, name):
    for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                 deviceScaleFactor=1, mobile=False)
        if scale == 2:
            cdp.evaluate("""(() => {const all=[...document.querySelectorAll('body,body *')];
                const sizes=all.map(e=>parseFloat(getComputedStyle(e).fontSize));
                all.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px');})()""")
        geometry = cdp.evaluate("""(selector => {
            const f=document.querySelector(selector),r=f.getBoundingClientRect();
            const card=f.querySelector('.compact-card'),s=card&&getComputedStyle(card);
            return {client:document.documentElement.clientWidth,
                scroll:document.documentElement.scrollWidth,width:r.width,height:r.height,
                selected:[...f.querySelectorAll('[name=cards]:checked')].map(e=>e.value),
                card:card&&{color:s.color,background:s.backgroundColor,border:s.borderColor},
                text:f.innerText};})(""" + json.dumps(selector) + ")")
        assert geometry["client"] == geometry["scroll"], geometry
        assert geometry["width"] > 0 and geometry["height"] > 0
        if geometry["card"]:
            card = geometry["card"]
            card["contrast"] = contrast(card["color"], card["background"])
            card["border_contrast"] = contrast(card["border"], card["background"])
            assert card["contrast"] >= 4.5 and card["border_contrast"] >= 3
        evidence["measurements"].append({"name": name, "viewport": [width, height],
            "text_scale": scale, "focus": focus(cdp), **geometry})
        cdp.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView()")
        cdp.screenshot(output / (
            f"{evidence['mode']}-{evidence['locale']}-{name}-{width}-{scale}.png"))
        detail = (".compact-card-choices" if name == "selected-hand" else
                  ".local-time-editor" if name in {"optional-time", "time-error"} else None)
        if detail:
            cdp.evaluate(f"document.querySelector({json.dumps(selector + ' ' + detail)})"
                         ".scrollIntoView()")
            cdp.screenshot(output / (
                f"{evidence['mode']}-{evidence['locale']}-{name}-{width}-{scale}-controls.png"))
        if scale == 2:
            cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>"
                         "e.style.removeProperty('font-size'))")


def open_metadata(cdp, selector=METADATA):
    # Native Enter opens the existing optional/technical disclosure ancestors.
    while True:
        path = cdp.evaluate("""(selector => {const f=document.querySelector(selector);
            const closed=[];for(let p=f.parentElement;p;p=p.parentElement)
                if(p.tagName==='DETAILS'&&!p.open) closed.push(p);
            const p=closed.at(-1);if(!p)return null;
            return [...document.querySelectorAll('details')].indexOf(p);})("""
            + json.dumps(selector) + ")")
        if path is None:
            break
        cdp.evaluate(f"document.querySelectorAll('details')[{path}].querySelector('summary').focus()")
        # The index refers only to the current rendered disclosure, not Product state.
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Enter", code="Enter",
                 windowsVirtualKeyCode=13, text="\r")
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Enter", code="Enter",
                 windowsVirtualKeyCode=13)


def flow(cdp, server, context, output, evidence, counts):
    locale = evidence["locale"]
    cdp.navigate(server.origin + "/sessions")
    cdp.activate(f'form.language-selector button[value="{locale}"]')
    wait(cdp)
    form = 'form[action="/sessions/create"]'
    seat = "rearhand" if locale == "de" else "middlehand"
    for name, value in {"game_name": "Synthetic direct-start Game", "perspective_seat": seat,
        "forehand_name": "Alex", "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, form + f' [name="{name}"]', value)
    choose(cdp, form + ' input[value="live"]')
    submit(cdp, form + ' button[value="update"]', evidence, "roster-review")
    original_count = counts["sessions"]
    submit(cdp, form + ' button[value="create"]', evidence, "creation")
    active = context.managed_stateful.active_session
    assert counts["sessions"] == original_count + 1
    assert active.state.revision == 0 and active.state.phase == "setup"
    assert active.state.command_log == ()
    assert next(p.seat for p in active.state.players
                if p.player_id == active.state.local_player_id) == seat
    evidence["seat"] = seat
    evidence["creation_revision"] = 0
    initial_posts = []
    if evidence["phase"] == "before":
        assert not cdp.evaluate(f"!!document.querySelector('{CARDS}')")
        measure(cdp, output, evidence, "#session-recording", "initial-task")
        initial_posts += submit(cdp, METADATA + ' button', evidence, "required-metadata")
    else:
        assert cdp.evaluate(f"!!document.querySelector('{CARDS}')")
        measure(cdp, output, evidence, "#session-recording", "initial-task")
    source_revision = active.state.revision
    source_bytes = active.path.read_bytes()
    # Empty native submission is a real error and cannot initialize missing identity.
    submit(cdp, CARDS + ' button', evidence, "empty-selection", error=True)
    assert active.state.revision == source_revision and active.path.read_bytes() == source_bytes
    measure(cdp, output, evidence, ".error-summary", "empty-error")
    cdp.activate(f'form.language-selector button[value="{"en" if locale == "de" else "de"}"]')
    wait(cdp, error=True)
    assert cdp.evaluate(f"document.querySelectorAll('{CARDS} [name=cards]:checked').length") == 0
    cdp.activate(f'form.language-selector button[value="{locale}"]')
    wait(cdp, error=True)
    cdp.navigate(server.origin + "/sessions/current")
    cdp.events.clear()
    for card in get_full_deck()[:10]:
        choose(cdp, CARDS + f' input[value="{card}"]')
    assert posts(cdp) == [] and active.path.read_bytes() == source_bytes
    evidence["actions"]["selection"] = {"posts": [], "focus": focus(cdp)}
    measure(cdp, output, evidence, CARDS, "selected-hand")
    if evidence["javascript"]:
        for language in ("en" if locale == "de" else "de", locale):
            submit(cdp, f'form.language-selector button[value="{language}"]',
                   evidence, "unsent-language-" + language, error=True)
            assert cdp.evaluate(
                f"document.querySelectorAll('{CARDS} [name=cards]:checked').length") == 10
        assert active.path.read_bytes() == source_bytes
    choose(cdp, CARDS + f' input[value="{get_full_deck()[10]}"]')
    submit(cdp, CARDS + ' button', evidence, "over-capacity", error=True)
    assert active.path.read_bytes() == source_bytes and active.state.revision == source_revision
    for language in ("en" if locale == "de" else "de", locale):
        submit(cdp, f'form.language-selector button[value="{language}"]',
               evidence, "rejected-language-" + language, error=True)
        assert cdp.evaluate(
            f"document.querySelectorAll('{CARDS} [name=cards]:checked').length") == 11
    measure(cdp, output, evidence, ".error-summary", "capacity-error")
    choose(cdp, CARDS + f' input[value="{get_full_deck()[10]}"]')
    original_count = counts["sessions"]
    initial_posts += submit(cdp, CARDS + ' button', evidence, "first-hand")
    assert counts["sessions"] == original_count + 1
    assert active.state.revision == 11 and active.state.phase == "declaration"
    facts = replay_session_state_v1(active.state)
    assert facts.game_id == facts.session_id and facts.played_at is None
    assert facts.initial_hand_for(active.state.local_player_id) == tuple(get_full_deck()[:10])
    assert [r.command.kind for r in active.state.command_log] == (
        ["set_game_metadata"] + ["record_dealt_card"] * 10)
    evidence["initial_mutation_posts"] = initial_posts
    assert initial_posts == (["/sessions/command"] if evidence["phase"] == "before" else []) + [
        "/sessions/cards"]
    evidence["first_hand"] = {"revision": 11, "identity_matches_session": True,
        "timestamp": None, "save_replacements": 1,
        "expected_revisions": [r.command.expected_revision for r in active.state.command_log]}
    measure(cdp, output, evidence, "#session-recording", "next-task")
    open_metadata(cdp)
    cdp.activate(METADATA + " .local-time-editor > summary")
    measure(cdp, output, evidence, METADATA, "optional-time")
    time_values(cdp, METADATA, "2026-03-29", "02:30")
    assert native_select(cdp, METADATA + ' [name=local_zone]') == "Europe/Berlin"
    before = active.path.read_bytes()
    submit(cdp, METADATA + " button", evidence, "time-gap", error=True)
    assert active.path.read_bytes() == before
    measure(cdp, output, evidence, METADATA, "time-error")
    time_values(cdp, METADATA, "2026-01-15", "19:30")
    submit(cdp, METADATA + " button", evidence, "optional-time-save")
    assert active.state.revision == 12
    assert active.state.command_log[-1].command.game_id is None
    assert replay_session_state_v1(active.state).played_at == "2026-01-15T19:30:00+01:00"
    correction = ('form:has(input[value="session-metadata-correction"])'
                  ':has(input[name="target_revision"][value="12"])')
    open_metadata(cdp, correction)
    cdp.activate(correction + " .local-time-editor > summary")
    assert native_select(cdp, correction + ' [name=time_mode]', down=1) == "replace"
    time_values(cdp, correction, "2026-07-15", "19:30")
    submit(cdp, correction + ' button', evidence, "time-correction")
    assert active.state.revision == 12
    assert replay_session_state_v1(active.state).played_at == "2026-07-15T19:30:00+02:00"
    before = active.path.read_bytes()
    cdp.navigate(server.origin + "/sessions")
    submit(cdp, f'form[action="/sessions/open"]:has(input[value="{active.handle}"]) button',
           evidence, "reopen")
    assert context.managed_stateful.active_session.path.read_bytes() == before
    evidence["reopened_sha256"] = hashlib.sha256(before).hexdigest()
    resource_evidence(cdp, server, evidence)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    hashes = {}
    for name in MODULES:
        data = files("skatmind.app_web").joinpath(name).read_bytes()
        if args.phase == "after":
            assert data == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = hashlib.sha256(data).hexdigest()
    evidence = {"baseline": BASELINE, "phase": args.phase, "completed": False,
        "python": sys.version, "package": skatmind.__version__, "module": skatmind.__file__,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(), "hashes": hashes,
        "runs": []}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="direct-start-evidence")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            cdp = browser.cdp
            try:
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=direct-start-evidence")
                time.sleep(.5)
                for locale in ("de", "en"):
                    item = {"javascript": javascript, "mode": mode, "phase": args.phase,
                        "locale": locale, "browser": browser.version, "actions": {},
                        "measurements": []}
                    evidence["runs"].append(item)
                    counts = {"sessions": 0}
                    real_replace = os.replace
                    def counted(source, destination, real_replace=real_replace, counts=counts):
                        result = real_replace(source, destination)
                        if Path(destination).parent.name == "sessions":
                            counts["sessions"] += 1
                        return result
                    with patch.object(os, "replace", counted):
                        flow(cdp, server, context, output, item, counts)
                    item["session_replacements_total"] = counts["sessions"]
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"completed": evidence["completed"], "measurements": sum(
            len(item["measurements"]) for item in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    run(parser.parse_args())
