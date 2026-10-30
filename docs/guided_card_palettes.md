# Guided suit-grouped Card palettes (Issue #304)

**Accepted baseline:** the maintainer accepted #304 A–D at
`3d4681b35d6fe7a41cc2a7ed3e5d63def80cfbf6`, including all eight checkbox palettes,
restricted Discards, native operation and enlarged browser zoom. The implementation
and pending-gate statements below are historical developer evidence. Issue #305's
[active-Play palette and footer correction](manual_review_play_and_navigation.md)
is a separate boundary and does not reopen that acceptance.

## Boundary and implementation

The clean starting checkout was `bug/304-guided-card-palettes` at
`038130df1296675b96a83c4631d7ecb754ebadd1`. The branch and HEAD remain unchanged;
the implementation is unstaged working-tree work.

The old `guided_rendering._card_palette()` rendered every Card into one
`repeat(auto-fit, minmax(11.5rem, 1fr))` grid. The disposable browser reproduction
at 1365 CSS pixels produced five columns and rows that mixed printed suits,
matching the maintainer's screenshot finding.

`compact_card_rendering.compact_card_groups()` now owns only the shared native
choice/group markup and compact faces. Its caller supplies ordered groups,
localized plain-text headings, accessible Card names, field name and selection.
It escapes text, omits empty groups and does not sort. The existing Session/Match
selector delegates to it with its original J-first display order and summary.
The guided adapter supplies canonical guided order:

* Printed suits: **C, S, H, D**.
* Ranks: **A, 10, K, Q, J, 9, 8, 7**.

This is also native keyboard and submission order. No CSS order is involved.
Historical `values.all(field)` and retained Position arrays therefore receive
the same ordered selections as before.

| Caller | Offered Cards |
| --- | --- |
| Review step 2: `forehand_hand`, `middlehand_hand`, `rearhand_hand`, `skat` | Four complete printed suits in each palette |
| Review step 4: `discarded_cards` | Exactly the declarer's original ten plus original Skat; empty suits omitted |
| Analyze: `hand`, `skat`, `public_declarer_cards` | Four complete printed suits in each palette |

The guided adapter retains `card-palette`, its fieldset/legend, `field-<name>`,
error IDs and ARIA relationships, original count meaning, checkbox names/values,
form ownership, revisions and instrumentation. It adds `compact-cards` and
`data-balanced-grid` to use the established tracks at 48/24/12em available suit
widths. Existing 16px faces, 20px native inputs, 44px minimum targets, checked
styling and focus treatment apply. All three Analyze palettes retain exactly one
`data-validation-group`, the exact `<p data-validation-card-count="FIELD">`
marker, and `<!-- validation-messages:FIELD -->` boundary.

There is no `.compact-selection`, `.compact-count`, `.compact-selected` or
`data-count-template` in guided palettes. The existing optional JavaScript
summary updater returns without changing the guided count. Native pending checks
remain the selection indication; no second summary is introduced.

Review still validates one unique complete 10/10/10/2 distribution, exactly two
authorized non-Hand discards, and the existing Hand exception with no discard
palette. Single-Card dropdowns, chronological Tricks, legal Play selection,
ranked Results, imported Requests and retained download ownership keep their
existing contracts. CSS, JavaScript, translations, locale resolution, Product
validation, execution methods, persistence and public/package contracts are not
changed. Inventories remain **9 static routes / 73 POST routes / 125 forms /
2,118 matching catalog keys per locale**.

## Regression-first HTTP verification

`tests/test_guided_card_palettes.py` adds 16 German/English cases using delivered
HTTP forms, real hidden revisions/instrumentation and supported HTTP transitions.
Selections are serialized from emitted checkbox order. Coverage includes all
eight callers, full and restricted group membership, omitted empty groups,
complete accessible names, unique page IDs, native ownership, stale submission,
valid deal/discard progression and Back, invalid counts and duplicate distribution,
safe rejected checks, native/enhanced language return, analysis feedback/count
restoration, forged unavailable discard rejection, exact retained Position
Request arrays and passive file preservation.

The existing guided HTTP test now checks all nine retained rejected hand Cards
through the actual form parser, rather than assuming `value` and `checked`
attributes are adjacent. This strengthens the behavioral assertion while allowing
the full accessible-name attribute.

