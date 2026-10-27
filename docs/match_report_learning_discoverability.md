# Match Report download and Learning file attachment (Issue #299)

## Implemented boundary

The unified selected Match Report now exposes **Report for Learning (JSON)** within
its existing visible **Downloads for this analysis** group. The ordinary Result
remains distinct. The private state capability is separate from materialization's
`download_availability` map, so it cannot become an invented materialization route.
The shared download renderer's new argument defaults to absent for every other
caller.

The exact selected, current, retained, outer-`executed` Decision Report qualifies
under the existing source export methods. Whole-game rollout remains excluded.
Information-set inner unavailability does not change outer execution eligibility.
No collection is needed for download. Projection inspects the already validated
Report; the existing download builder still owns lookup, active ownership, revision,
persisted-source freshness, canonical serialization, filenames and error behavior.

Learning has one **Attach a report file** disclosure containing the existing multipart
upload, target description/selection, attached-source descriptions, removal and clear
controls. It follows **View prepared datasets** when present and precedes preparation
and results. Ordinary views are collapsed; non-current sources and rejected uploads
expose the remedy. The `learning-sources`, `learning-report-target` and
`report-attachment-feedback` identities are retained. Validation still focuses the
real error/field, including when no target is available. File content is never restored.

The upload's explicit compatible Current Snapshot and existing Decision reconciliation
are authoritative, independently of the open Match. Metadata-only same-revision
alternatives can reconcile; changed Game identities reject. The source store remains
process-local. Actual additions invalidate preparation; exact duplicate/no-op and
rejected input retain the objects and bytes specified by the existing contract.

The file path alone requests the new receipt. Authoritative `applied` and `unchanged`
map to **Report attached.** and **Report already attached.**, respectively, under the
existing lock and one-use feedback lifecycle. Native first delivery works without
JavaScript. Refresh cannot replay it. Existing enhanced language continuation can
translate the remaining authorized display budget; native language changes do not
recreate consumed feedback. Errors suppress old success. No new receipt store,
timeout, route, form, schema, persistence field or export format is introduced.

