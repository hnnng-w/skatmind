from fractions import Fraction

import pytest
from test_event_context_web import activate_match, create_context
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

from skatmind.accounting_store import ACCOUNTING_FILENAME, load_accounting
from skatmind.api.v1.session import SessionPlayerV1
from skatmind.app_web.accounting_rendering import render_accounting
from skatmind.app_web.session_frontend import create_guided_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.event_context_store import EVENT_CONTEXT_FILENAME
from skatmind.mode_accounting import STANDARD_RULE, component_totals


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def activate_session(app, identity="synthetic-cent-one", ids=("a", "b", "c")):
    active = create_guided_session_v1(app.managed_stateful.root("sessions"),
        handle="b" * 64, session_id=identity, players=tuple(SessionPlayerV1(
            player_id=player, player_label=label, seat=seat) for player, label, seat in zip(
                ids, ("Alice", "Bob", "Carol"),
                ("forehand", "middlehand", "rearhand"), strict=True)),
        capture_mode="live", local_player_id=ids[0])
    app.managed_stateful.activate_session(active)
    return active


def start(browser):
    return follow(browser, browser.submit(Forms(browser.page()).find("/sessions/accounting/start"),
        round_name="Synthetic round", cent_tariff="1/2", confirm_terms="yes",
        provenance="Synthetic actual table conditions"))


def game_form(page, number):
    return next(form for form in Forms(page).forms if form["action"] == "/sessions/accounting/game"
                and form["values"].get("position") == str(number))


def open_form(page, number):
    return next(form for form in Forms(page).forms if form["action"] == "/sessions/accounting/open"
                and form["values"].get("position") == str(number)
                and "round_id" not in form["values"])


@pytest.mark.parametrize("locale", ["en", "de"])
def test_three_sessions_reopen_next_round_native_forms_and_exact_immutable_history(
        localized_server, locale, monkeypatch):
    app = localized_server.app_context
    first = activate_session(app)
    original = first.path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Accounting must not run Card analysis")
    monkeypatch.setattr("skatmind.app_web.execution.execute_guided_frontend_analysis_v1", forbidden)
    browser = Browser(localized_server)
    page = switch(browser, browser.page(), locale)
    assert text(locale, "accounting.title") in page
    assert not (app.managed_home.root / ACCOUNTING_FILENAME).exists()
    page = start(browser)
    for number, settlement in ((1, "23"), (2, "-46"), (3, "100")):
        if number != 1:
            page = follow(browser, browser.submit(open_form(page, number),
                source_choice="new", provenance="Actual next game"))
        page = follow(browser, browser.submit(game_form(page, number), game_status="settled",
            declarer="1", settlement=settlement, provenance="Actual signed result"))
    journal = load_accounting(app.managed_home.root)
    row = journal.round_heads[0]
    assert len(row.context.bindings) == 3
    assert len({b.source.product_id for b in row.context.bindings}) == 3
    assert row.game(1)[1][1].gross.value == Fraction(-23, 200)
    assert row.game(2)[1][1].net is None
    assert row.game(3)[1][0].fee.value == Fraction(3, 100)
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
        status="finished", provenance="Three recorded positions; provider completion unknown"))
    before = (app.managed_home.root / ACCOUNTING_FILENAME).read_bytes()
    browser.page()
    assert (app.managed_home.root / ACCOUNTING_FILENAME).read_bytes() == before
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
        status="open", provenance="Explicit isolated correction"))
    page = follow(browser, browser.submit(game_form(page, 1), settlement="24",
        reconciliation="Corrected actual result", provenance="Corrected receipt"))
    corrected = load_accounting(app.managed_home.root)
    assert corrected.rounds[:len(journal.rounds)] == journal.rounds
    assert corrected.round_heads[0].game(1)[1][0].gross.value == Fraction(24, 100)
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
        status="finished", actual_complete="yes", personal_net="0.735", net_scope="block",
        provenance="Actual personal block receipt, not funding"))
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/next"),
        round_name="Synthetic next round", continuing_terms="yes", provenance="Same actual table"))
    heads = load_accounting(app.managed_home.root).round_heads
    assert len(heads) == 2 and heads[1].previous_round_id == heads[0].identity
    assert heads[1].context.participant_ids == heads[0].context.participant_ids
    assert heads[1].game(1)[0] == "unfinished"
    assert first.path.read_bytes() == original
    assert not (app.managed_home.root / "automatic-learning").exists()
    assert not (app.managed_home.root / EVENT_CONTEXT_FILENAME).exists()
    assert text(locale, "accounting.title") in page


