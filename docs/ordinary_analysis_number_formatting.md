# Ordinary analysis number formatting (Issue #301)

## Implementation and preserved policies

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

## Changed files and handoff

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
