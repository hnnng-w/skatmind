# Match perspective, evidence workflow and derived Hand readiness — Issue #297

## Implementation and authority

Expected and actual clean starting branch: `bug/297-match-evidence-workflow`.
Starting HEAD: `c5ab67bf02bfde9bbae4565d19e17b5b0b2f8f19`. This build leaves all
changes unstaged and uncommitted. The starting #296 branch/main runs
`39944920636` / `39960298198` and installed functional acceptance belong to that
baseline, not this working tree.

The implementation covers:

* One person-bound reviewed recording-perspective result beside Create, native
  result focus and next-Tab-to-Create, plus the accepted Match identity near the
  current Game heading. Selection, expiry and Create authority remain in the
  existing setup contract.
* Full-width current-Game source editors before Play and the 36-position overview,
  one native disclosure per ordinary source, accepted-state initial opening,
  concise source-specific help and explanation of the existing candidate domain.
* Scoped normal two-card zero Save to unknown, exact pair replacement, truthful
  no-op/removal receipts, unchanged exact-ten initial-hand and independent exact
  transport semantics, and preserved one-owner declaration drafts.
* Literal retained discard observations with declaration-aware Hand complete-deal
  capability and one shared canonical Historical projection. Normal explicit-empty
  entry and the old historical remedy are removed. Legacy Hand/`[]` has a separate,
  source-bound correction withdrawal before an explicitly saved declaration change.

Normative details are in [Card entry](compact_card_entry.md),
[creation](profile_driven_stateful_creation.md),
[observed evidence](observed_game_capture_contracts.md),
[materialization](match_review_and_materialization.md), and
[analysis](match_analysis_and_exports.md). No dependency, Package version, route,
API/CLI shape, Schema, persisted observation shape or observed-record normalizer
is added. Derived inventories are **73 POST routes / 125 forms / 2,072 catalog
keys per locale**, versus 73 / 125 / 2,061 at the start.

## Before-fix and intermediate evidence

Nine focused regression cases establish the changed boundaries: misplaced review
landing, source placement/opening, missing contextual explanation, both two-card
zero Saves, normal explicit-empty entry in undeclared/Hand states, Hand/`null`
capability and shared Historical projection. The first setup test used an incorrect
header-dictionary capitalization; correcting that test reproduced the actual
`/matches/new` return instead of `#match-setup-review`. The baseline had a reviewed
paragraph, and its 32-card candidate selection was correct. Neither is reported as
missing HTML or a candidate-rule defect.

The complete baseline browser probe loads production modules/resources from a
read-only archive of the exact starting commit, with disposable current test
transport helpers. It records the existing review paragraph offscreen on native
initial delivery, rejected normal zero Save, and unavailable complete Hand/`null`
historical capability. It makes no installed-UAT claim.

Iterative development runs exposed catalog ordering/interpolation errors and
test-fixture assumptions, corrected before the complete inventory. The complete
81-module run initially had **1,930 passes and 15 failures in 684.47s**. Those
15 assertions encoded superseded Hand readiness, outer-disclosure/primary-action
placement, generic candidate text and the old setup redirect. All five entire
affected modules then passed **183 tests in 29.24s**. No retry, skip, xfail or
relaxed inventory substitutes for those semantic corrections.

Browser probe corrections are also retained honestly: one probe expected the
numeric `10` in a localized Card name; the draft sentinel initially opened the
discard editor while trying to operate the now-separate original-Skat editor;
an early layout helper reused a disclosure ID and measured fewer palettes than
intended. These are incomplete verification attempts. The final verifier preserves
existing IDs, requires all four visible palettes in every layout sample, and
captures initial landings before any verifier scrolling, focusing or opening.

## Complete local module inventory

The 69 prescribed parallel modules are extended by two new modules and ten complete
shared-caller modules for Session/profile creation, Session feedback/corrections and
prepared Learning navigation. The original exclusive Match module and the adjacent
unified rejection-transport module run separately after parallel workers exit.
Final coverage is **2,007 distinct passing tests in 83 complete modules, zero skips**.
Repeated executions and before-fix failures are not counted as extra distinct tests.

Evidence uses CPython **3.13.7**, pytest **9.0.3**, pytest-xdist **3.8.0**, Windows
**11 Pro 10.0.26300**, PowerShell **5.1.26100.9711**, and Microsoft Edge
**156.0.4314.42** (headless DevTools protocol 1.3). The Python executable is
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
The installed UAT environment is not used.

`$scratch` below is the existing external directory
`C:\Users\HENNIN~1\AppData\Local\Temp\opencode`. JUnit files retain exact test IDs
and phase timings. The complete parallel command was:

