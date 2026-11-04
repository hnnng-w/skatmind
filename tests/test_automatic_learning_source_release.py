"""Issue #313 review A: genuine saved-source history and native maintenance consent."""

from collections import Counter
from html import unescape

import pytest
from test_automatic_learning_ui import UPDATE, create, localized_server
from test_automatic_match_learning import rewrite, save
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

__all__ = ["localized_server"]


def cleanup_form(page, mode):
    matches = [form for form in Forms(page).forms
               if form["action"] == "/learning/automatic/cleanup-preview"
               and form["values"].get("mode") == mode]
    assert len(matches) == 1, f"Missing native cleanup mode: {mode}"
    return matches[0]


def confirm(browser, page):
    form = Forms(page).find("/learning/automatic/confirm")
    assert "confirm_apply" not in form["values"]
    return follow(browser, browser.submit(form, confirm_apply="on"))


def source_history(server, corrections=3):
    app = server.app_context
    path, document = save(app)
    browser = Browser(server)
    page = create(browser)
    for number in range(corrections):
        document = rewrite(path, document, title=f"Saved correction {number + 1}")
        page = browser.page("/learning/automatic")
        page = follow(browser, browser.submit(Forms(page).find(UPDATE)))
    return browser, path, document, page


def test_native_source_only_history_has_an_explicit_release_remedy(localized_server):
    browser, path, document, page = source_history(localized_server)
    store = localized_server.app_context.automatic_match_learning.store
    before = store.snapshot()
    assert len(before.manifest.sources) == 4 and before.manifest.evidence == ()
    saved = path.read_bytes()
    # Existing consent remains strictly orphan cleanup / Report removal respectively.
    for mode in ("orphans", "old_evidence"):
        page = confirm(browser, follow(browser, browser.submit(cleanup_form(page, mode))))
        assert store.snapshot().manifest.sources == before.manifest.sources
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    page = confirm(browser, preview)
    after = store.snapshot()
    assert len(after.manifest.sources) == 1
    assert (after.manifest.sources[0].source_version.content_fingerprint
            == document.content_fingerprint)
    assert after.retained_bytes < before.retained_bytes
    assert path.read_bytes() == saved


def test_small_quota_recovers_via_explicit_source_release(localized_server, monkeypatch):
    import skatmind.app_web.automatic_match_learning as preparation
    import skatmind.automatic_learning_io as io
    from skatmind.automatic_learning_store import StoreLimitsV1

    browser, path, document, _page = source_history(localized_server)
    service = localized_server.app_context.automatic_match_learning
    store = service.store
    bound = store.snapshot().retained_bytes + 256
    assert bound < 1_000_000  # Deliberately tiny genuine history, not a 512-MiB fixture.
    store.limits = StoreLimitsV1(total_bytes=bound)
    rewrite(path, document, title="Unsaved-to-Learning latest correction")
    recording = path.read_bytes()
    counts = Counter()
    real_build, real_write = preparation.build_automatic_match_bundle, io.write_temporary
    def build(*args, **kwargs):
        counts["preparation"] += 1
        return real_build(*args, **kwargs)
    def write(directory, raw):
        counts[directory.name] += 1
        return real_write(directory, raw)
    monkeypatch.setattr(preparation, "build_automatic_match_bundle", build)
    monkeypatch.setattr(io, "write_temporary", write)
    page = browser.page("/learning/automatic")
    assert counts == {}
    response = browser.submit(Forms(page).find(UPDATE))
    assert response[0] == 409 and b'storage is full' in response[2]
    assert counts == {}  # Reservation quota fails before preparation/publication.
    preview = follow(browser, browser.submit(cleanup_form(
        response[2].decode(), "obsolete_sources")))
    assert counts == {} and 'dependent' in preview
    page = confirm(browser, preview)
    assert counts == {"automatic-learning": 1}
    assert store.snapshot().manifest.current_generation is None
    assert service._installed is None
    follow(browser, browser.submit(Forms(page).find(UPDATE)))
    assert counts == {"automatic-learning": 2, "preparation": 1, "sources": 1, "generations": 1}
    assert len(store.snapshot().manifest.sources) == 1
    assert store.snapshot().retained_bytes < bound and path.read_bytes() == recording


@pytest.mark.parametrize("change", ("deleted", "invalid", "ambiguous", "unsupported"))
def test_release_requires_authoritative_inventory(localized_server, change):
    import json
    browser, path, _document, _page = source_history(localized_server, corrections=1)
    service = localized_server.app_context.automatic_match_learning
    original = service.store.snapshot().manifest
    if change == "deleted":
        path.unlink()  # Deliberate fixture deletion of the editable recording.
    elif change == "invalid":
        path.write_bytes(b'{}')
    elif change == "ambiguous":
        path.with_name("duplicate.json").write_bytes(path.read_bytes())
    else:
        data = json.loads(path.read_bytes())
        data["match_workspace_persistence_version"] = 99
        path.write_text(json.dumps(data), encoding="utf-8")
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    captured = service.app.automatic_learning_ui.confirmation
    assert len(captured.sources) == (2 if change == "deleted" else 0)
    assert captured.source_release_blocked is (change != "deleted")
    confirm(browser, preview)
    remaining = service.store.snapshot().manifest
    if change == "deleted":
        assert remaining.sources == () and remaining.generations == ()
        assert service._installed is None
    else:
        assert remaining.sources == original.sources


