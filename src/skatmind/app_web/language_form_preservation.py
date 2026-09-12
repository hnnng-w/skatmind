from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser

from .form_parsing import FormValuesV1, FormValueV1
from .form_registry import FrontendFormFieldV1, resolve_frontend_form_v1
from .validation_rendering import (
    _FORM_BLOCK,
    _attribute,
    _replace_safe_values,
    _set_attribute,
)

LANGUAGE_VALUES_MAX_BYTES = 262_144


@dataclass(frozen=True, slots=True)
class LanguageFormV1:
    identity: str
    fields: tuple[FrontendFormFieldV1, ...]
    choices: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class LanguagePageManifestV1:
    forms: tuple[LanguageFormV1, ...]
    disclosure_count: int


@dataclass(frozen=True, slots=True)
class LanguagePageValuesV1:
    forms: tuple[tuple[str, FormValuesV1], ...]
    disclosures: tuple[bool, ...]


class _Controls(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.controls = []
        self.choices: dict[str, list[str]] = {}
        self.select = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"input", "select", "textarea"}:
            self.controls.append((tag, attrs))
        if tag == "select":
            self.select = attrs.get("name")
        if tag == "option" and self.select is not None:
            self.choices.setdefault(self.select, []).append(attrs.get("value", ""))
        if tag == "input" and attrs.get("type") in {"checkbox", "radio"} and "name" in attrs:
            self.choices.setdefault(attrs["name"], []).append(attrs.get("value", "on"))

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None


def instrument_language_forms_v1(html: str) -> tuple[str, LanguagePageManifestV1]:
    """Derive exact form identities from trusted markup, never from client ordinals."""
    forms = []
    counts: dict[str, int] = {}

    def instrument(match):
        opening, content, closing = match.groups()
        if "language-selector" in (_attribute(opening, "class") or ""):
            return match.group(0)
        parsed = _Controls(content)
        controls = parsed.controls
        hidden = tuple((attrs.get("name"), attrs.get("value", "")) for _, attrs in controls
            if attrs.get("type") == "hidden"
            and attrs.get("name") not in {"profile_generation", "_frontend_form_instance"})
        try:
            definition = resolve_frontend_form_v1(_attribute(opening, "action"), dict(hidden),
                media_type=_attribute(opening, "enctype") or "application/x-www-form-urlencoded")
        except (KeyError, ValueError):
            return match.group(0)
        names = {attrs.get("name") for _, attrs in controls
            if attrs.get("type") not in {"hidden", "file", "password", "submit", "button"}
            and "disabled" not in attrs}
        fields = tuple(field for field in definition.safe_fields if field.field_key in names
            and field.control_type != "file" and not field.clear_after_rejection)
        if not fields:
            return match.group(0)
        # Stable hidden identities distinguish Players, reports, annotations, and
        # recovery selections. An ordinal only disambiguates identical forms within
        # this exact source page, whose complete manifest is checked on restoration.
        base = json.dumps((definition.form_key, hidden, sorted(names)), separators=(",", ":"))
        ordinal = counts.get(base, 0)
        counts[base] = ordinal + 1
        identity = hashlib.sha256(f"{base}\0{ordinal}".encode()).hexdigest()
        choices = tuple((field.field_key, tuple(parsed.choices[field.field_key]))
                        for field in fields if field.field_key in parsed.choices)
        forms.append(LanguageFormV1(identity, fields, choices))
        opening = _set_attribute(opening, "data-language-form", identity)
        opening = _set_attribute(opening, "data-preserve-fields",
                                 " ".join(field.field_key for field in fields))
        opening = _set_attribute(opening, "data-preserve-limits", json.dumps({
            field.field_key: [field.reflection_length, 64 if field.cardinality == "repeated" else 1]
            for field in fields}, separators=(",", ":")))
        return opening + content + closing

    html = _FORM_BLOCK.sub(instrument, html)
    count = len(tuple(re.finditer(r"<details\b", html)))
    return html, LanguagePageManifestV1(tuple(forms), count)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Language-switch values must not repeat keys.")
        result[key] = value
    return result


