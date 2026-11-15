import pytest
from event_context_fixtures import changed_document, synthetic_match
from test_frontend_language_switching import localized_server as _localized_server
from test_historical_game import build_historical_input
from test_language_switch_context import switch
from test_match_recording_recovery_web import follow
from test_session_recorded_review_web import Browser, Forms
from test_session_transitions import _complete_retrospective_session

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.event_context_rendering import render_event_context
from skatmind.app_web.match_frontend import (
    import_unified_match_v1,
    select_unified_match_position_v1,
)
from skatmind.app_web.session_frontend import import_guided_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text
from skatmind.event_context_store import EVENT_CONTEXT_FILENAME, load_event_context_v1
from skatmind.match_workspace_persistence import save_match_workspace_file_v1
from skatmind.session_persistence_codec import build_session_persistence_document_v1


@pytest.fixture
def localized_server(tmp_path):
    yield from _localized_server.__wrapped__(tmp_path)


def activate_match(app, *, position=25):
    document = synthetic_match(settled_position=position)
    active = import_unified_match_v1(app.managed_stateful.root("matches"),
                                     handle="a" * 64, document=document.to_dict())
    app.managed_stateful.activate_match(active)
    select_unified_match_position_v1(active, position)
    return active


def create_context(browser, *, family="matches", **overrides):
    page = browser.page("/matches/current" if family == "matches" else "/sessions/current")
    form = Forms(page).find(f"/{family}/event-context/create")
    return follow(browser, browser.submit(form, event_name="Synthetic event",
        series_name="Actual list 1", event_mode="tournament", through_position="24",
        personal_points="780", own_losses="3", provenance="Confirmed synthetic list",
        scoring_source="Confirmed synthetic tournament rules", scoring_edition="1",
        **overrides))


@pytest.mark.parametrize("locale", ["en", "de"])
def test_native_forms_checkpoint_continuation_freeze_restart_and_passive_isolation(
        localized_server, locale, monkeypatch):
    app = localized_server.app_context
    active = activate_match(app)
    original = active.path.read_bytes()
    def forbidden(*_args, **_kwargs):
        pytest.fail("Passive context operations must not execute analysis or update Learning")
    monkeypatch.setattr("skatmind.app_web.execution.execute_guided_frontend_analysis_v1", forbidden)
    monkeypatch.setattr("skatmind.app_web.match_frontend.execute_match_capture_web_analysis_v1",
                        forbidden)
    browser = Browser(localized_server)
    page = switch(browser, browser.page("/matches/current"), locale)
    assert text(locale, "event.title") in page
    assert "selected_player" not in Forms(page).find("/matches/event-context/create")["values"]
    assert not (app.managed_home.root / EVENT_CONTEXT_FILENAME).exists()
    page = create_context(browser)
    path = app.managed_home.root / EVENT_CONTEXT_FILENAME
    first = path.read_bytes()
    assert text(locale, "event.status.ready") in page
    page = browser.page("/matches/position/26")
    assert "780" in page and text(locale, "event.status.ready") in page
    checkpoint = Forms(page).find("/matches/event-context/checkpoint")
    page = follow(browser, browser.submit(checkpoint))
    assert path.read_bytes() == first  # Equal update is a durable no-op.
    page = browser.page("/matches/position/25")
    page = follow(browser, browser.submit(Forms(page).find("/matches/event-context/freeze"),
                                          decision_index="1"))
    journal = load_event_context_v1(app.managed_home.root)
    assert len(journal.preparations) == 1
    prepared = journal.preparations[0]
    assert prepared.personal_points == 780 and prepared.actor_id == "player-b"
    assert prepared.selected_participant_id == "player-a"
    saved = path.read_bytes()
    page = switch(browser, page, "de" if locale == "en" else "en")
    browser.page("/matches/current")
    restarted = AppWebContextV1.create(app.managed_home)
    reopened = load_event_context_v1(restarted.managed_home.root)
    assert reopened == journal and path.read_bytes() == saved
    assert active.path.read_bytes() == original
    assert not (app.managed_home.root / "automatic-learning").exists()
    assert list(app.managed_stateful.root("corpora").iterdir()) == []