```powershell
py -3.13 -m pytest `
  tests/test_player_seat_setup.py tests/test_settings_seat_setup_web.py `
  tests/test_profile_driven_match_creation.py tests/test_profile_driven_creation_web.py `
  tests/test_profile_driven_form_contracts.py tests/test_profile_driven_creation_packaging.py `
  tests/test_match_creation_details.py tests/test_match_person_review_actions.py `
  tests/test_match_setup_and_card_layout.py tests/test_direct_match_evidence.py `
  tests/test_match_evidence_navigation.py tests/test_match_evidence_presentation.py `
  tests/test_compact_card_entry_web.py tests/test_compact_initial_hand_web.py `
  tests/test_compact_play_grid_web.py tests/test_match_declaration_drafts.py `
  tests/test_compact_declaration_form.py tests/test_compact_declaration_web.py `
  tests/test_match_game_navigation.py tests/test_match_game_navigation_web.py `
  tests/test_task_first_stateful_projections.py tests/test_task_first_stateful_rendering.py `
  tests/test_task_first_match_and_learning_workflow.py tests/test_match_card_correction_ui.py `
  tests/test_match_recording_recovery.py tests/test_match_recording_recovery_web.py `
  tests/test_match_recording_diagnostics.py tests/test_recorded_trick_progress_web.py `
  tests/test_unplayed_card_summary.py tests/test_unplayed_card_summary_web.py `
  tests/test_null_recording_end.py tests/test_null_recording_end_web.py `
  tests/test_observed_game_contracts.py tests/test_observed_game_evidence.py `
  tests/test_observed_game_trace.py tests/test_match_capture_application_contracts.py `
  tests/test_match_capture_game_updates.py tests/test_match_capture_annotations_and_wrappers.py `
  tests/test_match_workspace_persistence.py tests/test_match_workspace_persistence_codec.py `
  tests/test_match_decision_review_preparation.py tests/test_match_historical_materialization.py `
  tests/test_match_workspace_materialization.py tests/test_match_historical_analysis.py `
  tests/test_match_analysis_contracts.py tests/test_match_analysis_exports.py `
  tests/test_local_match_capture_web.py tests/test_local_match_capture_web_analysis.py `
  tests/test_operation_feedback.py tests/test_operation_feedback_web.py `
  tests/test_operation_feedback_language.py tests/test_operation_feedback_script.py `
  tests/test_frontend_validation_preservation.py tests/test_task_first_language_preservation.py `
  tests/test_frontend_language_switching.py tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py tests/test_language_view_script.py `
  tests/test_unified_workflow_visual_contract.py tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py tests/test_skatmind_rename.py `
  tests/test_packaging_and_distribution.py tests/test_match_workspace_contracts.py `
  tests/test_match_decision_analysis.py tests/test_learning_corpus_match_snapshot.py `
  tests/test_learning_dataset_v2.py tests/test_hand_evidence_labels.py `
  tests/test_recording_task_focus.py tests/test_match_evidence_workflow.py `
  tests/test_match_derived_hand_readiness.py tests/test_profile_driven_session_creation.py `
  tests/test_profile_driven_learning_creation.py tests/test_own_player_assignment_web.py `
  tests/test_profile_driven_settings_web.py tests/test_session_card_feedback.py `
  tests/test_session_card_feedback_web.py tests/test_session_declaration_correction.py `
  tests/test_session_declaration_correction_web.py tests/test_learning_prepared_navigation.py `
  tests/test_learning_debrief_web.py `
  -q --tb=short -n 2 --dist=loadfile --max-worker-restart=0 `
  --junitxml="$scratch\issue-297-complete-parallel.xml"
