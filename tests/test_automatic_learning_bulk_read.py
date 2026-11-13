"""Operation-local admission work with genuine retained evidence, never fake Reports."""

from collections import Counter
from time import perf_counter

import pytest
from test_automatic_historical_evidence import genuine_historical
from test_automatic_learning_delivery_receipt import rewrite_same_metadata
from test_automatic_match_evidence import commit_candidate, genuine_candidate, repack
from test_automatic_match_learning_evidence import forbid_execution
from test_automatic_session_evidence import genuine
from test_frontend_language_switching import localized_server

from skatmind.automatic_historical_evidence import build_historical_capture_candidate
from skatmind.automatic_learning_codec import decode_json
from skatmind.automatic_learning_store import (
    StoreConflictError,
    UnsupportedEvidenceError,
    initialize_automatic_learning_store_v1,
)

__all__ = ["genuine_historical", "localized_server"]


@pytest.fixture(scope="module")
def executions(tmp_path_factory, genuine_historical):
    start = perf_counter()
    session, _execution, _document = genuine(tmp_path_factory.mktemp("bulk-session"))
    draft, execution, native = genuine_historical
    values = (genuine_candidate(), genuine_candidate("bounded_search", decision=1), session,
              build_historical_capture_candidate("bulk-review", 0, execution, native, draft=draft))
    print({"fixture_creation_seconds": perf_counter() - start,
           "new_card_executions": 3, "historical_fixture_executions_separate": 1})
    return values


def measure_work(monkeypatch, store):
    """Count actual complete traversal bytes and successful typed retained-result loads."""
    import skatmind.automatic_historical_evidence as historical
    import skatmind.automatic_learning_io as io
    import skatmind.automatic_match_evidence as match
    import skatmind.automatic_session_evidence as session

    counts = Counter()
    read, admission = io.read_bounded, store._admission

    def reading(path, limit):
        raw = read(path, limit)
        if path.parent in tuple(store.root / area
                                for area in ("sources", "reports", "generations")):
            counts["object_reads"] += 1
            counts["object_bytes"] += len(raw)
        return raw

    def admitting(manifest, objects, storage):
        counts["admissions"] += 1
        counts["indexed_objects_admitted"] += len(manifest.objects)
        return admission(manifest, objects, storage)

    def loader(original):
        def load(*args):
            value = original(*args)
            counts["retained_results_loaded"] += 1
            return value
        return load

    monkeypatch.setattr(io, "read_bounded", reading)
    monkeypatch.setattr(store, "_admission", admitting)
    for module, name in ((match, "decode_match_decision"),
                         (session, "decode_session_execution"),
                         (historical, "decode_historical_execution")):
        monkeypatch.setattr(module, name, loader(getattr(module, name)))
    return counts


@pytest.fixture
def archived(tmp_path, executions, monkeypatch):
    store = initialize_automatic_learning_store_v1(tmp_path / "archive")
    start = perf_counter()
    with monkeypatch.context() as patch:
        counts = measure_work(patch, store)
        for value in executions:
            assert commit_candidate(store, value).status == "saved"
        snapshot = store.snapshot()
        print({"fixture_publication_seconds": perf_counter() - start, "work": dict(counts)})
    assert len(snapshot.available_evidence_ids) == 4
    return store, snapshot


@pytest.mark.parametrize("requested_count", (2, 4))
def test_bulk_work_and_original_results_match_single_reads(
    archived, monkeypatch, requested_count,
):
    store, snapshot = archived
    ids = tuple(reversed(snapshot.available_evidence_ids))[:requested_count]
    before_bytes = {p: p.read_bytes() for p in store.root.rglob("*") if p.is_file()}
    forbid_execution(monkeypatch)
    counts = measure_work(monkeypatch, store)
    start = perf_counter()
    singles = tuple(store.read_evidence(key) for key in ids)
    single_seconds, single_work = perf_counter() - start, dict(counts)
    counts.clear()
    start = perf_counter()
    bulk = store.read_evidence_many(ids, expected_manifest=snapshot.manifest.fingerprint)
    bulk_seconds = perf_counter() - start
    assert bulk == singles
    assert tuple(value.entry.identity for value in bulk) == ids
    assert tuple(value.downloads for value in bulk) == tuple(value.downloads for value in singles)
    assert counts["admissions"] == 1
    assert counts["indexed_objects_admitted"] == len(snapshot.manifest.objects)
    assert counts["retained_results_loaded"] == 4
    assert counts["object_reads"] == len(snapshot.manifest.objects)
    assert counts["object_bytes"] == sum(row.reference.size_bytes
                                         for row in snapshot.manifest.objects)
    assert single_work == {key: value * requested_count for key, value in counts.items()}
    assert {p: p.read_bytes() for p in store.root.rglob("*") if p.is_file()} == before_bytes
    print({"requested": requested_count, "single_work": single_work, "bulk_work": dict(counts),
           "single_seconds": single_seconds, "bulk_seconds": bulk_seconds})


