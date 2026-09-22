# ruff: noqa: E501
from __future__ import annotations

from html import escape

from .card_form import CANONICAL_CARD_CONTROLS_V1
from .guided_contracts import (
    ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESET_ACTION_ROUTE_PATH,
    ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
    ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
    REVIEW_BACK_ACTION_ROUTE_PATH,
    REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESET_ACTION_ROUTE_PATH,
    REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
    REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_START_ACTION_ROUTE_PATH,
    REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
)
from .historical_form import (
    HISTORICAL_PLAYER_IDS,
    HistoricalFormDraftV1,
    build_historical_options_summary_v1,
    build_historical_play_view_v1,
)
from .json_transfer import summarize_frontend_request_v1
from .position_form import (
    DEFAULT_POSITION_RANDOM_SEED_V1,
    DEFAULT_POSITION_SAMPLE_COUNT_V1,
    DEFAULT_POSITION_SEARCH_SEED_V1,
    POSITION_ANALYSIS_METHODS_V1,
    POSITION_COMPLETED_TRICK_ROW_COUNT_V1,
    POSITION_MULTI_STEP_POLICIES_V1,
    POSITION_OPPONENT_POLICIES_V1,
    POSITION_POLICY_PRESETS_V1,
    PositionFormDraftV1,
)
from .render_locale import html_message as _t
from .render_locale import localized_card_name, localized_render
from .render_locale import message as _m
from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .workflow_state import ProcessLocalFrontendWorkflowStateV1


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _selected(value: object, current: object) -> str:
    return " selected" if value == current else ""


def _checked(value: bool) -> str:
    return " checked" if value else ""


def _options(values: tuple[tuple[str, str], ...], current: object) -> str:
    return "".join(
        f'<option value="{_e(value)}"{_selected(value, current)}>{_e(label)}</option>'
        for value, label in values
    )


def _messages(state: ProcessLocalFrontendWorkflowStateV1) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for retained in state.validation_messages:
        field, separator, message = retained.partition("::")
        if not separator:
            field, message = "_form", retained
        grouped.setdefault(field, []).append(message)
    return {field: tuple(values) for field, values in grouped.items()}


def _field_errors(messages: dict[str, tuple[str, ...]], field: str) -> str:
    return "".join(
        f'<p class="field-error" id="error-{_e(field)}-{index}">{_e(message)}</p>'
        for index, message in enumerate(messages.get(field, ()), start=1)
    )


def _field_attributes(messages: dict[str, tuple[str, ...]], field: str) -> str:
    attributes = f'id="field-{_e(field)}"'
    errors = messages.get(field, ())
    if errors:
        described_by = " ".join(
            f"error-{field}-{index}" for index in range(1, len(errors) + 1)
        )
        attributes += f' aria-invalid="true" aria-describedby="{_e(described_by)}"'
    return attributes


def _field_group(
    messages: dict[str, tuple[str, ...]],
    field: str,
    content: str,
) -> str:
    return (
        f'<div class="form-field" role="group" {_field_attributes(messages, field)}>'
        f"{content}{_field_errors(messages, field)}</div>"
    )


def _error_summary(messages: dict[str, tuple[str, ...]]) -> str:
    if not messages:
        return ""
    items = []
    for field, values in messages.items():
        href = "#workflow-form" if field == "_form" else f"#field-{field}"
        for message in values:
            items.append(f'<li><a href="{_e(href)}">{_e(message)}</a></li>')
    return (
        '<section class="error-summary" aria-labelledby="error-summary-heading" tabindex="-1">'
        f'<h2 id="error-summary-heading">{_t("validation.summary.heading")}</h2><ul>'
        + "".join(items)
        + "</ul></section>"
    )


def _revision(state: ProcessLocalFrontendWorkflowStateV1) -> str:
    return f'<input type="hidden" name="revision" value="{state.revision}">'


def _card_palette(
    name: str,
    selected_cards: tuple[str, ...],
    *,
    legend: str,
    allowed_cards: tuple[str, ...] | None = None,
    messages: dict[str, tuple[str, ...]] | None = None,
) -> str:
    messages = messages or {}
    selected = set(selected_cards)
    allowed = set(allowed_cards) if allowed_cards is not None else None
    controls = []
    for card in CANONICAL_CARD_CONTROLS_V1:
        if allowed is not None and card.code not in allowed:
            continue
        controls.append(
            '<label class="card-choice">'
            f'<input type="checkbox" name="{_e(name)}" value="{_e(card.code)}"'
            f'{_checked(card.code in selected)}>'
            f'<span>{_e(localized_card_name(card.code))} <code>{_e(card.code)}</code></span></label>'
        )
    return (
        f'<fieldset class="card-palette" {_field_attributes(messages, name)}>'
        f'<legend>{_e(legend)}</legend><p>{_t("guided.cards_selected", count=len(selected))}</p>'
        '<div class="card-grid">'
        + "".join(controls)
        + f"</div>{_field_errors(messages, name)}</fieldset>"
    )


