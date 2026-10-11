"""Private version-1 whole-game rollout values; not a public method contract."""

from dataclasses import asdict, dataclass, field
from math import isfinite
from typing import Literal

from skatmind.public_hand_constraint import canonicalize_cards

RolloutObjective = Literal["played_game_goal", "complete_settlement"]
ROLLOUT_METHOD = "whole_game_candidate_rollout"
ROLLOUT_VERSION = 1
ROLLOUT_POLICY = "side_aware_baseline"
ROLLOUT_POLICY_VERSION = 1
ROLLOUT_LIMITATIONS = (
    "fixed_policy_conditioned_outcomes_not_optimal_play",
    "uniform_compatible_assignments_not_calibrated_probabilities",
    "normal_suit_and_grand_completion_only",
    "no_auction_or_behavioral_inference",
    "internal_only_pending_recorded_review_integration",
)


def _bounded_integer(value: int, name: str, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}].")


@dataclass(frozen=True, slots=True, kw_only=True)
class WholeGameRolloutSettingsV1:
    random_seed: int
    objective: RolloutObjective = "played_game_goal"
    requested_worlds: int = 100
    max_card_transitions: int = 300_000
    max_preparation_work: int = 100_000
    wall_clock_timeout_ms: int | None = None

    def __post_init__(self) -> None:
        _bounded_integer(self.random_seed, "random_seed", 0, 2**64 - 1)
        _bounded_integer(self.requested_worlds, "requested_worlds", 1, 1000)
        _bounded_integer(self.max_card_transitions, "max_card_transitions", 1, 300_000)
        _bounded_integer(self.max_preparation_work, "max_preparation_work", 1, 100_000)
        if self.wall_clock_timeout_ms is not None:
            _bounded_integer(self.wall_clock_timeout_ms, "wall_clock_timeout_ms", 1, 3_600_000)
        if self.objective not in ("played_game_goal", "complete_settlement"):
            raise ValueError("Unsupported whole-game rollout objective.")


