import re
from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def switch(browser, page, locale):
    before = browser.server.app_context.frontend_profile.document
    page = follow(browser, browser.submit(
        Forms(page).find("/actions/profile/language"), language=locale))
    after = browser.server.app_context.frontend_profile.document
    if before is not None:
        excluded = {"language", "revision", "content_fingerprint"}
        assert {k: v for k, v in before.to_dict().items() if k not in excluded} == {
            k: v for k, v in after.to_dict().items() if k not in excluded}
    return page


def known_players(browser):
    for name in ("Alexandra-Maria Synthetic", "Boris", "Clara"):
        page = browser.page("/settings")
        add = next(form for form in Forms(page).forms
            if form["action"] == "/actions/profile/players/edit"
            and not form["values"]["player_handle"])
        page = follow(browser, browser.submit(add))
        form = Forms(page).find("/actions/profile/players/add")
        follow(browser, browser.submit(form, display_name=name))
    page = browser.page("/sessions")
    choices = re.search(r'<select name="forehand_handle"[^>]*>(.*?)</select>', page, re.S)[1]
    return re.findall(r'<option value="([0-9a-f]{64})"', choices)


def test_returned_session_creation_error_language_and_single_creation(localized_server):
    browser = Browser(localized_server)
    handles = known_players(browser)
    page = switch(browser, browser.page("/sessions"), "de")
    before = localized_server.app_context.frontend_profile.document.known_players
    form = Forms(page).find("/sessions/create")
    status, _, body = browser.submit(
        form, game_name="Retained synthetic game", perspective_seat="forehand",
        forehand_handle=handles[0], middlehand_handle=handles[0], rearhand_handle=handles[2],
        setup_action="update", save_players="on")
    assert status == 400
    page = body.decode()
    assert text("de", "validation.summary.heading") in page
    language = Forms(page).find("/actions/profile/language")
    assert language["values"]["return_to"] == "/sessions"
    page = switch(browser, page, "en")
    assert text("en", "validation.summary.heading") in page
    assert Forms(page).find("/sessions/create")["values"]["middlehand_handle"] == handles[0]
    assert localized_server.app_context.managed_stateful.active_session is None
    assert localized_server.app_context.frontend_profile.document.known_players == before
    page = switch(browser, page, "de")
    form = Forms(page).find("/sessions/create")
    assert form["values"]["game_name"] == "Retained synthetic game"
    assert form["values"]["profile_generation"] == str(
        localized_server.app_context.frontend_profile.generation)
    page = follow(browser, browser.submit(
        form, middlehand_handle=handles[1], setup_action="update"))
    page = follow(browser, browser.submit(
        Forms(page).find("/sessions/create"), setup_action="create"))
    active = localized_server.app_context.managed_stateful.active_session
    assert active is not None and active.state.revision == 0
    assert len(tuple(active.category_root.glob("*.json"))) == 1
    assert 'id="session-app"' in page


@pytest.mark.parametrize("route,action,field", (
    ("/matches/new", "/matches/api/v1/create", "match_title"),
    ("/learning", "/learning/create", "collection_name"),
))
def test_creation_rejection_emits_semantic_language_origin(localized_server, route, action, field):
    browser = Browser(localized_server)
    form = Forms(browser.page(route)).find(action)
    status, _, body = browser.submit(form, **{field: ""})
    assert status == 400
    page = body.decode()
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == route
    page = switch(browser, page, "de")
    assert text("de", "validation.summary.heading") in page
    assert Forms(page).find(action)["values"][field] == ""


@pytest.mark.parametrize("route", ("/", "/about", "/analyze", "/review", "/sessions",
                                  "/matches", "/matches/new", "/learning"))
def test_native_absolute_targets_and_origins_on_normal_pages(localized_server, route):
    browser = Browser(localized_server)
    page = browser.page(route)
    for locale in ("de", "en"):
        selector = Forms(page).find("/actions/profile/language")
        assert selector["values"]["return_to"] == route
        assert "language" not in selector["values"]
        page = switch(browser, page, locale)
        assert f'<html lang="{locale}">' in page
        assert f'value="{locale}" lang="{locale}" aria-pressed="true"' in page
        assert page.count('aria-pressed="true"') == 1
        assert '<select name="language"' not in page


