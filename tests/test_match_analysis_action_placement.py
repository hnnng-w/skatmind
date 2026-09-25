"""One native decision action, with its settings retained inside the same form."""

import re
from collections import Counter
from html import escape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_game_navigation import rendered, workspace_for
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_decision_context_web import record_context_match
from test_recorded_review_navigation import chooser_form, home_chooser, saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope

import skatmind.capture_web.analysis as analysis
import skatmind.capture_web.context as capture
import skatmind.match_decision_analysis as decision_analysis
from skatmind.app_web.form_registry import get_frontend_form_by_key_v1
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1 as canonical
from skatmind.app_web.language_form_preservation import instrument_language_forms_v1
from skatmind.app_web.match_review_rendering import render_match_review_v1
from skatmind.app_web.stateful_localization import text
from skatmind.app_web.task_first_rendering import disclosure, form, hidden, input_field
from skatmind.app_web.validation_rendering import instrument_registered_forms_v1
from skatmind.capture_web.analysis import _decision_options
from skatmind.match_analysis_contracts import MatchDecisionAnalysisOptionsV1
from skatmind.match_decision_analysis import build_match_decision_position_request_v1

ADVANCED = (
    "recommendation_method", "immediate_sample_count", "immediate_random_seed",
    "search_random_seed", "search_budget_profile", "use_profile_presets",
)
DEFAULTS = dict(zip(ADVANCED, (
    "immediate_expected_value", "100", "0", "0", "historical_review_v1", "on"), strict=True))
METHODS = ("immediate_expected_value", "bounded_search", "auto", "information_set_search")
BUDGETS = ("historical_review_v1", "interactive_v1")


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def decision_nodes(page):
    nodes = Hierarchy(page).nodes
    operation, = [n for n in nodes if n["attrs"].get("name") == "operation"
                  and n["attrs"].get("value") == "analyze_decision"]
    owner, = [p for p in operation["parents"] if p["tag"] == "form"]
    return owner, [n for n in nodes if any(p is owner for p in n["parents"])]


def assert_decision_form(page, locale, *, indexes, focused, ordered=True):
    owner, nodes = decision_nodes(page)
    assert owner["attrs"]["method"] == "post"
    assert owner["attrs"]["action"] == "/matches/api/v1/analysis"
    assert "enctype" not in owner["attrs"]
    assert not any(n["tag"] == "form" for n in nodes)
    button, = [n for n in nodes if n["tag"] == "button"]
    assert button["attrs"] == {"type": "submit", "class": "primary"}
    assert button["text"] == text(locale, "task.match.action.analyze_decision")
    selector, = [n for n in nodes if n["attrs"].get("name") == "decision_index"]
    advanced, = [n for n in nodes if n["tag"] == "details"]
    assert advanced["attrs"].get("class") == "advanced-settings"
    assert not any(p is advanced for p in selector["parents"] + button["parents"])
    assert not any("autofocus" in n["attrs"]
                   or "tabindex" in n["attrs"] for n in nodes)
    if ordered:
        assert nodes.index(selector) < nodes.index(button) < nodes.index(advanced)
    controls = [n for n in nodes if n["tag"] in {"input", "select", "textarea"}]
    assert Counter(n["attrs"]["name"] for n in controls) == Counter({
        **{key: 1 for key in (*ADVANCED, "decision_index", "managed_handle", "operation",
                             "match_position", "expected_revision", "_frontend_form_instance")},
        **({"review_binding": 1} if focused else {}),
    })
    assert {n["attrs"]["name"] for n in controls
            if any(p is advanced for p in n["parents"])} == set(ADVANCED)
    for name, expected in (("decision_index", indexes), ("recommendation_method", METHODS),
                           ("search_budget_profile", BUDGETS)):
        select, = [n for n in controls if n["attrs"]["name"] == name]
        options = [n for n in nodes if n["tag"] == "option"
                   and any(p is select for p in n["parents"])]
        assert tuple(n["attrs"]["value"] for n in options) == expected
    assert set(owner["attrs"]["data-preserve-fields"].split()) == {*ADVANCED, "decision_index"}
    assert re.fullmatch("[0-9a-f]{64}", owner["attrs"]["data-language-form"])
    return owner, advanced


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("caller", ("recording", "review", "report"))
def test_emitted_callers_group_selection_action_and_settings(localized_server, locale, caller):
    browser = Browser(localized_server)
    page = record_context_match(browser)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                          language=locale))
    if caller == "report":
        page = follow(browser, browser.submit(operation_form(page, "analyze_decision")))
    else:
        page = browser.page("/matches/current" if caller == "recording" else "/matches/review/1")
    owner, advanced = assert_decision_form(page, locale, indexes=("2",),
                                         focused=caller != "recording")
    values = operation_form(page, "analyze_decision")["values"]
    assert {key: values[key] for key in ADVANCED} == DEFAULTS
    assert values["decision_index"] == "2"
    assert values["operation"] == "analyze_decision" and values["match_position"] == "1"
    assert "open" not in advanced["attrs"]
    outer = [p for p in owner["parents"] if p["tag"] == "details"]
    assert len(outer) == (1 if caller == "recording" else 0)
    assert all("open" not in p["attrs"] for p in outer)


