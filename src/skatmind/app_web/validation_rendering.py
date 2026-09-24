from __future__ import annotations

import re
from html import escape

from .form_parsing import FormValuesV1
from .form_registry import FrontendFormDefinitionV1, FrontendFormFieldV1
from .translation_catalog import translate_frontend_message_v1
from .validation_contracts import FrontendSubmittedFormStateV1

_FORM_OPEN = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
_DETAILS_OPEN = re.compile(r"<details\b[^>]*>", re.IGNORECASE)
_FORM_BLOCK = re.compile(r"(<form\b[^>]*>)(.*?)(</form>)", re.IGNORECASE | re.DOTALL)


def _attribute(tag: str, name: str) -> str | None:
    match = re.search(rf'\b{re.escape(name)}="([^"]*)"', tag, re.IGNORECASE)
    return None if match is None else match.group(1)


def _set_attribute(tag: str, name: str, value: str | None) -> str:
    pattern = re.compile(rf'\s+{re.escape(name)}(?:="[^"]*")?', re.IGNORECASE)
    tag = pattern.sub("", tag)
    if value is None:
        return tag
    return tag[:-1] + f' {name}="{escape(value, quote=True)}">'


def _find_form_bounds(
    html: str,
    definition: FrontendFormDefinitionV1,
    form_instance: int | None,
    form_identity: tuple[tuple[str, str], ...] = (),
) -> tuple[int, int] | None:
    matching_index = 0
    for match in _FORM_OPEN.finditer(html):
        if _attribute(match.group(0), "action") != definition.action_route:
            continue
        end = html.find("</form>", match.end())
        if end < 0:
            continue
        end += len("</form>")
        block = html[match.start() : end]
        if definition.discriminator_field is not None:
            discriminator_field = re.escape(definition.discriminator_field)
            discriminator_value = re.escape(definition.discriminator_value or "")
            discriminator = re.compile(
                rf'<input\b(?=[^>]*\bname="{discriminator_field}")'
                rf'(?=[^>]*\bvalue="{discriminator_value}")[^>]*>',
                re.IGNORECASE,
            )
            if discriminator.search(block) is None:
                continue
        if any(
            re.search(
                rf'<input\b(?=[^>]*\bname="{re.escape(field)}")'
                rf'(?=[^>]*\bvalue="{re.escape(value)}")[^>]*>',
                block,
                re.IGNORECASE,
            )
            is None
            for field, value in form_identity
        ):
            continue
        if form_instance is not None and matching_index != form_instance:
            matching_index += 1
            continue
        return match.start(), end
    return None


def instrument_registered_forms_v1(
    html: str,
    definitions: tuple[FrontendFormDefinitionV1, ...],
) -> str:
    """Adds opaque per-render ordinals only to unified URL-encoded forms."""

    counts: dict[str, int] = {}

    def instrument(match: re.Match[str]) -> str:
        opening, content, closing = match.groups()
        action = _attribute(opening, "action")
        media_type = _attribute(opening, "enctype") or "application/x-www-form-urlencoded"
        candidates = tuple(
            definition
            for definition in definitions
            if definition.action_route == action
            and definition.media_type == media_type
        )
        if not candidates:
            return match.group(0)
        definition = candidates[0]
        for candidate in candidates:
            if candidate.discriminator_field is None:
                definition = candidate
                break
            discriminator = re.compile(
                rf'<input\b(?=[^>]*\bname="{re.escape(candidate.discriminator_field)}")'
                rf'(?=[^>]*\bvalue="{re.escape(candidate.discriminator_value or "")}")[^>]*>',
                re.IGNORECASE,
            )
            if discriminator.search(content) is not None:
                definition = candidate
                break
        instance = counts.get(definition.form_key, 0)
        counts[definition.form_key] = instance + 1
        fields = " ".join(field.field_key for field in definition.safe_fields
                          if field.control_type != "file" and not field.clear_after_rejection)
        opening = _set_attribute(opening, "data-preserve-fields", fields)
        metadata = (f'<input type="hidden" name="_frontend_form_instance" value="{instance}">'
                    if media_type == "application/x-www-form-urlencoded" else "")
        return opening + metadata + content + closing

    return _FORM_BLOCK.sub(instrument, html)


