from __future__ import annotations

import copy
import re
from dataclasses import FrozenInstanceError, replace
from html import unescape

import pytest

from skatmind.api.v1 import (
    ExecutionResultV1,
    ResultDocumentV1,
    WorkflowV1,
    execute,
    parse_request,
    serialize_result,
)
from skatmind.app_web.guided_contracts import (
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESULT_DOWNLOAD_ROUTE_PATH,
)
from skatmind.app_web.result_presentation import (
    RESULT_SECTION_TITLES_V1,
    TEXTUAL_NORMAL_RESULT_STATES_V1,
    BrowserSafeResultPresentationV1,
    build_result_presentation_v1,
)
from skatmind.app_web.result_rendering import (
    render_result_presentation_v1,
    render_safe_result_error_summary_v1,
)
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


def score_review_request():
    """Public R09-equivalent input, independent of saved Session defaults."""
    return {
        "analysis_mode": "post_game_review", "game_type": "grand",
        "player_role": "defender", "player_position": "rearhand",
        "declarer_player": "left", "trick_leader": "left", "next_player": "me",
        "hand": ["C10", "CJ", "SA", "SJ", "HA", "DK", "D7"],
        "current_trick": ["HJ", "DJ"], "played_cards": [],
        "completed_tricks": [
            {"cards": ["CK", "C7", "CA"], "players": ["left", "right", "me"],
             "winner_player": "me", "winner_role": "defenders"},
            {"cards": ["SK", "S7", "S10"], "players": ["me", "left", "right"],
             "winner_player": "right", "winner_role": "defenders"},
            {"cards": ["HK", "H9", "H10"], "players": ["right", "me", "left"],
             "winner_player": "left", "winner_role": "declarer"},
        ],
        "declarer_points": 0, "defender_points": 0, "skat": [],
        "skat_visibility": "unknown", "game_end_reason": "not_ended",
        "game_declaration": {
            "game_type": "grand", "hand_game": False, "ouvert": False,
            "schneider_announced": False, "schwarz_announced": False,
            "matadors": 2, "bid_value": 18,
        },
        "left_hand_size": 6, "right_hand_size": 6, "sample_count": 100,
        "random_seed": 0, "use_basic_opponent_strategy": True, "actual_card_played": "SJ",
    }


