import http.client
import json
import re
from html import escape
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from test_compact_card_entry_web import choice_codes, create_live, selected
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_game import build_historical_input
from test_language_switch_context import switch
from test_local_time_entry_web import local_form
from test_match_recording_recovery_web import follow
from test_session_direct_card_start import fresh
from test_session_recorded_review_web import Browser, Forms, review_first
from test_session_transitions import _deal_card
from test_task_first_language_preservation import enhanced_switch, envelope

import skatmind.api.v1.session as api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.card_entry_http as card_http
import skatmind.app_web.session_card_entry as entry
from skatmind.app_web.local_time_forms import LOCAL_TIME_FIELDS
from skatmind.app_web.time_zone_provider import TimeZoneUnavailable
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck
from skatmind.historical_game import build_historical_game_record
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def create(browser, mode="live", seat="forehand"):
    form = Forms(browser.page("/sessions")).find("/sessions/create")
    page = follow(browser, browser.submit(form, game_name="Direct startup",
        forehand_name="Alex", middlehand_name="Boris", rearhand_name="Clara",
        capture_mode=mode, perspective_seat=seat, setup_action="update"))
    return follow(browser, browser.submit(Forms(page).find("/sessions/create"),
                                         setup_action="create"))


@pytest.mark.parametrize("mode,seat", (("live", "forehand"), ("live", "middlehand"),
    ("live", "rearhand"), ("retrospective", ""), ("retrospective", "rearhand")))
def test_real_creation_and_first_form_preserve_actual_player_and_phase(
    localized_server, mode, seat,
):
    browser = Browser(localized_server)
    with patch.object(session_files, "save_session_file",
                      wraps=session_files.save_session_file) as save:
        page = create(browser, mode, seat)
        assert save.call_count == 1  # The unchanged real revision-zero creation save.
        active = localized_server.app_context.managed_stateful.active_session
        assert active.state.revision == 0 and active.state.command_log == ()
        source, before = active.document, active.path.read_bytes()
        form = Forms(page).find("/sessions/cards")
        assert set(form["values"]) == {
            "managed_handle", "card_selection", "_frontend_form_instance"}
        assert text("en", "task.session.phase.setup") in page
        assert text("en", "task.session.metadata_title") in page
        assert len([f for f in Forms(page).forms
                    if f["values"].get("time_form") == "session-metadata"]) == 1
        metadata = local_form(page, "session-metadata")
        assert metadata["values"]["local_date"] == metadata["values"]["local_time"] == ""
        browser.page()
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/reload")))
        assert active.path.read_bytes() == before and active.document == source
        page = browser.page()
        assert save.call_count == 1
        response = browser.submit(Forms(page).find("/sessions/cards"), cards=get_full_deck()[:10])
        page = follow(browser, response)
        assert save.call_count == 2
    facts = replay_session_state_v1(active.state)
    actor = active.state.players[0].player_id if mode == "retrospective" else facts.local_player_id
    assert facts.initial_hand_for(actor) == tuple(get_full_deck()[:10])
    assert facts.game_id == facts.session_id and facts.played_at is None
    assert active.state.revision == 11
    if mode == "live":
        assert facts.phase == "declaration"
        assert next(p.seat for p in facts.players if p.player_id == actor) == seat
    else:
        assert facts.phase == "deal"
        assert entry.project_session_card_task(active.state).player_id == facts.players[1].player_id


@pytest.mark.parametrize("cards", ([], ["CA", "CA", "SJ"]))
def test_first_rejection_and_native_language_then_save_publish_only_once(localized_server, cards):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    with patch.object(session_files, "save_session_file",
                      wraps=session_files.save_session_file) as save:
        status, _, body = browser.submit(form, cards=cards)
        assert status == 400
        page = switch(browser, body.decode(), "de")
        assert selected(page) == (["CA", "SJ"] if cards else [])
        assert save.call_count == 0 and active.path.read_bytes() == before
        assert active.state.revision == 0 and replay_session_state_v1(active.state).game_id is None
        follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=["SJ", "CA"]))
        assert save.call_count == 1 and active.state.revision == 3


@pytest.mark.parametrize("cards", ([], ["SJ", "CA"]))
def test_enhanced_language_preserves_exact_unsent_initial_selection(localized_server, cards):
    browser = Browser(localized_server)
    create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    page = browser.page()
    raw = envelope(page, "/sessions/cards", {"cards": cards})
    page = follow(browser, enhanced_switch(browser, page, raw))
    # Restoration is by Card identity; returned DOM order follows printed suits.
    assert selected(page) == (["CA", "SJ"] if cards else [])
    assert active.path.read_bytes() == before and active.state.revision == 0
    assert entry.project_session_card_task(active.state).kind == "record_dealt_card"


