"""Optional installed-Wheel #238 evidence using the existing native DevTools harness."""

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
from urllib.parse import urlsplit

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import choose, posts, wait
from verify_compact_declaration import resource_evidence
from verify_home_recorded_review import download
from verify_local_time_entry import native_select
from verify_match_format_presentation import native_text
from verify_session_direct_card_start import focus

import skatmind
import skatmind.capture_web.analysis as analysis
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

ROOT = Path(__file__).resolve().parents[1]
START = "dd981819bf4a23577dd485ebd72b20a66435429d"
MODULES = ("app_web/assets/app.css", "app_web/assets/workflow.js",
    "app_web/locales/en.json", "app_web/locales/de.json", "app_web/server.py",
    "app_web/task_first_match_rendering.py", "app_web/task_first_match_state.py",
    "app_web/task_first_projections.py", "app_web/match_frontend.py",
    "app_web/match_review_rendering.py", "app_web/language_context.py",
    "app_web/match_recovery.py", "app_web/form_registry.py", "match_workspace_progress.py")
CREATE = 'form[action="/matches/api/v1/create"]'
PLAY = 'form[action="/matches/cards"]:has(input[value="append_plays"])'
DECLARATION = '#match-declaration form:has(input[value="match-declaration"])'


def operation(name):
    return f'#match-recording form:has(input[name="operation"][value="{name}"])'


def action(cdp, selector, item, name, counts, *, saves=0, post=None, error=False):
    before = counts["saves"]
    executions = counts["executions"]
    cdp.events.clear()
    cdp.activate(selector)
    try:
        wait(cdp, error=error)
    except AssertionError:
        message = cdp.evaluate("document.querySelector('main').innerText")
        raise AssertionError((name, message)) from None
    observed = posts(cdp)
    record = {"posts": observed, "saves": counts["saves"] - before,
        "executions": counts["executions"] - executions,
        "path": cdp.evaluate("location.pathname+location.hash"), "focus": focus(cdp),
        "requests": [{"method": e["params"]["request"]["method"],
                      "path": urlsplit(e["params"]["request"]["url"]).path}
                     for e in cdp.events]}
    item["actions"][name] = record
    assert observed == ([] if post is None else [post]), (name, record)
    assert record["saves"] == saves, (name, record)
    assert record["executions"] == int(name == "analyze"), (name, record)
    if error:
        assert cdp.evaluate("document.activeElement.matches('.error-summary')")
    return record


