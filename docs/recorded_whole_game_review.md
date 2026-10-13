# Explicit recorded whole-game review

Issue #285 connects the accepted #284 core at
`2b7eae606c59230268bdcc4563eff211cc442c95` to individual saved Session decisions.
Implementation began on `feature/285-recorded-whole-game-review`, at that exact
HEAD with a clean worktree. There was no drift from the accepted core. The
archived `4fce2d0` frontend and #284 handoff were checked against the integrated
contracts; the core commit left the frozen-review frontend unchanged.

## User path and bounded scope

Open a recording and select a saved own decision. **Evaluate whole game** is the
primary explicit POST action; the secondary **Review decision — saved method**
action retains the original frozen method. Both identify the game, player,
trick, card position, and actual card. Viewing, selecting, reopening, translating,
opening disclosures, and downloading never start evaluation.

The new controls belong to individual recorded Session review. The additive
public method is `recommendation_method: "whole_game_rollout"` within the existing
Position Analysis Root, with `analysis_mode: "post_game_review"` and an actual-card
annotation. The seven Root workflows, public contract version `1`, package
version, existing omitted-method behavior, and `auto` behavior remain the same.
Generic public API and installed/module/Legacy CLI transports execute the same
Request. Other modes, Multi-Step, policy comparison, and incompatible execution
overrides are rejected. The underlying normal-play Suit/Grand domain and core
endgame, sampling, policy, and scoring semantics remain those documented in
[the core contract](whole_game_candidate_rollout.md).

Internally, `POSITION_RECOMMENDATION_METHODS` admits the additive rollout method.
The shared `FLAT_RECOMMENDATION_METHODS` vocabulary retains its four existing
methods for Match Reports and their Teacher, Dataset, and Coaching consumers;
rollout does not add a category or alter those retained summary identities.

## Immutable derivation

`session_rollout_review.py` is a separate derived-request adapter. Server-owned
selection and observation checks resolve one existing frozen checkpoint. The
unchanged `frozen_request_plus_observed_card` exporter supplies a fresh Request;
the adapter's original version-1 path replaces only the analysis method and its
method-specific settings, removes incompatible Search settings, and adds bounded
derivation metadata:

* derivation version `1` and `frozen_checkpoint_method_settings_only` policy;
* domain-separated SHA-256 original Request and checkpoint fingerprints;
* checkpoint source revision and explicitly named `checkpoint_decision_index`.

Issue #287 additionally permits explicit analysis-only missing settlement inputs
under the separate version-2 policy documented below. It never describes these
manual values as facts frozen in the original checkpoint.

The original Request, checkpoint, and Session persistence bytes are not changed.
No missing checkpoint is constructed. Current opponent hands, later plays,
final results, later declarations, and later Skat facts never enrich the root.
The core receives its safe card-information view, explicit settings, and any
separately declared manual settlement inputs. Actual-card
comparison is attached after retaining the candidate result. Changing the actual
annotation cannot change sampled worlds, continuation actions, or ranking.

Derivation metadata records references, not independent authentication of an
arbitrary imported public Request. Only the app's retained source binding
authorizes frozen-recording wording. Public imported results use supplied-facts
wording. Mandatory internal provenance retains decision input, analysis, and
after-play comparison separately through final serialization; optional public
field provenance remains available through the existing API option.

## Settings and objective availability

The strict `whole_game_rollout_settings` object requires every effective setting:

| Field | Session action default | Public accepted values |
| --- | ---: | --- |
| `objective` | `complete_settlement` | `played_game_goal`, `complete_settlement` |
| `requested_worlds` | 100 | Integer 1–1000 |
| `random_seed` | 0 | Integer 0–2^64−1 |
| `policy_profile` | `side_aware_baseline` | Exactly this profile |
| `policy_version` | 1 | Exactly integer 1 |
| `max_card_transitions` | 300000 | Integer 1–300000 |
| `max_preparation_work` | 100000 | Integer 1–100000 |
| `wall_clock_timeout_ms` | 30000 | Integer 1–60000; finite and non-null |

