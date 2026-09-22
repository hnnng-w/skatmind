"""Real HTTP/semantic regressions; browser measurements are a separate check."""

import re
from html.parser import HTMLParser
from importlib.resources import files

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_recording_recovery_web import (
    Browser,
    Forms,
    entry_action,
    follow,
    operation_form,
    start_match,
)

from skatmind.app_web.language_form_preservation import instrument_language_forms_v1
from skatmind.app_web.match_frontend import execute_unified_match_analysis_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.styles = []
        self.tiles = []
        self.tile = None
        self.classes = []
        self.ids = []
        self.rounds = 0
        self.details = []
        self.buttons = []
        self.targets = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
            self.targets[attrs["id"]] = (tag, attrs)
        if tag == "details":
            self.details.append(attrs)
        if tag == "button":
            self.buttons.append(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.styles.append(attrs["href"])
        classes = attrs.get("class", "").split()
        if "round-slots" in classes:
            self.rounds += 1
        if tag == "a" and "match-tile" in classes:
            self.tile = {**attrs, "parts": {}, "text": ""}
            self.tiles.append(self.tile)
        if self.tile is not None:
            self.classes.append(classes)
            for name in classes:
                self.tile["parts"][name] = ""

    def handle_data(self, data):
        if self.tile is not None:
            self.tile["text"] += data
            for classes in self.classes:
                for name in classes:
                    self.tile["parts"][name] += data

    def handle_endtag(self, tag):
        if self.tile is not None:
            self.classes.pop()
        if tag == "a":
            self.tile = None


def assert_app_assets(browser, page):
    markup = Markup(page)
    assert markup.styles == ["/assets/app.css"]
    assert len(markup.ids) == len(set(markup.ids))
    status, headers, content = browser.request("GET", markup.styles[0])
    assert status == 200 and headers["content-type"] == "text/css; charset=utf-8"
    assert content == files("skatmind.app_web").joinpath("assets/app.css").read_bytes()
    assert headers["cache-control"] == "no-store"
    assert headers["x-content-type-options"] == "nosniff"
    assert "access-control-allow-origin" not in headers


@pytest.mark.parametrize("locale", ("de", "en"))
def test_all_unified_routes_and_contextual_errors_use_app_resources(localized_server, locale):
    browser = Browser(localized_server)
    follow(browser, browser.submit(Forms(browser.page("/")).find("/actions/profile/language"),
                                   language=locale))
    for route in ("/", "/sessions", "/matches", "/matches/new", "/learning"):
        assert_app_assets(browser, browser.page(route))
    page = browser.page("/learning")
    follow(browser, browser.submit(Forms(page).find("/learning/create"),
                                   collection_name="Synthetic collection"))
    assert_app_assets(browser, browser.page("/learning/current"))
    page = start_match(browser, locale)
    assert_app_assets(browser, page)
    active = localized_server.app_context.managed_stateful.active_match
    accepted = active.workspace
    status, _, content = browser.submit(operation_form(page, "set_declaration"),
                                        game_type="unsupported")
    assert status == 400 and active.workspace is accepted
    page = content.decode()
    assert_app_assets(browser, page)
    assert 'class="error-summary"' in page and 'role="alert"' in page
    assert 'id="match-declaration"' in page and 'id="match-evidence"' in page
    # An actual unavailable retained Report, with the same full page composition.
    page = browser.page("/matches/current")
    page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards="SA"))
    result = execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "1", "decision_index": "1",
        "expected_revision": str(active.workspace.revision),
    })
    page = browser.page(f'/matches/reports/{result.state["selected_report_id"]}')
    assert_app_assets(browser, page)
    assert text(locale, "task.match.decision_blocked") in page
    for package, route, resource in (
        ("skatmind.capture_web", "/matches/assets/capture.css", "assets/capture.css"),
        ("skatmind.corpus_web", "/learning/assets/corpus.css", "assets/corpus.css"),
    ):
        status, headers, content = browser.request("GET", route)
        assert status == 200 and headers["content-type"].startswith("text/css")
        assert content == files(package).joinpath(resource).read_bytes()
        assert browser.request("GET", route, headers={"Cookie": ""})[0] == 403
    assert browser.request("GET", "/assets/unregistered.css")[0] == 404


