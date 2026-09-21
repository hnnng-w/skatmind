"""Real returned-form Session correction; literal R06 suffix expectations."""

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_card_correction_ui import activated_form, form_nodes
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import (
    Browser,
    Forms,
    record_score_review_game,
    score_review_form,
)

import skatmind.api.v1.session as api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.session_declaration_correction as correction_module
import skatmind.session_persistence as persistence
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

PREFIX = "/sessions/declaration-correction/"


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def select(browser, kind, page=None):
    forms = Forms(page or browser.page()).forms
    # Entries occur beside declarer, then declaration; no submitted revision/kind.
    entries = [form for form in forms if form["action"] == PREFIX + "select"]
    entry = entries[("set_declarer", "set_declaration").index(kind)]
    assert set(entry["values"]) == {
        "managed_handle", "correction_selection", "_frontend_form_instance"}
    page = follow(browser, browser.submit(entry))
    return page, Forms(page).find(PREFIX + "preview")


def test_nine_play_partial_is_previewed_without_a_write(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=9)
    active = localized_server.app_context.managed_stateful.active_session
    before, document = active.path.read_bytes(), active.document
    page, form = select(browser, "set_declaration")
    assert form["values"]["matadors"] == ""
    page = follow(browser, browser.submit(form, game_type="null"))
    assert active.path.read_bytes() == before and active.document is document
    section = page.split('id="session-declaration-correction"')[1].split('</section>')[0]
    assert 'name="target_revision"' not in section
    assert not any(f["action"] == PREFIX + "preview" for f in Forms(page).forms)
    apply = Forms(page).find(PREFIX + "apply")
    assert "confirm_apply" not in apply["values"]
    assert browser.submit(apply)[0] == 400
    assert active.path.read_bytes() == before
    page = follow(browser, browser.submit(apply, confirm_apply="on"))
    plays = [r.command.card for r in active.state.command_log if r.command.kind == "record_play"]
    assert plays == ["CK", "C7", "CA", "SK", "S7", "S10"]
    assert active.state.phase == "play" and "/sessions/play" in page


def preview(browser, kind="set_declaration", **values):
    _, form = select(browser, kind)
    return follow(browser, browser.submit(form, **values))


def names(page):
    block = re.search(r'<select name="player_id"[^>]*>(.*?)</select>', page, re.S)[1]
    return dict((label, value) for value, label in re.findall(
        r'<option value="([^"]+)"[^>]*>(.*?)</option>', block))


