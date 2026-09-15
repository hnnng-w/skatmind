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
4. Open Session or Match creation. Own perspective supplies that identity, with
   **no seat selected**. For a Match, the seat explicitly means **game 1**.
5. Select a seat and use **Update setup and review roster**. Fill the other seats
   in saved-Player or new-name mode. Both modes work with JavaScript disabled;
   app-owned CSS follows the native select state.
6. Review the named roster and perspective, then Create. Changing the form after
   review requires another setup update. Setup-only requests create no Product,
   generate no Product/Player IDs, and save no preferences.

Other-perspective/manual setup remains available. Without an own preference it is
the initial mode. A Retrospective Session may have no local Player; a Live Session
requires a perspective. Recording afterward grants no additional hidden-card
knowledge beyond the existing capture-mode contracts.

## Private routes and forms

`GET /settings` is the eighth **shell page**, not an eighth Root workflow. About
retains Product/version/license/privacy/installation information and a Settings
link. Profile mutation forms are rendered only on Settings; the global language
form remains on every page.

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

Changing own seat moves only the server-retained automatic Player bundle. Any
independent destination handle, new name, or account value produces field-linked
collision feedback. Values are retained; no overwrite or swap resolves the conflict.
Final input must match the reviewed setup and current own identity. Final submission
consumes the setup selection once. Exact Product metadata is validated before ID
generation, followed by Product-first creation and at most one profile enrichment.

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
it retains own Player, directory, language and labels. Complete profile reset
clears the profile, including labels, but changes no Product document or artifact.

No-ops write nothing. A profile conflict, capacity limit or storage failure after
successful Product creation retains the valid Product and reports unsaved enrichment.
There is no retry, merge, automatic reload, deletion rollback or analysis side effect.

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
