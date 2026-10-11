"""Completion is an explicit ending; its handoff only navigates to saved decisions."""

import re

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play import build_open_play_prefix
from test_historical_game import build_historical_input
from test_historical_open_card_throw import build_throw_prefix
from test_match_recording_recovery_web import follow
from test_recorded_game_summaries_web import assert_declaration_order, hand_text
from test_recorded_trick_progress_web import html_totals, summary_html
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms, record_score_review_game
from test_session_transitions import _complete_retrospective_session

import skatmind.api.v1.session.files as session_files
import skatmind.app_web.execution as execution
import skatmind.app_web.session_frontend as frontend
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def forbid_passive_operations(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Passive completion/handoff must not save, collect, or execute")
    monkeypatch.setattr(session_files, "save_session_file", forbidden)
    monkeypatch.setattr(frontend, "_collect_current_checkpoint", forbidden)
    monkeypatch.setattr(execution, "execute", forbidden)


def recording_panel(page):
    return re.search(r'<div id="session-recording".*?</section></div>', page, re.S)[0]


@pytest.mark.parametrize("locale", ("en", "de"))
def test_finish_once_reopen_and_navigate_to_exact_selection_without_analysis(
    localized_server, monkeypatch, locale,
):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=30,
        names=("Alexandra Long-Synthetic-Player-Name", "Boris", "Clara"))
    active = localized_server.app_context.managed_stateful.active_session
    page = follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                                          language=locale))
    state, checkpoints = active.state, active.decision_checkpoints
    frozen = tuple(c.to_dict() for c in checkpoints)
    assert state.phase == "play"
    assert replay_session_state_v1(state).game_end_reason is None
    panel = recording_panel(page)
    assert text(locale, "task.session.finish_recording") in panel
    assert text(locale, "task.session.recording_completed") not in panel
    assert 'class="session-completion"' not in page
    form = Forms(panel).find("/sessions/command", kind="set_game_end")
    assert form["values"]["game_end_reason"] == "normal_completion"
    assert set(form["values"]) == {
        "managed_handle", "expected_revision", "kind", "game_end_reason",
        "_frontend_form_instance",
    }
    assert html_totals(summary_html(page)) == ((3, 42), (7, 78))
    saves = []
    real_save = session_files.save_session_file
    def save(*args, **kwargs):
        saves.append(1)
        return real_save(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    page = follow(browser, browser.submit(form))
    assert saves == [1]
    assert active.state.phase == "ended" and active.state.revision == state.revision + 1
    assert active.state.command_log[:-1] == state.command_log
    end = active.state.command_log[-1].command
    assert end.kind == "set_game_end" and end.game_end_reason == "normal_completion"
    assert end.expected_revision == state.revision and end.game_end is None
    assert active.decision_checkpoints == checkpoints
    assert active.execution is None
    assert active.state.validation.historical_export.status == "unavailable"
    saved, document = active.path.read_bytes(), active.document
    forbid_passive_operations(monkeypatch)
    for reopened in (False, True):
        if reopened:
            page = follow(browser, browser.submit(
                Forms(browser.page("/sessions")).find("/sessions/open")))
            active = localized_server.app_context.managed_stateful.active_session
        for target in (locale, "de" if locale == "en" else "en"):
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=target))
            panel = recording_panel(page)
            markup = Hierarchy(page)
            assert markup.by_id("session-recording")["attrs"]["class"] == "session-completion"
            assert markup.within("session-recording", "h2")[0]["text"] == text(
                target, "task.session.recording_completed")
            assert "recording-progress-layout" not in panel
            assert not markup.within("session-recording", "form")
            assert text(target, "trick_progress.completed", count=10) in panel
            assert html_totals(summary_html(panel)) == ((3, 42), (7, 78))
            assert "Alexandra Long-Synthetic-Player-Name" in panel
            assert "Synthetic score review" in next(n["text"] for n in markup.nodes
                                                     if n["tag"] == "h1")
            links = markup.within("session-recording", "a")
            assert [(n["attrs"]["href"], n["text"]) for n in links] == [
                ("#recorded-decisions", text(target, "recorded_review.title")),
                ("#session-history", text(target, "task.session.corrections")),
            ]
            assert links[0]["attrs"]["class"] == "button-link"
            assert "button-link" not in links[1]["attrs"].get("class", "")
            assert markup.visible(links[0])
            # Same-document navigation targets the existing source-bound selection forms.
            selection_page = browser.page("/sessions/current" + links[0]["attrs"]["href"])
            selections = [f for f in Forms(selection_page).forms
                          if f["action"] == "/sessions/review-decision"]
            assert len(selections) == 10
            assert all(f["values"]["managed_handle"] == active.handle for f in selections)
            destination = Hierarchy(selection_page).by_id("recorded-decisions")
            assert destination["attrs"]["tabindex"] == "-1"
            assert_declaration_order(page, target)
            assert len(markup.within("session-history", "form")) > 0
            assert Forms(page).find("/sessions/undo") and Forms(page).find("/sessions/reload")
            assert Forms(page).find("/sessions/declaration-correction/select")
            mode = text(target, "session.knowledge.accepted_mode",
                        mode=text(target, "session.knowledge.perspective"))
            assert mode not in page.split('id="session-recording"')[0]
            assert page.count(mode) == 1
            assert all(text(target, "task.session.hand_empty") in hand_text(page, n)
                       for n in range(1, 4))
            facts = replay_session_state_v1(active.state)
            assert facts.initial_hand_for(facts.players[0].player_id) is None
            assert active.document == document and active.path.read_bytes() == saved
            assert tuple(c.to_dict() for c in active.decision_checkpoints) == frozen
            assert browser.request("GET", "/sessions/downloads/session.json")[2] == saved
            assert active.execution is active.recorded_review_source is None


