# Automatic Learning integration and evidence lifetime (Issue #308)

## 1. Status, decision and reading guide

**Status: documentation contract and recommended implementation sequence.** This
issue implements no automatic aggregation, Report persistence, source adapter or
new Learning output. The inspected baseline is
`a3899e650afafcc7bd29b04e8fc5f3da5be4ce61`, on
`docs/308-automatic-learning-integration-contract`, with a clean starting worktree.
The complete current [Issue #308](https://github.com/hnnng-w/skatmind/issues/308)
had no comments when inspected.

Implementation follow-up: Issue #309 implements only the private S1 storage
foundation described in [Automatic Learning private store](automatic_learning_store.md).
That separate implementation does not change #308's historical documentation-only
acceptance or claim completion of the automatic Learning workflow. S2–S7 remained
subsequent work in that historical S1 record. Issue #310 now implements the bounded
[ordinary Match retention stage S2](ordinary_match_analysis_retention.md), including
strict original-source admission, saved-analysis access and save-only retry.
Exact-commit hosted CI and installed targeted acceptance remain pending. S3–S7
remain later work; this does not implement automatic Learning review preparation.

Separate implementation follow-up: Issue #311 implements the bounded
[selected Match whole-game retention stage S3](match_rollout_analysis_retention.md).
S1/S2 are maintainer-accepted at its baseline; the preceding status statements are
historical records. S3 adds strict original rollout execution retention, separate
incomplete attempts, save-only retry and family-aware Saved analyses. S4–S7 remain
subsequent stages; new exact-commit CI and narrow installed acceptance are pending.

Separate S4 follow-up: Issue #312 implements the private
[automatic Match membership and preparation service](automatic_match_learning_s4_verification.md).
The maintainer identifies S1–S3 as accepted at its baseline. S4 gathers complete
bounded saved-Match membership and exact retained evidence, composes isolated
existing artifacts and publishes guarded current/previous generations. Ordinary
S5 UI and S6/S7 adapters remain subsequent work; S4 does not complete this contract.
Earlier acceptance and pending-status paragraphs remain point-in-time history.

The maintainer has approved the following **v1 product direction**:

* Learning automatically brings together eligible saved games and existing
  analysis evidence, providing understandable reviews and evidence-backed hints.
* Ordinary use requires neither manual Snapshot selection nor Report JSON
  transfer. One explicit **Create Learning review / Update Learning review**
  action produces the derived review.
* Passive viewing executes no new card analysis. Gathering and deriving Learning
  evidence does not silently change future recommendations.
* Using accumulated Learning data to adapt future automatic card recommendations
  is an intended **later development goal**, not a v1 requirement or a permanent
  exclusion. Its training method and architecture are not decided here.

Section 2 describes **implemented behavior**. Sections 3–7 specify **recommended
implementation choices** that realize the approved direction; names of new
internal records and storage locations are design recommendations, not existing
APIs. Section 8 orders the implementation. Section 9 separates later work and
acceptance. Historical implementation and acceptance records remain point-in-time
evidence. Accepted #292–#307 scopes remain intact; #208 stays open, formal
UAT-02–12 stay paused, and this contract neither accepts UAT-01 globally nor
authorizes release preparation.

## 2. Source-grounded inventory

### 2.1 Existing components and precise boundaries

Paths below are relative to `src/skatmind/` unless linked otherwise.

| Implemented component | Existing responsibility | Missing automatic integration boundary |
| --- | --- | --- |
| `app_web/managed_item_discovery.py`, `app_web/managed_item_storage.py`, `app_web/managed_item_contracts.py` | Strict direct-child managed Session/Match discovery; stable Product IDs separate from opaque path handles; at most 2,048 candidates per category; duplicate Product identities become `resolution_required` | Complete automatic source inventory and durable authoritative-version manifest; capped discovery cannot certify complete membership |
| `app_web/learning_direct_entry.py`, `app_web/learning_frontend.py` | Explicit saved-Match capture without activating the recording; strict file/content/active-context checks; immutable copy imported into the selected manual collection with `keep_current` | Automatic selection must be a separate policy and owner, not a change to this manual shortcut |
| `learning_corpus_match_snapshot.py`, `learning_corpus_current_snapshots.py`, `learning_corpus_persistence.py` | Content-addressed exact Workspace copies, closed Game/Decision references, explicit Current selection, strict Resume, no-clobber objects and optimistic atomic Catalog Save | No Session or manual Historical source object; no persistent executed Report; no automatic membership/deletion reconciliation |
| `match_observed_reconstruction.py`, `match_decision_review_preparation.py`, `match_decision_analysis.py` | Safe acting-own-hand before-Card reconstruction or an explicit skip; exact Position Request and relative Profile binding | Connect all eligible managed Workspaces to automatic review without running analysis |
| `match_historical_materialization.py` | Strict normal-completion Historical materialization from enough accepted evidence | Not a general partial-Match converter and not needed for Decision-based Learning coverage |
| `match_analysis_contracts.py`, `match_analysis_report_source_export.py`, `match_analysis_report_source_codec.py`, `learning_corpus_strategy_teacher_builder.py` | Exact executed ordinary Match Decision Report wrapper; strict resume and Current-Snapshot reconciliation; method-specific retained Result validation | Durable original-source envelope and automatic capture at successful Report publication |
| `match_rollout_review.py`, `match_debrief.py`, `app_web/debrief_frontend.py` | Selected Match whole-game rollout; exact original Snapshot plus separately reconciled selected target; complete-only debrief comparison; explicit native incorporation | Durable rollout codec/source retention; automatic inclusion without the manual incorporation step |
| `session_persistence_codec.py`, `session_decision_observation.py`, `session_checkpoint_review.py`, `app_web/session_recorded_review.py`, `session_rollout_review.py` | Strict accepted-Log and saved-Checkpoint resume; observed own-Play mapping; frozen-request review and separate derived rollout; source/generation/attempt checks | Session-native Learning references and durable executed evidence; no existing Session-to-Corpus adapter |
| `app_web/workflow_state.py`, `app_web/execution.py`, `app_web/historical_form.py` | Manual guided/imported Review Request and successful Request/options/Result/download tuple; revision-safe process-local publication; guided creation reuses fixed Game/Player identifiers | Saved Historical-review source identity and private guided-identity namespace, version/correction lifecycle, retained execution codec and Learning projection |
| `corpus_web/preparation.py`, `corpus_web/downloads.py`, `app_web/learning_result_projection.py`, `app_web/learning_result_rendering.py` | Explicit no-analysis artifact derivation; atomic prepared families; exact owner/generation/fingerprint checks; concise retained Learning review | Automatic-source orchestration, durable preparation recipe and source freshness across all represented families |

The existing guided producer in
[`app_web/historical_form.py`](../src/skatmind/app_web/historical_form.py) uses
`HISTORICAL_GAME_ID = "frontend-historical-review"` and `HISTORICAL_PLAYER_IDS`
containing `frontend-forehand`, `frontend-middlehand` and `frontend-rearhand`.
`HistoricalFormDraftV1` requires those Player IDs; `create_historical_form_draft_v1`
reuses them for every new draft. `update_historical_players_v1` changes labels
only, and `build_historical_request_v1` copies the fixed IDs into the Request.
These literals identify a Game and its participants within that guided input;
they do not establish shared Game or person identity across independent Reviews.
S7 must retain their source-local scope as specified in section 4.1.

Relevant existing contracts are [Corpus persistence](learning_corpus_persistence_and_import.md),
[browser workflows](learning_corpus_browser_workflows.md),
[Match preparation/materialization](match_review_and_materialization.md),
[Strategy Teacher evidence](learning_corpus_strategy_teacher_evidence.md),
[Match whole-game review](match_whole_game_review.md),
[retained debriefs](learning_match_debrief.md),
[Session persistence](session_persistence_and_resume.md),
[recorded Session review](session_recorded_decision_review.md),
[Session whole-game review](recorded_whole_game_review.md), and
[manual guided Review](unified_local_frontend_guided_analysis_and_results.md).

### 2.2 Support matrix and staged claims

Stage identifiers refer to section 8. A Report is evidence about a source, not
another recorded Game. “Whole-game Report” here means a selected-decision
`whole_game_rollout` execution, not a Historical batch reviewing every Play.

| Source family | Implemented today | Recommended support and first stage | Explicit limit |
| --- | --- | --- | --- |
| Managed saved Match, complete or mixed 36-slot Workspace | Explicit immutable import into a manual collection; Current-Snapshot Dataset, Tactical and Coaching derivation | S4 automatic exact saved-version selection; S5 player-facing review | Match-only until S6/S7; never count a Workspace as 36 completed Games |
| Partial Match / partial observed Game | Safe reconstructed Decisions or `acting_hand_unavailable` / `required_public_hand_unavailable` skips; valid empty Workspaces can be imported | S4/S5 include available coverage, retained eligible Reports and explicit skips | No fabricated Deal, future opponent knowledge, complete Historical record or analysis for missing evidence; passed/empty slots have no card decisions |
| Live or Retrospective saved Session | Persistent accepted Log and optional frozen Checkpoints; explicit own-decision review; no Corpus import | S6 Session-native recorded/eligible-own-decision coverage and retained saved-method/rollout comparisons | Missing Checkpoints stay missing; other Players' recorded Plays are not saved own-decision evidence; no fabricated Match/36-slot wrapper |
| Manual Historical Review input | Guided normal-completion entry or strict Historical JSON; draft/import is process-local | S7 save a valid completed Historical input as part of the explicit successful Review action; stable saved-review identity and reopen/correct/delete | Unsaved drafts and raw Position inputs are not saved Games; supported Historical endings follow the existing Historical parser, not Match normal-completion limits |
| Manual Historical Review Result or Match Historical Report | Retained explicit Historical execution and downloads; not a Strategy Teacher source | S7 retain exact source plus execution; show recorded coverage and existing per-game review/coaching when actually present | No synthetic ordinary Decision Reports; absent review options mean no assessed decisions; one-game guidance is not a cross-game qualified focus |
| Ordinary Match Decision Report: Immediate, bounded Search, Auto, Information-set Search | Executed `MatchAnalysisReportV1` source wrapper and strict Teacher reconciliation; manual attachment; limited Search outcomes are legitimate evidence | S2 durable capture; S4 automatic exact-current-source inclusion; S5 existing Teacher/Tactical joins | Raw Result JSON, materialization and Historical Reports are not this wrapper; valid evidence need not contain a recommendation |
| Selected Match whole-game rollout Report | Separate `MatchDebriefEvidenceV1`, complete-only comparison, original/target reconciliation, process-local direct view or explicit incorporation | S3 durable capture; S4/S5 separate automatic comparison family | Remains outside Teacher source codecs, Dataset-v2 Teacher labels and qualified complete-Search focuses |
| Selected Session whole-game rollout or saved-method execution | Exact frozen Checkpoint/observation and separate retained execution slots | S6 durable Session evidence and automatic comparison projection | Not a `MatchAnalysisReportV1`; no automatic promotion to Match Teacher evidence or cross-game focus |

The existing manual Corpus contains Match Snapshots only. Its ten prepared
downloads do not represent Sessions, manual Review drafts or rollout debriefs.
The recommended v1 sequence includes S6 and S7; completing S5 alone must be
announced as **automatic Learning from managed Matches**, not all recordings.
S6/S7 broaden coverage and concrete retained comparisons. Qualified recurring
focuses remain explicitly scoped to the existing Match Teacher/Tactical path;
this sequence does not generalize their domain or lower their thresholds.

### 2.3 Evidence lifetime at the baseline

* Session and Match files and manual Corpus Catalog/Snapshot objects survive
  restart. Session files contain no executed analysis; saved Checkpoints are
  decision-time inputs, not Reports.
* Match Reports use a bounded eight-report process-local store. Source mutation,
  Reload and stale-file detection invalidate the live store. A captured debrief
  can outlive eviction/navigation within its bounded process-local scope.
* Manual Corpus Teacher sources and the separate incorporated debrief sources
  are process-local, each bounded at 2,048. Same-context Reload differs from
  reopening a collection. Prepared outputs are also process-local.
* Manual Analyze/Review drafts and successful execution tuples disappear with
  the process unless explicitly downloaded. Ordinary Request/Result downloads
  are not interchangeable with the strict Teacher source wrapper.

Already-lost process-local Reports cannot be recovered. A later execution, even
with the same seed, is new evidence; it cannot repair the historical identity
of a lost Report.

## 3. Ordinary workflow and independent manual collections

### 3.1 Recommended ordinary entry

Use one **Automatic Learning** space per managed data home. Give it a distinct
internal owner and storage root, outside the existing `corpora` discovery tree.
The Learning landing page presents its concise status and primary create/update
action, followed by **Independent collections** linking to the existing manual
list. Do not convert, rename or select an existing collection as the automatic
space based on its title, position or age.

1. The user records and saves Matches and, after S6, Sessions through their
   existing workflows. After S7, successful manual Historical Review also saves
   its complete input and genuine execution with a visible saved-source receipt.
2. Existing explicit analysis actions retain their method/settings semantics.
   Successful eligible executions are captured durably at their validated
   publication boundary, whether or not Learning is open. This captures evidence;
   it does not yet create or update a Learning review.
3. Opening Learning reads saved status, validates freshness and explains the
   actual supported families. No source selection, analysis or artifact
   preparation occurs merely from GET, language change or opening a disclosure.
4. One native POST **Create / Update Learning review** discovers the complete
   bounded source set, resolves authoritative versions, gathers exact eligible
   evidence, derives the review and publishes one coherent generation. The user
   does not choose Snapshots or upload Reports along this path.
5. Successful creation/update opens the concise review with result focus and a
   receipt. Native View, Player filters, supporting situations, language return
   and downloads use retained values; a second Update with identical inputs is
   an idempotent reuse, not another analysis or additional contribution.

The action may perform strict replay/reconstruction, Report validation, structural
motif detection and existing retained-evidence Coaching derivation. It must never
invoke Position/Historical Application execution, Search, Immediate evaluation,
rollout simulation or an opponent-policy evaluation. Missing comparisons link
to the existing explicit recorded-decision analysis path. There is no automatic
“analyze all missing decisions” fallback.

For the Match slice, reuse the existing preparation builders with a generated
stable Dataset ID, seeds `0` and partition weights `70/15/15` as explicit internal
recipe values. These match current browser defaults and do not alter underlying
contracts. Keep settings in secondary technical controls. All ten existing
exports can remain available for the **Match slice**; Sessions/manual sources
must not silently enter or inflate those downloads. Independent review families
publish with that slice under the outer automatic generation.

### 3.2 Coexistence rule

Manual collections retain their exact `corpus_id`, explicit Current selections,
independent immutable copies, `keep_current` shortcut, `reject`/`retain` conflict
choices, explicit Report attachment/incorporation, and preparation behavior.
Automatic updates never write their Catalogs, source stores or selected versions,
and never import their copied Games as extra automatic recordings.

Deleting or correcting an editable recording affects automatic membership, but
does not cascade into a manual collection. Its independently captured transfer
can still complete under the existing source-copy/target-owner rules. The new
automatic operation instead revalidates the live membership before publication.
Existing manual same-revision Decision reconciliation remains available; it does
not authorize automatic rebinding of old Reports. Durable automatic evidence
does not silently change manual source-store lifetime. A future explicit reuse
into a manual collection must retain its existing target reconciliation and
independent-copy semantics.

## 4. Identity, authoritative versions and source lifecycle

### 4.1 Separate identity layers

Recommend a private source manifest with four separate concepts:

* **Logical source key:** family plus stable Product identity (`match_id`,
  `session_id`, or an S7 generated saved-review ID). Cross-source Player
  aggregation requires an explicit validated retained identity binding, including
  the identity scope in which an existing stable Player ID is meaningful. Guided
  Historical placeholders alone supply no such binding. Labels, names, aliases,
  seats, media titles and matching placeholder strings never establish it.
* **Source version:** exact strict persistence content fingerprint and source
  contract version, plus the numeric revision as descriptive context. Match
  selection points to its exact Snapshot ID. Equal revision numbers do not imply
  equal source content; Undo/correction can reuse numeric revisions.
* **Situation key:** source-version-scoped Game and Decision reference, actor,
  observed Card and information cutoff. Session keys additionally retain exact
  Checkpoint and observed accepted-Play identity. Manual Historical keys retain
  the original Game ID, actual-play index and actor under the saved source and
  its applicable private identity scope.
* **Execution key:** exact original-source binding plus genuine complete Report
  or execution-envelope fingerprint. A separate semantic fingerprint follows the
  method's existing normalization. It is not a replacement execution identity.

For **app-produced guided Historical Reviews**, New creates an independent
generated saved-source identity and private identity namespace. On save, logical
Game and Player keys are scoped as `(saved_review_source_key, original_game_id)`
and `(saved_review_source_key, original_player_id)`. Reopening or correcting a
saved Review retains that source identity/namespace and replaces only its source
version. Repeated guided placeholder literals in independent saved sources alone
establish neither duplicate Games nor cross-review person identity, and cause no
ambiguity blocker. Without an explicit validated retained cross-source Player
binding, those participants remain source-local even when labels or seats match.
This introduces no identity-management UI or additional ordinary Player-selection
step.

Retain the app-produced guided origin and private scope outside the executed
payloads. Preserve the exact original Request/Result identifiers, fingerprints
and byte payloads; do not rewrite them with namespaced IDs. Trusted guided origin
comes from the retained validated producer/source binding, never from an ID's
literal value or string prefix. Imported identity/origin claims retain the strict
reconciliation and ambiguity rules in section 4.2, including when their IDs happen
to match guided placeholders; matching text does not establish trusted guided origin.

Private managed locators and fresh file/root stamps resolve authority and guard
delivery; they are not semantic identities or canonical export fields. Do not
persist process object IDs, HMAC selections or attempt tokens as restart authority.
Restart establishes new owners and capabilities after strict content validation.

### 4.2 Authority and duplicates

The authoritative Match/Session version is the single currently saved, strictly
valid managed recording for that Product identity, captured by the guarded
discovery operation. It is not the highest imported revision or the file with
the latest timestamp. An accepted correction or restored older version becomes
the saved authority even when its revision decreases. Filesystem timestamps may
detect a concurrent write; they never choose the correct version.

For manual Review, S7 introduces one saved-review head with optimistic version
replacement. Reopening it and explicitly applying a correction retains its
source identity and private namespace while replacing the head's source version.
A new independent guided Review gets its own source identity/namespace even
though its raw Game/Player IDs repeat. Imported Historical Game and Player IDs
remain explicit identity claims in their declared scope and must be reconciled,
not regenerated or treated as guided-local merely to hide conflicts.

| Situation | Required automatic behavior |
| --- | --- |
| Same source version encountered again | No new contribution; reuse content-addressed source and exact execution bindings |
| Two managed files claim the same Product identity, even with equal content | Preserve discovery's `resolution_required`; omit that logical source with an explicit blocker until storage ambiguity is resolved; never choose by filename/time |
| Same identity/revision with different bytes | Use only the unambiguous saved authority; flag ambiguous multiple owners; retain old evidence under its original fingerprint |
| Same execution ingested twice | Idempotent archive/index operation; do not pass duplicate bindings into the Teacher builder, which rejects them |
| Distinct runs of one Decision | Retain distinct exact Reports, including elapsed-only variants; existing semantic deduplication prevents multiplied Decision/focus counts |
| Equal display names, different stable IDs | Keep separate and disambiguate captions; no Player or Game merge |
| One Game explicitly represented through two families | Use a validated origin link to give it one coverage contribution and one Decision lineage; keep Reports separate |
| Repeated app-produced guided Game/Player placeholders across independent saved Reviews | Keep separate source-scoped Games and participants; repeated literals alone cause neither duplicate-ID ambiguity nor a Player merge |
| Repeated Historical Game identity claim in a shared/imported scope, or conflicting claimed origin without a verified link | Mark ambiguity; do not count both as independent Games or silently prefer Match/Session/Review; a placeholder-like spelling does not exempt an imported claim |

Recommend retaining origin links when a future app-owned conversion/export is
saved as another family. No such general cross-family adapter exists today.
For independently entered records with unrelated identities, the application
cannot prove they describe the same real deal. State that counts are distinct
**recorded identities**, not proven unique real-world Games; provide explicit
source exclusion in Included data for a known duplicate. This exclusion is an
exception remedy, not an ordinary Snapshot-selection prerequisite. Do not infer
same-Game identity from matching Cards, names, dates or final scores. Existing
manual copies are outside automatic discovery, eliminating that routine double
counting case.

### 4.3 Corrections, deletion and invalidity

Each published generation contains at most one version per included logical
source. Recompute that source's full contribution on replacement; never append
old and corrected decisions together or try to subtract only changed counters.
All joins, source exclusions and qualified focuses use the newly selected exact
versions. An old Report stays bound to its original source. Even an unchanged
Decision Request in a corrected Workspace does not make automatic rebinding
permissible. A new explicit analysis can create evidence for the new version.

* **Correction/addition/new evidence:** mark the prior review outdated. It may be
  inspected only as an explicitly labelled captured prior generation while its
  archived sources remain valid. Its recording-return controls require the exact
  original live version; no redirect substitutes the corrected one.
* **Managed source deletion or confirmed absence:** invalidate current automatic
  eligibility immediately when observed; the next successful Update removes its
  contribution and supersedes affected focuses. Do not render deleted-source
  findings as current. Hide the prior aggregate result if it contains deleted
  sources; offer Update and a concise cause, not a partially filtered aggregate.
  Retained private old bytes follow section 6 cleanup, not silent resurrection.
* **Invalid source or identity ambiguity:** omit it with a named safe diagnostic
  and coverage exclusion. A last good archived version cannot stand in for the
  invalid live recording. Other validated sources may form one coherent review
  whose exclusions are explicit.
* **Uncertain membership:** inaccessible category root, discovery cap or a scan
  interrupted by concurrent change is an update failure, not proof of deletion.
  Publish no replacement and remove no membership by inference.

Distinguish stale-valid captured evidence from corrupted evidence. Corrupted
Report/source objects are never displayed as validated old comparisons. They
remain diagnosable without being consumed. If an excluded entry changes while
building, the update must conflict just as it would for an included entry.

### 4.4 Concurrent preparation and final delivery

1. Capture the automatic owner/attempt, manifest revision/content identity,
   complete discovery membership, each exact source version, evidence-index
   revision, supported adapter versions and recipe. Reuse family lifecycle and
   Product locks for source capture; release them before entering Learning locks.
2. Build immutable candidate sources/evidence and all derived families outside
   app/Product locks. Use a candidate manifest; do not incrementally edit the
   published Current selection for each Match.
3. Revalidate complete discovery, exclusions, file freshness, active owners,
   evidence index, attempt and manifest compare-and-swap at final publication.
   An internal change generation shared by accepted recording changes and
   automatic Learning publication closes in-process mutation races. Keep the
   existing Product-lock-before-short-app-lock order and never hold Match and
   Corpus locks together.
4. Publish all candidate source references and derived families as one generation
   only after all checks agree. Persist the generation descriptor atomically;
   then install its matching process-local bundle. Superseded work publishes
   nothing, cannot clear newer work, and is not automatically retried. An unchanged
   input with a valid existing bundle reuses it.
5. HTML, language return and downloads validate owner, generation and exact
   persisted sources both before projection and immediately before delivery,
   including after unlocked rendering/serialization. Read-only display objects
   are not authorization. Stale controls cannot target a newly active collection
   or a same-named recording.

Current-result delivery requires the captured live inventory to remain equal.
An explicitly opened prior-generation view instead validates its immutable
archived sources and rechecks the current outdated/deleted classification before
delivery. It cannot authorize current-recording actions. A deleted-source aggregate
remains hidden as specified above; this is not an escape from the current guard.

This preserves the source/owner/final-delivery principles of the accepted
[concise Learning result](learning_result_readability.md) and debrief paths.
It provides optimistic local consistency, not distributed locking or immunity
to an uncontrolled external writer between final checks and file replacement.

## 5. Durable executed evidence: what must survive

### 5.1 Common retention boundary

Capture evidence at **successful validated execution publication**, not by
scraping rendered HTML, reconstructing from a summary or running an analysis on
Learning entry. The private envelope must retain:

* family, codec version, producer Package/contract versions and exact execution
  identity; origin distinguishes app-executed from explicitly imported evidence;
* immutable original source object and its verified fingerprint, logical source
  and situation references, stable actors and observed Card;
* exact Request wrapper, effective execution options, Result wrapper including
  warnings and relevant artifacts/provenance already returned by the execution;
* complete method options, budgets, seeds, effective policies, Profile binding
  and application summary, status/stop reason, coverage and comparisons;
* exact originally delivered Request/Result byte payloads with digests where
  download compatibility is promised, reconciled with their typed values;
* any external document actually required to validate that execution, retained
  privately at its original identity, not resolved from today's Player history.

No private Search Worlds, ownership assignments, caches, branches or policy
tables become browser evidence. Original source objects can contain private
hands, statistics or Commentary and stay inside the local persistence boundary.
Fingerprints verify identity and consistency, not historical truth or authorship.

Original-source validation and current-inclusion eligibility are separate tests:
an execution can remain a valid historical capture while being ineligible for
the current automatic review. A retained Result alone is insufficient proof of
either source binding.

### 5.2 Ordinary Match Decision Reports

Store the exact `MatchAnalysisReportV1` and its supported
`MatchAnalysisReportSourceExportV1` representation plus the **original exact
Workspace persistence document/Snapshot** and a new explicit original binding.
The existing wrapper contains Match ID and revision but does not independently
prove original whole-Workspace content; the original binding must be captured
from the producer while the source is still validated.

On resume, use the strict wrapper codec, reconstruct the source Snapshot, rebuild
the Position Request using the original options through
`build_match_decision_position_request_v1`, and reconcile actor, actual Card,
relative Profile binding, input reference and retained method-specific Result.
Reuse the existing Teacher validator without Application execution or Search.
For automatic inclusion, additionally require exact equality with the selected
source-version binding. The manual collection's permitted Decision-level
reconciliation is not a license to infer a new automatic original source.

Immediate, bounded Search, Auto and Information-set Search remain separate
methods. Partial, timeout and unavailable Search results can be durable evidence
when the Report was genuinely executed. A preparation that never executed is
an availability diagnostic, not an executed Teacher Report.

The Session saved-method equivalent uses a separate native envelope, not this
Match wrapper: retain the original Session document, exact Checkpoint and accepted
Play observation, frozen-request-plus-observed-card export, execution options and
genuine execution tuple. Re-enter strict replay, observation and export validation
on resume. It has no rollout derivation unless rollout was actually requested;
S6 projects its existing method-bound comparison without synthesizing a Teacher.

### 5.3 Selected-decision whole-game Reports

Use a **separate versioned private rollout envelope and codec**; do not extend or
reinterpret the ordinary Teacher wrapper. For a Match retain the full Report,
exact original Workspace/Snapshot and derivation, original before-Card Request,
effective Request and Result, actor-relative map, reconstruction policy, rollout
settings/objective, manual supplements with their declared origin, normalized
effective declaration, aggregate work/coverage, all tied-best Cards and actual-
Card comparison. Retain original and target Snapshot separately if a supported
explicit manual incorporation had reconciled them.

Resume re-enters typed options/Report identity, derivation, permitted-transform,
aggregate arithmetic/ranking and output validation, then original-source
reconciliation as in `MatchDebriefEvidenceV1`. Automatic reuse targets the exact
original selected source. The existing manual same-revision compatible-target
behavior remains separate and explicit. Never substitute the current Workspace
for a missing original Snapshot merely because its Decision Request matches.

Only completed rollout Reports create normal comparison rows. Retain genuinely
executed incomplete attempts as method-scoped availability evidence, preserving
any prior completed execution rather than overwriting it. Do not invent a rank,
recommendation or fallback. Rollout never becomes `complete_search`.

For a Session retain the exact original Session persistence document, frozen
Checkpoint, accepted-Log observation, observed Play revision and actor/Card map,
original review export, derived Request (including derivation version 1 or 2),
supplements/options and execution tuple. Strict replay and the existing
Checkpoint observation/export/derivation validate it without collecting a new
Checkpoint. Missing or diverged original evidence is not backfilled from later
hands or Historical materialization.

### 5.4 Historical Review executions

S7 requires a separate Historical envelope: exact saved Historical Request and
canonical Game record, source ID/version, all effective Review/Search/Replay
Coaching options, input reference, external Statistics inputs if supplied, and
the actual execution Result/warnings/artifacts. Retain source-time Player
bindings; labels or today's profile do not reconstruct them. Validate the strict
input/output contracts and exact retained Game/Decision/method relationships.
Use existing retained review/coaching fields only when executed and present.

For guided sources, retain the validated producer origin and source-local
Game/Player scope beside these exact payloads, plus any explicit validated
cross-source identity binding. Resume must restore that scope without changing
original executed IDs or bytes or inferring identity from labels/placeholders.

A Historical Result is not a bundle of genuine Match Decision Reports. Do not
manufacture their options, seeds, elapsed times or Report IDs from a Historical
summary. Any later Historical-to-Teacher adapter would require its own exact
evidence contract and tests; S7 instead offers source-labelled per-game review.
For an existing Match Historical Report, additionally retain its exact original
Workspace/Snapshot, selected Game and Historical materialization/options. Rebuild
and reconcile that strict Request without executing it. It contributes evidence
to the existing Match Game, never a second saved Game or a fabricated manual input.

### 5.5 Adoption of already-existing evidence

On the explicit Update, a bounded handoff may retain still-live producer Reports
whose original source can still be captured and verified through the existing
producer guard. Deduplicate against the archive. Do not scan arbitrary downloads
or independent collections, and do not label reconstructed guesses as originals.
An old manual upload may still be usable under its existing manual contract but
not possess the stronger original-source proof required for automatic adoption.
Already-downloaded valid source wrappers remain an advanced manual entry, not a
normal requirement. Missing old evidence is reported as missing; nothing reruns.

## 6. Recommended local persistence and restart design

### 6.1 Separate bounded store

Recommend an additive private `automatic-learning/` child of the managed home,
with a versioned manifest and immutable content-addressed `sources/`, `reports/`
and `generations/` objects. The exact new filenames/kinds belong to S1, not an
amendment of Session, Match or manual Corpus persistence. Use finite canonical
JSON, domain-separated SHA-256 identities, strict field sets/versions, bounded
reads, no-clobber object publication, and same-directory flushed atomic manifest
replacement. Paths derive from validated kinds and hashes; native handles stay
opaque. No database, new service or background watcher is needed for this bounded
local workflow.

One manifest binds the evidence index, explicit source exclusions, current
generation descriptor and retained prior descriptor. A generation records the
complete selected source/evidence identities, explicit skipped/excluded entries,
recipe (including stable Corpus/Dataset IDs, exact candidate Catalog revision and
canonical source order), adapter/builder versions and derived fingerprints. Match
builders receive an exact in-memory Corpus view assembled from genuine Snapshots;
no synthetic Match is created for a Session or Historical source.

Recommended initial bounds:

* preserve the existing 2,048-candidate managed-family discovery limits and reject
  an automatic update whose discovery is capped;
* at most 2,048 ordinary Decision envelopes, 2,048 rollout envelopes and 2,048
  Historical execution envelopes in the automatic evidence index, globally per
  automatic space, not per Game;
* at most 16 MiB per source/envelope object and 512 MiB total retained automatic
  objects, including old source dependencies and pending publication;
* retain the current and one previous successful generation descriptor; bound
  temporary preparation to one active candidate per owner, with supersession.

These are recommended private resource limits, not measured capacity promises.
They reuse existing per-object/source-count conventions while preventing silent
unbounded growth. If a limit is reached, preserve valid saved data and the
successful process-local analysis, report **analysis completed; Learning evidence
not saved**, and offer explicit cleanup/retry of persistence while the exact
execution still exists. Never silently evict evidence, truncate membership,
select the “best” run, or rerun analysis to retry a failed write.

### 6.2 Durable commit and interruption

Publish and validate immutable dependency objects first; only a successful
compare-and-swap manifest replacement makes them accepted evidence/generation.
Record an executed Report as durable only after that commit. A source/owner or
attempt conflict before evidence publication must not register obsolete work as
an accepted execution. A storage failure does not change the successful engine
Result or claim that it survived restart.

Before the generation manifest commit, failure or interruption leaves the last
accepted generation authoritative. Complete unreferenced objects are orphans;
temporary files are never candidates. After commit but before installing the
in-memory bundle, restart sees a complete descriptor with valid dependencies and
reports the review as needing reconstruction. It never combines some old and
some new artifact families. Retrying the same Update reuses exact objects and
cannot double count. A conflicting newer commit is not overwritten or rolled
back. No automatic merge or retry loop is introduced.

### 6.3 Restart, compatibility and derived reconstruction

Strictly load the manifest and validate its referenced objects, source bindings
and codec versions. Create fresh process owners and download capabilities.
Current mutable recordings must also be rediscovered: valid archived evidence
does not establish their continued membership. Unknown codec/producer contracts
are unsupported evidence, not compatible merely because JSON parses. Retain
bytes and explain incompatibility; use explicit future migrations only when a
tested identity-preserving adapter exists. Preserve existing strict legacy-input
handling and verified opaque object identities; do not rewrite old sources on
read or silently recompute Report IDs under a new producer.

An invalid top-level manifest blocks the automatic store with a value-free
diagnostic and instructions to restore a known-valid copy, never automatic repair
or replacement with an empty space. An individually missing, invalid
or unsupported Report/source object is quarantined from consumption with an
exact exclusion reason. An update can derive from other independently validated
entries, but cannot use a Report whose original dependency failed validation.
Reconstruction is not repair of missing evidence.

**Persist inputs and genuine executions; keep prepared artifacts disposable.**
After restart, the ordinary page says that saved sources and analysis evidence
are retained and the review needs rebuilding. The same explicit Update validates
and rebuilds deterministic derived summaries/Coaching from them without new card
analysis. A compatible recipe reproduces derived fingerprints; an intentional
builder-version change creates a new generation with visible method context.
Passive GET and download do not trigger this reconstruction.

There is no requirement to persist all ten prepared downloads, a Player Catalog,
Dataset-v2, partitions, Tactical summary or Coaching export. Keep existing exact
Request/Result payloads for executed evidence downloads; derived downloads become
available only with a validated prepared generation. Do not promise an expired
process-local URL survives restart; issue a fresh authorized route to the same
retained evidence.

### 6.4 Cleanup and deletion lifetime

Provide one explicit native local-storage maintenance action with an exact
preview and manifest compare-and-swap. Default cleanup removes only unreferenced
temporary/orphan objects and dependencies released by discarded generations.
Separate explicit removal of archived superseded/deleted-source evidence lists
the affected recorded situations and Reports. Remove manifest references first,
then delete only unreferenced owned objects; interrupted deletion leaves harmless
orphans, never dangling accepted references. In-flight readers pin their objects
until final delivery, and competing cleanup/update operations conflict.
An explicit Report removal also retires any generation descriptor that depends on
it and invalidates that entire prepared bundle; it never leaves a published focus
whose supporting evidence was removed. Rebuild requires the ordinary Update.

Retain original source objects while any retained executed Report depends on
them. Source deletion removes automatic eligibility, not silently all copies;
cleanup must never delete recordings, manual Corpus copies or external downloads.
At the storage bound request this explicit cleanup rather than using time-based
expiry. A separately offered “remove evidence” operation must explain loss of
future reuse and preserve source recording authority. These are local lifecycle
controls, not secure erasure or a backup policy.

## 7. Truthful Learning output

Reuse the accepted #300 hierarchy: a concise **Learning review**, a conclusion or
qualified focuses, then closed native **Included data** and **Technical details
and downloads**. Preserve #293's explicit result destination/focus, feedback
priority and ordinary compact entry. Show the following meanings separately:

| Output layer | Allowed meaning and supporting context |
| --- | --- |
| Coverage | Included source families/versions; recorded Games and Decisions; safely reconstructed or frozen eligible situations; explicit skips, invalid/deleted exclusions and distinct evidence-covered Decisions. Keep Match, Game, Report and semantic-group counts distinct. |
| Retained comparisons | Actual Card versus the retained alternatives/tied-best set, exact method/objective/settings and coverage. Include incomplete/unavailable and mixed results honestly. Whole-game fixed-policy simulations are not optimal-play or calibrated win-probability evidence. |
| Qualified recurring focuses | Existing exact Teacher/Tactical joins, semantic Decision consensus, focus thresholds/order and fixed Guidance. Show precise supporting recorded situations, Player, Game, Trick/Card position, source version, actual Card and retained method context. |

Preserve the [existing qualification](learning_corpus_tactical_cross_game_coaching.md):
only complete-Search assessable evidence can qualify, with unanimous qualifying
distinct-semantic complete-Search assessments and at least two strictly-below-best
Decisions in at least two distinct Game references for a Player/motif pair.
Each Decision counts once; at most five focuses per Player retain existing
priority. Immediate-only and completed-common-prefix assessments remain
descriptive. Information-set PIMC/Immediate diagnostics do not substitute for the
retained Information-set assessment. Mixed qualifying assessments do not produce
a focus. Whole-game rollout does not acquire Search qualification.

Motif frequency alone is structural coverage, not a mistake, weakness, cause or
learning focus. “No qualified focus” does not mean error-free play. Explain the
actual reason: absent evidence, a single covered Decision, Immediate-only,
incomplete/non-assessable evidence, mixed assessments, or insufficient recurrence.
Several Reports of one Decision are not several learning situations. Session and
manual Historical comparisons carry their own coverage scope; they cannot make
the Match-only qualified-focus denominator look universal.

Supporting situations use exact retained references and disambiguated captions,
not display-name joins. A live recording link requires an exact fresh source
binding. Otherwise show the retained situation with a changed/deleted-source
explanation, subject to section 4 visibility rules. Do not expose future hidden
hands in a decision comparison; retrospective outcome/context stays separate.

Explicit analysis methods, `auto` fallback rules, objectives, supplements,
budgets, seeds and time-safe opponent-profile precedence remain unchanged.
Learning may describe the effective original policies; it cannot apply a new
Profile, tune a future recommendation, choose a preferred Teacher or overwrite
an analysis assumption with a recording fact. Rollout's fixed policy remains
independent of profile presets.

## 8. Dependency-ordered implementation stages

All stages below are **future work**, not completed by #308. Each future change
needs focused tests, required local/exact-commit CI validation, and its own short
installed maintainer retest. Installed scenarios use disposable synthetic data;
they are instructions for later acceptance, not actions performed for this issue.

Dependency graph: **S1 → {S2, S3} → S4 → S5 → S6 → S7**. S4 requires both S2
and S3; S2 and S3 may be implemented independently after S1.

### S1 — Private source identities and durable object store

* **User outcome:** foundation for retaining executed evidence across restart;
  no new Learning result or recording-family support yet.
* **Components/contracts:** new private automatic-store/source/manifest codecs,
  managed-home integration, immutable object publication, bounded quota/cleanup
  services and source-version/origin/exclusion records from sections 4–6.
* **Prerequisites:** this contract; existing strict loaders and optimistic file
  patterns. Define source-family discriminators without inventing adapters.
* **Persistence/compatibility:** additive separately versioned root; no changes
  to manual Catalog, Session or Workspace bytes; no reinterpretation of old
  Reports; no automatic migration of independent collections.
* **Focused verification:** strict round trips, duplicate-key/nonfinite/unknown-
  version rejection, fingerprints, same-revision different content, duplicate
  identities, no-clobber/CAS, size/count bounds, missing dependencies, injected
  failure before/after manifest replace and interrupted cleanup. Reuse persistence
  and managed-discovery fixtures; do not execute evaluators to test storage.
* **Installed scenario:** with a disposable data home, initialize/reopen the
  private store through the new service boundary; interrupt a staged object write
  and verify the old manifest remains authoritative. Existing manual collection
  and recording bytes remain identical. No new interactive UI in this stage.

### S2 — Capture and resume ordinary Match Decision evidence

* **User outcome:** explicitly executed supported Match Decision analyses survive
  restart as reusable evidence; failures distinguish completed analysis from
  failed durable retention.
* **Components/contracts:** Match execution publication, existing Report-source
  codec/Teacher reconciliation, new original-Workspace envelope, evidence index
  and retained Request/Result retrieval. Add a persistence-only retry for a
  still-retained failed save, with source/owner checks.
* **Prerequisites:** S1; exact publication guard and original source capture.
* **Persistence/compatibility:** additive ordinary envelope; existing export bytes
  and manual upload contract unchanged. Genuine limited Search outcomes retained;
  no rollout or Historical Report accepted by this codec.
* **Focused verification:** all four flat methods, exact original-source mismatch,
  same-revision correction, no-op duplicate capture, elapsed-only variants,
  original external/profile context, restart/tampering, stale/superseded work,
  quota/write failure and no-rerun retry. Extend Report-source/Teacher/Match web
  tests with evaluator-call and file-write accounting.
* **Installed scenario:** in German and English with JavaScript disabled, run one
  tiny explicit Decision analysis, restart and open its retained evidence/downloads;
  confirm exact bytes and no additional analysis. Simulate a persistence failure,
  retry saving the still-retained execution and verify one execution identity.

### S3 — Capture and resume selected Match whole-game evidence

* **User outcome:** a completed whole-game comparison and its original assumptions
  remain inspectable/reusable after restart; incomplete attempts stay distinct.
* **Components/contracts:** rollout publication, new rollout envelope/strict codec,
  existing derivation validators and `MatchDebriefEvidenceV1`; retained comparison
  renderer/downloads, independent from the ordinary Teacher source codec.
* **Prerequisites:** S1 and the accepted selected-Match rollout/debrief contracts.
* **Persistence/compatibility:** preserve original Snapshot and original/effective
  Request, supplements and complete Result; no Dataset-v2 or Teacher-format change.
  Existing manual compatible-target reconciliation stays explicit.
* **Focused verification:** both objectives, tied-best set, manual supplements,
  typed arithmetic, incomplete-after-complete retention, original-vs-target
  tampering, duplicate/semantic variants, restart and interrupted persistence.
  Reuse rollout/debrief fixtures and assert Teacher-codec rejection still holds.
* **Installed scenario:** in both locales without JavaScript, execute a bounded
  Match rollout with an explicit missing-input supplement, restart, and inspect
  the same comparison and exact downloads. Correct the recording and confirm the
  retained Report remains old-source evidence rather than a current comparison.

### S4 — Atomic automatic Match membership and preparation

* **User outcome:** an explicit operation gathers all eligible managed Matches,
  including partial evidence, and their S2/S3 Reports without version picking or
  file transfer. This is the Match-only service slice.
* **Components/contracts:** guarded managed discovery/capture, automatic source
  manifest, candidate in-memory Corpus view, exact Teacher/debrief selection,
  existing preparation builders and outer coherent generation publication.
* **Prerequisites:** S1–S3. No Session or manual Review adapter is implied.
* **Persistence/compatibility:** current/prior generation descriptors and recipe;
  derived artifacts remain process-local. Manual Current/`keep_current`/source
  lifetimes and ten canonical Match exports keep their existing contracts.
* **Focused verification:** partial/empty/passed/complete Games; exact skip coverage;
  correction replaces rather than adds; deleted/invalid/duplicate source handling;
  complete-scan failure versus actual absence; new source/evidence during unlocked
  preparation; late owner/file changes; crash before/after commit; no mixed family
  publication and idempotent retry. Assert zero analysis calls and unchanged manual
  Catalog bytes. Extend managed-entry, Corpus-preparation and generation fixtures.
* **Installed scenario:** use two saved Matches, one partial, plus one independent
  manual collection. Invoke the automatic service, restart and explicitly rebuild;
  correct one Match, delete the other, and retry an interrupted update. Check exact
  replacement/exclusion counts and unchanged manual copies. The UI arrives in S5.

### S5 — Ordinary bilingual review, freshness and maintenance

* **User outcome:** one primary Create/Update action, concise review, source
  explanations, supporting situations, retained evidence and explicit cleanup;
  independent collections remain accessible. Match-only scope is visible.
* **Components/contracts:** Learning landing/current/prepared navigation, immutable
  result projection, native forms, translation catalog, feedback/language return,
  source-exclusion and cleanup previews, final-delivery/download authorization.
* **Prerequisites:** S4; accepted #293/#299/#300 presentation and existing security.
* **Persistence/compatibility:** only explicit update/exclusion/cleanup mutations;
  viewing writes no derived result. Persist exclusion by stable source identity,
  not title. Confirmed exclusion invalidates eligibility; Update replaces the
  review. Existing manual routes and downloads retain their meanings.
* **Focused verification:** current/outdated/deleted/corrupt/restart states, exact
  counts, Immediate-only/no-focus, two-Game qualified Search focus, rollout
  separation, duplicate ingestion, changed-during-render/download rejection,
  cleanup pins/CAS, token/Origin/body bounds, German/English parity, native focus,
  validation retention, JavaScript-disabled operation and passive zero-call counts.
* **Installed scenario:** in each locale with JavaScript disabled, create a review,
  inspect a supporting situation, switch language and download; no new analysis.
  Restart and Update; correct/delete a source and see the honest stale state before
  Update. Resolve duplicate identity, exclude a known duplicate and perform previewed
  cleanup. Open the pre-existing manual collection and confirm its selected copy.
  Check keyboard operation, narrow layout and genuine enlarged browser zoom.

### S6 — Session-native automatic Learning adapter

* **User outcome:** saved Sessions join automatic coverage and retained own-
  decision comparisons, including genuine saved-method and whole-game executions.
* **Components/contracts:** strict Session source snapshots, accepted-Log/Checkpoint
  observation/export, Session execution publication, new Session evidence codec and
  family-specific review projection under the common automatic generation.
* **Prerequisites:** S5 plus S1–S3 storage/validation patterns; no Session-to-Match
  conversion. Match builders/exports remain the Match slice.
* **Persistence/compatibility:** additive sidecar objects; Session persistence and
  frozen Checkpoints remain byte-compatible. No missing snapshot creation, later
  information enrichment or conversion of Session executions to Match Teachers.
* **Focused verification:** Live/Retrospective/ended/partial Sessions, no own
  perspective, missing/pending/future/diverged/observed-ancestor Checkpoints,
  deterministic saved variant choice, ordinary/rollout codecs, correction at equal
  revision, deletion, repeat ingestion, restart, interrupted update and cross-family
  origin collision. No double-counted Games or expanded qualified-focus scope.
* **Installed scenario:** in both languages without JavaScript, record own Plays,
  explicitly review one saved decision, restart and Update Learning. Verify the
  retained comparison and missing-Checkpoint explanation. Undo/correct/delete the
  Session and update again; Match-only counts/exports and manual collections keep
  their separate meanings. A captured old result cannot target the changed Session.

### S7 — Saved manual Historical Review sources and executions

* **User outcome:** a successful manual Historical Review automatically saves its
  input and executed evidence for later Learning; saved Reviews can be reopened,
  corrected and deleted without Report transfer. Per-game historical findings are
  visibly separate from selected-decision rollout and recurring Match focuses.
* **Components/contracts:** guided/imported Historical completion and publication,
  generated private source ID/head and guided-identity namespace, strict
  saved-review codec with validated producer/scope bindings, retained historical
  execution codec, Match Historical publication/materialization binding, native
  saved-source navigation/correction/deletion and review projection. Preserve
  accepted #303–#307 entry/validation behavior.
* **Prerequisites:** S5/S6 common family projection and duplicate/origin handling;
  existing Historical builder, snapshot information policy and Review contracts.
* **Persistence/compatibility:** new private saved-review family outside current
  Session/Match/manual Corpus layouts. Successful Review saves source plus execution
  atomically; failed save retains process-local success with an honest warning.
  Unfinished drafts/imports are not saved Games. Reopen correction replaces its
  source version under the same source identity/namespace; New starts an
  independent source identity/namespace despite repeated guided placeholders.
  Private Learning scoping leaves original executed Request/Result IDs and byte
  payloads exact. Imported identity/origin reconciliation stays strict. No existing
  public Historical Request/Result or persistence format is reinterpreted, and no
  identity-management UI or additional ordinary Player-selection step is added.
* **Focused verification:** normal and parser-supported shortened Historical inputs,
  effective options/external context, no-review-options coverage, no synthetic
  Decision Reports, genuine imported Game/origin ambiguity, edited input/new version,
  restart and no-analysis reconstruction, failed/interrupted saving/update,
  deletion and cross-family atomic delivery. Exercise genuine retained Historical
  tuples, not fabricated summary-only Reports. Add two independent guided Reviews
  with different people in the same seats and identical raw placeholder IDs:
  both contribute distinct Games without a duplicate-ID blocker or Player merge.
  Correct one reopened saved source and assert only its version/contribution is
  replaced; repeated ingestion of that same saved source is idempotent. Verify
  exact retained Request/Result IDs/bytes and reject imported-origin shortcuts
  based on a matching placeholder literal or prefix.
* **Installed scenario:** in German and English with JavaScript disabled, complete
  the normal manual Review, run it explicitly once, restart and Update Learning.
  Reopen/correct that saved input and verify replacement; repeated exact ingestion
  adds no duplicate contribution. Delete it and Update. Inspect historical method
  context and confirm missing analysis options produce no invented comparisons.
  Also save two independent guided Reviews with different people in the same seats.
  Confirm their raw Game/Player placeholder IDs repeat but Learning includes two
  distinct Games and separate participants, without a duplicate-ID blocker. Reopen
  and correct only one saved Review; Update replaces only that contribution under
  its retained source identity. Re-ingest the same saved source and confirm no
  additional contribution. Check that its original executed Request/Result IDs
  and downloads remain exact. Run this case in both locales without JavaScript.

## 9. Tradeoffs, later adaptation and acceptance boundary

The recommendations deliberately choose explicit update over background execution,
source/evidence persistence over ten persisted derived exports, a separate
automatic owner over implicit conversion of manual collections, and exact-version
reuse over clever cross-correction rebinding. This costs local storage and can
leave fewer comparisons after a correction, but preserves explainable identity,
restart reuse and the accepted information/qualification rules. Separate native
adapters cost more than wrapping every Game in a fake Match; they keep coverage
and canonical exports truthful.

No product decision is required to start this sequence. Routine storage, update,
failure, duplicate and presentation choices are recommended above rather than
left as TBD. Later cross-family qualified-focus generalization, general identity
merge/split tooling and recommendation adaptation require separately scoped
contracts; they are not hidden prerequisites for this bounded v1 review. In
particular, later recommendation adaptation has no chosen training method,
architecture, target or automatic Profile policy in this issue. Its eventual
design must state decision-time eligibility and evaluation separately from the
descriptive evidence collected here.

#308 completion means a reviewed, source-grounded contract and ordered plan only.
The proposed stages require their own implementation and acceptance. Existing
explicit analysis/opponent-profile behavior and accepted #292–#307 scopes remain
the baseline. #208 stays open, UAT-01 is not globally accepted, formal UAT-02–12
remain paused, and release preparation is not authorized.
