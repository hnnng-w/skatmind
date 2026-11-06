# Faster complete validation

## Status and acceptance boundary

Issue #315 is a bounded follow-up to maintainer-accepted #279. The pending-#279
paragraphs below retain the original migration's point-in-time history, not a
reopening of its accepted behavior. #315 changes hosted regression workers from
two to four and adds diagnostic timing summaries. Its explicit local scope is
complete affected validation-tool modules plus `./scripts/check.ps1 -Mode Quick`,
using development CPython 3.13.7 and a 7,200,000 ms tool timeout for every validation
invocation. No local Full, distribution build/install, or installed UAT is required
for this task. Handoff is **locally validated; exact-commit hosted CI pending**.
Keep #315 open until the next normal hosted execution and main-gate evidence are
reviewed; no measured speedup is claimed before that execution.

Issue #279 changes validation tooling and governance only. Package version,
runtime dependencies, Product behavior, UAT installation/profile/recording, and
UAT/release decisions are unchanged. The new routine policy is **pending actual
CI acceptance**. Local coordinator tests and a local Full pass cannot close #279.
Until the maintainer accepts that evidence, the prior final-local-Full policy
continues to apply. Historical audit evidence remains point-in-time evidence.

After activation, routine agent completion is **locally validated, CI pending**:
focused tests plus Quick are sufficient for local handoff, with exact-commit full
CI required for acceptance. Validation-tool changes, diagnosis, relevant platform
changes, and release/platform evidence still require Full. Explicit task-specific
verification requirements take precedence.

## Commands

Install development tooling with `python -m pip install -e ".[dev]"`.
pytest-xdist is a development-only extra; no runtime dependency or version changed.

```powershell
python -m pytest tests/test_packaging_and_distribution.py
.\scripts\check.ps1 -Mode Quick
.\scripts\check.ps1                       # Full, unchanged default
.\scripts\check.ps1 -Mode Full -Workers 2
.\scripts\check.ps1 -Mode Full -Workers 1  # complete serial diagnostic path
```

`-Workers` accepts 1 through 8, default 2. `-LogDirectory` optionally selects a
fresh external directory. The cross-platform equivalent is
`python scripts/run_validation.py --mode Full --workers 2`; `--stage` selects one
explicit CI gate and never reports Full. Focused pytest is separate from Quick.

Quick means Ruff, exact packaged-schema filename/byte parity, and Root/Session
input-example schema validation. Full retains those gates, all 98 generated-output
scenarios, inspected Wheel/sdist and clean-install smoke/parity, and the entire
pytest suite. The separate all-six-cells local platform entry point remains:

```powershell
py -3.13 scripts/validate_v1_supported_platform_matrix.py
```

That platform runner remains distinct from local Full, as before #279. Its existing
compact normalized JSON and all assertions are retained. CPython 3.13 is the
certified interpreter. On a Windows development shell without a working `python`
command, use the documented `py -3.13` PowerShell function binding; never redirect
checks to the maintainer's installed UAT environment.

## Old-gate-to-new-gate coverage map

| Existing gate | Local site | Full CI site |
|---|---|---|
| Ruff | Quick and Full | `standards` |
| Packaged-schema filename/byte parity | Quick and Full | `standards` |
| Root/Session input examples | Quick and Full | `standards` |
| All 98 generated outputs | Full | `generated` |
| Wheel/sdist archive, metadata, license, RECORD, resources | Full distribution validator | `build (ubuntu/windows)` using the same inspection helpers; reinspection on consumption |
| Clean-install API, CLI, workflows, Session/Capture/Corpus/app, resources, errors, dependencies | Full distribution validator | All six `cell` jobs per OS, through the existing smoke helper |
| Raw resolved Wheel/sdist smoke equality | Full distribution validator | Each `matrix-result` (preserves this stronger original assertion too) |
| Six-cell normalized semantic parity, dependency/import inventory, source non-mutation | Separate local platform runner | Each `matrix-result` plus final evidence verification |
| Complete regression suite | Full | `regression (ubuntu)` and `regression (windows)` |
| Windows 11 / PowerShell 5.1 evidence | Real local platform runner and Full when required | Hosted Windows is additional coverage, not a replacement |

CI consolidates overlapping distribution build/smoke work into the inspected
build plus resolved Wheel/sdist cells. Every original assertion remains in the
existing helpers; resolved cells additionally retain the full seven-workflow CLI
matrix. Minimum cells still install exact `jsonschema==4.23.0`,
`referencing==0.31.0`, and `tzdata==2026.4`, install the artifact with `--no-deps`,
verify exact installed versions, and run `pip check`. No environment is reused.

