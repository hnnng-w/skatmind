# Recording the bidding sequence

In Live play or Retrospective recording, open an individual game, a Cent game
or a started 36er position. In **Bidding sequence**, record each action as it
happened. The name at the prompt follows that game's seats, including rotation.
Each submission saves one action. Stop between any two actions, close the app
and resume at the next player. When the sequence is unknown, use **Short entry**
to record the declarer and final bid instead. Opening an older short record
does not change its bytes or fill in a sequence.

## Rules and declaration

The authority is the [November 2022 ISkO](https://dskv.de/app/uploads/sites/43/2022/11/ISkO-2022.pdf),
§§3.3.1–3.3.8 and the game-value table on printed page 44.
Middlehand bids to forehand; rearhand then bids to the remaining player.
The bidder can pass or name any higher legal game value from 18 through 264;
the listener can pass or hold precisely that value. For example, starting at
35 records one bid, with no implied bid of 18. A pass is final within that
account of the auction. The last remaining player gets the game at the highest
spoken value. If both challengers pass immediately, forehand must still choose:

| Forehand action | Recorded outcome | Declaration |
| --- | --- | --- |
| Take | Forehand takes an unbid game; no spoken value | Effective minimum 18 |
| Pass | Passed out; no declarer or bid | None; no plays or settlement |

The existing game-type, Hand, announcements, Skat and discard controls still
record their own facts. In complete capture the declaration uses the derived
winner and value. Short entry retains the previous declaration validation.

## Persistence and correction

* Individual and Cent games use the Session accepted log. A `record_bid`
  Command has `command_version: 2`, the acting `player_id`, `action`, and
  `value` (null for `pass` or `take`). A log containing such a command has
  State and projection version 2. Replay derives both the turn and outcome.
  A prefix containing only version-1 commands keeps its original representation.
  The [public Session API](public_session_api_v1.md#versions-and-options)
  exposes both supported versions through `get_session_api_version_info_v1()`.
  Its `RecordingCommand` union includes `RecordSessionBidCommandV2`, which can
  be constructed with the public `BidAction` or parsed from a command mapping.
* Match Workspace slots with bidding use `match_workspace_slot_version: 2`.
  The ordered `bidding` entries retain only the actor's then-known perspective
  initial hand, or null. A passed slot keeps its pre-play facts in `passed_game`
  for correction, while the existing passed-deal representation counts the
  position. Other slots retain version 1. The existing enclosing persistence
  documents, canonical fingerprint inputs and optimistic atomic saves apply.
* A correction changes the recorded account, not the moves permitted at the
  table. Select the erroneous entry. Valid subsequent actions are replayed.
  Removing a conflicting continuation requires confirmation. Session replay
  stops at the first rejected command; Match validates the whole candidate
  before saving it. A corrected Match retains its identity, seats, timecode,
  original Skat and independent initial-hand evidence. A conflicting
  declaration and its dependent discard/play/annotation facts must be recorded
  again. A stale form must be reopened.
* Bidding uses public observations only. Session knowledge at an action is
  bounded by its log prefix. Neither later hands nor later Skat/discards are
  inputs to the bidding turn. No card Decision Checkpoint, analysis, Learning
  selection or generation is created by recording a bid. Previously executed
  evidence remains associated with its original saved source.

## Narrow installed acceptance for #337 (pending)

Using a fresh local data home, use German Live play and English Retrospective
recording. In an individual game enter a jump, hold and pass; restart between
actions and finish the declaration. In a rotated Cent game enter three passes,
advance to the next dealer, reopen and correct the last pass to a take. Check
the original accounting receipt and saved effort. In a rotated Match position,
enter a full auction and a declaration with cards; change an earlier bid,
first declining then confirming removal of a conflicting continuation. Verify
stale tabs cannot save, earlier evidence/downloads still identify their
original source, and no evaluation or Learning starts. Reopen a short record
without edits and compare its bytes. Use keyboard-only submission at narrow
width. This is the maintainer's installed scenario after exact-main acceptance;
#208 and the remaining decision-chain work are separate.
