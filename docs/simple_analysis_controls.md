# Simple private analysis controls (Issue #325)

## Authority and ordinary behavior

This implements the maintainer-approved L–N boundary from Issue #325 on
`feat/325-simple-analysis-controls`, starting at
`fca6b3a1defe8a6320bbf8a8ee73840e7af26b46`. The starting index and worktree were
clean. Issue #324 and its waiting-time/Learning exclusion boundary are accepted.

One private `app_web/analysis_controls.py` boundary supplies native controls,
strict mode/effort resolution, and source-scoped submitted-value retention.
Concrete values reach the existing executors and original Request/Result exports;
the UI names are not public settings or persisted analysis preferences.

| Ordinary path | Quick | Standard | More time |
| --- | ---: | ---: | ---: |
| Guided Position Immediate samples | 250 | 1000 | 4000 |
| Session current Position, legacy Match decision, Match/Session/manual Historical Immediate samples per decision | 25 | 100 | 400 |
| Recorded Match/Session whole-game requested worlds | 25 | 100 | 400 |
| Recorded whole-game timeout, milliseconds | 5000 | 30000 | 60000 |

Fresh forms select Standard. Position/current-position/legacy Match decision uses
Immediate; recorded whole-game review keeps rollout. Historical Match/Session
keeps Immediate Review. Only a newly started frontend manual Historical draft
explicitly enables Immediate Review. `HistoricalFormOptionsV1`, public API/CLI
defaults, existing drafts, imports and retained executions keep their defaults
and deliberate selections. Result-only manual review remains available in custom
mode. Fresh seeds remain 42 for guided Position and 0 elsewhere; effort never
resets submitted seeds, objectives or information views.

These finite budgets are neither response-time guarantees nor accuracy levels.
Fresh rollout preparation/transition limits remain 100000/300000. Valid retained
custom limits are also preserved. Existing complete/common-world requirements,
incomplete/timeout output, fixed rollout policy and source/attempt cancellation
remain authoritative.

## Native precedence and disclosure ownership

The ordinary effort selector is outside the initially closed **Technical
settings** disclosure. That disclosure contains the explicit **Settings mode**
selector, method, custom numerical values, seeds, existing Search profiles,
individual policies and explicit simulation/comparison controls. A native
CSS-selected **Custom settings** marker is visible in the ordinary area when
custom mode is selected, including with page JavaScript disabled.

The precedence is deliberately explicit:

1. `settings_mode=ordinary` uses the selected `analysis_effort`, selects that
   path's ordinary method, and leaves custom simulation/comparison inactive.
   Submitted technical sample/method values cannot defeat the preset merely
   because closed controls are successful native controls. An inactive Match
   Search profile is normalized only as required by the existing Immediate
   contract; its original custom selection remains available in the form.
2. `settings_mode=custom` uses the technical values and ignores effort for
   execution. Changing effort alone cannot change a custom method to Immediate.
   Returning to the ordinary method requires explicitly selecting ordinary mode.
3. Missing mode metadata means legacy/custom behavior. An existing source-matched
   retained configuration is never inferred to be Standard merely because its
   sample count happens to be 100. Old Match Report options and recorded rollout
   settings reopen as custom; new submitted modes retain their exact choice.
4. Safe inactive values are retained independently of effective settings, in
   private immutable draft values or bounded process-local owner slots. They
   survive accepted posts, retries and language returns, without rewriting any
   original retained execution. Separate forms do not share settings or consent.

The affected analysis forms use `novalidate`: browser constraints cannot depend
on the selected mode without script. Existing server validators validate the
effective controls and associate errors with their actual native fields, opening
the containing disclosure. Thus a stale inactive invalid custom count cannot
prevent an explicit ordinary-mode post. Numeric constraints remain inspectable
on the controls. No new route or form owner is added.

**Additional reviews** separately contains the existing tactical, coaching,
snapshot and provenance outputs where supported. Selections are independent of
effort, retain existing Search budgets, and still pass the original prerequisites
and incompatible-family validation. Search, Auto, Information-set Search and
explicit simulations remain custom configurations; no effort maps to the
unbounded evaluation profile or introduces a Search-budget identifier.

