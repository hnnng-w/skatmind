from dataclasses import replace

import pytest
from test_session_transitions import _apply, _metadata, _players

import skatmind.api.v1.session as api
import skatmind.app_web.session_card_entry as entry
from skatmind.app_web.session_frontend import (
    _collect_current_checkpoint,
    default_session_position_export_options_v1,
)
from skatmind.deck import get_full_deck
from skatmind.game_declaration import GameDeclaration
from skatmind.rules import get_legal_cards
from skatmind.session_transitions import replay_session_state_v1


def initial(mode="live"):
    state = api.create_session(session_id="compact-test", players=_players(),
        capture_mode=mode, local_player_id="player-a").value
    return _metadata(state, game_id="compact-test-game")


def candidate(state, cards, checkpoints=()):
    return entry.prepare_session_card_candidate(
        state, checkpoints, cards, task=entry.project_session_card_task(state))


def local_declarer(game_type="grand", hand=False):
    state = candidate(initial(), get_full_deck()[:10]).state
    state = _apply(state, api.SetSessionDeclarerCommandV1(
        expected_revision=state.revision, declarer_player_id="player-a"))
    return _apply(state, api.SetSessionDeclarationCommandV1(
        expected_revision=state.revision,
        declaration=GameDeclaration(game_type=game_type, hand_game=hand)))


@pytest.mark.parametrize("size", (1, 4, 10))
@pytest.mark.parametrize("reverse", (False, True))
def test_canonical_candidate_equals_reference_commands_and_checkpoints(size, reverse):
    state = initial()
    cards = get_full_deck()[:size]
    actual = candidate(state, list(reversed(cards)) if reverse else cards)
    expected, checkpoints = state, ()
    for card in cards:
        checkpoints = _collect_current_checkpoint(state=expected, checkpoints=checkpoints,
            export_options=default_session_position_export_options_v1())
        expected = api.apply_session_command(expected, api.RecordSessionDealtCardCommandV1(
            expected_revision=expected.revision, destination="player_hand",
            player_id="player-a", card=card)).value.state
        checkpoints = _collect_current_checkpoint(state=expected, checkpoints=checkpoints,
            export_options=default_session_position_export_options_v1())
    assert actual.state == expected and actual.checkpoints == checkpoints
    assert actual.state.revision == state.revision + size
    assert state.revision == 1


@pytest.mark.parametrize("cards,reason", (([], "empty"), (["CA"] * 2, "duplicate"),
    (["bad", "CA"], "invalid"), (["CA", "bad"], "invalid"),
    (get_full_deck()[:11], "capacity")))
def test_malformed_set_has_no_candidate(cards, reason):
    with pytest.raises(entry.CardEntryError) as error:
        candidate(initial(), cards)
    assert error.value.reason == reason


def test_partial_append_preserves_accepted_prefix_and_rejects_assigned_member():
    state = candidate(initial(), ["SJ", "CA"]).state
    task = entry.project_session_card_task(state)
    assert task.capacity == 8 and set(task.accepted_cards) == {"SJ", "CA"}
    assert not set(task.accepted_cards).intersection(task.selectable_cards)
    final = candidate(state, ["D7", "C10"]).state
    assert final.command_log[:state.revision] == state.command_log
    with pytest.raises(entry.CardEntryError, match="rejected"):
        candidate(state, ["C10", "SJ"])
    assert state.revision == 3


@pytest.mark.parametrize("game_type", ("clubs", "grand", "null"))
def test_skat_discard_and_intermediate_checkpoint_parity(game_type):
    state = local_declarer(game_type)
    skat = candidate(state, ["D7", "H7"])
    state = skat.state
    task = entry.project_session_card_task(state)
    assert task.kind == "record_discard" and task.capacity == 2
    actual = candidate(state, ["D7", "CA"], skat.checkpoints)
    expected, checkpoints = state, skat.checkpoints
    for card in ("CA", "D7"):
        checkpoints = _collect_current_checkpoint(state=expected, checkpoints=checkpoints,
            export_options=default_session_position_export_options_v1())
        expected = api.apply_session_command(expected, api.RecordSessionDiscardCommandV1(
            expected_revision=expected.revision, card=card)).value.state
        checkpoints = _collect_current_checkpoint(state=expected, checkpoints=checkpoints,
            export_options=default_session_position_export_options_v1())
    assert actual.state == expected and actual.checkpoints == checkpoints
    assert actual.state.phase == "play" and len(actual.checkpoints) == 1
    assert len(replay_session_state_v1(actual.state).remaining_hand_for("player-a")) == 10
    # A real ownership failure after the first canonical Command rejects the whole candidate.
    with pytest.raises(entry.CardEntryError) as error:
        candidate(state, ["CA", "D8"])
    assert error.value.reason == "ownership"
    assert not state.command_log[-1].command.kind == "record_discard"


