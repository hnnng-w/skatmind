"""Delivered native S7 routes and original language/download authority."""

import re
from html import unescape

import pytest
from test_automatic_historical_evidence import genuine_historical, legacy_candidate
from test_automatic_historical_learning import retain_fixture
from test_automatic_learning_ui import create, localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

__all__ = ["genuine_historical", "legacy_candidate", "localized_server"]


def source_link(page):
    return re.search(r'href="(/review/saved/[0-9a-f]+/source/[0-9]+)"', page)[1]


def evidence_link(page):
    return re.search(r'href="(/review/saved/[0-9a-f]+/evidence/[0-9]+)"', page)[1]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_superseded_service_recovers_at_saved_get_and_post_entry(localized_server, locale):
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1
    from skatmind.app_web.stateful_localization import text

    browser = Browser(localized_server)
    app = localized_server.app_context
    headers = {"Accept-Language": locale}
    assert browser.request("GET", "/review/saved", headers=headers)[0] == 200
    controller = app.automatic_learning_ui
    token, = controller.views
    old = controller.service
    new = AutomaticMatchLearningServiceV1.open(app)
    assert new._owner() and not old._owner()
    for method, route, values in (("GET", "/review/saved", None),
            ("POST", "/review/reopen", {"view": token, "source": "0"})):
        status, _, raw = browser.request(method, route, values, headers=headers)
        assert status == 409
        assert text(locale, "historical_learning.conflict") in unescape(raw.decode())
        assert b'href="/review/saved"' in raw
        assert controller.service is old and app.automatic_match_learning is new
    assert not (app.managed_home.root / "automatic-learning").exists()


def test_source_caption_projection_reads_each_exact_revision_once_and_keeps_deleted_history(
    localized_server, genuine_historical, monkeypatch,
):
    from collections import Counter
    from dataclasses import replace

    from learning_archive_fixture_helpers import measure_work, publish_fresh_archive
    from test_automatic_match_learning_evidence import forbid_execution

    from skatmind.app_web.automatic_learning_controller import automatic_controller
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_historical_evidence import build_historical_capture_candidate
    from skatmind.automatic_learning_contracts import HistoricalReviewHeadV1

    app = localized_server.app_context
    draft, execution, native = genuine_historical
    candidates = tuple(build_historical_capture_candidate("same-source", revision,
        execution, native, draft=draft) for revision in (0, 1))
    store = archive_store(app, initialize=True)
    manifest = publish_fresh_archive(store, store.snapshot(), candidates)
    current = candidates[-1]
    head = HistoricalReviewHeadV1(source=current.source.source_version.source,
        source_version_id=current.source.source_version.identity,
        evidence_id=current.evidence.identity)
    assert store.update_manifest(replace(manifest, revision=2, historical_heads=(head,)),
                                 expected_manifest=manifest.fingerprint).status == "saved"
    browser = Browser(localized_server)
    browser.page("/review/saved")  # Seed this owner's exact bounded admission.
    service = automatic_controller(app).service
    original = service.read_delivery_historical_sources
    projections = []
    def project(*args):
        reads = Counter()
        read = service.store.read_object
        def reading(reference):
            reads[reference] += 1
            return read(reference)
        with monkeypatch.context() as patch:
            patch.setattr(service.store, "read_object", reading)
            result = original(*args)
        projections.append(reads)
        return result
    monkeypatch.setattr(service, "read_delivery_historical_sources", project)
    forbid_execution(monkeypatch)
    with monkeypatch.context() as patch:
        work = measure_work(patch, store)
        page = browser.page("/review/saved")
        assert work["retained_results_loaded"] == work["admissions"] == 0
    assert projections == [Counter({candidate.source.object_ref: 1 for candidate in candidates})]
    assert "revision 0" in page and "revision 1" in page
    assert len(re.findall(r'href="/review/saved/[0-9a-f]+/source/[0-9]+"', page)) == 1
    routes = re.findall(r'href="(/review/saved/[0-9a-f]+/evidence/[0-9]+)"', page)
    assert [route.rsplit("/", 1)[-1] for route in routes] == ["0", "1"]
    for route in routes:
        assert browser.request("GET", route + "/result.json")[2] == execution.result_json_bytes
    source = browser.page(source_link(page))
    preview = follow(browser, browser.submit(Forms(source).find("/review/delete-preview")))
    assert browser.submit(Forms(preview).find("/review/delete-confirm"),
                          confirm_delete="on")[0] == 303
    page = browser.page("/review/saved")
    assert "/source/" not in page and "revision 0" in page and "revision 1" in page


