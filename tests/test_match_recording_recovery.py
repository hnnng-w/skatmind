from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from test_task_first_match_and_learning_workflow import _match, _operation

import skatmind.app_web.match_recovery as recovery
from skatmind.app_web.match_frontend import reload_unified_match_v1
from skatmind.match_capture_game_updates import rebuild_match_capture_game_v1
from skatmind.match_recording_recovery import build_match_recovery_candidate
from skatmind.match_workspace_contracts import (
    _build_match_workspace_slot_v1,
    _build_match_workspace_v1,
)
from skatmind.match_workspace_persistence import load_match_workspace_file_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1
from skatmind.observed_trace_diagnostics import ObservedTraceError


def context_with_plays(tmp_path, cards="SA H7 S7 CA S8 C7"):
    context = _match(tmp_path)
    _operation(context, "start_game")
    _operation(context, "set_declaration", declarer_player_id="player-a", game_type="grand")
    _operation(context, "append_plays", cards=cards)
    return context


def select(context, index=2, action="replace"):
    with context.capture.lock:
        return next(item for item in recovery.recording_selections(context)
                    if item.play_index == index and item.action == action)


@pytest.mark.parametrize("index,card", ((1, "S10"), (2, "S9"), (6, "C8")))
def test_first_middle_last_replacement_retains_all_other_observations(tmp_path, index, card):
    context = context_with_plays(tmp_path)
    _operation(context, "set_commentary", decision_index="2", commentator_name="Observer",
               text="Unchanged free text")
    note = context.workspace.slots[0].observed_game.commentaries[0]
    _operation(context, "set_response_link", commentary_id=note.commentary_id,
               response_decision_index="6")
    before = context.workspace
    before_bytes = context.path.read_bytes()
    item = select(context, index)
    recovery.select_match_recovery(context, item.token)
    recovery.preview_match_recovery(context, item.token, card=card)
    preview = context.recovery.preview
    assert context.workspace is before and context.path.read_bytes() == before_bytes
    game = before.slots[0].observed_game
    candidate = preview.candidate.game
    assert candidate.plays == tuple(replace(play, card=card) if play.decision_index == index
                                    else play for play in game.plays)
    assert candidate.commentaries == game.commentaries
    assert candidate.response_links == game.response_links
    assert candidate.declaration == game.declaration
    assert recovery.apply_match_recovery(context, preview.apply_token) == "saved"
    assert context.workspace.revision == before.revision + 1
    assert load_match_workspace_file_v1(context.path).document.workspace == context.workspace
    with pytest.raises(recovery.MatchRecoveryConflict):
        recovery.apply_match_recovery(context, preview.apply_token)


def test_noop_invalid_suffix_and_changed_winner(tmp_path, monkeypatch):
    context = context_with_plays(tmp_path)
    before = context.workspace
    original = context.path.read_bytes()
    import skatmind.capture_web.context as capture_module
    monkeypatch.setattr(capture_module, "save_match_workspace_file_v1",
                        lambda *a, **k: pytest.fail("Unexpected Save"))
    token = select(context).token
    recovery.preview_match_recovery(context, token, card="H7")
    result = recovery.apply_match_recovery(context, context.recovery.preview.apply_token)
    assert result == "unchanged"
    assert context.workspace is before
    for card, reason, location in (("S7", "duplicate", 3), ("CJ", "wrong_actor", 4)):
        with pytest.raises(ObservedTraceError) as caught:
            recovery.preview_match_recovery(context, select(context).token, card=card)
        assert (caught.value.diagnostic.reason, caught.value.diagnostic.play_index) == (
            reason, location)
        assert context.recovery.preview is None
    assert context.path.read_bytes() == original and context.workspace is before
    # A final completed Trick can change winner without inventing a following actor.
    candidate = build_match_recovery_candidate(before, position=1, play_index=6,
                                               action="replace", card="CJ")
    assert len(candidate.changed_tricks) == 1
    old, new = candidate.changed_tricks[0]
    assert old.winner_player_id != new.winner_player_id
    assert candidate.warning is not None


