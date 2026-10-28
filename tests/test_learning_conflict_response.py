"""Complete HTTP rejection delivery when the ordinary Learning source is no longer safe."""

from collections import Counter
from html import unescape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_learning_direct_entry_web import (
    add_form,
    build,
    create_collection,
    saved_bytes,
    source_handle,
)
from test_match_recording_recovery_web import follow
from test_recorded_review_navigation import saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.learning_direct_entry as direct
import skatmind.app_web.learning_frontend as learning
import skatmind.app_web.server as web
import skatmind.learning_corpus_import as imports
from skatmind.app_web.stateful_localization import text
from skatmind.learning_corpus_catalog import build_learning_corpus_catalog_v1
from skatmind.learning_corpus_persistence import save_learning_corpus_catalog_v1
from skatmind.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def competing_catalog(active):
    original = active.corpus.store.document
    catalog = original.catalog
    competing = build_learning_corpus_catalog_persistence_document_v1(
        build_learning_corpus_catalog_v1(corpus_id=catalog.corpus_id,
            revision=catalog.revision + 1, match_snapshots=catalog.match_snapshots,
            current_matches=catalog.current_matches))
    assert save_learning_corpus_catalog_v1(active.path, competing,
        expected_content_fingerprint=original.content_fingerprint).status == "saved"
    return competing


def references(active):
    return (active.corpus.store, active.corpus.prepared_artifacts,
            active.corpus.tactical_prepared_artifacts,
            active.corpus.tactical_coaching_prepared_artifacts)


def observe(monkeypatch):
    calls = Counter()
    for module, name in (
        (direct, "import_workspace_bytes_into_unified_learning_v1"),
        (learning, "prepare_learning_corpus_artifacts_web_v1"),
        (learning, "select_current_learning_corpus_snapshot_web_v1"),
        (learning, "reload_learning_corpus_web_v1"),
        (imports, "save_learning_corpus_catalog_v1"),
        (imports, "publish_learning_corpus_match_snapshot_object_v1"),
    ):
        real = getattr(module, name)
        def counted(*args, _real=real, _name=name, **kwargs):
            calls[_name] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(module, name, counted)
    return calls


def assert_conflict(response, locale):
    status, headers, raw = response
    assert status == 409
    assert headers["content-type"] == "text/html; charset=utf-8"
    assert int(headers["content-length"]) == len(raw)
    page = raw.decode("utf-8")
    assert page.startswith("<!doctype html>") and page.rstrip().endswith("</html>")
    assert f'lang="{locale}"' in page
    assert text(locale, "validation.message.language_context_conflict") in unescape(page)
    assert "learning-result-primary" not in page and 'id="learning-sources"' not in page
    assert "data-operation-feedback " not in page
    assert not any(f["action"].startswith("/learning/") for f in Forms(page).forms)
    recovery, = [n for n in Hierarchy(page).nodes if n["tag"] == "a"
                 and n["text"] == text(locale, "language.open_task")]
    assert recovery["attrs"]["href"] == "/learning"
    return recovery["attrs"]["href"]


@pytest.mark.parametrize("locale", ("en", "de"))
@pytest.mark.parametrize("prepared", (False, True))
@pytest.mark.parametrize("source", ("catalog", "snapshot"))
@pytest.mark.parametrize("timing", ("before", "render", "delivery"))
def test_rejection_guard_returns_complete_localized_conflict_without_retry(
    localized_server, monkeypatch, locale, prepared, source, timing,
):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    if prepared:
        page = build(browser, page)
    follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language=locale))
    form = add_form(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    retained = references(active)
    home = localized_server.app_context.managed_home.root
    initial_files = saved_bytes(home)
    before_recording = path.read_bytes()
    generation = (active.corpus.generation, active.corpus.strategy_source_store.revision)
    calls = observe(monkeypatch)
    changed = []

    def change():
        assert not changed
        if source == "catalog":
            competing_catalog(active)
        else:
            next((active.path / "objects").rglob("*.json")).write_bytes(b"{}")
        changed.append(saved_bytes(home))

    if timing == "before":
        change()
    elif timing == "render":
        real = web.render_task_first_learning_v1
        def render(*args, **kwargs):
            content = real(*args, **kwargs)
            change()
            return content
        monkeypatch.setattr(web, "render_task_first_learning_v1", render)
    else:
        real = web.SkatMindAppWebRequestHandlerV1._send_text
        def deliver(handler, status, content, **kwargs):
            if 'id="task-first-learning"' in content:
                change()
            return real(handler, status, content, **kwargs)
        monkeypatch.setattr(web.SkatMindAppWebRequestHandlerV1, "_send_text", deliver)

    # A real emitted Add form with one deliberately stale capability; no mutation is authorized.
    response = browser.submit(form, source_handle=source_handle(path), learning_selection="0" * 64)
    recovery = assert_conflict(response, locale)
    assert len(changed) == 1 and initial_files != changed[0]
    assert saved_bytes(home) == changed[0] and path.read_bytes() == before_recording
    assert all(a is b for a, b in zip(retained, references(active), strict=True))
    assert generation == (active.corpus.generation, active.corpus.strategy_source_store.revision)
    assert not calls
    status, _, body = browser.request("GET", recovery)
    assert status == 200 and b"learning-result-primary" not in body
    assert not calls and saved_bytes(home) == changed[0]
    assert localized_server.app_context.managed_stateful.active_learning is active


@pytest.mark.parametrize("locale", ("en", "de"))
def test_owner_change_while_rendering_a_rejection_uses_source_independent_recovery(
    localized_server, monkeypatch, locale,
):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser, "Replacement collection")
    app = localized_server.app_context
    replacement = app.managed_stateful.active_learning
    create_collection(browser, "Original collection")
    page = browser.page("/learning/current")
    follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language=locale))
    form = add_form(browser)
    original = app.managed_stateful.active_learning
    files = saved_bytes(app.managed_home.root)
    calls = observe(monkeypatch)
    real = web.collection_scope
    def switched(context, target):
        assert target is original
        with app.lock:
            app.managed_stateful.active_learning = replacement
        return real(context, target)
    monkeypatch.setattr(web, "collection_scope", switched)
    recovery = assert_conflict(browser.submit(form, source_handle=source_handle(path),
                                              learning_selection="0" * 64), locale)
    assert recovery == "/learning" and app.managed_stateful.active_learning is replacement
    assert not calls and saved_bytes(app.managed_home.root) == files
    assert not replacement.corpus.store.match_snapshots
