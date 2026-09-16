# Start Session Card entry directly

Issue #231 changes the private unified Session startup interaction to **create or
open → select known initial Cards → save once**. The first Card selector is the
normal task in `setup` and `deal`, even when no Game identity has been recorded.
The actual Product phase remains visible: viewing a fresh selector still means
`setup`, not an accepted Deal.

## Task and optional details

Issue #233's [knowledge-based entry](session_knowledge_based_entry.md) supersedes the
time-based UI labels: `live` means Player-perspective recording, usable during or
after a Game; `retrospective` means complete-deal reconstruction. It adds contextual
hand help and labels the effective accepted mode without changing the direct-start
candidate, task selection, save boundary or Card request limit described below.

`app_web/task_first_projections.py` selects the existing `record_dealt_card` task
before the missing-identity task in setup/deal only. `session_card_entry.py` uses
the same accepted replay for destination, Player and remaining capacity:

* Live starts with the selected local Player's hand, in any of the three seats.
* Retrospective keeps Forehand/Middlehand/Rearhand hand order and exact complete
  32-Card Deal requirements, with or without a local perspective.
* Partial hands and initial Retrospective Skat append only remaining Cards.
* Later phases retain their existing priority, information limits and readiness.

**Game details (optional)** remains in the existing secondary area, with one
**Save game details** form and explicit accepted-Command corrections in history.
The German catalog supplies the corresponding labels. Exact date/time starts
blank; there is no separate metadata confirmation or automatic browser request.
All ten existing Command paths remain reachable under their existing phase rules.

Public and private creation are unchanged: revision zero, setup, empty accepted
Log, one creation save, and the existing separate profile-enrichment boundary.
GET, import, open, Reload, language changes and checkbox selection initialize
nothing. Import itself retains its ordinary explicit import save; opening an old
setup/deal recording preserves its bytes until an explicit successful edit.

## One immutable candidate and one publication

Issue #237's [Card conflict feedback](session_card_feedback.md) explains a rejected
batch from its original accepted source. It may name the failing Card after candidate
progress, but never calls unsaved identity/Card entries accepted or links to them.
The N+1/N history and single-save boundary below are unchanged; native empty/capacity
errors and valid pending choices remain usable through language switching.

The exact existing `/sessions/cards` source/task binding and the entire selection's
basic nonempty/code/duplicate/capacity shape are validated first. Only when the
accepted source is setup/deal, its authoritative task is `record_dealt_card`, and
replayed `game_id` is absent does preparation prepend:

```python
session_api.SetSessionGameMetadataCommandV1(
    expected_revision=state.revision,
    game_id=state.session_id,
    played_at=None,
)
```

The existing public `apply_session_command` wrapper applies this to an immutable
candidate. The selected Cards follow in `get_full_deck()` order, each through its
ordinary Command with the preceding candidate's actual expected revision. Every
Command, including metadata, has the existing pre/post checkpoint collection and
equality deduplication. Accepted prefix records and saved checkpoint variants are
retained exactly; no later knowledge reconstructs or renumbers them.

| Accepted Card submission | Added Commands/revisions | Mutation saves |
| --- | ---: | ---: |
| N initial Cards, identity missing | N + 1 | 1 |
| N Cards, identity already recorded | N | 1 |
| Invalid selection or failed preparation | 0 | 0 |

Thus a fresh ten-Card hand ends at revision **11**: ID at revision 1, Cards at
revisions 2–11. This is not a single batch-level Command or Undo unit. There is no
initialization marker or persisted flag. The disk-saving single-Command adapter
is not called in a loop.

Only the complete candidate reaches `_persist_session_mutation`, once, against
the original content fingerprint. Metadata/Card rejection, checkpoint failure,
stale source, CAS conflict or pre-replacement save failure publishes no candidate
prefix. Accepted state and still-valid Results remain. Only successful save uses
the normal generation change, Result/source-label clearing and in-flight execution
invalidation. The existing optimistic external-writer limitation remains; this
adds no retry, automatic conflict reload, rollback write or cross-file transaction.

An existing custom Game ID suppresses initialization. A timestamp-only accepted
Command stays byte-for-byte intact: the new ID Command has `played_at=None` and
does not resend, normalize or replace the original text. Card preparation does
not generate another identity, consult now, resolve local time or enrich a profile.

## Undo, optional time and later review

Strict-prefix Undo remains Command-based. Undo to zero removes both ID and Cards;
the next valid initial save can supply ID again. Undo to the ID-only prefix keeps
identity, so subsequent N Cards add N revisions. Reopen and correction use actual
accepted state, not a frontend counter. Future/diverged checkpoint variants remain
retained according to the existing lineage contract.

[Local time entry](local_time_entry.md) stays available before and after hand entry:
append a missing timestamp, or explicitly correct the exact accepted metadata
Command. Gap/fold checks, source/profile binding, original-string Keep and suffix
replay remain authoritative. Empty metadata Commands are invalid. In particular,
Remove cannot delete a timestamp-only legacy Command by replacing it with an
unrepresentable empty Command; another correction target is never substituted.
Changing a timezone preference does not retime Product data. An optional provider
problem does not block a valid Card-only action.

