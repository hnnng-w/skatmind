"""Direct native evidence intent over real observed-Game saves and emitted forms."""

import json
import re

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_game_navigation_web import create_empty
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_decision_context import MATCH_HAND
from test_recorded_decision_context_web import record_context_match
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.form_registry import FRONTEND_FORM_REGISTRY, resolve_frontend_form_v1
from skatmind.app_web.language_form_preservation import instrument_language_forms_v1
from skatmind.match_capture_application import set_match_capture_original_skat_v1
from skatmind.match_workspace_contracts import _build_match_workspace_v1
from skatmind.match_workspace_persistence import (
    build_match_workspace_persistence_document_v1,
    load_match_workspace_file_v1,
    save_match_workspace_file_v1,
)

VARIANTS = (
    ("set_perspective_hand", "perspective_hand_selected", "exact"),
    ("set_perspective_hand", "perspective_hand_unknown", "unknown"),
    ("set_original_skat", "original_skat_selected", "exact"),
    ("set_original_skat", "original_skat_unknown", "unknown"),
    ("set_discarded_cards", "discarded_cards_selected", "exact"),
    ("set_discarded_cards", "discarded_cards_unknown", "unknown"),
    ("set_discarded_cards", "discarded_cards_empty", "known_empty"),
)


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def evidence_form(page, marker):
    return next(form for form in Forms(page).forms
                if form["action"] == "/matches/cards"
                and form["values"].get("card_evidence_form") == marker)


def test_emitted_direct_save_has_no_mode_prerequisite(localized_server):
    browser = Browser(localized_server)
    page = record_context_match(browser, with_hand=False)
    form = operation_form(page, "set_perspective_hand")
    assert "card_evidence_mode" not in form["values"]
    assert form["values"]["card_evidence_form"] == "perspective_hand_selected"
    assert set(form["values"]) == {
        "managed_handle", "card_selection", "operation", "card_evidence_form",
        "_frontend_form_instance"}
    active = localized_server.app_context.managed_stateful.active_match
    before = active.workspace.revision
    follow(browser, browser.submit(form, cards=MATCH_HAND))
    assert active.workspace.revision == before + 1
    assert active.workspace.slots[0].observed_game.perspective_initial_hand == MATCH_HAND


def test_legacy_selected_unknown_deliberately_disregards_valid_cards(localized_server):
    browser = Browser(localized_server)
    page = record_context_match(browser, with_hand=False)
    # Explicit legacy transport fixture, not a helper that repairs emitted fields.
    emitted = operation_form(page, "set_perspective_hand")["values"]
    legacy = {key: emitted[key] for key in ("managed_handle", "card_selection", "operation")}
    legacy.update(card_evidence_mode="unknown", cards=list(MATCH_HAND))
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    follow(browser, browser.request("POST", "/matches/cards", legacy))
    assert active.workspace.slots[0].observed_game.perspective_initial_hand is None
    assert active.path.read_bytes() == before


def started(browser, context="undeclared", locale="en"):
    page = follow(browser, browser.submit(operation_form(
        create_empty(browser, locale), "start_game")))
    if context != "undeclared":
        options = re.search(r'<select name="declarer_player_id"[^>]*>(.*?)</select>', page, re.S)[1]
        declarer = re.findall(r'<option value="([^"]+)"', options)[0]
        page = follow(browser, browser.submit(operation_form(page, "set_declaration"),
            declarer_player_id=declarer, game_type="grand",
            **({"hand_game": "true"} if context == "hand" else {})))
    return page


def block_for(page, marker):
    return next(block for block in re.findall(r'<form\b.*?</form>', page, re.S)
                if f'name="card_evidence_form" value="{marker}"' in block)


