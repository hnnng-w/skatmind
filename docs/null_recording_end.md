# Rule-ended Null recording

Issue #290 ends normal Session and Match Card capture when the declarer first
wins a completed, validated Null Trick. This applies to Null, Hand, Ouvert and
Hand Ouvert. Unknown opponent hands, unknown Skat, absent Matadors, and a
zero-point Trick do not prevent recognition. A partial Trick or zero declarer
Tricks in an incomplete record do not establish an outcome.

## Reproduced boundary

At baseline `d488c4b2505d59bf52dc7b9c8c111e21ae0e71be`, the real returned-form
Session path accepted the ninth Card and still offered the next Card form.
The Session Command boundary and Match append boundary both accepted a tenth
Card. Three new regressions failed before the correction.

The exact fixture has Bea Forehand, Chris Middlehand/declarer and Alex
Rearhand/local perspective. Only Alex's original hand is known:
`CA C10 CJ SA SK SJ HA H9 DK D7`. With ordinary Null, bid 18, the accepted
chronology is:

1. Bea CK, Chris C7, Alex CA: Alex wins.
2. Alex SK, Bea S7, Chris S10: Alex wins under Null ranking.
3. Alex H9, Bea H10, Chris HK: Chris wins.

Shared Trick resolution already computed those winners correctly. Recording
did not derive a terminal loss. The separate completed-Null result helper
requires ten Tricks; explicit Session `normal_completion` requires exactly
30 Plays. Neither existing contract can represent this nine-Card recording
as normal completion without inventing evidence.

## Authoritative derived boundary

`recording_rule_end.py` supplies the private immutable `RecordingRuleEnd` and
`derive_recording_rule_end`. Its two facts are actual `declarer_player_id` and
the first decisive `trick_number`; `decisive_play_count` is three times that
number. Only the existing validated declaration and rule-resolved completed
winner sequence feed the helper. No client winner, point threshold, selected
Card, unfinished Trick, or browser flag feeds it.

| Consumer | Interpretation |
| --- | --- |
| `SessionProjectionV1.recording_rule_end` | Reproducible property of replayed accepted facts |
| `apply_session_command_v1` | Revision conflict first; reject a new `record_play` after the end with existing `game_end_violation` |
| Session task/Card projection and Assistant | No next capture actor/task; history and correction remain accessible |
| Current Position export and Checkpoint collection | Unavailable after the derived end; no fictitious next-decision Checkpoint |
| `ObservedGameTraceSummaryV1.recording_rule_end` | Internal retained result of the existing trace validator |
| Match append | Reject continuation, including a batch crossing the decisive boundary, before publishing any candidate |
| Match position view and first-unfinished selection | Private `rule_ended` state/blocker, no next actor or selectable Cards; skip this Game when suggesting unfinished recording |
| Recorded Trick progress | Actual observed history, counts and decisive end; later archived Cards remain visibly distinguished |
| Match decision preparation | Retain later archived Cards as explicit `after_rule_end` skips, not new legal decisions |

The final accepted Card uses the existing single validated save operation.
Derivation adds no Command, durable flag, second POST, second Save, or analysis.
Existing locking, expected revision, source freshness, CAS and publication
guards remain authoritative. Failed Save does not publish an in-memory end;
passive navigation does not retry it.

## Persistence and compatibility

Session's persisted `phase`, `validation`, `game_complete`, accepted Command Log,
fingerprints and explicit End meanings remain unchanged. These are the existing
authoring/export contract, not a new synonym for rule completion. The derived
recording end is consumed separately by capture and current export eligibility.
Thus an older nine-Card document whose stored phase is `play` loads strictly,
renders the terminal view and rejects continuation without changing its bytes.
Current export can be unavailable even when the legacy stored structural
Position readiness was available. No persisted readiness migration is performed.

Accepted-log replay, prefix reconstruction and Match source validation still
accept previously supported longer archives. They never truncate them on load.
Normal append is a separate guarded operation. Existing explicit correction
preview, first-rejected-suffix policy, removal consent and Match rewind/replacement
validation remain authoritative. Corrections recompute the derived end. Removing
its premise can reopen capture; an independently valid explicit End remains.

Frozen Checkpoints retain exact Request bytes and before-Card facts. Archival
Checkpoint lineage deliberately reconstructs the original contract, including
older post-terminal Checkpoints. Such a Checkpoint is retained but its observation
uses existing `ended_without_play`, making review unavailable. Earlier eligible
Checkpoints remain usable. Session review coverage excludes the archived tail;
the full chronological history displays its actual Cards and a localized notice.
Source mutation retains existing Report/Request/Result invalidation; passive
views retain exact downloads. Opening a completion/history page runs no analysis.

