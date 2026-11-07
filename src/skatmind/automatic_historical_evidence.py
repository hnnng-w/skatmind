"""Native Historical sources and genuine executions; admission never evaluates cards."""

from dataclasses import asdict, dataclass, replace

from . import __version__
from .api.v1 import RequestDocumentV1, WorkflowV1
from .api.v1.contracts import _restore_execution_options_v1
from .api.v1.execution import _translate_workflow_options, _validated_external_documents
from .api.v1.schema_validation import validate_input_document, validate_output_document
from .automatic_historical_codec import pack_native, unpack_native
from .automatic_learning_codec import canonical_json, decode_json, fingerprint, integer, text
from .automatic_learning_contracts import (
    EvidenceEntryV1,
    IdentityScopeV1,
    SourceKeyV1,
    SourceRecordV1,
    SourceVersionV1,
)
from .automatic_learning_objects import StoredObjectV1
from .automatic_match_evidence import UnsupportedMatchEvidence, _download_record, _fields
from .automatic_match_execution_codec import (
    decode_execution_value,
    encode_execution_value,
    validate_execution,
)
from .automatic_session_evidence import SessionCaptureCandidate, _public_result
from .historical_game import build_historical_game_record, build_serializable_historical_record
from .v1_information_provenance_sources import V1InformationProvenanceSourceMetadata


def _metadata():
    return {"version": 1, "producer": "native_historical_review", "producer_contract": 1,
            "package_version": __version__}


def _payload(obj, kind):
    if (obj.kind, obj.codec_version) != (kind, 2):
        raise UnsupportedMatchEvidence("Unsupported Historical archive codec.")
    data = decode_json(obj.payload)
    if (type(data.get("version")) is not int or data["version"] != 1
            or data.get("producer") != "native_historical_review"
            or type(data.get("producer_contract")) is not int or data["producer_contract"] != 1
            or data.get("package_version") not in ("0.17.0",)):
        raise UnsupportedMatchEvidence("Unsupported Historical producer.")
    return data


def draft_wire(draft):
    return None if draft is None else encode_execution_value(asdict(draft))


def resume_guided_draft(wire):
    from .app_web.historical_form import (
        HistoricalFormDeclarationV1,
        HistoricalFormDraftV1,
        HistoricalFormOptionsV1,
        HistoricalFormPlayerV1,
        HistoricalFormPlayV1,
    )
    data = decode_execution_value(wire)
    draft = HistoricalFormDraftV1(**{**data,
        "players": tuple(HistoricalFormPlayerV1(**row) for row in data["players"]),
        "declaration": HistoricalFormDeclarationV1(**data["declaration"]),
        "plays": tuple(HistoricalFormPlayV1(**row) for row in data["plays"]),
        "options": HistoricalFormOptionsV1(**data["options"])})
    if draft.step != 7 or draft_wire(draft) != wire:
        raise ValueError("Guided source must retain its completed producer draft.")
    return draft


def canonical_game(request):
    if type(request) is not RequestDocumentV1 or request.workflow is not WorkflowV1.HISTORICAL_GAME:
        raise ValueError("A saved Historical source requires a Historical Request.")
    root = request.to_dict()["document"]
    validate_input_document(root)
    # End adjudication belongs to the original execution. Resume validates the
    # typed input and chronological legal prefix, without rerunning Claim proofs.
    game = build_historical_game_record(root["historical_game_input"],
                                        validate_game_event_chain=False)
    from .historical_play_prefix import replay_historical_play_prefix
    replay = replay_historical_play_prefix(game)
    if game.game_events:
        from .historical_game_event import build_historical_game_event_chain_context
        build_historical_game_event_chain_context(game, final_replay=replay)
    return game


@dataclass(frozen=True, slots=True)
class OriginalHistoricalSource:
    record: SourceRecordV1
    request: object
    game: object
    origin: str
    draft: object

    @property
    def name(self):
        return " / ".join(player.player_label or player.player_id for player in self.game.players)