def assert_summary_points(html, locale, declarer, defenders):
    """Check labelled values in the normal Summary, excluding technical duplicates."""
    summaries = re.findall(
        r'<section aria-labelledby="result-section-1">(.*?)</section>', html, re.S)
    assert len(summaries) == 1
    summary, = summaries
    assert f'>{text(locale, "result.summary")}</h2>' in summary
    assert "<details" not in summary
    details = {unescape(label): unescape(value) for label, value in
               re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", summary)}
    for key, expected in (("guided.declarer_points", declarer),
                          ("guided.defender_points", defenders)):
        assert details[text(locale, key)] == (
            text(locale, "status.unavailable") if expected is None else str(expected))


@pytest.mark.parametrize(
    ("with_tricks", "supplements", "expected"),
    ((True, (0, 0), (14, 29)), (True, (5, 7), (19, 36)),
     (False, (5, 7), (5, 7)), (False, (0, 0), (0, 0))),
)
def test_executed_position_known_totals_in_normal_summary(with_tricks, supplements, expected):
    document = score_review_request()
    document["declarer_points"], document["defender_points"] = supplements
    if not with_tricks:
        document.update(
            completed_tricks=[], current_trick=[], player_position="forehand",
            trick_leader="me", hand=["CA", "C10", "CJ", "SA", "SK", "SJ", "HA", "H9", "DK", "D7"],
            left_hand_size=10, right_hand_size=10,
        )
    original = copy.deepcopy(document)
    request = parse_request(document)
    execution = execute(request)
    retained = serialize_result(execution)
    score = execution.result.document["score_summary"]
    assert (score["total_declarer_points"], score["total_defender_points"]) == expected
    assert (score["explicit_declarer_points"], score["explicit_defender_points"]) == supplements
    if with_tricks:
        assert execution.result.document["position"]["current_trick"] == ("HJ", "DJ")
        assert score["completed_trick_declarer_points"] == 14
        assert score["completed_trick_defender_points"] == 15 + 14
    for locale in ("de", "en"):
        presentation = build_result_presentation_v1(execution, locale=locale)
        details = {detail.label: detail.value for detail in presentation.sections[0].details}
        assert (details["Declarer points"], details["Defender points"]) == tuple(map(str, expected))
        assert_summary_points(render_result_presentation_v1(presentation, locale=locale),
                              locale, *expected)
    assert serialize_result(execution) == retained
    assert request.to_dict()["document"] == document == original


@pytest.mark.parametrize("side", ("declarer", "defender"))
@pytest.mark.parametrize("invalid", (None, True, False, "14", 14.0, 1.5, [], {}))
def test_defensive_non_integer_total_is_unavailable_per_side(side, invalid):
    document = _position_document()
    document["score_summary"] = {"total_declarer_points": 14, "total_defender_points": 29}
    document["score_summary"][f"total_{side}_points"] = invalid
    original = copy.deepcopy(document)
    execution = _execution(WorkflowV1.POSITION_ANALYSIS, document)
    expected = (None, 29) if side == "declarer" else (14, None)
    for locale in ("de", "en"):
        assert_summary_points(render_result_presentation_v1(
            build_result_presentation_v1(execution, locale=locale), locale=locale),
            locale, *expected)
    assert execution.result.to_dict()["document"] == document == original


@pytest.mark.parametrize("summary", ("missing", None, [], {}, {"total_declarer_points": 0},
                                    {"total_defender_points": 29}))
def test_defensive_missing_totals_never_use_position_or_placeholder_tricks(summary):
    document = _position_document()
    if summary != "missing":
        document["score_summary"] = summary
    expected = (summary.get("total_declarer_points"), summary.get("total_defender_points")) \
        if isinstance(summary, dict) else (None, None)
    for locale in ("de", "en"):
        assert_summary_points(render_result_presentation_v1(build_result_presentation_v1(
            _execution(WorkflowV1.POSITION_ANALYSIS, document), locale=locale), locale=locale),
            locale, *expected)


@pytest.mark.parametrize("method", ("immediate_expected_value", "compatible_world_minimax_v1",
                                  "bounded_information_set_policy_search_v1"))
def test_only_score_details_change_independently_of_method_and_ending_context(method):
    document = _position_document()
    document["recommendation_method_summary"]["effective_method"] = method
    document["score_summary"] = {"total_declarer_points": 14, "total_defender_points": 29}
    before = build_result_presentation_v1(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    document["score_summary"] = {"total_declarer_points": 19, "total_defender_points": 36}
    document["game_result_summary"] = {"declarer_points": 42, "defender_points": 78}
    document["adjusted_score_summary"] = {"total_declarer_points": 120, "total_defender_points": 0}
    after = build_result_presentation_v1(_execution(WorkflowV1.POSITION_ANALYSIS, document))
    assert_summary_points(render_result_presentation_v1(before), "en", 14, 29)
    assert_summary_points(render_result_presentation_v1(after), "en", 19, 36)
    def without_scores(presentation):
        summary = presentation.sections[0]
        return replace(presentation, sections=(replace(summary, details=tuple(
            detail for detail in summary.details
            if detail.label not in {"Declarer points", "Defender points"})),
            *presentation.sections[1:]))
    assert without_scores(before) == without_scores(after)


def _execution(
    workflow: WorkflowV1,
    document: dict[str, object],
    *,
    warnings: tuple[str, ...] = (),
) -> ExecutionResultV1:
    return ExecutionResultV1(
        result=ResultDocumentV1(
            workflow=workflow,
            document=document,
            warnings=warnings,
        )
    )


def _position_document(*, status: str = "partial") -> dict[str, object]:
    return {
        "input_file": "C:/private/result-input.json",
        "position": {
            "game_type": "grand",
            "player_role": "defender",
            "player_position": "rearhand",
            "next_player": "me",
            "current_trick": ["S7", "S8"],
            "completed_tricks": [{"private_cards": ["CA"]}],
            "declarer_points": 41,
            "defender_points": 30,
            "private_hand": ["CA"],
        },
        "settings": {"sample_count": 20, "recommendation_method": "auto"},
        "game_declaration": {
            "game_type": "grand",
            "hand_game": False,
            "ouvert": False,
            "matadors": 2,
            "bid_value": 24,
        },
        "legal_cards": ["S7", "H9"],
        "recommendation": {
            "card": "H9",
            "reason": "Prefer H9 over <unsafe & unescaped>.",
            "private_reason": "do-not-render-private-reason",
        },
        "recommendation_method_summary": {
            "requested_method": "auto",
            "effective_method": "immediate_expected_value",
            "fallback_used": True,
            "fallback_method": "immediate_expected_value",
            "private_seed": 999,
        },
        "analysis_report": [
            {
                "card": "H9",
                "is_recommended": True,
                "win_rate": 0.75,
                "expected_point_swing": 3.5,
                "average_trick_points": 7.0,
                "private_world": "first-secret",
            },
            {
                "card": "S7",
                "is_recommended": False,
                "win_rate": 0.5,
                "expected_point_swing": 1.0,
                "average_trick_points": 4.0,
                "private_world": "second-secret",
            },
        ],
        "bounded_search_result": {
            "status": status,
            "stop_reason": "node_budget_exhausted",
            "world_coverage": "sampled_compatible_worlds",
            "compatible_world_count": 18,
            "candidate_results": [
                {"card": "CA", "private_world": "unused-secret"},
            ],
            "requested_budget": {
                "max_remaining_tricks": 3,
                "max_depth_plies": 9,
                "max_selected_worlds": 4,
                "max_sampled_worlds": 4,
                "minimum_comparable_worlds": 2,
                "wall_clock_timeout_ms": None,
            },
            "consumed_budget": {
                "selected_world_count": 4,
                "completed_world_count": 2,
                "sampled_world_count": 4,
                "unique_sampled_world_count": 3,
                "nodes_expanded": 12,
            },
            "private_states": ["raw-complete-marker"],
        },
        "information_policy_summary": {
            "analysis_mode": "post_game_review",
            "skat_visibility": "known_post_game",
            "game_end_reason": "not_ended",
        },
        "post_game_review_summary": {
            "actual_card_played": "S7",
            "decision_quality": "acceptable",
        },
        "private_provenance": {"fingerprint": "raw-complete-marker"},
    }


def _historical_document() -> dict[str, object]:
    return {
        "input_file": "C:/private/history.json",
        "historical_game_summary": {
            "schema_version": 1,
            "game_id": "game-<unsafe>",
            "status": "complete",
            "played_at": "2026-08-31T10:00:00+00:00",
            "record": {
                "game_id": "game-<unsafe>",
                "declarer_player_id": "player-b",
                "declaration": {
                    "game_type": "clubs",
                    "hand_game": True,
                    "ouvert": False,
                    "bid_value": 36,
                    "matadors": 2,
                },
                "game_end_reason": "party_wide_all_remaining_tricks_claim",
                "tricks": [{"raw_cards": ["CA"]}],
                "players": [
                    {
                        "player_id": "player-a",
                        "player_label": "Alex",
                        "seat": "forehand",
                        "initial_hand": ["raw-complete-marker"],
                    },
                    {
                        "player_id": "player-b",
                        "player_label": "Blair",
                        "seat": "middlehand",
                    },
                    {"player_id": "player-c", "seat": "rearhand"},
                ],
            },
            "derived_tricks": [
                {"trick_number": 1, "private_plays": ["CA"]},
                {"trick_number": 2, "private_plays": ["SA"]},
            ],
            "declarer_points": 72,
            "defender_points": 48,
            "winner": "declarer",
            "schneider_status": "none",
            "schwarz_status": "none",
            "game_result_summary": {
                "status": "final",
                "winner": "declarer",
                "game_end_reason": "party_wide_all_remaining_tricks_claim",
            },
            "game_value_summary": {"game_value": 36},
            "overbid_summary": {"status": "not_overbid", "required_game_value": 36},
            "final_settlement_summary": {
                "is_complete": True,
                "effective_game_value": 36,
                "settlement_score": 36,
            },
            "historical_game_review_summary": {
                "analysis_method": "immediate_expected_value",
                "decision_count": 2,
                "reviewed_decision_count": 1,
                "unavailable_decision_count": 1,
                "decisions": [
                    {
                        "decision_index": 1,
                        "trick_number": 1,
                        "play_index": 1,
                        "acting_player_id": "player-<a>",
                        "actual_card_played": "CA",
                        "recommendation": {"card": "CA"},
                        "post_game_review_summary": {"decision_quality": "optimal"},
                        "private_snapshot": "first-decision-secret",
                    },
                    {
                        "decision_index": 2,
                        "trick_number": 1,
                        "play_index": 2,
                        "acting_player_id": "player-b",
                        "actual_card_played": "S7",
                        "recommendation": {"card": "S8"},
                        "post_game_review_summary": {"decision_quality": "mistake"},
                        "private_snapshot": "second-decision-secret",
                    },
                ],
            },
            "historical_search_review_summary": {
                "analysis_method": "bounded_search_with_immediate_baseline",
                "decision_counts": {"decision_count": 1},
                "status_counts": {
                    "complete": 0,
                    "partial": 0,
                    "timeout": 1,
                    "unavailable": 0,
                },
                "coverage": {
                    "exact_coverage_decision_count": 0,
                    "sampled_coverage_decision_count": 1,
                    "no_coverage_decision_count": 0,
                },
                "decisions": [
                    {
                        "decision_index": 2,
                        "trick_number": 1,
                        "play_index": 2,
                        "actual_card": "S7",
                        "bounded_search_result": {
                            "status": "timeout",
                            "recommended_card": None,
                        },
                        "immediate_baseline": {"recommendation": {"card": "S8"}},
                        "search_actual_card_comparison": {"is_available": False},
                    }
                ],
            },
            "historical_replay_coaching_summary": {
                "report_method": "historical_replay_coaching_v1",
                "limitations": [
                    "single_recorded_game_only",
                    "no_causal_outcome_claim",
                    "private_coaching_secret",
                ],
            },
            "historical_tactical_motif_review_summary": {
                "review_method": "historical_tactical_motif_review_v1",
                "observation_count": 2,
                "motif_occurrence_count": 3,
                "limitations": [
                    "structural_observation_not_quality_assessment",
                    "no_hidden_ownership_inference",
                ],
            },
            "historical_game_end_summary": {
                "kind": "party_wide_all_remaining_tricks_claim",
                "proof_maximum_unresolved_tricks": 5,
                "exact_proof": {
                    "status": "valid",
                    "evaluated_state_count": 12,
                    "terminal_state_count": 3,
                    "representative_line": ["raw-complete-marker"],
                },
            },
            "private_review": "raw-complete-marker",
        },
        "private_provenance": {"fingerprint": "raw-complete-marker"},
    }


def test_position_projection_is_immutable_minimized_and_preserves_candidate_order() -> None:
    execution = _execution(
        WorkflowV1.POSITION_ANALYSIS,
        _position_document(),
        warnings=("Warning <one> & retained.",),
    )

    presentation = build_result_presentation_v1(execution)

    assert type(presentation) is BrowserSafeResultPresentationV1
    assert tuple(section.title for section in presentation.sections) == RESULT_SECTION_TITLES_V1
    assert presentation.warnings == ("Warning <one> & retained.",)
    alternatives = presentation.sections[2].tables[0]
    assert [row[0] for row in alternatives.rows] == ["H9", "S7"]
    assert alternatives.rows[0][2] == "75.00%"
    serialized_projection = repr(presentation)
    for forbidden in (
        "private_world",
        "private_hand",
        "private_seed",
        "raw-complete-marker",
        "result-input.json",
        "fingerprint",
        "unused-secret",
    ):
        assert forbidden not in serialized_projection
    with pytest.raises(FrozenInstanceError):
        presentation.workflow = "historical_game"  # type: ignore[misc]


def test_position_renderer_has_exact_semantic_sections_escaping_and_downloads() -> None:
    presentation = build_result_presentation_v1(
        _execution(
            WorkflowV1.POSITION_ANALYSIS,
            _position_document(),
            warnings=("Warning <one> & retained.",),
        )
    )

    html = render_result_presentation_v1(
        presentation,
        request_download_available=True,
        result_download_available=True,
    )

    assert html.count("<section ") == 5
    heading_positions = [html.index(f'id="result-section-{index}"') for index in range(1, 6)]
    assert heading_positions == sorted(heading_positions)
    assert html.count("<h2 ") == 4
    assert '<summary id="result-section-5">Technical analysis details</summary>' in html
    assert '<table class="candidate-table" role="table">' in html
    assert re.search(r'<th scope="col"[^>]*>Card</th>', html)
    assert "Prefer H9 over &lt;unsafe &amp; unescaped&gt;." in html
    assert "Warning &lt;one&gt; &amp; retained." in html
    assert "<unsafe" not in html
    assert '<details class="technical-details">' in html
    assert "<details open" not in html
    assert f'href="{ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH}" download' in html
    assert f'href="{ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH}" download' in html
    assert REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH not in html
    assert REVIEW_RESULT_DOWNLOAD_ROUTE_PATH not in html
    assert text("en", "result.value.partial") in html
    assert "not a perfect-play claim" in html
    assert "not calibrated probability" in html
    assert "analysis cutoff" in html
    assert "fixed public policy" in html
    for forbidden in (
        "private_world",
        "private_hand",
        "raw-complete-marker",
        "result-input.json",
        "fingerprint",
        "field_provenance",
        "unused-secret",
    ):
        assert forbidden not in html


@pytest.mark.parametrize("status", TEXTUAL_NORMAL_RESULT_STATES_V1)
def test_normal_result_states_remain_textual_non_error_states(status: str) -> None:
    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.POSITION_ANALYSIS, _position_document(status=status))
    )

    html = render_result_presentation_v1(presentation)

    assert f'<dd>{text("en", "result.value." + status)}</dd>' in html
    assert "result-error" not in html
    assert ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH not in html
    assert ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH not in html


