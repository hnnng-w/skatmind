"""Completed operations acknowledge once, independently of retained Product outcomes."""

import http.client
from concurrent.futures import ThreadPoolExecutor
from html import escape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_learning_direct_entry_web import (
    add_form,
    build,
    create_collection,
    downloads,
    saved_bytes,
    source_handle,
)
from test_local_time_entry_web import local_form
from test_match_game_navigation_web import create_empty, declare, primary
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_review_navigation import chooser_form, external_pass, saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_direct_card_start_web import create
from test_session_recorded_review_web import Browser, Forms

import skatmind.api.v1.session.files as session_files
import skatmind.app_web.server as server_module
from skatmind.app_web.operation_feedback import feedback_source
from skatmind.app_web.task_first_session_rendering import render_task_first_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck


def notices(page):
    return [node for node in Hierarchy(page).nodes
            if "data-operation-feedback" in node["attrs"]]


def notice(page, key, locale="en", **values):
    rows = notices(page)
    assert len(rows) == 1
    assert rows[0]["text"] == text(locale, "feedback." + key, **values)
    assert Hierarchy.visible(rows[0])
    assert rows[0]["attrs"]["role"] == "status"
    assert "autofocus" not in rows[0]["attrs"]
    return rows[0]


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


@pytest.mark.parametrize("outcome", ("created", "applied", "unchanged"))
def test_retained_session_outcome_is_not_a_repeatable_success(localized_server, outcome):
    browser = Browser(localized_server)
    create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    if outcome == "applied":
        browser.command("set_game_metadata")
    elif outcome == "unchanged":
        follow(browser, browser.submit(Forms(browser.page()).find("/sessions/undo"),
                                       target_revision=str(active.state.revision)))
    operation, document = active.last_operation, active.document
    assert operation.status == outcome
    before = active.path.read_bytes()
    for _ in range(2):
        # A projection must never consume or reconstruct a routine success.
        rendered = render_task_first_session_v1(active, locale="de")
        assert text("de", "task.operation.saved") not in rendered
    for _ in range(2):
        page = browser.page()
        assert text("en", "task.operation.saved") not in page
    assert active.last_operation is operation and active.document is document
    assert active.path.read_bytes() == before


@pytest.mark.parametrize("locale", ("de", "en"))
def test_session_creation_batch_actor_and_passive_bytes(localized_server, monkeypatch, locale):
    browser = Browser(localized_server)
    page = browser.page("/sessions")
    follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language=locale))
    saves = []
    real_save = session_files.save_session_file
    def save(*a, **kw):
        saves.append(a)
        return real_save(*a, **kw)
    monkeypatch.setattr(session_files, "save_session_file", save)
    page = create(browser)
    notice(page, "session_created", locale)
    active = localized_server.app_context.managed_stateful.active_session
    form = Forms(page).find("/sessions/cards")
    response = browser.submit(form, cards=get_full_deck()[:10])
    assert response[0] == 303
    receipt = active.operation_feedback.pending
    assert receipt is not None and active.state.revision == 11
    assert len(saves) == 2
    # Projections, unrelated HTML, assets, JSON downloads and HEAD cannot consume.
    render_task_first_session_v1(active, locale=locale)
    for route in ("/", "/learning", "/assets/app.css", "/matches/assets/capture.js",
                  "/sessions/downloads/session.json"):
        browser.request("GET", route)
    browser.request("HEAD", "/sessions/current")
    assert active.operation_feedback.pending is receipt
    saved = active.path.read_bytes()
    operation = active.last_operation
    page = follow(browser, response)
    row = notice(page, "initial_cards", locale, count=10, player="Alex")
    assert any(p["attrs"].get("id") == "session-recording" for p in row["parents"])
    assert active.last_operation is operation and active.path.read_bytes() == saved
    assert not notices(browser.page())
    browser.command("set_declarer")
    notice(browser.page(), "declarer", locale)
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    page = browser.page()
    notice(page, "declaration", locale)
    response = browser.submit(Forms(page).find("/sessions/play"), cards="CK")
    page = follow(browser, response)
    from skatmind.app_web.stateful_localization import card_name
    notice(page, "play", locale, card=card_name(locale, "CK"), player="Alex")
    assert active.state.command_log[-1].command.player_id == active.state.players[0].player_id
    assert len(saves) == 5
    document, before = active.document, active.path.read_bytes()
    for language in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=language))
        assert not notices(page)
    assert active.document is document and active.path.read_bytes() == before and len(saves) == 5