Initial execution of the first 12 tests failed: eight on the missing compact
grouping and four because the test incorrectly applied Analyze-only error-target
assumptions to Historical form-level feedback. After correcting that test helper
and completing the suite, **all 16 failed on the missing grouping before Product
edits**. The first post-edit run of the new module plus guided HTTP module had
**36 passes / one failure**, the old attribute-adjacency assertion described above.
The complete affected-module runs subsequently passed.

## Complete affected-module inventory and commands

The inventory follows actual `_card_palette` callers through the page renderer,
guided parsing/execution/import/export, feedback/language restoration, #303 entry
and saved-name sentinels, strict inventories and packaging. The extracted shared
group renderer additionally reaches `task_first_session_rendering`,
`task_first_match_rendering` and `match_recovery_rendering`; their set/Play,
evidence, correction, task/focus and transport modules are included. Existing
read-only consumers are covered by the consistent-Card presentation module.
Neither CSS nor JavaScript changed.

Commands use process-selected CPython **3.13.7**. Every validation tool invocation
uses an explicit **7,200,000ms tool timeout**, not an application option. `$E`
below is `C:/Users/HENNIN~1/AppData/Local/Temp/opencode`. Cache, temporary test data,
JUnit and browser evidence are outside the repository.

```powershell
$E = 'C:/Users/HENNIN~1/AppData/Local/Temp/opencode'

# Regression-first executions; red2 is the completed pre-Product 16-case suite.
py -3.13 -m pytest tests/test_guided_card_palettes.py -q --tb=short `
  -o cache_dir="$E/304-red-cache" --basetemp="$E/304-red-tmp" --junitxml="$E/304-red.xml"
py -3.13 -m pytest tests/test_guided_card_palettes.py -q --tb=short `
  -o cache_dir="$E/304-red2-cache" --basetemp="$E/304-red2-tmp" --junitxml="$E/304-red2.xml"
py -3.13 -m pytest tests/test_guided_card_palettes.py tests/test_guided_frontend_web.py `
  -q --tb=short -o cache_dir="$E/304-green-cache" --basetemp="$E/304-green-tmp" `
  --junitxml="$E/304-green.xml"

# Complete guided modules: 777 passed.
py -3.13 -m pytest `
  tests/test_guided_card_palettes.py `
  tests/test_guided_frontend_contracts.py `
  tests/test_guided_frontend_web.py `
  tests/test_guided_frontend_execution.py `
  tests/test_guided_frontend_json_transfer.py `
  tests/test_guided_frontend_result_presentation.py `
  tests/test_guided_frontend_packaging.py `
  tests/test_guided_historical_review_form.py `
  tests/test_guided_position_form.py `
  tests/test_frontend_validation_preservation.py `
  tests/test_frontend_language_switching.py `
  tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py `
  tests/test_language_view_script.py `
  tests/test_task_first_language_preservation.py `
  tests/test_completed_trick_input_grouping.py `
  tests/test_analysis_download_details.py `
  tests/test_analysis_review_entry_paths.py `
  tests/test_manual_review_saved_names.py `
  tests/test_bilingual_home_information_architecture.py `
  tests/test_unified_workflow_visual_contract.py `
  tests/test_unified_local_app_contracts.py `
  tests/test_unified_local_app_web.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py `
  tests/test_packaging_and_distribution.py `
  tests/test_skatmind_rename.py `
  -q --tb=short --durations=15 -n 2 --dist=loadfile --max-worker-restart=0 `
  -o cache_dir="$E/304-guided-cache" --basetemp="$E/304-guided-tmp" `
  --junitxml="$E/304-guided.xml"

