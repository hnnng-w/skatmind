# Saved time zones and explicit local time entry

Issue #230 adds one optional metadata path: save a usual timezone in Settings,
enter a known local date and time, explicitly resolve ambiguity, and save the
existing Product `played_at` through its existing operation.

## Scope and defaults

The unified browser editor covers Match creation, Match metadata update, Session
`set_game_metadata`, and correction of an accepted Session metadata Command.
New exact date/time values start blank. The input-zone default is the saved
preference, otherwise the explicit UX default **Europe/Berlin**. Language, browser
location, OS timezone and today's offset never select it. A per-entry override
affects only that entry.

Settings has one native selector with **Use application default (Europe/Berlin)**,
then Europe/Berlin, UTC and remaining installed keys in stable order without
duplicates. Saving Berlin explicitly stores a preference even though the unset
default is also Berlin. Saving the stored selection is a no-op. GET creates/writes
no profile. The normal Match display-date field remains. Issue #231 makes Session
metadata secondary: [direct initial Card entry](session_direct_card_start.md) supplies
a missing ID in its one-save candidate, without a timestamp or separate confirmation.
Statistics/manual Analyze/Review timestamps, video timecodes,
platform/format controls and other timestamp surfaces are not replaced.

## Intentional private-profile extension

The private profile remains version `1`, in the same `frontend-profile.json`, with
the same top-level fields, fingerprint domain, revision, size bound, CAS and
canonical serializer. Only `interface_preferences` gains an optional second key:

```json
{"advanced_settings_expanded": false}
```

or, after an explicit selection:

```json
{"advanced_settings_expanded": false, "time_zone": "Europe/Berlin"}
```

Exactly these ordered shapes are accepted. Present null, reordered keys and extra
keys are rejected. The value enters the existing fingerprint. Unset omits the key,
so old profiles and unchanged default builders retain exact canonical bytes.
No startup/load/GET migration occurs.

Compatibility is directional: this build reads old profiles; older builds may
reject profiles containing `time_zone`. Before using an older build, explicitly
save **Use application default** in this build to remove only that preference.
Language, Players, legacy aliases/accounts, defaults and labels remain. This is
not a general downgrade guarantee. Recommended-default reset preserves this zone;
full explicit profile reset retains its whole-profile scope. Language, Player,
default, label and creation-enrichment operations preserve the optional field.

Stored keys use bounded ASCII IANA-style syntax (1–255 characters; nonempty
slash-separated alphanumeric/underscore/plus/minus components), independent of
database availability. New selections require exact installed membership and a
readable zone resource. A formerly saved unavailable key keeps the profile valid
and intact, with a timezone-specific explanation. Select another zone or clear
only the preference; there is no silent UTC/Berlin substitution or forced reset.

## Packaged database

The sole added runtime dependency on every supported platform is **tzdata>=2026.4**.
Existing jsonschema/referencing requirements remain. Minimum artifact lanes install
**tzdata==2026.4**. The dependency and optional profile field are intentional
compatibility changes, not unchanged contracts.

`time_zone_provider.py` reads `tzdata.zones` and `tzdata.IANA_VERSION`. It constructs
standard-library `ZoneInfo` using `ZoneInfo.from_file` over `importlib.resources`
bytes from `tzdata.zoneinfo`. It never searches host IANA directories or changes
`TZPATH`, environment variables, machine settings or global ZoneInfo caches.
Membership precedes resource access. Reads are bounded to 1 MiB; the inventory is
bounded to 2,048 keys and cached once; loaded zones use a 64-entry LRU. No files
are vendored. Missing/damaged data produces installation guidance. Keep and
explicit preference removal need no conversion or external timezone service.

Local verification used **tzdata 2026.4, IANA 2026d, 598 keys**, with empty Windows
host `zoneinfo.TZPATH`. Versions are diagnostic evidence, not Game fields. See the
[installation matrix](v1_installation_and_supported_platform_matrix.md) and
[dependency licensing](v1_package_license.md).

## Native input and conversion

The compact disclosure contains native date/time/select controls, with no editable
UTC-offset string. A zone alone records nothing. Date without time and time without
date have separate feedback. No Now, midnight, source-time or Session-start value
is invented. Accepted syntax is exact `YYYY-MM-DD` and `HH:MM`, optionally `:SS`
and one through six fractional digits following seconds. Years are 0001–9999,
also bounded by representable UTC conversion. `HH:MM` serializes seconds as `00`
without implying measured seconds. Browser presentation may differ by locale;
submitted fields are locale-neutral. Edge may submit `.000` after a native
minute/hour edit; explicit fractional replacement renders six digits. Existing
timestamps are never subjected to that formatting.

The pure `local_time_conversion.py` evaluates both fold interpretations, round-trips
through UTC and accepts only candidates returning the original wall fields.
Deduplication and ordering use UTC instants, never same-zone aware equality. Zero
candidates is a nonexistent-time error; one uses the actual date-specific offset;
two require the native earlier/later selector with actual offsets and no default.
Offsets requiring seconds are rejected, not rounded. The result passes the
unchanged Product RFC 3339 validator.

