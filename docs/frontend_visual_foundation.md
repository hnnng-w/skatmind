# Shared frontend visual foundation

Issue #295 establishes the first shared visual foundation in `app_web/assets/app.css`.
It applies to the unified shell, Home, Settings, analysis/review, Session, Match
and Learning. Standalone resources and the existing light-theme boundary remain
separate. This is presentation work; accepted #289–#294 interactions remain intact.

## Current visual rules

* Use the local `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
  stack. Root size is 100%; body and ordinary controls are 1rem with body line-height
  1.5. Secondary metadata may use .875rem. Machine-readable `pre`/`code` stays
  monospace. There are no external fonts or resources.
* Page titles are 1.75rem, sections 1.25rem and subsections 1.0625rem. There is no
  global title-width constraint or separate oversized Match/Session title scale.
* Shared spacing tokens are .25, .5, .75, 1, 1.5 and 2rem. Page vertical padding is
  2rem; section insets range from 1 to 1.5rem. Explicit `.content-stack` wrappers
  normalize their direct heading/body margins. Native form/fieldset gaps remain.
* Neutral page, white content surfaces, restrained borders and .5rem surface radii
  replace diagonal backgrounds and offset decorative shadows. Nested `.panel`
  sections share their containing region rather than acquiring another surface.
* `.primary` is filled green, `.secondary` is neutral/outlined and `.destructive`
  is red. Legacy unclassified submit buttons retain the primary default. Touched
  Settings, person-review, creation, deletion, guided reset and shared destructive
  workflow controls have explicit roles, independent of disclosure ancestry.
  Ordinary links retain their quieter underlined presentation. Hover/active,
  disabled and visible keyboard-focus states have complete color pairs.
* Visible buttons are at least 2.75rem high; native checkbox/radio boxes remain
  1.25rem and cannot flex-shrink. Hidden native default submitters receive no
  visible-control geometry. Their enabled status, form owner, order and implicit
  Enter behavior remain authoritative.
* Main retains its 76rem cap; reading paragraphs are separately bounded at 72ch.
  The application is not constrained to a prose column. No CSS visual reordering,
  clipping of focus, document-overflow hiding or zoom emulation is introduced.

## Card-width boundary

Normal Match's four palettes retain literal complete-suit rows of eight at
1365, 1920 and 2560 CSS pixels, including Play beside secondary context. The
existing 12em/24em/48em suit thresholds produce 1/2/4/8 balanced tracks; Match
stacks context until its 69em container transition, then uses
`minmax(0, 3fr) minmax(18em, 1fr)`. Card text is at least 16px, native inputs 20px,
tiles at least 44px. Local container geometry, real row membership, sparse
remainders and focus room must be checked after font/inset changes. Session's
existing layout remains a separate consumer of the shared card styles.

## Reset and deletion boundaries

Settings has one padded Reset section with two separate forms. Each description
and its consent/action group share a row when space permits, and stack in DOM
order when narrow. Compact heading/description stacks do not stretch vertically.
All other Settings controls and profile metadata remain available.

The paired catalogs contain the concise approved reset and recording-deletion
copy. Preferences reset still clears compatibility-only
`advanced_settings_expanded` alongside preferred perspective/platform; the
hidden preferences field retains its existing round-trip behavior. Its internal
name is absent from ordinary consent copy. Full reset, generation/CAS protection,
invalid-profile recovery, no-op behavior and recording-file boundaries are
unchanged. See [Settings](settings_and_player_seat_setup.md#explicit-saving-and-reset-scope).

Deletion retains the exact target, participants/progress, whole-recording scope,
irreversibility, conditional active-recording effects, required unchecked consent,
native destructive Apply and separate Cancel form. Routine retained-copy/download
prose and its two unused catalog keys are removed. Expired/error navigation and
successful-deletion/failed-list-refresh distinction remain. Existing guards stop
stale result publication; the copy does not claim forced computation termination.
See [managed deletion](managed_recording_deletion.md).

Derived inventories: **73 POST routes, 125 forms, 2,036 keys per locale**. Strict
form, paired-key/order/placeholder, packaging and rename checks remain enabled.
No operation, route, field allowlist, persisted format or dependency changes.

## Reproducible local verification

Use the existing CPython 3.13 environment for this process only. The source-tree
developer browser verifier uses genuine authenticated HTTP pages and disposable
managed roots. It records baseline/final screenshots, typography, dimensions,
native requests, persistence accounting, role states, CSP and resource hashes.
The #292/#293/#294 tools retain their own source-bound behavioral assertions.

```powershell
py -3.13 -m pytest `
  tests/test_unified_workflow_visual_contract.py `
  tests/test_recording_entry_settings_navigation.py `
  tests/test_profile_driven_settings_web.py `
  tests/test_settings_reset_presentation.py `
  tests/test_recording_deletion_web.py `
  tests/test_recording_deletion_lifecycle.py `
  tests/test_match_setup_and_card_layout.py `
  tests/test_match_person_review_actions.py `
  tests/test_match_declaration_drafts.py `
  tests/test_learning_prepared_navigation.py `
  tests/test_frontend_validation_preservation.py `
  tests/test_language_view_continuity.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py `
  tests/test_packaging_and_distribution.py `
  tests/test_skatmind_rename.py `
  -n 2 --dist=loadfile --max-worker-restart=0 -q -ra --tb=short --durations=10

# Complete shared card, form-role and creation/rendering callers.
py -3.13 -m pytest `
  tests/test_compact_initial_hand_web.py tests/test_compact_skat_discard_web.py `
  tests/test_compact_play_grid_web.py tests/test_task_first_stateful_rendering.py `
  tests/test_task_first_match_and_learning_workflow.py tests/test_guided_frontend_web.py `
  tests/test_profile_driven_creation_web.py `
  -n 2 --dist=loadfile --max-worker-restart=0 -q -ra --tb=short --durations=10