@pytest.mark.parametrize("step", range(1, 8))
def test_all_review_steps_keep_exact_accepted_draft(localized_server, step):
    from test_guided_historical_review_form import _completed_example_draft

    from skatmind.app_web.workflow_state import ProcessLocalFrontendWorkflowStateV1
    # Real validated Historical form fixture; no workflow result is fabricated.
    draft = replace(_completed_example_draft(), step=step)
    state = ProcessLocalFrontendWorkflowStateV1(revision=7, draft=draft)
    localized_server.app_context.review_state = state
    browser = Browser(localized_server)
    page = browser.page("/review")
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        assert text(locale, f"guided.review.step.{step}") in page
        assert localized_server.app_context.review_state is state


def test_real_recorded_result_native_switch_preserves_bytes_and_execution_count(
    localized_server, monkeypatch,
):
    from test_session_recorded_review_web import record_live_game, review_first

    import skatmind.app_web.execution as execution
    browser = Browser(localized_server)
    record_live_game(browser, play_count=3)
    page, _ = review_first(browser)
    active = localized_server.app_context.managed_stateful.active_session
    original = active.path.read_bytes()
    retained = active.execution
    label = active.recorded_review_source
    generation = active.generation
    monkeypatch.setattr(execution, "execute", lambda *a, **k: pytest.fail("Unexpected execution"))
    for locale in ("de", "en"):
        response = browser.submit(Forms(page).find("/actions/profile/language"), language=locale)
        assert response[1]["location"] == "/sessions/current#session-result"
        page = follow(browser, response)
        assert active.execution is retained and active.recorded_review_source is label
        assert active.generation == generation and active.path.read_bytes() == original
        assert (browser.request("GET", "/sessions/downloads/result.json")[2]
                == retained.result_json_bytes)
        assert (browser.request("GET", "/sessions/downloads/request.json")[2]
                == retained.request_json_bytes)


def test_real_recovery_preview_language_overlay_does_not_apply_or_renew(localized_server):
    from test_match_recording_recovery_web import (
        entry_action,
        operation_form,
        start_match,
        synthetic_cards,
    )
    from test_task_first_language_preservation import enhanced_switch, envelope
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in synthetic_cards()[:6]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    page = follow(browser, browser.submit(entry_action(page, 2)))
    old_overlay = envelope(page, "/matches/recovery/preview", {"card": ["SQ"]})
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="SK"))
    active = localized_server.app_context.managed_stateful.active_match
    preview = active.recovery.preview
    original = active.path.read_bytes()
    for locale in ("de", "en"):
        # A verified preview no longer has an independently editable Card palette.
        # Its former selection overlay must not recreate one beside a stale Apply.
        assert enhanced_switch(browser, page, old_overlay, locale)[0] == 400
        page = switch(browser, browser.page("/matches/current"), locale)
        assert not any(form["action"] == "/matches/recovery/preview"
                       for form in Forms(page).forms)
        assert active.recovery.preview is preview
        assert active.path.read_bytes() == original
        apply = Forms(page).find("/matches/recovery/apply")
        assert "confirm_apply" not in apply["values"]
        assert apply["values"]["recovery_selection"] == preview.apply_token
    assert browser.submit(apply)[0] == 400
    # The original real preview can still be applied explicitly exactly once.
    page = follow(browser, browser.submit(apply, confirm_apply="on"))
    assert active.workspace.slots[0].observed_game.plays[1].card == "SK"
    assert browser.submit(apply, confirm_apply="on")[0] == 409


@pytest.mark.parametrize("change", (
    "position", "position_roundtrip", "reopen", "equal_revision", "preview_expiry",
))
def test_stale_match_language_binding_rejects_before_profile_save(
    localized_server, change, monkeypatch,
):
    from test_match_recording_recovery_web import (
        entry_action,
        operation_form,
        start_match,
        synthetic_cards,
    )

    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    browser = Browser(localized_server)
    page = start_match(browser)
    for card in synthetic_cards()[:3]:
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    active = localized_server.app_context.managed_stateful.active_match
    if change == "preview_expiry":
        page = follow(browser, browser.submit(entry_action(page, 2, rewind=True)))
    old = Forms(page).find("/actions/profile/language")
    original_profile = localized_server.app_context.frontend_profile
    if change in {"position", "position_roundtrip"}:
        status, _, body = browser.submit(operation_form(page, "append_plays"), cards="SA")
        assert status == 400
        old = Forms(body.decode()).find("/actions/profile/language")
        browser.page("/matches/position/2")
        assert localized_server.app_context.form_feedback.current(
            "matches", active_identity=active) is None
        if change == "position_roundtrip":
            browser.page("/matches/position/1")
    elif change == "reopen":
        landing = browser.page("/matches")
        follow(browser, browser.submit(Forms(landing).find("/matches/open")))
    elif change == "equal_revision":
        # Same-revision replacement is a context-race fixture, not a save success mock.
        active.capture.workspace = _build_match_workspace_v1(
            revision=active.workspace.revision, slots=active.workspace.slots,
            match_definition=replace(
                active.workspace.match_definition, title="Other exact content"))
    else:
        import skatmind.app_web.language_context as binding
        now = binding.time.monotonic()
        monkeypatch.setattr(binding.time, "monotonic", lambda: now + 1801)
    status, _, body = browser.submit(old, language="de")
    assert status == 409
    assert text("en", "validation.message.language_context_conflict") in body.decode()
    assert localized_server.app_context.frontend_profile is original_profile
    if change == "position":
        assert active.selected_position == 2