[Recorded decision review](session_recorded_decision_review.md) still uses the exact
saved checkpoint plus accepted actual Card. [Recorded progress](recorded_trick_progress.md)
uses accepted Plays. No analysis, historical reconstruction or Game End is automatic.
Historical export still requires stable Game identity, Retrospective complete-deal
evidence and all existing declaration/ending prerequisites. Older later-phase or
ended recordings missing identity retain their actual explicit-recovery limits.
Ending does not require promotion for eligible saved-decision review. Explicit
promotion adds no facts and does not reopen initial-deal entry during play/ended.

## Exact HTTP and language boundary

The existing **8,192-byte** URL-encoded `POST /sessions/cards` contract is unchanged:
`managed_handle`, `card_selection`, repeated `cards`, and optional renderer-owned
`_frontend_form_instance` instrumentation. No Game ID, timestamp, arbitrary Command
or first-hand marker is accepted. No route or registry definition is added:
**59 private POST routes / 103 definitions**, with **1,463** matching de/en keys.

An exact-boundary regression exposed that the baseline registry declared this
limit but the HTTP reader used the larger application limit. The narrowly scoped
`server.py` integration now reads `/sessions/cards` using its existing registry
limit. At 8,192 bytes, malformed Card input reaches ordinary `400` validation;
8,193 bytes receives the existing contextual `413` before preparation or save.
Both preserve source bytes. Normal valid forms retain one save. Other routes are unchanged.

Complete-source HMAC, lifecycle lock, active identity, strict source freshness and
file CAS reject reopened, foreign, stale and equal-revision-different-content forms.
Competing duplicate requests can publish at most one candidate. Feedback remains
contextual `400`/`409`, with safe selected Cards and `303` success returning to
`/sessions/current#session-recording`. Existing cookie/bootstrap, Host/Origin, CSP,
no-CORS and private-path boundaries are retained.

Native no-JavaScript selection/save works. Native language changes retain accepted
and server-retained rejected state; supported unsent checkbox selections require
the existing optional JavaScript envelope. Empty and checked sets retain the same
actual task. Language changes record no identity or Cards. App-owned styles and
native keyboard/focus behavior are reused.

## Focused verification

`tests/test_session_direct_card_start.py` independently starts at real public
revision zero and compares exact Commands/state/checkpoints with sequential public
ID-plus-Card operations. It covers every Live seat, Retrospective perspective/no
perspective, 1/10/remaining Cards, old partial hand/Skat, exact timestamp/custom-ID
prefixes, malformed/forged input, real later rule rejection, Undo to zero/one and
saved future checkpoint variants. Metadata-rejection and checkpoint faults are
explicit injections, separate from rule rejection.

`tests/test_compact_card_entry_web.py` now creates through normal returned forms
without its former metadata call. Its main regression follows the actual creation
redirect, proves revision zero and an immediate Card form, then counts **one real
file-save call and one successful atomic replacement** for eleven exact Commands.
It reopens, records all 30 legal Live Plays without opponent hands, and executes
genuine saved #221 review. It retains partial/reopen, security, competing requests,
real CAS writer and failure/Result lifecycle regressions. Existing-ID candidate
tests in `test_compact_session_cards.py` remain compatibility coverage.

`tests/test_session_direct_card_start_web.py` adds actual Player/phase/form checks,
one unchanged creation save, read-only Reload, empty/checked language restoration,
Undo/reopen, optional time before/after hand entry, exact timestamp-only legacy
transport, invalid empty correction, provider outage, foreign/oversize requests,
genuine retained-Result fault checks, and a legal Retrospective Historical export.
Legal historical fixtures choose observed inputs; transitions, save, export and
review stay real. An old imported partial source is fixture setup through the real
import service; only its active-context placement is test setup. Enhanced-language
HTTP tests construct the documented presentation envelope; browser tests exercise
the actual JavaScript boundary.

The new focused modules passed **52 tests**, including the final HTTP reader-boundary
regression. A broader **957-test** run passed across
compact entry/declaration, local-time, language/validation, seats/creation, #221/#227/
#229 review/progress, transitions/replay/persistence/Undo/checkpoints/export, public
Session API/files/CLI, unified security, standalone Corpus and deterministic public
provenance. Corpus observer and provenance implementations/tests were not changed.
Final complete-check results and actual exit status belong to the implementation
report; the full check remains mandatory after all files are finished.

## Installed-browser evidence

`scripts/verify_session_direct_card_start.py` reuses the dependency-free local
DevTools harness. It rejects checkout imports, verifies 20 installed module/resource
hashes against the final runtime tree, and compares authenticated served CSS/JS
bytes. The existing local-time verifier now locates Session metadata in its secondary
area. Both use real native submission; synthetic names/date/time are assigned to
controls, while Card selection uses Space and submissions/disclosures use Enter.