@pytest.mark.parametrize("index,retained,notes,links", ((1, 0, 1, 1), (3, 2, 0, 1), (6, 5, 0, 1)))
def test_rewind_prefix_and_annotation_removal_preview(tmp_path, index, retained, notes, links):
    context = context_with_plays(tmp_path)
    _operation(context, "set_commentary", decision_index="2", commentator_name="Observer",
               text="Observation")
    note = context.workspace.slots[0].observed_game.commentaries[0]
    _operation(context, "set_response_link", commentary_id=note.commentary_id,
               response_decision_index="6")
    before = context.workspace
    original = context.path.read_bytes()
    recovery.select_match_recovery(context, select(context, index, "rewind").token)
    preview = context.recovery.preview
    candidate = preview.candidate
    assert (candidate.retained_play_count, candidate.removed_commentary_count,
            candidate.removed_response_count) == (retained, notes, links)
    assert candidate.game.plays == before.slots[0].observed_game.plays[:retained]
    assert context.path.read_bytes() == original
    recovery.apply_match_recovery(context, preview.apply_token)
    assert context.workspace.slots[0].observed_game == candidate.game


@pytest.mark.parametrize("cause", ("reload", "expired", "foreign", "content", "position", "game"))
def test_exact_selection_binding_rejects_without_write(tmp_path, monkeypatch, cause):
    context = context_with_plays(tmp_path)
    item = select(context)
    original = context.path.read_bytes()
    if cause == "reload":
        reload_unified_match_v1(context)
    elif cause == "expired":
        monkeypatch.setattr(recovery.time, "monotonic", lambda: item.created_at + 1801)
    elif cause == "foreign":
        item = replace(item, token="f" * 64)
    elif cause == "position":
        context.selected_position = 2
    else:
        workspace = context.workspace
        if cause == "content":
            definition = replace(workspace.match_definition, title="Same revision, other content")
            context.capture.workspace = _build_match_workspace_v1(
                revision=workspace.revision, match_definition=definition, slots=workspace.slots)
        else:
            game = workspace.slots[0].observed_game
            changed = rebuild_match_capture_game_v1(workspace, game, plays=game.plays[:3])
            slot = _build_match_workspace_slot_v1(match_position=1, slot_kind="observed_game",
                observed_game=changed, passed_deal=None,
                match_definition=workspace.match_definition)
            context.capture.workspace = _build_match_workspace_v1(revision=workspace.revision,
                match_definition=workspace.match_definition, slots=(slot, *workspace.slots[1:]))
    with pytest.raises(recovery.MatchRecoveryConflict):
        recovery.preview_match_recovery(context, item.token, card="S9")
    assert context.path.read_bytes() == original


def test_external_same_revision_change_and_save_failure_do_not_publish(tmp_path, monkeypatch):
    context = context_with_plays(tmp_path)
    token = select(context).token
    recovery.preview_match_recovery(context, token, card="S9")
    preview = context.recovery.preview
    before = context.workspace
    original = context.path.read_bytes()
    import skatmind.capture_web.context as capture_module
    real_save = capture_module.save_match_workspace_file_v1

    def failed(*args, **kwargs):
        raise OSError("Private path must never be displayed")

    monkeypatch.setattr(capture_module, "save_match_workspace_file_v1", failed)
    with pytest.raises(recovery.MatchRecoveryConflict) as caught:
        recovery.apply_match_recovery(context, preview.apply_token)
    assert caught.value.reason == "save_failed"
    assert context.workspace is before and context.path.read_bytes() == original
    monkeypatch.setattr(capture_module, "save_match_workspace_file_v1", real_save)
    other = _build_match_workspace_v1(revision=before.revision,
        match_definition=replace(before.match_definition, title="External edit"),
        slots=before.slots)
    result = real_save(context.path, build_match_workspace_persistence_document_v1(other),
                      expected_content_fingerprint=context.capture.content_fingerprint)
    assert result.status == "saved"
    external_bytes = context.path.read_bytes()
    with pytest.raises(recovery.MatchRecoveryConflict):
        recovery.apply_match_recovery(context, preview.apply_token)
    assert context.workspace is before and context.path.read_bytes() == external_bytes


