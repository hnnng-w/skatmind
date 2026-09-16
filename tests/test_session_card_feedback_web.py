"""Real returned-form negative payloads, separate from genuinely selectable saves."""

import http.client
import re
from concurrent.futures import ThreadPoolExecutor
from html import escape
from threading import Event
from urllib.parse import urlencode

import pytest
from test_compact_card_entry_web import choice_codes, create_live
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_recording_deletion_web import preview
from test_session_recorded_review_web import Browser, Forms

import skatmind.api.v1.session as api
import skatmind.api.v1.session.files as files
import skatmind.app_web.execution as execution
import skatmind.app_web.server as server_module
import skatmind.app_web.session_card_entry as entry
from skatmind.app_web.session_card_feedback import render_card_witness
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.deck import get_full_deck


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def start_play(browser, *, local="forehand", label="Anna"):
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/create"),
        game_name="Synthetic feedback", capture_mode="live", perspective_seat=local,
        forehand_name=label, middlehand_name="Boris", rearhand_name="Clara", setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/sessions/create"),
                                          setup_action="create"))
    hand = (["C7", "SQ", "CA", "C10", "CK", "CQ", "C9", "C8", "SA", "S10"]
            if local == "forehand" else
            ["C8", "C9", "C10", "CK", "CQ", "CA", "SQ", "SA", "S10", "SK"])
    follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=hand))
    active = browser.server.app_context.managed_stateful.active_session
    assert active.state.revision == 11
    browser.command("set_declarer", player_id=active.state.local_player_id)
    browser.command("set_declaration", game_type="grand", hand_game="true")
    return active


def snapshot(active):
    return (active.path.read_bytes(), active.document, active.decision_checkpoints,
            active.generation, active.execution, active.recorded_review_source)


@pytest.mark.parametrize("local,cards,rejected,kind,anchor", (
    ("forehand", ["C7", "H7"], "SQ", "owner_hand", "session-hand-1"),
    ("forehand", ["C7", "H7"], "C7", "played", "session-play-1"),
    ("middlehand", ["C7"], "SQ", "follow", "session-play-1"),
    ("middlehand", ["C7"], "H7", "missing_hand", "session-hand-2"),
))
def test_four_actual_rejections_links_language_and_one_selectable_save(
    localized_server, monkeypatch, local, cards, rejected, kind, anchor,
):
    browser = Browser(localized_server)
    active = start_play(browser, local=local)
    for card in cards:
        assert card in choice_codes(browser.page())
        browser.command("record_play", card=card)
    # A genuine #221 execution is retained for Anna's already accepted first Play.
    if local == "forehand":
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/review-decision")))
        assert active.execution is not None
    before = snapshot(active)
    downloads = tuple(browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                      for name in ("request", "result")) if active.execution else ()
    saves, executions = [], []
    real_save = files.save_session_file
    def save(*args, **kwargs):
        saves.append(args)
        return real_save(*args, **kwargs)
    def forbidden(*args, **kwargs):
        executions.append(args)
        raise AssertionError("Feedback and viewing must not execute analysis")
    monkeypatch.setattr(files, "save_session_file", save)
    monkeypatch.setattr(execution, "execute", forbidden)
    page = browser.page()
    assert rejected not in choice_codes(page)
    form = Forms(page).find("/sessions/play")
    # Deliberate source-bound negative transport payload; never claimed as a palette choice.
    response = browser.submit(form, cards=rejected)
    assert response[0] == 400
    page = response[2].decode()
    state = localized_server.app_context.form_feedback.current("sessions", active_identity=active)
    witness = state.validation_issues[0].session_card_feedback.witness
    assert witness.kind == kind
    for locale in ("en", "de", "en"):
        if locale != "en" or 'lang="de"' in page:
            response = browser.submit(Forms(page).find("/actions/profile/language"),
                                      language=locale)
            assert response[1]["location"] == "/sessions/current#session-card-error"
            page = follow(browser, response)
        message, actual_anchor = render_card_witness(witness, active.state.players, locale)
        assert actual_anchor == anchor and escape(message) in page
        assert text(locale, "validation.session_card.heading") in page
        assert text(locale, "validation.summary.heading") not in page
        assert text(locale, "validation.summary.guidance") not in page
        assert 'role="alert" tabindex="-1" autofocus' in page
        assert 'aria-invalid="true"' in page and 'class="field-error"' in page
        assert f'class="session-card-evidence" href="#{anchor}"' in page
        assert len(re.findall(f'id="{anchor}"', page)) == 1
        assert re.search(f'<[^>]+id="{anchor}"[^>]+tabindex="-1"', page)
        assert rejected not in choice_codes(page)
        assert not Forms(page).find("/sessions/play")["values"].get("cards")
        assert snapshot(active) == before
    # Native anchor navigation is a same-page read; HTTP GET likewise changes nothing.
    page = browser.page("/sessions/current#" + anchor)
    assert snapshot(active) == before and saves == executions == []
    if downloads:
        assert tuple(browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                     for name in ("request", "result")) == downloads
    valid = choice_codes(page)[0]
    response = browser.submit(Forms(page).find("/sessions/play"), cards=valid)
    assert response[0] == 303 and response[1]["location"] == "/sessions/current#session-recording"
    assert len(saves) == 1 and active.state.revision == before[1].state.revision + 1
    assert active.execution is None
    assert 'class="session-card-evidence"' not in follow(browser, response)
    saved = active.path.read_bytes()
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert localized_server.app_context.managed_stateful.active_session.path.read_bytes() == saved


