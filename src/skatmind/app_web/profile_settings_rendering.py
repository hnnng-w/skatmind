from __future__ import annotations

import time
from html import escape

from .frontend_identifier_generation import build_known_player_handle_v1
from .frontend_profile_contracts import LocalFrontendProfileV1
from .frontend_profile_operations import (
    FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE,
    FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE,
    FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE,
    FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE,
)
from .local_time_rendering import render_time_zone_settings
from .profile_driven_creation import FRIENDLY_GAME_PLATFORMS
from .settings_forms import SettingsEditorV1
from .translation_catalog import translate_frontend_message_v1


def _t(locale: str, key: str, **values: object) -> str:
    return escape(translate_frontend_message_v1(locale, key, **values))


def _generation(value: int) -> str:
    return f'<input type="hidden" name="profile_generation" value="{value}">'


def _player_options(
    profile: LocalFrontendProfileV1 | None,
    *,
    selected_id: str | None,
    locale: str,
) -> str:
    options = [f'<option value="">{_t(locale, "settings.players.none")}</option>']
    if profile is not None:
        options.extend(
            f'<option value="{build_known_player_handle_v1(player.player_id)}"'
            f"{' selected' if player.player_id == selected_id else ''}>"
            f"{escape(player.display_name)}</option>"
            for player in profile.known_players
        )
    return "".join(options)


def _platform_fields(
    profile: LocalFrontendProfileV1 | None,
    *,
    locale: str,
) -> str:
    preferred = None if profile is None else profile.preferred_game_platform
    product_values = {value for _choice, value in FRIENDLY_GAME_PLATFORMS}
    selected_choice = next(
        (choice for choice, value in FRIENDLY_GAME_PLATFORMS if value == preferred),
        "custom" if preferred is not None else "",
    )
    custom_value = preferred if preferred is not None and preferred not in product_values else ""
    options = [
        f'<option value=""{" selected" if not selected_choice else ""}>'
        f"{_t(locale, 'settings.platform.none')}</option>"
    ]
    options.extend(
        f'<option value="{choice}"'
        f"{' selected' if choice == selected_choice else ''}>"
        f"{_t(locale, f'creation.platform.{choice}')}</option>"
        for choice, _value in FRIENDLY_GAME_PLATFORMS
    )
    options.append(
        f'<option value="custom"{" selected" if selected_choice == "custom" else ""}>'
        f"{_t(locale, 'creation.platform.custom')}</option>"
    )
    return (
        f"<label>{_t(locale, 'settings.preferences.platform')}"
        f'<select name="platform_choice">{"".join(options)}</select></label>'
        f'<label class="custom-platform-field">{_t(locale, "settings.preferences.custom_platform")}'
        f'<input name="custom_platform" maxlength="120" '
        f'value="{escape(custom_value, quote=True)}"></label>'
    )


def _preferences(
    profile: LocalFrontendProfileV1 | None,
    *,
    generation: int,
    locale: str,
) -> str:
    own_player_id = None if profile is None else profile.own_player_id
    advanced = (
        False if profile is None else profile.interface_preferences.advanced_settings_expanded
    )
    return (
        '<section class="settings-panel" aria-labelledby="creation-defaults-heading">'
        f'<h3 id="creation-defaults-heading">'
        f"{_t(locale, 'settings.preferences.heading')}</h3>"
        f"<p>{_t(locale, 'settings.preferences.help')}</p>"
        f'<form method="post" action="{FRONTEND_PROFILE_PREFERENCES_ACTION_ROUTE}">'
        + _generation(generation)
        + f"<label>{_t(locale, 'settings.preferences.own_player')}"
        f'<select name="own_player_handle">'
        f"{_player_options(profile, selected_id=own_player_id, locale=locale)}"
        "</select></label>"
        + _platform_fields(profile, locale=locale)
        + f'<label><input type="checkbox" name="advanced_settings_expanded" value="on"'
        f"{' checked' if advanced else ''}> "
        f"{_t(locale, 'settings.preferences.advanced')}</label>"
        f"<p>{_t(locale, 'settings.preferences.advanced_help')}</p>"
        f'<button type="submit">{_t(locale, "settings.preferences.save")}</button>'
        "</form></section>"
    )


