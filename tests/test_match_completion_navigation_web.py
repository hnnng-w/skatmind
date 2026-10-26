"""Completion actions in delivered HTML, over canonical disposable Match records."""

import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_declaration_drafts import NativePage
from test_match_game_navigation import workspace_for
from test_match_recording_recovery_web import entry_action, follow
from test_match_workspace_contracts import _definition, _observed_game, _seat_order
from test_null_recording_end_web import record_null_match_prefix
from test_observed_game_contracts import declaration_from_historical, observed_plays_from_historical
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import (
    mark_match_workspace_passed_deal_v1,
    set_match_workspace_observed_game_v1,
)
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def completion_workspace():
    """The named 29-Play reproduction, derived from the valid historical example."""
    data = json.loads((Path(__file__).resolve().parents[1] / "examples" /
        "historical_grand_normal_completion.json").read_text())["historical_game_input"]
    definition = _definition(title="UAT Spielende 01")
    seats = _seat_order(definition, 1)
    mapping = dict(zip(("player-a", "player-b", "player-c"), seats, strict=True))
    labels = dict(zip(seats, ("Anna", "Bea", "Clara"), strict=True))
    definition = replace(definition, perspective_player_id=seats[0], participants=tuple(
        replace(p, player_label=labels[p.player_id]) for p in definition.participants))
    game = _observed_game(definition, game_timecode=None,
        perspective_initial_hand=data["players"][0]["initial_hand"],
        declarer_player_id=seats[1], declaration=declaration_from_historical(data),
        original_skat=data["skat"], discarded_cards=data["discarded_cards"],
        plays=tuple(replace(p, player_id=mapping[p.player_id])
                    for p in observed_plays_from_historical(data)[:29]))
    return set_match_workspace_observed_game_v1(create_match_workspace_v1(definition), game,
                                                expected_revision=0).workspace


def open_workspace(server, workspace, *, selected=1, locale="en"):
    path = server.app_context.managed_stateful.root("matches") / "completion-navigation.json"
    assert save_match_workspace_file_v1(path, build_match_workspace_persistence_document_v1(
        workspace), expected_content_fingerprint=None).status == "saved"
    browser = Browser(server)
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                         language=locale))
    return browser, browser.page(f"/matches/position/{selected}")


def recording_links(page):
    return Hierarchy(page).within("match-recording", "a")


def assert_upper_navigation(page, target, locale, *, review=None):
    tree = Hierarchy(page)
    links = tree.within("match-recording", "a")
    continuation = [a for a in links if a["attrs"].get("href", "").startswith(
        "/matches/position/")]
    assert len(continuation) == int(target is not None)
    seats = next(n for n in tree.nodes if n["tag"] == "dl"
                 and n["attrs"].get("class") == "match-game-seats")
    status = next(n for n in tree.nodes if n["attrs"].get("class") == "match-recording-status")
    if target is not None:
        anchor, = continuation
        assert anchor["attrs"]["href"] == f"/matches/position/{target}#match-recording"
        assert anchor["text"] == (f"Spiel {target} öffnen" if locale == "de"
                                  else f"Open Game {target}")
        assert text(locale, "task.match.next") in page
        assert tree.visible(anchor) and not any(p["tag"] == "form" for p in anchor["parents"])
        assert not {"autofocus", "role", "onclick"} & anchor["attrs"].keys()
    else:
        assert text(locale, "task.match.all_complete") in page
    overview, = [a for a in links if a["attrs"].get("href") == "#match-games"]
    upper = [overview, *continuation]
    reviews = [a for a in links if a["attrs"].get("href", "").startswith("/matches/review/")]
    assert len(reviews) == int(review is not None)
    if review is not None:
        assert reviews[0]["text"] == review
        upper += reviews
    for anchor in upper:
        assert tree.nodes.index(status) < tree.nodes.index(anchor) < tree.nodes.index(seats)
    return continuation[0]["attrs"]["href"] if continuation else None