@pytest.mark.parametrize("kind", ("empty", "passed", "started", "declaration", 3))
def test_unavailable_branches_have_no_decision_action(kind):
    view, state, recording = rendered(workspace_for((kind,)), 1, "en")
    assert state["decision_preparation"]["prepared_decision_count"] == 0
    review = render_match_review_v1(state, view, managed_handle="a" * 64, locale="en")
    for page in (recording, review):
        assert 'value="analyze_decision"' not in page
    if kind == 3:
        assert text("en", "task.match.decision_blocked") in review
        assert '#match-initial-hand' in review
        assert operation_form(review, "analyze_historical_game")
    else:
        assert 'value="analyze_historical_game"' not in review


@pytest.mark.parametrize("options", ({}, {"primary": True}, {"disabled": True},
    {"multipart": True, "confirm_key": "task.match.remove_note_help",
     "submitter": ('action<&"', 'save<&"')}))
def test_helper_empty_tail_keeps_exact_existing_markup(options):
    fields = hidden("managed_handle", '<&"') + input_field("en", "cards", "task.cards", '<&"')
    expected = ('<form method="post" action="/test" class="form-grid"'
        + (f' data-confirm="{escape(text("en", options["confirm_key"]))}"'
           if options.get("confirm_key") else "")
        + (' enctype="multipart/form-data"' if options.get("multipart") else "") + '>' + fields
        + f'<button type="submit" class="{"primary" if options.get("primary") else "secondary"}"'
        + (f' name="{escape(options["submitter"][0])}" value="{escape(options["submitter"][1])}"'
           if options.get("submitter") else "")
        + (' disabled' if options.get("disabled") else "") + '>Reload</button></form>')
    assert form("en", "/test", fields, "common.action.reload", **options) == expected
    assert form("en", "/test", fields, "common.action.reload",
                trailing_content="", **options) == expected


def test_opt_in_tail_is_instrumented_inside_form_and_stays_escaped():
    definition = get_frontend_form_by_key_v1("match.analysis.analyze_decision")
    tail = disclosure("en", "recordings.match.advanced", input_field(
        "en", "immediate_random_seed", "task.field.immediate_random_seed", '<&"'))
    page = form("en", definition.action_route, hidden("operation", "analyze_decision"),
        "task.match.action.analyze_decision", trailing_content=tail)
    assert page.endswith('</button>' + tail + '</form>')
    assert 'value="&lt;&amp;&quot;"' in page
    page, manifest = instrument_language_forms_v1(
        instrument_registered_forms_v1(page, (definition,)))
    assert len(manifest.forms) == 1 and manifest.disclosure_count == 1
    assert [f.field_key for f in manifest.forms[0].fields] == ["immediate_random_seed"]
    assert 'name="_frontend_form_instance" value="0"' in page