def _action(action, label, *, handle, generation, locale, selection=None):
    return (
        f'<form method="post" action="/actions/profile/players/{action}">'
        + _generation(generation)
        + f'<input type="hidden" name="player_handle" value="{handle}">'
        + (f'<input type="hidden" name="editor_selection" value="{selection}">'
           if selection is not None else '')
        + f'<button type="submit">{_t(locale, label)}</button></form>'
    )


def _player_card(
    player,
    *,
    profile: LocalFrontendProfileV1,
    generation: int,
    locale: str,
    editor: SettingsEditorV1 | None,
) -> str:
    handle = build_known_player_handle_v1(player.player_id)
    own = (f' <span class="own-player">{_t(locale, "settings.preferences.own_player")}</span>'
           if player.player_id == profile.own_player_id else "")
    expanded = editor is not None and editor.player_handle == handle
    return (
        '<article class="known-player-card">'
        f"<p><strong>{escape(player.display_name)}</strong>{own}</p>"
        '<div class="player-actions">'
        + _action("edit", "settings.players.edit", handle=handle,
                  generation=generation, locale=locale)
        + _action("remove-preview", "settings.players.remove", handle=handle,
                  generation=generation, locale=locale)
        + '</div>'
        + (_editor(profile, player, editor, generation=generation, locale=locale)
           if expanded else "")
        + '</article>'
    )


def _account_fields(locale, account=None):
    platform = "" if account is None else account.platform
    account_id = "" if account is None else account.player_id
    return (
        f'<label>{_t(locale, "settings.players.account_platform")}'
        f'<input name="account_platform" maxlength="120" value="{escape(platform, quote=True)}">'
        '</label>'
        f'<label>{_t(locale, "settings.players.account_id")}'
        f'<input name="account_id" maxlength="255" value="{escape(account_id, quote=True)}">'
        '</label>'
        f'<p>{_t(locale, "settings.players.account_help")}</p>'
    )


def _editor(profile, player, editor, *, generation, locale):
    handle = "" if player is None else build_known_player_handle_v1(player.player_id)
    transport = (_generation(generation)
                 + f'<input type="hidden" name="player_handle" value="{handle}">')
    cancel = _action("cancel", "settings.players.cancel", handle=handle,
                     generation=generation, locale=locale, selection=editor.confirmation)
    if editor.kind in {"remove", "accounts"}:
        effects = []
        if editor.kind == "remove":
            for reference, key in ((profile.own_player_id, "own"),
                    (profile.preferred_perspective_player_id, "preferred")):
                if reference == player.player_id:
                    effects.append(f'<li>{_t(locale, f"settings.players.removal_{key}")}</li>')
            detail = '<ul>' + ''.join(effects) + '</ul>' if effects else ''
            action = FRONTEND_PROFILE_PLAYER_REMOVE_ACTION_ROUTE
        else:
            old = '; '.join(f'{a.platform}: {a.player_id}' for a in player.platform_player_ids)
            new = '; '.join(f'{a.platform}: {a.player_id}' for a in editor.accounts)
            detail = (f'<p>{_t(locale, "settings.players.accounts_before")}: {escape(old)}</p>'
                      f'<p>{_t(locale, "settings.players.accounts_after")}: '
                      f'{escape(new) if new else _t(locale, "settings.players.none")}</p>')
            action = '/actions/profile/players/accounts-replace'
        current = editor.generation == generation and time.monotonic() - editor.created_at < 1800
        confirmation = (
            f'<form method="post" action="{action}">{transport}'
            f'<input type="hidden" name="confirmation_selection" value="{editor.confirmation}">'
            f'<label><input type="checkbox" name="confirm_replace" value="on" required> '
            f'{_t(locale, "settings.players.confirm_change")}</label>'
            f'<button type="submit">{_t(locale, "settings.players.confirm_action")}</button></form>'
            if current else f'<p>{_t(locale, "settings.players.preview_expired")}</p>'
        )
        heading = _t(locale, f"settings.players.preview_{editor.kind}", name=player.display_name)
        return (
            '<section class="player-editor" tabindex="-1">'
            f'<p><strong>{heading}</strong></p>'
            f'{detail}<p>{_t(locale, "settings.players.recordings_unchanged")}</p>'
            f'{confirmation}{cancel}</section>'
        )
    name = '' if player is None else player.display_name
    action = (FRONTEND_PROFILE_PLAYER_ADD_ACTION_ROUTE if player is None
              else FRONTEND_PROFILE_PLAYER_UPDATE_ACTION_ROUTE)
    account_controls = _account_fields(locale) if player is None else (
        '<input type="hidden" name="account_action" value="keep">'
        '<p>' + _t(locale, "settings.players.legacy_accounts",
                   count=len(player.platform_player_ids)) + '</p>'
        if len(player.platform_player_ids) > 1 else
        f'<label>{_t(locale, "settings.players.account_action")}<select name="account_action">'
        f'<option value="keep">{_t(locale, "settings.players.account_keep")}</option>'
        f'<option value="edit">{_t(locale, "settings.players.account_edit")}</option>'
        '</select></label>'
        '<div class="account-edit-fields">'
        + _account_fields(locale, next(iter(player.platform_player_ids), None)) + '</div>'
    )
    replacement = ''
    if player is not None and len(player.platform_player_ids) > 1:
        replacement = (
            f'<details><summary>{_t(locale, "settings.players.replace_accounts")}</summary>'
            '<form method="post" action="/actions/profile/players/accounts-preview">'
            + transport + _account_fields(locale)
            + f'<button type="submit">{_t(locale, "settings.players.preview_action")}</button>'
            '</form></details>'
        )
    return (
        '<div class="player-editor">'
        f'<form method="post" action="{action}">{transport if player else _generation(generation)}'
        f'<label>{_t(locale, "settings.players.display_name")}'
        f'<input name="display_name" maxlength="120" required '
        f'value="{escape(name, quote=True)}"></label>'
        f'{account_controls}<button type="submit">{_t(locale, "settings.players.save")}</button>'
        f'</form>{replacement}{cancel}</div>'
    )


