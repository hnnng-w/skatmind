# Session-native automatic Learning (Issue #314, S6)

**Current acceptance: S1–S6 are maintainer-accepted.** #314 and #315 are closed;
S6 installed acceptance completed on main
`08022a6def9f06891d99e1097c2bf0ba84d77039`. Earlier local/hosted/installed pending
statements below are preserved point-in-time records. [S7, Issue #316](automatic_historical_learning_s7_verification.md)
adds manual and managed Match Historical evidence; it does not authorize another
S5/S6 installed acceptance sequence or direct Session Historical/Finalize capture.

## Baseline and acceptance boundary

Expected/actual branch: `feat/314-automatic-session-learning`. Expected/actual
starting HEAD: `7eacaf250b7d7e1f23338d45a020a1a27557b3d2`. The initial worktree and
index were clean. No baseline was substituted. The initial read-only issue lookup
failed because #314 had not yet been created; the maintainer authorized the supplied
specification, then created [Issue #314](https://github.com/hnnng-w/skatmind/issues/314).
Its complete body and empty comment list were read before continuing. The scope and
baseline agreed. S1–S5, including #313's installed functional acceptance and bounded
performance/readability correction, are accepted baseline evidence.

Product code changes. This implements S6 of the
[automatic Learning integration contract](automatic_learning_integration_contract.md).
New exact-commit branch/main `check` and `v1-supported-platform-matrix`, followed by
narrow maintainer installed acceptance, remain required. Keep #314 and #208 open.
UAT-01 is not globally accepted; formal UAT-02–12 remain paused. Accepted #292–#313
scopes and #308's documentation acceptance remain intact. S7 and recommendation
adaptation remain subsequent work. Release preparation is not authorized.

## Delivered source and evidence boundaries

`session_recorded_coverage.py` shares the existing recorded-review selection with
the native adapter. It replays the strictly resumed complete Session document;
it never creates a Checkpoint. Source identity includes the canonical Checkpoint
tuple and accepted Log through the **complete persistence content fingerprint**.
State fingerprint, revision, filename and mtime cannot replace it.

Valid Live, Retrospective, partial, ended and no-own-perspective recordings remain
sources. Pending, future, diverged and ended-without-Play observations retain their
existing classifications. Eligible observed ancestors use greatest source revision,
then the first canonical saved variant on a tie. Original variants remain archived.
Recorded Plays, own Plays, eligible saved situations, retained executions and
distinct evidence-covered own decisions remain separate. Two execution families on
one decision cover one decision. Partial missing-Checkpoint coverage does not claim
that every snapshot is absent. Opponent Plays do not inflate missing own evidence.

`automatic_session_evidence.py` adds explicit private object codec **2** for
`session_source`, `session_decision` and `session_rollout`, with producer
`managed_session_recorded_review`, producer contract **1**, envelope version **1**
and supported Package `0.17.0`. Codec-1 opaque fixtures and unfamiliar producers,
contracts and versions remain unsupported. Known malformed payloads are corrupt.
The source retains the exact persistence document. The execution envelope retains:

* exact selected Checkpoint, accepted-Play observation, actor/seat/Player map,
  actual Card, accepted revision and before-Card cutoff;
* original frozen Request, observed-card review export and effective Request;
* native public options, including supplied-option presence, public Result,
  warnings/artifacts/provenance, and exact native Request/Result bytes/digests;
* genuine original internal invocation/execution captured during that same public
  call, using an invocation-local private `ContextVar`, for strict provenance
  source/linkage/final-serialization validation;
* rollout derivation v1/v2, settings, supplements and original method outcome.

The actual producer still executes `GuidedFrontendExecutionV1` through the public
boundary. The private observer adds no public option, signature, schema field or
Result field. Admission reconciles its native tuple and original internal context;
it never fabricates an internal execution from Result JSON or constructs a Match
Report. Existing native saved-method acceptance determines supported ordinary
methods; default Immediate, explicit Immediate, bounded Search and Auto are covered
by genuine fixtures. Separate whole-game review retains its existing methods and
settings. Current-position and Session Historical executions are not archived here.

Capture follows the existing source/context/attempt publication guards. It receives
the **local attempted execution**, including an incomplete rollout after a complete
one. The earlier completed display survives; the incomplete execution is separately
retained. Native rollout admission additionally checks typed aggregate arithmetic,
legal candidates, actual-card comparison, derivation and method/fallback boundaries.
Exact execution identity is separate from elapsed-normalized semantic identity.

One bounded pending Session save binds the original execution and source. Retry
performs dependency publication and manifest CAS only. Superseded retries reject.
An error after replacement is classified from authoritative storage; it does not
roll back a committed archive or trigger another analysis. Strict restart restores
native evidence/downloads under fresh archive-owned capabilities without opening
the Session, analyzing it or collecting Checkpoints.

## Coherent mixed generation and lifecycle

`automatic_session_inventory.py` extends the complete bounded direct-child inventory
to Sessions. Both family roots, every candidate's fresh bytes and every invalid,
unsupported, duplicate or excluded entry participate in freshness. An incomplete,
inaccessible, capped or racing scan is a conflict, not deletion proof. Duplicate
managed Session identities are excluded even when their bytes are equal.

Logical identities remain family-qualified and source-local. Matching names, seats,
literal Player/Game IDs or similar cards do not merge Sessions with Matches. The
existing archive's explicit unverified cross-source Game claims block both endpoints
as ambiguous. No general origin-proof validator or identity-management UI is added;
unverified claims never become trusted bindings.

`automatic_mixed_preparation.py` introduces **generation object codec 3**, producer
`automatic_mixed_preparation`, recipe version **1**. Codec-2 Match-only semantic
admission stays strict and remains the path for a Match-only inventory. Mixed recipes
explicitly name Session adapters and bind the native review alongside the Match
slice. There is one outer current/previous generation and one originating attempt.
Preparation stays outside Product locks; dependencies precede one manifest CAS.
Post-commit reconstruction is explicit, and unchanged updates reuse without preparing
or writing. Superseded work cannot claim an identical generation committed by a
different attempt as its own publication.

The outer membership revision and `match_catalog_revision` are separate. Session-only
changes do not advance the Match Catalog or alter the ten canonical Match downloads
when the selected Match inputs/evidence are unchanged. Sessions never enter Match
Dataset, Teacher, Tactical/Coaching qualification or debrief builders. Session-only
review needs no fabricated Match and is displayed even with an empty Match slice.
Independent manual collections retain their owners, selected copies and persistence.

Accepted Session replacements and deletion use the saved-source barrier. Directory
epochs invalidate mixed inventory operations even after byte restoration. Weak,
per-recording epochs protect native execution/publication and final delivery without
invalidating a completed Session Result when an unrelated Session is saved/deleted.
Correction replaces the current contribution; old executions remain bound to their
original full source version. Confirmed deletion hides affected old aggregates.

The service retains **one owner-scoped delivery receipt**: archive admission plus
its complete mixed source capture. Every hit rereads indexed object bytes, manifest,
storage inventory and all live candidate bytes. Both accepted-write epochs and owned
root identities are checked. The combined capture stays within **64 objects/candidates
and 16 MiB**; larger or changed inputs take strict admission. There is no TTL,
metadata-only authority, persisted cache or repeated typed admission on unchanged
bounded hits. HTML, language returns, recording actions and downloads keep the
original binding through final response authorization and dependency pins.

## Native UI and maintenance

The bilingual Learning navigation/Home and automatic scope now include Matches and
Sessions. Match and Session coverage remain labelled separately. Session source,
own-decision and comparison pages show concrete missing evidence and the original
method/objective/assumptions. Full fingerprints remain in closed native details.

| Method | Private route | Purpose |
| --- | --- | --- |
| GET | `/sessions/saved-analyses` | Discover retained Session analyses after restart |
| GET | `/sessions/saved-analyses/{capability}` | Exact native comparison or availability |
| GET | above + `/request.json` or `/result.json` | Exact native bytes/filenames |
| POST | `/sessions/retry-saving` | Exact attempt's persistence-only retry |
| GET | `/learning/automatic/{view}/session/source/{index}` | Captured Session coverage |
| GET | `/learning/automatic/{view}/session/decision/{index}` | Recorded own decision and evidence links |
| GET | `/learning/automatic/{view}/session/evidence/{index}` | Retained comparison |
| GET | above + `/request.json` or `/result.json` | Generation-bound native download |

The existing `/learning/automatic/recording` action additionally accepts a bounded
Session decision selector and opens only its exact current recording. Existing Match
URLs retain their meaning. Saved lists are family-filtered and include a return to
automatic Learning. Native forms work without JavaScript; enhanced language returns
preserve the original view rather than recapturing a newer tab's view.

Exclusion/re-inclusion, old-evidence removal and obsolete source-history release
reuse the existing exact preview, original token and one-use confirmation. Retained
executions, bindings, readers and current sources protect their dependencies. Removal
is reference-first, dependent generations retire coherently, and partial failures
retain their actual classification. Consent clears on language restoration. A preview
is effect-free only when **both** its physical list is empty and its complete manifest
is unchanged; a blocked source release does not disable permissible orphan cleanup.

Measured source inventories: **80 POST routes, 132 forms, 2,270 keys per locale**;
nine canonical app routes, 72 packaged Schemas and ten Match prepared downloads.
Existing Session/Checkpoint, Match and manual collection bytes, native exports,
Public APIs/schemas, dependency versions and recommendation methods are preserved.

## Local verification

Development interpreter: **CPython 3.13.7**, absolute path
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.
The ambient `python` was the Windows Store alias, so validation uses `py -3.13` and
the PowerShell function binding below. Every validation tool invocation used
**7,200,000 ms** timeout. Evidence, caches, fixtures, browser profiles and screenshots
are outside the repository under `$E` below. No real managed/installed data was used.

Final pytest union: **72 complete modules, 1,546 distinct tests: 1,539 passed and
seven skipped**, including **48 new passing S6 tests**. Across 19 pytest invocations:
**2,262 passing executions, 12 intermediate failed executions, two collection-error
entries and nine skip events**. Collection errors are not additional distinct tests.
All intermediate failures were resolved. The seven distinct skips are unavailable
actual Windows symlink privileges: three store cases, one automatic inventory case,
one managed-item case, one manual direct-entry case and one recording-deletion case.
Actual Windows junction checks passed.

The inventory follows changed callers: native Session producer/export/persistence,
archive admission, automatic preparation/delivery/lifecycle, saved-family navigation,
managed creation/correction/deletion, public execution's private observer, language,
forms, Home, source packaging, CLI imports and manual-collection compatibility.
Unchanged solver regression suites and distribution builds are not substituted for
these affected modules. The three affected exclusive modules run only after parallel
workers exit. The standalone Corpus transport is unchanged; its in-memory preparation
and manual integration callers are covered by the listed source tests.

### Complete module inventory and actual commands

The following array is the exact 69-module ordered parallel invocation, also retained
in `$E\314-affected.ps1`:

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$env:PYTHONDONTWRITEBYTECODE = '1'
$Affected = @(
  'tests/test_automatic_session_evidence.py',
  'tests/test_automatic_session_learning.py',
  'tests/test_automatic_session_lifecycle.py',
  'tests/test_automatic_session_web.py',
  'tests/test_session_evidence_retention.py',
  'tests/test_automatic_learning_contracts.py',
  'tests/test_automatic_learning_store.py',
  'tests/test_automatic_learning_lifecycle.py',
  'tests/test_automatic_learning_managed_service.py',
  'tests/test_automatic_match_evidence.py',
  'tests/test_automatic_match_rollout_evidence.py',
  'tests/test_match_evidence_retention.py',
  'tests/test_match_rollout_retention.py',
  'tests/test_saved_match_analyses_web.py',
  'tests/test_saved_match_rollouts_web.py',
  'tests/test_automatic_match_learning.py',
  'tests/test_automatic_match_learning_evidence.py',
  'tests/test_automatic_learning_delivery_receipt.py',
  'tests/test_automatic_learning_language_work.py',
  'tests/test_automatic_learning_entry_language.py',
  'tests/test_automatic_learning_source_release.py',
  'tests/test_automatic_learning_maintenance_readability.py',
  'tests/test_automatic_learning_ui.py',
  'tests/test_automatic_learning_ui_evidence.py',
  'tests/test_session_recorded_review.py',
  'tests/test_session_recorded_review_web.py',
  'tests/test_session_whole_game_review_web.py',
  'tests/test_session_rollout_review.py',
  'tests/test_session_persistence.py',
  'tests/test_session_persistence_codec.py',
  'tests/test_session_persistence_contracts.py',
  'tests/test_session_decision_observation.py',
  'tests/test_session_checkpoint_review.py',
  'tests/test_public_session_files.py',
  'tests/test_session_cli.py',
  'tests/test_session_declaration_correction.py',
  'tests/test_session_declaration_correction_web.py',
  'tests/test_recording_deletion_files.py',
  'tests/test_recording_deletion_lifecycle.py',
  'tests/test_recording_deletion_web.py',
  'tests/test_profile_driven_session_creation.py',
  'tests/test_profile_driven_creation_web.py',
  'tests/test_unified_local_app_contracts.py',
  'tests/test_unified_local_app_managed_items.py',
  'tests/test_unified_local_app_web.py',
  'tests/test_public_python_api_v1.py',
  'tests/test_public_api_contracts.py',
  'tests/test_guided_frontend_execution.py',
  'tests/test_app_cli.py',
  'tests/test_frontend_localization_foundation.py',
  'tests/test_complete_frontend_localization.py',
  'tests/test_frontend_validation_preservation.py',
  'tests/test_frontend_language_switching.py',
  'tests/test_language_switch_context.py',
  'tests/test_language_view_continuity.py',
  'tests/test_task_first_language_preservation.py',
  'tests/test_task_first_stateful_rendering.py',
  'tests/test_bilingual_home_information_architecture.py',
  'tests/test_direct_match_evidence.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_recorded_review_navigation.py',
  'tests/test_analysis_download_details.py',
  'tests/test_recorded_decision_context_web.py',
  'tests/test_learning_direct_entry.py',
  'tests/test_learning_direct_entry_web.py',
  'tests/test_learning_report_attachment_web.py',
  'tests/test_learning_corpus_web_core.py',
  'tests/test_skatmind_rename.py'
)
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\314-affected" --junitxml "$E\314-affected.xml"
py -3.13 -m pytest tests/test_early_rejection_observer.py tests/test_unified_rejection_transport.py tests/test_match_analysis_action_placement.py -q -p no:cacheprovider --basetemp "$E\314-exclusive" --junitxml "$E\314-exclusive.xml"
```

Initial focused invocations used `py -3.13 -m pytest` with the complete modules and
flags below, followed by `-p no:cacheprovider --basetemp "$E\314-<prefix>"
--junitxml "$E\314-<prefix>.xml"`. `P` means exactly
`-q -n 2 --dist=loadfile --max-worker-restart=0`; `X` means `-x -q`.
`N`, `M`, `L`, `W`, `R` abbreviate the five new modules in the first five array rows
(native evidence, mixed Learning, lifecycle, HTTP, retention).

| Prefix | Complete modules / flags | Actual result | Console seconds |
| --- | --- | --- | ---: |
| native-1 | N / X | 1 passed, 1 failed: fixture used `world_count` instead of `requested_worlds` | 6.45 |
| native-2 | N, `test_session_recorded_review.py` / X | 7 passed, 1 failed: negative fixture supplied the unchanged empty presence list | 10.07 |
| core-1 | N, `test_session_recorded_review.py`, `test_automatic_match_learning.py` / X | 92 passed, 1 failed: old test inspected a single lock instead of both barriers; one diagnostic thread warning | 98.07 |
| mixed-1 | M / X | 1 failed: private inventory field needed the exact `SourceKeyV1` type | 2.43 |
| mixed-2 | M / X | 8 passed | 50.34 |
| focused-1 | N, M, W, R / P | 20 passed; 1 collection error: renderer imported from the wrong module | 49.94 |
| web-1 | W / X | 1 collection error: retry route missing from server registry | 1.34 |
| web-2 | W / X | 1 failed: fixture submitted `locale` instead of native `language` | 1.73 |
| focused-2 | W, M, R, N, `test_app_cli.py` / P | 51 passed, 2 failed: default Immediate caption assumed an optional settings field | 53.70 |
| web-diagnosis | W / X | 1 failed: direct caption reproduction of that defect | 6.86 |
| focused-3 | W, L, N / P | 26 passed, 1 failed: older attempt misclassified a newer identical commit | 58.09 |
| affected | Exact array above / P | 1,464 passed, 3 failed, 7 skipped | 2,886.43 |
| corrected | Exact 22-module list below / P | 430 passed, 2 skipped | 1,682.11 |
| exclusive | Three complete serial modules above / `-q` | 68 passed | 75.84 |
| final-boundaries | W, L / P | 17 passed, including native retry and Report-before-source release | 156.02 |
| partial-coverage | L / `-q` | 12 passed after removing an inaccurate all-snapshots-missing sentence | 48.44 |
| final-copy | `test_frontend_localization_foundation.py`, `test_complete_frontend_localization.py` / `-q` | 26 passed after correcting shared empty-list/source-release scope copy | 2.54 |
| home-catalog | `test_bilingual_home_information_architecture.py` / `-q` | 14 passed; new German expectation resolved from the catalog | 0.49 |
| entry-copy | Same complete modules as final-copy / `-q` | 26 passed after the final missing-review entry copy included all saved recordings | 2.45 |

The affected pass's three failures were an old scalar-epoch expectation, the old
Match-only scope sentence, and unrelated Session deletion expiring native downloads.
The first two expectations were updated; the third was corrected with per-recording
epochs alongside the shared inventory barrier. The corrected pass also verifies the
single bounded combined receipt. Its exact command was:

```powershell
py -3.13 -m pytest tests/test_automatic_match_learning.py tests/test_automatic_match_learning_evidence.py tests/test_automatic_learning_delivery_receipt.py tests/test_automatic_learning_language_work.py tests/test_automatic_learning_entry_language.py tests/test_automatic_learning_source_release.py tests/test_automatic_learning_maintenance_readability.py tests/test_automatic_learning_ui.py tests/test_automatic_learning_ui_evidence.py tests/test_automatic_session_learning.py tests/test_automatic_session_lifecycle.py tests/test_automatic_session_web.py tests/test_session_evidence_retention.py tests/test_session_recorded_review.py tests/test_session_recorded_review_web.py tests/test_session_whole_game_review_web.py tests/test_session_persistence.py tests/test_public_session_files.py tests/test_recording_deletion_files.py tests/test_recording_deletion_lifecycle.py tests/test_recording_deletion_web.py tests/test_unified_local_app_web.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\314-corrected" --junitxml "$E\314-corrected.xml"
py -3.13 -m pytest tests/test_automatic_session_web.py tests/test_automatic_session_lifecycle.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider --basetemp "$E\314-final-boundaries" --junitxml "$E\314-final-boundaries.xml"
py -3.13 -m pytest tests/test_automatic_session_lifecycle.py -q -p no:cacheprovider --basetemp "$E\314-partial-coverage" --junitxml "$E\314-partial-coverage.xml"
py -3.13 -m pytest tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py -q -p no:cacheprovider --basetemp "$E\314-final-copy" --junitxml "$E\314-final-copy.xml"
py -3.13 -m pytest tests/test_bilingual_home_information_architecture.py -q -p no:cacheprovider --basetemp "$E\314-home-catalog" --junitxml "$E\314-home-catalog.xml"
py -3.13 -m pytest tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py -q -p no:cacheprovider --basetemp "$E\314-entry-copy" --junitxml "$E\314-entry-copy.xml"
```

Ruff diagnosis found 43 initial formatting/import issues, then three remaining
findings, then seven findings after later edits. Changes were applied through
patches; the two `ruff check --select I --diff` invocations did not edit files.
The first catalog patch failed context matching without changing files. A repeated
file section in an early patch omitted the intended server retry-route edit; the
collection failure exposed it and the corrected registry passed. No unresolved
test failure or warning remains in the final affected evidence. Final Quick and
file-review results are recorded in the completion receipt below.

### Execution and browser accounting

The final 48 new tests require **36 genuine bounded native fixture executions** in
one complete pass. Repeated/intermediate new-test invocations account for **138**
such executions; the failed wrong-setting and language-form fixtures stopped before
execution. These counts concern the new S6 fixtures, not the pre-existing regression
fixtures in the other modules. Automatic Update does no card analysis. Wire mutations
and injected pre-write/post-commit failures are controlled negative fixtures; the
incomplete-after-complete case is a genuine one-transition-budget-limited execution.
Save-only retry asserts no evaluator call and preserves the actual attempt.

Two bounded source-tree probes used headless **Edge 156.0.4314.58**, with synthetic
data only, native German/English without JavaScript and an enhanced language return.
The initial probe passed in **37.442 s**. The final probe, repeated after the receipt,
per-recording epoch and truthful navigation-copy corrections, passed in **55.897 s**.
No latency comparison or guarantee is inferred; the final probe overlapped a test
invocation. Each produced six screenshots. Initial result focus was `learning-result`;
keyboard activation had a visible **3px** outline. The 1,100px/390px viewport checks
showed no horizontal overflow. Narrow viewports are not browser-zoom evidence.

```powershell
py -3.13 "$E\314-browser.py" "$E\314-browser-1"
py -3.13 "$E\314-browser.py" "$E\314-browser-final"
py -3.13 "$E\314-accounting.py"
```

Each probe performed two intentional native fixture analyses, two fixture recording
saves, one explicit mixed Learning preparation and three deliberate language Profile
saves. Archive temporary-write accounting per probe: **two sources, two Reports,
one generation and four manifests** (initial manifest, two execution commits and
one generation commit). Source reuse caused no extra source-object publication.
Directory/coordination creation and immutable publication links are not extra
analysis/manifest writes. Passive navigation, disclosures, language return and
saved access performed **zero analysis, preparation, import, cleanup or archive
writes**. Recording bytes stayed unchanged. The HTTP suite separately verifies
restart capabilities, native download equality and final-delivery races.

Evidence resides in `$E\314-browser-final\evidence.json`, its six PNGs, the earlier
probe directory, all listed JUnit XML files and `$E\314-accounting.json`. The actual
producer module path is this checkout's `src/skatmind/app_web/session_recorded_review.py`.
The portable fixture generation below was source-tested separately: three recording
saves, zero analyses. None of this is installed acceptance.

## Later narrow maintainer installed scenario — not performed here

After both exact-commit hosted gates, use the maintainer's independently installed
runtime from an external directory and a **new disposable data home**. Reuse accepted
S5 evidence; do not repeat its full matrix. Record exact build/commit, installed module
path, interpreter and browser. Keep one accepted synthetic S5 Match and independent
manual collection, and capture their bytes and the ten Match-download digests before
adding Sessions.

Create portable fixtures with the following external script and the installed
interpreter. Its destination must be a new child of an existing temporary directory.
This script was checked against the source tree as `$E\314-installed-fixtures.py`;
it uses existing Session APIs and creates **no analysis or distribution**:

```python
import sys
from pathlib import Path
import skatmind.api.v1.session as api
from skatmind.api.v1.session.files import save_session_file
from skatmind.game_declaration import GameDeclaration

out = Path(sys.argv[1])
out.mkdir()
players = tuple(api.SessionPlayerV1(player_id=identifier, player_label=label, seat=seat)
    for identifier, label, seat in (("s6-a", "Alice", "forehand"),
                                   ("s6-b", "Bob", "middlehand"),
                                   ("s6-c", "Carol", "rearhand")))
def applied(state, command):
    result = api.apply_session_command(state, command).value
    assert result.status == "applied"
    return result.state
for identifier, keep in (("s6-own-decision", True), ("s6-no-checkpoint", False)):
    state = api.create_session(session_id=identifier, players=players,
                               capture_mode="live", local_player_id="s6-a").value
    for card in ("CJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7", "SA", "S10"):
        state = applied(state, api.RecordSessionDealtCardCommandV1(
            expected_revision=state.revision, destination="player_hand", player_id="s6-a", card=card))
    state = applied(state, api.SetSessionDeclarerCommandV1(expected_revision=state.revision,
                                                         declarer_player_id="s6-a"))
    state = applied(state, api.SetSessionDeclarationCommandV1(expected_revision=state.revision,
        declaration=GameDeclaration(game_type="grand", hand_game=True, bid_value=24)))
    exported = api.export_session_position_request(state, api.SessionPositionExportOptionsV1(
        sample_count=1, random_seed=0, use_basic_opponent_strategy=True,
        recommendation_method=None, bounded_search_settings=None)).value
    checkpoint = api.build_session_decision_checkpoint(state=state, position_export=exported).value
    state = applied(state, api.RecordSessionPlayCommandV1(expected_revision=state.revision,
                                                         player_id="s6-a", card="CA"))
    document = api.build_session_persistence_document(state,
        decision_checkpoints=(checkpoint,) if keep else ()).value
    assert save_session_file(out / (identifier + ".json"), document,
                             expected_content_fingerprint=None).value.status == "saved"
state = api.create_session(session_id="s6-no-perspective", players=players,
                           capture_mode="retrospective", local_player_id=None).value
document = api.build_session_persistence_document(state).value
assert save_session_file(out / "s6-no-perspective.json", document,
                         expected_content_fingerprint=None).value.status == "saved"
```

1. Import these three valid files through the Session advanced JSON transfer
   (`/sessions/import`). The missing-Checkpoint file is constructed through the
   supported persistence builder, not by corrupting JSON. Open Learning and use
   **Create Learning review / Update Learning review**. Expected Session counts:
   **3 Sessions, 2 recorded Plays, 2 own Plays, 1 eligible situation, 1 missing
   Checkpoint, 1 no-perspective Session, 0 covered decisions, 0 executions**.
2. Open `s6-own-decision`. Its **already recorded** own decision is **Alice, Trick 1,
   Card 1, Clubs Ace (CA)** at revision **13**, from the revision-12 Checkpoint.
   Use **Review decision** (`/sessions/review-decision`) once, then **Evaluate whole
   game** (`/sessions/review-whole-game`) on that same recorded row, with played-game
   goal, one requested world and seed 0. Do not record CA again. Retain both native
   Request/Result downloads. After explicit Learning Update, expect **2 executions
   covering 1 decision**; all other Session counts remain unchanged.
3. Stop and restart the installed process. Without opening a Session, follow
   **Saved Session analyses** at `/sessions/saved-analyses`, retrieve both families
   and compare all four native byte payloads. Old capabilities expire; new ones have
   identical contents. Automatic review says reconstruction is needed. Explicit
   Update rebuilds with **zero analyses**, preserving those counts and Match digests.
4. Correct history using the existing **Undo to this revision** control
   (`/sessions/undo`), targeting revision **12** of `s6-own-decision`. Update. Expected
   Session counts become **3 / 1 recorded / 1 own / 0 eligible / 1 missing /
   1 no-perspective / 0 covered / 0 current executions**. The two earlier executions
   remain historical saved analyses, bound to revision 13. Prior recording controls
   must reject instead of opening the corrected version under old authority.
5. In automatic Included data, use **Preview source exclusion** for `s6-own-decision`,
   confirm, and Update: **2 Sessions**, with the other counts from step 4 unchanged.
   **Preview source re-inclusion**, confirm and Update restores **3**. Delete that
   Session through the recording deletion UI; affected old aggregates disappear.
   Update again gives **2 Sessions**, one recorded own Play with a missing Checkpoint
   and one no-perspective Session. Historical native analyses remain accessible.
6. Optionally preview **removal of old analysis evidence**: its two executions must
   be named before consent. Source history remains protected while Reports reference
   it. After explicit Report removal, preview **release of obsolete source history**;
   use the actual displayed exact version/file counts, including the original and
   Undo versions. Confirm only that preview. No recording/manual collection is deleted
   by archive maintenance. Switching language clears checked destructive consent.
7. Exercise changed Session source/decision/comparison and saved-analysis routes in
   both languages without JavaScript, then one enhanced language return. Verify the
   original route/view, keyboard focus, initial result focus and narrow readability.
   Check that unchanged Match inputs still produce the original ten bytes and the
   independent manual collection retains its bytes/selection. Count language Profile
   saves separately. This narrow scenario does not accept global UAT-01 or resume
   formal UAT-02–12.

## Final file inventory and completion receipt

Exactly **53 intended files**: **30 Product files**, **12 test files**, **10
documentation/instruction files**, and **one source-only packaging inventory update**.
All remain unstaged and uncommitted. New files are listed separately from modifications.

New (15):

```text
docs/automatic_session_learning_s6_verification.md
src/skatmind/app_web/automatic_session_inventory.py
src/skatmind/app_web/session_evidence_retention.py
src/skatmind/app_web/session_learning_navigation.py
src/skatmind/app_web/session_learning_rendering.py
src/skatmind/automatic_mixed_preparation.py
src/skatmind/automatic_session_evidence.py
src/skatmind/automatic_session_rollout_validation.py
src/skatmind/private_execution_capture.py
src/skatmind/session_recorded_coverage.py
tests/test_automatic_session_evidence.py
tests/test_automatic_session_learning.py
tests/test_automatic_session_lifecycle.py
tests/test_automatic_session_web.py
tests/test_session_evidence_retention.py
```

Modified (38):

```text
AGENTS.md
README.md
docs/automatic_learning_integration_contract.md
docs/automatic_learning_store.md
docs/automatic_match_learning_ui.md
docs/project_handoff.md
docs/roadmap.md
docs/session_recorded_decision_review.md
docs/v1_scope.md
scripts/validate_distribution_artifacts.py
src/skatmind/api/v1/execution.py
src/skatmind/app_web/automatic_learning_controller.py
src/skatmind/app_web/automatic_learning_http.py
src/skatmind/app_web/automatic_learning_rendering.py
src/skatmind/app_web/automatic_learning_routes.py
src/skatmind/app_web/automatic_match_learning.py
src/skatmind/app_web/contracts.py
src/skatmind/app_web/form_registry.py
src/skatmind/app_web/frontend_profile_operations.py
src/skatmind/app_web/language_context.py
src/skatmind/app_web/locales/de.json
src/skatmind/app_web/locales/en.json
src/skatmind/app_web/recording_deletion.py
src/skatmind/app_web/saved_match_analyses.py
src/skatmind/app_web/server.py
src/skatmind/app_web/session_frontend.py
src/skatmind/app_web/session_recorded_review.py
src/skatmind/automatic_learning_objects.py
src/skatmind/automatic_learning_store.py
src/skatmind/match_source_coordination.py
src/skatmind/session_persistence.py
tests/test_automatic_match_learning.py
tests/test_bilingual_home_information_architecture.py
tests/test_direct_match_evidence.py
tests/test_frontend_localization_foundation.py
tests/test_frontend_validation_preservation.py
tests/test_unified_local_app_contracts.py
tests/test_unified_local_app_web.py
```

Explicit `.\scripts\check.ps1 -Mode Quick` passed on development CPython **3.13.7** /
`Windows-11-10.0.26300-SP0`, exit **0**, total **6.105 s**: Ruff **0.365 s**,
packaged-schema parity **0.182 s**, input examples **5.136 s**.
Logs: `C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-e2fkqb7i`.
Checked source digest:
`28595d88b3d93c787daaaa4630b62ca840aed53c72f4438c0e7e7265bb44e130`.
Only documentation completion receipts followed Quick; Product code/tests did not
change afterward. Quick is partial validation, not hosted or installation acceptance.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode\314-pycache'
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
# Each new file also receives: git diff --no-index --check -- NUL <file>
git diff --cached --stat
git status --short --branch
git rev-parse HEAD
```

All changed/new files were reviewed; tracked and new-file whitespace checks passed.
The index is empty. Current HEAD remains the expected starting
`7eacaf250b7d7e1f23338d45a020a1a27557b3d2` on
`feat/314-automatic-session-learning`; exactly the intended 53 files remain unstaged.
No local Full, unrelated regression suite, distribution/UAT build or installation,
installed acceptance, real managed/UAT-data access, Actions trigger, Git publication,
GitHub comment, issue closure or release preparation was performed.

**Locally validated; new exact-commit hosted CI and narrow maintainer installed
acceptance pending. Keep #314 open.**

## Review correction follow-up at `ebb34a18` (2026-11-06)

### Baseline and historical CI

Expected/actual branch: `feat/314-automatic-session-learning`. Expected/actual
starting HEAD: `ebb34a18a7f53ee3fd06f8c99630e46095bb53e3`. The worktree/index were
clean after the maintainer's commit and push. There was no baseline deviation,
branch change, reset or replacement of existing work. Development interpreter:
CPython **3.13.7** at
`C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe`.

Read-only `gh run view` confirms [run 42207456689](https://github.com/hnnng-w/skatmind/actions/runs/42207456689)
completed successfully for that exact commit: **all 23 jobs succeeded**, including
`regression (ubuntu)`, `regression (windows)`, `check`, and
`v1-supported-platform-matrix`. This is preserved historical evidence for `ebb34a18`,
not acceptance of the subsequent corrections. The original implementation, local
checks, browser evidence and pending installed acceptance above are unchanged.
Issue #314 and the applicable instructions/contracts were read before correction.

### Pre-Product reproduction and confirmed corrections

All four findings were reproduced on the supported development interpreter before
Product edits. The two new regression modules initially exercised nine cases. Eight
exposed A/C/D; B's first fixture stopped at its own finite-JSON encoding error. The
private execution decoder returns tuples for sequences, so the independently built
semantic material needed conversion to JSON arrays. Correcting that fixture did not
weaken a Product validator. The subsequent B-only run reached native and full store
admission and confirmed B. No proposed finding was prevented by an existing validated
Product boundary once its valid wire preconditions were met.

| Finding | Actual pre-correction result | Corrected boundary and result |
| --- | --- | --- |
| A — Session-only cleanup | With unchanged Match source/evidence selection, catalog revision **2 → 1** after cleanup/restart. **All ten** Match downloads changed. This occurred both with a surviving Match-only previous descriptor and when both mixed descriptors retired. In the first captured case, canonical `player_catalog` SHA-256 changed from `22608805d022afae9dae7bcf2718fc51604d8faefb485cd130160a53eb27b66b` to `62cfaa24bd348bb3ea5794c4c597ae9e946d7cdd46c711ebd89d187135e9ea92`. | Versioned private Match membership continuity survives Session-dependent generation retirement. Restart keeps revision **2**, identical selected Match inputs, and **all ten identical native download bytes**, including Player Catalog fingerprint data. |
| B — contradictory rollout core | A genuine bounded rollout was captured, then only its core source fingerprint was replaced consistently in all retained Result/provenance/checkpoint copies. Native bytes/digest, semantic identity, envelope and manifest references were rebuilt. Existing execution-provenance validation passed; **native decoding accepted it and the store admitted it**. | Admission independently rebuilds the authoritative information view or pure unavailable-preparation identity from the frozen/effective Request. The same contradictory wire is rejected; the store classifies the execution as corrupt, refuses evidence access after restart, preserves bytes and executes no analysis. |
| C — malformed codec-3 inventory | Independently fingerprinted null and nested-array members caused **`AttributeError`** in direct admission, restarted service Inspect and Update. Delivered automatic GET returned **HTTP 500**. | An explicit per-element object check raises controlled **`ValueError`**. Inspect returns `excluded`; Update returns `failed`. Native GET recovery is **409** and the submitted stale Update form receives controlled **400**, localized in German/English. Archive bytes remain unchanged. |
| D — imprecise recording return | A valid recording with ten own decisions selected **decision 28, Player A/Alice, S10**. Both eligible and missing-Checkpoint actions redirected to `/sessions/current#recorded-decisions`, even though the exact target elements existed. | Eligible selection redirects to `/sessions/current#recorded-decision-28`; missing-Checkpoint selection redirects to `/sessions/current#session-play-28`. The emitted history action uses the existing history/correction label. Both locales verify the actual form, redirect, anchor-local Player/Card content and unchanged recording bytes, with analysis/preparation/archive writes forbidden. |

#### A: narrow persistence and compatibility support

The optional private `ManifestV1.match_basis` contains a version-1
`MatchSliceBasisV1`: same-space Match source membership and compatible Catalog/recipe
settings. It contains **no executed evidence, skipped situations or derived result
fingerprints** and cannot authorize a current result. The field is omitted when
absent, preserving canonical legacy manifest bytes and fingerprints. Manifest/storage
version `1`, generation codecs `2`/`3`, current-plus-previous limits, immutable object
formats and canonical Match export formats remain intact.

New generation publication captures this basis in the same manifest CAS. When an
explicit cleanup retires a legacy current generation without a basis, its strictly
admitted Match slice supplies the basis before retirement. Cleanup keeps its original
source-release eligibility, preview identity, reader protection, reference-first
removal and partial-failure semantics. The metadata adds no object-file dependency
on a Session and does not block its legitimate cleanup.

Basis references must remain closed, Match-only, unique by logical source and bound
to the same automatic space. Explicit release of a referenced Match source retires
the basis coherently. Evidence-only changes leave membership revision intact;
regressions include removal of Match evidence that retires both result descriptors.
Actual new Match membership still advances the retained revision during normal Update.
No Session evidence is rebound.

The legacy previous-descriptor fallback is used only after strict compatible
admission and an exact selected Match source/evidence match. Unrelated or unsupported
previous recipes do not supply continuity. An unsupported retained basis cannot seed
a rebuild. Neither a previous descriptor nor a retired mixed result is promoted
automatically; an explicit Update still prepares, checks current membership and
publishes the complete authorized generation.

#### B: independent pure core reconciliation

`automatic_session_rollout_validation.py` reuses the existing local-state,
declaration, continuation/public-hand and live Search-information-view builders.
For a normal prepared view it recomputes the existing
`skatmind.whole_game_rollout.source.v1` fingerprint. For a genuinely unavailable
root it reuses the pure `unavailable_rollout_root` identity/status boundary. It checks
source classification, information cutoff, Game type, local actor party and prepared
Position facts against that authoritative Request context.

The decoder retains all existing provenance, arithmetic, comparison, derivation and
byte checks. It does not construct a Match Report or call a rollout evaluator.
Positive ordinary, complete, work-budget-incomplete, unavailable-settlement and
supplemented derivation/provenance cases pass. The consistent negative wire keeps the
Session, Checkpoint, accepted observation, review export, Request, options and
invocation fixed; its source/Result copies are not rejected merely for an unrelated
checksum discrepancy.

#### C/D: bounded transport changes

The codec-3 correction checks inventory members before calling `.get`; it adds no
broad catch-all and leaves codec-2 and unsupported-future dispatch unchanged.
The navigation correction only selects the appropriate existing fragment and
existing localized action label. Source/version ownership, original view bindings
and final-delivery checks remain in place. Routes, form definitions and translation
catalog counts stay **80 / 132 / 2,270**. No shared active-context redesign, new schema,
new recommendation method or dependency change is introduced.

### Exact correction inventory

**10 intended files; Product code changes.**

Modified:

```text
src/skatmind/app_web/automatic_match_learning.py
src/skatmind/app_web/session_learning_navigation.py
src/skatmind/automatic_learning_contracts.py
src/skatmind/automatic_learning_store.py
src/skatmind/automatic_mixed_preparation.py
src/skatmind/automatic_session_rollout_validation.py
docs/automatic_session_learning_s6_verification.md
```

New:

```text
src/skatmind/automatic_match_continuity.py
tests/test_automatic_session_review_corrections.py
tests/test_automatic_session_review_corrections_web.py
```

The original S6 implementation, accepted #292–#313 behavior, native exports,
Session/Checkpoint/Match/manual collection persistence and public APIs remain intact.

### Correction validation inventory and actual commands

Every validation tool invocation used **7,200,000 ms** timeout. Logs, JUnit, disposable
data and the operation-accounting plugin are outside the repository under `$E`.
The inventory follows the changed private manifest/store and recipe callers, native
Session admission/retention, automatic delivery/maintenance, native Session returns,
CLI import boundary and source-only packaging. It does not repeat the former 72-module
inventory or unrelated solver suites. Existing automatic cleanup/manual-independence
tests exercise the preserved manual boundary.

The complete set is **31 parallel modules plus one affected exclusive module**:

```powershell
$E = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPATH = "$E;$env:PYTHONPATH"
$Affected = @(
  'tests/test_automatic_session_review_corrections.py',
  'tests/test_automatic_session_review_corrections_web.py',
  'tests/test_automatic_learning_contracts.py',
  'tests/test_automatic_learning_store.py',
  'tests/test_automatic_learning_lifecycle.py',
  'tests/test_automatic_learning_managed_service.py',
  'tests/test_automatic_match_learning.py',
  'tests/test_automatic_match_learning_evidence.py',
  'tests/test_automatic_session_evidence.py',
  'tests/test_automatic_session_learning.py',
  'tests/test_automatic_session_lifecycle.py',
  'tests/test_automatic_session_web.py',
  'tests/test_session_evidence_retention.py',
  'tests/test_automatic_learning_delivery_receipt.py',
  'tests/test_automatic_learning_language_work.py',
  'tests/test_automatic_learning_entry_language.py',
  'tests/test_automatic_learning_source_release.py',
  'tests/test_automatic_learning_maintenance_readability.py',
  'tests/test_automatic_learning_ui.py',
  'tests/test_automatic_learning_ui_evidence.py',
  'tests/test_saved_match_analyses_web.py',
  'tests/test_saved_match_rollouts_web.py',
  'tests/test_match_evidence_retention.py',
  'tests/test_match_rollout_retention.py',
  'tests/test_automatic_match_evidence.py',
  'tests/test_automatic_match_rollout_evidence.py',
  'tests/test_session_whole_game_review_web.py',
  'tests/test_recorded_review_navigation.py',
  'tests/test_session_recorded_review_web.py',
  'tests/test_app_cli.py',
  'tests/test_packaging_and_distribution.py'
)
py -3.13 -m pytest @Affected -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider -p review314_accounting -o junit_logging=all --basetemp "$E\314-review-affected" --junitxml "$E\314-review-affected.xml"
py -3.13 -m pytest tests/test_unified_rejection_transport.py -q -p no:cacheprovider -o junit_logging=all --basetemp "$E\314-review-exclusive" --junitxml "$E\314-review-exclusive.xml"
```

The exclusive module ran after both workers exited. The other exclusive modules
were not affected: no early-body observer, standalone Corpus transport or Match
action-placement change was made. Packaging checks exercised source metadata and
assertion snippets; no distribution was built or installed.

Earlier invocations used these exact commands:

```powershell
py -3.13 -m pytest tests/test_automatic_session_review_corrections.py tests/test_automatic_session_review_corrections_web.py -q -p no:cacheprovider -o junit_logging=all --basetemp "$E\314-review-red" --junitxml "$E\314-review-red.xml"
py -3.13 -m pytest tests/test_automatic_session_review_corrections.py -k consistent_false_core -q -p no:cacheprovider -o junit_logging=all --basetemp "$E\314-review-b-red" --junitxml "$E\314-review-b-red.xml"
py -3.13 -m pytest tests/test_automatic_session_review_corrections.py tests/test_automatic_session_review_corrections_web.py tests/test_automatic_session_evidence.py -q -p no:cacheprovider -o junit_logging=all --basetemp "$E\314-review-focused-1" --junitxml "$E\314-review-focused-1.xml"
py -3.13 -m pytest tests/test_automatic_session_review_corrections.py tests/test_automatic_session_review_corrections_web.py tests/test_automatic_learning_contracts.py tests/test_automatic_learning_lifecycle.py tests/test_automatic_session_learning.py -q -n 2 --dist=loadfile --max-worker-restart=0 -p no:cacheprovider -o junit_logging=all --basetemp "$E\314-review-focused-2" --junitxml "$E\314-review-focused-2.xml"
```

| Invocation | Actual result | Console seconds |
| --- | --- | ---: |
| Pre-Product red reproductions | 9 failures: eight confirmed A/C/D cases, one B fixture encoding error | 32.66 |
| Corrected B wire, still before Product edits | 1 expected failure, 4 deselected; contradictory identity admitted | 10.20 |
| First corrected focused pass | 28 passed | 72.83 |
| Expanded corrected focused pass | 115 passed | 227.64 |
| Complete 31-module affected pass | **690 passed, 4 skipped** | **3,701.70** |
| Complete exclusive module | **37 passed** | **46.55** |

Final union: **32 complete modules, 731 distinct tests: 727 passed and four skipped**,
including **27 new passing correction tests**. Across the six pytest invocations,
there were **870 passing executions, ten failed executions and four skip events**.
The failures were confined to the pre-Product reproduction/fixture runs; all corrected
passes succeeded. The original English HTTP case IDs were normalized to their later
explicit `en` parameter when reconciling repeats; the additional `de` cases are
distinct. Repeated tests are not additional coverage.

The four skips are this Windows account's existing actual-symlink privilege limits:
three automatic-store tests and the automatic Match inventory file-symlink case.
Actual Windows junction cases passed. There were no warnings or unresolved affected
failures in the corrected passes. Standalone targeted Ruff found 12 formatting/import
issues, then two remaining line-length findings; all were corrected with patches.
The import-only `ruff check --select I --diff` was read-only. Final Quick is recorded
below. The timings are actual test totals, not a performance benchmark or latency claim.

### Delivered HTTP and operation accounting

The final new tests use genuine bounded fixture executions, not reconstructed
substitute executions. External `review314_accounting.py` wraps the actual entry
points without changing returned values, only while the new correction cases run.
Its two successful worker receipts are:

* `$E\314-review-operations-32076.json`
* `$E\314-review-operations-15480.json`

For the **27 new cases in the complete affected pass**, actual counters are:

| Operation | Count and scope |
| --- | --- |
| Intentional fixture analyses | **4**: one ordinary Match and three native Session executions |
| Explicit/fixture Learning preparations | **40**, including original/rebuilt generations and negative-wire setup |
| Fixture recording saves | **36** |
| Deliberate fixture language Profile saves | **8**, before the native HTTP checks |
| Successful archive temporary writes | **35 sources, 2 Reports, 44 generations, 80 manifests** |

These include deliberately published malformed/future-wire fixture objects and
initial manifests. Immutable publication links, coordination-file creation and
cleanup unlinks are not additional temporary writes. The cases explicitly commit
five cleanup previews and perform four disposable Session source deletions. They
never access real managed or installed data.

Admission/restart rejection preserves all archive JSON bytes. Both localized recovery
paths prohibit preparation, and exact later-decision navigation prohibits analysis,
preparation and archive writes while asserting unchanged recording bytes. Each native
HTTP case has only its one setup preparation; the subsequent failed Update/recovery
or navigation causes none. Existing save-only retry, receipt bounds/exact-byte
invalidation and manual-independence modules pass unchanged.

No additional browser probe or broad performance run was performed. These are actual
delivered loopback HTTP/form/HTML checks in both locales, not browser zoom or installed
acceptance. The original S5/S6 browser evidence remains historical evidence and is not
recast as a browser acceptance of these corrected fragments. The later narrow installed
scenario should additionally exercise a later eligible own decision and a missing-
Checkpoint history return, plus the A cleanup-before-Update/restart ordering.

Accounting is reconciled by `$E\314-review-accounting.py` into
`$E\314-review-accounting.json`. Original pre-correction stdout, outcomes and durations
remain in the named JUnit files. The successful CI run at `ebb34a18` remains separate
from every local correction result here.

### Correction completion gate

Final Quick, whitespace/file review and unchanged checkout identity are recorded in
the following completion receipt. New exact-commit branch/main `check` and
`v1-supported-platform-matrix`, then narrow maintainer installed acceptance, remain
required. Keep #314 and #208 open; UAT-01 is not globally accepted and formal UAT-02–12
remain paused. S7 and recommendation adaptation remain later work. Release preparation
is not authorized.

#### Correction completion receipt

Explicit `.\scripts\check.ps1 -Mode Quick`
passed on development CPython **3.13.7** / `Windows-11-10.0.26300-SP0`, exit **0**,
reported total **25.591 s**. Stages: Ruff **0.333 s**, packaged-schema parity
**0.126 s**, input examples **4.153 s**. Logs:
`C:\Users\Henning-DT\AppData\Local\Temp\skatmind-check-i5l443d2`.
Checked source digest:
`4aa5905f0d14ba8908dde13a6e0029c291f673c7f6e28bf40e9d2811697cbecb`.
Only this documentation receipt followed Quick; Product code and tests did not change.

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONPYCACHEPREFIX = 'C:\Users\HENNIN~1\AppData\Local\Temp\opencode\314-review-pycache'
function python { & 'C:\Users\Henning-DT\AppData\Local\Programs\Python\Python313\python.exe' @args }
.\scripts\check.ps1 -Mode Quick
git diff --check
git diff --no-index --check -- NUL src/skatmind/automatic_match_continuity.py
git diff --no-index --check -- NUL tests/test_automatic_session_review_corrections.py
git diff --no-index --check -- NUL tests/test_automatic_session_review_corrections_web.py
git diff --cached --stat
git status --short --branch
git rev-parse HEAD
```

All ten changed/new files were reviewed. Tracked and new-file whitespace checks
passed. The index remains empty; all ten intended changes are unstaged/uncommitted.
Expected/actual branch remains `feat/314-automatic-session-learning`; starting/current
HEAD remains `ebb34a18a7f53ee3fd06f8c99630e46095bb53e3`. There was no baseline deviation.

No local Full, unrelated suite, distribution/UAT build or installation, real managed/
installed UAT-data access, installed acceptance, Actions trigger, Git/GitHub publication
or release preparation was performed. The historical 23-job success at `ebb34a18`
does not cover these working-tree changes.

**Locally validated; new exact-commit hosted CI and narrow maintainer installed
acceptance pending. Keep #314 and #208 open.** UAT-01 is not globally accepted;
formal UAT-02–12 remain paused. S7 and recommendation adaptation remain later work.
