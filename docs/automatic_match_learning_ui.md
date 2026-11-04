# Automatic Match Learning review and maintenance UI (Issue #313, S5)

## Baseline, scope and acceptance

Expected and actual branch: `feat/313-automatic-learning-review`. Expected/actual
starting and current HEAD: `521b61b638e651348bd3b938d88e87f4af17b36e`. The initial
index and worktree were clean. Read-only `gh issue view 313 --json
number,title,body,comments` confirmed the actual issue number and full task; it had
no comments. There was no baseline substitution, staging, commit or publication.

The maintainer accepted #292–#312, including #312's corrected exact-commit gates
and installed service scenario (614 verified installed files, three process phases).
Historical pending-status paragraphs are preserved. This is the implementation of
S5 and sections 3, 4, 6 and 7 of the
[accepted contract](automatic_learning_integration_contract.md), **managed Matches
only**. Product code changes. S6 Session and S7 manual Historical adapters remain
future work; recommendation adaptation remains a later goal. #208 stays open,
UAT-01 is not globally accepted, formal UAT-02–12 remain paused, and release
preparation is not authorized.

Status: **locally validated; new exact-commit hosted CI and maintainer installed
targeted UI acceptance pending. Keep #313 open.** The maintainer alone performs
later installed acceptance. No distribution was built, installed or started; no
installed/UAT or real managed data was accessed by this task.

## Ordinary workflow and exact evidence

`/learning` presents automatic Match Learning first, followed by independent manual
collections. `/learning/automatic` is its concise status entry.
`/learning/collections` provides independent access even when automatic storage is
blocked. Existing manual current/prepared/import/attachment/debrief/download routes
retain their meanings and active owner.

One primary native **Create Learning review / Update Learning review** action
(`Lernauswertung erstellen / Lernauswertung aktualisieren`) invokes S4. Successful
preparation/reconstruction/reuse redirects to its exact scoped result and focuses
`learning-result`. The existing one-use receipt lifecycle distinguishes those
outcomes. Rejected operations prioritize error focus; a newer attempt never lends
its success receipt to an earlier request.

The compact result reuses #300's conclusion/focus hierarchy and closed **Included
data** and **Technical details and downloads**. Player navigation filters retained
focuses and supporting situations, with an explicit note that total coverage and
downloads remain whole-review values. Per-Player no-focus explanations use retained
Player assessments; another Player's focus is never advertised as theirs. Source
and situation pages resolve exact retained references and disambiguated source
ordinals/version captions. Decisions show actor, Game, Trick/card position and
observed Card. A current-recording POST requires the exact fresh original source;
captured prior reviews cannot open current recordings.

Ordinary retained evidence uses the existing safe Report presentation, including
method, original objective/settings, coverage, actual Card and tie/ranking semantics.
The S3 complete rollout comparison and incomplete availability families remain
separate from ordinary Teacher/Dataset evidence and qualified Search focuses.
No qualification threshold, consensus, retained order, maximum-five focus limit,
Search method, Profile policy or recommendation changes. Counts of Matches,
observed Games, passed/empty slots, Decisions, reconstructed records, skips, Reports,
distinct Teacher-covered Decisions, semantic groups and focuses keep their distinct
meanings. Retrospective context remains separate from decision-time information.

All ten prepared downloads have automatic generation-owned routes and unchanged
canonical bytes. Included S2/S3 evidence also exposes its exact retained native
Request/Result/source-wrapper bytes where supported. The existing Saved analyses
path remains historical archive access, independent of current automatic membership.

## Ownership, projection and final delivery

* `context.py` uses a lazy context factory. The automatic controller binds S4 once;
  ordinary GETs do not replace its owner. CLI-help import checks remain lightweight.
* The controller retains at most 32 opaque views and one confirmation. It never
  assigns `active_learning`, fabricates an active Corpus, imports into a manual
  store, changes manual Current selections or replaces manual prepared values.
* The S4 bundle additionally retains tuples of its already-admitted source records,
  exact Snapshots and executed evidence. These are process-local display inputs,
  not a second source admission algorithm or a persistence/recipe change.
* Frozen display values and pure presentation helpers parameterize links/download
  bases. Rendering never reselects current filesystem content.
* `capture_delivery`, `delivery_reader` and `validate_delivery` bind the exact
  owner, original attempt, installed object/bundle, generation, complete resumed
  manifest/object status and complete live inventory. Archive dependencies remain
  pinned throughout ordinary rendering/serialization/HTTP delivery.
* The server's retained-delivery hook revalidates after rendering and immediately
  before headers. No HTTP bytes are written inside S4's `consume()` callback.
  Language-return pages and rejected-operation responses use the same boundary,
  or a complete localized source-independent recovery page. A copied projection
  or `inspect()` result is never authorization.
* Missing, current, outdated, deleted, excluded, invalid, unsupported, incomplete
  inventory, restart, conflict, quota, failed/unconfirmed and superseded outcomes
  have bounded localized explanations. A typed private `StoreManifestError`
  distinguishes top-level invalid authority while retaining S1's private diagnostic
  text. Browser classification never parses exception messages or filenames.

Confirmed absence/exclusion hides the old aggregate. A current source/evidence
change requires explicit labelled prior access; old capability URLs reject rather
than substituting a newer result. Incomplete scans fail instead of proving deletion.
No malformed top-level archive is reset or repaired.

## Source exceptions and storage maintenance

