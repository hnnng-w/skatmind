# Public Session API version 1

## Contract identity

The stable in-memory Session namespace is `skatmind.api.v1.session`:

```text
PUBLIC_SESSION_API_VERSION = 1
PUBLIC_SESSION_API_NAMESPACE = skatmind.api.v1.session
PUBLIC_SESSION_API_COMPATIBILITY_POLICY = additive_until_v1_0
```

`session` is appended to `skatmind.api.v1.__all__`; every earlier export retains
its order and identity. `skatmind.__all__`, `skatmind.api.__all__`, and
`skatmind.errors.__all__` are unchanged. Direct imports from `skatmind.session_*`
remain unsupported. Only names in `skatmind.api.v1.session.__all__` are stable.

The canonical operations are, in order:

```text
create
apply_command
rewind
correct
export_position
export_historical
build_checkpoint
classify_checkpoint
build_persistence_document
resume_persistence_document
observe_checkpoint
export_checkpoint_review
```

## Stable exports

The first 52 names remain unchanged and preserve their exact order and identity:

```text
PUBLIC_SESSION_API_VERSION
PUBLIC_SESSION_API_NAMESPACE
PUBLIC_SESSION_API_COMPATIBILITY_POLICY
SESSION_API_OPERATIONS
SESSION_FIELD_PROVENANCE_VERSION
SESSION_FIELD_PROVENANCE_DOCUMENT_SCOPE
SessionApiVersionInfoV1
SessionApiOptionsV1
SessionApiResultV1
SessionProvenanceContextV1
SessionFieldProvenanceAttachmentV1
SessionFieldProvenanceBundleV1
get_session_api_version_info_v1
SessionPlayerV1
SessionStateV1
SessionCommandRecordV1
SessionCommandV1
SetSessionGameMetadataCommandV1
RecordSessionDealtCardCommandV1
SetSessionDeclarerCommandV1
SetSessionDeclarationCommandV1
RecordSessionDiscardCommandV1
RecordSessionPlayCommandV1
SetSessionGameEventCommandV1
SetSessionGameEndCommandV1
PromoteSessionToRetrospectiveCommandV1
SetSessionPublicHandCommandV1
SessionValidationDiagnosticV1
SessionExportReadinessV1
SessionValidationResultV1
SessionTransitionResultV1
SessionPositionExportOptionsV1
SessionRequestExportV1
SessionDecisionCheckpointV1
SessionUndoResultV1
SessionCommandCorrectionV1
SessionCorrectionResultV1
SessionCheckpointLineageV1
SessionPersistenceDocumentV1
SessionResumeResultV1
parse_session_command
create_session
apply_session_command
rewind_session
correct_session_command
export_session_position_request
export_session_historical_request
build_session_decision_checkpoint
classify_session_decision_checkpoint
build_session_persistence_document
resume_session_document
serialize_session_result
```

Issue #157 appends these names in exact order:

```text
SESSION_DECISION_OBSERVATION_VERSION
SESSION_CHECKPOINT_REVIEW_EXPORT_VERSION
SessionDecisionObservationV1
SessionCheckpointReviewExportV1
observe_session_decision_checkpoint
export_session_checkpoint_review_request
files
```

Issue #337 appends `RecordingCommand`, `RecordSessionBidCommandV2`, and
`BidAction`, in that order. `SessionCommandV1` remains the closed union of the
ten original command types. `RecordingCommand` is the public type accepted by
`apply_session_command` and returned by `parse_session_command`:
`SessionCommandV1 | RecordSessionBidCommandV2`. `apply_session_command` also
accepts a JSON-object mapping.

The exposed domain types are the exact existing frozen internal types, not
copies or adapters. Type identity is therefore preserved. Projection values,
low-level validators, persistence codec and fingerprint helpers, temporary-file
helpers, and internal ledger builders remain internal. Stable file transport is
available only through the appended `files` subnamespace; it does not expose the
low-level helpers.

## Versions and options

Use `get_session_api_version_info_v1()` to discover supported recording
versions. Its read-only Python properties give all supported versions:

| Property | Versions | Version used for a particular record |
| --- | --- | --- |
| `supported_session_command_versions` | `(1, 2)` | The ten original commands use 1; `record_bid` uses 2. |
| `supported_session_contract_versions` | `(1, 2)` | A state uses 2 exactly when its accepted log contains a `record_bid`; otherwise 1. |
| `supported_projection_versions` | `(1, 2)` | Replay of that log follows the same rule, including when rewound to a prefix. |

The singular fields `session_command_version`, `session_contract_version`, and
`projection_version` report the **V1 baseline** (`1`), not the maximum supported
versions. The constructor and `to_dict()` retain the original descriptor shape
and values; the three discovery properties are not serialized. The public API,
transition, export, checkpoint, history, persistence and other envelope versions
keep their existing meanings. Package and Schema versions are independent.

