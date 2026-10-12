# Bounded whole-game candidate rollout

Issue #284 implements stage 1: a private executable Suit/Grand evaluator for one
decision, including ten remaining tricks. Method `whole_game_candidate_rollout`,
method version `1`, compares every legal root card by normal terminal outcomes
under one deterministic continuation profile. It is outcome evaluation under
fixed policies, not optimal-policy Search.

## Internal entry points and data flow

The modules are `whole_game_rollout.py`, `whole_game_rollout_contracts.py`, and
`whole_game_rollout_policy.py` under `src/skatmind/`.

```python
from skatmind.whole_game_rollout import evaluate_whole_game_rollout_v1
from skatmind.whole_game_rollout_contracts import WholeGameRolloutSettingsV1

# view is a decision-time SearchInformationView from the existing safe builders.
result = evaluate_whole_game_rollout_v1(
    view,
    WholeGameRolloutSettingsV1(random_seed=284),
)
aggregate_document = result.to_dict()
```

`prepare_whole_game_rollout_v1(view, settings)` returns a frozen, builder-owned
`WholeGameRolloutPreparationV1`. It reconciles the view with the existing safe
builder, selects the objective, derives one canonical legal candidate tuple,
counts compatible assignments, and materializes one bounded IID world sequence.
It retains only decision-time input and private execution roots. It has no
serializer and excludes roots and the information view from its representation.

`execute_whole_game_rollout_v1(preparation)` starts each candidate independently
from each immutable root. It forces the candidate once, then repeatedly builds
the next actor's observation, selects a baseline action, and applies the shared
legal transition until terminal. The private optional `candidate_order` is a
permutation of the full legal set, useful for scheduling-invariance verification.
It cannot select a subset. Results always use canonical candidate order.

The one-call evaluator composes these operations. Settings, work, candidates,
preparations, and results are immutable. Timing is separately identified and
excluded from value equality. Preparation does not execute any candidate path.

## Supported decision boundary

* A fixed three-player table, Suit or Grand, and normal remaining play.
* Perspective `me`, a concrete declarer, resolved local party, and `me` next to act.
* One through ten unresolved tricks, including zero, one, or two already played
  cards in the current trick.
* Complete attributed public prefix, its accepted points and reliable trick
  ownership, exact own remaining hand, public remaining counts, normalized
  declaration, legitimate Skat knowledge, and authorized public hands/voids.
* The existing `live_local_view` or `historical_decision_snapshot` source with
  `current_decision` cutoff. The caller must obtain a historical view from the
  unchanged frozen decision snapshot, not reconstruct it from future evidence.

Completed roots, unresolved declarers/turns, other actors/perspectives, Null, and
missing strict-settlement inputs return explicit unavailable reasons. Malformed
or contradictory views raise validation errors. Complete attributed history is
required: unaccounted score offsets, legacy unattributed played cards, and missing
trick ownership are not substituted with invented history. A zero compatible
count returns `incompatible_world_space`.

Ouvert requires an authorized public declarer hand. Known Skat is forbidden for
Hand games and local defenders. A non-Hand local declarer may retain zero, one,
or two legitimately known out-of-play cards; subsequent local observations keep
exactly that knowledge. Sampling never supplies the missing identities to that
actor. The existing world builder's new `allow_partial_root_skat_knowledge`
keyword defaults to `False`, preserving strict existing Search preparation.

Null and shortened-ending simulation are not part of this slice. Existing
authorized exposure evidence may constrain normal remaining play, but this
evaluator does not simulate future exposures, concessions, Claims, or other ends.

## Reused components

The evaluator uses the immutable `SearchInformationView` boundary,
`build_compatible_search_world_space`, existing exact assignment DP and IID
sampler, and `build_exact_search_state_from_compatible_world`. It does not invoke
the three-trick Information-set Search preparation or five-trick Minimax gate.

`InformationSetSearchWorldStateV1` carries exact ownership privately while
`build_information_set_search_observation_v1` supplies actor-visible facts.
`apply_information_set_search_card_v1` delegates each play to the existing
`ExactSearchState` transition, updating public history, hands, and voids. Card
ownership, follow obligations, partial-trick resolution, trick winners, and
score accounting therefore share the existing rules implementation.

