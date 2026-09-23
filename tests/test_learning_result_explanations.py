"""Literal presentation contract; scalar specimens supplement real HTTP preparation."""

from copy import deepcopy

import pytest
from test_learning_direct_entry_web import (
    add_form,
    create_collection,
    downloads,
    source_handle,
)
from test_learning_outcome_navigation import localized_server as _localized_server
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_review_navigation import saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser

from skatmind.app_web.learning_frontend import build_unified_learning_state_v1
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.corpus_web.downloads import LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS

CANONICAL = (
    "player_catalog", "human_evidence", "strategy_teacher_evidence", "learning_dataset_v2",
    "known_player_partitions", "unseen_player_partitions", "cross_game_summary",
    "tactical_motif_evidence", "tactical_motif_cross_game_summary", "tactical_cross_game_coaching",
)
GROUPS = (
    ("Summaries and review focuses", (
        "cross_game_summary", "tactical_motif_cross_game_summary", "tactical_cross_game_coaching")),
    ("Underlying evidence", (
        "player_catalog", "human_evidence", "strategy_teacher_evidence",
        "tactical_motif_evidence")),
    ("Dataset and partitioning", (
        "learning_dataset_v2", "known_player_partitions", "unseen_player_partitions")),
)
# Field ownership, independent of the rendering helper. No full Report enters HTML.
NORMAL_COUNTS = {
    "cross_game_match_count", "observed_decision_count", "record_count", "skipped_decision_count",
    "commentary_evidence_count", "response_evidence_count", "strategy_teacher_evidence_count",
    "tactical_evidence_count", "tactical_skipped_decision_count", "tactical_motif_occurrence_count",
    "tactical_coaching_focus_area_count", "tactical_coaching_player_with_focus_count",
}
TECHNICAL = {
    "dataset_id", "dataset_status", "known_player", "unseen_player", "cross_game_player_count",
    "tactical_collection_status", "tactical_cross_game_player_count",
    "tactical_cross_game_recurrence_count", "tactical_coaching_status",
    "tactical_coaching_decision_count", "tactical_coaching_teacher_assessment_count",
    "players", "player_count", "platform_alias_conflict_count",
}


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def specimen(**changes):
    """Supplementary minimized scalar state, never a fabricated successful operation."""
    prepared = dict.fromkeys(NORMAL_COUNTS, 0)
    prepared.update(dataset_status="partial", observed_decision_count=3, record_count=1,
        skipped_decision_count=2, cross_game_match_count=1, cross_game_player_count=3,
        tactical_collection_status="partial", tactical_evidence_count=1,
        tactical_skipped_decision_count=2, tactical_motif_occurrence_count=4,
        tactical_coaching_status="insufficient_evidence", tactical_coaching_decision_count=1,
        tactical_coaching_teacher_assessment_count=0,
        known_player={"status": "unavailable", "unavailable_reason": "missing_match_played_at"},
        unseen_player={"status": "unavailable",
                       "unavailable_reason": "insufficient_player_components"})
    prepared.update(changes)
    return {"corpus": {"catalog_revision": 1, "corpus_id": "synthetic"},
            "matches": [], "current_match_snapshots": [], "strategy_sources": [],
            "prepared": prepared}


def rendered(state, locale="en"):
    before = deepcopy(state)
    page = render_task_first_learning_v1(state, managed_handle="a" * 64, locale=locale)
    assert state == before
    tree = Hierarchy(page)
    return tree, tree.by_id("learning-results")["text"]


def assert_downloads(tree, locale="en"):
    links = tree.within("learning-results", "a")
    expected = [kind for _, kinds in GROUPS for kind in kinds]
    assert [n["attrs"]["href"] for n in links] == [
        f'/learning/downloads/{kind.replace("_", "-")}.json' for kind in expected]
    assert LEARNING_CORPUS_ALL_PREPARED_DOWNLOAD_KINDS == CANONICAL
    for link in links:
        assert "download" in link["attrs"] and "autofocus" not in link["attrs"]
        assert Hierarchy.visible(link) and len(link["text"]) > 10 and "JSON" in link["text"]
        item = next(p for p in reversed(link["parents"]) if p["tag"] == "li")
        assert len(item["text"]) > len(link["text"]) + 25
    if locale == "en":
        assert [n["text"] for n in tree.within("learning-results", "h4")] == [
            title for title, _ in GROUPS]


