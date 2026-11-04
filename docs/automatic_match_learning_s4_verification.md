# Automatic Match Learning service and verification (Issue #312, S4)

## Scope and acceptance boundary

S4 implements one explicit private Match-only service over saved managed recordings
and retained S2/S3 evidence. The baseline is branch
`feat/312-automatic-match-learning`, HEAD
`9b9b66c3289c222f284d737d122f15c4b5f5c124`, with a clean starting worktree. The
complete Issue #312 description was inspected through read-only `gh issue view`.
There is no baseline substitution. Product code changes; all changes remain
unstaged and uncommitted for maintainer review.

Accepted #292–#311 scopes and #308's documentation acceptance remain historical
facts. S4 does not complete automatic Learning integration. S5 owns the ordinary
bilingual routes/forms and maintenance UI; S6/S7 own native Session and Historical
adapters. Recommendation adaptation remains a later goal. Keep #312 open for new
exact-commit branch/main `check` and `v1-supported-platform-matrix` and subsequent
maintainer installed service acceptance. #208 stays open, UAT-01 is not globally
accepted, formal UAT-02–12 remain paused, and release preparation is not authorized.

## Private entry and result lifetime

`skatmind.app_web.automatic_match_learning.AutomaticMatchLearningServiceV1.open(app)`
attaches a fresh preparation owner to an existing `AppWebContextV1`. Opening does
not initialize the archive or prepare artifacts. The only preparation action is
`service.update()`. There are no startup, browser, CLI or background callers.

* `inspect()` performs read-only source/archive validation. Statuses distinguish
  `missing`, `current`, `outdated`, `reconstruction_needed`, `deleted`, `excluded`,
  `unsupported`, and `conflict`.
* `update()` returns `prepared`, `rebuilt`, or `reused` on success; failures include
  `conflict`, `quota`, `failed`, `unsupported`, `unconfirmed`, and committed but
  non-installed `reconstruction_needed` / `committed_superseded` outcomes.
* `consume(projector, allow_outdated=False)` authorizes the exact retained bundle,
  pins archived dependencies, runs projection outside app/Product locks, then
  rechecks source, root, archive, owner, attempt and generation before return.
* `download(kind, allow_outdated=False)` uses that same guard for the unchanged ten
  canonical Match download types. A returned immutable value is for immediate
  delivery; it is not a capability for a later request.

An intact captured prior bundle requires explicit `allow_outdated=True`. Confirmed
absence of any included identity hides the whole aggregate. An unidentified invalid
live replacement also hides the old aggregate conservatively: it cannot prove that
the old Product still exists. No filtered old aggregate is presented with stale
totals. Restart establishes a new owner, rediscovers live membership, reports
reconstruction needed, and rebuilds only on an explicit Update.

## Authoritative membership and exact evidence

`app_web/automatic_match_inventory.py` performs two complete bounded captures of
direct `.json` children, with owned-root/ancestor identities, regular-file checks,
non-traversal of links/junctions/reparse points/hardlinks, bounded reads and content
digests. It rejects more than 2,048 candidates, reads above 16 MiB per file or
512 MiB aggregate, inaccessible roots/files, interrupted enumeration and unstable
contents. These are failures, not evidence of deletion. Stable nonregular/invalid
entries have safe diagnostics without inferred Product IDs or labels. Future
document kinds/versions are unsupported, without inferred identity.

Every candidate, including invalid, duplicate and explicitly excluded candidates,
participates in final freshness checks. The browser discovery list and its refresh
counter are not used as authority. Two valid files claiming one Match are ambiguous
even when their bytes match. Neither timestamps nor revision ordering select a
winner. The sole unambiguous exact saved version replaces the entire contribution,
including same-revision corrections and restored lower revisions.

Every selected recording uses `build_managed_match_source` unchanged: original
codec-2 source bytes/header, persistence content identity and genuine original
Snapshot. Empty/passed/partial/complete coverage is admitted without requiring a
Report. Dataset reconstruction and skips remain the existing builders' decisions.
Manual Corpus copies are outside this inventory.

Retained evidence must match the exact selected source version and pass the existing
typed ordinary/rollout admission. The ordinary source store deduplicates exact
Teacher bindings, preserving distinct executed variants and semantic consensus.
All four methods and executed limited Search remain eligible. Complete rollouts
use `build_debrief_projection`; unavailable/partial/timeout/cancelled executions
remain separate availability values. They never enter Teacher/Dataset labels or
complete-Search focus qualification. Missing/corrupt/unsupported dependencies are
quarantined explicitly; a valid live file does not silently repair its archive.

