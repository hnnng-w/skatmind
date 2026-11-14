"""Separate bounded revision journal with strict reconstruction and optimistic atomic save."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from .automatic_learning_codec import Record, canonical_json, decode_json, unique
from .automatic_learning_io import checked_root, read_bounded, sync_directory
from .event_context_contracts import EventContextV1, identity
from .event_context_operations import EventContextConflict, validate_event_revision_transition_v1
from .event_context_projection import PreparedEventContextV1, validate_frozen_context_v1

EVENT_CONTEXT_FILENAME = "event-contexts.json"
EVENT_CONTEXT_MAX_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True, kw_only=True)
class EventContextJournalV1(Record):
    revisions: tuple[EventContextV1, ...] = ()
    preparations: tuple[PreparedEventContextV1, ...] = ()
    version: int = 1

    def __post_init__(self):
        self.validate()
        if len(self.revisions) > 4096 or len(self.preparations) > 4096:
            raise ValueError("Event context history exceeds its private bound.")
        heads, revisions = {}, {}
        for context in self.revisions:
            validate_event_revision_transition_v1(heads.get(context.event_id), context)
            heads[context.event_id] = context
            revisions[context.fingerprint] = context
        unique(tuple(binding.source for context in heads.values() for binding in context.bindings))
        unique(tuple(item.fingerprint for item in self.preparations))
        acknowledgements = {}
        for prepared in self.preparations:
            context = revisions.get(prepared.context_fingerprint)
            if context is None:
                raise ValueError("Frozen context requires its exact retained context revision.")
            validate_frozen_context_v1(prepared, context)
            for item in prepared.disagreements:
                key = context.event_id, item.fingerprint
                acknowledgements[key] = min(context.revision,
                    acknowledgements.get(key, context.revision))
        for context in self.revisions:
            for checkpoint in context.checkpoints:
                acknowledgement = context.event_id, checkpoint.acknowledged_disagreement
                if (checkpoint.acknowledged_disagreement is not None
                        and acknowledgements.get(acknowledgement, context.revision)
                        >= context.revision):
                    raise ValueError(
                        "Reconfirmation requires the retained exact disagreement basis.")

    @property
    def fingerprint(self):
        return identity("journal", self.to_dict())

    @property
    def heads(self):
        latest = {context.event_id: context for context in self.revisions}
        return tuple(latest.values())

    def for_source(self, source):
        return next((context for context in self.heads
                     if context.binding(source) is not None), None)

    def context(self, event_id):
        return next((context for context in self.heads if context.event_id == event_id), None)


def append_event_revision_v1(journal, context, *, prepared=None):
    old = journal.context(context.event_id)
    if old == context and (prepared is None or prepared in journal.preparations):
        return journal
    preparations = journal.preparations
    if prepared is not None and prepared not in preparations:
        preparations += (prepared,)
    return replace(journal, revisions=journal.revisions + (() if old == context else (context,)),
                   preparations=preparations)


def event_context_bytes_v1(journal):
    journal.__post_init__()
    return canonical_json({"document_kind": "skatmind_event_context_journal", "version": 1,
        "content_fingerprint": journal.fingerprint, "journal": journal.to_dict()}) + b"\n"


def resume_event_context_v1(raw):
    data = decode_json(raw)
    if (set(data) != {"document_kind", "version", "content_fingerprint", "journal"}
            or data["document_kind"] != "skatmind_event_context_journal"
            or type(data["version"]) is not int or data["version"] != 1):
        raise ValueError("Unsupported event context persistence contract.")
    journal = EventContextJournalV1.from_dict(data["journal"])
    if journal.fingerprint != data["content_fingerprint"]:
        raise ValueError("Event context fingerprint differs from its retained content.")
    return journal


def load_event_context_v1(root: Path):
    checked_root(root)
    try:
        raw = read_bounded(root / EVENT_CONTEXT_FILENAME, EVENT_CONTEXT_MAX_BYTES)
    except FileNotFoundError:
        return EventContextJournalV1()
    return resume_event_context_v1(raw)


def save_event_context_v1(root, journal, *, expected_fingerprint, source_guard=lambda: True):
    """Append-only history; failure before replace preserves the original file."""
    checked_root(root)
    first = load_event_context_v1(root)
    if first.fingerprint != expected_fingerprint or not source_guard():
        raise EventContextConflict("Event context or recording changed; reload before saving.")
    if first == journal:
        return "unchanged"
    if (journal.revisions[:len(first.revisions)] != first.revisions
            or journal.preparations[:len(first.preparations)] != first.preparations):
        raise ValueError("Existing context revisions and frozen values are immutable.")
    raw = event_context_bytes_v1(journal)
    if len(raw) > EVENT_CONTEXT_MAX_BYTES:
        raise ValueError("Event context journal exceeds its byte bound.")
    descriptor, name = tempfile.mkstemp(prefix=".event-context-", suffix=".tmp", dir=root)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            view = memoryview(raw)
            while view:
                written = file.write(view)
                if type(written) is not int or written <= 0:
                    raise OSError("Incomplete event context write.")
                view = view[written:]
            file.flush()
            os.fsync(file.fileno())
        checked_root(root)
        if load_event_context_v1(root) != first or not source_guard():
            raise EventContextConflict("Event context or recording changed during save.")
        os.replace(temporary, root / EVENT_CONTEXT_FILENAME)
        sync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)
    return "saved"
