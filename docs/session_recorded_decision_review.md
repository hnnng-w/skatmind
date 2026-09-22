# Review recorded Session decisions

## Status and user path

Issue #221 connects saved Session Decision Checkpoints to the active unified
Session page. On September 11, 2026, repeated maintainer UAT-01 failed: after
recording 30 Plays, the user could not find actionable analysis of that recording,
and the separate manual Review wizard appeared to require entering the Game again.
This implementation addresses that bounded Session path. Issue #208 and unresolved
findings remain open; UAT-02 through UAT-12 remain paused; B-09/B-07 remain open,
B-06 remains closed, and Package `1.0.0` preparation is not ready.

1. From Home, choose **Review recorded games** (`/review/recorded`) and explicitly
   open an individual recording. `/sessions` also remains its recording entry.
2. When an own Play has been observed, follow **Review recorded decisions**, or
   **Inspect recorded decisions** if no saved snapshot is eligible. The list follows
   the recording task, including after all 30 Plays and after Game End.
3. Recognize an own decision by Player name, one-based Trick, Card position within
   the Trick, and actual Card. Select **Review decision** on that row.
4. The page moves to the Result with the source Game/Player/Trick/Card label,
   visible pre-Card situation, actual Card, recommendation, and available assessment.
    After the normal Result, **Downloads for this analysis** exposes the existing
    Request and Result links directly, without opening technical details. They
    contain the exact retained execution bytes.

The German labels are in the packaged translation catalog. Native forms, links,
buttons, disclosures, and downloads work without JavaScript and with a keyboard.
Normal Card recording remains primary during play. No manual Review draft or
re-entry of the Game is required.

