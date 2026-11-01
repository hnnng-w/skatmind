"""Disposable storage fixtures; deliberately not genuine engine executions."""

from dataclasses import replace

from skatmind.automatic_learning_codec import canonical_json, fingerprint
from skatmind.automatic_learning_contracts import (
    REPORT_KINDS,
    SOURCE_KINDS,
    EvidenceEntryV1,
    GenerationV1,
    IdentityScopeV1,
    ManifestV1,
    NamedValueV1,
    SituationV1,
    SourceKeyV1,
    SourceRecordV1,
    SourceVersionV1,
)
from skatmind.automatic_learning_objects import StoredObjectV1


def source_fixture(*, name="source-a", family="match", content="first", revision=1):
    source = SourceKeyV1(family=family, product_id=name)
    payload = {"synthetic_content": content}
    obj = StoredObjectV1(
        area="sources", kind=SOURCE_KINDS[family], codec_version=1,
        payload=canonical_json(payload),
    )
    record = SourceRecordV1(
        source_version=SourceVersionV1(
            source=source, source_contract="synthetic_source", contract_version=1,
            content_fingerprint=fingerprint("synthetic_test_source", payload),
        ), object_ref=obj.reference, revision=revision,
        scope=IdentityScopeV1(kind="source_local", namespace=source.identity),
    )
    return record, obj


def evidence_fixture(source, obj, *, evidence_class="decision", run=1):
    family = source.source_version.source.family
    envelope = StoredObjectV1(
        area="reports", kind=REPORT_KINDS[(family, evidence_class)], codec_version=1,
        dependencies=(obj.reference,),
        payload=canonical_json({"synthetic_run": run, "not_a_genuine_report": True}),
    )
    situation = SituationV1(
        source_version_id=source.source_version.identity,
        game_id="frontend-historical-review", actor_id="frontend-forehand",
        decision_index=0, observed_card="CA", information_cutoff=0,
        checkpoint_fingerprint="1" * 64 if family == "session" else None,
        accepted_play_fingerprint="2" * 64 if family == "session" else None,
    )
    evidence = EvidenceEntryV1(
        evidence_class=evidence_class, source_version_id=source.source_version.identity,
        envelope=envelope.reference, situation=situation,
    )
    return evidence, envelope


def generation_fixture(sources, evidence, *, seed=0):
    value = GenerationV1(
        source_version_ids=tuple(source.source_version.identity for source in sources),
        evidence_ids=tuple(entry.identity for entry in evidence),
        exclusions=(), skipped_situations=(), corpus_id="synthetic-corpus",
        dataset_id="synthetic-dataset", catalog_revision=0, seed=seed,
        partition_weights=(70, 15, 15),
        adapter_versions=(NamedValueV1(name="synthetic", value="1"),),
        builder_versions=(NamedValueV1(name="synthetic", value="1"),),
        derived_fingerprints=(NamedValueV1(name="synthetic", value="3" * 64),),
    )
    refs = tuple(dict.fromkeys(
        [source.object_ref for source in sources] + [entry.envelope for entry in evidence]
    ))
    return StoredObjectV1(
        area="generations", kind="generation_descriptor", codec_version=1,
        payload=canonical_json(value.to_dict()), dependencies=refs,
    )


def indexed_manifest(store, *, generation=False):
    current = store.snapshot().manifest
    source, obj = source_fixture()
    evidence, envelope = evidence_fixture(source, obj)
    objects = [obj, envelope]
    if generation:
        objects.append(generation_fixture((source,), (evidence,)))
    for item in objects:
        store.publish_object(item)
    manifest = replace(
        current, revision=current.revision + 1, sources=(source,), evidence=(evidence,),
        objects=tuple(item.entry for item in objects),
        current_generation=objects[-1].reference if generation else None,
    )
    return manifest, tuple(objects)


def commit_fixture(store, *, generation=False):
    old = store.snapshot().manifest
    manifest, objects = indexed_manifest(store, generation=generation)
    assert store.update_manifest(manifest, expected_manifest=old.fingerprint).status == "saved"
    return manifest, objects


def manifest_wire_bytes(data):
    """Fingerprint wire data without constructing or serializing a typed manifest."""
    return canonical_json({
        "document_kind": "skatmind_automatic_learning_manifest", "version": 1,
        "content_fingerprint": fingerprint("manifest_v1", data), "manifest": data,
    }) + b"\n"


def mismatched_binding_fixture(case, *, space_id="synthetic", codec_version=1):
    """Keep objects/references exact; introduce the contradiction only in wire data."""
    source, obj = source_fixture()
    source_data = source.to_dict()
    if case == "source_kind":
        obj = replace(obj, kind="session_source", codec_version=codec_version)
        source_data["object_ref"] = obj.reference.to_dict()
        evidence_data, objects = [], (obj,)
        diagnostic = "Source family and stored kind disagree."
    elif case == "evidence_class":
        entry, envelope = evidence_fixture(source, obj)
        envelope = replace(envelope, codec_version=codec_version)
        entry_data = entry.to_dict()
        entry_data["envelope"] = envelope.reference.to_dict()
        entry_data["evidence_class"] = "rollout"
        evidence_data, objects = [entry_data], (obj, envelope)
        diagnostic = "Evidence family and stored kind disagree."
    else:
        raise ValueError("Unknown mismatch fixture case.")
    data = ManifestV1(space_id=space_id, revision=1).to_dict()
    data.update(sources=[source_data], evidence=evidence_data,
                objects=[obj.entry.to_dict() for obj in objects])
    return data, objects, diagnostic
