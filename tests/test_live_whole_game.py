"""Current-decision objective selection, Null policy and terminal-party accounting."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from whole_game_rollout_oracle import synthetic_view

from skatmind.app_web.session_live_rendering import live_card_choices, live_score
from skatmind.app_web.stateful_localization import text
from skatmind.bounded_search_information import SearchPublicPlay
from skatmind.game_declaration import GameDeclaration
from skatmind.live_whole_game import _null_card, evaluate_live_game, live_rollout_view
from skatmind.whole_game_rollout import evaluate_whole_game_rollout_v1


@pytest.mark.parametrize("game,declarer,bid,matadors,flags", [
    ("clubs", "me", None, None, {}), ("grand", "right", 24, None, {}),
    ("diamonds", "left", 18, 2, {}), ("grand", "me", 480, 1, {}),
    ("clubs", "left", None, None, {"schneider_announced": True}),
    ("hearts", "me", 18, None, {"schwarz_announced": True}),
    ("grand", "me", None, 1, {"ouvert": True}),
])
def test_ordinary_live_reuses_exact_existing_terminal_objectives(game, declarer, bid, matadors,
                                                               flags):
    view, _, _ = synthetic_view(remaining=3, partial=1, declarer=declarer,
        declaration=GameDeclaration(game, bid_value=bid, matadors=matadors, **flags))
    live = evaluate_live_game(view, worlds=25, timeout_ms=5000)
    assert live.settings.objective == (
        "complete_settlement" if bid is not None and matadors is not None else "played_game_goal")
    original = evaluate_whole_game_rollout_v1(view, live.settings)
    assert live.status == "complete" and live.completed_common_worlds == 25
    assert (live.policy, live.policy_version) == ("side_aware_baseline", 1)
    assert live.tied_best_cards == original.tied_best_cards
    assert live.ranked_cards == original.ranked_cards
    assert [(c.card, c.successes, c.total_game_score, c.total_point_margin)
            for c in live.candidates] == [(c.card, c.local_success_count, c.total_local_game_score,
                c.total_local_card_point_margin) for c in original.candidates]


@pytest.mark.parametrize("bid", [None, 35, 36])
@pytest.mark.parametrize("seed,partial,declarer,expected", [
    # With DA led, discard SA to avoid winning the last trick with it.
    (48, 1, "me", {"CK": 0, "SA": 25}),
    # Defending, lead C8 to leave the declarer winning a spade on the last trick.
    (17, 0, "right", {"C8": 25, "HQ": 0}),
])
def test_null_party_success_with_without_and_above_fixed_value(seed, partial, declarer,
                                                                expected, bid):
    view, _, _ = synthetic_view(seed=seed, remaining=2, partial=partial, declarer=declarer,
        public_players=("left", "right"), declaration=GameDeclaration(
            "null", hand_game=True, bid_value=bid))
    result = evaluate_live_game(view, worlds=25, timeout_ms=5000)
    expected_objective = "played_game_goal" if bid is None else "complete_settlement"
    assert result.settings.objective == expected_objective
    assert (result.policy, result.policy_version) == ("null_avoid_or_force_trick", 1)
    if bid == 36:
        assert (result.status, result.stop_reason) == ("unavailable", "unsupported_null_overbid")
        assert not result.ranked_cards and result.work.sampled_worlds == 0
    else:
        assert result.status == "complete" and result.completed_common_worlds == 25
        assert {c.card: c.successes for c in result.candidates} == expected
        assert all(c.total_point_margin is None for c in result.candidates)
        assert result.tied_best_cards == (max(expected, key=expected.get),)
        if bid is not None:
            orientation = 1 if declarer == "me" else -1
            assert all(c.total_game_score == orientation * 25 * (
                35 if bool(c.successes) == (declarer == "me") else -70) for c in result.candidates)
    # The strict recorded version remains Suit/Grand only, even for valid Live Null.
    legacy = evaluate_whole_game_rollout_v1(view, result.settings)
    assert legacy.stop_reason == "unsupported_game_type"


@pytest.mark.parametrize("actor,declarer,trick,legal,expected", [
    ("me", "me", (("right", "S10"),), ("SJ", "S9"), "S9"),
    ("me", "right", (("right", "SJ"),), ("SA", "S10"), "S10"),
    ("me", "right", (), ("SA", "S7"), "S7"),
])
def test_null_policy_uses_only_actor_legal_cards_and_the_public_partial_trick(
        actor, declarer, trick, legal, expected):
    observation = SimpleNamespace(actor_side="declarer" if actor == declarer else "defenders",
        declarer_player=declarer, legal_cards=legal,
        current_trick=tuple(SearchPublicPlay(*play) for play in trick))
    assert _null_card(observation) == expected


def choices(result, locale):
    return live_card_choices(locale, SimpleNamespace(outcome=result, unavailable=False),
        SimpleNamespace(selectable_cards=result.ranked_cards, scope="exact_legal_cards"))


def test_true_null_tie_has_no_point_tiebreaker_and_every_tied_card_is_visible():
    view, _, _ = synthetic_view(remaining=10, declarer="me",
                                declaration=GameDeclaration("null", bid_value=18))
    result = evaluate_live_game(view, worlds=25, timeout_ms=5000)
    best = max(c.successes for c in result.candidates)
    assert len(result.tied_best_cards) > 1
    assert result.tied_best_cards == tuple(c.card for c in result.candidates if c.successes == best)
    for locale in ("en", "de"):
        body = choices(result, locale)
        assert body.count(text(locale, "rollout.marker.tied")) == len(result.tied_best_cards)
        assert "<details" not in body and "analysis_report" not in body
        assert body.count("%</b>") == min(len(result.candidates), len(result.tied_best_cards) + 2)
        assert body.count('type="radio"') == len(result.candidates)
        assert text(locale, "analysis.live.final_margin") not in body


def test_live_null_context_reports_completed_tricks_instead_of_card_points():
    prefix = SimpleNamespace(declarer=SimpleNamespace(tricks=0, points=0),
                             defenders=SimpleNamespace(tricks=2, points=38))
    for locale in ("de", "en"):
        body = live_score(SimpleNamespace(latest=prefix, game_type="null"), locale)
        assert text(locale, "trick_progress.tricks") in body
        assert text(locale, "trick_progress.points") not in body
        assert "<dd>0</dd>" in body and "<dd>2</dd>" in body and "38" not in body


def test_contradictory_or_retrospective_facts_do_not_downgrade_to_goal():
    with pytest.raises(ValueError, match="current Session"):
        live_rollout_view({"analysis_mode": "post_game_review", "actual_card_played": "S9"})
    view, _, _ = synthetic_view(remaining=2)
    with pytest.raises(ValueError):
        evaluate_live_game(replace(view, defender_points=view.defender_points+1),
                           worlds=25, timeout_ms=5000)


def test_live_null_cancellation_discards_unfinished_common_world(monkeypatch):
    import skatmind.live_whole_game as module

    view, _, _ = synthetic_view(seed=48, remaining=2, partial=1,
        declaration=GameDeclaration("null", hand_game=True, ouvert=True, bid_value=59))
    leaves = []
    real = module._null_terminal
    def observe(*args):
        leaves.append(None)
        return real(*args)
    monkeypatch.setattr(module, "_null_terminal", observe)
    result = evaluate_live_game(view, worlds=25, timeout_ms=5000, cancelled=lambda: len(leaves)==3)
    assert result.status == "cancelled" and result.work.terminal_evaluations == 3
    assert result.completed_common_worlds == 1 and not result.ranked_cards
    assert not result.tied_best_cards and all(c.successes <= 1 for c in result.candidates)


def test_visible_secondary_metric_and_fractional_precision():
    from skatmind.live_whole_game import LiveCardOutcome

    view, _, _ = synthetic_view(remaining=2)
    base = evaluate_live_game(view, worlds=25, timeout_ms=5000)
    # Rendering-only fixture for a one-world difference at More time precision.
    rows = (LiveCardOutcome("DA", 399, 360, -16), LiveCardOutcome("S9", 399, 340, 8))
    result = replace(base, settings=replace(base.settings, objective="complete_settlement",
        requested_worlds=400, wall_clock_timeout_ms=60000), completed_common_worlds=400,
        candidates=rows, ranked_cards=("DA", "S9"), tied_best_cards=("DA",))
    for locale, percent in (("de", "99,75 %"), ("en", "99.75%")):
        page = choices(result, locale)
        assert page.count(percent) == page.count("399/400") == 2
        assert page.count(text(locale, "result.mean_score")) == 2
        assert text(locale, "analysis.live.tie_complete_settlement") in page
        assert "<details" not in page
