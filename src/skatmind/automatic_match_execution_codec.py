"""Closed private codec for original Match Application executions and rollout Reports.

Only the explicitly listed immutable contracts can be reconstructed. Wire values
never name Python modules or select arbitrary constructors. Mapping order is
retained so original canonical download bytes can be reconciled exactly.
"""

from collections.abc import Mapping
from dataclasses import fields

from .api.v1.contracts import RequestDocumentV1, ResultDocumentV1, WorkflowV1
from .application.contracts import (
    ApplicationArtifact,
    ApplicationExecutionOptions,
    ApplicationExecutionResult,
    ApplicationExternalDocuments,
    ApplicationInvocation,
    HistoricalGameApplicationOptions,
    PositionAnalysisApplicationOptions,
)
from .application.provenance import ApplicationProvenanceAttachment, ApplicationProvenanceBundle
from .automatic_learning_codec import _decode_json_and_canonical_bytes, canonical_json
from .field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceExemption,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
)
from .field_provenance_coverage import FieldProvenanceCoverageSummary
from .field_provenance_policy import InformationUseContext
from .match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisOptionsV1,
    MatchDecisionAnalysisResultV1,
    MatchHistoricalAnalysisOptionsV1,
    MatchHistoricalAnalysisResultV1,
)
from .match_decision_review_preparation import MatchDecisionOpponentProfileBindingV1
from .v1_information_provenance_enforcement import validate_v1_retained_stage_linkage
from .v1_information_provenance_serialization import (
    V1InformationProvenanceArtifactCheckpoint,
    V1InformationProvenanceSerializationCheckpoint,
    validate_v1_information_provenance_serialization_checkpoint,
)
from .v1_information_provenance_sources import (
    V1InformationProvenanceSourceBinding,
    V1InformationProvenanceSourceMetadata,
    V1InformationProvenanceSources,
    validate_v1_information_provenance_sources,
)
from .whole_game_rollout_contracts import WholeGameRolloutSettingsV1

_TYPES = {cls.__name__: cls for cls in (
    RequestDocumentV1, ResultDocumentV1, ApplicationArtifact, ApplicationExecutionOptions,
    ApplicationExecutionResult, ApplicationExternalDocuments, ApplicationInvocation,
    PositionAnalysisApplicationOptions, ApplicationProvenanceAttachment,
    HistoricalGameApplicationOptions,
    ApplicationProvenanceBundle,
    FieldProvenanceEntry, FieldProvenanceExemption, FieldProvenanceLedger,
    FieldProvenanceSourceReference, FieldProvenanceCoverageSummary, InformationUseContext,
    V1InformationProvenanceArtifactCheckpoint, V1InformationProvenanceSerializationCheckpoint,
    V1InformationProvenanceSourceBinding, V1InformationProvenanceSourceMetadata,
    V1InformationProvenanceSources,
    MatchAnalysisReportV1, MatchDecisionAnalysisOptionsV1, MatchDecisionAnalysisResultV1,
    MatchDecisionOpponentProfileBindingV1, WholeGameRolloutSettingsV1,
    MatchHistoricalAnalysisOptionsV1, MatchHistoricalAnalysisResultV1,
)}


def _record_wire(value, encode):
    return {"type": type(value).__name__, "value": {
        item.name: encode(getattr(value, item.name)) for item in fields(value)}}


def encode_execution_value(value):
    if type(value) is WorkflowV1:
        return {"type": "workflow", "value": value.value}
    if value is None or type(value) in (str, bool, int, float):
        return value
    if isinstance(value, Mapping):
        return {"type": "mapping", "value": [
            [key, encode_execution_value(item)] for key, item in value.items()]}
    if type(value) in (tuple, list):
        return {"type": "sequence", "value": [encode_execution_value(item) for item in value]}
    if type(value) not in _TYPES.values():
        raise ValueError("Unsupported retained Application contract.")
    result = _record_wire(value, encode_execution_value)
    if type(value) in (PositionAnalysisApplicationOptions, HistoricalGameApplicationOptions):
        result["supplied"] = list(value._provenance_supplied_option_names)
    return result


def _same_wire(left, right):
    """Exact JSON tree, including mapping order, numeric types and signed zero."""
    kind = type(left)
    if kind is not type(right):
        return False
    if kind is dict:
        return len(left) == len(right) and all(
            type(k) is str and type(j) is str and k == j and _same_wire(v, w)
            for (k, v), (j, w) in zip(left.items(), right.items(), strict=True))
    if kind is list:
        return len(left) == len(right) and all(map(_same_wire, left, right))
    if kind is float:
        return left.hex() == right.hex()
    return (left is None or kind in (str, int, bool)) and left == right


