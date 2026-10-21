# Prepared Learning result navigation (Issue #293)

## Confirmed defect and destination

The starting commit is `0f6e0ef4ea00aa6f9f96253dde928f9a05680ba6`, on
`bug/293-learning-result-navigation`. The former View link and successful
preparation redirect used `#learning-results` on a visible outer wrapper. The
actual result inside `learning-prepared-result` remained inside a closed
**Dataset preparation and exports** disclosure. The wrapper did not itself have
a closed ancestor. Neither historical cache behavior nor an exact scroll-position
cause was established.

The unified app now emits one exact private destination for explicit View and the
current successful preparation return:

```text
GET /learning/prepared/<64-lowercase-hex-collection-scope>
```

The emitted URL has no fragment, including its self-link. Repeated activation on
the result page therefore makes a real GET and reopens the result even after the
user manually closed the disclosure. Ordinary `/learning/current` retains its
compact defaults. All other disclosures keep their existing behavior.

## Availability and publication

The route reuses `collection_scope` and `resolve_scope`, including the existing
eight-scope bound. It requires a collection-owned scope whose owner is still the
same active Learning context. A Match-owned scope cannot authorize this page.
Reopen, collection switch, source/version changes and scope eviction invalidate
old destinations; another active collection is never substituted.

Scope lineage also retains primary prepared-object identity. Lookup alone is
insufficient: `require_learning_corpus_prepared_bundle_v1` narrowly extracts the
existing canonical-download checks for all three prepared families, their source
store, generation, source revision, Catalog identity and cross-family fingerprints.
It neither serializes a download nor prepares any artifact. The existing download
builder calls the same helper and keeps its canonical serializers and bytes.

The full Learning language/source binding includes prepared objects, last result,
discovery, relevant feedback, active Match workspace and Report references, and
source revisions. The new view uses that branch, not the narrower debrief-only
binding. Managed-directory validation and strict persisted Catalog/Snapshot load
checks run before rendering and again at final HTML delivery. Invalidation during
rendering rejects publication. Old language forms and already prepared native or
enhanced language returns cannot bypass subsequent owner/source/file changes.

Only the exact path is added to dispatch and the safe HTML return allowlist.
Malformed/unknown scopes, unsupported suffixes, arbitrary query parameters,
external submitted return URLs and submitted fragments remain rejected. The
existing authenticated one-use `_language_return` transport remains separate;
it is not accepted inside submitted `return_to` values.

## Native focus, language continuity and feedback

Explicit result navigation delivers an already-open disclosure. The unique
`learning-results` ID is on the actual result's `h2`, with `tabindex="-1"` and
narrowly identifiable native `autofocus`. A heading-sized target avoids centering
a very tall result region with its heading outside the viewport. JavaScript is
not required to open or focus the result.

The preparation receipt is associated with the visible result. With enhancement
its existing Dismiss button can be the next Tab destination while the receipt is
present; otherwise the next destination is the first result download. Passive
View and Refresh never manufacture or replay a preparation-success receipt.
Ordinary entry retains visible one-use feedback outside its compact disclosure.

Validation feedback is applied before the final result-focus decision. An error
summary suppresses result autofocus even on a 200 GET containing retained errors.
A rejected recreation retains its previous valid bundle, values and downloads;
it does not redirect successfully merely because an older result exists. Valid
empty and partial outcomes remain successful prepared results with their original
qualifications and download availability.

Language forms retain the exact scoped path. Verified language return suppresses
the identifiable result autofocus through the existing language-return mechanism,
as it already does for retained error autofocus. A language return is not a new
View command and adds no fragment jump. Native return retains the valid result
view with its server-open disclosure, without result autofocus. Enhanced return
also restores verified disclosure state (including manually closed), viewport
and language-button focus. Unsupplied native disclosure state is not invented.

## Passive-operation guarantees

View, repeated View and Refresh execute no preparation, analysis, import,
selection or reload, and write no recording, Catalog or profile. Existing
process-local scope retention and one-use receipt handling remain allowed.
A deliberate language change keeps its existing single profile write; it is
accounted separately. Prepared object identities, source generations/revisions,
recording/Corpus bytes and all ten canonical download bytes remain unchanged.

## Verification and reproducible commands

Verification used process-local CPython **3.13.7**, Windows and PowerShell 5.1.
The Python installation was placed first on `PATH` for commands that invoke
`python`; no environment configuration was persisted:

```powershell
$env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python313;$env:LOCALAPPDATA\Programs\Python\Python313\Scripts;" + $env:PATH
```

The initial new HTTP regression failed on the old fragment-only destination:
`py -3.13 -m pytest tests/test_learning_prepared_navigation.py -q` reported
**1 failed in 1.82s**. Before correction, the real-browser verifier reproduced the
closed actual result in all four locale/JavaScript combinations using a genuine
30-decision disposable collection. The baseline evidence is not an inference from
text presence or an outer-wrapper bounding box.

Complete affected-module command (26 modules):

