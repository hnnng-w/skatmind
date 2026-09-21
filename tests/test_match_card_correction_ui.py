"""R06: real returned forms distinguish a proposal, verified Apply, and removal consent."""

from dataclasses import replace
from html import escape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_decision_context import MATCH_HAND
from test_recorded_party_presentation import (
    assert_match_cards,
    assert_party_score,
    corrected_match_setup,
)
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck
from skatmind.match_workspace_persistence import load_match_workspace_file_v1

PREVIEW = "/matches/recovery/preview"
APPLY = "/matches/recovery/apply"
CANCEL = "/matches/recovery/cancel"
SELECT = "/matches/recovery/select"


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def form_nodes(page, route):
    markup = Hierarchy(page)
    form, = [n for n in markup.nodes if n["tag"] == "form"
             and n["attrs"].get("action") == route]
    return form, [n for n in markup.nodes if any(p is form for p in n["parents"])]


def activated_form(page, route):
    """HTTP model of the emitted submitter; actual native activation is checked in Edge."""
    form = Forms(page).find(route)
    _, nodes = form_nodes(page, route)
    button, = [n["attrs"] for n in nodes if n["tag"] == "button"]
    if "name" in button:
        assert button["name"] not in form["values"]
        form["values"][button["name"]] = button["value"]
    return form


def recovery_text(page):
    return Hierarchy(page).by_id("match-recovery")["text"]


def assert_palette(page, locale, selected):
    form, nodes = form_nodes(page, PREVIEW)
    choices = [n["attrs"] for n in nodes if n["tag"] == "input"
               and n["attrs"].get("name") == "card"]
    expected = [suit + rank for suit in "CSHD"
                for rank in ("J", "A", "10", "K", "Q", "9", "8", "7")]
    assert [c["value"] for c in choices] == expected
    assert set(expected) == set(get_full_deck())
    assert all(c["type"] == "radio" and "required" in c for c in choices)
    assert [c["value"] for c in choices if "checked" in c] == [selected]
    assert [c["aria-label"] for c in choices] == [card_name(locale, c) for c in expected]
    assert "card" in form["attrs"]["data-preserve-fields"].split()
    assert not any(n["attrs"].get("name") in {"cards", "card_selection", "confirm_apply"}
                   for n in nodes)
    assert text(locale, "recovery.choose_card") in recovery_text(page)
    assert not any(n["attrs"].get("class") == "compact-selection" for n in nodes)
    assert not any(n["tag"] == "select" for n in nodes)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_graphical_selection_and_verified_preview_are_distinct(localized_server, locale):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(entry_action(page, 3)))
    assert_palette(page, locale, "CA")
    assert not any(f["action"] == APPLY for f in Forms(page).forms)
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C10"))
    assert not any(f["action"] == PREVIEW for f in Forms(page).forms)
    apply, nodes = form_nodes(page, APPLY)
    confirmation, = [n for n in nodes if n["attrs"].get("name") == "confirm_apply"]
    assert confirmation["tag"] == "button"
    assert confirmation["attrs"]["value"] == "on"
    assert confirmation["attrs"]["type"] == "submit"
    assert confirmation["attrs"]["class"] == "primary"
    assert "confirm_apply" not in apply["attrs"]["data-preserve-fields"].split()
    assert "data-language-form" not in apply["attrs"]
    scope = recovery_text(page)
    assert text(locale, "recovery.annotations_unchanged") not in scope
    assert text(locale, "recovery.metadata_unchanged") not in scope
    assert "15 → 14" in scope
    assert text(locale, "recovery.winner_same", trick=1, player="A") in scope
    assert text(locale, "recovery.following", count=0) not in scope
    assert text(locale, "task.match.position", number=1) in scope
    assert card_name(locale, "CA") in scope and card_name(locale, "C10") in scope
    assert active.path.read_bytes() == before
    assert_party_score(page, (0, 0), (15, 1))
    assert_match_cards(page, ["CK", "C7", "CA"])


