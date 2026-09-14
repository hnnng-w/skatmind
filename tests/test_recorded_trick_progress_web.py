import re

import pytest
from test_compact_card_entry_web import create_live
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import entry_action, follow, operation_form, start_match
from test_recorded_trick_progress import GRAND_PREFIXES, progress_data
from test_session_recorded_review_web import Browser, Forms, review_first

import skatmind.api.v1.session.files as session_files
import skatmind.app_web.execution as execution
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.capture_web.context import MatchCaptureWebContextV1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def summary_html(page):
    return re.search(r'<aside class="recorded-summary".*?</aside>', page, re.S)[0]


def html_totals(block):
    values = re.findall(r'<dd data-trick-metric="(tricks|points)">(\d+)</dd>', block)
    tricks = [int(value) for metric, value in values if metric == "tricks"]
    points = [int(value) for metric, value in values if metric == "points"]
    return tuple(zip(tricks, points, strict=True)) if points else tuple(tricks)


def assert_progress(page, expected, prefixes=()):
    assert html_totals(summary_html(page)) == expected
    rows = re.findall(r'<section class="recorded-trick".*?</section>', page, re.S)
    for row, prefix in zip(rows, prefixes, strict=False):
        assert html_totals(row) == prefix
    assert 'data-trick-number="11"' not in page


