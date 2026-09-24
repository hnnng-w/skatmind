"""Captured presentation specimens; these do not establish Product eligibility."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from test_learning_entry_purpose import specimen
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Forms

from skatmind.app_web.form_parsing import FormValuesV1, FormValueV1
from skatmind.app_web.form_registry import FRONTEND_FORM_REGISTRY
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.app_web.validation_contracts import (
    FrontendSubmittedFormStateV1,
    FrontendValidationIssueV1,
)
from skatmind.app_web.validation_rendering import apply_validation_feedback_to_html_v1

OPERATION = "import_strategy_teacher_report"


def render(state, locale="en", recorded=()):
    return render_task_first_learning_v1(state, managed_handle="a" * 64,
                                        locale=locale, recorded=recorded)


def upload_form(page):
    return next(f for f in Forms(page).forms if f["values"].get("operation") == OPERATION)


def upload_nodes(page):
    nodes = Hierarchy(page).nodes
    marker = next(n for n in nodes if n["attrs"].get("value") == OPERATION)
    form = next(n for n in marker["parents"] if n["tag"] == "form")
    return form, [n for n in nodes if form in n["parents"]]


def variants(state):
    match = state["matches"][0]
    match["snapshots"] = [dict(match["snapshots"][0], match_snapshot_id=identity,
        current=identity == "snapshot") for identity in ("older", "snapshot", "other")]
    return state


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("retained", (1, 3))
def test_single_current_is_readonly_with_one_exact_hidden_target(locale, retained):
    state = specimen("build")
    if retained == 3:
        variants(state)
    page = render(state, locale)
    form, nodes = upload_nodes(page)
    fields = [n for n in nodes if n["attrs"].get("name") == "match_snapshot_id"]
    assert len(fields) == 1 and fields[0]["tag"] == "input"
    assert fields[0]["attrs"]["type"] == "hidden"
    assert fields[0]["attrs"]["value"] == "snapshot"
    assert upload_form(page)["values"] == {"managed_handle": "a" * 64,
        "operation": OPERATION, "match_snapshot_id": "snapshot"}
    assert form["attrs"]["method"] == "post"
    assert form["attrs"]["enctype"] == "multipart/form-data"
    assert form["attrs"]["action"] == "/learning/api/v1/operations"
    label = text(locale, "task.learning.saved_revision", revision=1)
    if retained == 3:
        label = text(locale, "task.learning.version_variant", revision_label=label, number=2)
    assert label in form["text"]
    assert any(n["tag"] == "button" and "disabled" not in n["attrs"] for n in nodes)
    assert any(n["attrs"].get("name") == "report_source_file" and
               n["attrs"].get("type") == "file" and "required" in n["attrs"] for n in nodes)


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("status", ("add", "select"))
def test_zero_targets_have_a_visible_remedy_and_no_upload_action(locale, status):
    state = specimen(status)
    # Defensive orphaned binding: retain removal even with no offered target.
    state["strategy_sources"] = [dict(match_id="match", match_snapshot_id="lost",
        match_position=3, decision_index=2, recommendation_method="immediate_expected_value",
        binding_status="non_current", source_binding_id="b" * 64)]
    page = render(state, locale)
    assert not any(f["values"].get("operation") == OPERATION for f in Forms(page).forms)
    assert 'value="remove_strategy_teacher_report"' in page
    assert 'value="clear_strategy_teacher_reports"' in page
    assert ('href="#insight-versions"' if status == "select" else
            'href="#learning-recorded-matches"') in page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_multiple_targets_distinguish_equal_titles_and_revisions_without_new_values(locale):
    state = variants(specimen("build"))
    other = deepcopy(state["matches"][0])
    other.update(match_id="second", current_match_snapshot_id="second-snapshot")
    other["snapshots"] = [dict(other["snapshots"][0],
        match_snapshot_id="second-snapshot", current=True)]
    state["matches"].append(other)
    state["current_match_snapshots"].append(dict(
        match_id="second", match_snapshot_id="second-snapshot"))
    recorded = tuple(SimpleNamespace(semantic_product_id=identity, display_label='Same <title>',
        status="available", handle=str(i) * 64, revision=1)
        for i, identity in enumerate(("match", "second"), 1))
    page = render(state, locale, recorded)
    _, nodes = upload_nodes(page)
    fields = [n for n in nodes if n["attrs"].get("name") == "match_snapshot_id"]
    assert len(fields) == 1 and fields[0]["tag"] == "select"
    options = [n for n in nodes if n["tag"] == "option"]
    assert [n["attrs"]["value"] for n in options] == ["snapshot", "second-snapshot"]
    assert len({n["text"] for n in options}) == 2
    assert all("Same <title>" in n["text"] for n in options)
    described = next(n for n in nodes if n["attrs"].get("id") == "learning-report-targets")
    assert "learning-report-targets" in fields[0]["attrs"]["aria-describedby"].split()
    assert all(option["text"] in described["text"] for option in options)
    assert text(locale, "task.learning.version_variant",
                revision_label=text(locale, "task.learning.saved_revision", revision=1),
                number=2) in options[0]["text"]
    assert 'Same <title>' not in page and 'Same &lt;title&gt;' in page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_attached_noncurrent_label_uses_bound_variant_not_current(locale):
    state = variants(specimen("build"))
    state["strategy_sources"] = [dict(match_id="match", match_snapshot_id="older",
        match_position=3, decision_index=2, recommendation_method="immediate_expected_value",
        binding_status="non_current", source_binding_id="b" * 64)]
    tree = Hierarchy(render(state, locale))
    source = next(n for n in tree.nodes if n["attrs"].get("class") == "learning-attached-source")
    bound = text(locale, "task.learning.version_variant",
                 revision_label=text(locale, "task.learning.saved_revision", revision=1), number=1)
    assert bound in source["text"]
    assert text(locale, "task.learning.binding.non_current") in source["text"]
    assert text(locale, "task.field.decision_index") in source["text"]
    assert not any(n["tag"] == "select" for n in tree.nodes if source in n["parents"])
    assert any(n["attrs"].get("href") == "#insight-versions"
               for n in tree.nodes if source in n["parents"])


def test_optional_source_help_names_wrapper_effect_and_lifetime():
    page = render(specimen("build"))
    assert "Attach an existing decision-analysis Report" in page
    assert "Check and attach Report" in page and "Report source (JSON)" in page
    assert "-strategy-source.json" in page and "Download for Learning Corpus" in page
    assert "Request, Result or recording JSON" in page
    assert "restart" in page and "Reload" in page
    assert "not evaluate the collection" in page


def test_hidden_target_error_links_to_visible_description_and_is_not_restored():
    definition = next(d for d in FRONTEND_FORM_REGISTRY
                      if d.form_key == "learning.operation." + OPERATION)
    state = FrontendSubmittedFormStateV1(contract_version=1, form_key=definition.form_key,
        originating_route=definition.action_route, active_family_binding="learning",
        review_wizard_step=None, form_instance=None,
        safe_visible_values=FormValuesV1((FormValueV1("match_snapshot_id", ("rejected",)),)),
        validation_issues=(FrontendValidationIssueV1(field_key="match_snapshot_id",
            message_key="validation.message.choice"),), status="invalid", feedback_generation=1)
    page = apply_validation_feedback_to_html_v1(
        render(specimen("build")), definition, state, locale="en")
    assert upload_form(page)["values"]["match_snapshot_id"] == "snapshot"
    tree = Hierarchy(page)
    summary = next(n for n in tree.nodes if n["attrs"].get("class") == "error-summary")
    link = next(n for n in tree.nodes if n["tag"] == "a" and summary in n["parents"])
    target = next(n for n in tree.nodes if n["attrs"].get("id") == link["attrs"]["href"][1:])
    assert target["tag"] != "input" and target["attrs"].get("tabindex") == "-1"
    assert "not accepted" in page and "Try again" in page


def test_defensive_duplicate_offered_identity_counts_once_and_missing_metadata_is_not_offered():
    state = specimen("build")
    state["current_match_snapshots"] *= 2
    state["current_match_snapshots"].append(dict(match_id="unknown", match_snapshot_id="unknown"))
    _, nodes = upload_nodes(render(state))
    controls = [n for n in nodes if n["attrs"].get("name") == "match_snapshot_id"]
    assert len(controls) == 1 and controls[0]["attrs"]["type"] == "hidden"
    assert controls[0]["attrs"]["value"] == "snapshot"


def test_no_target_feedback_stays_visible_and_language_excludes_hidden_transport_and_files():
    from skatmind.app_web.language_form_preservation import instrument_language_forms_v1

    html, manifest = instrument_language_forms_v1(render(specimen("build")))
    # Every offered field is hidden or a file; none is editable language state.
    _, nodes = upload_nodes(html)
    assert not any(n["tag"] == "select" for n in nodes)
    assert not any(f.field_key in {"match_snapshot_id", "report_source_file"}
                   for form in manifest.forms for f in form.fields)
    definition = next(d for d in FRONTEND_FORM_REGISTRY
                      if d.form_key == "learning.operation." + OPERATION)
    state = FrontendSubmittedFormStateV1(contract_version=1, form_key=definition.form_key,
        originating_route=definition.action_route, active_family_binding="learning",
        review_wizard_step=None, form_instance=None, safe_visible_values=FormValuesV1(),
        validation_issues=(FrontendValidationIssueV1(field_key="report_source_file",
            message_key="validation.message.file_reselection"),),
        status="invalid", feedback_generation=1)
    page = apply_validation_feedback_to_html_v1(
        render(specimen("add")), definition, state, locale="en")
    tree = Hierarchy(page)
    summary = next(n for n in tree.nodes if n["attrs"].get("class") == "error-summary")
    assert all("open" in n["attrs"] for n in summary["parents"] if n["tag"] == "details")
    assert 'href="#learning-report-target"' in page
    assert text("en", "validation.message.file_reselection") in page