## Presentation and downstream limits

The persistent German/English terminal heading and sentence identify the losing
declarer and decisive Trick. Session offers the existing recorded-decision link
and corrections. Match retains the selected Game, offers history/decision
inspection and explicit navigation to the first unfinished Game, and leaves the
other 35 Slots untouched. Its aggregate presentation separately counts rule-ended
short Null Games. `complete_play_trace_count` still means 30 actual recorded
Cards; neither it nor Trick totals are inflated.

The exact fixture remains nine Cards, three completed Tricks, one declarer Trick
and two defender Tricks. Current-position analysis is unavailable. Earlier
per-decision analysis retains its existing method/evidence rules. Null
`whole_game_rollout` remains explicitly unsupported, including its existing
unsupported-operation feedback; no fallback or new Null algorithm is enabled.

A known loss does not make a partial record eligible for existing full
Historical export, Match Historical materialization, or full settlement. Those
operations keep their independent evidence/end prerequisites and report
unavailability. No concession, exposure, remaining points, hidden ownership,
unplayed Tricks or incompatible `normal_completion` is fabricated. Supported
full ten-Trick Null results and explicit endings retain existing settlement.
Suit/Grand play is unaffected, including continuation beyond 61 points.

## Contract and inventory delta

There is no public API field, Root workflow, persistence document, Schema,
example or generated-output scenario change. The internal additions are the
typed result/property, Match position-view `recording_rule_end` attribute,
private `rule_ended` state/blocker, and preparation `after_rule_end` skip reason.
Derived Python attributes are not added to the existing serialized projection
or trace documents. The private Match position-view serialization exposes the
new state/blocker through its existing fields. No schema mirror is needed.

Inventories were derived from the actual registry/catalog definitions:
72 POST routes and 124 form definitions are unchanged; paired ordered catalogs
increase from 2,025 to 2,033 keys. The eight new keys are
`recording.null_end.{archive,detail,match_count,title}`,
`recordings.skip.after_rule_end`, and
`task.match.{blocker,next,status}.rule_ended`. Existing
`task.match.all_complete` wording now includes rule-ended Games.
The current schema/resource definition count is 72, with six Session examples
and 102 generated-output scenarios; all three inventories are unchanged here.

## Verification

`tests/test_null_recording_end.py` and `tests/test_null_recording_end_web.py`
cover the exact eight/nine boundary, actual Grand/declarer/Null correction with
removal consent, all four valid variants, all perspectives, decisive actor
positions, Tricks 1/9/10, a zero-point loss, rejected/stale submissions,
cross-boundary batch rejection, saved prefixes and longer archives, exact earlier
and archival Checkpoints, native HTTP, source conflict, failed atomic replacement,
one successful durable write, passive reads, preserved downloads, correction/Undo,
independent explicit ending and a full-length Null win. Existing score tests now
construct longer Null histories as archives instead of illegal new continuation.
Complete affected modules, the strict rename inventory, executable packaging
smoke assertions, and explicit final Quick are reported in the implementation
handoff. Local checks do not replace exact-commit hosted CI or installed UAT.

`scripts/verify_null_recording_end.py` reuses the dependency-free local Edge
DevTools harness and disposable HTTP fixtures. The successful checkout-source run
used Python 3.13.7 and headless Edge 155.0.4283.45, JavaScript enabled and natively
disabled, at 1365x900 and 390x844. Its 36 page measurements and inspected screenshots
cover eight Cards, native Space/Enter HK submission, persistent terminal state,
history/decision navigation, German/English return and reopen. It additionally
builds the nine-Card accepted source using the actual baseline transition source
from read-only Git inspection, then opens it without a subsequent Save.

Successful evidence resides outside the repository at the disposable
`opencode/null-290-browser-2/evidence.json` and sibling PNGs. Product writes were
separated from profile writes:

| Operation | Session | Match |
| --- | ---: | ---: |
| Explicit fixture writes | 28, including two pre-fix source imports | 22 |
| Accepted decisive Play writes | 2 | 2 |
| Rejected duplicate requests | 2 | 2 |
| Writes from rejected requests | 0 | 0 |
| Product writes from passive navigation/reopen | 0 | 0 |
| Automatic analysis calls | 0 | 0 |

Profile creation/preferences account for four fixture and nine language writes,
separately from Product writes. Earlier browser attempts exposed only verification
harness setup issues (test import path, then the browser's initial German locale);
they are not counted as successful evidence. Narrow viewport evidence is not
browser zoom, physical-device testing, or maintainer UAT.

Issue #290 and #208 remain open pending their respective acceptance. #289 stays
closed. All implementation changes are left uncommitted for the maintainer.
