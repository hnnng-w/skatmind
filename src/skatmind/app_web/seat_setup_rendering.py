from __future__ import annotations

from html import escape

from .frontend_identifier_generation import build_known_player_handle_v1
from .player_seat_setup import (
    SEATS,
    initial_seat_values_v1,
    match_perspective_seat_v1,
    roster_names_v1,
)
from .profile_player_operations import resolve_known_player_handle_v1
from .translation_catalog import translate_frontend_message_v1


def _t(locale, key, **values):
    return escape(translate_frontend_message_v1(locale, key, **values))


def _select(name, label, choices, selected, *, own="", required=False):
    return (f'<label>{label}<select name="{name}"{" required" if required else ""}>'
        + ''.join(f'<option value="{escape(value, quote=True)}"'
                  f'{" selected" if value == selected else ""}'
                  f'{" data-own" if own and value == own else ""}>{text}</option>'
                  for value, text in choices) + '</select></label>')


def render_seat_setup_v1(profile, locale, *, family, setup=None):
    values = initial_seat_values_v1(profile) if setup is None else dict(setup.values)
    token = '' if setup is None else setup.token
    own = values.get("own_player_handle", "")
    seats = tuple((seat, _t(locale, f"creation.seat.{seat}")) for seat in SEATS)
    modes = (("manual", _t(locale, "creation.setup.manual")),)
    if own:
        player = resolve_known_player_handle_v1(profile, own)
        modes = (("own", _t(locale, "creation.setup.own", name=player.display_name)), *modes)
    controls = (
        f'<input type="hidden" name="setup_context" value="{token}">'
        f'<input type="hidden" name="own_player_handle" value="{own}">'
        + (_select("perspective_mode", _t(locale, "creation.setup.mode"), modes,
                  values.get("perspective_mode"))
        + '<div class="own-seat-choice">'
        + _select("own_seat", _t(locale, f"creation.setup.own_seat_{family}"),
            (("", _t(locale, "creation.setup.choose_seat")), *seats), values.get("own_seat"))
        + '</div>' if own or family == "sessions" else
            '<input type="hidden" name="perspective_mode" value="manual">'
            '<input type="hidden" name="own_seat" value="">')
    )
    options = (("", _t(locale, "creation.common.no_saved_player")),) + tuple(
        (build_known_player_handle_v1(player.player_id), escape(player.display_name))
        for player in (() if profile is None else profile.known_players))
    rows = []
    for seat, label in seats:
        auto = setup is not None and seat == setup.auto_seat
        own_label = (
            f'<p class="derived-own"><strong>{escape(player.display_name)}</strong> · '
            f'{_t(locale, "settings.preferences.own_player")}'
            f'<span class="own-pending"> — {_t(locale, "creation.setup.pending")}</span></p>'
            if own else '')
        release = ('<p class="own-release">'
                   + _t(locale, "creation.setup.release", name=player.display_name)
                   + '</p>' if auto else '')
        rows.append(
            f'<fieldset class="seat-entry" data-seat="{seat}"'
            f'{" data-auto" if auto else ""}><legend>{label}</legend>'
            + own_label + release + '<div class="seat-identity">'
            + _select(f"{seat}_mode", _t(locale, "creation.setup.entry_mode"),
                (("saved", _t(locale, "creation.common.known_player")),
                 ("new", _t(locale, "creation.common.new_player_name"))), values[f"{seat}_mode"])
            + '<div class="saved-player-entry">'
            + _select(f"{seat}_handle", _t(locale, "creation.common.known_player"),
                      options, values.get(f"{seat}_handle", ""), own=own) + '</div>'
            + f'<label class="new-player-entry">{_t(locale, "creation.common.new_player_name")}'
            f'<input name="{seat}_name" maxlength="120" placeholder=" " '
            f'value="{escape(values.get(f"{seat}_name", ""), quote=True)}"></label>'
            + (f'<button class="manual-perspective-action" type="submit" name="setup_action" '
               f'value="choose_{seat}" formnovalidate>'
               + _t(locale, "creation.match.use_perspective") + '</button>'
               if family == "matches" else '') + '</div></fieldset>')
    names = roster_names_v1(values, profile)
    perspective = values.get("perspective_seat", "")
    perspective_seat = match_perspective_seat_v1(values) if family == "matches" else perspective
    perspective_name = names[SEATS.index(perspective_seat)] if perspective_seat in SEATS else ""
    if family == "matches":
        perspective_control = (f'<input type="hidden" name="perspective_seat" '
                               f'value="{escape(perspective, quote=True)}">')
        if setup is None or not setup.reviewed:
            perspective_control += ('<p>' + _t(locale, "creation.match.perspective") + ': '
                + (escape(perspective_name) if perspective_name else
                   _t(locale, "creation.match.choose_perspective")) + '</p>')
        perspective_control += f'<p>{_t(locale, "creation.match.perspective_help")}</p>'
    else:
        perspective_control = _select(
            "perspective_seat", _t(locale, "creation.session.perspective"),
            (("", _t(locale, "creation.common.no_perspective")), *seats), perspective)
    return (
        '<div class="seat-setup"'
        + (' data-reviewed' if setup is not None and setup.reviewed else '') + '>' + controls
        + '<p>' + _t(locale, "creation.match.setup_help"
            if family == "matches" and values.get("perspective_mode") == "manual"
            else "creation.setup.help") + '</p>'
        + (f'<p>{_t(locale, "creation.setup.game_one")}</p>' if family == "matches" else '')
        + (f'<p>{_t(locale, "creation.session.knowledge_perspective")}</p>'
           if family == "sessions" else '')
        + ''.join(rows)
        + '<div class="manual-perspective">'
        + perspective_control + '</div>'
        + (f'<p class="reviewed-perspective">{_t(locale, "creation.setup.reviewed")}: '
        + (escape(perspective_name) if perspective_name else _t(
            locale, "creation.common.no_perspective")) + '</p>'
            if setup is not None and setup.reviewed else '')
        +
        '</div>'
    )


def render_setup_actions_v1(locale, *, family, setup=None):
    action = "creation.session.action" if family == "sessions" else "creation.match.action"
    return (
        f'<button type="submit" name="setup_action" value="update" formnovalidate>'
        f'{_t(locale, "creation.setup.update")}</button>'
        + (f'<button type="submit" name="setup_action" value="create">{_t(locale, action)}</button>'
           if setup is not None and setup.reviewed else '')
    )