## Recipe, storage and coordination

`automatic_match_preparation.py` creates an isolated in-memory Corpus from selected
Snapshots, reuses the existing ordinary/Tactical/Coaching preparation and ten
serializers, and adds separate rollout comparisons/availability and coverage.
Corpus/Dataset IDs derive from the stable automatic-space ID. Source order is
logical Match-ID order, evidence order is exact execution-ID order, and the existing
Teacher builder retains its own canonical order. Both partition seeds are `0` and
weights are `70/15/15`. Catalog revision advances only when the selected source set
changes; evidence-only updates and restart rebuilds do not gratuitously advance it.

The narrow private evolution is **generation object codec 2**, containing the
existing `GenerationV1` recipe plus exact inventory/evidence outcome ledgers and
their input fingerprint. Manifest/storage envelope versions and S2/S3 object bytes
remain unchanged. Codec-1 generation fixtures remain storage-only. Semantic
`admit_generation` requires the exact supported producer/adapter/builder recipe,
IDs, seed/weights, ordering, selected identities, exclusions and complete fingerprint
family set. A compatible restart rebuild must reproduce the entire descriptor,
including skips and every derived fingerprint, before installation.

Prepared objects/bytes are disposable process-local values. Dependencies publish
first, followed by one manifest CAS for the complete current/previous descriptor
rotation. Retired descriptor objects remain orphans; archived sources/Reports remain
retained. No implicit cleanup, repair, eviction, rebinding or retry occurs.

S4 uses a distinct `AutomaticLearningStoreV1` reservation owner sharing the existing
root coordinator, quota accounting, OS lease and reader pins. It cannot supersede
S2/S3 pending reservations. Preparation runs outside app/Product locks. The final
publication order is app lock → saved-source barrier → archive transaction; accepted
writes use Product lock → optional short app lock → saved-source barrier. S4 never
holds a Match lock and a Corpus lock together.

Manifest replacement is authoritative even when synchronization/return fails.
The service inspects authoritative state before installation, never rolls back a
commit and never installs a descriptor merely because it remains `previous` after
a newer writer. A crash after commit leaves reconstruction needed. An unchanged
in-process Update reuses its bundle and writes nothing; an explicit restart rebuild
also writes nothing when its exact supported descriptor still matches.

### Accepted mutation audit

The actual save call graph has two callers of `save_match_workspace_file_v1`:
`capture_web/context.py::save_candidate` and managed import in
`app_web/match_frontend.py`. `capture_web/operations.py::_persist_change` covers
creation, Game setup, declaration/card evidence, Plays/truncation, passed/clear,
metadata, statistics, Commentary and response links. Managed normal/profile-driven
creation enters that same Capture path. `app_web/match_recovery.py::apply_match_recovery`
also uses `save_candidate` for correction/rewind. Every accepted atomic replacement
now increments the shared directory-owned source generation under its barrier;
unchanged/conflicting saves do not. Serialization/domain validation remains outside
that barrier.

The separate accepted deletion path is
`app_web/recording_deletion.py::apply_recording_deletion`. Match deletion rechecks its
exact preview digest under the same barrier, unlinks once and increments the source
generation. Session deletion retains its existing path. Reload, opening, selection,
profile labels, analysis publication and manual Snapshot import do not mutate saved
Match bytes; archive evidence mutations are independently protected by manifest CAS.
No route/form, engine option, public Schema/API or dependency changes.

## Verification environment and affected inventory

Development interpreter: CPython **3.13.7**,
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
Every validation tool invocation uses **7,200,000 ms** timeout. Disposable homes,
pytest XML and temporary directories are under
`C:\Users\HENNIN~1\AppData\Local\Temp\opencode` (`$E` below). No real managed data or
installed maintainer environment is accessed.

