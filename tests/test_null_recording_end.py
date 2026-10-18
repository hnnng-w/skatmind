"""Rule-ended capture uses accepted evidence, not ten-trick completeness."""

from dataclasses import replace

import pytest
from test_match_capture_game_updates import _entry, _start
from test_match_workspace_contracts import _definition
from test_session_transitions import _apply, _deal_card

from skatmind.app_web.task_first_projections import (
    project_task_first_match_v1,
    project_task_first_session_v1,
)
from skatmind.game_declaration import GameDeclaration
from skatmind.match_capture_application import (
    append_match_capture_plays_v1,
    set_match_capture_declaration_v1,
    set_match_capture_perspective_initial_hand_v1,
)
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.session_commands import (
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameMetadataCommandV1,
)
from skatmind.session_contracts import SessionPlayerV1
from skatmind.session_transitions import apply_session_command_v1, create_session_state_v1

HAND = tuple("CA C10 CJ SA SK SJ HA H9 DK D7".split())
PLAYS = (("bea", "CK"), ("chris", "C7"), ("alex", "CA"),
         ("alex", "SK"), ("bea", "S7"), ("chris", "S10"),
         ("alex", "H9"), ("bea", "H10"), ("chris", "HK"))


def session_prefix(count=8):
    state = create_session_state_v1(session_id="null-recording", capture_mode="live",
        local_player_id="alex", players=tuple(SessionPlayerV1(player_id=pid,
            player_label=pid.title(), seat=seat) for pid, seat in
            zip(("bea", "chris", "alex"), ("forehand", "middlehand", "rearhand"), strict=True)))
    state = _apply(state, SetSessionGameMetadataCommandV1(expected_revision=state.revision,
                                                        game_id="null-game"))
    for card in HAND:
        state = _deal_card(state, destination="player_hand", player_id="alex", card=card)
    state = _apply(state, SetSessionDeclarerCommandV1(expected_revision=state.revision,
                                                    declarer_player_id="chris"))
    state = _apply(state, SetSessionDeclarationCommandV1(expected_revision=state.revision,
        declaration=GameDeclaration(game_type="null", bid_value=18)))
    for player, card in PLAYS[:count]:
        state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                                                        player_id=player, card=card))
    return state


def match_prefix(count=8):
    # Canonical first Match rotation: B forehand, C middlehand, A rearhand.
    workspace = create_match_workspace_v1(_definition(perspective_player_id="player-a"))
    workspace = _start(workspace).workspace_change.workspace
    workspace = set_match_capture_perspective_initial_hand_v1(workspace, match_position=1,
        cards=HAND, expected_revision=workspace.revision).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(workspace, match_position=1,
        declarer_player_id="player-c", declaration=GameDeclaration(game_type="null", bid_value=18),
        expected_revision=workspace.revision).workspace_change.workspace
    if count:
        workspace = append_match_capture_plays_v1(workspace, match_position=1,
            entries=tuple(_entry(card) for _, card in PLAYS[:count]),
            expected_revision=workspace.revision).workspace_change.workspace
    return workspace


def test_session_ninth_card_ends_capture_and_domain_rejects_continuation():
    state = session_prefix()
    assert project_task_first_session_v1(state).workflow.primary_action == "record_play"
    command = RecordSessionPlayCommandV1(expected_revision=state.revision,
                                        player_id="chris", card="HK")
    result = apply_session_command_v1(state, command)
    assert result.status == "applied"
    view = project_task_first_session_v1(result.state)
    assert [t.winner_player_id for t in view.facts.completed_tricks] == ["alex", "alex", "chris"]
    continuation = apply_session_command_v1(result.state,
        replace(command, expected_revision=result.state.revision, card="C8"))
    assert continuation.status == "rejected"
    assert view.workflow.primary_action is None
    assert view.facts.played_card_count == 9