@dataclass(frozen=True, slots=True)
class RetainedHistoricalExecution:
    entry: EvidenceEntryV1
    source: object
    game: object
    execution: object
    invocation: object
    internal_execution: object
    downloads: tuple
    report: object = None
    guided_draft: object = None

    def download(self, kind):
        for name, filename, raw in self.downloads:
            if name == kind:
                return filename, raw
        raise KeyError("Unknown Historical download.")


def build_historical_source(source_id, revision, request, *, draft=None):
    text(source_id)
    integer(revision)
    game = canonical_game(request)
    origin = "guided" if draft is not None else "imported"
    if draft is not None:
        from .app_web.historical_form import HistoricalFormOptionsV1, build_historical_request_v1
        draft = resume_guided_draft(draft_wire(draft))
        if build_historical_request_v1(draft) != request:
            raise ValueError("Guided producer and executed Request disagree.")
        # Execution choices do not create another recorded Game version. Retain
        # their exact original producer draft in the execution envelope instead.
        draft = replace(draft, options=HistoricalFormOptionsV1())
    key = SourceKeyV1(family="historical_review", product_id=source_id)
    scope = IdentityScopeV1(kind="source_local" if draft is not None else "shared_claim",
        namespace=key.identity if draft is not None else "historical_input_v1")
    content = {"source": key.to_dict(), "revision": revision, "origin": origin,
        "scope": scope.to_dict(), "request": encode_execution_value(request),
        "game": build_serializable_historical_record(game), "draft": draft_wire(draft)}
    obj = StoredObjectV1(area="sources", kind="historical_source", codec_version=2,
                        payload=canonical_json({**_metadata(), **content}))
    record = SourceRecordV1(source_version=SourceVersionV1(source=key,
        source_contract="saved_historical_review", contract_version=1,
        content_fingerprint=fingerprint("historical_source_v1", content)),
        object_ref=obj.reference, scope=scope, revision=revision)
    return obj, record, OriginalHistoricalSource(record, request, game, origin, draft)


def decode_historical_source(obj, record):
    data = _payload(obj, "historical_source")
    _fields(data, (*_metadata(), "source", "revision", "origin", "scope", "request",
                   "game", "draft"))
    if data["origin"] not in ("guided", "imported") or (
            (data["draft"] is not None) != (data["origin"] == "guided")):
        raise ValueError("Historical producer origin is contradictory.")
    rebuilt = build_historical_source(record.source_version.source.product_id, data["revision"],
        decode_execution_value(data["request"]), draft=None if data["draft"] is None else
        resume_guided_draft(data["draft"]))
    if rebuilt[0] != obj or rebuilt[1] != record:
        raise ValueError("Historical source identity, scope or canonical Game disagrees.")
    return rebuilt[2]


def _native_downloads(execution):
    return (("request", "skatmind-review-request.json", execution.request_json_bytes),
            ("result", "skatmind-review-result.json", execution.result_json_bytes))


def build_historical_capture_candidate(source_id, revision, execution, native, *, draft=None):
    invocation, internal, public = native
    if public is not execution.result:
        raise ValueError("Historical observation belongs to another execution.")
    obj, record, source = build_historical_source(
        source_id, revision, execution.request, draft=draft)
    envelope = StoredObjectV1(area="reports", kind="historical_review", codec_version=2,
        dependencies=(obj.reference,), payload=canonical_json({**_metadata(),
            "original_source": record.to_dict(),
            "guided_draft": draft_wire(draft),
            "options": encode_execution_value(execution.options.to_dict()),
            "supplied_options": list(execution.options._provenance_supplied_option_names),
            "result": pack_native(execution.result.to_dict()),
            "invocation": pack_native(invocation),
            "internal_execution": pack_native(internal),
            "downloads": [_download_record(*row) for row in _native_downloads(execution)]}))
    entry = EvidenceEntryV1(evidence_class="historical",
                           source_version_id=record.source_version.identity,
                           envelope=envelope.reference, situation=None)
    decode_historical_execution(envelope, entry, source)
    return SessionCaptureCandidate(record, entry, (obj, envelope))


