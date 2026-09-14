from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path
from threading import Event
from urllib.parse import urlencode, urlsplit

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_decision_review_preparation import _workspace_with_partial_game
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first
from test_unified_local_app_managed_items import _save_session

import skatmind.app_web.execution as execution_module
import skatmind.app_web.recorded_review_opening as opening
import skatmind.capture_web.analysis as match_analysis
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_item_discovery import discover_managed_items_v1
from skatmind.app_web.recorded_review_opening import open_recording_for_review_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_historical_materialization import materialize_match_observed_game_historical_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


def external_pass(path, workspace):
    from skatmind.match_workspace_operations import mark_match_workspace_passed_deal_v1
    old = build_match_workspace_persistence_document_v1(workspace)
    changed = mark_match_workspace_passed_deal_v1(workspace, match_position=2,
        game_timecode=None, expected_revision=workspace.revision).workspace
    result = save_match_workspace_file_v1(
        path, build_match_workspace_persistence_document_v1(changed),
        expected_content_fingerprint=old.content_fingerprint)
    assert result.status == "saved"
    return changed


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def chooser_form(page, family):
    return next(form for form in Forms(page).forms if form["action"] == "/review/open-recording"
                and form["values"]["family"] == family)


def home_chooser(browser):
    page = browser.page("/")
    main = page.split('<main', 1)[1].split('</main>', 1)[0]
    link = re.search(r'<a[^>]+href="(/review/recorded)"', main)[1]
    return browser.page(link)


def saved_partial_match(server):
    workspace, _ = _workspace_with_partial_game()
    path = server.app_context.managed_stateful.root("matches") / "synthetic.json"
    document = build_match_workspace_persistence_document_v1(workspace)
    saved = save_match_workspace_file_v1(path, document, expected_content_fingerprint=None)
    assert saved.status == "saved"
    return path, workspace


def select_game(browser, page, position):
    selector = next(form for form in Forms(page).forms if "position" in form["values"])
    values = {**selector["values"], "position": str(position)}
    return follow(browser, browser.request("GET", selector["action"] + "?" + urlencode(values)))


def test_home_session_real_review_round_trip_keeps_exact_context_and_bytes(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    record_live_game(browser)
    active = localized_server.app_context.managed_stateful.active_session
    disk = active.path.read_bytes()
    generation, key = active.generation, active.review_selection_key
    calls = []
    real = execution_module.execute
    def counted(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(execution_module, "execute", counted)
    page = home_chooser(browser)
    form = chooser_form(page, "sessions")
    assert set(form["values"]) == {"family", "handle", "generation", "_frontend_form_instance"}
    response = browser.submit(form)
    assert response[1]["location"] == "/sessions/current#recorded-decisions"
    follow(browser, response)
    assert not calls
    _, review_form = review_first(browser)
    retained = active.execution
    source = active.recorded_review_source
    download = browser.request("GET", "/sessions/downloads/result.json")[2]
    request = browser.request("GET", "/sessions/downloads/request.json")[2]
    assert len(calls) == 1
    assert browser.submit(review_form, actual_card_played="CA")[0] == 400
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "sessions")))
    assert 'class="recorded-review-source"' in page
    assert text("en", "validation.recorded_review.invalid_fields") in page
    assert localized_server.app_context.managed_stateful.active_session is active
    assert (active.generation, active.review_selection_key) == (generation, key)
    assert active.execution is retained and active.recorded_review_source is source
    assert browser.request("GET", "/sessions/downloads/result.json")[2] == download
    assert browser.request("GET", "/sessions/downloads/request.json")[2] == request
    assert active.path.read_bytes() == disk and len(calls) == 1


