import re
from copy import deepcopy
from dataclasses import FrozenInstanceError
from html import escape
from types import SimpleNamespace

import pytest

from skatmind.app_web.recorded_decision_context import (
    DecisionContextPlayer,
    project_recorded_decision_context,
    source_player_labels,
)
from skatmind.app_web.recorded_decision_context_rendering import render_recorded_decision_context
from skatmind.app_web.stateful_localization import card_name
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as text

SESSION_HAND = ("C10", "CJ", "SA", "SJ", "HA", "DK", "D7")
MATCH_HAND = ("C9", "C8", "C7", "S10", "S8", "HK", "H8", "DQ", "DJ", "D9")


def context_html(page):
    contexts = re.findall(r'<div class="recorded-decision-context"[^>]*>(.*?)</div>', page, re.S)
    assert len(contexts) == 1, "One visible pre-Card situation must be present"
    context, = contexts
    assert not any(tag in context for tag in ("<details", "<input", "<button", "<table", "<script"))
    return context


def assert_context(page, locale, *, hand, prefix, actor, trick, play, game=None):
    context = context_html(page)
    assert text(locale, "decision_context.title") in context
    assert escape(text(locale, "decision_context.position",
                       trick=trick, play=play, player=actor)) in context
    if game is not None:
        assert text(locale, "task.match.position", number=game) in context
    assert escape(text(locale, "decision_context.next", player=actor)) in context
    hand_html = re.search(r'<ul class="decision-context-hand"[^>]*>(.*?)</ul>', context, re.S)[1]
    assert re.findall(r'role="img" aria-label="([^"]+)"', hand_html) == [
        escape(card_name(locale, card), quote=True) for card in hand]
    if prefix:
        trick_html = re.search(
            r'<ol class="decision-context-trick"[^>]*>(.*?)</ol>', context, re.S)[1]
        rows = re.findall(r'<li>(.*?)</li>', trick_html, re.S)
        assert len(rows) == len(prefix)
        for row, (player, card) in zip(rows, prefix, strict=True):
            assert escape(player) in row
            assert f'aria-label="{escape(card_name(locale, card))}"' in row
    else:
        assert text(locale, "decision_context.empty_trick") in context
    return context


def document():
    return {"position": {"hand": list(SESSION_HAND), "current_trick": ["HJ", "DJ"],
        "trick_leader": "left", "next_player": "me", "declarer_player": "left",
        "game_type": "grand", "declarer_points": 0, "defender_points": 0,
        "public_hand_cards": ["H7"], "skat": ["S9", "H7"]},
        "legal_cards": ["CJ", "SJ"], "score_summary": {
            "total_declarer_points": 14, "total_defender_points": 29},
        "input_file": "private-source-must-not-be-rendered", "recommendation": None}


PLAYERS = dict(zip(("me", "left", "right"),
                  (DecisionContextPlayer(name, n) for n, name in enumerate("ABC", 1)), strict=True))


def project(data=None, **kwargs):
    return project_recorded_decision_context(
        document() if data is None else data, players=PLAYERS,
        trick_number=4, play_index=3, **kwargs)


@pytest.mark.parametrize("leader", ("me", "left", "right"))
@pytest.mark.parametrize("count", (0, 1, 2))
def test_canonical_relative_cycle_and_chronological_prefix(leader, count):
    data = document()
    cycle = ("me", "left", "right")
    start = cycle.index(leader)
    order = tuple(cycle[(start + offset) % 3] for offset in range(3))
    data["position"].update(trick_leader=leader, current_trick=["HJ", "DJ"][:count],
                            next_player=order[count])
    original = deepcopy(data)
    context = project(data)
    assert context.current_trick == tuple((PLAYERS[relative], card) for relative, card in
        zip(order[:count], ["HJ", "DJ"][:count], strict=True))
    assert context.next_player == PLAYERS[order[count]]
    assert context.actor == PLAYERS["me"]
    assert context.hand == SESSION_HAND and context.declarer_points == 14
    assert context.declarer == PLAYERS["left"]
    for locale in ("en", "de"):
        rendered = render_recorded_decision_context(context, locale)
        assert card_name(locale, "SJ") in rendered
        assert "private-source" not in rendered and card_name(locale, "H7") not in rendered
        if not count:
            assert text(locale, "decision_context.empty_trick") in rendered
    assert data == original
    with pytest.raises(FrozenInstanceError):
        context.hand = ()


@pytest.mark.parametrize("field", ("hand", "current_trick"))
@pytest.mark.parametrize("bad", (None, "CA", True, ["invalid"], ["HJ", "HJ"], [{}]))
def test_defensive_card_absence_preserves_safe_siblings(field, bad):
    data = document()
    data["position"][field] = bad
    context = project(data)
    assert getattr(context, field) is None
    assert context.declarer_points == 14 and context.next_player == PLAYERS["me"]
    rendered = render_recorded_decision_context(context, "de")
    assert text("de", "status.unavailable") in rendered
    assert text("de", "decision_context.empty_trick") not in rendered
    assert text("de", "task.known_empty") not in rendered


