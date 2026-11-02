# Selected Match whole-game analysis retention (Issue #311, S3)

## Delivery and acceptance boundary

S3 retains explicitly executed managed selected-Decision whole-game analyses,
including their original assumptions, across application restarts. Both
`played_game_goal` and `complete_settlement` use the existing evaluator. Completed
comparisons and executed unavailable/partial/timeout/cancelled attempts are distinct
saved executions. The earlier completed live comparison stays selected after an
incomplete attempt.

Build-Mode baseline: branch `feat/311-match-rollout-evidence`, starting HEAD
`021bb2f7a963b6899462e238255abe805b01d1ea`, clean worktree, no baseline deviation.
The maintainer identifies S1 and S2 as accepted at this baseline. Their original
implementation, CI-follow-up and point-in-time pending-gate records remain intact.
This document is a separate S3 implementation record.

Product code changes. S3 does not finish automatic Learning integration: S4
membership/discovery/preparation, S5 maintenance UI, S6 Session and S7 saved
Historical Review remain subsequent stages. Recommendation adaptation remains an
intended later goal. Keep #311 and #208 open for new exact-commit hosted branch/main
`check` and `v1-supported-platform-matrix`, then narrow installed maintainer
acceptance. UAT-01 is not globally accepted, formal UAT-02–12 remain paused, and
release preparation is not authorized.

## Actual capture and strict resume

`execute_unified_match_rollout(..., app_context=...)` is the managed opt-in
boundary used by `POST /matches/review-whole-game`. It loads the exact saved
Workspace persistence document before execution. The existing core
`execution_observer` captures only the actual invocation/execution in memory.
The observer performs no persistence. Durable capture follows the frontend's
source, managed-file freshness, active/archive owner, generation, attempt and
selected-Decision checks and live publication. Standalone/core callers do not
implicitly acquire a managed archive.

The returned attempted Report and selected display Report remain separate.
Retention receives the new attempt's actual execution, even when the display is
an earlier complete Report. Form rejection, outer preparation unavailability and
exceptions without a successfully published execution never initialize the archive.
Executed inner availability can be saved despite the existing HTTP 400 presentation.

`automatic_match_rollout_evidence.py` defines the separate private `match_rollout`
object codec **2**, inner version **1**, producer `managed_match_rollout`, producer
contract **1**, explicitly supported Package version `0.17.0`. It retains:

* full typed Report and exact original persistence document/Snapshot dependency;
* original Match/Game/position/Decision, actor map, actual Card and before-Card cutoff;
* original unsupplemented Request, effective Request, derivation/reconstruction
  policy, effective declaration and explicitly originated manual supplements;
* objective, settings, budgets, work, coverage, status, candidates, all tied-best
  Cards and actual-card comparison;
* actual Application invocation, option presence, ordered mappings, Result,
  warnings, artifacts, provenance sources/linkage and serialization checkpoint;
* exact native Result and effective executable Request payloads, filenames and
  SHA-256 digests.

The closed private execution codec adds five explicit immutable constructors.
It recomputes Report identity and compares exact re-encoding; it never imports a
wire-named module. Existing option-presence and mapping-order rules remain intact.
Resume re-enters `validate_match_rollout_report_v1`, output-schema validation,
typed aggregate arithmetic/ranking, legal candidates, generic settings and exact
original-source reconciliation. It rebuilds the invocation from the retained
original Workspace/options for equality validation, without executing it. Complete
results re-enter `MatchDebriefEvidenceV1` with the exact original Snapshot as both
source and target. That contract remains complete-only. Executed incomplete
results use the same source reconciliation and strict method-specific validators,
without constructing a completed comparison or inventing ranking, recommendation,
fallback or `complete_search` qualification.

Automatic capture never substitutes a current or compatible manual target for the
original. Existing explicit same-revision compatible-target manual reconciliation
still retains its separate original and target Snapshots. No new manual ingestion
or automatic incorporation action is added.

### Shared source schema and compatibility

