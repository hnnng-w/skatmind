# Manual Review deal validation (Issue #306)

## Scope and authoritative boundary

Expected and actual initial branch: `bug/306-manual-deal-validation`.
Expected and actual starting HEAD: `e0067fe1f2964f05686a1dbf7b55491580d9c98a`.
The initial worktree was clean. Implementation is unstaged working-tree work on
that unchanged branch and HEAD.

The reported ordered distribution contains 10/10/9/2 Cards; Rearhand omits `H7`.
Before Product edits, two new delivered-HTTP regressions submitted the emitted
step-2 form, including its revision and form-instance authority. Both received
HTTP 400 but a generic required-value message and a form-level summary link.
Neither received the missing Rearhand/count explanation. This is a genuine HTTP
reproduction, not a conclusion inferred from the supplied screenshots.

The former `_card_tuple` count error reached the Historical parser as English
prose, was wrapped with field `_form`, and matched the global required-message
heuristic. Step-2 palettes lacked group-feedback markers and scoped registry
labels. Their server-rendered selected-count captions could remain at zero while
native controls were checked; the existing JavaScript summary updater expects
compact-selection markup that guided palettes deliberately do not emit.

The correction keeps `update_historical_deal_v1` as the sole acceptance boundary:

* Validate shape, canonical Card membership and within-field duplicates, then
  cross-group duplicates, before producing ordinary count diagnostics. No invalid
  Card or duplicate is misrepresented as a simple selection-count problem.
* Collect private immutable `HistoricalDealCountV1` facts for every unequal group
  count, in Forehand/Middlehand/Rearhand/Skat order. The parser retains these facts
  in `FormFieldErrorV1`; only `review.deal` maps them to localized count feedback.
  The global required-message heuristic and Discards' validation remain unchanged.
* Retain exact 10/10/10/2, full 32-Card membership and uniqueness requirements.
  There is no alternative acceptance path, automatic assignment or repair.
* Give each palette a scoped validation label, existing unique `field-...` target,
  `data-validation-group` marker and outside-tile inline-message boundary. The
  unchanged feedback renderer supplies initial summary autofocus, native group
  focus, invalid state and ARIA error associations.
* Render only static localized step-2 requirements (ten/two cards required), with
  no selected-count restoration marker. The actual rejected count is in the error
  explanation. No live counter, compact code list or JavaScript dependency is added.

Safe rejected values remain presentation state, independent of the accepted draft
and revision. Native language return preserves submitted checks and translates the
diagnostic. Enhanced return can additionally preserve pending changes; it does not
revalidate or replace the earlier rejection facts. Language return retains its
existing focus-continuity rules rather than repeating initial error autofocus.
Adding `H7` to the returned form and explicitly submitting advances once to step 3
with the original canonical ordered distribution.

Analyze, other manual steps, Match/Session palettes, #305 Play radios and Back,
rules, persistence and public contracts retain their existing boundaries. Route
and form inventories remain **9 static routes / 73 POST routes / 125 forms**.
Six paired catalog additions bring the strict locale inventory to **2,124 keys**.

## Verification commands and scope

Every validation tool call uses an explicit **7,200,000 ms tool timeout**, never a
pytest or PowerShell argument. Actual runtime: **CPython 3.13.7, 64-bit Windows**,
`C:/Users/Henning-DT/AppData/Local/Programs/Python/Python313/python.exe`, pytest
**9.0.3**, pytest-xdist **3.8.0**, Windows PowerShell **5.1**. Data, profiles, logs
and captures use disposable fixtures with source-tree imports; no installed UAT
environment or real managed data is accessed.

```powershell
$E = 'C:/Users/HENNIN~1/AppData/Local/Temp/opencode'
$B = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'

py -3.13 -m pytest tests/test_manual_review_deal_validation.py -q --tb=short `
  -o cache_dir="$E/306-red-cache" --basetemp="$E/306-red-tmp" --junitxml="$E/306-red.xml"

