import copy
import json
from types import SimpleNamespace

import pytest

from scripts import validate_installation_cells as cells
from scripts import validate_v1_supported_platform_matrix as matrix
from scripts.validation_identity import digest, read_json

SOURCE = {"commit": "a" * 40, "source_digest": "b" * 64}
PLATFORM = {"platform_id": matrix.V1_SUPPORTED_PLATFORMS[1], "operating_system": "Ubuntu",
            "operating_system_version": "24.04", "python_implementation": "CPython",
            "python_version": "3.13.7"}


def bundle():
    return {"bundle_version": 1, "status": "passed", "source": SOURCE,
            "platform": PLATFORM, "artifacts": {
                "skatmind-0.17.0-py3-none-any.whl": "c" * 64,
                "skatmind-0.17.0.tar.gz": "d" * 64}}


def smoke():
    return {"environment": {"direct_dependency_versions": {
        "jsonschema": "4.23.0", "referencing": "0.31.0", "tzdata": "2026.4"},
        "pip_check": "passed"}, "semantic": {"root_workflows": {
            name: {"default": {"document": {}}, "provenance": {
                "document": {"field_provenance": {}}, "artifacts": [], "warnings": [],
            }} for name in matrix.V1_ROOT_WORKFLOWS}}}


def evidence():
    return [{"cell_version": 1, "status": "passed", "cell": name,
             "manifest_digest": digest(bundle()), "source": SOURCE, "platform": PLATFORM,
             "repository_mutation": "none", "result": matrix._cell_result(form, lane, smoke()),
             "smoke": smoke()}
            for name, (form, lane) in zip(cells.CELL_NAMES, matrix.V1_MATRIX_CELLS, strict=True)]


def aggregate(rows):
    return cells.aggregate_cells(rows, bundle(), SOURCE, PLATFORM["platform_id"])


def test_six_cell_aggregation_preserves_canonical_order_and_result():
    result = aggregate(list(reversed(evidence())))
    matrix.validate_matrix_result(result["result"])
    assert result["source"] == SOURCE
    assert result["evidence_kind"] == "supported_platform_matrix"
    assert [row["installation_form"] for row in result["result"]["cells"]] == [
        "source", "editable", "wheel", "sdist", "wheel", "sdist"]


@pytest.mark.parametrize("key,value", [("python_version", "3.14.0"),
                                      ("python_implementation", "PyPy"),
                                      ("operating_system", "Windows 11"),
                                      ("operating_system_version", None)])
def test_manifest_rejects_malformed_or_false_environment(key, value):
    manifest = copy.deepcopy(bundle())
    manifest["platform"][key] = value
    with pytest.raises(ValueError, match="platform evidence"):
        cells.validate_manifest(manifest, SOURCE, PLATFORM["platform_id"])


@pytest.mark.parametrize("bad", ["missing", "duplicate", "malformed", "cancelled", "failed",
                               "wrong-commit", "wrong-source", "wrong-platform", "artifact",
                               "semantic", "summary", "minimum", "raw-parity", "pip"])
def test_cell_aggregation_rejects_invalid_evidence(bad):
    rows = copy.deepcopy(evidence())
    if bad == "missing":
        rows.pop()
    elif bad == "duplicate":
        rows[-1] = rows[0]
    elif bad == "malformed":
        rows[0] = {}
    elif bad in ("failed", "cancelled"):
        rows[0]["status"] = bad
    elif bad.startswith("wrong-"):
        if bad == "wrong-platform":
            rows[0]["platform"] = {"platform_id": matrix.V1_SUPPORTED_PLATFORMS[0]}
        else:
            rows[0]["source"]["commit" if bad == "wrong-commit" else "source_digest"] = "e" * 64
    elif bad == "artifact":
        rows[0]["manifest_digest"] = "e" * 64
    elif bad == "summary":
        rows[0]["result"]["semantic_digest"] = "e" * 64
    else:
        index = 4 if bad == "minimum" else 0 if bad == "semantic" else 2
        item = rows[index]
        if bad == "semantic":
            item["smoke"]["semantic"]["foreign"] = True
        elif bad == "pip":
            item["smoke"]["environment"]["pip_check"] = "failed"
        else:
            item["smoke"]["environment"]["direct_dependency_versions"]["jsonschema"] = "9.0"
        item["result"] = matrix._cell_result(*matrix.V1_MATRIX_CELLS[index], item["smoke"])
    with pytest.raises((ValueError, matrix.V1SupportedPlatformMatrixError)):
        aggregate(rows)


