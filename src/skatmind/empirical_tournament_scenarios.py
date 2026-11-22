"""Joint, uniformly resampled recorded tables for private post-list monetary analysis."""

import random
from dataclasses import asdict, dataclass, field, replace
from fractions import Fraction
from math import ceil
from time import monotonic

from .automatic_learning_codec import unique
from .bounded_search_information import build_live_search_information_view
from .coherent_hidden_world import derive_simulation_child_seed
from .empirical_tournament_sources import (
    Population,
    RecordedList,
    add_points,
    evidence_time,
    prepare_population,
    prepare_target,
    score_game,
    supported_match,
)
from .event_context_contracts import (
    TOURNAMENT_RULE,
    EventContextV1,
    RecordingVersionV1,
    RuleSourceV1,
    bounded_text,
    position,
)
from .event_context_sources import recording_version_v1
from .input_loader import build_local_game_state_from_input
from .match_analysis_contracts import MatchDecisionAnalysisOptionsV1
from .match_decision_analysis import (
    _build_position_root,
    _DecisionUnavailable,
    _select_match_prepared_decision_v1,
)
from .match_workspace_persistence_contracts import MatchWorkspacePersistenceDocumentV1
from .mode_accounting import STANDARD_RULE
from .ouvert_simulation import build_declared_ouvert_public_hand_constraint
from .rollout_derivation import rollout_source_fingerprint
from .tournament_money_valuation import (
    Candidate,
    Comparison,
    Continuation,
    PoolSchedule,
    PoolStanding,
    TournamentModel,
    TournamentPrefix,
    WorldOutcome,
    evaluate_tournament_money,
    terminal_list_game,
)
from .whole_game_rollout import _completed_batches, _Stopped, _Work, prepare_whole_game_rollout_v1
from .whole_game_rollout_contracts import WholeGameRolloutSettingsV1, WholeGameRolloutWorkV1
from .whole_game_rollout_policy import select_whole_game_rollout_card_v1
from .whole_game_rollout_workflow import rollout_declaration

POLICY = "uniform_recorded_standard_table_blocks_v1"
ASSUMPTIONS = ("uniform_logical_lists_with_replacement", "observed_joint_table_behavior",
               "independent_table_draws", "common_draws_across_cards", "single_series")


def _ids(values, maximum):
    if type(values) is not tuple or len(values) > maximum:
        raise ValueError("Expected bounded immutable participant identities.")
    for item in values:
        bounded_text(item)
    unique(values)


@dataclass(frozen=True, slots=True)
class FieldTable:
    table_id: str
    places: tuple[str, ...]
    through: int = 0
    points: tuple[int, ...] | None = None  # Observed cumulative points, never a prediction.

    def __post_init__(self):
        bounded_text(self.table_id)
        _ids(self.places, 3)
        position(self.through, zero=True)
        if self.points is None and self.through == 0:
            object.__setattr__(self, "points", (0, 0, 0))
        if (len(self.places) != 3 or type(self.points) is not tuple or len(self.points) != 3
                or any(type(n) is not int or abs(n) > 10**6 for n in self.points)
                or not self.through and any(self.points)):
            raise ValueError("A table requires three canonical places and an established prefix.")


