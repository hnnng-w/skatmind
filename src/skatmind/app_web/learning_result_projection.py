"""Ephemeral display values from an already guarded bundle, never source authority."""

from collections import Counter
from dataclasses import dataclass

from .learning_source_labels import snapshot_labels
from .stateful_localization import managed_name, text


@dataclass(frozen=True, slots=True)
class LearningFocusDisplay:
    player: str
    topic: str
    guidance: str
    decisions: int
    games: int
    matches: int
    references: tuple[str, ...]
    reference_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LearningResultDisplay:
    explanation: str
    focuses: tuple[LearningFocusDisplay, ...]
    sources: tuple[str, ...]
    analysis_sources: tuple[str, ...]
    coaching_counts: tuple[tuple[str, int], ...]
    expected_coaching: tuple[tuple[str, object], ...]


def _players(snapshots, locale):
    names = {}
    for snapshot in snapshots:
        for player in snapshot.workspace.match_definition.participants:
            names.setdefault(player.player_id, player.player_label or player.player_id)
    counts = Counter(names.values())
    return {identity: (text(locale, "learning.result.player_number", name=name, number=number)
            if counts[name] > 1 else name)
            for number, (identity, name) in enumerate(names.items(), 1)}


def _reference_caption(value, snapshots, labels, players, locale):
    snapshot = next((s for s in snapshots if s.match_snapshot_id == value.match_snapshot_id), None)
    reference = None if snapshot is None else next((r for r in snapshot.decision_references
        if (r.decision_reference_id, r.game_reference_id, r.acting_player_id) == (
            value.decision_reference_id, value.game_reference_id, value.acting_player_id)), None)
    if reference is None or reference.match_snapshot_id not in labels:
        return text(locale, "learning.result.reference_unavailable")
    return text(locale, "learning.result.reference", source=labels[reference.match_snapshot_id],
        game=reference.match_position, decision=reference.decision_index,
        player=players.get(reference.acting_player_id, text(locale, "learning.result.unknown")))


def project_learning_focuses(report, snapshots, locale, *, profile=None, labels=None,
                            player_id=None, reference_urls=None):
    """Keep retained Player order, focus priority and exact membership, with no selection rule."""
    if report is None:
        return ()
    if labels is None:
        names = {s.match_id: managed_name(locale, profile, "matches", s.match_id,
            s.workspace.match_definition.title) for s in snapshots}
        counts = Counter(names.values())
        labels = {s.match_snapshot_id: text(locale, "task.learning.report_target",
            name=(text(locale, "task.learning.report_match", name=names[s.match_id], number=i)
                  if counts[names[s.match_id]] > 1 else names[s.match_id]),
            version=text(locale, "task.learning.saved_revision", revision=s.workspace_revision))
            for i, s in enumerate(snapshots, 1)}
    players = _players(snapshots, locale)
    decisions = {d.decision_summary_id: d for d in report.decision_summaries}
    return tuple(LearningFocusDisplay(
        players.get(player.player_id, text(locale, "learning.result.unknown")),
        text(locale, "debrief.motif." + focus.motif_type),
        text(locale, "debrief.guidance." + focus.guidance_code),
        focus.qualifying_decision_count, focus.distinct_game_count, focus.distinct_match_count,
        tuple(_reference_caption(decisions[identity], snapshots, labels, players, locale)
              if identity in decisions else text(locale, "learning.result.reference_unavailable")
               for identity in focus.decision_summary_ids),
         tuple(reference_urls.get(decisions[identity].decision_reference_id, "")
               for identity in focus.decision_summary_ids) if reference_urls else ())
        for player in report.player_reports if player_id is None or player.player_id == player_id
        for focus in player.focus_areas)


def _explanation(report, player_id=None):
    # These summarize retained facts, never recalculate consensus or focus eligibility.
    if player_id is not None:
        player = next((row for row in report.player_reports if row.player_id == player_id), None)
        if player is None or not player.exact_teacher_assessment_count:
            return "no_analysis"
        if player.retained_focus_area_count:
            return "available"
        if player.mixed_count:
            return "mixed"
        if player.teacher_covered_decision_count == 1:
            return "one_decision"
        scopes = {row.assessment_scope for row in report.teacher_assessments
                  if row.acting_player_id == player_id}
        if "complete_search" not in scopes:
            return "immediate" if scopes == {"immediate_only"} else "limited"
        return "no_recurrence"
    if report.focus_area_count:
        return "available"
    if not report.joined_teacher_evidence_count:
        return "unjoined" if report.unjoined_teacher_evidence_count else "no_analysis"
    if report.mixed_decision_count:
        return "mixed"
    if report.teacher_covered_decision_count == 1:
        return "one_decision"
    if not report.complete_search_assessable_decision_count:
        scopes = {item.assessment_scope for item in report.teacher_assessments}
        return "immediate" if scopes == {"immediate_only"} else "limited"
    return "no_recurrence"


def project_learning_result(bundle, snapshots, state, locale, *, profile=None, recorded=(),
                            labels=None, player_id=None, reference_urls=None):
    """Caller captures under the Corpus lock and revalidates source before HTML delivery."""
    prepared, _tactical, coaching = bundle
    report = coaching.tactical_cross_game_coaching_report
    if labels is None:
        labels = snapshot_labels(state, locale, profile, recorded, snapshots)
    players = _players(snapshots, locale)
    sources = tuple(labels.get(s.match_snapshot_id,
        text(locale, "learning.result.reference_unavailable")) for s in snapshots)
    analyses = tuple(text(locale, "learning.result.analysis_source", number=number,
        decision=_reference_caption(e, snapshots, labels, players, locale),
        method=text(locale, "task.value." + e.options.recommendation_method))
        for number, e in enumerate(prepared.strategy_teacher_evidence.evidences, 1))
    return LearningResultDisplay(_explanation(report, player_id),
        project_learning_focuses(report, snapshots, locale, profile=profile, labels=labels,
                                player_id=player_id, reference_urls=reference_urls),
        sources, analyses,
        tuple((name, getattr(report, name)) for name in (
            "joined_teacher_evidence_count", "unjoined_teacher_evidence_count",
            "teacher_covered_decision_count", "complete_search_assessable_decision_count",
            "mixed_decision_count", "semantic_teacher_group_count")),
        tuple(("tactical_coaching_" + key, value) for key, value in (
            ("status", report.status), ("decision_count", report.decision_summary_count),
            ("teacher_assessment_count", report.teacher_assessment_count),
            ("focus_area_count", report.focus_area_count),
            ("player_with_focus_count", report.player_with_focus_count))))
