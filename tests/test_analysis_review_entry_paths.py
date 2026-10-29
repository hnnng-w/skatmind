"""Delivered entry controls distinguish manual input from guarded recorded review."""

import pytest
from test_frontend_language_switching import localized_server as _server
from test_guided_frontend_web import _position_values
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_recorded_review_navigation import chooser_form, saved_partial_match
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Browser, Forms
from test_task_first_language_preservation import enhanced_switch, envelope
from test_unified_local_app_managed_items import _save_session

import skatmind.app_web.execution as execution
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def entry_link(page, destination, caption, *, button=False):
    tree = Hierarchy(page)
    links = [node for node in tree.nodes if node["tag"] == "a"
             and node["attrs"].get("href") == destination
             and any(parent["tag"] == "main" for parent in node["parents"])]
    assert len(links) == 1
    link = links[0]
    assert link["text"] == caption
    assert tree.visible(link)
    assert not any(parent["tag"] == "form" for parent in link["parents"])
    assert not {"role", "onclick", "tabindex", "target", "download"} & link["attrs"].keys()
    assert ("button-link" in link["attrs"].get("class", "").split()) == button
    return link["attrs"]["href"]


def recorded_link(page, locale, *, button=False):
    caption = ("Choose a decision from a recording" if locale == "en"
               else "Entscheidung aus Aufzeichnung auswählen")
    return entry_link(page, "/review/recorded", caption, button=button)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_delivered_independent_entry_has_direct_form_and_one_native_recorded_action(
    localized_server, locale,
):
    browser = Browser(localized_server)
    status, _, body = browser.request("GET", "/analyze", headers={"Accept-Language": locale})
    assert status == 200
    page = body.decode()
    tree = Hierarchy(page)
    heading = ("Enter a situation yourself" if locale == "en"
               else "Situation selbst eingeben")
    assert [node["text"] for node in tree.nodes if node["tag"] == "h2"].count(heading) == 1
    assert page.count(text(locale, "entry.decision")) == 1
    recorded_link(page, locale, button=True)
    assert page.index('href="/review/recorded"', page.index("<main")) < page.index(
        'id="workflow-form"')
    form = tree.by_id("workflow-form")
    assert tree.visible(form)
    assert form["attrs"]["action"] == "/actions/analyze/run-guided"
    assert form["attrs"]["method"] == "post"
    modes = tree.within("field-analysis_mode", "input")
    assert [(node["attrs"]["type"], node["attrs"]["name"], node["attrs"]["value"])
            for node in modes] == [("radio", "analysis_mode", value)
                                  for value in ("live_decision", "post_game_review")]
    assert ["checked" in node["attrs"] for node in modes] == [True, False]
    assert tree.within("field-analysis_mode", "legend")[0]["text"] == text(
        locale, "guided.choice")
    assert [form["action"] for form in Forms(page).forms] == [
        "/actions/profile/language", "/actions/analyze/run-guided",
        "/actions/analyze/import-json", "/actions/analyze/reset"]
    home = browser.request("GET", "/", headers={"Accept-Language": locale})[2].decode()
    expected = ("Enter a card situation yourself and analyze one decision." if locale == "en"
                else "Eine Kartensituation selbst eingeben und eine Entscheidung analysieren.")
    assert f'<p class="task-summary">{expected}</p>' in home


@pytest.mark.parametrize("locale", ("de", "en"))
def test_manual_purpose_editor_scope_and_secondary_native_alternatives(localized_server, locale):
    browser = Browser(localized_server)
    page = browser.request("GET", "/review", headers={"Accept-Language": locale})[2].decode()
    tree = Hierarchy(page)
    purpose = ("Review a completed game manually" if locale == "en"
               else "Abgeschlossenes Spiel manuell auswerten")
    assert [node["text"] for node in tree.nodes if node["tag"] == "h1"] == [purpose]
    assert not any(node["text"] == purpose for node in tree.nodes if node["tag"] == "h2")
    explanation = ("In the guided editor, enter the full deal and play history." if locale == "en"
                   else "Im geführten Editor geben Sie die vollständige Kartenverteilung "
                        "und den Spielverlauf ein.")
    assert page.count(explanation) == 1
    assert 'class="workflow-choice"' not in page
    assert text(locale, "guided.process_local") in page
    assert text(locale, "guided.review.scope_help") in page
    assert text(locale, "guided.import_help") in page
    recorded_link(page, locale)
    entry_link(page, "/sessions", text(locale, "entry.recording_action"))
    assert text(locale, "entry.recording_introduction") in page
    assert [form["action"] for form in Forms(page).forms] == [
        "/actions/profile/language", "/actions/review/start", "/actions/review/import-json"]
    assert localized_server.app_context.review_state.draft is None
    chooser = browser.request("GET", "/review/recorded",
                              headers={"Accept-Language": locale})[2].decode()
    entry_link(chooser, "/review", purpose)
    assert text(locale, "recordings.manual_help") in chooser


