"""Private, lossless adapters for the compact Settings forms."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

from .frontend_profile_operations import (
    FRONTEND_SETTINGS_PLAYER_ACTION_ROUTES,
    StaleFrontendProfileGenerationError,
)
from .profile_player_contracts import MAX_KNOWN_PLAYERS, KnownPlayerPlatformIdV1, KnownPlayerV1
from .profile_player_operations import (
    _current_document,
    add_known_player_v1,
    remove_known_player_v1,
    replace_known_player_v1,
    resolve_known_player_handle_v1,
    set_frontend_creation_preferences_v1,
)

SETTINGS_PLAYER_ROUTES = FRONTEND_SETTINGS_PLAYER_ACTION_ROUTES


@dataclass(frozen=True, slots=True)
class SettingsEditorV1:
    kind: str
    player_handle: str = ""
    generation: int = 0
    player: KnownPlayerV1 | None = None
    accounts: tuple[KnownPlayerPlatformIdV1, ...] = ()
    confirmation: str = ""
    created_at: float = 0


class SettingsFieldError(ValueError):
    def __init__(self, field_key, message):
        super().__init__(message)
        self.field_key = field_key


def account_pair_v1(values: dict[str, str]) -> tuple[KnownPlayerPlatformIdV1, ...]:
    platform = values.get("account_platform", "").strip()
    account_id = values.get("account_id", "").strip()
    if not platform and not account_id:
        return ()
    try:
        return (KnownPlayerPlatformIdV1(platform, account_id),)
    except ValueError as error:
        field = "account_platform" if not platform or len(platform) > 120 else "account_id"
        raise SettingsFieldError(field, str(error)) from error


def edit_player_v1(context, values, *, generation, entropy_source):
    """An explicit keep operation preserves every legacy tuple verbatim."""
    document = _current_document(context, expected_generation=generation)
    name = values["display_name"].strip()
    from .profile_player_contracts import normalize_player_display_name_v1
    try:
        normalize_player_display_name_v1(name)
    except ValueError as error:
        raise SettingsFieldError("display_name", str(error)) from error
    handle = values.get("player_handle", "")
    if not handle:
        if document is not None and len(document.known_players) >= MAX_KNOWN_PLAYERS:
            raise ValueError("known_players may contain at most 512 Players.")
        accounts = account_pair_v1(values)
        # Validate every value before requesting a generated identity.
        KnownPlayerV1("frontend-player-" + "0" * 64, name, (), accounts)
        return add_known_player_v1(context, display_name=name, aliases=(),
            platform_player_ids=accounts, expected_generation=generation,
            entropy_source=entropy_source)
    player = resolve_known_player_handle_v1(document, handle)
    action = values.get("account_action")
    if action == "keep":
        accounts = player.platform_player_ids
    elif action == "edit" and len(player.platform_player_ids) <= 1:
        accounts = account_pair_v1(values)
    else:
        raise ValueError("Account action must be one supported explicit choice.")
    return replace_known_player_v1(context, player_handle=handle, display_name=name,
        aliases=player.aliases, platform_player_ids=accounts, expected_generation=generation)


def set_ordinary_preferences_v1(context, values, *, generation):
    from .profile_driven_creation import resolve_friendly_game_platform_v1

    document = _current_document(context, expected_generation=generation)
    handle = values["own_player_handle"]
    own_id = resolve_known_player_handle_v1(document, handle).player_id if handle else None
    choice, custom = values["platform_choice"], values["custom_platform"]
    if not choice and custom.strip():
        raise ValueError("custom_platform requires one supported platform choice.")
    platform = resolve_friendly_game_platform_v1(choice, custom) if choice else None
    advanced = values.get("advanced_settings_expanded", "")
    if advanced not in {"", "on"}:
        raise ValueError("advanced_settings_expanded must be one explicit checkbox value.")
    return set_frontend_creation_preferences_v1(context, own_player_id=own_id,
        preferred_perspective_player_id=(
            None if document is None else document.preferred_perspective_player_id),
        preferred_game_platform=platform, advanced_settings_expanded=advanced == "on",
        expected_generation=generation)


def select_settings_editor_v1(context, *, kind, handle, generation, accounts=()):
    document = _current_document(context, expected_generation=generation)
    player = resolve_known_player_handle_v1(document, handle) if handle else None
    if kind != "edit" and player is None:
        raise ValueError("Select one known Player.")
    with context.lock:
        if context.frontend_profile.generation != generation:
            raise StaleFrontendProfileGenerationError
        context.settings_serial += 1
        token = hmac.new(context.language_context.key,
            f"settings\0{context.settings_serial}\0{generation}\0{kind}\0{handle}".encode(),
            hashlib.sha256).hexdigest()
        context.settings_editor = SettingsEditorV1(
            kind, handle, generation, player, accounts, token, time.monotonic())


def confirm_player_change_v1(context, values, *, kind, generation):
    """Consume one exact generation/target-bound preview before attempting CAS."""
    document = _current_document(context, expected_generation=generation)
    with context.lock:
        editor = context.settings_editor
        if (editor is None or editor.kind != kind or editor.generation != generation
                or editor.player_handle != values.get("player_handle")
                or editor.confirmation != values.get("confirmation_selection")
                or time.monotonic() - editor.created_at >= 1800
                or editor.player != resolve_known_player_handle_v1(document, editor.player_handle)):
            raise StaleFrontendProfileGenerationError
        if values.get("confirm_replace") != "on":
            raise ValueError("Explicit confirmation is required.")
        context.settings_editor = None
    if kind == "remove":
        return remove_known_player_v1(context, player_handle=editor.player_handle,
            confirm_referenced=True, expected_generation=generation)
    return replace_known_player_v1(context, player_handle=editor.player_handle,
        display_name=editor.player.display_name, aliases=editor.player.aliases,
        platform_player_ids=editor.accounts, expected_generation=generation)


def dispatch_settings_form_v1(context, path, values, *, generation, entropy_source):
    """Exact private form parsing; no absent-field deletion convention."""
    action = path.rsplit("/", 1)[1]
    fields = {"profile_generation"}
    if action == "preferences":
        fields |= {"own_player_handle", "platform_choice", "custom_platform",
                   "advanced_settings_expanded"}
        values.setdefault("advanced_settings_expanded", "")
    else:
        if action != "add":
            fields.add("player_handle")
        if action in {"add", "update", "accounts-preview"}:
            fields |= {"account_platform", "account_id"}
            values.setdefault("account_platform", "")
            values.setdefault("account_id", "")
        if action in {"add", "update"}:
            fields.add("display_name")
        if action == "update":
            fields.add("account_action")
        if action == "cancel":
            fields.add("editor_selection")
        if action in {"remove", "accounts-replace"}:
            fields |= {"confirmation_selection", "confirm_replace"}
            values.setdefault("confirm_replace", "")
    if set(values) != fields:
        raise ValueError("Use the current Settings form; unsupported or missing fields.")
    _current_document(context, expected_generation=generation)
    if action in {"add", "update"}:
        edit_player_v1(context, values, generation=generation, entropy_source=entropy_source)
    elif action == "preferences":
        set_ordinary_preferences_v1(context, values, generation=generation)
    elif action in {"edit", "remove-preview", "accounts-preview"}:
        kinds = {"edit": "edit", "remove-preview": "remove", "accounts-preview": "accounts"}
        select_settings_editor_v1(context,
            kind=kinds[action],
            handle=values["player_handle"], generation=generation,
            accounts=account_pair_v1(values) if action == "accounts-preview" else ())
        return
    elif action in {"remove", "accounts-replace"}:
        confirm_player_change_v1(context, values,
            kind="remove" if action == "remove" else "accounts", generation=generation)
    elif action != "cancel":
        raise ValueError("Unsupported Settings action.")
    with context.lock:
        if action == "cancel":
            editor = context.settings_editor
            if (editor is None or editor.player_handle != values["player_handle"]
                    or editor.confirmation != values["editor_selection"]):
                raise StaleFrontendProfileGenerationError
        context.settings_editor = None
