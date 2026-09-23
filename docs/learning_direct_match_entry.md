# Add recorded Matches directly to Learning

Issue #236 adds one private unified-app shortcut:
**Choose saved Match → Add Match to collection → Evaluate collection → View evaluation.**
It supersedes the former open-Match-first Learning guidance and mandatory
complete-Match wording. Partial and empty valid Workspaces are accepted by the
existing strict import; they do not promise rich decision evidence. No new Engine,
public API, Schema, source format, or persisted result is introduced.

Issue #255 clarifies this existing path and collection purpose. A named collection
holds saved Match versions the user chooses to examine together. Creating it leaves
it empty. It is not a prerequisite for ordinary single-decision review, and partial
input does not require two Matches or complete 36-Game recordings. Evaluation builds
the existing descriptive evidence, dataset, partition and summary artifacts. It does
not run new Card analyses, train a model or adapt future recommendations. Workspace
Add does not incorporate separately executed decision Reports.

| Control/state | Current English wording | Existing operation/target |
| --- | --- | --- |
| Name entry | Create learning collection | `/learning/create` |
| Source choice | Saved Match | Native `source_handle`; no submission on choice |
| Direct Add | Add Match to collection | `/learning/add-recorded-match`, fixed `keep_current` |
| Current inputs | Match versions used for the evaluation | Existing Catalog Current selections |
| Ready | Evaluate collection | `prepare_learning_artifacts` |
| Prepared | View evaluation | Native `#learning-results` link |
| Explicit repeat | Recreate evaluation | Same preparation form in the same secondary position |

The de/en catalogs carry the corresponding localized wording. The extra next-task
panel and adjacent-source jump are removed; source/selection remedies and the real
results link remain. Feedback markers, section anchors and disclosure/form identity
remain available to #223 and #245. Shared Match-transfer policy wording is unchanged;
the shared selected-version caption now says evaluation rather than insights.

## Native routes and discovery

| Method / route | Effect |
| --- | --- |
| `GET /learning/recorded-matches/refresh` | Refresh bounded read-only managed-Match discovery; redirect to `/learning/current#learning-recorded-matches` |
| `POST /learning/add-recorded-match` | Copy one explicitly selected saved Match into the exact active collection; successful `303` returns to the same section |

The first explicit collection-page GET initializes missing Match discovery once.
Ordinary renders, errors and language changes reuse its retained object/generation.
Refresh is explicit. Discovery remains nonrecursive, with at most 2,048 candidates;
the existing truncation condition is visible. A bounded strict classification at
submission rechecks availability and duplicate identity without publishing another
discovery generation. There is no library-wide decision preparation or analysis.

One native required selector starts unselected. Friendly names, list ordinals and
listed revisions distinguish choices, including equal titles. Invalid and duplicate-
identity entries are explained and non-actionable. Only managed Matches are sources.
The recording list remains optional navigation; opening a recording is unnecessary.

The exact URL-encoded fields are `managed_handle`, `source_handle`,
`source_generation`, `expected_catalog_revision`, `learning_selection`, and
`same_revision_resolution`, plus optional existing `_frontend_form_instance`.
Every field is singular. The actual HTTP reader enforces **8,192 bytes before
parsing**. There are no caller paths, documents, fingerprints or analysis payloads.
The private registry now contains **63 POST routes / 107 forms**.

## Source capture and target lifecycle

`learning_direct_entry.py` binds the target's unique process-local key, exact
Catalog content fingerprint, context generation/revision, and retained discovery
identity/generation. Reopened and equal-revision different collections do not share
bindings. Source resolution uses the retained discovery, but means the **currently
valid saved version at submission**, not the revision shown in the earlier list.

The Match lifecycle gate serializes capture with source activation and #235 deletion.
An active source also uses its Capture lock and must match the strictly loaded disk
fingerprint. An inactive source is strictly loaded without activation. The existing
direct-child/type checks, bounded non-link file digest, root/file stamps, strict
Match loader, and canonical Workspace serializer are reused. Source changes during
capture, missing/replaced identity, malformed files, ambiguous identity, links,
junctions/reparse points and detectable multiple hard links are refused. The source
is never rewritten, reloaded into the active recording, or enriched with #234's
presentation-only unplayed Cards.

After immutable capture, source locks are released. A separate narrow Learning
lifecycle gate, shared with target activation, guards exact target revalidation and
`import_workspace_bytes_into_unified_learning_v1`. Product locks precede short app
snapshots; file I/O holds no global app/profile lock. Match and Corpus locks are
never held together. A replaced target receives neither an old request's write nor
its outcome notice. The adapter does not retry.

Deletion before guarded capture rejects the add. An independently authorized copy
already captured may finish importing after source deletion, including deletion's
discovery refresh. It does not recreate the editable source, touch a deletion preview,
or retire another context. Unrelated Session Results, Match Reports, selected Game,
recovery preview/expiry and profile bytes remain intact.

## Versions, outcomes and persistence

This shortcut fixes `selection_mode=keep_current` server-side. Existing Match-side
transfer and multipart upload still default to `select_imported`.

* A new logical Match's first version is added and selected by the existing contract.
* Another saved version is retained while keeping Current. Existing version controls
  explicitly select another retained version; two versions are not two Matches.
* Exact identical input is `unchanged`: no object/Catalog write, selection change,
  prepared-object replacement, or download-byte change.
* Same-revision different content with default `reject` is the normal HTTP `200`
  `resolution_required` no-change result. The chosen source is retained and Advanced
  visibly exposes `retain`; only another explicit submission can retain both.
* Applied new content invalidates preparation even when Current stays unchanged.
  Rebuilding remains explicit.

