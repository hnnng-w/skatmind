# Choose Session recording by available Card knowledge

Issue #233 supersedes the unified frontend's former **During play / After the game**
choice. It changes presentation and narrowly scoped private validation prose, not
the existing capture-mode, phase, information-policy or persistence contracts.

## Choose the evidence path

**Which Cards can you supply?** offers native radios with unchanged `capture_mode`:

| Visible path | Canonical value | Required initial evidence |
| --- | --- | --- |
| Player-perspective recording | `live` | One explicitly seated local Player and that Player's ten initial Cards. |
| Complete-deal reconstruction | `retrospective` | All three ten-Card initial hands and the original two-Card Skat before normal declaration. |

Matching German labels and explanations belong to the packaged translation catalog.
The initial selection remains `live`; retained submitted/setup values take priority.
Perspective recording works during or after a Game. Choose the Player whose initial
hand is known, then enter observed Plays chronologically. Unknown opponent hands
stay unknown. Permitted local-declarer Skat/discards and public-hand facts retain
their existing accepted entry points. Later Plays, revelations and outcomes must
never be backfilled into earlier decisions.

Reconstruction's complete-deal requirement applies with or without a local Player.
Applicable discards follow later. Selecting this mode does not establish that the
Cards have been entered or that export is ready. Direct entry names the current
Player and lists all three hands in canonical Forehand/Middlehand/Rearhand order.

Own/manual identity and explicit seats retain #225 setup review. Own identity never
implies Forehand. Changing mode after roster review requires the same existing
re-review; it does not clear the own Player or choose a seat. Rejected setup creates
no Product or IDs and saves no preference. Safe names and the checked radio survive
rejection and language changes; bindings are regenerated. Unsent browser-only input
requires the existing optional JavaScript enhancement. Native creation/entry works
without JavaScript.

## Direct entry and accepted state

#231 startup is retained exactly: creation is revision zero, and the first successful
initial ten-Card submission adds eleven ordinary Commands when identity is absent,
with one save. An existing identity means N Cards add N Commands. Game details and
exact time remain optional. Past `played_at`, language, zone and system time do not
select the path. `/sessions/cards` retains its 8,192-byte bound.

Opened, imported and reopened records display their effective accepted mode.
A promoted record displays reconstruction even if its initial mode was `live`.
Passive viewing, radio selection and disclosures cause no Product write, promotion,
analysis or preparation. Language saving retains its separate profile operation.

## Three independent analysis capabilities

* **Analyze current position** uses its existing current-turn and playable-hand gate.
* **Review recorded decisions** uses actual eligible #221 saved local snapshots and
  accepted observed Cards. Thirty Plays and ended perspective recordings need no
  promotion. Missing snapshots retain their unavailable explanation and navigation.
* **Full Historical review/export** requires reconstruction mode, the complete
  original deal, metadata, declaration/discard evidence and a valid recorded ending.
  Its blockers are explicitly scoped and do not hide eligible saved decisions.

Thirty Plays still require an explicit Game-End Command to become `ended`; reviewing
an eligible saved decision does not require forcing that ending. Ended guidance now
points to saved decisions and existing history/correction rather than promotion.

**Switch to reconstruction mode** retains `promote_to_retrospective` in optional
specialist actions and correction surfaces. It is an explicit one-way normal Command:
no new facts, no phase rewind and no automatic Historical readiness. During play or
after ending it does not reopen initial-deal entry. Existing Undo and correction
are separate operations, not a downgrade toggle. Successful promotion uses normal
Result invalidation. A still-valid ancestor Checkpoint's exported Request remains
frozen, including its original information and configuration; its observation
envelope correctly reports the current observation revision.

## Verification

Preflight started clean on `feature/233-session-knowledge-choice` at
`ffe1c3c6f8f08940e80875f4a5608516ad170f50`. The four specified core/creation files
had no differences from planning archive `aecd151aafff1601b0366bb024e65a98006f4240`.
No intervening contract discrepancy invalidated the design; #231/#232 are retained.

`tests/test_session_knowledge_entry_web.py` adds 14 real returned-form cases covering
both locales, missing perspective, retained radios/names, all own seats, reviewed
mode changes, complete reconstruction with/without perspective, strict file round
trips, and play/ended promotion with real Result invalidation and frozen exports.
The extended `test_compact_card_entry_web.py` regression creates through emitted
forms, checks eleven Commands/one save, appends an explicit past timestamp, records
30 legal Plays with only one hand supplied, explicitly ends, reopens and executes
genuine saved review. Legal fixtures choose observed Cards; no hidden hand, readiness,
Checkpoint or successful Result is injected. Spies count saves/execution or forbid
ID generation during rejected setup. Existing fault-injection tests remain separate.