| Entered Berlin date/time | Independently verified outcome |
| --- | --- |
| 2026-01-15 19:30 | `2026-01-15T19:30:00+01:00` |
| 2026-07-15 19:30 | `2026-07-15T19:30:00+02:00` |
| 2026-03-29 02:30 | Nonexistent; no Product/profile write |
| 2026-10-25 02:30 | Explicit `+02:00` earlier or `+01:00` later occurrence |

Independent tests also cover UTC, Kathmandu `+05:45`, Kiritimati local/UTC date
boundaries, Lord Howe's 30-minute fold/gap, Apia's skipped date, fractions/calendar
limits, historical offset seconds, forged keys and missing/corrupt data.

## Keep, Replace, Remove and date-only safety

Existing metadata defaults to **Keep recorded time**. The server retrieves the
original string from the bound recording or particular accepted Command being
corrected. No hidden client `played_at` is trusted. Read-only text identifies the
supplied offset honestly; an offset does not identify an IANA zone. Keep preserves
lowercase spelling, negative-zero offset, higher fractional precision and accepted
leap-second spelling byte-for-byte. `rfc3339.py` is unchanged.

**Replace** exposes local entry; **Remove** supplies the existing absent timestamp.
Replacement values under Keep/Remove are rejected rather than ignored. Session
correction still replaces one Command and replays the suffix, with existing
partial/rejected outcomes. A later accepted metadata Command may still determine
the current projected time.

Session metadata remains append-only: an additional metadata entry supplies only
a missing field. Once time is recorded, the optional area links to its explicit
accepted-Command correction. Supplying a missing Game ID keeps an already recorded
timestamp by leaving the new Command's timestamp absent, preserving the accepted
original rather than attempting to record it twice. Direct Card startup uses the
same ID-only semantics without invoking local-time resolution. Optional time may
still be appended after hand entry. Remove cannot replace a timestamp-only legacy
Command with an invalid empty metadata Command or silently change correction targets.

Match display date remains profile-only metadata, never temporal evidence. At
creation it must match an explicitly entered local calendar date, not the UTC
date. Later metadata updates do not synchronize labels through a second write.
Statistics eligibility remains strict accepted-instant comparison: before is
eligible, equal/after is not; absent Match time remains unavailable.

## Private forms and lifecycle

The only new route is `POST /actions/profile/time-zone`, returning to `/settings`.
It reuses profile generation, CAS and same-directory atomic replacement. Current
counts are **59 POST routes / 103 forms / 1,460 matching catalog keys**. Five
definitions are added: `profile.time_zone`, `match.local_create` on
`/matches/api/v1/create`, `match.local_metadata` on `/matches/api/v1/operation`, and
`session.local_metadata`/`session.local_metadata_correction` on `/sessions/command`.

Local forms use `time_form`, `time_selection`, `time_mode`, `local_date`, `local_time`,
`local_zone`, `local_occurrence`, profile generation and existing source transport.
Private fields are stripped before canonical Product construction. Unmarked explicit
RFC 3339 legacy submissions keep their separate parser. Mixed representations are
rejected; standalone Capture and public Session parsing are unchanged.

Bindings cover the setup token or exact active content/generation, reopen-specific
key, selected Match Game and correction target. Occurrence HMACs additionally bind
the exact date/time/zone, package/IANA versions and candidate instant. Conversion
and generation are checked before the existing operation. Invalid input precedes
identity generation and Product creation. #225 roster review remains: an ambiguous
time included in setup review is explicitly selected again on final Create, without
changing the reviewed roster. Changed local input cannot silently reuse a choice.

Success is `303`, contextual validation `400`, and source/generation/save conflict
`409`. Bilingual field errors have focus and useful anchors. #223 preserves safe
submitted values/errors natively; unsent values in another form require optional
JavaScript. Occurrence selection and obsolete hidden transport are excluded from
that envelope. Transport is regenerated; language never saves metadata.

Preference-only changes preserve recording bytes, Checkpoints, #221 Requests/Results,
#222 previews, eligibility and downloads. Real Product edits keep their existing
invalidation. Product-first/profile-second creation warnings, one intended save,
no-ops and explicit conflict recovery remain. No retry, automatic reload, rollback
or cross-file transaction is introduced.

## Installed-browser evidence

`scripts/verify_local_time_entry.py` reuses dependency-free local DevTools tooling
with an independently installed Wheel. It rejects checkout imports and verifies
loaded source/resource bytes. It is separate from dependencies and the full check.

```powershell
python scripts/verify_local_time_entry.py `
  --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
  --output "$env:TEMP\opencode\time-entry-evidence" --phase after
