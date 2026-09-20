"""Real saved copies and native returned forms; every home is disposable."""

from dataclasses import replace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_review_navigation import chooser_form, external_pass, saved_partial_match
from test_recording_deletion_web import preview
from test_session_recorded_review_web import Browser, Forms, record_live_game, review_first

import skatmind.app_web.learning_direct_entry as entry
import skatmind.app_web.server as server_module
from skatmind.app_web.learning_frontend import build_unified_learning_state_v1
from skatmind.app_web.managed_item_storage import build_managed_item_handle_v1
from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
from skatmind.learning_corpus_persistence import load_learning_corpus_directory_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def create_collection(browser, name="Synthetic direct collection"):
    return follow(browser, browser.submit(Forms(browser.page("/learning")).find(
        "/learning/create"), collection_name=name))


def source_handle(path):
    return build_managed_item_handle_v1(family="matches", basename=path.name)


def add_form(browser):
    return Forms(browser.page("/learning/current")).find(entry.LEARNING_ADD_ROUTE)


def build(browser, page=None):
    page = page or browser.page("/learning/current")
    return follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))


def downloads(browser):
    result = {}
    for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
        status, headers, content = browser.request(
            "GET", f'/learning/downloads/{kind.replace("_", "-")}.json')
        assert status == 200
        result[kind] = (headers["content-disposition"], content)
    assert len(result) == 10
    return result


