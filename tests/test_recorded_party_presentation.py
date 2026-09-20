"""R05 presentation from real accepted sources, independent of analysis readiness."""

import re
from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_decision_context import MATCH_HAND
from test_recorded_trick_progress import match_trace
from test_recorded_trick_progress_web import summary_html
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms, record_score_review_game

from skatmind.app_web.recorded_trick_progress import project_match_trick_progress
from skatmind.app_web.recorded_trick_rendering import (
    render_recorded_history,
    render_recorded_summary,
)
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def history_rows(page):
    markup = Hierarchy(page)
    histories = [n for n in markup.nodes if n["attrs"].get("class") == "recorded-history"]
    assert len(histories) == 1
    history, = histories
    assert markup.visible(history)
    rows = [n for n in markup.nodes if n["tag"] == "li"
            and any(p is history for p in n["parents"])]
    assert all(markup.visible(n) for n in rows)
    return rows


def assert_party_score(page, declarer, defenders):
    """Each expected pair is (points, won Tricks), independently enumerated by callers."""
    summary = summary_html(page)
    assert 'class="trick-total"' not in page and 'trick-prefix-heading' not in page
    assert re.findall(r'data-recorded-party="([^"]+)"', summary) == ["declarer", "defenders"]
    values = re.findall(r'<dd data-trick-metric="(points|tricks)">(\d+)</dd>', summary)
    assert values == [(metric, str(value)) for pair in (declarer, defenders)
                      for metric, value in zip(("points", "tricks"), pair, strict=True)]
    assert "data-seat=" not in summary


def test_normal_history_has_no_individual_prefix_grids():
    progress = project_match_trick_progress(match_trace("HJ SJ DJ C7 C8 C9".split()), 3)
    history = render_recorded_history(progress, "en")
    assert 'class="trick-total"' not in history
    assert "After trick" not in history and "data-seat=" not in history
    assert history.count("Winner:") == history.count("Trick value:") == 2


@pytest.mark.parametrize("locale,heading", (("en", "Game score"), ("de", "Spielstand")))
def test_session_distinct_score_single_history_and_independent_uat_prefixes(
    localized_server, locale, heading,
):
    browser = Browser(localized_server)
    plays = record_score_review_game(browser, play_count=0)
    page = follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                                         language=locale))
    assert f"<h3>{heading}</h3>" in summary_html(page)
    assert_party_score(page, (0, 0), (0, 0))
    expected = {3: ((0, 0), (15, 1)), 6: ((0, 0), (29, 2)),
                9: ((14, 1), (29, 2)), 12: ((14, 1), (35, 3))}
    for index, play in enumerate(plays[:12], 1):
        page = follow(browser, browser.submit(Forms(page).find("/sessions/play"),
                                              cards=play["card"]))
        if index in expected:
            assert_party_score(page, *expected[index])
        rows = history_rows(page)
        assert len(rows) == index
        assert [row["attrs"].get("id") for row in rows] == [
            f"session-play-{i}" for i in range(1, index + 1)]
        assert page.index('action="/sessions/play"') < page.index('class="recorded-history"')


def corrected_match_setup(browser):
    page = browser.page("/matches/new")
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        match_title="Synthetic party score", forehand_name="B", middlehand_name="C",
        rearhand_name="A", perspective_seat="middlehand", setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
                                         setup_action="create"))
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    player = next(value for value, label in re.findall(
        r'<option value="([^"]+)"[^>]*>(.*?)</option>', options) if label.startswith("B"))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=player, game_type="grand", hand_game="true"))
    for card in ("CK", "C7", "CA"):
        page = follow(browser, browser.submit(Forms(page).find("/matches/cards"), cards=card))
    return page


def test_match_review_has_visible_chronology_without_ready_decisions(localized_server):
    browser = Browser(localized_server)
    corrected_match_setup(browser)
    page = browser.page("/matches/review/1")
    rows = history_rows(page)
    assert len(rows) == 3
    assert [re.search(r"\((C\w+)\)", row["text"])[1] for row in rows] == ["CK", "C7", "CA"]
    assert not any(f["values"].get("operation") == "analyze_decision" for f in Forms(page).forms)
    assert "/matches/recovery/" not in page


