"""Retained real synthetic rollouts; preparation never evaluates the recording again."""

from dataclasses import fields, replace

import pytest
from test_learning_corpus_human_evidence import _store
from test_match_rollout_review import alex_workspace, rollout_options
from test_match_workspace_contracts import _observed_game, _set_game

from skatmind.api.v1.contracts import ResultDocumentV1
from skatmind.app_web.debrief_frontend import DebriefScopeV1, DebriefSourceStoreV1
from skatmind.app_web.debrief_rendering import render_debrief
from skatmind.app_web.stateful_localization import text
from skatmind.learning_corpus_match_snapshot import build_learning_corpus_match_snapshot_v1
from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
)
from skatmind.learning_corpus_tactical_motif_builder import (
    build_learning_corpus_tactical_motif_evidence_collection_v1,
)
from skatmind.match_analysis_contracts import build_match_analysis_report_v1
from skatmind.match_analysis_exports import (
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
)
from skatmind.match_debrief import MatchDebriefEvidenceV1, build_debrief_projection
from skatmind.match_decision_analysis import execute_match_decision_analysis_v1
from skatmind.match_workspace_contracts import _build_match_workspace_v1
from skatmind.match_workspace_persistence_codec import build_match_workspace_persistence_document_v1
from skatmind.whole_game_rollout_contracts import (
    WholeGameRolloutCandidateV1,
    WholeGameRolloutResultV1,
    WholeGameRolloutWorkV1,
)
from skatmind.whole_game_rollout_workflow import compare_rollout_actual, serialize_rollout_result


def snapshot(workspace):
    return build_learning_corpus_match_snapshot_v1(
        build_match_workspace_persistence_document_v1(workspace))


def evidence(workspace, *, position=2, decision=3, options=None):
    report = build_match_analysis_report_v1(execute_match_decision_analysis_v1(workspace,
        match_position=position, decision_index=decision, options=options or rollout_options()))
    source = snapshot(workspace)
    return MatchDebriefEvidenceV1(report, source, source)


@pytest.fixture(scope="module")
def retained():
    return evidence(alex_workspace(), options=rollout_options("complete_settlement"))


def test_exact_alex_before_card_and_manual_assumption_preserved(retained, monkeypatch):
    import skatmind.match_decision_analysis as analysis

    def forbidden(*args, **kwargs):
        pytest.fail("Debrief must not execute analysis")
    monkeypatch.setattr(analysis, "execute_application_invocation", forbidden)
    before = tuple(builder(retained.report).to_bytes() for builder in (
        build_match_rollout_request_export_v1, build_match_report_result_export_v1))
    duplicate = replace(retained)
    root = duplicate.report.value.request.document
    original = root["whole_game_rollout_derivation"]["original_request"]["document"]
    assert original["game_declaration"]["bid_value"] == 18
    assert original["game_declaration"]["matadors"] is None
    assert original["current_trick"] == ("CQ", "CA")
    assert original["declarer_points"] == original["defender_points"] == 0
    assert root["whole_game_rollout_derivation"]["supplements"] == {"matadors": 1}
    assert duplicate.reference.acting_player_id == "alex"
    view = build_debrief_projection((retained.snapshot,), (duplicate,))
    assert view.recorded_decisions == 30 and len(view.decisions) == view.report_count == 1
    assert before == tuple(builder(retained.report).to_bytes() for builder in (
        build_match_rollout_request_export_v1, build_match_report_result_export_v1))
    with pytest.raises(ValueError, match="does not support"):
        build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=retained.snapshot.match_snapshot_id, report=retained.report)


def test_metadata_compatible_snapshot_but_not_different_decision(retained):
    workspace = retained.snapshot.workspace
    changed = _build_match_workspace_v1(match_definition=replace(workspace.match_definition,
        title="Another descriptive title"), revision=workspace.revision, slots=workspace.slots)
    compatible = snapshot(changed)
    rebound = replace(retained, snapshot=compatible)
    assert rebound.snapshot != rebound.source_snapshot
    assert rebound.report is retained.report
    with pytest.raises(ValueError):
        replace(retained, source_snapshot=compatible)
    for incompatible in (alex_workspace(actual="CK"), alex_workspace(count=3),
                         _build_match_workspace_v1(match_definition=workspace.match_definition,
                             revision=workspace.revision + 1, slots=workspace.slots)):
        # A short prefix with the same source revision and safe own hand is legitimately
        # compatible; the policy compares reconstructed knowledge, not the whole file.
        if incompatible == alex_workspace(count=3):
            assert replace(retained, snapshot=snapshot(incompatible)).report is retained.report
        else:
            with pytest.raises(ValueError):
                replace(retained, snapshot=snapshot(incompatible))


