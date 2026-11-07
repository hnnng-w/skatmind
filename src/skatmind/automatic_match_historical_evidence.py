"""Managed Match Historical evidence retains its original Workspace and materialization."""

from .api.v1 import WorkflowV1
from .application.contracts import ApplicationExecutionOptions
from .application.execution import build_application_invocation
from .automatic_historical_codec import pack_native, unpack_native
from .automatic_historical_evidence import (
    RetainedHistoricalExecution,
    _metadata,
    _payload,
    _require_original,
    canonical_game,
)
from .automatic_historical_validation import validate_historical_execution
from .automatic_learning_codec import canonical_json
from .automatic_learning_contracts import EvidenceEntryV1
from .automatic_learning_objects import StoredObjectV1
from .automatic_match_evidence import (
    _download_record,
    _fields,
    build_managed_match_source,
    decode_match_source,
)
from .automatic_match_execution_codec import (
    encode_execution_value,
    validate_execution,
)
from .automatic_session_evidence import SessionCaptureCandidate
from .historical_game import build_serializable_historical_record
from .match_analysis_exports import build_match_report_result_export_v1
from .match_historical_analysis import _build_historical_external_documents
from .match_historical_information_set_analysis import build_match_historical_application_options_v1
from .match_historical_materialization import materialize_match_observed_game_historical_v1
from .match_player_statistics_preparation import build_match_player_statistics_preparation_v1


def _downloads(report):
    from .app_web.json_transfer import canonical_frontend_json_bytes_v1
    artifact = build_match_report_result_export_v1(report)
    return (("request", artifact.filename.removesuffix(".json") + "-request.json",
             canonical_frontend_json_bytes_v1(report.value.request.to_dict()["document"])),
            ("result", artifact.filename, artifact.to_bytes()))


def build_match_historical_capture_candidate(document, report, invocation, execution):
    obj, record, _snapshot = build_managed_match_source(document)
    source = decode_match_source(obj, record)
    envelope = StoredObjectV1(area="reports", kind="match_historical", codec_version=2,
        dependencies=(obj.reference,), payload=canonical_json({**_metadata(),
            "original_source": record.to_dict(), "report": pack_native(report),
            "invocation": pack_native(invocation),
            "internal_execution": pack_native(execution),
            "downloads": [_download_record(*row) for row in _downloads(report)]}))
    entry = EvidenceEntryV1(evidence_class="historical",
                           source_version_id=record.source_version.identity,
                           envelope=envelope.reference, situation=None)
    decode_match_historical_execution(envelope, entry, source)
    return SessionCaptureCandidate(record, entry, (obj, envelope))


def decode_match_historical_execution(obj, entry, source):
    from .api.v1.schema_validation import validate_output_document
    from .match_analysis_contracts import MatchHistoricalAnalysisResultV1
    data = _payload(obj, "match_historical")
    _fields(data, (*_metadata(), "original_source", "report", "invocation", "internal_execution",
                   "downloads"))
    _require_original(obj, entry, source, data)
    report = unpack_native(data["report"])
    value, workspace = report.value, source.document.workspace
    if (type(value) is not MatchHistoricalAnalysisResultV1 or value.status != "executed"
            or report.match_id != workspace.match_definition.match_id
            or report.workspace_revision != workspace.revision):
        raise ValueError("Match Historical Report changed its source identity.")
    materialized = materialize_match_observed_game_historical_v1(
        workspace, match_position=report.match_position)
    root = {"historical_game_input": build_serializable_historical_record(
        materialized.historical_game)}
    if value.request.to_dict()["document"] != root or value.game_id != materialized.game_id:
        raise ValueError("Match Historical Request changed its exact materialization.")
    statistics = build_match_player_statistics_preparation_v1(workspace.match_definition)
    external = _build_historical_external_documents(workspace, statistics, value.options)
    expected = build_application_invocation(root,
        input_reference=f"match:{report.match_id}:workspace:{workspace.revision}:"
                        f"position:{report.match_position}:historical",
        options=ApplicationExecutionOptions(historical_game=build_match_historical_application_options_v1(
            value.options, inject_statistics=external.opponent_statistics_document is not None)),
        external_documents=external)
    invocation = unpack_native(data["invocation"])
    internal = unpack_native(data["internal_execution"])
    if encode_execution_value(invocation) != encode_execution_value(expected):
        raise ValueError("Match Historical invocation changed options or external context.")
    validate_execution(invocation, internal, workflow=WorkflowV1.HISTORICAL_GAME)
    game = canonical_game(value.request)
    validate_historical_execution(game, invocation, internal)
    if internal.result != value.result:
        raise ValueError("Match Historical Report changed its original Result.")
    validate_output_document(value.result.to_dict()["document"])
    downloads = _downloads(report)
    if data["downloads"] != [_download_record(*row) for row in downloads]:
        raise ValueError("Match Historical native exports disagree.")
    return RetainedHistoricalExecution(entry, source, game, None, invocation, internal,
                                       downloads, report)
