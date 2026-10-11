"""Independent list-based fixed-policy reference, using only the shared card rules.

No rollout, observation, preference, exact-transition, or terminal adapter calls
are used in the reference continuation. Synthetic prefixes also use this plain
list accounting instead of the production transition kernel.
"""

import random
from itertools import combinations

from skatmind.bounded_search_information import build_live_search_information_view
from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration
from skatmind.game_state import GameState
from skatmind.hidden_card_inference import CompatibleHiddenWorld, get_public_effective_category
from skatmind.public_hand_constraint import PublicHandConstraint, canonicalize_cards
from skatmind.rules import (
    get_card_points,
    get_card_strength,
    get_effective_suit,
    get_legal_cards,
    get_trick_points,
    get_trick_winner,
    is_trump,
)

PLAYERS = ("me", "left", "right")
DECK = tuple(get_full_deck())


def synthetic_view(
    *, seed=0, remaining=2, partial=0, declarer="me", public_players=(),
    declaration=None, known_skat=True,
):
    declaration = declaration or GameDeclaration("grand")
    game = declaration.game_type
    rng = random.Random(seed)
    deck = list(DECK)
    rng.shuffle(deck)
    hands = {player: deck[index * 10:index * 10 + 10] for index, player in enumerate(PLAYERS)}
    actor = "me"
    current = []
    completed = []
    for _ in range(30 - 3 * remaining + partial):
        card = rng.choice(get_legal_cards(hands[actor], [c for _, c in current], game))
        hands[actor].remove(card)
        current.append((actor, card))
        actor = PLAYERS[(PLAYERS.index(actor) + 1) % 3]
        if len(current) == 3:
            actor = current[get_trick_winner([c for _, c in current], game)][0]
            completed.append(current)
            current = []
    # Relative seats rotate; the current actor is always the root local player.
    offset = PLAYERS.index(actor)
    mapping = {player: PLAYERS[(index - offset) % 3] for index, player in enumerate(PLAYERS)}
    hands = {mapping[player]: canonicalize_cards(tuple(cards)) for player, cards in hands.items()}
    history = []
    for trick in completed:
        cards = [card for _, card in trick]
        players = [mapping[player] for player, _ in trick]
        winner = players[get_trick_winner(cards, game)]
        history.append({
            "cards": cards, "players": players, "winner_player": winner,
            "winner_role": "declarer" if winner == declarer else "defenders",
        })
    current = [(mapping[player], card) for player, card in current]
    public_players = tuple(dict.fromkeys((
        *public_players, *((declarer,) if declaration.ouvert else ()),
    )))
    constraints = tuple(PublicHandConstraint(
        player=player, cards=hands[player],
        source=(
            "declared_ouvert" if declaration.ouvert and player == declarer
            else "declarer_card_exposure_continuation" if player == declarer
            else "defender_open_play_continuation"
        ),
    ) for player in public_players)
    state = GameState(
        game_type=game, player_role="declarer" if declarer == "me" else "defender",
        declarer_player=declarer, hand=list(hands["me"]),
        current_trick=[card for _, card in current], completed_tricks=history,
        next_player="me", trick_leader=current[0][0] if current else "me",
        skat=deck[-2:] if known_skat and declarer == "me" and not declaration.hand_game else [],
    )
    view = build_live_search_information_view(
        state=state, declaration=declaration,
        left_hand_size=len(hands["left"]), right_hand_size=len(hands["right"]),
        skat_visibility="known_to_declarer" if state.skat else "unknown",
        public_hand_constraints=constraints,
    )
    return view, hands, canonicalize_cards(tuple(deck[-2:]))


def reference_action(hand, current, actor, declarer, game):
    """Independent transcription of the documented version-1 baseline preferences."""
    cards = [card for _, card in current]
    legal = get_legal_cards(list(hand), cards, game)
    order = DECK.index
    if not current:
        choices = legal
        if actor != declarer:
            choices = [card for card in legal if not is_trump(card, game)] or legal
        return min(choices, key=lambda card: (get_card_points(card), order(card)))
    lead = get_effective_suit(cards[0], game)
    def strength(card):
        return get_card_strength(card, game, lead)
    winner_index = max(range(len(cards)), key=lambda index: strength(cards[index]))
    winner = current[winner_index][0]
    winning = [card for card in legal if strength(card) > strength(cards[winner_index])]
    losing = [card for card in legal if card not in winning]
    if actor == declarer:
        return min(winning or legal, key=lambda card: (get_card_points(card), order(card)))
    if winner != declarer:
        return min(
            losing or legal,
            key=lambda card: (
                -get_card_points(card) if losing else get_card_points(card),
                strength(card), order(card),
            ),
        )
    if winning:
        if (
            len(cards) == 1 and get_card_points(cards[0]) == 0
            and not is_trump(cards[0], game)
            and all(is_trump(card, game) for card in winning) and losing
        ):
            return min(losing, key=lambda card: (get_card_points(card), order(card)))
        return min(winning, key=lambda card: (get_card_points(card), strength(card), order(card)))
    return min(legal, key=lambda card: (get_card_points(card), order(card)))