# Executed with suffixes green, green2, green3, green4, in that order.
$suffix = 'green4'
py -3.13 -m pytest tests/test_manual_review_deal_validation.py `
  tests/test_guided_historical_review_form.py tests/test_guided_card_palettes.py `
  -q --tb=short -o cache_dir="$E/306-$suffix-cache" --basetemp="$E/306-$suffix-tmp" `
  --junitxml="$E/306-$suffix.xml"

py -3.13 scripts/verify_manual_review_deal_validation.py --browser $B --output "$E/306-browser-a"
py -3.13 scripts/verify_manual_review_deal_validation.py --browser $B --output "$E/306-browser-final"

$modules = @(
  'tests/test_manual_review_deal_validation.py',
  'tests/test_guided_historical_review_form.py',
  'tests/test_guided_card_palettes.py',
  'tests/test_frontend_validation_preservation.py',
  'tests/test_guided_frontend_web.py',
  'tests/test_guided_frontend_contracts.py',
  'tests/test_guided_position_form.py',
  'tests/test_completed_trick_input_grouping.py',
  'tests/test_manual_review_play_navigation.py',
  'tests/test_manual_review_saved_names.py',
  'tests/test_frontend_language_switching.py',
  'tests/test_language_switch_context.py',
  'tests/test_task_first_language_preservation.py',
  'tests/test_language_view_continuity.py',
  'tests/test_language_view_script.py',
  'tests/test_frontend_localization_foundation.py',
  'tests/test_complete_frontend_localization.py',
  'tests/test_packaging_and_distribution.py',
  'tests/test_guided_frontend_packaging.py',
  'tests/test_skatmind_rename.py',
  'tests/test_guided_frontend_execution.py',
  'tests/test_guided_frontend_json_transfer.py',
  'tests/test_guided_frontend_result_presentation.py',
  'tests/test_analysis_download_details.py',
  'tests/test_analysis_review_entry_paths.py',
  'tests/test_unified_local_app_web.py',
  'tests/test_unified_local_app_contracts.py',
  'tests/test_consistent_card_presentation.py'
)
py -3.13 -m pytest @modules -q --tb=short --durations=15 `
  -n 2 --dist=loadfile --max-worker-restart=0 `
  -o cache_dir="$E/306-affected-cache" --basetemp="$E/306-affected-tmp" `
  --junitxml="$E/306-affected.xml"

py -3.13 -m ruff check src/skatmind/app_web/historical_deal_feedback.py `
  src/skatmind/app_web/historical_form.py src/skatmind/app_web/historical_form_parsing.py `
  src/skatmind/app_web/form_parsing.py src/skatmind/app_web/form_registry.py `
  src/skatmind/app_web/validation_mapping.py src/skatmind/app_web/guided_rendering.py `
  tests/test_manual_review_deal_validation.py tests/test_guided_historical_review_form.py `
  tests/test_guided_card_palettes.py tests/test_frontend_localization_foundation.py `
  tests/test_guided_frontend_packaging.py scripts/verify_manual_review_deal_validation.py

git diff --check
function python { & py -3.13 @args }
.\scripts\check.ps1 -Mode Quick
git diff --cached --stat
git status --short --branch
git rev-parse HEAD
```

The complete-module inventory follows the edited Historical validation/parser,
shared field-error payload and scoped mapper/registry changes, guided rendering,
native and enhanced language delivery, accepted execution/JSON/download callers,
paired localization, guided package discovery, packaging and strict rename checks.
Shared CSS, JavaScript, compact-card rendering and rejection transport are not
edited. No exclusive module is selected: the four established exclusive modules
cover unchanged transport/worker rejection, standalone Corpus or Match analysis
placement. No local Full is run or authorized for this correction.

The new HTTP module includes 48 cases: the reported correction/return flow, all
four groups with empty/short/excess selection in both languages, enhanced return,
within/across-group duplicates, malformed/unsupported input, stale/repeated
revision and stale step/language authority. Empty-group cases first accept a deal
and return via Back, proving rejected emptiness clears prior accepted checks only
in presentation. Excess cases transfer a real Card, distinguishing count mistakes
from duplicate ownership. Four additional parser cases cover malformed mapping
shapes; a retained-count test proves mapping is independent of exception prose.

Intermediate results are retained honestly:

| Run | Result | Explanation |
| --- | --- | --- |
| `306-red` | 2 failed | Intended pre-Product HTTP reproduction |
| `306-green` | 33 passed, 18 failed | New catalog keys initially inserted out of strict lexical order; fixed |
| `306-green2` | 97 passed, 4 failed | Test incorrectly required initial autofocus after language return; corrected to existing continuity behavior |
| `306-green3` | 99 passed, 2 failed | Test incorrectly treated explicit locale-profile writes as passive; corrected to require only the profile change |
| `306-green4` | 101 passed in 49.73s | Complete focused modules; no skips |

Focused Ruff passed. The **28 complete affected modules passed all 860 distinct
tests in 146.45s**, with no skips or failures (`$E/306-affected.xml`). The earlier
passing cases overlap those 860; they are not additional distinct coverage.
The final explicit Quick result and external log path are recorded in the
completion handoff. A final complete strict-rename rerun follows documentation
review before Quick:

```powershell
py -3.13 -m pytest tests/test_skatmind_rename.py -q --tb=short `
  -o cache_dir="$E/306-final-rename-cache" --basetemp="$E/306-final-rename-tmp" `
  --junitxml="$E/306-final-rename.xml"
