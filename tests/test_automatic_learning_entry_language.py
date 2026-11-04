"""Issue #313 review B: language uses the delivered entry's original authority."""

import json
import re
from collections import Counter
from dataclasses import replace

import pytest
from test_automatic_learning_ui import create, localized_server
from test_automatic_match_learning import rewrite, save
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

__all__ = ["localized_server"]


def observe_passive(monkeypatch):
    from test_automatic_match_learning_evidence import forbid_execution

    import skatmind.app_web.automatic_match_learning as service
    import skatmind.app_web.frontend_profile_operations as profile
    import skatmind.automatic_learning_io as io
    import skatmind.capture_web.context as capture
    import skatmind.learning_corpus_import as imports

    calls = Counter()
    original = profile.save_frontend_profile_file_v1
    def save_profile(*args, **kwargs):
        calls["profile"] += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(profile, "save_frontend_profile_file_v1", save_profile)
    monkeypatch.setattr(service, "build_automatic_match_bundle",
                        lambda *a, **kw: pytest.fail("Passive preparation"))
    monkeypatch.setattr(io, "write_temporary",
                        lambda *a, **kw: pytest.fail("Passive archive write"))
    monkeypatch.setattr(capture, "save_match_workspace_file_v1",
                        lambda *a, **kw: pytest.fail("Passive recording write"))
    monkeypatch.setattr(imports, "import_match_workspace_file_into_learning_corpus_v1",
                        lambda *a, **kw: pytest.fail("Passive manual import"))
    forbid_execution(monkeypatch)
    return calls


@pytest.mark.parametrize("change", ("unchanged", "source", "manifest"))
def test_delivered_native_entry_language_checks_original_state(
    localized_server, monkeypatch, change,
):
    app = localized_server.app_context
    path, document = save(app)
    browser = Browser(localized_server)
    create(browser)
    page = browser.page("/learning/automatic")
    language = Forms(page).find("/actions/profile/language")
    service = app.automatic_match_learning
    attempt, installed, profile = service.attempt, service._installed, app.frontend_profile
    if change == "source":
        rewrite(path, document)
    elif change == "manifest":
        from skatmind.automatic_learning_contracts import ExclusionV1
        before = service.store.snapshot().manifest
        changed = replace(before, revision=before.revision + 1, exclusions=(ExclusionV1(
            source=before.sources[0].source_version.source, reason="explicit"),))
        assert service.store.update_manifest(changed,
            expected_manifest=before.fingerprint).status == "saved"
    assert service.attempt is attempt and service._installed is installed
    counts = observe_passive(monkeypatch)
    response = browser.submit(language, language="de")
    if change == "unchanged":
        assert response[0] == 303
        returned = follow(browser, response)
        assert 'lang="de"' in returned
        assert counts == {"profile": 1}
    else:
        assert response[0] == 409, response[2].decode()
        assert b'</html>' in response[2]
        assert app.frontend_profile is profile and counts == {}


@pytest.mark.parametrize("route", ("/learning/automatic", "/learning"))
def test_a_newer_tab_cannot_replace_an_older_entry_binding(localized_server, monkeypatch, route):
    app = localized_server.app_context
    path, document = save(app)
    browser = Browser(localized_server)
    create(browser)
    old = Forms(browser.page(route)).find("/actions/profile/language")
    rewrite(path, document)
    new = Forms(browser.page(route)).find("/actions/profile/language")
    profile = app.frontend_profile
    counts = observe_passive(monkeypatch)
    assert browser.submit(old, language="de")[0] == 409
    assert app.frontend_profile is profile and counts == {}
    returned = follow(browser, browser.submit(new, language="de"))
    assert 'lang="de"' in returned and counts == {"profile": 1}


def test_unchanged_entry_language_never_recaptures_authority(localized_server, monkeypatch):
    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    create(browser)
    page = browser.page("/learning/automatic")
    counts = observe_passive(monkeypatch)
    monkeypatch.setattr(app.automatic_match_learning, "capture_delivery",
                        lambda: pytest.fail("Language replaced original entry authority"))
    follow(browser, browser.submit(Forms(page).find("/actions/profile/language"), language="de"))
    assert counts == {"profile": 1}


@pytest.mark.parametrize("stage", ("after_save", "before_return", "render", "headers"))
def test_valid_save_then_late_source_conflict_is_accounted_separately(
    localized_server, monkeypatch, stage,
):
    import skatmind.app_web.automatic_learning_http as automatic
    import skatmind.app_web.server as server

    app = localized_server.app_context
    path, document = save(app)
    browser = Browser(localized_server)
    create(browser)
    page = browser.page("/learning/automatic")
    language = Forms(page).find("/actions/profile/language")
    counts = observe_passive(monkeypatch)
    fired = False
    def change():
        nonlocal fired
        if not fired:
            fired = True
            rewrite(path, document, title="Deliberate concurrent source save")
    if stage == "after_save":
        original = server.set_frontend_language_v1
        def language_save(*args, **kwargs):
            value = original(*args, **kwargs)
            change()
            return value
        monkeypatch.setattr(server, "set_frontend_language_v1", language_save)
    response = browser.submit(language, language="de")
    if stage != "after_save":
        assert response[0] == 303 and counts == {"profile": 1}
        if stage == "before_return":
            change()
        elif stage == "render":
            original = automatic.render_entry
            def render(*args, **kwargs):
                value = original(*args, **kwargs)
                change()
                return value
            monkeypatch.setattr(automatic, "render_entry", render)
        else:
            original = server.SkatMindAppWebRequestHandlerV1._send_bytes
            def send(handler, status, content, **kwargs):
                if handler.path == "/learning/automatic" and status == 200:
                    change()
                return original(handler, status, content, **kwargs)
            monkeypatch.setattr(server.SkatMindAppWebRequestHandlerV1, "_send_bytes", send)
        response = browser.request("GET", response[1]["location"])
    assert fired and response[0] == 409
    assert b'</html>' in response[2] and b'lang="de"' in response[2]
    assert app.frontend_profile.document.language == "de" and counts == {"profile": 1}


@pytest.mark.parametrize("changed", (False, True))
def test_enhanced_entry_disclosures_use_the_same_exact_binding(
    localized_server, monkeypatch, changed,
):
    from test_language_view_continuity import return_data
    from test_task_first_language_preservation import enhanced_switch

    app = localized_server.app_context
    path, document = save(app)
    browser = Browser(localized_server)
    create(browser)
    page = browser.page("/learning/automatic")
    value = {"forms": [], "disclosures": [True] * len(re.findall(r"<details\b", page)),
             "view": {"anchor": "top", "offset": 0, "x": 0, "focus": "de"}}
    if changed:
        rewrite(path, document)
    counts = observe_passive(monkeypatch)
    response = enhanced_switch(browser, page, json.dumps(value), "de")
    if changed:
        assert response[0] == 409 and counts == {}
    else:
        returned = follow(browser, response)
        assert return_data(returned)["view"] == value["view"]
        assert len(re.findall(r"<details\b[^>]*\bopen\b", returned)) == len(value["disclosures"])
        assert counts == {"profile": 1}
