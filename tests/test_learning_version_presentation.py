"""Captured display specimens; missing Current is defensive, never persisted here."""

from copy import deepcopy
from html import escape

import pytest
from test_learning_entry_purpose import specimen
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Forms

from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


def render(state, locale="en"):
    return render_task_first_learning_v1(state, managed_handle="a" * 64, locale=locale,
                                        learning_selection="b" * 64)


def selections(page):
    return [f for f in Forms(page).forms
            if f["values"].get("operation") == "select_current_snapshot"]


@pytest.mark.parametrize("locale", ("de", "en"))
def test_current_singleton_has_no_empty_alternatives_or_selection(locale):
    page = render(specimen("build"), locale)
    assert not selections(page)
    assert text(locale, "task.learning.alternatives") not in page
    assert ("Selected for evaluation" if locale == "en" else
            "Für die Auswertung ausgewählt") in page
    assert 'id="learning-match-' in page and 'id="learning-version-' in page


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("status", ("add", "select", "sources"))
def test_absence_missing_current_and_teacher_blocker_are_independent(locale, status):
    page = render(specimen(status), locale)
    assert len(selections(page)) == (1 if status == "select" else 0)
    if status == "select":
        assert text(locale, "task.learning.missing_selection") in page
        assert 'value="snapshot"' in page
    if status == "sources":
        assert 'href="#learning-sources"' in page
        assert 'value="remove_strategy_teacher_report"' in page
        assert 'value="prepare_learning_artifacts"' not in page
    assert text(locale, "task.learning.alternatives") not in page


@pytest.mark.parametrize("locale,labels", (
    ("en", ("Saved recording revision 8 — variant 1", "Saved recording revision 8 — variant 2",
            "Saved recording revision 8 — variant 3", "Saved recording revision 2")),
    ("de", ("Gespeicherte Aufzeichnungsrevision 8 — Variante 1",
            "Gespeicherte Aufzeichnungsrevision 8 — Variante 2",
            "Gespeicherte Aufzeichnungsrevision 8 — Variante 3",
            "Gespeicherte Aufzeichnungsrevision 2")),
))
def test_equal_progress_variants_and_older_choice_have_exact_identity(locale, labels):
    state = specimen("build")
    first = state["matches"][0]
    identities = (("one", 8), ("two", 8), ("three", 8), ("old", 2))
    first["snapshots"] = [dict(first["snapshots"][0], match_snapshot_id=identity,
        workspace_revision=revision, current=index == 0)
        for index, (identity, revision) in enumerate(identities)]
    other = deepcopy(first)
    other["match_id"] = "other"
    other["snapshots"] = [dict(other["snapshots"][0], match_snapshot_id="other-one")]
    state["matches"].append(other)
    page = render(state, locale)
    forms = selections(page)
    assert [f["values"]["match_snapshot_id"] for f in forms] == ["two", "three", "old"]
    assert all(f["values"]["match_id"] == "match" for f in forms)
    assert all(set(f["values"]) == {"managed_handle", "operation", "expected_catalog_revision",
                                    "match_id", "match_snapshot_id"} for f in forms)
    assert all(label in page for label in labels)
    disclosures = [n for n in Hierarchy(page).nodes if n["tag"] == "details"
                   and text(locale, "task.learning.alternatives") in n["text"]]
    assert len(disclosures) == 1
    assert any(n["attrs"].get("id", "").startswith("learning-match-")
               for n in disclosures[0]["parents"])
    for form, label in zip(forms, labels[1:], strict=True):
        node = next(n for n in Hierarchy(page).nodes if n["tag"] == "form"
                    and any(c["attrs"].get("value") == form["values"]["match_snapshot_id"]
                            for c in Hierarchy(page).nodes if n in c["parents"]))
        button = next(n for n in Hierarchy(page).nodes
                      if n["tag"] == "button" and node in n["parents"])
        ids = button["attrs"]["aria-labelledby"].split()
        name = " ".join(next(n["text"] for n in Hierarchy(page).nodes if n["attrs"].get("id") == i)
                        for i in ids)
        assert label in name


@pytest.mark.parametrize("locale,reject,retain", (
    ("en", "Do not add the conflicting version", "Keep as a separate saved version"),
    ("de", "Abweichende Version nicht hinzufügen", "Als zusätzliche gespeicherte Version behalten"),
))
def test_policy_labels_default_and_associated_full_explanation(locale, reject, retain):
    page = render(specimen("build"), locale)
    forms = Forms(page)
    add = forms.find("/learning/add-recorded-match")
    assert add["values"]["same_revision_resolution"] == "reject"
    assert "selection_mode" not in add["values"]
    upload = next(f for f in forms.forms
                  if f["values"].get("operation") == "import_match_workspace")
    assert upload["values"]["selection_mode"] == "select_imported"
    nodes = Hierarchy(page).nodes
    for select in (n for n in nodes if n["tag"] == "select"
                   and n["attrs"].get("name") == "same_revision_resolution"):
        options = [n for n in nodes if n["tag"] == "option" and select in n["parents"]]
        assert [(n["attrs"]["value"], n["text"]) for n in options] == [
            ("reject", reject), ("retain", retain)]
        description = next(n for n in nodes
                           if n["attrs"].get("id") == select["attrs"]["aria-describedby"])
        assert reject in description["text"] and retain in description["text"]


def test_fallback_and_supplied_label_escaping():
    from types import SimpleNamespace

    state = specimen("build")
    label = '<Synthetic & "same">'
    recorded = (SimpleNamespace(semantic_product_id="match", display_label=label,
                                status="available", handle="c" * 64, revision=1),)
    page = render_task_first_learning_v1(state, managed_handle="a" * 64, recorded=recorded)
    assert escape(label) in page and label not in page
    assert "Recorded Match" in render(state)
