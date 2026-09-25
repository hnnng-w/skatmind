"""Named evidence navigation over captured accepted Games; no new preparation rules."""

import re
from copy import deepcopy
from dataclasses import replace
from html import escape
from urllib.parse import urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_game_navigation import rendered, workspace_for
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_match_workspace_contracts import _definition, _observed_game, _set_game
from test_recorded_decision_context import MATCH_HAND, assert_context
from test_recorded_decision_context_web import record_context_match, record_second_context_game
from test_recorded_party_presentation import assert_party_score
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first

from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1 as canonical
from skatmind.app_web.match_review_rendering import render_match_analysis_v1
from skatmind.app_web.task_first_match_rendering import render_task_first_match_v1
from skatmind.app_web.task_first_match_state import build_task_first_match_page_state_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.game_declaration import GameDeclaration
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import replace_match_workspace_definition_v1
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.observed_game_trace import ObservedPlayV1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@pytest.mark.parametrize("kind", ("empty", "passed"))
@pytest.mark.parametrize("locale,caption", (
    ("en", "Original Skat and discard evidence"),
    ("de", "Ursprünglicher Skat und gedrückte Karten"),
))
def test_no_empty_evidence_wrapper(kind, locale, caption):
    _, state, page = rendered(workspace_for((kind,)), 1, locale)
    assert state["game"] is None
    assert 'id="match-evidence"' not in page
    assert f"<summary>{caption}</summary>" not in page
    assert 'id="match-initial-hand"' not in page


def test_missing_hand_review_has_one_named_visible_destination(localized_server):
    browser = Browser(localized_server)
    record_context_match(browser, with_hand=False)
    review = browser.page("/matches/review/1")
    href = "/matches/position/1#match-initial-hand"
    assert review.count(f'href="{href}"') == 1
    assert f'href="{href}">Enter known initial hand for C</a>' in review
    page = browser.page(urlsplit(href).path)
    assert '<summary id="match-initial-hand">Initial hand for C</summary>' in page
    assert len(re.findall(r'name="operation" value="set_perspective_hand"', page)) == 1


@pytest.mark.parametrize("kind", ("started", "declaration", 3, "complete"))
def test_unknown_editors_do_not_depend_on_cards_or_prepared_count(kind):
    view, state, page = rendered(workspace_for((kind,)), 1, "en")
    assert state["game"]["perspective_initial_hand"] is None
    assert 'id="match-evidence"' in page and 'id="match-initial-hand"' in page
    for operation in ("set_perspective_hand", "set_original_skat", "set_discarded_cards"):
        form = operation_form(page, operation)
        assert form["action"] == "/matches/cards"
        assert form["values"]["card_evidence_mode"] == "unknown"
        assert not form["values"].get("cards")
    review = render_match_analysis_v1(state, view, "a" * 64, "en")
    if kind == "complete":
        assert state["decision_preparation"]["prepared_decision_count"] == 30
        assert "#match-initial-hand" not in review
    elif kind != 3:
        assert "#match-initial-hand" not in review


@pytest.mark.parametrize("position", (1, 2, 3))
@pytest.mark.parametrize("label", ('Same <&" name', None))
def test_rotated_games_equal_names_and_fallback_do_not_choose_owner_by_label(position, label):
    workspace = workspace_for((6, 6, 6))
    definition = replace(workspace.match_definition,
        participants=tuple(replace(p, player_label=label)
                           for p in workspace.match_definition.participants))
    workspace = replace_match_workspace_definition_v1(
        workspace, definition, expected_revision=workspace.revision).workspace
    view, state, page = rendered(workspace, position, "en")
    assert state["hand_editor_player_id"] == "player-a"
    owner_label = label or "Player 1"
    assert (f'<summary id="match-initial-hand">Initial hand for {escape(owner_label)}</summary>'
            in page)
    own_rows = [row for row in state["decision_preparation"]["decisions"]
                if row["acting_player_id"] == "player-a"]
    assert len(own_rows) == 2
    assert {row["reason"] for row in own_rows} == {"acting_hand_unavailable"}
    review = render_match_analysis_v1(state, view, "a" * 64, "en")
    assert review.count(f'href="/matches/position/{position}#match-initial-hand"') == 1
    assert f'>Enter known initial hand for {escape(owner_label)}</a>' in review