def _card_select(
    name: str,
    current: str | None,
    *,
    label: str,
    include_empty: bool = True,
    allowed_cards: tuple[str, ...] | None = None,
    field_id: str | None = None,
) -> str:
    allowed = set(allowed_cards) if allowed_cards is not None else None
    values = [f'<option value="">{_t("guided.no_card")}</option>'] if include_empty else []
    values.extend(
        f'<option value="{_e(card.code)}"{_selected(card.code, current)}>'
        f'{_e(localized_card_name(card.code))} ({_e(card.code)})</option>'
        for card in CANONICAL_CARD_CONTROLS_V1
        if allowed is None or card.code in allowed
    )
    identifier = field_id or f"field-{name}"
    return (
        f'<label for="{_e(identifier)}">{_e(label)}</label>'
        f'<select id="{_e(identifier)}" name="{_e(name)}">'
        f'{"".join(values)}</select>'
    )


def _process_local_notice() -> str:
    return (
        f'<aside class="local-notice">{_t("guided.process_local")}</aside>'
    )


def _import_form(
    *,
    action: str,
    revision: int,
    heading: str | None = None,
) -> str:
    return (
        '<details class="secondary-action"><summary>'
        + _e(heading or _m("guided.import"))
        + f'</summary><p>{_t("guided.import_help")}</p>'
        f'<form method="post" action="{_e(action)}" enctype="multipart/form-data">'
        f'<input type="hidden" name="revision" value="{revision}">'
        f'<label for="request-file">{_t("creation.import.file")}</label>'
        '<input id="request-file" name="request_file" type="file" accept="application/json,.json" required>'
        f'<button type="submit">{_t("guided.import")}</button></form></details>'
    )


def _imported_request(
    state: ProcessLocalFrontendWorkflowStateV1,
    *,
    run_action: str,
    page: str,
) -> str:
    if state.imported_request is None:
        return ""
    summary = summarize_frontend_request_v1(state.imported_request)
    rows = [
        (_m("guided.workflow"), summary.workflow.value),
        (_m("guided.mode"), summary.analysis_mode or _m("guided.not_applicable")),
        (_m("task.field.game_end_reason"), summary.game_end_reason or _m("guided.not_applicable")),
    ]
    executed = state.latest_successful_request == state.imported_request
    if state.execution_source_revision is not None:
        status = _m("guided.running")
        run_label = _m("guided.run_imported")
    elif executed:
        status = _m("guided.imported_executed")
        run_label = _m("guided.run_imported_again")
    else:
        status = _m("guided.imported_not_executed")
        run_label = _m("guided.run_imported")
    run_control = (
        f'<p class="execution-status" role="status">{_t("guided.running")}</p>'
        if state.execution_source_revision is not None
        else f'<button type="submit">{run_label}</button>'
    )
    request_download = (
        ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH
        if page == "analyze"
        else REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH
    )
    # The endpoint exports the successful Request when retained, otherwise the
    # accepted import. A rejected candidate/current form is never a download owner.
    import_owns_download = state.request_json_bytes is not None and (
        state.latest_successful_request is None or executed)
    result_shows_download = (state.latest_successful_result is not None
                             and state.execution_source_revision is None)
    download = (f'<p><a href="{request_download}" download>{_t("guided.request_download")}</a></p>'
                if import_owns_download and not result_shows_download else "")
    return (
        '<section class="import-summary" aria-labelledby="import-summary-heading">'
        f'<h2 id="import-summary-heading">{_t("guided.imported_document")}</h2>'
        f'<p>{_t("guided.imported_retained")} {_e(status)}</p>'
        f'<details><summary>{_t("result.import_details")}</summary><dl class="result-details" lang="en">'
        + "".join(f"<dt>{_e(label)}</dt><dd>{_e(value)}</dd>" for label, value in rows)
        + "</dl></details>"
        + download +
        f'<form method="post" action="{_e(run_action)}">{_revision(state)}'
        f"{run_control}</form></section>"
    )


def _result(state: ProcessLocalFrontendWorkflowStateV1, *, page: str) -> str:
    if state.execution_source_revision is not None:
        return f'<p class="execution-status" role="status">{_t("guided.running")}</p>'
    if state.latest_successful_result is None:
        return ""
    presentation = build_result_presentation_v1(state.latest_successful_result)
    return render_result_presentation_v1(
        presentation,
        request_download_available=state.request_json_bytes is not None,
        result_download_available=state.result_json_bytes is not None,
        page=page,
    )


