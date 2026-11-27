# Current-turn Live advice in 36-game Match capture (#329)

Start Live on the selected game's ordinary recording page, even if setup is
incomplete. A declaration, hand/evidence edit, card, applied correction or
truncation can make the next perspective turn ready. Only the accepted save
counts. Draft declaration fields accompanying an evidence submission have no
effect. A page refresh, language change, preview, unchanged edit or change to
Match metadata does not run an analysis. Start and Stop apply to this game only;
a different position, clear/pass, reload and reopening also drop assistance.
Effort changes are saved for the game. **Apply to this Match** additionally
sets the default for games without a deliberate selection. Neither saving nor
inheriting this default starts advice on another game. Private choices follow
the selected managed file across its guarded saves; a separately imported or
replaced copy does not acquire the original's choices by Match ID or title.

The private adapter uses the recording projection's validated trace, including
the current incomplete trick, rotated player order and **all** remaining cards
of the perspective hand. The legal set determines whether to compare choices or
show the single-card rule hint. A defender's and a Hand declarer's stored Skat
are hidden. A pickup declarer needs their initial hand, original Skat and two
discards; only the discards enter the Position as known out-of-play cards.
Only decision-time visible facts establish matadors. In a partial Match there
is no public opponent-hand editor: defender advice against an Ouvert declarer
waits rather than reconstructing that hand. No opponent statistics, later
games, observed response or actual-card annotation enter the evaluator.

Start, effort and Stop are native forms. The recorder reserves an attempt against
its saved Workspace, selected game, control generation, per-file write epoch and
operation-feedback identity. Exact file checks surround unlocked preparation and
evaluation and guard the rendered result at delivery. A cooperating replacement
and restoration advances the per-file epoch even when the bytes end up identical.
The comparison is transient: the Workspace is the ordinary recording, and no
Live Report is admitted to the archive or Learning.

The existing [whole-game policies, objectives and effort budgets](current_turn_live_advice.md)
apply: 25/100/400 common worlds and 5/30/60 seconds of evaluator time.
Percentages describe party success under those policies. They do not estimate
tournament payouts or optimize monetary tournament returns.
The separate [private monetary evaluator](tournament_money_valuation.md) values
fully specified scenarios for post-list analysis and training.

## Prepared installed Match check (pending)

Use the disposable seven-play Workspace from the source check. Import it via
the unified Match page, then select **game 2**. Alternatively reproduce it with
the following ordinary inputs:

1. Create a 36-game Match with game-1 forehand **Anna**, middlehand **Boris**
   (perspective), rearhand **Clara**. Start game 2: Boris is now forehand,
   Clara middlehand and Anna rearhand.
2. Enter Boris's initial hand `CA C10 CK CQ CJ C9 C8 C7 SA S10`. Declare
   **Boris, Grand Hand, bid 24**, leaving matadors unspecified. Leave the Skat
   unknown. Record `CA SK HJ`, `H9 C10 HA`, then `SQ`. The synthetic source
   factory `seven_play_match` in `tests/test_match_live_advice.py` uses these
   native forms; the supplied Workspace already contains this prefix.
3. Start **Quick**. Anna is next: only unscored choices. Record **H8**.
   Boris can follow with **SA** or **S10**. Both tiles must show **10/25, 40%**;
   SA is recommended on mean final point margin **−24.16** versus **−25.36**.
   Switch language; the same comparison remains, with unchecked radios.
4. Select **SA** and explicitly record it. Boris leads next with seven choices.
   **CQ** and **CK** both win **21/25 (84%)**; CQ leads on margin **3.04** to
   **1.36**. **CJ** shows **20/25 (80%)**. Other legal cards remain selectable.
   Record **CK**: the next opponent receives no forecast. Stop or switch games;
   returning to game 2 after switching must show Live off.

### Source-only observation

Development CPython 3.13.7, headless Edge 157.0.4341.60, page JavaScript
disabled, disposable loopback home, 1440 × 900 CSS pixels. From the native
record button through persistence, evaluation, redirect and the percentages
visible in the viewport, **H8 took 2.128 s cold** (English; 25 worlds, 50
terminal evaluations, 1,100 transitions). **SA took 0.442 s** (German; 25
worlds, 175 terminal evaluations, 3,675 transitions). These final observations
overlapped the affected two-worker pytest run. The redirect targets the choices
directly, including the single-card rule hint. Both languages aligned the
percentage rows. Native arrow keys changed the selected card without recording
it. These individual measurements are not installed acceptance or response-time
guarantees.

Keep #329 open for branch feedback, published-source review, maintainer
integration, exact-commit main `check` and `v1-supported-platform-matrix`, then
the installed Match check above. #327/#328 acceptance and #326's retrospective
latency deferral stand; #208 remains open.
