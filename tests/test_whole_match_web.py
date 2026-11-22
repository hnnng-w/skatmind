import re
from html import unescape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_match_rollout_web import open_alex
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Forms

from skatmind.app_web.stateful_localization import card_name, text
from skatmind.app_web.whole_match_routes import OVERVIEW, PAGE


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def test_invalid_start_recovers_in_both_languages_without_work(localized_server, monkeypatch):
    from test_match_workspace_contracts import _observed_game, _set_game

    import skatmind.application.execution as executor
    import skatmind.capture_web.context as capture
    from skatmind.app_web.whole_match_job import progress_file

    browser, recording, _ = open_alex(localized_server, bid=None)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    workspace = active.workspace
    game = workspace.slots[1].observed_game
    second = _observed_game(workspace.match_definition, match_position=5,
        plays=game.plays, declaration=game.declaration, declarer_player_id=game.declarer_player_id,
        perspective_initial_hand=game.perspective_initial_hand)
    assert active.capture.save_candidate(_set_game(workspace, second)) == "saved"
    original = recording.read_bytes()
    monkeypatch.setattr(capture, "save_match_workspace_file_v1",
                        lambda *a, **kw: pytest.fail("Review form saved the recording"))
    checkpoint = progress_file(app, active)
    start = Forms(browser.page(PAGE)).find(PAGE + "/start")
    calls = []
    execute = executor.execute_application_invocation
    def counted(invocation, **options):
        calls.append(invocation)
        return execute(invocation, **options)
    monkeypatch.setattr(executor, "execute_application_invocation", counted)
    status, _, raw = browser.submit(start, analysis_effort="quick", matadors_2="0",
                                    bid_value_2="24", bid_value_5="36", random_seed="19")
    assert status == 400
    page = raw.decode()
    # Before a job exists the direct overview URL also offers the Start form.
    direct = Forms(browser.page(OVERVIEW)).find(PAGE + "/start")
    assert direct["values"]["retry_generation"] == Forms(page).find(PAGE + "/start")[
        "values"]["retry_generation"]
    for locale in (None, "de", "en"):
        if locale is not None:
            language = Forms(page).find("/actions/profile/language")
            assert language["values"]["return_to"] == PAGE
            page = follow(browser, browser.submit(language, language=locale))
        locale = locale or "en"
        for recovered in (page, browser.page(PAGE)):
            restored = Forms(recovered).find(PAGE + "/start")["values"]
            assert (restored["analysis_effort"], restored["objective"],
                    restored["random_seed"], restored["bid_value_2"], restored["matadors_2"]) == (
                        "quick", "complete_settlement", "19", "24", "0")
            assert restored["bid_value_5"] == "36" and restored["matadors_5"] == ""
            assert re.search(r'<input\b(?=[^>]*name="matadors_2")(?=[^>]*aria-invalid="true")',
                             recovered)
            assert text(locale, "validation.rollout.invalid_matadors_suit") in unescape(recovered)
            field = next(n for n in Hierarchy(recovered).nodes
                         if n["attrs"].get("name") == "matadors_2")
            assert all("open" in p["attrs"] for p in field["parents"] if p["tag"] == "details")
        assert checkpoint.read() is None and app.whole_match.worker is None and not calls
        assert recording.read_bytes() == original and not (app.managed_home.root /
                                                           "automatic-learning").exists()
    assert browser.submit(Forms(page).find(PAGE + "/start"), matadors_2="1")[0] == 303
    worker = app.whole_match.worker
    if worker:
        worker.thread.join(60)
    saved = checkpoint.read()
    assert saved["phase"] == "finished" and len(calls) == 1
    assert saved["settings"]["requested_worlds"] == 25 and saved["settings"]["random_seed"] == 19
    assert saved["supplements"] == {"2": {"bid_value": 24, "matadors": 1}, "5": {"bid_value": 36}}


