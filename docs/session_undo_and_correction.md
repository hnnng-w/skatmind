# Session Undo, correction, and Checkpoint lineage

Issue #154 adds the internal version-1 history-edit layer around immutable
Session States. It rewinds one accepted Command Log to a strict prefix, replaces
one accepted Command and replays the original later suffix, and classifies frozen
Decision Checkpoints against the resulting linear history. Issue #155 adds a
separate private persistence wrapper for the resulting active State and optional
caller-supplied Checkpoints, without changing this history layer. Issue #156 adds
stable `rewind_session()`, `correct_session_command()`, and
`classify_session_decision_checkpoint()` wrappers over the existing operations.

## Normal browser declarer/declaration correction (Issue #250)

The unified Session page now offers **Change declarer** and **Change declaration**
beside their accepted facts, including during play and after End. Each action binds
the unique accepted Command of that kind. The normal path is:

**Select accepted fact → edit its prefilled value → Check change → Apply or Cancel.**

There is no normal revision or Command-JSON input. The other fact is read-only context.
The named Player selector uses the source roster. Declaration input comes from the
accepted Command, including its supplied or absent Matadors; later inferred counts
never prefill it. Compact declaration flags remain explicit true/false, and blank
bid/count remain absent. Missing or ambiguous targets issue no entry selection.

`app_web/session_declaration_correction.py`, its HTTP adapter and renderer retain one
private editor/preview and at most two current-source entry tokens per Session.
Selections expire after 30 monotonic minutes. Selecting again or **Change proposal**
rotates the editor identity and revokes old Apply without extending that deadline.
Invalid re-preview also revokes old Apply. Cancel must match the current editor;
stale Cancel cannot discard newer work. Drafts and discarded suffixes are not saved.

Preview invokes the existing public immutable `correct_session_command()` once. It
does not call the guided saving adapter, collect Checkpoints, change accepted bytes,
publish `last_operation`, execute analysis, or clear a valid Result. Rendering uses
the retained typed result; it does not build another correction candidate. Ordinary
preview text distinguishes Plays from other Commands and shows:

* **Applied/full replay:** the changed fact and retained continuation; deliberate
  named Apply sends `confirm_apply=on`, without a checkbox.
* **Unchanged:** the original full continuation remains. The canonical empty replay
  tuple means no replay was necessary, not missing or discarded history. Apply saves
  nothing and retains the valid Result.
* **Partial:** visible removal counts, the first failed entry (itself removed), the
  actual conflict, all removed records in an inspectable disclosure, and the next
  recording task. Plays, public-hand/deal/Skat/discard evidence, events and End are
  accounted for. A fresh unchecked required removal checkbox supplies
  `confirm_apply=on`; its separate unnamed Apply button explicitly mentions removal.
* **Rejected:** actual validation feedback and no usable Apply. The editor retains
  applicable safe values; Matador verification failures identify the count field.

A verified preview has no editable proposal alongside its Apply. Language switching
preserves the selected source and appropriate editor/preview, clears destructive
consent, and never extends expiry. Enhanced unsent fields remain bound to the exact
form/source; native no-script switching preserves submitted values only. Named
submitters never enter language overlays. Native selection alone sends no POST.

