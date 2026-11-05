"""S5 native HTTP boundaries; disposable genuine saved Matches, no fixture analysis."""

import re
from html import unescape

import pytest
from test_automatic_match_learning import save
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms


@pytest.fixture
def localized_server(tmp_path, monkeypatch):
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    original = Handler._stateful_get
    failures = []
    def checked(handler, path):
        try:
            return original(handler, path)
        except Exception as error:
            failures.append(error)
            raise
    monkeypatch.setattr(Handler, "_stateful_get", checked)
    yield from _localized_server.__wrapped__(tmp_path)
    assert not failures, repr(failures)


UPDATE = "/learning/automatic/update"
PREVIEW = "/learning/automatic/cleanup-preview"
EXCLUDE = "/learning/automatic/exclude-preview"


def create(browser):
    return follow(browser, browser.submit(Forms(browser.page("/learning")).find(UPDATE)))


def test_native_entry_explicit_update_and_passive_owner(localized_server, monkeypatch):
    import skatmind.app_web.automatic_match_learning as service

    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    page = browser.page("/learning")
    assert UPDATE in page
    assert 'A learning collection holds saved Match versions you choose' not in page
    assert page.index(UPDATE) < page.index('/learning/create')
    assert not (app.managed_home.root / "automatic-learning").exists()
    page = create(browser)
    assert 'id="learning-result"' in page and 'autofocus' in page
    owner, installed = app.automatic_match_learning, app.automatic_match_learning._installed
    before = {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")}
    monkeypatch.setattr(service, "build_automatic_match_bundle",
                        lambda *a, **kw: pytest.fail("Passive/reused preparation"))
    route = Forms(page).find("/actions/profile/language")["values"]["return_to"]
    browser.page(route)
    browser.page("/learning")
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert "unchanged" in unescape(page).lower()
    assert app.automatic_match_learning is owner and owner._installed is installed
    assert app.managed_stateful.active_learning is None
    assert {p: p.read_bytes() for p in before} == before


def test_ten_generation_downloads_and_final_delivery(localized_server, monkeypatch):
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler

    app = localized_server.app_context
    path, _ = save(app)
    browser = Browser(localized_server)
    page = create(browser)
    routes = re.findall(r'href="(/learning/automatic/[^\"]+/downloads/[^\"]+)"', page)
    assert len(routes) == 10
    expected = {v.kind.replace("_", "-") + ".json": v.content
                for v in app.automatic_match_learning._installed.bundle.downloads}
    for route in routes:
        assert browser.request("GET", route)[2] == expected[route.rsplit("/", 1)[1]]
    original = Handler._send_bytes
    def changed(handler, status, content, **kwargs):
        if handler.path == routes[0] and status == 200:
            path.unlink()
        return original(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", changed)
    response = browser.request("GET", routes[0])
    assert response[0] == 409 and b'</html>' in response[2]
    assert b'Create Learning review' not in response[2]


def test_cleanup_preview_does_not_invalidate_itself_and_reader_requires_new_consent(
    localized_server,
):
    from automatic_learning_helpers import source_fixture

    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    create(browser)
    store = app.automatic_match_learning.store
    _record, first = source_fixture(content="first consent fixture")
    store.publish_object(first)  # Storage-only orphan; this preview has a real effect.
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(Forms(page).find(PREVIEW)))
    confirmation = Forms(preview).find("/learning/automatic/confirm")
    assert "confirm_apply" not in confirmation["values"]
    response = browser.submit(confirmation, confirm_apply="on")
    assert response[0] == 303, response[2].decode()
    _record, second = source_fixture(content="second consent fixture")
    store.publish_object(second)
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(Forms(page).find(PREVIEW)))
    confirmation = Forms(preview).find("/learning/automatic/confirm")
    app.automatic_match_learning.consume(lambda bundle: bundle.coverage)
    response = browser.submit(confirmation, confirm_apply="on")
    assert response[0] == 409 and b'</html>' in response[2]
    assert b'checked' not in response[2]
    assert store.read_object(second.reference) == second