@pytest.mark.parametrize("target", (0, 1))
def test_real_undo_reopen_restart_uses_exact_prefix(localized_server, target):
    browser = Browser(localized_server)
    form = create_live(browser)
    page = follow(browser, browser.submit(form, cards=get_full_deck()[:10]))
    active = localized_server.app_context.managed_stateful.active_session
    first = active.document
    page = follow(browser, browser.submit(
        Forms(page).find("/sessions/undo"), target_revision=target))
    assert active.state.revision == target and active.state.phase == "setup"
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.path.read_bytes() == before
    follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=get_full_deck()[:10]))
    assert active.document == first


def test_imported_partial_deal_is_read_only_until_first_successful_card_save(localized_server):
    browser = Browser(localized_server)
    app = localized_server.app_context
    # Fixture is an old accepted direct-Card source with no identity; import remains real.
    old = _deal_card(fresh(), destination="player_hand", player_id="player-a", card="SJ")
    from skatmind.app_web.session_frontend import import_guided_session_v1
    active = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="a" * 64,
        document=api.build_session_persistence_document(old).value.to_dict())
    app.managed_stateful.active_session = active
    before = active.path.read_bytes()
    page = browser.page()
    form = Forms(page).find("/sessions/cards")
    assert active.state == old and active.path.read_bytes() == before
    assert "SJ" not in choice_codes(page, mode="set")
    status, _, body = browser.submit(form, cards=["CA", "SJ"])
    assert status == 400 and active.path.read_bytes() == before and active.state == old
    assert re.search(r'<input[^>]*value="CA"[^>]*checked', body.decode())
    follow(browser, browser.submit(Forms(body.decode()).find("/sessions/cards"), cards=["CA"]))
    assert active.state.revision == 3 and active.state.command_log[:1] == old.command_log
    assert active.state.command_log[1].command == api.SetSessionGameMetadataCommandV1(
        expected_revision=1, game_id=old.session_id, played_at=None)


@pytest.mark.parametrize("when", ("before", "after"))
def test_optional_time_append_correction_and_preference_preserve_card_prefix(
    localized_server, when,
):
    browser = Browser(localized_server)
    page = create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    if when == "before":
        page = follow(browser, browser.submit(local_form(page, "session-metadata"),
            local_date="2026-01-15", local_time="19:30", game_id="Custom identity"))
    page = follow(browser, browser.submit(
        Forms(page).find("/sessions/cards"), cards=get_full_deck()[:10]))
    assert active.state.revision == 11
    prefix = active.state.command_log
    target = 1 if when == "before" else 12
    if when == "after":
        page = follow(browser, browser.submit(local_form(page, "session-metadata"),
            local_date="2026-01-15", local_time="19:30"))
        assert active.state.command_log[:11] == prefix
        assert active.state.command_log[-1].command.game_id is None
    assert replay_session_state_v1(active.state).played_at == "2026-01-15T19:30:00+01:00"
    records = active.state.command_log
    page = follow(browser, browser.submit(local_form(page, "session-metadata-correction", target),
        time_mode="replace", local_date="2026-07-15", local_time="19:30"))
    assert active.state.revision == len(records)
    assert active.state.command_log[:target - 1] == records[:target - 1]
    assert active.state.command_log[target:] == records[target:]
    assert replay_session_state_v1(active.state).played_at == "2026-07-15T19:30:00+02:00"
    before = active.path.read_bytes()
    settings = Forms(browser.page("/settings")).find("/actions/profile/time-zone")
    follow(browser, browser.submit(settings, time_zone="UTC"))
    assert active.path.read_bytes() == before
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert localized_server.app_context.managed_stateful.active_session.path.read_bytes() == before