def test_first_emitted_declarer_cancel_repreview_apply_then_record_without_reentering_hand(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    plays = record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    before, document, operation = active.path.read_bytes(), active.document, active.last_operation
    saves = []
    real = session_files.save_session_file
    def save(*args, **kwargs):
        saves.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    page, form = select(browser, "set_declarer")
    roster = names(page)
    assert form["values"]["player_id"] == roster["B"]
    page = follow(browser, browser.submit(form, player_id=roster["C"]))
    assert active.document is document and active.last_operation is operation
    stale = activated_form(page, PREFIX + "apply")
    cancelled = browser.submit(Forms(page).find(PREFIX + "cancel"))
    assert cancelled[1]["location"] == "/sessions/current#session-recording"
    assert active.path.read_bytes() == before and not saves
    response = browser.submit(stale)
    assert response[0] == 409
    page = preview(browser, "set_declarer", player_id=roster["C"])
    page = follow(browser, browser.submit(activated_form(page, PREFIX + "apply")))
    assert len(saves) == 1 and active.state.revision == document.state.revision
    assert len([r for r in active.state.command_log if r.command.kind == "record_dealt_card"]) == 10
    for play in plays[:9]:
        browser.command("record_play", card=play["card"])
    assert len(saves) == 10
    assert [r.command.card for r in active.state.command_log
            if r.command.kind == "record_play"] == [
        "CK", "C7", "CA", "SK", "S7", "S10", "HK", "H9", "H10"]


@pytest.mark.parametrize("proposal,status,retained,removed,phase", (
    ({"bid_value": "20"}, "applied", 9, 0, "play"),
    ({}, "unchanged", 9, 0, "play"),
    ({"game_type": "null"}, "partial", 6, 3, "play"),
    ({"player": "C"}, "applied", 9, 0, "play"),
    ({"player": "A"}, "partial", 0, 9, "skat_and_discard"),
))
def test_literal_canonical_effects_and_single_save_reopen(
    localized_server, monkeypatch, proposal, status, retained, removed, phase,
):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=9)
    active = localized_server.app_context.managed_stateful.active_session
    before, document = active.path.read_bytes(), active.document
    checkpoints = active.decision_checkpoints
    operation = active.last_operation
    saves, evaluations = [], []
    real_save, real_correct = session_files.save_session_file, api.correct_session_command
    def save(*args, **kwargs):
        saves.append(args)
        return real_save(*args, **kwargs)
    def correct(*args, **kwargs):
        evaluations.append(args)
        return real_correct(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    monkeypatch.setattr(api, "correct_session_command", correct)
    values = dict(proposal)
    player = values.pop("player", None)
    page, form = select(browser, "set_declarer" if player else "set_declaration")
    if player:
        values["player_id"] = names(page)[player]
    page = follow(browser, browser.submit(form, **values))
    candidate = active.declaration_correction.preview.result
    assert candidate.status == status and candidate.state.phase == phase
    assert sum(r.command.kind == "record_play" for r in candidate.state.command_log) == retained
    assert len(candidate.discarded_suffix_records) == removed
    assert len(evaluations) == 1 and not saves
    assert active.document is document and active.last_operation is operation
    assert active.path.read_bytes() == before and active.decision_checkpoints is checkpoints
    if status == "partial":
        assert candidate.failed_original_revision == candidate.discarded_suffix_records[0].revision
        for record in candidate.discarded_suffix_records:
            assert card_name("en", record.command.card) in page
        assert text("en", "session.correction.removal", plays=removed, other=0) in page
        assert text("en", "session.correction.reason.turn" if retained else
                    "session.correction.reason.phase") in page
    elif status == "unchanged":
        assert candidate.replayed_suffix_records == ()
        assert text("en", "session.correction.retained", plays=9, records=9) in page
    apply = activated_form(page, PREFIX + "apply")
    _, nodes = form_nodes(page, PREFIX + "apply")
    consent, = [n for n in nodes if n["attrs"].get("name") == "confirm_apply"]
    assert consent["tag"] == ("input" if status == "partial" else "button")
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(
            Forms(page).find("/actions/profile/language"), language=locale))
        assert not saves and len(evaluations) == 1
    response = browser.submit(apply, **({"confirm_apply": "on"} if status == "partial" else {}))
    page = follow(browser, response)
    assert len(saves) == int(status != "unchanged") and len(evaluations) == 3
    assert active.state == candidate.state
    assert all(cp in active.decision_checkpoints for cp in checkpoints)
    assert active.last_operation.status == status
    if status == "partial":
        assert text("en", "task.operation.partial") in page
        assert 'data-operation-feedback' not in page
    assert browser.submit(apply, confirm_apply="on")[0] == 409
    if retained == 6:
        for card in ("HA", "H10", "HK"):
            browser.command("record_play", card=card)
    saved = active.path.read_bytes()
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened.document == active.document and reopened.path.read_bytes() == saved


def test_rejected_matadors_invalid_flags_and_language_safe_values(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=9)
    active = localized_server.app_context.managed_stateful.active_session
    before, operation = active.path.read_bytes(), active.last_operation
    page, form = select(browser, "set_declaration")
    response = browser.submit(form, matadors="2", bid_value="20")
    assert response[0] == 400
    page = response[2].decode()
    assert text("en", "validation.declaration.count_unverifiable") in page
    assert not any(f["action"] == PREFIX + "apply" for f in Forms(page).forms)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(
            Forms(page).find("/actions/profile/language"), language=locale))
        form = Forms(page).find(PREFIX + "preview")
        assert form["values"]["matadors"] == "2" and form["values"]["bid_value"] == "20"
        assert text(locale, "validation.declaration.count_unverifiable") in page
    response = browser.submit(form, matadors="", schneider_announced="true")
    assert response[0] == 400
    assert text("en", "validation.declaration.schneider_announced_requires") in response[2].decode()
    assert active.path.read_bytes() == before and active.last_operation is operation


