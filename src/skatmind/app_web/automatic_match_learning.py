"""Explicit private automatic Match preparation and guarded process-local access.

No routes, passive reconstruction, analysis execution, manual collection mutation,
automatic retry or repair. Final publication orders app -> source barrier -> store;
accepted writers order Product -> optional app -> source barrier. No Corpus lock
is held with a Product lock.
"""

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace

from skatmind import automatic_learning_io as io
from skatmind.automatic_learning_contracts import ExclusionV1, GenerationV1
from skatmind.automatic_learning_store import (
    AutomaticLearningStoreV1,
    StoreConflictError,
    StoreLimitError,
    StoreManifestError,
)
from skatmind.automatic_match_preparation import (
    ADAPTERS,
    BUILDERS,
    AutomaticMatchGeneration,
    EvidenceOutcome,
    UnsupportedGeneration,
    admit_generation,
    automatic_ids,
    build_automatic_match_bundle,
    generation_object,
    input_fingerprint,
)
from skatmind.errors import SkatMindError
from skatmind.match_source_coordination import match_source_coordinator

from .automatic_match_inventory import (
    InventoryConflict,
    capture_match_inventory,
    inventory_still_current,
)
from .saved_match_analyses import archive_store


@dataclass(frozen=True, slots=True)
class AutomaticMatchServiceResult:
    status: str
    generation: AutomaticMatchGeneration | None = None
    committed: bool = False
    failure: str | None = None
    attempt: object = None


@dataclass(frozen=True, slots=True)
class AutomaticDeliveryBinding:
    owner: object
    attempt: object
    installed: object
    result: AutomaticMatchServiceResult
    resumed: object
    inventory: object
    epoch: int


@dataclass(frozen=True, slots=True)
class _Installed:
    reference: object
    generation: AutomaticMatchGeneration
    bundle: object
    inventory: object


def _selection(inventory, resumed):
    manifest = resumed.manifest
    states = {row.reference: row.consumption_status for row in resumed.objects}
    archived = {row.source_version.identity: row for row in manifest.sources}
    exclusions = {row.source: row for row in manifest.exclusions}
    for row in inventory.rows:
        if row.source is not None and row.status != "selected":
            exclusions[row.source] = ExclusionV1(source=row.source, reason=row.status)
    live = {row.source for row in inventory.rows if row.source is not None}
    # Unknown invalid candidates never inherit a guessed Product identity. A prior
    # aggregate is hidden conservatively when its identity cannot be found alive.
    for source in manifest.sources:
        key = source.source_version.source
        if key.family == "match" and key not in live and key not in exclusions:
            exclusions[key] = ExclusionV1(source=key, reason="missing")
    selected = []
    for value in inventory.sources:
        _obj, record, _snapshot = value
        old = archived.get(record.source_version.identity)
        if old is not None and (old != record or states[old.object_ref] != "available"):
            reason = "unsupported" if states[old.object_ref] == "unsupported" else "invalid"
            exclusions[record.source_version.source] = ExclusionV1(
                source=record.source_version.source, reason=reason)
        else:
            selected.append(value)
    selected = tuple(selected)
    ids = tuple(value[1].source_version.identity for value in selected)
    outcomes = tuple(EvidenceOutcome(evidence_id=entry.identity,
        status=(states[entry.envelope] if states[entry.envelope] != "available" else
                "selected" if entry.source_version_id in ids else "non_current"))
        for entry in sorted(manifest.evidence, key=lambda entry: entry.identity))
    exclusions = tuple(sorted(exclusions.values(), key=lambda row: row.source.identity))
    identity = input_fingerprint(inventory.rows, outcomes, exclusions, ids)
    return selected, outcomes, exclusions, identity


def _requested_manifest(before, sources, obj):
    records = {row.source_version.identity: row for row in before.sources}
    entries = {row.reference: row for row in before.objects}
    for source_obj, record, _snapshot in sources:
        records[record.source_version.identity] = record
        entries[source_obj.reference] = source_obj.entry
    entries[obj.reference] = obj.entry
    # Retire only the third descriptor reference. Its bytes remain an orphan until
    # explicit cleanup; all archived sources and executions remain indexed.
    roots = [row.object_ref for row in records.values()]
    roots += [row.envelope for row in before.evidence] + [row.proof for row in before.bindings]
    roots += [obj.reference] + ([before.current_generation] if before.current_generation else [])
    reached = set()

    def visit(ref):
        if ref not in reached:
            reached.add(ref)
            for dependency in entries[ref].dependencies:
                visit(dependency)

    for ref in roots:
        visit(ref)
    return replace(before, revision=before.revision + 1,
        objects=tuple(entries[ref] for ref in sorted(reached, key=lambda ref: ref.identity)),
        sources=tuple(records[key] for key in sorted(records)),
        current_generation=obj.reference, previous_generation=before.current_generation)


