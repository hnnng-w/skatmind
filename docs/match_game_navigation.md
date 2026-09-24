# Match Game navigation and recording focus

Issue #238 puts the selected Game and its actual recording action before the
36-entry overview. It supersedes #220's progress → suggestion → full grid → task
ordering and normal **Position** numbering. Technical `match_position`, canonical
rotation, `/position/` routes, standalone presentation and analysis Position
terminology retain their meanings. This addresses the reported numbering,
selection-destination and recording-hierarchy observations; it does not reproduce
the original maintainer trace or constitute UAT acceptance.

## Accepted state, selection and destinations

Compact progress labels distinguish started Games, complete play traces and passed
deals. `#match-recording` is a labelled, focusable section containing **Game N of
36**, accepted recording coverage, and escaped full Forehand/Middlehand/Rearhand names from the
accepted selected position view. Existing Start/Pass, declaration or Card controls
follow. Compact captured totals, current Trick, accepted declaration, #234's
separately sourced unplayed pair and the full accepted/correction history retain
their existing evidence boundaries. Full history remains after the primary action.

The single native `#match-games` section follows recording. It contains all 36
tiles in twelve canonical rounds, retaining statuses, selected `aria-current`,
text markers and exact seats. Nearby overview/selected-Game links work without
JavaScript. Optional evidence, metadata including #232's fixed format, Statistics,
transfer, analysis and specialist correction remain accessible.

Issue #244 consolidates the selected Game's normal task: one Start/declaration/
named-next-Player heading leads to its existing controls, with short selection/Trick
context. The separate instruction paragraph and completed-step bookkeeping list
are removed; accepted declaration, evidence, warnings and history remain. Passed
and play-complete status use their actual existing projection; a missing declaration
or rejected Play is not completion. The normal review link is omitted at zero Plays,
offers truthful inspection at nonzero/zero-prepared coverage, and retains review at
prepared decisions. Direct empty/passed review and exact retained Report routes
remain supported. The existing Learning-transfer forms are in a secondary native
disclosure after recording/overview, opened for relevant feedback. The first-unfinished
rule, selected-Game-first ordering, all 36 tiles, rotation and Mark as passed remain.

The existing `view.next_position` is unchanged: first canonical entry whose view
is neither `passed_deal` nor `play_complete`. If it equals the selection, there is
no redundant continuation CTA. Otherwise **Open Game N for recording**, preceded by
**First Game with incomplete recording**,
can point backward. Passing or recording the final Card keeps the selected Game;
continuation is explicit. If there is no suggestion, the message states only that
all 36 entries are passed or contain complete traces. All-started/zero-Play input
still suggests Game 1 even though Product occupancy status is `complete`.

Tiles and continuation links use `/matches/position/N#match-recording`. Normal
creation returns to Game 1 with that fragment after exactly one create and no
Start mutation. `/matches/current`, old fragment-free URLs and existing bookmarks
remain supported. Selection is process-local: a fresh open retains the existing
Game-1 initial selection; same-active-context reuse retains selection. There is
no persisted resume pointer, scheduling rule, auto-advance or sequential lockout.

No route, query field, POST form, registry count or public version is added.
Existing lifecycle/Capture locking captures heading, seats, controls, summaries,
history and tokens from the same accepted source. Same-Game reads preserve the
selection generation, Report store and recovery expiry/token. Actual switching
retains existing recovery invalidation and exact-source Card/declaration rejection.
A Report's route still opens its actual Game, with same-Game recording backlinks.

