# Match declaration drafts across evidence submissions

Issue #292, Finding A only. This is private unified-browser presentation over the
existing Match operations. A draft is never a saved declaration, an analysis
input, a reconstruction fact, or an export field.

## Native ownership and action map

There is one visible declaration editor and one native owner,
`form#match-recording-input`, posting to `/matches/recording-input`. The existing
evidence panels stay in their existing locations. Their actual checkbox controls
and submit buttons use HTML's `form` attribute to belong to that owner. There are
no nested forms, duplicate editable declarations, script-populated hidden draft
copies, or browser-storage drafts.

| Explicit submitter (`recording_action`) | Selected existing operation | Evidence field |
| --- | --- | --- |
| `set_declaration` | Compact declaration Save | None |
| `perspective_hand_selected` | `set_perspective_hand`, exact | `evidence_perspective_hand` |
| `original_skat_selected` | `set_original_skat`, exact | `evidence_original_skat` |
| `discarded_cards_selected` | `set_discarded_cards`, exact | `evidence_discarded_cards` |
| Each corresponding `_unknown` | The same operation, unknown/withdrawal | None |
| `discarded_cards_empty` | `set_discarded_cards`, known-empty | None |

Only the clicked/keyboard-activated submitter supplies `recording_action`.
Missing, duplicate, foreign, or ambiguous actions are rejected before mutation.
All three evidence selections can travel with the form, but only the selected
operation's selection is translated into canonical `cards`. Withdrawal and
known-empty ignore the still-visible selection, as their labels promise.

An enabled hidden declaration submitter precedes all associated evidence buttons
in document order. HTML's [implicit submission rule](https://html.spec.whatwg.org/multipage/form-control-infrastructure.html#implicit-submission)
therefore routes Enter inside `bid_value` or `matadors` to declaration Save even
when the visible editor is later in Corrections. This submitter has the same
`set_declaration` intent and normal constraint validation, is hidden from the
visible/accessibility layout and Tab order, and duplicates no editable controls.
Explicit evidence buttons still supply only their own intent and retain
`formnovalidate`. No input/change/blur event triggers a save.

Evidence submitters use `formnovalidate`: incomplete required declaration selects
cannot block evidence entry. Declaration Save retains native required controls
and the existing compact server parser. There are no new numeric browser
constraints. Server-side evidence counts, ownership, accepted Hand/declarer/Game
type, continuation rules, and CAS persistence remain authoritative. Uncommitted
Hand/declarer/type controls never change evidence eligibility. Existing editable
declarations still use their existing whole-candidate validation; clearing and
history correction/preview/consent remain separate actions.

`match_declaration_drafts.py` normalizes only this owner's external fragments
before the existing validation/language renderers, then moves each fragment back
to its original location before delivery. It moves controls, rather than copying
them. Native `form.elements` therefore works for the existing enhanced language
capture. The scoped Card-field rendering preserves fieldsets, selected Cards,
error links, disclosure opening and validation-focus priority. Other forms retain
their existing ownership. JavaScript only enhances presentation; the evidence
submission and restoration protocol is identical with scripts disabled.

## Presentation payload and allowed source transition

The registered visible declaration fields are `declarer_player_id`, `game_type`,
`bid_value`, `matadors`, and the four existing announcement flags. Their exact
strings, explicit blanks and absent unchecked flags are retained. Structural
cardinality, registered reflection bounds, selectable values, actual participant
identity, and original source authority are checked before evidence mutation.
No declaration object is constructed on an evidence action. Semantically invalid
numbers or incompatible announcement combinations can remain a draft.

The route retains the 8,192-byte evidence body limit and 256-field URL-encoded
parser limit. Only the three named evidence fields permit repetition, with at
most 32 bounded values each. The common single-field/unknown-field parser is not
relaxed. HTML reflection uses the existing safe escaping. Neither drafts nor
private source contents are placed in URLs or application diagnostic logs.

