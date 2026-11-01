from dataclasses import FrozenInstanceError, replace

import pytest
from automatic_learning_helpers import (
    evidence_fixture,
    generation_fixture,
    manifest_wire_bytes,
    mismatched_binding_fixture,
    source_fixture,
)

from skatmind.automatic_learning_codec import canonical_json, decode_json, fingerprint
from skatmind.automatic_learning_contracts import (
    AUTOMATIC_LEARNING_MAX_CANDIDATES_PER_OWNER,
    AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS,
    AUTOMATIC_LEARNING_MAX_GENERATIONS,
    AUTOMATIC_LEARNING_MAX_OBJECT_BYTES,
    AUTOMATIC_LEARNING_MAX_TOTAL_BYTES,
    EntityReferenceV1,
    EvidenceEntryV1,
    ExclusionV1,
    IdentityScopeV1,
    ManifestV1,
    ObjectEntryV1,
    OriginBindingV1,
    SourceRecordV1,
)
from skatmind.automatic_learning_objects import (
    StoredObjectV1,
    manifest_bytes,
    resume_manifest,
    validate_generation,
)
from skatmind.automatic_learning_store import StoreLimitsV1


def manifest_fixture():
    source, obj = source_fixture()
    evidence, envelope = evidence_fixture(source, obj)
    return ManifestV1(space_id="synthetic", sources=(source,), evidence=(evidence,),
                      objects=(obj.entry, envelope.entry))


def test_production_constants_are_independently_exact():
    assert AUTOMATIC_LEARNING_MAX_OBJECT_BYTES == 16_777_216
    assert AUTOMATIC_LEARNING_MAX_TOTAL_BYTES == 536_870_912
    assert AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS == 2048
    assert AUTOMATIC_LEARNING_MAX_GENERATIONS == 2
    assert AUTOMATIC_LEARNING_MAX_CANDIDATES_PER_OWNER == 1
    assert StoreLimitsV1() == StoreLimitsV1(
        object_bytes=16_777_216, total_bytes=536_870_912, evidence_per_class=2048,
    )


def test_strict_canonical_roundtrip_and_immutable_records():
    manifest = manifest_fixture()
    raw = manifest_bytes(manifest)
    assert resume_manifest(raw) == manifest
    assert manifest_bytes(resume_manifest(raw)) == raw
    assert raw.endswith(b"\n") and b"\r" not in raw
    with pytest.raises(FrozenInstanceError):
        manifest.sources = ()
    copied = manifest.to_dict()
    copied["sources"].clear()
    assert len(manifest.sources) == 1


@pytest.mark.parametrize("raw", [
    b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
    b'{"x":1e999}', b'[]', b'null', b'\xef\xbb\xbf{}', b'\xff', b'{',
])
def test_strict_json_rejection(raw):
    with pytest.raises(ValueError):
        decode_json(raw)


@pytest.mark.parametrize("value", [
    float("nan"), float("inf"), {1: "invalid"}, (1,), {"x": object()},
])
def test_finite_json_encoder_rejects_non_json(value):
    with pytest.raises(ValueError):
        canonical_json(value)


@pytest.mark.parametrize("field,value", [
    ("version", True), ("version", 2), ("version", 1.0), ("revision", False),
    ("revision", -1), ("sources", {}), ("space_id", " padded "), ("space_id", 1),
])
def test_manifest_wrong_types_and_versions(field, value):
    document = manifest_fixture().to_dict()
    document[field] = value
    with pytest.raises(ValueError):
        ManifestV1.from_dict(document)


@pytest.mark.parametrize("operation", ["unknown", "missing", "nested_unknown", "fingerprint"])
def test_closed_fields_and_manifest_fingerprint(operation):
    document = decode_json(manifest_bytes(manifest_fixture()))
    if operation == "unknown":
        document["extra"] = 1
    elif operation == "missing":
        del document["manifest"]["revision"]
    elif operation == "nested_unknown":
        document["manifest"]["sources"][0]["scope"]["label"] = "Player"
    else:
        document["content_fingerprint"] = "0" * 64
    with pytest.raises(ValueError):
        resume_manifest(canonical_json(document))


def test_source_version_is_content_and_contract_bound_not_revision_or_label():
    first, _ = source_fixture(content="first", revision=7)
    corrected, _ = source_fixture(content="second", revision=7)
    assert first.source_version.identity != corrected.source_version.identity
    assert replace(first, revision=3).source_version.identity == first.source_version.identity
    changed_contract = replace(first.source_version, contract_version=2)
    assert changed_contract.identity != first.source_version.identity
    other, _ = source_fixture(name="another", content="first", revision=7)
    assert other.source_version.identity != first.source_version.identity
    assert fingerprint("one", {}) != fingerprint("two", {})


def test_guided_placeholders_remain_independent_source_local_namespaces():
    first, _ = source_fixture(name="review-a", family="historical_review")
    second, _ = source_fixture(name="review-b", family="historical_review")
    entities = tuple(EntityReferenceV1(
        source=source.source_version.source, scope=source.scope, entity_kind="player",
        original_id="frontend-forehand",
    ) for source in (first, second))
    assert entities[0] != entities[1]
    assert entities[0].original_id == entities[1].original_id
    with pytest.raises(ValueError, match="namespace"):
        replace(entities[0], scope=second.scope)
    # Imported placeholder-like IDs stay explicit shared claims, never inferred guided origins.
    imported = replace(entities[0], scope=IdentityScopeV1(kind="shared_claim", namespace="import"))
    assert imported != entities[0]
    assert "origin" not in imported.to_dict()