def test_pre325_source_reopens_with_original_downloads(
    localized_server, genuine_historical, legacy_candidate, monkeypatch,
):
    from dataclasses import replace

    from test_automatic_match_evidence import commit_candidate
    from test_automatic_match_learning_evidence import forbid_execution
    from test_automatic_session_review_corrections import archive_bytes

    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_learning_contracts import HistoricalReviewHeadV1

    app = localized_server.app_context
    store = archive_store(app, initialize=True)
    assert commit_candidate(store, legacy_candidate).status == "saved"
    before = store.snapshot().manifest
    head = HistoricalReviewHeadV1(source=legacy_candidate.source.source_version.source,
        source_version_id=legacy_candidate.source.source_version.identity,
        evidence_id=legacy_candidate.evidence.identity)
    assert store.update_manifest(replace(before, revision=before.revision + 1,
        historical_heads=(head,)), expected_manifest=before.fingerprint).status == "saved"
    original = archive_bytes(store)
    forbid_execution(monkeypatch)
    browser = Browser(localized_server)
    page = browser.page("/review/saved")
    source = browser.page(source_link(page))
    response = browser.submit(Forms(source).find("/review/reopen"))
    assert response[0] == 303 and response[1]["location"] == "/review"
    assert app.historical_reviews.head == head
    assert app.review_state.draft == genuine_historical[0]
    assert app.review_state.latest_successful_options == genuine_historical[1].options
    route = evidence_link(page)
    for kind in ("request", "result"):
        status, _, raw = browser.request("GET", route + "/" + kind + ".json")
        assert status == 200 and raw == getattr(genuine_historical[1], kind + "_json_bytes")
    assert archive_bytes(store) == original


def test_native_ordinary_guided_review_is_saved_and_reopened(localized_server, monkeypatch):
    from dataclasses import replace

    from test_automatic_match_learning_evidence import forbid_execution
    from test_guided_historical_review_form import _completed_example_draft

    from skatmind.app_web.automatic_historical_inventory import capture_historical_inventory
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_learning_codec import decode_json

    browser = Browser(localized_server)
    page = follow(browser, browser.submit(Forms(browser.page("/review")).find(
        "/actions/review/start")))
    app = localized_server.app_context
    fresh = app.review_state.draft
    assert fresh.options.immediate_review
    app.review_state = replace(app.review_state, draft=replace(_completed_example_draft(),
        options=fresh.options, analysis_form_values=fresh.analysis_form_values))
    page = browser.page("/review")
    response = browser.submit(Forms(page).find("/actions/review/update-options"),
        analysis_effort="quick", immediate_sample_count="7", immediate_base_random_seed="invalid")
    assert response[0] == 400 and app.historical_reviews.head is None
    page = response[2].decode()
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        values = Forms(page).find("/actions/review/update-options")["values"]
        assert values["settings_mode"] == "ordinary" and values["analysis_effort"] == "quick"
        assert values["immediate_sample_count"] == "7"
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/update-options"),
        immediate_base_random_seed="11"))
    draft = app.review_state.draft
    assert draft.analysis_form_values.singular("immediate_sample_count") == "7"
    assert draft.options.immediate_review and draft.options.immediate_sample_count == 25
    response = browser.submit(Forms(page).find("/actions/review/run-guided"))
    assert response[0] == 303
    assert app.historical_reviews.notice[1] == "saved"
    assert app.historical_reviews.pending is None
    head = app.historical_reviews.head
    assert head is not None
    state = app.review_state
    assert state.draft is draft  # Saving does not erase the process-local inactive controls.
    assert state.latest_successful_options.workflow_options["immediate_sample_count"] == 25
    assert state.latest_successful_options.workflow_options["immediate_base_random_seed"] == 11
    store = archive_store(app)
    assert head.evidence_id in store.snapshot().available_evidence_ids
    inventory = capture_historical_inventory(store, store.snapshot(), ())
    assert inventory.sources == () and inventory.rows[0].status == "ineligible"
    retained = store.read_evidence(head.evidence_id)
    source_wire = decode_json(store.read_object(retained.source.record.object_ref).payload)["draft"]
    envelope = decode_json(store.read_object(retained.entry.envelope).payload)
    for wire in (source_wire, envelope["guided_draft"]):
        assert [key for key, _ in wire["value"]] == [
            "step", "players", "skat", "declaration", "discarded_cards", "plays", "options"]
    assert retained.guided_draft == replace(draft, analysis_form_values=None)
    assert retained.execution.options == state.latest_successful_options
    forbid_execution(monkeypatch)
    page = browser.page("/review/saved")
    route = evidence_link(page)
    for kind in ("request", "result"):
        status, _, raw = browser.request("GET", route + "/" + kind + ".json")
        assert status == 200 and raw == getattr(state, kind + "_json_bytes")
    source = browser.page(source_link(page))
    assert browser.submit(Forms(source).find("/review/reopen"))[0] == 303
    assert app.historical_reviews.head == head
    assert app.review_state.draft == retained.guided_draft
    assert app.review_state.latest_successful_options == state.latest_successful_options
    assert app.review_state.request_json_bytes == state.request_json_bytes
    assert app.review_state.result_json_bytes == state.result_json_bytes


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


