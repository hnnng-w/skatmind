# Simple analysis entry and grouped recording metadata

## Scope and authority

Issue #324 implements approved G, H, I, K and corrected J: source URL, kind and
associated source metadata belong together. Starting branch is
`feat/324-simple-entry-forms`, starting HEAD
`c84a95e1f9d102dc63468c5cbddcde070e6843a8`, with a clean index and worktree.
The maintainer has accepted and closed #321/#322. Their Tournament/Cent evidence,
accepted Learning evidence and other earlier valid acceptances remain valid.
#208 remains open.

## Ordinary entry

Home presents three native task links in two ordered groups:

| Group | Task | Destination |
| --- | --- | --- |
| `record_games` | Record a 36-game Match | `/matches` |
| `record_games` | Record an individual game | `/sessions` |
| `analyze_and_review` | Analyze | `/review/recorded` |

Main navigation is Home, Match recording, individual recording, Analyze, Settings;
About remains in the footer. Analyze reuses the existing recorded Match/Session
chooser and its exact native `POST /review/open-recording` owner, freshness and
source checks. Alongside the lists it offers **Enter a situation yourself**
(`/analyze`), **Review a completed game manually** (`/review`), and secondary
**Learning** (`/learning`). Single-situation, manual Review and Learning pages
highlight the Analyze parent. Match review/report pages retain their existing
Analyze highlighting; recording pages retain their own recording-family parent.
`data-workflow`, language return paths, drafts, sources and Results keep their
existing identities and lifetimes.

Rendering Home/the chooser and changing language execute no analysis, prepare no
Learning and load no Learning archive preview. Recording activation remains an
explicit source-bound POST. Language may save the existing local language preference;
it writes no Product file. Route/form inventories and distribution-smoke chooser
expectations remain compatible; no new route or form owner is introduced.

## Match creation and shared defaults

The existing Match form owns every control exactly once:

1. Required editable Match title.
2. Initially closed **Optional details**, immediately below the title and before
   player setup: date-only display field, nested native exact-time editor, then
   one contiguous Source fieldset. URL and source-kind selection share a responsive
   row, followed by alternate title, channel, video start and end.
3. Existing platform, fixed-format summary and player setup/review controls.
4. Initially closed **Save as defaults**, containing the existing unchecked
   `save_players` and `save_platform` choices.
5. Initially closed Advanced Match details, containing external Match ID,
   platform-player IDs and the nested read-only technical format definition.
6. Existing reviewed-perspective and explicit Create actions.

The shared Session renderer groups only its existing `save_players` choice. There
is no new Session source/metadata contract or profile preference. Legacy
`advanced_settings_expanded` values remain lossless through unrelated Settings saves;
they do not control fresh disclosure layout.

Collapsed controls remain enabled successful form controls. Existing
`profile_generation`, `setup_context`, local-time bindings, full-form review and
one-use consent remain authoritative. Automatic source classification and blank
source-title fallback to Match title are unchanged; URLs are never fetched.
Channel/timecode visibility no longer depends on a manually selected video kind.
Date-only and exact timestamp meanings, minute-only input, timezone/DST resolution
and active metadata editing retain their existing implementation.

Validation retains safe values and opens every ancestor disclosure of an invalid
field. The creation adapter now associates existing video-timecode validation
failures with start/end controls, including malformed components, missing start
and reversed ranges; it reuses the existing parser and range constructor.
Enhanced language switching retains safe unsent values, deliberate checkbox
choices and disclosure state; validation-required visibility takes precedence.
Native JavaScript-free Update/error submission retains values for the subsequent
language switch and final Create. A native language form cannot transmit edits
never submitted from a different form; that existing no-script limitation remains.

## Missing Cent value

Only a won/lost result with absent or empty `game_value` receives
`validation.accounting.missing_game_value`, associated with the actual value field.
It requests the game value before loss doubling and explains automatic doubling
for a loss. Nonempty malformed/out-of-range values retain the generic invalid
message; passed/derived results do not acquire this requirement. Source/conflict
checks still precede result mutation. Existing fee calculation and exactly-once
loss doubling remain in the same owner.

## Local verification and remaining acceptance

Complete affected modules cover navigation contracts, Home/chooser and independent
entry paths, recording/settings navigation, shared creation, legacy preferences,
validation/language restoration, catalogs and Accounting web behavior. The moved
nested time editor justifies the complete local-time web module; existing shared
language preservation is exercised directly. The account-ID error disclosure is
also covered through own-player setup. The timecode field-diagnostic adjustment
adds the complete profile-driven Match creation module to the selection; the shared
timecode parser itself is unchanged. Arithmetic/store and large Learning-archive
suites are not affected. Direct distribution-smoke
Home/chooser consumers were inspected and retain their exact expectations.
The complete rename and CLI architecture guards run against final documentation.

Use development CPython 3.13, two file-grouped workers with disabled restarts,
external temporary outputs and 7,200,000 ms invocation timeouts. Run explicit
`scripts/check.ps1 -Mode Quick` after workers exit, then tracked/new-file whitespace
checks. Record actual commands, counts, failures/recovery and timings in the handoff.
Quick is partial validation, not distribution or complete-regression certification.

One compact checkout-only Chromium check uses a disposable synthetic home and
browser profile: DE/EN navigation, initially closed source/default groups, automatic
source visibility, native JavaScript-disabled submission, validation recovery,
checked-choice retention and enhanced unsent-value/disclosure language restoration.
It enters no complete game and runs no card analysis. This is developer evidence,
not installed acceptance.