def saved_bytes(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*.json")}


def independent_workspace(workspace, identity):
    from test_match_workspace_contracts import _observed_game, _set_game

    from skatmind.match_workspace_contracts import create_match_workspace_v1
    definition = replace(workspace.match_definition, match_id=identity)
    source = workspace.slots[2].observed_game
    game = _observed_game(definition, match_position=3,
        perspective_initial_hand=source.perspective_initial_hand,
        declarer_player_id=source.declarer_player_id, declaration=source.declaration,
        original_skat=source.original_skat, discarded_cards=source.discarded_cards,
        plays=source.plays)
    return _set_game(create_match_workspace_v1(definition), game)


def test_returned_partial_add_build_versions_downloads_and_independent_recordings(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    app = localized_server.app_context
    # One genuine Session Result, plus one genuine Match Report/recovery preview.
    record_live_game(browser)
    review_first(browser)
    session = app.managed_stateful.active_session
    session_result = session.execution
    session_download = browser.request("GET", "/sessions/downloads/result.json")[2]
    path, workspace = saved_partial_match(localized_server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    page = browser.page("/matches/position/3")
    follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                   immediate_sample_count="2"))
    active = app.managed_stateful.active_match
    report = active.capture.report_store.list()[0]
    assert report.value.status == "executed"
    report_route = f"/matches/api/v1/reports/{report.report_id}.json"
    report_bytes = browser.request("GET", report_route)[2]
    follow(browser, browser.submit(entry_action(
        browser.page("/matches/position/3"), 2, rewind=True)))
    recovery = (active.recovery.selected, active.recovery.preview)
    # Separate logical Match, same title; saved fixture creation is not activation.
    source = independent_workspace(workspace, "independent-partial")
    source_path = path.with_name("inactive.json")
    assert save_match_workspace_file_v1(source_path,
        build_match_workspace_persistence_document_v1(source), expected_content_fingerprint=None
    ).status == "saved"
    create_collection(browser)
    follow(browser, browser.request("GET", entry.LEARNING_REFRESH_ROUTE))
    target = app.managed_stateful.active_learning
    before_profile = app.frontend_profile.profile_path.read_bytes()
    original_files = saved_bytes(app.managed_stateful.root("matches"))
    imports, builds = [], []
    real_import = entry.import_workspace_bytes_into_unified_learning_v1
    real_build = server_module.prepare_unified_learning_artifacts_v1
    def imported(*args, **kwargs):
        imports.append((args, kwargs))
        return real_import(*args, **kwargs)
    def prepared(*args, **kwargs):
        builds.append(kwargs)
        return real_build(*args, **kwargs)
    monkeypatch.setattr(entry, "import_workspace_bytes_into_unified_learning_v1", imported)
    monkeypatch.setattr(server_module, "prepare_unified_learning_artifacts_v1", prepared)
    form = add_form(browser)
    assert form["values"]["source_handle"] == ""
    assert set(form["values"]) == entry.LEARNING_ENTRY_FIELDS | {"_frontend_form_instance"}
    page = follow(browser, browser.submit(form, source_handle=source_handle(source_path)))
    assert "Match version added." in page and len(imports) == 1 and not builds
    assert imports[0][1]["selection_mode"] == "keep_current"
    assert target.corpus.prepared_artifacts is None
    store = load_learning_corpus_directory_v1(target.path)
    assert store.match_snapshots[0].workspace == source
    first = store.document.catalog.current_matches
    page = build(browser, page)
    state = build_unified_learning_state_v1(target)
    assert (state["prepared"]["observed_decision_count"], state["prepared"]["record_count"],
            state["prepared"]["skipped_decision_count"]) == (6, 2, 4)
    assert state["prepared"]["strategy_teacher_evidence_count"] == 0
    assert 'href="#learning-results"' in page and len(builds) == 1
    artifacts = target.corpus.prepared_artifacts
    actual_downloads = downloads(browser)
    files = saved_bytes(target.path)
    discovery = app.managed_stateful.discoveries["matches"]
    for route in ("/", "/learning/current", "/learning/current"):
        browser.page(route)
    page = switch(browser, browser.page("/learning/current"), "de")
    page = switch(browser, page, "en")
    assert app.managed_stateful.discoveries["matches"] is discovery
    # Language alone changes only its existing preference; then compare that profile.
    changed_profile = app.frontend_profile.profile_path.read_bytes()
    assert changed_profile != before_profile
    page = follow(browser, browser.submit(add_form(browser),
                                         source_handle=source_handle(source_path)))
    assert "identical content" in page
    assert target.corpus.prepared_artifacts is artifacts and downloads(browser) == actual_downloads
    assert saved_bytes(target.path) == files and len(builds) == 1
    form = add_form(browser)
    revised = external_pass(source_path, source)
    page = follow(browser, browser.submit(form, source_handle=source_handle(source_path)))
    assert f"saved revision {revised.revision}" in page
    assert "keeping the previously selected" in page
    assert target.corpus.store.document.catalog.current_matches == first
    assert target.corpus.prepared_artifacts is None
    page = follow(browser, browser.submit(operation_form(page, "select_current_snapshot")))
    assert target.corpus.store.document.catalog.current_matches != first
    build(browser, page)
    assert build_unified_learning_state_v1(target)["prepared"]["cross_game_match_count"] == 1
    follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    build(browser)
    assert build_unified_learning_state_v1(target)["prepared"]["cross_game_match_count"] == 2
    assert len(imports) == 4 and len(builds) == 3
    assert app.managed_stateful.active_match is active and active.selected_position == 3
    assert active.capture.report_store.list() == (report,)
    assert (active.recovery.selected, active.recovery.preview) == recovery
    assert browser.request("GET", report_route)[2] == report_bytes
    assert app.managed_stateful.active_session is session and session.execution is session_result
    assert browser.request("GET", "/sessions/downloads/result.json")[2] == session_download
    assert path.read_bytes() == original_files[path.relative_to(path.parent)]
    assert app.frontend_profile.profile_path.read_bytes() == changed_profile
    # Real #235 removal of the inactive editable source preserves the prepared copy.
    copied = saved_bytes(target.path)
    retained_downloads = downloads(browser)
    page = preview(browser, "matches", source_handle(source_path))
    follow(browser, browser.submit(Forms(page).find("/recordings/delete/apply"),
                                   confirm_delete="on"))
    assert not source_path.exists() and saved_bytes(target.path) == copied
    assert downloads(browser) == retained_downloads


@pytest.mark.parametrize("change", ("missing", "invalid", "identity", "duplicate"))
def test_revalidate_source_before_any_corpus_work(localized_server, monkeypatch, change):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    create_collection(browser)
    target = localized_server.app_context.managed_stateful.active_learning
    form = add_form(browser)
    if change == "missing":
        path.unlink()  # External disappearance of a disposable fixture.
    elif change == "invalid":
        path.write_bytes(b"{}")
    elif change == "duplicate":
        path.with_name("duplicate.json").write_bytes(path.read_bytes())
    else:
        replacement = independent_workspace(workspace, "replaced")
        assert save_match_workspace_file_v1(path,
            build_match_workspace_persistence_document_v1(replacement),
            expected_content_fingerprint=build_match_workspace_persistence_document_v1(
                workspace).content_fingerprint).status == "saved"
    before = saved_bytes(target.path)
    monkeypatch.setattr(entry, "import_workspace_bytes_into_unified_learning_v1",
                        lambda *a, **k: pytest.fail("Invalid source entered Corpus work"))
    status, _, body = browser.submit(form, source_handle=source_handle(path))
    assert status == 409 and b'id="learning-recorded-matches"' in body
    returned = Forms(body.decode()).find(entry.LEARNING_ADD_ROUTE)
    assert returned["values"]["source_handle"] == source_handle(path)
    assert saved_bytes(target.path) == before


@pytest.mark.parametrize("field", tuple(sorted(entry.LEARNING_ENTRY_FIELDS)))
def test_exact_field_cardinality_and_no_caller_payload(localized_server, field):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    form = add_form(browser)
    values = {**form["values"], "source_handle": source_handle(path)}
    values[field] = [values[field], values[field]]
    status, _, body = browser.request("POST", entry.LEARNING_ADD_ROUTE, values)
    assert status == 400 and b'id="learning-recorded-matches"' in body
    assert browser.submit(form, source_handle=source_handle(path), path=str(path))[0] == 400
    target = localized_server.app_context.managed_stateful.active_learning
    assert not target.corpus.store.match_snapshots


def test_http_bound_auth_refresh_and_no_automatic_work(localized_server, monkeypatch):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    app = localized_server.app_context
    discovery = app.managed_stateful.discoveries["matches"]
    form = add_form(browser)
    monkeypatch.setattr(entry, "import_workspace_bytes_into_unified_learning_v1",
                        lambda *a, **k: pytest.fail("Unexpected import"))
    assert browser.submit(form, source_handle=source_handle(path), extra="x" * 8192)[0] == 413
    for headers in ({"Origin": "null"}, {"Cookie": ""}, {"Origin": "https://example.com"}):
        assert browser.request("POST", entry.LEARNING_ADD_ROUTE, form["values"], headers)[0] == 403
    assert browser.request("GET", entry.LEARNING_ADD_ROUTE)[0] == 405
    assert browser.request("GET", entry.LEARNING_REFRESH_ROUTE + "?path=anything")[0] == 403
    response = browser.request("GET", entry.LEARNING_REFRESH_ROUTE)
    assert response[0] == 303 and response[1]["location"] == entry.LEARNING_ENTRY_LOCATION
    assert app.managed_stateful.discoveries["matches"] is not discovery
    assert browser.submit(form, source_handle=source_handle(path))[0] == 409
    assert not app.managed_stateful.active_learning.corpus.store.match_snapshots
