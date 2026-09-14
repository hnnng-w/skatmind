"""Escaped, localized read-only progress; recovery owns all supplied action markup."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

from .compact_card_rendering import compact_recorded_card
from .recorded_trick_progress import RecordedPrefix, RecordedTrickProgress
from .stateful_localization import text, translated
from .task_first_rendering import paragraph


def _name(progress, locale, player_id):
    player = next(p for p in progress.players if p.player_id == player_id)
    return player.player_label or text(locale, "task.player", number=player.fallback_number)


def _totals(progress: RecordedTrickProgress, locale: str, prefix: RecordedPrefix) -> str:
    content = '<div class="trick-totals">'
    for player, (player_id, value) in zip(progress.players, prefix.players, strict=True):
        content += f'<div class="trick-total" data-seat="{player.seat}"><p class="trick-player">'
        content += escape(_name(progress, locale, player_id)) + ' <span>— '
        content += translated(locale, f"creation.seat.{player.seat}") + '</span></p><dl>'
        metrics = (("tricks", value.tricks),) if progress.game_type == "null" else (
            ("tricks", value.tricks), ("points", value.points))
        for metric, number in metrics:
            content += '<div><dt>' + translated(locale, f"trick_progress.{metric}")
            content += f'</dt><dd data-trick-metric="{metric}">{number}</dd></div>'
        content += '</dl></div>'
    content += '</div>'
    if prefix.declarer is None:
        return content + paragraph(locale, "trick_progress.party_unknown")
    content += '<div class="trick-parties">'
    for side, value in (("declarer", prefix.declarer), ("defenders", prefix.defenders)):
        content += '<p>' + translated(locale, f"trick_progress.{side}") + ': '
        content += translated(locale, "trick_progress.party_tricks", tricks=value.tricks)
        if progress.game_type != "null":
            content += ' · ' + translated(locale, "trick_progress.party_points",
                                          points=value.points)
        content += '</p>'
    return content + '</div>'


def render_recorded_summary(progress: RecordedTrickProgress, locale: str) -> str:
    body = '<aside class="recorded-summary" data-recorded-summary><h3>'
    body += translated(locale, "trick_progress.title") + '</h3>'
    if progress.latest is None:
        return body + paragraph(locale, f"trick_progress.status.{progress.status}") + '</aside>'
    body += paragraph(locale, "trick_progress.completed", count=progress.completed_count)
    if progress.warning is not None:
        body += '<p class="trick-warning">' + translated(locale, "trick_progress.warning")
        body += f' <a href="#match-play-{progress.warning.play_index}">'
        body += translated(locale, "trick_progress.inspect") + '</a></p>'
    body += _totals(progress, locale, progress.latest)
    body += paragraph(locale, "trick_progress.null_scope" if progress.game_type == "null"
                      else "trick_progress.scope")
    return body + '</aside>'


def render_current_trick(progress: RecordedTrickProgress, locale: str) -> str:
    if progress.status != "active":
        return ""
    body = '<div class="recorded-current"><p>' + translated(locale, "trick_progress.current")
    body += '</p>'
    current = next((trick for trick in progress.tricks if trick.prefix is None), None)
    if current is None:
        return body + paragraph(locale, "trick_progress.no_cards") + '</div>'
    body += '<ol>'
    for play in current.plays:
        body += '<li>' + escape(_name(progress, locale, play.player_id)) + ': '
        body += compact_recorded_card(locale, play.card) + '</li>'
    return body + '</ol></div>'


def render_recorded_history(
    progress: RecordedTrickProgress, locale: str, *,
    actions: Mapping[int, str] | None = None, anchor_prefix: str | None = None,
) -> str:
    if not progress.tricks:
        return ""
    actions = actions or {}
    body = '<section class="recorded-history"><h3>'
    body += translated(locale, "trick_progress.title") + '</h3>'
    for trick in progress.tricks:
        body += f'<section class="recorded-trick" data-trick-number="{trick.number}"><h4>'
        body += translated(locale, "recovery.trick", number=trick.number) + '</h4><ol>'
        for position, play in enumerate(trick.plays, 1):
            anchor = ("" if anchor_prefix is None else
                      f' id="{escape(anchor_prefix)}-{play.decision_index}" tabindex="-1"')
            body += f'<li{anchor}><p><span class="trick-play-position">'
            body += translated(locale, "trick_progress.position", position=position) + '</span> — '
            body += escape(_name(progress, locale, play.player_id)) + ': '
            body += compact_recorded_card(locale, play.card) + '</p>'
            body += actions.get(play.decision_index, "") + '</li>'
        body += '</ol>'
        if trick.prefix is None:
            body += paragraph(locale, "trick_progress.terminal_incomplete"
                              if progress.status == "ended" else "trick_progress.incomplete")
        else:
            body += paragraph(locale, "trick_progress.winner",
                              player=_name(progress, locale, trick.winner_player_id))
            if progress.game_type != "null":
                body += paragraph(locale, "trick_progress.value", points=trick.points)
            body += '<p class="trick-prefix-heading">' + translated(
                locale, "trick_progress.after", number=trick.number) + '</p>'
            body += _totals(progress, locale, trick.prefix)
        body += '</section>'
    return body + '</section>'