@pytest.mark.parametrize("context", ("undeclared", "hand", "non_hand"))
@pytest.mark.parametrize("locale,save,withdraw,empty", (
    ("en", "Save selected Cards", "Remove saved initial hand",
     "Record that no Cards were discarded"),
    ("de", "Ausgewählte Karten speichern", "Gespeicherte Anfangshand entfernen",
     "Festhalten: keine Karten gedrückt"),
))
def test_native_shapes_eligibility_and_independent_literal_captions(
    localized_server, context, locale, save, withdraw, empty,
):
    browser = Browser(localized_server)
    page = started(browser, context, locale)
    markers = {form["values"]["card_evidence_form"] for form in Forms(page).forms
               if "card_evidence_form" in form["values"]}
    expected = {"perspective_hand_selected", "original_skat_selected"}
    if context != "hand":
        expected.add("discarded_cards_selected")
    if context != "non_hand":
        expected.add("discarded_cards_empty")
    assert markers == expected
    assert 'name="card_evidence_mode"' not in page
    for marker in expected:
        form = evidence_form(page, marker)
        assert set(form["values"]) == {"managed_handle", "operation", "card_selection",
                                        "card_evidence_form", "_frontend_form_instance"}
        block = block_for(page, marker)
        assert block.count('<button') == 1
        assert ('<fieldset' in block) == marker.endswith("_selected")
        if marker.endswith("_selected"):
            assert save in block and 'class="primary"' in block
        else:
            assert empty in block
            assert not re.search(r'<(?:select|textarea)|<input(?![^>]*type="hidden")', block)
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected"),
                                          cards=MATCH_HAND))
    assert withdraw in block_for(page, "perspective_hand_unknown")
    _, manifest = instrument_language_forms_v1(page)
    assert all(field.field_key not in {"card_selection", "card_evidence_form", "operation"}
               for form in manifest.forms for field in form.fields)


@pytest.mark.parametrize("operation,marker,mode", VARIANTS)
def test_exact_new_and_legacy_registry_identity(operation, marker, mode):
    definition = resolve_frontend_form_v1("/matches/cards", {
        "operation": operation, "card_evidence_form": marker})
    assert definition.form_key == "match.evidence." + marker
    assert definition.body_limit == 8192
    assert {field.field_key for field in definition.safe_fields} == (
        {"card_selection", "cards"} if mode == "exact" else {"card_selection"})
    legacy = resolve_frontend_form_v1("/matches/cards", {
        "operation": operation, "card_evidence_mode": mode})
    assert legacy.form_key == "match.cards." + operation
    assert len(FRONTEND_FORM_REGISTRY) == 119


@pytest.mark.parametrize("prefix,field,cards", (
    ("perspective_hand", "perspective_initial_hand", MATCH_HAND),
    ("original_skat", "original_skat", ("SA", "S7")),
    ("discarded_cards", "discarded_cards", ("SA", "S7")),
))
def test_unknown_known_empty_selection_and_withdrawal_transitions(
    localized_server, monkeypatch, prefix, field, cards,
):
    import skatmind.capture_web.context as capture
    browser = Browser(localized_server)
    page = started(browser)
    active = localized_server.app_context.managed_stateful.active_match
    saves = []
    real = capture.save_match_workspace_file_v1
    def save(*args, **kwargs):
        saves.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", save)
    before, revision = active.path.read_bytes(), active.workspace.revision
    selected = evidence_form(page, prefix + "_selected")
    for invalid in ([], [""], list(cards[:-1]), [cards[0], cards[0]], ["invalid"]):
        response = browser.submit(selected, cards=invalid)
        assert response[0] == 400
        assert active.path.read_bytes() == before and not saves
        assert 'href="#validation-field-' in response[2].decode()
        assert re.search(r'<fieldset[^>]*aria-invalid="true"', response[2].decode())
    page = follow(browser, browser.submit(selected, cards=list(reversed(cards))))
    assert len(saves) == 1 and active.workspace.revision == revision + 1
    assert set(getattr(active.workspace.slots[0].observed_game, field)) == set(cards)
    before = active.path.read_bytes()
    selected = evidence_form(page, prefix + "_selected")
    page = follow(browser, browser.submit(selected, cards=cards))
    assert len(saves) == 1 and active.path.read_bytes() == before
    assert browser.submit(selected, cards=[])[0] == 400
    assert active.path.read_bytes() == before
    withdrawal = evidence_form(page, prefix + "_unknown")
    assert "cards" not in withdrawal["values"]
    for extra in ("", cards[0], list(cards)):
        assert browser.submit(withdrawal, cards=extra)[0] == 400
        assert active.path.read_bytes() == before and len(saves) == 1
    page = follow(browser, browser.submit(withdrawal))
    assert len(saves) == 2 and active.workspace.revision == revision + 2
    assert getattr(active.workspace.slots[0].observed_game, field) is None
    game_json = active.workspace.slots[0].observed_game.to_dict()
    assert field in game_json and game_json[field] is None
    # Supported transport no-op without a redundant unknown-to-unknown button.
    current = evidence_form(page, prefix + "_selected")
    values = {**current["values"], "card_evidence_form": prefix + "_unknown"}
    follow(browser, browser.request("POST", "/matches/cards", values))
    assert len(saves) == 2
    assert load_match_workspace_file_v1(active.path).document.workspace == active.workspace