Five new authenticated POST routes, each limited to **4,096 bytes**, use exact field
cardinality and the existing Host/Origin/cookie boundary:

* `/learning/automatic/update`
* `/learning/automatic/exclude-preview`
* `/learning/automatic/cleanup-preview`
* `/learning/automatic/confirm`
* `/learning/automatic/recording`

Source preview/confirmation binds the exact source identity, owner, manifest and
complete inventory. Exclusion immediately blocks affected aggregate eligibility;
ordinary Update publishes its replacement. Re-inclusion is explicit. Ambiguous
duplicate owners are never chosen by name, timestamp or revision. Blocked source
details open to expose their remedy; ordinary result disclosures remain closed.

Default maintenance delegates to `preview_cleanup()` / `commit_cleanup()` and
removes only owned unreferenced objects. Separately previewed old-evidence removal
lists retained Reports/situations, explains lost future reuse, and retires dependent
generations. Source dependencies still referenced by other evidence remain retained.
Recordings, manual copies and external downloads are outside cleanup ownership.

The integration captures typed cleanup captions while protected, **releases all
reader pins, then creates the final preview**. Its rendering and language translation
never call `consume()`, acquire new archive pins or regenerate the plan. Confirmation
uses the same preview object, manifest, inventory and shared coordinator epoch.
Intervening readers/writers force a new preview and consent. Destructive consent is
unchecked and excluded from submitted-value and language restoration. Cancellation
is navigation only; GET never cleans anything.

A small optional cleanup commit guard rechecks the complete original source binding
at reference publication, including during temporary manifest writing. Removal
remains reference-first. A later physical-delete failure preserves authoritative
references and reports remaining orphans, rather than rolling back or claiming a
fully completed cleanup. No retry, eviction or repair runs automatically.

## Final measured inventories and compatibility

| Inventory | Baseline | S5 |
| --- | ---: | ---: |
| Registered POST routes | 74 | **79** |
| Registered forms | 126 | **131** |
| Keys per German/English catalog | 2,158 | **2,237** |
| Canonical `APP_ROUTE_PATHS` | 9 | **9** |
| Packaged Schemas | 72 | **72** |
| Canonical prepared Match downloads | 10 | **10** |

The nine canonical routes are not an asset count. No asset, public Schema/API,
dependency, Package version, existing persistence format or wire recipe was added
or changed. Registry consumers in validation, direct Match evidence and the
source-executed distribution smoke snippet were updated. Catalog ordering/parity,
source packaging, rename and CLI-help sentinels passed. Distribution smoke was
exercised **only through its source test**, without building or installing anything.

## Complete affected-module inventory and commands

Development interpreter: **CPython 3.13.7** at
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
Every validation tool invocation used timeout **7,200,000 ms**. Tests disabled
pytest's cache provider and Python bytecode writes. Logs, fixtures, XML and browser
profiles/downloads/screenshots are outside the repository under `$E` below.

The union is **44 complete modules / 1,070 distinct tests: 1,066 passed, four
skipped**, including **37 passing new S5 tests**. Repeats are not extra coverage.
The skips are existing actual-symlink cases unavailable to this Windows account
(three store cases, one S4 inventory case). No final unresolved failure remains.

The affected inventory follows the final call graph: S4 delivery/preparation and
store lifecycle; shared Learning result/focus and manual navigation/attachment/
conflict callers; new automatic HTTP/evidence behavior; shared language/feedback/
validation; app context/help/security transport and independent registry/packaging
consumers. Unchanged domain engines, all other Product families and unrelated
suites were not rerun as a substitute for this inventory.

Commands below use explicitly expanded module/flag arrays for readability. These
are the executed module sets, argument order and evidence prefixes; no `-k` subsets
were used. Initial `313-ui-diagnosis` additionally used `-x` before `-q`.

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$env:PYTHONDONTWRITEBYTECODE = '1'
py -3.13 -c "import sys; print(sys.executable); print(sys.version)"
$serial = @('-q', '-p', 'no:cacheprovider')
$parallel = @('-q', '-n', '2', '--dist=loadfile', '--max-worker-restart=0', '-p', 'no:cacheprovider')
$UI = 'tests/test_automatic_learning_ui.py'
$Evidence = 'tests/test_automatic_learning_ui_evidence.py'

# These six invocations used the evolving complete UI module.
py -3.13 -m pytest $UI @serial --basetemp "$E\313-red" --junitxml "$E\313-red.xml"
py -3.13 -m pytest $UI @serial --basetemp "$E\313-ui-1" --junitxml "$E\313-ui-1.xml"
py -3.13 -m pytest $UI @serial --basetemp "$E\313-ui-2" --junitxml "$E\313-ui-2.xml"
py -3.13 -m pytest $UI -x @serial --basetemp "$E\313-ui-diagnosis" --junitxml "$E\313-ui-diagnosis.xml"
py -3.13 -m pytest $UI @serial --basetemp "$E\313-ui-3" --junitxml "$E\313-ui-3.xml"
py -3.13 -m pytest $UI @serial --basetemp "$E\313-ui-4" --junitxml "$E\313-ui-4.xml"
py -3.13 -m pytest $UI $Evidence @parallel --basetemp "$E\313-new-1" --junitxml "$E\313-new-1.xml"