def parse_language_page_values_v1(
    raw: str, *, manifest: LanguagePageManifestV1,
) -> LanguagePageValuesV1:
    """Allowlisted presentation values; never accepted Commands or Product facts."""
    if len(raw.encode("utf-8")) > LANGUAGE_VALUES_MAX_BYTES:
        raise ValueError("Language-switch presentation values exceed the bound.")
    try:
        value = json.loads(raw, object_pairs_hook=_object)
    except RecursionError as error:
        raise ValueError("Language-switch presentation nesting is invalid.") from error
    keys = {"forms", "disclosures"}
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Language-switch presentation envelope is invalid.")
    forms = value["forms"]
    disclosures = value["disclosures"]
    if type(forms) is not list or len(forms) > 256 or type(disclosures) is not list:
        raise ValueError("Language-switch presentation collections are invalid.")
    if (len(disclosures) != manifest.disclosure_count or len(disclosures) > 1024
            or any(type(opened) is not bool for opened in disclosures)):
        raise ValueError("Language-switch disclosure states are invalid.")
    retained = []
    seen = set()
    registered = {form.identity: form for form in manifest.forms}
    for item in forms:
        if type(item) is not dict or set(item) != {"form", "values"}:
            raise ValueError("Language-switch form entry is invalid.")
        identity = item["form"]
        if type(identity) is not str or identity not in registered or identity in seen:
            raise ValueError("Language-switch form identity is invalid.")
        seen.add(identity)
        fields = {field.field_key: field for field in registered[identity].fields}
        choices = dict(registered[identity].choices)
        values = item["values"]
        if type(values) is not dict or not set(values) <= set(fields):
            raise ValueError("Language-switch fields must be registered visible controls.")
        entries = []
        for name, supplied in values.items():
            field = fields[name]
            if (type(supplied) is not list
                    or len(supplied) > (64 if field.cardinality == "repeated" else 1)
                    or any(type(entry) is not str or len(entry) > field.reflection_length
                           for entry in supplied)):
                raise ValueError("Language-switch field values exceed their bounds.")
            if field.allowed_values and any(entry and entry not in field.allowed_values
                                            for entry in supplied):
                raise ValueError("Language-switch choice is unsupported.")
            if name in choices and any(entry and entry not in choices[name] for entry in supplied):
                raise ValueError("Language-switch choice must belong to the exact rendered form.")
            if field.control_type == "card" and any(entry and not re.fullmatch(
                    r"[CSHD](?:A|10|K|Q|J|9|8|7)", entry) for entry in supplied):
                raise ValueError("Language-switch Card choice is invalid.")
            if (name.endswith("_handle") and any(entry and not re.fullmatch(r"[0-9a-f]{64}", entry)
                                                for entry in supplied)):
                raise ValueError("Language-switch identity choice is invalid.")
            entries.append(FormValueV1(field=name, values=tuple(supplied) or ("",)))
        retained.append((identity, FormValuesV1(tuple(entries))))
    return LanguagePageValuesV1(tuple(retained), tuple(disclosures))


def apply_language_page_values_v1(html: str, state: LanguagePageValuesV1) -> str:
    values = dict(state.forms)
    def restore(match):
        identity = _attribute(match.group(1), "data-language-form")
        return (_replace_safe_values(match.group(0), values[identity])
                if identity in values else match.group(0))
    html = _FORM_BLOCK.sub(restore, html)
    stack = []
    required = set()
    for match in re.finditer(
            r'<details\b[^>]*>|</details>|'
            r'<[^>]+(?:aria-invalid="true"|class="error-summary")[^>]*>', html):
        if match.group(0).startswith("<details"):
            stack.append(match.start())
        elif match.group(0) == "</details>":
            if stack:
                stack.pop()
        else:
            required.update(stack)
    for index, match in reversed(tuple(enumerate(re.finditer(r"<details\b[^>]*>", html)))):
        html = (html[:match.start()] + _set_attribute(match.group(0), "open",
                "open" if state.disclosures[index] or match.start() in required else None)
                + html[match.end():])
    return html
