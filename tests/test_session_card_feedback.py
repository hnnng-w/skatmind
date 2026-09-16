"""Canonical negative Commands; no hidden-hand completion or alternative validator."""

from dataclasses import FrozenInstanceError, replace

import pytest
from test_compact_session_cards import candidate, initial, local_declarer
from test_session_transitions import _apply, _players

import skatmind.api.v1.session as api
import skatmind.app_web.session_card_entry as entry
from skatmind.app_web.session_card_feedback import (
    SessionCardFeedback,
    SessionCardWitness,
    rejected_card_witness,
    render_card_witness,
)
from skatmind.app_web.stateful_localization import text
from skatmind.app_web.validation_contracts import FrontendValidationIssueV1
from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration
from skatmind.session_transitions import replay_session_state_v1


def live(hand, *, local="player-a", game="grand", hand_game=True, declarer=None, ouvert=False):
    state = api.create_session(session_id="synthetic-feedback", players=_players(),
                              capture_mode="live", local_player_id=local).value
    state = candidate(state, hand).state
    state = _apply(state, api.SetSessionDeclarerCommandV1(expected_revision=state.revision,
                    declarer_player_id=declarer or local))
    return _apply(state, api.SetSessionDeclarationCommandV1(expected_revision=state.revision,
        declaration=GameDeclaration(game_type=game, hand_game=hand_game, ouvert=ouvert)))


def rejection(state, card, kind, *, command=None):
    facts = replay_session_state_v1(state)
    command = command or api.RecordSessionPlayCommandV1(expected_revision=state.revision,
        player_id=facts.next_player_id, card=card)
    result = api.apply_session_command(state, command).value
    assert result.status == "rejected" and result.state == state
    diagnostic = result.diagnostics[0]
    original = diagnostic.to_dict()
    witness = rejected_card_witness(facts, command, result.diagnostics)
    assert witness.kind == kind and witness.card == card
    assert rejected_card_witness(facts, command, (replace(diagnostic,
        message="Deliberately unrelated English prose with no ownership hints."),)) == witness
    assert diagnostic.to_dict() == original
    return witness


def test_owner_and_played_are_distinct_and_only_use_accepted_prefix():
    state = live(["C7", "SQ", "CA", "C10", "CK", "CQ", "C9", "C8", "SA", "S10"])
    state = candidate(state, ["C7"]).state
    state = candidate(state, ["H7"]).state
    own = rejection(state, "SQ", "owner_hand")
    used = rejection(state, "C7", "played")
    assert (own.player, own.owner) == (3, 1)
    assert (used.player, used.owner, used.play) == (3, 1, 1)
    assert not {"SQ", "C7"}.intersection(entry.project_session_card_task(state).selectable_cards)


def test_exact_missing_membership_is_not_follow_suit():
    state = live(["C8", "C9", "C10", "CK", "CQ", "CA", "SQ", "SA", "S10", "SK"],
                 local="player-b")
    state = candidate(state, ["C7"]).state
    assert rejection(state, "SQ", "follow").suit == "C"
    assert rejection(state, "H7", "missing_hand").owner is None


@pytest.mark.parametrize("game,lead,held,attempt,suit", (
    ("grand", "CJ", "HJ", "SQ", "TRUMP"),
    ("clubs", "C7", "SJ", "SQ", "TRUMP"),
    ("hearts", "SJ", "H7", "SQ", "TRUMP"),
    ("null", "CJ", "C7", "SQ", "C"),
    ("null", "SJ", "SQ", "H7", "S"),
))
def test_follow_uses_existing_effective_suit_and_jack_rules(game, lead, held, attempt, suit):
    hand = [held, attempt] + [c for c in get_full_deck() if c not in {held, attempt, lead}][:8]
    state = candidate(live(hand, local="player-b", game=game), [lead]).state
    witness = rejection(state, attempt, "follow")
    assert witness.suit == suit and witness.play == 1
    with pytest.raises(entry.CardEntryError) as error:
        candidate(state, [attempt])
    assert error.value.reason == "ownership" and error.value.witness == witness


def test_unknown_hand_and_void_hand_never_prove_follow_or_missing_membership():
    state = candidate(local_declarer(hand=True), ["CA"]).state
    facts = replay_session_state_v1(state)
    result = api.apply_session_command(state, api.RecordSessionPlayCommandV1(
        expected_revision=state.revision, player_id="player-b", card="D7")).value
    assert result.status == "applied" and facts.remaining_hand_for("player-b") is None
    diagnostic = api.apply_session_command(state, api.RecordSessionPlayCommandV1(
        expected_revision=state.revision, player_id="player-b", card="C10")).value.diagnostics[0]
    command = api.RecordSessionPlayCommandV1(expected_revision=state.revision,
                                            player_id="player-b", card="D7")
    assert rejected_card_witness(facts, command, (diagnostic,)) is None
    hand = ["CJ", "SQ", "SA", "S10", "SK", "S9", "S8", "S7", "H7", "D7"]
    void = candidate(live(hand, local="player-b"), ["C7"]).state
    assert candidate(void, ["SQ"]).state.revision == void.revision + 1


def test_exact_public_hand_owner_membership_and_follow():
    state = live(get_full_deck()[:10], game="null", declarer="player-b", ouvert=True)
    state = _apply(state, api.SetSessionPublicHandCommandV1(expected_revision=state.revision,
        player_id="player-b", cards=tuple(get_full_deck()[10:20]), source="declared_ouvert"))
    assert rejection(state, "SQ", "owner_public").owner == 2
    state = candidate(state, ["SA"]).state
    assert rejection(state, "D7", "missing_public").player == 2
    assert rejection(state, "HA", "follow").suit == "S"


