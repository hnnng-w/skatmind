# Ordinary analysis number formatting (Issues #301 and #302)

## Current policy

Issue #302 renders ordinary Match numeric `win_rate` cells as percentages:
`float(rate) * 100`, Python `.2f`, request-local decimal separator, then one `%`.
The accepted Issue #301 `expected_point_swing` policy remains Python `.2f`.
Only exact `int`/`float` values are converted; missing/`None` is localized unavailable,
booleans remain literal, and strings remain escaped literal text. Retained Reports
and canonical exports keep their original fractions and full numeric precision.
The metric remains the acting side winning the current simulated Trick. Existing
labels, explanations, Null objectives, recommendation and tie semantics are unchanged.

Issue #301 is complete within its accepted scope, including installed number
localization, two-decimal Match points, language return and native operation. The
following original implementation and point follow-up sections preserve their actual
observations, then-current policies and then-pending handoffs as **historical**.
Their raw-fraction observations are not evidence for #302. The #302 record at the end
documents the new percentage behavior and its separate pending acceptance gates.

## Original locale-only implementation (historical)

Ordinary analysis has two numeric presentation paths:

* `src/skatmind/app_web/result_presentation.py` projects guided and Session
  Results before rendering. Float details and ordinary Search means retain Python
  `.6g`; Immediate best-card point swings and the equal-best explanatory value
  retain `.2f`; percentages retain `float(value) * 100`, `.2f`, and `%`.
* `src/skatmind/app_web/match_report_rendering.py` renders ordinary Match Report
  `immediate_candidate_values`. `capture_web/state.py` retains typed original
  values. These cells retain the existing raw scalar representation, including
  all digits and the fraction unit for `win_rate`.

Both use the private `ordinary_result_numbers.ordinary_scalar()` boundary. It
formats only exact Python integers/floats, then localizes their decimal separator
within the established request-local `localized_render` context. Match passes its
explicit locale; shared projection inherits its caller's context. The helper reuses
only the existing decimal-separator catalog entry from rollout presentation, not
its Decimal rounding, fixed precision, signed-zero normalization, or endpoint policy.

| Typed value / field | English, before and after | German, before | German, after |
| --- | --- | --- | --- |
| R10 Immediate equal-best swing and explanation | `6.00` | `6.00` | `6,00` |
| Shared win fraction `0.125` | `12.50%` | `12.50%` | `12,50%` |
| Shared `.6g` mean `-1.23456789` | `-1.23457` | `-1.23457` | `-1,23457` |
| Shared `.6g` mean `1.23456789e-7` | `1.23457e-07` | `1.23457e-07` | `1,23457e-07` |
| Immediate `.2f` swing `-1.125` | `-1.12` | `-1.12` | `-1,12` |
| Match raw swing `-1.25` | `-1.25` | `-1.25` | `-1,25` |
| Match raw fraction `0.125` | `0.125` | `0.125` | `0,125` |
| Match raw fraction `0.875` | `0.875` | `0.875` | `0,875` |

Existing integer, zero, boolean and unavailable distinctions remain. For example,
shared `.6g` negative zero stays `-0`; Match raw negative zero becomes `-0,0` in
German while retaining `-0.0` in English. Ordinary rounded percentage endpoints
remain unchanged. Already formatted table strings are preserved literally in
either locale. Names such as `B 1.25`, IDs, filenames, versions, timestamps and
retained English technical prose are not parsed or rewritten.

The inspected callers are `guided_rendering.py`, `stateful_rendering.py`, ordinary
and rollout branches of `task_first_session_rendering.py`, `task_first_match_rendering.py`,
`result_rendering.py`, and `rollout_result_presentation.py`. The whole-game Match
rollout branch and `debrief_rendering.report_presentation()` continue to use their
existing localized rollout projection. Source/owner validation, selected Report
identity, language return, error-focus priority, native controls, canonical exports,
ranking, tied-best semantics, confidence, candidate order and execution are preserved.

## Regression-first reproduction

At clean branch `bug/301-analysis-number-formatting`, starting HEAD
`2ca831c1ffb27ca5c505d8c2f443bb03b2ca15bf`, the new German HTTP assertions ran
before Product edits. Both failed against actual delivered HTML:

1. Genuine recorded Session R10 review: the equal-best explanation contained
   `6.00` instead of `6,00`; CJ/SJ still had equal retained `6.0` scores.
2. Genuine Match analysis from the existing partial-game context fixture, eight
   samples per Card: candidate values included `12.0`, `10.625`, `9.5`, `1.0`,
   `0.875` rather than `12,0`, `10,625`, `9,5`, `1,0`, `0,875`.

```powershell
$scratch = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
py -3.13 -m pytest tests/test_analysis_explanations_web.py -k real_ordinary_numbers -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-before.json"
```

