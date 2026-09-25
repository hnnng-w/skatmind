# Settings and explicit Player seat setup

Issue #225 implements a private Settings-to-recording path. It revises the earlier
Issue-#219 About placement, alias/account-list editor, preferred-perspective UI,
and default-saving choices. Earlier release and browser evidence remains historical.

Issue #230 subsequently adds an independent native Time zone form at
`POST /actions/profile/time-zone`. Unset uses Europe/Berlin for new exact-time
input; explicit save/clear changes only the optional `interface_preferences.time_zone`
field through existing CAS. This deliberately extends the private shape and adds
`tzdata>=2026.4`; older readers may reject the extension. Recommended-default reset
preserves the zone, full reset clears it, and no GET or unrelated edit changes it.
Current counts are 59 POST routes/103 forms. Existing roster/seat/account semantics
below remain. See [Local time entry](local_time_entry.md) for compatibility and evidence.

## Normal flow

1. Open **Settings** from the shared navigation. Viewing it creates no profile.
2. Use **Add player** to enter a name and, optionally, one complete account
   platform/ID pair. Only the selected Add/Edit view expands.
3. Choose **Your player**, or explicitly leave it unset.
4. Open Session or Match creation through Home or the shared navigation. Own perspective supplies that identity, with
   **no seat selected**. For a Match, the seat explicitly means **game 1**.
5. Select a seat and fill the other two seats in saved-Player or new-name mode,
   then use **Update setup and review roster** once. Issue #242 shows the free
   own seat immediately as the derived own Player, with an Update-to-review note.
   No own-only preparatory submission is required. Both modes work with JavaScript
   disabled; app-owned CSS follows the native select state.
6. Review the named roster and perspective, then Create. Changing the form after
   review requires another setup update. Setup-only requests create no Product,
   generate no Product/Player IDs, and save no preferences.

Other-perspective/manual setup remains available. Without an own preference it is
the initial mode. Issue #233's [knowledge-based Session choice](session_knowledge_based_entry.md)
uses Player-perspective recording (`live`) during or after a Game, requiring the
known hand's explicitly seated local Player. Complete-deal reconstruction
(`retrospective`) may have no local Player, but always requires all three initial
hands and original Skat before normal declaration. Switching the radio never clears
own identity or assigns a seat; changed setup requires re-review. Recording afterward
grants no additional hidden-card knowledge beyond the existing capture-mode contracts.

## Private routes and forms

`GET /settings` is the eighth **shell page**, not an eighth Root workflow. About
retains Product/version/license/privacy/installation information and the shared
Settings navigation entry. Profile mutation forms are rendered only on Settings; the global language
form remains on every page.

Issue #265 removes the normal in-content Create Game/Create Match paragraph between
Time zone and Recommended defaults, and About's extra generic Settings paragraph.
The actual creation routes, global navigation, footer About, contextual invalid-profile
Settings remedy and all semantic returns remain. At #265, Settings rendered Players,
Creation defaults, Time zone, Recommended-default reset, local-profile information,
then full-profile reset. Issue #266 moves both resets after profile information into
one lower Reset section, with recommended defaults first. Both reset consents remain initially
unchecked and required; Player/account previews, warnings, field associations,
repeated-form identities and capture-disclosure preference/default remain unchanged.
The bounded R01f presentation is implemented by #266; R01g disclosure preferences
remain separate open work.