def _players(
    profile: LocalFrontendProfileV1 | None,
    *,
    generation: int,
    locale: str,
    editor: SettingsEditorV1 | None,
) -> str:
    cards = (
        ""
        if profile is None
        else "".join(
            _player_card(
                player,
                profile=profile,
                generation=generation,
                locale=locale,
                editor=editor,
            )
            for player in profile.known_players
        )
    )
    empty_players = f"<p>{_t(locale, 'settings.players.empty')}</p>"
    return (
        '<section class="settings-panel" aria-labelledby="known-players-heading">'
        f'<h3 id="known-players-heading">{_t(locale, "settings.players.heading")}</h3>'
        f"<p>{_t(locale, 'settings.players.help')}</p>"
        f'<div class="known-player-grid">{cards or empty_players}</div>'
        + _action("edit", "settings.players.add", handle="", generation=generation, locale=locale)
        + (_editor(profile, None, editor, generation=generation, locale=locale)
           if editor is not None and editor.kind == "edit" and not editor.player_handle else "")
        + '</section>'
    )


def _recommended_reset(*, generation: int, locale: str) -> str:
    return (
        '<section class="settings-panel" aria-labelledby="recommended-reset-heading">'
        f'<h3 id="recommended-reset-heading">'
        f"{_t(locale, 'settings.recommended_reset.heading')}</h3>"
        f"<p>{_t(locale, 'settings.recommended_reset.help')}</p>"
        f'<form method="post" action="{FRONTEND_PROFILE_RECOMMENDED_RESET_ACTION_ROUTE}">'
        + _generation(generation)
        + '<label><input type="checkbox" name="confirm_recommended_reset" '
        'value="on" required> '
        f"{_t(locale, 'settings.recommended_reset.confirm')}</label>"
        f'<button type="submit">{_t(locale, "settings.recommended_reset.action")}</button>'
        "</form></section>"
    )


def render_local_settings_v1(
    *,
    profile: LocalFrontendProfileV1 | None,
    profile_generation: int,
    profile_valid: bool,
    locale: str,
    editor: SettingsEditorV1 | None = None,
) -> str:
    if type(profile_generation) is not int or profile_generation < 0:
        raise ValueError("profile_generation must be a non-negative integer.")
    if type(profile_valid) is not bool:
        raise ValueError("profile_valid must be a boolean.")
    if not profile_valid:
        return f"<p>{_t(locale, 'settings.invalid_reset_only')}</p>"
    return (
        '<div class="local-settings">'
        + _players(
            profile,
            generation=profile_generation,
            locale=locale,
            editor=editor,
        )
        + _preferences(
            profile,
            generation=profile_generation,
            locale=locale,
        )
        + render_time_zone_settings(profile, profile_generation, locale)
        + _recommended_reset(generation=profile_generation, locale=locale)
        + "</div>"
    )