def test_excluded_current_source_is_still_protected(localized_server):
    from dataclasses import replace

    from skatmind.automatic_learning_contracts import ExclusionV1

    browser, _path, document, _page = source_history(localized_server, corrections=1)
    store = localized_server.app_context.automatic_match_learning.store
    before = store.snapshot().manifest
    exclusion = ExclusionV1(source=before.sources[0].source_version.source, reason="explicit")
    requested = replace(before, revision=before.revision + 1, exclusions=(exclusion,))
    assert store.update_manifest(requested, expected_manifest=before.fingerprint).status == "saved"
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    confirm(browser, preview)
    remaining, = store.snapshot().manifest.sources
    assert remaining.source_version.content_fingerprint == document.content_fingerprint


def test_incomplete_inventory_and_changed_confirmation_never_release_sources(
    localized_server, monkeypatch,
):
    import skatmind.app_web.automatic_match_inventory as inventory
    import skatmind.automatic_learning_io as io

    browser, path, document, page = source_history(localized_server, corrections=1)
    store = localized_server.app_context.automatic_match_learning.store
    before = store.snapshot().manifest
    with monkeypatch.context() as patch:
        patch.setattr(inventory, "MANAGED_ITEM_MAX_CANDIDATES", 0)
        assert browser.submit(cleanup_form(page, "obsolete_sources"))[0] == 409
        assert store.snapshot().manifest == before
    preview = follow(browser, browser.submit(cleanup_form(
        browser.page("/learning/automatic"), "obsolete_sources")))
    original = io.write_temporary
    fired = False
    def write(directory, raw):
        nonlocal fired
        temporary = original(directory, raw)
        if directory == store.root and not fired:
            fired = True
            rewrite(path, document, title="Concurrent correction before manifest replacement")
        return temporary
    monkeypatch.setattr(io, "write_temporary", write)
    response = browser.submit(Forms(preview).find("/learning/automatic/confirm"),
                              confirm_apply="on")
    assert fired and response[0] == 409
    assert store.snapshot().manifest == before


def test_source_preview_cancel_language_and_reader_conflict_preserve_consent(
    localized_server, monkeypatch,
):
    browser, path, _document, page = source_history(localized_server, corrections=1)
    controller = localized_server.app_context.automatic_learning_ui
    store = controller.service.store
    before = {p: p.read_bytes() for p in store.root.rglob("*.json")}
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    old_form = Forms(preview).find("/learning/automatic/confirm")
    # Cancel is ordinary native navigation and performs no cleanup.
    browser.page("/learning/automatic")
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert browser.submit(old_form, confirm_apply="on")[0] == 409
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    exact = controller.confirmation.cleanup
    monkeypatch.setattr(store, "preview_cleanup", lambda **kw: pytest.fail("Consent regenerated"))
    for locale in ("de", "en"):
        preview = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
                                                language=locale))
        assert controller.confirmation.cleanup is exact
        assert "confirm_apply" not in Forms(preview).find("/learning/automatic/confirm")["values"]
        record = controller.confirmation.sources[0][0]
        assert record.source_version.content_fingerprint in preview
    manifest = store.snapshot().manifest
    with store.pin_objects((manifest.sources[0].object_ref,),
                           expected_manifest=manifest.fingerprint):
        response = browser.submit(Forms(preview).find("/learning/automatic/confirm"),
                                  confirm_apply="on")
    assert response[0] == 409 and b'</html>' in response[2]
    assert all(p.read_bytes() == raw for p, raw in before.items()) and path.exists()


def test_existing_reader_protects_released_object_until_later_orphan_cleanup(localized_server):
    from skatmind import automatic_learning_io as io

    browser, _path, document, _page = source_history(localized_server, corrections=1)
    store = localized_server.app_context.automatic_match_learning.store
    manifest = store.snapshot().manifest
    obsolete = next(row for row in manifest.sources
                    if row.source_version.content_fingerprint != document.content_fingerprint)
    path = io.object_path(store.root, obsolete.object_ref)
    original = path.read_bytes()
    with store.pin_objects((obsolete.object_ref,), expected_manifest=manifest.fingerprint):
        page = browser.page("/learning/automatic")
        preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
        confirm(browser, preview)
        assert obsolete not in store.snapshot().manifest.sources
        assert path.read_bytes() == original
    page = browser.page("/learning/automatic")
    confirm(browser, follow(browser, browser.submit(cleanup_form(page, "orphans"))))
    assert not path.exists()


