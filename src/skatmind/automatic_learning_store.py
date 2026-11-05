"""Private automatic archive transactions with explicit no-execution admission.

Cooperating owners share reservations and pins. A nonblocking local OS lease
serializes other processes during mutations and while candidates/readers live.
Filesystem checks remain optimistic against writers bypassing this service.
"""

from __future__ import annotations

import os
import threading
import uuid
import weakref
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path

from . import automatic_learning_io as io
from .automatic_learning_codec import digest, fingerprint, integer
from .automatic_learning_contracts import (
    AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS,
    AUTOMATIC_LEARNING_MAX_OBJECT_BYTES,
    AUTOMATIC_LEARNING_MAX_TOTAL_BYTES,
    EVIDENCE_CLASSES,
    OBJECT_AREAS,
    REPORT_KINDS,
    SOURCE_KINDS,
    ManifestV1,
    ObjectRefV1,
)
from .automatic_learning_objects import (
    StoredObjectV1,
    manifest_bytes,
    resume_manifest,
    validate_generation,
)


class StoreConflictError(ValueError):
    """A process-local owner/candidate/preview is stale; callers may explicitly retry."""


class StoreBusyError(StoreConflictError):
    """Another cooperating local process owns staged work or an in-flight reader."""


class StoreLimitError(ValueError):
    """Publication cannot fit; no eviction or truncation is performed."""


class StoreManifestError(ValueError):
    """Top-level authority could not be read/validated; never reset it as empty."""


class UnsupportedEvidenceError(ValueError):
    """Storage integrity is not semantic evidence admission."""


@dataclass(frozen=True, slots=True, kw_only=True)
class StoreLimitsV1:
    object_bytes: int = AUTOMATIC_LEARNING_MAX_OBJECT_BYTES
    total_bytes: int = AUTOMATIC_LEARNING_MAX_TOTAL_BYTES
    evidence_per_class: int = AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS

    def __post_init__(self):
        for actual, maximum in (
            (self.object_bytes, AUTOMATIC_LEARNING_MAX_OBJECT_BYTES),
            (self.total_bytes, AUTOMATIC_LEARNING_MAX_TOTAL_BYTES),
            (self.evidence_per_class, AUTOMATIC_LEARNING_MAX_EVIDENCE_PER_CLASS),
        ):
            integer(actual, 1)
            if actual > maximum:
                raise ValueError("Injected limits may only tighten production bounds.")


DEFAULT_LIMITS = StoreLimitsV1()

# One optional S4 delivery receipt, never a general archive cache. Large archives
# retain the strict snapshot path; no entries are evicted/truncated for admission.
_DELIVERY_RECEIPT_MAX_OBJECTS = 64
_DELIVERY_RECEIPT_MAX_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class WriteResultV1:
    status: str
    manifest_fingerprint: str


@dataclass(frozen=True, slots=True)
class ObjectStatusV1:
    reference: ObjectRefV1
    storage_status: str
    consumption_status: str


@dataclass(frozen=True, slots=True)
class ResumeV1:
    manifest: ManifestV1
    objects: tuple[ObjectStatusV1, ...]
    orphan_names: tuple[str, ...]
    temporary_names: tuple[str, ...]
    retained_bytes: int
    over_limit: bool
    available_evidence_ids: tuple[str, ...] = ()
    trusted_binding_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _DeliverySnapshotReceipt:
    owner: object
    limits: StoreLimitsV1
    resumed: ResumeV1
    objects: tuple[tuple[ObjectRefV1, bytes], ...]
    inventory_fingerprint: str


@dataclass(frozen=True, slots=True)
class CandidateV1:
    owner: object
    token: object
    references: tuple[ObjectRefV1, ...]
    dependencies: tuple[ObjectRefV1, ...]


@dataclass(frozen=True, slots=True)
class CleanupPreviewV1:
    owner: object
    expected_manifest: str
    epoch: int
    inventory_fingerprint: str
    manifest: ManifestV1
    files: tuple[tuple[str, tuple[int, ...]], ...]
    removed_evidence_ids: tuple[str, ...]


