# Match Game navigation and recording focus

## Opened Match navigation (Issue #333)

The local work-area navigation names the opened Match and the game. Its
underlined, bold area is current; the other area is a native link. On an
individual result or original, the play number identifies the decision.

* **Record & Live help** contains card entry, explicit Live controls, corrections,
  Undo and the 36-game selector. After a completed game the next unfinished
  game is still offered near the top. Switching games uses the normal selection
  and Live retirement path.
* **Review** offers the whole-Match review and the selected game's independent
  decision selector. Choose a game, apply a recorded decision, then explicitly
  analyze it. Empty and passed games still offer the series workflow. Historical
  analysis, materialization and reports are available here. Recording no longer
  embeds a second analysis/report panel, a readiness-dependent decision link,
  or another whole-Match or archive button.
* From a whole-Match comparison, open **Original analysis**. Its comparison
  return lands on the originating game; its recording link opens the same
  game. Changing language on the returned comparison keeps that section.
  On that overview, the **Record & Live help** link, the originating game's
  recording link and its individual decision selector all check the original
  source before opening the game.
  An expired return explains the conflict and offers independent archive access.
  Original downloads continue to address the retained execution. From an
  individual decision or its result, **Record & Live help** also returns to
  that game's recording.

### Small import and later installed orientation check

The source-only verifier creates `synthetic-hearts.json` in its fresh output
directory, separately from its disposable managed copy. Game 1 is passed.
Game 2 has 18 recorded plays, six by Alex: five statistical decisions and one
forced card. Generate the fixture and exercise the native source workflow with
development Python, the checkout and a local Chromium browser:

```powershell
& $py scripts/verify_opened_match_navigation.py --output "$E/browser" --browser $edge
```

After published-source review, maintainer integration and successful automatic
exact-commit main `check` and `v1-supported-platform-matrix`, use that small
import in a disposable installed home:

1. Open **Synthetic Hearts review** from the normal Match list. Find game 2,
   recording, Live help and corrections. Can you tell which area is active?
2. Without running a series job, find and analyze Alex's first decision
   (play 3, Clubs Seven). Use Quick and played-game goal. Return to recording.
3. Find the series review. Explicitly start it with the same settings. Open
   game 2's comparisons and a real original. Return to the comparison section
   and to game 2's recording using the on-page links. Switch language and refresh.
4. Judge whether the Match, game, current task and next action are clear in both
   areas. Check visible comparison values and keyboard navigation at desktop
   and narrow widths. No personal recording or volume benchmark is needed.

Issue #332 already passed installed acceptance. Earlier placements and
verification records below describe their respective baselines.

### Returned overview: published-source correction (#333)

At `aedc81051d0d3574b92e72c16ece8be3b1b1dfa6`, an original from Match A
correctly returned to A's overview, but its two header links addressed the
active Match. Authenticated HTTP tests read the links from the delivered HTML,
opened Match B through the normal list, and followed each old link. The
section-level recording link returned 409 and left B on game 1. The header
recording link and the individual-review link each returned 200 **and selected
game 2 of B**. The saved recordings were not rewritten.

The header and section now emit the same signed recording destination. The
individual selector uses the same signed row with one additional fixed suffix,
`/review`. Both handoffs validate the recording, file, review run and row
before the normal game-selection path can clear feedback or retire Live. They
check the origin again before delivering the page. Refreshing the signed URL
rechecks it. After a successful handoff the ordinary game page owns decision
forms and DE/EN changes, with its existing source-bound language return. The
handoff URL itself is not a language return target. An independently opened
individual review still needs no series job.

**Development verification.** The red run on the published product had three
failures in 152.32 s: two `(200, game 2)` results instead of `(409, game 1)`,
and different recording destinations in the header and section. No harness
correction was needed to reproduce them. The expanded green run passed six
tests in 269.94 s. The complete eight-module selection on the final product
passed **231 tests in 727.06 s**, including both delayed control redirects.
The six green cases are included in that total.

Each new case starts with one genuine retained result from the short synthetic
Hearts recording. With a valid origin, refresh and both language changes
preserve the game and the native chooser can apply the recorded decision.
After a foreign open, both old handoffs return 409 without changing the
selected game, selection generation, Live control revision or retained form
error. Resuming the job or replacing the recording with identical bytes also
invalidates old links. Replacement during final review delivery suppresses the
stale page. Historical Request and Result downloads remain byte-identical;
navigation does not invoke the evaluator or save a recording.

Commands below use development Windows CPython 3.13.7, a 7,200,000 ms
invocation timeout, and external temporary data, logs, JUnit and Ruff cache.
Run `red` before the product fix, `green` after it:

