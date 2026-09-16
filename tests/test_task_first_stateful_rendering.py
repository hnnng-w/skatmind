from pathlib import Path

import pytest
from test_match_workspace_contracts import _definition
from test_task_first_stateful_projections import session_states

from skatmind.app_web.session_frontend import GuidedSessionContextV1
from skatmind.app_web.task_first_learning_rendering import render_task_first_learning_v1
from skatmind.app_web.task_first_match_rendering import render_task_first_match_v1
from skatmind.app_web.task_first_projections import project_task_first_match_v1
from skatmind.app_web.task_first_session_rendering import render_task_first_session_v1
from skatmind.app_web.translation_catalog import translate_frontend_message_v1 as t
from skatmind.capture_web.state import build_match_capture_web_state_v1
from skatmind.corpus_web.context import LearningCorpusWebContextV1
from skatmind.corpus_web.operations import initialize_learning_corpus_web_v1
from skatmind.corpus_web.state import build_learning_corpus_web_state_v1
from skatmind.match_workspace_contracts import create_match_workspace_v1
from skatmind.session_commands import SESSION_COMMAND_KINDS
from skatmind.session_persistence_codec import build_session_persistence_document_v1


@pytest.mark.parametrize("locale", ("en", "de"))
def test_session_render_all_phases_and_all_commands(tmp_path: Path, locale):
    seen = set()
    for state in session_states():
        if state.phase in seen and state.phase != "play":
            continue
        seen.add(state.phase)
        context = GuidedSessionContextV1(category_root=tmp_path, path=tmp_path / "game.json",
            handle="a" * 64, document=build_session_persistence_document_v1(state))
        original = context.document
        html = render_task_first_session_v1(context, locale=locale)
        mode = "perspective" if state.capture_mode == "live" else "reconstruction"
        assert t(locale, "session.knowledge.accepted_mode",
                 mode=t(locale, f"session.knowledge.{mode}")) in html
        assert t(locale, "creation.session.after_help") not in html
        assert t(locale, "task.session.next.promote_to_retrospective") not in html
        headings = [html.index('<h2>' + t(locale, key) + '</h2>') for key in (
            "task.session.state", "task.session.next", "task.session.entered")]
        assert headings == sorted(headings)
        assert headings[1] < html.index('id="session-recording"') < headings[2]
        assert all(f'name="kind" value="{kind}"' in html for kind in SESSION_COMMAND_KINDS
                   if kind != "set_declaration")
        # Declaration correction is rendered only for its actual accepted target.
        accepted = any(record.command.kind == "set_declaration" for record in state.command_log)
        assert ('value="session-correction"' in html) is accepted
        assert context.document is original
        assert '<script' not in html


@pytest.mark.parametrize("locale", ("en", "de"))
def test_match_empty_render_has_named_36_positions_and_explicit_choices(locale):
    workspace = create_match_workspace_v1(_definition())
    state = build_match_capture_web_state_v1(workspace, workspace_filename="managed-match.json")
    view = project_task_first_match_v1(workspace, selected_position=1)
    html = render_task_first_match_v1(state, view, managed_handle="b" * 64, locale=locale)
    assert html.count('class="match-tile ') + html.count('class="match-tile"') == 36
    assert t(locale, "task.match.action.start_game") in html
    assert t(locale, "task.match.action.mark_passed_deal") in html
    assert '<script' not in html


@pytest.mark.parametrize("locale", ("en", "de"))
def test_learning_empty_sequence_precedes_import_and_has_no_build(tmp_path, locale):
    context = LearningCorpusWebContextV1.open(tmp_path / "collection")
    initialize_learning_corpus_web_v1(context, corpus_id="private-collection")
    state = build_learning_corpus_web_state_v1(context)
    html = render_task_first_learning_v1(state, managed_handle="c" * 64, locale=locale)
    for key in ("next.add", "recorded_help", "no_recorded", "refresh_recorded"):
        assert t(locale, f"task.learning.{key}") in html
    assert 'value="prepare_learning_artifacts"' not in html
    assert html.index(t(locale, "task.learning.next")) < html.index('name="workspace_file"')
    assert '<script' not in html
