# Mode-specific accounting and three-game Cent rounds

## Delivery and acceptance boundary

Issue #322 starts on `feat/322-mode-accounting-cent-rounds` at
`65db02bc7f39e0b6c5c0f7bf95a7bbaea80478b2`. Its starting index/worktree were clean.
#321 branch run 43709016736 and main run 43718786360 passed at that exact commit.
#321 remains open only for the agreed combined installed acceptance. Accepted
#316–#320 and the completed #321 source reviews remain valid.

This implementation adds private exact monetary components, retained accounting
revisions, and native German/English controls alongside ordinary managed recordings.
It uses no Card-analysis invocation. Final local commands, complete-module counts,
durations and outcomes are reported in the implementation handoff after verification.
Exact-commit hosted gates and the single combined installed acceptance remain
maintainer work; neither a source HTTP test nor Quick authorizes issue closure.

## Ordinary tournament workflow

1. Open the Match or attached Session and confirm its existing **Event and
   chronological score** context. A Match checkpoint such as 24 / 780 / 3 needs
   no earlier hands. The selected participant remains the recording perspective.
2. Open **Money and Cent rounds**. Select the named Standard progressive-loss rule
   only when it actually applies. Its proposed readable source/edition are editable;
   an existing supplied source is retained. An unverified policy remains unverified.
3. Confirm the rule's starting game and the consumed prefix. Match accounting can
   include game 36 explicitly. The beginning loss count comes from the retained
   checkpoint or established prefix, not an arbitrary monetary counter.
4. Confirm total entry/table obligations and amounts paid against them. Old
   `paid`/`committed` pairs remain unchanged. The form displays them as a draft and
   requires explicit selection: committed is total, committed is remainder, or an
   independently entered actual total. Payment is never a second expense.
5. Confirm actual Plus level and tandem participation where known. The published
   Plus table rule is an explicit choice; it supplies `0.75 + 0.25 * level` EUR.
   A conflicting supplied total is rejected rather than overwritten. Other actual
   table amounts remain supplied obligations with their own confirmation evidence.
6. Enter actual **personal** base, Plus and tandem receipts separately. A team prize
   is not personal entitlement. Confirm complete receipt coverage only after all
   actual receipts, including zero, are known. No payout table, field ranking,
   score threshold or forecast is inferred.

For Standard, in cents:

```text
F(L) = 50*min(L,3) + 100*min(max(L-3,0),2) + 300*[L>=6] + 500*max(L-6,0)
increment = F(after) - F(before)
F(6) - F(4) = 400
```

The existing fixed-three-player contribution service supplies tournament score and
**own declarer** loss counts only. A defender's loss does not advance that count.
Checkpoint-covered backfill and duplicate semantically agreeing Match/Session
bindings are consumed once through the existing preparation machinery. Earlier
loss costs remain independently unknown unless confirmed, or their applicable
interval starts at zero losses. A cumulative counter alone does not establish an
earlier fee edition. The global `financial_missing` flag is not used for readiness.
Each obligation, receipt, earlier expense, additional loss charge and side result
has its own known/unknown value. Known subtotals remain visible; complete net needs
all necessary components. Payment status may remain unknown without erasing an
established incurred cost.

`tournament_cent` retains a separate confirmed actual side result, with an explicit
unsupported-rule state otherwise. It never acquires three-game Cent arithmetic.
A 24-game provider exception is not modeled as a 36-position Match: the current
Match source adapter remains fixed-36, while Session/context capture retains its
existing bounded applicability. This is a source-adapter limitation, not a blanket
v1 scope exclusion.

## Ordinary Cent workflow

Open or create a normal Session, then choose **Start Cent round with this Session**.
Confirm its three participants, seating, perspective, tariff and actual conditions
once. The supported tariffs are exactly 0.5 / 1 / 2 / 3 / 5 cents. Existing explicitly
confirmed Cent context can be adopted without rewriting that context journal.

Each of three positions can open its Session, create a normal live Session with
rotated seating, or attach an existing saved Session. Source selections retain
exact version identity. Explicit participant mapping is required for source-local
aliases; labels never join people. The aggregate owns three distinct positions and
uses the existing recorder, creation, opening, activation and cancellation paths.
It does not modify the 36-slot Match contract or add another Card recorder.

Established results are obtained through `build_recording_facts_v1`, `OutcomeFactV1`
and `bind_recording_facts`. For an incomplete live recording, a compact confirmation
can retain the actual declarer and signed settlement, an explicit passed deal or
interruption, or an actual external personal game-level monetary result. Such a
confirmation does not invent Cards or make Historical analysis ready. A known
declarer/trace or later complete outcome disagreement is shown as a conflict.
Correct the supplied outcome or select derived evidence with an explicit reason;
earlier interpretations remain retained.

For signed declarer settlement `S` and tariff `t` in cents:

```text
declarer gross = 2*t*S
each defender gross = -t*S
sum of gross transfers = 0
```

Signed settlement already includes loss doubling. No list bonuses or tournament
loss fees enter Cent. `SignedMoneyV1` is a separate reduced signed rational in
currency units with strict bounds; old nonnegative `AmountV1` is unchanged.
Floats, Boolean numbers, nonfinite values, unreduced fractions and out-of-bound
amounts are rejected. Half cents remain exact. There is no balancing-cent policy.

For an established individual positive winning fee base `g` in cents, current
Obolus is `ceil(3*g/100)` whole cents **per game**. Winning-declarer fees are
determined. Winning-defender allocation/rounding remains unresolved. Known losing
payments and determined fees remain visible even when a fractional principal or
defender fee prevents a complete posting. The table distinguishes gross, fee, net,
supplied/derived basis and unresolved reasons. Totals explicitly label known
subtotals and incomplete net.

**Finish** requires three recorded settled/passed/external positions, without
contradictions. **Actual provider block completion** is a separate explicit fact;
three local positions do not establish provider compliance. **Interrupted** is a
distinct state and creates no penalty. Reopen explicitly before correction. The
next-round action confirms continuing participants/perspective/terms and creates
new round/block and Session identities, retaining table lineage. A changed roster
starts a distinct table through an ordinary Session with that roster. Earlier rounds
remain available through native open actions, including after application restart.

An optional personal **whole-block or table-stay net confirmation** is a separate
reconciliation of the same activity, not account balance or table funding and not
an added gain/loss. It retains covered round identities and exact activity
fingerprints. Overlapping confirmations are rejected. Correct/remove an earlier
confirmation explicitly before confirming wider coverage. Later activity changes
leave the original confirmation historical and visibly stale; they do not rewrite
its total or synthesize per-game allocations. A separately evidenced external
adjustment can be recorded. Local browser closure, restart and interruption have
no financial effect, refund or automatic abandonment charge.

## Provider authority and unresolved details

The issue's references were reviewed on 2026-11-15. The current Cent and tournament
fee pages were also retrieved during implementation:

* <https://www.euroskat.com/turniere/36er-standard>
* <https://www.euroskat.com/turniere/gebuehren>
* <https://www.euroskat.com/gebuehren>
* <https://www.euroskat.com/spiele/cent-skat>
* <https://www.euroskat.com/faq>
* <https://www.euroskat.com/turnierordnung>
* <https://www.euroskat.com/turniere/preisverteilung>
* <https://alt.euroskat.com/info/cent-skat> — historical only

Pairwise arithmetic is derived from the provider's point-difference description;
it is not an observed account statement. Current public material does not fully
establish two-defender fee allocation/rounding, fractional principal posting,
passed-deal block eligibility or every interrupted-block posting. The implementation
does not silently choose a policy for those gaps. The old official example's
commercial fee rounding conflicts with current upward-rounding wording and is
not the default. The current published abandonment schedule does not prove that
any particular local interruption caused an external charge. Only an explicitly
confirmed actual external adjustment is recorded. No runtime fetch, login,
scraping, financial transaction, forecasting or learned strategy is involved.

## Private state and compatibility

`mode_accounting.py` owns arithmetic and components. `accounting_state.py` owns
strict private version-1 interpretations, exact retained context preparation,
source facts, applicability, participant mapping, confirmations and round lifecycle.
`accounting_store.py` owns a separate `mode-accounting.json` journal. Native frontend
modules compose those services without changing public Request/Result schemas,
recording codecs, Package/dependency versions or Root workflows.

The journal is created only by an accepted action. It has at most 4,096 accounting
revisions and 16 MiB, with no implicit cleanup. Old revisions are append-only;
current heads replace an interpretation rather than add another posting. Historical
source ownership prevents posting a recording in independent accounts. Strict
resume validates closed fields, versions, fingerprints, linear history, retained
preparation reconstruction and aggregate coverage. Equal saves are byte-preserving
no-ops. Stale forms, journal CAS and fresh recording guards reject replacement.
Writes use bounded checked paths and flushed/fsynced same-directory temporaries,
then a fresh guard and atomic replace. A failed accounting save after explicit
Session creation can leave that ordinary saved Session available for explicit
attachment; it does not invent an accepted accounting or silently delete the source.

The exact old recording, independent collection and retained Request/Result bytes
remain owned by their existing contracts. Both #321 preparation versions reconstruct
from their actual retained facts. This producer does not change #321 journals or
their legacy acknowledgement bridges. Views may calculate a labeled fresh preview,
but write no accounting, execute no Card analysis and do not update Learning.
Learning Update has no dependency on these monetary modules. Existing admitted
invocation ownership, feedback and cancellation guards remain intact.

## Focused evidence and registry review

