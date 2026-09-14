# ruff: noqa: E501 - Keep complete server-rendered elements legible.
from __future__ import annotations

from .compact_declaration_rendering import accepted_declaration_summary
from .recorded_trick_rendering import render_recorded_summary
from .stateful_localization import text, translated
from .task_first_match_rendering import _named_seat, _reports, operation_form
from .task_first_rendering import disclosure, hidden, paragraph, section, select_field


def render_match_analysis_v1(state, view, handle, locale):
    game = state["game"]
    content = paragraph(locale, "recordings.match.coverage")
    if game is None:
        return content + paragraph(locale, f"task.match.status.{view.selected.slot_kind}")
    preparation = state["decision_preparation"]
    ready = preparation["prepared_decision_count"] > 0
    content += paragraph(locale, "recordings.match.prepared",
                         prepared=preparation["prepared_decision_count"], total=preparation["source_play_count"])
    if ready:
        content += operation_form(state, handle, locale, "analyze_decision", analysis=True, primary=True, values={
            "immediate_sample_count": 100, "immediate_random_seed": 0, "search_random_seed": 0,
            "search_budget_profile": "historical_review_v1", "recommendation_method": "immediate_expected_value",
            "use_profile_presets": True})
    else:
        content += paragraph(locale, "task.match.decision_blocked")
    skipped = ''
    for row in preparation["decisions"]:
        if row["state"] == "skipped":
            skipped += '<li>' + translated(locale, "recordings.match.decision",
                trick=(row["decision_index"] - 1) // 3 + 1,
                player=_named_seat(state, locale, row["acting_player_id"]), card=row["actual_card"])
            skipped += ' — ' + translated(locale, f"recordings.skip.{row['reason']}") + '</li>'
    if skipped:
        content += disclosure(locale, "recordings.match.skipped", '<ul>' + skipped + '</ul>')
    evidence = view.selected.evidence_summary
    historical_ready = (evidence is not None and evidence.complete_initial_deal_reconstructable
                        and state["match"]["played_at"] is not None)
    historical = paragraph(locale, "recordings.match.historical")
    if not historical_ready:
        historical += paragraph(locale, "task.match.historical_blocked")
    historical += operation_form(state, handle, locale, "analyze_historical_game", analysis=True,
        disabled=not historical_ready, values={"immediate_sample_count": 100,
            "immediate_random_seed": 0, "search_random_seed": 0,
            "search_budget_profile": "historical_review_v1", "immediate_review": True,
            "use_profile_presets": True})
    return content + disclosure(locale, "task.match.action.analyze_historical_game", historical)


def render_match_review_v1(state, view, *, managed_handle, locale, transfer=""):
    position = view.selected_position
    body = '<div id="match-review" tabindex="-1">'
    body += '<form method="get" class="match-review-selector" action="/matches/review/' + str(position) + '">'
    body += select_field(locale, "position", "recordings.match.select", tuple(
        (item.match_position, text(locale, "task.match.position", number=item.match_position)
         + ' — ' + text(locale, f"task.match.status.{item.game_state}")) for item in view.positions), position)
    body += '<button type="submit">' + translated(locale, "recordings.match.show") + '</button></form>'
    body += '<h2>' + translated(locale, "recordings.match.game", position=position) + '</h2>'
    body += '<p><a href="/matches/position/' + str(position) + '#match-recording">' + translated(
        locale, "recordings.continue") + '</a></p>'
    if state["selected_report"] is not None:
        body += section(locale, "recordings.match.result", _reports(state, managed_handle, locale, secondary=False))
    game = state["game"]
    if game is not None:
        body += accepted_declaration_summary(locale, game["declaration"],
                                             _named_seat(state, locale, game["declarer_player_id"]))
        body += render_recorded_summary(state["recorded_progress"], locale)
    body += section(locale, "task.match.action.analyze_decision",
                    render_match_analysis_v1(state, view, managed_handle, locale))
    if state["selected_report"] is None:
        body += section(locale, "recordings.match.result", _reports(state, managed_handle, locale, secondary=False))
    body += disclosure(locale, "task.match.action.prepare_materialization",
        paragraph(locale, "recordings.match.materialization")
        + _reports(state, managed_handle, locale, secondary=True, results=False))
    body += transfer
    body += disclosure(locale, "recordings.reload.matches", paragraph(locale, "recordings.reload_help")
        + '<form method="post" action="/matches/api/v1/reload">'
        + hidden("managed_handle", managed_handle) + hidden("match_position", position)
        + '<button type="submit">' + translated(locale, "common.action.reload") + '</button></form>')
    body += '<p><a href="/review/recorded">' + translated(locale, "recordings.choose_another") + '</a></p>'
    return body + '</div>'