## Retained rollout authority

The old parser's unconditional 30000-ms timeout is replaced with explicit preset
resolution or owner-supplied retained settings. Session resolution runs after
active-owner, exact selection, accepted-document and fresh disk checks under its
existing lock. Match resolution runs after attachment, fresh file, revision and
bound-decision checks under the Workspace lock. Retained configuration must match
the exact source and selected decision; a prior validated attempt may retain its
effective timeout even when the previous completed output remains displayed.

Custom edits preserve 5000-ms, 60000-ms and other valid existing timeouts, plus
unexposed preparation/transition limits. Hidden client timeout fields are rejected.
An explicit ordinary preset can replace the timeout according to the table.
Publication continues to use existing source/generation/attempt guards; stale or
incomplete work cannot become an ordinary complete ranking or overwrite a prior
completed execution. Original downloads are retained unchanged on rejection.

## Existing opponent information

The ordinary **Use available opponent information** choice is shown for Match
decision/Historical paths when their actual prepared statistics are eligible.
Decision presentation excludes the acting player's own statistics. Strictly
before-Match eligibility, missing-time behavior, defaults, confidence and original
policy precedence are unchanged. With no eligible source, the legacy setting
remains inspectable in Technical settings with explicit unavailable-source text.

Guided Position's legacy profile flag stays technical and explicitly does not
establish usable player bindings. Session/manual Historical paths acquire no
profile adapter. Whole-game rollout has no profile checkbox and continues to
use its fixed policy. Saved Player names alone are not statistics bindings.

## Developer verification

Focused development checks precede the final complete-module selection below.
The selection follows the changed private resolver, guided draft/parser/renderers,
Session/Match owners, retained rollout/form consumers, registry/resource smoke
consumer, localization/value-preservation paths and source architecture guards.
Shared Capture parsing and the public engines are exercised through their real
callers, without changing their contracts. Archive/accounting/UAT scenarios are
not repeated merely because they call the same server.

Final parallel command (development CPython 3.13; two file-grouped workers; no
worker restarts; external cache, temporary files and JUnit output):

```powershell
py -3.13 -m pytest tests/test_analysis_controls.py tests/test_analysis_controls_web.py tests/test_guided_position_form.py tests/test_guided_historical_review_form.py tests/test_guided_frontend_contracts.py tests/test_guided_frontend_execution.py tests/test_guided_frontend_json_transfer.py tests/test_guided_frontend_packaging.py tests/test_guided_frontend_web.py tests/test_unified_local_app_managed_items.py tests/test_unified_local_app_web.py tests/test_task_first_stateful_rendering.py tests/test_task_first_language_preservation.py tests/test_frontend_validation_preservation.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py tests/test_frontend_language_switching.py tests/test_language_view_continuity.py tests/test_language_switch_context.py tests/test_session_recorded_review.py tests/test_session_recorded_review_web.py tests/test_session_whole_game_review_web.py tests/test_recorded_review_compact_forms.py tests/test_recorded_review_objective_default.py tests/test_match_rollout_web.py tests/test_match_rollout_retention.py tests/test_match_decision_selection_web.py tests/test_recorded_review_navigation.py tests/test_packaging_and_distribution.py tests/test_skatmind_rename.py tests/test_cli_internal_architecture.py -n 2 --dist=loadfile --max-worker-restart=0 -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-final --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-final.xml -q --tb=short
```

After every parallel worker exits, run the complete affected Match action-placement
module exclusively, then Quick and tracked/new-file whitespace checks:

```powershell
py -3.13 -m pytest tests/test_match_analysis_action_placement.py -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-exclusive --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-exclusive.xml -q --tb=short
.\scripts\check.ps1 -Mode Quick -LogDirectory C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-quick
git diff --check
```

Every validation invocation uses a 7200000-ms timeout. The final implementation
report records actual results, corrections/rechecks and new-file whitespace
verification. Quick covers Ruff, packaged-schema parity and input examples; it
does not establish complete regression, generated-output or installed acceptance.