def test_genuine_partial_preparation_explains_units_and_preserves_downloads(localized_server):
    browser = Browser(localized_server)
    path, _ = saved_partial_match(localized_server)
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[1]["location"] == "/learning/current#learning-results"
    page = follow(browser, response)
    active = localized_server.app_context.managed_stateful.active_learning
    state = build_unified_learning_state_v1(active)
    assert set(state["prepared"]) == NORMAL_COUNTS | TECHNICAL
    assert (state["prepared"]["observed_decision_count"], state["prepared"]["record_count"],
            state["prepared"]["skipped_decision_count"]) == (6, 2, 4)
    text = Hierarchy(page).by_id("learning-results")["text"]
    assert "Recorded decisions: 6." in text
    assert "Included with a reconstructed before-Card state: 2." in text
    assert "Without such a state (skipped): 4." in text
    assert "Strategy Teacher evidence included in this Dataset: 0." in text
    assert "does not automatically include every previously executed Report" in text
    assert "No qualifying review focus" in text
    assert_downloads(Hierarchy(page))
    retained = downloads(browser)
    for locale in ("en", "de"):
        tree, _ = rendered(state, locale)
        assert_downloads(tree, locale)
    assert downloads(browser) == retained


@pytest.mark.parametrize(("kind", "counts", "sentence"), (
    ("empty", (0, 0, 0), "No recorded decisions in this Dataset."),
    ("unavailable", (6, 0, 6), "All recorded decisions lack a safe Dataset Record."),
    ("complete", (1, 1, 0), "Every recorded decision has a safe Dataset Record."),
))
def test_genuine_empty_all_skipped_and_complete_coverage_partial_match(
    localized_server, kind, counts, sentence,
):
    from test_match_workspace_contracts import _observed_game, _set_game

    from skatmind.match_workspace_contracts import create_match_workspace_v1
    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    browser = Browser(localized_server)
    path, workspace = saved_partial_match(localized_server)
    game = workspace.slots[2].observed_game
    target = create_match_workspace_v1(workspace.match_definition)
    if kind != "empty":
        target = _set_game(target, _observed_game(workspace.match_definition, match_position=3,
            perspective_initial_hand=(None if kind == "unavailable"
                                      else game.perspective_initial_hand),
            declarer_player_id=game.declarer_player_id, declaration=game.declaration,
            original_skat=game.original_skat, discarded_cards=game.discarded_cards,
            plays=game.plays if kind == "unavailable" else game.plays[:1]))
    assert save_match_workspace_file_v1(path,
        build_match_workspace_persistence_document_v1(target),
        expected_content_fingerprint=build_match_workspace_persistence_document_v1(workspace)
            .content_fingerprint).status == "saved"
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))
    active = localized_server.app_context.managed_stateful.active_learning
    state = build_unified_learning_state_v1(active)["prepared"]
    assert state["dataset_status"] == kind
    assert tuple(state[k] for k in (
        "observed_decision_count", "record_count", "skipped_decision_count")) == counts
    assert state["known_player"]["status"] == state["unseen_player"]["status"] == "unavailable"
    text = Hierarchy(page).by_id("learning-results")["text"]
    assert sentence in text
    assert_downloads(Hierarchy(page))
    downloads(browser)


@pytest.mark.parametrize(("status", "counts", "sentence"), (
    ("empty", (0, 0, 0), "No recorded decisions in this Dataset."),
    ("unavailable", (3, 0, 3), "All recorded decisions lack a safe Dataset Record."),
    ("partial", (3, 1, 2), "Some recorded decisions lack a safe Dataset Record."),
    ("complete", (3, 3, 0), "Every recorded decision has a safe Dataset Record."),
))
def test_dataset_literal_coverage_is_not_game_completion(status, counts, sentence):
    tree, text = rendered(specimen(dataset_status=status, observed_decision_count=counts[0],
        record_count=counts[1], skipped_decision_count=counts[2]))
    assert sentence in text
    assert "not completion of every Game or model training" in text
    assert "Commentary included in this Dataset: 0; linked responses included: 0." in text
    assert "Optional evidence can be absent without a failed evaluation." in text
    assert "Tactical decisions with reconstructed observations: 1; skipped: 2." in text
    assert "Motif occurrences: 4." in text
    assert "Several motifs can occur in one decision" in text
    assert_downloads(tree)


