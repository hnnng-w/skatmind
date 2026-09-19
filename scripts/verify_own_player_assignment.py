"""Optional #242 installed-Wheel native browser evidence, using existing DevTools tooling."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from importlib.resources import files
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, posts, wait
from verify_compact_declaration import resource_evidence
from verify_local_time_entry import native_select
from verify_match_format_presentation import native_text as _native_text
from verify_session_direct_card_start import open_metadata

import skatmind
from skatmind.api.v1.session import files as session_files
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("player_seat_setup.py", "seat_setup_rendering.py", "profile_driven_creation.py",
    "friendly_creation_rendering.py", "validation_mapping.py", "validation_rendering.py",
    "language_context.py", "language_form_preservation.py", "form_registry.py", "server.py",
    "assets/app.css", "assets/workflow.js", "locales/de.json", "locales/en.json")
NAMES = ('Alexandra <A> & "Own" ' + "Long synthetic name " * 4, "Boris", "Clara")
HAND = ("CA", "C10", "CJ", "SA", "SK", "SJ", "HA", "H9", "DK", "D7")


def native_text(cdp, selector, value):
    assert cdp.evaluate(
        f"document.querySelector({json.dumps(selector)}).checkVisibility()"), selector
    _native_text(cdp, selector, value)
    assert cdp.evaluate(f"document.querySelector({json.dumps(selector)}).value") == value


def submit(cdp, selector, item, label, counts, *, error=False):
    before = dict(counts)
    cdp.events.clear()
    cdp.activate(selector)
    wait(cdp, error=error)
    assert len(posts(cdp)) == 1, posts(cdp)
    request = next(e["params"]["request"] for e in cdp.events
                   if e["params"]["request"]["method"] == "POST")
    data = parse_qs(request.get("postData", ""), keep_blank_values=True)
    assert all(len(v) == 1 for k, v in data.items() if k != "cards")
    focus = cdp.evaluate("({tag:document.activeElement.tagName,id:document.activeElement.id,"
                         "classes:document.activeElement.className})")
    item["actions"].append({"label": label, "posts": posts(cdp), "values": data,
        "writes": {k: counts[k] - before[k] for k in counts}, "focus": focus})
    if error:
        assert "error-summary" in focus["classes"]


def measure(cdp, output, item, selector, label, *, full_matrix=True):
    sizes = ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2))
    for width, height, scale in sizes if full_matrix else ((390, 844, 1),):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                 deviceScaleFactor=1, mobile=False)
        if scale == 2:
            cdp.evaluate("""(()=>{const all=[...document.querySelectorAll('body,body *')];
                const sizes=all.map(e=>parseFloat(getComputedStyle(e).fontSize));
                all.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px');})()""")
        geometry = cdp.evaluate("""(s=>{
            const form=document.querySelector(s), controls=[...form.elements];
            const fields=controls.filter(e=>e.name).map(e=>({name:e.name,type:e.type,
                value:e.value,visible:e.checkVisibility(),disabled:e.disabled,tabIndex:e.tabIndex}));
            const rows=[...form.querySelectorAll('.seat-entry')].map(e=>({seat:e.dataset.seat,
                text:e.innerText,derived:e.querySelector('.derived-own')?.checkVisibility(),
                editor:e.querySelector('.seat-identity').checkVisibility()}));
            const links=[...document.querySelectorAll('.error-summary a')].map(a=>{
                const e=document.getElementById(a.hash.slice(1));return {text:a.innerText,
                    target:e?.name,visible:e?.checkVisibility(),disabled:e?.disabled};});
            return {client:document.documentElement.clientWidth,
                scroll:document.documentElement.scrollWidth,fields,rows,links};
            }) (""" + json.dumps(selector) + ")")
        assert geometry["client"] == geometry["scroll"], geometry
        assert all(link["visible"] and not link["disabled"] for link in geometry["links"])
        if label in {"chosen-own", "reviewed"}:
            assert [row["seat"] for row in geometry["rows"] if row["derived"]] == ["rearhand"]
            assert [row["seat"] for row in geometry["rows"] if row["editor"]] == [
                "forehand", "middlehand"]
        if label in {"occupied", "retained-language"}:
            rear = geometry["rows"][2]
            assert rear["editor"] and not rear["derived"] and "Boris" in rear["text"]
        item["measurements"].append({"label": label, "viewport": [width, height],
                                     "text_scale": scale, **geometry})
        for target, suffix in ((selector + " .seat-setup", "seats"),
                               (selector + ' [data-seat="rearhand"]', "own-row"),
                               (".error-summary", "error")):
            if not cdp.evaluate(f"!!document.querySelector({json.dumps(target)})"):
                continue
            cdp.evaluate(f"document.querySelector({json.dumps(target)}).scrollIntoView()")
            time.sleep(.2)
            cdp.screenshot(output / f"{item['key']}-{label}-{width}-{scale}-{suffix}.png")
        if scale == 2:
            cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>"
                         "e.style.removeProperty('font-size'))")


def snapshot(context, family):
    active = getattr(context.managed_stateful,
                     "active_session" if family == "sessions" else "active_match")
    if family == "sessions":
        state = session_files.load_session_file(active.path).value.document.state
        assert state == active.state
        roster = [(p.seat, p.player_label) for p in state.players]
        perspective = next(p.player_label for p in state.players
                           if p.player_id == state.local_player_id)
        revision = state.revision
        accounts, played_at = {}, None
    else:
        workspace = load_match_workspace_file_v1(active.path).document.workspace
        assert workspace == active.workspace
        definition = workspace.match_definition
        labels = {p.player_id: p.player_label for p in definition.participants}
        seats = build_match_workspace_seat_assignment_v1(definition, 1)
        roster = [(s, labels[getattr(seats, s + "_player_id")]) for s in (
            "forehand", "middlehand", "rearhand")]
        perspective = labels[definition.perspective_player_id]
        revision = workspace.revision
        accounts = {p.player_label: p.platform_player_id for p in definition.participants}
        played_at = definition.played_at
    return {"roster": roster, "perspective": perspective, "revision": revision,
        "accounts": accounts, "played_at": played_at,
        "sha256": hashlib.sha256(active.path.read_bytes()).hexdigest()}


def flow(cdp, server, context, output, item, counts, family):
    route, action, title = (("/sessions", "/sessions/create", "game_name") if family == "sessions"
                           else ("/matches/new", "/matches/api/v1/create", "match_title"))
    form = f'form[action="{action}"]'
    locale = item["locale"]
    cdp.navigate(server.origin + route)
    submit(cdp, f'form.language-selector button[value="{locale}"]', item, "flow-language", counts)
    initial_counts = dict(counts)
    assert cdp.evaluate("document.querySelector('[name=own_seat]').value") == ""
    measure(cdp, output, item, form, "initial", full_matrix=False)
    cdp.events.clear()
    native_select(cdp, form + " [name=own_seat]", down=3)
    native_text(cdp, form + f" [name={title}]", "Synthetic one-assignment " + family)
    native_select(cdp, form + " [name=forehand_handle]", down=2)
    native_select(cdp, form + " [name=middlehand_handle]", down=3)
    assert posts(cdp) == [] and counts == initial_counts
    measure(cdp, output, item, form, "chosen-own")
    submit(cdp, form + ' button[value="update"]', item, "first-complete-review", counts)
    assert counts == initial_counts
    measure(cdp, output, item, form, "reviewed")
    cdp.events.clear()
    native_select(cdp, form + " [name=own_seat]", down=1)
    measure(cdp, output, item, form, "pending-reviewed-move", full_matrix=False)
    assert cdp.evaluate("document.querySelector('[data-seat=rearhand] .own-release')"
                        ".checkVisibility()")
    assert cdp.evaluate("document.querySelector('[name=forehand_handle]').checkVisibility()")
    native_select(cdp, form + " [name=own_seat]", down=3)
    assert posts(cdp) == [] and counts == initial_counts
    item["selection_posts"] = []
    submit(cdp, form + ' button[value="create"]', item, "own-create", counts)
    assert counts[family] == initial_counts[family] + 1
    own = snapshot(context, family)
    assert own["revision"] == 0 and own["perspective"] == NAMES[0].strip()
    assert [name for _, name in own["roster"]] == [NAMES[1], NAMES[2], NAMES[0].strip()]
    item["own_created"] = own
    if family == "sessions":
        for card in HAND:
            choose(cdp, f'form[action="/sessions/cards"] input[value="{card}"]')
        submit(cdp, 'form[action="/sessions/cards"] button', item, "initial-hand-save", counts)
        assert snapshot(context, family)["revision"] == 11
    else:
        submit(cdp, 'form:has(input[name="operation"][value="start_game"]) button',
               item, "explicit-start", counts)
        assert snapshot(context, family)["revision"] == 1
    accepted = snapshot(context, family)
    cdp.navigate(server.origin + "/" + family)
    active = getattr(context.managed_stateful,
                     "active_session" if family == "sessions" else "active_match")
    submit(cdp, f'form[action="/{family}/open"]:has(input[value="{active.handle}"]) button',
           item, "reopen", counts)
    assert snapshot(context, family) == accepted

    # A second native flow keeps a genuine entered destination, then explicitly chooses manual C.
    cdp.navigate(server.origin + route)
    native_text(cdp, form + f" [name={title}]", "Submitted collision")
    for seat, index in (("forehand", 2), ("middlehand", 3), ("rearhand", 2)):
        native_select(cdp, form + f" [name={seat}_handle]", down=index)
    native_select(cdp, form + " [name=own_seat]", down=3)
    if family == "matches":
        native_select(cdp, form + " [name=platform_choice]", down=4)
        native_text(cdp, form + " [name=custom_platform]", 'Club <18> & "Friends"')
        native_text(cdp, form + " [name=source_url]", "https://youtu.be/synthetic")
        open_metadata(cdp, form + " [name=rearhand_platform_id]")
        for seat, value in (("forehand", "B-account"), ("middlehand", "C-account"),
                            ("rearhand", "entered-B-account")):
            native_text(cdp, form + f" [name={seat}_platform_id]", value)
    before = dict(counts)
    submit(cdp, form + ' button[value="update"]', item, "real-occupied-target", counts, error=True)
    assert counts == before and snapshot(context, family) == accepted
    measure(cdp, output, item, form, "occupied")
    native_text(cdp, form + f" [name={title}]", "Unsent collision title")
    other = "en" if locale == "de" else "de"
    submit(cdp, f'form.language-selector button[value="{other}"]', item,
           "collision-language", counts, error=True)
    assert cdp.evaluate(f"document.querySelector('[name={title}]').value") == (
        "Unsent collision title" if item["javascript"] else "Submitted collision")
    measure(cdp, output, item, form, "retained-language")
    native_select(cdp, form + " [name=perspective_mode]", down=1)
    native_select(cdp, form + " [name=perspective_seat]", down=2)
    native_select(cdp, form + " [name=rearhand_handle]", down=1)
    if family == "matches":
        open_metadata(cdp, form + " [name=rearhand_platform_id]")
        native_text(cdp, form + " [name=rearhand_platform_id]", "A-account")
    submit(cdp, form + ' button[value="update"]', item, "manual-c-review", counts)
    measure(cdp, output, item, form, "manual-c", full_matrix=False)
    submit(cdp, form + ' button[value="create"]', item, "manual-c-create", counts)
    manual = snapshot(context, family)
    assert manual["revision"] == 0 and manual["perspective"] == "Clara"
    assert manual["roster"] == own["roster"]
    profile = context.frontend_profile.document
    assert profile.own_player_id == profile.known_players[0].player_id
    if family == "matches":
        assert manual["accounts"] == {NAMES[0].strip(): "A-account", "Boris": "B-account",
                                     "Clara": "C-account"}
    item["manual_created"] = manual
    resource_evidence(cdp, server, item)


def account_flow(cdp, server, context, output, item, counts):
    """Separate established-bundle probe; never used to prepare the first-form positive flow."""
    form = 'form[action="/matches/api/v1/create"]'
    cdp.navigate(server.origin + "/matches/new")
    native_select(cdp, form + " [name=own_seat]", down=3)
    submit(cdp, form + ' button[value="update"]', item, "establish-account-source", counts)
    cdp.events.clear()
    native_select(cdp, form + " [name=forehand_handle]", down=1)
    open_metadata(cdp, form + " [name=rearhand_platform_id]")
    native_text(cdp, form + " [name=rearhand_platform_id]", "source-account")
    native_text(cdp, form + " [name=forehand_platform_id]", "target-account")
    native_select(cdp, form + " [name=own_seat]", down=1)
    assert posts(cdp) == []
    submit(cdp, form + ' button[value="update"]', item, "distinct-own-accounts", counts, error=True)
    native_select(cdp, form + " [name=own_seat]", down=2)
    other = "en" if item["locale"] == "de" else "de"
    submit(cdp, f'form.language-selector button[value="{other}"]', item,
           "pending-seat-language", counts, error=True)
    expected = "middlehand" if item["javascript"] else "forehand"
    assert cdp.evaluate("document.querySelector('[name=own_seat]').value") == expected
    for seat, value in (("forehand", "target-account"), ("rearhand", "source-account")):
        assert cdp.evaluate(f"document.querySelector('[name={seat}_platform_id]').value") == value
    measure(cdp, output, item, form, "account-conflict")
    cdp.evaluate("document.querySelector('[name=forehand_platform_id]').scrollIntoView()")
    time.sleep(.2)
    cdp.screenshot(output / f"{item['key']}-account-controls.png")
    native_select(cdp, form + " [name=own_seat]", down=1)
    native_text(cdp, form + " [name=rearhand_platform_id]", "")
    submit(cdp, form + ' button[value="update"]', item, "retain-target-account", counts)
    assert cdp.evaluate("document.querySelector('[name=forehand_platform_id]').value") == (
        "target-account")
    assert cdp.evaluate("document.querySelector('[name=rearhand_platform_id]').value") == ""
    assert counts["matches"] == counts["sessions"] == 0
    native_text(cdp, form + " [name=match_title]", "Explicit account move")
    native_select(cdp, form + " [name=middlehand_handle]", down=3)
    native_select(cdp, form + " [name=rearhand_handle]", down=2)
    submit(cdp, form + ' button[value="update"]', item, "complete-moved-roster", counts)
    submit(cdp, form + ' button[value="create"]', item, "create-moved-roster", counts)
    result = snapshot(context, "matches")
    assert result["accounts"] == {NAMES[0].strip(): "target-account", "Boris": None, "Clara": None}
    assert result["perspective"] == NAMES[0].strip() and result["revision"] == 0
    assert counts["matches"] == 1
    item["created"] = result
    # Native manual -> own selection can retain a conflicting perspective control.
    cdp.navigate(server.origin + "/matches/new")
    native_select(cdp, form + " [name=perspective_mode]", down=1)
    native_select(cdp, form + " [name=perspective_seat]", down=2)
    native_select(cdp, form + " [name=perspective_mode]", down=0)
    native_select(cdp, form + " [name=own_seat]", down=3)
    native_select(cdp, form + " [name=forehand_handle]", down=2)
    native_select(cdp, form + " [name=middlehand_handle]", down=3)
    native_text(cdp, form + " [name=match_title]", "Pending manual perspective")
    submit(cdp, form + ' button[value="update"]', item, "mixed-perspective", counts, error=True)
    assert cdp.evaluate("document.querySelector('[name=perspective_seat]').checkVisibility()")
    measure(cdp, output, item, form, "mixed-perspective", full_matrix=False)
    native_select(cdp, form + " [name=perspective_seat]", down=3)
    submit(cdp, form + ' button[value="update"]', item, "resolve-perspective", counts)
    assert counts["matches"] == 1


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh evidence directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    hashes = {}
    for name in MODULES:
        content = files("skatmind.app_web").joinpath(name).read_bytes()
        assert content == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = hashlib.sha256(content).hexdigest()
    evidence = {"starting_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
        text=True).strip(), "python": sys.version, "package": skatmind.__version__,
        "module": skatmind.__file__,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        "hashes": hashes, "runs": [], "completed": False}
    try:
        for javascript in (True, False):
            for locale in ("de", "en"):
                key = ("js" if javascript else "native") + "-" + locale
                context = AppWebContextV1.create(prepare_managed_home_v1(output / (key + "-data")))
                server = start_app_web_server_v1(context, port=0, token="own-assignment-evidence")
                thread = serve_app_web_in_thread_v1(server)
                browser = LocalBrowser(args.browser, output / (key + "-browser"))
                counts = {"sessions": 0, "matches": 0, "profile": 0}
                real_replace = os.replace
                def counted(source, destination, *, context=context, counts=counts,
                            real_replace=real_replace):
                    for family in ("sessions", "matches"):
                        if Path(destination).parent == context.managed_stateful.root(family):
                            counts[family] += 1
                    if Path(destination) == context.frontend_profile.profile_path:
                        counts["profile"] += 1
                    return real_replace(source, destination)
                try:
                    cdp = browser.cdp
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                    cdp.call("Page.navigate", url=server.origin + "/?token=own-assignment-evidence")
                    time.sleep(.5)
                    cdp.navigate(server.origin + "/settings")
                    # Real native Settings fixture preparation is recorded separately.
                    fixture = {"actions": []}
                    with patch("os.replace", side_effect=counted):
                        for name in NAMES:
                            submit(cdp, 'form[action$="/players/edit"]:has(input[value=""]) button',
                                   fixture, "open-add-player", counts)
                            native_text(cdp, '[name="display_name"]', name.strip())
                            submit(cdp, 'form[action$="/players/add"] button', fixture,
                                   "add-player", counts)
                        native_select(cdp, '[name="own_player_handle"]', down=1)
                        submit(cdp, 'form[action$="/profile/preferences"] button', fixture,
                               "choose-own-a", counts)
                        submit(cdp, f'form.language-selector button[value="{locale}"]', fixture,
                               "choose-language", counts)
                        for family in (("accounts",) if args.supplement_only else
                                       ("sessions", "matches")):
                            item = {"key": key + "-" + family, "locale": locale,
                                "javascript": javascript, "browser": browser.version,
                                "actions": [], "measurements": [], "fixture": fixture}
                            evidence["runs"].append(item)
                            if args.supplement_only:
                                account_flow(cdp, server, context, output, item, counts)
                            else:
                                flow(cdp, server, context, output, item, counts, family)
                            item["cumulative_writes"] = dict(counts)
                finally:
                    browser.close()
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"completed": True, "runs": len(evidence["runs"]),
        "measurements": sum(len(r["measurements"]) for r in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--supplement-only", action="store_true")
    run(parser.parse_args())
