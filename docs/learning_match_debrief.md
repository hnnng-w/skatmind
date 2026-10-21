# Retained Match post-game debriefs

Issue #289 adds a private player-facing post-game review from completed selected-
Decision whole-game rollout Reports. The starting branch is
`feature/289-learning-debrief`, at
`dede3606eb6e7ee64b042b06f4b6f6fd0bb757f9`. Issue #289 and its follow-ups #290 and
#291 are now closed. Issue #293 separately corrects prepared-result navigation;
#208 remains open pending maintainer UAT acceptance.

The completed navigation/presentation correction starts from installed baseline
`28b8e5a1f69ec2d38dc22bb597b1eb0d897dc02a`. See
[Collection overview navigation](learning_overview_navigation.md) for the named
incorporation action, compact rows, passive current-context entry, diagnostic
limits and fresh before/after evidence. The earlier browser and validation
measurements below remain evidence for the original implementation only.

## Two entries, one retained comparison

* The detailed Match Report is the normal individual result. When a compatible
  active collection is resolved it directly offers **Add to {collection}** and
  **Open analysis overview**. Otherwise the user explicitly chooses a collection
  through the existing collection list or resolves the selected-Snapshot mismatch.
  **Summary of this Report only** remains an optional disclosure and supported
  collection-free captured route, not a prerequisite for incorporation.
* An opened collection offers currently available completed Reports from the
  active Match's bounded report store. Every offer names the Match, Game, Trick,
  Card position, acting Player, objective, requested worlds, seed, revision,
  supplements when present, and target collection. **Add to {collection}**
  performs the explicit source update. One valid option needs one button press;
  several options remain separate. Acceptance redirects to that captured
  collection overview and delivers the existing compact receipt. There is no
  file round trip or report scan.

The shared debrief shows recorded-decision, distinct included analyzed-decision,
and exact Report counts. Native Player links select the view in the URL itself;
there is no unapplied dropdown behind a differently bound action. A Player filter
counts only that stable Player's recorded decisions. Scope captions explicitly
identify the whole-game comparison family. Existing prepared qualified Search
focuses remain a separately identified family.

Every concrete entry shows the actual Card, the complete authoritative tied-best
set, the retained comparison explanation, objective and common-world coverage.
The compact entry uses the shared rollout projection's exact comparison wording;
**View comparison** uses the existing full result renderer and number formatting.
The detailed comparison and its downloads read the captured evidence. They do
not depend on the active Match Report or re-execute simulation.

Recorded bid and manual supplements are visibly separate. An analysis assumption
such as matadors `1` is never written back to the recording or required to appear
in it. The top-level qualification describes fixed-policy simulation evidence,
not a mistake, guaranteed advantage, calibrated probability or strategic cause.

With no included comparisons, one source-scoped explanation and the existing
recorded-decision chooser replace the old stack of empty technical results.
Compatible Reports are offered explicitly. Missing selected Snapshots link to
Add; incompatible selections link to the existing version controls. Neither
remedy imports a version, switches Current or discards a Report automatically.

Dataset preparation remains the existing separate operation, now named
**Prepare dataset** / **Recreate dataset preparation**. Its settings, coverage,
ten downloads and diagnostics are under **Dataset preparation and exports**.
Issue #293 adds a [source-bound prepared-result view](learning_prepared_result_navigation.md).
Explicit View and successful preparation open the disclosure and focus the actual
`learning-results` heading. Ordinary collection entry stays compact. Validation
feedback retains focus priority and opens its affected form.

## Narrow evidence and reconciliation

`match_debrief.py` defines immutable `MatchDebriefEvidenceV1`, separate from
Strategy Teacher evidence. It requires an exact completed `MatchAnalysisReportV1`
with an exact executed rollout `MatchDecisionAnalysisResultV1`. It re-enters the
existing Report identity, options, typed rollout derivation/aggregate/comparison
and output-schema boundaries, and reconciles generic Result settings and legal
Cards with those retained values. Raw mappings, filenames and captions are not
source bindings. Partial, timeout and unavailable Reports cannot become completed
comparison evidence.

