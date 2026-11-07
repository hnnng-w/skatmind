"""Delivered native S7 routes and original language/download authority."""

import re
from html import unescape

import pytest
from test_automatic_historical_evidence import genuine_historical
from test_automatic_historical_learning import retain_fixture
from test_automatic_learning_ui import create, localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

__all__ = ["genuine_historical", "localized_server"]


def source_link(page):
    return re.search(r'href="(/review/saved/[0-9a-f]+/source/[0-9]+)"', page)[1]


def evidence_link(page):
    return re.search(r'href="(/review/saved/[0-9a-f]+/evidence/[0-9]+)"', page)[1]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_saved_discovery_download_reopen_delete_and_original_consent(
    localized_server, genuine_historical, locale, monkeypatch,
):
    import skatmind.app_web.execution as executor
    from skatmind.app_web.stateful_localization import text
    app = localized_server.app_context
    head = retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    monkeypatch.setattr(executor, "execute", lambda *a, **k: pytest.fail("Passive evaluation"))
    page = browser.page("/review/saved")
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                         language=locale))
    assert text(locale, "historical_learning.saved") in unescape(page)
    route = evidence_link(page)
    evidence = browser.page(route)
    assert "Alice" in evidence
    for kind, raw in (("request", genuine_historical[1].request_json_bytes),
                      ("result", genuine_historical[1].result_json_bytes)):
        response = browser.request("GET", route + "/" + kind + ".json")
        assert response[0] == 200 and response[2] == raw
    source = browser.page(source_link(page))
    assert 'class="entry-introduction"' not in source
    assert 'class="entry-actions"' not in source
    response = browser.submit(Forms(source).find("/review/reopen"))
    assert response[0] == 303 and response[1]["location"] == "/review"
    assert app.historical_reviews.head == head
    assert app.review_state.draft == genuine_historical[0]
    page = browser.page("/review/saved")
    source = browser.page(source_link(page))
    preview = follow(browser, browser.submit(Forms(source).find("/review/delete-preview")))
    original = app.historical_reviews.confirmation
    translated = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
        language="en" if locale == "de" else "de"))
    assert app.historical_reviews.confirmation is original
    confirmation = Forms(translated).find("/review/delete-confirm")
    assert "confirm_delete" not in confirmation["values"]
    assert browser.submit(confirmation, confirm_delete="on")[0] == 303
    assert browser.request("GET", route + "/result.json")[0] == 409
    historical = browser.page("/review/saved")
    assert "/source/" not in historical
    assert "/evidence/" in historical


