# Unified local frontend guided analysis and Results

## Status

Issue #211 implements the guided Analyze and Review slice of the
[unified local frontend contract](unified_local_frontend_contract.md). It extends
the Issue #210 [application shell](unified_local_frontend_application_shell.md)
without adding a Root workflow, Public API export, Schema, persistence format,
dependency, or Product algorithm.

Issue #218 adds separate submitted-form preservation and localized validation
feedback without changing the guided Product builders or execution boundary. See
[Frontend validation state and localized feedback](frontend_validation_state_and_localized_feedback.md).

The implemented browser areas are:

```text
/analyze
    guided current or retrospective one-Decision analysis
    guided one-Decision Post-game Review
    strict Position JSON import

/review
    explicit manual guided normal-completion Historical entry
    strict Historical and retrospective Position JSON import

/review/recorded
    normal Review navigation: select an existing Session or Match
    explicit opening reaches its existing source-specific review actions

/sessions
/matches
/learning
    managed stateful workflows implemented by Issue #212
```

Package version remains `0.17.0`, Public API contract version remains `1`, the
Root workflow count remains seven, and the one Console Script remains
`skatmind = skatmind.cli:main`.

## Private contracts

The private versions are exactly:

```text
GUIDED_ANALYSIS_FRONTEND_VERSION = 1
GUIDED_POSITION_FORM_VERSION = 1
GUIDED_HISTORICAL_REVIEW_FORM_VERSION = 1
FRONTEND_RESULT_PRESENTATION_VERSION = 1
FRONTEND_JSON_TRANSFER_VERSION = 1
PROCESS_LOCAL_FRONTEND_WORKFLOW_STATE_VERSION = 1
FRONTEND_VALIDATION_PRESERVATION_VERSION = 1
```

The private policy tuple is exactly:

```text
guided_forms_build_existing_root_documents
one_explicit_application_execution_per_run
normal_forms_reuse_existing_product_defaults
advanced_settings_are_collapsed_and_explained
strict_json_import_is_explicit_and_non_executing
exact_json_download_uses_retained_values
public_result_is_the_only_presentation_source
normal_result_states_are_not_transport_errors
process_local_state_without_implicit_persistence
private_engine_state_never_enters_browser_state
```

These identities are independent from Package, Public API, Root workflow,
Schema, Session, Match, Corpus, Search, and persistence versions.

## Process-local state

Issue #229's [recorded-review navigation](home_and_recorded_review_navigation.md)
preserves the independent manual draft, step, import and Result when visiting Home,
the chooser or a recording. Its secondary manual link returns to `/review` without
reset. The chooser does not import or convert recordings into the wizard. Shared
concept/related panels are replaced by short introductions; the actual guided
steps, information choices, actions, Result types and downloads remain supported.

Analyze and Review have independent immutable revisioned state under the existing
application-context lock. Each area retains at most one draft or imported
`RequestDocumentV1`, one latest successful Request/options/Result tuple, exact
precomputed download bytes, legacy safe validation messages, and one in-progress source
revision.

Every accepted input mutation advances its route-specific revision once and
invalidates older output. A rejected submitted candidate remains separate and
does not advance accepted state or clear older successful output. Execution
failure publishes no replacement Result. Reset requires explicit confirmation.
Stale forms and duplicate Run attempts return HTTP `409`; stale completed work
cannot overwrite newer state. Product execution occurs outside the context lock,
and publication rechecks the exact source revision without retry.

State contains no timestamp, caller path, persistent Product identifier, Session,
Match Workspace, Corpus object, or managed-storage reference. Closing the process
discards drafts, imports, and Results unless the user explicitly downloaded JSON.

## Position form

`/analyze` begins with the normal choice between a current decision and one
actually played retrospective Card. The normal sections are:

```text
Your role and the contract
Cards you can currently see
Completed tricks and current trick
Current score and turn
Run analysis
```

