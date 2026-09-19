"""Real shared producers and strict retained old/new Report and Teacher boundaries."""

import json
from pathlib import Path

from test_historical_game import build_historical_input
from test_learning_corpus_strategy_teacher import _changed_report, _source_bundle

from skatmind.api.v1 import execute, parse_request
from skatmind.app_web.result_immediate import retained_immediate_best_cards
from skatmind.app_web.result_presentation import build_result_presentation_v1
from skatmind.historical_decision_snapshot import build_historical_decision_snapshots
from skatmind.historical_game import build_historical_game_record, build_historical_game_summary
from skatmind.historical_game_review import build_historical_game_review_summary
from skatmind.historical_search_review import (
    HistoricalSearchReviewSettings,
    build_historical_search_decision_review,
)
from skatmind.learning_corpus_strategy_teacher import (
    build_learning_corpus_strategy_teacher_report_source_v1,
    build_learning_corpus_strategy_teacher_result_fingerprint_v1,
)
from skatmind.learning_corpus_strategy_teacher_builder import (
    build_learning_corpus_strategy_teacher_evidence_collection_v1,
)
from skatmind.match_analysis_report_source_codec import (
    resume_match_analysis_report_source_export_v1,
)
from skatmind.match_analysis_report_source_export import (
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)


def test_real_match_tie_and_old_new_teacher_strict_roundtrips():
    _, snapshot, result, fresh_report, fresh_source, store = _source_bundle(decision_index=8)
    document = result.result.to_dict()["document"]
    assert retained_immediate_best_cards(document) == ("S8", "S7", "D8", "D7")
    assert "S8, S7, D8, D7 are equally best" in document["recommendation"]["reason"]
    assert "equally best" in document["strategic_summary"]
    # Exact pre-#240 producer leaves for this deterministic legal Match fixture.
    document["recommendation"]["reason"] = (
        "This card has the highest estimated immediate expected point swing: -12.00.")
    document["strategic_summary"] = (
        "Strategic summary: S8 is recommended because it is the least damaging option in "
        "this position. Even the best option has a non-positive expected point swing of -12.00.")
    old_report = _changed_report(result, result_document=document)
    assert old_report.report_id != fresh_report.report_id
    sources = []
    for report in (old_report, fresh_report):
        export = build_match_analysis_report_source_export_v1(report)
        raw = serialize_match_analysis_report_source_export_v1(export)
        resumed = resume_match_analysis_report_source_export_v1(json.loads(raw))
        assert serialize_match_analysis_report_source_export_v1(resumed) == raw
        assert resumed.report == report
        source = build_learning_corpus_strategy_teacher_report_source_v1(
            match_snapshot_id=snapshot.match_snapshot_id, report=resumed.report)
        assert source.source_result_fingerprint == (
            build_learning_corpus_strategy_teacher_result_fingerprint_v1(report.value.result))
        collection = build_learning_corpus_strategy_teacher_evidence_collection_v1(store, (source,))
        evidence, = collection.evidences
        assert evidence.strategic_summary == report.value.result.document["strategic_summary"]
        assert evidence.recommendation["reason"] == (
            report.value.result.document["recommendation"]["reason"])
        assert serialize_match_analysis_report_source_export_v1(resumed) == raw
        sources.append(source)
    assert sources[1] == fresh_source
    assert sources[0].source_request_fingerprint == sources[1].source_request_fingerprint
    assert sources[0].source_result_fingerprint != sources[1].source_result_fingerprint
    combined = build_learning_corpus_strategy_teacher_evidence_collection_v1(store, tuple(sources))
    assert len(combined.evidences) == 2
    assert len({e.teacher_semantic_fingerprint for e in combined.evidences}) == 2


def test_real_historical_immediate_and_search_baseline_reuse_tie_producer():
    record = build_historical_game_record(build_historical_input())
    snapshots = build_historical_decision_snapshots(build_historical_game_summary(record))
    history = build_historical_game_review_summary(
        snapshots, record, sample_count=1, base_random_seed=0)
    immediate = history["decisions"][7]
    baseline = build_historical_search_decision_review(
        snapshots.snapshots[7], record, HistoricalSearchReviewSettings(
            base_search_seed=0, immediate_sample_count=1, immediate_base_random_seed=0))
    assert "equally best" in immediate["recommendation"]["reason"]
    assert baseline["immediate_baseline"]["recommendation"] == immediate["recommendation"]
    assert baseline["immediate_baseline"]["analysis_report"] == immediate["analysis_report"]
    assert sum(row["is_recommended"] for row in immediate["analysis_report"]) == 1


def test_real_effective_search_preserves_primary_candidate_table():
    path = (Path(__file__).resolve().parents[1]
            / "examples/grand_bounded_search_post_game_review.json")
    result = execute(parse_request(json.loads(path.read_text(encoding="utf-8"))))
    document = result.result.document
    assert document["recommendation_method_summary"]["effective_method"] == (
        "compatible_world_minimax_v1")
    assert retained_immediate_best_cards(document) == ()
    table = build_result_presentation_v1(result).sections[2].tables[0]
    assert table.caption == "Search Candidate comparisons in public Result order"
    assert table.columns[:3] == ("Card", "Rank", "Recommended")
    assert table.rows[0][:3] == ("D7", "1", "Yes")
