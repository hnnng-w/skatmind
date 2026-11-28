import pytest
from test_match_workspace_contracts import _definition, _observed_game, _seat_order, _set_game

from skatmind.bidding import BID_VALUES, BidAction, BiddingContinuationConflict, replay_bidding
from skatmind.deck import get_full_deck
from skatmind.errors import SkatMindValidationError
from skatmind.game_declaration import GameDeclaration
from skatmind.match_bidding import edit_match_bidding
from skatmind.match_capture_game_updates import rebuild_match_capture_game_v1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
    resume_match_workspace_document_v1,
)
from skatmind.observed_game_trace import ObservedPlayV1


@pytest.mark.parametrize(("sequence", "winner", "spoken", "effective"), [
    ([("M", "bid", 23), ("F", "hold", 23), ("M", "pass"), ("R", "pass")], "F", 23, 23),
    ([("M", "bid", 18), ("F", "pass"), ("R", "bid", 59), ("M", "hold", 59),
      ("R", "pass")], "M", 59, 59),
    ([("M", "pass"), ("R", "bid", 264), ("F", "pass")], "R", 264, 264),
    ([("M", "pass"), ("R", "pass"), ("F", "take")], "F", None, 18),
    ([("M", "pass"), ("R", "pass"), ("F", "pass")], None, None, None),
])
def test_recorded_auction(sequence, winner, spoken, effective):
    events = tuple(BidAction(*item) for item in sequence)
    result = replay_bidding(("F", "M", "R"), events)
    assert result.actor is None
    assert (result.declarer, result.value, result.effective_value) == (winner, spoken, effective)
    with pytest.raises(ValueError):
        replay_bidding(("F", "M", "R"), (*events, BidAction("F", "pass")))


@pytest.mark.parametrize("sequence", [
    [("F", "pass")], [("M", "bid", True)], [("M", "bid", 19)], [("M", "take")],
    [("M", "hold", 18)], [("M", "bid", 18), ("F", "hold", 20)],
    [("M", "bid", 20), ("F", "hold", 20), ("M", "bid", 18)],
])
def test_illegal_observations(sequence):
    with pytest.raises(ValueError):
        replay_bidding(("F", "M", "R"), tuple(BidAction(*item) for item in sequence))


def test_auction_schema_exact_value_set_and_version_boundary():
    from skatmind.api.v1.session import parse_session_command
    from skatmind.errors import SkatMindSchemaError

    document = dict(kind="record_bid", expected_revision=0, command_version=2, player_id="player-b",
                    action="bid", value=18)
    for bid in BID_VALUES:
        candidate = document | {"value": bid}
        assert parse_session_command(candidate).to_dict() == candidate
    for override in ({"value": 19}, {"command_version": 1}, {"action": "pass"},
                     {"extra": None}, {"action": "hold", "value": None}):
        with pytest.raises(SkatMindSchemaError):
            parse_session_command(document | override)


def test_match_evidence_cutoff_strict_resume_and_conflicting_continuation():
    middlehand = _seat_order(_definition(), 1)[1]
    definition = _definition(perspective_player_id=middlehand)
    workspace = create_match_workspace_v1(definition)
    game = _observed_game(definition)
    workspace = _set_game(workspace, game)
    f, m, r = (p.player_id for p in game.players)
    assert m == game.perspective_player_id
    # Enter the first observation before capturing any private evidence.
    workspace = edit_match_bidding(workspace, 1, 0, BidAction(m, "bid", 23),
                                   expected_revision=workspace.revision).workspace
    cards = tuple(get_full_deck())
    game = rebuild_match_capture_game_v1(workspace, game, perspective_initial_hand=cards[:10],
                                         original_skat=cards[-2:])
    workspace = _set_game(workspace, game)
    for i, event in enumerate((BidAction(f, "hold", 23), BidAction(m, "pass"),
                               BidAction(r, "pass")), 1):
        workspace = edit_match_bidding(workspace, 1, i, event,
                                       expected_revision=workspace.revision).workspace
    game = rebuild_match_capture_game_v1(
        workspace, game, declarer_player_id=f, declaration=GameDeclaration(
            game_type="grand", bid_value=23), discarded_cards=cards[-2:],
        plays=(ObservedPlayV1(decision_index=1, player_id=f, card=cards[10],
                              decision_timecode=None),))
    workspace = _set_game(workspace, game)
    original = build_match_workspace_persistence_document_v1(workspace)
    source = original.to_dict()
    slot = source["workspace"]["slots"][0]
    assert slot["match_workspace_slot_version"] == 2
    for i, row in enumerate(slot["bidding"]):
        known = i > 0 and row["player_id"] == game.perspective_player_id
        expected = list(cards[:10]) if known else None
        assert row["actor_initial_hand"] == expected
    assert resume_match_workspace_document_v1(source).document == original
    del slot["bidding"][0]["value"]
    with pytest.raises(SkatMindValidationError):
        resume_match_workspace_document_v1(source)
    with pytest.raises(BiddingContinuationConflict) as conflict:
        edit_match_bidding(workspace, 1, 0, BidAction(m, "bid", 35),
                           expected_revision=workspace.revision)
    # The hold, both later passes, declaration, discard observation and play.
    assert conflict.value.count == 6
    corrected = edit_match_bidding(workspace, 1, 0, BidAction(m, "bid", 35),
        expected_revision=workspace.revision, confirm_suffix=True).workspace
    slot = corrected.slots[0]
    assert slot.bidding == (BidAction(m, "bid", 35),) and slot.bidding_hands == (None,)
    assert slot.observed_game.declaration is None and slot.observed_game.game_id == game.game_id
    assert slot.observed_game.original_skat == game.original_skat
    assert slot.observed_game.perspective_initial_hand == game.perspective_initial_hand
    assert slot.observed_game.discarded_cards is None and not slot.observed_game.plays
    assert build_match_workspace_persistence_document_v1(workspace) == original