def _completed_trick_controls(
    draft: PositionFormDraftV1 | None,
    messages: dict[str, tuple[str, ...]],
) -> str:
    rows = []
    completed = draft.completed_tricks if draft else ()
    leader_options = (
        ("", _m("guided.no_trick")),
        ("me", _m("guided.leader.me")),
        ("left", _m("guided.leader.left")),
        ("right", _m("guided.leader.right")),
    )
    for trick_number in range(1, POSITION_COMPLETED_TRICK_ROW_COUNT_V1 + 1):
        trick = completed[trick_number - 1] if trick_number <= len(completed) else None
        leader = trick.leader if trick else ""
        cards = trick.cards if trick else ()
        rows.append(
            f'<fieldset class="completed-trick-row"><legend>{_t("guided.trick_number", number=trick_number)}</legend>'
            f'<label>{_t("guided.leader")}<select name="completed_trick_{trick_number}_leader">'
            f'{_options(leader_options, leader)}</select></label>'
            + "".join(
                _card_select(
                    f"completed_trick_{trick_number}_card_{card_number}",
                    cards[card_number - 1] if len(cards) >= card_number else None,
                    label=_m("guided.card_number", number=card_number),
                    field_id=f"completed-trick-{trick_number}-card-{card_number}",
                )
                for card_number in range(1, 4)
            )
            + "</fieldset>"
        )
    return (
        f'<div class="completed-tricks" role="group" '
        f'{_field_attributes(messages, "completed_tricks")}>'
        f'<p>{_t("guided.tricks_help")}</p>'
        + "".join(rows)
        + _field_errors(messages, "completed_tricks")
        + "</div>"
    )


