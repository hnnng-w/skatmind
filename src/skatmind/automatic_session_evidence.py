"""Session-native original-source and execution admission. No Match Report adapter."""

from dataclasses import dataclass

from . import __version__
from .api.v1 import ExecutionArtifactV1, ExecutionResultV1, ResultDocumentV1
from .api.v1.contracts import _restore_execution_options_v1
from .api.v1.execution import _translate_workflow_options, _validated_external_documents
from .api.v1.schema_validation import validate_output_document
from .automatic_learning_codec import canonical_json, decode_json, fingerprint
from .automatic_learning_contracts import (
    EvidenceEntryV1,
    IdentityScopeV1,
    SituationV1,
    SourceKeyV1,
    SourceRecordV1,
    SourceVersionV1,
)
from .automatic_learning_objects import StoredObjectV1
from .automatic_match_evidence import (
    UnsupportedMatchEvidence,
    _download_record,
    _fields,
)
from .automatic_match_execution_codec import (
    decode_execution_value,
    encode_execution_value,
    validate_execution,
)
from .session_checkpoint_review import export_session_checkpoint_review_request_v1
from .session_persistence_codec import resume_session_document_v1
from .session_recorded_coverage import project_saved_session_coverage
from .session_rollout_review import derive_session_rollout_review_request_v1
from .v1_information_provenance_sources import V1InformationProvenanceSourceMetadata


def _metadata():
    return {"version": 1, "producer": "managed_session_recorded_review",
            "producer_contract": 1, "package_version": __version__}


def _payload(obj, kind):
    if (obj.kind, obj.codec_version) != (kind, 2):
        raise UnsupportedMatchEvidence("Unsupported native Session archive codec.")
    data = decode_json(obj.payload)
    if (type(data.get("version")) is not int or data["version"] != 1
            or data.get("producer") != "managed_session_recorded_review"
            or type(data.get("producer_contract")) is not int or data["producer_contract"] != 1
            or data.get("package_version") not in ("0.17.0",)):
        raise UnsupportedMatchEvidence("Unsupported native Session producer.")
    return data


@dataclass(frozen=True, slots=True)
class OriginalSessionSource:
    record: SourceRecordV1
    document: object
    coverage: object


@dataclass(frozen=True, slots=True)
class RetainedSessionExecution:
    entry: EvidenceEntryV1
    source: OriginalSessionSource
    checkpoint: object
    observation: object
    review_export: object
    execution: object
    invocation: object
    internal_execution: object
    downloads: tuple

    def download(self, kind):
        for name, filename, raw in self.downloads:
            if kind == name:
                return filename, raw
        raise KeyError("Unknown retained Session download.")


@dataclass(frozen=True, slots=True)
class SessionCaptureCandidate:
    source: SourceRecordV1
    evidence: EvidenceEntryV1
    objects: tuple


def _record(document, reference):
    key = SourceKeyV1(family="session", product_id=document.state.session_id)
    return SourceRecordV1(source_version=SourceVersionV1(source=key,
        source_contract=document.document_kind,
        contract_version=document.session_persistence_version,
        content_fingerprint=document.content_fingerprint), object_ref=reference,
        scope=IdentityScopeV1(kind="source_local", namespace=key.identity),
        revision=document.state.revision)


def build_managed_session_source(document):
    document = resume_session_document_v1(document.to_dict()).document
    obj = StoredObjectV1(area="sources", kind="session_source", codec_version=2,
        payload=canonical_json({**_metadata(), "document": document.to_dict()}))
    record = _record(document, obj.reference)
    return obj, record, OriginalSessionSource(record, document,
                                              project_saved_session_coverage(document))


def decode_session_source(obj, record):
    data = _payload(obj, "session_source")
    _fields(data, (*_metadata(), "document"))
    document = resume_session_document_v1(data["document"]).document
    if obj.dependencies or _record(document, obj.reference) != record:
        raise ValueError("Original complete Session binding disagrees.")
    return OriginalSessionSource(record, document, project_saved_session_coverage(document))