```

Exact complete-module follow-ups, including the five corrected modules and a final
layout-only caller retest after removing the source form-width cap:

```powershell
py -3.13 -m pytest tests/test_unplayed_card_summary.py tests/test_match_creation_details.py tests/test_match_game_navigation.py tests/test_unified_workflow_visual_contract.py tests/test_task_first_match_and_learning_workflow.py -q --tb=short -n 2 --dist=loadfile --max-worker-restart=0 --junitxml="$scratch\issue-297-complete-caller-retest.xml"
py -3.13 -m pytest tests/test_match_analysis_action_placement.py -q --tb=short -n 0 --junitxml="$scratch\issue-297-exclusive-match.xml"
py -3.13 -m pytest tests/test_unified_rejection_transport.py -q --tb=short -n 0 --junitxml="$scratch\issue-297-exclusive-rejection.xml"
py -3.13 -m pytest tests/test_match_setup_and_card_layout.py tests/test_unified_workflow_visual_contract.py tests/test_packaging_and_distribution.py tests/test_compact_card_entry_web.py tests/test_match_evidence_workflow.py -q --tb=short -n 2 --dist=loadfile --max-worker-restart=0 --junitxml="$scratch\issue-297-final-layout-callers.xml"
py -3.13 -m pytest tests/test_skatmind_rename.py -q --tb=short --junitxml="$scratch\issue-297-documentation-retest.xml"
py -3.13 -m pytest tests/test_match_game_navigation.py tests/test_unplayed_card_summary.py tests/test_skatmind_rename.py -q --tb=short -n 2 --dist=loadfile --max-worker-restart=0 --junitxml="$scratch\issue-297-final-format-retest.xml"
```

The exclusive runs passed **25 in 23.52s** and **37 in 18.29s**; the final layout
caller run passed **108 in 76.26s**. Caller/documentation retests overlap earlier
modules; the two exclusive modules add 62 distinct tests. New tests cover real source-bound zero Save, malformed/stale/
foreign/failed persistence, accepted versus pending facts, every opening branch,
language/error priority, legacy withdrawal/draft separation, canonical Historical
requests, complete-list/Training consumers, source fingerprints and information-safe
Hand Position requests and Learning-v2 rows.

The first Quick attempt found three overlong lines in the updated navigation and
unplayed-summary tests. They were wrapped without changing assertions; both complete
modules and the documentation inventory were rerun before final Quick. The final
format-retest and Quick results are recorded in the completion handoff.

Final byte review and explicit Quick use the development interpreter process-locally:

```powershell
$env:Path = "C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313;" + $env:Path
.\scripts\check.ps1 -Mode Quick
git diff --check
```

The final Quick result/log and final read-only status are recorded in the completion
handoff. **Local Full was not run under the approved routine.** Quick covers Ruff,
packaged-schema parity and input examples; it does not certify the complete regression
suite, generated outputs, distributions or the installation matrix.

## Browser commands and evidence

```powershell
git archive --format=zip --output="$scratch\issue-297-start.zip" c5ab67bf02bfde9bbae4565d19e17b5b0b2f8f19
py -3.13 scripts/verify_match_evidence_workflow.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue-297-browser-baseline-final-layout" --phase before --baseline-archive "$scratch\issue-297-start.zip"
py -3.13 scripts/verify_match_evidence_workflow.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue-297-browser-final-layout" --phase after
py -3.13 scripts/verify_match_setup_and_card_layout.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue-297-setup-supplement" --phase after --scope supplement
py -3.13 scripts/verify_match_declaration_drafts.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue-297-drafts-verified" --phase after
py -3.13 scripts/verify_match_draft_lifecycle.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\issue-297-draft-lifecycle" --phase after
```

| Probe | Completed evidence |
| --- | --- |
| Exact baseline, de/en × JavaScript on/off | 20 landings, 24.247s |
| Changed workflow, same four cells | 101 landings, 35 layout samples / 140 actual palettes, 117.188s |
| Setup supplement | 8 saved/new/mixed/own/manual-own cases, reorder/replacement, neutral Enter, validation/language, real stale Create, 36 Session layout measurements, 93.976s |
| Bea / Grand / 18 → H7/D7 → retained draft → explicit Save | Four cells, 25.847s |
| Native Enter, withdrawal/no-op, two-browser return revocation | Four cells, 106.261s |

Main layout samples use **1365, 1920, 2560, 700, 520, 320 and 240 CSS pixels**,
including a separate long-name fixture. All three source palettes are measured
independently, alongside the genuine sparse Play palette after S10 and rewind.
Representative source fieldset widths/complete-suit rows are:

| CSS viewport | Each source fieldset width | Complete suit row membership |
| --- | --- | --- |
| 1365 / 1920 / 2560 | 1132px | 8 |
| 700 | 585px | 4 + 4 |
| 520 | 405px | 2 + 2 + 2 + 2 |
| 320 | 205px | Eight single Cards |
| 240 | 125px | Eight single Cards |

Card text remains **16px**, inputs **20px**, tiles at least **44px**. Document/client
widths agree and there is no measured horizontal overflow. Screenshots were inspected
for all-source placement, wide/narrow rows, long names, native focus, count/overlap
errors, review landing and legacy correction. The main 1365×900 native review
result is at Y **654.45–678.45**, Create at **686.45–730.45**, focused on
`match-setup-review`; next Tab reaches `setup_action=create` in all four cells.
No verifier scroll/focus occurs before these landing measurements. Example files:

* `issue-297-browser-final-layout/de-0-review-initial-landing.png`
* `issue-297-browser-final-layout/en-1-update-initial-landing.png`
* `issue-297-browser-final-layout/de-1-count-error-initial-landing.png`
* `issue-297-browser-final-layout/de-0-error-language-en-initial-landing.png`
* `issue-297-browser-final-layout/de-0-layout-1365-evidence_original_skat.png`
* `issue-297-browser-final-layout/de-1-layout-700-evidence_discarded_cards.png`
* `issue-297-browser-final-layout/long-name-layout-320-evidence_perspective_hand.png`

All artifacts are external. Actual reported browser zoom is **1 (100%)**; viewport
emulation and device scale 1 are not genuine zoom. Changed-layout **200% zoom remains
pending installed targeted acceptance**. Earlier genuine zoom acceptance remains
valid for its earlier layout, without being borrowed for this change.

### Phase-specific write and operation accounting

Fixture construction is excluded; exact retained bytes/revisions/fingerprints and
actual emitted submitter/checkbox values are retained in each `evidence.json`.

| Phase | Observed accounting |
| --- | --- |
| Native choose/review/Update | Zero recording/profile writes; zero Match/Player IDs |
| Each valid new-player Create | One Match creation, one recording save/replacement, one Match ID, three Player IDs, one legitimate product-first/profile-second metadata write |
| Passive GET/open/focus, capability/materialization inspection | Zero recording/profile writes and zero analysis |
| Changed evidence Save or selected-zero withdrawal | One evidence operation/save/replacement; zero declaration/profile/analysis operations |
| Equal pair or already-absent zero Save | Existing operation, zero recording writes; truthful unchanged receipt; Report/download preservation also tested |
| Count/overlap rejection | Zero accepted changes; no success receipt; exact error/source focus |
| Stale/foreign/ambiguous/failed persistence | HTTP tests require zero accepted recording change; failure cannot publish the candidate |
| Main evidence sequence per cell | Seven evidence saves (one initial-hand plus six pair changes/withdrawals); four separate legitimate language profile writes; zero declarations/analysis |
| S10 / SK / S7 and rewind | Three Play saves, no writes for preview/Cancel, one explicit Apply save; S10 retained |
| Legacy `[]` withdrawal | One evidence save; zero declaration/profile/analysis; accepted-Hand readiness remains available |
| Subsequent explicit non-Hand declaration Save | One declaration/save; no extra evidence mutation; missing non-Hand Discards again block historical materialization |

Historical execution is verified explicitly through the real canonical Request and
Application in tests; it is not attributed to browser GETs or evidence operations.
The generated complete Hand fixtures avoid manual entry of 30 Plays. #292's original
absolute deadline, selected-operation isolation, one-use/replay revocation, source
checks and hidden declaration default submitter remain covered by complete modules
and native sentinels.

## Complete changed-file inventory (41)

Product (13):

```text
src/skatmind/app_web/assets/app.css
src/skatmind/app_web/friendly_creation_rendering.py
src/skatmind/app_web/locales/de.json
src/skatmind/app_web/locales/en.json
src/skatmind/app_web/match_declaration_drafts.py
src/skatmind/app_web/match_evidence_presentation.py
src/skatmind/app_web/match_review_rendering.py
src/skatmind/app_web/seat_setup_rendering.py
src/skatmind/app_web/server.py
src/skatmind/app_web/task_first_match_rendering.py
src/skatmind/app_web/task_first_match_state.py
src/skatmind/match_historical_materialization.py
src/skatmind/observed_game_evidence.py
```

Tests (16; the two workflow/derived-Hand modules are new):

```text
tests/test_compact_card_entry_web.py
tests/test_direct_match_evidence.py
tests/test_frontend_localization_foundation.py
tests/test_match_creation_details.py
tests/test_match_declaration_drafts.py
tests/test_match_derived_hand_readiness.py
tests/test_match_evidence_navigation.py
tests/test_match_evidence_presentation.py
tests/test_match_evidence_workflow.py
tests/test_match_game_navigation.py
tests/test_match_historical_materialization.py
tests/test_match_person_review_actions.py
tests/test_observed_game_evidence.py
tests/test_task_first_match_and_learning_workflow.py
tests/test_unified_workflow_visual_contract.py
tests/test_unplayed_card_summary.py
```

Verification tools (4; the evidence-workflow verifier is new):

```text
scripts/verify_match_declaration_drafts.py
scripts/verify_match_draft_lifecycle.py
scripts/verify_match_evidence_workflow.py
scripts/verify_match_setup_and_card_layout.py
```

Documentation (8; this verification record is new):

```text
docs/compact_card_entry.md
docs/match_analysis_and_exports.md
docs/match_evidence_workflow.md
docs/match_recording_error_recovery.md
docs/match_review_and_materialization.md
docs/match_setup_and_card_layout.md
docs/observed_game_capture_contracts.md
docs/profile_driven_stateful_creation.md
```

## Remaining gates

Keep **#297 open** for new exact-commit branch/main `check` and
`v1-supported-platform-matrix` evidence and installed changed-path acceptance,
including native JavaScript-disabled operation and genuine 200% changed-layout
zoom. This is source-tree developer verification, not maintainer UAT. #292–#296
remain functionally complete. #208 remains open; UAT-01 is not globally accepted,
UAT-02–12 remain paused, and full maintainer UAT plus the current detailed
architecture/code analysis and treatment of material findings are still required
before v1.0.0. This issue authorizes no release preparation.
