from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event

import pytest
from test_historical_game import build_historical_input
from test_session_decision_checkpoint import _checkpoint
from test_session_decision_observation import _diverged_state, _ended_without_play, _observed
from test_session_position_export import _options, _search_settings
from test_session_transitions import _apply, _play_commands_from_data, _retrospective_before_play

import skatmind.api.v1.session as session_api
import skatmind.api.v1.session.files as session_files
import skatmind.app_web.session_recorded_review as review
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.session_frontend import (
    GuidedSessionContextV1,
    apply_guided_session_command_v1,
    correct_guided_session_command_v1,
    execute_guided_session_historical_v1,
    execute_guided_session_position_v1,
    reload_guided_session_v1,
    rewind_guided_session_v1,
)
from skatmind.app_web.session_recorded_review import (
    RecordedDecisionReviewConflictError,
    execute_recorded_session_decision_v1,
    project_recorded_session_decisions_v1,
)
from skatmind.app_web.session_recorded_review_form import parse_recorded_review_selection_v1
from skatmind.app_web.task_first_session_rendering import render_task_first_session_v1
from skatmind.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameMetadataCommandV1,
)
from skatmind.session_history import build_session_state_from_accepted_prefix_v1


def context_for(tmp_path, state=None, checkpoints=None):
    if state is None:
        _, state, checkpoint = _observed()
        checkpoints = (checkpoint,)
    app = AppWebContextV1.create(prepare_managed_home_v1(tmp_path / "managed"))
    root = app.managed_stateful.root("sessions")
    document = session_api.build_session_persistence_document(
        state, decision_checkpoints=checkpoints or (),
    ).value
    context = GuidedSessionContextV1(category_root=root, path=root / "game.json",
                                     handle="a" * 64, document=document)
    session_files.save_session_file(context.path, document, expected_content_fingerprint=None)
    app.managed_stateful.activate_session(context)
    return app, context


def selection(context):
    return project_recorded_session_decisions_v1(context).decisions[0].selection


@pytest.mark.parametrize(
    "status", ("observed", "pending", "future", "diverged", "ended_without_play"),
)
def test_projection_observation_statuses_are_distinct_and_read_only(tmp_path, status):
    state, _, checkpoint = _checkpoint()
    if status == "observed":
        _, state, checkpoint = _observed()
    elif status == "future":
        state = build_session_state_from_accepted_prefix_v1(
            state, target_revision=state.revision - 1,
        )
    elif status == "diverged":
        state = _diverged_state(state)
    elif status == "ended_without_play":
        state, checkpoint = _ended_without_play()
    _, context = context_for(tmp_path, state, (checkpoint,))
    before = context.path.read_bytes()
    view = project_recorded_session_decisions_v1(context)
    if status == "observed":
        assert len(view.decisions) == view.local_play_count == 1
        assert view.decisions[0].observation.lineage.relationship == "ancestor"
        assert view.missing_snapshot_count == 0
    else:
        assert not view.decisions
        assert dict(view.unavailable_counts)[status] == 1
    for locale in ("en", "de"):
        html = render_task_first_session_v1(context, locale=locale)
        assert 'id="recorded-decisions"' in html
    assert context.path.read_bytes() == before
    assert context.execution is None


def test_missing_and_partial_coverage_do_not_reconstruct_snapshots(tmp_path):
    _, state, checkpoint = _observed()
    app, context = context_for(tmp_path, state, ())
    view = project_recorded_session_decisions_v1(context)
    assert (view.local_play_count, view.missing_snapshot_count, view.decisions) == (1, 1, ())
    assert not context.decision_checkpoints
    context.document = session_api.build_session_persistence_document(
        state, decision_checkpoints=(checkpoint,),
    ).value
    assert project_recorded_session_decisions_v1(context).missing_snapshot_count == 0
    assert app.managed_stateful.active_session is context