def test_profile_success_then_source_change_discards_overlay_without_rollback(
    localized_server, monkeypatch,
):
    import skatmind.app_web.server as server_module
    from skatmind.app_web.workflow_state import ProcessLocalFrontendWorkflowStateV1
    browser = Browser(localized_server)
    page = browser.page("/analyze")
    real_save = server_module.set_frontend_language_v1
    def interleaved(*args, **kwargs):
        result = real_save(*args, **kwargs)
        localized_server.app_context.analyze_state = ProcessLocalFrontendWorkflowStateV1(revision=1)
        return result
    monkeypatch.setattr(server_module, "set_frontend_language_v1", interleaved)
    status, _, body = browser.submit(Forms(page).find("/actions/profile/language"), language="de")
    assert status == 409 and b'<html lang="de">' in body
    assert text("de", "validation.message.language_context_saved_conflict") in body.decode()
    assert localized_server.app_context.frontend_profile.document.language == "de"
    assert localized_server.app_context.language_context.pending is None


@pytest.mark.parametrize("expired", (False, True))
def test_source_changes_between_prg_and_render_report_conflict(
    localized_server, monkeypatch, expired,
):
    from skatmind.app_web.workflow_state import ProcessLocalFrontendWorkflowStateV1
    browser = Browser(localized_server)
    page = browser.page("/review")
    response = browser.submit(Forms(page).find("/actions/profile/language"), language="de")
    assert response[0] == 303
    if expired:
        import skatmind.app_web.language_context as binding
        now = binding.time.monotonic()
        monkeypatch.setattr(binding.time, "monotonic", lambda: now + 1801)
    else:
        localized_server.app_context.review_state = ProcessLocalFrontendWorkflowStateV1(revision=1)
    status, _, body = browser.request("GET", response[1]["location"])
    assert status == 409 and b'<html lang="de">' in body
    assert text("de", "validation.message.language_context_saved_conflict") in body.decode()
    assert 'href="/review"' in body.decode()
    assert localized_server.app_context.language_context.pending is None


def test_real_match_report_and_learning_artifacts_keep_exact_downloads(
    localized_server, monkeypatch,
):
    from test_match_decision_review_preparation import _workspace_with_partial_game
    from test_match_recording_recovery_web import operation_form

    import skatmind.app_web.server as server_module
    from skatmind.app_web.match_frontend import (
        execute_unified_match_analysis_v1,
        import_unified_match_v1,
    )
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )
    browser = Browser(localized_server)
    page = browser.page("/learning")
    follow(browser, browser.submit(Forms(page).find("/learning/create"),
                                   collection_name="Exact artifact collection"))
    context = localized_server.app_context
    workspace, _ = _workspace_with_partial_game()
    active = import_unified_match_v1(context.managed_stateful.root("matches"), handle="6" * 64,
        document=build_match_workspace_persistence_document_v1(workspace).to_dict())
    context.managed_stateful.activate_match(active)
    analyzed = execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "3",
        "expected_revision": str(workspace.revision), "decision_index": "1",
    })
    report_id = analyzed.state["selected_report_id"]
    route = f"/matches/reports/{report_id}"
    page = browser.page(route)
    follow(browser, browser.submit(Forms(page).find("/matches/transfer-workspace")))
    page = browser.page(route)
    report_bytes = browser.request("GET", f"/matches/api/v1/reports/{report_id}.json")[2]
    workspace_bytes = active.path.read_bytes()
    # An actual rejected transfer must keep the exact Report origin, not its category.
    transfer = Forms(page).find("/matches/transfer-report")
    status, _, body = browser.submit(transfer, target_managed_handle="0" * 64)
    assert status == 409
    page = body.decode()
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == route
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == route
        assert active.selected_position == 3 and active.path.read_bytes() == workspace_bytes
        assert (browser.request("GET", f"/matches/api/v1/reports/{report_id}.json")[2]
                == report_bytes)
    language = Forms(page).find("/actions/profile/language")
    active.capture.report_store.clear()
    status, _, body = browser.submit(language, language="de")
    assert status == 409 and 'href="/matches"' in body.decode()
    assert text("en", "validation.message.language_context_conflict") in body.decode()
    page = browser.page("/learning/current")
    page = follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))
    learning = context.managed_stateful.active_learning
    retained = learning.corpus.prepared_artifacts
    store = learning.corpus.store
    paths = re.findall(r'href="(/learning/downloads/[^"]+)"', page)
    assert len(paths) == 10
    downloads = {path: browser.request("GET", path)[2] for path in paths}
    def forbidden(*args, **kwargs):
        pytest.fail("Language switching executed a Product operation")
    for name in ("execute_unified_match_analysis_v1", "prepare_unified_learning_artifacts_v1",
                 "transfer_active_match_workspace_to_corpus_v1"):
        monkeypatch.setattr(server_module, name, forbidden)
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        assert learning.corpus.store is store and learning.corpus.prepared_artifacts is retained
        assert {path: browser.request("GET", path)[2] for path in paths} == downloads


