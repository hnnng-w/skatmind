"""Stable HTTP work counts, not elapsed-time performance gates."""

from collections import Counter

import pytest
from test_automatic_learning_ui import create, localized_server, route_of
from test_automatic_match_learning import save
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

__all__ = ["localized_server"]


@pytest.mark.parametrize("page", ("result", "entry", "control"))
def test_native_language_checks_once_per_logical_boundary(localized_server, monkeypatch, page):
    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    result = create(browser)
    route = {"result": route_of(result), "entry": "/learning/automatic", "control": "/about"}[page]
    html = browser.page(route)
    counts = Counter()
    service = app.automatic_match_learning
    original = service.validate_delivery
    def validate(binding):
        counts["delivery"] += 1
        return original(binding)
    monkeypatch.setattr(service, "validate_delivery", validate)
    monkeypatch.setattr(service.store, "snapshot",
                        lambda: pytest.fail("Unchanged language repeated archive admission"))
    response = browser.submit(Forms(html).find("/actions/profile/language"), language="de")
    assert response[0] == 303
    assert counts["delivery"] == (0 if page == "control" else 3)
    counts.clear()
    returned = follow(browser, response)
    assert 'lang="de"' in returned
    assert counts["delivery"] == (0 if page == "control" else 6)


def test_in_memory_binding_is_rechecked_after_filesystem_validation(localized_server, monkeypatch):
    from skatmind.app_web.language_context import (
        LanguageContextConflict,
        validate_language_source_v1,
    )

    app = localized_server.app_context
    save(app)
    browser = Browser(localized_server)
    create(browser)
    page = browser.page("/learning/automatic")
    token = Forms(page).find("/actions/profile/language")["values"]["_frontend_language_context"]
    source = app.language_context.pages[token].source
    controller = app.automatic_learning_ui
    original = controller.resolve
    def changed(token):
        result = original(token)
        controller.service.attempt = object()
        return result
    monkeypatch.setattr(controller.__class__, "resolve", lambda self, token: changed(token))
    with pytest.raises(LanguageContextConflict):
        validate_language_source_v1(app, source)
