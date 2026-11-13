# Automatic Learning private store (Issue #309, S1)

Current follow-up: the maintainer identifies #309, its strict-resume correction
and installed service acceptance as complete at the #310 starting baseline.
Historical pending-status records below remain point-in-time records. Issue #310
adds only the [S2 ordinary Match adapters, capture, access and retry](ordinary_match_analysis_retention.md)
on this unchanged storage format. Its typed object codecs use version `2`;
S1 opaque codec-1 fixtures remain non-consumable. The S1 service descriptions below
describe the original foundation; the linked S2 document is authoritative for the
new `read_evidence` admission and optional final commit guard.

Separate S3 follow-up: [Issue #311 rollout retention](match_rollout_analysis_retention.md)
adds explicit `rollout`/`match_rollout` admission. Both Match families deliberately
reuse the original codec-2 `match_source` bytes/header and one SourceVersion record.
Store format, S1 opaque behavior, quotas and transaction lifetime remain unchanged.
The historical S1/S2 descriptions and validation records below are preserved.

Separate S4 follow-up: [Issue #312](automatic_match_learning_s4_verification.md)
adds a distinct preparation reservation owner and **generation object codec 2**
with an exact input ledger and strict service-level semantic recipe admission.
Manifest/storage envelope version `1`, S2/S3 source/evidence bytes, existing quotas,
pins and cleanup semantics remain intact. Codec-1 generation descriptors remain
storage-only. Current/previous replacement is one manifest CAS; derived artifacts
stay process-local and restart reconstruction is explicit.

Separate S6 follow-up: [Issue #314](automatic_session_learning_s6_verification.md)
registers native Session source/ordinary/rollout object codec **2** and an explicit
mixed generation codec **3**. Original complete Session fingerprints, native public
execution tuples and genuinely captured internal provenance are reconciled on
admission. Codec-2 Match generation admission and S2/S3 bytes remain unchanged.
The one bounded delivery receipt additionally binds fresh mixed source membership;
source-history release retains existing reference-first and reader protection.
Manifest/storage envelope version **1** and all existing quotas remain intact.

S7 follow-up: [Issue #316](automatic_historical_learning_s7_verification.md) registers
codec-2 `historical_source`, `historical_review` and `match_historical` objects and
explicit generation codec **4**. Optional manifest `historical_heads` binds each
live manual source to one exact successful execution; `historical_retired` prevents
save-only retry from reviving a deleted identity. Empty fields are omitted so legacy
manifest bytes remain exact. Source, execution and head publish in one manifest CAS.
Cleanup cannot release live-head dependencies. The Match continuity basis survives
Historical-only descriptor retirement.

Historical native tuples use private lossless `zlib-json-v1` encoding with strict
length, digest, complete-stream and trailing-data checks. Each expanded tuple is
bounded at 128 MiB; the existing stored-object 16-MiB and total 512-MiB quotas remain
unchanged. The optional exact-byte delivery receipt can retain admitted typed values
only within its existing 64-object/candidate and 16-MiB stored-byte bounds, plus a
128-MiB expanded-native bound. Every hit still reads exact current bytes and inventory;
larger values take strict admission. No TTL or metadata-only authority is introduced.
Standalone strict `read_evidence` and mutation admission retain their boundaries.

## Operation-scoped bulk reads (Issue #318)

The baseline for this correction is `24e7dfe62b3544cdbb988b25d592083233ba2289`
on `bug/318-learning-bulk-read`, initially clean. Product code changes in the store
and four private frontend consumers. No persistence format, evidence codec, public
contract, download representation or independent collection owner changes.

`read_evidence_many(evidence_ids, expected_manifest=...)` accepts an immutable tuple
of requested identities and the original manifest fingerprint. Under the existing
store coordination lock it checks that manifest and indexed membership, reads the
complete indexed archive through bounded exact-byte/object/dependency validation,
performs **one complete typed semantic admission**, and rechecks the manifest.
It returns only the requested typed values in caller order, including repeated IDs.
Unknown IDs fail as unindexed; missing, corrupt or unsupported requested evidence
raises `UnsupportedEvidenceError` without a partial result. Independently intact
evidence remains readable. An empty selection checks the expected manifest without
loading evidence. `read_evidence` retains its strict single-record behavior through
the same private admission helper.

The tuple is operation-local data, **not a delivery credential**. The store retains
no new receipt, cross-operation cache, TTL or metadata-based authority. Each strict
bulk call reads current bytes again. Existing typed source, original execution and
download reconciliation, owned-root checks and same-size/same-mtime corruption
detection remain active. The complete archive is processed even when only a subset
of IDs is requested; neither receipt overflow nor unavailable unrelated evidence
truncates the index.

Migrated consumers:

* Automatic Learning Update reads its ordered selected evidence once inside its
  existing reader pins. Post-build strict snapshot comparison, reservations,
  source/owner/attempt checks, manifest CAS and installation authorization remain.
* Maintenance previews bulk-load available evidence captions once, preserve the
  original entries and `None` captions for unavailable evidence, and end reader
  pins before capturing the exact cleanup preview/consent epoch. Source-release
  consent, final source checks and reference-first cleanup are unchanged.
* Saved Match and Session analysis lists bulk-load the same available entries in
  manifest order. Final delivery additionally checks that every rendered evidence
  ID remains available, so bytes corrupted after projection cannot deliver stale
  captions under an otherwise unchanged manifest. Original-record routes and
  original Request/Result/Strategy-source downloads keep their contracts.
* Saved Historical Review lists share one load across both source-head and evidence
  captions. The existing bounded delivery receipt, when eligible, is freshly
  byte-checked once for that bulk phase; otherwise the service uses strict bulk
  admission against the binding's manifest. Original binding validation, reader
  pins, final HTTP authorization and stale-response recovery remain in place.

The receipt stays bounded at **64 objects/candidates**, **16 MiB stored bytes** and
**128 MiB expanded native values**. Per-object/expanded-tuple bounds, the **512 MiB**
store quota and **2,048 entries per evidence class** remain unchanged. Above receipt
limits, full strict processing remains available without eviction or omission.
Restart still requires strict admission. Passive list/caption operations perform
zero Card analysis and zero archive mutation; Update derives from existing evidence.
Cooperating reader pins, source barriers and reservations remain separate from these
temporary values. Filesystem checks remain optimistic against uncontrolled writers.

### Work evidence and affected validation

The new complete `tests/test_automatic_learning_bulk_read.py` uses genuine Match
Immediate, genuinely unavailable early Match Search, Session and guided Historical
executions. Counters wrap real archive reads, full admission and successful typed
retained-result loads without replacing their implementation. Fixture creation and
publication are measured separately; retained-result loading is not Card analysis.
Two requested-count comparisons use the unchanged strict single-record path as the
before-work reference on the identical disposable archive:

| Requested records | Complete admissions, before → bulk | Indexed objects/read objects | Retained Results loaded | Object bytes read |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 2 → 1 | 14 → 7 | 8 → 4 | 13,552,006 → 6,776,003 |
| 4 | 4 → 1 | 28 → 7 | 16 → 4 | 27,104,012 → 6,776,003 |

The focused serial observation was **8.527 → 4.386 seconds** for two requested
records and **21.226 → 5.253 seconds** for four. These are bounded local observations,
not latency gates, full-tournament measurements or measured CI speedup. This fixture
created three new Card executions in 5.491 seconds plus one separately scoped genuine
Historical execution. Each disposable publication/snapshot setup performed five
admissions, 17 indexed-object visits, 39 object reads (47,562,771 bytes), and ten
retained-result loads; setup took 20.336–32.250 seconds in that invocation. Those
setup costs are excluded from the before/after read times above.

Consumer checks use five genuine retained bindings in nine indexed objects, including
two independent guided sources with equal original public Game/Player IDs. Update,
maintenance and Match/Session list bulk phases each admit once and load five retained
Results. An eligible Historical receipt phase performs zero new typed admissions
but still reads all nine exact objects; its overflow phase admits once. Complete
list operations retain their constant boundary work: Match/Session lists performed
three admissions each; the Historical list performed zero with a warm exact receipt
and seven with strict fallback. Source/evidence links, ordering, original download
bytes, maintenance consent and same-metadata corruption rejection are also asserted.
These are behavioral checks accompanied by work counters, not call-count substitutes.

The fallback coverage includes tightened object-count and byte thresholds using the
same genuine four-Report archive, plus a **67-object / 34-Report** archive crossing
the unchanged production 64-object limit. Its additional independent Historical
bindings reuse a genuine captured execution; they do not invent an execution Result.
All requested records must be admitted and retain their original bytes.

Final affected selection consists of these **29 complete modules** under `tests/`:

* Store/shared admission and lifecycle: `test_automatic_learning_bulk_read.py`,
  `test_automatic_learning_store.py`, `test_automatic_learning_lifecycle.py`,
  `test_automatic_learning_delivery_receipt.py`.
* Match preparation, native codecs and producer compatibility:
  `test_automatic_match_learning.py`, `test_automatic_match_learning_evidence.py`,
  `test_automatic_match_evidence.py`, `test_automatic_match_rollout_evidence.py`,
  `test_match_evidence_retention.py`, `test_match_rollout_retention.py`.
* Migrated maintenance and browser lists, original consent/language bindings and
  independent collections: `test_automatic_learning_ui.py`,
  `test_automatic_learning_ui_evidence.py`, `test_automatic_learning_source_release.py`,
  `test_automatic_learning_maintenance_readability.py`,
  `test_automatic_learning_language_work.py`, `test_automatic_learning_entry_language.py`,
  `test_saved_match_analyses_web.py`, `test_saved_match_rollouts_web.py`.
* Native Session admission, saved lists and correction isolation:
  `test_automatic_session_evidence.py`, `test_automatic_session_learning.py`,
  `test_automatic_session_web.py`, `test_automatic_session_review_corrections.py`,
  `test_session_evidence_retention.py`.
* Native Historical admission, saved lists, head/correction/deletion isolation and
  Match Historical compatibility: `test_automatic_historical_admission.py`,
  `test_automatic_historical_evidence.py`, `test_automatic_historical_learning.py`,
  `test_automatic_historical_lifecycle.py`, `test_automatic_historical_web.py`,
  `test_automatic_match_historical_evidence.py`.

This selection follows the five Product-file diff, the shared single-record helper
and its genuine-evidence callers, rather than expanding into CLI, solver or unrelated
transport suites. None belongs to the four exclusive modules in
[the validation policy](faster_validation.md); those modules' assignments are unchanged.
The selected parallel workers must exit before the final explicit Quick invocation.

Development CPython 3.13.7 was used, with a **7,200,000 ms** timeout for every
validation invocation. External evidence lives under
`C:\Users\HENNIN~1\AppData\Local\Temp\opencode\318-*`; no maintainer data or installed
UAT environment is used.

| Invocation | Result | Elapsed |
| --- | --- | ---: |
| Pre-implementation `-k bulk_work` | 2 expected failures: bulk method absent; 6 deselected | 91.71s |
| Initial complete bulk test module | 8 passed | 346.45s |
| Added consumer/content/final-delivery checks | 7 passed, 8 deselected | 1313.07s |
| Final 29 complete affected modules, two file-grouped workers | **613 passed, 4 skipped** | **3722.96s** |
| Final explicit `.\scripts\check.ps1 -Mode Quick` | **Passed, exit 0** | **22.296s** |

The final collection contains **617 distinct tests**, including all **16** new bulk
tests. The four existing skips are actual file/root/source-directory symlink checks
requiring unavailable Windows account privileges; actual junction checks pass.
There were no final pytest failures or warnings. No selected module requires the
exclusive phase; both parallel workers finished before Quick. Focused executions
are repeated coverage, not additional distinct passing tests. The first targeted
Ruff invocation found five line-length findings; those were fixed and the next
targeted Ruff invocation passed before complete-module validation.

The final run reconfirmed the table's deterministic counts exactly. Its concurrent
two-worker timing observations were 8.162 → 4.543 seconds (two requested) and
19.076 → 4.274 seconds (four requested). They are not directly comparable to a CI
run or a controlled serial benchmark. The actual production-limit test admitted
all **34 Reports / 67 objects**, reading **9,531,123 bytes**, with **one** complete
admission and **34** typed retained-result loads. Creating/publishing its 30
additional genuine Historical bindings took **21.659s**, with **zero additional
Card executions**, separately from the measured bulk phase.

Exact commands, with `$E` abbreviating the verified existing external parent and
`$Affected` expanded in the actual invocation order:

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
py -3.13 -m pytest tests/test_automatic_learning_bulk_read.py -k bulk_work -q -s -p no:cacheprovider --basetemp "$E\318-red"
py -3.13 -m pytest tests/test_automatic_learning_bulk_read.py -q -s -p no:cacheprovider --basetemp "$E\318-bulk-focused" --junitxml "$E\318-bulk-focused.xml"
py -3.13 -m pytest tests/test_automatic_learning_bulk_read.py -k 'native_lists or mixed_update or list_bulk' -q -s -p no:cacheprovider --basetemp "$E\318-consumers-focused" --junitxml "$E\318-consumers-focused.xml"
$Affected = @(
  'tests/test_automatic_learning_bulk_read.py',
  'tests/test_automatic_learning_store.py',
  'tests/test_automatic_learning_lifecycle.py',
  'tests/test_automatic_learning_delivery_receipt.py',
  'tests/test_automatic_match_learning.py',
  'tests/test_automatic_match_learning_evidence.py',
  'tests/test_automatic_match_evidence.py',
  'tests/test_automatic_match_rollout_evidence.py',
  'tests/test_match_evidence_retention.py',
  'tests/test_match_rollout_retention.py',
  'tests/test_automatic_learning_ui.py',
  'tests/test_automatic_learning_ui_evidence.py',
  'tests/test_automatic_learning_source_release.py',
  'tests/test_automatic_learning_maintenance_readability.py',
  'tests/test_automatic_learning_language_work.py',
  'tests/test_automatic_learning_entry_language.py',
  'tests/test_saved_match_analyses_web.py',
  'tests/test_saved_match_rollouts_web.py',
  'tests/test_automatic_session_evidence.py',
  'tests/test_automatic_session_learning.py',
  'tests/test_automatic_session_web.py',
  'tests/test_automatic_session_review_corrections.py',
  'tests/test_session_evidence_retention.py',
  'tests/test_automatic_historical_admission.py',
  'tests/test_automatic_historical_evidence.py',
  'tests/test_automatic_historical_learning.py',
  'tests/test_automatic_historical_lifecycle.py',
  'tests/test_automatic_historical_web.py',
  'tests/test_automatic_match_historical_evidence.py'
)
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 --durations=20 -p no:cacheprovider --basetemp "$E\318-affected" --junitxml "$E\318-affected.xml" -o junit_logging=all -o junit_log_passing_tests=true
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Both targeted Ruff invocations used `py -3.13 -m ruff check` with the five changed
Product files and `tests/test_automatic_learning_bulk_read.py`. The complete-module
JUnit file retains captured work/timing output, original skips and per-test times.
Final Quick passed Ruff (0.141s), exact packaged-schema parity (0.067s), and Root/Session
input examples (1.925s). Its logs are in
`C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-uafexfv1`, with source digest
`86690ec9dcce66a10d059470609a11cc6a0742f6733f1e252724e5e6787507c6`.
Only this documentation verification result was added after Quick; Product/tests
remain those from the successful complete-module run. Quick does not certify
generated outputs, distributions, the installation matrix or complete regression.

Status: **locally validated; exact-commit hosted CI pending**. Starting and ending
HEAD are both `24e7dfe62b3544cdbb988b25d592083233ba2289`; all seven intended files
remain unstaged/uncommitted. The final diff consists of
`src/skatmind/automatic_learning_store.py`,
`src/skatmind/app_web/automatic_match_learning.py`,
`src/skatmind/app_web/automatic_learning_controller.py`,
`src/skatmind/app_web/saved_match_analyses.py`,
`src/skatmind/app_web/saved_historical_reviews.py`,
`tests/test_automatic_learning_bulk_read.py`, and this document.

### Acceptance and concrete limits

This diff specifically affects installed **multi-record Update, maintenance previews,
Saved Match/Session analyses and Saved Historical source/evidence lists**, including
original downloads and stale-list recovery. A narrow maintainer-installed check of
those paths using disposable genuine evidence below/above receipt limits is relevant
after exact-commit hosted gates. It does not reopen unrelated installed CLI parity or
accepted UAT sequences. No UAT build is created, installed or started by the agent.

One complete archive admission per strict bulk phase still costs proportional work
in archive size and loads all retained Results once, including unrequested entries.
Independent publication/final-delivery checks can add further full passes, especially
above receipt limits. This change neither removes that necessary work nor establishes
a full-tournament/CI timing claim. Keep #318 open pending exact-commit hosted
`check` / `v1-supported-platform-matrix` and maintainer acceptance. No Full run,
extra CI measurement run, installed acceptance or release authorization is claimed.

## Scope and acceptance

This implements S1 of the accepted
[Issue #308 contract](automatic_learning_integration_contract.md), sections 4–6.
It supplies private identities, a durable bounded object archive, an authoritative
manifest, staged-publication reservations, reader pins and explicit cleanup.
Product code changes are additive. Existing Session, Match, manual Corpus,
Request/Result/download bytes, schemas, Public APIs, recommendation behavior and
browser behavior use their existing implementations.

S1 does not capture an execution, create a saved Historical Review, discover
automatic membership, prepare artifacts or provide a new Learning page. All
source/Report semantic adapters are still unavailable. A storage-valid synthetic
payload is never an accepted genuine Report. The original #308 acceptance remains
documentation-only; accepted #292–#307 scopes and evidence remain intact.

Exact-commit branch/main `check` and `v1-supported-platform-matrix`, followed by
maintainer installed service acceptance, remain required. #208 remains open;
UAT-01 is not globally accepted and formal UAT-02–12 remain paused. Recommendation
adaptation is a later goal. This stage does not authorize release preparation.

## Entry points and layering

The private `skatmind.app_web.automatic_learning` module exposes:

* `automatic_learning_root_v1(home)` — pure resolution from an exact
  `ManagedHomeV1` to its separate `automatic-learning` child;
* `initialize_managed_automatic_learning_v1(home)` — explicit initialization;
* `resume_managed_automatic_learning_v1(home)` — strict read-only reopen with a
  fresh process-local owner.

These services have no browser or startup caller. `prepare_managed_home_v1`
continues to create exactly `sessions`, `matches`, `corpora`. The automatic root
is neither a fourth discovered category nor a manual Corpus. Existing 2,048-item
discovery limits are unchanged; complete scans and capped-scan handling are S4.

`skatmind.automatic_learning_store` supplies the underlying explicit-root
`initialize_automatic_learning_store_v1`, `resume_automatic_learning_store_v1`
and `resolve_automatic_learning_root_v1`. A returned `AutomaticLearningStoreV1`
supports:

| Method | Boundary |
| --- | --- |
| `snapshot()` | Bounded strict manifest/object validation, individual quarantine diagnostics, orphan/temporary inventory and retained-byte accounting; no repair or preparation |
| `read_object(reference)` | Bounded storage-envelope read, including a complete orphan; **not** semantic evidence admission |
| `read_evidence(evidence_id)` | Requires an indexed execution identity, then raises `UnsupportedEvidenceError` in S1; no typed Report decoder is registered |
| `begin_candidate(objects)` | Reserves exact object bytes and existing dependency closure; atomically supersedes this owner's prior candidate after successful quota validation |
| `release_candidate(candidate)` | Explicitly releases only the matching active reservation; does not delete published objects |
| `publish_object(object, candidate=...)` | Dependency-first, immutable no-clobber publication; `saved`, `unchanged` or local-process-busy `conflict`; does not register evidence |
| `update_manifest(requested, expected_manifest=..., candidate=...)` | Complete manifest transaction with exact expected fingerprint, next revision and dependency validation; returns `WriteResultV1` with `saved`, `unchanged` or `conflict` |
| `pin_objects(references, expected_manifest=...)` | Context manager retaining the exact indexed dependency closure through caller storage delivery |
| `preview_cleanup(expected_manifest=..., remove_evidence_ids=(), release_source_version_ids=())` | Exact owner-bound preview with manifest, inventory stamps, affected execution identities and deletion list |
| `commit_cleanup(preview)` | Rechecks preview/manifest/inventory, commits reference removal first, then removes only safe owned unreferenced files |

Consumers must release abandoned candidates explicitly. Superseded candidates
cannot publish a manifest or clear a newer reservation. Candidates and pins are
process-local capabilities, never restart authority. These pins protect storage
lifetime; S4/S5 must still implement source/owner/attempt/final-delivery guards.
Saved and unchanged candidate commits release that exact candidate. Resume also
rechecks the authoritative manifest after object validation and conflicts on a
concurrent replacement, without an automatic retry.

## Format and identities

All persisted records/envelopes use private version `1`, strict complete field
sets and exact types (including rejecting booleans as integers). Canonical JSON
is finite, ASCII-escaped UTF-8, sorted-key, compact JSON with one final newline
for stored files. Duplicate keys, BOMs, invalid UTF-8, nonfinite constants and
overflowing numbers are rejected. The manifest accepts equivalent finite JSON
formatting; immutable objects require their exact canonical bytes.

```text
<explicit managed home>/automatic-learning/
    .coordination.lock          # one-byte local OS advisory coordination file
    manifest.json              # authoritative private version-1 document
    sources/<sha256>.json
    reports/<sha256>.json
    generations/<sha256>.json
```

Owned temporary names are `.auto-<32 lowercase hex digits>.tmp`, located beside
their destination. They are never candidate objects. Other filenames are never
cleanup targets. Initialization requires an absent root and an existing non-link
parent. A partially initialized existing root requires explicit human recovery;
resume/initialization never silently repairs it or replaces an invalid manifest.

`automatic_learning_contracts.py` defines:

* `SourceKeyV1`: family (`match`, `session`, `historical_review`) plus stable
  Product ID. `SourceVersionV1` adds source contract/version and exact retained
  content fingerprint. `SourceRecordV1.revision` is descriptive, not identity.
* `IdentityScopeV1`, `EntityReferenceV1`, `OriginBindingV1`: separate source-local
  namespaces or explicit shared identity claims, original Game/Player IDs and a
  required retained proof reference/validator version for origin/binding claims.
  A source-local namespace equals its logical source-key fingerprint. Independent
  future guided Reviews can retain the same `frontend-historical-review` and
  `frontend-forehand` literals without sharing identity. Corrections retain their
  source/scope. No label/prefix establishes origin, and **no retained binding is
  trusted by S1**; its future typed validator must validate the proof first.
* `SituationV1`: exact source-version, original Game/actor, decision index,
  observed Card and information cutoff; Session situations additionally require
  both original Checkpoint and accepted-Play fingerprints.
* `ObjectRefV1` / `ObjectEntryV1`: fixed area, kind, codec version, fingerprint,
  exact byte size and checked dependency references. The manifest must contain
  the exact acyclic root closure, without duplicate identities or dangling edges.
* `EvidenceEntryV1`: separate Decision, rollout and Historical classes. Its exact
  identity binds original source version and complete envelope reference, not its
  optional semantic fingerprint. Distinct exact envelopes remain distinct.
* `ExclusionV1`, `SkippedSituationV1`, `GenerationV1`: explicit exclusions/skips,
  complete ordered source/evidence selection, Corpus/Dataset IDs, Catalog revision,
  seed, partition weights, named adapter/builder versions and derived fingerprints.
  A descriptor selects at most one version per logical source and exactly its
  selected source/envelope dependencies. It stores no prepared artifact bundle.
* `ManifestV1`: stable generated automatic-space ID, revision, closed object index,
  archived source versions, binding claims, evidence index, source exclusions,
  separately nullable current and previous generation descriptors. Retirement
  never promotes a previous descriptor into current.

SHA-256 domains start with `skatmind\0automatic_learning\0` and separately identify
logical sources, source versions, execution bindings, origin bindings, objects,
manifests and cleanup inventories. Paths, filenames, labels and timestamps are
not source identity. Filesystem stamps only detect mutation and guard cleanup.
Original Request/Result IDs and bytes are not rewritten. Later adapters may retain
exact delivered payloads inside their own envelopes without changing public bytes.

`StoredObjectV1` in `automatic_learning_objects.py` validates only the storage
envelope and finite opaque payload. Reserved source/report discriminators are
listed in `SOURCE_KINDS` and `REPORT_KINDS`; future/unknown codecs are not silently
accepted as compatible execution contracts. Generation descriptors have a strict
structural decoder, but they cannot authorize derived output or evidence admission.

## Limits, coordination and commit boundary

Production constants are independently tested:

* **16,777,216 bytes** per stored source/envelope (also applied to descriptors),
  with a separately bounded **16 MiB manifest** read/write;
* **536,870,912 bytes** of retained objects and staged object work across all three
  object directories, including old dependencies, complete orphans and interrupted
  object temporaries;
* **2,048** indexed ordinary Decision entries, **2,048** rollout entries and
  **2,048** Historical entries, each globally per automatic space;
* current plus one previous generation descriptor;
* one active preparation candidate per owner, with explicit supersession.

The manifest/coordination metadata is separate from retained object accounting.
This permits a manifest-first cleanup at the exact object quota. Old unreferenced
generation objects still count as retained bytes until explicit cleanup. Existing
over-limit stores can be inspected and reduced; no data is silently truncated.
`StoreLimitsV1` permits only smaller injected limits for focused tests.

All owners for the same root inode share a process-local mutation lock, pending
byte reservations and reader pins. Equal pending objects reserve their missing
bytes once; distinct reservations must fit together. A nonblocking OS advisory
lease (`msvcrt` on Windows, `flock` on Linux) blocks other cooperating processes'
mutations while a mutation, candidate or reader pin is active. Busy publication,
manifest and cleanup commits return `conflict`; reservation/preview/pin boundaries
raise `StoreBusyError`. No waiting/retry/merge loop is introduced. Process death
releases the OS lease. This is local cooperation, not distributed coordination or
protection against uncontrolled writers bypassing the service.

All owned paths and ancestors must be regular non-link directories/files;
symlinks, Windows junctions and reparse points are rejected. Open-file identity
and post-read stamps are checked. Reads request at most `limit + 1` bytes even
after a successful size check. No unbounded Corpus file-reader is reused.

Publication flushes/fsyncs a same-directory temporary, then uses a hard-link
no-clobber publication and validates an occupied winner. Differing/corrupt winners
are never overwritten. Complete dependency objects precede their manifest
references. Updates validate newly introduced references and their whole closure;
unchanged quarantined entries may remain while independent entries are removed or
added. A new generation cannot use a corrupt/missing dependency.

The expected manifest is checked on entry and again immediately before atomic
`os.replace`. Exact unchanged content is idempotent without a revision bump.
**Replacement is the commit boundary.** Before replacement, failure preserves the
old authoritative manifest; complete unreferenced objects are orphans. After
replacement, even a failed return, process-local installation or subsequent load
leaves the new manifest authoritative. No rollback path removes a committed
manifest or overwrites another writer's newer commit. Directory fsync is
best-effort where the operating system does not support it.

## Restart, quarantine and explicit cleanup

Resume creates a new owner and validates all referenced objects/dependencies.
Invalid top-level structure, versions, references or fingerprint block the store
with value-free errors. The manifest is never replaced by an empty one.
Individual objects report `missing` or `corrupt` storage status; independently
intact entries remain available for storage inspection. Consumption statuses
distinguish those failures, `dependency_unavailable` and `unsupported`. In S1,
`available_evidence_ids` and `trusted_binding_ids` are always empty. Unknown
source/Report/producer contracts require later typed adapters. No evaluator,
reconstruction or derived preparation runs on resume or passive reads.

Default cleanup touches only owned unreferenced immutable objects/temporaries.
Explicit evidence removal retires every dependent current/previous descriptor
before deletion. Original source records remain retained until separately
released; releasing a source still needed by another Report is rejected. Reader
pins and active candidate dependencies remain protected. Exact preview ownership,
manifest fingerprint, process epoch and full file inventory are rechecked.
Competing work conflicts. Deletion rechecks the authoritative manifest and each
file immediately before unlinking. Interrupted deletion leaves only harmless
unreferenced remnants. No recordings, independent collections, external exports,
unknown filenames or linked paths are cleanup targets. Cleanup never runs on
startup and has no age-based eviction policy or UI in S1.

## Development validation and affected-module inventory

Development interpreter: CPython **3.13.7**, outside the installed UAT environment.
The ambient `python` executable was an App Execution Alias; use `py -3.13` and the
documented PowerShell function binding for Quick. Every validation invocation uses
a 7,200,000 ms harness timeout. Logs, pytest caches and disposable evidence stay
outside the repository: pytest evidence under `%TEMP%\opencode`, and Quick logs
under `%TEMP%\skatmind-check-*`.

The complete affected inventory is **15 test modules**:

* New service/contract/lifecycle/integration coverage:
  `test_automatic_learning_contracts.py`, `test_automatic_learning_store.py`,
  `test_automatic_learning_lifecycle.py`, `test_automatic_learning_managed_service.py`.
* Managed-home/discovery contract compatibility:
  `test_unified_local_app_contracts.py`, `test_unified_local_app_managed_items.py`.
* Existing persistence-byte/codec/contract compatibility:
  `test_session_persistence.py`, `test_session_persistence_codec.py`,
  `test_session_persistence_contracts.py`, `test_match_workspace_persistence.py`,
  `test_match_workspace_persistence_codec.py`, `test_match_workspace_persistence_contracts.py`,
  `test_learning_corpus_persistence.py`, `test_learning_corpus_persistence_codec.py`,
  `test_learning_corpus_persistence_contracts.py`.

This inventory follows the new service's only existing Product dependency
(`ManagedHomeV1`), the preserved discovery categories and the three explicit
persistence compatibility requirements. No existing runtime caller is rewired.
The byte-preservation test creates valid synthetic Session/Match/manual-Corpus
fixtures and compares their bytes around initialization, publication, resume and
cleanup, with analysis/preparation entry points prohibited. Storage fixtures are
synthetic opaque JSON; they execute no card evaluator.

None of these modules is in the four-module exclusive validation set. No browser,
JavaScript-disabled, zoom or accepted UAT sequence retest is introduced. Local Full,
distribution builds and unrelated suites are excluded by this task's explicit
validation boundary. The execution record below distinguishes intermediate passes,
corrections, repeats and final results.

### Local execution record (2026-11-01)

**Locally validated; exact-commit hosted CI and maintainer installed service
acceptance pending.** Expected and actual branch are
`feat/309-automatic-learning-store`. Expected starting, actual starting and final
HEAD are all `e80af537c8ad37215ac5ece65b3faa50c99604d9`. The starting worktree was
clean; there was no baseline substitution. Changes remain unstaged/uncommitted.

| Invocation | Actual outcome | Elapsed |
| --- | --- | ---: |
| Four new modules, focused pass 1 | 95 passed, 3 skipped | 16.90 s |
| Four new modules, focused pass 2 after lifecycle additions | 99 passed, 3 skipped | 20.93 s |
| Four new modules, focused pass 3 after cleanup/path/process coverage | 103 passed, 3 skipped; two Windows console-decoding thread warnings | 22.17 s |
| Junction-only correction, warnings as errors | 2 passed, 29 deselected, no warnings | 0.50 s |
| All 15 complete affected modules, first pass | 359 passed, 4 skipped | 23.05 s |
| Quick, first pass | Ruff, schema parity and input examples passed | 4.447 s |
| Final-review candidate-release/resume-race tests | 2 passed, 31 deselected | 0.86 s |
| All 15 complete affected modules, final repeat after those two fixes | **361 passed, 4 skipped** | **14.75 s** |
| Quick, final repeat | **Passed**: Ruff 0.128 s, parity 0.084 s, examples 2.793 s | **3.405 s** |

The final inventory contains **365 distinct tests**, including 108 new-module
tests (105 passed, 3 skipped). Repeats above are not additional distinct coverage.
Across seven pytest invocations there were 1,021 passing executions and 17 skip
events: 361 distinct passing tests and four distinct skipped tests. No pytest
invocation failed. Four actual symlink checks were skipped for this Windows
account's missing symlink privilege (three new tests and one existing managed-item
test); the two actual Windows junction checks passed. Junction subprocess output
was changed to binary capture to remove the intermediate console-encoding warnings.
The final affected pass had no warnings. No exclusive module was affected/run;
both parallel-worker runs completed before subsequent checks.

Three standalone focused Ruff invocations preceded Quick: the first found 25
style/import issues, the second found two remaining line-length issues, and the
third passed. Both Quick Ruff stages then passed. The initial ambient `python`
environment probe failed because it was an App Execution Alias; the development
`py -3.13` probe succeeded. Neither is a pytest result. No local Full, unrelated
suite, distribution/install/UAT build, hosted CI or installed acceptance was run.

For readability the following commands use `$E` for the exact external evidence
prefix and PowerShell arrays for the **same expanded module order and arguments**
used in the invocations:

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$Focused = @(
  'tests/test_automatic_learning_contracts.py',
  'tests/test_automatic_learning_store.py',
  'tests/test_automatic_learning_lifecycle.py',
  'tests/test_automatic_learning_managed_service.py'
)
$Affected = $Focused + @(
  'tests/test_unified_local_app_contracts.py',
  'tests/test_unified_local_app_managed_items.py',
  'tests/test_session_persistence.py',
  'tests/test_session_persistence_codec.py',
  'tests/test_session_persistence_contracts.py',
  'tests/test_match_workspace_persistence.py',
  'tests/test_match_workspace_persistence_codec.py',
  'tests/test_match_workspace_persistence_contracts.py',
  'tests/test_learning_corpus_persistence.py',
  'tests/test_learning_corpus_persistence_codec.py',
  'tests/test_learning_corpus_persistence_contracts.py'
)
py -3.13 -m pytest @Focused -q -p no:cacheprovider --basetemp "$E\309-focused-1" --junitxml "$E\309-focused-1.xml"
py -3.13 -m pytest @Focused -q -p no:cacheprovider --basetemp "$E\309-focused-2" --junitxml "$E\309-focused-2.xml"
py -3.13 -m pytest @Focused -q -p no:cacheprovider --basetemp "$E\309-focused-3" --junitxml "$E\309-focused-3.xml"
py -3.13 -m pytest tests/test_automatic_learning_store.py -k windows_junctions -q -W error -p no:cacheprovider --basetemp "$E\309-junction-retest" --junitxml "$E\309-junction-retest.xml"
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\309-affected" --junitxml "$E\309-affected.xml"
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
py -3.13 -m pytest tests/test_automatic_learning_store.py -k "unchanged_commit_releases or resume_detects_manifest_change" -q -p no:cacheprovider --basetemp "$E\309-final-lifecycle" --junitxml "$E\309-final-lifecycle.xml"
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\309-affected-final" --junitxml "$E\309-affected-final.xml"
.\scripts\check.ps1 -Mode Quick
```

Standalone Ruff used `py -3.13 -m ruff check` with the six new production modules,
`tests/automatic_learning_helpers.py` and the four new test modules. Quick evidence
directories are `%TEMP%\skatmind-check-ybn629wo` (first) and
`%TEMP%\skatmind-check-lj6695rd` (final). The final Quick source digest is
`554ddc3eb94cc6291c0e6ab40aa79d9da0526e5c0fb326b20ba70a67306efda9`; this execution
record was added afterward as documentation only. The final review includes every
changed/new file and whitespace checking of tracked and untracked additions.
`git diff --check` passed. Untracked files were checked with
`git diff --no-index --check -- NUL <file>` and produced no diagnostics. The first
wrapper incorrectly treated the normal no-index difference exit code `1` as a
whitespace failure; the corrected wrapper accepts `0`/`1` only with empty output
and passed for all twelve new files. This was a check-wrapper correction, not a
source whitespace defect.

## Strict-resume consistency correction (Issue #309 follow-up)

This is a bounded S1 correction on the expected/actual branch
`feat/309-automatic-learning-store`, starting at
`b2d0bb95c9029666e0c3934f03df7178132811d4` with a clean worktree. The maintainer
reported that branch CI run `41352058480` passed all 23 jobs for that commit.
That evidence does not cover this subsequent correction. The historical S1
execution record above and #308's documentation-only acceptance remain unchanged.

### Confirmed finding and correction

Before Product edits, an external synthetic reproduction on development CPython
**3.13.7** confirmed both published-code findings:

1. A Match `SourceRecordV1` referenced an exact object with known kind
   `session_source`.
2. A Match `EvidenceEntryV1` used evidence class `rollout` while referencing its
   exact known `match_decision` envelope.

Both had valid object bytes, dependency references and manifest fingerprints.
Normal publication rejected both, but manifest construction, `resume_manifest`
and full `resume_automatic_learning_store_v1` accepted them. After resume, the
unchanged update returned `unchanged`. The reproduction also verified that all
disposable store bytes remained unchanged by those operations.

`ManifestV1` now shares a private known-kind compatibility check for its source
and evidence bindings. Existing codec and publication paths already reconstruct
this contract. `manifest_bytes` also revalidates the contract before serialization,
including defensively supplied inconsistent in-memory values. Known contradictory
bindings fail with the existing value-free diagnostics:

* `Source family and stored kind disagree.`
* `Evidence family and stored kind disagree.`

A future codec version does not erase a known kind's family/class meaning.
Unfamiliar future kinds and compatible known kinds with unfamiliar codec versions
remain retainable as unsupported. The existing stricter publication restriction
on **newly introduced unfamiliar kinds** remains unchanged; retaining such an
already archived unsupported entry does not admit genuine Report evidence.

Malformed wire regression fixtures calculate their fingerprints independently of
the strengthened manifest constructor/serializer. Tests cover constructor/codec
rejection, defensive serialization and publication rejection, full resume and
the formerly accepted unchanged-update path. Rejected loading preserves the exact
manifest, object files and directory inventory. Positive cases cover all six
reserved source-family/evidence-class combinations plus unfamiliar source kinds,
envelope kinds and codec versions. All remain outside semantic Report/trusted
binding admission. Valid canonical manifest bytes are preserved.

The two Product edits are confined to `automatic_learning_contracts.py` and
`automatic_learning_objects.py`. Store transactions, identity rules, dependency
closure, no-clobber/CAS, post-commit preservation, quotas, candidates, reader pins,
cleanup and existing recording/manual-Corpus persistence are unchanged. No S2–S7
adapter, UI, public API, storage feature or migration is introduced.

### Follow-up validation inventory and evidence

The complete affected inventory is exactly:

* `tests/test_automatic_learning_contracts.py`
* `tests/test_automatic_learning_store.py`
* `tests/test_automatic_learning_lifecycle.py`
* `tests/test_automatic_learning_managed_service.py`

The contract is consumed only by the private object/IO/store modules. The only
existing integration caller is `app_web/automatic_learning.py`, covered by the
managed-service test, including its unchanged Session/Match/manual-Corpus byte
checks. Import/caller inspection found no additional affected test module or
exclusive module. The broader initial S1 compatibility inventory above is
historical evidence, not a reason to rerun unrelated modules for this fix.

All commands use development CPython 3.13 and a 7,200,000 ms harness timeout.
The baseline reproduction script, pytest XML and disposable stores are outside
the repository under `%TEMP%\opencode`. No real managed data, installed UAT,
installed service smoke, browser retest, local Full or unrelated suite was used.
**Locally validated; new exact-commit hosted CI and maintainer installed service
acceptance pending.** Starting/current HEAD remains
`b2d0bb95c9029666e0c3934f03df7178132811d4`; all six intended changed files remain
unstaged/uncommitted. The changed-file inventory is:

* `src/skatmind/automatic_learning_contracts.py`
* `src/skatmind/automatic_learning_objects.py`
* `tests/automatic_learning_helpers.py`
* `tests/test_automatic_learning_contracts.py`
* `tests/test_automatic_learning_store.py`
* `docs/automatic_learning_store.md`

| Invocation | Actual result | Elapsed |
| --- | --- | ---: |
| External pre-Product-edit baseline reproduction | 2 passed, confirming both gaps and publication rejection | 5.64 s |
| New rejection regressions before Product edits | 8 expected failures, 2 publication-rejection passes, 86 deselected | 1.00 s |
| Focused corrected negative/positive compatibility cases | 20 passed, 76 deselected | 3.72 s |
| Four complete automatic-Learning modules, two file-grouped workers | **125 passed, 3 skipped** | **14.47 s** |
| Explicit `.\scripts\check.ps1 -Mode Quick` | **Passed** | **28.377 s** |

The final suite comprises **128 distinct repository tests**, including all 20 new
regression/compatibility cases. The focused 20 are repeated coverage within that
complete pass, and the initial red 10 are a subset of those 20. The two external
baseline reproduction cases are separate historical-defect evidence, not extra
corrected-suite coverage. The three complete-suite skips are the existing actual
symlink checks unavailable to this Windows account; actual Windows junction tests
passed. The final complete pass had no failures or warnings. No exclusive module
was affected, and the workers exited before Quick.

One standalone targeted Ruff invocation found three test-only line-length issues;
they were corrected before the complete-module pass. The final Quick Ruff stage
passed in 0.229 s, packaged-schema parity in 0.129 s, and input examples in 2.846 s.
Quick's reported total wall time was 28.377 s; the remaining overhead is not
attributed to an individual stage. No other intermediate failure occurred in this
follow-up. The expected pre-correction regression failures are recorded separately
above. Final `git diff --check` and changed-file review passed.

Commands below use `$E` only to abbreviate the exact external path; module order,
flags, arguments and evidence filenames match the actual invocations:

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
py -3.13 -c "import sys; print(sys.executable); print(sys.version)"
py -3.13 -m pytest "$E\test_309_strict_resume_baseline.py" -q -s -p no:cacheprovider --basetemp "$E\309-resume-baseline" --junitxml "$E\309-resume-baseline.xml"
py -3.13 -m pytest tests/test_automatic_learning_contracts.py tests/test_automatic_learning_store.py -k known_binding_mismatch -q -p no:cacheprovider --basetemp "$E\309-resume-red" --junitxml "$E\309-resume-red.xml"
py -3.13 -m pytest tests/test_automatic_learning_contracts.py tests/test_automatic_learning_store.py -k "known_binding_mismatch or known_binding_combinations or future_bindings" -q -p no:cacheprovider --basetemp "$E\309-resume-focused" --junitxml "$E\309-resume-focused.xml"
py -3.13 -m ruff check src/skatmind/automatic_learning_contracts.py src/skatmind/automatic_learning_objects.py tests/automatic_learning_helpers.py tests/test_automatic_learning_contracts.py tests/test_automatic_learning_store.py
py -3.13 -m pytest tests/test_automatic_learning_contracts.py tests/test_automatic_learning_store.py tests/test_automatic_learning_lifecycle.py tests/test_automatic_learning_managed_service.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\309-resume-complete" --junitxml "$E\309-resume-complete.xml"
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Quick logs are in `%TEMP%\skatmind-check-xgtho0m4`. Its source digest is
`0a02cc8e919c70ed3b1c649599605556672a81f78d6450f8c40bce39f2dbe474`; these final
documentation-only results were appended after that check. Local Full was not run
under the explicit follow-up validation boundary. New hosted CI and installed
service acceptance were not performed or claimed.

Keep #309 open for new exact-commit branch/main `check` and
`v1-supported-platform-matrix` evidence and maintainer installed service
acceptance. Accepted #292–#307 scopes and #308's documentation acceptance remain
intact. #208 remains open; UAT-01 is not globally accepted, formal UAT-02–12 remain
paused, and release preparation is not authorized.

## Maintainer-only installed service smoke (documented, not executed here)

After exact-commit hosted gates, use an independently installed build's CPython
3.13 interpreter, from an external directory, with a **new disposable data home**.
This is an installed private-service acceptance check, not a public CLI or a
browser/UAT-sequence test. The agent does not build, install or launch it.

1. Create a fresh `%TEMP%\skatmind-309-smoke-<unique>` home containing only valid
   **synthetic** Session and Match persistence fixtures in `sessions/` and
   `matches/`. Use the existing installed persistence APIs or previously prepared
   synthetic fixtures; do not copy real managed data. Keep the fixture filenames
   and expected bytes for the receipt.
2. Save the following as an external `store-smoke.py`. Run it with the installed
   interpreter and that disposable home, with no checkout `PYTHONPATH`:

   ```powershell
   & $InstalledPython "$env:TEMP\store-smoke.py" $DisposableHome
   ```

   ```python
   import sys
   from pathlib import Path
   from unittest.mock import patch

   import skatmind.automatic_learning_io as io
   from skatmind.app_web.automatic_learning import (
       initialize_managed_automatic_learning_v1,
       resume_managed_automatic_learning_v1,
   )
   from skatmind.app_web.managed_data import prepare_managed_home_v1
   from skatmind.automatic_learning_codec import canonical_json
   from skatmind.automatic_learning_objects import StoredObjectV1
   from skatmind.learning_corpus_persistence import initialize_learning_corpus_directory_v1

   home = prepare_managed_home_v1(Path(sys.argv[1]))
   assert tuple(home.category("sessions").path.glob("*.json"))
   assert tuple(home.category("matches").path.glob("*.json"))
   initialize_learning_corpus_directory_v1(
       home.category("corpora").path / "manual-smoke", corpus_id="synthetic-manual"
   )
   before = {p: p.read_bytes() for category in home.categories
             for p in category.path.rglob("*") if p.is_file()}
   store = initialize_managed_automatic_learning_v1(home)
   original = store.snapshot().manifest
   assert resume_managed_automatic_learning_v1(home).snapshot().manifest == original
   obj = StoredObjectV1(area="sources", kind="match_source", codec_version=1,
                       payload=canonical_json({"synthetic_storage_probe": True}))
   candidate = store.begin_candidate((obj,))
   original_write = io.write_temporary

   def interrupted(directory, raw):
       original_write(directory, raw[:20])
       raise OSError("synthetic staged-write interruption")

   try:
       with patch.object(io, "write_temporary", interrupted):
           store.publish_object(obj, candidate=candidate)
   except OSError:
       pass
   else:
       raise AssertionError("Expected the injected interruption")
   finally:
       store.release_candidate(candidate)
   reopened = resume_managed_automatic_learning_v1(home)
   result = reopened.snapshot()
   assert result.manifest == original
   assert result.available_evidence_ids == ()
   assert len(result.temporary_names) == 1 and result.orphan_names == ()
   assert all(path.read_bytes() == raw for path, raw in before.items())
   print("PASS: initialize/reopen, interrupted staging, manifest and existing bytes")
   ```

3. Record installed package path/version, exact commit/build identity, interpreter,
   disposable path, synthetic fixture identities and actual assertions/output.
   Optionally preview/commit cleanup against the reopened manifest to remove the
   owned partial temporary. Retain the receipt outside the repository. The expected
   output above is an instruction, **not an executed acceptance result**.

## Remaining stages

S2 must supply genuine Match Decision capture/resume with exact original-source
validation and retained bytes. S3 supplies the separate rollout codec/capture.
S4 supplies complete automatic discovery, authoritative selection, original-source
eligibility, recipe execution and generation/final-delivery guards. S5 supplies
the bilingual player-facing workflow and maintenance controls. S6/S7 supply native
Session and saved Historical Review adapters, including validated guided origin
and source-local identity retention. None is completed by this foundation.
