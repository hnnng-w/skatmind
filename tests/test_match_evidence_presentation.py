"""Issue #296: accepted evidence, native Hand remedy and source-safe feedback."""

import json
import re
from html import escape

import pytest
from test_direct_match_evidence import evidence_form, independent_form
from test_frontend_language_switching import localized_server as _localized_server
from test_match_card_correction_ui import activated_form, recovery_text
from test_match_recording_recovery_web import declarer_choice, entry_action, follow, operation_form
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.stateful_localization import card_name
from skatmind.match_historical_materialization import materialize_match_observed_game_historical_v1
from skatmind.observed_game_evidence import build_observed_game_evidence_summary_v1

HAND = ("CJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7", "SA", "S10")


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def source_game(browser, locale="en", *, hand=False, name="Alex"):
    page = browser.page("/matches/new")
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
        match_title="Synthetic evidence and rewind", forehand_name=name,
        middlehand_name="Bea", rearhand_name="Chris", perspective_seat="forehand",
        platform_choice="in_person", setup_action="update"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/api/v1/create"),
                                          setup_action="create"))
    page = follow(browser, browser.submit(operation_form(page, "start_game")))
    return follow(browser, browser.submit(operation_form(page, "set_declaration"),
        declarer_player_id=declarer_choice(page, escape(name)), game_type="grand", bid_value="18",
        **({"hand_game": "true"} if hand else {})))


def accepted(page, field):
    tree = Hierarchy(page)
    node = tree.by_id("match-accepted-" + field)
    assert tree.visible(node), "Accepted evidence must be readable before opening any editor"
    return node


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("boundary", (1, 2, 3))
def test_rewind_delivers_visible_exact_chronology(localized_server, locale, boundary):
    browser = Browser(localized_server)
    page = source_game(browser, locale)
    for card in ("SA", "SK", "S7"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    page = follow(browser, browser.submit(entry_action(page, 1)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"),
                                          card="S10"))
    assert "15 → 14" in recovery_text(page)
    page = follow(browser, browser.submit(activated_form(page, "/matches/recovery/apply")))
    active = localized_server.app_context.managed_stateful.active_match
    before, revision = active.path.read_bytes(), active.workspace.revision
    page = follow(browser, browser.submit(entry_action(page, boundary, rewind=True)))
    tree = Hierarchy(page)
    for identity, cards in (("match-rewind-retained", ("S10", "SK", "S7")[:boundary - 1]),
                            ("match-rewind-removed", ("S10", "SK", "S7")[boundary - 1:])):
        node = tree.by_id(identity)
        assert tree.visible(node)
        rows = tree.within(identity, "li")
        assert len(rows) == len(cards)
        assert all(tree.visible(row) for row in rows)
        for row, card in zip(rows, cards, strict=True):
            assert card_name(locale, card) in row["text"]
            assert any(name in row["text"] for name in ("Alex", "Bea", "Chris"))
        if not cards:
            assert "0" in node["text"]
    scope = recovery_text(page)
    assert "0 comment" not in scope and "0 response" not in scope
    assert "0 Kommentare" not in scope and "0 Antwort" not in scope
    assert active.path.read_bytes() == before and active.workspace.revision == revision
    follow(browser, browser.submit(Forms(page).find("/matches/recovery/cancel")))
    assert active.path.read_bytes() == before


@pytest.mark.parametrize("locale", ("de", "en"))
def test_accepted_sources_visible_and_hand_display_is_not_retained_evidence(
    localized_server, locale,
):
    browser = Browser(localized_server)
    page = source_game(browser, locale, hand=True)
    active = localized_server.app_context.managed_stateful.active_match
    original = active.path.read_bytes()
    absent = "nicht erfasst" if locale == "de" else "not recorded"
    for field in ("perspective_initial_hand", "original_skat"):
        assert absent in accepted(page, field)["text"]
    expected = ("Gedrückte Karten: entfällt (Handspiel)" if locale == "de" else
                "Discarded cards: not applicable (Hand game)")
    assert expected in accepted(page, "discarded_cards")["text"]
    assert 'value="discarded_cards_empty"' not in page
    assert 'id="match-hand-evidence"' not in page
    assert 'name="evidence_discarded_cards"' not in page
    assert active.path.read_bytes() == original
    assert active.workspace.slots[0].observed_game.discarded_cards is None
    page = follow(browser, browser.submit(independent_form(
        browser, "set_discarded_cards", "discarded_cards_empty")))
    assert expected in accepted(page, "discarded_cards")["text"]
    assert active.workspace.slots[0].observed_game.discarded_cards == ()
    page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_unknown")))
    assert active.workspace.slots[0].observed_game.discarded_cards is None
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                          cards=HAND))
    assert "Alex" in accepted(page, "perspective_initial_hand")["text"]
    assert len(Hierarchy(page).within("match-accepted-perspective_initial_hand", "span")) >= 10


