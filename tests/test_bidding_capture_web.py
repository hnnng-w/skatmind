import json
import os
import re
import subprocess
import sys
from contextlib import closing
from unittest.mock import patch

import pytest
from test_accounting_web import open_form, start
from test_compact_card_entry_web import create_live
from test_compact_declaration_web import before_declaration
from test_effort_preferences_web import start_live, submit
from test_frontend_language_switching import localized_server
from test_match_game_navigation_web import create_empty
from test_match_recording_recovery_web import follow, operation_form, start_match
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms

from skatmind.accounting_store import load_accounting
from skatmind.app_web.match_live_advice import MATCH_LIVE_ROUTES
from skatmind.app_web.saved_match_analyses import archive_store
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck
from skatmind.event_context_sources import build_recording_facts_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.session_persistence import load_session_persistence_file_v1
from skatmind.session_transitions import replay_session_state_v1


def bid_form(page, index):
    return next(f for f in Forms(page).forms if f["values"].get("bidding_form") == "auction"
                and f["values"]["index"] == str(index))


def cold_auction(path, family, position=1):
    # Read the original file in a fresh interpreter and report only observed public facts.
    program = """
import json, sys
from skatmind.bidding import replay_bidding
if sys.argv[2] == 'match':
    from skatmind.match_workspace_persistence import load_match_workspace_file_v1
    slot = load_match_workspace_file_v1(sys.argv[1]).document.workspace.slots[int(sys.argv[3])-1]
    game = slot.observed_game or slot.passed_game
    events, seats = slot.bidding, tuple(p.player_id for p in game.players)
    declaration = game.declaration
else:
    from skatmind.session_persistence import load_session_persistence_file_v1
    from skatmind.session_transitions import replay_session_state_v1
    game = replay_session_state_v1(load_session_persistence_file_v1(sys.argv[1]).document.state)
    events, seats, declaration = game.bidding, game.player_ids, game.declaration
turn = replay_bidding(seats, events)
print(json.dumps([[e.action for e in events], turn.actor, turn.declarer, turn.value,
                  turn.effective_value, declaration.bid_value if declaration else None]))
"""
    before = path.read_bytes()
    output = subprocess.check_output(
        [sys.executable, "-c", program, str(path), family, str(position)], text=True)
    assert path.read_bytes() == before
    return json.loads(output)


@pytest.mark.parametrize("family", ["session", "cent", "match"])
@pytest.mark.parametrize("locale", ["de", "en"])
def test_returned_forms_restart_and_correct(tmp_path, family, locale):
    with (closing(localized_server.__wrapped__(tmp_path)) as servers,
          patch("skatmind.app_web.execution.execute") as evaluate,
          patch("skatmind.app_web.automatic_match_learning.AutomaticMatchLearningServiceV1.update")
          as prepare):
        server = next(servers)
        browser = Browser(server)
        task = "/record-after" if locale == "de" else "/live-play"
        browser.page(task)
        if family == "match":
            start_match(browser, locale)
            page = browser.page("/matches/position/2")
            page = follow(browser, browser.submit(operation_form(page, "start_game")))
        elif family == "cent":
            page = start(browser)
        else:
            page = create(browser, mode="retrospective" if locale == "de" else "live")
        if family != "match" and locale == "de":
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
        managed = server.app_context.managed_stateful
        active = managed.active_match if family == "match" else managed.active_session
        path = active.path
        form = bid_form(page, 0)
        page = follow(browser, browser.submit(form, choice="pass"))
        assert browser.submit(form, choice="pass")[0] == 409
        assert text(locale, "bidding.title") in page
        before = path.read_bytes()
        evaluate.assert_not_called()
        prepare.assert_not_called()
    position = 2 if family == "match" else 1
    partial = cold_auction(path, family, position)
    assert partial[0] == ["pass"] and partial[1] and partial[2:] == [None] * 4
    with (closing(localized_server.__wrapped__(tmp_path)) as servers,
          patch("skatmind.app_web.execution.execute") as evaluate,
          patch("skatmind.app_web.automatic_match_learning.AutomaticMatchLearningServiceV1.update")
          as prepare):
        server = next(servers)
        browser = Browser(server)
        if family == "cent":
            page = follow(browser, browser.submit(
                Forms(browser.page("/cent")).find("/cent/resume")))
        elif family == "session":
            page = follow(browser, browser.submit(
                Forms(browser.page("/sessions")).find("/sessions/open")))
        else:
            follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
            page = browser.page("/matches/position/2")
        assert before == path.read_bytes()
        page = follow(browser, browser.submit(bid_form(page, 1), choice="pass"))
        assert browser.submit(bid_form(page, 2), choice="18")[0] == 400
        page = follow(browser, browser.submit(bid_form(page, 2), choice="pass"))
        assert text(locale, "task.value.passed_deal") in page
        assert cold_auction(path, family, position) == [["pass"] * 3, *([None] * 5)]
        if family == "match":
            document = load_match_workspace_file_v1(path).document
            assert document.workspace.slots[1].slot_kind == "passed_deal"
        else:
            document = load_session_persistence_file_v1(path).document
            assert build_recording_facts_v1(document).outcomes[0].status == "passed"
            assert document.decision_checkpoints == ()
        if family == "cent":
            page = follow(browser, browser.submit(open_form(page, 2)))
            rotated = server.app_context.managed_stateful.active_session.state
            assert bid_form(page, 0)["values"]["player_id"] == rotated.players[1].player_id
            assert rotated.players[1].player_id == document.state.players[2].player_id
            page = follow(browser, browser.submit(open_form(page, 1)))
        page = follow(browser, browser.submit(bid_form(page, 2), choice="take"))
        if family == "match":
            slot = load_match_workspace_file_v1(path).document.workspace.slots[1]
            assert slot.slot_kind == "observed_game"
            declaration = operation_form(page, "set_declaration")
            assert declaration["values"]["declarer_player_id"] == (
                slot.observed_game.players[0].player_id)
            assert declaration["values"]["bid_value"] == "18"
            assert browser.submit(declaration, game_type="grand", bid_value="19")[0] == 400
            page = follow(browser, browser.submit(declaration, game_type="grand"))
        else:
            document = load_session_persistence_file_v1(path).document
            assert replay_session_state_v1(document.state).declarer_player_id == (
                document.state.players[0].player_id)
        if family == "cent":
            row, = load_accounting(server.app_context.managed_home.root).round_heads
            assert row.context.bindings[0].attached_source.revision == 0
        complete = cold_auction(path, family, position)
        assert complete[:2] == [["pass", "pass", "take"], None] and complete[2]
        assert complete[3:5] == [None, 18]
        evaluate.assert_not_called()
        prepare.assert_not_called()


