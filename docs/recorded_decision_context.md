# Recorded decision context

Issue #241 implements only the visible pre-Card situation slice of R11 in #208's
consolidated retest. Saved Session decision Results and executed one-Decision Match
Reports show **Situation before this Card** in normal content, before assessment.
The German text lives in the unified frontend catalog. #240 remains completed;
R11's remaining method/navigation/download/layout findings and #208 remain open.

## Private field and source ownership

`app_web/recorded_decision_context.py` projects a small frozen value containing only
display labels/fallback ordinals, Game/Trick/Card numbering, Game type, named
Declarer, ordered current-Trick Cards/Players, next Player, the full analyzed hand,
and retained known party points. It retains no Request, Report, stable Player ID,
path, profile, Checkpoint or execution object. Its renderer is read-only HTML.

| Field | Authority |
| --- | --- |
| Hand and ordered Trick prefix | Retained Position Result `position.hand` and `position.current_trick` |
| Contract and turn | Result `position.game_type`, `declarer_player`, `trick_leader`, `next_player` |
| Known points | Result `score_summary.total_declarer_points` / `total_defender_points` |
| Session identity | Matching `RecordedReviewSourceV1.document` and selected Checkpoint's stored Trick/play/actor metadata and `relative_player_map` |
| Match identity | Selected typed `MatchAnalysisReportV1` Game/position/one-based decision index and executed `profile_binding` acting/left/right stable IDs |
| Names | Only Players in the matching accepted source; existing localized source-roster ordinal fallback for an unlabelled Player |

`recorded_decision_context_sources.py` contains the two narrow adapters. Session
capture happens inside the existing Session rendering lock. Match capture happens
in `build_task_first_match_page_state_v1` inside its existing locked page snapshot.
The Match adapter uses the Report's own Game, even if another Game has the same
integer decision index. Profile binding supplies identities even without eligible
or actionable opponent profiles. An absent/mismatched source cannot borrow names
from the selected Game, global own-player preference, filename or `input_file`.

`turn_phase.derive_next_player` maps each prefix offset from the stored leader
using **me → left → right**. Initial Forehand/Middlehand/Rearhand is separate from
Card position in the current Trick. Session indexes remain stored values; Match
Trick/Card numbers come from the Report's canonical one-based decision index.

The adapters neither consult Request fields for normalized Position facts nor read
today's remaining hand. They perform no replay, scoring, legal-Card calculation,
Checkpoint collection, preparation, Historical materialization or execution.
Existing source freshness, report-store publication, invalidation and retirement
remain authoritative; no new lifecycle gate or filesystem work is introduced.

## Normal presentation and minimization

Session passes a strictly optional private context to the existing shared Result
renderer. It appears inside **Summary**, before Recommendation. Equivalent raw
Contract/Next Player/Current Trick details are replaced in normal content; their
existing technical disclosure remains. #239's two score rows are reused once.
The canonical top-level section order, anchors and #240's CJ/SJ equal-best
assessment remain intact. Callers without recorded metadata retain their output.

Match places the same component after source identification and before the
existing actual/recommended Card comparison. Its score is the Report's known
decision-time score, independently of the separate current-recording progress.
Standalone Capture state JSON and rendering are unchanged. The unified component
is not a whole Report/Result serialized into browser script state.

Cards use the app-owned read-only symbol primitive with full localized accessible
names. Its optional `show_code=False` applies only here; existing callers keep
their defaults. Issue #248 displays a **copy** of the complete normalized hand in
C/S/H/D, J/A/10/K/Q/9/8/7 order, including the actual played Card. The normalized
Result hand itself retains its exact original order. Shared Heart/Diamond glyphs
and ranks are red, with system-color override in forced colors. The prefix remains
chronological and contains neither the
actual Card nor the following Player's later Card. An empty Trick gets one short
sentence. Missing/malformed display facts are unavailable, not fabricated empty
hands, zero scores or identities; valid siblings remain visible. These are defensive
presentation checks, not a second Product validator or wider input acceptance.

