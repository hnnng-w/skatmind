"""Bounded per-candidate normal-completion rollout over shared compatible worlds."""

import hashlib
import json
import random
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from time import monotonic

from skatmind.bounded_search_information import (
    SearchInformationView,
    _build_search_information_view,
    get_remaining_search_trick_count,
)
from skatmind.coherent_hidden_world import derive_simulation_child_seed
from skatmind.compatible_search_world import (
    build_compatible_search_world_space,
    build_exact_search_state_from_compatible_world,
)
from skatmind.exact_search_state import ExactSearchState, get_exact_search_terminal_facts
from skatmind.exact_terminal_utility import (
    build_exact_terminal_utility,
    has_supported_terminal_utility_inputs,
)
from skatmind.final_settlement import (
    is_schneider_announcement_failed,
    is_schwarz_announcement_failed,
)
from skatmind.game_declaration import SUIT_GAME_TYPES
from skatmind.game_result import build_game_result_summary_from_points
from skatmind.game_state import GameState
from skatmind.game_value import build_game_value_summary
from skatmind.hidden_card_inference import iter_compatible_hidden_worlds
from skatmind.information_set_search_state import (
    InformationSetSearchWorldStateV1,
    apply_information_set_search_card_v1,
    build_information_set_search_observation_v1,
    build_information_set_search_world_state_v1,
)
from skatmind.public_hand_constraint import canonicalize_cards
from skatmind.rules import get_legal_cards
from skatmind.turn_phase import CONCRETE_PLAYERS
from skatmind.whole_game_rollout_contracts import (
    WholeGameRolloutCandidateV1,
    WholeGameRolloutResultV1,
    WholeGameRolloutSettingsV1,
    WholeGameRolloutWorkV1,
)
from skatmind.whole_game_rollout_policy import select_whole_game_rollout_card_v1


