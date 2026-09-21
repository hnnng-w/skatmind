import json
import re
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_game import build_historical_input
from test_local_time_entry_web import local_form
from test_match_recording_recovery_web import entry_action, follow, operation_form, start_match
from test_session_recorded_review_web import Browser, Forms, review_first

import skatmind.api.v1.session as api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.execution as execution
import skatmind.app_web.session_card_entry as entry
import skatmind.session_persistence as persistence
from skatmind.app_web.card_entry_http import dispatch_card_entry
from skatmind.app_web.compact_card_rendering import card_display_groups
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.capture_web.context import MatchCaptureWebContextV1
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def create_live(browser):
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/create"),
        game_name="Synthetic recorded Game", capture_mode="live", perspective_seat="forehand",
        forehand_name="Alexandra Long-Synthetic-Player-Name", middlehand_name="Boris",
        rearhand_name="Clara", setup_action="update"))
    page = follow(browser, browser.submit(
        Forms(page).find("/sessions/create"), setup_action="create"))
    active = browser.server.app_context.managed_stateful.active_session
    assert active.state.revision == 0 and active.state.command_log == ()
    assert active.state.phase == "setup"
    return Forms(page).find("/sessions/cards")


def selected(page, route="/sessions/cards"):
    return Forms(page).find(route)["values"].get("cards", [])


def choice_codes(page, *, mode="play"):
    block = re.search(r'<fieldset class="compact-cards" data-card-mode="' + mode
                      + r'".*?</fieldset>', page, re.S)[0]
    return re.findall(r'<input[^>]+name="cards" value="([^"]+)"', block)