```

## Real-browser evidence and write accounting

Final evidence: **`$E/306-browser-final/report.json`** and four directories
`de-False`, `de-True`, `en-False`, `en-True`. The earlier `306-browser-a` also passed
all four cells; final evidence additionally captures narrow inline explanations
and explicitly asserts no passive POSTs. Both use actual headless Microsoft Edge
**156.0.4314.50** (JavaScript runtime **15.6.12.7**)
through the existing dependency-free DevTools transport. Exact browser version,
source paths and resource hashes are retained in each report; served stylesheet
and script bytes match the source assets.

Each cell selects all 31 reported Cards with real checkbox input and submits by
native keyboard interaction through the emitted form. `rejection-initial.png`
is captured before verifier scrolling/focusing, and `rejection.html` is the actual
HTTP response body. The summary initially owns focus. Tab/Enter activates its
Rearhand link; `error-link-keyboard.png` shows focus on the real labelled group,
with the outside-tile error and retained selections. Both the expected actual
count and ten-card requirement are present.

Native language return is exercised in every cell (temporarily disabling script
for that action in script-enabled cells). Script-enabled cells then exercise the
existing enhanced return, with its actual POST envelope verified. Both directions
preserve the rejection, safe checks and static requirements in delivered HTML.
The final real `H7` check and explicit submission reach step 3 with all ordered
hands and Skat intact, at accepted revision 3 from step-2 revision 2.

There are **24 layout measurements** per completed run: initial rejection and
opposite-language return at **1365×900, 520×900 and 320×900**, in all four cells.
Full suit rows remain **8**, **4+4**, and **2+2+2+2**, respectively. Document,
summary, inline explanation and tiles have no horizontal overflow. Faces remain
16px, checkboxes 20px and targets at least 44px. Browser zoom, DPR and visual scale
are all **1**. These are viewport reflow measurements at 100% browser zoom, not
evidence of enlarged browser zoom; historical #304 zoom acceptance is preserved.

For each completed four-cell run:

| Activity | Observed operations |
| --- | --- |
| Synthetic fixture | Four manual Starts and four Players submissions; process-local drafts only |
| Initial locale and two explicit returns | 12 profile saves and 12 corresponding managed atomic replacements |
| Reported rejection | Four HTTP 400 deal responses; no draft/revision advance, workflow execution or persistent writes |
| Passive selection, inspection and error navigation | No POST, workflow execution or persistent replacement; accepted state/file snapshots retained |
| Corrected explicit submission | Four HTTP 303 deal responses; one process-local revision advance each, no recording write |
| Analysis, Review execution and Learning preparation | Zero |

Across the two completed repeats there are 24 profile saves/replacements, all
attributable to explicit locale actions, not passive activity. Browser logs and
screenshots are verifier output, outside managed Product persistence.

## Remaining gates

**Locally validated; exact-commit hosted CI and installed targeted acceptance
pending.** Explicit Quick is partial validation, not generated-output, built
distribution, installation-matrix or full-regression certification. The maintainer
still needs exact-commit `check` and `v1-supported-platform-matrix`, plus installed
affected-path acceptance for this manual-deal boundary. No hosted CI or installed
maintainer UAT is claimed.

Keep **#306 and #208 open**. Preserve accepted #292–#305 scopes and their historical
evidence. UAT-01 is not globally accepted; UAT-02–12 remain paused. Release
preparation is not authorized. The agent does not stage, commit, publish, modify
GitHub or trigger Actions.