$scratch = "$env:TEMP\opencode"
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
py -3.13 scripts/verify_frontend_visual_foundation.py --browser "$edge" --output "$scratch\295-foundation-baseline" --phase before
py -3.13 scripts/verify_frontend_visual_foundation.py --browser "$edge" --output "$scratch\295-foundation-current" --phase after
py -3.13 scripts/verify_match_setup_and_card_layout.py --browser "$edge" --output "$scratch\295-layout-final" --phase after --scope layout
py -3.13 scripts/verify_match_setup_and_card_layout.py --browser "$edge" --output "$scratch\295-setup-final" --phase after --scope supplement
py -3.13 scripts/verify_match_declaration_drafts.py --browser "$edge" --output "$scratch\295-drafts-final" --phase after
py -3.13 scripts/verify_match_draft_lifecycle.py --browser "$edge" --output "$scratch\295-enter-final" --phase after
py -3.13 scripts/verify_learning_prepared_navigation.py --browser "$edge" --output "$scratch\295-learning-final" --phase after
py -3.13 scripts/verify_operation_feedback.py --source --phase after --overlay --browser "$edge" --output "$scratch\295-overlay-complete"
git diff --check
function python { py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
```

Output directories must be fresh; baseline captures run before Product edits.
The accepted #294/#293 behavior is the #295 baseline, so their existing tools use
`--phase after` in both comparisons. Their historical `--phase before` modes
expect pre-#294/#293 defects and are not the #295 baseline. The feedback probe now
measures actual control/notice overlap before checking withdrawal, rather than
assuming that a fixed control top still overlaps after a font change. It retains
the same real timed/no-layout-shift, native fallback and language assertions.

Evidence uses Windows 11 Pro build 26300, PowerShell 5.1.26100.9711, CPython 3.13.7,
pytest 9.0.3 and headless Edge 155.0.4283.62. Genuine 100% browser zoom is measured.
The headless Ctrl-plus probe requested 200% but still reported zoom 1: **changed-font
200% acceptance remains pending for installed retest**. Viewport emulation is
labelled separately and is not zoom. No maintainer installation/data or manual
reset is used. These checks do not constitute UAT or appearance approval.

After successful local gates, report **locally validated, CI and installed retest
pending**. Keep #295 and #208 open; #289–#294 remain complete. UAT-01 is not globally
accepted, UAT-02–12 remain paused, and overall UI, fresh architecture/code analysis
and v1.0.0 readiness remain open. Exact-commit hosted CI and installed visual
acceptance are subsequent maintainer gates. Final counts, timings and external
evidence locations are in the task handoff.
