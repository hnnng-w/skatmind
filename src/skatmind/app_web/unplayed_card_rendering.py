"""Compact full-recording conclusion, separate from recorded input and Results."""

from .compact_card_rendering import compact_recorded_card
from .stateful_localization import translated
from .task_first_rendering import cards_summary, paragraph
from .unplayed_card_summary import UnplayedCardSummary


def render_unplayed_cards(
    summary: UnplayedCardSummary | None, locale: str, *,
    original_skat, discarded_cards, review: bool = False,
) -> str:
    if summary is None:
        return ""
    recorded = original_skat if summary.hand_game else discarded_cards
    exact = recorded is not None and set(recorded) == set(summary.cards)
    body = '<div class="accepted-declaration" data-unplayed-cards><h3>'
    body += translated(locale, "unplayed.title") + '</h3>'
    body += paragraph(locale, "unplayed.derived")
    key = "unplayed.hand_skat" if summary.hand_game else "unplayed.discards"
    body += '<p><strong>' + translated(locale, key) + '</strong>: '
    body += ' '.join(compact_recorded_card(locale, card) for card in summary.cards)
    body += '</p><p>' + (translated(locale, "unplayed.recorded") if exact else
        translated(locale, "unplayed.recorded_input") + ': ' + (
            translated(locale, "unplayed.not_recorded") if recorded is None else
            cards_summary(locale, recorded))) + '</p>'
    if summary.hand_game:
        body += paragraph(locale, "unplayed.no_discards")
    else:
        body += '<p><strong>' + translated(locale, "unplayed.original_skat") + '</strong>: '
        body += (translated(locale, "unplayed.not_recorded") if original_skat is None else
                 translated(locale, "unplayed.recorded") + ' — '
                 + cards_summary(locale, original_skat)) + '</p>'
    if review:
        body += paragraph(locale, "unplayed.review_scope")
    return body + '</div>'
