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
legacy/guided/standalone editors and correction dropdowns keep their presentation
kind. No producer, source array, Report, Request, Result or download is sorted.

Normal active Session deal, known Skat, discard, and Play use the component.
Normal Match perspective-hand, original-Skat, discard evidence, and single Play
use it. The optional initial-hand editor is beside recording, before history;
other evidence remains secondary. Unknown evidence does not block observed Plays.
Corrections, public hands, events, advanced ordered Play, guided Analyze/Review,
and standalone surfaces retain their meanings. Shared legacy `card_select` and
`card_palette` were not globally replaced.

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

Match retains existing `set_perspective_hand`, `set_original_skat`, and
`set_discarded_cards` operations. These replace evidence sets, not Session Commands.
Whole-candidate validation, canonical set representation, single-save/no-op behavior,
and Report invalidation remain authoritative.

`unknown` means absent knowledge. `exact` requires ten initial-hand Cards or two
Skat/discard Cards. `known_empty` is offered only for discards, subject to existing
declaration validation. Empty checkboxes never implicitly select a mode. Changing
mode alone saves nothing; explicit Save applies that mode's existing semantics.
Rejected saves retain useful safe input.

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
| `POST /matches/cards` | `managed_handle`, `card_selection`, `operation`, `cards`; evidence also requires `card_evidence_mode` | Existing evidence set operation or one `append_plays` |

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
R06 correction dropdown/consent and remaining R04/other findings remain open.
#247 stays completed. This is bounded presentation implementation, not whole-UAT acceptance.
Both `check` and `v1-supported-platform-matrix` must pass on the exact merged commit
before closure. #221–#225 remain bounded completed slices. #208 and unresolved
findings remain open; UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed.
Remaining knowledge-mode, declaration/scoring, Home/timezone, and Release work is
not completed by this change.