The complete affected inventory follows the nine Product files and their actual
callers: archive contracts/transactions and both retained families; Match save,
create/import/recovery/delete; app context/help and source packaging; isolated
preparation, exact exports, manual independent-copy lifetime and existing qualification.
The 40 complete parallel modules below run with two file-grouped workers. The
complete standalone Corpus transport module exercises unchanged preparation/download
compatibility and is exclusive; it runs serially after the workers exit. Other
historical UI suites are not replayed. No new browser interaction is introduced.

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$Affected = @(
  'tests/test_automatic_match_learning.py',
  'tests/test_automatic_match_learning_evidence.py',
  'tests/test_automatic_learning_contracts.py',
  'tests/test_automatic_learning_store.py',
  'tests/test_automatic_learning_lifecycle.py',
  'tests/test_automatic_learning_managed_service.py',
  'tests/test_automatic_match_evidence.py',
  'tests/test_automatic_match_rollout_evidence.py',
  'tests/test_match_evidence_retention.py',
  'tests/test_match_rollout_retention.py',
  'tests/test_saved_match_analyses_web.py',
  'tests/test_saved_match_rollouts_web.py',
  'tests/test_match_workspace_persistence.py',
  'tests/test_match_workspace_persistence_codec.py',
  'tests/test_match_workspace_persistence_contracts.py',
  'tests/test_local_match_capture_web.py',
  'tests/test_local_match_capture_web_statistics.py',
  'tests/test_local_match_capture_web_analysis.py',
  'tests/test_unified_local_app_managed_items.py',
  'tests/test_unified_local_app_contracts.py',
  'tests/test_unified_local_app_web.py',
  'tests/test_profile_driven_match_creation.py',
  'tests/test_profile_driven_creation_web.py',
  'tests/test_match_recording_recovery.py',
  'tests/test_match_recording_recovery_web.py',
  'tests/test_recording_deletion_files.py',
  'tests/test_recording_deletion_lifecycle.py',
  'tests/test_recording_deletion_web.py',
  'tests/test_app_cli.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_learning_corpus_web_core.py',
  'tests/test_learning_corpus_import.py',
  'tests/test_learning_direct_entry.py',
  'tests/test_learning_direct_entry_web.py',
  'tests/test_match_debrief.py',
  'tests/test_learning_corpus_tactical_coaching.py',
  'tests/test_learning_corpus_strategy_teacher.py',
  'tests/test_learning_dataset_v2.py',
  'tests/test_learning_corpus_tactical_motif.py'
)
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\312-affected" --junitxml "$E\312-affected.xml"
py -3.13 -m pytest tests/test_local_learning_corpus_web.py -q -p no:cacheprovider --basetemp "$E\312-exclusive" --junitxml "$E\312-exclusive.xml"
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
```

Packaging regressions inspect source metadata/resources and registry snippets;
they do not build/install distributions. Quick covers Ruff, packaged-schema parity
and input examples only. Local Full, distribution builds/installations, unrelated
suites, hosted Actions and installed UAT are outside this task's executed boundary.

## Later maintainer installed service scenario (instructions only)

After exact-commit hosted gates, use a separately installed build and its development-
independent interpreter from an external directory, with a **new disposable home**.
Record build/commit/module/interpreter identity. This is private-service acceptance,
not S5 browser acceptance or a resumption of the paused formal UAT sequence.

1. Save two synthetic Matches, one partial, and retain existing genuine ordinary
   and rollout evidence through the accepted S2/S3 workflow. Make an independent
   manual collection with an explicitly selected original copy. Capture all recording,
   manual Catalog/Snapshot and native S2/S3 export bytes. Start execution counters
   only after those explicit fixture analyses have finished.
2. Construct an installed `AppWebContextV1` for that home, open the S4 service and
   explicitly Update. Assert exactly two selected source versions, exact original
   evidence eligibility, truthful partial skips, separate rollout availability and
   complete comparisons. Capture recipe/IDs and all ten canonical bytes/digests.
3. Stop the process. Reopen the same disposable home in a new process. Passive
   Inspect must say reconstruction needed and execute/write nothing. Explicit
   Update must rebuild identical recipe, Catalog revision and ten download bytes,
   with zero new analysis and no gratuitous manifest publication.
4. Correct one saved Match, including an equal/lower numeric revision fixture if
   desired. Prior intact output becomes outdated. Update replaces exactly one
   source version; old Reports stay archived and are excluded as `non_current`.
   It never appends old and corrected Decisions together.
5. Delete the other editable recording through the supported deletion operation.
   The prior aggregate is hidden. Update selects exactly one source and reports the
   deleted logical source as missing. Independent manual bytes and Current selection
   remain identical, and original archived native S2/S3 downloads still match.
6. Make another controlled correction, inject an external harness-only failure
   before manifest replacement, then explicitly retry once after disabling it.
   Before commit the old descriptor remains authoritative; immutable staged objects
   may remain orphans. Retry reuses those objects and publishes one replacement.
   Separately interrupt after descriptor commit but before bundle installation;
   restart must require explicit deterministic reconstruction, without rollback.
7. Record exact replacement/exclusion/evidence/skip counts, native and ten-derived
   byte digests, preparation counts and archive-write deltas. Verify zero Application,
   evaluator, Search, rollout and Historical executions throughout steps 2–6, and
   unchanged manual data/selections/prepared values in surviving contexts.

This scenario is documented, not executed by the agent. CI and installed acceptance
must be reported separately from local source-tree verification.

## Actual local execution record

All results below are source-tree results with disposable fixtures. Times are
pytest console wall times, not performance promises. The final union contains
**1,050 distinct tests across 41 complete modules: 1,043 passing, seven skipped**.
The two new modules contribute **84 distinct tests: 83 passing, one skipped**.
The final lifecycle-only repeat follows the narrowly added malformed-ledger guard
and expanded operation accounting; it does not repeat the entire compatibility
inventory or add repeats to the distinct count.

| Evidence prefix | Actual outcome | Seconds |
| --- | --- | ---: |
| `312-red` | Five meaningful service regressions failed before implementation | 1.32 |
| `312-service-1` | 5 passed | 7.84 |
| `312-lifecycle-1` | 41 passed, 1 failed: future source classified invalid rather than unsupported | 35.10 |
| `312-evidence-1` | 9 passed, 7 failed: two wrong fixture field names and an attempted immutable-binding mutation | 343.35 |
| `312-focused-2` | 74 passed, 3 failed, 1 skipped: nonregular-entry digest tuple encoding (two cases), wrong manual-import status assertion | 738.30 |
| `312-boundary-red` | 5 passed, 2 failed, 1 skipped: unknown source kind and external hardlink admission, before corrections | 3.20 |
| `312-attempt-red` | 1 failed: missing in-flight consumption attempt revalidation, before correction | 1.34 |
| `312-lifecycle-2` | 56 passed, 1 skipped | 31.73 |
| `312-root-red` | 1 failed: an existing owner accepted a replacement Match root, before correction | 1.29 |
| `312-affected` | **1,014 passed, 7 skipped**, all 40 complete parallel modules | **1,100.69** |
| `312-exclusive` | **27 passed**, complete exclusive module after both workers exited | **15.81** |
| `312-shape-red` | 2 failed: malformed nullable generation ledgers escaped as TypeError, before correction | 1.88 |
| `312-final-lifecycle` | **59 passed, 1 skipped**, complete affected lifecycle module after final correction | **44.19** |

All 22 intermediate failed executions are resolved. Thirteen pytest invocations
contain **1,290 passing executions, 22 failed executions and 11 skip events**;
repeats are not extra distinct coverage. The earlier single future-source test
was subsequently expanded into version/kind parameters. The seven distinct skips
are actual symlink creation unavailable to this Windows account: one new inventory
case, three automatic-store cases, one managed-item case, one direct-entry case and
one deletion case. Actual Windows junction and hardlink cases passed. The complete
affected, exclusive and final lifecycle passes had no failures or warnings.

The malformed-ledger fix adds only an exact-array shape check before iteration in
semantic admission. Supported recipe/byte behavior stays as exercised by the full
affected run. The complete lifecycle repeat includes restart/all-ten-byte,
publication/fault/concurrency and final-delivery cases as well as both new rejection
cases. All changed/new Product, test and documentation files were reviewed.

Three standalone targeted Ruff invocations found 32 findings, then two findings,
then passed. These were import ordering, unused import, line length and one
test-only semicolon; all were corrected. Final Quick evidence is recorded below.
No local Full was run under this task's explicit validation boundary.

### Exact focused commands and evidence paths

Each prefix above names both `$E\<prefix>.xml` and its disposable pytest directory.
The following commands use the same flags, selectors and module order as executed:

```powershell
py -3.13 -c "import sys; print(sys.executable); print(sys.version)"
$Lifecycle = 'tests/test_automatic_match_learning.py'
$Evidence = 'tests/test_automatic_match_learning_evidence.py'
py -3.13 -m pytest $Lifecycle -q -p no:cacheprovider --basetemp "$E\312-red" --junitxml "$E\312-red.xml"
py -3.13 -m pytest $Lifecycle -q -p no:cacheprovider --basetemp "$E\312-service-1" --junitxml "$E\312-service-1.xml"
py -3.13 -m pytest $Lifecycle -q -p no:cacheprovider --basetemp "$E\312-lifecycle-1" --junitxml "$E\312-lifecycle-1.xml"
py -3.13 -m pytest $Evidence -q -p no:cacheprovider --basetemp "$E\312-evidence-1" --junitxml "$E\312-evidence-1.xml"
py -3.13 -m pytest $Lifecycle $Evidence -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\312-focused-2" --junitxml "$E\312-focused-2.xml"
py -3.13 -m pytest $Lifecycle -k 'future_source_contract or hardlink or nonregular or independent_manual' -q -p no:cacheprovider --basetemp "$E\312-boundary-red" --junitxml "$E\312-boundary-red.xml"
py -3.13 -m pytest $Lifecycle -k 'final_consumption and attempt' -q -p no:cacheprovider --basetemp "$E\312-attempt-red" --junitxml "$E\312-attempt-red.xml"
py -3.13 -m pytest $Lifecycle -q -p no:cacheprovider --basetemp "$E\312-lifecycle-2" --junitxml "$E\312-lifecycle-2.xml"
py -3.13 -m pytest $Lifecycle -k replaced_category_root -q -p no:cacheprovider --basetemp "$E\312-root-red" --junitxml "$E\312-root-red.xml"
# Complete $Affected and exclusive commands are listed above.
py -3.13 -m pytest $Lifecycle -k 'generation_tampering and shape' -q -p no:cacheprovider --basetemp "$E\312-shape-red" --junitxml "$E\312-shape-red.xml"
py -3.13 -m pytest $Lifecycle -q -p no:cacheprovider --basetemp "$E\312-final-lifecycle" --junitxml "$E\312-final-lifecycle.xml"
py -3.13 "$E\312-accounting.py"
```

The external accounting script reconciles all 13 XML receipts, final test identities
and actual skip reasons, and asserts no unresolved final failure. It executes no
Product code. Targeted Ruff used `py -3.13 -m ruff check` with these exact arguments:
`src/skatmind/app_web/automatic_match_inventory.py`,
`src/skatmind/app_web/automatic_match_learning.py`,
`src/skatmind/automatic_match_preparation.py`,
`src/skatmind/match_source_coordination.py`,
`src/skatmind/match_workspace_persistence.py`,
`src/skatmind/app_web/recording_deletion.py`,
`tests/test_automatic_match_learning.py`,
`tests/test_automatic_match_learning_evidence.py`.

## Operation and write accounting

The final complete S4 evidence module uses **16 explicit fixture Application
executions**, separately from S4: seven original-method fixtures, four controlled
Search assessment/elapsed variants for consensus, two controlled limited Search
fixtures, and three bounded/clock/cancellation rollout fixtures. Every fixture
retains its actual invocation and execution through the strict S2/S3 codec. The
controlled cases are identified in their test docstrings; they are not claims that
the solver proved the supplied semantic assessments. Across the earlier evidence
run, focused repeat and complete affected pass, these fixtures executed 7 + 16 + 16
= **39** times. Existing compatibility-module fixture executions are outside this
S4-only count and are not represented as zero.

**S4 has zero new Application, Immediate evaluator, bounded Search, information-set
Search, rollout or Historical execution calls.** The new evidence tests install
failing call guards at actual execution seams after fixture creation. Allowed
Snapshot/Request reconstruction, existing preparation builders, motif detection,
Teacher/Coaching reconciliation and canonical serialization remain separate work.

`test_successful_unchanged_and_restart_write_accounting` instruments successful
`write_temporary` calls and outer bundle preparation calls. Its final measured
sequence is:

| Explicit phase | Bundle builds | Source writes | Report writes | Generation writes | Manifest writes |
| --- | ---: | ---: | ---: | ---: | ---: |
| First Update, absent archive, one saved Match | 1 | 1 | 0 | 1 | 2 (initial + generation) |
| Unchanged Update and guarded download | 0 | 0 | 0 | 0 | 0 |
| Fresh-owner explicit restart rebuild | 1 | 0 | 0 | 0 | 0 |
| Update after same-revision correction | 1 | 1 | 0 | 1 | 1 |
| Update after confirmed deletion | 1 | 0 | 0 | 1 | 1 |
| Replacement source, injected failure before manifest bytes | 1 | 1 | 0 | 1 | 0 |
| One explicit retry | 1 | 0 | 0 | 0 | 1 |
| **Total** | **6** | **3** | **0** | **4** | **5** |

Initialization separately creates four archive directories and the one-byte
coordination file. Immutable no-clobber links and same-directory manifest replacement
consume the counted temporary payloads; lease activity and temporary unlinking are
not additional evidence writes. Recording creation/correction/deletion/replacement
are explicit disposable fixture actions, not S4 writes. Separate regressions prove
unchanged recording bytes, exact S2/S3 native exports, independent manual Catalog/
Snapshot bytes, `keep_current`, `reject`/`retain`, selected/prepared manual state and
all ten automatic canonical download bytes/fingerprints after restart.

## Complete intended file inventory

New Product modules:

* `src/skatmind/app_web/automatic_match_inventory.py`
* `src/skatmind/app_web/automatic_match_learning.py`
* `src/skatmind/automatic_match_preparation.py`
* `src/skatmind/match_source_coordination.py`

Modified Product modules:

* `src/skatmind/app_web/context.py`
* `src/skatmind/app_web/recording_deletion.py`
* `src/skatmind/automatic_learning_objects.py`
* `src/skatmind/automatic_learning_store.py`
* `src/skatmind/match_workspace_persistence.py`

New tests:

* `tests/test_automatic_match_learning.py`
* `tests/test_automatic_match_learning_evidence.py`

Directly affected documentation:

* `docs/automatic_match_learning_s4_verification.md` (new)
* `docs/automatic_learning_integration_contract.md`
* `docs/automatic_learning_store.md`
* `docs/ordinary_match_analysis_retention.md`
* `docs/match_rollout_analysis_retention.md`
* `AGENTS.md`

This is **17 intended files**. The external receipt-accounting script and validation
logs are outside the repository. Existing public contracts, engine behavior,
dependencies, S2/S3 native bytes and the ten canonical Match export formats retain
their meanings. No distribution, installed service or UAT environment was built,
installed or started; no Git/GitHub publication action occurred.

## Quick and final review receipt

The first explicit Quick invocation stopped at Ruff with one import-order finding
in the newly expanded operation-accounting test. It ran on development CPython
3.13.7 / Windows 11 and reported **19.608 s** total, Ruff **1.158 s**, exit `1`.
Its logs are `C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-8z2uuo33`.
The test-only import order was corrected; its behavior/assertions were unchanged.
The final explicit Quick result follows below.

**Locally validated; exact-commit hosted CI and maintainer installed service
acceptance pending.** Final `.\scripts\check.ps1 -Mode Quick` used the
development-Python function binding shown above. It passed with exit `0` in **2.347 s** on
`Windows-11-10.0.26300-SP0`: Ruff **0.096 s**, packaged-schema parity **0.065 s**,
input examples **1.928 s**, all exit `0`. Logs:
`C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-7r_6ywbb`.
Checked source digest:
`de47ac41d5bb6e088e763d2b68cfd41dcf2fe8fdef0ccf9174bb78ff88652034`.
Only this documentation receipt was added afterward. Quick does not certify full
regression, generated outputs, distributions, installations or hosted acceptance.

Tracked `git diff --check` and `git diff --no-index --check -- NUL <file>` for all
seven new files passed with no diagnostics. Final review confirmed exactly the
17 intended files above; `git diff --cached --stat` is empty. Expected/actual branch
remain `feat/312-automatic-match-learning`; expected/actual starting and current HEAD
remain `9b9b66c3289c222f284d737d122f15c4b5f5c124`. Changes are unstaged/uncommitted.
No unresolved local finding remains. Exact-commit hosted branch/main gates and the
documented installed service scenario are still pending; **keep Issue #312 open**.

## Review follow-up: unchanged-update supersession receipt

### Reviewed baseline and historical CI

This narrow Issue-#312 correction starts on the expected/actual branch
`feat/312-automatic-match-learning`, at expected/actual HEAD
`b1fe6b331b75792b3dc3fb25d09da421b5cdea1e`, with a clean worktree and no baseline
substitution. Starting/current HEAD remain equal; the correction is unstaged and
uncommitted. The earlier implementation and validation sections above remain
point-in-time records.

Authenticated read-only inspection of
[branch run 41746088422](https://github.com/hnnng-w/skatmind/actions/runs/41746088422)
confirmed `headSha=b1fe6b331b75792b3dc3fb25d09da421b5cdea1e`, the expected branch,
completed/success status and **all 23 jobs successful**, including both regression
jobs, `check` and `v1-supported-platform-matrix`. This remains historical validation
of that exact reviewed commit. It does not validate this subsequent correction;
new exact-commit hosted branch/main gates remain required.

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
py -3.13 -c "import sys; print(sys.executable); print(sys.version)"
gh run view 41746088422 --json headSha,headBranch,status,conclusion,url,jobs
```

