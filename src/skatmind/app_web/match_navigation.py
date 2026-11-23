"""Local navigation for an opened Match; destinations are built by its page owner."""

from html import escape

from .stateful_localization import translated


def match_navigation(locale, title, position, *, recording=None, review=None, decision=None):
    def area(key, href):
        label = translated(locale, "match_nav." + key)
        if href is None:
            return f'<strong aria-current="page">{label}</strong>'
        return f'<a href="{escape(href)}">{label}</a>'

    location = translated(locale, "task.match.game_heading", number=position)
    if decision:
        location += " · " + translated(locale, "match_nav.play", number=decision)
    return ('<nav class="match-navigation" aria-label="' + translated(locale, "match_nav.areas")
            + '"><p><b>' + escape(title) + '</b> · ' + location + '</p><div>'
            + area("record", recording) + area("review", review) + '</div></nav>')
