from dataclasses import replace

import pytest
from test_compact_session_cards import candidate
from test_session_transitions import _apply, _deal_card, _players

import skatmind.api.v1.session as api
import skatmind.app_web.session_card_entry as entry
from skatmind.app_web.session_frontend import (
    _collect_current_checkpoint,
    default_session_position_export_options_v1,
)
from skatmind.app_web.task_first_projections import project_task_first_session_v1
from skatmind.deck import get_full_deck
from skatmind.session_transitions import replay_session_state_v1


def fresh(mode="live", local="player-a"):
    """Real revision-zero creation, deliberately without metadata preparation."""
    return api.create_session(session_id="direct-start", players=_players(),
        capture_mode=mode, local_player_id=local).value


@pytest.mark.parametrize("mode,local,actor", (
    ("live", "player-a", "player-a"), ("live", "player-b", "player-b"),
    ("live", "player-c", "player-c"), ("retrospective", None, "player-a"),
    ("retrospective", "player-c", "player-a"),
))
@pytest.mark.parametrize("size", (1, 10))
def test_fresh_task_and_exact_public_sequential_reference(mode, local, actor, size, monkeypatch):
    source = fresh(mode, local)
    before = source.to_dict()
    view = project_task_first_session_v1(source)
    task = entry.project_session_card_task(source)
    assert view.workflow.primary_action == "record_dealt_card"
    assert "set_game_metadata" in view.workflow.secondary_actions
    assert task.player_id == actor and task.destination == "player_hand" and task.capacity == 10
    assert view.facts.phase == "setup" and view.facts.game_id is None
    visits = []
    real = entry._collect_current_checkpoint
    def collect(**kwargs):
        visits.append(kwargs["state"].revision)
        return real(**kwargs)
    monkeypatch.setattr(entry, "_collect_current_checkpoint", collect)
    cards = get_full_deck()[:size]
    actual = candidate(source, list(reversed(cards)))
    expected, checkpoints = source, ()
    commands = [api.SetSessionGameMetadataCommandV1(expected_revision=0,
        game_id=source.session_id, played_at=None)]
    commands += [api.RecordSessionDealtCardCommandV1(expected_revision=index + 1,
        destination="player_hand", player_id=actor, card=card) for index, card in enumerate(cards)]
    for command in commands:
        checkpoints = _collect_current_checkpoint(state=expected, checkpoints=checkpoints,
            export_options=default_session_position_export_options_v1())
        result = api.apply_session_command(expected, command).value
        assert result.status == "applied"
        expected = result.state
        checkpoints = _collect_current_checkpoint(state=expected, checkpoints=checkpoints,
            export_options=default_session_position_export_options_v1())
    assert actual.state == expected and actual.checkpoints == checkpoints
    assert visits == [r for index in range(size + 1) for r in (index, index + 1)]
    assert [record.command for record in actual.state.command_log] == commands
    assert actual.state.revision == size + 1 and source.to_dict() == before
    assert source.revision == 0 and source.command_log == ()


@pytest.mark.parametrize("metadata", (
    {"game_id": "custom-exact-ID"},
    {"played_at": "2026-01-15t19:30:00.123456789-00:00"},
    {"game_id": "custom-exact-ID", "played_at": "2016-12-31t23:59:60z"},
))
def test_metadata_prefix_is_exact_and_only_missing_identity_is_appended(metadata):
    source = _apply(fresh(), api.SetSessionGameMetadataCommandV1(expected_revision=0, **metadata))
    actual = candidate(source, ["SJ", "CA"])
    missing = "game_id" not in metadata
    assert actual.state.revision == source.revision + 2 + missing
    assert actual.state.command_log[:1] == source.command_log
    appended = actual.state.command_log[1:]
    assert [r.command.kind for r in appended] == (
        (["set_game_metadata"] if missing else []) + ["record_dealt_card"] * 2)
    if missing:
        assert appended[0].command == api.SetSessionGameMetadataCommandV1(
            expected_revision=1, game_id=source.session_id, played_at=None)
    facts = replay_session_state_v1(actual.state)
    assert facts.game_id == metadata.get("game_id", source.session_id)
    assert facts.played_at == metadata.get("played_at")


@pytest.mark.parametrize("size", (1, 9))
def test_old_partial_hand_appends_missing_id_and_only_remaining_cards(size):
    source = fresh()
    for card in get_full_deck()[:size]:
        source = _deal_card(source, destination="player_hand", player_id="player-a", card=card)
    document = api.build_session_persistence_document(source).value
    source = api.resume_session_document(document.to_dict()).value.document.state
    task = entry.project_session_card_task(source)
    assert task.capacity == 10 - size
    actual = candidate(source, get_full_deck()[size:10])
    assert actual.state.command_log[:size] == source.command_log
    assert actual.state.command_log[size].command.kind == "set_game_metadata"
    assert actual.state.revision == 11 and actual.state.phase == "declaration"


def test_old_retrospective_initial_skat_uses_same_bounded_rule():
    source = fresh("retrospective", None)
    for index, player in enumerate(source.players):
        for card in get_full_deck()[index * 10:(index + 1) * 10]:
            source = _deal_card(source, destination="player_hand", player_id=player.player_id,
                                card=card)
    source = _deal_card(source, destination="skat", card=get_full_deck()[30])
    task = entry.project_session_card_task(source)
    assert task.destination == "skat" and task.player_id is None and task.capacity == 1
    actual = candidate(source, [get_full_deck()[31]])
    assert actual.state.revision == 33 and actual.state.phase == "declaration"
    assert actual.state.command_log[:31] == source.command_log
    assert actual.state.command_log[31].command.game_id == source.session_id