def _advanced_position(
    draft: PositionFormDraftV1 | None,
    messages: dict[str, tuple[str, ...]],
) -> str:
    method = draft.analysis_method if draft else "immediate"
    sample_count = draft.sample_count if draft else DEFAULT_POSITION_SAMPLE_COUNT_V1
    random_seed = draft.random_seed if draft else DEFAULT_POSITION_RANDOM_SEED_V1
    search_seed = draft.search_seed if draft else DEFAULT_POSITION_SEARCH_SEED_V1
    opponent_strategy = draft.opponent_strategy if draft else None
    preset = draft.opponent_policy_preset if draft else None

    method_options = tuple(
        (item.form_value, _m(f"task.value.{item.form_value}")) for item in POSITION_ANALYSIS_METHODS_V1
    )
    policy_options = (("", _m("task.value.automatic")),) + tuple(
        (value, _m(f"task.value.{value}")) for value in POSITION_OPPONENT_POLICIES_V1
    )
    preset_options = (("", _m("task.value.automatic")),) + tuple(
        (value, _m(f"task.value.{value}")) for value in POSITION_POLICY_PRESETS_V1
    )
    multi_options = (("", _m("task.value.automatic")),) + tuple(
        (value, _m(f"task.value.{value}")) for value in POSITION_MULTI_STEP_POLICIES_V1
    )

    def policy_select(field: str, label: str) -> str:
        current = getattr(draft, field) if draft else None
        return _field_group(
            messages,
            field,
            f'<label>{_e(label)}<select name="{field}">'
            f'{_options(policy_options, current or "")}</select></label>',
        )

    return f'''
      <section class="advanced-settings" aria-labelledby="advanced-heading">
        <h2 id="advanced-heading">{_t("task.advanced")}</h2>
        <p>{_t("task.analysis_help")}</p>
        <details><summary>{_t("task.field.recommendation_method")}</summary>
          {_field_group(messages, "analysis_method", f'<label>{_t("task.field.recommendation_method")}<select name="analysis_method">{_options(method_options, method)}</select></label>')}
          <p>{_t("guided.advanced.method_help")}</p>
        </details>
        <details><summary>{_t("guided.advanced.runtime")}</summary>
          {_field_group(messages, "sample_count", f'<label>{_t("task.field.immediate_sample_count")}<input name="sample_count" type="number" min="1" max="100000" value="{sample_count}"></label>')}
          {_field_group(messages, "random_seed", f'<label>{_t("task.field.immediate_random_seed")}<input name="random_seed" type="number" value="{random_seed}"></label>')}
          {_field_group(messages, "search_seed", f'<label>{_t("task.field.search_seed")}<input name="search_seed" type="number" value="{search_seed}"></label>')}
          <p>{_t("guided.advanced.runtime_help")}</p>
        </details>
        <details><summary>{_t("task.field.opponent_strategy")}</summary>
          {_field_group(messages, "opponent_strategy", f'<label>{_t("task.field.opponent_strategy")}<select name="opponent_strategy">{_options(tuple((value, _m(f"task.value.{value or 'basic'}")) for value in ("", "basic", "random")), opponent_strategy or "")}</select></label>')}
          {_field_group(messages, "opponent_policy_preset", f'<label>{_t("guided.advanced.preset")}<select name="opponent_policy_preset">{_options(preset_options, preset or "")}</select></label>')}
          {policy_select("opponent_lead_policy", _m("guided.advanced.lead"))}
          {policy_select("opponent_response_policy", _m("guided.advanced.response"))}
          {policy_select("left_opponent_lead_policy", _m("guided.advanced.left_lead"))}
          {policy_select("left_opponent_response_policy", _m("guided.advanced.left_response"))}
          {policy_select("right_opponent_lead_policy", _m("guided.advanced.right_lead"))}
          {policy_select("right_opponent_response_policy", _m("guided.advanced.right_response"))}
          {_field_group(messages, "use_profile_presets", f'<label><input type="checkbox" name="use_profile_presets"{_checked(draft.use_profile_presets if draft else False)}> {_t("task.field.use_profile_presets")}</label>')}
          <p>{_t("guided.advanced.policy_help")}</p>
        </details>
        <details><summary>{_t("guided.advanced.simulation")}</summary>
          {_field_group(messages, "multi_step_count", f'<label>{_t("guided.advanced.steps")}<input name="multi_step_count" type="number" min="1" value="{_e(draft.multi_step_count or "" if draft else "")}"></label>')}
          {_field_group(messages, "card_selection_policy", f'<label>{_t("guided.advanced.local_policy")}<select name="card_selection_policy">{_options(multi_options, draft.card_selection_policy or "" if draft else "")}</select></label>')}
          {_field_group(messages, "expected_value_sample_count", f'<label>{_t("guided.advanced.expected_samples")}<input name="expected_value_sample_count" type="number" min="1" max="100000" value="{draft.expected_value_sample_count if draft else 100}"></label>')}
          {_field_group(messages, "strict_context", f'<label><input type="checkbox" name="strict_context"{_checked(draft.strict_context if draft else False)}> {_t("guided.advanced.strict")}</label>')}
          {_field_group(messages, "compare_policies", f'<label><input type="checkbox" name="compare_policies"{_checked(draft.compare_policies if draft else False)}> {_t("guided.advanced.compare")}</label>')}
          {_field_group(messages, "comparison_only", f'<label><input type="checkbox" name="comparison_only"{_checked(draft.comparison_only if draft else False)}> {_t("guided.advanced.comparison_only")}</label>')}
          <p>{_t("guided.advanced.simulation_help")}</p>
        </details>
        <details><summary>{_t("guided.advanced.evidence")}</summary>
          {_field_group(messages, "include_provenance", f'<label><input type="checkbox" name="include_provenance"{_checked(draft.include_provenance if draft else False)}> {_t("guided.advanced.provenance")}</label>')}
          <p>{_t("guided.advanced.provenance_help")}</p>
        </details>
        <details><summary>{_t("guided.advanced.dataset")}</summary>
          <p>{_t("guided.advanced.dataset_help")}</p>
        </details>
      </section>'''


