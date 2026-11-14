"""Fresh disposable publication and observed work for the two archive-cost modules."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
from time import perf_counter

from skatmind.automatic_learning_contracts import HistoricalReviewHeadV1, ManifestV1
from skatmind.automatic_learning_store import AutomaticLearningStoreV1, StoreConflictError


def _unique(values, key):
    retained = {}
    for value in values:
        identity = key(value)
        if identity in retained and retained[identity] != value:
            raise ValueError("Contradictory fixture duplicate.")
        retained.setdefault(identity, value)
    return tuple(retained.values())


def publish_fresh_archive(store, empty, candidates, *, live_historical=False):
    """Batch only an empty store; callers perform their necessary final strict admission."""
    before = empty.manifest
    if (before != ManifestV1(space_id=before.space_id) or empty.retained_bytes
            or empty.orphan_names or empty.temporary_names):
        raise ValueError("Fixture publication requires a fresh empty store.")
    objects = _unique((obj for value in candidates for obj in value.objects),
                      lambda obj: obj.reference.identity)
    sources = _unique((value.source for value in candidates),
                      lambda source: source.source_version.identity)
    evidence = _unique((value.evidence for value in candidates), lambda entry: entry.identity)
    heads = tuple(sorted((HistoricalReviewHeadV1(
        source=source.source_version.source, source_version_id=source.source_version.identity,
        evidence_id=entry.identity)
        for source in sources for entry in evidence
        if live_historical and source.source_version.source.family == "historical_review"
        and entry.source_version_id == source.source_version.identity),
        key=lambda head: head.source.identity))
    requested = replace(before, revision=1, objects=tuple(obj.entry for obj in objects),
                        sources=sources, evidence=evidence, historical_heads=heads)
    reservation = store.begin_candidate(objects)
    try:
        pending, published = list(objects), set()
        while pending:
            obj = next((obj for obj in pending if set(obj.dependencies) <= published), None)
            if obj is None:
                raise ValueError("Fixture dependencies are not closed and acyclic.")
            assert store.publish_object(obj, candidate=reservation) == "saved"
            published.add(obj.reference)
            pending.remove(obj)
        assert store.update_manifest(requested, expected_manifest=before.fingerprint,
                                     candidate=reservation).status == "saved"
    finally:
        try:
            store.release_candidate(reservation)
        except StoreConflictError:  # A successful CAS already released this exact reservation.
            pass
    return requested


def measure_work(monkeypatch, store):
    """Observe real reads/admission/publication, including new service owners of this root."""
    import skatmind.automatic_historical_evidence as historical
    import skatmind.automatic_learning_io as io
    import skatmind.automatic_match_evidence as match
    import skatmind.automatic_match_rollout_evidence as rollout
    import skatmind.automatic_session_evidence as session

    counts = Counter()
    read, admission = io.read_bounded, AutomaticLearningStoreV1._admission
    areas = tuple(store.root / area for area in ("sources", "reports", "generations"))

    def reading(path, limit):
        raw = read(path, limit)
        if path.parent in areas:
            counts["object_reads"] += 1
            counts["object_bytes"] += len(raw)
        return raw

    def admitting(owner, manifest, objects, storage):
        if owner.root == store.root:
            counts["admissions"] += 1
            counts["indexed_objects_admitted"] += len(manifest.objects)
        return admission(owner, manifest, objects, storage)

    def loader(original):
        def load(*args):
            value = original(*args)
            counts["retained_results_loaded"] += 1
            return value
        return load

    def publication(name, counter):
        original = getattr(AutomaticLearningStoreV1, name)
        def call(owner, *args, **kwargs):
            if owner.root == store.root:
                counts[counter] += 1
            return original(owner, *args, **kwargs)
        monkeypatch.setattr(AutomaticLearningStoreV1, name, call)

    monkeypatch.setattr(io, "read_bounded", reading)
    monkeypatch.setattr(AutomaticLearningStoreV1, "_admission", admitting)
    for module, name in ((match, "decode_match_decision"), (rollout, "decode_match_rollout"),
                         (session, "decode_session_execution"),
                         (historical, "decode_historical_execution")):
        monkeypatch.setattr(module, name, loader(getattr(module, name)))
    for name, counter in (("begin_candidate", "reservations"),
                          ("publish_object", "object_publications"),
                          ("update_manifest", "manifest_publications")):
        publication(name, counter)
    return counts


@contextmanager
def work_phase(monkeypatch, store, phase):
    with monkeypatch.context() as patch:
        counts = measure_work(patch, store)
        start = perf_counter()
        yield counts
        print({"phase": phase, "seconds": perf_counter() - start, "work": dict(counts)})