@pytest.mark.parametrize(("status", "decisions", "focus", "players", "sentence"), (
    ("empty", 0, 0, 0, "No Tactical Decision summaries are available for review focuses."),
    ("insufficient_evidence", 1, 0, 0, "No qualifying review focus from this report's evidence."),
    ("available", 4, 2, 1, "Qualified review focuses are present."),
))
def test_coaching_literal_states_not_error_free_play(status, decisions, focus, players, sentence):
    _, text = rendered(specimen(tactical_coaching_status=status,
        tactical_coaching_decision_count=decisions, tactical_coaching_focus_area_count=focus,
        tactical_coaching_player_with_focus_count=players))
    assert sentence in text
    assert (f"Retained Player–motif review focuses: {focus}. "
            f"Players with a focus: {players}.") in text
    assert "not a verdict on mistakes or Player weakness" in text
    assert "Immediate-only assessments do not establish a review focus" in text


@pytest.mark.parametrize("status", ("complete", "unavailable"))
def test_partition_modes_have_separate_status_and_settings_are_not_membership(status):
    tree, text = rendered(specimen(known_player={"status": status, "unavailable_reason": None},
        unseen_player={"status": "unavailable", "unavailable_reason": "insufficient_components"}))
    assert ("Known-player split: available." if status == "complete"
            else "Known-player split: unavailable for this preparation.") in text
    assert "Unseen-player split: unavailable for this preparation." in text
    assert "An unavailable split does not invalidate this evaluation or its downloads." in text
    assert "Neither mode refers to the current Settings directory" in text
    assert_downloads(tree)


@pytest.mark.parametrize("bad", (None, True, False, -1, "3", 1.5, [], {}))
def test_defensive_metadata_is_unavailable_not_zero_or_a_repaired_status(bad):
    _, text = rendered(specimen(record_count=bad))
    assert "Included with a reconstructed before-Card state: unavailable." in text
    assert "Coverage interpretation unavailable" in text
    assert "Some recorded decisions lack a safe Dataset Record." not in text


def test_contradictory_metadata_preserves_literal_counts_without_combined_claim():
    _, text = rendered(specimen(record_count=8))
    assert "Included with a reconstructed before-Card state: 8." in text
    assert "Coverage interpretation unavailable" in text


def test_unprepared_has_no_fabricated_summary_or_downloads():
    state = specimen()
    state["prepared"] = None
    tree, text = rendered(state)
    assert not tree.within("learning-results", "a")
    assert "Recorded decisions:" not in text


@pytest.mark.parametrize("field", sorted(NORMAL_COUNTS))
def test_every_normal_counter_distinguishes_missing_and_boolean_from_zero(field):
    for value in (None, False, -2, "0"):
        state = specimen(**{field: value})
        tree, text = rendered(state)
        assert "unavailable" in text
        technical = [n["text"] for n in tree.nodes if n["tag"] == "pre"]
        assert f'"{field}"' in technical[0]  # Invalid raw diagnostic is retained.
    state = specimen()
    del state["prepared"][field]
    _, text = rendered(state)
    assert "unavailable" in text


@pytest.mark.parametrize("status", (None, True, "future_status", [], {}))
def test_unknown_statuses_are_separate_neutral_defensive_metadata(status):
    _, text = rendered(specimen(dataset_status=status, tactical_collection_status=status,
        tactical_coaching_status=status, known_player={"status": status}))
    assert "Coverage interpretation unavailable" in text
    assert "Tactical coverage: interpretation unavailable." in text
    assert "Coaching interpretation unavailable" in text
    assert "Known-player split: status unavailable." in text


