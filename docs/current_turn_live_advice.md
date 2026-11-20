# Live card advice in a Session

Choose **Start live card advice** on the active game's recording page. You can
start before entering the hand. Recording from one player's perspective, opening
a saved recording, and visiting the card-entry page do not start assistance.
Start, stop, and effort changes are native forms; no JavaScript is required.

After an accepted change is saved, the card-entry area shows advice only for
the **current** perspective player's decision. This includes a declaration,
the last required discard, and an opponent's card that passes play to you.
The existing Position export must admit the complete hand and public facts.
An opponent still to play, an incomplete setup, or the end of play needs no
card analysis. A correction or Undo discards the previous advice. Previewing
a correction, a rejected input, or a partial suffix rejection does not run it.

* **One legal card:** one selectable tile with the card and a short rule label. No simulation.
* **Several legal cards:** how often does **your party win the game** after
  each choice? All candidates play out the same sampled deals. The form
  shows all equally recommended cards and up to two evaluated alternatives.
  In a bound three-game Cent round, your **estimated personal return** ranks
  the cards; the win frequency remains visible.
  Each tile is the native radio label: it contains the card face and name,
  recommendation or alternative marker, percentage, successes/common samples,
  and any tie-breaking mean needed to distinguish the leaders. Other playable
  cards remain selectable below. Selecting a tile does not record the play;
  use **Record selected Card**. Nothing is preselected.
* **Effort:** Quick, Standard and More time request **25 / 100 / 400 common
  worlds**, with **5 / 30 / 60 seconds** of evaluator time respectively.
  Seed 0, the 100,000 preparation-unit limit and the 300,000 card-transition
  limit apply. Changing effort cannot select a different objective. These are
  evaluator budgets, not end-to-end deadlines. Specialist analysis, including
  explicit Immediate analysis, remains independent.

Stop, reload, replacement of the active Session, or process restart drops
assistance. A refresh or language switch can display existing advice but does
not execute or publish any. The saved game and its normal decision checkpoints
remain available for review even if advice fails.

## What success means

The adapter takes the admitted current Session Position export, including its
decision-time public plays, relative player map, visible Skat and Ouvert or
continuation hands. The export already derives matadors when the visible
cards establish them. There is no observed-card annotation, post-game input,
later deal reconstruction, manual supplement, or archive lookup.
Outside a bound Cent round the following success-based ranking applies:

* **Complete settlement:** with a supported bid and the required matadors
  (Suit/Grand), success uses the existing exact terminal settlement including
  overbid and declaration obligations. Ranking is by party wins, then terminal
  game score for that party, then final card-point margin. The score is not a
  monetary payoff or a tournament ranking.
* **Played-game goal:** when the bid or a required matador count is missing,
  show the party's simulated success **without overbid evaluation**. Ordinary
  Suit/Grand needs 61 points for the declarer. Announced Schneider also needs
  defenders at 30 points or fewer; announced Schwarz and normalized Ouvert need
  all ten tricks. Defenders succeed when the declarer fails. Ties on success
  are ordered by final party card-point margin. The objective and party are
  printed beside the counts in both languages.
* **Null:** the declarer must take **no tricks**; defenders need the declarer
  to take at least one. The existing fixed values apply to pickup, Hand, Ouvert
  and Hand Ouvert. A missing bid permits played-goal evaluation; a known bid
  above the fixed value is unsupported and produces no ranking. Card points
  never rank or explain Null candidates. At a supported fixed settlement
  value, equal success counts also imply equal total game scores.

Every draw is uniform from compatible assignments, with replacement and common
weight across candidates. Suit/Grand uses the original `side_aware_baseline`
v1 for each later actor. Live Null uses private `null_avoid_or_force_trick` v1:
lead low; as declarer shed the highest legal loser when possible, otherwise
play low; as defender leave a winning declarer on the trick when possible,
otherwise play low. Only actor observations reach the policy. Both use existing
legal transitions and terminal rules. These are frequencies under fixed
continuation policies, not calibrated human win probabilities. There is no
opponent-profile adaptation, future claim, concession, or optimal-play search.

Only **complete common coverage** yields advice. Timeout, cancellation, budget
exhaustion, contradictory or unsupported facts never fall back to Immediate.
For a success-ranked tie decided by a secondary metric, the form shows equal
percentages and the relevant numeric means. The separately labelled **points
from completed tricks** (tricks won for Null) are the recording's current
score, not a forecast or final settlement. None of these numbers needs a
disclosure, hover or separate Results page.

