# Delete a saved Session or entire Match

## Confirmation presentation (Issue #261)

Starting clean `bug/261-recording-deletion-presentation` HEAD:
`9977fb93c5909388423ac64c9b5517d354555e69`, after integrated #260. The actual #261
specification, R15 in #208's consolidated retest and the supplied post-#259
reconciliation identify R15a/c/d as presentation work. Current source reproduced
the two German Match grammar errors, repeated confirmation composition and extra
valid-preview destinations. R15b's chooser opening caption was already correct;
R15e's unchecked consent is preserved. This is not whole-R15 human acceptance.

| Entry action | Captured scope | Final action after native consent |
| --- | --- | --- |
| Delete Game recording | Entire saved single-Game Session recording | Permanently delete Game recording |
| Delete entire Match | Entire saved Workspace, all 36 positions including empty and passed | Permanently delete Match |

Both catalogs express the same scope. Available managed list/chooser entries still
open Preview; the first click removes nothing. The name appears once prominently,
followed by compact family, recorded Players and accepted progress. Match counts
are labelled recording/passed/empty counts, not completed-Game counts. Escaping and
the existing managed-name projection cover long, same-title and imported labels.
Names never resolve the target. The old raw Product-ID disclosure is omitted.

The normal confirmation keeps these consequences visible before consent:

* **Unconditional:** whole-recording removal, no Undo within SkatMind, retained
  independent exports/Learning copies and unchanged other recordings/Players/settings.
  The existing advice to Cancel and use opening/download controls for a copy is shorter.
  This promises neither secure erasure nor an inability to restore a separate file.
* **Captured active target only:** its in-memory Results, Reports and correction
  previews are discarded; running work cannot publish Results for the deleted source.
* **Post-removal refresh failure:** the original untimed deleted-with-warning outcome
  remains, with its list-refresh remedy and no repeated deletion. Pre-removal refusals
  retain their original diagnostics and valid state.

The two native forms retain their order, fields and validation: required unchecked
checkbox, literal `confirm_delete=on`, destructive Apply and secondary Cancel.
Only valid confirmations lose the extra in-content `RETURN_AREAS` links. The routing
domain, exact Cancel return, global navigation and non-actionable fallback links
remain. Invalid/expired pages expose neither fabricated Cancel tokens nor Delete.
Language clears consent while preserving the exact selection and nonrenewed expiry.
There is no new discovery, read, lock, token, write, JavaScript or history mechanism.

The registry remains **67 POST routes / 112 forms**. Two family-specific final
captions and two scope captions replace the generic final caption and technical-ID
caption: **1,800 -> 1,802** paired, ordered, placeholder-checked keys. Package
0.17.0, Python >=3.13, AGPL-3.0-only, all dependency floors including tzdata>=2026.4,
public/persistence contracts and 98 generated scenarios remain unchanged.