Objective, worlds, and seed are exposed in a native advanced disclosure.
Complete settlement also offers only the applicable bid/matador inputs missing
from the selected frozen decision, with empty initial values.
The work/time limits and fixed policy remain server-owned in the browser action.
All settings remain in the Request and technical details. Booleans, unknown
settings, incompatible method settings, unsupported profiles, and unbounded work
are rejected. Original generic simulation fields remain frozen compatibility
context; they do not override the rollout-specific settings or policies.

Played-game goal uses complete simulated card outcomes and normalized declaration
conditions, excluding overbid and complete settlement. It can run without a bid.
Complete settlement requires explicit bid and matador inputs, either retained
in the frozen Request or supplied manually for this new analysis. The adapter
does not infer an absent matador value even when another method could do so. It
does not substitute a bid or silently choose the other objective.

Missing complete attributed public history/point accounting or an authorized
Ouvert hand produces an explicit unavailable pre-core result with
`source: "flat_decision_input"`. Its domain-separated fingerprint covers the
unprepared safe input, not a fabricated Search view. Valid prepared results keep
the core's safe-view fingerprint and `current_decision` cutoff. Other malformed
or contradictory inputs retain normal validation errors.

### Fresh-form objective default

The final #287 adjustment, starting from `8725692`, changes only recorded-Session
form initialization and objective-option wording. The local settings dictionary
in `render_recorded_session_decisions_v1` selects `complete_settlement` when no
applicable retained choice exists. It is independent of core/API defaults.

The retained execution's settings apply only to its exact source-bound decision.
Validation feedback then restores safe submitted values to the matching form;
enhanced language return can restore an explicit unsent choice. Native language
return preserves submitted/retained choices. An explicit `played_game_goal`
choice takes precedence, including after invalid numeric submissions. A rejected
missing, empty, or unsupported objective renders as unselected, rather than
silently acquiring the fresh default; POST validation remains strict.

For an initially selected complete-settlement objective, the existing advanced
disclosure opens when required bid/matador inputs are missing. Only those absent
in the frozen decision are offered, and they remain empty. Known inputs require
no supplement. Native rendering and selection neither execute analysis nor save
the recording, and missing inputs never select another objective automatically.

The selector uses separate `rollout.option.*` catalog keys. Its default annotation
does not appear in retained result identity. Result captions, numeric formatting
(including two-decimal settlement values), columns, layout, ranking, and ties
are unchanged. Core `WholeGameRolloutSettingsV1` still defaults to
`played_game_goal`; public rollout Requests still require the explicit objective,
and omitted-method API/CLI Requests retain their existing semantics. Derivation
versions 1 and 2 and original checkpoint settings remain unchanged.

An HTTP regression uses the normal live declaration form to enter bid `24` once,
records six Plays, and verifies that multiple automatically collected decision
snapshots retain that bid. Their whole-game forms do not ask for a manual bid.
No declaration-entry defect was found, and no older snapshot is backfilled.

### Initial complete-settlement feedback repair

This subsection records the message-only repair integrated at `8c57a02`. Its
objective-only recovery was rejected in the installed retest; the current
supplementation path below supersedes that recovery presentation.

Issue #287 reproduces the ordinary rendered-form sequence at baseline
`75d189dea3d871ea81195e58752f3006830f5f89`: a successful played-goal result,
then changing only the objective to complete settlement. The disposable saved
second-trick C7 decision has no bid and a safely inferred matador value of `1`.
The maintainer's recording and retained analysis were not accessed.

The first failing boundary was **feedback construction**, after successful form
parsing, source binding, Request derivation, public validation, and an expected
core result with `stop_reason: "missing_terminal_utility_inputs"`. The route
constructed a `FrontendValidationIssueV1` with `rollout.incomplete_attempt`, but
that contract accepts only `validation.*` keys. The resulting `ValueError` was
mapped to legacy `validation.recorded_review.invalid_fields`, falsely saying
that analysis settings were forbidden. The earlier opening regression checked
the lower availability notice and retained result, but not this misleading
summary.