@pytest.mark.parametrize("enhanced", (False, True))
def test_multiple_choices_error_language_recovery_exact_execution_and_stale_source(
    localized_server, monkeypatch, enhanced,
):
    path, workspace = saved_partial_match(localized_server)
    disk = path.read_bytes()
    browser = Browser(localized_server)
    follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    page = browser.page("/matches/review/3")
    active = localized_server.app_context.managed_stateful.active_match
    calls, invocations = [], []
    real = analysis.execute_match_decision_analysis_v1
    execute = decision_analysis.execute_application_invocation
    def counted(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)
    def invocation(value, **kwargs):
        invocations.append(value)
        return execute(value, **kwargs)
    def forbidden(*args, **kwargs):
        pytest.fail("Analysis, invalid input, navigation and language must not save the Match")
    monkeypatch.setattr(analysis, "execute_match_decision_analysis_v1", counted)
    monkeypatch.setattr(decision_analysis, "execute_application_invocation", invocation)
    monkeypatch.setattr(capture, "save_match_workspace_file_v1", forbidden)
    assert_decision_form(page, "en", indexes=("1", "6"), focused=True)
    response = browser.submit(operation_form(page, "analyze_decision"))
    page = follow(browser, response)
    first, = active.capture.report_store.list()
    assert response[1]["location"] == f"/matches/reports/{first.report_id}"
    assert first.value.options == MatchDecisionAnalysisOptionsV1()
    before = canonical(first.to_dict())
    downloads = {route: browser.request("GET", route)[2] for route in re.findall(
        r'href="(/matches/api/v1/reports/[^\"]+)"', page)}
    assert downloads
    submitted = operation_form(page, "analyze_decision")
    submitted["values"].pop("use_profile_presets")
    response = browser.submit(submitted, decision_index="6", immediate_sample_count="-1",
        immediate_random_seed="27", search_random_seed="91")
    assert response[0] == 400 and len(calls) == 1
    page = response[2].decode()
    for locale in ("de", "en"):
        if enhanced:
            raw = envelope(page, "/matches/api/v1/analysis", {"use_profile_presets": [],
                "immediate_random_seed": ["27"]})
            response = enhanced_switch(browser, page, raw, locale)
        else:
            response = browser.submit(Forms(page).find("/actions/profile/language"),
                                      language=locale)
        assert response[1]["location"].endswith("#match-review")
        page = follow(browser, response)
        owner, nodes = decision_nodes(page)
        advanced, = [n for n in nodes if n["tag"] == "details"]
        assert "open" in advanced["attrs"]  # Overrides the enhanced request to close every details.
        invalid, = [n for n in nodes if n["attrs"].get("aria-invalid") == "true"]
        assert invalid["attrs"]["name"] == "immediate_sample_count"
        assert f'href="#{invalid["attrs"]["id"]}"' in page
        assert f'id="{invalid["attrs"]["aria-describedby"]}"' in page
        error = next(n for n in Hierarchy(page).nodes if n["attrs"].get("class") == "error-summary")
        assert not any(p is owner for p in error["parents"])
        retry = operation_form(page, "analyze_decision")
        assert {name: retry["values"].get(name) for name in (*ADVANCED, "decision_index")} == {
            **DEFAULTS, "decision_index": "6", "use_profile_presets": None,
            "immediate_sample_count": "-1", "immediate_random_seed": "27",
            "search_random_seed": "91"}
        assert len(calls) == 1 and canonical(first.to_dict()) == before
        assert {route: browser.request("GET", route)[2] for route in downloads} == downloads
    response = browser.submit(retry, immediate_sample_count="3")
    assert response[0] == 303, [n["text"] for n in Hierarchy(response[2].decode()).nodes
                              if n["attrs"].get("class") == "error-summary"]
    page = follow(browser, response)
    report = active.capture.report_store.list()[-1]
    expected = MatchDecisionAnalysisOptionsV1(immediate_sample_count=3, immediate_random_seed=27,
        search_random_seed=None, use_profile_presets=False)
    assert response[1]["location"] == f"/matches/reports/{report.report_id}"
    assert report.value.decision_index == calls[-1]["decision_index"] == 6
    assert report.value.options == calls[-1]["options"] == expected
    prepared = build_match_decision_position_request_v1(workspace, match_position=3,
        decision_index=6, options=expected)
    assert report.value.request == prepared.request
    assert invocations[-1].request == prepared.request
    assert invocations[-1].options == prepared.application_options
    assert invocations[-1].external_documents == prepared.external_documents
    assert len(calls) == len(invocations) == 2
    # A retained non-first Report does not supply the new selector or advanced defaults.
    values = operation_form(page, "analyze_decision")["values"]
    assert values["decision_index"] == "1"
    assert {key: values[key] for key in ADVANCED} == DEFAULTS
    retained = canonical(report.to_dict())
    stale = operation_form(page, "analyze_decision")
    browser.page("/matches/review/2")
    assert browser.submit(stale)[0] == 409
    assert active.selected_position == 2 and len(calls) == 2
    assert canonical(report.to_dict()) == retained and path.read_bytes() == disk


