# Task-first bilingual stateful workflows

## Status and compatibility

Issue #220 implements private task-first Session, Match, and Learning presentation
in the unified local application. It completes the two remaining approved policies,
in their original canonical positions:

```text
normal_workflows_are_task_first_and_profile_driven
advanced_settings_are_secondary_explicit_and_explained
```

`IMPLEMENTED_BILINGUAL_FRONTEND_POLICIES` now equals the complete ordered
`BILINGUAL_FRONTEND_POLICIES` tuple. No Issue-#220-specific version is introduced.
The existing frontend versions remain:

```text
BILINGUAL_FRONTEND_CONTRACT_VERSION = 1
FRONTEND_TRANSLATION_CATALOG_VERSION = 1
MANAGED_STATEFUL_FRONTEND_VERSION = 1
MANAGED_ITEM_DISCOVERY_VERSION = 1
GUIDED_SESSION_FRONTEND_VERSION = 1
UNIFIED_MATCH_CAPTURE_FRONTEND_VERSION = 1
UNIFIED_LEARNING_FRONTEND_VERSION = 1
FRONTEND_CROSS_AREA_TRANSFER_VERSION = 1
PROFILE_DRIVEN_FORM_DEFAULTS_VERSION = 1
```

The profile, information-architecture, validation-preservation, guided-analysis,
Result-presentation, and underlying Product contract versions are also unchanged.
Package `0.17.0`, Python `>=3.13`, `AGPL-3.0-only`, runtime dependencies, Public API
contract `1`, seven Root workflows, one Console Script, Settlement Matrix version
`3` with 61 cases, 71 authoritative and packaged Schemas, six Session examples,
98 generated outputs, and ten Corpus downloads remain unchanged.

## Projection and renderer boundaries

Private modules under `src/skatmind/app_web/` separate:

* `task_first_contracts.py`: frozen presentation values with immutable tuples;
* `task_first_projections.py`: deterministic ordering over existing Session replay,
  Match position views, Catalog selections, and classified Report sources;
* `task_first_rendering.py` and `stateful_localization.py`: escaped controls,
  native disclosures, Card names, Player names, and managed display-label lookup;
* workflow-specific Session, Match, and Learning renderers;
* `task_first_match_state.py`: entered Match facts and retained Reports without
  running Historical materialization on page load;
* `render_locale.py` and `result_localization.py`: scoped concurrent-safe rendering
  locale and explicit trusted Result-label translation keys;
* `language_form_preservation.py`: bounded, non-persisted presentation transfer for
  an explicit language change.

The projections have no persistence, wizard revision, independent phase,
independent Match position, or Product mutation authority. Session replay,
existing legal-Card helpers, exact Match rotation/position views, and current
Corpus selection/source classifications remain authoritative. Rendering does not
append a Command, start or pass a Game, transfer a Workspace, select a version,
prepare a Dataset, materialize a Report, or run analysis.

## Normal, Advanced, and Technical hierarchy

Normal content precedes optional controls: current state, next task, one primary
entry action where available, and entered facts. Native Advanced disclosures hold
specialist evidence, analysis parameters, corrections, source editing, and conflict
choices. Native Technical disclosures hold IDs, revisions, raw Commands, exact
machine values, and retained diagnostic data. Disclosures begin closed; an explicit
language change can retain their current presentation state. Validation opens every
containing disclosure needed to reach an invalid field.

Managed labels are page identities, with friendly localized fallbacks. Player
choices display names and seats; exact IDs remain submitted transport values.
User names, labels, commentary, Card codes, filenames, and machine documents are
never translated.

## Session

The active page starts with Current game state, Next required Skat action, Primary
action, and Cards and Players already entered, with complete German equivalents.
It uses During play and After the game and localized explanations for all six
existing phases: setup, deal, declaration, skat_and_discard, play, and ended.

One replay provides the selected perspective, declaration, known remaining hands,
public hands, Skat/discards, chronological Plays, current Trick, completed Tricks,
next Player, continuation, ending, and existing export readiness. Missing evidence
remains unknown; exact known-empty hands or Hand-game discards remain distinct.
No hidden ownership is completed. During-play entry retains the existing local
hand and legitimate Skat restrictions. Retrospective promotion remains explicit,
one-way, and fact-free.

The primary task selects an existing typed Command from the phase and retained
facts. Game metadata confirmation reuses the Session identity as the Game identity
only on explicit submission. Cards use exact submitted codes with localized names.
All ten existing Commands remain reachable through normal, optional, or correction
forms. Corrections, strict-prefix Undo, Reload, accepted history, and raw payloads
remain separate from normal recording. Existing expected-revision, replay,
first-rejection suffix, and persistence semantics are reused.

Analysis follows recording. Existing Position/Historical readiness provides the
blocked prerequisites. Available actions remain explicit, with existing samples,
seeds, methods, budgets, and review-family defaults inside Advanced disclosures.
Information-set review is never the primary recording action. Results are retained
only under the existing process-local publication rules.

## Match

The active page begins with Match progress, Next empty or active position,
36-position overview, and Record this game or mark it passed. All 36 positions
remain in canonical order across twelve rounds and the existing three-seat
rotation. Named Players, localized text statuses, selected/next markers, and native
links provide keyboard-accessible, non-color-only navigation. The next position is
the first position whose existing view is neither passed nor play-complete.

An empty position offers Record this game as primary and Mark as passed as
secondary. Neither requires a Game ID or timecode. Optional exact values remain
under later disclosures. Starting, passing, and appending execute their exact
existing operations once after submission.