def test_same_source_competing_reads_and_wrong_source_navigation_are_distinct(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    assert browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"])[0] == 303
    active = localized_server.app_context.managed_stateful.active_session
    retained = active.last_operation
    with ThreadPoolExecutor(max_workers=2) as pool:
        pages = list(pool.map(lambda _: browser.page(), range(2)))
    assert sorted(len(notices(page)) for page in pages) == [0, 1]
    assert active.last_operation is retained
    page = create_empty(browser, "en")
    active_match = localized_server.app_context.managed_stateful.active_match
    assert browser.submit(primary(page, "start_game"))[0] == 303
    assert active_match.operation_feedback.pending is not None
    assert not notices(browser.page("/matches/position/2"))
    assert not notices(browser.page("/matches/position/1"))


def test_latest_rejection_and_retirement_do_not_replay_pending_success(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    form = Forms(page).find("/sessions/cards")
    assert browser.submit(form, cards=["CA"])[0] == 303
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    status, _, body = browser.submit(form, cards=["CA"])
    assert status == 409 and not notices(body.decode()) and 'role="alert"' in body.decode()
    assert active.path.read_bytes() == before and active.operation_feedback.pending is None
    page = browser.page()
    assert browser.submit(Forms(page).find("/sessions/cards"), cards=["C10"])[0] == 303
    pending = active.operation_feedback.pending
    assert pending is not None
    follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    assert localized_server.app_context.managed_stateful.active_session is not active
    assert not notices(browser.page())


@pytest.mark.parametrize("locale", ("de", "en"))
def test_match_card_correction_noop_and_pass_are_contextual(localized_server, locale):
    browser = Browser(localized_server)
    page = create_empty(browser, locale)
    notice(page, "match_created", locale)
    active = localized_server.app_context.managed_stateful.active_match
    page = follow(browser, browser.submit(primary(page, "start_game")))
    notice(page, "game_started", locale, number=1)
    page = declare(browser, page)
    notice(page, "declaration", locale)
    from skatmind.app_web.stateful_localization import card_name
    for card, actor in (("CK", "Anna"), ("C7", "Boris"), ("CA", "Clara")):
        page = follow(browser, browser.submit(primary(page, "append_plays"), cards=card))
        notice(page, "play", locale, card=card_name(locale, card), player=actor)
    for replacement, changed in (("C10", True), ("C10", False)):
        before, revision = active.path.read_bytes(), active.workspace.revision
        page = follow(browser, browser.submit(entry_action(page, 3)))
        assert not notices(page)
        page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"),
                                              card=replacement))
        assert not notices(page) and active.path.read_bytes() == before
        page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/apply"),
                                              confirm_apply="on"))
        if changed:
            notice(page, "correction", locale)
            assert active.workspace.revision == revision + 1
        else:
            assert not notices(page) and active.path.read_bytes() == before
        assert not notices(browser.page("/matches/current"))
    page = browser.page("/matches/position/2")
    page = follow(browser, browser.submit(primary(page, "mark_passed_deal")))
    notice(page, "game_passed", locale, number=2)
    saved = active.path.read_bytes()
    for route in ("/matches/downloads/workspace.json", "/matches/position/1",
                  "/matches/position/2"):
        assert not notices(browser.request("GET", route)[2].decode())
    assert active.path.read_bytes() == saved


def test_learning_creation_add_noop_retained_version_selection_and_build(localized_server):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    page = create_collection(browser)
    notice(page, "learning_created")
    target = localized_server.app_context.managed_stateful.active_learning
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    row = notice(page, "version_added")
    assert any(p["attrs"].get("id", "").startswith("learning-match-") for p in row["parents"])
    assert not notices(browser.page("/learning/current"))
    page = build(browser)
    notice(page, "prepared")
    prepared, result = target.corpus.prepared_artifacts, target.last_result
    exact_downloads, files = downloads(browser), saved_bytes(target.path)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    assert not notices(page) and "identical content" in page
    assert target.last_result.status == "unchanged" and result.status == "prepared"
    assert target.corpus.prepared_artifacts is prepared and downloads(browser) == exact_downloads
    assert saved_bytes(target.path) == files
    external_pass(path, workspace)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    assert not notices(page) and "keeping the previously selected" in page
    assert "Prepared results were cleared" in page
    page = follow(browser, browser.submit(operation_form(page, "select_current_snapshot")))
    notice(page, "version_selected")
    assert not notices(browser.page("/learning/current"))


