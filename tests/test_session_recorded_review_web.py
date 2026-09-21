from __future__ import annotations

import http.client
import json
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from threading import Event
from urllib.parse import urlencode

import pytest
from test_equal_best_immediate import assert_visible_equal_best
from test_frontend_language_switching import localized_server as _localized_server
from test_guided_frontend_result_presentation import assert_summary_points, score_review_request
from test_historical_game import build_historical_input
from test_recorded_decision_context import SESSION_HAND, assert_context, context_html

import skatmind.api.v1.session.files as session_files
import skatmind.app_web.execution as execution_module
from skatmind.api.v1 import serialize_result
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.historical_game import build_historical_game_summary_from_input


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


class Forms(HTMLParser):
    """Submit native returned controls, including the exact server-owned bindings."""

    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.current = None
        self.select = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {"action": attrs["action"], "values": {}}
            self.forms.append(self.current)
        elif self.current is not None:
            values = self.current["values"]
            if tag == "input" and "name" in attrs and attrs.get("type") != "file":
                if attrs.get("type") not in {"checkbox", "radio"} or "checked" in attrs:
                    name = attrs["name"]
                    value = attrs.get("value", "on" if attrs.get("type") in {
                        "checkbox", "radio"} else "")
                    if attrs.get("type") == "checkbox" and name in values:
                        prior = values[name]
                        values[name] = [*(prior if isinstance(prior, list) else [prior]), value]
                    else:
                        values[name] = value
            elif tag == "select":
                self.select = attrs["name"]
            elif tag == "option" and self.select is not None:
                if self.select not in values or "selected" in attrs:
                    values[self.select] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None
        elif tag == "select":
            self.select = None

    def find(self, action, *, kind=None, index=0):
        return [form for form in self.forms if form["action"] == action
                and (kind is None or form["values"].get("kind") == kind)][index]


class Browser:
    def __init__(self, server):
        self.server = server
        self.cookie = ""
        status, headers, _ = self.request("GET", "/?token=localization-test-token")
        assert status == 303
        self.cookie = headers["set-cookie"].split(";", 1)[0]

    def request(self, method, route, values=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=120)
        supplied = {"Cookie": self.cookie, "Accept-Language": "en"}
        if method == "POST":
            supplied.update({"Origin": self.server.origin,
                             "Content-Type": "application/x-www-form-urlencoded"})
        supplied.update(headers or {})
        body = None if values is None else urlencode(values, doseq=True).encode("ascii")
        try:
            connection.request(method, route, body=body, headers=supplied)
            with connection.getresponse() as response:
                return (response.status, dict((k.lower(), v) for k, v in response.getheaders()),
                        response.read())
        finally:
            connection.close()

    def page(self, route="/sessions/current"):
        status, _, content = self.request("GET", route)
        assert status == 200, (status, content.decode())
        return content.decode()

    def submit(self, form, **overrides):
        return self.request("POST", form["action"], {**form["values"], **overrides})

    def command(self, kind, **values):
        forms = Forms(self.page())
        route = ("/sessions/play" if kind == "record_play" else "/sessions/cards"
                 if kind in {"record_dealt_card", "record_discard"} else None)
        compact = next((form for form in forms.forms if form["action"] == route), None)
        form = compact or forms.find("/sessions/command", kind=kind)
        if compact is not None:
            values["cards"] = values.pop("card")
        if form["values"].get("declaration_form"):
            # Explicit test unchecking removes the native successful control.
            for name in ("hand_game", "ouvert", "schneider_announced", "schwarz_announced"):
                if values.get(name) == "false":
                    values.pop(name)
                    form["values"].pop(name, None)
        status, headers, content = self.submit(form, **values)
        assert status == 303, (status, content.decode())
        assert headers["location"] == "/sessions/current" + (
            "#session-recording" if compact is not None or form["values"].get("declaration_form")
            or form["values"].get("time_form")
            else "")


