# Unified Match and Learning visual contract

Issue #243 adds the bounded unified action-state, Session Result-focus and Match
peer-disclosure repair documented under [R08 evidence](#r08-action-focus-and-disclosure-repair).
The earlier issue measurements below remain historical evidence.

Issue #244's [R03 composition evidence](#r03-recording-task-composition) supersedes
the three-panel normal recording hierarchy while retaining the #243 stylesheet.

Issue #224 repairs one private presentation boundary: unified light presentation,
readable Match/Learning content, responsive controls and all 36 Match entries.
Recording, recovery, analysis, transfer, selection, preparation and persistence
retain their existing operations. This is scoped implementation evidence, not
whole-frontend accessibility certification or maintainer UAT acceptance.

Issue #225 extends the app-owned light/shrinkable boundary to Settings and the
seat-setup/managed landing forms. Native saved/new mode choices suppress unused
entry controls without JavaScript, and only the selected Player editor expands.
Its separate installed-browser evidence covers desktop/narrow de/en, 320-pixel
reflow, 200% text, real creation, collision feedback and removal. The original #224
evidence below remains historical. See [Settings and Player seat setup](settings_and_player_seat_setup.md).

## Asset and component ownership

Issue #238's [Match Game navigation](match_game_navigation.md) deliberately
supersedes the grid-before-task ordering and ordinary Position numbering. One
labelled recording section leads with the selected Game and wrapping named seats;
one labelled focusable overview follows. App-owned focus/scroll styles cover both
native targets. The separately installed before/after evidence includes real
zero-save navigation, 320-pixel/200%-text reflow and error/recovery focus priority.
Earlier #224 measurements below remain historical, not current page coordinates.

Issue #230 adds a compact app-owned local-time disclosure and shrinkable native
date/time/zone tracks to Settings and unified Match/Session metadata. CSS follows
Keep/Replace/Remove without disabling or clearing submitted values. Date-only Match
entry remains separate. Installed-Wheel Edge evidence covers 128 de/en/script/no-script
measurements, including 320 pixels and 200% text; document/client widths agree.
Baseline forms, native keyboard changes, actual saves, focus and source/resource
hashes are documented in [Local time entry](local_time_entry.md). This slice
intentionally adds a private preference and timezone-data dependency.

Issue #229 extends the app-owned boundary to the compact Home, recording chooser,
and focused Match review/Report view. Historical #224 concept disclosures are
superseded by short shared introductions; active correction/transfer controls
remain. A visible footer About link uses explicit light text and focus on the dark
surface. Shrinkable chooser/manual-entry tracks and wrapping Home actions address
observed narrow/enlarged-text overflow. Matched baseline/final headings, geometry,
272 installed-Wheel measurements and native Result paths are documented in
[Home and recorded-game review navigation](home_and_recorded_review_navigation.md).
Earlier evidence below remains historical, not a claim about current Home structure.

Issue #226 extends the same app-owned boundary to normal Session/Match compact
native Card sets and single-Play radios. Its focused installed-Wheel checks cover
de/en desktop/narrow/320-pixel selection, 200% text, native focus, explicit saves,
and continuation. A discovered enlarged-text Session grid overflow was corrected
with a shrinkable recording track. Original #224/#225 evidence remains historical;
current measurements and resource hashes are in [Compact Card entry](compact_card_entry.md).

Issue #227 adds shared read-only Session/Match summary/history components to the
same app-owned stylesheet. Desktop uses recording and summary side by side;
narrow/enlarged text reflows the summary after the controls. Labelled numeric
definition lists preserve units without compressed Player columns. All correction
targets remain expanded. Installed-Wheel Edge inspection covers 176 measurements,
both languages and script modes, ten Tricks, Null, errors and warnings. A measured
Session analysis-form intrinsic overflow at 320 pixels/200% text was fixed with
the existing shrinkable form-track pattern. See
[Recorded Trick progress](recorded_trick_progress.md) for actual totals, hashes,
screenshots and focus evidence. Historical #224–#226 evidence remains unchanged.

Issue #228 extends this app-owned boundary to shared Session/Match declaration
fields and accepted summaries. Visible bid input and a shrinkable native checkbox
group replace the earlier Session bid-under-Advanced layout. Optional Matador help
and CSS-only Game-family guidance never disable retained inputs. Installed-Wheel
Edge 153 checks include de/en, JavaScript on/off, native saves/correction/reopen,
320-pixel reflow and 200% text. Desktop forms are shorter than the old exposed
bid-entry form; wrapped guidance increases some narrow heights. Actual comparisons,
15.93:1 checkbox-label contrast and inspected screenshots are in
[Compact Game declaration](compact_game_declaration.md).

`app_web/assets/app.css` remains the single theme owner. All unified Match and Learning
HTML loads only `/assets/app.css`. The shell's `main[data-workflow]` attribute
scopes these workflow components, including creation, contextual errors, status
feedback and secondary content outside the task-first wrapper. The attribute is
presentation metadata, not an operation, preference or versioned contract.

The authenticated compatibility URLs `/matches/assets/capture.css` and
`/learning/assets/corpus.css` still serve their original Package resources. They
are no longer linked into unified pages. Standalone Capture and Corpus retain
their templates, English renderers, stylesheets, scripts and resource URLs.
The unified language enhancement remains `app_web/assets/workflow.js` at the
existing `/matches/assets/capture.js` URL.

The affected markup inventory is:

| Area | App-owned presentation |
| --- | --- |
| Shell-adjacent content | Existing heading, concept disclosure, creation/profile warning, submitted-form error summary and operation status |
| Match overview | Twelve `.round-slots` groups, 36 `.match-tile` links; explicit title, status, selected/next markers and participant summary |
| Selected Match | Recording, diagnostic, accepted Trick history, preview, confirmation and return anchors |
| Match secondary areas | Transfer, Card evidence, annotations, metadata, Player Statistics, analysis options, retained Report, technical data and downloads |
| Learning | Empty/blocked guidance, available/added Matches, selected/alternative versions, preparation, summaries, source warnings, files and ten downloads |
| Report table | A named, focusable `.workflow-table-scroll` region containing the captioned candidate comparison table |

Only the unified Match tile markup changes structure. Its canonical link order,
rotation, `data-status`, selected `aria-current="page"`, textual selected/next
markers and next-position calculation remain authoritative. Tiles use a vertical
internal layout; available container width determines the number of columns.
No meaningful text is removed, ellipsized, fixed-height clipped or reduced in size.

Nested forms use shrinkable containers and `minmax(0, 1fr)` tracks. Controls stay
inside their parent, actions wrap, and file-selection buttons wrap at enlarged
text sizes. Primary, secondary, destructive and disabled appearances have explicit
foreground/background pairs. Unavailable-work explanations remain ordinary,
readable text outside disabled buttons. Scoped hover styles retain readable text.
In the original #224 slice, native controls, names, values, options, destinations
and required semantics were unchanged, with no form/disclosure duplication or
reordering. #238 subsequently moves the existing overview below recording and
adds named native fragments; #223 identity and transport regeneration remain.

## Contrast and reflow targets

Issue #236's [direct Learning entry](learning_direct_match_entry.md) adds one native
Match selector and explicit Add, consolidates selected/alternative versions, exposes
blocking source controls and leads prepared input to View results. Only the Learning
form track and its anchored panel ownership extend the app CSS. Its separate
installed-Wheel evidence covers native source/conflict/build controls and retained
versions at 320 pixels and 200% text, retaining this document's contrast/reflow rules.

Issue #231 reuses these app-owned styles for
[direct Session Card startup](session_direct_card_start.md#installed-browser-evidence).
Its separate installed-Wheel evidence covers both languages/script modes, actual
first-hand saves, optional details, errors and narrow/enlarged controls.

The scoped reference is [WCAG 2.2](https://www.w3.org/TR/WCAG22/): normal text
at least 4.5:1; large text at least 3:1 using the standard size definition;
required authored enabled-control/state visuals at least 3:1 against adjacent
colors, with the applicable exceptions. Keyboard focus stays visible, and selection
is textual/programmatic as well as colored. Ordinary content must reflow at
320 CSS pixels and remain usable with 200% text enlargement.

The workflow main, panels, nested disclosures, controls, warnings and errors use
solid surfaces. The shell's existing decorative body background is outside the
opaque workflow main. No workflow root palette, color-scheme override, CSS build
pipeline, remote asset or broad `!important` patch is introduced.

Only the genuinely two-dimensional candidate comparison table may scroll
horizontally, inside its labelled `role="region"`, `tabindex="0"` wrapper. Its
32-em minimum preserves readable columns at enlarged text sizes. The wrapper is
keyboard-scrollable and has an unclipped focus outline. The 36-entry overview,
forms, buttons, paragraphs and technical text do not use horizontal-scroll regions.
Native single-line edit fields retain browser caret scrolling; native selects
retain their complete option lists and keyboard selection. This is distinct from
authored clipping or document overflow. No document overflow is hidden and zoom
is not disabled.

## Reproduced baseline and measured repair

Baseline commit: `0cb392c0577f66ef0e40562dc18ce12e5e67caa0`.
The source/editable baseline was captured before production edits. Final checks
used a separately installed Wheel built from the changed tree, with loaded
resource bytes verified against the checkout. Both runs used headless Microsoft
Edge **152.0.4191.66** on Windows with Python **3.13.7**, device scale 1 and browser
zoom 100%. The final evidence records the baseline HEAD plus resource hashes,
since agents do not create an implementation commit.

Measured German comparisons at **390x844**:

| Measurement | Before | After |
| --- | --- | --- |
| Learning panel body text | `#f0eee7` on `#fffdf8`, **1.14:1** | `#18231d` on `#fffdf8`, **15.93:1** |
| Learning secondary disclosure text | `#f0eee7` on `#fbf8f0`, **1.09:1** | App-owned light foreground/surface pairs; no failing measured text pair |
| Match document width, transfer/settings | **503 px** | **375 px** |
| Learning document width, all disclosures open | **1083 px** | **375 px** |
| Selected Match tile participant width | **11.11 px** | **279.81 px** |
| Same selected tile height | **1624.47 px** | **282.48 px** |

The 390-pixel browser has a 375-pixel document client area after its native vertical
scrollbar. Final document/client widths also agree at **1350/1350**, **305/305**
and **753/753** for 1365-, 320- and 768-pixel viewports respectively. This is reflow,
not hidden overflow. Representative authored input borders measure **4.01:1**
against the panel; the blue focus outline measures **5.89:1** against that surface.
Primary white-on-green text measures **7.95:1**; ordinary green links on the light
surface measure **11.72:1**. Active, hover, error and warning pairs are retained in
the evidence alongside the scoped threshold checks.

The actual baseline stylesheet list was `app.css` followed by Capture or Corpus
CSS. Corpus `:root` supplied `--ink: #f0eee7` and `color-scheme: dark`, while the
more specific unified panels retained `background: var(--surface)` (`#fffdf8`).
These computed solid pairs establish the original Learning contrast failure;
no gradient estimate or antialiased glyph-edge pixel was used for those ratios.
The legacy Corpus `.panel` gradient also appeared in other nested panels; the
reported solid-pair ratios are not claims about its full gradient range.

Capture `.position-card { grid-template-columns: auto 1fr }` and
`.position-card small { grid-column: 2 }` acted on unified anonymous title/status
text. The selected tile's actual tracks were **259.13 px / 11.11 px**. Its
standalone component expected a separate number element. The German transfer
disclosure/button occupied a **469.53-pixel** intrinsic grid track starting at
33 px, producing the measured 503-pixel document width. Removing the conflicting
sheet alone would not fix all intrinsic minima; app-owned shrinkable form tracks,
controls and explicit tile children address both boundaries.

## Repeatable optional browser verification

Use the existing development environment (including pytest fixtures) and an
already installed local Edge/Chromium executable. This reuses the dependency-free
DevTools transport from the #222/#223 verification. It is deliberately separate
from `scripts/check.ps1`; no browser, driver, Node or Python runtime dependency is
added to the Package or full check.

Choose an existing scratch parent outside managed Product data. From the checkout:

```powershell
py -3.13 scripts/verify_unified_workflow_visuals.py `
    --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
    --output "$env:TEMP\opencode\workflow-224-after" --phase after
```

`--phase before` captures the four original failing states without enforcing the
repaired thresholds; it must run against the intended pre-fix application.
`--baseline PATH_TO_BEFORE_EVIDENCE_JSON` adds same-state comparisons. The script
never switches branches or rewrites the application to emulate a baseline.

For installed-resource verification, build a local Wheel into the scratch parent,
create a Python 3.13 verification venv with `--system-site-packages` to reuse the
existing dev tooling, and install that Wheel using `pip install --no-deps --no-index`.
Invoke the script with that venv's Python and `--expect-installed`. This flag rejects
loading SkatMind from the checkout; loaded CSS/template hashes must still match
the checked tree. The browser uses real unified and standalone servers and their
returned resources throughout. Clean Wheel/sdist isolation and API/CLI/resource
checks remain the separate distribution gate.

The final run records **280 page measurements across 15 states**:

* German and English at **1365x900**, **390x844**, **320x800**, **768x1024**,
  with disclosures closed and fully open;
* selected same/different next entries, mixed completed/passed/empty entries,
  twelve rounds and long synthetic names including a 120-character name;
* declaration, Card entry, a real duplicate rejection, continued recording,
  linked diagnostic, replacement and rewind previews;
* expanded transfer, metadata, Statistics, evidence, analysis settings and a real
  retained executed Decision Report;
* empty Learning, selected and alternative versions, executed Teacher source,
  prepared Results and all ten downloads, real preparation error, and a
  non-current-source blocker after a genuine new Snapshot import;
* **200% text** at 320 and 768 pixels for ten worst-case states. The harness
  doubles each measured font size once, preserving layout dimensions and browser
  zoom, rather than shrinking a screenshot or pretending device scale is text zoom.

Native Enter with page JavaScript disabled selects/previews/applies a replacement,
records another Card, rejects a duplicate, applies a confirmed rewind, transfers
Workspace and Report evidence, explicitly prepares Learning, and downloads a file
whose bytes equal the retained HTTP artifact. All ten authenticated downloads are
checked. One complete synthetic Game is recorded and reused across viewports;
success, validation and Save are not mocked.

JavaScript-enabled native language changes preserve safe unsent values and open
disclosures for Match recording, retained Report, Learning, Learning error and a
#221 source-labelled Session Result. Each activation sends exactly one language
POST. Match bytes, prepared artifacts and exact Session/Report downloads remain
unchanged where their source remains current. Keyboard focus, hover, native select
keys and the narrow table's ArrowRight scrolling are separately inspected.

Home and a real Session Result receive shared-shell spot checks. Real standalone
Capture and Corpus are inspected at desktop/narrow sizes with their original asset
sets. Their pre-existing long-ID/long-name overflow is not a repaired unified-page
result; no standalone styling is changed. Additional browser engines, physical
devices, assistive technology and every possible Product state were not tested.

## Evidence and remaining gates

Sanitized local evidence is outside runtime data:

```text
<temporary-directory>/opencode/workflow-224-before/
<temporary-directory>/opencode/workflow-224-installed-after/
```

The baseline has `evidence.json` and German desktop/narrow whole-page/area PNGs.
The final directory has `evidence.json`, `summary.json`, the same original-state
PNG names, additional Match/Learning state PNGs, enlarged-text captures, control
focus/hover captures and shared/standalone spot checks. `summary.json` must have
`completed: true`. Evidence contains computed RGBA pairs with transparent ancestor
composition, ratios, offending-element dimensions, tile tracks, resource URLs and
hashes, viewport/locale/script/text-scale metadata, native POST paths and download
byte hashes. It contains no cookie, bootstrap token or personal filesystem path.
Screenshots are synthetic local evidence, not generated-output fixtures or assets.

Source/HTTP regressions live in `tests/test_unified_workflow_visual_contract.py`.
They verify resource delivery, creation/error/active/Report composition, all 36
semantic tile links and rotation, deterministic language manifests, required
confirmation and existing diagnostic anchors, and exact retained Report downloads.
Distribution validation checks active installed Match/Learning HTML asset ownership
as well as Package Resource byte parity. #221/#222/#223, locale, security and
standalone suites remain intact.

Package **0.17.0**, Python **>=3.13**, dependencies, license, public APIs, Schemas,
seven Root workflows, persistence, examples and generated outputs are unchanged.
Issue #223's contrast/overflow observations remain historical evidence; #224
technically remediates those scoped failures. Issues #221/#222/#223 remain completed
implementation slices. Exact merged-commit `check` and `v1-supported-platform-matrix`
must be green before #224 closure. Issue #208 and unresolved findings remain open;
UAT-01 remains failed, UAT-02 through UAT-12 remain paused, B-09/B-07 remain open,
B-06 remains closed, and v1.0.0 preparation remains unready. No new complete
maintainer walkthrough or acceptance claim is made.

## R08 action, focus and disclosure repair

Issue #243 starts on clean `bug/243-hover-focus-disclosures` at
`2af0e7af73980862140b1bc46cab9b099feedaf4`, after completed #242. The actual #243
issue and R08 in #208's consolidated report were read. The earlier archive
`aecd151aafff1601b0366bb024e65a98006f4240` and maintainer UAT installation
`483e51269d0206d29d9f73001dfadf8f0e7b2f32` are distinct baselines.

### Styling ownership

Only `app_web/assets/app.css` changes Product code. Button variants now own complete
normal and enabled hover/active foreground/background pairs via local CSS properties.
Secondary actions, including native-details callers, stay light; primary actions stay
filled green; existing destructive operations and Settings resets stay red. Explicit
`.primary` semantics take priority over incidental placement inside details. Disabled
buttons retain their native attribute, muted palette and disabled hover appearance.
Selected-language borders, underline and `aria-pressed` remain authoritative. Ordinary
links retain their colors; header/skip-link focus uses the existing gold dark-surface
indicator, matching the footer rather than low-contrast blue on dark green.

`#session-result:focus` uses a **2 CSS-pixel solid** `--focus` outline with **3px offset**,
including redirected focus without `:focus-visible`. Constant 0.25rem block padding
and direct-paragraph inline inset separate its source caption from the ring. The
Result sections retain their original width, including the comparison table. Focus
changes no box dimensions. The existing ID, `tabindex=-1`, labels, next Tab order,
native fragments, error autofocus, recovery destinations and language-return logic
are unchanged. There is no outline reset, timer, focus-script change or forced-color
opt-out; an outline, rather than a shadow alone, survives forced colors.

The existing direct-child peer rule also includes
`#task-first-match > #match-metadata > details`. This preserves the wrapper anchor,
native markers, summary typography, open spacing, DOM order, forms and nested levels
while giving the wrapped peer the same 0.8rem padding. Long translated captions wrap.
The repeated Technical details hierarchy remains a separate concern.

### Installed before/after measurements

Both baseline and final Wheels were independently installed outside the checkout;
Python **3.13.7**, Package **0.17.0**, headless Microsoft Edge **153.0.4234.32** on
Windows, device scale 1. Real emitted pages reuse a legal 12-Play Session with its
collected Trick-4/Card-3 decision, a normal six-Play Match, and an empty Learning
collection for disabled controls. Setup follows returned HTTP forms. Review Results,
analysis, saves and recovery are genuine, not injected success markup or mocked work.
Counters wrap and call the real functions.

| Computed measurement | Installed baseline | Installed repair |
| --- | --- | --- |
| Saved review and nested Session secondary, rest / keyboard focus | `#0b3f2d` on `#fffdf8`, 11.716458:1 | Same |
| Same secondary, hover / hover-focus / pressed | `#0b3f2d` on `#0b3f2d`, **1:1** | `#0b3f2d` on `#dcebe3`, **9.662205:1** |
| Primary and button link, rest / hover | White on green, 7.949569 / 11.910673:1 | Same pairs; active explicitly paired |
| Destructive Match and Settings, rest / hover | White on `#7e2119`, 9.911720:1 | 9.911720 / 12.985151:1; hover stays dark red |
| Native disabled, rest / hover | `#58655e` on `#eee9dd`, 5.042136:1 | Same, still disabled |
| Selected / unselected language | Opposite white / `#173b2c` pairs, 12.364670:1 | Same, with non-color selection cues |
| Result outline after genuine review return | UA `auto`, computed 1px `#101010`, 0px offset | Solid 2px `#005fcc`, 3px offset, **5.887344:1** adjacent contrast |
| Source-caption left text inset | 0px | 4px, plus the external ring separation |
| Header link focus adjacent contrast | 1.990109:1 | Gold `#ffd477`, **8.471197:1** |
| Direct / wrapped Match disclosure padding, 1365px | 12.8 / 20px | 12.8 / 12.8px |
| Direct / wrapped padding, 390/320px | 12.8 / 10.4px | 12.8 / 12.8px |

Both summaries were already **16px / 700 / 24.8px line-height**, with native inside
disclosure markers; at 200% text they are **32px / 700 / 49.6px**. The proven mismatch
was spacing, not font size. Open-summary bottom spacing remains 16px. Match/Learning
secondary hover was already readable; consolidation retains contrast while making
the secondary state visually distinct from primary. Ordinary link text measures
11.716458:1; dark header/footer text measures 10.852019:1. Measured opacity is 1 for
each tested control and its ancestors; ratios use computed colors and composed solid
backgrounds, not selector presence. Thresholds use unrounded values.

There are **32 responsive page measurements and 67 representative control-state
measurements**, covering de/en, script on/off, 1365/390/320px and representative 200%
text at 320px. The harness doubles captured font sizes once on a fresh document;
device scale is not presented as text zoom. Native input dispatch covers mouse hover
and press, actual Tab/Shift+Tab traversal, Enter/Space disclosure toggles, and four
review returns: German pointer and English keyboard, each with script on/off. Each
review sends one POST and executes once. All four focus `session-result`; next Tab
reaches the existing `#recorded-decision-12` source-return link. Bringing the headless
tab to the foreground is recorded separately from element focus; no `element.focus()`
is used to manufacture these results. Early inactive-tab samples were superseded.

A real whitespace-title rejection opens Match metadata, autofocuses its error summary,
retains that priority after language switching, and its field link focuses
`validation-field-1-title` inside the open disclosure. Native preview focuses
`match-recovery`; Cancel returns to `match-recording`, with no Apply/rewind/delete.
Same-source language switching preserves safe unsent metadata and disclosure state.
The retained Session scores, equal-best content and pre-Card context remain #239–#241's
output, with unchanged Request/Result download hashes before/after and across passive
views. Existing #242 seat/conflict selectors and #238 transport are intact.

After setup, the run observes **4 review POSTs / 4 executions**, **15 explicit language
POSTs / 15 profile saves**, one rejected metadata POST and one each recovery Select,
Preview and Cancel. Session/Match saves after setup are **zero**. Hover, focus,
disclosure toggles and a passive interval cause zero requests, Product saves or
executions. Setup separately records 17 Session saves, 9 Match saves, 3 profile saves
and one real empty-Corpus creation. The registry remains **63 POST routes / 107 forms**.

Document/client widths agree at **1350/1350**, **375/375**, **305/305**. Reviewed
screenshots show wrapping controls, source captions and unclipped focus rings, including
320px/200% text. The **#240 comparison-table limitation remains open**, visibly including
very narrow wrapped columns and a clipped/scrolling table presentation. Its measured
section/wrapper/table geometry is exactly equal before/after at every matched viewport;
for German 320px/200%, the wrapper is 202px and table 228.328125px. This is neither a
table repair nor a table-usability pass.

Forced-colors **emulation** retains a solid 2px/3px cyan indicator at **14.371255:1**
against black, with readable source text and unchanged focus. It is not real-system
high-contrast, physical-device, screen-reader or whole-application accessibility UAT.
The historical user's exact Edge outline was not measured by this work.

### Reproduction and retained evidence

Use an independently installed Wheel interpreter with the existing dev fixture
environment and the caller's already installed browser. From the checkout:

```powershell
& "PATH_TO_DISPOSABLE_WHEEL_ENV\Scripts\python.exe" scripts/verify_action_visuals.py `
    --browser "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" `
    --output "$env:TEMP\opencode\unique-action-evidence" --phase after
```

The output must be a new directory under an existing disposable parent. The script
rejects loading Product modules from the checkout and verifies installed module/CSS
hashes and served CSS bytes. `--phase before` uses a separately retained baseline
Wheel, permits its different CSS hash and records failing visual states without
pretending they pass. It never rewrites Product assets to simulate a baseline.
This tooling reuses `_workflow_visual_browser.py` and is not a full-check dependency.

Evidence is retained under `<temporary-directory>/opencode/`:

* `243-before-final-tree/evidence.json` and matched PNGs;
* `243-after-spaced/evidence.json` and matched PNGs, both `completed: true`;
* baseline installed CSS SHA-256
  `63f7645e346e46e7a1d8522494234149ef5b2db3d7b1a07630f6d80332bc80e5`;
* final installed CSS SHA-256
  `e94bee2b4967c25607109bafb58b9fbe5d75927cf8c93a0d0b978ab32060bd12`.

Evidence includes actual request paths/counts, outlines, geometry, focus targets,
computed colors/opacity, retained download and unchanged module hashes. Matched hover,
Result, metadata, narrow/enlarged, contextual-error, recovery and forced-color PNGs
were inspected. Earlier incomplete verifier attempts remain retained, superseded by
these completed runs. All data is disposable synthetic data; the maintainer's UAT
installation and files were untouched.

The focused HTTP tests protect anchors/tabindex, review button variants and payloads,
native disabled state, disclosure order, same-source returns and refreshed profile
bindings. Existing language/validation/recovery/#238–#242 suites remain the behavioral
guards. Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependencies including
`tzdata>=2026.4`, public/profile/persistence formats and 98 scenarios remain unchanged.
Both `check` and `v1-supported-platform-matrix` must pass on the exact merged commit
before manual #243 closure. #242 remains completed; #208/other findings remain open,
UAT-01 unaccepted, UAT-02–12 paused, B-09/B-07 open and B-06 closed.

## R03 recording task composition

Issue #244 starts clean on `bug/244-recording-task-focus` at
`8f0211f76e59fbbb1026c147b4b0e99825c28943`, after completed #243. The actual issue
and R03 of #208's consolidated report were read. Four current returned-page
regressions first failed on the redundant Session instruction headings and
zero-Play Match invitation. The planning archive and maintainer installation remain
historical evidence, not this source/browser baseline.

Normal recording now pairs one accepted primary task heading with its form.
Session identity/status is compact; Match keeps Game identity, seats, rotation,
overview and explicit Pass. Zero-observation review destinations are quiet but
addressable. Observations with insufficient evidence retain inspection and reasons;
prepared decisions retain explicit analysis. Specialist Session controls and
capability blockers are inside a named native disclosure; retained Results stay
outside at `session-result`. Match transfer is secondary and opens for relevant
feedback. Existing native forms, #243 focus styling, field-error priority, safe
language restoration and independent source lifetimes remain authoritative.

### Installed evidence

`scripts/verify_recording_task_focus.py` reuses `_workflow_visual_browser.py` and
the existing legal HTTP fixtures. Run with an independently installed Wheel:

```powershell
& PATH_TO_INSTALLED_PYTHON scripts/verify_recording_task_focus.py `
    --browser PATH_TO_EDGE --output FRESH_SCRATCH_DIRECTORY `
    --wheel PATH_TO_WHEEL --phase after
```

`--phase before` verifies the actual starting-HEAD installed files against Git;
`after` verifies the changed installed modules/catalogs/assets against the tree.
No branch switch or source rewrite simulates a baseline. Both completed runs used
Windows CPython **3.13.7**, Package **0.17.0**, headless Edge **153.0.4234.32**,
de/en, JavaScript on/off, **1365×900**, **390×844**, **320×800**, and doubled text at
320 pixels. Each has **224 page measurements**. Document/client widths agree at
1350/1350, 375/375 and 305/305. Representative screenshots were inspected for
current task/control, zero review, declaration, eligible decisions, retained Result,
secondary transfer, enlarged text, error-field focus and correction preview/Cancel.

Matched German/no-script document coordinates, CSS pixels:

| State / width | Recording anchor before → after | Current control before → after |
| --- | --- | --- |
| Session initial hand / 1365 | 925.5 → 492.3 | 2034.0 → 1600.8 |
| Session choose declarer / 390 | 1028.9 → 594.5 | 1138.9 → 704.5 |
| Session choose declarer / 320 | 1108.8 → 594.5 | 1218.8 → 732.1 |
| Match empty / 390 | 538.2 → 538.2 | 914.6 → 872.0 |
| Match declaration / 390 | 538.2 → 538.2 | 1076.7 → 986.3 |
| Match three Plays, missing evidence / 320 | 602.9 → 602.9 | 2390.6 → 2270.6 |

The Session's three generic normal instruction headings become one task-specific
heading; its initial visible page heading count falls from eight to four, including
the omitted empty review/analysis panels. Match retains its Game/overview headings.
No one-screen or all-headings-removal target is claimed. Enlarged labels require
vertical scrolling. Result composition uses the ordinary outer content width;
the candidate table itself is unchanged and still has the known narrow/enlarged
wrapping/clipping limitation. No new recording-control or feedback clipping was
observed. This is headless synthetic evidence, not physical-device, screen-reader,
whole-frontend accessibility or maintainer UAT acceptance.

Each matched run has **24 native POSTs**, **41 Session saves**, **8 Match saves**,
**2 Session review executions**, **1 Match decision execution**, and **63 explicit
profile-language saves**, including fixture setup and measurement-language changes.
The accepted counts and revisions match before/after. The extra after-only action
opens the transfer disclosure and sends no request. Native input exercises partial
and full hand saves, declarer/declaration, three Match Cards, explicit hand evidence,
review, End, Pass, language, source-return, field focus and preview/Cancel. One real
30-Play Session is shared across all Result locales/viewports. It ends at revision
44 with ten Checkpoints and both current/Historical exports unavailable. Strict
reopen requires the second explicit review; no process-local Result survives it.

The real SJ Request and Result hashes are identical across installed before/after:

```text
Request  05dc65aa713fb37c7b40cd9a4027ce6926881e6bb0c98adaf4256b8a7f14ec94
Result   76eb05221cab155ff59f734ec568bbead767c2f309d6823546d598412ac545c1
Before Wheel  3d47962f375548730b55becd5dc841aade22534c87ace7a34ff22b47820d84f1
After Wheel   c3176f80be4da75321fc7cc1d16354249197958fe464d7029b523a39ba806f7f
```

Completed evidence is under `<temporary-directory>/opencode/244-before-03/` and
`244-after-01/`, with loaded/served hashes, headings, geometry, requests, operation
counts and PNGs. Two earlier baseline harness attempts stopped on fixture-opener
selection and multiline-link pointer targeting; they are not successful runs.
`244-result-detail/` strictly reopens the prepared synthetic ended source and
records eight additional de/en normal-score/context/tie/table measurements and
screenshots, with one explicit review and zero Product saves. Visible 14/29 appears
once, the pre-Card hand has seven Cards, and CJ/SJ remain equal-best at 6.00.
Exact per-source saved bytes and retained downloads remain unchanged on passive
viewing/language/navigation. A Report is still reachable after selecting another
empty Game; adding hand evidence changes real Match availability from 0/3 to 1/3.
The optional import copies the actual partial Workspace with Game 2 passed into a
real disposable collection, without analysis or preparation.

Only R03 task/readiness composition is implemented. Generic notice lifecycle,
other R03 work and remaining UAT findings stay open. Package, dependencies,
public/profile/persistence formats, 63 POST routes / 107 forms and 98 scenarios
are unchanged. #243 stays completed; exact merged-commit `check` and
`v1-supported-platform-matrix` gate manual #244 closure. #208 stays open, UAT-01
unaccepted, UAT-02–12 paused, B-09/B-07 open and B-06 closed.
