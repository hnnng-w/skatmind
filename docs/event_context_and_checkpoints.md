# Event context and chronological checkpoints

## Scope and ordinary use

Issue #321 implements private version-1 context for managed Match and Session
recordings. #316–#320 are accepted and closed. #208 and release acceptance remain
open. Hosted exact-commit gates and the later **combined** installed acceptance
with accounting/Cent work remain maintainer work; this feature does not request
an intermediate installed test.

Open an existing Match and find **Event and chronological score**. The selected
participant comes from the recording's perspective. Enter the actual event and
series/list identity, explicitly confirm its mode and scoring-rule source/version,
then enter **24 / 780 / 3** with the confirmation evidence. No earlier hands are
required. Saving continues at position 25: the applicable score is 780, with three own lost
declarer games and twelve remaining positions **including** game 25. At position
26, only an established result for position 25 is added, once. Reopening or
reprojecting does not add it again.

The compact checkpoint form remains directly available. Optional financial facts
sit in a native disclosure. Another disclosure distinguishes a factual correction
at an existing terms boundary from terms that genuinely changed at a later game.
Position 36 also offers explicit end-of-list inspection through the last position,
with zero later positions and any unresolved gaps still shown.
The interface uses the DE/EN catalogs, native forms, accessible validation and
submitted-value preservation. It works without JavaScript or JSON/model transport.
Existing recording import remains useful for transferring developer fixtures.

On a Session, explicitly attach to an existing event and game position, mapping
each of the three existing participants. Exact stable IDs may prefill that
mapping; names never join identities. An existing local participant is reused.
Only a complete-deal Session with no local participant needs one explicit
selection from its existing roster. The selected participant and the actor at a
Card decision remain separate. A Session binding to a Match must agree with its
fixed seat rotation. Correcting a Session position is an explicit attachment
revision; moving it silently to an unrelated event is rejected.

**Save this decision's context only** accepts an already recorded Card decision
number. It saves no recommendation and starts no analysis. Historical saved
contexts are labeled as captured values, with an explicit stale-source/context
notice when applicable. Existing native Request/Result downloads and retained
analyses keep their original meaning and bytes. Independent Learning collections
are not edited by context operations.

## Private contracts and boundaries

The implementation is split into focused modules:

| Module | Responsibility |
| --- | --- |
| `event_context_contracts.py` | Immutable event/series identity, participants, explicit recording bindings, terms, exact financial facts and cumulative checkpoints |
| `event_context_sources.py` | Existing strict recording reconstruction, decision actor/cutoff and established-outcome adapters |
| `event_context_projection.py` | Prefix coverage, duplicate-source agreement, contribution arithmetic, checkpoint comparisons and immutable preparation |
| `event_context_operations.py` | Explicit no-op/revision/conflict, checkpoint, reconciliation, attachment and applicability operations |
| `event_context_store.py` | Bounded append-only context history and frozen-value journal, strict resume and optimistic atomic save |
| `event_context_recording_files.py` | Existing strict Match/Session file loaders |
| `app_web/event_context_*.py` | Managed-source discovery, source-bound forms, localized presentation and explicit context-only operations |

All new records use exact private version `1` and reject unknown/missing fields,
wrong types, Boolean counts, unsupported versions and invalid nested values.
Shared finite-JSON/closed-record and bounded local-I/O helpers are reused without
changing Automatic Learning's contracts or identity domains. Context fingerprints
use their own `skatmind\0event_context_v1\0` namespace.

An event/list has stable generated event and series IDs, confirmed descriptive
names, exactly three participants and one selected participant. Each binding
retains the original source family, Product identity, persistence contract version,
revision and content fingerprint, plus the exact ordered participant mapping.
Match bindings cover their unchanged 36 slots; Session bindings identify one game.
A source has at most one current event owner, and an event does not combine
independent Matches. Labels, filenames, times and similar scores are not identity
evidence. Recording changes are freshly verified, rather than interpreted as
another event or implicitly merged.

The journal is separate from closed Match/Session v1 payloads and from
`frontend-profile.json`. No old archive producer, codec, public API, Root workflow,
Schema, package/dependency version or recording format changed.

## Prefix arithmetic and actual evidence

For a decision in game `g`, the service considers only anchors with
`through_position < g` and contributions through `g - 1`. The latest eligible
**boundary**, not the latest entered checkpoint, supplies the cumulative anchor.
Covered positions are never added again. With no anchor, the empty prefix starts
at zero, and each earlier position must have established evidence. Missing
uncovered positions stop the displayed established total; later results cannot
bridge a gap. Negative personal scores are valid.