Result: **two expected failures, five deselected, 10.92s**. The final verification
below uses complete modules. The original R10 execution, recommendation, stable
ordering, played-card, rank, equality and raw-export assertions remain. Only the
locale-dependent expected strings in `assert_visible_equal_best()` and the Match
scalar-layout test changed. Literal preformatted table assertions remain intact.

New HTTP coverage also executes genuine Bounded and Information-set Search through
the delivered guided import/run forms, then verifies locale-specific candidate
cells and identical canonical Request/Result bytes. The separate precision and
defensive tests in `test_ordinary_result_numbers.py` use **controlled retained
scalars**, not genuine Search executions. Concurrent HTTP locale requests and
barrier-synchronized shared projection verify request-local isolation; repeated
`de -> en -> de` views preserve retained identities and exports.

## Environment, commands and derived inventory

Source-tree development environment on Windows 11 `10.0.26300`, PowerShell 5.1,
64-bit CPython **3.13.7**, pytest **9.0.3**. Interpreter:
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
`skatmind.__file__` resolves to this checkout's `src/skatmind/__init__.py`.
All data is disposable; no installed maintainer environment or real managed data
was accessed. No dependency, schema, CLI, persistence or public contract changed.

Inventory derivation starts with both producers, their shared projection/rendering
callers and the HTTP callers of the changed equal-best assertion. It extends to
guided/Session/Match results, selected and reopened Reports, download ownership,
native and enhanced language return, rejection/focus guards, adjacent rollout and
debrief presentation, package discovery, architecture and strict rename checks.
The following command is the complete **54-module parallel inventory**:

```powershell
py -3.13 -m pytest tests/test_ordinary_result_numbers.py tests/test_guided_frontend_result_presentation.py tests/test_equal_best_immediate.py tests/test_equal_best_immediate_consumers.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations.py tests/test_analysis_explanations_web.py tests/test_session_recorded_review_web.py tests/test_recorded_decision_context_web.py tests/test_guided_frontend_web.py tests/test_guided_frontend_json_transfer.py tests/test_task_first_stateful_rendering.py tests/test_task_first_match_and_learning_workflow.py tests/test_match_learning_report_discoverability.py tests/test_match_analysis_exports.py tests/test_analysis_download_details.py tests/test_rollout_result_presentation.py tests/test_frontend_language_switching.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py tests/test_language_view_continuity.py tests/test_language_switch_context.py tests/test_language_view_script.py tests/test_operation_feedback_language.py tests/test_task_first_language_preservation.py tests/test_guided_frontend_packaging.py tests/test_profile_driven_creation_packaging.py tests/test_packaging_and_distribution.py tests/test_skatmind_rename.py tests/test_cli_internal_architecture.py tests/test_completed_trick_input_grouping.py tests/test_hand_evidence_labels.py tests/test_match_evidence_navigation.py tests/test_match_game_navigation.py tests/test_operation_feedback.py tests/test_operation_feedback_web.py tests/test_recording_task_focus.py tests/test_review_return_labels.py tests/test_session_recorded_review.py tests/test_session_declaration_correction_web.py tests/test_unified_local_app_managed_items.py tests/test_unified_local_app_web.py tests/test_learning_overview_navigation.py tests/test_session_rollout_review.py tests/test_match_rollout_web.py tests/test_match_rollout_review.py tests/test_learning_debrief_web.py tests/test_match_debrief.py tests/test_recorded_review_navigation.py tests/test_guided_frontend_execution.py tests/test_guided_frontend_contracts.py tests/test_frontend_validation_preservation.py tests/test_match_analysis_report_source_export.py tests/test_local_match_capture_web_analysis.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest --validation-report="$scratch\issue301-final-parallel.json" --durations=10 --tb=short -rs
```

**1,387 passed / one skipped in 488.05s.** The sole skip is the existing
`test_unified_local_app_managed_items.py` symbolic-link test: this Windows account
cannot create symbolic links. After both workers and the browser process exited,
all four exclusive modules ran serially:

```powershell
py -3.13 -m pytest tests/test_early_rejection_observer.py tests/test_local_learning_corpus_web.py tests/test_unified_rejection_transport.py tests/test_match_analysis_action_placement.py -q -p scripts.validation_pytest --validation-report="$scratch\issue301-final-serial.json" --durations=10 --tb=short -rs
```

**95 passed in 65.36s**, no skips. Total: **58 complete modules, 1,482 distinct
passing tests, one skip**. All existing whole-game rollout number tests passed.

Earlier overlapping development runs, not additional distinct passes:

```powershell
py -3.13 -m pytest tests/test_ordinary_result_numbers.py tests/test_equal_best_immediate.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations_web.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-focused-01.json"
py -3.13 -m pytest tests/test_analysis_explanations_web.py tests/test_ordinary_result_numbers.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-focused-02.json"
```