Notices use the actual import status/relation and accepted exact selected Snapshot,
and show the copied Workspace revision. Validation uses contextual `400`, stale/source/
Catalog conflicts `409`, oversize `413`, and applied/unchanged success `303`.
Failures remain in Learning with safe submitted values and current transport bindings.

The existing canonical import classifies once and saves the Catalog at most once.
Immutable object publication may precede a Catalog compare-and-swap conflict and
leave a valid orphan reported by strict Resume. No rollback/unlink cleanup, stronger
cross-process transaction, automatic selection, retry or synchronization is claimed.
Imported copies remain independent of later source edits/deletion.

## Progression and coverage

No imported Match means choose one here, or record one if none is available.
Current input without preparation leads to explicit Evaluate. Missing selection remains
defensive guidance. A non-current retained Report source exposes its existing native
remove/clear controls outside closed Advanced content; restoring the matching version
also remains possible. Matching prepared input leads to **View evaluation** at
`#learning-results`; **Recreate evaluation** remains secondary. No persisted wizard is added.

Preparation reuses its existing operation, Corpus-derived dataset ID, seeds `0/0`,
weights `70/15/15`, and editable Advanced options. Observed/usable/skipped decision
counts and dataset status describe coverage, not completion of 36 positions, Player
strength, or mistake counts. Zero decisions is valid empty evidence. Ordinary
summaries require no Teacher Reports; absent coaching evidence is not zero mistakes.
All ten downloads retain their existing filenames, canonical bytes and lineage.
GET, source choice, refresh, import and language changes never prepare artifacts.
Reload/reopen/restart preserves imported files but can require explicit rebuilding
of process-local results. Nothing is automatically recreated.

## Language, accessibility and verification

Current #255 evidence is linked from the
[visual contract](unified_workflow_visual_contract.md#learning-entry-and-purpose-issue-255).
It preserves the existing Add destination `#learning-recorded-matches` and Build
destination `/learning/current`. Return-position repair, version/conflict ergonomics,
R14 result interpretation and ten-download organization remain separate follow-ups.
Automatic Match inclusion, incorporation of executed Reports and adaptation of future
recommendations remain distinct open product expectations; explaining today's explicit
operations neither accepts nor rejects them. The historical #236 evidence below is
retained with its original counts.

The exact de/en catalogs have **1,529 keys** with matching placeholders. Safe submitted
values survive contextual errors/language changes; #223's browser-only unsent values
survive only with its enhancement. Hidden bindings are regenerated; no destructive
consent is restored. Native keyboard/no-JavaScript forms, focusable section anchors,
app-owned shrinkable CSS, Host/Origin/token checks, CSP and no-CORS rules remain.

All fixtures use disposable synthetic managed homes. The new adapter/HTTP tests use
real save/import/preparation/download operations, genuine Session/Match Results,
real #235 deletion, controlled source/target races, strict restart and actual Catalog
CAS/orphan outcomes. Symlink creation has an honest platform-permission skip;
hard-link/junction and oversized-file fixtures perform actual filesystem operations.
The broad 46-module affected run produced 946 passes, three skips and two obsolete
Learning-text assertion failures. Corrected private UI assertions and the expanded
focused run passed **120 tests, one skip, in 63.43s**. No core acceptance was relaxed.

`scripts/verify_learning_direct_entry.py` uses the existing dependency-free DevTools
harness and an independently installed Wheel. Legal fixture setup is identified
separately from native actions. September 16 evidence in
`$env:TEMP/opencode/236-browser-3/evidence.json` and adjacent screenshots covers
Edge **153.0.4234.32**, CPython **3.13.7**, Package **0.17.0**, de/en, scripts on/off,
1365×900, 390×844, 320×800 and representative 200% text: **144 passing measurements**.
Each native run adds an inactive source, builds real **6 observed / 2 usable / 4
skipped** coverage with no Teacher, navigates results/downloads, preserves identical
input, retains an update, explicitly selects/rebuilds, resolves same-revision content,
and switches language while remaining in Learning. Each records exactly five import
invocations, three builds and only the separately identified fixture activation.
All ten download hashes, served resource/module hashes, requests, focus and geometry
are retained. Earlier `236-browser-1` and `236-browser-2` runs are passing narrower
evidence; the third adds enlarged controls and retained-version measurements.

* Wheel SHA-256: `78909a1b8d1bf0cca341716a8debd1882b74d63095a05a5653041a2eb338ffe1`.
* Served CSS SHA-256: `65e5452fdde73c4d9c45fbb9742602c7d782c693f8c7613d85da9184f9092865`.
* Existing script SHA-256: `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298`.

Final complete-check native output/child exit accompanies the completion report.
The first attempt, September 16 **14:17:33–15:17:30 UTC**, passed Ruff, schema parity,
input schemas, 98 generated outputs and Wheel/sdist/clean-install checks, then failed
with **9,037 passed / 3 skipped / 1 failed** in pytest. Actual child exit was **1**;
full output is `$env:TEMP/opencode/236-full-check-20260916T141732Z.log`, with adjacent
exit metadata. The exact rename inventory detected seven README line-number shifts.
Only those references were updated; historical line hashes/classifications remain
unchanged. This failed attempt is not success; a corrected-tree full check is required.
The external logger separately captured both streams and propagated a harmless
child's exit **23**, recorded in `236-proof-20260916T141648Z.log` and metadata.

Both `check` and `v1-supported-platform-matrix` must pass on the exact merged commit
before manual closure. #235 remains completed. #208/unresolved findings remain open;
UAT-01 failed, UAT-02–12 paused, B-09/B-07 open, B-06 closed. This is not maintainer
UAT, a whole-UAT pass, release preparation, or a change to the closed technical ledger.
