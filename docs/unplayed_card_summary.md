# Unplayed Cards after complete recording

Issue #234 adds a private read-only conclusion beside the accepted declaration in
Session, selected Match recording and focused Match review. It describes the supplied
complete recorded play, not an independently certified deal or newly entered evidence.

## Accepted-source gate and meaning

`app_web/unplayed_card_summary.py` consumes the page's retained `RecordedTrickProgress`
and accepted `GameDeclaration`. It requires three distinct recorded Players, thirty
distinct canonical Cards, ten Plays per Player, ten completed three-Player Tricks,
contiguous chronological indexes and no incomplete Trick. Malformed bounded inputs
produce no pair. This is deck accounting, not another whole-Game legality validator.

The complement uses `get_full_deck()` order, independently of chronological Play,
seat, perspective or locale. Session reuses the page's already computed replay.
Match obtains progress and declaration from the same selected accepted Game under
the existing Capture snapshot/lock boundary. No hands or hidden worlds are constructed.

| Accepted declaration | Meaning of the two unplayed Cards |
| --- | --- |
| `hand_game=True` | Original Skat, not picked up; no discards. |
| `hand_game=False` | Discarded pair; original Skat is a separate recorded fact. |

This applies to Clubs, Spades, Hearts, Diamonds, Grand and Null. Null does not imply
Hand. The deterministic non-Hand example leaves **SK/SQ**, with original Skat
**D8/D7** when explicitly supplied. **HQ/D8** is another valid original Skat for
the same recorded Plays with an unknown original declarer hand. The final pair
cannot establish either the original Skat or original declarer hand. A separate
Hand example leaves **D8/D7**. At 29 Plays neither example displays a remainder.

Thirty accepted Plays suffice before or after explicit normal Game End. A shortened
ending does not fill missing Plays. Empty and passed Match slots have no pair.
Selected, rejected, failed-save and preview Cards never enter this conclusion.

## Presentation and evidence boundary

`unplayed_card_rendering.py` uses existing accessible Card labels and local
accepted-declaration styling. Issue #247 supersedes the original attribution prose
with concise inline English/German source labels. It adds
no form or large panel above recording. A source-labelled pair replaces contradictory
normal Session unknown-discard wording. Original Skat remains separately labelled.
An exact recorded pair appears once with **Recorded**, including when it agrees with
the conclusion. A derived-only pair appears once with **Derived from recorded play**,
without an additional unqualified absent-input line. Partial supplied membership
is marked **Recorded** beside its Card; only the other Card is marked derived, in
the pair's display order. Conflicting defensive input is retained separately with
an explicit difference message; existing accepted-recording warnings remain visible.
Neither source is silently preferred or certified. Hand uses its no-discard
explanation. Before completion, Session's existing source targets show **Not recorded**
or supplied Cards marked **Recorded**; its empty observation tuples still mean absence.
This does not reinterpret Match's distinct None and known-empty discard modes.

