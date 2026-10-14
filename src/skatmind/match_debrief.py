"""Private retained rollout evidence. Neither a Teacher nor a training label."""

from dataclasses import dataclass, replace

from skatmind.api.v1.schema_validation import validate_output_document
from skatmind.learning_corpus_match_snapshot import (
    LearningCorpusMatchSnapshotV1,
    validate_learning_corpus_match_snapshot_v1,
)
from skatmind.learning_corpus_references import LearningCorpusDecisionReferenceV1
from skatmind.learning_corpus_tactical_coaching_contracts import (
    LearningCorpusTacticalCoachingFocusAreaV1,
)
from skatmind.match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisResultV1,
    _validate_match_analysis_report_identity_v1,
)
from skatmind.match_decision_analysis import build_match_decision_position_request_v1
from skatmind.rollout_derivation import rollout_source_fingerprint


def completed_rollout(report):
    return (type(report) is MatchAnalysisReportV1
            and type(report.value) is MatchDecisionAnalysisResultV1
            and report.value.status == "executed"
            and report.value.options.recommendation_method == "whole_game_rollout"
            and report.value.result.document["whole_game_rollout_result"]["status"] == "complete")


def _reconcile(report, snapshot):
    """Keep the existing same-revision, exact-Decision Request reconciliation policy."""
    if type(snapshot) is not LearningCorpusMatchSnapshotV1:
        raise ValueError("Debrief requires an exact Match Snapshot.")
    validate_learning_corpus_match_snapshot_v1(snapshot)
    value = report.value
    if (report.match_id != snapshot.match_id
            or report.workspace_revision != snapshot.workspace_revision):
        raise ValueError("Debrief report requires its selected Match revision.")
    game = snapshot.workspace.slots[report.match_position - 1].observed_game
    if game is None or game.game_id != value.game_id:
        raise ValueError("Debrief report requires its exact recorded Game.")
    reference = next((item for item in snapshot.decision_references
                      if item.match_position == report.match_position
                      and item.decision_index == report.decision_index), None)
    play = next((item for item in game.plays if item.decision_index == report.decision_index), None)
    if (reference is None or play is None or reference.acting_player_id != play.player_id
            or play.player_id != value.profile_binding.acting_player_id
            or play.card != value.request.document["actual_card_played"]):
        raise ValueError("Debrief report requires its exact actor and actual Card.")
    # Rebuild the original unsupplemented before-card Request, not a rollout derived
    # with the target's content fingerprint. Metadata-only alternatives may reconcile.
    options = replace(value.options, recommendation_method="immediate_expected_value",
                      rollout_settings=None, settlement_supplements={})
    prepared = build_match_decision_position_request_v1(snapshot.workspace,
        match_position=report.match_position, decision_index=report.decision_index, options=options)
    original = prepared.request.to_dict()
    original["document"]["analysis_mode"] = "live_decision"
    original["document"].pop("actual_card_played")
    derivation = value.request.to_dict()["document"]["whole_game_rollout_derivation"]
    if (original != derivation["original_request"]
            or prepared.profile_binding != value.profile_binding):
        raise ValueError("Debrief report changed the reconstructed Decision knowledge or binding.")
    return reference