The corrected route consumes its exact immutable, publication-checked attempt
notice and uses valid validation keys. The notice retains the actual missing
`bid_value` and/or `matadors` from the derived decision-time Request, only when
the existing structured core reason identifies missing terminal inputs. It
does not obtain those inputs from current or later recording facts. Separate
messages name a missing bid, missing matadors, or both. Original settlement
eligibility and the public Result contract are unchanged.

Both languages show an objective-unavailable heading and explicit guidance to
choose the separate played-game objective if desired. Safe attempted objective,
sample count, and seed survive feedback and native/enhanced language return.
The existing accessible field-feedback mechanism associates the explanation and
summary link with the exact source-bound **Evaluation objective** control and
opens its advanced disclosure. No editable bid field or legacy selection-only
action is offered as recovery. No alternate analysis starts automatically.

Strict field allowlists and bounds are unchanged. Malformed fields/settings,
malformed selection, stale/foreign selection, and evaluation failures now have
distinct whole-game feedback; the legacy action retains its selection-only
contract. Unavailable and incomplete attempts retain the previous completed
execution, its source label, and exact Request/Result bytes. An additional
caption identifies the retained result's own objective separately from the new
attempt. Existing source/generation/attempt checks, supersession, actual-card
comparison, ranking, tied-best presentation, and sampling remain in force.

### Analysis-only missing-input supplementation (current)

The October 13 maintainer addendum explicitly extends #287 beyond message repair.
The original recording, checkpoint, and frozen Request remain immutable. A new
complete-settlement analysis may use only explicit, validated values for
originally missing `bid_value` and/or `matadors`. Already known values cannot be
submitted, even if the proposed value is identical. Other declarations, Cards,
hands, scores, Players, and history are not editable through this form.

The normal advanced form offers **Bid for this analysis** and/or **Matadors for
this analysis**, without defaults. Domain validation retains a positive integer
bid and the existing positive consecutive-top-trump count: Suit `1–11`, Grand
`1–4`; both "with 2" and "without 2" use `2`, not a signed replacement convention.
The browser text transport accepts at most 20 digits (plus an optional minus
sign, which domain validation rejects). The native objective selector uses CSS
conditional presentation, not an analysis request or JavaScript requirement.
Without support for that CSS enhancement, the same labelled inputs remain usable
and explicitly scoped to complete settlement. Switching to played-game goal
disregards their text and derives the unchanged original factual root.

One short note explains that the missing values apply only to analysis and the
recording remains unchanged. Offering an empty field produces no error. An
explicit empty/invalid submission produces one inline field error, opens the
advanced disclosure, and focuses the actual input. It does not execute. This
case has no repeated red summary or missing-input notice at the result. Safe
values survive rejection and native/enhanced language return, and remain scoped
to their source-bound decision form. Previous output is captioned once at its
result section. Genuine conflicts, unsupported contracts, and execution failures
retain distinct feedback.

`rollout_derivation.py` validates the additive policy:

| Derivation field | Meaning |
| --- | --- |
| `version: 2` | Separate derivation version; Public API remains version `1` |
| `policy: "frozen_checkpoint_with_manual_settlement_inputs"` | Original facts plus the narrowly permitted explicit supplements |
| Existing source fingerprints/revision/index | Original Request/checkpoint identity, unchanged |
| `original_request` | Exact original public Request wrapper, with before-card mode and no nested rollout derivation |
| `supplement_origin: "manual_analysis_input"` | Caller-supplied analysis assumptions, not verified historical facts |
| `supplements` | Nonempty object containing only originally absent `bid_value` and/or `matadors` |
| `effective_declaration` | Exact normalized declaration used in the new execution |