def test_native_empty_and_partial_batch_keep_valid_selection_without_save(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = snapshot(active)
    response = browser.submit(form)  # Native empty checkbox form has no required control.
    assert response[0] == 400 and snapshot(active) == before
    assert text("en", "validation.card_entry.empty") in response[2].decode()
    follow(browser, browser.submit(Forms(response[2].decode()).find("/sessions/cards"), cards="SQ"))
    before = snapshot(active)
    response = browser.submit(Forms(browser.page()).find("/sessions/cards"), cards=["CA", "SQ"])
    assert response[0] == 400 and snapshot(active) == before
    page = response[2].decode()
    assert "already assigned" in page and card_name("en", "SQ") in page
    assert 'href="#session-hand-1"' in page and "SQ" not in choice_codes(page, mode="set")
    assert Forms(page).find("/sessions/cards")["values"]["cards"] == "CA"
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    assert Forms(page).find("/sessions/cards")["values"]["cards"] == "CA"
    assert snapshot(active) == before
    follow(browser, browser.submit(Forms(page).find("/sessions/cards")))
    assert active.state.revision == before[1].state.revision + 1


@pytest.mark.parametrize("change", ("reopen", "reload", "undo", "foreign", "equal", "retire"))
def test_old_sources_and_language_forms_never_retain_witness_on_new_data(
    localized_server, change,
):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards="SQ"))
    active = localized_server.app_context.managed_stateful.active_session
    form = Forms(browser.page()).find("/sessions/cards")
    response = browser.submit(form, cards="SQ")
    assert response[0] == 400
    language = Forms(response[2].decode()).find("/actions/profile/language")
    if change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    elif change == "reload":
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/reload")))
    elif change == "undo":
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/undo"),
                                       target_revision="1"))
    elif change == "foreign":
        create_live(browser)
    elif change == "retire":
        page = preview(browser, "sessions", active.handle)
        follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                       confirm_delete="on"))
        assert active.retired
    else:
        alternate = api.correct_session_command(active.state, api.SessionCommandCorrectionV1(
            expected_revision=2, target_revision=2,
            replacement_command=api.RecordSessionDealtCardCommandV1(expected_revision=1,
                destination="player_hand", player_id=active.state.local_player_id,
                card="CA"))).value
        other = api.build_session_persistence_document(alternate.state).value
        assert files.save_session_file(active.path, other,
            expected_content_fingerprint=(
                active.document.content_fingerprint)).value.status == "saved"
        # Explicit equal-revision external-writer fixture. Accepted context still has old data.
        page = browser.page()
        assert 'class="session-card-evidence"' not in page
        active.document = other  # Same-context replacement fixture, with no generation increment.
    response = browser.submit(language, language="de")
    assert response[0] == 409 and 'class="session-card-evidence"' not in response[2].decode()
    response = browser.submit(form, cards="SQ")
    assert response[0] == 409 and 'class="session-card-evidence"' not in response[2].decode()