The affected-path run passed **1,153 tests**, with one existing Windows account
symlink-permission skip, in **569.56s**. It includes #221/#225/#229–#232, direct entry,
declaration, time, language/validation, security/packaging, core replay/files/history,
information policy, CLI compatibility, Corpus and deterministic public provenance.
Ruff passed. Final full-check output and actual exit status accompany the report;
the prescribed full check follows all edits and browser verification.
The first full-check attempt hit a 3,600-second timeout near the end of pytest and
is not a pass. It also exposed a README insertion shifting the exact historical
rename inventory's line numbers. The new paragraph was moved into the current
workflow guidance after those historical lines, preserving both the evidence and
inventory unchanged. The corrected tree requires a complete rerun.

## Independently installed browser evidence

`scripts/verify_session_knowledge_entry.py` reuses the dependency-free DevTools
harness. It rejects checkout imports, checks 26 installed module/resource hashes
against the runtime tree, and verifies authenticated served CSS/script bytes.
The fresh environment installs the Wheel plus pytest for legal fixture helpers;
no browser/runtime dependency is added to the project.

Evidence: `<temporary-directory>/opencode/session-233-browser-1/evidence.json`
(`completed: true`), **88 measurements and 88 screenshots**. Windows CPython
**3.13.7**, Package **0.17.0**, headless Microsoft Edge **153.0.4234.32**,
revision `@9aab8632678bdbd60c393455e1394ee523ba682d`.

All four German/English and JavaScript-on/off runs actually choose both radios,
reject missing perspective, change language, create a perspective recording and
save ten Cards once. German uses local Rearhand; English uses local Forehand.
Actual submitted values/routes, focus and save counts are retained. Selection alone
has zero POSTs/writes. Each first hand has eleven Commands and one replacement;
there is no metadata helper request or automatic analysis. Submitted error state
survives native language changes; unsent mode changes are additionally tested with
the actual JavaScript enhancement.

Each run also creates reconstruction with local Forehand, saves that hand, sees
the named Middlehand request and full-deal explanation, then supplies the remaining
two hands and original Skat to reach declaration at revision 33. The native English
perspective recording separately uses **real HTTP fixture setup** for declaration
and 30 legal Plays. Browser Enter then explicitly ends the Game, executes genuine
saved-decision review, reopens and reviews again with the same frozen Request.
Only that run executes analysis (two explicit reviews); no promotion is submitted.

Measured viewports: **1365×900**, **390×844**, **320×800**, plus **200% text at
320 pixels**. Computed fonts are doubled once and restored; device scale remains 1.
Every document/client width agrees: **1350/1350**, **375/375**, **305/305**.
Long names wrap, native focus remains visible, errors focus their summary and Card
saves focus `session-recording`. Representative inspected screenshots:

* `js-de-knowledge-choices-1365-1.png`
* `native-de-knowledge-choices-320-2.png`
* `native-en-missing-perspective-error-320-1.png`
* `js-de-perspective-initial-390-1.png`
* `js-en-reconstruction-opponent-1365-1.png`
* `native-de-reconstruction-opponent-320-2.png`
* `native-en-ended-result-390-1.png`

| Artifact/resource | SHA-256 |
| --- | --- |
| Installed Wheel | `b822c33ca3034618ad964c9c01560836d9a86651b7280b79da1276d19c7c8505` |
| `locales/en.json` | `c4b7be32278812417d2d67a953d68599660d8d1d7b5cd521a6da5e42595fb571` |
| `locales/de.json` | `bd3413a8a339c60b3c4b12742eed085868dc9ed7963b3e735a63d0e895183bef` |
| `friendly_creation_rendering.py` | `e2e27148fdd10eebf000357b752bb81254eb4c603598f93528cecf8e9cbafb60` |
| `task_first_session_rendering.py` | `8cdbdef0d83a0e5018c1ac35a59f804a274d89ed0dc026b479124057b4cbcc5b` |
| `assets/app.css` | `3b8257ebb8b9fa8f4587772c41bb5d749970a18da42e617349326e9f1377459c` |
| `assets/workflow.js` | `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298` |

These are implementation checks, not maintainer UAT. No requested bounded browser
item is omitted; other browser engines and assistive technology are not covered.

## Compatibility and closure

No route, field, mode, stored timing preference, profile shape, Schema, public
wrapper, dependency or core transition changes. Package **0.17.0**, Python
**>=3.13**, **AGPL-3.0-only**, **tzdata>=2026.4**, 98 generated outputs, 59 private
POST routes and 103 form definitions remain. Catalogs now have 1,474 matching keys.
Raw documents/Logs and standalone CLI/Capture/manual Review retain their contracts.

#231 and #232 remain completed. Both `check` and `v1-supported-platform-matrix`
must pass on the exact merged commit before manual #233 closure. #208 and unresolved
findings remain open; UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed.
No complete UAT, release readiness or publication is claimed.
