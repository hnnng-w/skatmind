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
    PositionAnalysisApplicationOptions,
)
from .application.provenance import ApplicationProvenanceAttachment, ApplicationProvenanceBundle
from .automatic_learning_codec import canonical_json
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
    ApplicationProvenanceBundle,
    FieldProvenanceEntry, FieldProvenanceExemption, FieldProvenanceLedger,
    FieldProvenanceSourceReference, FieldProvenanceCoverageSummary, InformationUseContext,
    V1InformationProvenanceArtifactCheckpoint, V1InformationProvenanceSerializationCheckpoint,
    V1InformationProvenanceSourceBinding, V1InformationProvenanceSourceMetadata,
    V1InformationProvenanceSources,
    MatchAnalysisReportV1, MatchDecisionAnalysisOptionsV1, MatchDecisionAnalysisResultV1,
    MatchDecisionOpponentProfileBindingV1, WholeGameRolloutSettingsV1,
)}


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
    result = {"type": type(value).__name__, "value": {
        item.name: encode_execution_value(getattr(value, item.name)) for item in fields(value)}}
    if type(value) is PositionAnalysisApplicationOptions:
        result["supplied"] = list(value._provenance_supplied_option_names)
    return result


def _decode(value):
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
        kwargs = {name: _decode(item) for name, item in data.items()}
        if cls is PositionAnalysisApplicationOptions:
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


def decode_execution_value(value):
    result = _decode(value)
    if canonical_json(encode_execution_value(result)) != canonical_json(value):
        raise ValueError("Retained Application value changed during typed reconstruction.")
    return result


def validate_execution(invocation, execution):
    if type(invocation) is not ApplicationInvocation or type(execution) is not (
            ApplicationExecutionResult):
        raise ValueError("Expected an original Application invocation and execution.")
    if invocation.request.workflow is not WorkflowV1.POSITION_ANALYSIS:
        raise ValueError("Only ordinary Position execution is supported.")
    validate_v1_information_provenance_serialization_checkpoint(execution)
    validate_v1_information_provenance_sources(
        invocation, execution.information_provenance_enforcement.sources)
    checkpoint = execution.information_provenance_enforcement
    linkage = validate_v1_retained_stage_linkage(invocation, checkpoint.sources,
        execution.provenance, trusted_checkpoint_documents=checkpoint.trusted_checkpoint_documents)
    if linkage.linked_attachment_names != checkpoint.linked_attachment_names:
        raise ValueError("Retained execution provenance linkage disagrees.")
