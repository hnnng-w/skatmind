"""Private native Match form ownership and one-use evidence-successor presentation."""

from __future__ import annotations

import hmac
import re
import secrets
import time
from dataclasses import dataclass, field, replace

from skatmind.observed_trace_diagnostics import ObservedTraceError

from .card_entry_http import (
    MATCH_EVIDENCE_FORMS,
    CardEntryConflict,
    _fresh,
    _match_entry,
    match_card_binding,
)
from .compact_declaration_form import DECLARATION_FIELDS, form_error
from .compact_declaration_http import declaration_binding, dispatch_compact_declaration
from .form_parsing import FormValuesV1, FormValueV1
from .session_card_entry import CardEntryError

MATCH_RECORDING_INPUT_ROUTE = "/matches/recording-input"
MATCH_RECORDING_FORM_ID = "match-recording-input"
EVIDENCE_FIELDS = (
    "evidence_perspective_hand", "evidence_original_skat", "evidence_discarded_cards")
DRAFT_FIELDS = ("declarer_player_id", *DECLARATION_FIELDS)
RETURN_SECONDS = 60
_FRAGMENT = re.compile(
    r'<!-- match-input:([a-z_]+):start -->(.*?)<!-- match-input:\1:end -->', re.S)


class DeclarationDraftConflict(CardEntryConflict):
    """No presentation values may be restored to the current recording."""


def fragment(name, content):
    return f'<!-- match-input:{name}:start -->{content}<!-- match-input:{name}:end -->'


def assemble_recording_input(html):
    """Normalize this one external-owner form for existing safe-field renderers.

    Each fragment is moved, never copied. Final delivery restores its exact visual
    location and native form ownership, without changing other forms.
    """
    if f'id="{MATCH_RECORDING_FORM_ID}"' not in html:
        return html
    fragments = []
    def collect(match):
        fragments.append(match[0])
        return f'<!-- match-input:{match[1]}:location -->'
    html = _FRAGMENT.sub(collect, html)
    start = html.index(f'id="{MATCH_RECORDING_FORM_ID}"')
    end = html.index('</form>', start)
    return html[:end] + ''.join(fragments) + html[end:]


def distribute_recording_input(html):
    from .validation_rendering import _open_containing_details

    fragments = tuple(_FRAGMENT.finditer(html))
    for match in fragments:
        content = re.sub(r'<(input|button|select|textarea|fieldset)\b',
            rf'<\1 form="{MATCH_RECORDING_FORM_ID}"', match[2])
        html = html.replace(match[0], '', 1)
        html = html.replace(f'<!-- match-input:{match[1]}:location -->',
                            fragment(match[1], content), 1)
        if 'aria-invalid="true"' in content or 'class="error-summary"' in content:
            start = html.index(f'<!-- match-input:{match[1]}:start -->')
            html = _open_containing_details(html, start, start + len(content))
    return html


@dataclass(slots=True)
class DeclarationDraftReturn:
    """At most one bounded successor handoff per active Match, never persisted."""

    active: object = field(repr=False)
    selection: str = field(repr=False)
    values: FormValuesV1 = field(repr=False)
    created: float = field(default_factory=time.monotonic)
    token: str = field(default_factory=lambda: secrets.token_hex(32), repr=False)
    consumed: bool = False

    def take(self, active):
        used = self.consumed
        self.consumed = True
        if (used or time.monotonic() - self.created >= RETURN_SECONDS
                or active is not self.active or active.retired
                or not hmac.compare_digest(self.selection,
                    declaration_binding(active, "match-declaration"))):
            raise DeclarationDraftConflict()
        try:
            _fresh(active, session=False)
        except CardEntryConflict as error:
            raise DeclarationDraftConflict() from error
        return self.values


