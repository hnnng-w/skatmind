"""Deterministic version-1 baseline for every actor, including later local turns."""

from skatmind.deck import get_full_deck
from skatmind.information_set_search_state import InformationSetSearchObservationV1
from skatmind.opponent_policy import (
    determine_current_trick_winner_index,
    get_preferred_opponent_cards_by_policy,
)

_CARD_ORDER = {card: index for index, card in enumerate(get_full_deck())}


def select_whole_game_rollout_card_v1(observation: InformationSetSearchObservationV1) -> str:
    """Accepts only an actor observation; no world, seed, or shared partner hand."""
    if not isinstance(observation, InformationSetSearchObservationV1):
        raise ValueError("A rollout policy requires an actor observation.")
    if not observation.legal_cards:
        raise ValueError("A rollout policy requires legal cards.")
    current = [play.card for play in observation.current_trick]
    partner_index = 0
    partner_winning = False
    policy = "basic_trick_play"
    if observation.actor_side == "defenders":
        policy = "basic_defender_response" if current else "basic_defender_lead"
        if current:
            partner_index = determine_current_trick_winner_index(current, observation.game_type)
            partner_winning = (
                observation.current_trick[partner_index].player != observation.declarer_player
            )
    preferred = get_preferred_opponent_cards_by_policy(
        hand=list(observation.own_remaining_hand),
        current_trick=current,
        game_type=observation.game_type,
        player_index=len(current),
        policy=policy,
        partner_currently_winning=partner_winning,
        partner_index=partner_index,
    )
    if not preferred or any(card not in observation.legal_cards for card in preferred):
        raise ValueError("The rollout baseline returned an invalid preferred-card set.")
    return min(preferred, key=_CARD_ORDER.__getitem__)