### Personal return in a three-game Cent round

Only an existing accounting round's current Session binding selects this
objective. The binding maps the Session's perspective and seat order to the
round participants and selects the terms for that game position. A Session
title, platform preference, standalone event context or `tournament_cent`
does not select it. No new input is required.

Every legal card plays the **same complete sample**. A supplied matador count
conditions the compatible deals (including the buried cards): “with” and
“without” branches are sampled in proportion to their exact numbers of deals.
Otherwise each simulated Suit/Grand deal supplies its own matador count, using
the declarer's already played and remaining cards plus the two out-of-play
cards. Only terminal scoring uses those hypothetical facts. The Session, its
export and continuation players' observations do not acquire them.

The terminal settlement includes declaration requirements and overbidding.
The signed declarer score, **already doubled on a loss**, goes through the
round's normal pairwise transfer calculation. Each simulated game's applicable
individual fee is rounded **before** averaging. Tiles say **net** only if the
perspective player's net is established for every card in every common deal.
Otherwise all tiles use gross **before fees**: local fees, winning-defender
fee allocation or fractional provider posting can be unresolved. Equal means
remain co-best regardless of win counts. Amounts show fractional cents when
needed. The comparison is for this game, not a prediction of an account posting.

A missing bid retains the played-game comparison with a visible qualification;
a known overbid Null, incompatible declaration, timeout or incomplete common
sample does not produce a monetary recommendation. Forced cards and opponent
turns require no monetary evaluation. Evaluating, viewing and switching
language do not book a transfer or create retained evidence.

Admission freezes the strict accounting binding as well as the saved Session.
A per-source accounting write epoch signals cooperating changes during work.
Publication and delivery also read the bounded file content. Bytes different
from those verified at admission require strict decode and comparison of the
current round identity, revision, terms and participant binding. An unrelated
round need not invalidate the advice. No journal or source reads run inside
the simulated card transitions.

### Synthetic Cent check (#328)

For one short installed check after hosted acceptance, use the disposable
pre-declaration Session, or recreate its complete input below:

1. Create a three-player perspective Session (Alice in forehand, Bob, Carol).
   Start a three-game round on **EuroSkat, ½ cent per point**. Alice's hand is
   `CQ C9 SK H10 HQ HJ H7 DA D9 D8`; set Alice as declarer. If importing the
   prepared Session, the hand and declarer are already saved; start the round
   for that Session.
2. Enable **Quick** Live advice. Declare **Grand Hand, bid 18**, leaving
   matadors unspecified. No plays, Skat cards or other hands are needed.
3. Check the three featured tiles below. All ten legal choices start
   unselected and recording still requires the explicit button. This opening
   alone is sufficient for the installed check.

| Card | Party wins | Expected personal net | Tile |
| --- | ---: | ---: | --- |
| Hearts Queen (HQ) | 2/25 (8%) | −€1.7212 | Recommended |
| Diamonds Ace (DA) | 1/25 (4%) | −€1.7584 | Alternative |
| Hearts Jack (HJ) | 3/25 (12%) | −€1.79 | Alternative |

HJ wins most often, but HQ has the smallest expected loss. Without the Cent
binding the same opening recommends HJ. With the in-person half-cent tariff
the HQ gross estimate is −€1.7184 **before fees**.

**Source observation:** development CPython 3.13.7, headless Edge
157.0.4341.60, page JavaScript disabled, disposable loopback home. The native
declaration submit through visible English advice took **3.041 s cold**,
including save, real round lookup, 25 common deals, 250 terminal evaluations,
7,500 transitions, redirect and page rendering. Switching to German preserved
the amounts and counts and left the choices unchecked. Recording HQ, followed
by H9 and H8, gave another own lead. The H8 submit through visible German
advice took **1.115 s** (25 deals, 225 terminal evaluations, 6,075 transitions).
DA then led at −€1.8624 net, 0/25. Accounting bytes were unchanged. These are
two individual source measurements, not installed acceptance or latency limits.

For reproducing the local checks, the affected parallel pytest modules are
listed below (module names under `tests/`, with the `test_` prefix):

