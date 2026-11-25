from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction
from threading import Event

import pytest
from test_accounting_web import activate_session, game_form, historical_round, open_form
from test_event_context_web import native_submit
from test_frontend_language_switching import localized_server
from test_match_recording_recovery_web import follow
from test_session_live_advice_web import START, post, tile_labels
from test_session_recorded_review_web import Browser, Forms

from skatmind.accounting_store import (
    ACCOUNTING_FILENAME,
    accounting_bytes,
    append_accounting,
    load_accounting,
    save_accounting,
)
from skatmind.app_web import session_live_advice as live
from skatmind.app_web.server import SkatMindAppWebRequestHandlerV1 as Handler
from skatmind.app_web.session_live_cent import capture_cent_authority

__all__ = ["localized_server"]
HAND = "CQ C9 SK H10 HQ HJ H7 DA D9 D8".split()


def prepare_opening(server, *, enable=True):
    browser = Browser(server)
    active = activate_session(server.app_context)
    historical_round(server.app_context, title="Synthetic round")
    page = browser.page()
    page = follow(browser, post(browser, "/sessions/cards", page, cards=HAND))
    browser.command("set_declarer")
    if enable:
        follow(browser, post(browser, START))
    return browser, active


def declare(browser, **extra):
    form = Forms(browser.page()).find("/sessions/command", kind="set_declaration")
    return browser.submit(form, game_type="grand", hand_game="true", bid_value="18", **extra)


def test_real_three_game_round_recommends_lower_win_frequency_on_personal_net(localized_server):
    browser, active = prepare_opening(localized_server)
    file = localized_server.app_context.managed_home.root / ACCOUNTING_FILENAME
    before = file.read_bytes()
    page = follow(browser, declare(browser))
    result = active.live.outcome
    assert result.money_basis == "net" and result.completed_common_worlds == 25
    assert result.settings.objective == "complete_settlement"
    assert result.tied_best_cards == ("HQ",)
    assert result.ranked_cards[:3] == ("HQ", "DA", "HJ")
    assert [(c.card, c.successes, c.expected_personal_eur) for card in result.ranked_cards[:3]
            for c in result.candidates if c.card == card] == [
        ("HQ", 2, Fraction("-1.7212")), ("DA", 1, Fraction("-1.7584")),
        ("HJ", 3, Fraction("-1.79"))]
    assert max(result.candidates, key=lambda c: c.successes).card == "HJ"
    assert (result.work.materialized_worlds, result.work.terminal_evaluations,
            result.work.card_transitions) == (25, 250, 7500)
    tiles = tile_labels(page, "live-recommendation")
    assert set(tiles) == set(HAND) and len([s for s in tiles.values() if "€" in s]) == 3
    assert all(s in tiles["HQ"] for s in ("Net: €-1.7212", "2/25", "8%"))
    assert all(s in tiles["HJ"] for s in ("Net: €-1.79", "3/25", "12%"))
    assert active.state.command_log[-1].command.declaration.matadors is None
    assert active.execution is None and file.read_bytes() == before


def test_existing_binding_uses_rotated_participants_and_accepted_count(localized_server):
    from test_historical_game import build_historical_input
    from test_session_transitions import _retrospective_before_play

    from skatmind.app_web.session_frontend import import_guided_session_v1
    from skatmind.deck import get_full_deck
    from skatmind.session_persistence_codec import build_session_persistence_document_v1

    app = localized_server.app_context
    # Only the explicitly supplied declaration count may narrow the exported
    # view, not the two other dealt hands or the real Hand Skat in this Session.
    data = build_historical_input(deck=HAND + [c for c in get_full_deck() if c not in HAND],
        hand_game=True, declarer_player_id="player-a")
    data["declaration"]["matadors"] = 2
    state = _retrospective_before_play(data, local_player_id="player-a")
    first = import_guided_session_v1(app.managed_stateful.root("sessions"), handle="b"*64,
        document=build_session_persistence_document_v1(state).to_dict())
    app.managed_stateful.activate_session(first)
    browser = Browser(localized_server)
    historical_round(app, title="Bound Session")
    page = follow(browser, post(browser, START))
    base = first.live.outcome
    assert base.money_basis == "net" and base.completed_common_worlds == 25
    assert base.tied_best_cards == ("DA",)
    assert next(c.expected_personal_eur for c in base.candidates if c.card == "DA") == (
        Fraction("-1.8456"))
    page = follow(browser, native_submit(browser, game_form(page, 1),
                                         game_status="won", game_value="96"))
    page = follow(browser, native_submit(browser, open_form(page, 2)))
    second = app.managed_stateful.active_session
    assert second is not first
    binding = capture_cent_authority(app.managed_home.root, second.document).binding
    assert binding.position == 2 and binding.terms.players == ("player-a", "player-b", "player-c")
    assert [p.player_id for p in second.state.players] == ["player-b", "player-c", "player-a"]


def test_tournament_cent_title_and_mode_do_not_create_a_round(localized_server):
    app = localized_server.app_context
    active = activate_session(app)
    browser = Browser(localized_server)
    form = Forms(browser.page()).find("/sessions/event-context/create")
    page = follow(browser, native_submit(browser, form, title="Three game Cent",
        event_mode="tournament_cent", platform="euroskat"))
    follow(browser, post(browser, "/sessions/cards", page, cards=HAND))
    browser.command("set_declarer")
    follow(browser, post(browser, START))
    page = follow(browser, declare(browser))
    assert active.live.outcome.tied_best_cards == ("HJ",)
    assert active.live.outcome.money_basis is None
    assert not any("€" in s for s in tile_labels(page, "live-recommendation").values())