@pytest.mark.parametrize("context", ("undeclared", "hand", "non_hand"))
def test_explicit_empty_legality_noop_and_no_nonempty_hand_grid(localized_server, context):
    browser = Browser(localized_server)
    page = started(browser, context)
    active = localized_server.app_context.managed_stateful.active_match
    before, revision = active.path.read_bytes(), active.workspace.revision
    if context == "non_hand":
        values = {**evidence_form(page, "discarded_cards_selected")["values"],
                  "card_evidence_form": "discarded_cards_empty"}
        assert browser.request("POST", "/matches/cards", values)[0] == 400
        assert active.path.read_bytes() == before
        return
    page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_empty")))
    assert active.workspace.revision == revision + 1
    assert active.workspace.slots[0].observed_game.to_dict()["discarded_cards"] == []
    saved = active.path.read_bytes()
    page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_empty")))
    assert active.path.read_bytes() == saved
    if context == "undeclared":
        assert browser.submit(evidence_form(page, "discarded_cards_selected"))[0] == 400
        assert active.path.read_bytes() == saved
        page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_selected"),
                                              cards=["SA", "S7"]))
        page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_empty")))
        assert active.workspace.slots[0].observed_game.discarded_cards == ()
    else:
        assert 'value="discarded_cards_selected"' not in page
        values = {**evidence_form(page, "discarded_cards_empty")["values"],
                  "card_evidence_form": "discarded_cards_selected", "cards": ["SA", "S7"]}
        assert browser.request("POST", "/matches/cards", values)[0] == 400
    page = follow(browser, browser.submit(evidence_form(page, "discarded_cards_unknown")))
    assert active.workspace.slots[0].observed_game.discarded_cards is None


def test_strict_multimaps_authorization_and_legacy_preliminary_validation(localized_server):
    browser = Browser(localized_server)
    page = started(browser)
    form = evidence_form(page, "original_skat_selected")
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    base = form["values"]
    invalids = [
        {**base, "card_evidence_mode": "exact"},
        {**base, "card_evidence_form": "bad"},
        {**base, "card_evidence_form": "perspective_hand_selected"},
        {**base, "position": "1"}, {**base, "player_id": "forged"},
        {**base, "expected_revision": "1"}, {**base, "extra": ""},
        {key: value for key, value in base.items() if key != "card_evidence_form"},
    ]
    invalids += [{**base, field: [value, value]} for field, value in base.items()]
    for values in invalids:
        assert browser.request("POST", "/matches/cards",
                               {**values, "cards": ["SA", "S7"]})[0] == 400
    for headers in ({"Origin": "null"}, {"Cookie": ""}, {"Origin": "http://foreign.invalid"}):
        assert browser.request("POST", "/matches/cards", base, headers=headers)[0] == 403
    legacy = {key: value for key, value in base.items() if key != "card_evidence_form"}
    for mode in ("unknown", "exact"):
        for cards in (["bad"], ["SA", "SA"], ["SA", "S7", "S8"], [""]):
            assert browser.request("POST", "/matches/cards",
                {**legacy, "card_evidence_mode": mode, "cards": cards})[0] == 400
    assert active.path.read_bytes() == before
    for cards in ([], ["SA", "S7"]):
        follow(browser, browser.request("POST", "/matches/cards",
            {**legacy, "card_evidence_mode": "unknown", "cards": cards}))
    assert active.path.read_bytes() == before
    # Legacy empty mode intentionally ignores valid within-capacity Cards as before.
    empty = evidence_form(page, "discarded_cards_empty")["values"]
    legacy = {key: value for key, value in empty.items() if key != "card_evidence_form"}
    follow(browser, browser.request("POST", "/matches/cards",
        {**legacy, "card_evidence_mode": "known_empty", "cards": ["SA", "S7"]}))
    assert active.workspace.slots[0].observed_game.discarded_cards == ()


