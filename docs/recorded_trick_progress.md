# Recorded Trick history and captured Card points

Issue #227 adds a private read-only Session and selected-Match-Game presentation:
**record a Card → recognize the Trick → inspect each Player's captured totals →
retain the correct accepted prefix after correction**. This partially remediates
C6. It is neither final scoring nor whole-frontend acceptance.

## Accepted-source ownership

`app_web/recorded_trick_progress.py` normalizes only named recorded Players,
Game seats, accepted chronological Plays, completed-Trick winners/points, status,
and an optional recording warning. Frozen slotted values and tuples retain every
completed prefix. There is no serializer for a complete trace, reconstructed hand,
private evidence, Result, or persistence document in this component.

* **Session:** `project_session_trick_progress` consumes the `SessionProjectionV1`
  already replayed by `project_task_first_session_v1`. Its completed Tricks supply
  the rule-derived winners/points and its incomplete Trick supplies accepted Plays.
  The page's existing Session lock covers facts, rendering and form bindings. The
  adapter performs no additional replay, Checkpoint collection, or rule evaluation.
* **Match:** `project_match_trick_progress` consumes the accepted immutable Workspace
  and selected Game, using `recovery_tricks(game)` and the existing
  `get_trick_winner`/`get_trick_points` rules. The existing
  `find_observed_trace_warning` supplies the same #222 warning to feedback and totals.
  No Historical materialization or hidden-hand reconstruction populates progress.
  The page captures progress, names, recovery actions, and Card bindings together
  under the Capture lock. Selection is rechecked there after the earlier language
  source capture; an intervening navigation cannot pair one Game's view with another
  Game's recovery actions. Existing language-source conflict handling still applies.

Internal Player identity is the recorded stable ID. Display labels come from the
Session roster or the same Workspace's Match participants. Match column/row order
uses the selected Game's historical seats, not fixed table places or a current
profile rename. Within each Trick, Plays retain actual accepted order, including
leads by the preceding winner in Middlehand or Rearhand.

## Exact prefixes and scope

One chronological accumulation credits each complete Trick's full existing Card
point value to its winner and increments that Player's won-Trick count once. A
zero-point Trick still counts. Every completed row retains its own immutable
prefix; the running summary returns the last completed prefix. With a declaration
and no completed Trick, all captured totals are genuinely zero.

At every prefix:

* the three won-Trick counts sum to the completed recorded-Trick count;
* the three captured-point values sum to those completed Trick values;
* the known declarer has their own total; the two defenders retain distinct
  individual totals plus a separate combined party total;
* absent declarer identity yields unknown party assignment, never a perspective-
  or seat-derived default.

The scope note excludes Skat, discards, unplayed remainder and final settlement.
Neither contributed Card values nor `120 - recorded` are assigned to Players.
Nothing calculates Game value, settlement, Match standings, quality, probability,
or an automatic winner of the Game. Existing final Results are unchanged.

An independently counted Grand fixture leaves `HA` and `D10` outside play:

| Completed prefix | Forehand tricks / points | Middlehand tricks / points | Rearhand tricks / points |
| --- | --- | --- | --- |
| 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| 1: `CA SK H9` | 1 / 15 | 0 / 0 | 0 / 0 |
| 2: `C10 SQ H8` | 2 / 28 | 0 / 0 | 0 / 0 |
| 3: `CK SJ H7` | 2 / 28 | 1 / 6 | 0 / 0 |
| 4: `S9 DA SA` | 3 / 50 | 1 / 6 | 0 / 0 |
| 5 | 4 / 57 | 1 / 6 | 0 / 0 |
| 6 | 5 / 63 | 1 / 6 | 0 / 0 |
| 7 | 6 / 66 | 1 / 6 | 0 / 0 |
| 8 | 7 / 76 | 1 / 6 | 0 / 0 |
| 9 | 8 / 80 | 1 / 6 | 0 / 0 |
| 10 | 9 / 93 | 1 / 6 | 0 / 0 |

The final captured sum is **99**, including when those two Skat Cards are known.
The fourth Trick starts with Middlehand. A separate `HJ SJ DJ / C7 C8 C9` Grand
fixture credits Middlehand 6 points and then Forehand a zero-point won Trick.