@pytest.mark.parametrize("bound", ("_DELIVERY_RECEIPT_MAX_OBJECTS", "_DELIVERY_RECEIPT_MAX_BYTES"))
def test_large_archive_fallback_still_admits_every_requested_result(archived, monkeypatch, bound):
    import skatmind.automatic_learning_store as module

    store, snapshot = archived
    monkeypatch.setattr(module, bound, 1)  # Exercise the actual fallback without raising any cap.
    forbid_execution(monkeypatch)
    resumed, receipt = store._snapshot_for_delivery()
    assert receipt is None and resumed == snapshot
    counts = measure_work(monkeypatch, store)
    values = store.read_evidence_many(snapshot.available_evidence_ids,
                                     expected_manifest=snapshot.manifest.fingerprint)
    assert tuple(value.entry.identity for value in values) == snapshot.available_evidence_ids
    assert len(values) == 4 and counts["admissions"] == 1
    assert counts["retained_results_loaded"] == 4
    assert values[1].report.value.result.document["bounded_search_result"]["status"] == (
        "unavailable")
    print({"fallback": bound, "work": dict(counts)})


def test_actual_object_limit_fallback_is_complete_with_genuine_evidence(
    archived, genuine_historical, monkeypatch,
):
    from dataclasses import replace

    import skatmind.automatic_learning_store as module

    store, before = archived
    draft, execution, native = genuine_historical
    start = perf_counter()
    # Independent guided sources may retain equal original public IDs and bytes.
    # Publish one genuine batch through the normal reservation/object/CAS boundaries.
    candidates = tuple(build_historical_capture_candidate(
        "large-bulk-" + str(index), 0, execution, native, draft=draft) for index in range(30))
    objects = tuple(obj for candidate in candidates for obj in candidate.objects)
    reservation = store.begin_candidate(objects)
    for obj in objects:
        assert store.publish_object(obj, candidate=reservation) == "saved"
    manifest = replace(before.manifest, revision=before.manifest.revision + 1,
        objects=before.manifest.objects + tuple(obj.entry for obj in objects),
        sources=before.manifest.sources + tuple(candidate.source for candidate in candidates),
        evidence=before.manifest.evidence + tuple(candidate.evidence for candidate in candidates))
    assert store.update_manifest(manifest, expected_manifest=before.manifest.fingerprint,
                                 candidate=reservation).status == "saved"
    print({"large_fixture_publication_seconds": perf_counter() - start,
           "additional_card_executions": 0, "genuine_retained_bindings": len(candidates)})
    assert len(manifest.objects) == 67 > module._DELIVERY_RECEIPT_MAX_OBJECTS == 64
    assert sum(row.reference.size_bytes for row in manifest.objects) < (
        module._DELIVERY_RECEIPT_MAX_BYTES) == 16 * 1024 * 1024
    forbid_execution(monkeypatch)
    resumed, receipt = store._snapshot_for_delivery()
    assert receipt is None and resumed.manifest == manifest
    assert len(resumed.available_evidence_ids) == 34
    counts = measure_work(monkeypatch, store)
    ids = tuple(reversed(resumed.available_evidence_ids))
    values = store.read_evidence_many(ids, expected_manifest=manifest.fingerprint)
    assert tuple(value.entry.identity for value in values) == ids
    assert counts["admissions"] == 1 and counts["retained_results_loaded"] == 34
    assert counts["indexed_objects_admitted"] == counts["object_reads"] == 67
    for value in values[:30]:
        assert value.download("request")[1] == execution.request_json_bytes
        assert value.download("result")[1] == execution.result_json_bytes
    print({"production_object_limit_fallback_work": dict(counts)})


@pytest.mark.parametrize("damage", ("missing", "same_metadata", "unsupported"))
def test_bulk_failure_is_atomic_and_independent_evidence_stays_available(
    archived, executions, monkeypatch, damage,
):
    from skatmind import automatic_learning_io as io

    store, snapshot = archived
    bad = executions[0]
    if damage == "unsupported":
        bad = repack(bad, decode_json(bad.objects[1].payload), codec=99)
        assert commit_candidate(store, bad).status == "saved"
        snapshot = store.snapshot()
    else:
        path = io.object_path(store.root, bad.evidence.envelope)
        if damage == "missing":
            path.unlink()
        else:
            rewrite_same_metadata(path)
    forbid_execution(monkeypatch)
    good = executions[2].evidence.identity
    with pytest.raises(UnsupportedEvidenceError):
        store.read_evidence_many((good, bad.evidence.identity),
                                 expected_manifest=snapshot.manifest.fingerprint)
    with pytest.raises(UnsupportedEvidenceError):
        store.read_evidence(bad.evidence.identity)
    assert store.read_evidence_many((good,), expected_manifest=snapshot.manifest.fingerprint) == (
        store.read_evidence(good),)


