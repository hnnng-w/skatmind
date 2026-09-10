from __future__ import annotations

from contextvars import ContextVar
from functools import wraps
from html import escape

from .stateful_localization import card_name
from .translation_catalog import translate_frontend_message_v1

_RENDER_LOCALE = ContextVar("frontend_render_locale", default="en")


def localized_render(function):
    """Scope locale to one synchronous renderer, including concurrent HTTP requests."""
    @wraps(function)
    def render(*args, locale=None, **kwargs):
        token = _RENDER_LOCALE.set(locale or _RENDER_LOCALE.get())
        try:
            return function(*args, **kwargs)
        finally:
            _RENDER_LOCALE.reset(token)
    return render


def message(key: str, **values: object) -> str:
    return translate_frontend_message_v1(_RENDER_LOCALE.get(), key, **values)


def html_message(key: str, **values: object) -> str:
    return escape(message(key, **values), quote=True)


def localized_card_name(code: str) -> str:
    return card_name(_RENDER_LOCALE.get(), code)
