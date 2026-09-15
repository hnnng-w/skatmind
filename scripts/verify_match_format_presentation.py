"""Optional installed-Wheel Match scope probe; reuses dependency-free local DevTools."""

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
from verify_compact_card_entry import choose, fill, posts, wait
from verify_compact_declaration import resource_evidence
from verify_local_time_entry import native_select
from verify_session_direct_card_start import focus, open_metadata

import skatmind
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.match_tournament_format import EUROSKAT_36_STANDARD_V1_FORMAT as FORMAT
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_rotation import build_match_workspace_seat_assignment_v1 as rotation

ROOT = Path(__file__).resolve().parents[1]
START = "5c073862c3e3b8d5cbd79921fe50e62a8a0b34ad"
MODULES = ("app_web/assets/app.css", "app_web/assets/workflow.js",
    "app_web/locales/en.json", "app_web/locales/de.json",
    "app_web/friendly_creation_rendering.py", "app_web/task_first_match_rendering.py",
    "app_web/profile_driven_creation.py", "app_web/form_registry.py", "app_web/server.py",
    "app_web/language_context.py", "app_web/language_form_preservation.py",
    "app_web/local_time_forms.py", "app_web/player_seat_setup.py",
    "capture_web/operations.py", "match_tournament_format.py", "match_capture_contracts.py")
CREATE = 'form[action="/matches/api/v1/create"]'
META = 'form:has(input[name="time_form"][value="match-metadata"])'
CUSTOM = 'Club <18> & "Zocker"'


def native_text(cdp, selector, value):
    cdp.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
    cdp.call("Input.dispatchKeyEvent", type="keyDown", key="a", code="KeyA",
             windowsVirtualKeyCode=65, modifiers=2)
    cdp.call("Input.dispatchKeyEvent", type="keyUp", key="a", code="KeyA",
             windowsVirtualKeyCode=65, modifiers=2)
    if value:
        cdp.call("Input.insertText", text=value)
    else:
        cdp.call("Input.dispatchKeyEvent", type="keyDown", key="Backspace", code="Backspace",
                 windowsVirtualKeyCode=8)
        cdp.call("Input.dispatchKeyEvent", type="keyUp", key="Backspace", code="Backspace",
                 windowsVirtualKeyCode=8)


def values(cdp, selector=CREATE):
    return cdp.evaluate("""(s=>Object.fromEntries([...document.querySelector(s).elements]
        .filter(e=>['match_title','platform_choice','custom_platform','source_url',
        'forehand_name','middlehand_name','rearhand_name','local_date','local_time',
        'local_zone','game_platform','save_platform'].includes(e.name))
        .map(e=>[e.name,e.type==='checkbox'?e.checked:e.value]))) (""" + json.dumps(selector) + ")")


def submit(cdp, selector, evidence, name, *, error=False):
    cdp.events.clear()
    cdp.activate(selector)
    wait(cdp, error=error)
    assert len(posts(cdp)) == 1, posts(cdp)
    request = next(e["params"]["request"] for e in cdp.events
                   if e["params"]["request"]["method"] == "POST")
    submitted = parse_qs(request.get("postData", ""), keep_blank_values=True)
    assert not {"format", "format_id", "tournament_format"} & submitted.keys()
    evidence["actions"][name] = {"posts": posts(cdp), "focus": focus(cdp),
        "values": {key: value for key, value in submitted.items() if key in {
            "platform_choice", "custom_platform", "save_platform", "setup_action", "language"}}}
    if error:
        assert cdp.evaluate("document.activeElement.matches('.error-summary')")
        assert focus(cdp)["width"] != "0px"


def measure(cdp, output, evidence, selector, name, *, scope=None):
    for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                 deviceScaleFactor=1, mobile=False)
        if scale == 2:
            cdp.evaluate("""(()=>{const all=[...document.querySelectorAll('body,body *')];
                const sizes=all.map(e=>parseFloat(getComputedStyle(e).fontSize));
                all.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px');})()""")
        geometry = cdp.evaluate("""(s=>{
            const e=document.querySelector(s),r=e.getBoundingClientRect();
            return {client:document.documentElement.clientWidth,
                scroll:document.documentElement.scrollWidth,width:r.width,height:r.height,
                scope:[...document.querySelectorAll('.match-recording-format')].map(e=>e.innerText),
                fields:[...e.querySelectorAll('input,select,button')].map(e=>({name:e.name,
                    visible:e.checkVisibility(),disabled:e.disabled})),
                overflow:[...document.querySelectorAll('main *')].filter(e=>e.checkVisibility()&&
                    e.getBoundingClientRect().right>document.documentElement.clientWidth+1)
                    .map(e=>({tag:e.tagName,classes:e.className})).slice(0,10)};}) ("""
                    + json.dumps(selector) + ")")
        if evidence["phase"] == "after":
            assert geometry["client"] == geometry["scroll"], geometry
            assert len(geometry["scope"]) == 1
        evidence["measurements"].append({"name": name, "viewport": [width, height],
            "text_scale": scale, "focus": focus(cdp), **geometry})
        target = scope or selector
        cdp.evaluate(f"document.querySelector({json.dumps(target)}).scrollIntoView()")
        time.sleep(.2)  # Let the browser paint after reflow/scroll before capturing pixels.
        cdp.screenshot(output / (
            f"{evidence['mode']}-{evidence['locale']}-{name}-{width}-{scale}.png"))
        if name in {"initial", "setup"}:
            cdp.evaluate(f"document.querySelector('{CREATE} [name=platform_choice]')"
                         ".closest('label').scrollIntoView()")
            time.sleep(.2)
            cdp.screenshot(output / (
                f"{evidence['mode']}-{evidence['locale']}-{name}-{width}-{scale}-platform.png"))
        if scale == 2:
            cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>"
                         "e.style.removeProperty('font-size'))")