def _parse(values):
    """Structural/choice bounds only. No GameDeclaration construction or defaults."""
    from .form_registry import get_frontend_form_by_key_v1

    required = {"managed_handle", "expected_revision", "match_position", "declaration_form",
                "declaration_selection", "operation", "recording_action",
                "declarer_player_id", "game_type", "bid_value", "matadors"}
    allowed = required | set(DRAFT_FIELDS) | set(EVIDENCE_FIELDS)
    if set(values) - allowed or required - set(values):
        raise form_error("fields")
    if (values["operation"] != "set_declaration"
            or values["declaration_form"] != "match-declaration"
            or values["recording_action"] not in {"set_declaration", *MATCH_EVIDENCE_FORMS}):
        raise form_error("fields")
    if not re.fullmatch(r"[0-9a-f]{64}", values["declaration_selection"]):
        raise form_error("binding")
    definition = get_frontend_form_by_key_v1("match.recording_input")
    fields = {f.field_key: f for f in definition.safe_fields}
    for name, supplied in values.items():
        if name in EVIDENCE_FIELDS:
            if (type(supplied) not in (str, list) or
                    isinstance(supplied, list) and len(supplied) > 32):
                raise form_error("fields")
            entries = [supplied] if isinstance(supplied, str) else supplied
            if any(type(value) is not str or len(value) > 3 for value in entries):
                raise CardEntryError("invalid", name)
        elif type(supplied) is not str or len(supplied) > (
                fields[name].reflection_length if name in fields else 128):
            raise form_error("fields")
    retained = []
    for name in DRAFT_FIELDS:
        value = values.get(name, "")
        definition = fields[name]
        if (definition.allowed_values and value and value not in definition.allowed_values
                or definition.control_type == "checkbox" and name in values and value != "true"):
            raise form_error("fields")
        retained.append(FormValueV1(field=name, values=(value,)))
    return FormValuesV1(tuple(retained))


def _verify_successor(before, predecessor, active, operation):
    if predecessor != (active.handle, active.selected_position,
                       active.position_generation, active.card_entry_key):
        raise DeclarationDraftConflict()
    after = active.workspace.to_dict()
    if before == after:
        return
    field_name = {"set_perspective_hand": "perspective_initial_hand",
                  "set_original_skat": "original_skat",
                  "set_discarded_cards": "discarded_cards"}[operation]
    index = active.selected_position - 1
    before["slots"][index]["observed_game"][field_name] = (
        after["slots"][index]["observed_game"][field_name])
    before["revision"] += 1
    if before != after:
        raise DeclarationDraftConflict()


def dispatch_recording_input(handler, parsed):
    """Route one native submitter; the canonical operation never receives drafts."""
    if parsed.get("recording_action") != ["set_declaration"]:
        handler._current_safe_values = FormValuesV1(tuple(entry for entry in
            handler._current_safe_values.entries if entry.field not in DRAFT_FIELDS))
    # Cardinality is checked here, not relaxed in the shared form parser.
    if any(len(items) != 1 for name, items in parsed.items() if name not in EVIDENCE_FIELDS):
        raise form_error("duplicate")
    values = {name: items if name in EVIDENCE_FIELDS else items[0]
              for name, items in parsed.items()}
    draft = _parse(values)
    app = handler.server.app_context
    with app.managed_stateful.match_lifecycle_lock:
        with app.lock:
            active = app.managed_stateful.active_match
        if active is None or active.handle != values["managed_handle"]:
            raise DeclarationDraftConflict()
        with active.capture.lock:
            active.require_attached()
            if (values["match_position"] != str(active.selected_position)
                    or values["expected_revision"] != str(active.workspace.revision)
                    or not hmac.compare_digest(values["declaration_selection"],
                        declaration_binding(active, "match-declaration"))):
                raise DeclarationDraftConflict()
            _fresh(active, session=False)
            if values["declarer_player_id"] and values["declarer_player_id"] not in {
                    p.player_id for p in active.workspace.match_definition.participants}:
                raise form_error("fields")
            action = values["recording_action"]
            if action == "set_declaration":
                declaration = {name: value for name, value in values.items()
                               if name not in {*EVIDENCE_FIELDS, "recording_action"}}
                handler._redirect(dispatch_compact_declaration(
                    app, "/matches/api/v1/operation", declaration))
                return
            operation, mode = MATCH_EVIDENCE_FORMS[action]
            field_name = "evidence_" + operation.removeprefix("set_")
            before = active.workspace.to_dict()
            predecessor = (active.handle, active.selected_position,
                           active.position_generation, active.card_entry_key)
            payload = {"managed_handle": active.handle, "operation": operation,
                       "card_selection": match_card_binding(active, operation),
                       "card_evidence_form": action}
            if mode == "exact":
                payload["cards"] = values.get(field_name, [])
            error = None
            status = 400
            try:
                _match_entry(active, payload)
            except CardEntryConflict as failure:
                if failure.reason != "save_failed":
                    raise
                error, status = failure, 409
            except (CardEntryError, ObservedTraceError) as failure:
                if isinstance(failure, CardEntryError):
                    failure.field_key = field_name if mode == "exact" else None
                error = failure
            _verify_successor(before, predecessor, active, operation)
            _fresh(active, session=False)
            returned = DeclarationDraftReturn(active,
                declaration_binding(active, "match-declaration"), draft)
            if error is not None:
                handler._declaration_draft_return = returned
                from .validation_contracts import FrontendValidationIssueV1

                issues = (None if isinstance(error, (CardEntryError, CardEntryConflict)) else (
                    FrontendValidationIssueV1(field_key=field_name if mode == "exact" else None,
                        message_key="validation.message.match_recording_conflict"),))
                handler._reject_registered_form(error, status=status, issues=issues)
            else:
                active.declaration_draft_return = returned
                handler._redirect(f"/matches/position/{active.selected_position}"
                    f"?_declaration_return={returned.token}#match-recording")