$Boundary = @(
 'tests/test_automatic_learning_ui.py',
 'tests/test_automatic_learning_ui_evidence.py',
 'tests/test_frontend_validation_preservation.py',
 'tests/test_direct_match_evidence.py',
 'tests/test_frontend_localization_foundation.py',
 'tests/test_unified_local_app_contracts.py',
 'tests/test_packaging_and_distribution.py',
 'tests/test_guided_frontend_packaging.py',
 'tests/test_complete_frontend_localization.py',
 'tests/test_skatmind_rename.py',
 'tests/test_app_cli.py'
)
py -3.13 -m pytest @Boundary @parallel --basetemp "$E\313-boundary" --junitxml "$E\313-boundary.xml"
$Affected = @(
 'tests/test_automatic_learning_ui.py',
 'tests/test_automatic_match_learning.py',
 'tests/test_automatic_match_learning_evidence.py',
 'tests/test_automatic_learning_store.py',
 'tests/test_automatic_learning_lifecycle.py',
 'tests/test_automatic_learning_managed_service.py',
 'tests/test_learning_result_readability.py',
 'tests/test_learning_result_explanations.py',
 'tests/test_learning_prepared_navigation.py',
 'tests/test_learning_overview_navigation.py',
 'tests/test_learning_outcome_navigation.py',
 'tests/test_learning_conflict_response.py',
 'tests/test_learning_report_attachment.py',
 'tests/test_learning_report_attachment_web.py',
 'tests/test_learning_report_rejection.py',
 'tests/test_learning_source_navigation.py',
 'tests/test_learning_entry_purpose.py',
 'tests/test_learning_direct_entry_web.py',
 'tests/test_learning_debrief_web.py',
 'tests/test_learning_corpus_web_core.py',
 'tests/test_task_first_match_and_learning_workflow.py',
 'tests/test_frontend_language_switching.py',
 'tests/test_language_switch_context.py',
 'tests/test_language_view_continuity.py',
 'tests/test_task_first_language_preservation.py',
 'tests/test_operation_feedback.py',
 'tests/test_operation_feedback_web.py',
 'tests/test_operation_feedback_language.py',
 'tests/test_operation_feedback_script.py',
 'tests/test_unified_local_app_web.py',
 'tests/test_saved_match_analyses_web.py',
 'tests/test_saved_match_rollouts_web.py'
)
py -3.13 -m pytest @Affected @parallel --basetemp "$E\313-affected" --junitxml "$E\313-affected.xml"

