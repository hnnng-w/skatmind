"""Cent membership survives genuine managed edits, independently of retained accounting."""

import json
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from test_accounting_web import activate_session, game_form, historical_round
from test_frontend_language_switching import localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review import selection
from test_session_recorded_review_web import Browser, Forms

import skatmind.api.v1.session as api
from skatmind.accounting_store import append_accounting, load_accounting, save_accounting
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.api.v1.session.files import save_session_file
from skatmind.app_web import session_frontend
from skatmind.app_web.accounting_forms import AccountingFormError
from skatmind.app_web.accounting_frontend import fresh_round, new_round
from skatmind.app_web.cent_publication import publish_game
from skatmind.app_web.cent_sources import open_bound, session_entries
from skatmind.app_web.event_context_forms import supported_terms
from skatmind.app_web.session_frontend import (
    apply_guided_session_command_v1,
    correct_guided_session_command_v1,
    default_session_position_export_options_v1,
    execute_guided_session_position_v1,
    import_guided_session_v1,
    prepare_guided_session_document,
    rewind_guided_session_v1,
)
from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration
from skatmind.session_checkpoint_collection import collect_session_decision_checkpoint_v1
from skatmind.session_history import build_session_state_from_accepted_prefix_v1
from skatmind.session_persistence import load_session_persistence_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1


def publish_facts(app, row, active):
    journal = load_accounting(app.managed_home.root)
    updated = append_accounting(journal, fresh_round(row, ((active.path, active.document),)))
    save_accounting(app.managed_home.root, updated, expected_fingerprint=journal.fingerprint,
                    source_guard=lambda: load_session_persistence_file_v1(
                        active.path).document == active.document)
    return updated.head(row.identity)


def direct_row(document):
    return new_round(document, supported_terms("cent", "euroskat", tariff="1/2"))


def command(active, cmd):
    assert apply_guided_session_command_v1(active, cmd).status == "applied"


def opening(app, direct):
    if direct:
        players = tuple(api.SessionPlayerV1(player_id=p, player_label=p, seat=s) for p, s in
                        zip("abc", ("forehand", "middlehand", "rearhand"), strict=True))
        zero = prepare_guided_session_document("synthetic-direct", players, "live", "a")
        row = direct_row(zero)
        active = publish_game(app, load_accounting(app.managed_home.root), row, zero,
                              guard=lambda: True)
        app.managed_stateful.activate_session(active)
    else:
        active = activate_session(app)
    for i, card in enumerate(get_full_deck()[:10]):
        command(active, api.RecordSessionDealtCardCommandV1(expected_revision=i,
            destination="player_hand", player_id="a", card=card))
    command(active, api.SetSessionDeclarerCommandV1(expected_revision=10, declarer_player_id="a"))
    command(active, declaration(24))
    assert [c.source_revision for c in active.decision_checkpoints] == [12]
    assert load_session_persistence_file_v1(active.path).document == active.document
    row = publish_facts(app, row, active) if direct else historical_round(app)
    assert row.context.bindings[0].attached_source.revision == (0 if direct else 12)
    assert row.recordings[0].source.content_fingerprint == active.document.content_fingerprint
    return active, row


def declaration(bid):
    return api.SetSessionDeclarationCommandV1(expected_revision=11,
        declaration=GameDeclaration(game_type="grand", hand_game=True, bid_value=bid))


def play(card):
    return api.RecordSessionPlayCommandV1(expected_revision=12, player_id="a", card=card)


def correct(active, cmd):
    result = correct_guided_session_command_v1(active, api.SessionCommandCorrectionV1(
        expected_revision=active.state.revision, target_revision=cmd.expected_revision + 1,
        replacement_command=cmd))
    assert result.status == "applied"


def bound(app, row):
    return open_bound(app, row, row.context.bindings[0], session_entries(app))


