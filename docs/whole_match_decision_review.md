# Resumable recorded-perspective Match review (#332)

Open an existing managed Match. Follow **Review my decisions across this Match**
from the recording or decision-review page. Choose the objective and effort, then
**Start whole-Match review**. The progress page (`/matches/whole-review`) returns
without waiting for the batch. **Refresh progress** is a read; **Cancel further
calculation** asks the worker to stop at its next evaluator checkpoint. Native
forms, links, original downloads and language switching work without page scripts.

**Open per-game comparisons** lists all 36 slots in recording order. The table
puts the played card beside its simulated success count and the entire equally
best set beside theirs. Where success counts tie but ranking differs, the
deciding secondary measure appears for both (exact total / common worlds).
The party is either the declarer or both defenders. These are comparisons under
a fixed policy, not proof of a mistake, winning strategy, or calibrated odds.
**Original analysis** opens that exact retained execution; use its Request and
Result links for the original downloads. Browser Back returns to the overview.

## What gets evaluated

The inventory traverses the authoritative slots and only actual plays by the
recorded `perspective_player_id`. A passed deal, an empty slot or the unplayed
suffix of a partial game contributes zero decisions. The existing before-card
reconstruction supplies the actor's hand, legal set, public prefix and authorized
knowledge. The observed card is retrospective comparison evidence. A sole legal
card in the full hand is a rule-only row. Null has no recorded numerical
evaluator. An unknown acting hand, missing required exposed hand, and recorded
play after the rule-determined end have their own skip reasons.

Fresh Standard uses 100 common worlds and 30 seconds per decision. Quick uses
25 / 5 seconds, More time 400 / 60 seconds. Seed defaults to 0. The effective
settings retain policy `side_aware_baseline` version 1, 100,000 preparation units
and 300,000 transitions. Only completed common coverage produces a ranked
comparison. A genuine timeout, partial or cancelled execution has its own original
and coverage, never a replacement ranking. The deadline applies to evaluation,
not durable capture or archive verification.

Complete settlement is the fresh objective. An optional bid or matador assumption
is scoped to the **numbered game** and used only on decisions whose before-card
view actually lacks it. Blank required values leave an explicit gap. Selecting
played-game goal explicitly omits settlement and ignores those assumptions.
Neither choice changes the recording. Future scores, commentary, later opponents'
plays or later games are not supplied as sampling inputs.

## Source, persistence and recovery

* One dedicated worker and a nonblocking home-local OS lease serialize Starts
  and Resumes. Evaluation and candidate encoding run outside application and
  capture locks. Selection of an individual decision is independent.
* The bounded private `whole-match-reviews` directory contains one latest
  checkpoint per managed recording filename and a coordination file. Each
  checkpoint is at most 96 KiB, with at most 360 decision references, at most
  36 supplement groups, the exact source content fingerprint, file identity,
  settings and attempt generation. It uses a checked digest and flushed
  same-directory replacement. The Match document itself is not modified.
* Open the same Match after restart and explicitly **Resume**. Viewing, language
  changes and reopening never schedule work. Resume re-admits the actual stored
  executions against the exact source, perspective, decision and effective
  options. It skips complete compatible executions, including ones originally
  saved by the selected-decision workflow. It explicitly retries other eligible
  decisions. Starting with different settings creates a new current checkpoint;
  original evidence remains under Saved analyses.
* The evaluator observer captures the actual Application invocation/execution.
  Each statistical result uses the existing `match_rollout` encoder, source,
  admission, quota, reservations and manifest CAS. A checkpoint records the
  intended identity **before** the archive commit. A crash between commit and
  acknowledgement is reconciled on Resume. One bounded, process-local candidate
  permits save-only retry when storage fails. After a restart an **uncommitted**
  candidate may need computation again. Freed space or a corrected storage
  problem can be necessary before continuing.
* The progress screen reports **references**, not a count of verified available
  results. The overview validates the archive in bulk, pins its matching objects
  through delivery and rechecks the manifest, admission and source before sending
  the page. Unavailable or deleted originals do not count as comparisons. No
  archive admission is cached for the lifetime of a worker. Ordinary archive
  limits remain 16 MiB/object, 512 MiB retained/staged, 2,048 entries per family.
  Larger archives can make overview and original-detail reads expensive.
* Editing, replacing or deleting the active source blocks stale publication and
  resume. An identical-content replacement still requires a fresh Start.
  Previously retained originals keep their historical identity. Changing settings,
  restarting or switching views never rewrites their Request or Result.

This is a private managed-Match workflow. It does not produce a Learning review,
change eligibility, apply tournament-money adjustments or change the evaluator.

## Disposable verification and later installed check