def test_duplicate_elapsed_and_setting_variants_keep_distinct_units(retained):
    store = DebriefSourceStoreV1()
    assert store.add(retained) == "applied"
    assert store.add(retained) == "unchanged"
    raw = retained.report.value.result.to_dict()["document"]
    raw["whole_game_rollout_result"]["work"]["elapsed_ms"] += 1
    result = ResultDocumentV1(workflow=retained.report.value.result.workflow, document=raw)
    elapsed = replace(retained, report=build_match_analysis_report_v1(
        replace(retained.report.value, result=result)))
    assert elapsed.semantic_fingerprint == retained.semantic_fingerprint
    assert store.add(elapsed) == "applied"
    other = evidence(retained.snapshot.workspace, options=rollout_options("played_game_goal"))
    store.add(other)
    view = build_debrief_projection((retained.snapshot,), store.sources, player_id="alex")
    assert view.recorded_decisions == 10 and len(view.decisions) == 1
    assert view.report_count == 3 and view.semantic_report_count == 2
    assert len(view.decisions[0].reports) == 3
    other_player = build_debrief_projection((retained.snapshot,), store.sources, player_id="bea")
    assert other_player.recorded_decisions == 10 and other_player.report_count == 0


@pytest.mark.parametrize("count,known", ((0, True), (3, False), (30, False)))
def test_empty_and_partially_reconstructed_counts_are_recorded_units(count, known):
    source = snapshot(alex_workspace(count=count, known_hand=known))
    view = build_debrief_projection((source,), ())
    assert view.recorded_decisions == count and view.report_count == 0
    html = render_debrief(DebriefScopeV1("a" * 64, (source,), ()), "en")
    assert "No completed comparisons are included" in html
    assert "Choose a recorded decision" in html and "dataset_status" not in html


@pytest.mark.parametrize("objective", ("played_game_goal", "complete_settlement"))
def test_forced_move_and_both_objectives(objective):
    item = evidence(alex_workspace(), decision=30, options=replace(
        rollout_options(objective), settlement_supplements={}))
    html = render_debrief(DebriefScopeV1("a" * 64, (item.snapshot,), (item,)), "en")
    assert "CK" in html and text("en", "rollout.only_card") in html


def test_incomplete_and_raw_reports_never_become_comparison_evidence():
    workspace = alex_workspace(count=3)
    source = snapshot(workspace)
    report = build_match_analysis_report_v1(execute_match_decision_analysis_v1(workspace,
        match_position=2, decision_index=3, options=rollout_options(max_card_transitions=1)))
    for supplied in (report, report.to_dict()):
        with pytest.raises(ValueError, match="completed"):
            MatchDebriefEvidenceV1(supplied, source, source)


def test_tampering_is_rejected_even_when_bypassing_frozen_constructor(retained):
    report = replace(retained.report)
    object.__setattr__(report, "report_id", "0" * 64)
    with pytest.raises(ValueError, match="identity"):
        replace(retained, report=report)


def test_real_distinct_game_topics_are_not_report_counts():
    workspace = alex_workspace()
    original = workspace.slots[1].observed_game
    second = _observed_game(workspace.match_definition, match_position=5,
        perspective_initial_hand=original.perspective_initial_hand,
        declarer_player_id=original.declarer_player_id, declaration=original.declaration,
        plays=original.plays)
    workspace = _set_game(workspace, second)
    first = evidence(workspace)
    same_game = evidence(workspace, decision=5)
    second_game = evidence(workspace, position=5, decision=5)
    tactical = build_learning_corpus_tactical_motif_evidence_collection_v1(
        _store(first.snapshot, current=(first.snapshot,)))
    single = build_debrief_projection((first.snapshot,), (first, first, same_game),
                                      tactical=tactical)
    assert all(games == 1 for _, _, _, games in single.topics)
    combined = build_debrief_projection((first.snapshot,), (first, same_game, second_game),
                                        tactical=tactical)
    assert combined.topics and any(games == 2 for _, _, _, games in combined.topics)
    assert all(player == "alex" for player, _, _, _ in combined.topics)
    assert not combined.focuses