def route_of(page):
    return Forms(page).find("/actions/profile/language")["values"]["return_to"]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_exclusion_reinclusion_and_preview_language_preserve_exact_consent(
    localized_server, locale,
):
    from skatmind.app_web.stateful_localization import text
    app = localized_server.app_context
    path, _ = save(app)
    original = path.read_bytes()
    browser = Browser(localized_server)
    page = create(browser)
    old = route_of(page)
    preview = follow(browser, browser.submit(Forms(page).find(EXCLUDE)))
    token = Forms(preview).find("/learning/automatic/confirm")["values"]["confirmation"]
    preview = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
                                            language=locale))
    confirmation = Forms(preview).find("/learning/automatic/confirm")
    assert confirmation["values"]["confirmation"] == token
    assert "confirm_apply" not in confirmation["values"]
    page = follow(browser, browser.submit(confirmation, confirm_apply="on"))
    assert text(locale, "automatic.state.excluded") in unescape(page)
    assert browser.request("GET", old)[0] == 409
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert app.automatic_match_learning._installed.bundle.sources == ()
    preview = follow(browser, browser.submit(Forms(page).find(EXCLUDE)))
    page = follow(browser, browser.submit(Forms(preview).find("/learning/automatic/confirm"),
                                          confirm_apply="on"))
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert len(app.automatic_match_learning._installed.bundle.sources) == 1
    assert path.read_bytes() == original


@pytest.mark.parametrize("change", ("source", "delete", "owner", "attempt", "installed"))
@pytest.mark.parametrize("stage", ("projection", "headers"))
def test_html_authorizes_exact_boundary(localized_server, monkeypatch, change, stage):
    from dataclasses import replace

    from test_automatic_match_learning import rewrite

    import skatmind.app_web.automatic_learning_http as http
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    app = localized_server.app_context
    path, document = save(app)
    browser = Browser(localized_server)
    route = route_of(create(browser))
    fired = False
    def mutate():
        nonlocal fired
        if fired:
            return
        fired = True
        service = app.automatic_match_learning
        if change == "source":
            rewrite(path, document)
        elif change == "delete":
            path.unlink()
        elif change == "owner":
            app.automatic_match_learning = object()
        elif change == "attempt":
            service.attempt = object()
        else:
            service._installed = replace(service._installed)
    if stage == "projection":
        original = http.render_review
        def render(*args, **kwargs):
            value = original(*args, **kwargs)
            mutate()
            return value
        monkeypatch.setattr(http, "render_review", render)
    else:
        original = Handler._send_bytes
        def send(handler, status, content, **kwargs):
            if handler.path == route:
                mutate()
            return original(handler, status, content, **kwargs)
        monkeypatch.setattr(Handler, "_send_bytes", send)
    response = browser.request("GET", route)
    assert fired and response[0] == 409
    assert b'</html>' in response[2] and b'id="learning-result"' not in response[2]


def test_corrected_prior_is_explicit_deleted_aggregate_hidden_and_restart_needs_update(
    localized_server, monkeypatch,
):
    from test_automatic_match_learning import rewrite

    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.stateful_localization import text
    app = localized_server.app_context
    path, document = save(app)
    browser = Browser(localized_server)
    page = create(browser)
    original_route = route_of(page)
    rewrite(path, document)
    page = browser.page("/learning/automatic")
    assert text("en", "automatic.state.outdated") in unescape(page)
    assert browser.request("GET", original_route)[0] == 409
    prior = re.search(r'href="(/learning/automatic/[0-9a-f]+/all)"', page)[1]
    assert text("en", "automatic.state.outdated") in unescape(browser.page(prior))
    path.unlink()
    assert browser.request("GET", prior)[0] == 409
    page = browser.page("/learning/automatic")
    assert text("en", "automatic.state.deleted") in unescape(page)
    assert 'id="learning-result"' not in page
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    bytes_before = tuple(v.content
                         for v in app.automatic_match_learning._installed.bundle.downloads)
    localized_server.app_context = AppWebContextV1.create(app.managed_home)
    page = browser.page("/learning/automatic")
    assert text("en", "automatic.state.reconstruction_needed") in unescape(page)
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert text("en", "feedback.automatic_rebuilt") in unescape(page)
    assert tuple(v.content for v in localized_server.app_context.automatic_match_learning.
                 _installed.bundle.downloads) == bytes_before


