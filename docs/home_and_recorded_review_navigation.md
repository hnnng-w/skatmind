# Home and recorded-game review navigation

Issue #229 connects **Home → choose a recording → existing review action → Result
→ the same recording**. It deliberately supersedes the earlier scope guide,
per-task unit/timing/detail blocks, generic related-area panels, and large Home
Product-information card. Earlier #215/#217 implementation evidence remains
historical. This is private presentation and source opening, not another Engine
workflow, a source conversion, or maintainer UAT acceptance.

## Home and entry contracts

The private information-architecture version remains `1`. Three ordered groups
contain five tasks:

| Group | Ordered task keys | Destinations |
| --- | --- | --- |
| `record_games` | `record_match`, `record_session` | `/matches`, `/sessions` |
| `analyze_and_review` | `review_game`, `analyze_decision` | `/review/recorded`, `/analyze` |
| `learn_across_matches` | `learning_insights` | `/learning` |

Issue #255 supersedes #229's plain-link Learning exception: all five tasks have
the same task card, title, description, and native button-styled link. Learning
stays last in its existing group at `/learning`. About is a small normal footer link;
Settings stays directly accessible. Issue #265 makes the Session recording caption
describe recording or opening a saved recording. Continuing an eligible Session
does not start another Game or insert it into a Match. Shared entry rendering supplies one optional short
explanation beneath the page title. Actual recovery, transfer, prerequisite,
source-selection, and return links remain; Learning's explicit-operation
explanation is retained beside its existing preparation controls.

### About reflow (Issue #270)

About retains its three sections in order: Installation; Local operation with the
initially closed native storage-location disclosure; Development and automation.
The four non-clickable filenames below, all facts/prose, IDs, hrefs and language
controls remain exact. About panels now inherit `overflow-wrap: anywhere`, and the
storage summary uses available-width `auto` sizing. This About-only CSS correction
keeps the desktop two-column/full-width-last-section arrangement and shared Settings
description-list rules. At narrow/enlarged text sizes, complete content is available
through ordinary vertical scrolling, including the actual long configured path.