The source helper `scripts/verify_whole_match_review.py --output <new-directory>`
generates `synthetic-332.json` through normal Workspace persistence. The optional
`--measure` runs one Quick/played-game-goal worker followed by an authenticated
overview and original-detail GET. It records elapsed time and counts around the
real Application, evaluator, encoding, strict admissions, decodes, archive reads
and manifest update validation. Those phases are **inclusive and overlap**.

The fixture contains seven complete games and 27 partial recordings, one passed
deal and one empty slot: **291 plays, 97 perspective decisions**. There are 62
numerically eligible decisions (25 Grand defender, 9 Grand declarer, 20 Hearts
defender, 8 Hearts declarer), 33 forced, one unsupported Null and one missing hand.
This is substantial mixed coverage, not a simulation of 360 decisions.

The generated Workspace is 119,302 bytes, SHA-256
`a16fc08d9c5509f7bd275a3338756ba59a88de30a6792ccb27317a41a9586b5f`.

### End-to-end measurement

One fresh recorded-perspective Quick run completed all 62 eligible decisions,
reused zero originals and skipped the other 35 recorded decisions as described
above. The retained Results contain 1,550 completed common worlds, 184,100 card
transitions and 7,750 terminal evaluations. Thirteen decisions have multiple
equally best cards. The 63 immutable objects (one source plus 62 executions)
occupy 119,393,270 bytes; the largest is 2,254,335 bytes. Including manifest
and coordination file, the archive occupies 119,461,546 bytes. This exceeds
the 16 MiB **delivery receipt** byte bound despite staying below 64 objects.
Every overview and detail observation used strict validation of the real archive.

| Operation | Wall seconds | Full admissions | Rollout decodes | Object reads | Object bytes read |
| --- | ---: | ---: | ---: | ---: | ---: |
| Explicit fresh Start to worker exit | 2,029.637 | 1 (initially empty) | 62 | 2,138 | 3,911,618,991 |
| Reopen numerical overview | 224.084 | 2 | 124 | 189 | 358,179,810 |
| Open an original detail | 311.749 | 3 | 186 | 191 | 359,902,142 |

The Start timer excludes fixture creation and opening the Match. The real
producer made exactly 62 Application calls (33.294 s inclusive), including 62
evaluations (17.463 s). Building the 62 strict capture candidates took 115.130 s,
including 62 decoder round trips (62.952 s). Structural manifest update
validation took 1,685.280 s, including reads of existing objects. The two GETs
made **zero** Application/evaluator calls. Their admissions included 95.054 s
and 162.964 s respectively decoding retained rollouts. Timers nest; do not add
the phase times or interpret the 5-second evaluator limit as an HTTP deadline.
Focused tests were running on the same development machine for part of the probe.

This first measurement used a 5,811-byte progress file, before the final
checkpoint digest, file-replacement fencing and publication-lock correction.
The measurement exposed a responsiveness problem: holding the application
and Match locks across structural archive validation would delay progress and
Cancel on larger archives. The private manifest writer now accepts an optional
publication context only around the final compare-and-replace. The worker never
waits for Product locks while holding the store lock; a busy final publication
leaves a save-only candidate. All other writers retain their default context.
A real-execution regression pauses archive validation and verifies both that
Cancel can run immediately and that an intervening source correction prevents
publication. This removes the blocking of unrelated controls; it does not make
archive reads, schema validation or normal commits faster.

The final verification used an independent copy of that above-limit archive,
with one evidence entry and its envelope removed from the manifest's indexed
closure on the copy. The immutable files and original archive were kept. An
initial fixture setup removed only the entry; the strict closure check correctly
rejected that setup before any review. With the valid 61-result starting point,
the complete Quick job **reused 61, computed 1** (one real Application invocation,
one evaluator call) and still skipped the same 35 decisions. The final 63 indexed
objects occupy 119,393,270 bytes, with a 5,839-byte checkpoint. This separately
verifies the final publication path; it is not a claim of 62 new simulations.

| Final operation | Wall seconds | Full admissions | Rollout decodes | Object reads | Object bytes read |
| --- | ---: | ---: | ---: | ---: | ---: |
| Start, reconcile 61 originals, evaluate and save one | 253.129 | 2 | 123 | 251 | 473,848,925 |
| Reopen overview | 206.833 | 2 | 124 | 189 | 358,179,810 |
| Open original detail | 269.429 | 3 | 186 | 191 | 359,902,142 |

The single evaluation took 0.160 s within 0.295 s of Application execution;
the capture candidate took 1.398 s, and the one manifest validation took
39.132 s outside the Product locks. Both passive GETs made zero executor calls.
Independent strict final admission (including above the receipt limit) is a
concrete remaining cost. Full observations are in `volume/measurement.json`,
`volume/counts.json` and `reconcile-final/measurement.json` under the external
evidence directory below.

### Native source browser

