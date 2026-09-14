from __future__ import annotations

from .stateful_localization import translated


def render_entry_introduction_v1(route: str, locale: str) -> str:
    """One optional explanation beneath the shell title; task controls own guidance."""
    key = {"/analyze": "decision", "/review": "manual", "/sessions": "session",
           "/matches": "match", "/learning": "learning"}.get(route)
    if key is None:
        return ""
    return '<p class="entry-introduction">' + translated(locale, f"entry.{key}") + '</p>'
