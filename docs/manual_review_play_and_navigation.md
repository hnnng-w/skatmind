# Manual Review Play selection and navigation (Issue #305)

## Checkout, scope and implementation

Expected and actual starting branch: `bug/305-review-play-and-navigation`.
Expected and actual starting HEAD: `3d4681b35d6fe7a41cc2a7ed3e5d63def80cfbf6`.
The initial worktree was clean. Implementation remains unstaged and uncommitted
on that branch and HEAD.

The maintainer accepted #304 A–D at that commit: all eight checkbox palettes,
restricted Discards, native operation and enlarged browser zoom. That acceptance
is retained. This issue separately corrects active manual Review step-5 Play entry
and the shared seven-step manual wizard footer.

The step-5 renderer previously called `_card_select()` with no empty option. The
browser displayed the first legal Card by default. `_review_play_palette()` now
adapts the existing neutral `compact_card_groups()` renderer to exactly
`view.legal_cards`, in guided printed-suit **C/S/H/D** and rank
**A/10/K/Q/J/9/8/7** order. Empty suit groups are omitted. The unchanged authoritative
view supplies actor/legality; this is presentation ordering only.

All choices are required native radios named singular `card`, with exact canonical
values and no initial check, including singleton sets. They retain compact faces,
localized accessible names, native selection/focus and the balanced layout.
One explicit Record played Card submission appends once through the existing
route/revision/instrumentation. Card selection itself has no request or Product
effect. The completed 30-Play Back/Continue path remains card-free.

The fieldset owns one `field-card` ID and `data-validation-group="card"`.
`<!-- validation-messages:card -->` places error text outside the tile groups.
Existing validation code supplies summary focus, a real focusable group link and
ARIA descriptions. Existing safe radio restoration can check only offered choices;
unavailable rejected Cards cannot create tiles. Enhanced language return retains
one offered selection or explicit emptiness; native return does not carry unsent
selection. All accepted-operation/stale-binding checks remain authoritative.

The old footer was a wrapping flex row with default cross-axis stretching. Its
Back form is a grid, so its sole visible button stretched to the Reset form's full
row height, including Reset's extra top margin. Back now uses `button.secondary`.
Only `.wizard > .wizard-actions` and its direct forms receive start alignment,
bounded wrapping and zero margins. The wizard gap owns footer spacing; Reset keeps
its distinct border, padding, destructive button and unchecked required consent.
There is no fixed height. Step 1 has only Reset; steps 2–7 have separate Back and
Reset forms in their existing keyboard order.

No shared compact renderer, rejection code, JavaScript, registry or translation
changed. Inventories remain **9 static routes / 73 POST routes / 125 forms /
2,118 matching catalog keys per locale**. Other dropdowns, chronological input,
retained Requests/Results/downloads, Product rules and persistence keep their
existing contracts.

## Regression-first evidence and intermediate corrections

All validation invocations use process-selected **CPython 3.13.7** and an explicit
**7,200,000ms tool timeout**. The timeout is tool configuration, not a CLI argument.
All browser homes/profiles, temporary tests, logs and evidence are disposable and
outside the repository. No installed UAT environment or real managed data is used.

Before Product edits, delivered HTTP contained one step-5 dropdown and zero radios.
The actual browser reproduction in `305-before` confirmed the same for German/
English with JavaScript on/off. At 1365×900, Back measured **138px** high; Reset
measured **114px**, with **24px** extra top margin. Initial captures precede
verifier scrolling/focus. The screenshot is supported by HTTP and runtime geometry.

The new delivered-HTTP module initially reported **20 failed / 12 passed**. Its
first helper incorrectly assumed every page had field-level error links and every
footer form had editable language fields; the missing-value probe also inherited
the old dropdown default. After correcting those test assumptions, the unchanged
Product rerun again reported **20 failed / 12 passed**, now precisely on absent
radio fieldsets and Back's absent secondary role. The 12 passes verify existing
stale language/Play binding rejection.

The first repaired three-module run reported **121 passed / 2 failed** because the
new Trick fixture attempted Bea's `HA` for Clara. Correcting that test to Clara's
`H9` produced **123 passed**. A focused Ruff invocation found import formatting,
one unused verifier import and one long test line; all were corrected. There were
no failing real-browser repaired runs: `305-after-a` and final `305-after-b` each
completed all four cells and 120 measurements. The final script adds aggregate
operation totals to its retained per-phase records.

## Exact commands and complete affected-module inventory

```powershell
$E = 'C:/Users/HENNIN~1/AppData/Local/Temp/opencode'
$B = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

# Both regression-first executions ran before Product edits.
py -3.13 -m pytest tests/test_manual_review_play_navigation.py -q --tb=short `
  -o cache_dir="$E/305-red-cache" --basetemp="$E/305-red-tmp" --junitxml="$E/305-red.xml"