The checked source-browser scenario used a smaller, independently disposable
partial Match to exercise the native interaction rather than repeat the volume
measurement. Edge 158.0.4370.33, 1280 × 900, disabled page JavaScript: one
Application/evaluator call before Cancel, process 37368 exited, and reopening in
process 30404 made zero calls. Explicit Resume made four more calls. The original
first reference survived. Both languages, detail and overview return left the
counts at four. The screenshots in `%TEMP%/opencode/332/browser4/overview-de.png`
and `overview-en.png` were visually inspected. The cards and both success counts
align across six columns, without clipped text or horizontal page overflow.
Play 15 shows both sides at 25/25 and the deciding final margin totals
1284/25 versus 1386/25; play 17 is a rule-only row without a simulated value.
These are source observations, not installed acceptance.

After the publication-lock correction, the same native scenario (`browser-final`)
also exercised a cancellation *inside* the evaluator: decision 3 retained a genuine
23/25 cancelled attempt rather than a completed comparison. Restart from process
10900 to 25972 made zero calls before Resume. Resume explicitly retried that
incomplete decision and evaluated the four remaining eligible decisions (five
calls total); it did not evaluate the forced play. Reading both languages and
the saved detail left those counts unchanged. The five complete originals and
the separate cancelled original were present. Both final screenshots were
inspected; the values and six-column alignment matched the first browser run.

### Local validation commands

Development Windows CPython 3.13.7; tool timeout 7,200,000 ms. External temporary
files, logs and JUnit under `$E`. The complete affected selection follows the
existing Match producer/retention consumers, native navigation/feedback, language
and packaging assertions. The additional archive selection covers the changed
private manifest writer and its direct producer, bulk-read, delivery and
maintenance consumers. Store limits, execution codecs and saved-detail
contracts remain unchanged.

```powershell
$E = "$env:TEMP/opencode/332"
$py = "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe"
$env:PYTHONDONTWRITEBYTECODE = '1'
$flags = @('-q','-n','2','--dist=loadfile','--max-worker-restart=0','-p','no:cacheprovider')
$jobs = @('tests/test_whole_match_job.py','tests/test_whole_match_web.py')
& $py -m pytest @jobs @flags --basetemp="$E/focused" --junitxml="$E/focused.xml" --log-file="$E/focused.log" --tb=short
& $py -m pytest @jobs @flags --basetemp="$E/fixed" --junitxml="$E/fixed.xml" --log-file="$E/fixed.log" --tb=short
& $py scripts/verify_whole_match_review.py --output "$E/volume" --measure
& $py scripts/verify_whole_match_browser.py --output "$E/browser4" --browser "${env:ProgramFiles(x86)}/Microsoft/Edge/Application/msedge.exe"
$M = @('match_decision_review_preparation','match_decision_analysis','match_rollout_review',
  'match_rollout_web','match_rollout_retention','automatic_match_rollout_evidence',
  'saved_match_rollouts_web','match_evidence_retention','saved_match_analyses_web',
  'analysis_controls','forced_card_guidance','recorded_review_navigation',
  'rollout_result_presentation','match_game_navigation_web','frontend_language_switching',
  'language_switch_context','language_view_continuity','task_first_language_preservation',
  'frontend_validation_preservation','frontend_localization_foundation',
  'complete_frontend_localization','direct_match_evidence','guided_frontend_packaging',
  'packaging_and_distribution','unified_local_app_web') | ForEach-Object {"tests/test_$_.py"}
& $py -m pytest @M @flags --basetemp="$E/affected" --junitxml="$E/affected.xml" --log-file="$E/affected.log" --tb=short
$J = @('whole_match_job','whole_match_web','frontend_localization_foundation',
  'packaging_and_distribution','unified_local_app_web') | ForEach-Object {"tests/test_$_.py"}
& $py -m pytest @J @flags --basetemp="$E/jobs-final" --junitxml="$E/jobs-final.xml" --log-file="$E/jobs-final.log" --tb=short
& $py -m pytest tests/test_cli_internal_architecture.py tests/test_skatmind_rename.py @flags --basetemp="$E/guards" --junitxml="$E/guards.xml" --log-file="$E/guards.log" --tb=short
# Only after the parallel workers exit:
& $py -m pytest tests/test_match_analysis_action_placement.py -q -p no:cacheprovider --basetemp="$E/exclusive" --junitxml="$E/exclusive.xml" --log-file="$E/exclusive.log" --tb=short
& $py -m pytest @jobs tests/test_frontend_localization_foundation.py @flags --basetemp="$E/receipts" --junitxml="$E/receipts.xml" --log-file="$E/receipts.log" --tb=short
& $py -m pytest @jobs tests/test_app_cli.py tests/test_unified_local_app_contracts.py @flags --basetemp="$E/source-final" --junitxml="$E/source-final.xml" --log-file="$E/source-final.log" --tb=short
& $py -m pytest tests/test_whole_match_job.py -k 'archive_validation or save_boundary' @flags --basetemp="$E/commit-focus" --junitxml="$E/commit-focus.xml" --log-file="$E/commit-focus.log" --tb=short
$A = @('whole_match_job','whole_match_web','automatic_learning_store',
  'automatic_learning_managed_service','automatic_learning_lifecycle','automatic_learning_bulk_read',
  'automatic_learning_delivery_receipt','automatic_learning_maintenance_readability',
  'automatic_learning_source_release','automatic_learning_language_work','automatic_learning_entry_language',
  'automatic_learning_ui','automatic_learning_ui_evidence','learning_landing_delivery',
  'automatic_match_learning','automatic_match_learning_evidence','automatic_historical_learning',
  'automatic_historical_lifecycle','automatic_historical_web','automatic_historical_admission',
  'automatic_session_lifecycle','automatic_session_learning','automatic_session_web',
  'automatic_session_review_corrections','automatic_session_review_corrections_web',
  'match_evidence_retention','match_rollout_retention','session_evidence_retention',
  'saved_match_analyses_web','saved_match_rollouts_web') | ForEach-Object {"tests/test_$_.py"}
& $py -m pytest @A @flags --basetemp="$E/archive" --junitxml="$E/archive.xml" --log-file="$E/archive.log" --tb=short
& $py scripts/verify_whole_match_review.py --output "$E/reconcile" --measure --retained-from "$E/volume"
& $py scripts/verify_whole_match_review.py --output "$E/reconcile-final" --measure --retained-from "$E/volume"
& $py scripts/verify_whole_match_browser.py --output "$E/browser-final" --browser "${env:ProgramFiles(x86)}/Microsoft/Edge/Application/msedge.exe"
& $py -m pytest tests/test_cli_internal_architecture.py tests/test_skatmind_rename.py @flags --basetemp="$E/final-guards" --junitxml="$E/final-guards.xml" --log-file="$E/final-guards.log" --tb=short
$env:RUFF_CACHE_DIR = "$E/ruff"
function python { & "$env:LOCALAPPDATA/Programs/Python/Python313/python.exe" @args }
.\scripts\check.ps1 -Mode Quick -LogDirectory "$E/quick"
git diff --check
git ls-files --others --exclude-standard | ForEach-Object { git diff --no-index --check -- NUL $_ }
```