def take_recording_draft(handler, active):
    """Called under the source lock; consume before checking, including failures."""
    pending = getattr(handler, "_declaration_draft_return", None)
    token = getattr(handler, "_declaration_return_token", None)
    if token is not None:
        pending = active.declaration_draft_return
        active.declaration_draft_return = None
        if pending is None or not hmac.compare_digest(token, pending.token):
            raise DeclarationDraftConflict()
    if pending is None:
        active.declaration_draft_return = None
        return None
    handler._native_draft_deadline = pending.created + RETURN_SECONDS
    return pending.take(active)


def continue_native_match_draft(page, overlay):
    """Carry only this already-submitted draft through the unchanged language gate."""
    native = page.native_match_draft
    if native is None or overlay is None:
        return native
    updates = dict(overlay.forms)
    forms = []
    for identity, values in native.forms:
        merged = {entry.field: entry for entry in values.entries}
        if identity in updates:
            merged.update((entry.field, entry) for entry in updates[identity].entries
                          if entry.field in DRAFT_FIELDS)
        forms.append((identity, FormValuesV1(tuple(merged.values()))))
    return replace(native, forms=tuple(forms), disclosures=overlay.disclosures)


def bridge_independent_evidence_feedback(active, definition, state):
    """Compatibility feedback may reach the new editor only on its verified source."""
    if active is None or definition.action_route != "/matches/cards":
        return definition, state
    from .form_registry import get_frontend_form_by_key_v1

    marker = definition.discriminator_value
    if definition.form_key.startswith("match.cards."):
        marker = next((key for key, intent in MATCH_EVIDENCE_FORMS.items() if intent == (
            definition.discriminator_value,
            state.safe_visible_values.singular("card_evidence_mode"))), None)
    if marker not in MATCH_EVIDENCE_FORMS:
        return definition, state
    operation, mode = MATCH_EVIDENCE_FORMS[marker]
    with active.capture.lock:
        if (active.retired or state.safe_visible_values.singular("card_selection")
                != match_card_binding(active, operation)):
            return definition, state
        try:
            _fresh(active, session=False)
        except CardEntryConflict:
            return definition, state
        name = "evidence_" + operation.removeprefix("set_")
        values = [FormValueV1(field="declaration_selection",
                             values=(declaration_binding(active, "match-declaration"),)),
                  FormValueV1(field="recording_action", values=(marker,))]
        if mode == "exact":
            values.append(FormValueV1(
                field=name, values=state.safe_visible_values.all("cards") or ("",)))
        definition = get_frontend_form_by_key_v1("match.recording_input")
        state = replace(state, form_key=definition.form_key,
            originating_route=definition.action_route,
            form_instance=None, safe_visible_values=FormValuesV1(tuple(values)),
            validation_issues=tuple(replace(issue, field_key=name if mode == "exact" else None)
                                    for issue in state.validation_issues))
        return definition, state
