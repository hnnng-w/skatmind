"""Version-2 comparison identity, separate from exact source/save authorization."""

from dataclasses import dataclass
from typing import get_type_hints

from .automatic_learning_codec import Record, _convert, digest
from .event_context_contracts import identity


def validate_v2_record(value):
    """Reuse exact field conversion without changing the shared version-1 codec."""
    for name, annotation in get_type_hints(type(value)).items():
        _convert(annotation, getattr(value, name), decode=False)
    if type(value.version) is not int or value.version != 2:
        raise ValueError("Unsupported event context version-2 record.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReconciliationAliasV1(Record):
    legacy_fingerprint: str
    semantic_fingerprint: str
    version: int = 1

    def __post_init__(self):
        self.validate()
        digest(self.legacy_fingerprint)
        digest(self.semantic_fingerprint)


def semantic_disagreement_fingerprint_v2(context, disagreement):
    """Only the compared prefix, checkpoint and relevant identity/scoring bindings.

    Source revisions/content fingerprints remain in the retained basis and in
    freshness checks. They are not the identity of an unchanged historical fact.
    """
    value = disagreement.to_dict()
    value["checkpoint"]["acknowledged_disagreement"] = None
    if value["start_checkpoint"] is not None:
        value["start_checkpoint"]["acknowledged_disagreement"] = None
    bindings = []
    for row, stored in zip(disagreement.basis, value["basis"], strict=True):
        stored["sources"] = [dict(source=source.source.to_dict(),
            contract_version=source.contract_version) for source in row.sources]
        for source in row.sources:
            binding = context.binding(source.source)
            if binding is None:
                raise ValueError("Comparison source has no event binding.")
            fact = dict(source=source.source.to_dict(), game_position=binding.game_position,
                        players=[player.to_dict() for player in binding.players],
                        selected=binding.source_selected_player_id)
            if fact not in bindings:
                bindings.append(fact)
    return identity("disagreement_semantic_v2", dict(comparison=value, bindings=bindings,
        event_id=context.event_id, series_id=context.series_id,
        participant_ids=list(context.participant_ids), selected=context.selected_participant_id,
        scoring=[dict(position=row.fact.position,
            rule=context.applicable_terms(row.fact.position).scoring_rule,
            source=context.applicable_terms(row.fact.position).scoring_source.to_dict())
            for row in disagreement.basis]))


def acknowledgement_matches(disagreement, comparison_identity, aliases=()):
    acknowledged = disagreement.checkpoint.acknowledged_disagreement
    return (acknowledged == comparison_identity
            or any(alias.legacy_fingerprint == acknowledged
                   and alias.semantic_fingerprint == comparison_identity for alias in aliases))
