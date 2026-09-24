"""Genuine returned multipart forms, executed Reports and disposable persisted sources."""

import http.client
import json
from collections import Counter

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_learning_corpus_web_uploads import _multipart
from test_learning_direct_entry_web import (
    add_form,
    build,
    create_collection,
    downloads,
    independent_workspace,
    saved_bytes,
    source_handle,
)
from test_learning_report_attachment import upload_form, upload_nodes
from test_learning_version_selection_web import exact_selection, save_variant
from test_match_recording_recovery_web import follow, operation_form
from test_match_workspace_contracts import _observed_game
from test_recorded_review_navigation import chooser_form, external_pass, saved_partial_match
from test_session_recorded_review_web import Browser, Forms
from test_skatmind_rename import _legacy_report_source

import skatmind.app_web.learning_frontend as learning
import skatmind.capture_web.analysis as analysis
import skatmind.learning_corpus_strategy_teacher_builder as teacher
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.match_workspace_contracts import (
    _build_match_workspace_slot_v1,
    _build_match_workspace_v1,
)
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def submit_upload(browser, form, source, *, fields=None):
    """Send emitted text controls verbatim. Overrides are explicitly negative tests."""
    body, content_type = _multipart(tuple(form["values"].items()) if fields is None else fields,
        (("report_source_file", "synthetic-strategy-source.json", source, "application/json"),))
    connection = http.client.HTTPConnection("127.0.0.1", browser.server.port, timeout=120)
    try:
        connection.request("POST", form["action"], body, headers={"Cookie": browser.cookie,
            "Origin": browser.server.origin, "Content-Type": content_type, "Accept-Language": "en"})
        with connection.getresponse() as response:
            return (response.status, {k.lower(): v for k, v in response.getheaders()},
                    response.read())
    finally:
        connection.close()


def executed_source(browser, server):
    path, workspace = saved_partial_match(server)
    follow(browser, browser.submit(chooser_form(browser.page("/review/recorded"), "matches")))
    follow(browser, browser.submit(operation_form(browser.page("/matches/position/3"),
        "analyze_decision"), immediate_sample_count="2"))
    report = server.app_context.managed_stateful.active_match.capture.report_store.list()[0]
    assert report.value.status == "executed"
    status, headers, source = browser.request("GET",
        f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")
    assert status == 200 and '-strategy-source.json"' in headers["content-disposition"]
    return path, workspace, report, source


def add_source_match(browser, path):
    return follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))


def save_other(path, workspace):
    other = independent_workspace(workspace, "unrelated-match")
    other_path = path.with_name("unrelated.json")
    assert save_match_workspace_file_v1(other_path,
        build_match_workspace_persistence_document_v1(other),
        expected_content_fingerprint=None).status == "saved"
    return other_path, other


def open_other(browser, path):
    page = browser.page("/review/recorded")
    form = next(f for f in Forms(page).forms if f["action"] == "/review/open-recording"
                and f["values"]["handle"] == source_handle(path))
    return follow(browser, browser.submit(form))


def observe(monkeypatch):
    calls = Counter()
    for module, name, key in ((analysis, "execute_match_decision_analysis_v1", "analysis"),
        (learning, "prepare_learning_corpus_artifacts_web_v1", "preparation"),
        (teacher, "build_match_decision_position_request_v1", "reconciliation")):
        real = getattr(module, name)
        def counted(*args, _real=real, _key=key, **kwargs):
            calls[_key] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(module, name, counted)
    return calls