The ordinary public execution boundary validates the original fingerprint,
reconstructs the permitted method/settings/observed-card transformation plus
supplements, and compares every other Request fact exactly. Schema validation
rejects malformed metadata and unknown fields; runtime validation rejects known
overwrites, contradictory effective inputs, changed facts, invalid domain values,
and supplements on played-game goal. Version-1 derivations retain their exact
policy and validation, and unsupplemented Requests do not acquire new metadata.
No old retained/exported bytes are rewritten.

An imported Request can establish consistency with its supplied original, not
authenticate a real historical recording by itself. The Session path additionally
resolves and revalidates the actual server-owned checkpoint, document, generation,
file fingerprint, and attempt token. Evaluation remains outside the global lock.
Supplement values are copied as immutable work, never written to recording or
profile storage. Failed and superseded work cannot replace the prior completed
execution. An explicit incomplete-input attempt also supersedes older in-flight
work, without running an alternative objective.

The existing Result echoes the validated derivation and effective declaration.
Result field provenance identifies supplemented declaration values as
`caller_supplied`, referencing `/whole_game_rollout_derivation/supplements/...`.
Card evidence retains its before-card cutoff; manual settlement values are
separate assumptions for this analysis. The visible result contains one compact
manual-input caption and its own objective. Fingerprints and the full derivation
remain in Calculation details and the canonical Request/Result downloads.

## Result meaning

`whole_game_rollout_result` retains the core's aggregate terminal metrics,
settings, policy/version, status/reason, structural work, complete common-world
coverage, exact ranking, and `tied_best_cards`. It exposes no sampled ownership,
opponent hands, hypothetical Skat identities, or private paths.

The compact candidate table shows the card with recommended/played/equally
recommended text markers, goal success count and percentage in completed
simulations, mean final point margin, and settlement score for the settlement
objective. There is no repetitive lower-rated column. All legal candidates keep
their exact retained order. Margin is local party points minus opposing party
points; a defender's party is both defenders together. These are simulated
terminal outcomes, not current-trick values or real-player win probabilities.

`whole_game_rollout_comparison` attaches the actual card descriptively:

* `equal_complete_objective`: exact equality of the core's complete integer tuple;
* `lower_primary_success`: fewer sampled successes;
* `lower_secondary_outcome`: equal success but a lower settlement score or margin;
* `unavailable`: incomplete/unavailable evaluation.

The first responsible metric and integer-total gaps are retained. Full equality
with a different canonical representative is explicitly display ordering only.
All-candidate primary ties are stated explicitly. Rendering never re-ranks rounded
values or applies Immediate quality thresholds. The legacy Immediate summary is
unavailable for this method; the method-specific comparison owns the assessment.

### Focused clarity correction

The single-winner view uses direct **Recommended card** and **Played card** labels. For
the supplied 100-world synthetic case, it says that played CJ matches the
recommendation, all ten cards reached the played goal in all 100 simulations,
and the higher mean final point margin distinguishes CJ from the next alternative.
That preference is explicitly not a higher simulated goal-success rate.

Other results use their exact retained comparison state. Primary differences
refer to success frequency; equal-success secondary differences identify either
mean settlement score or mean final point margin. Complete-settlement ordering
remains success, settlement score, then margin. All tied-best cards receive text
markers and an explanation that their fixed display order confers no evaluated
advantage. A sole legal card is identified without inventing a comparison.

Number formatting uses the existing request-local locale context. English uses
`100 of 100 · 100%` and `101.18`; German uses its localized count wording, a space
before `%`, and `101,18`. Percentages normally use at most two decimal places,
with additional precision when rounding would falsely produce 0% or 100%.
Missing/non-finite values are unavailable, zero sample counts are not divided,
and rounded negative zero is displayed without a minus sign. Formatting never
changes numeric Result fields, rankings, or semantic ties.

Fixed-policy dependence, simulation-only percentages, the played-goal settlement
exclusion, and the party-oriented margin definition remain visible. The existing
native technical disclosure is labelled **Calculation details** for this method.
It contains policy/version, sampling, source/cutoff explanation, and exact raw
rollout values. Source captions, decision-return links, and downloads remain
available; no new JavaScript or global styling is introduced.

