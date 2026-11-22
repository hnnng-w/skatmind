"""Private finite-model tournament valuation. All monetary amounts are exact EUR cents."""

from dataclasses import InitVar, dataclass, field, fields
from fractions import Fraction

from .automatic_learning_codec import digest, unique
from .event_context_contracts import EventContextV1, PoolFactV1, RuleSourceV1, bounded_text
from .event_context_projection import PreparedEventContextV1, validate_frozen_context_v1
from .exact_search_state import ExactSearchState
from .exact_terminal_utility import (
    build_exact_terminal_utility,
    has_supported_terminal_utility_inputs,
)
from .fixed_three_player_list_contribution import build_fixed_three_player_list_contributions
from .fixed_three_player_list_rotation import (
    FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
    build_fixed_three_player_list_seat_assignment,
)
from .mode_accounting import STANDARD_RULE, STANDARD_SOURCE, additional_loss_fee_cents

OBJECTIVE = "expected_personal_future_net_eur_v1"


def _bounded_tuple(values, maximum, item_type):
    if (type(values) is not tuple or len(values) > maximum
            or any(type(v) is not item_type for v in values)):
        raise ValueError(f"Expected a bounded tuple of {item_type.__name__} values.")


def _exact(value, *, signed=False):
    if type(value) not in (int, Fraction) or not signed and value < 0:
        raise ValueError("Expected an exact rational amount or probability.")
    if abs(value.numerator) > 10**12 or value.denominator > 10**6:
        raise ValueError("Exact input exceeds the finite model bound.")


def _distribution(weights):
    for weight in weights:
        _exact(weight)
    if sum(weights) != 1:
        raise ValueError("Explicit probabilities must sum to one.")


@dataclass(frozen=True, slots=True)
class TournamentPrefix:
    """Verify the retained preparation once. Keep only cutoff facts and the bound seat map."""

    prepared: PreparedEventContextV1
    context: InitVar[EventContextV1]
    seats: tuple[str, ...] = field(init=False)
    fingerprint: str = field(init=False)

    def __post_init__(self, context):
        p = self.prepared
        validate_frozen_context_v1(p, context)
        if (p.status != "ready" or not context.tournament or p.target_source is None
                or not 1 <= p.game_position <= 36 or p.unresolved):
            raise ValueError(f"Expected a ready tournament game prefix; got {p.status}.")
        binding = context.binding(p.target_key)
        players = tuple(row.event_player_id for row in binding.players)
        if p.target_key.family == "match":
            assignment = build_fixed_three_player_list_seat_assignment(
                p.game_position, dict(zip(FIXED_THREE_PLAYER_LIST_TABLE_PLACES,
                                          players, strict=True)))
            players = (assignment.forehand_player_id, assignment.middlehand_player_id,
                       assignment.rearhand_player_id)
        object.__setattr__(self, "seats", players)
        object.__setattr__(self, "fingerprint", p.fingerprint)


@dataclass(frozen=True, slots=True)
class ListGame:
    """A specified outcome (stable event declarer), including an explicitly passed deal."""

    declarer_id: str | None
    settlement_score: int | None

    def __post_init__(self):
        if self.declarer_id is None:
            if self.settlement_score is not None:
                raise ValueError("A passed deal has no settlement.")
        else:
            bounded_text(self.declarer_id)
            if type(self.settlement_score) is not int or self.settlement_score == 0:
                raise ValueError("A played game requires a nonzero signed settlement.")

    def contribution(self, prefix):
        score = self.settlement_score
        outcome = ("passed_deal" if score is None else
                   "declarer_win" if score > 0 else "declarer_loss")
        rows = build_fixed_three_player_list_contributions(player_ids=prefix.seats,
            entry_outcome=outcome, declarer_player_id=self.declarer_id, settlement_score=score)
        return next(r for r in rows if r.player_id == prefix.prepared.selected_participant_id)


def terminal_list_game(prefix: TournamentPrefix, state: ExactSearchState) -> ListGame:
    """The exact world's 'me' is the bound decision actor, not necessarily the payee."""
    actor = prefix.prepared.actor_id
    if actor is None:
        raise ValueError("A card continuation requires an exact decision actor.")
    if not has_supported_terminal_utility_inputs(state.declaration):
        raise ValueError("The declaration has no supported complete terminal settlement.")
    offset = ("me", "left", "right").index(state.declarer_player)
    declarer = prefix.seats[(prefix.seats.index(actor) + offset) % 3]
    utility = build_exact_terminal_utility(state=state, local_side="declarer")
    return ListGame(declarer, utility.local_side_game_score)