def _situation(source, checkpoint, observation):
    return SituationV1(source_version_id=source.record.source_version.identity,
        game_id=source.coverage.game_id, decision_index=checkpoint.decision_index,
        actor_id=checkpoint.acting_player_id, observed_card=observation.actual_card,
        information_cutoff=checkpoint.decision_index - 1,
        checkpoint_fingerprint=fingerprint("session_checkpoint_v1", checkpoint.to_dict()),
        accepted_play_fingerprint=fingerprint("session_observation_v1", observation.to_dict()))


def _public_result(internal, options):
    result, provenance = internal.result, None
    if options.include_provenance:
        from .public_field_provenance import attach_public_field_provenance
        document, provenance = attach_public_field_provenance(internal)
        result = ResultDocumentV1(workflow=result.workflow, document=document,
                                  warnings=result.warnings)
    return ExecutionResultV1(result=result, artifacts=tuple(ExecutionArtifactV1(
        name=artifact.name, document=artifact.to_dict()) for artifact in internal.artifacts),
        field_provenance=provenance)


def _downloads(execution, rollout):
    prefix = "skatmind-session-" + ("rollout-" if rollout else "")
    return (("request", prefix + "request.json", execution.request_json_bytes),
            ("result", prefix + "result.json", execution.result_json_bytes))


def _semantic(execution, situation):
    def without_elapsed(value):
        if type(value) is dict:
            return {key: without_elapsed(item) for key, item in value.items()
                    if key not in ("wall_clock_elapsed_ms", "elapsed_ms")}
        if type(value) is list:
            return [without_elapsed(item) for item in value]
        return value
    return fingerprint("session_execution_semantics_v1", {
        "situation": situation.to_dict(), "request": execution.request.to_dict(),
        "options": execution.options.to_dict(),
        "supplied_options": list(execution.options._provenance_supplied_option_names),
        "result": without_elapsed(execution.result.to_dict())})


def build_session_capture_candidate(document, checkpoint, observation, execution, native):
    """Native is the genuine tuple observed during this exact public execution."""
    invocation, internal, public = native
    if public is not execution.result:
        raise ValueError("The native observation belongs to another execution.")
    source_obj, record, source = build_managed_session_source(document)
    export = export_session_checkpoint_review_request_v1(
        state=document.state, checkpoint=checkpoint)
    rollout = "whole_game_rollout_derivation" in execution.request.document
    situation = _situation(source, checkpoint, observation)
    obj = StoredObjectV1(area="reports", kind="session_rollout" if rollout else "session_decision",
        codec_version=2, dependencies=(source_obj.reference,), payload=canonical_json({
            **_metadata(), "original_source": record.to_dict(),
            "checkpoint": checkpoint.to_dict(), "observation": observation.to_dict(),
            "review_export": export.to_dict(), "situation": situation.to_dict(),
            "request": encode_execution_value(execution.request),
            "options": encode_execution_value(execution.options.to_dict()),
            "supplied_options": list(execution.options._provenance_supplied_option_names),
            "result": encode_execution_value(execution.result.to_dict()),
            "invocation": encode_execution_value(invocation),
            "internal_execution": encode_execution_value(internal),
            "downloads": [_download_record(*row) for row in _downloads(execution, rollout)]}))
    entry = EvidenceEntryV1(evidence_class="rollout" if rollout else "decision",
        source_version_id=record.source_version.identity, envelope=obj.reference,
        situation=situation,
        semantic_fingerprint=_semantic(execution, situation))
    decode_session_execution(obj, entry, source)
    return SessionCaptureCandidate(record, entry, (source_obj, obj))