The original authority is the existing domain-separated declaration HMAC over
the active handle, movement generation, content fingerprint, complete Workspace,
selected position and actual Game ID, signed with the active context's private
Card-entry key. Revision/position controls must also match. The direct-child
recording is loaded and compared to the exact in-memory Workspace and fingerprint.
The family lifecycle gate and Capture lock cover validation, the single selected
operation, and successor verification.

The only permitted transition is:

1. The same active context, handle, position, movement generation and private key.
2. Either the complete Workspace is unchanged (no-op/recoverable rejection), or
   its revision increases by exactly one and **only** the selected Game's one
   evidence field changes. The complete before/after dictionaries are compared
   after substituting that field and the single revision increment. All other
   Games, metadata, accepted declarer/declaration, Plays and annotations must agree.
3. The resulting on-disk document must equal that exact successor and fingerprint.

Thus revision equality alone cannot authorize restoration. A same-revision
different-content replacement fails the file check. A competing declaration save,
unrelated source edit, another Game/Match, away-and-back movement, Reload or reopen
cannot qualify as the authorized evidence successor.

## Return lifetime, rejection and language

An accepted/no-op action creates at most one process-local return in the active
Match context. A 303 carries only a random opaque `_declaration_return` token to
the same position. The return expires after 60 monotonic seconds. It is consumed
before validation, including on failure, and checks exact context object identity,
fresh successor HMAC and actual recording bytes again. A normal recording GET
without the return token invalidates an undelivered return; replay/refresh of a
consumed return cannot restore it. New authority and revision controls are rendered
from the accepted successor; old hidden controls are never overlaid.

A recoverable validation rejection uses the same one-use object for its immediate
error render against the unchanged source. A prepublication storage failure can
also restore only after unchanged-source verification. Evidence feedback retains
its selected Card values and priority. Declaration draft values are excluded from
the single rejected-form slot on evidence attempts. Structural malformed requests
do not acquire a handoff. Unsafe restoration shows the localized draft-conflict
message and never overlays accepted facts.

For native language return after an evidence submission, the existing bounded
language-page registry may retain the already verified declaration presentation.
It remains separate from rejected-form state, has the same absolute 60-second
deadline, and is one-use per rendered language binding. Language switching does
not renew the deadline. Existing complete source, file and manifest checks still
apply. The enhanced language envelope continues to capture current unsent visible
values; native language switching can preserve only the already submitted draft,
not later unsent changes. Language submission is an explicit profile operation;
evidence/draft transport itself performs no profile write.

The direct return and every language-page copy also share one revocable private
`DeclarationDraftAuthorization` identity. The active Match holds only its current
identity. An ordinary recording GET revokes it, even for the same position and
unchanged Workspace revision/generation. An older unused language form can no
longer resurrect a delivered draft. The identity is checked at language submission
and again when a prepared language return is consumed/rendered, so an intervening
ordinary GET also invalidates an already prepared return. Only a language return
carrying that same current authorization preserves it. New evidence submissions
replace the authorization; retirement/reopen also invalidates it. These identity
checks perform no I/O or nested Product-lock acquisition under the app lock.
Existing source, file, manifest, one-use and absolute-deadline checks still apply.
Unrelated language pages are not cleared and Product generation is not changed.

## Compatibility and derived inventories

Independent `/matches/cards` and compact `/matches/api/v1/operation` callers remain
supported without draft fields. Their parsers retain their strict fields. Exact
current-source legacy evidence errors can target the new visible evidence editor;
stale/foreign legacy errors cannot populate it. Standalone Capture, Session,
evaluation, public schemas, persistence formats, dependencies and package version
are unchanged.

Current definitions derive **73 POST routes**, **125 registered forms**, and
**2,034 keys in each de/en catalog**. This change adds one private route, one form
definition and one paired conflict message. Packaging's exact registry assertions
now include the new route, body bound and exact safe-field set. The strict
case-sensitive rename inventory is executed without weakening its line/hash
assertions; no historical counts are used as final-state proof.

## Regression and browser evidence

The initial failing command was:

```powershell
py -3.13 -m pytest tests/test_match_declaration_drafts.py -q
```

It failed at the returned declarer value after a real persisted H7/D7 save. Browser
verification uses the actual emitted controls, native pointer/keyboard input,
real persistence and disposable profiles/data. It does not inject declaration
fields into evidence HTTP requests. The first probe selected Anna because it
assumed option order; its screenshots exposed that verification mistake. The
corrected probe selects Bea by the visible option label and verifies the choice.
The exact baseline is re-executed from a read-only Git archive of
`9709cb1420d8a9c2158f66d7665f7d7f896f6202`, with an assertion on the imported archive
module path. It reproduces **Bea / Grand / 18 → H7/D7 Save → empty declaration
controls** in de/en with JavaScript enabled and disabled. Accepted declarer and
declaration remain absent; revision changes from 1 to 2 and the fingerprint changes.

The optional browser command is:

```powershell
py -3.13 scripts/verify_match_declaration_drafts.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "<fresh-temporary-output>" --phase after
```

For the baseline add `--phase before --baseline-archive "<baseline.zip>"` instead
of `--phase after`. The archive can be produced with read-only
`git archive --format=zip --output="<baseline.zip>" 9709cb1420d8a9c2158f66d7665f7d7f896f6202`.
The output parent must exist and the output directory must be new.

The corrected browser sequence records the valid save, rejected single-Card
selection, unchanged save, explicit declaration Save, an incomplete/negative-bid
editing draft, native constraint blocking of declaration Save, an original-Skat
save despite that draft, and language return. Each of the four language/script
combinations measures actual Product calls, Save calls and `os.replace` recording
writes, draft-return consumption, analysis calls and profile writes separately:
Counters start after disposable Match/Game creation.

| Stage | Cumulative recording replacements | Declaration operations |
| --- | ---: | ---: |
| H7/D7 save | 1 | 0 |
| Invalid evidence | 1 | 0 |
| Unchanged evidence save | 1 | 0 |
| Explicit declaration Save | 2 | 1 |
| Original Skat with incomplete draft | 3 | 1 |
| Explicit language change | 3 | 1 |

Analysis calls remain zero. Profile writes remain zero until the explicit
language change, which writes once. The draft never appears in saved-declaration
summaries. Screenshots and submitted/returned controls are inspected at 1365×900
and 390×844. Viewport checks are not browser-zoom verification. This is bounded
headless Edge source-tree evidence, not maintainer-installed UAT, other-engine,
physical-device or assistive-technology acceptance.