Only newly executed rollout output changes the legacy
`post_game_review_summary.decision_explanation` prose. It starts with
"The legacy immediate-trick review summary is unavailable for whole_game_rollout."
A completed comparison directs the reader to `whole_game_rollout_comparison`;
incomplete/unavailable work explicitly says no whole-game card comparison is
available. Legacy availability/reason codes, other fields and numeric values,
schemas, and other methods retain their existing behavior. Passive rendering and
language changes do not rewrite a previously retained explanation or export.

Incomplete results expose common completed coverage and the stop reason but no
normal ranking or recommendation. There is no Immediate fallback. Browser failure
feedback is not a success receipt.

### Complete tied-best primary summary

Issue #286 corrects the primary summary for completed multi-card ties. It uses
the authoritative `tied_best_cards` in its retained order, under **Equally
recommended cards**, with the full localized name and code of every card in the
same visible label/value layout. The existing shared renderer and responsive
wrapping give all cards equal prominence before the alternatives table.

For the synthetic C9/C8/C7 full tie, the primary value is **Clubs Nine (C9),
Clubs Eight (C8), Clubs Seven (C7)**. The next value is **Played card: Clubs Seven
(C7) — equally recommended**, even though the canonical representative remains
C9. The accompanying text identifies membership and no evaluated disadvantage.
Comparisons with a lower candidate refer to the recommended group and preserve
the decisive success-count, settlement-score, or point-margin distinction. Full
ties describe aggregate equality, not identical individual simulated trajectories.
Both languages use the existing translation catalogs.

Single winners retain their singular summary. Nonmatching actual cards retain
their metric-based comparison without a positive membership marker. Incomplete
and unavailable results do not acquire a recommendation set. Equal primary
success or rounded display values do not establish a full tie. Legacy methods,
calculations, exact ties, ranking, canonical order, machine fields, schemas,
numeric Results, export prose, and retained Request/Result bytes are unchanged.
Rendering and language switching reuse retained output without evaluation or
recording saves.

## Ownership, lifecycle, and downloads

The active Session retains one latest legacy execution and one latest rollout
execution, each with its own immutable source label and canonical Request/Result
bytes. The existing legacy download URLs remain bound to the legacy slot. Rollout
downloads use `/sessions/downloads/rollout-request.json` and
`/sessions/downloads/rollout-result.json`, under the same authenticated protection.
Requests are executable Root JSON; Results use the existing public execution
envelope. No browser-only download format is introduced.

An incomplete first execution is inspectable/downloadable. A later incomplete
attempt retains an earlier completed execution and records only one bounded
notice identifying the failed source, objective, coverage, and reason. Rejected
or failed attempts preserve previous valid bytes and labels. Source mutation,
strict reload, retirement/replacement, or stale/unverifiable disk content clears
both slots through the existing lifecycle. No cross-restart retention is promised.

Immutable work is captured under the Session lock and short app binding lock.
Public evaluation runs outside both locks. Before publication, the exact source
document, generation, current attempt token, active context, and strict loaded
file fingerprint are checked again. Superseded work cannot publish. Language and
deletion-context binding includes both execution slots. Evaluation performs no
recording save or revision change.

## Schemas, examples, and verification

The authoritative and packaged `whole_game_rollout.schema.json` adds strict
settings, derivation, comparison, and aggregate Result components. Input/output
Root schemas enforce the additive method and incomplete-result restrictions.
There are now **72** authoritative and byte-identical packaged schemas.
The private frontend inventory is **68 POST routes**, **120 form definitions**,
and **1941 keys per language** after the fresh-form default adjustment, derived
from the registry and both strict catalogs. Analysis-only supplementation had
1939 keys, and the message-only repair had 1927 keys.
The existing whole-game form now has six registered safe fields, including its
two conditional analysis inputs; the installed smoke expectation matches them.
No route, form, schema filename, or generated-output scenario was added.
The tied-summary correction
had 1914 keys per language (1906 after the earlier clarity correction, 1882
before it; the initial pre-rollout frontend had 67 routes, 119 forms, and 1832 keys).

