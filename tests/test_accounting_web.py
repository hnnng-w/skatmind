from dataclasses import replace
from fractions import Fraction

import pytest
from test_event_context_web import activate_match, create_context, native_submit
from test_frontend_language_switching import localized_server as _localized_server
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms

from skatmind.accounting_store import (
    ACCOUNTING_FILENAME,
    append_accounting,
    load_accounting,
    save_accounting,
)
from skatmind.api.v1.session import SessionPlayerV1
from skatmind.app_web.accounting_rendering import render_accounting
from skatmind.app_web.session_frontend import create_guided_session_v1, import_guided_session_v1
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


def start(browser, **values):
    form = Forms(browser.page()).find("/sessions/accounting/start")
    return follow(browser, native_submit(browser, form, cent_tariff="1/2", platform="euroskat",
                                         **values))


def action_fields(form):
    return set(form["values"]) - {
        "managed_handle", "accounting_selection", "_frontend_form_instance"}


def game_form(page, number):
    return next(form for form in Forms(page).forms if form["action"] == "/sessions/accounting/game"
                and form["values"].get("position") == str(number))


def open_form(page, number, *, external=False):
    return next(form for form in Forms(page).forms if form["action"] == "/sessions/accounting/open"
                and form["values"].get("position") == str(number)
                and "round_id" not in form["values"]
                and (form["values"].get("source_choice", "new") != "new") == external)


def result(browser, page, number, value="100", status="won"):
    return follow(browser, native_submit(browser, game_form(page, number), game_status=status,
                                         declarer="1", game_value=value))


def complete_round(browser, page):
    for number in range(1, 4):
        if number > 1:
            page = follow(browser, native_submit(browser, open_form(page, number)))
        page = result(browser, page, number)
    return page


@pytest.mark.parametrize("locale", ["en", "de"])
def test_three_sessions_reuse_rotation_finish_explicit_next_and_immutable_history(
        localized_server, locale, monkeypatch):
    app = localized_server.app_context
    first = activate_session(app)
    original = first.path.read_bytes()
    def forbidden(*args, **kwargs):
        pytest.fail("Accounting must not run Card analysis")
    monkeypatch.setattr("skatmind.app_web.execution.execute_guided_frontend_analysis_v1", forbidden)
    browser = Browser(localized_server)
    page = switch(browser, browser.page(), locale)
    form = Forms(page).find("/sessions/accounting/start")
    assert action_fields(form) == {
        "title", "platform", "cent_tariff"}
    assert form["values"]["title"]
    page = start(browser, title="Edited Cent title")
    for number, value, status in ((1, "23", "won"), (2, "23", "lost"), (3, "100", "won")):
        if number > 1:
            form = open_form(page, number)
            assert action_fields(form) == {
                "position", "source_choice"}
            page = follow(browser, native_submit(browser, form))
        current = app.managed_stateful.active_session.document.state
        assert tuple(p.player_id for p in current.players) == (
            ("a", "b", "c")[number - 1:] + ("a", "b", "c")[:number - 1])
        assert current.local_player_id == "a"
        page = result(browser, page, number, value, status)
    journal = load_accounting(app.managed_home.root)
    row = journal.round_heads[0]
    assert row.context.event_name == "Edited Cent title"
    assert len({b.source.product_id for b in row.context.bindings}) == 3
    assert row.game(1)[1][1].gross.value == Fraction(-23, 200)
    assert row.game(2)[1][0].gross.value == Fraction(-46, 100)
    assert row.game(3)[1][0].fee.value == Fraction(3, 100)
    finish = Forms(page).find("/sessions/accounting/lifecycle")
    assert action_fields(finish) == {"status"}
    page = follow(browser, native_submit(browser, finish))
    finished = load_accounting(app.managed_home.root).round_heads[0]
    assert finished.status == "finished" and not finished.actual_block_complete
    assert finished.net_confirmation is None and finished.adjustment is None
    before = (app.managed_home.root / ACCOUNTING_FILENAME).read_bytes()
    browser.page()
    assert (app.managed_home.root / ACCOUNTING_FILENAME).read_bytes() == before
    page = follow(browser, native_submit(browser,
        Forms(page).find("/sessions/accounting/lifecycle")))
    page = result(browser, page, 1, "24")
    corrected = load_accounting(app.managed_home.root)
    assert corrected.rounds[:len(journal.rounds)] == journal.rounds
    page = follow(browser, native_submit(browser,
        Forms(page).find("/sessions/accounting/lifecycle")))
    next_form = Forms(page).find("/sessions/accounting/next")
    assert "platform" not in next_form["values"]
    assert next_form["values"]["cent_tariff"] == "1/2"
    page = follow(browser, native_submit(browser, next_form))
    heads = load_accounting(app.managed_home.root).round_heads
    assert len(heads) == 2 and heads[1].previous_round_id == heads[0].identity
    assert heads[1].context.participant_ids == heads[0].context.participant_ids
    assert heads[1].context.terms[0].platform == "euroskat"
    assert heads[1].game(1)[0] == "unfinished"
    assert first.path.read_bytes() == original
    assert not (app.managed_home.root / "automatic-learning").exists()
    assert not (app.managed_home.root / EVENT_CONTEXT_FILENAME).exists()