@pytest.mark.parametrize("locale", ("de", "en"))
def test_36_structured_tiles_match_authoritative_rotation_and_selection(localized_server, locale):
    browser = Browser(localized_server)
    start_match(browser, locale, "Alexandra-Maria von Hohenlohe-Schillingsfuerst")
    page = browser.page("/matches/position/2")
    follow(browser, browser.submit(operation_form(page, "mark_passed_deal")))
    active = localized_server.app_context.managed_stateful.active_match
    original = active.path.read_bytes()
    for selected in (1, 2, 36):
        page = browser.page(f"/matches/position/{selected}")
        markup = Markup(page)
        view = project_task_first_match_v1(active.workspace, selected_position=selected)
        assert markup.rounds == 12 and len(markup.tiles) == 36
        assert [tile["href"] for tile in markup.tiles] == [
            f"/matches/position/{number}#match-recording" for number in range(1, 37)]
        assert sum(tile.get("aria-current") == "page" for tile in markup.tiles) == 1
        for tile, position in zip(markup.tiles, view.positions, strict=True):
            assert tile["data-status"] == position.game_state
            assert tile["parts"]["match-tile-title"] == text(
                locale, "task.match.position", number=position.match_position)
            assert tile["parts"]["match-tile-status"] == text(
                locale, f"task.match.status.{position.game_state}")
            markers = tile["parts"]["match-tile-markers"]
            assert (text(locale, "task.match.selected") in markers) == (
                position.match_position == selected)
            assert (text(locale, "task.match.next") in markers) == (
                position.match_position == view.next_position)
            participants = tile["parts"]["match-tile-participants"]
            for seat in ("forehand", "middlehand", "rearhand"):
                player = next(p for p in active.workspace.match_definition.participants
                              if p.player_id == getattr(position, f"{seat}_player_id"))
                label = text(locale, f"creation.seat.{seat}") + ": " + player.player_label
                assert label in participants
        assert active.path.read_bytes() == original


def test_recovery_transfer_fields_and_language_identities_survive_rendering(localized_server):
    browser = Browser(localized_server)
    follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/create"),
                                   collection_name="Synthetic target"))
    page = start_match(browser)
    for card in ("SA", "H7", "S7", "CA", "S8"):
        page = follow(browser, browser.submit(operation_form(page, "append_plays"), cards=card))
    assert 'href="#match-play-2"' in page and 'href="#match-play-5"' in page
    page = follow(browser, browser.submit(entry_action(page, 2)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="S9"))
    manifest = instrument_language_forms_v1(page)[1]
    forms = Forms(page)
    transfer = forms.find("/matches/transfer-workspace")["values"]
    assert set(transfer) == {
        "managed_handle", "target_managed_handle", "expected_catalog_revision",
        "selection_mode", "same_revision_resolution", "_frontend_form_instance",
    }
    assert transfer["selection_mode"] == "select_imported"
    assert transfer["same_revision_resolution"] == "reject"
    preview = localized_server.app_context.managed_stateful.active_match.recovery.preview
    translated = follow(browser, browser.submit(forms.find("/actions/profile/language"),
                                                language="de"))
    assert instrument_language_forms_v1(translated)[1] == manifest
    assert Forms(translated).find("/matches/recovery/apply")["values"] == forms.find(
        "/matches/recovery/apply")["values"]
    apply = re.search(r'<form[^>]*action="/matches/recovery/apply".*?</form>', translated, re.S)[0]
    assert re.search(r'<button[^>]*name="confirm_apply" value="on"', apply)
    assert not re.search(r'<input[^>]*name="confirm_apply"', apply)
    assert re.search(r'<section id="match-recovery" tabindex="-1">', translated)
    assert localized_server.app_context.managed_stateful.active_match.recovery.preview is preview
    assert_app_assets(browser, translated)