def test_manifest_race_and_unindexed_ids_never_return_partial_bulk(archived, monkeypatch):
    from dataclasses import replace

    from skatmind.automatic_learning_objects import manifest_bytes

    store, snapshot = archived
    ids = snapshot.available_evidence_ids
    with pytest.raises(ValueError, match="not indexed"):
        store.read_evidence_many((*ids, "f" * 64), expected_manifest=snapshot.manifest.fingerprint)
    with pytest.raises(StoreConflictError):
        store.read_evidence_many(ids, expected_manifest="f" * 64)
    assert store.read_evidence_many((), expected_manifest=snapshot.manifest.fingerprint) == ()
    assert store.read_evidence_many((ids[0], ids[0]),
        expected_manifest=snapshot.manifest.fingerprint) == (store.read_evidence(ids[0]),) * 2
    original = store._admission
    def changed(*args):
        result = original(*args)
        (store.root / "manifest.json").write_bytes(manifest_bytes(
            replace(snapshot.manifest, revision=snapshot.manifest.revision + 1)))
        return result
    monkeypatch.setattr(store, "_admission", changed)
    with pytest.raises(StoreConflictError):
        store.read_evidence_many(ids, expected_manifest=snapshot.manifest.fingerprint)


@pytest.fixture
def consumer_archive(localized_server, executions, genuine_historical):
    from test_automatic_historical_learning import retain_fixture

    from skatmind.app_web.automatic_learning_controller import automatic_controller
    from skatmind.app_web.saved_match_analyses import archive_store

    app = localized_server.app_context
    store = archive_store(app, initialize=True)
    for candidate in executions[:3]:
        assert commit_candidate(store, candidate).status == "saved"
    # Two independent heads deliberately share the same genuine execution's public IDs.
    for _ in range(2):
        retain_fixture(app, genuine_historical)
    controller = automatic_controller(app)
    view = controller.capture()
    assert len(view.binding.resumed.available_evidence_ids) == 5
    return app, store, controller


def observe_bulk(monkeypatch, store, counts, *, delivery=False):
    name = "read_delivery_evidence_many" if delivery else "read_evidence_many"
    original = getattr(store, name)
    phases = []
    def bulk(ids, *args, **kwargs):
        before = counts.copy()
        values = original(ids, *args, **kwargs)
        phases.append((ids, counts - before))
        return values
    monkeypatch.setattr(store, name, bulk)
    return phases


@pytest.mark.parametrize("fallback", (False, True))
def test_native_lists_and_maintenance_use_one_bulk_phase_with_original_content(
    consumer_archive, localized_server, monkeypatch, fallback,
):
    import re
    from html import unescape

    from test_session_recorded_review_web import Browser

    import skatmind.automatic_learning_store as module
    from skatmind.app_web.saved_match_analyses import _caption

    app, archive, controller = consumer_archive
    if fallback:
        monkeypatch.setattr(module, "_DELIVERY_RECEIPT_MAX_OBJECTS", 1)
    original = archive.snapshot()
    values = archive.read_evidence_many(original.available_evidence_ids,
                                        expected_manifest=original.manifest.fingerprint)
    before_bytes = {p: p.read_bytes() for p in archive.root.rglob("*") if p.is_file()}
    forbid_execution(monkeypatch)
    monkeypatch.setattr("skatmind.automatic_learning_io.write_temporary",
                        lambda *a, **kw: pytest.fail("Passive archive mutation"))
    browser = Browser(localized_server)
    for family in ("match", "session", "historical_review"):
        store = controller.service.store if family == "historical_review" else archive
        with monkeypatch.context() as patch:
            counts = measure_work(patch, store)
            phases = observe_bulk(patch, store, counts,
                                  delivery=family == "historical_review" and not fallback)
            route = {"historical_review": "/review/saved", "match": "/matches/saved-analyses",
                     "session": "/sessions/saved-analyses"}[family]
            page = browser.page(route)
            selected = tuple(value for value in values
                             if value.source.record.source_version.source.family == family)
            assert len(phases) == 1
            assert phases[0][0] == tuple(value.entry.identity for value in selected)
            assert phases[0][1]["admissions"] == int(family != "historical_review" or fallback)
            assert phases[0][1]["retained_results_loaded"] == (
                5 * int(family != "historical_review" or fallback))
            for value in selected:
                assert _caption(value, "en") in unescape(page)
            if family == "historical_review":
                evidence_routes = re.findall(
                    r'href="(/review/saved/[a-f0-9]+/evidence/[0-9]+)"', page)
                assert len(re.findall(r'href="/review/saved/[a-f0-9]+/source/[0-9]+"', page)) == 2
                assert [path.rsplit("/", 1)[1] for path in evidence_routes] == ["0", "1"]
            else:
                evidence_routes = re.findall(r'href="(' + route + r'/[a-f0-9]+)"', page)
                assert evidence_routes == [route + "/" + app.saved_match_analyses.token(
                    original.manifest.space_id, value.entry) for value in selected]
            print({"consumer": family, "fallback": fallback, "operation_work": dict(counts),
                   "bulk_work": dict(phases[0][1])})
        for path, value in zip(evidence_routes, selected, strict=True):
            for kind in ("request", "result"):
                status, _headers, raw = browser.request("GET", path + "/" + kind + ".json")
                assert status == 200 and raw == value.download(kind)[1]

    view = controller.capture()
    with monkeypatch.context() as patch:
        store = controller.service.store
        counts = measure_work(patch, store)
        phases = observe_bulk(patch, store, counts)
        preview = controller.preview_cleanup(view, old_evidence=True)
        assert len(phases) == 1 and phases[0][1]["admissions"] == 1
        assert tuple(entry.identity for entry, _ in preview.evidence) == phases[0][0]
        assert tuple(value for _, value in preview.evidence) == values[:3]
        assert not store._coordinator.pins
        # Bulk pins have ended before the exact cleanup-consent epoch is captured.
        assert controller.require_confirmation(preview.token) is preview
        print({"consumer": "maintenance", "fallback": fallback,
               "bulk_work": dict(phases[0][1])})
    assert {p: p.read_bytes() for p in archive.root.rglob("*") if p.is_file()} == before_bytes


