"""Scoped feedback over actual downloaded Report artifacts and emitted upload forms."""

import json
from contextlib import closing

import pytest
from test_analysis_download_details import download_nodes
from test_frontend_language_switching import localized_server as _server
from test_language_switch_context import switch
from test_learning_direct_entry_web import build, create_collection, downloads, saved_bytes
from test_learning_report_attachment import upload_form
from test_learning_report_attachment_web import (
    add_source_match,
    executed_source,
    observe,
    submit_upload,
)
from test_match_recording_recovery_web import follow
from test_operation_feedback_language import presentation
from test_operation_feedback_web import notice, notices
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser
from test_task_first_language_preservation import enhanced_switch

from skatmind.app_web.learning_report_feedback import ReportFileError, report_file_validation_issues
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def downloaded_result(browser, report):
    page = browser.page(f"/matches/reports/{report.report_id}")
    link, = (n for n in download_nodes(page) if n["text"] == text("en", "result.download_result"))
    status, _, raw = browser.request("GET", link["attrs"]["href"])
    assert status == 200
    return raw


def assert_rejection(page, locale, key, *, field_name="report_source_file", initial=True):
    tree = Hierarchy(page)
    summary, = (n for n in tree.nodes if n["attrs"].get("class") == "error-summary")
    assert text(locale, "validation.summary.heading") not in summary["text"]
    assert text(locale, "validation.summary.guidance") not in summary["text"]
    assert text(locale, "validation.report_file.heading") in summary["text"]
    assert text(locale, key) in summary["text"]
    if key == "validation.report_file.format":
        assert text(locale, "result.download_report_source") in summary["text"]
        assert text(locale, "result.downloads") in summary["text"]
    links = [n for n in tree.nodes if n["tag"] == "a" and summary in n["parents"]]
    assert len(links) == 1
    field = tree.by_id(links[0]["attrs"]["href"][1:])
    if field_name == "report_source_file":
        assert field["attrs"]["name"] == field_name
        assert field["attrs"]["aria-invalid"] == "true"
        assert "value" not in field["attrs"]
        descriptions = [tree.by_id(identifier)["text"]
                        for identifier in field["attrs"]["aria-describedby"].split()]
        assert any(text(locale, key) in description for description in descriptions)
    else:
        assert field["attrs"].get("name") == field_name or (
            field["attrs"].get("id") == "learning-report-target")
    if initial:
        assert "autofocus" in summary["attrs"]
    assert all("open" in p["attrs"] for p in summary["parents"] if p["tag"] == "details")
    assert text(locale, "validation.message.file_reselection") not in page
    assert text(locale, "validation.report_file.reselect") not in summary["text"]
    assert not notices(page)
    if key != "validation.report_file.format":
        hint, = (n for n in tree.nodes if n["tag"] == "p"
                 and n["text"] == text(locale, "validation.report_file.reselect"))
        assert "field-error" not in hint["attrs"].get("class", "")
        assert any(p["tag"] == "form" for p in hint["parents"])


def retained(active):
    return (active.corpus.store, active.corpus.prepared_artifacts,
            active.corpus.tactical_prepared_artifacts,
            active.corpus.tactical_coaching_prepared_artifacts)


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("already_bound", (False, True))
def test_downloaded_ordinary_result_explains_required_report_file(
    localized_server, monkeypatch, locale, already_bound,
):
    calls = observe(monkeypatch)
    browser = Browser(localized_server)
    path, _, report, source = executed_source(browser, localized_server)
    ordinary = downloaded_result(browser, report)
    create_collection(browser)
    page = add_source_match(browser, path)
    if already_bound:
        page = follow(browser, submit_upload(browser, upload_form(page), source))
    page = switch(browser, build(browser, page), locale)
    active = localized_server.app_context.managed_stateful.active_learning
    references, artifacts = retained(active), downloads(browser)
    sources = active.corpus.strategy_source_store.sources
    target = upload_form(page)["values"]["match_snapshot_id"]
    for filename in ("ordinary-result.json", "plausible-strategy-source.json"):
        files = saved_bytes(localized_server.app_context.managed_home.root)
        before = calls.copy()
        response = submit_upload(browser, upload_form(page), ordinary, filename=filename)
        assert response[0] == 400
        page = response[2].decode()
        assert_rejection(page, locale, "validation.report_file.format")
        assert upload_form(page)["values"]["match_snapshot_id"] == target
        assert active.corpus.strategy_source_store.sources == sources
        assert all(a is b for a, b in zip(references, retained(active), strict=True))
        assert downloads(browser) == artifacts
        assert saved_bytes(localized_server.app_context.managed_home.root) == files
        assert calls == before
    for other, enhanced in (("en" if locale == "de" else "de", False), (locale, True)):
        page = (follow(browser, enhanced_switch(browser, page,
                json.dumps(presentation(page, None, other)), other)) if enhanced
                else switch(browser, page, other))
        assert_rejection(page, other, "validation.report_file.format", initial=False)
        assert all(a is b for a, b in zip(references, retained(active), strict=True))
        assert active.corpus.strategy_source_store.sources == sources
        assert downloads(browser) == artifacts
    page = follow(browser, submit_upload(browser, upload_form(page), source,
                                         filename="renamed.data"))
    notice(page, "report_already_attached" if already_bound else "report_attached", locale)
    assert len(active.corpus.strategy_source_store.sources) == 1
    if already_bound:
        assert all(a is b for a, b in zip(references, retained(active), strict=True))
        assert downloads(browser) == artifacts
    else:
        assert active.corpus.prepared_artifacts is None
    page = follow(browser, submit_upload(browser, upload_form(page), source,
                                         filename="another-name.json"))
    notice(page, "report_already_attached", locale)


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("raw", (b'{"private-marker":', b"\xff", b"[]", b'{"a":1,"a":2}'))
def test_early_json_rejection_is_truthful_without_reaching_source_import(
    localized_server, monkeypatch, locale, raw,
):
    import skatmind.app_web.server as web

    browser = Browser(localized_server)
    path, _, _, _ = executed_source(browser, localized_server)
    create_collection(browser)
    page = switch(browser, build(browser, add_source_match(browser, path)), locale)
    active = localized_server.app_context.managed_stateful.active_learning
    references, artifacts, files = retained(active), downloads(browser), saved_bytes(active.path)
    monkeypatch.setattr(web, "import_report_source_bytes_into_unified_learning_v1",
                        lambda *a, **kw: pytest.fail("Malformed JSON reached the bytes importer"))
    response = submit_upload(browser, upload_form(page), raw)
    assert response[0] == 400
    page = response[2].decode()
    assert_rejection(page, locale, "validation.report_file.json")
    assert text(locale, "validation.report_file.format") not in page
    assert "private-marker" not in page
    assert all(a is b for a, b in zip(references, retained(active), strict=True))
    assert downloads(browser) == artifacts and saved_bytes(active.path) == files


