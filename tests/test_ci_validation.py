import copy
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from test_installation_cells import SOURCE, aggregate, evidence
from test_validation_runner import phase

from scripts import ci_validation as ci
from scripts.validate_installation_cells import HOSTED_WINDOWS

REPOSITORY = "hnnng-w/skatmind"
COMMIT = "a" * 40
BEFORE = "b" * 40
CURRENT = {"id": 300, "head_sha": COMMIT, "workflow_id": 42,
           "created_at": "2026-10-07T12:00:00Z", "path": ci.WORKFLOW,
           "repository": {"full_name": REPOSITORY}}


def run():
    return {**CURRENT, "id": 200, "event": "push", "head_branch": "task/279-faster-validation",
            "run_attempt": 1, "status": "completed", "conclusion": "success",
            "created_at": "2026-10-07T08:00:00Z", "updated_at": "2026-10-07T10:00:00Z",
            "head_repository": {"full_name": REPOSITORY}}


def jobs():
    return [{"name": name, "status": "completed", "conclusion": "success",
             "head_sha": COMMIT, "run_id": 200, "run_attempt": 1}
            for name in sorted(ci.REQUIRED_JOBS)]


def eligible(candidate, workers):
    return ci.eligible_run(candidate, workers, current=CURRENT, repository=REPOSITORY,
                           commit=COMMIT, cycle_start=ci.timestamp("2026-10-06T12:00:00Z"))


def test_exact_successful_branch_run_is_eligible():
    assert eligible(run(), jobs())
    assert len(ci.REQUIRED_JOBS) == 23


def test_fresh_run_from_before_current_integration_cycle_is_ineligible():
    assert not ci.eligible_run(run(), jobs(), current=CURRENT, repository=REPOSITORY,
                               commit=COMMIT, cycle_start=ci.timestamp("2026-10-07T09:00:00Z"))


@pytest.mark.parametrize("bad", ["missing", "duplicate", "malformed", "cancelled", "failed",
                               "skipped", "wrong-job-commit", "wrong-attempt", "wrong-run",
                               "wrong-commit", "wrong-repository", "fork", "stale", "future",
                               "previous-cycle", "workflow", "policy", "partial", "main", "pr"])
def test_reuse_rejects_foreign_or_incomplete_green_labels(bad):
    candidate, workers = copy.deepcopy(run()), copy.deepcopy(jobs())
    if bad == "missing":
        workers.pop()
    elif bad == "duplicate":
        workers[-1] = workers[0]
    elif bad == "malformed":
        workers[0] = {}
    elif bad in ("cancelled", "failed", "skipped"):
        workers[0]["conclusion"] = bad
    elif bad == "wrong-job-commit":
        workers[0]["head_sha"] = BEFORE
    elif bad == "wrong-attempt":
        workers[0]["run_attempt"] = 2
    elif bad == "wrong-run":
        workers[0]["run_id"] = 199
    elif bad == "wrong-commit":
        candidate["head_sha"] = BEFORE
    elif bad == "wrong-repository":
        candidate["repository"]["full_name"] = "foreign/repository"
    elif bad == "fork":
        candidate["head_repository"]["full_name"] = "foreign/repository"
    elif bad in ("stale", "previous-cycle"):
        candidate["created_at"] = "2026-10-05T08:00:00Z"
    elif bad == "future":
        candidate["updated_at"] = "2026-10-07T12:01:00Z"
    elif bad == "workflow":
        candidate["workflow_id"] = 43
    elif bad == "policy":
        candidate["path"] = ".github/workflows/foreign.yml"
    elif bad == "partial":
        candidate["status"] = "in_progress"
    elif bad == "main":
        candidate["head_branch"] = "main"
    else:
        candidate["event"] = "pull_request"
    assert not eligible(candidate, workers)


class FakeGitHub:
    def __init__(self, *, bad=None):
        self.bad = bad
        self.calls = []

    def get(self, route):
        self.calls.append(route)
        if self.bad == "unavailable":
            raise OSError("API unavailable")
        if route == "actions/runs/300":
            return CURRENT
        if route == "actions/runs/200":
            return run()
        if route.startswith("compare/"):
            return {"status": "diverged" if self.bad == "not-ff" else "ahead",
                    "merge_base_commit": {"sha": BEFORE}}
        if "branch=main" in route:
            return {"workflow_runs": [] if self.bad == "no-cycle" else [{
                "id": 100, "head_sha": BEFORE, "created_at": "2026-10-06T13:00:00Z"}]}
        if "head_sha=" in route:
            return {"workflow_runs": [] if self.bad == "missing" else [run()]}
        raise AssertionError(route)

    def jobs(self, candidate):
        return jobs()[:-1] if self.bad == "partial" else jobs()


