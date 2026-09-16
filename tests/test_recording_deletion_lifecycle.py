"""Real executed artifacts and independent copies in disposable synthetic roots."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_review_navigation import chooser_form, saved_partial_match
from test_recording_deletion_web import create_recording, preview
from test_recording_deletion_web import localized_server as _localized_server
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first
from test_unified_local_app_managed_items import _save_session

import skatmind.app_web.execution as session_execution
import skatmind.capture_web.analysis as match_execution
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def open_partial_match(browser):
    path, workspace = saved_partial_match(browser.server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    return path, workspace, browser.page("/matches/position/3")


def test_completed_session_result_and_manual_draft_survive_inactive_delete_then_retire(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    record_live_game(browser, play_count=30)
    _, review_form = review_first(browser)
    app = localized_server.app_context
    active = app.managed_stateful.active_session
    execution, source = active.execution, active.recorded_review_source
    result = browser.request("GET", "/sessions/downloads/result.json")[2]
    source_bytes = active.path.read_bytes()
    failed = Forms(preview(browser, "sessions", active.handle)).find("/recordings/delete/apply")
    real_unlink = Path.unlink
    def refused(path, *args, **kwargs):
        if path == active.path:
            raise PermissionError("Controlled access refusal with a genuine retained Result")
        return real_unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", refused)
        assert browser.submit(failed, confirm_delete="on")[0] == 400
    assert active.execution is execution and active.recorded_review_source is source
    assert active.path.read_bytes() == source_bytes
    page = browser.page("/review")
    follow(browser, browser.submit(Forms(page).find("/actions/review/start")))
    manual = app.review_state
    path = active.category_root / "separate-imported-name.json"
    _save_session(path, session_id="independent-synthetic-session")
    from skatmind.app_web.managed_item_storage import build_managed_item_handle_v1
    handle = build_managed_item_handle_v1(family="sessions", basename=path.name)
    page = preview(browser, "sessions", handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/cancel")))
    assert active.execution is execution and active.recorded_review_source is source
    page = preview(browser, "sessions", handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                   confirm_delete="on"))
    assert not path.exists() and active.path.read_bytes() == source_bytes
    assert browser.request("GET", "/sessions/downloads/result.json")[2] == result
    assert active.execution is execution and app.review_state is manual
    match, _ = create_recording(browser, "matches")
    match_bytes = match.path.read_bytes()
    page = preview(browser, "sessions", active.handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/cancel")))
    assert active.execution is execution and active.recorded_review_source is source
    page = preview(browser, "sessions", active.handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                   confirm_delete="on"))
    assert active.execution is active.recorded_review_source is active.execution_attempt is None
    assert app.managed_stateful.active_session is None and active.retired
    assert browser.submit(review_form)[0] == 409
    assert browser.request("GET", "/sessions/downloads/result.json")[0] == 404
    assert not active.path.exists()
    assert app.review_state is manual and app.managed_stateful.active_match is match
    assert match.path.read_bytes() == match_bytes


def test_real_match_report_recovery_and_imported_corpus_survive_source_removal(localized_server):
    from test_historical_game import build_historical_input
    browser = Browser(localized_server)
    path, _, page = open_partial_match(browser)
    for position in (1, 2):
        page = browser.page(f"/matches/position/{position}")
        follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    page = browser.page("/matches/position/3")
    data = build_historical_input(game_type="grand")
    plays = [play for trick in data["tricks"] for play in trick["plays"]]
    for play in plays[6:]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"),
                                             cards=play["card"]))
    workspace = localized_server.app_context.managed_stateful.active_match.workspace
    assert len(workspace.slots[2].observed_game.plays) == 30
    assert [slot.slot_kind for slot in workspace.slots[:3]] == [
        "passed_deal", "passed_deal", "observed_game"]
    follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                   immediate_sample_count="4"))
    app = localized_server.app_context
    active = app.managed_stateful.active_match
    report = active.capture.report_store.list()[0]
    assert report.value.status == "executed"
    download_route = f"/matches/api/v1/reports/{report.report_id}.json"
    download = browser.request("GET", download_route)[2]
    exported = app.managed_home.root.parent / "independent-result.json"
    exported.write_bytes(download)
    page = browser.page("/matches/position/3")
    play_form = operation_form(page, "append_plays")
    page = follow(browser, browser.submit(entry_action(page, 2, rewind=True)))
    recovery = (active.recovery.selected, active.recovery.preview)
    correction = Forms(page).find("/matches/recovery/apply")
    disk = path.read_bytes()
    page = preview(browser, "matches", active.handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/cancel")))
    assert active.capture.report_store.list() == (report,) and active.selected_position == 3
    assert (active.recovery.selected, active.recovery.preview) == recovery
    assert browser.request("GET", download_route)[2] == download and path.read_bytes() == disk
    # A real second source, created through the normal native flow, is deleted inactive.
    other, _ = create_recording(browser, "matches")
    form = next(form for form in Forms(browser.page("/matches")).forms
                if form["action"] == "/matches/open" and form["values"]["handle"] == active.handle)
    follow(browser, browser.submit(form))
    active = app.managed_stateful.active_match
    page = browser.page("/matches/position/3")
    follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                   immediate_sample_count="4"))
    report = active.capture.report_store.list()[0]
    page = preview(browser, "matches", other.handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                   confirm_delete="on"))
    assert not other.path.exists() and active.capture.report_store.list() == (report,)
    # Real Corpus initialization and explicit Workspace transfer, no injected copies.
    form = Forms(browser.page("/learning")).find("/learning/create")
    follow(browser, browser.submit(form, collection_name="Independent synthetic Learning"))
    learning = app.managed_stateful.active_learning
    page = browser.page("/matches/position/3")
    follow(browser, browser.submit(Forms(page).find("/matches/transfer-workspace")))
    store = load_learning_corpus_directory_v1(learning.path)
    assert store.document.catalog.current_matches
    copied = {p.relative_to(learning.path): p.read_bytes()
              for p in learning.path.rglob("*.json")}
    session, _ = create_recording(browser, "sessions")
    session_bytes = session.path.read_bytes()
    page = preview(browser, "matches", active.handle)
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                   confirm_delete="on"))
    assert not path.exists() and active.retired
    assert not active.capture.report_store.list() and active.recovery.selected is None
    assert browser.submit(play_form, cards="S7")[0] == 409
    assert browser.submit(correction, confirm_apply="on")[0] == 409
    assert browser.request("GET", download_route)[0] == 404
    assert not path.exists()
    reopened = load_learning_corpus_directory_v1(learning.path)
    assert reopened == store
    assert {p.relative_to(learning.path): p.read_bytes()
            for p in learning.path.rglob("*.json")} == copied
    assert app.managed_stateful.active_learning is learning
    assert session.path.read_bytes() == session_bytes and exported.read_bytes() == download


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_delayed_genuine_execution_cannot_publish_after_active_deletion(
    localized_server, monkeypatch, family,
):
    browser = Browser(localized_server)
    if family == "sessions":
        record_live_game(browser)
        form = Forms(browser.page()).find("/sessions/review-decision")
        module, name = session_execution, "execute"
        active = localized_server.app_context.managed_stateful.active_session
    else:
        _, _, page = open_partial_match(browser)
        form = operation_form(page, "analyze_decision")
        form["values"]["immediate_sample_count"] = "4"
        module, name = match_execution, "execute_match_decision_analysis_v1"
        active = localized_server.app_context.managed_stateful.active_match
    entered, proceed = Event(), Event()
    real = getattr(module, name)
    executed = []
    def delayed(*args, **kwargs):
        value = real(*args, **kwargs)
        executed.append(value)
        entered.set()
        assert proceed.wait(30)
        return value
    monkeypatch.setattr(module, name, delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(browser.submit, form)
        try:
            assert entered.wait(30)
            page = preview(browser, family, active.handle)
            follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                           confirm_delete="on"))
            assert active.retired and not active.path.exists()
        finally:
            proceed.set()
        assert worker.result(timeout=30)[0] == 409
    assert len(executed) == 1 and not active.path.exists()
    if family == "sessions":
        assert active.execution is active.recorded_review_source is None
    else:
        assert active.capture.workspace is None and not active.capture.report_store.list()


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_reopening_same_file_invalidates_exact_preview(localized_server, family):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, family)
    page = preview(browser, family, active.handle)
    apply = Forms(page).find("/recordings/delete/apply")
    follow(browser, browser.submit(Forms(browser.page(f"/{family}")).find(f"/{family}/open")))
    assert browser.submit(apply, confirm_delete="on")[0] == 409
    assert active.path.exists() and not active.retired


def test_transfer_captured_before_deletion_completes_independently(localized_server, monkeypatch):
    import skatmind.app_web.cross_area_transfer as transfer
    browser = Browser(localized_server)
    _, _, _ = open_partial_match(browser)
    app = localized_server.app_context
    source = app.managed_stateful.active_match
    form = Forms(browser.page("/learning")).find("/learning/create")
    follow(browser, browser.submit(form, collection_name="Captured independent copy"))
    target = app.managed_stateful.active_learning
    form = Forms(browser.page("/matches/position/3")).find("/matches/transfer-workspace")
    real = transfer.import_workspace_bytes_into_unified_learning_v1
    entered, proceed = Event(), Event()
    captured = []
    def delayed(context, content, **kwargs):
        captured.append(content)
        entered.set()
        assert proceed.wait(20)
        return real(context, content, **kwargs)
    monkeypatch.setattr(transfer, "import_workspace_bytes_into_unified_learning_v1", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        worker = pool.submit(browser.submit, form)
        try:
            assert entered.wait(20)
            page = preview(browser, "matches", source.handle)
            follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                           confirm_delete="on"))
        finally:
            proceed.set()
        result = worker.result(timeout=20)
    assert result[0] == 303 and result[1]["location"] == "/learning/current"
    store = load_learning_corpus_directory_v1(target.path)
    assert len(captured) == 1 and len(store.document.catalog.current_matches) == 1
    assert source.retired and source.transfer_notice is None and not source.path.exists()


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_equal_revision_valid_product_replacement_conflicts(localized_server, family):
    from dataclasses import replace

    import skatmind.api.v1.session as api
    from skatmind.api.v1.session import files
    from skatmind.match_workspace_contracts import create_match_workspace_v1
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )
    browser = Browser(localized_server)
    active, _ = create_recording(browser, family)
    form = Forms(preview(browser, family, active.handle)).find("/recordings/delete/apply")
    if family == "sessions":
        state = api.create_session(session_id=active.state.session_id,
            players=tuple(replace(player, player_label="Changed " + player.player_label)
                          for player in active.state.players),
            capture_mode=active.state.capture_mode,
            local_player_id=active.state.local_player_id).value
        assert state.revision == active.state.revision
        document = api.build_session_persistence_document(state).value
        assert files.save_session_file(active.path, document,
            expected_content_fingerprint=active.document.content_fingerprint
        ).value.status == "saved"
    else:
        workspace = create_match_workspace_v1(replace(
            active.workspace.match_definition, title="Equal-revision changed source"))
        assert workspace.revision == active.workspace.revision
        assert save_match_workspace_file_v1(active.path,
            build_match_workspace_persistence_document_v1(workspace),
            expected_content_fingerprint=active.capture.content_fingerprint).status == "saved"
    changed = active.path.read_bytes()
    assert browser.submit(form, confirm_delete="on")[0] == 409
    assert active.path.read_bytes() == changed and not active.retired


def test_accepted_edit_after_preview_preserves_new_source_on_delete_conflict(localized_server):
    browser = Browser(localized_server)
    active, _ = create_recording(browser, "sessions")
    command = Forms(browser.page()).find("/sessions/command", kind="set_game_metadata")
    form = Forms(preview(browser, "sessions", active.handle)).find("/recordings/delete/apply")
    follow(browser, browser.submit(command))
    changed = active.path.read_bytes()
    assert active.state.revision == 1
    assert browser.submit(form, confirm_delete="on")[0] == 409
    assert active.path.read_bytes() == changed and not active.retired