def test_real_direct_start_eleven_commands_one_save_reopen_then_all_plays_and_review(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    hand = data["players"][0]["initial_hand"]
    original_state = active.state
    saves, executes, replacements = [], [], []
    real_save, real_execute = session_files.save_session_file, execution.execute
    real_replace = persistence.os.replace
    def save(*args, **kwargs):
        saves.append(kwargs["expected_content_fingerprint"])
        return real_save(*args, **kwargs)
    def execute(*args, **kwargs):
        executes.append(args)
        return real_execute(*args, **kwargs)
    def replace_file(*args, **kwargs):
        replacements.append(args)
        return real_replace(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    monkeypatch.setattr(execution, "execute", execute)
    monkeypatch.setattr(persistence.os, "replace", replace_file)
    original_fingerprint = active.document.content_fingerprint
    page = follow(browser, browser.submit(form, cards=list(reversed(hand))))
    assert saves == [original_fingerprint] and not executes
    assert len(replacements) == 1
    records = active.state.command_log[original_state.revision:]
    assert len(records) == 11
    assert records[0].command == api.SetSessionGameMetadataCommandV1(
        expected_revision=0, game_id=active.state.session_id, played_at=None)
    assert all(record.command.kind == "record_dealt_card" for record in records[1:])
    assert [record.command.card for record in records[1:]] == [
        c for c in get_full_deck() if c in hand]
    assert [record.revision for record in records] == list(range(1, 12))
    assert [record.command.expected_revision for record in records] == list(range(11))
    assert replay_session_state_v1(active.state).played_at is None
    assert active.state.phase == "declaration"
    assert active.state.revision == original_state.revision + 11
    saved = active.document
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.document == saved and replay_session_state_v1(active.state).initial_hand_for(
        active.state.local_player_id) == tuple(c for c in get_full_deck() if c in hand)
    assert browser.submit(form, cards=hand)[0] == 409
    # Explicit past metadata describes the Game; it never selects the recording path.
    page = browser.page()
    follow(browser, browser.submit(local_form(page, "session-metadata"),
        local_date="2026-01-15", local_time="19:30"))
    assert active.state.capture_mode == "live"
    assert replay_session_state_v1(active.state).played_at == "2026-01-15T19:30:00+01:00"
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    frozen = active.decision_checkpoints[0].request.to_dict()["document"]
    plays = [play for trick in data["tricks"] for play in trick["plays"]]
    observed = []
    for play in plays:
        page = browser.page()
        recording = page.split('id="session-recording"', 1)[1].split('</fieldset>', 1)[0]
        assert "Completed Trick" not in recording
        assert set(observed).isdisjoint(choice_codes(page))
        assert play["card"] in choice_codes(page)
        form = Forms(page).find("/sessions/play")
        assert "cards" not in form["values"]
        count, revision = len(saves), active.state.revision
        response = browser.submit(form, cards=play["card"])
        assert response[1]["location"] == "/sessions/current#session-recording"
        follow(browser, response)
        assert len(saves) == count + 1 and active.state.revision == revision + 1
        observed.append(play["card"])
    assert not executes and len(active.decision_checkpoints) == 10
    facts = replay_session_state_v1(active.state)
    assert len(facts.initial_known_hands) == 1 and facts.played_card_count == 30
    assert active.state.phase == "play"
    assert Forms(browser.page()).find("/sessions/review-decision")
    browser.command("set_game_end")
    assert active.state.phase == "ended" and active.state.capture_mode == "live"
    assert all(r.command.kind != "promote_to_retrospective" for r in active.state.command_log)
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    save_count = len(saves)
    page, _ = review_first(browser)
    assert len(executes) == 1 and len(saves) == save_count
    assert active.path.read_bytes() == before and "10 of 10" in page
    request = json.loads(browser.request("GET", "/sessions/downloads/request.json")[2])
    assert request == {**frozen, "analysis_mode": "post_game_review",
                       "actual_card_played": plays[0]["card"]}
    assert text("en", "session.knowledge.accepted_mode",
                mode=text("en", "session.knowledge.perspective")) in page
    assert '<h2>' + text("en", "task.session.phase.ended") + '</h2>' in page
    assert text("en", "task.session.next.complete") not in page
    assert text("en", "task.session.next.promote_to_retrospective") not in page
    assert text("en", "task.session.readiness.historical.capture_mode") in page
    assert active.state.capture_mode == "live" and active.state.phase == "ended"


def test_partial_reopen_append_and_real_invalid_members_retain_selection(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=get_full_deck()[:4]))
    active = localized_server.app_context.managed_stateful.active_session
    prefix = active.state.command_log
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    form = Forms(browser.page()).find("/sessions/cards")
    assert not set(get_full_deck()[:4]).intersection(choice_codes(browser.page(), mode="set"))
    before = active.path.read_bytes()
    for cards, reason in ((["C9", "D7", "invalid-last"], "invalid"),
                          (["C9", "C9"], "duplicate"),
                          (get_full_deck()[4:11], "capacity"),
                          (["C9", "CA"], "unavailable"), ([], "empty")):
        status, _, body = browser.submit(form, cards=cards)
        assert status == 400
        page = body.decode()
        if reason == "unavailable":
            assert 'class="session-card-evidence" href="#session-hand-1"' in page
            assert text("en", "task.card.name", suit="Clubs", rank="Ace") in page
            assert "already assigned" in page
        else:
            assert text("en", f"validation.card_entry.{reason}") in page
        assert active.path.read_bytes() == before and active.state.command_log == prefix
        if "C9" in cards:
            assert re.search(r'<input[^>]*value="C9"[^>]*checked', page)
        if "CA" in cards:
            assert text("en", "compact.rejected", cards="CA") in page
            assert "CA" not in choice_codes(page, mode="set")
    page = follow(browser, browser.submit(form, cards=get_full_deck()[4:10]))
    assert active.state.command_log[:len(prefix)] == prefix and active.state.phase == "declaration"
    assert '/sessions/cards' not in page


def test_real_grouped_skat_and_discards_and_no_analysis(localized_server, monkeypatch):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="false")
    active = localized_server.app_context.managed_stateful.active_session
    def forbidden(*args, **kwargs):
        raise AssertionError("Recording must not execute")
    monkeypatch.setattr(execution, "execute", forbidden)
    for cards in (["D7", "H7"], ["D7", "CA"]):
        original = active.state.revision
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/cards"), cards=cards))
        assert active.state.revision == original + 2
    facts = replay_session_state_v1(active.state)
    assert facts.phase == "play" and len(active.decision_checkpoints) == 1
    assert set(facts.remaining_hand_for(active.state.local_player_id)) == (
        set(get_full_deck()[:10]) | {"H7"}) - {"CA"}