`build_managed_match_source` extracts S2's existing byte-for-byte codec-2 source
builder. Its historical header deliberately remains `managed_match_decision`.
SourceVersion identity still derives from the Match document kind/version/content,
not the Report family. Ordinary and rollout evidence on one exact source therefore
share one source record/object, before and after restart, without changing S2 bytes
or identities. S1 opaque codec-1 objects remain unsupported, even with copied typed
payloads. Unknown future codecs, producers, contracts and Package versions remain
unsupported; malformed known payloads are corrupt. Missing, corrupt,
dependency-unavailable and unsupported statuses stay distinct and no read repairs
or rewrites them. Ordinary Report-for-Learning codecs and Teacher admission still
reject `whole_game_rollout`.

## Durability, incomplete attempts and save-only retry

S3 reuses S1/S2's 16 MiB object bound, 512 MiB retained/staged total, independent
2,048-entry family quotas, bounded reservations, no-clobber dependencies, manifest
CAS, cooperating-process lease and reader pins. Final publication retains
Match-lock → app-lock → store-transaction order, with persisted-source freshness
checked at the final commit guard. Replacement remains authoritative after a
post-replacement failure; the service checks committed state without rollback or
new evaluation. Duplicate capture is idempotent. Exact execution identity stays
separate from debrief semantic grouping, which removes only `work.elapsed_ms`.
Seeds, budgets, supplements, source and meaningful Result differences remain
significant.

`PendingMatchRolloutSave` extends the existing one-per-owner bounded pending slot
with the exact attempt notice and selected display Report. An incomplete attempt
can belong solely to `active.rollout_notice`; it need not be inserted into the
eight-Report store. The ordinary S2 Report-store identity predicate remains strict.
Retry checks the exact notice, source, active/archive owners, attempt, generation,
selection and retained display Report. Correction, reload, owner replacement,
selection changes and superseding attempts expire the retry. Replayed tokens
conflict. Saving never re-enters the executor/evaluator.

The existing `POST /matches/retry-saving` form/route is reused with family-aware
ownership and navigation. For incomplete-after-complete, it returns to the earlier
completed Report and displays the separate attempt's truthful persistence receipt.
The localized receipt says that the **attempt** was saved or not saved; it does not
claim an incomplete execution completed successfully. Navigation may expire this
receipt/retry without expiring the earlier valid live comparison/downloads.
Final delivery still validates any receipt actually rendered, including HTTP 400.
A final conflict returns a value-free localized 409 instead of re-entering a stale
form renderer.

## Native saved access and exact exports

Navigation: open **Record a 36-game Match** (`/matches`) and follow **Saved analyses**
(`Gespeicherte Analysen`). This link is present before opening a Match. The direct
read-only entry is **`/matches/saved-analyses`**. The list contains both families;
rollout captions add method, objective and execution status to original
Match/Game/Decision/actor, captured revision, source fingerprint and Report identity.

`/matches/saved-analyses/<fresh-process-capability>` renders the retained comparison
or availability explanation, original before-Card context and assumptions. Its
`/result.json` and `/request.json` downloads use precisely the existing
`build_match_report_result_export_v1` and `build_match_rollout_request_export_v1`
bytes/filenames. The Request is the effective executable Request, not a new public
format for the original unsupplemented Request. Rollouts expose no
`strategy-source.json` download or live debrief-transfer/recording link. Ordinary
entries retain their existing three downloads and concise presentation.

Archive-owned URLs replace the renderer's live Report URLs; old process
capabilities expire. Pins protect the dependency closure through delivery, and
owner/manifest/admission checks run again after rendering/serialization. Both saved
list and exact execution retain existing native/enhanced language-return ownership.
Saved retrieval needs no active Match. A corrected or missing editable recording
does not change the original captured revision or establish current membership.
Passive viewing, restart loading, downloads and navigation execute no analysis,
prepare no Learning artifact and write no archive. Explicit language changes
retain their separately accounted profile saves.

Measured inventories: **74 POST routes, 126 forms, 2,158 keys per locale**.
The route/form totals stay unchanged because retry is generalized narrowly.
`test_direct_match_evidence.py`, packaging/guided-packaging and the distribution
smoke's exact 74/126 assertions were inspected and executed as source tests; those
expectations remain correct. Only the exact catalog count changes from 2,151 to
2,158. The #310 lazy context factory and lightweight `app --help` boundary remain
covered by their complete modules.

## Complete affected inventory and actual commands

