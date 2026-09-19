"""Visible read-only pre-Card context; the caller retains source and Result lifetime."""

from html import escape

from .compact_card_rendering import compact_recorded_card
from .recorded_decision_context import RecordedDecisionContext
from .stateful_localization import text, translated


def _player(locale, player):
    if player is None:
        return text(locale, "status.unavailable")
    return player.label or text(locale, "task.player", number=player.number)


def render_recorded_decision_context(context: RecordedDecisionContext, locale, *, scores=True):
    unavailable = text(locale, "status.unavailable")
    unknown = escape(unavailable)
    content = '<h3>' + translated(locale, "decision_context.title") + '</h3>'
    if context.game_number is not None:
        content += '<p>' + translated(
            locale, "task.match.position", number=context.game_number) + '</p>'
    content += '<p>' + translated(locale, "decision_context.position",
        trick=context.trick_number if context.trick_number is not None else unavailable,
        play=context.play_index if context.play_index is not None else unavailable,
        player=_player(locale, context.actor)) + '</p>'
    content += '<dl><dt>' + translated(locale, "task.field.game_type") + '</dt><dd>' + (
        translated(locale, "task.value." + context.game_type)
        if context.game_type else unknown) + '</dd>'
    content += '<dt>' + translated(locale, "task.field.declarer_player_id") + '</dt><dd>' + escape(
        _player(locale, context.declarer)) + '</dd></dl>'
    content += '<h4>' + translated(locale, "result.current_trick") + '</h4>'
    if context.current_trick is None:
        content += '<p>' + unknown + '</p>'
    elif not context.current_trick:
        content += '<p>' + translated(locale, "decision_context.empty_trick") + '</p>'
    else:
        content += '<ol class="decision-context-trick">' + ''.join(
            '<li><span>' + escape(_player(locale, player)) + ':</span> '
            + compact_recorded_card(locale, card, show_code=False) + '</li>'
            for player, card in context.current_trick) + '</ol>'
    content += '<p>' + translated(locale, "decision_context.next",
                                 player=_player(locale, context.next_player)) + '</p>'
    content += '<h4>' + translated(locale, "decision_context.hand") + '</h4>'
    if context.hand is None:
        content += '<p>' + unknown + '</p>'
    elif not context.hand:
        content += '<p>' + translated(locale, "task.known_empty") + '</p>'
    else:
        content += '<ul class="decision-context-hand">' + ''.join(
            '<li>' + compact_recorded_card(locale, card, show_code=False) + '</li>'
            for card in context.hand) + '</ul>'
    if scores:
        content += '<dl>' + ''.join('<dt>' + translated(locale, key) + '</dt><dd>'
            + (unknown if value is None else str(value)) + '</dd>' for key, value in (
                ("guided.declarer_points", context.declarer_points),
                ("guided.defender_points", context.defender_points))) + '</dl>'
    return '<div class="recorded-decision-context">' + content + '</div>'
