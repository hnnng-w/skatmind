"""Genuine Historical HTTP execution and separately identified scalar display fixtures."""

import hashlib
import json
import re
from html import escape, unescape
from unittest.mock import patch

import pytest
from test_analysis_download_details import assert_delivery
from test_frontend_language_switching import localized_server as _server
from test_guided_frontend_result_presentation import _execution, _historical_document
from test_guided_frontend_web import ROOT, _multipart, _request
from test_language_switch_context import switch
from test_manual_review_saved_names import snapshot
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

import skatmind.app_web.execution as execution_module
from skatmind.api.v1 import WorkflowV1, serialize_result
from skatmind.app_web.json_transfer import canonical_frontend_json_bytes_v1
from skatmind.app_web.result_presentation import build_result_presentation_v1
from skatmind.app_web.result_rendering import render_result_presentation_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

# Independent approved copy assertions, not translations looked up from the code under test.
COPY = {
    "final_decided": ("Ergebnis steht fest", "Result determined"),
    "currently_decided": ("Nach aktuellem Stand entschieden", "Decided on the current evidence"),
    "final_undecided": (
        "Endstand ohne feststehenden Gewinner", "Final result; winner undetermined"),
    "in_progress": ("Ergebnis noch offen", "Outcome unresolved"),
    "final_adjudicated": ("Durch Regelentscheidung festgestellt", "Determined by adjudication"),
    "unknown_bid_value": ("Nicht prüfbar: Reizwert fehlt", "Cannot assess: bid value missing"),
    "unknown_game_value": (
        "Nicht prüfbar: Spielwert nicht ermittelt", "Cannot assess: game value unavailable"),
    "overbid": ("Überreizt", "Overbid"),
    "not_overbid": ("Nicht überreizt", "Not overbid"),
}

# Captured from genuine pre-catalog-change HTTP execution in both languages.
BASELINE_SHA256 = (
    "cc27919d83201943c934c7d5713a6a8abcd36d1a248b814f9963d5b418141d16",
    "827059c49d1f2181c1a413b734328a65f030494a554c80a3d606047d6487d3d8",
)


def approved(locale, status):
    return COPY[status][0 if locale == "de" else 1]


def summary_cells(page):
    """Read only labelled ordinary Summary cells, never tokens in technical details."""
    summary, = re.findall(
        r'<section aria-labelledby="result-section-1">(.*?)</section>', page, re.S)
    assert "<details" not in summary
    pairs = re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", summary)
    assert len({label for label, _ in pairs}) == len(pairs)
    return {unescape(label): unescape(value) for label, value in pairs}


def completed_grand_request():
    """Supported 30-Play Anna/Bea/Clara Grand: bid 18, D8/D7 discards, 105/15, +72.

    Adapt the repository's legal complete-deal example: Anna declares and leaves
    the Skat, Bea wins the first 15-point Trick, Anna wins the remaining nine.
    This is Request input for real execution, not a constructed Result.
    """
    document = json.loads((ROOT / "examples/historical_grand_normal_completion.json").read_text())
    game = document["historical_game_input"]
    game["game_id"] = "manual-review-status-grand"
    for player, label in zip(game["players"], ("Anna", "Bea", "Clara"), strict=True):
        player["player_label"] = label
    game["declarer_player_id"] = "player-a"
    game["discarded_cards"] = ["D8", "D7"]
    for trick, card in zip(game["tricks"],
                           ("SJ", "SK", "SQ", "S9", "S8", "S7", "HA", "H10", "HK", "HQ"),
                           strict=True):
        next(play for play in trick["plays"] if play["player_id"] == "player-b")["card"] = card
    return document


def import_request(browser, content):
    form = Forms(browser.page("/review")).find("/actions/review/import-json")
    body, kind = _multipart(content, revision=int(form["values"]["revision"]))
    return follow(browser, _request(browser.server, "POST", form["action"], body=body,
        headers={"Cookie": browser.cookie, "Origin": browser.server.origin, "Content-Type": kind}))