def test_choose_another_clears_only_preview_and_supersedes_apply(localized_server):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3)))
    active = localized_server.app_context.managed_stateful.active_match
    selected = active.recovery.selected
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C10"))
    stale = activated_form(page, APPLY)
    section = page.split('id="match-recovery"', 1)[1].split('</section>', 1)[0]
    choose = next(f for f in Forms(section).forms if f["action"] == SELECT
                  and f["values"]["recovery_selection"] == selected.token)
    page = follow(browser, browser.submit(choose))
    assert active.recovery.selected is selected and active.recovery.preview is None
    assert_palette(page, "en", "CA")
    assert browser.submit(stale)[0] == 409
    assert active.path.read_bytes() == before


def test_annotation_free_preview_omits_irrelevant_inventories(localized_server):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C10"))
    scope = recovery_text(page)
    assert text("en", "recovery.annotations_unchanged") not in scope
    assert text("en", "recovery.metadata_unchanged") not in scope
    assert "all 0 following" not in scope


@pytest.mark.parametrize("rewind", (False, True))
def test_confirmation_is_owned_by_the_correct_action(localized_server, rewind):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3, rewind=rewind)))
    if not rewind:
        page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C10"))
    _, nodes = form_nodes(page, APPLY)
    confirmation, = [n for n in nodes if n["attrs"].get("name") == "confirm_apply"]
    if rewind:
        assert confirmation["tag"] == "input"
        assert confirmation["attrs"]["type"] == "checkbox"
        assert "required" in confirmation["attrs"] and "checked" not in confirmation["attrs"]
        assert text("en", "recovery.removal_final") in page
    else:
        assert confirmation["tag"] == "button"
    for route in (CANCEL, "/actions/profile/language"):
        assert not any(n["attrs"].get("name") == "confirm_apply"
                       for n in form_nodes(page, route)[1])
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    apply = Forms(page).find(APPLY)
    for value in (None, "", "true", ["on", "on"]):
        values = dict(apply["values"])
        if value is not None:
            values["confirm_apply"] = value
        assert browser.request("POST", APPLY, values)[0] == 400
    assert browser.submit(apply, confirm_apply="on",
                          recovery_selection=active.recovery.selected.token)[0] == 409
    assert active.path.read_bytes() == before


def test_rejected_choice_language_return_uses_singular_radio(localized_server):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3)))
    status, _, body = browser.submit(Forms(page).find(PREVIEW), card="CK")
    assert status == 400
    page = body.decode()
    assert_palette(page, "en", "CK")
    assert not any(f["action"] == APPLY for f in Forms(page).forms)
    assert 'href="#match-play-1"' in page
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    assert_palette(page, "de", "CK")
    assert 'class="error-summary"' in page
    assert escape(text("de", "recovery.reason.duplicate")) in page


