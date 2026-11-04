"""Complete bounded Match inventory; browser summaries are not source authority."""

import hashlib
import os
import stat
from collections import Counter
from dataclasses import dataclass, replace

from skatmind import automatic_learning_io as io
from skatmind.automatic_learning_codec import Record, digest, fingerprint
from skatmind.automatic_learning_contracts import AUTOMATIC_LEARNING_MAX_TOTAL_BYTES, SourceKeyV1
from skatmind.automatic_match_evidence import build_managed_match_source
from skatmind.errors import SkatMindError
from skatmind.match_workspace_persistence import _decode_persistence_json
from skatmind.match_workspace_persistence_codec import resume_match_workspace_document_v1
from skatmind.match_workspace_persistence_contracts import MATCH_WORKSPACE_SUPPORTED_DOCUMENT_KINDS

from .managed_item_contracts import MANAGED_ITEM_MAX_CANDIDATES, MANAGED_ITEM_MAX_IMPORT_BYTES


class InventoryConflict(ValueError):
    """Incomplete/unstable membership is never interpreted as deletion."""


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchInventoryRow(Record):
    candidate_id: str
    content_digest: str
    status: str
    source: SourceKeyV1 | None
    source_version_id: str | None
    version: int = 1

    def __post_init__(self):
        self.validate()
        digest(self.candidate_id)
        digest(self.content_digest)
        if self.status not in ("selected", "explicit", "ambiguous", "invalid", "unsupported"):
            raise ValueError("Unsupported Match inventory outcome.")
        if self.source is None:
            if self.status not in ("invalid", "unsupported") or self.source_version_id is not None:
                raise ValueError("Unidentified entries must not claim Product identity.")
        elif self.source.family != "match" or self.source_version_id is None:
            raise ValueError("Expected an exact Match identity.")
        if self.source_version_id is not None:
            digest(self.source_version_id)


@dataclass(frozen=True, slots=True)
class MatchInventory:
    rows: tuple[MatchInventoryRow, ...]
    # Exact private physical capture, including every invalid/excluded candidate.
    physical: tuple
    sources: tuple

    @property
    def fingerprint(self):
        return fingerprint("match_inventory_v1", [row.to_dict() for row in self.rows])


def _listing(root):
    identity = io.checked_root(root)
    before = io.stamp(io.checked_path(root, directory=True))
    result = []
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name.lower().endswith(".json"):
                result.append(entry.name)
                if len(result) > MANAGED_ITEM_MAX_CANDIDATES:
                    raise InventoryConflict("Managed Match inventory is capped.")
    if io.stamp(io.checked_path(root, directory=True)) != before:
        raise InventoryConflict("Managed Match inventory changed during enumeration.")
    return identity, before, tuple(sorted(result))


def _capture(root):
    identity, stamp, names = _listing(root)
    entries = []
    captured_bytes = 0
    for name in names:
        path = root / name
        info = path.lstat()
        physical = (io.stamp(info), info.st_mode,
                    getattr(info, "st_file_attributes", 0), info.st_nlink)
        unsafe = (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                  or path.is_symlink() or path.is_junction()
                  or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        if unsafe:
            # No traversal of targets or invalid directories, including broken links.
            raw = None
            content = fingerprint("invalid_match_entry_v1", [
                list(physical[0]), *physical[1:]])
        else:
            if info.st_size > MANAGED_ITEM_MAX_IMPORT_BYTES:
                raise InventoryConflict("Managed Match inventory exceeds its read bound.")
            captured_bytes += info.st_size
            if captured_bytes > AUTOMATIC_LEARNING_MAX_TOTAL_BYTES:
                raise InventoryConflict("Managed Match inventory exceeds its aggregate byte bound.")
            raw = io.read_bounded(path, MANAGED_ITEM_MAX_IMPORT_BYTES)
            content = hashlib.sha256(raw).hexdigest()
        entries.append((name, physical, content, raw))
    if _listing(root) != (identity, stamp, names):
        raise InventoryConflict("Managed Match membership changed during capture.")
    return identity, tuple(entries)


def capture_match_inventory(home, exclusions=()):
    """Two complete reads detect replacement and changes to all candidate contents."""
    root = home.category("matches").path
    try:
        first = _capture(root)
        rows, sources = [], {}
        excluded = {entry.source for entry in exclusions}
        for name, _stamp, content, raw in first[1]:
            source = version = None
            status = "invalid"
            candidate_id = fingerprint("match_candidate_locator_v1", name)
            if raw is not None:
                try:
                    data = _decode_persistence_json(raw)
                    contract = data.get("match_workspace_persistence_version")
                    kind = data.get("document_kind")
                    if (type(contract) is int and contract != 1
                            or type(kind) is str and kind not in
                            MATCH_WORKSPACE_SUPPORTED_DOCUMENT_KINDS):
                        status = "unsupported"
                        raise ValueError("Unsupported saved Match contract.")
                    document = resume_match_workspace_document_v1(data).document
                    obj, record, snapshot = build_managed_match_source(document)
                except (ValueError, TypeError, RecursionError, SkatMindError):
                    pass
                else:
                    source = record.source_version.source
                    version = record.source_version.identity
                    status = "explicit" if source in excluded else "selected"
                    sources[candidate_id] = (obj, record, snapshot)
            rows.append(MatchInventoryRow(candidate_id=candidate_id, content_digest=content,
                status=status, source=source, source_version_id=version))
        counts = Counter(row.source for row in rows if row.source is not None)
        rows = tuple(sorted((replace(row, status="ambiguous")
            if row.source is not None and counts[row.source] > 1 else row
            for row in rows), key=lambda row: row.candidate_id))
        if _capture(root) != first:
            raise InventoryConflict("Managed Match candidates changed during validation.")
        selected = tuple(sorted((sources[row.candidate_id] for row in rows
                                 if row.status == "selected"),
                                key=lambda value: value[1].source_version.source.product_id))
        return MatchInventory(rows, (first[0], tuple(
            (name, stamp, content) for name, stamp, content, _raw in first[1])), selected)
    except (OSError, ValueError) as error:
        raise InventoryConflict("Managed Match inventory is incomplete or changed.") from error


def inventory_still_current(home, inventory):
    """Fresh bounded bytes for every candidate, without Snapshot rebuilding."""
    root = home.category("matches").path
    try:
        captured = _capture(root)
        physical = (captured[0], tuple((name, stamp, content)
                    for name, stamp, content, _raw in captured[1]))
        return physical == inventory.physical
    except (OSError, ValueError):
        return False