| Evidence | Projection |
| --- | --- |
| Empty Match slot | `missing`, not zero or passed |
| Observed incomplete game / non-ended Session | `unfinished` |
| Complete trace without required settlement evidence | `unsettled` |
| Explicit Match passed deal | `passed`, consumes one position and contributes zero |
| Supported established settlement | `settled`, one contribution from the existing scorer |
| Bound source absent, invalid or ambiguous | `source_unavailable` |
| Contradictory bound recordings | `source_conflict` |

Match settlement requires the existing strict normal-completion Historical
materializer: complete declaration/bid, legal complete trace, known original Skat
and exact non-Hand discards (or accepted Hand semantics). Occupancy and 30 Plays
alone are not settlement. No missing Skat or hands are invented to obtain a score.

The Session adapter uses accepted-log reconstruction and existing Historical-ready
export for normal completion, declarer concession and defender concession. Other
Session endings remain explicitly unsettled in this context adapter: it does not
launch proof search to obtain accounting facts. It does not use retained Card
analysis as a substitute for an established recording result.

`build_historical_game_summary()` and `get_game_outcome_for_rating()` establish
the complete signed settlement. `build_fixed_three_player_list_contributions()`
then supplies the selected participant's personal list points and own-loss delta.
Only their own lost **declarer** games advance that count. Another declarer's loss
can supply the existing defender bonus without increasing the selected person's
own losses.

When a Match and Session refer to the same event position, the position contributes
once. Complete normalized outcome evidence must agree; shared known declaration
facts and observed trace prefixes must also agree, including when one source is
unfinished. A completed source cannot silently hide a contradictory partial one.
Private comparison signatures contain declaration facts and trace-prefix hashes,
not hidden hands or a second recording archive.

Overlapping checkpoints are cumulative anchors. Complete intervening detail can
compare one anchor with the next; incomplete evidence makes no invented historical
claim. A disagreement exposes supplied and derived points and own losses. The
user can correct the checkpoint or explicitly reconfirm the supplied total with a
reason. Reconfirmation is bound to the **displayed exact disagreement** and retains
its comparison basis. Changed evidence requires a new reconciliation. Removing
an active checkpoint retains its earlier revisions. Separate saved-checkpoint
inspection is not an earlier decision's applicable context.

## Financial facts and applicability

Supported modes are `tournament`, `tournament_cent` and Session-only `cent`.
Tournament modes use `fixed_three_player_isko_v1`; Cent facts use
`cent_game_points_v1` and cannot contain list-score checkpoints. A Match cannot
be relabeled as a three-game Cent round. Session Cent metadata is bounded to
positions 1–3; this implements no round lifecycle or monetary execution.

Financial facts retain optional currency, paid and committed entry/table amounts,
selected pools and known personal participation/entitlement, exact selected Cent
tariff, fee/payout source references and editions, confirmed supplied prize facts,
their completeness and provenance. Unknown stays `null`/`unknown`, never zero.
Explicit zero is a known fact. Amounts are reduced integer rational pairs; ordinary
decimal entry is converted exactly. Optional rational input is also exact. Known
amounts need a currency and confirmation evidence; prize facts need their source
and completeness. The eight-pool bound is a small fact list, not a prize-table or
competition engine.

The supported EuroSkat tariff facts are 1/4 Cent for the tournament-table variant
and 1/2, 1, 2, 3 or 5 Cent for Session Cent-Skat, with EUR when a tariff is known.
Tariff absence remains an explicit financial gap. A standard tournament cannot
silently acquire a Cent tariff. No fee, loss charge, transfer, balance, prize,
expected return or threshold is computed.

Terms have explicit `from_position` boundaries. A factual correction replaces one
existing boundary in a new context revision. A genuine later change appends a
later boundary and preserves all earlier terms. Frozen contexts retain the exact
earlier terms. New historical preparation selects by applicability rather than
today's newest settings or global UI preferences.

Provider pages consulted for the meaning of these **recorded** facts:

* <https://www.euroskat.com/turniere/36er-standard>
* <https://www.euroskat.com/spiele/cent-skat>

The tournament page describes differing stakes and a 1/4-Cent table variant;
the Cent page distinguishes game-point scoring without list bonuses and lists
the supported tariffs. These pages are not authoritative evidence of a user's
actual participation, payment, prize entitlement or applicable historical edition.
No runtime fetch, time-derived preset, provider account integration or invented
posting is used. Unresolved Cent posting/rounding and tournament forecasting
inputs belong to subsequent accounting work and do not block this fact capture.