These passed **132 tests in 31.69s** and **17 tests in 39.12s**, respectively.
Initial Ruff probes found import layout and overlong lines; these were corrected
without relaxing lint. There were no post-implementation pytest failures.

After this documentation update, rerun the complete documentation-sensitive modules
and final explicit Quick, with process-local interpreter selection:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py tests/test_profile_driven_creation_packaging.py tests/test_guided_frontend_packaging.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py tests/test_cli_internal_architecture.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-final-documentation.json"
$env:PATH = 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313;' + $env:PATH
$env:TEMP = $scratch
$env:TMP = $scratch
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Final repeat count/timing and the generated `skatmind-check-*` Quick log path are
reported in the completion handoff, avoiding a post-gate documentation edit. Quick
covers Ruff, packaged-schema parity and input examples. Local Full is not authorized
for this task; no Full, new hosted CI or installed acceptance is claimed.

## Bounded browser evidence

```powershell
py -3.13 scripts/verify_ordinary_result_numbers.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue301-browser-03"
```

Final result: **four cases passed in 48.374s**, actual headless Microsoft Edge
**156.0.4314.50**. Each Session/Match case runs with JavaScript disabled or enabled
and activates the actual language buttons in the sequence `de -> en -> de`.
Fresh isolated profiles use default 100% zoom; measured device pixel ratio and visual
viewport scale are `1`, viewport 1365 x 900. Resizing is not zoom evidence.

The verifier captures actual DOM numeric text, checks visibility, saves 12 PNGs,
activates native download anchors, and compares downloaded files byte-for-byte with
canonical retained exports. It reopens the older Match Report after a second genuine
analysis for another Game; selected Report identity and candidate order survive
every language return. The genuine fixtures display:

* Session: CJ, SJ in stable order, both equally best, played SJ still optimal;
  German `100,00% / 6,00 / 6`, English `100.00% / 6.00 / 6`.
* Match: C8, C7, C9 in stable order; German swings `12,0 / 10,625 / 9,5` and
  raw fractions `1,0 / 0,875 / 0,875`; English `12.0 / 10.625 / 9.5` and
  `1.0 / 0.875 / 0.875`.

Evidence is under `$scratch\issue301-browser-03`: `evidence.json`, per-case PNGs,
and `downloads-{index}-{locale}` with actual Request, Result and Report-for-Learning
files. The JSON retains byte lengths, SHA-256 values, Report IDs, request counts,
environment, displayed values, visibility and phase counters. Representative German
and English screenshots were inspected for both paths, including native-disabled
and enhanced-enabled views.

Operation accounting per case:

| Phase | Session (each JavaScript mode) | Match (each JavaScript mode) |
| --- | --- | --- |
| Disposable fixture recording | 17 Session saves, one creation Profile save | 13 Match saves, one creation Profile save |
| Deliberate initial analysis | one genuine Session analysis | two genuine Match analyses |
| Three explicit language controls | three Profile saves | three Profile saves |
| Passive views, disclosures and downloads | zero operations/writes | zero operations/writes |

Across all four cases: 34 Session saves and 26 Match saves during fixture recording;
four creation Profile saves; two Session and four Match analyses; **12 separate
explicit language Profile saves**. Passive activity adds zero analysis, preparation,
import, recording, Catalog or Snapshot writes. All non-Profile managed bytes remain
identical, and no Learning collection is opened or prepared. All 24 native downloads
match their canonical bytes; HTTP byte checks independently verify the same routes.

Intermediate browser probes:

* `-01` stopped during verifier import because the repository root was missing
  from the script's import path (`ModuleNotFoundError: scripts`). No browser case or
  Product failure occurred, and no evidence directory was created.
* `-02` passed four cases in **49.050s**. Final `-03` repeated them after the import
  formatting and counter-label cleanup; it is the final evidence above.

## Original changed files and handoff (historical)

Product changes are limited to these three private frontend files:

* `src/skatmind/app_web/ordinary_result_numbers.py` (new)
* `src/skatmind/app_web/result_presentation.py`
* `src/skatmind/app_web/match_report_rendering.py`

Verification changes:

* `tests/test_ordinary_result_numbers.py` (new)
* `tests/test_analysis_explanations_web.py`
* `tests/test_candidate_comparison_layout.py`
* `tests/test_equal_best_immediate.py`
* `tests/test_guided_frontend_packaging.py` (adds private helper discovery)
* `scripts/verify_ordinary_result_numbers.py` (new)

Documentation changes:

* `docs/ordinary_analysis_number_formatting.md` (this new evidence record)
* `docs/unified_local_frontend_guided_analysis_and_results.md`
* `docs/match_report_learning_discoverability.md`

All changes remain unstaged and uncommitted. Expected/actual branch and starting/current
HEAD remain the values above. No Git/GitHub publication actions were performed.