| Area | Modules |
| --- | --- |
| Objective, shared engine and accounting | `cent_live_objective`, `live_whole_game`, `exact_terminal_utility`, `whole_game_rollout`, `whole_game_rollout_workflow`, `accounting_state_store`, `mode_accounting` |
| Native flow and ownership | `cent_live_web`, `session_live_advice_web`, `accounting_web`, `session_declaration_correction_web`, `forced_card_guidance`, `compact_card_entry_web`, `language_switch_context` |
| Catalogs and architecture guards | `complete_frontend_localization`, `frontend_localization_foundation`, `skatmind_rename`, `cli_internal_architecture` |

Use development CPython 3.13 with `-n 2 --dist=loadfile --max-worker-restart=0`.
Run `test_unified_rejection_transport.py` separately after the workers exit,
then explicit Quick and whitespace checks. This scope does not certify the
full hosted gates or installed acceptance.

## Ownership and execution

The Session owner has one process-local preference and at most one automatic
attempt/result. Generation-bound editable forms, explicit Result downloads and
recorded-review evidence remain independent. The native card, compact
declaration, generic command, Undo and applied correction handlers reserve work
against their own committed source. Work runs synchronously **after** releasing
the lifecycle, Session and app locks. There is no second checkpoint save for the
automatic analysis settings.

Admission, publication and final HTML delivery check the active owner, immutable
Session document, generation, effort and attempt. The per-file write epoch also
detects a cooperating writer that restores the original content. Exact byte
comparison to the admitted canonical document checks the file; a different
encoding must pass strict resume and equality. Replaced attempts cannot publish
their advice or failures, or clear newer form feedback on redirect. Automatic
advice produces no archive entry, saved Report, or Learning evidence.
Cooperative cancellation polls only in-memory owner, source generation, write
epoch, effort, attempt and feedback identities. Disk freshness is checked at
the established boundaries, not on each simulated play. The private Live result
does not use the recorded rollout serializer. Recorded v1 still has its original
Suit/Grand policy, objective, aggregate shape, readers and downloads.

## Historical source measurements: original Immediate integration

Disposable loopback Session, Windows, development CPython 3.13.7. One native
Grand Hand trajectory per path, same cards, seed, strategy and 25-sample Quick.
The baseline is `94d115829937be404d57e17f875e6927b308ed93`. Each process
started without a warm schema validator. Fixture creation/hand/declarer setup,
including activation in the automatic case, was separate (1.60 / 1.65 s).
Elapsed times below start at submitting the decision-changing input and include
persistence, redirects, and receipt of the rendered HTML. The manual chain
includes finding and submitting the rendered Analyze form; human think time is
excluded. These are individual observations, not percentiles or an engine speedup.

| Accepted input / resulting turn | Manual chain (s) | Automatic POST (s) | Redirect GET (s) | Automatic total (s) |
| --- | ---: | ---: | ---: | ---: |
| Declaration / first multiple-card decision | 3.807 | 1.730 | 0.083 | 1.815 |
| Play 1 / opponent next | 0.238 | 0.076 | 0.114 | 0.193 |
| Play 4 / multiple cards | 0.745 | 0.268 | 0.133 | 0.405 |
| Play 14 / forced | 0.944 | 0.275 | 0.282 | 0.562 |
| Play 15 / multiple cards | 1.769 | 0.433 | 0.352 | 0.790 |
| Play 24 / late multiple cards | 3.012 | 0.618 | 0.603 | 1.230 |
| Play 27 / forced | 2.230 | 0.562 | 0.739 | 1.310 |

Phase probes are inclusive; they should **not** be added to the totals:

* Cold manual: two saves, two exports and two recording-page renders; 3.394 s
  in schema validation versus 0.073 s in Application execution. Cold automatic:
  one save (0.021 s), one export (0.006 s), input/output schema validation
  (1.573 s), Application (0.071 s), download serialization (<0.001 s), and
  task body render (0.013 s). On cold automatic execution the two distinct
  validators share the same fully checked package registry **within that
  invocation**. Both documents still undergo their own validation.
* Play 24 automatic: candidate/checkpoints 0.058 s, persistence-document build
  0.069 s, save 0.201 s, strict Session loads across the interaction 0.336 s,
  export 0.015 s, schema 0.008 s, Application including provenance 0.126 s,
  serialization <0.001 s, task body render 0.206 s. Rendering the rest of the
  Session page and delivering it are included in the GET column.
