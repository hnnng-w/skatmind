"""Private Match recipe continuity across retirement of Session-dependent generations."""

from dataclasses import replace

from .automatic_learning_contracts import MatchSliceBasisV1
from .automatic_match_preparation import ADAPTERS, BUILDERS, UnsupportedGeneration, automatic_ids
from .automatic_mixed_preparation import admit_generation


def validate_match_basis(basis, manifest):
    recipe = basis.recipe
    if (basis.space_id != manifest.space_id or recipe.adapter_versions != ADAPTERS
            or recipe.builder_versions != BUILDERS
            or (recipe.corpus_id, recipe.dataset_id) != automatic_ids(manifest.space_id)
            or recipe.seed != 0 or recipe.partition_weights != (70, 15, 15)):
        raise UnsupportedGeneration("Unsupported Match continuity recipe.")
    sources = {row.source_version.identity: row for row in manifest.sources}
    ordered = tuple(sorted(recipe.source_version_ids,
        key=lambda key: sources[key].source_version.source.product_id))
    if ordered != recipe.source_version_ids:
        raise ValueError("Match continuity requires canonical selection order.")
    return basis


def basis_from_generation(generation, manifest):
    sources = {row.source_version.identity: row for row in manifest.sources}
    recipe = generation.recipe
    match_ids = tuple(key for key in recipe.source_version_ids
                      if sources[key].source_version.source.family == "match")
    match_recipe = replace(recipe, source_version_ids=match_ids,
        evidence_ids=(), exclusions=(), skipped_situations=(), derived_fingerprints=(),
        catalog_revision=getattr(generation, "match_catalog_revision", recipe.catalog_revision),
        adapter_versions=ADAPTERS, builder_versions=BUILDERS)
    return validate_match_basis(MatchSliceBasisV1(space_id=manifest.space_id, recipe=match_recipe),
                                 manifest)


def basis_for_cleanup(store, manifest):
    """Capture supported legacy current metadata before reference-first retirement."""
    if manifest.match_basis is not None or manifest.current_generation is None:
        return manifest.match_basis
    try:
        generation = admit_generation(store.read_object(manifest.current_generation), manifest)
        return basis_from_generation(generation, manifest)
    except (OSError, ValueError):
        # Storage cleanup can retire unavailable/unsupported descriptors, but cannot
        # invent compatible continuity from them or consult orphan objects.
        return None


def basis_for_update(store, manifest, current, match_ids, evidence_ids):
    if manifest.match_basis is not None:
        basis = validate_match_basis(manifest.match_basis, manifest)
        if current is not None and basis != basis_from_generation(current, manifest):
            raise ValueError("Match continuity disagrees with the current generation.")
        return basis
    if current is not None:
        return basis_from_generation(current, manifest)
    # Legacy fallback is only an exact supported Match-input match. It neither
    # promotes the previous descriptor nor authorizes its mixed output as current.
    if manifest.previous_generation is not None:
        try:
            generation = admit_generation(
                store.read_object(manifest.previous_generation), manifest)
            basis = basis_from_generation(generation, manifest)
        except (OSError, ValueError):
            return None
        evidence = {row.identity: row for row in manifest.evidence}
        prior_evidence = tuple(key for key in generation.recipe.evidence_ids
            if evidence[key].source_version_id in basis.recipe.source_version_ids)
        if basis.recipe.source_version_ids == match_ids and prior_evidence == evidence_ids:
            return basis
    return None
