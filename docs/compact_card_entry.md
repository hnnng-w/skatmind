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

The default shared **5em** interactive width accommodates the native control, suit and
two-digit rank; tiles wrap without stretching per suit. Normal Session set entry
(Issues #275/#278) and Play (Issue #281) instead share explicit grid tracks as described below. The shared read-only face
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

## Compact initial Session hand (Issue #275)

The normal setup/deal **player-hand** task retains its compact presentation within
the shared `session-set-entry` variant extended by Issue #278. The existing task
projection and destination select presentation, independently of Card authorization.
One heading names the target Player and original seat. A differing
reconstruction perspective remains a separate, explicitly labelled context. The
existing accepted overview retains effective mode/phase in one secondary line.
Brief German/English guidance supplies remaining capacity and permits partial Save.
Empty accepted-Card blocks are omitted; saved membership and a native correction
link appear after partial Save/reopen. Background knowledge policy and ordinary
Command/Checkpoint mechanics remain documented above and in
[knowledge-based entry](session_knowledge_based_entry.md).

The recording task uses the full panel width without rendering the undeclared-score
placeholder. Issue #278 also applies this treatment to normal original-Skat and
discard entry; later Play retains its score/progress renderer and calculation.
The marker scopes the smaller outer Game title through `main:has(...) > h1`, as that
heading belongs to `templates/app.html`, not the recording panel. Local panel/form
spacing is reduced; content height, feedback and navigation anchors stay natural.

The suit container opts into explicit **8/4/2/1** grid tracks at **48/24/12em**
minimum available widths. Tracks override the inherited fixed tile width, preserving
the existing 16px normal Card text, 44px minimum tile height, native controls,
focus room and selected cues. Filtered groups contain only offered Cards, without
fabricated placeholders. Issue #281 extends these same tracks to normal Session Play;
other Session/Match selectors keep their default layout.
Issue #275 added an optional localized-guidance parameter mapping to the shared helper;
Issue #278 reuses it without changing that helper. Default guidance and other callers'
labels/values remain the same. The four #275 messages brought the catalog from
1,818 to 1,822 keys; eight paired #278 messages bring it to **1,830**. Routes, form identities,
bindings, Command order, persistence, information policy and explicit saving remain.

### Skat and discard extension (Issue #278)

`_set_entry_variant()` in `task_first_session_rendering.py` uses the existing
projected action and destination: setup/deal player hands, `record_dealt_card` to
original Skat in both reconstruction setup/deal and later pickup entry, and normal
`record_discard`. It controls only presentation. `project_session_card_task()` still
supplies selectable Cards, accepted membership and remaining capacity. Original-Skat
choices exclude assigned Cards; discards can include picked-up original-Skat Cards.
Neither domain is changed or reused as the other's exclusion rule.

Each task has one localized heading and short remaining-capacity guidance. Discards
name the declarer. Saved original Skat and saved discards have separate labels and
correction access after partial Save/reopen; empty accepted blocks and revision/append
explanations are absent from the primary flow. Mode/phase move to the accepted
overview. The accepted declaration and its correction controls remain visible.
The common scoped container, title and spacing treatment uses the full panel width
without a pre-play score column. Advanced/correction editors, single-Card Play,
Match selectors, native labels/values, keyboard order, form/feedback identities,
language return and operation-overlay mechanisms retain their existing behavior.

#### Focused developer browser evidence

Clean base: `63fe9c51b968b8238b3e6d644fab79bec49ca8f0` on
`bug/278-compact-skat-discard-entry`. Before/after runs used source-tree imports and
assets, Windows CPython **3.13.7**, headless Microsoft Edge **154.0.4258.62**, and
the existing dependency-free DevTools utilities with fresh isolated profiles/data.
The synthetic Game has all Clubs plus SA/S10 in the initial hand, non-Hand Clubs,
and H7 pending in original Skat; no maintainer UAT data was used.

Measured **CSS** viewports were **1200×900**, **1440×1000**, and **520×844** at the
fresh profile's **100% zoom** (DPR 1, visual scale 1, no emulation/text scaling).
Corresponding outer windows were 1234×997, 1474×1097, and 554×941.

| German task / CSS viewport | Complete suit rows before → after | Selector width before → after | Save document Y before → after |
| --- | --- | --- | --- |
| Original Skat / 1200×900 | 6+2 → 8 | 646.4 → 1127px | 1399.2 → 736.0px |
| Original Skat / 1440×1000 | 7+1 → 8 | 684.2 → 1190px | 1407.2 → 744.0px |
| Discards / 1200×900 | 6+2 → 8 | 646.4 → 1127px | 1432.0 → 824.0px |
| Discards / 1440×1000 | 7+1 → 8 | 684.2 → 1190px | 1440.0 → 832.0px |

At 520px, complete suits use **4+4**; sparse suits contain only genuine choices.
All nine repaired measurements have equal document/client widths and no horizontal
overflow. Text stays 16px, native checkboxes 20px, tile height at least 44px, and
Save height 44.4px. Inspected screenshots show concise context, readable controls,
focus room and Save directly below selection/actual feedback. Narrow views use
ordinary vertical scrolling.

The focused workflow exercised native Space/Tab/Enter, H7 pending through German →
English, partial Save/reopen with one remaining place, a real over-capacity rejection,
safe rejected choices through return to German, the existing error link, correction,
and completion. H7 was subsequently discarded from the original Skat; partial discard
completion restored Play/progress at revision 17. Selection sent no POST; each valid
Card Save called persistence once, and rejection called it zero times.

Completed scratch artifacts are `issue-278-before-c6p_91zx/report.json` and
`issue-278-after-tt7nbgzl/report.json` under `<temporary-directory>/opencode/`.
They retain geometry, screenshots and exact renderer/helper/projection/catalog/asset
SHA-256 identities. Served CSS and workflow JavaScript were byte-checked against the
tested source files. Repaired CSS SHA-256:
`dd7679c086bb02d45da5913bf296fde74bb08882f494a556135880ce30c83f0a`.
An earlier repaired run completed the interactions but stopped on a harness assertion
that confused set-projection order with accepted Command order; the completed run
checks both correctly. No Product change was needed for that harness correction.

This is source-tree developer evidence, not installed-build maintainer acceptance.
**Actual narrow-window 200% browser zoom remains outstanding:** the existing headless
harness has no verified real-zoom control; resizing is not zoom. Keep #278 open for
one short natural installed-build pass through Skat and discards, including that zoom
condition, after integration and green CI. This does not reopen #275–#277 or establish
overall UAT/release readiness. Final full-check results belong to the completion report.

### Historical Issue #275 developer evidence

The following measurements and then-outstanding acceptance notes describe #275's
initial-hand repair only. They are historical evidence, not proof of #278 or a new
request to repeat accepted #275 checks.

Preflight was clean on `bug/275-compact-initial-hand-entry`, HEAD
`b8d70925f6e55171ea64b68caefbe354dd1153c5`. Measurements were captured before source
edits, then on the repaired working tree. Both runs used Windows CPython **3.13.7**,
headless Microsoft Edge **154.0.4258.37**, the existing dependency-free DevTools
harness, separate disposable profiles/data, and real final application responses.
They use source-tree imports/assets, not an independently installed repair.

Matched source-independent conditions: **Synthetic Game 275**, **Synthetic Alex**
in Forehand, perspective recording, revision zero, empty hand, no pending choices
or transient creation receipt, JavaScript disabled. The browser retained its fresh
profile's **100%** zoom; measured DPR and visual scale were both 1. No viewport or
CSS emulation was used in this comparison. CSS viewports came from `innerWidth` /
`innerHeight`, not requested window bounds:

| CSS viewport | Measured outer window |
| --- | --- |
| 1200 × 900 | 1234 × 997 |
| 1440 × 1000 | 1474 × 1097 |
| 520 × 844 | 554 × 941 |

All distances below are CSS pixels, rounded to one decimal. Heading distance is
Game-heading **top to first Card top**; Save Y is document-relative button top.

| Locale / viewport | Heading distance before → after | Selector height before → after | Cards per suit row before → after | Save Y before → after |
| --- | --- | --- | --- | --- |
| German / 1200 × 900 | 897.1 → 203.6 | 700.1 → 454.5 | 6+2 → 8 | 1741.5 → 824.0 |
| German / 1440 × 1000 | 897.1 → 203.6 | 700.1 → 454.5 | 7+1 → 8 | 1749.5 → 832.0 |
| English / 1200 × 900 | 872.3 → 203.6 | 700.1 → 454.5 | 6+2 → 8 | 1716.8 → 824.0 |
| English / 1440 × 1000 | 872.3 → 203.6 | 700.1 → 454.5 | 7+1 → 8 | 1708.6 → 815.9 |
| German / 520 × 844 | 933.0 → 246.8 | 724.9 → 700.1 | 4+4 → 4+4 | 1834.3 → 1144.9 |
| English / 520 × 844 | 883.4 → 246.8 | 724.9 → 700.1 | 4+4 → 4+4 | 1784.7 → 1144.9 |

At the desktop references, heading-bottom-to-first-Card distance decreased from
805.1px (German) / 780.3px (English) to **162.2px**. Normal tile text remains **16px**,
tile height **44px**, and Save height **44.4px**. The Save button remains directly
after the selector; narrow views intentionally require vertical scrolling.

The completed before run has ten measurements; the repaired native run has eighteen,
covering both languages, empty entry, partial Save/reopen, over-capacity rejection,
and long Game/Player names. Native Space selection and Tab order, visible focus,
Enter submission, saved-file preservation, one explicit batch POST, reopen,
safe checked-value retention through rejection/language return, the existing error
link to a Card control, and corrected one-Card append were exercised. Selection
sent no POST. Representative desktop, narrow, saved, rejected and long-name
screenshots were inspected. All repaired measured pages/selectors stayed within
their available width, without clipped or overlapping controls.

A separate four-measurement supplement used **emulated 320 × 800** viewports in
German/English: two-column rows normally and one-column rows with **200% text**
via the existing enlargement helper. Document/client and selector widths agreed.
This is additional reflow evidence, **not actual 200% browser zoom**. An earlier
attempt at a native 390px viewport hit Edge's minimum outer-window size; native
narrow evidence therefore uses the measured 520px viewport above.

Completed local artifacts are `issue-275-before-l_oiilpu/report.json`,
`issue-275-after-iiw2hiax/report.json`, and
`issue-275-supplement-aonluvo1/report.json` under the disposable evidence root.
They retain source hashes, geometry and screenshots without publishing local
authentication or recording paths. Earlier incomplete harness runs are not the
completed authority: one encountered the minimum window size, and another assumed
Session validation focused a fieldset rather than its existing first Card control.

Focused tests inspect final HTTP output and real submissions: the new
`tests/test_compact_initial_hand_web.py`, updated reconstruction expectations,
compact entry/feedback, direct startup, printed-suit presentation, task composition,
later progress/declaration, language preservation, localization and #273/#274 guided
validation/grouping suites. Final full-check results belong to the completion report.

**Outstanding:** actual **200% browser zoom** in both languages (the available
headless harness has no verified real-zoom control), interactive Edge GUI checks,
and the maintainer's installed-build affected-path retest. No new optional help is
introduced; existing native disclosures remain available without JavaScript.
Developer evidence does not establish maintainer acceptance. Keep **#275 open**
pending that retest and outstanding evidence; #208 and overall UAT/release status
are unchanged, and #273/#274 are not reopened.

## Normal Session Play grid (Issue #281)

The existing projected `record_play` primary action now adds `session-play-entry`
to the recording container. This marker and `session-set-entry` share one
`session-card-suits` container rule in `assets/app.css`: **8/4/2/1** columns at
**48/24/12em** minimum available suit-container widths. Only the grid and tile-width
override are shared. Play retains its ordinary headings, spacing, current actor,
current Trick, completed-Trick history and score/progress column.

`project_session_card_task()` continues to supply the exact available/legal subset.
The shared selector still renders the same required native radios, implicit labels,
localized names, printed-suit/rank DOM order, selected state and explicit submitter.
Form identity, pending/rejected values, feedback anchors, language return, overlays
and recording semantics retain their existing paths. Sparse suits remain sparse.
Initial-hand/Skat/discard tasks reuse the same grid; Match and correction callers
do not receive the Play marker.

### Focused developer evidence

The clean base was `cd6be679e8161dcb245a387d5c2c7bc70d5e1837` on
`bug/281-compact-play-card-grid`. Before/after source-tree runs used CPython **3.13.7**,
headless Microsoft Edge **154.0.4258.62**, the existing dependency-free DevTools
utilities, and disposable profiles/HTTP fixtures. The legal live Forehand has all
eight Clubs plus SA/S10, Grand Hand, and unknown opponent hands. The fresh browser
profile stayed at **100% zoom**, DPR 1 and visual scale 1, without text scaling.

| CSS viewport | Actual suit-container width | Complete Clubs rows before → after |
| --- | --- | --- |
| 1440 × 1000 | 663.05px (beside score) | 7+1 → 4+4 |
| 1000 × 900 | 872.22px (score below) | 8 → 8 |
| 520 × 844 | 418.63px | 4+4 → 4+4 |
| 320 × 800, emulated viewport | 225.81px | repaired 2+2+2+2 |

The three native outer windows were respectively 1474×1097, 1034×997 and 554×941.
The complete-suit German and sparse-suit English observations retain 16px Card text,
20px radios, 44px tiles and 44.39px submitters. All six completed repaired
measurements have equal document/client widths and no selector overflow. After
CA/H7/D7, the genuine seven-Club remainder displays 4+3, with CA absent and the
accepted score showing one Trick/11 points. Screenshots confirm focus room and
readable controls. Native Space, ArrowRight, Tab and Enter select exactly CA, send
zero selection POSTs, then one explicit Play POST/one save and advance to Middlehand.

Completed scratch reports are `issue-281-before-_ykrs2qq/report.json` and
`issue-281-after-evwdogiw/report.json` under `<temporary-directory>/opencode/`.
They retain source hashes, geometry and screenshots. Served CSS and workflow
JavaScript were byte-checked against the checkout; repaired CSS SHA-256 is
`c6ead1ca5108418cf815e64c945b07b83e42611a6580af8e3275ab576c75d64a`.
An earlier incomplete repaired run additionally tried 288px emulation: its 273px
client area fell below the existing 288px body minimum and exposed page overflow;
that condition is not claimed as passing reflow evidence.

`tests/test_compact_play_grid_web.py` exercises complete/sparse/follow-suit palettes,
native control semantics, pending language/view return, exact form identity, valid
Save/next actor, unknown-hand candidates, rejected unavailable Cards, accepted-file
preservation and retained progress in both languages. Neighboring compact entry,
set-entry, Match, feedback and progress tests remain regression boundaries.

This is source-tree developer evidence. Actual narrow **200% browser zoom** remains
for the brief installed-build maintainer retest: the existing headless harness has
no verified real-zoom control, and viewport emulation is not zoom. Focused tests and
Quick are local validation only; keep #281 open for exact-commit branch CI,
identical-commit main integration and the installed retest. Wider UAT remains open.

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

### Historical Issue #226 installed browser evidence

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

### Historical Issue #248 installed evidence

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
