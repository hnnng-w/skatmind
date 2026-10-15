# Collection overview navigation correction (#289)

This private navigation/presentation correction starts from
`28b8e5a1f69ec2d38dc22bb597b1eb0d897dc02a` on
`feature/289-learning-debrief`. The maintainer's installed observations at that
baseline already confirmed incorporation of Alex/C7 and Alex/S8, two distinct
analyzed Decisions/two Reports, the retained C7 alternative comparison, the S8
forced move, and comparison-to-collection return retaining both entries.
Those remain successful observations for that build. They do not establish
overall Learning usefulness or acceptance of this correction.

## Current journey

```text
detailed individual Match Report
  -> resolved named collection / explicit real collection choice
  -> Add to {collection}
  -> accepted captured collection overview + compact receipt
  -> View comparison for the exact retained variant
  -> Open analysis overview for that exact scope and Player filter
```

The individual Match result remains the existing full rollout comparison.
Its optional **Summary of this Report only** disclosure preserves the direct,
collection-free captured-summary route. Collection-related actions no longer
require visiting that summary.

The normal incorporation button says **Add to {collection}**; both catalogs
provide the corresponding localized wording. The label comes from the actual
bound target's display projection and is escaped. The original hidden source
handle, target handle and keyed revision/generation proof remain authorization.
Equal names do not merge targets, and a target replaced between render and submit
is rejected. No active target means an explicit choice through the existing
collection list; neither the first listed collection nor a hidden new collection
is selected automatically. Missing or incompatible selected Match Snapshots keep
the existing explicit Add/version remedies.

Successful incorporation now returns a private typed outcome retaining status,
accepted evidence and the captured target scope. The HTTP redirect names that
scope, rather than the generic current page. A target replaced before the redirect
GET cannot receive the old outcome or silently become its destination.

The existing compact operation-feedback mechanism renders the accepted Decision,
actual Card and collection plus **Open analysis overview**. Its receipt stores
only the exact binding ID and existing source/attempt/deadline data; labels are
resolved from the still-matching accepted source. It retains the existing
one-delivery, 60-second deadline, enhanced dismissal and native fallback behavior.
No empty panel remains after dismissal. Receipt expiry does not remove evidence.

The individual Report page independently shows **Included in {collection}** and
a stable overview button when its exact Report ID and Snapshot binding are in the
captured Current source set. Inclusion is not inferred from absence in the offers.
Intentional removal makes the Report available again. A fresh different variant
is still a distinct Report. Rejections neither increment counts nor display a new
success receipt.

## Compact, collection-scoped presentation

The collection page and captured overview use one shell heading:
**Analysis overview · {collection}**. The previous repeated debrief heading is
omitted. The detailed retained comparison has a separate **Retained comparison ·
{collection}** title and a clear exact-overview return.

The overview keeps selected Match revisions, the native Player filter and concise
recorded/unique-analyzed/Report counts above compact semantic Decision articles.
Every Report row retains:

* Match, Game, Trick/Card-position and stable Player presentation;
* actual Card;
* the shared retained comparison sentence and authoritative tied-best set;
* the objective and a visible explicit-supplement marker;
* a direct comparison action.

One legal Card shows the shared forced-move explanation without a separate
recommendation or praise. Equality of primary success alone is not a full-objective
tie. The exact shared comparison supplies the decisive metric. Multiple variants
retain distinct entries and objectives; mixed comparisons remain marked. The
original distinct-Decision and per-Player denominator rules are unchanged.

Sample counts, seed, known bid and full supplement/coverage prose move into
per-entry **Analysis inputs and coverage** or the existing detailed comparison.
Full policies, assumptions, metrics and original downloads remain accessible.
The overview has one simulation qualification. Existing exact motif groups and
retained qualified focuses are preserved. It adds no strategic explanation,
coaching eligibility, weakness classification or quality guarantee.

CSS is confined to overview rows and Report collection actions. It uses normal
wrapping, a responsive action column and compact spacing. It changes no font size,
hit-target size, Match capture/creation layout or fixed-height scrolling container.

