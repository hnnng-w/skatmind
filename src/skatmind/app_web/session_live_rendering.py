"""Native card entry with party outcomes from the admitted whole-game simulation."""

from .analysis_controls import EFFORTS
from .compact_card_rendering import compact_recorded_card
from .forced_card_guidance import ForcedCardGuidance
from .ordinary_result_numbers import ordinary_scalar
from .render_locale import localized_render
from .rollout_result_numbers import simulation_success
from .session_live_advice import LIVE_ROUTES, control_binding
from .stateful_localization import text, translated
from .task_first_rendering import form, hidden, paragraph, select_field

_local_success = localized_render(simulation_success)


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


def live_recommendation(active, locale):
    outcome = active.live.outcome
    if active.live.unavailable:
        return paragraph(locale, "analysis.live.unavailable")
    if outcome is None:
        return ""
    if isinstance(outcome, ForcedCardGuidance):
        return ('<p id="forced-card-guidance" role="status"><strong>'
                + translated(locale, "analysis.live.forced") + ':</strong> '
                + compact_recorded_card(locale, outcome.card, show_code=False) + '</p>')
    if outcome.status != "complete":
        return paragraph(locale, "analysis.live.unavailable")
    best = outcome.tied_best_cards
    candidates = {c.card: c for c in outcome.candidates}
    shown = outcome.ranked_cards[:len(best) + 2]
    leader = candidates[best[0]]
    same_count = [candidates[card] for card in shown if card not in best
                  and candidates[card].successes == leader.successes]
    show_score = any(c.total_game_score != leader.total_game_score for c in same_count)
    show_margin = any(c.total_game_score == leader.total_game_score for c in same_count)
    result = ('<section id="live-recommendation" role="status"><strong>'
              + translated(locale, "analysis.live." + outcome.settings.objective,
                           party=text(locale, "trick_progress." + outcome.local_side))
              + '</strong><ul>')
    for card in shown:
        row = candidates[card]
        successes = row.successes
        count = outcome.completed_common_worlds
        frequency = _local_success(successes, count, locale=locale)
        marker = "analysis.live.alternative"
        if card in best:
            marker = "rollout.marker.tied" if len(best) > 1 else "rollout.marker.recommended"
        result += ('<li>' + compact_recorded_card(locale, card, show_code=False)
                   + f' <b>{frequency}</b> · ' + translated(locale, marker))
        if successes == leader.successes:
            for show, key, total in ((show_score, "mean_score", row.total_game_score),
                                     (show_margin, "mean_margin", row.total_point_margin)):
                if show and total is not None:
                    result += (' · ' + translated(locale, "result." + key) + ': '
                               + ordinary_scalar(total / count, locale=locale))
        result += '</li>'
    result += '</ul>'
    if same_count:
        result += paragraph(locale, "analysis.live.tie_" + outcome.settings.objective)
    return result + '</section>'


def live_score(progress, locale):
    prefix = progress.latest
    if prefix is None or prefix.declarer is None:
        return ""
    metric = "tricks" if progress.game_type == "null" else "points"
    return paragraph(locale, "analysis.live.score", metric=text(locale, "trick_progress." + metric),
                     declarer=getattr(prefix.declarer, metric),
                     defenders=getattr(prefix.defenders, metric))