def _open_containing_details(html: str, form_start: int, form_end: int) -> str:
    stack = []
    containers = []
    for match in re.finditer(r"<details\b[^>]*>|</details>", html, re.IGNORECASE):
        if match.group(0).lower().startswith("</"):
            if stack:
                opening = stack.pop()
                if opening.end() <= form_start and match.start() >= form_end:
                    containers.append(opening)
        else:
            stack.append(match)
    for opening in sorted(containers, key=lambda item: item.start(), reverse=True):
        if re.search(r"\sopen(?:\s|=|>)", opening.group(0), re.IGNORECASE) is None:
            html = html[:opening.end() - 1] + " open>" + html[opening.end():]
    return html


def _open_field_details(block: str, field: str) -> str:
    field_pattern = re.escape(field)
    control = re.search(
        rf'<(?:input|select|textarea)\b(?=[^>]*\bname="{field_pattern}")[^>]*>',
        block,
        re.IGNORECASE,
    )
    if control is None:
        return block
    return _open_containing_details(block, control.start(), control.end())


def _insert_field_messages(block: str, field: str, messages: str) -> str:
    if field in {"card", "cards"} and 'class="compact-cards"' in block:
        return block.replace('</fieldset>', '</fieldset>' + messages, 1)
    field_pattern = re.escape(field)
    control = re.search(
        rf'<input\b(?=[^>]*\bname="{field_pattern}")[^>]*>'
        rf'|<select\b(?=[^>]*\bname="{field_pattern}")[^>]*>.*?</select>'
        rf'|<textarea\b(?=[^>]*\bname="{field_pattern}")[^>]*>.*?</textarea>',
        block,
        re.IGNORECASE | re.DOTALL,
    )
    if control is None:
        return block
    label_end = block.find("</label>", control.end())
    insertion = control.end() if label_end < 0 else label_end + len("</label>")
    return block[:insertion] + messages + block[insertion:]


def _replace_values(block: str, state: FrontendSubmittedFormStateV1) -> str:
    return _replace_safe_values(block, state.safe_visible_values)


def _replace_safe_values(block: str, values_state: FormValuesV1) -> str:
    for entry in values_state.entries:
        field = re.escape(entry.field)
        values = entry.values

        input_pattern = re.compile(
            rf'<input\b(?=[^>]*\bname="{field}")[^>]*>',
            re.IGNORECASE,
        )
        input_index = 0

        def replace_input(
            match: re.Match[str],
            retained_values: tuple[str, ...] = values,
        ) -> str:
            nonlocal input_index
            tag = match.group(0)
            control_type = (_attribute(tag, "type") or "text").lower()
            if control_type in {"file", "password", "hidden", "submit", "button"}:
                return tag
            if control_type in {"checkbox", "radio"}:
                submitted = _attribute(tag, "value") or "on"
                return _set_attribute(
                    tag,
                    "checked",
                    "checked" if submitted in retained_values else None,
                )
            value = retained_values[min(input_index, len(retained_values) - 1)]
            input_index += 1
            return _set_attribute(tag, "value", value)

        block = input_pattern.sub(replace_input, block)

        textarea_pattern = re.compile(
            rf'(<textarea\b(?=[^>]*\bname="{field}")[^>]*>).*?(</textarea>)',
            re.IGNORECASE | re.DOTALL,
        )
        block = textarea_pattern.sub(
            lambda match, retained_value=values[0]: (
                match.group(1) + escape(retained_value) + match.group(2)
            ),
            block,
        )

        select_pattern = re.compile(
            rf'(<select\b(?=[^>]*\bname="{field}")[^>]*>)(.*?)(</select>)',
            re.IGNORECASE | re.DOTALL,
        )
        select_index = 0

        def replace_select(
            match: re.Match[str],
            retained_values: tuple[str, ...] = values,
            field_name: str = entry.field,
        ) -> str:
            nonlocal select_index
            options = re.sub(r"\s+selected(?:=\"selected\")?", "", match.group(2))
            multiple = re.search(r"\bmultiple(?:\s|=|>)", match.group(1)) is not None
            retained_value = retained_values[min(select_index, len(retained_values) - 1)]
            select_index += 1
            selected = escape(retained_value, quote=True)
            option_pattern = re.compile(
                rf'(<option\b(?=[^>]*\bvalue="{re.escape(selected)}")[^>]*)(>)',
                re.IGNORECASE,
            )
            options = option_pattern.sub(r"\1 selected\2", options, count=1)
            if not multiple and retained_value == "" and " selected" not in options:
                options = '<option value="" selected></option>' + options
            if multiple:
                for value in retained_values:
                    pattern = re.compile(
                        rf'(<option\b(?=[^>]*\bvalue="{re.escape(escape(value, quote=True))}")'
                        rf'[^>]*)(>)', re.IGNORECASE)
                    options = pattern.sub(lambda option: _set_attribute(
                        option.group(0), "selected", "selected"), options)
            if (field_name in {"card", "cards", "actual_card_played"}
                    and re.fullmatch(r"[CSHD](?:A|10|K|Q|J|9|8|7)", retained_value)
                    and " selected" not in options):
                options = f'<option value="{selected}" selected>{selected}</option>' + options
            return match.group(1) + options + match.group(3)

        block = select_pattern.sub(replace_select, block)
    if 'class="compact-cards"' in block and values_state.contains("cards"):
        cards = values_state.all("cards")
        available = re.findall(
            r'<input\b[^>]*name="cards"[^>]*value="([CSHD](?:A|10|K|Q|J|9|8|7))"', block)
        selected = ', '.join(card for card in available if card in cards)
        block = re.sub(r'(<span class="compact-selected">).*?(</span>)',
                       lambda match: match[1] + escape(selected) + match[2], block, flags=re.S)
        rejected = tuple(dict.fromkeys(card for card in cards if card not in available
            and re.fullmatch(r"[CSHD](?:A|10|K|Q|J|9|8|7)", card)))
        if rejected:
            locale = re.search(r'data-card-locale="(de|en)"', block)[1]
            message = escape(translate_frontend_message_v1(
                locale, "compact.rejected", cards=', '.join(rejected)))
            block = block.replace('<p class="compact-rejected"></p>',
                                  '<p class="compact-rejected">' + message + '</p>')
    return block


