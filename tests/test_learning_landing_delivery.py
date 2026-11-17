"""One passive landing operation, with capture/final byte checks and real retained evidence."""

from dataclasses import replace
from time import perf_counter

import pytest
from learning_archive_fixture_helpers import measure_work, publish_fresh_archive, work_phase
from test_automatic_learning_bulk_read import passive_browser
from test_automatic_learning_delivery_receipt import rewrite_same_metadata
from test_automatic_learning_entry_language import observe_passive
from test_automatic_match_evidence import genuine_candidate
from test_automatic_match_learning import save
from test_frontend_language_switching import localized_server
from test_match_decision_analysis import _complete_workspace

from skatmind.app_web.automatic_learning_controller import automatic_controller
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.saved_match_analyses import archive_store

__all__ = ["localized_server", "passive_browser"]


@pytest.fixture(scope="module")
def candidate():
    start = perf_counter()
    result = genuine_candidate()
    print({"fixture_execution_seconds": perf_counter() - start})
    return result


@pytest.fixture
def landing(localized_server, candidate, monkeypatch):
    app = localized_server.app_context
    path, document = save(app, workspace=_complete_workspace())
    store = archive_store(app, initialize=True)
    with work_phase(monkeypatch, store, "landing_fixture_publication"):
        publish_fresh_archive(store, store.snapshot(), (candidate,))
    with work_phase(monkeypatch, store, "landing_explicit_update"):
        controller = automatic_controller(app)
        assert controller.service.update().status == "prepared"
    return app, store, path, document


@pytest.fixture
def empty_landing(localized_server):
    app = localized_server.app_context
    path, document = save(app)
    controller = automatic_controller(app)
    assert controller.service.update().status == "prepared"
    return app, controller.service.store, path, document


@pytest.mark.parametrize("fallback", (False, True))
def test_fresh_and_unchanged_get_share_work_but_keep_both_boundaries(
    landing, localized_server, passive_browser, monkeypatch, fallback,
):
    import skatmind.app_web.automatic_match_inventory as inventory
    import skatmind.app_web.automatic_session_inventory as sessions
    import skatmind.automatic_learning_store as storage
    from skatmind.app_web.automatic_match_learning import AutomaticMatchLearningServiceV1

    old, store, path, _document = landing
    before = {p: p.read_bytes() for p in old.managed_home.root.rglob("*") if p.is_file()}
    app = localized_server.app_context = AppWebContextV1.create(old.managed_home)
    observe_passive(monkeypatch)
    for name in ("build_mixed_bundle", "build_historical_bundle"):
        monkeypatch.setattr("skatmind.app_web.automatic_match_learning." + name,
                            lambda *a, **kw: pytest.fail("Passive preparation"))
    if fallback:
        monkeypatch.setattr(storage, "_DELIVERY_RECEIPT_MAX_OBJECTS", 1)
    counts = measure_work(monkeypatch, store)
    inspect, capture = AutomaticMatchLearningServiceV1._inspect, inventory._capture
    def inspected(service):
        counts["inspections"] += 1
        return inspect(service)
    def captured(root):
        counts["recording_inventory_captures"] += 1
        return capture(root)
    monkeypatch.setattr(AutomaticMatchLearningServiceV1, "_inspect", inspected)
    monkeypatch.setattr(inventory, "_capture", captured)
    monkeypatch.setattr(sessions, "_capture", captured)
    for first in (True, False):
        counts.clear()
        start = perf_counter()
        assert passive_browser.request("GET", "/learning")[0] == 200
        assert counts["inspections"] == 2
        expected_admissions = (4 if first else 2) if fallback else (2 if first else 0)
        assert counts["admissions"] == expected_admissions
        assert counts["retained_results_loaded"] == counts["admissions"]
        assert counts["object_reads"] > 0
        assert counts["reservations"] == counts["manifest_publications"] == 0
        assert not app.automatic_match_learning.store._coordinator.pins
        assert app.automatic_match_learning._installed is None
        print({"first_get": first, "fallback": fallback, "seconds": perf_counter() - start,
               "work": dict(counts)})
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert path.read_bytes() == before[path]


