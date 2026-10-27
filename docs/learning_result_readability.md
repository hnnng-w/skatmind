# Concise, actionable Learning results (Issue #300)

## Checkout and implemented presentation

The verified starting checkout was clean, on
`bug/300-learning-result-readability`, at
`19054040ba4e7b11cd887896f25e8512c57f6391`. The implementation leaves changes
unstaged and uncommitted for the maintainer.

The reported 30 recorded / 30 reconstructed / zero skipped / one included
analysis-evidence item exposed a presentation problem. A real disposable fixture
with those quantities reproduces it; its motif count is not forced to 77.
The new hierarchy is:

1. One **Learning review** heading at the existing `learning-results` identity.
2. Represented Match summaries, recorded decisions and safely reconstructed
   before-Card records, followed by the retained conclusion or actual focuses.
3. **Included data**: exact selected Match revision/variant captions and readable,
   exact-bound analysis-source descriptions, with references to existing controls.
4. **Technical details and downloads**: retained counters, reconstruction coverage,
   localized actual partition reasons, defensive raw facts, and ten short native
   download anchors in their existing three purpose groups.

The two inner native disclosures start closed on fresh explicit navigation.
No control or text size is reduced. Existing result typography/wrapping selectors
now target the result container rather than descendants of its heading.
The #299 attachment disclosure remains outside technical results and before
preparation, including rejection/blocker opening and file-input error association.

## Private display boundary and exact meanings

`learning_result_projection.py` creates frozen, invocation-local display values
from retained objects captured under the Corpus context lock. The server calls
`require_learning_corpus_prepared_bundle_v1` before projection. The display has
strings, counts and immutable tuples, not complete Reports, Requests, Cards, source
objects or an independent authorization. Rendering performs no source reads,
analysis, reconstruction, reconciliation or export serialization.

The existing exact owner, source revision/generation, prepared object identities,
Catalog and cross-family fingerprints remain authoritative. Ordinary current-page
language/source capture now also checks a present bundle; partial/inconsistent
families cannot silently appear unprepared. Both ordinary and scoped prepared
HTML validate persisted Catalog/Snapshot sources before rendering and again before
delivery. Source changes during projection/rendering reject publication.

| Quantity | Meaning |
| --- | --- |
| `cross_game_match_count` | Represented Match summaries; not completed Games or versions |
| `observed_decision_count` | Recorded decisions accounted for by the Dataset |
| `record_count` | Safely reconstructed before-Card Dataset records |
| `skipped_decision_count` | Decisions without such a safe record |
| `strategy_teacher_evidence_count` | Normalized analysis-evidence items in the Dataset pool; not uploaded files, executions or distinct analyzed decisions |
| `joined_teacher_evidence_count`, `unjoined_teacher_evidence_count` | Exact retained Coaching joins/non-joins with tactical decisions |
| `teacher_covered_decision_count` | Distinct tactical decisions with joined analysis evidence |
| `complete_search_assessable_decision_count` | Retained decisions assessable by the existing complete-Search rule |
| `semantic_teacher_group_count` | Distinct retained semantic analysis groups; duplicate exact Reports do not multiply decision coverage |
| `tactical_motif_occurrence_count` | Structural occurrences, potentially several per decision |
| `focus_area_count` | Existing qualified Player/topic focus pairs |

No percentage, quality score, completed-Game inference or count relabeling is added.
Zero remains zero; malformed/unknown/contradictory minimized metadata keeps literal
diagnostics and uses a neutral explanation. The source-bound minimized Corpus state
is unchanged. The new display projection is never retained in that state or a cache.

Conditional explanations distinguish absent preparation; empty, partial, complete
and unavailable reconstruction; no joined evidence; retained unjoined evidence;
one covered decision (including multiple Reports); Immediate-only assessments;
other non-assessable evidence; mixed complete-Search assessments; and assessable
evidence without a retained recurring focus. These are private presentation choices,
not a new global no-focus-reason domain enum. They do not select eligible decisions,
recalculate consensus, change thresholds, infer perfect play or promise that one
more Report will produce a focus.

Qualified focuses use retained Player-report order and per-Player priority. The
shared renderer shows the localized topic, unchanged fixed Guidance meaning, exact
Decision/Game/Match counts and supporting decisions in a native disclosure. Captions
resolve exact Snapshot/Game/Decision references; equal Player names and Game 1 in
different identically named Matches remain distinguishable. Display ordinals are
not persisted identities or chronology. Selected older versions are never called
latest. Existing revision/variant mapping is shared with attachment presentation.

