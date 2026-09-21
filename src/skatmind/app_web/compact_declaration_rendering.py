# ruff: noqa: E501 - Keep complete server-rendered elements legible.
"""Shared declaration controls and accepted-only summaries, without rule decisions."""

from __future__ import annotations

from html import escape

from skatmind.game_declaration import BOOLEAN_DECLARATION_FIELDS, VALID_DECLARATION_GAME_TYPES

from .stateful_localization import text, translated
from .task_first_rendering import input_field, paragraph, select_field


def compact_declaration_fields(locale, values=None, *, session=False):
    values = values or {}
    core = select_field(locale, "game_type", "declaration.game_type",
        (("", text(locale, "declaration.choose")), *(
            (value, text(locale, "task.value." + value)) for value in VALID_DECLARATION_GAME_TYPES)),
        values.get("game_type", ""), required=True)
    core += input_field(locale, "bid_value", "declaration.bid_value", values.get("bid_value"))
    flags = ''.join(
        '<label><input type="checkbox" name="' + name + '" value="true"'
        + (' checked' if values.get(name) is True else '') + '><span>'
        + translated(locale, "declaration." + name) + '</span></label>'
        for name in BOOLEAN_DECLARATION_FIELDS)
    details = input_field(locale, "matadors", "declaration.matadors", values.get("matadors"))
    details += paragraph(locale, "declaration.count_help") + paragraph(locale, "declaration.count_examples")
    if session:
        details += paragraph(locale, "declaration.session_count")
    return ('<div class="compact-declaration"><div class="declaration-core">' + core + '</div>'
        + '<fieldset class="declaration-options"><legend>' + translated(locale, "declaration.options")
        + '</legend><div class="declaration-checks">' + flags + '</div>'
        + '<p class="declaration-dependencies">' + translated(locale, "declaration.dependencies") + '</p>'
        + '<p class="declaration-null">' + translated(locale, "declaration.null") + '</p>'
        + paragraph(locale, "declaration.announced") + '</fieldset>'
        + '<details class="declaration-count"' + (' open' if values.get("matadors") is not None else '')
        + '><summary>' + translated(locale, "declaration.count_summary") + '</summary>'
        + details + '</details></div>')


def accepted_declaration_summary(locale, values, declarer, *, actions=None):
    if values is None:
        return ""
    actions = actions or {}
    rows = [("task.field.declarer_player_id", escape(declarer) + actions.get("set_declarer", "")),
            ("declaration.game_type", translated(locale, "task.value." + values["game_type"])
             + actions.get("set_declaration", ""))]
    for name in BOOLEAN_DECLARATION_FIELDS:
        rows.append(("declaration." + name, translated(locale,
            "common.answer.yes" if values[name] else "common.answer.no")))
    for name in ("bid_value", "matadors"):
        value = values[name]
        rendered = (translated(locale, "declaration.not_applicable")
                    if name == "matadors" and values["game_type"] == "null" else
                    translated(locale, "declaration.not_entered") if value is None else escape(str(value)))
        rows.append(("declaration." + name, rendered))
    return ('<section class="accepted-declaration"><h3>' + translated(locale, "declaration.accepted")
        + '</h3><dl>' + ''.join('<div><dt>' + translated(locale, key) + '</dt><dd>'
                              + value + '</dd></div>' for key, value in rows) + '</dl></section>')