@pytest.mark.parametrize("method,seed,normalized", (
    ("immediate_expected_value", "37", None), ("bounded_search", "37", 37),
    ("auto", "", 0), ("information_set_search", "37", 37),
))
def test_emitted_settings_keep_method_normalization(method, seed, normalized):
    from test_match_decision_review_preparation import _workspace_with_partial_game
    workspace, _ = _workspace_with_partial_game()
    view, state, _ = rendered(workspace, 3, "en")
    page = render_match_review_v1(state, view, managed_handle="a" * 64, locale="en")
    values = operation_form(page, "analyze_decision")["values"]
    options = _decision_options({**values, "recommendation_method": method,
                                 "search_random_seed": seed}, browser_form=True)
    assert options.search_random_seed == normalized
    assert options.recommendation_method == method and options.use_profile_presets


def test_actual_analysis_route_bounds_and_strict_fields(localized_server):
    from test_frontend_language_switching import _request

    from skatmind.capture_web.contracts import MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES
    browser = Browser(localized_server)
    page = record_context_match(browser)
    offered = operation_form(page, "analyze_decision")
    definition = get_frontend_form_by_key_v1("match.analysis.analyze_decision")
    assert definition.body_limit == MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES == 1_048_576
    for changes in ({"unexpected": "value"}, {"decision_index": ["2", "2"]},
                    {"search_random_seed": "not-an-integer"}):
        assert browser.submit(offered, **changes)[0] == 400
    headers = {"Cookie": browser.cookie, "Origin": localized_server.origin,
               "Content-Type": "application/x-www-form-urlencoded"}
    assert _request(localized_server, "POST", offered["action"], headers=headers,
                    body=b"operation=analyze_decision&search_random_seed=%ZZ")[0] == 400
    assert _request(localized_server, "POST", offered["action"], headers=headers,
                    body=b"x" * (definition.body_limit + 1))[0] == 413
    active = localized_server.app_context.managed_stateful.active_match
    assert not active.capture.report_store.list()


def test_returned_form_executes_small_late_search(localized_server):
    from test_match_decision_analysis import _complete_workspace

    from skatmind.match_workspace_persistence import save_match_workspace_file_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )
    workspace = _complete_workspace()
    path = localized_server.app_context.managed_stateful.root("matches") / "search.json"
    assert save_match_workspace_file_v1(path,
        build_match_workspace_persistence_document_v1(workspace),
        expected_content_fingerprint=None).status == "saved"
    browser = Browser(localized_server)
    follow(browser, browser.submit(chooser_form(home_chooser(browser), "matches")))
    offered = operation_form(browser.page("/matches/review/3"), "analyze_decision")
    response = browser.submit(offered, decision_index="28", recommendation_method="bounded_search",
        immediate_sample_count="1", immediate_random_seed="13", search_random_seed="7",
        search_budget_profile="interactive_v1")
    follow(browser, response)
    report, = localized_server.app_context.managed_stateful.active_match.capture.report_store.list()
    assert response[1]["location"] == f"/matches/reports/{report.report_id}"
    assert report.value.options == MatchDecisionAnalysisOptionsV1(
        recommendation_method="bounded_search", immediate_sample_count=1, immediate_random_seed=13,
        search_random_seed=7, search_budget_profile="interactive_v1", use_profile_presets=True)
    assert report.value.result.document["bounded_search_result"]["status"] == "complete"
    expected = build_match_decision_position_request_v1(workspace, match_position=3,
        decision_index=28, options=report.value.options)
    assert report.value.request == expected.request