@dataclass(frozen=True, slots=True)
class MatchDebriefEvidenceV1:
    """Complete method-bound report plus original and explicitly reconciled target."""

    report: MatchAnalysisReportV1
    source_snapshot: LearningCorpusMatchSnapshotV1
    snapshot: LearningCorpusMatchSnapshotV1

    def __post_init__(self):
        if not completed_rollout(self.report):
            raise ValueError("Debrief comparison requires a completed whole-game rollout Report.")
        _validate_match_analysis_report_identity_v1(self.report, legacy_identity=False)
        # Re-enter the complete existing typed Result/options and schema boundaries.
        replace(self.report.value.options)
        replace(self.report.value)
        replace(self.report)
        validate_output_document(self.report.value.result.to_dict()["document"])
        root = self.report.value.request.document
        result = self.report.value.result.document
        if (result["settings"]["whole_game_rollout_settings"] != root["whole_game_rollout_settings"]
                or result["settings"]["recommendation_method"] != "whole_game_rollout"
                or result["profile_preset_settings"]["use_profile_presets"]
                or set(result["legal_cards"]) != {
                    item["card"] for item in result["whole_game_rollout_result"]["candidates"]}):
            raise ValueError("Debrief settings and legal Cards must match the exact rollout.")
        source = self.report.value.request.document["whole_game_rollout_derivation"]
        if (source["workspace_content_fingerprint"]
                != self.source_snapshot.source_content_fingerprint):
            raise ValueError("Debrief report does not belong to its captured source content.")
        _reconcile(self.report, self.source_snapshot)
        if self.snapshot != self.source_snapshot:
            _reconcile(self.report, self.snapshot)

    @property
    def binding_id(self):
        return rollout_source_fingerprint("skatmind.match_debrief.binding.v1", {
            "report_id": self.report.report_id, "snapshot": self.snapshot.match_snapshot_id})

    @property
    def reference(self):
        return next(item for item in self.snapshot.decision_references
                    if item.match_position == self.report.match_position
                    and item.decision_index == self.report.decision_index)

    @property
    def semantic_fingerprint(self):
        value = self.report.value.to_dict()
        value["result"]["document"]["whole_game_rollout_result"]["work"].pop("elapsed_ms")
        return rollout_source_fingerprint("skatmind.match_debrief.semantic.v1", value)


@dataclass(frozen=True, slots=True)
class DebriefDecisionV1:
    reference: LearningCorpusDecisionReferenceV1
    reports: tuple[MatchDebriefEvidenceV1, ...]
    mixed: bool
    motifs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DebriefProjectionV1:
    player_id: str | None
    recorded_decisions: int
    decisions: tuple[DebriefDecisionV1, ...]
    report_count: int
    semantic_report_count: int
    topics: tuple[tuple[str, str, int, int], ...]
    focuses: tuple[LearningCorpusTacticalCoachingFocusAreaV1, ...]


def build_debrief_projection(snapshots, sources, *, player_id=None, tactical=None, coaching=None):
    """Project accepted sources; count Decisions, not reruns. No evaluation or detection."""
    current = {item.match_snapshot_id for item in snapshots}
    references = {item.decision_reference_id: item for snapshot in snapshots
                  for item in snapshot.decision_references
                  if player_id is None or item.acting_player_id == player_id}
    grouped = {}
    for source in sources:
        if source.snapshot.match_snapshot_id not in current:
            continue
        reference = source.reference
        if reference.decision_reference_id in references:
            grouped.setdefault(reference.decision_reference_id, {})[source.binding_id] = source
    motifs = {} if tactical is None else {
        (item.match_snapshot_id, item.game_reference_id, item.decision_reference_id,
         item.acting_player_id, item.actual_card_played): item for item in tactical.evidences}
    decisions, topics = [], {}
    for identity, reports in grouped.items():
        reference = references[identity]
        retained = tuple(reports.values())
        comparisons = {(
            item.report.value.result.document["whole_game_rollout_comparison"]["status"],
            tuple(item.report.value.result.document["whole_game_rollout_result"]["tied_best_cards"])
        ) for item in retained}
        actual = retained[0].report.value.request.document["actual_card_played"]
        evidence = motifs.get((reference.match_snapshot_id, reference.game_reference_id, identity,
                               reference.acting_player_id, actual))
        categories = () if evidence is None else tuple(dict.fromkeys(
            motif.motif_type for motif in evidence.observation.motifs))
        decisions.append(DebriefDecisionV1(reference, retained, len(comparisons) > 1, categories))
        for motif in categories:
            row = topics.setdefault((reference.acting_player_id, motif), (set(), set()))
            row[0].add(identity)
            row[1].add(reference.game_reference_id)
    return DebriefProjectionV1(player_id, len(references), tuple(decisions),
        sum(len(row.reports) for row in decisions), len({item.semantic_fingerprint
            for row in decisions for item in row.reports}),
        tuple((player, motif, len(counts[0]), len(counts[1]))
              for (player, motif), counts in sorted(topics.items())),
        () if coaching is None else tuple(focus for focus in coaching.focus_areas
            if player_id is None or focus.player_id == player_id))