`SessionApiOptionsV1` has two strict booleans:

```text
validate_output = true
include_provenance = false
```

Disabling `validate_output` skips only final Session Result Schema validation.
Python contract, replay, transition, export, persistence, and information-policy
validation remain mandatory.

## Result envelope

`SessionApiResultV1` contains `api_contract_version`,
`public_session_api_version`, `operation`, `value`, and nullable
`field_provenance`. It contains no path, transport metadata, request ID, or
timestamp. Null provenance is omitted from serialized output.

| Operation | Exact value |
| --- | --- |
| `create` | `SessionStateV1` |
| `apply_command` | `SessionTransitionResultV1` |
| `rewind` | `SessionUndoResultV1` |
| `correct` | `SessionCorrectionResultV1` |
| `export_position` | `SessionRequestExportV1`, target `position_analysis` |
| `export_historical` | `SessionRequestExportV1`, target `historical_game` |
| `build_checkpoint` | `SessionDecisionCheckpointV1` |
| `classify_checkpoint` | `SessionCheckpointLineageV1` |
| `build_persistence_document` | `SessionPersistenceDocumentV1` |
| `resume_persistence_document` | `SessionResumeResultV1` |
| `observe_checkpoint` | `SessionDecisionObservationV1` |
| `export_checkpoint_review` | `SessionCheckpointReviewExportV1` |

Rejected, conflicted, unavailable, unchanged, and partial domain outcomes are
normal typed Results, not transport failures.

## Parsing and execution

`parse_session_command()` validates a JSON-object mapping against the packaged
Session Schema and uses the persistence codec to reconstruct the ten V1 command
kinds and the V2 `record_bid`. It preserves explicit nulls and rejects missing,
unknown, or invalid fields. It performs no transition.

For example, with a state at revision zero and middlehand player ID `M`, a
caller can submit the typed command or its JSON-object mapping:

```python
from skatmind.api.v1 import session

bid: session.RecordingCommand = session.RecordSessionBidCommandV2(
    expected_revision=0, observation=session.BidAction("M", "bid", 18),
)
assert session.parse_session_command(bid.to_dict()) == bid
result = session.apply_session_command(state, bid)
```

Each operation wrapper invokes exactly one corresponding internal operation.
Position and Historical exports return existing immutable `RequestDocumentV1`
values without executing Position Analysis, bounded Search, Historical review,
Application dispatch, or `execute()`. Persistence construction and resume remain
in-memory operations. Observation derives the first accepted local Play after a
frozen Checkpoint; Checkpoint Review Export copies the frozen Request and adds
only `analysis_mode = post_game_review` and that observed Card. Neither operation
executes analysis. See
[Session Decision observations](session_decision_observations.md).

## Public file transport

Issue #157 adds stable `skatmind.api.v1.session.files` version `1`, with exact
`save` and `load` operations. `SessionFileApiResultV1` maps Save to the existing
`SessionPersistenceWriteResultV1` and Load to `SessionResumeResultV1`, retains no
path, and has no provenance option. Save preserves expected-content-fingerprint
compare-and-swap and atomic same-directory replacement; Load preserves strict
UTF-8 parsing, fingerprint verification, replay, and lineage reconstruction.

The file API is independently versioned and exported only as the appended
`files` module from this namespace. See
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md) for
its exact 12-name export surface and signatures.

The existing public error hierarchy is reused. Existing `SkatMindError` values
pass through; public-boundary `ValueError` and `TypeError` become
`SkatMindValidationError`; Schema, resource, invariant, and serialization failures
use their existing stable error classes.

## Schema and boundaries

`schemas/session.schema.json` is a strict Draft 2020-12 standalone contract,
loaded lazily from Package Resources. Issue #157 extends that same Schema for
creation input, file API values, observations, review exports, and the two
appended operations. It does not add a Session Root workflow: `WorkflowV1`
remains seven values. The published `v0.14.0` baseline has 63 authoritative and
packaged Schemas, 85 generated outputs, and Package version `0.14.0`; the current
Package version is `0.17.0`, and the historical published `v0.13.0` baseline
remains 62 Schemas and 77 scenarios.

Installed, module, and Legacy CLIs expose the same 12-subcommand `session`
family, public file transport, automatic exact Checkpoint collection,
Checkpoint-based review, explicit Position/Historical execution, and the
phase-aware Assistant. Issue #158 completed Release preparation before the
maintainer's manual `v0.14.0` publication. There is still no Session Root
workflow, automatic analysis after every Command, persisted analysis Result,
default path, or GUI/platform integration.

See [Session provenance](session_provenance.md) for the optional returned-value
sidecar.