Issue #248 uses the shared printed-suit **C/S/H/D, J/A/10/K/Q/9/8/7** display copy
for these explicitly set-like summaries and accepted/remaining/public hands. This
supersedes previous display order, including Null, but leaves the canonical complement
and source tuples above untouched. Card-level recorded/derived attribution follows
identity, not visual position. Existing read-only symbols share red Heart/Diamond
faces; full names, optional codes and source links remain. See
[Card presentation evidence](compact_card_entry.md#issue-248-current-installed-evidence).

Specialist Match editors remain exact source views: absent evidence still selects
Unknown with no checked Cards; valid known-empty Hand discards remain empty. There
is no Apply/Save deduction action. Technical summaries and downloads retain exact
source data. Match review places the conclusion outside the decision Result and
explicitly distinguishes full-recording knowledge from decision-time knowledge.

Session hands, Skat/discards, Commands, revisions, fingerprints and Checkpoints are
unchanged by reading. Match fields, `original_skat_known`, `discarded_cards_known`
and full-original-deal readiness are unchanged. The existing
`test_complete_trace_does_not_infer_missing_skat_or_discards` remains unchanged.
No pair enters frozen #221 Requests, Match decision preparation, Card palettes,
exports, Learning, old Result bytes or scoring. #227 prefix totals continue counting
only completed recorded Tricks; neither unplayed Card adds points or forces 120.

Accepted corrections, Undo/rewind, reopen and selected-Game changes recompute the
view. A valid S9-to-SK correction changes **SK/SQ → SQ/S9**; 30-to-29 removes only
the conclusion, preserving explicitly recorded evidence. Session partial suffix
replay uses its actual accepted length, not the attempted candidate. Passive
language/navigation preserves Results and #222 previews; real edits retain normal
invalidation. No cache, reload, analysis, Checkpoint collection or Product save is
introduced by this component.

## Issue #247 wording verification

The implementation began clean at `e9e1fc0ec2bb5bf474307804f8d90b62a9d51ecd`
on `bug/247-hand-evidence-labels`, after completed #246. Four current-code regressions
reproduced the misleading Session heading, generic exhausted-hand label and redundant
absent-discard line. The guarded `unplayed_card_summary.py` remains unchanged.

The current #246 legal suffix differs from #247's supplied intermediate-hand table:
it plays A's HA in Trick 5, SA in Trick 6 and D7 in Trick 7. The maintainer explicitly
selected **Actual #246 prefixes** during implementation. Tests therefore retain that
fixture unchanged: **C10/CJ/DK/D7 after six Tricks, CJ after nine, and known-empty
after thirty**, before or after End. They do not relabel it as the archived UAT trace.
The final derived pair remains **S9/H7**; B/C source hands remain absent. The earlier
SJ context remains seven Cards, **14/29**, with equal-best Jacks and exact downloads.

Focused HTTP coverage reuses #234 corrections/rewind, #237 evidence targets, #241
retained context and #246 chronology/party-score fixtures. Real source saves,
strict reopen, Cancel/no-op, language/error feedback and explicit executions remain
covered; fault-injection cases are identified separately. Match's initial-hand
editor retains all original Cards after Play, even Cards no longer selectable for Play.
Passive views preserve exact source/Checkpoint/Request/Result/Report values and
receipt/recovery lifetimes. No additional replay, preparation, save or execution is
introduced to select a label.

See [installed browser measurements](unified_workflow_visual_contract.md#r05-remaining-hands-and-evidence-labels)
for the independent Wheels, scoped coverage and limits. The final full-check log and
actual child exit accompany the implementation report. Both exact merged-commit CI
jobs remain required before #247 closure; #246 remains completed and #208 stays open.

## Historical Issue #234 automated and installed-browser evidence

Preflight started clean on `feature/234-unplayed-card-summary` at
`fc81206ae09bc5abbeab05bfd1754248bc63ad38`. The six requested files (`deck.py`,
`observed_game_contracts.py`, `observed_game_evidence.py`, `session_projection.py`,
`app_web/recorded_trick_progress.py`, `app_web/task_first_match_state.py`) had no
differences from planning archive `aecd151aafff1601b0366bb024e65a98006f4240`.

The affected-path run passed **715 tests in 721.05s**, including observed records/
trace/evidence, Session replay/history/files, progress/recovery, #221/#229/#231–#233,
language/security, standalone Capture/Corpus, packaging and corrected deterministic
public provenance. After additional defensive-prefix and evidence/rewind coverage,
the final feature modules passed **65 tests in 107.89s**. Ruff passed.

The first complete check passed all pre-pytest stages but finished with **8,948
passed, 1 failed, 1 skipped in 4394.00s**: the catalog foundation still expected
1,474 keys. Its exact assertion is updated to 1,484 without weakening order, parity
or placeholder checks; that module then passed **22 tests in 1.79s**. The nested
PowerShell host incorrectly reported outer status zero for that failed run; it is
not success. A separate exit-7 script probe verified direct script-block exit
propagation for the required complete rerun. Validation scripts/configuration are
unchanged. The first transcript is retained as `unplayed-234-final-check.log`; final
corrected-tree results belong to the accompanying report.

The HTTP tests use actual returned forms and successful saves/executions. Perspective
Session creation starts at revision zero; its first hand adds eleven Commands with
one save. Only the local hand is supplied, with an opponent declarer. The thirtieth
Card adds one save, no evidence/metadata Command and no analysis. End/reopen/eligible
saved review invokes one real execution with the exact frozen Request. Passive
language and downloads preserve Session/Request/Result bytes. A genuine duplicate
rejection and a separately labelled injected storage failure both retain 29 Plays.
Match completion, real Report, preview/cancel/apply, rewind, reopen and empty/partial/
passed selection protect exact source, evidence modes, readiness and Report bytes.

`scripts/verify_unplayed_card_summary.py` reuses the dependency-free DevTools harness.
Install a separately built Wheel plus pytest for fixture helpers, then run that
environment's Python with `--browser PATH --output FRESH_DIRECTORY --wheel PATH`.
It rejects checkout imports, compares thirteen installed module/resource hashes with
the checkout, and verifies authenticated served CSS/script bytes. Surrounding legal
setup uses returned-form HTTP, never injected successful Reports or hidden hands.

Final evidence is in:

```text
<temporary-directory>/opencode/unplayed-234-browser-final-tree/evidence.json
<temporary-directory>/opencode/unplayed-234-browser-final-tree/*.png
```

Windows CPython **3.13.7**, Package **0.17.0**, headless Microsoft Edge
**153.0.4234.32** (`@9aab8632678bdbd60c393455e1394ee523ba682d`) completed **240
measurements**, with screenshots and source-tail captures. German/English and
JavaScript on/off cover Session/Match 29 Plays, complete non-Hand and Hand, shortened
Session, empty/passed Match, evidence editors, earlier labelled Reports and recovery.
Viewports are **1365×900**, **390×844**, **320×800**, and representative **200% text
at 320×800**. Computed fonts are doubled once; device scale and browser zoom stay
unchanged. Every document/client width agrees: **1350/1350**, **375/375**, **305/305**.
Narrow enlarged content wraps and uses ordinary vertical scrolling.

Native Space/Enter performs actual Session and Match final-Card **D9** saves, explicit
reviews, Session Undo and Match rewind/Apply. Card saves focus the existing recording
target; Match Apply returns there too. Session Undo retains its existing page-level
return. Selection produces zero POSTs; language produces only its one preference
POST, no Product save or extra execution. Each script-mode run records 71 Session
and 38 Match replacements **including fixture setup**, with exactly one explicit
Session and one explicit Match execution. Both retained downloads remain byte-equal
through passive views. Native preview/cancel keeps the old accepted pair and Report;
confirmed rewind removes the pair and invalidates the Report normally.

Representative inspected screenshots include `js-en-session-non-hand-390-1.png`,
`native-de-session-hand-source-tail.png`, `native-de-match-review-conclusion-320-2.png`,
`native-en-session-report-390-1.png` and `js-en-recorded-evidence-editor-1365-1.png`.

| Installed artifact/resource | SHA-256 |
| --- | --- |
| Wheel | `4cac92e2dff8f3296f1c076bdb9b45dc2aef723f61aaa719693f9b6d5ceba36f` |
| `unplayed_card_summary.py` | `cd65cf9174998b991eb6259c9308e1b9421193925926acf7099e07d46a393071` |
| `unplayed_card_rendering.py` | `d31fdae2ba35b15ad5255ba4b5e43a85063d922895737cd25c22acbbfcec1851` |
| `locales/en.json` | `7d7a0417effb363bdb1e75181f099fefe7e62182aa1c581ff4eaab9199b5497e` |
| `locales/de.json` | `bf85446ed517474c53333af972c18b5ae5cd60ce5934e9388026450bf06fd74d` |
| `assets/app.css` | `3b8257ebb8b9fa8f4587772c41bb5d749970a18da42e617349326e9f1377459c` |
| `assets/workflow.js` | `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298` |

The initial non-isolated optional Wheel rebuild lacked local `setuptools.build_meta`;
the normal isolated build succeeded without changing dependencies. Final browser
evidence uses that rebuilt installed Wheel. No requested bounded browser item is
omitted; other browsers/devices and assistive technology are not covered. These are
implementation checks, not maintainer UAT. Final full-check output/status belongs
to the implementation report; it follows all edits and browser verification.

Package **0.17.0**, Python **>=3.13**, **AGPL-3.0-only**, **tzdata>=2026.4**, #230
profile shape, public/Product contracts, 59 private POST routes/103 forms and 98
outputs remain. Catalogs have 1,484 matching keys. #233 remains completed. Both
`check` and `v1-supported-platform-matrix` must pass on the exact merged commit
before manual #234 closure. #208/unresolved findings remain open, UAT-01 failed,
UAT-02–12 paused, B-09/B-07 open and B-06 closed. No release-readiness claim is made.