## Persistence, frozen basis and concurrency

The managed-home root gains `event-contexts.json` only on an explicit successful
context save. Passive opening, language changes and application restart create
no context file, write no recording and run no Card analysis or Learning update.
The fixed private envelope identifies `skatmind_event_context_journal`, version
`1`, its complete canonical fingerprint and the journal. Limits are 16 MiB,
4,096 context revisions and 4,096 retained preparations; exceeding a bound fails
without truncation or automatic cleanup.

The journal retains every earlier context revision and prepared value. Strict
resume rejects invalid JSON, duplicate keys, nonfinite values, unsupported
versions, mismatched fingerprints, non-linear history, invalid source ownership,
unbacked reconfirmations and prepared values inconsistent with their retained
basis. Reads and writes use checked regular paths. Save compares the expected
journal fingerprint and fresh bound sources, writes/flushed/fsyncs a unique
same-directory temporary, rechecks, then atomically replaces. Failed pre-replace
writes preserve existing data. This is local optimistic concurrency, not
distributed locking. Equal updates are unchanged. A stale page or corrected
source receives controlled conflict/reload guidance.

`prepare_event_context_v1()` is transport-free. Its immutable value retains the
event revision, selected participant, exact target recording version, original
game identity where supplied, game/decision cutoff, independent actor, applicable
terms/financial facts, checkpoint, exact earlier-position basis, disagreements,
score status and remaining-position semantics. Each established contribution
retains source versions, signed settlement, declarer/outcome and the consumed
evidence identity. Reconciliation retains its actual comparison facts. Restart
recomputes arithmetic from these retained values; an overwritten recording's
fingerprint alone is not the basis.

The service accepts an optional exact `expected_source` for a requested original
version. If unavailable, new preparation reports `source_unavailable`; it does
not substitute today's recording. `preparation_is_current_v1()` requires exact
fresh reproduction and the current context revision. Context-only capture never
claims to have influenced Card ranking. A subsequent monetary producer must
explicitly consume this frozen value through its own versioned contract.

## Small developer fixture and acceptance map

Development-only fixture generation, from a source checkout with development
CPython 3.13 and an already existing disposable external directory:

```powershell
py -3.13 tests/event_context_fixtures.py --output "C:\Temp\synthetic-event-match.json"
```

The generator refuses overwrite and produces one ordinary Workspace with only
game 25 recorded. It creates no UAT build, installation, server, profile, context
journal or Learning generation. For the later combined maintainer checklist,
import this file through existing Match transfer, open game 25 and save the
24 / 780 / 3 checkpoint with a synthetic confirmation note. Position 26 shows
820 / 3: the established other declarer's loss contributes 40 once. Reopen and
inspect the same boundary; no entry of 36 games or raw JSON inspection is needed.
The following accounting/Cent issue adds its own example to that same later
prepared build. Source-only developer checks do not establish installed acceptance.

Focused complete new modules cover contracts/projection, source adapters,
store/reconstruction and native forms. Small synthetic cases cover all nine issue
acceptance areas: context-free sources; continuation/reopen; passed/missing/
unfinished/unsettled and negative/own-loss semantics; cutoffs/applicability;
overlap/backfill/reconciliation; no-op/stale/correction/failure/isolation; durable
frozen basis; shared explicit attachment; bilingual passive native forms and
original-byte preservation.

The final affected-module selection follows the changed call sites: unified server
Match/Session integration, form registry and validation feedback, language-form
preservation and catalog loading, plus the required complete architecture and
rename guards. The changed server's exclusive rejection-transport and Match-action
placement modules run separately after workers exit. The standalone Corpus server
and synthetic early-rejection observer are unchanged. Closed recording codecs,
scoring algorithms, archive producers, schemas and output scenarios are consumed
without modification; their new adapter integration is tested directly. No
unchanged 29-module Learning rerun or local Full is part of this work.

Final command outcomes and durations belong to the implementation handoff, after
documentation is complete. Routine local acceptance requires complete selected
tests with two file-grouped workers, affected exclusive modules, explicit Quick
and whitespace checks. Quick does not certify the complete regression suite,
generated outputs, distributions, platform matrix or installed acceptance. Keep
#321 open for exact-commit branch/main `check` and `v1-supported-platform-matrix`
and the later combined maintainer installed acceptance.