def test_different_real_skip_reasons_and_supplied_non_hand_declarer_hand():
    # Ouvert: the known defender hand does not replace the missing public declarer hand.
    definition = _definition(perspective_player_id="player-a")
    hand = ("C9", "C8", "C7", "S10", "S8", "HK", "H8", "DQ", "DJ", "D9")
    game = _observed_game(definition, match_position=3, perspective_initial_hand=hand,
        declarer_player_id="player-b", declaration=GameDeclaration(game_type="null", ouvert=True),
        plays=(ObservedPlayV1(decision_index=1, player_id="player-a", card="C7",
                              decision_timecode=None),
               ObservedPlayV1(decision_index=2, player_id="player-b", card="CK",
                              decision_timecode=None)))
    view, state, _ = rendered(_set_game(create_match_workspace_v1(definition), game), 3, "en")
    assert [row["reason"] for row in state["decision_preparation"]["decisions"]] == [
        "required_public_hand_unavailable", "acting_hand_unavailable"]
    review = render_match_analysis_v1(state, view, "a" * 64, "en")
    assert "#match-initial-hand" not in review
    # Original ten dealt Cards alone are insufficient after declarer pickup/discard.
    game = _observed_game(definition, match_position=3, perspective_initial_hand=hand,
        declarer_player_id="player-a", declaration=GameDeclaration(game_type="grand"),
        plays=(ObservedPlayV1(decision_index=1, player_id="player-a", card="C7",
                              decision_timecode=None),))
    view, state, _ = rendered(_set_game(create_match_workspace_v1(definition), game), 3, "en")
    assert state["decision_preparation"]["decisions"][0]["reason"] == "acting_hand_unavailable"
    assert "#match-initial-hand" not in render_match_analysis_v1(state, view, "a" * 64, "en")


@pytest.mark.parametrize("owner", (None, "foreign-player", "", True))
def test_defensive_missing_owner_has_no_named_destination(owner):
    view, state, _ = rendered(workspace_for((3,)), 1, "en")
    state["hand_editor_player_id"] = owner
    assert "#match-initial-hand" not in render_match_analysis_v1(state, view, "a" * 64, "en")
    assert 'id="match-initial-hand"' not in render_task_first_match_v1(
        state, view, managed_handle="a" * 64, locale="en")


def test_only_owner_skips_trigger_remedy_and_rendering_is_passive(monkeypatch):
    import skatmind.app_web.task_first_match_state as page_state
    view, state, _ = rendered(workspace_for((6,)), 1, "en")
    before = deepcopy(state)
    def forbidden(*args, **kwargs):
        raise AssertionError("Rendering must reuse the captured facts")
    monkeypatch.setattr(page_state, "_decision_preparation_summary", forbidden)
    render_task_first_match_v1(state, view, managed_handle="a" * 64, locale="en")
    render_match_analysis_v1(state, view, "a" * 64, "en")
    assert state == before
    # Defensive scalar projection isolates eligibility from labels and aggregate counts.
    for row in state["decision_preparation"]["decisions"]:
        if row["acting_player_id"] == "player-a":
            row.update(state="prepared", reason=None)
    assert "#match-initial-hand" not in render_match_analysis_v1(state, view, "a" * 64, "en")


def test_real_other_game_report_cannot_supply_remedy_owner_or_destination(localized_server):
    browser = Browser(localized_server)
    record_context_match(browser, with_hand=False)
    record_second_context_game(browser)
    page = browser.page("/matches/review/4")
    follow(browser, browser.submit(operation_form(page, "analyze_decision")))
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    saved, retained = active.path.read_bytes(), canonical(report.to_dict())
    view = project_task_first_match_v1(active.workspace, selected_position=1)
    with active.capture.lock:
        state = build_task_first_match_page_state_v1(active, view, report_id=report.report_id)
    assert state["game"]["perspective_initial_hand"] is None
    assert state["selected_report"] is not None and report.match_position == 4
    html = render_match_analysis_v1(state, view, active.handle, "en")
    assert html.count('href="/matches/position/1#match-initial-hand"') == 1
    assert '>Enter known initial hand for C</a>' in html
    assert "/matches/position/4" not in html
    assert active.path.read_bytes() == saved and canonical(report.to_dict()) == retained


