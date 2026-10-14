"""Compact native controls for one explicitly selected reconstructed Match decision."""

from .rollout_form_rendering import rollout_basic_fields, rollout_technical_fields
from .stateful_localization import translated
from .task_first_match_rendering import _named_seat
from .task_first_rendering import hidden, paragraph, select_field


def render_match_rollout_form(state, handle, locale):
    view = state.get("rollout_form")
    if view is None:
        return ""
    position = state["selected_position"]
    content = '<div class="recorded-decisions match-rollout">'
    content += '<form method="get" action="/matches/review/' + str(position) + '">'
    content += select_field(locale, "decision_index", "task.field.decision_index", (
        (row["decision_index"], translated(locale, "recordings.match.decision",
            trick=(row["decision_index"] - 1) // 3 + 1,
            player=_named_seat(state, locale, row["acting_player_id"]), card=row["actual_card"]))
        for row in state["decision_preparation"]["decisions"] if row["state"] == "prepared"),
        view["decision"])
    content += ('<button type="submit">' + translated(locale, "match_rollout.select")
                + '</button></form>')
    content += paragraph(locale, "match_rollout.source")
    content += '<p id="match-rollout-objective-help">' + translated(
        locale, "rollout.objective_help") + '</p>'
    if view["missing"]:
        content += '<p id="match-rollout-settlement-help">' + translated(
            locale, "rollout.supplement_help") + '</p>'
    if "matadors" in view["missing"]:
        content += '<p id="match-rollout-matadors-help">' + translated(
            locale, "declaration.count_examples") + '</p>'
    content += ('<form class="recorded-rollout-form" method="post" '
                'action="/matches/review-whole-game">')
    for name, value in (("managed_handle", handle),
                        ("expected_revision", state["workspace_revision"]),
                        ("match_position", position), ("decision_index", view["decision"]),
                        ("decision_selection", view["selection"])):
        content += hidden(name, value)
    content += '<div class="recorded-basic">' + rollout_basic_fields(locale,
        view["settings"], view["missing"], view["supplied"], help_prefix="match-rollout") + '</div>'
    content += '<div class="recorded-actions"><button type="submit" class="primary">' + translated(
        locale, "rollout.action") + '</button></div>'
    content += rollout_technical_fields(locale, view["settings"])
    return content + '</form></div>'
