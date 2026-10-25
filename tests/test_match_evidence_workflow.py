"""Issue #297 accepted-state evidence workflow over final HTTP-delivered forms."""

import json

import pytest
from test_direct_match_evidence import evidence_form
from test_frontend_language_switching import localized_server as _localized_server
from test_match_declaration_drafts import NativePage
from test_match_evidence_presentation import HAND, source_game
from test_match_person_review_actions import action_form, fresh_roster
from test_match_recording_recovery_web import follow, operation_form
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def source_editors(page):
    tree = Hierarchy(page)
    return [node for node in tree.within("match-evidence", "details")
            if "match-source-editor" in node["attrs"].get("class", "").split()]


def test_review_result_is_the_named_focus_target_beside_create(localized_server):
    browser = Browser(localized_server)
    page, values, _ = fresh_roster(browser, "new")
    response = browser.submit(action_form(page, "choose_middlehand"), **values)
    assert response[0] == 303
    assert response[1]["location"].endswith("#match-setup-review")
    page = follow(browser, response)
    tree = Hierarchy(page)
    summary = tree.by_id("match-setup-review")
    assert summary["attrs"]["tabindex"] == "-1"
    assert summary["text"] == "Reviewed recording perspective: Bea"
    create, = [node for node in tree.nodes if node["tag"] == "button"
               and node["attrs"].get("value") == "create"]
    assert tree.visible(summary) and tree.visible(create)
    assert summary["parents"][-1] is create["parents"][-1]
    assert tree.nodes.index(create) == tree.nodes.index(summary) + 1
    assert len([n for n in tree.nodes if "reviewed-perspective" in
                n["attrs"].get("class", "").split()]) == 1


def test_sources_precede_play_and_overview_with_one_native_editor_each(localized_server):
    browser = Browser(localized_server)
    page = source_game(browser, name="Anna")
    editors = source_editors(page)
    assert len(editors) == 3
    assert [e["attrs"]["data-source"] for e in editors if "open" in e["attrs"]] == [
        "perspective_initial_hand"]
    tree = Hierarchy(page)
    for editor in editors:
        assert not any(p["tag"] == "details" for p in editor["parents"])
        assert any(p["attrs"].get("id") == "match-recording" for p in editor["parents"])
    assert page.index('id="match-evidence"') < page.index('action="/matches/cards"')
    assert page.index('id="match-evidence"') < page.index('id="match-games"')
    assert tree.by_id("match-recording-perspective")["text"] == "Recording perspective: Anna"


def test_missing_sources_explain_unchanged_candidates_and_advance_opening(localized_server):
    browser = Browser(localized_server)
    page = source_game(browser, name="Anna")
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                          cards=HAND))
    for missing, prefix in (("both", "original_skat"), ("discards", "discarded_cards")):
        tree = Hierarchy(page)
        explanation = tree.by_id("match-card-selection-help")["text"]
        assert "Anna" in explanation and "discarded cards" in explanation
        assert ("original Skat" in explanation) == (missing == "both")
        assert len([c for c in NativePage(page).controls
                    if c.get("name") == "cards" and c.get("type") == "radio"]) == 32
        assert [e["attrs"]["data-source"] for e in source_editors(page)
                if "open" in e["attrs"]] == [prefix]
        page = follow(browser, browser.submit(evidence_form(page, prefix + "_selected"),
                                              cards=["HA", "D7"]))
    assert not any("open" in e["attrs"] for e in source_editors(page))
    assert {c["value"] for c in NativePage(page).controls if c.get("name") == "cards"
            and c.get("type") == "radio"} == set(HAND)


