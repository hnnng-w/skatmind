"""Typed ordinary Match archive adapters. No evaluator, discovery or preparation.

Codec 2 deliberately does not reinterpret S1's opaque codec-1 storage fixtures.
The producer binding establishes consistency, not authenticated authorship.
"""

import base64
import hashlib
from dataclasses import dataclass, replace

from . import __version__
from .application.contracts import ApplicationExecutionResult, ApplicationInvocation
from .application.execution import build_application_invocation
from .automatic_learning_codec import canonical_json, decode_json
from .automatic_learning_contracts import (
    EvidenceEntryV1,
    IdentityScopeV1,
    SituationV1,
    SourceKeyV1,
    SourceRecordV1,
    SourceVersionV1,
)
from .automatic_learning_objects import StoredObjectV1
from .automatic_match_execution_codec import (
    decode_execution_value,
    encode_execution_value,
    validate_execution,
)
from .learning_corpus_match_snapshot import (
    LearningCorpusMatchSnapshotV1,
    build_learning_corpus_match_snapshot_v1,
)
from .learning_corpus_strategy_teacher_builder import validate_original_match_teacher_v1
from .match_analysis_contracts import (
    MatchAnalysisReportV1,
    _build_match_analysis_report_with_report_id_v1,
)
from .match_analysis_exports import (
    build_match_report_result_export_v1,
    canonical_match_artifact_json_bytes_v1,
)
from .match_analysis_report_source_codec import resume_match_analysis_report_source_export_v1
from .match_analysis_report_source_export import (
    LEGACY_MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND,
    MatchAnalysisReportSourceExportV1,
    build_match_analysis_report_source_export_v1,
    serialize_match_analysis_report_source_export_v1,
)
from .match_decision_analysis import build_match_decision_position_request_v1
from .match_workspace_persistence_codec import resume_match_workspace_document_v1
from .match_workspace_persistence_contracts import MatchWorkspacePersistenceDocumentV1

MATCH_ARCHIVE_CODEC = 2
ORDINARY_METHODS = (
    "immediate_expected_value", "bounded_search", "auto", "information_set_search",
)
_PRODUCER = "managed_match_decision"
_SUPPORTED_PACKAGES = ("0.17.0",)


class UnsupportedMatchEvidence(ValueError):
    """An intact stored contract has no compatible ordinary Match adapter."""