@pytest.mark.parametrize("change", ("source", "same_metadata", "manifest", "attempt",
                                   "installed", "store", "controller"))
@pytest.mark.parametrize("boundary", ("render", "headers"))
def test_landing_scope_never_authorizes_changed_final_delivery(
    empty_landing, localized_server, passive_browser, monkeypatch, change, boundary,
):
    import skatmind.app_web.automatic_learning_http as http
    from skatmind.app_web.automatic_learning_controller import AutomaticLearningController
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    from skatmind.automatic_learning_io import object_path
    from skatmind.automatic_learning_objects import manifest_bytes
    from skatmind.automatic_learning_store import AutomaticLearningStoreV1

    app, _archive, path, _document = empty_landing
    service = app.automatic_match_learning
    old_store = service.store
    manifest = old_store.snapshot().manifest
    other = AutomaticLearningStoreV1(old_store.root) if change == "store" else None
    observe_passive(monkeypatch)
    fired = []
    def mutate():
        if fired:
            return
        fired.append(True)
        assert old_store._coordinator.pins  # Pin survives rendering and the final header boundary.
        if change == "source":
            rewrite_same_metadata(path)
        elif change == "same_metadata":
            rewrite_same_metadata(object_path(old_store.root, manifest.current_generation))
        elif change == "manifest":
            (old_store.root / "manifest.json").write_bytes(manifest_bytes(
                replace(manifest, revision=manifest.revision + 1)))
        elif change == "attempt":
            service.attempt = object()
        elif change == "installed":
            service._installed = None
        elif change == "store":
            service.store = other
        else:
            app.automatic_learning_ui = AutomaticLearningController()
    if boundary == "render":
        original = http.render_entry
        def render(*args, **kwargs):
            result = original(*args, **kwargs)
            mutate()
            return result
        monkeypatch.setattr(http, "render_entry", render)
    else:
        original = Handler._send_bytes
        def send(handler, status, content, **kwargs):
            if handler.path == "/learning" and status == 200:
                mutate()
            return original(handler, status, content, **kwargs)
        monkeypatch.setattr(Handler, "_send_bytes", send)
    status, _headers, raw = passive_browser.request("GET", "/learning")
    assert fired == [True] and status == 409 and b"</html>" in raw
    assert not old_store._coordinator.pins


def test_landing_reader_pins_survive_actual_body_write(empty_landing, passive_browser, monkeypatch):
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler

    app, _archive, _path, _document = empty_landing
    original = Handler._headers
    seen = []
    def headers(handler, status, *args, **kwargs):
        if handler.path == "/learning" and status == 200:
            writer = handler.wfile
            class PinnedWriter:
                def write(self, raw):
                    assert app.automatic_match_learning.store._coordinator.pins
                    seen.append(True)
                    return writer.write(raw)

                def __getattr__(self, name):
                    return getattr(writer, name)
            handler.wfile = PinnedWriter()
        return original(handler, status, *args, **kwargs)
    monkeypatch.setattr(Handler, "_headers", headers)
    assert passive_browser.request("GET", "/learning")[0] == 200
    assert seen and not app.automatic_match_learning.store._coordinator.pins


def test_store_owner_changed_inside_final_validation_is_rejected(
    empty_landing, passive_browser, monkeypatch,
):
    from skatmind.automatic_learning_store import AutomaticLearningStoreV1

    app, old, _path, _document = empty_landing
    service = app.automatic_match_learning
    other = AutomaticLearningStoreV1(old.root)
    original = old._snapshot_for_delivery
    captures = []
    def snapshot(*args, **kwargs):
        result = original(*args, **kwargs)
        captures.append(True)
        if len(captures) == 2:
            service.store = other
        return result
    monkeypatch.setattr(old, "_snapshot_for_delivery", snapshot)
    status, _headers, raw = passive_browser.request("GET", "/learning")
    assert len(captures) == 2 and status == 409 and b"</html>" in raw
    assert not old._coordinator.pins
