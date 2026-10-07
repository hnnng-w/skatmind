"""Small timed local/CI entry point; performance logs are never Product evidence."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections import Counter, deque
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.validation_identity import source_identity

ROOT = Path(__file__).resolve().parents[1]
QUICK = ("ruff", "schema-parity", "input-examples")
FULL = (*QUICK, "generated-outputs", "distribution", "pytest")
COMMANDS = {
    "ruff": ("-m", "ruff", "check", "."),
    "schema-parity": ("scripts/sync_packaged_schemas.py", "--check"),
    "input-examples": ("scripts/validate_examples_schema.py",),
    "generated-outputs": ("scripts/validate_generated_outputs_schema.py",),
    "distribution": ("scripts/validate_distribution_artifacts.py",),
}


def selected_stages(mode: str) -> tuple[str, ...]:
    if mode not in ("Quick", "Full"):
        raise ValueError("Unknown validation mode")
    return QUICK if mode == "Quick" else FULL


def environment_evidence(workers: int) -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()
    return {
        "commit": commit, "python": sys.version, "interpreter": sys.executable,
        "platform": platform.platform(), "workers": workers,
        "installation_mode": "development", "runner_os": os.environ.get("RUNNER_OS"),
        "runner_image": os.environ.get("ImageOS"),
        "runner_image_version": os.environ.get("ImageVersion"),
        "source_digest": source_identity()["source_digest"],
    }


def run_stage(name: str, command: list[str], directory: Path) -> dict:
    started = time.perf_counter()
    print(f"\nStarting {name}: {' '.join(command)}", flush=True)
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    # An ambient -k/-m/-x or injected worker option must not narrow Full.
    environment.pop("PYTEST_ADDOPTS", None)
    tail = deque(maxlen=2000)
    code = 1
    try:
        with subprocess.Popen(
            command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
        ) as child:
            for line in child.stdout:
                print(line, end="", flush=True)
                tail.append(line)
            code = child.wait()
    except OSError as error:
        tail.append(str(error))
        print(error, file=sys.stderr)
    finally:
        elapsed = time.perf_counter() - started
        (directory / f"{name}.log").write_text(
            "".join(tail)[-512_000:], encoding="utf-8",
        )
    print(f"Stage {name}: exit={code}; wall_seconds={elapsed:.3f}", flush=True)
    return {"stage": name, "exit_status": code, "wall_seconds": elapsed}


def validate_test_accounting(collection: dict, phases: list[dict], workers: int) -> dict:
    expected = collection["collected"]
    if collection["exit_status"] != 0 or not expected or len(set(expected)) != len(expected):
        raise ValueError("Full collection failed, is empty, or has duplicate IDs")
    actual = []
    outcomes = Counter()
    durations = Counter()
    for phase in phases:
        ids = phase["collected"]
        if phase["exit_status"] != 0:
            raise ValueError("A pytest phase failed")
        collections = phase["worker_collections"]
        if collections and (len(collections) != workers or any(c != ids for c in collections)):
            raise ValueError("Worker collections are incomplete or inconsistent")
        actual.extend(ids)
        reports = phase["reports"]
        if any(r["nodeid"] not in ids for r in reports):
            raise ValueError("Unexpected executed test")
        grouped = {}
        for report in reports:
            grouped.setdefault(report["nodeid"], []).append(report)
        for nodeid in ids:
            rows = grouped.get(nodeid, [])
            by_phase = {row["when"]: row for row in rows}
            if len(by_phase) != len(rows) or set(by_phase) not in (
                {"setup", "call", "teardown"}, {"setup", "teardown"},
            ):
                raise ValueError(f"Missing or duplicate execution: {nodeid}")
            if any(r["outcome"] not in ("passed", "skipped") for r in rows):
                raise ValueError(f"Failed test: {nodeid}")
            if by_phase["teardown"]["outcome"] != "passed":
                raise ValueError(f"Incomplete teardown: {nodeid}")
            if "call" not in by_phase and by_phase["setup"]["outcome"] != "skipped":
                raise ValueError(f"Missing test call: {nodeid}")
            outcomes["skipped" if any(r["outcome"] == "skipped" for r in rows) else "passed"] += 1
            for row in rows:
                durations[row["when"]] += row["duration"]
    if Counter(actual) != Counter(expected):
        raise ValueError("Parallel and serial phases do not cover the full suite exactly once")
    return {"collected": len(expected), "outcomes": dict(outcomes),
            "summed_test_phase_seconds": dict(durations)}


def run_pytest(directory: Path, workers: int, stages: list) -> int:
    common = [sys.executable, "-m", "pytest", "-p", "scripts.validation_pytest",
              "-o", f"cache_dir={directory / 'pytest-cache'}",
              "-o", "addopts=",
              "--durations=40", "--durations-min=1"]
    phases = [("collection", "all", ["--collect-only", "-qq"])]
    if workers == 1:
        phases.append(("serial-all", "all", []))
    else:
        phases.extend([
            ("parallel", "parallel", ["-n", str(workers), "--dist=loadfile",
                                      "--max-worker-restart=0"]),
            ("exclusive", "serial", []),
        ])
    results = []
    for name, phase, options in phases:
        report = directory / f"pytest-{name}.json"
        result = run_stage(f"pytest-{name}", [
            *common, "--validation-phase", phase, "--validation-report", str(report), *options,
        ], directory)
        stages.append(result)
        if result["exit_status"]:
            return result["exit_status"]
        results.append(json.loads(report.read_text(encoding="utf-8")))
    if workers > 1 and len(results[1]["worker_collections"]) != workers:
        raise ValueError("Parallel workers did not all report collection")
    summary = validate_test_accounting(results[0], results[1:], workers)
    (directory / "pytest-accounting.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8",
    )
    print(f"Complete pytest accounting: {summary}", flush=True)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("Quick", "Full"), default="Full")
    parser.add_argument("--stage", choices=FULL, help="One explicit CI gate; never a Full claim")
    parser.add_argument("--workers", type=int, choices=range(1, 9), default=2)
    parser.add_argument("--log-directory", type=Path)
    args = parser.parse_args(argv)
    directory = (args.log_directory or Path(tempfile.mkdtemp(prefix="skatmind-check-"))).resolve()
    if directory.is_relative_to(ROOT):
        parser.error("Validation logs must remain outside the repository")
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        parser.error("Use a fresh log directory")
    started = time.perf_counter()
    summary = {"mode": args.stage or args.mode, "environment": environment_evidence(args.workers),
               "stages": [], "exit_status": 1}
    print(f"Validation {summary['mode']}; logs: {directory}\n{summary['environment']}", flush=True)
    code = 1
    try:
        for stage in (args.stage,) if args.stage else selected_stages(args.mode):
            code = 1  # An interruption must never retain the previous stage's success.
            if stage == "pytest":
                code = run_pytest(directory, args.workers, summary["stages"])
            else:
                result = run_stage(stage, [sys.executable, *COMMANDS[stage]], directory)
                summary["stages"].append(result)
                code = result["exit_status"]
            if code:
                break
    except (ValueError, KeyError, OSError) as error:
        print(f"Validation accounting failed: {error}", file=sys.stderr)
        code = 1
    finally:
        summary.update(exit_status=code, wall_seconds=time.perf_counter() - started)
        (directory / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8",
        )
        lines = [f"### Validation {summary['mode']}: exit {code}",
                 f"Wall time: {summary['wall_seconds']:.3f}s; workers: {args.workers}",
                 f"Commit: `{summary['environment']['commit']}`",
                 f"Environment: `{summary['environment']['platform']}`", "",
                 "| Stage | Wall seconds | Exit |", "|---|---:|---:|"]
        lines.extend(f"| {r['stage']} | {r['wall_seconds']:.3f} | {r['exit_status']} |"
                     for r in summary["stages"])
        rendered = "\n".join(lines) + "\n"
        print(rendered, flush=True)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
                output.write(rendered)
    if code == 0:
        print(f"{summary['mode']} passed." + (
            " Focused tests, exhaustive tests, generated outputs and installations are separate."
            if summary["mode"] == "Quick" else ""
        ))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
