"""Private maintenance presentation uses the exact captured plan, without new work."""

from html import unescape
from html.parser import HTMLParser

import pytest
from test_automatic_learning_source_release import cleanup_form, source_history
from test_automatic_learning_ui import create, localized_server
from test_automatic_match_learning import save
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.stateful_localization import text

__all__ = ["localized_server"]
CONFIRM = "/learning/automatic/confirm"


class PreviewText(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.visible = []
        self.details = []
        self.depth = 0
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "details":
            self.depth += 1
            self.details.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == "details":
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.visible.append(data)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_blocked_effect_free_preview_leads_with_blocker_without_consent(localized_server, locale):
    app = localized_server.app_context
    path, _ = save(app)
    browser = Browser(localized_server)
    create(browser)
    path.with_name("duplicate.json").write_bytes(path.read_bytes())
    page = browser.page("/learning/automatic")
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                        language=locale))
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    value = app.automatic_learning_ui.confirmation
    assert value.source_release_blocked
    assert value.cleanup.files == ()
    assert value.cleanup.manifest == value.view.binding.resumed.manifest
    assert 'name="confirm_apply"' not in preview
    assert not any(form["action"] == CONFIRM for form in Forms(preview).forms)
    visible = " ".join(PreviewText(preview).visible)
    blocker = text(locale, "automatic.source_release_blocked")
    reason = text(locale, "automatic.source_release_blocker.ambiguous", count=2)
    assert visible.index(blocker) < visible.index(reason)
    assert visible.index(reason) < visible.index(text(locale, "automatic.preview.no_changes"))
    assert text(locale, "automatic.preview.obsolete_sources") not in visible
    assert text(locale, "automatic.source_release_blocker.invalid", count=1) not in visible
    assert app.automatic_learning_ui.confirmation is value


@pytest.mark.parametrize("locale", ("de", "en"))
def test_actionable_source_summary_is_visible_and_fingerprints_are_closed(localized_server, locale):
    browser, path, _document, page = source_history(localized_server, corrections=1)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                        language=locale))
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    value = localized_server.app_context.automatic_learning_ui.confirmation
    assert len(value.sources) == 1
    parsed = PreviewText(preview)
    visible = " ".join(parsed.visible)
    record, snapshot = value.sources[0]
    caption = text(locale, "automatic.source_release_name",
                   name=snapshot.workspace.match_definition.title,
                   revision=snapshot.workspace_revision, number=1)
    assert caption in visible
    assert record.source_version.content_fingerprint not in visible
    assert record.source_version.content_fingerprint in preview
    assert parsed.details and all("open" not in attrs for attrs in parsed.details)
    assert text(locale, "automatic.retire_generation") in visible
    assert text(locale, "automatic.preview.obsolete_sources") in visible
    assert text(locale, "automatic.source_release_count", sources=1, retained=1) in visible
    assert preview.index(caption) < preview.index('name="confirm_apply"')
    assert visible.index(text(locale, "automatic.retire_generation")) < visible.index(
        text(locale, "automatic.consent"))
    assert Forms(preview).find(CONFIRM)["values"]["confirmation"] == value.token
    assert path.exists()


@pytest.mark.parametrize("reason", ("invalid", "unsupported"))
def test_only_observed_blockers_are_described(localized_server, reason):
    import json
    app = localized_server.app_context
    path, _document = save(app)
    browser = Browser(localized_server)
    create(browser)
    if reason == "invalid":
        path.write_bytes(b'{}')
    else:
        data = json.loads(path.read_bytes())
        data["match_workspace_persistence_version"] = 99
        path.write_text(json.dumps(data), encoding="utf-8")
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    visible = " ".join(PreviewText(preview).visible)
    assert text("en", "automatic.source_release_blocker." + reason, count=1) in visible
    absent = "invalid" if reason == "unsupported" else "unsupported"
    assert text("en", "automatic.source_release_blocker." + absent, count=1) not in visible
    assert 'name="confirm_apply"' not in preview


