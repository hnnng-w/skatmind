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
Settings stays directly accessible. Recording descriptions explain resumability
and evidence-limited review. Continuing one Session does not start another Game
or insert it into a Match. Shared entry rendering supplies one optional short
explanation beneath the page title. Actual recovery, transfer, prerequisite,
source-selection, and return links remain; Learning's explicit-operation
explanation is retained beside its existing preparation controls.

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
