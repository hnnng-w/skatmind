"""Entry-path replay of sanitized observed evidence; variants are explicitly synthetic."""

import copy
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from scripts import ci_validation as ci

FIXTURE = Path(__file__).parent / "fixtures" / "ci_reuse" / "recorded_main_integration.json"


@pytest.fixture
def recorded():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class RecordedAPI(ci.GitHub):
    def __init__(self, data):
        super().__init__(data["repository"])
        self.data = data
        self.calls = []
        self.responses = {}
        self.job_page_size = 100

    def get(self, route):
        self.calls.append(route)
        category = ("jobs" if "/jobs?" in route else "ancestry" if route.startswith("compare/")
                    else "history" if "branch=main" in route
                    else "candidates" if "head_sha=" in route else "current")
        if category in self.responses:
            response = self.responses[category]
            if isinstance(response, Exception):
                raise response
            return copy.deepcopy(response)
        data = self.data
        if "/jobs?" in route:
            candidate = data["candidate"]
            assert f"/{candidate['id']}/attempts/{candidate['run_attempt']}/" in route
            page = int(parse_qs(urlsplit(route).query)["page"][0])
            start = (page - 1) * self.job_page_size
            rows = data["candidate_jobs"]
            return {"total_count": rows["total_count"],
                    "jobs": copy.deepcopy(rows["jobs"][start:start + self.job_page_size])}
        if route == f"actions/runs/{data['current']['id']}":
            return copy.deepcopy(data["current"])
        if route == f"actions/runs/{data['candidate']['id']}":
            return copy.deepcopy(data["candidate"])
        if category == "ancestry":
            return copy.deepcopy(data["comparison"])
        if category == "history":
            return {"total_count": 431,
                    "workflow_runs": [data["current"], data["previous_main"]]}
        if category == "candidates":
            return {"total_count": 2, "workflow_runs": [
                {"id": data["current"]["id"], "head_branch": "main"}, data["candidate"],
            ]}
        raise AssertionError("Unexpected recorded-response lookup")