The Match projection fixture used by the exclusive module also requires the
complete `tests/test_match_game_navigation.py` module. Its minimal private owner
now supplies the new empty control slots and explicit selected-position fields.
Run that module with the same parallel-worker settings; run both rename and CLI
architecture guards against this final documentation before the exclusive phase.

### Compact source-browser observation

`scripts/verify_analysis_controls.py` uses a disposable synthetic complete Match
and real native controls in source-checkout Edge **157.0.4341.60**, development
CPython **3.13.7**, with page JavaScript disabled throughout. The completed report
is outside the repository at
`%TEMP%/opencode/issue325-browser-07/report.json`.

The English/German sequence verified initially closed Technical settings, Standard
initial mode, a genuine Quick execution at 25 worlds/5000 ms, a custom invalid-seed
retry with the correct disclosure opened, and custom 2-world/seed-19 execution
retaining 5000 ms even after changing effort to More time. A separate Historical
form retained its selected tactical output and eligible opponent-information
choice through invalid-count feedback and both languages. Rollout offered no
profile application. Exactly **two analysis executions** and **zero recording
saves** occurred. Native Request/Result downloads matched retained documents;
their hashes and the unchanged synthetic source hash are recorded.

This is native-keyboard/DOM developer evidence, not installed UAT or visual-layout
acceptance. Earlier attempts diagnosed a browser screenshot timeout and harness
selection/navigation synchronization; no screenshots are claimed. The completed
compact check uses no screenshot or zoom acceptance claim.

## Guided archive compatibility correction

Published-source review of #325 identified a persistence regression at
`5a30af915bdecb93fb99d39aa636571d420714f9`. The maintainer reports successful
partial feedback run `44204448322` at that exact commit; complete main acceptance
has not occurred. This correction starts on the same branch and commit with a
clean index/worktree.

### Demonstrated failure

`HistoricalFormDraftV1.analysis_form_values` is private process-local UI state.
The former archive writer recursively encoded `asdict(draft)`, accidentally
adding this field to the canonical producer representation:

* A pre-#325 wire reconstructed with the new default `None` gained an extra
  field on reserialization. The unchanged strict comparison rejected it with
  `Guided source must retain its completed producer draft.`
* A new draft with real `FormValuesV1` controls had that immutable value converted
  into a dictionary by `asdict()`. Reconstruction rejected it with
  `analysis_form_values must be private immutable form values.`
* A same-candidate roundtrip with the field set to `None` passed before the fix,
  demonstrating why that test alone did not establish compatibility.

The affected old source is classified as corrupt by admission. A fresh native
producer can return a successful analysis response while reporting persistence
`unavailable`. This is a source/producer compatibility defect, not evidence that
every object or the entire archive fails.

Before changing production code, a disposable source-only probe loaded the
accepted `fca6b3a1defe8a6320bbf8a8ee73840e7af26b46` versions of
`historical_form.py` and `automatic_historical_evidence.py` directly with
`git show`. Using the genuine completed Historical example and result-only
options, the baseline writer and decoder accepted the original bytes. The
candidate rejected both their guided wire and source. The frozen regression
fixture is `tests/historical_pre325_fixture.py`; it is not generated by the
candidate writer and requires no Git history during normal tests. Test-only
compression does not change the archive format.

| Frozen baseline fact | Value |
| --- | --- |
| Canonical source payload size | 11957 bytes |
| Stored source size | 12062 bytes |
| Source payload SHA-256 | `44bc213aa3d525d5d3ed9703efabb01cf8a428784b510e8dad6ca98fc112af0b` |
| Guided wire SHA-256 | `16d425c4b46a1a37944207bd989511ca874fc1b3a0f036260e3ccab1feafa7a3` |
| Source content fingerprint | `4ab5c0dfae81e65124d46ac9a79feab1f92e49761a9b034d46f6ae8cb793741a` |

The pre-fix focused run failed both new regressions: legacy wire rejection and
native persistence `unavailable` instead of `saved` (**2 failed, 13.97 s**).

### Stable persistence boundary

`automatic_historical_evidence.draft_wire()` now explicitly projects the seven
original producer fields, in their original order, before recursively encoding
their existing values:

```text
step, players, skat, declaration, discarded_cards, plays, options
```

Nested player/declaration/play/option representations and tuple/scalar types
remain those of the accepted writer. UI values are never traversed, archived,
or included in source/envelope identity. The decoder, canonical comparisons,
source/execution reconciliation and corruption handling remain strict. No codec
version, migration, rewrite, limits change or deletion is introduced.

The current process retains its ordinary/custom controls, inactive values,
validation retries and language state. Archived reopening restores the actual
executed options and original downloads; ephemeral UI-only values are not
reconstructed from storage. Fresh manual Immediate Review initialization and
deliberate result-only execution retain their existing behavior. Standalone
manual Reviews remain excluded from Learning.

### Bounded verification

The source-only probe accepts the same frozen legacy wire/source and the new
UI-bearing draft after the correction, with the unchanged source payload hash.
The new focused tests passed **10 tests in 85.86 s**. Coverage includes:

* Exact frozen source bytes, original fingerprints and source-local identity.
* Store admission/restart without archive writes, plus native saved-source reopen.
* One genuine native ordinary Quick Review: 25 effective samples, seed 11,
  successful persistence and reopen, with inactive custom sample text preserved
  in the original process-local draft.
* Reuse of one genuine result-only execution across UI-only identity comparisons.
* Exact effective options and original Request/Result download bytes.
* Continued `ineligible` classification of the successfully saved standalone
  manual Review for automatic Learning.
* Rejection of extra UI fields, reordered producer fields, changed scalar types,
  contradictory cards and the existing rehashed source/execution corruptions.

The correction changes only the archive projection in production. Guided form
state/handoff, owner/lifecycle/reopen implementation and production imports or
layering are unchanged. Consequently the complete core evidence, admission and
web modules plus the rename guard are sufficient; no extra guided-control,
lifecycle, architecture, exclusive or unchanged browser/UAT replay is required.

Use development CPython 3.13, two file-grouped workers, no worker restarts,
external cache/output paths and a 7200000-ms timeout for every invocation:

```powershell
py -3.13 -m pytest tests/test_automatic_historical_evidence.py tests/test_automatic_historical_admission.py tests/test_automatic_historical_web.py tests/test_skatmind_rename.py -n 2 --dist=loadfile --max-worker-restart=0 -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-complete --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-complete.xml -q --tb=short
py -3.13 -m pytest tests/test_skatmind_rename.py -n 2 --dist=loadfile --max-worker-restart=0 -o cache_dir=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-cache --basetemp=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-docs --junitxml=C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-docs.xml -q --tb=short
.\scripts\check.ps1 -Mode Quick -LogDirectory C:/Users/HENNIN~1/AppData/Local/Temp/opencode/issue325-compat-quick
git diff --check
git diff --no-index --check -- /dev/null tests/historical_pre325_fixture.py
```

The complete four-module run passed **72 tests in 157.29 s**, with no skips or
failures. Only this validation record was finalized afterward; the second
command checks the complete rename guard against the final documentation before
explicit Quick and whitespace verification. Their final results are recorded in
the implementation report. Logs and disposable reproduction artifacts remain
under `%TEMP%/opencode/issue325-compat-*` and
`%TEMP%/opencode/issue325-pre325-*`. No real maintainer data is used.

## Acceptance boundary

Issue #325 and #208 remain open. After required local checks succeed, report
**locally validated; hosted acceptance pending**. The established sequence is
automatic partial branch feedback, published-source review, maintainer integration,
automatic complete exact-commit main `check` and `v1-supported-platform-matrix`,
then one later narrow installed check of these controls with existing data.
There is no manual Check dispatch or intermediate maintainer UAT.

For that later maintainer check: inspect the ordinary mappings in one existing
recording; select a preset explicitly; reopen and edit custom settings without
resetting its timeout; verify one native retry/language return, an additional
output and the actual opponent-information availability. This document creates
no UAT environment or installed artifact. Public schemas, API/CLI defaults,
recording formats, original retained artifacts, Learning eligibility, #324 waiting
behavior and release authorization remain at their accepted boundaries.
