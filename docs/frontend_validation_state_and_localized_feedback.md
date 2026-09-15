# Frontend validation state and localized feedback

## Status

Issue #218 implements safe submitted-form preservation and localized validation
feedback in the private unified local frontend. It implements the frozen policy:

```text
validation_preserves_safe_values_and_workflow_context
```

It changes no Skat rule, Product algorithm, persistence format, Public API, CLI,
Root workflow, Schema, example, generated output, dependency, or Package version.
Standalone `skatmind capture`, `skatmind corpus`, and `skatmind session` behavior
remains unchanged.

## Contract Identity

The private contract identity is:

```text
FRONTEND_VALIDATION_PRESERVATION_VERSION = 1
```

`FrontendValidationIssueV1` retains only a locale-neutral message key, an
optional registered field key, and bounded interpolation arguments.
`FrontendSubmittedFormStateV1` retains one rejected form key, originating route,
active-family binding, optional Review step, optional opaque rendered-form
ordinal, allowlisted visible values, structured issues, status, and process-local
feedback generation.

These immutable values are private implementation contracts. They are not Public
API exports and are not persisted.

Issue #225 adds exact Settings editor/preview/confirmation routes and changes the
two private creation forms to seat-named fields and setup-only/final submitters.
Operational profile origins are `/settings`. New native save-Players, save-platform
and Advanced-expansion checkboxes preserve unchecked omission as false. Confirmation
controls and editor/setup transport selections are excluded from the language
envelope. Collision feedback retains independent seat input without swapping Players.
See [Settings and Player seat setup](settings_and_player_seat_setup.md).

Issue #233 reuses the same `session.create` form and exact `capture_mode` values
for [knowledge-based entry](session_knowledge_based_entry.md). Its missing-perspective
message identifies the Player whose initial hand is known, during or after a Game.
Field targeting, accepted values, safe roster/radio retention and regenerated
language/setup bindings are unchanged; no invalid setup generates IDs or saves data.

## Canonical Form Registry

`FRONTEND_FORM_REGISTRY` covers all 59 unified frontend POST routes through 103
exact definitions. Shared routes are split by their existing discriminator:

```text
Session Command kind
Match mutation operation
Match analysis operation
Learning operation
```

Each definition records its media type, request bound, safe visible fields,
cardinality, control type, fixed choices where applicable, originating page,
active context, Review step, upload reselection rule, success redirect, and
contextual failure page. Registry validation rejects missing routes, orphaned
routes, duplicate identities, and incomplete Session or Match operation coverage.

The registry excludes revisions, optimistic fingerprints, tokens, cookies,
caller paths, caller filenames, and other hidden transport or private state.
Opaque known-Player and managed handles may be retained only as bounded hidden
or select identity values for exact form targeting; they are never visible IDs
or raw error text. File inputs and destructive confirmations are never
retained. Text and repeated values are bounded; fixed select and radio values
use explicit allowlists; Card selections use canonical Card limits. Omitted
checkbox and repeated Card groups retain an explicit empty presentation value so
a rejected form does not restore an older accepted selection.

Issue #221 adds `session.review_decision` at `/sessions/review-decision`.
Only its 64-character opaque `decision_selection` may be retained for exact form
targeting. Expired selections receive feedback at the recorded-decision section.
Same-context `400`, contextual `409`, and native language return keep the Session
selected; source labels and retained Request/Result bytes remain atomic. See
[Review recorded Session decisions](session_recorded_decision_review.md).

Issue #222 adds four exact private Match recovery forms. Only the replacement
Card and opaque selection are safe retained fields; Apply confirmation is cleared.
Typed authoritative trace diagnostics are captured before generic mapping, and
stale recovery feedback stays beside the selected Game's recording controls.
See [Match recording error recovery](match_recording_error_recovery.md).

When one definition has several rendered instances, the unified renderer adds a
bounded process-local ordinal hidden field. It identifies only the rendered form
instance and contains no Product identity. Multipart forms are not instrumented.
The standalone Capture and Corpus renderers are not modified.

## Accepted And Submitted State

Issue #230 adds five exact local-time/Settings forms with narrow `time_form` markers,
source-bound `time_selection`, current profile generation, native date/time/zone
controls, explicit Keep/Replace/Remove and occurrence choices. The unchanged raw
RFC 3339 forms remain a separate legacy adapter; mixed representations are rejected.
Safe local controls/errors reuse #223 preservation, with occurrence choices excluded
from language envelopes. HMAC choices bind exact input, provider version and source.
Gaps, partial date/time, unavailable zones, stale selections and save failures have
specific bilingual `400`/`409` feedback. See [Local time entry](local_time_entry.md).