def test_injected_later_checkpoint_failure_does_not_mutate_source(monkeypatch):
    state = initial()
    real = entry._collect_current_checkpoint
    calls = []
    def fail(**kwargs):
        calls.append(kwargs["state"].revision)
        if len(calls) == 4:
            raise RuntimeError("Injected Checkpoint failure")
        return real(**kwargs)
    monkeypatch.setattr(entry, "_collect_current_checkpoint", fail)
    with pytest.raises(RuntimeError):
        candidate(state, ["CA", "C10"])
    assert calls == [1, 2, 2, 3] and state.revision == 1


@pytest.mark.parametrize("game_type", ("clubs", "grand", "null"))
def test_live_observation_does_not_complete_unknown_hands_or_offer_played_cards(game_type):
    state = local_declarer(game_type, hand=True)
    own = entry.project_session_card_task(state)
    assert own.scope == "exact_legal_cards"
    state = candidate(state, ["CA"]).state
    task = entry.project_session_card_task(state)
    facts = replay_session_state_v1(state)
    assert task.player_id == "player-b" and task.scope == "bounded_observation_candidates"
    assert set(task.selectable_cards) == set(get_full_deck()[10:])
    assert facts.remaining_hand_for("player-b") is None
    state = candidate(state, ["H7"]).state
    assert "H7" not in entry.project_session_card_task(state).selectable_cards


def test_task_cannot_be_forged_or_reused_for_another_destination():
    state = initial()
    task = entry.project_session_card_task(state)
    for forged in (replace(task, player_id="player-b"), replace(task, destination="skat")):
        with pytest.raises(entry.CardEntryError):
            entry.prepare_session_card_candidate(state, (), ["CA"], task=forged)
    assert entry.project_session_card_task(local_declarer(hand=True)).kind == "record_play"


def test_retrospective_hands_and_skat_remain_separate_batches():
    state = initial("retrospective")
    for start in (0, 10, 20, 30):
        state = candidate(state, get_full_deck()[start:start + 10]).state
    assert state.phase == "declaration" and state.revision == 33


def test_exact_public_hand_uses_current_trick_legality():
    state = candidate(initial(), get_full_deck()[:10]).state
    state = _apply(state, api.SetSessionDeclarerCommandV1(
        expected_revision=state.revision, declarer_player_id="player-b"))
    state = _apply(state, api.SetSessionDeclarationCommandV1(expected_revision=state.revision,
        declaration=GameDeclaration(game_type="null", hand_game=True, ouvert=True)))
    state = _apply(state, api.SetSessionPublicHandCommandV1(expected_revision=state.revision,
        player_id="player-b", cards=tuple(get_full_deck()[10:20]), source="declared_ouvert"))
    state = candidate(state, ["SA"]).state
    task = entry.project_session_card_task(state)
    assert task.scope == "exact_legal_cards"
    assert set(task.selectable_cards) == set(
        get_legal_cards(get_full_deck()[10:20], ["SA"], "null"))


def test_snapshot_variants_are_preserved_and_equality_deduplicated():
    state = local_declarer(hand=True)
    options = default_session_position_export_options_v1()
    checkpoints = _collect_current_checkpoint(state=state, checkpoints=(), export_options=options)
    checkpoints = _collect_current_checkpoint(state=state, checkpoints=checkpoints,
        export_options=replace(options, sample_count=2))
    assert len(checkpoints) == 2
    actual = candidate(state, ["CA"], checkpoints)
    reference = api.apply_session_command(state, api.RecordSessionPlayCommandV1(
        expected_revision=state.revision, player_id="player-a", card="CA")).value.state
    expected = _collect_current_checkpoint(state=reference, checkpoints=checkpoints,
        export_options=options)
    assert actual.state == reference and actual.checkpoints == expected == checkpoints


@pytest.mark.parametrize("group", ("skat", "discard"))
def test_partial_skat_and_discards_append_only_remaining_capacity(group):
    state = local_declarer()
    if group == "discard":
        state = candidate(state, ["H7", "D7"]).state
    first = "H7" if group == "skat" else "CA"
    state = candidate(state, [first]).state
    task = entry.project_session_card_task(state)
    assert task.capacity == 1 and task.accepted_cards == (first,)
    with pytest.raises(entry.CardEntryError) as error:
        candidate(state, ["D7", "C10"])
    assert error.value.reason == "capacity"
    state = candidate(state, ["D7"]).state
    assert state.phase == ("skat_and_discard" if group == "skat" else "play")
