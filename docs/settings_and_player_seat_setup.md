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