@pytest.mark.parametrize("prefix,count", (("perspective_hand", 10), ("original_skat", 2),
                                        ("discarded_cards", 2)))
@pytest.mark.parametrize("locale", ("de", "en"))
def test_wrong_count_names_only_the_affected_source(localized_server, prefix, count, locale):
    browser = Browser(localized_server)
    page = source_game(browser, locale)
    form = evidence_form(page, prefix + "_selected")
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    invalids = ([[]] if count == 10 else []) + [
        ["CJ"], list(HAND[:3]) if count == 2 else [*HAND, "H7"]]
    for cards in invalids:
        status, _, raw = browser.submit(form, cards=cards)
        assert status == 400 and active.path.read_bytes() == before
        tree = Hierarchy(raw.decode())
        errors = [n["text"] for n in tree.nodes if n["attrs"].get("class") == "error-summary"]
        assert len(errors) == 1
        assert str(count) in errors[0]
        assert ("10" if count == 2 else "2") not in errors[0]
        assert re.search(r'<fieldset[^>]*aria-invalid="true"', raw.decode())


@pytest.mark.parametrize("locale", ("de", "en"))
def test_cj_overlap_names_actual_accepted_owner_and_valid_skat_discard_overlap(
    localized_server, locale,
):
    browser = Browser(localized_server)
    page = source_game(browser, locale)
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                          cards=HAND))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    status, _, raw = browser.submit(evidence_form(page, "original_skat_selected"),
                                   cards=["CJ", "D7"])
    assert status == 400 and active.path.read_bytes() == before
    summary, = [n for n in Hierarchy(raw.decode()).nodes
                if n["attrs"].get("class") == "error-summary"]
    assert "Alex" in summary["text"] and card_name(locale, "CJ") in summary["text"]
    assert ("Anfangshand" if locale == "de" else "initial hand") in summary["text"]
    page = follow(browser, browser.submit(Forms(raw.decode()).find("/actions/profile/language"),
                                          language="en" if locale == "de" else "de"))
    other = "en" if locale == "de" else "de"
    summary, = [n for n in Hierarchy(page).nodes if n["attrs"].get("class") == "error-summary"]
    assert card_name(other, "CJ") in summary["text"] and "Alex" in summary["text"]
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=["HA", "D7"]))
    follow(browser, browser.submit(evidence_form(page, "discarded_cards_selected"),
                                   cards=["HA", "D7"]))
    game = active.workspace.slots[0].observed_game
    assert set(game.original_skat) == set(game.discarded_cards) == {"HA", "D7"}


@pytest.mark.parametrize("locale", ("de", "en"))
def test_real_save_noop_and_withdrawal_deliver_distinct_one_use_receipts(localized_server, locale):
    browser = Browser(localized_server)
    page = source_game(browser, locale)
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=["HA", "D7"]))
    assert 'data-operation-feedback' in page
    active = localized_server.app_context.managed_stateful.active_match
    saved = active.path.read_bytes()
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected")))
    assert active.path.read_bytes() == saved
    receipt, = [n for n in Hierarchy(page).nodes if "data-operation-feedback" in n["attrs"]]
    assert ("Nichts geändert" if locale == "de" else "Nothing changed") in receipt["text"]
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"), cards=[]))
    receipt, = [n for n in Hierarchy(page).nodes if "data-operation-feedback" in n["attrs"]]
    assert ("entfernt" if locale == "de" else "removed") in receipt["text"]
    assert 'data-operation-feedback' not in browser.page("/matches/position/1")