def assert_completed_result(state):
    summary = state.latest_successful_result.result.document["historical_game_summary"]
    assert (summary["declarer_points"], summary["defender_points"]) == (105, 15)
    assert summary["winner"] == summary["game_result_summary"]["winner"] == "declarer"
    assert summary["game_result_summary"]["status"] == "final_decided"
    assert summary["overbid_summary"]["status"] == "not_overbid"
    assert summary["final_settlement_summary"]["settlement_score"] == 72
    record = summary["record"]
    assert record["declarer_player_id"] == "player-a"
    assert tuple(p["player_label"] for p in record["players"]) == ("Anna", "Bea", "Clara")
    assert record["declaration"]["bid_value"] == 18
    assert record["discarded_cards"] == ("D8", "D7")
    assert len(summary["derived_tricks"]) == 10


def assert_completed_summary(page, locale):
    cells = summary_cells(page)
    expected = {
        "result.result": approved(locale, "final_decided"),
        "result.overbid": approved(locale, "not_overbid"),
        "guided.declarer_points": "105", "guided.defender_points": "15",
        "result.settlement": "72", "result.winner": text(locale, "task.value.declarer"),
        "task.field.declarer_player_id": "Anna", "result.players": "Anna, Bea, Clara",
    }
    assert {text(locale, key): cells[text(locale, key)] for key in expected} == {
        text(locale, key): value for key, value in expected.items()}


@pytest.fixture
def localized_server(tmp_path):
    yield from _server.__wrapped__(tmp_path)


@pytest.mark.parametrize("locale", ("de", "en"))
def test_genuine_completed_review_delivered_summary_and_retained_bytes(
    localized_server, locale, tmp_path,
):
    browser = Browser(localized_server)
    switch(browser, browser.page("/review"), locale)
    context = localized_server.app_context
    with patch.object(execution_module, "execute", wraps=execution_module.execute) as executed:
        page = import_request(browser, canonical_frontend_json_bytes_v1(completed_grand_request()))
        assert executed.call_count == 0
        page = follow(browser, browser.submit(Forms(page).find("/actions/review/run-imported")))
        assert executed.call_count == 1
        state = context.review_state
        assert_completed_result(state)
        before = (state.request_json_bytes, state.result_json_bytes)
        for name, raw in zip(("request", "result"), before, strict=True):
            (tmp_path / (name + ".json")).write_bytes(raw)
        (tmp_path / "delivered.html").write_text(page, encoding="utf-8")
        assert tuple(hashlib.sha256(raw).hexdigest() for raw in before) == BASELINE_SHA256
        assert state.request_json_bytes == canonical_frontend_json_bytes_v1(
            completed_grand_request())
        assert_completed_summary(page, locale)
        assert state.result_json_bytes == canonical_frontend_json_bytes_v1(
            serialize_result(state.latest_successful_result))
        for current in (locale, "en" if locale == "de" else "de", locale):
            # Explicit profile language save is separate from passive observations.
            page = switch(browser, browser.page("/review"), current)
            assert context.review_state is state
            files = snapshot(context)
            assert_completed_summary(page, current)
            browser.page("/")
            assert_completed_summary(browser.page("/review"), current)
            for name, raw in zip(("request", "result"), before, strict=True):
                assert_delivery(browser, f"/downloads/review/{name}.json", raw,
                                f"skatmind-review-{name}.json")
            assert snapshot(context) == files
            assert context.review_state is state and executed.call_count == 1
        # Deliberate re-import and explicit re-execution, never passive rerunning.
        page = import_request(browser, before[0])
        assert context.review_state.latest_successful_result is None
        assert executed.call_count == 1
        page = follow(browser, browser.submit(Forms(page).find("/actions/review/run-imported")))
        assert executed.call_count == 2
        assert_completed_summary(page, locale)
        assert (context.review_state.request_json_bytes,
                context.review_state.result_json_bytes) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize(("status", "winner"), (
    ("final_decided", "declarer"), ("final_decided", "defenders"),
    ("currently_decided", "declarer"), ("currently_decided", "defenders"),
    ("final_undecided", "undecided"), ("in_progress", "undecided"),
    ("final_adjudicated", "declarer"), ("final_adjudicated", "defenders"),
))
def test_scalar_result_status_copy_and_independent_winning_party(locale, status, winner):
    """Presentation fixture only: no claim that every combination is engine-reachable."""
    document = _historical_document()
    summary = document["historical_game_summary"]
    summary["game_result_summary"].update(status=status, winner=winner)
    summary["winner"] = winner
    execution = _execution(WorkflowV1.HISTORICAL_GAME, document)
    before = serialize_result(execution)
    presentation = build_result_presentation_v1(execution, locale=locale)
    page = render_result_presentation_v1(presentation, locale=locale)
    cells = summary_cells(page)
    assert cells[text(locale, "result.result")] == approved(locale, status)
    assert next(d.value for d in presentation.sections[0].details if d.label == "Winner") == winner
    # Only singular declarer has an existing Winner catalog entry. Plural defenders
    # and undecided retain the existing fallback; they are outside these two families.
    assert cells[text(locale, "result.winner")] == text(locale,
        "task.value.declarer" if winner == "declarer" else "result.technical_value")
    technical = page.split('<details class="technical-details">', 1)[1]
    assert f'<dt>{text(locale, "result.status")}</dt><dd lang="en">{status}</dd>' in technical
    assert f'<dt>{text(locale, "result.result")}</dt>' not in technical
    if winner != "declarer":
        assert f'<dt>{text(locale, "result.winner")}</dt><dd lang="en">{winner}</dd>' in technical
    assert serialize_result(execution) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("status", (
    "unknown_bid_value", "unknown_game_value", "overbid", "not_overbid"))
