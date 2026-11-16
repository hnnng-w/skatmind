# Simple event context, costs and Cent rounds — Issue #322 A–F

## Authority and checkout

This is the maintainer-approved A–F follow-up within #322, including the shared
#321 forms. It supersedes the original ordinary questionnaires described in
[event context](event_context_and_checkpoints.md) and
[accounting/Cent rounds](mode_accounting_and_cent_rounds.md). Their earlier
implementation, verification and acceptance records remain point-in-time history.

Actual starting branch: `feat/322-simple-event-cent-forms`. Starting HEAD:
`9e45544901fdf37257d3d6b9f0ddaff91407f5e5`. The initial index and worktree were
clean. Work is left unstaged and uncommitted. Product code changes; public
Request/Result, recording and retained-analysis formats remain unchanged.

## Ordinary visible inputs

| Action | Inputs the user can edit |
| --- | --- |
| Tournament context | One suggested title and tournament mode. The actual Match platform is reused. A standalone Session asks EuroSkat / At the table once, and only asks for perspective when its recording has none. |
| Tournament costs on EuroSkat | Entry cost and Plus level (0–8, or unknown). Table cost follows the supported rule. |
| Tournament costs on another/unknown platform | Optional entry and table costs; provider fees remain unknown. |
| Missing history or explicit score correction | Last covered position, personal list points and cumulative own declarer losses. |
| Attach an external Session to an event | Event/position and only genuinely unresolved participant relationships. Existing stable IDs and perspective are reused. |
| Start Cent | One suggested editable title, actual platform once, and tariff. Reuse the Session's players/seating/perspective; select perspective only when absent. |
| Continue Cent with a generated game | One action button. No repeated mapping, provenance, platform or rule fields. |
| Attach an existing Cent Session | Select the actual saved source; mapping controls appear only for unresolved IDs. Its seating and perspective must agree with the round. |
| Missing Cent result | Won/lost/passed, declarer only if not already recorded, and game value when needed. Passed needs neither declarer nor value. |
| Finish/reopen | One local lifecycle button, no entered values. |
| Explicit next round | Suggested editable title and prefilled continuing tariff. Players, perspective and platform carry forward. |

Form security/selection tokens and the selected position/action remain internal
transport controls. Removed questionnaire answers are not supplied as hidden
required fields or injected by ordinary test helpers. Native retries and language
switches use these same field sets. Obsolete fields are rejected with localized
reload guidance; changed form-selection domains also reject stale selections.
The exact inventory remains **104 POST routes / 156 forms**, with **2,551 keys per
locale**. Installed-smoke and packaging consumers assert the reduced field sets
and retain all seven Accounting routes' **16,384-byte** limits.

Generated event/series/round identities and local round numbering are internal,
not confirmed external tournament IDs. Saved Match/Session titles are reused
where available; otherwise the frontend suggests a readable player-based title.
Cent always has three Session-backed positions. After three games, the user can
finish and stop, or explicitly start the next three. It is not a 36-position Match.

## Actual platform, rules and unknowns

`EventTermsV1` now carries an explicit private wire version `2` with `platform`.
Its version-1 wire shape, strict decoder, fingerprints and frozen values remain
unchanged, without an added platform field or inferred provider. Version 2 rejects
missing/invalid platforms and unsupported versions. New native contexts use v2;
there is no passive rewrite of old journals. An attached Match supplies its actual
recorded platform, including for a Session sharing that context. A standalone
Session's platform comes from its explicit initial choice, never its title or a
profile preference.

Supported scoring and accounting source/version facts are constructed internally
from that actual platform/mode and the explicit action. EuroSkat tournament Cent
retains its distinct quarter-cent context; it does not acquire three-game Cent
arithmetic. Current supported Standard loss bands and Plus table costs are reused.
Unknown historical rate/coverage, receipts and unsupported side settlements remain
unknown. They do not prevent recording Cards or running existing explicit analysis.

Cent transfers preserve exact signed settlement and half cents. A missing-result
entry takes the positive game value before doubling, with loss doubling applied
once when constructing the existing signed-settlement confirmation. Established
recording results are reused without another result form. Supplied results remain
separate from Cards and do not make a Session Historical-ready. Contradictions
remain explicit and prevent ordinary round completion until corrected.

EuroSkat's supported per-game fee calculation is confined to an actual EuroSkat
context. At-the-table and legacy platform-unknown rounds use the separate private
`cent_pairwise_unverified_fees_v1` rule: exact gross transfers are available,
applicable fees/net remain unknown, and no EuroSkat provider charges are applied.
Defender allocation, fractional principal posting and passed/interrupted provider
posting remain bounded unresolved cases on EuroSkat. Unknown fees are not zero.