@pytest.mark.parametrize("platform", ["euroskat", "in_person"])
def test_established_recording_reused_and_only_actual_platform_controls_fees(
        localized_server, platform):
    from accounting_fixtures import completed_cent_session

    app = localized_server.app_context
    active = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="a" * 64,
                                     document=completed_cent_session().to_dict())
    app.managed_stateful.activate_session(active)
    original = active.path.read_bytes()
    browser = Browser(localized_server)
    form = Forms(browser.page()).find("/sessions/accounting/start")
    page = follow(browser, native_submit(browser, form, platform=platform, cent_tariff="1/2",
                                         selected_player="2"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.game(1)[0] == "settled" and row.game(1)[2] == "derived"
    assert not any(f["action"] == "/sessions/accounting/game" for f in Forms(page).forms)
    assert row.game(1)[1][1].gross.value == Fraction(-144, 100)
    assert (row.game(1)[1][1].fee is not None) == (platform == "euroskat")
    if platform == "in_person":
        assert all(r.fee is None and r.net is None for r in row.game(1)[1])
        assert text("en", "accounting.local_fees_unknown") in page
    assert active.path.read_bytes() == original


def test_partial_recording_asks_only_missing_result_and_reuses_known_declarer(localized_server):
    from accounting_fixtures import completed_cent_session

    from skatmind.session_history import rewind_session_state_v1
    from skatmind.session_persistence_codec import build_session_persistence_document_v1

    app = localized_server.app_context
    state = completed_cent_session().state
    cutoff = next(r.revision for r in state.command_log if r.command.kind == "record_play") - 1
    partial = rewind_session_state_v1(state, expected_revision=state.revision,
                                      target_revision=cutoff)
    active = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="a" * 64,
        document=build_session_persistence_document_v1(partial.state).to_dict())
    app.managed_stateful.activate_session(active)
    original = active.path.read_bytes()
    browser = Browser(localized_server)
    page = start(browser, selected_player="2")
    form = game_form(page, 1)
    assert action_fields(form) == {"position", "game_status", "game_value"}
    follow(browser, native_submit(browser, form, game_status="lost", game_value="72"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.confirmations[0].declarer_id == "player-b"
    assert row.confirmations[0].settlement == -144
    assert row.game(1)[0] == "settled" and row.game(1)[2] == "supplied"
    assert active.path.read_bytes() == original


def test_saved_session_title_is_reused_but_profile_platform_is_not(localized_server):
    from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
    from skatmind.app_web.frontend_profile_state import state_from_saved_profile_v1
    from skatmind.app_web.profile_player_contracts import ManagedItemDisplayLabelV1

    app = localized_server.app_context
    active = activate_session(app)
    profile = build_local_frontend_profile_v1(revision=0, language="en",
        preferred_game_platform="EuroSkat", managed_item_display_labels=(ManagedItemDisplayLabelV1(
            family="sessions", product_id=active.state.session_id,
            display_name="Saved own title"),))
    app.frontend_profile = state_from_saved_profile_v1(app.frontend_profile, profile)
    form = Forms(Browser(localized_server).page()).find("/sessions/accounting/start")
    assert form["values"]["title"] == "Saved own title"
    assert form["values"]["platform"] == ""


def test_old_game_payment_override_does_not_hide_an_established_recording(localized_server):
    from accounting_fixtures import completed_cent_session

    from skatmind.accounting_state import ConfirmedGameV1
    from skatmind.mode_accounting import SignedMoneyV1

    app = localized_server.app_context
    active = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="a" * 64,
                                      document=completed_cent_session().to_dict())
    app.managed_stateful.activate_session(active)
    browser = Browser(localized_server)
    start(browser, selected_player="2")
    journal = load_accounting(app.managed_home.root)
    row = replace(journal.round_heads[0], confirmations=(ConfirmedGameV1(position=1,
        status="external", personal_net=SignedMoneyV1.parse("987"),
        provenance="Old game payment"),))
    save_accounting(app.managed_home.root, append_accounting(journal, row),
                    expected_fingerprint=journal.fingerprint, source_guard=lambda: True)
    before = (app.managed_home.root / ACCOUNTING_FILENAME).read_bytes()
    page = browser.page()
    assert "-1.44" in page and "Old game payment" not in page
    assert not any(f["action"] == "/sessions/accounting/game" for f in Forms(page).forms)
    assert (app.managed_home.root / ACCOUNTING_FILENAME).read_bytes() == before


def test_legacy_bank_facts_cannot_govern_new_cost_calculations(localized_server):
    from skatmind.event_context_contracts import AmountV1
    from skatmind.mode_accounting import PersonalReceiptV1

    app = localized_server.app_context
    activate_match(app)
    browser = Browser(localized_server)
    page = create_context(browser)
    follow(browser, native_submit(browser, Forms(page).find("/matches/accounting/save"),
                                  entry_total="5", plus_level="0"))
    journal = load_accounting(app.managed_home.root)
    row = journal.tournament_heads[0]
    old = replace(row, receipts=(PersonalReceiptV1(pool="base", participation=True,
        personal_entitlement=True, received=AmountV1.parse("999"), provenance="Old payout"),),
        receipts_complete=True,
        obligations=tuple(replace(o, paid=o.total) for o in row.obligations))
    save_accounting(app.managed_home.root, append_accounting(journal, old),
        expected_fingerprint=journal.fingerprint, source_guard=lambda: True)
    page = browser.page("/matches/current")
    assert "Old payout" not in page
    form = Forms(page).find("/matches/accounting/save")
    assert action_fields(form) == {"entry_total", "plus_level"}
    follow(browser, native_submit(browser, form))
    current = load_accounting(app.managed_home.root)
    assert current.tournament_heads[0].receipts == ()
    assert not current.tournament_heads[0].receipts_complete
    assert all(o.paid is None for o in current.tournament_heads[0].obligations)
    assert any(r.receipts == old.receipts for r in current.tournaments)


def test_valid_existing_fee_boundary_needs_no_reentry(localized_server):
    from accounting_fixtures import cumulative_session_prefix

    from skatmind.accounting_state import TournamentAccountingV1, freeze_preparation
    from skatmind.event_context_projection import prepare_event_context_v1
    from skatmind.event_context_store import (
        append_event_revision_v1,
        load_event_context_v1,
        save_event_context_v1,
    )
    from skatmind.mode_accounting import STANDARD_SOURCE

    app = localized_server.app_context
    context, facts, documents = cumulative_session_prefix()
    context = replace(context, terms=(replace(context.terms[0], version=2,
                                              platform="euroskat"),))
    for document in documents:
        active = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="b" * 64,
                                          document=document.to_dict())
    app.managed_stateful.activate_session(active)
    journal = load_event_context_v1(app.managed_home.root)
    save_event_context_v1(app.managed_home.root, append_event_revision_v1(journal, context),
                         expected_fingerprint=journal.fingerprint)
    prepared = prepare_event_context_v1(context, facts, target=facts[-1].source.source,
                                        game_position=27)
    row = TournamentAccountingV1(context=context, preparation=freeze_preparation(prepared),
        rule=STANDARD_RULE, rule_source=STANDARD_SOURCE, rule_from_position=26, losses_before=4,
        obligations=(), receipts=(), receipts_complete=False, currency="EUR",
        provenance="Existing supported interval")
    accounting = load_accounting(app.managed_home.root)
    save_accounting(app.managed_home.root, append_accounting(accounting, row),
                    expected_fingerprint=accounting.fingerprint, source_guard=lambda: True)
    browser = Browser(localized_server)
    form = Forms(browser.page()).find("/sessions/accounting/save")
    assert "rule_from_position" not in form["values"]
    follow(browser, native_submit(browser, form))
    saved = load_accounting(app.managed_home.root).tournament_heads[0]
    assert saved.rule_from_position == 26 and saved.losses_before == 4
    assert next(c.value.value for c in saved.components if c.kind == "additional_losses") == -1


def test_tournament_checkpoint_derived_fee_boundary_four_to_six_is_four_euros(localized_server):
    from accounting_fixtures import own_loss_match

    from skatmind.app_web.match_frontend import import_unified_match_v1

    app = localized_server.app_context
    active = import_unified_match_v1(app.managed_stateful.root("matches"), handle="a" * 64,
                                     document=own_loss_match().to_dict())
    app.managed_stateful.activate_match(active)
    original = active.path.read_bytes()
    browser = Browser(localized_server)
    form = Forms(browser.page("/matches/current")).find("/matches/event-context/create")
    page = follow(browser, native_submit(browser, form))
    for through, points, losses in (("24", "780", "4"), ("26", "800", "5")):
        page = follow(browser, native_submit(browser,
            Forms(page).find("/matches/event-context/checkpoint"), through_position=through,
            personal_points=points, own_losses=losses))
    page = browser.page("/matches/position/28")
    form = Forms(page).find("/matches/accounting/save")
    assert action_fields(form) == {
        "entry_total", "plus_level"}
    page = follow(browser, native_submit(browser, form, entry_total="5", plus_level="2"))
    row = load_accounting(app.managed_home.root).tournament_heads[0]
    assert row.rule == STANDARD_RULE and row.rule_from_position == 25
    assert row.losses_before == 4 and row.prepared.own_losses == 6
    assert row.prepared.personal_points == 606
    assert next(c.value.value for c in row.components if c.kind == "additional_losses") == -4
    assert component_totals(row.components) == (Fraction(-41, 4), None)
    assert row.receipts == () and not row.receipts_complete
    assert all(o.paid is None for o in row.obligations)
    assert text("en", "accounting.cost_subtotal", total="10.25") in page
    path = app.managed_home.root / ACCOUNTING_FILENAME
    before = path.read_bytes()
    follow(browser, native_submit(browser, Forms(page).find("/matches/accounting/save")))
    assert path.read_bytes() == before
    assert active.path.read_bytes() == original


@pytest.mark.parametrize("platform", ["In-person game", "Unknown"])
def test_match_platform_reused_without_provider_defaults_or_a_new_questionnaire(
        localized_server, platform):
    from event_context_fixtures import synthetic_match

    from skatmind.app_web.match_frontend import import_unified_match_v1
    from skatmind.match_workspace_contracts import create_match_workspace_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )

    app = localized_server.app_context
    workspace = synthetic_match().workspace
    workspace = create_match_workspace_v1(replace(workspace.match_definition,
                                                  game_platform=platform))
    document = build_match_workspace_persistence_document_v1(workspace)
    active = import_unified_match_v1(app.managed_stateful.root("matches"), handle="a" * 64,
                                    document=document.to_dict())
    app.managed_stateful.activate_match(active)
    browser = Browser(localized_server)
    form = Forms(browser.page("/matches/current")).find("/matches/event-context/create")
    assert "platform" not in form["values"]
    page = follow(browser, native_submit(browser, form))
    costs = Forms(page).find("/matches/accounting/save")
    assert action_fields(costs) == {"entry_total", "table_total"}
    follow(browser, native_submit(browser, costs, entry_total="0"))
    row = load_accounting(app.managed_home.root).tournament_heads[0]
    assert row.rule == "unverified"
    assert next(c.value for c in row.components if c.kind == "additional_losses") is None
    assert row.obligations[0].total.numerator == 0
    assert component_totals(row.components)[1] is None


