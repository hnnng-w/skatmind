# Compact Game declaration and bid entry

Issue #228 implements one private unified-browser interaction:
**choose the actual Game → enter the known bid → select announced options →
save explicitly → recognize the accepted declaration and continue recording**.

Issue #250 supersedes only normal **Session correction** entry below: accepted
declarer/declaration facts now lead to a source-bound prefilled editor, explicit
Check change, immutable verified preview and Apply/Cancel. Lossless/no-op Apply
uses a named submitter; partial first-rejection suffix removal requires a fresh
unchecked checkbox. Initial entry and legacy expert direct correction keep their
existing contracts. See [Session correction](session_undo_and_correction.md#normal-browser-declarerdeclaration-correction-issue-250).
The new private inventory is 67 POST routes / 112 forms and 1,657 paired catalog
keys. Source Command Matadors, explicit Boolean flags and blank-number semantics
remain authoritative; inferred analysis counts never prefill corrections.

## Optional count presentation (Issue #262)

R07a/b changes only the optional Matador field's presentation. Starting clean
`bug/262-optional-matador-entry` HEAD was
`4cd274db3df883b29d021de6ec78f01fda6d245a`, after integrated #261. The actual #262
specification, #208 R07 and supplied post-#259 width/help audit references were
checked against current callers. The older #228 evidence below remains historical;
it did not establish that the repeated Matador complaint was resolved.

| Caller | Count ID / help owner | Evidence boundary |
| --- | --- | --- |
| `task_first_session_rendering._command` | `session-declaration-matadors`; shared renderer | Current accepted mode, perspective and permitted ownership |
| `session_declaration_correction_rendering` editor | `session-correction-matadors`; same renderer | Exact #250 selected source; no later inferred count |
| `task_first_match_rendering.operation_form` | `match-declaration-matadors`; same renderer | Existing whole-candidate and continuation validation |
| Retained Session compatibility rendering branches | Marker-derived correction ID or `session-command-matadors` | Existing caller semantics; no restored normal direct-save path |

The field remains one native `input type="text" name="matadors"`, with its exact
submitted value. An opt-in `declaration-matadors` class limits only this input to
`7em` and available width. Its label's single `minmax(0, 1fr)` grid track prevents
intrinsic sizing from overflowing a narrow container at enlarged text. Label, help
and errors retain natural width. The generic input helper, bid, announcements,
standalone controls and workflow script are unchanged. No acceptance-related
attribute, numeric filtering, formatting, truncation or default is introduced.

The existing optional disclosure still opens for a supplied count or applicable
error. One concise paragraph combines unknown/blank guidance, all-type ranges,
the top-trump count and positive with/without-two example. Session adds one short
permitted-evidence/Live-defender restriction. Caller-specific `-help` and
`-evidence` IDs associate these with the field; validation appends its existing
error association. No nested help disclosure or Game-type JavaScript is needed.
Changing Game type without submitting therefore leaves the guidance truthful.

Blank stays `None`; Suit stays `1..11`, Grand `1..4`, and Null requires explicit
clearing. Positive bid semantics, exact source bindings, #223 safe-value/disclosure
restoration, #245 receipts and #250's nonrenewable Select/Edit/Preview/Apply/Cancel
lifetime remain. A verified preview is read-only. Live defenders still cannot
supply counts; Live declarer ownership must verify, and Retrospective requires the
complete deal. Match retains its distinct validation boundary. Formatting consults
no Settings identity, later hand or Report and adds no inference or Product work.

Current inventory remains **67 POST routes / 112 forms / 1,802 paired catalog keys**,
Package 0.17.0, Python >=3.13, AGPL-3.0-only, the existing dependency floors including
tzdata>=2026.4, and 98 scenarios. See
[measured before/after evidence](unified_workflow_visual_contract.md#optional-matador-entry-issue-262).
R07's empty evidence wrappers, initial-hand findability and Unknown/Exact controls
remain separate work, as do other audited residues and automatic-Learning decisions.

## Shared fields and accepted summary

`app_web/compact_declaration_rendering.py` supplies the same fields to active
Session and Match declaration entry and their existing correction surfaces.
Game type and optional bid are always outside disclosures. The earlier Session
decision to put bid input under Advanced is superseded. Both begin blank for a
new declaration; corrections start from their accepted source values. Four native
checkboxes share one compact labelled group. No selection submits the form.

The group distinguishes announced Schneider/Schwarz from achieved levels, and
declared Ouvert from later exposure. Short Suit/Grand dependency guidance is
replaced by the Null applicability explanation when Null is selected, using CSS
only. All four controls remain enabled and visible in either case. A retained
incompatible flag must be unchecked explicitly. Public-hand and event entry remain
separate operations.

One secondary Matador disclosure explains the optional positive count. It opens
for a supplied accepted count and for field-local count errors. The explanation
counts consecutive highest trumps held or absent from the top, beginning with the
Jack of Clubs, rather than a total of Jacks/trumps. With-two and without-two
examples both use `2`; the integer contains no polarity.

The shared accepted summary follows normal recording, before full history. It
shows the named declarer, Game type, all four actual Boolean values, entered bid,
and supplied count. Blank numbers say **Not entered**; Null Matadors say **Not
applicable**. Numeric zero is never used as an unknown sentinel. Summary input is
the accepted canonical declaration, not a rejected draft or a later inferred
Result value. It calculates no Game value or final-score readiness.

## Exact private HTML transport

All forms are URL-encoded and retain their existing route/body/security limits.
Common fields are singular `managed_handle`, `expected_revision`,
`declaration_form`, and `declaration_selection`. Existing optional
`_frontend_form_instance` is stripped by the common renderer/parser boundary.

| Route | Exact marker | Additional fields |
| --- | --- | --- |
| `/sessions/command` | `session-declaration` | `kind=set_declaration`, shared fields |
| `/sessions/command` | `session-correction` | `kind=set_declaration`, server-rendered `target_revision`, shared fields |
| `/matches/api/v1/operation` | `match-declaration` | `operation=set_declaration`, `match_position`, named `declarer_player_id`, shared fields |
| `/matches/api/v1/operation` | `match-clear` | `operation=set_declaration`, `match_position`, explicit `confirm_clear=on` |

Shared fields are required singular `game_type`, `bid_value`, and `matadors`,
plus zero or one occurrence of each of `hand_game`, `ouvert`,
`schneider_announced`, and `schwarz_announced`. A selected checkbox sends exactly
`true`; an unchecked checkbox sends nothing. The compact adapter supplies
**explicit false for every unchecked flag** to `GameDeclaration`. Empty bid/count
strings map to `None`. Nonempty numeric strings must be unpadded base-10 integers;
the canonical validator enforces their existing permitted values. No browser
min/max attribute is an acceptance authority.

Missing required controls, malformed markers/bindings, duplicate fields,
non-`true` selected flag values, foreign fields and incompatible route/kind/marker
combinations are rejected. Compact fields never enter a canonical Command or
Capture operation. `compact_declaration_form.py` produces only the existing
explicit `true`/`false` and nullable-integer transport for those translators.
`session_form_translation.py` and standalone `capture_web/operations.py` are
unchanged. Legacy explicit forms without private markers retain their existing
parsers; in particular, a missing legacy Session Boolean is still invalid.

The registry adds four definitions, with marker discrimination taking precedence
over the legacy kind/operation discriminator: **57 routes, 97 definitions**.
New checkbox control types and field labels are scoped to these definitions.
`declaration_selection` is a retained bounded opaque identity, never a visible
label or a restored hidden control. Markers and revision/position/target fields
are freshly rendered transport, not language-envelope input.

## Canonical dependency and information boundary

The existing normalizer remains authoritative:

* Suit/Grand Schneider announced requires Hand.
* Suit/Grand Schwarz announced requires Hand and Schneider announced.
* Suit/Grand Ouvert requires Hand, Schneider announced and Schwarz announced.
* Null Hand and Ouvert are independent. Announced Schneider/Schwarz and concrete
  Matadors do not apply.

No unchecked prerequisite is omitted to trigger the public omitted-value
normalization behavior. A dependency failure preserves every selected and
unselected option and names the requirements. Public omitted-versus-explicit-false
semantics remain unchanged.

Bid is optional and positive when supplied. Values such as `1`, `17`, `19` and
`9999` remain permitted: there is no new minimum 18, bidding ladder, Game-value
ceiling, clamping or overbid correction. Matadors remain Suit `1..11`, Grand
`1..4`, and absent for Null. Blank is unknown, without a promise of automatic
inference.

Session concrete counts still require verification under the actual mode,
perspective and evidence. Live defenders cannot supply a concrete count. Live
declarers need sufficient permitted ownership; Retrospective validation retains
the exact complete-deal requirement. Contradictions name the count without
revealing hidden Cards. The help recommends leaving an unverified optional count
blank, not supplying unknown opponent hands. Match retains its own existing
whole-candidate validation boundary. No new inference, final-Skat reconstruction,
score preview or recommendation is introduced.

## Structured feedback and lifecycle

`declaration_diagnostics.py` adds a private `DeclarationValueError(ValueError)`
carrier at the existing declaration checks. It retains a reason, affected field
and dependency requirements, while preserving every English technical message
and accepted/rejected combination. The compact frontend maps those reasons to
localized issues; it has no duplicate acceptance table or English-message parser.
The private guided Session operation result additionally retains the already
returned typed diagnostics for exact count-path/code mapping. No public diagnostic
or Session contract changes.

`compact_declaration_http.py` uses a domain-separated HMAC with existing context
keys. Session binding includes the managed handle, generation, complete persistence
document, marker and correction target. Match binding includes the handle,
position-movement generation, content fingerprint, complete Workspace, selected
position, actual Game ID and marker. Reopening, Reload, equal-revision different
content, moving away/back and another Game invalidate old forms. There is no
selection map or persistent/multi-tab draft model.

Dispatch acquires the family lifecycle gate and Product lock, with only a short
app-lock active-context lookup. Strict direct-child file freshness is checked
without app-locked I/O. Existing CAS remains the Save authority; no cross-process
transaction stronger than that existing boundary is claimed.

Initial Session entry calls the existing one-Command application, Checkpoint
collection and Save boundary. Correction renders its actual accepted declaration
Command and fixed target revision, using the declarer known before that target.
It invokes the existing explicit historical correction and retains its real
unchanged/applied/partial first-rejection suffix result. A second normal declaration
submission never becomes an implicit correction.

Match uses the existing complete-candidate declaration operation. It does not
reassign actors, repair or truncate Plays. A trace failure remains the original
`ObservedTraceError` and #222 linked diagnosis. A true no-op saves nothing and
preserves Reports/previews; real changes retain Report/Result/preview invalidation
and #227 progress recomputation. Specialist clearing uses its explicit confirmed
marker, so a missing normal Game/declarer cannot clear accepted evidence.

Malformed/invalid forms return contextual `400`, source/storage conflicts `409`,
and success `303` to `/sessions/current#session-recording` or selected
`/matches/position/N#match-recording`. `match-declaration` remains an exact editor
anchor. Relevant controls/disclosures and error-summary focus remain accessible.
Still-applicable rejected values restore only into the exact source-bound form.
Stale values remain separate unaccepted text, without exposing internal declarer
IDs or restoring obsolete tokens into a new source.

#223 native language switching preserves submitted safe errors and values. The
existing enhancement also preserves supported unsent values, including unchecked
flags and explicitly emptied bid/count, through exact form/source manifests.
Without JavaScript, unsent values in another browser form cannot be recovered.
Language changes do not save declarations, collect Checkpoints or execute analysis.

## Focused verification

`tests/test_compact_declaration_form.py` checks all six Game types and sixteen
explicit flag combinations against the existing normalizer, independent expected
combinations, legacy explicit parsing, nullable/positive/non-ladder bids, numeric
format/ranges and count preservation. Existing public omitted-value tests remain
unchanged.

`tests/test_compact_declaration_web.py` uses the real unified server, returned
#225/#226 creation/Card/declaration forms, canonical validation and persistence.
It covers one-save Session entry and reopen, dependency retention through both
languages, Live defender rejection/blank success, verifiable Live Grand-four,
Retrospective Grand-two and ownership mismatch, Null clearing, real Match
declaration/no-op/trace conflict/edit/reopen, explicit clear, stale/equal-revision/
wrong-Game/target/reopen forms, security and real #221 Result/download retention.
Fault injection is limited to failed prepublication Saves. Costly Retrospective
setup uses actual promotion/deal Commands; equal-revision source fixtures change
metadata while retaining the existing Game. Successful submissions are not mocked
and helpers never add missing checkbox values.

Focused compatibility runs covered #221–#227, declaration/Matador/Session/Match,
language/validation, standalone Capture/Corpus, security and packaging. An initial
904-case run had 902 passed, one skipped and one old all-Commands-visible assertion
failure. That assertion was updated for actual-target-only declaration correction;
the affected 84-test run passed. An earlier canonical/validation suite passed 430
tests. The corrected 33-module compatibility run passed **904 tests, one skipped**
in **319.26 seconds**. The final full-check output is reported separately against
the final tree.

The first full-check attempt passed Ruff, Schema parity, input examples and all
98 generated outputs, then stopped at an installed-smoke assertion that still
expected 93 form definitions. `scripts/validate_distribution_artifacts.py` now
expects 97 and checks the new declaration catalog keys in both locales. This is
a validation expectation update; its failed attempt is not a successful full check.
The corrected direct distribution validation passed for Wheel, sdist and clean
installs before the required complete rerun.

## Installed browser evidence

`scripts/verify_compact_declaration.py` reuses the dependency-free local DevTools
harness and an existing Edge executable. It rejects checkout imports for both
phases; `after` additionally compares 16 loaded source/module/resource hashes with
the checkout. Authenticated HTTP CSS/JS bytes are checked against loaded resources.
It adds no Package dependency, asset service or full-check browser requirement.

September 14, 2026 evidence used Python **3.13.7**, Package **0.17.0**, and headless
Microsoft Edge **153.0.4234.32**, with synthetic Players and fresh local data.
The baseline Wheel was built from `9f4a172c07d6aff26c2e378ac50ee90293150673` before
production edits. The final Wheel hash was
`75ba48067f4fc65810d0f275db60cf6a3aba766d5a66a14ad989e0876ee8b158`.

The final run completed **64 measurements** covering Session/Match normal and
dependency/Null error forms in de/en, JavaScript enabled/disabled, **1365×900**,
**390×844**, **320×800**, and **200% text at 320×800 in both languages**. Text
enlargement doubles each computed font once without changing browser zoom or
device scale. Optional help, accepted summaries and actual post-error/save focus
have separate screenshots. These screenshots were inspected.

Document/client widths agree at **1350/1350**, **375/375** and **305/305**, without
overflow suppression. Checkbox-label text measures **15.93:1** against its solid
surface. Error summaries retain visible blue focus; native successful saves focus
the existing recording section. Four checkbox choices remain native and enabled.

Matched German normal-form heights (CSS pixels):

| Viewport | Old Session, bid hidden / visible | New Session, bid visible | Old Match | New Match |
| --- | --- | --- | --- | --- |
| 1365×900 | 363.72 / 671.66 | 427.52 | 537.89 | 466.70 |
| 390×844 | 363.72 / 671.66 | 659.47 | 537.89 | 698.66 |
| 320×800 | 363.72 / 671.66 | 747.45 | 537.89 | 786.64 |
| 320×800, 200% text | 632.50 / 1268.41 | 2244.88 | 1039.44 | 2291.27 |

Desktop interaction is shorter than the previously exposed bid-entry form.
Narrow/enlarged forms use more vertical space where the new explanatory text wraps;
no claim of universally reduced height is made. Text is not shrunk or clipped to
hide that tradeoff. The 390-pixel normal Session form exposes all ordinary controls
and Save together; narrower/enlarged operation uses normal vertical scrolling.

Native Space/Enter actually saved Session Grand with all flags false, blank
Matadors and bid **17** (JavaScript unsent-language test) or **19** (no-script).
After reopen, explicit historical correction saved bid **29**. Native Match entry
saved Grand/bid **19** with all flags false; its editor then rejected retained Null
count/announcement conflicts until explicit clearing. Accepted Null has Ouvert
true, the other flags false, blank bid/count, followed by one actual `CA` Play and
reopen. Draft changes sent **zero** Product requests; every native save/correction
or invalid attempt sent **one** existing-route POST. Unsent-language changes sent
one language POST and retained empty numbers/unchecked flags without a Product
write. HTTP tests independently count actual Saves and preserve real Results.

Synthetic local evidence, outside runtime/UAT data:

```text
<temporary-directory>/opencode/declaration-228-before-complete/
<temporary-directory>/opencode/declaration-228-verified/
  evidence.json   # completed: true; fields, actions, focus, geometry, hashes
  summary.json    # matched normal/expanded baseline heights
  {js,native}-{state}-{de,en}-{width}-{text-scale}[-help].png
  {js,native}-{session,match}-{accepted,error-focus,saved-focus}.png
```

Representative current hashes:

```text
app.css      90186f8d78cfda3b368c1044438b99363a966584763e917a5a7de6aaa13f558c
workflow.js  f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298
form helper  78c4c5185621998220ff8b3fdee1772beb3295f7c4986ffdd060b0c4d6e3930e
HTTP helper  c1d107c3712de36a38f833e3329b0b38962579ee8f83c5598c269ff7cc7dcd51
rendering    d994bfc5d5592fcf0f7af68597c0086f98ad158d3e8dfdcc0fd473938360cbb5
```

Invoke the script using a separately installed Wheel environment's Python with
`--browser PATH --output FRESH_SCRATCH_DIRECTORY --phase before|after`; optional
`--baseline PATH_TO_BEFORE_EVIDENCE_JSON` records exact comparisons. Baseline mode
also exposes the old Session Advanced fields to measure actual bid access. The
script never changes branches or rewrites the application to simulate a baseline.

## Compatibility and remaining gates

Package **0.17.0**, Python **>=3.13**, license, dependencies, public APIs, Commands,
Schemas, seven Root workflows, persistence and generated outputs remain unchanged.
The catalogs contain **1,375** matching ordered keys. Authentication, Host/Origin,
CSP, bounded requests, private resources/downloads and no CORS remain unchanged.
Standalone CLI/browser/JSON remain English with their existing behavior.

Other browser engines, physical devices and assistive technology were not tested.
No installed-browser acceptance item is omitted; these are bounded technical
checks, not maintainer UAT. Exact merged-commit `check` and
`v1-supported-platform-matrix` remain required before closure. #221–#227 remain
completed bounded implementation slices. #208 and unresolved findings remain open;
UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed. Metadata, knowledge,
timezone, Home/Learning and remaining unrelated UAT work are not completed here.
