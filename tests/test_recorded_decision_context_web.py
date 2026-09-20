import re
from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_decision_context import MATCH_HAND, assert_context
from test_recorded_review_navigation import chooser_form, home_chooser, select_game
from test_session_recorded_review_web import Browser, Forms

import skatmind.capture_web.analysis as match_analysis
import skatmind.capture_web.context as capture_context
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1 as canonical
from skatmind.app_web.match_report_rendering import render_match_reports_v1
from skatmind.app_web.recorded_decision_context_sources import match_decision_context
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.app_web.task_first_match_state import build_task_first_match_page_state_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def record_context_match(browser, *, names=("B", "C", "A")):
    """Returned native forms, only C's hand and the complete three-Play partial trace."""
    page = browser.page("/matches/new")
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        match_title="Synthetic decision context", forehand_name=names[0], middlehand_name=names[1],
        rearhand_name=names[2], perspective_seat="middlehand", platform_choice="in_person",
        setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
                                          setup_action="create"))
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    declarer = next(value for value, label in re.findall(
        r'<option value="([^"]+)"[^>]*>(.*?)</option>', options) if label.startswith("B"))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=declarer, game_type="grand", bid_value="18"))
    for card in ("CK", "C7", "C10"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    return follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
                                          card_evidence_mode="exact", cards=MATCH_HAND))


def record_second_context_game(browser):
    page = browser.page("/matches/position/4")
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    declarer = next(value for value, label in re.findall(
        r'<option value="([^"]+)"[^>]*>(.*?)</option>', options) if label.startswith("B"))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=declarer, game_type="grand", bid_value="18"))
    for card in ("H7", "HK", "HA"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    return follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
                                          card_evidence_mode="exact", cards=MATCH_HAND))


def test_real_match_normal_pre_card_context(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_context_match(browser)
    record_second_context_game(browser)
    active = localized_server.app_context.managed_stateful.active_match
    source = active.workspace
    disk = active.path.read_bytes()
    calls, saves = [], []
    real = match_analysis.execute_match_decision_analysis_v1
    def counted(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    def save(*args, **kwargs):
        saves.append(args)
        raise AssertionError("Passive context display must not save Product data")
    monkeypatch.setattr(match_analysis, "execute_match_decision_analysis_v1", counted)
    monkeypatch.setattr(capture_context, "save_match_workspace_file_v1", save)
    page = browser.page("/matches/review/4")
    follow(browser, browser.submit(operation_form(page, "analyze_decision")))
    other, = active.capture.report_store.list()
    page = browser.page("/matches/review/1")
    form = operation_form(page, "analyze_decision")
    assert form["values"]["decision_index"] == "2"
    page = follow(browser, browser.submit(form))
    report = active.capture.report_store.list()[-1]
    result = report.value.result.document
    binding = report.value.profile_binding
    labels = {p.player_id: p.player_label for p in source.match_definition.participants}
    assert [labels[player] for player in (binding.acting_player_id,
        binding.left_opponent_player_id, binding.right_opponent_player_id)] == ["C", "A", "B"]
    assert not binding.left_profile_available and not binding.right_profile_available
    assert result["position"]["current_trick"] == ("CK",)
    assert result["position"]["hand"] == MATCH_HAND
    retained = canonical(report.to_dict())
    source_bytes = canonical(source.to_dict())
    route = f"/matches/reports/{report.report_id}"
    download_route = f"/matches/api/v1/reports/{report.report_id}.json"
    download = browser.request("GET", download_route)[2]
    assert len(calls) == 2 and not saves
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        context = assert_context(page, locale, hand=MATCH_HAND, prefix=(("B", "CK"),), actor="C",
                                 trick=1, play=2, game=1)
        assert f'{text(locale, "task.field.declarer_player_id")}</dt><dd>B' in context
        assert card_name(locale, "C10") not in context and card_name(locale, "HA") not in context
        for key in ("guided.declarer_points", "guided.defender_points"):
            assert f'{text(locale, key)}</dt><dd>0' in context
        assert page.index('class="recorded-decision-context"') < page.index(
            text(locale, "result.actual_card"))
        other_page = browser.page(f"/matches/reports/{other.report_id}")
        assert_context(other_page, locale, hand=MATCH_HAND, prefix=(("B", "H7"),), actor="C",
                       trick=1, play=2, game=4)
        select_game(browser, other_page, 2)
        page = browser.page(route)
        page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
        page = browser.page(route)
        assert_context(page, locale, hand=MATCH_HAND, prefix=(("B", "CK"),), actor="C",
                       trick=1, play=2, game=1)
        assert browser.request("GET", download_route)[2] == download
    assert len(calls) == 2 and not saves
    assert active.path.read_bytes() == disk and active.workspace is source
    assert canonical(report.to_dict()) == retained and canonical(source.to_dict()) == source_bytes

    # The minimized page snapshot also binds correctly if another Game was selected.
    with active.capture.lock:
        state = build_task_first_match_page_state_v1(active,
            project_task_first_match_v1(source, selected_position=2), report_id=report.report_id)
    assert state["game"] is None and state["decision_preparation"]["source_play_count"] == 0
    assert_context(render_match_reports_v1(state, "en"), "en", hand=MATCH_HAND,
                    prefix=(("B", "CK"),), actor="C", trick=1, play=2, game=1)
    # The normal history belongs to the selected Game, even with an earlier
    # retained Report having the same decision index in another Game.
    from test_recorded_party_presentation import assert_party_score, history_rows

    from skatmind.app_web.match_review_rendering import render_match_review_v1
    with active.capture.lock:
        view = project_task_first_match_v1(source, selected_position=4)
        state = build_task_first_match_page_state_v1(active, view, report_id=report.report_id)
    page = render_match_review_v1(state, view, managed_handle=active.handle, locale="en")
    assert_party_score(page, (0, 0), (15, 1))
    assert [re.search(r'\(([A-Z0-9]+)\)', row["text"])[1]
            for row in history_rows(page)] == ["H7", "HK", "HA"]
    assert_context(page, "en", hand=MATCH_HAND, prefix=(("B", "CK"),), actor="C",
                   trick=1, play=2, game=1)
    assert 'href="/matches/position/4#match-play-2"' in page
    foreign_report = replace(report, value=replace(report.value, game_id="foreign"))
    unbound = match_decision_context(foreign_report, source)
    assert unbound.actor is unbound.declarer is None and unbound.hand == MATCH_HAND
    assert unbound.game_number is unbound.trick_number is None


@pytest.mark.parametrize("method", ("bounded_search", "information_set_search", "auto"))
def test_executed_method_limits_still_have_context(localized_server, method):
    browser = Browser(localized_server)
    record_context_match(browser)
    form = operation_form(browser.page("/matches/review/1"), "analyze_decision")
    page = follow(browser, browser.submit(form, recommendation_method=method))
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    assert report.value.status == "executed"
    if method == "auto":
        assert report.value.result.document["recommendation_method_summary"]["fallback_used"]
    else:
        assert report.value.result.document["recommendation"]["card"] is None
    assert_context(page, "en", hand=MATCH_HAND, prefix=(("B", "CK"),), actor="C",
                   trick=1, play=2, game=1)