def test_real_singleton_attach_prepare_duplicate_language_reload_and_fresh_context(
    localized_server, monkeypatch,
):
    calls = observe(monkeypatch)
    browser = Browser(localized_server)
    path, _, report, source = executed_source(browser, localized_server)
    create_collection(browser)
    page = add_source_match(browser, path)
    active = localized_server.app_context.managed_stateful.active_learning
    files = saved_bytes(active.path)
    form = upload_form(page)
    _, nodes = upload_nodes(page)
    assert [n["attrs"]["type"] for n in nodes
            if n["attrs"].get("name") == "match_snapshot_id"] == ["hidden"]
    target = form["values"]["match_snapshot_id"]
    before = calls.copy()
    response = submit_upload(browser, form, source)
    assert response[0] == 303 and response[1]["location"] == "/learning/current"
    page = follow(browser, response)
    bound = active.corpus.strategy_source_store.sources[0]
    assert bound.match_snapshot_id == target and bound.source_report_id == report.report_id
    assert bound.report == report and active.corpus.prepared_artifacts is None
    assert calls - before == {"reconciliation": 1}
    assert saved_bytes(active.path) == files
    page = build(browser, page)
    prepared = active.corpus.prepared_artifacts
    retained = downloads(browser)
    before = calls.copy()
    page = follow(browser, submit_upload(browser, upload_form(page), source))
    assert active.last_result.status == "unchanged"
    assert active.corpus.strategy_source_store.sources == (bound,)
    assert active.corpus.prepared_artifacts is prepared
    assert calls - before == {"reconciliation": 1}
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        assert upload_form(page)["values"]["match_snapshot_id"] == target
        assert downloads(browser) == retained
    assert saved_bytes(active.path) == files
    assert calls["analysis"] == 1 and calls["preparation"] == 1
    page = follow(browser, browser.submit(operation_form(page, "reload_corpus")))
    assert active.corpus.strategy_source_store.sources == (bound,)
    assert active.corpus.prepared_artifacts is None
    state = learning.build_unified_learning_state_v1(active)
    assert state["strategy_sources"][0]["binding_status"] == "current"
    page = build(browser, page)
    assert downloads(browser) == retained
    page = follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/open")))
    reopened = localized_server.app_context.managed_stateful.active_learning
    assert reopened is not active and reopened.corpus.strategy_source_store.sources == ()
    assert reopened.corpus.prepared_artifacts is None and saved_bytes(reopened.path) == files


@pytest.mark.parametrize("add_unrelated", (False, True))
def test_old_singleton_stays_valid_after_unrelated_match_but_not_after_current_replacement(
    localized_server, add_unrelated,
):
    browser = Browser(localized_server)
    path, workspace, _, source = executed_source(browser, localized_server)
    other_path, _ = save_other(path, workspace)
    open_other(browser, other_path)
    create_collection(browser)
    page = add_source_match(browser, path)
    singleton = upload_form(page)
    first = singleton["values"]["match_snapshot_id"]
    if add_unrelated:
        add_source_match(browser, other_path)
    # No invented global-cardinality guard: exact original target is still Current.
    page = follow(browser, submit_upload(browser, singleton, source))
    active = localized_server.app_context.managed_stateful.active_learning
    bound = active.corpus.strategy_source_store.sources[0]
    assert bound.match_snapshot_id == first
    external_pass(path, workspace)
    page = add_source_match(browser, path)
    alternative = operation_form(page, "select_current_snapshot")
    second = alternative["values"]["match_snapshot_id"]
    page = follow(browser, browser.submit(alternative))
    assert "Bound to another saved version" in page
    assert 'value="prepare_learning_artifacts"' not in page
    assert "Saved recording revision 1" in page
    files, sources = saved_bytes(active.path), active.corpus.strategy_source_store.sources
    rejected = submit_upload(browser, singleton, source)
    assert rejected[0] == 400
    page = rejected[2].decode()
    assert text("en", "validation.message.file_reselection") in page
    assert "not accepted" in page and 'role="alert"' in page
    # A singleton's new transport is regenerated, explicitly described as an unaccepted retry.
    assert upload_form(page)["values"]["match_snapshot_id"] == ("" if add_unrelated else second)
    assert saved_bytes(active.path) == files
    assert active.corpus.strategy_source_store.sources == sources
    assert next(s.match_snapshot_id for s in active.corpus.store.document.catalog.current_matches
        if s.match_id == workspace.match_definition.match_id) == second
    page = follow(browser, browser.submit(exact_selection(page, first)))
    page = build(browser, page)
    assert active.corpus.prepared_artifacts is not None
    page = follow(browser, browser.submit(operation_form(page, "remove_strategy_teacher_report")))
    assert active.corpus.strategy_source_store.sources == ()
    assert active.corpus.prepared_artifacts is None
    assert path.exists()  # Removal leaves the original source recording intact.