def test_automatic_historical_download_and_stale_final_delivery(
    localized_server, genuine_historical, monkeypatch,
):
    from dataclasses import replace

    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    app = localized_server.app_context
    retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    page = create(browser)
    assert "Session coverage and comparisons" not in page
    assert "Historical game reviews" in page
    route = re.search(r'href="(/learning/automatic/[0-9a-f]+/historical/evidence/[0-9]+)"', page)[1]
    assert browser.request("GET", route + "/result.json")[2] == (
        genuine_historical[1].result_json_bytes)
    original = Handler._send_bytes
    fired = False
    def changed(handler, status, content, **kwargs):
        nonlocal fired
        if handler.path == route + "/result.json" and status == 200 and not fired:
            fired = True
            store = app.automatic_match_learning.store
            before = store.snapshot().manifest
            store.update_manifest(replace(before, revision=before.revision + 1,
                                          historical_heads=()),
                                  expected_manifest=before.fingerprint)
        return original(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", changed)
    response = browser.request("GET", route + "/result.json")
    assert response[0] == 409 and b"</html>" in response[2]


def test_original_saved_entry_language_rejects_head_change(localized_server, genuine_historical):
    from dataclasses import replace

    from skatmind.app_web.saved_match_analyses import archive_store
    app = localized_server.app_context
    retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    page = browser.page("/review/saved")
    language = Forms(page).find("/actions/profile/language")
    before_profile = app.frontend_profile.generation
    store = archive_store(app)
    before = store.snapshot().manifest
    store.update_manifest(replace(before, revision=before.revision + 1, historical_heads=()),
                          expected_manifest=before.fingerprint)
    response = browser.submit(language, language="de")
    assert response[0] == 409
    assert app.frontend_profile.generation == before_profile


def test_passive_saved_access_reuses_exact_byte_admission_and_old_process_urls_reject(
    localized_server, genuine_historical, monkeypatch,
):
    from skatmind.app_web.workflow_operations import start_review_v1
    app = localized_server.app_context
    retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    page = browser.page("/review/saved")
    route = evidence_link(page)
    browser.page(route)
    process_page = browser.page("/review")
    download = re.search(r'href="(/review/execution/[0-9a-f]+/result.json)"', process_page)[1]
    for store in (app.automatic_match_learning.store, app.saved_match_analyses.store):
        monkeypatch.setattr(store, "_admission", lambda *a, **k: pytest.fail("Repeated admission"))
    assert browser.request("GET", route + "/result.json")[2] == (
        genuine_historical[1].result_json_bytes)
    assert browser.request("GET", download)[2] == genuine_historical[1].result_json_bytes
    browser.page("/review/saved")
    start_review_v1(app, expected_revision=app.review_state.revision)
    response = browser.request("GET", download)
    assert response[0] == 409


def test_native_download_rechecks_original_owner_after_unlocked_archive_read(
    localized_server, genuine_historical, monkeypatch,
):
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    from skatmind.app_web.workflow_operations import start_review_v1
    app = localized_server.app_context
    retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    page = browser.page("/review")
    route = re.search(r'href="(/review/execution/[0-9a-f]+/result.json)"', page)[1]
    store = app.saved_match_analyses.store
    snapshot, send = store._snapshot_for_delivery, Handler._send_bytes
    fired = False
    def changed(*args, **kwargs):
        nonlocal fired
        result = snapshot(*args, **kwargs)
        if not fired:
            fired = True
            start_review_v1(app, expected_revision=app.review_state.revision)
        return result
    def at_headers(handler, status, content, **kwargs):
        if handler.path == route and status == 200:
            monkeypatch.setattr(store, "_snapshot_for_delivery", changed)
        return send(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", at_headers)
    assert browser.request("GET", route)[0] == 409
    assert fired and app.review_state.latest_successful_result is None


@pytest.mark.parametrize("action", ("reopen", "delete-preview", "delete-confirm", "retry-saving"))
def test_original_post_receipt_rejects_supersession_at_headers(
    localized_server, genuine_historical, monkeypatch, action,
):
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    from skatmind.app_web.workflow_operations import start_review_v1
    app = localized_server.app_context
    if action == "retry-saving":
        store = archive_store(app, initialize=True)
        with monkeypatch.context() as patch:
            def failed(*args, **kwargs):
                raise OSError("Controlled save failure before manifest commit")
            patch.setattr(store, "update_manifest", failed)
            retain_fixture(app, genuine_historical, expect_saved=False)
    else:
        retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    values = {}
    if action == "retry-saving":
        form = Forms(browser.page("/review")).find("/review/retry-saving")
    else:
        page = browser.page("/review/saved")
        source = browser.page(source_link(page))
        if action == "delete-confirm":
            source = follow(browser, browser.submit(Forms(source).find("/review/delete-preview")))
            values = {"confirm_delete": "on"}
        form = Forms(source).find("/review/" + action)
    send = Handler._send_bytes
    fired = False
    def at_headers(handler, status, content, **kwargs):
        nonlocal fired
        if handler.path == form["action"] and status == 303 and not fired:
            fired = True
            if action == "delete-preview":
                app.historical_reviews.confirmation = None
            elif action == "delete-confirm":
                app.automatic_match_learning.attempt = object()
            else:
                start_review_v1(app, expected_revision=app.review_state.revision)
        return send(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", at_headers)
    response = browser.submit(form, **values)
    assert response[0] == 409 and b"</html>" in response[2]
    assert fired
    if action == "delete-confirm":
        assert archive_store(app).snapshot().manifest.historical_heads == ()
    if action == "retry-saving":
        assert len(archive_store(app).snapshot().manifest.historical_heads) == 1


def test_ordinary_imports_are_independent_and_reset_keeps_saved_sources(localized_server):
    from test_analysis_download_details import import_example

    from skatmind.app_web.saved_match_analyses import archive_store
    app = localized_server.app_context
    browser = Browser(localized_server)
    identities = []
    for _ in range(2):
        page = follow(browser, import_example(
            browser, "review", "historical_grand_normal_completion.json"))
        page = follow(browser, browser.submit(Forms(page).find("/actions/review/run-imported")))
        assert app.historical_reviews.notice[1] == "saved"
        identities.append(app.historical_reviews.head.source)
    assert identities[0] != identities[1]
    store = archive_store(app)
    before = store.snapshot().manifest
    assert len(before.historical_heads) == 2
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/reset"),
                                         confirm_reset="on"))
    assert Forms(page).find("/actions/review/start")
    assert app.review_state.imported_request is None
    assert store.snapshot().manifest == before
    create(browser)
    assert app.automatic_match_learning._installed.bundle.historical_sources == ()
    assert all(row.reason == "ambiguous"
               for row in app.automatic_match_learning._installed.generation.recipe.exclusions)
