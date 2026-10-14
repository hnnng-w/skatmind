# Selected Match decision whole-game review

Issue #288 adds one explicit whole-game action for a safely prepared Match
decision. The implementation starts from `1cf0ac06ee96731593406771261b3dc4ad1339e8`
on `feature/288-match-whole-game-review`. It reuses the existing rollout evaluator,
fixed policy, terminal scoring, exact tie semantics, settlement supplementation,
and shared localized result presentation.

## Execution map

1. `/matches/review/N` offers a native decision selector. Its GET selection is
   normalized back to the query-free route without analysis or recording saves.
2. `POST /matches/review-whole-game` resolves the managed handle, expected revision,
   selected Game and opaque authenticated decision selection. Freshness is checked
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

Actual current definitions contain **69 POST routes**, **121 form definitions**,
**1949 keys per language**, **72 authoritative/packaged schemas**, and **102 generated
output scenarios**. The feature adds one POST route/form, one authenticated GET
Request download, one Match derivation alternative in the existing rollout schema,
and seven keys per language. Schema filenames and generated scenarios are unchanged.
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

The final local handoff uses `.\scripts\check.ps1 -Mode Quick` with process-local
CPython 3.13 selection. Full exact-commit CI and the installed Match whole-game
retest remain the maintainer's acceptance steps.