@pytest.mark.parametrize("locale", ("de", "en"))
def test_wrong_target_media_and_active_conflict_do_not_claim_format(localized_server, locale):
    browser = Browser(localized_server)
    path, _, _, source = executed_source(browser, localized_server)
    create_collection(browser)
    page = switch(browser, add_source_match(browser, path), locale)
    form = upload_form(page)
    fields = tuple((key, "f" * 64 if key == "match_snapshot_id" else value)
                   for key, value in form["values"].items())
    response = submit_upload(browser, form, source, fields=fields)
    assert response[0] == 400
    page = response[2].decode()
    assert_rejection(page, locale, "validation.report_file.attachment",
                     field_name="match_snapshot_id")
    assert text(locale, "validation.report_file.format") not in page
    response = submit_upload(browser, upload_form(page), source, file_type="text/plain")
    assert response[0] == 400  # Existing file-part media rejection status.
    page = response[2].decode()
    assert_rejection(page, locale, "validation.message.upload_type")
    assert text(locale, "validation.report_file.format") not in page
    create_collection(browser, "Another collection")
    response = submit_upload(browser, form, source)
    assert response[0] == 409
    page = response[2].decode()
    assert text(locale, "validation.summary.conflict_heading") in page
    assert text(locale, "validation.message.stale") in page
    assert text(locale, "validation.report_file.format") not in page and not notices(page)


@pytest.mark.parametrize(("status", "error", "key"), (
    (413, OverflowError(), "validation.message.upload_size"),
    (415, TypeError(), "validation.message.upload_type"),
    (409, FileExistsError(), "validation.message.persistence_conflict"),
    (409, ReportFileError("format"), "validation.message.stale"),
))
def test_transport_and_conflict_statuses_take_precedence(status, error, key):
    issue, = report_file_validation_issues(error, status=status)
    assert issue.message_key == key


@pytest.mark.parametrize("fault", ("size", "media"))
def test_actual_shared_route_transport_rejection_preserves_preparation(localized_server, fault):
    import http.client

    from skatmind.corpus_web.contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES

    browser = Browser(localized_server)
    path, _, _, _ = executed_source(browser, localized_server)
    create_collection(browser)
    page = build(browser, add_source_match(browser, path))
    active = localized_server.app_context.managed_stateful.active_learning
    references, artifacts, files = retained(active), downloads(browser), saved_bytes(active.path)
    with closing(http.client.HTTPConnection(
            "127.0.0.1", browser.server.port, timeout=30)) as connection:
        connection.putrequest("POST", upload_form(page)["action"])
        connection.putheader("Cookie", browser.cookie)
        connection.putheader("Origin", browser.server.origin)
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(
            LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES + 1 if fault == "size" else 0))
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == (413 if fault == "size" else 415)
        page = response.read().decode()
    # Before reading the shared-route discriminator, the ordinary transport page is authoritative.
    assert text("en", "validation.report_file.format") not in page
    assert all(a is b for a, b in zip(references, retained(active), strict=True))
    assert downloads(browser) == artifacts and saved_bytes(active.path) == files


def test_unrelated_workspace_upload_keeps_generic_feedback(localized_server):
    import http.client

    from test_learning_corpus_web_uploads import _multipart
    from test_match_recording_recovery_web import operation_form

    browser = Browser(localized_server)
    create_collection(browser)
    form = operation_form(browser.page("/learning/current"), "import_match_workspace")
    body, content_type = _multipart(tuple(form["values"].items()),
        (("workspace_file", "ordinary.json", b'{"broken":', "application/json"),))
    with closing(http.client.HTTPConnection(
            "127.0.0.1", browser.server.port, timeout=30)) as connection:
        connection.request("POST", form["action"], body, headers={"Cookie": browser.cookie,
            "Origin": browser.server.origin, "Content-Type": content_type})
        response = connection.getresponse()
        assert response.status == 400
        page = response.read().decode()
    assert text("en", "validation.summary.heading") in page
    assert text("en", "validation.message.file_reselection") in page
    assert text("en", "validation.report_file.heading") not in page
