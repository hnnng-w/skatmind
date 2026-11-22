# Exact tournament monetary valuation (#330)

`evaluate_tournament_money` in `src/skatmind/tournament_money_valuation.py`
answers a conditional question: **given this decision prefix and this finite
joint outcome model, which alternatives have the highest expected personal
future net return?** It values a supplied model exactly. It does not estimate
that model. The existing Session, Cent and Match recommendations do not call it.

## What enters the calculation

* `TournamentPrefix` verifies the original [prepared event context](event_context_and_checkpoints.md)
  against its retained event revision. Its fingerprint binds event, applicable
  terms, participant, source version, game and decision cutoff. Only the
  applicable checkpoint and the established prefix after it contribute. Missing
  individual recordings **covered** by a checkpoint are fine; an uncovered gap
  or conflicting preparation is not. The current recording's actual result
  and later checkpoints are not scenario inputs.
* `terminal_list_game` obtains the **declarer's** signed settlement from an
  exact supported terminal state. It maps the root decision actor's relative
  players to event IDs using the bound seats (rotated for a Match; already
  assigned for a Session). The payee can differ from the actor. `ListGame`
  delegates to the fixed-three-player list scorer: for example, −96 contributes
  −146 and one own loss to the declarer, +40 and no own loss to each defender.
  A specified passed deal accounts for one position; it says nothing about the
  value of *choosing* to pass.
* `TournamentModel` identifies the objective, the revision of the continuation
  and field assumptions, the scenario set, the common current-world occurrence
  IDs and weights, and the monetary basis for the remaining series. It is an
  internal assertion of which pools and costs apply at this cutoff. A producer
  must bind its scenarios to the original decision when constructing them.
  Inventing a new ID cannot turn retrospectively observed facts into a forecast.
* Each candidate covers every occurrence once. Its continuations for each
  occurrence sum to one, independently; each contains exactly one specified
  list outcome per **later** game, the applicable pool standings, and the
  established transfers and charges for that path. Joint weight is world
  probability times conditional probability. Duplicate sampled values retain
  their weights under distinct occurrence IDs. Missing mass, repeated IDs
  within a distribution, a different source/model/payout basis, or impossible
  list length invalidates comparison. There is no inferred weighting.

Each base or selected Plus competition needs its own complete schedule of final
personal awards in cents, including zero for every unpaid rank, field size,
payout edition, and participation/entitlement. A rank must be resolved with
model evidence, or derived from **all other pool members'** modeled scores. For
equal scores the latter requires the number of tied opponents ahead and explicit
resolution evidence. Neither table standing nor another format's tiebreak is
a Standard tournament rank. Coverage includes pools recorded at the cutoff.
Free-text prize descriptions and actual personal receipts do not supply a schedule.

For each path the evaluator first scores the current game once, then the later
games. It uses the [established Standard fee arithmetic](mode_accounting_and_cent_rounds.md)
in cents, `F(final own losses) − F(own losses before the current game)`. Going
from four to six costs 400 cents; a half chance of staying at four and a half
chance of reaching six costs 200 cents in expectation, **not** the 100 cents
for reaching five. The fee edition must be applicable; no local fee is guessed.

Personal future net is the sum of awards and signed future transfers less
incremental fees and other future charges. A tournament-Cent side settlement
requires its own established outcome. Amounts must already incorporate any
applicable per-outcome allocation and rounding; there is no rounding of the
expectation. Unresolved inputs leave path-specific reasons and independently
known components. Any missing required money at positive mass withholds the
whole ranking. Equal expected nets share a rank. The optional complete incurred
net (including entry, table and earlier loss costs) shifts total profit only.
It is not derived from amounts paid or today's rules.

## Executable example: success and money recommend different cards

`tests/test_tournament_money_valuation.py::test_real_common_card_continuations_reverse_success_and_score`
uses a synthetic Grand with one matador, bid 24, and three tricks left. It
reuses the existing compatible-world preparation, side-aware policy, common
batch terminal seam, exact settlement and list scorer. The decision is play 22
of **game 36**: `remaining_including_current = 1`; there are **zero future games**.
The position-34 checkpoint gives B 920 points and five own losses. A's loss
in game 35 brings B to 960/5. Games 1–34 need no invented individual results.

The finite model consists of four draws (synthetic deal seed 605, rollout seed
1), each of weight **1/4**, with deterministic continuation per draw. All cards
face the same six-person base competition: the other table players start on
500 and 650 (both gain 40 if B loses); the other table finishes on 1070, 1040,
and 900. The personal award schedule in EUR is **[30, 0, 0, 0, 0, 0]**. There
is no Plus pool, other charge or transfer. These are developer assumptions, not
EuroSkat payout facts. B's three possible settlements imply:

| Settlement | B's final list points | Base prize | Incremental fee |
| ---: | ---: | ---: | ---: |
| −96 | 960 − 96 − 50 = 814 | EUR 0 | EUR 3 (sixth loss) |
| +48 | 960 + 48 + 50 = 1058 | EUR 0 | EUR 0 |
| +72 | 960 + 72 + 50 = 1082 | EUR 30 | EUR 0 |

| Card | Signed settlements in common draw order | Success | Mean final points | Expected prize | Expected fee | Expected future net |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| S8 | +72, −96, −96, −96 | 1/4 | 881 | EUR 7.50 | EUR 2.25 | **EUR +5.25** |
| H9 | +48, +48, +48, +48 | 4/4 | 1058 | EUR 0 | EUR 0 | **EUR 0** |
| S10 | −96, −96, +48, −96 | 1/4 | 875 | EUR 0 | EUR 2.25 | **EUR −2.25** |

H9 maximizes both success and mean list points; S8 maximizes expected money.
The test records the elapsed valuation and end-to-end fixture cost with the
12 actual terminal evaluations and 108 legal card transitions. Neither timing
nor this illustrative ranking is a performance or strategy guarantee.

## What an ordinary automatic forecast still needs

A future estimator must obtain decision-time evidence for remaining games,
personal and field score/loss distributions and their dependencies; eligible
fields for each selected pool; actual membership, personal shares, complete
paid-place schedules and rounding/tie policy; and the applicable edition of
fees, side transfers and other charges. Ordinary users should not have to
construct statistical models. Win rates alone do not supply a joint field
forecast. Approximately 1100 points is a practical observation, not a threshold
or a guaranteed payout. The published first-prize and interpolation wording is
not a complete executable schedule.

This component is for **post-list analysis and training**. The current
[EuroSkat tournament rules](https://www.euroskat.com/turnierordnung), dated
2026-11-17 and reviewed 2026-11-22, prohibit external decision aids during an
ongoing list. No provider in-play integration or change to existing controls
is part of this work. Bidding/game selection and recommendation-affecting
defender conventions remain separate work.

Provider references: [36-game Standard](https://www.euroskat.com/turniere/36er-standard),
[prize distribution](https://www.euroskat.com/turniere/preisverteilung),
[Plus levels](https://www.euroskat.com/turniere/plus-stufen), and
[fees](https://www.euroskat.com/gebuehren).