## Passive navigation, strict reopen, and the zero-count investigation

The bounded disposable diagnostic distinguished these paths:

| Path | Observed behavior |
| --- | --- |
| Include C7 -> comparison -> exact overview | One source retained |
| Include C7 -> ordinary Match current/position navigation -> explicit small S8 analysis -> current collection | C7 retained; S8 available for explicit incorporation |
| Include S8 -> C7 comparison -> exact overview/filter/language return | Two distinct Decisions and two Reports retained |
| GET Learning menu/list | Existing collection context and Reports retained |
| Existing POST `learning/open` on the active collection | New context, zero process-local debrief sources; saved recording unchanged |
| Same-context Corpus Reload | Sources retained; old captured scope invalidated |
| Scope/report-store expiry | Existing guarded expiry behavior; incorporated copies follow their owning collection lifetime |
| Profile reset | Incorporated Report sources retained |
| Explicit debrief removal | Only the selected binding removed; remaining evidence retained |

At the starting build, the active collection card's main action was the strict
Reopen POST. This offered a resetting operation where the user needed passive
current navigation. The corrected card primarily offers **Open analysis overview**
with a captured scope URL. Strict Reopen remains under a secondary disclosure
with its actual fresh-context consequence. Choosing another collection also
explicitly starts a fresh context. The menu renderer matches the overview's bound
handle, not merely a potentially older discovery `active` flag.

No ordinary GET or comparison-return source-loss defect was reproduced. The
strict-reopen sequence reproduces a zero state, but the maintainer's historical
intervening route sequence is unknown. This correction removes the demonstrated
navigation trap; it does not establish the cause of that historical observation
or claim a storage defect was fixed.

The collection inputs link uses the additive scope-checked GET shape
`/learning/debrief/<scope>/<player>/inputs`. It rechecks the expected active owner
before rendering the existing collection page, without strict reopen or arbitrary
redirect input. Source locks are not held across target lifecycle/rendering work.
Existing comparison URLs retain scope, Player filter and exact Report ID. Editable
recording return continues to require the original source checks.

## Preserved boundaries and inventories

`MatchDebriefEvidenceV1`, its source/Snapshot reconciliation, rollout evaluator,
policies, budgets, ranking, ties, precision, public Request/Result/provenance,
Teacher/Dataset/partition/qualified-Coaching semantics and all serializers are
unchanged. Original recording and retained Request/Result bytes remain unchanged.
Collection import/Current policies, eight-scope and 2,048-source bounds are unchanged.
There is no durable Report store, lifetime extension, reimport, automatic analysis,
model training or source-directory scan.

Definition-derived inventories are **72 POST routes**, **124 forms**, and
**2,025 keys per catalog** (13 added keys). The only new route shape is the private
scope-bound inputs GET above. No POST field or form-registry contract changes.
Schemas remain **72 authoritative / 72 packaged**, generated scenarios **102**,
and prepared Corpus downloads **10**. No public export or persisted format changes.

## Browser evidence

`scripts/verify_learning_overview.py` used disposable #288/#289 Hearts fixtures
and the existing dependency-free DevTools harness. Baseline measurements were
taken before Product edits under
`$env:TEMP/opencode/issue289-overview-before-01/`. Final correction evidence is
under `$env:TEMP/opencode/issue289-overview-after-02/`. The intervening `after-01`
run is earlier development evidence. These folders contain `report.json` and
inspected desktop/narrow screenshots, including named individual-Report actions.

Both sides used CPython **3.13.7**, Edge **155.0.4283.45**, and genuine eight-world
Reports for Game 2 Decisions 3 and 17. The retained C7 comparison had equal primary
success and settlement-score totals but a lower local Card-point margin, so the
shared secondary-metric explanation named its retained alternative. S8 had one
legal Card. No Product code hard-codes those Cards or a preferred winning Card.