@pytest.mark.parametrize("locale", ["de", "en"])
def test_native_retry_language_switch_stale_and_pre_simplification_recovery(
        localized_server, locale):
    app = localized_server.app_context
    activate_session(app)
    browser = Browser(localized_server)
    switch(browser, browser.page(), locale)
    page = start(browser)
    stale = game_form(page, 1)
    bad = native_submit(browser, stale, game_status="lost", game_value="bad", declarer="1")
    assert bad[0] == 400 and 'role="alert"' in bad[2].decode()
    page = switch(browser, bad[2].decode(), "en" if locale == "de" else "de")
    assert game_form(page, 1)["values"]["game_value"] == "bad"
    page = follow(browser, native_submit(browser, game_form(page, 1), game_value="23"))
    assert native_submit(browser, stale, game_status="passed")[0] == 409
    before = load_accounting(app.managed_home.root)
    old = browser.submit(game_form(page, 1), settlement="-46", provenance="Old mandatory answer")
    assert old[0] == 400 and load_accounting(app.managed_home.root) == before
    returned = game_form(old[2].decode(), 1)
    assert "provenance" not in returned["values"] and "settlement" not in returned["values"]
    follow(browser, native_submit(browser, returned, game_value="24"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.game(1)[1][0].gross.value == -Fraction(48, 100)


def test_passed_missing_and_unfinished_remain_distinct(localized_server):
    app = localized_server.app_context
    activate_session(app)
    browser = Browser(localized_server)
    page = start(browser)
    page = follow(browser, native_submit(browser, game_form(page, 1), game_status="passed"))
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert row.game(1)[0] == "passed" and row.game(2)[0] == "missing"
    assert not any(f["action"] == "/sessions/accounting/lifecycle" for f in Forms(page).forms)
    page = follow(browser, native_submit(browser, open_form(page, 2)))
    assert load_accounting(app.managed_home.root).round_heads[0].game(2)[0] == "unfinished"
    assert "<script" not in render_accounting(app,
        app.managed_stateful.active_session, "sessions", "en")


def test_external_session_mapping_only_for_unresolved_identity_and_correct_rotation(
        localized_server):
    app = localized_server.app_context
    other = activate_session(app, "alias-session", ("x", "y", "z"))
    # This source's local player is the future rearhand (round participant a).
    from skatmind.session_persistence import save_session_persistence_file_v1
    from skatmind.session_persistence_codec import build_session_persistence_document_v1
    document = build_session_persistence_document_v1(
        replace(other.document.state, local_player_id="z"))
    save_session_persistence_file_v1(other.path, document,
        expected_content_fingerprint=other.document.content_fingerprint)
    before = other.path.read_bytes()
    activate_session(app)
    browser = Browser(localized_server)
    page = result(browser, start(browser), 1)
    form = open_form(page, 2, external=True)
    assert {"map_1", "map_2", "map_3"} <= set(form["values"])
    assert native_submit(browser, form, map_1="1", map_2="2", map_3="3")[0] == 400
    page = follow(browser, native_submit(browser, form, map_1="2", map_2="3", map_3="1"))
    assert other.path.read_bytes() == before
    row = load_accounting(app.managed_home.root).round_heads[0]
    assert tuple(p.event_player_id for p in row.context.bindings[-1].players) == ("b", "c", "a")


def test_finish_preserves_all_legacy_confirmations_without_using_them_in_ordinary_summary(
        localized_server):
    from skatmind.accounting_state import ExternalAdjustmentV1, NetConfirmationV1
    from skatmind.mode_accounting import SignedMoneyV1

    app = localized_server.app_context
    activate_session(app)
    browser = Browser(localized_server)
    page = complete_round(browser, start(browser))
    journal = load_accounting(app.managed_home.root)
    row = journal.round_heads[0]
    adjustment = ExternalAdjustmentV1(amount=SignedMoneyV1.parse("-99"),
                                      provenance="Old adjustment")
    row = replace(row, adjustment=adjustment, actual_block_complete=True)
    net = NetConfirmationV1(scope="block", round_ids=(row.identity,),
        activity_fingerprints=(row.activity_fingerprint,), personal_net=SignedMoneyV1.parse("123"),
        provenance="Original external confirmation")
    row = replace(row, net_confirmation=net)
    save_accounting(app.managed_home.root, append_accounting(journal, row),
                    expected_fingerprint=journal.fingerprint, source_guard=lambda: True)
    page = result(browser, browser.page(), 2, "200")
    page = follow(browser, native_submit(browser,
        Forms(page).find("/sessions/accounting/lifecycle")))
    finished = load_accounting(app.managed_home.root).round_heads[0]
    assert finished.net_confirmation == net and finished.adjustment == adjustment
    assert finished.actual_block_complete
    assert finished.activity_fingerprint != net.activity_fingerprints[0]
    assert "Old adjustment" not in page and "Original external confirmation" not in page
    assert "3.88" in page


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
    follow(browser, native_submit(browser, Forms(page).find("/matches/accounting/save"),
                                  entry_total="5", plus_level="0"))
    assert retained == tuple(build_unified_match_report_download_v1(active, report_id,
        strategy_source=value) for value in (False, True))
    assert independent == {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_accounting_oversized_start_rejected_before_mutation(localized_server):
    import http.client

    from skatmind.app_web.accounting_forms import ACCOUNTING_ROUTES

    app = localized_server.app_context
    active = activate_session(app)
    original = active.path.read_bytes()
    browser = Browser(localized_server)
    form = Forms(browser.page()).find("/sessions/accounting/start")
    values = dict(title="x" * 20000, cent_tariff="1/2", platform="euroskat")
    for route in ACCOUNTING_ROUTES:
        assert browser.request("POST", route, {**form["values"], **values})[0] == 413
        assert not (app.managed_home.root / ACCOUNTING_FILENAME).exists()
        assert active.path.read_bytes() == original
    connection = http.client.HTTPConnection("127.0.0.1", localized_server.port, timeout=30)
    try:
        connection.putrequest("POST", form["action"])
        for name, value in {"Cookie": browser.cookie, "Origin": localized_server.origin,
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "16385"}.items():
            connection.putheader(name, value)
        connection.endheaders()
        assert connection.getresponse().status == 413
    finally:
        connection.close()
    follow(browser, native_submit(browser, form, **{**values, "title": "Recovered"}))
    assert len(load_accounting(app.managed_home.root).round_heads) == 1


def test_cross_family_stale_publication_and_fresh_retry_preserve_both(localized_server):
    app = localized_server.app_context
    activate_match(app)
    activate_session(app)
    browser = Browser(localized_server)
    match_page = create_context(browser)
    stale_cent = Forms(browser.page()).find("/sessions/accounting/start")
    follow(browser, native_submit(browser, Forms(match_page).find("/matches/accounting/save")))
    accepted = load_accounting(app.managed_home.root)
    assert native_submit(browser, stale_cent, cent_tariff="1/2", platform="euroskat")[0] == 409
    assert load_accounting(app.managed_home.root) == accepted
    start(browser)
    current = load_accounting(app.managed_home.root)
    assert current.tournaments == accepted.tournaments and len(current.round_heads) == 1