# Workers had exited. Only these two actually affected exclusive modules ran,
# serially, alongside the three complete correction modules.
$CorrectionsAndExclusive = @(
 'tests/test_automatic_learning_store.py', 'tests/test_unified_local_app_web.py',
 'tests/test_frontend_language_switching.py', 'tests/test_local_learning_corpus_web.py',
 'tests/test_unified_rejection_transport.py'
)
py -3.13 -m pytest @CorrectionsAndExclusive @serial --basetemp "$E\313-corrections-exclusive" --junitxml "$E\313-corrections-exclusive.xml"
$Final = @(
 $UI, $Evidence, 'tests/test_automatic_learning_store.py',
 'tests/test_automatic_learning_lifecycle.py', 'tests/test_learning_result_explanations.py',
 'tests/test_learning_result_readability.py', 'tests/test_frontend_localization_foundation.py'
)
py -3.13 -m pytest @Final @parallel --basetemp "$E\313-final-boundaries" --junitxml "$E\313-final-boundaries.xml"
py -3.13 -m pytest $UI tests/test_unified_local_app_web.py tests/test_frontend_language_switching.py @parallel --basetemp "$E\313-final-presentation" --junitxml "$E\313-final-presentation.xml"
py -3.13 -m pytest tests/test_unified_local_app_web.py @serial --basetemp "$E\313-final-landing" --junitxml "$E\313-final-landing.xml"
py -3.13 "$E\313-accounting.py"
```

The other two exclusive modules in `scripts/validation_pytest.py` were unaffected:
early-rejection drainage and Match action-placement algorithms were not changed.
No exclusive test ran alongside workers. The later final-boundary workers covered
new maintenance commit-guard and Player-presentation concerns only.

### Intermediate failures and repeat accounting

| Evidence prefix | Actual result | Console seconds |
| --- | --- | ---: |
| `313-red` | 3 expected pre-implementation failures | 17.52 |
| `313-ui-1` | 3 failures: new catalog keys not yet sorted | 4.41 |
| `313-ui-2` | 3 failures: automatic `capture` method collided with feedback duck typing | 3.61 |
| `313-ui-diagnosis` | 1 failure, 1 diagnostic teardown error; same cause | 1.88 |
| `313-ui-3` | 2 passed, 1 failed: download route omitted digit in `v2` | 14.35 |
| `313-ui-4` | 22 passed, 1 failed, 1 teardown error: test injected deletion repeatedly during recovery | 79.49 |
| `313-new-1` | 29 passed | 748.83 |
| `313-boundary` | 213 passed, 1 failed: test compared volatile HTTP Date headers | 1152.65 |
| `313-affected` | 808 passed, 4 failed, 4 skipped: two S1 diagnostic expectations and two manual empty-state expectations | 2248.85 |
| `313-corrections-exclusive` | 168 passed, 3 skipped | 72.29 |
| `313-final-boundaries` | 197 passed, 3 skipped | 1066.12 |
| `313-final-presentation` | 86 passed, 1 failed: stale manual-introduction expectation after intentional automatic-first presentation | 86.32 |
| `313-final-landing` | 40 passed | 25.27 |

All failures/errors were corrected. Across 13 pytest invocations: **1,565 passing
case executions, 18 failures, two diagnostic teardown errors and ten skip events**.
JUnit records teardown errors as separate case entries; these are not additional
distinct tests. `313-accounting.json` reconciles final identities and module sets.
Standalone Ruff initially found 38 import/line-length/unused-import findings, then
two test line-length findings; its final targeted pass succeeded. Final Quick is
recorded below. No local Full or installation/matrix command ran, under the explicit
task-specific validation authorization.

## Browser evidence, operation and byte accounting

The bounded external harness is `$E\313-browser.py`, reusing the repository's
dependency-free Chromium DevTools transport. It starts only source-tree child
processes with explicit disposable homes and fresh browser profiles. Final passing
scenario: `$E\313-browser-6`; narrow final entry/recovery check:
`$E\313-browser-final-presentation`, driven by `$E\313-browser-followup.py`.

Actual browser: **Microsoft Edge 156.0.4314.58**, headless Chromium, Windows.
Native forms/links/keyboard and disclosures ran with JavaScript disabled in German
and English. Enhanced language return separately preserved the open disclosure and
cleared destructive consent while retaining the same exact preview. Initial result,
confirmation and error focus was inspected before verifier scrolling/focusing.
The autofocus observer waits up to two seconds for browser-native focus to settle;
it never assigns the asserted result/error focus.

The final scenario covers Create, unchanged Update, Player/source/supporting-situation
and retained-evidence navigation, ten downloads in each locale, actual child-process
stop/restart and explicit reconstruction, corrected/outdated and explicit prior views,
deleted aggregate withholding, duplicate diagnostic, stable-identity exclusion and
re-inclusion, preview/cancel/confirm cleanup, stale error focus, and reopening the
unchanged independent selected copy. It records **21 screenshots**, plus four final
presentation screenshots. At 390-pixel emulated viewport width, document client and
scroll widths both measured **375 pixels** with long source labels. This is narrow
reflow evidence at **100% zoom**, not enlarged-browser-zoom acceptance.

Final browser downloads: **30 files**, ten per German/English/restart set, each set
**1,307,407 bytes**, with identical per-file SHA-256 values across all three sets.
Full hashes, screenshots, native POST history, focus/geometry facts and counts are
in `evidence.json`, `phase1-counts.json`, `phase2-counts.json`, and the three download
directories. Two independent manual JSON files remained byte-identical.

| Final browser phase | Bundle builds | Source payload writes | Generation writes | Manifest writes | Profile saves |
| --- | ---: | ---: | ---: | ---: | ---: |
| Process 1: Create, reuse, passive navigation/downloads, language, default cleanup | 1 | 1 | 1 | 1 | 4 |
| Process 2: restart rebuild, correction/deletion Update, exclusion/re-inclusion, stale reject | 2 | 1 | 1 | 3 | 0 |
| Final presentation-only follow-up | 0 | 0 | 0 | 0 | 2 |

Payload-write instrumentation counts successful archive temporary-payload writes;
OS lease/pin activity is separate. The initial archive/source/Report setup is fixture
creation, outside these tables. Process-1 before/after passive checkpoints are equal;
unchanged Update adds no build or payload write. The restarted passive page records
an empty counter set. No new card analysis executes in either browser process.

New HTTP evidence fixtures use **five explicit producer executions per complete
evidence-module run**: one genuine Immediate, two genuine complete/missing-input
rollouts, and two real producer invocations with **controlled injected Search
assessments**. Those two are not genuine solver proofs. Three such complete runs
execute 15 fixture analyses in total. S5 paths then install failing guards at the
Application/evaluator/Search/rollout seams and require zero additional execution.
The separate final HTTP accounting test measures one build/one generation write/one
manifest write after fixture retention, zero passive/reuse writes, and two separate
language Profile saves. Existing affected compatibility suites have their own
fixture executions; they are not included in this S5-only count or claimed as zero.

Browser harness attempts are preserved rather than hidden: an initial import-path
failure preceded fixture creation; attempts 1 and 3 stopped on harness selector
escaping, attempt 2 queued downloads too quickly and retained only six files,
attempt 4 exposed the useful blocked-source disclosure remedy, and attempt 5's
observer sampled before native autofocus settled. Downloads now wait for each actual
file; the blocked-source disclosure opens without changing normal result defaults.
Attempt 6 completed. Each numbered attempt executed one genuine fixture analysis
(six total); the final presentation follow-up executed none. None executed a new
analysis from Learning. Evidence spans from directory creation to final receipt,
including fixture setup, were 198.453 / 378.812 / 921.718 / 1715.883 / 658.119 /
1079.978 seconds, plus 101.605 seconds for the presentation follow-up. These are
filesystem-recorded evidence spans, not latency or performance promises.

```powershell
# Initial invocation failed before creating browser-1, then was retried there.
py -3.13 "$E\313-browser.py" "$E\313-browser-1"
# Subsequent actual invocations used each fresh directory, in order:
py -3.13 "$E\313-browser.py" "$E\313-browser-2"
py -3.13 "$E\313-browser.py" "$E\313-browser-3"
py -3.13 "$E\313-browser.py" "$E\313-browser-4"
py -3.13 "$E\313-browser.py" "$E\313-browser-5"
py -3.13 "$E\313-browser.py" "$E\313-browser-6"
py -3.13 "$E\313-browser-followup.py"
```

## Complete intended changed-file inventory

New Product modules:

1. `src/skatmind/app_web/automatic_learning_controller.py`
2. `src/skatmind/app_web/automatic_learning_http.py`
3. `src/skatmind/app_web/automatic_learning_rendering.py`
4. `src/skatmind/app_web/automatic_learning_routes.py`

Modified Product files:

5. `src/skatmind/app_web/automatic_match_learning.py`
6. `src/skatmind/app_web/context.py`
7. `src/skatmind/app_web/form_registry.py`
8. `src/skatmind/app_web/frontend_profile_operations.py`
9. `src/skatmind/app_web/language_context.py`
10. `src/skatmind/app_web/learning_focus_rendering.py`
11. `src/skatmind/app_web/learning_result_projection.py`
12. `src/skatmind/app_web/learning_result_rendering.py`
13. `src/skatmind/app_web/locales/de.json`
14. `src/skatmind/app_web/locales/en.json`
15. `src/skatmind/app_web/operation_feedback.py`
16. `src/skatmind/app_web/server.py`
17. `src/skatmind/app_web/validation_contracts.py`
18. `src/skatmind/automatic_learning_store.py`
19. `src/skatmind/automatic_match_preparation.py`
20. `src/skatmind/corpus_web/state.py`

Source validation and tests:

21. `scripts/validate_distribution_artifacts.py`
22. `tests/test_automatic_learning_ui.py` (new)
23. `tests/test_automatic_learning_ui_evidence.py` (new)
24. `tests/test_direct_match_evidence.py`
25. `tests/test_frontend_localization_foundation.py`
26. `tests/test_frontend_validation_preservation.py`
27. `tests/test_unified_local_app_web.py`

Directly affected documentation:

28. `AGENTS.md`
29. `README.md`
30. `docs/automatic_learning_integration_contract.md`
31. `docs/automatic_match_learning_s4_verification.md` (appended acceptance/follow-up)
32. `docs/learning_result_readability.md` (scoped follow-up)
33. `docs/automatic_match_learning_ui.md` (this new document)

External verification harnesses, fixtures and evidence are not repository files.
All 33 intended files remain unstaged and uncommitted.

## Later maintainer installed UI scenario — instructions only

After new exact-commit branch/main `check` and `v1-supported-platform-matrix` gates,
the maintainer builds/installs separately and uses a new disposable installed home.
Record actual commit, interpreter, installed file verification and browser identity.

1. In each locale with JavaScript disabled, create a review from two saved synthetic
   Matches (one partial) plus genuine retained evidence. Inspect Player and supporting
   situation/evidence links; verify initial result focus, native keyboard behavior and
   all ten downloads. Confirm no passive analysis/preparation.
2. Actually stop/restart the installed application. GET must require reconstruction;
   explicit Update reproduces the ten bytes. An unchanged Update reuses its bundle.
3. Correct one source, inspect the labelled prior view, then delete another source.
   Verify the deleted aggregate is hidden before Update and replacement counts are
   exact. Old Reports remain bound to their originals.
4. Create a controlled duplicate identity; verify no arbitrary owner is chosen.
   Preview/confirm exclusion, resolve the duplicate and explicitly re-include/Update.
5. Preview default orphan cleanup, cancel, then freshly preview/confirm. Separately
   preview removal of old evidence and inspect the situations, Report count and lost
   reuse warning. Change language with consent checked: consent must clear. An
   intervening reader/writer must require fresh preview/consent.
6. Reopen the independent manual collection and compare its selected copy and bytes.
   Check narrow/long-label wrapping, keyboard and error-focus priority, and **genuine
   enlarged browser zoom** in both locales. Developer viewport emulation does not
   satisfy that installed zoom check.

These are future maintainer instructions, not performed installed acceptance and
not a resumption of formal UAT-02–12.

## Final local check receipt

The task-specific authorization requires complete affected modules plus explicit
Quick, not local Full. Quick and final whitespace/status receipts are recorded in
the completion follow-up below.

Explicit `.\scripts\check.ps1 -Mode Quick` passed on development CPython 3.13.7 /
`Windows-11-10.0.26300-SP0`, exit **0**, in **3.092 s**:
Ruff **0.228 s**, packaged-schema parity **0.124 s**, input examples **2.421 s**.
Logs: `C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-qql9gi99`.
Checked source digest:
`11f744cfa8a144658f189114ae8188844fa0d8c936215f3560b63e8c642e9050`.
Only this documentation receipt followed that check.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode\313-pycache'
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
git diff --cached --stat
git status --short
git branch --show-current
git rev-parse HEAD
```

