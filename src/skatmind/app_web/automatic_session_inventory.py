"""Complete mixed membership using the same bounded physical capture as Matches."""

from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace

from skatmind.automatic_learning_codec import Record, digest, fingerprint
from skatmind.automatic_learning_contracts import SourceKeyV1
from skatmind.automatic_match_evidence import UnsupportedMatchEvidence
from skatmind.automatic_session_evidence import build_managed_session_source
from skatmind.errors import SkatMindError
from skatmind.match_source_coordination import match_source_coordinator
from skatmind.session_persistence import _decode_persistence_json
from skatmind.session_persistence_codec import resume_session_document_v1
from skatmind.session_persistence_contracts import SESSION_PERSISTENCE_SUPPORTED_DOCUMENT_KINDS

from .automatic_historical_inventory import (
    HistoricalInventory,
    capture_historical_inventory,
    reconcile_imported_claims,
)
from .automatic_match_inventory import (
    InventoryConflict,
    MatchInventory,
    _capture,
    capture_match_inventory,
    inventory_still_current,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionInventoryRow(Record):
    candidate_id: str
    content_digest: str
    status: str
    source: SourceKeyV1 | None
    source_version_id: str | None
    family: str = "session"
    version: int = 1

    def __post_init__(self):
        from skatmind.automatic_learning_contracts import SourceKeyV1
        self.validate()
        digest(self.candidate_id)
        digest(self.content_digest)
        if self.family != "session" or self.status not in (
                "selected", "explicit", "ambiguous", "invalid", "unsupported"):
            raise ValueError("Unsupported Session inventory outcome.")
        if self.source is None:
            if self.status not in ("invalid", "unsupported") or self.source_version_id is not None:
                raise ValueError("Unidentified Session must not claim identity.")
        elif type(self.source) is not SourceKeyV1 or self.source.family != "session":
            raise ValueError("Expected a Session identity.")
        else:
            digest(self.source_version_id)

    @classmethod
    def from_dict(cls, data):
        from skatmind.automatic_learning_contracts import SourceKeyV1
        if type(data) is not dict or set(data) != {
                "candidate_id", "content_digest", "status", "source", "source_version_id",
                "family", "version"}:
            raise ValueError("Invalid Session inventory fields.")
        return cls(**{**data, "source": None if data["source"] is None else
                     SourceKeyV1.from_dict(data["source"])})


@dataclass(frozen=True, slots=True)
class MixedInventory:
    matches: MatchInventory
    sessions: MatchInventory
    historical: HistoricalInventory = HistoricalInventory()

    @property
    def rows(self):
        return self.historical.rows + self.matches.rows + self.sessions.rows

    @property
    def sources(self):
        return self.historical.sources + self.matches.sources + self.sessions.sources

    @property
    def fingerprint(self):
        return fingerprint("mixed_inventory_v1", [row.to_dict() for row in self.rows])


class MixedSourceCoordinator:
    def __init__(self, home):
        self.values = tuple(match_source_coordinator(home.category(family).path)
                            for family in ("matches", "sessions"))

    @property
    def generation(self):
        return tuple(value.generation for value in self.values)

    @property
    @contextmanager
    def lock(self):
        with ExitStack() as stack:
            for value in self.values:
                stack.enter_context(value.lock)
            yield


def capture_session_inventory(home, exclusions=()):
    root = home.category("sessions").path
    try:
        first = _capture(root)
        rows, sources = [], {}
        excluded = {entry.source for entry in exclusions}
        for name, _stamp, content, raw in first[1]:
            source = version = None
            status = "invalid"
            candidate_id = fingerprint("session_candidate_locator_v1", name)
            if raw is not None:
                try:
                    data = _decode_persistence_json(raw)
                    contract = data.get("session_persistence_version")
                    kind = data.get("document_kind")
                    if (type(contract) is int and contract != 1 or type(kind) is str
                            and kind not in SESSION_PERSISTENCE_SUPPORTED_DOCUMENT_KINDS):
                        raise UnsupportedMatchEvidence("Unsupported saved Session contract.")
                    document = resume_session_document_v1(data).document
                    value = build_managed_session_source(document)
                except UnsupportedMatchEvidence:
                    status = "unsupported"
                except (ValueError, TypeError, RecursionError, SkatMindError):
                    pass
                else:
                    source = value[1].source_version.source
                    version = value[1].source_version.identity
                    status = "explicit" if source in excluded else "selected"
                    sources[candidate_id] = value
            rows.append(SessionInventoryRow(candidate_id=candidate_id, content_digest=content,
                status=status, source=source, source_version_id=version))
        counts = Counter(row.source for row in rows if row.source is not None)
        rows = tuple(sorted((replace(row, status="ambiguous") if row.source is not None
                             and counts[row.source] > 1 else row for row in rows),
                            key=lambda row: row.candidate_id))
        if _capture(root) != first:
            raise InventoryConflict("Session inventory changed during validation.")
        selected = tuple(sorted((sources[row.candidate_id] for row in rows
                                 if row.status == "selected"),
                                key=lambda value: value[1].source_version.source.product_id))
        return MatchInventory(rows, (first[0], tuple((name, stamp, content)
            for name, stamp, content, _raw in first[1])), selected)
    except (OSError, ValueError) as error:
        raise InventoryConflict("Session inventory is incomplete or changed.") from error


def capture_mixed_inventory(home, exclusions=(), *, store=None, resumed=None):
    value = MixedInventory(capture_match_inventory(home, exclusions),
                           capture_session_inventory(home, exclusions),
                           capture_historical_inventory(store, resumed, exclusions))
    value = reconcile_imported_claims(value)
    if not mixed_inventory_still_current(home, value):
        raise InventoryConflict("Mixed source membership changed.")
    return value


def mixed_inventory_still_current(home, inventory):
    if not inventory_still_current(home, inventory.matches):
        return False
    try:
        from skatmind import automatic_learning_io as io
        from skatmind.automatic_learning_contracts import AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
        from skatmind.automatic_learning_objects import resume_manifest
        path = home.root / "automatic-learning" / "manifest.json"
        heads = (resume_manifest(io.read_bounded(path, AUTOMATIC_LEARNING_MAX_OBJECT_BYTES))
                 .historical_heads if path.exists() else ())
        if heads != inventory.historical.heads:
            return False
        captured = _capture(home.category("sessions").path)
        return (captured[0], tuple((name, stamp, content)
            for name, stamp, content, _raw in captured[1])) == inventory.sessions.physical
    except (OSError, ValueError):
        return False