def product_bytes(context):
    return {p.name: p.read_bytes() for p in context.managed_stateful.root("matches").glob("*.json")}


def flow(cdp, server, context, output, evidence, counts):
    locale, after = evidence["locale"], evidence["phase"] == "after"
    cdp.navigate(server.origin + "/matches/new")
    cdp.activate(f'form.language-selector button[value="{locale}"]')
    wait(cdp)
    before = product_bytes(context)
    original_profile = context.frontend_profile.profile_path.read_bytes()
    cdp.navigate(server.origin + "/matches/new")
    assert context.frontend_profile.profile_path.read_bytes() == original_profile
    before_count = counts["matches"]
    for name, value in {"match_title": "Synthetic fixed-scope Match", "forehand_name": "Anna",
                        "middlehand_name": "Peter", "rearhand_name": "Mira",
                        "source_url": "https://youtu.be/synthetic"}.items():
        native_text(cdp, CREATE + f' [name="{name}"]', value)
    native_select(cdp, CREATE + ' [name="perspective_seat"]', down=2)
    cdp.activate(CREATE + " .local-time-editor > summary")
    fill(cdp, CREATE + ' [name="local_date"]', "2026-09-03")
    fill(cdp, CREATE + ' [name="local_time"]', "19:30")
    retained = values(cdp)
    scope = CREATE + (" .match-recording-format" if after else " > p:has(strong)")
    original_scope = cdp.evaluate(f"document.querySelector('{scope}').innerText")
    cdp.events.clear()
    selections = []
    for index, choice in enumerate(("euroskat", "in_person", "other_online", "unknown", "custom")):
        assert native_select(cdp, CREATE + ' [name="platform_choice"]', down=index) == choice
        current = values(cdp)
        assert {k: v for k, v in current.items() if k != "platform_choice"} == {
            k: v for k, v in retained.items() if k != "platform_choice"}
        assert cdp.evaluate(f"document.querySelector('{scope}').innerText") == original_scope
        selections.append(current["platform_choice"])
    assert posts(cdp) == [] and product_bytes(context) == before
    assert counts["matches"] == before_count
    evidence["actions"]["native-platform-changes"] = {"selections": selections, "posts": [],
        "retained": values(cdp), "focus": focus(cdp)}
    evidence["normal_text"] = cdp.evaluate(f"document.querySelector('{scope}').innerText")
    measure(cdp, output, evidence, CREATE, "initial", scope=scope)
    if not after:
        return
    technical = CREATE + " .technical-details pre"
    cdp.events.clear()
    open_metadata(cdp, technical)
    assert posts(cdp) == [] and counts["matches"] == before_count
    identity = json.loads(cdp.evaluate(f"document.querySelector('{technical}').innerText"))
    assert identity == FORMAT.to_dict()
    evidence["actions"]["technical-details"] = {"posts": [], "focus": focus(cdp)}
    measure(cdp, output, evidence, CREATE, "technical", scope=technical)
    native_text(cdp, CREATE + ' [name="custom_platform"]', "")
    submit(cdp, CREATE + ' button[value="update"]', evidence, "custom-error", error=True)
    assert product_bytes(context) == before and counts["matches"] == before_count
    assert context.frontend_profile.profile_path.read_bytes() == original_profile
    measure(cdp, output, evidence, CREATE, "error", scope=".error-summary")
    other = "en" if locale == "de" else "de"
    # Submitted errors survive natively; unsent values in a different form require #223 JS.
    native_text(cdp, CREATE + ' [name="custom_platform"]', "Unsent browser-only value")
    submit(cdp, f'form.language-selector button[value="{other}"]', evidence,
           "unsent-language", error=True)
    assert values(cdp)["custom_platform"] == (
        "Unsent browser-only value" if evidence["javascript"] else "")
    native_text(cdp, CREATE + ' [name="custom_platform"]', CUSTOM)
    native_text(cdp, CREATE + ' [name="middlehand_name"]', "Anna")
    submit(cdp, CREATE + ' button[value="update"]', evidence, "roster-error", error=True)
    submit(cdp, f'form.language-selector button[value="{locale}"]', evidence,
           "submitted-language", error=True)
    assert values(cdp)["custom_platform"] == CUSTOM
    assert values(cdp)["middlehand_name"] == "Anna"
    assert values(cdp)["source_url"] == "https://youtu.be/synthetic"
    assert values(cdp)["local_date"] == "2026-09-03" and values(cdp)["local_time"] == "19:30"
    native_text(cdp, CREATE + ' [name="middlehand_name"]', "Peter")
    if locale == "de":
        choose(cdp, CREATE + ' [name="save_platform"]')
    submit(cdp, CREATE + ' button[value="update"]', evidence, "setup-review")
    assert product_bytes(context) == before and counts["matches"] == before_count
    expected_profile = context.frontend_profile.profile_path.read_bytes()
    measure(cdp, output, evidence, CREATE, "setup", scope=scope)
    assert context.frontend_profile.profile_path.read_bytes() == expected_profile
    submit(cdp, CREATE + ' button[value="create"]', evidence, "create")
    assert counts["matches"] == before_count + 1
    active = context.managed_stateful.active_match
    workspace = load_match_workspace_file_v1(active.path).document.workspace
    definition = workspace.match_definition
    assert workspace == active.workspace and workspace.revision == 0
    assert definition.tournament_format is FORMAT and len(workspace.slots) == 36
    assert definition.game_platform == CUSTOM
    assert definition.source.source_kind == "youtube_video"
    assert definition.played_at == "2026-09-03T19:30:00+02:00"
    first = rotation(definition, 1)
    labels = {p.player_id: p.player_label for p in definition.participants}
    assert [labels[getattr(first, f"{s}_player_id")] for s in (
        "forehand", "middlehand", "rearhand")] == ["Anna", "Peter", "Mira"]
    assert first.middlehand_player_id == definition.perspective_player_id
    assert context.frontend_profile.document.preferred_game_platform == CUSTOM
    evidence["created"] = {"format": FORMAT.to_dict(), "platform": definition.game_platform,
        "slots": len(workspace.slots), "first_game": ["Anna", "Peter", "Mira"],
        "perspective": "Peter", "source_kind": definition.source.source_kind,
        "played_at": definition.played_at, "product_saves": 1}
    accepted = product_bytes(context)
    cdp.events.clear()
    open_metadata(cdp, META)
    assert posts(cdp) == [] and product_bytes(context) == accepted
    measure(cdp, output, evidence, "#match-metadata", "metadata")
    submit(cdp, f'form.language-selector button[value="{other}"]', evidence, "metadata-language")
    assert product_bytes(context) == accepted and counts["matches"] == before_count + 1
    submit(cdp, f'form.language-selector button[value="{locale}"]', evidence,
           "metadata-language-back")
    cdp.navigate(server.origin + "/matches")
    submit(cdp, f'form[action="/matches/open"]:has(input[value="{active.handle}"]) button',
           evidence, "reopen")
    assert product_bytes(context) == accepted and counts["matches"] == before_count + 1
    reopened = context.managed_stateful.active_match
    assert load_match_workspace_file_v1(reopened.path).document.workspace == workspace
    evidence["reopened_sha256"] = hashlib.sha256(reopened.path.read_bytes()).hexdigest()
    resource_evidence(cdp, server, evidence)
    evidence["loaded_resources"] = cdp.evaluate("""performance.getEntriesByType('resource')
        .map(e=>new URL(e.name).pathname)""")


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    hashes = {}
    for name in MODULES:
        data = files("skatmind").joinpath(name).read_bytes()
        expected = ((ROOT / "src/skatmind" / name).read_bytes() if args.phase == "after" else
            subprocess.check_output(["git", "show", f"{START}:src/skatmind/{name}"], cwd=ROOT))
        assert data == expected, name
        hashes[name] = hashlib.sha256(data).hexdigest()
    evidence = {"starting_head": START, "phase": args.phase, "completed": False,
        "python": sys.version, "package": skatmind.__version__, "module": skatmind.__file__,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(), "hashes": hashes,
        "runs": []}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="match-format-evidence")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            try:
                cdp = browser.cdp
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=match-format-evidence")
                time.sleep(.5)
                for locale in ("de", "en"):
                    item = {"javascript": javascript, "mode": mode, "phase": args.phase,
                        "locale": locale, "browser": browser.version, "actions": {},
                        "measurements": []}
                    evidence["runs"].append(item)
                    counts = {"matches": 0}
                    real_replace = os.replace
                    def counted(source, destination, context=context, counts=counts,
                                real_replace=real_replace):
                        if Path(destination).parent == context.managed_stateful.root("matches"):
                            counts["matches"] += 1
                        return real_replace(source, destination)
                    with (patch("os.replace", side_effect=counted),
                          patch("skatmind.capture_web.analysis.execute_match_decision_analysis_v1",
                                side_effect=AssertionError("Unexpected analysis")),
                          patch("skatmind.capture_web.analysis.execute_match_historical_analysis_v1",
                                side_effect=AssertionError("Unexpected analysis"))):
                        flow(cdp, server, context, output, item, counts)
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        evidence["completed"] = True
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({"completed": True, "measurements": sum(
        len(item["measurements"]) for item in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--phase", choices=("before", "after"), required=True)
    run(parser.parse_args())
