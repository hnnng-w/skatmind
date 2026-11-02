# Ordinary Match analysis retention (Issue #310, S2)

## Status and boundary

S2 implements durable capture, strict restart admission, exact retrieval and a
save-only retry for explicitly executed **managed ordinary Match Decisions**.
Immediate, bounded Search, Auto and Information-set Search are supported. The
original live eight-Report list and its expiry remain independent of the archive.

**Locally validated; exact-commit hosted CI and installed targeted acceptance
pending. Keep #310 open.** Local verification is recorded below. Expected/actual branch:
`feat/310-match-decision-evidence`. Starting/current HEAD:
`9e98056a53be487020f1b1877fc8b94f1e629b09`. The starting worktree was clean, with no
baseline substitution. Changes are unstaged and uncommitted.

The maintainer identifies S1 #309, its strict-resume correction and installed
service acceptance as complete at this baseline. Its older pending-status records
remain historical records. Accepted #292–#309 scopes are preserved. #208 stays
open; UAT-01 is not globally accepted, formal UAT-02–12 remain paused,
recommendation adaptation remains a later goal, and release preparation is not
authorized.

S3 rollout retention, S4 automatic membership/discovery/preparation/generations,
S5 general Learning/maintenance UI, S6 Session and S7 Historical adapters remain
later work. This change does not prepare a Learning review. It changes no public
Schema/API, existing recording/manual-Corpus format, dependency, recommendation,
policy precedence or qualification rule. Standalone Capture, CLI and core
execution have no implicit managed-home persistence.

## Producer and original-source contract

`execute_unified_match_analysis_v1(..., app_context=...)` is the managed opt-in
boundary. Before execution it strictly loads the exact original persistence
document, including its supported identity domain, and checks both the Workspace
and complete content fingerprint. Capture retains its original immutable Workspace,
revision, Match identity, fingerprint and Report-store generation.

The optional core `execution_observer` retains the **actual** Application
invocation and execution after producer validation. It neither executes again nor
changes `MatchDecisionAnalysisResultV1`. The optional Capture
`publication_observer` runs only after successful source/selection/attempt checks
and live publication. It receives the originally captured Workspace, exact Report,
invocation and execution; generic `MatchAnalysisReportStoreV1.put()` is not a hook.
An `applied` operation without that actual execution tuple cannot archive a Report.

Only outer `status=executed`, `report_kind=decision_analysis` and the four ordinary
methods qualify. Genuine inner Search `partial`, `timeout` and `unavailable`
outcomes qualify even without a recommendation. Rejected forms, execution errors,
stale/superseded work and never-executed outer unavailability do not. Materialization,
Historical, rollout and Session producers do not enter this envelope.

### Strict codec/origin boundary

The unchanged S1 storage envelope and manifest remain version `1`. New typed
adapters use **object codec `2`** for `match_source` and `match_decision`, with a
strict inner envelope version `1`, producer `managed_match_decision`, producer
contract `1`, and an explicit supported Package-version set (currently `0.17.0`).
S1's opaque **codec-1 synthetic payloads remain unsupported**, including a
well-formed payload copied beneath a codec-1 reference. Unknown codecs, producers,
producer contracts and Package versions do not acquire compatibility from hashes.

The source object retains the exact original persistence document and its derived
Snapshot, including closed Game/Decision references. Its `SourceVersionV1` binds
the logical Match key, original persistence document kind/contract version and
complete content fingerprint. The descriptive revision is not identity. The
ordinary envelope also retains the exact source record and Snapshot ID; the
source-scoped situation binds Game, one-based Decision, stable actor, observed
Card and pre-Card information cutoff (`decision_index - 1`). An unrelated
same-revision Workspace change cannot be hidden by an unchanged selected Request.

The complete Report-source representation includes Request, Result, warnings,
options and Profile binding. A closed private Application codec additionally
retains original invocation/effective options, option-presence metadata,
original external Statistics document/reference, returned artifacts, complete
provenance bundle and final serialization checkpoint. Its constructor allowlist
cannot import wire-specified modules or instantiate arbitrary types. Mapping order
is retained independently of sorted-key storage JSON.