@localized_render
def render_analyze_workflow_v1(state: ProcessLocalFrontendWorkflowStateV1) -> str:
    if type(state) is not ProcessLocalFrontendWorkflowStateV1:
        raise ValueError("state must be exact process-local workflow state.")
    messages = _messages(state)
    draft = state.draft if type(state.draft) is PositionFormDraftV1 else None
    mode = draft.analysis_mode if draft else "live_decision"
    game_type = draft.game_type if draft else "grand"
    role = draft.player_role if draft else "declarer"
    seat = draft.player_position if draft else "forehand"
    declarer = draft.declarer_player if draft else "me"
    leader = draft.trick_leader if draft else "me"
    current = draft.current_trick if draft else ()
    run_control = (
        f'<p class="execution-status" role="status">{_t("guided.running")}</p>'
        if state.execution_source_revision is not None
        else f'<button type="submit">{_t("guided.run")}</button>'
    )
    content = [
        _process_local_notice(),
        _error_summary(messages),
        _result(state, page="analyze"),
        '<form id="workflow-form" class="workflow-form" method="post" action="'
        + ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH
        + '">',
        _revision(state),
        f'<fieldset {_field_attributes(messages, "analysis_mode")}><legend>{_t("guided.choice")}</legend>',
        f'<label><input type="radio" name="analysis_mode" value="live_decision"{_checked(mode == "live_decision")}> {_t("guided.current_decision")}</label>',
        f'<label><input type="radio" name="analysis_mode" value="post_game_review"{_checked(mode == "post_game_review")}> {_t("guided.actual_decision")}</label>{_field_errors(messages, "analysis_mode")}</fieldset>',
        f'<section aria-labelledby="contract-heading"><h2 id="contract-heading">{_t("guided.contract")}</h2>',
        _field_group(messages, "game_type", f'<label>{_t("task.field.game_type")}<select name="game_type">{_options(tuple((value, _m(f"task.value.{value}")) for value in ("clubs", "spades", "hearts", "diamonds", "grand", "null")), game_type)}</select></label>'),
        _field_group(messages, "player_role", f'<label>{_t("guided.role")}<select name="player_role">{_options(tuple((value, _m(f"task.value.{value}")) for value in ("declarer", "defender")), role)}</select></label>'),
        _field_group(messages, "player_position", f'<label>{_t("guided.seat")}<select name="player_position">{_options(tuple((value, _m(f"creation.seat.{value}")) for value in ("forehand", "middlehand", "rearhand")), seat)}</select></label>'),
        _field_group(messages, "declarer_player", f'<label>{_t("guided.declarer_relative")}<select name="declarer_player">{_options(tuple((value, _m(f"task.value.{value}")) for value in ("me", "left", "right")), declarer)}</select></label>'),
        _field_group(messages, "hand_game", f'<label><input type="checkbox" name="hand_game"{_checked(draft.hand_game if draft else False)}> {_t("task.field.hand_game")}</label>'),
        _field_group(messages, "schneider_announced", f'<label><input type="checkbox" name="schneider_announced"{_checked(draft.schneider_announced if draft else False)}> {_t("task.field.schneider_announced")}</label>'),
        _field_group(messages, "schwarz_announced", f'<label><input type="checkbox" name="schwarz_announced"{_checked(draft.schwarz_announced if draft else False)}> {_t("task.field.schwarz_announced")}</label>'),
        _field_group(messages, "ouvert", f'<label><input type="checkbox" name="ouvert"{_checked(draft.ouvert if draft else False)}> {_t("task.field.ouvert")}</label>'),
        _field_group(messages, "bid_value", f'<label>{_t("task.field.bid_value")}<input name="bid_value" type="number" min="1" value="{_e(draft.bid_value or "" if draft else "")}"></label>'),
        _field_group(messages, "matadors", f'<label>{_t("task.field.matadors")}<input name="matadors" type="number" min="1" max="11" value="{_e(draft.matadors or "" if draft else "")}"></label>'),
        f'<p>{_t("guided.matadors_help")}</p></section>',
        f'<section aria-labelledby="visible-heading"><h2 id="visible-heading">{_t("guided.visible")}</h2>',
        _card_palette("hand", draft.hand if draft else (), legend=_m("guided.hand"), messages=messages),
        _card_palette("skat", draft.skat if draft else (), legend=_m("guided.skat"), messages=messages),
        _card_palette("public_declarer_cards", draft.public_declarer_cards if draft else (), legend=_m("guided.public_hand"), messages=messages),
        f'<p>{_t("guided.hidden_help")}</p></section>',
        f'<section aria-labelledby="tricks-heading"><h2 id="tricks-heading">{_t("guided.tricks")}</h2>',
        _completed_trick_controls(draft, messages),
        _field_group(messages, "current_trick", _card_select("current_trick", current[0] if current else None, label=_m("guided.current_first"), field_id="current-trick-first") + _card_select("current_trick", current[1] if len(current) > 1 else None, label=_m("guided.current_second"), field_id="current-trick-second")),
        _field_group(messages, "trick_leader", f'<label>{_t("guided.current_leader")}<select name="trick_leader">{_options(tuple((value, _m(f"task.value.{value}")) for value in ("me", "left", "right")), leader)}</select></label>'),
        f'<p>{_t("guided.rules_help")}</p></section>',
        f'<section aria-labelledby="score-heading"><h2 id="score-heading">{_t("guided.score")}</h2>',
        _field_group(messages, "declarer_points", f'<label>{_t("guided.declarer_points")}<input name="declarer_points" type="number" min="0" max="120" value="{draft.declarer_points if draft else 0}"></label>'),
        _field_group(messages, "defender_points", f'<label>{_t("guided.defender_points")}<input name="defender_points" type="number" min="0" max="120" value="{draft.defender_points if draft else 0}"></label>'),
        _field_group(messages, "actual_card_played", _card_select("actual_card_played", draft.actual_card_played if draft else None, label=_m("guided.actual_card"), field_id="actual-card-played")),
        f'<p>{_t("guided.sizes_help")}</p></section>',
        _advanced_position(draft, messages),
        f'<section aria-labelledby="run-heading"><h2 id="run-heading">{_t("guided.run")}</h2>',
        f'<p>{_t("guided.run_help")}</p>{run_control}</section></form>',
        _import_form(action=ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH, revision=state.revision),
        _imported_request(
            state,
            run_action=ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
            page="analyze",
        ),
        f'<form class="reset-form" method="post" action="{ANALYZE_RESET_ACTION_ROUTE_PATH}">{_revision(state)}<label><input type="checkbox" name="confirm_reset" required> {_t("guided.reset_confirm")}</label><button type="submit">{_t("common.action.reset")}</button></form>',
    ]
    return "".join(content)