def test_invalid_top_level_is_specific_and_never_reset(localized_server):
    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    page = create(browser)
    path = app.automatic_match_learning.store.root / "manifest.json"
    path.write_bytes(b'{}')  # Controlled malformed authority, not an individual object.
    for response in (browser.request("GET", "/learning/automatic"),
                     browser.submit(Forms(page).find(UPDATE))):
        assert response[0] == 409 and b'known-valid copy' in response[2]
        assert b'</html>' in response[2]
    assert path.read_bytes() == b'{}'


def test_native_language_and_reused_receipt_are_one_use(localized_server, monkeypatch):
    import skatmind.app_web.automatic_match_learning as module
    import skatmind.automatic_learning_io as io
    from skatmind.app_web.stateful_localization import text
    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    page = create(browser)
    route = route_of(page)
    assert text("en", "feedback.automatic_prepared") in unescape(page)
    assert text("en", "feedback.automatic_prepared") not in unescape(browser.page(route))
    monkeypatch.setattr(io, "write_temporary", lambda *a, **kw: pytest.fail("Archive write"))
    monkeypatch.setattr(module, "build_automatic_match_bundle",
                        lambda *a, **kw: pytest.fail("Passive preparation"))
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        assert route_of(page) == route and f'lang="{locale}"' in page
    stale_language = Forms(page).find("/actions/profile/language")
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert text("en", "feedback.automatic_reused") in unescape(page)
    assert browser.submit(stale_language, language="de")[0] == 409


@pytest.mark.parametrize("defect", ("extra", "duplicate", "body", "origin", "consent"))
def test_bounded_rejected_forms_deliver_complete_native_response(localized_server, defect):
    browser = Browser(localized_server)
    page = create(browser)
    values = Forms(page).find(UPDATE)["values"]
    if defect == "consent":
        from automatic_learning_helpers import source_fixture
        _record, orphan = source_fixture()
        localized_server.app_context.automatic_match_learning.store.publish_object(orphan)
        page = browser.page("/learning/automatic")
        preview = follow(browser, browser.submit(Forms(page).find(PREVIEW)))
        response = browser.submit(Forms(preview).find("/learning/automatic/confirm"))
    else:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if defect == "extra":
            values["unexpected"] = "value"
        elif defect == "duplicate":
            values["view"] = [values["view"], values["view"]]
        elif defect == "body":
            values["extra"] = "x" * 4096
        else:
            headers["Origin"] = "null"
        response = browser.request("POST", UPDATE, values, headers=headers)
    assert response[0] in (400, 403, 409, 413)
    assert b'</html>' in response[2]


def test_incomplete_scan_and_duplicate_owner_are_not_deletion(localized_server, monkeypatch):
    import skatmind.app_web.automatic_match_inventory as inventory
    app = localized_server.app_context
    path, _ = save(app)
    browser = Browser(localized_server)
    create(browser)
    before = app.automatic_match_learning.store.snapshot().manifest
    path.with_name("duplicate.json").write_bytes(path.read_bytes())
    with monkeypatch.context() as patch:
        patch.setattr(inventory, "MANAGED_ITEM_MAX_CANDIDATES", 1)
        response = browser.request("GET", "/learning/automatic")
        assert response[0] == 409
        assert b'no longer present' not in response[2]
        assert app.automatic_match_learning.store.snapshot().manifest == before
    page = browser.page("/learning/automatic")
    assert 'Multiple files claim this identity' in page
    assert '<details open ' in page
    page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert app.automatic_match_learning._installed.bundle.sources == ()
    assert 'Multiple files claim this identity' in page