def _fields(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise ValueError("Invalid ordinary Match archive field set.")


def _header(data):
    if (type(data.get("version")) is not int or data["version"] != 1
            or data.get("producer") != _PRODUCER
            or type(data.get("producer_contract")) is not int or data["producer_contract"] != 1
            or data.get("package_version") not in _SUPPORTED_PACKAGES):
        raise UnsupportedMatchEvidence("Unsupported ordinary Match producer contract.")


def _metadata():
    return {"version": 1, "producer": _PRODUCER, "producer_contract": 1,
            "package_version": __version__}


@dataclass(frozen=True, slots=True)
class OriginalMatchSource:
    record: SourceRecordV1
    document: MatchWorkspacePersistenceDocumentV1
    snapshot: LearningCorpusMatchSnapshotV1


@dataclass(frozen=True, slots=True)
class RetainedMatchDecision:
    entry: EvidenceEntryV1
    source: OriginalMatchSource
    report: MatchAnalysisReportV1
    invocation: ApplicationInvocation
    execution: ApplicationExecutionResult
    downloads: tuple[tuple[str, str, bytes], ...]

    def download(self, kind):
        for name, filename, raw in self.downloads:
            if name == kind:
                return filename, raw
        raise KeyError("Unknown retained download.")


@dataclass(frozen=True, slots=True)
class MatchCaptureCandidate:
    source: SourceRecordV1
    evidence: EvidenceEntryV1
    objects: tuple[StoredObjectV1, ...]


def _source_record(document, reference):
    key = SourceKeyV1(family="match", product_id=document.workspace.match_definition.match_id)
    return SourceRecordV1(
        source_version=SourceVersionV1(source=key, source_contract=document.document_kind,
            contract_version=document.match_workspace_persistence_version,
            content_fingerprint=document.content_fingerprint),
        object_ref=reference, scope=IdentityScopeV1(kind="source_local", namespace=key.identity),
        revision=document.workspace.revision)


def build_managed_match_source(document):
    """Canonical shared S2/S3 source; preserve the historical codec-2 header/bytes."""
    snapshot = build_learning_corpus_match_snapshot_v1(document)
    obj = StoredObjectV1(area="sources", kind="match_source",
        codec_version=MATCH_ARCHIVE_CODEC, payload=canonical_json({**_metadata(),
            "document": document.to_dict(), "snapshot": snapshot.to_dict()}))
    return obj, _source_record(document, obj.reference), snapshot


def decode_match_source(obj, record):
    if (obj.kind, obj.codec_version) != ("match_source", MATCH_ARCHIVE_CODEC):
        raise UnsupportedMatchEvidence("Unsupported original Match source codec.")
    data = decode_json(obj.payload)
    _header(data)
    _fields(data, (*_metadata(), "document", "snapshot"))
    if obj.dependencies:
        raise ValueError("Original Match source cannot have dependencies.")
    document = resume_match_workspace_document_v1(data["document"]).document
    snapshot = build_learning_corpus_match_snapshot_v1(document)
    if (canonical_json(snapshot.to_dict()) != canonical_json(data["snapshot"])
            or _source_record(document, obj.reference) != record):
        raise ValueError("Original whole-Workspace binding disagrees.")
    return OriginalMatchSource(record, document, snapshot)


def _situation(source, report):
    value = report.value
    return SituationV1(source_version_id=source.source_version.identity,
        game_id=value.game_id, decision_index=report.decision_index,
        actor_id=value.profile_binding.acting_player_id,
        observed_card=value.request.document["actual_card_played"],
        information_cutoff=report.decision_index - 1)


def _download_record(kind, filename, raw):
    return {"kind": kind, "filename": filename,
            "bytes": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest()}


def build_match_capture_candidate(document, report, invocation, execution):
    """Called only with the original values from validated managed publication."""
    wrapper = build_match_analysis_report_source_export_v1(report)
    if report.value.options.recommendation_method not in ORDINARY_METHODS:
        raise ValueError("Only ordinary executed Match Decisions can be retained.")
    validate_execution(invocation, execution)
    source_object, source, snapshot = build_managed_match_source(document)
    teacher = validate_original_match_teacher_v1(report, snapshot)
    artifact = build_match_report_result_export_v1(report)
    stem = artifact.filename.removesuffix(".json")
    downloads = [
        _download_record("result", artifact.filename, artifact.to_bytes()),
        _download_record("strategy-source", stem + "-strategy-source.json",
            serialize_match_analysis_report_source_export_v1(wrapper)),
        _download_record("request", stem + "-request.json",
            canonical_match_artifact_json_bytes_v1(report.value.request.to_dict()["document"])),
    ]
    envelope = StoredObjectV1(area="reports", kind="match_decision",
        codec_version=MATCH_ARCHIVE_CODEC, dependencies=(source_object.reference,),
        payload=canonical_json({**_metadata(), "original_source": source.to_dict(),
            "snapshot_id": snapshot.match_snapshot_id,
            "situation": _situation(source, report).to_dict(),
            "report_source": wrapper.to_dict(),
            "invocation": encode_execution_value(invocation),
            "execution": encode_execution_value(execution), "downloads": downloads}))
    entry = EvidenceEntryV1(evidence_class="decision",
        source_version_id=source.source_version.identity, envelope=envelope.reference,
        situation=_situation(source, report),
        semantic_fingerprint=teacher.teacher_semantic_fingerprint)
    # Re-enter the same strict admission used after restart, without execution.
    decode_match_decision(envelope, entry, decode_match_source(source_object, source))
    return MatchCaptureCandidate(source, entry, (source_object, envelope))


def decode_match_decision(obj, entry, source):
    if (obj.kind, obj.codec_version) != ("match_decision", MATCH_ARCHIVE_CODEC):
        raise UnsupportedMatchEvidence("Unsupported ordinary Match evidence codec.")
    data = decode_json(obj.payload)
    _header(data)
    _fields(data, (*_metadata(), "original_source", "snapshot_id", "situation", "report_source",
                   "invocation", "execution", "downloads"))
    if (obj.reference != entry.envelope or obj.dependencies != (source.record.object_ref,)
            or data["original_source"] != source.record.to_dict()
            or data["snapshot_id"] != source.snapshot.match_snapshot_id):
        raise ValueError("Evidence changed its original whole-Workspace binding.")
    wrapper = resume_match_analysis_report_source_export_v1(data["report_source"])
    report = wrapper.report
    teacher = validate_original_match_teacher_v1(report, source.snapshot)
    expected = EvidenceEntryV1(evidence_class="decision",
        source_version_id=source.record.source_version.identity, envelope=obj.reference,
        situation=_situation(source.record, report),
        semantic_fingerprint=teacher.teacher_semantic_fingerprint)
    if entry != expected or data["situation"] != expected.situation.to_dict():
        raise ValueError("Evidence situation or semantic grouping disagrees.")
    invocation = decode_execution_value(data["invocation"])
    execution = decode_execution_value(data["execution"])
    validate_execution(invocation, execution)
    prepared = build_match_decision_position_request_v1(source.document.workspace,
        match_position=report.match_position, decision_index=report.decision_index,
        options=report.value.options)
    rebuilt = build_application_invocation(prepared.request.to_dict()["document"],
        input_reference=prepared.input_reference, options=prepared.application_options,
        external_documents=prepared.external_documents)
    if (canonical_json(encode_execution_value(invocation)) !=
            canonical_json(encode_execution_value(rebuilt))
            or execution.result != report.value.result
            or invocation.request != report.value.request):
        raise ValueError("Original execution, external inputs or effective options disagree.")
    downloads = data["downloads"]
    if type(downloads) is not list or len(downloads) != 3:
        raise ValueError("Retained downloads must be complete.")
    artifact = build_match_report_result_export_v1(report)
    stem = artifact.filename.removesuffix(".json")
    # The execution codec retains original mapping order, unlike the surrounding
    # sorted-key storage envelope. Restore that order without normalizing IDs.
    ordered_report = _build_match_analysis_report_with_report_id_v1(
        value=replace(report.value, request=invocation.request, result=execution.result),
        report_id=report.report_id,
        legacy_identity=wrapper.document_kind == LEGACY_MATCH_ANALYSIS_REPORT_SOURCE_DOCUMENT_KIND)
    ordered_wrapper = MatchAnalysisReportSourceExportV1(document_kind=wrapper.document_kind,
        report_id=report.report_id, report=ordered_report)
    expected_documents = (execution.result.to_dict()["document"], ordered_wrapper.to_dict(),
                          invocation.request.to_dict()["document"])
    result = []
    for row, kind, filename, document in zip(downloads,
            ("result", "strategy-source", "request"),
            (artifact.filename, stem + "-strategy-source.json", stem + "-request.json"),
            expected_documents, strict=True):
        _fields(row, ("kind", "filename", "bytes", "sha256"))
        if type(row["bytes"]) is not str:
            raise ValueError("Invalid retained bytes.")
        raw = base64.b64decode(row["bytes"], validate=True)
        # Decode the original bytes directly. In particular, never pass a legacy
        # source wrapper through the normalizing current-domain export serializer.
        parsed = decode_json(raw)
        if (row != _download_record(kind, filename, raw)
                or canonical_json(parsed) != canonical_json(document)
                or raw != canonical_match_artifact_json_bytes_v1(document)):
            raise ValueError("Retained download bytes disagree with their typed values.")
        result.append((kind, filename, raw))
    return RetainedMatchDecision(entry, source, report, invocation, execution, tuple(result))