## Pytest execution and isolation review

Full first collects the complete suite, then runs `--dist=loadfile -n <workers>
--max-worker-restart=0`, then the exclusive serial phase. The local default remains
two workers; both hosted regression lanes explicitly use four. Worker crashes are not
retried. Each worker must report the same complete selected collection. The final
accounting requires the two phases to equal the complete collection exactly once,
with no duplicate/unknown node IDs, missing execution, failed setup/call/teardown,
or incomplete teardown. Setup skips are retained as skips, never as passes.
New test files automatically enter parallel execution. One-worker diagnosis runs
all tests once in one process after the same collection check.
The final hosted verifier requires the committed four-worker policy, four matching
parallel collection reports, and zero worker collections in the exclusive phase.
A submitted worker count cannot choose its own policy. Missing/extra phases or
worker collections are rejected, including an absent parallel worker set. The
local serial diagnostic path instead requires one non-xdist execution phase.

The opt-in plugin changes no ordinary focused pytest invocation. Ambient
`PYTEST_ADDOPTS` and configured `addopts` cannot narrow the exhaustive runner.
It uses external pytest cache/report paths. Existing `tmp_path` and
`tmp_path_factory` isolation is retained; xdist supplies worker-specific temporary
roots. Module-scoped license fixtures stay within one worker. CLI subprocesses
use the current interpreter and test-local outputs. Real server fixtures use
ephemeral `port=0`; literal fixed ports in protocol tests are synthetic values.
Existing event synchronization, injected-clock Search tests, assertions, and
timeouts were inspected and retained.

These four complete modules run exclusively after parallel workers exit:

* `tests/test_early_rejection_observer.py`
* `tests/test_local_learning_corpus_web.py`
* `tests/test_unified_rejection_transport.py`
* `tests/test_match_analysis_action_placement.py`

They contain real socket teardown/early-rejection/late-body observers with tight
2/5-second bounds. This protects the previously unstable transport observation
checks from concurrent CPU-heavy tests. The actual isolation changes are process
separation, file grouping, external pytest cache/report paths, and this serial
phase. No Product timeouts, observer implementation, retries, xfails, blanket skips,
or existing Product test assertions were changed.

Existing capability skips remain explicit: Windows junction fixtures require
Windows, actual symlink fixtures may lack account privileges, and the JavaScript
unit harness requires Node. The new PowerShell-wrapper test requires an available
PowerShell executable (present on the intended hosted runners). Collection and
outcome reports expose these skips; no platform's skipped tests count as passes.
Synthetic runner tests also isolate the CI summary variable so mocked gate
results cannot be appended to an actual Actions job summary.

## Independent installation evidence

`scripts/validate_installation_cells.py` supplies three bounded operations:

```text
--build-bundle <external-directory> --expected-platform <id> --output <external-file>
--cell <name> --bundle <directory> --expected-platform <id> --output <external-file>
--aggregate <cell-evidence-directory> --bundle <directory> --expected-platform <id> --output <external-file>
```

The six names are `source-resolved`, `editable-resolved`, `wheel-resolved`,
`sdist-resolved`, `wheel-minimum_supported`, and `sdist-minimum_supported`.
Build manifests bind the Git commit, actual source-file content digest, exact
Wheel/sdist SHA-256 bytes, and detected environment. Cell consumers verify the
manifest against their checkout, rehash and reinspect the artifacts, and retain
the exact smoke for final comparison. Source/Editable install copied source;
Wheel/sdist install the actual artifact in a new external virtual environment.

The aggregate requires exactly six unique successful cells, exact manifest/source/
environment identity, reconstructed cell summaries, pinned minimum versions, and
full semantic equality under the existing normalization. It rejects missing,
duplicate, failed, cancelled, malformed, foreign-commit/platform/artifact, or
semantically incompatible evidence. Duplicate JSON keys/non-finite values fail.
Downloaded cell artifacts keep separate directories, so duplicate files cannot
silently overwrite one another. Only approved wall-clock fields and the existing
environment exclusion participate in semantic normalization; performance sidecars
never enter canonical Product outputs or semantic parity.

## CI graph, limits, and honest platforms