@dataclass(frozen=True, slots=True, init=False)
class WholeGameRolloutPreparationV1:
    """Builder-owned preparation. Private roots deliberately have no serializer."""

    information_view: SearchInformationView = field(repr=False)
    settings: WholeGameRolloutSettingsV1
    source_fingerprint: str
    legal_root_cards: tuple[str, ...]
    remaining_tricks: int
    status: str
    stop_reason: str
    compatible_world_count: int | None
    unique_sampled_worlds: int
    work: WholeGameRolloutWorkV1
    _worlds: tuple[InformationSetSearchWorldStateV1, ...] = field(repr=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("Use prepare_whole_game_rollout_v1().")


class _Stopped(Exception):
    def __init__(self, status: str, reason: str):
        self.status = status
        self.reason = reason


class _Work:
    def __init__(
        self,
        settings: WholeGameRolloutSettingsV1,
        clock: Callable[[], float],
        cancelled: Callable[[], bool] | None,
        prior: WholeGameRolloutWorkV1 | None = None,
    ) -> None:
        prior = prior or WholeGameRolloutWorkV1()
        self.settings = settings
        self.clock = clock
        self.cancelled = cancelled
        self.start = clock()
        self.prior_elapsed_ms = prior.elapsed_ms
        self.preparation_units = prior.preparation_units
        self.sampled_worlds = prior.sampled_worlds
        self.materialized_worlds = prior.materialized_worlds
        self.card_transitions = prior.card_transitions
        self.terminal_evaluations = prior.terminal_evaluations

    def elapsed(self) -> float:
        return self.prior_elapsed_ms + max(0.0, (self.clock() - self.start) * 1000)

    def check(self) -> None:
        if self.cancelled is not None and self.cancelled():
            raise _Stopped("cancelled", "cancelled")
        limit = self.settings.wall_clock_timeout_ms
        if limit is not None and self.elapsed() >= limit:
            raise _Stopped("timeout", "wall_clock_timeout")

    def prepare_unit(self) -> None:
        self.check()
        if self.preparation_units >= self.settings.max_preparation_work:
            raise _Stopped("partial", "preparation_budget_exhausted")
        self.preparation_units += 1

    def transition(self) -> None:
        self.check()
        if self.card_transitions >= self.settings.max_card_transitions:
            raise _Stopped("partial", "transition_budget_exhausted")
        self.card_transitions += 1

    def snapshot(self) -> WholeGameRolloutWorkV1:
        return WholeGameRolloutWorkV1(
            self.preparation_units, self.sampled_worlds, self.materialized_worlds,
            self.card_transitions, self.terminal_evaluations, self.elapsed(),
        )


def _validate_view(view: SearchInformationView) -> None:
    """Reconcile a supplied immutable view against the original safe-view builder."""
    state = GameState(
        game_type=view.game_type,
        player_role=(
            "declarer" if view.declarer_player == "me"
            else "defender" if view.declarer_player in ("left", "right") else "unknown"
        ),
        declarer_player=view.declarer_player,
        hand=list(view.local_remaining_hand),
        current_trick=[play.card for play in view.current_trick],
        completed_tricks=[
            {
                "cards": [play.card for play in trick.plays],
                "players": [play.player for play in trick.plays],
                "winner_player": trick.winner_player,
                "winner_role": trick.winner_side,
            }
            for trick in view.completed_tricks
        ],
        trick_leader=view.current_trick[0].player if view.current_trick else view.next_player,
        next_player=view.next_player,
    )
    rebuilt = _build_search_information_view(
        source=view.source, state=state, declaration=view.declaration,
        left_hand_size=view.remaining_hand_size("left"),
        right_hand_size=view.remaining_hand_size("right"),
        known_skat_cards=view.known_skat_cards,
        public_hand_constraints=view.public_hand_constraints,
        perspective_player=view.perspective_player,
    )
    if rebuilt != view:
        raise ValueError("Rollout information must match its canonical decision-time facts.")
    if view.known_skat_cards and view.declarer_player != "me":
        raise ValueError("A defender rollout cannot use private Skat knowledge.")
    if len(view.completed_tricks) + get_remaining_search_trick_count(view) != 10:
        raise ValueError("Rollout requires a complete attributed normal-play prefix.")
    if view.declaration.ouvert and not any(
        item.player == view.declarer_player for item in view.public_hand_constraints
    ):
        raise ValueError("An Ouvert rollout requires the authorized public declarer hand.")


def _unavailable_reason(
    view: SearchInformationView,
    settings: WholeGameRolloutSettingsV1,
    remaining: int,
    cards: tuple[str, ...],
) -> str | None:
    if view.game_type not in (*SUIT_GAME_TYPES, "grand"):
        return "unsupported_game_type"
    if view.perspective_player != "me":
        return "unsupported_perspective"
    if view.declarer_player not in CONCRETE_PLAYERS or view.local_side is None:
        return "missing_concrete_declarer"
    if remaining == 0:
        return "game_already_complete"
    if not 1 <= remaining <= 10:
        return "remaining_trick_limit_exceeded"
    if view.next_player not in CONCRETE_PLAYERS:
        return "unsupported_turn_phase"
    if view.next_player != "me":
        return "local_player_not_to_act"
    if not cards:
        return "no_legal_cards"
    if settings.objective == "complete_settlement" and not has_supported_terminal_utility_inputs(
        view.declaration
    ):
        return "missing_terminal_utility_inputs"
    return None


def prepare_whole_game_rollout_v1(
    information_view: SearchInformationView,
    settings: WholeGameRolloutSettingsV1,
    *,
    clock: Callable[[], float] = monotonic,
    cancelled: Callable[[], bool] | None = None,
) -> WholeGameRolloutPreparationV1:
    """Validate one safe root and freeze bounded IID draws before candidate execution."""
    if not isinstance(information_view, SearchInformationView):
        raise ValueError("information_view must be a SearchInformationView.")
    if not isinstance(settings, WholeGameRolloutSettingsV1):
        raise ValueError("settings must be WholeGameRolloutSettingsV1.")
    work = _Work(settings, clock, cancelled)
    view = information_view
    _validate_view(view)
    fingerprint = hashlib.sha256(
        b"skatmind.whole_game_rollout.source.v1\0"
        + json.dumps(asdict(view), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    remaining = get_remaining_search_trick_count(view)
    cards = canonicalize_cards(tuple(get_legal_cards(
        list(view.local_remaining_hand), [play.card for play in view.current_trick], view.game_type
    )))
    reason = _unavailable_reason(view, settings, remaining, cards)
    status = "unavailable" if reason else "ready"
    count = None
    worlds = []
    sampled = set()
    try:
        work.prepare_unit()  # Bounded root validation and fingerprint work.
        if reason is None:
            work.prepare_unit()  # At most 32 cards of assignment-problem construction.
            space = build_compatible_search_world_space(view, work_hook=work.prepare_unit)
            count = space.compatible_world_count
            if count == 0:
                status, reason = "unavailable", "incompatible_world_space"
            else:
                rng = random.Random(derive_simulation_child_seed(
                    settings.random_seed, "whole_game_rollout_worlds_v1"
                ))
                for world in iter_compatible_hidden_worlds(
                    space._assignment_problem, settings.requested_worlds, rng,
                    work_hook=work.prepare_unit,
                ):
                    work.sampled_worlds += 1
                    sampled.add(world)
                    work.prepare_unit()  # One bounded exact/public root reconciliation.
                    exact = build_exact_search_state_from_compatible_world(
                        world_space=space, world=world
                    )
                    root = build_information_set_search_world_state_v1(
                        information_view=view, exact_state=exact,
                        allow_partial_root_skat_knowledge=True,
                    )
                    if build_information_set_search_observation_v1(root).legal_cards != cards:
                        raise ValueError("Compatible roots disagree on legal candidates.")
                    worlds.append(root)
                    work.materialized_worlds += 1
                work.check()
    except _Stopped as stop:
        status, reason = stop.status, stop.reason
    result = object.__new__(WholeGameRolloutPreparationV1)
    for name, value in {
        "information_view": view, "settings": settings, "source_fingerprint": fingerprint,
        "legal_root_cards": cards, "remaining_tricks": remaining, "status": status,
        "stop_reason": reason or "prepared", "compatible_world_count": count,
        "unique_sampled_worlds": len(sampled), "work": work.snapshot(),
        "_worlds": tuple(worlds),
    }.items():
        object.__setattr__(result, name, value)
    return result


def _terminal_candidate(
    state: ExactSearchState, card: str, objective: str, local_side: str
) -> WholeGameRolloutCandidateV1:
    facts = get_exact_search_terminal_facts(state)
    orientation = 1 if local_side == "declarer" else -1
    margin = orientation * (facts.declarer_final_points - facts.defender_final_points)
    score = None
    if objective == "complete_settlement":
        utility = build_exact_terminal_utility(state=state, local_side=local_side)
        success = utility.local_contract_success
        score = utility.local_side_game_score
        margin = utility.local_side_card_point_margin
        if margin is None:
            raise ValueError("Suit/Grand terminal utility must retain a card-point margin.")
    else:
        result = build_game_result_summary_from_points(
            facts.declarer_final_points, facts.defender_final_points
        )
        value = build_game_value_summary(state.declaration)
        tricks = [
            *({"winner_role": "declarer"} for _ in range(facts.declarer_trick_count)),
            *({"winner_role": "defenders"} for _ in range(facts.defender_trick_count)),
        ]
        declarer_success = (
            result["winner"] == "declarer"
            and not is_schneider_announcement_failed(value, result)
            and not is_schwarz_announcement_failed(value, result, tricks)
        )
        success = declarer_success if local_side == "declarer" else not declarer_success
    return WholeGameRolloutCandidateV1(
        card, 1, int(success), margin, score,
        facts.declarer_final_points, facts.defender_final_points,
        facts.declarer_trick_count, facts.defender_trick_count,
    )


def _sum_candidates(
    left: WholeGameRolloutCandidateV1, right: WholeGameRolloutCandidateV1
) -> WholeGameRolloutCandidateV1:
    if (left.total_local_game_score is None) != (right.total_local_game_score is None):
        raise ValueError("Cannot combine different rollout objectives.")
    return WholeGameRolloutCandidateV1(
        left.card, left.completed_samples + right.completed_samples,
        left.local_success_count + right.local_success_count,
        left.total_local_card_point_margin + right.total_local_card_point_margin,
        None if left.total_local_game_score is None else (
            left.total_local_game_score + right.total_local_game_score
        ),
        left.total_declarer_points + right.total_declarer_points,
        left.total_defender_points + right.total_defender_points,
        left.total_declarer_tricks + right.total_declarer_tricks,
        left.total_defender_tricks + right.total_defender_tricks,
    )


def execute_whole_game_rollout_v1(
    preparation: WholeGameRolloutPreparationV1,
    *,
    clock: Callable[[], float] = monotonic,
    cancelled: Callable[[], bool] | None = None,
    candidate_order: tuple[str, ...] | None = None,
) -> WholeGameRolloutResultV1:
    """Complete independent candidate paths, publishing only common completed batches.

    candidate_order is a private scheduling permutation, never a candidate subset.
    Preparation time counts toward timeout; idle time between the two calls does not.
    """
    if not isinstance(preparation, WholeGameRolloutPreparationV1):
        raise ValueError("preparation must be WholeGameRolloutPreparationV1.")
    p = preparation
    order = p.legal_root_cards if candidate_order is None else candidate_order
    if not isinstance(order, tuple) or (
        len(order) != len(p.legal_root_cards) or set(order) != set(p.legal_root_cards)
    ):
        raise ValueError("candidate_order must permute all legal root cards exactly once.")
    work = _Work(p.settings, clock, cancelled, p.work)
    score_zero = 0 if p.settings.objective == "complete_settlement" else None
    totals = {
        card: WholeGameRolloutCandidateV1(card, 0, 0, 0, score_zero, 0, 0, 0, 0)
        for card in p.legal_root_cards
    }
    completed = 0
    status, reason = p.status, p.stop_reason
    if status == "ready":
        try:
            for root in p._worlds:
                batch = {}
                for card in order:
                    work.transition()
                    child = apply_information_set_search_card_v1(root, card)
                    while not child.exact_state.is_terminal:
                        work.transition()
                        observation = build_information_set_search_observation_v1(child)
                        action = select_whole_game_rollout_card_v1(observation)
                        child = apply_information_set_search_card_v1(child, action)
                    work.check()
                    batch[card] = _terminal_candidate(
                        child.exact_state, card, p.settings.objective, p.information_view.local_side
                    )
                    work.terminal_evaluations += 1
                # Commit the entire common draw atomically, including duplicate draws.
                work.check()
                totals = {card: _sum_candidates(totals[card], batch[card]) for card in totals}
                completed += 1
            status, reason = "complete", "completed"
        except _Stopped as stop:
            status, reason = stop.status, stop.reason
    candidates = tuple(totals.values())
    ranking = ()
    ties = ()
    if status == "complete":
        ranked = sorted(candidates, key=lambda item: item.comparison_key(), reverse=True)
        ranking = tuple(item.card for item in ranked)
        ties = tuple(
            item.card for item in ranked if item.comparison_key() == ranked[0].comparison_key()
        )
    return WholeGameRolloutResultV1(
        p.settings, p.information_view.source, p.information_view.information_cutoff,
        p.source_fingerprint, p.information_view.game_type, p.information_view.local_side,
        p.remaining_tricks, status, reason, p.compatible_world_count, p.unique_sampled_worlds,
        completed, candidates, ranking, ties, ranking[0] if ranking else None, work.snapshot(),
    )


def evaluate_whole_game_rollout_v1(
    information_view: SearchInformationView,
    settings: WholeGameRolloutSettingsV1,
    *,
    clock: Callable[[], float] = monotonic,
    cancelled: Callable[[], bool] | None = None,
) -> WholeGameRolloutResultV1:
    """Prepare and execute one internal analysis without changing any Root workflow."""
    return execute_whole_game_rollout_v1(
        prepare_whole_game_rollout_v1(
            information_view, settings, clock=clock, cancelled=cancelled
        ),
        clock=clock, cancelled=cancelled,
    )