Development interpreter: **CPython 3.13.7**,
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
Every validation invocation used a **7,200,000 ms** harness timeout. Evidence and
pytest temporary homes are outside the repository under `$E` below.

The inventory follows the common archive/codec callers, managed execution/retry,
source/Teacher compatibility, rollout/debrief and native downloads, shared Report
rendering, selection/language/feedback/final delivery, context/help, exact private
registries, packaged resources and strict rename. It contains **54 complete
parallel modules plus three complete exclusive modules**. The standalone Corpus
server's exclusive module is not affected: its transport and preparation are
unchanged. Exclusive modules ran only after all parallel workers exited.

The arrays below abbreviate the exact expanded module order/arguments used:

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
  'tests/test_automatic_match_rollout_evidence.py',
  'tests/test_match_rollout_retention.py',
  'tests/test_saved_match_rollouts_web.py',
  'tests/test_match_analysis_report_source_export.py',
  'tests/test_learning_corpus_strategy_teacher.py',
  'tests/test_learning_corpus_strategy_teacher_search.py',
  'tests/test_learning_corpus_information_set_strategy_teacher.py',
  'tests/test_learning_corpus_strategy_teacher_export.py',
  'tests/test_local_match_capture_web_analysis.py',
  'tests/test_match_decision_selection_web.py',
  'tests/test_match_decision_selection_script.py',
  'tests/test_match_learning_report_discoverability.py',
  'tests/test_analysis_download_details.py',
  'tests/test_match_analysis_exports.py',
  'tests/test_match_analysis_contracts.py',
  'tests/test_match_decision_analysis.py',
  'tests/test_match_information_set_search.py',
  'tests/test_recorded_review_navigation.py',
  'tests/test_unified_local_app_web.py',
  'tests/test_unified_local_app_managed_items.py',
  'tests/test_unified_local_app_contracts.py',
  'tests/test_app_cli.py',
  'tests/test_direct_match_evidence.py',
  'tests/test_learning_report_attachment.py',
  'tests/test_learning_report_attachment_web.py',
  'tests/test_frontend_localization_foundation.py',
  'tests/test_complete_frontend_localization.py',
  'tests/test_frontend_language_switching.py',
  'tests/test_language_switch_context.py',
  'tests/test_language_view_continuity.py',
  'tests/test_language_view_script.py',
  'tests/test_task_first_language_preservation.py',
  'tests/test_frontend_validation_preservation.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_skatmind_rename.py',
  'tests/test_recorded_decision_context_web.py',
  'tests/test_analysis_explanations_web.py',
  'tests/test_match_rollout_web.py',
  'tests/test_match_rollout_review.py',
  'tests/test_match_debrief.py',
  'tests/test_learning_debrief_web.py',
  'tests/test_rollout_result_presentation.py',
  'tests/test_task_first_stateful_rendering.py',
  'tests/test_operation_feedback_web.py',
  'tests/test_operation_feedback_language.py',
  'tests/test_operation_feedback_script.py'
)
$New = @('tests/test_automatic_match_rollout_evidence.py',
  'tests/test_match_rollout_retention.py', 'tests/test_saved_match_rollouts_web.py')
