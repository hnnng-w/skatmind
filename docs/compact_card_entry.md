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

Display order is independent of accepted chronology:

* Before declaration, Jacks appear first in Clubs/Spades/Hearts/Diamonds order,
  labelled as undeclared Jacks, followed by the four suits.
* Suit/Grand uses existing `is_trump` and Jack strengths. Trumps appear first,
  with Jacks first; remaining suit Cards retain deck rank order.
* Null has four printed-suit groups in existing `A K Q J 10 9 8 7` order.

Capacity guidance and a compact code summary accompany the selector. Without
JavaScript, the summary explicitly describes selection on page load; native checks
still show unsent selection. `assets/workflow.js` updates the pending count and
summary when available. It sends no Card request. App-owned CSS retains native
checked/focus states and reflows without hiding horizontal overflow.

Normal active Session deal, known Skat, discard, and Play use the component.
Normal Match perspective-hand, original-Skat, discard evidence, and single Play
use it. The optional initial-hand editor is beside recording, before history;
other evidence remains secondary. Unknown evidence does not block observed Plays.
Corrections, public hands, events, advanced ordered Play, guided Analyze/Review,
and standalone surfaces retain their meanings. Shared legacy `card_select` and
`card_palette` were not globally replaced.

## Session append: candidate first, save last

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
**N Cards are N ordinary Commands and N Product revisions, with one submission and
one save.** There is no batch marker, new public kind, persistence field, group Undo,
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
transitions and files. It saves ten Cards in one POST/save, reopens partial/complete
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

## Compatibility and gates

Package **0.17.0**, Python **>=3.13**, dependencies, license, public APIs, Command
kinds, Schemas, seven Root workflows, persistence, examples, and generated outputs
remain unchanged. Final full-check results belong to the implementation report.
Both `check` and `v1-supported-platform-matrix` must pass on the exact merged commit
before closure. #221–#225 remain bounded completed slices. #208 and unresolved
findings remain open; UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed.
Remaining knowledge-mode, declaration/scoring, Home/timezone, and Release work is
not completed by this change.
