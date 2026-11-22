# Empirical tournament scenarios (#331)

`produce_empirical_tournament_money` in `src/skatmind/empirical_tournament_scenarios.py`
estimates personal future net cents for a **recorded card decision in a single-series
EuroSkat 36er Standard tournament**. It takes the target Match document, event context,
game and play index, original donor Match documents with availability evidence, factual
field data and the existing seeded rollout effort settings. It constructs the common
world measure, card candidates and continuations and calls the [#330 evaluator](tournament_money_valuation.md).
There is no forecast-rank, probability or future-game input.

## What can enter a forecast

* **Historical population.** `empirical_tournament_sources.py` uses the recording-facts
  adapter: strict Match resume, observed-game reconstruction, canonical Historical
  materialization, signed declarer settlement or an explicitly recorded pass, at **all
  36** positions. Missing, unfinished and unsettled are distinct exclusions. The original
  document must identify EuroSkat and the canonical 36er Standard format. A source-bound
  `AvailableList` identifies the exact revision and content fingerprint, single series,
  tournament mode, fixed-three-player scoring rule and dated evidence of availability
  of the **complete** outcome block. A retained analysis report is unnecessary.
* **Time.** The decision cutoff within the game is immediately before the selected play.
  The conservative wall-time cutoff for external information is the target's recorded
  **Match start**. A donor's complete-block availability instant must be **strictly
  earlier**, and later than its own start if recorded. Start alone, video offsets,
  filesystem/import times, date-only or ambiguous times are insufficient. Comparison uses
  offset-aware instants at microsecond or coarser precision; an unspecified offset
  (`-00:00`) is not used. The factual field sheet must already be available at target start.
* **Identity.** Group by logical Match ID and any EuroSkat external Match ID, including
  transitive aliases. Exclude the entire target group. Count an exact copy once; quarantine
  groups with competing versions or conflicting evidence instead of picking a revision
  on the caller's behalf. Equal scores do not identify copies. Reliable source acquisition
  must preserve logical IDs/aliases across imports.
* **Current table.** Extract only positions before the current game as outcomes; map
  established declarers to the bound event players. Use the list scorer for all three,
  and the validated event projection/checkpoint for the payee's points and own losses.
  A covered recording gap still identifies **which opponents, position and evidence
  status** prevent an all-player prefix. The selected player's checkpoint is not an
  opponent score. Build the rollout view from the existing reconstructed Match snapshot:
  the actor's hand, visible declaration, authorized Skat/public hand and pre-play trace.
  No current recorded settlement, later target outcome or final standing is a forecast input.
* **Field sheet.** `FieldFacts` binds the complete field to the exact target version,
  event, series, game, decision, evidence reference and availability time. It identifies
  every table and its three participants in fixed table-place order. An unstarted or
  unconditioned remote table uses zero positions of progress. An observed remote prefix
  requires its position **and all three factual point totals**; position 36 is a known
  final table and needs no draw. No external current-table score override is allowed.
  Each applicable pool needs members, the payee's participation and entitlement, payout
  edition and complete per-rank personal awards (including unpaid places). The base field
  covers the tournament; Plus members are a subset of the same field. The supported tie
  rule is a documented priority established **before** the cutoff, used only between
  equal scores. An unknown priority cannot settle a realized tie. It is not an assertion
  about the actual EuroSkat tie rule.

## Sampling and valuation

Policy `uniform_recorded_standard_table_blocks_v1` sorts eligible logical donors by Match
ID and draws uniformly **with replacement**. Each modeled table has a separate seeded
random stream. Dependence *within* a table is retained: use the same recorded ordered
block for all three people, mapping donor places 1–3 to recipient places 1–3 throughout
the rotation. The model assumes independent tables and reuses observed play without
skill, recency or score weighting or counterfactual bidding adjustments.

For each complete compatible-world batch, play **every legal root card** through the
existing whole-game fixed policy and obtain its signed terminal settlement. Apply that
current outcome once to the current three players. All cards share the same donor draw
for positions `game + 1` through 36, and the same remote table draws for positions
`through + 1` through 36. Project the resulting joint scores into each pool; there is no
second draw for someone in Plus. Game 36 has no target suffix. If every remote table
is already complete, game 36 needs no donors at all.

There are `N` distinct current-world occurrence IDs at exact weight `1/N`, one joint path
at conditional probability one per card and occurrence. Duplicate values keep their
mass; these are sample weights, not calibrated probabilities. The model fingerprint
binds the exact prefix, cutoff, donor versions/evidence, field sheet, policy, settings,
decision view and occurrence draws. Target revision bytes bind identity but do **not**
seed either the current worlds or table draws. Changing only a later actual target game
requires re-preparation; the draws and numerical values reproduce, while the old basis
is rejected.

The evaluator retains explicit zero awards for excluded pools and known fee/award
components when other money is unknown. Only fixed, evidenced transfers/charges may
be supplied; contingent side settlements without a supported factual basis stay unknown.
A positive-mass monetary gap withholds the ranking. Unavailable sources or interrupted
work cannot produce a successful comparison on a renormalized subset. Diagnostics
retain exclusions by version/reason, distinct donor count, modeled table IDs, completed
draws, work counts and preparation time. Bounds include 128 supplied sources, 64 tables,
eight pools and 500,000 candidate/occurrence/pool-member projections; existing rollout
world, preparation, transition, cancellation and deadline limits still apply. Donor
materialization, cumulative table scores and suffix reuse are invocation-local.

## Reproducible six-player example

`tests/test_empirical_tournament_scenarios.py::test_recorded_sources_to_joint_money`
starts with **two valid synthetic original Match recordings**, a third Match with
play 22 of game **33**, and a separate **synthetic** six-player field sheet. It checks
the resulting joint standings, awards, fees and expected nets independently. All
amounts below are **EUR cents**. In place order A/B/C:

* Through position 32, eight B wins of +48 give B `8 × 98`, and four B losses of −144
  give B `4 × −194` and each defender `4 × 40`: prefix **(160, 8, 160)**, B on four
  own losses. Other positions were recorded passes.
* Donor 1: A +48 at 3, C +48 at 35, B −144 at 36; all others passed. Its whole
  trajectory totals **(138, −194, 138)**; its 34–36 suffix contributes **(40, −194, 138)**.
* Donor 2: B −144 at 6, B +48 at 34, A −144 at 35; all others passed. Its whole
  trajectory totals **(−154, −56, 80)**; its 34–36 suffix contributes **(−194, 138, 40)**.
* The remote D/E/F table has no observed progress. Rollout seed 1 and four occurrences
  yield donor IDs **(remote, current suffix)**: **(2,2), (2,1), (1,2), (1,1)**.
  Base awards for A–F are `[3000,1500,800,400,100,0]` in rank order. Plus awards for
  B/C/D are `[600,200,0]`. Tied scores use the indicated member order. Other costs and
  transfers are confirmed zero in the synthetic sheet.

| Card | Genuine B settlements in draw order | Expected prize | Expected loss fee | Expected future net |
|---|---|---:|---:|---:|
| H9 | +48, +48, +48, +48 | 1900 | 50 | **1850** |
| S10 | −96, −96, +48, −96 | 1050 | 225 | **825** |
| S8 | +72, −96, −96, −96 | 925 | 225 | **700** |

For example, S10 in occurrence 2 gives A and C +40 each and B −146 for the current
loss. Add donor 1's suffix to obtain **(240, −332, 338)**. The other table has donor
2's whole scores. B is sixth in base and third in Plus: zero prize. B's fifth and
sixth losses cost **100 + 300 = 400** incremental cents, so net is **−400** on this
path. The integration test times source preparation and the complete call, and verifies
three source extractions (32 prior target positions and two 36-position donors), four
common worlds, 12 terminal evaluations and 108 legal transitions. One Windows development
CPython 3.13.7 run measured 177 ms for source preparation and 194 ms for the complete
producer-to-comparison call. These are fixture measurements, not installed latency or
evidence of strategy quality.

## Acquisition and applicability

A managed Match records one table. It does **not** supply dated prior availability of
complete lists, a whole tournament roster, other tables' cutoff progress, selected pool
memberships/entitlements, tie evidence, complete applicable personal payout schedules,
or all fees/transfers. The private fact types identify what's needed from independently
verified sources; they do not establish an importer or provider export. Win rates, prize
interpolation prose and an observation around 1100 points cannot fill those gaps.

Applicability is post-list analysis and training under the [documented EuroSkat rules](tournament_money_valuation.md#what-an-ordinary-automatic-forecast-still-needs).
Ordinary recommendations and Learning eligibility are unchanged. Bidding/game choice,
defender conventions and ordinary factual acquisition remain separate work. #326's
retrospective-latency deferral stands; #208 remains open.