@pytest.mark.parametrize("mode", ("live_decision", "post_game_review"))
def test_emitted_analysis_modes_still_execute_their_exact_request(localized_server, mode):
    browser = Browser(localized_server)
    form = Forms(browser.page("/analyze")).find("/actions/analyze/run-guided")
    values = {**_position_values(int(form["values"]["revision"])), "sample_count": "1",
              "analysis_mode": mode,
              "actual_card_played": "CJ" if mode == "post_game_review" else ""}
    page = follow(browser, browser.submit(form, **values))
    state = localized_server.app_context.analyze_state
    assert state.latest_successful_result is not None
    assert state.draft.analysis_mode == mode
    assert state.latest_successful_request.document["analysis_mode"] == mode
    assert Forms(page).find(form["action"])["values"]["analysis_mode"] == mode
    recorded_link(page, "en", button=True)


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("enhanced", (False, True))
def test_entry_navigation_keeps_result_rejected_values_and_language_error_priority(
    localized_server, locale, enhanced,
):
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/analyze"), locale)
    form = Forms(page).find("/actions/analyze/run-guided")
    page = follow(browser, browser.submit(form, **_position_values(0), sample_count="1"))
    state = localized_server.app_context.analyze_state
    downloads = {kind: browser.request("GET", f"/downloads/analyze/{kind}.json")[2]
                 for kind in ("request", "result")}
    status, _, body = browser.submit(Forms(page).find(form["action"]), hand=[])
    assert status == 400
    page = body.decode()
    summary = next(node for node in Hierarchy(page).nodes
                   if node["attrs"].get("class") == "error-summary")
    assert "autofocus" in summary["attrs"]
    assert page.index('class="result-presentation"') < page.index('class="error-summary"')
    assert page.index('class="error-summary"') < page.index('id="workflow-form"')
    browser.page(recorded_link(page, locale, button=True))
    page = browser.page("/analyze")
    other = "en" if locale == "de" else "de"
    language = Forms(page).find("/actions/profile/language")
    assert language["values"]["return_to"] == "/analyze"
    page = (follow(browser, enhanced_switch(browser, page,
            envelope(page, form["action"], {"hand": []}), other)) if enhanced
            else switch(browser, page, other))
    recorded_link(page, other, button=True)
    assert text(other, "validation.summary.heading") in page
    assert "hand" not in Forms(page).find(form["action"])["values"]
    assert localized_server.app_context.analyze_state is state
    for kind, raw in downloads.items():
        assert browser.request("GET", f"/downloads/analyze/{kind}.json")[2] == raw


@pytest.mark.parametrize("locale", ("de", "en"))
def test_accepted_manual_step_survives_both_entry_alternatives(localized_server, locale):
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/review"), locale)
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/start")))
    page = follow(browser, browser.submit(Forms(page).find("/actions/review/update-players"),
                                        forehand_label="Synthetic retained name"))
    state = localized_server.app_context.review_state
    assert state.draft.step == 2
    browser.page(entry_link(page, "/sessions", text(locale, "entry.recording_action")))
    page = browser.page("/review")
    chooser = browser.page(recorded_link(page, locale))
    page = browser.page(entry_link(chooser, "/review", text(locale, "recordings.manual")))
    assert localized_server.app_context.review_state is state
    form = Forms(page).find("/actions/review/update-deal")
    assert form["values"]["revision"] == str(state.revision)
    assert not any(form["action"] == "/actions/review/start" for form in Forms(page).forms)
    assert localized_server.app_context.analyze_state.draft is None
    assert localized_server.app_context.managed_stateful.active_session is None


@pytest.mark.parametrize("family", ("sessions", "matches"))
def test_passive_entry_links_preserve_files_and_require_exact_recording_open_form(
    localized_server, monkeypatch, family,
):
    context = localized_server.app_context
    if family == "sessions":
        _save_session(context.managed_stateful.root(family) / "synthetic.json")
    else:
        saved_partial_match(localized_server)
    root = context.managed_home.root
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("Entry navigation must not execute or prepare Learning data")

    monkeypatch.setattr(execution, "execute", forbidden)
    monkeypatch.setattr("skatmind.capture_web.analysis.execute_match_decision_analysis_v1",
                        forbidden)
    monkeypatch.setattr("skatmind.app_web.learning_frontend.prepare_learning_corpus_artifacts_web_v1",
                        forbidden)
    browser = Browser(localized_server)
    initial = (context.analyze_state, context.review_state)
    page = browser.page(recorded_link(browser.page("/analyze"), "en", button=True))
    page = browser.page(entry_link(page, "/review", text("en", "recordings.manual")))
    browser.page(entry_link(page, "/sessions", text("en", "entry.recording_action")))
    page = browser.page(recorded_link(browser.page("/review"), "en"))
    assert context.managed_stateful.active_session is context.managed_stateful.active_match is None
    assert (context.analyze_state, context.review_state) == initial
    form = chooser_form(page, family)
    assert set(form["values"]) == {"family", "handle", "generation", "_frontend_form_instance"}
    assert form["values"]["family"] == family
    assert len(form["values"]["handle"]) == 64
    assert int(form["values"]["generation"]) > 0
    page = follow(browser, browser.submit(form))
    assert (context.managed_stateful.active_session if family == "sessions"
            else context.managed_stateful.active_match) is not None
    # An openable setup/empty Game still has no eligible decision to execute.
    assert not any(f["action"] == "/sessions/review-decision"
                   or f["values"].get("operation") == "analyze_decision" for f in Forms(page).forms)
    assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
