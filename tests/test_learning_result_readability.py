"""Delivered compact results over genuine preparation and explicitly controlled Search evidence."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_learning_direct_entry_web import add_form, create_collection, downloads, source_handle
from test_learning_report_attachment import upload_form
from test_learning_report_attachment_web import submit_upload
from test_match_recording_recovery_web import follow, operation_form
from test_match_rollout_web import open_alex
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms

from skatmind.app_web.learning_frontend import build_unified_learning_state_v1
from skatmind.app_web.stateful_localization import text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def one_item_result(server):
    """Real Immediate execution, source attachment and 30/30/0 Dataset preparation."""
    browser, path, page = open_alex(server, count=30)
    page = follow(browser, browser.submit(operation_form(page, "analyze_decision"),
                                          immediate_sample_count="2"))
    report, = server.app_context.managed_stateful.active_match.capture.report_store.list()
    status, _, source = browser.request("GET",
        f"/matches/api/v1/reports/{report.report_id}/strategy-source.json")
    assert status == 200
    create_collection(browser)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    page = follow(browser, submit_upload(browser, upload_form(page), source))
    response = browser.submit(operation_form(page, "prepare_learning_artifacts"))
    assert response[0] == 303
    return browser, follow(browser, response), source


@pytest.mark.parametrize("locale", ("en", "de"))
def test_actual_one_item_result_is_compact_and_distinguishes_units(localized_server, locale):
    browser, page, _ = one_item_result(localized_server)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    active = localized_server.app_context.managed_stateful.active_learning
    state = build_unified_learning_state_v1(active)["prepared"]
    assert tuple(state[key] for key in ("cross_game_match_count", "observed_decision_count",
        "record_count", "skipped_decision_count", "strategy_teacher_evidence_count")) == (
            1, 30, 30, 0, 1)
    tree = Hierarchy(page)
    assert tree.by_id("learning-results")["text"] == (
        "Learning review" if locale == "en" else "Lernauswertung")
    technical = tree.by_id("learning-result-technical")
    included = tree.by_id("learning-result-inputs")
    assert technical["tag"] == included["tag"] == "details"
    assert "open" not in technical["attrs"] and "open" not in included["attrs"]
    links = [n for n in tree.nodes if n["tag"] == "a"
             and n["attrs"].get("href", "").startswith("/learning/downloads/")]
    assert len(links) == 10
    assert all(technical in n["parents"] and not Hierarchy.visible(n) for n in links)
    primary = tree.by_id("learning-result-primary")["text"]
    assert len(primary) < 1000
    assert "1 of 30" not in primary and "1 von 30" not in primary
    assert "/review/recorded" in [n["attrs"].get("href")
        for n in tree.within("learning-result-primary", "a")]
    assert "learning-debrief" not in page  # No fabricated whole-game comparison from attachment.
    assert text(locale, "learning.result.explanation.one_decision") in primary
    assert "Game 2" in included["text"] if locale == "en" else "Spiel 2" in included["text"]
    index = active.corpus.strategy_source_store.sources[0].report.decision_index
    assert (f"Decision {index}" if locale == "en" else f"Entscheidung {index}") in included["text"]
    assert "Normalized analysis-evidence items included in this Dataset: 1." in technical["text"] \
        if locale == "en" else "normalisierte Analysebelege: 1." in technical["text"]
    assert len(downloads(browser)) == 10


def controlled_focus_bundles(monkeypatch):
    """Accepted deterministic retained-Search specimens, NOT executed real Search."""
    from test_learning_corpus_strategy_teacher import _source_bundle
    from test_learning_corpus_tactical_coaching import _below_best_search_result
    from test_match_workspace_contracts import _complete_observed_game, _definition, _set_game

    from skatmind.match_workspace_contracts import create_match_workspace_v1

    def search(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(information_view=information_view,
            requested_budget=requested_budget, random_seed=random_seed, expected_seed=9,
            below_best_cards=frozenset({"C8", "HQ"}))

    monkeypatch.setattr("skatmind.recommendation_workflow.solve_compatible_world_minimax", search)
    bundles = []
    for suffix in ("a", "b"):
        definition = _definition(match_id="readability-" + suffix,
            title='Same <Match> & ' + 'LongName' * 18)
        # Rotate table places so the historical fixture's exact seats are valid at Game 1.
        players = tuple(replace(p, player_label='Same <Player> & name', table_place=place)
            for p, place in zip(definition.participants, ("place_2", "place_3", "place_1"),
                                strict=True))
        definition = replace(definition, participants=tuple(sorted(players,
                                                                  key=lambda p: p.table_place)))
        workspace = _set_game(create_match_workspace_v1(definition),
                               _complete_observed_game(definition, match_position=1))
        for index in (22, 23):
            bundles.append(_source_bundle(workspace=workspace, match_position=1,
                decision_index=index, recommendation_method="bounded_search",
                search_random_seed=9, search_budget_profile="interactive_v1"))
    return bundles


def include_bundles(browser, bundles, *, variants=False):
    """Real Workspace/source import and preparation; no prepared-object injection."""
    from skatmind.app_web.learning_frontend import (
        import_report_source_into_unified_learning_v1,
        import_workspace_bytes_into_unified_learning_v1,
    )
    from skatmind.match_workspace_contracts import _build_match_workspace_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    create_collection(browser)
    active = browser.server.app_context.managed_stateful.active_learning
    seen = set()
    def add(workspace):
        return import_workspace_bytes_into_unified_learning_v1(active,
            json.dumps(build_match_workspace_persistence_document_v1(workspace).to_dict()).encode(),
            selection_mode="keep_current", same_revision_resolution="retain",
            expected_catalog_revision=active.corpus.store.document.catalog.revision)
    for workspace, snapshot, _result, _report, source, _store in bundles:
        if snapshot.match_snapshot_id not in seen:
            assert add(workspace).status == "applied"
            if variants:
                alternative = _build_match_workspace_v1(match_definition=replace(
                    workspace.match_definition, external_match_id="alternative"),
                    revision=workspace.revision, slots=workspace.slots)
                assert add(alternative).status == "applied"
            seen.add(snapshot.match_snapshot_id)
        assert import_report_source_into_unified_learning_v1(active, source).status in (
            "applied", "unchanged")
    page = browser.page("/learning/current")
    return follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))


@pytest.mark.parametrize("locale", ("en", "de"))
def test_retained_focus_order_exact_references_and_shared_debrief(localized_server, monkeypatch,
                                                               locale):
    from skatmind.app_web.debrief_frontend import collection_scope
    from skatmind.app_web.debrief_rendering import render_debrief
    from skatmind.app_web.learning_result_projection import project_learning_result
    from skatmind.corpus_web.downloads import require_learning_corpus_prepared_bundle_v1

    bundles = controlled_focus_bundles(monkeypatch)
    browser = Browser(localized_server)
    page = include_bundles(browser, bundles, variants=True)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    active = localized_server.app_context.managed_stateful.active_learning
    scope = collection_scope(localized_server.app_context, active)
    with active.corpus.lock:
        bundle = require_learning_corpus_prepared_bundle_v1(active.corpus)
        report = bundle[2].tactical_cross_game_coaching_report
        display = project_learning_result(bundle, scope.snapshots,
            build_unified_learning_state_v1(active), locale,
            recorded=tuple(SimpleNamespace(semantic_product_id=s.match_id,
                display_label="Later recording title") for s in scope.snapshots))
    assert all("Later recording title" not in caption for caption in display.sources)
    assert all("Same <Match>" in caption for caption in display.sources)
    assert report.status == "available" and report.player_with_focus_count == 2
    expected = [focus for player in report.player_reports for focus in player.focus_areas]
    assert [f.guidance for f in display.focuses] == [text(locale,
        "debrief.guidance." + f.guidance_code) for f in expected]
    tree = Hierarchy(page)
    articles = [n for n in tree.nodes if n["attrs"].get("class") ==
                "debrief-decision learning-focus"]
    assert len(articles) == len(expected)
    assert len({f.player for f in display.focuses}) == 2  # Identical names remain distinct.
    for node, focus, retained in zip(articles, display.focuses, expected, strict=True):
        assert focus.guidance in node["text"]
        assert len(focus.references) == retained.qualifying_decision_count == 2
        assert len(set(focus.references)) == 2  # Game 1 in two identically named Matches.
        for caption in focus.references:
            assert caption in node["text"] and "variant" in caption.lower()
        details = [n for n in tree.nodes if n["tag"] == "details" and node in n["parents"]]
        assert len(details) == 1 and "open" not in details[0]["attrs"]
    assert "<Player>" not in page and "&lt;Player&gt;" in page
    assert "<Match>" not in page and "&lt;Match&gt;" in page
    assert "learning-debrief" not in page
    assert not active.debrief_sources.sources  # Imported Decision Reports are a separate family.
    filtered = render_debrief(scope, locale,
        selector=str(scope.players.index(expected[0].player_id)))
    assert filtered.count('class="debrief-decision learning-focus"') == sum(
        f.player_id == expected[0].player_id for f in expected)
    assert all(key not in str(build_unified_learning_state_v1(active)) for key in (
        "focus_areas", "teacher_covered_decision_count", "guidance_text", "decision_summaries"))
    assert all(key not in page for key in (
        "candidate_results", "teacher_semantic_fingerprint", "local_remaining_hand"))
    if locale == "en":
        from test_learning_prepared_navigation import view_link
        from test_match_debrief import evidence

        comparison = evidence(bundles[0][0], position=1, decision=22)
        # Explicit fixture incorporation is separate from imported Decision evidence.
        assert active.debrief_sources.add(comparison) == "applied"
        page = browser.page(view_link(browser.page("/learning/current")))
        assert 'id="learning-debrief"' in page and "View comparison" in page
        assert page.count('class="debrief-decision learning-focus"') == len(expected)


def test_semantic_duplicates_do_not_become_distinct_decisions(localized_server, monkeypatch):
    from test_learning_corpus_strategy_teacher import _changed_report

    from skatmind.learning_corpus_strategy_teacher import (
        build_learning_corpus_strategy_teacher_report_source_v1,
    )

    first = controlled_focus_bundles(monkeypatch)[0]
    workspace, snapshot, result, _, _, store = first
    changed = result.result.to_dict()["document"]
    changed["bounded_search_result"]["consumed_budget"]["wall_clock_elapsed_ms"] += 1
    report = _changed_report(result, result_document=changed)
    source = build_learning_corpus_strategy_teacher_report_source_v1(
        match_snapshot_id=snapshot.match_snapshot_id, report=report)
    page = include_bundles(Browser(localized_server), (first,
        (workspace, snapshot, result, report, source, store)))
    active = localized_server.app_context.managed_stateful.active_learning
    retained = (active.corpus.tactical_coaching_prepared_artifacts
                .tactical_cross_game_coaching_report)
    assert (retained.teacher_assessment_count, retained.teacher_covered_decision_count,
            retained.semantic_teacher_group_count) == (2, 1, 1)
    assert text("en", "learning.result.explanation.one_decision") in page
    assert "Normalized analysis-evidence items included in this Dataset: 2." in page
    assert page.count("Analysis evidence ") == 2
    assert not retained.focus_areas


@pytest.mark.parametrize("reason", ("no_analysis", "immediate", "limited", "no_recurrence"))
def test_explanation_uses_actual_retained_assessment_scopes(localized_server, monkeypatch, reason):
    from test_learning_corpus_strategy_teacher import _source_bundle

    browser = Browser(localized_server)
    if reason == "no_recurrence":
        bundles = controlled_focus_bundles(monkeypatch)[:2]  # Two players, one Game, no focus.
    else:
        method = "bounded_search" if reason == "limited" else "immediate_expected_value"
        bundles = [_source_bundle(decision_index=i, recommendation_method=method,
            search_random_seed=0 if reason == "limited" else None,
            search_budget_profile="interactive_v1" if reason == "limited"
            else "historical_review_v1") for i in (1, 2)]
    page = include_bundles(browser, bundles)
    if reason == "no_analysis":
        page = follow(browser, browser.submit(operation_form(
            page, "clear_strategy_teacher_reports")))
        page = follow(browser, browser.submit(operation_form(page, "prepare_learning_artifacts")))
    assert text("en", "learning.result.explanation." + reason) in Hierarchy(page).by_id(
        "learning-result-primary")["text"]


def test_mixed_retained_assessments_are_explained_without_new_consensus(
    localized_server, monkeypatch,
):
    from test_learning_corpus_strategy_teacher import _source_bundle
    from test_learning_corpus_tactical_coaching import _below_best_search_result

    bundles = controlled_focus_bundles(monkeypatch)[:2]
    def best(*, information_view, requested_budget, random_seed):
        return _below_best_search_result(information_view=information_view,
            requested_budget=requested_budget, random_seed=random_seed, expected_seed=9,
            below_best_cards=frozenset())
    monkeypatch.setattr("skatmind.recommendation_workflow.solve_compatible_world_minimax", best)
    bundles.append(_source_bundle(workspace=bundles[0][0], match_position=1,
        decision_index=22, recommendation_method="bounded_search", search_random_seed=9,
        search_budget_profile="interactive_v1"))
    page = include_bundles(Browser(localized_server), bundles)
    report = localized_server.app_context.managed_stateful.active_learning.corpus\
        .tactical_coaching_prepared_artifacts.tactical_cross_game_coaching_report
    assert report.mixed_decision_count == 1 and report.focus_area_count == 0
    assert text("en", "learning.result.explanation.mixed") in page


def test_unjoined_explanation_uses_explicit_retained_unjoined_evidence():
    from test_learning_corpus_strategy_teacher import _source_bundle
    from test_learning_corpus_tactical_coaching import (
        _coaching_sources,
        _replace_tactical_evidence_with_skip,
    )

    from skatmind.app_web.learning_result_projection import _explanation
    from skatmind.learning_corpus_tactical_cross_game_coaching import (
        build_learning_corpus_tactical_cross_game_coaching_report_v1,
    )
    from skatmind.learning_corpus_tactical_motif_summary import (
        build_learning_corpus_tactical_motif_cross_game_summary_v1,
    )

    bundle = _source_bundle(decision_index=2)
    players, teachers, tactical, _ = _coaching_sources(bundle[5], (bundle[4],))
    target = next(e for e in tactical.evidences
                  if e.decision_reference_id == teachers.evidences[0].decision_reference_id)
    tactical = _replace_tactical_evidence_with_skip(tactical, target)
    report = build_learning_corpus_tactical_cross_game_coaching_report_v1(
        player_catalog=players, strategy_teacher_collection=teachers,
        tactical_motif_collection=tactical,
        tactical_motif_cross_game_summary=build_learning_corpus_tactical_motif_cross_game_summary_v1(
            tactical, players))
    assert report.unjoined_teacher_evidence_count == 1
    assert _explanation(report) == "unjoined"


@pytest.mark.parametrize("locale", ("en", "de"))
def test_all_partition_reasons_localized_and_raw_values_preserved(locale):
    from test_learning_result_explanations import rendered, specimen

    from skatmind.learning_dataset_v2_partition_contracts import (
        LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS,
    )

    for reason in LEARNING_DATASET_PARTITION_UNAVAILABLE_REASONS:
        tree, content = rendered(specimen(known_player={
            "status": "unavailable", "unavailable_reason": reason}), locale)
        assert text(locale, "learning.result.partition_reason." + reason) in content
        assert reason in tree.by_id("learning-result-technical")["text"]
        assert reason not in tree.by_id("learning-result-primary")["text"]


@pytest.mark.parametrize("route", ("current", "prepared"))
@pytest.mark.parametrize("change", ("source", "replacement", "catalog"))
def test_projection_never_publishes_with_a_newer_source(
    localized_server, monkeypatch, route, change,
):
    import skatmind.app_web.learning_result_projection as projection

    browser, page, _ = one_item_result(localized_server)
    active = localized_server.app_context.managed_stateful.active_learning
    from test_learning_prepared_navigation import view_link
    path = "/learning/current" if route == "current" else view_link(page)
    real = projection.project_learning_result
    def project(*args, **kwargs):
        display = real(*args, **kwargs)
        if change == "source":
            active.corpus.strategy_source_store.revision += 1
        elif change == "replacement":
            active.corpus.prepared_artifacts = replace(active.corpus.prepared_artifacts)
        else:
            (active.path / "catalog.json").write_bytes(b"{}")
        return display
    monkeypatch.setattr(projection, "project_learning_result", project)
    status, _, body = browser.request("GET", path)
    assert status == 409
    assert b"learning-result-primary" not in body


def test_inconsistent_minimized_metadata_does_not_hide_conflict(localized_server, monkeypatch):
    import skatmind.app_web.server as web

    browser, page, _ = one_item_result(localized_server)
    from test_learning_prepared_navigation import view_link
    real = web.render_task_first_learning_v1
    def render(state, **kwargs):
        state["prepared"]["tactical_coaching_focus_area_count"] = 99
        return real(state, **kwargs)
    monkeypatch.setattr(web, "render_task_first_learning_v1", render)
    tree = Hierarchy(browser.page(view_link(page)))
    primary = tree.by_id("learning-result-primary")["text"]
    assert text("en", "learning.result.coaching.unknown") in primary
    assert text("en", "learning.result.explanation.one_decision") not in primary
    assert "99" in tree.by_id("learning-result-technical")["text"]