def test_safe_validation_values_stale_form_and_failed_write(localized_server, monkeypatch):
    app = localized_server.app_context
    active = activate_match(app)
    browser = Browser(localized_server)
    page = create_context(browser)
    path = app.managed_home.root / EVENT_CONTEXT_FILENAME
    before = path.read_bytes()
    form = Forms(page).find("/matches/event-context/checkpoint")
    response = browser.submit(form, own_losses="25", personal_points="-80")
    assert response[0] == 400
    page = response[2].decode()
    retained = Forms(page).find("/matches/event-context/checkpoint")
    assert retained["values"]["personal_points"] == "-80"
    assert retained["values"]["own_losses"] == "25"
    assert path.read_bytes() == before and 'role="alert"' in page
    page = follow(browser, browser.submit(retained, own_losses="3"))
    assert browser.submit(form, personal_points="990")[0] == 409
    before = path.read_bytes()
    def fail(*_args):
        raise OSError("Synthetic storage failure")
    monkeypatch.setattr("skatmind.event_context_store.os.replace", fail)
    response = browser.submit(Forms(page).find("/matches/event-context/checkpoint"),
                              personal_points="-70")
    assert response[0] == 409 and text("en", "validation.event.save") in response[2].decode()
    assert path.read_bytes() == before
    assert active.path.read_bytes() == synthetic_match_file_bytes(active)


def synthetic_match_file_bytes(active):
    from skatmind.match_workspace_persistence import _build_match_workspace_file_bytes_v1
    from skatmind.match_workspace_persistence_codec import (
        build_match_workspace_persistence_document_v1,
    )
    return _build_match_workspace_file_bytes_v1(
        build_match_workspace_persistence_document_v1(active.workspace))


def test_source_correction_requires_reload_preserves_frozen_context(localized_server):
    app = localized_server.app_context
    active = activate_match(app)
    browser = Browser(localized_server)
    page = create_context(browser)
    form = Forms(page).find("/matches/event-context/checkpoint")
    document = synthetic_match()
    corrected = changed_document(document)
    save_match_workspace_file_v1(active.path, corrected,
        expected_content_fingerprint=document.content_fingerprint)
    path = app.managed_home.root / EVENT_CONTEXT_FILENAME
    before = path.read_bytes()
    response = browser.submit(form, personal_points="500")
    assert response[0] == 409
    assert path.read_bytes() == before


def test_session_explicit_attachment_native_mapping_and_same_position_dedup(localized_server):
    app = localized_server.app_context
    match = activate_match(app, position=27)
    browser = Browser(localized_server)
    create_context(browser)
    session_document = build_session_persistence_document_v1(_complete_retrospective_session(
        build_historical_input(game_type="grand", hand_game=False)))
    active = import_guided_session_v1(app.managed_stateful.root("sessions"),
        handle="b" * 64, document=session_document.to_dict())
    app.managed_stateful.activate_session(active)
    before = active.path.read_bytes(), match.path.read_bytes()
    page = browser.page("/sessions/current")
    form = Forms(page).find("/sessions/event-context/attach")
    bad = browser.submit(form, game_position="26", selected_player="1", provenance="Same event")
    assert bad[0] == 400  # Fixed seat rotation is checked, not just similar names.
    page = follow(browser, browser.submit(form, game_position="27", selected_player="1",
                                          provenance="Confirmed same game at position 27"))
    journal = load_event_context_v1(app.managed_home.root)
    assert len(journal.heads) == 1 and len(journal.heads[0].bindings) == 2
    assert text("en", "event.title") in page
    page = browser.page("/matches/position/28")
    assert text("en", "event.status.incomplete") in page  # Missing positions 25 and 26.
    assert before == (active.path.read_bytes(), match.path.read_bytes())


def test_financial_facts_exact_tariff_source_compatibility_and_old_terms(localized_server):
    app = localized_server.app_context
    activate_match(app)
    browser = Browser(localized_server)
    page = create_context(browser)
    form = Forms(page).find("/matches/event-context/terms")
    values = dict(event_mode="tournament_cent", cent_tariff="1/4", currency="EUR",
        entry_paid="5.00", table_committed="0.75", financial_provenance="Confirmed event receipt",
        from_position="25", change_kind="later", provenance="Changed from game 25")
    invalid = browser.submit(form, **{**values, "cent_tariff": "1"})
    assert invalid[0] == 400
    page = follow(browser, browser.submit(form, **values))
    event = load_event_context_v1(app.managed_home.root).heads[0]
    assert event.applicable_terms(24).financial.currency is None
    terms = event.applicable_terms(25)
    assert terms.financial.entry_paid.numerator == 5 and terms.financial.entry_paid.denominator == 1
    assert terms.financial.table_committed.numerator == 3
    assert terms.financial.table_committed.denominator == 4
    page = browser.page("/matches/position/12")
    assert Forms(page).find("/matches/event-context/terms")["values"]["currency"] == ""