@pytest.mark.parametrize("boundary", ("foreign_route", "unknown_binding", "missing_context",
                                     "reopened_session", "review_step", "external_source"))
def test_native_stale_or_foreign_sources_are_contextual(localized_server, boundary):
    from test_session_recorded_review_web import record_live_game

    from skatmind.app_web.workflow_state import ProcessLocalFrontendWorkflowStateV1
    browser = Browser(localized_server)
    if boundary == "review_step":
        page = browser.page("/review")
        localized_server.app_context.review_state = ProcessLocalFrontendWorkflowStateV1(revision=1)
    else:
        record_live_game(browser, play_count=0)
        page = browser.page()
    form = Forms(page).find("/actions/profile/language")
    context = localized_server.app_context
    profile = context.frontend_profile
    if boundary == "foreign_route":
        form["values"]["return_to"] = "/about"
    elif boundary == "unknown_binding":
        form["values"]["_frontend_language_context"] = "0" * 64
    elif boundary == "missing_context":
        context.managed_stateful.active_session = None
    elif boundary == "reopened_session":
        follow(browser, browser.submit(Forms(browser.page("/sessions")).find("/sessions/open")))
    elif boundary == "external_source":
        # An external invalid writer is a real file change, never a successful workflow mock.
        context.managed_stateful.active_session.path.write_bytes(b"external invalid source")
    status, _, body = browser.submit(form, language="de")
    assert status == 409
    assert text("en", "validation.message.language_context_conflict") in body.decode()
    assert context.frontend_profile is profile


def test_browser_resolved_active_language_can_be_saved_and_noop_preserves_profile(localized_server):
    from skatmind.app_web.frontend_profile_persistence import load_frontend_profile_file_v1
    browser = Browser(localized_server)
    _, _, body = browser.request("GET", "/about", headers={"Accept-Language": "de-DE"})
    page = body.decode()
    assert 'value="de" lang="de" aria-pressed="true"' in page
    page = switch(browser, page, "de")
    path = localized_server.app_context.frontend_profile.profile_path
    original, stamp = path.read_bytes(), path.stat().st_mtime_ns
    page = switch(browser, page, "de")
    assert path.read_bytes() == original and path.stat().st_mtime_ns == stamp
    assert load_frontend_profile_file_v1(path.parent).document.language == "de"


def test_external_profile_conflict_stays_on_task_and_preserves_product_feedback(localized_server):
    from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
    from skatmind.app_web.frontend_profile_persistence import save_frontend_profile_file_v1
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/sessions"), "en")
    _, _, body = browser.submit(Forms(page).find("/sessions/create"), game_name="Rejected draft")
    page = body.decode()
    context = localized_server.app_context
    feedback = context.form_feedback._feedback["sessions"]
    profile = context.frontend_profile
    external = build_local_frontend_profile_v1(revision=1, language="de")
    assert save_frontend_profile_file_v1(context.managed_home.root, external,
        expected_fingerprint=profile.expected_fingerprint).status == "saved"
    persisted = profile.profile_path.read_bytes()
    status, _, body = browser.submit(Forms(page).find("/actions/profile/language"), language="de")
    assert status == 409
    html = body.decode()
    assert text("en", "error.profile_conflict.message") in html
    assert Forms(html).find("/actions/profile/language")["values"]["return_to"] == "/sessions"
    assert "Rejected draft" in html and context.form_feedback._feedback["sessions"] is feedback
    assert profile.profile_path.read_bytes() == persisted and context.frontend_profile is profile
