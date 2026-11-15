"""Explicit context revisions; no source writes, automatic backfill or default lookup."""

from dataclasses import replace

from .event_context_contracts import CheckpointV1, EventContextV1, EventTermsV1


class EventContextConflict(ValueError):
    """A stale context/source requires explicit reload and review."""


def revise_event_context_v1(context, *, expected_revision, change, provenance, **updates):
    if context.revision != expected_revision:
        raise EventContextConflict("Event context revision changed.")
    if set(updates) - {"event_name", "series_name", "terms", "checkpoints", "bindings"}:
        raise ValueError("Event/series/participant identities are immutable.")
    if all(getattr(context, name) == value for name, value in updates.items()):
        return context
    return replace(context, revision=context.revision + 1, change=change,
                   provenance=provenance, **updates)


def set_event_checkpoint_v1(context, checkpoint, *, expected_revision):
    if type(checkpoint) is not CheckpointV1 or checkpoint.acknowledged_disagreement is not None:
        raise ValueError("Use explicit reconciliation to acknowledge a disagreement.")
    checkpoints = tuple(sorted((*[c for c in context.checkpoints
        if c.through_position != checkpoint.through_position], checkpoint),
        key=lambda item: item.through_position))
    return revise_event_context_v1(context, expected_revision=expected_revision,
        change="checkpoint", provenance=checkpoint.provenance, checkpoints=checkpoints)


def set_event_terms_v1(context, terms, *, expected_revision, correction, provenance,
                       event_name=None, series_name=None):
    if type(terms) is not EventTermsV1:
        raise ValueError("Expected exact event terms.")
    existing = next((term for term in context.terms
                     if term.from_position == terms.from_position), None)
    if correction:
        if existing is None:
            raise ValueError(
                "A factual correction must identify an existing applicability boundary.")
    elif existing is not None or terms.from_position <= context.terms[-1].from_position:
        raise ValueError("A later terms change requires a new later applicability boundary.")
    values = tuple(sorted((*[term for term in context.terms
        if term.from_position != terms.from_position], terms), key=lambda term: term.from_position))
    return revise_event_context_v1(context, expected_revision=expected_revision,
        change="terms_correction" if correction else "terms_change", provenance=provenance,
        terms=values, event_name=context.event_name if event_name is None else event_name,
        series_name=context.series_name if series_name is None else series_name)


def reconfirm_event_checkpoint_v1(context, prepared, *, through_position, expected_revision,
                                  provenance):
    if prepared.context_fingerprint != context.fingerprint:
        raise EventContextConflict("Reconciliation context changed.")
    disagreement = next((item for item in prepared.disagreements
                         if item.checkpoint.through_position == through_position), None)
    if disagreement is None:
        raise ValueError("There is no complete established disagreement to reconfirm.")
    checkpoints = tuple(replace(item,
        acknowledged_disagreement=prepared.disagreement_identity(disagreement))
        if item.through_position == through_position else item for item in context.checkpoints)
    return revise_event_context_v1(context, expected_revision=expected_revision,
        change="reconciliation", provenance=provenance, checkpoints=checkpoints)


def validate_event_revision_transition_v1(previous, current):
    if type(current) is not EventContextV1:
        raise ValueError("Expected an exact context revision.")
    if previous is None:
        if current.revision != 0 or current.change != "created":
            raise ValueError("Event history must start with creation at revision zero.")
        return
    stable = ("event_id", "series_id", "participant_ids", "selected_participant_id", "tournament")
    if (current.revision != previous.revision + 1 or current.change == "created"
            or any(getattr(previous, name) != getattr(current, name) for name in stable)):
        raise ValueError("Event revision changed immutable identity or skipped history.")
    if current.terms != previous.terms:
        old = {term.from_position: term for term in previous.terms}
        new = {term.from_position: term for term in current.terms}
        if current.change == "terms_correction":
            if old.keys() != new.keys() or sum(old[key] != new[key] for key in old) != 1:
                raise ValueError("A factual correction replaces one explicit terms boundary.")
        elif current.change == "terms_change":
            if (current.terms[:-1] != previous.terms
                    or current.terms[-1].from_position <= previous.terms[-1].from_position):
                raise ValueError("A later terms change must preserve earlier applicability.")
        else:
            raise ValueError("Terms require an explicit correction or later-change revision.")
    if current.bindings != previous.bindings and current.change != "attachment":
        raise ValueError("Binding changes require an explicit attachment revision.")
    if current.checkpoints != previous.checkpoints and current.change not in (
            "checkpoint", "checkpoint_removed", "reconciliation"):
        raise ValueError("Checkpoint changes require their own explicit revision.")
    old_checkpoints = {item.through_position: item for item in previous.checkpoints}
    for checkpoint in current.checkpoints:
        old = old_checkpoints.get(checkpoint.through_position)
        if checkpoint.acknowledged_disagreement is not None and (
                old is None
                or old.acknowledged_disagreement != checkpoint.acknowledged_disagreement):
            if (current.change != "reconciliation" or old is None
                    or replace(checkpoint, acknowledged_disagreement=old.acknowledged_disagreement)
                    != old):
                raise ValueError(
                    "Reconfirmation may acknowledge only the unchanged supplied anchor.")