`examples/whole_game_rollout.json` is a two-world no-bid opening. The actual
98-scenario inventory was preserved in order, with four append-only cases:
`whole_game_rollout_played_goal`, `whole_game_rollout_settlement`,
`whole_game_rollout_unavailable`, and `whole_game_rollout_partial`. The current
inventory is **102**; historical published release counts remain historical facts.

The focused suites include the actual core, original checkpoint exporter,
recorded-review HTTP path, public API/schema and serialization, descriptive ties,
failed-attempt retention, source/attempt races, and language/view preservation.
Small routine fixtures avoid repeated default-size executions. The combined
affected selection passed 835 tests; the subsequent transport/example/language
selection passed 474 tests. The generated-output validator passed all 102 cases.
Those figures describe the initial implementation validation. The maintainer
subsequently confirmed technical integration, installed execution, and English
readability at actual 200% zoom, but rejected result comprehensibility. The
subsequent #285 clarity correction was accepted. Issue #286's complete tied-set
summary requires its own exact-commit CI and brief installed-summary retest.

### Earlier developer browser observation

One default-size native POST used a disposable saved synthetic opening containing
all Clubs plus SA/S10, known H7/D7 discards, actual CJ, no bid, seed 0, and 100 worlds.
Source-checkout Edge **155.0.4283.45**, CPython **3.13.7**, completed the action in
**6.410 seconds**, including transport/rendering; core work recorded **4230.95 ms**,
2624 preparation units, 30000 transitions, and 1000 terminal evaluations.
It counted 184756 compatible worlds and completed 100 common worlds for all ten
candidates. Every candidate tied on sampled primary success at **100/100**.

Secondary mean margins were CJ **101.18**; C9/C8/C7 **93.20** each; SA **92.04**;
S10 **92.00**; CQ **86.66**; CK **84.66**; C10 **72.66**; CA **70.66**. CJ was the
sole best complete objective in this run, not a higher sampled win-rate claim.
No test requires CJ or SA to rank first.

English/German 1365×900 and German 390×844 views showed the same retained metrics;
the narrow table used the existing labelled card blocks with no measured page or
result overflow. Screenshots were inspected. Four native downloads matched the
exact retained legacy/rollout bytes. After fixture/legacy setup, counters recorded
**one rollout execution and zero recording saves**, including language changes,
viewing, resizing, and downloads. Recording and checkpoint bytes were unchanged.

Evidence is outside the repository in
`$env:TEMP/opencode/issue285-browser-9pmk4sga/report.json` and adjacent screenshots.
The report records module/catalog/resource hashes and exact download hashes.
Served CSS and script bytes matched checkout resources; CSS SHA-256 was
`d2b2a25363a879364e61c5b7fcbdf5638f2a3c94d0df6d8bb1bf2437e25f2d74`.
This is source-build, headless, synthetic evidence. True 200% browser zoom and the
brief installed-build observation remain for the maintainer. The UAT installation
and recording were not accessed. Issue #208 and release acceptance remain open.

### Clarity-correction browser observation

At base `61de48d96f0fa5607a8921030884bfcfb25803b0` with the presentation edits,
headless Edge **155.0.4283.45** and CPython **3.13.7** reused the earlier
developer-owned synthetic completed Request/Result pair. Both documents were
validated and the Request was matched to the disposable saved checkpoint before
binding the retained fixture. No maintainer recording or download was accessed.

One 7.496-second presentation sequence covered German/English **1365×900** views,
German **390×844**, native keyboard opening/closing of Calculation details, and
preservation of the open disclosure across language return. Screenshots and DOM
measurements showed the direct card labels, three-column comparison, all ten
cards, localized percentages/margins, and no measured page/result overflow.
CJ remained `101.18`, SA `92.04`, and C9/C8/C7 `93.20`, with 100/100 successes for
every candidate. This was retained evidence, not another 100-world evaluation.

