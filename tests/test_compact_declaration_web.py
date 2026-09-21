import re
from dataclasses import replace

import pytest
from test_compact_card_entry_web import create_live
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form, start_match
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first

import skatmind.api.v1.session as api
import skatmind.api.v1.session.files as session_files
import skatmind.session_persistence as persistence
from skatmind.app_web.compact_declaration_form import explicit_declaration_values
from skatmind.app_web.compact_declaration_http import declaration_binding
from skatmind.app_web.session_frontend import apply_guided_session_command_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.capture_web.context import MatchCaptureWebContextV1
from skatmind.deck import get_full_deck
from skatmind.game_declaration import BOOLEAN_DECLARATION_FIELDS
from skatmind.session_transitions import replay_session_state_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def declaration_form(page, marker="session-declaration"):
    return next(form for form in Forms(page).forms
                 if form["values"].get("declaration_form") == marker)


def legacy_correction_form(browser):
    """Compatibility client: #250 no longer emits this direct-save normal form."""
    active = browser.server.app_context.managed_stateful.active_session
    record = next(r for r in active.state.command_log if r.command.kind == "set_declaration")
    values = explicit_declaration_values(record.command.declaration)
    values = {k: v for k, v in values.items() if v != "false"}
    values.update(managed_handle=active.handle, expected_revision=str(active.state.revision),
        kind="set_declaration", declaration_form="session-correction",
        target_revision=str(record.revision),
        declaration_selection=declaration_binding(
            active, "session-correction", str(record.revision)))
    return {"action": "/sessions/command", "values": values}


def before_declaration(browser, *, defender=True, hand=None):
    form = create_live(browser)
    page = follow(browser, browser.submit(form, cards=hand or get_full_deck()[:10]))
    form = Forms(page).find("/sessions/command", kind="set_declarer")
    players = re.findall(r'<option value="([^"]+)"', re.search(
        r'<select name="player_id"[^>]*>(.*?)</select>', page, re.S)[1])
    page = follow(browser, browser.submit(form, player_id=players[int(defender)]))
    return declaration_form(page)


def summary(page):
    return re.search(r'<section class="accepted-declaration">.*?</section>', page, re.S)[0]


def test_real_native_session_visible_bid_one_save_exact_command_next_task_and_reopen(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    active = localized_server.app_context.managed_stateful.active_session
    assert set(form["values"]) == {"managed_handle", "expected_revision", "kind",
        "declaration_form", "declaration_selection", "game_type", "bid_value", "matadors",
        "_frontend_form_instance"}
    assert form["values"]["bid_value"] == ""
    original, revision = active.path.read_bytes(), active.state.revision
    saves = []
    real_save = session_files.save_session_file
    def save(*args, **kwargs):
        saves.append(kwargs)
        return real_save(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    page = follow(browser, browser.submit(form, game_type="grand", bid_value="19"))
    assert len(saves) == 1 and active.state.revision == revision + 1
    command = active.state.command_log[-1].command
    assert command.kind == "set_declaration"
    assert command.declaration.bid_value == 19 and command.declaration.matadors is None
    assert all(getattr(command.declaration, name) is False for name in BOOLEAN_DECLARATION_FIELDS)
    assert len(active.decision_checkpoints) == 1
    assert active.state.phase == "play" and '/sessions/play' in page
    assert active.path.read_bytes() != original
    accepted = summary(page)
    assert "Boris" in accepted and "19" in accepted
    assert text("en", "declaration.not_entered") in accepted
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened.document == active.document and len(saves) == 1
    # Reopen deliberately issues different source-context correction entry tokens.
    assert re.sub(r'<form.*?</form>', '', summary(page), flags=re.S) == re.sub(
        r'<form.*?</form>', '', accepted, flags=re.S)


def test_dependency_retains_every_choice_through_both_native_languages_then_explicit_save(
    localized_server,
):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    status, _, body = browser.submit(form, game_type="grand", bid_value="17",
                                    schneider_announced="true")
    assert status == 400
    page = body.decode()
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                               language=locale))
        values = declaration_form(page)["values"]
        assert values["schneider_announced"] == "true" and values["bid_value"] == "17"
        assert all(name not in values for name in ("hand_game", "ouvert", "schwarz_announced"))
        assert text(locale, "validation.declaration.schneider_announced_requires") in page
        assert active.path.read_bytes() == before
    page = follow(browser, browser.submit(declaration_form(page), hand_game="true"))
    accepted = active.state.command_log[-1].command.declaration
    assert accepted.hand_game and accepted.schneider_announced and not accepted.ouvert
    assert accepted.bid_value == 17 and accepted.matadors is None


