"""R03 composition over accepted sources; native HTTP, not injected successful Results."""

from html.parser import HTMLParser

import pytest
from test_frontend_language_switching import localized_server as _localized_server
from test_match_game_navigation_web import create_empty, declare, primary
from test_match_recording_recovery_web import entry_action, follow, operation_form
from test_recorded_decision_context import MATCH_HAND
from test_session_direct_card_start_web import create
from test_session_position_export import _live_ouvert_defender_state, _set_opponent_ouvert_hand
from test_session_recorded_review_web import Browser, Forms, record_score_review_game
from test_task_first_language_preservation import enhanced_switch, envelope
from test_task_first_stateful_projections import session_states

import skatmind.api.v1.session.files as session_files
import skatmind.capture_web.analysis as match_analysis
import skatmind.capture_web.context as match_context
from skatmind.app_web.session_frontend import GuidedSessionContextV1
from skatmind.app_web.task_first_projections import project_task_first_session_v1
from skatmind.app_web.task_first_session_rendering import render_task_first_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.deck import get_full_deck
from skatmind.session_commands import SetSessionGameMetadataCommandV1
from skatmind.session_persistence_codec import build_session_persistence_document_v1
from skatmind.session_transitions import apply_session_command_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


class Hierarchy(HTMLParser):
    """Structural disclosure visibility and ancestry, independently of CSS."""

    def __init__(self, html):
        super().__init__()
        self.nodes = []
        self.stack = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "parents": tuple(self.stack), "text": ""}
        self.nodes.append(node)
        if tag not in {"input", "br", "hr", "img", "link", "meta", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    def by_id(self, identity):
        return next(node for node in self.nodes if node["attrs"].get("id") == identity)

    @staticmethod
    def visible(node):
        return all(parent["tag"] != "details" or "open" in parent["attrs"]
                   for parent in node["parents"])

    def within(self, identity, tag):
        parent = self.by_id(identity)
        return [node for node in self.nodes if node["tag"] == tag
                and any(item is parent for item in node["parents"])]


@pytest.mark.parametrize("locale", ("en", "de"))
def test_initial_session_has_one_task_and_quiet_review_destination(localized_server, locale):
    browser = Browser(localized_server)
    page = create(browser)
    page = follow(browser, browser.submit(Forms(page).find("/actions/profile/language"),
                                         language=locale))
    active = localized_server.app_context.managed_stateful.active_session
    assert active.state.phase == "setup" and active.state.revision == 0
    for key in ("task.session.state", "task.session.next", "task.session.primary"):
        assert f'<h2>{text(locale, key)}</h2>' not in page
    assert Forms(page).find("/sessions/cards")
    assert 'href="#recorded-decisions"' not in page
    assert text(locale, "recorded_review.coverage", available=0, recorded=0) not in page
    markup = Hierarchy(page)
    assert markup.visible(markup.by_id("recorded-decisions"))
    assert markup.visible(markup.by_id("recorded-review-feedback"))


@pytest.mark.parametrize("locale", ("en", "de"))
def test_empty_started_and_passed_match_have_no_normal_review_invitation(localized_server, locale):
    browser = Browser(localized_server)
    page = create_empty(browser, locale)
    for operation in (None, "start_game", "mark_passed_deal"):
        if operation:
            page = follow(browser, browser.submit(operation_form(page, operation),
                **({"confirm_replace": "on"} if operation == "mark_passed_deal" else {})))
        active = localized_server.app_context.managed_stateful.active_match
        game = active.workspace.slots[0].observed_game
        assert game is None or not game.plays
        assert 'href="/matches/review/1"' not in page.split('<section id="match-games"')[0]
        direct = browser.page("/matches/review/1")
        assert 'href="/matches/position/1#match-recording"' in direct
        assert not any(form["values"].get("operation") == "analyze_decision"
                       for form in Forms(direct).forms)
        page = browser.page("/matches/position/1")


@pytest.mark.parametrize("locale", ("en", "de"))
def test_accepted_session_prefix_matrix_keeps_one_task_with_its_form(tmp_path, locale):
    """Prefix fixtures intentionally have no snapshots; they test recording, not readiness."""
    seen = set()
    states = list(session_states())
    public_missing = _live_ouvert_defender_state()
    public_missing = apply_session_command_v1(public_missing, SetSessionGameMetadataCommandV1(
        expected_revision=public_missing.revision, game_id="synthetic-public-hand")).state
    states.extend((public_missing, _set_opponent_ouvert_hand(public_missing)))
    for state in states:
        view = project_task_first_session_v1(state)
        facts = view.facts
        marker = (facts.phase, view.workflow.primary_action, view.deal_destination,
                  sum(len(cards) for _, cards in facts.initial_known_hands),
                  len(facts.known_skat), len(facts.discarded_cards), facts.played_card_count)
        seen.add(marker)
        context = GuidedSessionContextV1(category_root=tmp_path, path=tmp_path / "prefix.json",
            handle="a" * 64, document=build_session_persistence_document_v1(state))
        markup = Hierarchy(render_task_first_session_v1(context, locale=locale))
        headings = markup.within("session-recording", "h2")
        assert len(headings) == 1 and markup.visible(headings[0])
        normal = markup.within("session-recording", "form")
        if facts.phase == "ended":
            assert not normal and headings[0]["text"] == text(locale, "task.session.phase.ended")
        else:
            assert len(normal) == 1 and markup.visible(normal[0])
            assert headings[0]["parents"][-1] is normal[0]["parents"][-1]
            if facts.phase in {"setup", "deal", "skat_and_discard"}:
                assert normal[0]["attrs"]["action"] == "/sessions/cards"
            elif facts.phase == "play" and facts.played_card_count < 30 and state != public_missing:
                assert normal[0]["attrs"]["action"] == "/sessions/play"
            else:
                fields = [node["attrs"] for node in markup.nodes if node["tag"] == "input"
                          and any(parent is normal[0] for parent in node["parents"])]
                kind = next(field["value"] for field in fields if field.get("name") == "kind")
                assert kind == ("set_game_end" if facts.played_card_count == 30 else
                    "set_public_hand" if state == public_missing else
                    "set_declarer" if facts.declarer_player_id is None else "set_declaration")
        assert context.state is state and context.execution is None
    assert {marker[0] for marker in seen} == {
        "setup", "deal", "declaration", "skat_and_discard", "play", "ended"}
    assert {marker[1] for marker in seen} >= {"record_discard", "set_public_hand", "set_game_end"}
    assert {marker[3] for marker in seen} >= {0, 1, 9, 10, 20, 30}
    assert {marker[-1] for marker in seen} >= {0, 1, 29, 30}


def test_direct_partial_hand_declarer_and_declaration_save_once(localized_server, monkeypatch):
    browser = Browser(localized_server)
    page = create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    calls = []
    real = session_files.save_session_file
    def save(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)
    monkeypatch.setattr(session_files, "save_session_file", save)
    for cards, revision, phase in ((get_full_deck()[:4], 5, "deal"),
                                   (get_full_deck()[4:10], 11, "declaration")):
        page = follow(browser, browser.submit(Forms(page).find("/sessions/cards"), cards=cards))
        assert (active.state.revision, active.state.phase) == (revision, phase)
        assert 'href="#recorded-decisions"' not in page
    assert len(calls) == 2
    browser.command("set_declarer")
    assert active.state.revision == 12
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    assert active.state.phase == "play" and len(calls) == 4
    assert active.execution is None
    assert all(record.command.kind != "promote_to_retrospective"
               for record in active.state.command_log)


def test_zero_review_rejection_retains_visible_destination_and_language_feedback(localized_server):
    browser = Browser(localized_server)
    create(browser)
    active = localized_server.app_context.managed_stateful.active_session
    before = active.path.read_bytes()
    # Negative fixture: an old/forged direct submission cannot acquire an eligible row.
    status, _, raw = browser.request("POST", "/sessions/review-decision", {
        "managed_handle": active.handle, "expected_revision": "0", "decision_selection": "a" * 64})
    assert status == 409
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(raw.decode()).find("/actions/profile/language"),
                                             language=locale))
        markup = Hierarchy(page)
        feedback = markup.by_id("recorded-review-feedback")
        assert markup.visible(feedback) and feedback["text"].strip()
        assert any(node["attrs"].get("role") == "alert" and markup.visible(node)
                   for node in markup.nodes)
        raw = page.encode()
    assert active.path.read_bytes() == before and active.execution is None