Capture verifies the managed source handle, attached context, strictly loaded
file, canonical content fingerprint and current Report store. The immutable
original Snapshot must equal the content identity retained in the derivation.
For incorporation, the collection's selected Snapshot is resolved through the
existing strict Current resolver. Match, revision, Game, Decision, stable actor,
actual Card, original before-card Request and relative Profile binding reconcile.

The reconciliation deliberately preserves the existing policy: a same-revision
metadata-only alternative, or another same-revision recording with the identical
safely reconstructed Decision Request, can be compatible. Target whole-Workspace
byte equality is not substituted for Decision reconciliation. The original
captured content identity remains separate from the selected target Snapshot.
Known-value overwrites and changes outside the existing permitted rollout
transformation remain rejected. Fingerprints establish identity and consistency,
not independently authenticated historical truth.

The root still uses only safely reconstructed acting-own-hand knowledge and the
accepted before-card prefix. Original and effective Requests and Results remain
immutable. No later opponent ownership, observed continuation, final scores,
inferred Skat or sampled hidden World is promoted to root knowledge.

## Variants, topics and retained focuses

Exact duplicate bindings are no-ops. Distinct Reports, including elapsed-only
variants, remain individually accessible. The semantic count removes only the
rollout's operational `work.elapsed_ms`; seeds, objectives, policies, budgets,
assumptions, coverage and comparisons remain significant. Distinct Decision
References, rather than Report counts, determine the reviewed-decision count.
Different comparisons or tied-best sets mark the Decision as mixed. No preferred
run, average or new consensus score is selected.

Optional situation grouping consumes already-prepared Tactical Motif evidence;
displaying a debrief never runs the full dataset pipeline to obtain it. Joins use
Snapshot, Game Reference, Decision Reference, stable actor and actual Card.
Categories count distinct Decisions and Game References per Player. Two Reports
of one Decision, or two Decisions in one Game, cannot become two Games. A report
without a motif still has its concrete entry. Categories make no causal or
Player-weakness claim.

Already-prepared qualified Coaching focuses render their retained Player, motif,
Decision/Game counts and fixed Guidance code/content. Presentation does not
recompute thresholds. Rollout never becomes `complete_search`; the existing
complete-Search eligibility, exact Teacher evidence, Dataset-v2 joins, partition
semantics and training labels remain unchanged. The old Teacher source codecs
and `strategy-source.json` routes continue to reject rollout. There is no new
public API, Root workflow, Schema, persisted source format or training artifact.

## Lifetime and publication guards

The unified app retains at most eight immutable debrief scopes, using the existing
Match report-store bound. A direct scope is a captured read-only view: Match
navigation and later report eviction do not substitute its comparison. Scope
eviction or process restart yields a concise expiry remedy. It is not a hidden
persistent collection.

Each active unified collection owns a separate bounded store of up to 2,048
debrief source copies. Successful incorporation increments that store's revision;
it does not change Catalog files, recording files, Teacher sources or prepared
Dataset exports. Explicit removal updates only that store. Duplicate and failed
operations preserve prior matching evidence. Reopening a collection starts a
fresh source context. Same-context Reload retains sources, reclassifies them
against Current, and invalidates old view lineage. A non-current source remains
visible with restoration/removal controls, rather than being rebound or discarded.

Source capture uses the Match lifecycle/Capture locks and releases them before
entering the collection lifecycle/Corpus locks. Incorporation rechecks the target
handle, keyed context identity, Catalog revision/content, context generation and
source/prepared lineage before publication. Unlocked reconciliation cannot
publish into a replaced target. HTML/language and download publication recheck
captured collection lineage. Match and Corpus locks are not held together.

**Return to this recorded decision** separately checks the original managed
handle and exact content fingerprint, then uses the existing selection/preparation
path. The recording-page capture rechecks that binding; there is no unbound
redirect window that can substitute another revision. If the source changed or
is no longer open, the comparison remains readable and return gives a remedy.