```

Use the verification environment's Python. `--phase before` captures an old build;
it never rewrites application code to emulate one. Local evidence:

```text
<temporary-directory>/opencode/time-230-before/evidence.json
<temporary-directory>/opencode/time-230-after/evidence.json
```

Baseline Wheel commit `3341b9fc645ee808158a4fc3131f5b359cb50777` has 64 measurements.
Final Edge **153.0.4234.32**, Python **3.13.7**, Package **0.17.0** evidence has 96:
de/en, JavaScript on/off, 1365×900, 390×844, 320×800 and 200% text at 320 pixels.
All final document/client widths agree (1350, 375 or 305 pixels). Native inputs
stay in their column; long single-line content uses browser caret scrolling.
Errors focus the summary; Session saves focus `session-recording`.

Each script mode saves a zone, verifies no-op/fresh-context load, creates date-only,
winter/summer and both fold Matches, rejects gaps/ambiguity without creation,
edits Match metadata with Keep, saves/corrects Session time and reopens identical
bytes. Native ArrowUp changed date `2026-01-15` to `2026-01-16` and time `18:30` to
`19:30:00.000`. Home/ArrowDown selected UTC/Berlin without typing zone names. The
actual Session value was `2026-01-16T19:30:00.000000+01:00`, explicitly corrected
to `2026-07-15T19:30:00+02:00`. Synthetic initialization assigns control values;
native key changes, submission, validation and saves are real.

Each measured save sends one POST. A transparent successful `os.replace` counter
records **21 profile / 3 Session / 6 Match** replacements per script mode, including
deliberate language saves/creation labels. Five creations and one metadata edit
account for the six Match saves. HTTP tests separately assert zero ID/Product calls
on failed time input; one Match ID/three Player IDs/one creation on success; zero
writes on metadata no-op and one on a title edit. Injected provider/save failures
are fault tests, not observed outages.

Selected final SHA-256 hashes; all module/resource hashes are in `evidence.json`:

| Resource | SHA-256 |
| --- | --- |
| `assets/app.css` | `3b8257ebb8b9fa8f4587772c41bb5d749970a18da42e617349326e9f1377459c` |
| `assets/workflow.js` | `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298` |
| `locales/en.json` | `f99373d356f868b90b6453a82320501c5fa4772efe473731878d54b512a1e4be` |
| `locales/de.json` | `cb70c1fdac83d1bc7c45ec60c6199c1d6a7a072f412406c8f62034c5d51bed3c` |
| `time_zone_provider.py` | `88dbe6d54d37d1a53d5d5868d590302e8056816d4b8e319eea86ec9e03cc40f1` |
| `local_time_conversion.py` | `21171fa4228eef310f0e80576112b162b885294890923bffeefeac1c553bba77` |

## Installation and regression evidence

The existing Windows supported-platform runner passed all six cells: resolved
source/Editable/Wheel/sdist and minimum-supported Wheel/sdist. Resolved direct
versions were jsonschema **4.26.0**, referencing **0.37.0**, tzdata **2026.4**;
minimum versions were **4.23.0 / 0.31.0 / 2026.4**. All `pip check`, installed
smoke, seven-workflow, resource and semantic comparisons passed. The shared
semantic digest was `51d0cb5e0502adc92446cc7c4efa60e0acd55c0010dffccdb43894e10a170ec6`;
the runner reported no repository mutation. Windows evidence does not substitute
for the required exact-merged-commit Ubuntu jobs.

Focused conversion/profile, real metadata/creation/correction/reopen, temporal,
language, security, standalone and #221–#229 regressions were exercised. The broad
run passed 890 tests and exposed seven old normal-UI fixtures mixing raw timestamps
with emitted local fields. Those UI fixtures now submit explicit local controls;
the shared helper does no conversion or missing-field completion, and separate
legacy timestamp transport cases remain. The corrected affected run passed 168
tests; a final timestamp/contract/profile/packaging-focused run passed 344 tests.
The final full-check result belongs to the accompanying implementation report.

The first complete Python 3.13 check passed Ruff, schemas, all 98 generated
outputs and distribution validation, then reported 8,780 passed, 1 skipped and
one failed pytest test. Its only failure was the exact reviewed legacy-name
inventory's stale line references after documentation insertions. Eleven line
numbers in `docs/skatmind_rename_inventory.json` were synchronized; occurrence
hashes, classifications, reasons and historical text were retained. The corrected
tree requires a complete full-check rerun; the first attempt is not success.

This is implementation verification, not maintainer UAT or a whole-frontend pass.
Exact merged-commit `check` and `v1-supported-platform-matrix` remain required.
#208/unresolved findings remain open; UAT-01 failed, UAT-02–12 are paused,
B-09/B-07 are open, B-06 is closed, and Package 1.0.0/Release preparation is unready.
Package/Python/license, public APIs, Commands, Schemas, seven Root workflows,
Product persistence and 98 generated outputs remain unchanged.
