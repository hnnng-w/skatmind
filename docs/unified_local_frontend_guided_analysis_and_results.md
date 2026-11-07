# Unified local frontend guided analysis and Results

## Status

Current S7 extension: [Issue #316](automatic_historical_learning_s7_verification.md)
saves a successful manual guided/imported Historical Review's exact input and genuine
execution at the manual producer's guarded publication boundary. `/review/saved`
provides restart discovery, original downloads, reopening/correction and confirmed
deletion. New guided sources have private independent identity scopes; raw executed
IDs and bytes remain exact. The seven-step normal-completion editor and all supported
imported Historical endings retain their existing input behavior. Direct Session
Historical/Finalize calls to the shared executor are not automatically saved here.

Issue #211 implements the guided Analyze and Review slice of the
[unified local frontend contract](unified_local_frontend_contract.md). It extends
the Issue #210 [application shell](unified_local_frontend_application_shell.md)
without adding a Root workflow, Public API export, Schema, persistence format,
dependency, or Product algorithm.

Issue #218 adds separate submitted-form preservation and localized validation
feedback without changing the guided Product builders or execution boundary. See
[Frontend validation state and localized feedback](frontend_validation_state_and_localized_feedback.md).

The implemented browser areas are:

```text
/analyze
    guided current or retrospective one-Decision analysis
    guided one-Decision Post-game Review
    strict Position JSON import

/review
    explicit manual guided normal-completion Historical entry
    strict Historical and retrospective Position JSON import

/review/recorded
    normal Review navigation: select an existing Session or Match
    explicit opening reaches its existing source-specific review actions

/sessions
/matches
/learning
    managed stateful workflows implemented by Issue #212
```

Package version remains `0.17.0`, Public API contract version remains `1`, the
Root workflow count remains seven, and the one Console Script remains
`skatmind = skatmind.cli:main`.

## Private contracts

The private versions are exactly:

```text
GUIDED_ANALYSIS_FRONTEND_VERSION = 1
GUIDED_POSITION_FORM_VERSION = 1
GUIDED_HISTORICAL_REVIEW_FORM_VERSION = 1
FRONTEND_RESULT_PRESENTATION_VERSION = 1
FRONTEND_JSON_TRANSFER_VERSION = 1
PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION = 1
FRONTEND_VALIDATION_PRESERVATION_VERSION = 1
```

The private policy tuple is exactly:

```text
guided_forms_build_existing_root_documents
one_explicit_application_execution_per_run
normal_forms_reuse_existing_product_defaults
advanced_settings_are_collapsed_and_explained
strict_json_import_is_explicit_and_non_executing
exact_json_download_uses_retained_values
public_result_is_the_only_presentation_source
normal_result_states_are_not_transport_errors
process_local_state_without_implicit_persistence
private_engine_state_never_enters_browser_state
```

These identities are independent from Package, Public API, Root workflow,
Schema, Session, Match, Corpus, Search, and persistence versions.

## Process-local state

Issue #229's [recorded-review navigation](home_and_recorded_review_navigation.md)
preserves the independent manual draft, step, import and Result when visiting Home,
the chooser or a recording. Its secondary manual link returns to `/review` without
reset. The chooser does not import or convert recordings into the wizard. Shared
concept/related panels are replaced by short introductions; the actual guided
steps, information choices, actions, Result types and downloads remain supported.

Analyze and Review have independent immutable revisioned state under the existing
application-context lock. Each area retains at most one draft or imported
`RequestDocumentV1`, one latest successful Request/options/Result tuple, exact
precomputed download bytes, legacy safe validation messages, and one in-progress source
revision.

Every accepted input mutation advances its route-specific revision once and
invalidates older output. A rejected submitted candidate remains separate and
does not advance accepted state or clear older successful output. Execution
failure publishes no replacement Result. Reset requires explicit confirmation.
Stale forms and duplicate Run attempts return HTTP `409`; stale completed work
cannot overwrite newer state. Product execution occurs outside the context lock,
and publication rechecks the exact source revision without retry.

The workflow State remains process-local and contains no timestamp, caller path,
Session, Match Workspace, Corpus object or managed-storage reference. Closing the
process discards drafts and unexecuted imports. S7 separately retains successful
manual Historical source/execution/head values in the private automatic archive.
Saving failure leaves the successful process-local Result available with truthful
feedback and a bounded original-attempt persistence-only retry where possible.
Single-situation Position imports keep their process-local lifetime.

## Position form

Issue #303 identifies `/analyze` as **Enter a situation yourself**, with one short
hand/visible-situation introduction and a native button-styled link to the saved
recording chooser outside the form. The form stays directly available. Its mode
legend asks what to assess in this situation; the current decision and actually
played retrospective Card options retain their values and execution behavior.
Retained Result presentation and validation-focus priority remain intact.
The normal sections are:

```text
Your role and the contract
Cards you can currently see
Completed tricks and current trick
Current score and turn
Run analysis
```

The form supports Suit, Grand, and all four Null declaration variants; Declarer
and Defender perspectives; all three local seats; declaration flags; bid value;
optional Matadors; the local hand; legitimately visible Skat and public Declarer
Cards; completed and current Tricks; points; opponent Cards remaining; and the
retrospective actual Card.

The canonical 32-Card control order and readable labels come from the existing
Deck and Card-name contracts. Existing Product helpers validate Card uniqueness,
declaration dependencies, Trick order and winners, Turn Phase, all three
remaining hand sizes, information visibility, and actual-Card legality. The
frontend does not infer hidden ownership or calculate Game value independently.

### Suit-grouped Card palettes (Issue #304)

All eight `_card_palette()` callers now share the compact native Card faces and
container-based balanced **8/4/2/1** suit layout. This covers Analyze `hand`, `skat`,
`public_declarer_cards`, Review's four deal fields and its restricted non-Hand
discard field. Printed suits are labelled in German/English and empty restricted
groups are omitted. Guided DOM, keyboard and native submission order stays
**C/S/H/D**, then **A/10/K/Q/J/9/8/7**. The guided fieldset, selected-count meaning,
feedback markers and explicit form operations remain owned by the guided adapter.
Full localized accessible Card names accompany the compact visual faces.

The maintainer accepted #303 A–C on
`038130df1296675b96a83c4631d7ecb754ebadd1`, including the native saved-name picker,
JavaScript-disabled operation and zoom. That acceptance remains within #303's
scope. The maintainer subsequently accepted #304 A–D on
`3d4681b35d6fe7a41cc2a7ed3e5d63def80cfbf6`, including its native operation and
enlarged browser zoom. Issue #305's separate active-Play/footer boundary requires
its own exact-commit CI and installed targeted acceptance.
See [Issue #304 verification](guided_card_palettes.md) for measured geometry,
complete module commands, operation accounting and remaining gates.

### Completed-trick input grouping (Issue #273)

Each of the nine numbered fieldsets contains four local input wrappers in the
existing order: leader, Card 1, Card 2, Card 3. Each wrapper keeps its visible
label directly above its native select. The row uses wrapping flex layout with
intrinsic option widths; the wrappers use a single-column grid. Start alignment
and a consistent select font weight preserve natural control heights. This fixes
the former separate-label/separate-select grid items without clipping overflow
or using fixed heights. The leader's implicit label and Cards' explicit IDs,
the shared `_card_select()` helper, and other selector layouts are unchanged.

`tests/test_completed_trick_input_grouping.py` covers all rows in German/English,
empty and populated drafts, unique IDs, associations, option/order/value parity,
final HTTP validation responses, retained accepted Results, safe rejected input,
native and enhanced language returns, and neighboring current/actual/manual-review
Card selectors. These are structural and HTTP checks, not visual-layout proof.

Developer browser evidence on 2026-09-29 used the uncommitted Issue #273 repair
over base `471f0d5fde08e827d60e3157dd795dafa8fd6713`, working-tree resources,
disposable synthetic drafts, and a separate headless Microsoft Edge
`154.0.4258.37` profile through the existing local DevTools helper. All 30
German/English combinations of empty, populated, and native submitted-error
states passed at these actual window/viewport conditions:

| Window (pixels) | Reported CSS viewport | Zoom condition |
| --- | --- | --- |
| 1440 x 1000 | 1406 x 903 | Default 100% |
| 1200 x 1000 | 1166 x 903 | Default 100% |
| 1000 x 1000 | 966 x 903 | Default 100% |
| 800 x 1000 | 766 x 903 | Default 100% |
| 552 x 1000 | 518 x 903 | Default 100% |

Measured label/control containment, complete-group wrapping, selected-text room,
and equal 42.39 CSS-pixel control heights passed, with no detected row or document
horizontal overflow. Native Tab/ArrowDown selection and visible focus passed;
current-Trick/actual-Card readability and manual-review native selection passed.
Representative rendered screenshots were also inspected. No viewport emulation,
CSS zoom, transform, or text enlargement supplied these results.

Actual **200% browser zoom remains outstanding**: the disposable profile zoom
probe did not change the measured zoom. Interactive Edge GUI and installed-package
browser verification were not performed. This developer evidence does not replace
the required focused maintainer retest; Issue #273 remains open pending that
retest and outstanding acceptance checks.

Normal Position translation preserves:

```text
sample_count = 1000
random_seed = 42
use_basic_opponent_strategy = true
recommendation_method = omitted
analysis_mode = live_decision unless retrospective was selected
game_end_reason = not_ended
validate_output = true
```

### Guided-analysis validation feedback (Issue #274)

Rejected Analyze input now distinguishes an empty remaining hand from an incomplete
numbered completed Trick in German and English. The hand summary links to its
visible palette fieldset, with feedback after the tiles; an incomplete row links
to its first missing selector and names all missing inputs. The row message is
after its four-group fieldset, preserving #273's layout and native controls. A used
row requires its leader and all three Cards. Clearing the entire row is described
only as an alternative for an unused row. Other Card-validation semantics are
unchanged. The [validation guide](frontend_validation_state_and_localized_feedback.md#guided-analyze-omission-feedback-issue-274)
records the bounded diagnostic and targeting mechanism.

Developer browser evidence on **2026-09-30** used headless Microsoft Edge
**154.0.4258.37**, the uncommitted #274 working-tree implementation over
`edcb8f1ea1d57ab1a3e61cf5a718b1a1a925a4a7`, source-tree Python/resources and the
existing local DevTools helper. This was not an installed-package browser check.
A newly created disposable profile and synthetic managed home were used; the
optional application script was disabled for native rejected-state language return.

Both English and German passed empty, actual server-rejected, and corrected valid
presentations at these native window sizes, without viewport emulation or CSS scaling:

| Window (pixels) | Reported CSS viewport | Browser zoom |
| --- | --- | --- |
| 1440 x 1000 | 1406 x 903 | Fresh-profile default 100% |
| 800 x 1000 | 766 x 903 | Fresh-profile default 100% |
| 552 x 1000 | 518 x 903 | Fresh-profile default 100% |

Device pixel ratio and visual viewport scale were both 1. The checks submitted
the real form using native Enter, verified the POST and retained server feedback,
and observed the two distinct correction messages. Hand feedback remained outside
the Card grid; completed-Trick feedback remained outside all four input groups.
Summary activation focused the intended fieldset and missing Card selector with
visible outlines. Tab continued to the following row's leader, and native
ArrowDown/Home selection remained usable. Unique IDs and all accessibility
references resolved. No page/row horizontal overflow or selected-option clipping
was detected at these sizes; representative normal/narrow screenshots were inspected.

Native language switching retained the explicit empty hand and Card 3, CK/C7 order
and translated feedback without another analysis submission. Additional rejection
checks preserved an empty first current-Trick slot, second Card and actual Card;
the previous valid accepted state remained identical. Correcting the row and hand
produced a real valid Result. The neighboring manual Review legal-Card selector
also retained native selection and visible keyboard focus at all tested sizes.

**Outstanding:** actual **200% browser zoom**, interactive Edge GUI verification,
and the focused maintainer retest on the identified integrated installed build.
The available headless helper has no established real browser-zoom control;
resizing/scaling is not counted as zoom evidence. Developer checks do not replace
maintainer acceptance. Keep #274 open, with #273 and #208 unchanged, pending the
required installed-build retest and outstanding evidence. This is not UAT-01
acceptance or Release readiness.

## Advanced Settings

Both workflows use the six initially collapsed groups:

```text
Analysis method
Runtime and reproducibility
Opponent behavior
Simulation and comparison
Technical evidence
Dataset and evaluation
```

Analyze maps understandable controls to the existing Immediate, bounded Search,
Auto, Information-set Search, Multi-Step, Policy Comparison, opponent Policy,
Profile-preset, sample, seed, and public Provenance options. Existing versioned
interactive Search settings are reused rather than duplicated.

Review exposes the existing Decision Snapshot, Immediate Review, bounded Search
Review, Information-set Search Review, Replay Coaching, Information-set Replay
Coaching, Tactical Motif Review, seed/sample, Historical Review budget-profile,
and public Provenance options. Selected dependent families show their existing
implied prerequisites before Run. The two pages contain no fake Dataset control;
the Dataset group states that those operations remain advanced automation.

Settings explain runtime, reproducibility, evidence scope, fixed-policy behavior,
and boundedness. They do not change Skat rules, promise calibrated probability,
describe Search as perfect play, or describe rule-based behavior as a learned
prediction.

## Historical editor

Issue #303 labels `/review` **Review a completed game manually**, also used on the
chooser's manual link. Its concise full-deal/full-history explanation explicitly
applies to the guided editor; the Historical and retrospective Position JSON-import
paths below remain separate supported variants. Secondary native links outside
forms reach the recorded chooser and `/sessions`, the persistently saved recording
alternative. They do not save or transfer the manual draft. S7's notice distinguishes
unsaved drafts from successful saved Historical executions. Its original-attempt
downloads reject stale views rather than exporting a newer execution under an older
control; native filenames and payload bytes remain unchanged.
GET `/review` resumes the available step/import/Result without starting or resetting
the editor. See [entry navigation](home_and_recorded_review_navigation.md#independent-analysis-and-manual-review-entry-issue-303)
for the source distinction and scoped verification.

The bounded #303 installed-feedback follow-up gives these secondary entry links a
scoped button-style surface and moves the chooser's manual entry above its recording
lists, preserving the maintainer's earlier functional acceptances. Step 1 now offers
saved display names through native `input[list]` controls and one shared `datalist`.
The single localized hint is conditional on available names; absent, empty or invalid
profiles retain the ordinary free-text guidance. The already loaded validated profile
supplies a request-local immutable tuple of display names only, read under the existing
lock. No complete private profile is passed to the manual page renderer.

Selecting a suggestion copies editable display text into a seat field. It does not
allocate a seat automatically, bind a profile Player, save a profile or create a
recording. The POST still submits only the existing three optional label fields and
normal revision/instrumentation guards. Names are escaped in HTML, all three `list`
associations resolve to the same unique datalist, and the accepted draft owns its
labels independently of later profile edits. Previously offered names remain valid
free text. Fixed Historical Player IDs, uniqueness validation, rejected values,
language return, imports, Results and exports remain unchanged.

The normal `/review` editor has exactly seven server-rendered steps:

```text
1. Players and seats
2. Deal
3. Declarer and declaration
4. Skat pickup and Discards
5. Card play
6. Review options
7. Validate and run
```

It uses deterministic process-local IDs `frontend-forehand`,
`frontend-middlehand`, and `frontend-rearhand`, and Game ID
`frontend-historical-review`. Optional non-empty display labels must be unique.
The editor accepts one exact 10/10/10/2 Deal, validates pickup or Hand-game
Discards, derives each acting Player and legal Card set, and delegates actor,
winner, and next-leader replay to the existing observed-trace and rule helpers.
It appends one chronological Card at a time and can undo only the final play.
Back preserves valid entered facts; a completed Play step can return to Review
options without re-entry.

### Active Play selection and wizard navigation (Issue #305)

Active step 5 uses compact native radios in one singular `card` group inside the
existing append form. `build_historical_play_view_v1()` still owns the actor and
legal membership. The guided presentation adapter filters those Cards into printed
**C/S/H/D** groups, with **A/10/K/Q/J/9/8/7** ranks and empty groups omitted. It
does not derive legality or effective trump suits. Every initial group is empty,
including a singleton. Pointer, Space and arrow-key selection only change the
native choice; the explicit Record played Card button appends one chronological
Play. Native Tab enters and leaves the group rather than visiting every radio.

The group has one `field-card` identity, full localized accessible Card names and
an explicit feedback boundary outside its tiles. Existing feedback rendering links
to the group, associates its error text and focuses the initial error summary.
Rejected unavailable Cards cannot add tiles. Enhanced language return carries one
offered choice or an explicit empty selection. Native language return retains its
existing accepted/rejected-state contract; it does not transport an unsent choice.
Append, Undo and Back still invalidate old language bindings. Back from step 6
with all 30 Plays renders no Card selector and retains the card-free Continue path.

The shared manual wizard footer retains Reset alone at step 1 and Back at steps
2–7. Back has the existing secondary role. Footer-scoped start alignment and
zero child-form margins prevent the taller Reset form from stretching Back or
adding duplicate spacing. Content-driven height, existing minimum targets and
natural wrapping retain readable translated text. Back and Reset remain independent
native forms; unchecked required Reset consent belongs only to Reset.

This active-Play change is separate from #304's accepted eight checkbox palettes.
See [Issue #305 verification](manual_review_play_and_navigation.md) for the exact
module inventory, regression-first failures, browser measurements, operation
accounting and remaining gates.

The bounded manual editor emits only `normal_completion` after exactly 30 legal
plays. It does not remove broader Historical support. Existing shortened endings,
continuations, party-wide Claims, concession/exposure/open-play variants, and
other supported Historical documents remain available through optional strict
JSON import and receive the same Result presentation.

## JSON import

Import is a secondary explicit action and never executes. Each page accepts one
strict multipart upload containing one finite UTF-8 JSON object without a BOM,
duplicate object keys, nested multipart, duplicate file fields, or unsupported
headers. The maximum file content is exactly `1,048,576` bytes; bounded multipart
framing is accounted for separately. Caller filenames are ignored and retained
nowhere. Parsing uses no temporary file.

Analyze accepts only `position_analysis`. Review accepts `historical_game` and
`position_analysis` with exact `analysis_mode=post_game_review`. Existing public
input parsing constructs one immutable Request, and a separate explicit Run is
required. Incompatible workflows produce a distinct safe HTTP `400` response.

Issue #252 names the metadata disclosure **Import details**. Before execution the
validated Request link remains in this imported-document context, with no Result
claim. Once the displayed Result owns that same retained Request, its download
area owns the action alone. This uses `latest_successful_request` / `imported_request`
ownership and retained bytes, never href equality, filenames or submitted form values.
A running page retains import-only access when applicable; a rejected new input
does not relabel an older Result. Accepted replacement still invalidates old output.

## Application execution

Every explicit Run constructs or reuses one immutable Request and one immutable
`ExecutionOptionsV1`, then calls the existing Public/Application execution
boundary exactly once with one of:

```text
memory://skatmind/app/analyze
memory://skatmind/app/review
```

No CLI subprocess, Root input file, external request, execution retry, Search
workflow rerun, Historical workflow rerun, or render/download execution exists.
The retained public `ExecutionResultV1` is the only Product source for
presentation. Presentation
does not inspect private Search Worlds, Application bundles, private Provenance,
or hidden ownership and does not recompute recommendations, settlement, winner,
score, or decision quality.

## Result presentation

Issue #221 reuses `execute_guided_frontend_review_v1` directly for an exported
Session Checkpoint Position Request in `post_game_review` mode, with default
output-validating options and no manual Review draft. The active Session page
uses this same Result presentation with a separate exact recorded-decision source
label and its existing authenticated Session downloads. See
[Review recorded Session decisions](session_recorded_decision_review.md).

Successful Results appear before the secondary raw-JSON import controls. Result
content uses these exact sections and order:

```text
Summary
Recommendation
Alternatives
Evidence and limits
Technical details
```

The model retains these five identities. Issue #252 renders the final identity as
one native **Technical analysis details** disclosure closed by default, retaining
`result-section-5` on its summary rather than repeating the caption in an h2.
The renderer-owned **Downloads for this analysis** utility precedes it, after
Evidence and limits. Available **Analysis Request (JSON)** and **Analysis Result
(JSON)** links are native secondary actions outside every disclosure. Downloads
are not a sixth Result data section or a save of the editable recording. Candidate and
Decision tables preserve retained public order. Whole-game Results explicitly
state that there is no single whole-game Card recommendation. Review coverage,
warnings, fallback, boundedness, information cutoffs, fixed-policy limits,
selected-world limits, observed-Card limits, Coaching/Tactical limits, and Claim
scope are shown only from retained public fields.

Issue #239 remediates #208 retest R09 in the shared Position Summary: the existing
known-party point details read `score_summary.total_declarer_points` and
`score_summary.total_defender_points` from the retained Result. The Position's
`declarer_points` / `defender_points` remain supplemental inputs outside completed
Tricks. Totals already include these supplements once: the R09 completed history
with 0/0 displays 14/29; a separate valid 5/7 input displays 19/36. The unfinished
current Trick, later recording state, Skat/discards, forecasts and adjusted ending
or settlement fields are not added during presentation. This applies to guided
Position analysis/review and saved/current-position Session Results. Historical
and separate Match rendering retain their existing contracts.

Integer zero is displayed as zero. Defensive missing/non-integer total fixtures
show localized **Not available** on that side without coercion or supplemental
fallback, preserving an independently valid other total. Canonical Results already
require both integers; import acceptance and Schemas are unchanged. Focused de/en
normal-Summary assertions cover the score cases, immutable source documents,
candidate/method/order preservation and Historical regressions. The
[Session review guide](session_recorded_decision_review.md#verification-and-future-affected-path-retest)
records genuine Session execution, exact downloads and installed-browser evidence.
Issue #240 supplies the bounded R10 implementation below. Issue #241 adds only
R11's recorded context slice. Issue #251 repairs the candidate layout described
below; Issue #252 addresses download/detail organization below. Issue #253 adds the
single-decision method/information explanation below; other R11 findings stay open.

### Ordinary Historical Result and Overbid statuses (Issue #307)

The ordinary Summary projects `historical_game_summary.game_result_summary.status`
and `historical_game_summary.overbid_summary.status` through the existing trusted
`Result` and `Overbid` field identities. Nine paired private catalog entries use
Issue #307's exact approved German/English copy. The mapper and renderer remain
the existing authorities; no calculation or exported token is translated.

| Retained status | English display / meaning |
| --- | --- |
| `final_decided` | Result determined; neutral about which party won |
| `currently_decided` | Decided on the current evidence |
| `final_undecided` | Final result; winner undetermined; not a draw claim |
| `in_progress` | Outcome unresolved; not a background execution indicator |
| `final_adjudicated` | Determined by adjudication |
| `unknown_bid_value` | Cannot assess: bid value missing |
| `unknown_game_value` | Cannot assess: game value unavailable |
| `overbid` | Overbid |
| `not_overbid` | Not overbid |

Producer inspection covers `game_result.get_card_point_result_status`,
`overbid.build_overbid_summary`, and structured ending adjudication. In particular,
`declarer_concession.adjudicate_declarer_concession` sets `final_adjudicated` with
a defender winner and without assigning unplayed points. Defender concession,
accepted exposure, open play, open-card throwing and party-wide Claim adjudication
also distinguish adjudicated outcomes from pre-existing decisions. The wording
does not assert normal completion or a particular winning party.

Existing `final`, `complete`, and generic `unknown` mappings remain. Literal Player
names are not enum lookups. Genuinely unfamiliar values retain the localized
technical-details fallback and escaped exact value. Known entries no longer need
incidental fallback-only duplicate rows. Existing dedicated technical details,
including exact `Result status`, and canonical exports remain intact. Other enum
families retain their current behavior, including existing Winner fallbacks.

The strict inventory is **2,133 keys per locale**, including **25 `result.value.*`
keys** (nine additions to 2,124 / 16). Only the exact catalog-count assertion changes;
package discovery/resource expectations need no adjustment. Static routes, POST
routes and forms remain **9 / 73 / 125**, and packaged schemas remain **72**.

#### Regression and validation evidence

Expected and actual initial branch: `bug/307-manual-review-status-labels`.
Expected and actual starting HEAD: `4e975af17f44cfb1c769319a1e9d8cb7abf6a707`;
the initial worktree and index were clean. Product edits are only the two catalogs.

`test_manual_review_status_labels.py` separates real HTTP execution from controlled
presentation fixtures. Its genuine supported Request adapts the repository's
completed Grand example to Anna/Bea/Clara, Anna declaring at 18, D8/D7 discards,
and 30 legal Plays. Bea wins the first 15-point Trick; Anna wins the remaining
nine. Execution retains **105/15 points, declarer victory and settlement 72**.
This equivalent synthetic Request is not the maintainer's original installed file.

The pre-Product run reproduced both incorrect ordinary cells in delivered German
and English HTML: **26 expected failures / 22 passes in 5.71s**. The first repaired
run had **129 passes / six failures in 18.50s**: a new test incorrectly assumed an
existing plural `defenders` Winner translation. The assertion was corrected to
require the actual unchanged Winner fallback and exact technical value, retaining
both winning-party Result cases. The four complete focused modules then passed
**135 tests in 22.14s**. No skips occurred in these runs.

The **20 complete affected modules passed 413 distinct tests in 123.30s**, with
no skips. Earlier passing tests overlap this inventory. Focused Ruff initially
found 11 unbound-loop references in the new synchronous browser helper and five
long test lines; explicit server/script parameters and line wrapping corrected
them. The final complete new regression module passed **48 tests in 6.55s** after
also asserting the literal Player table column. These are repeats within the 413,
not additional distinct coverage. Focused Ruff then passed. The final complete
documentation-sensitive rename module passed **eight tests in 2.44s**, also repeats.

Pre-change canonical SHA-256 values are pinned in the regression:

* Request: `cc27919d83201943c934c7d5713a6a8abcd36d1a248b814f9963d5b418141d16`
* Result: `827059c49d1f2181c1a413b734328a65f030494a554c80a3d606047d6487d3d8`

Validation uses process-selected **CPython 3.13.7**, pytest **9.0.3**, xdist **3.8.0**,
Windows 11 and PowerShell 5.1. Every validation tool invocation has an explicit
**7,200,000 ms tool timeout**. Test caches, temporary homes, browser profiles and
probe evidence are outside the repository under `$E` below. Quick selects its own
external log directory, reported in the completion handoff. Explicit Quick passed
Ruff, schema parity and input examples; `git diff --check` passed and the index
remained empty. Local Full was not run.

```powershell
$E = 'C:/Users/HENNIN~1/AppData/Local/Temp/opencode'
$B = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

py -3.13 -m pytest tests/test_manual_review_status_labels.py -q --tb=short `
  -o cache_dir="$E/307-red-cache" --basetemp="$E/307-red-tmp" --junitxml="$E/307-red.xml"

# The first repaired run used green; the corrected complete rerun used green2.
$suffix = 'green2'
py -3.13 -m pytest tests/test_manual_review_status_labels.py `
  tests/test_guided_frontend_result_presentation.py tests/test_analysis_download_details.py `
  tests/test_frontend_localization_foundation.py -q --tb=short --durations=10 `
  -o cache_dir="$E/307-$suffix-cache" --basetemp="$E/307-$suffix-tmp" `
  --junitxml="$E/307-$suffix.xml"

$modules = @(
  'tests/test_manual_review_status_labels.py',
  'tests/test_guided_frontend_result_presentation.py',
  'tests/test_analysis_download_details.py',
  'tests/test_candidate_comparison_layout.py',
  'tests/test_guided_frontend_web.py',
  'tests/test_guided_frontend_execution.py',
  'tests/test_guided_frontend_json_transfer.py',
  'tests/test_guided_frontend_contracts.py',
  'tests/test_session_recorded_review_web.py',
  'tests/test_task_first_stateful_rendering.py',
  'tests/test_frontend_language_switching.py',
  'tests/test_language_switch_context.py',
  'tests/test_task_first_language_preservation.py',
  'tests/test_language_view_continuity.py',
  'tests/test_language_view_script.py',
  'tests/test_frontend_localization_foundation.py',
  'tests/test_complete_frontend_localization.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_skatmind_rename.py'
)
py -3.13 -m pytest @modules -q --tb=short --durations=15 `
  -n 2 --dist=loadfile --max-worker-restart=0 `
  -o cache_dir="$E/307-affected-cache" --basetemp="$E/307-affected-tmp" `
  --junitxml="$E/307-affected.xml"

py -3.13 scripts/verify_manual_review_status_labels.py --browser $B --output "$E/307-browser"
py -3.13 scripts/verify_manual_review_status_labels.py --browser $B --output "$E/307-browser-final"

py -3.13 -m pytest tests/test_manual_review_status_labels.py -q --tb=short --durations=10 `
  -o cache_dir="$E/307-final-status-cache" --basetemp="$E/307-final-status-tmp" `
  --junitxml="$E/307-final-status.xml"
py -3.13 -m ruff check tests/test_manual_review_status_labels.py `
  tests/test_guided_frontend_result_presentation.py tests/test_frontend_localization_foundation.py `
  scripts/verify_manual_review_status_labels.py

# Final documentation-sensitive complete module, after parallel workers exit.
py -3.13 -m pytest tests/test_skatmind_rename.py -q --tb=short `
  -o cache_dir="$E/307-final-rename-cache" --basetemp="$E/307-final-rename-tmp" `
  --junitxml="$E/307-final-rename.xml"

git diff --check
function python { & py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --cached --stat
git status --short --branch
git rev-parse HEAD
```

The 20-module inventory follows the changed catalog/projection fixture, its direct
download and candidate-table test consumers, guided HTTP/execution/import/state
boundaries, shared Session Result rendering, native/enhanced language return,
strict localization, source package resources, and rename policy. Match/Corpus
rollout callers use separate rollout projections and do not acquire these status
fields. None of the four exclusive modules in `scripts/validation_pytest.py` is
affected: transport rejection, standalone Corpus and Match action placement are
unchanged. No exclusive worker or arbitrary full-regression run is selected.
Local Full is not run under this approved issue routine.

#### Disposable browser observations and acceptance boundary

`$E/307-browser-final/report.json` records four successful cells: German/English with
JavaScript disabled/enabled in actual headless Microsoft Edge **156.0.4314.50**.
The final probe passed in **53.062s** after the helper's explicit-parameter cleanup;
the earlier `$E/307-browser/report.json` also passed all four cells. The observations
and operation counts below are per run, not summed across these repeats.
Each uses the native Request file input and explicit Run button, checks delivered
HTML against actual ordinary DOM cells, and captures screenshots with technical
details closed. Every cell exercises native language return; enabled cells also
return with script enabled. Home/Review navigation and post-server-restart import
of the downloaded Request retain the same result and exact download bytes.

The probe records **20 ordinary Summary observations and 24 native downloads**.
Eight imports and eight explicit executions (initial plus restarted in each cell)
are separate from 12 deliberate language-profile saves/atomic replacements. All
passive phases have **zero POSTs, executions or persistent replacements** and
retain exact state identity and managed-file snapshots. The source hashes,
delivered HTML, screenshots, downloaded JSON and phase accounting are retained in
the evidence directory. No installed UAT environment or real managed data is used.

Completion status: **Locally validated; exact-commit hosted CI and installed
targeted acceptance pending.** Quick is partial validation, not a distribution,
installation-matrix or full-regression certification. The maintainer must verify
exact-commit branch/main `check` and `v1-supported-platform-matrix` gates and a
narrow installed retest using the already exported Request. Keep **#307 and #208
open**, preserve accepted **#292–#306** scopes, and keep formal **UAT-02–12 paused**.
Release preparation is not authorized.

### Single-decision method and information scope (Issue #253)

`analysis_explanation.py` provides one private frozen scalar projection. It reads
the retained Result, never a current draft, final recording hand, sampled World,
Profile, or file. `result_presentation.py` composes its localized detail rows into
Recommendation and Evidence and limits. `result_localization.py` registers those
private labels. The five section identities, #240 ties, #251 columns/precision/order,
and #252 renderer/download ownership remain. No model/version, route, form, option,
method default, producer text, Request/Result or persistence format changes.

| Retained facts | Normal meaning / technical owner |
| --- | --- |
| `recommendation_method_summary.effective_method`, matching recommendation/Search facts | Actual method, not the requested method or diagnostic baseline |
| Existing `result_immediate._effective_immediate` rule | Supports legacy Immediate only when summary and explicit method setting are absent and no Search result exists; consistent explicit Immediate and Auto fallback also qualify |
| `compatible_world_minimax_v1` | Bounded continuations; each selected possible unseen-Card distribution is fully known within that solver |
| `bounded_information_set_policy_search_v1` | Controlled Player's consistent choices at equal visible information against fixed other-Player policies; not joint-defender or unrestricted perfect strategy |
| `effective_method=none` and no Card | No recommendation; diagnostic comparisons do not supply a replacement |
| Unsupported/contradictory method metadata | Neutral missing/unclear explanation; no repair, rejection or success inferred from settings/prose |
| `settings.sample_count` | Per-Card Immediate setting, not a measured unique-world or full-Game count; strict nonnegative integers only in normal explanation, with missing/bool/malformed data unavailable and actual zero retained |
| Matching Search `status`, `stop_reason`, `world_coverage` | Visible bounded completion, fallback or incomplete/stop consequence; complete does not guarantee the real Game |
| `consumed_budget.selected_world_count`, `completed_world_count` | Selected and completed distribution evaluations, retained separately in Technical analysis details; no per-candidate summation |
| `sampled_world_count`, `unique_sampled_world_count` | Draws including repeats versus distinct sampled distributions; multiplicity retains its weight |
| `requested_budget.max_*`, `minimum_comparable_worlds`, timeout | Requested caps/thresholds, distinct from completed work; existing technical rows |
| `settings.sample_count` beside Search | Explicitly named **Immediate sample setting** in technical scope, never Search completion |
| Immediate `win_rate`, `expected_point_swing` | Current-Trick local-side win fraction and points won minus points lost; Null ranks by its role-dependent objective instead of point fields |
| Search contract-success values | Selected modeled cases, not calibrated forecasts of human play |

The normal **Information cutoff mode** row and unconditional Position limitation
list are superseded by **Information used**, concrete known-Skat use, metric scope
and relevant sampling/coverage. The accepted `analysis_mode` remains inspectable once
in Technical analysis details, with visibility and exact method/budget facts. Existing
warning count and original warning text remain under #252's authority. Whole-Historical
aggregates retain their original presentation and limitations.

| Caller / binding | Information statement |
| --- | --- |
| Guided/manual/imported Position | Supplied facts and accepted policy; `post_game_review` alone establishes no saved historical checkpoint or absence of hindsight |
| Current Session Position | Position retained for that execution, not today's form or recording |
| `task_first_session_rendering._analysis_result` with matching `RecordedReviewSourceV1` | Frozen before-Play situation; the review attaches the accepted actual Card without later Plays/final derived Skat |
| Selected typed Match Report through `task_first_match_state` and `recorded_decision_context_sources.match_analysis_explanation` | Reconstructed before-Card view from accepted evidence for that exact Report/Game, without claiming contemporaneous hand entry |

Skat explanation combines `position.skat` in the **local retained Result** with
`skat_visibility`, accepted allowance and role. An unknown empty pair, known visibility
without concrete local Cards, supplied declarer-known Cards and explicit post-game
knowledge are distinct. Permission alone is not use. A defender's privileged input
can already have been removed by the existing local-information producer; the normal
text says no concrete Cards in this analysis rather than denying that the input ever
contained them. No Card identities are added by this explanation.

The narrow source adapters run inside existing page snapshots/locks. They add no
replay, preparation, sampling, Checkpoint collection, token generation, file access,
analysis or Product save. A failed newer attempt does not relabel an otherwise valid
retained source. Existing invalidation, strict reopen, receipt delivery and exact
download bytes remain. See [installed evidence](unified_workflow_visual_contract.md#analysis-explanations-issue-253).

### Artifact and technical-content ownership (Issue #252)

`analysis_download_rendering.py` composes only caller-supplied available hrefs.
Guided state owns its existing precomputed Request/Result bytes; Session execution
owns its separate existing Request/Result endpoints. Match supplies only its selected
Report Result endpoint and existing availability flag. No Request counterpart or
Teacher-source alias is added. The Match serializer remains distinct from the public
guided/Session envelope. Mutable active-result URLs retain latest-active delivery.

The shared renderer no longer appends a blanket raw copy of normal details:

| Original projected content | Rendering owner |
| --- | --- |
| Summary facts, Recommendation values, Alternatives, ordinary Evidence/limits | Original normal section; optional recorded context replaces its existing equivalent Contract/Next Player/Current Trick rows |
| General/Left/Right fixed-policy details | One localized scoped label each inside Technical analysis details; original joined lead/response text unchanged, explicitly English |
| Position recommendation producer paragraph; safe Historical Replay/Information-set Coaching/Tactical limitation items | Technical prose once, preserving exact producer text |
| Unmapped technical detail identities, including Historical method status counts | Technical details once; trusted labels use existing localization |
| Unmapped enum values hidden by the existing localized technical-value placeholder | Exact original value once in Technical analysis details; the normal placeholder remains, not another raw value |
| Public warnings | Existing visible warning count plus exact technical warning list once |

Position's original technical section retains Search method, solution/policy claims,
policy consistency, controlled decisions, requested Trick/depth/world/minimum/timeout
budgets, consumed depth/nodes/states/information sets, deterministic representative,
declaration flags/Matadors/bid, ending, requested/simulated Multi-Step decisions,
stop/Card policy, Policy Comparison request/recommendation, and public artifact names.
Issue #253 moves requested/effective method, fallback, selected/completed/sampled/unique
world counts, the explicitly named Immediate sample setting and accepted information
mode to this same technical owner. Relevant plain-language interpretation is normal
Recommendation/Evidence content. Equal numbers or strings never merge these fields.

Historical's original technical section retains API/schema versions, Player IDs,
played-at and Game ID, Result/Schneider/Schwarz status, game/effective/required values,
settlement completeness/score, Claim proof state/terminal counts, each selected review/
Coaching/Tactical method and public artifact names. Original model tuples, privacy
filtering, values and order remain unchanged. No policy parsing, execution, source
read or export generation occurs during this composition. Match continues to render
its separate curated Report diagnostic object once, without exposing a full Result.

Recording files have separately named recording contexts, and import metadata has
its own disclosure. Source-safe language/disclosure restoration keeps the same
native disclosure count and existing binding; no workflow JavaScript changes are
needed. See [installed evidence](unified_workflow_visual_contract.md#analysis-downloads-and-technical-details-issue-252).

### Responsive single-decision comparisons

Issue #251 opts only Position **Alternatives** into the private
`candidate_table_rendering.py` helper. `result_rendering.py` passes already formatted,
localized, escaped cells; `ResultTableV1`, projection and effective-method selection
are unchanged. The five-column Immediate and seven-column Search comparisons retain
every candidate, column, value and their original order. Guided Position analysis/
review and current/saved Session Results share this path. Full-Historical Immediate,
bounded Search and Information-set chronological tables keep the original renderer.

Above **56em of local component width**, headings and rows stay aligned. At or below
that width, the same rows become expanded labelled blocks: Card, then each existing
metric in order. The container-relative `em` threshold responds to inherited text
size and narrow parents independently of viewport size, without JavaScript. Values
are never copied into another mobile comparison or parsed back into numbers. Local
labels reuse catalog keys, occupy the full metric width and can wrap long compounds;
normal numeric tokens retain their signs, decimals and percent suffixes.

Native caption/column/Card-row headers remain, with page-local IDs, `headers` links
and explicit static table roles for the changed CSS display types. Narrow repeated
visual labels are real HTML marked `aria-hidden`, so each value remains one accessible
cell. No metric gains a Tab stop. Existing focus/source-return and download behavior
are unchanged. [Installed visual evidence](unified_workflow_visual_contract.md#responsive-candidate-comparisons-issue-251)
supersedes the earlier candidate-table limitation on these tested surfaces. Broader
full-Historical table layouts remain separate. Issue #253 supplies R11 method explanations. Issue #252
adds wrapping analysis-download/technical composition without changing this comparison.

### Optional recorded pre-Card context

Saved Session decision Results additionally pass a minimized, immutable private
[recorded decision context](recorded_decision_context.md) into this renderer. It
appears inside Summary before Recommendation, replacing equivalent raw Contract/
Next Player/Current Trick rows while reusing the existing known-score rows once.
The retained Result owns Cards and turn/contract facts; the matching saved source
owns names and indexes. The legitimate full analyzed acting hand is deliberately
visible in normal read-only HTML, with localized accessible symbols. It is not
limited to legal Cards or candidates and does not append the actual Play to the
Trick prefix. No opponent hands, Skat, full Requests or private execution state
are added. Guided/current-position/Historical callers without recorded metadata
remain unchanged; no producer output or exact download bytes change.

### Equal-best Immediate evaluations

For effective Immediate, the existing Alternatives table uses one **Evaluation**
column: best evaluated, equally best evaluated, or lower evaluated. It preserves
retained order and metrics. The primary Recommendation names all exactly equal-best
Cards with localized names, retains the actual Card and quality, and explains that
an equal-best observed Card has no evaluated disadvantage. Suit/Grand ties include
the shared estimated point swing in the normal explanation as well as in the table.
Thus CJ and played SJ both show 6.00 in the R10 example; 14/29 remains in Summary.

`result_immediate.py` reads only retained Result values, reusing the existing
full-precision game/role objective. Null equality is contract-objective equality,
not equality of Card points. No rounding/tolerance or secondary-metric tie-breaker
is added. Registered fixed detail/column labels keep this narrow catalog-backed
explanation visible; raw English producer paragraphs still belong to Technical
details. The deterministic representative is technical context. Its singleton
flag and the existing ordinal ranks remain exact in downloads.

This applies to legacy default-Immediate Results, explicit Immediate and genuine
Auto fallback. Missing/inconsistent method evidence, incomplete/malformed or
nonfinite/bool/duplicate candidate evidence cannot produce a confident tie claim.
Primary Search and diagnostic Immediate baselines do not acquire effective-Immediate
labels. Public acceptance, Search rendering and unavailable meanings are unchanged.

Presentation performs no recording read, replay, simulation, score calculation or
save. Retained old English strings can coexist with the new metric-based display;
their downloads remain byte-identical. Corrected producer reason/summary text
belongs only to a fresh explicit execution, as described in
[Output JSON](output_json.md#recommendation). Source binding, invalidation and
retirement remain unchanged.

Existing normal states such as `complete`, `partial`, `timeout`, `unavailable`,
`final`, `lot_required`, and `not_assessable` remain successful Result pages, not
HTTP failures. Observed Cards are not described as ground truth, and Search is
not described as perfect play or calibrated probability.

## Errors and HTTP behavior

The private browser transport uses these status meanings:

```text
303    accepted POST followed by redirect
400    input, import, or public validation failure
404    unknown route or unavailable retained download
405    unsupported method on a known route
409    stale revision, stale publication, or duplicate execution
413    oversized request or JSON file
415    unsupported media type
500    generic unexpected internal failure
```

Form failures show a translated error summary and translated field-local escaped
messages where a registered field maps to a visible control. Safe submitted Deal
selections remain in separate bounded process-local feedback state for correction;
the accepted Review draft and exact wizard step remain unchanged. A rejected Run
retains and identifies any last successful visible Result. Unexpected, resource, serialization, and
invariant failures expose no internal message, stack, token, path, fingerprint,
private Source Reference, hidden Card, or complete uploaded document.

## Private routes

The documented private action paths are:

```text
/actions/analyze/run-guided
/actions/analyze/import-json
/actions/analyze/run-imported
/actions/analyze/reset

/actions/review/start
/actions/review/update-players
/actions/review/update-deal
/actions/review/update-declaration
/actions/review/update-discards
/actions/review/append-play
/actions/review/undo-play
/actions/review/update-options
/actions/review/back
/actions/review/run-guided
/actions/review/import-json
/actions/review/run-imported
/actions/review/reset
```

The exact authenticated GET download paths and filenames are:

```text
/downloads/analyze/request.json
    skatmind-position-request.json

/downloads/analyze/result.json
    skatmind-position-result.json

/downloads/review/request.json
    skatmind-review-request.json

/downloads/review/result.json
    skatmind-review-result.json
```

Request downloads use the retained canonical Root document. Result downloads use
the full existing public serializer envelope, including public warnings and
artifacts. Both use deterministic finite UTF-8 JSON bytes, LF line endings, and
one trailing newline. They rebuild and execute nothing and are unavailable before
the corresponding retained value exists.

## Security and accessibility

Issue #211 preserves the Issue #210 loopback token/cookie boundary, exact Host
and mutation-Origin checks, duplicate-header rejection, bounded reads,
`Transfer-Encoding` rejection, restrictive CSP, `no-store`, `nosniff`, frame
denial, no CORS, no access log, and no external resource or runtime request.
Issue #214 changes the response policy from `no-referrer`, which makes non-CORS
browser POST Origin serialization `null`, to `Referrer-Policy: origin`. Concrete
same-origin Review POSTs are accepted; missing, null, forged, malformed, and
Host-mismatched Origins remain rejected. Any Referer is origin-only and therefore
contains no source path or query.

Normal workflows use semantic server-rendered forms, visible labels, text status,
keyboard-operable native Card controls, field-linked error summaries, local error
descriptions, native collapsed disclosures, semantic Result headings and tables,
normal download links, visible focus, and responsive packaged CSS. JavaScript is
optional; Issue #220 adds only a progressive language-form preservation enhancement.

## Current boundary and UAT state

Analyze and Review remain usable and process-local. Session, Match Capture, and
Learning Corpus lifecycle integration is implemented by Issue #212, and Issue
#213 provides canonical `skatmind run` and layered CLI help.

Repeated UAT-01 exposed UAT-FINDING-004. Issue #214 implemented the browser-
Origin correction, and maintainer Microsoft Edge verification resolved both
Issue #214 and UAT-FINDING-004. Repeated UAT-01 nevertheless failed. Issue #208
remains open; UAT-02 through UAT-12 remain paused; B-09 and B-07 remain open;
B-06 remains closed; and Package `1.0.0` and Release preparation are not ready.

Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
Issue #216 implements the shared private profile/localization foundation. When
German is active, Issue #220 now renders Analyze, Review, and fixed Result text
through the German catalog. Issue #217 adds localized one-Decision
current/retrospective and one-completed-Game guidance plus safe related links
outside that English region without changing either workflow. Issue #218 adds
accepted-versus-submitted state separation, safe rejected-value preservation,
and localized accessible contextual validation without changing workflow
execution. Issue #219 changes only private stateful creation, profile settings,
and managed display presentation; it does not change Analyze or Review execution.
See [Profile-driven stateful creation](profile_driven_stateful_creation.md).
Issue #220 is documented in [Task-first bilingual stateful workflows](task_first_bilingual_stateful_workflows.md).

## Ordinary numeric presentation (Issues #301 and #302)

Guided and Session ordinary Results now localize typed numeric display values to
the request's German/English locale before HTML rendering. Existing `.6g` means,
`.2f` Immediate best-card point swings and equal-best explanation values, and
scaled `.2f` percentages retain their exact precision and units. German uses decimal
commas; default English retains decimal points. Literal strings and retained
technical prose remain untouched. Following installed feedback, the separate ordinary
Match renderer uses the same private boundary with Python `.2f` for numeric point
cells. Issue #302 renders its exact numeric rates as percentages with `float(rate) * 100`,
Python `.2f`, the request-local decimal separator and one `%`, preserving ordinary
rounding and signed zero. Missing/`None` stays unavailable; booleans and escaped
literal strings are not converted. The metric remains current-Trick local-side wins,
with the existing label and method explanation. The accepted shared
guided/Session projection retains its existing policies. Canonical values and exports
remain unchanged; display rounding does not create ties or alter recommendations.

See [ordinary analysis number formatting](ordinary_analysis_number_formatting.md)
for regression-first HTTP evidence, complete module inventory, browser downloads,
operation accounting, and the pending exact-commit CI/installed acceptance boundary.