Issue #229 adds value-free `recordings.open` selection with a separate bounded
feedback family, contextual chooser `400`/`409`, and existing explicit Reload.
Match analysis from its focused review view includes private exact-source
`review_binding`, removed before existing Capture parsing. Safe options stay on
that selected review task on failure. Landing/chooser rendering does not discard
feedback bound to an active source; real source/Game changes retain invalidation.
Language return retains exact discoveries, Game and Report context. See
[Home and recorded-game review navigation](home_and_recorded_review_navigation.md).

Issue #228 adds four exact compact-declaration marker definitions on the existing
Session Command and Match operation routes. Their native checkbox types, localized
labels and safe empty values are scoped; legacy explicit parsers are unchanged.
Private reasons from canonical declaration checks and existing typed Session
diagnostics provide field feedback without a duplicate acceptance table. Exact
`declaration_selection` identity prevents stale draft restoration into a different
source or correction target. Current controls are regenerated; stale values remain
separate unaccepted text without internal declarer IDs. Match trace conflicts retain
#222's actual diagnosis. See [Compact Game declaration](compact_game_declaration.md).

Issue #226 registers three private Card routes and six exact definitions. Their
opaque `card_selection` binds complete source content and the current task;
Session batch sets and single Plays have distinct cardinalities. Valid members
of rejected compact sets are retained without silently accepting duplicates.
Unavailable attempted Cards remain plain rejected input, and missing/stale bindings
cannot restore selections into a new actor's form through a matching ordinal.
Structured diagnostics, contextual `400`/`409`, recording anchors, and exact #223
language restoration are documented in [Compact Card entry](compact_card_entry.md).
Issue #231's [direct Session startup](session_direct_card_start.md) reuses those exact
fields and bindings. Failure publishes neither missing identity nor a Card prefix;
empty/checked initial selections retain the same task through language restoration.

Rejected submitted state is separate from authoritative Product and accepted
workflow state. Validation occurs before Product creation or mutation wherever
the existing operation permits it. Analyze candidate execution validates and
executes without accepting its draft; only successful publication atomically
accepts the draft and Result.

A rejected Analyze or Review attempt does not advance its accepted revision,
replace its draft or imported Request, clear its last successful Result, or
replace Request/Result download bytes. Review parser rejection therefore remains
on the exact accepted wizard step. Session, Match, and Learning rejection keeps
the exact active managed context. Existing Product conflict results remain
authoritative, but their raw messages are not used as frontend validation text.

The process-local feedback store retains at most one rejected attempt for each
of these families:

```text
analyze
review
profile
local_settings
sessions
matches
learning
```

A later rejection replaces the prior attempt in that family. Successful form
submission clears that family's feedback. Switching an active Session, Match, or
Learning Corpus invalidates feedback bound to the previous exact active object.
Closing the process discards all feedback.

## HTTP And Rendering

Successful browser actions retain POST/Redirect/GET and HTTP `303`. Normal
validation and unsupported-workflow failures return contextual HTML with HTTP
`400`. Stale form, optimistic persistence, duplicate identity, and Product
conflict failures return contextual HTML with HTTP `409`. Existing `413`, `415`,
authorization, method, not-found, and generic internal-error boundaries remain
in force. Shared-route failures that occur before one unique registered
discriminator and media type can be recovered remain fixed, localized, form-
agnostic errors; they never bind feedback to an arbitrary form.

Once the originating form is uniquely identified, the failed response renders
that form rather than a generic error page. Safe values are applied to text
controls, textareas, checkboxes, radios, repeated Card controls, and selects. The
Review disclosure containing the exact accepted step and any disclosure
containing the failed form or failed field is opened. Issue #219 creation errors
may declare their exact registered field. Repeated Player and managed-label
forms bind feedback to opaque form identity values so only the rejected item is
annotated; if that exact item is no longer renderable, a page-level summary is
used instead.

Each response contains one translated error summary for the rejected form and
translated field-local messages where a visible control exists. The summary is a
focus target with `role="alert"`; summary links target the corresponding control;
controls use `aria-invalid="true"` and `aria-describedby`; focus styling and
status presentation do not depend on color alone. If a prior valid Result remains
visible, the summary says that it was retained.