def legacy_checkpoint_pair(app):
    active, row = opening(app, direct=False)
    original, = active.decision_checkpoints
    # Exercise the ordinary writer used before member receipts existed. The
    # checkpoint collection, document builder, sort and file CAS all run.
    options = replace(default_session_position_export_options_v1(), sample_count=1)
    with (patch.object(session_frontend, "save_cent_member_edit", return_value=None),
          patch.object(session_frontend, "execute_guided_frontend_analysis_v1",
                       side_effect=RuntimeError("stop at evaluator entry")),
          pytest.raises(RuntimeError, match="stop at evaluator entry")):
        execute_guided_session_position_v1(active, export_options=options,
                                           execution_options=ExecutionOptionsV1())
    saved = load_session_persistence_file_v1(active.path).document
    newer, retained = saved.decision_checkpoints
    assert retained == original and newer.source_revision == retained.source_revision == 12
    rebuilt = build_session_persistence_document_v1(saved.state, decision_checkpoints=(retained,))
    attached = row.context.bindings[0].attached_source
    assert rebuilt.content_fingerprint == attached.content_fingerprint
    assert saved.content_fingerprint != rebuilt.content_fingerprint
    assert not tuple(app.managed_home.root.glob("*.receipt"))
    return active, row


def test_legacy_partial_boundary_reopens_read_only_then_accepts_managed_undo(tmp_path):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        app = server.app_context
        active, row = legacy_checkpoint_pair(app)
        home = app.managed_home.root
        def files():
            return {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in home.rglob("*")
                    if p.is_file()}
        before = files()
        with patch("skatmind.app_web.execution.execute") as evaluate:
            assert bound(app, row).document == active.document
            browser = Browser(server)
            resume = Forms(browser.page("/cent")).find("/cent/resume")
            assert game_form(follow(browser, browser.submit(resume)), 1)
            analyze = Forms(browser.page("/review/recorded")).find("/review/open-recording")
            assert analyze["values"]["bound_selection"]
            assert 'href="/sessions/decisions"' in follow(browser, browser.submit(analyze))
            evaluate.assert_not_called()
        assert files() == before
        selected = app.managed_stateful.active_session
        assert selected.path == active.path and selected.document == active.document
        assert rewind_guided_session_v1(selected, target_revision=11).status == "applied"
        assert len(tuple(home.glob("*.receipt"))) == 1
        assert bound(app, row).document == selected.document
        assert load_accounting(home).head(row.identity) == row


@pytest.mark.parametrize("missing", [True, False], ids=["missing-original", "over-subset-bound"])
def test_unproven_legacy_checkpoint_subset_cannot_grant_membership(tmp_path, missing):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        app = next(servers).app_context
        active, row = legacy_checkpoint_pair(app)
        # Either the required checkpoint is absent from two genuine variants, or
        # it is present among five, where partial-subset search is not attempted.
        variants = active.decision_checkpoints[:1] if missing else active.decision_checkpoints
        for count in ((2,) if missing else (2, 3, 4)):
            variants = collect_session_decision_checkpoint_v1(
                state=active.state, decision_checkpoints=variants, export_options=replace(
                    default_session_position_export_options_v1(), sample_count=count)
            ).decision_checkpoints
        assert len(variants) == (2 if missing else 5)
        candidate = build_session_persistence_document_v1(active.state,
                                                          decision_checkpoints=variants)
        saved = save_session_file(active.path, candidate,
                                  expected_content_fingerprint=active.document.content_fingerprint)
        assert saved.value.status == "saved"
        with pytest.raises(AccountingFormError):
            bound(app, row)
        assert not tuple(app.managed_home.root.glob("*.receipt"))


