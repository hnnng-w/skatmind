"""Native card entry with party outcomes from the admitted whole-game simulation."""

from html import escape

from .analysis_controls import EFFORTS
from .compact_card_rendering import _card_face, card_set_display_order
from .forced_card_guidance import ForcedCardGuidance
from .ordinary_result_numbers import ordinary_scalar
from .session_live_advice import LIVE_ROUTES, control_binding
from .stateful_localization import card_name, text, translated
from .task_first_rendering import form, hidden, paragraph, select_field


def live_controls(active, locale, ended):
    effort = active.live.effort
    status = paragraph(locale, "analysis.live.inactive" if effort is None
                       else "analysis.live.active")

    def control(route, label, fields=""):
        return form(locale, route, hidden("managed_handle", active.handle)
                    + hidden("expected_revision", active.state.revision)
                    + hidden("live_binding", control_binding(active, route)) + fields, label)

    if effort is None:
        return status if ended else status + control(LIVE_ROUTES[0], "analysis.live.start")
    choices = select_field(locale, "analysis_effort", "analysis.effort",
                           tuple((v, text(locale, "analysis.effort." + v)) for v in EFFORTS),
                           effort)
    return (status + ("" if ended else control(LIVE_ROUTES[1], "analysis.live.apply", choices))
            + control(LIVE_ROUTES[2], "analysis.live.stop"))


def _tile(locale, card, *, marker=None, best=False, metrics=""):
    badge = ""
    if marker:
        star = '<span aria-hidden="true">★ </span>' if best else ''
        badge = f'<span class="live-badge">{star}{translated(locale, marker)}</span>'
    return ('<label class="live-tile"' + (' data-best' if best else '') + '>'
            + f'<input type="radio" name="cards" value="{escape(card, quote=True)}" required>'
            + badge + '<span class="live-identity">' + _card_face(card)
            + '<span>' + escape(card_name(locale, card)) + '</span></span>' + metrics + '</label>')


def _compared_choices(locale, outcome):
    best = outcome.tied_best_cards
    candidates = {c.card: c for c in outcome.candidates}
    shown = outcome.ranked_cards[:len(best) + 2]
    leader = candidates[best[0]]
    same_count = [candidates[card] for card in shown if card not in best
                  and candidates[card].successes == leader.successes]
    show_score = any(c.total_game_score != leader.total_game_score for c in same_count)
    show_margin = any(c.total_game_score == leader.total_game_score for c in same_count)
    objective = translated(locale, "analysis.live." + outcome.settings.objective,
                           party=text(locale, "trick_progress." + outcome.local_side))
    money = outcome.money_basis in ("net", "gross")
    if money:
        objective = translated(locale, "analysis.live.money_objective") + " " + objective
    elif outcome.money_basis == "unavailable":
        objective += " " + translated(locale, "analysis.live.money_missing_bid")
    result = f'<p class="live-objective">{objective}</p><div class="live-featured">'
    count = outcome.completed_common_worlds
    for card in shown:
        row = candidates[card]
        successes = row.successes
        # The three common counts (25/100/400) need at most two decimal places.
        percentage = ordinary_scalar(100 * successes / count, "g", locale=locale)
        metrics = ('<span class="live-frequency"><b>'
                   + translated(locale, "analysis.live.percent", value=percentage)
                   + '</b><span>' + translated(locale, "analysis.live.samples",
                                               successes=successes, count=count)
                   + '</span></span>')
        marker = "analysis.live.alternative"
        if card in best:
            marker = "rollout.marker.tied" if len(best) > 1 else "rollout.marker.recommended"
        if money:
            # Half a cent / 400 = 0.0000125 EUR. Seven places cover every native
            # effort exactly; Fraction formatting never passes through a float.
            units, decimals = format(row.expected_personal_eur, ".7f").split(".")
            amount = units + text(locale, "rollout.number.decimal_separator") + (
                decimals.rstrip("0").ljust(2, "0"))
            metrics += ('<span class="live-secondary"><b>' + translated(
                locale, "analysis.live.money_" + outcome.money_basis, amount=amount)
                + '</b></span>')
        elif successes == leader.successes:
            for show, key, total in ((show_score, "result.mean_score", row.total_game_score),
                                     (show_margin, "analysis.live.final_margin",
                                      row.total_point_margin)):
                if show and total is not None:
                    metrics += ('<span class="live-secondary">' + translated(locale, key)
                                + ': <b>' + ordinary_scalar(total / count, locale=locale)
                                + '</b></span>')
        result += _tile(locale, card, marker=marker, best=card in best, metrics=metrics)
    result += '</div>'
    if same_count and not money:
        result += paragraph(locale, "analysis.live.tie_" + outcome.settings.objective)
    return result, shown


def live_card_choices(locale, live, task):
    """The recording task owns selectable cards. Advice decorates them, never selects one."""
    cards = task.selectable_cards
    outcome = live.outcome
    identity = body = ""
    shown = ()
    if task.scope != "exact_legal_cards":
        body = paragraph(locale, "task.match.scope." + task.scope)
    elif live.unavailable:
        body = paragraph(locale, "analysis.live.unavailable")
    elif isinstance(outcome, ForcedCardGuidance):
        if cards == (outcome.card,):
            identity = ' id="forced-card-guidance"'
            shown = (outcome.card,)
            body = ('<div class="live-featured">'
                    + _tile(locale, outcome.card, marker="analysis.live.forced") + '</div>')
    elif outcome is not None:
        if outcome.status == "complete" and set(cards) == set(outcome.ranked_cards):
            identity = ' id="live-recommendation"'
            body, shown = _compared_choices(locale, outcome)
        else:
            body = paragraph(locale, "analysis.live.unavailable")
    remaining = [card for card in card_set_display_order(cards) if card not in shown]
    if remaining:
        if shown:
            body += paragraph(locale, "analysis.live.other_choices")
        body += ('<div class="live-other-choices">'
                 + ''.join(_tile(locale, card) for card in remaining) + '</div>')
    return (f'<fieldset class="compact-cards" data-card-mode="play" data-card-locale="{locale}"'
            + identity + '><legend>' + translated(locale, "compact.choose_play") + '</legend>'
            + body + '<p class="compact-rejected"></p></fieldset>')


def live_score(progress, locale):
    prefix = progress.latest
    if prefix is None or prefix.declarer is None:
        return ""
    metric = "tricks" if progress.game_type == "null" else "points"
    parties = (("declarer", prefix.declarer), ("defenders", prefix.defenders))
    rows = ''.join('<div><dt>' + translated(locale, "trick_progress." + side)
                   + f'</dt><dd>{getattr(party, metric)}</dd></div>'
                   for side, party in parties)
    return ('<div class="live-score"><h4>' + translated(locale, "trick_progress." + metric)
            + '</h4><dl>' + rows + '</dl></div>')