def _review_back_and_reset(state: ProcessLocalFrontendWorkflowStateV1, draft: HistoricalFormDraftV1) -> str:
    back = ""
    if draft.step > 1:
        back = (
            f'<form method="post" action="{REVIEW_BACK_ACTION_ROUTE_PATH}">{_revision(state)}'
            f'<button type="submit">{_t("guided.review.back")}</button></form>'
        )
    reset = (
        f'<form class="reset-form" method="post" action="{REVIEW_RESET_ACTION_ROUTE_PATH}">{_revision(state)}'
        f'<label><input type="checkbox" name="confirm_reset" required> {_t("guided.reset_confirm")}</label>'
        f'<button type="submit">{_t("common.action.reset")}</button></form>'
    )
    return f'<div class="wizard-actions">{back}{reset}</div>'


def _review_step(
    state: ProcessLocalFrontendWorkflowStateV1,
    draft: HistoricalFormDraftV1,
    messages: dict[str, tuple[str, ...]],
) -> str:
    progress = (
        f'<p class="wizard-progress" role="status">{_t("guided.review.progress", step=draft.step)}: '
        f'{_t(f"guided.review.step.{draft.step}")}</p>'
    )
    if draft.step == 1:
        body = f'''<form id="workflow-form" method="post" action="{REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH}">{_revision(state)}
          <h2>{_t("guided.review.step.1")}</h2><p>{_t("guided.review.players_help")}</p>
          {_field_group(messages, "forehand_label", f'<label>{_t("creation.seat.forehand")}<input name="forehand_label" value="{_e(draft.players[0].player_label or "")}"></label>')}
          {_field_group(messages, "middlehand_label", f'<label>{_t("creation.seat.middlehand")}<input name="middlehand_label" value="{_e(draft.players[1].player_label or "")}"></label>')}
          {_field_group(messages, "rearhand_label", f'<label>{_t("creation.seat.rearhand")}<input name="rearhand_label" value="{_e(draft.players[2].player_label or "")}"></label>')}
          <button type="submit">{_t("common.action.continue")}</button></form>'''
    elif draft.step == 2:
        body = (
            f'<form id="workflow-form" method="post" action="{REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH}">{_revision(state)}'
            f'<h2>{_t("guided.review.step.2")}</h2><p>{_t("guided.review.deal_help")}</p>'
            + _card_palette("forehand_hand", draft.players[0].initial_hand, legend=_m("creation.seat.forehand"), messages=messages)
            + _card_palette("middlehand_hand", draft.players[1].initial_hand, legend=_m("creation.seat.middlehand"), messages=messages)
            + _card_palette("rearhand_hand", draft.players[2].initial_hand, legend=_m("creation.seat.rearhand"), messages=messages)
            + _card_palette("skat", draft.skat, legend=_m("task.skat"), messages=messages)
            + f'<button type="submit">{_t("guided.review.validate_deal")}</button></form>'
        )
    elif draft.step == 3:
        declaration = draft.declaration
        body = f'''<form id="workflow-form" method="post" action="{REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH}">{_revision(state)}
          <h2>{_t("guided.review.step.3")}</h2>
          {_field_group(messages, "declarer_player_id", f'<label>{_t("task.field.declarer_player_id")}<select name="declarer_player_id">{_options(tuple((player.player_id, player.player_label or _m(f"creation.seat.{player.seat}")) for player in draft.players), declaration.declarer_player_id if declaration else HISTORICAL_PLAYER_IDS[0])}</select></label>')}
          {_field_group(messages, "game_type", f'<label>{_t("task.field.game_type")}<select name="game_type">{_options(tuple((value, _m(f"task.value.{value}")) for value in ("clubs", "spades", "hearts", "diamonds", "grand", "null")), declaration.game_type if declaration else "grand")}</select></label>')}
          {_field_group(messages, "bid_value", f'<label>{_t("task.field.bid_value")}<input name="bid_value" type="number" min="1" value="{declaration.bid_value if declaration else 18}"></label>')}
          {_field_group(messages, "hand_game", f'<label><input type="checkbox" name="hand_game"{_checked(declaration.hand_game if declaration else False)}> {_t("task.field.hand_game")}</label>')}
          {_field_group(messages, "schneider_announced", f'<label><input type="checkbox" name="schneider_announced"{_checked(declaration.schneider_announced if declaration else False)}> {_t("task.field.schneider_announced")}</label>')}
          {_field_group(messages, "schwarz_announced", f'<label><input type="checkbox" name="schwarz_announced"{_checked(declaration.schwarz_announced if declaration else False)}> {_t("task.field.schwarz_announced")}</label>')}
          {_field_group(messages, "ouvert", f'<label><input type="checkbox" name="ouvert"{_checked(declaration.ouvert if declaration else False)}> {_t("task.field.ouvert")}</label>')}
          <p>{_t("guided.review.declaration_help")}</p>
          <button type="submit">{_t("common.action.continue")}</button></form>'''
    elif draft.step == 4:
        hand_game = bool(draft.declaration and draft.declaration.hand_game)
        declarer = (
            next(
                player
                for player in draft.players
                if player.player_id == draft.declaration.declarer_player_id
            )
            if draft.declaration is not None
            else None
        )
        discard_controls = (
            ""
            if hand_game or declarer is None
            else _card_palette(
                "discarded_cards",
                draft.discarded_cards,
                legend=_m("task.discards"),
                allowed_cards=(*declarer.initial_hand, *draft.skat),
                messages=messages,
            )
        )
        body = (
            f'<form id="workflow-form" method="post" action="{REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH}">{_revision(state)}'
            f'<h2>{_t("guided.review.step.4")}</h2>'
            f'<p>{_t("guided.review.hand_discards" if hand_game else "guided.review.two_discards")}</p>'
            + discard_controls
            + f'<button type="submit">{_t("guided.review.validate_discards")}</button></form>'
        )
    elif draft.step == 5:
        view = build_historical_play_view_v1(draft)
        actor = next((player.player_label or _m(f"creation.seat.{player.seat}") for player in draft.players if player.player_id == view.acting_player_id), _m("guided.review.complete"))
        current_cards = ", ".join(play.card for play in view.current_trick_plays) or _m("guided.no_card")
        play_control = (
            f'<form method="post" action="{REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH}">{_revision(state)}'
            f'<button type="submit">{_t("common.action.continue")}</button></form>'
            if view.is_complete
            else f'''<form method="post" action="{REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH}">{_revision(state)}
             {_field_group(messages, "card", _card_select("card", None, label=_m("task.card.choose"), include_empty=False, allowed_cards=view.legal_cards, field_id="legal-card"))}
            <button type="submit">{_t("task.command.record_play")}</button></form>'''
        )
        body = f'''<section id="workflow-form"><h2>{_t("guided.review.step.5")}</h2>
          <p>{_t("guided.review.play_progress", count=view.played_card_count, tricks=len(view.completed_tricks), cards=current_cards)}</p>
          <p>{_t("task.session.play_for", player=actor)}</p>
          {play_control}
          {f'<form method="post" action="{REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH}">{_revision(state)}<button type="submit">{_t("guided.review.undo")}</button></form>' if draft.plays else ""}
          <p>{_t("guided.rules_help")}</p></section>'''
    elif draft.step == 6:
        options = draft.options
        body = f'''<form id="workflow-form" method="post" action="{REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH}">{_revision(state)}
          <h2>{_t("guided.review.step.6")}</h2><p>{_t("guided.review.options_help")}</p>
          <section class="advanced-settings" aria-labelledby="advanced-heading"><h3 id="advanced-heading">{_t("task.advanced")}</h3>
          <details><summary>{_t("task.field.recommendation_method")}</summary>
            {_field_group(messages, "decision_snapshots", f'<label><input type="checkbox" name="decision_snapshots"{_checked(options.decision_snapshots)}> {_t("task.field.decision_snapshots")}</label>')}
            {_field_group(messages, "immediate_review", f'<label><input type="checkbox" name="immediate_review"{_checked(options.immediate_review)}> {_t("task.field.immediate_review")}</label>')}
            {_field_group(messages, "search_review", f'<label><input type="checkbox" name="search_review"{_checked(options.search_review)}> {_t("task.field.search_review")}</label>')}
            {_field_group(messages, "information_set_search_review", f'<label><input type="checkbox" name="information_set_search_review"{_checked(options.information_set_search_review)}> {_t("task.field.information_set_search_review")}</label>')}
            <p>{_t("guided.review.method_help")}</p>
          </details>
          <details><summary>{_t("guided.advanced.runtime")}</summary>
            {_field_group(messages, "search_seed", f'<label>{_t("task.field.search_seed")}<input name="search_seed" type="number" value="{options.search_seed}"></label>')}
            {_field_group(messages, "immediate_sample_count", f'<label>{_t("task.field.immediate_sample_count")}<input name="immediate_sample_count" type="number" min="1" value="{options.immediate_sample_count}"></label>')}
            {_field_group(messages, "immediate_base_random_seed", f'<label>{_t("task.field.immediate_random_seed")}<input name="immediate_base_random_seed" type="number" value="{options.immediate_base_random_seed}"></label>')}
            <p>{_t("guided.review.runtime_help")}</p>
          </details>
          <details><summary>{_t("task.field.opponent_strategy")}</summary><p>{_t("guided.review.policy_help")}</p></details>
          <details><summary>{_t("guided.advanced.simulation")}</summary>
            {_field_group(messages, "replay_coaching", f'<label><input type="checkbox" name="replay_coaching"{_checked(options.replay_coaching)}> {_t("task.field.replay_coaching")}</label>')}
            {_field_group(messages, "information_set_replay_coaching", f'<label><input type="checkbox" name="information_set_replay_coaching"{_checked(options.information_set_replay_coaching)}> {_t("task.field.information_set_replay_coaching")}</label>')}
            {_field_group(messages, "tactical", f'<label><input type="checkbox" name="tactical"{_checked(options.tactical)}> {_t("task.field.tactical_motif_review")}</label>')}
            <p>{_t("guided.review.coaching_help")}</p>
          </details>
          <details><summary>{_t("guided.advanced.evidence")}</summary>
            {_field_group(messages, "include_provenance", f'<label><input type="checkbox" name="include_provenance"{_checked(options.include_provenance)}> {_t("guided.advanced.provenance")}</label>')}
            <p>{_t("guided.advanced.provenance_help")}</p>
          </details>
          <details><summary>{_t("guided.advanced.dataset")}</summary><p>{_t("guided.advanced.dataset_help")}</p></details>
          </section><button type="submit">{_t("guided.review.selections")}</button></form>'''
    else:
        summary = build_historical_options_summary_v1(draft)
        selected = ", ".join(_m(f"guided.review.output.{value}") for value in summary.selected_outputs) or _m("guided.review.no_optional")
        prerequisites = ", ".join(_m(f"guided.review.output.{value}") for value in summary.implied_prerequisites) or _m("task.known_empty")
        run_control = (
            f'<p class="execution-status" role="status">{_t("guided.running")}</p>'
            if state.execution_source_revision is not None
            else f'<form method="post" action="{REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH}">{_revision(state)}<button type="submit">{_t("guided.review.run")}</button></form>'
        )
        body = f'''<section id="workflow-form"><h2>{_t("guided.review.step.7")}</h2>
          <dl class="result-details"><dt>{_t("guided.review.game")}</dt><dd>{_t("guided.review.normal")}</dd>
          <dt>{_t("guided.review.included")}</dt><dd>{_e(", ".join(_m(f"guided.review.output.{value}") for value in summary.always_included))}</dd>
          <dt>{_t("task.selected")}</dt><dd>{_e(selected)}</dd><dt>{_t("guided.review.prerequisites")}</dt><dd>{_e(prerequisites)}</dd></dl>
          {run_control}</section>'''
    return '<section class="wizard">' + progress + body + _review_back_and_reset(state, draft) + "</section>"


