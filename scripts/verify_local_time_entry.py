"""Optional installed-Wheel local-time browser evidence using dependency-free DevTools."""

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
from urllib.parse import parse_qs, urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import fill, posts, wait
from verify_compact_declaration import resource_evidence

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.session_transitions import replay_session_state_v1

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json",
    "task_first_session_rendering.py", "task_first_match_rendering.py",
    "friendly_creation_rendering.py", "profile_settings_rendering.py", "server.py",
    "frontend_profile_contracts.py", "frontend_profile_codec.py", "time_zone_provider.py",
    "local_time_conversion.py", "local_time_forms.py", "local_time_http.py",
    "local_time_rendering.py", "time_zone_preferences.py", "time_zone_keys.py",
    "frontend_profile_operations.py", "frontend_profile_persistence.py",
    "profile_player_operations.py", "profile_driven_creation.py", "player_seat_setup.py",
    "form_registry.py", "validation_mapping.py", "validation_rendering.py",
    "session_form_translation.py")


def measure(cdp, output, evidence, selector, name):
    for locale in ("de", "en"):
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp, error=bool(cdp.evaluate("!!document.querySelector('.error-summary')")))
        cdp.evaluate("""(selector => {const f=document.querySelector(selector);
            for(let p=f.parentElement;p;p=p.parentElement) if(p.tagName==='DETAILS') p.open=true;
            f.querySelectorAll('details').forEach(e=>e.open=true);
        })(""" + json.dumps(selector) + ")")
        if name == "match-metadata-replace":
            fill(cdp, selector + ' [name=time_mode]', "replace")
        for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
            cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                     deviceScaleFactor=1, mobile=False)
            if scale == 2:
                cdp.evaluate("""(() => { const all=[...document.querySelectorAll('body,body *')];
                    const sizes=all.map(e=>parseFloat(getComputedStyle(e).fontSize));
                    all.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px'); })()""")
            geometry = cdp.evaluate("""(selector => {
                const f=document.querySelector(selector),r=f.getBoundingClientRect();
                return {client:document.documentElement.clientWidth,
                  scroll:document.documentElement.scrollWidth,
                  form:{width:r.width,height:r.height},
                  fields:[...f.querySelectorAll('input,select')].map(e=>({name:e.name,type:e.type,
                    required:e.required,visible:e.checkVisibility(),options:e.options?.length})),
                  focus:{tag:document.activeElement.tagName,id:document.activeElement.id,
                    outline:getComputedStyle(document.activeElement).outlineColor}};
                }) (""" + json.dumps(selector) + ")")
            evidence["measurements"].append({"name": name, "locale": locale,
                "viewport": [width, height], "text_scale": scale, **geometry})
            if evidence["phase"] == "after":
                assert geometry["client"] == geometry["scroll"], geometry
                assert geometry["form"]["width"] > 0 and geometry["form"]["height"] > 0
            cdp.evaluate(f"document.querySelector({json.dumps(selector)}).scrollIntoView()")
            cdp.screenshot(output / f"{evidence['mode']}-{name}-{locale}-{width}-{scale}.png")
            if name == "settings" and evidence["phase"] == "after":
                cdp.evaluate("document.querySelector('#time-zone-settings').scrollIntoView()")
                cdp.screenshot(
                    output / f"{evidence['mode']}-zone-settings-{locale}-{width}-{scale}.png")
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp, error=bool(cdp.evaluate("!!document.querySelector('.error-summary')")))


