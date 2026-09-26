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

Issue #229 adds focused chooser/opening, shared entry-introduction, Match review
and retained-Report renderers. It supersedes the generic concept/related panels
and closed-only Match analysis discovery described in the original #220 evidence.
Ordinary recording stays primary; `/matches/review/N` and existing Report URLs
openly expose the selected Game's existing review actions and Results. Actual
correction, transfer and Learning prerequisite links remain. See
[Home and recorded-game review navigation](home_and_recorded_review_navigation.md)
for exact routes, lifecycle, manual compatibility and installed-browser evidence.

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

Issue #262 scopes compact sizing to the optional Matador input in shared Session/
Match declaration forms, including the #250 editor. The existing count disclosure
contains concise bilingual all-types help and an applicable Session evidence note.
Labels/errors wrap independently of the `7em`, container-bounded text input. It
does not change generic controls, disclosure preferences, hand-evidence entry,
declaration semantics or the staged correction actions. See
[caller and field map](compact_game_declaration.md#optional-count-presentation-issue-262).

Issue #244 supersedes the former **Current state → Next required Skat action →
Next step** instruction stack. Normal Session/Match recording has compact accepted
identity/status, one task heading immediately beside its existing form, and entered
facts. The two redundant instruction panels are removed from markup, not hidden by
CSS. Native Advanced disclosures hold
specialist evidence, analysis parameters, corrections, source editing, and conflict
choices. Native Technical disclosures hold IDs, revisions, raw Commands, exact
machine values, and retained diagnostic data. Disclosures generally begin closed;
#267's sole exception is the existing outer Advanced Match details on `/matches/new`,
which starts open independently of the retained profile compatibility Boolean. An explicit
language change can retain their current presentation state. Validation opens every
containing disclosure needed to reach an invalid field.

Managed labels are page identities, with friendly localized fallbacks. Player
choices display names and seats; exact IDs remain submitted transport values.
User names, labels, commentary, Card codes, filenames, and machine documents are
never translated.

## Session

Issue #265 makes the Home Session task and landing introduction describe recording
or opening a saved recording. The separate recorded-review Home task and active
saved-own-decision review retain their purpose and lifetime; independent manual
analysis remains distinct. Accurate headings/actions, knowledge modes and all forms
remain. Settings/About lose only three redundant body shortcuts; About's existing
secondary technical section is called **Development and automation**. See the
[R01a/c/d/e map](home_and_recorded_review_navigation.md#recording-entry-and-settingsabout-navigation-issue-265).
R01f's reset grouping is implemented by #266; #267 implements only R01g's fresh-open
Match creation and retired Settings toggle. R07f/R13g and automatic Learning remain
separate. See the [one-section state map](profile_driven_stateful_creation.md#default-open-match-details-issue-267)
and [hidden compatibility transport](settings_and_player_seat_setup.md#default-open-match-details-and-hidden-compatibility-issue-267).

The active page starts with its accepted path, phase and perspective, then one
task at `session-recording`: initial hand, declarer, declaration, known Skat,
discards, required public hand, observed Card, or explicit Game End. An ended
recording has one normal ended heading and a history/correction link, with no empty
Next step panel. Detailed accepted ending/history remains. German and English use
the same accepted facts and primary-action projection.
Issue #233 supersedes During play / After the game with knowledge-based paths:
Player-perspective recording (`live`) and complete-deal reconstruction (`retrospective`).
The effective accepted mode is shown independently of timestamps and completeness,
with localized explanations for all six existing phases: setup, deal, declaration,
skat_and_discard, play, and ended. See [Knowledge-based Session entry](session_knowledge_based_entry.md).

One replay provides the selected perspective, declaration, known remaining hands,
public hands, Skat/discards, chronological Plays, current Trick, completed Tricks,
next Player, continuation, ending, and existing export readiness. Missing evidence
remains unknown; exact known-empty hands or Hand-game discards remain distinct.
No hidden ownership is completed. Perspective entry works during or after the Game
with the existing local-hand, legitimate Skat/discard and public-hand rules.
Reconstruction requires all three initial hands and original Skat even with a local
Player. Promotion remains explicit, one-way, fact-free and phase-preserving; it is
an optional specialist action rather than the expected next step after ending.

The primary task selects an existing typed Command from the phase and retained
facts. Issue #231 prioritizes authorized initial Cards in setup/deal: the first
successful normal Card save supplies missing Session-derived Game identity through
one existing ID-only Command before the Cards. Creation stays revision zero;
N Cards add N+1 revisions if identity is missing, otherwise N, with one save.
Game details and exact time remain optional secondary operations. Opening and
language changes initialize nothing. See [Direct Session Card start](session_direct_card_start.md).
Cards use exact submitted codes with localized names.
All ten existing Commands remain reachable through normal, optional, or correction
forms. Corrections, strict-prefix Undo, Reload, accepted history, and raw payloads
remain separate from normal recording. Existing expected-revision, replay,
first-rejection suffix, and persistence semantics are reused.

Analysis follows recording. The named **Other analysis: current position and full
Historical review** native disclosure contains those specialist controls and their
capability-specific blockers. A valid retained Result is rendered outside it at
`session-result`, independently of current Position/Historical readiness. Available
actions remain explicit, with existing samples,
seeds, methods, budgets, and review-family defaults inside Advanced disclosures.
Information-set review is never the primary recording action. Results are retained
only under the existing process-local publication rules.

Issue #221 adds **Review recorded decisions** near the opened Game summary and a
visible compact list after the primary recording action. Issue #244 uses one
source-consistent recorded-decision projection for both. Before an observed local
Play, the ordinary invitation and numeric 0/0 panel are omitted; the existing
destination remains a visible neutral region. Recorded Plays without eligible
snapshots instead offer inspection, diagnostics and applicable corrections. No
perspective, opponent-only Plays, pending, future, diverged and missing snapshots
remain distinct. Saved observed own
decisions have Player/Trick/Card-position/actual-Card labels and direct actions,
including after all 30 Plays. Current-position analysis and full Historical review
keep independent readiness. Exact source binding, variant selection, read-only
execution, Result lifetime, and contextual bilingual feedback are documented in
[Review recorded Session decisions](session_recorded_decision_review.md).

## Match

Issue #264 groups the shared prepared-decision selector with its existing Analyze
button, before Advanced analysis options, inside the same POST form. Recording's
outer analysis disclosure remains initially closed; focused review and retained
Report pages reuse the same composition. Closed Advanced options still submit
their current values. No second action, settings persistence or automatic execution
is added. The typed helper tail defaults to empty for Session, Learning, recovery
and other Match forms; validation/language instrumentation includes the entire
tail. See the [caller/field/default map](match_analysis_and_exports.md#unified-decision-action-placement-issue-264).
Inventory remains 67 routes / 112 forms / 1,805 paired keys, preserving #238–#263.

Issue #263 addresses R07d/e only: genuinely empty Skat/discard disclosures are
omitted, and the existing optional initial-hand summary names its accepted Game
perspective and provides a native target for conditional missing-hand guidance.
Unknown-but-editable evidence stays available. The link follows structured skipped
reasons and exact actor/owner identity, not a Report, next actor or Settings Player.
Original dealt-hand evidence includes already played Cards from that hand; Save
and explicit review/analysis remain separate. See the
[state/owner/target map](match_game_navigation.md#discoverable-match-evidence-issue-263).
The normal/native disclosure needs one explicit opening after arrival. #223
restoration, #245 receipts, #247 caption, #248 ordering and #249–#262 remain.
Current inventory is 67 routes / 112 forms / 1,805 paired keys. Unknown/Exact and
global disclosure preferences are separate work, not part of this repair.

Issue #238 supersedes the old progress → suggestion → full overview → task order
and normal Position labels. Compact started/complete-trace/passed counts now precede
the selected **Game N of 36**, accepted progress, named seats and existing recording
action inside `#match-recording`. The one native 36-tile/twelve-round overview
follows recording at `#match-games`. Tiles and first-unfinished links use the
existing `/matches/position/N#match-recording` destination. The suggestion still
uses the first view neither passed nor play-complete; it is omitted as a CTA when
already selected, can point backward, and never changes selection automatically.
See [Match Game navigation](match_game_navigation.md) for exact progress, native
focus, same-source lifecycle and measured before/after evidence.

Issue #260 supersedes only R12a–c's activity-sounding partial label, ambiguous
first-open wording and redundant primary round paragraph. Accepted completed
Tricks and any one/two Cards in the next Trick share one compact coverage caption;
empty/setup/zero-Play-ready/passed/complete remain distinct. The existing captured
first-incomplete target is named by **Open Game N for recording**. Twelve secondary
round headings and all 36 entries remain, with the already-correct tile-local text
and `aria-current` selection cue (R12d). Coverage is not unsaved work, analysis
readiness or settlement. No state, operation, Report lifetime or workflow-script
change follows; historical UAT observations and remaining residues remain open.

An empty position offers Record this game as primary and Mark as passed as
secondary. Neither requires a Game ID or timecode. Optional exact values remain
under later disclosures. Starting, passing, and appending execute their exact
existing operations once after submission.

After starting, declaration and observed Card play form the concise primary path.
Known perspective-hand, original-Skat, and discard evidence remain available without
trapping an observer in a duplicate wizard when evidence is unknown. Completed
declaration/evidence and the chronological trace remain visible. Issue #244 removes
the normal completed-steps bookkeeping list while retaining its projection data.
The palette uses the existing
exact legal Cards or bounded observation candidates and explains the distinction.
Unknown and known-empty evidence remain different Product values.

Commentary, later-response links, metadata/timecodes, Statistics, prepared Profiles,
Decision/Historical analysis, Reports, supported exports, truncation, replacement,
clear, and Reload remain reachable after recording. Statistics retain the exact
strict-before-Match eligibility and existing Profile derivation. Browser changes
neither apply a Profile nor analyze automatically. Confirmations for existing
destructive operations remain required by the Product boundary.

Issue #222 places linked accepted Trick history, evidence-supported warnings, and
native correction/rewind previews beside normal Card entry. Source-bound Apply
reuses authoritative Game construction and Workspace CAS persistence. See
[Match recording error recovery](match_recording_error_recovery.md).

Issue #224 gives unified Match/Learning presentation one app-owned stylesheet.
Explicit tile title/status/marker/participant children replace the standalone
two-column class collision, while all 36 links and twelve rounds remain unchanged.
Expanded forms, transfer/settings, recovery and Reports use shrinkable scoped
components; only the captioned candidate table has a labelled keyboard-scroll
region. See [Unified workflow visual contract](unified_workflow_visual_contract.md)
for measured contrast/reflow and repeatable installed-browser evidence.

Issue #226 updates normal Session/Match Card entry with shared compact native
set/single-Play selectors. Session batches append N ordinary Commands through an
immutable candidate and one save; Match retains replacement evidence operations.
Exact-source forms and truthful palettes return to recording controls. The current
registry has 57 POST routes and 93 definitions. See
[Compact Card entry](compact_card_entry.md) for ordering, Checkpoint parity,
rejected-input/language behavior, and installed-browser evidence.

Issue #227 adds [Recorded Trick progress](recorded_trick_progress.md): a compact
three-Player captured-point/won-Trick summary beside recording and immutable
cumulative prefixes in the accepted history. Session consumes its existing replay;
Match enhances #222 history with the same rule-derived winners and exact correction
anchors. Null omits point metrics; incomplete and shortened records receive no
unplayed credit. Accepted warnings remain visible. This is partial C6 remediation.
No route, Product operation, persistent counter or analysis is added.

Issue #228 adds [Compact Game declaration](compact_game_declaration.md) to Session
and Match. Game type and bid are visible; the earlier bid-under-Advanced decision
is superseded. Shared native checkboxes send four explicit canonical choices through
exact-source private markers on existing routes. Optional Matador help, precise
localized errors and accepted-only summaries retain existing information limits,
historical correction, Match no-op/clear and #221–#227 lifecycle semantics. There
are now 97 form definitions on the same 57 routes. Bilingual narrow/enlarged forms
wrap guidance without shrinking text; actual browser measurements are linked above.

## Explicit transfer and Learning

Issue #259 clarifies optional attachment of an existing executed Match Decision
Report's specialized source JSON. Current-only offered targets determine the
control: no target gives a prerequisite/remedy, one gives a read-only named version
and one hidden ID, several give an explicit native selector with distinguishable
full captions. Attached-source labels use their own exact bound version; non-current
blockers retain restoration/removal/clear controls. File reselection, explicit
validation/evaluation and process-local source lifetime remain. The existing direct
transfer, #245 receipts, #256 returns, #257 version policy and #258 result groups
are preserved. See [attachment ownership](learning_corpus_browser_workflows.md#unified-optional-attachment-issue-259).
Inventory remains **67 routes / 112 forms**, now **1,797 paired keys**. Automatic
inclusion/discovery/conversion, durable Report sources, full Coaching presentation
and recommendation adaptation remain separate open work.

Issue #258 explains the retained result inside the existing `learning-results`
identity. Compact source-qualified sentences precede separate Human/Teacher/Tactical
evidence and Coaching status, then per-mode split availability and ten grouped native
JSON downloads. The [field/status and artifact maps](learning_corpus_browser_workflows.md#unified-retained-result-explanation-issue-258)
define units, zero/unavailable handling, aggregate privacy and technical ownership.
Rendering uses the captured prepared view only; no workflow or lifecycle boundary
changes. #256 focus/receipt routing and #257 selection/variant policies remain.
The current inventory is **67 routes / 112 forms / 1,786 paired keys** (48 legitimate
result/description captions added). Historical milestone counts below remain evidence
of their original trees. Optional Report attachment and automatic source inclusion,
Report incorporation and recommendation adaptation remain separate open questions.

Issue #257 clarifies selected input and retained alternatives using the existing
per-Snapshot forms. A valid selected singleton is read-only without an empty
disclosure. Multiple versions retain one visible Current summary and one native
alternatives disclosure per Match. Missing-selection remedies, rejected-form feedback
and Teacher-source blockers remain independent. Stored Workspace revision plus a
display-only same-revision variant ordinal distinguish exact identities; no Catalog
version or chronology is invented. Selection saves only Current, followed by separate
explicit evaluation. Shared `reject`/`retain` help explains no-add versus separate
retention, while direct Add keeps its fixed `keep_current` and transfer/upload keep
their explicit selection policies. #256 targets and #245 receipt ownership remain.
See [state/field mapping](learning_direct_match_entry.md#selected-versions-and-conflict-policy-issue-257).
The current inventory is 67 routes / 112 forms / 1,738 paired keys. Earlier milestone
evidence below retains its original wording and counts.

Issue #244 makes the existing Match-side **Add this Match to Learning** shortcut a
secondary native disclosure after recording/overview. Relevant retained transfer
feedback opens it, including when the old exact form is no longer present; normal
validation also opens the failed form's containing disclosures. The existing
transfer notice opens its controls on the outcome render without changing that
notice's lifetime. Learning's own page, discovery, direct-add semantics and source
deletion rules are unchanged. Empty/partial Workspace imports remain valid; an
empty selected Game says nothing about other Games in the Workspace.

Transfer displays friendly source-Match and target-collection labels and whether
the logical Match already exists. It uses the existing verified Workspace transfer.
The first imported version becomes selected under the existing import contract;
this effect is explained before submission. For subsequent imports, the default
selects the imported version and Advanced settings can keep the current selection.
Same-revision conflict defaults to explicit resolution; retaining both never merges
them. Decision Report-source transfer is Advanced and limited to eligible executed
Decision Reports. No transfer runs analysis, preparation, or Dataset construction.

Issue #236 supersedes the former five-step/open-Match-first Learning presentation:
[Direct saved-Match entry](learning_direct_match_entry.md) provides one initially
unselected native selector, explicit Add, explicit Evaluate, then View evaluation.
The first collection-page GET can initialize missing bounded Match discovery once;
ordinary/language/error renders reuse it and refresh is explicit. Add copies the
current valid saved version without activating a recording. Partial/empty valid
Matches are allowed. The first version becomes Current; later direct adds use
`keep_current`, unlike the unchanged Match-side transfer default above.

Issue #255 clarifies the landing purpose and replaces the redundant opened-collection
next-task panel with action-local help. Name-only creation makes an empty collection;
it imports and prepares nothing. A collection is not required for ordinary individual
decision review. Add copies the currently saved Match version, not a live link or
every separately executed decision Report. The source dropdown alone imports nothing.

Snapshot presentation uses Saved Match version and Version used for evaluation.
Retained alternatives stay Advanced, selection stays explicit, and IDs stay
Technical. Missing selection and non-current Report-source blockers are explained.
The normal Evaluate collection action appears after prerequisite guidance. Defaults remain
Dataset ID derived from the Corpus ID, seeds `0` and `0`, and weights `70/15/15`.
Configuration is neither learned nor saved automatically.

Strategy Teacher import remains Advanced. Non-current-source remediation exposes
its native removal controls visibly when it blocks evaluation. Uploads always require
file reselection when needed. Matching prepared artifacts lead to View evaluation at
`#learning-results`, with the existing secondary preparation control labelled Recreate
evaluation in its original placement. Missing-selection and source-remediation links
remain; the redundant jump to the adjacent source form is removed. Counts describe available evidence,
not 36-position completeness, Player strength, or zero mistakes without Teacher input.
Prepared summaries and all ten exact authenticated downloads retain existing
filenames, Routes, JSON, lineage, and invalidation behavior. Viewing or downloading
does not rebuild artifacts.

The #255 change is private composition/copy only: the existing task projection,
`prepare_learning_artifacts`, #236 direct entry, #245 receipts, error/disclosure
identities and all ten outputs remain authoritative. The registry is still 67 POST
routes / 112 forms; three scoped captions bring paired catalog keys from 1,731 to
1,734. Automatic source inclusion, executed-Report incorporation and recommendation
adaptation remain distinct open product questions. Return/focus routing, version/
conflict controls, result interpretation and download organization are separate
follow-ups at that milestone; this explanation does not resolve R13/R14 or accept UAT.

Issue #256 changes only successful direct-Add and preparation returns. Add targets its
collection/Match-derived native block, where the exact affected saved version and
the version used for evaluation are named separately. First/keep-current/identical
semantics, Current controls and alternative disclosures remain. Preparation/recreation
returns to the existing `#learning-results`; an older retained result cannot establish
new success. The actual typed returned outcome determines routing. Error-summary and
source remedies retain priority, and limited/empty successful results remain allowed.
See [outcome mapping](learning_direct_match_entry.md#outcome-returns-issue-256).

The one #245 receipt is colocated with its outcome, independently of content lifetime;
no second toast, renewed receipt, automatic operation or persistent result is added.
The existing direct-entry outcome carries an exact Snapshot/source binding instead of
looking up a version by revision/title. Stable anchors remain navigation only. Both
targets use native negative tabindex and a measured scroll margin; script and #223
language/validation restoration are unchanged. One new caption brings the catalog to
1,735 paired keys on the same 67 routes / 112 forms. Remaining R13 version/conflict and
R14 result/download/automatic-use questions remain open.

The #224 light surface/foreground pairs cover empty, selected, blocked, prepared,
error and Advanced states. Standalone Corpus CSS no longer overrides the unified
theme. This technically remediates the earlier #223 visual observations without
changing Learning prerequisites, operations or the failed maintainer UAT result.

## Localization, validation, and language changes

### Contextual completion feedback

Issue #245 replaces the retained generic-success tails with a small source-bound
presentation receipt. It leaves #244's one-current-task hierarchy and the existing
recording, recovery, error and Result destinations intact. Normal acknowledgements
use the following finite de/en outcome mapping:

| Accepted action | Routine feedback |
| --- | --- |
| Normal Session / Match / Learning creation | Game / Match / learning collection created |
| Initial Session Card batch | Accepted Card count and Player, excluding any implicit identity Command |
| Observed Play | Localized accepted Card and its actor, not the next Player |
| Declaration / declarer / metadata / ending | Specific saved fact |
| Initial-hand, public-hand, original-Skat or discard evidence | Specific evidence, with Card count where applicable |
| Match start / pass | Actual Game number started / marked as passed |
| Actual Card correction | Card correction saved |
| New Learning version / explicit Current selection | Version added / version selected |
| Published Learning artifacts | Collection evaluation prepared |

No-op, same-Card Apply, navigation, preview, Cancel, opening and unallowlisted
advanced operations mint no save receipt. A genuine review returns its Result
without a second confirmation. An identical import keeps its neutral explanation;
`keep_current` retaining another version keeps its untimed selection/rebuild guidance
and receives no clean-success toast. Preparation does not train a model or improve
future recommendations. The selected versions, accepted recording and prepared
Result remain inspectable without a timer.
An identical-version import that actually changes Current selection uses the
selection message, not the added-version message, including the Match-side transfer.

Delivery lasts at most 60 monotonic seconds after publication and is consumed only
by one matching final HTML response. New operations supersede it. Native HTML is
untimed; the optional script uses eight seconds of visible idle time, paused on
hover/focus/hidden documents, and retains normal-flow space when hidden to avoid an
input jump. It makes no request. Full Player names are source-resolved and escaped.
Language changes do not mint or renew a recording acknowledgement. Receipt delivery
is best-effort across identical-source tabs and lost responses, not per-tab exactly
once; native cached history may still contain the old response. See the
[validation boundary](frontend_validation_state_and_localized_feedback.md#completed-operation-receipts-issue-245)
and [installed evidence](unified_workflow_visual_contract.md#r03-contextual-operation-feedback).

The current registry remains **63 POST routes / 107 forms**, with **98** generated
scenarios and **1,604** matching locale keys. No engine, retained Request/Result/Report,
Checkpoint, profile or persistence shape changes. #244 remains completed. Only this
R03 operation-feedback slice is implemented; #208 and the other findings stay open.

The unified frontend uses exactly German and English. The catalogs have exact key
order and placeholder parity and strict deterministic lookup. Fixed Analyze,
Review, and shared Result presentation use catalog messages; their workflow
semantics are unchanged. The transitional English-workflow marker is removed.
Exact diagnostic/machine text remains under Technical details.

With Issue #222 the registry has 49 POST Routes and 82 form definitions. Existing
same-form `400`, contextual `409`, safe-value allowlists, field links, focused error
summaries, file reselection, and successful `303` PRG remain in force. Selected
canonical Card codes survive rejection even if no longer in the current palette.
Invalid forms apply no Product operation or profile write.

Issue #223 makes language selection one native Deutsch/English button activation
with an absolute target and effective-locale pressed state. Semantic origins keep
creation rejections, selected Match Game/Report, active Session/Learning, Review
step, Analyze, and About in their rendered task. The safe HTML-route allowlist
remains unchanged; only known server-owned Result/recording/recovery anchors are
appended separately. A complete PRG response uses one consistent rendering locale.

Issue #236 additionally binds Learning's retained Match discovery/generation into
that semantic source. Safe submitted source choices and conflict resolution survive
errors/language changes; hidden direct-add target/discovery bindings are regenerated.
The current registry is 63 POST routes / 107 definitions; the de/en catalogs have
1,529 keys. Historical #222/#223 counts retain their original evidence scope.

Native language switching retains authoritative state, active items, selected
position, rejected safe values, structured validation issues, and process-local
Results. A small packaged enhancement additionally transfers registered unsent
controls and open/closed disclosures during the same POST. Explicit empty,
unchecked, repeated, and selected values are retained; validation-required
disclosures remain open. Without JavaScript, unsent values in another browser form
cannot be recovered. File selections, passwords, secrets, hidden transport fields,
and destructive confirmations are never copied. Current validated transport fields,
including profile generations, are regenerated after saving the language.

The optional envelope is limited to 262,144 UTF-8 bytes, 256 forms, and 1,024
disclosures plus registered field bounds. Client capture failures prevent navigation
and explain the problem. Exact rendered-page/source/form bindings are checked before
preference saving and on restoration, including reopen, complete content identity,
position movement, Review step, repeated identities, and preview expiry. A source
change after a successful preference save discards the overlay with honest conflict
feedback; it does not undo that save. Valid #221 Results/downloads, #222 selections,
preview lifetime and Apply tokens, and Learning artifacts remain unexecuted and
unchanged. Genuine Product edits retain their normal invalidation behavior.

No browser storage, persistent drafts, implicit preference save, background request,
or per-tab Product workspace is added. The existing private
`/matches/assets/capture.js` resource Route serves **`app_web/assets/workflow.js`**;
standalone Capture retains its original asset and English behavior. Detailed
binding, conflict, and actual browser evidence is recorded in
[Local frontend profile and localization](local_frontend_profile_and_localization.md).

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

Issue #244 implements only R03's current-task/readiness composition. Observation,
analysis availability and a retained execution Result are independent axes. Native
submission remains explicit: no automatic metadata confirmation, promotion, Card
save, End, Game switch, import or analysis. Exact source bindings, frozen options,
Requests/Results/downloads, #238 navigation/transport and #239–#243 remain intact.
The current registry is still 63 POST routes / 107 forms, with 98 scenarios and
1,577 matching catalog keys. [Installed browser evidence](unified_workflow_visual_contract.md#r03-recording-task-composition)
records matched counts/geometry. Generic operation-notice lifecycle, R05 and other
backlog work remain open. #243 stays completed; both exact merged-commit CI jobs
gate manual #244 closure. No maintainer UAT acceptance follows.

```text
UAT-FINDING-001: task-first implementation through Issue #220;
                  open after failed September 11 repeated UAT-01
UAT-FINDING-002: resolved
UAT-FINDING-003: Home, Product-concept, and active-workflow distinction implemented;
                  open after failed September 11 repeated UAT-01
UAT-FINDING-004: resolved
UAT-FINDING-005: creation and relevant active-view remediation implemented;
                  open after failed September 11 repeated UAT-01
UAT-FINDING-006: Issue #218 implementation complete; open after repeated UAT-01
UAT-FINDING-007: task-first remediation implemented; open after repeated UAT-01
UAT-FINDING-008: German and English unified-frontend implementation complete;
                  open after failed September 11 repeated UAT-01
Repeated UAT-01: failed again on September 11, 2026
UAT-02 through UAT-12: paused
Issue #208: open
B-09: open
B-07: open
B-06: closed
Package 1.0.0 preparation: not ready
```

The completed 53-row technical ledger and Issue #220 are not reopened. The
September 11 repeated UAT failure included the lack of actionable review after 30
Session Plays. Issue #221 implements only that direct recorded-decision path;
other Match, Learning, settings, layout, and language-control findings remain
outside it. Both `check` and `v1-supported-platform-matrix` must pass on the exact
merged commit. Implementation and automated tests do not constitute maintainer
UAT acceptance or close its findings.