@pytest.mark.parametrize("locale", ("en", "de"))
def test_real_session_record_undo_reject_complete_reopen_and_readonly_result(
    localized_server, monkeypatch, locale,
):
    browser = Browser(localized_server)
    form = create_live(browser)
    data = progress_data()
    follow(browser, browser.submit(form, cards=data["players"][0]["initial_hand"]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true")
    page = follow(browser, browser.submit(Forms(browser.page()).find("/actions/profile/language"),
                                          language=locale))
    active = localized_server.app_context.managed_stateful.active_session
    start = active.state.revision
    saves = []
    real_save = session_files.save_session_file
    def save(*args, **kwargs):
        saves.append(1)
        return real_save(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    assert_progress(page, GRAND_PREFIXES[0])
    plays = [p for trick in data["tricks"] for p in trick["plays"]]
    for count, play in enumerate(plays, 1):
        response = browser.submit(Forms(page).find("/sessions/play"), cards=play["card"])
        assert response[1]["location"] == "/sessions/current#session-recording"
        page = follow(browser, response)
        assert_progress(page, GRAND_PREFIXES[count // 3], GRAND_PREFIXES[1:count // 3 + 1])
        if count % 3:
            assert text(locale, "trick_progress.incomplete") in page
        if count == 3:
            before = active.path.read_bytes()
            bad = browser.submit(Forms(page).find("/sessions/play"), cards="CA")
            assert bad[0] == 400 and active.path.read_bytes() == before
            assert_progress(bad[2].decode(), GRAND_PREFIXES[1])
            page = follow(browser, browser.submit(Forms(page).find("/sessions/undo"),
                                                  target_revision=str(start + 2)))
            assert_progress(page, GRAND_PREFIXES[0])
            page = follow(browser, browser.submit(Forms(page).find("/sessions/play"), cards="H9"))
            assert_progress(page, GRAND_PREFIXES[1])
    assert len(saves) == 32  # Thirty Plays, one Undo, one re-recorded Card.
    assert active.state.phase == "play" and "/sessions/play" not in page
    assert len(active.decision_checkpoints) == 10
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.path.read_bytes() == before and len(saves) == 32
    assert_progress(page, GRAND_PREFIXES[-1], GRAND_PREFIXES[1:])
    # This is a genuine executed #221 Result, not an injected successful value.
    if locale == "de":
        follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                       language="en"))
    page, _ = review_first(browser)
    retained = active.execution
    downloads = tuple(browser.request("GET", f"/sessions/downloads/{kind}.json")[2]
                      for kind in ("request", "result"))
    generation, checkpoints = active.generation, active.decision_checkpoints
    def forbidden(*args, **kwargs):
        pytest.fail("Read-only progress must not write, collect Checkpoints, or execute")
    with monkeypatch.context() as guard:
        import skatmind.app_web.session_frontend as frontend
        guard.setattr(session_files, "save_session_file", forbidden)
        guard.setattr(execution, "execute", forbidden)
        guard.setattr(frontend, "_collect_current_checkpoint", forbidden)
        for target in ("de", "en"):
            page = browser.page()
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=target))
            assert_progress(page, GRAND_PREFIXES[-1])
            assert active.execution is retained
            assert active.path.read_bytes() == before and active.generation == generation
            assert active.decision_checkpoints == checkpoints
            assert tuple(browser.request("GET", f"/sessions/downloads/{kind}.json")[2]
                         for kind in ("request", "result")) == downloads


@pytest.mark.parametrize("locale", ("en", "de"))
def test_real_match_preview_cancel_apply_rewind_continue_reopen_and_slot_switch(
    localized_server, monkeypatch, locale,
):
    browser = Browser(localized_server)
    page = start_match(browser, locale)
    active = localized_server.app_context.managed_stateful.active_match
    saves = []
    real_save = MatchCaptureWebContextV1.save_candidate
    def save(context, candidate):
        saves.append(candidate)
        return real_save(context, candidate)
    monkeypatch.setattr(MatchCaptureWebContextV1, "save_candidate", save)
    for count, card in enumerate("SA S9 S7 CA C9 C7 H7 H8 H9".split(), 1):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
        expected = (((count // 3, 11 * (count // 3)), (0, 0), (0, 0)) if count < 9
                    else ((2, 22), (0, 0), (1, 0)))
        assert_progress(page, expected)
    assert len(saves) == 9
    before = active.path.read_bytes()
    original = ((2, 22), (0, 0), (1, 0))
    for cancel in (True, False):
        page = follow(browser, browser.submit(entry_action(page, 2)))
        page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"),
                                              card="SK"))
        assert_progress(page, original)
        assert active.path.read_bytes() == before and len(saves) == 9
        if cancel:
            page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/cancel")))
            assert_progress(page, original)
        else:
            page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                                  confirm_apply="on"))
    assert len(saves) == 10
    assert_progress(page, ((2, 26), (0, 0), (1, 0)),
                    (((1, 15), (0, 0), (0, 0)), ((2, 26), (0, 0), (0, 0))))
    for index in range(1, 10):
        assert page.count(f'id="match-play-{index}"') == 1
        assert entry_action(page, index) and entry_action(page, index, rewind=True)
    # Same-Card preview/apply is a real no-op, including Save count.
    page = follow(browser, browser.submit(entry_action(page, 2)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="SK"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    assert len(saves) == 10
    page = follow(browser, browser.submit(entry_action(page, 6, rewind=True)))
    assert_progress(page, ((2, 26), (0, 0), (1, 0)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                          confirm_apply="on"))
    assert_progress(page, ((1, 15), (0, 0), (0, 0)))
    assert text(locale, "trick_progress.incomplete") in page
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards="C7"))
    assert_progress(page, ((2, 26), (0, 0), (0, 0)))
    assert len(saves) == 12
    saved = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    assert_progress(page, ((2, 26), (0, 0), (0, 0)))
    active = localized_server.app_context.managed_stateful.active_match
    assert active.path.read_bytes() == saved
    page = browser.page("/matches/position/2")
    assert html_totals(summary_html(page)) == ()
    assert text(locale, "trick_progress.status.empty") in page
    page = follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    assert text(locale, "trick_progress.status.passed_deal") in page
    page = browser.page("/matches/position/1")
    assert_progress(page, ((2, 26), (0, 0), (0, 0)))


def test_rejected_thirtieth_witness_excluded_and_accepted_warning_is_distinct(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    cards = ("DK D8 D7 H10 HQ H7 SQ S10 S8 S9 S7 SK DJ SJ HJ "
             "H8 CQ HA C10 CA CK H9 DA C9 D9 D10 CJ C7 C8 DQ").split()
    for index, card in enumerate(cards[:29], 1):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"),
                                              cards="SA" if index == 26 else card))
    accepted_summary = summary_html(page)
    accepted_rows = re.findall(r'<section class="recorded-trick".*?</section>', page, re.S)
    assert "trick-warning" not in accepted_summary
    before = active.path.read_bytes()
    bad = browser.submit(operation_form(page, "append_plays"), cards="DQ")
    assert bad[0] == 400 and active.path.read_bytes() == before
    page = bad[2].decode()
    assert summary_html(page) == accepted_summary
    assert re.findall(r'<section class="recorded-trick".*?</section>', page, re.S) == accepted_rows
    assert 'id="match-play-30"' not in page and 'href="#match-play-26"' in page
    # A distinct accepted partial recording has a real supported warning.
    page = browser.page("/matches/position/2")
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=active.workspace.match_definition.participants[0].player_id,
        game_type="grand", hand_game="true"))
    for card in "SA H7 S7 CA S8".split():
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    assert_progress(page, ((1, 11), (0, 0), (0, 0)))
    assert "trick-warning" in summary_html(page)
    assert 'href="#match-play-2"' in page and 'href="#match-play-5"' in page