The form supports Suit, Grand, and all four Null declaration variants; Declarer
and Defender perspectives; all three local seats; declaration flags; bid value;
optional Matadors; the local hand; legitimately visible Skat and public Declarer
Cards; completed and current Tricks; points; opponent Cards remaining; and the
retrospective actual Card.

The canonical 32-Card control order and readable labels come from the existing
Deck and Card-name contracts. Existing Product helpers validate Card uniqueness,
declaration dependencies, Trick order and winners, Turn Phase, all three
remaining hand sizes, information visibility, and actual-Card legality. The
frontend does not infer hidden ownership or calculate Game value independently.

Normal Position translation preserves:

```text
sample_count = 1000
random_seed = 42
use_basic_opponent_strategy = true
recommendation_method = omitted
analysis_mode = live_decision unless retrospective was selected
game_end_reason = not_ended
validate_output = true
```

## Advanced Settings

Both workflows use the six initially collapsed groups:

```text
Analysis method
Runtime and reproducibility
Opponent behavior
Simulation and comparison
Technical evidence
Dataset and evaluation
```

Analyze maps understandable controls to the existing Immediate, bounded Search,
Auto, Information-set Search, Multi-Step, Policy Comparison, opponent Policy,
Profile-preset, sample, seed, and public Provenance options. Existing versioned
interactive Search settings are reused rather than duplicated.

Review exposes the existing Decision Snapshot, Immediate Review, bounded Search
Review, Information-set Search Review, Replay Coaching, Information-set Replay
Coaching, Tactical Motif Review, seed/sample, Historical Review budget-profile,
and public Provenance options. Selected dependent families show their existing
implied prerequisites before Run. The two pages contain no fake Dataset control;
the Dataset group states that those operations remain advanced automation.

Settings explain runtime, reproducibility, evidence scope, fixed-policy behavior,
and boundedness. They do not change Skat rules, promise calibrated probability,
describe Search as perfect play, or describe rule-based behavior as a learned
prediction.

## Historical editor

The normal `/review` editor has exactly seven server-rendered steps:

```text
1. Players and seats
2. Deal
3. Declarer and declaration
4. Skat pickup and Discards
5. Card play
6. Review options
7. Validate and run
```

It uses deterministic process-local IDs `frontend-forehand`,
`frontend-middlehand`, and `frontend-rearhand`, and Game ID
`frontend-historical-review`. Optional non-empty display labels must be unique.
The editor accepts one exact 10/10/10/2 Deal, validates pickup or Hand-game
Discards, derives each acting Player and legal Card set, and delegates actor,
winner, and next-leader replay to the existing observed-trace and rule helpers.
It appends one chronological Card at a time and can undo only the final play.
Back preserves valid entered facts; a completed Play step can return to Review
options without re-entry.

The bounded manual editor emits only `normal_completion` after exactly 30 legal
plays. It does not remove broader Historical support. Existing shortened endings,
continuations, party-wide Claims, concession/exposure/open-play variants, and
other supported Historical documents remain available through optional strict
JSON import and receive the same Result presentation.

## JSON import

Import is a secondary explicit action and never executes. Each page accepts one
strict multipart upload containing one finite UTF-8 JSON object without a BOM,
duplicate object keys, nested multipart, duplicate file fields, or unsupported
headers. The maximum file content is exactly `1,048,576` bytes; bounded multipart
framing is accounted for separately. Caller filenames are ignored and retained
nowhere. Parsing uses no temporary file.

Analyze accepts only `position_analysis`. Review accepts `historical_game` and
`position_analysis` with exact `analysis_mode=post_game_review`. Existing public
input parsing constructs one immutable Request, and a separate explicit Run is
required. Incompatible workflows produce a distinct safe HTTP `400` response.

Issue #252 names the metadata disclosure **Import details**. Before execution the
validated Request link remains in this imported-document context, with no Result
claim. Once the displayed Result owns that same retained Request, its download
area owns the action alone. This uses `latest_successful_request` / `imported_request`
ownership and retained bytes, never href equality, filenames or submitted form values.
A running page retains import-only access when applicable; a rejected new input
does not relabel an older Result. Accepted replacement still invalidates old output.