def baseline(cdp, server, context, output, evidence):
    cdp.navigate(server.origin + "/settings")
    measure(cdp, output, evidence, ".local-settings", "settings")
    cdp.navigate(server.origin + "/matches/new")
    create = 'form[action="/matches/api/v1/create"]'
    measure(cdp, output, evidence, create, "match-create")
    for name, value in {"match_title": "Synthetic time Match", "perspective_seat": "forehand",
        "forehand_name": "Alex", "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, create + f' [name="{name}"]', value)
    cdp.activate(create + ' button[value="update"]')
    wait(cdp)
    cdp.activate(create + ' button[value="create"]')
    wait(cdp)
    metadata = 'form:has(input[name="operation"][value="update_match_metadata"])'
    cdp.evaluate(f"document.querySelector('{metadata}').closest('details').open=true")
    measure(cdp, output, evidence, metadata, "match-metadata")
    cdp.navigate(server.origin + "/sessions")
    create = 'form[action="/sessions/create"]'
    for name, value in {"game_name": "Synthetic time Game", "perspective_seat": "forehand",
        "forehand_name": "Alex", "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, create + f' [name="{name}"]', value)
    cdp.activate(create + ' button[value="update"]')
    wait(cdp)
    cdp.activate(create + ' button[value="create"]')
    wait(cdp)
    measure(cdp, output, evidence,
        '#session-recording form:has(input[value="set_game_metadata"])', "session-metadata")


def key(cdp, value, code, number):
    cdp.call("Input.dispatchKeyEvent", type="keyDown", key=value, code=code,
             windowsVirtualKeyCode=number)
    cdp.call("Input.dispatchKeyEvent", type="keyUp", key=value, code=code,
             windowsVirtualKeyCode=number)


def native_select(cdp, selector, *, down=0, end=False):
    cdp.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
    key(cdp, "End" if end else "Home", "End" if end else "Home", 35 if end else 36)
    for _ in range(down):
        key(cdp, "ArrowDown", "ArrowDown", 40)
    key(cdp, "Tab", "Tab", 9)
    return cdp.evaluate(f"document.querySelector({json.dumps(selector)}).value")


def save(cdp, selector, evidence, name, *, error=False):
    cdp.events.clear()
    cdp.activate(selector)
    wait(cdp, error=error)
    assert len(posts(cdp)) == 1, posts(cdp)
    request = next(event["params"]["request"] for event in cdp.events
                   if event["params"]["request"]["method"] == "POST")
    values = parse_qs(request.get("postData", ""), keep_blank_values=True)
    safe = {name: value for name, value in values.items() if name in {
        "time_zone", "time_mode", "local_date", "local_time", "local_zone", "played_date",
        "setup_action", "language"}}
    safe["occurrence"] = [value.split(".")[0] for value in values.get("local_occurrence", [])]
    evidence["actions"][name] = {"path": urlsplit(request["url"]).path, "values": safe,
        "locale": cdp.evaluate("document.documentElement.lang"),
        "post_count": len(posts(cdp)), "focus": cdp.evaluate("""(() => {
          const e=document.activeElement;return {id:e.id,tag:e.tagName,
            outline:getComputedStyle(e).outlineColor};})()""")}


def match_setup(cdp, server, title):
    cdp.navigate(server.origin + "/matches/new")
    selector = 'form[action="/matches/api/v1/create"]'
    for name, value in {"match_title": title, "perspective_seat": "rearhand",
        "forehand_name": "Alex", "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, selector + f' [name="{name}"]', value)
    return selector


def time_values(cdp, form, day, clock):
    cdp.evaluate(f"""(() => {{for(let p=document.querySelector('{form}').parentElement;
        p;p=p.parentElement) if(p.tagName==='DETAILS') p.open=true;}})()""")
    cdp.evaluate(f"document.querySelector('{form} .local-time-editor').open=true")
    fill(cdp, form + ' [name="local_date"]', day)
    fill(cdp, form + ' [name="local_time"]', clock)


def current_matches(context):
    return len(tuple(context.managed_stateful.root("matches").glob("*.json")))


def final_flow(cdp, server, context, output, evidence):
    import zoneinfo

    from skatmind.app_web.time_zone_provider import time_zone_inventory
    inventory = time_zone_inventory()
    evidence["provider"] = {"tzdata": inventory.package_version, "iana": inventory.iana_version,
                            "keys": len(inventory.keys), "host_tzpath_empty": not zoneinfo.TZPATH}
    cdp.navigate(server.origin + "/settings")
    assert not context.frontend_profile.profile_path.exists()
    cdp.activate('form.language-selector button[value="de"]')
    wait(cdp)
    settings = 'form[action="/actions/profile/time-zone"]'
    assert native_select(cdp, settings + ' select', down=1) == "Europe/Berlin"
    save(cdp, settings + ' button', evidence, "save-zone")
    assert context.frontend_profile.document.interface_preferences.time_zone == "Europe/Berlin"
    profile = context.frontend_profile.profile_path.read_bytes()
    save(cdp, settings + ' button', evidence, "zone-noop")
    assert context.frontend_profile.profile_path.read_bytes() == profile
    measure(cdp, output, evidence, ".local-settings", "settings")
    resumed = AppWebContextV1.create(context.managed_home)
    assert resumed.frontend_profile.document.interface_preferences.time_zone == "Europe/Berlin"
    evidence["profile_restart_loaded"] = True
    form = match_setup(cdp, server, "Date-only Match")
    assert cdp.evaluate(f"document.querySelector('{form} [name=local_date]').value") == ""
    assert cdp.evaluate(f"document.querySelector('{form} [name=local_time]').value") == ""
    measure(cdp, output, evidence, form, "match-create")
    # Native language changes without JavaScript do not preserve unsent names.
    form = match_setup(cdp, server, "Date-only Match")
    fill(cdp, form + ' [name="played_date"]', "2026-01-15")
    save(cdp, form + ' button[value="update"]', evidence, "date-only-setup")
    save(cdp, form + ' button[value="create"]', evidence, "date-only-create")
    assert context.managed_stateful.active_match.workspace.match_definition.played_at is None
    evidence["date_only"] = True
    for season, day, offset in (("winter", "2026-01-15", "+01:00"),
                                ("summer", "2026-07-15", "+02:00")):
        locale = "de" if season == "winter" else "en"
        cdp.activate(f'form.language-selector button[value="{locale}"]')
        wait(cdp)
        form = match_setup(cdp, server, season + " Match")
        time_values(cdp, form, day, "19:30")
        fill(cdp, form + ' [name="played_date"]', day)
        save(cdp, form + ' button[value="update"]', evidence, season + "-setup")
        save(cdp, form + ' button[value="create"]', evidence, season + "-create")
        active = context.managed_stateful.active_match
        assert active.workspace.match_definition.played_at == day + "T19:30:00" + offset
        evidence[season] = active.workspace.match_definition.played_at
    for which, down, offset in (("earlier", 1, "+02:00"), ("later", 2, "+01:00")):
        form = match_setup(cdp, server, which + " Match")
        time_values(cdp, form, "2026-03-29", "02:30")
        count = current_matches(context)
        profile = context.frontend_profile.profile_path.read_bytes()
        save(cdp, form + ' button[value="update"]', evidence, which + "-gap", error=True)
        assert current_matches(context) == count
        assert context.frontend_profile.profile_path.read_bytes() == profile
        measure(cdp, output, evidence, form, "gap-" + which)
        time_values(cdp, form, "2026-10-25", "02:30")
        save(cdp, form + ' button[value="update"]', evidence, which + "-ambiguous", error=True)
        assert current_matches(context) == count
        assert cdp.evaluate(f"document.querySelector('{form} [name=local_occurrence]').value") == ""
        if which == "earlier":
            measure(cdp, output, evidence, form, "ambiguous")
        assert native_select(cdp, form + ' [name=local_occurrence]', down=down).startswith(which)
        save(cdp, form + ' button[value="update"]', evidence, which + "-resolved-setup")
        cdp.evaluate(f"document.querySelector('{form} .local-time-editor').open=true")
        assert native_select(cdp, form + ' [name=local_occurrence]', down=down).startswith(which)
        save(cdp, form + ' button[value="create"]', evidence, which + "-create")
        assert current_matches(context) == count + 1
        assert context.managed_stateful.active_match.workspace.match_definition.played_at == (
            "2026-10-25T02:30:00" + offset)
        evidence[which] = context.managed_stateful.active_match.workspace.match_definition.played_at
    active = context.managed_stateful.active_match
    metadata = 'form:has(input[value="match-metadata"])'
    cdp.evaluate(f"document.querySelector('{metadata}').closest('details').open=true")
    before_profile = context.frontend_profile.profile_path.read_bytes()
    before_time = active.workspace.match_definition.played_at
    fill(cdp, metadata + ' [name=title]', "Edited time Match")
    save(cdp, metadata + ' button', evidence, "match-metadata-keep")
    assert active.workspace.match_definition.played_at == before_time
    assert context.frontend_profile.profile_path.read_bytes() == before_profile
    cdp.evaluate(f"document.querySelector('{metadata}').closest('details').open=true")
    measure(cdp, output, evidence, metadata, "match-metadata")
    measure(cdp, output, evidence, metadata, "match-metadata-replace")
    saved = active.path.read_bytes()
    cdp.navigate(server.origin + "/matches")
    cdp.activate(f'form[action="/matches/open"]:has(input[value="{active.handle}"]) button')
    wait(cdp)
    assert context.managed_stateful.active_match.path.read_bytes() == saved
    evidence["match_reopened_hash"] = hashlib.sha256(saved).hexdigest()
    cdp.navigate(server.origin + "/sessions")
    form = 'form[action="/sessions/create"]'
    for name, value in {"game_name": "Native time Game", "perspective_seat": "forehand",
        "forehand_name": "Alex", "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        fill(cdp, form + f' [name="{name}"]', value)
    save(cdp, form + ' button[value="update"]', evidence, "session-setup")
    save(cdp, form + ' button[value="create"]', evidence, "session-create")
    form = 'form:has(input[value="session-metadata"])'
    cdp.evaluate(f"""(() => {{for(let p=document.querySelector('{form}').parentElement;
        p;p=p.parentElement) if(p.tagName==='DETAILS') p.open=true;}})()""")
    measure(cdp, output, evidence, form, "session-metadata")
    time_values(cdp, form, "2026-01-15", "18:30")
    # Exercise native segmented date/time keys; inspect the actual resulting values.
    keyboard = {}
    for name in ("local_date", "local_time"):
        selector = form + f' [name="{name}"]'
        before = cdp.evaluate(f"document.querySelector('{selector}').value")
        cdp.evaluate(f"document.querySelector('{selector}').focus()")
        key(cdp, "ArrowUp", "ArrowUp", 38)
        after = cdp.evaluate(f"document.querySelector('{selector}').value")
        assert before != after, (name, before, after)
        keyboard[name] = {"before": before, "after": after}
    zone_selector = form + ' [name="local_zone"]'
    assert native_select(cdp, zone_selector, down=1) == "UTC"
    assert native_select(cdp, zone_selector) == "Europe/Berlin"
    evidence["native_keyboard"] = keyboard
    day = keyboard["local_date"]["after"]
    clock = keyboard["local_time"]["after"]
    evidence["session_submitted"] = {"date": day, "time": clock, "zone": "Europe/Berlin"}
    save(cdp, form + ' button', evidence, "session-time-save")
    active = context.managed_stateful.active_session
    timestamp = replay_session_state_v1(active.state).played_at
    assert timestamp.startswith(day + "T" + clock[:5])
    evidence["session_timestamp"] = timestamp
    correction = 'form:has(input[value="session-metadata-correction"])'
    cdp.evaluate("document.querySelector('#session-history > details').open=true")
    cdp.evaluate(f"document.querySelector('{correction}').closest('details').open=true")
    cdp.evaluate(f"document.querySelector('{correction} .local-time-editor').open=true")
    assert native_select(cdp, correction + ' [name=time_mode]', down=1) == "replace"
    time_values(cdp, correction, "2026-07-15", "19:30")
    save(cdp, correction + ' button', evidence, "session-time-correction")
    assert replay_session_state_v1(active.state).played_at == "2026-07-15T19:30:00+02:00"
    saved = active.path.read_bytes()
    cdp.navigate(server.origin + "/sessions")
    cdp.activate('form[action="/sessions/open"] button')
    wait(cdp)
    assert context.managed_stateful.active_session.path.read_bytes() == saved
    evidence["session_reopened_hash"] = hashlib.sha256(saved).hexdigest()
    resource_evidence(cdp, server, evidence)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    hashes = {}
    for name in MODULES:
        resource = files("skatmind.app_web").joinpath(name)
        if args.phase == "before" and not resource.is_file():
            continue
        data = resource.read_bytes()
        if args.phase == "after":
            assert data == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = hashlib.sha256(data).hexdigest()
    evidence = {"baseline": "3341b9fc645ee808158a4fc3131f5b359cb50777", "phase": args.phase,
        "python": sys.version.split()[0], "package": skatmind.__version__, "hashes": hashes,
        "runs": [], "completed": False}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="local-time-evidence")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            cdp = browser.cdp
            item = {"javascript": javascript, "mode": mode, "phase": args.phase,
                "browser": browser.version["product"], "measurements": [], "actions": {}}
            evidence["runs"].append(item)
            try:
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=local-time-evidence")
                time.sleep(.5)
                if args.phase == "before":
                    baseline(cdp, server, context, output, item)
                else:
                    real_replace = os.replace
                    counts = {"profile": 0, "sessions": 0, "matches": 0}
                    def counted(source, destination, real_replace=real_replace, counts=counts):
                        result = real_replace(source, destination)
                        destination = Path(destination)
                        family = ("profile" if destination.name == "frontend-profile.json"
                                  else destination.parent.name)
                        if family in counts:
                            counts[family] += 1
                        return result
                    with patch.object(os, "replace", counted):
                        final_flow(cdp, server, context, output, item)
                    item["successful_atomic_replacements"] = counts
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
    parser.add_argument("--browser", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--phase", required=True, choices=("before", "after"))
    run(parser.parse_args())
