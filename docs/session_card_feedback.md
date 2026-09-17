# Rejected Session Card feedback

Issue #237 addresses the remaining C5 explanation request on the normal unified
`/sessions/cards` and `/sessions/play` forms. The four planning probes were controlled
negative submissions; their Cards were already excluded by the normal palette.
This implementation preserves that prevention and does not claim reproduction of
the complete original UAT trace.

## Accepted evidence, separate from the attempt

The existing source/task HMAC, lifecycle lock, strict file freshness and canonical
Command application remain authoritative. Only after a real rejection does
`app_web/session_card_feedback.py` inspect the structured diagnostic code/path,
typed Command and original accepted projection retained by candidate preparation.
It never parses diagnostic prose, replays a second acceptance engine or reconstructs
unknown hands. Public diagnostic documents and core rules are unchanged.

One optional immutable witness contains a canonical attempted Card, bounded Player
seat ordinals and, where relevant, one accepted Play index or effective suit.
The private validation descriptor additionally binds the exact existing Card-form
selection and route. It contains no State/hand dump, pretranslated text or Player
label. At rendering, the source/task binding and file are revalidated before full
accepted labels and localized Card/suit/fallback Player names are resolved and
escaped. The generic 80-character interpolation bound is unchanged; valid long
labels are never truncated to fit it.

| Supported explanation | Accepted inspection target |
| --- | --- |
| Card already assigned in the initial deal | Recorded hand or Skat |
| Card already played | Exact recorded Player, Trick and Card position |
| Explicitly discarded Card | Recorded discards |
| Known untouched Hand-Skat Card | Recorded Skat |
| Another recorded remaining/public owner | That Player's current recorded hand |
| Missing membership in an exact own/public hand | Actor's exact recorded hand, without inventing another owner |
| Proven obligation to follow | Actual lead in the current Trick |
| Invalid declarer discard membership | Recorded declarer hand-plus-Skat boundary |

Follow-suit requires authorized exact hand knowledge, membership of the attempted
Card and rejection by existing `get_legal_cards`; `get_effective_suit` supplies
Suit/Grand/Null and Jack semantics. Initial Skat assignment does not imply perpetual
ownership after pickup. The #234 final pair, later Plays/revelation, hypothetical
worlds and review knowledge are never witnesses.

Basic empty, malformed, duplicate and capacity messages remain. Unsupported codes,
paths or insufficient facts retain safe fallback feedback. Optional witness failure
cannot turn rejection into success or a server error. If a supported failure can
only be explained by candidate progress, a bounded batch message has no accepted
record link. An earlier unsaved Card in that batch is never labelled accepted.
Specialist Commands/corrections and Match feedback retain their existing fallback
contracts.

## Presentation, lifetime and publication

These two forms show **Card not recorded**, one concrete linked summary, field
association, **None of this selection was saved**, and **Show recorded entry** /
**Change selection** actions. German text lives in the translation catalog.
Session-only hand/public-hand/Skat/discard anchors are natively visible and focusable.
Play links reuse the shared history renderer's optional `session-play` prefix;
Match anchors are unchanged. Links inspect evidence and never select a replacement
or open/apply a destructive correction. Other workflows keep their summary policy.

Feedback remains process-local and exact-context/content/generation/task/form-bound.
Reopen, Reload, edits, Undo, equal-revision changed history, context replacement,
retirement and superseding attempts cannot attach an earlier witness to new facts.
Same-source native language switching retains the attempt and translates afresh.
The existing complete language-source restrictions remain; Card feedback returns
focus to `session-card-error`, including while a valid #221 Result is retained.
Unavailable attempted Cards remain rejected text, never selectable choices. Valid
pending selections remain checked.

The whole candidate still saves once or publishes nothing. #231's missing-ID N+1
versus existing-ID N history, exact custom metadata and all checkpoint variants
are preserved. Rejection, language and inspection preserve Session bytes and valid
Request/Result downloads; accepted edits invalidate Results normally. Successful
explicit entry retains the `303` to `#session-recording`; errors retain `400/409/413`.
The existing registered **8,192-byte** limit is now enforced on `/sessions/play`
as well as `/sessions/cards`: preflight found only the latter wired to its limit.
No incoming field, route, Product format, acceptance rule or save is added.

### Issue #238 response-transport follow-up

The post-merge failure at `cc051c77615edf3a28fee04b5321f00f7ebb4812`
(run `35187708150`, job `105093241807`, Linux/Python 3.13.15) occurred during
the client's complete response-body read after the expected status assertion.
The original loop does not establish whether malformed 8192/400 or oversized
8193/413 failed, and its evidence-content assertion did not complete.

On Windows 11/Python 3.13.7 the unchanged exact test passed. A bounded staged
real-socket regression then established the lifecycle defect on both routes:
headers-only oversized input produced a response followed by full socket closure,
with no body consumption or staged cleanup. This is deterministic lifecycle
evidence, not a reproduction of Linux Errno 104 or proof of its original iteration.

The private unified byte-response path now sends existing rejected responses with
`Connection: close`, flushes, half-closes the sending direction, then discards opaque
input before normal final teardown. It uses the standalone Corpus design's limits:
**65,536 bytes total**, **at most 8,192 bytes/read**, a **250-ms absolute monotonic
cleanup deadline** that arriving bytes cannot renew, and **250-ms socket timeouts
for response writes**. Buffered header read-ahead and late socket input both pass
through `rfile.read1`. No declared length controls cleanup, no discarded bytes are
parsed, and no pipelined request is dispatched. Authorization rejection also replies
first, replacing its former declared-length read before the response. Successful
responses do not drain or change their socket timeout. Transport-only write/cleanup
errors end the connection without generating a second filesystem-error response.