Tracked whitespace checks and `git diff --no-index --check -- NUL <path>` for each
of the seven new files passed without diagnostics. Changed/new Product, test,
validation and documentation files were reviewed. Final status contains exactly
the 33 intended files above; the index is empty and branch/HEAD remain unchanged.
No concrete local failure remains. Quick does not certify full regression,
generated outputs, distributions or installations. New exact-commit hosted gates
and maintainer installed targeted UI acceptance remain pending; **keep #313 open**.

## Issue #313 review correction — source-history release and exact entry language binding

### Reviewed baseline and historical CI

This bounded correction starts on the expected/actual branch
`feat/313-automatic-learning-review`, at expected/actual HEAD
`8259f7a1a70cc8b8db896aa1e67b6602f42c63cc`, with a clean index and worktree.
Starting/current HEAD remain equal; the correction is unstaged and uncommitted.
There is no substituted baseline or unrelated work.

Read-only inspection of [Actions run 41871675685](https://github.com/hnnng-w/skatmind/actions/runs/41871675685)
confirmed that exact `headSha`, branch, completed/success status and **all 23 jobs
successful**, including both hosted regression jobs, `check` and
`v1-supported-platform-matrix`. This is historical validation of the starting
commit, **not validation of these subsequent corrections**. The initial S5 record
above and accepted #292–#312 evidence remain intact. The reviewer's isolated
CPython-3.12 AST/control-flow diagnostic was not run or treated as supported Product
or HTTP evidence.

### Finding A: source-only retention gap and correction

Before Product edits, genuine delivered HTTP forms created a review from one saved
Match with no executed analysis, then performed three saved corrections and three
explicit Updates. All four exact source versions remained indexed after native
preview/confirmation of **both** previously offered maintenance modes. The new
regression then failed because no emitted form could release that history.

Cause: the UI supplied only `remove_evidence_ids`; S1 deliberately treats every
indexed source record as a protected root until `release_source_version_ids` is
explicitly supplied. Retiring a generation alone does not release those roots.

The existing cleanup route now offers a **separate `obsolete_sources` mode**, with
its own explicit preview and destructive confirmation. Ordinary orphan cleanup and
old-Report removal retain their original consent meanings; the two removal families
cannot be combined through the controller flags.

Eligibility is derived from S4's complete captured inventory and exact version IDs:

* A current saved version remains protected even if explicitly excluded from Learning.
* An incomplete scan fails existing capture/delivery validation. Any invalid,
  unsupported or ambiguous inventory entry conservatively blocks source release;
  it is not evidence of deletion. The preview explains a zero-release outcome.
* Retained evidence's original source IDs, non-retirable dependency edges, and
  retained binding endpoints protect source records/objects. Unsupported or corrupt
  archived sources are not consumed to invent display captions.
* Only eligible available obsolete Match sources are passed to the existing S1
  `release_source_version_ids` parameter. S1 still performs graph retirement,
  reference-first publication, pin/candidate protection and physical deletion.
  **The storage foundation and S4 service were not modified.**

Exact decoded archived source captions are captured under reader protection, then
those pins are released **before** the final cleanup preview is created. The frozen
confirmation retains title, Match identity, numeric revision and full source-version
fingerprint, plus exact released/retained source counts and S1's object/Report counts.
Both catalogs explain lost historical reuse and dependent-generation retirement.
Rendering, language return and confirmation do not acquire new pins or regenerate
the plan. The original preview, manifest CAS, coordinator epoch, one-use consent
and final source checks remain authoritative.

An explicitly released source can retire the current or prior dependent generation;
the whole affected installed bundle is invalidated. Rebuilding remains an explicit
Create/Update action. A pre-existing reader can keep released physical objects alive
until a later explicit orphan cleanup. Interrupted physical source deletion retains
committed reference removal and the existing truthful partial-cleanup receipt.
Recordings, retained Report dependencies, manual copies and external downloads are
outside the new release effect.

The tiny-quota HTTP regression uses valid `StoreLimitsV1(total_bytes=retained_bytes
+ 256)`, explicitly asserted below **1,000,000 bytes**, instead of a large fixture.
Its requested Update hits quota before preparation/publication. Native source-release
confirmation performs one manifest write, retires the old generation, and allows a
subsequent explicit Update to succeed with one source, one generation and one manifest
write. No silent eviction, preparation, repair or retry was introduced.

### Finding B: original entry authority and correction

Before Product edits, the delivered native `/learning/automatic` language form
returned **303** after either a saved-source correction or an actual manifest
exclusion change, while service, attempt and installed bundle references were
unchanged. Unchanged native return also passed as a positive control. The first
manifest fixture attempted a revision-only update, which S1 correctly treated as
`unchanged`; it was corrected to a genuine exclusion CAS and reproduced the 303
gap before Product edits.

Cause: the root URL had no retained view token and language validation called a
fresh `capture_delivery()`. That proved the newly observed state, not the original
rendered entry. Tokenized review/download authorization was a separate boundary;
this finding does not establish stale download disclosure or unwanted preparation.

`LanguageSourceV1` now retains the exact immutable `automatic_view` supplied by the
renderer. Submission and return resolve that original token/object through the
existing controller/S4 delivery guard. The root entry's language return uses that
same view; it never calls fresh capture as a substitute. The mutable controller
`landing_view` slot was removed, and the automatic entry on `/learning` also uses
its per-page binding. A newer tab cannot replace an older submitted page's authority.

Unchanged native/enhanced return, disclosure/view restoration, receipt behavior and
cleared destructive consent retain their existing mechanisms. Tokenized result,
evidence, download and confirmation checks remain in place. A narrow server branch
uses the existing complete localized language-conflict response directly for rejected
automatic entry contexts. This avoids refreshing the manual discovery list during
rejection and invalidating an otherwise correctly bound second tab.

Regression checks cover source and manifest changes before submission, a newer tab,
explicit prohibition of recapture during valid language return, enhanced disclosure
restoration, and changes after a valid save, before return, during rendering and at
the final byte-delivery hook. Pre-save rejection has **zero Profile writes**. Each
post-save conflict has exactly **one deliberate Profile save**, retains the saved
locale, and delivers a complete localized conflict/recovery response.

### Correction inventory and affected-module selection

Exactly **11 intended files** change:

1. `src/skatmind/app_web/automatic_learning_controller.py`
2. `src/skatmind/app_web/automatic_learning_http.py`
3. `src/skatmind/app_web/automatic_learning_rendering.py`
4. `src/skatmind/app_web/language_context.py`
5. `src/skatmind/app_web/server.py`
6. `src/skatmind/app_web/locales/de.json`
7. `src/skatmind/app_web/locales/en.json`
8. `tests/test_frontend_localization_foundation.py`
9. `tests/test_automatic_learning_source_release.py` (new)
10. `tests/test_automatic_learning_entry_language.py` (new)
11. `docs/automatic_match_learning_ui.md` (this appended correction record)

Five new catalog keys bring each locale from **2,237 to 2,242**. The exact assertion
was updated. Registered POST routes remain **79**, registered form definitions
**131**, canonical routes **nine**, packaged Schemas **72**, and automatic canonical
downloads **ten**. The added native maintenance form uses the existing registered
shared route; no registry assertion was weakened. No public schema, export bytes,
persistence recipe, analysis method, focus rule, dependency or Package version changed.

The final affected inventory is **18 complete modules / 425 distinct tests:
422 passed, three skipped**, including **25 passing new correction regressions**.
The skips are the existing automatic-store actual-symlink cases unavailable to this
Windows account. Direct S5 HTTP/evidence callers cover ordinary and changed cleanup
paths; complete S1 store/lifecycle modules cover source release, shared dependencies
and readers. Shared language/feedback modules cover native/enhanced return; catalog,
registry, source-packaging and app-help sentinels cover the affected resource/import
boundary. S4's algorithms and the other historical browser scenarios were not rerun
as an unrelated acceptance suite.

Only `test_unified_rejection_transport.py` is an affected exclusive module: the
server's rejected-language response integration changed. It ran serially after both
parallel workers exited. The other three exclusive modules cover unchanged drainage,
standalone Corpus and Match action-placement code and were not run for this correction.

### Exact validation commands and results

Development interpreter: CPython **3.13.7** at
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
Every validation tool call used timeout **7,200,000 ms**. All XML, fixtures, browser
profiles/screenshots and accounting are outside the repository. These are source-tree
developer checks, not installed acceptance.

```powershell
git status --short --branch
git rev-parse HEAD
git diff --cached --stat
git diff --stat
gh run view 41871675685 --json headSha,headBranch,status,conclusion,url,jobs
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$env:PYTHONDONTWRITEBYTECODE = '1'
py -3.13 -c "import sys; print(sys.executable); print(sys.version)"
$A = 'tests/test_automatic_learning_source_release.py'
$B = 'tests/test_automatic_learning_entry_language.py'
py -3.13 -m pytest $A $B -q -p no:cacheprovider --basetemp "$E\313-review-red" --junitxml "$E\313-review-red.xml"
py -3.13 -m pytest $A $B -q -p no:cacheprovider --basetemp "$E\313-review-red-2" --junitxml "$E\313-review-red-2.xml"
py -3.13 -m pytest $A $B -q -p no:cacheprovider --basetemp "$E\313-review-focused-1" --junitxml "$E\313-review-focused-1.xml"
py -3.13 -m pytest $A $B -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\313-review-new" --junitxml "$E\313-review-new.xml"
$Affected = @(
 'tests/test_automatic_learning_source_release.py',
 'tests/test_automatic_learning_entry_language.py',
 'tests/test_automatic_learning_ui.py',
 'tests/test_automatic_learning_ui_evidence.py',
 'tests/test_automatic_learning_store.py',
 'tests/test_automatic_learning_lifecycle.py',
 'tests/test_language_switch_context.py',
 'tests/test_language_view_continuity.py',
 'tests/test_frontend_language_switching.py',
 'tests/test_task_first_language_preservation.py',
 'tests/test_operation_feedback_language.py',
 'tests/test_frontend_validation_preservation.py',
 'tests/test_frontend_localization_foundation.py',
 'tests/test_complete_frontend_localization.py',
 'tests/test_guided_frontend_packaging.py',
 'tests/test_packaging_and_distribution.py',
 'tests/test_app_cli.py'
)
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\313-review-affected" --junitxml "$E\313-review-affected.xml"
py -3.13 -m pytest tests/test_unified_rejection_transport.py -q -p no:cacheprovider --basetemp "$E\313-review-exclusive" --junitxml "$E\313-review-exclusive.xml"
py -3.13 "$E\313-review-accounting.py"
py -3.13 "$E\313-review-browser.py" "$E\313-review-browser-1"
```

| Correction evidence prefix | Actual outcome | Console seconds |
| --- | --- | ---: |
| `313-review-red` | 3 failed, 1 passed: A gap, B source gap, and the revision-only manifest fixture mistake | 21.85 |
| `313-review-red-2` | 3 expected pre-Product failures, 1 unchanged positive control passed | 21.50 |
| `313-review-focused-1` | 4 passed after initial corrections | 22.97 |
| `313-review-new` | 24 passed, 1 failed: rejection refreshed discovery and invalidated the second `/learning` tab | 378.45 |
| `313-review-affected` | **385 passed, 3 skipped**, all 17 complete parallel modules | **1268.02** |
| `313-review-exclusive` | **37 passed**, complete exclusive module after worker exit | **19.32** |

All seven intermediate failed executions were resolved. Across six pytest
invocations: **452 passing executions, seven failures, three skip events**;
repeats are not additional distinct coverage. The external `313-review-accounting.json`
reconciles final identities and module inventory. Targeted Ruff initially found
12 import-order/line-length findings; all were corrected. The final explicit Quick
receipt is appended below. No local Full, distribution build/install, installed
matrix, unrelated suite or timing-only repetition was run.

### Browser and operation evidence

The bounded follow-up completed on its **first run in 87.599 seconds**, using
Microsoft Edge **156.0.4314.58**, headless, on the disposable source-tree server.
Evidence: `$E\313-review-browser-1\evidence.json` and **nine screenshots**.
The external harness is `$E\313-review-browser.py`, reusing the repository's
dependency-free DevTools transport. It starts no distribution or UAT environment.

Both locales were exercised with JavaScript disabled: exact source/version previews,
native cancellation, explicit confirmation, unchanged language return and stale
original-entry language rejection. Enhanced return separately preserved the same
preview identity, cleared checked destructive consent, restored an open root-entry
disclosure, and rejected an enhanced stale context. Native initial confirmation/error
focus was sampled before verifier scrolling. Full fingerprints wrap at a 390-pixel
viewport: client and scroll width both **375 pixels**. This is 100%-zoom reflow
evidence, not genuine enlarged-zoom acceptance.

The first release reduced indexed source history from four versions to one; the
second removed one subsequent obsolete version while preserving the current one.
Two independent manual JSON files and their selected version remained byte-identical;
the active manual owner was unchanged. The final editable recording matched the
latest deliberate fixture save. No Report was executed for this source-only browser
scenario and no historical S5 download/restart matrix was repeated.

Measured browser counters, excluding initial fixture setup:

| Explicit work | Actual count |
| --- | ---: |
| Requested Create/Update preparations | 5 |
| Source payload writes | 5 |
| Generation payload writes | 5 |
| Manifest writes | 8: initial authority + five generation publications + two cleanups |
| Explicit cleanup source-object deletions | 4 |
| Explicit cleanup generation-object deletions | 4 |
| Deliberate language Profile saves | 9 |
| Deliberate other-tab/source-history fixture recording saves | 6 |
| Analysis, passive preparation/import/recording/archive writes, or stale-rejection Profile saves | **0** |

Fixture setup separately created one initial recording, saved the initial English
Profile once and imported one independent manual copy. Payload-write counters are
distinct from OS lease/pin activity. Before/after checkpoints assert that passive
viewing, cancellation, disclosure use and stale rejection add no Product work.
Valid language changes account for Profile writes separately.

The new shared-evidence HTTP fixture executes **two genuine tiny Immediate analyses**
before guards are installed, sharing one exact original Workspace. It verifies
that releasing an unrelated obsolete version preserves retained evidence/source
bytes and the independent manual copy, including after one Report is explicitly
removed as a separate fixture operation. Its two complete module runs execute four
fixture analyses in total; the new language/source-only regressions and browser
scenario execute none. Existing affected suites retain their own fixture execution
accounting and are not claimed to have zero fixture analyses.

### Remaining acceptance

Both reviewed causes are corrected locally. Preserve the successful starting-commit
CI as history. New exact-commit hosted `check` and `v1-supported-platform-matrix`
evidence and maintainer installed targeted acceptance remain required. The installed
follow-up should repeat only these changed paths with disposable data: source-only
history and explicit release/quota recovery; protected retained evidence/current
sources; original-entry language rejection before save and honest conflict after a
valid save; unchanged native/enhanced return and exact consent in both locales.
These are maintainer instructions only, not performed installed acceptance.

Keep **#313 and #208 open**. Accepted #292–#312 behavior, independent manual ownership,
ten automatic exports, exact S2/S3 evidence and #312's reuse-supersession correction
remain intact. S6/S7, recommendation adaptation and release work remain outside this
correction. UAT-01 is not globally accepted, formal UAT-02–12 remain paused, and
release preparation is not authorized.

### Correction completion receipt

**Locally validated; new exact-commit hosted CI and maintainer installed targeted
acceptance pending. Keep #313 and #208 open.** Explicit
`.\scripts\check.ps1 -Mode Quick` passed with exit **0** on development CPython
3.13.7 / `Windows-11-10.0.26300-SP0`, total **29.420 s**: Ruff **0.476 s**,
packaged-schema parity **0.201 s**, input examples **5.673 s**. The total includes
runner setup and is not the sum of stage-only timings. Logs:
`C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-sg8w7wst`.
Checked source digest:
`1e76ee8cf0d61c0c717471c6a0efe4bcdb21debc19ece5cb1bdb922d032a2239`.
Only this documentation receipt followed Quick.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode\313-review-pycache'
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
git diff --no-index --check -- NUL tests/test_automatic_learning_source_release.py
git diff --no-index --check -- NUL tests/test_automatic_learning_entry_language.py
git diff --cached --stat
git status --short
git branch --show-current
git rev-parse HEAD
```

All changed/new files were reviewed; tracked and new-file whitespace checks passed.
The final worktree contains exactly the 11 intended correction files, with no staged
changes. Branch and starting/current HEAD remain the exact values above. Both
confirmed findings have passing supported-runtime HTTP regressions and bounded
browser follow-up; no concrete local issue remains. Quick does not certify full
regression, generated outputs, distributions, hosted gates or installed acceptance.