@pytest.mark.parametrize("direct", [False, True], ids=["historical", "direct"])
@pytest.mark.parametrize("edit", ["play", "undo", "correct"])
def test_cent_membership_after_managed_edit_and_restart(tmp_path, direct, edit):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        app = server.app_context
        active, row = opening(app, direct)
        journal = load_accounting(app.managed_home.root)
        assert bound(app, row).document == active.document
        browser = Browser(server)
        stale = game_form(browser.page(), 1)
        if edit == "play":
            command(active, play("CA"))
        elif edit == "undo":
            assert rewind_guided_session_v1(active, target_revision=11).status == "applied"
        else:
            correct(active, declaration(27))
        expected = active.document
        assert expected.state.revision == {"play": 13, "undo": 11, "correct": 12}[edit]
        assert expected.decision_checkpoints[0].source_revision == 12
        assert load_session_persistence_file_v1(active.path).document == expected
        assert bound(app, row).document == expected
        assert browser.submit(stale, game_status="passed")[0] == 409
        assert load_accounting(app.managed_home.root) == journal

    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        app = server.app_context
        browser = Browser(server)
        resume = Forms(browser.page("/cent")).find("/cent/resume")
        page = follow(browser, browser.submit(resume))
        assert game_form(page, 1)
        analyze = Forms(browser.page("/review/recorded")).find("/review/open-recording")
        assert analyze["values"]["bound_selection"]
        scopes = follow(browser, browser.submit(analyze))
        assert 'href="/sessions/decisions"' in scopes
        active = app.managed_stateful.active_session
        assert active.document == expected and load_accounting(app.managed_home.root) == journal
        if edit == "undo":
            command(active, declaration(27))
        if edit != "play":
            command(active, play("CA"))
        correct(active, play("C10"))
        assert bound(app, row).document == active.document
        form = game_form(browser.page(), 1)
        follow(browser, browser.submit(form, game_status="passed"))
        refreshed = load_accounting(app.managed_home.root)
        assert refreshed.rounds[:-1] == journal.rounds
        assert refreshed.head(row.identity).recordings[0].source.content_fingerprint == (
            active.document.content_fingerprint)


def test_managed_example_undo_from_published_revision_13(tmp_path):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        app = next(servers).app_context
        active = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="e"*64,
            document=json.loads(Path("examples/session_live_persistence.json").read_text("utf-8")))
        prefix = build_session_state_from_accepted_prefix_v1(active.state, target_revision=0)
        row = direct_row(build_session_persistence_document_v1(prefix))
        journal = load_accounting(app.managed_home.root)
        save_accounting(app.managed_home.root, append_accounting(journal, row),
                        expected_fingerprint=journal.fingerprint, source_guard=lambda: True)
        row = publish_facts(app, row, active)
        assert row.recordings[0].source.revision == 13
        opened = bound(app, row)
        app.managed_stateful.activate_session(opened)
        assert rewind_guided_session_v1(opened, target_revision=12).status == "applied"
        saved = load_session_persistence_file_v1(opened.path).document
        assert saved.state.revision == 12
        assert bound(app, row).document == saved


def test_checkpoint_only_save_and_original_analysis_remain_source_scoped(tmp_path):
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
    from skatmind.app_web.saved_match_analyses import SELECTION_ROUTE, archive_store
    from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1

    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        app, browser = server.app_context, Browser(server)
        active, row = opening(app, direct=False)
        original = active.document
        options = replace(default_session_position_export_options_v1(), sample_count=1)
        assert execute_guided_session_position_v1(active, export_options=options,
            execution_options=ExecutionOptionsV1()).status == "executed"
        changed = bound(app, row).document
        assert changed.state == original.state and changed != original
        assert original.decision_checkpoints[0] in changed.decision_checkpoints
        assert [c.source_revision for c in changed.decision_checkpoints] == [12, 12]
        command(active, play("CA"))
        execute_recorded_session_decision_v1(app, active, selection=selection(active))
        archive = archive_store(app)
        key, = archive.snapshot().available_evidence_ids
        retained = archive.read_evidence(key)
        service = AutomaticMatchLearningServiceV1.open(app)
        assert service.update().status == "prepared"
        assert len(service.consume(lambda b: b.session_evidence)) == 1
        direct = "/sessions/decisions/" + selection(active)
        form = Forms(browser.page(direct)).find(SELECTION_ROUTE)
        base = "/sessions/saved-analyses/" + form["values"]["analysis"]
        def downloads():
            parts = [browser.request("GET", f"{base}/{kind}.json")
                     for kind in ("request", "result")]
            assert all(status == 200 for status, _, _ in parts)
            return [raw for _, _, raw in parts]
        originals = downloads()
        follow(browser, browser.submit(form))
        assert archive.snapshot().manifest.excluded_analysis_ids == (key,)
        correct(active, play("C10"))
        assert bound(app, row).document == active.document and active.execution is None
        assert downloads() == originals
        assert archive.snapshot().manifest.excluded_analysis_ids == (key,)
        follow(browser, browser.submit(Forms(browser.page(base)).find(SELECTION_ROUTE)))
        assert archive.snapshot().manifest.excluded_analysis_ids == ()
        assert service.update().status == "prepared"
        assert service.consume(lambda b: b.session_evidence) == ()
        assert archive.read_evidence(key) == retained


