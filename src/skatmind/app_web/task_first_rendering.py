# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

import json
from html import escape

from skatmind.deck import get_full_deck

from .stateful_localization import card_name, translated


def hidden(name: str, value: object) -> str:
    return f'<input type="hidden" name="{escape(name)}" value="{escape(str(value), quote=True)}">'


def disclosure(locale: str, key: str, content: str, *, technical: bool = False) -> str:
    kind = "technical-details" if technical else "advanced-settings"
    return f'<details class="{kind}"><summary>{translated(locale, key)}</summary>{content}</details>'


def technical_details(locale: str, value: object) -> str:
    return disclosure(locale, "task.technical", '<pre lang="en">'
                      + escape(json.dumps(value, ensure_ascii=False, indent=2)) + '</pre>',
                      technical=True)


def section(locale: str, key: str, content: str, *, level: int = 2) -> str:
    return f'<section class="panel"><h{level}>{translated(locale, key)}</h{level}>{content}</section>'


def paragraph(locale: str, key: str, **values: object) -> str:
    return f'<p>{translated(locale, key, **values)}</p>'


def input_field(
    locale: str, name: str, key: str, value: object = "", *, kind: str = "text",
    required: bool = False,
) -> str:
    return (f'<label>{translated(locale, key)} <input name="{escape(name)}" '
            f'type="{kind}" value="{escape(str(value) if value is not None else "", quote=True)}"'
            f'{" required" if required else ""}></label>')


def select_field(locale: str, name: str, key: str, options, current: object = None, *, required=False) -> str:
    return (f'<label>{translated(locale, key)} <select name="{escape(name)}"{" required" if required else ""}>'
            + ''.join(f'<option value="{escape(str(value), quote=True)}"'
                      f'{" selected" if value == current else ""}>{escape(label)}</option>'
                      for value, label in options) + '</select></label>')


def boolean_field(locale: str, name: str, key: str, value: bool = False) -> str:
    return select_field(locale, name, key, (
        ("false", translated(locale, "common.answer.no")),
        ("true", translated(locale, "common.answer.yes")),
    ), "true" if value else "false")


def card_select(locale: str, name: str = "card", *, cards=None, current=None) -> str:
    choices = tuple(
        (code, f"{card_name(locale, code)} ({code})")
        for code in (get_full_deck() if cards is None else cards)
    )
    return select_field(locale, name, "task.card.choose",
                        (("", translated(locale, "task.card.choose")), *choices),
                        current or "", required=True)


def card_palette(locale: str, selected=None, *, name: str = "cards") -> str:
    return (f'<fieldset><legend>{translated(locale, "task.cards")}</legend><div class="card-grid">'
            + ''.join(f'<label class="card-choice"><input type="checkbox" name="{name}" '
                      f'value="{code}"{" checked" if code in (selected or ()) else ""}>'
                      f'{escape(card_name(locale, code))} <code>{code}</code></label>'
                      for code in get_full_deck()) + '</div></fieldset>')


def cards_summary(locale: str, cards) -> str:
    if cards is None:
        return translated(locale, "task.unknown")
    if not cards:
        return translated(locale, "task.known_empty")
    return escape(', '.join(f"{card_name(locale, code)} ({code})" for code in cards))


def form(
    locale: str, action: str, fields: str, label_key: str, *, primary: bool = False,
    disabled: bool = False, multipart: bool = False, confirm_key: str | None = None,
) -> str:
    return (f'<form method="post" action="{action}" class="form-grid"'
            + (f' data-confirm="{translated(locale, confirm_key)}"' if confirm_key else "")
            +
            f'{" enctype=\"multipart/form-data\"" if multipart else ""}>{fields}'
            f'<button type="submit" class="{"primary" if primary else "secondary"}"'
            f'{" disabled" if disabled else ""}>{translated(locale, label_key)}</button></form>')
