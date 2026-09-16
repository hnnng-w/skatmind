"""Installed-Wheel browser evidence; synthetic recordings and explicit negative transport setup."""

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
from verify_compact_card_entry import choose, fill, posts, wait
from verify_compact_declaration import resource_evidence
from verify_home_recorded_review import download
from verify_session_direct_card_start import focus, measure, submit

import skatmind
import skatmind.app_web.execution as execution
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
from skatmind.app_web.session_card_feedback import render_card_witness
from skatmind.app_web.stateful_localization import text

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    "assets/app.css", "assets/workflow.js", "locales/en.json", "locales/de.json",
    "session_card_feedback.py", "session_card_entry.py", "card_entry_http.py",
    "validation_contracts.py", "validation_mapping.py", "validation_rendering.py",
    "task_first_session_rendering.py", "recorded_trick_rendering.py", "session_frontend.py",
    "language_context.py", "language_form_preservation.py", "recording_deletion.py", "server.py",
)
CARDS = 'form[action="/sessions/cards"]'
PLAY = 'form[action="/sessions/play"]'
LONG_NAME = "Anna <synthetic & accepted> " + "LongName" * 11


def snapshot(active):
    return (active.path.read_bytes(), active.document, active.decision_checkpoints,
            active.generation, active.execution, active.recorded_review_source)


def negative_request(cdp, card, item, name):
    """Construct an authenticated invalid request, not an offered native Card selection.

    Copy only the emitted transport controls to a temporary harness-owned form.
    The application's legal palette is neither changed nor claimed to offer the Card.
    Enter submits this deliberately invalid request and displays its real HTTP response.
    """
    assert cdp.evaluate(f"document.querySelector('{PLAY} input[value=\"{card}\"]')===null")
    cdp.evaluate("""(card => {
        const source=document.querySelector('form[action="/sessions/play"]');
        const form=document.createElement('form');form.method='post';form.action=source.action;
        form.id='harness-negative-request';
        for(const control of source.querySelectorAll('input[type=hidden]'))
            form.append(control.cloneNode());
        const input=document.createElement('input');input.type='hidden';input.name='cards';
        input.value=card;form.append(input);
        const button=document.createElement('button');button.type='submit';
        button.textContent='Synthetic negative request';form.append(button);
        document.body.append(form);
    })(""" + json.dumps(card) + ")")
    submit(cdp, '#harness-negative-request button', item, name, error=True)
    item["actions"][name]["setup"] = "Authenticated negative payload; Card excluded by real palette"
    item["actions"][name]["attempted_card"] = card