def complete_hand(browser, locale="en"):
    from test_historical_game import build_historical_input
    from test_local_time_entry_web import local_form

    page = source_game(browser, locale, hand=True)
    page = follow(browser, browser.submit(local_form(page, "match-metadata"),
        time_mode="replace", local_date="2026-01-15", local_time="19:30",
        local_zone="Europe/Berlin"))
    data = build_historical_input(hand_game=True, declarer_player_id="player-a")
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                          cards=data["players"][0]["initial_hand"]))
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=data["skat"]))
    # Existing advanced ordered recording form, not a synthesized evidence owner.
    form = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/operation"
                and f["values"].get("operation") == "append_plays")
    page = follow(browser, browser.submit(form, cards=" ".join(
        p["card"] for trick in data["tricks"] for p in trick["plays"])))
    return page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_complete_hand_readiness_and_legacy_withdrawal_keep_literal_evidence(
    localized_server, monkeypatch, locale,
):
    import skatmind.app_web.frontend_profile_operations as profile
    import skatmind.app_web.match_frontend as frontend
    import skatmind.capture_web.analysis as analysis
    import skatmind.capture_web.context as capture

    browser = Browser(localized_server)
    complete_hand(browser, locale)
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    game = active.workspace.slots[0].observed_game
    result = materialize_match_observed_game_historical_v1(active.workspace, match_position=1)
    assert result.status == "available"
    evidence = build_observed_game_evidence_summary_v1(game)
    assert evidence.complete_initial_deal_reconstructable and not evidence.discarded_cards_known
    assert evidence.all_player_decision_samples_reconstructable
    assert active.workspace.match_definition.played_at is not None
    calls = []
    real = capture.save_match_workspace_file_v1
    def save(*args, **kwargs):
        calls.append("save")
        return real(*args, **kwargs)
    operation = frontend.apply_unified_match_operation_v1
    def operated(context, values):
        calls.append(values["operation"])
        return operation(context, values)
    def forbidden(*args, **kwargs):
        pytest.fail("Evidence must not execute analysis or save the profile")
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    monkeypatch.setattr(frontend, "apply_unified_match_operation_v1", operated)
    monkeypatch.setattr(profile, "save_frontend_profile_file_v1", forbidden)
    monkeypatch.setattr(analysis, "execute_match_decision_analysis_v1", forbidden)
    monkeypatch.setattr(analysis, "execute_match_historical_analysis_v1", forbidden)
    review = browser.page("/matches/review/1")
    assert '#match-hand-evidence' not in review
    assert 'value="discarded_cards_empty"' not in review
    page = browser.page("/matches/position/1")
    assert 'id="match-hand-evidence"' not in page
    assert active.path.read_bytes() == before and not calls
    # The independent compatibility client constructs the legacy retained observation.
    page = follow(browser, browser.submit(independent_form(
        browser, "set_discarded_cards", "discarded_cards_empty")))
    assert calls == ["set_discarded_cards", "save"]
    after = active.workspace.slots[0].observed_game
    assert {k: v for k, v in after.to_dict().items() if k != "discarded_cards"} == {
        k: v for k, v in game.to_dict().items() if k != "discarded_cards"}
    assert build_observed_game_evidence_summary_v1(after).complete_initial_deal_reconstructable
    assert build_observed_game_evidence_summary_v1(after).discarded_cards_known
    assert materialize_match_observed_game_historical_v1(
        active.workspace, match_position=1).status == "available"
    retained = active.path.read_bytes()
    browser.page("/matches/review/1")
    page = browser.page("/matches/position/1")
    assert active.path.read_bytes() == retained and calls == ["set_discarded_cards", "save"]
    page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_unknown")))
    assert calls == ["set_discarded_cards", "save"] * 2
    assert active.workspace.slots[0].observed_game == game
    assert materialize_match_observed_game_historical_v1(
        active.workspace, match_position=1) == result
    assert build_observed_game_evidence_summary_v1(
        active.workspace.slots[0].observed_game) == evidence


