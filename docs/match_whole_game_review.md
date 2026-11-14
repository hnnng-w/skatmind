# Selected Match decision whole-game review

Separate S3 follow-up: [Issue #311 retention](match_rollout_analysis_retention.md)
retains managed executions and their exact original source across restart, with
family-owned Saved analyses downloads and separate incomplete attempts. The
historical execution/acceptance records below remain intact; the live eight-Report
store and existing manual debrief behavior retain their own lifetime.

Issue #288 adds one explicit whole-game action for a safely prepared Match
decision. The implementation starts from `1cf0ac06ee96731593406771261b3dc4ad1339e8`
on `feature/288-match-whole-game-review`. It reuses the existing rollout evaluator,
fixed policy, terminal scoring, exact tie semantics, settlement supplementation,
and shared localized result presentation.

The maintainer subsequently confirmed the installed Alex/C7 evaluation and matching
exports at `9cae27c1bd6fb06a4d56b92b68884744f769dcad`. The remaining selection-workflow
correction below starts from that commit. It changes selection/preparation and
ownership checks, not the evaluator, scoring or reconstructed Request semantics.

## Execution map

1. `/matches/review/N` offers an authenticated decision-preparation form at
   `POST /matches/select-decision`. The enhanced path applies committed selection
   changes in place. The native path explicitly applies a choice before exposing
   its analysis actions. The existing bounded GET selection remains supported.
2. `POST /matches/review-whole-game` resolves the managed handle, expected revision,
   selected Game, submitted visible decision and opaque authenticated decision
   selection. The independent legacy action checks the same ownership. Freshness is checked
   against the strictly loaded managed Workspace file.
3. `execute_unified_match_rollout` captures the immutable Workspace, settings,
   supplements, report-store generation and attempt ownership under the Capture
   lock. It uses `build_match_decision_position_request_v1` to obtain the original
   safely prepared decision, not a Session checkpoint or Historical materialization.
4. The selected-decision adapter derives one Position Request and executes the
   normal Application boundary once, outside the app/Capture/lifecycle locks.
5. `MatchDecisionAnalysisResultV1` reconciles the captured source, Request, settings,
   declaration, legal candidates, core-source fingerprint, typed aggregate arithmetic,
   exact ranking and descriptive actual-card comparison. Publication rechecks the
   managed file, source, attachment, selection, generation and attempt token.
6. The existing eight-report process-local store retains published reports.
   `build_rollout_presentation` and `render_result_presentation_v1` render that exact
   captured Result. Authenticated downloads refer to its report ID.

## Information policy

The unchanged preparation policy is
`reconstruct_decision_time_own_hand_without_future_opponent_information`.
The selected actor becomes `me`; historical seats and circular left/right mapping
are relative to that actor, including decisions by players other than the capture
perspective. Both defenders are one local party when the actor is a defender.

Partial recordings are supported where the existing evidence reconstructs that
actor's playable hand. A complete accepted trace may reconstruct only the acting
player's own playable hand for that decision. Declared-Ouvert public-hand evidence
retains the existing authorization rule. Only accepted plays strictly before the
selected card supply completed tricks, their validated winners, the current partial
trick, public hand sizes and banked points. Existing attributed completed tricks
already carry the required prefix; no additional history representation is needed.

Original Skat/discards are never inferred from a deck complement for this adapter.
Existing declarer-only known discards and authorized public hands keep their cutoff.
Later opponent hands, trick order, final scores, annotations, final discards and
recorded future actions do not reach the evaluator. Prepared bid/matador values are
reused; absent matadors are not inferred from later reconstructed opponent ownership.
The observed actual card enters the existing retrospective comparison only after
candidate evaluation; changing that annotation does not change sampling or ranking.

## Match derivation and compatibility

The additive `whole_game_rollout_derivation` alternative uses version `1` with the
distinct policy `reconstructed_match_decision`. Session derivation versions `1`
and `2` retain their existing policies and transport shapes.

The Match alternative retains:

* Match ID, Workspace revision and canonical content fingerprint;
* Game ID, Match position and `match_decision_index` (distinct from a core-local
  provenance decision index);
* the actor-relative stable player map and exact reconstruction policy;
* the immutable original before-card Position Request wrapper and its fingerprint;
* effective rollout settings and normalized effective declaration;
* explicit `supplements` and `supplement_origin: manual_analysis_input` when used;
* a domain-separated fingerprint of the complete derivation metadata.

Ordinary public parsing/execution validates the discriminator, shape, prefix index,
fingerprints, original Request, and exact permitted transformation. Only method
configuration, retrospective actual-card annotation, and originally absent explicit
settlement inputs may differ. Known-value overwrites, unrelated factual changes,
contradictory effective inputs and unsupported fields are rejected. Imported hashes
establish identity and internal consistency, not independent historical authentication.

`MatchDecisionAnalysisOptionsV1` explicitly accepts rollout settings and immutable
settlement supplements for this adapter. Legacy options retain their exact serialized
shape, omitted defaults, report IDs and export filenames. `FLAT_RECOMMENDATION_METHODS`
is unchanged. Historical batches, Teacher, Dataset, Coaching and Learning methods are
not extended. Rollout Report-source export, codec resume and direct Teacher ingestion
reject this unsupported transfer explicitly. The ordinary Result download is not a
Teacher source.

## Controls, results and retention

Fresh unified forms explicitly use `whole_game_rollout`, `complete_settlement`,
100 common worlds, seed `0`, `side_aware_baseline` version `1`, 300,000 transition
and 100,000 preparation limits, and a 30,000-ms deadline. Core/API omitted-setting
semantics do not change. Exact retained settings and safe submitted/restored choices
override fresh presentation defaults.

Only missing bid/matador fields are offered, initially empty and visible. Shared
Session field rendering and validation preserve integer/domain rules, known-value
protection, analysis-only origin, field-specific feedback, and explicit objective
switching. Switching to `played_game_goal` disregards supplement text without
changing original facts. Legacy-only Search, Immediate and profile controls live in
a separate secondary form. Profile presets do not condition the fixed rollout policy.

The selected-game page starts with compact Match/Game/contract context and decision
controls. The primary action has its own row; world-count/seed controls start closed
below it. Full recorded summaries are separately labelled and collapsed below the
controls; recorded chronology remains accessible below. Result pages use the shared
all-tied-best summary, actual-card membership, decisive metric, combined-defender
orientation, localized precision and Calculation details. They never substitute the
recording's final score for the decision root.

Invalid/failed attempts retain earlier reports and their exact bytes. A later
incomplete execution retains a completed report for the same decision and records
one bounded revision/generation-scoped attempt notice, with its own objective,
coverage and reason. An incomplete first execution remains inspectable. Incomplete
execution has no normal recommendation/ranking and never falls back to Immediate
or another objective. Successful reports retain the existing bounded-store lifetime;
source mutation, Reload and stale files invalidate them. Superseded work cannot
publish, including when the newer validly bound attempt fails field validation.

The existing `/matches/api/v1/reports/{report_id}.json` Result export remains an
exact Root Result. The additive
`/matches/api/v1/reports/{report_id}/rollout-request.json` exports executable Root
Request JSON. Neither download borrows current form settings or another Game's
same-numbered decision. Rendering, selection, language return, disclosure changes
and downloads execute no analysis and save no recording.

## Synthetic evidence and inventories

The disposable acceptance fixture has 36 slots, position 1 passed and the specified
Hearts trace in position 2. Bea is forehand/declarer, Chris middlehand and Alex
rearhand/capture perspective. Immediately before Alex's C7, the prepared root has
CQ/CA, no completed tricks, 0/0 banked points, ten Alex cards, opponent sizes 9/9,
legal CK/C9/C7 and unknown Skat. Bid 18 is known; matadors are absent. Neither final
43/67 trick points nor unplayed C10/H9 enters this root.

Paired short-prefix, complete-trace, own-hand-reconstruction and legal alternative
opponent-suffix fixtures produce identical core inputs and deterministic seeded
metrics for both objectives. Changing only the retrospective legal card likewise
leaves those metrics unchanged. Other tests cover declarer/defender roots, later
partial tricks, missing inputs, explicit synthetic supplements, unsupported Null,
preparation absence, incomplete/controlled-timeout execution, public round trips,
recomputed-hash known-value tampering, provenance, report tampering, native forms,
both locales, exact ties, stale files/selections, supersession and retained downloads.

Actual current definitions after the selection correction contain **70 POST routes**,
**122 form definitions**, **1956 keys per language**, **72 authoritative/packaged
schemas**, and **102 generated output scenarios**. The initial integration added one
POST route/form, one authenticated GET Request download, one Match derivation
alternative and seven keys per language. The selection correction adds one private
preparation POST/form and seven further keys per language. Schema filenames and
generated scenarios are unchanged. The legacy analysis form additionally registers
its hidden decision proof for source-safe validation feedback; its method settings
and independent native validation remain separate from rollout.
The installed-smoke registry assertions are updated and executed by
`test_installed_smoke_frontend_registry_contract_executes`; this is executable source
validation of those assertions, not a claim of installed UAT acceptance.

### Browser observation

The optional `scripts/verify_match_whole_game_review.py` uses the existing local
DevTools harness, a fresh disposable browser profile and synthetic Workspace.
Headless Edge **155.0.4283.45**, CPython **3.13.7**, and disabled page JavaScript
verified native decision selection, visible empty supplements, closed technical
controls and English/German language return. The completed default-sized run used
matadors **1 explicitly as an analysis assumption** and completed all 100 common
worlds for all three candidates. Its observed metrics were:

| Card | Simulated settlement successes | Mean local final margin | Mean local settlement score |
| --- | ---: | ---: | ---: |
| CK | 95/100 | 50.50 | 46.30 |
| C9 | 93/100 | 47.00 | 44.10 |
| C7 | 91/100 | 44.68 | 42.10 |

No regression asserts that ordering as a required winning card. This observation
records 9,237,800 compatible assignments, 3,016 preparation units, 8,400 transitions,
300 terminal evaluations, **394.29 ms** core time and **2.284 s** native submission
through publication. It is fixed-policy synthetic evidence, not optimal-play,
calibrated probability, quality or latency acceptance.

English/German 1365×900 and German 390×844 views had no measured horizontal overflow.
Screenshots were inspected. Both native downloads matched the exact retained
Request/Result bytes. Counters recorded **one evaluation and zero recording saves**;
passive actions added no executions. Served CSS and script bytes matched checkout
resources. Evidence is under `$env:TEMP/opencode/issue288-browser-02/`, including
`report.json`, screenshots, native downloads, module/catalog/asset hashes and the
browser identity. CSS SHA-256 is
`146e59f66cfad3cc61c527637361971180936679cddfaabc5304d075052c6dd1`.
An earlier harness run completed the action but failed its script-resource URL
assertion; the corrected run above supplies the complete evidence.

This is source-checkout evidence, not the maintainer's installation, private Match,
physical-device/true-zoom observation or UAT acceptance. #288 and wider #208 remain
open pending exact-commit full CI, identical-commit integration and the maintainer's
existing Alex/C7 Match retest. Previously deferred creation spacing, capture-grid
and progress/completion findings remain under #208 without new issues.

### Local validation commands

The following focused invocations passed. Counts are invocation counts, not a sum
of distinct tests; the later groups intentionally retest affected paths after final
adjustments. No local Full or installed UAT acceptance is claimed.

**665 passed in 400.39 s:**

```powershell
py -3.13 -m pytest tests/test_match_rollout_review.py tests/test_match_rollout_web.py tests/test_match_decision_review_preparation.py tests/test_match_decision_analysis.py tests/test_match_analysis_contracts.py tests/test_match_analysis_exports.py tests/test_match_analysis_report_source_export.py tests/test_match_information_set_search.py tests/test_match_historical_analysis.py tests/test_local_match_capture_web_analysis.py tests/test_match_analysis_action_placement.py tests/test_recorded_review_navigation.py tests/test_match_game_navigation_web.py tests/test_match_evidence_navigation.py tests/test_direct_match_evidence.py tests/test_task_first_match_and_learning_workflow.py tests/test_session_rollout_review.py tests/test_session_recorded_review_web.py tests/test_whole_game_rollout.py tests/test_whole_game_rollout_workflow.py tests/test_rollout_result_presentation.py tests/test_frontend_localization_foundation.py tests/test_frontend_validation_preservation.py tests/test_complete_frontend_localization.py tests/test_recorded_review_compact_forms.py tests/test_recorded_review_objective_default.py tests/test_recorded_game_summaries_web.py tests/test_recorded_decision_context_web.py -q
```

**917 passed in 132.22 s**, including the executable installed-smoke registry slice:

```powershell
py -3.13 -m pytest tests/test_input_schema.py tests/test_output_schema.py tests/test_public_field_provenance.py tests/test_public_field_provenance_schema.py tests/test_v1_provenance_enforcement.py tests/test_v1_provenance_serialization.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py tests/test_frontend_language_switching.py tests/test_language_switch_context.py tests/test_task_first_language_preservation.py tests/test_language_view_continuity.py tests/test_learning_corpus_strategy_teacher.py tests/test_learning_corpus_strategy_teacher_search.py tests/test_learning_corpus_strategy_teacher_export.py tests/test_learning_corpus_information_set_strategy_teacher.py tests/test_learning_corpus_tactical_coaching.py tests/test_match_historical_materialization.py tests/test_match_workspace_contracts.py tests/test_observed_game_contracts.py tests/test_match_capture_contracts.py -q
```

**276 passed in 206.72 s**, including the final secondary-action adjustment:

```powershell
py -3.13 -m pytest tests/test_public_python_api_v1.py tests/test_public_api_contracts.py tests/test_learning_dataset_v2.py tests/test_learning_dataset_v2_export.py tests/test_learning_dataset_v2_cross_game_summary.py tests/test_match_rollout_review.py tests/test_match_rollout_web.py tests/test_match_analysis_action_placement.py tests/test_recorded_review_compact_forms.py tests/test_recorded_review_objective_default.py tests/test_language_switch_context.py -q
```

**47 passed in 24.92 s**, after adding both-objective actor/prefix and authorized
Ouvert coverage:

```powershell
py -3.13 -m pytest tests/test_match_rollout_review.py tests/test_match_rollout_web.py -q
```

**198 passed in 78.74 s** after final source-transfer guard, unavailable-download,
empty-selection and retained-report navigation checks:

```powershell
py -3.13 -m pytest tests/test_match_rollout_review.py tests/test_match_rollout_web.py tests/test_match_analysis_report_source_export.py tests/test_learning_corpus_strategy_teacher.py tests/test_learning_corpus_strategy_teacher_search.py tests/test_learning_corpus_strategy_teacher_export.py tests/test_learning_corpus_information_set_strategy_teacher.py tests/test_match_analysis_action_placement.py tests/test_language_switch_context.py -q
```

**102 generated outputs validated:**

```powershell
py -3.13 scripts/validate_generated_outputs_schema.py
```

That initial handoff used `.\scripts\check.ps1 -Mode Quick` with process-local
CPython 3.13 selection. Full exact-commit CI and the installed Match whole-game
retest were then pending; the subsequently confirmed installed evaluation and the
remaining selection correction are recorded below.

## Applied selection correction

### Reproduced boundary

At the installed baseline above, the visible dropdown belonged to a separate GET
form. Changing it to Alex/decision 3 without submitting that form left the rollout
form's hidden decision and proof bound to Bea/decision 1. A disposable, JavaScript-
enabled Edge reproduction observed visible `3`, submitted/bound `1`, then a coherent
Bea/CQ Request and Result. It recorded one small explicit evaluation and zero saves.
The engine did not mix an Alex Request with a Bea Result. Earlier disabled-script
browser evidence did not exercise automatic selection.

### Enhanced preparation and ownership

`initializeMatchDecisionSelection` in the existing packaged workflow script is
scoped to the selected-Match control region. An input change immediately makes both
analysis actions unready. A committed change requests preparation through the new
authenticated form using the existing accepted-evidence builder. It performs no
evaluation and no Match save.

Preparation requests are serialized; rapid changes coalesce to the latest intended
choice. A delayed response can advance the transport binding for that next choice
but cannot install older controls. No analysis click is queued. Failed, foreign,
malformed or contradictory responses leave analysis blocked and expose explicit
native recovery. There is no automatic retry.

Only the analysis controls and their language-return binding are refreshed. The
selector node remains in place, retaining keyboard focus and its current viewport
offset. Pending settings are copied through the existing safe-field/length rules
into bounded page-local, source-and-decision-specific drafts. Returning to Bea on the
same page restores Bea's draft; it does not copy those supplements into Alex. Current
visible values continue through the existing language-return mechanism. Drafts for
inactive decisions are not durable and do not survive a new page navigation.

Both actions submit `visible_decision_index`, their bound `decision_index` and an
opaque decision proof. The server requires exact agreement with the current ready
context, expected Workspace revision, managed-source identity and fresh file. A
separate decision generation invalidates earlier proofs and in-flight analysis
without invalidating unrelated same-Game capture forms. The legacy Capture service
has an optional source guard, checked under its lock before execution and before
publication; standalone callers retain its omitted default. Rollout retains its
existing attempt/source publication checks.

Selection failures preserve the originating review, recording or exact Report page.
In-place error controls therefore use the same complete form/disclosure manifest as
the retained page for language return. The failed selection remains unready. Prior
completed Results and their canonical downloads keep their own source identity.

### Native fallback

Without JavaScript, or when enhancement cannot initialize, the user first chooses
and explicitly applies a decision. Only then are the independent rollout and legacy
forms exposed beside a noneditable prepared-decision caption. A visible **Choose a
different decision** link returns to the selection step. Editable unapplied selection
and executable old analysis are never shown together. No additional confirmation
wizard or global preference is introduced. The manual apply button is hidden only
after the scoped enhancement initializes successfully.

Missing, unknown, foreign, stale or inconsistent selections do not silently fall
back to the first or previous decision. Source changes and failed preparation cannot
make an older context appear to be the successfully prepared new choice.
If a recording edit removes the selected decision but other decisions remain
preparable, the selector offers an unselected preparation-only state. The user must
choose again; the first remaining decision is not silently installed for analysis.

### Bounded browser evidence

`scripts/verify_match_decision_selection.py` reuses the disposable #288 Workspace
fixture. The completed source-checkout observation used Headless Edge
**155.0.4283.45**, CPython **3.13.7**, and **1365×900** with JavaScript enabled, followed
by a bounded disabled-script native check. It did not re-enter ten tricks or rerun
the 100-world benchmark.

The sequence checked delayed Bea → Alex → Bea selection, blocking a click during
loading, restoration of Bea's unsent matador value `2`, empty Alex supplement fields,
and one explicit **one-world** Alex/decision-3 evaluation with analysis assumption
`matadors: 1`. The selector kept keyboard focus and the same **428.6875 px** top
offset across successful in-place preparation. Both legacy and rollout bindings
identified decision `3`; the executed Request/Result identified Alex and actual C7.

A deliberately failed later preparation left analysis unavailable. English/German
return retained the prior report and unready selection, followed by explicit
recovery. The native check showed no analysis action while an unapplied choice was
editable, then exposed only the explicitly applied context. Across the completed
sequence there were **six explicit selection-preparation attempts, one evaluation and zero recording
saves**. The recording bytes and prior Request/Result download bytes were unchanged.
Screenshots were inspected; served CSS/script bytes matched checkout resources.

Evidence is outside the repository under
`$env:TEMP/opencode/issue288-selection-after-05/`, with source-browser identity,
request statuses, observations, screenshots and download/resource hashes in
`report.json`. The before-correction reproduction is under
`$env:TEMP/opencode/issue288-selection-before-f98yw7bi/`. Earlier development probes
preceded the explicit navigation wait and the Report-page failure-manifest repair;
they are not final acceptance evidence.

Final served script SHA-256:
`5237d60fb26a69c7ae9e2c0f32a4a9a6020ff520787e8409858ec4baa909011a`.
CSS SHA-256:
`5d42513895f0c8e62697774867a3b9134a8f00b4d8acdc5c5c9fa4ce8e6b5c31`.

The script tests cover delayed/stale replies, failure, foreign source, exact draft
isolation, independent action blocking and initialization fallback. Real HTTP tests
cover the shared visible/bound checks, missing proofs, strict preparation, stale
files/revisions, source changes during preparation, both in-flight publication
paths, language return and retained downloads. The strict rename inventory module
is included in local verification; no inventoried occurrence was moved by this
selection correction.

This is synthetic source-checkout evidence. #288 remains open for exact-commit CI
and the maintainer's short installed decision-selection retest.

### Selection correction validation

The complete affected HTTP/script/language, source-binding, retention, Session,
packaging and strict rename modules passed **589 tests in 379.32 s**:

```powershell
py -3.13 -m pytest tests/test_match_decision_selection_web.py tests/test_match_decision_selection_script.py tests/test_match_rollout_web.py tests/test_match_rollout_review.py tests/test_match_analysis_action_placement.py tests/test_local_match_capture_web_analysis.py tests/test_task_first_match_and_learning_workflow.py tests/test_recorded_review_navigation.py tests/test_language_view_script.py tests/test_language_view_continuity.py tests/test_language_switch_context.py tests/test_task_first_language_preservation.py tests/test_frontend_language_switching.py tests/test_frontend_validation_preservation.py tests/test_complete_frontend_localization.py tests/test_frontend_localization_foundation.py tests/test_operation_feedback_script.py tests/test_operation_feedback_web.py tests/test_operation_feedback_language.py tests/test_packaging_and_distribution.py tests/test_guided_frontend_packaging.py tests/test_skatmind_rename.py tests/test_direct_match_evidence.py tests/test_session_rollout_review.py tests/test_recorded_review_compact_forms.py tests/test_recorded_review_objective_default.py tests/test_unified_local_app_web.py -q
```

After the final removed-decision recovery, uncommitted-preview and retired-selector-
feedback checks, the directly affected selection, language and ownership modules
passed **149 tests in 95.38 s**:

```powershell
py -3.13 -m pytest tests/test_match_decision_selection_web.py tests/test_match_decision_selection_script.py tests/test_match_rollout_web.py tests/test_match_analysis_action_placement.py tests/test_language_view_script.py tests/test_language_view_continuity.py tests/test_task_first_language_preservation.py tests/test_skatmind_rename.py -q
```

These groups overlap. The installed-smoke registry assertions were executed through
the packaging test module. Final local validation is explicit Quick; complete
exact-commit hosted CI and the short installed selection retest remain pending.

## Retained post-game debrief reuse (Issue #289)

The new [Match debrief](learning_match_debrief.md) supersedes the former blanket
Learning-transfer limitation only for a narrow private player-facing evidence
family. Completed Reports expose a direct captured review, and opened collections
offer explicit compatible Report incorporation without JSON handling. Detailed
comparisons and canonical downloads reuse the retained Request/Result; they do
not evaluate again. The original source handle/content is checked separately on
recording return. Teacher source exports/codecs, `FLAT_RECOMMENDATION_METHODS`,
Dataset and qualified Coaching eligibility remain unchanged and reject rollout.

## Issue #320: superseded-work cancellation and CLI parity

Branch `bug/320-rollout-cancellation` started at
`b80e6641c78885546c5e09b369ecade1714d2c37` with a clean index/worktree. Changes are
unstaged and uncommitted. Accepted #316–#318 evidence remains valid; this bounded
follow-up does not repeat S7 or establish overall UAT-01/v1 completion.

### A2 — Invocation-local runtime cancellation

The Product change is confined to three files:

1. `app_web/match_rollout_frontend.py` supplies an invocation-local
   `ApplicationWorkflowDependencies` through the existing Match `dependencies=` seam.
2. `application/position_workflow.py` carries optional runtime-only
   `PositionWorkflowDependencies.rollout_cancelled` into the recommendation workflow.
3. `recommendation_workflow.py` forwards the hook only to the whole-game evaluator's
   existing `cancelled=` parameter, which already reaches preparation and execution.

The predicate reuses captured attempt, Workspace identity, source binding,
position/selection generations and Report generation, plus retirement, active Match
replacement and saved-analysis owner identity. A bound new attempt supersedes old
work before field validation; ordinary analysis and explicit selection retain their
existing invalidation behavior. Unchanged passive navigation and language changes
do not invalidate ownership. Hooks and dependency instances are invocation-local;
the omitted-hook path, other methods, public signatures, serialized options,
Schemas, provenance and core rollout contracts remain unchanged.

Checkpoint locking is briefly **Capture → app**, matching publication/retention;
no lifecycle/store lock is acquired by the predicate and computation runs unlocked.
Checkpoint checks use only in-memory ownership and the existing small binding HMAC,
never recording reads/hashes. Final disk freshness, source reconciliation, guarded
publication and archive ownership remain authoritative. Consequently an external
disk-only edit is detected by the final freshness guard, not by polling during
computation. Cancellation is cooperative at existing checkpoints, not preemption.

Deterministic synthetic evidence uses the existing Alex/C7 fixture, Events, a fixed
clock and independent counters around actual sampled-world yields and Card
transitions. Threads/HTTP handlers finish before persistent-file assertions.

| Case | Sampled worlds | Card transitions | Terminal evaluations | Common coverage | Ranking |
| --- | ---: | ---: | ---: | ---: | --- |
| Before correction, obsolete work (both pause locations) | 2 | 168 | 6 | 2/2 | Completed internally; publication rejected |
| A2 cancellation before core preparation | 0 | 0 | 0 | 0/2 | None |
| A2 cancellation during actual evaluation | 2 | 85 | 3 | 1/2 | None |
| Current, independent, later, or unchanged-passive invocation | 2 | 168 | 6 | 2/2 | Completed |

Tests cover all ownership dimensions, bound-invalid supersession, real ordinary
analysis/explicit-selection invalidation, controlled HTTP 409 recovery, no stale
Report/attempt notice/pending save, original recording bytes and retained completed
archive/download bytes. Existing final staging/manifest/source guards and retry
tests remain in the complete selection. Runtime/default execution isolation and
non-rollout method checks also exercise the internal dependency seam.

Two existing wrappers in `tests/test_saved_match_rollouts_web.py` and the wrapper
in `scripts/verify_saved_match_rollouts.py` now compose/forward the runtime hook
while retaining their controlled cancellation; existing clock/tie wrappers in the
required modules also forward it. This concrete dependency adds the complete saved
Match rollout module to the eleven requested modules. No exclusive module is
affected. The development browser script is adapted but not executed here.

### A3 — All six existing CLI documents

`test_all_seven_provenance_outputs_match_public_installed_module_and_legacy` now
compares each complete document with the public API result, naming the invocation
on failure. All six existing executions (installed-style, module and Root facade,
each implicit and explicit `run`), exit-code, quiet-output and provenance assertions
are retained. There are no additional CLI executions or selected-field comparisons.
This repairs verification coverage; no CLI Product mismatch was demonstrated.

### Local commands and acceptance

Development CPython 3.13.7; each validation tool invocation has a **7,200,000 ms**
timeout. `$E` is an existing external temporary/log directory. JUnit captures actual
work-counter output and failed assertions; pytest caches are disabled.

```powershell
$E = Join-Path $env:TEMP 'opencode'
if (-not (Test-Path -LiteralPath $E)) { throw 'Missing external evidence parent' }
$env:PYTHONDONTWRITEBYTECODE = '1'
$Flags = @('-q', '-n', '2', '--dist=loadfile', '--max-worker-restart=0', '-p', 'no:cacheprovider')
py -3.13 -m pytest tests/test_match_rollout_web.py::test_superseded_unlocked_work_cannot_publish @Flags --basetemp "$E/320-red" --junitxml "$E/320-red.xml" -o junit_logging=all --log-file "$E/320-red.log"
py -3.13 -m pytest tests/test_match_rollout_web.py tests/test_match_rollout_retention.py tests/test_saved_match_rollouts_web.py tests/test_whole_game_rollout_workflow.py::test_runtime_dependency_cancels_without_mutating_invocation_or_default_execution tests/test_recommendation_workflow.py::test_omitted_and_explicit_immediate_invoke_only_immediate tests/test_recommendation_workflow.py::test_search_recommendation_skips_immediate_for_strict_and_auto @Flags --basetemp "$E/320-focused" --junitxml "$E/320-focused.xml" -o junit_logging=all --log-file "$E/320-focused.log"
py -3.13 -m ruff check --cache-dir "$E/320-ruff-cache" src/skatmind/app_web/match_rollout_frontend.py src/skatmind/application/position_workflow.py src/skatmind/recommendation_workflow.py tests/test_match_rollout_web.py tests/test_match_rollout_retention.py tests/test_saved_match_rollouts_web.py tests/test_whole_game_rollout_workflow.py tests/test_recommendation_workflow.py tests/test_installed_cli.py scripts/verify_saved_match_rollouts.py
$Affected = @(
  'tests/test_match_rollout_web.py', 'tests/test_match_rollout_retention.py',
  'tests/test_match_rollout_review.py', 'tests/test_match_decision_analysis.py',
  'tests/test_whole_game_rollout_workflow.py', 'tests/test_recommendation_workflow.py',
  'tests/test_application_orchestration.py', 'tests/test_application_provenance.py',
  'tests/test_session_rollout_review.py', 'tests/test_installed_cli.py',
  'tests/test_skatmind_rename.py', 'tests/test_saved_match_rollouts_web.py'
)
py -3.13 -m pytest @Affected @Flags --basetemp "$E/320-affected" --junitxml "$E/320-affected.xml" -o junit_logging=all --log-file "$E/320-affected.log"
# After affected-module workers have exited:
$env:RUFF_CACHE_DIR = "$E/320-ruff-cache"
function python { py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Pre-implementation reproduction: **two expected failures in 10.56s**, proving the
obsolete work completed internally despite HTTP 409. Focused verification:
**85 passed in 220.32s**. Targeted Ruff found two overlong lines, subsequently wrapped.
Final complete affected selection: **318 passed, zero failures/skips, in 633.54s**
across all twelve modules, with two file-grouped workers and no worker restart.
This includes all seven A3 workflow cases, each comparing six whole CLI documents
(42 comparisons against the corresponding public results). The earlier invocations
overlap this final selection and are not additional distinct coverage.

After workers exited, explicit Quick passed with exit **0** in **2.432s** on
development Windows 11 / CPython 3.13.7: Ruff **0.462s**, schema parity **0.059s**,
input examples **1.674s**, each exit 0. Logs are in
`$env:TEMP/skatmind-check-0nafzf1s`; failure/counter JUnit evidence remains in
`$E/320-red.xml`, `$E/320-focused.xml` and `$E/320-affected.xml` with their log files
and disposable temporary roots. No unresolved local failure remains. Only this
documentation receipt/command accounting was completed after Quick; Product and
tests remain as validated. Final `git diff --check` passes, staging stays empty,
and ending HEAD remains `b80e6641c78885546c5e09b369ecade1714d2c37`.

Status: **locally validated; exact-commit hosted CI and installed acceptance pending**.

Local verification uses development execution and disposable synthetic data.
Quick covers Ruff, packaged-schema byte/name parity and input examples; it does not
certify generated outputs, distributions, installation matrices or full regression.
No local Full, timing-only suite, hosted trigger, UAT build/install/start or access
to maintainer UAT data is part of this task.

Keep **#320 open** for exact-commit branch/main `check` and
`v1-supported-platform-matrix`, followed by A2's narrow installed maintainer check:
supersede one existing Match rollout from a second tab, confirm controlled recovery,
complete the current invocation, and reopen retained completed evidence. A3 needs
no additional installed scenario. #208/overall UAT-01 remain open, formal UAT-02–12
remain paused, and release preparation is not authorized.

## Issue #320 hosted layering correction

The preceding 318-pass local record remains point-in-time evidence. The maintainer
published that implementation as `3aa3ba1c053819af9b519e31fe34d99acefea2f4` on
`bug/320-rollout-cancellation`. This correction starts at that exact commit with a
clean worktree. The separate final-documentation follow-up also remains valid:
eight rename-module tests passed, followed by Quick and whitespace, before publication.

### Verified hosted evidence

Authenticated read-only inspection retrieved both regression artifacts and full
job logs from [run 43609661047, attempt 1](https://github.com/hnnng-w/skatmind/actions/runs/43609661047).
Run metadata, artifact workflow bindings, job metadata, checkout logs and both
validation summaries identify the exact published commit above. Both summaries
record source digest
`4d00333faed77daa1e5535dbeb393338cd380cb31c4fd2e6b78e3796dfeeb92f`, independently
recomputed from the clean starting checkout before correction.

| Evidence | Ubuntu | Windows |
| --- | --- | --- |
| Regression job | `132491766193` | `132491766203` |
| Artifact | `regression-ubuntu`, `14123895217` | `regression-windows`, `14123425308` |
| Python | 3.13.15 | 3.13.15 |
| Platform | Linux, Ubuntu hosted runner | Windows Server 2025 hosted runner |
| Complete collection | 12,461 | 12,461 |
| Parallel selected/executed node IDs | 12,366 | 12,366 |
| Passed / failed / skipped | 12,360 / 1 / 5 | 12,365 / 1 / 0 |
| Matching worker collections | 4 | 4 |
| Unexecuted exclusive tests | 95 | 95 |
| Collection / parallel exit | 0 / 1 | 0 / 1 |

The artifacts contain JSON collection/phase records and summaries, not JUnit XML.
All selected parallel node IDs have exactly their expected execution phases and
successful teardown, without duplicate or missing reports. Ubuntu has three setup
skips and two call skips, all in Windows-junction cases. There are no failed setup
or teardown reports on either platform. The only failed call is:

```text
tests/test_cli_internal_architecture.py::test_app_web_layering_and_startup_execution_boundaries
worker: gw0 (both platforms)
tests/test_cli_internal_architecture.py:689: AssertionError
assert violations == []

Actual violations:
(src/skatmind/app_web/match_rollout_frontend.py, 6, skatmind.application.execution)
(src/skatmind/app_web/match_rollout_frontend.py, 7, skatmind.application.position_workflow)
```

Both artifact logs retain this full traceback and both complete job logs agree;
there is no missing traceback to reconstruct. After the failed parallel phase the
runner stopped. The unexecuted exclusive modules contain 6 early-rejection tests,
27 Corpus-web tests, 25 Match-action-placement tests and 37 unified-rejection tests.
Neither exclusive execution nor final complete-suite accounting/performance
publication ran; their reports are absent. The reconciliation above is inspection
of the failed parallel evidence, not successful full-suite accounting.

The run has 20 successful jobs and three failures: both regressions and `check`.
The actual `check` gate rejected the failed regression prerequisite with
`gate_prerequisites_invalid`. Standards, generated outputs, both builds, all twelve
installation cells, both matrix-result jobs and the actual
`v1-supported-platform-matrix` gate succeeded. Those results do not accept the
correction or authorize integration of a failed regression commit.

### Demonstrated cause and bounded correction

This is a Product dependency-layering defect: the frontend directly constructed
internal Application/Position dependencies despite the existing architectural
boundary. The architecture module was missing from the original local selection.
It is not a synchronization, infrastructure, or timeout failure. Before editing,
the exact node reproduced the same two violations on development CPython 3.13.7:
one failure in 1.56s. No repeated scheduling runs were needed.

**A2 correction:** `match_decision_analysis.py`, the existing Match-to-Application
adapter, now owns `build_match_rollout_dependencies_v1`. It adapts a live cancellation
callback to fresh Application/Position dependency values without executing analysis.
The frontend imports this focused Match builder and passes its result through the
unchanged `dependencies=` seam. This is the concrete minimal extension beyond the
original three-file Product scope; Application types are no longer imported by the
frontend. The architecture assertion and its forbidden-import policy are unchanged.

The ownership predicate, Capture → app lock order, unlocked computation, actual
core checkpoints, final freshness/publication/archive authority and retained bytes
are unchanged. Existing Match and Application execution signatures, serialized
options, default/non-rollout paths, limits and invocation isolation are preserved.
One added Match integration test changes cancellation after dependency construction
and verifies zero obsolete work, a genuinely completed independent invocation and
identical Requests/options. The focused architecture plus integration pair passed
two tests in 3.17s. The existing Event/work-counter and retention tests exercise the
new builder through the real frontend path in final verification.

**A3:** all six complete CLI provenance comparisons and their original execution,
exit-code, quiet-output and provenance checks remain intact. This correction does
not alter or rerun the complete CLI module. Accepted #316–#318 evidence is preserved.

### Final verification selection and commands

The final selection is seven complete modules: the missed architecture invariant;
the Match adapter and rollout integration modules; real rollout HTTP cancellation,
retention and saved-download consumers; and the repository-name inventory against
this completed documentation. No exclusive module is affected by moving only this
runtime dependency construction. The earlier 318-pass selection is retained rather
than repeated in full. All validation tool invocations use **7,200,000 ms** timeouts,
development Python and external temporary/log/JUnit paths.

```powershell
$E = Join-Path $env:TEMP 'opencode'
if (-not (Test-Path -LiteralPath $E)) { throw 'Missing external evidence parent' }
$env:PYTHONDONTWRITEBYTECODE = '1'
gh run download 43609661047 --repo hnnng-w/skatmind --name regression-ubuntu --name regression-windows --dir "$E/320-hosted-43609661047"
gh run view 43609661047 --repo hnnng-w/skatmind --attempt 1 --job 132491766193 --log
gh run view 43609661047 --repo hnnng-w/skatmind --attempt 1 --job 132491766203 --log
$Flags = @('-q', '-n', '2', '--dist=loadfile', '--max-worker-restart=0', '-p', 'no:cacheprovider')
# Before correction:
py -3.13 -m pytest tests/test_cli_internal_architecture.py::test_app_web_layering_and_startup_execution_boundaries @Flags --basetemp "$E/320-layering-red" --junitxml "$E/320-layering-red.xml" -o junit_logging=all --log-file "$E/320-layering-red.log"
# Focused correction check:
py -3.13 -m pytest tests/test_cli_internal_architecture.py::test_app_web_layering_and_startup_execution_boundaries tests/test_match_rollout_review.py::test_match_dependency_uses_live_cancellation_without_affecting_another_invocation @Flags --basetemp "$E/320-layering-focused" --junitxml "$E/320-layering-focused.xml" -o junit_logging=all --log-file "$E/320-layering-focused.log"
# Complete affected modules, after finishing all documentation:
$Affected = @(
  'tests/test_cli_internal_architecture.py', 'tests/test_match_decision_analysis.py',
  'tests/test_match_rollout_review.py', 'tests/test_match_rollout_web.py',
  'tests/test_match_rollout_retention.py', 'tests/test_saved_match_rollouts_web.py',
  'tests/test_skatmind_rename.py'
)
py -3.13 -m pytest @Affected @Flags --basetemp "$E/320-layering-final" --junitxml "$E/320-layering-final.xml" -o junit_logging=all --log-file "$E/320-layering-final.log"
# After all workers exit:
$env:RUFF_CACHE_DIR = "$E/320-ruff-cache"
function python { py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
```

Downloaded raw phase reports, metadata, full job logs and a derived inspection
summary are retained under `$E/320-hosted-43609661047`. The external inspection
helper `320-inspect-hosted.py` checks commit/source identity, exact per-worker
collections, per-node phase uniqueness, outcomes and the unexecuted exclusive set.
Final local results are reported in the handoff, without a post-check documentation
edit. Quick remains partial validation; no local Full, extra timing run, browser
script, UAT build/install/start or access to maintainer UAT data is involved.

Keep #320 open for new exact-commit branch/main hosted gates and the existing narrow
installed A2 check (second-tab supersession, controlled recovery, current completion
and reopening retained evidence). No repeated S7, blanket UAT or release acceptance
is authorized. Cooperative checkpoints and final detection of disk-only source edits
remain the same bounded behavior.
