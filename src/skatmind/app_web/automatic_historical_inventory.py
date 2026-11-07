"""Live saved-Review heads, never archive-history resurrection or filename authority."""

from collections import defaultdict
from dataclasses import dataclass, replace

from skatmind.automatic_historical_evidence import decode_historical_source
from skatmind.automatic_learning_codec import Record, digest, fingerprint
from skatmind.automatic_learning_contracts import SourceKeyV1


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInventoryRow(Record):
    candidate_id: str
    content_digest: str
    status: str
    source: SourceKeyV1
    source_version_id: str
    family: str = "historical_review"
    version: int = 1

    def __post_init__(self):
        self.validate()
        for value in (self.candidate_id, self.content_digest, self.source_version_id):
            digest(value)
        if (self.family != "historical_review" or self.source.family != self.family
                or self.status not in (
                    "selected", "explicit", "ambiguous", "invalid", "unsupported")):
            raise ValueError("Invalid saved Review inventory outcome.")


@dataclass(frozen=True, slots=True)
class HistoricalInventory:
    rows: tuple = ()
    sources: tuple = ()
    heads: tuple = ()
    captions: tuple = ()


def capture_historical_inventory(store, resumed, exclusions):
    if store is None:
        return HistoricalInventory()
    manifest = resumed.manifest
    records = {row.source_version.identity: row for row in manifest.sources}
    states = {row.reference: row.consumption_status for row in resumed.objects}
    excluded = {row.source for row in exclusions}
    rows, sources, captions = [], [], []
    for head in manifest.historical_heads:
        record = records[head.source_version_id]
        status = states[record.object_ref]
        if status == "available" and head.evidence_id in resumed.available_evidence_ids:
            obj = store.read_object(record.object_ref)
            source = decode_historical_source(obj, record)
            captions.append((head.source, source.name, record.revision))
            status = "explicit" if head.source in excluded else "selected"
            if status == "selected":
                sources.append((obj, record, source))
        elif status != "unsupported":
            status = "invalid"
        rows.append(HistoricalInventoryRow(candidate_id=head.source.identity,
            content_digest=fingerprint("historical_head_v1", head.to_dict()), status=status,
            source=head.source, source_version_id=head.source_version_id))
    return HistoricalInventory(tuple(sorted(rows, key=lambda row: row.candidate_id)),
        tuple(sorted(sources, key=lambda row: row[1].source_version.source.product_id)),
        manifest.historical_heads, tuple(captions))


def reconcile_imported_claims(inventory):
    claims = defaultdict(set)
    for _obj, record, source in inventory.historical.sources:
        if source.origin == "imported":
            claims[source.game.game_id].add(record.source_version.source)
    imported = set(claims)
    for _obj, record, source in inventory.matches.sources:
        for game in source.game_references:
            if game.game_id in imported:
                claims[game.game_id].add(record.source_version.source)
    for _obj, record, source in inventory.sessions.sources:
        if source.coverage.game_id in imported:
            claims[source.coverage.game_id].add(record.source_version.source)
    ambiguous = {key for keys in claims.values() if len(keys) > 1 for key in keys}
    def reconciled(part):
        return replace(part,
            rows=tuple(replace(row, status="ambiguous") if row.source in ambiguous else row
                       for row in part.rows),
            sources=tuple(row for row in part.sources
                          if row[1].source_version.source not in ambiguous))
    return replace(inventory, matches=reconciled(inventory.matches),
                   sessions=reconciled(inventory.sessions),
                   historical=reconciled(inventory.historical))
