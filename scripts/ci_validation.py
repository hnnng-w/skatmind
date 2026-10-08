"""Read-only GitHub evidence lookup and fail-closed final validation gates."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
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


def _reject(diagnostics: dict, reason: str) -> bool:
    diagnostics.update(mode="full", reason=reason)
    return False


def _candidate_id(diagnostics: dict, value: object) -> None:
    diagnostics.pop("candidate_run_id", None)
    if type(value) is int and 0 < value < 10**20:
        diagnostics["candidate_run_id"] = value


def eligible_run(run: dict, jobs: list[dict], *, current: dict, repository: str,
                 commit: str, cycle_start: datetime, diagnostics: dict | None = None) -> bool:
    """Never authorize from a green label alone; inspect the entire current attempt."""
    diagnostics = {} if diagnostics is None else diagnostics
    _candidate_id(diagnostics, run.get("id") if isinstance(run, dict) else None)
    try:
        end = timestamp(current["created_at"])
        created, updated = timestamp(run["created_at"]), timestamp(run["updated_at"])
        if any(type(run[key]) is not int or run[key] <= 0
               for key in ("id", "workflow_id", "run_attempt")):
            return _reject(diagnostics, "candidate_malformed")
        if run["id"] == current["id"]:
            return _reject(diagnostics, "candidate_is_current")
        if run["event"] != "push" or not run["head_branch"] or run["head_branch"] == "main":
            return _reject(diagnostics, "candidate_event_or_branch")
        if not run["head_sha"] == commit == current["head_sha"]:
            return _reject(diagnostics, "candidate_commit_mismatch")
        if (run["repository"]["full_name"] != repository
                or run["head_repository"]["full_name"] != repository):
            return _reject(diagnostics, "candidate_repository_mismatch")
        if (run["workflow_id"] != current["workflow_id"]
                or not run["path"] == current["path"] == WORKFLOW):
            return _reject(diagnostics, "candidate_workflow_mismatch")
        if run["status"] != "completed" or run["conclusion"] != "success":
            return _reject(diagnostics, "candidate_not_successful")
        if created < end - FRESHNESS:
            return _reject(diagnostics, "candidate_stale")
        if created < cycle_start:
            return _reject(diagnostics, "candidate_before_integration_cycle")
        if not created <= updated <= end:
            return _reject(diagnostics, "candidate_time_order")
        names = [job["name"] for job in jobs]
        if len(names) != len(REQUIRED_JOBS) or set(names) != REQUIRED_JOBS:
            return _reject(diagnostics, "candidate_job_coverage")
        if any(job["status"] != "completed" or job["conclusion"] != "success" for job in jobs):
            return _reject(diagnostics, "candidate_job_unsuccessful")
        if any(job["head_sha"] != commit or job["run_id"] != run["id"]
               or job["run_attempt"] != run["run_attempt"] for job in jobs):
            return _reject(diagnostics, "candidate_job_identity")
        diagnostics.update(mode="reuse", reason="eligible_candidate")
        return True
    except (KeyError, TypeError, ValueError):
        return _reject(diagnostics, "candidate_malformed")


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
               required_run: int | None = None, diagnostics: dict | None = None) -> dict | None:
    diagnostics = {} if diagnostics is None else diagnostics
    diagnostics.clear()
    diagnostics.update(mode="full", reason="candidate_missing", lookup="request")
    if force_full:
        _reject(diagnostics, "force_full")
        return None
    if event_name != "push":
        _reject(diagnostics, "unsupported_event")
        return None
    if event.get("ref") != "refs/heads/main":
        _reject(diagnostics, "not_main_push")
        return None
    if policy_commit != commit:
        _reject(diagnostics, "policy_commit_mismatch")
        return None
    if event.get("after") != commit:
        _reject(diagnostics, "event_commit_mismatch")
        return None
    before = event.get("before", "")
    if not re.fullmatch("[0-9a-f]{40}", before) or before == "0" * 40:
        _reject(diagnostics, "invalid_previous_commit")
        return None
    diagnostics["lookup"] = "current_run"
    current = api.get(f"actions/runs/{run_id}")
    if (current["head_sha"] != commit or current["path"] != WORKFLOW
            or current["repository"]["full_name"] != repository):
        _reject(diagnostics, "current_run_identity_mismatch")
        return None
    diagnostics["lookup"] = "ancestry"
    comparison = api.get(f"compare/{before}...{commit}")
    if comparison["status"] != "ahead" or comparison["merge_base_commit"]["sha"] != before:
        _reject(diagnostics, "ancestry_not_fast_forward")
        return None
    # Establish this integration cycle from the immediately preceding main push.
    diagnostics["lookup"] = "main_history"
    history = api.get(f"actions/workflows/{current['workflow_id']}/runs?"
                      + urlencode({"branch": "main", "event": "push", "per_page": 100}))
    prior = [run for run in history["workflow_runs"] if run["id"] != run_id
             and timestamp(run["created_at"]) < timestamp(current["created_at"])]
    if not prior:
        _reject(diagnostics, "integration_history_missing")
        return None
    previous = max(prior, key=lambda run: timestamp(run["created_at"]))
    if previous["head_sha"] != before:
        _reject(diagnostics, "integration_previous_commit_mismatch")
        return None
    cycle_start = timestamp(previous["created_at"])
    diagnostics["lookup"] = "candidate_discovery"
    if required_run is not None:
        candidates = [api.get(f"actions/runs/{required_run}")]
    else:
        candidates = api.get(f"actions/workflows/{current['workflow_id']}/runs?"
                             + urlencode({"head_sha": commit, "event": "push", "per_page": 100}))[
                                 "workflow_runs"]
    for candidate in candidates:
        _candidate_id(diagnostics, candidate["id"])
        if candidate["id"] == run_id:
            _reject(diagnostics, "candidate_is_current")
            continue
        if candidate.get("head_branch") == "main":
            _reject(diagnostics, "candidate_is_main")
            continue
        diagnostics["lookup"] = "candidate_jobs"
        if eligible_run(candidate, api.jobs(candidate), current=current, repository=repository,
                        commit=commit, cycle_start=cycle_start, diagnostics=diagnostics):
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


def _exception_reason(error: Exception, diagnostics: dict) -> str:
    """Classify failures without rendering exception text, headers, or payloads."""
    lookup = diagnostics["lookup"]
    if lookup in ("gate_prerequisites", "gate_evidence"):
        return f"{lookup}_invalid"
    if lookup in ("configuration", "api_client"):
        return "configuration_invalid"
    if lookup in ("event", "request"):
        return "event_unavailable" if isinstance(error, OSError) else "event_malformed"
    if isinstance(error, HTTPError):
        if type(error.code) is int and 100 <= error.code <= 599:
            diagnostics["http_status"] = error.code
        return "api_http_error"
    if isinstance(error, OSError):
        return "api_unavailable"
    if isinstance(error, KeyError) and error.args == ("GITHUB_TOKEN",):
        return "api_credentials_unavailable"
    if isinstance(error, (KeyError, TypeError, ValueError, AttributeError)):
        return "api_malformed"
    return "decision_error"


def _decision_text(diagnostics: dict, repository: str) -> str:
    text = (f"Validation decision: mode={diagnostics['mode']} reason={diagnostics['reason']}"
            f" lookup={diagnostics['lookup']}")
    candidate_id = diagnostics.get("candidate_run_id")
    if candidate_id is not None:
        text += f" candidate_run_id={candidate_id}"
    if "http_status" in diagnostics:
        text += f" http_status={diagnostics['http_status']}"
    if (diagnostics["mode"] == "reuse" and candidate_id is not None
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", repository)):
        text += f" source_run=https://github.com/{repository}/actions/runs/{candidate_id}"
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("decide", "gate"))
    parser.add_argument("--gate", choices=("check", "matrix"))
    parser.add_argument("--evidence-root", type=Path)
    args = parser.parse_args(argv)
    repository, commit = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    reuse = os.environ.get("REUSE", "false") == "true"
    candidate = None
    diagnostics = {"mode": "full", "reason": "decision_error", "lookup": "configuration"}
    code = 0
    try:
        if args.operation == "decide" or reuse:
            diagnostics["lookup"] = "api_client"
            api = GitHub(repository)
            diagnostics["lookup"] = "event"
            event = read_json(Path(os.environ["GITHUB_EVENT_PATH"]))
            diagnostics["lookup"] = "configuration"
            candidate = find_reuse(
                api, event,
                repository=repository, commit=commit, run_id=int(os.environ["GITHUB_RUN_ID"]),
                event_name=os.environ["GITHUB_EVENT_NAME"],
                force_full=os.environ.get("FORCE_FULL", "false") == "true",
                policy_commit=os.environ.get("POLICY_COMMIT", ""),
                required_run=int(os.environ["REUSE_RUN"]) if reuse else None,
                diagnostics=diagnostics,
            )
        if args.operation == "gate":
            if reuse and candidate is None:
                code = 1
            else:
                diagnostics["lookup"] = "gate_prerequisites"
                needs = json.loads(os.environ["NEEDS_JSON"])
                expected = {"coordinator", "build", "cells", "matrix-result"}
                if args.gate == "check":
                    expected |= {"standards", "generated", "regression"}
                if reuse:
                    if (set(needs) != expected or needs["coordinator"]["result"] != "success"
                            or any(needs[name]["result"] != "skipped"
                                   for name in expected - {"coordinator"})):
                        raise ValueError("Reuse authorization or skipped-worker state is invalid")
                else:
                    require_needs(needs, expected)
                    diagnostics["lookup"] = "gate_evidence"
                    validate_gate_evidence(args.evidence_root, args.gate, source_identity())
                    diagnostics["reason"] = "current_run_complete"
    except Exception as error:
        candidate = None
        _reject(diagnostics, _exception_reason(error, diagnostics))
        code = 1 if args.operation == "gate" else 0
    message = _decision_text(diagnostics, repository)
    if code:
        message = "Final gate rejected. " + message
    print(message, file=sys.stderr if code else sys.stdout)
    if args.operation == "decide":
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"reuse={'true' if candidate else 'false'}\n"
                         f"reuse_run={candidate['id'] if candidate else ''}\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        safe_commit = commit if re.fullmatch("[0-9a-f]{40}", commit) else "invalid"
        summary.write(f"### Validation evidence\n{message}\nCommit: `{safe_commit}`\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
