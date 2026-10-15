"""Two retained decisions and the distinction between passive views and strict reopen."""

import re
from html import unescape

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_learning_debrief_web import comparison_link
from test_learning_direct_entry_web import add_form, create_collection, source_handle
from test_match_recording_recovery_web import follow
from test_match_rollout_web import form, open_alex
from test_recording_task_focus import Hierarchy
from test_session_recorded_review_web import Forms

from skatmind.app_web.stateful_localization import text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def analyze_retained(browser, decision):
    page = follow(browser, browser.request("GET", f"/matches/review/2?decision_index={decision}"))
    action = form(page)
    values = {"requested_worlds": "8"}
    if "analysis_matadors" in action["values"]:
        values["analysis_matadors"] = "1"
    page = follow(browser, browser.submit(action, **values))
    reports = browser.server.app_context.managed_stateful.active_match.capture.report_store.list()
    return page, reports[-1]


def setup_collection(server, name="Synthetic overview"):
    browser, path, _ = open_alex(server, count=30)
    _, first = analyze_retained(browser, 3)
    create_collection(browser, name)
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    return browser, path, page, first


def include_form(page, report):
    return next(item for item in Forms(page).forms
                if item["action"] == "/learning/debrief/include"
                and item["values"]["report_id"] == report.report_id)


def test_ordinary_match_navigation_and_comparison_preserve_two_sources(localized_server):
    browser, path, page, first = setup_collection(localized_server)
    target = localized_server.app_context.managed_stateful.active_learning
    before = path.read_bytes()
    report_page = browser.page(f"/matches/reports/{first.report_id}")
    assert 'Add to Synthetic overview' in report_page
    response = browser.submit(include_form(report_page, first))
    assert response[1]["location"].startswith("/learning/debrief/")
    page = follow(browser, response)
    assert 'Analysis overview · Synthetic overview' in unescape(page)
    assert 'Added Synthetic Hearts review' in unescape(page)
    assert 'to Synthetic overview.' in page
    assert 'Open analysis overview' in page
    route = comparison_link(page)
    assert browser.request("GET", route)[0] == 200
    assert browser.request("GET", route.rsplit("/", 1)[0])[0] == 200
    assert len(target.debrief_sources.sources) == 1
    browser.page("/matches/current")
    browser.page("/matches/position/1")
    report_page, second = analyze_retained(browser, 17)
    assert second.value.request.document["actual_card_played"] == "S8"
    assert len(second.value.result.document["legal_cards"]) == 1
    page = browser.page("/learning/current")
    assert len(target.debrief_sources.sources) == 1
    assert 'Add to Synthetic overview' in report_page
    page = follow(browser, browser.submit(include_form(report_page, second)))
    assert "included: 2 (2 reports)" in page
    menu = browser.page("/learning")
    overview = re.search(r'href="(/learning/debrief/[a-f0-9]{64}/all)"', menu)[1]
    reopened_page = browser.page(overview)
    assert 'included: 2 (2 reports)' in reopened_page
    reopen = next(node for node in Hierarchy(menu).nodes if node["tag"] == "form"
                  and node["attrs"].get("action") == "/learning/open")
    assert not Hierarchy.visible(reopen)
    assert localized_server.app_context.managed_stateful.active_learning is target
    assert len(target.debrief_sources.sources) == 2
    assert path.read_bytes() == before


def test_named_target_is_not_a_caption_authority_and_rejection_preserves_old_source(
    localized_server,
):
    browser, path, page, report = setup_collection(localized_server)
    old_target = localized_server.app_context.managed_stateful.active_learning
    action = include_form(browser.page(f"/matches/reports/{report.report_id}"), report)
    create_collection(browser, "Synthetic overview")  # Equal name, different identity/context.
    target = localized_server.app_context.managed_stateful.active_learning
    page = follow(browser, browser.submit(add_form(browser), source_handle=source_handle(path)))
    assert target is not old_target and target.handle != old_target.handle
    rejected = browser.submit(action)
    assert rejected[0] == 409 and "Added Synthetic" not in rejected[2].decode()
    assert not target.debrief_sources.sources and not old_target.debrief_sources.sources
    page = browser.page(f"/matches/reports/{report.report_id}")
    response = browser.submit(include_form(page, report))
    overview = follow(browser, response)
    assert target.debrief_sources.sources and "included: 1 (1 reports)" in overview
    current = browser.page(f"/matches/reports/{report.report_id}")
    assert "Included in Synthetic overview" in current
    assert not any(f["action"] == "/learning/debrief/include" for f in Forms(current).forms)
    assert "Open analysis overview" in current