def test_match_ninth_card_ends_capture_and_first_unfinished_moves_without_starting():
    workspace = match_prefix()
    assert project_task_first_match_v1(workspace, selected_position=1).selected.can_record_play
    result = append_match_capture_plays_v1(workspace, match_position=1,
        entries=(_entry("HK"),), expected_revision=workspace.revision)
    workspace = result.workspace_change.workspace
    with pytest.raises(ValueError, match="Null"):
        append_match_capture_plays_v1(workspace, match_position=1,
            entries=(_entry("C8"),), expected_revision=workspace.revision)
    view = project_task_first_match_v1(workspace, selected_position=1)
    assert not view.selected.can_record_play
    assert view.selected.next_player_id is None and view.next_position == 2
    assert view.selected.play_count == 9
    assert view.selected.workspace_progress.complete_play_trace_count == 0
    assert workspace.slots[1].slot_kind == "empty"


def archived_append(state, player, card):
    """Build an old accepted record through the unchanged compatibility validator."""
    from skatmind.session_contracts import SessionCommandRecordV1
    from skatmind.session_history import _build_state_from_projection_v1
    from skatmind.session_incremental_validation import apply_session_command_to_projection_v1
    from skatmind.session_transitions import replay_session_state_v1
    command = RecordSessionPlayCommandV1(expected_revision=state.revision,
                                        player_id=player, card=card)
    result = apply_session_command_to_projection_v1(replay_session_state_v1(state), command)
    assert result.projection is not None
    return _build_state_from_projection_v1(source_state=state, projection=result.projection,
        command_log=(*state.command_log, SessionCommandRecordV1(
            revision=state.revision + 1, command=command)))


def test_pending_rejected_duplicate_stale_and_untrusted_winner_do_not_end():
    import skatmind.api.v1.session as api
    from skatmind.errors import SkatMindInvariantError, SkatMindValidationError
    from skatmind.session_transitions import replay_session_state_v1
    state = session_prefix(8)
    for player, card in (("alex", "HK"), ("chris", "CA"), ("chris", "HA")):
        result = apply_session_command_v1(state, RecordSessionPlayCommandV1(
            expected_revision=state.revision, player_id=player, card=card))
        assert result.status == "rejected" and result.state is state
        assert replay_session_state_v1(state).recording_rule_end is None
    decisive = RecordSessionPlayCommandV1(expected_revision=state.revision,
                                          player_id="chris", card="HK")
    with pytest.raises(SkatMindValidationError):
        api.parse_session_command({**decisive.to_dict(), "winner_player_id": "chris"})
    ended = apply_session_command_v1(state, decisive).state
    assert apply_session_command_v1(ended, decisive).status == "revision_conflict"
    forged = replace(state)
    object.__setattr__(forged, "phase", "ended")
    with pytest.raises(SkatMindInvariantError):
        replay_session_state_v1(forged)


@pytest.mark.parametrize("tail", (False, True))
def test_saved_prefix_and_longer_archive_resume_without_rewrite_or_new_checkpoints(tmp_path, tail):
    import skatmind.api.v1.session as api
    from skatmind.app_web.session_frontend import default_session_position_export_options_v1
    from skatmind.session_checkpoint_collection import collect_session_decision_checkpoint_v1
    from skatmind.session_persistence import (
        load_session_persistence_file_v1,
        save_session_persistence_file_v1,
    )
    from skatmind.session_transitions import replay_session_state_v1
    state = session_prefix(9)
    if tail:
        state = archived_append(state, "chris", "C8")
        state = archived_append(state, "alex", "C10")
    options = default_session_position_export_options_v1()
    document = api.build_session_persistence_document(state).value
    path = tmp_path / "pre-fix.json"
    save_session_persistence_file_v1(path, document, expected_content_fingerprint=None)
    before = path.read_bytes()
    loaded = load_session_persistence_file_v1(path).document
    assert loaded == document and path.read_bytes() == before
    assert replay_session_state_v1(loaded.state).recording_rule_end.trick_number == 3
    assert loaded.state.phase == "play"  # Stored authoring contract remains byte-compatible.
    assert api.export_session_position_request(state, options).value.status == "unavailable"
    assert collect_session_decision_checkpoint_v1(state=state, export_options=options,
        decision_checkpoints=()).status == "unavailable"
    assert api.export_session_historical_request(state).value.status == "unavailable"
    assert path.read_bytes() == before