def test_all_skipped_tactical_is_partial_not_empty_and_does_not_merge_dataset_counts():
    _, text = rendered(specimen(dataset_status="unavailable", record_count=0,
        skipped_decision_count=3, tactical_evidence_count=0, tactical_skipped_decision_count=3,
        tactical_motif_occurrence_count=0, tactical_coaching_status="empty",
        tactical_coaching_decision_count=0))
    assert "All recorded decisions lack a safe Dataset Record." in text
    assert "Tactical coverage: at least one recorded decision is skipped." in text
    assert "Motif occurrences: 0." in text
    assert "No Tactical Decision summaries are available for review focuses." in text


def test_german_literal_coverage_and_groups_with_optional_evidence():
    tree, text = rendered(specimen(commentary_evidence_count=2, response_evidence_count=1,
        strategy_teacher_evidence_count=4), "de")
    assert "Erfasste Entscheidungen: 3." in text
    assert "Mit rekonstruiertem Zustand vor dem Kartenspiel enthalten: 1." in text
    assert "Ohne solchen Zustand (übersprungen): 2." in text
    assert ("In diesem Datensatz enthaltene Kommentare: 2; "
            "enthaltene verknüpfte Reaktionen: 1.") in text
    assert "In diesem Datensatz enthaltene Analysebelege (Strategy Teacher): 4." in text
    assert [n["text"].replace("\u00ad", "") for n in tree.within("learning-results", "h4")] == [
        "Zusammenfassungen und Prüfschwerpunkte", "Zugrunde liegende Belege",
        "Datensatz und Aufteilungen"]
    assert_downloads(tree, "de")


def test_secondary_facts_and_exact_status_reasons_remain_once_without_raw_report():
    state = specimen()
    state["prepared"].update(tactical_cross_game_recurrence_count=7,
                             tactical_coaching_teacher_assessment_count=5)
    tree, _ = rendered(state)
    technical = next(n["text"] for n in tree.nodes if n["tag"] == "pre")
    assert '"tactical_cross_game_recurrence_count": 7' in technical
    assert '"tactical_coaching_teacher_assessment_count": 5' in technical
    assert '"unavailable_reason": "missing_match_played_at"' in technical
    assert '"dataset_status": "partial"' in technical
    assert all(f'"{key}"' not in technical for key in NORMAL_COUNTS)
    assert all(name not in technical for name in (
        "guidance_text", "focus_areas", "actual_card_played", "candidate_results"))


def test_available_focus_reuses_bounded_coaching_fixture_without_changing_thresholds(monkeypatch):
    """Supplementary retained-Search fixture, not a genuine Search/browser execution claim."""
    from test_learning_corpus_human_evidence import _store
    from test_learning_corpus_strategy_teacher import _source_bundle
    from test_learning_corpus_tactical_coaching import _below_best_search_result, _report

    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(information_view=information_view,
            requested_budget=requested_budget, random_seed=random_seed, expected_seed=9,
            below_best_cards=frozenset({"C8"}))

    monkeypatch.setattr("skatmind.recommendation_workflow.solve_compatible_world_minimax", search)
    sources = [_source_bundle(recommendation_method="bounded_search", decision_index=22,
        match_id="result-focus-" + suffix, search_random_seed=9,
        search_budget_profile="interactive_v1") for suffix in ("a", "b")]
    store = _store(*(s[1] for s in sources), current=tuple(s[1] for s in sources))
    report = _report(store, tuple(s[4] for s in sources))
    assert report.status == "available" and report.focus_area_count == 2
    assert report.player_with_focus_count == 1
    _, text = rendered(specimen(tactical_coaching_status=report.status,
        tactical_coaching_decision_count=report.decision_summary_count,
        tactical_coaching_focus_area_count=report.focus_area_count,
        tactical_coaching_player_with_focus_count=report.player_with_focus_count))
    assert "Qualified review focuses are present." in text
    assert "Retained Player–motif review focuses: 2. Players with a focus: 1." in text
    assert "Coaching JSON below contains the retained Player focuses and guidance" in text
    assert "C8" not in text and "player-a" not in text
    assert all(focus.guidance_text not in text for player in report.player_reports
               for focus in player.focus_areas)