The original #235 implementation and historical evidence follow. The current
[installed verification](unified_workflow_visual_contract.md#recording-deletion-confirmation-issue-261)
uses independent Wheels and disposable synthetic roots. Exact merged-commit `check`
and `v1-supported-platform-matrix` must pass before manual #261 closure. #260 remains
completed; #208, other residues and automatic-Learning decisions remain open.
UAT-01 is unaccepted; UAT-02–12 paused; B-09/B-07 open; B-06 closed.

## Original deletion implementation (Issue #235)

Issue #235 adds a **private managed-file lifecycle operation** to the unified local
app. Available Session and Match entries in their normal lists and
`/review/recorded` offer a secondary deletion action. A Match means its entire
single Workspace file and all 36 positions, including passed deals. Separate
recordings with equal titles remain separately addressable. The existing
single-use Create guard and deliberate same-title creation remain intact.

## Permanent scope and retained copies

One confirmed action permanently unlinks one exact discovered file. There is no
app Undo, recycle bin, restoration, secure erase, automatic backup, bulk action,
invalid-file cleanup, or deletion of Learning collections/Snapshots. This is not
a Game Command or a presentation-only change.

The frontend profile remains byte-identical, including known Players, defaults,
time zone, and the recording's now-dormant display label. Independent exports,
other recordings, Corpus Catalog/Snapshot bytes and Current selections remain.
No collection scan, cascade, transfer, preparation, analysis, or new Checkpoint
runs because of deletion. Removing a recording does not erase all copies or all
personal data. Cancel first to use existing open/download controls if a copy is
wanted. An independent explicit transfer that already captured valid immutable
source bytes can finish under its existing lifecycle after source removal.

## Exact private HTTP contract

| Method / route | Exact operation fields, excluding optional existing instrumentation |
| --- | --- |
| `GET /recordings/delete` | Render the current preview or safe navigation/outcome; no query selection |
| `POST /recordings/delete/preview` | `family`, `handle`, `generation`, `return_area` |
| `POST /recordings/delete/apply` | `deletion_selection`, `confirm_delete=on` |
| `POST /recordings/delete/cancel` | `deletion_selection` |

Family is exactly `sessions` or `matches`. Return area is the corresponding family
or `review`, mapped to `/sessions`, `/matches`, or `/review/recorded`. No client path,
filename, arbitrary URL, file content, or fingerprint is accepted. Single fields
cannot repeat. Every new POST enforces **8,192 bytes before reading the body**, as
well as registering that bound. Optional `_frontend_form_instance` retains its
existing bounded cardinality. The three definitions bring the private registry
to **62 POST routes / 106 forms**, without adding public or persistence versions.

One native confirmation page names the recording, family, recorded Players, and
actual source progress. Originally, exact Product identity was secondary; #261
omits that raw-ID disclosure. Paths remain absent.
The checkbox starts unchecked; Apply accepts only literal `on`. Native required
validation, visible keyboard focus, and server validation work without JavaScript.
The destructive action receives no default focus. Error rerenders and both language
directions never restore affirmative consent. The de/en catalogs have **1,508
matching keys** with exact placeholder parity.

At most one pending preview is retained. A fresh opaque selection binds the exact
discovered path/handle/family, Product identity, canonical content fingerprint, raw
digest, file/root identity, displayed source/label, and relevant active-context
state. Its monotonic **30-minute expiry never renews**. A newer preview supersedes
the old one. Old Cancel/Apply cannot act on or attach feedback to the newer target.
Reopen, source/label change, accepted edits, and relevant active-state changes
require a fresh preview. Language alone preserves the target and original expiry.
Restart or explicit later reimport cannot revive a consumed deletion selection.

## Filesystem checks and outcomes

The manager reuses current strict discovery, managed direct-child validation,
the public Session file loader, and the strict Match loader. It deletes the
resolved discovered path, which can differ from the canonical generated basename.
It performs no migration Save. Before removal it checks root/target type,
containment, existing size bound, reconstructed identity, fingerprint, raw digest,
file identity, and current duplicate-identity classification. Links, junctions,
reparse points, directories, nonregular files and detectable multiple hard links
are refused. A reached discovery cap is conservatively unavailable for deletion.

On CPython 3.13 Windows, `lstat` and descriptor `fstat` can expose different `ctime`
semantics. Cross-checks compare device/file ID, birthtime, modification time, size,
link count and type; each full path/descriptor stamp is also rechecked separately.
The file is read boundedly, with `O_NOFOLLOW` where provided by Python's platform.
Existing legacy Session files rejected by default public-loader output-schema
validation remain invalid managed entries; deletion does not bypass that boundary.
Legacy Match files accepted by the strict loader retain their original bytes.

Lock order is the deletion gate, existing family lifecycle gate, relevant Product
lock, then short app snapshots/publication. Filesystem work holds no global app or
profile lock. Source checks run again after acquisition. Accepted attempts consume
their selection even when removal is refused. Competing Applies remove at most
once. The only removal is one `Path.unlink()`; there is no recursive helper,
permission change, shell deletion, retry, quarantine, rollback write, or restore.

* Invalid forms use contextual `400`; missing/stale/changed selections use `409`.
  Pre-removal failures leave accepted files and active artifacts intact. Filesystem
  refusals explain local access/other-program checks without raw exceptions/paths.
* Successful preview, cancel and apply use `303`.
* After unlink succeeds, deletion and retirement are committed **before** refreshing
  the affected discovery. A refresh exception produces explicit deletion-success-
  with-refresh-warning presentation, never a claim that the file survived. No
  automatic next-item activation or recreation occurs.

This assumes one app owns its managed working files. Rechecking and unlinking are
separate operations: an uncontrolled external writer can still change the path
between the final check and unlink. **This is not atomic compare-and-delete** or
distributed locking. Tests detect observed races; they do not eliminate that gap.

## Active-source retirement

Preview/Cancel do not activate inactive recordings or clear current Results,
downloads, selected Match Game, or recovery preview/expiry. Inactive deletion keeps
unrelated active contexts and manual Analyze/Review drafts and Results.

Active deletion detaches exactly its family context, invalidates its execution
attempts or Report generation, and clears its Result/source labels, Reports,
recovery and source-bound language/feedback bindings. Narrow private retired guards
prevent old adapter work from saving or publishing into that context. Delayed
computation may finish, but cannot publish a new Result for the deleted source;
this does not claim forced computation termination. Ordinary source-bound old
Card/correction/review tabs receive missing/stale handling. Independently invoked
legacy/public transports retain their own semantics.

## Synthetic verification and installed-browser evidence

All deletion tests use new disposable managed roots. No maintainer profile, normal
data root, or real UAT recording is used. The three `test_recording_deletion_*`
modules pass **54 tests with one actual-symlink-permission skip** in **67.75s**.
They exercise real returned-form creation and removal, same-title active/inactive
sources, completed Session Results, genuine Match Reports/recovery after 30 Plays
and two passed positions, retained Result bytes under permission refusal, real persisted
Corpus import and strict reopen, independent in-flight transfer, delayed real
execution, concurrent Apply, source/revision/replacement/reimport conflicts,
consent, language, request/security bounds, and honest permission/refresh faults.
Hard links and Windows junctions are real fixtures. Reparse attributes and a small
size-bound override are explicitly simulated. The affected 32-module regression
run passed **710 tests with one existing skip in 548.48s**. A later focused run
passed 180 tests with one skip and exposed the legacy-Session fixture's incorrect
availability assumption; the corrected new-test run above preserves the existing
invalid-entry boundary. Final complete-check evidence accompanies the report.

`scripts/verify_recording_deletion.py` reuses the dependency-free local DevTools
transport and requires a separately installed Wheel with matching source/resource
hashes. It performs native keyboard creation, preview, Cancel, consent, unchecked
submission, stale Apply following competing real HTTP open, language switching,
and real deletion. Run with that installed interpreter:

```powershell
python scripts/verify_recording_deletion.py --browser "PATH_TO_EDGE" `
    --output "FRESH_SCRATCH_DIRECTORY" --wheel "INSTALLED_WHEEL"
```

September 16 evidence uses CPython **3.13.7**, Package **0.17.0**, and Microsoft Edge
**153.0.4234.32**, in de/en with JavaScript enabled/disabled. All **224 measurements**
pass at **1365×900, 390×844, 320×800**, plus representative **200% text**. There are
**16 actual removals** (8 Session / 8 Match), each deleting exactly one file. Preview,
GET, Cancel, native unchecked attempts and stale Applies remove zero files. Both
active and inactive equal/long-title sources are covered. Profile and remaining
recording bytes are checked after each removal; language preference writes are
checked separately. Focus, request paths/statuses, file hashes and screenshots,
including enlarged confirmation controls, are retained in:

* `$env:TEMP/opencode/235-browser-5/evidence.json` and adjacent PNGs;
* Wheel SHA-256 `4009468719b24f63061e75cdebfd1a9a2541938f0782660c3fe39d954fbe90c3`;
* served CSS SHA-256 `3ef51804096826ca264d43d44ab812ffeb9b55a20274f68ad0f5e384b7a4574d`;
* unchanged script SHA-256 `f15857d1303a9a46f42b13ae3311533f50d822f8ef4f47d0d5c8015c04cf5298`.

Browser attempts `235-browser-1` and `235-browser-2` retain the failed English
320-pixel/200%-text implicit-grid overflow evidence. A scoped `minmax(0, 1fr)`
confirmation-form track fixes it. `235-browser-3` passed, and `235-browser-4` adds
the enlarged-control and checked-focus screenshots on the same installed source.
`235-browser-5` repeats all 224 measurements and 16 removals on the final Wheel
after restoring lazy deletion-state construction for CLI help.
An initial no-isolation build lacked its build backend; the normal isolated Wheel
build and independent installation succeeded without dependency changes.

The external full-check logger was proven with a harmless child writing stdout
and stderr and exiting **23**; both streams and the actual nonzero status were
retained and propagated. Final check logging remains outside repository files.
The first full attempt on September 16, **09:39:54–09:48:36 UTC**, failed with actual
child exit **1** at the installed-Wheel smoke test's stale 59-route/103-form
expectations. Ruff, schema parity, input schemas and 98 output validations had
passed; pytest had not started. Its complete output is retained as
`$env:TEMP/opencode/235-full-check-20260916T093954Z.log` with adjacent exit metadata.
The installed smoke now asserts exactly 62 routes/106 forms and the three bounded
deletion definitions. A complete corrected-tree check is required; the failed
attempt is not counted as success. Browser evidence remains bound to the identical
installed application source/resources; this correction changes validation only.
The second full attempt, **09:50:00–10:48:36 UTC**, passed all build/schema stages
and finished pytest with **9,002 passed, 2 skipped, 1 failed in 2,463.27s**. Its
unchanged `app --help` startup test detected the deletion state's eager Product
imports. The complete log is `235-full-check-20260916T095000Z.log`, with actual child
exit **1**. `context.py` now constructs that private state lazily, preserving the
startup guard rather than weakening it. The focused CLI/deletion run passed
**116 tests with one skip in 70.98s**; installed-browser verification was repeated
on the corrected Wheel. A complete corrected-tree success remains mandatory.
Both exact-merged-commit CI jobs, `check` and `v1-supported-platform-matrix`, remain
required before closure. This is not maintainer UAT. #234 remains completed; #208
and unresolved findings remain open, UAT-01 failed, UAT-02–12 paused, B-09/B-07 open,
B-06 closed. No whole-UAT or release-readiness claim is made.
