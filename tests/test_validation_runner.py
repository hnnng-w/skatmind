import copy
import json
import os
import shutil
import subprocess
import sys

import pytest

from scripts import run_validation as runner
from scripts.validation_pytest import SERIAL_FILES, assigned_phase


@pytest.fixture(autouse=True)
def isolated_ci_summary(monkeypatch):
    # Synthetic runner invocations must never append fake results to a real CI summary.
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


def phase(ids, workers=0):
    return {"collected": ids, "exit_status": 0,
            "worker_collections": [ids[:] for _ in range(workers)],
            "reports": [{"nodeid": nodeid, "when": when, "outcome": "passed", "duration": 1}
                        for nodeid in ids for when in ("setup", "call", "teardown")]}


def test_quick_and_full_are_explicit_and_complete():
    assert runner.selected_stages("Quick") == ("ruff", "schema-parity", "input-examples")
    assert runner.selected_stages("Full") == (*runner.QUICK, "generated-outputs",
                                             "distribution", "pytest")
    with pytest.raises(ValueError):
        runner.selected_stages("fast")


def test_subprocess_exit_and_output_are_retained_outside_source(tmp_path):
    result = runner.run_stage("failure", [sys.executable, "-c",
                             "print('useful failure'); raise SystemExit(23)"], tmp_path)
    assert result["exit_status"] == 23
    assert result["wall_seconds"] >= 0
    assert "useful failure" in (tmp_path / "failure.log").read_text()


def test_runner_fail_fast_and_full_default(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "environment_evidence",
                        lambda _: {"commit": "a", "platform": "test"})

    def fail(name, command, directory):
        calls.append(name)
        return {"stage": name, "exit_status": 17, "wall_seconds": 0.5}

    monkeypatch.setattr(runner, "run_stage", fail)
    assert runner.main(["--log-directory", str(tmp_path)]) == 17
    data = json.loads((tmp_path / "summary.json").read_text())
    assert data["mode"] == "Full" and data["exit_status"] == 17
    assert calls == ["ruff"]


@pytest.mark.parametrize("mode", ["Quick", "Full"])
def test_main_executes_exact_mode_selection_with_synthetic_stages(tmp_path, monkeypatch, mode):
    calls = []
    monkeypatch.setattr(runner, "environment_evidence",
                        lambda _: {"commit": "a", "platform": "test"})

    def execute(name, command, directory):
        calls.append(name)
        return {"stage": name, "exit_status": 0, "wall_seconds": 0}

    def pytest_stage(*args):
        calls.append("pytest")
        return 0

    monkeypatch.setattr(runner, "run_stage", execute)
    monkeypatch.setattr(runner, "run_pytest", pytest_stage)
    assert runner.main(["--mode", mode, "--log-directory", str(tmp_path)]) == 0
    assert tuple(calls) == runner.selected_stages(mode)


def test_interruption_never_records_previous_stage_success(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "environment_evidence",
                        lambda _: {"commit": "a", "platform": "test"})

    def interrupt(name, command, directory):
        if name == "schema-parity":
            raise KeyboardInterrupt
        return {"stage": name, "exit_status": 0, "wall_seconds": 0}

    monkeypatch.setattr(runner, "run_stage", interrupt)
    with pytest.raises(KeyboardInterrupt):
        runner.main(["--mode", "Quick", "--log-directory", str(tmp_path)])
    assert json.loads((tmp_path / "summary.json").read_text())["exit_status"] == 1


def test_existing_log_files_cannot_substitute_for_fresh_execution(tmp_path):
    (tmp_path / "pytest-parallel.json").write_text("{}")
    with pytest.raises(SystemExit) as error:
        runner.main(["--log-directory", str(tmp_path)])
    assert error.value.code == 2


def test_powershell_wrapper_default_and_failure_propagation(tmp_path):
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell wrapper is exercised on Windows and PowerShell-equipped hosts")
    script = runner.ROOT / "scripts" / "check.ps1"
    command = ("function python { $global:LASTEXITCODE = 19; "
               "[Console]::WriteLine(($args -join '|')) }; "
               f"& '{script}'")
    completed = subprocess.run([shell, "-NoProfile", "-Command", command + "; exit $LASTEXITCODE"],
                               capture_output=True, text=True)
    assert completed.returncode == 19
    assert "--mode|Full|--workers|2" in completed.stdout
    completed = subprocess.run([shell, "-NoProfile", "-Command",
                                command + " -Mode Quick; exit $LASTEXITCODE"],
                               capture_output=True, text=True)
    assert completed.returncode == 19
    assert "--mode|Quick|--workers|2" in completed.stdout


def test_phase_assignment_includes_future_files_and_exclusive_modules():
    assert assigned_phase("tests/test_future_module.py::test_new") == "parallel"
    assert all(assigned_phase(f"{name}::test_example") == "serial" for name in SERIAL_FILES)
    assert all((runner.ROOT / name).is_file() for name in SERIAL_FILES)


def test_complete_accounting_keeps_skips_and_all_phase_durations():
    parallel, serial = phase(["a", "b"], 2), phase(["c"])
    serial["reports"] = [r for r in serial["reports"] if r["when"] != "call"]
    serial["reports"][0]["outcome"] = "skipped"
    result = runner.validate_test_accounting(phase(["a", "b", "c"]), [parallel, serial], 2)
    assert result == {"collected": 3, "outcomes": {"passed": 2, "skipped": 1},
                      "summed_test_phase_seconds": {"setup": 3, "call": 2, "teardown": 3}}


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "failed", "cancelled",
                                      "missing-call", "worker-missing", "worker-different",
                                      "unexpected", "duplicate-report"])
def test_accounting_rejects_incomplete_or_duplicate_execution(corruption):
    full = phase(["a", "b"])
    parallel = phase(["a"], 2)
    serial = phase(["b"])
    if corruption == "missing":
        serial = phase([])
    elif corruption == "duplicate":
        serial = phase(["a", "b"])
    elif corruption in ("failed", "cancelled"):
        parallel["exit_status"] = 1 if corruption == "failed" else 2
    elif corruption == "missing-call":
        serial["reports"].pop(1)
    elif corruption == "worker-missing":
        parallel["worker_collections"].pop()
    elif corruption == "worker-different":
        parallel["worker_collections"][0] = ["b"]
    elif corruption == "unexpected":
        parallel["reports"][0]["nodeid"] = "foreign"
    else:
        parallel["reports"].append(copy.deepcopy(parallel["reports"][0]))
    with pytest.raises(ValueError):
        runner.validate_test_accounting(full, [parallel, serial], 2)


def test_real_xdist_plugin_reports_file_grouped_complete_execution(tmp_path):
    # Synthetic suite only: no recursive exhaustive invocation.
    for name in ("a", "b"):
        (tmp_path / f"test_{name}.py").write_text("def test_one():\n    assert True\n")
    report = tmp_path / "report.json"
    environment = os.environ.copy()
    environment.pop("PYTEST_ADDOPTS", None)
    completed = subprocess.run([
        sys.executable, "-m", "pytest", "-p", "scripts.validation_pytest", "-n", "2",
        "--dist=loadfile", "--max-worker-restart=0", "--validation-report", str(report),
        "-o", f"cache_dir={tmp_path / 'cache'}", str(tmp_path),
    ], cwd=runner.ROOT, env=environment, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    evidence = json.loads(report.read_text())
    assert len(evidence["worker_collections"]) == 2
    assert len(evidence["collected"]) == 2
    assert runner.validate_test_accounting(evidence, [evidence], 2)["outcomes"] == {"passed": 2}