Previously scored points are carried forward exactly. Current-trick points are
awarded only when its third card is played. The two fixed out-of-play cards are
never played and are added exactly once to declarer points by
`get_exact_search_terminal_facts`, which checks 120 points and ten tricks.

## Fixed policy profile

Profile `side_aware_baseline`, version `1`, applies to **all** later actors,
including the root player's subsequent turns:

| Actor | Lead | Response |
| --- | --- | --- |
| Declarer | `basic_trick_play` | `basic_trick_play` |
| Each defender separately | `basic_defender_lead` | `basic_defender_response` |

Selection reuses `get_preferred_opponent_cards_by_policy`, with the first card
in canonical deck order among equally preferred legal cards. Declarer leads
thus currently prefer lowest-point legal cards. Defender cooperation sees only
the public current winner and the acting defender's own hand. Partners are
separate actors, never one jointly informed hand.

The selector's only input is `InformationSetSearchObservationV1`. It receives
no world, world identifier, sample index, random seed, hidden partner hand, or
private continuation. Other simulated non-Hand declarers may see their own
world's Skat; local root knowledge remains the frozen subset described above.
Equal observations produce equal actions. No nested Search or Monte Carlo runs
inside the baseline. The profile is intentionally simple, not a model of actual
human strategy or an optimized contingent policy.

## Objective version 1

An objective is selected once, before counting or sampling. No fallback changes
it between worlds or candidates.

### `played_game_goal` (default)

Existing point-result and declaration-announcement helpers determine whether
the declarer achieved the played goal. Ordinary Suit/Grand needs at least 61
points; announced Schneider additionally requires defenders at 30 or fewer;
announced Schwarz and normalized Ouvert require all ten tricks. A defender's
zero-point trick still defeats Schwarz. Success is complemented for a local
defender, and card-point margin is oriented to that local party.

Ranking is descending mean local played-goal success, then mean final local
card-point margin. Bid and matadors may be unknown. Settlement scores remain
absent, and the result explicitly states that played goal excludes overbid and
complete settlement. A supplied high bid does not change this objective.

### `complete_settlement` (explicit)

Known bid and matadors are required by the unchanged
`has_supported_terminal_utility_inputs` check. Missing inputs produce
`missing_terminal_utility_inputs` before sampling. Every leaf calls
`build_exact_terminal_utility`, preserving existing declaration, overbid, and
settlement semantics. No bid or matador value is inferred or invented here.

Ranking is descending mean local settlement success, then mean local game
score, then mean local card-point margin. All supported normalized Suit/Grand
declarations reuse the existing exact terminal adapter, including overbid.

Both objectives compare integer totals at common sample coverage to avoid
floating-point tie artifacts. Canonical card order is only the final
reproducibility tie-breaker. `tied_best_cards` includes every equal best
objective tuple; a canonical recommendation does not claim strict improvement
over another tied card. These are terminal metrics, not Immediate trick-point
losses or mistake labels.

## Sampling, limits, and interruption

| Setting | Default | Accepted range |
| --- | ---: | --- |
| `random_seed` | Required | Integer 0 through 2^64 - 1 |
| `requested_worlds` | 100 | Integer 1 through 1000 |
| `max_card_transitions` | 300,000 | Integer 1 through 300,000 |
| `max_preparation_work` | 100,000 | Integer 1 through 100,000 |
| `wall_clock_timeout_ms` | `None` | `None` or integer 1 through 3,600,000 |

Booleans and non-integers are rejected. The existing child-seed derivation uses
the new stream `whole_game_rollout_worlds_v1`. Selection is always uniform IID
with replacement, including tiny or one-world spaces; it never silently
enumerates or deduplicates. The same ordered sequence is used by every
candidate. Duplicates retain one unit of weight for every draw.

Preparation work counts one bounded validation/fingerprint unit, one bounded
assignment-construction unit, every uncached DP state in both existing counting
passes, every sampled card assignment, and one bounded exact/public root
materialization unit per draw. This is structural accounting, not a CPU-time
estimate. Optional hooks were added to the existing counter and a streaming
wrapper around the same sampler. They allow interruption before material work
and avoid allocating an unbounded enumeration. The original batch sampler keeps
its sequence and duplicate behavior.