Issue #252 gives this Result one **Technical analysis details** disclosure, with
each General/Left/Right policy and original producer paragraph inspectable once.
The accepted Commands/IDs/revisions/Checkpoint metadata remain in separate
**Recording details**, beside the original file link under **Recording file**.
That file is the editable recording; the analysis Result is not a whole-app backup.
Existing source-bound lifetimes, exact bytes, warning authority, success focus and
next decision-return link remain. Native downloads/toggles perform no execution,
Checkpoint collection, Product save or receipt replay. #250 Preview/Cancel/no-op
retention and normal invalidation on accepted changes remain authoritative.
See the [shared ownership inventory](unified_local_frontend_guided_analysis_and_results.md#artifact-and-technical-content-ownership-issue-252)
and [independent-Wheel evidence](unified_workflow_visual_contract.md#analysis-downloads-and-technical-details-issue-252).

Issue #243 styles the existing `#session-result` focus destination with a solid 2px
blue outline and 3px offset, including native redirected focus. Constant block
padding and a small source-paragraph inset separate the caption without reducing
Result/table width or changing layout on focus. The secondary review action now
retains readable text through hover, pressed and keyboard-focus states. The existing
`tabindex=-1`, source-return link, error priority, Request/Result bytes and execution
lifecycle remain unchanged. Installed before/after measurements and forced-colors
emulation are in the [R08 visual evidence](unified_workflow_visual_contract.md#r08-action-focus-and-disclosure-repair).

## Coverage and deterministic variant selection

Issue #251 makes the shared Position Alternatives comparison responsive: aligned
columns at sufficient local width, one expanded Card block with the original labelled
metrics at narrow width or enlarged text. This supersedes the historical five-column
cramping/clipping observation below for the repaired candidate comparison. Full
labels, both equal-best CJ/SJ rows, **100.00% / 6.00 / 6**, seven pre-decision Cards,
HJ/DJ and **14/29** remain from the same retained execution. There is one native
table and one copy of each value; no new disclosure or focus stop is needed to read
alternatives. Current-position Results use the same opt-in; full-Historical tables
remain separate. See the [shared Result contract](unified_local_frontend_guided_analysis_and_results.md#responsive-single-decision-comparisons)
and [independent-Wheel evidence](unified_workflow_visual_contract.md#responsive-candidate-comparisons-issue-251).

The #251 HTTP/browser probe reuses the approved #246–#250 legal trace, including
C10/CJ/DK/D7 after six Tricks and CJ after nine. A native saved-SJ review still
focuses `session-result`; next Tab reaches its original decision-return link.
Same-source opening, de/en changes, resize, native downloads and one #250 no-op
Preview/Cancel preserve exact Session/Checkpoint/Request/Result bytes. Preparation
and execution lifetimes are unchanged; #250 remains completed.

Issue #229 adds chooser opening directly to `/sessions/current#recorded-decisions`.
An unchanged already active source reuses the exact context, Result/source label,
selection key and download bytes; inactive opening uses the existing strict loader.
Legacy explicit reopen/Reload still discards derived execution. This distinction
supersedes neither the #221 exporter nor its evidence cutoff. See
[Home and recorded-game review navigation](home_and_recorded_review_navigation.md).

`session_recorded_review.py` starts from
`GuidedSessionContextV1.document.decision_checkpoints` and the loaded accepted
State. It calls the public `session_api.observe_session_decision_checkpoint()`
wrapper for each saved Checkpoint. It never constructs a missing snapshot or
collects another Checkpoint.

Within that exact accepted history, observed variants are grouped by their
authoritative observed Play revision. One row represents each observed local Play
with a usable saved snapshot. The greatest valid source revision before the Play
wins; equal-source-revision ties retain the first variant in the original stored
tuple. Persistence already defines that tuple's canonical order. Every variant
remains unchanged in persistence. Rows are sorted by the existing one-based
decision index; Requests and assessments are never merged or averaged.

Issue #244 reuses one recorded-decision projection inside the existing Session lock
for the invitation, counts and rows. Before an observed local Play there is no top
invitation or numeric 0/0 panel. `recorded-decisions` remains a visible, focusable
neutral destination with `recorded-review-feedback`, so chooser, direct and rejected
selection links remain meaningful. No perspective and no local Play are different
messages; pending snapshot diagnostics remain separate. With observed Plays, coverage
counts and missing-snapshot explanations remain explicit, without telling the user
to record a Card already present. Separate unavailable snapshot counts are:

| State | Meaning and action |
| --- | --- |
| `pending` | No observed Play yet. Continue normal Card entry when the Card is known. |
| `future` | Undo placed the current history before the snapshot. Only an accepted recording reproducing the decision and Play can make it reviewable. |
| `diverged` | The accepted prefix no longer reproduces the snapshot. Inspect history/correction; this snapshot cannot assess that changed decision. |
| `ended_without_play` | Game End precedes the observed Play. There is no actual Card to compare. |
| Missing snapshot | The recording is supported, but its missing decision-time evidence cannot be recovered here. |

The view links to history, correction, and explicit Session Reload controls.
Sessions with no checkpoints or no own perspective remain supported recordings.
A valid observed ancestor remains reviewable independently of the current hand,
current turn, phase, Live-to-Retrospective promotion, or Historical readiness.

## Immutable information cutoff and execution

Issue #250's normal declarer/declaration correction preview retains the exact
Session source, Checkpoint tuple, execution/source label and Request/Result bytes.
Cancel and no-op Apply retain them too. Real full or partial Apply uses the existing
guided correction boundary: it preserves historical Checkpoint variants, collects
only according to the existing rules, and invalidates the Session Result even if
numeric revision is unchanged. It does not backfill future hand/Skat knowledge or
re-analyze to keep old decisions eligible. Unrelated Match Reports remain intact.
A partial corrected prefix may no longer be ended or reviewable; its removal
warning remains explicit and untimed. Frozen Checkpoints are not an Undo/Redo log.
See [staged correction and evidence](session_undo_and_correction.md#normal-browser-declarerdeclaration-correction-issue-250).

Issue #234's [Unplayed Card summary](unplayed_card_summary.md) is a separate current
full-recording conclusion. It never enters these frozen Requests or retained Results.
Passive display preserves downloads; accepted corrections retain normal invalidation.

Submission calls the public
`session_api.export_session_checkpoint_review_request(state=..., checkpoint=...)`,
which delegates to the existing
`export_session_checkpoint_review_request_v1`. The exporter validates the exact
accepted observation and changes only `analysis_mode` to `post_game_review` and
`actual_card_played` to the accepted observed Card in a new Request. All other
frozen decision-time fields, samples, seed, method, Search settings, and legitimate
information remain unchanged. Later hands, opponent ownership, public revelations,
and final outcomes do not enter that Request.

The returned `RequestDocumentV1` goes directly to the existing
`execute_guided_frontend_review_v1` with `ExecutionOptionsV1()` and normal output
validation. An accepted submission invokes one workflow once, outside both app
and Session locks. There is no batch, background worker, retry, configuration UI,
or invocation during rendering, navigation, language switching, or download.
Current-position analysis is not used as a shortcut: its existing collection and
persistence behavior remains separate.

### Known points in the retained decision Result (R09)

Issue #239 corrects the two existing normal Summary details in the shared private
Position Result projection. Known Declarer points come from
`score_summary.total_declarer_points`; known Defender points come from
`score_summary.total_defender_points`. The retained Result owns both values.
`position.declarer_points` and `position.defender_points` are supplemental inputs
outside the supplied completed Tricks, not totals. Requests, Checkpoints, scoring,
saved recordings and exact technical downloads retain their original values.

For the R09-equivalent Grand decision, the completed Tricks contribute 14 Declarer
points and 15 + 14 Defender points. The normal Summary therefore shows **14/29**
despite supplemental **0/0**. The incomplete HJ/DJ Trick contributes nothing yet.
Reviewing this saved decision after later Plays, Game End or strict reopen still
uses its decision-time Result, never later 14/35 or final 42/78 context. Normal
mutation invalidation still applies; reopen requires explicit review execution.
Rendering never sums Tricks, adds Skat/discards, or calls a score builder.

Literal integer zero remains zero. Defensive partial/malformed presentation
fixtures use the existing localized unavailable value independently for a missing
or non-integer total, including booleans, strings and floats. No supplemental-value
fallback or new import/Schema rule is introduced. Valid canonical Results already
require both totals. The same mapping serves guided Position Results and Session
current-position analysis; Historical and separate Match presentation retain their
existing ownership. Issue #240 adds the bounded R10 implementation below; Issue
#241 adds only R11's visible context slice. Other R11 findings remain open.

### Equal-best saved Immediate decisions (R10)

The shared normal Result now identifies all exactly equal-best Immediate Cards.
In the saved Trick-4/Card-3 example, CJ and played SJ both have estimated point
swing **6.00**, and the localized explanation explicitly gives SJ no evaluated
disadvantage. Its existing **optimal** quality remains. The single candidate table
marks both equally best, while normal Recommendation names both Cards. The exact
download still selects CJ alone and retains ordinal ranks 1/2, flags true/false,
zero loss and zero better Cards. Ordinal rank 2 is a stable ordering position,
not evidence of worse play when objective values are equal.

Equality is exact full-precision game/role objective equality, not rounded display
equality or a whole-game strategy claim. Null uses contract utility; effective
Search and diagnostic Immediate baselines are excluded. Legacy default Immediate,
explicit Immediate and real Auto fallback are supported with defensive method and
candidate checks. No later Plays, completed-recording hand knowledge or inferred
Skat enter the display. Sole-choice and unavailable meanings remain.

Fresh explicit execution corrects the producer's English reason/summary for ties
and zero-looking positive gaps. Retained old Results/Reports/Teacher sources keep
their exact strings, hashes and download bytes; the new private display needs only
their metrics. No saved Session or Checkpoint changes, automatic execution, source
rebinding or new form field is involved.

### Visible pre-Card situation (R11 context slice)

Issue #241 adds a shared private [recorded decision context](recorded_decision_context.md)
inside the normal Summary. Cards, contract, current leader/next Player and known
points belong to the retained Position Result; names and stored Trick/Card indexes
belong to the matching `RecordedReviewSourceV1` and selected Checkpoint. The normal
view shows the full analyzed acting hand and chronological named prefix, including
after Game End or strict reopen/review. For Trick 4/Card 3 this is B HJ / C DJ,
A next, seven Cards including SJ, and the existing 14/29 score rows once.

The renderer replaces equivalent raw context details without reordering top-level
Result sections or changing #240 assessment. It does not replay, collect, prepare,
execute, save or consult today's hand. Opponent/public hands, Skat and other
technical evidence remain outside this compact slice. Exact Requests, Results,
source bytes, downloads and the existing lifetime rules below remain unchanged.

## Private route and form contract

```text
POST /sessions/review-decision
Content-Type: application/x-www-form-urlencoded
managed_handle
expected_revision
decision_selection
_frontend_form_instance  (existing optional renderer instrumentation)
```

`decision_selection` is exactly 64 lowercase hexadecimal characters. It is an
opaque HMAC binding using a private per-context random key, generation, complete
content fingerprint, stored variant ordinal, exact Checkpoint, and observation.
It is resolved only against current server-owned rows. It is neither a raw
Checkpoint ID nor a user-selected revision/fingerprint. Reopen of the identical
file creates a different binding; an equal-integer-revision corrected history
also expires older selections. No selection map or unbounded attempt history is
retained.

`session_recorded_review_form.py` handles transport selection validation and
structured feedback separately from projection and execution. Extra actual-Card,
Request, hidden-evidence, or execution-option fields are rejected. The canonical
registry has **45 POST routes and 78 form definitions**. Its new
`session.review_decision` definition allowlists only the bounded opaque selection
for exact repeated-form feedback targeting. Hidden values are never made visible
or translated.

Normal malformed submissions return same-context `400`; unknown, expired,
superseded, changed-context, and source-file conflicts return contextual `409`.
Success returns `303` to `/sessions/current#session-result`. Feedback is attached
to the exact selected form, or to the decision section if the source selection no
longer exists. Language changes retain the active Session and render the same
feedback/source label in the selected language without executing a review.

## Freshness and Result lifetime

Issue #237's [normal Session Card feedback](session_card_feedback.md) preserves a
still-valid recorded-decision Result, source label, checkpoints and exact downloads
through rejection, source inspection and native language changes. A retained Card
error takes language-return focus at `session-card-error`; it performs no review.
A real accepted Card keeps the ordinary Result invalidation below.

Before execution, the adapter snapshots the exact active context, complete
persistence document, generation, selected Checkpoint and observed Play, and a
private attempt object. The strict direct-child validator and public Session
File Load/fingerprint boundary revalidate the source before execution and again
before publication. An external edit is never silently reloaded, overwritten,
or repaired. Fingerprints follow existing semantic canonical-content identity;
whitespace/key-order differences alone do not identify a different history.

The Session lock protects source snapshots and retained execution/source metadata.
Filesystem work occurs without the app lock. A short nested Session-then-app lock
rechecks exact active binding and publishes execution, exact Request/Result bytes,
and source label metadata together. Activation releases the app lock before
clearing the previous Session, so it never waits for the Session lock while
holding the app lock.

Command application, Undo, correction, and Reload clear retained execution and
its label and invalidate in-flight work. Switching/reopening checks exact context
identity. A newer accepted analysis attempt supersedes earlier work, including
out-of-order completion. Older work cannot replace the newer Result or attach its
label. Successful current-position or Historical publication clears the recorded
source label. A rejected new attempt can retain an earlier still-valid Result,
its original label, and its original download bytes.

Refresh and Request/Result downloads read retained bytes, checking recorded-source
freshness without executing again. A changed/unverifiable source discards derived
execution and offers contextual Reload feedback. Save/reopen restores the saved
Checkpoints, not derived Results. Listing, selection, review execution, and
downloads write no Session, profile, Match, or Corpus data. Explicit language
preference changes retain their existing separate profile behavior.

## Separation from complete Historical review

Issue #233's [knowledge-based entry](session_knowledge_based_entry.md) replaces the
unified time-based mode labels with Player-perspective recording (`live`) and
complete-deal reconstruction (`retrospective`). A past Game can remain `live` and
use these saved decisions after 30 Plays or explicit Game End, without promotion.
Historical blockers now explicitly identify full Historical review/export. The
optional **Switch to reconstruction mode** Command adds no evidence, preserves
phase and cannot reopen initial-deal entry during play/ended. It retains normal
Result invalidation and leaves still-valid ancestor Requests frozen.

The three actions have distinct labels and readiness:

* **Analyze current position** uses the existing current-turn Position exporter.
* **Review recorded decisions** uses saved own-perspective snapshots and accepted
  actual Cards, including in an ended Live recording.
* **Full Historical review** uses the existing completed Retrospective export and
   its required original evidence. Its unavailability does not hide recorded rows.

Issue #244 places current-position/full-Historical controls and detailed blockers
inside one named secondary native disclosure. Retained execution is composed
separately outside that disclosure at the unchanged `session-result` focus target.
Observation, available analysis and retained execution do not imply one another.
In particular, an ended perspective recording can have ten eligible saved decisions
while both exports are unavailable. Its real Trick-4/SJ review retains 14/29, seven
historical hand Cards and equal-best CJ/SJ. The existing HTTP regression exercises
that returned form, passive/language/source-return byte retention and strict reopen
followed by explicit re-execution. Results remain process-local, not restart-persisted.

Shared Result presentation uses only retained public Result fields, with their
supported metrics and units. Method/sample/budget limits and the recorded source
scope are explicit. This is not full three-Player review, an optimal truth label,
final-outcome causality, recovery of missing evidence, or general hidden-hand
inference. Package `0.17.0`, Python `>=3.13`, license, dependencies, Public APIs,
seven Root workflows, Schemas, persistence, examples, and the set of 98 generated
validation scenarios remain unchanged. Issue #240 intentionally changes fresh
producer text within those existing contracts. No issue-specific version constant
is introduced.

## Verification and future affected-path retest

Issue #240 extends the existing genuine R09 HTTP sequence to assert de/en equal-best
CJ/SJ, observed SJ, unchanged 6.0/6.0, singleton flags, ordinal ranks, optimal quality,
supplemental 0/0 and known 14/29 before/after completion and strict reopen. Counters
after real fixture setup verify that passive views, language actions and downloads
execute no analysis or Product save and preserve source bytes and exact downloads.
Scalar tests separately cover multi-Card ties, zero/negative maxima, tied lower
groups, Null roles, positive sub-display-precision differences and malformed
presentation evidence. Real Match exports and Historical Immediate/Search-baseline
composition retain strict old/new Teacher source validation and derived identities.

Installed-Wheel browser verification on September 19, 2026 reused the dependency-free
DevTools harness with Python **3.13.7**, Package **0.17.0**, and headless Edge
**153.0.4234.32**. One disposable synthetic 30-Play recording provided native tie
review with JavaScript off, four native language submissions, exact native Request/
Result downloads, and a second native review of its unique-best first decision
(CA 15.00 versus C10 14.00). After HTTP fixture setup the counters recorded exactly
**two executions and zero Product saves**. The tie Result was reused across de/en,
JavaScript on/off, 1365/390/320 pixels and representative German 320-pixel 200% text.

Evidence and 35 screenshots are retained outside the repository under
`$env:TEMP/opencode/240-browser-02/`; `evidence.json` records installed module/resource
hashes, native request counts, values and exact download hashes. The separately
installed Wheel SHA-256 is
`711cccb58d7fd9a905c236759d761a0daf0f088739a8382061bf8f74ee75892e`.
Screenshots were inspected in addition to DOM assertions. Both best Cards, actual
SJ, unchanged quality and the shared 6.00 estimate are readable in normal
Recommendation without technical disclosure, including by scrolling at 200% text.
The existing five-column table wraps heavily at narrow widths and becomes cramped
and clipped at 320 pixels/200% text; its layout and the existing focus outline are
not an R11 or whole-page usability pass. The normal explanation carries the complete
tie meaning independently of that table. This is synthetic installed-browser
evidence, not maintainer UAT; no broader browser/device acceptance is claimed.

Issue #239's focused presentation regressions execute public Position Requests and
check normal Summary labels in both languages: 14/29, supplemental 5/7 yielding
19/36, explicit-only scores, genuine zero and per-side unavailable fixtures.
They retain source immutability, non-score presentation, alternate-method and
Historical regressions. The real Session web regression records B/C/A with A's
known hand, collects Checkpoints normally, analyzes the current HJ/DJ position,
and reviews A's SJ after later Plays, normal completion and strict reopen. Passive
views, same-source chooser navigation, language changes and downloads execute no
review or Product save and preserve exact bytes and source identity.

Scoped installed-Wheel browser evidence on September 19, 2026 used Python 3.13.7,
Package 0.17.0 and headless Edge 153.0.4234.32 with the existing dependency-free
DevTools harness. One synthetic completed recording supplied one genuine native
no-JavaScript review, then de/en views with JavaScript on/off at 1365, 390 and 320
pixels and representative German 320-pixel 200% text. Native language changes and
same-source opening preserved the Result; native downloads matched its exact
retained bytes. After legal HTTP fixture setup, counters recorded one execution,
zero Product saves, four language POSTs and one same-source opening POST.
The same genuine Result projected through the starting-HEAD builder showed 0/0;
the corrected installed builder showed 14/29 with identical non-score projection.
Module/resource hashes, request counts and 28 viewport screenshots are retained
outside the repository in `$env:TEMP/opencode/239-browser-02/evidence.json` and
adjacent `*-source.png` / `*-score.png` files. Narrow enlarged labels wrap heavily;
the existing focus outline and other UX findings remain separate. This is synthetic
browser verification, not maintainer UAT or general accessibility acceptance.

`tests/test_session_recorded_review.py` covers projection statuses, grouping,
coverage, immutable cutoff/settings, exact identity, source freshness, correction,
Undo/re-recording, promotion, reload/reopen, publication races, failure retention,
and Historical compatibility. `tests/test_session_recorded_review_web.py` uses the
real unified server and returned forms to create a Live recording, submit only
the local initial hand and observed legal Plays, collect snapshots normally,
review after later Plays and all 30 Plays, end, download, reopen, and review again.
The main scenario retains the real exporter and executor. Edge-case tests that
deliberately stop or block execution are distinct from that real execution path.

Local browser inspection on September 11 used Microsoft Edge
`152.0.4191.66` headless, driven through the DevTools Protocol with JavaScript
disabled, at **1365 × 900** and **390 × 844**. Synthetic long Player names and
German decision/source text wrapped without page-level horizontal overflow.
Screenshots were inspected for the decision list and source-labelled Result at
both sizes and for contextual German validation at the narrow size. A native
focused review button submitted with Enter and reached `#session-result`.
Canonical Session bytes remained unchanged. This is synthetic browser validation,
not maintainer UAT.

Evidence is outside the repository under
`$env:TEMP/opencode/session-review-221-visual-1789156271/`:

* `evidence.json` records browser, viewports, measured widths, and keyboard outcome;
* `de-1365x900-recorded-decisions.png` and `de-390x844-recorded-decisions.png`;
* `de-1365x900-session-result.png` and `de-390x844-session-result.png`;
* `de-390x844-validation.png`.

No browser automation or runtime dependency was added to the Package. Real-device
or interactive maintainer acceptance is not claimed by these headless screenshots.

A future focused maintainer retest can open the recorded Game, review an earlier
own decision after the final Play, recognize its source-labelled comparison, and
reopen/review the same saved decision. This does not request a complete UAT
walkthrough now or claim acceptance of Issue #208's umbrella findings. Exact
merged-commit `check` and `v1-supported-platform-matrix` remain required.