def test_historical_projection_covers_outcome_reviews_and_bounded_families() -> None:
    presentation = build_result_presentation_v1(
        _execution(
            WorkflowV1.HISTORICAL_GAME,
            _historical_document(),
            warnings=("Imported ending retained.",),
        )
    )

    summary = {detail.label: detail.value for detail in presentation.sections[0].details}
    assert summary == {
        "Status": "complete",
        "Players": "Alex, Blair, Rearhand",
        "Declarer": "Blair",
        "Declaration": "clubs",
        "Game end": "party_wide_all_remaining_tricks_claim",
        "Completed Tricks": "2",
        "Declarer points": "72",
        "Defender points": "48",
        "Winner": "declarer",
        "Result": "final",
        "Overbid": "not_overbid",
        "Settlement": "36",
        "Hand game": "Yes",
        "Ouvert": "No",
        "Bid value": "36",
        "Matadors": "2",
        "Immediate review Decisions": "2",
        "Bounded Search review Decisions": "1",
    }
    assert presentation.sections[1].paragraphs == (
        "A completed game has no single whole-game Card recommendation.",
        "Decision reviews remain bounded to their retained public evidence and do not "
        "establish one globally optimal game policy.",
    )
    assert any(detail.label == "Game ID" and detail.value == "game-<unsafe>"
               for detail in presentation.sections[4].details)
    alternatives = presentation.sections[2].tables
    assert [row[0] for row in alternatives[0].rows] == ["1", "2"]
    assert alternatives[1].rows[0][6] == "timeout"
    evidence = " ".join(presentation.sections[3].items)
    assert "Replay Coaching" in evidence
    assert "Tactical motifs are structural observations" in evidence
    assert "Claim adjudication is limited" in evidence
    assert "no_causal_outcome_claim" in evidence
    assert "private_coaching_secret" not in evidence
    assert "no_hidden_ownership_inference" not in evidence