@dataclass(frozen=True, slots=True)
class FieldPool:
    schedule: PoolSchedule
    members: tuple[str, ...] | None  # Unknown is different from a complete roster.
    priority: tuple[str, ...] | None = None  # Pre-established priority for equal points only.

    def __post_init__(self):
        if type(self.schedule) is not PoolSchedule:
            raise ValueError("Expected a personal pool schedule.")
        if any(n > 10**12 for n in self.schedule.awards_cents or ()):
            raise ValueError("Award exceeds the finite monetary bound.")
        if self.members is not None:
            _ids(self.members, 192)
            if len(self.members) != self.schedule.field_size:
                raise ValueError("Pool roster must reconcile with the declared field size.")
        if self.priority is not None:
            _ids(self.priority, 192)
            if self.members is None or set(self.priority) != set(self.members):
                raise ValueError("Tie priority must cover exactly the pool roster.")

    def standing(self, scores, selected, reference):
        if self.members is None or selected not in self.members:
            return None
        others = tuple(scores[p] for p in self.members if p != selected)
        ahead = None if self.priority is None else sum(scores[p] == scores[selected]
            for p in self.priority[:self.priority.index(selected)])
        return PoolStanding(self.schedule.pool_id, others, tied_ahead=ahead,
                            resolution_evidence=None if ahead is None else reference)


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldFacts:
    """Cutoff facts about the whole event; not supplied by an ordinary Match importer."""

    source: RecordingVersionV1
    event_id: str
    series_id: str
    game_position: int
    decision_index: int
    available_at: str
    reference: str
    series_count: int
    tables: tuple[FieldTable, ...]
    pools: tuple[FieldPool, ...]
    payout_source: RuleSourceV1 | None
    transfer_cents: int | None
    other_charge_cents: int | None
    tournament_side_cents: int | None = None  # Only an independently fixed side amount.

    def __post_init__(self):
        bounded_text(self.reference)
        bounded_text(self.event_id)
        bounded_text(self.series_id)
        position(self.game_position)
        position(self.decision_index, end=30)
        bounded_text(self.available_at, 64)
        if type(self.source) is not RecordingVersionV1 or self.source.source.family != "match":
            raise ValueError("Field facts require the exact target Match version.")
        if self.payout_source is not None and type(self.payout_source) is not RuleSourceV1:
            raise ValueError("Expected a factual payout edition.")
        if type(self.series_count) is not int or self.series_count < 1:
            raise ValueError("Expected the factual number of tournament series.")
        if (type(self.tables) is not tuple or len(self.tables) > 64
                or any(type(t) is not FieldTable for t in self.tables)
                or type(self.pools) is not tuple or len(self.pools) > 8
                or any(type(p) is not FieldPool for p in self.pools)):
            raise ValueError("Expected bounded immutable field tables and pools.")
        unique(tuple(t.table_id for t in self.tables))
        players = tuple(p for t in self.tables for p in t.places)
        unique(players)
        unique(tuple(p.schedule.pool_id for p in self.pools))
        for pool in self.pools:
            if pool.members is not None and not set(pool.members).issubset(players):
                raise ValueError("Pool members must belong to the factual field.")
        for cents in (self.transfer_cents, self.other_charge_cents, self.tournament_side_cents):
            if cents is not None and (type(cents) is not int or abs(cents) > 10**12):
                raise ValueError("Expected bounded fixed cents or an unresolved amount.")
        if self.other_charge_cents is not None and self.other_charge_cents < 0:
            raise ValueError("Other charges cannot be negative.")


@dataclass(frozen=True, slots=True)
class EmpiricalResult:
    status: str
    reasons: tuple[str, ...]
    population: Population
    modeled_tables: tuple[str, ...]
    # Occurrence order, then modeled-table order. Repeated donor IDs are intentional.
    draws: tuple[tuple[str, ...], ...]
    prefix: TournamentPrefix | None
    prefix_points: tuple[int, ...]
    candidates: tuple[Candidate, ...]
    comparison: Comparison | None
    settings: WholeGameRolloutSettingsV1
    work: WholeGameRolloutWorkV1
    source_preparation_ms: float = field(compare=False)
    policy: str = POLICY
    assumptions: tuple[str, ...] = ASSUMPTIONS


def _decision_view(workspace, game, decision):
    selected = _select_match_prepared_decision_v1(workspace, match_position=game,
                                                  decision_index=decision)
    root = _build_position_root(workspace, match_position=game, selected=selected,
                                options=MatchDecisionAnalysisOptionsV1(use_profile_presets=False))
    public = build_declared_ouvert_public_hand_constraint(root)
    return build_live_search_information_view(state=build_local_game_state_from_input(root),
        declaration=rollout_declaration(root), left_hand_size=root["left_hand_size"],
        right_hand_size=root["right_hand_size"], skat_visibility=root["skat_visibility"],
        public_hand_constraints=() if public is None else (public,))