Viewing, filtering, translation, comparison rendering and downloading execute no
evaluator and perform no recording save. Explicit incorporation is an authorized
process-local source mutation. Language selection retains the existing explicit
profile-save behavior; neither action is described as universally write-free.

## Private route and resource inventory

| Method / route | Effect |
| --- | --- |
| `GET /learning/debrief/from/<report_id>` | Capture one available exact Report; redirect to its opaque scope |
| `GET /learning/debrief/<scope_id>/<player_selector>` | Shared scope projection; `all` or captured Player ordinal |
| `GET /learning/debrief/<scope_id>/<player_selector>/<report_id>` | Exact retained comparison |
| Same comparison prefix + `/recording` | Verified return through existing Match selection and page capture |
| Same comparison prefix + `/request.json` or `/result.json` | Existing canonical Request/Result serializers and filenames |
| `POST /learning/debrief/include` | Explicit exact-source incorporation |
| `POST /learning/debrief/remove` | Explicit binding removal |

Both new POST forms are native URL-encoded forms with an 8,192-byte reader and
registry bound. Inclusion fields are `managed_handle`, `source_handle`,
`report_id`, `selection`; removal fields are `managed_handle`, `scope_id`,
`binding_id`, plus the existing optional form-instance transport. Every field is
singular; unknown fields are rejected. Hidden source proofs are not restored as
editable language state. Existing Host, Origin, cookie and CSP rules apply.

Initial implementation totals: **72 POST routes, 124 forms, 2,012 paired catalog keys**.
The current correction keeps the POST/form totals, adds one scope-checked inputs
GET shape, and has **2,025 paired keys**. Its inventories are detailed in the
[correction contract](learning_overview_navigation.md).
There are **72 authoritative and packaged Schemas**, **102 generated scenarios**,
and the same **ten prepared Corpus downloads**. The two scoped download suffixes
reuse exact Match serializers and do not extend that prepared-download set.

## Initial implementation synthetic browser evidence

`scripts/verify_learning_debrief.py` uses only disposable synthetic fixtures and
the existing dependency-free DevTools harness. The final observation is under
`$env:TEMP/opencode/issue289-browser-04/`, with `report.json`, inspected screenshots,
resource hashes and exact Request/Result hashes. It used CPython **3.13.7** and
Headless Edge **155.0.4283.45**, at **1365×900** and **390×844**.

The sequence covered direct no-collection entry, a collection with 30 recorded
decisions and zero included comparisons, explicit reuse, a concrete debrief,
detailed comparison, exact recording return, and German/English return. Native
operation ran with page JavaScript disabled; the final narrow-language return
used the existing enhancement and retained focus on the English language button.
Measured horizontal overflow was absent (`scrollWidth - innerWidth = -15`, the
scrollbar allowance). Typical action heights were **44.390625 px**; the wrapped
German recording-return control was **69.1875 px** high. Screenshots confirmed
readable wrapping and the existing responsive candidate presentation. A narrow
viewport is not a true browser-zoom measurement.

Counters were **one evaluation**, **zero recording writes**, **one explicit
Workspace import**, **one explicit Report incorporation**, **zero dataset
preparations**, and **eight debrief projections**. The one evaluation created the
retained fixture before reuse. Synthetic file creation and collection setup are
identified separately from navigation. Recording bytes and retained Request/
Result download bytes were unchanged.

For this deterministic two-world observation, C7, C9 and CK were tied on every
objective metric: 2/2 simulated settlement successes, mean local margin `70.00`,
mean local settlement score `50.00`. The UI preserves all three ties and shows
recorded bid `18` versus explicit analysis assumption matadors `1`. This teaches
how to interpret this retained comparison; it establishes neither a preferred
real-deal Card nor a calibrated advantage. No test requires CK to win a new run.

## Local validation and remaining acceptance