def test_real_named_apply_cancel_noop_report_retention_and_reopen(localized_server, monkeypatch):
    import skatmind.capture_web.analysis as analysis
    import skatmind.capture_web.context as capture
    from skatmind.app_web.task_first_projections import project_task_first_match_v1

    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
        card_evidence_mode="exact", cards=MATCH_HAND))
    page = follow(browser, browser.submit(operation_form(browser.page("/matches/review/1"),
                                                        "analyze_decision")))
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    assert report.value.status == "executed"
    route = f"/matches/api/v1/reports/{report.report_id}.json"
    report_bytes = browser.request("GET", route)[2]
    original, workspace = active.path.read_bytes(), active.workspace
    saves = []
    real_save = capture.save_match_workspace_file_v1
    def save(*a, **kw):
        saves.append(1)
        return real_save(*a, **kw)
    def no_analysis(*a, **kw):
        pytest.fail("Passive correction must not execute analysis")
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    monkeypatch.setattr(analysis, "execute_match_decision_analysis_v1", no_analysis)
    page = browser.page("/matches/position/1")
    for proposal, finish in (("C10", CANCEL), ("CA", APPLY), ("C10", APPLY)):
        page = follow(browser, browser.submit(entry_action(page, 3)))
        page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card=proposal))
        if proposal == "CA":
            assert text("en", "recovery.unchanged") in page
        for locale in ("de", "en"):
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                  language=locale))
            assert not any(f["action"] == PREVIEW for f in Forms(page).forms)
            assert browser.request("GET", route)[2] == report_bytes
        assert active.path.read_bytes() == original and active.workspace is workspace and not saves
        sent = activated_form(page, finish)
        assert ("confirm_apply" in sent["values"]) == (finish == APPLY)
        page = follow(browser, browser.submit(sent))
        if proposal == "CA" or finish == CANCEL:
            assert active.path.read_bytes() == original
            assert browser.request("GET", route)[2] == report_bytes
            assert active.capture.report_store.list() == (report,)
            assert_party_score(page, (0, 0), (15, 1))
    assert saves == [1] and active.workspace.revision == workspace.revision + 1
    assert active.path.read_bytes() != original
    assert not active.capture.report_store.list()
    assert browser.request("GET", route)[0] == 404
    assert_party_score(page, (0, 0), (14, 1))
    assert_match_cards(page, ["CK", "C7", "C10"])
    game = active.workspace.slots[0].observed_game
    view = project_task_first_match_v1(active.workspace, selected_position=1)
    assert view.selected.next_player_id == game.plays[-1].player_id
    page = browser.page("/matches/position/2")
    follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    assert len(saves) == 2
    assert_party_score(browser.page("/matches/position/1"), (0, 0), (14, 1))
    saved = active.path.read_bytes()
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    reopened = localized_server.app_context.managed_stateful.active_match
    assert reopened is not active and reopened.path.read_bytes() == saved and len(saves) == 2
    assert reopened.workspace.slots[1].slot_kind == "passed_deal"
    assert_match_cards(browser.page("/matches/review/1"), ["CK", "C7", "C10"], review=True)


def test_retained_suffix_annotations_timecodes_evidence_and_rewind(localized_server):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
        card_evidence_mode="exact", cards=MATCH_HAND))
    for index, card in enumerate(("SK", "S7", "S10"), 4):
        # Existing advanced chronological entry carries an actual media timecode.
        form = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/operation"
                    and f["values"].get("operation") == "append_plays")
        page = follow(browser, browser.submit(form, cards=card,
                                              decision_timecode=f"00:0{index}"))
    page = follow(browser, browser.submit(operation_form(page, "set_commentary"),
        decision_index="3", commentator_name="Observer", text="<C10> observed, unchanged text"))
    active = localized_server.app_context.managed_stateful.active_match
    note = active.workspace.slots[0].observed_game.commentaries[0]
    page = follow(browser, browser.submit(operation_form(page, "set_response_link"),
        commentary_id=note.commentary_id, response_decision_index="6"))
    original, before = active.path.read_bytes(), active.workspace
    game = before.slots[0].observed_game
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C10"))
    assert text("en", "recovery.following", count=3) in page
    assert text("en", "recovery.annotations_unchanged") in page
    assert active.path.read_bytes() == original
    candidate = active.recovery.preview.candidate.game
    assert {k: v for k, v in candidate.to_dict().items() if k != "plays"} == {
        k: v for k, v in game.to_dict().items() if k != "plays"}
    assert candidate.plays == (*game.plays[:2], replace(game.plays[2], card="C10"), *game.plays[3:])
    page = follow(browser, browser.submit(activated_form(page, APPLY)))
    assert active.workspace.slots[0].observed_game == candidate
    assert all(p.decision_timecode is not None for p in candidate.plays[3:])
    corrected = active.path.read_bytes()
    page = follow(browser, browser.submit(entry_action(page, 3)))
    status, _, body = browser.submit(Forms(page).find(PREVIEW), card="H7")
    assert status == 400 and text("en", "recovery.reason.wrong_actor") in body.decode()
    assert active.path.read_bytes() == corrected and active.recovery.preview is None
    page = follow(browser, browser.submit(entry_action(body.decode(), 3, rewind=True)))
    candidate = active.recovery.preview.candidate
    assert (candidate.retained_play_count, candidate.removed_play_count,
            candidate.removed_commentary_count, candidate.removed_response_count) == (2, 4, 1, 1)
    assert "&lt;C10&gt; observed, unchanged text" in page
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    _, nodes = form_nodes(page, APPLY)
    checkbox, = [n for n in nodes if n["attrs"].get("name") == "confirm_apply"]
    assert "checked" not in checkbox["attrs"]
    assert "confirm_apply" not in activated_form(page, APPLY)["values"]
    follow(browser, browser.submit(Forms(page).find(APPLY), confirm_apply="on"))
    assert active.workspace.slots[0].observed_game.plays == game.plays[:2]