### Confirmed interleaving and bounded correction

An unchanged Update A selected an existing one-source generation, then called
`consume()`, which captured whichever attempt was active when consumption started.
An accepted second Match save and newer Update B could finish in that interval.
Consumption then validated B's two-source state, while A returned `reused` with
its captured older generation. A corresponding stale receipt was also possible
when B completed after consumption returned but before A returned its receipt.
The impact was a stale success/generation receipt; the regression verified no
rollback, replacement or corruption of B's manifest, installed bundle or bytes.

The supplied external probe used CPython **3.12.14** and controlled Package-version
metadata for an uninstalled tree. That evidence is a control-flow diagnostic,
not supported-runtime validation, and was not rerun or treated as acceptance.
Before editing Product code, the new deterministic regression reproduced stale
`reused` receipts on development **CPython 3.13.7**, using actual source-tree
Package metadata and genuine disposable saved Workspaces. A wrapper around
`consume()` establishes the exact interleaving; it uses no timing sleeps. B saves
the second Match through accepted persistence and executes the real S4 preparation.

The correction is confined to the unchanged-input branch of `update()`:

1. Retain the exact installed object whose immutable reference and generation
   match the captured manifest and previous descriptor.
2. Use existing guarded consumption to obtain the authorized bundle identity.
3. Immediately before returning the reuse receipt, hold the existing app → source
   coordinator → archive guard order and require the originating update attempt,
   same installed object, same consumed bundle and exact captured manifest.