def _add_control_accessibility(
    block: str,
    field: str,
    described_by: str,
    control_id: str,
) -> tuple[str, str | None]:
    field_pattern = re.escape(field)
    patterns = (
        re.compile(rf'<input\b(?=[^>]*\bname="{field_pattern}")[^>]*>', re.IGNORECASE),
        re.compile(rf'<select\b(?=[^>]*\bname="{field_pattern}")[^>]*>', re.IGNORECASE),
        re.compile(rf'<textarea\b(?=[^>]*\bname="{field_pattern}")[^>]*>', re.IGNORECASE),
    )
    identifier_added = False
    first_control_id: str | None = None
    for pattern in patterns:

        def update(match: re.Match[str]) -> str:
            nonlocal first_control_id, identifier_added
            tag = _set_attribute(match.group(0), "aria-invalid", "true")
            if not identifier_added:
                first_control_id = _attribute(tag, "id") or control_id
                tag = _set_attribute(tag, "id", first_control_id)
                identifier_added = True
            existing = _attribute(tag, "aria-describedby")
            identifiers = tuple(dict.fromkeys((*(existing or "").split(), described_by)))
            return _set_attribute(tag, "aria-describedby", " ".join(identifiers))

        block = pattern.sub(update, block)
    return block, first_control_id


def _learning_report_feedback(block, state, locale):
    """A regenerated sole target is transport, never a restored accepted attachment."""
    retained = state.safe_visible_values.singular("match_snapshot_id")
    pattern = re.compile(r'(<select\b[^>]*name="match_snapshot_id"[^>]*>)(.*?)(</select>)', re.S)

    def choices(match):
        if retained is not None and not re.search(
                rf'<option\b[^>]*value="{re.escape(escape(retained, quote=True))}"', match[2]):
            options = re.sub(r'\s+selected(?:="selected")?', '', match[2])
            caption = escape(translate_frontend_message_v1(locale, "task.learning.report_choose"))
            return match[1] + f'<option value="" selected>{caption}</option>' + options + match[3]
        return match[0]

    block = pattern.sub(choices, block)
    return '<p>' + escape(translate_frontend_message_v1(
        locale, "task.learning.report_retry")) + '</p>' + block