@pytest.mark.parametrize("fault", ("replace", "checkpoint"))
def test_injected_prepublication_failure_preserves_exact_state_and_bytes(
    localized_server, monkeypatch, fault,
):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before, document, generation = active.path.read_bytes(), active.document, active.generation
    sentinel = object()
    active.execution_attempt = sentinel
    if fault == "replace":
        def fail(*args):
            raise OSError("Injected replacement failure")
        monkeypatch.setattr(persistence.os, "replace", fail)
    else:
        real = entry._collect_current_checkpoint
        def fail(**kwargs):
            if kwargs["state"].revision == document.state.revision + 2:
                raise ValueError("Injected later Checkpoint failure")
            return real(**kwargs)
        monkeypatch.setattr(entry, "_collect_current_checkpoint", fail)
    assert browser.submit(form, cards=["CA", "C10"])[0] in {400, 409}
    assert active.document is document and active.path.read_bytes() == before
    assert active.generation == generation and active.execution_attempt is sentinel


def test_exact_binding_concurrent_duplicate_reopen_and_equal_revision_change(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: browser.submit(form, cards=["CA"])[0], range(2)))
    assert sorted(statuses) == [303, 409] and active.state.revision == 2
    current_form = Forms(browser.page()).find("/sessions/cards")
    alternate = api.correct_session_command(active.state, api.SessionCommandCorrectionV1(
        expected_revision=active.state.revision, target_revision=2,
        replacement_command=api.RecordSessionDealtCardCommandV1(expected_revision=1,
            destination="player_hand", player_id=active.state.local_player_id, card="C10"))).value
    other = api.build_session_persistence_document(alternate.state).value
    session_files.save_session_file(active.path, other,
        expected_content_fingerprint=active.document.content_fingerprint)
    accepted = active.document
    assert browser.submit(current_form, cards=["C9"])[0] == 409
    assert active.document is accepted
    active.document = other  # Simulates an equal-revision current-context correction publication.
    assert browser.submit(current_form, cards=["C9"])[0] == 409
    fresh = Forms(browser.page()).find("/sessions/cards")
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert browser.submit(fresh, cards=["C9"])[0] == 409


def test_native_rejected_selection_language_and_forged_fields(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    status, _, body = browser.submit(form, cards=["CA", "CA", "SJ"])
    assert status == 400
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(body.decode()).find("/actions/profile/language"),
                                          language="de"))
    assert selected(page) == ["CA", "SJ"]
    assert text("de", "validation.card_entry.duplicate") in page
    assert active.path.read_bytes() == before
    for extra in ({"player_id": "forged"}, {"destination": "skat"}, {"command": "forged"},
                  {"game_id": "forged"}, {"played_at": "2026-01-15T19:30:00Z"}):
        assert browser.submit(form, cards=["CA"], **extra)[0] == 400
    assert browser.submit(form, cards=["CA"], managed_handle="f" * 64)[0] == 409
    assert browser.submit(form, cards=["CA"], card_selection="f" * 64)[0] == 409
    for header in ({"Origin": "null"}, {"Cookie": ""}, {"Origin": "http://foreign.invalid"}):
        assert browser.request("POST", form["action"], {**form["values"], "cards": "CA"},
                               headers=header)[0] == 403
    assert active.path.read_bytes() == before