def test_historical_renderer_escapes_values_and_excludes_raw_result_content() -> None:
    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, _historical_document())
    )

    html = render_result_presentation_v1(
        presentation,
        request_download_available=True,
        result_download_available=True,
    )

    assert html.count("<section ") == 5
    assert "game-&lt;unsafe&gt;" in html
    assert "player-&lt;a&gt;" not in html
    assert "Unnamed Player" in html
    assert "A completed game has no single whole-game Card recommendation." in html
    assert html.index('<th scope="row">1</th>') < html.index('<th scope="row">2</th>')
    assert text("en", "result.value.timeout") in html
    assert REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH in html
    assert REVIEW_RESULT_DOWNLOAD_ROUTE_PATH in html
    assert ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH not in html
    assert ANALYZE_RESULT_DOWNLOAD_ROUTE_PATH not in html
    for forbidden in (
        "raw-complete-marker",
        "private_review",
        "private_snapshot",
        "history.json",
        "fingerprint",
        "field_provenance",
        "representative_line",
        "no_hidden_ownership_inference",
    ):
        assert forbidden not in html


def test_information_set_and_simulation_results_use_retained_public_order() -> None:
    document = _position_document(status="complete")
    document["recommendation_method_summary"] = {
        "requested_method": "information_set_search",
        "effective_method": "bounded_information_set_policy_search_v1",
        "fallback_used": False,
    }
    document["information_set_search_result"] = {
        "status": "complete",
        "candidate_results": [
            {
                "card": "D8",
                "rank": 1,
                "is_recommended": True,
                "completed_world_count": 3,
            },
            {
                "card": "D7",
                "rank": 2,
                "is_recommended": False,
                "completed_world_count": 3,
            },
        ],
    }
    document["multi_step_result"] = {
        "requested_step_count": 2,
        "steps_simulated": 2,
        "stop_reason": "completed",
        "card_selection_policy": "highest_expected_value",
    }
    document["policy_comparison_result"] = {
        "requested_step_count": 2,
        "recommended_policy": {"policy": "highest_expected_value"},
    }

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.POSITION_ANALYSIS, document)
    )

    alternatives = presentation.sections[2].tables[0]
    assert [row[0] for row in alternatives.rows] == ["D8", "D7"]
    technical = {detail.label: detail.value for detail in presentation.sections[4].details}
    assert technical["Multi-Step requested Decisions"] == "2"
    assert technical["Multi-Step simulated Decisions"] == "2"
    assert technical["Recommended comparison Policy"] == "highest_expected_value"