def test_tournament_confirmed_checkpoint_legacy_overlap_and_known_components(localized_server):
    app = localized_server.app_context
    active = activate_match(app)
    original = active.path.read_bytes()
    browser = Browser(localized_server)
    create_context(browser, entry_paid="2", entry_committed="5", currency="EUR",
                   financial_provenance="Old values with no overlap meaning")
    context_bytes = (app.managed_home.root / EVENT_CONTEXT_FILENAME).read_bytes()
    page = browser.page("/matches/position/26")
    form = Forms(page).find("/matches/accounting/save")
    values = dict(rule=STANDARD_RULE, rule_from_position="25",
        table_total="1.25", table_paid="0.75",
        entry_overlap="committed_is_total", plus_level="2", provenance="Confirmed Standard from 25")
    bad = browser.submit(form, **{**values, "entry_overlap": ""})
    assert bad[0] == 400
    retained = Forms(bad[2].decode()).find("/matches/accounting/save")
    assert retained["values"]["table_total"] == "1.25"
    page = follow(browser, browser.submit(retained, **values))
    row = load_accounting(app.managed_home.root).tournament_heads[0]
    assert row.prepared.personal_points == 820 and row.prepared.own_losses == 3
    assert component_totals(row.components) == (Fraction(-25, 4), None)
    assert next(c for c in row.components if c.kind == "additional_losses").value.value == 0
    page = follow(browser, browser.submit(Forms(page).find("/matches/accounting/save"),
        base_receipt="0", receipts_complete="yes", earlier_losses="1.5", earlier_paid="1.5"))
    row = load_accounting(app.managed_home.root).tournament_heads[0]
    assert component_totals(row.components) == (Fraction(-31, 4), Fraction(-31, 4))
    assert active.path.read_bytes() == original
    assert (app.managed_home.root / EVENT_CONTEXT_FILENAME).read_bytes() == context_bytes


def test_stale_forms_preserved_safe_language_and_changed_table_identity(localized_server):
    app = localized_server.app_context
    activate_session(app)
    browser = Browser(localized_server)
    page = start(browser)
    stale = game_form(page, 1)
    bad = browser.submit(stale, game_status="settled", settlement="bad", declarer="1",
                         provenance="Known actual result")
    assert bad[0] == 400 and 'role="alert"' in bad[2].decode()
    page = switch(browser, bad[2].decode(), "de")
    assert game_form(page, 1)["values"]["settlement"] == "bad"
    page = follow(browser, browser.submit(game_form(page, 1), settlement="23"))
    assert browser.submit(stale, game_status="passed", provenance="Old form")[0] == 409
    activate_session(app, "changed-table", ("a", "d", "e"))
    start(browser)
    heads = load_accounting(app.managed_home.root).round_heads
    assert len(heads) == 2 and heads[0].table_id != heads[1].table_id


def test_passed_incomplete_interruption_adjustment_and_reopen(localized_server):
    app = localized_server.app_context
    activate_session(app)
    browser = Browser(localized_server)
    page = start(browser)
    page = follow(browser, browser.submit(game_form(page, 1), game_status="passed",
                                         provenance="Actually passed deal"))
    assert browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
                          status="finished", provenance="Incomplete block")[0] == 400
    page = browser.page()
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
        status="interrupted", provenance="External game interrupted"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.game(1)[0] == "passed" and row.game(2)[0] == "missing" and row.adjustment is None
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
        status="open", adjustment="-1.25", adjustment_provenance="Actual external charge receipt",
        provenance="Reopen with separately observed external charge"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.adjustment.amount.value == Fraction(-5, 4)
    assert "<script" not in render_accounting(app,
        app.managed_stateful.active_session, "sessions", "en")


