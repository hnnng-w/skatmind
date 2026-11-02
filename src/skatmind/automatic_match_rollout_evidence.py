"""Private codec-2 Match rollout admission, separate from ordinary Teacher evidence."""

from dataclasses import dataclass

from . import __version__
from .api.v1.schema_validation import validate_output_document
from .application.execution import build_application_invocation
from .automatic_learning_codec import canonical_json, decode_json
from .automatic_learning_contracts import EvidenceEntryV1
from .automatic_learning_objects import StoredObjectV1
from .automatic_match_evidence import (
    MATCH_ARCHIVE_CODEC,
    MatchCaptureCandidate,
    RetainedMatchDecision,
    UnsupportedMatchEvidence,
    _download_record,
    _fields,
    _situation,
    build_managed_match_source,
    decode_match_source,
)
from .automatic_match_execution_codec import (
    decode_execution_value,
    encode_execution_value,
    validate_execution,
)
from .match_analysis_contracts import (
    MatchAnalysisReportV1,
    MatchDecisionAnalysisResultV1,
    _validate_match_analysis_report_identity_v1,
)
from .match_analysis_exports import (
    build_match_report_result_export_v1,
    build_match_rollout_request_export_v1,
)
from .match_debrief import MatchDebriefEvidenceV1, _reconcile, completed_rollout
from .match_decision_analysis import build_match_decision_position_request_v1
from .match_rollout_review import validate_match_rollout_report_v1
from .rollout_derivation import rollout_source_fingerprint


def _metadata():
    return {"version": 1, "producer": "managed_match_rollout", "producer_contract": 1,
            "package_version": __version__}


@dataclass(frozen=True, slots=True)
class RetainedMatchRollout(RetainedMatchDecision):
    comparison: MatchDebriefEvidenceV1 | None


def _admit(report, source):
    if (type(report) is not MatchAnalysisReportV1
            or type(report.value) is not MatchDecisionAnalysisResultV1
            or report.value.status != "executed"
            or report.value.options.recommendation_method != "whole_game_rollout"):
        raise ValueError("Only an executed selected Match rollout can be retained.")
    _validate_match_analysis_report_identity_v1(report, legacy_identity=False)
    validate_match_rollout_report_v1(report.value)
    root = report.value.request.to_dict()["document"]
    result = report.value.result.to_dict()["document"]
    validate_output_document(result)
    if completed_rollout(report):
        comparison = MatchDebriefEvidenceV1(report, source.snapshot, source.snapshot)
    else:
        # Same original-source admission, without weakening the complete-only debrief.
        if result["whole_game_rollout_result"]["status"] not in (
                "unavailable", "partial", "timeout", "cancelled"):
            raise ValueError("Unsupported executed rollout availability.")
        if root["whole_game_rollout_derivation"]["workspace_content_fingerprint"] != (
                source.snapshot.source_content_fingerprint):
            raise ValueError("Rollout availability changed its original source.")
        _reconcile(report, source.snapshot)
        comparison = None
    from .input_loader import build_local_game_state_from_input
    from .rules import get_legal_cards

    state = build_local_game_state_from_input(root)
    if (result["settings"]["whole_game_rollout_settings"] != root["whole_game_rollout_settings"]
            or result["settings"]["recommendation_method"] != "whole_game_rollout"
            or result["profile_preset_settings"]["use_profile_presets"]
            or result["legal_cards"] != get_legal_cards(state.hand, state.current_trick,
                                                       state.game_type)):
        raise ValueError("Rollout settings or legal candidates disagree.")
    value = report.value.to_dict()
    value["result"]["document"]["whole_game_rollout_result"]["work"].pop("elapsed_ms")
    semantic = rollout_source_fingerprint("skatmind.match_debrief.semantic.v1", value)
    return comparison, semantic