@pytest.mark.parametrize("interrupt", (False, True))
def test_retirement_and_reference_first_source_removal(localized_server, monkeypatch, interrupt):
    from pathlib import Path

    from skatmind.app_web.stateful_localization import text

    browser, path, document, page = source_history(localized_server, corrections=0)
    original_route = Forms(page).find("/actions/profile/language")["values"]["return_to"]
    service = localized_server.app_context.automatic_match_learning
    old = service.store.snapshot().manifest.sources[0]
    rewrite(path, document, title="Corrected outside Learning")
    recording = path.read_bytes()
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    assert text("en", "automatic.retire_generation") in unescape(preview)
    original = Path.unlink
    def unlink(value, *args, **kwargs):
        if interrupt and value.parent.name == "sources" and value.suffix == ".json":
            raise OSError("Controlled post-commit source removal interruption")
        return original(value, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", unlink)
    page = confirm(browser, preview)
    assert service.store.snapshot().manifest.sources == ()
    assert service._installed is None
    if interrupt:
        assert text("en", "feedback.automatic_partial_cleanup") in unescape(page)
        assert service.store.read_object(old.object_ref)
    assert browser.request("GET", original_route)[0] == 409
    assert path.read_bytes() == recording


@pytest.fixture(scope="module")
def shared_reports():
    from test_automatic_match_evidence import genuine_candidate
    # Two genuine tiny Immediate executions sharing one exact original Workspace.
    return (genuine_candidate(decision=28), genuine_candidate(decision=29))


def test_shared_evidence_and_independent_manual_copy_keep_original_sources(
    localized_server, shared_reports, monkeypatch,
):
    from test_automatic_match_learning_evidence import forbid_execution, stage

    from skatmind.app_web.learning_frontend import UnifiedLearningContextV1
    from skatmind.automatic_match_evidence import decode_match_source
    from skatmind.corpus_web.context import LearningCorpusWebContextV1
    from skatmind.learning_corpus_import import import_match_workspace_file_into_learning_corpus_v1
    from skatmind.learning_corpus_persistence import (
        initialize_learning_corpus_directory_v1,
        load_learning_corpus_directory_v1,
    )

    app = localized_server.app_context
    source = decode_match_source(shared_reports[0].objects[0], shared_reports[0].source)
    path, document = save(app, workspace=source.document.workspace)
    archive = stage(app, shared_reports)
    manual = app.managed_home.category("corpora").path / "independent-release"
    initialize_learning_corpus_directory_v1(manual, corpus_id="independent-release")
    initial = load_learning_corpus_directory_v1(manual).document
    assert import_match_workspace_file_into_learning_corpus_v1(manual, path,
        expected_catalog_revision=initial.catalog.revision,
        expected_catalog_content_fingerprint=initial.content_fingerprint,
        selection_mode="keep_current", same_revision_resolution="reject").status == "applied"
    corpus = LearningCorpusWebContextV1.open(manual)
    active = UnifiedLearningContextV1(category_root=manual.parent, path=manual,
                                      handle="a" * 64, corpus=corpus)
    app.managed_stateful.active_learning = active
    bytes_before = {p: p.read_bytes() for p in manual.rglob("*.json")}
    manual_store = corpus.store
    native = {value.evidence.identity: archive.read_evidence(value.evidence.identity).downloads
              for value in shared_reports}
    calls = forbid_execution(monkeypatch)
    browser = Browser(localized_server)
    create(browser)
    for index in (1, 2):
        document = rewrite(path, document, title=f"Saved evidence-free correction {index}")
        page = browser.page("/learning/automatic")
        follow(browser, browser.submit(Forms(page).find(UPDATE)))
    recording = path.read_bytes()
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    assert len(app.automatic_learning_ui.confirmation.sources) == 1
    confirm(browser, preview)
    remaining = archive.snapshot().manifest
    assert len(remaining.sources) == 2 and len(remaining.evidence) == 2
    assert source.record in remaining.sources
    # Explicit fixture removal of only one Report proves the shared dependency remains protected.
    partial = archive.preview_cleanup(expected_manifest=remaining.fingerprint,
                                      remove_evidence_ids=(shared_reports[0].evidence.identity,))
    assert archive.commit_cleanup(partial).status == "saved"
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    assert app.automatic_learning_ui.confirmation.sources == ()
    confirm(browser, preview)
    retained = archive.read_evidence(shared_reports[1].evidence.identity)
    assert retained.downloads == native[shared_reports[1].evidence.identity]
    assert archive.read_object(source.record.object_ref).raw == shared_reports[0].objects[0].raw
    assert path.read_bytes() == recording and calls == []
    assert app.managed_stateful.active_learning is active and corpus.store is manual_store
    assert all(p.read_bytes() == raw for p, raw in bytes_before.items())