@pytest.mark.parametrize("field,value", (
    ("bid_value", "0"), ("bid_value", "-18"), ("bid_value", "18.1"),
    ("matadors", "5"), ("matadors", "0"), ("matadors", "1"),
    ("game_type", "invalid"), ("game_type", ""), ("hand_game", "on"),
    ("hand_game", "false"), ("hand_game", ["true", "true"]),
    ("declaration_form", ["session-declaration", "session-declaration"]),
    ("declaration_selection", ["a" * 64, "a" * 64]), ("declaration_selection", "bad"),
    ("unknown_field", "true"),
))
def test_rejection_never_changes_accepted_session(localized_server, field, value):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before, document = active.path.read_bytes(), active.document
    response = browser.submit(form, **{"game_type": "grand", field: value})
    assert response[0] == 400
    assert active.document is document and active.path.read_bytes() == before
    assert "Traceback" not in response[2].decode()


@pytest.mark.parametrize("missing", ("declaration_form", "declaration_selection", "bid_value",
                                      "matadors", "game_type", "expected_revision"))
def test_missing_private_or_required_controls_rejected(localized_server, missing):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    form["values"]["game_type"] = "grand"
    del form["values"][missing]
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    assert browser.submit(form)[0] == 400
    assert active.path.read_bytes() == before


def test_live_defender_blank_count_and_null_correction_requires_explicit_clearing(localized_server):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    active = localized_server.app_context.managed_stateful.active_session
    response = browser.submit(form, game_type="grand", matadors="2")
    assert response[0] == 400
    assert text("en", "validation.declaration.count_unverifiable") in response[2].decode()
    page = follow(browser, browser.submit(declaration_form(response[2].decode()), matadors=""))
    form = legacy_correction_form(browser)
    response = browser.submit(form, game_type="null", matadors="2", schneider_announced="true")
    assert response[0] == 400
    page = response[2].decode()
    assert text("en", "validation.declaration.null_matadors") in page
    form["values"].update(game_type="null", matadors="2", schneider_announced="true")
    response = browser.submit(form, matadors="")
    assert response[0] == 400
    assert text("en", "validation.declaration.null_announcement") in response[2].decode()
    form["values"]["matadors"] = ""
    del form["values"]["schneider_announced"]
    page = follow(browser, browser.submit(form, ouvert="true"))
    declaration = replay_session_state_v1(active.state).declaration
    assert declaration.game_type == "null" and declaration.ouvert and not declaration.hand_game
    assert declaration.matadors is None and declaration.bid_value is None
    assert text("en", "declaration.not_applicable") in summary(page)


def test_retrospective_known_ownership_accepts_two_and_rejects_mismatch(localized_server):
    browser = Browser(localized_server)
    hand = [*get_full_deck()[:8], "SJ", "SA"]
    before_declaration(browser, defender=False, hand=hand)
    active = localized_server.app_context.managed_stateful.active_session
    # Fixture setup uses real Commands; complete the unknown deal after explicit promotion.
    result = apply_guided_session_command_v1(active, api.PromoteSessionToRetrospectiveCommandV1(
        expected_revision=active.state.revision))
    assert result.status == "applied"
    players = active.state.players
    remaining = [card for card in get_full_deck() if card not in hand]
    for player, cards in zip(players[1:], (remaining[:10], remaining[10:20]), strict=True):
        for card in cards:
            result = apply_guided_session_command_v1(active, api.RecordSessionDealtCardCommandV1(
                expected_revision=active.state.revision, destination="player_hand",
                player_id=player.player_id, card=card))
            assert result.status == "applied"
    for card in remaining[20:]:
        assert apply_guided_session_command_v1(active, api.RecordSessionDealtCardCommandV1(
            expected_revision=active.state.revision, destination="skat", player_id=None,
            card=card)).status == "applied"
    form = declaration_form(browser.page())
    before = active.path.read_bytes()
    response = browser.submit(form, game_type="grand", hand_game="true", matadors="1")
    assert response[0] == 400
    assert text("en", "validation.declaration.count_mismatch") in response[2].decode()
    assert active.path.read_bytes() == before
    page = follow(browser, browser.submit(declaration_form(response[2].decode()), matadors="2"))
    assert replay_session_state_v1(active.state).declaration.matadors == 2
    assert "2" in summary(page)


