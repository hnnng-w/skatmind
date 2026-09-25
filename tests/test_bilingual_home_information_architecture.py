from __future__ import annotations

import re
from dataclasses import asdict

import pytest

import skatmind
import skatmind.api.v1 as public_api
from skatmind.app_web.information_architecture import (
    FRONTEND_EMPTY_STATE_KEYS,
    FRONTEND_INFORMATION_ARCHITECTURE_VERSION,
    HOME_GROUP_KEYS,
    HOME_GROUP_TASK_MEMBERSHIP,
    HOME_RELATED_TASK_MEMBERSHIP,
    HOME_TASK_KEYS,
    HOME_TASK_ROUTE_MAPPINGS,
    validate_frontend_information_architecture_v1,
)
from skatmind.app_web.localization_contracts import BrowserSafeFrontendProfileStateV1
from skatmind.app_web.rendering import render_app_content_page_v1, render_app_page_v1
from skatmind.app_web.state import build_browser_safe_application_state_v1


def _frontend(locale: str) -> BrowserSafeFrontendProfileStateV1:
    return BrowserSafeFrontendProfileStateV1(
        locale=locale,
        resolution_source="fallback" if locale == "en" else "browser",
        profile_status="absent",
        profile_revision=None,
        profile_generation=0,
        warning=False,
    )