@dataclass(frozen=True, slots=True)
class PoolSchedule:
    """One competition; explicit final personal award for every place, including zeros."""

    membership: PoolFactV1
    field_size: int
    awards_cents: tuple[int, ...] | None

    def __post_init__(self):
        if type(self.membership) is not PoolFactV1:
            raise ValueError("A pool requires explicit participation and entitlement facts.")
        if type(self.field_size) is not int or not 1 <= self.field_size <= 4096:
            raise ValueError("Invalid tournament pool field size.")
        if self.awards_cents is not None:
            _bounded_tuple(self.awards_cents, self.field_size, int)
            if any(n < 0 for n in self.awards_cents):
                raise ValueError("A prize cannot be negative.")

    @property
    def pool_id(self):
        return self.membership.pool_id


@dataclass(frozen=True, slots=True)
class PoolStanding:
    """Either a model-resolved rank, or all other pool members' final scores."""

    pool_id: str
    other_scores: tuple[int, ...] | None = None
    resolved_rank: int | None = None
    tied_ahead: int | None = None
    resolution_evidence: str | None = None

    def __post_init__(self):
        bounded_text(self.pool_id)
        if self.other_scores is not None:
            _bounded_tuple(self.other_scores, 4095, int)
            if self.resolved_rank is not None:
                raise ValueError("Supply field scores or a resolved rank, not both.")
        if self.resolved_rank is not None and (
                type(self.resolved_rank) is not int or self.resolved_rank < 1):
            raise ValueError("Invalid resolved rank.")
        if self.tied_ahead is not None and (self.other_scores is None
                or type(self.tied_ahead) is not int or self.tied_ahead < 0):
            raise ValueError("Tie facts require a modeled field.")
        if self.resolution_evidence is not None:
            bounded_text(self.resolution_evidence)

    def rank(self, points, size):
        if self.resolved_rank is not None:
            if self.resolved_rank > size:
                raise ValueError("Resolved rank exceeds pool size.")
            return ((self.resolved_rank, None) if self.resolution_evidence else
                    (None, "rank_evidence_missing"))
        scores = self.other_scores
        if scores is None or len(scores) < size - 1:
            return None, "incomplete_field"
        if len(scores) != size - 1:
            raise ValueError("Field exceeds pool size.")
        tied = scores.count(points)
        if self.tied_ahead is not None and self.tied_ahead > tied:
            raise ValueError("More tied opponents ahead than in the modeled field.")
        if tied and (self.tied_ahead is None or not self.resolution_evidence):
            return None, "unresolved_tie"
        return 1 + sum(s > points for s in scores) + (self.tied_ahead or 0), None


@dataclass(frozen=True, slots=True, kw_only=True)
class TournamentModel:
    """Common basis fixed at this exact preparation, including the world occurrence measure."""

    prefix_id: str
    model_revision: str
    scenario_set_id: str
    fee_rule: str
    payout_source: RuleSourceV1 | None
    pools: tuple[PoolSchedule, ...]
    worlds: tuple[tuple[str, Fraction], ...]
    sunk_net_cents: Fraction | None = None  # All incurred components, or unknown.
    objective: str = OBJECTIVE

    def __post_init__(self):
        digest(self.prefix_id)
        for label in (self.model_revision, self.scenario_set_id, self.fee_rule):
            bounded_text(label)
        if self.objective != OBJECTIVE:
            raise ValueError("Unsupported monetary objective.")
        if self.payout_source is not None and type(self.payout_source) is not RuleSourceV1:
            raise ValueError("Expected an identified payout edition.")
        _bounded_tuple(self.pools, 8, PoolSchedule)
        unique(tuple(p.pool_id for p in self.pools))
        _bounded_tuple(self.worlds, 1000, tuple)
        for name, _ in self.worlds:
            bounded_text(name)
        unique(tuple(name for name, _ in self.worlds))
        _distribution(tuple(w for _, w in self.worlds))
        if self.sunk_net_cents is not None:
            _exact(self.sunk_net_cents, signed=True)


