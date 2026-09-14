from __future__ import annotations

from typing import Final

from .contracts import APP_HOME_TASK_ROUTES

FRONTEND_INFORMATION_ARCHITECTURE_VERSION = 1

HOME_GROUP_KEYS: Final[tuple[str, ...]] = (
    "record_games",
    "analyze_and_review",
    "learn_across_matches",
)
HOME_TASK_KEYS: Final[tuple[str, ...]] = (
    "record_match",
    "record_session",
    "review_game",
    "analyze_decision",
    "learning_insights",
)
HOME_TASK_ROUTE_MAPPINGS: Final[tuple[tuple[str, str], ...]] = (
    ("record_match", "/matches"),
    ("record_session", "/sessions"),
    ("review_game", "/review/recorded"),
    ("analyze_decision", "/analyze"),
    ("learning_insights", "/learning"),
)
HOME_GROUP_TASK_MEMBERSHIP: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("record_games", ("record_match", "record_session")),
    ("analyze_and_review", ("review_game", "analyze_decision")),
    ("learn_across_matches", ("learning_insights",)),
)
HOME_RELATED_TASK_MEMBERSHIP: Final[tuple[tuple[str, tuple[str, ...]], ...]] = ()
FRONTEND_EMPTY_STATE_KEYS: Final[tuple[str, ...]] = (
    "sessions",
    "matches",
    "learning_collections",
    "learning_data",
)


def _require_exact_tuple(value: object, expected: tuple, field_name: str) -> None:
    if type(value) is not tuple or value != expected:
        raise ValueError(f"{field_name} must contain the exact canonical ordered values.")


def validate_frontend_information_architecture_v1(
    *,
    version: int = FRONTEND_INFORMATION_ARCHITECTURE_VERSION,
    group_keys: tuple[str, ...] = HOME_GROUP_KEYS,
    task_keys: tuple[str, ...] = HOME_TASK_KEYS,
    task_routes: tuple[tuple[str, str], ...] = HOME_TASK_ROUTE_MAPPINGS,
    group_membership: tuple[tuple[str, tuple[str, ...]], ...] = (
        HOME_GROUP_TASK_MEMBERSHIP
    ),
    related_membership: tuple[tuple[str, tuple[str, ...]], ...] = (
        HOME_RELATED_TASK_MEMBERSHIP
    ),
    empty_state_keys: tuple[str, ...] = FRONTEND_EMPTY_STATE_KEYS,
) -> None:
    """Rejects drift in the private Home contract revised by Issue #229."""

    if type(version) is not int or version != FRONTEND_INFORMATION_ARCHITECTURE_VERSION:
        raise ValueError("version must equal the frontend information architecture version.")
    for value, expected, field_name in (
        (group_keys, HOME_GROUP_KEYS, "group_keys"),
        (task_keys, HOME_TASK_KEYS, "task_keys"),
        (task_routes, HOME_TASK_ROUTE_MAPPINGS, "task_routes"),
        (group_membership, HOME_GROUP_TASK_MEMBERSHIP, "group_membership"),
        (related_membership, HOME_RELATED_TASK_MEMBERSHIP, "related_membership"),
        (empty_state_keys, FRONTEND_EMPTY_STATE_KEYS, "empty_state_keys"),
    ):
        _require_exact_tuple(value, expected, field_name)

    mapped_task_keys = tuple(task_key for task_key, _route in task_routes)
    mapped_routes = tuple(route for _task_key, route in task_routes)
    grouped_task_keys = tuple(
        task_key
        for _group_key, member_task_keys in group_membership
        for task_key in member_task_keys
    )
    if mapped_task_keys != task_keys or grouped_task_keys != task_keys:
        raise ValueError("Every Home task must be mapped and grouped exactly once.")
    if tuple(group_key for group_key, _members in group_membership) != group_keys:
        raise ValueError("Every Home group must have exact ordered membership.")
    if mapped_routes != APP_HOME_TASK_ROUTES:
        raise ValueError("Home task Routes must cover the five ordered task Routes exactly.")