def assert_match_cards(page, cards, *, review=False):
    rows = history_rows(page)
    assert [re.search(r'\(([A-Z0-9]+)\)', row["text"])[1] for row in rows] == cards
    for index, row in enumerate(rows, 1):
        assert row["attrs"]["id"] == f"match-play-{index}"
        assert row["attrs"]["tabindex"] == "-1"
        if review:
            assert f'href="/matches/position/1#match-play-{index}"' in page
        else:
            assert entry_action(page, index) and entry_action(page, index, rewind=True)
    if review:
        assert "/matches/recovery/" not in page


def test_real_corrected_match_cancel_apply_noop_rewind_hand_pass_reopen(
    localized_server, monkeypatch,
):
    import skatmind.app_web.match_recovery as recovery
    import skatmind.app_web.task_first_match_state as page_state
    import skatmind.capture_web.context as capture
    from skatmind.app_web.match_review_rendering import render_match_review_v1
    from skatmind.app_web.task_first_projections import project_task_first_match_v1
    from skatmind.match_workspace_persistence import load_match_workspace_file_v1

    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    active = localized_server.app_context.managed_stateful.active_match
    saves = []
    real_save = capture.save_match_workspace_file_v1
    def save(*args, **kwargs):
        saves.append(1)
        return real_save(*args, **kwargs)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    original = active.path.read_bytes()
    assert_party_score(page, (0, 0), (15, 1))
    for cancel in (True, False):
        page = follow(browser, browser.submit(entry_action(page, 3)))
        page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"),
                                              card="C10"))
        assert_party_score(page, (0, 0), (15, 1))
        assert_match_cards(page, ["CK", "C7", "CA"])
        assert active.path.read_bytes() == original and not saves
        preview, selections = active.recovery.preview, recovery.recording_selections(active)
        # Same-source read-only review must not issue or refresh recovery selections.
        def forbidden(*args, **kwargs):
            pytest.fail("Read-only chronology must not mint selections or perform Product work")
        with monkeypatch.context() as guard:
            import skatmind.app_web.server as server
            guard.setattr(server, "recording_selections", forbidden)
            review = browser.page("/matches/review/1")
        assert_match_cards(review, ["CK", "C7", "CA"], review=True)
        assert active.recovery.preview is preview
        assert recovery.recording_selections(active) == selections
        page = browser.page("/matches/position/1")
        page = follow(browser, browser.submit(Forms(page).find(
            "/matches/recovery/cancel" if cancel else "/matches/recovery/apply"),
            **({} if cancel else {"confirm_apply": "on"})))
    assert len(saves) == 1
    assert_party_score(page, (0, 0), (14, 1))
    assert_match_cards(page, ["CK", "C7", "C10"])
    game = active.workspace.slots[0].observed_game
    assert game.plays[-1].card == "C10"
    view = project_task_first_match_v1(active.workspace, selected_position=1)
    assert view.selected.next_player_id == game.plays[-1].player_id
    assert [row["text"].split(" — ")[1].split(":")[0]
            for row in history_rows(page)] == ["B", "C", "A"]
    corrected = active.path.read_bytes()
    # Genuine same-Card Apply keeps revision, bytes and save count.
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"),
                                          card="C10"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    assert len(saves) == 1 and active.path.read_bytes() == corrected
    # Rewind to the two-Card uncredited prefix and continue through the normal Card form.
    page = follow(browser, browser.submit(entry_action(page, 3, rewind=True)))
    assert_party_score(page, (0, 0), (14, 1))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    assert_party_score(page, (0, 0), (0, 0))
    assert_match_cards(page, ["CK", "C7"])
    page = follow(browser, browser.submit(Forms(page).find("/matches/cards"), cards="C10"))
    assert len(saves) == 3
    for hand in (False, True):
        if hand:
            page = browser.page("/matches/position/1")
            page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
                card_evidence_mode="exact", cards=MATCH_HAND))
        review = browser.page("/matches/review/1")
        assert_party_score(review, (0, 0), (14, 1))
        assert_match_cards(review, ["CK", "C7", "C10"], review=True)
        assert text("en", "recordings.match.prepared", prepared=int(hand), total=3) in review
    # One existing locked page snapshot; pure rendering must add zero preparation or I/O.
    with active.capture.lock:
        view = project_task_first_match_v1(active.workspace, selected_position=1)
        state = page_state.build_task_first_match_page_state_v1(active, view)
    with monkeypatch.context() as guard:
        guard.setattr(page_state, "_decision_preparation_summary", forbidden)
        guard.setattr(capture, "save_match_workspace_file_v1", forbidden)
        for locale in ("de", "en"):
            rendered = render_match_review_v1(state, view, managed_handle=active.handle,
                                             locale=locale)
            assert_party_score(rendered, (0, 0), (14, 1))
            assert_match_cards(rendered, ["CK", "C7", "C10"], review=True)
    page = browser.page("/matches/position/2")
    page = follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    assert active.workspace.slots[1].slot_kind == "passed_deal" and len(saves) == 5
    page = browser.page("/matches/position/1")
    assert_party_score(page, (0, 0), (14, 1))
    saved = active.path.read_bytes()
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    reopened = localized_server.app_context.managed_stateful.active_match
    assert reopened is not active and reopened.path.read_bytes() == saved and len(saves) == 5
    assert_party_score(page, (0, 0), (14, 1))
    assert_match_cards(browser.page("/matches/review/1"), ["CK", "C7", "C10"], review=True)


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("count,key", ((0, "none_completed"), (1, "none_completed"),
    (2, "none_completed"), (3, "one"), (4, "one"), (6, "many")))