@dataclass
class _Coordinator:
    lock: object = field(default_factory=threading.RLock)
    candidates: dict = field(default_factory=dict)
    pins: Counter = field(default_factory=Counter)
    epoch: int = 0
    lease: object = None
    depth: int = 0

    def __del__(self):
        # A dropped service owner must not leave its OS lease held indefinitely.
        if self.lease is not None:
            self.lease.close()


_COORDINATORS = weakref.WeakValueDictionary()
_COORDINATOR_LOCK = threading.Lock()


def _coordinator(root):
    key = io.checked_root(root)
    with _COORDINATOR_LOCK:
        value = _COORDINATORS.get(key)
        if value is None:
            value = _Coordinator()
            _COORDINATORS[key] = value
        return value


def resolve_automatic_learning_root_v1(managed_home: Path) -> Path:
    """Pure private locator. Never prepares the home, discovers items or creates files."""
    if not isinstance(managed_home, Path):
        raise ValueError("Expected an explicit managed-home Path.")
    return managed_home / "automatic-learning"


class AutomaticLearningStoreV1:
    """Fresh process-local owner over one strictly resumed explicit private root."""

    def __init__(self, root: Path, *, limits: StoreLimitsV1 = DEFAULT_LIMITS):
        if not isinstance(root, Path) or type(limits) is not StoreLimitsV1:
            raise ValueError("Expected an explicit Path and exact store limits.")
        self.root = root.absolute()
        self.limits = limits
        self.owner = object()
        self._coordinator = _coordinator(self.root)
        self._directories = {
            path: io.directory_identity(path)
            for path in (self.root, *(self.root / area for area in OBJECT_AREAS))
        }
        self._coordination_stamp = io.stamp(io.checked_path(self.root / ".coordination.lock"))
        self.snapshot()  # A failed resume never creates, repairs or rewrites anything.

    def _check_root(self):
        io.checked_root(self.root)
        if any(io.directory_identity(path) != identity
               for path, identity in self._directories.items()):
            raise StoreConflictError("Automatic Learning owned directories changed.")
        if io.stamp(io.checked_path(self.root / ".coordination.lock")) != self._coordination_stamp:
            raise StoreConflictError("Automatic Learning coordination file changed.")

    @contextmanager
    def _guard(self):
        with self._coordinator.lock:
            self._check_root()
            if self._coordinator.lease is None:
                try:
                    self._coordinator.lease = io.acquire_local_lease(self.root)
                except OSError as error:
                    raise StoreBusyError(
                        "Automatic Learning is busy in another process."
                    ) from error
            self._coordinator.depth += 1
            try:
                yield
            finally:
                self._coordinator.depth -= 1
                if (self._coordinator.depth == 0 and not self._coordinator.candidates
                        and not self._coordinator.pins):
                    lease, self._coordinator.lease = self._coordinator.lease, None
                    io.release_local_lease(lease)

    def _manifest(self):
        self._check_root()
        try:
            return resume_manifest(io.read_bounded(
                self.root / "manifest.json", AUTOMATIC_LEARNING_MAX_OBJECT_BYTES,
            ))
        except (OSError, ValueError) as error:
            # Keep existing private diagnostics; browser classification uses this type only.
            raise StoreManifestError(str(error)) from error

    def _read(self, ref):
        self._check_root()
        raw = io.read_bounded(io.object_path(self.root, ref), self.limits.object_bytes)
        obj = StoredObjectV1.from_bytes(raw)
        if obj.reference != ref:
            raise ValueError("Object identity, contract or size does not match its reference.")
        return obj

    def read_object(self, reference: ObjectRefV1) -> StoredObjectV1:
        """Storage-only access, including orphans. Does not admit an executed Report."""
        with self._coordinator.lock:
            return self._read(reference)

    def read_evidence(self, evidence_id: str):
        """Admit only an indexed exact original dependency closure through typed codecs."""
        digest(evidence_id)
        with self._coordinator.lock:
            manifest = self._manifest()
            if evidence_id not in {entry.identity for entry in manifest.evidence}:
                raise ValueError("Evidence is not indexed.")
            objects, storage = self._object_states(manifest)
            _statuses, admitted = self._admission(manifest, objects, storage)
            if self._manifest().fingerprint != manifest.fingerprint:
                raise StoreConflictError("Evidence manifest changed during validation.")
            if evidence_id not in admitted:
                raise UnsupportedEvidenceError("Indexed evidence is unavailable or unsupported.")
            return admitted[evidence_id]

    def _admission(self, manifest, objects, storage):
        from .automatic_match_evidence import (
            UnsupportedMatchEvidence,
            decode_match_decision,
            decode_match_source,
        )
        from .automatic_match_rollout_evidence import decode_match_rollout
        from .errors import SkatMindError

        entries = {entry.reference: entry for entry in manifest.objects}
        sources = {entry.object_ref: entry for entry in manifest.sources}
        evidence = {entry.envelope: entry for entry in manifest.evidence}
        source_by_version = {entry.source_version.identity: entry for entry in manifest.sources}
        consumption, decoded, admitted = {}, {}, {}

        def classify(ref):
            if ref in consumption:
                return consumption[ref]
            dependencies = [classify(dep) for dep in entries[ref].dependencies]
            if storage[ref] != "valid":
                status = storage[ref]
            elif any(value in ("missing", "corrupt", "dependency_unavailable")
                     for value in dependencies):
                status = "dependency_unavailable"
            else:
                status = "unsupported"
                try:
                    if ref in sources:
                        decoded[ref] = decode_match_source(objects[ref], sources[ref])
                        status = "available"
                    elif ref in evidence:
                        entry = evidence[ref]
                        source_ref = source_by_version[entry.source_version_id].object_ref
                        if source_ref in decoded:
                            adapter = {("decision", "match_decision"): decode_match_decision,
                                       ("rollout", "match_rollout"): decode_match_rollout}.get(
                                           (entry.evidence_class, ref.kind))
                            if adapter is not None:
                                value = adapter(objects[ref], entry, decoded[source_ref])
                                admitted[entry.identity] = value
                                status = "available"
                except UnsupportedMatchEvidence:
                    pass
                except (ValueError, TypeError, KeyError, AttributeError,
                        RecursionError, SkatMindError):
                    status = "corrupt"
            consumption[ref] = status
            return status

        for ref in entries:
            classify(ref)
        return consumption, admitted

    def _object_states(self, manifest):
        objects, status = {}, {}
        for entry in manifest.objects:
            ref = entry.reference
            try:
                obj = self._read(ref)
                if obj.entry != entry:
                    raise ValueError("Object dependencies disagree with the manifest.")
                objects[ref] = obj
                status[ref] = "valid"
            except FileNotFoundError:
                status[ref] = "missing"
            except (OSError, ValueError, RecursionError):
                status[ref] = "corrupt"
        for ref in manifest.generations:
            if (status[ref] == "valid" and ref.kind == "generation_descriptor"
                    and ref.codec_version in (1, 2)):
                try:
                    validate_generation(objects[ref], manifest)
                except (ValueError, KeyError, TypeError, RecursionError):
                    status[ref] = "corrupt"
        return objects, status

    def snapshot(self) -> ResumeV1:
        with self._coordinator.lock:
            manifest = self._manifest()
            objects, storage = self._object_states(manifest)
            entries = {entry.reference: entry for entry in manifest.objects}
            consumption, admitted = self._admission(manifest, objects, storage)
            states = tuple(ObjectStatusV1(ref, storage[ref], consumption[ref]) for ref in entries)
            files = io.scan_files(self.root)
            indexed = {io.object_path(self.root, ref) for ref in entries}
            orphan_names, temporary_names = [], []
            for path, (_stamp, owned) in files.items():
                if not owned:
                    continue
                name = path.relative_to(self.root).as_posix()
                if path.suffix == ".tmp":
                    temporary_names.append(name)
                elif path not in indexed:
                    orphan_names.append(name)
            retained = io.total_bytes(self.root, files)
            if self._manifest().fingerprint != manifest.fingerprint:
                raise StoreConflictError("Automatic Learning manifest changed during resume.")
            return ResumeV1(
                manifest, states, tuple(sorted(orphan_names)), tuple(sorted(temporary_names)),
                retained, retained > self.limits.total_bytes,
                tuple(entry.identity for entry in manifest.evidence if entry.identity in admitted),
            )

    def _snapshot_for_delivery(self, receipt=None):
        """Reuse one admitted snapshot only after fresh exact-byte/closure checks.

        Caller retains at most one receipt. It is process/store-owner scoped and
        bounded by both object count and bytes. Every invocation still checks owned
        roots, the complete manifest, all indexed object bytes and the full storage
        inventory. Restart or changed inputs re-enter strict snapshot admission;
        unreadable/storage-invalid objects are not retained in a receipt. There is
        no TTL, metadata-only hit or persisted cache. Existing snapshot,
        read_evidence and publication paths remain strict.
        """
        with self._coordinator.lock:
            manifest = self._manifest()
            if (len(manifest.objects) > _DELIVERY_RECEIPT_MAX_OBJECTS or
                    sum(entry.reference.size_bytes for entry in manifest.objects)
                    > _DELIVERY_RECEIPT_MAX_BYTES):
                return self.snapshot(), None

            def read_objects():
                self._check_root()
                return tuple((entry.reference, io.read_bounded(
                    io.object_path(self.root, entry.reference),
                    min(entry.reference.size_bytes, self.limits.object_bytes)))
                    for entry in manifest.objects)

            try:
                objects = read_objects()
            except (OSError, ValueError):
                return self.snapshot(), None
            inventory = self._inventory_fingerprint(io.scan_files(self.root))
            if (type(receipt) is _DeliverySnapshotReceipt and receipt.owner is self.owner
                    and receipt.limits == self.limits and receipt.resumed.manifest == manifest
                    and receipt.objects == objects and receipt.inventory_fingerprint == inventory):
                if self._manifest() != manifest:
                    raise StoreConflictError("Archive authority changed during delivery checks.")
                return receipt.resumed, receipt

            # Seed only from strict admission bracketed by matching exact input reads.
            resumed = self.snapshot()
            if any(row.storage_status != "valid" for row in resumed.objects):
                return resumed, None
            if (resumed.manifest != manifest or read_objects() != objects
                    or self._inventory_fingerprint(io.scan_files(self.root)) != inventory
                    or self._manifest() != manifest):
                raise StoreConflictError("Archive changed while capturing delivery admission.")
            return resumed, _DeliverySnapshotReceipt(self.owner, self.limits, resumed,
                                                      objects, inventory)

    def _quota(self, *, extra: tuple[ObjectRefV1, ...] = (), candidates=None):
        files = io.scan_files(self.root)
        active = self._coordinator.candidates if candidates is None else candidates
        refs = {}
        for ref in (*extra, *(ref for value in active.values() for ref in value.references)):
            if ref.size_bytes > self.limits.object_bytes:
                raise StoreLimitError("Automatic Learning object byte limit exceeded.")
            prior = refs.get(ref.identity)
            if prior is not None and prior != ref:
                raise ValueError("Conflicting pending object references.")
            refs[ref.identity] = ref
        pending = sum(ref.size_bytes for ref in refs.values()
                      if io.object_path(self.root, ref) not in files)
        if io.total_bytes(self.root, files) + pending > self.limits.total_bytes:
            raise StoreLimitError("Automatic Learning retained and pending byte limit exceeded.")

    def begin_candidate(self, objects: tuple[StoredObjectV1, ...]) -> CandidateV1:
        """Reserves staged bytes, superseding this owner's sole prior candidate."""
        if type(objects) is not tuple or any(type(obj) is not StoredObjectV1 for obj in objects):
            raise ValueError("Expected an immutable tuple of storage objects.")
        refs = tuple(obj.reference for obj in objects)
        if len({ref.identity for ref in refs}) != len(refs):
            raise ValueError("Duplicate candidate objects.")
        with self._guard():
            self._manifest()
            # Capture existing dependency closure even before a planned envelope is written.
            dependencies = set()

            def visit(ref):
                if ref not in refs and ref not in dependencies:
                    obj = self._read(ref)
                    dependencies.add(ref)
                    for dependency in obj.dependencies:
                        visit(dependency)

            for obj in objects:
                for dependency in obj.dependencies:
                    visit(dependency)
            candidate = CandidateV1(self.owner, object(), refs, tuple(sorted(
                dependencies, key=lambda ref: ref.identity,
            )))
            candidates = dict(self._coordinator.candidates)
            candidates[self.owner] = candidate
            self._quota(candidates=candidates)
            self._coordinator.candidates = candidates
            self._coordinator.epoch += 1
            return candidate

    def _candidate(self, candidate):
        if (type(candidate) is not CandidateV1 or candidate.owner is not self.owner
                or self._coordinator.candidates.get(self.owner) is not candidate):
            raise StoreConflictError("Automatic Learning candidate was superseded or released.")

    def release_candidate(self, candidate: CandidateV1):
        with self._guard():
            self._candidate(candidate)
            del self._coordinator.candidates[self.owner]
            self._coordinator.epoch += 1

    def publish_object(self, obj: StoredObjectV1, *, candidate: CandidateV1 | None = None) -> str:
        """Complete immutable no-clobber publication; leaves a storage-only orphan."""
        try:
            return self._publish_object(obj, candidate=candidate)
        except StoreBusyError:
            return "conflict"

    def _publish_object(self, obj, *, candidate):
        if type(obj) is not StoredObjectV1:
            raise ValueError("Expected an exact storage object.")
        obj = StoredObjectV1.from_bytes(obj.raw)
        ref = obj.reference
        with self._guard():
            self._manifest()
            if candidate is not None:
                self._candidate(candidate)
                if ref not in candidate.references:
                    raise ValueError("Object was not reserved by this candidate.")
            for dependency in obj.dependencies:
                self._read(dependency)
            try:
                existing = self._read(ref)
            except FileNotFoundError:
                pass
            else:
                if existing != obj:
                    raise ValueError("Occupied immutable object differs.")
                return "unchanged"
            self._quota(extra=(ref,))
            self._coordinator.epoch += 1
            path = io.object_path(self.root, ref)
            temporary = io.write_temporary(path.parent, obj.raw)
            try:
                self._check_root()
                try:
                    os.link(temporary, path)
                except FileExistsError:
                    if self._read(ref) != obj:
                        raise ValueError("Immutable publication winner differs.") from None
                    return "unchanged"
                io.sync_directory(path.parent)
                return "saved"
            finally:
                # No authoritative object is removed, even if link/return fails.
                self._check_root()
                io.discard_temporary(self.root, temporary)

    def _validate_update(self, manifest, current):
        manifest = ManifestV1.from_dict(manifest.to_dict())
        for kind in EVIDENCE_CLASSES:
            if sum(entry.evidence_class == kind for entry in manifest.evidence) > (
                self.limits.evidence_per_class
            ):
                raise StoreLimitError("Automatic Learning evidence class limit exceeded.")
        objects, states = self._object_states(manifest)
        old_entries = set(current.objects)
        entries = {entry.reference: entry for entry in manifest.objects}
        required = set()

        def visit(ref):
            if ref not in required:
                required.add(ref)
                for dep in entries[ref].dependencies:
                    visit(dep)

        for entry in manifest.objects:
            if entry not in old_entries:
                visit(entry.reference)
        for entry in manifest.evidence:
            if entry not in current.evidence:
                visit(entry.envelope)
        for entry in manifest.sources:
            if entry not in current.sources:
                visit(entry.object_ref)
        for entry in manifest.bindings:
            if entry not in current.bindings:
                visit(entry.proof)
        for ref in manifest.generations:
            if ref not in current.generations:
                visit(ref)
        if any(states[ref] != "valid" for ref in required):
            raise ValueError("Manifest publication requires complete intact dependencies.")
        # Check structural bindings, not method-specific execution semantics.
        sources = {entry.source_version.identity: entry for entry in manifest.sources}
        for source in manifest.sources:
            expected_kind = SOURCE_KINDS[source.source_version.source.family]
            if (source not in current.sources
                    and source.object_ref.kind != expected_kind):
                raise ValueError("Source family and stored kind disagree.")
        for entry in manifest.evidence:
            family = sources[entry.source_version_id].source_version.source.family
            if (entry not in current.evidence
                    and entry.envelope.kind != REPORT_KINDS.get((family, entry.evidence_class))):
                raise ValueError("Evidence family and stored kind disagree.")
        for ref in manifest.generations:
            if states[ref] == "valid" and (ref not in current.generations or (
                ref.kind == "generation_descriptor" and ref.codec_version in (1, 2)
            )):
                validate_generation(objects[ref], manifest)
        return manifest

    def update_manifest(
        self, requested: ManifestV1, *, expected_manifest: str,
        candidate: CandidateV1 | None = None,
        commit_guard=None,
    ) -> WriteResultV1:
        """Dependencies first, flushed same-directory CAS last; never rolls back a commit."""
        try:
            return self._update_manifest(
                requested, expected_manifest=expected_manifest, candidate=candidate,
                commit_guard=commit_guard,
            )
        except StoreBusyError:
            return WriteResultV1("conflict", self._manifest().fingerprint)

    def _update_manifest(self, requested, *, expected_manifest, candidate, commit_guard=None):
        digest(expected_manifest)
        if type(requested) is not ManifestV1:
            raise ValueError("Expected an exact manifest.")
        with self._guard():
            current = self._manifest()
            if commit_guard is not None and not commit_guard():
                return WriteResultV1("conflict", current.fingerprint)
            if current.fingerprint != expected_manifest:
                return WriteResultV1("conflict", current.fingerprint)
            if candidate is not None:
                try:
                    self._candidate(candidate)
                except StoreConflictError:
                    return WriteResultV1("conflict", current.fingerprint)
            if requested.space_id != current.space_id:
                raise ValueError("The automatic space identity is immutable.")
            for old_values, new_values, key in (
                (current.sources, requested.sources, lambda entry: entry.source_version.identity),
                (current.evidence, requested.evidence, lambda entry: entry.identity),
            ):
                old = {key(entry): entry for entry in old_values}
                if any(key(entry) in old and old[key(entry)] != entry for entry in new_values):
                    raise ValueError("Retained exact source/execution bindings are immutable.")
            old_scopes = {entry.source_version.source: entry.scope for entry in current.sources}
            if any(entry.source_version.source in old_scopes
                   and old_scopes[entry.source_version.source] != entry.scope
                   for entry in requested.sources):
                raise ValueError("A correction cannot change its logical identity namespace.")
            requested = self._validate_update(requested, current)
            if replace(requested, revision=current.revision) == current:
                if candidate is not None:
                    self.release_candidate(candidate)
                return WriteResultV1("unchanged", current.fingerprint)
            if requested.revision != current.revision + 1:
                raise ValueError("A manifest change must increment revision exactly once.")
            raw = manifest_bytes(requested)
            if len(raw) > AUTOMATIC_LEARNING_MAX_OBJECT_BYTES:
                raise StoreLimitError("Automatic Learning manifest byte limit exceeded.")
            if not set(requested.objects).issubset(current.objects):
                self._quota()
            temporary = io.write_temporary(self.root, raw)
            self._coordinator.epoch += 1
            try:
                latest = self._manifest()  # Immediately before atomic replacement.
                if (latest.fingerprint != expected_manifest
                        or commit_guard is not None and not commit_guard()):
                    return WriteResultV1("conflict", latest.fingerprint)
                os.replace(temporary, self.root / "manifest.json")
                # COMMIT BOUNDARY: no cleanup of manifest or rollback after this line.
                io.sync_directory(self.root)
                if candidate is not None:
                    self.release_candidate(candidate)
                return WriteResultV1("saved", requested.fingerprint)
            finally:
                self._check_root()
                io.discard_temporary(self.root, temporary)

    @contextmanager
    def pin_objects(self, references: tuple[ObjectRefV1, ...], *, expected_manifest: str):
        """Pins immutable dependency closure until the caller finishes storage delivery."""
        digest(expected_manifest)
        with self._guard():
            manifest = self._manifest()
            if manifest.fingerprint != expected_manifest:
                raise StoreConflictError("Reader manifest changed.")
            entries = {entry.reference: entry for entry in manifest.objects}
            closure = set()

            def visit(ref):
                if ref not in entries:
                    raise ValueError("Readers can pin only manifest-indexed dependencies.")
                if ref not in closure:
                    self._read(ref)
                    closure.add(ref)
                    for dep in entries[ref].dependencies:
                        visit(dep)

            for ref in references:
                visit(ref)
            self._coordinator.pins.update(closure)
            self._coordinator.epoch += 1
        try:
            yield
        finally:
            with self._guard():
                self._coordinator.pins.subtract(closure)
                self._coordinator.pins += Counter()
                self._coordinator.epoch += 1

    def _protected(self, manifest):
        refs = {entry.reference for entry in manifest.objects} | set(self._coordinator.pins)
        for candidate in self._coordinator.candidates.values():
            refs.update(candidate.references)
            refs.update(candidate.dependencies)
            # A staged object may depend on already published objects not in its reservation.
            pending = list(candidate.references)
            while pending:
                ref = pending.pop()
                try:
                    obj = self._read(ref)
                except FileNotFoundError:
                    continue
                except (OSError, ValueError):
                    # Unknown edges must not license deletion. Require release/recovery first.
                    raise StoreConflictError(
                        "Cannot clean up an invalid active candidate."
                    ) from None
                for dep in obj.dependencies:
                    if dep not in refs:
                        refs.add(dep)
                        pending.append(dep)
        return {io.object_path(self.root, ref) for ref in refs}

    def preview_cleanup(
        self, *, expected_manifest: str, remove_evidence_ids: tuple[str, ...] = (),
        release_source_version_ids: tuple[str, ...] = (),
    ) -> CleanupPreviewV1:
        """Exact explicit deletion preview; source release is separate from evidence removal."""
        digest(expected_manifest)
        with self._guard():
            current = self._manifest()
            if current.fingerprint != expected_manifest:
                raise StoreConflictError("Cleanup manifest changed.")
            for ids in (remove_evidence_ids, release_source_version_ids):
                if type(ids) is not tuple or len(set(ids)) != len(ids):
                    raise ValueError("Removal identities must be unique immutable tuples.")
                for value in ids:
                    digest(value)
            removed = set(remove_evidence_ids)
            released = set(release_source_version_ids)
            if (removed - {entry.identity for entry in current.evidence}
                    or released - {entry.source_version.identity for entry in current.sources}):
                raise ValueError("Removal identity is not retained.")
            removed_refs = {
                entry.envelope for entry in current.evidence if entry.identity in removed
            }
            removed_refs.update(entry.object_ref for entry in current.sources
                                if entry.source_version.identity in released)
            entries = {entry.reference: entry for entry in current.objects}

            def depends(ref):
                return ref in removed_refs or any(depends(dep) for dep in entries[ref].dependencies)

            generations = [ref if ref is not None and not depends(ref) else None
                           for ref in (current.current_generation, current.previous_generation)]
            sources = tuple(entry for entry in current.sources
                            if entry.source_version.identity not in released)
            evidence = tuple(entry for entry in current.evidence if entry.identity not in removed)
            roots = [entry.object_ref for entry in sources] + [entry.envelope for entry in evidence]
            roots += [entry.proof for entry in current.bindings]
            roots += [ref for ref in generations if ref]
            reached = set()

            def visit(ref):
                if ref not in reached:
                    reached.add(ref)
                    for dep in entries[ref].dependencies:
                        visit(dep)

            for ref in roots:
                visit(ref)
            changed = bool(removed or released)
            requested = replace(
                current, revision=current.revision + int(changed),
                sources=sources, evidence=evidence,
                objects=tuple(entry for entry in current.objects if entry.reference in reached),
                current_generation=generations[0], previous_generation=generations[1],
            )
            protected = self._protected(requested)
            inventory = io.scan_files(self.root)
            files = tuple(sorted(
                (path.relative_to(self.root).as_posix(), stamp)
                for path, (stamp, owned) in inventory.items()
                if owned and path not in protected
            ))
            return CleanupPreviewV1(
                self.owner, expected_manifest, self._coordinator.epoch,
                self._inventory_fingerprint(inventory), requested, files,
                remove_evidence_ids,
            )

    def _inventory_fingerprint(self, files):
        return fingerprint("cleanup_inventory_v1", sorted(
            [path.relative_to(self.root).as_posix(), list(stamp), owned]
            for path, (stamp, owned) in files.items()
        ))

    def commit_cleanup(self, preview: CleanupPreviewV1, *, commit_guard=None) -> WriteResultV1:
        """Remove references first. Interrupted physical deletion leaves harmless orphans."""
        try:
            return self._commit_cleanup(preview, commit_guard=commit_guard)
        except StoreBusyError:
            return WriteResultV1("conflict", self._manifest().fingerprint)

    def _commit_cleanup(self, preview, *, commit_guard=None):
        if type(preview) is not CleanupPreviewV1 or preview.owner is not self.owner:
            raise StoreConflictError("Cleanup preview belongs to a different owner.")
        with self._guard():
            current = self._manifest()
            if (current.fingerprint != preview.expected_manifest
                    or self._coordinator.epoch != preview.epoch
                    or commit_guard is not None and not commit_guard()):
                return WriteResultV1("conflict", current.fingerprint)
            protected = self._protected(preview.manifest)
            files = io.scan_files(self.root)
            if self._inventory_fingerprint(files) != preview.inventory_fingerprint:
                return WriteResultV1("conflict", current.fingerprint)
            for name, expected_stamp in preview.files:
                path = self.root / name
                if path in protected or files.get(path) != (expected_stamp, True):
                    return WriteResultV1("conflict", current.fingerprint)
            if preview.manifest != current:
                result = self.update_manifest(
                    preview.manifest, expected_manifest=current.fingerprint,
                    commit_guard=commit_guard,
                )
                if result.status == "conflict":
                    return result
                current = preview.manifest
            self._coordinator.epoch += 1
            for name, expected_stamp in preview.files:
                # Recheck before each deletion, including an external newer manifest commit.
                if self._manifest().fingerprint != current.fingerprint:
                    return WriteResultV1("conflict", self._manifest().fingerprint)
                path = self.root / name
                if io.stamp(io.checked_path(path)) != expected_stamp:
                    return WriteResultV1("conflict", current.fingerprint)
                path.unlink()
            return WriteResultV1(
                "saved" if (preview.files
                            or preview.manifest.fingerprint != preview.expected_manifest)
                else "unchanged", current.fingerprint,
            )