def _sample_tables(field, current, points, game, modeled, donors, settings, work):
    tables = sorted(field.tables, key=lambda t: t.table_id)
    rng = {key: random.Random(derive_simulation_child_seed(settings.random_seed,
                                                           POLICY + ":" + key)) for key in modeled}
    # Materialize a donor suffix only on its first draw at the target table.
    suffixes = {}
    for _ in range(settings.requested_worlds):
        scores, draws, suffix = {}, [], ()
        for table in tables:
            work.prepare_unit()
            totals = points if table == current else table.points
            key = table.table_id
            if key in rng:
                donor = rng[key].choice(donors)
                name = donor.evidence.source.source.product_id
                draws.append(name)
                totals = add_points(totals, donor.suffix_points(
                    game if table == current else table.through))
                if table == current:
                    if name not in suffixes:
                        suffixes[name] = donor.suffix_games(game, table.places)
                    suffix = suffixes[name]
            scores.update(zip(table.places, totals, strict=True))
        yield scores, tuple(draws), suffix


def _validate_rosters(field, current, selected):
    if current.through:
        raise ValueError("Do not substitute external scores for the current table prefix.")
    for pool in field.pools:
        member = pool.schedule.membership
        if pool.members is None:
            continue
        if (member.participation == "yes" and selected not in pool.members
                or member.participation == "no" and selected in pool.members):
            raise ValueError("Personal participation contradicts pool roster.")
        if member.pool_id == "base" and len(pool.members) != 3 * len(field.tables):
            raise ValueError("Base competition must cover the whole field.")


def _joint_leaf(wid, scores, places, current_game, suffix, field, selected):
    joint = scores.copy()
    for player, delta in zip(places, score_game(places, current_game), strict=True):
        joint[player] += delta
    standings = tuple(row for pool in field.pools
                      if (row := pool.standing(joint, selected, field.reference)) is not None)
    return Continuation(scenario_id=wid, probability=Fraction(1), future_games=suffix,
                        standings=standings, transfer_cents=field.transfer_cents,
                        other_charge_cents=field.other_charge_cents,
                        tournament_side_cents=field.tournament_side_cents)


