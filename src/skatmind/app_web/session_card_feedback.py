"""Bounded witnesses for rejected normal Card Commands, never an acceptance engine."""

from __future__ import annotations

import re
from dataclasses import dataclass

from skatmind.deck import get_full_deck
from skatmind.rules import get_effective_suit, get_legal_cards

_KINDS = {
    "assigned_hand", "assigned_skat", "played", "discarded", "hand_skat",
    "owner_hand", "owner_public", "missing_hand", "missing_public", "follow",
    "discard_membership", "batch",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCardWitness:
    """Seat ordinals refer only to the separately verified accepted source."""

    kind: str
    card: str
    player: int | None
    owner: int | None = None
    play: int | None = None
    suit: str | None = None

    def __post_init__(self):
        if (self.kind not in _KINDS or type(self.card) is not str
                or self.card not in get_full_deck()):
            raise ValueError("A witness requires a supported reason and one canonical Card.")
        for value in (self.player, self.owner):
            if value is not None and (type(value) is not int or not 1 <= value <= 3):
                raise ValueError("Player references must be bounded seat ordinals.")
        if self.player is None and self.kind not in {"assigned_hand", "assigned_skat", "batch"}:
            raise ValueError("This witness requires an attempted Player.")
        if (self.owner is not None) != (self.kind in {
                "assigned_hand", "played", "owner_hand", "owner_public"}):
            raise ValueError("Only owner witnesses contain a recorded owner.")
        if (self.play is not None) != (self.kind in {"played", "follow"}):
            raise ValueError("Only Play witnesses contain an accepted Play position.")
        if self.play is not None and (type(self.play) is not int or not 1 <= self.play <= 30):
            raise ValueError("Play position must be bounded.")
        if self.kind == "follow":
            if self.suit not in {"C", "S", "H", "D", "TRUMP"}:
                raise ValueError("Follow-suit requires a canonical effective suit.")
        elif self.suit is not None:
            raise ValueError("Only follow-suit witnesses contain an effective suit.")


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionCardFeedback:
    selection: str
    route: str
    witness: SessionCardWitness

    def __post_init__(self):
        if type(self.selection) is not str or re.fullmatch(r"[0-9a-f]{64}", self.selection) is None:
            raise ValueError("Feedback requires an exact opaque Card source binding.")
        if self.route not in {"/sessions/cards", "/sessions/play"}:
            raise ValueError("Feedback belongs only to normal Session Card forms.")
        if type(self.witness) is not SessionCardWitness:
            raise ValueError("Feedback requires one exact immutable witness.")


def rejected_card_witness(facts, command, diagnostics, *, candidate_progress=False):
    """Use the original accepted projection only, after the real validator rejects.

    No replay, prose parsing, future knowledge, or candidate projection is used.
    An unsupported diagnostic remains the caller's existing safe fallback.
    """
    # Shared validation contracts also load during CLI help; keep Product imports lazy.
    from skatmind.session_commands import (
        RecordSessionDealtCardCommandV1,
        RecordSessionDiscardCommandV1,
        RecordSessionPlayCommandV1,
    )
    from skatmind.session_incremental_validation import _has_exact_playable_hand
    from skatmind.session_validation import SessionValidationDiagnosticV1

    if (len(diagnostics) != 1 or type(diagnostics[0]) is not SessionValidationDiagnosticV1
            or not diagnostics[0].blocks_command or diagnostics[0].path != "/command/card"
            or diagnostics[0].code not in {"card_identity_violation", "card_ownership_violation"}
            or type(command) not in {RecordSessionDealtCardCommandV1,
                RecordSessionDiscardCommandV1, RecordSessionPlayCommandV1}):
        return None
    card = command.card
    identity = diagnostics[0].code == "card_identity_violation"
    actor = (facts.declarer_player_id if type(command) is RecordSessionDiscardCommandV1
             else command.player_id)

    def seat(player_id):
        return None if player_id is None else facts.player_ids.index(player_id) + 1

    def witness(kind, **values):
        return SessionCardWitness(kind=kind, card=card, player=seat(actor), **values)

    if type(command) is RecordSessionDealtCardCommandV1 and identity:
        for owner, hand in facts.initial_known_hands:
            if card in hand:
                return witness("assigned_hand", owner=seat(owner))
        if card in facts.known_skat:
            return witness("assigned_skat")
    elif type(command) in {RecordSessionPlayCommandV1, RecordSessionDiscardCommandV1}:
        if identity:
            for index, (owner, played) in enumerate(facts.plays, 1):
                if card == played:
                    return witness("played", owner=seat(owner), play=index)
            if card in facts.discarded_cards:
                return witness("discarded")
            if (type(command) is RecordSessionPlayCommandV1 and facts.declaration is not None
                    and facts.declaration.hand_game and card in facts.known_skat):
                return witness("hand_skat")
        elif type(command) is RecordSessionDiscardCommandV1:
            initial = facts.initial_hand_for(actor)
            if (initial is not None and len(initial) == 10 and len(facts.known_skat) == 2
                    and card not in (*initial, *facts.known_skat)):
                return witness("discard_membership")
        else:
            # Current remaining ownership respects pickup, discards and accepted Plays.
            for kind, hands in (("owner_hand", facts.remaining_known_hands),
                                ("owner_public", facts.exact_public_hands)):
                for owner, hand in hands:
                    if owner != actor and card in hand:
                        return witness(kind, owner=seat(owner))
            exact = _has_exact_playable_hand(facts, actor)
            hand = facts.remaining_hand_for(actor) if exact else facts.public_hand_for(actor)
            if hand is not None:
                if card not in hand:
                    return witness("missing_hand" if exact else "missing_public")
                trick = facts.incomplete_trick
                if trick is not None and facts.declaration is not None:
                    cards = [played for _, played in trick.plays]
                    if card not in get_legal_cards(list(hand), cards, facts.declaration.game_type):
                        return witness("follow", play=(trick.trick_number - 1) * 3 + 1,
                            suit=get_effective_suit(cards[0], facts.declaration.game_type))
    return witness("batch") if candidate_progress else None


def render_card_witness(witness, players, locale):
    """Resolve full accepted labels at render time, outside generic 80-character arguments."""
    from .stateful_localization import card_name, player_name, text

    def name(index):
        return (text(locale, "task.skat") if index is None else
                player_name(locale, players, players[index - 1].player_id))

    values = {"card": card_name(locale, witness.card), "player": name(witness.player)}
    anchor = None
    kind = witness.kind
    if witness.owner is not None:
        values["owner"] = name(witness.owner)
    if kind in {"played", "follow"}:
        values["trick"] = (witness.play - 1) // 3 + 1
        anchor = f"session-play-{witness.play}"
        if kind == "played":
            values["position"] = (witness.play - 1) % 3 + 1
        else:
            values["suit"] = text(locale, "compact.trumps" if witness.suit == "TRUMP"
                                  else "task.card.suit." + witness.suit)
    elif kind in {"assigned_hand", "owner_hand"}:
        anchor = f"session-hand-{witness.owner}"
    elif kind == "owner_public":
        anchor = f"session-public-hand-{witness.owner}"
    elif kind in {"assigned_skat", "hand_skat"}:
        anchor = "session-skat"
    elif kind == "discarded":
        anchor = "session-discards"
    elif kind in {"missing_hand", "discard_membership"}:
        anchor = f"session-hand-{witness.player}"
    elif kind == "missing_public":
        anchor = f"session-public-hand-{witness.player}"
    return text(locale, "validation.session_card." + kind, **values), anchor
