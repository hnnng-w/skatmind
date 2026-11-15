"""Chronological prefix projection and immutable, analysis-free preparation."""

from __future__ import annotations

from dataclasses import dataclass

from .automatic_learning_codec import Record, digest, integer, unique
from .event_context_contracts import (
    CheckpointV1,
    EventContextV1,
    EventTermsV1,
    RecordingKeyV1,
    RecordingVersionV1,
    bounded_text,
    identity,
    position,
)
from .event_context_reconciliation import (
    ReconciliationAliasV1,
    acknowledgement_matches,
    semantic_disagreement_fingerprint_v2,
    validate_v2_record,
)
from .fixed_three_player_list_contribution import build_fixed_three_player_list_contributions

ESTABLISHED = ("passed", "settled")
POSITION_STATUSES = (*ESTABLISHED, "missing", "unfinished", "unsettled", "source_unavailable",
                     "source_conflict")


@dataclass(frozen=True, slots=True, kw_only=True)
class OutcomeFactV1(Record):
    """Minimal established Product facts; unknown outcomes carry no invented score."""

    position: int
    status: str
    declarer_id: str | None = None
    outcome: str | None = None
    settlement_score: int | None = None
    evidence_fingerprint: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        position(self.position)
        if self.status not in POSITION_STATUSES:
            raise ValueError("Unsupported position evidence status.")
        if self.status == "settled":
            bounded_text(self.declarer_id)
            digest(self.evidence_fingerprint)
            if (self.outcome not in ("declarer_win", "declarer_loss")
                    or type(self.settlement_score) is not int
                    or (self.settlement_score > 0) != (self.outcome == "declarer_win")
                    or self.settlement_score == 0):
                raise ValueError("Settled evidence requires a signed established outcome.")
        elif any(value is not None for value in (self.declarer_id, self.outcome,
                 self.settlement_score, self.evidence_fingerprint)):
            raise ValueError("Unestablished/passed positions cannot claim settlement facts.")


@dataclass(frozen=True, slots=True, kw_only=True)
class DecisionCutoffV1(Record):
    position: int
    decision_index: int
    actor_id: str
    game_id: str | None = None
    version: int = 1

    def __post_init__(self):
        self.validate()
        position(self.position)
        position(self.decision_index, end=30)
        bounded_text(self.actor_id)
        if self.game_id is not None:
            bounded_text(self.game_id)


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclarationFactV1(Record):
    name: str
    value: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        if self.name not in ("declarer_seat", "game_type", "hand_game", "ouvert", "matadors",
                             "bid_value", "schneider_announced", "schwarz_announced"):
            raise ValueError("Unsupported accounting declaration fact.")
        bounded_text(self.value)


@dataclass(frozen=True, slots=True, kw_only=True)
class GameSignatureV1(Record):
    """Comparison-only known declarations and trace-prefix hashes, never hidden hands."""

    position: int
    declaration: tuple[DeclarationFactV1, ...]
    trace_prefixes: tuple[str, ...]
    version: int = 1

    def __post_init__(self):
        self.validate()
        position(self.position)
        unique(tuple(item.name for item in self.declaration))
        if len(self.trace_prefixes) > 30:
            raise ValueError("A source trace has at most 30 Plays.")
        for value in self.trace_prefixes:
            digest(value)


