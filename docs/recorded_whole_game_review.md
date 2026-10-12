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

## Immutable derivation

`session_rollout_review.py` is a separate derived-request adapter. Server-owned
selection and observation checks resolve one existing frozen checkpoint. The
unchanged `frozen_request_plus_observed_card` exporter supplies a fresh Request;
the adapter replaces only the analysis method and its method-specific settings,
removes incompatible Search settings, and adds bounded derivation metadata:

* derivation version `1` and `frozen_checkpoint_method_settings_only` policy;
* domain-separated SHA-256 original Request and checkpoint fingerprints;
* checkpoint source revision and explicitly named `checkpoint_decision_index`.

The original Request, checkpoint, and Session persistence bytes are not changed.
No missing checkpoint is constructed. Current opponent hands, later plays,
final results, later declarations, and later Skat facts never enrich the root.
The core receives only its safe decision-time view and settings. Actual-card
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
| `objective` | `played_game_goal` | `played_game_goal`, `complete_settlement` |
| `requested_worlds` | 100 | Integer 1–1000 |
| `random_seed` | 0 | Integer 0–2^64−1 |
| `policy_profile` | `side_aware_baseline` | Exactly this profile |
| `policy_version` | 1 | Exactly integer 1 |
| `max_card_transitions` | 300000 | Integer 1–300000 |
| `max_preparation_work` | 100000 | Integer 1–100000 |
| `wall_clock_timeout_ms` | 30000 | Integer 1–60000; finite and non-null |

Only objective, worlds, and seed are exposed in a native advanced disclosure.
The work/time limits and fixed policy remain server-owned in the browser action.
All settings remain in the Request and technical details. Booleans, unknown
settings, incompatible method settings, unsupported profiles, and unbounded work
are rejected. Original generic simulation fields remain frozen compatibility
context; they do not override the rollout-specific settings or policies.

Played-game goal uses complete simulated card outcomes and normalized declaration
conditions, excluding overbid and complete settlement. It can run without a bid.
Complete settlement requires the core's known bid and matador inputs. The adapter
does not infer an absent matador value even when another method could do so. It
does not substitute a bid or silently choose the other objective.

Missing complete attributed public history/point accounting or an authorized
Ouvert hand produces an explicit unavailable pre-core result with
`source: "flat_decision_input"`. Its domain-separated fingerprint covers the
unprepared safe input, not a fabricated Search view. Valid prepared results keep
the core's safe-view fingerprint and `current_decision` cutoff. Other malformed
or contradictory inputs retain normal validation errors.

## Result meaning

`whole_game_rollout_result` retains the core's aggregate terminal metrics,
settings, policy/version, status/reason, structural work, complete common-world
coverage, exact ranking, and `tied_best_cards`. It exposes no sampled ownership,
opponent hands, hypothetical Skat identities, or private paths.

The compact candidate table shows sampled local-party success count/fraction,
mean final local card-point margin, and settlement score for the settlement
objective. Margin is local party points minus opposing party points, including
Skat points exactly once for the declarer. These are simulated terminal outcomes,
not current-trick values or calibrated real-player probabilities.

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

Incomplete results expose common completed coverage and the stop reason but no
normal ranking or recommendation. There is no Immediate fallback. Browser failure
feedback is not a success receipt.

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
and **1882 keys per language** (previously 67, 119, and 1832).

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
Final focused follow-ups and Quick are reported separately with the completion
handoff. Exact-commit CI and installed maintainer acceptance remain outstanding.

### Bounded developer browser observation

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