py -3.13 -c "import sys; print(sys.executable); print(sys.version)"
py -3.13 -m pytest tests/test_automatic_match_rollout_evidence.py tests/test_saved_match_analyses_web.py::test_rollout_enters_separate_family_and_rejects_ordinary_teacher -q -p no:cacheprovider --basetemp "$E\311-red" --junitxml "$E\311-red.xml"
py -3.13 -m pytest tests/test_automatic_match_rollout_evidence.py -q -p no:cacheprovider --basetemp "$E\311-codec" --junitxml "$E\311-codec.xml"
py -3.13 -m pytest tests/test_automatic_match_rollout_evidence.py -q -p no:cacheprovider --basetemp "$E\311-codec-2" --junitxml "$E\311-codec-2.xml"
py -3.13 -m pytest tests/test_match_rollout_retention.py -q -p no:cacheprovider --basetemp "$E\311-retention-red" --junitxml "$E\311-retention-red.xml"
py -3.13 -m pytest tests/test_match_rollout_retention.py tests/test_saved_match_analyses_web.py::test_rollout_enters_separate_family_and_rejects_ordinary_teacher -q -p no:cacheprovider --basetemp "$E\311-retention" --junitxml "$E\311-retention.xml"
py -3.13 -m pytest @New -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\311-focused" --junitxml "$E\311-focused.xml"
py -3.13 -m pytest tests/test_automatic_match_rollout_evidence.py tests/test_saved_match_rollouts_web.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\311-corrected" --junitxml "$E\311-corrected.xml"
py -3.13 -m pytest tests/test_saved_match_rollouts_web.py -q -p no:cacheprovider --basetemp "$E\311-delivery" --junitxml "$E\311-delivery.xml"
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\311-affected" --junitxml "$E\311-affected.xml"
py -3.13 -m pytest tests/test_saved_match_analyses_web.py tests/test_saved_match_rollouts_web.py tests/test_match_decision_selection_web.py tests/test_match_rollout_web.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\311-navigation" --junitxml "$E\311-navigation.xml"
py -3.13 -m pytest tests/test_early_rejection_observer.py tests/test_unified_rejection_transport.py tests/test_match_analysis_action_placement.py -q -p no:cacheprovider --basetemp "$E\311-exclusive" --junitxml "$E\311-exclusive.xml"
```

| Invocation | Actual result | Console seconds |
| --- | --- | ---: |
| `311-red`, before Product changes | 4 expected failures: absent rollout adapter and no managed retention | 2.97 |
| `311-codec` | 3 failures: constructor filtering dropped private option-presence replacement state | 3.61 |
| `311-codec-2` | 3 passed after preserving that state | 5.87 |
| `311-retention-red`, before managed-boundary changes | 1 expected failure: no managed rollout capture parameter | 0.90 |
| `311-retention` | 2 passed | 18.91 |
| `311-focused` | 89 passed, 8 failed | 271.82 |
| `311-corrected` | 57 passed, 5 failed | 162.43 |
| `311-delivery` | 17 passed | 248.71 |
| `311-affected` | 1,288 passed, 4 skipped, 3 failed | 1,787.28 |
| `311-navigation` | 72 passed | 498.27 |
| `311-exclusive` | 68 passed | 119.43 |

Final union: **1,363 distinct tests in 57 complete modules: 1,359 passed, four
skipped, no unresolved failures**. This includes the **98 tests in the three new
S3 modules**. Eleven pytest invocations contain 1,596 passing executions, 24 failed
executions and four skip events; repetitions are not additional distinct coverage.
Five failures were deliberate pre-implementation regressions. Four existing skips
require unavailable Windows symlink privileges (three automatic-store cases and one
managed-direct-child case); actual junction coverage passed.

The first focused run exposed two test exception-type expectations, an incorrect
test call to `StoredObjectV1.to_bytes` instead of `.raw`, and five actual HTTP-400
final-delivery bypasses. The next run exposed a test's attempt to read the actively
leased Windows coordination byte and four recursive stale-form error responses.
Tests now compare persisted JSON bytes separately from the lock; delivery rejection
uses a value-free 409. The full affected run exposed three prior-comparison
navigation regressions caused by applying expired receipt ownership to the whole
page. Suppressing only already-expired receipts preserves prior Reports; final
in-flight receipt races still reject. All affected HTTP modules then passed in
full. The entire broad inventory was not repeated merely to measure timing.

Two targeted Ruff invocations found 42 and then one import/unused-import/line-length
findings; all were corrected. One patch application needed corrected context;
no historical text was overwritten. Final Quick and whitespace receipts are
recorded in the completion section below. No local Full, unrelated suite,
distribution build/install, hosted execution or installed UAT was run.

## Disposable browser evidence and operation accounting

```powershell
py -3.13 scripts/verify_saved_match_rollouts.py --output "$E\311-browser-1" --browser 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
py -3.13 scripts/verify_saved_match_rollouts.py --output "$E\311-browser-2" --browser 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
```

The first probe stopped after **12.197 s**, before analysis, because the generic navigation helper
could not recognize the token redirect. Explicit Page navigation plus readiness
waiting corrected the harness. The second completed in **202.905 s**, using
headless **Edge 156.0.4314.58**, source-tree module paths and a real server-process
restart from PID **6292** to **30640**. Evidence is `$E\311-browser-2\evidence.json`,
five screenshots, `last-page.html` and two native browser downloads. Screenshots
were reviewed at 1100px and 390px in both locales, plus incomplete English at 390px;
complete-view document widths matched viewport widths. Native keyboard analysis,
saved Open and retry had visible 3px focus outlines. Enhanced language return
retained the exact saved execution and visible language-button focus.

The genuine synthetic fixture is Alex's already recorded Decision 3, actual C7,
two common worlds, complete settlement and explicit missing matadors `1` as an
analysis assumption. It produced the full tied-best set CK/C9/C7. The second
explicit attempt uses seed `1` and controlled cancellation at the real evaluator
seam, with an external reports-only `OSError` before any Report bytes. The script
guards **`application.execution.execute_application_invocation`**, the actual
whole-game seam, and the evaluator against passive/retry calls. No production
fault endpoint exists.

| Phase delta | Application executions / evaluations | Successful archive temporary writes | Other writes |
| --- | ---: | --- | --- |
| Fixture creation | 0 / 0 | 0 | One synthetic Match save |
| Passive entry and explicit Decision selection | 0 / 0 | 0 | 0 |
| Explicit complete analysis | 1 / 1 | Source 1, Report 1, manifest 2 (initial + accepted) | Four archive directories and one-byte coordination file |
| Controlled cancelled attempt / saving failure | 1 / 1 | 0; one failed Report write before bytes, source reused | 0 |
| Explicit save-only retry | **0 / 0** | Report 1, manifest 1 | 0 |
| Native saved views/downloads and German→English | 0 / 0 | 0 | One explicit profile save, revision 0 |
| Real restart, no active Match, complete/incomplete inspection and exact downloads | **0 / 0** | **0** | **0** |
| Enhanced English→German return | 0 / 0 | 0 | One explicit profile save, revision 1 |

Totals: two actual executions/evaluations, two accepted evidence identities, zero
Learning-artifact preparation calls and unchanged recording bytes. Immutable
publication uses corresponding no-clobber links; manifests replace same-directory
temporaries. Lease operations and temporary unlinking are not extra evidence
writes. Request digest:
`608c41e344899aefea7b5228c6395d71bfcbbd9fcf9f96a29d9fc2b85c397127`;
Result digest:
`95c2148706b6454e414292525241c59f350fb478f281c600467a13a5511d4a2a`.
Native downloads equal earlier live and later restarted bytes. Controlled partial,
timeout, cancellation, aggregate ties and storage-fault fixtures are labelled in
tests; the ordinary complete and missing-input inner-unavailable codec fixtures
execute genuinely. This is disposable source-tree evidence, not installed UAT or
genuine browser zoom. The later receipt-navigation correction was retested through
the complete four affected HTTP modules, without repeating the unrelated browser
sequence.

## Complete changed/new-file inventory

New:

* `src/skatmind/automatic_match_rollout_evidence.py`
* `tests/test_automatic_match_rollout_evidence.py`
* `tests/test_match_rollout_retention.py`
* `tests/test_saved_match_rollouts_web.py`
* `scripts/verify_saved_match_rollouts.py`
* `docs/match_rollout_analysis_retention.md`

Modified:

* `src/skatmind/automatic_learning_store.py`
* `src/skatmind/automatic_match_evidence.py`
* `src/skatmind/automatic_match_execution_codec.py`
* `src/skatmind/app_web/match_evidence_retention.py`
* `src/skatmind/app_web/match_frontend.py`
* `src/skatmind/app_web/match_rollout_frontend.py`
* `src/skatmind/app_web/match_report_rendering.py`
* `src/skatmind/app_web/saved_match_analyses.py`
* `src/skatmind/app_web/server.py`
* `src/skatmind/app_web/locales/de.json`
* `src/skatmind/app_web/locales/en.json`
* `tests/test_saved_match_analyses_web.py`
* `tests/test_frontend_localization_foundation.py`
* `docs/automatic_learning_integration_contract.md`
* `docs/automatic_learning_store.md`
* `docs/ordinary_match_analysis_retention.md`
* `docs/match_whole_game_review.md`
* `docs/learning_match_debrief.md`
* `docs/match_analysis_and_exports.md`

## Narrow installed maintainer scenario after CI (not executed here)

After both new exact-commit branch/main gates, use a separately installed build
from an external directory with a disposable synthetic home. Record exact commit,
build/module/interpreter/browser identity. No repeat of the accepted full S2
ordinary-analysis sequence is required.

1. Without JavaScript, open an **already recorded Decision**; do not play its Card
   again. Execute one bounded complete-settlement rollout with an explicitly
   missing-input supplement. Confirm the actual Card, tied-best comparison and
   analysis-only assumption. Keep the two native export bytes/digests.
2. Restart the application. Before opening any Match, open `/matches`, follow
   **Saved analyses**, and open that exact captured execution. Check comparison,
   revision/source, assumptions and identical Request/Result downloads.
3. Repeat retained inspection and native language return in German and English,
   still without JavaScript. Confirm there is no rollout Report-for-Learning or
   expired live debrief/download link.
4. Correct the disposable recording through a supported operation. Reopen the
   exact Saved analysis and confirm that its earlier captured revision remains
   clearly identified and is not evidence for the corrected recording/current
   collection. Record the outcome as narrow installed acceptance only.

No distribution or installed environment was created or started for this issue.

## Completion receipt

**Locally validated; new exact-commit CI and narrow installed acceptance pending.**
Final explicit `.\scripts\check.ps1 -Mode Quick` (invoked as shown below) passed
with exit **0** on development CPython **3.13.7**, Windows 11
`Windows-11-10.0.26300-SP0`, in **5.777 s**. Stages: Ruff **0.199 s**,
packaged-schema parity **0.185 s**, input examples **5.043 s**, all exit 0.
Logs: `C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-8l9zowok`.
Source digest: `ded460ca0b5525e309314731c8fd5cc360b5ed3bec91fcefdbf1aac2db79ccd4`.
Only this documentation receipt was added after Quick. Quick does not certify
generated outputs, distributions, installations or the full regression suite.
**Local Full was not run**, as explicitly required for this task.

```powershell
$Lint = @(
  'src/skatmind/automatic_match_evidence.py',
  'src/skatmind/automatic_match_execution_codec.py',
  'src/skatmind/automatic_match_rollout_evidence.py',
  'src/skatmind/automatic_learning_store.py',
  'src/skatmind/app_web/match_evidence_retention.py',
  'src/skatmind/app_web/match_frontend.py',
  'src/skatmind/app_web/match_rollout_frontend.py',
  'src/skatmind/app_web/saved_match_analyses.py',
  'src/skatmind/app_web/match_report_rendering.py',
  'src/skatmind/app_web/server.py',
  'tests/test_automatic_match_rollout_evidence.py',
  'tests/test_match_rollout_retention.py',
  'tests/test_saved_match_analyses_web.py',
  'tests/test_saved_match_rollouts_web.py',
  'scripts/verify_saved_match_rollouts.py'
)
py -3.13 -m ruff check @Lint # first: 42 findings; second: 1 finding
py -3.13 "$E\311-accounting.py"
py -3.13 -c "from skatmind.app_web.server import UNIFIED_FRONTEND_POST_ROUTES; from skatmind.app_web.form_registry import FRONTEND_FORM_REGISTRY; from skatmind.app_web.translation_catalog import load_frontend_translation_catalogs_v1; print('POST routes:', len(UNIFIED_FRONTEND_POST_ROUTES)); print('Forms:', len(FRONTEND_FORM_REGISTRY)); print('Catalogs:', {key: len(value) for key, value in load_frontend_translation_catalogs_v1().items()})"
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
# Each of the six new files, accepting exit 0/1 only with no whitespace diagnostics:
git diff --no-index --check -- NUL <new-file>
git diff --cached --stat
git status --short
git branch --show-current
git rev-parse HEAD
```

The external accounting helper reconciles actual JUnit identities/outcomes from
all eleven invocations; no unresolved failure remains. All changed/new files were
reviewed, and tracked plus new-file whitespace checks passed without diagnostics.
The exact changed-file inventory above contains **25 intended files**. Staging is
empty; all changes remain **unstaged and uncommitted**. Branch and current HEAD
remain the verified starting values. No unrelated work was present, removed or
overwritten. No commit, stage, push, branch change, Actions trigger, issue mutation,
distribution/install/UAT or release operation occurred.
