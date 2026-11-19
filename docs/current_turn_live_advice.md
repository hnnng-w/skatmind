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

* **One legal card:** a short rule-based fact beside the card. No simulation.
* **Several legal cards:** how often does **your party win the game** after
  each choice? All candidates play out the same sampled deals. The form
  shows all equally recommended cards and at most two alternatives, each with
  its success count, common sample count, and percentage. A star marks the
  recommended choices; nothing is preselected or automatically played.
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
For a success-count tie decided by a secondary metric, the form shows equal
percentages and the relevant numeric means. The separately labelled **points
from completed tricks** (tricks won for Null) are the recording's current
score, not a forecast or final settlement. None of these numbers needs a
disclosure, hover or separate Results page.

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

## Later installed acceptance (maintainer)

After source review and successful automatic exact-commit main gates, import the
prepared synthetic seven-play Session (`327-live-seven-plays.json`, revision 20)
once. No full-game re-entry is needed.

1. Start assistance at Quick. The opponent is next. Enter **H8** and time the
   input through visible first whole-game advice. Check both 10/25 results and
   the secondary-margin explanation beside the selectable cards.
2. Enter **SA**; the perspective player leads the next trick and gets fresh
   advice. Enter **CK, SJ, H7, S9** in order; advice disappears while opponents
   are next.
3. Enter **DA**: the only legal card is **S10**, shown without statistical advice.
4. Undo the DA entry (return to revision **26**). Confirm the forced hint is
   gone and the recording can continue. Stop assistance.

Record actual first/subsequent response times and whether they are usable during
play. #327 awaits new hosted and installed whole-game Live acceptance; #208
remains open. #326's accepted retrospective
latency deferral is unchanged.