After starting, declaration and observed Card play form the concise primary path.
Known perspective-hand, original-Skat, and discard evidence remain available without
trapping an observer in a duplicate wizard when evidence is unknown. Completed
entries and the chronological trace are summarized. The palette uses the existing
exact legal Cards or bounded observation candidates and explains the distinction.
Unknown and known-empty evidence remain different Product values.

Commentary, later-response links, metadata/timecodes, Statistics, prepared Profiles,
Decision/Historical analysis, Reports, supported exports, truncation, replacement,
clear, and Reload remain reachable after recording. Statistics retain the exact
strict-before-Match eligibility and existing Profile derivation. Browser changes
neither apply a Profile nor analyze automatically. Confirmations for existing
destructive operations remain required by the Product boundary.

## Explicit transfer and Learning

Transfer displays friendly source-Match and target-collection labels and whether
the logical Match already exists. It uses the existing verified Workspace transfer.
The first imported version becomes selected under the existing import contract;
this effect is explained before submission. For subsequent imports, the default
selects the imported version and Advanced settings can keep the current selection.
Same-revision conflict defaults to explicit resolution; retaining both never merges
them. Decision Report-source transfer is Advanced and limited to eligible executed
Decision Reports. No transfer runs analysis, preparation, or Dataset construction.

Learning starts with What is needed next?, Recorded Matches available, Matches
added to this collection, Versions selected for insights, Build insights, and
Results and downloads. Its empty state explains the full five-step recording,
adding, choosing, building, and reviewing/downloading sequence in both languages.
It distinguishes managed recorded Matches from imported collection evidence and
provides an explicit path through the existing Match-open and transfer operations.
Opening Learning does not silently discover, import, activate, or select Matches.

Snapshot presentation uses Saved Match version and Version used for insights.
Retained alternatives stay Advanced, selection stays explicit, and IDs stay
Technical. Missing selection and non-current Report-source blockers are explained.
The normal Build action appears after prerequisite guidance. Defaults remain
Dataset ID derived from the Corpus ID, seeds `0` and `0`, and weights `70/15/15`.
Configuration is neither learned nor saved automatically.

Strategy Teacher import, binding, replacement/removal, and non-current-source
remediation remain Advanced. Uploads always require file reselection when needed.
Prepared summaries and all ten exact authenticated downloads retain existing
filenames, Routes, JSON, lineage, and invalidation behavior. Viewing or downloading
does not rebuild artifacts.

## Localization, validation, and language changes

The unified frontend uses exactly German and English. The catalogs have exact key
order and placeholder parity and strict deterministic lookup. Fixed Analyze,
Review, and shared Result presentation use catalog messages; their workflow
semantics are unchanged. The transitional English-workflow marker is removed.
Exact diagnostic/machine text remains under Technical details.

The Issue-#218 registry still has 44 POST Routes and 77 form definitions. Existing
same-form `400`, contextual `409`, safe-value allowlists, field links, focused error
summaries, file reselection, and successful `303` PRG remain in force. Selected
canonical Card codes survive rejection even if no longer in the current palette.
Invalid forms apply no Product operation or profile write.

Native language switching retains authoritative state, active items, selected
position, rejected safe values, validation issues, and process-local Results. A
small packaged enhancement additionally transfers unsubmitted allowlisted control
values and explicitly opened disclosures during the same language POST. It uses no
browser storage or background request. Its bounded envelope is validated before
the preference write, bound to the active item/revision, consumed on the matching
return GET, and never accepted as Product state. File bytes and confirmations are
excluded. The existing private `/matches/assets/capture.js` resource Route serves
this unified enhancement; standalone Capture retains its original asset and behavior.

## Accessibility, security, and packaging

Pages retain exact HTML language, headings, visible labels, fieldsets, keyboard
Cards/positions, visible focus, textual status, responsive German labels, native
disclosures, and accessible localized validation. All Product actions, legality,
and downloads work without JavaScript. The enhancement is not authoritative.

Loopback binding, bootstrap exchange, app cookie, Host/Origin checks,
`Referrer-Policy: origin`, CSP, duplicate-header rejection, bounded bodies, no CORS,
no external resource/request, no tracking, no access log, and path/token/cookie
minimization remain unchanged. No cloud, lookup, translation service, encryption,
backup, or secure-storage claim is added.

Standalone Session, Capture, Corpus, canonical `run`, and Public API v1 retain their
existing English behavior and persistence. Python modules are package-discovered;
the existing resource rules package catalogs, CSS, and the new enhancement in
Source, Editable, Wheel, and sdist. Distribution validation checks their byte parity
and strict installed loading in clean Wheel and sdist environments.

## UAT and maintainer gate

```text
UAT-FINDING-001: implementation remediation complete through Issue #220;
                 open pending repeated UAT-01
UAT-FINDING-002: resolved
UAT-FINDING-003: Home, Product-concept, and active-workflow distinction implemented;
                 open pending repeated UAT-01
UAT-FINDING-004: resolved
UAT-FINDING-005: creation and relevant active-view remediation implemented;
                 open pending repeated UAT-01
UAT-FINDING-006: Issue #218 implementation complete; open pending repeated UAT-01
UAT-FINDING-007: task-first remediation implemented; open pending repeated UAT-01
UAT-FINDING-008: German and English unified-frontend implementation complete;
                 open pending repeated UAT-01
Repeated UAT-01: failed
UAT-02 through UAT-12: paused
Issue #208: open
B-09: open
B-07: open
B-06: closed
Package 1.0.0 preparation: not ready
```

The completed 53-row technical ledger is not reopened. Issue #220 remains
conditional on both `check` and `v1-supported-platform-matrix` passing on the exact
merged `main` commit. After merge and green exact-commit CI, the next maintainer
action is **Repeat UAT-01 under Issue #208.** The implementation does not perform
that UAT, close findings, create another Issue, or publish anything.