def test_in_person_uses_gross_for_every_candidate(localized_server):
    app = localized_server.app_context
    active = activate_session(app)
    browser = Browser(localized_server)
    historical_round(app, platform="in_person")
    page = browser.page()
    follow(browser, post(browser, "/sessions/cards", page, cards=HAND))
    browser.command("set_declarer")
    follow(browser, post(browser, START))
    page = follow(browser, declare(browser))
    r = active.live.outcome
    assert r.money_basis == "gross" and r.tied_best_cards == ("HQ",)
    assert all(c.expected_personal_eur == Fraction(c.total_game_score, 2500) for c in r.candidates)
    assert "Before fees: €-1.7184" in tile_labels(page, "live-recommendation")["HQ"]


def test_detach_rebind_cannot_revive_authority_and_mapping_uses_event_ids(localized_server):
    from skatmind.app_web.session_frontend import create_guided_session_v1
    from skatmind.event_context_sources import build_event_binding_v1

    app = localized_server.app_context
    _, active = prepare_opening(localized_server, enable=False)
    root = app.managed_home.root
    original = capture_cent_authority(root, active.document)
    journal = load_accounting(root)
    row, = journal.round_heads
    one, = row.context.bindings
    # Same selected participant but different source IDs and seat rotation.
    other = create_guided_session_v1(active.category_root, handle="c"*64,
        session_id="second-session", players=tuple(replace(p, player_id=name) for p, name in
            zip(active.state.players, ("x", "y", "z"), strict=True)),
        capture_mode="live", local_player_id="y")
    mapped = build_event_binding_v1(other.document, game_position=3,
        player_map={"x": "c", "y": "a", "z": "b"})
    def save(previous, bindings):
        updated = replace(row, recordings=(), context=replace(row.context, bindings=bindings))
        journal = append_accounting(previous, updated)
        assert save_accounting(root, journal, expected_fingerprint=previous.fingerprint,
                               source_guard=lambda: True) == "saved"
        return journal
    detached = save(journal, (mapped,))
    assert capture_cent_authority(root, active.document).binding is None
    assert capture_cent_authority(root, other.document).binding.terms.players == ("a", "b", "c")
    save(detached, (one, mapped))
    assert not original.current(root, active.document)
    rebound = capture_cent_authority(root, active.document)
    assert rebound.current(root, active.document) and rebound.binding.position == 1


@pytest.mark.parametrize("boundary", ("admission", "evaluation", "send"))
def test_obsolete_round_cannot_authorize_delivery(localized_server, monkeypatch, boundary):
    import os

    from skatmind.app_web import server

    app = localized_server.app_context
    browser, active = prepare_opening(localized_server)
    entered, release = Event(), Event()
    def pause():
        entered.set()
        assert release.wait(20)

    if boundary == "admission":
        ran = server.run_live_attempt
        def delayed(*args):
            pause()
            return ran(*args)
        monkeypatch.setattr(server, "run_live_attempt", delayed)
    elif boundary == "evaluation":
        evaluate = live.evaluate_live_position
        def delayed(*args, **kwargs):
            pause()
            assert kwargs["cancelled"]()
            return evaluate(*args, **kwargs)
        monkeypatch.setattr(live, "evaluate_live_position", delayed)
    else:
        follow(browser, declare(browser))
        send = Handler._send_bytes
        def delayed(self, status, content, **kwargs):
            if b'id="live-recommendation"' in content:
                pause()
            return send(self, status, content, **kwargs)
        monkeypatch.setattr(Handler, "_send_bytes", delayed)
    with ThreadPoolExecutor(max_workers=1) as pool:
        response = (pool.submit(browser.request, "GET", "/sessions/current") if boundary == "send"
                    else pool.submit(declare, browser))
        try:
            assert entered.wait(15)
            journal = load_accounting(app.managed_home.root)
            row, = journal.round_heads
            term, = row.context.terms
            updated = replace(term, financial=replace(term.financial, cent_tariff="3"))
            changed = replace(row, context=replace(row.context, terms=(updated,)))
            if boundary == "send":
                # Non-cooperating replacement: same size, inode and timestamp.
                # Replace the owning round with a different same-length identity.
                file = app.managed_home.root / ACCOUNTING_FILENAME
                stamp = file.stat()
                raw = accounting_bytes(replace(journal, rounds=(replace(row, context=replace(
                    row.context, event_id="X"+row.identity[1:])),)))
                assert len(raw) == stamp.st_size
                file.write_bytes(raw)
                os.utime(file, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            else:
                assert save_accounting(app.managed_home.root, append_accounting(journal, changed),
                    expected_fingerprint=journal.fingerprint, source_guard=lambda: True) == "saved"
        finally:
            release.set()
        code, _, body = response.result(timeout=15)
    assert code == (409 if boundary == "send" else 303) and b'id="live-recommendation"' not in body
    page = browser.page()
    assert 'id="live-recommendation"' not in page and Forms(page).find("/sessions/play")
    assert active.live.outcome is None
