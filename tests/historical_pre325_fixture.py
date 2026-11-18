"""Frozen genuine guided source from accepted pre-#325 commit fca6b3a.

Generated with that commit's historical_form and automatic_historical_evidence
modules (loaded with git show), using _completed_example_draft() and default
result-only options. The baseline writer and decoder both accepted these bytes.
Do not regenerate this fixture using the candidate writer: it guards compatibility,
not a same-version roundtrip. Compression is test storage only, not an archive codec.
"""

import base64
import hashlib
import zlib

from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_learning_contracts import SourceRecordV1
from skatmind.automatic_learning_objects import StoredObjectV1

BASELINE = "fca6b3a1defe8a6320bbf8a8ee73840e7af26b46"
SOURCE_PAYLOAD_SHA256 = "44bc213aa3d525d5d3ed9703efabb01cf8a428784b510e8dad6ca98fc112af0b"
DRAFT_WIRE_SHA256 = "16d425c4b46a1a37944207bd989511ca874fc1b3a0f036260e3ccab1feafa7a3"
SOURCE_PAYLOAD = (
    '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'
    'ebem/2Y5I82JKz/+B+a5tuw='
)


def legacy_guided_source():
    payload = zlib.decompress(base64.b64decode(SOURCE_PAYLOAD))
    assert len(payload) == 11957
    assert hashlib.sha256(payload).hexdigest() == SOURCE_PAYLOAD_SHA256
    wire = decode_json(payload)["draft"]
    assert hashlib.sha256(canonical_json(wire)).hexdigest() == DRAFT_WIRE_SHA256
    obj = StoredObjectV1(area="sources", kind="historical_source", codec_version=2, payload=payload)
    record = SourceRecordV1.from_dict({
        "source_version": {
            "source": {"family": "historical_review", "product_id": "pre325-guided-fixture",
                       "version": 1},
            "source_contract": "saved_historical_review", "contract_version": 1,
            "content_fingerprint": (
                "4ab5c0dfae81e65124d46ac9a79feab1f92e49761a9b034d46f6ae8cb793741a"),
            "version": 1},
        "object_ref": {"area": "sources", "kind": "historical_source", "codec_version": 2,
            "fingerprint": "c6be7360c917f3608af3c995493ccf96e6982d457abcdbcc4c5236573d48ce65",
            "size_bytes": 12062, "version": 1},
        "scope": {"kind": "source_local",
            "namespace": "7d0b5a0c8c9d212bd22a53a19991f432b4181d18fefb39d97ace9c8b77c52f85",
            "version": 1},
        "revision": 0, "version": 1})
    assert obj.reference == record.object_ref
    return obj, record
