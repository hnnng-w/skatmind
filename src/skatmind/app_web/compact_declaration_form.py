"""Narrow native-checkbox translation, separate from legacy explicit forms."""

from __future__ import annotations

import re

from skatmind.declaration_diagnostics import DeclarationValueError
from skatmind.game_declaration import (
    BOOLEAN_DECLARATION_FIELDS,
    GameDeclaration,
    build_serializable_game_declaration,
)

DECLARATION_FIELDS = ("game_type", "bid_value", *BOOLEAN_DECLARATION_FIELDS, "matadors")


def form_error(reason, field_key=None):
    return DeclarationValueError("Compact declaration form is invalid: " + reason + ".",
                                 reason=reason, field_key=field_key)


def parse_compact_declaration(values):
    """Pass all four explicit choices to the existing canonical validator."""
    for name in ("game_type", "bid_value", "matadors"):
        if name not in values or type(values[name]) is not str:
            raise form_error("fields", name)
    for name in BOOLEAN_DECLARATION_FIELDS:
        if name in values and values[name] != "true":
            raise form_error("flag", name)
    numbers = {}
    for name in ("bid_value", "matadors"):
        raw = values[name]
        if raw and not re.fullmatch(r"-?[0-9]+", raw):
            raise form_error("integer", name)
        try:
            numbers[name] = int(raw) if raw else None
        except ValueError as error:
            raise form_error("integer", name) from error
    return GameDeclaration(
        game_type=values["game_type"],
        **{name: name in values for name in BOOLEAN_DECLARATION_FIELDS},
        **numbers,
    )


def explicit_declaration_values(declaration):
    """Private controls never reach the existing Command or Capture operation."""
    return {name: "true" if value is True else "false" if value is False else
            "" if value is None else str(value)
            for name, value in build_serializable_game_declaration(declaration).items()}