After fixture setup, counters recorded **zero analysis executions and zero
recording saves**. All four native legacy/rollout downloads matched their original
bytes, including the old retained legacy explanation. Served CSS and script bytes
matched checkout resources. Evidence is under
`$env:TEMP/opencode/issue285-clarity-ya1tut9m/report.json`, with module/catalog/asset
and download hashes plus adjacent screenshots. CSS remains
`d2b2a25363a879364e61c5b7fcbdf5638f2a3c94d0df6d8bb1bf2437e25f2d74`.

This source-build observation does not transfer the previous installed English
200%-zoom acceptance to the changed markup and does not establish maintainer
comprehension. The short installed wording/table and true-zoom observation remains
with the maintainer; no repeated headless true-zoom probes were performed.

### Tied-summary browser observation

At base `498c5835f06d40dbb0153c71d25c6c704a454479` with the #286 presentation edits,
source-checkout headless Edge **155.0.4283.45** and CPython **3.13.7** reused one
typed synthetic completed Result with C9/C8/C7 tied at **100/100**, mean margin
**105.20**, actual C7, and lower alternatives at **104.20**. Fixture setup used
one-world scaffolding and synthetic aggregates through the real Session POST and
public output validation; it did not run a 100-world rollout.

The **6.451-second** passive sequence inspected both languages at **1365×900**
and one narrow condition, **390×844**. Screenshots and DOM measurements showed
the complete primary set, immediate C7 membership, equal text styling, wrapping,
and no measured page/result overflow. The accessibility tree exposed the plural
label without a second singular recommendation label. Opening Calculation
details and switching language reused the same retained Result.

After fixture setup, counters recorded **zero analysis executions, zero rollout
executions, and zero recording saves**. Both native rollout downloads matched
the original retained Request/Result bytes; the disposable recording and frozen
checkpoint were unchanged. Served CSS and script bytes matched checkout resources.
The report records the module path, browser identity, source/catalog/asset hashes,
summary measurements, and download hashes under
`$env:TEMP/opencode/issue286-summary-t_gu754_/report.json`, with four adjacent
screenshots. CSS remains
`d2b2a25363a879364e61c5b7fcbdf5638f2a3c94d0df6d8bb1bf2437e25f2d74`.

This is synthetic source-build evidence. The brief installed tied-summary retest,
including actual browser zoom observation, remains with the maintainer. Automated
checks do not establish maintainer comprehension. Issue #286 remains open pending
full exact-commit CI, identical-commit integration, and that acceptance. The
maintainer's UAT installation, recordings, checkpoints, and retained downloads
were not accessed.

### Availability-correction browser observation

At base `75d189d` with the #287 edits, source-checkout headless Edge
**155.0.4283.45** and CPython **3.13.7** used a new disposable completed Session
with a saved second-trick C7 decision. The original frozen decision has no bid
and a visible matador value of `1`. One native played-goal submission used one
world and seed `7`; it completed normally. The next native submission changed
only the advanced objective, retaining every other successful control and the
server-owned source selection.

The core returned unavailable for missing terminal inputs, with one preparation
unit and **zero sampled/materialized worlds, card transitions, and terminal
evaluations**. The English → German → English sequence preserved the attempted
settings and correct explanation. Activating each summary link focused the
visible objective control in its open advanced disclosure. Screenshots were
inspected; the retained-result text separately identified the previous played-goal
objective. The accepted tied-best summary remained present.

There were exactly **two public execution calls and two core calls** (the
explicit successful action and explicit unavailable action), **zero recording
saves**, and no additional execution during language return, feedback navigation,
or downloading. Both native Request/Result downloads matched the prior completed
execution byte-for-byte; the recording, checkpoint, execution object, and source
binding were unchanged. The source/browser identity, counters, screenshots,
feedback-target observations, and download hashes are retained under
`$env:TEMP/opencode/issue287-browser-elm7hyft/report.json`.