def test_information_architecture_contract_values_are_exact_and_private() -> None:
    assert FRONTEND_INFORMATION_ARCHITECTURE_VERSION == 1
    assert HOME_GROUP_KEYS == (
        "record_games",
        "analyze_and_review",
        "learn_across_matches",
    )
    assert HOME_TASK_KEYS == (
        "record_match",
        "record_session",
        "review_game",
        "analyze_decision",
        "learning_insights",
    )
    assert HOME_TASK_ROUTE_MAPPINGS == (
        ("record_match", "/matches"),
        ("record_session", "/sessions"),
        ("review_game", "/review/recorded"),
        ("analyze_decision", "/analyze"),
        ("learning_insights", "/learning"),
    )
    assert HOME_GROUP_TASK_MEMBERSHIP == (
        ("record_games", ("record_match", "record_session")),
        ("analyze_and_review", ("review_game", "analyze_decision")),
        ("learn_across_matches", ("learning_insights",)),
    )
    assert HOME_RELATED_TASK_MEMBERSHIP == ()
    assert FRONTEND_EMPTY_STATE_KEYS == (
        "sessions",
        "matches",
        "learning_collections",
        "learning_data",
    )
    validate_frontend_information_architecture_v1()
    for name in (
        "FRONTEND_INFORMATION_ARCHITECTURE_VERSION",
        "HOME_GROUP_KEYS",
        "HOME_TASK_KEYS",
    ):
        assert name not in skatmind.__all__ and not hasattr(skatmind, name)
        assert name not in public_api.__all__ and not hasattr(public_api, name)


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("version", True),
        ("version", 2),
        ("group_keys", tuple(reversed(HOME_GROUP_KEYS))),
        ("group_keys", (*HOME_GROUP_KEYS, "extra")),
        ("task_keys", (*HOME_TASK_KEYS[:-1], HOME_TASK_KEYS[0])),
        ("task_keys", HOME_TASK_KEYS[:-1]),
        ("task_routes", tuple(reversed(HOME_TASK_ROUTE_MAPPINGS))),
        (
            "task_routes",
            (*HOME_TASK_ROUTE_MAPPINGS[:-1], ("orphan", "/about")),
        ),
        ("group_membership", tuple(reversed(HOME_GROUP_TASK_MEMBERSHIP))),
        (
            "group_membership",
            (*HOME_GROUP_TASK_MEMBERSHIP[:-1], ("product_information", ())),
        ),
    ),
)
def test_information_architecture_rejects_drift(
    field_name: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        validate_frontend_information_architecture_v1(**{field_name: value})


@pytest.mark.parametrize(
    ("locale", "group_headings", "task_titles", "guide_heading"),
    (
        (
            "en",
            (
                "Record games",
                "Analyze and review",
                "Learn across Matches",
            ),
            (
                "Record a 36-game Match",
                "Record an individual game",
                "Review recorded games",
                "Analyze one decision",
            ),
            "Which area do I need?",
        ),
        (
            "de",
            (
                "Spiele erfassen",
                "Analysieren und auswerten",
                "Über mehrere Matches lernen",
            ),
            (
                "36er-Match erfassen",
                "Einzelspiel erfassen",
                "Erfasste Spiele auswerten",
                "Eine Entscheidung analysieren",
            ),
            "Welchen Bereich brauche ich?",
        ),
    ),
)
def test_home_groups_match_first_recorded_review_and_fifth_learning_card(
    locale: str,
    group_headings: tuple[str, ...],
    task_titles: tuple[str, ...],
    guide_heading: str,
) -> None:
    state = build_browser_safe_application_state_v1()
    retained_state = asdict(state)
    html = render_app_page_v1(state, "/", frontend=_frontend(locale))
    main = html[html.index("<main") : html.index("</main>")]
    groups_html = main[main.index('<section class="home-group"') :]

    assert f'<html lang="{locale}">' in html
    assert html.count('<section class="home-group"') == 3
    assert html.count('<article class="task-card">') == 5
    cards = re.findall(r'<article class="task-card">(.*?)</article>', main, re.DOTALL)
    assert [re.search(r'href="([^"]+)"', card)[1] for card in cards] == [
        route for _, route in HOME_TASK_ROUTE_MAPPINGS]
    assert all('<h3>' in card and 'class="task-summary"' in card
               and 'class="button-link"' in card for card in cards)
    assert 'class="task-disclosure"' not in html
    assert 'class="task-scope"' not in html
    assert html.count('class="task-action"') == 5
    assert guide_heading not in html and 'class="scope-guide"' not in html
    assert 'href="/about"' not in main
    assert '<a href="/about">' in html.split('<footer>')[1]
    assert 'href="/review/recorded"' in main and 'href="/review"' not in main
    assert [groups_html.index(value) for value in group_headings] == sorted(
        groups_html.index(value) for value in group_headings
    )
    assert [groups_html.index(value) for value in task_titles] == sorted(
        groups_html.index(value) for value in task_titles
    )
    assert groups_html.index(task_titles[0]) < groups_html.index(task_titles[1])
    assert groups_html.index('href="/matches"') < groups_html.index('href="/sessions"')
    assert "Available now." not in html and "Jetzt verfügbar." not in html
    assert "Live</dd>" not in html
    assert "english-workflow-body" not in html
    assert asdict(state) == retained_state


def test_short_introductions_replace_generic_related_panels_without_losing_controls() -> None:
    state = build_browser_safe_application_state_v1()
    for route in ("/analyze", "/review", "/sessions", "/matches", "/learning"):
        html = render_app_content_page_v1(
            state,
            route,
            title="Retained workflow title",
            content='<h2>Current task</h2><a href="/matches/current">Resolve prerequisite</a>',
            frontend=_frontend("en"),
        )
        assert 'class="related-areas"' not in html and 'class="concept-guide"' not in html
        assert html.count('<h1>') == 1 and html.count('class="entry-introduction"') == 1
        assert '<a href="/matches/current">Resolve prerequisite</a>' in html

    analyze = render_app_page_v1(state, "/analyze", frontend=_frontend("en"))
    assert "current or retrospective Card choice" in analyze
    review = render_app_page_v1(state, "/review", frontend=_frontend("en"))
    assert "has not already been recorded" in review

    german = render_app_content_page_v1(
        state,
        "/sessions",
        title="Retained workflow title",
        content="<p>Retained user text</p>",
        frontend=_frontend("de"),
        empty_state_key="sessions",
    )
    assert ('<p class="entry-introduction">Ein Spiel erfassen oder eine gespeicherte '
            'Aufzeichnung öffnen.</p>') in german
    assert "Noch keine erfassten einzelnen Spiele" in german
    assert german.index("Noch keine erfassten einzelnen Spiele") < german.index(
        "<p>Retained user text</p>"
    )
    assert "english-workflow-body" not in german