def test_match_real_prepared_analysis_report_and_same_game_recording(localized_server, monkeypatch):
    path, workspace = saved_partial_match(localized_server)
    historical = materialize_match_observed_game_historical_v1(workspace, match_position=3)
    assert historical.status == "unavailable"
    disk = path.read_bytes()
    browser = Browser(localized_server)
    calls = []
    real = match_analysis.execute_match_decision_analysis_v1
    def counted(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    monkeypatch.setattr(match_analysis, "execute_match_decision_analysis_v1", counted)
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    active = localized_server.app_context.managed_stateful.active_match
    assert active.selected_position == 1 and not calls
    assert 'action="/matches/api/v1/operation"' not in page
    page = select_game(browser, page, 3)
    assert "2 of 6 recorded decisions" in page
    form = operation_form(page, "analyze_decision")
    assert form["values"]["decision_index"] == "1"
    assert "Trick 1" in page and "Actual Card" in page
    page = follow(browser, browser.submit(form))
    assert len(calls) == 1 and calls[0]["match_position"] == 3
    report = active.capture.report_store.list()[0]
    assert report.value.status == "executed"
    route = f"/matches/reports/{report.report_id}"
    download_route = f"/matches/api/v1/reports/{report.report_id}.json"
    assert download_route in page and "Game 3" in page
    assert 'id="match-review"' in page and 'id="match-recording"' not in page
    assert 'action="/matches/api/v1/operation"' not in page
    download = browser.request("GET", download_route)[2]
    back = re.search(r'href="(/matches/position/3#match-recording)"', page)[1]
    page = browser.page(urlsplit(back).path)
    review_link = re.search(r'href="(/matches/review/3)"', page)[1]
    page = browser.page(review_link)
    page = switch(browser, page, "de")
    assert report.report_id in page
    page = browser.page(route)
    page = switch(browser, page, "en")
    assert Forms(page).find("/actions/profile/language")["values"]["return_to"] == route
    assert browser.request("GET", download_route)[2] == download
    assert path.read_bytes() == disk and len(calls) == 1
    assert active.selected_position == 3


def test_same_source_preserves_real_recovery_but_selector_invalidates(localized_server):
    path, _ = saved_partial_match(localized_server)
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    select_game(browser, page, 3)
    page = browser.page("/matches/position/3")
    page = follow(browser, browser.submit(entry_action(page, 2, rewind=True)))
    active = localized_server.app_context.managed_stateful.active_match
    selection, preview = active.recovery.selected, active.recovery.preview
    apply = Forms(page).find("/matches/recovery/apply")
    disk = path.read_bytes()
    generation = active.position_generation
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    assert active.recovery.selected is selection and active.recovery.preview is preview
    assert active.position_generation == generation and active.selected_position == 3
    page = switch(browser, page, "de")
    assert active.recovery.preview is preview
    select_game(browser, page, 2)
    assert active.recovery.selected is None and active.recovery.preview is None
    assert browser.submit(apply, confirm_apply="on")[0] == 409
    assert path.read_bytes() == disk


def test_manual_partial_draft_survives_recorded_navigation(localized_server):
    browser = Browser(localized_server)
    page = browser.page("/review")
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/start")))
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/update-players")))
    state = localized_server.app_context.review_state
    assert state.draft.step == 2
    saved_partial_match(localized_server)
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    page = browser.page(re.search(r'href="(/review/recorded)"', page)[1])
    manual = re.search(r'href="(/review)"', page)[1]
    page = browser.page(manual)
    assert localized_server.app_context.review_state is state
    assert 'action="/actions/review/update-deal"' in page


@pytest.mark.parametrize("extra", ({"family": "corpora"}, {"path": "private.json"},
    {"destination": "/review"}, {"request": "{}"}, {"generation": "01"}))
def test_open_rejects_foreign_fields_with_semantic_error_language(localized_server, extra):
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    status, _, body = browser.submit(form, **extra)
    assert status == 400
    assert text("en", "validation.recordings.invalid") in body.decode()
    page = switch(browser, body.decode(), "de")
    assert text("de", "validation.recordings.invalid") in page
    language = Forms(page).find("/actions/profile/language")
    assert language["values"]["return_to"] == "/review/recorded"
    assert localized_server.app_context.managed_stateful.active_match is None


def test_discovery_staleness_invalid_duplicate_identity_and_missing_files(localized_server):
    path, _ = saved_partial_match(localized_server)
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    browser.page("/review/recorded")
    assert browser.submit(form)[0] == 409
    form = chooser_form(browser.page("/review/recorded"), "matches")
    path.unlink()
    assert browser.submit(form)[0] == 409
    root = localized_server.app_context.managed_stateful.root("sessions")
    _save_session(root / "a.json")
    _save_session(root / "b.json")
    (root / "invalid.json").write_text("{}")
    page = browser.page("/review/recorded")
    assert not any(f["action"] == "/review/open-recording" for f in Forms(page).forms)
    assert text("en", "creation.managed.status.resolution_required") in page
    assert text("en", "creation.managed.status.invalid") in page
    assert str(root) not in page and "invalid.json" not in page


def test_inactive_restart_reopen_loads_current_file_without_execution(
    localized_server, monkeypatch,
):
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    previous = localized_server.app_context.managed_stateful.active_match
    context = AppWebContextV1.create(localized_server.app_context.managed_home)
    localized_server.app_context = context
    def forbidden(*args, **kwargs):
        raise AssertionError("Opening must not execute")
    monkeypatch.setattr(match_analysis, "execute_match_decision_analysis_v1", forbidden)
    follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    active = context.managed_stateful.active_match
    assert active is not previous and active.workspace == previous.workspace
    assert not active.capture.report_store.list()


def test_racing_open_rechecks_discovery_before_activation(localized_server, monkeypatch):
    saved_partial_match(localized_server)
    context = localized_server.app_context
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    values = {k: v for k, v in form["values"].items() if k != "_frontend_form_instance"}
    entered, proceed = Event(), Event()
    real = opening.open_unified_match_v1
    def delayed(*args):
        active = real(*args)
        entered.set()
        assert proceed.wait(10)
        return active
    monkeypatch.setattr(opening, "open_unified_match_v1", delayed)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(open_recording_for_review_v1, context, values)
        assert entered.wait(10)
        browser.page("/review/recorded")
        proceed.set()
        with pytest.raises(opening.RecordingOpenConflict):
            future.result(timeout=10)
    assert context.managed_stateful.active_match is None


def test_discovery_limit_stays_bounded_without_eligibility(localized_server, monkeypatch):
    import skatmind.app_web.managed_item_discovery as discovery
    root = localized_server.app_context.managed_stateful.root("sessions")
    for index in range(4):
        _save_session(root / f"{index}.json", session_id=f"session-{index}")
    monkeypatch.setattr(discovery, "MANAGED_ITEM_MAX_CANDIDATES", 2)
    result = discover_managed_items_v1(root, family="sessions", generation=1)
    assert len(result.view.items) == 2 and result.view.candidate_limit_reached


def test_two_concurrent_http_opens_do_not_replace_the_winning_context(
    localized_server, monkeypatch,
):
    from skatmind.app_web.stateful_context import ManagedStatefulContextV1
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    entered, second_resolved, proceed = Event(), Event(), Event()
    loads, resolutions = [], []
    real_open = opening.open_unified_match_v1
    real_resolve = ManagedStatefulContextV1.resolve
    def delayed(*args):
        active = real_open(*args)
        loads.append(active)
        entered.set()
        assert proceed.wait(10)
        return active
    def resolve(self, *args, **kwargs):
        result = real_resolve(self, *args, **kwargs)
        resolutions.append(result)
        if len(resolutions) == 3:
            second_resolved.set()
        return result
    monkeypatch.setattr(opening, "open_unified_match_v1", delayed)
    monkeypatch.setattr(ManagedStatefulContextV1, "resolve", resolve)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(browser.submit, form)
        assert entered.wait(10)
        second = pool.submit(browser.submit, form)
        assert second_resolved.wait(10)
        proceed.set()
        assert first.result(timeout=10)[0] == 303
        assert second.result(timeout=10)[0] == 409
    assert len(loads) == 1
    assert localized_server.app_context.managed_stateful.active_match is loads[0]


def test_file_change_after_strict_open_before_publication_is_rejected(
    localized_server, monkeypatch,
):
    path, workspace = saved_partial_match(localized_server)
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    real = opening.open_unified_match_v1
    def changed_after_load(*args):
        loaded = real(*args)
        external_pass(path, workspace)
        return loaded
    monkeypatch.setattr(opening, "open_unified_match_v1", changed_after_load)
    assert browser.submit(form)[0] == 409
    assert localized_server.app_context.managed_stateful.active_match is None


def test_active_file_conflict_requires_explicit_reload_and_inactive_loads_current(localized_server):
    path, workspace = saved_partial_match(localized_server)
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    changed = external_pass(path, workspace)
    # An inactive open loads the current valid file, rather than discovery's old revision.
    page = follow(browser, browser.submit(form))
    active = localized_server.app_context.managed_stateful.active_match
    assert active.workspace == changed
    page = select_game(browser, page, 2)
    assert "Passed" in page and 'action="/matches/api/v1/operation"' not in page
    form = chooser_form(home_chooser(browser), "matches")
    from skatmind.match_workspace_operations import clear_match_workspace_slot_v1
    current = build_match_workspace_persistence_document_v1(changed)
    next_workspace = clear_match_workspace_slot_v1(changed, match_position=2,
        expected_revision=changed.revision).workspace
    assert save_match_workspace_file_v1(path,
        build_match_workspace_persistence_document_v1(next_workspace),
        expected_content_fingerprint=current.content_fingerprint).status == "saved"
    disk = path.read_bytes()
    status, _, body = browser.submit(form)
    assert status == 409 and escape(text("en", "validation.recordings.file")) in body.decode()
    assert active.workspace is not next_workspace and active.workspace == changed
    assert localized_server.app_context.managed_stateful.active_match is active
    reload_form = Forms(body.decode()).find("/matches/api/v1/reload")
    follow(browser, browser.submit(reload_form))
    assert active.workspace == next_workspace and path.read_bytes() == disk


def test_analysis_errors_keep_review_options_language_and_reject_old_source(localized_server):
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    page = select_game(browser, page, 3)
    form = operation_form(page, "analyze_decision")
    status, _, body = browser.submit(form, immediate_sample_count="-1", immediate_random_seed="27")
    assert status == 400 and 'id="match-review"' in body.decode()
    assert 'id="match-recording"' not in body.decode()
    language = Forms(body.decode()).find("/actions/profile/language")
    assert language["values"]["return_to"] == "/matches/review/3"
    page = switch(browser, body.decode(), "de")
    retried = operation_form(page, "analyze_decision")
    assert retried["values"]["immediate_random_seed"] == "27"
    assert retried["values"]["immediate_sample_count"] == "-1"
    active = localized_server.app_context.managed_stateful.active_match
    assert not active.capture.report_store.list()
    browser.page("/matches/review/2")
    status, _, body = browser.submit(form)
    assert status == 409 and 'id="match-review"' in body.decode()
    assert active.selected_position == 2 and not active.capture.report_store.list()
    # Reopening identical bytes through the legacy open is an explicit new context.
    follow(browser, browser.submit(Forms(browser.page("/matches")).find("/matches/open")))
    browser.page("/matches/review/3")
    assert browser.submit(form)[0] == 409


@pytest.mark.parametrize("download", (True, False))
def test_changed_file_invalidates_report_download_without_executor_retry(
    localized_server, download,
):
    path, workspace = saved_partial_match(localized_server)
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    page = select_game(browser, page, 3)
    follow(browser, browser.submit(operation_form(page, "analyze_decision")))
    active = localized_server.app_context.managed_stateful.active_match
    report = active.capture.report_store.list()[0]
    if not download:
        browser.page("/matches/review/2")
    external_pass(path, workspace)
    route = (f"/matches/api/v1/reports/{report.report_id}.json" if download
             else f"/matches/reports/{report.report_id}")
    status, _, body = browser.request("GET", route)
    assert status == 409 and 'id="match-review"' in body.decode()
    assert text("en", "validation.recordings.match_file") in body.decode()
    assert active.workspace == workspace and not active.capture.report_store.list()
    status, _, body = browser.request("GET", f"/matches/reports/{report.report_id}")
    assert status == 404 and text("en", "validation.recordings.report_missing") in body.decode()
    assert 'href="/matches/position/3#match-recording"' in body.decode()


def test_missing_report_feedback_survives_semantic_language_return(localized_server):
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    page = follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    select_game(browser, page, 3)
    status, _, body = browser.request("GET", "/matches/reports/" + "0" * 64)
    assert status == 404
    page = switch(browser, body.decode(), "de")
    assert text("de", "validation.recordings.report_missing") in page
    language = Forms(page).find("/actions/profile/language")
    assert language["values"]["return_to"] == "/matches/review/3"


def test_duplicate_names_are_distinct_and_source_switch_clears_only_prior_results(localized_server):
    browser = Browser(localized_server)
    record_live_game(browser)
    review_first(browser)
    original = localized_server.app_context.managed_stateful.active_session
    root = localized_server.app_context.managed_stateful.root("sessions")
    _save_session(root / "other.json", session_id="different-session")
    page = home_chooser(browser)
    forms = [form for form in Forms(page).forms if form["action"] == "/review/open-recording"]
    assert len(forms) == 2
    other = next(form for form in forms if form["values"]["handle"] != original.handle)
    page = follow(browser, browser.submit(other))
    assert text("en", "recorded_review.no_snapshots") in page
    assert original.execution is None and original.recorded_review_source is None
    assert localized_server.app_context.managed_stateful.active_session is not original
    # Same fallback Player names on two distinct semantic IDs must remain separate.
    _save_session(root / "another.json", session_id="another-session")
    page = home_chooser(browser)
    forms = [form for form in Forms(page).forms if form["action"] == "/review/open-recording"]
    assert len(forms) == 3 and len({form["values"]["handle"] for form in forms}) == 3
    assert page.count("Alice, Bob, Carol") == 2


def test_chooser_passive_paths_never_prepare_library_or_write(localized_server, monkeypatch):
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    root = localized_server.app_context.managed_home.root
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    def forbidden(*args, **kwargs):
        raise AssertionError("Passive library navigation must not prepare or execute")
    monkeypatch.setattr("skatmind.capture_web.state.build_match_decision_review_preparation_v1",
                        forbidden)
    monkeypatch.setattr("skatmind.capture_web.state.materialize_match_observed_game_historical_v1",
                        forbidden)
    monkeypatch.setattr(execution_module, "execute", forbidden)
    monkeypatch.setattr(match_analysis, "execute_match_decision_analysis_v1", forbidden)
    page = home_chooser(browser)
    generations = dict(localized_server.app_context.managed_stateful.generations)
    form = chooser_form(page, "matches")
    page = switch(browser, page, "de")
    assert chooser_form(page, "matches")["values"] == form["values"]
    assert localized_server.app_context.managed_stateful.generations == generations
    browser.page("/")
    assert localized_server.app_context.managed_stateful.generations == generations
    # Explicit language preference is the only permitted separate write.
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
            and p.name != "frontend-profile.json"} == before