Issue #254 names those existing review backlinks **Recording: Game N**, including
passed and completed Games. The ready-review invitation says **Decision selection:
Game N**; retained decision Report links say **Open existing analysis: Game N** with
their own available Trick/Card position. Their hrefs, fragments and readiness remain
exactly as above. Existing missing-evidence inspection, first-unfinished/overview
controls and explicit analysis POSTs retain their meanings. See the
[destination ownership map](home_and_recorded_review_navigation.md#destination-wording-issue-254).

Language return uses existing semantic source checks and safe input restoration.
The scoped Match branch now omits a normal fragment when retained validation
feedback exists: Chromium otherwise suppresses the existing error-summary
autofocus in favor of `#match-recording`. This was measured during verification.
Without feedback, valid recovery selection returns to `#match-recovery`; ordinary
recording returns to `#match-recording`. No new autofocus or JavaScript focus
handler is introduced. `match-play-N`, declaration, evidence, metadata and review
targets remain exact. Unsent other-form inputs survive language changes only with
the existing JavaScript enhancement; submitted safe input survives natively.

## Focused verification

### Saved progress presentation (Issue #260)

Starting clean `bug/260-match-progress-presentation` HEAD:
`6477188ee89034bb5d49f8f5b93086a1f73150d6`, the integrated #259 tree. The actual
#260 specification and #208's consolidated comment `5740775548` preserve the
historical UAT installation `483e51269d0206d29d9f73001dfadf8f0e7b2f32` as separate
evidence. The supplied post-#259 engineering reconciliation was confirmed at the
renderer seams: activity-sounding partial status, generic Card count, first-open
wording and the selected-Game round paragraph. The existing selected text and
`aria-current="page"` were already tile-local. Issue #260 implements R12a–c and
preserves R12d; it does not establish whole-R12 human acceptance.

`_recording_status` reads only the captured position's `game_state`, `play_count`
and `completed_trick_count`. For `play_in_progress`, integer Plays must be from
1 through 29 and completed Tricks must equal `play_count // 3`. The accepted
remainder is `play_count - 3 * completed_trick_count`, either zero, one or two.
The existing `game_result.COMPLETED_TRICK_COUNT` supplies the ten-Trick bound.
Malformed partial counts raise rather than clamp, round or fabricate completion.
There is no additional position replay, hand reconstruction, recovery, score or I/O.

| Existing accepted state/count | English caption meaning (paired German catalog) |
| --- | --- |
| `empty` | Not yet recorded |
| `setup` | Declaration needed |
| `ready_for_play`, zero Plays | Ready to record Cards; no Cards recorded yet |
| 1 / 2 Plays | Partially recorded: 0 of 10 Tricks; 1 Card / 2 Cards in Trick 1 |
| 3 Plays | Partially recorded: 1 of 10 Tricks |
| 4 Plays | Partially recorded: 1 of 10 Tricks; 1 Card in Trick 2 |
| 29 Plays | Partially recorded: 9 of 10 Tricks; 2 Cards in Trick 10 |
| `play_complete`, 30 Plays | Play record complete |
| `passed_deal` | Passed |

These are all six current Match position states. There is no shortened-terminal
state in this Match contract; Historical/Session terminal support is not changed.
Only the partial branch uses a denominator. Completion, next target and review
eligibility remain independent authoritative facts. A partial Game may have prepared
decisions, and thirty Plays do not guarantee every export or a settled score.

The same compact caption is used on the selected Game and its overview tile;
the separate generic tile Card count and redundant completed/passed task paragraph
are removed. The selected-Game round paragraph is removed. All twelve `h3` round
groups remain, at the same font size/contrast with normal weight, beneath the
overview `h2`. All 36 ordered native links, seats, exact hrefs/fragments and the
single tile-local textual selected marker retain their behavior. The actual
captured `next_position` supplies both the first-incomplete cue and link; selection
coincidence and no-target rules remain unchanged.

The navigation tests add literal bilingual coverage for the table, invalid scalar
counts, ordered groups, earlier targets and unchanged selection. Existing real
HTTP tests now record a first Trick, Pass Game 2, return, continue and strictly
reopen; rejected input leaves accepted progress unchanged. The existing final-Card
and rewind Preview/Cancel/Apply case checks 30 accepted Plays during the proposal,
then 29 only after Apply. Same-Game navigation/language retains exact Report bytes
and recovery identity; a real Game switch invalidates recovery but preserves a
still-current Report whose own source stays Game 1. Rendering Game 2 never borrows
that Report's progress. Strict reopen retains Workspace bytes, not process-local
Reports. No source/selection/readiness contract was changed.

Twenty-two new presentation cases failed before the repair. Focused corrected
runs passed **92**, then **198**, then **188** tests (overlapping selections,
not an additive suite count). See the
[independent installed comparison](unified_workflow_visual_contract.md#saved-match-progress-issue-260)
for the bounded browser matrix, native focus, operation accounting and hashes.
The prescribed final complete check is separately reported with its actual child
exit and retained log; these focused runs do not replace it.

Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependency floors including
tzdata>=2026.4, 67 POST routes, 112 forms and 98 scenarios remain. Three partial
captions increase the paired catalogs from 1,797 to 1,800 with sorted key and
placeholder parity. No workflow JavaScript, standalone Capture, consent, persistence
or public field changes follow. R01/R07/R11/R13/R15 residues and automatic Learning
questions remain separate. Both #259 CI jobs on the starting SHA subsequently
passed in [run 35977510861](https://github.com/hnnng-w/skatmind/actions/runs/35977510861);
this is baseline evidence, not #260 validation. #259 remains completed. Exact
merged-#260 `check` and `v1-supported-platform-matrix` must pass before manual closure.

### Historical Issue #238 evidence

Starting clean branch: `feature/238-match-game-navigation`, HEAD
`dd981819bf4a23577dd485ebd72b20a66435429d`. The bounded comparison with planning
archive `aecd151aafff1601b0366bb024e65a98006f4240` found unchanged Match projection,
first-unfinished rule and Workspace progress. Intervening renderer changes were
#232's format and #234's unplayed summary; lifecycle changes were #235 retirement
guards. Those changes, #236 integration and #237 Session request protection remain.

`tests/test_match_game_navigation.py` and `tests/test_match_game_navigation_web.py`
add 27 regressions over canonical views and real returned forms. They cover empty,
setup, declared, partial, passed, complete, earlier gaps, all passed, all complete,
all started, seats, escaping, one ordered overview, unique anchors, real creation,
one-save actions, zero-save navigation, strict reopen, stale forms, rejection and
language focus. A legal final-Card save keeps selection. A genuine executed Report,
exact download, no-op correction, preview/cancel, language restoration and actual
switch invalidation precede a real 30-to-29 rewind, changing the suggestion from
Game 2 to Game 1 and removing the complete-recording conclusion.

Completed compatibility runs: **221 passed in 540.52s**, **327 passed / 2 existing
skips in 279.41s**, and **150 passed in 13.37s**. These cover Match progression,
creation, #222/#223/#225/#226/#229/#232/#234–#237, language/security, standalone
Capture/Corpus, the Corpus observer/provenance boundary and CLI lazy-import/layer
guards. The skips are `test_actual_file_boundaries_fail_before_import[symlink]`
(`Actual symlink creation unavailable: 22`) and
`test_managed_direct_child_validation_rejects_escape_and_links`
(`This Windows account cannot create symbolic links.`). An earlier larger run
timed out and is not counted as successful. Final prescribed complete-check
stdout/stderr, actual child exit status and pytest totals accompany the implementation
report; focused passes do not replace that gate. The first complete attempt passed
all non-pytest stages, then reported 9,098 passed / 3 skipped / 1 failed: the catalog
inventory assertion still expected 1,545 rather than the four-key-expanded 1,549.
The expectation is corrected without changing catalog parity checks or production
code. A complete corrected-tree check is required; that attempt's child exit `1`
is not success. The focused catalog follow-up passed 22 tests and explicitly
reported the three existing skips: the two above plus
`test_recording_deletion_files.py::test_real_symlink_is_not_followed`
(`Actual symlink creation unavailable: 1314`). Installed production/resource bytes
are unchanged by this inventory correction, so the final browser evidence below
still covers the production tree.

## Independently installed browser evidence

`scripts/verify_match_game_navigation.py` reuses the dependency-free DevTools
harness with an independently installed Wheel, rejects checkout imports, and
compares 14 loaded module/resource hashes with the intended tree. Use an existing
local Edge executable and a fresh disposable output directory:

```powershell
& PATH_TO_INSTALLED_PYTHON scripts/verify_match_game_navigation.py `
    --browser PATH_TO_EDGE --output FRESH_SCRATCH_DIRECTORY `
    --wheel PATH_TO_WHEEL --phase after
```

`--phase before` verifies the actual starting-HEAD Wheel; it does not rewrite source
or switch branches. Synthetic evidence is under `$env:TEMP/opencode/`:

* `238-before-03/evidence.json`: 96 matched baseline measurements;
* `238-after-06/evidence.json`: final 176 measurements, `completed: true`, source
  hashes, actual request paths/counts, saves, focus, geometry, Report/source IDs
  and download hashes;
* matching PNGs, including `native-de-empty-390-1-True.png`,
  `native-de-declaration-390-1-True-controls.png`,
  `native-en-partial-320-2-True-controls.png`, `js-de-error-320-2-False.png`,
  `native-de-overview-focus.png` and `native-de-rewind-focus.png`;
* `238-browser-env/`: independent installed environment;
  `238-after-wheel-02/skatmind-0.17.0-py3-none-any.whl`: inspected Wheel.

Python **3.13.7**, SkatMind **0.17.0**, Microsoft Edge **153.0.4234.32**, de/en,
JavaScript on/off, 1365×900, 390×844, 320×800 and representative doubled text at
320×800 were used. Each computed font size is doubled once without changing
browser zoom or device scale. Native tile/overview/backward-continuation actions
were also exercised at desktop and narrow widths. Document/client widths agree at
**1350/1350**, **375/375**, **305/305**, including enlarged text. Screenshots include
separate control-area captures; required controls remain available and names wrap.

Matched German/no-script full-document top coordinates (CSS pixels, rounded):

| State / width | Heading before → after | Primary button before → after | Overview before → after |
| --- | --- | --- | --- |
| Empty / 1365 | 5602 → 533 | 5691 → 777 | 790 → 984 |
| Declaration / 1365 | 5602 → 533 | 6161 → 1247 | 790 → 1528 |
| Partial / 1365 | 5602 → 533 | 6524 → 1611 | 790 → 2452 |
| Empty / 390 | 13501 → 555 | 13694 → 989 | 777 → 1313 |
| Declaration / 390 | 13501 → 555 | 14396 → 1691 | 777 → 2160 |
| Partial / 390 | 13501 → 555 | 14879 → 2174 | 777 → 4311 |
| Empty / 320 | 14512 → 660 | 14757 → 1144 | 857 → 1493 |
| Declaration / 320 | 14512 → 660 | 15547 → 1934 | 857 → 2477 |
| Partial / 320 | 14512 → 660 | 16317 → 2704 | 857 → 5019 |

Direct fragment entry keeps those document coordinates and focuses the recording
section; its heading is about **45.5 px** from the viewport top on desktop and
**33.2/33.4 px** at 390/320. The old target showed an unnamed generic task heading;
the new one includes the selected Game. At 320/200% the partial primary button is
**8389.5 px**, before the overview at **15783.2 px**. Long names, full history and
enlarged guidance still require vertical scrolling: no one-screen or reduced-total-
height claim is made.

Each of four final browser flows has **37 native actions, 18 POSTs, 9 actual Match
saves and one explicitly requested analysis**. Eight saves are native create,
Start, declaration, two Cards, Pass, final Card and rewind. One separately labelled
fixture POST/save supplies 27 legal surrounding Plays through the returned
specialist form. Navigation, language, rejection, Report view/download and preview
save nothing. Same-source Report/download and preview/token identity survive
overview, same-Game tile and language navigation. Native error language return
focuses the error summary; preview language return focuses `match-recovery`; Apply
returns to the named recording region. Focus has a visible 3-pixel blue outline.
Earlier unsuccessful probe directories remain diagnostic evidence, not passes.

```text
Wheel        78d272ef7a7875925fdb4cd8ef772de3e5439ac659c33e199beed4e00e50a478
app.css      deec38856f8cc22f7ec5b46a15629422f486830b616be99a1ef559413757c627
workflow.js  f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298
Match render fcc754995a1037f2b8fbe86c2374c75d79608cda098596b7ae25e332e65eb46d
Language     13a66f4a0bbe1629591bc5d4e0b57392c62e688070756c4dd244287314e4352a
```

Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependencies including tzdata>=2026.4,
#230 profile shape, public/Product formats, registry counts and 98 generated
outputs are unchanged. No real recordings or UAT files are used. Both exact-merged-
commit `check` and `v1-supported-platform-matrix` remain manual closure gates.
#237 remains completed; #208/unresolved findings stay open, UAT-01 failed,
UAT-02–12 paused, B-09/B-07 open and B-06 closed. No whole-UAT or release-readiness
claim is made.
