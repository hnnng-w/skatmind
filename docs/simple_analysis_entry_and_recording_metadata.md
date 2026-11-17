# Simple analysis entry and grouped recording metadata

Current status: the maintainer accepted the original functional installed A–D
observations. Main Check `43965683990` passed all 23 jobs at
`4b653587088741306d921d66425a52fbdf374047`. The
[installed follow-up](#installed-acceptance-follow-up) below extends #324; it does
not restart or invalidate that acceptance. Earlier pending statements are history.

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

## Installed acceptance follow-up

The maintainer explicitly approved these additional changes after the original
A–D observations passed. Actual starting branch is `feat/324-simple-entry-forms`,
HEAD `4b653587088741306d921d66425a52fbdf374047`, with a clean index/worktree.
Cent accounting, the accepted missing-value message and saved round titles are
unchanged. Accepted #316–#323 evidence and completed #321/#322 installed acceptance
remain valid. This follow-up requires its own publication, source review, automatic
exact-commit main gates and one later narrow installed check. #324/#208 remain open.

### Saved existence is separate from Learning eligibility

`automatic_historical_inventory.py` retains every live saved Review head, exact
identity and readable source caption. An admitted standalone `historical_review`
row is now `ineligible`, with no selected source tuple. This applies equally to
guided and imported Reviews and cannot be overridden by an old explicit exclusion
or a new inclusion action. `source_keys()` offers only recorded source families.
Generation diagnostics use the existing `unsupported` exclusion reason; no new
ordinary field, preference, route or transport is introduced.

`automatic_session_inventory.py` still captures the complete mixed live inventory
and exact head/source changes. Imported-claim reconciliation receives only eligible
source tuples, so an ineligible imported standalone Review cannot block a recorded
Match/Session. Existing duplicate recording identities and untrusted explicit
cross-source binding safeguards remain unchanged. There is no blanket filter on
`evidence_class == "historical"`: executed Historical evidence attached to an actual
recorded Match remains eligible through the existing Historical bundle builder.

Old codec-4 descriptors keep their original adapter/builder constants and strict
admission semantics in `automatic_historical_preparation.py`. Historical selected
rows remain readable. When a retained generation references a standalone Review,
current live inventory blocks its delivery as `excluded`, including an installed
old bundle and after restart. Passive access neither rewrites the descriptor nor
prepares a replacement. Explicit Update publishes a new generation without that
contribution, retains the old descriptor as previous where applicable, and preserves
the independent Match exports. Unchanged Update and restart reconstruction retain
their ordinary reuse/rebuild behavior.

Live `ineligible` versions count as current for old-evidence cleanup, do not block
otherwise valid obsolete-source preview, and remain protected from source release.
They are not deleted or obsolete merely because Learning does not select them.
Saved Review discovery, reopening/correction, explicit deletion and original
Request/Result downloads still use their existing head/owner and strict archive
readers. DE/EN saving, current-version, deletion and Learning scope text now describe
that separation. No archive migration or split is needed.

### Applicable source controls

Within the existing Match Source group, `.video-source-fields` contains only the
channel, start/end timecodes, their labels and video help. Native CSS hides that
group only when explicit manual observation is selected, all three values are
empty, and none is marked invalid. URL/kind stay together and alternate source title
stays reachable. Automatic and both video choices show the group without JavaScript.
Any populated or invalid field exposes it, even after clearing an invalid value
until successful validation. Controls remain enabled, single-owned and present in
native POSTs; switching kinds preserves values. Parsing, classification, title
fallback and persistence are unchanged.

One compact checkout-only Edge check used disposable synthetic inputs, actual native
keyboard submissions and no installed/UAT data. Ten observations and five POSTs
verified automatic/empty manual/populated manual/video visibility, JavaScript-disabled
operation, channel-error recovery, DE/EN language return, enhanced unsent preservation
and one submitted copy of each video field. Screenshots and POST evidence are external
under `opencode/324-manual-source-browser-01`; the driver is
`opencode/324-manual-source-browser.py`. This is developer evidence only.

### Measured landing work and bounded correction

The actual path is managed collection discovery/rendering → `send_landing` →
controller capture → service `_inspect`/`_capture` → archive delivery snapshot and
mixed recording inventory. Previously immediate capture validation, reader entry,
language-context resolution and final response authorization each repeated inspection.
First entry also strictly initializes separate saved-archive and automatic-service
owners. The landing already omits full maintenance/source-exception rendering.

`delivery_operation()` now scopes one captured binding to that response's execution
context, with `finally` reset. Intermediate checks reuse only that exact binding and
still check process owner, store identity, attempt, installed bundle and source epoch.
`validate_final_delivery()` bypasses this scope and performs the full fresh archive,
manifest and recording checks immediately before headers, checking store identity
before and after validation. Reader pins remain held through body writing. Other
routes and POSTs retain their existing validation work. A later GET starts a new
operation; there is no TTL, metadata-only cache, persistent cache or raised bound.
`_snapshot_for_delivery` still checks every indexed byte and storage inventory and
keeps its complete strict-admission fallback above existing limits.

Before/after measurements use the **same unchanged recorded-Match archive**, one
genuine retained Immediate execution and a current generation. No standalone Review
is present, so eligibility changes cannot explain the work reduction. The existing
`measure_work` / `publish_fresh_archive` helpers separate fixture costs from HTTP:
execution 4.683s, publication 2.923s, explicit Update 15.590s. Each measured sequence
starts fresh app/service owners, then sends one subsequent unchanged GET. Card
analysis, all Learning preparation builders and archive writes were prohibited;
all managed file bytes remained identical.

| Operation | Before | After |
| --- | ---: | ---: |
| First GET elapsed | 8.744s | 9.821s |
| First admissions / retained-result decodes | 3 / 3 | 3 / 3 |
| First indexed object reads / bytes | 37 / 41,515,449 | 22 / 27,667,350 |
| First recording inventory captures / bytes | 32 / 262,608 | 14 / 114,891 |
| Unchanged GET elapsed | 1.066s | 0.386s |
| Unchanged admissions / retained-result decodes | 0 / 0 | 0 / 0 |
| Unchanged indexed object reads / bytes | 25 / 23,080,165 | 10 / 9,232,066 |
| Unchanged recording inventory captures / bytes | 28 / 229,782 | 10 / 82,065 |

Evidence is external `opencode/324-learning-entry-measurement/{before,after}-work.json`,
from `opencode/324-learning-entry-work.py`. Elapsed observations are not thresholds or
an installed-latency claim. **Cold latency did not improve in this observation**;
three strict startup admissions/decodes remain. The installed delay is not proven
solved. A bounded subsequent proposal is to seed a store-owner-specific startup
receipt from constructor admission, bracketed by exact bytes, limits and inventory,
so first capture need not repeat it. Sharing admission across independent archive
and service owners additionally needs explicit ownership design and adversarial
tests; this follow-up does not expand into that change.

### Follow-up validation boundary

Complete selected modules cover Historical eligibility/lifecycle/native access,
old-descriptor compatibility, genuine recorded Match Historical evidence, Match and
Session service behavior, receipt/bulk/fallback reads, Learning UI/maintenance/source
release, language ownership, and the new landing capture/final races and reader pins.
Creation detail/settings/shared-preservation and catalog modules cover conditional
source rendering. The existing actual 67-object over-limit fixture is included with
the complete bulk-read module; tightened-limit landing checks separately exercise
both required HTTP boundaries without truncation. Timing assertions use structural
work counts, never elapsed gates. Final documentation is checked by the complete
rename guard. None of the repository's four exclusive modules is affected: no
standalone Corpus transport, rejection teardown or Match action-placement code changes.
Final commands/results are recorded in the handoff, using development CPython 3.13,
two file-grouped workers, disabled worker restarts, external outputs and 7,200,000 ms
timeouts, followed by explicit Quick and tracked/new-file whitespace checks.