@pytest.mark.parametrize("bad", (None, True, "0", 0.0, [], {}))
def test_unknown_total_is_not_zero_and_keeps_other_side(bad):
    data = document()
    data["score_summary"] = {"total_declarer_points": bad, "total_defender_points": 0}
    context = project(data)
    assert context.declarer_points is None and context.defender_points == 0
    for locale in ("de", "en"):
        html = render_recorded_decision_context(context, locale)
        assert (f'{text(locale, "guided.declarer_points")}</dt><dd>'
                f'{text(locale, "status.unavailable")}') in html
        assert f'{text(locale, "guided.defender_points")}</dt><dd>0' in html


@pytest.mark.parametrize("bad", (None, "unknown", [], {}))
def test_unknown_turn_contract_and_absent_execution_are_not_invented(bad):
    data = document()
    data["position"].update(trick_leader=bad, next_player=bad, declarer_player=bad, game_type=bad)
    context = project(data)
    assert context.current_trick == ((None, "HJ"), (None, "DJ"))
    assert context.next_player is context.declarer is context.game_type is None
    assert context.hand == SESSION_HAND
    assert project_recorded_decision_context({"position": bad}, players={}) is None


def test_source_labels_are_complete_escaped_localized_and_never_private_ids():
    long_name = 'Ann <&"\'> ' + "LongName" * 40
    players = tuple(SimpleNamespace(player_id=identifier, player_label=label)
        for identifier, label in (("stable-a", long_name), ("stable-b", None), ("stable-c", "Yes")))
    relative = {"me": "stable-a", "left": "stable-b", "right": "stable-c"}
    labels = source_player_labels(players, relative)
    assert source_player_labels(players, {**relative, "left": "foreign"}) == {}
    assert source_player_labels(players, {**relative, "left": "stable-a"}) == {}
    context = project_recorded_decision_context(document(), players=labels)
    for locale in ("en", "de"):
        html = render_recorded_decision_context(context, locale)
        assert escape(long_name) in html and "stable-" not in html
        assert text(locale, "task.player", number=2) in html and "Yes" in html
    unbound = project_recorded_decision_context(document(), players={})
    html = render_recorded_decision_context(unbound, "en")
    assert escape(long_name) not in html and text("en", "status.unavailable") in html
    assert card_name("en", "DJ") in html


@pytest.mark.parametrize("rotation", (0, 1, 2))
def test_source_relative_identity_does_not_follow_initial_seats(rotation):
    ids = ("player-b", "player-c", "player-a")
    players = tuple(SimpleNamespace(player_id=identifier, player_label=label)
                    for identifier, label in zip(ids, "BCA", strict=True))
    relative = dict(zip(("me", "left", "right"), ids[rotation:] + ids[:rotation], strict=True))
    labels = source_player_labels(players, relative)
    assert labels["me"].label == "BCA"[rotation]
    assert labels["left"].label == "BCA"[(rotation + 1) % 3]
    assert labels["right"].label == "BCA"[(rotation + 2) % 3]


def test_session_adapter_uses_only_the_retained_source_and_result(tmp_path):
    from test_session_recorded_review import context_for, selection

    from skatmind.app_web.recorded_decision_context_sources import session_decision_context
    from skatmind.app_web.session_recorded_review import execute_recorded_session_decision_v1
    from skatmind.app_web.session_recorded_review_rendering import render_recorded_review_source_v1

    app, context = context_for(tmp_path)
    execute_recorded_session_decision_v1(app, context, selection=selection(context))
    source, result = context.recorded_review_source, context.execution.result.result
    projected = session_decision_context(source, result)
    checkpoint = source.decision.checkpoint
    assert (projected.trick_number, projected.play_index) == (
        checkpoint.trick_number, checkpoint.play_index)
    assert projected.hand == result.document["position"]["hand"]
    assert projected.actor.label == next(p.player_label for p in source.document.state.players
                                        if p.player_id == checkpoint.acting_player_id)
    # A renderer can only label the retained source, even with an unrelated current state.
    view = SimpleNamespace(recorded_review_source=source, state=SimpleNamespace(players=()))
    html = render_recorded_review_source_v1(view, locale="en", game_label="Synthetic")
    assert projected.actor.label in html
    assert session_decision_context(None, result) is None


def test_no_match_execution_or_non_position_report_has_no_context():
    from skatmind.app_web.recorded_decision_context_sources import match_decision_context

    assert match_decision_context(None, None) is None
    assert match_decision_context(SimpleNamespace(report_kind="historical_analysis"), None) is None
    assert match_decision_context(SimpleNamespace(report_kind="decision_analysis",
        value=SimpleNamespace(status="unavailable")), None) is None