The new domain module tests arithmetic without repeated archives. A small genuine
fixture set exercises established accepted Session Logs, normal Match outcomes,
checkpoint/backfill/duplicate-source accounting, correction, strict resume,
optimistic failure and no-clobber synthetic generation. Native HTTP form tests cover
both languages, three real managed Session files, restart/reopen/next round,
explicit aliases, stale forms, preserved safe input, historical revisions and
passive byte isolation. These are source-checkout developer observations, not a
graphical browser or installed-acceptance claim.

The current exact inventory is **104 POST routes / 156 forms / 2,521 keys per
locale**. All seven added routes are enumerated in the installed smoke fragment.
Its existing packaging regression executes that exact fragment without building
or installing a distribution. Exact consumers in distribution validation, packaging,
direct Match evidence, validation preservation and localization foundation were
reviewed together. The optional #269/#271 evidence script's historical 67/119 and
1,811-key inventory remains a point-in-time record and was not rewritten or run.

Dependency-based final selection:

* new domain/state/store/native modules;
* all four existing event-context modules for consumed adapters, immutable v1/v2
  preparation and existing exact-byte evidence;
* unified app/managed-item and Session review callers for server rendering,
  registration, source opening and activation;
* complete registry/packaging/direct-evidence, localization, language continuity
  and submitted-value-preservation modules;
* complete Match decision-selection/rollout modules for the unchanged admitted
  invocation and cancellation protections at the modified HTTP server boundary;
* `test_cli_internal_architecture.py` and `test_skatmind_rename.py`;
* after parallel workers exit, exclusive `test_unified_rejection_transport.py` and
  `test_match_analysis_action_placement.py`, because registered rejection and Match
  page composition changed. Standalone Corpus transport and the synthetic early
  rejection observer are not affected and are excluded.

Final validation uses development CPython 3.13, two file-grouped workers with no
restart, external logs and 7,200,000 ms invocation timeouts. Complete selected
modules precede the affected exclusive phase, then explicit Quick and tracked/new
file whitespace checks. No routine Full, new hosted trigger, measurement-only run,
CI-policy change, installed environment or maintainer UAT data is involved.

## Prepared-data plan for one later combined installed check (not executed)

The developer-owned generator only writes three disposable source files into an
already existing external directory, refusing overwrite:

```powershell
py -3.13 tests/accounting_fixtures.py --output-directory "C:\Temp\synthetic-accounting"
```

The generator does not build/install/start an application or create profiles,
accounting, Learning state or UAT. Its no-clobber behavior is tested in disposable
pytest storage. The following is a **maintainer-only later prepared-build plan**:

1. Import `synthetic-checkpoint-match.json` through existing Match transfer once.
   Confirm #321 checkpoint 24 / 780 / 3. Open game 26: 820 / 3. Restart and reopen;
   the same score appears and no loss fee is charged for the other declarer's loss.
2. Import `synthetic-progressive-match.json` once (distinct Match identity,
   perspective player B). Confirm checkpoints 24 / 780 / 4 and 26 / 800 / 5.
   Game 27 is already fully recorded with player B's signed settlement **-144**.
   Open game 28: **606 / 6**. Confirm Standard from game 25 through game 27:
   additional loss cost is **EUR 4**, earlier costs remain unknown. Confirm earlier
   cost EUR 2.50, entry EUR 5, Plus level 2/table EUR 1.25 and personal base receipt
   zero with complete receipts: net is **EUR -12.75**. Paying an outstanding portion
   changes remaining obligation, not that net. Restart/reopen preserves it.
3. Import `synthetic-cent-established.json` once. Start a Cent round at **0.5 cent**
   with selected participant **player B**. Game 1 already has B's loss **-144**:
   B gross/net **-1.44 EUR**; each defender gross **+0.72 EUR**, fee/net unresolved.
   Create/open positions 2 and 3 normally; no hand reconstruction is needed.
   Explicitly confirm B's settlements **+23** and **+100**. B's gross/fee/net are
   **0.23 / 0.01 / 0.22** and **1.00 / 0.03 / 0.97 EUR**. Game-2 defenders retain
   **-0.115 EUR**, with principal posting unresolved. B's calculated round net is
   **-0.25 EUR**. The other participants' complete postings remain unresolved.
4. Finish locally without claiming provider block completion. Restart/reopen.
   Reopen explicitly, correct only game 2 from +23 to +24 with a reason: B's net
   becomes **-0.24 EUR**; old **-0.25** interpretation and original Session bytes
   remain. An optional actual synthetic whole-block net confirms a separate total,
   never adds it. Start the next round with explicitly continuing terms and verify
   the original three positions remain available. Change language in a rejected
   amount form and verify safe values and useful feedback survive.

No previous hands, per-game JSON editing or blanket historical/UAT rerun is needed.
Keep #321 and #322 open until this single combined installed acceptance is actually
recorded. #208 and the separate release/UAT boundaries remain unchanged.
