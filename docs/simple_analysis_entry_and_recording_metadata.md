# Simple analysis entry and grouped recording metadata

## Scope and authority

Issue #324 implements approved G, H, I, K and corrected J: source URL, kind and
associated source metadata belong together. Starting branch is
`feat/324-simple-entry-forms`, starting HEAD
`c84a95e1f9d102dc63468c5cbddcde070e6843a8`, with a clean index and worktree.
The maintainer has accepted and closed #321/#322. Their Tournament/Cent evidence,
accepted Learning evidence and other earlier valid acceptances remain valid.
#208 remains open.

## Ordinary entry

Home presents three native task links in two ordered groups:

| Group | Task | Destination |
| --- | --- | --- |
| `record_games` | Record a 36-game Match | `/matches` |
| `record_games` | Record an individual game | `/sessions` |
| `analyze_and_review` | Analyze | `/review/recorded` |

Main navigation is Home, Match recording, individual recording, Analyze, Settings;
About remains in the footer. Analyze reuses the existing recorded Match/Session
chooser and its exact native `POST /review/open-recording` owner, freshness and
source checks. Alongside the lists it offers **Enter a situation yourself**
(`/analyze`), **Review a completed game manually** (`/review`), and secondary
**Learning** (`/learning`). Single-situation, manual Review and Learning pages
highlight the Analyze parent. Match review/report pages retain their existing
Analyze highlighting; recording pages retain their own recording-family parent.
`data-workflow`, language return paths, drafts, sources and Results keep their
existing identities and lifetimes.

Rendering Home/the chooser and changing language execute no analysis, prepare no
Learning and load no Learning archive preview. Recording activation remains an
explicit source-bound POST. Language may save the existing local language preference;
it writes no Product file. Route/form inventories and distribution-smoke chooser
expectations remain compatible; no new route or form owner is introduced.

## Match creation and shared defaults

The existing Match form owns every control exactly once:

1. Required editable Match title.
2. Initially closed **Optional details**, immediately below the title and before
   player setup: date-only display field, nested native exact-time editor, then
   one contiguous Source fieldset. URL and source-kind selection share a responsive
   row, followed by alternate title, channel, video start and end.
3. Existing platform, fixed-format summary and player setup/review controls.
4. Initially closed **Save as defaults**, containing the existing unchecked
   `save_players` and `save_platform` choices.
5. Initially closed Advanced Match details, containing external Match ID,
   platform-player IDs and the nested read-only technical format definition.
6. Existing reviewed-perspective and explicit Create actions.

The shared Session renderer groups only its existing `save_players` choice. There
is no new Session source/metadata contract or profile preference. Legacy
`advanced_settings_expanded` values remain lossless through unrelated Settings saves;
they do not control fresh disclosure layout.

Collapsed controls remain enabled successful form controls. Existing
`profile_generation`, `setup_context`, local-time bindings, full-form review and
one-use consent remain authoritative. Automatic source classification and blank
source-title fallback to Match title are unchanged; URLs are never fetched.
Channel/timecode visibility no longer depends on a manually selected video kind.
Date-only and exact timestamp meanings, minute-only input, timezone/DST resolution
and active metadata editing retain their existing implementation.

Validation retains safe values and opens every ancestor disclosure of an invalid
field. The creation adapter now associates existing video-timecode validation
failures with start/end controls, including malformed components, missing start
and reversed ranges; it reuses the existing parser and range constructor.
Enhanced language switching retains safe unsent values, deliberate checkbox
choices and disclosure state; validation-required visibility takes precedence.
Native JavaScript-free Update/error submission retains values for the subsequent
language switch and final Create. A native language form cannot transmit edits
never submitted from a different form; that existing no-script limitation remains.

## Missing Cent value

Only a won/lost result with absent or empty `game_value` receives
`validation.accounting.missing_game_value`, associated with the actual value field.
It requests the game value before loss doubling and explains automatic doubling
for a loss. Nonempty malformed/out-of-range values retain the generic invalid
message; passed/derived results do not acquire this requirement. Source/conflict
checks still precede result mutation. Existing fee calculation and exactly-once
loss doubling remain in the same owner.

## Local verification and remaining acceptance

Complete affected modules cover navigation contracts, Home/chooser and independent
entry paths, recording/settings navigation, shared creation, legacy preferences,
validation/language restoration, catalogs and Accounting web behavior. The moved
nested time editor justifies the complete local-time web module; existing shared
language preservation is exercised directly. The account-ID error disclosure is
also covered through own-player setup. The timecode field-diagnostic adjustment
adds the complete profile-driven Match creation module to the selection; the shared
timecode parser itself is unchanged. Arithmetic/store and large Learning-archive
suites are not affected. Direct distribution-smoke
Home/chooser consumers were inspected and retain their exact expectations.
The complete rename and CLI architecture guards run against final documentation.

Use development CPython 3.13, two file-grouped workers with disabled restarts,
external temporary outputs and 7,200,000 ms invocation timeouts. Run explicit
`scripts/check.ps1 -Mode Quick` after workers exit, then tracked/new-file whitespace
checks. Record actual commands, counts, failures/recovery and timings in the handoff.
Quick is partial validation, not distribution or complete-regression certification.

One compact checkout-only Chromium check uses a disposable synthetic home and
browser profile: DE/EN navigation, initially closed source/default groups, automatic
source visibility, native JavaScript-disabled submission, validation recovery,
checked-choice retention and enhanced unsent-value/disclosure language restoration.
It enters no complete game and runs no card analysis. This is developer evidence,
not installed acceptance.

The checkout-only Edge `157.0.4341.60` run completed with 12 captured observations
and seven genuine native POSTs. JavaScript-disabled DE/EN Home, chooser, manual
Review and single-situation navigation retained the correct parent. Source URL/kind
were adjacent at desktop width and stacked without horizontal overflow at 390 px;
all six source controls were enabled and visible with automatic selection. A
contradictory manual-kind/URL submission exposed the source error, retained both
save choices through native language return, and recovered through the unchanged
review action. Enhanced language return preserved an unsent source title, explicit
checkbox clearing and both open disclosures. No recording was activated or Product
file created, no known Player/platform default was saved, and guarded analysis,
Learning preparation and archive binding were never called. Screenshots and native
POST observations are in the external `opencode/324-browser-01` evidence directory;
the checkout-only driver is external `opencode/324-browser-check.py`.

Keep #324 open for automatic partial branch feedback, ChatGPT published-source
review, maintainer integration, automatic successful complete exact-commit main
`check` and `v1-supported-platform-matrix` gates, and one short later installed
acceptance of these entry/forms. No manual Check dispatch is required. Existing
accepted Tournament, Cent and Learning scenarios need no replay. #208 and release
acceptance remain separate.