def test_seed_is_optional_and_technical(localized_server):
    from skatmind.app_web.whole_match_job import progress_file

    browser, _, _ = open_alex(localized_server)
    page = browser.page(PAGE)
    seed, = (node for node in Hierarchy(page).nodes if node["attrs"].get("name") == "random_seed")
    assert any(p["tag"] == "details" and "open" not in p["attrs"] for p in seed["parents"])
    assert "required" not in seed["attrs"]
    start = Forms(page).find(PAGE + "/start")
    del start["values"]["random_seed"]
    assert browser.submit(start)[0] == 303
    app = localized_server.app_context
    worker = app.whole_match.worker
    if worker:
        worker.thread.join(60)
    state = progress_file(app, app.managed_stateful.active_match).read()
    assert state["settings"]["random_seed"] == 0


@pytest.mark.parametrize(("field", "value", "key"), [
    ("random_seed", str(2**64), "validation.rollout.invalid_random_seed"),
    ("analysis_effort", "unsupported", "validation.message.choice"),
])
def test_invalid_setting_marks_the_control_and_preserves_nondefault_objective(
        localized_server, field, value, key):
    browser, _, _ = open_alex(localized_server)
    start = Forms(browser.page(PAGE)).find(PAGE + "/start")
    status, _, raw = browser.submit(start, objective="played_game_goal", **{field: value})
    assert status == 400
    page = raw.decode()
    assert text("en", key) in unescape(page)
    control = next(n for n in Hierarchy(page).nodes if n["attrs"].get("name") == field)
    assert control["attrs"]["aria-invalid"] == "true"
    assert all("open" in p["attrs"] for p in control["parents"] if p["tag"] == "details")
    assert Forms(page).find(PAGE + "/start")["values"]["objective"] == "played_game_goal"


@pytest.mark.parametrize("change", ["replace", "correct", "supersede"])
def test_stale_retry_neither_restores_values_nor_starts_review(localized_server, change, tmp_path):
    from test_match_evidence_retention import change_source

    from skatmind.app_web.whole_match_job import progress_file

    browser, recording, _ = open_alex(localized_server)
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    start = Forms(browser.page(PAGE)).find(PAGE + "/start")
    status, _, raw = browser.submit(start, analysis_effort="quick", matadors_2="0")
    assert status == 400
    rejected = Forms(raw.decode())
    retry = rejected.find(PAGE + "/start")
    language = rejected.find("/actions/profile/language")
    if change == "replace":
        new = tmp_path / "identical.json"
        new.write_bytes(recording.read_bytes())
        new.replace(recording)
    elif change == "correct":
        change_source(active)
    else:
        status, _, raw = browser.submit(retry, random_seed="bad", analysis_effort="more_time")
        assert status == 400
        assert text("en", "validation.rollout.invalid_random_seed") in raw.decode()
    before = recording.read_bytes()
    assert browser.submit(language, language="de")[0] == 409
    for value in ("0", "2"):
        status, _, raw = browser.submit(retry, matadors_2=value)
        assert status == 409 and PAGE + "/start" not in raw.decode()
    if change == "supersede":
        current = Forms(browser.page(PAGE)).find(PAGE + "/start")
        assert current["values"]["analysis_effort"] == "more_time"
        assert current["values"]["random_seed"] == "bad"
    elif change == "replace":
        current = Forms(browser.page(PAGE)).find(PAGE + "/start")
        assert current["values"]["analysis_effort"] == "standard"
        assert current["values"]["matadors_2"] == ""
    assert recording.read_bytes() == before
    assert app.whole_match.worker is None and progress_file(app, active).read() is None
    assert not (app.managed_home.root / "automatic-learning").exists()


