from __future__ import annotations

from html import escape

from .frontend_profile_contracts import LocalFrontendProfileV1
from .translation_catalog import translate_frontend_message_v1


def text(locale: str, key: str, **values: object) -> str:
    return translate_frontend_message_v1(locale, key, **values)


def translated(locale: str, key: str, **values: object) -> str:
    return escape(text(locale, key, **values), quote=True)


def card_name(locale: str, code: str) -> str:
    return text(locale, "task.card.name", suit=text(locale, f"task.card.suit.{code[0]}"),
                rank=text(locale, f"task.card.rank.{code[1:]}"))


def player_name(locale: str, players, player_id: str | None) -> str:
    for index, player in enumerate(players, 1):
        if player.player_id == player_id:
            return player.player_label or text(locale, "task.player", number=index)
    return text(locale, "task.unknown")


def managed_name(
    locale: str, profile: LocalFrontendProfileV1 | None, family: str,
    product_id: str, fallback: str | None = None,
) -> str:
    if profile is not None:
        for label in profile.managed_item_display_labels:
            if label.family == family and label.product_id == product_id:
                return label.display_name
    return fallback or text(locale, f"task.identity.{family}")