def test_opponent_only_and_pending_snapshot_use_one_projection_per_page(
    localized_server, monkeypatch,
):
    import skatmind.app_web.session_recorded_review_rendering as rows
    import skatmind.app_web.task_first_session_rendering as renderer

    browser = Browser(localized_server)
    record_score_review_game(browser, play_count=2)
    active = localized_server.app_context.managed_stateful.active_session
    calls = []
    real = renderer.project_recorded_session_decisions_v1
    def project(context):
        calls.append(context.document)
        return real(context)
    monkeypatch.setattr(renderer, "project_recorded_session_decisions_v1", project)
    monkeypatch.setattr(rows, "project_recorded_session_decisions_v1", project)
    before = active.path.read_bytes()
    page = browser.page()
    assert calls == [active.document]
    assert text("en", "recorded_review.no_observations") in page
    assert text("en", "recorded_review.no_perspective") not in page
    assert text("en", "recorded_review.no_snapshots") not in page
    assert 'href="#recorded-decisions"' not in page
    view = real(active)
    assert view.local_play_count == 0 and dict(view.unavailable_counts)["pending"] == 1
    assert text("en", "recorded_review.pending", count=1) in page
    assert active.path.read_bytes() == before and active.execution is None


def test_transfer_is_secondary_and_rejected_form_is_exposed_without_import(localized_server):
    browser = Browser(localized_server)
    create_empty(browser, "en")
    follow(browser, browser.submit(Forms(browser.page("/learning")).find("/learning/create"),
                                   collection_name="Synthetic focus collection"))
    app = localized_server.app_context
    source, target = app.managed_stateful.active_match, app.managed_stateful.active_learning
    before, catalog = source.path.read_bytes(), target.corpus.store.document
    page = browser.page("/matches/current")
    def transfer_node(html):
        return next(node for node in Hierarchy(html).nodes
                    if node["attrs"].get("action") == "/matches/transfer-workspace")
    assert not Hierarchy.visible(transfer_node(page))
    assert source.path.read_bytes() == before and target.corpus.store.document is catalog
    form = Forms(page).find("/matches/transfer-workspace")
    assert form["values"]["selection_mode"] == "select_imported"
    status, _, raw = browser.submit(form, selection_mode="invalid")
    assert status == 400
    for locale in ("de", "en"):
        page = follow(browser, browser.submit(Forms(raw.decode()).find("/actions/profile/language"),
                                             language=locale))
        assert Hierarchy.visible(transfer_node(page))
        assert 'role="alert"' in page
        raw = page.encode()
    page = follow(browser, enhanced_switch(browser, page, envelope(
        page, "/matches/transfer-workspace", {}), locale="en"))
    assert Hierarchy.visible(transfer_node(page))  # Validation outranks a closed overlay.
    assert target.corpus.store.document is catalog
    page = follow(browser, browser.submit(Forms(page).find("/matches/transfer-workspace"),
                                          selection_mode="keep_current"))
    assert Hierarchy.visible(transfer_node(page))
    assert target.corpus.store.document.catalog.revision == catalog.catalog.revision + 1
    assert source.path.read_bytes() == before and target.corpus.prepared_artifacts is None
    # A stale target revision is rejected and exposes the actual current native controls.
    status, _, raw = browser.submit(form)
    assert status == 409 and Hierarchy.visible(transfer_node(raw.decode()))


