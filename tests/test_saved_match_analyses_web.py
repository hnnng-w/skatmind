"""Native HTTP archive workflow; every recording is disposable synthetic data."""

import re
from collections import Counter
from html import unescape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_match_rollout_web import downloads, open_alex
from test_session_recorded_review_web import Forms

from skatmind.app_web.saved_match_analyses import SAVED_MATCH_ROUTE
from skatmind.app_web.stateful_localization import text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def saved_route(page):
    return re.findall(r'href="(/matches/saved-analyses/[0-9a-f]{64})"', page)[0]


def _live_quick(server, rollout=False):
    from test_match_rollout_web import form

    browser, path, page = open_alex(server)
    original = path.read_bytes()
    native = form(page) if rollout else operation_form(page, "analyze_decision")
    response = browser.submit(native, settings_mode="ordinary", analysis_effort="quick",
                              **({"objective": "played_game_goal"} if rollout else {}))
    assert response[0] == 303
    return browser, path, original, response[1]["location"]


@pytest.mark.parametrize("rollout", (False, True))
def test_live_quick_receipt_is_response_local_and_fresh_at_headers(
    localized_server, monkeypatch, rollout,
):
    from learning_archive_fixture_helpers import measure_work
    from test_automatic_match_learning_evidence import forbid_execution

    from skatmind.app_web.saved_match_analyses import archive_store

    browser, path, original, route = _live_quick(localized_server, rollout)
    store = archive_store(localized_server.app_context)
    manifest = store.snapshot().manifest
    entry, = manifest.evidence
    saved = store.read_evidence(entry.identity)
    forbid_execution(monkeypatch)
    for _ in range(2):
        with monkeypatch.context() as patch:
            work = measure_work(patch, store)
            page = browser.page(route)
            assert work["admissions"] == work["retained_results_loaded"] == 1
            assert work["object_reads"] == 4 * len(manifest.objects)
            assert work["manifest_publications"] == work["object_publications"] == 0
        assert text("en", "saved_analysis." + ("rollout." if rollout else "") + "saved") in page
        outputs = downloads(browser, page).values()
        # Live Immediate offers Result and Strategy source; rollout offers Request and Result.
        assert saved.download("result")[1] in outputs
        if rollout:
            assert saved.download("request")[1] in outputs
        assert path.read_bytes() == original


@pytest.mark.parametrize("change", ("corruption", "selection", "report", "archive_owner"))
def test_live_match_refuses_changed_authority_at_final_receipt_check(
    localized_server, monkeypatch, change,
):
    from test_automatic_learning_delivery_receipt import rewrite_same_metadata
    from test_automatic_match_learning_evidence import forbid_execution

    from skatmind import automatic_learning_io as io
    from skatmind.app_web.saved_match_analyses import SavedMatchAnalyses, archive_store

    browser, path, original, route = _live_quick(localized_server)
    app = localized_server.app_context
    store = archive_store(app)
    active = app.managed_stateful.active_match
    ref = store.snapshot().manifest.evidence[0].envelope
    read = store._snapshot_for_delivery
    fired = []
    def changed(receipt=None):
        if receipt is None:
            return read()
        assert receipt.owner is store.owner
        fired.append(True)
        if change == "corruption":
            rewrite_same_metadata(io.object_path(store.root, ref))
        result = read(receipt)
        if change == "selection":
            active.review_decision_generation += 1
        elif change == "report":
            active.capture.report_store.clear()
        elif change == "archive_owner":
            app.saved_match_analyses = SavedMatchAnalyses(store=store)
        return result
    forbid_execution(monkeypatch)
    monkeypatch.setattr(store, "_snapshot_for_delivery", changed)
    status, _, raw = browser.request("GET", route)
    assert status == 409 and fired == [True]
    assert text("en", "saved_analysis.saved") not in unescape(raw.decode())
    assert path.read_bytes() == original