def test_match_evidence_after_play_noop_modes_stale_position_and_real_recovery(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    data = build_historical_input(hand_game=True)
    hand = data["players"][0]["initial_hand"]
    # The generated source's first Play belongs to the perspective's original hand.
    card = data["tricks"][0]["plays"][0]["card"]
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    assert card not in choice_codes(page)
    form = operation_form(page, "set_perspective_hand")
    page = follow(browser, browser.submit(form, card_evidence_mode="exact", cards=hand))
    assert card in active.workspace.slots[0].observed_game.perspective_initial_hand
    saved, revision = active.path.read_bytes(), active.workspace.revision
    form = operation_form(page, "set_perspective_hand")
    assert set(form["values"]["cards"]) == set(hand)
    assert form["values"]["card_evidence_mode"] == "exact"
    assert card in form["values"]["cards"]  # INITIAL evidence still includes the played Card.
    page = follow(browser, browser.submit(form, card_evidence_mode="exact",
                                          cards=list(reversed(hand))))
    assert active.path.read_bytes() == saved and active.workspace.revision == revision
    status, _, body = browser.submit(operation_form(page, "append_plays"), cards=card)
    assert status == 400 and text("en", "recovery.reason.duplicate") in body.decode()
    assert active.path.read_bytes() == saved
    page = follow(browser, browser.submit(entry_action(body.decode(), 1, rewind=True)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    assert len(active.workspace.slots[0].observed_game.plays) == 1
    assert set(operation_form(page, "set_perspective_hand")["values"]["cards"]) == set(hand)
    # Evidence clear is explicit; merely unchecking an Exact hand fails.
    form = operation_form(page, "set_perspective_hand")
    assert browser.submit(form, cards=[], card_evidence_mode="exact")[0] == 400
    page = follow(browser, browser.submit(form, cards=[], card_evidence_mode="unknown"))
    assert active.workspace.slots[0].observed_game.perspective_initial_hand is None
    page = follow(browser, browser.submit(operation_form(page, "set_discarded_cards"),
                                          cards=[], card_evidence_mode="known_empty"))
    assert active.workspace.slots[0].observed_game.discarded_cards == ()
    stale = operation_form(page, "append_plays")
    browser.page("/matches/position/2")
    before = active.path.read_bytes()
    assert browser.submit(stale, cards="S9")[0] == 409
    assert active.selected_position == 2 and active.path.read_bytes() == before


def test_shared_display_order_is_printed_suits_not_strength_or_command_order():
    deck = get_full_deck()
    for game in (None, "clubs", "spades", "hearts", "diamonds", "grand", "null"):
        groups = card_display_groups(deck, game)
        assert groups[0] == ("task.card.suit.C", ("CJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7"))
        assert [key for key, _ in groups] == ["task.card.suit." + suit for suit in "CSHD"]


def test_direct_batch_adapter_does_not_accept_arbitrary_target(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    with pytest.raises(entry.CardEntryError):
        dispatch_card_entry(localized_server.app_context, "/sessions/cards",
                           {**form["values"], "cards": ["CA"], "destination": "skat"})


def test_real_match_overlap_single_save_and_advanced_trace_order(localized_server, monkeypatch):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    declaration = operation_form(page, "set_declaration")
    choices = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    own = re.search(r'<option value="([^"]+)"[^>]*>Alexandra', choices)[1]
    declaration["values"].pop("hand_game", None)  # Native explicit uncheck.
    page = follow(browser, browser.submit(declaration, declarer_player_id=own))
    saves = []
    original = MatchCaptureWebContextV1.save_candidate
    def save(context, candidate):
        saves.append(candidate)
        return original(context, candidate)
    monkeypatch.setattr(MatchCaptureWebContextV1, "save_candidate", save)
    for operation, cards in (("set_perspective_hand", get_full_deck()[:10]),
                             ("set_original_skat", ["D7", "H7"]),
                             ("set_discarded_cards", ["D7", "CA"])):
        count = len(saves)
        response = browser.submit(operation_form(page, operation),
                                  cards=cards, card_evidence_mode="exact")
        assert response[0] == 303, (operation, re.findall(
            r'<section class="error-summary".*?</section>', response[2].decode(), re.S))
        page = follow(browser, response)
        assert len(saves) == count + 1
    game = active.workspace.slots[0].observed_game
    assert set(game.original_skat).intersection(game.discarded_cards) == {"D7"}
    assert "H7" in choice_codes(page) and "D7" not in choice_codes(page)
    before = active.path.read_bytes()
    assert browser.submit(operation_form(page, "append_plays"), cards=["H7", "C10"])[0] == 400
    assert active.path.read_bytes() == before
    # The ordered advanced transport still takes a trace, not an unordered set.
    advanced = next(form for form in Forms(browser.page("/matches/current")).forms
                    if form["action"] == "/matches/api/v1/operation"
                    and form["values"].get("operation") == "append_plays")
    follow(browser, browser.submit(advanced, cards="H7 D8"))
    assert [p.card for p in active.workspace.slots[0].observed_game.plays] == ["H7", "D8"]


def test_real_match_report_noop_retention_and_success_invalidation(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    hand = get_full_deck()[:10]
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
                                          card_evidence_mode="exact", cards=hand))
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards="CA"))
    analysis = operation_form(page, "analyze_decision")
    response = browser.submit(analysis, immediate_sample_count="1")
    assert response[0] == 303, (analysis, re.findall(
        r'<section class="error-summary".*?</section>', response[2].decode(), re.S))
    page = follow(browser, response)
    reports = active.capture.report_store.list()
    assert len(reports) == 1
    before = active.path.read_bytes()
    # Reports now lead with review; follow the emitted same-Game recording link.
    recording = re.search(r'href="(/matches/position/1)#match-recording"', page)[1]
    page = browser.page(recording)
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
                                          card_evidence_mode="exact", cards=list(reversed(hand))))
    assert active.capture.report_store.list() == reports and active.path.read_bytes() == before
    assert browser.submit(operation_form(page, "append_plays"), cards="CA")[0] == 400
    assert active.capture.report_store.list() == reports
    follow(browser, browser.submit(operation_form(page, "append_plays"), cards="H7"))
    assert active.capture.report_store.list() == ()


