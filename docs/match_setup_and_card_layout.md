# Match setup and Card layout — Issue #294

## Scope and implementation

Preflight found a clean `bug/294-match-setup-and-card-layout` at
`27164c80ae5b4ce13220767eb47ff087beda7f84`. The branch and HEAD are retained.
Product changes are private browser setup/presentation changes:

* `player_seat_setup.py`, `profile_driven_creation.py`, `seat_setup_rendering.py`
  and the Match creation form metadata implement person-bound manual choices,
  incomplete roster Update, explicit review/Create, and derived own placement.
* `compact_declaration_rendering.py` separates presentation order from the domain
  constant. `task_first_match_rendering.py` orders declarers by the current Game's
  projected stable identities, retaining the blank required placeholder.
* `compact_card_rendering.py` and `assets/app.css` narrowly extend the Session
  suit-container grid to all four normal Match palettes. External evidence-action
  wrappers use a shrinkable track, including the no-discards action.
* German/English catalogs distinguish assistance from perspective and explain the
  two-step manual setup. Three paired messages are added; two labels are revised.

The directly affected contracts are documented in
[setup](settings_and_player_seat_setup.md#match-person-choice-issue-294),
[creation](profile_driven_stateful_creation.md),
[declaration](compact_game_declaration.md#shared-fields-and-accepted-summary),
and [Card entry](compact_card_entry.md#normal-match-grid-issue-294).

Changed-file inventory (30 files):

* `src/skatmind/app_web/`: `player_seat_setup.py`, `profile_driven_creation.py`,
  `seat_setup_rendering.py`, `form_registry.py`, `compact_declaration_rendering.py`,
  `compact_card_rendering.py`, `task_first_match_rendering.py`, `assets/app.css`,
  `locales/de.json`, `locales/en.json`.
* `tests/`: `test_match_setup_and_card_layout.py` (new),
  `test_compact_card_entry_web.py`, `test_direct_match_evidence.py`,
  `test_frontend_localization_foundation.py`, `test_local_time_entry_web.py`,
  `test_match_card_correction_ui.py`, `test_match_declaration_drafts.py`,
  `test_match_format_presentation.py`, `test_match_game_navigation_web.py`,
  `test_match_recording_recovery_web.py`, `test_own_player_assignment_web.py`,
  `test_profile_driven_creation_web.py`, `test_profile_driven_settings_web.py`.
* `scripts/`: `verify_match_setup_and_card_layout.py` (new),
  `verify_match_declaration_drafts.py` (diagnostic assertion only).
* `docs/`: this new verification record, `settings_and_player_seat_setup.md`,
  `profile_driven_stateful_creation.md`, `compact_game_declaration.md`,
  `compact_card_entry.md`.

Current derived inventories are **73 POST routes, 125 registered forms and 2,037
keys per locale**. The two Match creation definitions use actual dynamic person
choices rather than a static seat-only reflection inventory. No route or form
definition is added. Domain/persisted contracts, dependencies, Package 0.17.0,
the compatibility-only preferred perspective and 98 generated scenarios remain.

## Reproduction and browser evidence

Disposable source-tree checks use Windows 11, CPython **3.13.7**, pytest **9.0.3**
and headless Microsoft Edge **155.0.4283.62**. They do not use installed UAT data.
The pre-edit HTTP regressions and actual browser controls reproduce the redundant
manual-only question, first-roster perspective error, domain-order announcement
controls, table-place-order declarers and a **7+1** Play suit at **663.05px**.

The browser verifier is `scripts/verify_match_setup_and_card_layout.py`. It uses
the existing dependency-free DevTools transport, native keyboard and pointer
events, authenticated real HTTP responses and actual persistence accounting.
It records source/resource hashes, row **membership** from actual tile geometry,
control options, requests, screenshots and operation/write counts. Final layout
measurements require opened evidence panels; a probe-only duplicate disclosure ID
in an earlier exploratory run was corrected before acceptance measurements.

Commands use the approved temporary `opencode` directory as `$scratch`:

```powershell
git archive --format=zip --output="$scratch\match-294-base.zip" 27164c80ae5b4ce13220767eb47ff087beda7f84
py -3.13 scripts/verify_match_setup_and_card_layout.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\match-294-before-visible" --phase before --baseline-archive "$scratch\match-294-base.zip"
py -3.13 scripts/verify_match_setup_and_card_layout.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\match-294-layout-zoom-recorded" --phase after --scope layout
py -3.13 scripts/verify_match_setup_and_card_layout.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\match-294-supplement-zoom-recorded" --phase after --scope supplement
```

The layout matrix is **de/en × JavaScript on/off**, at emulated CSS viewports
**1365×900, 1000×900, 520×844, 320×800**, with a fresh **100% browser zoom** profile,
DPR 1 and visual scale 1. Each final measurement additionally records DevTools'
`cssVisualViewport.zoom = 1`. Viewport emulation is not browser zoom. **Genuine 200%
browser zoom is pending**; the headless harness has no verified zoom control.

Final Match checks cover three evidence palettes, normal Play and the real sparse
31-Card remainder after CA: **48 measurements in 73.178s**. Wide evidence uses eight tracks;
Play beside progress changes 7+1 to 4+4; sufficient full-width Play uses eight.
Narrow palettes use 2/1 tracks according to their own available width. Text stays
16px, controls 20px, tiles at least 44px. Visible panels have equal document/client
widths and no tile overflow; inspected screenshots retain readable faces and
focus outlines. Real sparse membership is retained without placeholders.

The supplement exercises six further native new/mixed/configured-own creations,
reorders a selected person, replaces that person, verifies blank reselection,
switches language, reviews and creates. Existing Session hand/Play grids receive
**16 additional measurements** in English/script-on and German/script-off, with
shared correction-editor screenshots and literal control-order checks.
The complete supplement, including all six creations, took **52.053s**.
The scripts assert selection/Update/review causes zero recording/profile writes;
each Create writes one recording and enriches the profile once. Explicit language
changes are separately counted profile writes. Native CA selection writes nothing;
explicit Play calls `append_plays` and replaces the recording once.

Two exploratory supplement runs lost their DevTools connection during native
select-popup interaction in headless Edge.
The verifier now focuses the actual select and uses native Home/Arrow/Tab keys,
asserting its selected option; it does not assign select values through JavaScript.
One earlier Session supplement assumed an empty directory after saved-Player
fixtures; the completed run explicitly resets only its disposable profile first.

## #292 and #293 compatibility

The existing browser tools also run against this working tree:

```powershell
py -3.13 scripts/verify_match_declaration_drafts.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\match-294-drafts-final" --phase after
py -3.13 scripts/verify_match_draft_lifecycle.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "$scratch\match-294-enter-final" --phase after
```

Both cover all four language/script cells using final HTTP ownership. The draft
probe took **27.499s**; the Enter/lifecycle probe took **110.140s**.
The Bea / Grand / 18 → H7/D7 evidence Save → preserved draft → explicit declaration
Save sequence passes. Valid evidence writes once with zero declaration operations,
profile writes or analysis; invalid/no-op evidence writes zero times. Explicit
declaration Save writes once. Enter in bid and Matadors retains declaration Save;
all evidence intents retain `formnovalidate` and operation isolation. An exploratory
central probe failed a post-submit snapshot assertion; the unchanged behavior
passed the repeat with diagnostic assertion output retained. The enabled hidden
default submitter, absolute draft
deadline, single-use return/replay revocation, source/manifest/language guards and
Session correction safeguards are unchanged. #293's complete prepared-Learning
navigation module is included in affected regressions.

## Regression commands and gates

Complete modules are selected from actual shared callers and assertion searches.
They cover setup/profile creation, local time, all declaration/correction callers,
Match navigation/drafts/direct evidence, Card entry/Play, language/validation,
Session behavior, #293 Learning, strict rename, packaging and localization.
Fixture helpers now resolve their intended declarer by name/identity rather than
the reordered option index. A roster-name replacement explicitly reselects the
person. The Card helper accepts the narrow presentation attribute while retaining
its exact native-control assertions.

The final **68-module run passed 1,658 tests in 1,351.65s**, with **zero skips**.
The first consolidated run had four outdated fixture expectations and 1,617
passes; the corrected six-module helper/caller run passed 157 tests in 154.69s,
before the complete clean final run. The exact final command is below; `$scratch`
is the pre-existing approved temporary directory, and JUnit output is outside
the repository:

```powershell
py -3.13 -m pytest `
  tests/test_match_setup_and_card_layout.py tests/test_player_seat_setup.py `
  tests/test_settings_seat_setup_web.py tests/test_own_player_assignment_web.py `
  tests/test_profile_driven_match_creation.py tests/test_profile_driven_session_creation.py `
  tests/test_profile_driven_learning_creation.py tests/test_profile_driven_creation_web.py `
  tests/test_profile_driven_creation_packaging.py tests/test_profile_driven_form_contracts.py `
  tests/test_profile_driven_settings_web.py tests/test_frontend_profile_persistence.py `
  tests/test_match_creation_details.py tests/test_match_format_presentation.py `
  tests/test_local_time_entry_web.py tests/test_compact_declaration_form.py `
  tests/test_compact_declaration_web.py tests/test_game_declaration.py `
  tests/test_session_declaration_correction_web.py tests/test_session_declaration_correction.py `
  tests/test_match_game_navigation.py tests/test_match_game_navigation_web.py `
  tests/test_match_declaration_drafts.py tests/test_direct_match_evidence.py `
  tests/test_match_evidence_navigation.py tests/test_compact_card_entry_web.py `
  tests/test_consistent_card_presentation.py tests/test_compact_initial_hand_web.py `
  tests/test_compact_skat_discard_web.py tests/test_compact_play_grid_web.py `
  tests/test_compact_session_cards.py tests/test_recorded_trick_progress_web.py `
  tests/test_match_card_correction_ui.py tests/test_optional_matador_entry.py `
  tests/test_task_first_language_preservation.py tests/test_task_first_stateful_rendering.py `
  tests/test_task_first_stateful_projections.py tests/test_task_first_match_and_learning_workflow.py `
  tests/test_frontend_validation_preservation.py tests/test_frontend_language_switching.py `
  tests/test_language_switch_context.py tests/test_language_view_continuity.py `
  tests/test_language_view_script.py tests/test_operation_feedback_language.py `
  tests/test_operation_feedback_web.py tests/test_operation_feedback_script.py `
  tests/test_operation_feedback.py tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py tests/test_packaging_and_distribution.py `
  tests/test_skatmind_rename.py tests/test_match_recording_recovery_web.py `
  tests/test_match_recording_recovery.py tests/test_match_recording_diagnostics.py `
  tests/test_match_workspace_persistence.py tests/test_unplayed_card_summary_web.py `
  tests/test_recorded_decision_context_web.py tests/test_recorded_party_presentation.py `
  tests/test_recorded_review_navigation.py tests/test_session_recorded_review_web.py `
  tests/test_session_direct_card_start_web.py tests/test_session_card_feedback_web.py `
  tests/test_match_analysis_action_placement.py tests/test_null_recording_end_web.py `
  tests/test_null_recording_end.py tests/test_learning_prepared_navigation.py `
  tests/test_learning_debrief_web.py tests/test_unified_rejection_transport.py `
  -q --tb=short --junitxml="$scratch\match-294-focused-final.xml"
```

The final explicit local gate follows diff review:

```powershell
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Quick certifies only Ruff, packaged-schema byte parity and input examples. Local
Full is not run under the approved routine. Exact-commit hosted CI and the
installed targeted maintainer retest remain pending. **Keep #294 open** for those
gates. #292/#293 remain complete, #208 remains open, UAT-01 is not globally
accepted, and UAT-02–12 remain paused. No UAT or release-readiness claim is made.