@pytest.mark.parametrize("locale", ("de", "en"))
def test_named_final_card_stays_selected_then_native_continuation_only_navigates(
    localized_server, monkeypatch, locale,
):
    import skatmind.app_web.frontend_profile_operations as profile
    import skatmind.app_web.match_frontend as frontend
    import skatmind.app_web.profile_driven_creation as creation
    import skatmind.capture_web.context as capture

    browser, page = open_workspace(localized_server, completion_workspace(), locale=locale)
    active = localized_server.app_context.managed_stateful.active_match
    original_revision = active.workspace.revision
    calls = []
    real_save = capture.save_match_workspace_file_v1
    def save(*args, **kwargs):
        calls.append("save")
        return real_save(*args, **kwargs)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    def forbidden(*args, **kwargs):
        pytest.fail("Navigation must not mutate, generate identities, analyze or prepare")
    for module, name in ((frontend, "execute_unified_match_analysis_v1"),
                         (profile, "save_frontend_profile_file_v1"),
                         (creation, "generate_frontend_match_id_v1"),
                         (creation, "generate_frontend_player_id_v1")):
        monkeypatch.setattr(module, name, forbidden)
    response = browser.submit(Forms(page).find("/matches/cards"), cards="D9")
    assert response[1]["location"] == "/matches/position/1#match-recording"
    page = follow(browser, response)
    assert calls == ["save"] and active.workspace.revision == original_revision + 1
    assert active.selected_position == 1
    assert len(active.workspace.slots[0].observed_game.plays) == 30
    assert all(page.count(f'id="match-play-{n}"') == 1 for n in range(1, 31))
    assert 'action="/matches/cards"' not in page
    target = assert_upper_navigation(page, 2, locale,
                                    review=text(locale, "recordings.match.open", number=1))
    assert page.index(target) < page.index('id="match-evidence"') < page.index('id="match-play-1"')
    # The enabled hidden declaration default remains first among associated submitters.
    native = NativePage(page)
    default = native.button("set_declaration")
    owner = native.owner(default)
    assert "hidden" in default and "disabled" not in default
    assert next(c for c in native.controls if c["tag"] == "button"
                and native.owner(c) is owner) is default
    saved, workspace = active.path.read_bytes(), active.workspace
    generation = active.position_generation
    monkeypatch.setattr(frontend, "apply_unified_match_operation_v1", forbidden)
    page = browser.page(urlsplit(target).path)
    assert active.selected_position == 2 and active.position_generation == generation + 1
    assert active.workspace is workspace and active.path.read_bytes() == saved and calls == ["save"]
    assert active.workspace.slots[1].observed_game is None
    tree = Hierarchy(page)
    seats = next(n for n in tree.nodes if n["attrs"].get("class") == "match-game-seats")
    assert [n["text"] for n in tree.nodes if n["tag"] == "dd"
            and any(p is seats for p in n["parents"])] == ["Bea", "Clara", "Anna"]
    assert tree.by_id("match-recording-perspective")["text"].endswith(": Anna")
    assert not any(a["attrs"].get("href", "").startswith("/matches/review/")
                   for a in recording_links(page))
    assert not any(a["attrs"].get("href", "").startswith("/matches/position/")
                   for a in recording_links(page))
    assert Forms(page).find("/matches/api/v1/operation")["values"]["operation"] == "start_game"


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("states,selected,target", (
    (("empty", "complete"), 2, 1), (("passed",), 1, 2),
    (("passed",) * 36, 36, None), (("complete",) * 36, 36, None),
))
def test_terminal_states_use_actual_first_unfinished_or_truthful_all_terminal(
    localized_server, states, selected, target, locale,
):
    browser, page = open_workspace(localized_server, workspace_for(states),
                                   selected=selected, locale=locale)
    view = project_task_first_match_v1(
        localized_server.app_context.managed_stateful.active_match.workspace,
        selected_position=selected)
    assert view.next_position == target
    review = (text(locale, "recordings.match.open", number=selected)
              if view.selected.play_count else None)
    assert_upper_navigation(page, target, locale, review=review)
    assert text(locale, "task.match.status." + view.selected.game_state) in page
    assert (text(locale, "task.match.all_complete") in page) == (target is None)
    assert '/matches/position/37' not in page and 'action="/matches/cards"' not in page
    if target is None:
        assert page.index(text(locale, "task.match.all_complete")) < page.index(
            'class="match-game-seats"')
    assert browser.page(f"/matches/position/{selected}")