def test_undo_and_correction_recompute_without_clearing_independent_explicit_end():
    import skatmind.api.v1.session as api
    from skatmind.session_commands import SetSessionGameEndCommandV1
    from skatmind.session_transitions import replay_session_state_v1
    state = session_prefix(9)
    before = api.rewind_session(state, expected_revision=state.revision,
                                target_revision=state.revision - 1).value.state
    assert replay_session_state_v1(before).recording_rule_end is None
    record = state.command_log[-1]
    corrected = api.correct_session_command(state, api.SessionCommandCorrectionV1(
        expected_revision=state.revision, target_revision=record.revision,
        replacement_command=replace(record.command, card="H7"))).value
    assert corrected.status == "applied"
    assert replay_session_state_v1(corrected.state).recording_rule_end is None
    restored = api.correct_session_command(corrected.state, api.SessionCommandCorrectionV1(
        expected_revision=corrected.state.revision, target_revision=record.revision,
        replacement_command=record.command)).value.state
    assert replay_session_state_v1(restored).recording_rule_end.trick_number == 3
    # Preserve supported explicit assertions independently of the derived end.
    ended = _apply(state, SetSessionGameEndCommandV1(expected_revision=state.revision,
        game_end_reason="declarer_concession", game_end={
            "schema_version": 1, "kind": "declarer_concession", "declarer_hand_cards_remaining": 7,
            "defender_consent": {"status": "granted",
                                 "consenting_defender_player_ids": ["bea", "alex"]}}))
    changed = api.correct_session_command(ended, api.SessionCommandCorrectionV1(
        expected_revision=ended.revision, target_revision=record.revision,
        replacement_command=replace(record.command, card="H7"))).value.state
    facts = replay_session_state_v1(changed)
    assert facts.recording_rule_end is None
    assert facts.phase == "ended" and facts.game_end_reason == "declarer_concession"


LATE_TRICKS = (
    "CA CQ CJ", "CK C9 C10", "SA SQ SJ", "SK S9 S10", "HA HQ HJ", "HK H9 H10",
    "DA DQ C7", "DK DJ S7", "D10 D7 H7", "D8 D9 H8",
)


@pytest.mark.parametrize("hand,ouvert", (
    (False, False), (True, False), (False, True), (True, True)))
@pytest.mark.parametrize("winner_index,decisive", ((0, 1), (1, 9), (1, 10), (2, 10)))
@pytest.mark.parametrize("local", ("player-a", "player-b", "player-c"))
def test_valid_variants_all_perspectives_early_late_zero_point_and_tenth(hand, ouvert,
                                                                     winner_index, decisive, local):
    from test_session_transitions import _retrospective_before_play

    from skatmind.session_transitions import replay_session_state_v1
    players = ("player-a", "player-b", "player-c")
    tricks = [cards.split() for cards in LATE_TRICKS]
    if decisive == 9:
        tricks[8][0], tricks[9][0] = tricks[9][0], tricks[8][0]
        tricks[8][1], tricks[9][1] = tricks[9][1], tricks[8][1]
    if winner_index == 2:
        tricks = [[a, c, b] for a, b, c in tricks]
    data = {"game_id": "variant", "players": [
        {"player_id": player, "seat": seat, "initial_hand": [t[i] for t in tricks]}
        for i, (player, seat) in enumerate(zip(players,
            ("forehand", "middlehand", "rearhand"), strict=True))],
        "skat": ["C8", "S8"], "discarded_cards": [] if hand else ["C8", "S8"],
        "declarer_player_id": players[winner_index], "declaration": {
            "game_type": "null", "hand_game": hand, "ouvert": ouvert, "bid_value": 18}}
    state = _retrospective_before_play(data, local_player_id=local)
    workspace = create_match_workspace_v1(_definition(perspective_player_id=local))
    workspace = _start(workspace, position=3).workspace_change.workspace
    workspace = set_match_capture_declaration_v1(workspace, match_position=3,
        declarer_player_id=players[winner_index],
        declaration=GameDeclaration(**data["declaration"]),
        expected_revision=workspace.revision).workspace_change.workspace
    for index, cards in enumerate(tricks[:decisive], 1):
        for player, card in zip(players, cards, strict=True):
            assert replay_session_state_v1(state).recording_rule_end is None
            state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                                                            player_id=player, card=card))
            workspace = append_match_capture_plays_v1(workspace, match_position=3,
                entries=(_entry(card),),
                expected_revision=workspace.revision).workspace_change.workspace
        if index < decisive:
            assert replay_session_state_v1(state).recording_rule_end is None
    facts = replay_session_state_v1(state)
    assert facts.recording_rule_end.trick_number == decisive
    assert facts.recording_rule_end.declarer_player_id == players[winner_index]
    assert not project_task_first_match_v1(workspace, selected_position=3).selected.can_record_play
    if decisive == 10:
        assert facts.completed_tricks[-1].trick_points == 0