def _downloads(report):
    return tuple((kind, artifact.filename, artifact.to_bytes()) for kind, artifact in (
        ("result", build_match_report_result_export_v1(report)),
        ("request", build_match_rollout_request_export_v1(report))))


def build_match_rollout_capture_candidate(document, report, invocation, execution):
    """Original producer values only; strict admission precedes any store initialization."""
    obj, record, snapshot = build_managed_match_source(document)
    source = decode_match_source(obj, record)
    _, semantic = _admit(report, source)
    situation = _situation(record, report)
    envelope = StoredObjectV1(area="reports", kind="match_rollout",
        codec_version=MATCH_ARCHIVE_CODEC, dependencies=(obj.reference,),
        payload=canonical_json({**_metadata(), "original_source": record.to_dict(),
            "snapshot_id": snapshot.match_snapshot_id, "situation": situation.to_dict(),
            "report": encode_execution_value(report),
            "invocation": encode_execution_value(invocation),
            "execution": encode_execution_value(execution),
            "downloads": [_download_record(*row) for row in _downloads(report)]}))
    entry = EvidenceEntryV1(evidence_class="rollout",
        source_version_id=record.source_version.identity, envelope=envelope.reference,
        situation=situation, semantic_fingerprint=semantic)
    decode_match_rollout(envelope, entry, source)
    return MatchCaptureCandidate(record, entry, (obj, envelope))


def decode_match_rollout(obj, entry, source):
    if (obj.kind, obj.codec_version) != ("match_rollout", MATCH_ARCHIVE_CODEC):
        raise UnsupportedMatchEvidence("Unsupported Match rollout codec.")
    data = decode_json(obj.payload)
    if (type(data.get("version")) is not int or data["version"] != 1
            or data.get("producer") != "managed_match_rollout"
            or type(data.get("producer_contract")) is not int or data["producer_contract"] != 1
            or data.get("package_version") not in ("0.17.0",)):
        raise UnsupportedMatchEvidence("Unsupported Match rollout producer.")
    _fields(data, (*_metadata(), "original_source", "snapshot_id", "situation", "report",
                   "invocation", "execution", "downloads"))
    if (obj.reference != entry.envelope or obj.dependencies != (source.record.object_ref,)
            or data["original_source"] != source.record.to_dict()
            or data["snapshot_id"] != source.snapshot.match_snapshot_id):
        raise ValueError("Rollout changed its original whole-Workspace binding.")
    report = decode_execution_value(data["report"])
    comparison, semantic = _admit(report, source)
    expected = EvidenceEntryV1(evidence_class="rollout",
        source_version_id=source.record.source_version.identity, envelope=obj.reference,
        situation=_situation(source.record, report), semantic_fingerprint=semantic)
    if entry != expected or data["situation"] != expected.situation.to_dict():
        raise ValueError("Rollout situation or semantic identity disagrees.")
    invocation = decode_execution_value(data["invocation"])
    execution = decode_execution_value(data["execution"])
    validate_execution(invocation, execution)
    prepared = build_match_decision_position_request_v1(source.document.workspace,
        match_position=report.match_position, decision_index=report.decision_index,
        options=report.value.options)
    rebuilt = build_application_invocation(prepared.request.to_dict()["document"],
        input_reference=prepared.input_reference, options=prepared.application_options,
        external_documents=prepared.external_documents)
    if (encode_execution_value(invocation) != encode_execution_value(rebuilt)
            or encode_execution_value(execution.result) != (
                encode_execution_value(report.value.result))
            or encode_execution_value(invocation.request) != (
                encode_execution_value(report.value.request))
            or prepared.profile_binding != report.value.profile_binding):
        raise ValueError("Rollout invocation, execution or original source disagrees.")
    downloads = _downloads(report)
    if data["downloads"] != [_download_record(*row) for row in downloads]:
        raise ValueError("Rollout native export bytes or digests disagree.")
    return RetainedMatchRollout(entry, source, report, invocation, execution, downloads, comparison)