def test_timestamp_only_legacy_prefix_is_never_resent_or_silently_deleted(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    form = local_form(page, "session-metadata")
    legacy = {k: v for k, v in form["values"].items()
              if k not in {*LOCAL_TIME_FIELDS, "profile_generation", "_frontend_form_instance"}}
    original = "2026-01-15t19:30:00.123456789-00:00"
    page = follow(browser, browser.request("POST", form["action"],
        {**legacy, "game_id": "", "played_at": original}))
    active = localized_server.app_context.managed_stateful.active_session
    prefix = active.state.command_log
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"]))
    assert active.state.revision == 3 and active.state.command_log[:1] == prefix
    assert active.state.command_log[1].command.played_at is None
    assert replay_session_state_v1(active.state).played_at == original
    before = active.path.read_bytes()
    # A timestamp-only Command cannot be replaced by an empty metadata Command.
    response = browser.submit(
        local_form(page, "session-metadata-correction", 1), time_mode="remove")
    assert response[0] == 400 and active.path.read_bytes() == before
    assert active.state.command_log[:1] == prefix


def test_optional_provider_outage_does_not_block_card_only_action(localized_server):
    browser = Browser(localized_server)
    create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    with (
        patch("skatmind.app_web.local_time_rendering.time_zone_inventory",
              side_effect=TimeZoneUnavailable("database")),
        patch("skatmind.app_web.local_time_forms.resolve_local_form_timestamp",
              side_effect=AssertionError("Card entry must not resolve time")),
    ):
        page = browser.page()
        assert escape(text("en", "validation.local_time.database")) in page
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"]))
    assert active.state.revision == 2 and replay_session_state_v1(active.state).played_at is None


def test_foreign_first_form_and_body_limit_preserve_both_sources(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    old = localized_server.app_context.managed_stateful.active_session
    before = old.path.read_bytes()
    create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    current = active.path.read_bytes()
    assert browser.submit(form, cards=["CA"])[0] == 409
    form = Forms(browser.page()).find("/sessions/cards")
    with patch("skatmind.app_web.card_entry_http.prepare_session_card_candidate",
               side_effect=AssertionError("Oversize input must precede preparation")):
        assert browser.submit(form, cards="C" * 8193)[0] == 413
    assert old.path.read_bytes() == before and active.path.read_bytes() == current
    assert active.state.revision == old.state.revision == 0


@pytest.mark.parametrize("length,status", ((8192, 400), (8193, 413)))
def test_card_route_enforces_declared_body_bound_before_preparation(
    localized_server, length, status,
):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    body = urlencode({**form["values"], "cards": ""}).encode("ascii")
    body += b"C" * (length - len(body))  # At the bound, ordinary Card validation rejects.
    connection = http.client.HTTPConnection("127.0.0.1", localized_server.port, timeout=30)
    try:
        with (
            patch.object(card_http, "prepare_session_card_candidate",
                         wraps=card_http.prepare_session_card_candidate) as prepare,
            patch.object(session_files, "save_session_file",
                         wraps=session_files.save_session_file) as save,
        ):
            connection.request("POST", form["action"], body=body, headers={
                "Cookie": browser.cookie, "Origin": localized_server.origin,
                "Content-Type": "application/x-www-form-urlencoded"})
            response = connection.getresponse()
            response.read()
            assert response.status == status
            assert prepare.call_count == (1 if length == 8192 else 0)
            assert save.call_count == 0
    finally:
        connection.close()
    assert active.state.revision == 0 and active.path.read_bytes() == before


def test_genuine_review_result_survives_later_card_checkpoint_and_save_faults(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true")
    browser.command("record_play", card="CA")
    review_first(browser)
    active = localized_server.app_context.managed_stateful.active_session
    result, label = active.execution, active.recorded_review_source
    checkpoint, document = active.decision_checkpoints, active.document
    before = active.path.read_bytes()
    for target, error in (("skatmind.app_web.session_card_entry._collect_current_checkpoint",
                           ValueError("Injected checkpoint failure")),
                          ("skatmind.app_web.session_frontend.session_files.save_session_file",
                           OSError("Injected save failure"))):
        form = Forms(browser.page()).find("/sessions/play")
        with patch(target, side_effect=error):
            assert browser.submit(form, cards="H7")[0] in {400, 409}
        assert active.document is document and active.path.read_bytes() == before
        assert active.execution is result and active.recorded_review_source is label
        assert active.decision_checkpoints == checkpoint
        assert browser.request("GET", "/sessions/downloads/result.json")[2] == (
            result.result_json_bytes)


def test_retrospective_direct_deal_reaches_legal_historical_export(localized_server):
    browser = Browser(localized_server)
    page = create(browser, "retrospective", "")
    active = localized_server.app_context.managed_stateful.active_session
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    # Legal fixture Cards choose inputs; every initial batch and later save is real.
    for player in data["players"]:
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                             cards=player["initial_hand"]))
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=data["skat"]))
    assert active.state.revision == 33 and active.state.phase == "declaration"
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    for trick in data["tricks"]:
        for play in trick["plays"]:
            browser.command("record_play", card=play["card"])
    assert api.export_session_historical_request(active.state).value.status == "unavailable"
    browser.command("set_game_end")
    exported = api.export_session_historical_request(active.state).value
    assert exported.status == "available"
    document = exported.request.to_dict()["document"]["historical_game_input"]
    record = build_historical_game_record(document)
    assert record.game_id == active.state.session_id
    assert document.get("played_at") is None
    saved = json.loads(browser.request("GET", "/sessions/downloads/session.json")[2])
    assert api.resume_session_document(saved).value.document == active.document
