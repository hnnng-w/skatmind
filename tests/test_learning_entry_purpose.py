"""Presentation specimens are not evidence of successful Corpus operations."""

from html import escape

import pytest
from test_match_recording_recovery_web import operation_form

from skatmind.app_web.entry_rendering import render_entry_introduction_v1
from skatmind.app_web.friendly_creation_rendering import render_profile_driven_learning_creation_v1
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as t


def specimen(status):
    snapshot = {"match_snapshot_id": "snapshot", "current": True, "workspace_revision": 1,
                "observed_game_count": 1, "decision_count": 3}
    match = {"match_id": "match", "current_match_snapshot_id": "snapshot", "snapshots": [snapshot]}
    state = {"corpus": {"corpus_id": "collection", "catalog_revision": 1},
             "matches": [] if status == "add" else [match],
             "current_match_snapshots": [] if status == "add" else [
                 {"match_snapshot_id": "snapshot", "match_id": "match"}],
             "strategy_sources": [], "prepared": None}
    if status == "select":
        match["current_match_snapshot_id"] = None
        snapshot["current"] = False
        state["current_match_snapshots"] = []
    if status == "sources":
        state["strategy_sources"] = [{"binding_status": "non_current", "match_id": "match",
            "match_position": 1, "decision_index": 1, "recommendation_method": "immediate",
            "source_binding_id": "binding"}]
    return state


def test_learning_entry_explains_present_operation_instead_of_model_adaptation():
    purpose = t("en", "entry.learning")
    assert "saved Match versions" in purpose
    assert "summaries" in purpose and "does not train a model" in purpose
    assert "future Card recommendations" in purpose
    assert len(purpose.split()) < 65
    add = t("en", "task.learning.recorded_help")
    assert "first version" in add and "later version" in add
    assert "partial" in add and "Reports" in add and "later edits" in add


@pytest.mark.parametrize("locale", ("de", "en"))
def test_name_only_creation_has_visible_purpose_and_empty_creation_help(locale):
    introduction = render_entry_introduction_v1("/learning", locale)
    creation = render_profile_driven_learning_creation_v1(profile_generation=0, locale=locale)
    assert escape(t(locale, "entry.learning")) in introduction
    assert escape(t(locale, "creation.learning.help")) in creation
    assert 'name="collection_name" maxlength="160" required' in creation
    assert creation.count('<form ') == 1 and 'action="/learning/create"' in creation
    assert 'prepare_learning_artifacts' not in creation and 'source_handle' not in creation


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("status", ("add", "select", "sources", "build"))
def test_action_local_guidance_preserves_blockers_and_native_controls(locale, status):
    html = render_task_first_learning_v1(specimen(status), managed_handle="a" * 64,
                                       locale=locale, learning_selection="b" * 64)
    assert '<h2>' + t(locale, "task.learning.next") + '</h2>' not in html
    assert 'href="#learning-recorded-matches"' not in html
    assert t(locale, "concept.learning.automatic") not in html
    assert html.count(t(locale, "task.learning.recorded_help")) == 1
    assert 'id="learning-recorded-matches" tabindex="-1"' in html
    assert '<!-- entry-operation-feedback -->' in html and '<!-- operation-feedback -->' in html
    assert 'id="learning-build" tabindex="-1"' in html
    assert 'id="learning-results" tabindex="-1"' in html
    assert 'action="/learning/add-recorded-match"' in html
    assert ('value="prepare_learning_artifacts"' in html) == (status == "build")
    if status == "select":
        assert 'href="#insight-versions"' in html and 'value="select_current_snapshot"' in html
    if status == "sources":
        assert 'href="#learning-sources"' in html
        assert html.index('id="learning-sources"') < html.rindex('<details ')
    if status == "build":
        assert t(locale, "task.learning.build_help") in html
        values = operation_form(html, "prepare_learning_artifacts")["values"]
        for name, value in (("dataset_id", "collection-learning-dataset-v2"),
                            ("known_player_seed", "0"), ("unseen_player_seed", "0"),
                            ("train_weight", "70"), ("validation_weight", "15"),
                            ("test_weight", "15")):
            assert values[name] == value