def test_prefilled_matadors_are_supplied_command_value(localized_server):
    from test_compact_declaration_web import before_declaration
    browser = Browser(localized_server)
    entry = before_declaration(browser, defender=False,
        hand="CJ SJ HJ DJ CA C10 CK CQ C9 C8".split())
    follow(browser, browser.submit(entry, game_type="grand", hand_game="true", matadors="4"))
    _, editor = select(browser, "set_declaration")
    assert editor["values"]["matadors"] == "4"
    assert editor["values"]["hand_game"] == "true"
    assert all(name not in editor["values"] for name in (
        "ouvert", "schneider_announced", "schwarz_announced"))


def test_preview_pages_do_not_consume_accepted_receipt_or_collect_checkpoints(
    localized_server, monkeypatch,
):
    from skatmind.app_web import session_frontend
    from skatmind.app_web.task_first_session_rendering import render_task_first_session_v1
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    receipt, attempt = active.operation_feedback.pending, active.operation_feedback.attempt
    assert receipt is not None
    # Render the real entry markup without delivering the pending prior receipt.
    page = render_task_first_session_v1(active)
    entry = Forms(page).find(PREFIX + "select", index=1)
    page = follow(browser, browser.submit(entry))
    form = Forms(page).find(PREFIX + "preview")
    calls = []
    real = session_frontend._collect_current_checkpoint
    def collect(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)
    monkeypatch.setattr(session_frontend, "_collect_current_checkpoint", collect)
    page = follow(browser, browser.submit(form, bid_value="20"))
    response = browser.submit(form, matadors="2")
    assert response[0] == 400
    assert active.operation_feedback.pending is receipt
    assert active.operation_feedback.attempt is attempt and not calls


@pytest.mark.parametrize("bad", ({"bid_value": "" , "game_type": ""},
    {"bid_value": ["18", "20"]}, {"correction_kind": "set_declarer"},
    {"hand_game": "false"}, {"target_revision": "1"}, {"replacement_command": "{}"}))
def test_invalid_repreview_supersedes_old_apply(localized_server, bad):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    _, form = select(browser, "set_declaration")
    page = follow(browser, browser.submit(form, bid_value="20"))
    stale = activated_form(page, PREFIX + "apply")
    assert browser.submit(form, **bad)[0] == 400
    assert browser.submit(stale)[0] == 409
    assert active.path.read_bytes() == before