def create(cdp, server, context, item, counts, output, *, local):
    cdp.navigate(server.origin + "/sessions")
    cdp.activate(f'form.language-selector button[value="{item["locale"]}"]')
    wait(cdp)
    form = 'form[action="/sessions/create"]'
    for field, value in {"game_name": "Synthetic feedback " + local, "perspective_seat": local,
            "forehand_name": LONG_NAME, "middlehand_name": "Boris",
            "rearhand_name": "Clara"}.items():
        fill(cdp, form + f' [name="{field}"]', value)
    choose(cdp, form + ' input[value="live"]')
    submit(cdp, form + ' button[value="update"]', item, local + "-setup")
    submit(cdp, form + ' button[value="create"]', item, local + "-create")
    active = context.managed_stateful.active_session
    assert active.state.revision == 0
    before, old_count = snapshot(active), dict(counts)
    submit(cdp, CARDS + ' button', item, local + "-native-empty", error=True)
    assert snapshot(active) == before and counts == old_count
    assert text(item["locale"], "validation.card_entry.empty") in cdp.evaluate(
        "document.querySelector('.error-summary').innerText")
    measure(cdp, output, item, ".error-summary", local + "-native-empty")
    hand = (["C7", "SQ", "CA", "C10", "CK", "CQ", "C9", "C8", "SA", "S10"]
            if local == "forehand" else
            ["C8", "C9", "C10", "CK", "CQ", "CA", "SQ", "SA", "S10", "SK"])
    cdp.events.clear()
    for card in hand:
        choose(cdp, CARDS + f' input[value="{card}"]')
    assert posts(cdp) == [] and snapshot(active) == before
    submit(cdp, CARDS + ' button', item, local + "-hand")
    assert active.state.revision == 11 and counts["saves"] == old_count["saves"] + 1
    declarer = '#session-recording form:has(input[name="kind"][value="set_declarer"])'
    fill(cdp, declarer + ' select', active.state.local_player_id)
    submit(cdp, declarer + ' button', item, local + "-declarer")
    declaration = '#session-recording form:has(input[name="kind"][value="set_declaration"])'
    fill(cdp, declaration + ' [name=game_type]', "grand")
    choose(cdp, declaration + ' [name=hand_game]')
    submit(cdp, declaration + ' button', item, local + "-declaration")
    for card in (["C7", "H7"] if local == "forehand" else ["C7"]):
        choose(cdp, PLAY + f' input[value="{card}"]')
        submit(cdp, PLAY + ' button', item, local + "-accepted-" + card)
    if local == "forehand":
        prior = counts["executions"]
        submit(cdp, 'form[action="/sessions/review-decision"] button', item, "real-review")
        assert counts["executions"] == prior + 1 and active.execution is not None
    return active


def flow(cdp, server, context, output, item, counts):
    for local, cases in (("forehand", (("SQ", "owner_hand"), ("C7", "played"))),
                         ("middlehand", (("SQ", "follow"), ("H7", "missing_hand")))):
        active = create(cdp, server, context, item, counts, output, local=local)
        before, old_counts = snapshot(active), dict(counts)
        retained = ({name: download(cdp, server, "/sessions/downloads/" + name + ".json")
                     for name in ("request", "result")} if active.execution else {})
        for card, kind in cases:
            negative_request(cdp, card, item, kind + "-negative")
            assert snapshot(active) == before and counts == old_counts
            feedback = context.form_feedback.current("sessions", active_identity=active)
            witness = feedback.validation_issues[0].session_card_feedback.witness
            assert witness.kind == kind
            for locale in (item["locale"], "en" if item["locale"] == "de" else "de"):
                if locale != item["locale"]:
                    submit(cdp, f'form.language-selector button[value="{locale}"]',
                           item, kind + "-language-" + locale, error=True)
                message, anchor = render_card_witness(witness, active.state.players, locale)
                summary = cdp.evaluate("document.querySelector('.error-summary').innerText")
                assert message in summary
                assert text(locale, "validation.session_card.heading") in summary
                assert text(locale, "validation.summary.guidance") not in summary
                assert cdp.evaluate(
                    f"document.querySelector('{PLAY} input[value=\"{card}\"]')===null")
                assert cdp.evaluate("document.activeElement.classList.contains('error-summary')"), (
                    kind, locale, focus(cdp))
                measure(cdp, output, item, ".error-summary", kind + "-error-" + locale)
                cdp.events.clear()
                cdp.activate('a.session-card-evidence')
                assert posts(cdp) == [] and cdp.evaluate("document.activeElement.id") == anchor
                assert cdp.evaluate("document.activeElement.checkVisibility()")
                measure(cdp, output, item, "#" + anchor, kind + "-evidence-" + locale)
                item["actions"][kind + "-inspect-" + locale] = {
                    "posts": [], "focus": focus(cdp), "anchor": anchor, "message": message}
                assert snapshot(active) == before and counts == old_counts
            submit(cdp, f'form.language-selector button[value="{item["locale"]}"]',
                   item, kind + "-language-return", error=True)
        for name, data in retained.items():
            assert download(cdp, server, "/sessions/downloads/" + name + ".json") == data
        item.setdefault("preservation", {})[local] = {
            "session_sha256": hashlib.sha256(before[0]).hexdigest(),
            "checkpoints": len(active.decision_checkpoints),
            "downloads": {name: hashlib.sha256(data).hexdigest()
                          for name, data in retained.items()},
            "rejection_save_count": counts["saves"] - old_counts["saves"],
            "rejection_execution_count": counts["executions"] - old_counts["executions"]}
        # Correct using an actually emitted selectable radio, with native Space and Enter.
        valid = cdp.evaluate(f"document.querySelector('{PLAY} input[name=cards]').value")
        choose(cdp, PLAY + f' input[value="{valid}"]')
        submit(cdp, PLAY + ' button', item, local + "-continued-entry")
        assert counts["saves"] == old_counts["saves"] + 1
        assert active.state.revision == before[1].state.revision + 1
        assert active.execution is None
        assert cdp.evaluate("document.activeElement.id") == "session-recording"
        assert not cdp.evaluate("!!document.querySelector('.error-summary')")
        measure(cdp, output, item, "#session-recording", local + "-continued-entry")
        saved = active.path.read_bytes()
        cdp.navigate(server.origin + "/sessions")
        submit(cdp, f'form[action="/sessions/open"]:has(input[value="{active.handle}"]) button',
               item, local + "-reopen")
        assert context.managed_stateful.active_session.path.read_bytes() == saved
        assert not cdp.evaluate("!!document.querySelector('.session-card-evidence')")
    resource_evidence(cdp, server, item)