The first focused run had six passes and three failures. A successful manifest
commit already consumes its candidate; the worker now handles that release
correctly. The cancellation fixture expected two sampled worlds from the older
custom action rather than the ordinary Quick preset's 25. The corrected run
passed nine tests in 67.43 s. Later tests also exercise a real evaluator timeout,
same-content file replacement, second-decision save failure, cross-owner conflict
and damaged progress. Earlier browser probes corrected a DOM readiness predicate,
isolated the source server's counters, and fixed an overflow assertion that
incorrectly counted the vertical scrollbar as a failure.

The 25 complete affected modules (`affected.xml`) passed **678 tests in
1,130.26 s**. The final five-module selection (`jobs-final.xml`) passed **89
tests in 112.01 s**: 15 new job/native cases and 74 overlapping checks. The
overlaps are not additional distinct cases.

The architecture/rename pair passed 67 tests in 10.52 s. The isolated Match
action-placement module passed 25 tests in 77.44 s. After improving the
computed/reused receipt and completed-original preference, the complete
job/native/catalog modules passed 37 tests in 112.34 s. The startup consumers
are included with the final file-identity and stale-checkpoint checks (79 passed
in 112.12 s). The lock-scope/save-boundary selection passed four tests in 35.04 s.
The 30 complete archive and job modules passed 635 tests in 2,276.71 s;
four existing symlink cases skipped on this Windows account. Across the complete
module selections there were **1,343 distinct passing cases and four skips in
56 modules**. Repeated focus/guard runs do not add distinct coverage. No routine
local Full was run. Quick covers Ruff, packaged schema parity and input examples;
it does not certify the distribution matrix or complete regression suite.

### Installed handoff

After hosted acceptance, use the generated import in a disposable installed
home. No manual deal entry or personal Match data is needed:

1. Import the Workspace, open its whole-Match review and choose Quick and
   played-game goal. Start, inspect progress, then Cancel after initial work.
2. Restart and reopen that Match. Confirm that viewing leaves progress stopped.
   Explicitly Resume, then inspect per-game comparisons and rule-only/gap rows.
3. Open an original result, inspect both downloads and return to the overview.
   Check the same source and decision in German and English.

#332 stays open for automatic partial branch feedback, published-source review,
maintainer integration, automatic exact-commit main `check` and
`v1-supported-platform-matrix`, then this narrow installed check. #208 stays open.
No manual Actions dispatch or release authorization follows from local evidence.