def prepare_entry(tmp_path, monkeypatch, recorded):
    api = RecordedAPI(recorded)
    monkeypatch.setattr(ci, "GitHub", lambda _: api)
    frozen = datetime.fromisoformat(
        recorded["provenance"]["replay_wall_clock"].replace("Z", "+00:00"),
    )

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz is None else frozen.astimezone(tz)

    monkeypatch.setattr(ci, "datetime", FrozenDateTime)
    event = tmp_path / "event-projection.json"
    event.write_text(json.dumps(recorded["event_projection"]), encoding="utf-8")
    for key, value in {
        "GITHUB_REPOSITORY": recorded["repository"], "GITHUB_SHA": recorded["commit"],
        "GITHUB_RUN_ID": str(recorded["current"]["id"]), "GITHUB_EVENT_NAME": "push",
        "POLICY_COMMIT": recorded["commit"], "FORCE_FULL": "false", "REUSE": "false",
        "GITHUB_EVENT_PATH": str(event), "GITHUB_OUTPUT": str(tmp_path / "outputs.txt"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary.md"),
    }.items():
        monkeypatch.setenv(key, value)
    return api


def test_recorded_historical_entry_selects_reuse_without_current_main_proof(
    tmp_path, monkeypatch, recorded,
):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=true\nreuse_run=37679574939\n"
    job_calls = [route for route in api.calls if "/jobs?" in route]
    assert job_calls == ["actions/runs/37679574939/attempts/1/jobs?per_page=100&page=1"]


def test_recorded_entry_success_diagnostic_links_exact_source(
    tmp_path, monkeypatch, recorded, capsys,
):
    prepare_entry(tmp_path, monkeypatch, recorded)
    assert ci.main(["decide"]) == 0
    output = capsys.readouterr().out
    assert "mode=reuse reason=eligible_candidate" in output
    assert "candidate_run_id=37679574939" in output
    assert "https://github.com/hnnng-w/skatmind/actions/runs/37679574939" in output
    assert output.strip() in (tmp_path / "summary.md").read_text()


def test_entry_policy_fallback_is_explainable(tmp_path, monkeypatch, recorded, capsys):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    monkeypatch.setenv("POLICY_COMMIT", "f" * 40)
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=false\nreuse_run=\n"
    assert "mode=full reason=policy_commit_mismatch" in capsys.readouterr().out
    assert api.calls == []


@pytest.mark.parametrize("variant,reason", [
    ("commit", "candidate_commit_mismatch"),
    ("repository", "candidate_repository_mismatch"),
    ("fork", "candidate_repository_mismatch"),
    ("workflow", "candidate_workflow_mismatch"),
    ("policy_path", "candidate_workflow_mismatch"),
    ("run_failed", "candidate_not_successful"),
    ("run_cancelled", "candidate_not_successful"),
    ("run_incomplete", "candidate_not_successful"),
    ("missing_job", "candidate_job_coverage"),
    ("duplicate_job", "candidate_job_coverage"),
    ("failed_job", "candidate_job_unsuccessful"),
    ("cancelled_job", "candidate_job_unsuccessful"),
    ("skipped_job", "candidate_job_unsuccessful"),
    ("wrong_attempt", "candidate_job_identity"),
    ("wrong_job_commit", "candidate_job_identity"),
    ("malformed_job", "candidate_malformed"),
    ("stale", "candidate_stale"),
    ("previous_cycle", "candidate_before_integration_cycle"),
    ("later_run", "candidate_time_order"),
    ("current_run", "candidate_is_current"),
    ("main_run", "candidate_is_main"),
    ("ancestry", "ancestry_not_fast_forward"),
    ("merge_base", "ancestry_not_fast_forward"),
    ("integration_before", "integration_previous_commit_mismatch"),
    ("current_identity", "current_run_identity_mismatch"),
])
def test_synthetic_variants_of_recorded_entry_fail_closed_with_reason(
    tmp_path, monkeypatch, recorded, capsys, variant, reason,
):
    candidate, rows = recorded["candidate"], recorded["candidate_jobs"]
    if variant == "commit":
        candidate["head_sha"] = "f" * 40
    elif variant in ("repository", "fork"):
        candidate["repository" if variant == "repository" else "head_repository"][
            "full_name"] = "foreign/DO_NOT_ECHO_PRIVATE_DIAGNOSTIC"
    elif variant == "workflow":
        candidate["workflow_id"] += 1
    elif variant == "policy_path":
        candidate["path"] = ".github/workflows/foreign.yml"
    elif variant in ("run_failed", "run_cancelled"):
        candidate["conclusion"] = "failure" if variant == "run_failed" else "cancelled"
    elif variant == "run_incomplete":
        candidate["status"] = "in_progress"
    elif variant == "missing_job":
        rows["jobs"].pop()
        rows["total_count"] -= 1
    elif variant == "duplicate_job":
        rows["jobs"][-1] = copy.deepcopy(rows["jobs"][0])
    elif variant in ("failed_job", "cancelled_job", "skipped_job"):
        rows["jobs"][0]["conclusion"] = ("failure" if variant == "failed_job"
                                         else variant.removesuffix("_job"))
    elif variant == "wrong_attempt":
        rows["jobs"][0]["run_attempt"] += 1
    elif variant == "wrong_job_commit":
        rows["jobs"][0]["head_sha"] = "f" * 40
    elif variant == "malformed_job":
        rows["jobs"][0].pop("head_sha")
    elif variant == "stale":
        candidate["created_at"] = "2026-10-06T20:00:00Z"
    elif variant == "previous_cycle":
        candidate["created_at"] = "2026-10-06T21:45:00Z"
    elif variant == "later_run":
        candidate.update(created_at="2026-10-07T22:00:00Z", updated_at="2026-10-07T23:00:00Z")
    elif variant == "current_run":
        candidate["id"] = recorded["current"]["id"]
    elif variant == "main_run":
        candidate["head_branch"] = "main"
    elif variant == "ancestry":
        recorded["comparison"]["status"] = "diverged"
    elif variant == "merge_base":
        recorded["comparison"]["merge_base_commit"]["sha"] = "f" * 40
    elif variant == "integration_before":
        recorded["previous_main"]["head_sha"] = "f" * 40
    elif variant == "current_identity":
        recorded["current"]["head_sha"] = "f" * 40
    prepare_entry(tmp_path, monkeypatch, recorded)
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=false\nreuse_run=\n"
    output = capsys.readouterr().out
    assert f"mode=full reason={reason}" in output
    assert "DO_NOT_ECHO_PRIVATE_DIAGNOSTIC" not in output
    assert len(output) < 500
    assert output.strip() in (tmp_path / "summary.md").read_text()


@pytest.mark.parametrize("category,lookup", [
    ("current", "current_run"), ("ancestry", "ancestry"), ("history", "main_history"),
    ("candidates", "candidate_discovery"), ("jobs", "candidate_jobs"),
])
@pytest.mark.parametrize("failure,reason", [
    ("unavailable", "api_unavailable"), ("malformed", "api_malformed"),
    ("http_403", "api_http_error"), ("http_502", "api_http_error"),
])
def test_entry_reports_safe_lookup_category_for_unavailable_or_malformed_api(
    tmp_path, monkeypatch, recorded, capsys, category, lookup, failure, reason,
):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    private = "DO_NOT_ECHO_PRIVATE_DIAGNOSTIC"
    if failure == "unavailable":
        response = OSError(private)
    elif failure == "malformed":
        response = {"private_payload": private}
    else:
        response = HTTPError(f"https://example.invalid/?token={private}",
                             int(failure.removeprefix("http_")), private,
                             {"Authorization": f"Bearer {private}"}, None)
    api.responses[category] = response
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=false\nreuse_run=\n"
    output = capsys.readouterr().out
    assert f"mode=full reason={reason} lookup={lookup}" in output
    assert private not in output and private not in (tmp_path / "summary.md").read_text()
    if failure.startswith("http_"):
        assert f"http_status={failure.removeprefix('http_')}" in output
    if category == "jobs":
        assert "candidate_run_id=37679574939" in output


@pytest.mark.parametrize("setting,value,reason", [
    ("FORCE_FULL", "true", "force_full"),
    ("GITHUB_EVENT_NAME", "pull_request", "unsupported_event"),
    ("GITHUB_EVENT_NAME", "workflow_dispatch", "unsupported_event"),
    ("POLICY_COMMIT", "f" * 40, "policy_commit_mismatch"),
])
def test_entry_request_guards_need_no_api_lookup(
    tmp_path, monkeypatch, recorded, capsys, setting, value, reason,
):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    monkeypatch.setenv(setting, value)
    assert ci.main(["decide"]) == 0
    assert api.calls == []
    assert f"mode=full reason={reason} lookup=request" in capsys.readouterr().out


@pytest.mark.parametrize("event,reason", [
    ({"ref": "refs/heads/task/279"}, "not_main_push"),
    ({"ref": "refs/heads/main", "after": "f" * 40}, "event_commit_mismatch"),
    (None, "event_malformed"),
    ("malformed-json", "event_malformed"),
    ("missing-file", "event_unavailable"),
])
def test_entry_event_failures_are_distinct_from_api_failures(
    tmp_path, monkeypatch, recorded, capsys, event, reason,
):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    path = Path(os.environ["GITHUB_EVENT_PATH"])
    if event == "missing-file":
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(tmp_path / "absent.json"))
    else:
        path.write_text("{" if event == "malformed-json" else json.dumps(event))
    assert ci.main(["decide"]) == 0
    assert api.calls == []
    assert f"mode=full reason={reason}" in capsys.readouterr().out