@pytest.mark.parametrize("locale", ("de", "en"))
def test_blocked_release_can_confirm_its_original_orphan_cleanup(
    localized_server, monkeypatch, locale,
):
    from automatic_learning_helpers import source_fixture
    from test_automatic_learning_entry_language import observe_passive

    app = localized_server.app_context
    path, _document = save(app)
    browser = Browser(localized_server)
    create(browser)
    path.with_name("duplicate.json").write_bytes(path.read_bytes())
    store = app.automatic_match_learning.store
    _record, orphan = source_fixture()  # Controlled storage-only owned orphan, not evidence.
    store.publish_object(orphan)
    original_sources = store.snapshot().manifest.sources
    recording = path.read_bytes()
    page = browser.page("/learning/automatic")
    preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
    value = app.automatic_learning_ui.confirmation
    assert value.source_release_blocked and value.sources == ()
    assert len(value.cleanup.files) == 1
    assert value.cleanup.manifest == value.view.binding.resumed.manifest
    with monkeypatch.context() as patch:
        counts = observe_passive(patch)
        patch.setattr(store, "preview_cleanup", lambda **kw: pytest.fail("Preview regenerated"))
        patch.setattr(store, "commit_cleanup", lambda *a, **kw: pytest.fail("Passive cleanup"))
        preview = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
                                                language=locale))
        assert counts == {"profile": 1}
        assert app.automatic_learning_ui.confirmation is value
        assert store.read_object(orphan.reference) == orphan
    visible = " ".join(PreviewText(preview).visible)
    assert visible.index(text(locale, "automatic.source_release_blocked")) < visible.index(
        text(locale, "automatic.preview.blocked_cleanup"))
    assert text(locale, "automatic.cleanup_effect", objects=1, reports=0) in visible
    assert text(locale, "automatic.preview.no_changes") not in visible
    form = Forms(preview).find(CONFIRM)
    assert form["values"]["confirmation"] == value.token
    assert "confirm_apply" not in form["values"]
    follow(browser, browser.submit(form, confirm_apply="on"))
    assert store.snapshot().manifest.sources == original_sources
    assert path.read_bytes() == recording
    assert not (store.root / orphan.area / (orphan.reference.fingerprint + ".json")).exists()


@pytest.mark.parametrize("locale", ("de", "en"))
def test_reference_only_release_keeps_consent_when_all_files_are_reader_protected(
    localized_server, locale,
):
    from skatmind import automatic_learning_io as io

    browser, _path, _document, page = source_history(localized_server, corrections=1)
    app = localized_server.app_context
    store = app.automatic_match_learning.store
    manifest = store.snapshot().manifest
    objects = {row.reference: store.read_object(row.reference).raw for row in manifest.objects}
    with store.pin_objects((manifest.previous_generation,), expected_manifest=manifest.fingerprint):
        page = browser.page("/learning/automatic")
        preview = follow(browser, browser.submit(cleanup_form(page, "obsolete_sources")))
        value = app.automatic_learning_ui.confirmation
        assert len(value.sources) == 1 and value.cleanup.files == ()
        assert value.cleanup.manifest != manifest
        preview = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
                                                language=locale))
        assert app.automatic_learning_ui.confirmation is value
        assert text(locale, "automatic.preview.no_changes") not in unescape(preview)
        assert text(locale, "automatic.source_release_count", sources=1, retained=1) in unescape(
            preview)
        form = Forms(preview).find(CONFIRM)
        assert "confirm_apply" not in form["values"]
        assert form["values"]["confirmation"] == value.token
        follow(browser, browser.submit(form, confirm_apply="on"))
        assert store.snapshot().manifest == value.cleanup.manifest
        assert all(io.object_path(store.root, ref).read_bytes() == raw
                   for ref, raw in objects.items())


@pytest.mark.parametrize("mode", ("orphans", "old_evidence", "obsolete_sources"))
def test_effect_free_cleanup_has_no_destructive_form_in_either_locale(localized_server, mode):
    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    page = create(browser)
    preview = follow(browser, browser.submit(cleanup_form(page, mode)))
    value = app.automatic_learning_ui.confirmation
    before = value.cleanup.manifest
    assert value.cleanup.files == () and before == value.view.binding.resumed.manifest
    for locale in ("de", "en"):
        preview = follow(browser, browser.submit(Forms(preview).find("/actions/profile/language"),
                                                language=locale))
        assert text(locale, "automatic.preview.no_changes") in unescape(preview)
        assert not any(form["action"] == CONFIRM for form in Forms(preview).forms)
        assert 'name="confirm_apply"' not in preview
        assert app.automatic_learning_ui.confirmation is value
        assert app.automatic_match_learning.store.snapshot().manifest == before


@pytest.mark.parametrize("locale", ("de", "en"))
def test_recovery_link_is_short_truthful_and_passive(localized_server, monkeypatch, locale):
    from test_automatic_learning_entry_language import observe_passive

    app = localized_server.app_context
    path, _document = save(app)
    browser = Browser(localized_server)
    create(browser)
    page = browser.page("/learning/automatic")
    follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language=locale))
    store = app.automatic_match_learning.store
    original = store.snapshot().manifest
    recording = path.read_bytes()
    counts = observe_passive(monkeypatch)
    monkeypatch.setattr(store, "commit_cleanup", lambda *a, **kw: pytest.fail("Passive cleanup"))
    monkeypatch.setattr(app.automatic_match_learning, "update",
                        lambda: pytest.fail("Passive Update"))
    response = browser.request("GET", "/learning/automatic/" + "f" * 64 + "/all")
    assert response[0] == 409 and b'</html>' in response[2]
    recovery = response[2].decode()
    assert '<a class="button-link secondary" href="/learning/automatic">' + text(
        locale, "automatic.recover") + '</a>' in recovery
    assert text(locale, "automatic.state.conflict") in unescape(recovery)
    if locale == "en":
        assert text(locale, "automatic.recover") == "Back to automatic Learning"
        assert "Nothing was changed" not in recovery and "owner" not in recovery
    browser.page("/learning/automatic")
    assert counts == {} and store.snapshot().manifest == original
    assert path.read_bytes() == recording