@pytest.mark.parametrize("ended", (False, True))
def test_null_recorded_facts_not_outcome(locale, count, key, ended):
    view = project_match_trick_progress(match_trace("CA C7 C8 SA S7 S8".split()[:count],
        game_type="null"), 3)
    if ended:
        # Scalar status fixture: no new Null ending rule is inferred from the trace.
        view = replace(view, status="ended")
    rendered = render_recorded_summary(view, locale) + render_recorded_history(view, locale)
    assert text(locale, "trick_progress.null." + key,
                **({"count": 2} if key == "many" else {})) in rendered
    assert "data-trick-metric" not in rendered and "data-recorded-party" not in rendered
    assert text(locale, "trick_progress.value", points=11) not in rendered
    assert rendered.count('class="recorded-card"') == count
    if count >= 3:
        assert text(locale, "trick_progress.winner", player="Alice") in rendered
    unknown = replace(view, declarer_player_id=None,
        tricks=tuple(replace(t, prefix=None if t.prefix is None else
            replace(t.prefix, declarer=None, defenders=None)) for t in view.tricks))
    unknown_summary = render_recorded_summary(unknown, locale)
    assert text(locale, "trick_progress.party_unknown") in unknown_summary
    assert text(locale, "trick_progress.null.zero") not in unknown_summary


def test_review_warning_target_is_visible_and_links_to_recording(localized_server):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    # Accepted contradiction: C failed to follow clubs, then is observed playing C8.
    page = follow(browser, browser.submit(entry_action(page, 2)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="H7"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    for card in ("C10", "CQ", "C8"):
        page = follow(browser, browser.submit(Forms(page).find("/matches/cards"), cards=card))
    for locale in ("de", "en"):
        page = browser.page("/matches/review/1")
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert 'class="trick-warning"' in summary_html(page)
        assert 'href="#match-play-2"' in summary_html(page)
        markup = Hierarchy(page)
        assert markup.visible(markup.by_id("match-play-2"))
        assert 'href="/matches/position/1#match-play-2"' in page
