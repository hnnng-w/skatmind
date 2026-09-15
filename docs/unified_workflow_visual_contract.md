# Unified Match and Learning visual contract

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
Native controls, names, values, options, destinations and required semantics are
unchanged. No form or disclosure is duplicated or reordered; #223 identity and
transport regeneration remain unchanged.

## Contrast and reflow targets

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