def test_hand_empty_withdrawal_allows_later_non_hand_correction(localized_server):
    browser = Browser(localized_server)
    page = source_game(browser, hand=True)
    page = follow(browser, browser.submit(independent_form(
        browser, "set_discarded_cards", "discarded_cards_empty")))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    form = operation_form(page, "set_declaration")
    values = {k: v for k, v in form["values"].items() if k != "hand_game"}
    assert browser.request("POST", form["action"], values)[0] == 400
    assert active.path.read_bytes() == before
    page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_unknown")))
    form = operation_form(page, "set_declaration")
    values = {k: v for k, v in form["values"].items() if k != "hand_game"}
    page = follow(browser, browser.request("POST", form["action"], values))
    assert not active.workspace.slots[0].observed_game.declaration.hand_game
    assert 'name="evidence_discarded_cards"' in page


def test_overlap_witness_reverse_escaping_and_stale_source(localized_server):
    browser = Browser(localized_server)
    label = "Alex <&> " + "Long-name-" * 10
    page = source_game(browser, name=label)
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                          cards=HAND))
    form = evidence_form(page, "original_skat_selected")
    status, _, raw = browser.submit(form, cards=["CJ", "D7"])
    assert status == 400
    assert "Alex &lt;&amp;&gt; " in raw.decode()
    assert label in Hierarchy(raw.decode()).by_id("match-accepted-perspective_initial_hand")["text"]
    browser.page("/matches/position/2")
    browser.page("/matches/position/1")
    status, _, raw = browser.submit(form, cards=["CJ", "D7"])
    assert status == 409
    summary, = [n for n in Hierarchy(raw.decode()).nodes
                if n["attrs"].get("class") == "error-summary"]
    assert label not in summary["text"] and card_name("en", "CJ") not in summary["text"]
    page = follow(browser, browser.submit(evidence_form(raw.decode(), "perspective_hand_unknown")))
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=["CJ", "D7"]))
    status, _, raw = browser.submit(evidence_form(page, "perspective_hand_selected"), cards=HAND)
    assert status == 400
    summary, = [n for n in Hierarchy(raw.decode()).nodes
                if n["attrs"].get("class") == "error-summary"]
    assert card_name("en", "CJ") in summary["text"] and "recorded original Skat" in summary["text"]


@pytest.mark.parametrize("marker,key", (("original_skat_selected", "unchanged"),
    ("original_skat_unknown", "evidence_removed"), ("discarded_cards_empty", "evidence_empty")))
def test_evidence_receipt_language_continuation_keeps_identity_and_deadline(
    localized_server, marker, key,
):
    from test_operation_feedback_language import bound_page, continued, presentation
    from test_task_first_language_preservation import enhanced_switch

    browser = Browser(localized_server)
    page = source_game(browser, hand=True)
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=["HA", "D7"]))
    if marker == "discarded_cards_empty":
        page = follow(browser, browser.submit(independent_form(
            browser, "set_discarded_cards", marker)))
    else:
        page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
            **({"cards": []} if marker.endswith("_unknown") else {})))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    receipt = bound_page(localized_server, page).feedback.receipt
    assert receipt.message_key == "feedback." + key
    for locale, remaining in (("de", 4000), ("en", 2000)):
        page = follow(browser, enhanced_switch(browser, page,
            json.dumps(presentation(page, remaining, locale)), locale))
        continued(page, key, locale, remaining)
        assert bound_page(localized_server, page).feedback.receipt is receipt
        assert active.path.read_bytes() == before
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    assert 'data-operation-feedback' not in page