def run(args):
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Use a fresh evidence directory under an existing temporary parent")
    output.mkdir()
    assert not Path(skatmind.__file__).resolve().is_relative_to(ROOT), "Install the Wheel first"
    hashes = {}
    for name in MODULES:
        data = files("skatmind.app_web").joinpath(name).read_bytes()
        assert data == (ROOT / "src/skatmind/app_web" / name).read_bytes(), name
        hashes[name] = hashlib.sha256(data).hexdigest()
    evidence = {"completed": False, "python": sys.version, "package": skatmind.__version__,
        "module": skatmind.__file__,
        "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        "hashes": hashes, "runs": [], "unmet": []}
    try:
        for javascript in (True, False):
            mode = "js" if javascript else "native"
            context = AppWebContextV1.create(prepare_managed_home_v1(output / ("managed-" + mode)))
            server = start_app_web_server_v1(context, port=0, token="feedback-evidence")
            thread = serve_app_web_in_thread_v1(server)
            browser = LocalBrowser(args.browser, output / ("browser-" + mode))
            cdp = browser.cdp
            try:
                cdp.call("Emulation.setScriptExecutionDisabled", value=not javascript)
                cdp.call("Page.navigate", url=server.origin + "/?token=feedback-evidence")
                time.sleep(.5)
                for locale in ("de", "en"):
                    item = {"mode": mode, "locale": locale, "javascript": javascript,
                        "browser": browser.version, "actions": {}, "measurements": []}
                    evidence["runs"].append(item)
                    counts = {"saves": 0, "executions": 0}
                    real_replace, real_execute = os.replace, execution.execute
                    def counted(source, destination, real_replace=real_replace, counts=counts):
                        result = real_replace(source, destination)
                        if Path(destination).parent.name == "sessions":
                            counts["saves"] += 1
                        return result
                    def execute(*args, real_execute=real_execute, counts=counts, **kwargs):
                        counts["executions"] += 1
                        return real_execute(*args, **kwargs)
                    with patch.object(os, "replace", counted), patch.object(execution, "execute",
                                                                           execute):
                        flow(cdp, server, context, output, item, counts)
                    item["counts"] = counts
            finally:
                browser.close()
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        evidence["completed"] = True
    except Exception as error:
        evidence["unmet"].append(str(error))
        raise
    finally:
        (output / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(json.dumps({"completed": evidence["completed"], "unmet": evidence["unmet"],
            "measurements": sum(len(item["measurements"]) for item in evidence["runs"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    run(parser.parse_args())
