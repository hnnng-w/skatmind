"""Explicit codec-3 mixed recipe; codec-2 Match admission retains its exact meaning."""

from dataclasses import dataclass

from .automatic_learning_codec import canonical_json, decode_json, fingerprint, integer
from .automatic_learning_contracts import NamedValueV1
from .automatic_learning_objects import StoredObjectV1, validate_generation
from .automatic_match_preparation import (
    ADAPTERS,
    BUILDERS,
    AutomaticMatchGeneration,
    EvidenceOutcome,
    UnsupportedGeneration,
    automatic_ids,
    build_automatic_match_bundle,
    input_fingerprint,
)
from .automatic_match_preparation import (
    admit_generation as admit_match_generation,
)
from .automatic_match_preparation import (
    generation_object as match_generation_object,
)

MIXED_ADAPTERS = ADAPTERS + tuple(NamedValueV1(name=name, value=value) for name, value in (
    ("automatic_mixed", "1"), ("session_source", "2"), ("session_decision", "2"),
    ("session_rollout", "2")))
MIXED_BUILDERS = BUILDERS + (NamedValueV1(name="session_coverage", value="1"),)


@dataclass(frozen=True, slots=True)
class AutomaticMixedGeneration(AutomaticMatchGeneration):
    match_catalog_revision: int

    def to_dict(self):
        return {**super(AutomaticMixedGeneration, self).to_dict(),
                "producer": "automatic_mixed_preparation", "version": 1,
                "match_catalog_revision": self.match_catalog_revision}


@dataclass(frozen=True, slots=True)
class AutomaticMixedBundle:
    match: object
    session_sources: tuple
    session_evidence: tuple
    session_coverage: tuple
    fingerprints: tuple

    def __getattr__(self, name):
        return getattr(self.match, name)


def build_mixed_bundle(sources, evidence, *, mixed, corpus_id, dataset_id, catalog_revision):
    matches = tuple(row for row in sources if row[1].source_version.source.family == "match")
    match_evidence = tuple(row for row in evidence
                           if row.source.record.source_version.source.family == "match")
    match = build_automatic_match_bundle(matches, match_evidence, corpus_id=corpus_id,
        dataset_id=dataset_id, catalog_revision=catalog_revision)
    if not mixed:
        return match
    sessions = tuple(row[2] for row in sources if row[1].source_version.source.family == "session")
    session_evidence = tuple(row for row in evidence
                             if row.source.record.source_version.source.family == "session")
    covered = {(row.entry.source_version_id, row.observation.observed_play_revision)
               for row in session_evidence}
    coverage = tuple(NamedValueV1(name=name, value=str(value)) for name, value in (
        ("sessions", len(sessions)),
        ("recorded_plays", sum(row.coverage.recorded_plays for row in sessions)),
        ("own_plays", sum(row.coverage.own_plays for row in sessions)),
        ("eligible_decisions", sum(len(row.coverage.decisions) for row in sessions)),
        ("covered_decisions", len(covered)), ("retained_executions", len(session_evidence)),
        ("missing_checkpoints", sum(row.coverage.missing_checkpoints for row in sessions)),
        ("no_perspective", sum(not row.coverage.has_perspective for row in sessions))))
    fingerprints = match.fingerprints + (NamedValueV1(name="session_review", value=fingerprint(
        "session_review_v1", {"sources": [row.record.to_dict() for row in sessions],
        "evidence": [row.entry.to_dict() for row in session_evidence],
        "coverage": [row.to_dict() for row in coverage]})),)
    return AutomaticMixedBundle(match, sessions, session_evidence, coverage, fingerprints)


def generation_object(generation, sources, evidence):
    if type(generation) is AutomaticMatchGeneration:
        return match_generation_object(generation, sources, evidence)
    dependencies = tuple(sorted({row[1].object_ref for row in sources}
        | {row.entry.envelope for row in evidence}, key=lambda ref: ref.identity))
    return StoredObjectV1(area="generations", kind="generation_descriptor", codec_version=3,
        payload=canonical_json(generation.to_dict()), dependencies=dependencies)


def admit_generation(obj, manifest):
    from .app_web.automatic_match_inventory import MatchInventoryRow
    from .app_web.automatic_session_inventory import SessionInventoryRow
    from .corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS

    if obj.codec_version != 3:
        return admit_match_generation(obj, manifest)
    data = decode_json(obj.payload)
    if (set(data) != {"version", "producer", "recipe", "inventory", "evidence_outcomes",
                     "input_fingerprint", "match_catalog_revision"}
            or type(data["version"]) is not int or data["version"] != 1
            or data["producer"] != "automatic_mixed_preparation"):
        raise UnsupportedGeneration("Unsupported mixed generation producer.")
    recipe = validate_generation(obj, manifest)
    if (recipe.adapter_versions != MIXED_ADAPTERS or recipe.builder_versions != MIXED_BUILDERS
            or (recipe.corpus_id, recipe.dataset_id) != automatic_ids(manifest.space_id)
            or recipe.seed != 0 or recipe.partition_weights != (70, 15, 15)):
        raise UnsupportedGeneration("Unsupported mixed generation recipe.")
    integer(data["match_catalog_revision"])
    if data["match_catalog_revision"] > recipe.catalog_revision:
        raise ValueError("Match revision cannot exceed the outer membership revision.")
    if type(data["inventory"]) is not list or type(data["evidence_outcomes"]) is not list:
        raise ValueError("Mixed ledgers must be arrays.")
    rows = tuple((SessionInventoryRow if row.get("family") == "session" else
                  MatchInventoryRow).from_dict(row) for row in data["inventory"])
    outcomes = tuple(EvidenceOutcome.from_dict(row) for row in data["evidence_outcomes"])
    def order(row):
        return ("session" if type(row) is SessionInventoryRow else "match", row.candidate_id)
    if (tuple(sorted(rows, key=order)) != rows
            or len({row.candidate_id for row in rows}) != len(rows)
            or tuple(row.evidence_id for row in outcomes) != tuple(sorted({
                row.evidence_id for row in outcomes}))):
        raise ValueError("Mixed inputs require unique canonical order.")
    excluded = {row.source for row in recipe.exclusions}
    selected = sorted((row for row in rows
                       if row.status == "selected" and row.source not in excluded),
                      key=lambda row: (row.source.family, row.source.product_id))
    sources = {row.source_version.identity: row for row in manifest.sources}
    if (tuple(row.source_version_id for row in selected) != recipe.source_version_ids
            or any(sources[row.source_version_id].source_version.source != row.source
                   for row in selected)
            or tuple(row.evidence_id for row in outcomes if row.status == "selected")
            != recipe.evidence_ids
            or tuple(sorted(recipe.exclusions, key=lambda row: row.source.identity))
            != recipe.exclusions):
        raise ValueError("Mixed selection disagrees with its source ledger.")
    names = (*LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS, "rollout_comparisons",
             "rollout_availability", "coverage", "session_review")
    if tuple(row.name for row in recipe.derived_fingerprints) != names:
        raise ValueError("Mixed recipe must bind all derived families.")
    identity = input_fingerprint(rows, outcomes, recipe.exclusions, recipe.source_version_ids)
    if data["input_fingerprint"] != identity:
        raise ValueError("Mixed input identity disagrees.")
    return AutomaticMixedGeneration(recipe, rows, outcomes, identity,
                                     data["match_catalog_revision"])