def test_variant_grouping_uses_latest_source_then_stored_tuple_order(tmp_path):
    state, _, first = _checkpoint()
    state = _apply(state, SetSessionGameMetadataCommandV1(
        expected_revision=state.revision, game_id="synthetic-game"))
    variants = tuple(session_api.build_session_decision_checkpoint(
        state=state, position_export=session_api.export_session_position_request(
            state, replace(_options(), sample_count=samples, random_seed=samples),
        ).value,
    ).value for samples in (7, 11))
    state = _apply(state, RecordSessionPlayCommandV1(
        expected_revision=state.revision, player_id=first.acting_player_id, card="CA"))
    _, context = context_for(tmp_path, state, (variants[1], first, variants[0]))
    stored = context.decision_checkpoints
    expected = next(cp for cp in stored if cp.source_revision == variants[0].source_revision)
    row, = project_recorded_session_decisions_v1(context).decisions
    assert row.checkpoint is expected
    assert row.observation.observed_play_revision == state.revision
    assert len(stored) == 3 and context.decision_checkpoints is stored


def test_real_export_execution_preserves_frozen_request_and_exact_bytes(tmp_path):
    app, context = context_for(tmp_path)
    before = context.path.read_bytes()
    row, = project_recorded_session_decisions_v1(context).decisions
    frozen = row.checkpoint.request.to_dict()["document"]
    execute_recorded_session_decision_v1(app, context, selection=row.selection)
    execution = context.execution
    assert execution.options == ExecutionOptionsV1()
    expected = {**frozen, "analysis_mode": "post_game_review", "actual_card_played": "CA"}
    assert execution.request.to_dict()["document"] == expected
    assert execution.request_json_bytes == review.canonical_frontend_json_bytes_v1(expected)
    assert context.recorded_review_source.decision is not None
    assert context.recorded_review_source.decision == row
    assert context.path.read_bytes() == before
    assert row.checkpoint.request.to_dict()["document"] == frozen


@pytest.mark.parametrize(
    "extra", ("actual_card_played", "request", "hand", "sample_count", "options"),
)
def test_form_rejects_client_evidence_and_configuration(extra):
    with pytest.raises(ValueError):
        parse_recorded_review_selection_v1({"decision_selection": "a" * 64, extra: "forged"})


@pytest.mark.parametrize("value", ("", "1", "a" * 65, "Z" * 64, "ä" * 64))
def test_form_selection_is_bounded(value):
    with pytest.raises(ValueError):
        parse_recorded_review_selection_v1({"decision_selection": value})


def test_unknown_foreign_reopened_and_equal_revision_corrected_selections_execute_nothing(
    tmp_path, monkeypatch,
):
    app, context = context_for(tmp_path)
    old_selection = selection(context)
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid selections must not execute")
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", forbidden)
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, context, selection="f" * 64)
    reopened = replace(context, review_selection_key=b"x" * 32)
    app.managed_stateful.activate_session(reopened)
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, reopened, selection=old_selection)
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, context, selection=old_selection)
    app.managed_stateful.activate_session(context)
    revision = context.state.revision
    correction = session_api.SessionCommandCorrectionV1(
        expected_revision=revision, target_revision=revision,
        replacement_command=RecordSessionPlayCommandV1(
            expected_revision=revision - 1, player_id="player-a", card="C10"),
    )
    assert correct_guided_session_command_v1(context, correction).status == "applied"
    assert context.state.revision == revision
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, context, selection=old_selection)
    row, = project_recorded_session_decisions_v1(context).decisions
    assert row.observation.actual_card == "C10"


def test_undo_rerecord_and_reload_expire_selection_without_changing_stored_variants(tmp_path):
    app, context = context_for(tmp_path)
    old = selection(context)
    stored = context.decision_checkpoints
    revision = context.state.revision
    assert rewind_guided_session_v1(context, target_revision=revision - 1).status == "applied"
    assert dict(project_recorded_session_decisions_v1(context).unavailable_counts)["pending"] == 2
    assert apply_guided_session_command_v1(context, RecordSessionPlayCommandV1(
        expected_revision=revision - 1, player_id="player-a", card="CA")).status == "applied"
    assert all(checkpoint in context.decision_checkpoints for checkpoint in stored)
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, context, selection=old)
    current = selection(context)
    reload_guided_session_v1(context)
    assert context.recorded_review_source is context.execution is None
    assert selection(context) != current


