# Faster complete validation

## Status and acceptance boundary

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

Full first collects the complete suite, then runs `--dist=loadfile -n 2
--max-worker-restart=0`, then the exclusive serial phase. Worker crashes are not
retried. Each worker must report the same complete selected collection. The final
accounting requires the two phases to equal the complete collection exactly once,
with no duplicate/unknown node IDs, missing execution, failed setup/call/teardown,
or incomplete teardown. Setup skips are retained as skips, never as passes.
New test files automatically enter parallel execution. One-worker diagnosis runs
all tests once in one process after the same collection check.

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
by two per-OS semantic aggregates. Regressions use two processes each. Matrix
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

`setup-python` caches pip downloads keyed by OS/Python/`pyproject.toml`; no installed
venv, pytest outcome, or success file is cached. Every installation is fresh.
Transient Git environment settings disable automatic checkout newline conversion
on both OSes, retaining exact source-byte comparison without changing Git config.

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