Admission strictly resumes the Workspace, derives/checks the original Snapshot,
decodes the existing Report-source wrapper, and reuses the complete method-specific
Teacher validator via `validate_original_match_teacher_v1`. This focused pure
helper requires an explicit original Snapshot and creates no manual collection or
automatic generation. It closes Game/Decision/actor/Card references and rebuilds
through `build_match_decision_position_request_v1` with original options. The
adapter also reconciles the original invocation, effective options, external
documents/input reference, retained Result and full provenance source/retained-stage/
serialization checks. Today's Player history is never consulted.

Only indexed evidence with an intact, typed original dependency closure is
consumable. `read_object()` remains storage-only, including for orphans.
`read_evidence()` and `snapshot().available_evidence_ids` use explicit adapters.
Missing/corrupt dependencies exclude dependent Reports; independent valid entries
remain readable. Unsupported sources do not authorize Reports. A malformed top-level
manifest blocks the store without repair, replacement or empty-store fallback.
S1's known-kind mismatch rejection and untrusted general origin bindings remain intact.

Supported original legacy Workspace/Snapshot/Report identity domains are preserved
on reads. No current-domain normalizing serializer rewrites their IDs or bytes.
The legacy regression is a controlled identity-domain conversion of a genuine
current execution, not evidence that a historical producer ran S2. Fingerprints
establish identity and consistency, not historical authorship or truth.

### Exact downloads

Capture uses existing serializers for Result and Report-for-Learning bytes and
filenames. Each payload is retained with its SHA-256 digest. The additive retained
Request uses the executed Request's Root document and existing two-space,
ASCII-escaped, finite UTF-8/LF canonical convention, with `-request.json` appended
to the existing Decision artifact basename. It never uses today's Workspace.

Admission compares all three payloads/digests to typed values and original mapping
order. Even recomputed hashes over reordered or modified payloads do not pass.
Legacy wrapper checks rebuild the same legacy identity with the retained execution's
original order; they do not use the normalizing transfer serializer. Existing live
Result/Report-for-Learning bytes and filenames are unchanged.

## Publication, locks and failure semantics

1. Capture original source and execution under existing Product ownership rules.
2. Build/validate immutable source/envelope objects outside Product/app locks.
3. Retain at most one bounded pending execution per managed owner. It binds the
   exact active Match object, archive owner, attempt, original document, Report,
   Report-store generation and selection generations.
4. Use S1's shared store owner, bounded candidate reservation, dependency-first
   immutable no-clobber publication, then one expected-manifest CAS.
5. Final publication holds **Match lock → app lock → store transaction**. It checks
   the actual current active owner, not eventual clearing of the old live store.
   The optional `commit_guard` runs on transaction entry and immediately before
   replacement, after unlocked object staging and manifest temporary writing.
   It closes source, selection, generation, attempt and owner changes. No Match and
   manual-Corpus locks are held together.

The existing 16 MiB/object, 512 MiB retained-plus-pending bytes, 2,048 ordinary
entries globally, one active candidate per store owner, reader pins and
manifest-first cleanup guarantees remain unchanged. Abandoned work releases only
its own matching reservation; a newer candidate is not cleared. There is no
automatic cleanup, eviction, merge or retry loop.

**Manifest replacement is the durability boundary.** Pre-commit failure preserves
the successful live Report/downloads while their original authorization is valid.
The page says “Analysis completed. Learning evidence was not saved.” and offers
“Retry saving” for that exact pending execution. Retry performs only bounded
archive/manifest writes, without evaluation, rebinding or preparation. Expired or
foreign-owner retries return a localized conflict. A source correction, reload,
selection change, new attempt, owner replacement or live eviction cannot be undone
by retry.

After a post-replacement error the service reads authoritative state: an indexed
intact commit is reported saved; inability to establish the outcome is reported
unconfirmed. No rollback removes a committed manifest. Exact repeated capture is
idempotent without manifest revision/write changes. Distinct complete Reports,
including elapsed-only variants, remain distinct entries; Teacher semantic
grouping is separate.

The first explicit eligible capture may initialize an absent automatic root.
An existing invalid/partial root is never initialized as empty. No passive GET,
download, disclosure, language return or startup initializes/saves the archive or
runs evaluation/derived Learning preparation. Deliberate language changes keep
their separately accounted frontend-profile writes.

## Native access and ownership

