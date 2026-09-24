import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import entry_action, follow, operation_form, synthetic_cards
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_workspace_persistence import load_match_workspace_file_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@pytest.fixture
def saves(localized_server, monkeypatch):
    recorded = []
    original = os.replace
    root = localized_server.app_context.managed_stateful.root("matches")
    def counted(source, destination):
        if Path(destination).parent == root:
            recorded.append(destination)
        return original(source, destination)
    monkeypatch.setattr(os, "replace", counted)
    return recorded


def create_empty(browser, locale):
    page = browser.page("/matches/new")
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                         language=locale))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        match_title="Synthetic navigation", forehand_name="Anna", middlehand_name="Boris",
        rearhand_name="Clara", perspective_seat="middlehand", setup_action="update"))
    response = browser.submit(Forms(page).find("/matches/api/v1/create"), setup_action="create")
    assert response[1]["location"] == "/matches/position/1#match-recording"
    return follow(browser, response)


def primary(page, operation):
    return operation_form(page.split('<section id="match-games"', 1)[0], operation)


def link(browser, page, href):
    assert f'href="{href}"' in page
    return browser.page(urlsplit(href).path or "/matches/current")


def declare(browser, page):
    options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    player = re.findall(r'<option value="([^"]+)"', options)[0]
    return follow(browser, browser.submit(primary(page, "set_declaration"),
        declarer_player_id=player, game_type="grand", hand_game="true"))


def assert_progress(page, locale, kind):
    from test_match_game_navigation import PROGRESS
    assert (f'<p class="match-recording-status">{PROGRESS[locale][kind]}</p>'
            in page.split('<section id="match-games"', 1)[0])


@pytest.mark.parametrize("locale", ("en", "de"))
def test_real_empty_create_start_declare_play_pass_backward_continue_and_reopen(
    localized_server, saves, locale,
):
    browser = Browser(localized_server)
    page = create_empty(browser, locale)
    active = localized_server.app_context.managed_stateful.active_match
    assert len(saves) == 1 and active.workspace.revision == 0
    assert all(slot.observed_game is None for slot in active.workspace.slots)
    page = follow(browser, browser.submit(primary(page, "start_game")))
    assert len(saves) == 2 and active.workspace.revision == 1
    page = declare(browser, page)
    assert len(saves) == 3
    for count, card in enumerate(synthetic_cards()[:3], 1):
        page = follow(browser, browser.submit(primary(page, "append_plays"), cards=card))
        assert_progress(page, locale, count)
    assert len(saves) == 6
    original = active.path.read_bytes()
    generation = active.position_generation
    page = link(browser, page, "#match-games")
    page = link(browser, page, "/matches/position/1#match-recording")
    assert active.position_generation == generation
    stale_card = primary(page, "append_plays")
    stale_declaration = operation_form(page, "set_declaration")
    page = link(browser, page, "/matches/position/2#match-recording")
    assert active.selected_position == 2 and active.workspace.slots[1].observed_game is None
    assert active.path.read_bytes() == original and len(saves) == 6
    assert_progress(page, locale, "empty")
    assert browser.submit(stale_card, cards="S9")[0] == 409
    assert browser.submit(stale_declaration, bid_value="18")[0] == 409
    page = browser.page("/matches/position/2")
    language = browser.submit(Forms(page).find("/actions/profile/language"), language=locale)
    assert language[1]["location"] == "/matches/position/2"
    page = follow(browser, language)
    assert re.search(r'<section class="error-summary"[^>]*autofocus', page)
    assert text(locale, "task.match.first_unfinished", number=1) in page
    page = follow(browser, browser.submit(primary(page, "mark_passed_deal")))
    assert len(saves) == 7 and active.selected_position == 2
    assert_progress(page, locale, "passed")
    assert active.workspace.slots[1].slot_kind == "passed_deal"
    page = link(browser, page, "/matches/position/1#match-recording")
    assert len(saves) == 7
    assert_progress(page, locale, 3)
    page = follow(browser, browser.submit(primary(page, "append_plays"), cards="CA"))
    assert len(saves) == 8 and active.selected_position == 1
    assert_progress(page, locale, 4)
    accepted = active.path.read_bytes()
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
    page = link(browser, page, "/matches/review/1")
    page = link(browser, page, "/matches/position/1#match-recording")
    page = link(browser, page, "/matches/position/2#match-recording")
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    reopened = localized_server.app_context.managed_stateful.active_match
    assert reopened is not active and reopened.selected_position == 1
    assert reopened.path.read_bytes() == accepted and len(saves) == 8
    assert reopened.workspace == active.workspace
    assert_progress(page, locale, 4)