Focused tests cover emitted native ownership, all evidence intents, exact empty/
unchecked values, semantically invalid drafts, escaping, failed storage,
independent compatibility requests, source replacement, concurrent saves, Game/
Match movement, reopen, expiry/replay and language lifetime. Existing correction,
Null-end (#290), persistence, validation, language, Session and Learning callers
are included in the complete affected-module runs.

Disposable evidence directories under the approved temporary `opencode` root are
`declaration-292-baseline-bea-verified` (exact baseline) and
`declaration-292-final` (final implementation). Each contains `evidence.json` and
the labeled screenshots. Earlier probe directories are exploratory evidence,
including the explicitly identified wrong-name probe, not the final acceptance
evidence.

The complete affected-module command is:

```powershell
py -3.13 -m pytest `
  tests/test_match_declaration_drafts.py tests/test_direct_match_evidence.py `
  tests/test_compact_declaration_web.py tests/test_compact_declaration_form.py `
  tests/test_compact_card_entry_web.py tests/test_task_first_language_preservation.py `
  tests/test_task_first_stateful_rendering.py tests/test_task_first_stateful_projections.py `
  tests/test_task_first_match_and_learning_workflow.py tests/test_operation_feedback_web.py `
  tests/test_operation_feedback_script.py tests/test_operation_feedback.py `
  tests/test_frontend_validation_preservation.py tests/test_null_recording_end_web.py `
  tests/test_null_recording_end.py tests/test_packaging_and_distribution.py `
  tests/test_skatmind_rename.py tests/test_frontend_language_switching.py `
  tests/test_language_switch_context.py tests/test_language_view_continuity.py `
  tests/test_language_view_script.py tests/test_operation_feedback_language.py `
  tests/test_match_recording_recovery_web.py tests/test_match_recording_recovery.py `
  tests/test_match_recording_diagnostics.py tests/test_match_workspace_persistence.py `
  tests/test_recording_deletion_lifecycle.py tests/test_learning_debrief_web.py `
  tests/test_session_recorded_review_web.py tests/test_match_game_navigation_web.py `
  tests/test_recorded_decision_context_web.py tests/test_session_declaration_correction_web.py `
  tests/test_session_declaration_correction.py tests/test_frontend_localization_foundation.py `
  tests/test_complete_frontend_localization.py tests/test_match_evidence_navigation.py `
  tests/test_match_game_navigation.py tests/test_recorded_trick_progress_web.py `
  tests/test_unplayed_card_summary_web.py tests/test_match_analysis_action_placement.py -q --tb=short
```

The same command includes strict rename-inventory and executable packaging-registry
assertions. The optional browser script uses CPython 3.13.7 and headless Edge
155.0.4283.62 in the measured local runs; it does not install dependencies.

The final local gate is explicitly:

```powershell
.\scripts\check.ps1 -Mode Quick
```

Full exact-commit hosted CI and the installed declaration-draft retest remain
maintainer gates. Keep #292 and #208 open; #289, #290 and #291 remain closed.
UAT-02–12 remain paused. Finding B remains separately pending.

## Follow-up after CI run 39503115230

The correction starts from clean branch `bug/292-match-declaration-drafts` at
`27431d03df7e4ee0e157ed4e0b3e191e68e5db4e`. Authenticated read-only access retrieved
the actual logs with:

```powershell
gh run view 39503115230 --repo hnnng-w/skatmind --log-failed
```

Both regression jobs reported the same 16 failed IDs:

```text
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[1-None-de]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[1-None-en]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[3-set_declaration-de]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[3-set_declaration-en]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[4-append_plays-de]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[4-append_plays-en]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[5-append_plays-de]
tests/test_match_game_navigation.py::test_selected_identity_controls_seats_and_single_overview[5-append_plays-en]
tests/test_match_evidence_navigation.py::test_missing_hand_review_has_one_named_visible_destination
tests/test_match_evidence_navigation.py::test_unknown_editors_do_not_depend_on_cards_or_prepared_count[started]
tests/test_match_evidence_navigation.py::test_unknown_editors_do_not_depend_on_cards_or_prepared_count[declaration]
tests/test_match_evidence_navigation.py::test_unknown_editors_do_not_depend_on_cards_or_prepared_count[3]
tests/test_match_evidence_navigation.py::test_unknown_editors_do_not_depend_on_cards_or_prepared_count[complete]
tests/test_match_evidence_navigation.py::test_returned_remedy_retry_save_review_lifecycle_and_frozen_session
tests/test_recorded_trick_progress_web.py::test_match_declaration_edit_null_and_faulted_apply_keep_accepted_progress
tests/test_unplayed_card_summary_web.py::test_match_real_completion_report_preview_correction_rewind_and_selection
```

The first eight expected the obsolete `card_evidence_form` hidden marker. The
missing-hand test expected one hidden `operation=set_perspective_hand` but found
zero. Four unknown-editor cases tried to submit unassociated intermediate
renderer fragments and raised `TypeError: 'NoneType' object is not subscriptable`
at `owner["action"]`. The remedy test expected the old five-field independent
payload instead of the new shared payload. The trick-progress test expected
`/matches/cards` on a rule-ended Null page; it had also retained a stale pre-#290
"no automatic stop" comment. The unplayed-summary test raised
`KeyError: 'card_evidence_form'`.

Windows job `118905409959` reported 16 failed / 10,980 passed. Ubuntu job
`118905410023` reported 16 failed / 10,978 passed / 2 skipped. The dependent
`check` job `118925929059` rejected with `gate_prerequisites_invalid` because
regression failed; it did not expose an additional test defect. The other 20
jobs succeeded. The workflow used CPython 3.13.15. This local reproduction on
CPython 3.13.7 produced the same 16 failures and 75 passes in 157.20 seconds:

```powershell
py -3.13 -m pytest tests/test_match_evidence_navigation.py tests/test_match_game_navigation.py tests/test_recorded_trick_progress_web.py tests/test_unplayed_card_summary_web.py -q --tb=short
```

These deterministic failures reproduce serially; no parallel-only failure or
Python-patch-version cause was established. New exact-commit hosted parallel CI
remains pending. No local Full or validation-architecture change is part of this
repair.

Submission tests now obtain real HTTP-rendered forms, including unknown/empty
evidence availability, named destinations, exact payloads and native ownership.
Projection tests continue inspecting intermediate renderer output as such. A
regression explicitly rejects using its unassociated fragments for submission;
the parser does not invent ownership. Equivalent explicit/implicit declaration
submitters yield one helper action view from genuine successful controls.
Independent Card-route compatibility remains covered separately. The Null test
now verifies the already implemented #290 stop while retaining evidence and
correction access; no Null behavior is changed here.

### Separate lifecycle and keyboard reproductions

Before correction, emitted-form regressions in both locales returned 303 instead
of the expected 409 when an old unused native language form was submitted after
an ordinary same-position GET. The browser probe confirmed the draft actually
reappeared. This is distinct from explicit recording Reload, strict reopen,
movement, and the earlier undelivered-return test. Regressions now cover each
boundary and an ordinary GET between language POST and its prepared GET return.
Legitimate immediate language switches preserve the submitted draft and original
absolute deadline.

Before correction, Enter in the bid field of an existing declaration selected
`perspective_hand_selected` and persisted a waiting ten-Card selection: one hand
operation/write, zero declaration operations. Enter in Matadors selected the same
evidence action again (a no-op). After correction both fields submit
`set_declaration`: one declaration operation/write each, no evidence write. A
semantically invalid Matador submission produces declaration validation feedback
with no mutation; incomplete required declaration controls block implicit Enter
without a POST. Explicit evidence actions still work with that incomplete draft.

`scripts/verify_match_draft_lifecycle.py` verifies these paths with real emitted
controls, native pointer/Tab/Enter events and disposable first/second browser
profiles. The second browser performs the ordinary recording GET while the first
retains its genuine older language form. The old form is never reconstructed or
injected. Each action records actual submitted fields, accepted state,
revision/fingerprint, Product calls, recording replacements and profile writes.

```powershell
py -3.13 scripts/verify_match_draft_lifecycle.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "<fresh-temporary-output>" --phase before
py -3.13 scripts/verify_match_draft_lifecycle.py --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --output "<different-fresh-temporary-output>" --phase after
```

The before phase was executed before Product edits. Evidence under the approved
temporary `opencode` root is in `declaration-292-followup-before` and
`declaration-292-followup-complete`. Both completed all four de/en × script-on/off
cases on headless Edge 155.0.4283.62. The after probe additionally exercises all
three evidence Save/withdrawal pairs and known-empty buttons with both pointer
and Tab/Enter activation, retaining the incomplete draft and validating no-op
behavior. Each changed evidence action writes once; no-op saves write zero times;
declaration/profile writes stay zero during those evidence actions. Stale language
submission now returns 409 with zero recording or profile writes, compared with
one explicit language-profile write and draft resurrection before correction.
The legitimate immediate language change writes only its profile preference.

The original central Bea / Grand / 18 → H7/D7 → explicit declaration Save browser
sequence was rerun unchanged in `declaration-292-followup-central`; all four cases
passed, including incomplete declaration/evidence and language handling. These
are source-tree checks, not installed UAT. The route/form/catalog inventories
remain 73 / 125 / 2,034 per locale; no new private endpoint or message is needed
for this follow-up.