```powershell
$E = "$env:TEMP/opencode/333-origin-fix"
New-Item -ItemType Directory -Force $E | Out-Null
$py = "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUFF_CACHE_DIR = "$E/ruff"
$flags = @('-q','-p','no:cacheprovider','-n','2','--dist=loadfile','--max-worker-restart=0')
function outputs($name) {
    @("--basetemp=$E/$name", "--junitxml=$E/$name.xml", "--log-file=$E/$name.log", '--tb=short')
}
$o = outputs red
& $py -m pytest tests/test_whole_match_web.py -k returned_overview @flags @o
$o = outputs green
& $py -m pytest tests/test_whole_match_web.py -k returned_overview @flags @o
$M = ('whole_match_web frontend_language_switching language_switch_context learning_prepared_navigation ' +
      'recorded_review_navigation match_decision_selection_web match_game_navigation_web saved_match_rollouts_web'
     ) -split ' ' | ForEach-Object { "tests/test_$_.py" }
$o = outputs affected
& $py -m pytest @M @flags @o
$o = outputs guards
& $py -m pytest tests/test_skatmind_rename.py tests/test_cli_internal_architecture.py @flags @o
function python { & "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe" @args }
.\scripts\check.ps1 -Mode Quick -LogDirectory "$E/quick"
git diff --check
git diff --cached --check
git ls-files --others --exclude-standard | ForEach-Object { git diff --no-index --check -- NUL $_ }
```

No layout, analysis-form placement or worker implementation changed. The
existing screenshot evidence and the narrow installed orientation check above
still apply; this correction is not installed acceptance.

### Source verification (#333)

The native browser probe opens the Match from its normal list, follows the
emitted game and area links and applies play 3. The explicit individual action
makes one real Application/evaluator call, with no series checkpoint. The
explicit Quick series reuses that original and evaluates four more decisions.
Play 17 is forced. Played Clubs Seven has 21/25 (84%) versus Clubs King at
22/25 (88%); play 15 ties on 25/25 with deciding totals of 1284/25 and 1386/25.
Refresh, language changes, original downloads and the contextual returns
leave the counts at five, the recording bytes/mtime and archive manifest
unchanged, and both downloaded originals byte-identical.

Development evidence used CPython 3.13.7 and Edge 158.0.4370.33 with page
JavaScript disabled. At 1280 × 900 the six comparison columns fit. At
390 × 900 the original navigation wraps normally and the comparison uses its
existing keyboard-focusable horizontal scroll region. The recording-to-review
link has a visible 3px keyboard focus outline. These are CSS viewport sizes,
not enlarged browser zoom. The disposable Workspace SHA-256 is
`281e74f92cbd29b95e39379ab6d4d407bcd0a87e603714f1f73ff798fae8aa56`.

#### Local command and module receipt

PowerShell from the source checkout; invocation timeout 7,200,000 ms. The
following gives the actual selections and arguments, with repeated flags factored
out. Use fresh output names to reproduce. Logs, pytest temporary roots, browser
profiles, import and JUnit reports are outside the repository.

```powershell
$E = "$env:TEMP/opencode/333-nav"
$py = "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe"
$edge = "${env:ProgramFiles(x86)}/Microsoft/Edge/Application/msedge.exe"
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RUFF_CACHE_DIR = "$E/ruff"
$flags = @('-q','-p','no:cacheprovider','-n','2','--dist=loadfile','--max-worker-restart=0')
function outputs($name) { @("--basetemp=$E/$name", "--junitxml=$E/$name.xml", '--tb=short') }
function modules($names) { $names.Split(' ',[StringSplitOptions]::RemoveEmptyEntries) |
    ForEach-Object { "tests/test_$_.py" } }
$o = outputs origin
& $py -m pytest tests/test_whole_match_web.py -k native_controls @flags @o
$a = modules ('match_game_navigation match_game_navigation_web match_completion_navigation_web ' +
    'task_first_match_and_learning_workflow task_first_stateful_rendering recorded_review_navigation ' +
    'whole_match_web match_rollout_web saved_match_rollouts_web saved_match_analyses_web ' +
    'match_live_advice match_decision_selection_web review_return_labels recording_task_focus ' +
    'unified_workflow_visual_contract compact_card_entry_web learning_direct_entry ' +
    'learning_direct_entry_web recording_deletion_lifecycle match_evidence_navigation ' +
    'match_evidence_workflow direct_match_evidence match_learning_report_discoverability ' +
    'frontend_language_switching language_switch_context language_view_continuity ' +
    'operation_feedback_language task_first_language_preservation frontend_validation_preservation ' +
    'frontend_localization_foundation complete_frontend_localization frontend_profile_persistence ' +
    'recorded_decision_context_web packaging_and_distribution')
$o = outputs affected
& $py -m pytest @a @flags @o *> "$E/affected.log"
$b = modules ('whole_match_web frontend_language_switching frontend_localization_foundation ' +
    'match_live_advice recording_deletion_lifecycle learning_report_attachment_web ' +
    'learning_report_rejection match_learning_report_discoverability saved_match_analyses_web ' +
    'saved_match_rollouts_web match_game_navigation_web match_completion_navigation_web ' +
    'task_first_match_and_learning_workflow review_return_labels match_decision_selection_web ' +
    'language_switch_context learning_prepared_navigation guided_frontend_packaging ' +
    'unified_local_app_web analysis_controls_web forced_card_guidance')
$o = outputs final
& $py -m pytest @b @flags @o *> "$E/final.log"
# After parallel workers exited:
$o = outputs exclusive
& $py -m pytest tests/test_match_analysis_action_placement.py -q -p no:cacheprovider @o
$o = outputs guards
& $py -m pytest tests/test_cli_internal_architecture.py tests/test_skatmind_rename.py @flags @o
# All three browser runs used fresh disposable data, overlapping focused pytest.
foreach ($name in 'browser','browser-final','browser-section') {
    & $py scripts/verify_opened_match_navigation.py --output "$E/$name" --browser $edge
}
function python { & "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe" @args }
.\scripts\check.ps1 -Mode Quick -LogDirectory "$E/quick"
git diff --check
git diff --cached --check
git ls-files --others --exclude-standard | ForEach-Object { git diff --no-index --check -- NUL $_ }
```