def test_bounded_search_effective_method_uses_search_candidates() -> None:
    document = _position_document(status="complete")
    document["recommendation_method_summary"] = {
        "requested_method": "bounded_search",
        "effective_method": "compatible_world_minimax_v1",
        "fallback_used": False,
    }
    document["bounded_search_result"] = {
        "status": "complete",
        "candidate_results": [
            {
                "card": "D8",
                "rank": 1,
                "is_recommended": True,
                "completed_world_count": 3,
            }
        ],
    }

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.POSITION_ANALYSIS, document)
    )

    assert presentation.sections[2].tables[0].rows[0][0] == "D8"


def test_historical_information_set_coaching_is_separate_bounded_evidence() -> None:
    document = _historical_document()
    summary = document["historical_game_summary"]
    assert isinstance(summary, dict)
    summary["historical_information_set_search_review_summary"] = {
        "review_method": "historical_information_set_search_review_v1",
        "decision_count": 1,
        "status_counts": {"complete": 1, "not_available": 0},
        "selected_world_count_total": 2,
        "sampled_world_count_total": 2,
        "decisions": [
            {
                "decision_index": 1,
                "trick_number": 1,
                "play_index": 1,
                "actual_card": "CA",
                "information_set_search_result": {
                    "recommended_card": "CA",
                    "status": "complete",
                },
                "same_selection_pimc_result": {"recommended_card": "CA"},
                "immediate_baseline": {"recommended_card": "C10"},
                "comparison": {"comparison_status": "available"},
            }
        ],
    }
    summary["historical_information_set_replay_coaching_summary"] = {
        "report_method": "historical_information_set_replay_coaching_v1",
        "limitations": ("complete_candidate_evidence_only",),
    }

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, document)
    )

    assert len(presentation.sections[2].tables) == 3
    evidence = " ".join(presentation.sections[3].items)
    assert "Information-set Coaching uses complete Candidate evidence without fallback." in evidence
    assert "complete_candidate_evidence_only" in evidence
    assert "ground truth" in evidence


@pytest.mark.parametrize(
    "ending",
    (
        "defender_concession",
        "declarer_card_exposure_continuation",
        "impossible_null",
    ),
)
def test_supported_historical_endings_remain_normal_presented_results(ending: str) -> None:
    document = _historical_document()
    summary = document["historical_game_summary"]
    assert isinstance(summary, dict)
    record = summary["record"]
    assert isinstance(record, dict)
    record["game_end_reason"] = ending
    summary["historical_game_end_summary"] = {"kind": ending}

    presentation = build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, document)
    )

    details = {detail.label: detail.value for detail in presentation.sections[0].details}
    assert details["Game end"] == ending
    assert details["Settlement"] == "36"
    assert presentation.sections[1].title == "Recommendation"


def test_safe_error_summary_is_separate_and_escaped() -> None:
    html = render_safe_result_error_summary_v1(
        title="Could not <run>",
        message="Invalid & rejected input.",
    )

    assert "Could not &lt;run&gt;" in html
    assert "Invalid &amp; rejected input." in html
    assert "<run>" not in html