**Locally validated; new exact-commit hosted CI and installed targeted acceptance
pending.** Keep #301 and #208 open. #292–#300 remain complete, including #300's
installed acceptance. UAT-01 is not globally accepted; UAT-02–12 remain paused.
Broader design and Learning product-policy questions remain separate. Release
preparation is not authorized.

## Installed-feedback follow-up: two-decimal Match point display (Issue #301, historical)

### Accepted installed baseline and bounded correction

Expected/actual branch: `bug/301-analysis-number-formatting`. Expected/actual
starting HEAD: `f665d36761f439b96ae7ec351c3b8ce6059f03f9`; the initial worktree was
clean. The maintainer reported these installed targeted results on that commit:

1. Ordinary Match localization and language switching worked, with excessive
   floating-point digits in the point-comparison column as the remaining finding.
2. Shared guided formatting and language switching worked. The supplied screenshot
   showed `100,00%` and point values `11,00 / 10,00 / 0,00`.
3. Native language return worked with JavaScript disabled.
4. Downloads worked and preserved canonical JSON numeric formatting.

These are maintainer acceptances for the tested build. This source-tree follow-up
does not replace them or claim new installed acceptance.

The Product patch changes only `match_report_rendering.py`: its ordinary candidate
cell calls `ordinary_scalar(value, ".2f", locale=locale)` for `expected_point_swing`
and retains the default format for `win_rate`. `ordinary_result_numbers.py` and
`result_presentation.py` are unchanged. Exact integers/floats use Python's existing
two-decimal rounding, including signed zero. `None` remains unavailable; booleans
and strings retain their prior literal rendering. No rounded string enters scoring,
ranking, recommendation, tie classification, persistence or serialization.

| Card | Controlled original point value | German after | English after |
| --- | --- | --- | --- |
| CQ | `2.0599999999999996` | `2,06` | `2.06` |
| C10 | `1.2400000000000002` | `1,24` | `1.24` |
| C8 | `1.2200000000000002` | `1,22` | `1.22` |
| C7 | `1.1600000000000001` | `1,16` | `1.16` |

Numeric point zero now displays `0,00` / `0.00`. Point `-0.0` and `-0.004` display
`-0,00` / `-0.00`; `2.675` follows Python float `.2f` as `2,67` / `2.67`.
Raw rates remain `0,125` / `0.125`, `1,0` / `1.0`, integer zero `0`, float zero
`0,0` / `0.0`, and scientific-notation precision as before. There is no percentage
conversion, Decimal policy or zero normalization.

### Regression and complete-module verification

The new HTTP regression uses a genuine disposable Match Report as the page owner,
then explicitly substitutes only the four screenshot scalars in the display
projection. It is a **controlled display fixture**, not an assertion that the engine
produced those scores. Both locale cases failed before the Product edit, with
`2,0599999999999996` versus `2,06` and `2.0599999999999996` versus `2.06`.
All four expected point cells are checked together. Report objects, recording bytes
and Result/Report-for-Learning downloads remain the genuine baseline and unchanged.

The existing genuine-analysis HTTP case now checks points with `.2f` and rates with
raw `str`, preserving its concurrent locale requests, `de -> en -> de` return,
selected Report identity, execution/save counters and exact downloads. The shared
genuine Bounded/Information-set HTTP tests are preserved. Arithmetic-only fixtures
also cover positive/negative/zero and integer points, both booleans, unavailable and
literal strings, Python rounding, raw rate precision, and repeated/concurrent locales.
The rounding-collision fixture uses distinct retained scores `1.2421875` and
`1.240234375`: both display `1.24`, but CJ alone remains best, SJ retains rank 2,
one better Card and a positive unrounded difference. Literal preformatted table
assertions and shared `.6g`, percentage and equal-best tests remain intact.

Environment: Windows 11 `10.0.26300`, PowerShell 5.1, source-tree development package,
64-bit CPython **3.13.7**, pytest **9.0.3**, using the interpreter path above. All
fixtures and browser profiles are disposable, outside the checkout. No installed
UAT environment or real managed data was accessed.

```powershell
$scratch = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
py -3.13 -m pytest tests/test_analysis_explanations_web.py -k controlled_match_screenshot -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-points-before.json"
py -3.13 -m pytest tests/test_ordinary_result_numbers.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations_web.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-points-focused.json"
```

Before: **two expected failures, nine deselected in 7.23s**. After: **66 passed in
36.17s** across the three complete modules. One intermediate Ruff probe found an
overlong new test signature, which was wrapped; subsequent lint passed. There were
no failed post-correction pytest or browser runs.

The inventory derives from the sole Product boundary and its actual callers:

* `task_first_match_rendering._reports()` supplies the ordinary Report renderer to
  recording/review/Report views. Direct renderer tests, Match navigation/context,
  selected older Report ownership, and both canonical download families are included.