@dataclass(frozen=True, slots=True)
class WholeGameRolloutWorkV1:
    preparation_units: int = 0
    sampled_worlds: int = 0
    materialized_worlds: int = 0
    card_transitions: int = 0
    terminal_evaluations: int = 0
    elapsed_ms: float = field(default=0.0, compare=False)

    def __post_init__(self) -> None:
        for name in ("preparation_units", "sampled_worlds", "materialized_worlds",
                     "card_transitions", "terminal_evaluations"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if self.materialized_worlds > self.sampled_worlds:
            raise ValueError("Materialized worlds cannot exceed sampled worlds.")
        if not isfinite(self.elapsed_ms) or self.elapsed_ms < 0:
            raise ValueError("elapsed_ms must be finite and non-negative.")


@dataclass(frozen=True, slots=True)
class WholeGameRolloutCandidateV1:
    card: str
    completed_samples: int
    local_success_count: int
    total_local_card_point_margin: int
    total_local_game_score: int | None
    total_declarer_points: int
    total_defender_points: int
    total_declarer_tricks: int
    total_defender_tricks: int

    def __post_init__(self) -> None:
        _bounded_integer(self.completed_samples, "completed_samples", 0, 1000)
        _bounded_integer(self.local_success_count, "local_success_count", 0, self.completed_samples)
        if type(self.total_local_card_point_margin) is not int:
            raise ValueError("A candidate requires an integer card-point margin total.")
        if self.total_local_game_score is not None and type(self.total_local_game_score) is not int:
            raise ValueError("A settlement score total must be an integer or absent.")
        for name in ("total_declarer_points", "total_defender_points",
                     "total_declarer_tricks", "total_defender_tricks"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if self.total_declarer_points + self.total_defender_points != 120 * self.completed_samples:
            raise ValueError("Candidate final points must total 120 per completed sample.")
        if self.total_declarer_tricks + self.total_defender_tricks != 10 * self.completed_samples:
            raise ValueError("Candidate trick counts must total ten per completed sample.")

    def comparison_key(self) -> tuple[int, ...]:
        """Integer totals avoid floating-point tie artifacts at common coverage."""
        if self.total_local_game_score is None:
            return self.local_success_count, self.total_local_card_point_margin
        return (
            self.local_success_count,
            self.total_local_game_score,
            self.total_local_card_point_margin,
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        count = self.completed_samples
        result.update(
            sampled_local_success_fraction=self.local_success_count / count if count else None,
            mean_final_local_card_point_margin=(
                self.total_local_card_point_margin / count if count else None
            ),
            mean_local_game_score=(
                self.total_local_game_score / count
                if count and self.total_local_game_score is not None else None
            ),
        )
        return result


@dataclass(frozen=True, slots=True)
class WholeGameRolloutResultV1:
    settings: WholeGameRolloutSettingsV1
    source: str
    information_cutoff: str
    source_fingerprint: str
    game_type: str
    local_side: str | None
    remaining_tricks: int
    status: str
    stop_reason: str
    compatible_world_count: int | None
    unique_sampled_worlds: int
    completed_common_worlds: int
    candidates: tuple[WholeGameRolloutCandidateV1, ...]
    ranked_cards: tuple[str, ...]
    tied_best_cards: tuple[str, ...]
    recommended_card: str | None
    work: WholeGameRolloutWorkV1

    def __post_init__(self) -> None:
        for name in ("candidates", "ranked_cards", "tied_best_cards"):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be a tuple.")
        cards = tuple(item.card for item in self.candidates)
        if cards != canonicalize_cards(cards) or len(cards) != len(set(cards)):
            raise ValueError("Result candidates must be unique and canonical.")
        _bounded_integer(self.completed_common_worlds, "completed_common_worlds",
                         0, self.settings.requested_worlds)
        _bounded_integer(self.unique_sampled_worlds, "unique_sampled_worlds",
                         0, self.work.sampled_worlds)
        if self.work.sampled_worlds > self.settings.requested_worlds:
            raise ValueError("Sampling exceeds the requested world count.")
        if self.completed_common_worlds > self.work.materialized_worlds:
            raise ValueError("Common coverage exceeds materialized worlds.")
        if self.work.preparation_units > self.settings.max_preparation_work or (
            self.work.card_transitions > self.settings.max_card_transitions
        ):
            raise ValueError("Consumed work exceeds its configured limit.")
        for candidate in self.candidates:
            if candidate.completed_samples != self.completed_common_worlds:
                raise ValueError("Every candidate must retain identical common coverage.")
            if (candidate.total_local_game_score is None) != (self.objective == "played_game_goal"):
                raise ValueError("Candidate scores must match the selected objective.")
        if self.status == "complete":
            if self.completed_common_worlds != self.settings.requested_worlds or not cards:
                raise ValueError("A complete result requires every requested common world.")
            expected = sorted(self.candidates, key=lambda item: item.comparison_key(), reverse=True)
            ties = tuple(c.card for c in expected
                         if c.comparison_key() == expected[0].comparison_key())
            if self.ranked_cards != tuple(c.card for c in expected) or (
                self.tied_best_cards != ties or self.recommended_card != ties[0]
            ):
                raise ValueError(
                    "Complete ranking must preserve objective ties and canonical order."
                )
        elif self.status not in ("unavailable", "partial", "timeout", "cancelled"):
            raise ValueError("Invalid rollout result status.")
        elif self.ranked_cards or self.tied_best_cards or self.recommended_card is not None:
            raise ValueError("Incomplete rollout results cannot rank or recommend candidates.")

    @property
    def objective(self) -> RolloutObjective:
        return self.settings.objective

    @property
    def limitations(self) -> tuple[str, ...]:
        return ROLLOUT_LIMITATIONS + (
            ("played_goal_excludes_overbid_and_complete_settlement",)
            if self.objective == "played_game_goal" else ()
        )

    def to_dict(self) -> dict:
        """Aggregate-only output, with no retained worlds, observations, or paths."""
        return {
            "method": ROLLOUT_METHOD,
            "method_version": ROLLOUT_VERSION,
            "objective": self.objective,
            "objective_version": 1,
            "policy": {
                "profile": ROLLOUT_POLICY,
                "version": ROLLOUT_POLICY_VERSION,
                "declarer_lead": "basic_trick_play",
                "declarer_response": "basic_trick_play",
                "defender_lead": "basic_defender_lead",
                "defender_response": "basic_defender_response",
                "tie_break": "first_canonical_preferred_card",
            },
            "sampling": "uniform_iid_with_replacement",
            "settings": asdict(self.settings),
            "source": self.source,
            "information_cutoff": self.information_cutoff,
            "source_fingerprint": self.source_fingerprint,
            "game_type": self.game_type,
            "local_side": self.local_side,
            "remaining_tricks": self.remaining_tricks,
            "status": self.status,
            "stop_reason": self.stop_reason,
            "requested_worlds": self.settings.requested_worlds,
            "compatible_world_count": self.compatible_world_count,
            "unique_sampled_worlds": self.unique_sampled_worlds,
            "completed_common_worlds": self.completed_common_worlds,
            "candidate_count": len(self.candidates),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "ranked_cards": list(self.ranked_cards),
            "tied_best_cards": list(self.tied_best_cards),
            "recommended_card": self.recommended_card,
            "work": asdict(self.work),
            "limitations": list(self.limitations),
        }
