import json
from collections.abc import Iterable
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Any

from skatmind.errors import (
    SkatMindInvariantError,
    SkatMindResourceError,
    SkatMindSchemaError,
)

_INPUT_SCHEMA_NAME = "input.schema.json"
_OUTPUT_SCHEMA_NAME = "output.schema.json"
_SCOPED_RESOURCES = ContextVar("checked_schema_resources", default=None)


@contextmanager
def _share_checked_resources():
    """One synchronous execution may reuse its fully checked package registry."""
    token = _SCOPED_RESOURCES.set({})
    try:
        yield
    finally:
        _SCOPED_RESOURCES.reset(token)


def _schema_resource_root() -> Traversable:
    from skatmind import schema_resources

    try:
        return resources.files(schema_resources)
    except (ModuleNotFoundError, OSError, TypeError) as error:
        raise SkatMindResourceError(str(error)) from error


def _read_schema(resource: Traversable) -> dict[str, Any]:
    try:
        content = resource.read_bytes().decode("utf-8")
    except OSError as error:
        raise SkatMindResourceError(str(error)) from error
    except UnicodeDecodeError as error:
        raise SkatMindInvariantError(
            f"Packaged schema {resource.name!r} is not valid UTF-8: {error}."
        ) from error
    try:
        schema = json.loads(content)
    except json.JSONDecodeError as error:
        raise SkatMindInvariantError(
            f"Packaged schema {resource.name!r} is not valid JSON: {error}."
        ) from error
    if not isinstance(schema, dict):
        raise SkatMindInvariantError(
            f"Packaged schema {resource.name!r} must contain a JSON object."
        )
    return schema


def _reject_schema_retrieval(uri: str):
    from referencing.exceptions import NoSuchResource

    raise NoSuchResource(ref=uri)


@lru_cache(maxsize=3)
def _validator_for(schema_name: str):
    from jsonschema import Draft202012Validator, FormatChecker

    scope = _SCOPED_RESOURCES.get()
    if scope is not None and "checked" in scope:
        registry, by_name = scope["checked"]
    else:
        registry, by_name = _checked_package_resources(schema_name)
        if scope is not None:
            scope["checked"] = registry, by_name
    if schema_name not in by_name:
        raise SkatMindResourceError(f"Schema resource not found: {schema_name!r}.")
    return Draft202012Validator(by_name[schema_name], registry=registry,
        format_checker=FormatChecker() if schema_name == _INPUT_SCHEMA_NAME else None)


def _checked_package_resources(schema_name):
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
    from referencing import Registry, Resource
    from referencing.exceptions import CannotDetermineSpecification
    from referencing.jsonschema import UnknownDialect

    resource_root = _schema_resource_root()
    try:
        schema_resources = sorted(
            (
                resource
                for resource in resource_root.iterdir()
                if resource.name.endswith(".schema.json") and resource.is_file()
            ),
            key=lambda resource: resource.name,
        )
    except OSError as error:
        raise SkatMindResourceError(str(error)) from error
    if schema_name not in {resource.name for resource in schema_resources}:
        raise SkatMindResourceError(f"Schema resource not found: {schema_name!r}.")
    schemas = [(resource, _read_schema(resource)) for resource in schema_resources]

    registry_resources = []
    schema_ids: set[str] = set()
    for resource, schema in schemas:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise SkatMindInvariantError(
                f"Packaged schema {resource.name!r} is invalid: {error.message}"
            ) from error
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise SkatMindInvariantError(
                f"Packaged schema {resource.name!r} requires a non-empty $id."
            )
        if schema_id in schema_ids:
            raise SkatMindInvariantError(f"Packaged schema $id {schema_id!r} is duplicated.")
        schema_ids.add(schema_id)
        try:
            registry_resources.append((schema_id, Resource.from_contents(schema)))
        except (CannotDetermineSpecification, UnknownDialect) as error:
            raise SkatMindInvariantError(
                f"Packaged schema {resource.name!r} has no supported specification."
            ) from error
    registry = Registry(retrieve=_reject_schema_retrieval).with_resources(
        registry_resources
    )
    return registry, {resource.name: schema for resource, schema in schemas}


def _sortable_path(path: Iterable[object]) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, token) if type(token) is int else (1, str(token))
        for token in path
    )


def _error_sort_key(error) -> tuple[object, ...]:
    return (
        _sortable_path(error.absolute_path),
        _sortable_path(error.absolute_schema_path),
        error.message,
    )


def _json_pointer(path: Iterable[object]) -> str:
    tokens = (
        str(token).replace("~", "~0").replace("/", "~1")
        for token in path
    )
    return "".join(f"/{token}" for token in tokens)


def _validate_document(document: object, *, schema_name: str) -> None:
    from referencing.exceptions import Unresolvable

    validator = _validator_for(schema_name)
    try:
        errors = sorted(validator.iter_errors(document), key=_error_sort_key)
    except Unresolvable as error:
        raise SkatMindResourceError(
            f"Packaged schema resource is unavailable: {error}"
        ) from error
    if errors:
        error = errors[0]
        raise SkatMindSchemaError(
            error.message,
            path=_json_pointer(error.absolute_path),
        )


def validate_input_document(document: object) -> None:
    _validate_document(document, schema_name=_INPUT_SCHEMA_NAME)


def validate_output_document(document: object) -> None:
    _validate_document(document, schema_name=_OUTPUT_SCHEMA_NAME)