## Presentation and edge states

`recorded_trick_rendering.py` renders the shared read-only rows. Recovery supplies
action markup separately. Session's separate winner paragraphs and flat normal
Play list are replaced; its technical Command history, entered evidence, event/end
display and #221 recorded-decision actions remain. Match enhances its existing
#222 history with exactly one `match-play-{decision_index}` target per accepted
Play. Local Card positions restart at 1/2/3 and never replace those global indexes.

The compact running summary is beside recording controls on wide screens and
immediately after them on narrow screens. Full history follows recording, never
precedes the next-Card controls. All ten Tricks and correction targets stay open
and reachable without JavaScript, pagination, or virtualization. No Product form
is duplicated. Existing language form/disclosure identities and return fragments
remain authoritative. Localized Card symbols have full accessible names and exact
codes; numeric values have definition-list labels and units.

* An incomplete Trick has only accepted Cards/actors; winner, credited points and
  cumulative prefix are absent. An unsent or rejected Card and a recovery preview
  do not enter history.
* Empty slots, passed deals and undeclared setup have explicit distinct statuses.
* Thirty Plays yield exactly ten Tricks and no current Trick/next actor in this
  display. Session still needs its existing explicit Game End and export evidence.
* Supported shortened Session endings count only completed observed Tricks. A
  terminal incomplete Trick is explicitly not credited; concession/exposure/other
  awards do not distribute a remainder here.
* Null displays **Tricks won** and omits ordinary point metrics in running and
  cumulative rows. A short scope explanation distinguishes its objective. Internal
  rule values and Result outputs remain intact, with no automatic capture stop.
* An accepted partial contradiction retains #222 diagnostics and links. The running
  summary explicitly marks its unresolved recording basis. A proposed thirtieth
  Card can reveal a conflict while the accepted summary remains at 29 Plays.

## Correction and read-only lifecycle

Applied replacement, declaration correction, Session Undo/partial correction,
Match rewind, clear/pass, explicit Reload, reopen and selected-Game changes derive
new prefixes from the returned accepted source. There is no browser or persisted
counter, separate scoreboard cache, extra route, or issue-specific version.

Preview/cancel, same-Card no-op, invalid retained suffix, source conflict and failed
Save preserve accepted totals. A Session correction that changes the first winner
can retain three Plays and discard the now-invalid later lead: those three accepted
Plays, not the original/requested suffix length, determine the new summary.

Rendering and language switching execute no analysis, materialization, transfer,
preparation, Card Command, Checkpoint collection or Product Save. Existing #221
Results/downloads and #222 selection expiry/Apply tokens survive read-only views;
genuine changes retain existing invalidation. Language preference saving remains
separate. JavaScript preserves an unsent Card across language changes; without it,
unsent input in another browser form cannot be recovered, as documented by #223.

## Focused automated and installed-browser verification

`tests/test_recorded_trick_progress.py` uses legal existing source builders with
independent prefix expectations: Suit/Grand/Null, Jacks/trumps, changing leaders,
zero-point Tricks, all declarer/perspective identities and Match rotations,
0/1/2/3/5/29/30 boundaries, known Skat, shortened ends and partial correction.
`tests/test_recorded_trick_progress_web.py` uses real returned creation, Card,
review, Undo, replacement, Apply, cancel, reopen and slot-selection forms. It
checks actual HTML totals, exact anchors, single-save counts, real #221 execution
and byte-identical downloads. Fault injection is confined to a pre-replacement
Save failure and a deterministic navigation interleaving. Read-only spies forbid
Product writes, execution, Checkpoint collection, materialization and transfer.

A **577-test** focused compatibility run passed across the new tests and #221–#226,
replay/history/files, recovery, localization/security, standalone and packaging.
After the installed-browser reflow correction and extra read-only test, **35**
targeted rendering/visual/localization/HTTP checks passed. Final full-check results
belong to the implementation report.