py -3.13 -m pytest tests/test_manual_review_play_navigation.py -q --tb=short `
  -o cache_dir="$E/305-red2-cache" --basetemp="$E/305-red2-tmp" --junitxml="$E/305-red2.xml"

# First repaired run, then corrected fixture repeat.
py -3.13 -m pytest tests/test_manual_review_play_navigation.py `
  tests/test_completed_trick_input_grouping.py tests/test_guided_card_palettes.py `
  -q --tb=short -o cache_dir="$E/305-green-cache" --basetemp="$E/305-green-tmp" `
  --junitxml="$E/305-green.xml"
py -3.13 -m pytest tests/test_manual_review_play_navigation.py `
  tests/test_completed_trick_input_grouping.py tests/test_guided_card_palettes.py `
  -q --tb=short -o cache_dir="$E/305-green2-cache" --basetemp="$E/305-green2-tmp" `
  --junitxml="$E/305-green2.xml"

$modules = @(
  'tests/test_manual_review_play_navigation.py',
  'tests/test_guided_card_palettes.py',
  'tests/test_guided_frontend_contracts.py',
  'tests/test_guided_frontend_web.py',
  'tests/test_guided_frontend_execution.py',
  'tests/test_guided_frontend_json_transfer.py',
  'tests/test_guided_frontend_result_presentation.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_guided_historical_review_form.py',
  'tests/test_guided_position_form.py',
  'tests/test_frontend_validation_preservation.py',
  'tests/test_frontend_language_switching.py',
  'tests/test_language_switch_context.py',
  'tests/test_language_view_continuity.py',
  'tests/test_language_view_script.py',
  'tests/test_task_first_language_preservation.py',
  'tests/test_completed_trick_input_grouping.py',
  'tests/test_consistent_card_presentation.py',
  'tests/test_analysis_download_details.py',
  'tests/test_analysis_review_entry_paths.py',
  'tests/test_manual_review_saved_names.py',
  'tests/test_bilingual_home_information_architecture.py',
  'tests/test_unified_workflow_visual_contract.py',
  'tests/test_unified_local_app_contracts.py',
  'tests/test_unified_local_app_web.py',
  'tests/test_frontend_localization_foundation.py',
  'tests/test_complete_frontend_localization.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_skatmind_rename.py',
  'tests/test_settings_reset_presentation.py'
)
py -3.13 -m pytest @modules -q --tb=short --durations=15 `
  -n 2 --dist=loadfile --max-worker-restart=0 `
  -o cache_dir="$E/305-affected-cache" --basetemp="$E/305-affected-tmp" `
  --junitxml="$E/305-affected.xml"

# Final complete-module repeat after documentation and full diff review.
py -3.13 -m pytest @modules -q --tb=short --durations=15 `
  -n 2 --dist=loadfile --max-worker-restart=0 `
  -o cache_dir="$E/305-final-affected-cache" --basetemp="$E/305-final-affected-tmp" `
  --junitxml="$E/305-final-affected.xml"

py -3.13 scripts/verify_manual_review_play_navigation.py --browser $B --output "$E/305-before" --phase before
py -3.13 scripts/verify_manual_review_play_navigation.py --browser $B --output "$E/305-after-a" --phase after
py -3.13 scripts/verify_manual_review_play_navigation.py --browser $B --output "$E/305-after-b" --phase after

py -3.13 -m ruff check src/skatmind/app_web/guided_rendering.py `
  tests/test_manual_review_play_navigation.py tests/test_completed_trick_input_grouping.py `
  scripts/verify_manual_review_play_navigation.py

function python { & py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
git diff --cached --stat
git status --short --branch
git rev-parse HEAD
```

The **30 complete modules contain 850 distinct passing tests**, with no skips.
The complete affected run passed in **191.99s**. The new module contributes 32
tests. The earlier 123-test pass and all later repeats overlap those 850; they are
not additional distinct coverage. #303/#304 tests and strict inventories remain
intact. The two existing manual-selector sentinels in completed-Trick coverage
now check radio names, membership/order, full accessible labels and the group
feedback target rather than assuming a select; neighboring select assertions remain.

The inventory follows `guided_rendering` through its actual guided workflows,
forms, execution, JSON transfer, retained Results/downloads, feedback, language,
packaging/localization and rename checks. The narrowly scoped footer CSS is covered
by visual-contract and independent Settings-reset sentinels. The shared neutral
component and rejection transport were not edited, so no extra Session/Match
caller expansion is required.

No exclusive module is selected: `test_early_rejection_observer.py` and
`test_unified_rejection_transport.py` concern unchanged transport/worker rejection;
`test_local_learning_corpus_web.py` concerns unchanged standalone Corpus;
`test_match_analysis_action_placement.py` concerns unchanged Match analysis layout.
No exclusive worker overlaps the parallel run. The approved routine uses explicit
Quick, not local Full. Quick is partial validation and cannot authorize issue closure.

Explicit Quick passed with exit **0** in **2.397s**: Ruff, packaged-schema byte
parity and all Root/Session input examples. Its log directory is
`C:/Users/Henning-DT/AppData/Local/Temp/skatmind-check-30lxz3lt`. The final
complete-module repeat uses `305-final-affected.xml`; the final post-documentation
Quick log and unchanged checkout confirmation are recorded in the handoff.

## Real-browser results and operation accounting