def test_match_batch_crossing_end_is_atomic_and_recovery_reopens():
    from skatmind.match_recording_recovery import build_match_recovery_candidate
    workspace = match_prefix(8)
    with pytest.raises(ValueError, match="Null"):
        append_match_capture_plays_v1(workspace, match_position=1,
            entries=(_entry("HK"), _entry("C8")), expected_revision=workspace.revision)
    assert len(workspace.slots[0].observed_game.plays) == 8
    ended = match_prefix(9)
    for action, kwargs in (("replace", {"card": "H7"}), ("rewind", {})):
        candidate = build_match_recovery_candidate(ended, position=1, play_index=9,
                                                  action=action, **kwargs)
        view = project_task_first_match_v1(candidate.change.workspace, selected_position=1)
        assert view.selected.can_record_play and view.next_position == 1
    stale = append_match_capture_plays_v1(ended, match_position=1, entries=(_entry("C8"),),
                                         expected_revision=ended.revision - 1)
    assert stale.status == "revision_conflict"


def test_archival_match_tail_is_inspectable_but_explicitly_skipped(tmp_path):
    from skatmind.match_capture_game_updates import rebuild_match_capture_game_v1
    from skatmind.match_decision_review_preparation import (
        build_match_decision_review_preparation_v1,
    )
    from skatmind.match_workspace_operations import set_match_workspace_observed_game_v1
    from skatmind.match_workspace_persistence import (
        load_match_workspace_file_v1,
        save_match_workspace_file_v1,
    )
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )
    from skatmind.observed_game_trace import ObservedPlayV1
    workspace = match_prefix(9)
    game = workspace.slots[0].observed_game
    extended = rebuild_match_capture_game_v1(workspace, game, plays=(*game.plays,
        ObservedPlayV1(decision_index=10, player_id="player-c", card="C8", decision_timecode=None),
        ObservedPlayV1(decision_index=11, player_id="player-a", card="C10",
                       decision_timecode=None)))
    workspace = set_match_workspace_observed_game_v1(workspace, extended,
        expected_revision=workspace.revision).workspace
    document = build_match_workspace_persistence_document_v1(workspace)
    path = tmp_path / "archive.json"
    save_match_workspace_file_v1(path, document, expected_content_fingerprint=None)
    before = path.read_bytes()
    loaded = load_match_workspace_file_v1(path).document.workspace
    preparation = build_match_decision_review_preparation_v1(loaded, match_position=1)
    assert [(d.decision_index, d.reason) for d in preparation.skipped_decisions if
            d.decision_index > 9] == [(10, "after_rule_end"), (11, "after_rule_end")]
    assert [s.decision_index for s in preparation.snapshots] == [3, 4, 7]
    view = project_task_first_match_v1(loaded, selected_position=1)
    assert view.selected.play_count == 11 and not view.selected.can_record_play
    assert path.read_bytes() == before