* Native/enhanced language return and error feedback remain covered by the affected
  language modules and the exclusive Match analysis/action-placement module.
* Shared guided/Session presentation and equal-best behavior, plus the neighboring
  Match rollout branch, are explicit unchanged sentinels.
* Private module discovery, package metadata/resources, translation inventory and
  strict rename checks cover the changed source/tests/documentation.

This is **27 parallel modules plus one exclusive module**, rather than a repeat of
the original 58-module inventory. No rejection transport, standalone Corpus, engine
or helper implementation changed, so their former broader inventories are not
repeated independently.

```powershell
py -3.13 -m pytest tests/test_ordinary_result_numbers.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations_web.py tests/test_analysis_download_details.py tests/test_recorded_decision_context_web.py tests/test_review_return_labels.py tests/test_match_evidence_navigation.py tests/test_match_game_navigation.py tests/test_task_first_match_and_learning_workflow.py tests/test_task_first_stateful_rendering.py tests/test_match_learning_report_discoverability.py tests/test_match_analysis_exports.py tests/test_match_analysis_report_source_export.py tests/test_frontend_language_switching.py tests/test_language_view_continuity.py tests/test_language_switch_context.py tests/test_task_first_language_preservation.py tests/test_operation_feedback_language.py tests/test_rollout_result_presentation.py tests/test_match_rollout_web.py tests/test_guided_frontend_result_presentation.py tests/test_equal_best_immediate.py tests/test_complete_frontend_localization.py tests/test_frontend_localization_foundation.py tests/test_guided_frontend_packaging.py tests/test_packaging_and_distribution.py tests/test_skatmind_rename.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest --validation-report="$scratch\issue301-points-parallel.json" --durations=10 --tb=short -rs
py -3.13 -m pytest tests/test_match_analysis_action_placement.py -q -p scripts.validation_pytest --validation-report="$scratch\issue301-points-serial.json" --durations=10 --tb=short -rs
```

Parallel: **696 passed in 135.67s**. After both workers and browser verification
exited, exclusive serial: **25 passed in 17.51s**. Total: **721 distinct passing
tests across 28 complete modules, no skips**. The earlier 66 focused passes overlap.