def test_executed_report_table_is_named_focusable_and_keeps_exact_download(localized_server):
    from test_match_decision_review_preparation import _workspace_with_partial_game

    from skatmind.app_web.match_frontend import import_unified_match_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    browser = Browser(localized_server)
    workspace, _ = _workspace_with_partial_game()
    managed = localized_server.app_context.managed_stateful
    active = import_unified_match_v1(managed.root("matches"), handle="6" * 64,
        document=build_match_workspace_persistence_document_v1(workspace).to_dict())
    managed.activate_match(active)
    result = execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "3", "decision_index": "1",
        "immediate_sample_count": "4", "expected_revision": str(workspace.revision),
    })
    report_id = result.state["selected_report_id"]
    route = f"/matches/reports/{report_id}"
    download = f"/matches/api/v1/reports/{report_id}.json"
    status, _, retained = browser.request("GET", download)
    assert status == 200
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(
            Forms(browser.page(route)).find("/actions/profile/language"), language=locale))
        region = re.search(
            r'<div class="workflow-table-scroll candidate-comparison" role="region" tabindex="0" '
            r'aria-label="([^"]+)"><table class="candidate-table" role="table">'
            r'<caption>([^<]+)</caption>', page)
        assert region and region[1] == region[2] == text(locale, "result.table.immediate")
        assert 'scope="col"' in page and 'scope="row"' in page
        assert f'href="{download}" download' in page
        assert browser.request("GET", download)[2] == retained
        assert_app_assets(browser, page)


def test_review_secondary_form_and_native_result_focus_contract(localized_server):
    from test_session_recorded_review_web import record_live_game, review_first

    browser = Browser(localized_server)
    record_live_game(browser, play_count=1)
    page, submitted = review_first(browser)
    active = localized_server.app_context.managed_stateful.active_session
    source, execution = active.recorded_review_source, active.execution
    saved = active.path.read_bytes()
    markup = Markup(page)
    assert markup.targets["session-result"] == (
        "div", {"id": "session-result", "tabindex": "-1"})
    button, = [b for b in markup.buttons if b.get("aria-describedby") == "recorded-decision-1"]
    assert button == {"type": "submit", "class": "secondary",
                      "aria-describedby": "recorded-decision-1"}
    assert set(submitted["values"]) == {
        "managed_handle", "expected_revision", "decision_selection", "_frontend_form_instance"}
    retained = {name: browser.request("GET", f"/sessions/downloads/{name}.json")[2]
                for name in ("request", "result")}
    for locale in ("de", "en"):
        response = browser.submit(Forms(page).find("/actions/profile/language"), language=locale)
        assert response[1]["location"] == "/sessions/current#session-result"
        page = follow(browser, response)
        translated = Markup(page)
        assert translated.targets["session-result"] == markup.targets["session-result"]
        assert translated.details == markup.details
        assert Forms(page).find("/sessions/review-decision") == submitted
        assert 'href="#recorded-decision-1"' in page
        assert active.recorded_review_source is source and active.execution is execution
        assert active.path.read_bytes() == saved
        for name, raw in retained.items():
            assert browser.request("GET", f"/sessions/downloads/{name}.json")[2] == raw


def test_match_peer_disclosures_keep_wrapper_order_fields_and_disabled_actions(localized_server):
    browser = Browser(localized_server)
    page = start_match(browser)
    markup = Markup(page)
    assert markup.targets["match-metadata"] == (
        "div", {"id": "match-metadata", "tabindex": "-1"})
    assert '<div id="match-metadata" tabindex="-1"><details class="advanced-settings">' in page
    keys = ("task.match.evidence", "task.match.annotations", "task.match.metadata",
            "task.match.statistics", "task.match.analysis", "task.match.corrections")
    positions = [page.index(f'<summary>{text("en", key)}</summary>') for key in keys]
    assert positions == sorted(positions)
    fields = operation_form(page, "update_match_metadata")
    source = localized_server.app_context.managed_stateful.active_match.path.read_bytes()
    translated = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                                language="de"))
    assert Markup(translated).details == markup.details
    refreshed = operation_form(translated, "update_match_metadata")
    assert refreshed == {**fields, "values": {**fields["values"],
        "profile_generation": str(int(fields["values"]["profile_generation"]) + 1)}}
    assert localized_server.app_context.managed_stateful.active_match.path.read_bytes() == source
    # Empty Learning genuinely disables unavailable work; CSS must not replace this attribute.
    page = follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/create"),
                                         collection_name="Synthetic visual contract"))
    disabled = [button for button in Markup(page).buttons if "disabled" in button]
    assert disabled and all(button["type"] == "submit" for button in disabled)