@dataclass(frozen=True, slots=True, kw_only=True)
class Continuation:
    scenario_id: str
    probability: Fraction  # Conditional on this candidate's specified current-world outcome.
    future_games: tuple[ListGame, ...]
    standings: tuple[PoolStanding, ...]
    transfer_cents: Fraction | None  # Signed future transfers other than tournament-Cent.
    other_charge_cents: Fraction | None
    tournament_side_cents: Fraction | None = None

    def __post_init__(self):
        bounded_text(self.scenario_id)
        _exact(self.probability)
        _bounded_tuple(self.future_games, 35, ListGame)
        _bounded_tuple(self.standings, 8, PoolStanding)
        unique(tuple(p.pool_id for p in self.standings))
        for value in (self.transfer_cents, self.tournament_side_cents):
            if value is not None:
                _exact(value, signed=True)
        if self.other_charge_cents is not None:
            _exact(self.other_charge_cents)


@dataclass(frozen=True, slots=True)
class WorldOutcome:
    world_id: str
    current_game: ListGame
    continuations: tuple[Continuation, ...]

    def __post_init__(self):
        bounded_text(self.world_id)
        if type(self.current_game) is not ListGame:
            raise ValueError("Expected one current outcome per world.")
        _bounded_tuple(self.continuations, 1000, Continuation)
        unique(tuple(c.scenario_id for c in self.continuations))
        _distribution(tuple(c.probability for c in self.continuations))


@dataclass(frozen=True, slots=True)
class Candidate:
    name: str
    basis: TournamentModel
    worlds: tuple[WorldOutcome, ...]

    def __post_init__(self):
        bounded_text(self.name)
        if type(self.basis) is not TournamentModel:
            raise ValueError("Expected the candidate's exact tournament model.")
        _bounded_tuple(self.worlds, 1000, WorldOutcome)
        unique(tuple(w.world_id for w in self.worlds))
        if sum(len(w.continuations) for w in self.worlds) > 10000:
            raise ValueError("Exceeded finite scenario bound.")


@dataclass(frozen=True, slots=True)
class Money:
    prize_cents: Fraction | None
    transfer_cents: Fraction | None
    loss_fee_cents: Fraction | None
    other_charge_cents: Fraction | None
    cost_cents: Fraction | None
    net_cents: Fraction | None


@dataclass(frozen=True, slots=True)
class ValuedOutcome:
    world_id: str
    scenario_id: str
    weight: Fraction
    final_points: int
    final_own_losses: int
    awards_cents: tuple[tuple[str, int | None], ...]
    money: Money
    unavailable: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CandidateValue:
    name: str
    outcomes: tuple[ValuedOutcome, ...]
    expected: Money
    total_net_cents: Fraction | None


@dataclass(frozen=True, slots=True)
class Comparison:
    basis: TournamentModel
    candidates: tuple[CandidateValue, ...]
    ranking: tuple[tuple[str, ...], ...]  # Descending net, one group per exact value.


def _pool_excluded(member):
    return member.participation == "no" or member.entitlement == "no"


def _award(pool, standing, points, source):
    member = pool.membership
    if _pool_excluded(member):
        return 0, None
    if source is None or pool.awards_cents is None or len(pool.awards_cents) != pool.field_size:
        return None, "incomplete_schedule"
    if member.participation != "yes" or member.entitlement != "yes":
        return None, "entitlement_unknown"
    if standing is None:
        return None, "standing_missing"
    rank, gap = standing.rank(points, pool.field_size)
    return (None, gap) if gap else (pool.awards_cents[rank - 1], None)


def _pool_basis(prefix, model):
    financial = prefix.prepared.terms.financial
    if financial.currency not in ("EUR", None):
        raise ValueError("The monetary model uses EUR cents.")
    if (financial.payout_source is not None and model.payout_source is not None
            and model.payout_source != financial.payout_source):
        raise ValueError("Payout edition conflicts with the cutoff.")
    pools = {p.pool_id: p for p in model.pools}
    omitted_awards = {} if "base" in pools else {"base": None}
    for fact in financial.pools:
        if fact.pool_id not in pools:
            omitted_awards[fact.pool_id] = 0 if _pool_excluded(fact) else None
            continue
        supplied = pools[fact.pool_id].membership
        for key in ("participation", "entitlement"):
            if getattr(fact, key) not in ("unknown", getattr(supplied, key)):
                raise ValueError("Pool membership conflicts with the cutoff.")
    return pools, dict(sorted(omitted_awards.items()))