def test_late_reuse_supersession_has_no_success_receipt(localized_server, monkeypatch):
    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    page = create(browser)
    service = app.automatic_match_learning
    original = service.update
    def superseded():
        earlier = original()
        assert original().status == "reused"
        return earlier
    monkeypatch.setattr(service, "update", superseded)
    response = browser.submit(Forms(page).find(UPDATE))
    assert response[0] == 409
    assert b'exact Learning review was reused' not in response[2]
    assert service.inspect().status == "current"


def test_independent_manual_owner_copies_and_downloads_survive_ui(localized_server):
    from skatmind.app_web.learning_frontend import UnifiedLearningContextV1
    from skatmind.corpus_web.context import LearningCorpusWebContextV1
    from skatmind.corpus_web.preparation import prepare_learning_corpus_artifacts_web_v1
    from skatmind.learning_corpus_import import import_match_workspace_file_into_learning_corpus_v1
    from skatmind.learning_corpus_persistence import (
        initialize_learning_corpus_directory_v1,
        load_learning_corpus_directory_v1,
    )
    app = localized_server.app_context
    path, _ = save(app)
    root = app.managed_home.category("corpora").path / "independent"
    initialize_learning_corpus_directory_v1(root, corpus_id="independent")
    before = load_learning_corpus_directory_v1(root).document
    assert import_match_workspace_file_into_learning_corpus_v1(root, path,
        expected_catalog_revision=before.catalog.revision,
        expected_catalog_content_fingerprint=before.content_fingerprint,
        selection_mode="keep_current", same_revision_resolution="reject").status == "applied"
    corpus = LearningCorpusWebContextV1.open(root)
    prepare_learning_corpus_artifacts_web_v1(corpus, dataset_id="manual", known_player_seed=0,
        unseen_player_seed=0, train_weight=70, validation_weight=15, test_weight=15)
    active = UnifiedLearningContextV1(category_root=root.parent, path=root,
        handle="a" * 64, corpus=corpus)
    app.managed_stateful.active_learning = active
    manual = {p: p.read_bytes() for p in root.rglob("*.json")}
    prepared, store, sources = corpus.prepared_artifacts, corpus.store, corpus.strategy_source_store
    browser = Browser(localized_server)
    native = browser.request("GET", "/learning/downloads/player-catalog.json")
    page = create(browser)
    path.unlink()
    page = browser.page("/learning/automatic")
    follow(browser, browser.submit(Forms(page).find(UPDATE)))
    after = browser.request("GET", "/learning/downloads/player-catalog.json")
    assert after[0] == native[0] == 200 and after[2] == native[2]
    assert corpus.prepared_artifacts is prepared and corpus.store is store
    assert corpus.strategy_source_store is sources
    assert app.managed_stateful.active_learning is active
    assert all(p.read_bytes() == raw for p, raw in manual.items())
    (app.automatic_match_learning.store.root / "manifest.json").write_bytes(b'{}')
    page = browser.page("/learning/collections")
    assert '/learning/open' in page and '/learning/create' in page


def test_cleanup_cancel_and_language_do_not_regenerate_preview(localized_server, monkeypatch):
    from automatic_learning_helpers import source_fixture
    app = localized_server.app_context
    browser = Browser(localized_server)
    page = create(browser)
    store = app.automatic_match_learning.store
    _record, orphan = source_fixture()  # Storage-only owned orphan, not executed evidence.
    store.publish_object(orphan)
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(Forms(page).find(PREVIEW)))
    exact = app.automatic_learning_ui.confirmation.cleanup
    assert len(exact.files) == 1
    monkeypatch.setattr(store, "preview_cleanup", lambda **kw: pytest.fail("Preview regenerated"))
    for locale in ("de", "en"):
        preview = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
                                                  language=locale))
        assert app.automatic_learning_ui.confirmation.cleanup is exact
    response = browser.submit(Forms(preview).find("/learning/automatic/confirm"),
                              confirm_apply="on")
    assert response[0] == 303
    assert not (store.root / orphan.area / (orphan.reference.fingerprint + ".json")).exists()