def test_saved_source_attachment_mapping_noop_and_terms_correction(localized_server):
    from skatmind.app_web.accounting_frontend import choice_key, session_choices

    app = localized_server.app_context
    other = activate_session(app, "alias-session", ("x", "y", "z"))
    activate_session(app)
    browser = Browser(localized_server)
    page = start(browser)
    entry = next(e for e in session_choices(app)
                 if e.summary.semantic_product_id == "alias-session")
    before = other.path.read_bytes()
    page = follow(browser, browser.submit(open_form(page, 2), source_choice=choice_key(entry),
        map_1="1", map_2="2", map_3="3", provenance="Same actual people, explicit source mapping"))
    page = follow(browser, browser.submit(game_form(page, 2), game_status="settled",
        declarer="1", settlement="100", provenance="Actual result"))
    path = app.managed_home.root / ACCOUNTING_FILENAME
    saved = path.read_bytes()
    page = follow(browser, browser.submit(game_form(page, 2)))
    assert path.read_bytes() == saved
    page = follow(browser, browser.submit(Forms(page).find("/sessions/accounting/lifecycle"),
        cent_tariff="1", from_position="2", change_kind="later",
        provenance="Actual changed tariff"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.context.applicable_terms(1).financial.cent_tariff == "1/2"
    assert row.context.applicable_terms(2).financial.cent_tariff == "1"
    assert row.game(2)[1][0].gross.value == 2
    assert other.path.read_bytes() == before
    # An old round remains available through normal source navigation after restart.
    from skatmind.app_web.context import AppWebContextV1
    restarted = AppWebContextV1.create(app.managed_home)
    assert load_accounting(restarted.managed_home.root).round_heads[0] == row


def test_confirmed_plus_rule_and_unknown_policy_are_independent_of_prizes(localized_server):
    app = localized_server.app_context
    activate_match(app)
    browser = Browser(localized_server)
    page = create_context(browser)
    page = follow(browser, browser.submit(Forms(page).find("/matches/accounting/save"),
        table_rule="published_plus", plus_level="2", table_paid="0", provenance="Actual Plus 2"))
    row = load_accounting(app.managed_home.root).tournament_heads[0]
    assert next(o for o in row.obligations if o.kind == "table").total.numerator == 5
    assert next(c for c in row.components if c.kind == "table").value.value == Fraction(-5, 4)
    assert next(c for c in row.components if c.kind == "additional_losses").value is None


def test_accounting_preserves_genuine_reports_and_independent_collection(localized_server):
    from skatmind.app_web.cross_area_transfer import transfer_active_match_workspace_to_corpus_v1
    from skatmind.app_web.learning_frontend import create_unified_learning_corpus_v1
    from skatmind.app_web.match_frontend import (
        build_unified_match_report_download_v1,
        execute_unified_match_analysis_v1,
    )

    app = localized_server.app_context
    active = activate_match(app)
    corpus = create_unified_learning_corpus_v1(app.managed_stateful.root("corpora"),
        handle="c" * 64, corpus_id="independent-synthetic-accounting")
    transfer_active_match_workspace_to_corpus_v1(active, corpus,
        selection_mode="select_imported", same_revision_resolution="reject",
        expected_catalog_revision=0)
    root = app.managed_stateful.root("corpora")
    independent = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    analyzed = execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "25",
        "expected_revision": str(active.workspace.revision), "decision_index": "28",
        "immediate_sample_count": "1"})
    report_id = analyzed.state["selected_report_id"]
    retained = tuple(build_unified_match_report_download_v1(active, report_id,
        strategy_source=value) for value in (False, True))
    browser = Browser(localized_server)
    page = create_context(browser)
    follow(browser, browser.submit(Forms(page).find("/matches/accounting/save"),
        rule=STANDARD_RULE, entry_total="5", table_total="0.75",
        provenance="Actual synthetic obligations"))
    assert retained == tuple(build_unified_match_report_download_v1(active, report_id,
        strategy_source=value) for value in (False, True))
    assert independent == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