Issue #262 makes only the editor's optional Matador input `7em`, bounded by available
width, with concise all-types help and the Session evidence restriction. Its label
and errors remain full natural width and help/error IDs remain separately associated.
Accepted supplied counts and blank values still prefill from the selected Command;
safe submitted/unsent language restoration follows the existing boundaries above.
The verified preview stays read-only. Select/Preview/Cancel expiry, no-op retention,
real Apply invalidation and fresh unchecked partial-removal consent are unchanged.
See [count presentation](compact_game_declaration.md#optional-count-presentation-issue-262).

Apply holds the existing Session lifecycle gate and Session lock, checks exact
context/generation/persistence content and the current file, rebuilds the canonical
correction, and compares the complete result including retained/discarded records
and diagnostics. It then delegates to `correct_guided_session_command_v1()` under
that same lock. Its repeated calculation deliberately preserves the existing
Checkpoint/CAS boundary. A real full or partial change saves once; a no-op saves
nothing. External CAS conflicts and pre-save failures retain accepted in-memory
data and valid Results; there is no hidden retry.

Existing frozen Checkpoint variants are retained, with normal collection and
current/ancestor/future/diverged lineage. No future knowledge is backfilled to
recover review eligibility. Equal numeric revision after a real edit still
invalidates the Session Result. Another family's Match Report is independent.
Partial warnings remain untimed and are not clean success receipts. Preview does
not consume an earlier operation receipt.

**Removal is destructive to the active linear recording.** There is no automatic
in-app Undo/Redo, backup, suffix salvage, inferred replacement evidence, automatic
promotion, or second correction. An ended Game can become incomplete. The normal
recording controls and strict reopen work with the saved valid prefix.

### Private transport

Exactly four POST routes and five registered definitions are added. Each reads at
most **8,192 bytes**, retains existing Host/Origin/authentication enforcement and
optional `_frontend_form_instance`, and rejects extra or repeated fields.

| Route suffix under `/sessions/declaration-correction/` | Fields besides `managed_handle` |
| --- | --- |
| `select` | `correction_selection` |
| `preview` (declarer) | `correction_selection`, `correction_kind=set_declarer`, `player_id` |
| `preview` (declaration) | `correction_selection`, `correction_kind=set_declaration`, the seven compact declaration fields |
| `apply` | `correction_selection`, literal `confirm_apply=on` |
| `cancel` | `correction_selection` |

No client revision, replacement Command, suffix, actor mapping or removal count is
accepted. Preview kind and Player membership are checked against the retained source.
Success uses 303 PRG: Select/Preview to `#session-declaration-correction`, Apply/Cancel
to `#session-recording`. Contextual 400/409 feedback retains usable controls and
error focus. Reload/reopen, mutation, foreign/equal-revision content, retirement and
expiry invalidate old work. Global app-lock sections do no file I/O.

The intentional private inventory changes from **63 POST routes / 107 forms** to
**67 / 112**. Catalogs change from **1,625** to **1,657** ordered paired keys.
Public APIs, schemas, persistence contracts, Package 0.17.0, Python >=3.13,
AGPL-3.0-only, dependencies including `tzdata>=2026.4`, and 98 generated scenarios
are preserved.

### Legacy direct operation

Expert `/sessions/command` correction, including old compact declaration clients,
metadata/time correction and Undo retain their direct transport and canonical
semantics. They are not silently made staged. Competing ordinary direct declarer/
declaration forms are no longer emitted beside the staged path; other advanced
tools and `session-history` remain. The immutable engine behavior documented below
is unchanged.

### Focused and installed evidence

Starting clean branch: `bug/250-session-declaration-correction`, HEAD
`6134c3dd72588b56799a6f96dea581b601355a30`. Actual #250 and R06 in #208 were read.
The first added real-HTTP regression failed because no staged entry forms existed.
The independently installed baseline confirmed numeric declarer targeting and
immediate declaration saves; canonical partial replay was not a scoring defect.

The literal B/C/A nine-Play fixture confirms full B→C and bid 18→20 replay,
unchanged original suffix, rejected unverifiable Matadors=2, Grand→Null with exactly
six retained/three removed Plays, and B→local A with nine removed Plays and return
to Skat/discard entry. Additional existing Hand/public-hand/event/ending fixtures
check retained and removed evidence without a new rules matrix. Tests exercise
real saves, continuation/reopen, submitted language values, exact tokens, duplicates,
source mismatch, supersession, expiry, competing Apply and actual external CAS.
Clock and pre-save-failure injections are explicitly labelled. A focused 18-module
run passed **513 tests**, no skips, in **370.59 seconds**.
After the receipt guard and its focused regression, the final correction/catalog/
validation run passed **86 tests**, no skips, in **103.25 seconds**; repository Ruff
also passed. Catalog key, placeholder and lexical-order checks ran before the full check.
The first complete full-check attempt passed all pre-pytest stages, then reported
six failures in older knowledge-entry/general-HTTP tests that expected the removed
invalid-stage declarer/declaration forms (9,568 passed, three platform skips;
actual child exit 1). Their assertions now check the intended source-bound UI and
retain real legacy expert phase/parse rejection coverage. This unsuccessful run is
retained as `250-full-check-20260921T180312Z.{log,json}`; the corrected tree requires
a new complete full check, not a filtered retry.
The focused correction of those expectations, neighboring file-boundary checks and
catalog/validation gates then passed **154 tests**, with the three existing Windows
symlink-permission skips, in **72.75 seconds**. Ruff passed again. No product code,
installed browser surface, dependency, skip condition or check configuration changed
in this test/documentation correction.

The optional `scripts/verify_session_declaration_correction.py` uses independent
Wheels, synthetic managed roots and the existing dependency-free Edge harness.
It validates installed module/resource hashes, HTTP asset bytes, emitted payloads,
native pointer/Enter actions and zero selection-only POSTs. Both editors, full/
partial/no-op/rejection, Cancel, de/en and script on/off are exercised. Representative
desktop 1365, 390, 320 and doubled-text 320 views include warnings, removal details,
actions and focus. The first repaired screenshot inspection led to a scoped wider
checkbox-column rule; no global Card/Result-table redesign was made.

The real SJ review keeps 14/29, its seven historical Cards and equal-best Jacks
through Preview/Cancel/no-op. The approved fixture retains C10/CJ/DK/D7 after six
Tricks and CJ after nine. Exact source and Request/Result download files and hashes
are retained beside browser evidence, including an unrelated actual Match Report
that survives Session mutation. Strict reopen still needs explicit analysis.

Final browser artifacts are under the disposable temporary `opencode` directory:
`250-before-browser-5/evidence.json` and `250-after-browser-4/evidence.json`, with
their inspected PNGs, exact initial/before-partial/partial Session files, SJ
downloads and unrelated Match Report. Windows used Python **3.13.7** and headless
Edge **153.0.4234.48**. Baseline/repaired runs retain 18/41 representative page
measurements and 34/129 recorded browser actions (not an acceptance quota). Each
run includes 109 real Session saves across fixture creation, normal recording,
and deliberate mutations; the repaired run records 63 canonical correction calls,
63 existing Checkpoint-collection calls and one explicit Session review execution.
Per-action counts demonstrate zero Save/collection/execution during Preview and
one Save for a real Apply. The unrelated executed Match Report is retained separately.

Installed Wheel SHA-256:

```text
baseline 36d95f17708b5801a954d7590ae210bfa53784f6e94e2b6598a65e551fc012b7
repaired cc66166c05c4375bb738959f9dade5ea4567799cf6c178183e13ffe8d9829060
```

The final repaired SJ Request/Result are 1,534/9,640 bytes with hashes
`05dc65aa713fb37c7b40cd9a4027ce6926881e6bb0c98adaf4256b8a7f14ec94` /
`76eb05221cab155ff59f734ec568bbead767c2f309d6823546d598412ac545c1`.
The unrelated Match Report is 8,739 bytes,
`34a33fe4259847afa164387b438e6e0df5cb4dce62370f89eed8e7f802843b94`.
Earlier interrupted/failed probe attempts remain retained; none is counted as a
successful final browser run. Failures included harness import/navigation/closed-
disclosure handling and a locale assertion, followed by inspected script corrections.

This is headless Edge technical evidence, not physical-device, assistive-technology
or maintainer UAT acceptance. Full-check results belong to the final unchanged-tree
execution report. Both `check` and `v1-supported-platform-matrix` must pass on the
exact merged commit before manual closure. #249 stays completed; #208/other findings
remain open, UAT-01 unaccepted, UAT-02–12 paused, B-09/B-07 open and B-06 closed.

## Engine contract identity

The independent constants are:

```text
SESSION_HISTORY_EDIT_VERSION = 1
SESSION_UNDO_POLICY = immutable_strict_prefix_rewind
SESSION_CORRECTION_POLICY = replace_one_command_then_replay_suffix
SESSION_CORRECTION_SUFFIX_POLICY = stop_before_first_rejected_command
SESSION_HISTORY_STATE_POLICY = accepted_log_length_per_immutable_state
SESSION_BRANCHING_POLICY = unsupported
SESSION_REDO_POLICY = caller_retained_suffix_only
SESSION_CHECKPOINT_LINEAGE_VERSION = 1
```

History Edit and Checkpoint Lineage versions are independent of the Package,
Public API, Application, installed CLI, Session, Command, transition, projection,
Request-export, Position-option, Decision-Checkpoint, Provenance, Schema, and
other Domain versions. Package version is `0.17.0`. Session Persistence
version `1` is also independent of both versions here.

The canonical Undo statuses are:

```text
applied
unchanged
rejected
revision_conflict
```

The canonical Correction statuses are:

```text
applied
unchanged
partial
rejected
revision_conflict
```

## Immutable source-State model

History operations never mutate the source `SessionStateV1`. The source remains
one immutable accepted Log and may be retained by the caller. A successful edit
constructs another immutable State containing exactly one active linear accepted
Log.

Revision remains:

```text
revision = len(command_log)
```

Undo may lower the numeric revision. A complete one-for-one correction may keep
the same numeric revision while changing the accepted Log. Numeric revision is
therefore not a globally unique history identity. Generation, branch, commit,
merge, active-head, and fingerprint fields are absent. Persisted content
fingerprints and cross-process stale-write detection belong only to the separate
persistence wrapper; State remains the authoritative accepted Log and gains no
persistence field or path.

## Strict-prefix Undo

`rewind_session_state_v1()` first replay-validates the exact source State once.
It then handles revision conflict before target-range semantics.

An earlier valid target reconstructs from the empty revision-zero projection
through exactly the retained accepted prefix. It uses the existing projection-
level Command validator, preserves the original accepted Commands and revision
fields, calculates Validation once from the final projection, and constructs one
canonical State. It does not call normal State-level Command application for
each prefix record.

`SessionUndoResultV1` reports:

```text
session_history_edit_version
status
session_id
expected_revision
source_revision
target_revision
current_revision
state
removed_records
diagnostics
```

An applied result contains the exact source suffix beginning at
`target_revision + 1`. An unchanged result targets the current revision. A target
beyond the source revision is a normal rejected Result with the appended
`history_revision_violation` Diagnostic at `/target_revision`. A stale or future
expected revision returns exactly one blocking `revision_conflict` Diagnostic.
Negative and Boolean revision inputs remain contract errors.

Undo is not a Command. It appends no accepted record and stores no removed suffix
inside the resulting State. Undo Results and removed suffixes are never persisted.

## Mode, phase, and readiness recomputation

The retained Log is authoritative. Prefix reconstruction derives current Capture
Mode, phase, Validation, Position readiness, and Historical readiness from only
the retained Commands.

Consequences include:

* removing Game End returns an ended Session to `play`;
* removing Plays rederives completed and incomplete Tricks and the next Player;
* removing Discards, Declaration, Declarer, Deal Cards, or metadata removes their
  facts and may return to `skat_and_discard`, `declaration`, `deal`, or `setup`;
* removing a continuation or public-hand Command removes that public state;
* removing promotion returns an initially Live Session to current Mode `live`.

Initial Capture Mode, canonical Players, and the local Player identity never
change. No private or public fact is retained after its accepted Command leaves
the active prefix.

## One-command correction

Issue #230 adds private unified local date/time entry to the existing metadata
correction surface. Each emitted form targets one exact accepted metadata Command.
Keep reads that Command's original timestamp server-side, preserving all accepted
source spelling and precision; Replace converts an explicit local date/time/zone
and Remove uses the existing absent value. Source binding includes full history,
reopen context, target and profile generation, so equal revisions are insufficient.
The existing one-command/suffix replay below remains authoritative. See
[Local time entry](local_time_entry.md); no Command or Product persistence format changes.

`SessionCommandCorrectionV1` contains:

```text
session_history_edit_version
expected_revision
target_revision
replacement_command
```

The target is positive and no greater than the expected source revision. The
replacement is exactly one current `SessionCommandV1` whose expected revision is
`target_revision - 1`. Every current Command kind is supported through the same
existing validator. There is no deletion, insertion, JSON Patch, multi-command,
or caller-supplied suffix form.

`correct_session_command_v1()` performs one source replay, reconstructs the
prefix immediately before the target, applies the replacement once, and then
replays each original later Command in order through the projection-level
validator. Original suffix Commands retain their payload and original revision
numbers.

`SessionCorrectionResultV1` reports:

```text
session_history_edit_version
status
session_id
expected_revision
source_revision
target_revision
current_revision
replacement_command
state
original_record
replayed_suffix_records
discarded_suffix_records
failed_original_revision
diagnostics
```

An exact replacement equality is an unchanged no-op and evaluates no suffix.
Replacement rejection retains the exact source State and evaluates no suffix.
Complete replay returns `applied`, preserves the source numeric revision, and
reports every original later record as replayed.

If one later original Command becomes invalid, correction stops before it and
evaluates no later source Command. The normal `partial` Result contains the
corrected valid prefix, reports all successfully replayed records, reports the
failed and remaining records as the exact discarded suffix, identifies the first
failed original revision, and retains the existing Command-specific blocker
Diagnostics. Discarded records are not stored in the resulting State.
Correction Results and replayed or discarded suffix reports are never persisted.

## Information safety

Correction adds no semantic shortcut. Existing phase, exact ownership, legal-
card, turn, Declaration, Matador, Skat, Discard, public-hand, continuation,
Game-end, and information-policy rules remain authoritative for the replacement
and every suffix Command.

Removing or replacing promotion can therefore make later Retrospective private-
hand entry invalid. Replacing an earlier Play rederives every later Turn and
Trick. Replacing a Declaration can invalidate Skat, Discards, Ouvert public hands,
and Plays. Replacing a public hand can invalidate a later owner Play. The history
layer never infers ownership, Skat, Discards, private hands, public hands, events,
or endings to preserve a suffix.

Search Worlds, simulation ownership, inference results, proof states,
Provenance attachments, Recommendations, and workflow Results are not caller
facts and cannot enter correction through a Session Command.

## No branching or Redo stack

Version 1 has one active linear Log. Removed and discarded records exist only in
the operation Result. There is no branch identity, alternate head, merge,
automatic retry, or stored Redo stack. A caller may retain returned records and
submit a later explicit operation, but the Session State stores none of them.
Persistence stores only that active State plus optional caller-supplied frozen
Checkpoints, never a Result, suffix, or Redo value.

## Checkpoint lineage

`SessionCheckpointLineageV1` contains only:

```text
session_checkpoint_lineage_version
relationship
session_id
checkpoint_revision
state_revision
```

`classify_session_decision_checkpoint_v1()` replay-validates the State and, when
the State reaches the Checkpoint revision, reconstructs that exact accepted
prefix and the expected information-safe Position Request. It compares the full
expected Checkpoint, including Mode, decision indexes, actor, seat, relative map,
and frozen Request.

Relationships are:

* `current`: equal revisions and exact Checkpoint reproduction;
* `ancestor`: a later State has an unchanged effective prefix through the
  Checkpoint;
* `future`: the State revision is below the Checkpoint revision;
* `diverged`: the State reaches the Checkpoint revision but its actual prefix no
  longer reproduces the frozen Checkpoint.

A correction at or before the Checkpoint normally diverges, but may remain
current or ancestor when the complete effective frozen Checkpoint is exactly
equal. A correction strictly after it remains ancestor.

Undo and correction never mutate, delete, rewrite, or attach data to a
Checkpoint. Its source revision and Request remain frozen. Issue #157 derives an
actual-card Decision Observation from the accepted Log and automatically
collects exact Checkpoints in CLI orchestration without changing this rule.

Strict Resume reconstructs optional persisted Checkpoints and recomputes each
`current`, `ancestor`, `future`, or `diverged` relationship against the resumed
active State. Lineage Results themselves are derived and are not persisted.

## Export compatibility

History edits execute no export automatically and cache no Request. Callers may
pass the resulting active State to the existing Position or Historical Session
exporter. Each exporter replays that edited State normally and uses its recomputed
readiness. Removed and discarded Commands cannot influence the export because
they are absent from the active accepted Log. Existing frozen Checkpoints remain
separate values.

A resumed State is the same `SessionStateV1` and remains compatible with Undo,
correction, lineage classification, and both exporters. Persistence Load/Resume
does not automatically run a history operation, export a Request, or execute
analysis. See [Session persistence and Resume](session_persistence_and_resume.md).

## Determinism and execution bounds

For equal typed inputs, Undo, correction, State, suffix reports, Diagnostics,
lineage, and serialization are equal. No operation adds random state, current
time, generated identity, fingerprint, environment path, or file path.

One Undo performs at most one source replay and one prefix reconstruction. One
correction performs at most one source replay, one prefix reconstruction, one
replacement application, and one linear suffix pass. One lineage classification
performs at most one source replay, one prefix reconstruction, and one expected-
Request reconstruction.

Each public wrapper invokes its matching internal history operation exactly once
and returns the existing Undo, Correction, or lineage value in a Session Result.
Optional complete provenance and final standalone-Session-Schema validation do
not add replay. These operations run no Search, Immediate Analysis, hidden-card inference,
Multi-Step, Policy Comparison, Historical workflow, Review, Coaching, scoring,
Settlement, Application, file I/O, timeout, or background task.

## Current boundary

The implementation remains under `skatmind.session_history*` and is exposed
through the additive `skatmind.api.v1.session` namespace. Issue #157 adds
installed/module/Legacy `session undo` and `session correct`, optimistic file
Save, automatic collection of a newly Position-ready State, lineage display,
examples, and generated scenarios without changing history semantics. Only
applied Undo and applied or partial Correction States are saved; unchanged and
rejected Results do not rewrite the file.

The published `v0.14.0` baseline remains bounded to seven Root workflows, 63
authoritative and packaged Schemas, 85 generated outputs, and Package version
`0.14.0`. Issue #158 completed Release preparation before manual maintainer
publication. Automatic Redo, branching/merge, arbitrary Log surgery,
GUI/platform/cloud/encryption, and unrelated pre-v1 gaps remain open. See
[Session CLI and end-to-end capture](session_cli_and_end_to_end_capture.md).