def test_change_proposal_and_stale_cancel_do_not_clear_new_editor_or_renew_expiry(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    page = preview(browser, bid_value="20")
    old = active.declaration_correction.selected
    stale_apply = activated_form(page, PREFIX + "apply")
    stale_cancel = Forms(page).find(PREFIX + "cancel")
    edit = next(f for f in Forms(page).forms if f["action"] == PREFIX + "select"
                and f["values"]["correction_selection"] == old.token)
    page = follow(browser, browser.submit(edit))
    pending = active.declaration_correction.selected
    assert pending.created_at == old.created_at and pending.token != old.token
    assert Forms(page).find(PREFIX + "preview")["values"]["bid_value"] == "20"
    assert browser.submit(stale_apply)[0] == 409 and browser.submit(stale_cancel)[0] == 409
    assert active.declaration_correction.selected is pending


@pytest.mark.parametrize("confirmation", (None, "", "true", ["on", "on"]))
def test_no_default_confirmation(localized_server, confirmation):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    page = preview(browser, bid_value="20")
    before = active.path.read_bytes()
    form = Forms(page).find(PREFIX + "apply")
    response = browser.submit(form, **({} if confirmation is None else {
        "confirm_apply": confirmation}))
    assert response[0] == 400
    assert active.path.read_bytes() == before


@pytest.mark.parametrize("change", (
    "expiry", "reload", "reopen", "external", "foreign", "mutation"))
def test_source_lifecycle_rejects_apply(localized_server, monkeypatch, change):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    page = preview(browser, bid_value="20")
    form = activated_form(page, PREFIX + "apply")
    if change == "expiry":
        now = active.declaration_correction.selected.created_at + 1800
        monkeypatch.setattr(correction_module, "time", SimpleNamespace(monotonic=lambda: now))
    elif change == "reload":
        follow(browser, browser.submit(Forms(page).find("/sessions/reload")))
    elif change == "reopen":
        follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    elif change == "mutation":
        browser.command("record_play", card="CK")
    elif change == "foreign":
        form["values"]["managed_handle"] = "f" * 64
    else:
        old = active.state.command_log[0]
        result = api.correct_session_command(active.state, api.SessionCommandCorrectionV1(
            expected_revision=active.state.revision, target_revision=old.revision,
            replacement_command=replace(old.command, game_id="external-same-revision"))).value
        document = api.build_session_persistence_document(result.state,
            decision_checkpoints=active.decision_checkpoints).value
        saved = session_files.save_session_file(active.path, document,
            expected_content_fingerprint=active.document.content_fingerprint).value
        assert saved.status == "saved"
        assert document.state.revision == active.state.revision
    before = active.path.read_bytes()
    assert browser.submit(form)[0] == 409 and active.path.read_bytes() == before


def test_competing_apply_and_pre_save_failure_are_single_save(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    page = preview(browser, bid_value="20")
    form = activated_form(page, PREFIX + "apply")
    before, document = active.path.read_bytes(), active.document
    # Labelled fault injection only; successful saves below use real persistence.
    def fail(*args):
        raise OSError("Synthetic pre-replacement fault")
    with monkeypatch.context() as fault:
        fault.setattr(persistence.os, "replace", fail)
        assert browser.submit(form)[0] == 409
    assert active.document is document and active.path.read_bytes() == before
    assert browser.submit(form)[0] == 409
    page = preview(browser, bid_value="20")
    form = activated_form(page, PREFIX + "apply")
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: browser.submit(form)[0], range(2)))
    assert sorted(statuses) == [303, 409]