def test_returned_remedy_retry_save_review_lifecycle_and_frozen_session(
    localized_server, monkeypatch,
):
    import skatmind.capture_web.analysis as analysis
    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    record_live_game(browser, play_count=3)
    review_first(browser)
    session = localized_server.app_context.managed_stateful.active_session
    session_disk, checkpoints = session.path.read_bytes(), session.decision_checkpoints
    session_exports = {kind: browser.request("GET", f"/sessions/downloads/{kind}.json")[2]
                       for kind in ("request", "result")}
    page = record_context_match(browser, with_hand=False)
    active = localized_server.app_context.managed_stateful.active_match
    original = active.path.read_bytes()
    saves, executions = [], []
    real_save = capture.save_match_workspace_file_v1
    real_execute = analysis.execute_match_decision_analysis_v1
    def save(*args, **kwargs):
        saves.append(args)
        return real_save(*args, **kwargs)
    def execute(*args, **kwargs):
        executions.append(args)
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    monkeypatch.setattr(analysis, "execute_match_decision_analysis_v1", execute)
    assert_party_score(page, (0, 0), (14, 1))
    view = project_task_first_match_v1(active.workspace, selected_position=1)
    third_actor = active.workspace.slots[0].observed_game.plays[2].player_id
    assert view.selected.next_player_id == third_actor
    page = browser.page("/matches/review/1")
    assert "0 of 3" in page
    href, = re.findall(r'href="([^"]+#match-initial-hand)"', page)
    page = browser.page(urlsplit(href).path)
    form = operation_form(page, "set_perspective_hand")
    assert set(form["values"]) == {
        "managed_handle", "operation", "card_selection", "card_evidence_mode",
        "_frontend_form_instance"}
    status, _, body = browser.submit(form, card_evidence_mode="exact", cards=["C7"])
    assert status == 400
    page = body.decode()
    assert 'autofocus' in page and 'aria-invalid="true"' in page
    assert 'href="#validation-field-' in page and 'id="match-initial-hand"' in page
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    assert "Anfangshand von C" in page
    retry = operation_form(page, "set_perspective_hand")
    assert retry["values"]["cards"] == "C7"
    assert active.path.read_bytes() == original and not saves and not executions
    response = browser.submit(retry, card_evidence_mode="exact", cards=MATCH_HAND)
    assert response[1]["location"] == "/matches/position/1#match-recording"
    page = follow(browser, response)
    assert len(saves) == 1 and not executions
    saved = active.path.read_bytes()
    assert active.workspace.slots[0].observed_game.perspective_initial_hand == MATCH_HAND
    assert_party_score(page, (0, 0), (14, 1))
    assert 'href="/matches/review/1"' in page
    page = browser.page("/matches/review/1")
    assert "1 von 3" in page and "#match-initial-hand" not in page
    form = operation_form(page, "analyze_decision")
    assert form["values"]["decision_index"] == "2"
    page = follow(browser, browser.submit(form))
    assert len(executions) == 1 and len(saves) == 1
    report, = active.capture.report_store.list()
    assert_context(page, "de", hand=MATCH_HAND, prefix=(("B", "CK"),), actor="C",
                   trick=1, play=2, game=1)
    result = report.value.result.document
    assert result["position"]["current_trick"] == ("CK",)
    assert result["position"]["hand"] == MATCH_HAND
    retained = canonical(report.to_dict())
    download_route = f"/matches/api/v1/reports/{report.report_id}.json"
    download = browser.request("GET", download_route)[2]
    page = browser.page(urlsplit(href).path)
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand")))
    assert active.path.read_bytes() == saved and len(saves) == 1
    assert canonical(active.capture.report_store.list()[0].to_dict()) == retained
    page = follow(browser, browser.submit(entry_action(page, 2)))
    selection = active.recovery.selected
    for locale in ("en", "de"):
        page = browser.page("/matches/review/1")
        page = browser.page(urlsplit(href).path)
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert active.recovery.selected is selection
        assert browser.request("GET", download_route)[2] == download
        assert canonical(active.capture.report_store.list()[0].to_dict()) == retained
    stale = operation_form(page, "set_perspective_hand")
    browser.page("/matches/position/2")
    assert active.recovery.selected is None
    status, _, body = browser.submit(stale)
    assert status == 409
    assert 'id="match-evidence"' not in body.decode()
    assert 'href="#match-recording"' in body.decode()
    assert 'id="match-recording"' in body.decode() and "autofocus" in body.decode()
    assert active.workspace.slots[1].observed_game is None and active.path.read_bytes() == saved
    assert browser.request("GET", download_route)[2] == download
    assert session.path.read_bytes() == session_disk and session.decision_checkpoints == checkpoints
    for kind, raw in session_exports.items():
        assert browser.request("GET", f"/sessions/downloads/{kind}.json")[2] == raw
    assert len(saves) == len(executions) == 1
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
    page = browser.page("/matches/position/1")
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/reload")))
    assert active.path.read_bytes() == saved and not active.capture.report_store.list()
    assert set(operation_form(page, "set_perspective_hand")["values"]["cards"]) == set(MATCH_HAND)