def test_native_controls_progress_comparison_and_original(localized_server):
    from skatmind.app_web.whole_match_job import progress_file

    browser, _, recording = open_alex(localized_server, count=18)
    assert f'href="{PAGE}"' in recording
    page = browser.page(PAGE)
    start = Forms(page).find(PAGE + "/start")
    assert start["values"]["analysis_effort"] == "standard"
    assert "matadors_2" in start["values"]
    response = browser.submit(start, analysis_effort="quick", objective="played_game_goal")
    assert response[0] == 303
    app = localized_server.app_context
    worker = app.whole_match.worker
    if worker:
        worker.thread.join(60)
    assert browser.submit(start)[0] == 409
    active = app.managed_stateful.active_match
    checkpoint = progress_file(app, active)
    state = checkpoint.read()
    archive = app.managed_home.root / "automatic-learning"
    manifest = (archive / "manifest.json").read_bytes()
    invalid = Forms(browser.page(PAGE)).find(PAGE + "/start")
    status, _, raw = browser.submit(invalid, objective="invalid-objective", analysis_effort="quick")
    assert status == 400 and text("en", "validation.rollout.invalid_objective") in raw.decode()
    assert app.whole_match.worker is None and checkpoint.read() == state
    assert (archive / "manifest.json").read_bytes() == manifest
    for locale in ("de", "en"):
        page = browser.page(OVERVIEW)
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                               language=locale))
        first = next(r for r in re.findall("<tr>(.*?)</tr>", unescape(page), re.S)
                     if '<th scope="row">3</th>' in r)
        cells = re.findall(r"<td>(.*?)</td>", first)
        assert cells[1] == text(locale, "rollout.number.success", successes=21, samples=25,
                                percentage="84")
        assert cells[3] == text(locale, "rollout.number.success", successes=22, samples=25,
                                percentage="88")
        forced = next(r for r in re.findall("<tr>(.*?)</tr>", page, re.S)
                      if text(locale, "whole_review.forced") in r)
        assert "%" not in forced
        secondary = next(r for r in re.findall("<tr>(.*?)</tr>", page, re.S)
                         if '<th scope="row">15</th>' in r)
        assert "1284/25" in secondary and "1386/25" in secondary and secondary.count("%") == 2
        detail = re.search(r'href="(/matches/saved-analyses/[0-9a-f]{64})"', page)[1]
        original = browser.page(detail)
        assert detail + "/request.json" in original and detail + "/result.json" in original


def test_retained_timeout_has_coverage_but_no_success_percentage(localized_server, monkeypatch):
    import skatmind.recommendation_workflow as workflow

    browser, _, _ = open_alex(localized_server)
    real = workflow.evaluate_whole_game_rollout_v1
    def timed(*args, **kw):
        ticks = iter(range(0, 1000000, 100))
        return real(*args, clock=lambda: next(ticks), **kw)
    monkeypatch.setattr(workflow, "evaluate_whole_game_rollout_v1", timed)
    start = Forms(browser.page(PAGE)).find(PAGE + "/start")
    assert browser.submit(start, analysis_effort="quick", objective="played_game_goal")[0] == 303
    worker = localized_server.app_context.whole_match.worker
    if worker:
        worker.thread.join(60)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(browser.page(OVERVIEW)).find(
            "/actions/profile/language"), language=locale))
        row, = re.findall(r'<tr><th scope="row">3</th>(.*?)</tr>', page)
        assert text(locale, "rollout.reason.wall_clock_timeout") in unescape(row)
        assert "/25)" in row and "%" not in row and "/saved-analyses/" in row


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
    workspace = _set_game(workspace, synthetic_game(definition, 33))
    app, active = make_managed(tmp_path / "home")
    assert active.capture.save_candidate(workspace) == "saved"
    state = finish(app, active, submit(app, active))
    rows = app.whole_match.plays(workspace)
    options = row_options(rows, state)
    with evidence_view(app, workspace, state["source"], options) as (values, space, guard):
        result = values[state["refs"]["7:5"][1]].report.value.result.document
        assert set(result["whole_game_rollout_result"]["tied_best_cards"]) == {"C8", "C7"}
        for locale in ("en", "de"):
            html = overview(app, workspace, state, rows, options, values, space, locale)
            tie = re.search(r'<th scope="row">5</th>(.*?)</tr>', html)[1]
            assert ", ".join(card_name(locale, c) for c in ("C8", "C7")) in tie
            assert tie.count("%") == 2
            unsupported = html.split('id="game-33"', 1)[1].split("</section>", 1)[0]
            assert text(locale, "rollout.reason.unsupported_game_type") in unsupported
            assert "%" not in unsupported and "/saved-analyses/" not in unsupported
        assert result["whole_game_rollout_comparison"]["display_order_only"]
        guard()