On a unified collection page the focus list appears only in the Learning result.
An independent whole-game-comparison debrief remains when incorporated sources
exist. With prepared results and no such sources, its empty panel is omitted.
Standalone and Player-filtered debriefs retain their focuses and comparisons.
Imported Decision evidence creates neither whole-game comparison rows nor live
Match Report capabilities. Supporting references are in-page content, not invented
routes. The optional next action is the existing GET `/review/recorded`, labelled
as choosing a recorded decision; it runs no analysis.

## Native navigation and compatibility

#293's fragment-free `/learning/prepared/<scope_id>` remains the common View and
successful preparation destination, with one actual natively focused heading.
Ordinary entry stays compact. Rejected recreation keeps the prior valid result;
error focus takes priority. Receipts retain their one-use/lifetime semantics.
After an enhanced receipt's Dismiss control, the meaningful next keyboard target
is the chooser or first supporting-decisions disclosure. Empty/unavailable results
continue to Included data. Downloads require explicit disclosure opening.

Enhanced verified language return restores disclosure state (including a manually
closed outer result), viewport and language-button focus. Native language return
retains server defaults without inventing unsupplied client disclosure state or
refocusing the result. Opening details performs no request, preparation or download.
All ten canonical routes, filenames, bytes, headers and native `download` attributes
are retained. Domain Coaching, Dataset information boundaries, persistence, public
contracts, package/release metadata and export families are unchanged.

## Complete affected-module inventory and commands

Supported process-local interpreter: **CPython 3.13.7**, Windows PowerShell 5.1;
Actual host: **Windows 11 10.0.26300**, PowerShell **5.1.26100.9711**.
Node **24.16.0** is available for existing script tests. No installed UAT environment
or real managed data is used. The task-specific routine is complete affected modules
and final explicit Quick, not local Full.

The affected inventory follows the changed result/source/focus renderers, their
server/debrief callers, language publication guard and directly consumed retained
Coaching/Dataset contracts. It includes strict rename, packaging and localization.
The parallel command covers **53 complete modules**:

```powershell
py -3.13 -m pytest `
  tests/test_learning_result_readability.py tests/test_learning_result_explanations.py `
  tests/test_learning_prepared_navigation.py tests/test_learning_outcome_navigation.py `
  tests/test_learning_entry_purpose.py tests/test_learning_direct_entry_web.py `
  tests/test_learning_source_navigation.py tests/test_learning_overview_navigation.py `
  tests/test_learning_version_presentation.py tests/test_learning_version_selection_web.py `
  tests/test_learning_debrief_web.py tests/test_match_debrief.py `
  tests/test_learning_report_attachment.py tests/test_learning_report_attachment_web.py `
  tests/test_learning_report_rejection.py tests/test_match_learning_report_discoverability.py `
  tests/test_analysis_download_details.py tests/test_task_first_stateful_rendering.py `
  tests/test_task_first_stateful_projections.py tests/test_task_first_match_and_learning_workflow.py `
  tests/test_unified_local_app_web.py tests/test_unified_local_app_managed_items.py `
  tests/test_frontend_language_switching.py tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py tests/test_language_view_script.py `
  tests/test_task_first_language_preservation.py tests/test_frontend_validation_preservation.py `
  tests/test_operation_feedback.py tests/test_operation_feedback_web.py `
  tests/test_operation_feedback_language.py tests/test_operation_feedback_script.py `
  tests/test_recorded_review_navigation.py tests/test_recorded_decision_context_web.py `
  tests/test_session_recorded_review_web.py tests/test_learning_corpus_web_core.py `
  tests/test_learning_corpus_web_uploads.py tests/test_learning_corpus_tactical_coaching.py `
  tests/test_learning_corpus_tactical_motif.py tests/test_learning_corpus_strategy_teacher.py `
  tests/test_learning_corpus_strategy_teacher_search.py tests/test_learning_dataset_v2.py `
  tests/test_learning_dataset_v2_cross_game_summary.py tests/test_learning_dataset_v2_partition_preparation.py `
  tests/test_learning_corpus_match_snapshot.py tests/test_match_analysis_report_source_export.py `
  tests/test_match_rollout_web.py tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py `
  tests/test_profile_driven_creation_packaging.py tests/test_guided_frontend_packaging.py `
  tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py `
  -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest `
  --validation-report="$env:TEMP\opencode\issue300-affected-parallel-02.json" `
  --durations=15 --tb=short -rs
```

Only after both workers exit, the **four complete exclusive modules** run:

```powershell
py -3.13 -m pytest tests/test_early_rejection_observer.py tests/test_local_learning_corpus_web.py tests/test_unified_rejection_transport.py tests/test_match_analysis_action_placement.py -q -p scripts.validation_pytest --validation-report="$env:TEMP\opencode\issue300-affected-serial.json" --durations=10 --tb=short -rs
function python { & py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
```

The sole observed platform skip is the existing Windows symbolic-link privilege
check in `test_unified_local_app_managed_items.py`; it is not counted as a pass.
Final complete parallel run: **1,031 passed / one skipped in 494.14s**. The exclusive
serial run, after both workers exited: **95 passed in 72.67s**, no skips. Together:
**57 complete modules / 1,126 distinct passes / one skip**.

Final review made selected-Snapshot titles take precedence over later discovery
titles, while preserving the attachment renderer's existing first-discovered
fallback. Both positive locale cases now explicitly test that distinction.
The 12 complete modules affected by this refinement passed **200 tests in 113.91s**
with no skips; these overlap the 1,126 distinct passes above:

```powershell
py -3.13 -m pytest tests/test_learning_result_readability.py tests/test_learning_result_explanations.py tests/test_learning_report_attachment.py tests/test_learning_report_attachment_web.py tests/test_learning_report_rejection.py tests/test_learning_version_presentation.py tests/test_learning_version_selection_web.py tests/test_learning_source_navigation.py tests/test_learning_debrief_web.py tests/test_match_debrief.py tests/test_task_first_stateful_rendering.py tests/test_task_first_match_and_learning_workflow.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest --validation-report="$env:TEMP\opencode\issue300-final-label-modules.json" --durations=10 --tb=short -rs
```