def test_match_edit_noop_invalid_continuation_and_reopen(localized_server, monkeypatch):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    for card in ("CA", "SJ", "H9", "S9"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    game = active.workspace.slots[0].observed_game
    before, revision = active.path.read_bytes(), active.workspace.revision
    saves = []
    real_save = MatchCaptureWebContextV1.save_candidate
    def save(self, *args, **kwargs):
        saves.append(args)
        return real_save(self, *args, **kwargs)
    monkeypatch.setattr(MatchCaptureWebContextV1, "save_candidate", save)
    page = follow(browser, browser.submit(declaration_form(page, "match-declaration")))
    assert not saves and active.workspace.revision == revision
    assert active.path.read_bytes() == before
    response = browser.submit(declaration_form(page, "match-declaration"), game_type="null")
    assert response[0] == 400 and active.path.read_bytes() == before
    page = response[2].decode()
    assert text("en", "recovery.reason.wrong_actor") in page and 'href="#match-play-4"' in page
    assert 'id="match-declaration"' in page and active.recovery.diagnostic.play_index == 4
    page = follow(browser, browser.submit(declaration_form(page, "match-declaration"),
                                           game_type="grand", bid_value="9999"))
    assert len(saves) == 1 and active.workspace.revision == revision + 1
    assert active.workspace.slots[0].observed_game.plays == game.plays
    assert "9999" in summary(page) and active.recovery.diagnostic is None
    page = follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    assert "9999" in summary(page) and 'id="match-play-4"' in page


def test_session_stale_reopen_failed_save_and_real_result_lifetime(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_live_game(browser)
    page, _ = review_first(browser)
    active = localized_server.app_context.managed_stateful.active_session
    execution, before = active.execution, active.path.read_bytes()
    downloads = tuple(browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                      for name in ("request", "result"))
    form = legacy_correction_form(browser)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                               language=locale))
        assert active.execution is execution and active.path.read_bytes() == before
        assert tuple(browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                     for name in ("request", "result")) == downloads
    def fail(*args):
        raise OSError("Injected pre-replacement failure")
    with monkeypatch.context() as patch:
        patch.setattr(persistence.os, "replace", fail)
        assert browser.submit(form, bid_value="19")[0] == 409
    assert active.execution is execution and active.path.read_bytes() == before
    page = follow(browser, browser.submit(legacy_correction_form(browser),
                                           bid_value="19"))
    assert active.execution is None and active.path.read_bytes() != before
    assert browser.submit(form, bid_value="20")[0] == 409
    current = legacy_correction_form(browser)
    page = follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert browser.submit(current, bid_value="20")[0] == 409


def test_equal_revision_different_session_source_cannot_use_binding(localized_server):
    browser = Browser(localized_server)
    before_declaration(browser)
    active = localized_server.app_context.managed_stateful.active_session
    form = declaration_form(browser.page())
    # A valid equal-revision external metadata correction is persisted through the real API.
    record = active.state.command_log[0]
    correction = api.SessionCommandCorrectionV1(expected_revision=active.state.revision,
        target_revision=record.revision,
        replacement_command=replace(record.command, game_id="other-game"))
    corrected = api.correct_session_command(active.state, correction).value
    document = api.build_session_persistence_document(corrected.state).value
    session_files.save_session_file(active.path, document,
        expected_content_fingerprint=active.document.content_fingerprint)
    assert document.state.revision == active.state.revision
    assert browser.submit(form, game_type="grand")[0] == 409
    active.document = document  # Fixture: the equal-revision correction is now published.
    assert browser.submit(form, game_type="grand")[0] == 409


def test_live_declarer_verifiable_four_and_known_mismatch(localized_server):
    browser = Browser(localized_server)
    hand = "CJ SJ HJ DJ CA C10 CK CQ C9 C8".split()
    form = before_declaration(browser, defender=False, hand=hand)
    active = localized_server.app_context.managed_stateful.active_session
    response = browser.submit(form, game_type="grand", hand_game="true", matadors="2")
    assert response[0] == 400
    assert text("en", "validation.declaration.count_mismatch") in response[2].decode()
    page = follow(browser, browser.submit(declaration_form(response[2].decode()), matadors="4"))
    assert active.state.command_log[-1].command.declaration.matadors == 4
    assert len(active.decision_checkpoints) == 1 and '/sessions/play' in page