def test_competing_rejections_publish_in_attempt_order(localized_server, monkeypatch):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=["CA", "SQ"]))
    form = Forms(browser.page()).find("/sessions/cards")
    active = localized_server.app_context.managed_stateful.active_session
    before = snapshot(active)
    entered, release = Event(), Event()
    real = server_module.SkatMindAppWebRequestHandlerV1._retain_form_feedback
    def paused(self, definition, **kwargs):
        witness = kwargs["issues"][0].session_card_feedback
        if witness is not None and witness.witness.card == "CA":
            entered.set()
            assert release.wait(15)
        return real(self, definition, **kwargs)
    monkeypatch.setattr(server_module.SkatMindAppWebRequestHandlerV1,
                        "_retain_form_feedback", paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(browser.submit, form, cards="CA")
        assert entered.wait(15)
        second = pool.submit(browser.submit, form, cards="SQ")
        release.set()
        first_response, second_response = first.result(), second.result()
        assert first_response[0] == second_response[0] == 400
    state = localized_server.app_context.form_feedback.current("sessions", active_identity=active)
    assert state.validation_issues[0].session_card_feedback.witness.card == "SQ"
    assert snapshot(active) == before
    old_language = Forms(first_response[2].decode()).find("/actions/profile/language")
    assert browser.submit(old_language, language="de")[0] == 409


@pytest.mark.parametrize("failure", ("witness", "save"))
def test_optional_witness_failure_and_failed_save_preserve_real_result(
    localized_server, monkeypatch, failure,
):
    browser = Browser(localized_server)
    active = start_play(browser)
    browser.command("record_play", card="C7")
    follow(browser, browser.submit(Forms(browser.page()).find("/sessions/review-decision")))
    before = snapshot(active)
    def fail(*args, **kwargs):
        raise OSError("Injected failure")
    monkeypatch.setattr(entry if failure == "witness" else files,
        "rejected_card_witness" if failure == "witness" else "save_session_file", fail)
    page = browser.page()
    card = "SQ" if failure == "witness" else choice_codes(page)[0]
    response = browser.submit(Forms(page).find("/sessions/play"), cards=card)
    assert response[0] == (400 if failure == "witness" else 409)
    assert 'class="session-card-evidence"' not in response[2].decode()
    assert snapshot(active) == before


@pytest.mark.parametrize("route", ("/sessions/cards", "/sessions/play"))
def test_real_8192_boundary_and_strict_security(localized_server, route):
    browser = Browser(localized_server)
    if route.endswith("play"):
        active = start_play(browser)
    else:
        create_live(browser)
        active = localized_server.app_context.managed_stateful.active_session
    form = Forms(browser.page()).find(route)
    before = snapshot(active)
    prefix = urlencode({**form["values"], "cards": ""}).encode()
    for size, expected in ((8192, 400), (8193, 413)):
        connection = http.client.HTTPConnection("127.0.0.1", localized_server.port, timeout=60)
        connection.request("POST", route, prefix + b"X" * (size - len(prefix)), headers={
            "Origin": localized_server.origin, "Cookie": browser.cookie,
            "Content-Type": "application/x-www-form-urlencoded"})
        response = connection.getresponse()
        assert response.status == expected
        assert b"session-card-evidence" not in response.read()
        connection.close()
    for field in ("managed_handle", "card_selection"):
        assert browser.submit(form, **{field: [form["values"][field]] * 2}, cards="SQ")[0] == 400
    for header in ({"Origin": "null"}, {"Origin": "http://foreign.invalid"}, {"Cookie": ""}):
        assert browser.request("POST", route, form["values"], headers=header)[0] == 403
    assert snapshot(active) == before


def test_complete_long_label_is_escaped_and_language_resolves_names_again(localized_server):
    browser = Browser(localized_server)
    label = "Anna <synthetic & accepted> " + "LongName" * 11
    active = start_play(browser, label=label)
    browser.command("record_play", card="C7")
    response = browser.submit(Forms(browser.page()).find("/sessions/play"), cards="SQ")
    assert response[0] == 400
    page = response[2].decode()
    for locale in ("en", "de"):
        if locale == "de":
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
        summary = re.search(r'<section class="error-summary".*?</section>', page, re.S)[0]
        assert escape(label) in summary and label not in summary
        assert card_name(locale, "SQ") in summary
        assert len(active.state.players[0].player_label) > 80


def negative_evidence(browser, active, card, kind, anchor, route="/sessions/play"):
    page = browser.page()
    assert card not in choice_codes(page, mode="play" if route.endswith("play") else "set")
    before = snapshot(active)
    response = browser.submit(Forms(page).find(route), cards=card)
    assert response[0] == 400 and snapshot(active) == before
    feedback = browser.server.app_context.form_feedback.current("sessions", active_identity=active)
    witness = feedback.validation_issues[0].session_card_feedback.witness
    assert witness.kind == kind
    message, actual_anchor = render_card_witness(witness, active.state.players, "en")
    assert anchor == actual_anchor and escape(message) in response[2].decode()
    assert f'href="#{anchor}"' in response[2].decode()
    assert f'id="{anchor}" tabindex="-1"' in response[2].decode()


def test_real_skat_discard_membership_discarded_and_pickup_sources(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="false")
    active = localized_server.app_context.managed_stateful.active_session
    browser.command("record_dealt_card", card="H7")
    negative_evidence(browser, active, "H7", "assigned_skat", "session-skat", "/sessions/cards")
    browser.command("record_dealt_card", card="D7")
    negative_evidence(browser, active, "D8", "discard_membership", "session-hand-1",
                      "/sessions/cards")
    browser.command("record_discard", card="CA")
    negative_evidence(browser, active, "CA", "discarded", "session-discards", "/sessions/cards")
    browser.command("record_discard", card="C10")
    negative_evidence(browser, active, "CA", "discarded", "session-discards")
    assert "H7" in choice_codes(browser.page())
    browser.command("record_play", card="H7")
    negative_evidence(browser, active, "D7", "owner_hand", "session-hand-1")


def test_real_complete_deal_untouched_hand_skat_source(localized_server):
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/create"),
        game_name="Synthetic reconstruction", capture_mode="retrospective",
        perspective_seat="forehand", forehand_name="Anna", middlehand_name="Boris",
        rearhand_name="Clara", setup_action="update"))
    follow(browser, browser.submit(Forms(page).find("/sessions/create"), setup_action="create"))
    for start in (0, 10, 20, 30):
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/cards"),
                                       cards=get_full_deck()[start:start + 10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true")
    active = localized_server.app_context.managed_stateful.active_session
    negative_evidence(browser, active, "D7", "hand_skat", "session-skat")


def test_real_accepted_public_hand_links_membership_and_follow(localized_server):
    browser = Browser(localized_server)
    form = create_live(browser)
    follow(browser, browser.submit(form, cards=get_full_deck()[:10]))
    active = localized_server.app_context.managed_stateful.active_session
    player = active.state.players[1].player_id
    browser.command("set_declarer", player_id=player)
    browser.command("set_declaration", game_type="null", hand_game="true", ouvert="true")
    # An ordinary specialist public-hand Command supplies accepted evidence, not a fault fixture.
    browser.command("set_public_hand", player_id=player, cards=" ".join(get_full_deck()[10:20]))
    negative_evidence(browser, active, "SQ", "owner_public", "session-public-hand-2")
    browser.command("record_play", card="SA")
    negative_evidence(browser, active, "D7", "missing_public", "session-public-hand-2")
    negative_evidence(browser, active, "HA", "follow", "session-play-1")
