"""Deterministic S4 recipe and isolated existing-builder composition. No execution."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .automatic_learning_codec import Record, canonical_json, decode_json, digest, fingerprint
from .automatic_learning_contracts import (
    GenerationV1,
    NamedValueV1,
    SituationV1,
    SkippedSituationV1,
)
from .automatic_learning_objects import StoredObjectV1, validate_generation
from .automatic_match_evidence import RetainedMatchDecision
from .automatic_match_rollout_evidence import RetainedMatchRollout
from .corpus_web.context import LearningCorpusWebContextV1
from .corpus_web.downloads import (
    LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS,
    build_learning_corpus_prepared_download_v1,
)
from .corpus_web.preparation import prepare_learning_corpus_artifacts_web_v1
from .learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
)
from .learning_corpus_persistence_codec import build_learning_corpus_catalog_persistence_document_v1
from .learning_corpus_persistence_contracts import LearningCorpusStoreResumeResultV1
from .learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from .match_debrief import build_debrief_projection

# The storage envelope advances only the generation codec. S1 descriptors remain
# inspectable storage, never supported reconstruction recipes. S2/S3 bytes stay exact.
ADAPTERS = tuple(NamedValueV1(name=name, value=value) for name, value in (
    ("automatic_match", "1"), ("match_source", "2"),
    ("match_decision", "2"), ("match_rollout", "2")))
BUILDERS = tuple(NamedValueV1(name=name, value=value) for name, value in (
    ("corpus_preparation", "1"), ("dataset", "2"), ("debrief", "1"),
    ("known_player_seed", "0"), ("unseen_player_seed", "0")))


class UnsupportedGeneration(ValueError):
    """A storage-valid descriptor is not a supported preparation recipe."""


@dataclass(frozen=True, slots=True, kw_only=True)
class EvidenceOutcome(Record):
    evidence_id: str
    status: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        digest(self.evidence_id)
        if self.status not in ("selected", "non_current", "missing", "corrupt",
                               "dependency_unavailable", "unsupported"):
            raise ValueError("Unsupported automatic evidence outcome.")


@dataclass(frozen=True, slots=True)
class AutomaticMatchGeneration:
    recipe: GenerationV1
    inventory: tuple
    evidence_outcomes: tuple[EvidenceOutcome, ...]
    input_fingerprint: str

    def to_dict(self):
        return {"version": 1, "producer": "automatic_match_preparation",
                "recipe": self.recipe.to_dict(),
                "inventory": [row.to_dict() for row in self.inventory],
                "evidence_outcomes": [row.to_dict() for row in self.evidence_outcomes],
                "input_fingerprint": self.input_fingerprint}


def input_fingerprint(inventory, outcomes, exclusions, selected):
    return fingerprint("automatic_match_inputs_v1", {
        "inventory": [row.to_dict() for row in inventory],
        "evidence": [row.to_dict() for row in outcomes],
        "exclusions": [row.to_dict() for row in exclusions], "selected": list(selected)})


def automatic_ids(space_id):
    return space_id + "-matches", space_id + "-match-decisions"


def admit_generation(obj, manifest):
    """Strict semantic recipe admission, separate from storage graph validation."""
    from .app_web.automatic_match_inventory import MatchInventoryRow

    if (obj.kind, obj.codec_version) != ("generation_descriptor", 2):
        raise UnsupportedGeneration("Unsupported automatic Match generation codec.")
    data = decode_json(obj.payload)
    if (set(data) != {"version", "producer", "recipe", "inventory", "evidence_outcomes",
                     "input_fingerprint"} or type(data["version"]) is not int
            or data["version"] != 1 or data["producer"] != "automatic_match_preparation"):
        raise UnsupportedGeneration("Unsupported automatic Match generation producer.")
    recipe = validate_generation(obj, manifest)
    if (recipe.adapter_versions != ADAPTERS or recipe.builder_versions != BUILDERS
            or (recipe.corpus_id, recipe.dataset_id) != automatic_ids(manifest.space_id)
            or recipe.seed != 0 or recipe.partition_weights != (70, 15, 15)):
        raise UnsupportedGeneration("Unsupported automatic Match preparation recipe.")
    if type(data["inventory"]) is not list or type(data["evidence_outcomes"]) is not list:
        raise ValueError("Automatic generation ledgers must be arrays.")
    rows = tuple(MatchInventoryRow.from_dict(row) for row in data["inventory"])
    outcomes = tuple(EvidenceOutcome.from_dict(row) for row in data["evidence_outcomes"])
    if (tuple(row.candidate_id for row in rows) != tuple(sorted({row.candidate_id for row in rows}))
            or tuple(row.evidence_id for row in outcomes) != tuple(sorted({
                row.evidence_id for row in outcomes}))):
        raise ValueError("Automatic inputs must have unique canonical order.")
    excluded = {row.source for row in recipe.exclusions}
    selected_rows = sorted((row for row in rows if row.status == "selected"
                            and row.source not in excluded), key=lambda row: row.source.product_id)
    if (tuple(row.source_version_id for row in selected_rows) != recipe.source_version_ids
            or tuple(row.evidence_id for row in outcomes if row.status == "selected")
            != recipe.evidence_ids):
        raise ValueError("Automatic generation selection disagrees with its outcomes.")
    sources = {row.source_version.identity: row for row in manifest.sources}
    if any(sources[row.source_version_id].source_version.source != row.source
           for row in selected_rows):
        raise ValueError("Automatic inventory changed its Product identity.")
    if tuple(sorted(recipe.exclusions, key=lambda row: row.source.identity)) != recipe.exclusions:
        raise ValueError("Automatic exclusions must be canonical.")
    expected_names = (*LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS, "rollout_comparisons",
                      "rollout_availability", "coverage")
    if tuple(row.name for row in recipe.derived_fingerprints) != expected_names:
        raise ValueError("Automatic generation must bind every derived family.")
    expected = input_fingerprint(rows, outcomes, recipe.exclusions, recipe.source_version_ids)
    if data["input_fingerprint"] != expected:
        raise ValueError("Automatic generation input fingerprint disagrees.")
    return AutomaticMatchGeneration(recipe, rows, outcomes, expected)


@dataclass(frozen=True, slots=True)
class AutomaticMatchBundle:
    prepared: object
    tactical: object
    coaching: object
    debrief: object
    availability: tuple
    downloads: tuple
    coverage: tuple[NamedValueV1, ...]
    skipped: tuple[SkippedSituationV1, ...]
    fingerprints: tuple[NamedValueV1, ...]
    # Admitted generation inputs, retained only for private presentation/navigation.
    # Neither field changes the recipe, fingerprints or canonical exports.
    sources: tuple = ()
    evidence: tuple = ()

    def download(self, kind):
        return next(value for value in self.downloads if value.kind == kind)


def build_automatic_match_bundle(sources, evidence, *, corpus_id, dataset_id, catalog_revision):
    """Own fresh Corpus context, no filesystem writes and no active manual owner."""
    snapshots = tuple(value[2] for value in sources)
    catalog = build_learning_corpus_catalog_v1(corpus_id=corpus_id, revision=catalog_revision,
        match_snapshots=tuple(build_learning_corpus_match_snapshot_catalog_entry_v1(value)
                              for value in snapshots),
        current_matches=tuple(build_learning_corpus_current_match_selection_v1(
            match_id=value.match_id, match_snapshot_id=value.match_snapshot_id)
            for value in snapshots))
    store = LearningCorpusStoreResumeResultV1(
        document=build_learning_corpus_catalog_persistence_document_v1(catalog),
        match_snapshots=snapshots, orphan_match_snapshot_ids=())
    # This context is exclusively in-memory. None of its persistence operations is called.
    context = LearningCorpusWebContextV1(corpus_root=Path("automatic-in-memory"), store=store)
    comparisons, availability = [], []
    for value in evidence:
        if type(value) is RetainedMatchDecision:
            context.strategy_source_store.add(build_learning_corpus_strategy_teacher_report_source_v1(
                match_snapshot_id=value.source.snapshot.match_snapshot_id, report=value.report))
        elif type(value) is RetainedMatchRollout:
            if value.comparison is not None:
                comparisons.append(value.comparison)
            else:
                availability.append(value)
        else:
            raise ValueError("Only typed original Match evidence can enter preparation.")
    result = prepare_learning_corpus_artifacts_web_v1(context, dataset_id=dataset_id,
        known_player_seed=0, unseen_player_seed=0,
        train_weight=70, validation_weight=15, test_weight=15)
    if result.status != "prepared":
        raise ValueError("Isolated automatic preparation failed.")
    prepared = context.prepared_artifacts
    tactical = context.tactical_prepared_artifacts
    coaching = context.tactical_coaching_prepared_artifacts
    debrief = build_debrief_projection(snapshots, tuple(comparisons),
        tactical=tactical.tactical_motif_collection,
        coaching=coaching.tactical_cross_game_coaching_report)
    downloads = tuple(build_learning_corpus_prepared_download_v1(context, kind=kind)
                      for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS)
    coverage = tuple(NamedValueV1(name=name, value=str(value)) for name, value in (
        ("matches", len(snapshots)),
        ("observed_games", sum(len(value.game_references) for value in snapshots)),
        ("passed_deals", sum(row.passed_deal_count for row in catalog.match_snapshots)),
        ("empty_slots", sum(row.empty_slot_count for row in catalog.match_snapshots)),
        ("recorded_decisions", sum(len(value.decision_references) for value in snapshots)),
        ("dataset_records", prepared.learning_dataset.record_count),
        ("skipped_decisions", prepared.learning_dataset.skipped_decision_count),
        ("ordinary_bindings", len(context.strategy_source_store.sources)),
        ("complete_rollout_reports", debrief.report_count),
        ("incomplete_rollout_attempts", len(availability))))
    source_by_snapshot = {value[2].match_snapshot_id: value[1] for value in sources}
    references = {ref.decision_reference_id: (snapshot, ref)
                  for snapshot in snapshots for ref in snapshot.decision_references}
    skipped = []
    for item in prepared.learning_dataset.skipped_decisions:
        snapshot, ref = references[item.decision_reference_id]
        game = snapshot.workspace.slots[ref.match_position - 1].observed_game
        play = game.plays[ref.decision_index - 1]
        skipped.append(SkippedSituationV1(situation=SituationV1(
            source_version_id=source_by_snapshot[snapshot.match_snapshot_id].source_version.identity,
            game_id=game.game_id, decision_index=ref.decision_index, actor_id=play.player_id,
            observed_card=play.card, information_cutoff=ref.decision_index - 1),
            reason=item.reason))
    fingerprints = tuple(NamedValueV1(name=value.kind,
        value=hashlib.sha256(value.content).hexdigest()) for value in downloads)
    fingerprints += tuple(NamedValueV1(name=name, value=fingerprint(name + "_v1", value))
        for name, value in (
            ("rollout_comparisons", [{"reference": row.reference.to_dict(), "mixed": row.mixed,
                "bindings": [item.binding_id for item in row.reports], "motifs": list(row.motifs)}
                for row in debrief.decisions]),
            ("rollout_availability", [item.entry.to_dict() for item in availability]),
            ("coverage", [row.to_dict() for row in coverage])))
    return AutomaticMatchBundle(prepared, tactical, coaching, debrief, tuple(availability),
                                downloads, coverage, tuple(skipped), fingerprints,
                                tuple((record, snapshot) for _obj, record, snapshot in sources),
                                evidence)


def generation_object(generation, sources, evidence):
    dependencies = tuple(sorted({value[1].object_ref for value in sources}
        | {value.entry.envelope for value in evidence}, key=lambda ref: ref.identity))
    return StoredObjectV1(area="generations", kind="generation_descriptor", codec_version=2,
                          payload=canonical_json(generation.to_dict()), dependencies=dependencies)