def _value_leaf(prefix, model, pools, omitted_awards, world, weight, current, leaf):
    p = prefix.prepared
    if len(leaf.future_games) != p.remaining_including_current - 1:
        raise ValueError("Future games must cover exactly the remaining positions after this game.")
    points = p.personal_points + current.total_performance_points
    losses = p.own_losses + current.own_games_lost
    for game in leaf.future_games:
        row = game.contribution(prefix)
        points += row.total_performance_points
        losses += row.own_games_lost

    standings = {s.pool_id: s for s in leaf.standings}
    if standings.keys() - pools.keys() - omitted_awards.keys():
        raise ValueError("Unselected pool in scenario.")
    awards = list(omitted_awards.items())
    gaps = [f"{key}:missing_pool_basis" for key, award in awards if award is None]
    for key, pool in pools.items():
        award, reason = _award(pool, standings.get(key), points, model.payout_source)
        awards.append((key, award))
        if reason:
            gaps.append(f"{key}:{reason}")
    prize = None if gaps else sum(value for _, value in awards)
    fees = None
    if (model.fee_rule == STANDARD_RULE and p.terms.financial.fee_source == STANDARD_SOURCE
            and p.terms.platform in (None, "euroskat")):
        fees = additional_loss_fee_cents(p.own_losses, losses)
    else:
        gaps.append("loss_rule_unconfirmed")
    transfer = leaf.transfer_cents
    if transfer is None:
        gaps.append("future_transfer_unknown")
    if p.terms.mode == "tournament_cent":
        if leaf.tournament_side_cents is None:
            gaps.append("tournament_side_unresolved")
            transfer = None
        elif transfer is not None:
            transfer += leaf.tournament_side_cents
    elif leaf.tournament_side_cents is not None:
        raise ValueError("Unexpected tournament side settlement.")
    other = leaf.other_charge_cents
    if other is None:
        gaps.append("future_charge_unknown")
    cost = None if fees is None or other is None else fees + other
    money = Money(prize, transfer, fees, other, cost, None if gaps else prize + transfer - cost)
    return ValuedOutcome(world.world_id, leaf.scenario_id, weight * leaf.probability,
                         points, losses, tuple(awards), money, tuple(gaps))


def _expectation(outcomes, component):
    total = Fraction()
    for row in outcomes:
        if row.weight:
            value = getattr(row.money, component)
            if value is None:
                return None
            total += row.weight * value
    return total


def evaluate_tournament_money(prefix: TournamentPrefix, model: TournamentModel,
                              candidates: tuple[Candidate, ...]) -> Comparison:
    """Value exactly the supplied joint model. Never impute or reweight missing outcomes."""
    _bounded_tuple(candidates, 10, Candidate)
    unique(tuple(c.name for c in candidates))
    if not candidates or model.prefix_id != prefix.fingerprint:
        raise ValueError("Expected candidates bound to this exact tournament prefix.")
    pools, omitted_awards = _pool_basis(prefix, model)
    weights = dict(model.worlds)
    values = []
    declarers = set()
    for candidate in candidates:
        if candidate.basis != model or {w.world_id for w in candidate.worlds} != weights.keys():
            raise ValueError("Candidates must cover the same complete world and monetary basis.")
        outcomes = []
        for world in candidate.worlds:
            current = world.current_game.contribution(prefix)
            declarers.add(world.current_game.declarer_id)
            if len(declarers) > 1 or (current.passed_deal_count and prefix.prepared.actor_id):
                raise ValueError("Card alternatives cannot change the current declarer or pass.")
            for leaf in world.continuations:
                outcomes.append(_value_leaf(prefix, model, pools, omitted_awards, world,
                                            weights[world.world_id], current, leaf))
        expected = Money(*(_expectation(outcomes, f.name) for f in fields(Money)))
        total = None if model.sunk_net_cents is None or expected.net_cents is None else (
            model.sunk_net_cents + expected.net_cents)
        values.append(CandidateValue(candidate.name, tuple(outcomes), expected, total))
    ranking = ()
    if all(c.expected.net_cents is not None for c in values):
        levels = sorted({c.expected.net_cents for c in values}, reverse=True)
        ranking = tuple(tuple(c.name for c in values if c.expected.net_cents == net)
                        for net in levels)
    return Comparison(model, tuple(values), ranking)