def test_session_declared_bid_and_first_conflicting_continuation(tmp_path):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        browser = Browser(server)
        hand = create_live(browser)
        page = follow(browser, browser.submit(hand, cards=get_full_deck()[:10]))
        for index, choice in enumerate(("35", "pass", "pass")):
            page = follow(browser, browser.submit(bid_form(page, index), choice=choice))
        declaration = Forms(page).find("/sessions/command", kind="set_declaration")
        assert declaration["values"]["bid_value"] == "35"
        page = follow(browser, browser.submit(declaration, game_type="grand", hand_game="true"))
        active = server.app_context.managed_stateful.active_session
        assert active.state.phase == "play"
        page = follow(browser, browser.submit(Forms(page).find("/sessions/play"),
                                              cards=get_full_deck()[0]))
        follow(browser, browser.submit(Forms(page).find("/sessions/review-decision")))
        archive = archive_store(server.app_context)
        route = re.search(r'href="(/sessions/saved-analyses/[a-f0-9]{64})"',
                          browser.page("/sessions/saved-analyses"))[1]
        page = browser.page(route)
        follow(browser, browser.submit(Forms(page).find("/learning/analysis-selection")))
        manifest = archive.snapshot().manifest
        assert len(manifest.excluded_analysis_ids) == 1
        downloads = {}
        for kind in ("request", "result"):
            status, _, raw = browser.request("GET", route + "/" + kind + ".json")
            assert status == 200
            downloads[kind] = raw
        original = active.document
        page = browser.page()
        target = bid_form(page, 0)
        status, _, rejection = browser.submit(target, choice="46")
        assert status == 400 and "Nothing was changed." in rejection.decode()
        assert active.document == original
        follow(browser, browser.submit(target, choice="46", confirm_suffix="yes"))
        facts = replay_session_state_v1(active.state)
        assert facts.bidding_turn.effective_value == 46
        assert facts.declaration is None and facts.phase == "declaration"
        assert original.decision_checkpoints == active.document.decision_checkpoints
        assert not facts.plays and archive.snapshot().manifest == manifest
        for kind, raw in downloads.items():
            status, _, current = browser.request("GET", route + "/" + kind + ".json")
            assert status == 200 and current == raw


def test_short_record_remains_unknown_after_restart(tmp_path):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        browser = Browser(server)
        page = follow(browser, browser.submit(before_declaration(browser),
                      game_type="grand", bid_value="19"))
        assert text("en", "bidding.unknown") in page
        path = server.app_context.managed_stateful.active_session.path
    short = cold_auction(path, "session")
    assert short[0] == [] and short[2:] == [None, None, None, 19]


def test_match_effort_survives_pass_correction_and_replacement_is_rejected(tmp_path):
    with (closing(localized_server.__wrapped__(tmp_path)) as servers,
          patch("skatmind.app_web.match_live_advice.evaluate_live_position") as evaluate):
        server = next(servers)
        browser = Browser(server)
        page = create_empty(browser, "en")
        page = follow(browser, browser.submit(operation_form(page, "start_game")))
        page = start_live(browser, page, MATCH_LIVE_ROUTES, "quick")
        page = submit(browser, page, MATCH_LIVE_ROUTES[1], analysis_effort="more_time")
        for index in range(3):
            page = follow(browser, browser.submit(bid_form(page, index), choice="pass"))
        page = follow(browser, browser.submit(bid_form(page, 2), choice="take"))
        page = start_live(browser, page, MATCH_LIVE_ROUTES, "more_time")
        active = server.app_context.managed_stateful.active_match
        path = active.path
        before = path.read_bytes()
        other = path.with_suffix(".replacement")
        other.write_bytes(before)
        os.replace(other, path)
        for html in (page, browser.page("/matches/position/1")):
            assert browser.submit(bid_form(html, 2), choice="pass")[0] == 409
        assert path.read_bytes() == before
        evaluate.assert_not_called()
