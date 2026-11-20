from dataclasses import replace
from fractions import Fraction
from functools import partial
from random import Random

import pytest
from test_live_whole_game import choices
from whole_game_rollout_oracle import finite_worlds, synthetic_view

from skatmind.compatible_search_world import build_compatible_search_world_space
from skatmind.game_declaration import GameDeclaration
from skatmind.live_cent import CentComparison, LiveCentTerms, matador_draws
from skatmind.live_whole_game import evaluate_live_game
from skatmind.matador_inference import infer_matadors_from_declarer_cards

TERMS = LiveCentTerms(("Alice", "Bob", "Carol"), "1/2", True)
evaluate = partial(evaluate_live_game, worlds=25, timeout_ms=5000)


@pytest.mark.parametrize("tariff", ("1/2", "1", "2", "3", "5"))
def test_exact_personal_transfers_once_doubled_and_individually_rounded(tariff):
    terms = replace(TERMS, tariff=tariff)
    t = Fraction(tariff)
    # Declarer loses Null: signed settlement -46 already includes the double.
    assert terms.personal_transfer("me", -46) == (-92*t/100, -92*t/100)
    assert terms.personal_transfer("left", -46) == (46*t/100, None)
    gross, net = terms.personal_transfer("right", 23)
    assert gross == -23*t/100
    assert net == (None if t.denominator == 2 else gross)
    assert replace(terms, provider_fees=False).personal_transfer("me", -46)[1] is None

    comparison = CentComparison(("HJ",), terms, "me")
    for score in (23, -46):
        comparison.add("HJ", score)
    # Even when the mean is negative there is a positive fee for the one win.
    fee_cents = -(-(46*t*3) // 100)
    assert comparison.means(2) == ("net", {"HJ": (-46*t-fee_cents)/200})


def test_one_unknown_fee_forces_gross_even_for_a_candidate_with_only_known_outcomes():
    view, _, _ = synthetic_view(seed=17, remaining=2, partial=0, declarer="right",
        public_players=("left", "right"), declaration=GameDeclaration("null",
            hand_game=True, bid_value=35))
    result = evaluate(view, cent=replace(TERMS, tariff="1"))
    assert result.money_basis == "gross" and result.tied_best_cards == ("C8",)
    assert [(c.card, c.successes, c.expected_personal_eur) for c in result.candidates] == [
        ("C8", 25, Fraction("0.70")), ("HQ", 0, Fraction("-0.35"))]
    assert "Before fees: €0.70" in choices(result, "en")
    assert evaluate(replace(view, declaration=replace(view.declaration, bid_value=36)),
                    cent=TERMS).stop_reason == "unsupported_null_overbid"


@pytest.mark.parametrize("declarer,seed", (("me", 3), ("left", 46), ("right", 3)))
def test_supplied_matadors_condition_the_entire_common_space(declarer, seed):
    view, _, _ = synthetic_view(seed=seed, remaining=2, partial=1, declarer=declarer,
        declaration=GameDeclaration("clubs", hand_game=True, bid_value=18))
    space = build_compatible_search_world_space(view)
    plays = [p for trick in view.completed_tricks for p in trick.plays]
    played = [p.card for p in (*plays, *view.current_trick) if p.player == declarer]
    def owned(world):
        hand = {"me": view.local_remaining_hand, "left": world.left_hand,
                "right": world.right_hand}[declarer]
        return infer_matadors_from_declarer_cards("clubs",
                                                  [*played, *hand, *world.hypothetical_skat])
    all_worlds = finite_worlds(view)
    assert len(all_worlds) == space.compatible_world_count
    for count in range(1, 12):
        expected = {w for w in all_worlds if owned(w) == count}
        size, draws = matador_draws(space, 25, Random(0), lambda: None, count=count)
        assert size == len(expected)
        if size:
            sample = tuple(draws)
            assert len(sample) == 25 and set(sample) <= expected
            if seed == 46 and count == 1:
                # Six deals with the top Jack and six without it.
                assert size == 12 and {"CJ" in (*w.left_hand, *w.hypothetical_skat)
                                       for w in sample} == {True, False}
        else:
            assert evaluate(view, cent=TERMS, supplied_matadors=count).stop_reason == (
                "incompatible_world_space")


def test_genuine_missing_bid_retains_success_comparison_and_labels_it():
    view, _, _ = synthetic_view(remaining=4, declaration=GameDeclaration("clubs", hand_game=True))
    base, cent = evaluate(view), evaluate(view, cent=TERMS)
    assert cent.completed_common_worlds == 25 and cent.candidates == base.candidates
    assert (cent.ranked_cards, cent.tied_best_cards) == (base.ranked_cards, base.tied_best_cards)
    assert cent.money_basis == "unavailable" and "bid is unknown" in choices(cent, "en")
    assert "Reizwert ist unbekannt" in choices(cent, "de")


def test_sampled_declaration_is_only_used_at_settlement(monkeypatch):
    import skatmind.live_whole_game as live

    view, _, _ = synthetic_view(seed=3, remaining=2, partial=1, declarer="left",
        declaration=GameDeclaration("clubs", hand_game=True, bid_value=18))
    actors = set()
    policy = live.select_whole_game_rollout_card_v1
    def observed(obs):
        actors.add(obs.actor_player)
        assert obs.declaration == view.declaration and obs.declaration.matadors is None
        assert obs.visible_out_of_play_cards == ()
        return policy(obs)
    monkeypatch.setattr(live, "select_whole_game_rollout_card_v1", observed)
    r = evaluate(view, cent=TERMS)
    assert actors == {"me", "left", "right"} and r.completed_common_worlds == 25


def test_cancellation_at_last_transfer_does_not_publish_a_money_ranking(monkeypatch):
    view, _, _ = synthetic_view(remaining=2, declaration=GameDeclaration("grand", bid_value=18))
    real = CentComparison.add
    seen = 0
    def count_transfer(self, card, score):
        nonlocal seen
        seen += 1
        return real(self, card, score)
    monkeypatch.setattr(CentComparison, "add", count_transfer)
    result = evaluate(view, cent=TERMS, cancelled=lambda: seen >= 25*2)
    assert result.status == "cancelled" and seen == 50 and not result.ranked_cards
    assert all(c.expected_personal_eur is None for c in result.candidates)


def test_overbid_settlement_money_ties_and_fine_display_precision():
    view, _, _ = synthetic_view(remaining=2, declaration=GameDeclaration("grand", bid_value=480))
    r = evaluate(view, cent=TERMS)
    assert r.money_basis == "net" and len(r.tied_best_cards) > 1
    assert all(c.successes == 0 and c.expected_personal_eur == Fraction("-9.60")
               for c in r.candidates)
    # Minimum native difference: a half-cent in one out of 400 games.
    a, b = r.candidates[:2]
    sample = replace(r, candidates=(replace(a, expected_personal_eur=Fraction(1, 80000)),
                                    replace(b, expected_personal_eur=Fraction(0))),
                     ranked_cards=(a.card, b.card), tied_best_cards=(a.card,))
    assert "0.0000125" in choices(sample, "en") and "0,0000125" in choices(sample, "de")
