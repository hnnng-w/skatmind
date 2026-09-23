"""Destination captions: scalar characterization plus genuine returned-form sources."""
from collections import Counter
from html import escape
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from test_frontend_language_switching import localized_server as _server
from test_match_recording_recovery_web import follow, operation_form
from test_recorded_decision_context_web import record_context_match, record_second_context_game
from test_session_recorded_review_web import Browser, Forms

import skatmind.capture_web.analysis as analysis
import skatmind.capture_web.context as capture
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1 as canonical
from skatmind.app_web.match_report_rendering import render_match_reports_v1
from skatmind.app_web.match_review_rendering import render_match_review_v1
from skatmind.app_web.session_recorded_review_rendering import render_recorded_review_source_v1
from skatmind.app_web.task_first_match_state import build_task_first_match_page_state_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1


class Links(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.links = []
        self.current = None
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = {**dict(attrs), "text": ""}
            self.links.append(self.current)

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "a":
            self.current = None


def assert_link(page, href, label):
    links = [link for link in Links(page).links if link.get("href") == href]
    assert links and all(link["text"] == label for link in links), links
    assert all(link.get("aria-label", label) == label for link in links)


def assert_session_return(page, locale):
    label = ("Zur Entscheidungsauswahl: Stich 4, Karte 3" if locale == "de" else
             "Decision selection: Trick 4, Card 3")
    assert_link(page, "#recorded-decision-12", label)
    assert_link(page, "#recorded-decisions", "Zur Auswahl erfasster Entscheidungen"
                if locale == "de" else "Recorded decision selection")
    assert 'id="recorded-decision-12"' in page
    assert 'id="session-result" tabindex="-1"' in page


@pytest.mark.parametrize("locale", ("de", "en"))
def test_scalar_source_caption_uses_retained_trick_and_card(locale):
    # Explicit renderer characterization, not a fabricated successful execution.
    name = 'A <&> "' + "Long player name " * 8
    checkpoint = SimpleNamespace(decision_index=12, trick_number=4, play_index=3,
                                 acting_player_id="a")
    source = SimpleNamespace(decision=SimpleNamespace(checkpoint=checkpoint,
        observation=SimpleNamespace(actual_card="SJ")), document=SimpleNamespace(
            state=SimpleNamespace(players=(SimpleNamespace(player_id="a", player_label=name),))))
    context = SimpleNamespace(recorded_review_source=source)
    page = render_recorded_review_source_v1(context, locale=locale, game_label='<Game & "name">')
    assert_link(page, "#recorded-decision-12", "Zur Entscheidungsauswahl: Stich 4, Karte 3"
                if locale == "de" else "Decision selection: Trick 4, Card 3")
    assert escape(name) in page and escape('<Game & "name">') in page
    assert name not in page and "SJ" in page
    context.recorded_review_source = None
    assert render_recorded_review_source_v1(context, locale=locale, game_label="Game") == ""


@pytest.mark.parametrize("locale", ("de", "en"))
def test_report_link_uses_its_captured_owner_and_neutral_missing_location(locale):
    reports = [dict(report_id=str(index), report_kind="decision_analysis", match_position=1,
                    decision_index=decision) for index, decision in enumerate((2, 12, None))]
    state = dict(reports=reports, selected_position=1, selected_report=None)
    page = render_match_reports_v1(state, locale)
    base = ("Vorhandene Auswertung öffnen: Spiel 1" if locale == "de" else
            "Open existing analysis: Game 1")
    assert_link(page, "/matches/reports/0", base + (" — Stich 1, Karte 2" if locale == "de"
                                                  else " — Trick 1, Card 2"))
    assert_link(page, "/matches/reports/1", base + (" — Stich 4, Karte 3" if locale == "de"
                                                  else " — Trick 4, Card 3"))
    assert_link(page, "/matches/reports/2", base)
    # Other Report kinds and their existing absence of a Game sub-location stay neutral.
    state["reports"] = [dict(report_id="historical", report_kind="historical_analysis",
                            match_position=1), dict(report_id="materialization",
                            report_kind="materialization", match_position=None)]
    other = render_match_reports_v1(state, locale)
    assert "Open existing analysis" not in other and "Vorhandene Auswertung öffnen" not in other
    assert len(Links(other).links) == 2


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


def test_real_match_links_keep_game_report_identity_and_bytes(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_context_match(browser, names=('B <&> "' + "Long " * 20, "C", "A"))
    record_second_context_game(browser)
    active = localized_server.app_context.managed_stateful.active_match
    # Passed Game 2 is established before analysis so it cannot invalidate the Reports.
    follow(browser, browser.submit(operation_form(browser.page("/matches/position/2"),
                                                  "mark_passed_deal")))
    for number in (4, 1):
        follow(browser, browser.submit(operation_form(browser.page(
            f"/matches/review/{number}"), "analyze_decision")))
    other, report = active.capture.report_store.list()
    assert (other.decision_index, report.decision_index) == (2, 2)
    source = active.path.read_bytes()
    reports = canonical([r.to_dict() for r in active.capture.report_store.list()])
    routes = {r.report_id: f"/matches/api/v1/reports/{r.report_id}.json" for r in (other, report)}
    downloads = {key: browser.request("GET", route)[2] for key, route in routes.items()}
    calls = Counter()
    for module, name, key in ((analysis, "execute_match_decision_analysis_v1", "execute"),
                              (capture, "save_match_workspace_file_v1", "save")):
        real = getattr(module, name)
        def counted(*args, _real=real, _key=key, **kwargs):
            calls[_key] += 1
            return _real(*args, **kwargs)
        monkeypatch.setattr(module, name, counted)
    for locale in ("de", "en"):
        follow(browser, browser.submit(Forms(browser.page("/matches/review/1")).find(
            "/actions/profile/language"), language=locale))
        for number in (1, 2, 3, 4):
            page = browser.page(f"/matches/review/{number}")
            back = f"/matches/position/{number}#match-recording"
            assert_link(page, back, f"Zur Erfassung: Spiel {number}" if locale == "de"
                        else f"Recording: Game {number}")
            assert_link(page.split('<main', 1)[1], "/review/recorded",
                        "Andere Aufzeichnung auswählen" if locale == "de" else
                        "Choose another recording")
            recording = browser.page(back.split("#")[0])
            assert 'id="match-recording"' in recording
            if number in (2, 3):
                assert f'href="/matches/review/{number}"' not in recording
                continue
            assert_link(recording, f"/matches/review/{number}",
                f"Zur Entscheidungsauswahl: Spiel {number}" if locale == "de" else
                f"Decision selection: Game {number}")
            owner = report if number == 1 else other
            assert_link(page, f"/matches/reports/{owner.report_id}",
                f"Vorhandene Auswertung öffnen: Spiel {number} — Stich 1, Karte 2"
                if locale == "de" else f"Open existing analysis: Game {number} — Trick 1, Card 2")
            form = operation_form(page, "analyze_decision")
            assert form["action"] == "/matches/api/v1/analysis"
            assert ("Erfasste Entscheidung analysieren" if locale == "de" else
                    "Analyze recorded decision") in page
        # Actual typed snapshot, with Game 2 selected and Game-1 Report still displayed.
        with active.capture.lock:
            view = project_task_first_match_v1(active.workspace, selected_position=2)
            state = build_task_first_match_page_state_v1(active, view, report_id=report.report_id)
        page = render_match_review_v1(state, view, managed_handle=active.handle, locale=locale)
        assert_link(page, "/matches/position/2#match-recording", "Zur Erfassung: Spiel 2"
                    if locale == "de" else "Recording: Game 2")
        assert state["decision_context"].game_number == 1
        assert state["decision_context"].play_index == 2
        # A native Report route normally selects that Report's Game; it does not execute.
        page = browser.page(f"/matches/reports/{report.report_id}")
        assert active.selected_position == 1
        assert_link(page, "/matches/position/1#match-recording", "Zur Erfassung: Spiel 1"
                    if locale == "de" else "Recording: Game 1")
        for key, route in routes.items():
            assert browser.request("GET", route)[2] == downloads[key]
    assert not calls and active.path.read_bytes() == source
    assert canonical([r.to_dict() for r in active.capture.report_store.list()]) == reports
