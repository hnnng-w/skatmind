"""Independent cells using the existing strict installation/platform validators."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import validate_distribution_artifacts as distribution
from scripts import validate_v1_supported_platform_matrix as matrix
from scripts.validation_identity import (
    digest,
    external_directory,
    file_digest,
    read_json,
    require_digest,
    source_identity,
)

CELL_NAMES = tuple(f"{form}-{lane}" for form, lane in matrix.V1_MATRIX_CELLS)
HOSTED_WINDOWS = "windows_server_github_actions_cpython_3_13"
PLATFORMS = (*matrix.V1_SUPPORTED_PLATFORMS, HOSTED_WINDOWS)


def validate_environment(evidence: dict, expected: str) -> None:
    fields = {"platform_id", "operating_system", "operating_system_version",
              "python_implementation", "python_version"}
    operating_system = "Ubuntu"
    if expected == HOSTED_WINDOWS:
        fields.add("edition")
        operating_system = "Windows Server"
    elif expected == matrix.V1_SUPPORTED_PLATFORMS[0]:
        fields.add("powershell_version")
        operating_system = "Windows 11"
    if (expected not in PLATFORMS or not isinstance(evidence, dict) or set(evidence) != fields
            or any(not isinstance(value, str) or not value for value in evidence.values())
            or evidence["platform_id"] != expected
            or evidence["operating_system"] != operating_system
            or evidence["python_implementation"] != "CPython"
            or not evidence["python_version"].startswith("3.13.")):
        raise ValueError("Malformed or incompatible platform evidence")
    if "powershell_version" in fields and not (
        evidence["powershell_version"] == "5.1"
        or evidence["powershell_version"].startswith("5.1.")
    ):
        raise ValueError("Windows 11 evidence requires PowerShell 5.1")


def actual_environment(expected: str) -> dict:
    if expected != HOSTED_WINDOWS:
        return matrix.detect_actual_platform(expected)
    if (platform.system() != "Windows" or os.environ.get("GITHUB_ACTIONS") != "true"
            or sys.getwindowsversion().product_type not in (2, 3)):
        raise ValueError("Hosted Windows evidence requires an actual GitHub Windows Server")
    return {"platform_id": HOSTED_WINDOWS, "operating_system": "Windows Server",
            "operating_system_version": platform.version(),
            "edition": platform.win32_edition() or "unknown", **matrix._python_evidence()}


def inspect_pair(wheel: Path, sdist: Path) -> None:
    distribution._validate_source_license_metadata()
    arguments = (
        distribution._expected_schema_bytes(), distribution._expected_module_names(),
        distribution._expected_capture_resource_bytes(),
        distribution._expected_corpus_resource_bytes(),
        distribution._expected_app_resource_bytes(), distribution._expected_legal_file_bytes(),
    )
    wheel_metadata = distribution._inspect_wheel(wheel, *arguments)
    sdist_metadata = distribution._inspect_sdist(sdist, *arguments)
    if (wheel_metadata["Name"], wheel_metadata["Version"]) != (
        sdist_metadata["Name"], sdist_metadata["Version"],
    ):
        raise ValueError("Wheel and sdist metadata differ")


def build_bundle(destination: Path, expected_platform: str) -> dict:
    destination = external_directory(destination)
    if list(destination.iterdir()):
        raise ValueError("Build bundle destination must be empty")
    before = matrix.repository_snapshot()
    source = source_identity()
    environment = actual_environment(expected_platform)
    matrix.validate_direct_import_inventory()
    with tempfile.TemporaryDirectory(prefix="skatmind-cell-build-") as temporary:
        _, wheel, sdist, _ = distribution._build_and_inspect_distribution_artifacts(Path(temporary))
        artifacts = {}
        for artifact in (wheel, sdist):
            shutil.copyfile(artifact, destination / artifact.name)
            artifacts[artifact.name] = file_digest(artifact)
    if matrix.repository_snapshot() != before:
        raise ValueError("Build changed repository content")
    manifest = {"bundle_version": 1, "status": "passed", "source": source,
                "platform": environment, "artifacts": artifacts}
    (destination / "manifest.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    return manifest


def validate_manifest(manifest: dict, source: dict, expected_platform: str) -> None:
    if (not isinstance(manifest, dict) or set(manifest) != {
        "bundle_version", "status", "source", "platform", "artifacts",
    } or type(manifest["bundle_version"]) is not int or manifest["bundle_version"] != 1
            or manifest["status"] != "passed"
            or manifest["source"] != source
            or manifest["platform"]["platform_id"] != expected_platform):
        raise ValueError("Incompatible, failed, or foreign build manifest")
    validate_environment(manifest["platform"], expected_platform)
    require_digest(source["commit"], 40)
    require_digest(source["source_digest"])
    artifacts = manifest["artifacts"]
    expected = {f"skatmind-{distribution.PACKAGE_VERSION}-py3-none-any.whl",
                f"skatmind-{distribution.PACKAGE_VERSION}.tar.gz"}
    if set(artifacts) != expected:
        raise ValueError("Missing or unexpected build artifacts")
    for value in artifacts.values():
        require_digest(value)


def load_bundle(bundle: Path, expected_platform: str) -> dict:
    manifest = read_json(bundle / "manifest.json")
    validate_manifest(manifest, source_identity(), expected_platform)
    if {p.name for p in bundle.iterdir()} != {*manifest["artifacts"], "manifest.json"}:
        raise ValueError("Unexpected bundle contents")
    for name, expected in manifest["artifacts"].items():
        if file_digest(bundle / name) != expected:
            raise ValueError("Artifact bytes do not match build identity")
    inspect_pair(*[bundle / next(n for n in manifest["artifacts"] if n.endswith(suffix))
                   for suffix in (".whl", ".tar.gz")])
    return manifest


def run_cell(name: str, bundle: Path, expected_platform: str) -> dict:
    if name not in CELL_NAMES:
        raise ValueError("Unknown installation cell")
    before = matrix.repository_snapshot()
    manifest = load_bundle(bundle, expected_platform)
    environment = actual_environment(expected_platform)
    if environment != manifest["platform"]:
        raise ValueError("Build and cell environments differ")
    matrix.validate_direct_import_inventory()
    form, lane = matrix.V1_MATRIX_CELLS[CELL_NAMES.index(name)]
    with tempfile.TemporaryDirectory(prefix=f"skatmind-{name}-") as temporary:
        root = Path(temporary)
        if form in ("source", "editable"):
            artifact = root / "source"
            distribution._copy_source_tree(artifact)
        else:
            suffix = ".whl" if form == "wheel" else ".tar.gz"
            artifact = bundle / next(n for n in manifest["artifacts"] if n.endswith(suffix))
        try:
            smoke = distribution._install_and_smoke(
                artifact, label=name, temporary_root=root,
                expected_schemas=distribution._expected_schema_bytes(),
                installation_form=form, editable=form == "editable",
                external_source_root=artifact if form == "editable" else None,
                minimum_dependencies=matrix.V1_MINIMUM_RUNTIME_DEPENDENCIES
                if lane == "minimum_supported" else None,
                full_root_cli_matrix=lane == "resolved",
            )
        except distribution.DistributionValidationError as error:
            raise ValueError(matrix._matrix_cell_failure_message(
                error, installation_form=form, dependency_lane=lane, temporary_root=root,
            )) from error
    if matrix.repository_snapshot() != before:
        raise ValueError("Installation cell changed repository content")
    return {"cell_version": 1, "status": "passed", "cell": name,
            "manifest_digest": digest(manifest), "source": manifest["source"],
            "platform": environment, "repository_mutation": "none",
            "result": matrix._cell_result(form, lane, smoke), "smoke": smoke}


def aggregate_cells(evidence: list[dict], manifest: dict, source: dict,
                    expected_platform: str) -> dict:
    validate_manifest(manifest, source, expected_platform)
    if len(evidence) != len(CELL_NAMES):
        raise ValueError("Missing or duplicate installation cell evidence")
    by_name = {}
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {
            "cell_version", "status", "cell", "manifest_digest", "source", "platform",
            "repository_mutation", "result", "smoke",
        }:
            raise ValueError("Malformed cell evidence")
        name = item["cell"]
        if name not in CELL_NAMES or name in by_name:
            raise ValueError("Duplicate or foreign cell evidence")
        if (type(item["cell_version"]) is not int or item["cell_version"] != 1
                or item["status"] != "passed"
                or item["source"] != source or item["manifest_digest"] != digest(manifest)
                or item["platform"] != manifest["platform"]
                or item["repository_mutation"] != "none"):
            raise ValueError("Failed, incompatible, wrong-commit or wrong-platform cell evidence")
        form, lane = matrix.V1_MATRIX_CELLS[CELL_NAMES.index(name)]
        if item["result"] != matrix._cell_result(form, lane, item["smoke"]):
            raise ValueError("Cell summary does not match retained semantic evidence")
        if lane == "minimum_supported" and item["result"]["direct_dependency_versions"] != {
            requirement.split("==")[0]: requirement.split("==")[1]
            for requirement in matrix.V1_MINIMUM_RUNTIME_DEPENDENCIES
        }:
            raise ValueError("Minimum-supported dependencies were substituted")
        by_name[name] = item
    smokes = [by_name[name]["smoke"] for name in CELL_NAMES]
    normalized = [matrix.normalize_semantic_output(smoke) for smoke in smokes]
    if any(smoke != normalized[0] for smoke in normalized[1:]):
        raise ValueError("Semantic outputs differ across installation cells")
    # Preserve the standalone distribution gate's stronger raw resolved-pair comparison.
    if by_name["wheel-resolved"]["smoke"] != by_name["sdist-resolved"]["smoke"]:
        raise ValueError("Wheel and sdist clean-install smoke results differ")
    result = matrix.build_matrix_result(
        [by_name[name]["result"] for name in CELL_NAMES], manifest["platform"],
        ["jsonschema", "referencing", "tzdata"],
    )
    return {"aggregation_version": 1, "status": "passed", "source": source,
            "manifest_digest": digest(manifest),
            "evidence_kind": "hosted_windows_installations" if expected_platform == HOSTED_WINDOWS
            else "supported_platform_matrix", "result": result}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--build-bundle", type=Path)
    operation.add_argument("--cell", choices=CELL_NAMES)
    operation.add_argument("--aggregate", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--expected-platform", choices=PLATFORMS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    external_directory(args.output.parent)
    if args.output.exists():
        parser.error("Evidence output must be new")
    started = time.perf_counter()
    code = 1
    try:
        if args.build_bundle:
            result = build_bundle(args.build_bundle, args.expected_platform)
        elif args.cell:
            result = run_cell(args.cell, args.bundle, args.expected_platform)
        else:
            manifest = load_bundle(args.bundle, args.expected_platform)
            result = aggregate_cells(
                [read_json(p) for p in sorted(args.aggregate.rglob("*.json"))],
                manifest, source_identity(), args.expected_platform,
            )
        args.output.write_text(json.dumps(result, allow_nan=False) + "\n", encoding="utf-8")
        code = 0
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        print(f"Installation validation failed: {error}", file=sys.stderr)
        args.output.with_suffix(".failure.txt").write_text(str(error)[-16_000:], encoding="utf-8")
    finally:
        timing = {"operation": args.cell or ("build" if args.build_bundle else "aggregate"),
                  "wall_seconds": time.perf_counter() - started, "exit_status": code,
                  "platform": platform.platform(), "python": sys.version}
        args.output.with_suffix(".timing.txt").write_text(
            json.dumps(timing) + "\n", encoding="utf-8",
        )
        print(json.dumps(timing), flush=True)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
                output.write(f"### Installation validation\n```json\n{json.dumps(timing)}\n```\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
