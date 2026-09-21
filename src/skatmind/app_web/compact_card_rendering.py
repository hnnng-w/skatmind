"""Native Card presentation only; callers own availability and set/trace semantics."""

from __future__ import annotations

from html import escape

from skatmind.deck import get_full_deck

from .stateful_localization import card_name, translated

_SYMBOLS = {"C": "♣", "S": "♠", "H": "♥", "D": "♦"}
_DISPLAY_RANKS = ("J", "A", "10", "K", "Q", "9", "8", "7")


def _card_face(card):
    """Validated printed identity, shared by native choices and read-only labels."""
    if card not in get_full_deck():
        raise ValueError("Card face requires a canonical Card code.")
    return (f'<span class="card-face" data-card-suit="{card[0]}" aria-hidden="true">'
            f'<span class="card-suit">{_SYMBOLS[card[0]]}</span> '
            f'<span class="card-rank">{card[1:]}</span></span>')


def compact_recorded_card(locale, card, *, show_code=True):
    """Read-only Card label with the same symbols, exact code and full accessible name."""
    face = _card_face(card)
    suffix = f" ({card})" if show_code else ""
    return ('<span class="recorded-card" role="img" aria-label="'
            + escape(f"{card_name(locale, card)}{suffix}", quote=True) + '">'
            + face
            + (f'<span aria-hidden="true">{suffix}</span>' if suffix else '') + '</span>')


def card_display_groups(cards, game_type=None):
    """Printed suits, not effective suits; game_type is retained for caller compatibility."""
    groups = []
    for suit in "CSHD":
        group = tuple(suit + rank for rank in _DISPLAY_RANKS if suit + rank in cards)
        if group:
            groups.append((f"task.card.suit.{suit}", group))
    return tuple(groups)


def card_set_display_order(cards):
    """A display copy for explicitly set-like hands/evidence, never ordered Plays or ranks."""
    return tuple(card for _, group in card_display_groups(cards) for card in group)


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
                + '>' + _card_face(card) + '</label>')
        groups.append('<div class="compact-card-group"><h4>' + translated(locale, key)
                      + '</h4><div class="compact-card-choices">'
                      + ''.join(choices) + '</div></div>')
    summary = ''
    if mode == "set":
        codes = escape(', '.join(card for card in card_set_display_order(cards)
                                 if card in selected))
        summary = ('<p class="compact-selection" data-count-template="'
            + translated(locale, "compact.pending", count="{count}") + '">'
            '<span class="compact-count">' + translated(locale, "compact.snapshot") + '</span> '
            '<span class="compact-selected">' + codes + '</span></p>')
    return (
        f'<fieldset class="compact-cards" data-card-mode="{mode}" data-card-locale="{locale}">'
        '<legend>' + translated(locale, "compact.choose_" + mode) + '</legend>'
        '<p class="compact-guidance">' + translated(locale, "compact.capacity_" + mode,
                                                     capacity=capacity) + '</p>'
        '<div class="compact-card-groups">' + ''.join(groups) + '</div>'
        + summary + '<p class="compact-rejected"></p></fieldset>')
