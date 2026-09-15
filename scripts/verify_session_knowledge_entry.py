"""Optional installed-Wheel knowledge-choice evidence with dependency-free DevTools."""

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
from urllib.parse import parse_qs

from _workflow_visual_browser import LocalBrowser
from verify_compact_card_entry import build_historical_input, choose, posts, wait
from verify_compact_declaration import resource_evidence
from verify_home_recorded_review import download
from verify_local_time_entry import native_select
from verify_match_format_presentation import native_text
from verify_session_direct_card_start import CARDS, MODULES, focus, measure

import skatmind
import skatmind.app_web.execution as execution
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.session_transitions import replay_session_state_v1

ROOT = Path(__file__).resolve().parents[1]
START = "ffe1c3c6f8f08940e80875f4a5608516ad170f50"
CREATE = 'form[action="/sessions/create"]'
KNOWLEDGE = CREATE + ' > fieldset:has(input[name="capture_mode"])'
NAMES = ("Alexandra-Maria von Hohenlohe-Schillingsfuerst", "Boris <&> Long-Player-Name", "Clara")


def submit(cdp, selector, evidence, name, *, error=False):
    cdp.events.clear()
    cdp.activate(selector)
    wait(cdp, error=error)
    assert len(posts(cdp)) == 1, posts(cdp)
    request = next(e["params"]["request"] for e in cdp.events
                   if e["params"]["request"]["method"] == "POST")
    values = parse_qs(request.get("postData", ""), keep_blank_values=True)
    evidence["actions"][name] = {"posts": posts(cdp), "focus": focus(cdp),
        "values": {k: v for k, v in values.items() if k in {
            "capture_mode", "perspective_seat", "setup_action", "cards", "language", "kind"}},
        "destination": cdp.evaluate("location.pathname+location.hash")}
    if error:
        assert cdp.evaluate("document.activeElement.matches('.error-summary')")
    return values


def checked(cdp):
    return cdp.evaluate(f"document.querySelector('{CREATE} [name=capture_mode]:checked').value")


def assert_text(cdp, selector, expected):
    assert expected in cdp.evaluate(f"document.querySelector({json.dumps(selector)}).innerText")


def names(cdp, title):
    native_text(cdp, CREATE + ' [name=game_name]', title)
    for seat, name in zip(("forehand", "middlehand", "rearhand"), NAMES, strict=True):
        native_text(cdp, CREATE + f' [name={seat}_name]', name)


def save_hand(cdp, active, hand, counts, evidence, name):
    before, count, revision = active.path.read_bytes(), counts["saves"], active.state.revision
    cdp.events.clear()
    for card in hand:
        choose(cdp, CARDS + f' input[value="{card}"]')
    assert posts(cdp) == [] and active.path.read_bytes() == before
    evidence["actions"][name + "-selection"] = {"posts": [], "focus": focus(cdp)}
    submit(cdp, CARDS + ' button', evidence, name)
    assert counts["saves"] == count + 1
    assert active.state.revision == revision + len(hand) + (1 if revision == 0 else 0)


def ended_review(cdp, server, active, output, evidence, counts, data):
    # Surrounding legal recorded Plays are HTTP fixture setup, not browser actions.
    # The native creation and initial hand above remain the only supplied private hand.
    from test_session_recorded_review_web import Browser
    browser = Browser(server)
    before = counts["executes"]
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    frozen = active.decision_checkpoints[0].request.to_dict()["document"]
    plays = [play for trick in data["tricks"] for play in trick["plays"]]
    for play in plays:
        browser.command("record_play", card=play["card"])
    assert counts["executes"] == before == 0
    facts = replay_session_state_v1(active.state)
    assert facts.played_card_count == 30 and len(facts.initial_known_hands) == 1
    assert active.state.phase == "play" and len(active.decision_checkpoints) == 10
    evidence["fixture_setup"] = {"transport": "real returned-form HTTP",
        "commands": ["set_declarer", "set_declaration", "30 record_play"],
        "private_initial_hands": 1, "analysis_executions": 0, "saved_checkpoints": 10}
    cdp.navigate(server.origin + "/sessions/current")
    assert cdp.evaluate("!!document.querySelector('form[action=\"/sessions/review-decision\"]')")
    submit(cdp, '#session-recording form button', evidence, "explicit-game-end")
    assert active.state.phase == "ended" and active.state.capture_mode == "live"
    measure(cdp, output, evidence, "#recorded-decisions", "ended-decisions")
    before, saves = active.path.read_bytes(), counts["saves"]
    submit(cdp, 'form[action="/sessions/review-decision"] button', evidence, "ended-review")
    assert counts["executes"] == 1 and counts["saves"] == saves
    assert active.path.read_bytes() == before
    request = download(cdp, server, "/sessions/downloads/request.json")
    assert json.loads(request) == {**frozen, "analysis_mode": "post_game_review",
                                   "actual_card_played": plays[0]["card"]}
    measure(cdp, output, evidence, "#session-result", "ended-result")
    result = download(cdp, server, "/sessions/downloads/result.json")
    evidence["ended_review"] = {"capture_mode": active.state.capture_mode,
        "phase": active.state.phase, "request_sha256": hashlib.sha256(request).hexdigest(),
        "result_sha256": hashlib.sha256(result).hexdigest(), "frozen_request_exact": True}
    cdp.navigate(server.origin + "/sessions")
    submit(cdp, f'form[action="/sessions/open"]:has(input[value="{active.handle}"]) button',
           evidence, "reopen-ended")
    reopened = server.app_context.managed_stateful.active_session
    assert reopened.path.read_bytes() == before and reopened.execution is None
    assert reopened.state.capture_mode == "live"
    assert all(r.command.kind != "promote_to_retrospective" for r in reopened.state.command_log)
    submit(cdp, 'form[action="/sessions/review-decision"] button', evidence, "reopened-review")
    assert download(cdp, server, "/sessions/downloads/request.json") == request
    assert counts["executes"] == 2 and counts["saves"] == saves