def test_rule_ended_null_keeps_short_history_and_truthful_inspection(localized_server):
    browser = Browser(localized_server)
    page = record_null_match_prefix(browser)
    page = follow(browser, browser.submit(Forms(page).find("/matches/cards"), cards="HK"))
    assert_upper_navigation(page, 2, "en", review=text("en", "recordings.match.inspect"))
    assert "Chris won trick 3. The game has ended." in page
    assert 'id="match-play-9"' in page and 'id="match-play-10"' not in page
    assert 'action="/matches/cards"' not in page
    assert text("en", "task.match.all_complete") not in page


def test_all_terminal_includes_short_null_without_claiming_full_traces(localized_server):
    browser = Browser(localized_server)
    record_null_match_prefix(browser, count=9)
    active = localized_server.app_context.managed_stateful.active_match
    workspace = active.workspace
    for position in range(2, 37):
        workspace = mark_match_workspace_passed_deal_v1(workspace, match_position=position,
            game_timecode=None, expected_revision=workspace.revision).workspace
    assert save_match_workspace_file_v1(active.path,
        build_match_workspace_persistence_document_v1(workspace),
        expected_content_fingerprint=active.capture.content_fingerprint).status == "saved"
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    assert_upper_navigation(page, None, "en", review=text("en", "recordings.match.inspect"))
    assert "Chris won trick 3. The game has ended." in page
    assert text("en", "task.match.progress_value", observed=1, complete=0, passed=35) in page
    assert text("en", "recording.null_end.match_count", count=1) in page
    assert 'id="match-play-10"' not in page


@pytest.mark.parametrize("kind,route", (
    ("empty", "/matches/api/v1/operation"), ("started", "/matches/recording-input"),
    ("partial", "/matches/cards"),
))
def test_earlier_gap_does_not_displace_selected_unfinished_task(localized_server, kind, route):
    _, page = open_workspace(localized_server, workspace_for(("empty", kind)), selected=2)
    continuation, = [a for a in recording_links(page)
                     if a["attrs"].get("href") == "/matches/position/1#match-recording"]
    assert continuation["text"] == "Open Game 1 for recording"
    assert page.index(f'action="{route}"') < page.index(continuation["text"])
    assert 'class="button-link"' not in page.split('<section id="match-games"', 1)[0]
    if kind == "partial":
        assert page.index('id="match-play-4"') < page.index(continuation["text"])


def test_genuine_rewind_removes_terminal_actions_and_restores_card_task(localized_server):
    browser, page = open_workspace(localized_server, completion_workspace())
    page = follow(browser, browser.submit(Forms(page).find("/matches/cards"), cards="D9"))
    assert_upper_navigation(page, 2, "en", review=text("en", "recordings.match.open", number=1))
    page = follow(browser, browser.submit(entry_action(page, 30, rewind=True)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                         confirm_apply="on"))
    active = localized_server.app_context.managed_stateful.active_match
    assert len(active.workspace.slots[0].observed_game.plays) == 29
    assert project_task_first_match_v1(active.workspace, selected_position=1).next_position == 1
    assert Forms(page).find("/matches/cards")
    assert text("en", "task.match.status.play_complete") not in page
    assert not any(a["attrs"].get("href", "").startswith("/matches/position/")
                   for a in recording_links(page))
    assert page.index('action="/matches/cards"') < page.index('href="#match-games"')
