# Compact Card selection and batch hand entry

Issue #226 implements one private unified-browser interaction: **select known
Cards together → save once → explicitly record one played Card → continue at the
recording controls with the accepted next Player**.

## Native component and integration

`app_web/compact_card_rendering.py` renders labelled native checkboxes for a set
and native radios for one Play. There is no default Play selection, change-submit,
modifier-key requirement, drag operation, image, external font, or new dependency.
Suit symbols and ranks have localized full accessible Card names. Submitted
values remain exact canonical codes. Selection is presentation only.

Issue #248 supersedes the former undeclared-Jacks/trump-first and Null-specific
**display** ordering. Every compact selector now uses four printed suits, **C/S/H/D**,
each in **J/A/10/K/Q/9/8/7** order. Filtered palettes omit empty suits and contain
only the already authorized subset. Printed-suit headings do not assert follow-suit
legality. DOM and keyboard order agree; `game_type` remains callable-compatible.
Canonical deck order, trump/Null strengths and legal membership are independent.

One shared **5em** interactive width accommodates the native control, suit and
two-digit rank; tiles wrap without stretching per suit. The shared read-only face
has no input or checkbox-sized padding. Validated suit markers color Heart/Diamond
symbols **and ranks** red, Club/Spade dark. Full localized accessible names, optional
raw codes, native checked states and existing focus remain. Forced colors use system
colors instead of literal red.

Multi-select capacity guidance and a compact code/count summary remain. Without
JavaScript, the summary explicitly describes selection on page load; native checks
still show unsent selection. `assets/workflow.js` updates this optional summary.
Single Play has **no duplicate pending-code/count row**: the checked required radio,
actor/current Trick, validation and explicit Save provide feedback. There is no
default Play, change-submit or selection request. The updater tolerates the absent row.

### Set and ordered callers

| Caller | Display boundary |
| --- | --- |
| Session accepted batch and remaining/public hands | `card_set_summary`, display copy only |
| Match initial-hand/original-Skat/discard evidence | `card_set_summary`, separate source sets |
| Recorded decision context hand | `card_set_display_order` over the retained historical hand |
| Unplayed pair and recorded/conflicting pair evidence | Display copy, preserving per-Card attribution |
| `cards_summary`, including Match actual/recommended/ranked candidates | Original supplied sequence |
| Current/completed Tricks, history, correction before/after traces | Chronological order, never set-sorted |

Only existing read-only symbol consumers share face styling. Plain-text summaries,
legacy/guided/standalone editors keep their presentation
kind. No producer, source array, Report, Request, Result or download is sorted.

Normal active Session deal, known Skat, discard, and Play use the component.
Normal Match perspective-hand, original-Skat, discard evidence, and single Play
use it. The optional initial-hand editor is beside recording, before history;
other evidence remains secondary. Unknown evidence does not block observed Plays.
Session corrections, public hands, events, advanced ordered Play, guided Analyze/Review,
and standalone surfaces retain their meanings. Shared legacy `card_select` and
`card_palette` were not globally replaced.

Issue #249 reuses this component for unified Match replacement only, with narrow
optional field/legend/guidance parameters. It submits singular `card`, offers the
unchanged full 32-Card correction domain, and initially selects the accepted old
Card. It does not use the next actor's palette or replay possible choices on render.
Selection is an unsaved proposal; verified preview has no editable palette. Native
Apply alone supplies the existing `confirm_apply=on` for replacement; destructive
rewind retains its required fresh checkbox. See [Match recovery](match_recording_error_recovery.md)
for exact source, effects, validation, installed-Wheel and native browser evidence.

## Session append: candidate first, save last

Issue #231 adds [Direct Session Card start](session_direct_card_start.md): setup/deal
immediately offers the authorized selector. Creation remains revision zero. A missing
Game ID is supplied by an existing ID-only Command in the first successful normal
initial-deal candidate, before the Cards; optional metadata stays secondary.