The workflow runs on all working-branch and main pushes, fork PRs to main, and
manual `workflow_dispatch`. Same-repository PR jobs are omitted in favor of their
branch push run; no privileged PR trigger executes fork code. A fork PR gets full
validation of its merge commit with read-only permissions. No PR is mandatory.

After `coordinator`, `standards`, `generated`, two regressions, and two builds can
run independently. Builds feed twelve cells (maximum four concurrent), followed
by two per-OS semantic aggregates. Regressions use four workers each. Matrix
`fail-fast` is false; required cells are allowed to finish for diagnosis. Exhaustive
jobs have explicit 180-minute budgets. Per-ref concurrency never cancels an active
run. This is a fixed graph, not changed-path test selection.

Stable final statuses are exactly `check` and `v1-supported-platform-matrix`.
Both run with `always()` and explicitly check every required upstream result.
`check` additionally reopens the standards/generated and both full pytest reports,
including complete collection accounting. The matrix gate checks both OS results.
Failed, cancelled, skipped, missing, or malformed prerequisites cannot make a
normal run green. The sole permitted skipped-worker case is separately reverified
exact candidate reuse.

Ubuntu uses `ubuntu-latest`, CPython 3.13, and the existing supported Ubuntu ID.
Windows uses `windows-2025`, records actual Windows Server edition/version and
Python, and emits `windows_server_github_actions_cpython_3_13` with evidence kind
`hosted_windows_installations`. It never emits the Windows-11 ID. The Windows-11
detector now also rejects Server product types, including Server builds above
22000. Hosted Windows does not certify Windows 11, Windows PowerShell 5.1 behavior,
installed browser UAT, or a browser-vendor matrix. Real Windows-11-specific
verification remains necessary for release, relevant platform-specific changes,
and installed UAT under the existing supported-platform contract.

Every `setup-python` step uses the single workflow-level
`VALIDATION_PYTHON_VERSION: "3.13.15"`. This exact CI toolchain selection prevents
independent runners from resolving the floating `3.13` request to different patch
versions. It does not change Package Python requirements or direct dependency
floors. Patch upgrades are deliberate workflow changes requiring full CI; the
recorded build/cell environment equality remains exact, including Python patch.

`setup-python` caches pip downloads keyed by OS/Python/`pyproject.toml`; no installed
venv, pytest outcome, or success file is cached. Every installation is fresh.
Transient Git environment settings select `core.autocrlf=false` and `core.eol=lf`
on both OSes, retaining exact source-byte comparison without changing Git config.
Both settings are necessary: `.gitattributes` marks unspecified text as `text=auto`,
so disabling `autocrlf` alone still permits Windows-native CRLF checkout for files
without an explicit `eol` attribute, including legal files and packaged CSS.