After this documentation update, repeat these complete documentation-sensitive
modules and final explicit Quick with process-local interpreter selection:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue301-points-documentation.json"
$env:PATH = 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313;' + $env:PATH
$env:TEMP = $scratch
$env:TMP = $scratch
.\scripts\check.ps1 -Mode Quick
git diff --check
```

The completion handoff records the final repeat result/timing and exact generated
Quick log path. Local Full is not authorized and is not claimed.

### New browser evidence and operation accounting

```powershell
py -3.13 scripts/verify_ordinary_result_numbers.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue301-points-browser-01"
```

**Six cases passed in 68.784s**, actual headless Microsoft Edge **156.0.4314.50**,
fresh profiles at default 100% zoom, 1365 x 900 viewport, device pixel ratio and
visual viewport scale `1`. These are new source-tree results, not installed acceptance.
The first four cases are genuine Session/Match executions, each with JavaScript
disabled/enabled. Two additional Match cases use the explicitly controlled display
projection described above. Every case activates actual `de -> en -> de` language
buttons, returns to the selected page, captures visible numeric cells and screenshots,
and activates native download links. The older selected Match Report is retained
after a newer Report for another Game exists.

Observed new-policy values:

* Genuine Match: C8/C7/C9 point cells `12,00 / 10,62 / 9,50` in German and
  `12.00 / 10.62 / 9.50` in English. Rates remain `1,0 / 0,875 / 0,875` and
  `1.0 / 0.875 / 0.875`. The unrounded `10.625` follows Python `.2f` to `10.62`.
* Controlled precision projection: CQ/C10/C8/C7 display `2,06 / 1,24 / 1,22 / 1,16`
  and `2.06 / 1.24 / 1.22 / 1.16`; raw rates remain `0,94 / 0,96 / 1,0 / 0,58`
  and `0.94 / 0.96 / 1.0 / 0.58`. These four display scalars do not replace the
  genuine Report, its recommendation or its canonical exports.
* Genuine shared Session sentinel: unchanged CJ/SJ equality, `100,00% / 6,00 / 6`
  and `100.00% / 6.00 / 6`, played SJ optimal and stable candidate order.

Evidence under `$scratch\issue301-points-browser-01` contains `evidence.json`,
**18 readable screenshots**, displayed values and source classification, retained
Report IDs, operation/request counters, and **36 actual native downloads** with
byte lengths and SHA-256 values. All downloads matched canonical bytes, with separate
HTTP byte checks. Representative German/native and English/enhanced precision
screenshots, genuine Match and shared Session screenshots were inspected.

| Phase | Two Session cases | Four Match cases (two controlled-display) |
| --- | --- | --- |
| Disposable recording | 34 Session saves; two creation Profile saves | 52 Match saves; four creation Profile saves |
| Deliberate baseline analysis | two genuine Session analyses | eight genuine Match analyses |
| Explicit language changes | six Profile saves | twelve Profile saves |
| Passive viewing/disclosures/downloads | zero operations/writes | zero operations/writes |

Thus **18 explicit language-profile saves** are separate from six creation-profile
saves. Passive phases added no analysis, preparation, import, recording, Catalog or
Snapshot writes. All non-Profile managed bytes and genuine retained Reports remain
identical. Controlled projection adds no execution or write. No Learning workflow
or complete prior acceptance sequence was repeated.

### Follow-up changed files and handoff

Exactly eight files change:

* `src/skatmind/app_web/match_report_rendering.py`
* `tests/test_ordinary_result_numbers.py`
* `tests/test_candidate_comparison_layout.py`
* `tests/test_analysis_explanations_web.py`
* `scripts/verify_ordinary_result_numbers.py`
* `docs/ordinary_analysis_number_formatting.md`
* `docs/match_report_learning_discoverability.md`
* `docs/unified_local_frontend_guided_analysis_and_results.md`

All changes remain unstaged and uncommitted; no publication action is performed.
**Locally validated; new exact-commit hosted CI and installed targeted follow-up
pending.** Keep #301 and #208 open. Preserve existing maintainer acceptances for
their tested build; the subsequent installed follow-up should focus on corrected
Match point display and language/native return. #292–#300 remain complete. UAT-01
is not globally accepted; UAT-02–12 remain paused. Broader design and Learning
product-policy questions stay separate. Release preparation is not authorized.

## Issue #302: ordinary Match win percentages

### Checkout, root cause and implementation

Expected and actual branch: `bug/302-match-win-percentages`. Expected and actual
starting/current HEAD: `60117e6d60e05923bfe6bb402810763f8cb922e4`; the starting
worktree was clean. Verification used `git status --short`,
`git branch --show-current` and `git rev-parse HEAD`. All edits remain unstaged
and uncommitted; no Git/GitHub publication action was performed.

The ordinary Match renderer read `details["immediate_candidate_values"]` through
the default raw scalar format for rates, unlike the established numeric percentage
arithmetic in `result_presentation._percentage`. A private `_candidate_value` cell
helper now handles missing values, converts exact numeric rates using that arithmetic,
and HTML-escapes the result. It retains the existing `.2f` point branch and literal
fallback. `ordinary_result_numbers.py`, its defaults/callers and
`result_presentation.py` are unchanged. No shared Search method semantics, rollout
formatting, schemas, catalog messages, routes, forms or Product operations change.

| Retained rate | German | English |
| --- | --- | --- |
| `0.94` | `94,00%` | `94.00%` |
| `0.96` | `96,00%` | `96.00%` |
| `0.875` | `87,50%` | `87.50%` |
| `0.125` | `12,50%` | `12.50%` |
| `1`, `1.0` | `100,00%` | `100.00%` |
| `0`, `0.0` | `0,00%` | `0.00%` |
| `-0.0`, `-0.00001` | `-0,00%` | `-0.00%` |
| `0.9999999` | `100,00%` | `100.00%` |
| `0.0000001` | `0,00%` | `0.00%` |
| `0.01125` | `1,12%` | `1.12%` |

These are ordinary Python float rounding results, including signed zero and rounded
endpoints. No Decimal, clamping, endpoint special case or rollout policy is introduced.
Text `"0.94"` and `"94.00%"` remains exactly that text in both locales. Boolean
`True`/`False` remains literal; missing and `None` remain localized unavailable.

### Regression-first evidence and environment

Before Product edits, both delivered-HTTP controlled screenshot cases failed:
German `0,94` versus `94,00%`, English `0.94` versus `94.00%`. Their genuine retained
Report owns the page/downloads; only its disposable display projection receives the
explicit screenshot scalars. These are not engine-produced scores. The existing
point expectations `2.06 / 1.24 / 1.22 / 1.16` and decimal-comma equivalents remain.

Environment: Windows 11 `10.0.26300`, PowerShell **5.1.26100.9711**, 64-bit CPython
**3.13.7**, pytest **9.0.3**, pytest-xdist **3.8.0**, Ruff **0.15.17**. Interpreter:
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
`skatmind.__file__` resolves to this checkout's `src/skatmind/__init__.py`. Only
disposable source-tree data and isolated browser profiles were used; no installed
UAT environment or real managed data was accessed.

```powershell
$scratch = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
Test-Path -LiteralPath $scratch
py -3.13 -m pytest tests/test_analysis_explanations_web.py -k controlled_match_screenshot -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue302-before.json"
py -3.13 -m pytest tests/test_ordinary_result_numbers.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations_web.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue302-focused.json"
py -3.13 -m pytest tests/test_ordinary_result_numbers.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations_web.py -q --tb=short -p scripts.validation_pytest --validation-report="$scratch\issue302-focused-02.json"
py -3.13 -m ruff check src/skatmind/app_web/match_report_rendering.py tests/test_ordinary_result_numbers.py tests/test_candidate_comparison_layout.py tests/test_analysis_explanations_web.py scripts/verify_ordinary_result_numbers.py
```

* Before: **two expected failures, nine deselected, 9.36s**.
* First complete three-module run: **88 passed / two failed, 64.81s**. The new Null
  collision fixtures omitted the required `game_value`; supplying `23` corrected
  their setup without changing Product semantics. An initial scoped Ruff probe
  (the command above without the browser script) also found one overlong test line;
  wrapping it corrected lint.
* Corrected complete three-module run: **90 passed, 86.55s**; scoped Ruff passed.
  These are overlapping executions, not additional distinct tests.

New literal expectations cover all acceptance examples, integer/float endpoints,
signed zero, near-endpoint/Python rounding, missing cells, `None`, both booleans,
numeric-looking/preformatted/empty/HTML-sensitive strings and repeated concurrent
locales. Renamed Match tests deliberately replace their former raw-fraction policy;
generic already-formatted candidate-table tests remain lossless literal tests.
Independent point, label, accessibility, empty-state and immutability checks remain.

Controlled distinct rates `0.12501` and `0.12504` both display `12.50%`, but retain
their values, unique recommendation and rank/quality behavior for Grand and both
Null roles. The distinct-point `1.2421875`/`1.240234375` collision regression remains.
Genuine Match HTTP coverage separately executes two Games, reopens the older Report,
checks explicit C8/C7/C9 values/order and C8 recommendation, concurrent request locales,
native `de -> en -> de` return, exact canonical Result and Report-for-Learning bytes,
unchanged recording bytes/Report identity, and three language-profile saves only.
Genuine shared Search HTTP, shared percentage/equality and separate rollout tests
remain sentinels.

### Complete affected-module inventory

The starting inventory is the **27 parallel modules plus one exclusive module**
from #301's point follow-up above. The sole Product caller remains
`task_first_match_rendering._reports()`; the new helper is private to that renderer.
There is no new shared-helper caller or dependency requiring expansion. The inventory
retains Match source/generation/navigation checks, older-Report ownership, canonical
downloads, native/enhanced language behavior, shared/rollout sentinels and strict
rename, packaging and localization assertions without relaxing inventories.

Exact full commands (line-wrapped only for readability):

```powershell
py -3.13 -m pytest `
  tests/test_ordinary_result_numbers.py `
  tests/test_candidate_comparison_layout.py `
  tests/test_analysis_explanations_web.py `
  tests/test_analysis_download_details.py `
  tests/test_recorded_decision_context_web.py `
  tests/test_review_return_labels.py `
  tests/test_match_evidence_navigation.py `
  tests/test_match_game_navigation.py `
  tests/test_task_first_match_and_learning_workflow.py `
  tests/test_task_first_stateful_rendering.py `
  tests/test_match_learning_report_discoverability.py `
  tests/test_match_analysis_exports.py `
  tests/test_match_analysis_report_source_export.py `
  tests/test_frontend_language_switching.py `
  tests/test_language_view_continuity.py `
  tests/test_language_switch_context.py `
  tests/test_task_first_language_preservation.py `
  tests/test_operation_feedback_language.py `
  tests/test_rollout_result_presentation.py `
  tests/test_match_rollout_web.py `
  tests/test_guided_frontend_result_presentation.py `
  tests/test_equal_best_immediate.py `
  tests/test_complete_frontend_localization.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_guided_frontend_packaging.py `
  tests/test_packaging_and_distribution.py `
  tests/test_skatmind_rename.py `
  -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest `
  --validation-report="$scratch\issue302-parallel.json" --durations=10 --tb=short -rs
py -3.13 -m pytest tests/test_match_analysis_action_placement.py -q -p scripts.validation_pytest --validation-report="$scratch\issue302-serial.json" --durations=10 --tb=short -rs
```

