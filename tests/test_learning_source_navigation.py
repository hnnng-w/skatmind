"""R13g: ordinary source controls and existing no-source recovery, using real files."""

from collections import Counter
from types import SimpleNamespace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_learning_direct_entry_web import (
    create_collection,
    downloads,
    independent_workspace,
    saved_bytes,
    source_handle,
)
from test_learning_outcome_navigation import match_target, node
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_review_navigation import external_pass, saved_partial_match
from test_recording_entry_settings_navigation import assert_shell
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.learning_frontend as learning
import skatmind.learning_corpus_import as corpus_import
from skatmind.app_web.learning_direct_entry import LEARNING_ENTRY_FIELDS
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.task_first_rendering import select_field
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as t
from skatmind.app_web.validation_rendering import _add_control_accessibility
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1

ADD = "/learning/add-recorded-match"
REFRESH = "/learning/recorded-matches/refresh"
DESCRIPTION = "learning-recorded-source-captions"
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


def assert_references(page, expected=None):
    tree = Hierarchy(page)
    selectors = [n for n in tree.within("learning-recorded-matches", "select")
                 if n["attrs"].get("name") == "source_handle"]
    assert len(selectors) == 1
    selector = selectors[0]
    options = [(n["attrs"]["value"], n["text"]) for n in tree.nodes
               if n["tag"] == "option" and any(p is selector for p in n["parents"])]
    if expected is not None:
        assert options == expected
    offered = [caption for value, caption in options if value != ""]
    lists = [n for n in tree.nodes if n["attrs"].get("id") == DESCRIPTION]
    if not offered:
        assert lists == [] and DESCRIPTION not in selector["attrs"].get("aria-describedby", "")
        return options
    assert len(lists) == 1 and lists[0]["tag"] == "ul"
    assert DESCRIPTION in selector["attrs"]["aria-describedby"].split()
    label = selector["parents"][-1]
    assert label["tag"] == "label" and "aria-label" not in selector["attrs"]
    assert lists[0]["parents"] == label["parents"]  # Outside the implicit name.
    siblings = [n for n in tree.nodes if n["parents"] == label["parents"]]
    assert siblings[siblings.index(label) + 1] is lists[0]
    assert siblings[siblings.index(lists[0]) + 1]["tag"] == "details"
    rows = tree.within(DESCRIPTION, "li")
    assert [row["text"] for row in rows] == offered
    for n in [lists[0], *[n for n in tree.nodes if any(p is lists[0] for p in n["parents"])]]:
        assert n["tag"] in {"ul", "li"}
        assert not {"tabindex", "aria-live", "hidden", "name"} & n["attrs"].keys()
        assert Hierarchy.visible(n)
    return options


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
    assert_references(page)
    assert_shell(page)
    return form


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("count", (0, 1, 2, 12))
def test_exact_captured_captions_and_fallbacks(localized_server, locale, count):
    browser = Browser(localized_server)
    create_collection(browser)
    active = localized_server.app_context.managed_stateful.active_learning
    state = learning.build_unified_learning_state_v1(active)
    long_name = '<Same & "caption">' + 'UnbrokenName' * 15
    recorded = [SimpleNamespace(status="invalid", semantic_product_id=None, display_label=None)]
    expected = [("", "Gespeichertes Match auswählen" if locale == "de" else "Choose a saved Match")]
    for index in range(count):
        handle = f"opaque-source-{index}"
        name = long_name if index < 2 else None
        recorded.append(SimpleNamespace(status="available", handle=handle,
            semantic_product_id=f"private-product-{index}", display_label=name, revision=123))
        resolved = name or ("Erfasstes Match" if locale == "de" else "Recorded Match")
        expected.append((handle, f"{index + 2}. {resolved} — " + (
            "aufgelistete Revision 123" if locale == "de" else "listed revision 123")))
    page = render_task_first_learning_v1(state, managed_handle=active.handle,
        locale=locale, recorded=tuple(recorded), learning_selection="binding")
    assert_references(page, expected)
    body = source_body(page)
    assert 'private-product-' not in body and '<Same' not in body
    if count:
        assert '&lt;Same &amp; &quot;caption&quot;&gt;' in body
        profile = SimpleNamespace(managed_item_display_labels=(SimpleNamespace(
            family="matches", product_id="private-product-0", display_name="Profile <name>"),))
        page = render_task_first_learning_v1(state, managed_handle=active.handle,
            locale=locale, recorded=tuple(recorded), profile=profile, learning_selection="binding")
        expected[1] = (expected[1][0], expected[1][1].replace(long_name, "Profile <name>"))
        assert_references(page, expected)
    no_form = render_task_first_learning_v1(state, managed_handle=active.handle,
        locale=locale, recorded=tuple(recorded))
    assert DESCRIPTION not in no_form and f'action="{ADD}"' not in no_form