The initial HTTP check passed (1 test). The first 34-module selection had
683 passes, one Windows symlink skip and eight failures. Seven cases shared
one fixture that still submitted the removed recording form. It now obtains
the form from Review. The deletion race also needed to exercise its original
direct submission: the focused Review form holds the lifecycle gate, whereas
the legacy direct submission can overlap deletion. The test uses the same
decision proofs and explicitly omits only the optional Review binding. No
lock or worker behavior was changed. The 21-module correction/consumer run
passed 417 tests, including both delayed Cancel/Resume redirect cases. The
exclusive action-placement module passed all 25 tests. Repeated selections
and repeated synthetic browser computations are not additional distinct cases.
The last screenshot covers the targeted comparison's Match and area caption.

Issue #238 puts the selected Game and its actual recording action before the
36-entry overview. It supersedes #220's progress → suggestion → full grid → task
ordering and normal **Position** numbering. Technical `match_position`, canonical
rotation, `/position/` routes, standalone presentation and analysis Position
terminology retain their meanings. This addresses the reported numbering,
selection-destination and recording-hierarchy observations; it does not reproduce
the original maintainer trace or constitute UAT acceptance.

## Accepted state, selection and destinations

Compact progress labels distinguish started Games, complete play traces and passed
deals. `#match-recording` is a labelled, focusable section containing **Game N of
36**, accepted recording coverage, and escaped full Forehand/Middlehand/Rearhand names from the
accepted selected position view. Existing Start/Pass, declaration or Card controls
follow. Compact captured totals, current Trick, accepted declaration, #234's
separately sourced unplayed pair and the full accepted/correction history retain
their existing evidence boundaries. Full history remains after the primary action.

The single native `#match-games` section follows recording. It contains all 36
tiles in twelve canonical rounds, retaining statuses, selected `aria-current`,
text markers and exact seats. Nearby overview/selected-Game links work without
JavaScript. Optional evidence, metadata including #232's fixed format, Statistics,
transfer, analysis and specialist correction remain accessible.

Issue #244 consolidates the selected Game's normal task: one Start/declaration/
named-next-Player heading leads to its existing controls, with short selection/Trick
context. The separate instruction paragraph and completed-step bookkeeping list
are removed; accepted declaration, evidence, warnings and history remain. Passed
and play-complete status use their actual existing projection; a missing declaration
or rejected Play is not completion. The normal review link is omitted at zero Plays,
offers truthful inspection at nonzero/zero-prepared coverage, and retains review at
prepared decisions. Direct empty/passed review and exact retained Report routes
remain supported. The existing Learning-transfer forms are in a secondary native
disclosure after recording/overview, opened for relevant feedback. The first-unfinished
rule, selected-Game-first ordering, all 36 tiles, rotation and Mark as passed remain.

The existing `view.next_position` is unchanged: first canonical entry whose view
is not `passed_deal`, `play_complete` or `rule_ended`. If it equals the selection,
there is no redundant continuation CTA. The destination can point backward.
Passing or recording the final Card keeps the selected Game; continuation is explicit.
If there is no suggestion, the message states only that all 36 entries are passed,
rule-ended, or contain complete traces. All-started/zero-Play input still suggests
Game 1 even though Product occupancy status is `complete`.

Issue #298 places terminal selected-Game navigation immediately after the accepted
recording status, before seats, declaration/evidence editors, totals and history.
**First Game with incomplete recording** gives context to the concise **Open Game N**
native GET link. It uses the shared `.button-link` treatment and `.content-stack`
spacing, with overview and readiness-dependent decision-selection/inspection links
as secondary actions. There is one group, without a duplicate below history. When
all entries are terminal, the existing truthful all-complete message and secondary
navigation occupy this upper area, without a continuation target. The complete
36-entry overview remains below recording.

For an unfinished selected Game, existing Start/declaration/Card actions retain
priority and the unchanged **Open Game N for recording** link stays after history.
Unavailable capture or missing declaration does not establish terminal completion.
Passed and rule-ended Null states keep their distinct status and explanation.

Tiles and continuation links use `/matches/position/N#match-recording`. Normal
creation returns to Game 1 with that fragment after exactly one create and no
Start mutation. `/matches/current`, old fragment-free URLs and existing bookmarks
remain supported. Selection is process-local: a fresh open retains the existing
Game-1 initial selection; same-active-context reuse retains selection. There is
no persisted resume pointer, scheduling rule, auto-advance or sequential lockout.

No route, query field, POST form, registry count or public version is added.
Existing lifecycle/Capture locking captures heading, seats, controls, summaries,
history and tokens from the same accepted source. Same-Game reads preserve the
selection generation, Report store and recovery expiry/token. Actual switching
retains existing recovery invalidation and exact-source Card/declaration rejection.
A Report's route still opens its actual Game, with same-Game recording backlinks.