`app_web/session_card_entry.py` derives one current task from accepted replay and
the task-first projection. A batch has one destination and, where applicable, one
Player. Initial hands allow one through the remaining capacity out of ten, known
Skat and discards one through the remaining capacity out of two. Existing Live/
Retrospective permission, declaration, phase, complete-deal, and ownership checks
remain authoritative. Partial hands, Skat, and discards can be completed after
reopening. Accepted Cards are separate from pending choices; unchecking never
deletes an accepted Command.

The submitted set is validated for nonempty input, codes, duplicates, and capacity
before ordering newly selected Cards by **`get_full_deck()`**. Click order, HTTP
field order, locale, and visual grouping cannot change this order. The accepted
prefix is preserved exactly. Batch order records input, not physical dealing order
or invented timing.

For each Card, preparation collects the current Checkpoint, constructs the existing
typed `record_dealt_card`, `record_discard`, or one-Card `record_play` Command with
the preceding candidate's actual revision, calls public
`session_api.apply_session_command`, requires `applied`, and collects against that
intermediate resulting state. Equality deduplication and different snapshot variants
at one revision are retained. No analysis executes. A candidate failure discards all
intermediate Commands and Checkpoints. The disk-saving single-Command frontend
operation is not called in a loop.

Only the final immutable candidate reaches existing `_persist_session_mutation`:
one existing persistence document, one public `session.files.save_session_file`
call against the original fingerprint, and unchanged same-directory atomic save.
**With identity already recorded, N Cards are N ordinary Commands and N Product
revisions. Missing-ID initial-deal entry adds N+1 ordinary Commands/revisions. Both
use one submission and one save.** There is no batch marker, new public kind,
persistence field, group Undo,
or direct Log replacement. Undo/correction/replay/provenance and #221 lineage retain
their existing interpretation.

Only successful Save publishes context/generation and invokes `clear_execution`,
clearing retained Result/source metadata and superseding in-flight analysis.
Rejected input preserves valid Results. Candidate, Checkpoint, source, CAS, and
pre-replacement save failures publish no prefix and preserve accepted bytes/state.
The existing optimistic external-writer limitation remains: no distributed lock,
retry, rollback write, or stronger cross-process transaction is claimed.

## Match replacement and truthful Play scope