def signatures_conflict(signatures):
    for index, first in enumerate(signatures):
        left = {item.name: item.value for item in first.declaration}
        for second in signatures[index + 1:]:
            right = {item.name: item.value for item in second.declaration}
            if any(left[key] != right[key] for key in left.keys() & right.keys()):
                return True
            common = min(len(first.trace_prefixes), len(second.trace_prefixes))
            if common and first.trace_prefixes[common - 1] != second.trace_prefixes[common - 1]:
                return True
    return False


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordingFactsV1(Record):
    source: RecordingVersionV1
    player_ids: tuple[str, ...]
    selected_player_id: str | None
    outcomes: tuple[OutcomeFactV1, ...]
    decisions: tuple[DecisionCutoffV1, ...] = ()
    signatures: tuple[GameSignatureV1, ...] = ()
    version: int = 1

    def __post_init__(self):
        self.validate()
        unique(self.player_ids)
        if len(self.player_ids) != 3:
            raise ValueError("Recording evidence requires three actual players.")
        for player in self.player_ids:
            bounded_text(player)
        if self.selected_player_id is not None and self.selected_player_id not in self.player_ids:
            raise ValueError("Selected recording player is absent.")
        unique(tuple(item.position for item in self.outcomes))
        unique(tuple((item.position, item.decision_index) for item in self.decisions))
        unique(tuple(item.position for item in self.signatures))
        if any(item.declarer_id not in self.player_ids for item in self.outcomes
               if item.status == "settled") or any(item.actor_id not in self.player_ids
                                                   for item in self.decisions):
            raise ValueError("Evidence actor/declarer must be an actual source player.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PositionBasisV1(Record):
    fact: OutcomeFactV1
    sources: tuple[RecordingVersionV1, ...]
    signatures: tuple[GameSignatureV1, ...] = ()
    version: int = 1

    def __post_init__(self):
        self.validate()
        unique(tuple(source.source for source in self.sources))
        if self.fact.status in ESTABLISHED and not self.sources:
            raise ValueError("Established contributions require exact source versions.")
        if any(item.position != self.fact.position for item in self.signatures):
            raise ValueError("Comparison signatures must belong to this exact position.")
        if signatures_conflict(self.signatures) and self.fact.status != "source_conflict":
            raise ValueError("Contradictory source facts must not yield a contribution.")

    def contribution(self, context):
        if self.fact.status not in ESTABLISHED:
            return None
        fact = self.fact
        rows = build_fixed_three_player_list_contributions(
            player_ids=context.participant_ids,
            entry_outcome="passed_deal" if fact.status == "passed" else fact.outcome,
            declarer_player_id=fact.declarer_id, settlement_score=fact.settlement_score)
        selected = next(row for row in rows if row.player_id == context.selected_participant_id)
        return selected.total_performance_points, selected.own_games_lost


@dataclass(frozen=True, slots=True, kw_only=True)
class DisagreementV1(Record):
    checkpoint: CheckpointV1
    start_checkpoint: CheckpointV1 | None
    basis: tuple[PositionBasisV1, ...]
    derived_points: int
    derived_losses: int
    version: int = 1

    def __post_init__(self):
        self.validate()
        integer(self.derived_losses)
        start = 0 if self.start_checkpoint is None else self.start_checkpoint.through_position
        if (tuple(item.fact.position for item in self.basis)
                != tuple(range(start + 1, self.checkpoint.through_position + 1))
                or any(item.fact.status not in ESTABLISHED for item in self.basis)):
            raise ValueError("A disagreement requires complete established comparison coverage.")
        if (self.derived_points, self.derived_losses) == (
                self.checkpoint.personal_points, self.checkpoint.own_losses):
            raise ValueError("Equal cumulative anchors do not disagree.")

    @property
    def fingerprint(self):
        # Exclude acknowledgement so explicitly reconfirmed facts can match the same basis.
        value = self.to_dict()
        value["checkpoint"]["acknowledged_disagreement"] = None
        if value["start_checkpoint"] is not None:
            value["start_checkpoint"]["acknowledged_disagreement"] = None
        return identity("disagreement", value)


def bind_recording_facts(context, recordings, *, through_position):
    """Map exact identities and resolve each event position once; never sum surfaces."""
    unique(tuple(recording.source.source for recording in recordings))
    records = {recording.source.source: recording for recording in recordings}
    candidates = {number: [] for number in range(1, through_position + 1)}
    for binding in context.bindings:
        recording = records.get(binding.source)
        positions = (range(1, through_position + 1) if binding.source.family == "match"
                     else (binding.game_position,) if binding.game_position <= through_position
                     else ())
        if recording is not None:
            if (recording.player_ids != tuple(item.source_player_id for item in binding.players)
                    or recording.selected_player_id != binding.source_selected_player_id):
                raise ValueError("Recording participant binding changed.")
        for number in positions:
            from dataclasses import replace

            original = None if recording is None else next((item for item in recording.outcomes
                if item.position == (number if binding.source.family == "match" else 1)), None)
            signature = None if recording is None else next((item for item in recording.signatures
                if item.position == (number if binding.source.family == "match" else 1)), None)
            if signature is not None:
                signature = replace(signature, position=number)
            if original is None:
                fact = OutcomeFactV1(position=number, status="source_unavailable")
            else:
                fact = replace(original, position=number, declarer_id=(
                    None if original.declarer_id is None else binding.player(original.declarer_id)))
            candidates[number].append((fact, None if recording is None else recording.source,
                                       signature))
    result = []
    for number, values in candidates.items():
        sources = tuple(source for _, source, _ in values if source is not None)
        signatures = tuple(signature for _, _, signature in values if signature is not None)
        actual = [fact for fact, _, _ in values if fact.status != "missing"]
        if signatures_conflict(signatures):
            fact = OutcomeFactV1(position=number, status="source_conflict")
        elif any(fact.status == "source_unavailable" for fact in actual):
            fact = OutcomeFactV1(position=number, status="source_unavailable")
        elif not actual:
            fact = OutcomeFactV1(position=number, status="missing")
        elif any(fact.status == "passed" for fact in actual) and any(
                fact.status != "passed" for fact in actual):
            fact = OutcomeFactV1(position=number, status="source_conflict")
        else:
            established = [fact for fact in actual if fact.status in ESTABLISHED]
            if len(set(established)) > 1:
                fact = OutcomeFactV1(position=number, status="source_conflict")
            elif established:
                fact = established[0]
            else:
                fact = OutcomeFactV1(position=number, status=("unsettled" if any(
                    row.status == "unsettled" for row in actual) else "unfinished"))
        result.append(PositionBasisV1(fact=fact, sources=sources,
            signatures=signatures if len(signatures) > 1 else ()))
    return tuple(result)


def compare_checkpoints(context, basis, *, before_position):
    """Compare cumulative anchors only where the complete intervening basis exists."""
    eligible = tuple(c for c in context.checkpoints if c.through_position < before_position)
    disagreements = []
    previous = None
    for checkpoint in eligible:
        start = 0 if previous is None else previous.through_position
        rows = tuple(row for row in basis
                     if start < row.fact.position <= checkpoint.through_position)
        if (len(rows) == checkpoint.through_position - start
                and all(row.fact.status in ESTABLISHED for row in rows)):
            points = 0 if previous is None else previous.personal_points
            losses = 0 if previous is None else previous.own_losses
            for row in rows:
                delta, loss = row.contribution(context)
                points += delta
                losses += loss
            if (points, losses) != (checkpoint.personal_points, checkpoint.own_losses):
                disagreements.append(DisagreementV1(checkpoint=checkpoint,
                    start_checkpoint=previous, basis=rows, derived_points=points,
                    derived_losses=losses))
        previous = checkpoint
    return tuple(disagreements)


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedEventContextV1(Record):
    event_id: str
    context_revision: int
    context_fingerprint: str
    target_source: RecordingVersionV1 | None
    target_key: RecordingKeyV1
    game_position: int
    decision_index: int | None
    actor_id: str | None
    target_game_id: str | None
    selected_participant_id: str
    terms: EventTermsV1
    checkpoint: CheckpointV1 | None
    basis: tuple[PositionBasisV1, ...]
    disagreements: tuple[DisagreementV1, ...]
    status: str
    personal_points: int | None
    own_losses: int | None
    established_through: int
    remaining_including_current: int | None
    version: int = 1

    def __post_init__(self):
        self.validate()
        bounded_text(self.event_id)
        digest(self.context_fingerprint)
        integer(self.context_revision)
        position(self.game_position, end=37)
        position(self.established_through, zero=True)
        bounded_text(self.selected_participant_id)
        if self.decision_index is not None:
            position(self.game_position)
            position(self.decision_index, end=30)
            if self.actor_id is not None:
                bounded_text(self.actor_id)
        elif self.actor_id is not None:
            raise ValueError("An actor requires an exact decision cutoff.")
        if self.target_game_id is not None:
            bounded_text(self.target_game_id)
        if self.status not in ("ready", "incomplete", "conflict", "source_unavailable",
                               "decision_unavailable", "not_applicable"):
            raise ValueError("Unsupported context preparation status.")
        if self.target_source is not None and self.target_source.source != self.target_key:
            raise ValueError("Prepared target source identity differs.")
        if self.checkpoint is not None and self.checkpoint.through_position >= self.game_position:
            raise ValueError("A decision cannot consume a current or later checkpoint.")
        if tuple(row.fact.position for row in self.basis) != tuple(range(1, self.game_position)):
            raise ValueError("Prepared basis must cover exactly the earlier prefix.")
        if any(item.checkpoint.through_position >= self.game_position
               for item in self.disagreements):
            raise ValueError("Later disagreement evidence cannot enter a preparation.")

    @property
    def fingerprint(self):
        return identity("prepared", self.to_dict())

    def disagreement_identity(self, disagreement):
        return disagreement.fingerprint

    def acknowledges(self, disagreement):
        return disagreement.checkpoint.acknowledged_disagreement == disagreement.fingerprint

    @property
    def financial_missing(self):
        return self.terms.financial.missing + (("cent_tariff",) if self.terms.mode != "tournament"
            and self.terms.financial.cent_tariff is None else ())

    @property
    def unresolved(self):
        start = 0 if self.checkpoint is None else self.checkpoint.through_position
        return tuple(row for row in self.basis if row.fact.status == "source_conflict"
                     or row.fact.position > start and row.fact.status not in ESTABLISHED)


@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedEventContextV2(PreparedEventContextV1):
    reconciliation_identities: tuple[str, ...]
    acknowledgement_aliases: tuple[ReconciliationAliasV1, ...] = ()
    version: int = 2

    def validate(self):
        validate_v2_record(self)

    def __post_init__(self):
        PreparedEventContextV1.__post_init__(self)
        if len(self.reconciliation_identities) != len(self.disagreements):
            raise ValueError("Each disagreement requires one semantic comparison identity.")
        for value in self.reconciliation_identities:
            digest(value)
        unique(self.acknowledgement_aliases)

    @property
    def fingerprint(self):
        return identity("prepared_v2", self.to_dict())

    def disagreement_identity(self, disagreement):
        return self.reconciliation_identities[self.disagreements.index(disagreement)]

    def acknowledges(self, disagreement):
        return acknowledgement_matches(disagreement, self.disagreement_identity(disagreement),
                                        self.acknowledgement_aliases)


def prepare_event_context_v1(context, recordings, *, target, game_position, decision_index=None,
                              expected_source=None, acknowledgement_aliases=()):
    """Freeze only explicit applicable facts and the prefix ending before game g.

    No financial or Card calculation is invoked. Context-only capture does not
    claim that the existing Card recommendation consumed these values.
    """
    if type(context) is not EventContextV1:
        raise ValueError("Expected an exact versioned event context.")
    context.__post_init__()
    position(game_position, end=(37 if decision_index is None else 36)
             if context.tournament else 3)
    binding = context.binding(target)
    if binding is None or (target.family == "session" and binding.game_position != game_position):
        raise ValueError("The target recording/game is not explicitly attached to this event.")
    if expected_source is not None:
        if type(expected_source) is not RecordingVersionV1 or expected_source.source != target:
            raise ValueError("The requested original version must identify the exact target.")
        recordings = tuple(item for item in recordings if item.source.source != target
                           or item.source == expected_source)
    recording = next((item for item in recordings if item.source.source == target), None)
    if recording is not None and (recording.player_ids
            != tuple(item.source_player_id for item in binding.players)
            or recording.selected_player_id != binding.source_selected_player_id):
        raise ValueError("The target participant binding changed.")
    actor = game_id = None
    if decision_index is not None:
        position(decision_index, end=30)
        decision = None if recording is None else next((item for item in recording.decisions
            if item.position == (game_position if target.family == "match" else 1)
            and item.decision_index == decision_index), None)
        actor = None if decision is None else binding.player(decision.actor_id)
        game_id = None if decision is None else decision.game_id
    basis = bind_recording_facts(context, recordings, through_position=game_position - 1)
    return _prepare_from_basis(context, basis, target=target,
        target_source=None if recording is None else recording.source, game_position=game_position,
        decision_index=decision_index, actor=actor, game_id=game_id, preparation_version=2,
        acknowledgement_aliases=acknowledgement_aliases)


def _prepare_from_basis(context, basis, *, target, target_source, game_position,
                        decision_index, actor, game_id, preparation_version=1,
                        acknowledgement_aliases=()):
    checkpoint = next((item for item in reversed(context.checkpoints)
                       if item.through_position < game_position), None)
    disagreements = compare_checkpoints(context, basis, before_position=game_position)
    semantic = tuple(semantic_disagreement_fingerprint_v2(context, item)
                     for item in disagreements) if preparation_version == 2 else ()
    aliases = tuple(sorted(set(alias for alias in acknowledgement_aliases
        if any(alias.legacy_fingerprint == item.checkpoint.acknowledged_disagreement
               and alias.semantic_fingerprint == semantic[index]
               for index, item in enumerate(disagreements))),
        key=lambda alias: (alias.legacy_fingerprint, alias.semantic_fingerprint)))
    start = 0 if checkpoint is None else checkpoint.through_position
    points = 0 if checkpoint is None else checkpoint.personal_points
    losses = 0 if checkpoint is None else checkpoint.own_losses
    through = start
    for row in basis[start:]:
        contribution = row.contribution(context) if context.tournament else None
        if contribution is None:
            break
        points += contribution[0]
        losses += contribution[1]
        through = row.fact.position
    status = "ready" if through == game_position - 1 else "incomplete"
    if any(not acknowledgement_matches(item, semantic[index], aliases)
           if preparation_version == 2 else
           item.checkpoint.acknowledged_disagreement != item.fingerprint
           for index, item in enumerate(disagreements)):
        status = "conflict"
    if any(row.fact.status == "source_conflict" for row in basis):
        status = "conflict"
    if not context.tournament:
        status, points, losses, through = "not_applicable", None, None, 0
    if target_source is None:
        status = "source_unavailable"
    elif decision_index is not None and actor is None:
        status = "decision_unavailable"
    prepared_type = PreparedEventContextV2 if preparation_version == 2 else PreparedEventContextV1
    extra = dict(reconciliation_identities=semantic, acknowledgement_aliases=aliases)
    return prepared_type(event_id=context.event_id, context_revision=context.revision,
        context_fingerprint=context.fingerprint, target_source=target_source,
        target_key=target, game_position=game_position,
        decision_index=decision_index, actor_id=actor, target_game_id=game_id,
        selected_participant_id=context.selected_participant_id,
        terms=context.applicable_terms(game_position), checkpoint=checkpoint, basis=basis,
        disagreements=disagreements, status=status, personal_points=points, own_losses=losses,
        established_through=through,
        remaining_including_current=37 - game_position if context.tournament else None,
        **(extra if preparation_version == 2 else {}))


def validate_frozen_context_v1(prepared, context):
    """Reconstruct exact consumed arithmetic from retained facts, not today's recording."""
    binding = context.binding(prepared.target_key)
    if (binding is None or context.fingerprint != prepared.context_fingerprint
            or binding.game_position is not None and binding.game_position != prepared.game_position
            or prepared.actor_id is not None and prepared.actor_id not in context.participant_ids):
        raise ValueError("Frozen context does not match its retained event/source binding.")
    for row in prepared.basis:
        for source in row.sources:
            bound = context.binding(source.source)
            if bound is None or (bound.game_position is not None
                                and bound.game_position != row.fact.position):
                raise ValueError("Frozen contribution source is outside its event position.")
        if row.fact.declarer_id is not None and row.fact.declarer_id not in context.participant_ids:
            raise ValueError("Frozen declarer is outside the event participant set.")
    expected = _prepare_from_basis(context, prepared.basis, target=prepared.target_key,
        target_source=prepared.target_source, game_position=prepared.game_position,
        decision_index=prepared.decision_index, actor=prepared.actor_id,
        game_id=prepared.target_game_id, preparation_version=prepared.version,
        acknowledgement_aliases=getattr(prepared, "acknowledgement_aliases", ()))
    if expected != prepared:
        raise ValueError("Frozen context differs from its exact retained basis.")


def preparation_is_current_v1(prepared, context, recordings):
    """Exact fresh reproduction, never authorization by a historical fingerprint alone."""
    if context.fingerprint != prepared.context_fingerprint:
        return False
    return prepared == prepare_event_context_v1(context, recordings, target=prepared.target_key,
        game_position=prepared.game_position, decision_index=prepared.decision_index,
        acknowledgement_aliases=getattr(prepared, "acknowledgement_aliases", ()))