def test_entry_job_pagination_retains_complete_attempt_identity(tmp_path, monkeypatch, recorded):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    api.job_page_size = 10  # Synthetic pagination of the same 23 observed records.
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=true\nreuse_run=37679574939\n"
    job_calls = [route for route in api.calls if "/jobs?" in route]
    assert job_calls == [f"actions/runs/37679574939/attempts/1/jobs?per_page=100&page={page}"
                         for page in (1, 2, 3)]


def test_entry_incomplete_job_pagination_is_not_success(tmp_path, monkeypatch, recorded, capsys):
    recorded["candidate_jobs"]["total_count"] += 1
    prepare_entry(tmp_path, monkeypatch, recorded)
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=false\nreuse_run=\n"
    assert "reason=api_malformed lookup=candidate_jobs" in capsys.readouterr().out


@pytest.mark.parametrize("category,reason", [
    ("history", "integration_history_missing"), ("candidates", "candidate_missing"),
])
def test_entry_missing_run_evidence_reports_which_lookup_is_empty(
    tmp_path, monkeypatch, recorded, capsys, category, reason,
):
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    api.responses[category] = {"total_count": 0, "workflow_runs": []}
    assert ci.main(["decide"]) == 0
    assert (tmp_path / "outputs.txt").read_text() == "reuse=false\nreuse_run=\n"
    assert f"mode=full reason={reason}" in capsys.readouterr().out