def test_rejected_card_language_keeps_summary_priority_safe_value_and_fresh_binding(
    localized_server, saves,
):
    browser = Browser(localized_server)
    page = declare(browser, follow(browser, browser.submit(primary(
        create_empty(browser, "en"), "start_game"))))
    form = primary(page, "append_plays")
    active = localized_server.app_context.managed_stateful.active_match
    before, count = active.path.read_bytes(), len(saves)
    response = browser.submit(form, cards="invalid")
    assert response[0] == 400
    page = response[2].decode()
    for locale in ("de", "en"):
        response = browser.submit(Forms(page).find("/actions/profile/language"), language=locale)
        assert response[1]["location"] == "/matches/position/1"
        page = follow(browser, response)
        assert re.search(r'<section class="error-summary"[^>]*autofocus', page)
        assert "invalid" in page
        assert active.path.read_bytes() == before and len(saves) == count
        assert_progress(page, locale, "declaration")
    follow(browser, browser.submit(primary(page, "append_plays"), cards="SA"))
    assert len(saves) == count + 1


@pytest.mark.parametrize("locale", ("de", "en"))
def test_final_card_report_preview_language_noop_cancel_and_real_rewind(
    localized_server, saves, locale,
):
    browser = Browser(localized_server)
    page = declare(browser, follow(browser, browser.submit(primary(
        create_empty(browser, locale), "start_game"))))
    active = localized_server.app_context.managed_stateful.active_match
    cards = synthetic_cards()
    # Surrounding legal fixture: one existing explicit batch, not 29 fake browser saves.
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=cards[0]))
    legacy = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/operation"
                  and f["values"].get("operation") == "append_plays")
    page = follow(browser, browser.submit(legacy, cards=" ".join(cards[1:29])))
    assert_progress(page, locale, 29)
    count = len(saves)
    response = browser.submit(primary(page, "append_plays"), cards=cards[-1])
    assert response[1]["location"] == "/matches/position/1#match-recording"
    page = follow(browser, response)
    assert len(saves) == count + 1 and active.selected_position == 1
    assert text(locale, "task.match.first_unfinished", number=2) in page
    assert len(active.workspace.slots[0].observed_game.plays) == 30
    assert_progress(page, locale, 30)
    assert 'data-unplayed-cards' in page
    assert all(page.count(f'id="match-play-{n}"') == 1 for n in range(1, 31))
    page = link(browser, page, "/matches/review/1")
    response = browser.submit(operation_form(page, "analyze_decision"), immediate_sample_count="1")
    page = follow(browser, response)
    report = active.capture.report_store.list()[-1]
    assert report.value.status == "executed" and report.match_position == 1
    report_path = response[1]["location"]
    download = f"/matches/api/v1/reports/{report.report_id}.json"
    report_bytes = browser.request("GET", download)[2]
    page = link(browser, page, "/matches/position/1#match-recording")
    original = active.path.read_bytes()
    # A genuine same-Card preview/apply is a no-op and preserves the Report.
    page = follow(browser, browser.submit(entry_action(page, 30)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"),
                                         card=cards[-1]))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                         confirm_apply="on"))
    assert active.path.read_bytes() == original and len(saves) == count + 1
    page = follow(browser, browser.submit(entry_action(page, 30, rewind=True)))
    assert_progress(page, locale, 30)
    preview, selected = active.recovery.preview, active.recovery.selected
    apply = Forms(page).find("/matches/recovery/apply")
    for route in ("/matches/current", "/matches/position/1", "/matches/review/1", report_path):
        page = browser.page(route)
        assert active.recovery.preview is preview and active.recovery.selected is selected
        assert active.capture.report_store.list() == (report,)
    page = link(browser, page, "/matches/position/1#match-recording")
    page = link(browser, page, "#match-games")
    for target in ("en", "de"):
        response = browser.submit(Forms(page).find("/actions/profile/language"), language=target)
        assert response[1]["location"].endswith("#match-recovery")
        page = follow(browser, response)
        binding = Forms(page).find("/matches/recovery/apply")["values"]["recovery_selection"]
        assert binding == preview.apply_token
        assert_progress(page, target, 30)
        assert active.recovery.selected is selected and active.recovery.preview is preview
        assert browser.request("GET", download)[2] == report_bytes
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/cancel")))
    assert_progress(page, "de", 30)
    assert active.path.read_bytes() == original and len(saves) == count + 1
    assert browser.submit(apply, confirm_apply="on")[0] == 409
    page = browser.page("/matches/current")
    page = follow(browser, browser.submit(entry_action(page, 30, rewind=True)))
    page = link(browser, page, "/matches/position/2#match-recording")
    assert_progress(page, "de", "empty")
    assert active.recovery.preview is None and active.recovery.selected is None
    assert active.capture.report_store.list() == (report,)
    page = browser.page(report_path)
    assert '<h2>' + text("de", "recordings.match.game", position=1) + '</h2>' in page
    assert 'href="/matches/position/1#match-recording"' in page
    assert active.selected_position == 1 and browser.request("GET", download)[2] == report_bytes
    page = link(browser, page, "/matches/position/1#match-recording")
    page = follow(browser, browser.submit(entry_action(page, 30, rewind=True)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                         confirm_apply="on"))
    assert len(saves) == count + 2 and active.selected_position == 1
    assert len(active.workspace.slots[0].observed_game.plays) == 29
    assert_progress(page, "de", 29)
    assert project_task_first_match_v1(active.workspace, selected_position=1).next_position == 1
    assert text("de", "task.match.first_unfinished", number=1) not in page
    assert 'data-unplayed-cards' not in page and active.capture.report_store.list() == ()
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
