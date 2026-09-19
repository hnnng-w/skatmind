# Profile-driven stateful creation

## Status and boundary

Issue #219 implements the private version-1 profile-driven creation layer in the
unified local browser application. It simplifies creation of one Session Game,
one EuroSkat 36-position Match, and one Learning collection without changing the
underlying Session, Match Workspace, or Learning Corpus persistence contracts.

The private contract identity is:

```text
PROFILE_DRIVEN_FORM_DEFAULTS_VERSION = 1
```

The implementation does not change Package version `0.17.0`, Python `>=3.13`,
the `AGPL-3.0-only` license, Public API contract version `1`, the seven Root
workflows, the one Console Script, Schemas, examples, generated outputs, Product
persistence formats, or standalone technical interfaces.

## Local settings and Players

Issue #225 revises the ordinary UI described by the historical #219 slice below.
The current authoritative flow is [Settings and Player seat
setup](settings_and_player_seat_setup.md): dedicated Settings, compact lossless
editing, one own-Player preference, explicit seats and unchecked enrichment.

Issue #219 activates the reserved version-1 fields in the existing private
`frontend-profile.json` document. `LOCAL_FRONTEND_PROFILE_VERSION` remains `1`,
and the historical canonical empty-profile bytes and fingerprint remain
unchanged. The profile may now retain:

* known Players with a display name, aliases, and optional platform Player IDs;
* one own Player and one preferred perspective Player;
* one preferred friendly game platform;
* the existing Advanced-settings display preference;
* Issue #230's optional independently saved timezone for new exact-time entry;
* private display names for managed Sessions, Matches, and Learning collections;
* an optional date-only Match display label.

The Settings page provides authenticated bilingual operations to add, edit, and
remove known Players, edit creation defaults, reset recommended defaults, and
reset the complete profile. Stateful landing pages allow display labels to be
edited for both created and imported managed Products. Labels never rename the
authoritative Product identity or persistence file.

The strict bounds are:

```text
known Players:                         512
aliases per Player:                    16
platform IDs per Player:               16
Player and platform-name characters:  120
platform Player-ID characters:         255
managed display labels:                2,048
managed display-name characters:       160
profile file bytes:                    1,048,576
```

Duplicate Player display names require explicit disambiguation. Profile writes
remain canonical, revisioned, fingerprinted, same-directory atomic replacements
with optimistic compare-and-swap behavior. A profile file changed outside the
running process requires restarting SkatMind before another profile-only write.
An invalid profile must be explicitly reset from Settings before profile-driven
creation or local-setting mutation; opening existing Products remains separate.

## Generated identities

Normal creation owns technical identifiers. Each identifier uses 32 bytes from
an injected entropy source, a domain-separated SHA-256 digest, and at most 16
generation attempts. The exact prefixes are:

```text
frontend-player-
frontend-session-
frontend-match-
frontend-corpus-
```

The frozen domains are:

```text
b"skatmind\0frontend_player_id_v1\0"
b"skatmind\0frontend_session_id_v1\0"
b"skatmind\0frontend_match_id_v1\0"
b"skatmind\0frontend_corpus_id_v1\0"
b"skatmind\0frontend_known_player_handle_v1\0"
```

Known-Player selection uses one-way SHA-256 browser handles together with the
current profile generation. Internal Player IDs, Product paths, profile
fingerprints, and platform IDs are not presented as normal visible values.
Imported Session and Match identities are retained unchanged; frontend identity
generation applies only to normal creation.

## Creation forms

Issue #233 supersedes the time-based Session choice with **Which Cards can you supply?**:
Player-perspective recording (`live`, during or after a Game) or complete-deal
reconstruction (`retrospective`, all three initial hands plus original Skat).
The form asks for a Game name, three named Players, and a perspective seat required
for `live` and optional for reconstruction. Selecting a local Player does not reduce
reconstruction's complete-deal requirement. See
[Knowledge-based Session entry](session_knowledge_based_entry.md).
A Player seat uses either saved-Player or new-name mode. Own identity never implies a seat;
the own seat begins empty and must be explicitly selected. A setup-only POST
projects the named roster before final creation. Saving new Players defaults off;
Session creation saves no separate perspective preference. The compatible hidden
preferred perspective is retained but does not fill ordinary forms. Capture mode
is not a saved profile preference.

