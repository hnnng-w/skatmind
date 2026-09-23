"""Presentation-only navigation over canonical accepted Match views."""

import re
from dataclasses import replace
from html import escape
from types import SimpleNamespace

import pytest
from test_match_workspace_contracts import (
    _complete_observed_game,
    _definition,
    _observed_game,
    _seat_order,
)

from skatmind.app_web.match_review_rendering import render_match_review_v1
from skatmind.app_web.task_first_match_rendering import render_task_first_match_v1
from skatmind.app_web.task_first_match_state import build_task_first_match_page_state_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.capture_web.report_store import MatchAnalysisReportStoreV1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_operations import (
    mark_match_workspace_passed_deal_v1,
    set_match_workspace_observed_game_v1,
)


def workspace_for(states):
    definition = _definition()
    definition = replace(definition, participants=tuple(replace(p,
        player_label=f'<Player {i}> & "' + "Long Name " * 8 + '"')
        for i, p in enumerate(definition.participants, 1)))
    workspace = create_match_workspace_v1(definition)
    complete = _complete_observed_game(definition)
    for number, state in enumerate(states, 1):
        if state == "empty":
            continue
        if state == "passed":
            workspace = mark_match_workspace_passed_deal_v1(workspace, match_position=number,
                game_timecode=None, expected_revision=workspace.revision).workspace
            continue
        mapping = dict(zip(_seat_order(definition, 3), _seat_order(definition, number),
                           strict=True))
        game = _observed_game(definition, match_position=number,
            declaration=None if state == "started" else complete.declaration,
            declarer_player_id=None if state == "started" else mapping[complete.declarer_player_id],
            plays=tuple(replace(play, player_id=mapping[play.player_id]) for play in
                complete.plays[:30 if state == "complete" else 4 if state == "partial" else 0]))
        workspace = set_match_workspace_observed_game_v1(workspace, game,
            expected_revision=workspace.revision).workspace
    return workspace


def rendered(workspace, selected, locale):
    view = project_task_first_match_v1(workspace, selected_position=selected)
    context = SimpleNamespace(workspace=workspace,
                              capture=SimpleNamespace(report_store=MatchAnalysisReportStoreV1()))
    state = build_task_first_match_page_state_v1(context, view)
    html = render_task_first_match_v1(state, view, managed_handle="a" * 64, locale=locale)
    return view, state, html


@pytest.fixture(scope="module")
def mixed():
    return workspace_for(("complete", "passed", "started", "declaration", "partial"))


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("selected,action", ((1, None), (2, None), (3, "set_declaration"),
    (4, "append_plays"), (5, "append_plays"), (6, "start_game"), (36, "start_game")))
def test_selected_identity_controls_seats_and_single_overview(mixed, selected, action, locale):
    view, state, html = rendered(mixed, selected, locale)
    assert view.next_position == 3 and view.workflow.primary_action == action
    recording, overview = html.split('<section id="match-games"', 1)
    assert 'class="match-tile' not in recording
    heading = text(locale, "task.match.game_heading", number=selected)
    assert f'<h2 id="match-recording-heading">{heading}</h2>' in recording
    assert text(locale, "task.match.round", number=view.selected.round_number) in recording
    seats = re.search(r'<dl class="match-game-seats">(.*?)</dl>', recording, re.S)[1]
    for seat in ("forehand", "middlehand", "rearhand"):
        player = next(p for p in mixed.match_definition.participants
                      if p.player_id == getattr(view.selected, seat + "_player_id"))
        assert ('<dt>' + text(locale, "creation.seat." + seat) + '</dt><dd>'
                + escape(player.player_label) + '</dd>') in seats
    assert "<Player" not in html
    assert ('href="/matches/position/3#match-recording"' in recording) == (selected != 3)
    assert (text(locale, "task.match.first_unfinished", number=3) in recording) == (selected != 3)
    assert 'href="#match-games"' in recording
    assert (f'href="/matches/review/{selected}"' in recording) == bool(view.selected.play_count)
    for step in view.workflow.completed_steps:
        assert (text(locale, f"task.match.action.{step}") + ' — '
                + text(locale, "task.recorded")) not in recording
    if action:
        assert text(locale, view.workflow.next_task_key) not in recording
    else:
        assert recording.count(text(locale, view.workflow.next_task_key)) == 1
    assert 'aria-labelledby="match-games-heading"' in overview and 'tabindex="-1"' in overview
    assert re.findall(r'class="match-tile(?: selected)?" href="([^"]+)"', overview) == [
        f"/matches/position/{n}#match-recording" for n in range(1, 37)]
    assert overview.count('class="round-slots"') == 12
    assert html.count('aria-current="page"') == 1
    assert len(re.findall(r'\bid="([^"]+)"', html)) == len(set(re.findall(r'\bid="([^"]+)"', html)))
    if action:
        assert f'value="{action}"' in recording and recording.count('class="primary"') == 1
    else:
        assert 'class="primary"' not in recording
    if selected in (1, 5):
        assert recording.index('class="recorded-history"') > recording.index(
            'recording-progress-layout')
    if selected == 1:
        assert 'data-unplayed-cards' in recording
    if selected in (2, 6, 36):
        assert state["game"] is None and 'data-unplayed-cards' not in recording
    review = render_match_review_v1(state, view, managed_handle="a" * 64, locale=locale)
    from test_review_return_labels import assert_link
    assert_link(review, f"/matches/position/{selected}#match-recording",
        f"Zur Erfassung: Spiel {selected}" if locale == "de" else f"Recording: Game {selected}")
    assert text(locale, "task.match.position", number=selected) in review
    assert "Position " not in review


@pytest.mark.parametrize("kind,next_position,observed,complete,passed", (
    ("empty", 1, 0, 0, 0), ("started", 1, 36, 0, 0),
    ("passed", None, 0, 0, 36), ("complete", None, 36, 36, 0)))
@pytest.mark.parametrize("locale", ("en", "de"))
def test_recording_completion_is_not_occupancy(
    kind, next_position, observed, complete, passed, locale,
):
    workspace = workspace_for((kind,) * 36)
    view, state, html = rendered(workspace, 2, locale)
    assert view.next_position == next_position
    assert state["progress"]["status"] == ("empty" if kind == "empty" else "complete")
    assert text(locale, "task.match.progress_value", observed=observed,
                complete=complete, passed=passed) in html
    assert (text(locale, "task.match.all_complete") in html) == (next_position is None)
    assert (text(locale, "task.match.first_unfinished", number=1) in html) == (next_position == 1)
    assert view.selected_position == 2
