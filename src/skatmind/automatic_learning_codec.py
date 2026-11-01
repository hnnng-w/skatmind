"""Private finite JSON and closed-record codec; no execution Report decoder."""

from __future__ import annotations

import hashlib
import json
import math
import types
from dataclasses import fields
from typing import get_args, get_origin, get_type_hints


def canonical_json(value: object) -> bytes:
    def check(item):
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise ValueError("Automatic Learning requires finite JSON values.")

    check(value)
    return json.dumps(
        value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def decode_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON keys are not allowed.")
            result[key] = value
        return result

    def nonfinite(_value):
        raise ValueError("Nonfinite JSON is not allowed.")

    if type(raw) is not bytes or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Expected UTF-8 bytes without a BOM.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite)
        canonical_json(value)  # Also rejects float overflow such as 1e999.
    except (UnicodeError, RecursionError) as error:
        raise ValueError("Invalid Automatic Learning JSON.") from error
    if type(value) is not dict:
        raise ValueError("Expected a JSON object.")
    return value


def fingerprint(domain: str, value: object) -> str:
    return hashlib.sha256(
        b"skatmind\0automatic_learning\0" + domain.encode("ascii") + b"\0" + canonical_json(value)
    ).hexdigest()


def text(value: object) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError("Expected nonempty, unpadded text.")


def digest(value: object) -> None:
    if type(value) is not str or len(value) != 64 or set(value) - set("0123456789abcdef"):
        raise ValueError("Expected a lowercase SHA-256 fingerprint.")


def integer(value: object, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError("Expected a bounded integer.")


def unique(values) -> None:
    if len(values) != len(set(values)):
        raise ValueError("Duplicate identities are not allowed.")


def _convert(annotation, value, *, decode: bool):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is types.UnionType:
        if value is None and type(None) in args:
            return None
        return _convert(next(arg for arg in args if arg is not type(None)), value, decode=decode)
    if origin is tuple:
        if type(value) is not (list if decode else tuple):
            raise ValueError("Expected an immutable tuple / JSON array.")
        return tuple(_convert(args[0], child, decode=decode) for child in value)
    if isinstance(annotation, type) and issubclass(annotation, Record):
        if decode:
            return annotation.from_dict(value)
        if type(value) is not annotation:
            raise ValueError("Expected an exact private record.")
        value.validate()
        return value
    if type(value) is not annotation:
        raise ValueError("Invalid private record field type.")
    return value


class Record:
    """Only explicitly declared dataclass fields are accepted, including defaults."""

    __slots__ = ()

    def validate(self):
        for name, annotation in get_type_hints(type(self)).items():
            _convert(annotation, getattr(self, name), decode=False)
        if type(self.version) is not int or self.version != 1:
            raise ValueError("Unsupported private record version.")

    def to_dict(self):
        def encode(value):
            if isinstance(value, Record):
                return value.to_dict()
            if type(value) is tuple:
                return [encode(item) for item in value]
            return value

        return {field.name: encode(getattr(self, field.name)) for field in fields(self)}

    @classmethod
    def from_dict(cls, value):
        if type(value) is not dict or set(value) != {field.name for field in fields(cls)}:
            raise ValueError("Invalid private record field set.")
        hints = get_type_hints(cls)
        return cls(**{
            name: _convert(hints[name], item, decode=True) for name, item in value.items()
        })