@pytest.mark.parametrize("family", ("session", "match", "learning"))
def test_real_product_creation_then_injected_profile_failure_is_only_a_warning(
    localized_server, monkeypatch, family,
):
    browser = Browser(localized_server)
    def fail(*args, **kwargs):
        raise OSError("Synthetic profile-only fault; never reflect this raw text")
    monkeypatch.setattr(server_module, "save_prepared_frontend_profile_v1", fail)
    page = (create(browser) if family == "session" else create_empty(browser, "en")
            if family == "match" else create_collection(browser))
    active = getattr(localized_server.app_context.managed_stateful, "active_" + family)
    assert active.path.exists() and active.operation_feedback.pending is None
    assert not notices(page) and text("en", "creation.profile_storage_warning") in page
    assert "Synthetic profile-only fault" not in page
    assert 'class="profile-warning"' in page and 'data-operation-feedback' not in page


def test_real_card_validation_preserves_safe_values_and_warning_priority(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    status, _, raw = browser.submit(Forms(page).find("/sessions/cards"), cards=["CA", "CA", "SJ"])
    page = raw.decode()
    assert status == 400 and not notices(page)
    assert 'role="alert"' in page and 'autofocus' in page
    assert 'aria-invalid="true"' in page
    assert Forms(page).find("/sessions/cards")["values"]["cards"] == ["CA", "SJ"]
    assert active.path.read_bytes() == before
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language="de"))
    assert not notices(page) and escape(text("de", "validation.card_entry.duplicate")) in page


def test_delivery_expiry_uses_fake_clock_without_replaying_or_reading_source(localized_server,
                                                                          monkeypatch):
    import skatmind.app_web.operation_feedback as feedback
    browser = Browser(localized_server)
    page = create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    monkeypatch.setattr(feedback.time, "monotonic", lambda: 100)
    assert browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"])[0] == 303
    assert active.operation_feedback.pending.expires_at == 160
    monkeypatch.setattr(feedback.time, "monotonic", lambda: 160)
    assert not notices(browser.page())
    assert active.operation_feedback.pending is None
    assert active.last_operation.status == "applied" and active.state.revision == 2
    assert feedback_source(active).references[1] is active.document


def test_skat_discards_and_metadata_batches_name_saved_evidence(localized_server):
    browser = Browser(localized_server)
    page = create(browser)
    page = follow(browser, browser.submit(local_form(page, "session-metadata"),
                                          local_date="2026-01-15", local_time="19:30"))
    notice(page, "details")
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"),
                                          cards=get_full_deck()[:10]))
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="false")
    page = follow(browser, browser.submit(Forms(browser.page()).find("/sessions/cards"),
                                          cards=["D7", "H7"]))
    notice(page, "skat", count=2)
    page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=["D7", "CA"]))
    notice(page, "discards", count=2)


def test_match_metadata_feedback_is_at_its_existing_native_return_target(localized_server):
    browser = Browser(localized_server)
    page = create_empty(browser, "en")
    response = browser.submit(local_form(page, "match-metadata"), time_mode="replace",
                              local_date="2026-01-15", local_time="19:30")
    page = follow(browser, response)
    row = notice(page, "details")
    assert response[1]["location"].endswith("#match-metadata")
    assert any(p["attrs"].get("id") == "match-metadata" for p in row["parents"])