def measure(cdp, server, output, item, name, *, path="/matches/position/1", error=False,
            counts=None):
    active = server.app_context.managed_stateful.active_match
    accepted, revision = active.path.read_bytes(), active.workspace.revision
    for width, height, scale in ((1365, 900, 1), (390, 844, 1), (320, 800, 1), (320, 800, 2)):
        cdp.call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                 deviceScaleFactor=1, mobile=False)
        for anchored in (False, True):
            if not error:
                cdp.navigate(server.origin + path + ("#match-recording" if anchored else ""))
            if scale == 2:
                cdp.evaluate("""(()=>{const es=[...document.querySelectorAll('body,body *')];
                    const sizes=es.map(e=>parseFloat(getComputedStyle(e).fontSize));
                    es.forEach((e,i)=>e.style.fontSize=sizes[i]*2+'px');})()""")
                if anchored:
                    cdp.evaluate("document.querySelector('#match-recording').scrollIntoView()")
            if error:
                cdp.evaluate("document.querySelector('.error-summary').scrollIntoView()")
            geometry = cdp.evaluate("""(()=>{
                const box=e=>{if(!e)return null;const r=e.getBoundingClientRect();return {
                    top:r.top+scrollY,viewport_top:r.top,width:r.width,height:r.height};};
                const recording=document.querySelector('#match-recording');
                const heading=recording.querySelector('h2');
                const primary=recording.querySelector('button.primary');
                const tiles=[...document.querySelectorAll('.match-tile')];
                return {path:location.pathname+location.hash,locale:document.documentElement.lang,
                    scroll_y:scrollY,error:box(document.querySelector('.error-summary')),
                    client:document.documentElement.clientWidth,
                    scroll:document.documentElement.scrollWidth,
                    heading:{text:heading.innerText,...box(heading)},
                    primary:box(primary),overview:box(document.querySelector('#match-games') ||
                        tiles[0].closest('.panel')),first_tile:box(tiles[0]),
                    tiles:tiles.length,rounds:document.querySelectorAll('.round-slots').length,
                    primary_count:recording.querySelectorAll('button.primary').length,
                    ids:[...document.querySelectorAll('[id]')].map(e=>e.id),
                    focus:{id:document.activeElement.id,tag:document.activeElement.tagName,
                        outline:getComputedStyle(document.activeElement).outline},
                    fields:[...recording.querySelectorAll('form')].filter(e=>e.checkVisibility())
                        .map(e=>({action:e.getAttribute('action'),...box(e)}))};})()""")
            item["measurements"].append({"state": name, "width": width, "scale": scale,
                                          "anchored": anchored, **geometry})
            assert geometry["tiles"] == 36 and geometry["rounds"] == 12
            if item["phase"] == "after":
                assert geometry["client"] == geometry["scroll"], geometry
                assert len(geometry["ids"]) == len(set(geometry["ids"])), geometry
                assert geometry["heading"]["top"] < geometry["overview"]["top"]
                if geometry["primary"]:
                    assert geometry["primary"]["top"] < geometry["overview"]["top"]
                if anchored and not error:
                    assert geometry["focus"]["id"] == "match-recording", geometry
            filename = f"{item['mode']}-{item['locale']}-{name}-{width}-{scale}-{anchored}.png"
            cdp.screenshot(output / filename)
            if anchored and geometry["primary"]:
                cdp.evaluate("document.querySelector('#match-recording button.primary')"
                             ".closest('form').scrollIntoView()")
                cdp.screenshot(output / filename.replace(".png", "-controls.png"))
            if scale == 2:
                cdp.evaluate("document.querySelectorAll('body,body *').forEach(e=>"
                             "e.style.removeProperty('font-size'))")
            if error:
                break
        if counts is not None and name == "partial" and item["phase"] == "after":
            prefix = f"native-{width}-{scale}"
            action(cdp, 'a[href="#match-games"]', item, prefix + "-overview", counts)
            action(cdp, '.match-tile[href="/matches/position/2#match-recording"]', item,
                   prefix + "-tile", counts)
            assert cdp.evaluate("document.activeElement.id") == "match-recording"
            action(cdp, '#match-recording a[href="/matches/position/1#match-recording"]',
                   item, prefix + "-gap", counts)
    assert active.path.read_bytes() == accepted and active.workspace.revision == revision


