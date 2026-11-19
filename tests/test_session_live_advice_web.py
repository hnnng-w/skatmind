"""Native accepted input, unlocked current-position advice and final delivery."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from test_compact_card_entry_web import create_live
from test_frontend_language_switching import localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import (
    Browser,
    Forms,
    record_live_game,
    record_score_review_game,
)

import skatmind.api.v1.session.files as files
import skatmind.app_web.execution as execution
from skatmind.app_web import session_live_advice as live
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
from skatmind.app_web.session_recorded_review import project_recorded_session_decisions_v1
from skatmind.app_web.stateful_localization import card_name, text
from skatmind.deck import get_full_deck

__all__ = ["localized_server"]
START, EFFORT, STOP = live.LIVE_ROUTES


def post(browser, route, page=None, **kwargs):
    return browser.submit(Forms(page or browser.page()).find(route), **kwargs)


def watch(monkeypatch):
    real, calls = execution.execute, []

    def counted(request, **kwargs):
        calls.append(request)
        return real(request, **kwargs)

    monkeypatch.setattr(execution, "execute", counted)
    return calls


def test_compact_declaration_first_advice_and_stale_generic_form(localized_server, monkeypatch):
    browser = Browser(localized_server)
    hand = create_live(browser)
    calls = watch(monkeypatch)
    follow(browser, post(browser, START))
    follow(browser, browser.submit(hand, cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    page = browser.page()
    current = Forms(page).find("/sessions/command", kind="set_declaration")
    page = follow(browser, browser.submit(current, game_type="grand", hand_game="true"))
    active = localized_server.app_context.managed_stateful.active_session
    assert len(calls) == 1 and 'id="live-recommendation"' in page
    old = Forms(page).find("/sessions/undo")
    follow(browser, post(browser, "/sessions/open", browser.page("/sessions")))
    owner = localized_server.app_context.managed_stateful.active_session
    assert owner is not active and owner.generation == 1 and owner.document == active.document
    follow(browser, post(browser, START))
    before = owner.live.outcome
    assert browser.submit(old, target_revision="0")[0] == 409
    assert len(calls) == 2 and owner.live.outcome is before
    follow(browser, post(browser, "/sessions/undo", target_revision="0"))
    assert owner.state.revision == 0 and owner.live.effort is owner.live.outcome is None
    assert len(calls) == 2


def test_activation_before_setup_then_discard_and_generic_play(localized_server, monkeypatch):
    browser = Browser(localized_server)
    hand = create_live(browser)
    active = localized_server.app_context.managed_stateful.active_session
    calls = watch(monkeypatch)
    start = Forms(browser.page()).find(START)
    follow(browser, browser.submit(start))
    assert active.state.revision == 0 and active.live.effort == "quick"
    assert browser.submit(start)[0] == 409
    assert browser.submit(hand, cards=["CA", "CA"])[0] == 400
    follow(browser, browser.submit(hand, cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="false")
    follow(browser, post(browser, "/sessions/cards", cards=["D7", "H7"]))
    assert not calls
    page = follow(browser, post(browser, "/sessions/cards", cards=["D7", "CA"]))
    assert 'id="live-recommendation"' in page
    assert len(calls) == len(active.decision_checkpoints) == 1
    original = active.live.outcome
    assert calls[0].document["sample_count"] == 25 and calls[0].document["random_seed"] == 0
    assert calls[0].document["analysis_mode"] == "live_decision"
    assert active.execution is None and active.pending_evidence is None
    assert not active.analysis_forms and active.recorded_review_source is None
    for locale in ("de", "en"):
        page = follow(browser, post(browser, "/actions/profile/language", page, language=locale))
        assert text(locale, "analysis.live.active") in page
        assert 'id="live-recommendation"' in page
    assert len(calls) == 1 and active.live.outcome is original
    page = follow(browser, post(browser, EFFORT, page, analysis_effort="standard"))
    assert calls[-1].document["sample_count"] == 100
    # The specialist form has its own authority. Compare the full equivalent Quick result.
    page = follow(browser, post(browser, "/sessions/analyze", page, analysis_effort="quick"))
    assert active.execution.result_json_bytes == original.result_json_bytes
    before = active.execution
    page = follow(browser, post(browser, EFFORT, page, analysis_effort="more_time"))
    assert active.execution is before and calls[-1].document["sample_count"] == 400
    assert browser.request("GET", "/sessions/downloads/result.json")[2] == before.result_json_bytes
    count = len(calls)
    # A generic accepted own Play leaves another player next.
    response = browser.request("POST", "/sessions/command", {"managed_handle": active.handle,
        "expected_revision": str(active.state.revision), "kind": "record_play",
        "player_id": active.state.local_player_id, "card": "C10"})
    page = follow(browser, response)
    assert 'id="live-recommendation"' not in page and len(calls) == count
    assert active.live.effort == "more_time" and not active.analysis_forms
    assert project_recorded_session_decisions_v1(active).local_play_count == 1
    old_stop = Forms(page).find(STOP)
    follow(browser, browser.submit(old_stop))
    assert active.live.effort is None
    follow(browser, post(browser, START))
    assert active.live.effort == "quick" and len(calls) == count
    assert browser.submit(old_stop)[0] == 409 and active.live.effort == "quick"


def test_post_save_failure_is_not_a_recording_failure(localized_server, monkeypatch):
    browser = Browser(localized_server)
    calls = watch(monkeypatch)
    _, plays = record_live_game(browser, play_count=3)
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.capture_mode == "live" and not calls and active.live.effort is None
    page = follow(browser, post(browser, START))
    form = Forms(page).find("/sessions/play")
    before = active.document
    with monkeypatch.context() as patch:
        def fail_save(*args, **kwargs):
            raise OSError("Injected save failure")
        patch.setattr(files, "save_session_file", fail_save)
        assert browser.submit(form, cards=plays[3]["card"])[0] == 409
        assert active.document is before and not calls
    persisted = []
    def fail(request, **kwargs):
        persisted.append(files.load_session_file(active.path).value.document)
        raise RuntimeError("Injected analysis failure")
    monkeypatch.setattr(execution, "execute", fail)
    # The generic command route can bring the perspective player to act.
    page = follow(browser, browser.request("POST", "/sessions/command", {
        "kind": "record_play", "managed_handle": active.handle,
        "expected_revision": str(active.state.revision),
        "player_id": active.state.players[2].player_id,
        "card": plays[3]["card"]}))
    assert persisted == [active.document] and active.state.revision == before.state.revision + 1
    assert active.decision_checkpoints[-1].source_revision == active.state.revision
    assert text("en", "analysis.live.unavailable") in page
    assert 'id="live-recommendation"' not in page
    assert Forms(page).find("/sessions/review-decision")
    follow(browser, post(browser, "/sessions/open", browser.page("/sessions")))
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened is not active and reopened.document == persisted[0]
    assert reopened.live.effort is None and len(persisted) == 1


def test_equal_best_cards_use_current_trick_objective(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=11)
    page = follow(browser, post(browser, START))
    advice = page.split('id="live-recommendation"', 1)[1].split("</div>", 1)[0]
    cards = ", ".join(card_name("en", card) for card in ("CJ", "SJ"))
    assert text("en", "analysis.live.best", cards=cards) in advice
    assert text("en", "result.point_swing") + ": 6.00" in advice
    assert "%" not in advice and text("en", "result.alternatives") not in advice


def test_forced_final_turn_completion_and_undo(localized_server, monkeypatch):
    from test_forced_card_guidance import current_session
    from whole_game_review_fixtures import ten_decision_document

    active = current_session(localized_server)
    browser = Browser(localized_server)
    calls = watch(monkeypatch)
    before = active.path.read_bytes()
    page = follow(browser, post(browser, START))
    forced = 'id="forced-card-guidance"'
    assert forced in page and active.live.outcome.card == "S10"
    assert active.path.read_bytes() == before and not active.decision_checkpoints
    state = ten_decision_document(bid_value=18).state
    for record in state.command_log[active.state.revision:]:
        page = follow(browser, post(browser, "/sessions/play", page, cards=record.command.card))
        assert forced not in page and 'id="live-recommendation"' not in page
    ending = Forms(page).find("/sessions/command", kind="set_game_end")
    page = follow(browser, browser.submit(ending))
    assert active.state.phase == "ended" and active.live.outcome is None
    page = follow(browser, post(browser, "/sessions/undo", page,
                                target_revision=str(state.revision - 3)))
    assert forced in page and not calls and active.execution is None


@pytest.mark.parametrize("change", ["stop", "reopen", "undo", "correction", "effort", "reject",
                                     "external_restore"])
def test_slow_attempt_cannot_overwrite_newer_advice_or_feedback(
        localized_server, monkeypatch, change):
    browser = Browser(localized_server)
    _, plays = record_live_game(browser, play_count=3)
    app = localized_server.app_context
    active = app.managed_stateful.active_session
    before = active.document
    page = follow(browser, post(browser, START))
    entered, release = Event(), Event()
    real, calls = live.execute_guided_frontend_analysis_v1, []

    def paused(request, **kwargs):
        calls.append(request)
        if len(calls) == 1:
            entered.set()
            assert release.wait(30)
            raise ValueError("Older attempt failed")
        return real(request, **kwargs)

    monkeypatch.setattr(live, "execute_guided_frontend_analysis_v1", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(post, browser, "/sessions/play", page, cards=plays[3]["card"])
        try:
            assert entered.wait(15)
            # These acquisitions are on a different thread than the real native POST.
            for lock in (active.lock, app.lock, app.managed_stateful.session_lifecycle_lock):
                assert lock.acquire(timeout=1)
                lock.release()
            page = browser.page()
            if change == "stop":
                follow(browser, post(browser, STOP, page))
            elif change == "reopen":
                follow(browser, post(browser, "/sessions/open", browser.page("/sessions")))
            elif change == "undo":
                follow(browser, post(browser, "/sessions/undo", page,
                                     target_revision=str(before.state.revision)))
            elif change == "correction":
                response = browser.request("POST", "/sessions/command", {
                    "managed_handle": active.handle,
                    "expected_revision": str(active.state.revision),
                    "kind": "record_play", "target_revision": str(active.state.revision),
                    "player_id": active.state.players[2].player_id, "card": "H8"})
                follow(browser, response)
            elif change == "effort":
                follow(browser, post(browser, EFFORT, page, analysis_effort="standard"))
            elif change == "reject":
                assert post(browser, "/sessions/play", page, cards="CA")[0] == 400
            else:
                admitted = active.document
                for old, new in ((admitted, before), (before, admitted)):
                    saved = files.save_session_file(active.path, new,
                        expected_content_fingerprint=old.content_fingerprint).value
                    assert saved.status == "saved"
            newer = active.live.outcome
            feedback = app.form_feedback.current("sessions", active_identity=active)
        finally:
            release.set()
        assert first.result(timeout=15)[0] == 303
    assert active.live.outcome is newer and not active.live.unavailable
    assert (newer is not None) == (change in {"effort", "correction"})
    assert (feedback is not None) == (change == "reject")
    assert app.form_feedback.current("sessions", active_identity=active) is feedback


def test_final_display_rechecks_original_attempt_after_render(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_live_game(browser, play_count=0)
    page = follow(browser, post(browser, START))
    assert 'id="live-recommendation"' in page
    entered, release = Event(), Event()
    real = Handler._send_bytes

    def paused(self, status, content, **kwargs):
        if b'id="live-recommendation"' in content and not entered.is_set():
            entered.set()
            assert release.wait(15)
        return real(self, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(browser.request, "GET", "/sessions/current")
        try:
            assert entered.wait(10)
            assert post(browser, STOP, page)[0] == 303
        finally:
            release.set()
        status, _, content = first.result(timeout=15)
    assert status == 409 and b'id="live-recommendation"' not in content


@pytest.mark.parametrize("change", ["stop", "resubmit_stale"])
def test_admission_after_save_checks_exact_owner_and_input(localized_server, monkeypatch, change):
    import skatmind.app_web.server as server

    browser = Browser(localized_server)
    _, plays = record_live_game(browser, play_count=3)
    page = follow(browser, post(browser, START))
    calls = watch(monkeypatch)
    form = Forms(page).find("/sessions/play")
    entered, release = Event(), Event()
    real = server.run_live_attempt

    def paused(app, active, attempt):
        entered.set()
        assert release.wait(15)
        return real(app, active, attempt)

    monkeypatch.setattr(server, "run_live_attempt", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(browser.submit, form, cards=plays[3]["card"])
        try:
            assert entered.wait(10)
            if change == "stop":
                assert post(browser, STOP)[0] == 303
            else:
                assert browser.submit(form, cards=plays[3]["card"])[0] == 409
        finally:
            release.set()
        page = follow(browser, first.result(timeout=15))
    assert ('id="live-recommendation"' in page) == (change != "stop")
    assert len(calls) == int(change != "stop") and 'class="error-summary"' not in page