## Application execution

Every explicit Run constructs or reuses one immutable Request and one immutable
`ExecutionOptionsV1`, then calls the existing Public/Application execution
boundary exactly once with one of:

```text
memory://skatmind/app/analyze
memory://skatmind/app/review
```

No CLI subprocess, Root input file, external request, execution retry, Search
workflow rerun, Historical workflow rerun, or render/download execution exists.
The retained public `ExecutionResultV1` is the only Product source for
presentation. Presentation
does not inspect private Search Worlds, Application bundles, private Provenance,
or hidden ownership and does not recompute recommendations, settlement, winner,
score, or decision quality.

## Result presentation

Issue #221 reuses `execute_guided_frontend_review_v1` directly for an exported
Session Checkpoint Position Request in `post_game_review` mode, with default
output-validating options and no manual Review draft. The active Session page
uses this same Result presentation with a separate exact recorded-decision source
label and its existing authenticated Session downloads. See
[Review recorded Session decisions](session_recorded_decision_review.md).

Successful Results appear before the secondary raw-JSON import controls. Result
content uses these exact sections and order:

```text
Summary
Recommendation
Alternatives
Evidence and limits
Technical details
```

The model retains these five identities. Issue #252 renders the final identity as
one native **Technical analysis details** disclosure closed by default, retaining
`result-section-5` on its summary rather than repeating the caption in an h2.
The renderer-owned **Downloads for this analysis** utility precedes it, after
Evidence and limits. Available **Analysis Request (JSON)** and **Analysis Result
(JSON)** links are native secondary actions outside every disclosure. Downloads
are not a sixth Result data section or a save of the editable recording. Candidate and
Decision tables preserve retained public order. Whole-game Results explicitly
state that there is no single whole-game Card recommendation. Review coverage,
warnings, fallback, boundedness, information cutoffs, fixed-policy limits,
selected-world limits, observed-Card limits, Coaching/Tactical limits, and Claim
scope are shown only from retained public fields.

Issue #239 remediates #208 retest R09 in the shared Position Summary: the existing
known-party point details read `score_summary.total_declarer_points` and
`score_summary.total_defender_points` from the retained Result. The Position's
`declarer_points` / `defender_points` remain supplemental inputs outside completed
Tricks. Totals already include these supplements once: the R09 completed history
with 0/0 displays 14/29; a separate valid 5/7 input displays 19/36. The unfinished
current Trick, later recording state, Skat/discards, forecasts and adjusted ending
or settlement fields are not added during presentation. This applies to guided
Position analysis/review and saved/current-position Session Results. Historical
and separate Match rendering retain their existing contracts.