def test_legacy_explicit_session_http_preserves_contract(localized_server):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    values = dict(form["values"])
    for name in ("declaration_form", "declaration_selection"):
        del values[name]
    values.update(game_type="grand", bid_value="1",
                  **{name: "false" for name in BOOLEAN_DECLARATION_FIELDS})
    missing = dict(values)
    del missing["ouvert"]
    assert browser.request("POST", "/sessions/command", missing)[0] == 400
    assert browser.request("POST", "/sessions/command", values)[0] == 303
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.command_log[-1].command.declaration.bid_value == 1


@pytest.mark.parametrize("change", ("wrong_game", "away_back", "reopen", "equal_revision"))
def test_match_exact_bindings_reject_other_sources(localized_server, change):
    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    form = declaration_form(page, "match-declaration")
    if change in {"wrong_game", "away_back"}:
        browser.page("/matches/position/2")
        if change == "away_back":
            browser.page("/matches/position/1")
    elif change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    else:
        # Fixture: equal revision, changed descriptive source, identical accepted Game.
        candidate = _build_match_workspace_v1(revision=active.workspace.revision,
            match_definition=replace(active.workspace.match_definition,
                                     title="Equal revision source"), slots=active.workspace.slots)
        document = build_match_workspace_persistence_document_v1(candidate)
        saved = save_match_workspace_file_v1(active.path, document,
            expected_content_fingerprint=active.capture.content_fingerprint)
        assert saved.status == "saved"
    current = localized_server.app_context.managed_stateful.active_match
    before = current.path.read_bytes()
    response = browser.submit(form, bid_value="19")
    assert response[0] == 409 and current.path.read_bytes() == before
    assert 'class="error-summary"' in response[2].decode()


def test_match_missing_declarer_never_clears_and_explicit_clear_is_separate(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    active = localized_server.app_context.managed_stateful.active_match
    before = active.path.read_bytes()
    form = declaration_form(page, "match-declaration")
    response = browser.submit(form, game_type="", declarer_player_id="")
    assert response[0] == 400 and active.path.read_bytes() == before
    response = browser.submit(form, declarer_player_id="")
    assert response[0] == 400
    assert text("en", "validation.declaration.declarer") in response[2].decode()
    clear = declaration_form(browser.page("/matches/current"), "match-clear")
    page = follow(browser, browser.submit(clear, confirm_clear="on"))
    game = active.workspace.slots[0].observed_game
    assert game.declaration is None and game.declarer_player_id is None
    assert 'value="match-declaration"' in page and 'class="accepted-declaration"' not in page


def test_match_prepublication_save_failure_preserves_preview_and_bytes(
    localized_server, monkeypatch,
):
    from test_match_recording_recovery_web import entry_action

    browser = Browser(localized_server)
    page = start_match(browser)
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards="CA"))
    page = follow(browser, browser.submit(entry_action(page, 1)))
    page = follow(browser, browser.submit(
        Forms(page).find("/matches/recovery/preview"), card="C10"))
    active = localized_server.app_context.managed_stateful.active_match
    preview, before, workspace = active.recovery.preview, active.path.read_bytes(), active.workspace
    page = follow(browser, browser.submit(declaration_form(page, "match-declaration")))
    assert active.recovery.preview is preview and active.path.read_bytes() == before
    def fail(self, *args, **kwargs):
        raise OSError("Injected before replacement")
    with monkeypatch.context() as patch:
        patch.setattr(MatchCaptureWebContextV1, "save_candidate", fail)
        response = browser.submit(declaration_form(page, "match-declaration"), bid_value="19")
    assert response[0] == 409 and active.path.read_bytes() == before
    assert active.recovery.preview is preview and active.workspace is workspace


def test_session_correction_target_cannot_be_changed_or_used_as_initial_submission(
    localized_server,
):
    browser = Browser(localized_server)
    record_live_game(browser, play_count=3)
    active = localized_server.app_context.managed_stateful.active_session
    form = legacy_correction_form(browser)
    before = active.path.read_bytes()
    assert browser.submit(form, target_revision="1")[0] == 409
    assert browser.submit(form, declaration_form="session-declaration")[0] == 400
    assert active.path.read_bytes() == before


def test_compact_declaration_security_retains_host_origin_cookie_boundary(localized_server):
    browser = Browser(localized_server)
    form = before_declaration(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    for headers in ({"Origin": "null"}, {"Origin": "http://foreign.invalid"},
                    {"Cookie": ""}, {"Host": "foreign.invalid"}):
        response = browser.request("POST", form["action"],
            {**form["values"], "game_type": "grand"}, headers=headers)
        assert response[0] == 403
        assert "access-control-allow-origin" not in response[1]
    assert active.path.read_bytes() == before
