import json
import re
from urllib.parse import urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_recorded_review_navigation import chooser_form, home_chooser
from test_session_recorded_review_web import Browser, Forms, record_live_game

from skatmind.app_web import session_batch_routes as routes
from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
from skatmind.app_web.saved_match_analyses import SELECTION_ROUTE, archive_store
from skatmind.automatic_learning_store import StoreConflictError


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def test_native_scope_progress_original_selection_language_and_foreign_return(
        localized_server, monkeypatch):
    import skatmind.app_web.execution as executor

    calls = []
    real = executor.execute
    def counted(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(executor, "execute", counted)
    app = localized_server.app_context
    browser = Browser(localized_server)
    assert 'href="/sessions"' in browser.page("/live-play")
    record_live_game(browser, play_count=6)
    active = app.managed_stateful.active_session
    original = active.path.read_bytes()
    mode = active.state.capture_mode
    browser.page("/record-after")
    recording = browser.page()
    assert 'action="/sessions/live-start"' not in recording
    assert 'action="/sessions/review-whole-game"' not in recording
    assert 'href="/sessions/decisions"' in recording
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "sessions")))
    assert mode == active.state.capture_mode == "live"
    assert 'href="/review/recorded" aria-current="page"' in page
    assert 'action="/sessions/review-whole-game"' not in page
    page = browser.page(re.search(r'href="(/sessions/game-review)"', page)[1])
    start = Forms(page).find(routes.PAGE + "/start")
    assert not calls
    status, _, rejected = browser.submit(start, random_seed="invalid", analysis_effort="quick")
    assert status == 400
    retry = Forms(rejected.decode()).find(routes.PAGE + "/start")
    assert retry["values"]["analysis_effort"] == "quick" and "retry_generation" in retry["values"]
    assert browser.submit(start)[0] == 409 and not calls
    start = retry
    assert browser.submit(start, random_seed="0", objective="played_game_goal")[0] == 303
    if worker := app.session_batch.worker:
        worker.thread.join(120)
    page = browser.page(routes.PAGE)
    watch = re.search(r'data-batch-watch="([^"]+)"', page)[1]
    assert len(calls) == 2
    store = archive_store(app)
    with monkeypatch.context() as patch:
        def forbidden(*args, **kwargs):
            pytest.fail("Status polled the evidence archive.")
        patch.setattr(store, "snapshot", forbidden)
        status, _, raw = browser.request("GET", watch + "/status")
        assert status == 200
        assert json.loads(raw)["processed"] == 2 and json.loads(raw)["phase"] == "finished"
    for page in (browser.page(watch + "/results"), browser.page(routes.OVERVIEW)):
        detail = re.search(r'href="(/sessions/saved-analyses/[^"]+/from-game/[^"]+)"', page)[1]
    page = browser.page(detail)
    downloads = {r: browser.request("GET", r)[2] for r in re.findall(
        r'href="([^"]+/(?:request|result).json)"', page)}
    assert len(downloads) == 2
    service = AutomaticMatchLearningServiceV1.open(app)
    previous = service.update().generation
    former_delivery = service.capture_delivery()
    assert len(previous.recipe.evidence_ids) == 2
    stale = Forms(page).find(SELECTION_ROUTE)
    assert browser.submit(stale)[0] == 409
    page = follow(browser, browser.submit(Forms(browser.page(detail)).find(SELECTION_ROUTE)))
    assert Forms(page).find(SELECTION_ROUTE)["values"]["choice"] == "include"
    assert service.inspect().status == "excluded"
    with pytest.raises(StoreConflictError):
        service.validate_final_delivery(former_delivery)
    assert len(service.update().generation.recipe.evidence_ids) == 1
    overview = re.search(r'href="([^"]+/overview)"', page)[1]
    returned = browser.page(overview)
    returned = follow(browser, browser.submit(Forms(returned).find("/actions/profile/language"),
                                              language="de"))
    recording_return = urlsplit(re.search(r'href="([^"]+/recording#[^"]+)"', returned)[1]).path
    review_return = re.search(r'href="([^"]+/review)"', returned)[1]
    assert 'id="recorded-decisions"' in browser.page(review_return)
    assert 'id="session-recording"' in browser.page(recording_return)
    page = follow(browser, browser.submit(Forms(browser.page(detail)).find(SELECTION_ROUTE)))
    assert Forms(page).find(SELECTION_ROUTE)["values"]["choice"] == "exclude"
    assert service.update().generation.recipe.evidence_ids == previous.recipe.evidence_ids
    assert active.path.read_bytes() == original and len(calls) == 2
    copy = active.path.with_suffix(".copy")
    copy.write_bytes(original)
    copy.replace(active.path)
    for path in (overview, recording_return, review_return, watch + "/status"):
        assert browser.request("GET", path)[0] == 409
    for route, expected in downloads.items():
        status, _, raw = browser.request("GET", route)
        assert status == 200 and raw == expected