def reference_continuation(view, hands, skat, candidate):
    """Returns scalar terminal facts plus a test-only trace for manual inspection."""
    hands = {player: list(cards) for player, cards in hands.items()}
    current = [(play.player, play.card) for play in view.current_trick]
    points = [view.declarer_points, view.defender_points]
    tricks = [view.declarer_trick_count, view.defender_trick_count]
    actor = "me"
    trace = []
    first_trick_margin = None
    forced = candidate
    while any(hands.values()):
        card = forced or reference_action(hands[actor], current, actor, view.declarer_player,
                                         view.game_type)
        forced = None
        assert card in get_legal_cards(hands[actor], [c for _, c in current], view.game_type)
        hands[actor].remove(card)
        current.append((actor, card))
        actor = PLAYERS[(PLAYERS.index(actor) + 1) % 3]
        if len(current) == 3:
            cards = [card for _, card in current]
            actor = current[get_trick_winner(cards, view.game_type)][0]
            side = 0 if actor == view.declarer_player else 1
            value = get_trick_points(cards)
            points[side] += value
            tricks[side] += 1
            if first_trick_margin is None:
                local_won = (side == 0) == (view.local_side == "declarer")
                first_trick_margin = value if local_won else -value
            trace.append((tuple(current), actor, value))
            current = []
    assert not current
    points[0] += get_trick_points(list(skat))
    assert sum(points) == 120 and sum(tricks) == 10
    declarer_won = points[0] >= 61
    if view.declaration.schneider_announced:
        declarer_won = declarer_won and points[1] <= 30
    if view.declaration.schwarz_announced or view.declaration.ouvert:
        declarer_won = declarer_won and tricks[1] == 0
    local_won = declarer_won if view.local_side == "declarer" else not declarer_won
    margin = (points[0] - points[1]) * (1 if view.local_side == "declarer" else -1)
    return int(local_won), margin, tuple(points), tuple(tricks), first_trick_margin, tuple(trace)


def finite_worlds(view):
    """Tiny exhaustive assignment oracle; no production counter/sampler/enumerator."""
    known = {
        *view.local_remaining_hand, *view.known_skat_cards,
        *(play.card for play in view.current_trick),
        *(play.card for trick in view.completed_tricks for play in trick.plays),
    }
    unseen = tuple(card for card in DECK if card not in known)
    assert len(unseen) <= 8
    constraints = {item.player: item for item in view.hidden_card_constraints}
    public = {item.player: item.cards for item in view.public_hand_constraints}
    worlds = []
    for left in combinations(unseen, view.remaining_hand_size("left")):
        rest = tuple(card for card in unseen if card not in left)
        for right in combinations(rest, view.remaining_hand_size("right")):
            hands = {"left": left, "right": right}
            if any(
                (player in public and hand != public[player])
                or any(get_public_effective_category(card, view.game_type)
                       in constraints[player].forbidden_effective_categories for card in hand)
                for player, hand in hands.items()
            ):
                continue
            worlds.append(CompatibleHiddenWorld(
                left, right, tuple(card for card in rest if card not in right)
            ))
    return tuple(worlds)


def small_view(*, public=True, declaration=None):
    """Frozen two-Trick fixture: DA wins more now, S9 wins the played game."""
    declaration = declaration or GameDeclaration("grand")
    cards_and_players = (
        (("H7", "H8", "HQ"), ("left", "right", "me")),
        (("CA", "D8", "C7"), ("me", "left", "right")),
        (("C8", "S8", "C9"), ("me", "left", "right")),
        (("CJ", "DJ", "HJ"), ("right", "me", "left")),
        (("C10", "CQ", "HA"), ("right", "me", "left")),
        (("SJ", "DK", "H10"), ("right", "me", "left")),
        (("S7", "SA", "SK"), ("right", "me", "left")),
        (("HK", "H9", "SQ"), ("me", "left", "right")),
    )
    history = []
    for cards, players in cards_and_players:
        winner = players[get_trick_winner(list(cards), "grand")]
        history.append({
            "cards": list(cards), "players": list(players), "winner_player": winner,
            "winner_role": "declarer" if winner == "me" else "defenders",
        })
    hands = {"me": ("S9", "DA"), "left": ("D10", "D7"), "right": ("S10", "DQ")}
    skat = ("CK", "D9")
    view = build_live_search_information_view(
        state=GameState(
            game_type="grand", player_role="declarer", declarer_player="me",
            hand=list(hands["me"]), current_trick=[], completed_tricks=history,
            skat=list(skat), trick_leader="me", next_player="me",
        ),
        declaration=declaration, left_hand_size=2, right_hand_size=2,
        skat_visibility="known_to_declarer",
        public_hand_constraints=tuple(
            PublicHandConstraint(player=player, cards=hands[player],
                                 source="defender_open_play_continuation")
            for player in ("left", "right") if public
        ),
    )
    return view, hands, skat
