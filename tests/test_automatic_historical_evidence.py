"""Genuine bounded Historical evidence; immutable execution reused across wire negatives."""

from dataclasses import replace

import pytest
from test_guided_historical_review_form import _completed_example_draft

from skatmind.app_web.execution import execute_guided_frontend_review_v1
from skatmind.app_web.historical_form import (
    build_historical_execution_options_v1,
    build_historical_request_v1,
    update_historical_options_v1,
)
from skatmind.automatic_historical_evidence import (
    build_historical_capture_candidate,
    decode_historical_execution,
    decode_historical_source,
)
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.private_execution_capture import capture_native_execution


@pytest.fixture(scope="module")
def genuine_historical():
    draft = update_historical_options_v1(_completed_example_draft())
    request = build_historical_request_v1(draft)
    with capture_native_execution() as native:
        execution = execute_guided_frontend_review_v1(
            request, options=build_historical_execution_options_v1(draft))
    assert len(native) == 1
    return draft, execution, native[0]


def test_independent_guided_sources_preserve_raw_ids_and_exact_bytes(genuine_historical):
    draft, execution, native = genuine_historical
    values = [build_historical_capture_candidate(name, 0, execution, native, draft=draft)
              for name in ("independent-one", "independent-two")]
    assert values[0].source.scope != values[1].source.scope
    for candidate in values:
        source = decode_historical_source(candidate.objects[0], candidate.source)
        retained = decode_historical_execution(candidate.objects[1], candidate.evidence, source)
        assert source.origin == "guided"
        assert source.game.game_id == "frontend-historical-review"
        assert retained.execution == execution
        assert retained.download("request")[1] == execution.request_json_bytes
        assert retained.download("result")[1] == execution.result_json_bytes
        assert "historical_game_review_summary" not in execution.result.result.document[
            "historical_game_summary"]


@pytest.mark.parametrize("field", ("origin", "scope", "game", "draft", "request"))
def test_rehashed_contradictory_source_is_rejected(genuine_historical, field):
    draft, execution, native = genuine_historical
    candidate = build_historical_capture_candidate("one", 0, execution, native, draft=draft)
    obj = candidate.objects[0]
    data = decode_json(obj.payload)
    data[field] = "imported" if field == "origin" else None
    malformed = replace(obj, payload=canonical_json(data))
    record = replace(candidate.source, object_ref=malformed.reference)
    with pytest.raises((ValueError, TypeError, KeyError, AttributeError)):
        decode_historical_source(malformed, record)


def test_placeholder_like_import_does_not_gain_guided_origin(genuine_historical):
    _draft, execution, native = genuine_historical
    candidate = build_historical_capture_candidate("frontend-guided-looking", 0, execution, native)
    source = decode_historical_source(candidate.objects[0], candidate.source)
    assert source.origin == "imported"
    assert source.record.scope.kind == "shared_claim"
    assert source.game.game_id == "frontend-historical-review"