def test_match_observations_preparation_report_and_pass_are_independent(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    page = create_empty(browser, "en")
    active = localized_server.app_context.managed_stateful.active_match
    calls = {"save": 0, "execute": 0}
    def count(name, real):
        def wrapped(*args, **kwargs):
            calls[name] += 1
            return real(*args, **kwargs)
        return wrapped
    monkeypatch.setattr(match_context, "save_match_workspace_file_v1",
        count("save", match_context.save_match_workspace_file_v1))
    monkeypatch.setattr(match_analysis, "execute_match_decision_analysis_v1",
        count("execute", match_analysis.execute_match_decision_analysis_v1))
    page = follow(browser, browser.submit(primary(page, "start_game")))
    # Genuine missing-declaration blocker: started is not play-complete.
    assert active.workspace.slots[0].observed_game.declaration is None
    assert 'href="/matches/review/1"' not in page.split('<section id="match-games"')[0]
    page = declare(browser, page)
    for card in ("CK", "C7", "C10"):
        page = follow(browser, browser.submit(primary(page, "append_plays"), cards=card))
    assert calls == {"save": 5, "execute": 0}
    assert text("en", "recordings.match.inspect") in page
    review = browser.page("/matches/review/1")
    assert text("en", "recordings.match.prepared", prepared=0, total=3) in review
    assert text("en", "task.match.decision_blocked") in review
    assert not any(f["values"].get("operation") == "analyze_decision" for f in Forms(review).forms)
    page = browser.page("/matches/position/1")
    page = follow(browser, browser.submit(operation_form(page, "set_perspective_hand"),
        card_evidence_mode="exact", cards=MATCH_HAND))
    assert calls == {"save": 6, "execute": 0}
    assert text("en", "recordings.match.open") in page
    review = browser.page("/matches/review/1")
    assert text("en", "recordings.match.prepared", prepared=1, total=3) in review
    form = operation_form(review, "analyze_decision")
    assert form["values"]["decision_index"] == "2"
    response = browser.submit(form)
    page = follow(browser, response)
    report, = active.capture.report_store.list()
    assert report.value.status == "executed" and calls == {"save": 6, "execute": 1}
    route = response[1]["location"]
    download_route = f"/matches/api/v1/reports/{report.report_id}.json"
    saved, downloaded = active.path.read_bytes(), browser.request("GET", download_route)[2]
    empty = browser.page("/matches/position/2")
    assert 'href="/matches/review/2"' not in empty.split('<section id="match-games"')[0]
    assert active.capture.report_store.list() == (report,)
    page = browser.page(route)
    assert 'href="/matches/position/1#match-recording"' in page
    assert active.selected_position == 1
    assert browser.request("GET", download_route)[2] == downloaded
    page = browser.page("/matches/position/1")
    page = follow(browser, browser.submit(entry_action(page, 3)))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/preview"), card="CA"))
    page = follow(browser, browser.submit(Forms(page).find("/matches/recovery/cancel")))
    assert active.path.read_bytes() == saved and calls == {"save": 6, "execute": 1}
    assert browser.request("GET", download_route)[2] == downloaded
    page = browser.page("/matches/position/2")
    page = follow(browser, browser.submit(primary(page, "mark_passed_deal")))
    assert active.selected_position == 2 and active.workspace.slots[1].slot_kind == "passed_deal"
    assert calls == {"save": 7, "execute": 1}
    assert 'href="/matches/review/2"' not in page.split('<section id="match-games"')[0]