The Match landing/recording/review workflow links to **Saved analyses /
Gespeicherte Analysen**, including after restart with no active Match. The compact
list identifies original Match/Game/Decision, actor/method, captured revision,
source fingerprint prefix and exact Report variant. The separate execution view
uses the original Snapshot and existing curated context/comparison/explanation
renderers. It omits live-only process-expiry text and exposes no private Search
Worlds, ownership assignments or Search internals.

| Method | New private route | Meaning |
| --- | --- | --- |
| GET | `/matches/saved-analyses` | Read-only indexed saved list |
| GET | `/matches/saved-analyses/{capability}` | Exact retained execution |
| GET | `/matches/saved-analyses/{capability}/request.json` | Retained executed Request |
| GET | `/matches/saved-analyses/{capability}/result.json` | Original Result bytes |
| GET | `/matches/saved-analyses/{capability}/strategy-source.json` | Original Report-for-Learning bytes |
| POST | `/matches/retry-saving` | Bound save-only retry |

The retry form has only opaque `managed_handle` and `save_token` inputs, plus
existing frontend instrumentation. It uses native controls, a registered
value-free form, loopback cookie/Origin protection, bilingual catalogs and shared
styling. Both saved list and exact view participate in language return. Measured
inventories: **74 POST routes, 126 form definitions, 2,151 keys per catalog**
(previously 73/125/2,133). Distribution smoke expectations reflect those measured
counts; no distribution was built or installed.

Fresh process-owned HMAC capabilities bind automatic-space identity and exact
indexed execution. Restart expires old capabilities. Reader pins protect the
dependency closure through delivery; separate owner/manifest/admission checks run
again after rendering/serialization immediately before sending bytes. The new live
save receipt/retry presentation also rechecks source/owner/attempt authorization
at final HTML delivery. Existing live Report URLs retain their expiry; archived
Reports are never inserted into the live store or replaced by the newest execution.

A changed/missing editable recording does not invalidate an intact captured
original. The view identifies historical captured-source context and does not
claim current automatic membership. It offers no recording-return action that
could target a corrected/missing recording. Membership reconciliation and general
storage-maintenance controls belong to S4/S5.

## Complete affected-module inventory and commands

The inventory follows actual callers: the four S1 service/transaction modules;
the producer and strict Report/Teacher source chain; unified Match execution,
selection, downloads and manual attachment consumers; app-context, route/form,
localization/language-return and package-resource contracts. Existing shared
renderers retain default output; the archived view opts out only of live lifetime
copy. No evaluator, Session engine, rollout engine, manual-Corpus format or general
dataset/preparation implementation changes; their unrelated suites are not added
merely because they are transitive imports.