def test_concurrent_apply_saves_once_and_invalidates_only_after_success(tmp_path, monkeypatch):
    context = context_with_plays(tmp_path)
    token = select(context).token
    recovery.preview_match_recovery(context, token, card="S9")
    preview = context.recovery.preview
    import skatmind.capture_web.context as capture_module
    original_save = capture_module.save_match_workspace_file_v1
    calls = []

    def save(*args, **kwargs):
        calls.append(1)
        return original_save(*args, **kwargs)

    monkeypatch.setattr(capture_module, "save_match_workspace_file_v1", save)

    def apply():
        try:
            return recovery.apply_match_recovery(context, preview.apply_token)
        except recovery.MatchRecoveryConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: apply(), range(2))) == ["conflict", "saved"]
    assert calls == [1]
    assert context.last_result is None and context.transfer_notice is None


def test_cas_race_preserves_reports_bytes_and_memory_until_success(tmp_path, monkeypatch):
    from skatmind.app_web.match_frontend import execute_unified_match_analysis_v1
    context = context_with_plays(tmp_path)
    execute_unified_match_analysis_v1(context, {
        "operation": "analyze_decision", "match_position": "1", "decision_index": "1",
        "expected_revision": str(context.workspace.revision),
    })
    reports = context.capture.report_store.list()
    assert reports
    last = context.last_result
    original = context.path.read_bytes()
    recovery.preview_match_recovery(context, select(context).token, card="H7")
    recovery.apply_match_recovery(context, context.recovery.preview.apply_token)
    assert context.capture.report_store.list() == reports
    assert context.last_result is last and context.path.read_bytes() == original
    recovery.preview_match_recovery(context, select(context).token, card="S9")
    preview = context.recovery.preview
    before = context.workspace
    import skatmind.capture_web.context as capture_module
    save = capture_module.save_match_workspace_file_v1
    external = _build_match_workspace_v1(revision=before.revision,
        match_definition=replace(before.match_definition, title="Concurrent writer"),
        slots=before.slots)

    def racing_save(*args, **kwargs):
        save(context.path, build_match_workspace_persistence_document_v1(external),
             expected_content_fingerprint=context.capture.content_fingerprint)
        return save(*args, **kwargs)

    monkeypatch.setattr(capture_module, "save_match_workspace_file_v1", racing_save)
    with pytest.raises(recovery.MatchRecoveryConflict):
        recovery.apply_match_recovery(context, preview.apply_token)
    assert context.workspace is before
    assert context.last_result is last and context.capture.report_store.list() == reports
    assert load_match_workspace_file_v1(context.path).document.workspace == external


def test_existing_warning_record_load_is_read_only_and_analysis_request_is_unchanged(tmp_path):
    from skatmind.match_decision_review_preparation import (
        build_match_decision_review_preparation_v1,
    )
    from skatmind.observed_trace_diagnostics import find_observed_trace_warning
    context = context_with_plays(tmp_path)
    before = context.path.read_bytes()
    loaded = load_match_workspace_file_v1(context.path).document.workspace
    assert loaded == context.workspace
    game = loaded.slots[0].observed_game
    prepared = build_match_decision_review_preparation_v1(loaded, match_position=1)
    assert find_observed_trace_warning(game.plays, "grand").play_index == 2
    assert build_match_decision_review_preparation_v1(loaded, match_position=1) == prepared
    assert context.path.read_bytes() == before