Issue #263 makes this existing evidence entry discoverable. Empty/passed positions
omit the empty Skat/discard wrapper; started Games retain usable unknown evidence,
known-empty modes, real diagnostics and clear actions. The separate initial-hand
summary names its accepted perspective owner and has the native destination
`/matches/position/N#match-initial-hand`. Applicable missing-hand review offers one
shared action to it. One native summary activation may be needed to open it;
there is no second editor, automatic selection, evidence submission or analysis.
See the [conditional remedy map](match_game_navigation.md#discoverable-match-evidence-issue-263).

Initial-hand evidence means the original ten dealt Cards **before pickup/discard**,
including already played Cards from that original set. A non-Hand declarer may
still need original Skat and discard evidence to reconstruct the playable hand.
The existing full-deck candidate domain and canonical replacement/no-op/clear behavior
remain. Issue #268 supersedes the normal mode selector as described below. Complete-trace review
does not acquire an explicit-hand prerequisite.

Match retains existing `set_perspective_hand`, `set_original_skat`, and
`set_discarded_cards` operations. These replace evidence sets, not Session Commands.
Whole-candidate validation, canonical set representation, single-save/no-op behavior,
and Report invalidation remain authoritative.

On the legacy transport, `unknown` means absent knowledge. `exact` requires ten initial-hand Cards or two
Skat/discard Cards. `known_empty` is offered only for discards, subject to existing
declaration validation. Empty checkboxes never implicitly select a mode. Changing
mode alone saves nothing; explicit Save applies that mode's existing semantics.
Rejected saves retain useful safe input. These legacy mode controls are no longer
the normal evidence editor after Issue #268.

Issue #247 corrects the adjacent disclosure caption to **Original Skat and discard
evidence**, matching its actual controls. The separate perspective **initial-hand**
editor stays in place and retains played Cards in its original set. The concise
[read-only pair summary](unplayed_card_summary.md) never checks derived Cards in an
editor, changes Unknown to Exact, or offers a save-inference action. No evidence
mode, binding, disclosure identity, native language/error restoration or Card
presentation/order changes with these labels.

Initial evidence offers the full deck. Its owner's already played Cards can belong
in that initial hand, and original Skat/discards can overlap where validation permits.
Evidence editors never reuse Play exclusions. Normal Match Play submits one Card;
the advanced `/matches/api/v1/operation` input still accepts chronological multi-Play
traces, which are never canonicalized as sets.

Match consumes the existing Position View's selectable Cards and exact/bounded/
unavailable scope. Session's read-only projection reuses exact-hand/public-hand
facts, `get_legal_cards`, `_unplayable_cards`, and ownership-conflict validation.
Exact authorized hands follow the current Trick. Otherwise only played Cards,
proven unplayable Cards, and accepted known/public ownership narrow the deck.
Unknown hands are not reconstructed; future/review information never narrows a live
palette. A bounded candidate is not a recommendation, ownership assertion, or
guaranteed legal Play. Backend validation checks every submission.

Player name/seat, current Trick number, and chronological Trick Cards stay near
selection. Successful PRG clears selection, derives the next actor, and focuses
recording. Unavailable attempted Cards are shown as rejected input, never inserted
as enabled options. #222 recovery and #221 later review stay reachable.

Issue #227 adds [Recorded Trick progress](recorded_trick_progress.md) beside these
controls, reusing accepted replay/recovery facts and the compact Card naming and
symbol convention. History follows recording; the existing focus/fragment, form
identities, submission/save counts and Checkpoint behavior remain intact. Running
totals ignore pending/rejected Cards. Its 24 additional catalog keys bring the
current total to 1,318 without changing the 57-route/93-definition registry.

## Direct Match evidence actions (Issue #268)

The normal selected-Game editors show **Saved evidence** separately from pending
native checkboxes. The selection form has one primary **Save selected Cards**
submitter and no prerequisite mode selector. Selection/toggling makes no request.
The accepted observed Game owns all three operations; its perspective owns the
initial hand, independently of the next actor, Settings and Reports. Empty/passed
Slots have no editors. Later evidence replacement remains supported under full
candidate validation, including complete-trace reconciliation.

| Evidence/context | Selection Save | Separate secondary actions |
| --- | --- | --- |
| Perspective original dealt hand | Exact ten, including already played original Cards | Withdraw when recorded |
| Original Skat, including Hand | Exact two | Withdraw when recorded |
| Undeclared discards | Exact two | Record no discards; withdraw when recorded |
| Hand discards | No nonempty grid or Save | Record no discards; withdraw when recorded |
| Non-Hand discards | Exact two | Withdraw when recorded |

Known-empty discards **before declaration are already legal**. Withdrawal writes
`None`/JSON `null`; the explicit no-discards action writes `()`/JSON `[]`. Required
keys, `_RETAIN` versus `None`, ownership/overlap rules and source attribution are
unchanged. A derived final pair or complete trace never backfills recorded evidence.

Zero-selection Save rejects for both unknown and recorded evidence, including
undeclared explicit-empty discards. It never withdraws or asserts emptiness. A
valid equal-set Save is a no-op. Invalid codes, counts, duplicates, ownership and
trace conflicts reject the entire candidate and retain applicable safe submitted
Cards. Secondary forms contain only regenerated hidden transport plus their explicit
button. They change saved evidence, **not the neighboring grid selection**. Unsent
grid changes need not survive their POST or rejection. There is no new consent,
clear-checkbox, autosave, radio wizard or automatic retry.

### Seven private variants and compatibility

All forms retain URL-encoded `POST /matches/cards`, an **8,192-byte read bound**,
256-field parsing, strict singular fields, optional `_frontend_form_instance`,
authorization and `303 /matches/position/N#match-recording`. Initial boundary
verification found the baseline registry declared 8,192 bytes while its actual
Match read used the generic limit; #268 enforces the specified bound in `server.py`.

Common fields are `managed_handle`, `card_selection`, and `operation`. The new
forms add exactly one `card_evidence_form`, without `card_evidence_mode`:

| Operation | Discriminator | Existing internal mode | Cards |
| --- | --- | --- | --- |
| `set_perspective_hand` | `perspective_hand_selected` | `exact` | Repeated, exact ten |
| `set_perspective_hand` | `perspective_hand_unknown` | `unknown` | Forbidden |
| `set_original_skat` | `original_skat_selected` | `exact` | Repeated, exact two |
| `set_original_skat` | `original_skat_unknown` | `unknown` | Forbidden |
| `set_discarded_cards` | `discarded_cards_selected` | `exact` | Repeated, exact two |
| `set_discarded_cards` | `discarded_cards_unknown` | `unknown` | Forbidden |
| `set_discarded_cards` | `discarded_cards_empty` | `known_empty` | Forbidden |

Only selection forms permit `cards`. Omission is invalid exact input; `cards=[""]`
is invalid Card input. Secondary requests forbid **any** Cards key, including blank.
Mixed marker/mode, wrong operation pairing, unknown markers/fields, duplicate
singular fields/instrumentation, and missing marker plus mode reject. Player,
position and revision remain derived from the strict source binding, not submitted.
The discriminator identifies an action; the existing operation/content/position-
generation HMAC and persistence CAS remain authority.

All legacy definitions and mode-based parsing remain. Legacy unknown/known-empty
may deliberately ignore valid within-capacity Cards; invalid/duplicate/excess Cards
still fail preliminary checks. The lower mapping's exact-empty discard convergence
is unchanged and is not authorization for normal exact-empty Save. Match Play,
Session and correction keep their shared selector behavior.

New selection registry metadata has only editable `cards`, plus internal feedback
identity `card_selection`; secondary forms have no editable fields. Hidden operation,
handle, discriminator and binding are regenerated and excluded from language overlays.
Current-source legacy rejection bridges to its matching new editor/action, otherwise
to recording feedback. Count/Card/candidate errors target the visible fieldset;
secondary errors name the action and target visible form feedback. Trace diagnostics
and error-first opening/focus remain. External changes are not described as unchanged
merely because this request saved nothing.

Without JavaScript, accepted facts and safe rejected selections survive language
return; arbitrary unsent input does not. Existing enhanced language can additionally
retain repeated Cards, explicit zero selection and local disclosure state under the
same manifest/source/lifetime checks. This is not a general draft store.

Genuine mutation keeps one revision/one successful save, then clears Reports and
recovery. Equal-set no-op keeps accepted bytes, Reports and recovery selection/preview;
service entry may clear or replace an old diagnostic. Reload renews the secret and
clears process-local state; real Game switching keeps existing generation rules.
Rendering adds no preparation, inference, execution, Checkpoints, locks or saves.

Inventory changes from **67 routes / 112 forms / 1,802 paired keys** to **67 / 119 /
1,811**, with ordered-key and placeholder parity. Package 0.17.0, Python >=3.13,
AGPL-3.0-only, dependencies, public/persistence contracts and 98 scenarios remain.
See [installed evidence](unified_workflow_visual_contract.md#direct-match-evidence-issue-268).

## Exact private HTTP contract

Issue #237 adds [source-bound Session Card feedback](session_card_feedback.md) to
the two normal Session forms. Real canonical rejections now distinguish recorded
ownership, exact-hand membership, follow-suit and used/unplayable Cards with accepted
evidence links. Palette prevention and one-save candidates remain unchanged. Both
Session routes now enforce their registered 8,192-byte limit; Match and specialist
feedback keep their existing contracts.

Issue #234 adds a compact [Unplayed Card summary](unplayed_card_summary.md) after
thirty accepted Plays, beside the accepted declaration. Hand means original Skat
with no discards; non-Hand means the discarded pair, not original Skat. This labelled
conclusion never populates evidence controls, changes a palette or adds a save.
Rewind to 29 removes it while recorded evidence remains visible under existing rules.

The three new URL-encoded routes have an **8,192-byte** body bound:

| Route | Exact fields after renderer instrumentation | Meaning |
| --- | --- | --- |
| `POST /sessions/cards` | `managed_handle`, `card_selection`, repeated `cards` | Current append task |
| `POST /sessions/play` | `managed_handle`, `card_selection`, one `cards` | Current actor's Play |
| `POST /matches/cards` | `managed_handle`, `card_selection`, `operation`; evidence uses one new discriminator above or legacy `card_evidence_mode`; permitted selections use `cards` | Existing evidence set operation or one `append_plays` |

`_frontend_form_instance` remains optional renderer instrumentation. Other fields
are rejected. Repeated single-Play values and duplicate batch Cards are errors.
Omitted `cards` reaches empty-selection validation or explicit evidence-mode handling.

`card_entry_http.py` uses a domain-separated HMAC binding to complete source content,
managed handle, task/destination, and context. Session includes its generation and
existing per-context secret. Match includes selected Game, position movement
generation, source fingerprint, complete Workspace, and a per-context secret renewed
on Reload. Actor identity is direct for Session and derived from the exact Match
trace. Reopen, equal-revision correction, another item/Game, and accepted progress
invalidate old forms. No selection map or per-tab Product workspace is added.

Dispatch uses the family lifecycle gate, Product lock, and short app identity
check in that order. Session activation now uses the corresponding gate, matching
the existing Match pattern. Strict file freshness precedes preparation; Save retains
CAS. Competing identical valid submissions accept at most one changed save. No-ops
retain Match bytes, revision, and Reports.

Validation returns contextual `400`; source/CAS/storage conflicts use `409`; success
uses `303` to `/sessions/current#session-recording` or selected
`/matches/position/N#match-recording`. Structured Session diagnostic codes map to
fixed localized reasons. Raw exception prose is not shown. Missing or stale bindings
receive recording-area feedback and plain rejected Cards, never restoration into
the current actor's form merely because an ordinal matches.

The registry has **57 POST routes and 93 definitions**; catalogs have **1,294 keys**.
#223 repeated/empty/checked restoration uses exact Card-form identity. Native language
switching retains accepted and server-retained rejected state. With JavaScript,
supported unsent selections remain in the exact task. Without it, browser-only input
cannot be recovered. Hidden transport is regenerated, never copied. Language saves
record no Cards and renew no correction confirmation. Security remains unchanged.

## Focused verification

`tests/test_compact_session_cards.py` compares candidates/Checkpoint tuples with
canonical existing in-memory Commands, including partial input, grouped Skat/
discards, snapshot variants, Live/Retrospective tasks, Suit/Grand/Null, public hands,
and bounded unknown-hand filtering. Real later discard ownership failure is
distinguished from injected Checkpoint failure.

`tests/test_compact_card_entry_web.py` uses real #225 returned creation forms,
transitions and files. Its #231 startup now omits separate metadata submission and
saves ID plus ten Cards at revision 11 in one POST/save, reopens partial/complete
hands, records all 30 legal Plays without opponent hands, and executes genuine #221
review after reopen. Match cases cover initial evidence after its owner's Play,
exact/unknown/empty modes, valid Skat/discard overlap, ordered advanced Plays, genuine
error/recovery, actual Report retention on no-op/rejection, and success invalidation.
Malformed selections, missing/duplicate bindings, concurrency, equal-revision content,
and reopen reject safely. Pre-replacement/Checkpoint fault injection and a real
competing write at Save separately demonstrate no candidate publication. Focused
#221–#225, language/validation/security, replay/files, Match, standalone, and packaging
suites remain regression boundaries.

### Installed browser evidence

`scripts/verify_compact_card_entry.py` reuses dependency-free DevTools and an existing
local Edge executable. Baseline/final runs used separately installed Wheels, Python
**3.13.7**, headless Microsoft Edge **152.0.4191.66**, synthetic names/data, native Space
selection and Enter submission, with JavaScript enabled and disabled. Final loaded
modules/resources are byte-checked against the checkout.

* Baseline ten-Card entry: **ten `/sessions/command` POSTs**.
* Final ten-Card selection: **zero POSTs**; Save: **one `/sessions/cards` POST**.
  Each grouped Skat/discard submission also produced one POST.
* Five consecutive Session Plays crossed a Trick boundary with five explicit
  `/sessions/play` POSTs, no default selection, and recording focus after each.
* JavaScript language switching retained ten unsent Cards with one language POST
  and unchanged Session bytes. No-script multi-selection, real over-capacity
  rejection/retention, and continued submission were exercised.
* Match recorded a Play, saved original-hand evidence containing that Card, and
  continued through a complete Trick using returned controls.
* **36 measurements** cover de/en at **1365×900**, **390×844**, **320×800**, plus
  Session-hand **200% text** at 320 pixels. Each measured font size is doubled once;
  browser zoom/device scale stay unchanged. Final document/client widths agree:
  **1350/1350, 375/375, 305/305**.
* A German 200%-text grid overflow was found and corrected. Representative Card
  text contrast is **13.13:1** selected and **16.19:1** unselected; borders measure
  **6.45:1** and **4.08:1** against their surfaces. Native checked and blue focus
  outlines remain visible. Screenshots include enlarged Cards and success/error focus.

Evidence is outside Product data under
`<temporary-directory>/opencode/cards-226-baseline-verified/` and
`<temporary-directory>/opencode/cards-226-installed-complete/`. It contains
`evidence.json`, `summary.json`, screenshots, POST sequences, geometry, browser data,
and SHA-256 hashes. Final `summary.json` must say `completed: true`. The source baseline
is `392fef89f19c0c93686e5be0b8c6163b1f8bc553`; no implementation commit is generated.

```text
app.css      82fb5bebc4380a25116887248f019c83b85250ef5719795e65ccfa13a72670e5
workflow.js  f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298
```

Invoke the script with the installed verification environment's Python and
`--browser PATH --output FRESH_DIRECTORY --phase before|after`. `after` rejects
checkout imports or differing resources. This optional tooling is separate from
the full check and introduces no runtime/browser dependency. Measurements are
implementation evidence, not all-device/assistive-technology coverage or maintainer UAT.

### Issue #248 current installed evidence

The clean starting HEAD was `340c251b8000c4aa07091b0a3763854f486b29e9` on
`bug/248-card-presentation`, after completed #247. The actual issue and R04 in
#208 were retrieved. Current pre-fix tests reproduced separate Jacks/trumps,
Null's former visual order, the duplicate Play row and unsorted historical hand.
The earlier archive probe is not the current installed baseline.

`scripts/verify_card_presentation.py` uses the existing dependency-free DevTools
transport, independent baseline/repaired Wheels, real loopback returned forms,
and disposable synthetic roots. Run using the respective installed interpreter:

```powershell
& PATH_TO_INSTALLED_PYTHON scripts/verify_card_presentation.py `
    --browser PATH_TO_EDGE --output FRESH_SCRATCH_DIRECTORY `
    --wheel PATH_TO_WHEEL --phase before
```

Use `--phase after` for the repaired Wheel. The script verifies installed Python,
catalog and resource bytes against HEAD/the working tree, plus served CSS/JavaScript.
Completed authorities under `<temporary-directory>/opencode/` are
`248-before-final/` and `248-after-verified/`, with `evidence.json`, exact downloads
and PNGs. Each records **53 scoped measurements**, Windows **Python 3.13.7**,
Package **0.17.0**, headless **Edge 153.0.4234.48**, **de/en and script on/off**.
Each of five primary surfaces has desktop/390/320/200%-text German native checks
and 390px checks for the other language/script cells: Session hand, Session Play,
Match Play, Match initial evidence and saved Session context. Additional states
cover selected red faces, keyboard focus, validation/language and forced colors.
This is a bounded matrix, not a Cartesian workflow replay.

| Computed measurement | Current baseline | Repair |
| --- | --- | --- |
| Interactive widths, 16px face text | 20 widths, 62.6875–73.921875px | **80px**, every suit/rank/state |
| Interactive widths, 32px face text | 20 widths, 103.40625–125.875px | **160px** |
| Red suit and rank | `#18231d` | **`#a31524`** |
| Red contrast, white / selected | Monochrome | **7.806555 / 6.332852:1** |
| Red read-only contrast, shell / panel | Monochrome | **6.864028 / 7.679261:1** |
| Dark contrast, selected / white | 13.134750 / 16.191305:1 | Same |
| Forced-color face contrast | System white/black | **21:1**, `forced-color-adjust: auto` |

Computed ancestor opacity is 1. Complete faces fit their tiles and immediate groups;
targets remain at least 44px high. The existing focused tile outline is 3.2px with
1.6px offset, surrounded by 5.6px group padding and 11.2px gaps; checking does not
resize tiles. Document/client widths agree at **1350/1350, 375/375, 305/305**.
Inspection of matched selection/Play/enlarged-hand/context screenshots, selected
H10/HJ/HA, native rejection, history, keyboard and forced-color screenshots confirms
readable faces and state cues. Long enlarged prose still requires vertical scrolling.
The existing narrow comparison-table limitation remains separate.

Native label clicks, Space, radio arrows, Tab, empty required Play and explicit
Save are exercised. Selection alone sends zero POSTs. Each matched run records
**45 native POSTs**, **20 native Session saves**, **8 native Match saves**, **8 native
profile saves**, and **one native SJ review/execution**. Including returned-form
fixture work, totals are **68 Session saves / 28 Match saves / 21 profile saves**
and **79 existing Match page preparations**. Passive views add no Product saves or
executions. The batch is submitted in actual DOM order, containing Jacks/Aces/Tens;
`CJ/CA/C10/D7` still saves **CA/C10/CJ/D7** with one save. Partial reopen, Skat/discard
append, Match initial membership after CA, evidence replacement/no-op, exact-count
failure and native/enhanced language preservation retain their semantics.

The unchanged #246/#247 sequence has canonical **C10/CJ/DK/D7 after six Tricks**,
**CJ after nine**, ten frozen Checkpoints, and the real retained SJ review. Its
serialized seven-Card hand stays **C10/CJ/SA/SJ/HA/DK/D7**, while display is
**CJ/C10/SJ/SA/HA/DK/D7**; chronological HJ/DJ, candidate order CJ/SJ and 14/29 remain.
Exact deterministic bytes match both installations and previous issues:

```text
Request (1,534 bytes) 05dc65aa713fb37c7b40cd9a4027ce6926881e6bb0c98adaf4256b8a7f14ec94
Result  (9,640 bytes) 76eb05221cab155ff59f734ec568bbead767c2f309d6823546d598412ac545c1
Baseline Wheel       aefc44481fe7bae6381aaf0dab9585cad76a6c536fe27c3f8d991466d22c97f9
Repaired Wheel       1dd87760371b0abf3a53b02aa82b0f9ea85b54f1ebd222dcc101d0e8b84e498d
```

Per-source files/Checkpoints are byte-preserved through passive views and downloads;
independent recordings have different generated identities and therefore different
source hashes. Those exact hashes are retained in evidence. Early incomplete harness
runs corrected opener selection and Result-envelope access. The tighter geometry
probe then exposed a too-wide 5.5em trial in nested enlarged Match evidence; 5em and
the smaller input gap repair it. Earlier runs do not replace the completed authorities.
There was no screen-reader, physical-device or maintainer UAT acceptance.

## Compatibility and gates

Package **0.17.0**, Python **>=3.13**, dependencies, license, public APIs, Command
kinds, Schemas, seven Root workflows, persistence, examples, and generated outputs
remain unchanged. Final full-check results belong to the implementation report.
The #248 baseline and repair retain **63 POST routes / 107 forms**, **1,617 keys per
catalog**, and **98 generated scenarios**; no catalog keys were added or pruned.
Issue #249 subsequently implements the bounded R06 Match dropdown/preview/consent
slice; its catalogs have 1,625 keys. Remaining R06 and R04/other findings remain open.
#247 stays completed. This is bounded presentation implementation, not whole-UAT acceptance.
Both `check` and `v1-supported-platform-matrix` must pass on the exact merged commit
before closure. #221–#225 remain bounded completed slices. #208 and unresolved
findings remain open; UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed.
Remaining knowledge-mode, declaration/scoring, Home/timezone, and Release work is
not completed by this change.
