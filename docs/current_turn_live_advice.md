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

* One legal card: the existing rule-based fact, with no simulation.
* Several legal cards: the ordinary current-Trick Immediate evaluation. All
  equally best cards are shown, followed by at most two lower-ranked choices.
  In Suit and Grand, the point swing estimates **points won minus points lost
  by your side in this trick**. Null uses its own trick objective. Neither
  evaluation gives the probability of winning the whole game.
* **Quick** starts at 25 samples per card. Explicitly applying **Standard**
  (100) or **More time** (400) updates advice if it is your turn and selects
  that effort for subsequent turns in this game. Seed 0 and basic opponent
  play are unchanged. Specialist settings and their explicit analysis actions
  remain separate. No sample count implies a response-time deadline.

Stop, reload, replacement of the active Session, or process restart drops
assistance. A refresh or language switch can display existing advice but does
not execute or publish any. The saved game and its normal decision checkpoints
remain available for review even if advice fails.

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

## Source measurements (#327)

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

## Later installed acceptance (maintainer)

After source review and successful automatic exact-commit main gates, import the
prepared synthetic seven-play Session (`327-live-seven-plays.json`, revision 20)
once. No full-game re-entry is needed.

1. Start assistance at Quick. The opponent is next. Enter **H8** and time the
   input through visible first multiple-card advice.
2. Enter **SA**; the perspective player leads the next trick and gets fresh
   advice. Enter **CK, SJ, H7, S9** in order; advice disappears while opponents
   are next.
3. Enter **DA**: the only legal card is **S10**, shown without statistical advice.
4. Undo the DA entry (return to revision **26**). Confirm the forced hint is
   gone and the recording can continue. Stop assistance.

Record actual first/subsequent response times and whether they are usable during
play. There is no agreed numerical threshold. #327 awaits hosted and installed
live-response acceptance; #208 remains open. #326's accepted retrospective
latency deferral is unchanged.