def test_no_active_collection_requires_explicit_choice_and_optional_summary_is_scoped(
    localized_server,
):
    browser, _, _ = open_alex(localized_server, count=30)
    page, report = analyze_retained(browser, 3)
    assert "Choose a collection for this Report" in page
    assert not any(f["action"] == "/learning/debrief/include" for f in Forms(page).forms)
    summary_link = next(node for node in Hierarchy(page).nodes if node["tag"] == "a"
        and node["attrs"].get("href") == f"/learning/debrief/from/{report.report_id}")
    assert not Hierarchy.visible(summary_link)
    page = follow(browser, browser.request("GET", summary_link["attrs"]["href"]))
    assert "Summary of this Report only" in page
    assert "Analysis overview ·" not in page
    assert localized_server.app_context.managed_stateful.active_learning is None


def test_compact_rows_exact_player_comparison_return_language_and_downloads(localized_server):
    from skatmind.match_analysis_exports import build_match_report_result_export_v1

    browser, path, page, first = setup_collection(localized_server)
    follow(browser, browser.submit(include_form(page, first)))
    page, second = analyze_retained(browser, 17)
    page = follow(browser, browser.submit(include_form(page, second)))
    before = path.read_bytes()
    route = comparison_link(page)
    base = route.rsplit("/", 1)[0].rsplit("/", 1)[0]
    filtered = base + "/1"  # Captured Alex identity in this fixture.
    page = browser.page(filtered)
    assert "Recorded decisions: 10" in page and "included: 2 (2 reports)" in page
    rows = [node for node in Hierarchy(page).nodes if node["tag"] == "article"
            and node["attrs"].get("class") == "debrief-decision"]
    assert len(rows) == 2
    assert "Trick 1, card 3 · Alex" in rows[0]["text"] and "C7" in rows[0]["text"]
    assert "Trick 6, card 2 · Alex" in rows[1]["text"] and "S8" in rows[1]["text"]
    assert text("en", "rollout.only_card") in rows[1]["text"]
    assert text("en", "debrief.alternatives") not in rows[1]["text"]
    coverage = next(node for node in Hierarchy(page).nodes if node["tag"] == "p"
                    and "Completed simulations per card" in node["text"])
    assert not Hierarchy.visible(coverage)
    assert "Analysis assumption:" in rows[0]["text"]
    for report in (first, second):
        detail = browser.page(filtered + "/" + report.report_id)
        assert f'href="{filtered}"' in detail and "Open analysis overview" in detail
        assert browser.request("GET", filtered + "/" + report.report_id + "/result.json")[2] == (
            build_match_report_result_export_v1(report).to_bytes())
        page = browser.page(filtered)
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                              language=locale))
        title = text(locale, "debrief.overview_title", collection="Synthetic overview")
        assert title in unescape(page)
        assert f'href="{filtered}/{first.report_id}"' in page
    assert path.read_bytes() == before


def test_expired_receipt_keeps_included_action_and_removal_restores_available(localized_server):
    from dataclasses import replace

    browser, _, _, report = setup_collection(localized_server)
    page = browser.page(f"/matches/reports/{report.report_id}")
    response = browser.submit(include_form(page, report))
    target = localized_server.app_context.managed_stateful.active_learning
    receipt = target.operation_feedback.pending
    assert receipt.message_key == "feedback.debrief_added"
    target.operation_feedback.pending = replace(receipt, expires_at=0)
    page = follow(browser, response)
    assert 'class="operation-feedback"' not in page
    individual = browser.page(f"/matches/reports/{report.report_id}")
    assert "Included in Synthetic overview" in individual and "Open analysis overview" in individual
    follow(browser, browser.submit(Forms(page).find("/learning/debrief/remove")))
    individual = browser.page(f"/matches/reports/{report.report_id}")
    assert "Included in Synthetic overview" not in individual
    assert include_form(individual, report)["values"]["report_id"] == report.report_id


def test_overview_inputs_link_does_not_open_a_replacement_collection(localized_server):
    browser, _, page, report = setup_collection(localized_server)
    page = follow(browser, browser.submit(include_form(page, report)))
    inputs = re.search(r'href="(/learning/debrief/[^"]+/inputs)"', page)[1]
    original = localized_server.app_context.managed_stateful.active_learning
    assert browser.request("GET", inputs)[0] == 200
    assert localized_server.app_context.managed_stateful.active_learning is original
    create_collection(browser, "Another target")
    assert browser.request("GET", inputs)[0] == 409