def test_legacy_rejection_bridges_only_current_source_to_new_visible_editor(localized_server):
    browser = Browser(localized_server)
    page = record_context_match(browser, with_hand=False)
    selected = evidence_form(page, "perspective_hand_selected")["values"]
    legacy = {key: value for key, value in selected.items() if key != "card_evidence_form"}
    legacy.update(card_evidence_mode="exact", cards=["C7"])
    status, _, raw = browser.request("POST", "/matches/cards", legacy)
    assert status == 400
    page = raw.decode()
    assert evidence_form(page, "perspective_hand_selected")["values"]["cards"] == "C7"
    assert re.search(r'<fieldset[^>]*aria-invalid="true"', page)
    assert 'name="card_evidence_mode"' not in page
    browser.page("/matches/position/2")
    browser.page("/matches/position/1")
    status, _, raw = browser.request("POST", "/matches/cards", legacy)
    assert status == 409 and 'href="#match-recording"' in raw.decode()
    assert "cards" not in evidence_form(raw.decode(), "perspective_hand_selected")["values"]


@pytest.mark.parametrize("fault", ("save", "cas", "equal_revision"))
def test_real_candidate_failure_and_external_source_are_not_published(
    localized_server, monkeypatch, fault,
):
    import skatmind.capture_web.context as capture
    browser = Browser(localized_server)
    page = started(browser)
    form = evidence_form(page, "perspective_hand_selected")
    active = localized_server.app_context.managed_stateful.active_match
    workspace, raw = active.workspace, active.path.read_bytes()
    real = capture.save_match_workspace_file_v1
    alternate = set_match_capture_original_skat_v1(workspace, match_position=1,
        cards=("SA", "S7"), expected_revision=workspace.revision).workspace_change.workspace
    if fault == "equal_revision":
        alternate = _build_match_workspace_v1(revision=workspace.revision,
            slots=alternate.slots, match_definition=alternate.match_definition)
    other = build_match_workspace_persistence_document_v1(alternate)
    calls = []
    def fail(*args, **kwargs):
        calls.append(args)
        if fault == "save":
            raise OSError("Synthetic pre-replacement failure")
        save_match_workspace_file_v1(active.path, other,
            expected_content_fingerprint=active.capture.content_fingerprint)
        return real(*args, **kwargs)
    if fault == "equal_revision":
        save_match_workspace_file_v1(active.path, other,
            expected_content_fingerprint=active.capture.content_fingerprint)
    else:
        monkeypatch.setattr(capture, "save_match_workspace_file_v1", fail)
    status, _, body = browser.submit(form, cards=MATCH_HAND)
    assert status == 409 and active.workspace is workspace
    assert len(calls) == (0 if fault == "equal_revision" else 1)
    if fault == "save":
        assert active.path.read_bytes() == raw
    else:
        assert load_match_workspace_file_v1(active.path).document == other
        assert "cards" not in evidence_form(body.decode(), "perspective_hand_selected")["values"]
        assert 'href="#match-recording"' in body.decode()


@pytest.mark.parametrize("injected", ("card_selection", "managed_handle", "operation",
                                     "card_evidence_form", "card_evidence_mode", "confirm_clear"))
def test_language_overlay_cannot_supply_evidence_authority(localized_server, injected):
    browser = Browser(localized_server)
    page = started(browser)
    block = block_for(page, "original_skat_selected")
    identity = re.search(r'data-language-form="([^"]+)"', block)[1]
    raw = json.dumps({"forms": [{"form": identity, "values": {injected: ["forged"]}}],
                      "disclosures": [False] * page.count('<details')})
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    assert browser.submit(Forms(page).find("/actions/profile/language"), language="de",
                          _frontend_language_values=raw)[0] == 400
    assert active.path.read_bytes() == before


def test_noop_keeps_real_report_recovery_preview_but_may_clear_diagnostic(localized_server):
    browser = Browser(localized_server)
    record_context_match(browser)
    page = follow(browser, browser.submit(operation_form(browser.page("/matches/review/1"),
                                                        "analyze_decision")))
    active = localized_server.app_context.managed_stateful.active_match
    report, = active.capture.report_store.list()
    download = f"/matches/api/v1/reports/{report.report_id}.json"
    retained = browser.request("GET", download)[2]
    page = browser.page("/matches/position/1")
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="CA"))
    selected, preview = active.recovery.selected, active.recovery.preview
    before = active.path.read_bytes()
    page = follow(browser, browser.submit(evidence_form(page, "perspective_hand_selected")))
    assert active.path.read_bytes() == before
    assert active.recovery.selected is selected and active.recovery.preview is preview
    assert browser.request("GET", download)[2] == retained
    follow(browser, browser.submit(evidence_form(page, "perspective_hand_unknown")))
    assert active.recovery.selected is active.recovery.preview is None
    assert active.capture.report_store.list() == ()