def flow(cdp, server, output, item, counts):
    context = server.app_context
    locale = item["locale"]
    cdp.navigate(server.origin + "/matches/new")
    action(cdp, f'form.language-selector button[value="{locale}"]', item,
           "initial-language", counts, post="/actions/profile/language")
    for name, value in {"match_title": "Synthetic navigation Match",
                        "forehand_name": 'Alexandra <Synthetic> & "Long Name" ' + "A" * 65,
                        "middlehand_name": "Boris", "rearhand_name": "Clara"}.items():
        native_text(cdp, CREATE + f' [name="{name}"]', value)
    native_select(cdp, CREATE + ' [name="perspective_seat"]', down=1)
    action(cdp, CREATE + ' button[value="update"]', item, "setup", counts,
           post="/matches/api/v1/create")
    action(cdp, CREATE + ' button[value="create"]', item, "create", counts,
           saves=1, post="/matches/api/v1/create")
    active = context.managed_stateful.active_match
    assert active.workspace.revision == 0 and active.workspace.slots[0].observed_game is None
    empty_bytes = active.path.read_bytes()
    measure(cdp, server, output, item, "empty")
    assert active.path.read_bytes() == empty_bytes
    action(cdp, operation("start_game") + ' button', item, "explicit-start", counts,
           saves=1, post="/matches/api/v1/operation")
    measure(cdp, server, output, item, "declaration")
    native_select(cdp, DECLARATION + ' [name="declarer_player_id"]', down=1)
    native_select(cdp, DECLARATION + ' [name="game_type"]', down=5)
    choose(cdp, DECLARATION + ' [name="hand_game"]')
    action(cdp, DECLARATION + ' button', item, "declare", counts,
           saves=1, post="/matches/api/v1/operation")
    assert active.workspace.slots[0].observed_game.declaration.game_type == "grand"
    choose(cdp, PLAY + ' input[value="SA"]')
    action(cdp, PLAY + ' button', item, "record", counts, saves=1, post="/matches/cards")
    measure(cdp, server, output, item, "partial", counts=counts)
    if item["phase"] == "before":
        return
    accepted = active.path.read_bytes()
    action(cdp, 'a[href="#match-games"]', item, "overview", counts)
    assert cdp.evaluate("document.activeElement.id") == "match-games"
    cdp.screenshot(output / f"{item['mode']}-{locale}-overview-focus.png")
    action(cdp, '.match-tile[href="/matches/position/2#match-recording"]', item,
           "select-game-2", counts)
    assert active.selected_position == 2 and active.workspace.slots[1].observed_game is None
    assert active.path.read_bytes() == accepted
    assert cdp.evaluate("document.activeElement.id") == "match-recording"
    action(cdp, operation("mark_passed_deal") + ' button', item, "explicit-pass", counts,
           saves=1, post="/matches/api/v1/operation")
    assert active.selected_position == 2 and active.workspace.slots[1].slot_kind == "passed_deal"
    measure(cdp, server, output, item, "passed", path="/matches/position/2")
    action(cdp, '#match-recording a[href="/matches/position/1#match-recording"]', item,
           "first-unfinished-backward", counts)
    choose(cdp, PLAY + ' input[value="S9"]')
    other = "en" if locale == "de" else "de"
    accepted = active.path.read_bytes()
    action(cdp, f'form.language-selector button[value="{other}"]', item,
           "safe-unsent-language", counts, post="/actions/profile/language")
    selected = cdp.evaluate(f"[...document.querySelectorAll('{PLAY} input[name=cards]:checked')]"
                           ".map(e=>e.value)")
    assert selected == (["S9"] if item["javascript"] else [])
    assert active.path.read_bytes() == accepted
    if not selected:
        choose(cdp, PLAY + ' input[value="S9"]')
    action(cdp, PLAY + ' button', item, "continue", counts, saves=1, post="/matches/cards")
    action(cdp, f'form.language-selector button[value="{locale}"]', item,
           "language-back", counts, post="/actions/profile/language")
    # A genuine server rejection from the existing specialist observed-Play form.
    legacy = 'form[action="/matches/api/v1/operation"]:has(input[value="append_plays"])'
    from verify_session_direct_card_start import open_metadata
    open_metadata(cdp, legacy)
    native_text(cdp, legacy + ' [name="cards"]', "SA")
    action(cdp, legacy + ' button', item, "duplicate-error", counts,
           post="/matches/api/v1/operation", error=True)
    measure(cdp, server, output, item, "error", error=True)
    action(cdp, f'form.language-selector button[value="{other}"]', item,
           "error-language", counts, post="/actions/profile/language", error=True)
    # Fixture continuation: real returned HTTP forms and saves, not browser actions.
    sys.path.insert(0, str(ROOT / "tests"))
    from test_match_recording_recovery_web import follow, synthetic_cards
    from test_session_recorded_review_web import Browser, Forms
    http = Browser(server)
    page = http.page("/matches/current")
    before = counts["saves"]
    batch = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/operation"
                 and f["values"].get("operation") == "append_plays")
    follow(http, http.submit(batch, cards=" ".join(synthetic_cards()[2:29])))
    assert counts["saves"] == before + 1
    item["fixture_setup"] = {"returned_form": "/matches/api/v1/operation",
                             "cards": 27, "saves": 1, "browser_action": False}
    # A fragment-only navigation deliberately does not refresh old source bindings.
    cdp.navigate(server.origin + "/matches/current")
    cdp.navigate(server.origin + "/matches/position/1#match-recording")
    action(cdp, f'form.language-selector button[value="{locale}"]', item,
           "fixture-language-back", counts, post="/actions/profile/language")
    choose(cdp, PLAY + f' input[value="{synthetic_cards()[-1]}"]')
    action(cdp, PLAY + ' button', item, "final-card", counts, saves=1, post="/matches/cards")
    assert active.selected_position == 1
    assert len(active.workspace.slots[0].observed_game.plays) == 30
    continuation = '#match-recording a[href="/matches/position/3#match-recording"]'
    assert cdp.evaluate(f"!!document.querySelector({json.dumps(continuation)})")
    measure(cdp, server, output, item, "complete")
    action(cdp, 'a[href="/matches/review/1"]', item, "review", counts)
    # Native review uses existing defaults; success is genuinely executed and retained.
    action(cdp, 'form:has(input[value="analyze_decision"]) button', item, "analyze", counts,
           post="/matches/api/v1/analysis")
    reports = active.capture.report_store.list()
    assert reports and reports[-1].value.status == "executed"
    report = reports[-1]
    result_route = f"/matches/api/v1/reports/{report.report_id}.json"
    result_bytes = download(cdp, server, result_route)
    item["report"] = {"id": report.report_id, "position": report.match_position,
        "game": active.workspace.slots[report.match_position - 1].observed_game.game_id,
        "download_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "heading": cdp.evaluate("document.querySelector('#match-review h2').innerText")}
    assert report.match_position == 1
    cdp.screenshot(output / f"{item['mode']}-{locale}-report.png")
    action(cdp, 'a[href="/matches/position/1#match-recording"]', item, "review-back", counts)
    action(cdp, '#match-play-30 form[action="/matches/recovery/select"]:nth-of-type(2) button',
           item, "rewind-preview", counts, post="/matches/recovery/select")
    selected, preview = active.recovery.selected, active.recovery.preview
    accepted = active.path.read_bytes()
    action(cdp, 'a[href="#match-games"]', item, "preview-overview", counts)
    action(cdp, '.match-tile[aria-current="page"]', item, "preview-same-game", counts)
    action(cdp, f'form.language-selector button[value="{locale}"]', item,
           "preview-language", counts, post="/actions/profile/language")
    assert cdp.evaluate("document.activeElement.id") == "match-recovery"
    assert active.recovery.selected is selected and active.recovery.preview is preview
    assert active.capture.report_store.list() == reports and active.path.read_bytes() == accepted
    assert download(cdp, server, result_route) == result_bytes
    cdp.screenshot(output / f"{item['mode']}-{locale}-rewind-focus.png")
    choose(cdp, 'form[action="/matches/recovery/apply"] [name="confirm_apply"]')
    action(cdp, 'form[action="/matches/recovery/apply"] button', item, "rewind-apply", counts,
           saves=1, post="/matches/recovery/apply")
    assert len(active.workspace.slots[0].observed_game.plays) == 29
    assert not active.capture.report_store.list() and active.recovery.preview is None
    assert not cdp.evaluate(f"!!document.querySelector({json.dumps(continuation)})")
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
    item["saved_sha256"] = hashlib.sha256(active.path.read_bytes()).hexdigest()
    item["total_saves"] = counts["saves"]
    resource_evidence(cdp, server, item)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh output under an existing scratch parent")
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
            for locale in ("de", "en"):
                mode = "js" if javascript else "native"
                suffix = mode + "-" + locale
                home = prepare_managed_home_v1(output / ("managed-" + suffix))
                context = AppWebContextV1.create(home)
                server = start_app_web_server_v1(context, port=0, token="localization-test-token")
                thread = serve_app_web_in_thread_v1(server)
                browser = LocalBrowser(args.browser, output / ("browser-" + suffix))
                counts = {"saves": 0, "executions": 0}
                real_replace = os.replace
                real_execute = analysis.execute_match_decision_analysis_v1
                def counted(source, destination, context=context, counts=counts,
                            real_replace=real_replace):
                    if Path(destination).parent == context.managed_stateful.root("matches"):
                        counts["saves"] += 1
                    return real_replace(source, destination)
                def executed(*args, counts=counts, real_execute=real_execute, **kwargs):
                    counts["executions"] += 1
                    return real_execute(*args, **kwargs)
                try:
                    cdp = browser.cdp
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                    cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
                    time.sleep(.5)
                    item = {"javascript": javascript, "mode": mode, "locale": locale,
                        "phase": args.phase, "browser": browser.version, "actions": {},
                        "measurements": []}
                    evidence["runs"].append(item)
                    with (patch("os.replace", side_effect=counted),
                          patch.object(analysis, "execute_match_decision_analysis_v1", executed)):
                        flow(cdp, server, output, item, counts)
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