def test_multiple_wrong_target_retry_preserves_actual_choice_and_valid_preparation(
    localized_server,
):
    browser = Browser(localized_server)
    path, workspace, _, source = executed_source(browser, localized_server)
    other_path, _ = save_other(path, workspace)
    open_other(browser, other_path)
    create_collection(browser)
    page = add_source_match(browser, path)
    right = upload_form(page)["values"]["match_snapshot_id"]
    page = add_source_match(browser, other_path)
    active = localized_server.app_context.managed_stateful.active_learning
    wrong = next(s.match_snapshot_id for s in active.corpus.store.document.catalog.current_matches
                 if s.match_snapshot_id != right)
    page = build(browser, page)
    prepared = active.corpus.prepared_artifacts
    files, retained = saved_bytes(active.path), downloads(browser)
    form = upload_form(page)
    form["values"]["match_snapshot_id"] = wrong  # A real offered select choice.
    response = submit_upload(browser, form, source)
    assert response[0] == 400
    page = response[2].decode()
    assert upload_form(page)["values"]["match_snapshot_id"] == wrong
    assert text("en", "validation.message.file_reselection") in page
    page = switch(browser, page, "de")
    assert upload_form(page)["values"]["match_snapshot_id"] == wrong
    assert text("de", "validation.message.file_reselection") in page
    assert active.corpus.prepared_artifacts is prepared and downloads(browser) == retained
    assert saved_bytes(active.path) == files and active.corpus.strategy_source_store.sources == ()
    form = upload_form(page)
    form["values"]["match_snapshot_id"] = right
    follow(browser, submit_upload(browser, form, source))
    assert active.corpus.prepared_artifacts is None
    assert active.corpus.strategy_source_store.sources[0].match_snapshot_id == right


@pytest.mark.parametrize("fault", ("missing", "duplicate", "foreign", "malformed", "extra"))
def test_untrusted_singleton_transport_rejects_without_implicit_target(localized_server, fault):
    browser = Browser(localized_server)
    path, _, _, source = executed_source(browser, localized_server)
    create_collection(browser)
    page = add_source_match(browser, path)
    form = upload_form(page)
    active = localized_server.app_context.managed_stateful.active_learning
    fields = list(form["values"].items())
    if fault == "missing":
        fields = [(k, v) for k, v in fields if k != "match_snapshot_id"]
    elif fault == "duplicate":
        fields.append(("match_snapshot_id", form["values"]["match_snapshot_id"]))
    elif fault == "extra":
        fields.append(("expected_catalog_revision", "1"))
    else:
        fields = [(k, ("f" * 64 if fault == "foreign" else "invalid")
                   if k == "match_snapshot_id" else v) for k, v in fields]
    files = saved_bytes(active.path)
    response = submit_upload(browser, form, source, fields=tuple(fields))
    assert response[0] == 400 and b'role="alert"' in response[2]
    assert saved_bytes(active.path) == files and active.corpus.strategy_source_store.sources == ()
    assert upload_form(response[2].decode())["values"]["match_snapshot_id"] == (
        form["values"]["match_snapshot_id"])