@pytest.mark.parametrize("fallback", (False, True))
def test_mixed_update_bulk_keeps_original_evidence_and_publication_checks(
    consumer_archive, monkeypatch, fallback,
):
    from test_automatic_match_learning import save

    import skatmind.automatic_learning_store as module
    from skatmind.automatic_match_evidence import decode_match_source
    from skatmind.automatic_session_evidence import decode_session_source
    from skatmind.session_persistence import save_session_persistence_file_v1

    app, archive, controller = consumer_archive
    before = archive.snapshot()
    for record in before.manifest.sources:
        if record.source_version.source.family == "match":
            source = decode_match_source(archive.read_object(record.object_ref), record)
            save(app, workspace=source.document.workspace)
        elif record.source_version.source.family == "session":
            source = decode_session_source(archive.read_object(record.object_ref), record)
            assert save_session_persistence_file_v1(
                app.managed_home.category("sessions").path / "session.json", source.document,
                expected_content_fingerprint=None).status == "saved"
    if fallback:
        monkeypatch.setattr(module, "_DELIVERY_RECEIPT_MAX_OBJECTS", 1)
    forbid_execution(monkeypatch)
    service = controller.service
    counts = measure_work(monkeypatch, service.store)
    phases = observe_bulk(monkeypatch, service.store, counts)
    assert service.update().status == "prepared"
    assert len(phases) == 1 and phases[0][1]["admissions"] == 1
    assert phases[0][1]["retained_results_loaded"] == 5
    assert phases[0][0] == tuple(sorted(before.available_evidence_ids))
    generation = service._installed.generation
    assert generation.recipe.evidence_ids == phases[0][0]
    assert len(service._installed.bundle.session_evidence) == 1
    assert len(service._installed.bundle.historical_evidence) == 2
    assert archive.snapshot().manifest.evidence == before.manifest.evidence
    print({"consumer": "update", "fallback": fallback, "bulk_work": dict(phases[0][1]),
           "operation_work": dict(counts)})


@pytest.mark.parametrize("family", ("match", "session", "historical_review"))
def test_list_bulk_values_do_not_authorize_corrupt_final_delivery(
    consumer_archive, localized_server, monkeypatch, family,
):
    from test_session_recorded_review_web import Browser

    from skatmind import automatic_learning_io as io

    _app, archive, controller = consumer_archive
    store = controller.service.store if family == "historical_review" else archive
    name = "read_delivery_evidence_many" if family == "historical_review" else "read_evidence_many"
    original = getattr(store, name)
    fired = []
    def changed(*args, **kwargs):
        values = original(*args, **kwargs)
        rewrite_same_metadata(io.object_path(store.root, values[0].entry.envelope))
        fired.append(True)
        return values
    monkeypatch.setattr(store, name, changed)
    forbid_execution(monkeypatch)
    route = {"match": "/matches/saved-analyses", "session": "/sessions/saved-analyses",
             "historical_review": "/review/saved"}[family]
    response = Browser(localized_server).request("GET", route)
    assert fired == [True] and response[0] == 409 and b"</html>" in response[2]