def _decode(value, *, execution_bundle=None):
    if value is None or type(value) in (str, bool, int, float):
        return value
    if type(value) is not dict or set(value) not in (
            {"type", "value"}, {"type", "value", "supplied"}):
        raise ValueError("Invalid retained Application value.")
    kind, data = value["type"], value["value"]
    if type(kind) is not str:
        raise ValueError("Invalid retained Application discriminator.")
    if kind == "workflow":
        result = WorkflowV1(data)
    elif kind == "mapping":
        if (type(data) is not list or any(type(pair) is not list or len(pair) != 2
                or type(pair[0]) is not str for pair in data)
                or len({pair[0] for pair in data}) != len(data)):
            raise ValueError("Invalid retained mapping.")
        result = {key: _decode(item) for key, item in data}
    elif kind == "sequence":
        if type(data) is not list:
            raise ValueError("Invalid retained sequence.")
        result = tuple(_decode(item) for item in data)
    else:
        cls = _TYPES.get(kind)
        if cls is None or type(data) is not dict or set(data) != {
                item.name for item in fields(cls)}:
            raise ValueError("Unsupported retained Application fields.")
        if cls is ApplicationExecutionResult:
            wire = data["provenance"]
            bundle = _decode(wire)
            original = (wire, bundle) if type(bundle) is ApplicationProvenanceBundle else None
            checkpoint = _decode(data["information_provenance_enforcement"],
                                 execution_bundle=original)
            kwargs = {name: _decode(item) for name, item in data.items()
                      if name not in ("provenance", "information_provenance_enforcement")}
            return cls(**kwargs, provenance=bundle, information_provenance_enforcement=checkpoint)
        elif cls is V1InformationProvenanceSerializationCheckpoint and execution_bundle is not None:
            wire, bundle = execution_bundle
            if not _same_wire(wire, data["provenance"]):
                # A miss only precludes sharing. Preserve this representation
                # and let the original execution/checkpoint checks reconcile it.
                bundle = _decode(data["provenance"])
            kwargs = {name: bundle if name == "provenance" else _decode(item)
                      for name, item in data.items()}
        else:
            kwargs = {name: _decode(item) for name, item in data.items()}
        if cls in (PositionAnalysisApplicationOptions, HistoricalGameApplicationOptions):
            supplied = value.get("supplied")
            if (type(supplied) is not list or any(type(name) is not str for name in supplied)
                    or len(set(supplied)) != len(supplied) or set(supplied) - set(kwargs)):
                raise ValueError("Invalid original option presence.")
            ordered = (*supplied, *(name for name in kwargs if name not in supplied))
            kwargs["_replace_state"] = (
                tuple(supplied), tuple((name, kwargs[name]) for name in ordered))
        if cls is MatchAnalysisReportV1:
            kwargs.pop("report_id")  # Constructor recomputes it; exact re-encoding checks it.
        result = cls(**kwargs)
    return result


def _roundtrip_wire(result):
    if type(result) is ApplicationExecutionResult:
        checkpoint = result.information_provenance_enforcement
        if checkpoint is not None and result.provenance is checkpoint.provenance:
            # Emit every field in both positions. Only the in-memory encoding of
            # this exact, already reconstructed immutable bundle need be built once.
            bundle_wire = encode_execution_value(result.provenance)

            def encode_field(field):
                return bundle_wire if field is result.provenance else encode_execution_value(field)

            checkpoint_wire = _record_wire(checkpoint, encode_field)
            return _record_wire(result, lambda field:
                checkpoint_wire if field is checkpoint else encode_field(field))
    return encode_execution_value(result)


def decode_execution_value(value):
    result = _decode(value)
    if canonical_json(_roundtrip_wire(result)) != canonical_json(value):
        raise ValueError("Retained Application value changed during typed reconstruction.")
    return result


def _decode_execution_bytes(raw: bytes):
    wire, canonical = _decode_json_and_canonical_bytes(raw)
    result = _decode(wire)
    del wire  # Only its locally computed canonical bytes are needed for the roundtrip.
    if canonical_json(_roundtrip_wire(result)) != canonical:
        raise ValueError("Retained Application value changed during typed reconstruction.")
    return result


def validate_execution(invocation, execution, *, workflow=WorkflowV1.POSITION_ANALYSIS):
    if type(invocation) is not ApplicationInvocation or type(execution) is not (
            ApplicationExecutionResult):
        raise ValueError("Expected an original Application invocation and execution.")
    if invocation.request.workflow is not workflow or execution.result.workflow is not workflow:
        raise ValueError("The retained execution workflow disagrees.")
    validate_v1_information_provenance_serialization_checkpoint(execution)
    validate_v1_information_provenance_sources(
        invocation, execution.information_provenance_enforcement.sources)
    checkpoint = execution.information_provenance_enforcement
    linkage = validate_v1_retained_stage_linkage(invocation, checkpoint.sources,
        execution.provenance, trusted_checkpoint_documents=checkpoint.trusted_checkpoint_documents)
    if linkage.linked_attachment_names != checkpoint.linked_attachment_names:
        raise ValueError("Retained execution provenance linkage disagrees.")
