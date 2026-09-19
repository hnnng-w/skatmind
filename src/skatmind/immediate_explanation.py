"""Pure explanation of exact Immediate objective ties; no selection or simulation."""

from collections.abc import Mapping

from skatmind.objective_utility import (
    calculate_expected_objective_utility,
    get_best_cards_by_expected_objective,
)


def build_equal_best_immediate_explanation(
    values: Mapping[str, Mapping[str, float]], game_type: str, player_role: str,
) -> str | None:
    cards = get_best_cards_by_expected_objective(values, game_type, player_role)
    if len(cards) < 2:
        return None
    utility = calculate_expected_objective_utility(game_type, player_role, values[cards[0]])
    if game_type == "null":
        objective = (
            "avoid taking any evaluated trick" if player_role == "declarer"
            else "make the concrete declarer take an evaluated trick"
        )
        metric = (
            f"estimated Null contract-objective utility {utility:.3f}; "
            f"the objective is to {objective}"
        )
    else:
        metric = f"estimated immediate expected point swing {utility:.2f}"
    return (
        f"{', '.join(cards)} are equally best in this Immediate evaluation, each with {metric}. "
        f"{cards[0]} is selected as the representative by stable legal-card order. "
        "Equal estimates under this method do not imply whole-game equivalence."
    )