The first real branch run, [37624632241](https://github.com/hnnng-w/skatmind/actions/runs/37624632241),
at `5cf0f4d695ed9e4688f984e385ba28f30ba9cd17` exposed this boundary. Windows build
job `112803240797` reported `LICENSE does not use LF-only line endings.` Its
`build-evidence-windows` failure/timing artifact recorded exit `1` on Windows
Server 2025 / CPython 3.13.15. The local Full had checked an existing LF worktree,
not fresh checkout under the CI Git environment. The corrective test reads the
workflow's actual settings and uses read-only `git cat-file --filters` against
committed blobs with simulated Windows EOL defaults on either OS. It covers both
legal files, workflow YAML, packaged CSS, and an explicitly LF PowerShell control.
No checkout rewrite, byte normalization, weakened legal-file assertion, or source
digest normalization is used. The dependent matrix gates correctly reject failed
builds and skipped cells; full migration acceptance remains required.
The run subsequently completed with failure: Ubuntu regression accounted for
10,417 passed / 2 skipped, while Windows regression reported 10,323 passed and one
canonical-LICENSE hash failure matching the reproduced CRLF bytes. Its exclusive
phase did not run after that failure. Both final gates rejected the failed
prerequisites; no installation cell executed. This evidence does not activate the
routine policy or establish a successful hosted run of the correction.

The subsequent run, [37658614905](https://github.com/hnnng-w/skatmind/actions/runs/37658614905),
at `8bf44bc3c7763fd10358a349c828c144916b89e3` passed both builds, both regression
jobs, and all six Windows cells, confirming that the checkout-EOL failure did not
recur. Ubuntu `wheel-resolved` (`112920619903`), `sdist-resolved`
(`112920620218`), and `sdist-minimum_supported` (`112920619857`) each failed inside
`run_cell` with `Build and cell environments differ`. All three downloaded and
verified the same `build-bundle-ubuntu`; its manifest recorded Python `3.13.15`,
while those runners selected `3.13.16`. Failure preceded consumer virtual-environment
creation, dependency installation, and smoke execution. The successful Ubuntu minimum-wheel
cell and Windows build/cell evidence recorded matching `3.13.15` environments.

The exact shared pin above repairs that workflow selection mismatch without
relaxing artifact hashes, source identity, platform equality, or clean installation.
Focused tests enforce one shared exact patch for every job and preserve rejection
before installation for each affected cell when build and consumer patches differ.
The local reproduction uses the downloaded build artifacts and a simulated consumer
environment, not a claim of hosted Ubuntu execution. Both per-OS aggregates in
that run stopped at `Require every upstream cell` because the combined `cells`
dependency failed. Windows semantic comparison did not execute despite its six
successful cells. Both final gates propagated failure; the shared dependency and
all aggregate safeguards remain intact. The migration stays pending hosted
acceptance of the corrected workflow.

## Exact-commit integration and safe evidence reuse

After activation, the maintainer's routine sequence is:

1. Review focused tests and explicit Quick results; use Full when required above.
2. Manually commit/push the working branch. Agents leave edits uncommitted.
3. Wait for both final CI gates on that **exact commit**, including all workers.
4. Manually fast-forward that same commit into main.
5. Inspect main's `coordinator` summary and both final gates. Reuse must link the
   specific successful branch run; otherwise wait for the full new graph.

Read-only Actions API lookup permits reuse only for a successful completed **push
run on a non-main branch in this same repository**, with exact head commit,
workflow ID/path, and the same committed validation policy (`github.workflow_sha`).
All 23 expected jobs, including both final gates and every OS/cell worker, must
exist exactly once and have succeeded in that run's current attempt on the exact
commit. A mere green workflow label, PR run, reusable success file, older commit,
similar tree, partial rerun, or previously reused main run is insufficient.

The candidate must have started within **24 hours** of the main run's creation,
finished before it, and started after the immediately preceding main push run.
That preceding run must match the push event's `before` commit. The read-only
compare endpoint must establish that `before` is the merge base and the new commit
is ahead. Missing history, non-fast-forward integration, absent permissions, API
errors, stale/incompatible evidence, or uncertain identity all select full CI.
This defines one bounded current integration cycle and prevents reuse chains.

Both final gates recheck the selected candidate via the API. If it becomes
unavailable or ineligible after coordination, they fail closed; the maintainer
must use the force-full path rather than accept it. A manual `workflow_dispatch`
with `force_full` (default true) always executes the complete graph; ordinary
non-main pushes also always execute it. No agent triggers or reruns Actions.

Only `contents: read` is global; coordinator/final gates additionally need
`actions: read`. Checkout does not persist credentials. No PAT, external service,
self-hosted runner, or settings mutation is required. External prerequisite: the
repository must permit the official checkout/setup-python/upload/download actions,
hosted Ubuntu/Windows runners, and read-only Actions API access. If branch rules
are used, the maintainer should require the two stable final statuses; settings
remain human-controlled. Same-repository PR acceptance must reference the branch
commit run, not assume a skipped PR workflow validated a different merge commit.

### Historical reuse replay and decision diagnostics

Commit `8890916dfc66fd02cb761dfccb597309a008d288` passed all 23 jobs in branch run
`37679574939` and then all 23 again in main run `37689639795`. The main coordinator
logged only `Full validation required`. The exact historical rejection condition
is not recoverable from that log: the original event file and transient HTTP
responses were not retained. Authenticated later retrieval established these facts:

* main push activity `45780778599` at `2026-10-07T21:28:21Z` advanced from
  `6d264a442c4e7f88366de00effb972837c5f51d2` to that exact commit;
* the compare API reports `ahead`, with that previous commit as the merge base;
* the preceding main run is `37537963789`, created `2026-10-06T22:02:10Z`;
* the branch run was created `2026-10-07T20:06:56Z`, completed successfully by
  `20:53:53Z`, and retains all 23 successful attempt-1 jobs;
* main was created `2026-10-07T21:28:23Z`, the implementation's freshness cutoff.

A replay of the **unmodified** coordinator using those sanitized response
projections selects reuse. It uses the recorded historical cutoff and a frozen
`21:28:40Z` replay wall clock, never today's time. The current main run is excluded
from candidate proof, including its later successful results. Its event projection
contains only the observed push activity's `ref`, `before`, and `after`; it is not
presented as the original `GITHUB_EVENT_PATH` file. The fixtures retain the complete
23-job response shape and the relevant main-history rows. The real first history
page contained the immediately preceding main run; the complete candidate job set
fit on one page. Synthetic tests separately exercise multi-page and incomplete job
responses. No checkout-depth or ancestry relaxation follows from this evidence.

The corrective change therefore improves the demonstrated diagnostic gap without
changing reuse eligibility. Stdout and the existing job summary now identify the
selected `mode`, stable `reason`, lookup category, bounded numeric candidate run ID
when available, and the accepted source-run URL. For example:

```text
Validation decision: mode=reuse reason=eligible_candidate lookup=candidate_jobs candidate_run_id=37679574939 source_run=https://github.com/hnnng-w/skatmind/actions/runs/37679574939
Validation decision: mode=full reason=policy_commit_mismatch lookup=request
Validation decision: mode=full reason=api_http_error lookup=candidate_jobs candidate_run_id=37679574939 http_status=403
```

The latter two are synthetic diagnostic examples, not claims about the historical
fallback. Codes distinguish request guards, current/candidate identity, ancestry,
integration history, freshness/time order, complete job coverage, unsuccessful jobs,
attempt identity, malformed evidence, and unavailable API access. No-candidate
results identify the last rejected candidate where applicable. API exceptions emit
only fixed categories and an optional numeric HTTP status, never arbitrary exception
text, credentials, headers, or payloads. Final gates retain source revalidation and
reject invalid reuse authorization; `reuse`/`reuse_run` outputs and all downstream
worker conditions remain unchanged. Recorded-response entry-path tests establish
local behavior, not hosted reuse acceptance. #279 remains open until the maintainer
verifies a fresh branch-to-identical-main reuse path on GitHub Actions.

## Timing, failure diagnostics, and migration verification

Ordinary exhaustive pytest includes `--durations=40 --durations-min=1`. JSON
reports retain node IDs, setup/call/teardown outcomes/durations, collection, worker
count, commit/source digest, interpreter, platform, and installation mode.
Each validation stage reports wall time and exit status, with fail-fast local
propagation. Installation cells record form/lane and separate timing sidecars.
Source builds and fresh installation setup are included in their operation time;
Actions exposes dependency/tool setup and total job time separately.

Local logs default to a unique external temporary directory and remain available
for inspection. Stage stdout/stderr tails are bounded to 512,000 characters/2,000
lines. CI retains a bounded fixed family of reports/artifacts for seven days,
including failure sidecars; these are validation artifacts, not Release assets.
Summaries distinguish elapsed wall time from **summed** test phase time across
parallel workers. There is no extra benchmark run or timing-only acceptance gate.

Issue #315 adds `logical_cpu_count` (`os.cpu_count`) and `process_cpu_count`
(`os.process_cpu_count`) to the validation environment, with null when unavailable.
These observed CPU counts and the existing OS/image/interpreter metadata are
diagnostic; they neither auto-size workers nor authorize validation. After complete
accounting, `pytest-performance.json` and the job summary report each execution
phase's elapsed wall time, effective workers derived from its collection reports
(one for serial), setup/call/teardown sums, and the slowest 20 modules by summed
phase seconds, with module-name tie breaking. The complete per-test reports remain
available. The sidecar is separate from Product outputs and from final-gate
authorization; no timing threshold or performance-sidecar claim can replace the
strict execution reports. Failed invocations retain their existing raw reports
and logs without a successful complete-accounting/performance claim.

### Issue #315 retrieved baseline and follow-up findings

Authenticated read-only retrieval of run
[`42245301290`](https://github.com/hnnng-w/skatmind/actions/runs/42245301290)
at `310bd93370be0e88531c0ec31e61771227ee3bed` obtained `regression-ubuntu`
(artifact `13525366761`) and `regression-windows` (artifact `13524675830`). All
23 jobs succeeded. Workflow elapsed time was **105m47s**; the Actions pytest steps
were **104m41s** on Ubuntu and **89m40s** on Windows. The platform-matrix gate
completed **46m20s after workflow creation**. These are wall-clock observations,
not sums of test time and not a controlled before/after benchmark.

The retrieved `summary.json`, `pytest-parallel.json`, `pytest-exclusive.json`, and
`pytest-accounting.json` give the following values, rounded to hundredths of a
second. Recomputed per-test phase sums agree with the accounting files.

| Measurement (seconds) | Ubuntu | Windows |
|---|---:|---:|
| Validation entry-point wall time | 6,279.97 | 5,380.50 |
| Collection wall time | 24.90 | 17.43 |
| Parallel phase wall time | 6,126.79 | 5,257.84 |
| Exclusive phase wall time | 125.73 | 103.29 |
| Summed setup, all executed tests | 760.62 | 637.16 |
| Summed call, all executed tests | 10,656.37 | 9,046.16 |
| Summed teardown, all executed tests | 767.71 | 775.72 |
| Exclusive summed setup | 0.09 | 0.33 |
| Exclusive summed call | 81.44 | 65.09 |
| Exclusive summed teardown | 19.44 | 20.32 |

Each platform collected 12,271 tests: 12,176 in the parallel phase with two
matching worker collections, then 95 in the four exclusive modules. Ubuntu had
12,266 passes and five explicit skips; Windows had 12,271 passes. Both recorded
CPython 3.13.15. Ubuntu recorded image `ubuntu24` / `20261101.360.1`,
`Linux-7.0.0-1017-azure-x86_64-with-glibc2.39`; Windows recorded image
`win25-vs2026` / `20261030.294.1`, `Windows-2025Server-10.0.26100-SP0`.
These artifacts did **not** record CPU capacity or per-worker scheduling
timestamps, so baseline capacity and an observed end-of-run worker tail cannot be
reconstructed from them. The new capacity fields must be inspected on the next
hosted run. Windows Server evidence remains distinct from Windows 11/UAT evidence.

Largest parallel modules (all paths below are under `tests/`; values are summed
test-phase seconds, **not job wall time**):

| Module | Ubuntu setup / call / teardown | Windows setup / call / teardown |
|---|---:|---:|
| `test_automatic_match_learning_evidence.py` | 13.61 / 1,085.11 / 0.004 | 11.58 / 984.81 / 0.006 |
| `test_installed_cli.py` | 0.03 / 1,048.48 / 0.008 | 0.06 / 764.40 / 0.012 |
| `test_automatic_learning_delivery_receipt.py` | 702.46 / 55.66 / 0.003 | 575.87 / 44.30 / 0.005 |
| `test_automatic_match_evidence.py` | 3.69 / 692.67 / 0.008 | 3.17 / 583.98 / 0.011 |
| `test_saved_match_rollouts_web.py` | 0.03 / 413.46 / 4.95 | 0.07 / 341.29 / 4.51 |

Concrete follow-up opportunities, without changing fixtures or Product code here:

* Delivery-receipt tests repeatedly use the function-scoped `admitted` fixture to
  create/archive/prepare genuine evidence. Its module's setup dominates its call
  time (702.46s Ubuntu / 575.87s Windows). Any later reuse proposal must preserve
  independent mutation/corruption isolation and genuine evidence assertions.
* File grouping keeps each large module on one worker. The largest module totals
  1,098.72s Ubuntu / 996.40s Windows; its
  `test_all_methods_rollout_separation_restart_bytes_and_zero_analysis` call alone
  takes 619.59s / 555.35s. Installed-CLI coverage totals 1,048.52s / 764.47s.
  These are measured indivisible file workloads and possible tail bottlenecks,
  not proof of when either worker finished. Four workers cannot split such files.
* Teardown totals remain 767.71s / 775.72s across the full suite; the largest
  individual teardown observations are about 0.5s in web-server fixtures. Preserve
  observer isolation and timeouts in any subsequent investigation.
* Exclusive `test_match_analysis_action_placement.py` contributes 67.79s / 54.45s
  summed time; the other exclusive modules total 17.23s / 15.97s (Corpus web),
  15.44s / 14.80s (unified rejection), and 0.51s / 0.51s (early rejection).
  All four stay serial after parallel workers exit.

Local #315 verification on development CPython 3.13.7 passed all 205 tests across
the complete validation runner, CI validator, recorded-reuse, and packaging-policy
test modules in 16.42s. The subsequent four-module exclusive run, after all parallel
workers exited, reported 94 passes and one failure in 92.82s:
`test_match_analysis_action_placement.py::test_actual_analysis_route_bounds_and_strict_fields`.
Its full-upload observer received Windows `ConnectionAbortedError(10053)` with no
response bytes after sending 1,048,577 bytes. No Python processes remained after
the run. One bounded diagnostic invocation of the complete failing module then
passed all 25 tests in 58.75s. The original serial-run failure remains a concrete
intermittent transport-observation finding for hosted acceptance; the diagnostic
pass is not a clean original-run result or proof of a cause/fix. No test, fixture,
observer, timeout, retry policy, or Product behavior was changed to obtain it.

The changed hosted graph, complete accounting, observed capacity/effective workers,
before/after wall times, remaining critical path, and both exact-commit main gates
remain maintainer acceptance work for #315. Accepted #279 behavior and #292–#313
Product scopes are preserved. #314 installed acceptance is separate and pending;
#208 remains open, formal UAT-02–12 remain paused, and release preparation is not
authorized.

The historical #278 observations were 10,330 passed / 3 skipped in 3890.52 pytest
seconds plus other local gates, and roughly 90 minutes for CI run 37537963789 at
`6d264a442c4e7f88366de00effb972837c5f51d2`. These are not a controlled benchmark.
The migration's final measured results belong in its completion report, avoiding
a post-validation documentation edit. Environment/collection differences must be
reported; no specific speedup is promised.

Focused machinery tests use synthetic evidence and tiny subprocess suites for
selection, exit propagation, collection completeness, artifact/source identity,
strict cell aggregation, exact reuse, fallback, and negative gate cases. Existing
packaging, license, platform, schema, and generated-scenario assertions remain.
The migration requires one final unchanged-tree local Full run with actual tool
timeout **at least 7,200,000 ms**, followed by real branch CI acceptance. If a run
is interrupted, inspect its original process/logs before another invocation.
Never start duplicate full checks or repeat a successful unchanged-state run.

Local tests do not execute GitHub Actions. #279 stays open until the maintainer
records the real graph's required jobs, timings, detected environments, aggregation
behavior, and exact-commit reuse/main fallback. No overall UAT or release readiness
claim follows from validation-tool acceptance.

## Issue #315 correction after failed run 42276626496

The bounded correction started on `feat/315-faster-regression-ci` at the expected
commit `2ffd3be0bf753ec3d780cacf70ceb6c537ab87fd`, with a clean index and worktree.
Authenticated read-only retrieval inspected the completed attempt-1 run
[`42276626496`](https://github.com/hnnng-w/skatmind/actions/runs/42276626496),
the failed logs for Ubuntu job `128094628924`, Windows job `128094629072`, and
aggregate `check` job `128127873819`, plus regression artifacts `13536356585`
(Ubuntu) and `13536779516` (Windows). Retrieval succeeded without missing evidence.

The graph had 20 successful jobs and three failures: both regressions and `check`.
All twelve installation cells, both matrix aggregates, and
`v1-supported-platform-matrix` succeeded. The aggregate `check` log records
`regression.result = failure` and
`reason=gate_prerequisites_invalid lookup=gate_prerequisites`: this was correct
fail-closed prerequisite propagation, before regression artifact validation.

### Complete hosted failure inventory and phase boundary

Both raw parallel reports contain exactly one failed call, with the same node ID:

```text
tests/test_v1_supported_platform_matrix.py::test_ci_preserves_final_gate_names_and_complete_platform_coverage
```

Both log tracebacks identify worker `gw2`, CPython 3.13.15, and the same assertion
at line 346 (Windows uses backslashes in the traceback path):

```text
>       assert "--stage pytest --workers 2" in workers
E       assert '--stage pytest --workers 2' in 'name: Check\n...'
tests/test_v1_supported_platform_matrix.py:346: AssertionError
```

The quoted workflow value is abbreviated here; the retrieved logs retain pytest's
full displayed assertion. There were no other failing test nodes or failed
setup/teardown reports on either platform.

| Raw evidence | Ubuntu | Windows |
|---|---:|---:|
| Complete collection / collection exit | 12,331 / 0 | 12,331 / 0 |
| Parallel selected and executed node IDs | 12,236 | 12,236 |
| Parallel passed / failed / skipped | 12,230 / 1 / 5 | 12,235 / 1 / 0 |
| Parallel exit | 1 | 1 |
| Matching worker collection reports | 4, each 12,236 IDs | 4, each 12,236 IDs |
| Observed logical / process-usable CPUs | 4 / 4 | 4 / 4 |
| Collection wall seconds | 13.217 | 17.406 |
| Parallel wall seconds | 2,643.577 | 3,864.769 |
| Validation entry-point wall seconds | 2,656.836 | 3,882.426 |
| Exclusive phase | Not executed | Not executed |

Raw reports match the selected parallel collection exactly, without duplicate or
missing execution-phase records; Ubuntu's five skips comprise three setup skips
and two call skips. The unexecuted 95 collected tests belong exactly to the four
exclusive modules: early rejection (6), Corpus web (27), unified rejection (37),
and Match analysis action placement (25). Both runners stopped after parallel exit
1. There is no exclusive report/log, complete accounting, or performance sidecar.
`pytest-performance.json` is intentionally written only after successful complete
accounting; its absence here is expected, not a defect.

The run therefore provided **no new execution** of
`test_match_analysis_action_placement.py::test_actual_analysis_route_bounds_and_strict_fields`.
The earlier local Windows `ConnectionAbortedError(10053)` and successful bounded
diagnostic rerun above remain historical evidence with no newly established cause
or fix. No additional Product failure was found in this run's executed tests.

Workflow elapsed time was **66m28s**; Actions pytest-step times were **44m17s**
(Ubuntu) and **64m42s** (Windows). These are **failed-run observations only**, not
accepted complete-suite speedup evidence. The successful baseline from run
42245301290 remains unchanged. In particular, the failed run omitted exclusive
execution, collected 60 more tests than that baseline, and used a newer Windows
image (`win25-vs2026` / `20261103.298.1`).

### Narrow correction and local verification

The earlier affected-module inventory **omitted the complete
`tests/test_v1_supported_platform_matrix.py` module**. Its stale assertion still
required `--stage pytest --workers 2` after the hosted workflow was approved and
changed to four workers. Before editing, the exact failing node was reproduced
on development CPython 3.13.7: **one failure in 0.44s**, at the same line 346.

The only test change replaces that literal expectation with
`--stage pytest --workers 4`. Every other substantive assertion in that test is
retained: both final gate names and commands, build/cell/aggregation commands,
Ubuntu and hosted Windows identities, the Windows-11/PowerShell-5.1 distinction,
the exact shared Python pin, final-gate separation, triggers, and publication
restriction. A related-expectation search across tests, scripts, and workflow
configuration found no other stale hosted two-worker requirement. Existing local
two-worker defaults and serial diagnosis remain intentional.

The correction affects only this complete test module; it changes no helper,
caller, validation-tool contract, workflow, or Product code. The prior validation
runner, CI validator, recorded-reuse, and packaging-policy results are reused as
unaffected evidence. No exclusive module is affected, and no transport diagnostic
was repeated. The four-worker policy, file grouping, disabled worker restarts,
complete accounting, all four exclusive assignments and phase ordering, 23-job
graph, twelve cells, strict final gates and reuse eligibility, and diagnostic-only
timing boundary remain unchanged.

Exact effective local commands (after verifying the external cache parent exists):

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
& "C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe" -c "import sys; print(sys.version); assert sys.version_info[:3] == (3, 13, 7)"
# Before editing: 1 failed in 0.44s.
& "C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe" -m pytest -q -o "cache_dir=C:\Users\HENNIN~1\AppData\Local\Temp\opencode\issue315-correction-pytest-cache" tests/test_v1_supported_platform_matrix.py::test_ci_preserves_final_gate_names_and_complete_platform_coverage
# After correction: 19 passed in 6.01s.
& "C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe" -m pytest -q -o "cache_dir=C:\Users\HENNIN~1\AppData\Local\Temp\opencode\issue315-correction-pytest-cache" tests/test_v1_supported_platform_matrix.py
function python { & "C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe" @args }
.\scripts\check.ps1 -Mode Quick
```

Every validation tool invocation uses timeout **7,200,000 ms**. Local scope is the
complete affected module plus explicit Quick; no local Full, distribution
build/install, installed UAT, or extra exhaustive benchmark is part of this
correction. Explicit Quick passed with exit 0 in **3.578s**: Ruff 0.133s,
packaged-schema parity 0.122s, and input examples 2.952s. Its retained log directory
is `C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-uv3059wi`. Only this
documentation result was appended after Quick; the tested assertion is unchanged.
Status: **locally validated; new exact-commit hosted CI pending**.

Keep #315 open for new exact-commit hosted execution of both complete regression
lanes, including the exclusive phase and strict accounting, all 23 jobs and both
final gates, followed by exact-commit main-gate/reuse review. Accepted #279 behavior
and #292–#313 Product scopes remain intact. #314 installed acceptance is separately
pending. #208 stays open, formal UAT-02–12 remain paused, and release preparation
is not authorized.
