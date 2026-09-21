# Match recording error recovery

Issue #222 adds a bounded private unified-frontend path:

**Record → understand a conflict → inspect its Trick → preview one Card
replacement or explicit rewind → apply → continue the same Game.**

The original maintainer declaration and trace were unavailable. The automated
late-completion regression is synthetic; it does not reproduce or explain the
specific reported final Queen of Hearts attempt.

## Diagnostic evidence boundary

`observed_trace_diagnostics.py` retains private finite diagnostic values.
`ObservedTraceError` is a `ValueError` subclass raised at the authoritative
`validate_observed_game_trace_v1` seam. Existing English technical messages and
acceptance behavior remain unchanged. The finite reasons are:

* `duplicate`: the conflicting Play and the other occurrence;
* `ownership`: known ownership or exact playable-hand conflict;
* `discard`: a played Card is in known Discards;
* `skat`: original Skat evidence conflicts with the observed Play;
* `wrong_actor`: the recorded actor differs from seat/winner-derived order;
* `follow_suit`: supported effective-suit conflict, with one Card witness.

The diagnostic can retain the actual conflict index, Card, actor, expected actor,
required effective suit, one witness index/Card, and a complete-replay flag. It
does not retain a reconstructed hand. The HTML adapter resolves actors to display
names, escapes values, and translates fixed messages from the matching English
and German catalogs. Unknown failures keep the safe generic validation fallback.
Raw exceptions, paths, internal Player IDs, and arbitrary client metadata are not
diagnostic presentation.

Complete 30-Play validation reconstructs the playable hands and replays every
Play. Consequently a final submission can expose an earlier contradiction. The
location is taken from the validator, never assumed to be Play 30. Rejected
input stays separate from accepted history and is retained as safe form input.
Witnesses distinguish accepted later observations, proposed input, and explicitly
known playable-hand evidence. Neither contradictory observation is declared to
be the original data-entry mistake.

## Read-only early warnings

`find_observed_trace_warning` visits earlier Plays in chronological order. A later
Card observed from the same actor can prove that an effective-suit Card was held
at an earlier off-suit Play. A two-Card evidence subset is passed to the existing
`get_legal_cards`; the required suit uses `get_effective_suit`. Suit and Grand
Jacks are trumps; Null Jacks follow their printed suit. There is no separate
legality engine or printed-suit shortcut.

Only the earliest supported contradiction and its deterministic witness are
shown. Unknown ownership without a witness produces no warning. This is a
derived recording-review warning, not a new validity condition. Existing partial
Workspaces with such contradictions still load without migration or write.
Complete validation remains strict. A replacement accepted as a partial record
may still have a warning, which its preview displays without claiming full repair.

Warning evidence is used only for recording inspection. It never enters an
earlier Decision Request, completes an unknown hand, or runs analysis.

## History, replacement, and rewind

Accepted history is grouped by Trick beside normal Card entry. Every row has a
Card position, Player name, Card, native **Correct this card** and **Rewind from
here** controls, and an anchor for diagnostic links. **Undo last card** selects
the same rewind boundary for the final accepted Play. Declaration and evidence
correction remain linked through their existing controls.

`match_recording_recovery.py` builds a transport-free candidate:

* Replacement changes exactly one Card, preserving its Player, index, timecode,
  full suffix, declaration, evidence, commentary, and response links. It composes
  `rebuild_match_capture_game_v1` and `set_match_workspace_observed_game_v1`.
* Rewind calls `truncate_match_capture_game_plays_v1` with the selected Play's
  prefix boundary, then the same Workspace replacement. It removes that Play and
  its suffix and canonically removes commentary/response links made invalid by
  truncation. It does not truncate first on disk or replay a suffix into storage.

No public Capture operation is added or relabelled. The entire candidate is
rebuilt and validated. Changed Trick winners/points use shared Trick helpers.
Invalid retained suffixes report the actual conflict, save nothing, and offer
explicit rewind. Actors are never reassigned, Plays reordered, extra Cards
swapped, or declarations changed automatically.