4. A mismatch raises the existing `StoreConflictError`, yielding the existing
   `conflict` result with no generation or commit claim. It publishes and clears
   nothing, preserving a newer successful update.

`consume()` and `download()` themselves, explicit outdated access, slow-path
supersession, restart reconstruction and post-commit authority handling retain their
existing implementations. No inventory, evidence, recipe, engine, UI, Schema,
dependency or identity-management change is part of this follow-up.

### Complete affected inventory and validation

Exactly **three tracked files** change:

* `src/skatmind/app_web/automatic_match_learning.py` — captured-state reuse receipt guard;
* `tests/test_automatic_match_learning.py` — eleven deterministic regression cases;
* `docs/automatic_match_learning_s4_verification.md` — this appended follow-up.

The complete affected test inventory is exactly the two S4 modules below. The
service branch is private, with no ordinary UI/startup caller. Its existing
consume/download helper and all shared storage/preparation modules are unchanged.
Together the modules cover retained S2/S3 ownership, manual-source compatibility,
exact bytes and genuine retained evidence through the changed service caller.
Neither module is exclusive in `scripts/validation_pytest.py`; no exclusive module
or additional historical browser suite is affected. Both complete modules ran
with two file-grouped workers.

Development interpreter:
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`,
**CPython 3.13.7**. Every validation tool invocation used timeout **7,200,000 ms**.
All pytest XML and disposable source-tree fixtures are outside the repository:

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
py -3.13 -m pytest tests/test_automatic_match_learning.py -k unchanged_reuse -q -p no:cacheprovider --basetemp "$E\312-reuse-red" --junitxml "$E\312-reuse-red.xml"
py -3.13 -m pytest tests/test_automatic_match_learning.py -k unchanged_reuse -q -p no:cacheprovider --basetemp "$E\312-reuse-focused" --junitxml "$E\312-reuse-focused.xml"
py -3.13 -m ruff check src/skatmind/app_web/automatic_match_learning.py tests/test_automatic_match_learning.py
py -3.13 -m pytest tests/test_automatic_match_learning.py tests/test_automatic_match_learning_evidence.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\312-reuse-complete" --junitxml "$E\312-reuse-complete.xml"
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
git diff --cached --stat
git status --short
git branch --show-current
git rev-parse HEAD
```