| Geometry in CSS px | Before | After |
| --- | ---: | ---: |
| Desktop 1365x900: C7 row | 401.08 | 249.52 |
| Desktop: S8 row | 360.28 | 219.92 |
| Desktop: overview section | 1201.22 | 860.20 |
| Narrow 390x844, German/Alex: C7 row | 672.42 | 483.69 |
| Narrow: S8 row | 507.64 | 305.31 |
| Narrow: overview section | 1841.05 | 1418.48 |
| Filter/comparison action height | 44.39 | 44.39 |

Both runs had no measured horizontal overflow (`scrollWidth - innerWidth = -15`,
the scrollbar allowance). The screenshots show normal wrapping and both retained
entries. Viewport resizing is not real browser-zoom evidence.

The final enabled-browser sequence used the named individual-Report action,
incorporated both Reports, opened C7's comparison, returned to the exact overview,
filtered Alex and changed language while retaining the filter and language-button
focus. A second explicitly created disposable target reused the same Reports with
page JavaScript disabled; incorporation used native keyboard activation.

Final counters: **2 explicit fixture evaluations**, **0 recording writes**,
**4 explicit incorporations** (two per enabled/native target), and **17 projections**.
No reuse/navigation step added an evaluation. Setup created synthetic files and
explicitly imported the saved Match into each test target separately. Both exact
Request and Result downloads were compared against retained serializers, and the
recording bytes were unchanged.

## Local validation and remaining acceptance

The before-correction diagnostic module passed **2 tests in 8.79s**. After the
main changes, the complete affected module group passed **535 tests, one platform
skip, in 347.03s**:

```powershell
py -3.13 -m pytest tests/test_learning_overview_navigation.py tests/test_match_debrief.py tests/test_learning_debrief_web.py tests/test_learning_outcome_navigation.py tests/test_learning_report_attachment.py tests/test_learning_report_attachment_web.py tests/test_learning_version_presentation.py tests/test_learning_version_selection_web.py tests/test_learning_direct_entry_web.py tests/test_learning_source_navigation.py tests/test_learning_entry_purpose.py tests/test_task_first_match_and_learning_workflow.py tests/test_match_analysis_action_placement.py tests/test_match_rollout_web.py tests/test_match_decision_selection_web.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py tests/test_frontend_validation_preservation.py tests/test_frontend_language_switching.py tests/test_language_switch_context.py tests/test_language_view_continuity.py tests/test_task_first_language_preservation.py tests/test_operation_feedback_web.py tests/test_operation_feedback_language.py tests/test_packaging_and_distribution.py tests/test_skatmind_rename.py tests/test_unified_local_app_web.py tests/test_unified_local_app_managed_items.py -q
```

After the final source-owner/navigation refinements, Ruff passed and the complete
directly affected modules passed **310 tests, one platform skip, in 156.27s**:

```powershell
py -3.13 -m ruff check .
py -3.13 -m pytest tests/test_learning_overview_navigation.py tests/test_learning_debrief_web.py tests/test_match_debrief.py tests/test_frontend_localization_foundation.py tests/test_complete_frontend_localization.py tests/test_frontend_validation_preservation.py tests/test_language_switch_context.py tests/test_task_first_language_preservation.py tests/test_operation_feedback_web.py tests/test_operation_feedback_language.py tests/test_unified_local_app_web.py tests/test_unified_local_app_managed_items.py tests/test_packaging_and_distribution.py tests/test_skatmind_rename.py -q
```

These invocations overlap. They include the executable installed-smoke registry
assertions and strict reviewed rename inventory; no rename locator was changed.
After the current documentation updates, the feedback, executable packaging and
strict rename modules passed again: **84 tests in 53.72s**:

```powershell
py -3.13 -m pytest tests/test_operation_feedback_web.py tests/test_operation_feedback_language.py tests/test_packaging_and_distribution.py tests/test_skatmind_rename.py -q
```

Final local validation is explicit `scripts/check.ps1 -Mode Quick`, not local Full.
Exact-commit hosted CI, identical-commit integration and the short installed
overview-navigation retest remain required. The original distribution-comparison
uncertainty is not reclassified as resolved by these presentation checks.

Keep #289 and #208 open. This correction improves organization and navigation;
it adds no strategic coaching and does not establish overall Learning usefulness.
