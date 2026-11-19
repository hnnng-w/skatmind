# Responsive advice and saved Reviews (Issue #326)

For the correction based on the published candidate, see
[Published-source follow-up](#published-source-follow-up). Earlier measurements
and validation below describe the initial implementation, not installed acceptance.

## Baseline and boundary

Implementation starts on `task/326-responsive-analysis` at
`74ed6857f105e7ae82413323cced0cdc3d57ebc5`, with a clean worktree/index. Read-only
GitHub retrieval confirmed Issue #326 and its complete requirements. The accepted
#325 controls and installed functional evidence remain intact. Product code changes;
publication, hosted acceptance and the narrow installed timing follow-up are pending.

All observations below use development CPython 3.13.7 and disposable synthetic
source-checkout environments under `%TEMP%/opencode/issue326-*`. They are not
installed UAT, hardware attribution or latency guarantees. No maintainer data,
installation, build, UAT startup or publication is involved.

## Bounded changes

* Saved Historical lists and source-opening pages project strictly admitted source
  versions. Each distinct required `source_version_id` is decoded once by the
  caption projector, including older/deleted versions. Names and logical source
  IDs are not deduplication keys. Evidence availability, order, indices, original
  links and original downloads still come from the complete admitted manifest.
* These pages and Reopen use the existing automatic service's operation-local
  intermediate validation reuse. Final guards explicitly call
  `validate_final_delivery`, including the formerly different Reopen POST guard.
  Source projections confer no delivery authority. Full Report corruption after
  projection still prevents delivery.
* Manual Review requests separately reuse their own freshly captured intermediate
  delivery binding. A request-scoped context is discarded on exit; final delivery
  disables it and checks exact archive bytes again. Manual and Automatic owners do
  not exchange receipts. Pins, source checks, CAS, reservations, corruption checks,
  quotas and all receipt limits retain their existing semantics.
* Historical Immediate preparation passes its exact inference model to the existing
  recommender's optional argument. No algorithm, seed, effort or budget changes.
  Unconstrained cases where no model exists retain the existing fallback behavior.
* German/English headings and actions distinguish **saved game inputs** / **open
  recorded input** from **saved analyses** / **view saved analysis**. A brief
  explanation covers multiple executions per input revision and retained history.

### Forced-card advice

The private `app_web/forced_card_guidance.py` boundary derives the complete legal
set from an existing validated Position Request, with schema/domain validation,
concrete own-turn identity and hand sizes reconciled against attributed play.
Unknown/incomplete hands, observation filters, other turns, terminal states and
invalid inputs cannot establish a forced Card. The rule fact is distinct from
winning chances and has no numeric Result fields.

Explicit ordinary submissions for guided Position, current Session, recorded-own
Session rollout and selected Match Immediate/rollout advice return this fact when
there is exactly one legal Card. There is no inference, sampling, Search, rollout,
Report, retained execution or Learning publication for the hint. Recorded cases
check their exact owner, file, revision and selection on admission and again at
final HTTP delivery. The response is ephemeral; returning to controls or changing
selection does not retain a hint credential. Custom/deeper requests keep the
existing executor and original controls. Multiple-card paths keep existing effort
presets. Whole-game Historical review still evaluates its requested decisions.
Submitted nonempty settlement supplements retain their existing validation. Missing
settlement facts are not required for a rule-only hint; explicit calculations retain
all existing required-supplement checks.

Guided Position retains its accepted draft for native retries/language returns.
Earlier original analysis/downloads remain available and are explicitly captioned
as earlier calculations when shown beneath a new rule hint. No public API, schema,
archive codec or persisted recording format changes. Passive views execute no
new Card analysis; standalone manual Reviews remain excluded from Learning.

## Source-only measurement method

`scripts/measure_responsive_analysis.py` creates genuine fixtures with existing
helpers, then reuses copies of the same untouched source archives for before/after.
Fixture construction took **27.04 s**, including one genuine result-only complete
Historical execution reused under independent source identities. It is outside
response timings. The small archive contains **4 objects / 183,672 bytes / 2
available executions**. The genuine above-limit archive contains **66 objects /
3,030,588 bytes / 33 available executions**; its receipt fallback is the unchanged
64-object limit, with no injected limit, truncation or eviction.

Cold means a new or invalidated service-owner receipt, not a flushed filesystem
cache. Warm means a subsequent unchanged request. HTTP POST and redirect GET are
measured separately. A genuine full thirty-Play guided Quick execution (25 samples,
seed 11) is saved before repeating small-archive discovery/reopen. Match decision
25 in the complete synthetic recording has two legal Cards and uses Quick 25-world
rollout separately from Quick Immediate. Current Session uses the final own-turn
one-Card prefix. It is not the maintainer's unestablished Match legal-card case.

Named phase durations in the external JSON are **inclusive and may overlap**.
They must not be added together. They separately expose source preparation,
recommendation/rollout, inference, serialization/output validation, retention,
admission, inventory, delivery capture and final HTTP work. Original probe aliases
did not instrument every lazily imported engine/sampling function: reported engine
figures below are measured recommendation work, not an invented whole-pipeline
partition. Focused seeded tests additionally compare actual sampling-call counts
and full values with/without the supplied model for Grand, Suit and Null.

### Response durations in seconds

| Operation | Before | After |
| --- | ---: | ---: |
| Small saved list, cold | 1.559 | 1.702 |
| Small saved list, warm | 0.612 | 0.303 |
| Small source opening | 0.513 | 0.280 |
| Small Reopen POST / redirect GET | 1.518 / 0.262 | 1.181 / 0.070 |
| Full guided Quick POST / redirect GET | 24.860 / 14.552 | 24.382 / 14.206 |
| Saved list after Quick, cold | 16.624 | 15.989 |
| Saved list after Quick, warm | 0.750 | 0.389 |
| Source opening after Quick | 0.667 | 0.373 |
| Reopen after Quick POST / redirect GET | 0.705 / 0.223 | 0.350 / 0.095 |
| Non-forced Match Quick rollout POST / GET | 19.417 / 35.822 | 19.334 / 35.351 |
| Non-forced Match Quick Immediate POST / GET | 26.121 / 41.309 | 26.223 / 39.063 |
| Forced current Session POST / GET | 0.663 / 0.334 | 0.215 / no redirect |
| Above-limit list, cold | 153.652 | 53.714 |
| Above-limit list, warm | 121.060 | 38.744 |
| Above-limit source opening | 103.961 | 39.264 |
| Above-limit Reopen POST / GET | 151.945 / 78.197 | 83.069 / 32.535 |

The final conservative hand-size/schema guard was added after these end-to-end
measurements; final tests cover that stricter boundary. The Session timing describes
the observed source candidate, not a certified final installed latency.

### Work and phase evidence

| Operation | Before | After |
| --- | --- | --- |
| Small warm list | 32 object reads, 1,469,376 bytes; 7 archive delivery checks | 14 reads, 575,122 bytes; 2 checks |
| Above-limit warm list | 7 admissions, 231 retained Result decodes; 726 reads, 26,631,198 bytes; 12 inventory captures | 2 admissions, 66 decodes; 297 reads, 10,285,011 bytes; 4 inventory captures |
| Above-limit cold list | 8 admissions, 264 decodes | 3 admissions, 99 decodes |
| Above-limit source opening | 6 admissions, 198 decodes | 2 admissions, 66 decodes |
| Above-limit Reopen POST | 9 admissions, 297 decodes | 5 admissions, 165 decodes |
| Above-limit Reopen redirect | 5 admissions, 165 decodes | 2 admissions, 66 decodes |
| Guided Quick | 580 model-builder calls, 30 recommendations | 552 builder calls, 30 recommendations |
| Guided Quick redirect | 35 reads, 15,228,087 bytes; 5 delivery checks | 20 reads, 8,701,764 bytes; 2 checks |

Warm small-list admission/Result-decode counts are zero in both cases, because
the exact-byte bounded receipt already works. Source-only projection removes the
extra full bulk admission above the receipt limit; fresh complete admission still
runs at capture and final delivery. Reopen additionally needs the selected original
execution and its separate manual owner, so it does not collapse to the list's count.

Guided Quick's measured recommendation sum is **0.236 / 0.251 s**, inference-model
time **0.164 / 0.093 s**, output-schema validation **0.630 / 0.652 s**, serialization
**0.003 / 0.005 s**, retention **17.533 / 17.309 s**, and first redirect admission
**14.141 / 13.933 s**. Source preparation is **0.093 / 0.104 s**. These observations
do not establish a substantial improvement of whole-game completion latency.

Match rollout engine work is **0.011 / 0.016 s**, while redirect admissions consume
**33.650 / 33.607 s**. Match Immediate redirect admissions consume **36.472 /
34.831 s**. These paths still perform two strict admissions for live retention
presentation/final delivery and are a remaining measured cost. No persistence was
skipped to make the response appear complete. The forced Session response has zero
statistical execution, archive reads, admission or publication.

### Exact output preservation

The full guided Quick Request and Result download bytes match before/after:

* Request SHA-256: `759add2d1f1845f476fd9db28fb62af2fa7780d55eecf5f4ba93b179523be734`
* Result SHA-256: `c589295cb5d7c7e5c2119b21949655ec83929c6aee4c08b8fd4fc0a16a9a64bd`

The unchanged per-decision budgets, seeds, recommendation values, internal retained
validation and successful save receipt are checked. Tests preserve archived original
bytes across reopen, historical/deleted revisions and corruption rejection. Explicit
custom single-Card calculations retain real original outputs; hints preserve those
objects and downloads without adding archive evidence.

## Compact native browser evidence

`scripts/verify_responsive_analysis.py` completed with source-checkout Edge
**157.0.4341.60**, page JavaScript disabled, using one synthetic complete Match and
one genuinely saved Historical fixture. Native controls verified both German and
English forced-card text, the Custom settings selector and distinct saved-input /
saved-analysis sections and actions. The sequence executed **zero new analyses**;
source bytes and archive manifest remained unchanged. Report:
`%TEMP%/opencode/issue326-browser/report.json`. This is developer DOM/native-control
evidence, not installed UAT, visual acceptance or a repetition of #325's UAT matrix.

## Validation selection and commands

The complete modules below follow the changed Historical Immediate caller and its
direct consumers, caption/admission/retention owners, guided/stateful transport,
ordinary/custom controls, original downloads, localization/language preservation,
and source architecture guards. The complete affected exclusive transport modules
run only after all parallel workers exit. Every invocation uses a 7,200,000-ms
timeout. Final results and any necessary failure-driven rechecks accompany the
implementation report; no routine local Full or full-suite timing run is used.

```powershell
$modules = @('test_forced_card_guidance', 'test_analysis_controls', 'test_analysis_controls_web', 'test_guided_position_form', 'test_guided_frontend_contracts', 'test_guided_frontend_execution', 'test_guided_frontend_web', 'test_guided_frontend_json_transfer', 'test_guided_card_palettes', 'test_frontend_validation_preservation', 'test_frontend_localization_foundation', 'test_complete_frontend_localization', 'test_frontend_language_switching', 'test_language_switch_context', 'test_language_view_continuity', 'test_task_first_language_preservation', 'test_task_first_stateful_rendering', 'test_unified_local_app_web', 'test_unified_local_app_managed_items', 'test_session_recorded_review', 'test_session_recorded_review_web', 'test_session_whole_game_review_web', 'test_match_rollout_web', 'test_match_decision_selection_web', 'test_analysis_explanations_web', 'test_recorded_decision_context_web', 'test_automatic_historical_web', 'test_automatic_historical_learning', 'test_automatic_historical_lifecycle', 'test_automatic_historical_admission', 'test_automatic_historical_evidence', 'test_automatic_learning_bulk_read', 'test_automatic_learning_delivery_receipt', 'test_automatic_learning_language_work', 'test_automatic_learning_entry_language', 'test_automatic_learning_ui', 'test_automatic_learning_ui_evidence', 'test_automatic_match_learning', 'test_historical_game', 'test_historical_review_provenance', 'test_historical_opponent_profiles', 'test_historical_game_event_chain', 'test_historical_defender_open_play', 'test_historical_defender_open_play_continuation', 'test_historical_defender_concession', 'test_historical_declarer_card_exposure', 'test_historical_declarer_card_exposure_continuation', 'test_historical_open_card_throw', 'test_variable_length_historical_decisions', 'test_equal_best_immediate_consumers', 'test_application_orchestration', 'test_application_provenance', 'test_output_schema', 'test_cli', 'test_skatmind_rename', 'test_cli_internal_architecture') | ForEach-Object { "tests/$_.py" }
py -3.13 -m pytest @modules -n 2 --dist=loadfile --max-worker-restart=0 -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-final --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-final.xml -q --tb=short
py -3.13 -m pytest tests/test_match_analysis_action_placement.py tests/test_unified_rejection_transport.py tests/test_early_rejection_observer.py -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-exclusive --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-exclusive.xml -q --tb=short
.\scripts\check.ps1 -Mode Quick -LogDirectory C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-quick
git diff --check
```

Measurement commands (before Product edits, then the same fixture copies afterward):

```powershell
py -3.13 scripts/measure_responsive_analysis.py --output C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-before --fixtures C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-fixtures --create-fixtures
py -3.13 scripts/measure_responsive_analysis.py --output C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-before-large --fixtures C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-fixtures --counts 33
py -3.13 scripts/measure_responsive_analysis.py --output C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-after --fixtures C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-fixtures
py -3.13 scripts/verify_responsive_analysis.py --browser "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --output C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-browser
```

The first baseline completed all small/current/Match observations, then the test
client timeout interrupted the large case. The dedicated large run increased only
the probe's HTTP client timeout; Product limits were unchanged. No interrupted
large observation is reported as successful. New-file whitespace checks use
`git diff --no-index --check -- /dev/null <path>` for each new file.

The initial complete selection ran **2,006 tests in 2,320.33 s**: 1,993 passed,
11 failed and two existing skips. Failures identified the shared Historical
test double's missing optional-model argument, the catalog's exact entry count,
the new strict adapter's architecture allowlist entry, and invalid supplied matadors
being bypassed by forced guidance. The correction updates those exact expectations
and validates supplied supplements while keeping missing facts unnecessary for a
rule-only hint. No existing corruption or source-guard assertion is removed.

The failure-driven complete-module recheck is:

```powershell
py -3.13 -m pytest tests/test_forced_card_guidance.py tests/test_analysis_controls_web.py tests/test_session_whole_game_review_web.py tests/test_match_rollout_web.py tests/test_historical_opponent_profiles.py tests/test_historical_declarer_card_exposure.py tests/test_historical_defender_concession.py tests/test_historical_open_card_throw.py tests/test_historical_defender_open_play.py tests/test_variable_length_historical_decisions.py tests/test_frontend_localization_foundation.py tests/test_cli_internal_architecture.py tests/test_skatmind_rename.py -n 2 --dist=loadfile --max-worker-restart=0 -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-recheck --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-recheck.xml -q --tb=short
```

After that parallel recheck exits, the exclusive command and explicit Quick/
whitespace checks above complete local validation. Successful earlier unaffected
modules are not rerun for timing.

The 13-module correction recheck passed **382 tests in 524.99 s**. The first
exclusive run passed 58 tests and exposed ten synthetic partial-write cases whose
minimal handler lacked the newly required request context. Only that fixture now
supplies an inert `server.app_context`; all partial-write/no-second-response
assertions remain unchanged. Final documentation guards and the complete exclusive
module recheck use these commands before Quick:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_cli_internal_architecture.py -n 2 --dist=loadfile --max-worker-restart=0 -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-final-guards --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-final-guards.xml -q --tb=short
py -3.13 -m pytest tests/test_unified_rejection_transport.py -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-exclusive-recheck --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue326-exclusive-recheck.xml -q --tb=short
```

## Acceptance and remaining costs

After required local checks pass, report **locally validated; hosted acceptance
pending**. Quick certifies Ruff, schema byte parity and input examples, not full
regression, generated outputs or distributions. #326 remains open for automatic
partial branch feedback, published-source review, automatic exact-commit main
`check` and `v1-supported-platform-matrix`, then the maintainer's narrow installed
follow-up with existing #325 data. #208 and the existing paused UAT/release
boundaries remain open. Remaining multi-second and tens-of-seconds costs above
are explicit; source-only improvement does not resolve the installed findings.

## Published-source follow-up

Branch `task/326-responsive-analysis` started this follow-up clean at
`e518f97e94f9d00858eae4a44f367d7729e3f7d6`. Branch feedback run `44378038599`
passed its sole partial job. This is not main integration or complete acceptance.

### Recovery before and after

A source-only native HTTP probe bound the controller with a successful saved-list
GET, opened a new `AutomaticMatchLearningServiceV1` for the same app, then
retried the list and Reopen with the superseded owner. The published GET returned
500 without the saved-Review recovery link; the POST returned 400. The outer
wrappers acquired the controller before the localized conflict handler, and
the inner handlers acquired it a second time.

Both routes now acquire one controller and enter the operation inside the
existing recovery boundary. The GET's operation encloses view capture/resolution,
reader pins, projection and final delivery; the POST's encloses the original
mutation and redirect guard. Original-owner failure returns localized **409**
with the saved-Review recovery link for both requests. A German/English native
regression uses an empty archive location, checks the old owner is no longer
current and leaves the replacement owner intact. Transport byte-write handling
is unchanged.

### Why these two cost reductions

**Live Match result.** The saved-status renderer and header callback previously
performed independent full snapshots. A single private helper now captures the
status and its delivery guard together. Only for a saved notice it obtains a
fresh strict snapshot and optional bounded receipt from the Match archive store.
Only this response's guard holds the receipt. It asks that same store to recheck
exact bytes, manifest and inventory before delivering; it compares the admitted
snapshot and requires the exact evidence ID. After that unlocked work it checks
the archive owner/store, live Match, file, attempt, selection and Report again.
Pending, retry and incomplete-rollout display bindings retain their own checks.
No producer writes, other saved routes or Learning owner receipts change.

This deliberately buys **less semantic reconstruction, not less I/O**. An
eligible cold capture reads each object before, during and after admission;
final delivery reads it again. Beyond receipt bounds there is no receipt, so
both calls perform full strict admission. The genuine fallback regression uses
66 objects and 33 admitted executions, including the displayed Match analysis:
two admissions, 66 Result decodes and 132 reads, without changing limits.
Corrupting the displayed report with the same length and mtime between capture
and delivery yields 409. Changing the archive owner, live Report or selection
during final validation also withholds the prepared HTML.

**Guided Quick.** Profiling one original retained thirty-Play Quick envelope
(`0ad8ad0d340ee883c822fce041a5ef8302d175e78ef603cff799ebb9f5330d6a`)
separately from fixture construction identified repeat work *inside* necessary
validation. The audit already enumerates every canonical leaf in the current
document. For every exact field it then parsed the path, traversed the document
again and tested membership in that same leaf set. Membership alone proves
both resolution and leaf status, including empty containers. Subtree traversal,
coverage counts, overlap/exemption/orphan detection and all attachment checks
still run. The other local change directly splits slash-prefixed ordinary string
pointers with no `~`: their tokens are already unescaped and their canonical
re-encoding is identical, including empty tokens. Escaped pointers retain the
original strict decoder and round-trip check. Neither optimization caches a
document, skips a validation stage or changes any wire representation.

| One strict Historical decode (cProfile; inclusive) | Published | Follow-up |
| --- | ---: | ---: |
| `decode_historical_execution` | 79.663 s | 43.117 s |
| `unpack_native` (3 calls) | 49.725 s | 29.672 s |
| `decode_execution_value` (6 calls) | 43.851 s | 23.720 s |
| `validate_execution` | 27.820 s | 11.396 s |
| `validate_v1_retained_stage_linkage` | 25.152 s | 10.510 s |
| `build_field_provenance_coverage_summary` (282 calls) | 21.122 s | 4.782 s |
| `parse_json_pointer` | 309,605 calls / 31.828 s | 188,552 calls / 0.532 s |
| `resolve_json_pointer` | 126,541 calls / 16.294 s | 5,488 calls / 0.068 s |

All 121,053 exact-field lookups still ran. A count probe found **all 309,605**
pointer parses in the published fixture had no escape character. These timings
overlap and include profiler overhead; they are not user wait times. Strict
reconstruction and canonical re-encoding of the original native tuple remain
expensive. In particular, its execution and serialization checkpoint both carry
provenance. A larger, separate decision would be whether to encode the repeated
bundle once through an exact checked reference in a versioned private codec.
That could save decoding/round-trip work but would require legacy-wire admission,
identity, corruption and byte-preserving export evidence. No such format or
trust change is part of this correction.

### Paired response measurements

The following are sequential, source-only runs on **this** baseline and
candidate, not comparisons against a different day's machine timings. Each run
started with its own copy of the original 4-object disposable fixture. The same
guided draft, seed 11 and 25 samples were used. Both non-forced Match cases
selected decision 25 of the same genuine synthetic recording; rollout requested
25 worlds, Immediate 25 samples. Fixture creation/opening and selection are
outside the named POST/GET timings. Bytes here count archive object reads, not
HTTP payload size. Admission and decoding times are included in response times.

| Path | Wall s before → after | Full admissions | Retained Result decodes | Object reads | Object bytes read |
| --- | ---: | ---: | ---: | ---: | ---: |
| Guided Quick POST | 39.522 → 27.215 | 1 → 1 | 3 → 3 | 11 → 11 | 2,383,219 → 2,383,219 |
| Guided redirect GET | 22.000 → 16.660 | 1 → 1 | 3 → 3 | 20 → 20 | 8,701,764 → 8,701,764 |
| Match Quick rollout POST | 29.952 → 23.672 | 1 → 1 | 4 → 4 | 13 → 13 | 6,621,969 → 6,621,969 |
| Match rollout result GET | 52.754 → 20.269 | 2 → 1 | 8 → 4 | 14 → 28 | 8,821,508 → 17,643,016 |
| Match Quick Immediate POST | 39.164 → 29.199 | 1 → 1 | 5 → 5 | 17 → 17 | 13,292,518 → 13,292,518 |
| Match Immediate result GET | 62.221 → 24.375 | 2 → 1 | 10 → 5 | 16 → 32 | 17,620,432 → 35,240,864 |
| Forced current Session POST (direct 200, after other workflows) | 0.383 → 0.385 | 0 → 0 | 0 → 0 | 0 → 0 | 0 → 0 |

Both Match result archives are receipt-eligible: rollout has 7 objects /
4,410,754 stored / 62,874,427 expanded-accounted bytes; Immediate has 8 /
8,810,216 / 67,273,889. Candidate GETs spent 18.514 s and 20.425 s respectively
in admission. The final HTTP phases, including fresh authorization, took 0.175 s
and 0.313 s (published: 26.314 s and 31.626 s). The measured rollout engine
took 0.030 s; the delay is not attributable to rollout alone. Guided retention
took 27.212 → 20.614 s and first redirect admission 21.550 → 16.195 s. Both
guided runs made 30 recommendations, 1,200 sampled hidden states, two object
publications and one manifest publication. Lasting storage is not deferred.
The final stricter forced-card path needed no redirect, statistical work or save.

On the final candidate an independent **first** current-Session Quick request in
a fresh Python process took **3.380 s**. A separate fresh process timed the call
to `forced_card_guidance.validate_input_document` within the native request:
**3.537 s** first POST (**3.202 s** in schema validation), then **0.341 s** on
repeat (**0.004 s** there). This explains why the already-warm mixed-workflow
measurement is not a cold-response claim. Both returned the rule hint directly
(HTTP 200), with identical recording bytes, no execution and no initialized
archive. These probes used `current_session` and `localized_server` from the
existing test fixtures, submitting the native `/sessions/analyze` form with
`analysis_effort=quick`; construction, form retrieval and bootstrap were outside
POST timing. The two phase measurements are in `issue326-fu-after/final-forced.json`.

The 5,577-byte guided Request and 575,934-byte Result are identical to the
published bytes and hashes above. Recording SHA-256 is
`a7a471185e93ae0c8c50fd8c0c98cf059b396d5df79cf906f5c8135d14982ad7` in both runs.
All three Match Immediate downloads match byte-for-byte across runs. Rollout's
Request matches; the only differing Result leaf across independent executions
was `/whole_game_rollout_result/work/elapsed_ms` (44.6501 vs 43.8141). Each
execution's own original downloads remain exact; no timing field is rewritten.

### Follow-up verification

All commands use development CPython 3.13.7 on Windows, external temporary
outputs and 7,200,000-ms invocation timeouts. Prefix for the commands below:

```powershell
$D = "$env:TEMP/opencode"
```

Timings were obtained with `py -3.13 scripts/measure_responsive_analysis.py
--counts 2 --output "$D/issue326-fu-before" --fixtures "$D/issue326-fixtures"`
on the published source, then the same command with `--output
"$D/issue326-fu-after"` on the follow-up. The two `report.json` files contain
per-phase timings and work. The separate function profile bracketed only
`decode_historical_execution(envelope, entry, original_source)` with
`cProfile.Profile.enable()/disable()` after strict store open and source decode
on a disposable copy; the candidate profile is `issue326-fu-after/decode.prof`.
For example, the bounded profile can be reproduced at either source revision
with the original synthetic envelope (the temporary copy is outside the repo):

```powershell
@'
import cProfile, pstats, shutil, tempfile
from pathlib import Path
from skatmind.automatic_learning_store import AutomaticLearningStoreV1
from skatmind.automatic_historical_evidence import decode_historical_source, decode_historical_execution
base = Path.home() / "AppData/Local/Temp/opencode"
with tempfile.TemporaryDirectory(dir=base, prefix="issue326-profile-") as work:
    store = AutomaticLearningStoreV1(shutil.copytree(
        base / "issue326-after/2/managed/automatic-learning", Path(work) / "archive"))
    manifest = store.snapshot().manifest
    entry = next(e for e in manifest.evidence if e.envelope.fingerprint ==
        "0ad8ad0d340ee883c822fce041a5ef8302d175e78ef603cff799ebb9f5330d6a")
    record = next(r for r in manifest.sources if r.source_version.identity == entry.source_version_id)
    source = decode_historical_source(store.read_object(record.object_ref), record)
    envelope = store.read_object(entry.envelope)
    profile = cProfile.Profile()
    profile.runcall(decode_historical_execution, envelope, entry, source)
    pstats.Stats(profile).strip_dirs().sort_stats("cumtime").print_stats(42)
'@ | py -3.13 -
```

Focused regressions (10 passed in 138.52 s):

```powershell
py -3.13 -m pytest tests/test_automatic_historical_web.py tests/test_saved_match_analyses_web.py tests/test_field_provenance_coverage.py -k 'superseded_service_recovers or live_quick or live_match_refuses or exact_coverage_proves' -n 2 --dist=loadfile --max-worker-restart=0 -o "cache_dir=$D/issue326-fu-cache" "--basetemp=$D/issue326-fu-focused" "--junitxml=$D/issue326-fu-focused.xml" -q --tb=short
```

Complete module selection follows the saved Review and live Match HTTP/retention
boundaries, strict archive admission/delivery and the changed JSON Pointer and
coverage primitives through their Historical, Application, adversarial,
serialization and public consumers:

```powershell
$M = @('automatic_historical_web','saved_match_analyses_web','saved_match_rollouts_web','match_evidence_retention','match_rollout_retention','match_rollout_web','automatic_learning_delivery_receipt','automatic_learning_bulk_read','automatic_historical_evidence','automatic_historical_admission','field_provenance','field_provenance_coverage','application_provenance','historical_review_provenance','v1_provenance_enforcement','v1_provenance_serialization','v1_provenance_adversarial','public_field_provenance') | ForEach-Object {"tests/test_$_.py"}
py -3.13 -m pytest @M -n 2 --dist=loadfile --max-worker-restart=0 -o "cache_dir=$D/issue326-fu-cache" "--basetemp=$D/issue326-fu-affected" "--junitxml=$D/issue326-fu-affected.xml" -q --tb=short
```

The 18-module run passed **584 tests in 1,845.88 s**. One final retry-specific
regression verifies that already-expired consent hides the retry form but does
not drop the existing final owner guard. The complete direct Immediate and
rollout feedback modules passed **41 tests in 407.34 s** after that adjustment:

```powershell
py -3.13 -m pytest tests/test_saved_match_analyses_web.py tests/test_saved_match_rollouts_web.py -n 2 --dist=loadfile --max-worker-restart=0 -o "cache_dir=$D/issue326-fu-cache" "--basetemp=$D/issue326-fu-retry" "--junitxml=$D/issue326-fu-retry.xml" -q --tb=short
```

Final guards and exclusive checks use the following commands, in order. The
exclusive modules cover native Match result-page placement and rejection after a
transport write. The implementation does not change the early-observer harness
or standalone Corpus transport. No new file requires a no-index whitespace check.

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_cli_internal_architecture.py -n 2 --dist=loadfile --max-worker-restart=0 -o "cache_dir=$D/issue326-fu-cache" "--basetemp=$D/issue326-fu-guards" "--junitxml=$D/issue326-fu-guards.xml" -q --tb=short
py -3.13 -m pytest tests/test_match_analysis_action_placement.py tests/test_unified_rejection_transport.py -o "cache_dir=$D/issue326-fu-cache" "--basetemp=$D/issue326-fu-exclusive" "--junitxml=$D/issue326-fu-exclusive.xml" -q --tb=short
.\scripts\check.ps1 -Mode Quick -LogDirectory "$D/issue326-fu-quick"
git diff --check
git diff --cached --check
git ls-files --others --exclude-standard
```

These are targeted source checks; no full-suite timing, installed UAT or
publication is authorized. Keep #326 and #208 open. The remaining tens of
seconds in cold admission and synchronous retention are still user-visible.

## Failed main Check: Learning test setup and standalone Capture rejection

### Source and hosted evidence

[Check 44410006539, attempt 1](https://github.com/hnnng-w/skatmind/actions/runs/44410006539/attempts/1)
was a `push` to `main` at `f69afdf0ff524fe1393bb6c341b7e8be678b25ca`.
It ran for 61m23s (22:16:43 to last job completion at 23:18:06 UTC on
November 18, 2026). Of 23 jobs, 20 succeeded, including all twelve installation
cells and `v1-supported-platform-matrix`. The two regression jobs and the
dependent final `check` failed.

Before editing, `git status --short --branch` showed a clean worktree and
index on `task/326-responsive-analysis`. `git rev-parse HEAD` matched the run.
`scripts.validation_identity.source_identity()` on those untouched files returned
`86bb0eb0030dd7302d7c72daa113d2b6838b2308d5589124d1f4677744c2b0c3`.
Both regression `summary.json` files match **both** the commit and source digest.
The authenticated GitHub API records for the attempt, its jobs and its artifacts
were saved under `%TEMP%/opencode/issue326-main-44410006539`. The artifact
records identify `hnnng-w/skatmind` (repository `1221973482`), this run, branch
and SHA. Each producing job's upload log identifies its artifact ID and ZIP
digest. Hashing the downloaded ZIP bytes before extraction matched those
values and the API digests:

| Regression job | Artifact | ID | ZIP SHA-256 |
| --- | --- | --- | --- |
| Ubuntu `135175492903` | `regression-ubuntu` | `14481356359` | `ead2c9639b4577db5899638f148e7a6a8e5a497113d3173d571d3688030b67f4` |
| Windows `135175492906` | `regression-windows` | `14481335529` | `4388564a1258951f9fa252e8741f571885070ba88cb5fa754d0c6367ea780065` |

The ZIPs, extracted collection and parallel JSON/log pairs, summaries and
three complete failed-job logs are retained in that external directory.
The collection lists were checked node-by-node, not just by count.

| Hosted CPython 3.13.15 | Full collection (exit 0) | Parallel selection and worker agreement | Setup / call / teardown reports | Parallel outcome (exit 1) |
| --- | ---: | --- | --- | --- |
| Ubuntu | 12,843 | 12,748; all four lists identical in order | 12,745 pass + 3 skip / 12,741 pass + 2 fail + 2 skip / 12,748 pass | 12,741 passed, 2 failed, 5 skipped |
| Windows | 12,843 | 12,748; all four lists identical in order | 12,748 pass / 12,745 pass + 3 fail / 12,748 pass | 12,745 passed, 3 failed, 0 skipped |

Every parallel node has an outcome. Ubuntu has 38,241 phase reports: only
the three setup-skipped Windows junction cases lack a call report (store root,
store sources and recording-deletion root). Two further junction cases skipped
in call (Match inventory and direct-entry file boundaries). Windows has all
38,244 reports. On **each** platform the failed parallel stage stopped the
runner before the exclusive phase: no exclusive JSON, log or executions.
The 95 unexecuted nodes on each are `test_early_rejection_observer.py` (6),
`test_local_learning_corpus_web.py` (27), `test_match_analysis_action_placement.py`
(25) and `test_unified_rejection_transport.py` (37). These are not pytest skips.
Final job `135208409829` had `REUSE: false`, `regression.result: failure` and
successful other prerequisites. It exited 1 with `mode=full
reason=gate_prerequisites_invalid lookup=gate_prerequisites`; it did not run
another failing test.

### Tracebacks, reproduction and correction

* **Obsolete test setup, both platforms (`gw0`, call).** In
  `tests/test_learning_overview_navigation.py`, both
  `test_ordinary_match_navigation_and_comparison_preserve_two_sources` and
  `test_compact_rows_exact_player_comparison_return_language_and_downloads`
  called `analyze_retained(browser, 17)` (lines 67 and 131 at the failed commit).
  Its form submission reached `test_match_recording_recovery_web.py:29`, which
  asserted HTTP 303 and received 200. Both failures reproduced on the clean
  checkout. A source-only probe recorded ordinary mode, HTTP 200 with
  `forced-card-guidance`, and zero Reports. Explicit custom mode on that same
  decision returned 303 and an executed eight-world Request; `S8` was both the
  actual card and the only legal card. Recording bytes did not change.
  The helper now explicitly requests custom execution and checks the decision
  index, executed status and eight-world budget. The tests still require two
  genuine Reports, explicit inclusion, passive navigation and original
  downloads. Ordinary forced-card guidance remains the correct Product result.
* **Product defect in rejection/close sequencing, Windows only (`gw1`, call).**
  `tests/test_local_match_capture_web.py::test_host_cookie_origin_request_limit_and_security_headers`
  failed at line 812 in the invalid-Origin loop for `POST /api/v1/create`.
  `HTTPConnection.getresponse()` → `HTTPResponse._read_status()` →
  `socket.recv_into()` raised `ConnectionAbortedError: [WinError 10053]` before
  the expected 403 status could be read. The traceback does not identify the
  particular Origin iteration. The exact node passed locally. In a synchronized
  pre-fix split upload, all 618 submitted form bytes were still queued at socket
  shutdown; the local client did receive `403 Forbidden`. That establishes the
  unread-input close hazard, **not** a local reproduction of error 10053.
  A regression with the body withheld until the complete 403 arrives also
  failed against the previous handler (missing `Connection: close`).
  Standalone Capture now flushes its rejection, half-closes the sending side
  and discards opaque pending input, capped at 64 KiB with a 0.25-second
  cleanup deadline, as in the existing standalone Corpus transport. No body
  parsing or dispatch is authorized. The new test observes the late body and
  completion with no Workspace creation; the original security test is intact.

The only Product change is in `src/skatmind/capture_web/server.py`. Neither
failure implicated archive delivery, conflict recovery, provenance or Learning
isolation. The source probes are recorded in `before-selection.json` and
`before-split.json` in the external evidence directory.

### Local validation

Development CPython 3.13.7 on Windows; 7,200,000-ms invocation timeouts.
Equivalent PowerShell commands below use distinct external outputs:

```powershell
$D = "$env:TEMP/opencode/issue326-main-44410006539"
$P = @('-n','2','--dist=loadfile','--max-worker-restart=0','-o',"cache_dir=$D/cache",'-q','--tb=short')
$L = 'tests/test_learning_overview_navigation.py'
$C = 'tests/test_local_match_capture_web.py'
$N = @("${L}::test_ordinary_match_navigation_and_comparison_preserve_two_sources", "${L}::test_compact_rows_exact_player_comparison_return_language_and_downloads", "${C}::test_host_cookie_origin_request_limit_and_security_headers")
$S = "${C}::test_invalid_origin_delivers_complete_403_before_discarding_late_body"
py -3.13 -m pytest @N @P "--basetemp=$D/repro" "--junitxml=$D/repro.xml"
py -3.13 -m pytest $S @P "--basetemp=$D/split-before" "--junitxml=$D/split-before.xml"
py -3.13 -m pytest @N $S @P "--basetemp=$D/focused" "--junitxml=$D/focused.xml"
py -3.13 -m pytest $L $C tests/test_local_match_capture_web_analysis.py @P "--basetemp=$D/affected" "--junitxml=$D/affected.xml"
```

The untouched three-node run had **2 failed, 1 passed**. The split-upload
regression failed before the Product change; the corrected four-node run had
**4 passed in 19.80 s**. The two complete affected modules and the standalone
Capture analysis HTTP consumer had **104 passed in 75.94 s**. None of these
modules is assigned to the exclusive phase.

Final documentation/architecture guards, Quick and whitespace commands:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_cli_internal_architecture.py @P "--basetemp=$D/guards" "--junitxml=$D/guards.xml"
$env:Path = "$(py -3.13 -c 'import sys; from pathlib import Path; print(Path(sys.executable).parent)');$env:Path"
.\scripts\check.ps1 -Mode Quick -LogDirectory "$D/quick"
git diff --check
git diff --cached --check
git ls-files --others --exclude-standard
```

This local selection does not establish a successful full check. Keep #326
and #208 open; the corrected commit needs published-source review and fresh
exact-commit main gates.