def lookup(api, **overrides):
    options = {"repository": REPOSITORY, "commit": COMMIT, "run_id": 300,
               "event_name": "push", "force_full": False, "policy_commit": COMMIT}
    options.update(overrides)
    return ci.find_reuse(api, {"before": BEFORE, "after": COMMIT, "ref": "refs/heads/main"},
                         **options)


def test_lookup_and_final_recheck_use_exact_run_and_current_integration_cycle():
    assert lookup(FakeGitHub())["id"] == 200
    assert lookup(FakeGitHub(), required_run=200)["id"] == 200


@pytest.mark.parametrize("reason", ["not-ff", "no-cycle", "missing", "partial"])
def test_ineligible_lookup_falls_back_to_full(reason):
    assert lookup(FakeGitHub(bad=reason)) is None


@pytest.mark.parametrize("override", [{"force_full": True}, {"event_name": "pull_request"},
                                      {"event_name": "workflow_dispatch"},
                                      {"policy_commit": BEFORE}])
def test_force_full_and_ordinary_execution_never_need_an_api_lookup(override):
    api = FakeGitHub(bad="unavailable")
    assert lookup(api, **override) is None
    assert api.calls == []


def setup_environment(tmp_path, monkeypatch):
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"before": BEFORE, "after": COMMIT, "ref": "refs/heads/main"}))
    for key, value in {
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_SHA": COMMIT, "GITHUB_RUN_ID": "300",
        "GITHUB_EVENT_NAME": "push", "POLICY_COMMIT": COMMIT, "GITHUB_EVENT_PATH": str(event),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
        "REUSE": "false", "FORCE_FULL": "false",
    }.items():
        monkeypatch.setenv(key, value)


def test_unavailable_api_is_full_fallback_not_assumed_success(tmp_path, monkeypatch):
    setup_environment(tmp_path, monkeypatch)
    monkeypatch.setattr(ci, "GitHub", lambda _: FakeGitHub(bad="unavailable"))
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs").read_text() == "reuse=false\nreuse_run=\n"
    assert "unavailable" in (tmp_path / "summary").read_text()


@pytest.mark.parametrize("outcome", ["missing", "skipped", "cancelled", "failure"])
def test_aggregate_needs_cannot_pass_omitted_or_failed_workers(outcome):
    needs = {"one": {"result": "success"}, "two": {"result": outcome}}
    if outcome == "missing":
        needs.pop("two")
    with pytest.raises(ValueError):
        ci.require_needs(needs, {"one", "two"})


def test_reuse_final_gate_rechecks_and_rejects_missing_evidence(tmp_path, monkeypatch):
    setup_environment(tmp_path, monkeypatch)
    monkeypatch.setenv("REUSE", "true")
    monkeypatch.setenv("REUSE_RUN", "200")
    needs = {name: {"result": "skipped"} for name in ("build", "cells", "matrix-result")}
    needs["coordinator"] = {"result": "success"}
    monkeypatch.setenv("NEEDS_JSON", json.dumps(needs))
    monkeypatch.setattr(ci, "GitHub", lambda _: FakeGitHub())
    assert ci.main(["gate", "--gate", "matrix"]) == 0
    monkeypatch.setattr(ci, "GitHub", lambda _: FakeGitHub(bad="partial"))
    assert ci.main(["gate", "--gate", "matrix"]) == 1


def write_gate_evidence(root):
    def write(name, filename, value):
        directory = root / name
        directory.mkdir(exist_ok=True)
        (directory / filename).write_text(json.dumps(value))

    result = aggregate(evidence())
    write("matrix-result-ubuntu", "result.json", result)
    windows = copy.deepcopy(result)
    windows["result"]["platform"].update(platform_id=HOSTED_WINDOWS,
                                         operating_system="Windows Server",
                                         edition="ServerDatacenter",
                                         operating_system_version="10.0.26100")
    windows["evidence_kind"] = "hosted_windows_installations"
    write("matrix-result-windows", "result.json", windows)
    for name, stages in (("standards", ci.QUICK), ("generated", ("generated-outputs",)),
                         ("regression-ubuntu", ("pytest-collection", "pytest-parallel",
                                                "pytest-exclusive")),
                         ("regression-windows", ("pytest-collection", "pytest-parallel",
                                                 "pytest-exclusive"))):
        write(name, "summary.json", {"exit_status": 0, "environment": {
            **SOURCE, "workers": 2,
            "runner_os": "Windows" if name.endswith("windows") else "Linux"},
            "stages": [{"stage": stage, "exit_status": 0} for stage in stages]})
        if name.startswith("regression"):
            for label, report in (("collection", phase(["a", "b"])),
                                  ("parallel", phase(["a"], 2)), ("exclusive", phase(["b"]))):
                write(name, f"pytest-{label}.json", report)