Translation occurs from structured message keys at render time. A language
change preserves the rejected form and values, then renders its summary and
messages in the newly selected German or English locale. Technical contracts,
Routes, field names, and Product values remain English and locale-neutral.

## Uploads And Security

Upload failures never reflect file paths, filenames, bytes, or multipart
metadata. The user receives a localized size, media-type, invalid-file, or
unsupported-workflow message and, when the exact upload form is identified, an
explicit instruction to select the file again. Failures before form identity is
available use only a fixed localized generic response. Successful parsed upload
content is never retained as submitted-form state.

Known exceptions are mapped to a finite localized vocabulary. Unknown validation
exceptions use one generic Product-rejection message. Browser output therefore
contains no raw exception text, stack trace, filesystem path, visible managed or
Player handle, token, cookie, fingerprint, hidden Card, or uploaded document.
Opaque handles may remain in bounded hidden/select values and are never copied
into validation messages. Existing escaping,
loopback binding, Host/Origin checks, app cookie, Content Security Policy,
`Referrer-Policy: origin`, no-CORS, and no-external-request boundaries remain
unchanged.

## Packaging And Verification

The implementation consists of private `skatmind.app_web` modules plus the
existing packaged German/English catalogs and `app.css`. Wheel and sdist
discovery includes the Python modules automatically; existing Package Resource
rules include the changed catalogs and stylesheet.

Focused tests cover immutable contracts, exact registry coverage, safe-value
limits, feedback lifecycle, exact form-instance targeting, repeated-select order,
German/English render-time translation, accessibility, accepted Result
retention, contextual Analyze/Review/Session/Match/Learning responses, upload
reselection, POST/Redirect/GET, standalone regression, and Package discovery.
Issue #219 adds profile-driven creation/settings, language-switch retention,
exact repeated-form identity, Advanced-field opening, and Product-first/profile-
second failure coverage.

## Current Boundary

Issue #218 implements the validation-preservation policy and further partially
remediates `UAT-FINDING-001`. Its assigned implementation for
`UAT-FINDING-006` is complete, but that finding remains open until repeated
maintainer UAT-01. UAT-02 through UAT-12 remain paused; B-09 and B-07 remain
open; Package `1.0.0` and Release preparation remain not ready.

Issue #219 integrates profile-driven Session, Match, and Learning creation,
friendly fields, generated internal IDs, known-Player selection, saved defaults,
and local display labels into this validation layer. Its implementation is
documented in [Profile-driven stateful creation](profile_driven_stateful_creation.md).
Issue #220 implements task-first active layouts, nested-disclosure error opening,
and complete workflow translation through this same registry.

Issue #223 replaces the shell dropdown/Apply pair with native absolute-target
Deutsch/English buttons. Known rejected creation pages now emit their semantic
HTML origins rather than Home. A validated return origin is captured before
optional presentation parsing, so a malformed language envelope does not erase
the affected task or its unrelated Product feedback. Rejected language choices
never become the active-language indicator.

Its optional packaged enhancement transfers only registered visible controls.
The 262,144-byte UTF-8 envelope has at most 256 exact form identities and 1,024
disclosure states. Empty/false/repeated values remain distinct from omission;
validation-required disclosures stay open. Files, passwords, hidden transport,
secrets, and destructive confirmations are excluded. Client bound failures prevent
navigation with localized feedback rather than dropping the draft.

Restoration is bound to an opaque rendered page, exact immutable source/context,
relevant generations, selected Game/Report or Review step, and stable repeated-form
identity. It is checked before preference saving and again before restoration.
Transport fields are regenerated, including fresh profile generations, without
accepting stale Product revisions. Pre-save conflicts make no change; a source
conflict after a valid preference save retains that language and drops the overlay.
The messages distinguish these outcomes. No source is automatically reopened.
The existing Report-transfer definition additionally retains its bounded opaque
Report ID only for exact feedback targeting. Match position navigation clears
the previous Game's rejected form feedback instead of applying it to the new Game.

Native switching retains accepted state and already submitted safe rejection
state without JavaScript. Unsent browser-only input in another form requires the
enhancement and cannot be recovered by a JavaScript-disabled server. Neither mode
accepts Product facts, persists drafts, or implicitly saves entered settings.
See the [exact language/profile boundary and browser evidence](local_frontend_profile_and_localization.md#semantic-origin-and-exact-presentation-binding)
and [Task-first bilingual stateful workflows](task_first_bilingual_stateful_workflows.md).