def test_match_declaration_edit_null_and_faulted_apply_keep_accepted_progress(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    for card in "C10 CJ CQ".split():
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    assert_progress(page, ((0, 0), (1, 15), (0, 0)))
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
                                          game_type="null"))
    assert html_totals(summary_html(page)) == (0, 0, 1)
    assert 'data-trick-metric="points"' not in summary_html(page)
    assert "/matches/cards" in page  # No automatic Null capture stop.
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="CK"))
    source, before = active.workspace, active.path.read_bytes()
    accepted = summary_html(page)
    import skatmind.capture_web.context as capture
    def fail(*args, **kwargs):
        raise OSError("Injected pre-replacement storage failure")
    with monkeypatch.context() as fault:
        fault.setattr(capture, "save_match_workspace_file_v1", fail)
        response = browser.submit(Forms(page).find("/matches/recovery/apply"), confirm_apply="on")
    assert response[0] == 409
    assert summary_html(response[2].decode()) == accepted
    assert active.workspace is source and active.path.read_bytes() == before
    page = follow(browser, browser.submit(entry_action(browser.page("/matches/current"), 3)))
    bad = browser.submit(Forms(page).find("/matches/recovery/preview"), card="C10")
    assert bad[0] == 400 and summary_html(bad[2].decode()) == accepted
    assert active.path.read_bytes() == before


def test_match_snapshot_keeps_history_names_and_actions_on_requested_game(
    localized_server, monkeypatch,
):
    import skatmind.app_web.server as server_module
    from skatmind.app_web.match_frontend import select_unified_match_position_v1
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in "SA S9 S7".split():
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    active = localized_server.app_context.managed_stateful.active_match
    original = server_module.capture_language_source_v1
    moved = []
    def interleaved(context, route):
        source = original(context, route)
        if not moved and route == "/matches/position/1":
            moved.append(True)
            # Deterministic navigation interleaving at the formerly unlocked seam.
            with active.capture.lock:
                select_unified_match_position_v1(active, 2)
        return source
    monkeypatch.setattr(server_module, "capture_language_source_v1", interleaved)
    status, _, content = browser.request("GET", "/matches/position/1")
    assert status == 409  # Existing language/source guard rejects the old page binding.
    page = content.decode()
    assert moved and active.selected_position == 1
    assert 'data-recorded-summary' not in page  # No mixed-source page is published.
    page = browser.page("/matches/position/1")
    assert_progress(page, ((1, 11), (0, 0), (0, 0)))
    assert entry_action(page, 2)
    page = follow(browser, browser.submit(entry_action(page, 2)))
    assert "/matches/recovery/preview" in page


def test_match_readonly_views_preserve_preview_expiry_bindings_and_bytes(
    localized_server, monkeypatch,
):
    import skatmind.app_web.cross_area_transfer as transfer
    import skatmind.app_web.match_recovery as recovery
    import skatmind.match_historical_materialization as materialization
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    for card in "SA S9 S7".split():
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    page = follow(browser, browser.submit(entry_action(page, 2)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="SK"))
    before = active.path.read_bytes()
    preview, selections = active.recovery.preview, recovery.recording_selections(active)
    def forbidden(*args, **kwargs):
        pytest.fail("Progress display must not save, execute, materialize, or transfer")
    with monkeypatch.context() as guard:
        guard.setattr(MatchCaptureWebContextV1, "save_candidate", forbidden)
        guard.setattr(execution, "execute", forbidden)
        guard.setattr(materialization, "materialize_match_observed_game_historical_v1", forbidden)
        guard.setattr(transfer, "transfer_active_match_workspace_to_corpus_v1", forbidden)
        for locale in ("de", "en"):
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
            assert_progress(page, ((1, 11), (0, 0), (0, 0)))
            assert active.recovery.preview is preview
            assert recovery.recording_selections(active) == selections
            assert active.path.read_bytes() == before
            assert Forms(page).find("/matches/recovery/apply")["values"][
                "recovery_selection"] == preview.apply_token
