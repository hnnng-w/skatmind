from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .form_parsing import FormValuesV1
from .form_registry import capture_safe_submitted_values_v1, resolve_frontend_form_v1
from .validation_rendering import _find_form_bounds, _replace_safe_values


@dataclass(frozen=True, slots=True)
class LanguageFormValuesV1:
    form_key: str
    instance: int
    safe_values: FormValuesV1


@dataclass(frozen=True, slots=True)
class LanguagePageValuesV1:
    route: str
    source_handle: str | None
    source_revision: str | None
    forms: tuple[LanguageFormValuesV1, ...]
    open_disclosures: tuple[int, ...]


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Language-switch values must not repeat keys.")
        result[key] = value
    return result


def parse_language_page_values_v1(raw: str, *, route: str) -> LanguagePageValuesV1:
    """Allowlisted presentation values; never accepted Commands or Product facts."""
    if len(raw.encode("utf-8")) > 262_144:
        raise ValueError("Language-switch presentation values exceed the bound.")
    value = json.loads(raw, object_pairs_hook=_object)
    keys = {"forms", "open_disclosures", "source_handle", "source_revision"}
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Language-switch presentation envelope is invalid.")
    forms = value["forms"]
    opened = value["open_disclosures"]
    handle, revision = value["source_handle"], value["source_revision"]
    if handle is not None and (
        type(handle) is not str or not re.fullmatch(r"[0-9a-f]{64}", handle)
    ):
        raise ValueError("Language-switch item binding is invalid.")
    if revision is not None and (type(revision) is not str or not revision.isdecimal()):
        raise ValueError("Language-switch revision is invalid.")
    if type(forms) is not list or len(forms) > 256 or type(opened) is not list:
        raise ValueError("Language-switch presentation collections are invalid.")
    if len(opened) > 1024 or any(
        type(index) is not int or not 0 <= index < 1024 for index in opened
    ):
        raise ValueError("Language-switch disclosure indexes are invalid.")
    retained = []
    seen = set()
    for item in forms:
        if type(item) is not dict or set(item) != {"action", "discriminator", "instance", "values"}:
            raise ValueError("Language-switch form entry is invalid.")
        if type(item["discriminator"]) is not dict or type(item["values"]) is not dict:
            raise ValueError("Language-switch form values must be objects.")
        instance = item["instance"]
        if type(instance) is not int or not 0 <= instance < 256:
            raise ValueError("Language-switch form instance is invalid.")
        definition = resolve_frontend_form_v1(item["action"], item["discriminator"])
        identity = (definition.form_key, instance)
        if identity in seen:
            raise ValueError("Language-switch form identities must not repeat.")
        seen.add(identity)
        supplied = {key: entry for key, entry in item["values"].items() if entry != []}
        retained.append(LanguageFormValuesV1(definition.form_key, instance,
            capture_safe_submitted_values_v1(definition, supplied)))
    return LanguagePageValuesV1(
        route, handle, revision, tuple(retained), tuple(sorted(set(opened))))


def apply_language_page_values_v1(html: str, state: LanguagePageValuesV1) -> str:
    from .form_registry import get_frontend_form_by_key_v1
    for item in state.forms:
        definition = get_frontend_form_by_key_v1(item.form_key)
        bounds = _find_form_bounds(html, definition, item.instance)
        if bounds is None:
            continue
        start, end = bounds
        html = html[:start] + _replace_safe_values(html[start:end], item.safe_values) + html[end:]
    for index, match in reversed(tuple(enumerate(re.finditer(r"<details\b[^>]*>", html)))):
        if (index in state.open_disclosures
                and re.search(r"\sopen(?:\s|=|>)", match.group(0)) is None):
            html = html[:match.end() - 1] + " open>" + html[match.end():]
    return html