def record_live_game(browser, *, play_count=6):
    data = build_historical_input(hand_game=True, declarer_player_id="player-a", bid_value=24)
    form = Forms(browser.page("/sessions")).find("/sessions/create")
    status, _, content = browser.submit(
        form, game_name="Synthetic recorded Game", capture_mode="live",
        forehand_name="Alexandra Long-Synthetic-Player-Name", middlehand_name="Boris",
        rearhand_name="Clara", perspective_seat="forehand", setup_action="update",
    )
    assert status == 303, content.decode()
    status, _, content = browser.submit(
        Forms(browser.page("/sessions")).find("/sessions/create"), setup_action="create")
    assert status == 303, content.decode()
    browser.command("set_game_metadata")
    response = browser.submit(Forms(browser.page()).find("/sessions/cards"),
                              cards=data["players"][0]["initial_hand"])
    assert response[0] == 303, response[2].decode()
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="true", bid_value="24")
    plays = [play for trick in data["tricks"] for play in trick["plays"]]
    for play in plays[:play_count]:
        # Complete-deal knowledge chooses legal observed Cards only. Opponent hands
        # and Skat are never submitted, nor is any Checkpoint injected.
        browser.command("record_play", card=play["card"])
    return data, plays


def review_first(browser):
    page = browser.page()
    form = Forms(page).find("/sessions/review-decision")
    assert set(form["values"]) == {
        "managed_handle", "expected_revision", "decision_selection", "_frontend_form_instance",
    }
    status, headers, content = browser.submit(form)
    assert status == 303, (status, content.decode())
    assert headers["location"] == "/sessions/current#session-result"
    page = browser.page()
    assert 'id="session-result"' in page
    assert "Synthetic recorded Game" in page
    assert "Alexandra Long-Synthetic-Player-Name" in page
    assert 'class="recorded-review-source"' in page
    return page, form


def record_score_review_game(browser, *, play_count=12, names=("B", "C", "A")):
    """Legally record R09 with a fixed independently counted 42/78 synthetic suffix.

    Fixture IDs follow the generator's seat order; visible Players are B, C, A.
    Only A's hand and observed Plays are submitted to the perspective recording.
    """
    local_hand = ["CA", "C10", "CJ", "SA", "SK", "SJ", "HA", "H9", "DK", "D7"]
    data = build_historical_input(declarer_player_id="player-a", deck=[
        "S9", "H7", "CK", "S7", "H10", "HJ", "CQ", "C9", "HQ", "D10",
        "C7", "S10", "HK", "DJ", "C8", "SQ", "S8", "H8", "DQ", "D9",
        *local_hand, "DA", "D8",
    ])
    prefix = (
        (("player-a", "CK"), ("player-b", "C7"), ("player-c", "CA")),
        (("player-c", "SK"), ("player-a", "S7"), ("player-b", "S10")),
        (("player-b", "HK"), ("player-c", "H9"), ("player-a", "H10")),
        (("player-a", "HJ"), ("player-b", "DJ"), ("player-c", "SJ")),
        # A wins 14 and 11; B wins 11; A wins 10; B wins 17; A wins 8.
        # B's complete recorded total is 14 + 11 + 17 = 42 (three Tricks).
        (("player-c", "HA"), ("player-a", "HQ"), ("player-b", "H8")),
        (("player-c", "SA"), ("player-a", "D8"), ("player-b", "S8")),
        (("player-c", "D7"), ("player-a", "DA"), ("player-b", "D9")),
        (("player-a", "C9"), ("player-b", "C8"), ("player-c", "C10")),
        (("player-c", "DK"), ("player-a", "D10"), ("player-b", "DQ")),
        (("player-a", "CQ"), ("player-b", "SQ"), ("player-c", "CJ")),
    )
    data["tricks"] = [
        {"trick_number": index, "leader_player_id": trick[0][0],
         "plays": [{"player_id": player, "card": card} for player, card in trick]}
        for index, trick in enumerate(prefix, 1)
    ]
    assert build_historical_game_summary_from_input(data)["status"] == "complete"
    form = Forms(browser.page("/sessions")).find("/sessions/create")
    assert browser.submit(form, game_name="Synthetic score review", capture_mode="live",
        forehand_name=names[0], middlehand_name=names[1], rearhand_name=names[2],
        perspective_seat="rearhand",
        setup_action="update")[0] == 303
    assert browser.submit(Forms(browser.page("/sessions")).find("/sessions/create"),
                          setup_action="create")[0] == 303
    browser.command("set_game_metadata")
    assert browser.submit(Forms(browser.page()).find("/sessions/cards"), cards=local_hand)[0] == 303
    browser.command("set_declarer")
    browser.command("set_declaration", game_type="grand", hand_game="false",
                    bid_value="18")
    plays = [play for trick in data["tricks"] for play in trick["plays"]]
    for play in plays[:play_count]:
        browser.command("record_play", card=play["card"])
    return plays