@pytest.mark.parametrize("locale", ("en", "de"))
@pytest.mark.parametrize("data", (
    build_concession_prefix(completed_trick_count=0),
    build_defender_concession_prefix(completed_trick_count=4, current_trick_card_count=2),
    build_exposure_prefix(completed_trick_count=4, current_trick_card_count=2),
    build_open_play_prefix(completed_trick_count=8),
    build_throw_prefix(completed_trick_count=8),
    build_historical_input(game_type="null"),
), ids=("declarer-concession", "defender-concession", "exposure", "open-play", "throw", "null"))
def test_existing_ended_files_show_only_accepted_coverage_without_resave(
    localized_server, monkeypatch, locale, data,
):
    # Strict accepted-log fixtures represent files predating the new presentation.
    state = _complete_retrospective_session(data)
    document = build_session_persistence_document_v1(state)
    path = localized_server.app_context.managed_home.root / "sessions" / "synthetic-ended.json"
    assert session_files.save_session_file(path, document,
        expected_content_fingerprint=None).value.status == "saved"
    before = path.read_bytes()
    browser = Browser(localized_server)
    forbid_passive_operations(monkeypatch)
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    panel = recording_panel(page)
    facts = replay_session_state_v1(state)
    count = len(facts.completed_tricks)
    normal = data["game_end_reason"] == "normal_completion"
    assert text(locale, "task.session.recording_completed" if normal
                else "task.session.phase.ended") in panel
    assert text(locale, "trick_progress.completed", count=count) in panel
    assert text(locale, "recorded_review.no_perspective") in page
    assert 'class="button-link"' not in panel and 'href="#session-history"' in panel
    if not normal:
        assert text(locale, "task.session.recording_completed") not in panel
        assert text(locale, "task.value." + data["game_end_reason"]) in panel
        assert text(locale, "trick_progress.completed", count=10) not in panel
        assert sum(v[0] for v in html_totals(summary_html(panel))) == count
        if facts.incomplete_trick is not None:
            assert text(locale, "trick_progress.terminal_incomplete") in page
    else:
        assert 'data-trick-metric="points"' not in panel
        assert text(locale, "trick_progress.null_scope") in panel
    active = localized_server.app_context.managed_stateful.active_session
    assert active.document == document and path.read_bytes() == before
    assert active.execution is None


def test_ended_recording_without_saved_snapshots_offers_inspection_only(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=30)
    browser.command("set_game_end")
    active = localized_server.app_context.managed_stateful.active_session
    document = build_session_persistence_document_v1(active.state)
    assert session_files.save_session_file(active.path, document,
        expected_content_fingerprint=active.document.content_fingerprint).value.status == "saved"
    before = active.path.read_bytes()
    forbid_passive_operations(monkeypatch)
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        panel = recording_panel(page)
        assert 'href="#recorded-decisions"' in panel and 'class="button-link"' not in panel
        assert text(locale, "recorded_review.inspect") in panel
        assert text(locale, "recorded_review.no_snapshots") in page
        assert not any(f["action"] == "/sessions/review-decision" for f in Forms(page).forms)
        assert active.path.read_bytes() == before
