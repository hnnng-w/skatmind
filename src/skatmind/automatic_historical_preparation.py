"""Explicit codec-4 Historical-capable recipe; existing codec 2/3 meanings stay strict."""

from dataclasses import dataclass

from .automatic_learning_codec import canonical_json, decode_json, fingerprint, integer
from .automatic_learning_contracts import NamedValueV1
from .automatic_learning_objects import StoredObjectV1, validate_generation
from .automatic_match_preparation import (
    EvidenceOutcome,
    UnsupportedGeneration,
    automatic_ids,
    input_fingerprint,
)
from .automatic_mixed_preparation import (
    MIXED_ADAPTERS,
    MIXED_BUILDERS,
    AutomaticMixedGeneration,
    build_mixed_bundle,
)

HISTORICAL_ADAPTERS = MIXED_ADAPTERS + tuple(NamedValueV1(name=name, value=value)
    for name, value in (("automatic_historical", "1"), ("historical_source", "2"),
                        ("historical_review", "2"), ("match_historical", "2")))
HISTORICAL_BUILDERS = MIXED_BUILDERS + (NamedValueV1(name="historical_coverage", value="1"),)


@dataclass(frozen=True, slots=True)
class AutomaticHistoricalGeneration(AutomaticMixedGeneration):
    def to_dict(self):
        return {**super(AutomaticHistoricalGeneration, self).to_dict(),
                "producer": "automatic_historical_preparation"}


@dataclass(frozen=True, slots=True)
class AutomaticHistoricalBundle:
    mixed: object
    historical_sources: tuple
    historical_evidence: tuple
    historical_coverage: tuple
    fingerprints: tuple

    def __getattr__(self, name):
        return getattr(self.mixed, name)


def build_historical_bundle(sources, evidence, *, corpus_id, dataset_id, catalog_revision):
    ordinary_sources = tuple(row for row in sources
                             if row[1].source_version.source.family != "historical_review")
    ordinary_evidence = tuple(row for row in evidence if row.entry.evidence_class != "historical")
    mixed = build_mixed_bundle(ordinary_sources, ordinary_evidence, mixed=True,
        corpus_id=corpus_id, dataset_id=dataset_id, catalog_revision=catalog_revision)
    reviews = tuple(row[2] for row in sources
                    if row[1].source_version.source.family == "historical_review")
    retained = tuple(row for row in evidence if row.entry.evidence_class == "historical")
    covered = {(row.entry.source_version_id, row.game.game_id) for row in retained}
    coverage = tuple(NamedValueV1(name=name, value=str(count)) for name, count in (
        ("saved_reviews", len(reviews)),
        ("recorded_plays", sum(len(trick.plays) for row in reviews for trick in row.game.tricks)),
        ("participants", len({(row.record.scope.namespace, player.player_id)
                              for row in reviews for player in row.game.players})),
        ("retained_executions", len(retained)), ("covered_games", len(covered)),
        ("match_games", len({(row.entry.source_version_id, row.game.game_id) for row in retained
                             if row.report is not None}))))
    fingerprints = mixed.fingerprints + (NamedValueV1(name="historical_review", value=fingerprint(
        "historical_review_v1", {"sources": [row.record.to_dict() for row in reviews],
        "evidence": [row.entry.to_dict() for row in retained],
        "coverage": [row.to_dict() for row in coverage]})),)
    return AutomaticHistoricalBundle(mixed, reviews, retained, coverage, fingerprints)


def historical_generation_object(generation, sources, evidence):
    dependencies = tuple(sorted({row[1].object_ref for row in sources}
        | {row.entry.envelope for row in evidence}, key=lambda ref: ref.identity))
    return StoredObjectV1(area="generations", kind="generation_descriptor", codec_version=4,
        payload=canonical_json(generation.to_dict()), dependencies=dependencies)


def admit_historical_generation(obj, manifest):
    from .app_web.automatic_historical_inventory import HistoricalInventoryRow
    from .app_web.automatic_match_inventory import MatchInventoryRow
    from .app_web.automatic_session_inventory import SessionInventoryRow
    from .corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS
    data = decode_json(obj.payload)
    if (set(data) != {"version", "producer", "recipe", "inventory", "evidence_outcomes",
                     "input_fingerprint", "match_catalog_revision"}
            or type(data["version"]) is not int or data["version"] != 1
            or data["producer"] != "automatic_historical_preparation"):
        raise UnsupportedGeneration("Unsupported Historical generation producer.")
    recipe = validate_generation(obj, manifest)
    if (recipe.adapter_versions != HISTORICAL_ADAPTERS
            or recipe.builder_versions != HISTORICAL_BUILDERS
            or (recipe.corpus_id, recipe.dataset_id) != automatic_ids(manifest.space_id)
            or recipe.seed != 0 or recipe.partition_weights != (70, 15, 15)):
        raise UnsupportedGeneration("Unsupported Historical generation recipe.")
    integer(data["match_catalog_revision"])
    if data["match_catalog_revision"] > recipe.catalog_revision:
        raise ValueError("Match revision exceeds outer membership revision.")
    if (type(data["inventory"]) is not list or type(data["evidence_outcomes"]) is not list
            or any(type(row) is not dict for row in data["inventory"])):
        raise ValueError("Historical generation ledgers require object arrays.")
    adapters = {"historical_review": HistoricalInventoryRow, "session": SessionInventoryRow,
                "match": MatchInventoryRow}
    if any(type(row.get("family", "match")) is not str
           or row.get("family", "match") not in adapters for row in data["inventory"]):
        raise ValueError("Unknown Historical inventory family.")
    rows = tuple(adapters[row.get("family", "match")].from_dict(row) for row in data["inventory"])
    outcomes = tuple(EvidenceOutcome.from_dict(row) for row in data["evidence_outcomes"])
    if (tuple(sorted(rows, key=lambda row: (
            getattr(row, "family", "match"), row.candidate_id))) != rows
            or len({row.candidate_id for row in rows}) != len(rows)
            or tuple(row.evidence_id for row in outcomes) != tuple(sorted({
                row.evidence_id for row in outcomes}))):
        raise ValueError("Historical ledgers require unique canonical order.")
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
        raise ValueError("Historical selection disagrees with its exact ledger.")
    names = (*LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS, "rollout_comparisons",
             "rollout_availability", "coverage", "session_review", "historical_review")
    if tuple(row.name for row in recipe.derived_fingerprints) != names:
        raise ValueError("Historical recipe must bind all derived families.")
    identity = input_fingerprint(rows, outcomes, recipe.exclusions, recipe.source_version_ids)
    if data["input_fingerprint"] != identity:
        raise ValueError("Historical generation input identity disagrees.")
    return AutomaticHistoricalGeneration(recipe, rows, outcomes, identity,
                                         data["match_catalog_revision"])