def produce_empirical_tournament_money(
    target: MatchWorkspacePersistenceDocumentV1, context: EventContextV1, *,
    game_position: int, decision_index: int, sources: tuple[RecordedList, ...],
    field: FieldFacts | None, settings: WholeGameRolloutSettingsV1, cancelled=None,
    candidate_order: tuple[str, ...] | None = None, clock=monotonic,
) -> EmpiricalResult:
    """Prepare once, execute every legal card, then value only the complete joint measure."""
    if type(target) is not MatchWorkspacePersistenceDocumentV1:
        raise ValueError("The empirical target must be an original Match document.")
    if type(settings) is not WholeGameRolloutSettingsV1:
        raise ValueError("Expected internal whole-game effort settings.")
    settings = replace(settings, objective="complete_settlement")
    position(game_position)
    position(decision_index, end=30)
    work = _Work(settings, clock, cancelled)
    population, modeled, draws = Population(), (), []
    prefix, points, source_ms = None, (), None

    def result(status, *reasons, candidates=(), comparison=None):
        measured = work.snapshot()
        return EmpiricalResult(status, tuple(reasons), population, modeled, tuple(draws), prefix,
                               points, candidates, comparison, settings, measured,
                               measured.elapsed_ms if source_ms is None else source_ms)

    try:
        work.check()
        version = recording_version_v1(target)
        terms = context.applicable_terms(game_position)
        if (not supported_match(target) or terms.platform != "euroskat"
                or terms.scoring_rule != TOURNAMENT_RULE):
            return result("unavailable", "unsupported_target_rules")
        if field is None:
            return result("unavailable", "field_facts_missing")
        if type(field) is not FieldFacts or (
                field.source, field.event_id, field.series_id, field.game_position,
                field.decision_index) != (version, context.event_id, context.series_id,
                                          game_position, decision_index):
            raise ValueError("Field facts do not belong to this exact Match decision.")
        if field.series_count != 1:
            return result("unavailable", "unsupported_series_count")
        cutoff = target.workspace.match_definition.played_at
        cutoff_time = evidence_time(cutoff)
        if cutoff_time is None:
            return result("unavailable", "target_cutoff_missing")
        field_time = evidence_time(field.available_at)
        if field_time is None or field_time > cutoff_time:
            return result("unavailable", "field_not_available_at_cutoff")
        prefix, places, points, gaps = prepare_target(target, context, game_position,
                                                       decision_index, work.prepare_unit)
        if gaps:
            return result("unavailable", *gaps)
        selected = prefix.prepared.selected_participant_id
        current = next((t for t in field.tables if t.places == places), None)
        if current is None:
            return result("unavailable", "current_table_places_missing")
        _validate_rosters(field, current, selected)
        modeled = tuple(sorted(t.table_id for t in field.tables
                               if (game_position if t == current else t.through) < 36))
        population = prepare_population(target, sources, work_hook=work.prepare_unit)
        view = _decision_view(target.workspace, game_position, decision_index)
        source_ms = work.elapsed()
        if modeled and not population.donors:
            return result("unavailable", "eligible_donor_population_empty")

        work.check()
        remaining = settings.max_preparation_work - work.preparation_units
        if not remaining:
            return result("partial", "preparation_budget_exhausted")
        # Source extraction and current-world preparation share the same effort and deadline.
        timeout = settings.wall_clock_timeout_ms
        budget = replace(settings, max_preparation_work=remaining,
            wall_clock_timeout_ms=None if timeout is None else max(1, ceil(timeout-work.elapsed())))
        rollout = prepare_whole_game_rollout_v1(view, budget, clock=clock, cancelled=cancelled)
        work.preparation_units += rollout.work.preparation_units
        work.sampled_worlds = rollout.work.sampled_worlds
        work.materialized_worlds = rollout.work.materialized_worlds
        if rollout.status != "ready":
            return result(rollout.status, rollout.stop_reason)
        work.check()
        cards = rollout.legal_root_cards
        order = cards if candidate_order is None else candidate_order
        if type(order) is not tuple or len(order) != len(cards) or set(order) != set(cards):
            raise ValueError("Candidate order must permute all legal cards.")
        n = settings.requested_worlds
        if n * len(cards) * sum(len(p.members or ()) for p in field.pools) > 500_000:
            return result("unavailable", "field_scenario_work_limit")
        batches = _completed_batches(rollout, order, work, select_whole_game_rollout_card_v1,
                                     lambda state, *_: terminal_list_game(prefix, state))
        samples = _sample_tables(field, current, points, game_position, modeled, population.donors,
                                 settings, work)
        worlds = tuple((f"draw-{i+1}", Fraction(1, n)) for i in range(n))
        outcomes = {c: [] for c in cards}
        for (wid, _), batch, (scores, draw, suffix) in zip(worlds, batches, samples, strict=True):
            for card in cards:
                work.check()
                game = batch[card]
                leaf = _joint_leaf(wid, scores, places, game, suffix, field, selected)
                outcomes[card].append(WorldOutcome(wid, game, (leaf,)))
            draws.append(draw)

        # Binding includes full source identity. None of it seeds either random stream.
        scenario_id = rollout_source_fingerprint("skatmind." + POLICY, {
            "prefix": prefix.fingerprint, "cutoff": cutoff, "field": asdict(field),
            "donors": [asdict(d.evidence) for d in population.donors],
            "settings": asdict(settings), "rollout_view": rollout.source_fingerprint,
            "modeled_tables": modeled, "occurrences": dict(zip((w for w, _ in worlds), draws,
                                                               strict=True)),
        })
        model = TournamentModel(prefix_id=prefix.fingerprint, model_revision=POLICY,
            scenario_set_id=scenario_id, fee_rule=STANDARD_RULE, payout_source=field.payout_source,
            pools=tuple(p.schedule for p in field.pools), worlds=worlds)
        candidates = tuple(Candidate(c, model, tuple(outcomes[c])) for c in cards)
        comparison = evaluate_tournament_money(prefix, model, candidates, work_hook=work.check)
        gaps = sorted({r for c in comparison.candidates
                       for row in c.outcomes for r in row.unavailable})
        work.check()
        return result("unavailable" if gaps else "complete", *gaps, candidates=candidates,
                      comparison=comparison)
    except _DecisionUnavailable as error:
        return result("unavailable", error.skipped_reason or error.reason)
    except _Stopped as stop:
        return result(stop.status, stop.reason)
