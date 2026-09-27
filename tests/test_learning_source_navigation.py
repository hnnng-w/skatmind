"""R13g: ordinary source controls and existing no-source recovery, using real files."""

from collections import Counter

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_learning_direct_entry_web import create_collection, downloads, saved_bytes, source_handle
from test_learning_outcome_navigation import match_target, node
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_review_navigation import external_pass, saved_partial_match
from test_recording_entry_settings_navigation import assert_shell
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.learning_frontend as learning
import skatmind.learning_corpus_import as corpus_import
from skatmind.app_web.learning_direct_entry import LEARNING_ENTRY_FIELDS
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as t

ADD = "/learning/add-recorded-match"
REFRESH = "/learning/recorded-matches/refresh"
CAPTIONS = {
    "de": ("Match erfassen oder öffnen", "Gespeichertes Match",
           "Match zur Sammlung hinzufügen", "Gespeicherte Matches aktualisieren"),
    "en": ("Record or open a Match", "Saved Match", "Add Match to collection",
           "Refresh saved Matches"),
}


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def source_body(page):
    return page.split('<div id="learning-recorded-matches" tabindex="-1">', 1)[1].split(
        '</section></div>', 1)[0]


def assert_controls(page, locale, *, recovery):
    body = source_body(page)
    open_match, label, add, refresh = CAPTIONS[locale]
    paragraph = f'<p><a href="/matches">{open_match}</a></p>'
    assert (paragraph in body) is recovery
    if not recovery:
        assert open_match not in body and 'href="/matches"' not in body
    assert f'<p><a href="{REFRESH}">{refresh}</a></p>' in body
    assert label in body and add in body and t(locale, "task.learning.recorded_help") in body
    assert '<p></p>' not in body
    form = Forms(body).find(ADD)
    assert set(form["values"]) == LEARNING_ENTRY_FIELDS | {"_frontend_form_instance"}
    nodes = Hierarchy(body).nodes
    actual = next(n for n in nodes if n["tag"] == "form")
    assert actual["attrs"]["method"] == "post" and actual["attrs"]["action"] == ADD
    selector = next(n for n in nodes if n["tag"] == "select"
                    and n["attrs"].get("name") == "source_handle")
    assert "required" in selector["attrs"]
    assert_shell(page)
    return form


@pytest.mark.parametrize("locale", ("de", "en"))
def test_available_source_omits_literal_body_shortcut_but_keeps_add_refresh_and_shell(
    localized_server, locale,
):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    # A rejected item beside a usable source must not turn ordinary entry into recovery.
    path.with_name("invalid.json").write_bytes(b"{}")
    create_collection(browser)
    page = browser.request("GET", "/learning/current",
                           headers={"Accept-Language": locale})[2].decode()
    form = assert_controls(page, locale, recovery=False)
    assert form["values"]["source_handle"] == ""
    assert f'value="{source_handle(path)}"' in source_body(page)
    assert t(locale, "creation.managed.status.invalid") in source_body(page)
    assert 'href="#learning-recorded-matches"' in page  # Optional Report's Add remedy.
    active = localized_server.app_context.managed_stateful.active_learning
    assert not active.corpus.store.match_snapshots


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("invalid", (False, True))
def test_no_usable_source_preserves_existing_match_remedy(localized_server, locale, invalid):
    browser = Browser(localized_server)
    if invalid:
        root = localized_server.app_context.managed_stateful.root("matches")
        (root / "invalid.json").write_bytes(b"{}")
    create_collection(browser)
    page = browser.request("GET", "/learning/current",
                           headers={"Accept-Language": locale})[2].decode()
    assert_controls(page, locale, recovery=True)
    body = source_body(page)
    assert t(locale, "task.learning.no_recorded") in body
    assert ' disabled' in body
    # Follow the emitted remedy; this is an entry visit, not opening a recording.
    assert 'href="/matches"' in body
    entry = browser.page("/matches")
    assert 'href="/matches/new"' in entry
    assert localized_server.app_context.managed_stateful.active_match is None


def test_retained_evaluation_survives_navigation_refresh_language_duplicate_and_stale_remedy(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    original = path.read_bytes()
    calls = Counter()

    def counted(name, real):
        def wrapped(*args, **kwargs):
            calls[name] += 1
            return real(*args, **kwargs)
        return wrapped

    for module, name, label in (
        (learning, "import_match_workspace_into_learning_corpus_web_v1", "imports"),
        (learning, "prepare_learning_corpus_artifacts_web_v1", "preparations"),
        (learning, "select_current_learning_corpus_snapshot_web_v1", "selections"),
        (corpus_import, "save_learning_corpus_catalog_v1", "catalog_saves"),
    ):
        monkeypatch.setattr(module, name, counted(label, getattr(module, name)))
    page = create_collection(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    response = browser.submit(assert_controls(page, "en", recovery=False),
                              source_handle=source_handle(path))
    assert response[1]["location"] == "/learning/current#" + match_target(
        active, workspace.match_definition.match_id)
    page = follow(browser, response)
    assert calls == Counter(imports=1, catalog_saves=1)
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[1]["location"] == "/learning/current#learning-results"
    page = follow(browser, response)
    retained, files = downloads(browser), saved_bytes(active.path)
    artifacts = active.corpus.prepared_artifacts
    current = active.corpus.store.document.catalog.current_matches
    assert tuple(learning.build_unified_learning_state_v1(active)["prepared"][key] for key in (
        "observed_decision_count", "record_count", "skipped_decision_count")) == (6, 2, 4)
    # Each destination is present on the preceding page; no source is opened.
    for route in ("/", "/matches", "/learning"):
        assert f'href="{route}"' in page
        page = browser.page(route)
        assert downloads(browser) == retained
    # HTTP lifetime probe; native browser Back is verified separately. The list's
    # explicit Open form is a strict reopen, not a passive current-page link.
    page = browser.page("/learning/current")
    for locale in ("de", "en"):
        page = switch(browser, page, locale)
        assert_controls(page, locale, recovery=False)
        assert downloads(browser) == retained
    stale = Forms(page).find(ADD)
    assert f'href="{REFRESH}"' in source_body(page)
    response = browser.request("GET", REFRESH)
    assert response[1]["location"] == "/learning/current#learning-recorded-matches"
    page = follow(browser, response)
    assert downloads(browser) == retained
    response = browser.submit(stale, source_handle=source_handle(path))
    assert response[0] == 409
    page = response[2].decode()
    assert 'class="error-summary"' in page
    assert_controls(page, "en", recovery=False)
    page = follow(browser, browser.request("GET", REFRESH))
    page = follow(browser, browser.submit(Forms(page).find(ADD), source_handle=source_handle(path)))
    assert active.last_result.status == "unchanged"
    affected = node(page, match_target(active, workspace.match_definition.match_id))
    assert "identical content" in affected["text"]
    assert 'data-operation-feedback' not in page
    assert active.corpus.prepared_artifacts is artifacts and downloads(browser) == retained
    assert active.corpus.store.document.catalog.current_matches == current
    assert saved_bytes(active.path) == files and path.read_bytes() == original
    assert localized_server.app_context.managed_stateful.active_match is None
    assert calls == Counter(imports=2, preparations=1, catalog_saves=1)
    # A genuine later Add keeps Current but invalidates the retained preparation.
    external_pass(path, workspace)
    follow(browser, browser.submit(Forms(page).find(ADD), source_handle=source_handle(path)))
    assert active.corpus.store.document.catalog.current_matches == current
    assert active.corpus.prepared_artifacts is None
    assert calls == Counter(imports=3, preparations=1, catalog_saves=2)