@pytest.mark.parametrize("cards", ([], ["SA", "S7"]))
def test_exact_source_language_selection_and_native_rejection_return(localized_server, cards):
    browser = Browser(localized_server)
    page = started(browser)
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=["SA", "S7"]))
    active = localized_server.app_context.managed_stateful.active_match
    saved = active.path.read_bytes()
    block = block_for(page, "original_skat_selected")
    identity = re.search(r'data-language-form="([^"]+)"', block)[1]
    raw = json.dumps({"forms": [{"form": identity, "values": {"cards": cards}}],
                      "disclosures": [False] * page.count('<details')})
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
        language="de", _frontend_language_values=raw))
    assert evidence_form(page, "original_skat_selected")["values"].get("cards", []) == cards
    assert active.path.read_bytes() == saved
    status, _, raw = browser.submit(evidence_form(page, "original_skat_selected"), cards=["SA"])
    assert status == 400
    page = follow(browser, browser.submit(Forms(raw.decode()).find("/actions/profile/language"),
                                          language="en"))
    assert evidence_form(page, "original_skat_selected")["values"]["cards"] == "SA"
    assert active.path.read_bytes() == saved
    assert 'value="original_skat_unknown"' in page


def test_all_action_markers_keep_movement_and_reload_source_guards(localized_server):
    browser = Browser(localized_server)
    page = started(browser)
    for prefix, cards in (("perspective_hand", MATCH_HAND), ("original_skat", ("SA", "S7")),
                          ("discarded_cards", ("SA", "S7"))):
        page = follow(browser, browser.submit(evidence_form(page, prefix + "_selected"),
                                              cards=cards))
    active = localized_server.app_context.managed_stateful.active_match
    forms = [evidence_form(page, marker) for _, marker, _ in VARIANTS]
    before = active.path.read_bytes()
    browser.page("/matches/position/2")
    browser.page("/matches/position/1")
    for form in forms:
        status, _, raw = browser.submit(form)
        assert status == 409
        assert 'href="#match-recording"' in raw.decode()
        assert 'href="#validation-field-' not in raw.decode()
    assert active.path.read_bytes() == before
    current = evidence_form(browser.page("/matches/position/1"), "original_skat_unknown")
    page = follow(browser, browser.submit(Forms(browser.page("/matches/position/1")).find(
        "/matches/api/v1/reload")))
    assert browser.submit(current)[0] == 409
    assert active.path.read_bytes() == before


def test_trace_error_keeps_visible_fieldset_and_legacy_secondary_has_action_feedback(
    localized_server,
):
    browser = Browser(localized_server)
    page = record_context_match(browser, with_hand=False)
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    status, _, raw = browser.submit(evidence_form(page, "original_skat_selected"),
                                  cards=["C7", "SA"])
    assert status == 400 and active.path.read_bytes() == before
    assert active.recovery.diagnostic is not None
    assert re.search(r'<fieldset[^>]*aria-invalid="true"', raw.decode())
    assert 'href="#validation-field-' in raw.decode()
    assert set(evidence_form(raw.decode(), "original_skat_selected")["values"]["cards"]) == {
        "C7", "SA"}
    page = follow(browser, browser.submit(evidence_form(page, "original_skat_selected"),
                                          cards=["SA", "S7"]))
    emitted = evidence_form(page, "original_skat_unknown")["values"]
    legacy = {key: value for key, value in emitted.items() if key != "card_evidence_form"}
    status, _, raw = browser.request("POST", "/matches/cards",
        {**legacy, "card_evidence_mode": "unknown", "cards": ["bad"]})
    assert status == 400
    block = block_for(raw.decode(), "original_skat_unknown")
    summary, = re.findall(r'<section class="error-summary".*?</section>', raw.decode(), re.S)
    assert 'Remove recorded original Skat' in summary
    assert 'href="#validation-form-heading-' in summary and 'aria-invalid="true"' not in block
    between = raw.decode().split(summary, 1)[1].split(block, 1)[0]
    assert re.fullmatch(r'<span class="validation-anchor" id="[^"]+"></span>', between)


def test_actual_body_and_field_bounds_remain_on_existing_route(localized_server):
    browser = Browser(localized_server)
    page = started(browser)
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    form = evidence_form(page, "original_skat_selected")
    assert browser.submit(form, cards=["SA"] * 257)[0] == 400
    assert browser.submit(form, extra="x" * 8192)[0] == 413
    assert active.path.read_bytes() == before