* A separate warm play-8 attribution with one unrelated genuine retained
  Session analysis: 0.474 s total; 0.004 s in semantic Position builders,
  0.012 s in the recommendation workflow, 0.008 s in schema validation,
  0.011 s in the three automatic source checks. No archive lookup, snapshot,
  or evidence read. Forced and opponent-only transitions made zero Application
  calls. The growing Session's checked persistence and full page rendering,
  and the cold schema bootstrap, remain measurable.

Source-only headless Edge 157.0.4341.60, page scripts disabled, also exercised
the native card controls, German and English presentation, Stop and Undo. From
the prepared seven-play prefix, submitting H8 to visible first advice took
2.883 s (browser click, save, redirect, completed page and advice in the DOM).
The next own turn took 0.731 s, the forced-card transition 0.707 s. Exactly two
card analyses ran in the sequence. Browser observations include browser and
automation overhead; neither they nor the HTTP timings are installed acceptance.

The maintainer subsequently accepted the installed **Immediate** mechanics and
responsiveness at `7a0680b5c4b1b0d0e5fbc470766c562a10b91e6e`: approximately
4 s first, 1.5 s subsequent, 1 s forced. Those observations are the comparison
reference, not acceptance of the corrected objective.

## Whole-game correction: source evidence

Windows, development CPython 3.13.7. Each version started in a fresh process
and imported the same disposable seven-play Grand Hand recording; native POSTs
were followed through their redirect to the rendered card-entry HTML. Setup
was separate (4.213 s baseline, 2.713 s corrected for that fixture). Grand and
Null openings used ten-card hands and a warm process. Elapsed times in seconds:

| Accepted input | Immediate total | Whole-game POST | Redirect GET | Whole-game total | Evaluator only |
| --- | ---: | ---: | ---: | ---: | ---: |
| H8: first own turn, two candidates | 2.093 | 1.686 | 0.138 | 1.825 | 0.058 |
| SA: next own turn, seven candidates | 0.511 | 0.345 | 0.176 | 0.521 | 0.173 |
| CK: opponent next | 0.420 | 0.163 | 0.219 | 0.382 | none |
| DA: forced S10 | 0.569 | 0.256 | 0.231 | 0.487 | none |
| Grand Hand declaration, ten candidates | 0.231 | 0.486 | 0.105 | 0.591 | 0.393 |
| Null Hand declaration, ten candidates | 0.367 | 0.335 | 0.071 | 0.406 | 0.253 |

For the Immediate baseline the execution boundary, including schema validation
and serialization, took 1.769 s at H8, 0.117 s at SA, 0.065 s for the Grand
opening and 0.108 s for the Null opening. Forced and opponent transitions did
not call it. The evaluator-only column times the corrected core, not that
broader baseline boundary.

The corrected cold adapter took 1.537 s including input schema initialization,
view construction and evaluation. Its 25 common worlds required 1,100 card
transitions; the next turn needed 3,675. For the ten-candidate Grand opening
the added cost is in the continuation itself: **7,500** legal simulated plays,
versus a one-trick analysis. Both openings completed all 25 worlds. Setup of
the separate opening fixtures was 0.800 s / 0.720 s. Results are individual
developer observations, not speed or completion guarantees for other machines,
efforts, or positions.

In headless Edge 157.0.4341.60 with page scripts disabled, native H8 input to
visible advice took **2.322 s**, SA **0.750 s**, and forced S10 **0.888 s**.
In both languages the browser showed SA and S10 at **10 of 25 (40%)**.
SA's mean final margin was −24.16 vs −25.36, not a higher win frequency.
The comparison was outside disclosures, 5.6 CSS pixels from the choices;
both radios remained selectable and unchecked. An injected evaluator timeout
showed brief unavailability with the input still usable. Language switching,
opponent turns, forced guidance, Undo and Stop did not start another simulation.

The two-trick strategic regression uses the documented Grand sacrifice with
only the declarer's legitimate hand and discards exposed. The native card that
passes the lead to the perspective produces **S9: 13/25**, **DA: 8/25**;
explicit Immediate prefers DA instead. The same run checks that an unrelated
genuine retained analysis is not read or updated.

### Local validation scope