def initialize_automatic_learning_store_v1(
    root: Path, *, limits: StoreLimitsV1 = DEFAULT_LIMITS,
) -> AutomaticLearningStoreV1:
    """Explicit absent-root initialization. A committed manifest is never rolled back."""
    if not isinstance(root, Path) or type(limits) is not StoreLimitsV1:
        raise ValueError("Expected an explicit root and exact limits.")
    root = root.absolute()
    io.checked_root(root.parent)
    root.mkdir()  # Never replace or repair an existing/partially initialized root.
    for area in OBJECT_AREAS:
        (root / area).mkdir()
    with (root / ".coordination.lock").open("xb") as file:
        file.write(b"\0")
        file.flush()
        os.fsync(file.fileno())
    manifest = ManifestV1(space_id=f"automatic-{uuid.uuid4().hex}")
    temporary = io.write_temporary(root, manifest_bytes(manifest))
    try:
        os.link(temporary, root / "manifest.json")  # No-clobber initial commit.
        io.sync_directory(root)
    finally:
        io.discard_temporary(root, temporary)
    return AutomaticLearningStoreV1(root, limits=limits)


def resume_automatic_learning_store_v1(
    root: Path, *, limits: StoreLimitsV1 = DEFAULT_LIMITS,
) -> AutomaticLearningStoreV1:
    return AutomaticLearningStoreV1(root, limits=limits)
