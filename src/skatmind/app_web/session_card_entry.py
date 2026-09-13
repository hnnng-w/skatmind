"""Read-only Card tasks and immutable composition of ordinary Session Commands."""

from __future__ import annotations

from dataclasses import dataclass

import skatmind.api.v1.session as session_api
from skatmind.deck import get_full_deck
from skatmind.rules import get_legal_cards
from skatmind.session_incremental_validation import (
    _has_exact_playable_hand,
    _unplayable_cards,
    _validate_card_owner_conflicts,
)

from .session_frontend import (
    _collect_current_checkpoint,
    default_session_position_export_options_v1,
)
from .task_first_projections import project_task_first_session_v1


class CardEntryError(ValueError):
    def __init__(self, reason: str, field_key: str = "cards") -> None:
        super().__init__("The Card entry was rejected.")
        self.reason = reason
        self.field_key = field_key


@dataclass(frozen=True, slots=True)
class SessionCardTask:
    kind: str
    destination: str
    player_id: str | None
    capacity: int
    accepted_cards: tuple[str, ...]
    selectable_cards: tuple[str, ...]
    scope: str


def project_session_card_task(state, *, view=None) -> SessionCardTask | None:
    view = view or project_task_first_session_v1(state)
    facts = view.facts
    kind = view.workflow.primary_action
    deck = tuple(get_full_deck())
    if kind == "record_dealt_card":
        destination = view.deal_destination
        player = view.entry_player_id if destination == "player_hand" else None
        accepted = (facts.initial_hand_for(player) or ()
                    if destination == "player_hand" else facts.known_skat)
        capacity = (10 if destination == "player_hand" else 2) - len(accepted)
        assigned = {card for _, hand in facts.initial_known_hands for card in hand}
        assigned.update(facts.known_skat)
        cards = tuple(card for card in deck if card not in assigned)
        return SessionCardTask(kind, destination, player, capacity, accepted, cards, "append")
    if kind == "record_discard":
        accepted = facts.discarded_cards
        cards = tuple(card for card in deck if card in {
            *(facts.initial_hand_for(facts.declarer_player_id) or ()), *facts.known_skat,
        } and card not in accepted)
        return SessionCardTask(kind, "discard", facts.declarer_player_id,
                               2 - len(accepted), accepted, cards, "append")
    if kind != "record_play" or facts.next_player_id is None or facts.declaration is None:
        return None
    actor = facts.next_player_id
    hand = (facts.remaining_hand_for(actor) if _has_exact_playable_hand(facts, actor)
            else facts.public_hand_for(actor))
    unavailable = _unplayable_cards(facts) | {card for _, card in facts.plays}
    candidates = tuple(card for card in deck if card not in unavailable
        and _validate_card_owner_conflicts(facts, player_id=actor, card=card,
                                           require_owner_membership=False) is None)
    if hand is not None:
        trick = ([] if facts.incomplete_trick is None
                 else [card for _, card in facts.incomplete_trick.plays])
        legal = get_legal_cards(list(hand), trick, facts.declaration.game_type)
        candidates = tuple(card for card in candidates if card in legal)
    return SessionCardTask(kind, "play", actor, 1, (), candidates,
                           "exact_legal_cards" if hand is not None
                           else "bounded_observation_candidates")


def validate_card_selection(cards, *, capacity: int, field_key="cards") -> tuple[str, ...]:
    """Validate before canonicalizing; duplicate input never becomes a valid set."""
    if type(cards) not in {tuple, list} or any(type(card) is not str for card in cards):
        raise CardEntryError("invalid", field_key)
    if not cards:
        raise CardEntryError("empty", field_key)
    if len(cards) > capacity:
        raise CardEntryError("capacity", field_key)
    if any(card not in get_full_deck() for card in cards):
        raise CardEntryError("invalid", field_key)
    if len(set(cards)) != len(cards):
        raise CardEntryError("duplicate", field_key)
    return tuple(card for card in get_full_deck() if card in cards)


@dataclass(frozen=True, slots=True)
class SessionCardCandidate:
    state: session_api.SessionStateV1
    checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...]


def prepare_session_card_candidate(
    state, checkpoints, cards, *, task: SessionCardTask, export_options=None,
) -> SessionCardCandidate:
    """N ordinary revisions, including intermediate Checkpoints, with no publication/I/O."""
    if task != project_session_card_task(state):
        raise CardEntryError("task")
    ordered = validate_card_selection(cards, capacity=task.capacity)
    options = export_options or default_session_position_export_options_v1()
    for card in ordered:
        checkpoints = _collect_current_checkpoint(
            state=state, checkpoints=checkpoints, export_options=options)
        if task.kind == "record_dealt_card":
            command = session_api.RecordSessionDealtCardCommandV1(
                expected_revision=state.revision, destination=task.destination,
                player_id=task.player_id, card=card)
        elif task.kind == "record_discard":
            command = session_api.RecordSessionDiscardCommandV1(
                expected_revision=state.revision, card=card)
        elif task.kind == "record_play":
            command = session_api.RecordSessionPlayCommandV1(
                expected_revision=state.revision, player_id=task.player_id, card=card)
        else:
            raise CardEntryError("task")
        result = session_api.apply_session_command(state, command).value
        if result.status != "applied":
            reason = {
                "card_identity_violation": "unavailable",
                "card_ownership_violation": "ownership",
                "information_policy_violation": "permission",
                "phase_violation": "task",
                "missing_required_value": "task",
            }.get(result.diagnostics[0].code, "task")
            raise CardEntryError(reason)
        state = result.state
        checkpoints = _collect_current_checkpoint(
            state=state, checkpoints=checkpoints, export_options=options)
    return SessionCardCandidate(state, checkpoints)