## Checkpoints and fee boundaries

The existing chronological projection still distinguishes missing, unfinished,
unsettled, passed, settled and contradictory positions. Passed consumes a position
and contributes confirmed zero; an empty game does not. A checkpoint form is
opened for an actual uncovered prefix, or deliberately through score correction.
Established scores/losses need no re-entry. Reconfirmation acknowledges only the
displayed exact disagreement and records the explicit action internally.

Tournament accounting derives its consumed Match extent from recorded positions
and valid checkpoints. Session decision-context cutoffs retain their original
strict-prefix semantics. The first applicable cumulative anchor establishes the
additional-fee interval; a later cumulative anchor updates its end count rather
than resetting the beginning. An existing supported, applicable accounting fee
boundary is reused. Neither covered backfill nor duplicate source bindings adds
another contribution. Missing fee-boundary evidence keeps the charge unknown
while permitting known cost entry.

The genuine prepared fixture has checkpoints **24 / 780 / 4** and **26 / 800 / 5**,
plus the already recorded own loss in game 27. It reaches **606 points / six own
losses**. The derived interval begins at game 25, and `F(6) - F(4) = 400` cents.
Entry EUR 5 plus Plus level 2/table EUR 1.25 gives a **known cost subtotal EUR
10.25**, with earlier costs and receipts unknown. It is not an actual net result.
The existing non-exact-boundary regression also retains the checkpoint-plus-detail
basis: four prior losses, five afterward, and EUR 1 additional fee from game 26.

**The maintainer's installed EUR 9 versus intended EUR 4 observation remains
unresolved.** These synthetic source fixtures neither reproduce that exact state
nor establish its cause or installed resolution. No maintainer UAT data was used.

## Targeted old-data handling and lifecycle semantics

The smallest compatibility path keeps the strict existing accounting readers.
There is no bank migration framework or historical bank UI. Existing paid/
committed pairs, payout receipts, tandem facts and external net confirmations are
not ordinary inputs and do not govern new ordinary calculations.

* New Tournament saves retain relevant cost totals/Plus selection, with payment
  amounts unset, receipts empty and receipt completeness false. Earlier journal
  revisions remain immutable. Old paid/committed pairs are not added or reinterpreted.
* Read-only Cent summaries use recording outcomes and supported game confirmations,
  excluding old external game-payment overrides, net confirmations and adjustments.
  An old game-payment override cannot hide an established recorded outcome.
* Finish/reopen refreshes the actual source facts and changes local lifecycle only.
  It retains the exact original adjustment, provider-completion flag and aggregate
  confirmation, including amount, activity fingerprints and provenance. It neither
  clears omitted fields nor renews a stale aggregate. New rounds inherit no bank facts.

The retained native Request/Result downloads, game files, source bindings and
independent collections remain protected. Selection checks, fresh-source guards,
journal CAS, the shared concurrent-publication barrier and body limits remain in
place. Passive viewing/language changes run no Card analysis or Learning update.

## Source-browser evidence

A disposable source-checkout check reused `scripts/_workflow_visual_browser.py`,
the existing real native server fixture, and genuine synthetic Match/Session
fixtures. Microsoft Edge **157.0.4341.60**, with page script execution disabled,
submitted ordinary controls via keyboard activation. It exercised a German
Tournament and an English Cent flow, actual invalid-value responses, DE/EN
switches preserving those values, correction/retry, generated games, Finish, and
explicit next round. DOM control inventories and screenshots were inspected.

The developer-only script and successful observations are outside the repository:

```text
C:\Users\HENNIN~1\AppData\Local\Temp\opencode\322-source-browser.py
C:\Users\HENNIN~1\AppData\Local\Temp\opencode\322-simple-browser-16q1t70s\observations.json
```

The final command used development CPython 3.13.7, checkout imports and a fresh
disposable browser profile/data root. It created no distribution or UAT build.
The known fee was EUR 4; recordings were byte-preserved; passive navigation and
language switches left accounting bytes unchanged and created no Learning state.
This is source-browser evidence, not installed acceptance.

## Final local selection and acceptance

Complete affected modules follow the changed form, rule, codec and consumer map:

* `test_event_context_web.py`, `test_accounting_web.py`: genuine rendered-input
  HTTP submissions, source preservation and reduced ordinary workflows.
* `test_accounting_state_store.py`, `test_mode_accounting.py`: actual arithmetic,
  platform boundary, immutable revisions and publication/CAS regression coverage.
