from dataclasses import replace

import pytest
from test_observed_game_contracts import build_observed_record

from skatmind.game_declaration import GameDeclaration
from skatmind.observed_game_trace import ObservedPlayV1
from skatmind.observed_trace_diagnostics import ObservedTraceError, find_observed_trace_warning


def plays(cards, actors=None):
    actors = actors or ("player-a", "player-b", "player-c") * 10
    return tuple(ObservedPlayV1(decision_index=index, player_id=actor,
                               card=card, decision_timecode=None)
                 for index, (card, actor) in enumerate(zip(cards, actors, strict=False), 1))


@pytest.mark.parametrize("game_type,lead,off,witness,expected", (
    ("grand", "SA", "H7", "S8", "S"),
    ("hearts", "HJ", "S7", "H8", "TRUMP"),
    ("grand", "HJ", "H7", "SJ", "TRUMP"),
    ("null", "HJ", "S7", "H8", "H"),
    ("null", "H7", "S7", "HJ", "H"),
    ("grand", "H7", "S7", "HJ", None),
    ("grand", "HJ", "S7", "H8", None),
    ("null", "HJ", "S7", "SJ", None),
))
def test_warning_uses_effective_suit_and_only_observed_same_actor_evidence(
    game_type, lead, off, witness, expected,
):
    trace = plays((lead, off, "D7", "CA", witness))
    assert find_observed_trace_warning(trace[:2], game_type) is None
    warning = find_observed_trace_warning(trace, game_type)
    if expected is None:
        assert warning is None
    else:
        assert (warning.play_index, warning.witness_index, warning.required_suit) == (
            2, 5, expected)
        assert warning.witness_card == witness
        assert not warning.complete_replay
    foreign_witness = trace[:-1] + (replace(trace[-1], player_id="player-a"),)
    assert find_observed_trace_warning(foreign_witness, game_type) is None


def test_partial_warning_does_not_change_acceptance_and_returns_earliest_conflict():
    trace = plays(("SA", "H7", "S7", "CA", "S8", "C7", "C10", "S9"))
    record = build_observed_record(declarer_player_id="player-c",
        declaration=GameDeclaration(game_type="grand"), plays=trace)
    warning = find_observed_trace_warning(record.plays, "grand")
    assert (warning.play_index, warning.witness_index) == (2, 5)
    assert record.plays == trace


@pytest.mark.parametrize("cards,kwargs,reason,index,witness", (
    (("SA", "SA"), {}, "duplicate", 2, 1),
    (("SA",), {"discarded_cards": ("SA", "D7")}, "discard", 1, None),
    (("SA",), {"original_skat": ("SA", "D7")}, "skat", 1, None),
))
def test_authoritative_errors_are_value_errors_with_finite_data(
    cards, kwargs, reason, index, witness,
):
    with pytest.raises(ObservedTraceError) as caught:
        build_observed_record(declarer_player_id="player-c",
            declaration=GameDeclaration(game_type="grand"), plays=plays(cards), **kwargs)
    assert isinstance(caught.value, ValueError)
    diagnostic = caught.value.diagnostic
    assert (diagnostic.reason, diagnostic.play_index, diagnostic.witness_index) == (
        reason, index, witness)


def test_wrong_actor_keeps_actual_location_and_expected_actor():
    with pytest.raises(ObservedTraceError) as caught:
        build_observed_record(declarer_player_id="player-c",
            declaration=GameDeclaration(game_type="grand"),
            plays=plays(("SA", "S7"), ("player-a", "player-c")))
    diagnostic = caught.value.diagnostic
    assert (diagnostic.reason, diagnostic.play_index, diagnostic.expected_player_id) == (
        "wrong_actor", 2, "player-b")


@pytest.mark.parametrize("card,reason", (("D7", "ownership"), ("H7", "follow_suit")))
def test_exact_hand_error_retains_one_witness_not_complete_hand(card, reason):
    from test_observed_game_contracts import build_observed_match
    hand = ("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "H7")
    with pytest.raises(ObservedTraceError) as caught:
        build_observed_record(
            match_definition=build_observed_match(perspective_player_id="player-b"),
            declarer_player_id="player-c", declaration=GameDeclaration(game_type="grand"),
            perspective_initial_hand=hand, plays=plays(("S7", card)))
    diagnostic = caught.value.diagnostic
    assert diagnostic.reason == reason and diagnostic.play_index == 2
    assert not hasattr(diagnostic, "hand")
    if reason == "follow_suit":
        assert diagnostic.required_suit == "S"
        assert diagnostic.witness_card == "SA" and diagnostic.witness_index is None


def test_known_ownership_and_hand_skat_conflicts_keep_technical_messages():
    hand = ("CA", "C10", "CK", "CQ", "CJ", "C9", "C8", "C7", "SA", "H7")
    with pytest.raises(ObservedTraceError, match="perspective initial hand") as caught:
        build_observed_record(declarer_player_id="player-c",
            declaration=GameDeclaration(game_type="grand"), perspective_initial_hand=hand,
            plays=plays(("CA", "SA")))
    assert caught.value.diagnostic.expected_player_id == "player-a"
    with pytest.raises(ObservedTraceError, match="Hand-game original Skat") as caught:
        build_observed_record(declarer_player_id="player-c",
            declaration=GameDeclaration(game_type="grand", hand_game=True),
            original_skat=("SA", "D7"), plays=plays(("SA",)))
    assert caught.value.diagnostic.reason == "skat"