Parallel: **720 passed in 197.54s**. After both workers and browser verification
exited, exclusive serial: **25 passed in 29.79s**. Total: **745 distinct passing
tests in 28 complete modules, zero failures/skips**. The development passes above
and documentation-sensitive repeats below overlap this inventory.

### Bounded browser verification

```powershell
py -3.13 scripts/verify_ordinary_result_numbers.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue302-browser-01"
py -3.13 scripts/verify_ordinary_result_numbers.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue302-browser-02"
```

Final `-02`: **six cases passed in 87.723s**, actual headless Microsoft Edge
**156.0.4314.50**. Initial `-01` passed in **97.257s**; its desktop inline-span
`clientWidth` was zero, so final instrumentation uses nonzero bounding widths and
parent-cell overflow measurements. This was a verifier measurement refinement,
not a Product/browser failure. Both runs use the same six bounded fixtures.

Two genuine Session cases, two genuine Match cases and two explicitly labelled
**controlled display projection** Match cases each cover JavaScript disabled/enabled,
actual language buttons `de -> en -> de`, and both 1365 x 900 desktop and 390 x 900
narrow layouts. Fresh profiles retain default 100% zoom, device pixel ratio and
visual viewport scale `1`; resizing is not zoom acceptance. Every candidate has
visible text/nonzero width, and cell/document overflow checks pass. Representative
German/English desktop/narrow screenshots were inspected for readable tables.