* `test_event_context_projection.py`, `test_event_context_store.py`,
  `test_event_context_sources.py`: strict platform-term wire compatibility,
  original frozen basis, prefix/contradiction rules and source adapters.
* `test_frontend_validation_preservation.py`, `test_frontend_localization_foundation.py`,
  `test_complete_frontend_localization.py`, `test_frontend_language_switching.py`,
  `test_language_switch_context.py`, `test_task_first_language_preservation.py`:
  exact registry/locale inventory, accessible errors and native value continuity.
* `test_packaging_and_distribution.py`: executes the current installed-smoke registry
  excerpt directly, without building/installing a distribution.
* `test_profile_driven_session_creation.py`, `test_unified_local_app_managed_items.py`:
  generated-Session creation/opening, participant/perspective reuse and consumers.
* `test_cli_internal_architecture.py`, `test_skatmind_rename.py`: complete required
  guards against final source/documentation.

No exclusive module boundary changed: HTTP rejection/observer code, route counts,
body limits, and analysis-action placement are unchanged. The native Accounting
module still verifies all seven limits and pre-body rejection. No exclusive
transport rerun, routine Full, timing-only run or broad Learning rerun is selected.

Run the listed 18 complete modules with development CPython 3.13,
`-n 2 --dist=loadfile --max-worker-restart=0`, external cache/base/report paths and
7,200,000 ms invocation timeouts. After workers exit, run explicit
`.\scripts\check.ps1 -Mode Quick` and whitespace checks. Final commands, results
and any capability skips belong to the handoff after this documentation is complete.
Quick is partial validation; it certifies neither distributions nor full regressions.

Keep **#321/#322 open**. The accepted sequence is automatic partial branch feedback,
ChatGPT published-source review, maintainer integration, and automatic complete
exact-commit main gates `check` and `v1-supported-platform-matrix`. Successful local
checks warrant **locally validated; hosted acceptance pending**, not issue closure.

One later short prepared combined installed acceptance remains pending: reuse the
existing fixture imports, verify checkpoint continuation/reopen and the EUR 4 fee,
then one three-game Cent round, a missing-result retry/language switch, finish and
explicit next round. Preserve prior valid evidence and repeat only remaining or
actually affected steps. No intermediate manual UAT is requested. #208, paused
formal UAT and release authorization retain their separate boundaries.

## Mixed-participant attachment correction at `38b6341`

The bounded follow-up starts on `feat/322-simple-event-cent-forms` at
`38b634190cea5b439eb87f2053589a3257edf63a`, with a clean index and worktree.
Maintainer-verified development-feedback run **43863428591** passed its sole
partial job (Quick and complete rename/architecture modules) in **44 seconds**
overall. This is partial feedback for that commit, not complete acceptance of
the A–F implementation or this subsequent correction.

Before the handler change, a genuine native HTTP regression failed in **4.04s**:
round IDs `(a, b, c)`, external Session IDs `(b, x, a)`, perspective `a`, and
position 2 requiring `(b, c, a)`. The returned form contained only `map_2`;
submitting `map_2="3"` returned **400**, not the expected **303**. The parser's
all-or-nothing mapping branch incorrectly required the omitted known-ID fields.

`accounting_frontend._open_position` now resolves each participant independently:
known IDs map directly, and only unknown IDs consume their rendered `map_i`.
The existing native test is parameterized for all-known, mixed and all-unknown
sources. It asserts exact rendered fields, invalid-mapping rejection without
mutation, accepted source/fingerprint, ordered seating, selected perspective and
unchanged source bytes. Existing uniqueness, perspective, source-binding and
seat-rotation validation still applies. No redundant or hidden mapping inputs
were added; rendering, state, arithmetic, registry and translations are unchanged.

Final verification for this correction is the complete `test_accounting_web.py`
and `test_skatmind_rename.py` modules against final source/documentation, using
development CPython 3.13.7, `-n 2 --dist=loadfile --max-worker-restart=0`, external
temporary outputs and 7,200,000 ms invocation timeouts, followed after worker exit
by explicit Quick and whitespace checks. Command outcomes belong to the handoff.
The earlier 18-module and source-browser evidence remains historical evidence;
no browser matrix, exclusive transport modules or Full rerun is required here.

Product code changed. Keep #321/#322 open for automatic partial feedback after
publication, published-source review, automatic complete exact-commit main gates
and the later combined installed acceptance. Prior A–F and accepted #316–#320
evidence remains intact. The installed EUR 9 versus intended EUR 4 observation
remains separate and unresolved. No UAT build or maintainer-data access occurred;
no manual Check dispatch or intermediate manual UAT is requested.