def test_legacy_source_wrapper_is_accepted_but_plain_documents_are_not(localized_server):
    browser = Browser(localized_server)
    path, _, report, source = executed_source(browser, localized_server)
    create_collection(browser)
    page = add_source_match(browser, path)
    legacy = json.dumps(_legacy_report_source(json.loads(source))).encode()
    page = follow(browser, submit_upload(browser, upload_form(page), legacy))
    active = localized_server.app_context.managed_stateful.active_learning
    assert len(active.corpus.strategy_source_store.sources) == 1
    page = build(browser, page)
    prepared, retained = active.corpus.prepared_artifacts, downloads(browser)
    # Deliberately inappropriate/malformed input specimens, not successful Report exports.
    invalid = [report.value.request.to_dict(), report.value.result.to_dict(),
               report.value.request.to_dict()["document"],
               report.value.result.to_dict()["document"],
               json.loads(path.read_bytes())]
    for kind in ("historical_analysis", "materialization"):
        changed = json.loads(source)
        changed["report"]["report_kind"] = kind
        invalid.append(changed)
    for document in invalid:
        response = submit_upload(browser, upload_form(page), json.dumps(document).encode())
        assert response[0] == 400
        page = response[2].decode()
        assert text("en", "validation.message.file_reselection") in page
        assert active.corpus.prepared_artifacts is prepared and downloads(browser) == retained


def test_same_revision_matching_is_decision_reconciliation_not_whole_workspace_origin(
    localized_server,
):
    browser = Browser(localized_server)
    path, workspace, _, source = executed_source(browser, localized_server)
    other_path, _ = save_other(path, workspace)
    open_other(browser, other_path)
    create_collection(browser)
    page = add_source_match(browser, path)
    active = localized_server.app_context.managed_stateful.active_learning
    first = upload_form(page)["values"]["match_snapshot_id"]
    # Genuine valid metadata-only variant: exact source Decision still reconciles.
    compatible = save_variant(path, workspace, 2)
    response = browser.submit(add_form(browser), source_handle=source_handle(path),
                              same_revision_resolution="retain")
    page = follow(browser, response)
    compatible_id = active.entry_outcome.snapshot_id
    page = follow(browser, browser.submit(exact_selection(page, compatible_id)))
    page = follow(browser, submit_upload(browser, upload_form(page), source))
    assert active.corpus.strategy_source_store.sources[0].match_snapshot_id == compatible_id
    # Valid same-revision alternative with a changed Game identity is incompatible.
    slots = list(compatible.slots)
    game = slots[2].observed_game
    changed_game = _observed_game(compatible.match_definition, match_position=3,
        game_id="synthetic-different-game", game_timecode=game.game_timecode,
        perspective_initial_hand=game.perspective_initial_hand,
        declarer_player_id=game.declarer_player_id, declaration=game.declaration,
        original_skat=game.original_skat, discarded_cards=game.discarded_cards,
        plays=game.plays, commentaries=game.commentaries, response_links=game.response_links)
    slots[2] = _build_match_workspace_slot_v1(match_position=3, slot_kind="observed_game",
        observed_game=changed_game, passed_deal=None, match_definition=compatible.match_definition)
    incompatible = _build_match_workspace_v1(match_definition=compatible.match_definition,
        revision=compatible.revision, slots=tuple(slots))
    assert save_match_workspace_file_v1(path,
        build_match_workspace_persistence_document_v1(incompatible),
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(
            compatible).content_fingerprint
    ).status == "saved"
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path),
                                         same_revision_resolution="retain"))
    incompatible_id = active.entry_outcome.snapshot_id
    page = follow(browser, browser.submit(exact_selection(page, incompatible_id)))
    assert first != compatible_id != incompatible_id
    files = saved_bytes(active.path)
    response = submit_upload(browser, upload_form(page), source)
    assert response[0] == 400 and saved_bytes(active.path) == files
    assert active.corpus.strategy_source_store.sources[0].match_snapshot_id == compatible_id
    state = learning.build_unified_learning_state_v1(active)
    assert state["strategy_sources"][0]["binding_status"] == "non_current"
    page = follow(browser, browser.submit(operation_form(
        response[2].decode(), "clear_strategy_teacher_reports")))
    assert active.corpus.strategy_source_store.sources == ()
    build(browser, page)
    assert active.corpus.prepared_artifacts is not None
