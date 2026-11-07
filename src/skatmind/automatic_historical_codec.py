"""Bounded lossless native tuples; repetitive Historical provenance stays private."""

import base64
import hashlib
import zlib

from .automatic_learning_codec import canonical_json, decode_json
from .automatic_match_execution_codec import decode_execution_value, encode_execution_value

MAX_EXPANDED_NATIVE_BYTES = 128 * 1024 * 1024


def pack_native(value):
    raw = canonical_json(encode_execution_value(value))
    if len(raw) > MAX_EXPANDED_NATIVE_BYTES:
        raise ValueError("Expanded Historical native tuple exceeds its bound.")
    return {"encoding": "zlib-json-v1", "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": base64.b64encode(zlib.compress(raw)).decode("ascii")}


def unpack_native(value):
    if (type(value) is not dict or set(value) != {"encoding", "size", "sha256", "bytes"}
            or value["encoding"] != "zlib-json-v1" or type(value["size"]) is not int
            or not 0 < value["size"] <= MAX_EXPANDED_NATIVE_BYTES
            or type(value["bytes"]) is not str):
        raise ValueError("Invalid bounded Historical native tuple.")
    try:
        encoded = base64.b64decode(value["bytes"], validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(encoded, value["size"] + 1)
        if (len(raw) != value["size"] or not decoder.eof or decoder.unused_data
                or decoder.unconsumed_tail or hashlib.sha256(raw).hexdigest() != value["sha256"]):
            raise ValueError("Historical native tuple bytes disagree.")
    except (zlib.error, TypeError) as error:
        raise ValueError("Invalid Historical native compression.") from error
    return decode_execution_value(decode_json(raw))
