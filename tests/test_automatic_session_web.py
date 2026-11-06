import re

import pytest
from test_automatic_learning_ui import create, route_of
from test_automatic_learning_ui import localized_server as _localized_server
from test_match_recording_recovery_web import follow
from test_session_decision_observation import _observed
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.session_frontend import GuidedSessionContextV1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.session_persistence import save_session_persistence_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path, monkeypatch):
    yield from _localized_server.__wrapped__(tmp_path, monkeypatch)


def install_session(app, *, missing=False):
    _before, state, checkpoint = _observed()
    document = build_session_persistence_document_v1(state,
        decision_checkpoints=() if missing else (checkpoint,))
    root = app.managed_home.category("sessions").path
    active = GuidedSessionContextV1(category_root=root, path=root / "session.json",
        handle="a" * 64, document=document)
    save_session_persistence_file_v1(active.path, document, expected_content_fingerprint=None)
    app.managed_stateful.activate_session(active)
    return active


@pytest.mark.parametrize("locale", ("en", "de"))
def test_session_only_native_navigation_and_saved_analysis(localized_server, locale):
    server = localized_server
    app = server.app_context
    active = install_session(app)
    browser = Browser(server)
    page = browser.page()
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    assert text(locale, "session_learning.saved") in page
    page = follow(browser, browser.submit(Forms(page).find("/sessions/review-decision")))
    assert active.evidence_notice[1] == "saved"
    expected = active.execution
    from skatmind.app_web.saved_match_analyses import _caption, archive_store
    store = archive_store(app)
    assert _caption(store.read_evidence(store.snapshot().available_evidence_ids[0]), locale)
    saved = browser.page("/sessions/saved-analyses")
    route = re.search(r'href="(/sessions/saved-analyses/[0-9a-f]+)"', saved)[1]
    page = browser.page(route)
    assert browser.request("GET", route + "/request.json")[2] == expected.request_json_bytes
    assert browser.request("GET", route + "/result.json")[2] == expected.result_json_bytes
    assert '/learning/automatic' in page
    assert '/sessions/saved-analyses/' not in browser.page("/matches/saved-analyses")
    page = create(browser)
    assert text(locale, "session_learning.title") in page
    source_route = re.search(r'href="([^"]+/session/source/0)"', page)[1]
    source = browser.page(source_route)
    decision_route = re.search(r'href="([^"]+/session/decision/0)"', source)[1]
    decision = browser.page(decision_route)
    evidence_route = re.search(r'href="([^"]+/session/evidence/0)"', decision)[1]
    evidence = browser.page(evidence_route)
    assert browser.request("GET", evidence_route + "/result.json")[2] == expected.result_json_bytes
    switched = follow(browser, browser.submit(Forms(evidence).find("/actions/profile/language"),
                                               language="de" if locale == "en" else "en"))
    assert route_of(switched) == evidence_route


def test_missing_checkpoint_is_valid_coverage_without_an_execution(localized_server):
    app = localized_server.app_context
    install_session(app, missing=True)
    browser = Browser(localized_server)
    page = create(browser)
    source = browser.page(re.search(r'href="([^"]+/session/source/0)"', page)[1])
    decision = browser.page(re.search(r'href="([^"]+/session/decision/0)"', source)[1])
    assert text("en", "session_learning.missing", count=1) in decision
    assert app.automatic_match_learning._installed.bundle.session_evidence == ()


def test_session_final_download_delivery_rejects_source_change(localized_server, monkeypatch):
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    app = localized_server.app_context
    active = install_session(app)
    browser = Browser(localized_server)
    follow(browser, browser.submit(Forms(browser.page()).find("/sessions/review-decision")))
    create(browser)
    controller = app.automatic_learning_ui
    view = controller.capture()
    route = view.base + "/session/evidence/0/result.json"
    original = Handler._send_bytes
    def changed(handler, status, content, **kwargs):
        if handler.path == route and status == 200:
            active.path.unlink()
        return original(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", changed)
    response = browser.request("GET", route)
    assert response[0] == 409 and b'</html>' in response[2]


def test_restart_native_access_needs_no_active_session_or_analysis(localized_server, monkeypatch):
    from test_session_recorded_review import selection

    import skatmind.automatic_learning_io as io
    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1
    from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

    app = localized_server.app_context
    active = install_session(app)
    execute_recorded_session_decision_v1(app, active, selection=selection(active))
    execute_recorded_session_decision_v1(app, active, selection=selection(active),
        rollout_settings=WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=1,
                                                    wall_clock_timeout_ms=30000))
    browser = Browser(localized_server)
    routes = re.findall(r'href="(/sessions/saved-analyses/[0-9a-f]+)"',
                        browser.page("/sessions/saved-analyses"))
    assert len(routes) == 2
    originals = [tuple(browser.request("GET", route + "/" + kind + ".json")[2]
                       for kind in ("request", "result")) for route in routes]
    localized_server.app_context = AppWebContextV1.create(app.managed_home)
    fresh = Browser(localized_server)
    monkeypatch.setattr(io, "write_temporary",
                        lambda *a, **kw: pytest.fail("Passive archive write"))
    monkeypatch.setattr("skatmind.app_web.session_recorded_review.execute_guided_frontend_review_v1",
                        lambda *a, **kw: pytest.fail("Passive analysis"))
    assert all(fresh.request("GET", route)[0] == 409 for route in routes)
    new_routes = re.findall(r'href="(/sessions/saved-analyses/[0-9a-f]+)"',
                            fresh.page("/sessions/saved-analyses"))
    assert len(new_routes) == 2 and set(new_routes).isdisjoint(routes)
    for route, expected in zip(new_routes, originals, strict=True):
        assert fresh.request("GET", route)[0] == 200
        assert tuple(fresh.request("GET", route + "/" + kind + ".json")[2]
                     for kind in ("request", "result")) == expected
    assert localized_server.app_context.managed_stateful.active_session is None


def test_native_session_retry_form_saves_without_reexecution(localized_server, monkeypatch):
    import skatmind.automatic_learning_io as io
    app = localized_server.app_context
    active = install_session(app)
    browser = Browser(localized_server)
    original = io.write_temporary
    def fail(directory, raw):
        if directory.name == "reports":
            raise OSError("Controlled native retry storage fault")
        return original(directory, raw)
    monkeypatch.setattr(io, "write_temporary", fail)
    page = follow(browser, browser.submit(Forms(browser.page()).find("/sessions/review-decision")))
    assert active.evidence_notice[1] == "unsaved"
    pending = active.pending_evidence
    monkeypatch.setattr(io, "write_temporary", original)
    monkeypatch.setattr("skatmind.app_web.session_recorded_review.execute_guided_frontend_review_v1",
                        lambda *a, **kw: pytest.fail("Retry must not execute analysis"))
    response = browser.submit(Forms(page).find("/sessions/retry-saving"))
    assert response[0] == 200
    assert active.evidence_notice == (pending.source, "saved", pending.candidate.evidence.identity)
