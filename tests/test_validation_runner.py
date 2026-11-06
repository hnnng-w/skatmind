import copy
import json
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
    def environment(workers):
        assert workers == 2
        return {"commit": "a", "platform": "test"}

    monkeypatch.setattr(runner, "environment_evidence", environment)

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
    assert SERIAL_FILES == {
        "tests/test_early_rejection_observer.py", "tests/test_local_learning_corpus_web.py",
        "tests/test_unified_rejection_transport.py",
        "tests/test_match_analysis_action_placement.py",
    }
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


@pytest.mark.parametrize("workers", range(1, 9))
def test_all_supported_worker_policies_require_exact_phase_layout(workers):
    full = phase(["a", "b"])
    phases = [phase(["a", "b"])] if workers == 1 else [phase(["a"], workers), phase(["b"])]
    assert runner.validate_test_accounting(full, phases, workers)["outcomes"] == {"passed": 2}
    with pytest.raises(ValueError, match="phase layout"):
        runner.validate_test_accounting(full, phases[:-1], workers)
    with pytest.raises(ValueError, match="phase layout"):
        runner.validate_test_accounting(full, [*phases, phase([])], workers)
    full["worker_collections"] = [["a", "b"]]
    with pytest.raises(ValueError, match="phase layout"):
        runner.validate_test_accounting(full, phases, workers)


@pytest.mark.parametrize("workers", [2, 4])
@pytest.mark.parametrize("corruption", ["missing", "duplicate", "failed", "cancelled",
                                      "missing-call", "worker-missing", "workers-absent",
                                      "worker-different", "exclusive-workers",
                                      "unexpected", "duplicate-report", "failed-teardown"])
def test_accounting_rejects_incomplete_or_duplicate_execution(corruption, workers):
    full = phase(["a", "b"])
    parallel = phase(["a"], workers)
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
    elif corruption == "workers-absent":
        parallel["worker_collections"] = []
    elif corruption == "worker-different":
        parallel["worker_collections"][0] = ["b"]
    elif corruption == "exclusive-workers":
        serial["worker_collections"] = [["b"]] * workers
    elif corruption == "unexpected":
        parallel["reports"][0]["nodeid"] = "foreign"
    elif corruption == "failed-teardown":
        serial["reports"][-1]["outcome"] = "failed"
    else:
        parallel["reports"].append(copy.deepcopy(parallel["reports"][0]))
    with pytest.raises(ValueError):
        runner.validate_test_accounting(full, [parallel, serial], workers)


