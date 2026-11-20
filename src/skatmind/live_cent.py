"""Private three-game Cent objective. No account postings or actor observations."""

from dataclasses import dataclass, replace
from fractions import Fraction

from .exact_search_state import get_exact_search_terminal_facts
from .exact_terminal_utility import _settled_terminal_utility
from .hidden_card_inference import count_compatible_hidden_worlds, iter_compatible_hidden_worlds
from .matador_inference import get_trump_order_for_matadors, infer_matadors_from_declarer_cards
from .mode_accounting import cent_transfers


@dataclass(frozen=True, slots=True)
class LiveCentTerms:
    # Event participant IDs in decision-relative (me, left, right) order.
    players: tuple[str, str, str]
    tariff: str
    provider_fees: bool

    def personal_transfer(self, declarer, settlement):
        index = ("me", "left", "right").index(declarer)
        personal = cent_transfers(self.players, self.players[index], settlement, self.tariff,
                                  provider_fees=self.provider_fees)[0]
        return personal.gross.value, None if personal.net is None else personal.net.value


def _declarer_plays(view):
    plays = [play for trick in view.completed_tricks for play in trick.plays]
    return [p.card for p in (*plays, *view.current_trick) if p.player == view.declarer_player]


def matador_draws(space, n, rng, hook, *, count):
    """Partition the ordinary DP by 'with' / 'without'; weight by exact assignment counts."""
    view, problem = space._information_view, space._assignment_problem
    order = get_trump_order_for_matadors(view.game_type)
    owned = set(_declarer_plays(view)) | set(view.known_skat_cards)
    if view.declarer_player == "me":
        owned.update(view.local_remaining_hand)
    branches = []
    for with_top in (True, False):
        required = {card: (i < count) == with_top for i, card in enumerate(order[:count+1])}
        if any((card in owned) != wanted for card, wanted in required.items()
               if card not in problem.cards):
            continue
        locations = tuple((card, tuple(owner for owner in owners if card not in required
            or (owner in ("skat", view.declarer_player)) == required[card]))
            for card, owners in problem.allowed_locations_by_card)
        if any(not owners for _, owners in locations):
            continue
        branch = replace(problem, allowed_locations_by_card=locations)
        weight = (space.compatible_world_count if branch == problem else
                  count_compatible_hidden_worlds(branch, work_hook=hook))
        if weight:
            branches.append((weight, iter_compatible_hidden_worlds(branch, n, rng, work_hook=hook)))
    total = sum(weight for weight, _ in branches)
    if not total:
        return 0, ()

    def draws():
        for _ in range(n):
            index = int(len(branches) == 2 and rng.randrange(total) >= branches[0][0])
            yield next(branches[index][1])

    return total, draws()


def cent_terminal_for_world(view):
    prefix = _declarer_plays(view)

    def for_world(root):
        exact = root.exact_state
        declaration = view.declaration
        if view.game_type != "null":
            count = infer_matadors_from_declarer_cards(view.game_type, [
                *prefix, *exact.hand_for(view.declarer_player), *exact.out_of_play_cards])
            declaration = replace(declaration, matadors=count)

        def terminal(state, card, objective, side):
            utility = _settled_terminal_utility(get_exact_search_terminal_facts(state),
                declaration, side, view.game_type == "null")
            return (int(utility.local_contract_success), utility.local_side_game_score,
                    utility.local_side_card_point_margin)

        return terminal

    return for_world


class CentComparison:
    def __init__(self, cards, terms, declarer):
        self.gross = dict.fromkeys(cards, Fraction())
        self.net = dict(self.gross)
        self.terms, self.declarer = terms, declarer
        self.transfers = {}  # Per attempt, keyed by signed declarer settlement.

    def add(self, card, local_score):
        settlement = local_score if self.declarer == "me" else -local_score
        if settlement not in self.transfers:
            self.transfers[settlement] = self.terms.personal_transfer(self.declarer, settlement)
        gross, net = self.transfers[settlement]
        self.gross[card] += gross
        if net is None:
            self.net = None  # One unresolved personal outcome rules out net for every candidate.
        elif self.net is not None:
            self.net[card] += net

    def means(self, count):
        totals = self.gross if self.net is None else self.net
        return ("gross" if self.net is None else "net",
                {card: value / count for card, value in totals.items()})