def test_real_competing_writer_at_save_rejects_whole_batch(localized_server, monkeypatch):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    source = active.document
    real = session_files.save_session_file
    calls = []
    competing = api.apply_session_command(source.state, api.RecordSessionDealtCardCommandV1(
        expected_revision=source.state.revision, destination="player_hand",
        player_id=source.state.local_player_id, card="D7")).value.state
    other = api.build_session_persistence_document(competing).value
    def compete(path, document, **kwargs):
        calls.append(document)
        real(path, other, expected_content_fingerprint=source.content_fingerprint)
        return real(path, document, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", compete)
    assert browser.submit(form, cards=["CA", "C10"])[0] == 409
    assert len(calls) == 1 and active.document is source
    assert session_files.load_session_file(active.path).value.document == other


def test_session_single_play_duplicate_values_and_success_result_lifecycle(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true")
    active = localized_server.app_context.managed_stateful.active_session
    play = Forms(browser.page()).find("/sessions/play")
    before = active.path.read_bytes()
    assert browser.submit(play, cards=["CA", "CA"])[0] == 400
    assert active.path.read_bytes() == before
    follow(browser, browser.submit(play, cards="CA"))
    review_first(browser)
    execution, label = active.execution, active.recorded_review_source
    before = active.path.read_bytes()
    play = Forms(browser.page()).find("/sessions/play")
    assert browser.submit(play, cards="CA")[0] == 400
    assert active.execution is execution and active.recorded_review_source is label
    assert active.path.read_bytes() == before
    follow(browser, browser.submit(play, cards="H7"))
    assert active.execution is active.recorded_review_source is active.execution_attempt is None


@pytest.mark.parametrize("binding", (None, ["f" * 64, "a" * 64], "x" * 65))
def test_unbound_rejection_does_not_select_card_in_current_task(localized_server, binding):
    browser = Browser(localized_server)
    form = create_live(browser)
    values = {**form["values"], "cards": "CA"}
    values.pop("card_selection")
    if binding is not None:
        values["card_selection"] = binding
    status, _, body = browser.request("POST", form["action"], values)
    assert status == 400
    page = body.decode()
    assert not re.search(r'<input[^>]*value="CA"[^>]*checked', page)
    assert text("en", "compact.stale_input", cards="CA") in page