About's existing secondary section is now **Development and automation**, with one
short explanation that CLI/Python-API script/tool access is optional for ordinary
browser use. Its four literal documentation filenames remain non-clickable and in
their original order; its storage disclosure is separate. See the
[exact caller/target map](home_and_recorded_review_navigation.md#recording-entry-and-settingsabout-navigation-issue-265).

Existing profile action routes remain:

```text
POST /actions/profile/language
POST /actions/profile/reset
POST /actions/profile/players/add
POST /actions/profile/players/update
POST /actions/profile/players/remove
POST /actions/profile/preferences
POST /actions/profile/recommended-defaults/reset
POST /actions/profile/managed-label
```

The five additional private presentation/confirmation routes are:

```text
POST /actions/profile/players/edit
POST /actions/profile/players/remove-preview
POST /actions/profile/players/accounts-preview
POST /actions/profile/players/accounts-replace
POST /actions/profile/players/cancel
```

Creation retains `POST /sessions/create` and `POST /matches/api/v1/create`.
Their private submitter is `setup_action=update` or `setup_action=create`.
Browser fields are explicitly `forehand_*`, `middlehand_*`, and `rearhand_*`,
with `_mode`, `_handle`, `_name`, and Match-only `_platform_id` suffixes.
`perspective_mode`, `own_seat`, and the server-bound own identity replace implicit
row defaults. Old numbered creation payloads receive contextual rejection.
Standalone Capture's numbered **table-place** fields retain their original meaning.

The registry now has **54 POST routes and 87 exact form definitions**. Safe return
paths add only `/settings`; queries, fragments, action routes, downloads, external
URLs, protocol-relative URLs, and unknown paths remain disallowed. Profile actions
use Settings as their semantic origin and return there on successful `303` and
contextual `400`/`409` responses. Reset of an invalid profile remains explicit.

## Identity and lossless legacy metadata

The simplified UI is an adapter over unchanged full-value profile operations.
It does not change profile version, fields, canonical order, fingerprints, ID
generation, persistence bytes, or compatible low-level contracts.

* New entries have empty aliases and zero or one account pair. Internal generated
  identity is distinct from optional account metadata and is never editable.
* A name-only **keep account data** edit preserves every alias and account tuple
  exactly. Loading Settings performs no migration or cleanup.
* A single account may be explicitly edited or cleared. Clearing requires the
  explicit edit choice with both account fields empty.
* Multiple legacy accounts remain stored. The editor shows their count without
  selecting the first account. A separate replacement preview displays the complete
  removed set and the proposed zero/one replacement pair. Confirmation is required.
* Aliases have no normal editor and are preserved even across explicit account
  replacement. Existing valid 16-alias/16-account values remain loadable.
* Duplicate normalized display names require explicit disambiguation. There is no
  name/account merge, external lookup, or automatic account transfer into Match
  evidence. Only explicitly submitted Match account metadata enters that Product.

The hidden `preferred_perspective_player_id` remains compatible and is preserved
on own-Player/unrelated edits. It is neither synchronized with own identity nor
used to populate new ordinary seat forms.

## Deliberate confirmation lifecycle

Remove first selects one named Player and displays actual preference-reference
effects. It states that recordings, participants and evidence are unchanged.
The no-JavaScript confirmation is a server-rendered Settings view with a fresh
unchecked native confirmation control; there is no permanent per-row checkbox.

One process-local editor retains the exact target, profile generation, original
Player value, optional replacement tuple, a keyed opaque selection and creation
time. Confirmation expires after 30 minutes and is single-use. Consuming it
precedes the existing CAS operation; conflict/failure does not retry. Cancel is
also bound to the exact editor selection. Foreign, stale, expired and repeated
confirmations cannot act on another or re-added Player.

Language changes execute no Player mutation and never preserve a checked
confirmation. A changed profile generation makes the old preview ineligible;
Settings explains that a fresh preview must be requested after cancellation.
Aliases/accounts and recordings are untouched by cancellation or navigation.

## Seat projection and Match translation

At most one bounded setup presentation is retained per creation family, with a
30-minute lifetime. It records safe fields, exact profile setup values, the one
automatically placed own seat, and whether the roster was reviewed. Opaque setup
bindings and fresh profile generations are transport values, not persisted state.
Language saves preserve applicable setup presentation using the #223 exact-source
and form-manifest checks, including the absent-to-language-only-profile case.

Changing own seat moves only the server-retained automatic Player bundle. Issue
#242 supersedes #225's blank-only destination rule with one exact-self exception:
saved mode, the current validated own handle, and a blank new-name field qualify
for adoption on **Update**. Selecting saved A again at own Rearhand therefore
produces the same reviewed roster as the former empty-placeholder workaround.
The adopted row becomes the server-retained automatic bundle, and repeated unchanged
Update is idempotent. Other handles, same-name new entries, mixed modes and an
independent duplicate own row remain rejected. Original inputs survive rejection.

The automatic source identity is validated before movement. Explicit account
values use the existing trimming/validation boundary: neither supplied stays empty;
one supplied value is retained; equal source/target values are retained once; two
distinct nonempty values are rejected with both controls preserved. This exception
requires the same saved own identity. Account-only occupancy remains a conflict,
and saved profile accounts are never imported implicitly. Other independent
destination input still produces field-linked feedback, without overwrite or swap.

All three named seats remain visible. The own row uses a complete escaped read-only
label; the other two use their normal controls. The former duplicate full roster
summary is removed. A changed reviewed seat/mode displays a pending automatic-source
release rather than another independent own participant. Existing source release
semantics remain: Update releases that bundle before the old seat can be refilled.
The last reviewed perspective is labelled as such. Conflicting entered identities,
mixed saved/new values, accounts and field errors remain editable and reachable.
Native CSS uses current control state, including #223 restored safe input, rather
than an old accepted-value attribute. Controls are neither duplicated, cleared nor
disabled for presentation; their successful values remain subject to server checks.
Selecting a seat or mode performs no POST. The existing optional language script
is unchanged, and language saving performs no setup Update or Create.

Final input must match the reviewed setup and current own identity. Final submission
consumes the setup selection once. Exact Product metadata is validated before ID
generation, followed by Product-first creation and at most one profile enrichment.
Changed final-Create values are not projected back into an old review. Setup token,
nonrenewed expiry, profile generation, family isolation and one-use failure behavior
remain authoritative. Settings own A can coexist with manual B/C/A and perspective C;
neither own nor hidden preferred perspective is changed by that choice.

Session seats map directly. The new Match adapter translates complete bundles:

| Confirmed game-1 seat | Existing initializer table place |
| --- | --- |
| Forehand A | `place_2 = A` |
| Middlehand B | `place_3 = B` |
| Rearhand C | `place_1 = C` |

The stable ID, label and explicitly supplied account value travel together.
Perspective is selected by identity before reordering. Preparation checks the
definition through the authoritative rotation, and genuine persistence/start/reopen
tests check the resulting Workspace and observed first Game. Games 2–36 use the
unchanged rotation. Existing/imported Workspace bytes are never rotated or repaired.

## Explicit saving and reset scope

**Save new players** is a native initially unchecked checkbox. Omission means
false. One-off participants still receive stable IDs in the saved recording.
Saved-Player reuse adds no duplicate directory entries. Managed display labels
retain the existing creation enrichment boundary.

Session creation saves no perspective default. Match's separate unchecked **Save
this platform as my default** changes only that platform preference. It saves no
seat, own identity, perspective, or analysis parameters. With no saved platform,
the ordinary Match form starts at the explicit **Unknown** choice.

Issue #232 supersedes the earlier #219 normal brand-specific format label. Match
creation and its setup/error rerenders now state **Recording format (fixed):
36 games · 3 fixed players**, with catalog-backed German/English wording. These
are 36 positions including passed deals, with the same participants. Platform
describes where play occurred; Source URL/kind describes the observation; the
canonical format controls the fixed structure. Other Match formats are unsupported.
All five native platform choices use that same scope immediately, without a request
or script. Choosing one alone saves nothing and retains roster, time and source.
Only the existing explicit save-platform choice changes the preferred platform.

The existing Advanced Match details disclosure contains optional read-only
**Technical details** with the canonical `euroskat_36_standard_v1` / `EuroSkat` /
`36er Standard` / 3 Players / 36 Games identity. No format field is submitted.
Active metadata correction uses the same scope and independent source guidance;
its accepted values, rejected input, revision/CAS and Report lifecycle remain
distinct. The template, account ownership, game-1 mapping and Games 2–36 rotation
are unchanged. Historical #219/#225 evidence below remains historical.

The Advanced creation-details checkbox retains its stored meaning: optional Match
details start expanded. It does not make those details mandatory. Recommended
reset still clears platform, legacy preferred perspective and Advanced expansion;
it retains own Player, directory, language, timezone and labels. Complete profile
reset clears the profile, including labels, but changes no Product document or artifact.

Recommended-default no-ops write nothing. Full-profile reset publishes a fresh
revision even when its user fields already have default values. A profile conflict,
capacity limit or storage failure after
successful Product creation retains the valid Product and reports unsaved enrichment.
There is no retry, merge, automatic reload, deletion rollback or analysis side effect.

### Grouped reset presentation (Issue #266)

Normal Settings now ends with one visible **Reset** section after Players, Creation
defaults, Time zone and local-profile information, before the footer. **Restore
recommended defaults** comes first; **Reset entire local profile** comes second.
Each retains its own form, initially unchecked required consent and distinct action.
The full reset keeps its destructive border/button. Existing headings, grid spacing
and panel styles suffice; there is no additional disclosure or stylesheet change.

The verified current operations, rather than the older #219 inventory, determine
the copy:

| Profile field or lifecycle | Recommended defaults | Entire local profile |
| --- | --- | --- |
| Saved language | Preserved | Cleared to null; the next response resolves usable browser language, then English fallback |
| Known Players, names, aliases and account IDs | Preserved exactly | Directory cleared |
| Own Player | Preserved | Cleared |
| Compatible preferred perspective | Cleared | Cleared |
| Preferred platform | Cleared | Cleared |
| Advanced Match-detail expansion | False | False |
| Explicit timezone | Preserved | Cleared; future unset-zone input uses Europe/Berlin |
| Workflow preferences | Preserved; both supported analysis fields are null | Both remain null; no new analysis defaults |
| Managed display labels, including Match date-only labels | Preserved | Cleared; later discovery may display fallback names/dates |
| Revision, fingerprint, process generation | A changed operation increments revision/generation once and rebuilds the fingerprint; an absent/already-reset profile returns unchanged without saving | Canonical replacement increments valid revision/generation once, even at default values; absent/invalid recovery writes revision zero |
| Pending Settings and creation presentation | Existing generation-bound confirmations become stale on a saved reset; changed setup-key values invalidate pending creation setup on next use | Same rules, with broader profile changes; old source-bound language overlays cannot restore cleared references |
| Active Product state and retained outputs | No direct reset of active Session/Match/Corpus, independent manual Review draft, or retained Request/Result bytes | Same non-cascading operation boundary; this does not promise preservation of every unsent browser edit or pending setup |

Private recording labels are separate from Session/Match files, independent Corpus
Catalog/Snapshot copies and exported files. Clearing those labels neither deletes
recordings nor regenerates profile labels from them. No backup or Undo is introduced.
Future explicit work can use changed defaults; retained Requests are not recalculated.

The transport remains exactly:

* `POST /actions/profile/recommended-defaults/reset`: `profile_generation` and
  `confirm_recommended_reset=on`; absent/valid profiles only.
* `POST /actions/profile/reset`: `profile_generation`, `return_to=/settings` and
  `confirm_reset=on`; also the existing invalid-profile recovery.
* Both retain optional `_frontend_form_instance`, the **1,052,672-byte** body limit,
  strict form parsing, current-generation checks and authenticated same-origin POST.
  No recording-deletion token or lifetime is added. Ordinary Save remains independent,
  including native implicit Enter.
* Success/unchanged returns `303 /settings`; malformed/missing consent returns `400`,
  stale generation or external CAS conflict `409`, and storage failure keeps its
  existing `500` response. External profile conflict requires restart, not GET repair.
* Canonical persistence retains the two observations, fingerprint/invalid-digest CAS,
  same-directory temporary write and atomic replacement. Full reset is not generally
  file unlink. Invalid-profile warnings remain above recovery; ordinary Settings and
  recommended reset are unavailable in that state.

The reset forms have no safe editable language-manifest values. Consent and hidden
authority are excluded; independent forms retain their instrumentation identities.
Successful redirects clear only their existing feedback family (`local_settings`
for recommended defaults, `profile` for full reset). Viewing Settings and resetting
do not consume another workflow's pending #245 acknowledgement or create a reset
receipt. See [bounded installed evidence](unified_workflow_visual_contract.md#grouped-settings-resets-issue-266).

## Verification and visual evidence

Focused tests cover returned-form Settings → own identity → explicit seat → Session
and Match creation/start/reopen for every own seat, one-off/manual/no-local setup,
duplicate correction after language switching, collisions, stale identities,
legacy metadata, confirmations, no-op bytes and existing Product-first failure
handling. Eighteen genuine persisted Match cases cover all six roster permutations
and three perspective seats, checking all 36 rotations and account ownership.
The #221–#224 review, recovery, language, visual, security and resource regressions
remain part of verification. Public seven-workflow and persistence tests are intact.

The optional `scripts/verify_settings_seat_setup.py` reuses #224's dependency-free
DevTools harness and already installed Microsoft Edge **152.0.4191.66**. A separate
Wheel installation is required with `--expect-installed`; loaded catalog/CSS/script
resources must equal checkout bytes. No runtime/browser dependency was added.

Recorded viewports are **1365×900**, **390×844**, **320×800**, with German/English,
JavaScript enabled/disabled, and **200% text** at 320 pixels. The native Enter/Space
flows genuinely add Players, choose own Rearhand, resolve an occupied-seat error,
create a Session and Match, start and reopen game 1, cancel/confirm removal and
verify unchanged recording bytes. The actual first Game is **Forehand Boris,
Middlehand Clara, Rearhand Alexandra-Maria**, with Alexandra-Maria as perspective.
The optional enhancement also retains an unsent safe creation name on language save.

Local synthetic evidence lives outside Product/user data:

```text
<temporary-directory>/opencode/settings-225-baseline/
<temporary-directory>/opencode/settings-225-installed-verified/
```

The baseline uses the retained #224 installed Wheel. Its resource hashes and source
baseline `fca43d777998218b6bd438c947ab64bb4cda0ba1` are recorded. Final evidence uses
that HEAD plus changed-resource hashes, since the agent creates no commit.
`evidence.json`, `summary.json`, roster/first-game/collision/removal screenshots,
and de/en viewport/text-scale screenshots record actual operations and geometry.
The final installed run also verifies source-module byte parity for the setup,
creation and Settings adapters and records the actual local resource URLs. Error
summaries receive focus, and native action controls retain a visible outline.
The final run has **48 measurements** with document/client width equality,
including 200% text. At German 390 pixels the former About Player area overflowed
to **1109 px**; Settings is **375/375 px**, with one Player editor instead of four
simultaneously present name editors. Settings with one editor is **3241 px** tall
versus the older About page's **4682 px**; those are different page compositions,
not a claim that the same unchanged component became shorter. An initial browser
run also found 200%-text overflow in Session landing labels; scoped shrinkable
managed-landing controls and Session word wrapping correct it.

These are implementation checks, not maintainer UAT or whole-frontend accessibility
certification. Other browser engines and assistive technologies were not exercised.
Exact merged-commit `check` and `v1-supported-platform-matrix` must be green before
#225 closure. #208 and unresolved findings remain open; UAT-01 remains failed,
UAT-02–12 paused, B-09/B-07 open, B-06 closed. #221–#224 remain completed bounded
implementation slices. Package **0.17.0**, Python **>=3.13**, dependencies, license,
public APIs, Schemas, generated outputs and Release state remain unchanged.

## Issue #232 fixed recording scope evidence

Starting clean branch: `feature/232-match-format-presentation`, HEAD
`5c073862c3e3b8d5cbd79921fe50e62a8a0b34ad`. GitHub confirmed Issue #232. The four
specified creation/format source files had no differences against archive
`aecd151aafff1601b0366bb024e65a98006f4240`; #231's shared changes were retained.
#231 remains a completed prerequisite.

The optional `scripts/verify_match_format_presentation.py` reuses the existing
dependency-free DevTools transport with independently installed Wheels. It rejects
checkout imports and checks 16 installed modules/resources byte-for-byte against
the starting commit (baseline) or current source (final). It uses real returned
forms and native keyboard select/Enter/Space/text entry, not injected Workspaces
or repaired hidden bindings. Local evidence is under:

```text
<temporary-directory>/opencode/match-232-before/evidence.json
<temporary-directory>/opencode/match-232-after-final/evidence.json
```

Both have `completed: true`. Baseline: **16 measurements**. Final: **80 measurements
and 112 PNGs**, Microsoft Edge **153.0.4234.32**, Windows, CPython **3.13.7**, Package
**0.17.0**. Both locales and JavaScript modes cover **1365×900**, **390×844**,
**320×800**, plus **200% text at 320 pixels**. Text enlargement doubles computed
font sizes once; browser zoom/device scale remain 100%/1. Every final measured
document/client width agrees: **1350/1350**, **375/375**, or **305/305** pixels.
Existing app-owned wrapping/focus styles suffice; no stylesheet change is needed.

The baseline normal line remained brand-specific after all five native platform
changes. The final line remains neutral after the same changes. Initial, setup,
validation-error, Technical details and active metadata screenshots were inspected,
including enlarged German text and literal escaped custom characters. A transient
blank capture after rapid reflow was corrected in the probe with a paint wait;
the final enlarged-text PNGs show the actual text. Representative filenames:

* `js-de-initial-1365-1.png` (also available in the baseline directory);
* `js-de-setup-1365-1-platform.png`;
* `native-en-initial-320-1-platform.png`;
* `native-de-initial-320-2.png`;
* `js-en-technical-320-2.png`;
* `native-en-error-390-1.png`;
* `js-en-metadata-1365-1.png` and `native-de-metadata-320-2.png`.

All four final native flows change every platform choice, enter a custom value,
reject empty custom text and duplicate Players, switch languages, correct and review
setup, create a non-EuroSkat Match, and strictly reopen it. The explicit platform
checkbox is checked in the German flow and omitted in the English flow, retaining
the existing default. The stored custom value is `Club <18> & "Zocker"`; it remains
descriptive. Source remains the supplied YouTube observation; local time remains
`2026-09-03T19:30:00+02:00`. Each Workspace has 36 Slots and game-1 Forehand Anna,
Middlehand Peter, Rearhand Mira, with Peter as perspective. Setup/errors write no
Product; explicit creation performs exactly one Product replacement. GET, platform
selection, disclosure opening and language changes perform no Product write or
analysis. Unsent browser-only values survive language switching only with #223's
optional JavaScript; already submitted safe errors/values survive both modes.

Final installed resource SHA-256 values (full module inventory is in `evidence.json`):

| Resource relative to `app_web` | SHA-256 |
| --- | --- |
| `assets/app.css` | `3b8257ebb8b9fa8f4587772c41bb5d749970a18da42e617349326e9f1377459c` |
| `assets/workflow.js` | `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298` |
| `locales/en.json` | `a2e3c33549d4eeae79bc7614b049ae5b1f3e8eac319845ce3afc0e3efdcbc77a` |
| `locales/de.json` | `3ba99b8c1904f3cde6def01c35684408f0b77eb2005bac3dad1ec6ad88b8deb3` |
| `friendly_creation_rendering.py` | `34d1beb4c8647bbb04c31ef799f09707f06f2d68e5aa137ba87b18a2cf3f34e5` |
| `task_first_match_rendering.py` | `a2e474c4a57782443e67ca1b6e8e2c82a0b223ab19b0e36864b2a0234f24d8e7` |

The final Wheel SHA-256 is
`8e9aacfcb17cab072f054ba2ffc4e2bc688fbc2e34ba66cbe04a43b2c8077932`.
Loaded HTTP resources are `/assets/app.css` and `/matches/assets/capture.js`;
authenticated bytes match their installed resources and current source. Catalogs
are Package resources used server-side, not new browser downloads.

The 488-test focused run covers creation/metadata, canonical contracts, locale,
validation/security, packaging, standalone Capture, and #225/#229–#231 regressions.
The 35-case new suite also checks real EuroSkat/custom HTTP creation in both languages,
all 36 rotations, and a platform-only metadata revision preserving a three-Play
prefix and invalidating a real Decision Report, with no-op/stale protection.
Final full-check results accompany the implementation report. Both exact merged-
commit `check` and `v1-supported-platform-matrix` remain required before manual
closure. This is bounded implementation evidence: #208/unresolved findings remain
open, UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed. Package, Python
minimum, AGPL-3.0-only, dependencies including `tzdata>=2026.4`, #230 profile shape,
public/Product contracts and 98 outputs remain unchanged. No whole-UAT acceptance
or Release readiness is claimed.

## Issue #242 own-assignment evidence

Preflight began clean on `bug/242-own-player-seat-setup` at
`dc7b8f575b111be267993c5677181c1008df74f5`. The live #242 issue and R02 in #208's
consolidated retest were read. The current shared adapter still rejected exact
saved-own targets, independently of the archived characterization. Before production
edits, six pure seat/family cases and two real returned-form HTTP cases failed:
both Session and Match returned 400 for B/C/A with own A at Rearhand. Profile bytes
were unchanged and neither Product was created. The retained pre-fix pytest output
records all eight failures; no archive was restored.

The corrected projection is compared with the valid placeholder-derived roster
under deterministic entropy, including canonical prepared Session/Match output.
Coverage includes all own seats, blank/exact/automatic targets, repeated Update,
all six moves, the account matrix, source-binding validation, genuine occupants,
mixed modes/names, unknown/forged handles and independent duplicates. Rejections
leave the original pure input unchanged. Existing persisted permutation tests retain
all eighteen roster/perspective combinations and every one of the 36 rotations.

Real Settings operations create A/B/C and choose own A. Both creation families now
reach a complete named roster with one Update from the first returned form, followed
by explicit Create. The old redundant saved-A payload remains a separately labelled
compatibility test; no helper clears it. Tests strictly reopen revision-zero files,
continue a representative Session into its eleven-Command first-hand save, and
explicitly Start/reopen a Match. Collision/language/manual-C paths retain exact
local date/time, platform/source metadata and account ownership without changing own A.
Changed final Create, stale/removed/forged own identity, expired/superseded setups,
competing submissions, Product failure and profile failure keep one-use behavior.
Real retained Session Results and Match Reports survive setup and rejection, with
normal invalidation on successful same-family activation.

The affected-path run passed **601 tests in 268.29s**, with no skips, covering
creation, profile/private/public compatibility, language/validation, local time,
knowledge entry, packaging/CLI imports and #239–#241 regressions. A final focused
run passed **102 tests in 34.78s**, also covering retention of a supplied source
account when the optional destination account key is absent. Three separately
executed existing filesystem probes retain their Windows symlink-permission skips
(learning entry errno 22, recording deletion WinError 1314, managed-item link creation).
They are not new skips. The final unchanged-tree full-check log and actual child exit
are reported with the implementation; both exact merged-commit CI jobs still gate closure.
The first full run completed with one stale catalog-count assertion (1,564 instead
of 1,569), 9,375 passing tests and the same three skips; all pre-pytest stages passed.
The assertion now includes the five matching #242 messages. Production code and
installed-browser resources were unchanged by this test-only correction; the final
report records the required complete corrected-tree rerun.

`scripts/verify_own_player_assignment.py` reuses the existing dependency-free native
DevTools tooling and an independently installed Wheel. It checks fourteen installed
module/resource hashes against the runtime source tree and authenticated served
resource bytes. Final synthetic evidence is outside Product/user data:

```text
<temporary-directory>/opencode/242-browser-complete/evidence.json
<temporary-directory>/opencode/242-accounts-complete/evidence.json
<temporary-directory>/opencode/242-browser-summary.json
```

Both runs have `completed: true`: **172 measurements / 432 screenshots**, headless
Microsoft Edge **153.0.4234.32**, Windows CPython **3.13.7**, Package **0.17.0**.
German/English and script/no-script cover **1365×900**, **390×844**, **320×800**, plus
**200% text at 320 pixels**, with browser zoom/device scale unchanged at 100%/1.
Document/client widths agree throughout. Native controls demonstrate initial
selection, the two remaining identity tasks, review/Create, an editable Boris
collision, language correction, pending reviewed movement, and manual Clara
perspective with Alexandra retained as own Player. The separate account probe
preserves both distinct values through language switching, retains the explicitly
chosen target account on correction, and verifies the moved persisted roster.
Manual-to-own perspective errors expose a usable selector. Unsent title/seat values
survive language changes only with the unchanged optional script; submitted values
survive both modes. No selection triggers a POST.

The native flows perform **20 creations**, each with one Product replacement and
one profile enrichment. Subsequent explicit first-hand/Start actions bring the
measured Product replacements to **12 Session / 16 Match**. The separately recorded
Settings fixture operations and explicit language saves are not creation writes.
Update/rejection performs zero Product/profile writes. Reopened rosters and
perspectives match persisted values. HTTP metadata and direct duplicate-payload
checks remain distinct from these native actions.

The installed Wheel SHA-256 is
`d036e2da730d0b0e01e0e3af1faf8df87fead8e20c467683f90ef244bddc9da3`.
Installed CSS SHA-256 is
`63f7645e346e46e7a1d8522494234149ef5b2db3d7b1a07630f6d80332bc80e5`;
the exact adapter, renderer, catalogs and unchanged script hashes are in the evidence.
Inspected screenshots include `native-de-sessions-reviewed-320-2-own-row.png`,
`js-en-matches-occupied-390-1-own-row.png`, and the account-controls and mixed-perspective
images. Complete long escaped names wrap and require vertical scrolling at enlarged
text; native selects retain their complete options. Other engines and assistive
technologies were not exercised. This is bounded implementation evidence, not
maintainer UAT, R08/residual-R11 closure or a whole-frontend accessibility claim.
#241 remains completed; #208 and other findings remain open, UAT-01 unaccepted,
UAT-02–12 paused, B-09/B-07 open and B-06 closed. Current 63-route/107-form counts,
Package, license, dependencies, profile/public/persistence contracts and 98 scenarios
are preserved. Maintainer UAT/default roots and installation remain untouched.