def test_final_gate_reads_both_platforms_and_complete_regression_reports(tmp_path):
    write_gate_evidence(tmp_path)
    ci.validate_gate_evidence(tmp_path, "check", SOURCE)
    path = tmp_path / "regression-windows" / "pytest-parallel.json"
    path.write_text(json.dumps(phase([])))
    with pytest.raises(ValueError, match="worker"):
        ci.validate_gate_evidence(tmp_path, "check", SOURCE)


def test_workflow_has_bounded_safe_complete_graph():
    text = (Path(__file__).resolve().parents[1] / ci.WORKFLOW).read_text()
    for name in ("coordinator", "standards", "generated", "regression", "build", "cells",
                 "matrix-result", "check", "v1-supported-platform-matrix"):
        assert f"\n  {name}:\n" in text
    assert 'branches: ["**"]' in text and "pull_request:" in text
    assert "max-parallel: 4" in text and "--workers 2" in text
    assert "windows-2025" in text and "ubuntu-latest" in text
    assert "cache: pip" in text and "retention-days: 7" in text
    assert "timeout-minutes: 180" in text
    assert "persist-credentials: false" in text
    assert "pull_request_target:" not in text and "write-all" not in text
    assert "cancel-in-progress: false" in text and "continue-on-error" not in text
    assert "workflow_dispatch:" in text and "force_full:" in text
    assert "--gate check" in text and "--gate matrix" in text
    assert all(cell in text for cell in ci.CELL_NAMES)


def test_every_ci_job_uses_one_exact_python_patch():
    text = (Path(__file__).resolve().parents[1] / ci.WORKFLOW).read_text(encoding="utf-8")
    workflow_env = text.split("\nenv:\n", 1)[1].split("\njobs:\n", 1)[0]
    pin = re.search(
        r'^  VALIDATION_PYTHON_VERSION: "([^"]+)"$', workflow_env, re.MULTILINE,
    )
    assert pin is not None, "CI must declare a shared exact Python patch"
    assert re.fullmatch(r"3\.13\.\d+", pin.group(1))
    assert text.count("VALIDATION_PYTHON_VERSION:") == 1
    selectors = re.findall(r"^ +python-version: (.+)$", text, re.MULTILINE)
    assert len(selectors) == text.count("uses: actions/setup-python@v6") == 9
    assert set(selectors) == {"${{ env.VALIDATION_PYTHON_VERSION }}"}


@pytest.mark.parametrize("relative", [
    "LICENSE", "COPYRIGHT", ".github/workflows/check.yml",
    "src/skatmind/app_web/assets/app.css", "scripts/check.ps1",
])
def test_ci_checkout_preserves_blob_bytes_with_windows_eol_defaults(relative):
    root = Path(__file__).resolve().parents[1]
    text = (root / ci.WORKFLOW).read_text(encoding="utf-8")
    workflow_env = text.split("\nenv:\n", 1)[1].split("\njobs:\n", 1)[0]
    settings = {key: value.strip('"') for key, value in re.findall(
        r"^  (GIT_CONFIG_\w+): (.+)$", workflow_env, re.MULTILINE,
    )}
    # Simulate Windows-native text checkout on either OS, without host Git config
    # masking the defect. All Git commands below only read committed objects.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("GIT_CONFIG")}
    count = int(settings["GIT_CONFIG_COUNT"])
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_CONFIG_COUNT=str(count + 1), GIT_CONFIG_KEY_0="core.eol",
                       GIT_CONFIG_VALUE_0="crlf")
    for index in range(count):
        environment[f"GIT_CONFIG_KEY_{index + 1}"] = settings[f"GIT_CONFIG_KEY_{index}"]
        environment[f"GIT_CONFIG_VALUE_{index + 1}"] = settings[f"GIT_CONFIG_VALUE_{index}"]
    original = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{relative}"], cwd=root, env=environment,
        check=True, capture_output=True,
    ).stdout
    checkout = subprocess.run(
        ["git", "cat-file", "--filters", f"HEAD:{relative}"], cwd=root, env=environment,
        check=True, capture_output=True,
    ).stdout
    assert hashlib.sha256(checkout).digest() == hashlib.sha256(original).digest(), (
        f"CI checkout changed committed bytes: {relative}"
    )