Issue #249 replaces only the unified Match single-Card dropdown with #248's
native graphical radios: four printed suits in C/S/H/D order, J/A/10/K/Q/9/8/7
within each, equal-width red/dark faces and full accessible names. Its unchanged
domain is all 32 Cards, not today's next actor's palette. The singular field is
`card`; the accepted old Card is initially selected as a legitimate no-op. Drawing
the palette performs no candidate replay. Whole-suffix validation remains authoritative.

Selection shows the accepted Game/Trick/Card/Player, palette, Preview and Cancel.
A verified preview replaces the editable palette with the exact old/new faces and
names, actual changed-Trick effects, Apply and Cancel. Unchanged winners are named
once; ordinary point changes are omitted for Null without inferring an outcome.
Only positive following-Play counts are shown. The ordinary unchanged-metadata
inventory is omitted; a short annotation-wording caution appears only when comments
or response links exist. Their exact content remains untouched. Accepted and candidate
warnings keep their diagnostics and evidence links. Same-Card preview says No change.

**Choose another Card** reuses select on the same accepted Play, clearing the preview
and invalidating its Apply token without renewing selection creation time. Rejection
has diagnostics and a usable palette, with no valid Apply. Submitted choices retain
their exact source-safe value through rejection and language return. Enhanced unsent
choices additionally require JavaScript; no obsolete overlay can recreate a palette
beside a different verified preview.

Rewind preview shows
retained/removed counts, the first removed Trick/Card position, inspectable exact
Play lists, and removed commentary and response links. Metadata and evidence
retention are explicit. Rewind preparation is separated below the main action row
and explains that it opens a removal preview. It removes the **selected Play and
its continuation**, including undo-last-Card.

Issue #249 supersedes the blanket extra-checkbox UI rule **only for full-suffix
replacement**. Its deliberately activated native Apply submitter is
`<button type="submit" name="confirm_apply" value="on">Apply correction</button>`
(with the existing primary class). The exact Apply token and common fields remain.
There is no hidden/default consent. Rewind keeps the initially unchecked required
checkbox and an unnamed submit button. Confirmation is excluded from safe-value and
language preservation in both cases; language clears checked destructive consent.
Missing, wrong or duplicate confirmation and invalid/expired/foreign tokens remain
rejected. These gestures do not replace source verification, revalidation or CAS.

A same-Card choice is unchanged: no revision increment, Save, or Report
invalidation. Cancel only discards process-local recovery state. Navigation and
language changes perform no correction. Applied rewind has no persistent Undo,
Redo, or automatic restoration. A successful correction does not resubmit the
previously rejected Card.

## Exact source, persistence, and lifecycle

Issue #229's [recorded-review navigation](home_and_recorded_review_navigation.md)
preserves this exact selection, preview, token and creation time through Home,
chooser reuse and same-Game review/recording views. It does not renew expiry or
prepare a replacement preview on navigation. Actual source or position changes,
Reload and accepted edits keep the invalidation below. The compact review selector
uses the same position-selection function; it never picks a different Game merely
to find a reviewable decision.

`app_web/match_recovery.py` owns a bounded process-local selection store and one
preview on each exact `UnifiedMatchContextV1`. At most sixty entry actions cover
the thirty accepted Plays. Random opaque selections bind the exact immutable
Workspace content, retained persistence content fingerprint, selected position,
Game identity, target Play, action, and context-local store. They expire after
thirty minutes and are discarded on Reload, position change, active-item switch,
or successful content change. Equal revisions with different content do not
match. A preview separately binds its proposed Card and single-use Apply token.

Select and preview strictly verify source-file freshness without writing. Apply
resolves the retained selection again, strictly reload-checks its source, and
rebuilds the candidate again. A successful change calls
`MatchCaptureWebContextV1.save_candidate` exactly once with the existing content-
fingerprint CAS and same-directory atomic replacement. Validation, stale-source,
CAS, and pre-replacement Save failures never publish the candidate Workspace in
memory. Successful Apply consumes its selections, so repeated submission cannot
write again.