@pytest.mark.parametrize("replacement,winner", (("C10", "B"), ("CJ", "B")))
def test_null_preview_shows_card_and_winner_without_point_emphasis(
    localized_server, replacement, winner,
):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
                                          game_type="null"))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card=replacement))
    scope = recovery_text(page)
    assert card_name("en", replacement) in scope
    assert text("en", "recovery.winner_changed", trick=1, before="A", after=winner) in scope
    assert "Points" not in scope and "15 →" not in scope
    assert active.path.read_bytes() == before


def test_warning_and_evidence_links_remain_visible_in_candidate(localized_server):
    from test_match_recording_recovery_web import start_match
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in ("SA", "H7", "S7", "CA", "S8", "C7"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    page = follow(browser, browser.submit(entry_action(page, 6)))
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C8"))
    assert text("en", "recovery.warning") in page
    assert text("en", "recovery.candidate_warning") in page
    assert 'href="#match-play-2"' in page and 'href="#match-play-5"' in page


def test_enhanced_choice_is_value_bound_and_cannot_restore_old_preview_overlay(localized_server):
    from test_task_first_language_preservation import enhanced_switch, envelope
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3)))
    raw = envelope(page, PREVIEW, {"card": ["H10"]})
    page = follow(browser, enhanced_switch(browser, page, raw))
    assert_palette(page, "de", "H10")
    # Server-retained preview has a different manifest: no editable Card form.
    page = follow(browser, browser.submit(Forms(page).find(PREVIEW), card="C10"))
    assert enhanced_switch(browser, page, raw, "en")[0] == 400
    page = browser.page("/matches/position/1")
    assert not any(f["action"] == PREVIEW for f in Forms(page).forms)
    assert activated_form(page, APPLY)["values"]["confirm_apply"] == "on"


def test_scoped_actions_have_separate_forms_and_danger_preparation(localized_server):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3)))
    for proposal in (None, "C10", "CK"):
        if proposal:
            if proposal == "CK":
                page = follow(browser, browser.submit(entry_action(page, 3)))
            response = browser.submit(Forms(page).find(PREVIEW), card=proposal)
            page = follow(browser, response) if response[0] == 303 else response[2].decode()
        markup = Hierarchy(page)
        row, = [n for n in markup.nodes if n["attrs"].get("class") == "recovery-primary-actions"]
        actions = [n for n in markup.nodes if n["tag"] == "form"
                   and any(p is row for p in n["parents"])]
        assert [n["attrs"]["action"] for n in actions] == [
            APPLY if proposal == "C10" else PREVIEW, CANCEL]
        assert all(not any(p["tag"] == "form" for p in n["parents"]) for n in actions)
        danger, = [n for n in markup.nodes if n["attrs"].get("class") == "recovery-danger"]
        assert text("en", "recovery.rewind_prepare") in danger["text"]
        assert [n["attrs"]["action"] for n in markup.nodes if n["tag"] == "form"
                and any(p is danger for p in n["parents"])] == [SELECT]
        ids = [n["attrs"]["id"] for n in markup.nodes if "id" in n["attrs"]]
        assert len(ids) == len(set(ids))


@pytest.mark.parametrize("overrides", ({"card": ""}, {"card": "X7"}, {"card": ["CA", "C10"]},
    {"card": "C10", "cards": "C10"}, {"card": "C10", "card_selection": "0" * 64}))
def test_malformed_proposals_keep_wire_rejections(localized_server, overrides):
    browser = Browser(localized_server)
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(entry_action(page, 3)))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    assert browser.submit(Forms(page).find(PREVIEW), **overrides)[0] == 400
    assert active.path.read_bytes() == before and active.recovery.preview is None