def test_live_quick_genuine_above_limit_fully_admits_at_capture_and_headers(
    localized_server, monkeypatch,
):
    from learning_archive_fixture_helpers import measure_work, publish_fresh_archive
    from test_automatic_historical_evidence import genuine_historical
    from test_automatic_match_learning_evidence import forbid_execution

    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_historical_evidence import build_historical_capture_candidate

    store = archive_store(localized_server.app_context, initialize=True)
    # Reuse a genuine execution under distinct disposable source identities.
    draft, execution, native = genuine_historical.__wrapped__()
    publish_fresh_archive(store, store.snapshot(), tuple(build_historical_capture_candidate(
        f"above-{i}", 0, execution, native, draft=draft) for i in range(32)))
    browser, path, original, route = _live_quick(localized_server)
    snapshot = store.snapshot()
    assert len(snapshot.manifest.objects) == 66 and len(snapshot.available_evidence_ids) == 33
    forbid_execution(monkeypatch)
    work = measure_work(monkeypatch, store)
    page = browser.page(route)
    assert text("en", "saved_analysis.saved") in page
    assert (work["admissions"], work["retained_results_loaded"]) == (2, 66)
    assert work["object_reads"] == 132 and work["object_bytes"] == 2 * snapshot.retained_bytes
    assert not work["object_publications"] and not work["manifest_publications"]
    assert path.read_bytes() == original


def test_native_genuine_capture_and_saved_downloads(localized_server):
    browser, path, page = open_alex(localized_server)
    before = path.read_bytes()
    response = browser.submit(operation_form(page, "analyze_decision"), immediate_sample_count="1")
    assert response[0] == 303, response[2].decode()
    live = follow(browser, response)
    assert text("en", "saved_analysis.saved") in unescape(live)
    originals = downloads(browser, live)
    listing = browser.page(SAVED_MATCH_ROUTE)
    assert '_frontend_language_context' in listing
    for locale in ("de", "en"):
        listing = follow(browser, browser.submit(Forms(listing).find("/actions/profile/language"),
                                                 language=locale))
        assert text(locale, "saved_analysis.title") in unescape(listing)
    route = saved_route(listing)
    saved = browser.page(route)
    assert text("en", "saved_analysis.historical") in unescape(saved)
    for locale in ("de", "en"):
        saved = follow(browser, browser.submit(Forms(saved).find("/actions/profile/language"),
                                               language=locale))
        assert text(locale, "saved_analysis.title") in unescape(saved)
    assert browser.request("GET", route + "/result.json")[2] == next(
        raw for name, raw in originals.items() if "strategy-source" not in name)
    assert browser.request("GET", route + "/strategy-source.json")[2] == next(
        raw for name, raw in originals.items() if "strategy-source" in name)
    assert browser.request("GET", route + "/request.json")[0] == 200
    assert path.read_bytes() == before


def test_native_save_only_retry_counts_exact_writes(localized_server, monkeypatch):
    import skatmind.automatic_learning_io as io
    import skatmind.match_decision_analysis as engine
    from skatmind.app_web.saved_match_analyses import RETRY_MATCH_ROUTE, archive_store
    browser, path, page = open_alex(localized_server)
    app = localized_server.app_context
    store = archive_store(app, initialize=True)  # Deliberate fixture initialization.
    counts = Counter()
    real_write, real_execute = io.write_temporary, engine.execute_application_invocation
    failing = True
    def write(directory, raw):
        if directory.name == "reports" and failing:
            counts["controlled_failure"] += 1
            raise OSError("External test harness failure")
        counts[directory.name] += 1
        return real_write(directory, raw)
    def evaluate(*args, **kwargs):
        counts["evaluate"] += 1
        return real_execute(*args, **kwargs)
    monkeypatch.setattr(io, "write_temporary", write)
    monkeypatch.setattr(engine, "execute_application_invocation", evaluate)
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                          immediate_sample_count="1"))
    assert text("en", "saved_analysis.unsaved") in unescape(page)
    retry = Forms(page).find(RETRY_MATCH_ROUTE)
    live = downloads(browser, page)
    assert counts == {"evaluate": 1, "sources": 1, "controlled_failure": 1}
    failing = False
    page = follow(browser, browser.submit(retry))
    assert text("en", "saved_analysis.saved") in unescape(page)
    assert downloads(browser, page) == live
    assert counts == {"evaluate": 1, "sources": 1, "controlled_failure": 1,
                      "reports": 1, "automatic-learning": 1}
    assert len(store.snapshot().manifest.evidence) == 1
    assert browser.submit(retry)[0] == 409