Final evidence: **`$E/305-after-b/report.json`**, delivered step HTML and PNGs in its
`de-False`, `de-True`, `en-False`, `en-True` directories. Baseline evidence is
`$E/305-before/report.json`, `initial.html`, `initial.png` and footer captures per
cell. `305-after-a` is a separate completed repeat, not additional distinct tests.
The verifier uses real HTTP, the existing dependency-free DevTools helper and
headless **Microsoft Edge 156.0.4314.50** on Windows with source-tree imports/assets.
Served CSS/JavaScript hashes match source; source hashes are retained in the report.

All seven wizard footers are measured at **1365×900, 520×900 and 320×900** in all
four language/script cells. Active Play additionally uses **1920×900, 2560×900
and 440×900**. Restricted and singleton palettes are measured at the three primary
sizes. Initial screenshots precede verifier scroll/focus. Actual rectangle data,
not CSS-string assertions, proves the fix:

| Measurement | Actual result |
| --- | --- |
| Back, steps 2–7, both languages and script modes | 44px height, matching its own form; independent of taller Reset |
| Reset at 1365px | 114px height, zero top margin |
| German Reset at 320px | 186px height, including 96px wrapped consent label; Back remains 44px |
| Step 1 | Reset only; no Back |
| Initial Clubs at 1365/1920/2560px | 1144.81px suit width; one eight-Card row |
| Initial Clubs at 520px | 417.81px suit width; 4 + 4 |
| Initial Clubs at 440/320px | 337.81/217.81px suit width; 2 + 2 + 2 + 2 |
| Card text / native radio / minimum tile height | 16px / 20px / 44px |
| Keyboard focus | Visible 3px outline and checked-tile cue |
| Horizontal overflow | None in any measured document or Card tile |

Real pointer and native Tab/Space/ArrowRight input exercise selection and explicit
submission. Tab enters/leaves the same-name radio group normally. Passive radio
changes produce no network request. Native required validation blocks empty Play
and unconfirmed Reset. Verifier-only `noValidate` then allows genuine HTTP 400
responses to test server rejection, unchanged accepted state, actual summary
autofocus and error-link focus on `field-card`. No rejection HTML is fabricated.

Each cell records `SA`, `SK`, `H9` through browser controls and verifies Anna wins
and leads again. Undo restores Clara's turn; native Back submits only Back and
preserves the Plays. The Grand `CJ` lead produces Bea's unselected singleton `SJ`.
Supported HTTP forms complete the remaining fixture to 30 Plays. Browser Back
and card-free Continue exercise the completed edge; no maintainer game re-entry
is required. Language return verifies explicit emptiness and one enhanced unsent
choice; native unsent choice is correctly absent. The HTTP suite additionally
checks stale language forms after append, Undo and Back and safe rejected choices.

For **each** completed repaired four-cell run (`305-after-a` and `305-after-b`):

| Phase | Operations |
| --- | --- |
| Initial synthetic fixtures | Four each: manual Start, Players, Deal, Declaration, Discards; four explicit locale profile saves |
| Accepted Play/Undo/Continue | 132 chronological appends, 12 Undo operations, four card-free Continue submissions; process-local only |
| Other accepted navigation | Eight Back, four additional Discards submissions, four Options submissions |
| Explicit language returns | Eight profile saves; no Product execution or recording write |
| Server rejection | Four missing-Card HTTP 400 responses and four unconfirmed Reset HTTP 400 responses |
| Deliberate confirmed Reset | Four process-local resets |
| Passive rendering, selection and unavailable-download probes | Zero POSTs, Product execution, preparation, persistent replacement, profile save or generated Product ID; snapshots unchanged |

Each repaired run has **12 profile saves / 12 corresponding persistent replacements**
total, all explicitly attributable to locale changes. No Product execution,
Learning preparation, recording persistence or generated Product IDs occur in any
phase. Across the two completed repeats there are 24 locale saves/replacements;
their mutations are separate from passive activity. The initial pre-edit browser
probe used four five-step fixtures and four explicit language changes; its original
report records geometry, while the repaired verifier adds observed per-phase
operation instrumentation. Downloads are unavailable because no review execution
was requested; retained successful-download ownership is covered by the complete
execution/JSON/Result/download modules.

**Zoom limitation:** measured browser zoom, DPR and visual scale are all **1**.
These CSS viewport measurements are at actual **100% browser zoom**, not genuine
enlarged zoom. Installed targeted acceptance, including genuine enlarged browser
zoom for this new boundary, remains pending. #304's already accepted enlarged-zoom
scope remains complete.

## Handoff gates

**Locally validated; new exact-commit hosted CI and installed targeted acceptance
pending.** Keep #305 open for those gates. The maintainer must obtain exact-commit
`check` and `v1-supported-platform-matrix` evidence and installed affected-path
acceptance. Quick does not certify generated outputs, built distributions,
installation matrix or the complete regression suite; no local Full is claimed.

#292–#304 remain complete within their accepted scopes. Keep #208 open: UAT-01 is
not globally accepted and UAT-02–12 remain paused. Release preparation is not
authorized. No Git publication, issue modification, Actions trigger or installed
UAT operation is performed by the agent.
