"""Atomic bidding edits to an existing rotated Match position."""

from skatmind.bidding import BidAction, BiddingContinuationConflict, replay_bidding
from skatmind.match_capture_game_updates import rebuild_match_capture_game_v1
from skatmind.match_workspace_contracts import (
    MatchPassedDealV1,
    MatchWorkspaceSlotV1,
    _require_match_position,
)
from skatmind.match_workspace_operations import _replace_slot


def edit_match_bidding(workspace, position: int, index: int, event: BidAction, *,
                       expected_revision: int, confirm_suffix: bool = False):
    """Append or replace one event. Recheck later observations before publishing any change."""
    if type(expected_revision) is not int or expected_revision != workspace.revision:
        raise ValueError("The Match revision has changed.")
    slot = workspace.slots[_require_match_position(position) - 1]
    game = slot.observed_game or slot.passed_game
    if game is None or (not slot.bidding and game.declaration is not None):
        raise ValueError("Start a game before bidding; a short declaration has no auction.")
    if type(index) is not int or not 0 <= index <= len(slot.bidding):
        raise ValueError("The selected bidding action does not exist.")
    if type(confirm_suffix) is not bool:
        raise ValueError("Continuation removal requires explicit confirmation.")
    seats = tuple(player.player_id for player in game.players)
    events = (*slot.bidding[:index], event)
    turn = replay_bidding(seats, events)
    hand = None
    if index < len(slot.bidding):
        hand = slot.bidding_hands[index]
    elif event.player_id == game.perspective_player_id:
        hand = game.perspective_initial_hand
    hands = (*slot.bidding_hands[:index], hand)
    for i in range(index + 1, len(slot.bidding)):
        candidate = (*events, slot.bidding[i])
        try:
            turn = replay_bidding(seats, candidate)
        except ValueError:
            break
        events = candidate
        hands += (slot.bidding_hands[i],)

    passed = turn.actor is None and turn.declarer is None
    declaration_conflict = game.declaration is not None and (
        game.declarer_player_id != turn.declarer
        or game.declaration.bid_value != turn.effective_value)
    remove_continuation = declaration_conflict or (passed and game.discarded_cards is not None)
    removed = len(slot.bidding) - len(events) if index < len(slot.bidding) else 0
    if remove_continuation:
        removed += (int(declaration_conflict) + int(game.discarded_cards is not None)
                    + len(game.plays) + len(game.commentaries) + len(game.response_links))
    if removed and not confirm_suffix:
        raise BiddingContinuationConflict(removed)
    if remove_continuation:
        game = rebuild_match_capture_game_v1(workspace, game, declarer_player_id=None,
            declaration=None, discarded_cards=None, plays=(), commentaries=(), response_links=())
    updated = MatchWorkspaceSlotV1._from_validated(
        match_position=position, slot_kind="passed_deal" if passed else "observed_game",
        observed_game=None if passed else game, passed_game=game if passed else None,
        passed_deal=MatchPassedDealV1(game_timecode=game.game_timecode) if passed else None,
        bidding=events, bidding_hands=hands)
    return _replace_slot(workspace, operation="mark_passed_deal" if passed else "set_observed_game",
        expected_revision=expected_revision, match_position=position, candidate_slot=updated)