| Invocation | Actual outcome | Console seconds |
| --- | --- | ---: |
| Pre-Product-edit regression (`312-reuse-red`) | **8 failed**, 3 passed, 60 deselected | **11.21** |
| Corrected focused regression (`312-reuse-focused`) | **11 passed**, 60 deselected | **9.93** |
| Standalone targeted Ruff | Passed | Not separately timed |
| Both complete S4 modules (`312-reuse-complete`) | **94 passed, 1 skipped** | **966.08** |
| Explicit `.\scripts\check.ps1 -Mode Quick` | **Passed**, exit 0 | **2.663** |

There are **95 distinct tests** in the complete pass, including all eleven new
cases. The focused cases are repeats, not additional distinct coverage. Across
the three pytest invocations there were **108 passing executions, eight expected
pre-correction failures and one skip event**. Every failing regression subsequently
passed. The sole skip is the existing actual-symlink case unavailable to this
Windows account; actual junction/hardlink cases passed. No unexpected failure or
warning occurred in the corrected focused or complete passes.

### Operation assertions and remaining acceptance

The two A/B cases cover both sides of consumption. After initial fixture preparation,
each B performs exactly **one** bundle build and **one each** source-object,
generation-object and manifest temporary write, following one accepted second-Match
save. Superseded A adds **zero** preparation/analysis/archive writes. B's exact
manifest, installed/bundle identity, current two-source generation and complete
disposable JSON byte inventory remain identical after A rejects.