@pytest.mark.parametrize("gate", ["check", "matrix"])
@pytest.mark.parametrize("invalid", [None, "candidate", "prerequisites"])
def test_recorded_final_gates_revalidate_source_and_skipped_worker_authorization(
    tmp_path, monkeypatch, recorded, gate, invalid,
):
    if invalid == "candidate":
        recorded["candidate"]["conclusion"] = "cancelled"
    api = prepare_entry(tmp_path, monkeypatch, recorded)
    monkeypatch.setenv("REUSE", "true")
    monkeypatch.setenv("REUSE_RUN", str(recorded["candidate"]["id"]))
    names = {"build", "cells", "matrix-result"}
    if gate == "check":
        names |= {"standards", "generated", "regression"}
    needs = {name: {"result": "skipped"} for name in names}
    needs["coordinator"] = {"result": "success"}
    if invalid == "prerequisites":
        needs.pop("cells")
    monkeypatch.setenv("NEEDS_JSON", json.dumps(needs))
    assert ci.main(["gate", "--gate", gate]) == (0 if invalid is None else 1)
    assert f"actions/runs/{recorded['candidate']['id']}" in api.calls
    assert not any("head_sha=" in route for route in api.calls)


def test_workflow_consumes_unchanged_coordinator_outputs_and_rechecks_both_gates():
    text = (Path(__file__).resolve().parents[1] / ci.WORKFLOW).read_text(encoding="utf-8")

    def job_block(name):
        following = text.split(f"\n  {name}:\n", 1)[1]
        return re.split(r"\n  [\w-]+:\n", following, maxsplit=1)[0]

    assert "reuse: ${{ steps.evidence.outputs.reuse }}" in text
    assert "reuse_run: ${{ steps.evidence.outputs.reuse_run }}" in text
    for job in ("standards", "generated", "regression", "build", "cells", "matrix-result"):
        block = job_block(job).split("\n    steps:", 1)[0]
        assert "needs.coordinator.outputs.reuse != 'true'" in block
    for job in ("check", "v1-supported-platform-matrix"):
        block = job_block(job)
        assert "if: always() && needs.coordinator.result != 'skipped'" in block
        assert "REUSE: ${{ needs.coordinator.outputs.reuse }}" in block
        assert "REUSE_RUN: ${{ needs.coordinator.outputs.reuse_run }}" in block