def test_old_automatic_historical_link_is_withheld_and_saved_download_stays_guarded(
    localized_server, genuine_historical, monkeypatch,
):
    from dataclasses import replace

    from test_automatic_historical_learning import prepare_legacy_generation

    from skatmind.app_web.automatic_learning_controller import automatic_controller
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    app = localized_server.app_context
    retain_fixture(app, genuine_historical)
    browser = Browser(localized_server)
    controller = automatic_controller(app)
    prepare_legacy_generation(controller.service, monkeypatch)
    old_view = controller.capture()
    assert old_view.binding.result.status == "excluded"
    old_route = old_view.base + "/historical/evidence/0"
    assert browser.request("GET", old_route + "/result.json")[0] == 409
    page = create(browser)  # Explicit Update installs only eligible recording contributions.
    assert "Session coverage and comparisons" not in page
    assert "Historical game reviews" in page
    assert re.search(r'/historical/evidence/[0-9]+', page) is None
    route = evidence_link(browser.page("/review/saved"))
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
    assert all(row.reason == "unsupported"
               for row in app.automatic_match_learning._installed.generation.recipe.exclusions)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_legacy_download_conflict_after_cooperating_context_deletes_saved_review(
    localized_server, monkeypatch, locale,
):
    from test_automatic_match_learning_evidence import forbid_execution
    from test_automatic_session_review_corrections import archive_bytes
    from test_guided_historical_review_form import _completed_example_draft

    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.historical_form import update_historical_options_v1
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.app_web.server import serve_app_web_in_thread_v1, start_app_web_server_v1
    from skatmind.app_web.stateful_localization import text
    from skatmind.app_web.workflow_operations import run_guided_review_v1

    app = localized_server.app_context
    draft = update_historical_options_v1(_completed_example_draft())
    app.review_state = app.review_state.mutate(expected_revision=0, draft=draft)
    run_guided_review_v1(app, expected_revision=app.review_state.revision)
    state, notice = app.review_state, app.historical_reviews.notice
    assert notice[1] == "saved"
    browser = Browser(localized_server)
    headers = {"Accept-Language": locale}
    page = browser.request("GET", "/review", headers=headers)[2].decode()
    tokenized = re.search(r'href="(/review/execution/[0-9a-f]+/result.json)"', page)[1]
    for kind in ("request", "result"):
        status, response_headers, raw = browser.request(
            "GET", f"/downloads/review/{kind}.json", headers=headers)
        assert status == 200 and raw == getattr(state, kind + "_json_bytes")
        assert response_headers["content-disposition"] == (
            f'attachment; filename="skatmind-review-{kind}.json"')

    forbid_execution(monkeypatch)
    other = start_app_web_server_v1(AppWebContextV1.create(app.managed_home),
        port=0, token="localization-test-token")
    thread = serve_app_web_in_thread_v1(other)
    try:
        cooperating = Browser(other)
        page = cooperating.page("/review/saved")
        source = cooperating.page(source_link(page))
        preview = follow(cooperating, cooperating.submit(
            Forms(source).find("/review/delete-preview")))
        response = cooperating.submit(Forms(preview).find("/review/delete-confirm"),
                                      confirm_delete="on")
        assert response[0] == 303
    finally:
        other.shutdown()
        other.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()

    store = archive_store(app)
    assert store.snapshot().manifest.historical_heads == ()
    before = archive_bytes(store)
    def forbidden(*args, **kwargs):
        pytest.fail("Conflict delivery must not write the archive")
    monkeypatch.setattr("skatmind.automatic_learning_io.write_temporary", forbidden)
    control = browser.request("GET", tokenized, headers=headers)
    assert control[0] == 409
    results = [browser.request("GET", f"/downloads/review/{kind}.json", headers=headers)
               for kind in ("request", "result")]
    print({"locale": locale, "legacy_statuses": [row[0] for row in results],
           "tokenized_status": control[0]})
    assert app.review_state is state and app.historical_reviews.notice is notice
    assert archive_bytes(store) == before
    for status, _headers, body in results:
        assert status == 409 and b"</html>" in body
        assert text(locale, "historical_learning.conflict") in unescape(body.decode())
