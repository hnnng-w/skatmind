"""Compact full-recording conclusion, separate from recorded input and Results."""

from .compact_card_rendering import card_set_display_order, compact_recorded_card
from .stateful_localization import translated
from .task_first_rendering import card_set_summary, paragraph
from .unplayed_card_summary import UnplayedCardSummary


def recorded_cards_summary(locale, cards):
    """Keep source absence distinct from a supplied set, including known-empty discards."""
    if cards is None:
        return translated(locale, "unplayed.not_recorded")
    return card_set_summary(locale, cards) + ' — ' + translated(locale, "unplayed.recorded")


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
    key = "unplayed.hand_skat" if summary.hand_game else "unplayed.discards"
    body += '<p><strong>' + translated(locale, key) + '</strong>: '
    partial = bool(recorded) and set(recorded) < set(summary.cards)
    conflict = recorded is not None and not exact and not partial
    if partial:
        body += '; '.join(compact_recorded_card(locale, card) + ' — ' + translated(
            locale, "unplayed.recorded" if card in recorded else "unplayed.derived")
            for card in card_set_display_order(summary.cards))
    else:
        body += ' '.join(compact_recorded_card(locale, card)
                         for card in card_set_display_order(summary.cards))
        body += ' — ' + translated(locale, "unplayed.recorded" if exact else "unplayed.derived")
    body += '</p>'
    if conflict:
        body += paragraph(locale, "unplayed.conflict")
        body += '<p>' + translated(locale, "unplayed.recorded_input") + ': '
        body += card_set_summary(locale, recorded) + '</p>'
    if summary.hand_game:
        body += paragraph(locale, "unplayed.no_discards")
        if discarded_cards:
            # Defensive presentation: retain contradictory supplied input, never certify it.
            body += paragraph(locale, "unplayed.conflict")
            body += '<p>' + translated(locale, "unplayed.discards") + ' — '
            body += translated(locale, "unplayed.recorded_input") + ': '
            body += card_set_summary(locale, discarded_cards) + '</p>'
    else:
        body += '<p><strong>' + translated(locale, "unplayed.original_skat") + '</strong>: '
        body += recorded_cards_summary(locale, original_skat) + '</p>'
    if review:
        body += paragraph(locale, "unplayed.review_scope")
    return body + '</div>'