def test_old_post_terminal_checkpoint_retained_exactly_but_not_reviewed(tmp_path):
    import skatmind.api.v1.session as api
    from skatmind.app_web.session_frontend import (
        default_session_position_export_options_v1,
        import_guided_session_v1,
    )
    from skatmind.app_web.session_recorded_review import project_recorded_session_decisions_v1
    from skatmind.session_decision_checkpoint import _build_replayed_session_decision_checkpoint_v1
    from skatmind.session_position_export import (
        _export_replayed_session_position_analysis_request_v1,
    )
    from skatmind.session_transitions import replay_session_state_v1
    earlier = session_prefix(6)
    options = default_session_position_export_options_v1()
    before_card = api.build_session_decision_checkpoint(state=earlier,
        position_export=api.export_session_position_request(earlier, options).value).value
    state = archived_append(session_prefix(9), "chris", "C8")
    projection = replay_session_state_v1(state)
    exported = _export_replayed_session_position_analysis_request_v1(state=state,
        projection=projection, options=options, archival_checkpoint=True)
    old_checkpoint = _build_replayed_session_decision_checkpoint_v1(
        state=state, projection=projection, position_export=exported)
    state = archived_append(state, "alex", "C10")
    document = api.build_session_persistence_document(state,
        decision_checkpoints=(before_card, old_checkpoint)).value
    context = import_guided_session_v1(tmp_path, handle="a" * 64, document=document.to_dict())
    assert context.document == document
    assert api.observe_session_decision_checkpoint(state=state,
        checkpoint=old_checkpoint).value.status == "ended_without_play"
    decisions = project_recorded_session_decisions_v1(context)
    assert decisions.local_play_count == 3
    assert [d.checkpoint.decision_index for d in decisions.decisions] == [7]
    assert before_card.request.to_dict() == document.decision_checkpoints[0].request.to_dict()


def test_full_length_null_win_and_explicit_normal_completion_remain_supported():
    from test_session_transitions import _retrospective_before_play

    from skatmind.session_commands import SetSessionGameEndCommandV1
    from skatmind.session_transitions import replay_session_state_v1
    players = ("player-a", "player-b", "player-c")
    tricks = [cards.split() for cards in LATE_TRICKS]
    data = {"game_id": "null-win", "players": [
        {"player_id": p, "seat": seat, "initial_hand": [t[i] for t in tricks]}
        for i, (p, seat) in enumerate(zip(players,
            ("forehand", "middlehand", "rearhand"), strict=True))],
        "skat": ["C8", "S8"], "discarded_cards": [], "declarer_player_id": "player-c",
        "declaration": {"game_type": "null", "hand_game": True, "bid_value": 18}}
    state = _retrospective_before_play(data)
    for cards in tricks:
        for player, card in zip(players, cards, strict=True):
            state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                                                            player_id=player, card=card))
    assert replay_session_state_v1(state).recording_rule_end is None
    state = _apply(state, SetSessionGameEndCommandV1(expected_revision=state.revision,
        game_end_reason="normal_completion", game_end=None))
    assert state.validation.historical_export.status == "available"


@pytest.mark.parametrize("hand", (False, True))
def test_live_ouvert_uses_existing_exact_public_hand_validation(hand):
    import skatmind.api.v1.session as api
    from skatmind.session_commands import SetSessionPublicHandCommandV1
    from skatmind.session_transitions import replay_session_state_v1
    state = session_prefix(0)
    record = state.command_log[-1]
    state = api.correct_session_command(state, api.SessionCommandCorrectionV1(
        expected_revision=state.revision, target_revision=record.revision,
        replacement_command=replace(record.command, declaration=GameDeclaration(
            game_type="null", bid_value=18, hand_game=hand, ouvert=True)))).value.state
    public = SetSessionPublicHandCommandV1(expected_revision=state.revision,
        player_id="chris", source="declared_ouvert",
        cards=tuple("C7 S10 HK C8 SQ S8 H8 DQ D9 DJ".split()))
    rejected = apply_session_command_v1(state, replace(public, cards=public.cards[:-1]))
    assert rejected.status == "rejected"
    assert replay_session_state_v1(state).recording_rule_end is None
    state = _apply(state, public)
    for player, card in PLAYS:
        state = _apply(state, RecordSessionPlayCommandV1(expected_revision=state.revision,
                                                        player_id=player, card=card))
    assert replay_session_state_v1(state).recording_rule_end.trick_number == 3