`scripts/verify_recorded_trick_progress.py` reuses the dependency-free DevTools
harness and an existing local Edge executable. Run it with a separately installed
Wheel environment's Python, `--browser PATH --output FRESH_SCRATCH_DIRECTORY`.
It rejects checkout imports and compares 12 loaded module/resource byte hashes
with the checkout, then verifies the actual authenticated HTTP CSS/JS hashes.
No browser dependency or mandatory framework is added to the full check.

On September 13, 2026, Python **3.13.7**, Package **0.17.0**, and headless Microsoft
Edge **152.0.4191.66** completed **176 measurements**, German/English and JavaScript
enabled/disabled, at **1365×900**, **390×844**, **320×800**, and representative
**200% text at 320×800**. Each computed font size is doubled once; device scale
and browser zoom are unchanged. States include both workflows' incomplete,
completed and ten-Trick histories, Null, errors, a partial warning, correction and
diagnostic navigation, with a long synthetic Player name.

The first run found a German 200%-text Session analysis-form intrinsic grid
overflow (467 versus 305 document pixels). The app-owned Session form track is
now shrinkable. Final document/client widths agree at **1350/1350**, **375/375**
and **305/305**. Screenshots were inspected for readable wrapping, totals, Card
codes, error/warning text and keyboard correction controls. At narrow/enlarged
sizes the summary follows the selector and requires ordinary vertical scrolling;
full history never displaces the next-Card controls above the return target.

Native Space/Enter recorded six Session Plays and one Match Play in each script
mode. Native Match selection/preview/confirmed Apply changed captured points
**28 → 24 → 28**; previews retained **28**, then **24**. Recording and Apply focused
the existing recording section approximately **16 CSS pixels** below the viewport
edge. Native warning navigation focused `match-play-2`. An actual Advanced Match
duplicate submission was rejected without changing bytes/totals. The browser
displayed **93/6/0 points and 9/1/0 won Tricks** at ten Tricks. Session Null's real
declaration correction retained a three-Trick prefix with **3/0/0**; rotated Match
Null showed **0/0/1**. JavaScript language switching retained unsent **H8** in both
directions with exactly one language POST and unchanged Product bytes. Setup and
long continuation sequences used real returned HTTP forms, not injected states.

Temporary synthetic evidence, outside Product/UAT data:

```text
<temporary-directory>/opencode/tricks-227-installed-final/
  evidence.json                 # Actual values, geometry, focus, actions and hashes
  summary.json                  # completed: true; measurements: 176
  {js,native}-{state}-{de,en}-{1365,390,320}-{1,2}-{area}.png
  {js,native}-diagnostic-target.png
```

Representative inspected files include
`native-session-ten-de-390-1-summary.png`,
`js-session-error-de-320-1-recording.png`,
`js-match-corrected-de-1365-1-recording.png`,
`native-match-ten-en-320-1-last.png`, and
`native-match-corrected-de-320-2-history.png`.

```text
app.css      d77f6abf998807214f70c6ef731ae530b6730e0ea25252f8e273793a7b616fc3
workflow.js  f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298
```

Other browsers, physical devices and assistive technology were not inspected.
These are synthetic implementation checks, not maintainer UAT.

## Validation-blocker follow-up

The two original complete-check attempts remain **unsuccessful historical
evidence**, each with **8,480 passed, 1 skipped, 1 failed**. One failed the
Information-set Search public-provenance additive document-equality assertion;
the other failed the standalone Corpus security test with Windows error 10053.
The 78 new #227 tests passed in both attempts. No successful complete check
preceded this follow-up. The original report also records an isolated provenance
pass and ten matching native comparisons; those do not explain its failed field.

On September 14, 2026, at baseline
`b8eb8e3b0eca8f7df29896e8db1720100ae810f7` on
`feature/227-trick-history-points`, the exact Corpus target reproduced error
10053 in `HTTPResponse._read_status`, before response headers were available,
on the `Origin: <server-origin>////` POST. It failed again after adding client
`finally` cleanup. Python 3.13.7's actual `HTTPConnection._send_output` sends
headers and body separately; the default HTTP/1.0 handler returns after writing
the rejection, closes its buffered streams, and immediately shuts down/closes
the socket. A bounded synthetic probe synchronized a late 55-byte body with that
cleanup and observed all 55 bytes unread at the socket. That instrumented request
received a real 403; it demonstrates the ordering, not the precise packet-level
cause of every recorded abort. No OS-security or environmental cause is claimed.
The new split-body regression failed against the old transport because cleanup
ended without retaining the receive direction for late bytes.