Native marker, pointer/keyboard activation, focus and next Tab to footer About
remain. Existing language restoration keeps open storage with JavaScript and reloads
closed without it. Local disclosure toggles make no request/write; ordinary navigation
and explicit language operations retain their own existing work. See the
[independent installed geometry and native evidence](unified_workflow_visual_contract.md#about-reflow-issue-270).
Learning caption/popup readability and automatic-Learning decisions remain separate.

### Recording entry and Settings/About navigation (Issue #265)

This implements only #208 R01a/c/d/e. Starting clean branch
`bug/265-entry-settings-navigation` was at
`4d0c0a9209210067b9ba2526c7528f65496bc593`, the integrated #264 implementation.
The audit coordinates at `6477188ee89034bb5d49f8f5b93086a1f73150d6` remain historical;
current callers and real HTTP output were inspected before editing.

| Item | Current key/caller | Region and exact target | Bounded change |
| --- | --- | --- | --- |
| R01a | `home.task.record_session.summary`, `rendering._home` | Session task card, `/sessions` | Record one Game or open a saved recording. |
| R01a | `entry.session`, `entry_rendering.render_entry_introduction_v1` via shell rendering | Session landing introduction | Same recording/opening meaning; the entry renderer itself needs no edit. |
| R01c | `profile_settings_rendering.render_local_settings_v1` | Paragraph between Time zone and Recommended defaults; `/sessions`, `/matches/new` | Remove only this two-link paragraph. |
| R01d | `rendering._about`, `navigation.settings` | Generic paragraph in `.about-grid`, `/settings` | Remove only this paragraph. |
| R01e | `about.advanced.heading` and `.description`, `rendering._about` | Existing `interfaces-heading` section | Development and automation; one sentence explaining script/tool access and ordinary-browser optionality. |

Both entry keys are entry-specific; active Session review uses separate captions.
There is no new helper panel or review shortcut. Existing recording titles/actions,
five Home cards, group/order/hrefs, recorded chooser and independent `/analyze` and
manual `/review` remain. Opening is explicit, not automatic last-source selection;
an ended recording is not promised resumable. #233's two paths remain knowledge-based.
Eligible recorded-own-decision review and its process-local Results/downloads remain.

The technical inventory is exactly four non-clickable `code` filenames, in order:
`README.md`, `docs/installed_cli.md`, `docs/public_python_api_v1.md`, and
`docs/unified_local_frontend_contract.md`. There are no technical hrefs, fragments,
command examples, launch buttons or visibility conditions at this HEAD. The existing
secondary section remains visible, and the separate storage-path disclosure remains
native. CLI and Public Python API contract-version-1 access is described accurately;
no HTTP endpoint, standalone-service launch or cloud/account feature is implied.

Header navigation, footer About and invalid-profile Settings remedies remain.
The reused creation-title and navigation keys retain their other callers. No form,
reset hierarchy, capture preference, route, profile codec, server, registry, CSS or
JavaScript change follows. See [Settings](settings_and_player_seat_setup.md) and
[independent installed evidence](unified_workflow_visual_contract.md#recording-entry-and-settingsabout-navigation-issue-265).
R01b remains completed by #255; R01f/g, R07f, R13g and automatic-Learning decisions
remain separate. #264 remains completed; exact merged-#265 `check` and
`v1-supported-platform-matrix` must pass before manual closure. #208 remains open,
UAT-01 unaccepted, UAT-02–12 paused, B-09/B-07 open and B-06 closed.

Issue #236 adds [direct saved-Match entry](learning_direct_match_entry.md) within an
active Learning collection. It supersedes the former requirement to open a Match
before transferring it: choose a saved Match, explicitly Add, explicitly Evaluate,
then View evaluation. Learning can initialize missing bounded Match discovery once on
explicit page entry and otherwise reuses it. Home remains passive. The shortcut
preserves unrelated active recordings, Reports, recovery and Session Results, and
retains #235's independent-copy/deletion semantics.

The #255 landing introduction explains that a collection holds chosen saved Match
versions for joint descriptive summaries. Name-only creation imports nothing;
ordinary single-decision review needs no collection. Partial input is allowed.
Opened collections explain Add, selected versions and evaluation at their controls,
without the former next-task box or adjacent-source jump. Meaningful result and
blocker links, anchors, forms and return destinations remain. Preparation creates
existing artifacts, not new Card analyses, a trained model or adapted recommendations.
Automatic Match inclusion, automatic incorporation of executed Reports and future
recommendation adaptation remain separate open R14 product questions. R13 return
routing/version/conflict ergonomics and R14 result/download organization remain open.

`APP_ROUTE_PATHS` retains eight prior static pages and adds the chooser. It is
separate from seven visible navigation entries, in order: Home, Match recording,
individual recording, recorded review, independent decision analysis, Learning,
Settings. `/review` and `/about` remain served without primary navigation entries.
These presentation counts are independent of the seven Engine Root workflows.

## Additive private transport

| Method and route | Meaning |
| --- | --- |
| `GET /review/recorded` | Refresh the bounded Session and Match chooser |
| `POST /review/open-recording` | Explicitly open or reuse one discovered recording |
| `GET /matches/review/{position}` | Review the active Match's selected Game, `1..36` |

The native GET Game selector submits only `position=1..36` to its current
`/matches/review/N` route. This exact query is immediately redirected with `303`
to the query-free canonical destination. All other queries remain rejected;
semantic language return paths remain query/fragment-free. Opening, report,
recording, correction, export, and analysis URLs retain their existing meanings.

The registered URL-encoded `recordings.open` form accepts exactly `family`
(`sessions` or `matches`), opaque `handle`, positive `generation`, and optional
existing `_frontend_form_instance` instrumentation. It accepts no path,
destination, Request, Product document, or execution setting. The registry now
has **58 POST routes and 98 definitions**, with a separate bounded `recordings`
feedback family. No tracking-only version is added.

Review-view Match analysis forms retain their existing operation definitions and
`POST /matches/api/v1/analysis`. A private `review_binding` authenticates the
exact active context key, content fingerprint, selected position, and position
generation. The adapter strips it before the unchanged Capture parser. It also
selects contextual review presentation for validation errors; it is not a client
return URL. Legacy forms without that field retain their original parser path.

## Discovery, explicit opening, and lifetime

Issue #235 adds a secondary delete action for available Session/Match choices.
Its [named permanent-file confirmation](managed_recording_deletion.md) is bound to
the exact discovered source, not its title. Preview/Cancel preserve genuine
Results, selected Game and recovery expiry; confirmed active deletion retires only
the owning context. The entire Match is selected, not one Game. Imported Learning
copies, exports and the profile remain. The private registry is now 62 POST
routes/106 definitions; the four deletion routes are separate from opening/review.

Issue #261 clarifies only these dedicated deletion captions and the shared
confirmation. A valid preview shows the captured name, compact Player/progress
facts, whole-recording scope/no app Undo, applicable active effects and retained
copies before unchecked consent. Its unrelated in-content shortcuts are removed;
global navigation, the separate exact Cancel return and non-actionable fallback
links remain. The chooser's German opening caption was already correct. List order,
availability, invalid-entry exclusions and source binding remain unchanged.
Current inventory remains 67 POST routes / 112 forms; see the
[confirmation map](managed_recording_deletion.md#confirmation-presentation-issue-261).

The chooser uses the existing direct-child, nonrecursive, strict discovery of at
most 2,048 candidates per family. Friendly profile labels and localized imported
fallbacks use the same managed-name projection. Duplicate titles remain separate
objects. Invalid and duplicate-semantic-identity files remain visible without an
open action, with local-storage resolution guidance. `available` means openable,
not analyzable. Partial recordings remain selectable. English summary strings
are not parsed into new facts.

No library-wide Request construction, hand reconstruction, decision preparation,
Historical materialization, or execution is added. Home does not scan the
library. Language-only chooser rendering reuses both discovery objects and their
generations. A genuinely superseded discovery yields contextual `409`.

`recorded_review_opening.py` resolves the exact generation and identity, snapshots
the active object, and uses the existing family's lifecycle gate. Before
publication it rechecks discovery and active identity. Inactive sources are
strict-loaded from the current valid file; discovery is not a historical-revision
snapshot. The exact active source instead retains its existing object, key,
generation, selected Game, #221 execution/download bytes, and valid #222
selection/preview/creation time. Existing strict loaders compare canonical
content fingerprints without replacing memory. A changed or unverifiable active
file gives contextual conflict and an existing explicit Reload form.

Switching to another recording of the same family discards the previous family's
derived Results/recovery state through its existing lifecycle. Separate active
families retain their original independence. Rejected selections leave the old
context intact. Product locks are never acquired while holding the app lock;
filesystem work holds no app lock. The Match lifecycle gate also serializes view
selection with review execution and source switching. No independent multi-tab
workspace or stronger cross-process transaction is claimed.

Navigation does not clear active-source feedback merely because a landing page
asks for category-level feedback. Actual source or Game changes still invalidate
the applicable state. No passive operation creates a Product, Player, profile
label, timestamp, Checkpoint, transfer, or prepared artifact, or rewrites Product
bytes. Explicit language preference saving retains its separate profile behavior.

## Session review and manual compatibility

### Independent analysis and manual review entry (Issue #303)

`GET /analyze` keeps its form directly available. A short **Enter a situation
yourself** heading and hand/visible-situation introduction identify manual input.
One native button-styled **Choose a decision from a recording** link outside the
form reaches `/review/recorded`. The mode legend asks what to assess in that
situation; `live_decision` and `post_game_review` retain their existing meanings.
The operative Home analysis description now says to enter a card situation yourself
and analyze one decision. The five tasks, order, destinations and navigation remain.

`GET /review` and the chooser's existing manual link use **Review a completed game
manually**. Its one introduction scopes full-deal/full-history input specifically
to the guided editor. The redundant choice heading and introductory import caption
are removed; the existing normal-completion scope and JSON-import guidance remain.
Historical and retrospective Position imports, editable process-local drafts,
repeat execution, retained Results and downloads remain supported.

Two secondary native links outside forms lead to the recorded chooser and to
`/sessions` (**Record a game and continue later**, introduced as the persistently
saved recording alternative). These links neither transfer nor save the manual
draft. The truthful process-local notice remains. Returning through `/review`
continues the accepted step or imported state without starting/resetting the editor.
Analyze and Review retain separate state; unsent browser input gains no persistence.

The existing chooser still opens only through `POST /review/open-recording` with
its exact family, opaque handle and generation. Discovery remains bounded;
openability is not decision eligibility. Same-source reuse, changed-source conflicts,
explicit Reload, selected Reports and canonical downloads keep their existing guards.
The correction adds no route, form, execution or Product write to passive entry.
Both locales use the existing CSS and language/error-focus mechanisms.

Current derived inventories are **9 static routes, 7 navigation entries, 5 Home
tasks, 73 POST routes, 125 form definitions and 2,118 matching catalog keys**.
The initial correction added four source-specific keys and retired two superseded
choice-copy keys; the installed-feedback follow-up adds one saved-name hint.
All route/form counts remain exact. Earlier inventories below are historical.

#### Installed-feedback follow-up

The maintainer accepted the other tested behavior at
`9e7cfb7240d6ae7abf295f9f842773b718882ba5` on
`bug/303-analysis-review-entry`. This bounded follow-up preserves those acceptances.
It addresses entry-action affordance, manual-entry placement and saved-name
convenience at manual editor step 1.

The two manual Review alternatives, the chooser's manual entry and its per-family
Session/Match entry links now share secondary button-link styling scoped to
`.entry-actions`. They inherit the existing wrapping, spacing, radius and 44px
minimum target height, with the established white secondary surface, dark text,
border, hover surface and visible native keyboard focus. The Analyze action retains
its green primary appearance. All remain native anchors with their original
captions/destinations, outside forms. The chooser's single manual-entry block now
follows the introductory explanation, above both recording lists; family ordering
and guarded recording-opening POSTs remain unchanged.

Manual editor step 1 offers saved display names through one native `datalist`
shared by its three existing editable text inputs. A short translated hint appears
only when names exist. The server projects only an immutable tuple of names from
the already loaded validated profile under the existing context lock. The generic
renderer still rejects a complete private profile on `/review`. Suggestions copy
text without allocating seats or binding profile Player identities. Empty labels,
new free text, duplicate-name validation, fixed Historical IDs and accepted draft
labels retain their existing behavior; a later profile rename only changes future
suggestions. See the [guided editor](unified_local_frontend_guided_analysis_and_results.md#historical-editor).

German startup remains an explicit **Deutsch** preference, persisted by the existing
language action and included when the UAT builder copies the profile. Saved English
still takes precedence over the browser language. The observed English startup alone
does not establish a lost-language regression, and this follow-up changes no locale
resolution or persistence policy.

##### Follow-up verification

The follow-up started from the clean branch/HEAD above and used CPython 3.13.7.
Evidence remains outside the repository under
`C:/Users/HENNIN~1/AppData/Local/Temp/opencode` (`$E` in these commands).

```powershell
$E = 'C:/Users/HENNIN~1/AppData/Local/Temp/opencode'
py -3.13 -m pytest tests/test_analysis_review_entry_paths.py tests/test_manual_review_saved_names.py -q --tb=short -o cache_dir="$E/303-followup-cache" --basetemp="$E/303-followup-red-tmp" --junitxml="$E/303-followup-red.xml"
py -3.13 -m pytest tests/test_analysis_review_entry_paths.py tests/test_manual_review_saved_names.py tests/test_recorded_review_navigation.py tests/test_frontend_localization_foundation.py -q --tb=short -o cache_dir="$E/303-followup-cache" --basetemp="$E/303-followup-focused-tmp" --junitxml="$E/303-followup-focused.xml"
```

Regression-first delivered HTTP produced **20 failed / 13 passed in 31.42s**:
19 failures demonstrated missing styling/suggestions; one test incorrectly expected
German for an invalid profile and was corrected to the unchanged English fallback.
The implementation then passed **85 tests in 57.33s**. A focused Ruff check found
four overlong new-test lines; wrapping them corrected that check.

The following **31 complete modules passed 779 tests in 156.18s, zero skips**:

```powershell
py -3.13 -m pytest -n 2 --dist=loadfile --max-worker-restart=0 `
  tests/test_analysis_review_entry_paths.py `
  tests/test_manual_review_saved_names.py `
  tests/test_recorded_review_navigation.py `
  tests/test_recording_entry_settings_navigation.py `
  tests/test_bilingual_home_information_architecture.py `
  tests/test_unified_workflow_visual_contract.py `
  tests/test_guided_frontend_web.py `
  tests/test_guided_frontend_json_transfer.py `
  tests/test_guided_frontend_execution.py `
  tests/test_frontend_validation_preservation.py `
  tests/test_frontend_language_switching.py `
  tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py `
  tests/test_task_first_language_preservation.py `
  tests/test_guided_frontend_packaging.py `
  tests/test_packaging_and_distribution.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py `
  tests/test_skatmind_rename.py `
  tests/test_completed_trick_input_grouping.py `
  tests/test_analysis_download_details.py `
  tests/test_learning_entry_purpose.py `
  tests/test_guided_position_form.py `
  tests/test_guided_historical_review_form.py `
  tests/test_unified_local_app_contracts.py `
  tests/test_unified_local_app_web.py `
  tests/test_frontend_profile_persistence.py `
  tests/test_profile_driven_form_contracts.py `
  tests/test_profile_driven_settings_web.py `
  tests/test_settings_seat_setup_web.py `
  tests/test_profile_driven_creation_packaging.py -q --tb=short --durations=15 `
  -o cache_dir="$E/303-followup-cache" --basetemp="$E/303-followup-complete-tmp" `
  --junitxml="$E/303-followup-complete.xml"
```

The inventory retains the initial #303 rendering/navigation, mode/editor/import,
Result/download, language/validation, package/localization and exact-inventory
callers. The new HTTP module and five profile/settings/packaging modules additionally
cover the locked display-name projection and unchanged profile boundary. The 85-test
pass repeats tests within the **779 distinct passing tests**. Both parallel workers
exited; no selected module belongs to the configured exclusive set. Strict inventories
were retained, with only the catalog count increased by the single new hint.

Browser commands used disposable source-tree fixtures only:

```powershell
# Preliminary native-picker diagnostics, separately retained for attempts 1 through 8.
py -3.13 "$E/303_native_picker_probe.py" "$E/303-followup-picker-8"
# Full presentation/navigation/free-text matrix with separately recorded picker attempts.
py -3.13 "$E/303_followup_browser.py" "$E/303-followup-browser-a"
```

The preliminary script evolved during diagnosis; each invocation used the same
command shape with the corresponding `303-followup-picker-N` output directory.
Attempts 1/2/3/5/8 did not commit a native suggestion: Enter reached the form.
Attempt 1 then failed its field lookup after that transition. Headed attempts
4/6/7 stopped at a foreground-ownership assertion before sending OS keys. Headless
and headed DevTools approaches, the arrow indicator, and a separate focused-page
emulation attempt did not establish picker selection. These are unsuccessful
verification attempts, not passing picker evidence or a proven Product defect.
Each diagnostic deliberately created three synthetic profile names; its 24 total
fixture updates are separate from the instrumented matrix below.

The matrix completed **8 German/English × JavaScript enabled/disabled × desktop/narrow
cells**, **128 actions** (48 pointer, 80 natural Tab/Enter), and **64 measurements**
in headless **Microsoft Edge 156.0.4314.50**. Each chooser contained 12 genuine saved
Sessions and one saved Match. Initial viewport screenshots and delivered HTML were
captured before verifier scrolling/focusing. Computed secondary surfaces, borders,
padding, wrapping, targets of at least 44px, the unchanged green primary action,
hover color and native focus passed. Manual entry appeared exactly once above both
lists. Free text, optional empty labels, duplicate-name rejection, corrected step-2
progression, accepted-state navigation and language/error return passed. File hashes
and modification times stayed unchanged during passive navigation and text entry.
Every matrix cell ended with a saved German preference.

**Native picker selection was verified in 0 of 8 cells.** The real Tab/character/
ArrowDown/Enter attempts typed only `Alex`, never the full suggested name. They
reached the existing form with that free text; the probe explicitly returned to
step 1 and tested free-text entry separately. No DOM assignment, fill operation or
free-text success is counted as suggestion-picker coverage. Actual native pointer
selection and keyboard suggestion selection, particularly without JavaScript,
remain required in the bounded installed follow-up.

The measured CSS viewports were **1365 x 900** and **390 x 844**, fresh-profile
default 100% zoom, DPR 1 and visual viewport scale 1. Viewport emulation is not
enlarged browser zoom; enlarged zoom was not tested. Representative screenshots
were inspected and no document horizontal overflow was detected. See
`303-followup-browser-a/evidence.json`, `summary.json`, delivered HTML and PNGs.

| Instrumented phase | Observed operations/writes across eight cells |
| --- | --- |
| Explicit fixtures | 96 Session saves, 8 Match saves, 32 profile saves (24 name additions and 8 initial language preferences) |
| Passive navigation, 80 actions | 80 bounded discovery calls; zero Product/profile writes, execution or Learning preparation |
| Native picker attempts, separately recorded | Eight existing label POSTs with the typed prefix; process-local only; zero persistent writes |
| Manual setup, 24 actions | Eight starts, eight explicit Back actions after picker attempts, eight accepted free-text steps; process-local only |
| Duplicate-name validation, 8 actions | Eight rejected label POSTs; zero persistent writes or execution |
| Explicit language selection, 16 actions | 12 profile saves and four unchanged-language actions; zero Product writes |

The final explicit Quick and diff-check results/log paths are recorded in the handoff.
Local Full is excluded by the approved task-specific routine. The earlier functional
acceptances remain; #303 stays open for new exact-commit branch/main `check` and
`v1-supported-platform-matrix` plus the bounded installed follow-up, including the
unverified native picker paths. #208 stays open; UAT-01 is not globally accepted,
UAT-02–12 remain paused, and full maintainer UAT plus current architecture/code
analysis with treatment of material findings remain required before v1.0.0.
Release preparation is not authorized.

#### Scoped developer verification

The following is the initial #303 implementation evidence, before the installed-
feedback follow-up above.

The clean starting branch was `bug/303-analysis-review-entry`, HEAD
`1c6381a7f2678ac7e562ced6f25950c97fb0f9ce`. Source-tree checks used CPython
3.13.7. Evidence is outside the repository at
`C:/Users/HENNIN~1/AppData/Local/Temp/opencode` (abbreviated `$E` below).

The new delivered-HTTP module first ran before Product edits. Its first run had
14 failures in 16.32s, including test-authoring assumptions about the Request
wrapper, existing Result-before-summary placement and the Learning preparation
patch target. Those assumptions were corrected against the actual contracts.
The second pre-implementation run had 14 expected failures in 15.30s for the
missing entry copy/links. No Product guard was relaxed to make a test pass.

```powershell
$E = 'C:/Users/HENNIN~1/AppData/Local/Temp/opencode'
# First and corrected pre-implementation runs; use red, then red2 for $run.
$run = 'red'
py -3.13 -m pytest tests/test_analysis_review_entry_paths.py -q `
  -o cache_dir="$E/303-pytest-cache" --basetemp="$E/303-$run-tmp" `
  --junitxml="$E/303-$run.xml"
# The red2 command additionally used --tb=short.

py -3.13 -m pytest tests/test_analysis_review_entry_paths.py `
  tests/test_recorded_review_navigation.py tests/test_bilingual_home_information_architecture.py `
  tests/test_frontend_localization_foundation.py -q --tb=short `
  -o cache_dir="$E/303-pytest-cache" --basetemp="$E/303-focused-tmp" `
  --junitxml="$E/303-focused.xml"
```

That four-module pass was **80 passed in 41.27s**. The complete caller-derived
inventory below then passed **705 tests in 143.11s**, with **zero skips**:

```powershell
py -3.13 -m pytest -n 2 --dist=loadfile --max-worker-restart=0 `
  tests/test_analysis_review_entry_paths.py `
  tests/test_recorded_review_navigation.py `
  tests/test_recording_entry_settings_navigation.py `
  tests/test_bilingual_home_information_architecture.py `
  tests/test_unified_workflow_visual_contract.py `
  tests/test_guided_frontend_web.py `
  tests/test_guided_frontend_json_transfer.py `
  tests/test_guided_frontend_execution.py `
  tests/test_frontend_validation_preservation.py `
  tests/test_frontend_language_switching.py `
  tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py `
  tests/test_task_first_language_preservation.py `
  tests/test_guided_frontend_packaging.py `
  tests/test_packaging_and_distribution.py `
  tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py `
  tests/test_skatmind_rename.py `
  tests/test_completed_trick_input_grouping.py `
  tests/test_analysis_download_details.py `
  tests/test_learning_entry_purpose.py `
  tests/test_guided_position_form.py `
  tests/test_guided_historical_review_form.py `
  tests/test_unified_local_app_contracts.py `
  tests/test_unified_local_app_web.py -q --tb=short --durations=15 `
  -o cache_dir="$E/303-pytest-cache" --basetemp="$E/303-complete-tmp" `
  --junitxml="$E/303-complete.xml"
```

The 25 modules cover the changed shared entry/guided renderers, operative Home
copy, exact routes/forms/catalogs, localization/package resources, strict rename
inventory, normal mode/editor/import execution, retained Results/downloads,
guarded Session/Match opening and source conflicts, and native/enhanced language
and validation paths. Direct shared-renderer callers additionally include completed
Trick controls, retained analysis downloads and Learning entry presentation.
None is a configured exclusive module. Both parallel workers exited normally.
The strict rename inventory passed without an inventory edit.

A focused Ruff check found four overlong lines in the new test module only.
Line wrapping corrected them, followed by the complete module rerun:

```powershell
py -3.13 -m pytest tests/test_analysis_review_entry_paths.py -q --tb=short `
  -o cache_dir="$E/303-pytest-cache" --basetemp="$E/303-final-entry-tmp" `
  --junitxml="$E/303-final-entry.xml"
```

It passed **14 tests in 17.48s**, zero skips. These focused passes repeat tests
within the 705 distinct passing tests; they do not increase distinct coverage.
After the evidence documentation update, the complete strict inventory module
also passed again: **8 tests in 2.55s**, zero skips:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py -q --tb=short `
  -o cache_dir="$E/303-pytest-cache" --basetemp="$E/303-final-inventory-tmp" `
  --junitxml="$E/303-final-inventory.xml"
```

The final explicit Quick and diff checks are reported with their actual external
log paths in the handoff. The approved task-specific routine does not run local Full:

```powershell
function python { py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
```

The disposable probe command was:

```powershell
py -3.13 "$E/303_probe.py" "$E/303-browser-a"
```

An initial probe import failed before browser/fixture creation because its external
script lacked the repository-root import path. After correcting only that disposable
script, all **8 cells, 172 actions and 48 measurements** passed. The probe used
headless **Microsoft Edge 156.0.4314.50**, German/English, application JavaScript
enabled/disabled, and emulated CSS viewports **1365 x 900** and **390 x 844**.
Fresh profiles retained default 100% zoom, measured DPR 1 and visual viewport
scale 1. No enlarged browser zoom was exercised; viewport emulation is not zoom.
Entry labels and controls fit without document horizontal overflow. Representative
screenshots and unscaled top crops were inspected.

There were **104 pointer** and **68 natural Tab/Enter** actions; programmatic focus
was not used. Actual delivered HTML, request paths, exact open-form fields, visible
focus and next Tab are retained in `303-browser-a/evidence.json` and `summary.json`.
All cells exercised the independent link, explicit genuine Session and Match opening,
manual entry and its recording alternative, accepted step-2 or imported Position
return, both language directions, a real retained Analyze Result, and rejected empty
hand feedback. Error autofocus and next Tab to its hand link were observed; language
return kept the existing script-mode-specific focus behavior and rejected values.
Canonical Analyze downloads remained byte-identical.

| Separate phase | Observed operations/writes across eight cells |
| --- | --- |
| Deliberate disposable fixture creation | 64 Session saves, 8 Match saves, 8 profile saves; 32 discovery calls |
| Passive navigation, 96 measured actions | 104 bounded discovery calls; zero execution, Learning preparation or persistent writes; file hashes and modification times unchanged |
| Explicit recording opening, 16 actions | 16 guarded open POSTs and 16 source loads; zero execution or writes |
| Manual setup, 12 actions | Four explicit starts plus four accepted Player steps; four native multipart Position imports; process-local only |
| Explicit synthetic Analyze setup | 8 actual executions, separately counted; zero Product saves |
| Rejected native Analyze submission, 8 actions | 8 validation POSTs; zero execution or writes |
| Explicit language selection, 40 actions | 40 profile saves; zero Product saves or execution |

This is source-tree developer evidence. **Locally validated; new exact-commit
hosted CI and installed targeted acceptance pending.** Keep #303 open for branch
and main `check` / `v1-supported-platform-matrix` and installed targeted entry-path
acceptance. Keep #208 open: UAT-01 is not globally accepted, UAT-02–12 remain paused.
Full maintainer UAT and current architecture/code analysis with treatment of material
findings remain required before v1.0.0; Release preparation is not authorized.

Session opening returns to `/sessions/current#recorded-decisions`. The existing
#221 list, observation/selection/exporter, frozen information, explicit executor,
source labels, and downloads are reused directly. An eligible saved own decision
remains accessible after 30 Plays without promotion, another Game End, or full
Historical readiness. Missing snapshots are explained and never backfilled.
This does not promise full three-Player coverage.

Issue #244 quiets the zero-observation destination without removing it. The ordinary
top invitation appears only after an observed local Play; missing snapshots offer
inspection and diagnostics rather than an enabled review. One source-consistent
projection supplies invitation and rows. Expired/rejected selections still reach
visible feedback at `recorded-review-feedback`, even when no row is now eligible.

The separate `/review` wizard still accepts unrecorded Games and supported strict
JSON imports. Its draft, current step, imported Request, Result, downloads, and
explicit reset are unchanged. Visiting Home, the chooser, or a recorded source
does not copy into or reset the manual workflow. The explicit manual link resumes
its existing state.

## Selected-Game Match review and Reports

Issue #238 uses Game/Spiel numbering consistently in ordinary recording tiles,
the existing review selector and Report links. Its
[selected-Game-first recording view](match_game_navigation.md) leads with identity,
seats and controls before the full overview, and normal tile/create/continuation
destinations include `#match-recording`. Technical position semantics and the
review routes, selector query, exact Report attribution and backlinks below remain.
Retained Match errors take priority over a normal language-return fragment, while
valid recovery previews keep their existing target and lifetime.

The focused page is an alternate view of the same Workspace. A new context keeps
its existing initial position; reuse keeps the current selection. The native
selector shows all 36 positions in canonical order with existing state labels.
Actual position changes call `select_unified_match_position_v1`, invalidating
recovery normally; same-Game view changes do not. Empty/passed states contain no
Game-creation action and link to the same position's recording controls.

Only the selected Game uses `_decision_preparation_summary`. Prepared choices
show Trick, named Player, and actual Card; skipped rows use its exact two reason
values. Normal review has one decision choice and one explicit action. Method,
seed, sample, budget, and profile settings remain under Advanced with unchanged
defaults. Full Historical review and materialization remain separately explained
secondary actions, never prerequisites for eligible individual decisions.

Issue #244 omits the recording-page review invitation at zero Plays, including
empty, started-zero-Play and passed Games. Direct review remains supported with a
named status and same-Game recording link. With Plays but zero prepared decisions,
the link offers **Inspect recorded decisions and missing evidence**; existing skip
reasons explain what is unavailable. Explicit hand evidence may prepare one decision
without all three hands or full completion. The already captured selected-Game
preparation summary determines the label; no extra preparation/materialization runs.
Report display remains independent of another selected Game's counts or matching
decision index. The Match-side transfer shortcut is secondary, with relevant
feedback exposing its native controls; Learning's own page is unchanged.

Issue #246 adds the selected Game's normal read-only chronology independently of
this preparation summary. Every accepted Card/actor/local position is visible,
including when all decisions are skipped. One separate Game score reads the
existing declarer/combined-defender prefix, with recorded-Trick facts instead of
points for Null. Warning links reach visible history rows; correction links reach
the exact recording target without issuing recovery selections. A retained Report
still owns its original Game/decision and historical context. See
[Recorded Trick progress](recorded_trick_progress.md).

`match_review_rendering.py` owns this presentation; `match_report_rendering.py`
renders retained validated report projections. Existing
`execute_unified_match_analysis_v1` and the maximum-eight revision-scoped Report
store remain authoritative. `/matches/reports/{report_id}` presents the Report's
actual Game and decision openly, with exact downloads and same-Game recording and
review links. Refresh/download never executes. Missing Reports stay contextual;
changed files invalidate derived Reports and offer explicit Reload. Bounded,
unavailable, and failure outcomes remain truthful. No analysis batch, fabricated
hand/Card, inferred timestamp, or relaxed knowledge rule is introduced.

## Destination wording (Issue #254)

Existing links now name their destination in both catalogs; execution controls keep
their action wording. The table describes existing controls, not additional links.

| Control / owner | English wording | Unchanged href |
| --- | --- | --- |
| Session Result / retained review Checkpoint | Decision selection: Trick T, Card P | `#recorded-decision-N` |
| Session invitation / whole eligible chooser | Recorded decision selection | `#recorded-decisions` |
| Match review / selected Game | Recording: Game N | `/matches/position/N#match-recording` |
| Match recording / selected Game with prepared decisions | Decision selection: Game N | `/matches/review/N` |
| Decision Report list / each captured Report summary | Open existing analysis: Game N — Trick T, Card P | `/matches/reports/{report_id}` |
| Review chooser return | Choose another recording | `/review/recorded` |

The chooser return and missing-evidence inspection wording were already accurate.
Zero-Play invitations remain suppressed; direct empty/passed/completed review names
the recording destination without implying that play can continue. A Report lacking
a decision sub-location uses its Game-only caption. Other Report kinds retain their
labels. No filename, input reference, current profile or another Game's preparation
rows supplies Report ownership. The existing Report route selects that Report's Game.

The original relative fragments, availability, form actions, focus targets, next Tab,
error priority and language-source restoration are preserved. Same-source navigation
retains valid Results/previews; real selection changes retain their existing
process-local selection/invalidation. Clearer labels add no per-tab snapshot, new
Return route, save, replay, preparation or execution. Existing page preparation and
explicit language preference saves remain. #245 receipt delivery is unchanged.
See [scoped evidence](unified_workflow_visual_contract.md#review-return-labels-issue-254).

## Language, security, and compatibility

The #223 semantic source capture includes chooser discoveries, active review
Game, and selected Report/error origins. Known focus targets add
`recorded-review-chooser` and `match-review`. Safe analysis options can survive
submitted errors and language changes; optional unsent-input preservation still
requires JavaScript. Hidden transport is regenerated, and destructive
confirmation remains excluded. The catalogs have **1,414 matching keys**.

App-owned CSS retains visible focus, native keyboard/no-script controls, long
names, 320-pixel reflow, and enlarged text. The footer About link has explicit
light text on its dark surface. Shrinkable grid tracks repair measured Home,
chooser, and legacy manual-entry overflow. The Report table remains the existing
labelled keyboard-scroll region. No overflow is hidden or font shrunk to fake
compactness; long Match titles use an ordinary responsive heading size.

Loopback/cookie/Host/Origin protection, CSP, no CORS, local-only resources,
request/discovery bounds, private downloads, standalone interfaces, #221 Results,
#222 correction, #225 seats, #226 save/Command counts, #227 progress, and #228
declaration semantics remain in force. Package `0.17.0`, Python `>=3.13`, license,
dependencies, Public APIs, persistence, 71 Schemas/resources, seven Root workflows,
six Session examples, and 98 generated outputs are unchanged.

## Installed-browser procedure and evidence

Focused verification includes real returned-form Session/Match execution,
same-context Result/recovery retention, explicit source/Game invalidation, partial
coverage, manual draft/import/Result retention, strict reopen, discovery bounds,
duplicates/invalid files, concurrent opens, file-change races, contextual language
errors and route/security guards. The 21-module regression run
passed **408 tests, with 1 existing skip**, in **326.42 seconds**. A focused
navigation/language follow-up passed **66 tests in 57.99 seconds**, including
retained missing-Report diagnostics through language return and file-conflict
feedback when opening a Report from another selected Game.
The seven reviewed README legacy-name inventory occurrences moved by five lines;
only their offsets were synchronized, retaining their exact hashes/classifications.
Final complete-check outcome is recorded in the implementation report.

The first complete Python 3.13 check passed all build/schema stages, then reported
8,694 passed, 1 skipped and 1 failed in 2,496.19 seconds. Its architecture guard
had not yet classified the new dedicated opener as a public Session API adapter.
The explicit adapter allowlist now includes only that additional module; forbidden
core/CLI imports and all other layer checks remain enforced. A complete corrected-
tree rerun is required; the unsuccessful attempt is not counted as success.

The optional dependency-free `scripts/verify_home_recorded_review.py` uses the
existing local DevTools transport and a separately installed Wheel. Synthetic
recordings are prepared through existing legal services/real forms; Results are
never inserted. Run from the checkout with the installed environment's Python:

```powershell
python scripts/verify_home_recorded_review.py `
    --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
    --output "$env:TEMP\opencode\navigation-after" --phase after `
    --baseline "$env:TEMP\opencode\navigation-before\evidence.json"
```

The `before` phase must run against the real pre-change build. No application
rewrite or branch switch emulates a baseline. Output must be a fresh scratch
directory under an existing parent. Source/resource hashes are checked against
the installed Package; canonical downloads are checked against retained bytes.

September 14 evidence uses CPython **3.13.7**, Microsoft Edge
**153.0.4234.32**, widths **1365, 390, 320**, and representative **200% text** in
both languages and script modes. Baseline: `115c9b8299c93c711a928b8feb2c8f02c919582a`.
There are **80 baseline and 272 final measurements**:

* `$env:TEMP/opencode/229-navigation-before/evidence.json`;
* `$env:TEMP/opencode/229-navigation-after-11/evidence.json`, full-page and
  `*-viewport.png` screenshots;
* final browser Wheel SHA-256:
  `4dd9ed735624309f67decb7bb4d0343d02346cca097b247cc52f1b26694afd48`;
* served `app.css` SHA-256:
  `cab37ae125f7117f66643b65b7006c28a93987e65be7de756048c469751a3ca9`;
* unchanged served `workflow.js` SHA-256:
  `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298`.

The evidence retains module/catalog hashes, source IDs, Report IDs, request paths,
focus, headings, orientation counts, action geometry, and download hashes.
Native Home actions reached a real #221 Session Result after 30 Plays, then the
same context/bytes through Home; Match opening retained initial Game 1, selected
passed Game 2 and partial recorded Game 3, and analyzed decision 1 in
`match-160` / `observed-game-3`. Each source open made one open POST and zero
executions. Each explicit review made one existing analysis POST and one real
execution, with no refresh/download retry. Both modes retained Product bytes.
Unsent seed `27` survived only with JavaScript; native mode correctly retained
the server default `0`. Both modes retained submitted invalid options through
translated errors. A genuine competing discovery refresh produced a chooser
conflict; missing snapshots and duplicate names were also inspected.

Matched German native measurements (CSS pixels, full document coordinates):

| State / width | Height before → after | First action top before → after |
| --- | --- | --- |
| Home / 1365 | 3197 → 1359 | 1486 → 636 |
| Home / 320 | 5928 → 2238 | 2509 → 727 |
| Session entry / 1365 | 3391 → 2916 | 2990 → 2515 |
| Match entry / 1365 | 1637 → 1162 | 1232 → 758 |
| Learning entry / 1365 | 1867 → 1164 | 1533 → 829 |
| Manual entry / 1365 | 1683 → 1233 | 1211 → 761 |

Home has 12 → 8 visible headings and 1 → 0 orientation blocks. Session/Match
entries have 6 → 4 headings and 2 → 0 blocks; Learning has 7 → 4 headings.
Final document/client widths agree at 1350, 375, and 305 pixels, including measured
200%-text states. Screenshots were inspected for Home, chooser/errors, source
labels, open Reports, and native Session Results. These metrics do not establish
universal compactness or replace interactive acceptance.

Earlier `after-1` through `after-6` runs retain unsuccessful layout/tooling probes;
`after-7` passed 224 measurements before the footer/title refinement; `after-8`
passed 256, and `after-9`/`after-10` added missing-Report language coverage.
`after-11` is the final browser source/resource authority after preserving file-
conflict feedback across a real selected-Game change.
No missing actual-browser
acceptance item is being substituted by HTML tests. Full maintainer UAT was not
performed. Exact merged-commit `check` and `v1-supported-platform-matrix` remain
required before #229 closure. #208 and unresolved findings remain open; UAT-01
failed, UAT-02–12 are paused, B-09/B-07 are open, B-06 is closed, and v1 release
preparation remains unready.
