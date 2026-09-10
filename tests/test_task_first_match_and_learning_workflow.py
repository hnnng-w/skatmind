import pytest
import test_unified_local_app_web as web_helpers
from test_local_match_capture_web import _creation_values
from test_unified_local_app_web import _bootstrap, _post_form, _request

from skatmind.app_web.cross_area_transfer import transfer_active_match_workspace_to_corpus_v1
from skatmind.app_web.learning_frontend import (
    build_unified_learning_state_v1,
    create_unified_learning_corpus_v1,
    prepare_unified_learning_artifacts_v1,
)
from skatmind.app_web.match_frontend import (
    apply_unified_match_operation_v1,
    create_unified_match_v1,
    execute_unified_match_analysis_v1,
)
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.task_first_match_rendering import render_task_first_match_v1
from skatmind.app_web.task_first_match_state import build_task_first_match_page_state_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as t
from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS

running_app_server = web_helpers.running_app_server


def _match(tmp_path):
    return create_unified_match_v1(tmp_path, handle="a" * 64, values=_creation_values())


def _operation(context, operation, **values):
    return apply_unified_match_operation_v1(context, {
        "operation": operation, "match_position": "1",
        "expected_revision": str(context.workspace.revision), **values,
    })


@pytest.mark.parametrize("locale", ("en", "de"))
def test_match_progression_reuses_exact_evidence_and_never_materializes_on_render(
    tmp_path, monkeypatch, locale,
):
    context = _match(tmp_path)
    assert _operation(context, "start_game").status == "applied"
    assert _operation(context, "set_declaration", declarer_player_id="player-a",
        game_type="grand", hand_game="true").status == "applied"
    assert _operation(
        context, "set_discarded_cards", card_evidence_mode="known_empty").status == "applied"
    assert _operation(context, "append_plays", cards="CA").status == "applied"
    assert _operation(context, "set_commentary", decision_index="1",
        commentator_name="Commentator", text="User observation").status == "applied"
    import skatmind.capture_web.state as capture_state
    monkeypatch.setattr(capture_state, "materialize_match_observed_game_historical_v1",
                        lambda *args, **kwargs: pytest.fail("Render materialized a Game"))
    before = context.workspace
    view = project_task_first_match_v1(before, selected_position=1)
    state = build_task_first_match_page_state_v1(context, view)
    assert state["game"]["original_skat"] is None
    assert state["game"]["discarded_cards"] == []
    html = render_task_first_match_v1(state, view, managed_handle=context.handle, locale=locale)
    assert context.workspace is before
    assert "User observation" in html
    assert t(locale, "task.match.scope.bounded_observation_candidates") in html
    assert 'value="set_response_link"' in html
    assert 'value="truncate_plays"' in html
    assert html.count('class="position-card') == 36
    assert tuple(position.round_number for position in view.positions) == tuple(
        number for number in range(1, 13) for _ in range(3))


@pytest.mark.parametrize("locale", ("en", "de"))
def test_explicit_transfer_selection_build_and_ten_downloads(tmp_path, locale):
    match_root = tmp_path / "matches"
    learning_root = tmp_path / "learning"
    match_root.mkdir()
    learning_root.mkdir()
    source = _match(match_root)
    target = create_unified_learning_corpus_v1(
        learning_root, handle="b" * 64, corpus_id="collection")
    original = source.workspace
    result = transfer_active_match_workspace_to_corpus_v1(source, target,
        selection_mode="keep_current", same_revision_resolution="reject",
        expected_catalog_revision=0)
    assert result.status == "applied"
    assert source.workspace is original and target.corpus.prepared_artifacts is None
    state = build_unified_learning_state_v1(target)
    first_selection = state["current_match_snapshots"][0]
    assert _operation(source, "mark_passed_deal").status == "applied"
    transfer_active_match_workspace_to_corpus_v1(source, target,
        selection_mode="keep_current", same_revision_resolution="reject",
        expected_catalog_revision=target.corpus.store.document.catalog.revision)
    state = build_unified_learning_state_v1(target)
    assert state["current_match_snapshots"][0] == first_selection
    assert len(state["matches"][0]["snapshots"]) == 2
    html = render_task_first_learning_v1(state, managed_handle=target.handle, locale=locale)
    assert t(locale, "task.learning.used_version") in html
    assert t(locale, "task.learning.alternatives") in html
    assert target.corpus.prepared_artifacts is None
    transfer_active_match_workspace_to_corpus_v1(source, target,
        selection_mode="select_imported", same_revision_resolution="reject",
        expected_catalog_revision=target.corpus.store.document.catalog.revision)
    assert target.corpus.prepared_artifacts is None
    result = prepare_unified_learning_artifacts_v1(
        target, dataset_id="dataset", known_player_seed=0,
        unseen_player_seed=0, train_weight=70, validation_weight=15, test_weight=15)
    assert result.status == "prepared"
    state = build_unified_learning_state_v1(target)
    html = render_task_first_learning_v1(state, managed_handle=target.handle, locale=locale)
    assert t(locale, "task.learning.current_results") in html
    for kind in LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS:
        assert f'/learning/downloads/{kind.replace("_", "-")}.json' in html


def test_native_record_and_pass_submit_once_and_get_performs_no_product_mutation(
    running_app_server,
):
    server = running_app_server
    cookie, headers = _bootstrap(server)
    root = server.app_context.managed_stateful.root("matches")
    context = _match(root)
    server.app_context.managed_stateful.activate_match(context)
    original_profile = server.app_context.frontend_profile
    for position, operation in ((1, "start_game"), (2, "mark_passed_deal")):
        before = context.workspace
        status, _headers, _body = _request(server, "GET", f"/matches/position/{position}",
                                          headers={"Cookie": cookie})
        assert status == 200 and context.workspace is before
        status, _headers, _body = _post_form(server, "/matches/api/v1/operation", headers, {
            "managed_handle": context.handle, "expected_revision": str(before.revision),
            "match_position": str(position), "operation": operation,
        })
        assert status == 303 and context.workspace.revision == before.revision + 1
    assert context.workspace.slots[0].slot_kind == "observed_game"
    assert context.workspace.slots[1].slot_kind == "passed_deal"
    assert server.app_context.frontend_profile is original_profile


@pytest.mark.parametrize("locale", ("en", "de"))
def test_unavailable_decision_report_has_plain_guidance_without_a_card(tmp_path, locale):
    context = _match(tmp_path)
    _operation(context, "start_game")
    _operation(context, "set_declaration", declarer_player_id="player-a",
               game_type="grand", hand_game="true")
    _operation(context, "append_plays", cards="CA")
    result = execute_unified_match_analysis_v1(context, {
        "operation": "analyze_decision", "match_position": "1", "decision_index": "1",
        "expected_revision": str(context.workspace.revision),
    })
    view = project_task_first_match_v1(context.workspace, selected_position=1)
    state = build_task_first_match_page_state_v1(
        context, view, report_id=result.state["selected_report_id"])
    assert state["selected_report"]["details"]["status"] == "unavailable"
    html = render_task_first_match_v1(state, view, managed_handle=context.handle, locale=locale)
    assert t(locale, "result.no_recommendation") in html
    assert t(locale, "task.match.decision_blocked") in html
