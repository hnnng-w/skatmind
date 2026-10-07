"""Read-only GitHub evidence lookup and fail-closed final validation gates."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.run_validation import QUICK, validate_test_accounting
from scripts.validate_installation_cells import CELL_NAMES, HOSTED_WINDOWS, validate_environment
from scripts.validate_v1_supported_platform_matrix import validate_matrix_result
from scripts.validation_identity import read_json, source_identity

WORKFLOW = ".github/workflows/check.yml"
FRESHNESS = timedelta(hours=24)
OS_NAMES = ("ubuntu", "windows")
REQUIRED_JOBS = frozenset({
    "coordinator", "standards", "generated", "check", "v1-supported-platform-matrix",
    *(f"regression ({os_name})" for os_name in OS_NAMES),
    *(f"build ({os_name})" for os_name in OS_NAMES),
    *(f"matrix-result ({os_name})" for os_name in OS_NAMES),
    *(f"cell ({os_name}, {cell})" for os_name in OS_NAMES for cell in CELL_NAMES),
})


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp lacks timezone")
    return result


def eligible_run(run: dict, jobs: list[dict], *, current: dict, repository: str,
                 commit: str, cycle_start: datetime) -> bool:
    """Never authorize from a green label alone; inspect the entire current attempt."""
    try:
        end = timestamp(current["created_at"])
        created, updated = timestamp(run["created_at"]), timestamp(run["updated_at"])
        if any(type(run[key]) is not int or run[key] <= 0
               for key in ("id", "workflow_id", "run_attempt")):
            return False
        if not (
            run["id"] != current["id"] and run["event"] == "push"
            and run["head_branch"] and run["head_branch"] != "main"
            and run["head_sha"] == commit == current["head_sha"]
            and run["repository"]["full_name"] == repository
            and run["head_repository"]["full_name"] == repository
            and run["workflow_id"] == current["workflow_id"]
            and run["path"] == current["path"] == WORKFLOW
            and run["status"] == "completed" and run["conclusion"] == "success"
            and max(cycle_start, end - FRESHNESS) <= created <= updated <= end
        ):
            return False
        names = [job["name"] for job in jobs]
        return (len(names) == len(REQUIRED_JOBS) and set(names) == REQUIRED_JOBS
                and all(job["status"] == "completed" and job["conclusion"] == "success"
                        and job["head_sha"] == commit and job["run_id"] == run["id"]
                        and job["run_attempt"] == run["run_attempt"]
                        for job in jobs))
    except (KeyError, TypeError, ValueError):
        return False


class GitHub:
    def __init__(self, repository: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Invalid repository")
        self.base = f"https://api.github.com/repos/{repository}/"

    def get(self, route: str):
        request = Request(self.base + route, headers={
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        })
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def jobs(self, run: dict) -> list:
        rows = []
        for page in range(1, 11):
            data = self.get(f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs"
                            f"?per_page=100&page={page}")
            rows.extend(data["jobs"])
            if len(rows) == data["total_count"]:
                return rows
            if len(rows) > data["total_count"] or not data["jobs"]:
                break
        raise ValueError("Incomplete job enumeration")


def find_reuse(api, event: dict, *, repository: str, commit: str, run_id: int,
               event_name: str, force_full: bool, policy_commit: str,
               required_run: int | None = None) -> dict | None:
    if (force_full or event_name != "push" or event.get("ref") != "refs/heads/main"
            or policy_commit != commit or event.get("after") != commit):
        return None
    before = event.get("before", "")
    if not re.fullmatch("[0-9a-f]{40}", before) or before == "0" * 40:
        return None
    current = api.get(f"actions/runs/{run_id}")
    if (current["head_sha"] != commit or current["path"] != WORKFLOW
            or current["repository"]["full_name"] != repository):
        return None
    comparison = api.get(f"compare/{before}...{commit}")
    if comparison["status"] != "ahead" or comparison["merge_base_commit"]["sha"] != before:
        return None
    # Establish this integration cycle from the immediately preceding main push.
    history = api.get(f"actions/workflows/{current['workflow_id']}/runs?"
                      + urlencode({"branch": "main", "event": "push", "per_page": 100}))
    prior = [run for run in history["workflow_runs"] if run["id"] != run_id
             and timestamp(run["created_at"]) < timestamp(current["created_at"])]
    if not prior:
        return None
    previous = max(prior, key=lambda run: timestamp(run["created_at"]))
    if previous["head_sha"] != before:
        return None
    cycle_start = timestamp(previous["created_at"])
    if required_run is not None:
        candidates = [api.get(f"actions/runs/{required_run}")]
    else:
        candidates = api.get(f"actions/workflows/{current['workflow_id']}/runs?"
                             + urlencode({"head_sha": commit, "event": "push", "per_page": 100}))[
                                 "workflow_runs"]
    for candidate in candidates:
        if candidate["id"] == run_id or candidate.get("head_branch") == "main":
            continue
        if eligible_run(candidate, api.jobs(candidate), current=current, repository=repository,
                        commit=commit, cycle_start=cycle_start):
            return candidate
    return None


def require_needs(needs: dict, expected: set[str]) -> None:
    if set(needs) != expected or any(row.get("result") != "success" for row in needs.values()):
        raise ValueError("Required upstream job missing, skipped, cancelled, or failed")


def validate_gate_evidence(root: Path, gate: str, source: dict) -> None:
    for os_name, platform_id in (("ubuntu", "ubuntu_github_actions_cpython_3_13"),
                                 ("windows", HOSTED_WINDOWS)):
        result = read_json(root / f"matrix-result-{os_name}" / "result.json")
        if (result["status"] != "passed" or result["source"] != source
                or result["aggregation_version"] != 1
                or result["result"]["platform"]["platform_id"] != platform_id
                or result["evidence_kind"] != ("supported_platform_matrix" if os_name == "ubuntu"
                                                else "hosted_windows_installations")):
            raise ValueError("Foreign or incomplete platform aggregation")
        validate_matrix_result(result["result"])
        validate_environment(result["result"]["platform"], platform_id)
    if gate != "check":
        return
    for name, expected_stages in (
        ("standards", QUICK), ("generated", ("generated-outputs",)),
        *((f"regression-{os_name}", ("pytest-collection", "pytest-parallel", "pytest-exclusive"))
          for os_name in OS_NAMES),
    ):
        directory = root / name
        report = read_json(directory / "summary.json")
        environment = report["environment"]
        if (report["exit_status"] != 0 or environment["commit"] != source["commit"]
                or environment["source_digest"] != source["source_digest"]
                or [s["stage"] for s in report["stages"]] != list(expected_stages)
                or any(s["exit_status"] != 0 for s in report["stages"])):
            raise ValueError("Incomplete or foreign validation stage evidence")
        if name.startswith("regression"):
            os_name = "Windows" if name.endswith("windows") else "Linux"
            if environment["workers"] != 2 or environment["runner_os"] != os_name:
                raise ValueError("Unexpected CI worker count or regression platform")
            collection, parallel, serial = [read_json(directory / f"pytest-{phase}.json")
                                            for phase in ("collection", "parallel", "exclusive")]
            if len(parallel["worker_collections"]) != 2:
                raise ValueError("Required pytest worker missing")
            validate_test_accounting(collection, [parallel, serial], 2)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("decide", "gate"))
    parser.add_argument("--gate", choices=("check", "matrix"))
    parser.add_argument("--evidence-root", type=Path)
    args = parser.parse_args(argv)
    repository, commit = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    reuse = os.environ.get("REUSE", "false") == "true"
    candidate = None
    reason = "Full validation required"
    try:
        if args.operation == "decide" or reuse:
            candidate = find_reuse(
                GitHub(repository), read_json(Path(os.environ["GITHUB_EVENT_PATH"])),
                repository=repository, commit=commit, run_id=int(os.environ["GITHUB_RUN_ID"]),
                event_name=os.environ["GITHUB_EVENT_NAME"],
                force_full=os.environ.get("FORCE_FULL", "false") == "true",
                policy_commit=os.environ.get("POLICY_COMMIT", ""),
                required_run=int(os.environ["REUSE_RUN"]) if reuse else None,
            )
            if candidate:
                reason = f"Exact full candidate evidence: https://github.com/{repository}/actions/runs/{candidate['id']}"
        if args.operation == "gate":
            needs = json.loads(os.environ["NEEDS_JSON"])
            expected = {"coordinator", "build", "cells", "matrix-result"}
            if args.gate == "check":
                expected |= {"standards", "generated", "regression"}
            if reuse:
                if (candidate is None or set(needs) != expected
                        or needs["coordinator"]["result"] != "success"
                        or any(needs[name]["result"] != "skipped"
                               for name in expected - {"coordinator"})):
                    raise ValueError("Reuse authorization or skipped-worker state is invalid")
            else:
                require_needs(needs, expected)
                validate_gate_evidence(args.evidence_root, args.gate, source_identity())
                reason = "All required current-run validation gates and evidence passed"
    except Exception as error:
        if args.operation == "gate":
            print(f"Final gate rejected: {type(error).__name__}: {error}", file=sys.stderr)
            return 1
        candidate = None
        reason = ("Full validation required: evidence unavailable/ineligible "
                  f"({type(error).__name__})")
    print(reason)
    if args.operation == "decide":
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"reuse={'true' if candidate else 'false'}\n"
                         f"reuse_run={candidate['id'] if candidate else ''}\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(f"### Validation evidence\n{reason}\nCommit: `{commit}`\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