@pytest.mark.parametrize("tamper", ["unrelated_same_id", "foreign", "identical_copy", "duplicate"])
def test_edited_member_rejects_substitution_without_activation(tmp_path, tamper):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        server = next(servers)
        app, browser = server.app_context, Browser(server)
        active, row = opening(app, direct=True)
        correct(active, declaration(27))
        other = activate_session(app, "independent")
        resume = Forms(browser.page("/cent")).find("/cent/resume")
        analyze = next(f for f in Forms(browser.page("/review/recorded")).forms
                       if f["action"] == "/review/open-recording"
                       and "bound_selection" in f["values"])
        if tamper in ("duplicate", "identical_copy"):
            copy = active.path.with_name("copy.json")
            copy.write_bytes(active.path.read_bytes())
            if tamper == "identical_copy":
                copy.replace(active.path)
        else:
            if tamper == "foreign":
                replacement = other.document
            else:
                # Same players, ID, revision and phase; independently corrected declaration.
                edit = api.SessionCommandCorrectionV1(expected_revision=12, target_revision=12,
                                                      replacement_command=declaration(30))
                alternative = api.correct_session_command(active.state, edit)
                replacement = build_session_persistence_document_v1(alternative.value.state)
            saved = save_session_file(active.path, replacement,
                expected_content_fingerprint=active.document.content_fingerprint).value
            assert saved.status == "saved"
        assert browser.submit(resume)[0] in (400, 409)
        assert browser.submit(analyze)[0] == 409
        assert app.managed_stateful.active_session is other
        assert "/cent/resume" not in browser.page("/cent")
        assert not any("bound_selection" in f["values"]
                       for f in Forms(browser.page("/review/recorded")).forms)
        assert load_accounting(app.managed_home.root).head(row.identity) == row


@pytest.mark.parametrize("failure", ["receipt", "recording"])
def test_interrupted_edit_preserves_last_file_and_allows_retry(tmp_path, monkeypatch, failure):
    import os

    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        app = next(servers).app_context
        active, row = opening(app, direct=True)
        original = active.document
        real_replace = os.replace
        def interrupt(src, dst):
            if (failure == "receipt" and dst.suffix == ".receipt"
                    or failure == "recording" and dst == active.path):
                raise OSError("Interrupted managed file publication")
            real_replace(src, dst)
        with monkeypatch.context() as m:
            m.setattr(os, "replace", interrupt)
            with pytest.raises(OSError, match="Interrupted"):
                correct(active, declaration(27))
        assert active.document == bound(app, row).document == original
        correct(active, declaration(27))
        assert bound(app, row).document == active.document != original


def test_replaced_open_file_cannot_mint_a_managed_edit(tmp_path):
    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        app = next(servers).app_context
        active, _ = opening(app, direct=False)
        original = active.document
        copy = active.path.with_suffix(".copy")
        copy.write_bytes(active.path.read_bytes())
        copy.replace(active.path)
        result = apply_guided_session_command_v1(active, play("CA"))
        assert result.status == "conflict"
        assert load_session_persistence_file_v1(active.path).document == active.document == original
        assert not tuple(app.managed_home.root.glob("*.receipt"))


def test_unreadable_journal_does_not_disable_independent_capture(tmp_path):
    from skatmind.accounting_store import ACCOUNTING_FILENAME

    with closing(localized_server.__wrapped__(tmp_path)) as servers:
        app = next(servers).app_context
        member, _ = opening(app, direct=True)
        journal = app.managed_home.root / ACCOUNTING_FILENAME
        journal.write_bytes(b"invalid")
        assert apply_guided_session_command_v1(member, play("CA")).status == "conflict"
        other = activate_session(app, "independent")
        command(other, api.RecordSessionDealtCardCommandV1(expected_revision=0,
            destination="player_hand", player_id="a", card="CA"))
        assert journal.read_bytes() == b"invalid"