def flow(cdp, server, context, output, evidence, counts):
    locale = evidence["locale"]
    other = "en" if locale == "de" else "de"
    cdp.navigate(server.origin + "/sessions")
    submit(cdp, f'form.language-selector button[value="{locale}"]', evidence, "initial-language")
    assert checked(cdp) == "live"
    profile = context.frontend_profile.profile_path.read_bytes()
    cdp.events.clear()
    for mode, key in (("retrospective", "reconstruction"), ("live", "perspective")):
        choose(cdp, CREATE + f' input[value="{mode}"]')
        assert checked(cdp) == mode
        assert_text(cdp, KNOWLEDGE, text(locale, "session.knowledge." + key))
        assert_text(cdp, KNOWLEDGE, text(locale, "creation.session." + key + "_help"))
    assert not posts(cdp) and counts == {"saves": 0, "executes": 0}
    assert context.frontend_profile.profile_path.read_bytes() == profile
    evidence["actions"]["knowledge-selection"] = {"posts": [], "values": ["retrospective", "live"]}
    measure(cdp, output, evidence, KNOWLEDGE, "knowledge-choices")
    names(cdp, "Synthetic past Game")
    submit(cdp, CREATE + ' button[value="update"]', evidence, "missing-perspective", error=True)
    assert_text(cdp, '.error-summary', text(locale, "validation.session.knowledge_perspective"))
    assert counts == {"saves": 0, "executes": 0}
    assert context.frontend_profile.profile_path.read_bytes() == profile
    measure(cdp, output, evidence, ".error-summary", "missing-perspective-error")
    for language in (other, locale):
        submit(cdp, f'form.language-selector button[value="{language}"]', evidence,
               "rejected-language-" + language, error=True)
        assert checked(cdp) == "live"
        value = cdp.evaluate(f"document.querySelector('{CREATE} [name=middlehand_name]').value")
        assert value == NAMES[1]
    choose(cdp, CREATE + ' input[value="retrospective"]')
    if evidence["javascript"]:
        submit(cdp, f'form.language-selector button[value="{other}"]', evidence,
               "unsent-mode-language", error=True)
        assert checked(cdp) == "retrospective"
        submit(cdp, f'form.language-selector button[value="{locale}"]', evidence,
               "unsent-mode-language-return", error=True)
        assert checked(cdp) == "retrospective"
    submit(cdp, CREATE + ' button[value="update"]', evidence, "no-local-reconstruction-setup")
    assert counts == {"saves": 0, "executes": 0}
    choose(cdp, CREATE + ' input[value="live"]')
    seat_index = 3 if locale == "de" else 1
    seat = "rearhand" if locale == "de" else "forehand"
    assert native_select(cdp, CREATE + ' [name=perspective_seat]', down=seat_index) == seat
    submit(cdp, CREATE + ' button[value="update"]', evidence, "perspective-setup")
    values = submit(cdp, CREATE + ' button[value="create"]', evidence, "perspective-create")
    assert values["capture_mode"] == ["live"] and values["perspective_seat"] == [seat]
    active = context.managed_stateful.active_session
    assert active.state.revision == 0 and active.state.command_log == () and counts["saves"] == 1
    local = next(p for p in active.state.players if p.player_id == active.state.local_player_id)
    assert local.seat == seat
    assert_text(cdp, "#session-app", text(locale, "session.knowledge.accepted_mode",
        mode=text(locale, "session.knowledge.perspective")))
    measure(cdp, output, evidence, "#session-recording", "perspective-initial")
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    save_hand(cdp, active, data["players"][seat_index - 1]["initial_hand"], counts,
              evidence, "first-hand")
    assert active.state.revision == 11 and active.state.phase == "declaration"
    assert len(replay_session_state_v1(active.state).initial_known_hands) == 1
    assert [r.command.kind for r in active.state.command_log] == [
        "set_game_metadata", *["record_dealt_card"] * 10]
    evidence["first_hand"] = {"capture_mode": "live", "seat": seat, "commands": 11,
        "save_replacements": 1, "played_at": replay_session_state_v1(active.state).played_at}
    measure(cdp, output, evidence, "#session-recording", "perspective-next")
    if not evidence["javascript"] and locale == "en":
        ended_review(cdp, server, active, output, evidence, counts, data)
    # A second native creation explicitly chooses full reconstruction with a local Player.
    cdp.navigate(server.origin + "/sessions")
    names(cdp, "Synthetic full reconstruction")
    choose(cdp, CREATE + ' input[value="retrospective"]')
    assert native_select(cdp, CREATE + ' [name=perspective_seat]', down=1) == "forehand"
    submit(cdp, CREATE + ' button[value="update"]', evidence, "reconstruction-setup")
    values = submit(cdp, CREATE + ' button[value="create"]', evidence, "reconstruction-create")
    assert values["capture_mode"] == ["retrospective"]
    active = context.managed_stateful.active_session
    save_hand(cdp, active, data["players"][0]["initial_hand"], counts,
              evidence, "reconstruction-hand-1")
    assert active.state.phase == "deal" and active.state.revision == 11
    assert_text(cdp, "#session-recording", text(locale, "compact.for",
        player=NAMES[1] + " — " + text(locale, "creation.seat.middlehand")))
    players = ", ".join(p.player_label + " — " + text(locale, "creation.seat." + p.seat)
                        for p in active.state.players)
    assert_text(cdp, "#session-recording", text(
        locale, "session.knowledge.all_hands", players=players))
    measure(cdp, output, evidence, "#session-recording", "reconstruction-opponent")
    for i in (1, 2):
        save_hand(cdp, active, data["players"][i]["initial_hand"], counts,
                  evidence, f"reconstruction-hand-{i + 1}")
        assert active.state.phase == "deal"
    save_hand(cdp, active, data["skat"], counts, evidence, "reconstruction-skat")
    assert active.state.phase == "declaration" and active.state.revision == 33
    evidence["reconstruction"] = {"capture_mode": "retrospective", "local_seat": "forehand",
        "initial_hands": 3, "original_skat_count": 2, "revision": 33, "phase": "declaration"}
    resource_evidence(cdp, server, evidence)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh directory under an existing scratch parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install a Wheel first"
    names = tuple("app_web/" + name for name in MODULES) + (
        "app_web/seat_setup_rendering.py", "app_web/validation_mapping.py",
        "app_web/session_recorded_review_rendering.py", "session_commands.py",
        "session_incremental_validation.py", "session_transitions.py")
    hashes = {}
    for name in names:
        data = files("skatmind").joinpath(name).read_bytes()
        assert data == (ROOT / "src/skatmind" / name).read_bytes(), name
        hashes[name] = hashlib.sha256(data).hexdigest()
    evidence = {"starting_sha": START, "completed": False, "python": sys.version,
        "package": skatmind.__version__, "module": skatmind.__file__, "hashes": hashes,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(), "runs": []}
    try:
        for javascript in (True, False):
            for locale in ("de", "en"):
                mode = "js" if javascript else "native"
                suffix = mode + "-" + locale
                context = AppWebContextV1.create(prepare_managed_home_v1(
                    output / ("managed-" + suffix)))
                server = start_app_web_server_v1(context, port=0, token="localization-test-token")
                thread = serve_app_web_in_thread_v1(server)
                browser = LocalBrowser(args.browser, output / ("browser-" + suffix))
                try:
                    cdp = browser.cdp
                    cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                    cdp.call("Page.navigate", url=server.origin + "/?token=localization-test-token")
                    time.sleep(.5)
                    item = {"javascript": javascript, "mode": mode, "locale": locale,
                        "browser": browser.version, "actions": {}, "measurements": []}
                    evidence["runs"].append(item)
                    counts = {"saves": 0, "executes": 0}
                    real_replace, real_execute = os.replace, execution.execute
                    def counted(source, destination, real_replace=real_replace, counts=counts):
                        result = real_replace(source, destination)
                        if Path(destination).parent.name == "sessions":
                            counts["saves"] += 1
                        return result
                    def executed(*args, real_execute=real_execute, counts=counts, **kwargs):
                        counts["executes"] += 1
                        return real_execute(*args, **kwargs)
                    with (patch.object(os, "replace", counted),
                          patch.object(execution, "execute", executed)):
                        flow(cdp, server, context, output, item, counts)
                    assert counts["executes"] == (2 if mode == "native" and locale == "en" else 0)
                    item["totals"] = counts
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
    run(parser.parse_args())