def test_apply_rebuild_compares_exact_preview_and_real_external_cas(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    app = localized_server.app_context
    active = app.managed_stateful.active_session
    page = preview(browser, bid_value="20")
    apply = activated_form(page, PREFIX + "apply")
    pending = active.declaration_correction
    retained = pending.preview
    before = active.path.read_bytes()
    # Labelled fault: retained proposal and result disagree; no save can publish it.
    replacement = retained.correction.replacement_command
    pending.preview = replace(retained, correction=replace(retained.correction,
        replacement_command=replace(replacement,
            declaration=replace(replacement.declaration, bid_value=21))))
    assert browser.submit(apply)[0] == 409 and active.path.read_bytes() == before
    page = preview(browser, bid_value="20")
    apply = activated_form(page, PREFIX + "apply")
    original = active.document
    old = active.state.command_log[0]
    external = api.correct_session_command(active.state, api.SessionCommandCorrectionV1(
        expected_revision=active.state.revision, target_revision=old.revision,
        replacement_command=replace(old.command, game_id="external-before-cas"))).value
    document = api.build_session_persistence_document(external.state).value
    real = session_files.save_session_file
    attempts = []
    def concurrent_writer(*args, **kwargs):
        assert not app.lock._is_owned()
        assert app.managed_stateful.session_lifecycle_lock._is_owned()
        assert active.lock._is_owned()
        attempts.append(args)
        assert real(active.path, document,
            expected_content_fingerprint=original.content_fingerprint).value.status == "saved"
        return real(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", concurrent_writer)
    assert browser.submit(apply)[0] == 409
    assert len(attempts) == 1 and active.document is original
    assert session_files.load_session_file(active.path).value.document == document


@pytest.mark.parametrize("field", ("managed_handle", "correction_selection", "correction_kind",
                                    "game_type", "bid_value", "matadors"))
def test_required_fields_and_duplicates(localized_server, field):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    _, form = select(browser, "set_declaration")
    before = active.path.read_bytes()
    assert browser.submit(form, **{field: [form["values"][field]] * 2})[0] == 400
    del form["values"][field]
    assert browser.submit(form)[0] == 400
    assert active.path.read_bytes() == before


def test_entry_token_is_not_apply_and_foreign_player_is_rejected(localized_server):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    page, form = select(browser, "set_declarer")
    before = active.path.read_bytes()
    assert browser.submit(form, player_id="unrelated-roster")[0] == 400
    assert browser.submit(form, player_id="")[0] == 400
    page = follow(browser, browser.submit(form, player_id=names(page)["C"]))
    entry = next(f for f in Forms(page).forms if f["action"] == PREFIX + "select")
    apply = activated_form(page, PREFIX + "apply")
    assert browser.submit(apply,
        correction_selection=entry["values"]["correction_selection"])[0] == 409
    assert active.path.read_bytes() == before


@pytest.mark.parametrize("action", ("select", "preview", "apply", "cancel"))
def test_actual_body_bound_and_security(localized_server, action):
    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=0)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    route = PREFIX + action
    assert browser.request("GET", route)[0] == 405
    assert browser.request("POST", route, {"x": "a" * 8192})[0] == 413
    for headers in ({"Origin": "null"}, {"Host": "foreign.invalid"}, {"Cookie": ""}):
        assert browser.request("POST", route, {}, headers=headers)[0] == 403
    assert active.path.read_bytes() == before


def test_real_sj_result_survives_preview_cancel_noop_then_equal_revision_edit_invalidates(
    localized_server,
):
    from test_equal_best_immediate import assert_visible_equal_best
    from test_guided_frontend_result_presentation import assert_summary_points
    from test_match_recording_recovery_web import operation_form
    from test_recorded_decision_context import MATCH_HAND, SESSION_HAND, assert_context
    from test_recorded_party_presentation import corrected_match_setup

    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=30)
    browser.command("set_game_end")
    page = follow(browser, browser.submit(score_review_form(browser)))
    active = localized_server.app_context.managed_stateful.active_session
    execution = active.execution
    downloads = tuple(browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                      for name in ("request", "result", "session"))
    page = corrected_match_setup(browser)
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
                                          cards=MATCH_HAND, card_evidence_mode="exact"))
    match = localized_server.app_context.managed_stateful.active_match
    page = browser.page("/matches/review/1")
    analysis = next(f for f in Forms(page).forms if f["action"] == "/matches/api/v1/analysis"
                    and f["values"].get("operation") == "analyze_decision")
    follow(browser, browser.submit(analysis))
    reports = match.capture.report_store.list()
    assert reports
    page = preview(browser, bid_value="20")
    follow(browser, browser.submit(Forms(page).find(PREFIX + "cancel")))
    page = preview(browser)
    follow(browser, browser.submit(activated_form(page, PREFIX + "apply")))
    page = browser.page()
    assert_summary_points(page, "en", 14, 29)
    assert_visible_equal_best(page, "en")
    assert_context(page, "en", hand=SESSION_HAND, prefix=(("B", "HJ"), ("C", "DJ")),
                   actor="A", trick=4, play=3)
    assert active.execution is execution
    assert tuple(browser.request("GET", "/sessions/downloads/" + name + ".json")[2]
                 for name in ("request", "result", "session")) == downloads
    revision, checkpoints = active.state.revision, active.decision_checkpoints
    page = preview(browser, bid_value="20")
    follow(browser, browser.submit(activated_form(page, PREFIX + "apply")))
    assert active.state.revision == revision and active.execution is None
    assert all(cp in active.decision_checkpoints for cp in checkpoints)
    assert match.capture.report_store.list() == reports