On the uncommitted correction to `7a0680b`, the complete 19-module affected
run passed **559 tests in 356.67 s**. It includes the private Live evaluator
and native browser tests, original rollout core and strict workflow, recorded
Session and Match adapters and retention, original evidence decoding, forced
guidance, card palettes, task rendering, localization and Null recording ends.
The separate exclusive `test_unified_rejection_transport.py` run passed
**37 tests in 19.73 s** after the two workers exited. Development CPython
3.13.7 used `-n 2 --dist=loadfile --max-worker-restart=0` for parallel tests,
external temporary/cache/JUnit paths and 7,200,000-ms invocation timeouts.
The final documentation gates are the complete rename and CLI architecture
modules, explicit Quick (Ruff, packaged-schema parity and input examples),
and tracked/new-file whitespace checks. Full-suite, hosted, and installed
results are separate evidence.

## Maintainer installed observations at `33b3dae`

The maintainer accepted the whole-game behavior and response times: approximately
4.5 s for first advice, 1.5 s for subsequent advice and 0.5 s for a forced card.
The seven-play fixture confirmed the two equal success counts after **H8**, fresh
advice after **SA**, opponent suppression, forced **S10** after **DA**, Undo to
revision **26** and Stop. The remaining finding was visual: the numbers and cards
were separate, small, and left most of the desktop panel empty.

## Selectable tile layout: source visual verification

Headless Edge 157.0.4341.60, page scripts disabled, disposable German and English
Session, development source. At 1230 × 860 the panel used 745 CSS px for the form
and 372 px for context, separated by 16 px. The first two tiles each measured
352 × 184 px; card faces and percentages were 36 px. The screenshot showed both
**10/25 (40%)** counts, the objective without overbid evaluation, and the visible
tie explanation. The Ace leads on mean final margin (−24.16 vs −25.36). Beside
them, Boris played ♠Q and Clara ♥8; completed-trick points were 0 to 38.

At 390 × 844 the two 280 px tiles stacked at full available width. The German
objective and margin labels wrapped, with context below the record button and no
horizontal overflow. The seven-card desktop view had three evaluated choices
and four other native radios. The forced view had one rule-labelled tile with
no statistics; the opponent view had observation candidates without evaluations.
In both languages the initial choices were unchecked. Native click and arrow-key
selection sent no POST and did not change the revision before explicit recording.

## Unscored card alignment on Clara's turn

The maintainer accepted the installed large recommendation tiles at `2b458df`.
The remaining finding was visible **before H8**, with Live enabled and Clara
next to play. At a measured German browser `innerWidth` of 3440 CSS px, only
8 of 17 unscored cards kept face and name on one line; rows were 54 or 78 px
high. The 76rem application width cap still applied on that viewport.

The small palette now reduces its column count before names need to wrap.
Each tile reserves aligned positions for its radio, face (including tens)
and full name. Grid rows share the height needed by their content, including
the partial last row. If the entire palette is narrower than one normal tile,
every name moves below its face. The same rules apply to additional cards
below the evaluated choices.

Source Edge 157.0.4341.60, seven-play synthetic Session at revision 20, page
scripts disabled. These are measured CSS pixels, not monitor dimensions:

| Language | Browser inner width × height | Application width | Small palette width | Columns | Each tile (width × height) |
| --- | ---: | ---: | ---: | ---: | ---: |
| German | 1230 × 860 | 1183 | 715.47 | 3 | 233.16 × 45.83 |
| German | 3440 × 1440 | 1216 | 737.47 | 3 | 240.48 × 45.83 |
| German | 390 × 844 | 343 | 279.81 | 1 | 279.81 × 45.83 |
| English | 1230 × 860 | 1183 | 715.47 | 3 | 233.16 × 45.83 |

All four views showed the same 17 native choices in the same order, with full
single-line names and no clipping. Radios, faces and names started 9, 37 and
91 px from the tile's left edge. At 1230 px the 16 px names had 133.16 px of
space; the widest English name, *Diamonds Queen*, measured 129.23 px. At 390 px
with the root text size doubled, every tile grew to 185.64 px high and placed
its full name below the face without clipping inside the palette.

A native click and arrow-key selection focused H8 without a POST or revision
change. Explicit recording advanced to revision 21. The resulting German
Alice screenshot at 1230 × 860 was byte-identical before and after the CSS
change. After SA the four unscored choices also had equal dimensions, including
the last tile alone in its row.

The maintainer subsequently accepted the small palette, completing #327
acceptance at the #328 baseline. Its seven-play sequence does not need to be
repeated for the Cent change. #208 remains open; #326's accepted retrospective
latency deferral is unchanged.