Lock order for recovery is the Match lifecycle gate, Capture lock, then short
app-lock identity checks. Active Match switching uses the same gate. Filesystem
work holds no app lock. The Capture lock serializes ordinary edits, preview, and
Apply; the lifecycle gate prevents a switch during a recovery write. This is
process-local coordination over the documented optimistic persistence contract,
not a cross-process transaction or distributed lock. The existing final-check to
atomic-replace race remains documented in
[Match Workspace contracts](match_workspace_contracts.md).

After a successful change, the existing Report store is cleared and retained
Result/transfer notices are invalidated. Report downloads and source transfers
therefore cannot use the old Report through this active context. Read-only,
unchanged, and rejected paths preserve accepted Reports. Existing imported Corpus
Snapshots and sources, Sessions, profiles, and other Matches are not mutated.
There is no automatic analysis, materialization, transfer, or Snapshot selection.

Issue #227 enhances this same accepted history with
[Recorded Trick progress](recorded_trick_progress.md). Issue #246 supersedes its
normal cumulative Player/prefix grids with one two-party score and one chronology.
Completed prefixes retain all internal individual/party values for comparisons;
normal rows show actual Card order, winner and Trick value. Incomplete
rows receive no winner/point credit. Summary and diagnostics share the accepted
warning. Preview effects remain separate until a real applied Save; no-op,
cancel, rejection and failure preserve the accepted prefix. Existing
`match-play-{decision_index}` targets, selection fields and confirmations remain.
The shared renderer receives recovery action markup separately and adds no route.
Read-only selected-Game review now shows that same accepted chronology without
issuing selections or rendering an editor. Its warning links reach visible local
rows, with correction links to the existing recording `match-play-N` targets.
Preview, Cancel, Apply consent, same-Card no-op, expiry, source/CAS checks and Save
ownership are unchanged. #245 receipts remain owned by final HTTP delivery, not
these renderers. Only the bounded R05 history/party-score slice is implemented.

## Private HTTP forms and focus

The four added URL-encoded POST routes have exact fields after the common
`managed_handle` binding and renderer-owned `_frontend_form_instance` are handled:

| Route | Fields | Effect |
| --- | --- | --- |
| `/matches/recovery/select` | `recovery_selection` | Resolve an accepted entry; rewind also prepares its removal preview |
| `/matches/recovery/preview` | `recovery_selection`, `card` | Validate one replacement with its entire retained suffix |
| `/matches/recovery/apply` | `recovery_selection`, `confirm_apply=on` | Revalidate and save one change, or consume a no-op |
| `/matches/recovery/cancel` | none | Discard process-local recovery selection/preview |