def test_already_expired_immediate_retry_does_not_drop_final_guard(localized_server, monkeypatch):
    from skatmind.app_web.saved_match_analyses import archive_store

    browser, _, page = open_alex(localized_server)
    app = localized_server.app_context
    store = archive_store(app, initialize=True)
    monkeypatch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
    response = browser.submit(operation_form(page, "analyze_decision"), immediate_sample_count="1")
    assert response[0] == 303
    active = app.managed_stateful.active_match
    assert active.pending_evidence is not None
    active.rollout_attempt = object()
    status, _, raw = browser.request("GET", response[1]["location"])
    assert status == 409 and b'action="/matches/retry-saving"' not in raw


def test_passive_absent_store_does_not_initialize(localized_server, monkeypatch):
    from test_session_recorded_review_web import Browser

    import skatmind.automatic_learning_io as io
    browser = Browser(localized_server)
    root = localized_server.app_context.managed_home.root / "automatic-learning"
    monkeypatch.setattr(io, "write_temporary", lambda *a, **kw: pytest.fail("Passive write"))
    assert text("en", "saved_analysis.empty") in unescape(browser.page(SAVED_MATCH_ROUTE))
    assert not root.exists()


def test_rollout_enters_separate_family_and_rejects_ordinary_teacher(localized_server):
    from test_match_rollout_web import form

    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.automatic_match_evidence import build_match_capture_candidate
    from skatmind.learning_corpus_strategy_teacher_builder import validate_original_match_teacher_v1
    from skatmind.match_analysis_report_source_export import (
        build_match_analysis_report_source_export_v1,
    )

    browser, path, page = open_alex(localized_server)
    response = browser.submit(form(page), objective="played_game_goal", requested_worlds="1")
    assert response[0] == 303
    store = archive_store(localized_server.app_context)
    assert store is not None
    entry, = store.snapshot().manifest.evidence
    assert entry.evidence_class == "rollout" and entry.envelope.kind == "match_rollout"
    value = store.read_evidence(entry.identity)
    with pytest.raises(ValueError):
        build_match_analysis_report_source_export_v1(value.report)
    with pytest.raises(ValueError):
        validate_original_match_teacher_v1(value.report, value.source.snapshot)
    with pytest.raises(ValueError):
        build_match_capture_candidate(value.source.document, value.report,
                                      value.invocation, value.execution)


