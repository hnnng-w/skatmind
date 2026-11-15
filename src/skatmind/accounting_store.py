"""Private bounded append-only accounting history; explicit optimistic atomic writes."""

from __future__ import annotations

import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from .accounting_state import CentRoundV1, TournamentAccountingV1, revise_accounting
from .automatic_learning_codec import Record, canonical_json, decode_json
from .automatic_learning_io import checked_root, read_bounded, sync_directory
from .mode_accounting import accounting_identity

ACCOUNTING_FILENAME = "mode-accounting.json"
MAX_BYTES = 16 * 1024 * 1024
# Both frontend families enter with their own lifecycle/active locks already held.
# This process-local barrier is always innermost: guards read sources without
# acquiring another family's lifecycle/active lock. Never enter it before those locks.
_PUBLICATION_LOCK = threading.Lock()


class AccountingConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountingJournalV1(Record):
    tournaments: tuple[TournamentAccountingV1, ...] = ()
    rounds: tuple[CentRoundV1, ...] = ()
    version: int = 1

    def __post_init__(self):
        self.validate()
        if len(self.tournaments) + len(self.rounds) > 4096:
            raise ValueError("Accounting history exceeds its private bound.")
        owners = {}
        for history in (self.tournaments, self.rounds):
            heads = {}
            for row in history:
                old = heads.get(row.identity)
                if row.revision != (0 if old is None else old.revision + 1):
                    raise ValueError("Accounting revisions must be linear and complete.")
                if old is not None:
                    if (row.context.series_id, row.context.participant_ids,
                            row.context.selected_participant_id) != (
                            old.context.series_id, old.context.participant_ids,
                            old.context.selected_participant_id):
                        raise ValueError("Participant or series changes require a new identity.")
                    if type(row) is CentRoundV1 and (row.table_id, row.previous_round_id) != (
                            old.table_id, old.previous_round_id):
                        raise ValueError("Round lineage cannot change.")
                # Historical source ownership is retained even after a correction.
                for binding in row.context.bindings:
                    prior = owners.setdefault(binding.source, row.identity)
                    if prior != row.identity:
                        raise ValueError("A recording cannot be posted into independent accounts.")
                heads[row.identity] = row
        rounds = {row.identity: row for row in self.round_heads}
        activities = {(row.identity, row.activity_fingerprint) for row in self.rounds}
        covered = set()
        for row in self.round_heads:
            if row.previous_round_id is not None:
                previous = rounds.get(row.previous_round_id)
                if previous is None or previous.identity == row.identity:
                    raise ValueError("A next round needs its retained predecessor.")
                if previous.table_id == row.table_id and (
                        previous.context.participant_ids != row.context.participant_ids or
                        previous.context.selected_participant_id !=
                        row.context.selected_participant_id):
                    raise ValueError("A changed table composition requires a distinct table.")
            confirmation = row.net_confirmation
            if confirmation is not None:
                for identity, fingerprint in zip(confirmation.round_ids,
                        confirmation.activity_fingerprints, strict=True):
                    target = rounds.get(identity)
                    if target is None or target.table_id != row.table_id or identity in covered:
                        raise ValueError("Net confirmations cannot overlap or cross tables.")
                    if (target.context.selected_participant_id !=
                            row.context.selected_participant_id):
                        raise ValueError("A net confirmation covers one actual participant.")
                    covered.add(identity)
                    if (identity, fingerprint) not in activities:
                        raise ValueError("Aggregate net requires its exact retained activity.")

    @property
    def fingerprint(self):
        return accounting_identity("journal", self.to_dict())

    @property
    def round_heads(self):
        return tuple({row.identity: row for row in self.rounds}.values())

    @property
    def tournament_heads(self):
        return tuple({row.identity: row for row in self.tournaments}.values())

    def head(self, identity):
        return next((row for row in (*self.round_heads, *self.tournament_heads)
                     if row.identity == identity), None)

    def for_source(self, source):
        return next((row for row in (*self.round_heads, *self.tournament_heads)
                     if row.context.binding(source) is not None), None)


def append_accounting(journal, candidate):
    previous = journal.head(candidate.identity)
    row = revise_accounting(previous, candidate)
    if row == previous:
        return journal
    return AccountingJournalV1(tournaments=journal.tournaments + (
        (row,) if type(row) is TournamentAccountingV1 else ()),
        rounds=journal.rounds + ((row,) if type(row) is CentRoundV1 else ()))


def accounting_bytes(journal):
    journal.__post_init__()
    return canonical_json({"document_kind": "skatmind_mode_accounting", "version": 1,
        "fingerprint": journal.fingerprint, "journal": journal.to_dict()}) + b"\n"


def resume_accounting(raw):
    value = decode_json(raw)
    if (set(value) != {"document_kind", "version", "fingerprint", "journal"}
            or value["document_kind"] != "skatmind_mode_accounting"
            or type(value["version"]) is not int or value["version"] != 1):
        raise ValueError("Unsupported private accounting document.")
    result = AccountingJournalV1.from_dict(value["journal"])
    if value["fingerprint"] != result.fingerprint:
        raise ValueError("Accounting content fingerprint differs.")
    return result


def load_accounting(root):
    checked_root(root)
    try:
        raw = read_bounded(root / ACCOUNTING_FILENAME, MAX_BYTES)
    except FileNotFoundError:
        return AccountingJournalV1()
    return resume_accounting(raw)


def save_accounting(root, journal, *, expected_fingerprint, source_guard):
    """Serialize comparison, guards and publication for every cooperating local writer."""
    with _PUBLICATION_LOCK:
        return _save_accounting_locked(root, journal, expected_fingerprint=expected_fingerprint,
                                       source_guard=source_guard)


def _save_accounting_locked(root, journal, *, expected_fingerprint, source_guard):
    checked_root(root)
    previous = load_accounting(root)
    if previous.fingerprint != expected_fingerprint or not source_guard():
        raise AccountingConflict("Accounting or its source changed; reload before saving.")
    if journal == previous:
        return "unchanged"
    if (journal.tournaments[:len(previous.tournaments)] != previous.tournaments or
            journal.rounds[:len(previous.rounds)] != previous.rounds):
        raise ValueError("Historical accounting cannot be replaced.")
    raw = accounting_bytes(journal)
    if len(raw) > MAX_BYTES:
        raise ValueError("Accounting exceeds its byte bound.")
    descriptor, filename = tempfile.mkstemp(prefix=".mode-accounting-", suffix=".tmp", dir=root)
    temporary = Path(filename)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            view = memoryview(raw)
            while view:
                written = stream.write(view)
                if type(written) is not int or written <= 0:
                    raise OSError("Incomplete accounting write.")
                view = view[written:]
            stream.flush()
            os.fsync(stream.fileno())
        checked_root(root)
        if load_accounting(root) != previous or not source_guard():
            raise AccountingConflict("Accounting changed during save.")
        os.replace(temporary, root / ACCOUNTING_FILENAME)
        sync_directory(root)
    finally:
        temporary.unlink(missing_ok=True)
    return "saved"