def score_review_form(browser):
    # A's fourth saved own decision is Trick 4, Card 3 (SJ).
    return Forms(browser.page()).find("/sessions/review-decision", index=3)


def test_real_score_review_after_later_plays_completion_reopen_and_passive_views(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    plays = record_score_review_game(browser, play_count=11)
    context = localized_server.app_context.managed_stateful.active_session
    calls, saves = [], []
    real_execute, real_save = execution_module.execute, session_files.save_session_file
    def execute(request, **kwargs):
        calls.append(request)
        return real_execute(request, **kwargs)
    def save(*args, **kwargs):
        saves.append(args)
        return real_save(*args, **kwargs)
    monkeypatch.setattr(execution_module, "execute", execute)
    monkeypatch.setattr(session_files, "save_session_file", save)

    # The same projection is also used by genuine current-position Session analysis.
    assert browser.submit(Forms(browser.page()).find("/sessions/analyze"))[0] == 303
    assert_summary_points(browser.page(), "en", 14, 29)
    assert len(calls) == 1 and context.recorded_review_source is None
    browser.command("record_play", card="SJ")
    assert context.execution is None

    def review_and_check():
        from test_hand_evidence_labels import hand_row, overview_html
        from test_recorded_party_presentation import assert_party_score, history_rows
        from test_recording_task_focus import Hierarchy

        form = score_review_form(browser)
        before = context.path.read_bytes()
        checkpoints = context.decision_checkpoints
        profile = localized_server.app_context.frontend_profile
        count, save_count = len(calls), len(saves)
        status, headers, _ = browser.submit(form)
        assert status == 303 and headers["location"] == "/sessions/current#session-result"
        assert len(calls) == count + 1 and len(saves) == save_count
        page = browser.page()
        markup = Hierarchy(page)
        assert markup.visible(markup.by_id("session-result"))
        assert not any(parent["tag"] == "details"
                       for parent in markup.by_id("session-result")["parents"])
        source = page.split('class="recorded-review-source"', 1)[1].split("</p>", 1)[0]
        assert "Synthetic score review" in source and "Trick 4 · Card position 3" in source
        assert "SJ" in source
        assert_summary_points(page, "en", 14, 29)
        ended = context.state.phase == "ended"
        assert_party_score(page, (42, 3) if ended else (14, 1),
                           (78, 7) if ended else (35, 3))
        assert len(history_rows(page)) == (30 if ended else 12)
        assert_visible_equal_best(page, "en")
        assert_context(page, "en", hand=SESSION_HAND, prefix=(("B", "HJ"), ("C", "DJ")),
                       actor="A", trick=4, play=3)
        execution, source = context.execution, context.recorded_review_source
        frozen = source.decision.checkpoint.request.to_dict()["document"]
        request_bytes = browser.request("GET", "/sessions/downloads/request.json")[2]
        result_bytes = browser.request("GET", "/sessions/downloads/result.json")[2]
        assert request_bytes == execution.request_json_bytes
        assert result_bytes == execution.result_json_bytes
        request = json.loads(request_bytes)
        assert request == {
            **frozen, "analysis_mode": "post_game_review", "actual_card_played": "SJ"}
        expected = score_review_request()
        for key in ("current_trick", "completed_tricks", "declarer_points", "defender_points"):
            assert request[key] == expected[key]
        result = execution.result.result.document
        assert result["position"]["declarer_points"] == result["position"]["defender_points"] == 0
        assert result["score_summary"]["total_declarer_points"] == 14
        assert result["score_summary"]["total_defender_points"] == 29
        assert result["recommendation"]["card"] == "CJ"
        assert "equally best" in result["recommendation"]["reason"]
        assert "equally best" in result["strategic_summary"]
        assert [row["expected_point_swing"] for row in result["analysis_report"]] == [6.0, 6.0]
        assert [row["is_recommended"] for row in result["analysis_report"]] == [True, False]
        review = result["post_game_review_summary"]
        assert (review["recommended_card_rank"], review["actual_card_rank"]) == (1, 2)
        assert review["decision_quality"] == "optimal"
        assert review["better_card_count"] == review["expected_point_swing_difference"] == 0
        assert json.loads(result_bytes) == serialize_result(execution.result)

        # Same-source chooser navigation preserves the exact active Result, unlike strict reopen.
        browser.page("/")
        chooser = Forms(browser.page("/review/recorded")).find("/review/open-recording")
        assert browser.submit(chooser)[0] == 303
        assert localized_server.app_context.frontend_profile is profile
        for locale in ("de", "en"):
            language = Forms(browser.page()).find("/actions/profile/language")
            status, headers, _ = browser.submit(language, language=locale)
            assert status == 303 and headers["location"] == "/sessions/current#session-result"
            assert_summary_points(browser.page(), locale, 14, 29)
            assert_party_score(browser.page(), (42, 3) if ended else (14, 1),
                               (78, 7) if ended else (35, 3))
            assert 'data-operation-feedback ' not in browser.page()
            assert_visible_equal_best(browser.page(), locale)
            assert_context(browser.page(), locale, hand=SESSION_HAND,
                            prefix=(("B", "HJ"), ("C", "DJ")), actor="A", trick=4, play=3)
            overview = overview_html(browser.page())
            assert text(locale, "task.session.remaining_hands") in overview
            assert overview.count(text(locale, "task.session.hand_unknown")) == 2
            if ended:
                assert text(locale, "task.session.hand_empty") in hand_row(overview, 3)
            assert browser.request("GET", "/sessions/downloads/request.json")[2] == request_bytes
            assert browser.request("GET", "/sessions/downloads/result.json")[2] == result_bytes
        assert len(calls) == count + 1 and len(saves) == save_count
        assert context.path.read_bytes() == before
        assert context.decision_checkpoints is checkpoints
        assert source.decision.checkpoint.request.to_dict()["document"] == frozen
        assert context.execution is execution and context.recorded_review_source is source
        return request_bytes, form

    earlier_request, earlier_form = review_and_check()
    for play in plays[12:]:
        browser.command("record_play", card=play["card"])
    assert context.state.phase == "play"
    assert Forms(browser.page()).find("/sessions/command", kind="set_game_end")
    browser.command("set_game_end")
    assert context.state.phase == "ended" and context.execution is None
    assert len(context.decision_checkpoints) == 10
    assert context.state.validation.position_export.status == "unavailable"
    assert context.state.validation.historical_export.status == "unavailable"
    assert browser.submit(earlier_form)[0] == 409
    assert browser.request("GET", "/sessions/downloads/result.json")[0] == 404
    ended_request, ended_form = review_and_check()
    assert ended_request == earlier_request
    saved, checkpoints = context.path.read_bytes(), context.decision_checkpoints
    assert browser.submit(Forms(browser.page("/sessions")).find("/sessions/open"))[0] == 303
    context = localized_server.app_context.managed_stateful.active_session
    assert context.execution is context.recorded_review_source is None
    assert context.decision_checkpoints == checkpoints
    assert browser.submit(ended_form)[0] == 409
    reopened_request, _ = review_and_check()
    assert reopened_request == earlier_request and context.path.read_bytes() == saved
    assert len(calls) == 4


def test_real_http_record_review_all_30_plays_reopen_and_exact_downloads(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    calls = []
    real_execute = execution_module.execute
    def counted(request, **kwargs):
        calls.append(request)
        return real_execute(request, **kwargs)
    monkeypatch.setattr(execution_module, "execute", counted)
    _, plays = record_live_game(browser)
    context = localized_server.app_context.managed_stateful.active_session
    profile = localized_server.app_context.frontend_profile
    original = context.path.read_bytes()
    frozen = context.decision_checkpoints[0].request.to_dict()["document"]
    page, early_form = review_first(browser)
    assert len(calls) == 1
    assert "Trick 1 · Card position 1 · Actual Card" in page
    assert "Recommended Card" in page and "Decision quality" in page
    assert context.path.read_bytes() == original
    request_bytes = browser.request("GET", "/sessions/downloads/request.json")[2]
    result_bytes = browser.request("GET", "/sessions/downloads/result.json")[2]
    assert request_bytes == context.execution.request_json_bytes
    assert result_bytes == context.execution.result_json_bytes
    assert json.loads(result_bytes) == serialize_result(context.execution.result)
    assert json.loads(request_bytes) == {
        **frozen, "analysis_mode": "post_game_review", "actual_card_played": plays[0]["card"],
    }
    browser.page()
    assert len(calls) == 1 and context.path.read_bytes() == original

    for play in plays[6:]:
        browser.command("record_play", card=play["card"])
    assert context.execution is context.recorded_review_source is None
    # All 30 Plays are recorded; neither promotion nor full original evidence is required.
    assert context.state.capture_mode == "live"
    assert context.state.validation.historical_export.status == "unavailable"
    assert len([record for record in context.state.command_log
                if record.command.kind == "record_play"]) == 30
    assert len(context.decision_checkpoints) >= 10
    original = context.path.read_bytes()
    assert browser.submit(early_form)[0] == 409
    assert len(calls) == 1
    page, _ = review_first(browser)
    assert len(calls) == 2
    assert "10 of 10 recorded own Plays" in page
    assert "Full Historical review is unavailable" in page
    assert browser.request("GET", "/sessions/downloads/request.json")[2] == request_bytes
    assert context.path.read_bytes() == original
    browser.command("set_game_end")
    assert context.state.phase == "ended"
    page, last_form = review_first(browser)
    assert len(calls) == 3 and "10 of 10 recorded own Plays" in page
    saved = context.path.read_bytes()
    assert browser.request("GET", "/sessions/downloads/session.json")[2] == saved

    open_form = Forms(browser.page("/sessions")).find("/sessions/open")
    assert browser.submit(open_form)[0] == 303
    reopened = localized_server.app_context.managed_stateful.active_session
    assert reopened is not context and reopened.execution is reopened.recorded_review_source is None
    assert reopened.decision_checkpoints == context.decision_checkpoints
    assert browser.request("GET", "/sessions/downloads/result.json")[0] == 404
    assert browser.submit(last_form)[0] == 409 and len(calls) == 3
    assert reopened.execution is reopened.recorded_review_source is None
    review_first(browser)
    assert len(calls) == 4
    assert browser.request("GET", "/sessions/downloads/request.json")[2] == request_bytes
    assert reopened.path.read_bytes() == saved
    assert localized_server.app_context.frontend_profile is profile
    assert localized_server.app_context.managed_stateful.active_match is None
    assert localized_server.app_context.managed_stateful.active_learning is None


def test_http_validation_language_security_and_retained_source(localized_server, monkeypatch):
    browser = Browser(localized_server)
    record_live_game(browser)
    page, form = review_first(browser)
    context = localized_server.app_context.managed_stateful.active_session
    execution, source = context.execution, context.recorded_review_source
    saved = context.path.read_bytes()
    def forbidden(*args, **kwargs):
        raise AssertionError("Passive or rejected actions must not execute")
    monkeypatch.setattr(execution_module, "execute", forbidden)
    for extra in ("actual_card_played", "hand", "request", "sample_count", "random_seed"):
        status, _, body = browser.submit(form, **{extra: "forged"})
        assert status == 400
        html = body.decode()
        assert text("en", "validation.recorded_review.invalid_fields") in html
        assert 'role="alert"' in html
        assert 'name="return_to" value="/sessions/current"' in html
        assert context.execution is execution and context.recorded_review_source is source
    # The rejected source selection and feedback stay in this Session with native language POST.
    language = Forms(html).find("/actions/profile/language")
    status, headers, _ = browser.submit(language, language="de")
    assert status == 303 and headers["location"] == "/sessions/current#session-result"
    german = browser.page()
    assert text("de", "recorded_review.title") in german
    assert text("de", "validation.recorded_review.invalid_fields") in german
    assert 'class="recorded-review-source"' in german
    assert form["values"]["decision_selection"] in german
    assert "Alexandra Long-Synthetic-Player-Name" in german
    assert context.execution is execution and context.recorded_review_source is source
    downloaded = browser.request("GET", "/sessions/downloads/result.json")[2]
    assert downloaded == execution.result_json_bytes
    assert browser.submit(form, decision_selection="f" * 64)[0] == 409
    assert browser.submit(form, decision_selection="unknown")[0] == 400
    for origin in ("null", "https://forged.invalid"):
        assert browser.request("POST", form["action"], form["values"],
                               headers={"Origin": origin})[0] == 403
    assert browser.request("POST", form["action"], form["values"],
                           headers={"Cookie": "wrong"})[0] == 403
    assert context.path.read_bytes() == saved
    assert context.execution is execution and context.recorded_review_source is source


def test_http_external_edit_invalidates_review_download_without_reloading(localized_server):
    browser = Browser(localized_server)
    record_live_game(browser)
    review_first(browser)
    context = localized_server.app_context.managed_stateful.active_session
    document = context.document
    context.path.write_bytes(b"{}\n")
    assert browser.request("GET", "/sessions/downloads/result.json")[0] == 409
    assert context.execution is context.recorded_review_source is None
    assert context.document is document and context.path.read_bytes() == b"{}\n"
    assert 'class="recorded-decision-context"' not in browser.page()


def test_http_out_of_order_different_decisions_keep_newer_label_and_downloads(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    record_live_game(browser)
    forms = Forms(browser.page())
    first_form = forms.find("/sessions/review-decision")
    second_form = forms.find("/sessions/review-decision", index=1)
    entered, release = Event(), Event()
    calls = 0
    original = execution_module.execute
    def execute(request, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            entered.set()
            assert release.wait(30)
        return original(request, **kwargs)
    monkeypatch.setattr(execution_module, "execute", execute)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(browser.submit, first_form)
        assert entered.wait(30)
        assert browser.submit(second_form)[0] == 303
        context = localized_server.app_context.managed_stateful.active_session
        execution, source = context.execution, context.recorded_review_source
        release.set()
        status, _, html = first.result(timeout=30)
    assert status == 409 and calls == 2
    assert context.execution is execution and context.recorded_review_source is source
    assert source.decision.selection == second_form["values"]["decision_selection"]
    source_block = html.decode().split('class="recorded-review-source"', 1)[1].split('</p>', 1)[0]
    assert "Trick 2" in source_block
    situation = context_html(html.decode())
    assert "Trick 2" in situation and "Trick 1" not in situation
    downloaded = browser.request("GET", "/sessions/downloads/request.json")[2]
    assert downloaded == execution.request_json_bytes


def test_http_current_position_and_unavailable_historical_keep_correct_labels(localized_server):
    browser = Browser(localized_server)
    _, plays = record_live_game(browser, play_count=3)
    for play in plays[3:]:
        if any(form["action"] == "/sessions/analyze" for form in Forms(browser.page()).forms):
            break
        browser.command("record_play", card=play["card"])
    page, _ = review_first(browser)
    context = localized_server.app_context.managed_stateful.active_session
    assert context.recorded_review_source is not None
    current_form = Forms(page).find("/sessions/analyze")
    assert browser.submit(current_form)[0] == 303
    assert context.execution.request.document["analysis_mode"] == "live_decision"
    assert context.recorded_review_source is None
    assert 'class="recorded-review-source"' not in browser.page()
    assert 'class="recorded-decision-context"' not in browser.page()
    _, form = review_first(browser)
    retained, source = context.execution, context.recorded_review_source
    status, _, _ = browser.request("POST", "/sessions/review", {
        "managed_handle": form["values"]["managed_handle"],
        "expected_revision": form["values"]["expected_revision"],
    })
    assert status == 400
    assert context.execution is retained and context.recorded_review_source is source


def test_http_no_active_session_rejects_foreign_selection_contextually(
    localized_server, monkeypatch,
):
    browser = Browser(localized_server)
    def forbidden(*args, **kwargs):
        raise AssertionError("An inactive Session cannot execute review")
    monkeypatch.setattr(execution_module, "execute", forbidden)
    status, _, content = browser.request("POST", "/sessions/review-decision", {
        "managed_handle": "a" * 64, "expected_revision": "1", "decision_selection": "b" * 64,
    })
    assert status == 409
    assert 'action="/sessions/create"' in content.decode()