The boundary test now names route and size/status independently, reads the complete
body, checks framing/security headers and absent Card evidence, and preserves all
original duplicate-field and authorization assertions. Genuine retained Request/
Result downloads, accepted State/file/checkpoints and zero save/analysis/witness
calls are checked. `tests/test_unified_rejection_transport.py` covers staged/split
and prefetched input, a valid pipelined mutation discarded without preparation,
missing bodies, excess bytes, departing peers, actual fresh-connection Card saves,
and deterministic byte/deadline/partial-write faults. Socket identity is retained
before teardown; request workers are joined, and client cleanup uses `finally` or
context managers. The standalone Corpus implementation and observer fix are retained.

Local verification uses disposable synthetic roots. The available WSL Ubuntu has
Python 3.12.3 rather than 3.13, and the Docker Linux engine is unavailable; no local
Linux/Python 3.13 pass is claimed. #238's completion gate and #208 UAT-01 approval
remain blocked until `check` and `v1-supported-platform-matrix` pass on the exact
corrected merged commit. This correction is not maintainer UAT.

## Verification and fixture boundaries

`tests/test_session_card_feedback.py` and `tests/test_session_card_feedback_web.py`
pass **34 focused tests**. They use real canonical rejections, current #233/#231
creation, accepted evidence, genuine persistence and #221 execution. They cover all
supported witness kinds, effective suits/Jacks, unknown/public hands, changed Skat
ownership, long/missing labels, code-versus-prose independence, safe fallbacks,
partial batches, exact source changes, competing attempts, retirement, security and
both real request-size boundaries. Fault injection and the helper-only candidate-
dependent fixture are explicitly separate from successful saves/Results.

A language/feedback run passed **37 tests**. A wider affected-path run reached over
900 passing cases but was interrupted at its 20-minute timeout and is not a successful
gate. The prescribed complete corrected-tree check and actual child exit are recorded
in the implementation report, with full external stdout/stderr. No separate six-cell
installation matrix is required for unchanged installation contracts.

The first complete check (`237-full-check-20260916T191253Z.log`) passed Ruff, schemas,
98 outputs and distribution validation, then exited **1** with **9,070 passed,
3 skipped and 2 failed**. The failures exposed eager Session imports at CLI help and
the stale catalog-count assertion. Product imports now occur only during witness
construction, preserving the cold-help boundary; the exact count is **1,545**.
The corrected focused CLI/localization/feedback run passed **85 tests** in **43.84s**.
The final corrected-tree complete check remains the report's authoritative gate.

`scripts/verify_session_card_feedback.py` uses an independently installed Wheel and
the existing dependency-free local DevTools transport. The successful evidence is
`<temporary-directory>/opencode/237-browser-03/evidence.json`: **320 measurements**,
de/en, JavaScript on/off, 1365/390/320 pixels and 320 pixels at 200% text. Document
and client widths agree at **1350/1350**, **375/375**, **305/305**. Full long labels
wrap; error and evidence targets retain visible keyboard focus. Representative
screenshots were inspected for actual returned errors, evidence and continued entry.

Semantic negatives use a clearly labelled harness-owned authenticated request form
copying emitted transport fields. They do not modify or select from the legal palette.
Actual production error responses are displayed in the browser. Native empty input,
language buttons, evidence links, legal radio selection/save and reopen are exercised
separately. Eight synthetic recordings produce **52 successful Session replacements**
and **four real review executions**; all rejected/error-inspection/language intervals
have zero Session replacements and executions, unchanged checkpoint tuples and exact
download hashes. Sixteen semantic negative requests and eight native empty submissions
are tracked separately. No requested browser item remains unmet in the successful run.
An earlier run exposed the retained-Result language-focus issue; its unsuccessful
evidence remains in `237-browser-01`.

Environment: Python **3.13.7**, Package **0.17.0**, Edge **153.0.4234.32**. The installed
Wheel SHA-256 is `41b6cb31f0e901691bc1274a5e404972aed210b855834c6c97fc61f18fc8111c`.
The evidence includes 17 installed module/resource hashes, served CSS/JS parity,
action/focus records, geometry and screenshots. It rejects checkout imports and
resource mismatch. All recordings live in disposable temporary homes.
The final installed run repeats the affected #237 paths after the cold-import fix;
the earlier successful presentation evidence is retained in `237-browser-02`.

## Boundaries and closure

Starting clean branch: `bug/237-session-card-feedback`, HEAD
`a08604050c17837ac7714da9c5dc7ef80068e277`. The focused archive comparison found no
intervening changes in the referenced core validators/rules; #231 startup is preserved.
Package 0.17.0, Python >=3.13, AGPL-3.0-only, dependencies including tzdata>=2026.4,
#230 profile shape, public/Product contracts, 63 routes/107 forms and 98 generated
outputs remain unchanged. There are 16 additional de/en translation keys.

#236 remains completed. Manual #237 closure requires both `check` and
`v1-supported-platform-matrix` on the exact merged commit. #208 and unresolved findings
remain open, UAT-01 failed, UAT-02–12 paused, B-09/B-07 open and B-06 closed. This is
bounded C5 implementation evidence, not maintainer UAT or release readiness.