class AutomaticMatchLearningServiceV1:
    """A separate preparation owner; a copied bundle never authorizes delivery."""

    def __init__(self, app):
        self.app = app
        self.home = app.managed_home
        self.archive_scope = app.saved_match_analyses
        self._roots = {root: io.checked_root(root) for root in (
            self.home.root, self.home.category("matches").path)}
        self.coordinator = match_source_coordinator(self.home.category("matches").path)
        self.attempt = None
        self.store = None
        self.archive = None
        self._installed = None
        self._delivery_snapshot_receipt = None

    @classmethod
    def open(cls, app):
        value = cls(app)
        with app.lock:
            app.automatic_match_learning = value
        return value

    def _owner(self, attempt=None):
        try:
            if any(io.checked_root(root) != identity for root, identity in self._roots.items()):
                return False
        except (OSError, ValueError):
            return False
        return (self.app.automatic_match_learning is self
                and self.app.managed_home is self.home
                and self.app.saved_match_analyses is self.archive_scope
                and (self.archive is None or self.archive_scope.store is self.archive)
                and (attempt is None or self.attempt is attempt))

    def _store(self, *, initialize=False):
        if not self._owner():
            raise StoreConflictError("Automatic Match owner changed.")
        archive = archive_store(self.app, initialize=initialize)
        if archive is not None and self.store is None:
            # Fresh store owner shares root quotas/pins/lock, never S2/S3 reservations.
            self.archive = archive
            self.store = AutomaticLearningStoreV1(archive.root, limits=archive.limits)
        if not self._owner():
            raise StoreConflictError("Automatic Match archive owner changed.")
        return self.store

    def _capture(self, store):
        epoch = self.coordinator.generation
        resumed, self._delivery_snapshot_receipt = store._snapshot_for_delivery(
            self._delivery_snapshot_receipt)
        inventory = capture_match_inventory(self.home, resumed.manifest.exclusions)
        with self.coordinator.lock:
            if epoch != self.coordinator.generation or not inventory_still_current(
                    self.home, inventory):
                raise InventoryConflict("Managed Match sources changed during capture.")
        return resumed, inventory, epoch

    def _inspect(self):
        store = self._store()
        if store is None:
            return AutomaticMatchServiceResult("missing"), None, None
        resumed, inventory, _epoch = self._capture(store)
        manifest = resumed.manifest
        ref = manifest.current_generation
        installed = self._installed
        # A previously installed, intact generation can be explicitly viewed as
        # outdated when another writer advances current and retains it as previous.
        if installed is not None and installed.reference in manifest.generations:
            ref = installed.reference
        if ref is None:
            return AutomaticMatchServiceResult("missing"), resumed, inventory
        generation = admit_generation(store.read_object(ref), manifest)
        states = {row.reference: row for row in resumed.objects}
        obj = store.read_object(ref)
        if any(states[dep].consumption_status != "available" for dep in obj.dependencies):
            return AutomaticMatchServiceResult("excluded", generation), resumed, inventory
        live = {row.source for row in inventory.rows if row.source is not None}
        sources = {row.source_version.identity: row for row in manifest.sources}
        if any(sources[key].source_version.source not in live
               for key in generation.recipe.source_version_ids):
            return AutomaticMatchServiceResult("deleted", generation), resumed, inventory
        blocked = {row.source for row in inventory.rows if row.status != "selected"}
        if any(sources[key].source_version.source in blocked
               for key in generation.recipe.source_version_ids):
            return AutomaticMatchServiceResult("excluded", generation), resumed, inventory
        _, _, _, identity = _selection(inventory, resumed)
        outdated = identity != generation.input_fingerprint or ref != manifest.current_generation
        valid_bundle = (installed is not None and installed.reference == ref
                        and installed.generation == generation)
        status = "outdated" if outdated else "current" if valid_bundle else "reconstruction_needed"
        return AutomaticMatchServiceResult(status, generation), resumed, inventory

    def inspect(self):
        """Passive validation only; never creates a store, prepares or writes."""
        try:
            result, resumed, inventory = self._inspect()
            with self.app.lock, self.coordinator.lock:
                if (not self._owner() or inventory is not None and not inventory_still_current(
                        self.home, inventory) or resumed is not None and
                        self.store._manifest() != resumed.manifest):
                    return AutomaticMatchServiceResult("conflict")
            return result
        except UnsupportedGeneration:
            return AutomaticMatchServiceResult("unsupported")
        except (StoreConflictError, InventoryConflict):
            return AutomaticMatchServiceResult("conflict")
        except StoreManifestError:
            return AutomaticMatchServiceResult("excluded", failure="invalid_storage")
        except (OSError, ValueError, SkatMindError):
            return AutomaticMatchServiceResult("excluded")

    def update(self):
        reservation = store = None
        requested = obj = bundle = generation = inventory = None
        with self.app.lock:
            if not self._owner():
                return AutomaticMatchServiceResult("conflict")
            attempt = self.attempt = object()
        try:
            store = self._store(initialize=True)
            resumed, inventory, epoch = self._capture(store)
            before = resumed.manifest
            sources, outcomes, exclusions, identity = _selection(inventory, resumed)
            previous = (None if before.current_generation is None else
                        admit_generation(store.read_object(before.current_generation), before))
            same = previous is not None and previous.input_fingerprint == identity
            installed = self._installed
            if (same and installed is not None
                    and installed.reference == before.current_generation
                    and installed.generation == previous):
                # Consumption does full before/after authorization, including storage pins.
                consumed = self.consume(lambda bundle: bundle)
                # consume captures its own attempt. Authorize this update's receipt
                # against its original state, including changes around that call.
                with self.app.lock, self.coordinator.lock, store._guard():
                    if (not self._owner(attempt) or self._installed is not installed
                            or consumed is not installed.bundle or store._manifest() != before):
                        raise StoreConflictError("Automatic reuse was superseded.")
                    return AutomaticMatchServiceResult("reused", previous, attempt=attempt)
            selected_ids = tuple(value[1].source_version.identity for value in sources)
            catalog_revision = (0 if previous is None else previous.recipe.catalog_revision)
            if previous is None and sources or previous is not None and (
                    previous.recipe.source_version_ids != selected_ids):
                catalog_revision += 1
            corpus_id, dataset_id = automatic_ids(before.space_id)
            with ExitStack() as stack:
                refs = {value[1].object_ref for value in sources if value[1] in before.sources}
                evidence_ids = tuple(row.evidence_id for row in outcomes
                                     if row.status == "selected")
                refs.update(entry.envelope for entry in before.evidence
                            if entry.identity in evidence_ids)
                stack.enter_context(store.pin_objects(
                    tuple(refs), expected_manifest=before.fingerprint))
                evidence = tuple(store.read_evidence(row.evidence_id) for row in outcomes
                                 if row.status == "selected")
                with self.app.lock:
                    if not self._owner(attempt):
                        raise StoreConflictError("Automatic preparation attempt changed.")
                    reservation = store.begin_candidate(tuple(value[0] for value in sources))
                bundle = build_automatic_match_bundle(sources, evidence, corpus_id=corpus_id,
                    dataset_id=dataset_id, catalog_revision=catalog_revision)
                recipe = GenerationV1(source_version_ids=selected_ids,
                    evidence_ids=evidence_ids,
                    exclusions=exclusions, skipped_situations=bundle.skipped,
                    corpus_id=corpus_id, dataset_id=dataset_id, catalog_revision=catalog_revision,
                    seed=0, partition_weights=(70, 15, 15), adapter_versions=ADAPTERS,
                    builder_versions=BUILDERS, derived_fingerprints=bundle.fingerprints)
                generation = AutomaticMatchGeneration(recipe, inventory.rows, outcomes, identity)
                if same and generation != previous:
                    raise ValueError("Reconstruction differs from the accepted generation.")
                obj = generation_object(generation, sources, evidence)
                requested = before if same else _requested_manifest(before, sources, obj)
                admit_generation(obj, requested)
                # All typed revalidation remains outside app/Product locks.
                if store.snapshot() != resumed:
                    raise StoreConflictError("Automatic archive changed during preparation.")
                with self.app.lock:
                    if not self._owner(attempt):
                        raise StoreConflictError("Automatic preparation was superseded.")
                    reservation = store.begin_candidate((
                        *tuple(value[0] for value in sources), obj))
                for value in (*tuple(value[0] for value in sources), obj):
                    if store.publish_object(value, candidate=reservation) == "conflict":
                        raise StoreConflictError("Automatic dependency publication conflicted.")
                with self.app.lock, self.coordinator.lock:
                    def guard():
                        return (self._owner(attempt) and self.coordinator.generation == epoch
                                and inventory_still_current(self.home, inventory))
                    result = store.update_manifest(requested, expected_manifest=before.fingerprint,
                        candidate=reservation, commit_guard=guard)
                    if result.status == "conflict":
                        raise StoreConflictError("Automatic generation publication conflicted.")
                # Read authority again: successful return alone does not mean still-current.
                return self._install(store, requested, obj, generation, bundle, inventory,
                                     attempt, epoch, "rebuilt" if same else "prepared")
        except UnsupportedGeneration:
            return AutomaticMatchServiceResult("unsupported")
        except StoreLimitError:
            return AutomaticMatchServiceResult("quota")
        except StoreManifestError:
            return AutomaticMatchServiceResult("failed", failure="invalid_storage")
        except (OSError, ValueError, SkatMindError) as error:
            if store is not None and requested is not None and obj is not None:
                try:
                    authority = store.snapshot().manifest
                    if authority == requested:
                        return self._install(store, requested, obj, generation, bundle, inventory,
                                             attempt, epoch, "prepared")
                    if (obj.reference in authority.generations
                            and obj.reference not in before.generations):
                        return AutomaticMatchServiceResult("committed_superseded", generation, True)
                except (OSError, ValueError, SkatMindError):
                    return AutomaticMatchServiceResult("unconfirmed")
            status = ("conflict" if isinstance(error, (StoreConflictError, InventoryConflict))
                      else "failed")
            return AutomaticMatchServiceResult(status)
        finally:
            if store is not None and reservation is not None:
                try:
                    store.release_candidate(reservation)
                except (OSError, ValueError):
                    pass  # Never releases newer work or deletes committed dependencies.

    def _install(self, store, requested, obj, generation, bundle, inventory,
                 attempt, epoch, status):
        authority = store.snapshot().manifest
        if authority != requested:
            return AutomaticMatchServiceResult("committed_superseded", generation, True)
        with self.app.lock, self.coordinator.lock, store._guard():
            if (not self._owner(attempt) or self.coordinator.generation != epoch
                    or not inventory_still_current(self.home, inventory)
                    or store._manifest() != requested):
                return AutomaticMatchServiceResult("reconstruction_needed", generation, True)
            self._installed = _Installed(obj.reference, generation, bundle, inventory)
        return AutomaticMatchServiceResult(status, generation, True, attempt=attempt)

    def consume(self, projector, *, allow_outdated=False):
        """Project/serialize unlocked, then validate immediately before delivery.

        A caller must deliver the returned value immediately; retaining a previous
        returned value does not create an authorization for subsequent requests.
        """
        attempt = self.attempt
        result, resumed, inventory = self._inspect()
        allowed = ("current", "outdated") if allow_outdated else ("current",)
        installed = self._installed
        if result.status not in allowed or installed is None:
            raise StoreConflictError("Automatic result changed, deleted or needs reconstruction.")
        epoch = self.coordinator.generation
        with self.store.pin_objects((installed.reference,),
                                     expected_manifest=resumed.manifest.fingerprint):
            value = projector(installed.bundle)
            final, latest, current_inventory = self._inspect()
            with self.app.lock, self.coordinator.lock, self.store._guard():
                if (not self._owner() or self.attempt is not attempt
                        or self._installed is not installed
                        or final != result or latest.manifest != resumed.manifest
                        or current_inventory != inventory or self.coordinator.generation != epoch
                        or not inventory_still_current(self.home, inventory)
                        or self.store._manifest() != resumed.manifest):
                    raise StoreConflictError("Automatic result changed during final delivery.")
            return value

    def download(self, kind, *, allow_outdated=False):
        return self.consume(lambda bundle: bundle.download(kind), allow_outdated=allow_outdated)

    def capture_delivery(self):
        """Capture exact HTML/control authority, including absent-store membership."""
        attempt, installed = self.attempt, self._installed
        result, resumed, inventory = self._inspect()
        if inventory is None:
            inventory = capture_match_inventory(self.home)
        binding = AutomaticDeliveryBinding(self, attempt, installed, result, resumed,
                                            inventory, self.coordinator.generation)
        self.validate_delivery(binding)
        return binding

    def validate_delivery(self, binding):
        """After serialization, immediately before headers; a projection is not authority."""
        result, resumed, inventory = self._inspect()
        if inventory is None:
            inventory = capture_match_inventory(self.home)
        with self.app.lock, self.coordinator.lock, ExitStack() as stack:
            if self.store is not None:
                stack.enter_context(self.store._guard())
            if (binding.owner is not self or not self._owner(binding.attempt)
                    or self.attempt is not binding.attempt
                    or self._installed is not binding.installed
                    or result != binding.result or resumed != binding.resumed
                    or inventory != binding.inventory
                    or self.coordinator.generation != binding.epoch
                    or not inventory_still_current(self.home, binding.inventory)
                    or resumed is not None and self.store._manifest() != resumed.manifest):
                raise StoreConflictError("Automatic delivery binding changed.")

    @contextmanager
    def delivery_reader(self, binding):
        """Keep the dependency closure pinned through HTTP delivery, outside projectors."""
        with ExitStack() as stack:
            if binding.installed is not None and binding.result.status in ("current", "outdated"):
                stack.enter_context(self.store.pin_objects((binding.installed.reference,),
                    expected_manifest=binding.resumed.manifest.fingerprint))
            self.validate_delivery(binding)
            yield
