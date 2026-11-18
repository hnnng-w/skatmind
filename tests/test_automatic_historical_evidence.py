"""Genuine bounded Historical evidence; immutable execution reused across wire negatives."""

from dataclasses import replace

import pytest
from historical_pre325_fixture import legacy_guided_source
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
    draft_wire,
    resume_guided_draft,
)
from skatmind.automatic_learning_codec import canonical_json, decode_json
from skatmind.automatic_match_execution_codec import decode_execution_value
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


@pytest.fixture(scope="module")
def legacy_candidate(genuine_historical):
    draft, execution, native = genuine_historical
    obj, record = legacy_guided_source()
    candidate = build_historical_capture_candidate(record.source_version.source.product_id,
        0, execution, native, draft=draft)
    assert candidate.source == record and candidate.objects[0].raw == obj.raw
    # Admission consumes the frozen baseline object, not a candidate-generated substitute.
    return replace(candidate, source=record, objects=(obj, candidate.objects[1]))


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


def test_pre325_wire_and_source_keep_exact_bytes_and_identity(genuine_historical):
    draft, execution, native = genuine_historical
    obj, record = legacy_guided_source()
    wire = decode_json(obj.payload)["draft"]
    resumed = resume_guided_draft(wire)
    assert resumed == draft and resumed.analysis_form_values is None
    assert tuple(decode_execution_value(wire)) == (
        "step", "players", "skat", "declaration", "discarded_cards", "plays", "options")
    assert draft_wire(resumed) == wire
    source = decode_historical_source(obj, record)
    assert source.record == record and source.request == execution.request
    candidate = build_historical_capture_candidate(
        record.source_version.source.product_id, 0, execution, native, draft=draft)
    assert candidate.source == record
    assert candidate.objects[0].raw == obj.raw


def test_private_controls_cannot_change_producer_wire_or_source_identity(genuine_historical):
    from skatmind.app_web.analysis_controls import safe_controls

    draft, execution, native = genuine_historical
    original = build_historical_capture_candidate("ui-isolation", 0, execution, native, draft=draft)
    # Reuse one genuine result-only execution. Only private, inactive UI state differs.
    for values in (
        {"settings_mode": "custom", "analysis_effort": "quick", "immediate_sample_count": "7"},
        {"settings_mode": "custom", "analysis_effort": "more_time", "search_seed": "19"},
    ):
        changed = replace(draft, analysis_form_values=safe_controls(values))
        candidate = build_historical_capture_candidate(
            "ui-isolation", 0, execution, native, draft=changed)
        assert candidate == original
        assert draft_wire(changed) == draft_wire(draft)
        assert changed.analysis_form_values == safe_controls(values)
        source = decode_historical_source(candidate.objects[0], candidate.source)
        retained = decode_historical_execution(candidate.objects[1], candidate.evidence, source)
        assert retained.guided_draft.analysis_form_values is None
        assert retained.guided_draft.options == changed.options
        assert not retained.guided_draft.options.immediate_review
        assert retained.execution.options == execution.options
        assert retained.download("request")[1] == execution.request_json_bytes
        assert retained.download("result")[1] == execution.result_json_bytes


@pytest.mark.parametrize("defect", ("extra_ui_none", "extra_ui_mapping", "order", "type", "card"))
def test_legacy_guided_wire_is_still_strict(defect):
    obj, record = legacy_guided_source()
    data = decode_json(obj.payload)
    fields = data["draft"]["value"]
    if defect.startswith("extra_ui"):
        fields.append(["analysis_form_values", None if defect == "extra_ui_none" else
                       {"type": "mapping", "value": []}])
    elif defect == "order":
        fields.reverse()
    elif defect == "type":
        fields[0][1] = True
    else:
        # Rehashed, well-formed draft contradicts the retained factual Request.
        players = fields[1][1]["value"]
        players[0]["value"][3][1]["value"][0] = "H7"
    malformed = replace(obj, payload=canonical_json(data))
    with pytest.raises((ValueError, TypeError)):
        decode_historical_source(malformed, replace(record, object_ref=malformed.reference))