# Complete shared-caller modules: 340 passed; independent two-worker process.
py -3.13 -m pytest `
  tests/test_consistent_card_presentation.py `
  tests/test_compact_card_entry_web.py `
  tests/test_compact_initial_hand_web.py `
  tests/test_compact_skat_discard_web.py `
  tests/test_compact_play_grid_web.py `
  tests/test_compact_session_cards.py `
  tests/test_session_card_feedback_web.py `
  tests/test_session_direct_card_start_web.py `
  tests/test_task_first_stateful_rendering.py `
  tests/test_task_first_match_and_learning_workflow.py `
  tests/test_match_setup_and_card_layout.py `
  tests/test_match_card_correction_ui.py `
  tests/test_match_recording_recovery_web.py `
  tests/test_direct_match_evidence.py `
  tests/test_match_evidence_presentation.py `
  tests/test_match_evidence_workflow.py `
  tests/test_match_evidence_navigation.py `
  tests/test_recording_task_focus.py `
  -q --tb=short --durations=15 -n 2 --dist=loadfile --max-worker-restart=0 `
  -o cache_dir="$E/304-shared-cache" --basetemp="$E/304-shared-tmp" `
  --junitxml="$E/304-shared.xml"

# Only after every parallel worker exited: 37 passed.
py -3.13 -m pytest tests/test_unified_rejection_transport.py -q --tb=short --durations=15 `
  -o cache_dir="$E/304-serial-cache" --basetemp="$E/304-serial-tmp" `
  --junitxml="$E/304-serial.xml"

# Final affected-module repeat after test-line formatting and documentation edits: 24 passed.
py -3.13 -m pytest tests/test_guided_card_palettes.py tests/test_skatmind_rename.py `
  -q --tb=short -o cache_dir="$E/304-final-focused-cache" `
  --basetemp="$E/304-final-focused-tmp" --junitxml="$E/304-final-focused.xml"
```

These **46 complete modules** contain **1,154 distinct passing tests**, with no
skips. Durations were 137.56s, 223.16s and 16.46s respectively. The serial module
was selected because it exercises the shared compact Session form/rejection
transport. Unrelated exclusive observer, standalone Corpus and Match analysis
placement modules were not selected. Repeated focused passes are not added to
the distinct count: the final two-module repeat passed 24 tests in 17.65s. Earlier
36 passing executions in the mixed pass/failure run also overlap the same inventory.

## Browser verification

`scripts/verify_guided_card_palettes.py` uses the existing dependency-free DevTools
helper and real headless **Microsoft Edge 156.0.4314.50** on Windows, source-tree
imports/assets, disposable browser profiles and synthetic managed homes. It never
opens an installed UAT environment. Profile selection is explicit; startup-language
behavior is not inferred from the screenshot or changed by this task.

```powershell
$B = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-before" --phase before
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-after-a" --phase after
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-after-b" --phase after
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-after-c" --phase after
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-after-d" --phase after
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-after-e" --phase after
py -3.13 scripts/verify_guided_card_palettes.py --browser $B --output "$E/304-after-f" --phase after
```

The completed baseline has 28 layout measurements across German/English and
JavaScript enabled/disabled. The final completed repaired matrix, **`304-after-f`**,
has 92: seven viewport
sizes for full deal, restricted discards and all three analysis palettes, plus a
bounded Session checkbox regression at two sizes, in all four language/script
cells. An additional 24 constrained-container probes cover both sides of each
8/4/2/1 transition. All eight guided callers receive real pointer selection;
native Tab/Space order is exercised in every palette, alongside explicit button
activation. The report records actual rendered language after each language switch,
not just the initial case label. Served CSS and workflow JavaScript match the source
hashes. `304-after-d` was a separate completed 92-measurement run; the final repeat
adds per-palette keyboard checks, measured transition rows and served-asset checks.

Wide geometry is measured from actual rendered tile rectangles, not inferred from
CSS declarations. At **1365/1920/2560 CSS pixels**, complete suits occupy **one
eight-Card row** in every guided palette. Narrow **520/440/420/320** viewports use
balanced rows with no document or tile horizontal overflow. Explicit verifier-only
suit widths **770/767, 386/383, 194/191px** demonstrate **8/4, 4/2, 2/1** transitions.
The one-track probe is a constrained container on the actual page, not a claim of
an ordinarily one-track 320px viewport. Card text is **16px**, native inputs **20px**,
targets at least **44px**. Checked tiles retain their green inset cue and native
checkmark; keyboard focus has a visible **3px** outline.

| CSS viewport | Actual guided suit width | Complete-suit rows |
| --- | --- | --- |
| 1365 / 1920 / 2560 | 1144.81px | 8 |
| 520 | 417.81px | 4 + 4 |
| 440 | 337.81px | 2 + 2 + 2 + 2 |
| 420 | 317.81px | 2 + 2 + 2 + 2 |
| 320 | 217.81px | 2 + 2 + 2 + 2 |

Every guided field was measured independently. The common actual main cap explains
equal desktop suit widths. The measured document/client widths agree; the native
vertical scrollbar accounts for the 15px difference from each CSS viewport.