Only the already analyzed acting hand is newly allowlisted in normal HTML. Opponent
hands, public hands, Skat/discards, hidden worlds/ownership, private IDs, profiles,
complete Requests and execution internals are excluded from this compact slice.
Full names are escaped and wrap; `.recorded-decision-context` owns the added CSS.
There are no controls, disclosures, new tables, routes, forms, preferences or saved
context. An executed Search Result without a recommendation can still show its
Position; an unavailable execution without a retained Position cannot.

No fresh producer output changes are authorized or implemented. Requests, Results,
Reports, saved recordings, Checkpoints, profile shape and downloads remain exact.
Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependency floors including
`tzdata>=2026.4`, public/persistence schemas and 98 generated scenarios remain.

## Focused verification

Pre-fix genuine HTTP regressions demonstrated the missing normal component.
`tests/test_recorded_decision_context.py` covers zero/one/two Cards, all relative
leader rotations, source identity, complete/escaped/unlabelled names, immutable
minimization and independent defensive absence. The real Match web fixture records
B CK / C C7 / A C10 with C's ten supplied Cards, analyzes decision 2 through its
returned form, and checks B CK, C next, all ten Cards including C7 and 0/0. C10 is
excluded specifically from the context. Another Game/Report with decision index 2
cannot rebind it; passive navigation and downloads preserve exact Report/source
bytes and make no additional execution or Product-save calls.

The existing #239/#240 legal Session HTTP sequence now also asserts B HJ / C DJ,
A next, C10/CJ/SA/SJ/HA/DK/D7 and 14/29 after later Plays, normal completion and
strict reopen. It preserves supplemental 0/0, final-recording separation, CJ/SJ's
6.00 equal-best view and exact downloads. Existing source-edit, out-of-order and
current-position publication tests assert context invalidation/attribution too.

### Installed browser evidence

An independent Wheel was installed into a separate environment with Python 3.13.7,
Package 0.17.0 and tzdata 2026.4. The existing dependency-free DevTools transport
drove headless Edge 153.0.4234.32. Disposable returned-form setup was followed by
native review, language/source controls, native downloads, another Match Game/Report
and return, and strict Session reopen followed by another native review.

The retained Results were reused across de/en, JavaScript on/off, 1365/390/320
pixels and representative German 320-pixel 200% text. Scoped geometry and inspected
viewport screenshots show complete wrapped names, named prefixes, full hands and
the appropriate score. Ordinary text remains 16px before enlargement. Per family,
the initial review made one execution; passive views/language/downloads made zero
additional executions and zero Product saves. The separate second-Game Match review
and reopened Session review each made exactly one further explicit execution.

Evidence, installed module/resource hashes, requests, exact-byte hashes and
screenshots are outside Git at `$env:TEMP/opencode/241-browser-03/`. The independent
Wheel SHA-256 is
`a5098e8cfa7fdf661c0acb52744a8f2a0c24334c9d5b91baf9d11bfff2057b2b`.
`241-browser-01` exposed offset offscreen-clip screenshots in the verification
harness; `241-browser-02` replaced them with ordinary viewport captures, and `03`
adds explicit score views. No product edit was needed for that capture correction.

`241-producer-baseline.json` and `241-producer-current.json` separately verify fresh
exact Root Result bytes for both `241-browser-02` Requests with their original
execution options. The baseline installation's relevant producer modules were
checked against actual starting HEAD `99d636548b48a6a8df0670ac3ab3df74fb69099b`.

Long names and enlarged German text require vertical scrolling. The existing #240
candidate-table clipping and general focus/download hierarchy remain separate;
these checks are not a whole-page accessibility or whole-R11 pass. No maintainer
UAT is claimed. Both `check` and `v1-supported-platform-matrix` remain required on
the exact merged commit before manual closure. UAT-01 remains unaccepted, UAT-02–12
paused, B-09/B-07 open and B-06 closed; no release-readiness claim follows.

Issue #248's [independent installed comparison](compact_card_entry.md#issue-248-current-installed-evidence)
reuses the real saved SJ execution and the unchanged #246/#247 fixture. Only the
seven-Card hand's visual order changes to CJ/C10/SJ/SA/HA/DK/D7. Its serialized
C10/CJ/SA/SJ/HA/DK/D7, HJ/DJ prefix, 14/29, CJ/SJ candidates and exact Request/Result
download bytes remain unchanged. Earlier #241 measurements above remain historical.
