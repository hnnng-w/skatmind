"""Immutable storage identities and indexes, independent of semantic admission."""

from __future__ import annotations

from dataclasses import dataclass

from .automatic_learning_codec import Record, digest, fingerprint, integer, text, unique

AUTOMATIC_LEARNING_VERSION = 1
AUTOMATIC_LEARNING_MAX_OBJECT_BYTES = 16 * 1024 * 1024
AUTOMATIC_LEARNING_MAX_TOTAL_BYTES = 512 * 1024 * 1024
AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS = 2_048
AUTOMATIC_LEARNING_MAX_GENERATIONS = 2
AUTOMATIC_LEARNING_MAX_CANDIDATES_PER_OWNER = 1
SOURCE_FAMILIES = ("match", "session", "historical_review")
EVIDENCE_CLASSES = ("decision", "rollout", "historical")
OBJECT_AREAS = ("sources", "reports", "generations")
# Reserved discriminators are not registrations of compatible semantic codecs.
SOURCE_KINDS = {"match": "match_source", "session": "session_source",
                "historical_review": "historical_source"}
REPORT_KINDS = {
    ("match", "decision"): "match_decision",
    ("session", "decision"): "session_decision",
    ("match", "rollout"): "match_rollout",
    ("session", "rollout"): "session_rollout",
    ("match", "historical"): "match_historical",
    ("historical_review", "historical"): "historical_review",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceKeyV1(Record):
    family: str
    product_id: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.family not in SOURCE_FAMILIES:
            raise ValueError("Unsupported source family.")
        text(self.product_id)

    @property
    def identity(self):
        return fingerprint("logical_source_v1", self.to_dict())


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceVersionV1(Record):
    source: SourceKeyV1
    source_contract: str
    contract_version: int
    content_fingerprint: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        text(self.source_contract)
        integer(self.contract_version, 1)
        digest(self.content_fingerprint)

    @property
    def identity(self):
        return fingerprint("source_version_v1", self.to_dict())


@dataclass(frozen=True, slots=True, kw_only=True)
class ObjectRefV1(Record):
    area: str
    kind: str
    codec_version: int
    fingerprint: str
    size_bytes: int
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.area not in OBJECT_AREAS:
            raise ValueError("Unsupported object area.")
        text(self.kind)
        integer(self.codec_version, 1)
        integer(self.size_bytes, 1)
        digest(self.fingerprint)

    @property
    def identity(self):
        return self.area, self.fingerprint


@dataclass(frozen=True, slots=True, kw_only=True)
class ObjectEntryV1(Record):
    reference: ObjectRefV1
    dependencies: tuple[ObjectRefV1, ...] = ()
    version: int = 1

    def __post_init__(self):
        self.validate()
        unique(tuple(item.identity for item in self.dependencies))
        if self.reference in self.dependencies:
            raise ValueError("An object cannot depend on itself.")


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentityScopeV1(Record):
    kind: str
    namespace: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.kind not in ("source_local", "shared_claim"):
            raise ValueError("Unsupported identity scope.")
        text(self.namespace)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceRecordV1(Record):
    source_version: SourceVersionV1
    object_ref: ObjectRefV1
    scope: IdentityScopeV1
    revision: int | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.revision is not None:
            integer(self.revision)
        if self.object_ref.area != "sources":
            raise ValueError("A source requires a source object.")
        if self.scope.kind == "source_local" and (
            self.scope.namespace != self.source_version.source.identity
        ):
            raise ValueError("Source-local namespaces must bind the logical source.")


@dataclass(frozen=True, slots=True, kw_only=True)
class EntityReferenceV1(Record):
    source: SourceKeyV1
    scope: IdentityScopeV1
    entity_kind: str
    original_id: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.entity_kind not in ("game", "player"):
            raise ValueError("Unsupported entity kind.")
        text(self.original_id)
        if self.scope.kind == "source_local" and self.scope.namespace != self.source.identity:
            raise ValueError("Source-local entity escaped its namespace.")


@dataclass(frozen=True, slots=True, kw_only=True)
class OriginBindingV1(Record):
    """A retained binding claim, never trusted without its future typed validator."""

    kind: str
    subject: EntityReferenceV1
    target: EntityReferenceV1 | None
    proof: ObjectRefV1
    validator: str
    validator_version: int
    version: int = 1

    def __post_init__(self):
        self.validate()
        text(self.validator)
        integer(self.validator_version, 1)
        if self.kind not in ("guided_producer", "cross_source_game", "cross_source_player"):
            raise ValueError("Unsupported binding kind.")
        if self.kind == "guided_producer":
            if (self.target is not None or self.subject.source.family != "historical_review"
                    or self.subject.scope.kind != "source_local"):
                raise ValueError("Guided origin requires a source-local Historical producer proof.")
        elif (self.target is None or self.target.source == self.subject.source
              or self.target.entity_kind != self.subject.entity_kind
              or self.kind != f"cross_source_{self.subject.entity_kind}"):
            raise ValueError("Cross-source binding requires matching explicit endpoints.")

    @property
    def identity(self):
        return fingerprint("origin_binding_v1", self.to_dict())


@dataclass(frozen=True, slots=True, kw_only=True)
class SituationV1(Record):
    source_version_id: str
    game_id: str
    decision_index: int
    actor_id: str
    observed_card: str
    information_cutoff: int
    checkpoint_fingerprint: str | None = None
    accepted_play_fingerprint: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        digest(self.source_version_id)
        for value in (self.game_id, self.actor_id, self.observed_card):
            text(value)
        integer(self.decision_index)
        integer(self.information_cutoff)
        if (self.checkpoint_fingerprint is None) != (self.accepted_play_fingerprint is None):
            raise ValueError("Checkpoint and accepted Play bindings must be supplied together.")
        for value in (self.checkpoint_fingerprint, self.accepted_play_fingerprint):
            if value is not None:
                digest(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceEntryV1(Record):
    evidence_class: str
    source_version_id: str
    envelope: ObjectRefV1
    situation: SituationV1 | None
    semantic_fingerprint: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.evidence_class not in EVIDENCE_CLASSES or self.envelope.area != "reports":
            raise ValueError("Invalid evidence class or envelope area.")
        digest(self.source_version_id)
        if self.semantic_fingerprint is not None:
            digest(self.semantic_fingerprint)
        if self.situation is None and self.evidence_class != "historical":
            raise ValueError("Decision and rollout entries require a situation.")
        if (self.situation is not None
                and self.situation.source_version_id != self.source_version_id):
            raise ValueError("Situation must retain the exact original source version.")

    @property
    def identity(self):
        return fingerprint("execution_binding_v1", {
            "source_version_id": self.source_version_id, "envelope": self.envelope.to_dict(),
        })


@dataclass(frozen=True, slots=True, kw_only=True)
class ExclusionV1(Record):
    source: SourceKeyV1
    reason: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.reason not in ("explicit", "missing", "invalid", "ambiguous", "unsupported"):
            raise ValueError("Unsupported exclusion reason.")


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedValueV1(Record):
    name: str
    value: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        text(self.name)
        text(self.value)


@dataclass(frozen=True, slots=True, kw_only=True)
class SkippedSituationV1(Record):
    situation: SituationV1
    reason: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.reason not in ("acting_hand_unavailable", "required_public_hand_unavailable",
                               "checkpoint_unavailable", "unsupported"):
            raise ValueError("Unsupported situation skip reason.")


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerationV1(Record):
    """A reconstruction recipe/descriptor, not persisted derived artifacts."""

    source_version_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    exclusions: tuple[ExclusionV1, ...]
    skipped_situations: tuple[SkippedSituationV1, ...]
    corpus_id: str
    dataset_id: str
    catalog_revision: int
    seed: int
    partition_weights: tuple[int, ...]
    adapter_versions: tuple[NamedValueV1, ...]
    builder_versions: tuple[NamedValueV1, ...]
    derived_fingerprints: tuple[NamedValueV1, ...]
    version: int = 1

    def __post_init__(self):
        self.validate()
        for values in (self.source_version_ids, self.evidence_ids):
            unique(values)
            for value in values:
                digest(value)
        unique(tuple(item.source for item in self.exclusions))
        unique(tuple(item.situation for item in self.skipped_situations))
        if any(item.situation.source_version_id not in self.source_version_ids
               for item in self.skipped_situations):
            raise ValueError("Skipped situations must belong to selected sources.")
        text(self.corpus_id)
        text(self.dataset_id)
        integer(self.catalog_revision)
        integer(self.seed)
        if len(self.partition_weights) != 3:
            raise ValueError("Expected three partition weights.")
        for weight in self.partition_weights:
            integer(weight, 1)
        for values in (self.adapter_versions, self.builder_versions, self.derived_fingerprints):
            unique(tuple(item.name for item in values))
        for item in self.derived_fingerprints:
            digest(item.value)


@dataclass(frozen=True, slots=True, kw_only=True)
class ManifestV1(Record):
    space_id: str
    revision: int = 0
    objects: tuple[ObjectEntryV1, ...] = ()
    sources: tuple[SourceRecordV1, ...] = ()
    bindings: tuple[OriginBindingV1, ...] = ()
    evidence: tuple[EvidenceEntryV1, ...] = ()
    exclusions: tuple[ExclusionV1, ...] = ()
    current_generation: ObjectRefV1 | None = None
    previous_generation: ObjectRefV1 | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        text(self.space_id)
        integer(self.revision)
        unique(tuple(entry.reference.identity for entry in self.objects))
        unique(tuple(entry.source_version.identity for entry in self.sources))
        unique(tuple(entry.identity for entry in self.bindings))
        unique(tuple(entry.identity for entry in self.evidence))
        unique(tuple(entry.source for entry in self.exclusions))
        unique(self.generations)
        if len(self.generations) > AUTOMATIC_LEARNING_MAX_GENERATIONS:
            raise ValueError("Only current and one previous generation may be retained.")
        if any(ref.area != "generations" for ref in self.generations):
            raise ValueError("Expected generation references.")
        for kind in EVIDENCE_CLASSES:
            if sum(entry.evidence_class == kind for entry in self.evidence) > (
                AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS
            ):
                raise ValueError("Evidence class limit exceeded.")
        objects = {entry.reference: entry for entry in self.objects}
        sources = {entry.source_version.identity: entry for entry in self.sources}
        scopes = {}
        for source in self.sources:
            key = source.source_version.source
            if key in scopes and scopes[key] != source.scope:
                raise ValueError("Corrections must retain their logical identity scope.")
            scopes[key] = source.scope
        roots = [source.object_ref for source in self.sources] + list(self.generations)
        for binding in self.bindings:
            for entity in (binding.subject, binding.target):
                if entity is not None and scopes.get(entity.source) != entity.scope:
                    raise ValueError("Binding endpoints must reference retained source scopes.")
            roots.append(binding.proof)
        for entry in self.evidence:
            source = sources.get(entry.source_version_id)
            if source is None:
                raise ValueError("Evidence requires its original source version.")
            family = source.source_version.source.family
            if entry.situation is not None and (
                (family == "session") != (entry.situation.checkpoint_fingerprint is not None)
            ):
                raise ValueError("Session situations require native Checkpoint/Play identity.")
            if entry.envelope not in objects or source.object_ref not in (
                objects[entry.envelope].dependencies
            ):
                raise ValueError("Evidence envelope must depend on its original source object.")
            roots.append(entry.envelope)
        # Closed acyclic dependency graph, including retained but unsupported objects.
        reached, active = set(), set()

        def visit(ref):
            if ref not in objects or ref in active:
                raise ValueError("Missing or cyclic object dependency reference.")
            if ref in reached:
                return
            active.add(ref)
            for dependency in objects[ref].dependencies:
                visit(dependency)
            active.remove(ref)
            reached.add(ref)

        for root in roots:
            visit(root)
        if reached != set(objects):
            raise ValueError("Manifest object index must equal the complete root closure.")

    @property
    def generations(self):
        return tuple(ref for ref in (self.current_generation, self.previous_generation)
                     if ref is not None)

    @property
    def fingerprint(self):
        return fingerprint("manifest_v1", self.to_dict())