def test_named_action_and_receipt_escape_the_actual_target(localized_server):
    name = 'Synthetic <overview> & friends'
    browser, _, _, report = setup_collection(localized_server, name)
    individual = browser.page(f"/matches/reports/{report.report_id}")
    assert 'Add to Synthetic &lt;overview&gt; &amp; friends' in individual
    page = follow(browser, browser.submit(include_form(individual, report)))
    assert 'Analysis overview · Synthetic &lt;overview&gt; &amp; friends' in page
    assert 'to Synthetic &lt;overview&gt; &amp; friends.' in page


def test_post_acceptance_target_change_cannot_redirect_to_another_collection(localized_server):
    browser, _, page, report = setup_collection(localized_server)
    accepted = browser.submit(include_form(page, report))
    assert accepted[0] == 303
    create_collection(browser, "Synthetic overview")
    assert browser.request("GET", accepted[1]["location"].split("#")[0])[0] == 409
    assert not localized_server.app_context.managed_stateful.active_learning.debrief_sources.sources


def test_profile_reset_does_not_reset_incorporated_reports(localized_server):
    browser, path, page, report = setup_collection(localized_server)
    page = follow(browser, browser.submit(include_form(page, report)))
    target = localized_server.app_context.managed_stateful.active_learning
    sources = target.debrief_sources.sources
    original = path.read_bytes()
    action = Forms(browser.page("/settings")).find("/actions/profile/reset")
    follow(browser, browser.submit(action, confirm_reset="on"))
    assert localized_server.app_context.managed_stateful.active_learning is target
    assert target.debrief_sources.sources == sources
    assert path.read_bytes() == original


def test_inputs_rechecks_owner_after_scope_resolution(localized_server, monkeypatch):
    import skatmind.app_web.debrief_http as transport
    from skatmind.app_web.learning_frontend import create_unified_learning_corpus_v1

    browser, _, page, report = setup_collection(localized_server)
    page = follow(browser, browser.submit(include_form(page, report)))
    inputs = re.search(r'href="(/learning/debrief/[^"]+/inputs)"', page)[1]
    app = localized_server.app_context
    other = create_unified_learning_corpus_v1(app.managed_stateful.root("corpora"),
        handle="f" * 64, corpus_id="synthetic-replacement")
    real = transport.resolve_scope
    def replaced(*args, **kwargs):
        scope = real(*args, **kwargs)
        with app.lock:
            app.managed_stateful.active_learning = other
        return scope
    monkeypatch.setattr(transport, "resolve_scope", replaced)
    response = browser.request("GET", inputs)
    assert response[0] == 409
    assert not other.debrief_sources.sources


def test_menu_overview_uses_bound_handle_not_an_older_discovery_active_flag(localized_server):
    from skatmind.app_web.stateful_rendering import render_managed_category_landing_v1

    browser, _, _, _ = setup_collection(localized_server)
    app = localized_server.app_context
    first = app.managed_stateful.active_learning
    create_collection(browser, "Different collection")
    browser.page("/learning")
    view = app.managed_stateful.discoveries["corpora"].view
    assert not next(item for item in view.items if item.handle == first.handle).active
    route = "/learning/debrief/" + "a" * 64 + "/all"
    page = render_managed_category_landing_v1(view, profile=app.frontend_profile.document,
        active_overview=(first.handle, route))
    link_node = next(node for node in Hierarchy(page).nodes if node["tag"] == "a"
                     and node["attrs"].get("href") == route)
    owner = next(node for node in reversed(link_node["parents"]) if node["tag"] == "article")
    assert "Synthetic overview" in owner["text"] and "Different collection" not in owner["text"]


def test_strict_reopen_reproduces_zero_without_changing_recording(localized_server):
    browser, path, page, first = setup_collection(localized_server)
    follow(browser, browser.submit(include_form(page, first)))
    target = localized_server.app_context.managed_stateful.active_learning
    before = path.read_bytes()
    menu = browser.page("/learning")
    follow(browser, browser.submit(Forms(menu).find("/learning/open")))
    reopened = localized_server.app_context.managed_stateful.active_learning
    assert reopened is not target and reopened.debrief_sources.sources == ()
    page = browser.page("/learning/current")
    assert "included: 0 (0 reports)" in unescape(page)
    assert path.read_bytes() == before
