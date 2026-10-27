"""Shared localized retained focus content for Learning and filtered debriefs."""

from html import escape

from .stateful_localization import translated
from .task_first_rendering import disclosure, paragraph


def render_learning_focuses(focuses, locale):
    body = ''
    for focus in focuses:
        body += '<article class="debrief-decision learning-focus"><h3>' + escape(
            focus.player + ' — ' + focus.topic) + '</h3><p>' + escape(focus.guidance) + '</p>'
        body += paragraph(locale, "learning.result.focus_scope", decisions=focus.decisions,
                          games=focus.games, matches=focus.matches)
        body += disclosure(locale, "learning.result.supporting_decisions", '<ul>' + ''.join(
            '<li>' + escape(caption) + '</li>' for caption in focus.references) + '</ul>')
        body += '</article>'
    if body:
        body = '<div class="learning-focuses"><p>' + translated(
            locale, "debrief.focuses") + '</p>' + body + '</div>'
    return body