The broad affected regression invocation produced **980 passes, one platform
skip and 15 obsolete Learning presentation assertions**. The assertions were
updated for preparation wording and collapsed technical output; a real hidden-
receipt problem was corrected by keeping the receipt/target outside the disclosure.
After corrections, the final affected frontend/source/language/packaging/rename
group passed **480 tests in 268.69s**. That group includes the new evidence and HTTP
modules, duplicate and elapsed-only variants, both objectives, ties, forced moves,
incomplete execution, player counts, real distinct-game motif joins, retained
qualified focuses, source/target changes, expiry, native language return and
exact-byte retention. Earlier passing checks cover the unchanged actual Corpus
preparation, Teacher, Dataset, Match and Session modules; counts overlap.

Exact final affected invocation:

```powershell
py -3.13 -m pytest tests/test_match_debrief.py tests/test_learning_debrief_web.py tests/test_learning_direct_entry_web.py tests/test_learning_report_attachment.py tests/test_learning_result_explanations.py tests/test_learning_outcome_navigation.py tests/test_learning_version_presentation.py tests/test_learning_entry_purpose.py tests/test_task_first_match_and_learning_workflow.py tests/test_operation_feedback_web.py tests/test_operation_feedback_language.py tests/test_match_rollout_web.py tests/test_match_decision_selection_web.py tests/test_frontend_localization_foundation.py tests/test_frontend_validation_preservation.py tests/test_complete_frontend_localization.py tests/test_frontend_language_switching.py tests/test_language_switch_context.py tests/test_task_first_language_preservation.py tests/test_language_view_continuity.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py tests/test_direct_match_evidence.py tests/test_skatmind_rename.py -q
```

After the documentation edits, Ruff and the strict rename/packaging modules passed
again (**22 tests in 6.00s**). The actual unified managed-item transfer/HTTP,
task-first render/projection and input/output schema modules also passed
(**562 tests, one platform skip, in 38.54s**):

```powershell
py -3.13 -m ruff check .
py -3.13 -m pytest tests/test_skatmind_rename.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py -q
py -3.13 -m pytest tests/test_unified_local_app_web.py tests/test_unified_local_app_managed_items.py tests/test_task_first_stateful_rendering.py tests/test_task_first_stateful_projections.py tests/test_input_schema.py tests/test_output_schema.py -q
```

`py -3.13 scripts/validate_generated_outputs_schema.py` validated all **102** outputs.
The executable installed-smoke registry assertions ran through the packaging test.
The separate complete distribution validator first exceeded its 600,000-ms tool
timeout; no surviving validator/child process remained before retry. A longer run
completed both smokes but reported Wheel/sdist result inequality. A diagnostic
rerun executed the unchanged validator and retained both complete smoke summaries
under `$env:TEMP/opencode/issue289-distribution-diagnostic/`; both passed and
`differences.json` is `[]`. The earlier inequality was not reproduced and its cause
was not established. No assertion was weakened to obtain the pass.

Final review then tightened active-target revalidation after waiting for the
Corpus lock, removed an unavailable collection link from direct-expiry remedies,
and made the shared empty sentence independent of the page's offer placement.
The final evidence/HTTP/language/packaging/strict-rename retest passed **185 tests
in 102.73s**, and the browser sequence above passed again with the same counters:

```powershell
py -3.13 -m pytest tests/test_match_debrief.py tests/test_learning_debrief_web.py tests/test_frontend_localization_foundation.py tests/test_frontend_language_switching.py tests/test_language_switch_context.py tests/test_task_first_language_preservation.py tests/test_language_view_continuity.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py tests/test_skatmind_rename.py -q
```

The complete distribution rerun preceded these final private guard/empty-state
refinements; its passing result is not a claim of installed maintainer acceptance.
The executable installed-smoke registry assertions were retested on the final
tree in the 185-test invocation.

Final local validation uses explicit `scripts/check.ps1 -Mode Quick` with the
verified supported interpreter. No local Full or installed UAT acceptance is
claimed. Exact-commit hosted `check` and `v1-supported-platform-matrix`, identical-
commit integration, and the maintainer's installed Learning/Alex-C7 debrief retest
remain required. The maintainer's installation, recordings, profile and retained
downloads were not accessed.