The **38 complete parallel modules** are exactly `$Affected` below. Two affected
exclusive modules run serially only after those workers exit. Packaging tests
inspect source metadata/resources and execute a small registry assertion fragment;
they do not build/install distributions.

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$Affected = @(
  'tests/test_automatic_learning_contracts.py',
  'tests/test_automatic_learning_store.py',
  'tests/test_automatic_learning_lifecycle.py',
  'tests/test_automatic_learning_managed_service.py',
  'tests/test_automatic_match_evidence.py',
  'tests/test_match_evidence_retention.py',
  'tests/test_saved_match_analyses_web.py',
  'tests/test_match_analysis_report_source_export.py',
  'tests/test_learning_corpus_strategy_teacher.py',
  'tests/test_learning_corpus_strategy_teacher_search.py',
  'tests/test_learning_corpus_information_set_strategy_teacher.py',
  'tests/test_learning_corpus_strategy_teacher_export.py',
  'tests/test_local_match_capture_web_analysis.py',
  'tests/test_match_decision_selection_web.py',
  'tests/test_match_learning_report_discoverability.py',
  'tests/test_analysis_download_details.py',
  'tests/test_match_analysis_exports.py',
  'tests/test_match_decision_analysis.py',
  'tests/test_match_information_set_search.py',
  'tests/test_recorded_review_navigation.py',
  'tests/test_unified_local_app_web.py',
  'tests/test_unified_local_app_managed_items.py',
  'tests/test_unified_local_app_contracts.py',
  'tests/test_learning_report_attachment.py',
  'tests/test_learning_report_attachment_web.py',
  'tests/test_frontend_localization_foundation.py',
  'tests/test_complete_frontend_localization.py',
  'tests/test_frontend_language_switching.py',
  'tests/test_language_switch_context.py',
  'tests/test_language_view_continuity.py',
  'tests/test_task_first_language_preservation.py',
  'tests/test_frontend_validation_preservation.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_recorded_decision_context_web.py',
  'tests/test_analysis_explanations_web.py',
  'tests/test_match_rollout_web.py',
  'tests/test_task_first_stateful_rendering.py'
)
$Focused = @('tests/test_automatic_match_evidence.py',
  'tests/test_match_evidence_retention.py', 'tests/test_saved_match_analyses_web.py')
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\310-affected" --junitxml "$E\310-affected.xml"
py -3.13 -m pytest tests/test_saved_match_analyses_web.py tests/test_packaging_and_distribution.py tests/test_match_analysis_action_placement.py tests/test_unified_rejection_transport.py -q -p no:cacheprovider --basetemp "$E\310-delivery-and-serial" --junitxml "$E\310-delivery-and-serial.xml"
py -3.13 -m pytest @Focused -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\310-final-focused" --junitxml "$E\310-final-focused.xml"
py -3.13 -m pytest tests/test_saved_match_analyses_web.py -q -p no:cacheprovider --basetemp "$E\310-list-language" --junitxml "$E\310-list-language.xml"
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
```

### Actual local execution record

All validation invocations use development **CPython 3.13.7** and a **7,200,000 ms**
harness timeout. Logs/caches/disposable homes stay outside the repository. Timings
below are actual pytest console totals, not latency gates.

| Evidence prefix / invocation | Result | Seconds |
| --- | --- | ---: |
| `310-baseline`: existing S1 synthetic non-admission and standalone analysis/no-save tests, before Product edits | 2 passed | 6.27 |
| `310-codec-1`: new four-method module, `-x` | 1 failed: option-presence order lost during typed reconstruction | 8.79 |
| `310-codec-2`: corrected complete four-method module | 4 passed | 43.69 |
| `310-web-1`: first native HTTP module | 1 passed | 26.57 |
| `310-focused-1`: three new modules | 31 passed, 4 failed: fixture used `dataclasses.replace` on builder-only Workspace | 162.37 |
| `310-focused-2`: expanded three new modules | 77 passed, 3 failed: identical fast-run elapsed values and wrong controlled Search method literal | 448.99 |
| `310-fixture-correction`: `-k 'genuine_ordinary_complete or distinct_elapsed or controlled_limited'` | 5 passed, 2 failed, 34 deselected: controlled prefix below historical-profile minimum | 42.59 |
| `310-affected`: all 38 complete modules | 819 passed, 4 skipped, 1 failed: stale installed-smoke registry count | 797.11 |
| `310-delivery-and-serial`: corrected packaging, complete HTTP module and both exclusive modules | 89 passed | 240.89 |
| `310-final-focused`: complete three S2 modules after byte-order/final-delivery and supersession coverage | 95 passed | 869.67 |
| `310-list-language`: complete HTTP module after list language binding | 16 passed | 206.05 |

Final union: **893 distinct tests across 40 complete modules: 889 passing and four
skipped**. The 95 S2 tests are included, not added again. Across eleven invocations
there are 1,139 passing executions, 11 intermediate failed executions and four skip
events. Every failed case passed after correction. Four skips are existing actual-
symlink privilege checks (three S1 and one managed-item); Windows junction checks
passed. Serial modules ran after workers exited. The complete inventory was not
repeated; follow-ups cover only changed/failing modules.

Earlier commands use the same `-q -p no:cacheprovider --basetemp "$E\<prefix>"
--junitxml "$E\<prefix>.xml"` arguments. Codec runs used
`tests/test_automatic_match_evidence.py -x`; `310-web-1` used
`tests/test_saved_match_analyses_web.py -x`; `310-focused-1/2` used `$Focused` with
`-n 2 --dist=loadfile --max-worker-restart=0`. Baseline selectors were
`tests/test_automatic_learning_store.py::test_storage_roundtrip_does_not_admit_synthetic_reports`
and `tests/test_local_match_capture_web_analysis.py::test_analysis_state_is_curated_and_execution_does_not_save`.
The fixture-correction command used the one module and table's `-k` expression,
without workers.

Three targeted standalone Ruff passes reported 35, 11 and one style/import/
line-length findings, all corrected. Final Ruff is included in Quick. Ambient `rg`
was unavailable for XML match-count accounting; external `310-accounting.py` then
computed the union/repeats from JUnit. That tool-availability failure is not a
pytest failure. One documentation patch initially failed its context match and
was reapplied without changing historical text.

**Final explicit Quick:** see the completion addendum below. Quick checks Ruff,
packaged-schema parity and input examples only. **Local Full was not run.** No
unrelated suite, distribution build/install, UAT build/start, hosted CI trigger or
installed acceptance was performed.

## Browser evidence and exact operation accounting

`scripts/verify_saved_match_analyses.py` uses existing dependency-free DevTools and
native-input helpers. It creates only a new synthetic home, independent manual
Corpus and fresh browser profile. Child stdin fault control is test-harness-only;
no production debug endpoint exists.

```powershell
py -3.13 scripts/verify_saved_match_analyses.py --output "$E\310-browser-final" --browser 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
```

The final probe passed in **89.352 s**, using headless **Edge 156.0.4314.50**.
Evidence: `%TEMP%\opencode\310-browser-final\evidence.json`, five PNGs,
`last-page.html` and three actual native browser downloads. Both process module
paths point into this checkout's `src/skatmind`; the real server process changed
from PID **9524** to **15500**. This is source-tree evidence, not installed UAT.

German/English work with JavaScript disabled. Keyboard activation of analysis,
saved Open and retry retained visible 3px focus outlines. Initial saved-execution
landing was at scroll position `0` with the correct heading. The saved list and
execution view were inspected at 390px; execution screenshots also cover 1100px.
Document width equalled viewport width, without horizontal overflow. Enhanced
language return preserved the exact saved capability and visible language-button
focus. Actual native downloads equal HTTP bytes; Result and Report-for-Learning
equal earlier live downloads. Restart rejects the old capability; a fresh capability
retrieves identical payloads without activating/resurrecting a recording. The later
saved-list language binding was additionally verified by the complete 16-test HTTP
module without rerunning unrelated browser scenarios.

The genuine fixture is Alex's recorded Decision 3 in synthetic Match Game 2,
Immediate with **one sample**, seed `0`. A second genuine execution uses seed `1`.
The simulated failure is an external harness `OSError` before its Report-object
write. No partial/timeout engine claim is made for this browser fixture.

| Phase delta | Executions | Successful archive temporary writes | Other persistent writes |
| --- | ---: | --- | --- |
| Fixture setup | 0 | 0 | One Match save; one independent manual-Corpus initialization |
| Passive entry/native decision selection | 0 | 0 | 0 |
| First explicit analysis | 1 | Source 1, Report 1, manifest 2 (initial + accepted commit) | Initial one-byte coordination file; four archive directories |
| Native views/disclosures/downloads | 0 | 0 | 0 |
| Explicit native German→English change | 0 | 0 | One frontend-profile save, initial revision 0 |
| Real restart/exact retained reads/downloads | 0 | 0 | 0 |
| Explicit enhanced English→German change | 0 | 0 | One frontend-profile save, revision 1 |
| Second analysis/controlled save failure | 1 | 0 (source reused; one failed Report write before bytes) | 0 |
| Save-only retry | **0** | **Report 1, manifest 1** | **0** |

Immutable publication adds corresponding no-clobber object links; manifests replace
corresponding same-directory temporaries. Temporary unlinking/advisory leases are
not extra evidence writes. There are **two genuine executions, two accepted
identities, zero Learning-artifact preparation calls**, and zero recording/manual-
Corpus changes. Retry preserves the second execution's exact identity. API/HTTP
regressions separately count this boundary, duplicate no-op, corruption,
supersession and pre/post-replacement failures. Limited-Search fixtures identify
themselves as controlled. Four-method complete and early inner-unavailable cases
use genuine executions. Elapsed-only coverage uses real Search with controlled
elapsed diagnostics instead of a machine-timing assertion.

Intermediate records are preserved: first browser invocation failed before setup
because the script lacked the repository-root import path; `310-browser-1` exposed
the probe's missing native Apply-selection prerequisite; `310-browser-2` exposed
its incorrect assumption that language used a select rather than two buttons.
Screenshot review also removed live-only expiry prose from the archived view.
`310-browser-3` then passed. The final repeat was justified by byte-order/final-
delivery hardening and added saved-list/landing evidence, not an extra timing run.

## Exact changed-file inventory

New:

* `src/skatmind/automatic_match_execution_codec.py`
* `src/skatmind/automatic_match_evidence.py`
* `src/skatmind/app_web/match_evidence_retention.py`
* `src/skatmind/app_web/saved_match_analyses.py`
* `tests/test_automatic_match_evidence.py`
* `tests/test_match_evidence_retention.py`
* `tests/test_saved_match_analyses_web.py`
* `scripts/verify_saved_match_analyses.py`
* `docs/ordinary_match_analysis_retention.md`

Modified:

* `src/skatmind/automatic_learning_store.py`
* `src/skatmind/match_decision_analysis.py`
* `src/skatmind/capture_web/analysis.py`
* `src/skatmind/learning_corpus_strategy_teacher_builder.py`
* `src/skatmind/app_web/context.py`
* `src/skatmind/app_web/form_registry.py`
* `src/skatmind/app_web/frontend_profile_operations.py`
* `src/skatmind/app_web/language_context.py`
* `src/skatmind/app_web/match_frontend.py`
* `src/skatmind/app_web/match_report_rendering.py`
* `src/skatmind/app_web/server.py`
* `src/skatmind/app_web/locales/de.json`
* `src/skatmind/app_web/locales/en.json`
* `tests/test_frontend_localization_foundation.py`
* `tests/test_frontend_validation_preservation.py`
* `tests/test_guided_frontend_packaging.py`
* `scripts/validate_distribution_artifacts.py` (measured private inventory only)
* `docs/automatic_learning_integration_contract.md`
* `docs/automatic_learning_store.md`
* `docs/match_analysis_and_exports.md`
* `docs/learning_corpus_strategy_teacher_evidence.md`

## Later maintainer installed targeted acceptance (not performed here)

After both exact-commit hosted gates, use the accepted installed interpreter from
an external working directory and a **new disposable synthetic home**, with no
checkout `PYTHONPATH` or real recordings. This is a short targeted scenario:

1. In German with JavaScript disabled, open the synthetic Match, explicitly apply
   its prepared decision selection and run one tiny ordinary analysis. Confirm
   completed/saved feedback; keep all three exact saved download bytes.
2. Stop the application and start a new process on that disposable home. Open
   Saved analyses without activating a Match. Select the exact original Report,
   check captured-source context and identical downloads. Repeat viewing/language
   return in English, still with JavaScript disabled.
3. In an **external Python test harness**, wrap installed
   `automatic_learning_io.write_temporary` in that test process only. A separate
   stdin/test-control event raises `OSError` only when the validated target is the
   disposable archive's `reports` directory, before the original writer. Count
   installed Match Application executor calls. Do not edit installed files,
   change ACLs, touch real data or add a production switch/route.
4. Run a second tiny analysis with a different seed. Confirm completed/not-saved
   feedback and intact live downloads. Disable the external fault, press Retry
   saving, and verify one new accepted identity, unchanged bytes and no extra
   evaluator call. Check concise retry feedback in the other language without
   inventing another execution.
5. Record installed module/build identity, exact commit, interpreter/browser,
   disposable source IDs, download digests and explicit operation/write counts.

The source-tree probe demonstrates the external fault-harness approach; its
source-path assertion/fixture imports are deliberately not installed acceptance
instructions. Direct maintainer PowerShell instructions follow separately after
CI. Keep #310 open until hosted CI and installed targeted acceptance pass.

## Completion addendum

Final explicit `.\scripts\check.ps1 -Mode Quick` passed on development CPython
3.13.7 / Windows 11 in **6.797 s**: Ruff **0.348 s**, packaged-schema parity
**0.190 s**, input examples **5.343 s**, all exit `0`. Logs:
`C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-s74f4df_`.
The checked source digest was
`d4e22b4db2f1d40cbdc75f430e947f2da6dfce75011e4bee593ddf80e0f22956`;
only this documentation completion receipt was added afterward. Quick does not
certify hosted full regression, generated outputs, distributions or installed
acceptance. Local Full was not run.

All tracked changes and nine new files were reviewed. `git diff --check` and
`git diff --no-index --check -- NUL <new-file>` passed without diagnostics.
`git diff --cached --stat` was empty. Final branch/HEAD match the starting values;
the worktree contains exactly the 30 intended files listed above. No unrelated
work was removed or overwritten, and no Git/GitHub publication action occurred.
