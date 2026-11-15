# Issue #321 CI and bounded source-review correction

## Starting state and retrieved evidence

The correction started on `feat/321-event-context-checkpoints` at
`159f2fb1a5be02e2805154b161ca0952e00a2ee2`, with a clean index and worktree.
Authenticated read-only GitHub retrieval succeeded for
[run 43652946992](https://github.com/hnnng-w/skatmind/actions/runs/43652946992),
attempt **1**, a push of that exact branch/commit. No new run was triggered.

Retrieved artifacts include both complete regression artifacts, all twelve small
installation-cell failure/timing artifacts and both build-evidence artifacts.
The full wheel-resolved job logs were also inspected on both platforms. Important
artifact/job identities are:

| Evidence | Artifact ID | Job ID |
| --- | --- | --- |
| Ubuntu regression | 14138302813 | 132625257691 |
| Windows regression | 14139305086 | 132625257642 |
| Ubuntu wheel-resolved cell | 14137795475 | 132625606228 |
| Windows wheel-resolved cell | 14136834563 | 132625606223 |
| Ubuntu build evidence | 14136766745 | 132625257707 |
| Windows build evidence | 14136643509 | 132625257727 |

Both regression summaries and both build results identify the same commit and
source digest:

```text
d78da652cab9a8428362838214f0b44c580d6182d846d9e5076e24a1fc05c4a8
```

Both regressions used CPython 3.13.15 and four file-grouped workers. Ubuntu reports
image `ubuntu24 / 20261111.127.1`; Windows reports
`win25-vs2026 / 20261103.298.1`, Windows Server 2025. This is hosted-platform
evidence, not Windows 11 or maintainer installed acceptance. Cell failure files
do not themselves contain source digests; their artifact `workflow_run` metadata
binds them to this run/commit, and the inspected full cell logs confirm the exact
checkout and same-run bundle downloads.

### Complete regression failure inventory

Both platforms failed all seven instances of:

```text
tests/test_direct_match_evidence.py::test_exact_new_and_legacy_registry_identity
  [set_perspective_hand-perspective_hand_selected-exact]
  [set_perspective_hand-perspective_hand_unknown-unknown]
  [set_original_skat-original_skat_selected-exact]
  [set_original_skat-original_skat_unknown-unknown]
  [set_discarded_cards-discarded_cards_selected-exact]
  [set_discarded_cards-discarded_cards_unknown-unknown]
  [set_discarded_cards-discarded_cards_empty-known_empty]
```

Each traceback reaches the exact `len(FRONTEND_FORM_REGISTRY) == 136` assertion
at line 159 and reports actual **149**. The preceding route/form identity and
field-preservation assertions pass.

Both also failed:

```text
tests/test_packaging_and_distribution.py::test_installed_smoke_frontend_registry_contract_executes
```

Its traceback reaches `installed-smoke.py:1`, the exact extracted smoke fragment's
`len(UNIFIED_FRONTEND_POST_ROUTES) == 84` assertion. Actual runtime inventory is
**97 POST routes / 149 forms**.

Windows alone additionally failed:

```text
tests/test_match_decision_selection_web.py::test_selection_supersedes_inflight_analysis_before_publication[rollout]
```

The old rollout's expected 409 assertion passed; the newer enhanced selection
returned **409 instead of 200** at line 191. There were no other failed setup,
call or teardown records in the retrieved regression reports.

### Executed and unexecuted phases

Raw collection and execution reports were reconciled, including unique node/phase
records and all four identical worker collections:

| Phase/count | Ubuntu | Windows |
| --- | --- | --- |
| Complete collection, exit 0 | 12,512 | 12,512 |
| Parallel selected/executed nodes | 12,417 | 12,417 |
| Passed / failed / skipped | 12,404 / 8 / 5 | 12,408 / 9 / 0 |
| Collection wall seconds | 16.474 | 14.876 |
| Parallel wall seconds | 3,700.465 | 3,868.404 |
| Validation entry-point wall seconds | 3,716.983 | 3,883.452 |

Ubuntu's five skips comprise three setup skips and two call skips. Both runners
stopped after parallel exit 1. The 95 unexecuted nodes are exactly:

* `test_early_rejection_observer.py`: 6;
* `test_local_learning_corpus_web.py`: 27;
* `test_unified_rejection_transport.py`: 37;
* `test_match_analysis_action_placement.py`: 25.

Neither artifact contains an exclusive report, completed accounting or successful
performance summary. The exclusive phase must not be inferred from job status.

### All twelve installation cells

All six forms/lanes on each OS were inspected: `source-resolved`,
`editable-resolved`, `wheel-resolved`, `sdist-resolved`,
`wheel-minimum_supported` and `sdist-minimum_supported`. Every small failure record
has the same diagnostic:

```text
DistributionValidationError: Command failed with exit code 1
  .../consumer-<cell>/installed-smoke.py, line 221
  assert len(UNIFIED_FRONTEND_POST_ROUTES) == 84
AssertionError
```

The two full wheel logs agree with those records and show successful bundle
download before the smoke execution. All twelve cells reached their installed
smoke, but none produced a completed cell-result JSON. Assertions after that
failure and subsequent full cell validation did not complete. Their next stale
form-count assertion was also corrected, without removing installation checks.

Standards, generated outputs and both builds passed. Both matrix-result jobs
failed at **Require every upstream cell**; their aggregation steps did not execute.
Both final gates failed their upstream prerequisites. These are failed-run facts,
not accepted installation or complete-suite evidence.

## Corrections and runtime reproductions

### Exact registry consumers

The installed smoke now asserts exactly **97 / 149** and the direct-evidence test
asserts exactly **149**. Route identity, form identity, field preservation and all
installation checks remain. Searches of direct registry consumers found no other
current CI assertion needing this update. Optional evidence scripts mostly report
actual counts; the old #269/#271 independent-Wheel scenario explicitly pins its
historical inventory and was inspected without executing or rewriting that
accepted historical scenario.

### A. Explicitly mapped equivalent concessions

Genuine accepted Session Logs with consistently renamed source-local participants
reproduced false conflicts for declarer consent, defender concession and both
supported continuation structures. Identity normalization now covers only their
explicit participant-reference fields inside `game_end` and `game_events`.
Declaration, trace, concession form, actors, outcome and all other game facts remain
meaningful. Equivalent mapped recordings contribute once; genuine actor,
declaration, trace and outcome differences still conflict. No ending support was
added.

### B. Unchanged comparison versus exact source freshness

A genuine position-25 discrepancy was reconfirmed and saved. Appending one legal
Card in game 26 preserved all compared outcomes but changed the Workspace version,
revoking the old acknowledgement. This reproduced after correcting two initial
test-fixture API mistakes, before changing Product behavior.

Version-2 semantic comparison identity excludes whole-document revision/content
fingerprints but includes the actual compared position facts, checkpoint values,
source identities/contracts, relevant participant mappings and scoring sources.
Changed results, relevant earlier facts, mapping or checkpoint require a fresh
reconciliation. Exact source versions remain in every consumed basis and in
current-preparation, form and CAS checks. A valid acknowledgement never authorizes
a stale save or stale active preparation.

This needs explicit preparation/journal versioning: replaying an old frozen
`conflict` under new acknowledgement rules must not silently turn it into `ready`.
`PreparedEventContextV1` and version-1 journal decoding retain their original field
sets, domains and reconstruction semantics. New `PreparedEventContextV2` values
retain semantic identities and any consumed legacy acknowledgement bridges.
`EventContextJournalV2` strictly discriminates version-1/version-2 preparations and
validates bridges against retained exact original comparisons and context revisions.
The private service entry point remains `prepare_event_context_v1()`; its new
result explicitly declares version 2.

Passive load and equal save preserve old bytes. An explicit changed save produces
a version-2 journal while retaining all earlier values. Regression evidence freezes
the original v1 journal fingerprint
`530d4b65725f35b2ae1cd000114c73231a8a9f0e64897f54cc2b8bce25747eec`
and byte SHA-256
`badc00b3c8dbe991dc8205aefcbed9845d756c7a38ab50977ba7ec8cc4d7aa37`,
captured before Product changes at the starting commit. Its original statuses
remain `conflict / ready / conflict`. A new preparation can recognize the same
retained semantic comparison as acknowledged without rewriting those statuses.
Unsupported versions, forged bridges, changed old statuses and downgrade fail.

An old concession comparison whose opaque outcome identity changes under A cannot
be retroactively normalized from that hash alone. Its frozen value remains exact;
new evidence requires explicit reconfirmation when the retained basis cannot prove
equivalence. No current recording is substituted to invent missing original facts.

### C. Cent scoring-source confirmation

The ordinary native Session form reproduced saving `cent_game_points_v1` alongside
the prefilled ISKO list-contribution source. New context forms now leave both
source and edition empty for explicit confirmation. Native submission without them
is rejected with preserved mode/values; supplying the actual Cent source succeeds.
Explicitly supplied and already saved provenance is not overwritten. No JavaScript,
financial calculation or Cent execution was introduced.

### Additional hosted selection failure

A deterministic two-request test reproduces the hosted 409/200 mismatch: an older
cancelled rollout publishes shared validation feedback after the newer selection
captured its rendering source, invalidating the newer page's final language-source
check. Accepted Match analyses now retain their request-scoped feedback owner.
Rejection checks that owner atomically with feedback publication. Superseded work
returns its own localized conflict response without publishing into the newer
selection's feedback or rendering source. Existing cancellation, execution budgets,
freshness checks and the original response assertions remain intact.

## Scoped validation and handoff

Complete affected modules cover packaging's exact smoke fragment, direct Match
evidence, form preservation, all four event-context modules, Match selection and
rollout HTTP/cancellation callers, and the complete architecture and rename guards.
The shared server rejection path also requires the existing exclusive unified
rejection-transport and Match-action-placement modules after parallel workers exit.
Standalone Corpus transport and the synthetic observer are unchanged. The changed
smoke fragment is executed directly by its existing packaging regression; no
distribution build/install is necessary to reproduce or verify this assertion fix.

Final commands, outcomes and durations are reported after documentation and code
are complete. Local validation uses development CPython 3.13, two file-grouped
workers, 7,200,000 ms invocation timeouts, external temporary outputs, then explicit
Quick and tracked/new-file whitespace checks. No Full, blanket previous-selection
rerun, hosted trigger or UAT build/environment access is part of this correction.

Keep #321 open for new exact-commit branch/main gates and combined installed
acceptance with the following accounting/Cent issue. No intermediate UAT is
requested; #208 and release acceptance remain open.