def _render_summary(
    state: FrontendSubmittedFormStateV1,
    translated: list[tuple[str | None, str, str]],
    field_definitions: dict[str, FrontendFormFieldV1],
    rendered_fields: dict[str, str],
    *,
    locale: str,
    fallback_anchor: str,
    last_valid_result_retained: bool,
    evidence_anchor: str | None = None,
) -> str:
    session_card = state.originating_route in {"/sessions/cards", "/sessions/play"}
    heading_key = "validation.session_card.heading" if session_card else (
        "validation.summary.conflict_heading"
        if state.status == "conflict"
        else "validation.summary.heading"
    )
    guidance_key = "validation.session_card.no_save" if session_card else (
        "validation.summary.conflict_guidance"
        if state.status == "conflict"
        else "validation.summary.guidance"
    )
    items = []
    for field, _identifier, message in translated:
        href = f"#{rendered_fields.get(field or '', fallback_anchor)}"
        label = ""
        field_definition = field_definitions.get(field or "")
        if field_definition is not None:
            label = (
                translate_frontend_message_v1(locale, field_definition.field_label_key) + ": "
            )
        items.append(f'<li><a href="{escape(href, quote=True)}">{escape(label + message)}</a></li>')
    retained_result = (
        f"<p>{escape(translate_frontend_message_v1(locale, 'validation.last_valid_result'))}</p>"
        if last_valid_result_retained
        else ""
    )
    conflict_guidance_key = (
        "error.profile_conflict.message"
        if state.active_family_binding in {"local_settings", "profile"}
        and any(
            issue.message_key == "validation.message.persistence_conflict"
            for issue in state.validation_issues
        )
        else "validation.reload_guidance"
    )
    reload_guidance = (
        f"<p>{escape(translate_frontend_message_v1(locale, conflict_guidance_key))}</p>"
        if state.status == "conflict"
        else ""
    )
    locale_attribute = escape(locale, quote=True)
    summary_identity = ' id="session-card-error"' if session_card else ""
    actions = ""
    if session_card:
        if evidence_anchor is not None:
            actions += f'<a class="session-card-evidence" href="#{evidence_anchor}">' + escape(
                translate_frontend_message_v1(locale, "validation.session_card.inspect"))
            actions += '</a> · '
        target = rendered_fields.get("cards", fallback_anchor)
        actions += f'<a href="#{escape(target, quote=True)}">' + escape(
            translate_frontend_message_v1(locale, "validation.session_card.change")) + '</a>'
        actions = '<p>' + actions + '</p>'
    return (
        f'<section class="error-summary"{summary_identity} role="alert" tabindex="-1" autofocus '
        f'aria-labelledby="validation-summary-heading-{state.feedback_generation}" '
        f'lang="{locale_attribute}">'
        f'<h2 id="validation-summary-heading-{state.feedback_generation}">'
        f"{escape(translate_frontend_message_v1(locale, heading_key))}</h2>"
        f"<p>{escape(translate_frontend_message_v1(locale, guidance_key))}</p>"
        f"<ul>{''.join(items)}</ul>{actions}{reload_guidance}{retained_result}</section>"
    )


def _prepend_to_main(html: str, content: str) -> str:
    main_start = html.find('<main id="main-content"')
    if main_start < 0:
        return html
    opening_end = html.find(">", main_start)
    if opening_end < 0:
        return html
    insertion = opening_end + 1
    return html[:insertion] + content + html[insertion:]