@pytest.mark.parametrize("workers,corruption", [
    (1, None), (2, None), (4, None), (4, "missing-worker"),
    (4, "inconsistent-worker"), (4, "duplicate-report"), (4, "failed-test"),
])
def test_real_runner_modes_group_files_and_finish_workers_before_exclusive(
    tmp_path, monkeypatch, workers, corruption,
):
    # Exercise the actual coordinator and plugin against a tiny external suite only.
    suite, logs = tmp_path / "suite", tmp_path / "logs"
    suite.mkdir()
    logs.mkdir()
    (suite / "tests").mkdir()
    (suite / "pytest.ini").write_text("[pytest]\naddopts = -k must_not_select\n")
    (suite / "conftest.py").write_text(
        "import atexit\nfrom pathlib import Path\n"
        "def pytest_configure(config):\n"
        "    if hasattr(config, 'workerinput'):\n"
        "        path = Path(__file__).parent / (config.workerinput['workerid'] + '.exited')\n"
        "        atexit.register(path.write_text, 'exited')\n"
    )
    for name in ("a", "b", "c", "d"):
        (suite / "tests" / f"test_{name}.py").write_text(
            "import os\nfrom pathlib import Path\nimport pytest\n"
            "@pytest.mark.parametrize('index', range(3))\n"
            "def test_grouped(index):\n"
            "    path = Path(__file__).with_suffix('.pid')\n"
            "    if path.exists():\n"
            "        assert path.read_text() == str(os.getpid())\n"
            "    path.write_text(str(os.getpid()))\n"
        )
    for name in SERIAL_FILES:
        (suite / name).write_text(
            "from pathlib import Path\n"
            "def test_exclusive():\n"
            f"    assert len(list(Path(__file__).parents[1].glob('*.exited'))) == "
            f"{workers if workers > 1 else 0}\n"
        )
    monkeypatch.setenv("PYTHONPATH", str(runner.ROOT))
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k must_not_select -x")
    monkeypatch.setattr(runner, "ROOT", suite)
    stages = []
    if corruption == "failed-test":
        (suite / "tests" / "test_failure.py").write_text("def test_failure():\n    assert False\n")
        assert runner.run_pytest(logs, workers, stages) == 1
        assert [row["stage"] for row in stages] == ["pytest-collection", "pytest-parallel"]
        assert len(list(suite.glob("*.exited"))) == workers
        assert not (logs / "pytest-exclusive.json").exists()
        assert not (logs / "pytest-accounting.json").exists()
        return
    if corruption:
        run_stage = runner.run_stage

        def corrupt_report(name, command, directory):
            result = run_stage(name, command, directory)
            if name == "pytest-parallel":
                path = directory / "pytest-parallel.json"
                report = json.loads(path.read_text())
                if corruption == "missing-worker":
                    report["worker_collections"].pop()
                elif corruption == "inconsistent-worker":
                    report["worker_collections"][0].pop()
                else:
                    report["reports"].append(report["reports"][0])
                path.write_text(json.dumps(report))
            return result

        monkeypatch.setattr(runner, "run_stage", corrupt_report)
        with pytest.raises(ValueError):
            runner.run_pytest(logs, workers, stages)
        assert not (logs / "pytest-accounting.json").exists()
        assert not (logs / "pytest-performance.json").exists()
        return
    assert runner.run_pytest(logs, workers, stages) == 0
    names = (["collection", "serial-all"] if workers == 1 else
             ["collection", "parallel", "exclusive"])
    assert [row["stage"] for row in stages] == [f"pytest-{name}" for name in names]
    reports = [json.loads((logs / f"pytest-{name}.json").read_text()) for name in names]
    assert len(reports[1]["worker_collections"]) == (workers if workers > 1 else 0)
    if workers > 1:
        assert all(assigned_phase(node) == "parallel" for node in reports[1]["collected"])
        assert {node.split("::")[0] for node in reports[2]["collected"]} == SERIAL_FILES
    accounting = json.loads((logs / "pytest-accounting.json").read_text())
    assert accounting["outcomes"] == {"passed": 12 + len(SERIAL_FILES)}
    performance = json.loads((logs / "pytest-performance.json").read_text())
    assert [row["effective_workers"] for row in performance["phases"]] == (
        [1] if workers == 1 else [workers, 1])
    assert [row["wall_seconds"] for row in performance["phases"]] == [
        row["wall_seconds"] for row in stages[1:]]
    rendered = runner.render_pytest_performance(performance)
    assert "not elapsed wall time or acceptance thresholds" in rendered
    assert f"effective workers {workers}" in rendered
    assert "| Module | Summed seconds | Setup | Call | Teardown |" in rendered


def test_runner_stops_before_exclusive_after_parallel_failure(tmp_path, monkeypatch):
    calls = []

    def execute(name, command, directory):
        calls.append(name)
        if name == "pytest-collection":
            (directory / "pytest-collection.json").write_text(json.dumps(phase(["a"])))
        if name == "pytest-parallel":
            assert command[command.index("-n") + 1] == "4"
            assert "--dist=loadfile" in command and "--max-worker-restart=0" in command
        return {"stage": name, "exit_status": 1 if name == "pytest-parallel" else 0,
                "wall_seconds": 1}

    monkeypatch.setattr(runner, "run_stage", execute)
    assert runner.run_pytest(tmp_path, 4, []) == 1
    assert calls == ["pytest-collection", "pytest-parallel"]
    assert not (tmp_path / "pytest-accounting.json").exists()


@pytest.mark.parametrize("cpu_count,process_count", [(8, 4), (None, None)])
def test_capacity_evidence_observes_counts_without_changing_worker_policy(
    monkeypatch, cpu_count, process_count,
):
    monkeypatch.setattr(runner.os, "cpu_count", lambda: cpu_count)
    monkeypatch.setattr(runner.os, "process_cpu_count", lambda: process_count)
    monkeypatch.setattr(runner, "source_identity", lambda: {"source_digest": "test"})
    result = runner.environment_evidence(4)
    assert result["logical_cpu_count"] == cpu_count
    assert result["process_cpu_count"] == process_count
    assert result["workers"] == 4


def test_duration_summary_bounds_rows_and_separates_setup_call_teardown():
    report = phase([f"tests/test_{i:02}.py::test_one" for i in range(25)])
    report["reports"][0]["duration"] = 20
    result = runner.test_duration_summary(report)
    assert result["module_count"] == 25
    assert len(result["slowest_modules"]) == 20
    assert result["summed_test_phase_seconds"] == {"setup": 44, "call": 25, "teardown": 25}
    first = result["slowest_modules"][0]
    assert first == {"module": "tests/test_00.py", "summed_seconds": 22,
                     "setup": 20, "call": 1, "teardown": 1}
    assert [row["module"] for row in result["slowest_modules"][1:]] == [
        f"tests/test_{i:02}.py" for i in range(1, 20)]
    assert runner.test_duration_summary(phase([]))["slowest_modules"] == []