* Genuine Match C8/C7/C9: points `12,00 / 10,62 / 9,50` and `12.00 / 10.62 / 9.50`;
  rates `100,00% / 87,50% / 87,50%` and `100.00% / 87.50% / 87.50%`.
* Controlled CQ/C10/C8/C7: points `2,06 / 1,24 / 1,22 / 1,16` and
  `2.06 / 1.24 / 1.22 / 1.16`; rates `94,00% / 96,00% / 100,00% / 58,00%` and
  `94.00% / 96.00% / 100.00% / 58.00%`. These display scalars do not replace the
  genuine retained Report, C8 recommendation or exports.
* Genuine shared Session: unchanged CJ/SJ equal-best order and played-SJ assessment,
  with `100,00% / 6,00 / 6` and `100.00% / 6.00 / 6`.

Evidence under `$scratch\issue302-browser-02` includes `evidence.json`, **36 PNGs**,
display values/layout measurements, older/newer Report IDs, phase/request counters,
and **36 actual native downloads** with byte lengths and SHA-256 values. Every emitted
available anchor downloads bytes identical to its canonical retained artifact; separate
HTTP GET checks verify those routes too. Match provides Result and Report-for-Learning;
Session provides Request and Result. The selected older Report, full Report-store order,
candidate order and recommendation survive every language return.

| Phase | Two Session cases | Four Match cases (two controlled-display) |
| --- | --- | --- |
| Disposable fixture recording | 34 Session saves; two creation Profile saves | 52 Match saves; four creation Profile saves |
| Deliberate baseline analysis | two genuine Session analyses | eight genuine Match analyses |
| Explicit language changes | six Profile saves | twelve Profile saves |
| Passive views, layout checks, disclosures and downloads | zero operations/writes | zero operations/writes |

The **18 language-profile saves** are separate from six creation-profile saves.
Passive activity adds no analysis, preparation, import, recording, Catalog or Snapshot
writes; all non-Profile managed bytes and genuine retained Reports remain identical.
Controlled display projection adds no execution/write. No Learning workflow is opened
or prepared. This is developer verification, not installed maintainer UAT or a repeat
of the prior full acceptance sequence.

### Changed files and final local gate

Exactly eight files change:

* Product: `src/skatmind/app_web/match_report_rendering.py`.
* Tests: `tests/test_ordinary_result_numbers.py`,
  `tests/test_candidate_comparison_layout.py`, `tests/test_analysis_explanations_web.py`.
* Browser verifier: `scripts/verify_ordinary_result_numbers.py`.
* Documentation: this file, `docs/match_report_learning_discoverability.md`, and
  `docs/unified_local_frontend_guided_analysis_and_results.md`.

After documentation, repeat complete documentation-sensitive modules, review the
complete tracked/new-file diff and empty index, then run the explicit final Quick:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p scripts.validation_pytest --validation-report="$scratch\issue302-documentation.json" --durations=10 --tb=short -rs
git diff
git status --short
git diff --cached --stat
git diff --check
$env:PATH = 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313;' + $env:PATH
$env:TEMP = $scratch
$env:TMP = $scratch
.\scripts\check.ps1 -Mode Quick
```

Final repeat results/timings and the generated `$scratch\skatmind-check-*` Quick
log directory are recorded in the completion handoff without a post-gate edit.
Quick covers Ruff, packaged-schema parity and input examples only. No local Full,
full regression/generated-output/distribution certification or installed acceptance
is claimed.

**Locally validated; exact-commit hosted CI and installed targeted acceptance
pending.** Keep #302 open for exact-commit branch/main `check` and
`v1-supported-platform-matrix`, followed by installed targeted acceptance of
percentages, language return and JavaScript-disabled behavior. #292–#301 remain
complete within their accepted scopes. Keep #208 open: UAT-01 is not globally
accepted and UAT-02–12 remain paused. Broader design and Learning product-policy
questions remain separate. Full maintainer UAT and current architecture/code analysis
with treatment of material findings remain required before v1.0.0. Release preparation
is not authorized.