def test_restart_and_reload_preserve_original_and_expire_live_urls(localized_server, monkeypatch):
    from test_session_recorded_review_web import Browser

    import skatmind.automatic_learning_io as io
    import skatmind.match_decision_analysis as engine
    from skatmind.app_web.context import AppWebContextV1
    from skatmind.app_web.match_frontend import reload_unified_match_v1
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                          immediate_sample_count="1"))
    live = downloads(browser, page)
    old_route = saved_route(browser.page(SAVED_MATCH_ROUTE))
    originals = {kind: browser.request("GET", old_route + "/" + kind + ".json")[2]
                 for kind in ("request", "result", "strategy-source")}
    app = localized_server.app_context
    reload_unified_match_v1(app.managed_stateful.active_match)
    assert all(browser.request("GET", route)[0] == 404 for route in live)
    assert browser.request("GET", old_route)[0] == 200
    before = {p: p.read_bytes() for p in app.managed_home.root.rglob("*.json")}
    localized_server.app_context = AppWebContextV1.create(app.managed_home)
    fresh = Browser(localized_server)
    monkeypatch.setattr(engine, "execute_application_invocation",
                        lambda *a, **kw: pytest.fail("Passive evaluation"))
    monkeypatch.setattr(io, "write_temporary",
                        lambda *a, **kw: pytest.fail("Passive archive write"))
    assert fresh.request("GET", old_route)[0] == 409
    route = saved_route(fresh.page(SAVED_MATCH_ROUTE))
    assert route != old_route
    assert fresh.request("GET", route)[0] == 200
    for kind, raw in originals.items():
        assert fresh.request("GET", route + "/" + kind + ".json")[2] == raw
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("resource", ("", "/result.json"))
@pytest.mark.parametrize("change", ("archive_owner", "archive_source", "live_source"))
def test_final_delivery_rechecks_archive_owner_and_closure(
    localized_server, monkeypatch, resource, change,
):
    from skatmind.app_web.saved_match_analyses import SavedMatchAnalyses, archive_store
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    browser, path, page = open_alex(localized_server)
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                          immediate_sample_count="1"))
    route = saved_route(browser.page(SAVED_MATCH_ROUTE))
    app = localized_server.app_context
    store = archive_store(app)
    source = store.snapshot().manifest.sources[0].object_ref
    real = Handler._send_bytes
    fired = False
    def send(handler, status, content, **kwargs):
        nonlocal fired
        if not fired and handler.path == route + resource:
            fired = True
            if change == "archive_owner":
                app.saved_match_analyses = SavedMatchAnalyses()
            elif change == "archive_source":
                (store.root / source.area / (source.fingerprint + ".json")).write_bytes(b"{}")
            else:
                path.unlink()  # Deliberate missing live recording; archive stays historical.
        return real(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", send)
    response = browser.request("GET", route + resource)
    assert fired and response[0] == (200 if change == "live_source" else 409)


@pytest.mark.parametrize("change", ("source", "owner", "selection", "attempt"))
def test_pending_receipt_is_not_delivered_after_authority_changes(
    localized_server, monkeypatch, change,
):
    from dataclasses import replace

    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
    browser, path, page = open_alex(localized_server)
    app = localized_server.app_context
    store = archive_store(app, initialize=True)
    with monkeypatch.context() as patch:
        patch.setattr(store, "publish_object", lambda *a, **kw: "conflict")
        response = browser.submit(operation_form(page, "analyze_decision"),
                                  immediate_sample_count="1")
    route = response[1]["location"]
    active = app.managed_stateful.active_match
    real = Handler._send_bytes
    fired = False
    def send(handler, status, content, **kwargs):
        nonlocal fired
        if not fired and handler.path == route:
            fired = True
            if change == "source":
                path.unlink()
            elif change == "owner":
                app.managed_stateful.activate_match(replace(active, handle="b" * 64))
            elif change == "selection":
                active.review_decision_generation += 1
            else:
                active.rollout_attempt = object()
        return real(handler, status, content, **kwargs)
    monkeypatch.setattr(Handler, "_send_bytes", send)
    response = browser.request("GET", route)
    assert fired and response[0] == 409
    assert text("en", "saved_analysis.unsaved") not in unescape(response[2].decode())


def test_exact_older_saved_selection_survives_live_eviction(localized_server):
    from skatmind.app_web.saved_match_analyses import archive_store
    from skatmind.match_analysis_contracts import (
        MatchDecisionAnalysisOptionsV1,
        build_match_analysis_report_v1,
    )
    from skatmind.match_decision_analysis import execute_match_decision_analysis_v1

    browser, path, page = open_alex(localized_server)
    first = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                           immediate_sample_count="1"))
    old_route = saved_route(browser.page(SAVED_MATCH_ROUTE))
    original = browser.request("GET", old_route + "/result.json")[2]
    second = follow(browser, browser.submit(operation_form(first, "analyze_decision"),
                                            immediate_sample_count="1", immediate_random_seed="2"))
    assert second != first
    active = localized_server.app_context.managed_stateful.active_match
    # Genuine non-executed availability reports evict the live list. Generic put
    # is not a durable producer hook, even when it accepts an applied report.
    for index in range(1, 10):
        value = execute_match_decision_analysis_v1(active.workspace, match_position=1,
            decision_index=index, options=MatchDecisionAnalysisOptionsV1())
        assert value.status == "unavailable"
        active.capture.report_store.put(build_match_analysis_report_v1(value))
    assert len(archive_store(localized_server.app_context).snapshot().manifest.evidence) == 2
    assert browser.request("GET", old_route + "/result.json")[2] == original
    assert browser.request("GET", old_route)[0] == 200
    for route in downloads(browser, first):
        assert browser.request("GET", route)[0] == 404
