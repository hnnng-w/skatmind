"""Current-turn Match advice: native saved inputs, exact perspective and delivery."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from test_frontend_language_switching import localized_server
from test_historical_game import build_historical_input
from test_match_game_navigation_web import create_empty
from test_match_recording_recovery_web import declarer_choice, entry_action, follow, operation_form
from test_match_workspace_contracts import _definition, _observed_game, _set_game
from test_session_live_advice_web import tile_labels
from test_session_recorded_review_web import Browser, Forms
from test_session_transitions import _play_commands_from_data, _retrospective_before_play

import skatmind.api.v1.session as api
import skatmind.capture_web.context as capture
from skatmind.app_web import match_live_advice as live
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
from skatmind.app_web.session_form_translation import build_session_position_options_from_form_v1
from skatmind.app_web.stateful_localization import text
from skatmind.game_declaration import GameDeclaration
from skatmind.live_whole_game import live_rollout_view
from skatmind.match_live_position import current_match_position
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

__all__ = ["localized_server"]

START, EFFORT, STOP = live.MATCH_LIVE_ROUTES
HAND = "CA C10 CK CQ CJ C9 C8 C7 SA S10".split()
PREFIX = "CA SK HJ H9 C10 HA SQ".split()


def submit(browser, page, path, **changes):
    return follow(browser, browser.submit(Forms(page).find(path), **changes))


def operation(browser, page, name, **changes):
    return follow(browser, browser.submit(operation_form(page, name), **changes))


def setup_game(browser, *, declaration=True, hand=True):
    create_empty(browser, "en")
    page = operation(browser, browser.page("/matches/position/2"), "start_game")
    if hand:
        page = operation(browser, page, "set_perspective_hand", cards=HAND)
    if declaration:
        page = declare(browser, page)
    return page


def declare(browser, page):
    return operation(browser, page, "set_declaration", declarer_player_id=declarer_choice(
        page, "Boris"), game_type="grand", hand_game="true", bid_value="24")


def seven_play_match(browser):
    page = setup_game(browser)
    batch = next(
        f for f in Forms(page).forms if f["action"] == "/matches/api/v1/operation"
        and f["values"].get("operation") == "append_plays")
    return follow(browser, browser.submit(batch, cards=" ".join(PREFIX)))


def test_next_unrecorded_rotated_view_matches_session_and_native_tiles(
        localized_server, monkeypatch):
    browser = Browser(localized_server)
    page = seven_play_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    assert active.selected_position == 2 and active.live.effort is None
    page = submit(browser, page, START)
    assert not active.live.outcome and 'class="live-frequency"' not in page
    response = browser.submit(Forms(page).find("/matches/cards"), cards="H8")
    assert response[1]["location"] == "/matches/position/2#live-recommendation"
    page = follow(browser, response)
    workspace = load_match_workspace_file_v1(active.path).document.workspace
    game = workspace.slots[1].observed_game
    assert [p.card for p in game.plays] == [*PREFIX, "H8"]
    request, legal = current_match_position(workspace, 2, samples=25)
    doc = request.to_dict()["document"]
    assert set(doc["hand"]) == set(HAND) - {"CA", "C10"} and legal == ("SA", "S10")
    assert doc["trick_leader"] == "left" and doc["player_position"] == "forehand"
    assert [p.seat for p in game.players] == ["forehand", "middlehand", "rearhand"]
    assert game.players[0].player_id == game.perspective_player_id
    assert doc["current_trick"] == ["SQ", "H8"] and "actual_card_played" not in doc
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    session = _retrospective_before_play(data, local_player_id="player-a")
    state = _play_commands_from_data(session, {"tricks": [*data["tricks"][:2],
        {"plays": data["tricks"][2]["plays"][:2]}]})
    options = build_session_position_options_from_form_v1({
        "settings_mode": "ordinary", "analysis_effort": "quick",
        "random_seed": "0", "opponent_strategy": "basic"})
    equivalent = api.export_session_position_request(state, options).value.request
    assert live_rollout_view(doc) == live_rollout_view(equivalent.to_dict()["document"])
    comparison = live.evaluate_live_position(equivalent, effort="quick", cancelled=lambda: False)
    assert active.live.outcome.candidates == comparison.candidates
    tiles = tile_labels(page, "live-recommendation")
    assert tuple(tiles) == ("SA", "S10")
    assert all("10/25" in tile and "40%" in tile for tile in tiles.values())
    assert "-24.16" in tiles["SA"] and "-25.36" in tiles["S10"]
    assert active.pending_evidence is None and not active.capture.report_store.list()
    page = submit(browser, page, "/matches/cards", cards="SA")
    assert len(active.live.outcome.ranked_cards) == 7
    monkeypatch.setattr(live, "evaluate_live_position",
                        lambda *a, **kw: pytest.fail("Opponent or forced turn simulated"))
    for card in ("CK", "SJ", "H7", "S9"):
        page = submit(browser, page, "/matches/cards", cards=card)
    response = browser.submit(Forms(page).find("/matches/cards"), cards="DA")
    assert response[1]["location"] == "/matches/position/2#forced-card-guidance"
    page = follow(browser, response)
    assert tuple(tile_labels(page, "forced-card-guidance")) == ("S10",)
    assert "live-frequency" not in page
    assert 'href="/matches/review/2"' in page
    review = browser.page("/matches/review/2")
    selector = Forms(review).find("/matches/review/2")
    assert selector["values"]["position"] == "2"
    response = browser.request("GET", selector["action"] + "?position=1")
    review = follow(browser, response)
    assert 'href="/matches/position/1#match-recording"' in review
    recording = browser.page("/matches/position/1")
    assert 'href="/matches/position/2#match-recording"' in recording
    recording = browser.page("/matches/position/2")
    assert active.live.effort is None and active.live.outcome is None
    assert Forms(recording).find(START) and 'id="forced-card-guidance"' not in recording


@pytest.mark.parametrize("declaration_last", (True, False))
def test_combined_native_readiness_noops_effort_correction_and_reload(
        localized_server, monkeypatch, declaration_last):
    browser = Browser(localized_server)
    page = setup_game(browser, declaration=not declaration_last, hand=declaration_last)
    active = localized_server.app_context.managed_stateful.active_match
    calls = []
    real = live.evaluate_live_position

    def counted(request, **kwargs):
        saved = load_match_workspace_file_v1(active.path).document.workspace
        assert saved == active.workspace
        calls.append((saved.revision, kwargs["effort"]))
        return real(request, **kwargs)

    monkeypatch.setattr(live, "evaluate_live_position", counted)
    page = submit(browser, page, START)
    assert not calls
    page = (declare(browser, page) if declaration_last else
            operation(browser, page, "set_perspective_hand", cards=HAND, game_type="null"))
    assert active.live.outcome.status == "complete" and len(calls) == 1
    page = declare(browser, page)  # Unchanged accepted declaration.
    page = submit(browser, browser.page("/matches/position/2"), "/actions/profile/language",
                  language="de")
    assert 'id="live-recommendation"' in page and len(calls) == 1
    page = submit(browser, page, EFFORT, analysis_effort="standard")
    assert active.live.outcome.completed_common_worlds == 100
    page = submit(browser, page, "/matches/cards", cards="CA")
    assert active.live.outcome is None and len(calls) == 2
    page = follow(browser, browser.submit(entry_action(page, 1, rewind=True)))
    assert len(calls) == 2
    page = submit(browser, page, "/matches/recovery/apply", confirm_apply="on")
    assert active.live.outcome.completed_common_worlds == 100 and len(calls) == 3
    page = submit(browser, page, "/matches/cards", cards="CA")
    page = operation(browser, page, "truncate_plays", target_play_count="0")
    assert len(calls) == 4 and 'id="live-recommendation"' in page
    page = submit(browser, page, "/matches/api/v1/reload")
    assert active.live.effort is None and not active.live.outcome
    page = submit(browser, page, START)
    assert len(calls) == 5 and active.live.effort == "standard"
    old = Forms(page).find(STOP)
    browser.page("/matches/position/1")
    page = browser.page("/matches/position/2")
    assert active.live.effort is None and not active.live.outcome
    assert browser.submit(old)[0] == 409 and Forms(page).find(START)


@pytest.mark.parametrize("ending", ("clear_position", "mark_passed_deal"))
def test_generic_declaration_metadata_and_replaced_game(localized_server, monkeypatch, ending):
    browser = Browser(localized_server)
    page = submit(browser, setup_game(browser, declaration=False), START)
    active = localized_server.app_context.managed_stateful.active_match
    # The compatibility operation carries only accepted fields, no combined-form draft.
    page = follow(browser, browser.request("POST", "/matches/api/v1/operation", {
        "managed_handle": active.handle, "match_position": "2", "operation": "set_declaration",
        "expected_revision": str(active.workspace.revision),
        "declarer_player_id": declarer_choice(page, "Boris"), "game_type": "grand",
        "hand_game": "true", "bid_value": "24"}))
    assert active.live.outcome.status == "complete"
    monkeypatch.setattr(live, "evaluate_live_position",
                        lambda *a, **kw: pytest.fail("Non-play change simulated"))
    page = operation(browser, page, "update_match_metadata", title="Changed title")
    assert active.workspace.match_definition.title == "Changed title"
    assert active.live.effort == "quick" and 'id="live-recommendation"' not in page
    page = operation(browser, page, ending, **{
        "confirm_replace" if ending == "mark_passed_deal" else "confirm_clear": "on"})
    assert active.workspace.slots[1].observed_game is None and active.live.effort is None
    assert START not in page and STOP not in page


def test_failed_save_and_failed_advice_keep_real_source(localized_server, monkeypatch):
    browser = Browser(localized_server)
    page = submit(browser, seven_play_match(browser), START)
    active = localized_server.app_context.managed_stateful.active_match
    original = active.workspace
    saved = []
    def fail(*args, **kwargs):
        saved.append(load_match_workspace_file_v1(active.path).document.workspace)
        raise ValueError("Injected evaluator failure")
    monkeypatch.setattr(live, "evaluate_live_position", fail)
    play = Forms(page).find("/matches/cards")
    with monkeypatch.context() as patch:
        def failed_save(*args, **kwargs):
            raise OSError("Injected save failure")
        patch.setattr(capture, "save_match_workspace_file_v1", failed_save)
        assert browser.submit(play, cards="H8")[0] == 409
        assert not saved and active.workspace is original
    page = follow(browser, browser.submit(play, cards="H8"))
    assert saved == [active.workspace] and saved[0].revision == original.revision + 1
    assert text("en", "analysis.live.unavailable") in page and Forms(page).find("/matches/cards")
    assert active.live.outcome is None and not active.capture.report_store.list()


@pytest.mark.parametrize("change", ("stop", "effort", "reopen"))
def test_superseded_failure_cannot_replace_newer_delivery(localized_server, monkeypatch, change):
    browser = Browser(localized_server)
    page = submit(browser, seven_play_match(browser), START)
    active = localized_server.app_context.managed_stateful.active_match
    entered, release = Event(), Event()
    cancellations = []
    real = live.evaluate_live_position
    def blocked(request, *, cancelled, **kwargs):
        if entered.is_set():
            return real(request, cancelled=cancelled, **kwargs)
        entered.set()
        assert release.wait(15)
        cancellations.append(cancelled())
        raise RuntimeError("Superseded failure")
    monkeypatch.setattr(live, "evaluate_live_position", blocked)
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(browser.submit, Forms(page).find("/matches/cards"), cards="H8")
        try:
            assert entered.wait(15)
            app = localized_server.app_context
            for lock in (active.capture.lock, app.lock, app.managed_stateful.match_lifecycle_lock):
                assert lock.acquire(timeout=1)
                lock.release()
            page = browser.page("/matches/current")
            if change == "effort":
                page = submit(browser, page, EFFORT, analysis_effort="standard")
                assert active.live.outcome.completed_common_worlds == 100
            elif change == "stop":
                page = submit(browser, page, STOP)
                status, _, body = browser.submit(Forms(page).find("/matches/cards"), cards="SQ")
                assert status == 400 and 'class="error-summary"' in body.decode()
            else:
                page = submit(browser, browser.page("/matches"), "/matches/open")
                assert app.managed_stateful.active_match is not active
            outcome = active.live.outcome
            feedback = localized_server.app_context.form_feedback.current(
                "matches", active_identity=active)
        finally:
            release.set()
        assert pending.result()[0] == 409
    assert (feedback is not None) == (change == "stop")
    assert cancellations == [True]
    assert feedback is localized_server.app_context.form_feedback.current(
        "matches", active_identity=active)
    assert active.live.outcome is outcome and not active.live.unavailable


@pytest.mark.parametrize("restore", (False, True))
def test_final_delivery_checks_exact_file_and_epoch(localized_server, monkeypatch, restore):
    from skatmind.match_capture_application import append_match_capture_plays_v1
    from skatmind.match_capture_application_contracts import MatchCaptureCardEntryV1
    from skatmind.match_workspace_persistence import (
        build_match_workspace_persistence_document_v1,
        save_match_workspace_file_v1,
    )

    browser = Browser(localized_server)
    page = seven_play_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    before = load_match_workspace_file_v1(active.path).document
    page = submit(browser, page, START)
    page = submit(browser, page, "/matches/cards", cards="H8")
    admitted = load_match_workspace_file_v1(active.path).document
    assert 'id="live-recommendation"' in page
    if not restore:
        alternate = append_match_capture_plays_v1(before.workspace, match_position=2,
            expected_revision=before.workspace.revision,
            entries=(MatchCaptureCardEntryV1(card="D8", decision_timecode=None),))
        other = active.path.with_name("independent.json")
        assert save_match_workspace_file_v1(other,
            build_match_workspace_persistence_document_v1(alternate.workspace_change.workspace),
            expected_content_fingerprint=None).status == "saved"
        stat = active.path.stat()
        assert other.stat().st_size == stat.st_size
        os.utime(other, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    original = Handler._send_bytes
    def change_before_send(handler, status, content, **kwargs):
        if b'id="live-recommendation"' in content:
            if restore:
                for old, new in ((admitted, before), (before, admitted)):
                    assert save_match_workspace_file_v1(active.path, new,
                        expected_content_fingerprint=old.content_fingerprint).status == "saved"
            else:
                # Same size and mtime; independent replacement, no notification.
                other.replace(active.path)
        return original(handler, status, content, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Handler, "_send_bytes", change_before_send)
        status, _, content = browser.request("GET", "/matches/current")
        assert status == 409 and b'id="live-recommendation"' not in content
    page = browser.page("/matches/current")
    assert active.live.effort is None and Forms(page).find(START)


@pytest.mark.parametrize("own,hand,ouvert", ((False, True, False), (False, False, False),
    (False, True, True), (True, True, True), (True, False, False)))
def test_skat_ouvert_and_visible_matadors_only(own, hand, ouvert):
    definition = _definition(perspective_player_id="player-a")
    workspace = create_match_workspace_v1(definition)
    game = _observed_game(definition, match_position=3, perspective_initial_hand=HAND,
        original_skat=("D8", "D7"), discarded_cards=None if hand else ("D8", "D7"),
        declarer_player_id="player-a" if own else "player-c",
        declaration=GameDeclaration(game_type="grand", bid_value=24, matadors=3,
                                    hand_game=hand, ouvert=ouvert))
    prepared = current_match_position(_set_game(workspace, game), 3, samples=25)
    if ouvert and not own:
        assert prepared is None
        return
    doc = prepared[0].document
    assert set(doc["skat"]) == ({"D7", "D8"} if own and not hand else set())
    assert doc["game_declaration"]["matadors"] != 3
    assert doc["declarer_player"] == ("me" if own else "right")
    assert not {"opponent_statistics", "actual_card_played"} & doc.keys()
    assert "public_declarer_cards" not in doc