def test_initial_assignments_discards_and_changed_skat_ownership():
    state = candidate(initial(), ["SQ"]).state
    command = api.RecordSessionDealtCardCommandV1(expected_revision=state.revision,
        destination="player_hand", player_id="player-a", card="SQ")
    assert rejection(state, "SQ", "assigned_hand", command=command).owner == 1
    state = candidate(local_declarer(), ["H7"]).state
    command = api.RecordSessionDealtCardCommandV1(expected_revision=state.revision,
        destination="skat", player_id=None, card="H7")
    assert rejection(state, "H7", "assigned_skat", command=command).player is None
    state = candidate(state, ["D7"]).state
    command = api.RecordSessionDiscardCommandV1(expected_revision=state.revision, card="D8")
    assert rejection(state, "D8", "discard_membership", command=command).player == 1
    state = candidate(state, ["CA"]).state
    command = api.RecordSessionDiscardCommandV1(expected_revision=state.revision, card="CA")
    rejection(state, "CA", "discarded", command=command)
    state = candidate(state, ["C10"]).state
    rejection(state, "CA", "discarded")
    # Original Skat membership is no longer an unplayable-location assertion after pickup.
    assert "H7" in entry.project_session_card_task(state).selectable_cards
    state = candidate(state, ["H7"]).state
    assert rejection(state, "D7", "owner_hand").owner == 1


def test_known_untouched_hand_skat():
    state = initial("retrospective")
    for start in (0, 10, 20, 30):
        state = candidate(state, get_full_deck()[start:start + 10]).state
    state = _apply(state, api.SetSessionDeclarerCommandV1(expected_revision=state.revision,
                    declarer_player_id="player-a"))
    state = _apply(state, api.SetSessionDeclarationCommandV1(expected_revision=state.revision,
                    declaration=GameDeclaration(game_type="grand", hand_game=True)))
    witness = rejection(state, get_full_deck()[-1], "hand_skat")
    assert render_card_witness(witness, state.players, "en")[1] == "session-skat"


def test_partial_candidate_keeps_original_witness_and_unsaved_progress_distinct(monkeypatch):
    state = candidate(initial(), ["SQ"]).state
    original = state.to_dict()
    with pytest.raises(entry.CardEntryError) as error:
        candidate(state, ["CA", "SQ"])
    assert error.value.witness.kind == "assigned_hand"
    assert state.to_dict() == original
    short = api.create_session(session_id="short", players=_players(),
        capture_mode="live", local_player_id="player-a").value
    # Structured helper-only fixture for candidate-dependent rejection; no saved state claimed.
    facts = replay_session_state_v1(short)
    diagnostic = api.apply_session_command(state, api.RecordSessionDealtCardCommandV1(
        expected_revision=state.revision, destination="player_hand", player_id="player-a",
        card="SQ")).value.diagnostics
    command = api.RecordSessionDealtCardCommandV1(expected_revision=1,
        destination="player_hand", player_id="player-a", card="CA")
    assert rejected_card_witness(facts, command, diagnostic) is None
    witness = rejected_card_witness(facts, command, diagnostic, candidate_progress=True)
    assert witness.kind == "batch" and render_card_witness(witness, short.players, "en")[1] is None
    def fail(*args, **kwargs):
        raise RuntimeError("Injected optional explanation failure")
    monkeypatch.setattr(entry, "rejected_card_witness", fail)
    with pytest.raises(entry.CardEntryError) as error:
        candidate(state, ["CA", "SQ"])
    assert error.value.reason == "unavailable" and error.value.witness is None
    assert state.to_dict() == original


def test_unsupported_codes_paths_and_commands_do_not_classify_card_like_values():
    state = local_declarer(hand=True)
    command = api.RecordSessionPlayCommandV1(expected_revision=state.revision,
        player_id="player-a", card="D7")
    diag = api.apply_session_command(state, command).value.diagnostics[0]
    facts = replay_session_state_v1(state)
    for changed in (replace(diag, code="invalid_value"), replace(diag, path="/command/player_id"),
                    replace(diag, blocks_command=False)):
        assert rejected_card_witness(facts, command, (changed,), candidate_progress=True) is None
    metadata = api.SetSessionGameMetadataCommandV1(expected_revision=state.revision, game_id="D7")
    assert rejected_card_witness(facts, metadata, (diag,)) is None


def test_private_payload_is_exact_bounded_and_does_not_truncate_labels():
    witness = SessionCardWitness(kind="owner_hand", card="SQ", player=3, owner=1)
    label = "Synthetic <full & accepted> " + "Name" * 40
    players = tuple(replace(p, player_label=label if i == 0 else None)
                    for i, p in enumerate(_players()))
    for locale in ("en", "de"):
        message, anchor = render_card_witness(witness, players, locale)
        assert label in message and anchor == "session-hand-1"
        assert text(locale, "task.player", number=3) in message
    feedback = SessionCardFeedback(selection="a" * 64, route="/sessions/play", witness=witness)
    FrontendValidationIssueV1(field_key="cards", message_key="validation.card_entry.ownership",
                             session_card_feedback=feedback)
    with pytest.raises(FrozenInstanceError):
        witness.card = "CA"
    for changes in ({"player": 4}, {"owner": True}, {"card": "path"}, {"kind": "unknown"},
                    {"play": 31}, {"suit": "clubs"}):
        with pytest.raises(ValueError):
            replace(witness, **changes)
    with pytest.raises(ValueError):
        FrontendValidationIssueV1(field_key="cards", message_key="validation.card_entry.ownership",
                                 interpolation_arguments=(("player", label),))