The correction is limited to
[`corpus_web/server.py`'s rejection lifecycle](learning_corpus_browser_workflows.md#loopback-security-and-network-boundary):
real 403 delivery, write-side shutdown, opaque bounded drain, then normal socket
cleanup. Tests cover seven Host/Cookie/Origin rejection variants, two synchronized
late chunks plus an otherwise authorized pipelined request, no Product parsing,
dispatch, temporary upload or state access, unchanged persistent bytes, and an
authorized initialization on the same live server. Missing, duplicate, oversized
and transfer-encoded framing cannot extend cleanup. Byte-cap, advancing-deadline
and partial-response-write regressions retain the existing security decisions.

The exact provenance target passed in isolation, and three additional native
document pairs matched. Retained original failure output was not found in local
scratch/tool outputs, so its original differing JSON path remains unknown.
Controlling only the private executor clock with different elapsed inputs exposed
exactly `/information_set_search_result/consumed_budget/wall_clock_elapsed_ms`
(`125` versus `250`); no non-timing differences were observed. The additive test
now resets `information_set_search_executor._monotonic` to the same advancing
clock for each real public execution. Exact full-document equality removes only
the additive `field_provenance` root. Coverage and hidden-information exclusions
remain intact. Two real public-execution regressions verify 125-ms elapsed
reporting without a timeout and timeout at the exact 125-ms deadline with 250-ms
elapsed reporting at Result construction. Search/public serialization/provenance
production code and global clocks are unchanged.

Follow-up checks, before the required final complete check:

* The first Corpus module run after the transport patch had **21 passed / 4
  failed**: four new synthetic handlers lacked the standard-library `requestline`
  fixture attribute. After fixing that test setup, those four tests passed.
* **175 passed in 92.18s** across the complete Corpus transport and provenance
  modules, executor/core-routing, Corpus core/uploads, and both #227 modules.
* Three fresh-process diagnostic runs of both original targets plus all seven
  split-body variants each passed **9/9**, in **8.28s**, **8.42s**, and **8.42s**.
  All outcomes are retained; there is no retry, skip, or platform exemption.
* Focused Ruff passed. The final-tree complete-check output, exit status and
  totals belong to the accompanying implementation report; focused passes do
  not substitute for that mandatory local gate or exact-merged-commit CI.

The only additional files beyond the original 22-file #227 feature manifest are
`src/skatmind/corpus_web/server.py`, `tests/test_local_learning_corpus_web.py`,
`tests/test_information_set_search_provenance.py`, and
`docs/learning_corpus_browser_workflows.md`. This adds 18 focused regressions.
Current #227 handoff/validation notes are updated in the already-listed
`docs/project_handoff.md` and this file. No #227 implementation/resource or browser
harness is changed by the follow-up. The 176 installed-browser measurements above
remain September 13 feature-build evidence, not measurements of the later complete
validation build. The standalone server is not used by the unified browser paths,
so those measurements need no affected-path rerun for this transport/test change.

## Compatibility and remaining gates

Package **0.17.0**, Python **>=3.13**, dependencies, license, APIs, Command kinds,
seven Root workflows, 71 Schemas/resources, six Session examples, persistence and
98 generated outputs are unchanged. Standalone presentation is unchanged. Host,
Origin, CSP, no-CORS, authentication, request limits and privacy retain existing
boundaries. There are no new routes, persisted counters, remote assets, browser
storage or background work. Catalogs retain exact key/placeholder parity at
**1,318** keys; the existing registry remains **57 POST routes / 93 definitions**.

#221–#226 remain completed bounded implementation slices. #208 and unresolved
findings stay open; UAT-01 remains failed; UAT-02–12 remain paused; B-09/B-07 remain
open and B-06 closed. Remaining knowledge-mode, declaration, Home, timezone and
Learning findings are not resolved here. Both `check` and
`v1-supported-platform-matrix` must pass on the exact merged commit before #227
closure. No whole-frontend pass or release readiness is claimed.