Screenshots include initial delivery before verifier scrolling/focusing, individual
palettes at wide/narrow sizes, restricted membership, the Hand exception, selected
keyboard focus and the container probes. Full names are checked in HTTP markup
and browser attributes. Restricted discards contain exactly twelve allowed Cards
with Hearts omitted in this fixture. Session retains J-first ordering. The matrix
submits genuine incomplete deals and invalid discards/analysis, follows actual
error links, corrects inputs, advances the deal, uses Back, changes to Hand and
returns through native/enhanced language forms. Rejected counts are restored;
enhanced unsent checks and explicit empty selection are retained without analysis.
One explicit small-sample analysis per cell succeeds, with exact retained Request
and Result download bytes checked afterwards.

**Zoom:** `Page.getLayoutMetrics().cssVisualViewport.zoom` is **1**, DPR and visual
scale are **1**. These are emulated CSS viewport sizes at actual **100% browser
zoom**, not enlarged browser zoom. Genuine enlarged zoom and interactive installed
browser acceptance remain outstanding for the changed layout.

### Operation accounting

For the final completed four-cell repaired matrix (`304-after-f/report.json`):

| Phase | Observed operations |
| --- | --- |
| Initial fixture | Four manual starts and four label-step submissions, process-local; four explicit language-profile saves |
| Passive rendering, Card selection and downloads | Zero POSTs, analysis, Learning preparation, persistent replacements, profile saves or generated Product IDs; file bytes/mtimes unchanged |
| Rejection and correction | Twelve rejected guided submissions; accepted deal/declaration/discard/Back operations remain process-local, with zero persistent writes |
| Explicit language return | Ten language-profile saves; zero Product execution or recording writes |
| Deliberate analysis | Four executions, one per cell; zero persistent writes |
| Bounded Session fixtures | Four explicit Session creations: four Session IDs, twelve Player IDs, four recording replacements and four profile saves; subsequent selection adds none |

All fixture and language saves are distinguished from passive activity in each
report. The initial baseline separately saved four explicit language preferences.
The completed `304-after-d` repeat has the same operation totals as the final run;
its executions, creations and language saves are separate, not additional passive
activity or additional distinct tests. Across these two completed repaired runs,
there are eight deliberate analyses, eight Session creations and 36 profile saves
(eight initial language, twenty language-return and eight creation-profile saves).
Earlier incomplete probes remain diagnostic evidence: the first launch lacked
the repository import path; `after-a` assumed a Historical heading link focuses
an ID-bearing control; `after-b` assumed the first Analyze error was necessarily
the hand; `after-c` checked completion before the response to explicit execution;
`after-e` requested the script by its resource filename rather than the existing
`/matches/assets/capture.js` route. Incomplete probe attempts are not included in
the completed-run operation totals; in particular `after-c` ended before it could
establish execution completion. The early scripts evolved between these commands.
These are verifier defects, not claimed passes or Product defects. The corrected
probe waits for actual POST responses and checks the emitted target. Historical
form-level error links preserve their existing fragment behavior; Analyze error
links focus their actual fieldset. An early Ruff pass found probe closure bindings
and a long test line; both were corrected without suppressing checks.

## Acceptance and handoff

**Locally validated; new exact-commit hosted CI and installed targeted acceptance
pending.** Keep #304 open for exact-commit branch/main `check` and
`v1-supported-platform-matrix`, followed by installed affected-path acceptance,
including genuine enlarged zoom. The approved task-specific routine excludes
local Full; Quick is explicitly partial validation. Final Quick/log and diff-review
evidence are recorded in the handoff.

```powershell
function python { & py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
git status --short --branch
git rev-parse HEAD
```

The tracked diff and each new file are reviewed before handoff. All changes remain
unstaged and uncommitted. The eight changed/new files are the two presentation
modules, `tests/test_guided_frontend_web.py`, new
`tests/test_guided_card_palettes.py`, new `scripts/verify_guided_card_palettes.py`,
`docs/compact_card_entry.md`,
`docs/unified_local_frontend_guided_analysis_and_results.md`, and this guide.

#292–#303 remain complete within their accepted scopes, including the maintainer's
#303 A–C acceptance at the starting commit. Historical developer records remain
point-in-time evidence. Keep #208 open: UAT-01 is not globally accepted and UAT-02–12
remain paused. Full maintainer UAT and current architecture/code analysis with
treatment of material findings remain required before v1.0.0. Release preparation
is not authorized.
