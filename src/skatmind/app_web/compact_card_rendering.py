"""Native Card presentation only; callers own availability and set/trace semantics."""

from __future__ import annotations

from html import escape

from skatmind.deck import get_full_deck
from skatmind.rules import JACK_STRENGTH, NULL_RANK_STRENGTH, is_trump

from .stateful_localization import card_name, translated

_SYMBOLS = {"C": "♣", "S": "♠", "H": "♥", "D": "♦"}


def compact_recorded_card(locale, card, *, show_code=True):
    """Read-only Card label with the same symbols, exact code and full accessible name."""
    suffix = f" ({card})" if show_code else ""
    return ('<span class="recorded-card" role="img" aria-label="'
            + escape(f"{card_name(locale, card)}{suffix}", quote=True) + '">'
            + f'<span aria-hidden="true">{_SYMBOLS[card[0]]} {card[1:]}{suffix}</span></span>')


def card_display_groups(cards, game_type=None):
    """Display order is independent of canonical set input and chronological Plays."""
    remaining = [card for card in get_full_deck() if card in cards]
    groups = []
    if game_type != "null":
        prominent = [card for card in remaining if (
            card.endswith("J") if game_type is None else is_trump(card, game_type))]
        prominent.sort(key=lambda card: (-JACK_STRENGTH.get(card, 0),
                                        get_full_deck().index(card)))
        if prominent:
            groups.append(("compact.jacks" if game_type is None else "compact.trumps",
                           tuple(prominent)))
        remaining = [card for card in remaining if card not in prominent]
    for suit in "CSHD":
        group = [card for card in remaining if card[0] == suit]
        if game_type == "null":
            group.sort(key=lambda card: -NULL_RANK_STRENGTH[card[1:]])
        if group:
            groups.append((f"task.card.suit.{suit}", tuple(group)))
    return tuple(groups)


def compact_card_selector(locale, *, mode, cards=None, selected=(), game_type=None, capacity=1):
    if mode not in {"set", "play"}:
        raise ValueError("Card selector mode must be set or play.")
    cards = tuple(get_full_deck() if cards is None else cards)
    selected = tuple(selected or ())
    groups = []
    for key, group in card_display_groups(cards, game_type):
        choices = []
        for card in group:
            label = escape(card_name(locale, card), quote=True)
            choices.append(
                '<label class="compact-card"><input type="'
                + ("checkbox" if mode == "set" else "radio")
                + f'" name="cards" value="{card}" aria-label="{label}"'
                + (' checked' if card in selected else '')
                + (' required' if mode == "play" else '')
                + f'><span aria-hidden="true">{_SYMBOLS[card[0]]} {card[1:]}</span></label>')
        groups.append('<div class="compact-card-group"><h4>' + translated(locale, key)
                      + '</h4><div class="compact-card-choices">'
                      + ''.join(choices) + '</div></div>')
    summary = escape(', '.join(card for card in cards if card in selected))
    return (
        f'<fieldset class="compact-cards" data-card-mode="{mode}" data-card-locale="{locale}">'
        '<legend>' + translated(locale, "compact.choose_" + mode) + '</legend>'
        '<p class="compact-guidance">' + translated(locale, "compact.capacity_" + mode,
                                                     capacity=capacity) + '</p>'
        '<div class="compact-card-groups">' + ''.join(groups) + '</div>'
        '<p class="compact-selection" data-count-template="'
        + translated(locale, "compact.pending", count="{count}") + '">'
        '<span class="compact-count">' + translated(locale, "compact.snapshot") + '</span> '
        '<span class="compact-selected">' + summary + '</span></p>'
        '<p class="compact-rejected"></p></fieldset>')