def test_failed_preparation_retains_exact_downloads_and_visible_error(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = build(browser)
    target = localized_server.app_context.managed_stateful.active_learning
    retained = target.corpus.prepared_artifacts
    before = downloads(browser)
    status, _, raw = browser.submit(operation_form(page, "prepare_learning_artifacts"),
                                    train_weight="0")
    page = raw.decode()
    assert status == 400 and not notices(page) and 'role="alert"' in page
    assert 'id="learning-results"' in page and 'name="train_weight"' in page
    assert target.corpus.prepared_artifacts is retained and downloads(browser) == before


def test_real_unlocked_preparation_losing_source_cannot_publish_notice(
    localized_server, monkeypatch,
):
    import skatmind.corpus_web.preparation as preparation
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    target = localized_server.app_context.managed_stateful.active_learning
    real = preparation.build_learning_corpus_player_catalog_v1
    def superseded(*a, **kw):
        result = real(*a, **kw)
        target.corpus.reload()  # Real source reload at the established unlocked seam.
        return result
    monkeypatch.setattr(preparation, "build_learning_corpus_player_catalog_v1", superseded)
    status, _, raw = browser.submit(operation_form(browser.page("/learning/current"),
                                                   "prepare_learning_artifacts"))
    assert status == 409 and not notices(raw.decode())
    assert target.last_result.status == "source_changed"
    assert target.corpus.prepared_artifacts is None and target.operation_feedback.pending is None


def test_old_render_rejection_does_not_consume_new_source_receipt(localized_server, monkeypatch):
    from skatmind.app_web.session_frontend import apply_guided_session_command_v1
    from skatmind.session_commands import SetSessionGameMetadataCommandV1
    browser = Browser(localized_server)
    page = create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    assert browser.submit(Forms(page).find("/sessions/cards"), cards=["CA"])[0] == 303
    real = server_module.render_task_first_session_v1
    def intervening(*a, **kw):
        rendered = real(*a, **kw)
        result = apply_guided_session_command_v1(active, SetSessionGameMetadataCommandV1(
            expected_revision=active.state.revision,
            played_at="2026-01-15T18:30:00Z"))
        assert result.status == "applied", result
        return rendered
    with monkeypatch.context() as patch:
        patch.setattr(server_module, "render_task_first_session_v1", intervening)
        status, _, raw = browser.request("GET", "/sessions/current")
    assert status == 409 and not notices(raw.decode())
    assert active.operation_feedback.pending.message_key == "feedback.details"
    notice(browser.page(), "details")


def test_match_transfer_feedback_stays_open_untimed_and_noop_is_not_saved(localized_server):
    browser = Browser(localized_server)
    create_empty(browser, "en")
    create_collection(browser)
    page = browser.page("/matches/current")
    for key in ("feedback.transfer_version", "feedback.transfer_unchanged"):
        page = follow(browser, browser.submit(Forms(page).find("/matches/transfer-workspace")))
        assert escape(text("en", key)) in page and not notices(page)
        markup = Hierarchy(page)
        form = next(n for n in markup.nodes
                    if n["attrs"].get("action") == "/matches/transfer-workspace")
        assert Hierarchy.visible(form)
        page = browser.page("/matches/current")
        assert escape(text("en", key)) not in page


@pytest.mark.parametrize("entry", ("upload", "transfer"))
def test_identical_version_import_can_change_selection_without_adding_a_version(
    localized_server, entry,
):
    from test_learning_corpus_web_uploads import _multipart

    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    external_pass(path, workspace)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    target = localized_server.app_context.managed_stateful.active_learning
    snapshots = target.corpus.store.match_snapshots
    previous = target.corpus.store.document.catalog.current_matches
    assert len(snapshots) == 2
    if entry == "upload":
        form = operation_form(page, "import_match_workspace")
        body, content_type = _multipart(tuple({**form["values"],
            "selection_mode": "select_imported"}.items()),
            (("workspace_file", "synthetic.json", path.read_bytes(), "application/json"),))
        connection = http.client.HTTPConnection("127.0.0.1", localized_server.port, timeout=120)
        try:
            connection.request("POST", form["action"], body, {
                "Cookie": browser.cookie, "Origin": localized_server.origin,
                "Content-Type": content_type, "Accept-Language": "en"})
            response = connection.getresponse()
            assert response.status == 303, response.read().decode()
            location = response.getheader("Location")
            response.read()
        finally:
            connection.close()
        page = browser.page(location)
        notice(page, "version_selected")
    else:
        follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
        page = browser.page("/matches/current")
        page = follow(browser, browser.submit(Forms(page).find("/matches/transfer-workspace")))
        assert text("en", "feedback.version_selected") in page and not notices(page)
    assert target.last_result.status == "applied"
    assert target.last_result.state["relation"] == "duplicate_snapshot"
    assert target.corpus.store.match_snapshots == snapshots
    assert target.corpus.store.document.catalog.current_matches != previous
    assert text("en", "feedback.version_added") not in page
    if entry == "upload":
        assert not notices(browser.page("/learning/current"))