def apply_validation_feedback_to_html_v1(
    html: str,
    definition: FrontendFormDefinitionV1,
    state: FrontendSubmittedFormStateV1,
    *,
    locale: str,
    last_valid_result_retained: bool = False,
    session_card_details: tuple[str, str | None] | None = None,
) -> str:
    """Applies locale-at-render-time feedback to one exact registered form."""

    if type(html) is not str or type(definition) is not FrontendFormDefinitionV1:
        raise ValueError("Validation rendering requires HTML and one registered form.")
    if type(state) is not FrontendSubmittedFormStateV1 or state.form_key != definition.form_key:
        raise ValueError("Submitted form state must match the registered form key.")
    translated: list[tuple[str | None, str, str]] = []
    field_messages: dict[str, list[tuple[str, str]]] = {}
    rendered_fields: dict[str, str] = {}
    field_definitions = {field.field_key: field for field in definition.safe_fields}
    evidence_anchor = None
    for index, issue in enumerate(state.validation_issues, start=1):
        message = translate_frontend_message_v1(
            locale,
            issue.message_key,
            **issue.interpolation_values(),
        )
        feedback = issue.session_card_feedback
        if (session_card_details is not None and feedback is not None
                and feedback.route == definition.action_route
                and feedback.selection == state.safe_visible_values.singular("card_selection")
                and _find_form_bounds(html, definition, None,
                    (("card_selection", feedback.selection),)) is not None):
            message, evidence_anchor = session_card_details
            if evidence_anchor is not None and f'id="{evidence_anchor}"' not in html:
                evidence_anchor = None
        message_id = f"validation-message-{state.feedback_generation}-{index}"
        translated.append((issue.field_key, message_id, message))
        if issue.field_key is not None:
            field_messages.setdefault(issue.field_key, []).append((message_id, message))
    identity_fields = (
        ("time_selection",)
        if definition.discriminator_field == "time_form"
        else
        ("managed_family", "managed_handle")
        if definition.form_key == "profile.managed_label"
        else ("player_handle",)
        if definition.form_key in {"profile.player_update", "profile.player_remove"}
        else ("decision_selection",)
        if definition.form_key == "session.review_decision"
        else ("report_id",)
        if definition.form_key == "match.transfer_report"
        else ("recovery_selection",)
        if definition.form_key.startswith("match.recovery.")
        else ("correction_selection",)
        if definition.form_key.startswith("session.correction.")
        else ("card_selection",)
        if definition.action_route in {"/sessions/cards", "/sessions/play", "/matches/cards"}
        else ("declaration_selection",)
        if definition.discriminator_field == "declaration_form"
        else ()
    )
    form_identity = tuple(
        (field, value)
        for field in identity_fields
        if (value := state.safe_visible_values.singular(field)) is not None
    )
    form_instance = None if form_identity else state.form_instance
    card_entry = definition.action_route in {"/sessions/cards", "/sessions/play", "/matches/cards"}
    declaration_entry = definition.discriminator_field == "declaration_form"
    time_entry = definition.discriminator_field == "time_form"
    # A missing/malformed source token cannot qualify an attempted selection for
    # today's actor merely because its old form happened to have the same ordinal.
    correction_entry = definition.form_key.startswith("session.correction.")
    source_bound = card_entry or declaration_entry or time_entry or correction_entry
    bounds = (None if source_bound and not form_identity else
              _find_form_bounds(html, definition, form_instance, form_identity))
    learning_report = definition.form_key == "learning.operation.import_strategy_teacher_report"
    if bounds is None:
        if learning_report and '<!-- report-attachment-feedback -->' in html:
            marker = '<!-- report-attachment-feedback -->'
            start = html.index(marker)
            html = _open_containing_details(html, start, start + len(marker))
            summary = _render_summary(
                state, translated, field_definitions, rendered_fields, locale=locale,
                fallback_anchor="learning-report-target",
                last_valid_result_retained=last_valid_result_retained)
            return html.replace(marker, summary + _learning_report_feedback("", state, locale), 1)
        if correction_entry:
            summary = _render_summary(
                state, translated, field_definitions, rendered_fields, locale=locale,
                fallback_anchor="session-recording",
                last_valid_result_retained=last_valid_result_retained)
            return html.replace('<div id="session-correction-feedback"></div>',
                '<div id="session-correction-feedback">' + summary + '</div>', 1)
        if declaration_entry:
            session = definition.active_context_requirement == "sessions"
            target = 'session-card-feedback' if session else 'match-recovery-feedback'
            summary = _render_summary(
                state, translated, field_definitions, rendered_fields, locale=locale,
                fallback_anchor="session-recording" if session else "match-recording",
                last_valid_result_retained=last_valid_result_retained)
            # Stale values are visible as rejected input, never restored into a new source form.
            summary += '<details open><summary>' + escape(translate_frontend_message_v1(
                locale, "declaration.rejected_input")) + '</summary><dl>'
            for entry in state.safe_visible_values.entries:
                field = field_definitions.get(entry.field)
                if field is not None and entry.field not in {
                        "declaration_selection", "declarer_player_id"}:
                    summary += '<dt>' + escape(translate_frontend_message_v1(
                        locale, field.field_label_key)) + '</dt><dd>'
                    value = entry.values[0]
                    if field.control_type == "checkbox":
                        value = translate_frontend_message_v1(locale,
                            "common.answer.yes" if value == "true" else "common.answer.no")
                    elif entry.field == "game_type" and value:
                        value = translate_frontend_message_v1(locale, "task.value." + value)
                    elif not value:
                        value = translate_frontend_message_v1(locale, "declaration.not_entered")
                    summary += escape(value) + '</dd>'
            summary += '</dl></details>'
            return html.replace(f'<div id="{target}"></div>',
                                f'<div id="{target}">' + summary + '</div>', 1)
        if definition.action_route in {"/sessions/cards", "/sessions/play", "/matches/cards"}:
            session = definition.active_context_requirement == "sessions"
            anchor = "session-recording" if session else "match-recording"
            summary = _render_summary(
                state, translated, field_definitions, rendered_fields, locale=locale,
                fallback_anchor=anchor, last_valid_result_retained=last_valid_result_retained)
            cards = tuple(card for card in state.safe_visible_values.all("cards")
                          if re.fullmatch(r"[CSHD](?:A|10|K|Q|J|9|8|7)", card))
            if cards:
                summary += '<p class="compact-rejected">' + escape(
                    translate_frontend_message_v1(locale, "compact.stale_input",
                                                 cards=', '.join(cards))) + '</p>'
            target = 'session-card-feedback' if session else 'match-recovery-feedback'
            return html.replace(f'<div id="{target}"></div>',
                                f'<div id="{target}">' + summary + '</div>', 1)
        if definition.form_key.startswith("match.recovery."):
            summary = _render_summary(
                state, translated, field_definitions, rendered_fields, locale=locale,
                fallback_anchor="match-recording",
                last_valid_result_retained=last_valid_result_retained,
            )
            return html.replace('<div id="match-recovery-feedback"></div>',
                                '<div id="match-recovery-feedback">' + summary + '</div>', 1)
        if definition.form_key == "session.review_decision":
            summary = _render_summary(
                state, translated, field_definitions, rendered_fields, locale=locale,
                fallback_anchor="recorded-decisions",
                last_valid_result_retained=last_valid_result_retained,
            )
            return html.replace('<div id="recorded-review-feedback"></div>',
                                '<div id="recorded-review-feedback">' + summary + '</div>', 1)
        return _prepend_to_main(
            html,
            _render_summary(
                state,
                translated,
                field_definitions,
                rendered_fields,
                locale=locale,
                fallback_anchor="main-content",
                last_valid_result_retained=last_valid_result_retained,
            ),
        )
    form_start, form_end = bounds
    html = _open_containing_details(html, form_start, form_end)
    bounds = _find_form_bounds(html, definition, form_instance, form_identity)
    if bounds is None:
        return html
    form_start, form_end = bounds
    block = _replace_values(html[form_start:form_end], state)
    if learning_report:
        block = _learning_report_feedback(block, state, locale)
    for field, messages in field_messages.items():
        block = _open_field_details(block, field)
        described_by = " ".join(identifier for identifier, _message in messages)
        control_id = f"validation-field-{state.feedback_generation}-{field}"
        singleton_target = (learning_report and field == "match_snapshot_id"
                            and '<select ' not in block)
        if singleton_target:
            rendered_control_id = "learning-report-target"
            block = block.replace('<div id="learning-report-target" tabindex="-1">',
                '<div id="learning-report-target" tabindex="-1" '
                f'aria-describedby="{escape(described_by, quote=True)}">', 1)
        else:
            block, rendered_control_id = _add_control_accessibility(
                block, field, described_by, control_id)
        if rendered_control_id is None:
            continue
        rendered_fields[field] = rendered_control_id
        rendered_messages = "".join(
            f'<p class="field-error" id="{identifier}">{escape(message)}</p>'
            for identifier, message in messages
        )
        if singleton_target:
            block = block.replace('</div>', rendered_messages + '</div>', 1)
        else:
            block = _insert_field_messages(block, field, rendered_messages)

    form_anchor_id = f"validation-form-heading-{state.feedback_generation}"
    summary = _render_summary(
        state,
        translated,
        field_definitions,
        rendered_fields,
        locale=locale,
        fallback_anchor="learning-report-target" if learning_report else form_anchor_id,
        last_valid_result_retained=last_valid_result_retained,
        evidence_anchor=evidence_anchor,
    )
    form_anchor = f'<span class="validation-anchor" id="{form_anchor_id}"></span>'
    block = form_anchor + block
    return html[:form_start] + summary + block + html[form_end:]