def decode_historical_execution(obj, entry, source):
    from .app_web.execution import REVIEW_INPUT_REFERENCE, GuidedFrontendExecutionV1
    from .app_web.historical_form import build_historical_execution_options_v1
    from .app_web.json_transfer import canonical_frontend_json_bytes_v1
    from .automatic_historical_validation import validate_historical_execution

    data = _payload(obj, "historical_review")
    _fields(data, (*_metadata(), "original_source", "guided_draft", "options",
                   "supplied_options", "result",
                   "invocation", "internal_execution", "downloads"))
    _require_original(obj, entry, source, data)
    supplied = data["supplied_options"]
    if type(supplied) is not list or any(type(name) is not str for name in supplied):
        raise ValueError("Invalid Historical option presence.")
    options_data = decode_execution_value(data["options"])
    options = _restore_execution_options_v1(options_data, tuple(supplied))
    if (encode_execution_value(options.to_dict()) != encode_execution_value(options_data)
            or len(set(supplied)) != len(supplied)
            or list(options._provenance_supplied_option_names) != supplied
            or set(supplied) - set(options_data) or not options.validate_output):
        raise ValueError("Historical option presence disagrees.")
    guided = None if data["guided_draft"] is None else resume_guided_draft(data["guided_draft"])
    if (guided is not None) != (source.origin == "guided"):
        raise ValueError("Historical execution changed its guided origin.")
    if guided is not None:
        if build_historical_source(source.record.source_version.source.product_id,
                source.record.revision, source.request, draft=guided)[1] != source.record:
            raise ValueError("Executed guided draft changed its source input.")
        expected = build_historical_execution_options_v1(guided)
        if (expected != options or expected._provenance_supplied_option_names != tuple(supplied)):
            raise ValueError("Guided options disagree with their retained producer.")
    invocation = unpack_native(data["invocation"])
    internal = unpack_native(data["internal_execution"])
    validate_execution(invocation, internal, workflow=WorkflowV1.HISTORICAL_GAME)
    metadata = V1InformationProvenanceSourceMetadata(application_options_supplied=True,
        supplied_execution_option_names=tuple(supplied),
        supplied_workflow_option_names=tuple(options.workflow_options),
        validate_output=options.validate_output,
        validate_output_supplied="validate_output" in supplied,
        include_provenance=options.include_provenance,
        include_provenance_supplied="include_provenance" in supplied)
    if (invocation.request != source.request or invocation.input_reference != REVIEW_INPUT_REFERENCE
            or invocation.provenance_source_metadata != metadata
            or encode_execution_value(invocation.options) != encode_execution_value(
                _translate_workflow_options(source.request.workflow, options.workflow_options))
            or invocation.external_documents != _validated_external_documents(options)):
        raise ValueError("Historical invocation, external context or option provenance disagrees.")
    validate_historical_execution(source.game, invocation, internal)
    public = _public_result(internal, options)
    if encode_execution_value(public.to_dict()) != encode_execution_value(
            unpack_native(data["result"])):
        raise ValueError("Historical native Result disagrees with the retained execution.")
    validate_output_document(public.result.to_dict()["document"])
    execution = GuidedFrontendExecutionV1(request=source.request, options=options, result=public,
        request_json_bytes=canonical_frontend_json_bytes_v1(source.request.to_dict()["document"]),
        result_json_bytes=canonical_frontend_json_bytes_v1(public.to_dict()))
    downloads = _native_downloads(execution)
    if data["downloads"] != [_download_record(*row) for row in downloads]:
        raise ValueError("Original Historical download bytes disagree.")
    return RetainedHistoricalExecution(entry, source, source.game, execution, invocation,
                                       internal, downloads, guided_draft=guided)


def _require_original(obj, entry, source, data):
    if (entry.evidence_class != "historical" or entry.situation is not None
            or entry.semantic_fingerprint is not None or obj.reference != entry.envelope
            or entry.source_version_id != source.record.source_version.identity
            or obj.dependencies != (source.record.object_ref,)
            or data["original_source"] != source.record.to_dict()):
        raise ValueError("Historical execution changed its exact original source.")