The affected regression selection passed **317 tests**, including the actual
Session rollout adapter, whole-game workflow, legacy and whole-game HTTP paths,
validation preservation, localization, language return, result presentation,
supported settlement, distinct missing-input cases, and source/attempt races.
The missing-input tests forbid sampling and fallback, and verify retained
Request/Result downloads plus recording/checkpoint identity through both
languages. A newer unavailable attempt also supersedes older in-flight work.

This is developer-owned synthetic source-build evidence, not installed-build
acceptance or evidence of maintainer comprehension. Full exact-commit CI,
identical-commit integration, and the brief installed missing-input retest remain
with the maintainer. Issue #287 remains open pending that acceptance.

### Supplementation browser observation

At base `8c57a02b238093b5c97afed1efc99fe6b494666d`, the existing local browser
harness used a new disposable completed recording and its saved second-trick C7
decision. Headless Edge **155.0.4283.45**, CPython **3.13.7**, **1365×900**, and
disabled page JavaScript exercised the native form. This did not access UAT data.

One-world played-game analysis completed. Changing only the objective exposed an
empty bid control without an availability error or execution. Submitting it empty
focused the actual field with one short inline error and retained both prior
downloads byte-for-byte. Entering **18** explicitly and submitting produced a new
complete-settlement result. That number is a declared synthetic analysis
assumption, not a recovered historical bid; the frozen bid remains absent.

English → German → English showed the single manual-input result caption,
complete-settlement objective, preserved form value, and unchanged tied-best
presentation. Native downloads matched the new execution's exact bytes. There
were **two executions, two core calls, and zero recording saves** across the whole
sequence; the empty submission, typing, selection, language return, and downloads
caused no extra execution. Original recording/checkpoint bytes and the old
Request/Result objects remained unchanged. Screenshots were inspected. Evidence
and hashes are under `$env:TEMP/opencode/issue287-supplement-88u7hrz5/report.json`.

The affected selection passed **1037 tests**, including actual Session/export,
HTTP, public API, input/output schema, provenance/serialization, localization,
retention/race, and package-resource/smoke-inventory modules. Tests include missing
bid, missing matadors, both missing, invalid values, known-value rejection,
factual/metadata tampering, exported public execution, objective switches, and
cross-decision isolation. These developer checks do not establish historical
truth or maintainer comprehension. Exact-commit CI, identical-commit integration,
and the brief installed supplementation recovery-path retest remain pending.

### Fresh-default browser observation

At base `87256928048739dcfa7cc4c30a681eaabddd14a4`, the existing browser harness
used a new disposable second-trick C7 snapshot with a missing bid. Headless Edge
**155.0.4283.45**, CPython **3.13.7**, and disabled page JavaScript showed fresh
English and German forms with complete settlement selected, the exact approved
option labels, an open advanced disclosure, and an immediately visible empty bid
field. No failed submission was needed to discover it. Screenshots were inspected.

An explicit native selection of played-game goal hid the supplemental field and
caused no evaluation. One explicit one-world/seed-7 submission then retained a
played-goal result. Native English/German language return preserved that choice,
execution identity, Request/Result bytes, and unchanged recording/checkpoint bytes.
Counters recorded **zero evaluations before explicit submit**, **one evaluation
in total**, and **zero recording saves**. No recommendation or zoom matrix was
repeated. Evidence is under
`$env:TEMP/opencode/issue287-default-gtt_vn_u/report.json`.

The affected selection passed **436 tests**, including actual Session HTTP,
form-preservation, localization, derivation, public-default, numerical-formatting,
tied-best, and retained-result modules. The normal declaration-to-checkpoint test
also passed. This is synthetic developer evidence, not installed-default
acceptance. Exact-commit CI, identical-commit integration, and the short installed
default-selection check remain with the maintainer; #287 remains open.