def test_cell_uses_existing_clean_install_and_exact_minimum_lane(tmp_path, monkeypatch):
    monkeypatch.setattr(cells, "load_bundle", lambda *_: bundle())
    monkeypatch.setattr(cells, "actual_environment", lambda _: PLATFORM)
    monkeypatch.setattr(matrix, "repository_snapshot", lambda: {})
    monkeypatch.setattr(matrix, "validate_direct_import_inventory", lambda: {})
    calls = []

    def install(artifact, **options):
        calls.append((artifact, options))
        assert options["temporary_root"].is_dir()
        return smoke()

    monkeypatch.setattr(cells.distribution, "_install_and_smoke", install)
    result = cells.run_cell("sdist-minimum_supported", tmp_path, PLATFORM["platform_id"])
    artifact, options = calls[0]
    assert artifact.name.endswith(".tar.gz")
    assert options["editable"] is False
    assert options["minimum_dependencies"] == matrix.V1_MINIMUM_RUNTIME_DEPENDENCIES
    assert options["full_root_cli_matrix"] is False
    assert result["status"] == "passed"
    assert not options["temporary_root"].exists()
    with pytest.raises(ValueError, match="Unknown"):
        cells.run_cell("source-minimum_supported", tmp_path, PLATFORM["platform_id"])


def test_bundle_requires_exact_artifact_bytes_and_source(tmp_path, monkeypatch):
    manifest = bundle()
    for name in manifest["artifacts"]:
        path = tmp_path / name
        path.write_bytes(b"artifact")
        manifest["artifacts"][name] = cells.file_digest(path)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(cells, "source_identity", lambda: SOURCE)
    monkeypatch.setattr(cells, "inspect_pair", lambda *_: None)
    assert cells.load_bundle(tmp_path, PLATFORM["platform_id"]) == manifest
    (tmp_path / "skatmind-0.17.0.tar.gz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="bytes"):
        cells.load_bundle(tmp_path, PLATFORM["platform_id"])
    monkeypatch.setattr(cells, "source_identity", lambda: {**SOURCE, "commit": "e" * 40})
    with pytest.raises(ValueError, match="foreign"):
        cells.load_bundle(tmp_path, PLATFORM["platform_id"])


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', 'not-json'])
def test_evidence_json_rejects_malformed_or_duplicate_keys(tmp_path, text):
    path = tmp_path / "evidence.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        read_json(path)


def test_windows_server_cannot_be_windows_11_evidence(monkeypatch):
    monkeypatch.setattr(matrix.platform, "win32_edition", lambda: "ServerDatacenter")
    with pytest.raises(matrix.V1SupportedPlatformMatrixError, match="not Windows Server"):
        matrix._windows_platform_evidence()


def test_hosted_windows_requires_server_product_type_and_records_actual_edition(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(cells.platform, "system", lambda: "Windows")
    monkeypatch.setattr(cells.platform, "win32_edition", lambda: "ServerDatacenterAzureEdition")
    monkeypatch.setattr(cells.sys, "getwindowsversion", lambda: SimpleNamespace(product_type=3),
                        raising=False)
    result = cells.actual_environment(cells.HOSTED_WINDOWS)
    assert result["platform_id"] == cells.HOSTED_WINDOWS
    assert result["edition"] == "ServerDatacenterAzureEdition"
    monkeypatch.setattr(cells.sys, "getwindowsversion", lambda: SimpleNamespace(product_type=1))
    with pytest.raises(ValueError, match="Windows Server"):
        cells.actual_environment(cells.HOSTED_WINDOWS)


def test_hosted_windows_result_is_explicitly_not_windows_11():
    manifest, rows = copy.deepcopy(bundle()), copy.deepcopy(evidence())
    manifest["platform"] = {**PLATFORM, "platform_id": cells.HOSTED_WINDOWS,
                            "operating_system": "Windows Server", "edition": "ServerDatacenter",
                            "operating_system_version": "10.0.26100"}
    for row in rows:
        row["platform"] = manifest["platform"]
        row["manifest_digest"] = digest(manifest)
    result = cells.aggregate_cells(rows, manifest, SOURCE, cells.HOSTED_WINDOWS)
    assert result["evidence_kind"] == "hosted_windows_installations"
    assert result["result"]["platform"]["platform_id"] == cells.HOSTED_WINDOWS
