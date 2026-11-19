"""Private current-decision outcomes. No actual-card annotation or archive representation."""

from dataclasses import dataclass
from time import monotonic

from skatmind.bounded_search_information import build_live_search_information_view
from skatmind.exact_search_state import get_exact_search_terminal_facts
from skatmind.exact_terminal_utility import build_exact_terminal_utility
from skatmind.game_continuation import get_game_continuation_from_input, resolve_game_continuation
from skatmind.game_result import get_null_contract_winner_from_completed_tricks
from skatmind.input_loader import build_game_state_from_input
from skatmind.ouvert_simulation import (
    build_declared_ouvert_public_hand_constraint,
    resolve_effective_public_hand_constraints,
)
from skatmind.rules import get_card_strength, get_effective_suit
from skatmind.whole_game_rollout import (
    _completed_batches,
    _prepare_common_worlds,
    _Stopped,
    _Work,
    evaluate_whole_game_rollout_v1,
)
from skatmind.whole_game_rollout_contracts import (
    ROLLOUT_POLICY,
    WholeGameRolloutSettingsV1,
    WholeGameRolloutWorkV1,
)
from skatmind.whole_game_rollout_workflow import rollout_declaration


@dataclass(frozen=True, slots=True)
class LiveCardOutcome:
    card: str
    successes: int
    total_game_score: int | None
    total_point_margin: int | None


@dataclass(frozen=True, slots=True)
class LiveGameOutcome:
    settings: WholeGameRolloutSettingsV1
    policy: str
    policy_version: int
    local_side: str
    status: str
    stop_reason: str
    completed_common_worlds: int
    candidates: tuple[LiveCardOutcome, ...]
    ranked_cards: tuple[str, ...]
    tied_best_cards: tuple[str, ...]
    work: WholeGameRolloutWorkV1

    def __post_init__(self):
        common = self.completed_common_worlds
        if not 0 <= common <= self.settings.requested_worlds or any(
                not 0 <= c.successes <= common for c in self.candidates):
            raise ValueError("Inconsistent Live common-world coverage.")
        if self.status == "complete":
            if common != self.settings.requested_worlds or not self.tied_best_cards:
                raise ValueError("Live recommendations require all requested common worlds.")
        elif self.ranked_cards or self.tied_best_cards:
            raise ValueError("Incomplete Live advice cannot recommend cards.")


def live_rollout_view(data):
    """Input is the validated, visibility-filtered Session Position export."""
    if (data.get("analysis_mode") != "live_decision" or "actual_card_played" in data
            or data.get("game_end_reason") != "not_ended" or data.get("game_shortening")
            or data.get("played_cards") or data["next_player"] != "me"):
        raise ValueError("Expected an attributed current Session decision.")
    declaration = rollout_declaration(data)
    constraints = []
    ouvert = build_declared_ouvert_public_hand_constraint(data, declaration)
    if ouvert is not None:
        constraints.append(ouvert)
    continuation = get_game_continuation_from_input(data)
    if continuation is not None:
        constraints.append(resolve_game_continuation(data, continuation).public_hand_constraint)
    return build_live_search_information_view(
        state=build_game_state_from_input(data), declaration=declaration,
        left_hand_size=data["left_hand_size"], right_hand_size=data["right_hand_size"],
        skat_visibility=data["skat_visibility"],
        public_hand_constraints=resolve_effective_public_hand_constraints(tuple(constraints)))


def _null_card(observation):
    """Duck as declarer; lead low or keep the declarer winning as defender."""
    legal = observation.legal_cards  # Canonical order breaks equal preferences.
    trick = observation.current_trick
    def rank(card):
        return get_card_strength(card, "null", get_effective_suit(card, "null"))
    if not trick:
        return min(legal, key=rank)
    suit = get_effective_suit(trick[0].card, "null")
    def strength(card):
        return get_card_strength(card, "null", suit)
    winning = max(trick, key=lambda play: strength(play.card))
    below = [card for card in legal if strength(card) < strength(winning.card)]
    if below and (observation.actor_side == "declarer"
                  or winning.player == observation.declarer_player):
        return max(below, key=rank)
    return min(legal, key=rank)


def _null_terminal(state, card, objective, side):
    if objective == "complete_settlement":
        utility = build_exact_terminal_utility(state=state, local_side=side)
        return int(utility.local_contract_success), utility.local_side_game_score
    facts = get_exact_search_terminal_facts(state)
    roles = ([{"winner_role": "declarer"}] * facts.declarer_trick_count
             + [{"winner_role": "defenders"}] * facts.defender_trick_count)
    winner = get_null_contract_winner_from_completed_tricks(roles)
    return int(winner == side), None


def evaluate_live_game(view, *, worlds, timeout_ms, cancelled=None, clock=monotonic):
    if view.source != "live_local_view" or view.next_player != "me" or view.local_side is None:
        raise ValueError("Live rollout requires the current perspective player's decision.")
    d = view.declaration
    # A known overbid Null must be rejected by preparation, not downgraded to played goal.
    missing = d.bid_value is None or (d.game_type != "null" and d.matadors is None)
    objective = "played_game_goal" if missing else "complete_settlement"
    settings = WholeGameRolloutSettingsV1(random_seed=0, requested_worlds=worlds,
                                          wall_clock_timeout_ms=timeout_ms, objective=objective)
    if view.game_type != "null":
        result = evaluate_whole_game_rollout_v1(view, settings, clock=clock, cancelled=cancelled)
        return LiveGameOutcome(settings, ROLLOUT_POLICY, 1, view.local_side, result.status,
            result.stop_reason, result.completed_common_worlds, tuple(LiveCardOutcome(
                row.card, row.local_success_count, row.total_local_game_score,
                row.total_local_card_point_margin) for row in result.candidates),
            result.ranked_cards, result.tied_best_cards, result.work)

    prep = _prepare_common_worlds(view, settings, clock=clock, cancelled=cancelled, live_null=True)
    work = _Work(settings, clock, cancelled, prep.work)
    counts = dict.fromkeys(prep.legal_root_cards, 0)
    scores = dict.fromkeys(counts, 0 if objective == "complete_settlement" else None)
    completed = 0
    status, reason = prep.status, prep.stop_reason
    ranked = ties = ()
    if status == "ready":
        try:
            for batch in _completed_batches(prep, prep.legal_root_cards, work,
                                            _null_card, _null_terminal):
                for card, (success, score) in batch.items():
                    counts[card] += success
                    if score is not None:
                        scores[card] += score
                completed += 1
            status, reason = "complete", "completed"
            # For one fixed non-overbid Null value, settlement score depends only on
            # success. Equal counts tie; card points never order Null candidates.
            ranked = tuple(sorted(counts, key=counts.get, reverse=True))
            ties = tuple(card for card in ranked if counts[card] == counts[ranked[0]])
        except _Stopped as stop:
            status, reason = stop.status, stop.reason
    return LiveGameOutcome(settings, "null_avoid_or_force_trick", 1, view.local_side,
        status, reason, completed,
        tuple(LiveCardOutcome(card, count, scores[card], None) for card, count in counts.items()),
        ranked, ties, work.snapshot())