def test_select_helper_default_is_byte_identical_and_description_is_opt_in():
    expected = ('<label>Saved Match <select name="source_handle" required>'
                '<option value="">Choose</option><option value="opaque&amp;value" selected>'
                '&lt;caption&gt;</option></select></label>')
    args = ("en", "source_handle", "task.learning.saved_match",
            (("", "Choose"), ("opaque&value", "<caption>")), "opaque&value")
    assert select_field(*args, required=True) == expected
    assert select_field(*args, required=True, described_by=None) == expected
    assert select_field(*args, required=True, described_by='private"id') == expected.replace(
        ' required>', ' required aria-describedby="private&quot;id">')
    markup = select_field(*args, required=True, described_by=DESCRIPTION + " existing-help")
    marked, control_id = _add_control_accessibility(
        markup, "source_handle", "field-error", "source-control")
    assert control_id == "source-control"
    assert f'aria-describedby="{DESCRIPTION} existing-help field-error"' in marked
    assert 'aria-invalid="true"' in marked


def test_references_regenerate_with_errors_language_and_discovery(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    page = create_collection(browser)
    options = assert_references(page)
    # Existing generic rejection is form-level; retain its actual choice and summary.
    response = browser.submit(Forms(page).find(ADD), source_handle=source_handle(path),
                              same_revision_resolution="invalid")
    assert response[0] == 400
    page = response[2].decode()
    assert_references(page, options)
    assert Forms(page).find(ADD)["values"]["source_handle"] == source_handle(path)
    selector = next(n for n in Hierarchy(page).nodes if n["tag"] == "select"
                    and n["attrs"].get("name") == "source_handle")
    descriptions = selector["attrs"]["aria-describedby"].split()
    assert descriptions == [DESCRIPTION]
    for identity in descriptions:
        assert sum(n["attrs"].get("id") == identity for n in Hierarchy(page).nodes) == 1
    assert 'class="error-summary"' in page and 'autofocus' in page
    page = switch(browser, page, "de")
    translated = assert_references(page)
    assert [v for v, _ in translated] == [v for v, _ in options]
    assert translated != options
    assert Forms(page).find(ADD)["values"]["source_handle"] == source_handle(path)
    # A duplicate identity is excluded on explicit refresh, never given a reference row.
    path.with_name("duplicate.json").write_bytes(path.read_bytes())
    page = follow(browser, browser.request("GET", REFRESH))
    assert_controls(page, "de", recovery=True)
    assert len(assert_references(page)) == 1


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
    # Import the non-first of two real equal-title/equal-revision sources.
    first = independent_workspace(workspace, "first-same-title")
    first_path = path.with_name("aaa.json")
    assert save_match_workspace_file_v1(first_path,
        build_match_workspace_persistence_document_v1(first),
        expected_content_fingerprint=None).status == "saved"
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
    options = assert_references(page)
    assert [v for v, _ in options] == ["", source_handle(first_path), source_handle(path)]
    active = localized_server.app_context.managed_stateful.active_learning
    response = browser.submit(assert_controls(page, "en", recovery=False),
                              source_handle=source_handle(path))
    assert response[1]["location"] == "/learning/current#" + match_target(
        active, workspace.match_definition.match_id)
    page = follow(browser, response)
    assert active.corpus.store.match_snapshots[0].workspace == workspace
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