def test_origin_binding_requires_proof_and_explicit_compatible_endpoints():
    first, obj = source_fixture(name="review-a", family="historical_review")
    second, _ = source_fixture(name="review-b", family="historical_review")
    subject, target = tuple(EntityReferenceV1(
        source=source.source_version.source, scope=source.scope, entity_kind="player",
        original_id="frontend-forehand",
    ) for source in (first, second))
    binding = OriginBindingV1(kind="cross_source_player", subject=subject, target=target,
                             proof=obj.reference, validator="future_binding", validator_version=1)
    assert OriginBindingV1.from_dict(binding.to_dict()) == binding
    for changes in ({"target": None}, {"target": subject}, {"proof": None},
                    {"kind": "cross_source_game"}, {"validator_version": True}):
        with pytest.raises(ValueError):
            replace(binding, **changes)


@pytest.mark.parametrize("field", ["sources", "evidence", "objects", "exclusions", "bindings"])
def test_duplicate_manifest_identities_are_rejected(field):
    manifest = manifest_fixture()
    if field == "exclusions":
        manifest = replace(manifest, exclusions=(ExclusionV1(
            source=manifest.sources[0].source_version.source, reason="explicit",
        ),))
    elif field == "bindings":
        source, obj = source_fixture(family="historical_review")
        entity = EntityReferenceV1(source=source.source_version.source, scope=source.scope,
                                   entity_kind="player", original_id="player")
        binding = OriginBindingV1(kind="guided_producer", subject=entity, target=None,
                                  proof=obj.reference, validator="future", validator_version=1)
        manifest = ManifestV1(space_id="synthetic", sources=(source,), objects=(obj.entry,),
                              bindings=(binding,))
    with pytest.raises(ValueError, match="Duplicate"):
        replace(manifest, **{field: getattr(manifest, field) * 2})


def test_checked_references_reject_missing_original_objects_and_orphan_index():
    manifest = manifest_fixture()
    for changes in ({"sources": ()}, {"objects": manifest.objects[1:]}, {"evidence": ()}):
        with pytest.raises(ValueError):
            replace(manifest, **changes)
    bad = replace(manifest.objects[1], dependencies=())
    with pytest.raises(ValueError, match="original source"):
        replace(manifest, objects=(manifest.objects[0], bad))


def test_generation_exact_sources_evidence_and_dependencies():
    manifest = manifest_fixture()
    generation = generation_fixture(manifest.sources, manifest.evidence)
    assert validate_generation(generation, manifest).seed == 0
    with pytest.raises(ValueError, match="dependencies"):
        validate_generation(replace(generation, dependencies=()), manifest)
    corrected, obj = source_fixture(content="correction")
    extended = replace(manifest, sources=(*manifest.sources, corrected),
                       objects=(*manifest.objects, obj.entry))
    both = generation_fixture(extended.sources, extended.evidence)
    with pytest.raises(ValueError, match="one version"):
        validate_generation(both, extended)


@pytest.mark.parametrize("changes", [{"version": True}, {"codec_version": False},
                                     {"area": "../sources"}, {"payload": b'{ "x":1 }'}])
def test_storage_envelope_strictness(changes):
    _, obj = source_fixture()
    with pytest.raises(ValueError):
        replace(obj, **changes)
    assert StoredObjectV1.from_bytes(obj.raw) == obj


@pytest.mark.parametrize("case", ("source_kind", "evidence_class"))
def test_known_binding_mismatch_rejected_by_manifest_construction(case):
    data, _objects, diagnostic = mismatched_binding_fixture(case)
    # Build the typed entries separately to exercise the manifest's cross-record boundary.
    sources = tuple(SourceRecordV1.from_dict(item) for item in data["sources"])
    evidence = tuple(EvidenceEntryV1.from_dict(item) for item in data["evidence"])
    objects = tuple(ObjectEntryV1.from_dict(item) for item in data["objects"])
    with pytest.raises(ValueError) as error:
        ManifestV1(space_id=data["space_id"], revision=1, sources=sources,
                   evidence=evidence, objects=objects)
    assert str(error.value) == diagnostic


@pytest.mark.parametrize("case", ("source_kind", "evidence_class"))
@pytest.mark.parametrize("codec_version", (1, 999))
def test_known_binding_mismatch_rejected_by_strict_codec(case, codec_version):
    data, _objects, diagnostic = mismatched_binding_fixture(case, codec_version=codec_version)
    raw = manifest_wire_bytes(data)
    wire = decode_json(raw)
    assert wire["content_fingerprint"] == fingerprint("manifest_v1", wire["manifest"])
    for load in (lambda: ManifestV1.from_dict(data), lambda: resume_manifest(raw)):
        with pytest.raises(ValueError) as error:
            load()
        assert str(error.value) == diagnostic