Work records distinguish completed samples, materialized roots, unique draws,
preparation units, all attempted card transitions, terminal evaluations, and
elapsed milliseconds. Each candidate path has exactly the remaining held-card
count of transitions. Discarded partial-batch work remains in these counters.

Both operations accept an injectable monotonic clock and zero-argument
cancellation predicate. Active preparation time counts toward the shared
elapsed limit; idle time between separate prepare/execute calls does not.
Checks occur during counting/sampling, before materialization and each play,
before terminal evaluation, and before committing each common batch.

A world contributes to aggregates only after **all** candidates have completed
for it. An interrupted batch is discarded. Earlier common batches remain
inspectable with identical candidate sample counts, but any preparation limit,
transition limit, timeout, or cancellation yields **no ranking, tied-best list,
or normal recommendation**. The evaluator never falls back to Immediate.

## Safe results and verification

Ordinary output contains only method/objective/profile identities, settings,
status/reason, source/cutoff and a domain-separated fingerprint of the safe view,
compatible and sampled coverage counts, work, candidate terminal totals/means,
complete ranking/ties, and limitations. The source fingerprint hashes only the
decision-time view; it is not a sampled ownership digest. Results retain no
worlds, observations, hidden hands, hypothetical Skat identities, or paths.

`tests/whole_game_rollout_oracle.py` independently transcribes the same fixed
preferences and uses plain list-based continuation accounting with the shared
card rules. It does not call the new selector or either production transition
adapter. A six-world combination oracle checks exhaustive aggregates at the
sampler seam; real seeded draws separately check repeated, unequal multiplicity.
The small manual Grand fixture starts at 36 declarer / 46 defender points with
four Skat points and two remaining tricks:

* `DA`: wins `DA/D7/DQ` for 14, then loses `S9/D10/S10` for 20; final 54/66.
* `S9`: loses `S9/D7/S10` for 10, then wins `DQ/DA/D10` for 24; final 64/56.

This demonstrates an Immediate-trick/terminal-outcome ranking difference under
the same fixed policies. It is not a comparison against optimal Minimax.

### One bounded opening measurement

On Windows 11 build 26300, CPython 3.13.7, the synthetic Clubs opening containing
all eight Clubs plus `SA/S10`, known discards `H7/D7`, no bid or matadors, and
seed `284` completed the default 100 worlds. It counted 184,756 compatible worlds,
sampled 100 unique draws, completed 100 common samples for each of ten candidates,
and performed 2,624 preparation units, 30,000 card transitions, and 1,000 terminal
evaluations in **2.971 seconds** (one wall-clock development run).

All ten cards had sampled played-goal success 100/100. The primary objective
therefore tied; secondary mean final local margins were:

| Card | Mean final margin |
| --- | ---: |
| CJ | 105.56 |
| C9, C8, C7 | 98.32 each |
| SA | 96.94 |
| S10 | 96.82 |
| CQ | 91.26 |
| CK | 89.26 |
| C10 | 77.26 |
| CA | 75.26 |

`CJ` was the sole best full objective tuple in this run. Neither `CJ` nor `SA`
is asserted as the opening winner in regression tests. Those tests use small
samples and assert availability, candidates, objective, and complete accounting.
The measured success fractions are fixed-policy simulated outcomes, not
calibrated real-player win probabilities. Timing is not a cross-machine latency
guarantee or a recurring benchmark gate.

## Stage 2 integration and acceptance

Issue #285 implements [explicit recorded whole-game review](recorded_whole_game_review.md)
through the separately derived public `whole_game_rollout` Position method,
strict settings/schema/serialization, bounded provenance, post-evaluation actual
comparison, localized Session controls, and separate retained result ownership.
The accepted core policy, scoring, sampling, and work semantics remain unchanged.

Stage 1 itself added no public routing or controls. Its technical acceptance is
recorded at `2b7eae6`. Stage 2 retains the package/API/workflow versions, Session
persistence, and global defaults. Its focused tests and Quick are local evidence;
exact-commit CI, identical-commit integration, and the brief installed retest remain
maintainer work. Issue #208 remains open. These methods do not establish general
optimal Skat, overall recommendation quality, or user acceptance.