The checkout-only Edge `157.0.4341.60` run completed with 12 captured observations
and seven genuine native POSTs. JavaScript-disabled DE/EN Home, chooser, manual
Review and single-situation navigation retained the correct parent. Source URL/kind
were adjacent at desktop width and stacked without horizontal overflow at 390 px;
all six source controls were enabled and visible with automatic selection. A
contradictory manual-kind/URL submission exposed the source error, retained both
save choices through native language return, and recovered through the unchanged
review action. Enhanced language return preserved an unsent source title, explicit
checkbox clearing and both open disclosures. No recording was activated or Product
file created, no known Player/platform default was saved, and guarded analysis,
Learning preparation and archive binding were never called. Screenshots and native
POST observations are in the external `opencode/324-browser-01` evidence directory;
the checkout-only driver is external `opencode/324-browser-check.py`.

Keep #324 open for automatic partial branch feedback, ChatGPT published-source
review, maintainer integration, automatic successful complete exact-commit main
`check` and `v1-supported-platform-matrix` gates, and one short later installed
acceptance of these entry/forms. No manual Check dispatch is required. Existing
accepted Tournament, Cent and Learning scenarios need no replay. #208 and release
acceptance remain separate.

## Main Check failure correction

The continuation starts on `feat/324-simple-entry-forms` at
`8c822c9f08a704660881deb077243ef107e276a5`, with a clean index/worktree.
Authenticated read-only retrieval verified existing [Check run 43944221564](https://github.com/hnnng-w/skatmind/actions/runs/43944221564):
`push`, `main`, attempt `1`, that exact SHA, failure, 79m21s, 20 successful and
three failed jobs. The twelve installation cells and platform-matrix gate passed;
both regressions failed, and the final `check` log reports
`gate_prerequisites_invalid` with regression as the failed prerequisite.

| Platform | Regression job | Artifact | ZIP SHA-256 |
| --- | --- | --- | --- |
| Ubuntu | `133569650897` | `14271301502` | `9bcca8671f99d3dc6307adcd378643f7d96c32cd1f46a31bbb60f57dbe7dfbe7` |
| Windows | `133569650651` | `14272986636` | `938504044fafc98546469c275685563928ce3e7f7048829649c6d97c520d9fca` |

Both archive hashes match API metadata and the corresponding job's upload record.
Both summaries name the exact SHA and source digest
`5046976447c21b47a78689dd180ab46c80560a4d9fe2f694725e6832b726ba3d`, also
recomputed from the untouched local checkout. API run/job metadata binds the
archives to attempt 1. Both hosted interpreters were CPython 3.13.15 with four workers.
Raw metadata, ZIPs, extracted reports, full regression job logs, complete failure
tracebacks and independently reconciled `verified-accounting.json` are retained
outside the repository in `opencode/324-main-43944221564`.

Each platform's complete collection contains **12,724** identical node IDs.
All four worker collections agree on the **12,629** parallel nodes; each selected
node has exactly its required setup/call/teardown reports, including skipped setup
handling. There are no setup or teardown failures.

| Platform | Parallel passed / failed / skipped | Setup passed / skipped | Call passed / failed / skipped | Teardown passed | Parallel wall / total pytest-stage wall |
| --- | --- | --- | --- | --- | --- |
| Ubuntu | 12,623 / 1 / 5 | 12,626 / 3 | 12,623 / 1 / 2 | 12,629 | 3720.040s / 3735.161s |
| Windows | 12,628 / 1 / 0 | 12,629 / 0 | 12,628 / 1 / 0 | 12,629 | 4613.266s / 4632.728s |

The exclusive phase **did not execute** on either platform. The complete reports
contain zero executions of its 95 collected nodes; full logs proceed directly from
parallel failure to the final summary/upload. The exact runner returns at the failed
parallel stage before launching exclusive execution. Those 95 are unexecuted, not
skipped: early-rejection observer 6, local Corpus web 27, Match analysis action
placement 25, and unified rejection transport 37.

Both platforms have exactly this one failed node, in **call**, with passed setup
and teardown:

```text
tests/test_learning_source_navigation.py::test_retained_evaluation_survives_navigation_refresh_language_duplicate_and_stale_remedy
```

Both relevant tracebacks are complete in `pytest-parallel.log` lines 187–245 and
the external `ubuntu-failure.txt` / `windows-failure.txt`. They terminate at test
line 284, `assert f'href="{route}"' in page`, for `route == "/learning"` after
visiting `/matches`. This is an obsolete navigation expectation: approved G/H
removed equal-primary Learning access and placed its native link under Analyze.
The correction changes only that test's route sequence to
`/` → `/matches` → `/review/recorded` → `/learning`, preserving the assertion that
each next link is actually emitted and all existing download-byte, prepared-object,
Current-selection, source-file, stale-recovery and operation-count assertions.
No Product code, assertion strength, skip, timeout or CI policy changes.

Local CPython 3.13.7 reproduction of that exact node failed at the same assertion
in **7.35s**. After correction, the complete `tests/test_learning_source_navigation.py`
module passed **17 tests in 27.19s**. Both used
`-n 2 --dist=loadfile --max-worker-restart=0`, external temporary/cache/JUnit outputs,
and 7,200,000 ms invocation timeouts. The changed verification document additionally
requires the complete rename guard against its final text, followed by explicit
Quick and whitespace checks; final outcomes are reported in the handoff. No
exclusive module is affected by this test-path/documentation correction. The
earlier 22-module selection, Full and installed scenarios are not repeated.

This corrects the demonstrated local failure but does not establish new hosted
acceptance. Keep #324 open for the normal publication sequence and planned narrow
installed acceptance. Accepted #316–#323 evidence, including completed #321/#322
installed acceptance, remains intact; #208 stays open.