Issue #242 makes the shared Session/Match own assignment a single input task: choose
the initially unset own seat, enter the other two Players, Update once, then explicitly
Create. Native CSS presents a free own row as derived before the first submission;
it retains real occupied destinations and error controls. Reviewed automatic rows
and pending moves remain distinguishable, without a second full roster summary.
The exact saved-own target (saved mode/current handle/blank new name) is idempotent
on Update. Explicit same-identity accounts are retained losslessly or rejected if
both nonempty values differ. Account-only occupancy, other Players, mixed names/modes
and independent own duplicates remain conflicts. See the
[exact-self and account rules](settings_and_player_seat_setup.md#seat-projection-and-match-translation).
Final Create still compares exact reviewed values before consuming its one-use setup.
No new route, field, setting, browser state, ID system or Product initialization
Command is introduced. Setup/rejection generates no IDs, saves no Product/profile,
collects no Checkpoint and runs no analysis. Manual C perspective with Settings own A,
no-own defaults, Live's local requirement and Retrospective no-local support remain.

Issue #232 supersedes #219's normal `EuroSkat 36-game standard` wording with
**Recording format (fixed): 36 games · 3 fixed players**, translated through the
German/English catalogs. The positions include passed deals. Platform describes
where play occurred and does not select another template; other Match formats
are not supported. Counts come from the existing canonical format object.
Creation, setup review, validation rerenders and active Match metadata share the
same compact scope paragraph. The existing metadata editor remains operational.

Optional **Technical details**, appended inside the existing Advanced Match
details disclosure, displays the exact read-only canonical definition:
`euroskat_36_standard_v1`, provider `EuroSkat`, display name `36er Standard`,
`player_count = 3`, `game_count = 36`. This is ordinary escaped presentation,
not a submitted field or new browser payload. The earlier label remains historical
evidence; the stored ID/provider/name, registry and template are unchanged.

The form asks for a Match title, an optional date-only
display value, a friendly platform, three named Players, and a perspective
seat. Friendly platform values are `euroskat`, `in_person`, `other_online`,
`unknown`, and `custom`. An optional Source URL is a normal field; source kind,
title, channel, timecodes, and other exact Product metadata remain inside
Advanced settings. A date-only value is private display metadata and does not
invent `played_at`. Issue #230 adds optional native local date/time/zone controls;
only an explicit complete, resolved entry populates that Product field. The separate
legacy explicit RFC 3339 adapter remains. Saved platform account IDs are not copied invisibly into a new
Match; only values explicitly submitted for that Match enter Product metadata.
Issue #225 gives these fields seat-named game-1 semantics. Complete Forehand,
Middlehand and Rearhand bundles map respectively to places 2, 3 and 1. Rotation
and standalone table-place creation are unchanged. Match has a separate unchecked
save-platform checkbox, with no seat or perspective saving effect.

All five choices retain their exact mapping: `euroskat` → `EuroSkat`, `in_person`
→ `In-person game`, `other_online` → `Other online platform`, `unknown` → `Unknown`,
and `custom` → existing validated custom text. Custom metadata is not inspected
for brands or Game counts. Source URL/kind describes the observation independently
of platform and format. Native selection changes only unsaved input; roster,
source and local-time values are retained. Neither selection nor disclosure
opening sends a Product request. There is no provider-specific ranking/fee claim.

The Learning form asks only for a collection name and generates the internal
Corpus ID. It does not import Matches, select a Current Snapshot, prepare
artifacts, or run analysis.

Session and Match JSON import remain secondary actions after normal creation and
saved items. Import preserves the supplied Product identity. There is no new
whole-Corpus JSON import path.

All creation and settings forms use the Issue-#218 registered validation layer.
Safe submitted values survive localized `400` and `409` responses and language
changes. Field-specific errors attach to the exact form and open their containing
Advanced disclosure when necessary. Opaque handles are retained only as bounded
hidden or select identity values and are never included in visible error text.

## Persistence ordering

The creation sequence is strict:

```text
validate submitted values and current profile generation
generate collision-checked private identities
create and persist the authoritative Product exactly once
attempt the optional profile update exactly once
publish the active Product and redirect to its normal page
```

A Product creation failure makes no profile change. Once Product persistence
succeeds, a profile conflict, capacity limit, size limit, or storage failure does
not roll back or delete the Product. The Product remains persisted, active, and
discoverable, and the browser displays a localized non-destructive warning.
There is no cross-file transaction claim. Creation runs no analysis,
preparation, automatic Learning import, or Match-to-Corpus transfer.

## Validation and packaging

After Issues #221–#225, the unified frontend has exactly 54 POST routes and 87
registered form definitions. The historical #219/#221 counts are superseded only
for this current private browser surface. German/English catalogs retain strict parity.
Focused tests cover profile compatibility and persistence, generated domains and
collision handling, known-Player operations, friendly creation translation,
safe validation retention, bilingual rendering, one-call Product/profile
ordering, and Product survival across profile conflict, size, and storage
failures for Session, Match, and Learning creation.

The private modules, translation catalogs, and local CSS remain packaged resources.
Issue #230 intentionally adds `tzdata>=2026.4` and optional `interface_preferences.time_zone`;
old default bytes remain exact, but older readers may reject the new shape. Current
counts are 59 POST routes/103 forms. See [Local time entry](local_time_entry.md) for
explicit gaps/folds, creation binding, before-ID validation, literal local-date
reconciliation and directional compatibility. No Public API, Schema, example,
generated output or Package entry point is introduced.

Issue #232 retains those 59 POST routes and 103 exact forms and adds one matching
catalog key, bringing the de/en catalogs to 1,464 keys. Its 35 focused cases cover
all platform choices, saved/default-saving choices, custom escaping, exact canonical
object identity, all 36 rotations, genuine returned-form creation/error/correction,
strict reopen, and metadata updates preserving an accepted Play prefix. A real
Decision Report survives no-op/passive operations and is invalidated by the actual
metadata revision. Existing canonical count-override/unsupported-format tests and
standalone interfaces remain intact. Installed-browser evidence is recorded in
[Settings and Player seat setup](settings_and_player_seat_setup.md#issue-232-fixed-recording-scope-evidence).

## Remaining frontend work

The #242 creation repair preserves the current **63 POST routes / 107 forms**,
Package 0.17.0, dependencies including `tzdata>=2026.4`, public/profile/persistence
shapes, Game-1 2/3/1 bundle mapping, 36 rotations and 98 generated scenarios.
Its focused HTTP and independent-Wheel browser evidence is recorded in the Settings
guide. #241 remains completed; R08 and residual R11 work remain separate.

Issue #219 further partially remediates UAT-FINDING-001, implements the creation-
form portion of UAT-FINDING-005, implements the profile/default/creation portion
of UAT-FINDING-007, and adds bilingual creation pages toward UAT-FINDING-008.
Issue #220 implements their applicable active-view remediation. Findings remain
open pending repeated UAT-01.

After Issue #220 merge and green exact-commit CI, the next maintainer action is:

```text
Repeat UAT-01 under Issue #208.
```

Issue #220 implements next-action active Session layout, minimal Match Game entry,
Learning prerequisites and Build-insights flow, plain-language Snapshot and
Preparation presentation, complete Advanced/Technical-detail separation, and
complete German and English workflow coverage. UAT-02 through UAT-12 remain
paused; B-09 and B-07 remain open; Package `1.0.0` and Release preparation are
not ready.

See [Task-first bilingual stateful workflows](task_first_bilingual_stateful_workflows.md).