def test_native_reconciliation_requires_the_displayed_exact_disagreement(localized_server):
    app = localized_server.app_context
    activate_match(app)
    browser = Browser(localized_server)
    page = create_context(browser)
    page = follow(browser, browser.submit(Forms(page).find("/matches/event-context/checkpoint"),
        through_position="25", personal_points="999", own_losses="3", provenance="Supplied total"))
    page = browser.page("/matches/position/26")
    assert text("en", "event.status.conflict") in page
    form = Forms(page).find("/matches/event-context/reconfirm")
    response = browser.submit(form, provenance="Checked original list", disagreement="a" * 64)
    assert response[0] == 409
    page = follow(browser, browser.submit(form, provenance="Checked original list"))
    assert text("en", "event.status.ready") in page
    journal = load_event_context_v1(app.managed_home.root)
    assert journal.heads[0].checkpoints[-1].acknowledged_disagreement is not None
    assert journal.preparations[-1].disagreements[0].checkpoint.personal_points == 999
    # Explicit acknowledgement retained its actual arithmetic and source basis.
    assert journal.preparations[-1].disagreements[0].basis[0].sources


def test_context_free_rendering_preserves_existing_source_and_uses_no_json_editor(localized_server):
    app = localized_server.app_context
    active = activate_match(app)
    before = active.path.read_bytes()
    html = render_event_context(app, active, "matches", "en")
    assert '<form method="post"' in html and '<details>' in html
    assert '<script' not in html and 'type="file"' not in html and '<textarea' not in html
    assert active.path.read_bytes() == before
    assert not (app.managed_home.root / EVENT_CONTEXT_FILENAME).exists()


def test_context_does_not_retrofit_native_results_or_independent_collections(localized_server):
    from skatmind.app_web.cross_area_transfer import transfer_active_match_workspace_to_corpus_v1
    from skatmind.app_web.learning_frontend import create_unified_learning_corpus_v1
    from skatmind.app_web.match_frontend import (
        build_unified_match_report_download_v1,
        execute_unified_match_analysis_v1,
    )

    app = localized_server.app_context
    active = activate_match(app)
    corpus = create_unified_learning_corpus_v1(app.managed_stateful.root("corpora"),
        handle="c" * 64, corpus_id="independent-synthetic-collection")
    transfer_active_match_workspace_to_corpus_v1(active, corpus, selection_mode="select_imported",
        same_revision_resolution="reject", expected_catalog_revision=0)
    root = app.managed_stateful.root("corpora")
    independent = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    analyzed = execute_unified_match_analysis_v1(active, {
        "operation": "analyze_decision", "match_position": "25",
        "expected_revision": str(active.workspace.revision), "decision_index": "28",
        "immediate_sample_count": "1"})
    report_id = analyzed.state["selected_report_id"]
    retained = tuple(build_unified_match_report_download_v1(active, report_id,
                     strategy_source=source) for source in (False, True))
    browser = Browser(localized_server)
    create_context(browser)
    assert retained == tuple(build_unified_match_report_download_v1(active, report_id,
                             strategy_source=source) for source in (False, True))
    assert independent == {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_cent_creation_requires_explicit_mode_consistent_source_without_javascript(
        localized_server):
    app = localized_server.app_context
    document = build_session_persistence_document_v1(_complete_retrospective_session(
        build_historical_input()))
    active = import_guided_session_v1(app.managed_stateful.root("sessions"),
        handle="b" * 64, document=document.to_dict())
    app.managed_stateful.activate_session(active)
    original = active.path.read_bytes()
    browser = Browser(localized_server)
    form = Forms(browser.page()).find("/sessions/event-context/create")
    response = browser.submit(form, event_name="Actual Cent table", series_name="Actual block",
        game_position="1", selected_player="1", event_mode="cent")
    assert response[0] == 400  # No tournament-scoring provenance may be silently confirmed.
    returned = Forms(response[2].decode()).find("/sessions/event-context/create")
    assert returned["values"]["event_mode"] == "cent"
    assert returned["values"]["scoring_source"] == ""
    page = follow(browser, browser.submit(returned,
        scoring_source="Confirmed Cent game-point rules",
        scoring_edition="event-notice-1", currency="EUR", cent_tariff="1/2",
        financial_provenance="Confirmed tariff notice"))
    context = load_event_context_v1(app.managed_home.root).heads[0]
    assert context.terms[0].scoring_rule == "cent_game_points_v1"
    assert context.terms[0].scoring_source.reference == "Confirmed Cent game-point rules"
    assert Forms(page).find("/sessions/event-context/terms")["values"]["scoring_source"] == (
        "Confirmed Cent game-point rules")
    assert active.path.read_bytes() == original