After this documentation update, the complete strict rename, distribution packaging,
profile-driven packaging and localization modules are rechecked before final Quick:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py tests/test_profile_driven_creation_packaging.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py -q --tb=short
```

Final Quick logs and this overlapping documentation-sensitive result are reported
in the completion handoff, avoiding an unvalidated post-Quick edit.

### Intermediate regression evidence

* Initial delivered-HTML regression: **2 expected failures in 7.96s**, both locales,
  against the actual former heading and hierarchy after genuine 30/30/0/1 preparation.
* First four-module development run: **118 passed / 20 obsolete-presentation failures
  in 76.23s**. Replacements retain units, exact downloads, privacy and native hierarchy.
* Expanded five-module run: **158 passed / 9 fixture failures in 72.89s**; corrected
  serializer/import assumptions, selected-decision expectation and strict method options.
* New module development: **7 passed / 2 fixture-option failures in 27.39s**, then
  **19 passed / 1 real publication-guard failure in 58.50s**. The latter established
  the missing final persisted-Catalog validation on ordinary current-page delivery;
  the current-page publication guard now checks it, retaining the test.
* First complete parallel inventory: **1,027 passed / 4 obsolete assertions / one
  platform skip in 422.87s**. The four assertions concerned the old heading,
  superseded count wording and repeated current-results boilerplate.
* Corrected complete affected modules plus strict rename/packaging: **62 passed in
  38.82s**. These overlap the final inventory and are not additional distinct passes.

## Disposable browser evidence

Commands use an existing browser binary with fresh disposable profiles and ephemeral
loopback ports. The external #299 probe is retained with its prior fixture code in
the approved scratch directory; it exercises emitted downloads and multipart forms.

```powershell
py -3.13 scripts/verify_learning_result_readability.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$env:TEMP\opencode\issue300-browser-06"
py -3.13 scripts/verify_learning_prepared_navigation.py --phase after --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$env:TEMP\opencode\issue300-navigation-browser-02"
py -3.13 "$env:TEMP\opencode\issue299_rejection_browser.py" --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$env:TEMP\opencode\issue300-attachment-browser-01"
```

The readability verifier covers eight cases: genuine one-item no-focus and controlled
retained-Search focus fixtures, each in German/English with JavaScript off/on. The
focus fixture uses real source import, reconciliation and preparation with an explicitly
controlled Search-result producer; it does **not** claim a real Search execution.
It retains two identically named Matches, Game 1 in each, same-revision alternatives,
equal Player names, two Players with focuses, and long/escaped captions.

Screenshots of the initial POST/303/GET and explicit View landings precede verifier
scroll/focus or next-Tab probes. Native Tab/Enter/Space and pointer actions verify
disclosures, keyboard order, visible focus, initially closed technical details,
desktop 1365 x 900 and narrow 390 x 900 layout, language restoration and manually
closed results. Actual browser: **headless Microsoft Edge 156.0.4314.42**, fresh
profile **100% zoom**, measured device pixel ratio/visual viewport scale **1**.
No horizontal document overflow was observed. Viewport resizing is not 200% zoom;
genuine 200% remains for installed targeted acceptance.

The #293 probe covers explicit/repeated View, refresh, rejected recreation retaining
valid outputs, error-focus priority, verified viewport/disclosure/focus return and
competing collection change. The #299 probe covers actual ordinary-Result rejection,
the one real file-input error link/ARIA association, empty file input, translated
errors and correct-file retry with applied/duplicate receipts.

Readability run `-03` passed in **145.020s**. Extended run `-04` passed in **165.457s**,
adding explicit version-selection invalidation and Search/Catalog counters. Their
screenshots were inspected. Earlier `-01` and `-02` were incomplete verifier probes:
they exposed omitted JavaScript `undefined` fields and capture before document/style
load had completed. The verifier now waits for normal completion without focusing
or scrolling the destination. The first concurrent #293 probe similarly sampled a
transitional null active element; its corrected second run completed all four cases.
The #299 reuse probe passed all four cases in **51.529s**. Readability run `-05`
passed in **157.231s** after explicit closure binding for lint; final run `-06`
passed all eight cases in **154.340s** after the selected-title refinement above.
All final evidence directories contain `completed: true`. Incomplete probes are
not acceptance evidence.

### Operation/write accounting

Per case, explicit fixture creation/import/attachment/preparation is separate from
browser preparation and passive viewing. Real Immediate fixture execution is separate
from the controlled-Search source production. The source recording fixture writes
its disposable file before navigation. Counters cover analysis/Search, preparation,
Dataset/Tactical reconstruction, Teacher reconciliation, import, selection, reload,
Product-ID generation, and Session/Match/Catalog/Snapshot/Profile writes.

Passive navigation, disclosure and download phases have zero added operations/writes.
Prepared object identities, source generations/revisions, persistent bytes and all
ten actual download byte strings remain equal. Download files, hashes, dispositions,
request sequences, counters and screenshots are under each case's evidence directory.
Two actual language changes each make one existing Profile write, recorded separately;
other persistent files remain equal. Deliberate prepared-object replacement, actual
version selection and source changes during rendering are separate invalidation probes.
The old destination rejects rather than combining old explanation with newer sources.
Existing bounded navigation-scope bookkeeping is not counted as a Product ID.

## Changed-file inventory and handoff

Product files:

* `src/skatmind/app_web/learning_result_projection.py` (new private immutable projection)
* `src/skatmind/app_web/learning_focus_rendering.py` (new shared focus presentation)
* `src/skatmind/app_web/learning_source_labels.py` (narrow shared exact caption mapping)
* `src/skatmind/app_web/learning_result_rendering.py`
* `src/skatmind/app_web/task_first_learning_rendering.py`
* `src/skatmind/app_web/debrief_rendering.py`
* `src/skatmind/app_web/server.py`
* `src/skatmind/app_web/language_context.py`
* `src/skatmind/app_web/assets/app.css`
* `src/skatmind/app_web/locales/de.json`, `src/skatmind/app_web/locales/en.json`

Tests and developer verification:

* `tests/test_learning_result_readability.py` (new)
* `tests/test_learning_result_explanations.py`
* `tests/test_learning_prepared_navigation.py`
* `tests/test_learning_outcome_navigation.py`
* `tests/test_match_debrief.py`
* `tests/test_task_first_match_and_learning_workflow.py`
* `tests/test_frontend_localization_foundation.py`
* `scripts/verify_learning_result_readability.py` (new)
* `scripts/verify_learning_prepared_navigation.py`

Documentation: this file, `docs/learning_corpus_browser_workflows.md`,
`docs/learning_corpus_tactical_cross_game_coaching.md`,
`docs/learning_match_debrief.md`, and `docs/learning_prepared_result_navigation.md`.

Measured inventory: **73 POST routes, 125 registered forms, 2,115 keys per locale,
ten prepared downloads**. The 33 added paired keys have exact placeholder parity;
route/form and executable packaging assertions remain strict. No new POST/form,
schema, package version or export family is introduced.

After final local validation report **Locally validated, CI pending**. Keep #300 open
for exact-commit branch/main `check` and `v1-supported-platform-matrix`, then installed
targeted acceptance. #292–#299 remain complete; #208 remains open. UAT-01 is not globally
accepted, UAT-02–12 remain paused, and release preparation is not authorized. Full
maintainer UAT and current architecture/code analysis with treatment of material
findings remain required before v1.0.0. No local Full or installed maintainer UAT is
performed by this implementation task.