def test_failed_attempt_retains_exact_previous_result_and_source(tmp_path, monkeypatch):
    app, context = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, context, selection=selection(context))
    execution, source = context.execution, context.recorded_review_source
    def fail(*args, **kwargs):
        raise ValueError("Synthetic execution failure")
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", fail)
    with pytest.raises(ValueError):
        execute_recorded_session_decision_v1(app, context, selection=selection(context))
    assert context.execution is execution and context.recorded_review_source is source
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, context, selection="f" * 64)
    assert context.execution is execution and context.recorded_review_source is source


@pytest.mark.parametrize(
    "change", ("command", "correction", "undo", "reload", "reopen", "external"),
)
def test_source_changes_during_unlocked_execution_cannot_publish(tmp_path, monkeypatch, change):
    app, context = context_for(tmp_path)
    original = context.document
    def execute(request, *, options):
        assert not app.lock._is_owned() and not context.lock._is_owned()
        if change == "command":
            assert apply_guided_session_command_v1(context, SetSessionGameMetadataCommandV1(
                expected_revision=context.state.revision, game_id="new-game-name",
            )).status == "applied"
        elif change == "correction":
            revision = context.state.revision
            correction = session_api.SessionCommandCorrectionV1(
                expected_revision=revision, target_revision=revision,
                replacement_command=RecordSessionPlayCommandV1(
                    expected_revision=revision - 1, player_id="player-a", card="C10"),
            )
            assert correct_guided_session_command_v1(context, correction).status == "applied"
        elif change == "undo":
            rewind_guided_session_v1(context, target_revision=context.state.revision - 1)
        elif change == "reload":
            reload_guided_session_v1(context)
        elif change == "reopen":
            app.managed_stateful.activate_session(replace(context, review_selection_key=b"x" * 32))
        else:
            context.path.write_bytes(b"{}\n")
        return object()  # No fake Result is accepted; publication must be rejected.
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", execute)
    with pytest.raises(RecordedDecisionReviewConflictError):
        execute_recorded_session_decision_v1(app, context, selection=selection(context))
    assert context.execution is context.recorded_review_source is None
    if change == "external":
        assert context.document is original and context.path.read_bytes() == b"{}\n"


def test_two_attempts_completing_out_of_order_keep_newest_atomic_result(tmp_path, monkeypatch):
    app, context = context_for(tmp_path)
    entered, release = Event(), Event()
    real = review.execute_guided_frontend_review_v1
    calls = 0
    def execute(request, *, options):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            assert release.wait(20)
            return object()
        return real(request, options=options)
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", execute)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(execute_recorded_session_decision_v1, app, context,
                            selection=selection(context))
        assert entered.wait(20)
        execute_recorded_session_decision_v1(app, context, selection=selection(context))
        latest, source = context.execution, context.recorded_review_source
        release.set()
        with pytest.raises(RecordedDecisionReviewConflictError) as caught:
            first.result(timeout=20)
    assert caught.value.reason == "superseded" and calls == 2
    assert context.execution is latest and context.recorded_review_source is source


def test_current_position_publication_clears_recorded_source_label(tmp_path):
    app, context = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, context, selection=selection(context))
    # Rewind clears retained metadata; review is unavailable until its Play is recorded again.
    rewind_guided_session_v1(context, target_revision=context.state.revision - 1)
    assert context.recorded_review_source is None
    result = execute_guided_session_position_v1(
        context, export_options=_options(), execution_options=ExecutionOptionsV1(),
    )
    assert result.status == "executed" and context.recorded_review_source is None