@localized_render
def render_review_workflow_v1(state: ProcessLocalFrontendWorkflowStateV1) -> str:
    if type(state) is not ProcessLocalFrontendWorkflowStateV1:
        raise ValueError("state must be exact process-local workflow state.")
    messages = _messages(state)
    draft = state.draft if type(state.draft) is HistoricalFormDraftV1 else None
    content = [
        _process_local_notice(),
        _error_summary(messages),
        _result(state, page="review"),
        f'<section class="workflow-choice"><h2>{_t("guided.review.choose")}</h2><p>{_t("guided.review.enter")}</p><p>{_t("guided.import")}</p></section>',
    ]
    if draft is None and state.imported_request is None:
        content.append(
            f'<form id="workflow-form" method="post" action="{REVIEW_START_ACTION_ROUTE_PATH}">{_revision(state)}'
            f'<button type="submit">{_t("guided.review.start")}</button></form>'
        )
    if draft is not None:
        content.append(_review_step(state, draft, messages))
    content.extend(
        (
            f'<aside class="scope-note"><h2>{_t("guided.review.scope")}</h2><p>{_t("guided.review.scope_help")}</p></aside>',
            _import_form(action=REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH, revision=state.revision),
            _imported_request(
                state,
                run_action=REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
                page="review",
            ),
        )
    )
    return "".join(content)