@pytest.mark.parametrize("prefix", ("original_skat", "discarded_cards"))
def test_native_selected_zero_withdraws_only_chosen_source_then_is_noop(
    localized_server, monkeypatch, prefix,
):
    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    page = source_game(browser)
    for source in ("original_skat", "discarded_cards"):
        page = follow(browser, browser.submit(evidence_form(page, source + "_selected"),
                                              cards=["HA", "D7"]))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.workspace.slots[0].observed_game.to_dict()
    calls = []
    real = capture.save_match_workspace_file_v1
    def save(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    native = NativePage(page)
    native.choose(prefix, ())
    response = native.submit(browser, prefix + "_selected")
    assert response[0] == 303
    page = follow(browser, response)
    before[prefix] = None
    assert active.workspace.slots[0].observed_game.to_dict() == before
    assert calls == [1]
    saved = active.path.read_bytes()
    page = follow(browser, NativePage(page).submit(browser, prefix + "_selected"))
    assert active.path.read_bytes() == saved and calls == [1]
    assert "Nothing changed" in page
    assert not any(c.get("value") == prefix + "_unknown" for c in NativePage(page).controls)


@pytest.mark.parametrize("declared", (False, True))
def test_normal_ui_never_offers_explicit_empty_entry(localized_server, declared):
    from test_direct_match_evidence import started

    browser = Browser(localized_server)
    page = source_game(browser, hand=True) if declared else started(browser)
    assert not any(c.get("value") == "discarded_cards_empty" for c in NativePage(page).controls)


@pytest.mark.parametrize("kind,opened", (
    ("empty", None), ("passed", None), ("missing_hand", "perspective_initial_hand"),
    ("undeclared", None), ("defender", None), ("hand", None),
    ("missing_both", "original_skat"), ("missing_skat", "original_skat"),
    ("missing_discards", "discarded_cards"), ("known", None), ("played", None),
    ("complete", None),
))
def test_server_source_opening_policy_uses_only_accepted_state(localized_server, kind, opened):
    from test_direct_match_evidence import started
    from test_match_evidence_presentation import complete_hand
    from test_match_game_navigation_web import create_empty

    browser = Browser(localized_server)
    if kind in {"empty", "passed"}:
        page = create_empty(browser, "en")
        if kind == "passed":
            page = follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
        assert 'id="match-evidence"' not in page
        return
    if kind == "complete":
        page = complete_hand(browser)
    elif kind == "undeclared":
        page = started(browser)
        page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                              cards=HAND))
    else:
        page = source_game(browser, hand=kind == "hand", name="Anna")
        if kind == "defender":
            native = NativePage(page)
            native.enter(declarer_player_id=native.declarer("Bea"))
            page = follow(browser, native.submit(browser, "set_declaration"))
        if kind not in {"missing_hand", "played"}:
            page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                                  cards=HAND))
        for prefix, permitted in (("original_skat", {"missing_discards", "known"}),
                                  ("discarded_cards", {"missing_skat", "known"})):
            if kind in permitted:
                page = follow(browser, browser.submit(evidence_form(page, prefix + "_selected"),
                                                      cards=["HA", "D7"]))
        if kind == "played":
            page = follow(browser, browser.submit(
                operation_form(page, "append_plays"), cards="S10"))
    assert [e["attrs"]["data-source"] for e in source_editors(page) if "open" in e["attrs"]] == (
        [] if opened is None else [opened])
    before = localized_server.app_context.managed_stateful.active_match.path.read_bytes()
    page = follow(browser, browser.submit(
        Forms(page).find("/actions/profile/language"), language="de"))
    assert [e["attrs"]["data-source"] for e in source_editors(page) if "open" in e["attrs"]] == (
        [] if opened is None else [opened])
    assert localized_server.app_context.managed_stateful.active_match.path.read_bytes() == before


@pytest.mark.parametrize("prefix", ("perspective_hand", "original_skat", "discarded_cards"))
def test_rejected_source_overrides_default_and_closed_language_overlay(localized_server, prefix):
    browser = Browser(localized_server)
    page = source_game(browser)
    response = browser.submit(evidence_form(page, prefix + "_selected"), cards=["H7"])
    assert response[0] == 400
    page = response[2].decode()
    source = "perspective_initial_hand" if prefix == "perspective_hand" else prefix
    for language in (None, "de"):
        if language:
            page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                language=language, _frontend_language_values=json.dumps({"forms": [],
                    "disclosures": [False] * page.count("<details")})))
        opened = [e["attrs"]["data-source"] for e in source_editors(page) if "open" in e["attrs"]]
        assert opened == [source]
        tree = Hierarchy(page)
        summary, = [n for n in tree.nodes if n["attrs"].get("class") == "error-summary"]
        assert tree.visible(summary) and "autofocus" in summary["attrs"]
        assert any(p["attrs"].get("data-source") == source for p in summary["parents"])


def test_enhanced_closed_source_survives_language_without_changing_accepted_facts(localized_server):
    browser = Browser(localized_server)
    page = source_game(browser)
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
        language="de", _frontend_language_values=json.dumps({"forms": [],
            "disclosures": [False] * page.count("<details")})))
    assert not any("open" in e["attrs"] for e in source_editors(page))
    assert active.path.read_bytes() == before
    assert [e["attrs"]["data-source"] for e in source_editors(browser.page("/matches/position/1"))
            if "open" in e["attrs"]] == ["perspective_initial_hand"]


@pytest.mark.parametrize("hand,declarer", ((True, "Anna"), (False, "Bea")))
def test_exact_hand_or_defender_needs_no_skat_then_opponent_copy(localized_server, hand, declarer):
    browser = Browser(localized_server)
    page = source_game(browser, hand=hand, name="Anna")
    if declarer != "Anna":
        native = NativePage(page)
        native.enter(declarer_player_id=native.declarer(declarer))
        page = follow(browser, native.submit(browser, "set_declaration"))
    page = follow(browser, browser.submit(
        evidence_form(page, "perspective_hand_selected"), cards=HAND))
    assert Hierarchy(page).by_id("match-card-selection-help")["text"] == (
        "Choose a legal card from Anna's known playable hand.")
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards="S10"))
    explanation = Hierarchy(page).by_id("match-card-selection-help")["text"]
    assert explanation == ("Bea's hand is not known through the recording perspective. "
                           "Choose the card actually observed.")
    assert not any("open" in e["attrs"] for e in source_editors(page))


