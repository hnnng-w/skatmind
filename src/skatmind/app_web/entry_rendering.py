from __future__ import annotations

from .stateful_localization import translated


def render_entry_introduction_v1(route: str, locale: str) -> str:
    """Concise source guidance and native alternatives beneath the shell title."""
    key = {"/analyze": "decision", "/review": "manual", "/sessions": "session",
           "/matches": "match", "/learning": "learning"}.get(route)
    if key is None:
        return ""
    introduction = '<p class="entry-introduction">' + translated(locale, f"entry.{key}") + '</p>'
    if route == "/analyze":
        return ('<h2>' + translated(locale, "entry.decision.heading") + '</h2>'
                + introduction + '<p><a class="button-link" href="/review/recorded">'
                + translated(locale, "entry.recorded_action") + '</a></p>')
    if route == "/review":
        return (introduction + '<p><a href="/review/recorded">'
                + translated(locale, "entry.recorded_action") + '</a></p><p>'
                + translated(locale, "entry.recording_introduction") + ' '
                + '<a href="/sessions">' + translated(locale, "entry.recording_action")
                + '</a></p>')
    return introduction