Issue #254 names those existing review backlinks **Recording: Game N**, including
passed and completed Games. The ready-review invitation says **Decision selection:
Game N**; retained decision Report links say **Open existing analysis: Game N** with
their own available Trick/Card position. Their hrefs, fragments and readiness remain
exactly as above. Existing missing-evidence inspection, first-unfinished/overview
controls and explicit analysis POSTs retain their meanings. See the
[destination ownership map](home_and_recorded_review_navigation.md#destination-wording-issue-254).

Language return uses existing semantic source checks and safe input restoration.
The scoped Match branch now omits a normal fragment when retained validation
feedback exists: Chromium otherwise suppresses the existing error-summary
autofocus in favor of `#match-recording`. This was measured during verification.
Without feedback, valid recovery selection returns to `#match-recovery`; ordinary
recording returns to `#match-recording`. No new autofocus or JavaScript focus
handler is introduced. `match-play-N`, declaration, evidence, metadata and review
targets remain exact. Unsent other-form inputs survive language changes only with
the existing JavaScript enhancement; submitted safe input survives natively.

## Focused verification

### Prominent completion continuation (Issue #298)

Starting clean branch: `bug/298-match-completion-navigation`, full HEAD
`0ca32d293cdbfeff3b49de97e1e45cdcad048907`. Maintainer installed acceptance of #297
already established complete status in both selected Game and overview, all ten
Tricks/30 Plays, and an empty Game 2 with Bea/Clara/Anna in canonical seat order
and Anna still the recording perspective. Those are accepted baseline facts.

Developer evidence reproduced the placement defect using a validated disposable copy
of `skatmind-uat-match-end-29-plays.json`, imported through `/matches/import`. At
1365x900, the German native final-Card return showed completion at viewport Y 142,
but continuation at Y 5424, below the full history. Twelve new regression cases
failed on the requested placement/copy contract before the repair. Completion itself
passed, including one final-Card save and passive continuation without writes.

The change reads only the already captured `view` and matching page state. It adds
one paired caption, for **2,073 catalog keys per locale**, retaining **73 POST routes
and 125 forms**. Native form ownership, the enabled hidden declaration default
submitter, existing routes, source/generation checks, Report/recovery lifetimes,
deletion boundaries and all persistence/public contracts remain intact. No CSS or
JavaScript changes are needed. Normal final-Card focus stays on `#match-recording`;
the link receives focus only through user navigation. Existing validation and
source-checked native/enhanced language return remain authoritative.

The new complete HTTP module builds the named Anna/Bea/Clara 29-Play prefix from
`examples/historical_grand_normal_completion.json` through official builders. Its
16 cases cover final D9, one save, unchanged selection, native GET/no-write
continuation, rotated empty Game 2, exact earlier gaps, unfinished task priority,
passed/complete/all-terminal entries, short Null with truthful inspection, mixed
passed/short-ended completion, and genuine 30-to-29 rewind. Existing modules retain
validation/language, review readiness, source-bound stale forms, Report/recovery,
deletion and #292 declaration ownership coverage. In particular, the complete
declaration-draft module checks the first associated enabled submitter; the new
terminal-page test checks it again in the moved-navigation composition. With no
submitter, ownership or draft changes, the unrelated #292 browser flow need not be
repeated.

The complete-module inventory follows actual renderer imports, helper callers and
`rg -l` searches for `task.match.first_unfinished`, `task.match.all_complete`,
`task.match.next`, `match-recording-status`, `match-game-seats`, `match-recording`,
`match-declaration`, `match-evidence` and `/matches/position/`, supplemented by the
shared language/validation, strict paired-catalog, rename and executable packaging
contracts. Run complete modules, with the exclusive analysis-action module after
parallel workers exit:

```powershell
$scratch = "C:\Users\HENNIN~1\AppData\Local\Temp\opencode"
py -3.13 -m pytest `
  tests/test_match_completion_navigation_web.py `
  tests/test_match_game_navigation.py tests/test_match_game_navigation_web.py `
  tests/test_task_first_stateful_rendering.py tests/test_task_first_stateful_projections.py `
  tests/test_recorded_trick_progress_web.py tests/test_null_recording_end_web.py `
  tests/test_match_evidence_workflow.py tests/test_match_evidence_navigation.py `
  tests/test_unified_workflow_visual_contract.py tests/test_task_first_match_and_learning_workflow.py `
  tests/test_direct_match_evidence.py tests/test_match_evidence_presentation.py `
  tests/test_operation_feedback_language.py tests/test_operation_feedback_web.py `
  tests/test_recording_task_focus.py tests/test_match_declaration_drafts.py `
  tests/test_compact_declaration_form.py tests/test_compact_declaration_web.py `
  tests/test_frontend_validation_preservation.py tests/test_task_first_language_preservation.py `
  tests/test_frontend_language_switching.py tests/test_language_switch_context.py `
  tests/test_language_view_continuity.py tests/test_language_view_script.py `
  tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py `
  tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py `
  tests/test_profile_driven_creation_packaging.py tests/test_profile_driven_form_contracts.py `
  tests/test_match_recording_recovery.py tests/test_match_recording_recovery_web.py `
  tests/test_match_card_correction_ui.py tests/test_recording_deletion_lifecycle.py `
  tests/test_match_setup_and_card_layout.py tests/test_review_return_labels.py `
  tests/test_compact_play_grid_web.py tests/test_unplayed_card_summary_web.py `
  tests/test_match_decision_selection_web.py `
  -q -ra --tb=short -p no:cacheprovider -n 2 --dist=loadfile --max-worker-restart=0 `
  --junitxml="$scratch\issue-298-complete-parallel.xml"
py -3.13 -m pytest tests/test_match_analysis_action_placement.py `
  -q -ra --tb=short -p no:cacheprovider -n 0 `
  --junitxml="$scratch\issue-298-exclusive.xml"
git diff --check
$env:Path = "C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313;" + $env:Path
.\scripts\check.ps1 -Mode Quick
```

The disposable source-tree browser verifier is retained externally as
`$scratch\verify_298.py`. Its `--phase before|after --output FRESH_DIRECTORY` modes
use the #297-compatible dependency-free Edge harness, real pointer and native
Tab/Space/Enter events, de/en, JavaScript enabled/disabled, 1365x900 and 320x900
with long names. The initial final-Card screenshot and geometry are captured before
verifier scroll/focus/disclosure actions. It also retains delivered HTML, network
requests, accepted state/fingerprints, actual computed prominence/focus outlines,
explicit rewind and error/recovery/language observations. Enhanced language return
is checked against its submitted landmark/offset while scrolled into history;
it does not jump back to the completion action. Native language keeps the existing
fragment-free return; initial recovery selection still lands on `#match-recovery`.
Error summaries retain focus on both script paths.

Successful baseline artifacts: `$scratch\issue-298-before-03`; changed artifacts:
`$scratch\issue-298-after-03`. Every completed browser cell has one legitimate
final-Card operation/save/replacement and zero navigation-triggered writes, IDs,
analysis or preparation operations. The four desktop cells separately exercise one
deliberate rewind save and three explicit language profile writes. Fixture import
and profile setup are excluded from those interaction counts. Measured browser zoom
is **1 (100%)**; narrow viewport emulation is not zoom. Genuine **200% changed-action
zoom remains an installed acceptance item**. Intermediate verifier failures were
accounting/fixture/selector or historical focus assumptions, not completion failures.

These are developer checks, not installed UAT. Exact counts/runtimes and the final
Quick result/log accompany the completion handoff; **local Full is not run under
the session-approved routine**. Keep #298 open for exact-commit branch/main CI and
installed targeted acceptance of the new completion action. #292–#297 remain
complete; #208 stays open, UAT-01 is not globally accepted and UAT-02–12 remain
paused. Full maintainer UAT and current architecture/code analysis with treatment
of material findings remain required before v1.0.0. Release preparation is not
authorized.

### Discoverable Match evidence (Issue #263)

The clean starting branch was `bug/263-match-evidence-entry`, full HEAD
`2ea5e90a695d1c047693a471498ca1d91989d59c`, with #262 integrated. The actual #263
specification, #208's consolidated R07 evidence and the supplied post-#259 R07d/e
audit rows were read. Current regressions reproduced the empty wrapper and absent
targeted hand remedy: **five new tests failed before the repair**. This confirms
those current seams, not the precise cause of every original UAT observation.
R07c's #247 Skat/discard caption was already correct; #262 stays completed.

| Captured selected-Game state / reason | Existing editor owner / domain | Presentation |
| --- | --- | --- |
| Empty or passed Slot, `game is None` | No evidence editor | Omit the entire empty Skat/discard disclosure; keep the actual recording task/status |
| Started Game with unknown evidence, even zero prepared decisions | Accepted Game perspective for initial hand; existing separate Skat/discard forms | Keep useful Unknown/Exact/known-empty controls and clearing |
| Skipped `acting_hand_unavailable`, actor ID equals editor owner, `perspective_initial_hand is None` | That Game's perspective, original ten dealt Cards | One named action to `/matches/position/N#match-initial-hand` after the skipped-reasons disclosure |
| Several matching skipped decisions | Same editor / target | One shared action, not one per row |
| Another actor, `required_public_hand_unavailable`, or an already supplied initial hand | No demonstrated hand-entry remedy for that cause | Keep the actual reason without this action |
| Prepared decision, no observation, or missing owner/editor | No applicable missing-hand remedy | No action or invented prerequisite |

`task_first_match_state.py` captures one private `hand_editor_player_id` directly
from the selected accepted Game alongside its existing summary. The renderers use
that scalar, participant identity and existing structured decision rows only.
The selected Report, Settings own Player, next actor and displayed seat/name do
not choose the owner. Equal labels are not identity; fallback labels and escaping
reuse the existing name helper. No standalone/public/browser-state contract is
extended. Missing-owner cases are defensive scalar tests: valid Match definitions
already require a perspective.

The existing optional hand disclosure has the visible native summary
`#match-initial-hand`, captioned **Initial hand for {player}** (paired German).
It remains one editor with the original fields and full-deck domain. Native
fragment navigation reaches the summary while closed; **one explicit summary
activation opens it**. It is not automatic reveal. Closed-summary Tab continues to
the existing Undo control; after opening, Tab reaches `card_evidence_mode`.
Installed measurements found the new summary flush with the viewport top before
styling. Adding this exact ID to the existing Match scroll-margin rule gives the
focus ring room. No fragment/focus allowlist conflict was observed or changed.

These are active-context URLs, not immutable cross-tab sources. Same-Game navigation
keeps recovery and Results; a real Game/source switch retains normal invalidation.
Stale evidence cannot recreate a removed Game. Existing validation opens the real
failed form, or falls back to `#match-recording` when its exact source/form is gone.
Language/error priority and source-bound receipt delivery remain unchanged.

The temporal input is the original **ten dealt Cards before Skat pickup/discard**,
including already played Cards belonging to that hand, not the current remaining
hand. Non-Hand declarer reconstruction still uses original hand plus original Skat
minus discards; the hand alone may not suffice. Complete traces can already prepare
decisions without explicit hand entry. Saving does not analyze, switch perspective
or return through a wizard; the existing recording-to-review link and analysis POST
remain separate.

`test_match_evidence_navigation.py` adds 23 focused cases, including canonical
unknown/complete states, actual mixed skip reasons, duplicate labels and rotated
Games, defensive missing owners, a retained other-Game Report, and real HTTP
rejection/retry/no-op/reopen/source switching. The established B/C/A CK/C7/C10 trace
is **0/3 → 1/3** only after C's valid ten-Card hand including C7. A remains the next
actor and winner of 14 points. C's explicit Report retains CK, all ten C Cards and
no later C10 in its historical prefix. Exact independent Session Request/Result
and frozen Checkpoints survive the Match work. Existing compact-entry, recovery,
navigation, validation/language and recorded-context tests remain in use.

See [installed evidence and limits](unified_workflow_visual_contract.md#match-evidence-entry-issue-263).
Inventory remains **67 POST routes / 112 forms**; three captions increase the paired
catalogs from **1,802 to 1,805**, preserving sorted keys and placeholders. Package
0.17.0, Python >=3.13, AGPL-3.0-only, dependency floors including tzdata>=2026.4,
98 scenarios and all public/persistence contracts remain. Unknown/Exact redesign,
global capture-disclosure preferences, other R01/R11/R13 residues and automatic
Learning decisions stay separate. Both exact merged-#263 CI jobs gate manual closure;
#208 stays open, UAT-01 unaccepted, UAT-02–12 paused, B-09/B-07 open and B-06 closed.

### Direct evidence interaction (Issue #268)

Issue #268 supersedes only the normal evidence-mode interaction described in the
#263 historical section above. The closed named summary and one native opening
remain; the first editable hand control is now a Card checkbox rather than the
removed mode selector. Owner/remedy selection, original-hand temporal meaning,
same-Game lifetimes and real-switch generation invalidation remain. Hand discards
omit the unusable nonempty grid, while original-Skat/initial-hand editors remain.
See [direct state/action map](compact_card_entry.md#direct-match-evidence-actions-issue-268).

### Saved progress presentation (Issue #260)

Starting clean `bug/260-match-progress-presentation` HEAD:
`6477188ee89034bb5d49f8f5b93086a1f73150d6`, the integrated #259 tree. The actual
#260 specification and #208's consolidated comment `5740775548` preserve the
historical UAT installation `483e51269d0206d29d9f73001dfadf8f0e7b2f32` as separate
evidence. The supplied post-#259 engineering reconciliation was confirmed at the
renderer seams: activity-sounding partial status, generic Card count, first-open
wording and the selected-Game round paragraph. The existing selected text and
`aria-current="page"` were already tile-local. Issue #260 implements R12a–c and
preserves R12d; it does not establish whole-R12 human acceptance.

`_recording_status` reads only the captured position's `game_state`, `play_count`
and `completed_trick_count`. For `play_in_progress`, integer Plays must be from
1 through 29 and completed Tricks must equal `play_count // 3`. The accepted
remainder is `play_count - 3 * completed_trick_count`, either zero, one or two.
The existing `game_result.COMPLETED_TRICK_COUNT` supplies the ten-Trick bound.
Malformed partial counts raise rather than clamp, round or fabricate completion.
There is no additional position replay, hand reconstruction, recovery, score or I/O.

| Existing accepted state/count | English caption meaning (paired German catalog) |
| --- | --- |
| `empty` | Not yet recorded |
| `setup` | Declaration needed |
| `ready_for_play`, zero Plays | Ready to record Cards; no Cards recorded yet |
| 1 / 2 Plays | Partially recorded: 0 of 10 Tricks; 1 Card / 2 Cards in Trick 1 |
| 3 Plays | Partially recorded: 1 of 10 Tricks |
| 4 Plays | Partially recorded: 1 of 10 Tricks; 1 Card in Trick 2 |
| 29 Plays | Partially recorded: 9 of 10 Tricks; 2 Cards in Trick 10 |
| `play_complete`, 30 Plays | Play record complete |
| `passed_deal` | Passed |

These are all six current Match position states. There is no shortened-terminal
state in this Match contract; Historical/Session terminal support is not changed.
Only the partial branch uses a denominator. Completion, next target and review
eligibility remain independent authoritative facts. A partial Game may have prepared
decisions, and thirty Plays do not guarantee every export or a settled score.

The same compact caption is used on the selected Game and its overview tile;
the separate generic tile Card count and redundant completed/passed task paragraph
are removed. The selected-Game round paragraph is removed. All twelve `h3` round
groups remain, at the same font size/contrast with normal weight, beneath the
overview `h2`. All 36 ordered native links, seats, exact hrefs/fragments and the
single tile-local textual selected marker retain their behavior. The actual
captured `next_position` supplies both the first-incomplete cue and link; selection
coincidence and no-target rules remain unchanged.

The navigation tests add literal bilingual coverage for the table, invalid scalar
counts, ordered groups, earlier targets and unchanged selection. Existing real
HTTP tests now record a first Trick, Pass Game 2, return, continue and strictly
reopen; rejected input leaves accepted progress unchanged. The existing final-Card
and rewind Preview/Cancel/Apply case checks 30 accepted Plays during the proposal,
then 29 only after Apply. Same-Game navigation/language retains exact Report bytes
and recovery identity; a real Game switch invalidates recovery but preserves a
still-current Report whose own source stays Game 1. Rendering Game 2 never borrows
that Report's progress. Strict reopen retains Workspace bytes, not process-local
Reports. No source/selection/readiness contract was changed.

Twenty-two new presentation cases failed before the repair. Focused corrected
runs passed **92**, then **198**, then **188** tests (overlapping selections,
not an additive suite count). See the
[independent installed comparison](unified_workflow_visual_contract.md#saved-match-progress-issue-260)
for the bounded browser matrix, native focus, operation accounting and hashes.
The prescribed final complete check is separately reported with its actual child
exit and retained log; these focused runs do not replace it.

Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependency floors including
tzdata>=2026.4, 67 POST routes, 112 forms and 98 scenarios remain. Three partial
captions increase the paired catalogs from 1,797 to 1,800 with sorted key and
placeholder parity. No workflow JavaScript, standalone Capture, consent, persistence
or public field changes follow. R01/R07/R11/R13/R15 residues and automatic Learning
questions remain separate. Both #259 CI jobs on the starting SHA subsequently
passed in [run 35977510861](https://github.com/hnnng-w/skatmind/actions/runs/35977510861);
this is baseline evidence, not #260 validation. #259 remains completed. Exact
merged-#260 `check` and `v1-supported-platform-matrix` must pass before manual closure.

### Historical Issue #238 evidence

Starting clean branch: `feature/238-match-game-navigation`, HEAD
`dd981819bf4a23577dd485ebd72b20a66435429d`. The bounded comparison with planning
archive `aecd151aafff1601b0366bb024e65a98006f4240` found unchanged Match projection,
first-unfinished rule and Workspace progress. Intervening renderer changes were
#232's format and #234's unplayed summary; lifecycle changes were #235 retirement
guards. Those changes, #236 integration and #237 Session request protection remain.

`tests/test_match_game_navigation.py` and `tests/test_match_game_navigation_web.py`
add 27 regressions over canonical views and real returned forms. They cover empty,
setup, declared, partial, passed, complete, earlier gaps, all passed, all complete,
all started, seats, escaping, one ordered overview, unique anchors, real creation,
one-save actions, zero-save navigation, strict reopen, stale forms, rejection and
language focus. A legal final-Card save keeps selection. A genuine executed Report,
exact download, no-op correction, preview/cancel, language restoration and actual
switch invalidation precede a real 30-to-29 rewind, changing the suggestion from
Game 2 to Game 1 and removing the complete-recording conclusion.

Completed compatibility runs: **221 passed in 540.52s**, **327 passed / 2 existing
skips in 279.41s**, and **150 passed in 13.37s**. These cover Match progression,
creation, #222/#223/#225/#226/#229/#232/#234–#237, language/security, standalone
Capture/Corpus, the Corpus observer/provenance boundary and CLI lazy-import/layer
guards. The skips are `test_actual_file_boundaries_fail_before_import[symlink]`
(`Actual symlink creation unavailable: 22`) and
`test_managed_direct_child_validation_rejects_escape_and_links`
(`This Windows account cannot create symbolic links.`). An earlier larger run
timed out and is not counted as successful. Final prescribed complete-check
stdout/stderr, actual child exit status and pytest totals accompany the implementation
report; focused passes do not replace that gate. The first complete attempt passed
all non-pytest stages, then reported 9,098 passed / 3 skipped / 1 failed: the catalog
inventory assertion still expected 1,545 rather than the four-key-expanded 1,549.
The expectation is corrected without changing catalog parity checks or production
code. A complete corrected-tree check is required; that attempt's child exit `1`
is not success. The focused catalog follow-up passed 22 tests and explicitly
reported the three existing skips: the two above plus
`test_recording_deletion_files.py::test_real_symlink_is_not_followed`
(`Actual symlink creation unavailable: 1314`). Installed production/resource bytes
are unchanged by this inventory correction, so the final browser evidence below
still covers the production tree.

## Independently installed browser evidence

`scripts/verify_match_game_navigation.py` reuses the dependency-free DevTools
harness with an independently installed Wheel, rejects checkout imports, and
compares 14 loaded module/resource hashes with the intended tree. Use an existing
local Edge executable and a fresh disposable output directory:

```powershell
& PATH_TO_INSTALLED_PYTHON scripts/verify_match_game_navigation.py `
    --browser PATH_TO_EDGE --output FRESH_SCRATCH_DIRECTORY `
    --wheel PATH_TO_WHEEL --phase after
```

`--phase before` verifies the actual starting-HEAD Wheel; it does not rewrite source
or switch branches. Synthetic evidence is under `$env:TEMP/opencode/`:

* `238-before-03/evidence.json`: 96 matched baseline measurements;
* `238-after-06/evidence.json`: final 176 measurements, `completed: true`, source
  hashes, actual request paths/counts, saves, focus, geometry, Report/source IDs
  and download hashes;
* matching PNGs, including `native-de-empty-390-1-True.png`,
  `native-de-declaration-390-1-True-controls.png`,
  `native-en-partial-320-2-True-controls.png`, `js-de-error-320-2-False.png`,
  `native-de-overview-focus.png` and `native-de-rewind-focus.png`;
* `238-browser-env/`: independent installed environment;
  `238-after-wheel-02/skatmind-0.17.0-py3-none-any.whl`: inspected Wheel.

Python **3.13.7**, SkatMind **0.17.0**, Microsoft Edge **153.0.4234.32**, de/en,
JavaScript on/off, 1365×900, 390×844, 320×800 and representative doubled text at
320×800 were used. Each computed font size is doubled once without changing
browser zoom or device scale. Native tile/overview/backward-continuation actions
were also exercised at desktop and narrow widths. Document/client widths agree at
**1350/1350**, **375/375**, **305/305**, including enlarged text. Screenshots include
separate control-area captures; required controls remain available and names wrap.

Matched German/no-script full-document top coordinates (CSS pixels, rounded):

| State / width | Heading before → after | Primary button before → after | Overview before → after |
| --- | --- | --- | --- |
| Empty / 1365 | 5602 → 533 | 5691 → 777 | 790 → 984 |
| Declaration / 1365 | 5602 → 533 | 6161 → 1247 | 790 → 1528 |
| Partial / 1365 | 5602 → 533 | 6524 → 1611 | 790 → 2452 |
| Empty / 390 | 13501 → 555 | 13694 → 989 | 777 → 1313 |
| Declaration / 390 | 13501 → 555 | 14396 → 1691 | 777 → 2160 |
| Partial / 390 | 13501 → 555 | 14879 → 2174 | 777 → 4311 |
| Empty / 320 | 14512 → 660 | 14757 → 1144 | 857 → 1493 |
| Declaration / 320 | 14512 → 660 | 15547 → 1934 | 857 → 2477 |
| Partial / 320 | 14512 → 660 | 16317 → 2704 | 857 → 5019 |

Direct fragment entry keeps those document coordinates and focuses the recording
section; its heading is about **45.5 px** from the viewport top on desktop and
**33.2/33.4 px** at 390/320. The old target showed an unnamed generic task heading;
the new one includes the selected Game. At 320/200% the partial primary button is
**8389.5 px**, before the overview at **15783.2 px**. Long names, full history and
enlarged guidance still require vertical scrolling: no one-screen or reduced-total-
height claim is made.

Each of four final browser flows has **37 native actions, 18 POSTs, 9 actual Match
saves and one explicitly requested analysis**. Eight saves are native create,
Start, declaration, two Cards, Pass, final Card and rewind. One separately labelled
fixture POST/save supplies 27 legal surrounding Plays through the returned
specialist form. Navigation, language, rejection, Report view/download and preview
save nothing. Same-source Report/download and preview/token identity survive
overview, same-Game tile and language navigation. Native error language return
focuses the error summary; preview language return focuses `match-recovery`; Apply
returns to the named recording region. Focus has a visible 3-pixel blue outline.
Earlier unsuccessful probe directories remain diagnostic evidence, not passes.

```text
Wheel        78d272ef7a7875925fdb4cd8ef772de3e5439ac659c33e199beed4e00e50a478
app.css      deec38856f8cc22f7ec5b46a15629422f486830b616be99a1ef559413757c627
workflow.js  f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298
Match render fcc754995a1037f2b8fbe86c2374c75d79608cda098596b7ae25e332e65eb46d
Language     13a66f4a0bbe1629591bc5d4e0b57392c62e688070756c4dd244287314e4352a
```

Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependencies including tzdata>=2026.4,
#230 profile shape, public/Product formats, registry counts and 98 generated
outputs are unchanged. No real recordings or UAT files are used. Both exact-merged-
commit `check` and `v1-supported-platform-matrix` remain manual closure gates.
#237 remains completed; #208/unresolved findings stay open, UAT-01 failed,
UAT-02–12 paused, B-09/B-07 open and B-06 closed. No whole-UAT or release-readiness
claim is made.

## Rule-ended short Null games (Issue #290)

[Rule-ended Null recording](null_recording_end.md) extends first-unfinished
selection to skip `rule_ended` alongside passed deals and complete play traces.
A decisive completed declarer Trick ends normal capture while retaining the
selected Game. The next Game is only an explicit navigation suggestion. Actual
Card/Trick counts and complete-trace metrics retain their existing meanings;
short rule-ended Games have separate wording/counts. History, evidence and
correction remain accessible, including after strict reopen.