def test_scalar_overbid_status_copy_without_fallback_duplicate(locale, status):
    """Finite Overbid presentation family, not a calculation fixture."""
    document = _historical_document()
    document["historical_game_summary"]["overbid_summary"]["status"] = status
    execution = _execution(WorkflowV1.HISTORICAL_GAME, document)
    before = serialize_result(execution)
    page = render_result_presentation_v1(build_result_presentation_v1(execution, locale=locale),
                                         locale=locale)
    assert summary_cells(page)[text(locale, "result.overbid")] == approved(locale, status)
    technical = page.split('<details class="technical-details">', 1)[1]
    assert f'<dt>{text(locale, "result.overbid")}</dt>' not in technical
    assert serialize_result(execution) == before


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("status", ("final", "complete", "unknown", "future_<status>&\""))
@pytest.mark.parametrize(("family", "key"), (("game_result_summary", "result.result"),
                                             ("overbid_summary", "result.overbid")))
def test_scalar_existing_statuses_and_escaped_future_fallback(locale, status, family, key):
    """Defensive/legacy presentation fixtures, separate from genuine execution."""
    document = _historical_document()
    document["historical_game_summary"][family]["status"] = status
    page = render_result_presentation_v1(build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, document), locale=locale), locale=locale)
    expected = (text(locale, "task.value.unknown") if status == "unknown" else
                text(locale, "result.value." + status) if status in {"final", "complete"} else
                text(locale, "result.technical_value"))
    assert summary_cells(page)[text(locale, key)] == expected
    if status.startswith("future"):
        technical = page.split('<details class="technical-details">', 1)[1]
        assert f'<dt>{text(locale, key)}</dt><dd lang="en">{escape(status)}</dd>' in technical
        assert status not in page


@pytest.mark.parametrize("locale", ("de", "en"))
@pytest.mark.parametrize("name", ("final_decided", "not_overbid", "unknown"))
def test_scalar_literal_player_name_matching_enum_remains_literal(locale, name):
    document = _historical_document()
    document["historical_game_summary"]["record"]["players"][1]["player_label"] = name
    page = render_result_presentation_v1(build_result_presentation_v1(
        _execution(WorkflowV1.HISTORICAL_GAME, document), locale=locale), locale=locale)
    cells = summary_cells(page)
    assert cells[text(locale, "task.field.declarer_player_id")] == name
    assert cells[text(locale, "result.players")] == (
        f'Alex, {name}, {text(locale, "creation.seat.rearhand")}')
    assert f"<td>{name}</td>" in page  # The separate literal Player table column.