Integer zero is displayed as zero. Defensive missing/non-integer total fixtures
show localized **Not available** on that side without coercion or supplemental
fallback, preserving an independently valid other total. Canonical Results already
require both integers; import acceptance and Schemas are unchanged. Focused de/en
normal-Summary assertions cover the score cases, immutable source documents,
candidate/method/order preservation and Historical regressions. The
[Session review guide](session_recorded_decision_review.md#verification-and-future-affected-path-retest)
records genuine Session execution, exact downloads and installed-browser evidence.
Issue #240 supplies the bounded R10 implementation below. Issue #241 adds only
R11's recorded context slice. Issue #251 repairs the candidate layout described
below; Issue #252 addresses download/detail organization below. Issue #253 adds the
single-decision method/information explanation below; other R11 findings stay open.

### Single-decision method and information scope (Issue #253)

`analysis_explanation.py` provides one private frozen scalar projection. It reads
the retained Result, never a current draft, final recording hand, sampled World,
Profile, or file. `result_presentation.py` composes its localized detail rows into
Recommendation and Evidence and limits. `result_localization.py` registers those
private labels. The five section identities, #240 ties, #251 columns/precision/order,
and #252 renderer/download ownership remain. No model/version, route, form, option,
method default, producer text, Request/Result or persistence format changes.

| Retained facts | Normal meaning / technical owner |
| --- | --- |
| `recommendation_method_summary.effective_method`, matching recommendation/Search facts | Actual method, not the requested method or diagnostic baseline |
| Existing `result_immediate._effective_immediate` rule | Supports legacy Immediate only when summary and explicit method setting are absent and no Search result exists; consistent explicit Immediate and Auto fallback also qualify |
| `compatible_world_minimax_v1` | Bounded continuations; each selected possible unseen-Card distribution is fully known within that solver |
| `bounded_information_set_policy_search_v1` | Controlled Player's consistent choices at equal visible information against fixed other-Player policies; not joint-defender or unrestricted perfect strategy |
| `effective_method=none` and no Card | No recommendation; diagnostic comparisons do not supply a replacement |
| Unsupported/contradictory method metadata | Neutral missing/unclear explanation; no repair, rejection or success inferred from settings/prose |
| `settings.sample_count` | Per-Card Immediate setting, not a measured unique-world or full-Game count; strict nonnegative integers only in normal explanation, with missing/bool/malformed data unavailable and actual zero retained |
| Matching Search `status`, `stop_reason`, `world_coverage` | Visible bounded completion, fallback or incomplete/stop consequence; complete does not guarantee the real Game |
| `consumed_budget.selected_world_count`, `completed_world_count` | Selected and completed distribution evaluations, retained separately in Technical analysis details; no per-candidate summation |
| `sampled_world_count`, `unique_sampled_world_count` | Draws including repeats versus distinct sampled distributions; multiplicity retains its weight |
| `requested_budget.max_*`, `minimum_comparable_worlds`, timeout | Requested caps/thresholds, distinct from completed work; existing technical rows |
| `settings.sample_count` beside Search | Explicitly named **Immediate sample setting** in technical scope, never Search completion |
| Immediate `win_rate`, `expected_point_swing` | Current-Trick local-side win fraction and points won minus points lost; Null ranks by its role-dependent objective instead of point fields |
| Search contract-success values | Selected modeled cases, not calibrated forecasts of human play |

The normal **Information cutoff mode** row and unconditional Position limitation
list are superseded by **Information used**, concrete known-Skat use, metric scope
and relevant sampling/coverage. The accepted `analysis_mode` remains inspectable once
in Technical analysis details, with visibility and exact method/budget facts. Existing
warning count and original warning text remain under #252's authority. Whole-Historical
aggregates retain their original presentation and limitations.

| Caller / binding | Information statement |
| --- | --- |
| Guided/manual/imported Position | Supplied facts and accepted policy; `post_game_review` alone establishes no saved historical checkpoint or absence of hindsight |
| Current Session Position | Position retained for that execution, not today's form or recording |
| `task_first_session_rendering._analysis_result` with matching `RecordedReviewSourceV1` | Frozen before-Play situation; the review attaches the accepted actual Card without later Plays/final derived Skat |
| Selected typed Match Report through `task_first_match_state` and `recorded_decision_context_sources.match_analysis_explanation` | Reconstructed before-Card view from accepted evidence for that exact Report/Game, without claiming contemporaneous hand entry |

Skat explanation combines `position.skat` in the **local retained Result** with
`skat_visibility`, accepted allowance and role. An unknown empty pair, known visibility
without concrete local Cards, supplied declarer-known Cards and explicit post-game
knowledge are distinct. Permission alone is not use. A defender's privileged input
can already have been removed by the existing local-information producer; the normal
text says no concrete Cards in this analysis rather than denying that the input ever
contained them. No Card identities are added by this explanation.

The narrow source adapters run inside existing page snapshots/locks. They add no
replay, preparation, sampling, Checkpoint collection, token generation, file access,
analysis or Product save. A failed newer attempt does not relabel an otherwise valid
retained source. Existing invalidation, strict reopen, receipt delivery and exact
download bytes remain. See [installed evidence](unified_workflow_visual_contract.md#analysis-explanations-issue-253).

### Artifact and technical-content ownership (Issue #252)

`analysis_download_rendering.py` composes only caller-supplied available hrefs.
Guided state owns its existing precomputed Request/Result bytes; Session execution
owns its separate existing Request/Result endpoints. Match supplies only its selected
Report Result endpoint and existing availability flag. No Request counterpart or
Teacher-source alias is added. The Match serializer remains distinct from the public
guided/Session envelope. Mutable active-result URLs retain latest-active delivery.

The shared renderer no longer appends a blanket raw copy of normal details:

| Original projected content | Rendering owner |
| --- | --- |
| Summary facts, Recommendation values, Alternatives, ordinary Evidence/limits | Original normal section; optional recorded context replaces its existing equivalent Contract/Next Player/Current Trick rows |
| General/Left/Right fixed-policy details | One localized scoped label each inside Technical analysis details; original joined lead/response text unchanged, explicitly English |
| Position recommendation producer paragraph; safe Historical Replay/Information-set Coaching/Tactical limitation items | Technical prose once, preserving exact producer text |
| Unmapped technical detail identities, including Historical method status counts | Technical details once; trusted labels use existing localization |
| Unmapped enum values hidden by the existing localized technical-value placeholder | Exact original value once in Technical analysis details; the normal placeholder remains, not another raw value |
| Public warnings | Existing visible warning count plus exact technical warning list once |

Position's original technical section retains Search method, solution/policy claims,
policy consistency, controlled decisions, requested Trick/depth/world/minimum/timeout
budgets, consumed depth/nodes/states/information sets, deterministic representative,
declaration flags/Matadors/bid, ending, requested/simulated Multi-Step decisions,
stop/Card policy, Policy Comparison request/recommendation, and public artifact names.
Issue #253 moves requested/effective method, fallback, selected/completed/sampled/unique
world counts, the explicitly named Immediate sample setting and accepted information
mode to this same technical owner. Relevant plain-language interpretation is normal
Recommendation/Evidence content. Equal numbers or strings never merge these fields.

Historical's original technical section retains API/schema versions, Player IDs,
played-at and Game ID, Result/Schneider/Schwarz status, game/effective/required values,
settlement completeness/score, Claim proof state/terminal counts, each selected review/
Coaching/Tactical method and public artifact names. Original model tuples, privacy
filtering, values and order remain unchanged. No policy parsing, execution, source
read or export generation occurs during this composition. Match continues to render
its separate curated Report diagnostic object once, without exposing a full Result.

Recording files have separately named recording contexts, and import metadata has
its own disclosure. Source-safe language/disclosure restoration keeps the same
native disclosure count and existing binding; no workflow JavaScript changes are
needed. See [installed evidence](unified_workflow_visual_contract.md#analysis-downloads-and-technical-details-issue-252).

### Responsive single-decision comparisons

Issue #251 opts only Position **Alternatives** into the private
`candidate_table_rendering.py` helper. `result_rendering.py` passes already formatted,
localized, escaped cells; `ResultTableV1`, projection and effective-method selection
are unchanged. The five-column Immediate and seven-column Search comparisons retain
every candidate, column, value and their original order. Guided Position analysis/
review and current/saved Session Results share this path. Full-Historical Immediate,
bounded Search and Information-set chronological tables keep the original renderer.

Above **56em of local component width**, headings and rows stay aligned. At or below
that width, the same rows become expanded labelled blocks: Card, then each existing
metric in order. The container-relative `em` threshold responds to inherited text
size and narrow parents independently of viewport size, without JavaScript. Values
are never copied into another mobile comparison or parsed back into numbers. Local
labels reuse catalog keys, occupy the full metric width and can wrap long compounds;
normal numeric tokens retain their signs, decimals and percent suffixes.

Native caption/column/Card-row headers remain, with page-local IDs, `headers` links
and explicit static table roles for the changed CSS display types. Narrow repeated
visual labels are real HTML marked `aria-hidden`, so each value remains one accessible
cell. No metric gains a Tab stop. Existing focus/source-return and download behavior
are unchanged. [Installed visual evidence](unified_workflow_visual_contract.md#responsive-candidate-comparisons-issue-251)
supersedes the earlier candidate-table limitation on these tested surfaces. Broader
full-Historical table layouts remain separate. Issue #253 supplies R11 method explanations. Issue #252
adds wrapping analysis-download/technical composition without changing this comparison.

### Optional recorded pre-Card context

Saved Session decision Results additionally pass a minimized, immutable private
[recorded decision context](recorded_decision_context.md) into this renderer. It
appears inside Summary before Recommendation, replacing equivalent raw Contract/
Next Player/Current Trick rows while reusing the existing known-score rows once.
The retained Result owns Cards and turn/contract facts; the matching saved source
owns names and indexes. The legitimate full analyzed acting hand is deliberately
visible in normal read-only HTML, with localized accessible symbols. It is not
limited to legal Cards or candidates and does not append the actual Play to the
Trick prefix. No opponent hands, Skat, full Requests or private execution state
are added. Guided/current-position/Historical callers without recorded metadata
remain unchanged; no producer output or exact download bytes change.

### Equal-best Immediate evaluations

For effective Immediate, the existing Alternatives table uses one **Evaluation**
column: best evaluated, equally best evaluated, or lower evaluated. It preserves
retained order and metrics. The primary Recommendation names all exactly equal-best
Cards with localized names, retains the actual Card and quality, and explains that
an equal-best observed Card has no evaluated disadvantage. Suit/Grand ties include
the shared estimated point swing in the normal explanation as well as in the table.
Thus CJ and played SJ both show 6.00 in the R10 example; 14/29 remains in Summary.

`result_immediate.py` reads only retained Result values, reusing the existing
full-precision game/role objective. Null equality is contract-objective equality,
not equality of Card points. No rounding/tolerance or secondary-metric tie-breaker
is added. Registered fixed detail/column labels keep this narrow catalog-backed
explanation visible; raw English producer paragraphs still belong to Technical
details. The deterministic representative is technical context. Its singleton
flag and the existing ordinal ranks remain exact in downloads.

This applies to legacy default-Immediate Results, explicit Immediate and genuine
Auto fallback. Missing/inconsistent method evidence, incomplete/malformed or
nonfinite/bool/duplicate candidate evidence cannot produce a confident tie claim.
Primary Search and diagnostic Immediate baselines do not acquire effective-Immediate
labels. Public acceptance, Search rendering and unavailable meanings are unchanged.

Presentation performs no recording read, replay, simulation, score calculation or
save. Retained old English strings can coexist with the new metric-based display;
their downloads remain byte-identical. Corrected producer reason/summary text
belongs only to a fresh explicit execution, as described in
[Output JSON](output_json.md#recommendation). Source binding, invalidation and
retirement remain unchanged.

Existing normal states such as `complete`, `partial`, `timeout`, `unavailable`,
`final`, `lot_required`, and `not_assessable` remain successful Result pages, not
HTTP failures. Observed Cards are not described as ground truth, and Search is
not described as perfect play or calibrated probability.

## Errors and HTTP behavior

The private browser transport uses these status meanings:

```text
303    accepted POST followed by redirect
400    input, import, or public validation failure
404    unknown route or unavailable retained download
405    unsupported method on a known route
409    stale revision, stale publication, or duplicate execution
413    oversized request or JSON file
415    unsupported media type
500    generic unexpected internal failure
```

Form failures show a translated error summary and translated field-local escaped
messages where a registered field maps to a visible control. Safe submitted Deal
selections remain in separate bounded process-local feedback state for correction;
the accepted Review draft and exact wizard step remain unchanged. A rejected Run
retains and identifies any last successful visible Result. Unexpected, resource, serialization, and
invariant failures expose no internal message, stack, token, path, fingerprint,
private Source Reference, hidden Card, or complete uploaded document.

## Private routes

The documented private action paths are:

```text
/actions/analyze/run-guided
/actions/analyze/import-json
/actions/analyze/run-imported
/actions/analyze/reset

/actions/review/start
/actions/review/update-players
/actions/review/update-deal
/actions/review/update-declaration
/actions/review/update-discards
/actions/review/append-play
/actions/review/undo-play
/actions/review/update-options
/actions/review/back
/actions/review/run-guided
/actions/review/import-json
/actions/review/run-imported
/actions/review/reset
```

The exact authenticated GET download paths and filenames are:

```text
/downloads/analyze/request.json
    skatmind-position-request.json

/downloads/analyze/result.json
    skatmind-position-result.json

/downloads/review/request.json
    skatmind-review-request.json

/downloads/review/result.json
    skatmind-review-result.json
```

Request downloads use the retained canonical Root document. Result downloads use
the full existing public serializer envelope, including public warnings and
artifacts. Both use deterministic finite UTF-8 JSON bytes, LF line endings, and
one trailing newline. They rebuild and execute nothing and are unavailable before
the corresponding retained value exists.

## Security and accessibility

Issue #211 preserves the Issue #210 loopback token/cookie boundary, exact Host
and mutation-Origin checks, duplicate-header rejection, bounded reads,
`Transfer-Encoding` rejection, restrictive CSP, `no-store`, `nosniff`, frame
denial, no CORS, no access log, and no external resource or runtime request.
Issue #214 changes the response policy from `no-referrer`, which makes non-CORS
browser POST Origin serialization `null`, to `Referrer-Policy: origin`. Concrete
same-origin Review POSTs are accepted; missing, null, forged, malformed, and
Host-mismatched Origins remain rejected. Any Referer is origin-only and therefore
contains no source path or query.

Normal workflows use semantic server-rendered forms, visible labels, text status,
keyboard-operable native Card controls, field-linked error summaries, local error
descriptions, native collapsed disclosures, semantic Result headings and tables,
normal download links, visible focus, and responsive packaged CSS. JavaScript is
optional; Issue #220 adds only a progressive language-form preservation enhancement.

## Current boundary and UAT state

Analyze and Review remain usable and process-local. Session, Match Capture, and
Learning Corpus lifecycle integration is implemented by Issue #212, and Issue
#213 provides canonical `skatmind run` and layered CLI help.

Repeated UAT-01 exposed UAT-FINDING-004. Issue #214 implemented the browser-
Origin correction, and maintainer Microsoft Edge verification resolved both
Issue #214 and UAT-FINDING-004. Repeated UAT-01 nevertheless failed. Issue #208
remains open; UAT-02 through UAT-12 remain paused; B-09 and B-07 remain open;
B-06 remains closed; and Package `1.0.0` and Release preparation are not ready.

Issue #215 freezes the authoritative
[bilingual profile-driven frontend UX contract](bilingual_profile_driven_frontend_ux_contract.md).
Issue #216 implements the shared private profile/localization foundation. When
German is active, Issue #220 now renders Analyze, Review, and fixed Result text
through the German catalog. Issue #217 adds localized one-Decision
current/retrospective and one-completed-Game guidance plus safe related links
outside that English region without changing either workflow. Issue #218 adds
accepted-versus-submitted state separation, safe rejected-value preservation,
and localized accessible contextual validation without changing workflow
execution. Issue #219 changes only private stateful creation, profile settings,
and managed display presentation; it does not change Analyze or Review execution.
See [Profile-driven stateful creation](profile_driven_stateful_creation.md).
Issue #220 is documented in [Task-first bilingual stateful workflows](task_first_bilingual_stateful_workflows.md).
