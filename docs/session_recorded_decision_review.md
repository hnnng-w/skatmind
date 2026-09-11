# Review recorded Session decisions

## Status and user path

Issue #221 connects saved Session Decision Checkpoints to the active unified
Session page. On September 11, 2026, repeated maintainer UAT-01 failed: after
recording 30 Plays, the user could not find actionable analysis of that recording,
and the separate manual Review wizard appeared to require entering the Game again.
This implementation addresses that bounded Session path. Issue #208 and unresolved
findings remain open; UAT-02 through UAT-12 remain paused; B-09/B-07 remain open,
B-06 remains closed, and Package `1.0.0` preparation is not ready.

1. Open a recorded individual Game from **Record one game** (`/sessions`).
2. Follow **Review recorded decisions** near its summary. The visible list follows
   the primary recording action, including after all 30 Plays and after Game End.
3. Recognize an own decision by Player name, one-based Trick, Card position within
   the Trick, and actual Card. Select **Review decision** on that row.
4. The page moves to the Result with the source Game/Player/Trick/Card label,
   actual Card, recommendation, and available assessment. The existing Request
   and Result downloads contain the exact retained execution bytes.

The German labels are in the packaged translation catalog. Native forms, links,
buttons, disclosures, and downloads work without JavaScript and with a keyboard.
Normal Card recording remains primary during play. No manual Review draft or
re-entry of the Game is required.

## Coverage and deterministic variant selection

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

Coverage states show counts of usable snapshots versus accepted local Plays and
explain missing snapshots explicitly. Separate unavailable snapshot counts are:

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

The three actions have distinct labels and readiness:

* **Analyze current position** uses the existing current-turn Position exporter.
* **Review recorded decisions** uses saved own-perspective snapshots and accepted
  actual Cards, including in an ended Live recording.
* **Full Historical review** uses the existing completed Retrospective export and
  its required original evidence. Its unavailability does not hide recorded rows.

Shared Result presentation uses only retained public Result fields, with their
supported metrics and units. Method/sample/budget limits and the recorded source
scope are explicit. This is not full three-Player review, an optimal truth label,
final-outcome causality, recovery of missing evidence, or general hidden-hand
inference. Package `0.17.0`, Python `>=3.13`, license, dependencies, Public APIs,
seven Root workflows, Schemas, persistence, examples, and generated outputs remain
unchanged. No issue-specific version constant is introduced.

## Verification and future affected-path retest

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
