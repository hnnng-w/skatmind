import re

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_match_rollout_web import open_alex
from test_session_recorded_review_web import Forms

from skatmind.app_web.whole_match_routes import OVERVIEW, PAGE
from skatmind.app_web.whole_match_web import text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def test_native_controls_progress_comparison_and_original(localized_server):
    browser, _, recording = open_alex(localized_server)
    assert f'href="{PAGE}"' in recording
    page = browser.page(PAGE)
    start = Forms(page).find(PAGE + "/start")
    assert start["values"]["analysis_effort"] == "standard"
    assert "matadors_2" in start["values"]
    response = browser.submit(start, analysis_effort="quick", matadors_2="1")
    assert response[0] == 303
    app = localized_server.app_context
    worker = app.whole_match.worker
    if worker:
        worker.thread.join(60)
    assert browser.submit(start)[0] == 409
    for locale in ("de", "en"):
        page = browser.page(OVERVIEW)
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                               language=locale))
        assert text(locale, "whole_review.actual") in page and "/25" in page
        detail = re.search(r'href="(/matches/saved-analyses/[0-9a-f]{64})"', page)[1]
        original = browser.page(detail)
        assert detail + "/request.json" in original and detail + "/result.json" in original


def test_genuine_tied_best_group_includes_actual_card_in_overview(tmp_path):
    from test_match_rollout_retention import make_managed
    from test_match_workspace_contracts import _definition, _observed_game, _set_game
    from test_whole_match_job import finish, submit

    from scripts.verify_whole_match_review import synthetic_game
    from skatmind.app_web.whole_match_job import evidence_view, row_options
    from skatmind.app_web.whole_match_web import overview
    from skatmind.match_workspace_contracts import create_match_workspace_v1

    definition = _definition(perspective_player_id="player-a")
    full = synthetic_game(definition, 7)
    game = _observed_game(definition, match_position=7, declaration=full.declaration,
        declarer_player_id=full.declarer_player_id,
        perspective_initial_hand=full.perspective_initial_hand, plays=full.plays[:5])
    workspace = _set_game(create_match_workspace_v1(definition), game)
    app, active = make_managed(tmp_path / "home")
    assert active.capture.save_candidate(workspace) == "saved"
    state = finish(app, active, submit(app, active))
    rows = app.whole_match.plays(workspace)
    options = row_options(rows, state)
    with evidence_view(app, workspace, state["source"], options) as (values, space, guard):
        html = overview(app, workspace, state, rows, options, values, space, "en")
        result = values[state["refs"]["7:5"][1]].report.value.result.document
        assert set(result["whole_game_rollout_result"]["tied_best_cards"]) == {"C8", "C7"}
        assert "Clubs Eight, Clubs Seven" in html
        assert result["whole_game_rollout_comparison"]["display_order_only"]
        guard()
