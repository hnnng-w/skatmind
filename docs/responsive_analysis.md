# Responsive advice and saved Reviews (Issue #326)

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
