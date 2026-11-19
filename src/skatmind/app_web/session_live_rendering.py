"""Native game-local controls and a compact view of the actual current Trick."""

from html import escape

from .analysis_controls import EFFORTS
from .forced_card_guidance import ForcedCardGuidance, render_guidance
from .ordinary_result_numbers import ordinary_scalar
from .result_immediate import retained_immediate_best_cards
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


def live_recommendation(active, locale):
    outcome = active.live.outcome
    if active.live.unavailable:
        return paragraph(locale, "analysis.live.unavailable")
    if outcome is None:
        return ""
    if isinstance(outcome, ForcedCardGuidance):
        return render_guidance(outcome, locale)
    document = outcome.result.result.document
    best = retained_immediate_best_cards(document)
    if not best:
        return paragraph(locale, "analysis.live.unavailable")
    cards = ", ".join(card_name(locale, card) for card in best)
    result = '<div id="live-recommendation" role="status"><strong>' + translated(
        locale, "analysis.live.best", cards=cards) + '</strong>'
    position = document["position"]
    null = position["game_type"] == "null"
    result += paragraph(locale, "analysis.objective.null_" + position["player_role"]
                        if null else "analysis.objective.points")
    rows = document["analysis_report"]
    def swing(row):
        return text(locale, "result.point_swing") + ": " + ordinary_scalar(
            row["expected_point_swing"], ".2f", locale=locale)

    if not null:
        result += "<p>" + escape(swing(rows[0])) + "</p>"
    lower = rows[len(best):len(best) + 2]
    if lower:
        alternatives = [card_name(locale, row["card"]) + ("" if null else " — " + swing(row))
                        for row in lower]
        result += "<p>" + translated(locale, "result.alternatives") + ": " + escape(
            "; ".join(alternatives)) + "</p>"
    return result + '</div>'