The browser never submits a replacement Game or Workspace, target index, actor,
timecode, or action override. The Issue-#249 baseline and repair contain 63 POST
routes and 107 definitions (the original #222 inventory was 49/82). Recovery
requests use the existing Capture request-size limit.
Validation returns contextual `400`; freshness, selection, CAS, and recovery Save
conflicts return contextual `409`; successful forms use `303`.

PRG returns to the selected position with `#match-recovery` for preview and
`#match-recording` for Apply, cancel, and ordinary Card entry. Exact history rows
have `#match-play-N` anchors. Missing/stale form feedback stays beside recording.
Native language return preserves the selected Game, recovery state, and safe
rejected values, with localized feedback and the appropriate fragment. This is
a focused Match-path extension of the existing language behavior.

Host/Origin, loopback, cookie/bootstrap, CSP, no-CORS, private files/downloads,
request bounds, and packaged-only assets remain unchanged. Standalone Capture
routes and behavior remain supported. No dependency or Node toolchain is added.

## Verification and compatibility

### Issue #249 current evidence

Clean starting HEAD: `33929aa4352006bf3ace1910d023677bebef532d`, on
`bug/249-match-card-correction`, after completed #248. Live #249 and the consolidated
R06 report in #208 were retrieved. Failing current-code UI regressions reproduced
the dropdown, redundant checkbox, missing choose-another action and irrelevant
annotation inventory before implementation; the archived probe is not current evidence.

`tests/test_match_card_correction_ui.py` reuses genuine returned-form creation and
recording fixtures. B/C/A, Grand declarer B, CK/C7/CA previews C10 with accepted
CA/15 untouched, Cancel retains it, and named-submitter Apply saves C10/14 once,
with A next. Game-2 Pass, return, strict reopen and normal review chronology pass.
Tests also cover exact radio options, submitted selection, malformed fields, absent/
wrong/duplicate confirmation, stale Apply after choose-another, invalid suffix without
truncation, a nonempty preserved suffix, actual timecodes/hand evidence, comments and
response links, Null winner changes, accepted/candidate warnings, no-op and genuine
Report/download retention. Existing expiry/equal-revision/foreign/CAS/failure and
concurrent-Apply tests retain their boundaries; their fault injections are separate
from successful real saves and analysis.

`scripts/verify_match_card_correction.py` uses independently installed baseline and
repaired Wheels, the existing dependency-free DevTools harness, and disposable
synthetic roots. Windows Python **3.13.7**, Package **0.17.0**, headless Edge
**153.0.4234.48** completed de/en and JavaScript on/off correction and rewind flows.
Authorities are `<temporary-directory>/opencode/249-before-02/` and
`249-after-final/`; each `evidence.json` records loaded/served hashes, actual POST
fields, counts, geometry and exact per-source fingerprints. The initial baseline
attempt exceeded its 120-second tool window and is unsuccessful; inspection found
no surviving Python worker before the longer completed run.

The final **29 measurements** cover selection, verified preview, rejection, keyboard
focus and rewind: representative desktop **1365×900**, **390×844**, **320×844** and
**200% computed text**. Document/client widths agree at **1350/1350**, **375/375**,
**305/305**; tiles remain **80px / 160px**, at least 44px high, with full faces and
accessible names. Inspected screenshots show peer primary/Cancel actions wrapping,
separate rewind preparation and visible focus. An error-summary insertion initially
separated Preview/Cancel; the final scoped layout also handles that rejected state.
Vertical scrolling and wrapped enlarged prose remain necessary.

Native labels, radio arrows/Space, explicit Preview, pointer/Enter/Space Apply,
Cancel, choose-another, real duplicate rejection and language return were exercised.
Choice alone sends zero POSTs. Captured preview fields contain singular `card`;
`confirm_apply=on` occurs only on Apply. No language overlay contains the named
submitter. Rewind's required unchecked submission sends zero POSTs, and switching
language after checking it clears consent. Each installation records **80 native
POSTs**, **12 native Match saves**, **20 native profile saves**, and no native analysis.
Including real fixture setup: **40 Match saves**, **36 Session saves**, **28 profile
saves**, **4 Match analyses**, **1 Session review**, **197 existing page preparations**.
Passive phases add zero Product saves/analyses; those preparation counts match baseline.

Every passive Match source (**11,267 bytes**) and genuine Report download (**8,739
bytes**) stays exactly equal through select/preview/cancel/language/rejection/no-op.
A real change normally invalidates that Report. The unrelated ended Session and ten
Checkpoints remain exact within each run. Its real SJ review retains historical
14/29, the seven-Card hand, equal-best CJ/SJ, and identical deterministic downloads:

```text
Request (1,534 bytes) 05dc65aa713fb37c7b40cd9a4027ce6926881e6bb0c98adaf4256b8a7f14ec94
Result  (9,640 bytes) 76eb05221cab155ff59f734ec568bbead767c2f309d6823546d598412ac545c1
Baseline Wheel       00675c0dc21d67c8ac1114115f1714446d1fbc973cd9b31753aeed25b92090b6
Repaired Wheel       900d8e00b8e0d4ffab17a1bd3125ffd2cae7a93b4239cada1870215a7e0a80b1
Repaired app.css     8b3938888a6e7cf93463e0ea7e2b5fdb7c35f51d27fc04e014715550a75336ec
Unchanged workflow.js aa3871d9880326fc27590d80f7f0bf9ebc0a7cf31fd64fc2fd04a1e3932efce1
```

Independent recordings have generated identities, so their Workspace/Session/Report
hashes differ across runs; evidence retains each exact hash. No equality across an
actual saved correction is claimed. No new scorer, recovery operation, wire field,
schema, persistence format or dependency is added. Catalogs change from **1,617** to
**1,625** matching keys; 63 routes / 107 forms and 98 generated scenarios remain.
The known narrow analysis-table limit, untested AT/physical devices, full Cartesian
viewport coverage and maintainer UAT remain outside this implementation evidence.
Final full-check stage/exit/skip evidence belongs to the implementation report.
#248 remains completed; both exact merged-commit CI jobs gate manual #249 closure.
Remaining R06 (including Session correction/discoverability), #208 and other findings
stay open. UAT-01 is unaccepted, UAT-02–12 paused, B-09/B-07 open, B-06 closed.

### Original recovery verification

Focused modules are `tests/test_match_recording_diagnostics.py`,
`tests/test_match_recording_recovery.py`, and
`tests/test_match_recording_recovery_web.py`. Real-server forms cover creation,
declaration, observed-only Card entry, early warning, correction preview/Apply,
resumed entry, 30-Play completion, and Workspace reopen in both locales. A second
sequence retains 29 Plays, attempts the final Card, locates the complete-replay
conflict at Play 2, corrects through rendered controls, and completes the same
Game. Another 29-Play sequence has no supported accepted-evidence warning: the
proposed final Card is the first witness for the conflict at Play 26. Its
diagnostic explicitly separates proposed and accepted evidence, and rendered
correction reaches valid completion. No validation or Save success is mocked in
those sequences.

Adapter edge tests separately inject clock expiry, same-revision alternate
content, an external writer, and Save failure. A CAS-race wrapper invokes the real
Save after a real competing write. They verify byte preservation, accepted-memory
preservation, single-save concurrent Apply, Report retention/invalidation, no-op,
annotation effects, and strict suffix validation. Existing observed trace,
Workspace, standalone Capture, localization/registry/security, packaging, and
Session #221 checks remain regression boundaries.

### Local browser evidence

On September 12, 2026, actual headless Microsoft Edge `152.0.4191.66` rendered
synthetic German recording pages at `1365x900` and `390x844`, with JavaScript both
enabled and disabled. Screenshots were inspected for the evidence warning, linked
Trick history, replacement preview, and continued recording, including the long
synthetic name `Alexandra-Maria von Hohenlohe-Schillingsfuerst`.

The inspected columns and controls remain usable; names and German text wrap.
No horizontal overflow was observed (document widths `1350` and `375`, within
the respective viewports). Native Enter submission with page JavaScript disabled
recorded one additional Card, returned to `#match-recording`, and focused that
section with its top approximately sixteen pixels below the viewport edge.
This is local implementation evidence, not maintainer UAT or assistive-technology
certification.

Sanitized process-external evidence location:
`<temporary-directory>/opencode/match-recovery-visual/`. It contains
`{warning,history,preview,continued}-{1365x900,390x844}-{js,nojs}.png`,
`native-continue-390x844-nojs.png`, and `evidence.json`. These synthetic captures
are temporary local evidence, not packaged assets, persisted Product data, or
generated-output fixtures.

Package `0.17.0`, Python `>=3.13`, dependencies, license, Public API, Root workflows,
Schemas, persistence formats, examples, and generated outputs are unchanged.
Final full-check evidence belongs to the implementation report. Both `check` and
`v1-supported-platform-matrix` must pass on the exact merged commit before
implementation-issue closure.

The whole UAT remains failed. Issue #208 and unresolved findings remain open;
UAT-02 through UAT-12 remain paused; B-09/B-07 remain open and B-06 remains closed.
This implementation does not perform maintainer UAT or claim maintainer acceptance.