Windows runs used Python **3.13.7**, Package **0.17.0**, headless Microsoft Edge
**153.0.4234.32** (`@9aab8632678bdbd60c393455e1394ee523ba682d`). The baseline Wheel
was built from clean `aecd151aafff1601b0366bb024e65a98006f4240` before runtime edits.
Evidence is outside Product data under `<temporary-directory>/opencode/`:

* `session-231-before/evidence.json`: completed, 96 measurements.
* `session-231-after-final/evidence.json`: completed, 112 measurements plus
  selected-Card and local-time control screenshots.

All four final language/script combinations actually create and directly save a
first hand. German uses local Rearhand, English local Middlehand; HTTP tests also
cover Forehand. Observed successful initial path after creation:

* Before: `POST /sessions/command`, then `POST /sessions/cards`.
* After: only `POST /sessions/cards`; ten selected Cards produce revision 11.
* Selection alone: zero POSTs and identical source bytes.
* Each hand save: one successful Session replacement. Creation, later time append
  and explicit time correction account for the other three replacements per run.
* Deliberate empty/over-capacity errors and language POSTs are recorded separately;
  rejected selections and time gaps cause no Product replacement. Safe checked
  error input survives native language changes in both script modes. Unsent checked
  input survives the actual JavaScript language round trip.

Each language/script mode measures initial task, empty/capacity errors, selected
hand, next task, expanded optional time and time error at **1365×900**, **390×844**,
**320×800** and **320×800 with 200% text**. Device scale remains 1; each measured font
size is doubled once and restored after measurement. Document/client widths agree
at **1350/1350**, **375/375** and **305/305**. Native single-line date/time fields use
their normal caret scrolling at enlarged text, with no authored clipping or hidden
document overflow. Selection/focus is visible; representative Card text contrast
is **16.19:1** unselected, **13.13:1** selected, and border contrast exceeds **4:1**.
Errors focus the summary; successful Card/time saves focus `session-recording`.

Representative inspected screenshots in the final directory:

```text
native-de-initial-task-1365-1.png
js-de-selected-hand-320-2-controls.png
native-en-capacity-error-390-1.png
native-en-optional-time-390-1-controls.png
native-de-time-error-320-2-controls.png
```

Exact SHA-256 evidence:

| Artifact/resource | SHA-256 |
| --- | --- |
| Baseline Wheel | `d092dcb6c2957ee159e2c5b0eba9e90137653e30751acd980e311a491e8b0037` |
| Verified runtime Wheel | `a00a4595649deccbb09eaa254bc615ce3428f3b07b6bf73ee111d33f99b9aa7a` |
| `session_card_entry.py` | `e80023fa5772a9675f717da8c02183f870ae09ce0615eebb9b143ccb384c5929` |
| `task_first_projections.py` | `eaf2d4447fa8c47540648e8c83c25fbf6a86bb228089448a48717e3d7c97b66c` |
| `task_first_session_rendering.py` | `01e7e1b97d2049488f28befc1708017fd12c305497f5a5fe2b546eaf3b178669` |
| `server.py` | `96a449a2c7fd68dbead988d9531258ccc55a24d29ff7136c517ab14cad765514` |
| `locales/en.json` | `6a8c82314ebe96e1d33df66e4fa4521fd84efe14630f874d377d62162461bd00` |
| `locales/de.json` | `cd2c344dbc83f2ce592193aadcfb17941d51130cd79fb1835935e931cd725322` |
| `assets/app.css` | `3b8257ebb8b9fa8f4587772c41bb5d749970a18da42e617349326e9f1377459c` |
| `assets/workflow.js` | `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298` |

Run with the independently installed Wheel environment's Python:

```powershell
python scripts/verify_session_direct_card_start.py `
  --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --output "$env:TEMP\opencode\fresh-direct-start-evidence" `
  --wheel "<installed-wheel-path>" --phase after
```

Use `before` with an independently installed baseline Wheel. No browser acceptance
item is omitted in this bounded evidence; this is implementation verification,
not maintainer UAT or all-device/assistive-technology coverage.

## Compatibility and remaining gates

Package **0.17.0**, Python **>=3.13**, **AGPL-3.0-only**, existing dependencies
including **tzdata>=2026.4**, optional profile timezone shape, public APIs, Schemas,
core Commands/transitions, CLI, Product persistence, seven Root workflows and
**98 generated outputs** remain unchanged. Match and Corpus runtime are unchanged.
No issue-specific tracking version is introduced.

#229/#230 are closed completed prerequisites following maintainer-confirmed CI.
Issue #231 remains conditional on `check` and `v1-supported-platform-matrix` passing
on the exact merged commit before manual closure. The separate local six-cell
installation matrix is not rerun for this unchanged dependency/installation slice.
#208 and unresolved findings stay open; UAT-01 remains failed, UAT-02–12 paused,
B-09/B-07 open, B-06 closed. No whole-frontend acceptance or Release readiness is
claimed; no Git/GitHub publication action or maintainer UAT is performed.