def test_pending_declarer_and_hand_do_not_change_source_policy_or_explanation(localized_server):
    browser = Browser(localized_server)
    page = source_game(browser, name="Anna")
    page = follow(browser, browser.submit(
        evidence_form(page, "perspective_hand_selected"), cards=HAND))
    expected = Hierarchy(page).by_id("match-card-selection-help")["text"]
    native = NativePage(page)
    native.enter(declarer_player_id=native.declarer("Bea"), hand_game=True)
    # Equal hand Save is a no-op carrying only the unsaved declaration presentation.
    page = follow(browser, native.submit(browser, "perspective_hand_selected"))
    assert Hierarchy(page).by_id("match-card-selection-help")["text"] == expected
    opened = [e["attrs"]["data-source"] for e in source_editors(page) if "open" in e["attrs"]]
    assert opened == ["original_skat"]


@pytest.mark.parametrize("prefix", ("original_skat", "discarded_cards"))
@pytest.mark.parametrize("cards", ([""], ["bad"], ["H7", "H7"], ["H7"], ["H7", "D7", "D8"]))
def test_two_card_malformed_or_nonzero_count_never_becomes_withdrawal(
    localized_server, prefix, cards,
):
    browser = Browser(localized_server)
    page = source_game(browser)
    page = follow(browser, browser.submit(
        evidence_form(page, prefix + "_selected"), cards=["HA", "D7"]))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    response = browser.submit(evidence_form(page, prefix + "_selected"), cards=cards)
    assert response[0] == 400 and active.path.read_bytes() == before
    if len(cards) in {1, 3} and cards[0] == "H7":
        assert "deselect all and Save" in response[2].decode()


def test_legacy_empty_native_withdrawal_keeps_unchecked_declaration_draft(localized_server):
    from test_direct_match_evidence import independent_form

    browser = Browser(localized_server)
    page = source_game(browser, hand=True)
    page = follow(browser, browser.submit(independent_form(
        browser, "set_discarded_cards", "discarded_cards_empty")))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    native = NativePage(page)
    native.enter(hand_game=False, bid_value="24")
    response = native.submit(browser, "set_declaration")
    assert response[0] == 400 and active.path.read_bytes() == before
    native = NativePage(response[2].decode())
    action = native.button("discarded_cards_unknown")
    assert native.owner(action) is native.owner(native.field("hand_game"))
    assert "formnovalidate" in action
    page = follow(browser, native.submit(browser, "discarded_cards_unknown"))
    game = active.workspace.slots[0].observed_game
    assert game.discarded_cards is None and game.declaration.hand_game
    assert game.declaration.bid_value == 18
    native = NativePage(page)
    assert "checked" not in native.field("hand_game") and native.field("bid_value")["value"] == "24"
    assert 'value="discarded_cards_unknown"' not in page
    follow(browser, native.submit(browser, "set_declaration"))
    assert not active.workspace.slots[0].observed_game.declaration.hand_game
    assert active.workspace.slots[0].observed_game.declaration.bid_value == 24


@pytest.mark.parametrize("prefix", ("original_skat", "discarded_cards"))
@pytest.mark.parametrize("fault", ("save", "stale", "foreign", "ambiguous", "extra"))
def test_selected_zero_checks_authority_and_persistence_before_acceptance(
    localized_server, monkeypatch, prefix, fault,
):
    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    page = source_game(browser)
    page = follow(browser, browser.submit(
        evidence_form(page, prefix + "_selected"), cards=["HA", "D7"]))
    active = localized_server.app_context.managed_stateful.active_match
    before, workspace = active.path.read_bytes(), active.workspace
    native = NativePage(page)
    native.choose(prefix, ())
    route, values = native.submission(prefix + "_selected")
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise OSError("Synthetic pre-replacement failure")
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", fail)
    if fault == "stale":
        browser.page("/matches/position/2")
        browser.page("/matches/position/1")
    elif fault == "foreign":
        values["managed_handle"] = "f" * 64
    elif fault == "ambiguous":
        values["recording_action"] = [prefix + "_selected", "set_declaration"]
    elif fault == "extra":
        values["unsupported"] = ""
    status, _, raw = browser.request("POST", route, values)
    assert status == (400 if fault in {"ambiguous", "extra"} else 409)
    assert calls == ([1] if fault == "save" else [])
    assert active.path.read_bytes() == before and active.workspace is workspace
    assert 'data-operation-feedback' not in raw.decode()


def test_absent_zero_save_preserves_real_report_and_download(localized_server, monkeypatch):
    from test_recorded_decision_context_web import record_context_match

    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    record_context_match(browser)
    page = follow(browser, browser.submit(operation_form(
        browser.page("/matches/review/1"), "analyze_decision")))
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    download = f"/matches/api/v1/reports/{report.report_id}.json"
    retained, before = browser.request("GET", download)[2], active.path.read_bytes()
    assert active.workspace.slots[0].observed_game.original_skat is None
    def forbidden(*args, **kwargs):
        pytest.fail("Already-absent zero Save attempted persistence")
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", forbidden)
    native = NativePage(browser.page("/matches/position/1"))
    native.choose("original_skat", ())
    page = follow(browser, native.submit(browser, "original_skat_selected"))
    assert "Nothing changed" in page
    assert active.capture.report_store.list() == (report,)
    assert browser.request("GET", download)[2] == retained
    assert active.path.read_bytes() == before