@pytest.mark.parametrize("cards,reason", (([], "empty"), (["CA", "CA"], "duplicate"),
    (["CA", "bad"], "invalid"), (get_full_deck()[:11], "capacity")))
def test_bad_basic_selection_never_applies_metadata(cards, reason, monkeypatch):
    source = fresh()
    def forbidden(*args, **kwargs):
        raise AssertionError("Basic selection must precede Commands")
    monkeypatch.setattr(entry.session_api, "apply_session_command", forbidden)
    with pytest.raises(entry.CardEntryError) as error:
        candidate(source, cards)
    assert error.value.reason == reason and source.revision == 0


def test_forged_actor_and_destination_never_initialize():
    source = fresh()
    task = entry.project_session_card_task(source)
    for forged in (replace(task, player_id="player-b"), replace(task, destination="skat")):
        with pytest.raises(entry.CardEntryError):
            entry.prepare_session_card_candidate(source, (), ["CA"], task=forged)
    assert replay_session_state_v1(source).game_id is None


def test_real_later_card_rejection_discards_metadata_and_earlier_card(monkeypatch):
    source = _deal_card(fresh(), destination="player_hand", player_id="player-a", card="SJ")
    before = source.to_dict()
    real = api.apply_session_command
    applied = []
    def observed(state, command):
        result = real(state, command)
        applied.append((command.kind, result.value.status))
        return result
    monkeypatch.setattr(entry.session_api, "apply_session_command", observed)
    with pytest.raises(entry.CardEntryError) as error:
        candidate(source, ["SJ", "CA"])
    assert error.value.reason == "unavailable"
    assert applied == [("set_game_metadata", "applied"), ("record_dealt_card", "applied"),
                       ("record_dealt_card", "rejected")]
    assert source.to_dict() == before and replay_session_state_v1(source).game_id is None


@pytest.mark.parametrize("revision", (1, 2, 3))
def test_checkpoint_fault_after_identity_or_cards_discards_candidate(monkeypatch, revision):
    source = fresh()
    real = entry._collect_current_checkpoint
    def fail(**kwargs):
        if kwargs["state"].revision == revision:
            raise ValueError("Injected checkpoint failure")
        return real(**kwargs)
    monkeypatch.setattr(entry, "_collect_current_checkpoint", fail)
    with pytest.raises(ValueError, match="Injected"):
        candidate(source, ["CA", "C10"])
    assert source.revision == 0 and source.command_log == ()


@pytest.mark.parametrize("target", (0, 1))
def test_strict_prefix_undo_restarts_from_actual_identity(target):
    first = candidate(fresh(), get_full_deck()[:10])
    source = api.rewind_session(
        first.state, expected_revision=11, target_revision=target).value.state
    actual = candidate(source, get_full_deck()[:10], first.checkpoints)
    assert actual == first
    assert len([r for r in actual.state.command_log if r.command.kind == "set_game_metadata"]) == 1


def test_public_direct_cards_and_later_missing_identity_priority_are_unchanged():
    source = fresh()
    for card in get_full_deck()[:10]:
        source = _deal_card(source, destination="player_hand", player_id="player-a", card=card)
    assert source.revision == 10 and source.phase == "declaration"
    assert replay_session_state_v1(source).game_id is None
    assert project_task_first_session_v1(source).workflow.primary_action == "set_game_metadata"
    assert entry.project_session_card_task(source) is None


def test_metadata_rejection_aborts_before_any_card(monkeypatch):
    source = fresh()
    real = api.apply_session_command
    calls = []
    def conflict(state, command):
        calls.append(command.kind)
        return real(state, replace(command, expected_revision=state.revision + 1))
    monkeypatch.setattr(entry.session_api, "apply_session_command", conflict)
    with pytest.raises(entry.CardEntryError):
        candidate(source, ["CA"])
    assert calls == ["set_game_metadata"] and source.command_log == ()


@pytest.mark.parametrize("target", (0, 1))
def test_saved_future_checkpoint_variants_survive_restart_and_deduplicate(target):
    from skatmind.game_declaration import GameDeclaration
    state = candidate(fresh(), get_full_deck()[:10]).state
    state = _apply(state, api.SetSessionDeclarerCommandV1(expected_revision=11,
        declarer_player_id="player-a"))
    state = _apply(state, api.SetSessionDeclarationCommandV1(expected_revision=12,
        declaration=GameDeclaration(game_type="grand", hand_game=True)))
    options = default_session_position_export_options_v1()
    checkpoints = _collect_current_checkpoint(state=state, checkpoints=(), export_options=options)
    checkpoints = _collect_current_checkpoint(state=state, checkpoints=checkpoints,
        export_options=replace(options, sample_count=2))
    assert len(checkpoints) == 2
    rewound = api.rewind_session(state, expected_revision=13, target_revision=target).value.state
    saved = api.build_session_persistence_document(rewound, decision_checkpoints=checkpoints).value
    resumed = api.resume_session_document(saved.to_dict()).value.document
    restarted = candidate(resumed.state, get_full_deck()[:10], resumed.decision_checkpoints)
    assert restarted.checkpoints == resumed.decision_checkpoints
    assert restarted.state.command_log == state.command_log[:11]
    expected = restarted.state
    for record in state.command_log[11:]:
        expected = api.apply_session_command(expected, record.command).value.state
    assert expected == state
    final = candidate(expected, ["CA"], resumed.decision_checkpoints)
    assert final.checkpoints == resumed.decision_checkpoints
