"""Storage envelopes preserve finite JSON without claiming genuine execution."""

from __future__ import annotations

from dataclasses import dataclass

from .automatic_learning_codec import canonical_json, decode_json, fingerprint, integer, text
from .automatic_learning_contracts import (
    OBJECT_AREAS,
    GenerationV1,
    ManifestV1,
    ObjectEntryV1,
    ObjectRefV1,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredObjectV1:
    area: str
    kind: str
    codec_version: int
    payload: bytes
    dependencies: tuple[ObjectRefV1, ...] = ()
    version: int = 1

    def __post_init__(self):
        if type(self.version) is not int or self.version != 1 or self.area not in OBJECT_AREAS:
            raise ValueError("Unsupported storage envelope.")
        text(self.kind)
        integer(self.codec_version, 1)
        if canonical_json(decode_json(self.payload)) != self.payload:
            raise ValueError("Storage payload must be canonical finite JSON bytes.")
        if type(self.dependencies) is not tuple or any(
            type(ref) is not ObjectRefV1 for ref in self.dependencies
        ):
            raise ValueError("Dependencies must be exact immutable references.")
        if len(set(ref.identity for ref in self.dependencies)) != len(self.dependencies):
            raise ValueError("Duplicate dependency identities.")

    def to_dict(self):
        return {
            "version": self.version, "area": self.area, "kind": self.kind,
            "codec_version": self.codec_version,
            "dependencies": [ref.to_dict() for ref in self.dependencies],
            "payload": decode_json(self.payload),
        }

    @property
    def raw(self):
        return canonical_json(self.to_dict()) + b"\n"

    @property
    def reference(self):
        return ObjectRefV1(
            area=self.area, kind=self.kind, codec_version=self.codec_version,
            fingerprint=fingerprint("object_v1", self.to_dict()), size_bytes=len(self.raw),
        )

    @property
    def entry(self):
        return ObjectEntryV1(reference=self.reference, dependencies=self.dependencies)

    @classmethod
    def from_bytes(cls, raw: bytes):
        data = decode_json(raw)
        if set(data) != {"version", "area", "kind", "codec_version", "dependencies", "payload"}:
            raise ValueError("Invalid storage envelope fields.")
        if type(data["dependencies"]) is not list or type(data["payload"]) is not dict:
            raise ValueError("Invalid storage envelope shape.")
        data["dependencies"] = tuple(ObjectRefV1.from_dict(ref) for ref in data["dependencies"])
        data["payload"] = canonical_json(data["payload"])
        result = cls(**data)
        if raw != result.raw:
            raise ValueError("Stored objects must retain canonical bytes.")
        return result


def manifest_bytes(manifest: ManifestV1) -> bytes:
    manifest = ManifestV1.from_dict(manifest.to_dict())
    return canonical_json({
        "document_kind": "skatmind_automatic_learning_manifest",
        "version": 1, "content_fingerprint": manifest.fingerprint,
        "manifest": manifest.to_dict(),
    }) + b"\n"


def resume_manifest(raw: bytes) -> ManifestV1:
    data = decode_json(raw)
    if (set(data) != {"document_kind", "version", "content_fingerprint", "manifest"}
            or data["document_kind"] != "skatmind_automatic_learning_manifest"
            or type(data["version"]) is not int or data["version"] != 1):
        raise ValueError("Invalid Automatic Learning manifest. Restore a known-valid copy.")
    manifest = ManifestV1.from_dict(data["manifest"])
    if data["content_fingerprint"] != manifest.fingerprint:
        raise ValueError("Invalid Automatic Learning manifest fingerprint.")
    return manifest


def validate_generation(obj: StoredObjectV1, manifest: ManifestV1) -> GenerationV1:
    if obj.kind != "generation_descriptor" or obj.codec_version not in (1, 2, 3):
        raise ValueError("Unsupported generation descriptor.")
    data = decode_json(obj.payload)
    # Codec 2 adds the S4 input ledger. This remains structural validation only;
    # automatic_match_preparation.admit_generation owns semantic authorization.
    generation = GenerationV1.from_dict(data if obj.codec_version == 1 else data["recipe"])
    sources = {entry.source_version.identity: entry for entry in manifest.sources}
    evidence = {entry.identity: entry for entry in manifest.evidence}
    if (set(generation.source_version_ids) - sources.keys()
            or set(generation.evidence_ids) - evidence.keys()):
        raise ValueError("Generation references must be retained in the manifest.")
    selected = [sources[key] for key in generation.source_version_ids]
    if len({entry.source_version.source for entry in selected}) != len(selected):
        raise ValueError("A generation may select only one version of each logical source.")
    if any(evidence[key].source_version_id not in generation.source_version_ids
           for key in generation.evidence_ids):
        raise ValueError("Generation evidence escaped its exact source selection.")
    if {entry.source for entry in generation.exclusions} & {
        entry.source_version.source for entry in selected
    }:
        raise ValueError("A generation cannot include an excluded source.")
    dependencies = {entry.object_ref for entry in selected} | {
        evidence[key].envelope for key in generation.evidence_ids
    }
    if set(obj.dependencies) != dependencies:
        raise ValueError("Generation dependencies must equal selected sources and evidence.")
    return generation