def comparison_variant(retained, *, lower_actual):
    """Explicit synthetic comparison variants from one real retained execution."""
    value = retained.report.value
    raw = value.result.to_dict()["document"]
    aggregate = raw["whole_game_rollout_result"]
    actual = value.request.document["actual_card_played"]
    first = aggregate["candidates"][0]
    candidates = tuple(WholeGameRolloutCandidateV1(**{
        **{field.name: first[field.name] for field in fields(WholeGameRolloutCandidateV1)},
        "card": row["card"],
        "local_success_count": 0 if lower_actual and row["card"] == actual
            else first["completed_samples"],
    }) for row in aggregate["candidates"])
    ranked = sorted(candidates, key=lambda item: item.comparison_key(), reverse=True)
    ties = tuple(item.card for item in ranked
                 if item.comparison_key() == ranked[0].comparison_key())
    typed = WholeGameRolloutResultV1(**{
        **{field.name: aggregate[field.name] for field in fields(WholeGameRolloutResultV1)
           if field.name not in {"settings", "work", "candidates", "ranked_cards",
                                 "tied_best_cards", "recommended_card"}},
        "settings": value.options.rollout_settings,
        "work": WholeGameRolloutWorkV1(**aggregate["work"]), "candidates": candidates,
        "ranked_cards": tuple(item.card for item in ranked), "tied_best_cards": ties,
        "recommended_card": ties[0]})
    raw["whole_game_rollout_result"] = serialize_rollout_result(typed)
    raw["whole_game_rollout_comparison"] = compare_rollout_actual(typed, actual)
    raw["recommendation"]["card"] = typed.recommended_card
    return replace(retained, report=build_match_analysis_report_v1(replace(value,
        result=ResultDocumentV1(workflow=value.result.workflow, document=raw))))


def test_exact_ties_and_conflicting_variants_remain_visible(retained):
    tied = comparison_variant(retained, lower_actual=False)
    lower = comparison_variant(retained, lower_actual=True)
    scope = DebriefScopeV1("a" * 64, (retained.snapshot,), (tied, lower))
    view = build_debrief_projection(scope.snapshots, scope.sources)
    assert view.report_count == 2 and len(view.decisions) == 1 and view.decisions[0].mixed
    for locale in ("de", "en"):
        html = render_debrief(scope, locale)
        assert text(locale, "debrief.mixed") in html
        assert html.count(text(locale, "debrief.comparison")) == 2
        assert all(f"({card})" in html for card in tied.report.value.result.document[
            "whole_game_rollout_result"]["tied_best_cards"])
    assert "equally recommended" in render_debrief(scope, "en")
    assert view.focuses == ()


@pytest.mark.parametrize("mutation", ("settings", "legal", "profile"))
def test_generic_result_copies_cannot_contradict_validated_aggregate(retained, mutation):
    raw = retained.report.value.result.to_dict()["document"]
    if mutation == "settings":
        raw["settings"]["whole_game_rollout_settings"]["random_seed"] = 45
    elif mutation == "legal":
        raw["legal_cards"] = ["C7"]
    else:
        raw["profile_preset_settings"]["use_profile_presets"] = True
    result = ResultDocumentV1(workflow=retained.report.value.result.workflow, document=raw)
    report = build_match_analysis_report_v1(replace(retained.report.value, result=result))
    with pytest.raises(ValueError, match="Debrief"):
        replace(retained, report=report)


def test_qualified_legacy_focus_content_is_rendered_without_threshold_recalculation(monkeypatch):
    from test_learning_corpus_strategy_teacher import _source_bundle
    from test_learning_corpus_tactical_coaching import _below_best_search_result, _report

    def search(**kwargs):
        return _below_best_search_result(**kwargs, expected_seed=9,
                                        below_best_cards=frozenset({"C8"}))
    monkeypatch.setattr("skatmind.recommendation_workflow.solve_compatible_world_minimax", search)
    bundles = tuple(_source_bundle(recommendation_method="bounded_search", decision_index=22,
        match_id=f"synthetic-debrief-focus-{index}", search_random_seed=9,
        search_budget_profile="interactive_v1") for index in (1, 2))
    snapshots = tuple(item[1] for item in bundles)
    coaching = _report(_store(*snapshots, current=snapshots), tuple(item[4] for item in bundles))
    assert coaching.focus_areas
    monkeypatch.setattr("skatmind.recommendation_workflow.solve_compatible_world_minimax",
                        lambda **kwargs: pytest.fail("Retained focuses must not execute Search"))
    scope = DebriefScopeV1("a" * 64, snapshots, (), coaching=coaching)
    view = build_debrief_projection(snapshots, (), coaching=coaching)
    assert view.focuses == coaching.focus_areas
    html = render_debrief(scope, "en")
    for focus in coaching.focus_areas:
        assert focus.guidance_text in html
    assert "2 distinct decisions in 2 distinct games" in html