Direct Match transfer retains its independent Match-return feedback; whole-game
rollout retains separate incorporation and debrief. Standalone Capture continues to
offer **Download for Learning Corpus**. The complete user path and source contract
are in [Learning Corpus browser workflows](learning_corpus_browser_workflows.md#unified-optional-attachment-issue-259).

## Checkout and regression evidence

Implementation began on `bug/299-learning-report-discoverability` at
`26224222869dd25bdd27ab54a8bf9b028bb54924`, with a clean worktree. The agent leaves
all changes unstaged and uncommitted. No branch, GitHub, installed UAT environment,
or real managed data was modified.

The first regression changed the existing real delivered-HTML selected-Report test:

```powershell
py -3.13 -m pytest tests/test_analysis_download_details.py::test_real_match_selected_report_owns_result_and_learning_source -q
```

It failed against the baseline in **8.41s** because the actual HTML omitted the
source anchor. The test retains exact older/newer Report ownership across two Games,
canonical source bytes/filename, unchanged Result bytes, and file/reload rejection.
The `python` command is an unavailable Windows App Execution Alias on this machine;
verification uses CPython **3.13.7** through `py -3.13`.

The new complete `test_match_learning_report_discoverability.py` exercises all four
eligible method families, complete and inner-unavailable Information-set execution,
ineligible outer/family cases, selected rollout alongside another retained eligible
Report, authorization, and emitted-link expiry after mutation/reload/activation/file
replacement/deletion/missing/evicted Reports. Guarded GET tests prohibit source
construction, serialization, Request rebuilding and execution during rendering.
Existing attachment tests now follow the emitted source anchor and submit its actual
bytes through the emitted multipart form. They cover zero/one/several targets, legacy
wrappers, malformed/plain Result input, wrong/stale targets, same-revision alternatives,
removal, duplicate retention, rejected-input preservation, bilingual receipts,
language continuity and independent direct-transfer feedback.

Intermediate runs exposed and corrected catalog key ordering and test-fixture
assumptions; they are not acceptance evidence. The two initial three-module runs
failed all 55 cases on catalog ordering (**11.84s**, **11.94s**). After that correction,
the three-module run had **53 passed / 2 failed in 42.87s** on a presentation specimen
that did not contain prepared results. Its ordering assertion moved to the genuine
prepared-result HTTP test. The five-module run then had **145 passed / 4 failed in
139.68s** on new test setup/options and pre-existing download error statuses. Corrected
fixture assertions preserved existing behavior; the new module passed **16/16 in
28.79s**. One attempted parallel inventory contained the nonexistent
`test_session_rollout_web.py`, ran **zero tests in 0.69s**, and was replaced with the
actual complete `test_session_rollout_review.py` and result-presentation coverage.

## Complete affected-module validation

The final parallel command below passed **1,115 tests**, with **one skip**, in
**382.53s**. The skip is
`test_unified_local_app_managed_items.py::test_managed_direct_child_validation_rejects_escape_and_links`:
this Windows account cannot create symbolic links. Strict rename and packaging
assertions remain intact. The command is line-wrapped only for readability:

```powershell
py -3.13 -m pytest `
  tests/test_analysis_download_details.py `
  tests/test_learning_report_attachment.py `
  tests/test_learning_report_attachment_web.py `
  tests/test_match_learning_report_discoverability.py `
  tests/test_match_analysis_report_source_export.py `
  tests/test_match_information_set_search.py `
  tests/test_match_rollout_web.py `
  tests/test_local_match_capture_web_analysis.py `
  tests/test_task_first_match_and_learning_workflow.py `
  tests/test_task_first_stateful_rendering.py `
  tests/test_unified_local_app_web.py `
  tests/test_unified_local_app_managed_items.py `
  tests/test_learning_prepared_navigation.py `
  tests/test_learning_debrief_web.py `
  tests/test_operation_feedback.py `
  tests/test_operation_feedback_web.py `
  tests/test_operation_feedback_language.py `
  tests/test_operation_feedback_script.py `
  tests/test_frontend_validation_preservation.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_frontend_language_switching.py `
  tests/test_complete_frontend_localization.py `
  tests/test_task_first_language_preservation.py `
  tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py `
  tests/test_language_view_script.py `
  tests/test_skatmind_rename.py `
  tests/test_packaging_and_distribution.py `
  tests/test_guided_frontend_packaging.py `
  tests/test_profile_driven_creation_packaging.py `
  tests/test_guided_frontend_result_presentation.py `
  tests/test_guided_frontend_web.py `
  tests/test_session_recorded_review_web.py `
  tests/test_session_rollout_review.py `
  tests/test_rollout_result_presentation.py `
  tests/test_candidate_comparison_layout.py `
  tests/test_learning_entry_purpose.py `
  tests/test_learning_outcome_navigation.py `
  tests/test_learning_result_explanations.py `
  tests/test_learning_version_presentation.py `
  tests/test_learning_source_navigation.py `
  tests/test_learning_version_selection_web.py `
  tests/test_learning_direct_entry_web.py `
  tests/test_match_evidence_navigation.py `
  tests/test_match_game_navigation.py `
  tests/test_recorded_decision_context_web.py `
  tests/test_recorded_party_presentation.py `
  tests/test_review_return_labels.py `
  tests/test_learning_corpus_web_uploads.py `
  -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest `
  --validation-report="C:\Users\HENNIN~1\AppData\Local\Temp\opencode\issue299-affected-parallel-02.json" `
  --durations=20 --tb=short
```

Only after both workers exited, the complete exclusive modules from
`scripts/validation_pytest.py` passed **95 tests in 60.89s**, with no skips:

```powershell
py -3.13 -m pytest tests/test_early_rejection_observer.py tests/test_local_learning_corpus_web.py tests/test_unified_rejection_transport.py tests/test_match_analysis_action_placement.py -q -p scripts.validation_pytest --validation-report="C:\Users\HENNIN~1\AppData\Local\Temp\opencode\issue299-affected-serial.json" --durations=10 --tb=short -rs
```

Together these are **53 complete modules / 1,210 passed / one skipped**. They cover
the changed renderers' callers, Session and generic Analyze/Review artifact sets,
Learning debrief/prepared navigation, feedback, validation/language preservation,
strict localization, source codecs, standalone Capture, rename and packaging.
The approved task-specific closure is explicit Quick, never local Full:

```powershell
function python { & py -3.13 @args }; .\scripts\check.ps1 -Mode Quick
git diff --check
```

Final Quick output and any documentation-sensitive recheck are recorded in the
completion handoff. Quick certifies Ruff, packaged-schema parity and input examples;
it does not replace exact-commit CI or installed acceptance.

## Disposable browser evidence

The external source-tree probe and all data live under the pre-approved scratch
directory. Exact final command:

```powershell
py -3.13 "C:\Users\HENNIN~1\AppData\Local\Temp\opencode\issue299_browser.py" --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "C:\Users\HENNIN~1\AppData\Local\Temp\opencode\issue299-browser-03"
```

This passed in **46.645s**, using real **Microsoft Edge 156.0.4314.42** in headless
mode with isolated disposable profiles, default **100% browser zoom**, device pixel
ratio and visual viewport scale `1`. Viewport resizing was not browser zoom.
`evidence.json`, actual downloads and per-state PNGs are retained in that directory.
Earlier probe runs corrected the external harness import path and its assumption
that a native HTTP-400 rejection returns at `/learning/current`; the actual rejection
retains the submitted operation URL. The second probe passed in **42.170s**; the final
probe adds source-control screenshots, Product-ID/Catalog write counters and actual
prepared-result focus navigation.

| Initial locale | JavaScript | Viewport | Primary interaction |
| --- | --- | --- | --- |
| English | on | 1365 x 900 | pointer |
| German | off | 1365 x 900 | native Tab/Enter |
| German | on | 390 x 900 | native Tab/Enter |
| English | off | 390 x 900 | pointer |

Each case opens the retained Report, activates the **emitted** source anchor,
compares the actual browser-downloaded file with canonical bytes, opens the named
disclosure, selects that downloaded file via DevTools' native file-input facility,
and submits the **emitted multipart form**. It verifies the exact bound Snapshot and
Report, applied and duplicate receipts, no refresh replay, plain ordinary-Result
rejection, file clearing, language return, retained prepared bytes, and the emitted
prepared-results link's native `learning-results` focus. Initial return screenshots
and active-element/scroll measurements precede any test-only scrolling or focusing.
Native keyboard activation checks `:focus-visible`; screenshots show readable wrapped
help and distinct download actions. No document overflow occurred at either width.
No CSS adjustment was needed. These are source-build technical probes, not installed
UAT or a claim of a complete browser/accessibility matrix.

### Operation and write accounting

Counters wrap the real operations; they do not replace execution or successful
mutation. Full managed JSON bytes are also compared across phases.

* Explicit fixture setup per browser case: one executed analysis; one generated
  collection identity; two Catalog saves (initialize/import), one Snapshot object
  publication, one creation Profile save, and one explicit preparation. A disposable
  saved Match fixture is written separately before ordinary navigation.
* View/download/disclosure and prepared-view navigation: zero analysis, preparation,
  Decision reconciliation, Session/Match/Catalog/Profile save, Snapshot publication,
  or generated Product ID; managed bytes unchanged.
* Explicit file addition: one existing Decision reconciliation and one process-local
  source binding; preparation invalidated; no persistent write or additional analysis.
* Explicit preparation after attachment: one preparation and its existing one-source
  reconciliation. This is recorded separately from attachment and navigation.
* Exact duplicate: one reconciliation, authoritative `unchanged`, same binding and
  prepared object, identical ten download artifacts and persistent files.
* Plain Result rejection: no reconciliation or Product write; existing source,
  prepared object and ten downloads retained; previous receipt suppressed.
* Deliberate setup/success/error language changes: Profile saves counted separately;
  no source attachment, analysis or preparation. No file content is restored.
* The new receipt adds no Product operation or persistent write.

Final measured inventory is **73 POST routes / 125 registered forms / 2,077 keys in
each locale / ten prepared Learning downloads**. Four paired messages were added
to the 2,073-key starting checkout; historical inventories remain historical facts.

## Acceptance and release gates

Report **Locally validated, CI pending** after the final local checks. Keep #299 open
for the maintainer's exact-commit branch/main `check` and
`v1-supported-platform-matrix` gates and installed targeted acceptance. #292–#298
remain complete. #208 remains open, UAT-01 is not globally accepted, and UAT-02–12
remain paused. Full maintainer UAT and the current architecture/code analysis with
treatment of material findings remain required before v1.0.0. Release preparation
is not authorized.
