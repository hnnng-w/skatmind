from html.parser import HTMLParser
from importlib.resources import files

import pytest
from test_bilingual_home_information_architecture import _frontend
from test_task_first_stateful_projections import session_states

from skatmind.app_web.guided_rendering import render_analyze_workflow_v1, render_review_workflow_v1
from skatmind.app_web.localization_contracts import (
    BILINGUAL_FRONTEND_POLICIES,
    IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES,
)
from skatmind.app_web.rendering import render_app_page_v1
from skatmind.app_web.state import build_browser_safe_application_state_v1
from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1
from skatmind.app_web.workflow_state import ProcessLocalFrontendWorkflowStateV1


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []

    def handle_data(self, data):
        if data.strip():
            self.values.append(data.strip())


@pytest.mark.parametrize("locale", ("en", "de"))
def test_shell_and_guided_route_matrix_uses_locale_without_transitional_regions(tmp_path, locale):
    for route in ("/", "/about", "/analyze", "/review"):
        html = render_app_page_v1(build_browser_safe_application_state_v1(), route,
            frontend=_frontend(locale), storage_root=tmp_path if route == "/about" else None)
        assert f'<html lang="{locale}">' in html
        assert "english-workflow-body" not in html and "translation-status" not in html
        assert 'name="language"' in html
    if locale == "de":
        for renderer in (render_analyze_workflow_v1, render_review_workflow_v1):
            html = renderer(ProcessLocalFrontendWorkflowStateV1(), locale=locale)
            parsed = VisibleText()
            parsed.feed(html)
            for forbidden in ("Advanced Settings", "Run analysis", "Game type", "Player role",
                              "Import JSON", "No Card", "Card play", "Review options"):
                assert forbidden not in parsed.values


def test_complete_policy_catalog_and_packaged_projection_modules():
    assert IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES == BILINGUAL_FRONTEND_POLICIES
    catalogs = load_frontend_translation_catalogs_v1()
    assert tuple(catalogs["en"]) == tuple(catalogs["de"]) == tuple(sorted(catalogs["en"]))
    assert "translation.english_body_notice" not in catalogs["en"]
    resources = files("skatmind.app_web")
    for name in ("task_first_contracts.py", "task_first_projections.py",
                 "task_first_session_rendering.py", "task_first_match_rendering.py",
                 "task_first_learning_rendering.py", "language_form_preservation.py",
                 "assets/workflow.js", "locales/en.json", "locales/de.json"):
        assert resources.joinpath(name).is_file()
    script = resources.joinpath("assets/workflow.js").read_text("utf-8")
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "XMLHttpRequest", "http://", "https://"):
        assert forbidden not in script


def test_phase_matrix_fixture_covers_all_retained_phases():
    assert {state.phase for state in session_states()} == {
        "setup", "deal", "declaration", "skat_and_discard", "play", "ended"}