def decode_session_execution(obj, entry, source):
    from .app_web.execution import REVIEW_INPUT_REFERENCE, GuidedFrontendExecutionV1
    from .app_web.json_transfer import canonical_frontend_json_bytes_v1
    from .whole_game_rollout_workflow import parse_rollout_settings

    rollout = entry.evidence_class == "rollout"
    data = _payload(obj, "session_rollout" if rollout else "session_decision")
    _fields(data, (*_metadata(), "original_source", "checkpoint", "observation", "review_export",
                   "situation", "request", "options", "supplied_options", "result", "invocation",
                   "internal_execution", "downloads"))
    if (obj.reference != entry.envelope or obj.dependencies != (source.record.object_ref,)
            or data["original_source"] != source.record.to_dict()):
        raise ValueError("Session execution changed its original source dependency.")
    selected = next((row for row in source.coverage.decisions
                     if row[1].to_dict() == data["checkpoint"]), None)
    if selected is None:
        raise ValueError("Execution requires the selected eligible saved own Checkpoint.")
    _index, checkpoint, observation = selected
    exported = export_session_checkpoint_review_request_v1(
        state=source.document.state, checkpoint=checkpoint)
    situation = _situation(source, checkpoint, observation)
    if (exported.status != "available" or exported.to_dict() != data["review_export"]
            or observation.to_dict() != data["observation"] or situation != entry.situation
            or situation.to_dict() != data["situation"]):
        raise ValueError("Saved Checkpoint, accepted Play, export or cutoff disagrees.")
    request = decode_execution_value(data["request"])
    expected_request = exported.request
    if rollout:
        root = request.to_dict()["document"]
        settings = parse_rollout_settings(root["whole_game_rollout_settings"])
        derivation = root["whole_game_rollout_derivation"]
        expected_request = derive_session_rollout_review_request_v1(state=source.document.state,
            checkpoint=checkpoint, settings=settings, supplements=derivation.get("supplements"))
    if request != expected_request:
        raise ValueError("Retained Request changed the frozen decision-time information.")
    supplied = data["supplied_options"]
    if type(supplied) is not list or any(type(name) is not str for name in supplied):
        raise ValueError("Invalid supplied execution options.")
    options_data = decode_execution_value(data["options"])
    options = _restore_execution_options_v1(options_data, tuple(supplied))
    if (options.to_dict() != options_data
            or list(options._provenance_supplied_option_names) != supplied
            or len(supplied) != len(set(supplied)) or set(supplied) - set(options_data)
            or not options.validate_output):
        raise ValueError("Native execution option presence disagrees.")
    invocation = decode_execution_value(data["invocation"])
    internal = decode_execution_value(data["internal_execution"])
    validate_execution(invocation, internal)
    metadata = V1InformationProvenanceSourceMetadata(application_options_supplied=True,
        supplied_execution_option_names=tuple(supplied),
        supplied_workflow_option_names=tuple(options.workflow_options),
        validate_output=options.validate_output,
        validate_output_supplied="validate_output" in supplied,
        include_provenance=options.include_provenance,
        include_provenance_supplied="include_provenance" in supplied)
    if (invocation.request != request or invocation.input_reference != REVIEW_INPUT_REFERENCE
            or invocation.provenance_source_metadata != metadata
            or encode_execution_value(invocation.options) != encode_execution_value(
                _translate_workflow_options(request.workflow, options.workflow_options))
            or invocation.external_documents != _validated_external_documents(options)):
        raise ValueError("Native execution provenance or effective options disagree.")
    public = _public_result(internal, options)
    if encode_execution_value(public.to_dict()) != data["result"]:
        raise ValueError("Original native public Result disagrees with genuine execution.")
    validate_output_document(public.result.to_dict()["document"])
    if rollout:
        from .automatic_session_rollout_validation import validate_native_rollout
        validate_native_rollout(request.to_dict()["document"], public.result.to_dict()["document"])
    execution = GuidedFrontendExecutionV1(request=request, options=options, result=public,
        request_json_bytes=canonical_frontend_json_bytes_v1(request.to_dict()["document"]),
        result_json_bytes=canonical_frontend_json_bytes_v1(public.to_dict()))
    downloads = _downloads(execution, rollout)
    if entry.semantic_fingerprint != _semantic(execution, situation):
        raise ValueError("Native Session semantic identity disagrees.")
    if data["downloads"] != [_download_record(*row) for row in downloads]:
        raise ValueError("Exact native Session download bytes disagree.")
    return RetainedSessionExecution(entry, source, checkpoint, observation, exported,
                                     execution, invocation, internal, downloads)