```powershell
python -m pytest `
  tests/test_learning_prepared_navigation.py `
  tests/test_learning_outcome_navigation.py `
  tests/test_learning_result_explanations.py `
  tests/test_learning_entry_purpose.py `
  tests/test_learning_direct_entry_web.py `
  tests/test_learning_source_navigation.py `
  tests/test_learning_overview_navigation.py `
  tests/test_learning_debrief_web.py `
  tests/test_task_first_match_and_learning_workflow.py `
  tests/test_frontend_language_switching.py `
  tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py `
  tests/test_language_view_script.py `
  tests/test_task_first_language_preservation.py `
  tests/test_operation_feedback_web.py `
  tests/test_operation_feedback_language.py `
  tests/test_frontend_validation_preservation.py `
  tests/test_learning_corpus_web_core.py `
  tests/test_local_learning_corpus_web.py `
  tests/test_unified_local_app_web.py `
  tests/test_unified_local_app_managed_items.py `
  tests/test_task_first_stateful_rendering.py `
  tests/test_complete_frontend_localization.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_skatmind_rename.py `
  tests/test_packaging_and_distribution.py `
  -q -ra --durations=10 --junitxml="$env:TEMP\opencode\issue293-affected-01.xml"
```

Result: **570 passed, 1 skipped in 305.78s**. The sole skip is the existing
Windows-account symbolic-link capability check in
`test_unified_local_app_managed_items.py:506`. Strict rename inventory,
localization inventories and packaging assertions passed without weakened
counts or allowlists. Subsequent regression additions extend enhanced stale
language-return and actual version-selection coverage. The complete updated
module plus strict rename inventory passed **86 tests, no skips, in 70.54s**:

```powershell
python -m pytest tests/test_learning_prepared_navigation.py tests/test_skatmind_rename.py `
  -q -ra --durations=5 --junitxml="$env:TEMP\opencode\issue293-final-focused.xml"
```

The new navigation module contains 78 cases. Unaffected complete-module results
above remain applicable. Review also removed one redundant redirect-follow GET
from the existing source-navigation regression. Its final complete-module rerun
passed **17 tests, no skips, in 11.92s**:

```powershell
python -m pytest tests/test_learning_source_navigation.py -q -ra `
  --junitxml="$env:TEMP\opencode\issue293-source-navigation.xml"
```

The source-tree browser verifier uses existing dependency-free local DevTools
and disposable Learning fixture helpers:

```powershell
py -3.13 scripts/verify_learning_prepared_navigation.py --phase before `
  --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --output "$env:TEMP\opencode\issue293-before"
py -3.13 scripts/verify_learning_prepared_navigation.py --phase after `
  --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --output "$env:TEMP\opencode\issue293-after-05"
```

Use a fresh output directory for another run; `before` is run on the original
product code. Both completed runs have `completed: true` in `evidence.json`.
The intermediate `issue293-after-01` through `-04` directories are incomplete
development probes, not passing verification. They exposed the tall-region focus
problem and verifier assumptions about the legitimate receipt Dismiss button,
reload viewport restoration after the next-Tab probe, and enhancement's consumed
language metadata. The final implementation focuses the meaningful heading;
the verifier captures native landing before any target scroll/focus or next Tab.

Final browser: **Headless Microsoft Edge 155.0.4283.62**, **1365 x 900**:

| Locale | JavaScript | Outcome |
| --- | --- | --- |
| German | off | Passed |
| German | on | Passed |
| English | off | Passed |
| English | on | Passed |

Each case checks pointer View, native Tab/Enter View after manual close, real
self-page requests, successful POST/303/GET landing, Refresh from that native
landing, real language changes with open/closed disclosure, retained-error
priority after failed recreation, and stale View after a competing collection
change. Screenshots, heading/content geometry, focused element, next Tab target,
network request sequences, action counters and ten exact download hashes are in
each run's evidence. Representative screenshots:

* `issue293-before/en-native/preparation-landing.png`
* `issue293-after-05/de-native/preparation-landing.png`
* `issue293-after-05/en-js/preparation-landing.png`
* `issue293-after-05/de-js/language-closed.png`
* `issue293-after-05/en-native/view-with-retained-error.png`

Per case, fixture setup explicitly imports one Workspace and prepares once.
The passive interval retains all three artifact identities, generations/revisions,
recording/Corpus bytes and all ten download byte strings; every operation/write
counter is zero except **two profile writes for two actual language changes**.
Competing collection creation is recorded separately. Failed recreation performs
no preparation. These are synthetic source-tree checks, not installed UAT,
screen-reader certification or physical-device tests.

Final validation uses the maintainer-approved explicit Quick routine:

```powershell
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Quick writes stage logs and a JSON summary outside the repository; its final
exit status and exact evidence directory accompany the Build handoff. Local Full
is not part of this Build's approved routine.

## Handoff boundary

Product code changes only the private prepared-result navigation/presentation
and its source/language guards. Actual registry definitions still contain **73
POST routes, 125 forms, 2,034 keys per locale and ten prepared downloads**. There
are no new POST operations, forms, locale keys, schemas, dataset formats or
download kinds. New exact-commit hosted CI and
the installed targeted Finding B retest remain pending. Issue #293 remains open
for those gates. #292 is complete; #289, #290 and #291 remain closed. #208 remains
open, UAT-01 is not globally accepted, and UAT-02 through UAT-12 remain paused.
The four queued Match UI findings are outside this Build. Changes remain unstaged
and uncommitted for maintainer review and publication.