Eight controlled component cases independently change attempt, app owner, installed
object identity or manifest identity before/after consumption. The two manifest
cases deliberately execute one exclusion CAS as fixture interleaving; A performs
no write or preparation. Equal installed values with a different object identity
are insufficient authorization. The normal unchanged case explicitly prohibits
preparation, execution, reservations, object publication and manifest writes, while
asserting the same generation value, identical installed/bundle objects and unchanged
manifest/recording/archive bytes. All eleven new cases require **zero fixture card
analyses**. The unchanged evidence module's full pass separately executes its existing
**16 explicit retained-evidence fixture analyses**, with S4 execution guards still
asserting zero new Application/evaluator/Search/rollout/Historical calls.

Local Full, unrelated suites, distribution checks/builds/installations, installed
UAT and the accepted browser matrix were not run. No real managed data was accessed.
No Git/GitHub publication, Actions trigger or release operation occurred. New
exact-commit hosted CI and maintainer installed-service acceptance remain pending;
keep **#312 open**. Accepted #292–#311 scopes and #308's documentation acceptance
remain intact. #208 stays open, UAT-01 is not globally accepted, formal UAT-02–12
remain paused, and release preparation is not authorized.

### Follow-up completion receipt

**Locally validated; new exact-commit hosted CI and maintainer installed-service
acceptance pending.** Explicit Quick passed on development CPython 3.13.7 /
`Windows-11-10.0.26300-SP0`: Ruff **0.094 s**, packaged-schema parity **0.060 s**,
input examples **1.864 s**, all exit `0`, total **2.663 s**. Logs:
`C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-t_d55d11`.
Checked source digest:
`8d21ec8970914d65d05600699bce4c8a034075666f06968ca96a201425cc37ae`.
Only documentation receipt/wording updates followed Quick. It does not certify
full regression, generated outputs, distributions, installations or new hosted CI.

All three intended changed files were reviewed; `git diff --check` passed and
`git diff --cached --stat` is empty. No new/unrelated files are present. Branch and
starting/current HEAD remain the exact values recorded in this follow-up. The
stale reuse receipt finding is corrected with no remaining concrete local finding.
Keep #312 open for new exact-commit branch/main gates and installed-service acceptance.

## Maintainer acceptance and S5 follow-up

The maintainer accepted #292–#312 before the S5 starting commit
`521b61b638e651348bd3b938d88e87f4af17b36e`. The supplied #313 baseline records #312's
corrected branch run `41795408129`, main run `41818546725`, and installed service
acceptance in three independent process phases with 614 verified installed files.
The earlier pending paragraphs above remain point-in-time history.

[Issue #313](automatic_match_learning_ui.md) now supplies the separate automatic
browser/controller, small admitted-input display capture, and explicit final-delivery
binding around this service. Its ordinary requests use lazy binding, rather than
calling `open()` on each GET. The accepted reuse-supersession correction, separate
S2/S3 reservations, wire recipe and canonical export bytes remain intact. #313's
new hosted and installed UI gates are separate pending acceptance work.