@pytest.mark.parametrize("method", (None, "bounded_search", "auto"))
def test_frozen_settings_exclude_retrospective_private_evidence_and_later_plays(
    tmp_path, monkeypatch, method,
):
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    state = _retrospective_before_play(data, local_player_id="player-a")
    options = _options(recommendation_method=method,
                       bounded_search_settings=None if method is None else _search_settings())
    checkpoint = session_api.build_session_decision_checkpoint(
        state=state,
        position_export=session_api.export_session_position_request(state, options).value,
    ).value
    state = _play_commands_from_data(state, data)
    app, context = context_for(tmp_path, state, (checkpoint,))
    captured = []
    def inspect_request(request, *, options):
        captured.append(request)
        assert options == ExecutionOptionsV1()
        # Intentional executor stop: the real exporter remains under test, and
        # no unvalidated synthetic Result is published.
        raise ValueError("Inspected frozen Request")
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", inspect_request)
    with pytest.raises(ValueError, match="Inspected"):
        execute_recorded_session_decision_v1(app, context, selection=selection(context))
    assert len(captured) == 1
    assert captured[0].to_dict()["document"] == {
        **checkpoint.request.to_dict()["document"],
        "analysis_mode": "post_game_review",
        "actual_card_played": data["tricks"][0]["plays"][0]["card"],
    }
    assert context.execution is context.recorded_review_source is None


def test_partial_coverage_and_historical_publication_clear_the_recorded_label(tmp_path):
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    state = _retrospective_before_play(data, local_player_id="player-a")
    checkpoint = session_api.build_session_decision_checkpoint(
        state=state,
        position_export=session_api.export_session_position_request(state, _options()).value,
    ).value
    state = _play_commands_from_data(state, data)
    state = _apply(state, SetSessionGameEndCommandV1(
        expected_revision=state.revision, game_end_reason="normal_completion", game_end=None))
    app, context = context_for(tmp_path, state, (checkpoint,))
    view = project_recorded_session_decisions_v1(context)
    assert (view.local_play_count, view.missing_snapshot_count, len(view.decisions)) == (10, 9, 1)
    before = context.path.read_bytes()
    execute_recorded_session_decision_v1(app, context, selection=selection(context))
    assert context.recorded_review_source is not None
    operation = execute_guided_session_historical_v1(
        context, execution_options=ExecutionOptionsV1(),
    )
    assert operation.status == "executed"
    assert context.execution.request.workflow.value == "historical_game"
    assert context.recorded_review_source is None
    assert context.path.read_bytes() == before


def test_valid_external_same_revision_edit_is_rejected_before_execution(tmp_path, monkeypatch):
    app, context = context_for(tmp_path)
    old_selection = selection(context)
    original = context.document
    revision = context.state.revision
    correction = session_api.SessionCommandCorrectionV1(
        expected_revision=revision, target_revision=revision,
        replacement_command=RecordSessionPlayCommandV1(
            expected_revision=revision - 1, player_id="player-a", card="C10"),
    )
    changed = session_api.correct_session_command(context.state, correction).value.state
    document = session_api.build_session_persistence_document(
        changed, decision_checkpoints=context.decision_checkpoints,
    ).value
    assert document.state.revision == revision
    session_files.save_session_file(context.path, document,
                                    expected_content_fingerprint=original.content_fingerprint)
    external_bytes = context.path.read_bytes()
    def forbidden(*args, **kwargs):
        raise AssertionError("External changes must be caught before execution")
    monkeypatch.setattr(review, "execute_guided_frontend_review_v1", forbidden)
    real_load = review.session_files.load_session_file
    def load(*args, **kwargs):
        assert not app.lock._is_owned()
        return real_load(*args, **kwargs)
    monkeypatch.setattr(review.session_files, "load_session_file", load)
    with pytest.raises(RecordedDecisionReviewConflictError) as caught:
        execute_recorded_session_decision_v1(app, context, selection=old_selection)
    assert caught.value.reason == "source_changed"
    assert context.document is original
    assert context.path.read_bytes() == external_bytes


def test_promotion_does_not_gate_or_rebuild_recorded_review(tmp_path):
    _, state, checkpoint = _observed()
    state = _apply(state, PromoteSessionToRetrospectiveCommandV1(expected_revision=state.revision))
    app, context = context_for(tmp_path, state, (checkpoint,))
    execute_recorded_session_decision_v1(app, context, selection=selection(context))
    assert context.execution.request.document["hand"] == checkpoint.request.document["hand"]
    assert context.recorded_review_source.decision.checkpoint == checkpoint