@pytest.mark.parametrize("route", ("/review/recorded", "/matches/review/1", "/matches/review/36"))
def test_additive_get_routes_method_and_security_contract(localized_server, route):
    browser = Browser(localized_server)
    assert browser.request("POST", route, {})[0] == 405
    assert browser.request("PUT", route)[0] == 403  # No concrete mutation Origin.
    assert browser.request("GET", route, headers={"Cookie": ""})[0] == 403
    assert browser.request("GET", route + "?destination=/about")[0] == 403


@pytest.mark.parametrize("values", ({"handle": "0" * 64}, {"generation": "999"}))
def test_unknown_and_stale_open_remain_contextual(localized_server, values):
    saved_partial_match(localized_server)
    browser = Browser(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    assert browser.submit(form, **values)[0] == 409
    assert localized_server.app_context.managed_stateful.active_match is None


def test_open_security_no_active_context_and_exact_query_allowlist(localized_server):
    browser = Browser(localized_server)
    status, _, body = browser.request("GET", "/matches/review/1")
    assert status == 409 and text("en", "validation.recordings.no_active") in body.decode()
    assert browser.request("GET", "/review/open-recording")[0] == 405
    for query in ("position=0", "position=37", "position=01", "position=2&position=3",
                  "position=2&handle=foreign", "position=%32"):
        assert browser.request("GET", "/matches/review/1?" + query)[0] == 403
    for position in ("0", "37", "01", "-1"):
        assert browser.request("GET", "/matches/review/" + position)[0] == 404
    saved_partial_match(localized_server)
    form = chooser_form(home_chooser(browser), "matches")
    for headers in ({"Origin": "null"}, {"Origin": "http://foreign.invalid"}, {"Cookie": ""}):
        assert browser.request("POST", form["action"], form["values"], headers=headers)[0] == 403


def test_manual_import_and_real_result_survive_chooser(localized_server):
    import http.client
    browser = Browser(localized_server)
    page = browser.page("/review")
    form = Forms(page).find("/actions/review/import-json")
    example = Path(__file__).parents[1] / "examples/grand_post_game_mistake_actual_card.json"
    data = example.read_bytes()
    boundary = "navigation-manual-import"
    body = b""
    for key, value in form["values"].items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
                 f'{value}\r\n').encode()
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="request_file"; '
             'filename="synthetic.json"\r\nContent-Type: application/json\r\n\r\n').encode()
    body += data + f"\r\n--{boundary}--\r\n".encode()
    connection = http.client.HTTPConnection("127.0.0.1", localized_server.port, timeout=120)
    connection.request("POST", form["action"], body, {"Cookie": browser.cookie,
        "Origin": localized_server.origin,
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    response = connection.getresponse()
    assert response.status == 303, response.read().decode()
    response.read()
    connection.close()
    page = browser.page("/review")
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/run-imported")))
    state = localized_server.app_context.review_state
    result = browser.request("GET", "/downloads/review/result.json")[2]
    assert state.latest_successful_result is not None
    home_chooser(browser)
    page = browser.page("/review")
    assert localized_server.app_context.review_state is state
    assert browser.request("GET", "/downloads/review/result.json")[2] == result
