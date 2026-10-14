"""Source-owned selection and independent analysis forms with a staged native fallback."""

from .rollout_form_rendering import rollout_basic_fields, rollout_technical_fields
from .stateful_localization import text, translated
from .task_first_match_rendering import _named_seat
from .task_first_rendering import hidden, paragraph, select_field


def render_match_rollout_form(state, handle, locale, *, legacy=""):
    view = state.get("rollout_form")
    if view is None:
        return ""
    position = state["selected_position"]
    native_ready = view["native_ready"] and view["ready"]
    content = ('<div id="match-decision-controls" data-match-selection '
        + f'data-source="{state["decision_source_scope"]}" data-applied="{view["decision"]}" '
        + f'data-ready="{str(view["ready"]).lower()}" '
        + f'data-loading-label="{translated(locale, "match_selection.loading")}" '
        + f'data-failed-label="{translated(locale, "match_selection.failed")}">')
    content += ('<form method="post" action="/matches/select-decision" data-decision-selector'
                + (' hidden' if native_ready else '') + '>')
    for name, value in (("managed_handle", handle), ("match_position", position),
                        ("expected_revision", state["workspace_revision"]),
                        ("selection_context", state["decision_selection_context"]),
                        ("return_to", state["decision_selection_return"])):
        content += hidden(name, value)
    options = tuple(
        (row["decision_index"], translated(locale, "recordings.match.decision",
            trick=(row["decision_index"] - 1) // 3 + 1,
            player=_named_seat(state, locale, row["acting_player_id"]), card=row["actual_card"]))
        for row in state["decision_preparation"]["decisions"] if row["state"] == "prepared")
    if view["decision"] == "":
        options = (("", text(locale, "match_selection.unready")), *options)
    content += select_field(locale, "decision_index", "task.field.decision_index",
                            options, view["decision"])
    content += ('<button type="submit" data-apply-decision>'
                + translated(locale, "match_rollout.select")
                + '</button></form>')
    content += '<p data-native-selection' + (' hidden' if native_ready else '') + '>' + translated(
        locale, "match_selection.native_help") + '</p>'
    row = next((row for row in state["decision_preparation"]["decisions"]
                if row["decision_index"] == view["decision"]), None)
    label = "" if row is None else translated(locale, "match_selection.applied",
        decision=text(locale, "recordings.match.decision",
            trick=(row["decision_index"] - 1) // 3 + 1,
            player=_named_seat(state, locale, row["acting_player_id"]), card=row["actual_card"]))
    content += '<p data-applied-decision>' + (label if view["ready"] else translated(
        locale, "match_selection.unready")) + '</p>'
    content += '<p data-native-change' + ('' if native_ready else ' hidden') + '><a href="'
    content += f'/matches/review/{position}?choose_decision=1">' + translated(
        locale, "match_selection.change") + '</a></p>'
    content += '<p data-selection-status role="status" aria-live="polite" hidden></p>'
    content += '<div data-match-analysis-controls' + ('' if native_ready else ' hidden') + '>'
    if row is None:
        return content + '</div></div>'
    content += '<div class="recorded-decisions match-rollout">'
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
                        ("visible_decision_index", view["decision"]),
                        ("decision_selection", view["selection"])):
        content += hidden(name, value)
    content += '<div class="recorded-basic">' + rollout_basic_fields(locale,
        view["settings"], view["missing"], view["supplied"], help_prefix="match-rollout") + '</div>'
    content += '<div class="recorded-actions"><button type="submit" class="primary">' + translated(
        locale, "rollout.action") + '</button></div>'
    content += rollout_technical_fields(locale, view["settings"])
    content += '</form></div>' + legacy
    return content + '</div></div>'
